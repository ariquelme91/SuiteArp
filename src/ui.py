"""Interfaz de usuario interactiva con Rich e Inquirer."""

import os
from datetime import datetime
from typing import Optional, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from inquirer import prompt, List, Text, Confirm as InquirerConfirm
import logging

from .buk_client import BukClient, Employee
from .payroll_engine import PayrollEngine
from .simulator import Simulator, ComparisonResult
from .exporter import ExcelExporter
from .pdf_exporter import PDFExporter

logger = logging.getLogger(__name__)
console = Console()


class InteractiveUI:
    """Interfaz de usuario interactiva para Propuestas de Renta."""

    def __init__(
        self,
        buk_client: BukClient,
        payroll_engine: PayrollEngine,
    ):
        """Inicializa UI."""
        self.buk_client = buk_client
        self.payroll_engine = payroll_engine
        self.simulator = Simulator(payroll_engine)
        self.excel_exporter = ExcelExporter()
        self.pdf_exporter = PDFExporter()
        self.current_employee: Optional[Employee] = None
        self.standard_proposals: Optional[Dict] = None

    def show_welcome(self):
        """Muestra pantalla de bienvenida."""
        console.clear()
        console.print(
            Panel(
                "[bold cyan]PROPUESTAS DE RENTA - SIMULADOR AUTOMÁTICO[/bold cyan]\n"
                "Sistema integrado con API Buk para cálculo de nómina chilena",
                title="Bienvenido",
                expand=False,
            )
        )

    def show_main_menu(self) -> str:
        """Menú principal."""
        questions = [
            List(
                "option",
                message="¿Qué desea hacer?",
                choices=[
                    "1. Buscar Colaborador",
                    "2. Listar Colaboradores",
                    "3. Configurar Parámetros",
                    "4. Salir",
                ],
            ),
        ]
        answers = prompt(questions)
        return answers["option"].split(".")[0].strip()

    def search_employee_by_rut(self) -> Optional[Employee]:
        """Busca empleado por RUT o apellido paterno interactivamente."""
        console.print(
            "\n[bold yellow]Búsqueda de Colaborador[/bold yellow]"
        )

        questions = [
            List(
                "search_type",
                message="¿Cómo desea buscar?",
                choices=[
                    "Por RUT (ej: 12.345.678-9)",
                    "Por Apellido Paterno",
                ],
            ),
        ]
        answers = prompt(questions)

        if answers["search_type"] == "Por RUT (ej: 12.345.678-9)":
            search_input = Prompt.ask("Ingrese RUT", default="").strip()
            if not search_input:
                console.print("[red]Operación cancelada[/red]")
                return None
            console.print("[cyan]Buscando por RUT...[/cyan]")
            employee = self.buk_client.search_employee(rut=search_input)
        else:
            search_input = Prompt.ask("Ingrese apellido paterno", default="").strip()
            if not search_input:
                console.print("[red]Operación cancelada[/red]")
                return None
            console.print("[cyan]Buscando por apellido paterno...[/cyan]")
            employee = self.buk_client.search_employee(name=search_input)

        if employee:
            self.current_employee = employee
            self._display_employee_card(employee)
            return employee
        else:
            console.print("[red]Colaborador no encontrado en Buk[/red]")
            console.print("[yellow]Nota: Solo se buscan empleados activos en el mes actual[/yellow]")
            return None

    def list_employees(self):
        """Lista colaboradores con paginación."""
        console.print("\n[bold yellow]Listado de Colaboradores[/bold yellow]")

        page = 1
        while True:
            employees = self.buk_client.list_employees(page=page, page_size=10)

            if not employees:
                console.print("[yellow]No hay más colaboradores[/yellow]")
                break

            table = Table(title=f"Página {page}")
            table.add_column("#", style="cyan")
            table.add_column("RUT", style="magenta")
            table.add_column("Nombre", style="green")
            table.add_column("Cargo", style="yellow")
            table.add_column("Sueldo Base", style="blue", justify="right")

            for idx, emp in enumerate(employees, 1):
                table.add_row(
                    str(idx),
                    emp.rut,
                    emp.full_name,
                    emp.job_title or "N/A",
                    f"${emp.base_salary:,.0f}",
                )

            console.print(table)

            questions = [
                List(
                    "action",
                    message="¿Qué desea hacer?",
                    choices=[
                        "Seleccionar Colaborador",
                        "Página Siguiente",
                        "Página Anterior",
                        "Volver",
                    ],
                ),
            ]
            answers = prompt(questions)
            action = answers["action"]

            if action == "Seleccionar Colaborador":
                idx_str = Prompt.ask("Ingrese número de colaborador (1-10)", default="1")
                try:
                    idx = int(idx_str) - 1
                    if 0 <= idx < len(employees):
                        self.current_employee = employees[idx]
                        self._display_employee_card(employees[idx])
                        break
                except ValueError:
                    console.print("[red]Número inválido[/red]")

            elif action == "Página Siguiente":
                page += 1

            elif action == "Página Anterior":
                if page > 1:
                    page -= 1

            elif action == "Volver":
                break

    def create_proposal(self) -> Optional[ComparisonResult]:
        """Crea una propuesta de renta interactivamente."""
        if not self.current_employee:
            console.print("[red]Debe seleccionar un colaborador primero[/red]")
            return None

        console.print(
            Panel(
                "[bold cyan]CREAR PROPUESTA DE RENTA[/bold cyan]",
                expand=False,
            )
        )

        # Preguntas de cambios organizacionales
        questions = [
            InquirerConfirm(
                "change_company",
                message=f"¿Cambiará de empresa? (Actual: {self.current_employee.company_name})",
                default=False,
            ),
            InquirerConfirm(
                "change_position",
                message=f"¿Cambiará de cargo? (Actual: {self.current_employee.job_title})",
                default=False,
            ),
            InquirerConfirm(
                "change_supervisor",
                message=f"¿Cambiará de jefatura? (Actual: {self.current_employee.supervisor})",
                default=False,
            ),
        ]
        org_changes = prompt(questions)

        # Construcción de datos de propuesta
        new_company = self.current_employee.company_name
        new_position = self.current_employee.job_title
        new_supervisor = self.current_employee.supervisor

        # Guardar datos actuales para exportación
        self.current_company_name = self.current_employee.company_name
        self.current_position = self.current_employee.job_title
        self.current_supervisor = self.current_employee.supervisor

        if org_changes["change_company"]:
            # Obtener listado de empresas
            companies = self.buk_client.get_companies()
            if companies:
                company_choices = [f"{c['name']} (ID: {c['id']})" for c in companies]
                questions = [
                    List(
                        "company",
                        message="Seleccione nueva empresa",
                        choices=company_choices,
                    ),
                ]
                answers = prompt(questions)
                # Extraer solo el nombre sin el ID
                new_company = answers["company"].split(" (ID:")[0]
            else:
                new_company = Prompt.ask("Ingrese nueva empresa (no se pudo cargar listado)")

        if org_changes["change_position"]:
            new_position = Prompt.ask("Ingrese nuevo cargo")

        if org_changes["change_supervisor"]:
            new_supervisor = Prompt.ask("Ingrese nuevo nombre de jefe")

        change_date = Prompt.ask(
            "Fecha de aplicación (DD/MM/YYYY)",
            default=datetime.now().strftime("%d/%m/%Y"),
        )

        # Datos de haberes actuales - INGRESO DEL USUARIO
        console.print("\n[bold yellow]Datos de Haberes ACTUALES del Mes[/bold yellow]")
        console.print("[cyan]Ingrese los valores actuales del colaborador. Deje en blanco si es 0.[/cyan]\n")

        current_collation_str = Prompt.ask(
            "Colación actual ($)",
            default="0",
        ).strip() or "0"
        current_collation = float(current_collation_str)

        current_mobility_str = Prompt.ask(
            "Movilización actual ($)",
            default="0",
        ).strip() or "0"
        current_mobility = float(current_mobility_str)

        current_other_taxable_str = Prompt.ask(
            "Otros haberes imponibles ($) - ej: bonos variables",
            default="0",
        ).strip() or "0"
        current_other_taxable = float(current_other_taxable_str)

        # Datos de haberes propuestos
        console.print("\n[bold yellow]Datos de Haberes PROPUESTOS[/bold yellow]")

        questions = [
            List(
                "salary_method",
                message="¿Cómo desea ingresar el nuevo sueldo?",
                choices=[
                    "Ingresar Sueldo Base Directamente",
                    "Calcular Base para Líquido Objetivo",
                ],
            ),
        ]
        answers = prompt(questions)

        if answers["salary_method"] == "Ingresar Sueldo Base Directamente":
            proposal_base_salary = float(
                Prompt.ask(
                    f"Nuevo Sueldo Base (Actual: ${self.current_employee.base_salary:,.0f})",
                    default=str(self.current_employee.base_salary)
                )
            )
        else:
            target_liquid = float(Prompt.ask("¿Cuál es el Sueldo Líquido objetivo? ($)"))
            proposal_base_salary = self.payroll_engine.reverse_calculate_base_salary(
                target_net_salary=target_liquid,
                collation=current_collation,
                mobility=current_mobility,
                contract_type=self.current_employee.contract_type,
                pension_fund=self.current_employee.pension_fund,
            )
            console.print(
                f"\n[green]✓ Sueldo Base calculado: ${proposal_base_salary:,.0f}[/green]\n"
            )

        console.print("[cyan]Ingrese nuevos montos. Presione ENTER para mantener actual.[/cyan]\n")

        proposal_collation_str = Prompt.ask(
            f"Colación propuesta (Actual: ${current_collation:,.0f})",
            default=str(current_collation),
        ).strip() or str(current_collation)
        proposal_collation = float(proposal_collation_str)

        proposal_mobility_str = Prompt.ask(
            f"Movilización propuesta (Actual: ${current_mobility:,.0f})",
            default=str(current_mobility),
        ).strip() or str(current_mobility)
        proposal_mobility = float(proposal_mobility_str)

        proposal_other_taxable_str = Prompt.ask(
            f"Otros haberes imponibles (Actual: ${current_other_taxable:,.0f})",
            default=str(current_other_taxable),
        ).strip() or str(current_other_taxable)
        proposal_other_taxable = float(proposal_other_taxable_str)

        # Crear comparativa principal
        comparison = self.simulator.compare(
            employee_name=self.current_employee.full_name,
            employee_rut=self.current_employee.rut,
            change_date=change_date,
            current_base_salary=self.current_employee.base_salary,
            current_collation=current_collation,
            current_mobility=current_mobility,
            current_other_taxable=current_other_taxable,
            proposal_base_salary=proposal_base_salary,
            proposal_collation=proposal_collation,
            proposal_mobility=proposal_mobility,
            proposal_other_taxable=proposal_other_taxable,
            contract_type=self.current_employee.contract_type,
            pension_fund=self.current_employee.pension_fund,
        )

        # Calcular propuestas estándar (5%, 10%, 15%, 20%)
        self.standard_proposals = self.simulator.calculate_standard_proposals(
            employee_name=self.current_employee.full_name,
            employee_rut=self.current_employee.rut,
            change_date=change_date,
            current_base_salary=self.current_employee.base_salary,
            contract_type=self.current_employee.contract_type,
            current_collation=current_collation,
            current_mobility=current_mobility,
            current_other_taxable=current_other_taxable,
            current_other_non_taxable=0,
            pension_fund=self.current_employee.pension_fund,
        )

        # Guardar datos de propuesta para exportación
        self.proposal_company_name = new_company
        self.proposal_position = new_position
        self.proposal_supervisor = new_supervisor

        return comparison

    def display_comparison(self, comparison: ComparisonResult):
        """Muestra tabla de comparación."""
        console.print("\n")
        console.print(comparison.format_comparison_table())

        impact = self.simulator.calculate_net_impact(comparison)

        console.print("\n[bold yellow]RESUMEN DE IMPACTO[/bold yellow]")
        table = Table(title="Impacto Económico")
        table.add_column("Concepto", style="cyan")
        table.add_column("Impacto", justify="right", style="magenta")

        for label, value in [
            ("Impacto Sueldo Líquido (Mensual)", impact["employee_impact"]),
            ("Impacto Costo Empresa (Mensual)", impact["employer_impact"]),
            ("Impacto Total Nómina (Mensual)", impact["total_payroll_impact"]),
        ]:
            color = "green" if value > 0 else "red" if value < 0 else "yellow"
            table.add_row(label, f"[{color}]${value:,.0f}[/{color}]")

        console.print(table)

    def export_to_excel(self, comparison: ComparisonResult) -> bool:
        """Exporta comparativa a Excel o PDF."""
        questions = [
            List(
                "format",
                message="¿Qué formato desea exportar?",
                choices=["Excel (.xlsx)", "PDF (.pdf)", "Ambos"],
            ),
        ]
        answers = prompt(questions)
        export_format = answers["format"]

        base_filename = f"Propuesta_Renta_{self.current_employee.rut.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        success = True

        # Obtener nombre de empresa
        company_display = self.current_employee.company_name
        if self.current_employee.company_id:
            try:
                companies = self.buk_client.get_companies()
                if companies:
                    for comp in companies:
                        if comp.get("id") == self.current_employee.company_id:
                            company_display = comp.get("name", self.current_employee.company_name)
                            break
            except Exception:
                pass

        if export_format in ["Excel (.xlsx)", "Ambos"]:
            filename_xlsx = base_filename + ".xlsx"
            console.print(f"[cyan]Generando Excel: {filename_xlsx}[/cyan]")

            success_xlsx = self.excel_exporter.export_comparison(
                comparison=comparison,
                output_filename=filename_xlsx,
                company_name=company_display or "Empresa",
                prepared_by="Recursos Humanos",
                standard_proposals=self.standard_proposals,
                current_company=getattr(self, 'current_company_name', ''),
                current_position=getattr(self, 'current_position', ''),
                current_supervisor=getattr(self, 'current_supervisor', ''),
                proposal_company=getattr(self, 'proposal_company_name', ''),
                proposal_position=getattr(self, 'proposal_position', ''),
                proposal_supervisor=getattr(self, 'proposal_supervisor', ''),
            )

            if success_xlsx:
                console.print(f"[green]✓ Excel generado exitosamente[/green]")
                console.print(f"[cyan]Ruta: {os.path.abspath(filename_xlsx)}[/cyan]")
            else:
                console.print("[red]✗ Error al generar Excel[/red]")
                success = False

        if export_format in ["PDF (.pdf)", "Ambos"]:
            filename_pdf = base_filename + ".pdf"
            console.print(f"[cyan]Generando PDF: {filename_pdf}[/cyan]")

            success_pdf = self.pdf_exporter.export_comparison(
                comparison=comparison,
                output_filename=filename_pdf,
                company_name=company_display or "Empresa",
                prepared_by="Recursos Humanos",
                standard_proposals=self.standard_proposals,
                current_company=getattr(self, 'current_company_name', ''),
                current_position=getattr(self, 'current_position', ''),
                current_supervisor=getattr(self, 'current_supervisor', ''),
                proposal_company=getattr(self, 'proposal_company_name', ''),
                proposal_position=getattr(self, 'proposal_position', ''),
                proposal_supervisor=getattr(self, 'proposal_supervisor', ''),
            )

            if success_pdf:
                console.print(f"[green]✓ PDF generado exitosamente[/green]")
                console.print(f"[cyan]Ruta: {os.path.abspath(filename_pdf)}[/cyan]")
            else:
                console.print("[red]✗ Error al generar PDF[/red]")
                success = False

        return success

    def _display_employee_card(self, employee: Employee):
        """Muestra tarjeta de información del colaborador."""
        # Obtener nombre de empresa si tenemos el ID
        company_display = employee.company_name
        if employee.company_id:
            try:
                companies = self.buk_client.get_companies()
                if companies:
                    for comp in companies:
                        if comp.get("id") == employee.company_id:
                            company_display = comp.get("name", employee.company_name)
                            break
            except Exception as e:
                logger.error(f"Error obteniendo nombre de empresa: {e}")
                company_display = employee.company_name

        card_content = f"""[bold cyan]{employee.full_name}[/bold cyan]
RUT: {employee.rut}
Email: {employee.email or 'N/A'}
Empresa: {company_display or 'N/A'}
Cargo: {employee.job_title or 'N/A'}
Jefe Directo: {employee.supervisor or 'N/A'}
Tipo de Contrato: {employee.contract_type}
Sueldo Base Actual: [bold green]${employee.base_salary:,.0f}[/bold green]
Fecha de Ingreso: {employee.start_date or 'N/A'}"""

        console.print(Panel(card_content, title="Información del Colaborador", expand=False))

    def run_interactive_session(self):
        """Ejecuta sesión interactiva completa."""
        self.show_welcome()

        while True:
            option = self.show_main_menu()

            if option == "1":
                if self.search_employee_by_rut():
                    if Confirm.ask("\n¿Desea crear una propuesta de renta?"):
                        comparison = self.create_proposal()
                        if comparison:
                            self.display_comparison(comparison)
                            if Confirm.ask("\n¿Desea exportar?"):
                                self.export_to_excel(comparison)

            elif option == "2":
                self.list_employees()

            elif option == "3":
                console.print("[yellow]Funcionalidad disponible en próxima versión[/yellow]")

            elif option == "4":
                console.print("[cyan]¡Hasta pronto![/cyan]")
                break

            if Confirm.ask("\n¿Desea continuar?", default=True):
                console.clear()
            else:
                break
