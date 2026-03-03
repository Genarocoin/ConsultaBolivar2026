# export.py
import io
import os
from datetime import datetime
from flask import Blueprint, send_file
import sqlite3

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import DoughnutChart, Reference

export_bp = Blueprint('export', __name__)

# Configuración de base de datos para Render
if os.environ.get('RENDER'):
    DATABASE = '/tmp/elecciones.db'
else:
    DATABASE = 'elecciones.db'

# ── Paleta ───────────────────────────────────────────────────
ROJO     = '#D7263D'
AZUL     = '#1B4F9B'
AMARILLO = '#F5A623'

RL_AZUL     = colors.HexColor(AZUL)
RL_ROJO     = colors.HexColor(ROJO)
RL_AMARILLO = colors.HexColor(AMARILLO)
RL_GRIS     = colors.HexColor('#F4F6FB')
RL_BLANCO   = colors.white

def _fetch_data():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT name, empleados, votos_reportados FROM secretarias ORDER BY name"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

# ... (el resto del código de export.py sigue igual) ...
