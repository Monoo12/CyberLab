"""FILE-SERVER vulnerable a proposito (Flask).

Expone UN login vencible por TRES metodos (todos reales):
  1. leak  -> las credenciales estan filtradas en el HTML (comentario + input oculto).
  2. sqli  -> el login arma la query SQL por concatenacion: ' OR '1'='1 la evade.
  3. hydra -> el usuario admin tiene una clave del diccionario (fuerza bruta).

Login OK -> sesion + /portal + acceso a /restricted/secret.txt.
Pensado para correr dentro del contenedor Docker (ver Dockerfile). NO usar en
una red de produccion: es inseguro por diseno.
"""
from __future__ import annotations

import os
import sqlite3

from flask import (Flask, g, redirect, render_template, request, send_file,
                   session, url_for)

APP_SECRET = os.environ.get("FLASK_SECRET", "cyberlab-dev-secret")
DB_PATH = os.environ.get("LAB_DB", "/tmp/lab.db")
BASE_PATH = os.environ.get("LAB_BASE", "/srv/lab")
LAB_USER = os.environ.get("LAB_USER", "admin")
LAB_PASS = os.environ.get("LAB_PASS", "S3cr3t-2024!")

app = Flask(__name__)
app.secret_key = APP_SECRET


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
    return g.db


@app.teardown_appcontext
def _close_db(_exc):
    d = g.pop("db", None)
    if d is not None:
        d.close()


@app.route("/")
def index():
    # Credenciales filtradas a proposito (metodo 1): el visitante las ve con
    # "Inspeccionar" en el navegador. El comentario y el input oculto son el cebo.
    return render_template("login.html", leak_user=LAB_USER, leak_pass=LAB_PASS,
                           error=None)


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    # *** VULNERABLE A PROPOSITO ***  Query armada por concatenacion de strings.
    # Permite SQL injection (metodo 2). NUNCA hacer esto en codigo real.
    query = ("SELECT username FROM users "
             "WHERE username = '" + username + "' AND password = '" + password + "'")
    try:
        row = db().execute(query).fetchone()
    except sqlite3.Error:
        row = None

    if row:
        session["user"] = row[0]
        return redirect(url_for("portal"))
    return render_template("login.html", leak_user=LAB_USER, leak_pass=LAB_PASS,
                           error="Credenciales incorrectas"), 401


@app.route("/portal")
def portal():
    if "user" not in session:
        return redirect(url_for("index"))
    return render_template("portal.html", user=session["user"])


@app.route("/restricted/secret.txt")
def secret():
    if "user" not in session:
        return "403 Forbidden - login requerido", 403
    path = os.path.join(BASE_PATH, "restricted", "secret.txt")
    if os.path.exists(path):
        return send_file(path, mimetype="text/plain")
    return "secret.txt no encontrado", 404


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "80")))
