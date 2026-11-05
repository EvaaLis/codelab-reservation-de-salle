from flask import Flask, redirect, render_template_string, request

from base import ouvrir_base

# Le HTML de la page.
PAGE = """
<h1>Réservation de salles</h1>

<h2>Salles</h2>
<ul>
  {% for salle in salles %}
    <li>
      <form method="post" action="/salles/{{ salle['id'] }}/modifier" style="display:inline">
        <input name="nom" value="{{ salle['nom'] }}" required>
        <input name="capacite" type="number" min="1" value="{{ salle['capacite'] }}" required>
        <button>Modifier</button>
      </form>
      <form method="post" action="/salles/{{ salle['id'] }}/supprimer" style="display:inline">
        <button>Supprimer</button>
      </form>
    </li>
  {% endfor %}
</ul>

<form method="post" action="/salles">
  <input name="nom" placeholder="Nom" required>
  <input name="capacite" type="number" min="1" placeholder="Capacité" required>
  <button>Ajouter</button>
</form>

<h2>Réservations</h2>
<ul>
  {% for r in reservations %}
    <li>
      {{ r["nom"] }} – {{ r["date"] }} {{ r["debut"] }}-{{ r["fin"] }} – {{ r["personne"] }} ({{ r["participants"] }})
      <form method="post" action="/reservations/{{ r['id'] }}/annuler" style="display:inline">
        <button>Annuler</button>
      </form>
    </li>
  {% endfor %}
</ul>

<h2>Réserver</h2>
<form method="post" action="/reservations">
  <select name="salle_id">
    {% for salle in salles %}
      <option value="{{ salle['id'] }}">{{ salle['nom'] }}</option>
    {% endfor %}
  </select>
  <input name="personne" placeholder="Personne" required>
  <input name="date" type="date" required>
  <input name="debut" type="time" required>
  <input name="fin" type="time" required>
  <input name="participants" type="number" min="1" placeholder="Participants" required>
  <button>Réserver</button>
</form>
"""

app = Flask(__name__)


# Page d'accueil : lit les salles et affiche PAGE.
@app.get("/")
def accueil():
    with ouvrir_base() as conn:
        salles = conn.execute("SELECT id, nom, capacite FROM salles").fetchall()
        reservations = conn.execute(
            "SELECT r.id, s.nom, r.date, r.debut, r.fin, r.personne, r.participants"
            " FROM reservations r JOIN salles s ON s.id = r.salle_id ORDER BY r.date, r.debut"
        ).fetchall()
    return render_template_string(PAGE, salles=salles, reservations=reservations)


# Exemple : reçoit le formulaire et ajoute une salle.
@app.post("/salles")
def ajouter_salle():
    nom = request.form["nom"]
    capacite = int(request.form["capacite"])
    with ouvrir_base() as conn:
        conn.execute("INSERT INTO salles (nom, capacite) VALUES (?, ?)", [nom, capacite])
    return redirect("/")


# Modifie le nom et la capacité d'une salle.
@app.post("/salles/<int:salle_id>/modifier")
def modifier_salle(salle_id):
    nom = request.form["nom"]
    capacite = int(request.form["capacite"])
    with ouvrir_base() as conn:
        max_participants = conn.execute(
            "SELECT MAX(participants) FROM reservations WHERE salle_id = ?", [salle_id]
        ).fetchone()[0]
        if max_participants is not None and capacite < max_participants:
            return "Capacité inférieure au nombre de participants d'une réservation.", 400
        conn.execute(
            "UPDATE salles SET nom = ?, capacite = ? WHERE id = ?", [nom, capacite, salle_id]
        )
    return redirect("/")


# Supprime une salle ; ses réservations partent avec (ON DELETE CASCADE).
@app.post("/salles/<int:salle_id>/supprimer")
def supprimer_salle(salle_id):
    with ouvrir_base() as conn:
        conn.execute("DELETE FROM salles WHERE id = ?", [salle_id])
    return redirect("/")


def minutes(heure):
    h, m = heure.split(":")
    return int(h) * 60 + int(m)


# Réserve une salle au nom d'une personne, en respectant les règles métier.
@app.post("/reservations")
def reserver():
    f = request.form
    salle_id = int(f["salle_id"])
    debut, fin = f["debut"], f["fin"]
    participants = int(f["participants"])
    if debut < "08:00" or fin > "20:00":
        return "La réservation doit avoir lieu entre 8 h et 20 h.", 400
    if not 30 <= minutes(fin) - minutes(debut) <= 240:
        return "La réservation doit durer de 30 min à 4 h.", 400
    with ouvrir_base() as conn:
        salle = conn.execute("SELECT capacite FROM salles WHERE id = ?", [salle_id]).fetchone()
        if salle is None:
            return "Salle inconnue.", 404
        if participants > salle["capacite"]:
            return "Trop de participants pour cette salle.", 400
        conflit = conn.execute(
            "SELECT 1 FROM reservations WHERE salle_id = ? AND date = ? AND debut < ? AND fin > ?",
            [salle_id, f["date"], fin, debut],
        ).fetchone()
        if conflit:
            return "La salle est déjà réservée sur ce créneau.", 400
        conn.execute(
            "INSERT INTO reservations (salle_id, personne, date, debut, fin, participants)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [salle_id, f["personne"], f["date"], debut, fin, participants],
        )
    return redirect("/")


# Annule (supprime) une réservation.
@app.post("/reservations/<int:reservation_id>/annuler")
def annuler(reservation_id):
    with ouvrir_base() as conn:
        conn.execute("DELETE FROM reservations WHERE id = ?", [reservation_id])
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
