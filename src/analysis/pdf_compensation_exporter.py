"""
Exportador de análisis de compensación a PDF - Diseño profesional y visual.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Frame, PageTemplate
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from datetime import datetime
from io import BytesIO
from src.utils.formatters import format_peso_chileno
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


class CompensationPDFExporter:
    """Exporta análisis de compensación a PDF con diseño visual profesional."""

    # Colores de la marca
    COLOR_PRIMARY = colors.HexColor('#1F4E78')
    COLOR_SUCCESS = colors.HexColor('#28A745')
    COLOR_WARNING = colors.HexColor('#FFC107')
    COLOR_DANGER = colors.HexColor('#DC3545')
    COLOR_INFO = colors.HexColor('#17A2B8')
    COLOR_LIGHT = colors.HexColor('#F8F9FA')
    COLOR_DARK = colors.HexColor('#343A40')

    def __init__(self, employee_data, compensation_data, internal_comp_data=None):
        """
        Inicializa el exportador.

        Args:
            employee_data: Dict con datos del empleado
            compensation_data: Dict con cálculos de compensación
            internal_comp_data: Dict con datos de competitividad interna (opcional)
        """
        self.employee = employee_data
        self.comp = compensation_data
        self.internal = internal_comp_data or {}

    def generate_pdf(self):
        """
        Genera el PDF visual y retorna BytesIO.

        Returns:
            BytesIO con el PDF generado
        """
        pdf_buffer = BytesIO()

        # Crear documento
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=0.4 * inch,
            leftMargin=0.4 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.4 * inch
        )

        # Estilos personalizados
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=6,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT
        )

        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            fontName='Helvetica'
        )

        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.whitesmoke,
            spaceAfter=10,
            fontName='Helvetica-Bold',
            leftIndent=8
        )

        metric_label = ParagraphStyle(
            'MetricLabel',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#999999'),
            fontName='Helvetica'
        )

        metric_value = ParagraphStyle(
            'MetricValue',
            parent=styles['Normal'],
            fontSize=11,
            textColor=self.COLOR_PRIMARY,
            fontName='Helvetica-Bold'
        )

        normal_style = styles['Normal']
        normal_style.fontSize = 8

        # Contenido del documento
        content = []

        # 1. Encabezado profesional
        content.append(Paragraph("💰 ANÁLISIS DE COMPENSACIÓN", title_style))
        content.append(Paragraph(f"Generado el {datetime.now().strftime('%d de %B de %Y')} | Suite ARP IA", subtitle_style))
        content.append(Spacer(1, 0.1 * inch))

        # 2. Tarjeta de datos del empleado
        content.append(Paragraph("INFORMACIÓN DEL EMPLEADO", section_style))

        employee_data = [
            ["Nombre", self.employee.get('nombre', ''), "Área", self.employee.get('area', '-')],
            ["RUT", self.employee.get('rut', ''), "Cargo", self.employee.get('cargo_actual', '-')],
            ["Nivel HAY", str(self.employee.get('nivel_hay', '-')), "Target", f"{self.employee.get('target', 1.0)} Rentas"],
        ]

        emp_table = Table(employee_data, colWidths=[1.3*inch, 1.5*inch, 1.3*inch, 1.8*inch])
        emp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
        ]))

        content.append(emp_table)
        content.append(Spacer(1, 0.25 * inch))

        # 3. Desglose de Compensación
        content.append(Paragraph("DESGLOSE DE COMPENSACIÓN", section_style))

        comp_data = [
            ["Componente", "Mensual", "Anual"],
            ["Sueldo Base", format_peso_chileno(self.comp.get('sueldo_base', 0)), format_peso_chileno(self.comp.get('sueldo_anual', 0))],
            ["Gratificación", format_peso_chileno(self.comp.get('gratificacion', 0)), format_peso_chileno(self.comp.get('gratificacion_anual', 0))],
            ["Colación", format_peso_chileno(self.comp.get('colacion', 0)), format_peso_chileno(self.comp.get('colacion_anual', 0))],
            ["Movilización", format_peso_chileno(self.comp.get('movilizacion', 0)), format_peso_chileno(self.comp.get('movilizacion_anual', 0))],
            ["Target", format_peso_chileno(self.comp.get('target', 0) / 12), format_peso_chileno(self.comp.get('target', 0))],
            ["TOTAL COMPENSACIÓN", format_peso_chileno(sum([
                self.comp.get('sueldo_base', 0),
                self.comp.get('gratificacion', 0),
                self.comp.get('colacion', 0),
                self.comp.get('movilizacion', 0),
                self.comp.get('target', 0) / 12
            ])), format_peso_chileno(self.comp.get('total', 0))],
        ]

        comp_table = Table(comp_data, colWidths=[2.2*inch, 1.9*inch, 1.9*inch])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#D4EDDA')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, -1), (-1, -1), self.COLOR_SUCCESS),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F8F9FA')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        content.append(comp_table)
        content.append(Spacer(1, 0.25 * inch))

        # 4. Análisis de Mercado
        content.append(Paragraph("ANÁLISIS DE POSICIÓN EN MERCADO", section_style))

        market_data = [
            ["Métrica", "Valor"],
            ["Compensación Total Anual", format_peso_chileno(self.comp.get('total', 0))],
            ["P50 Nivel (Referencia)", format_peso_chileno(self.comp.get('valor_nivel', 0))],
            ["P25 (Mínimo)", format_peso_chileno(self.comp.get('p25', 0))],
            ["P75 (Máximo)", format_peso_chileno(self.comp.get('p75', 0))],
            ["Compa Ratio", f"{self.comp.get('compa_ratio', 0):.1f}%"],
            ["Salary Spread", f"{self.comp.get('salary_spread', 0):.1f}%"],
            ["Posición en Banda", f"{self.comp.get('posicion_pct', 0):.1f}% del P50"],
            ["Estado", self.comp.get('estado', '')],
            ["Banda", self.comp.get('banda', '')],
        ]

        market_table = Table(market_data, colWidths=[2.5*inch, 3.5*inch])
        market_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_INFO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))

        content.append(market_table)
        content.append(Spacer(1, 0.25 * inch))

        # 5. Recomendación
        rec_data = [
            ["PRIORIDAD", self.comp.get('prioridad', '').upper()],
            ["ACCIÓN", self.comp.get('recomendacion', '')],
        ]

        rec_table = Table(rec_data, colWidths=[2*inch, 4*inch])

        # Determinar color según prioridad
        rec_color = self.COLOR_SUCCESS
        if "ALTA" in self.comp.get('prioridad', '').upper():
            rec_color = self.COLOR_DANGER
        elif "MEDIA" in self.comp.get('prioridad', '').upper():
            rec_color = self.COLOR_WARNING

        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), rec_color),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, -1), 9),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#F8F9FA')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('FONTSIZE', (1, 0), (1, -1), 9),
        ]))

        content.append(rec_table)
        content.append(Spacer(1, 0.3 * inch))

        # 6. Pie de página
        footer_style = ParagraphStyle(
            'Footer',
            parent=normal_style,
            fontSize=7,
            textColor=colors.HexColor('#999999'),
            alignment=TA_CENTER
        )
        content.append(Paragraph(
            f"Documento generado el {datetime.now().strftime('%d de %B de %Y a las %H:%M')} | Suite ARP IA - Análisis de Compensación",
            footer_style
        ))

        # Construir PDF
        doc.build(content)
        pdf_buffer.seek(0)
        return pdf_buffer
