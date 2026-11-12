from datetime import date, timedelta

from flask import Flask, redirect, render_template_string, request

from base import ouvrir_base

# Style commun aux pages (CSS intégré, aucune dépendance).
STYLE = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { --fond: #f4f6fa; --carte: #fff; --texte: #1f2937; --doux: #6b7280;
          --accent: #2563eb; --danger: #dc2626; --bord: #e5e7eb; }
  body { font-family: system-ui, sans-serif; background: var(--fond); color: var(--texte);
         max-width: 900px; margin: 0 auto; padding: 24px 16px; line-height: 1.5; }
  h1 { color: var(--accent); margin-top: 0; }
  h2 { margin-top: 32px; border-bottom: 2px solid var(--bord); padding-bottom: 4px; }
  h3 { margin: 0 0 8px; font-size: 1rem; }
  ul { list-style: none; padding: 0; margin: 0; }
  li { background: var(--carte); border: 1px solid var(--bord); border-radius: 8px;
       padding: 10px 12px; margin-bottom: 8px; display: flex; flex-wrap: wrap;
       align-items: center; gap: 8px; }
  form { display: inline-flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 0; }
  body > form { background: var(--carte); border: 1px solid var(--bord); border-radius: 8px;
                padding: 12px; }
  input, select { padding: 6px 8px; border: 1px solid var(--bord); border-radius: 6px;
                  font: inherit; }
  input[type=number] { width: 7em; }
  button { padding: 6px 12px; border: 0; border-radius: 6px; background: var(--accent);
           color: #fff; font: inherit; cursor: pointer; }
  button:hover { filter: brightness(1.1); }
  button.danger { background: var(--danger); }
  a { color: var(--accent); text-decoration: none; font-weight: 600; }
  a:hover { text-decoration: underline; }
  .infos { flex: 1; }
  .jours { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
           gap: 12px; margin-top: 16px; }
  .jour { background: var(--carte); border: 1px solid var(--bord); border-radius: 8px;
          padding: 12px; }
  .jour li { background: #eff6ff; border-color: #bfdbfe; }
  .jour li.libre { background: none; border-style: dashed; color: var(--doux); }
</style>
"""

# Le HTML de la page.
PAGE = STYLE + """
<h1>Réservation de salles</h1>

<h2>Salles</h2>
<ul>
  {% for salle in salles %}
    <li>
      <form method="post" action="/salles/{{ salle['id'] }}/modifier">
        <input name="nom" value="{{ salle['nom'] }}" required>
        <input name="capacite" type="number" min="1" value="{{ salle['capacite'] }}" required>
        <button>Modifier</button>
      </form>
      <form method="post" action="/salles/{{ salle['id'] }}/supprimer">
        <button class="danger">Supprimer</button>
      </form>
      <a href="/salles/{{ salle['id'] }}/planning">Planning</a>
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
      <span class="infos"><strong>{{ r["nom"] }}</strong> – {{ r["date"] }} {{ r["debut"] }}-{{ r["fin"] }} – {{ r["personne"] }} ({{ r["participants"] }} pers.)</span>
      <form method="post" action="/reservations/{{ r['id'] }}/annuler">
        <button class="danger">Annuler</button>
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

# Le HTML du planning d'une salle.
PLANNING = STYLE + """
<h1>Planning de {{ salle["nom"] }}</h1>
<p><a href="/">Retour</a></p>

<form method="get">
  <input name="date" type="date" value="{{ lundi }}">
  <button>Voir la semaine</button>
</form>

<div class="jours">
{% for jour in jours %}
  <div class="jour">
    <h3>{{ jour["nom"] }} {{ jour["date"] }}</h3>
    <ul>
      {% for r in jour["reservations"] %}
        <li><strong>{{ r["debut"] }}-{{ r["fin"] }}</strong> {{ r["personne"] }} ({{ r["participants"] }} pers.)</li>
      {% else %}
        <li class="libre">Libre</li>
      {% endfor %}
    </ul>
  </div>
{% endfor %}
</div>
"""

NOMS_JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

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
        deja_occupee = conn.execute(
            "SELECT 1 FROM reservations WHERE personne = ? AND date = ? AND debut < ? AND fin > ?",
            [f["personne"], f["date"], fin, debut],
        ).fetchone()
        if deja_occupee:
            return "Cette personne a déjà une réservation sur ce créneau.", 400
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


# Planning d'une salle sur la semaine (lundi au dimanche) contenant la date demandée.
@app.get("/salles/<int:salle_id>/planning")
def planning(salle_id):
    jour = date.fromisoformat(request.args.get("date") or date.today().isoformat())
    lundi = jour - timedelta(days=jour.weekday())
    dimanche = lundi + timedelta(days=6)
    with ouvrir_base() as conn:
        salle = conn.execute("SELECT nom FROM salles WHERE id = ?", [salle_id]).fetchone()
        if salle is None:
            return "Salle inconnue.", 404
        reservations = conn.execute(
            "SELECT date, debut, fin, personne, participants FROM reservations"
            " WHERE salle_id = ? AND date BETWEEN ? AND ? ORDER BY debut",
            [salle_id, lundi.isoformat(), dimanche.isoformat()],
        ).fetchall()
    jours = []
    for i, nom in enumerate(NOMS_JOURS):
        d = (lundi + timedelta(days=i)).isoformat()
        jours.append({"nom": nom, "date": d,
                      "reservations": [r for r in reservations if r["date"] == d]})
    return render_template_string(PLANNING, salle=salle, lundi=lundi.isoformat(), jours=jours)


if __name__ == "__main__":
    app.run(debug=True)
