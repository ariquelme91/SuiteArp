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

    def _add_salary_history_to_pdf(self, story, salary_history: list):
        """Agrega historial de sueldos a una segunda página del PDF."""
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
