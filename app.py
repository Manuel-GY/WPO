import os
import sys
import uuid
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database as db

app = Flask(__name__)
app.config["SECRET_KEY"] = "cambia-esta-clave-en-produccion"
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "fotos")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

# API LDAP corporativa de la planta (backend Django proxy al LDAP)
LDAP_API = os.environ.get("LDAP_API", "http://10.107.194.110:8080/api/login-ldap/")

db.init_db()
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# Usuario único autorizado para borrado de inspecciones
BORRADO_AUTORIZADO = "ac17157"


def ldap_autenticar(username, password):
    """Autentica contra el LDAP corporativo vía la API de la planta."""
    try:
        res = requests.post(
            LDAP_API,
            json={"username": username, "password": password},
            timeout=15,
        )
        data = res.json()
        if res.ok and data.get("status") == "ok":
            return {
                "ok": True,
                "username": username,
                "full_name": data.get("full_name")
                or f"{data.get('first_name','')} {data.get('last_name','')}".strip()
                or username,
                "is_admin": data.get("is_admin"),
            }
        return {"ok": False, "error": data.get("message") or data.get("error") or "Credenciales inválidas."}
    except requests.RequestException as e:
        return {"ok": False, "error": f"Error de conexión con el servidor LDAP ({e})."}


@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    result = ldap_autenticar(username, password)
    if not result["ok"]:
        return jsonify({"ok": False, "error": result["error"]}), 401

    # Privilegio de borrado exclusivo para AC17157 (independiente del LDAP)
    puede_borrar = username == BORRADO_AUTORIZADO

    session["username"] = result["username"]
    session["full_name"] = result["full_name"]
    session["puede_borrar"] = puede_borrar
    return jsonify({"ok": True, "full_name": result["full_name"], "puede_borrar": puede_borrar})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/inspeccion", methods=["GET", "POST"])
def inspeccion():
    # Fecha y hora tomadas directamente del servidor (no modificables por el usuario)
    now = datetime.now()
    fecha_servidor = now.strftime("%Y-%m-%d")
    hora_servidor = now.strftime("%H:%M")

    if request.method == "POST":
        data = {
            "operario": request.form.get("operario", "").strip(),
            "turno": request.form.get("turno", "").strip(),
            "fecha": fecha_servidor,  # Ignora la fecha que envía el navegador
            "area": request.form.get("area", "").strip(),
            "observaciones": request.form.get("observaciones", "").strip(),
        }
        puntos = {}
        for key in request.form:
            if key.startswith("punto_"):
                puntos[key[6:]] = request.form.get(key)
        data["puntos"] = puntos

        fotos = []
        files = request.files.getlist("fotos")
        for f in files:
            if f and f.filename:
                ext = os.path.splitext(f.filename)[1] or ".jpg"
                if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"):
                    ext = ".jpg"
                name = f"{uuid.uuid4().hex}{ext}"
                f.save(os.path.join(app.config["UPLOAD_FOLDER"], name))
                fotos.append(name)
        data["fotos"] = fotos

        db.guardar_inspeccion(data)
        return redirect(url_for("exito", n=len(fotos)))
    return render_template("formulario.html", fecha_servidor=fecha_servidor, hora_servidor=hora_servidor)


@app.route("/exito")
def exito():
    n = request.args.get("n", 0, type=int)
    return render_template("exito.html", n=n)


@app.route("/dashboard")
def dashboard():
    stats = db.estadisticas()
    return render_template("dashboard.html", stats=stats,
                           puede_borrar=session.get("puede_borrar", False),
                           username=session.get("username", ""))


@app.route("/borrar/<int:inspeccion_id>", methods=["POST"])
def borrar(inspeccion_id):
    if session.get("username") != BORRADO_AUTORIZADO:
        return jsonify({"ok": False, "error": "Acceso denegado. Solo AC17157 puede borrar inspecciones."}), 403
    db.borrar_inspeccion(inspeccion_id)
    return jsonify({"ok": True})


@app.route("/fotos/<path:filename>")
def fotos(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
