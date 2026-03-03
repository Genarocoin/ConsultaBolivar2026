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
    try:
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT name, empleados, votos_reportados FROM secretarias ORDER BY name"
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

# ════════════════════════════════════════════════════════════
#  EXCEL
# ════════════════════════════════════════════════════════════
@export_bp.route('/export/excel')
def export_excel():
    try:
        data = _fetch_data()
        
        if not data:
            return "No hay datos para exportar", 404
            
        total_emp = sum(r['empleados'] for r in data)
        total_vot = sum(r['votos_reportados'] for r in data)
        total_falt = total_emp - total_vot

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Resumen General"

        # Título
        ws['A1'] = "CONSULTA POPULAR NACIONAL 2026"
        ws['A1'].font = Font(bold=True, size=16, color="FFFFFF")
        ws['A1'].fill = PatternFill("solid", fgColor=AZUL[1:])
        ws.merge_cells('A1:G1')

        # Subtítulo
        ws['A2'] = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ws.merge_cells('A2:G2')

        # Encabezados
        headers = ['#', 'SECRETARÍA', 'EMPLEADOS', 'YA VOTARON', 'FALTAN', '% PARTICIPACIÓN']
        for col, header in enumerate(headers, 1):
            ws.cell(row=4, column=col, value=header)
            ws.cell(row=4, column=col).font = Font(bold=True)

        # Datos
        for idx, row in enumerate(data, 1):
            ws.cell(row=idx+4, column=1, value=idx)
            ws.cell(row=idx+4, column=2, value=row['name'])
            ws.cell(row=idx+4, column=3, value=row['empleados'])
            ws.cell(row=idx+4, column=4, value=row['votos_reportados'])
            faltan = row['empleados'] - row['votos_reportados']
            ws.cell(row=idx+4, column=5, value=faltan)
            pct = (row['votos_reportados'] / row['empleados'] * 100) if row['empleados'] > 0 else 0
            ws.cell(row=idx+4, column=6, value=f"{pct:.1f}%")

        # Totales
        last_row = len(data) + 5
        ws.cell(row=last_row, column=2, value="TOTAL GENERAL")
        ws.cell(row=last_row, column=2).font = Font(bold=True)
        ws.cell(row=last_row, column=3, value=total_emp)
        ws.cell(row=last_row, column=4, value=total_vot)
        ws.cell(row=last_row, column=5, value=total_falt)
        ws.cell(row=last_row, column=6, value=f"{(total_vot/total_emp*100):.1f}%" if total_emp else "0%")

        # Ajustar ancho de columnas
        for col in range(1, 7):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        
        fname = f"participacion_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        return send_file(buf, as_attachment=True, download_name=fname,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        return f"Error generando Excel: {str(e)}", 500

# ════════════════════════════════════════════════════════════
#  PDF
# ════════════════════════════════════════════════════════════
@export_bp.route('/export/pdf')
def export_pdf():
    try:
        data = _fetch_data()
        
        if not data:
            return "No hay datos para exportar", 404
            
        total_emp = sum(r['empleados'] for r in data)
        total_vot = sum(r['votos_reportados'] for r in data)
        total_falt = total_emp - total_vot
        pct_gen = (total_vot / total_emp * 100) if total_emp > 0 else 0

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        
        styles = getSampleStyleSheet()
        story = []

        # Título
        title = Paragraph("CONSULTA POPULAR NACIONAL 2026", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 0.5*cm))

        # Subtítulo
        subtitle = Paragraph(f"Gobernación del Estado Bolívar - {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                           styles['Normal'])
        story.append(subtitle)
        story.append(Spacer(1, 0.5*cm))

        # Tabla de datos
        table_data = [['#', 'Secretaría', 'Empleados', 'Votaron', 'Faltan', '%']]
        
        for idx, row in enumerate(data, 1):
            faltan = row['empleados'] - row['votos_reportados']
            pct = (row['votos_reportados'] / row['empleados'] * 100) if row['empleados'] > 0 else 0
            table_data.append([
                str(idx),
                row['name'],
                str(row['empleados']),
                str(row['votos_reportados']),
                str(faltan),
                f"{pct:.1f}%"
            ])
        
        # Fila de totales
        table_data.append(['', 'TOTAL GENERAL', str(total_emp), str(total_vot), 
                          str(total_falt), f"{pct_gen:.1f}%"])

        # Crear tabla
        table = Table(table_data, colWidths=[2*cm, 7*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(AZUL)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(AMARILLO)),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        story.append(table)

        doc.build(story)
        buf.seek(0)
        
        fname = f"participacion_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        return send_file(buf, as_attachment=True, download_name=fname,
                        mimetype='application/pdf')
    except Exception as e:
        return f"Error generando PDF: {str(e)}", 500
