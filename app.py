import os
import sys
import uuid
import io
import csv
import urllib.parse
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session, send_file
import requests
import qrcode
from PIL import Image, ImageOps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database as db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "goodyear-wpo-5s-secret-key-2026")
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "fotos")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

# API LDAP corporativa de la planta (backend Django proxy al LDAP)
LDAP_API = os.environ.get("LDAP_API", "http://10.107.194.110:8080/api/login-ldap/")

db.init_db()
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Usuario único autorizado para borrado de inspecciones y ver QRs
BORRADO_AUTORIZADO = "ac17157"


def es_colector_o_movil(user_agent_str):
    """Detecta si la petición proviene de un colector industrial (Datalogic, ZTBrowser, Windows CE) o móvil."""
    if not user_agent_str:
        return False
    ua = user_agent_str.lower()
    keywords = [
        "datalogic", "falcon", "skorpio", "ztbrowser", "windows ce", "wce",
        "mobile", "arm", "android", "pocketie", "symbian", "webos", "iphone",
        "ipad", "ipod", "blackberry", "iemobile", "opera mini", "windows phone"
    ]
    return any(k in ua for k in keywords)


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
    es_admin = session.get("username") == BORRADO_AUTORIZADO
    user_agent = request.user_agent.string if request.user_agent else ""
    es_dispositivo_movil = es_colector_o_movil(user_agent)

    # Restricción: Bloquear acceso desde navegador PC estándar si NO es el Administrador AC17157
    if not es_admin and not es_dispositivo_movil:
        return render_template("acceso_denegado_pc.html")

    now = datetime.now()
    fecha_servidor = now.strftime("%Y-%m-%d")
    hora_servidor = now.strftime("%H:%M")
    area_param = request.args.get("area", "").strip()

    if request.method == "POST":
        usuario_ldap = request.form.get("usuario_ldap", "").strip().lower()
        operario_nombre = request.form.get("operario", "").strip()
        password_ldap = request.form.get("password_ldap", "")

        if password_ldap:
            auth_res = ldap_autenticar(usuario_ldap, password_ldap)
            if not auth_res["ok"]:
                return render_template(
                    "formulario.html",
                    fecha_servidor=fecha_servidor,
                    hora_servidor=hora_servidor,
                    area_param=area_param,
                    error_ldap=auth_res["error"],
                    usuario_ldap_input=usuario_ldap,
                    operario_input=operario_nombre,
                )
            usuario_ldap = auth_res["username"]
            operario_nombre = auth_res["full_name"]
        elif session.get("username"):
            usuario_ldap = session.get("username")
            operario_nombre = session.get("full_name") or operario_nombre

        data = {
            "usuario_ldap": usuario_ldap,
            "operario": operario_nombre,
            "turno": request.form.get("turno", "").strip(),
            "fecha": fecha_servidor,
            "area": request.form.get("area", "Carros").strip(),
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
    return render_template(
        "formulario.html",
        fecha_servidor=fecha_servidor,
        hora_servidor=hora_servidor,
        area_param=area_param,
    )


@app.route("/qrs")
def qrs_page():
    """Vista de catálogo de QRs imprimibles - Exclusivo para Administrador AC17157."""
    if session.get("username") != BORRADO_AUTORIZADO:
        return redirect(url_for("dashboard", err="qr_denied"))
    
    host_url = request.host_url.rstrip("/")
    areas_predeterminadas = ["Carros", "Zona Tambores", "Taller", "Mezzanina"]
    return render_template("qrs.html", host_url=host_url, areas=areas_predeterminadas)


@app.route("/qr-img")
def qr_img():
    """Generador dinámico de imagen PNG de QR según área."""
    if session.get("username") != BORRADO_AUTORIZADO:
        return jsonify({"ok": False, "error": "Acceso denegado"}), 403

    area = request.args.get("area", "Carros").strip()
    host_url = request.host_url.rstrip("/")
    target_url = f"{host_url}/inspeccion?area={urllib.parse.quote(area)}"
    img = qrcode.make(target_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/exito")
def exito():
    return redirect(url_for("dashboard", ok=1))


@app.route("/dashboard")
def dashboard():
    stats = db.estadisticas()
    mostrar_ok = request.args.get("ok") == "1"
    err = request.args.get("err")
    return render_template(
        "dashboard.html",
        stats=stats,
        puede_borrar=session.get("puede_borrar", False),
        username=session.get("username", ""),
        mostrar_ok=mostrar_ok,
        err=err,
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
                r.get("area", "Carros"),
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

    filename = f"inspecciones_5s_wpo_goodyear_{datetime.now().strftime('%Y%m%d')}.csv"
    response = app.response_class(generate(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@app.route("/fotos/<path:filename>")
def fotos(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
