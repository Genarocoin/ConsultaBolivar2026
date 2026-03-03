# export.py - Reemplaza TODO el contenido con esto

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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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
        
        # Convertir a lista de diccionarios y asegurar tipos de datos
        result = []
        for row in rows:
            result.append({
                'name': str(row['name']),
                'empleados': int(row['empleados']),
                'votos_reportados': int(row['votos_reportados'])
            })
        return result
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
            cell = ws.cell(row=4, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        # Datos
        for idx, row in enumerate(data, 1):
            ws.cell(row=idx+4, column=1, value=idx).alignment = Alignment(horizontal='center')
            ws.cell(row=idx+4, column=2, value=row['name']).alignment = Alignment(horizontal='left', wrap_text=True)
            ws.cell(row=idx+4, column=3, value=row['empleados']).alignment = Alignment(horizontal='center')
            ws.cell(row=idx+4, column=4, value=row['votos_reportados']).alignment = Alignment(horizontal='center')
            faltan = row['empleados'] - row['votos_reportados']
            ws.cell(row=idx+4, column=5, value=faltan).alignment = Alignment(horizontal='center')
            pct = (row['votos_reportados'] / row['empleados'] * 100) if row['empleados'] > 0 else 0
            ws.cell(row=idx+4, column=6, value=f"{pct:.1f}%").alignment = Alignment(horizontal='center')

        # Totales
        last_row = len(data) + 5
        ws.cell(row=last_row, column=2, value="TOTAL GENERAL").font = Font(bold=True)
        ws.cell(row=last_row, column=3, value=total_emp).font = Font(bold=True)
        ws.cell(row=last_row, column=4, value=total_vot).font = Font(bold=True)
        ws.cell(row=last_row, column=5, value=total_falt).font = Font(bold=True)
        ws.cell(row=last_row, column=6, value=f"{(total_vot/total_emp*100):.1f}%" if total_emp else "0%").font = Font(bold=True)

        # Ajustar ancho de columnas
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 50  # Columna ancha para nombres largos
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 12
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 15

        # Ajustar altura de filas para texto envuelto
        for row in range(5, last_row + 1):
            ws.row_dimensions[row].height = 30

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        
        fname = f"participacion_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        return send_file(buf, as_attachment=True, download_name=fname,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        return f"Error generando Excel: {str(e)}", 500

# ════════════════════════════════════════════════════════════
#  PDF (CORREGIDO - CON WRAP DE TEXTO)
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
                                leftMargin=1.5*cm, rightMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        
        styles = getSampleStyleSheet()
        
        # Estilo para texto que hace wrap
        wrap_style = ParagraphStyle(
            'WrapStyle',
            parent=styles['Normal'],
            fontSize=7,
            leading=10,
            alignment=TA_LEFT,
            wordWrap='CJK'  # Esto permite el wrap de texto
        )
        
        center_style = ParagraphStyle(
            'CenterStyle',
            parent=styles['Normal'],
            fontSize=7,
            leading=10,
            alignment=TA_CENTER
        )
        
        bold_center_style = ParagraphStyle(
            'BoldCenterStyle',
            parent=styles['Normal'],
            fontSize=7,
            leading=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            textColor=colors.white
        )

        story = []

        # Título principal
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor(AZUL),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        title = Paragraph("CONSULTA POPULAR NACIONAL 2026", title_style)
        story.append(title)

        # Subtítulo
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor(ROJO),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        subtitle = Paragraph(f"Gobernación del Estado Bolívar - {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                           subtitle_style)
        story.append(subtitle)

        # Preparar datos para la tabla usando Paragraph para wrap de texto
        table_data = []
        
        # Encabezados
        headers = [
            Paragraph('#', header_style),
            Paragraph('SECRETARÍA', header_style),
            Paragraph('EMPLEADOS', header_style),
            Paragraph('VOTARON', header_style),
            Paragraph('FALTAN', header_style),
            Paragraph('%', header_style)
        ]
        table_data.append(headers)
        
        # Datos de cada secretaría
        for idx, row in enumerate(data, 1):
            faltan = row['empleados'] - row['votos_reportados']
            pct = (row['votos_reportados'] / row['empleados'] * 100) if row['empleados'] > 0 else 0
            
            # Usar Paragraph para permitir wrap de texto en nombres largos
            table_data.append([
                Paragraph(str(idx), center_style),
                Paragraph(row['name'], wrap_style),  # Esto hace wrap si es necesario
                Paragraph(str(row['empleados']), center_style),
                Paragraph(str(row['votos_reportados']), center_style),
                Paragraph(str(faltan), center_style),
                Paragraph(f"{pct:.1f}%", center_style)
            ])
        
        # Fila de totales
        table_data.append([
            Paragraph('', center_style),
            Paragraph('<b>TOTAL GENERAL</b>', wrap_style),
            Paragraph(f'<b>{total_emp}</b>', bold_center_style),
            Paragraph(f'<b>{total_vot}</b>', bold_center_style),
            Paragraph(f'<b>{total_falt}</b>', bold_center_style),
            Paragraph(f'<b>{pct_gen:.1f}%</b>', bold_center_style)
        ])

        # Crear tabla con anchos específicos - más ancho para secretarías
        col_widths = [1.2*cm, 9.5*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Estilo de la tabla
        table.setStyle(TableStyle([
            # Encabezados
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(AZUL)),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Todas las celdas
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -2), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -2), 6),
            
            # Bordes
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(AZUL)),
            
            # Filas alternadas
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F4F6FB')]),
            
            # Fila de totales
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(AMARILLO)),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor(AZUL)),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, -1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
        ]))

        story.append(table)
        
        # Pie de página
        story.append(Spacer(1, 0.5*cm))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        footer = Paragraph("Consulta Popular Nacional 2026 · Gobernación del Estado Bolívar · Documento generado automáticamente", footer_style)
        story.append(footer)

        # Construir PDF
        doc.build(story)
        buf.seek(0)
        
        fname = f"participacion_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        return send_file(buf, as_attachment=True, download_name=fname,
                        mimetype='application/pdf')
                        
    except Exception as e:
        import traceback
        error_msg = f"Error generando PDF: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return f"Error generando PDF: {str(e)}", 500
