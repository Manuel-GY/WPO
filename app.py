import os
import sys
import uuid
import io
import csv
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session, send_file
import requests
from PIL import Image, ImageOps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database as db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "goodyear-wpo-asrs-secret-key-2026")
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "fotos")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

# API LDAP corporativa de la planta (backend Django proxy al LDAP)
LDAP_API = os.environ.get("LDAP_API", "http://10.107.194.110:8080/api/login-ldap/")

db.init_db()
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Usuario único autorizado para borrado de inspecciones
BORRADO_AUTORIZADO = "ac17157"


def procesar_y_guardar_foto(file_obj, upload_folder, name):
    """Redimensiona y comprime la foto para optimizar ancho de banda y almacenamiento."""
    target_path = os.path.join(upload_folder, name)
    try:
        img = Image.open(file_obj)
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        img.save(target_path, "JPEG", quality=82, optimize=True)
    except Exception:
        file_obj.seek(0)
        file_obj.save(target_path)


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

    puede_borrar = username == BORRADO_AUTORIZADO

    session["username"] = result["username"]
    session["full_name"] = result["full_name"]
    session["puede_borrar"] = puede_borrar
    return jsonify({"ok": True, "full_name": result["full_name"], "puede_borrar": puede_borrar})


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/ldap-lookup", methods=["POST"])
def ldap_lookup():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")
    res = ldap_autenticar(username, password)
    if res["ok"]:
        return jsonify({"ok": True, "username": res["username"], "full_name": res["full_name"]})
    return jsonify({"ok": False, "error": res["error"]}), 401


@app.route("/inspeccion", methods=["GET", "POST"])
def inspeccion():
    now = datetime.now()
    fecha_servidor = now.strftime("%Y-%m-%d")
    hora_servidor = now.strftime("%H:%M")

    if request.method == "POST":
        usuario_ldap = request.form.get("usuario_ldap", "").strip().lower()
        operario_nombre = request.form.get("operario", "").strip()
        password_ldap = request.form.get("password_ldap", "")

        # Si el usuario ingresó contraseña o se requiere validar con el LDAP de la planta
        if password_ldap:
            auth_res = ldap_autenticar(usuario_ldap, password_ldap)
            if not auth_res["ok"]:
                return render_template(
                    "formulario.html",
                    fecha_servidor=fecha_servidor,
                    hora_servidor=hora_servidor,
                    error_ldap=auth_res["error"],
                    usuario_ldap_input=usuario_ldap,
                    operario_input=operario_nombre,
                )
            usuario_ldap = auth_res["username"]
            operario_nombre = auth_res["full_name"]
        elif session.get("username"):
            # Si hay una sesión activa, usar los datos del usuario logueado
            usuario_ldap = session.get("username")
            operario_nombre = session.get("full_name") or operario_nombre

        data = {
            "usuario_ldap": usuario_ldap,
            "operario": operario_nombre,
            "turno": request.form.get("turno", "").strip(),
            "fecha": fecha_servidor,
            "area": request.form.get("area", "ASRS").strip(),
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
                name = f"{uuid.uuid4().hex}.jpg"
                procesar_y_guardar_foto(f, app.config["UPLOAD_FOLDER"], name)
                fotos.append(name)
        data["fotos"] = fotos

        db.guardar_inspeccion(data)
        return redirect(url_for("dashboard", ok=1))
    return render_template("formulario.html", fecha_servidor=fecha_servidor, hora_servidor=hora_servidor)


@app.route("/exito")
def exito():
    return redirect(url_for("dashboard", ok=1))


@app.route("/dashboard")
def dashboard():
    stats = db.estadisticas()
    mostrar_ok = request.args.get("ok") == "1"
    return render_template(
        "dashboard.html",
        stats=stats,
        puede_borrar=session.get("puede_borrar", False),
        username=session.get("username", ""),
        mostrar_ok=mostrar_ok,
    )


@app.route("/borrar/<int:inspeccion_id>", methods=["POST"])
def borrar(inspeccion_id):
    if session.get("username") != BORRADO_AUTORIZADO:
        return jsonify({"ok": False, "error": "Acceso denegado. Solo AC17157 puede borrar inspecciones."}), 403
    
    fotos_a_borrar = db.borrar_inspeccion(inspeccion_id)
    for foto in fotos_a_borrar:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], foto)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    return jsonify({"ok": True})


@app.route("/exportar-csv")
def exportar_csv():
    registros = db.obtener_todas_inspecciones()

    def generate():
        data = io.StringIO()
        writer = csv.writer(data)
        writer.writerow([
            "ID", "Fecha", "Turno", "Area", "Usuario LDAP", "Nombre Operario",
            "Escritorio Limpio", "Piso Limpio", "Mueble Repuestos", "Sin Repuestos Mesón/Piso",
            "Observaciones", "Cantidad Fotos"
        ])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        for r in registros:
            puntos = r.get("puntos", {})
            writer.writerow([
                r.get("id"),
                r.get("fecha"),
                r.get("turno"),
                r.get("area", "ASRS"),
                r.get("usuario_ldap", ""),
                r.get("operario", ""),
                puntos.get("Escritorio", ""),
                puntos.get("Piso", ""),
                puntos.get("MuebleRepuestos", ""),
                puntos.get("SinRepuestos", ""),
                r.get("observaciones", ""),
                len(r.get("fotos_list", []))
            ])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    filename = f"inspecciones_wpo_goodyear_{datetime.now().strftime('%Y%m%d')}.csv"
    response = app.response_class(generate(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@app.route("/fotos/<path:filename>")
def fotos(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
