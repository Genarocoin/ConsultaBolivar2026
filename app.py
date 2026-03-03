# app.py
import sqlite3
import os
from flask import Flask, render_template, request, jsonify, g
from datetime import datetime

app = Flask(__name__)

# Configuración de base de datos
if os.environ.get('RENDER'):
    DATABASE = '/tmp/elecciones.db'  # Render permite escritura en /tmp
else:
    DATABASE = 'elecciones.db'

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
# FUNCIÓN DE INICIALIZACIÓN (se ejecuta al arrancar)
# ──────────────────────────────────────────────
def init_database():
    """Inicializa la base de datos al arrancar la aplicación"""
    print(f"Inicializando base de datos en: {DATABASE}")
    
    # Conectar y crear tablas
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Verificar si la tabla existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='secretarias'")
    if not cursor.fetchone():
        print("Tablas no encontradas. Creando base de datos...")
        
        # Crear tablas
        cursor.executescript("""
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
        cursor.executemany(
            "INSERT INTO secretarias (name, empleados) VALUES (?, ?)",
            SECRETARIAS_INICIALES
        )
        conn.commit()
        print(f"Base de datos creada con {len(SECRETARIAS_INICIALES)} secretarías")
    else:
        print("Base de datos ya existente. Verificando integridad...")
        # Verificar que hay datos
        count = cursor.execute("SELECT COUNT(*) FROM secretarias").fetchone()[0]
        print(f"Secretarías encontradas: {count}")
    
    conn.close()
    return True

# Ejecutar inicialización AL ARRANCAR LA APLICACIÓN
init_database()

# ──────────────────────────────────────────────
# BASE DE DATOS (para requests)
# ──────────────────────────────────────────────
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ──────────────────────────────────────────────
# RUTAS (igual que antes)
# ──────────────────────────────────────────────
@app.route('/')
def index():
    db = get_db()
    secretarias = db.execute("SELECT name FROM secretarias ORDER BY name").fetchall()
    return render_template('index.html', secretarias=[r['name'] for r in secretarias])

# ... (todas las demás rutas igual que antes, sin cambios) ...
