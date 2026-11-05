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
"""

app = Flask(__name__)


# Page d'accueil : lit les salles et affiche PAGE.
@app.get("/")
def accueil():
    with ouvrir_base() as conn:
        salles = conn.execute("SELECT id, nom, capacite FROM salles").fetchall()
    return render_template_string(PAGE, salles=salles)


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


if __name__ == "__main__":
    app.run(debug=True)
