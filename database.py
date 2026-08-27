import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inspecciones.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inspecciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            turno TEXT,
            area TEXT,
            operario TEXT,
            observaciones TEXT,
            puntos TEXT,
            creado_en TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    # Migración: agregar columna fotos si no existe (para BD creadas antes)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(inspecciones)").fetchall()]
    if "fotos" not in cols:
        conn.execute("ALTER TABLE inspecciones ADD COLUMN fotos TEXT DEFAULT '[]'")
    conn.commit()
    conn.close()


def guardar_inspeccion(data):
    conn = get_db()
    puntos_json = json_dumps(data.get("puntos", {}))
    fotos_l = data.get("fotos", [])
    fotos_json = json_dumps(fotos_l)
    conn.execute(
        """INSERT INTO inspecciones (fecha, turno, area, operario, observaciones, puntos, fotos)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("fecha"),
            data.get("turno"),
            data.get("area"),
            data.get("operario"),
            data.get("observaciones"),
            puntos_json,
            fotos_json,
        ),
    )
    conn.commit()
    conn.close()


def total_inspecciones():
    conn = get_db()
    cur = conn.execute("SELECT COUNT(*) AS c FROM inspecciones")
    row = cur.fetchone()
    conn.close()
    return row["c"] if row else 0


def borrar_inspeccion(inspeccion_id):
    conn = get_db()
    conn.execute("DELETE FROM inspecciones WHERE id = ?", (inspeccion_id,))
    conn.commit()
    conn.close()


def json_dumps(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


def json_loads(s):
    import json
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}


def estadisticas():
    conn = get_db()
    filas = conn.execute("SELECT * FROM inspecciones ORDER BY id DESC").fetchall()
    conn.close()

    base = datetime.now().strftime("%Y-%m")
    registros = [dict(r) for r in filas]
    for r in registros:
        r["puntos"] = json_loads(r.get("puntos", ""))
        r["fotos_list"] = json_loads(r.get("fotos", ""))

    mes_actual = [r for r in registros if (r["fecha"] or "")[:7] == base]

    # Total por mes (últimos 6 meses)
    meses = {}
    for r in registros:
        m = (r["fecha"] or "")[:7]
        if m:
            meses[m] = meses.get(m, 0) + 1

    # Conteo por turno
    turnos = {}
    for r in registros:
        t = r["turno"] or "Sin turno"
        turnos[t] = turnos.get(t, 0) + 1

    # Conteo por area
    areas = {}
    for r in registros:
        a = r["area"] or "Sin área"
        areas[a] = areas.get(a, 0) + 1

    return {
        "total": len(registros),
        "mes_actual": mes_actual,
        "total_mes": len(mes_actual),
        "por_mes": dict(sorted(meses.items())),
        "por_turno": turnos,
        "por_area": areas,
        "registros": registros,
    }
