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

# Usar la misma configuración de DB que app.py
if os.environ.get('RENDER'):
    DATABASE = '/tmp/elecciones.db'
else:
    DATABASE = 'elecciones.db'

# ── Paleta ───────────────────────────────────────────────────
ROJO     = '#D7263D'
AZUL     = '#1B4F9B'
AMARILLO = '#F5A623'

# ... (resto del código de export.py igual) ...
