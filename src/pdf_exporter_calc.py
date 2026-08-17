"""Exportador PDF para calculadora de sueldos - Formato 2x2 con 5 filas uniformes."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import logging

logger = logging.getLogger(__name__)


class PDFExporterCalc:
    """Exporta calculadora de sueldos a PDF."""

    def __init__(self):
        self.styles = getSampleStyleSheet()

    def export_calculator(self, calculation, output_filename: str, periodo: str = "", logo_path: str = None, has_parking: bool = False, parking_discount: float = 0) -> bool:
        try:
            doc = SimpleDocTemplate(
                output_filename,
                pagesize=letter,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.4 * inch,
                bottomMargin=0.4 * inch,
            )

            story = []

            # Título centrado
            title_style = ParagraphStyle("Title", parent=self.styles["Heading1"], fontSize=14, fontName="Helvetica-Bold", alignment=TA_CENTER)
            story.append(Paragraph("Liquidación de Sueldo", title_style))

            # Mes centrado
            mes_ano = ""
            if periodo:
                try:
                    mes_num, anio = int(periodo.split("-")[0]), periodo.split("-")[1]
                    meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                    if 1 <= mes_num <= 12:
                        mes_ano = f"Mes: {meses[mes_num]} {anio}"
                except:
                    pass

            info_style = ParagraphStyle("Info", parent=self.styles["Normal"], fontSize=8, alignment=TA_CENTER)
            if mes_ano:
                story.append(Paragraph(mes_ano, info_style))

            story.append(Spacer(1, 0.15 * inch))

            # CAJA 1: HABERES IMPONIBLES (6 filas: header + 3 items + espaciador + total)
            haberes_data = [
                ["HABERES IMPONIBLES", ""],
                ["Sueldo Base", f"$ {calculation.base_salary:,.0f}"],
                ["Gratificación", f"$ {calculation.gratification:,.0f}"],
                ["Otros Imponibles", f"$ {calculation.other_taxable:,.0f}" if calculation.other_taxable > 0 else ""],
                ["", ""],
                ["TOTAL", f"$ {calculation.total_taxable:,.0f}"],
            ]

            # CAJA 2: DESCUENTOS LEGALES (6 filas: 4 items + total + espaciador)
            descuentos_data = [
                ["DESCUENTOS LEGALES", ""],
                ["AFP", f"$ {calculation.afp_discount:,.0f}"],
                ["Salud", f"$ {calculation.health_discount:,.0f}"],
                ["AFC", f"$ {calculation.afc_discount:,.0f}" if calculation.afc_discount > 0 else ""],
                ["Impuesto Renta", f"$ {calculation.income_tax:,.0f}" if calculation.income_tax > 0 else ""],
                ["TOTAL", f"$ {calculation.total_discounts:,.0f}"],
            ]

            # CAJA 3: HABERES NO IMPONIBLES (6 filas: header + 3 items + 1 vacía + total)
            no_imponibles_data = [
                ["HABERES NO IMPONIBLES", ""],
                ["Movilización", f"$ {calculation.mobility:,.0f}" if calculation.mobility > 0 else ""],
                ["Colación", f"$ {calculation.collation:,.0f}" if calculation.collation > 0 else ""],
                ["Otros No Imponibles", f"$ {calculation.other_non_taxable:,.0f}" if calculation.other_non_taxable > 0 else ""],
                ["", ""],
                ["TOTAL", f"$ {calculation.total_non_taxable:,.0f}"],
            ]

            # CAJA 4: OTROS DESCUENTOS (6 filas: header + items + vacias + total - ALINEADO CON HABERES NO IMPONIBLES)
            otros_data = [
                ["OTROS DESCUENTOS", ""],
                ["Estacionamiento", f"$ {parking_discount:,.0f}" if has_parking and parking_discount > 0 else ""],
                ["", ""],
                ["", ""],
                ["", ""],
                ["TOTAL", f"$ {parking_discount:,.0f}" if has_parking and parking_discount > 0 else "$ 0"],
            ]

            # Crear tablas individuales con ancho uniforme
            haberes_table = Table(haberes_data, colWidths=[1.8*inch, 1.2*inch])
            descuentos_table = Table(descuentos_data, colWidths=[1.8*inch, 1.2*inch])
            no_imponibles_table = Table(no_imponibles_data, colWidths=[1.8*inch, 1.2*inch])
            otros_table = Table(otros_data, colWidths=[1.8*inch, 1.2*inch])

            # Estilo uniforme para todas las tablas
            table_style = [
                ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#D9E1F2")),
                ("FONTNAME", (0, 0), (1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (1, -1), 8),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (1, -1), 0.25, colors.HexColor("#CCCCCC")),
                ("LINEABOVE", (0, 0), (1, 0), 0.25, colors.HexColor("#CCCCCC")),
                ("LEFTPADDING", (0, 0), (1, -1), 3),
                ("RIGHTPADDING", (0, 0), (1, -1), 3),
                ("TOPPADDING", (0, 0), (1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (1, -1), 2),
                ("BACKGROUND", (0, -1), (1, -1), colors.HexColor("#E8E8E8")),
                ("FONTNAME", (0, -1), (1, -1), "Helvetica-Bold"),
                ("BOX", (0, 0), (1, -1), 0.25, colors.HexColor("#CCCCCC")),
            ]

            for table in [haberes_table, descuentos_table, no_imponibles_table, otros_table]:
                table.setStyle(TableStyle(table_style))

            # Grilla 2x3 de cajas con columna intermedia para separación
            from reportlab.platypus import Spacer as PlatypusSpacer
            separator_col = ""  # Columna vacía para separación
            grid_data = [
                [haberes_table, separator_col, descuentos_table],
                [no_imponibles_table, separator_col, otros_table],
            ]
            grid_table = Table(grid_data, colWidths=[3.0*inch, 0.3*inch, 3.0*inch], rowHeights=[1.5*inch, 1.5*inch])
            grid_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (2, 1), "TOP"),
                ("LEFTPADDING", (0, 0), (2, 1), 0),
                ("RIGHTPADDING", (0, 0), (2, 1), 0),
            ]))
            story.append(grid_table)
            story.append(Spacer(1, 0.12 * inch))

            # TOTALES GENERALES (incluye otros descuentos)
            total_all_discounts = calculation.total_discounts + (parking_discount if has_parking else 0)
            totales_data = [
                ["TOTAL HABERES", f"$ {calculation.total_earnings:,.0f}", "TOTAL DESCUENTOS", f"$ {total_all_discounts:,.0f}"],
            ]
            totales_table = Table(totales_data, colWidths=[1.5*inch, 1.0*inch, 1.5*inch, 1.0*inch])
            totales_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (3, 0), colors.HexColor("#E8E8E8")),
                ("FONTNAME", (0, 0), (3, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (3, 0), 9),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("ALIGN", (3, 0), (3, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (3, 0), 3),
                ("RIGHTPADDING", (0, 0), (3, 0), 3),
                ("TOPPADDING", (0, 0), (3, 0), 3),
                ("BOTTOMPADDING", (0, 0), (3, 0), 3),
                ("LINEBELOW", (0, 0), (3, 0), 0.25, colors.HexColor("#CCCCCC")),
                ("LINEABOVE", (0, 0), (3, 0), 0.25, colors.HexColor("#CCCCCC")),
            ]))
            story.append(totales_table)
            story.append(Spacer(1, 0.08 * inch))

            # LÍQUIDO A RECIBIR (incluye otros descuentos como estacionamiento)
            total_other_discounts = parking_discount if has_parking else 0
            final_liquid = calculation.net_salary - total_other_discounts
            liquid_data = [[f"LÍQUIDO A RECIBIR: $ {final_liquid:,.0f}"]]
            liquid_table = Table(liquid_data, colWidths=[6.0*inch])
            liquid_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#E8E8E8")),
                ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (0, 0), 10),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("LEFTPADDING", (0, 0), (0, 0), 3),
                ("RIGHTPADDING", (0, 0), (0, 0), 3),
                ("TOPPADDING", (0, 0), (0, 0), 3),
                ("BOTTOMPADDING", (0, 0), (0, 0), 3),
                ("LINEBELOW", (0, 0), (0, 0), 0.25, colors.HexColor("#CCCCCC")),
                ("LINEABOVE", (0, 0), (0, 0), 0.25, colors.HexColor("#CCCCCC")),
            ]))
            story.append(liquid_table)

            doc.build(story)
            logger.info(f"PDF generado: {output_filename}")
            return True

        except Exception as e:
            logger.error(f"Error en PDF: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
