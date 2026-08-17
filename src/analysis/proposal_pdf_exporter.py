"""
Exportador de simulaciones de propuestas a PDF.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from io import BytesIO
from src.utils.formatters import format_peso_chileno


class ProposalPDFExporter:
    """Exporta simulaciones de propuestas a PDF profesional."""

    COLOR_PRIMARY = colors.HexColor('#1F4E78')
    COLOR_SUCCESS = colors.HexColor('#28A745')
    COLOR_DANGER = colors.HexColor('#DC3545')

    def __init__(self, employee_data, actual_comp, proposal_comp):
        """
        Inicializa el exportador.

        Args:
            employee_data: Dict con datos del empleado
            actual_comp: Dict con compensación actual anualizada
            proposal_comp: Dict con compensación propuesta anualizada
        """
        self.employee = employee_data
        self.actual = actual_comp
        self.proposal = proposal_comp

    def generate_pdf(self):
        """
        Genera el PDF y retorna BytesIO.

        Returns:
            BytesIO con el PDF generado
        """
        pdf_buffer = BytesIO()

        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=0.4 * inch,
            leftMargin=0.4 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.4 * inch
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=6,
            fontName='Helvetica-Bold'
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

        content = []

        # 1. Encabezado
        content.append(Paragraph("📊 PROPUESTA DE INCREMENTO DE RENTA", title_style))
        content.append(Paragraph(f"Generado el {datetime.now().strftime('%d de %B de %Y')}", subtitle_style))
        content.append(Spacer(1, 0.1 * inch))

        # 2. Datos del empleado
        content.append(Paragraph("INFORMACIÓN DEL EMPLEADO", section_style))

        emp_data = [
            ["Nombre", self.employee.get('nombre', ''), "Empresa", self.employee.get('empresa', '-')],
            ["RUT", self.employee.get('rut', ''), "Cargo", self.employee.get('cargo_actual', '-')],
            ["Nivel HAY", str(self.employee.get('nivel_hay', '-')), "Área", self.employee.get('area', '-')],
        ]

        emp_table = Table(emp_data, colWidths=[1.3*inch, 1.5*inch, 1.3*inch, 1.8*inch])
        emp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ]))

        content.append(emp_table)
        content.append(Spacer(1, 0.25 * inch))

        # 3. Comparativa Actual vs Propuesto
        content.append(Paragraph("COMPARATIVA: ACTUAL VS PROPUESTO (ANUALIZADO)", section_style))

        comp_data = [
            ["Métrica", "Actual", "Propuesto", "Cambio"],
            ["Total Cash Anual", format_peso_chileno(self.actual.get('total_cash', 0)), format_peso_chileno(self.proposal.get('total_cash', 0)), format_peso_chileno(self.proposal.get('total_cash', 0) - self.actual.get('total_cash', 0))],
            ["Compa Ratio", f"{self.actual.get('compa_ratio', 0):.1f}%", f"{self.proposal.get('compa_ratio', 0):.1f}%", f"{self.proposal.get('compa_ratio', 0) - self.actual.get('compa_ratio', 0):+.1f}%"],
            ["Posición en Banda", f"{self.actual.get('banda_pct', 0):.1f}%", f"{self.proposal.get('banda_pct', 0):.1f}%", f"{self.proposal.get('banda_pct', 0) - self.actual.get('banda_pct', 0):+.1f}%"],
            ["Estado", self.actual.get('estado', ''), self.proposal.get('estado', ''), "✓" if self.proposal.get('estado') != self.actual.get('estado') else "-"],
        ]

        comp_table = Table(comp_data, colWidths=[2.2*inch, 1.9*inch, 1.9*inch, 1.9*inch])
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
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))

        content.append(comp_table)
        content.append(Spacer(1, 0.25 * inch))

        # 4. Impacto Presupuestario
        content.append(Paragraph("IMPACTO PRESUPUESTARIO", section_style))

        impacto_data = [
            ["Concepto", "Valor"],
            ["Incremento Mensual Propuesto", format_peso_chileno(self.proposal.get('incremento_mensual', 0))],
            ["Incremento Anual", format_peso_chileno(self.proposal.get('incremento_anual', 0))],
            ["% de Incremento", f"{self.proposal.get('incremento_pct', 0):.1f}%"],
        ]

        impacto_table = Table(impacto_data, colWidths=[3.5*inch, 2.5*inch])
        impacto_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
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

        content.append(impacto_table)
        content.append(Spacer(1, 0.3 * inch))

        # 5. Pie de página
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#999999'),
            alignment=TA_CENTER
        )
        content.append(Paragraph(
            f"Documento generado el {datetime.now().strftime('%d de %B de %Y a las %H:%M')} | Suite ARP IA - Simulador de Propuestas",
            footer_style
        ))

        doc.build(content)
        pdf_buffer.seek(0)
        return pdf_buffer
