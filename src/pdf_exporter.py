"""Generador de reportes PDF con formato ejecutivo."""

from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from .simulator import ComparisonResult
import logging
import io
import base64
from typing import List, Dict, Optional, Tuple
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import numpy as np

logger = logging.getLogger(__name__)


class PDFExporter:
    """Exporta comparativas de Propuestas de Renta a PDF."""

    def __init__(self):
        """Inicializa exportador PDF."""
        self.styles = getSampleStyleSheet()

    def export_comparison(
        self,
        comparison: ComparisonResult,
        output_filename: str,
        company_name: str = "Empresa",
        prepared_by: str = "RRHH",
        standard_proposals=None,
        current_company: str = "",
        current_position: str = "",
        current_supervisor: str = "",
        proposal_company: str = "",
        proposal_position: str = "",
        proposal_supervisor: str = "",
        logo_path: str = None,
        salary_history: list = None,
        proposal_reasons: list = None,
        compensation_data: dict = None,
        beneficios_data: dict = None,
    ) -> bool:
        """
        Exporta comparativa a archivo PDF en formato Excel-like.

        Args:
            comparison: ComparisonResult con datos a exportar
            output_filename: Ruta del archivo PDF
            company_name: Nombre de la empresa
            prepared_by: Persona que prepara el documento
            standard_proposals: Ignorado (solo propuesta específica)
            current_company: Empresa actual (Buk)
            current_position: Cargo actual (Buk)
            current_supervisor: Jefe actual (Buk)
            proposal_company: Empresa propuesta
            proposal_position: Cargo propuesto
            proposal_supervisor: Jefe propuesto

        Returns:
            True si es exitoso, False en caso contrario
        """
        try:
            doc = SimpleDocTemplate(
                output_filename,
                pagesize=letter,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.5 * inch,
                bottomMargin=0.5 * inch,
            )

            story = []

            # Agregar logo si existe (arriba, alineado a la derecha)
            if logo_path:
                try:
                    import os
                    if os.path.exists(logo_path):
                        logo_image = Image(logo_path, width=0.8*inch, height=0.8*inch)
                        logo_table = Table([[logo_image]], colWidths=[6*inch])
                        logo_table.setStyle(TableStyle([
                            ("ALIGN", (0, 0), (0, 0), "RIGHT"),
                        ]))
                        story.append(logo_table)
                        story.append(Spacer(1, 0.1 * inch))
                except Exception as e:
                    logger.warning(f"No se pudo cargar el logo: {e}")

            # Título centrado en una sola línea - Color azul
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=self.styles['Normal'],
                fontSize=16,
                textColor=colors.HexColor("#1F4E78"),
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=12,
            )
            story.append(Paragraph("PROPUESTA DE RENTA", title_style))
            story.append(Spacer(1, 0.2 * inch))

            # Encabezado con datos del empleado
            header_data = [
                ["Nombre", comparison.employee_name, "F. Ingreso", "01-09-2022"],
                ["Rut", comparison.employee_rut, "Tipo Cto.", "Indefinido"],
            ]
            header_table = Table(header_data, colWidths=[1 * inch, 2.5 * inch, 1 * inch, 1.5 * inch])
            header_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8E8E8")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E8E8E8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 0.15 * inch))

            # Sección de Comentarios
            comment_style = ParagraphStyle(
                'CommentHeader',
                parent=self.styles['Normal'],
                fontSize=10,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor("#1F4E78"),
                alignment=TA_CENTER,
                spaceAfter=6,
            )
            story.append(Paragraph("Comentarios", comment_style))

            # Preparar datos de comentarios y motivos
            motivos_text = ", ".join(proposal_reasons) if proposal_reasons else ""
            comment_data = [
                ["Motivos", motivos_text]
            ]

            comment_table = Table(comment_data, colWidths=[1 * inch, 5 * inch])
            comment_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#D9E1F2")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(comment_table)
            story.append(Spacer(1, 0.15 * inch))

            # Fecha de Aplicación
            date_header_style = ParagraphStyle(
                'DateHeader',
                parent=self.styles['Normal'],
                fontSize=10,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor("#1F4E78"),
                alignment=TA_CENTER,
                spaceAfter=6,
            )
            story.append(Paragraph("Fecha de Aplicación", date_header_style))
            date_data = [[comparison.change_date]]
            date_table = Table(date_data, colWidths=[6 * inch])
            date_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#D9E1F2")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(date_table)
            story.append(Spacer(1, 0.15 * inch))

            # Información de Empresa, Cargo, Jefe
            info_data = [
                ["Item", "Actual", "Propuesta"],
                ["Empresa", current_company or "N/A", proposal_company or current_company or "N/A"],
                ["Descripcion Cargo", current_position or "N/A", proposal_position or current_position or "N/A"],
                ["Nombre Jefe", current_supervisor or "N/A", proposal_supervisor or current_supervisor or "N/A"],
            ]
            info_table = Table(info_data, colWidths=[1.5 * inch, 2.25 * inch, 2.25 * inch])
            info_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.15 * inch))

            # Tabla COMPARATIVO
            comp_header = ParagraphStyle(
                'CompHeader',
                parent=self.styles['Normal'],
                fontSize=10,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor("#1F4E78"),
                alignment=TA_CENTER,
            )
            story.append(Paragraph("COMPARATIVO", comp_header))

            # Datos de haberes
            comp_data = [
                ["Haberes", "Renta Actual", "Renta Nueva", "Variación", "Variación %"],
                ["Sueldo Base", f"${comparison.current.base_salary:,.0f}",
                 f"${comparison.proposal.base_salary:,.0f}",
                 f"${comparison.proposal.base_salary - comparison.current.base_salary:,.0f}",
                 f"{self._calc_percent(comparison.current.base_salary, comparison.proposal.base_salary):.1f}%"],
                ["Gratificación", f"${comparison.current.gratification:,.0f}",
                 f"${comparison.proposal.gratification:,.0f}",
                 f"${comparison.proposal.gratification - comparison.current.gratification:,.0f}",
                 f"{self._calc_percent(comparison.current.gratification, comparison.proposal.gratification):.1f}%"],
                ["Colación", f"${comparison.current.collation:,.0f}",
                 f"${comparison.proposal.collation:,.0f}",
                 f"${comparison.proposal.collation - comparison.current.collation:,.0f}",
                 f"{self._calc_percent(comparison.current.collation, comparison.proposal.collation):.1f}%"],
                ["Movilización", f"${comparison.current.mobility:,.0f}",
                 f"${comparison.proposal.mobility:,.0f}",
                 f"${comparison.proposal.mobility - comparison.current.mobility:,.0f}",
                 f"{self._calc_percent(comparison.current.mobility, comparison.proposal.mobility):.1f}%"],
                ["Total haberes", f"${comparison.current.total_earnings:,.0f}",
                 f"${comparison.proposal.total_earnings:,.0f}",
                 f"${comparison.proposal.total_earnings - comparison.current.total_earnings:,.0f}",
                 f"{self._calc_percent(comparison.current.total_earnings, comparison.proposal.total_earnings):.1f}%"],
            ]

            comp_table = Table(comp_data, colWidths=[1.2 * inch, 1 * inch, 1 * inch, 1 * inch, 0.8 * inch])
            comp_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(comp_table)
            story.append(Spacer(1, 0.1 * inch))

            # Sueldo líquido (neto después de otros descuentos como estacionamiento)
            current_net_after_other = comparison.current.net_salary - comparison.current_parking_discount
            proposal_net_after_other = comparison.proposal.net_salary - comparison.proposal_parking_discount
            liquid_data = [
                ["Sueldo liquido App", f"${current_net_after_other:,.0f}",
                 f"${proposal_net_after_other:,.0f}",
                 f"${proposal_net_after_other - current_net_after_other:,.0f}",
                 f"{self._calc_percent(current_net_after_other, proposal_net_after_other):.1f}%"],
            ]

            liquid_table = Table(liquid_data, colWidths=[1.2 * inch, 1 * inch, 1 * inch, 1 * inch, 0.8 * inch])
            liquid_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(liquid_table)

            # Agregar tabla de Compensación Anual si se proporciona compensation_data
            if compensation_data:
                story.append(Spacer(1, 0.3 * inch))

                # Título de Compensación Anual - Centrado
                comp_title = ParagraphStyle(
                    'CompTitle',
                    parent=self.styles['Normal'],
                    fontSize=11,
                    textColor=colors.HexColor("#1F4E78"),
                    fontName='Helvetica-Bold',
                    spaceAfter=10,
                    alignment=TA_CENTER,
                )
                story.append(Paragraph("ANÁLISIS DE COMPENSACIÓN ANUAL", comp_title))

                # Tabla de Compensación
                comp_table_data = [
                    ["Concepto", "Renta Actual", "Renta Nueva"],
                    ["Bono Target",
                     f"{compensation_data.get('bono_actual', 0):,.0f}",
                     f"{compensation_data.get('bono_propuesto', 0):,.0f}"],
                    ["Mercado",
                     compensation_data.get('mercado_actual', '—'),
                     compensation_data.get('mercado_propuesto', '—')],
                    ["Nivel HAY",
                     compensation_data.get('nivel_hay_actual', '—'),
                     compensation_data.get('nivel_hay_propuesto', '—')],
                    ["Posición Media Nivel",
                     f"{compensation_data.get('posicion_media_actual', 0):.1f}%",
                     f"{compensation_data.get('posicion_media_propuesto', 0):.1f}%"],
                    ["Mediana",
                     f"{compensation_data.get('mediana_actual', 0):,.0f}",
                     f"{compensation_data.get('mediana_propuesto', 0):,.0f}"],
                    ["% Variable Target",
                     f"{compensation_data.get('pct_variable_actual', 0):.1f}%",
                     f"{compensation_data.get('pct_variable_propuesto', 0):.1f}%"],
                    ["Compensación Anual",
                     f"{compensation_data.get('comp_anual_actual', 0):,.0f}",
                     f"{compensation_data.get('comp_anual_propuesto', 0):,.0f}"],
                ]

                comp_table = Table(comp_table_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch])
                comp_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#E8F0F8")),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ]))
                story.append(comp_table)

            # Agregar tabla de Beneficios Adicionales si se proporciona beneficios_data
            if beneficios_data:
                story.append(Spacer(1, 0.3 * inch))

                ben_title = ParagraphStyle(
                    'BenTitle',
                    parent=self.styles['Normal'],
                    fontSize=11,
                    textColor=colors.HexColor("#1F4E78"),
                    fontName='Helvetica-Bold',
                    spaceAfter=10,
                    alignment=TA_CENTER,
                )
                story.append(Paragraph("BENEFICIOS ADICIONALES (COSTO EMPRESA, ANUAL)", ben_title))

                ben_table_data = [
                    ["Beneficio", "Actual", "Propuesta"],
                    ["Aguinaldo de Navidad",
                     f"{beneficios_data.get('aguinaldo_navidad_monto', 0):,.0f}",
                     f"{beneficios_data.get('aguinaldo_navidad_monto', 0):,.0f}"],
                    ["Aguinaldo Fiestas Patrias",
                     f"{beneficios_data.get('aguinaldo_fiestas_patrias_monto', 0):,.0f}",
                     f"{beneficios_data.get('aguinaldo_fiestas_patrias_monto', 0):,.0f}"],
                    ["Gift Card",
                     f"{beneficios_data.get('gift_card_monto', 0):,.0f}",
                     f"{beneficios_data.get('gift_card_monto', 0):,.0f}"],
                    ["Bono Vacaciones",
                     f"{beneficios_data.get('bono_vacaciones_actual_monto', 0):,.0f}",
                     f"{beneficios_data.get('bono_vacaciones_propuesta_monto', 0):,.0f}"],
                    ["Total Beneficios Anuales",
                     f"{beneficios_data.get('total_anual_actual', 0):,.0f}",
                     f"{beneficios_data.get('total_anual_propuesta', 0):,.0f}"],
                ]

                ben_table = Table(ben_table_data, colWidths=[2.3 * inch, 1.35 * inch, 1.35 * inch])
                ben_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 1), (-1, -2), colors.HexColor("#E8F0F8")),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#D4E4F0")),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ]))
                story.append(ben_table)

            # Agregar historial de sueldos si se proporciona
            if salary_history:
                from reportlab.platypus import PageBreak
                story.append(PageBreak())
                self._add_salary_history_to_pdf(story, salary_history)

            # Generar PDF
            doc.build(story)
            logger.info(f"Archivo PDF generado: {output_filename}")
            return True

        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _calc_percent(self, current: float, proposed: float) -> float:
        """Calcula porcentaje de cambio."""
        if current == 0:
            return 0
        return ((proposed - current) / current) * 100

    def export_calculator(
        self,
        calculation,
        output_filename: str,
        periodo: str = "",
        logo_path: str = None,
    ) -> bool:
        """
        Exporta resultado de calculadora a PDF con layout de 2 columnas.

        Args:
            calculation: PayrollCalculation object
            output_filename: Ruta del archivo PDF
            periodo: Período a mostrar
            logo_path: Ruta del logo (opcional)

        Returns:
            True si es exitoso, False en caso contrario
        """
        try:
            doc = SimpleDocTemplate(
                output_filename,
                pagesize=letter,
                rightMargin=0.4 * inch,
                leftMargin=0.4 * inch,
                topMargin=0.4 * inch,
                bottomMargin=0.4 * inch,
            )

            story = []

            # Logo + Título en una tabla
            header_elements = []

            # Logo si existe
            logo_element = None
            if logo_path:
                try:
                    import os
                    if os.path.exists(logo_path):
                        logo_element = Image(logo_path, width=0.6*inch, height=0.6*inch)
                except Exception as e:
                    logger.warning(f"No se pudo agregar logo: {e}")

            # Crear tabla con logo a la derecha y título centrado
            if logo_element:
                header_table = Table(
                    [[None, Paragraph("LIQUIDACIÓN DE SUELDO", ParagraphStyle(
                        "Title",
                        parent=self.styles["Heading1"],
                        fontSize=14,
                        textColor=colors.HexColor("#1F4E78"),
                        fontName="Helvetica-Bold",
                        alignment=TA_CENTER
                    )), logo_element]],
                    colWidths=[1.2*inch, 3.2*inch, 0.8*inch]
                )
                header_table.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                ]))
                story.append(header_table)
            else:
                title_style = ParagraphStyle(
                    "Title",
                    parent=self.styles["Heading1"],
                    fontSize=14,
                    textColor=colors.HexColor("#1F4E78"),
                    fontName="Helvetica-Bold",
                    alignment=TA_CENTER,
                    spaceAfter=0,
                )
                title = Paragraph("LIQUIDACIÓN DE SUELDO", title_style)
                story.append(title)

            # Fecha
            if periodo:
                date_style = ParagraphStyle(
                    "Date",
                    parent=self.styles["Normal"],
                    fontSize=8,
                    alignment=TA_CENTER,
                    spaceAfter=8,
                )
                story.append(Paragraph(f"Fecha: {periodo}", date_style))

            story.append(Spacer(1, 0.1 * inch))

            # ===== TABLA DE 2 COLUMNAS =====
            # Columna izquierda: HABERES IMPONIBLES
            haberes_data = [
                ["HABERES IMPONIBLES", ""],
                ["Sueldo Base", f"${calculation.base_salary:,.0f}"],
                ["Gratificación", f"${calculation.gratification:,.0f}"],
            ]

            if calculation.collation > 0:
                haberes_data.append(["Colación", f"${calculation.collation:,.0f}"])
            if calculation.mobility > 0:
                haberes_data.append(["Movilización", f"${calculation.mobility:,.0f}"])
            if calculation.other_taxable > 0:
                haberes_data.append(["Otros Imponibles", f"${calculation.other_taxable:,.0f}"])

            haberes_data.append(["Total Imponible", f"${calculation.total_taxable:,.0f}"])

            # Columna derecha: ESCUENTOS LEGALES
            descuentos_data = [
                ["ESCUENTOS LEGALES", ""],
                ["AFP", f"${calculation.afp_discount:,.0f}"],
                ["Salud", f"${calculation.health_discount:,.0f}"],
                ["AFC", f"${calculation.afc_discount:,.0f}"],
                ["Impuesto Renta", f"${calculation.income_tax:,.0f}"],
                ["", ""],
                ["Total Descuentos", f"${calculation.total_discounts:,.0f}"],
            ]

            # Tabla principal de 2 columnas
            main_data = []
            max_rows = max(len(haberes_data), len(descuentos_data))

            for i in range(max_rows):
                left = haberes_data[i] if i < len(haberes_data) else ["", ""]
                right = descuentos_data[i] if i < len(descuentos_data) else ["", ""]
                main_data.append([left, right])

            # Crear tabla con las dos columnas lado a lado
            two_col_table = Table(main_data, colWidths=[3.2*inch, 3.2*inch])
            two_col_table.setStyle(TableStyle([
                # Headers (HABERES IMPONIBLES / ESCUENTOS LEGALES)
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#1F4E78")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#1F4E78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, 0), "LEFT"),

                # Datos
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

                # Totales (últimas filas)
                ("BACKGROUND", (0, -1), (0, -1), colors.HexColor("#E2EFDA")),
                ("BACKGROUND", (1, -1), (1, -1), colors.HexColor("#E2EFDA")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]))
            story.append(two_col_table)
            story.append(Spacer(1, 0.1 * inch))

            # HABERES NO IMPONIBLES
            if calculation.total_non_taxable > 0:
                no_imponibles_table = Table(
                    [["HABERES NO IMPONIBLES", f"${calculation.total_non_taxable:,.0f}"]],
                    colWidths=[3.2*inch, 3.2*inch]
                )
                no_imponibles_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E1F2")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("LEFTPADDING", (0, 0), (-1, 0), 3),
                    ("RIGHTPADDING", (0, 0), (-1, 0), 3),
                    ("TOPPADDING", (0, 0), (-1, 0), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                    ("GRID", (0, 0), (-1, 0), 0.5, colors.grey),
                ]))
                story.append(no_imponibles_table)
                story.append(Spacer(1, 0.08 * inch))

            # RESUMEN FINAL (ancho completo)
            resumen_data = [
                ["TOTAL HABERES", f"${calculation.total_earnings:,.0f}"],
                ["TOTAL DESCUENTOS", f"${calculation.total_discounts:,.0f}"],
                ["LÍQUIDO A RECIBIR", f"${calculation.net_salary:,.0f}"],
            ]

            resumen_table = Table(resumen_data, colWidths=[3.2*inch, 3.2*inch])
            resumen_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#1F4E78")),
                ("TEXTCOLOR", (0, 0), (-1, 1), colors.whitesmoke),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#C6EFCE")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]))
            story.append(resumen_table)

            # Generar PDF
            doc.build(story)
            logger.info(f"Archivo PDF generado: {output_filename}")
            return True

        except Exception as e:
            logger.error(f"Error generando PDF calculadora: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _calculate_ipc_adjusted_salary(self, salary_history: list, ipc_history: List[Dict]) -> Tuple[list, list, list]:
        """
        Calcula el sueldo ajustado por IPC para cada período del historial.

        Args:
            salary_history: Lista de registros con start_date y base_wage
            ipc_history: Lista de registros con mes y valor_ipc

        Returns:
            Tupla con (fechas, sueldos_reales, sueldos_ipc)
        """
        if not salary_history:
            return [], [], []

        # Ordenar historial por fecha ascendente (más antiguo primero)
        sorted_history = sorted(salary_history, key=lambda x: x.get("start_date", ""))

        # Los IPC se guardan como tasa del período (ej: 0.0403 = 4,03% en
        # nov-2022) y solo para los meses en que la empresa reajusta (marzo,
        # julio y noviembre). Para poder valorizar cualquier mes se encadenan
        # las tasas en orden cronológico y se arma un índice acumulado.
        tasas = sorted(
            (
                (registro["mes"], float(registro["valor_ipc"]))
                for registro in ipc_history
                if registro.get("mes") and registro.get("valor_ipc") is not None
                # Descarta valores tipo "índice" de una carga antigua con otro
                # formato: una tasa por período nunca llega a 100% (1.0).
                and float(registro["valor_ipc"]) <= 1.0
            ),
            key=lambda item: item[0],
        )

        indice_por_mes = {}
        factor_acumulado = 1.0
        for mes_ipc, tasa in tasas:
            factor_acumulado *= (1 + tasa)
            indice_por_mes[mes_ipc] = factor_acumulado

        def indice_hasta(mes: str) -> float:
            """Índice acumulado del último reajuste aplicado en o antes de `mes`."""
            aplicables = [f for m, f in indice_por_mes.items() if m <= mes]
            return aplicables[-1] if aplicables else 1.0

        dates = []
        real_salaries = []
        ipc_salaries = []

        initial_salary = None
        indice_inicial = None

        for record in sorted_history:
            start_date = record.get("start_date", "")
            wage = record.get("base_wage", 0)

            if not start_date or not wage:
                continue

            # Extraer mes en formato YYYY-MM
            month_key = start_date[:7]
            dates.append(month_key)
            real_salaries.append(wage)

            if initial_salary is None:
                # Primer registro con datos válidos (más antiguo)
                initial_salary = wage
                indice_inicial = indice_hasta(month_key)
                ipc_salaries.append(wage)
            else:
                # Sueldo si solo se hubieran aplicado los reajustes por IPC
                ipc_salaries.append(initial_salary * (indice_hasta(month_key) / indice_inicial))

        return dates, real_salaries, ipc_salaries

    def _build_salary_evolution_figure(self, salary_history: list, ipc_history: List[Dict], sobrepasa_por_periodo: Optional[Dict[str, bool]] = None):
        """
        Construye la figura matplotlib de evolución salarial (Real vs Ajustado por IPC).

        Compartida entre la generación del PDF y el gráfico equivalente mostrado
        en la app (Propuestas), para que ambos se vean siempre igual.

        Args:
            salary_history: Lista de registros con start_date y base_wage (ya filtrados)
            ipc_history: Lista de registros con mes y valor_ipc
            sobrepasa_por_periodo: Si se entrega, marca los puntos usando esta
                comparación período a período ({"YYYY-MM": True/False}) en vez del
                criterio por defecto (acumulado vs sueldo inicial). Permite que el
                resaltado del gráfico coincida exactamente con el de la tabla.

        Returns:
            Tupla con (figura matplotlib, lista de puntos de ajuste) o (None, []) si hay error
        """
        try:
            if len(salary_history) < 2:
                return None, []

            dates, real_salaries, ipc_salaries = self._calculate_ipc_adjusted_salary(
                salary_history, ipc_history
            )

            if not dates:
                return None, []

            # Crear figura con estilo limpio
            fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
            fig.patch.set_facecolor('white')
            ax.set_facecolor('#F9F9F9')

            # Convertir fechas a índices para plotear
            x_indices = np.arange(len(dates))

            # Plotear líneas
            ax.plot(x_indices, real_salaries, color='#1F4E78', linewidth=2.5,
                   label='Sueldo Real (Efectivo)', marker='o', markersize=6, zorder=3)
            ax.plot(x_indices, ipc_salaries, color='#A0A0A0', linewidth=2,
                   linestyle='--', label='Sueldo Ajustado por IPC (Contractual)',
                   marker='s', markersize=4, zorder=2)

            # Marcar los puntos donde el reajuste difiere del IPC
            adjustment_points = []
            for i, (real, ipc) in enumerate(zip(real_salaries, ipc_salaries)):
                if sobrepasa_por_periodo is not None:
                    # El marcado viene indexado por mes, así que hay dos casos que
                    # cuidar: el primer punto es la base del gráfico y no tiene
                    # variación previa que destacar, y cuando un mes trae más de
                    # un registro la variación corresponde al último de ellos.
                    ultimo_del_mes = (i + 1 == len(dates)) or (dates[i + 1] != dates[i])
                    es_ajuste = (
                        i > 0
                        and ultimo_del_mes
                        and bool(sobrepasa_por_periodo.get(dates[i], False))
                    )
                else:
                    es_ajuste = real > ipc * 1.01  # 1% de tolerancia para evitar ruido

                if es_ajuste:
                    ax.scatter(i, real, marker='o', s=150, color='#FF8C00',
                              edgecolors='#E67E00', linewidths=1.5, zorder=4)
                    adjustment_points.append((dates[i], real, ipc))

            # Formato de ejes
            ax.set_xticks(x_indices[::max(1, len(x_indices)//6)])
            ax.set_xticklabels([dates[i] for i in x_indices[::max(1, len(x_indices)//6)]],
                              rotation=45, ha='right', fontsize=9)

            ax.set_ylabel('Pesos Chilenos ($)', fontsize=10, fontweight='bold')
            # Un decimal en los millones: redondear a entero hacía que marcas
            # distintas (2,4M y 2,8M) se mostraran con la misma etiqueta.
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M' if x >= 1e6 else f'${x/1e3:.0f}K'))

            # Leyenda
            ax.legend(loc='upper left', fontsize=9, framealpha=0.95)

            # Grid
            ax.grid(True, alpha=0.3, linestyle=':', zorder=0)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            plt.tight_layout()

            return fig, adjustment_points

        except Exception as e:
            logger.error(f"Error construyendo gráfico de evolución salarial: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None, []

    def _generate_salary_evolution_chart(
        self,
        salary_history: list,
        ipc_history: List[Dict],
        sobrepasa_por_periodo: Optional[Dict[str, bool]] = None,
    ) -> Tuple[Optional[Image], list]:
        """
        Genera un gráfico de evolución salarial con matplotlib y lo retorna como Image para PDF.

        Args:
            salary_history: Lista de registros con start_date y base_wage
            ipc_history: Lista de registros con mes y valor_ipc
            sobrepasa_por_periodo: Marcado período a período ({"YYYY-MM": True/False}),
                para que los puntos destacados coincidan con la tabla en pantalla

        Returns:
            Tupla con (Objeto Image de reportlab, lista de puntos de ajuste) o (None, []) si hay error
        """
        try:
            import tempfile

            # Filtrar historial
            filtered_history = [record for record in salary_history
                               if record.get("start_date", "")[:7] > "2019-05"]

            fig, adjustment_points = self._build_salary_evolution_figure(
                filtered_history, ipc_history, sobrepasa_por_periodo
            )
            if fig is None:
                return None, []

            # Guardar en archivo temporal
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
                plt.savefig(tmp_path, format='png', dpi=100, bbox_inches='tight')

            plt.close(fig)

            # Crear objeto Image de reportlab
            img = Image(tmp_path, width=6.5*inch, height=3.25*inch)

            return img, adjustment_points

        except Exception as e:
            logger.error(f"Error generando gráfico de evolución salarial: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None, []

    def _calcular_periodos_sobre_ipc(self, salary_history: list, db_manager) -> Dict[str, bool]:
        """
        Determina, período a período, qué aumentos superan el reajuste por IPC.

        Usa el mismo criterio que la app (AnalysisDBManager.aumento_supera_ipc),
        para que los puntos destacados del gráfico coincidan con las filas
        destacadas de la tabla en pantalla.

        Args:
            salary_history: Lista de registros con start_date y base_wage
            db_manager: AnalysisDBManager, o None si no se pudo inicializar

        Returns:
            Dict {"YYYY-MM": True/False}. Vacío si no hay con qué comparar.
        """
        if not db_manager:
            return {}

        ordenado = sorted(salary_history, key=lambda x: x.get("start_date", ""))
        resultado = {}
        sueldo_anterior = None

        for record in ordenado:
            start_date = record.get("start_date", "")
            wage = record.get("base_wage", 0)
            if not start_date or not wage:
                continue

            if sueldo_anterior and sueldo_anterior > 0 and wage != sueldo_anterior:
                aumento_pct = ((wage - sueldo_anterior) / sueldo_anterior) * 100
                resultado[start_date[:7]] = db_manager.aumento_supera_ipc(start_date[:7], aumento_pct)

            sueldo_anterior = wage

        return resultado

    def _add_salary_history_to_pdf(self, story, salary_history: list):
        """Agrega historial de sueldos con gráfico a una segunda página del PDF."""
        # Título
        title_style = ParagraphStyle(
            'HistoryTitle',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor("#1F4E78"),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=12,
        )
        story.append(Paragraph("HISTORIAL DE SUELDOS", title_style))
        story.append(Spacer(1, 0.2 * inch))

        # Filtrar registros
        filtered_history = [record for record in salary_history if record.get("start_date", "")[:7] > "2019-05"]

        if not filtered_history:
            story.append(Paragraph("No hay registro de historial de sueldos disponible.", self.styles['Normal']))
            return

        # Obtener datos de IPC desde la base de datos
        db_manager = None
        try:
            from .analysis.db_manager import AnalysisDBManager
            db_manager = AnalysisDBManager()
            ipc_history = db_manager.get_ipc_history()
        except Exception as e:
            logger.warning(f"No se pudo obtener historial de IPC: {e}")
            ipc_history = []

        # Marcar los mismos períodos que la app resalta en la tabla, para que
        # el PDF y la pantalla cuenten exactamente la misma historia.
        sobrepasa_por_periodo = self._calcular_periodos_sobre_ipc(filtered_history, db_manager)

        # Generar gráfico de evolución salarial
        if ipc_history and len(filtered_history) >= 2:
            chart_result = self._generate_salary_evolution_chart(
                filtered_history, ipc_history, sobrepasa_por_periodo=sobrepasa_por_periodo
            )
            if chart_result and chart_result[0]:
                chart_img, adjustment_points = chart_result
                story.append(chart_img)
                story.append(Spacer(1, 0.2 * inch))

                # Agregar tabla explicativa de ajustes reales
                if adjustment_points:
                    explanation_style = ParagraphStyle(
                        'ExplanationTitle',
                        parent=self.styles['Normal'],
                        fontSize=10,
                        fontName='Helvetica-Bold',
                        textColor=colors.HexColor("#1F4E78"),
                        spaceAfter=6,
                    )
                    story.append(Paragraph("Ajustes Salariales Realizados", explanation_style))

                    # Obtener los 2 mayores ajustes
                    sorted_adjustments = sorted(
                        adjustment_points,
                        key=lambda x: ((x[1] - x[2]) / x[2]) * 100 if x[2] > 0 else 0,
                        reverse=True
                    )[:2]

                    adjustment_data = [["Mes", "Aumento vs IPC", "% vs IPC", "Detalles del Ajuste"]]

                    for month, real_salary, ipc_salary in sorted_adjustments:
                        real_component = real_salary - ipc_salary
                        real_component_pct = ((real_component) / ipc_salary * 100) if ipc_salary > 0 else 0

                        adjustment_data.append([
                            month,
                            f"${real_component:,.0f}",
                            f"{real_component_pct:.1f}%",
                            f"Ajuste real adicional por encima de IPC"
                        ])

                    adjustment_table = Table(adjustment_data, colWidths=[1.2*inch, 1.2*inch, 1.0*inch, 2.1*inch])
                    adjustment_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
                    ]))
                    story.append(adjustment_table)
                    story.append(Spacer(1, 0.2 * inch))

        # Preparar datos para la tabla
        history_data = [["Periodo", "Sueldo Base", "Variación ($)", "Variación (%)"]]

        for i, record in enumerate(filtered_history):
            start = record.get("start_date", "")
            wage = record.get("base_wage", 0)

            periodo = start[:7] if start else "N/A"
            variation = 0
            variation_pct = 0

            if i < len(filtered_history) - 1:
                prev_wage = filtered_history[i + 1].get("base_wage", 0)
                if prev_wage:
                    variation = wage - prev_wage
                    variation_pct = (variation / prev_wage * 100) if prev_wage > 0 else 0

            history_data.append([
                periodo,
                f"${wage:,.0f}",
                f"${variation:,.0f}" if variation != 0 else "-",
                f"{variation_pct:+.1f}%" if variation != 0 else "-"
            ])

        # Crear tabla
        history_table = Table(history_data, colWidths=[1.3 * inch, 1.5 * inch, 1.3 * inch, 1 * inch])
        history_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
        ]))
        story.append(history_table)
        story.append(Spacer(1, 0.2 * inch))

        # Resumen
        if len(filtered_history) > 0:
            summary_style = ParagraphStyle(
                'SummaryTitle',
                parent=self.styles['Normal'],
                fontSize=11,
                fontName='Helvetica-Bold',
                spaceAfter=6,
            )
            story.append(Paragraph("RESUMEN", summary_style))

            # Datos del resumen
            total_periods = len(filtered_history)
            first_wage = filtered_history[-1].get("base_wage", 0)
            current_wage = filtered_history[0].get("base_wage", 0)
            total_increase = current_wage - first_wage
            total_increase_pct = (total_increase / first_wage * 100) if first_wage > 0 else 0

            summary_data = [
                ["Total Períodos:", f"{total_periods}"],
                ["Sueldo Inicial:", f"${first_wage:,.0f}"],
                ["Sueldo Actual:", f"${current_wage:,.0f}"],
                ["Aumento Total:", f"${total_increase:,.0f}"],
                ["% Aumento:", f"{total_increase_pct:+.1f}%"],
            ]

            summary_table = Table(summary_data, colWidths=[2 * inch, 1.5 * inch])
            summary_table.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8E8E8")),
            ]))
            story.append(summary_table)

    def export_compensation_comparison(self, empleado_nombre: str, comparativa: dict,
                                       filename: str = None) -> str:
        """
        Exporta comparativa de compensación anual a PDF.

        Args:
            empleado_nombre: Nombre del empleado
            comparativa: Dict con datos de comparativa de CompensationComparator
            filename: Nombre del archivo (default: auto-generated)

        Returns:
            Ruta del archivo generado
        """
        from datetime import datetime
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comparativa_compensacion_{timestamp}.pdf"

        doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()

        # Encabezado
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor("#1F4E78"),
            spaceAfter=12,
            alignment=1
        )

        story.append(Paragraph("💰 Comparativa de Compensación Anual", title_style))
        story.append(Spacer(1, 0.2*inch))

        # Información del empleado
        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#333333")
        )

        story.append(Paragraph(f"<b>Empleado:</b> {empleado_nombre}", info_style))
        story.append(Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}", info_style))
        story.append(Spacer(1, 0.2*inch))

        # Tabla comparativa
        table_data = [
            ["Concepto", "Actual", "Propuesta"],
            ["Bono Target (rentas)",
             f"{comparativa['actual']['target_rentas']:.1f}",
             f"{comparativa['propuesta']['target_rentas']:.1f}"],
            ["Nivel HAY",
             comparativa['actual']['nivel_hay'],
             comparativa['propuesta']['nivel_hay']],
            ["Mercado",
             comparativa['actual']['mercado'],
             comparativa['propuesta']['mercado']],
            ["Mediana",
             f"${comparativa['actual']['median']:,.0f}",
             f"${comparativa['propuesta']['median']:,.0f}"],
            ["Posición Media Nivel (%)",
             f"{comparativa['actual']['compratio_pct']:.1f}%",
             f"{comparativa['propuesta']['compratio_pct']:.1f}%"],
            ["% Variable Target",
             f"{comparativa['actual']['variable_pct']:.1f}%",
             f"{comparativa['propuesta']['variable_pct']:.1f}%"],
            ["Compensación Anual",
             f"${comparativa['actual']['annual_compensation']:,.0f}",
             f"${comparativa['propuesta']['annual_compensation']:,.0f}"],
        ]

        comp_table = Table(table_data, colWidths=[2.5*inch, 2*inch, 2*inch])
        comp_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8E8E8")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ]))

        story.append(comp_table)
        story.append(Spacer(1, 0.2*inch))

        # Resumen de cambios
        cambio = comparativa['cambio']['compensation_change']
        cambio_pct = comparativa['cambio']['compensation_change_pct']

        cambio_color = "#228B22" if cambio >= 0 else "#DC143C"
        story.append(Paragraph(
            f"<b>Cambio en Compensación Anual:</b> "
            f"<font color='{cambio_color}'>${cambio:,.0f} ({cambio_pct:+.2f}%)</font>",
            info_style
        ))

        # Generar PDF
        doc.build(story)
        return filename
