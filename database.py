import os
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inspecciones.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inspecciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                turno TEXT,
                area TEXT,
                usuario_ldap TEXT DEFAULT '',
                operario TEXT,
                observaciones TEXT,
                puntos TEXT,
                fotos TEXT DEFAULT '[]',
                creado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        # Migración: agregar columna fotos y usuario_ldap si no existen
        cols = [r[1] for r in conn.execute("PRAGMA table_info(inspecciones)").fetchall()]
        if "fotos" not in cols:
            conn.execute("ALTER TABLE inspecciones ADD COLUMN fotos TEXT DEFAULT '[]'")
        if "usuario_ldap" not in cols:
            conn.execute("ALTER TABLE inspecciones ADD COLUMN usuario_ldap TEXT DEFAULT ''")
        conn.commit()


def guardar_inspeccion(data):
    puntos_json = json_dumps(data.get("puntos", {}))
    fotos_l = data.get("fotos", [])
    fotos_json = json_dumps(fotos_l)
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO inspecciones (fecha, turno, area, usuario_ldap, operario, observaciones, puntos, fotos)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("fecha"),
                data.get("turno"),
                data.get("area", "ASRS"),
                data.get("usuario_ldap", ""),
                data.get("operario"),
                data.get("observaciones"),
                puntos_json,
                fotos_json,
            ),
        )
        conn.commit()
        return cur.lastrowid


def total_inspecciones():
    with get_db() as conn:
        cur = conn.execute("SELECT COUNT(*) AS c FROM inspecciones")
        row = cur.fetchone()
        return row["c"] if row else 0


def borrar_inspeccion(inspeccion_id):
    """Elimina el registro de la BD y devuelve la lista de nombres de fotos a borrar del disco."""
    fotos_a_borrar = []
    with get_db() as conn:
        cur = conn.execute("SELECT fotos FROM inspecciones WHERE id = ?", (inspeccion_id,))
        row = cur.fetchone()
        if row and row["fotos"]:
            fotos_a_borrar = json_loads(row["fotos"])
        conn.execute("DELETE FROM inspecciones WHERE id = ?", (inspeccion_id,))
        conn.commit()
    return fotos_a_borrar


def json_dumps(obj):
    return json.dumps(obj, ensure_ascii=False)


def json_loads(s):
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}


def obtener_todas_inspecciones():
    with get_db() as conn:
        filas = conn.execute("SELECT * FROM inspecciones ORDER BY id DESC").fetchall()
    registros = [dict(r) for r in filas]
    for r in registros:
        r["puntos"] = json_loads(r.get("puntos", ""))
        r["fotos_list"] = json_loads(r.get("fotos", ""))
    return registros


def estadisticas():
    registros = obtener_todas_inspecciones()
    base = datetime.now().strftime("%Y-%m")

    mes_actual = [r for r in registros if (r["fecha"] or "")[:7] == base]

    # Conteo mensual (últimos meses)
    meses = {}
    for r in registros:
        m = (r["fecha"] or "")[:7]
        if m:
            meses[m] = meses.get(m, 0) + 1

    # Conteo y cumplimiento por turno
    turnos_list = ["A", "B", "C", "D"]
    por_turno = {t: {"total": 0, "evaluados": 0, "cumplidos": 0, "pct": 0.0} for t in turnos_list}

    # Cumplimiento por punto de revisión
    nombres_puntos = {
        "Escritorio": "Escritorio limpio",
        "Piso": "Piso limpio",
        "MuebleRepuestos": "Mueble repuestos ordenado",
        "SinRepuestos": "Sin repuestos en mesón/piso",
    }
    por_punto = {k: {"nombre": v, "si": 0, "no": 0, "pct": 0.0} for k, v in nombres_puntos.items()}

    total_evaluados = 0
    total_cumplidos = 0

    for r in registros:
        t = r.get("turno") or "Otros"
        if t not in por_turno:
            por_turno[t] = {"total": 0, "evaluados": 0, "cumplidos": 0, "pct": 0.0}
        por_turno[t]["total"] += 1

        puntos = r.get("puntos", {})
        for pk, pv in puntos.items():
            if pk not in por_punto:
                por_punto[pk] = {"nombre": pk, "si": 0, "no": 0, "pct": 0.0}

            total_evaluados += 1
            por_turno[t]["evaluados"] += 1

            if pv == "Sí":
                total_cumplidos += 1
                por_turno[t]["cumplidos"] += 1
                por_punto[pk]["si"] += 1
            elif pv == "No":
                por_punto[pk]["no"] += 1

    # Calcular porcentajes por turno
    for t, data in por_turno.items():
        if data["evaluados"] > 0:
            data["pct"] = round((data["cumplidos"] / data["evaluados"]) * 100, 1)

    # Calcular porcentajes por punto
    for pk, data in por_punto.items():
        tot = data["si"] + data["no"]
        if tot > 0:
            data["pct"] = round((data["si"] / tot) * 100, 1)

    # Cumplimiento global %
    cumplimiento_global = (
        round((total_cumplidos / total_evaluados) * 100, 1) if total_evaluados > 0 else 100.0
    )

    # Conteo por area
    areas = {}
    for r in registros:
        a = r.get("area") or "ASRS"
        areas[a] = areas.get(a, 0) + 1

    return {
        "total": len(registros),
        "mes_actual": mes_actual,
        "total_mes": len(mes_actual),
        "cumplimiento_global": cumplimiento_global,
        "total_evaluados": total_evaluados,
        "total_cumplidos": total_cumplidos,
        "por_mes": dict(sorted(meses.items())),
        "por_turno": por_turno,
        "por_punto": por_punto,
        "por_area": areas,
        "registros": registros,
    }
