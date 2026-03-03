# app.py (modificado)

import sqlite3
import os
from flask import Flask, render_template, request, jsonify, g
from datetime import datetime

app = Flask(__name__)

# Configuración para producción
if os.environ.get('RENDER'):  # Detecta si está en Render
    # Usa una ruta persistente para la base de datos
    DATABASE = '/tmp/elecciones.db'  # Render permite escritura en /tmp
else:
    DATABASE = 'elecciones.db'  # Local

# Registrar Blueprint de exportación
from export import export_bp
app.register_blueprint(export_bp)

# ──────────────────────────────────────────────
# DATOS INICIALES
# ──────────────────────────────────────────────
SECRETARIAS_INICIALES = [
    ("DESPACHO DEL GOBERNADOR", 192),
    ("SECRETARIA CULTURAL", 264),
    ("SECRETARIA DE ADMINISTRACION Y FINANZAS", 253),
    ("SECRETARIA DE AMBIENTE", 62),
    ("SECRETARIA DE ASUNTOS ESTRATEGICOS Y PROYECTOS ESPECIALES", 8),
    ("SECRETARIA DE BUEN GOBIERNO", 11),
    ("SECRETARIA DE CIENCIA, TECNOLOGIA E INNOVACION", 29),
    ("SECRETARIA DE COMUNICACION E INFORMACION", 67),
    ("SECRETARIA DE DESARROLLO AGROINDUSTRIAL", 8),
    ("SECRETARIA DE DESARROLLO SOCIAL", 48),
    ("SECRETARIA DE ECONOMIA PRODUCTIVA", 16),
    ("SECRETARIA DE EDUCACION", 1540),
    ("SECRETARIA DE JUVENTUD", 22),
    ("SECRETARIA DE MANTENIMIENTO Y SERVICIOS GENERALES", 671),
    ("SECRETARIA DE PLANIFICACION PODER POPULAR COMUNAL", 115),
    ("SECRETARIA DE RELIGION Y CULTO", 17),
    ("SECRETARIA DE SEGURIDAD CIUDADANA", 2130),
    ("SECRETARIA DEL ADULTO MAYOR", 107),
    ("SECRETARIA DEL TALENTO HUMANO", 457),
    ("SECRETARIA DEL TURISMO", 52),
    ("SECRETARIA GENERAL DE GOBIERNO", 378),
    ("SECRETARIA POLITICA", 1178),
    ("SECRETARIA UNICA DEL SISTEMA INTEGRAL DE PROTECCION DE NIÑOS, NIÑAS Y ADOLESCENTES", 29),
]

# ──────────────────────────────────────────────
# BASE DE DATOS
# ──────────────────────────────────────────────
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        # Inicializar la base de datos si no existe
        init_db_if_needed(db)
    return db

def init_db_if_needed(db):
    """Crea las tablas y datos iniciales si no existen"""
    # Verificar si la tabla existe
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='secretarias'"
    )
    if not cursor.fetchone():
        # Crear tablas
        db.executescript("""
            CREATE TABLE secretarias (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                name             TEXT    UNIQUE NOT NULL,
                empleados        INTEGER NOT NULL DEFAULT 0,
                votos_reportados INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE voto_history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                secretaria_id INTEGER NOT NULL,
                timestamp     TEXT    NOT NULL,
                votos_sumados INTEGER NOT NULL,
                FOREIGN KEY (secretaria_id) REFERENCES secretarias(id)
            );
        """)
        # Insertar datos iniciales
        db.executemany(
            "INSERT INTO secretarias (name, empleados) VALUES (?, ?)",
            SECRETARIAS_INICIALES
        )
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ──────────────────────────────────────────────
# RUTAS
# ──────────────────────────────────────────────
@app.route('/')
def index():
    db = get_db()
    secretarias = db.execute("SELECT name FROM secretarias ORDER BY name").fetchall()
    return render_template('index.html', secretarias=[r['name'] for r in secretarias])


@app.route('/secretaria/<name>')
def secretaria(name):
    db = get_db()
    row = db.execute("SELECT * FROM secretarias WHERE name = ?", (name,)).fetchone()
    if not row:
        return "Secretaría no encontrada", 404
    history = db.execute(
        "SELECT * FROM voto_history WHERE secretaria_id = ? ORDER BY timestamp DESC",
        (row['id'],)
    ).fetchall()
    votos_faltantes = row['empleados'] - row['votos_reportados']
    return render_template('secretaria.html',
                           secretaria_name=name,
                           data=dict(row),
                           votos_faltantes=votos_faltantes,
                           voto_history=[dict(h) for h in history])


@app.route('/update_votos/<name>', methods=['POST'])
def update_votos(name):
    db = get_db()
    row = db.execute("SELECT * FROM secretarias WHERE name = ?", (name,)).fetchone()
    if not row:
        return jsonify({"status": "error", "message": "Secretaría no encontrada."}), 404
    try:
        votos_a_sumar = int(request.form['votos'])
        if votos_a_sumar < 0:
            return jsonify({"status": "error", "message": "Los votos no pueden ser negativos."}), 400
        new_total = row['votos_reportados'] + votos_a_sumar
        if new_total > row['empleados']:
            return jsonify({"status": "error", "message": "La cantidad de votos excede el total de empleados."}), 400

        db.execute("UPDATE secretarias SET votos_reportados = ? WHERE id = ?", (new_total, row['id']))
        db.execute(
            "INSERT INTO voto_history (secretaria_id, timestamp, votos_sumados) VALUES (?, ?, ?)",
            (row['id'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), votos_a_sumar)
        )
        db.commit()

        history = db.execute(
            "SELECT * FROM voto_history WHERE secretaria_id = ? ORDER BY timestamp DESC",
            (row['id'],)
        ).fetchall()
        return jsonify({"status": "success", "new_votos": new_total,
                        "voto_history": [dict(h) for h in history]})
    except ValueError:
        return jsonify({"status": "error", "message": "Cantidad de votos inválida."}), 400


@app.route('/delete_voto_entry/<name>/<int:entry_id>', methods=['POST'])
def delete_voto_entry(name, entry_id):
    db = get_db()
    row = db.execute("SELECT * FROM secretarias WHERE name = ?", (name,)).fetchone()
    if not row:
        return jsonify({"status": "error", "message": "Secretaría no encontrada."}), 404
    entry = db.execute(
        "SELECT * FROM voto_history WHERE id = ? AND secretaria_id = ?",
        (entry_id, row['id'])
    ).fetchone()
    if not entry:
        return jsonify({"status": "error", "message": "Entrada no encontrada."}), 404

    db.execute("DELETE FROM voto_history WHERE id = ?", (entry_id,))
    total = db.execute(
        "SELECT COALESCE(SUM(votos_sumados),0) FROM voto_history WHERE secretaria_id = ?",
        (row['id'],)
    ).fetchone()[0]
    db.execute("UPDATE secretarias SET votos_reportados = ? WHERE id = ?", (total, row['id']))
    db.commit()

    history = db.execute(
        "SELECT * FROM voto_history WHERE secretaria_id = ? ORDER BY timestamp DESC",
        (row['id'],)
    ).fetchall()
    return jsonify({"status": "success", "new_votos": total,
                    "voto_history": [dict(h) for h in history]})


@app.route('/grafico_general')
def grafico_general():
    db = get_db()
    row = db.execute(
        "SELECT SUM(empleados) as te, SUM(votos_reportados) as tv FROM secretarias"
    ).fetchone()
    te, tv = row['te'] or 0, row['tv'] or 0
    return render_template('grafico_general.html',
                           total_empleados=te,
                           total_votos_reportados=tv,
                           votos_faltantes=te - tv)


@app.route('/empleados_geb')
def empleados_geb():
    db = get_db()
    rows = db.execute("SELECT * FROM secretarias ORDER BY name").fetchall()
    secretarias_data = {r['name']: dict(r) for r in rows}
    total_general = sum(r['empleados'] for r in rows)
    return render_template('empleados_geb.html',
                           secretarias_data=secretarias_data,
                           total_general=total_general)


@app.route('/update_empleados/<name>', methods=['POST'])
def update_empleados(name):
    db = get_db()
    row = db.execute("SELECT * FROM secretarias WHERE name = ?", (name,)).fetchone()
    if not row:
        return jsonify({"status": "error", "message": "Secretaría no encontrada."}), 404
    try:
        new_emp = int(request.form['empleados'])
        if new_emp < 0:
            return jsonify({"status": "error", "message": "No puede ser negativo."}), 400
        new_votos = min(row['votos_reportados'], new_emp)
        db.execute(
            "UPDATE secretarias SET empleados = ?, votos_reportados = ? WHERE id = ?",
            (new_emp, new_votos, row['id'])
        )
        db.commit()
        total = db.execute("SELECT SUM(empleados) FROM secretarias").fetchone()[0]
        return jsonify({"status": "success", "new_empleados": new_emp,
                        "total_general": total,
                        "message": "Actualizado exitosamente."})
    except ValueError:
        return jsonify({"status": "error", "message": "Valor inválido."}), 400


if __name__ == '__main__':
    app.run(debug=True)
