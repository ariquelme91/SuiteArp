"""Simulación comparativa de Propuestas de Renta."""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from .payroll_engine import PayrollEngine, PayrollCalculation


@dataclass
class ComparisonResult:
    """Resultado de comparación Actual vs Propuesta."""
    current: PayrollCalculation
    proposal: PayrollCalculation
    change_date: str
    employee_name: str
    employee_rut: str
    current_parking_discount: float = 0.0
    proposal_parking_discount: float = 0.0

    def get_comparison_items(self) -> Dict[str, Dict[str, any]]:
        """Retorna diccionario con items comparables."""
        return {
            "Sueldo Base": {
                "actual": self.current.base_salary,
                "proposal": self.proposal.base_salary,
            },
            "Gratificación": {
                "actual": self.current.gratification,
                "proposal": self.proposal.gratification,
            },
            "Colación": {
                "actual": self.current.collation,
                "proposal": self.proposal.collation,
            },
            "Movilización": {
                "actual": self.current.mobility,
                "proposal": self.proposal.mobility,
            },
            "Total Imponible": {
                "actual": self.current.total_taxable,
                "proposal": self.proposal.total_taxable,
            },
            "Total No Imponible": {
                "actual": self.current.total_non_taxable,
                "proposal": self.proposal.total_non_taxable,
            },
            "Total Haberes": {
                "actual": self.current.total_earnings,
                "proposal": self.proposal.total_earnings,
            },
            "Descuento AFP": {
                "actual": self.current.afp_discount,
                "proposal": self.proposal.afp_discount,
            },
            "Descuento Salud": {
                "actual": self.current.health_discount,
                "proposal": self.proposal.health_discount,
            },
            "Descuento AFC": {
                "actual": self.current.afc_discount,
                "proposal": self.proposal.afc_discount,
            },
            "Impuesto a la Renta": {
                "actual": self.current.income_tax,
                "proposal": self.proposal.income_tax,
            },
            "Estacionamiento": {
                "actual": self.current_parking_discount,
                "proposal": self.proposal_parking_discount,
            },
            "Total Descuentos": {
                "actual": self.current.total_discounts + self.current_parking_discount,
                "proposal": self.proposal.total_discounts + self.proposal_parking_discount,
            },
            "Sueldo Líquido Neto": {
                "actual": self.current.net_salary - self.current_parking_discount,
                "proposal": self.proposal.net_salary - self.proposal_parking_discount,
            },
            "Costo Empresa": {
                "actual": self.current.total_employer_cost,
                "proposal": self.proposal.total_employer_cost,
            },
        }

    def format_comparison_table(self) -> str:
        """Retorna tabla formateada con la comparación."""
        items = self.get_comparison_items()
        lines = []
        lines.append("=" * 80)
        lines.append(f"COMPARATIVA: {self.employee_name} ({self.employee_rut})")
        lines.append("=" * 80)
        lines.append(f"{'Concepto':<25} {'Actual':>15} {'Propuesta':>15} {'Variación':>15}")
        lines.append("-" * 80)

        for concept, values in items.items():
            actual = values["actual"]
            proposal = values["proposal"]
            variation = proposal - actual
            variation_pct = (variation / actual * 100) if actual != 0 else 0

            variation_str = f"${variation:,.0f} ({variation_pct:+.1f}%)"

            lines.append(
                f"{concept:<25} ${actual:>14,.0f} ${proposal:>14,.0f} {variation_str:>15}"
            )

        lines.append("=" * 80)
        return "\n".join(lines)


class Simulator:
    """Simulador de Propuestas de Renta."""

    def __init__(self, payroll_engine: PayrollEngine):
        """Inicializa simulador con motor de cálculo."""
        self.engine = payroll_engine

    def compare(
        self,
        employee_name: str,
        employee_rut: str,
        change_date: str,
        current_base_salary: float,
        proposal_base_salary: float,
        contract_type: str = "indefinido",
        current_collation: float = 0,
        current_mobility: float = 0,
        current_other_taxable: float = 0,
        current_other_non_taxable: float = 0,
        proposal_collation: Optional[float] = None,
        proposal_mobility: Optional[float] = None,
        proposal_other_taxable: Optional[float] = None,
        proposal_other_non_taxable: Optional[float] = None,
        pension_fund: Optional[str] = None,
        current_parking_discount: float = 0,
        proposal_parking_discount: float = 0,
    ) -> ComparisonResult:
        """
        Compara situación actual vs propuesta.

        Args:
            employee_name: Nombre completo del empleado
            employee_rut: RUT del empleado
            change_date: Fecha de aplicación de la propuesta
            current_base_salary: Sueldo base actual
            current_collation: Colación actual
            current_mobility: Movilización actual
            current_other_taxable: Otros haberes imponibles actuales
            current_other_non_taxable: Otros haberes no imponibles actuales
            proposal_base_salary: Sueldo base propuesto
            proposal_collation: Colación propuesta (si no se especifica, usa actual)
            proposal_mobility: Movilización propuesta (si no se especifica, usa actual)
            proposal_other_taxable: Otros haberes imponibles propuestos
            proposal_other_non_taxable: Otros haberes no imponibles propuestos
            contract_type: Tipo de contrato
            pension_fund: Fondo de pensión (AFP) del empleado
        """
        # Si no se especifican valores de propuesta, usar actuales
        proposal_collation = proposal_collation or current_collation
        proposal_mobility = proposal_mobility or current_mobility
        proposal_other_taxable = proposal_other_taxable or current_other_taxable
        proposal_other_non_taxable = proposal_other_non_taxable or current_other_non_taxable

        # Calcular situación actual
        current = self.engine.calculate(
            base_salary=current_base_salary,
            collation=current_collation,
            mobility=current_mobility,
            other_taxable=current_other_taxable,
            other_non_taxable=current_other_non_taxable,
            contract_type=contract_type,
            pension_fund=pension_fund,
        )

        # Calcular propuesta
        proposal = self.engine.calculate(
            base_salary=proposal_base_salary,
            collation=proposal_collation,
            mobility=proposal_mobility,
            other_taxable=proposal_other_taxable,
            other_non_taxable=proposal_other_non_taxable,
            contract_type=contract_type,
            pension_fund=pension_fund,
        )

        return ComparisonResult(
            current=current,
            proposal=proposal,
            change_date=change_date,
            employee_name=employee_name,
            employee_rut=employee_rut,
            current_parking_discount=current_parking_discount,
            proposal_parking_discount=proposal_parking_discount,
        )

    def get_impact_summary(self, comparison: ComparisonResult) -> Dict[str, Tuple[float, float]]:
        """
        Obtiene resumen de impacto (variación absoluta y %).

        Returns:
            Dict con {concepto: (variacion_pesos, variacion_percent)}
        """
        items = comparison.get_comparison_items()
        summary = {}

        for concept, values in items.items():
            actual = values["actual"]
            proposal = values["proposal"]
            change = proposal - actual
            change_pct = (change / actual * 100) if actual != 0 else 0

            summary[concept] = (change, change_pct)

        return summary

    def calculate_net_impact(self, comparison: ComparisonResult) -> Dict[str, float]:
        """
        Calcula impacto neto para empleado y empresa.

        Returns:
            Dict con impacto_empleado y impacto_empresa
        """
        employee_impact = comparison.proposal.net_salary - comparison.current.net_salary
        employer_impact = (
            comparison.proposal.total_employer_cost
            - comparison.current.total_employer_cost
        )

        return {
            "employee_impact": employee_impact,
            "employer_impact": employer_impact,
            "total_payroll_impact": employee_impact + employer_impact,
        }

    def calculate_standard_proposals(
        self,
        employee_name: str,
        employee_rut: str,
        change_date: str,
        current_base_salary: float,
        contract_type: str = "indefinido",
        current_collation: float = 0,
        current_mobility: float = 0,
        current_other_taxable: float = 0,
        current_other_non_taxable: float = 0,
        pension_fund: Optional[str] = None,
    ) -> Dict[int, ComparisonResult]:
        """
        Calcula propuestas estándar con incrementos de 5%, 10%, 15%, 20%.

        Returns:
            Diccionario con {porcentaje: ComparisonResult}
        """
        standard_percentages = [5, 10, 15, 20]
        proposals = {}

        for percentage in standard_percentages:
            proposal_base = current_base_salary * (1 + percentage / 100)

            comparison = self.compare(
                employee_name=employee_name,
                employee_rut=employee_rut,
                change_date=change_date,
                current_base_salary=current_base_salary,
                proposal_base_salary=proposal_base,
                contract_type=contract_type,
                current_collation=current_collation,
                current_mobility=current_mobility,
                current_other_taxable=current_other_taxable,
                current_other_non_taxable=current_other_non_taxable,
                pension_fund=pension_fund,
            )

            proposals[percentage] = comparison

        return proposals
