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
