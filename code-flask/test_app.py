import pytest

import base
from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Base temporaire, recréée depuis base.sql pour chaque test.
    monkeypatch.setattr(base, "BASE", tmp_path / "test.db")
    return app.test_client()


def lire(sql, params=()):
    with base.ouvrir_base() as conn:
        return conn.execute(sql, params).fetchall()


def test_accueil(client):
    assert client.get("/").status_code == 200


def test_ajouter_salle(client):
    client.post("/salles", data={"nom": "S3", "capacite": "15"})
    assert lire("SELECT capacite FROM salles WHERE nom = 'S3'")[0][0] == 15


def test_modifier_salle(client):
    client.post("/salles/2/modifier", data={"nom": "S2 bis", "capacite": "10"})
    salle = lire("SELECT nom, capacite FROM salles WHERE id = 2")[0]
    assert (salle["nom"], salle["capacite"]) == ("S2 bis", 10)


def test_modifier_capacite_sous_participants_refusee(client):
    # S1 a une réservation de 12 participants.
    reponse = client.post("/salles/1/modifier", data={"nom": "S1", "capacite": "10"})
    assert reponse.status_code == 400
    assert lire("SELECT capacite FROM salles WHERE id = 1")[0][0] == 20


def test_supprimer_salle_supprime_ses_reservations(client):
    client.post("/salles/1/supprimer")
    assert lire("SELECT * FROM salles WHERE id = 1") == []
    assert lire("SELECT * FROM reservations WHERE salle_id = 1") == []


# Réservations. Base : S1 (capacité 20) réservée le 2026-11-09 de 10:00 à 12:00.
def reserver(client, **champs):
    data = {"salle_id": "1", "personne": "Bob", "date": "2026-11-09",
            "debut": "14:00", "fin": "15:00", "participants": "5"}
    data.update(champs)
    return client.post("/reservations", data=data)


def nb_reservations():
    return len(lire("SELECT * FROM reservations"))


def test_reserver_salle(client):
    assert reserver(client).status_code == 302
    assert lire("SELECT personne FROM reservations WHERE debut = '14:00'")[0][0] == "Bob"


def test_reserver_chevauchement_refuse(client):
    assert reserver(client, debut="11:00", fin="13:00").status_code == 400
    assert nb_reservations() == 1


def test_reserver_bout_a_bout_autorise(client):
    assert reserver(client, debut="12:00", fin="13:00").status_code == 302


def test_reserver_au_dela_capacite_refuse(client):
    assert reserver(client, participants="21").status_code == 400


def test_reserver_hors_horaires_refuse(client):
    assert reserver(client, debut="07:30", fin="09:00").status_code == 400
    assert reserver(client, debut="19:30", fin="20:30").status_code == 400


def test_reserver_duree_hors_limites_refusee(client):
    assert reserver(client, debut="14:00", fin="14:20").status_code == 400
    assert reserver(client, debut="14:00", fin="18:30").status_code == 400
    assert nb_reservations() == 1


def test_accueil_affiche_reservation(client):
    assert "Alice" in client.get("/").get_data(as_text=True)


def test_annuler_reservation(client):
    assert client.post("/reservations/1/annuler").status_code == 302
    assert nb_reservations() == 0


def test_annuler_libere_le_creneau(client):
    client.post("/reservations/1/annuler")
    assert reserver(client, debut="10:00", fin="12:00").status_code == 302


# Planning. Le 2026-11-09 est un lundi, le 2026-11-15 un dimanche.
def page_planning(client, salle_id, jour):
    return client.get(f"/salles/{salle_id}/planning?date={jour}").get_data(as_text=True)


def test_planning_semaine_du_lundi_au_dimanche(client):
    assert "Alice" in page_planning(client, 1, "2026-11-09")
    assert "Alice" in page_planning(client, 1, "2026-11-15")
    assert "Alice" not in page_planning(client, 1, "2026-11-08")
    assert "Alice" not in page_planning(client, 1, "2026-11-16")


def test_planning_affiche_seulement_la_salle(client):
    assert "Alice" not in page_planning(client, 2, "2026-11-09")


def test_planning_salle_inconnue(client):
    assert client.get("/salles/99/planning").status_code == 404


# Une personne ne peut pas avoir deux réservations qui se chevauchent (Alice : S1, lundi 10:00-12:00).
def test_personne_chevauchement_autre_salle_refuse(client):
    reponse = reserver(client, salle_id="2", personne="Alice", debut="11:00", fin="13:00")
    assert reponse.status_code == 400
    assert nb_reservations() == 1


def test_personne_bout_a_bout_autorise(client):
    assert reserver(client, salle_id="2", personne="Alice", debut="12:00", fin="13:00").status_code == 302


def test_autre_personne_meme_creneau_autre_salle_autorise(client):
    assert reserver(client, salle_id="2", personne="Bob", debut="11:00", fin="12:00").status_code == 302


# Type de local.
def test_ajouter_salle_avec_type(client):
    client.post("/salles", data={"nom": "Labo", "capacite": "12", "type": "Laboratoire"})
    assert lire("SELECT type FROM salles WHERE nom = 'Labo'")[0][0] == "Laboratoire"


def test_modifier_type_salle(client):
    client.post("/salles/2/modifier", data={"nom": "S2", "capacite": "8", "type": "Auditoire"})
    assert lire("SELECT type FROM salles WHERE id = 2")[0][0] == "Auditoire"


def test_type_inconnu_refuse(client):
    reponse = client.post("/salles", data={"nom": "X", "capacite": "5", "type": "Piscine"})
    assert reponse.status_code == 400
    assert lire("SELECT * FROM salles WHERE nom = 'X'") == []
