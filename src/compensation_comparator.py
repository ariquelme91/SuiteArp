"""Comparador de compensación anual Actual vs Propuesta."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class CompensationScenario:
    """Escenario de compensación (Actual o Propuesta)."""
    base_salary: float
    target_rentas: float
    nivel_hay: str
    mercado: str
    months: int = 12

    def __post_init__(self):
        """Validar datos."""
        if self.base_salary < 0:
            raise ValueError("base_salary no puede ser negativo")
        if self.target_rentas < 0:
            raise ValueError("target_rentas no puede ser negativo")
        if self.months <= 0:
            raise ValueError("months debe ser mayor a 0")


@dataclass
class CompensationResult:
    """Resultado del cálculo de compensación."""
    annual_compensation: float
    median: float
    compratio_pct: float
    variable_pct: float
    bono_anualizado: float


class CompensationComparator:
    """Comparador de compensación anual."""

    def __init__(self, db_manager, payroll_engine):
        """
        Inicializa comparador.

        Args:
            db_manager: AnalysisDBManager instance
            payroll_engine: PayrollEngine instance
        """
        self.db = db_manager
        self.engine = payroll_engine

    def get_median(self, nivel_hay: str, mercado: str) -> Optional[float]:
        """
        Obtiene mediana de compensation_levels.

        Args:
            nivel_hay: Nivel HAY (ej: "16", "18")
            mercado: Mercado (ej: "Mercado Financiero", "Mercado Seguros")

        Returns:
            Mediana en pesos o None si no existe
        """
        try:
            # Mapear nombres de mercado a claves en BD
            mercado_key = "mercado_financiero" if "Financiero" in mercado else "mercado_seguros"

            with __import__("sqlite3").connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT {mercado_key} FROM compensation_levels WHERE nivel = ?",
                    (nivel_hay,)
                )
                result = cursor.fetchone()
                return float(result[0]) if result and result[0] else None
        except Exception as e:
            logger.error(f"Error obteniendo mediana: {e}")
            return None

    def calculate_annual_compensation(
        self,
        base_salary: float,
        target_rentas: float,
        months: int = 12
    ) -> float:
        """
        Calcula compensación anual.

        Fórmula: (base_salary × meses) + (target_rentas × base_salary)

        Args:
            base_salary: Sueldo base mensual
            target_rentas: Bono target en rentas (ej: 2.8)
            months: Meses a anualizar (default: 12)

        Returns:
            Compensación anual en pesos
        """
        salary_component = base_salary * months
        bonus_component = target_rentas * base_salary
        return salary_component + bonus_component

    def calculate_compratio(
        self,
        annual_compensation: float,
        median: float
    ) -> float:
        """
        Calcula posición media nivel (Compratio %).

        Fórmula: (annual_compensation / median) × 100

        Args:
            annual_compensation: Compensación anual
            median: Mediana del nivel y mercado

        Returns:
            Compratio como porcentaje (ej: 96.5)
        """
        if median == 0 or median is None:
            return 0.0
        return (annual_compensation / median) * 100

    def calculate_variable_pct(
        self,
        target_rentas: float,
        base_salary: float,
        annual_compensation: float
    ) -> float:
        """
        Calcula porcentaje variable (% del bono sobre total).

        Fórmula: ((target_rentas × base_salary) / annual_compensation) × 100

        Args:
            target_rentas: Bono target en rentas
            base_salary: Sueldo base mensual
            annual_compensation: Compensación anual total

        Returns:
            Porcentaje variable (ej: 11.2)
        """
        if annual_compensation == 0:
            return 0.0
        bono_anualizado = target_rentas * base_salary
        return (bono_anualizado / annual_compensation) * 100

    def calculate_scenario(self, scenario: CompensationScenario) -> CompensationResult:
        """
        Calcula todos los valores de un escenario.

        Args:
            scenario: CompensationScenario con datos

        Returns:
            CompensationResult con todos los cálculos
        """
        annual_comp = self.calculate_annual_compensation(
            scenario.base_salary,
            scenario.target_rentas,
            scenario.months
        )

        median = self.get_median(scenario.nivel_hay, scenario.mercado)
        if median is None:
            median = 0.0

        compratio = self.calculate_compratio(annual_comp, median)
        variable = self.calculate_variable_pct(
            scenario.target_rentas,
            scenario.base_salary,
            annual_comp
        )
        bono_anual = scenario.target_rentas * scenario.base_salary

        return CompensationResult(
            annual_compensation=annual_comp,
            median=median,
            compratio_pct=compratio,
            variable_pct=variable,
            bono_anualizado=bono_anual
        )

    def compare(
        self,
        actual: CompensationScenario,
        propuesta: CompensationScenario
    ) -> Dict[str, Any]:
        """
        Compara dos escenarios de compensación.

        Args:
            actual: Escenario actual
            propuesta: Escenario propuesto

        Returns:
            Diccionario con comparativa completa
        """
        result_actual = self.calculate_scenario(actual)
        result_propuesta = self.calculate_scenario(propuesta)

        # Calcular variación
        comp_change = result_propuesta.annual_compensation - result_actual.annual_compensation
        comp_change_pct = (comp_change / result_actual.annual_compensation * 100
                          if result_actual.annual_compensation > 0 else 0)

        return {
            "actual": {
                "base_salary": actual.base_salary,
                "target_rentas": actual.target_rentas,
                "nivel_hay": actual.nivel_hay,
                "mercado": actual.mercado,
                "bono_anualizado": result_actual.bono_anualizado,
                "median": result_actual.median,
                "compratio_pct": result_actual.compratio_pct,
                "variable_pct": result_actual.variable_pct,
                "annual_compensation": result_actual.annual_compensation,
            },
            "propuesta": {
                "base_salary": propuesta.base_salary,
                "target_rentas": propuesta.target_rentas,
                "nivel_hay": propuesta.nivel_hay,
                "mercado": propuesta.mercado,
                "bono_anualizado": result_propuesta.bono_anualizado,
                "median": result_propuesta.median,
                "compratio_pct": result_propuesta.compratio_pct,
                "variable_pct": result_propuesta.variable_pct,
                "annual_compensation": result_propuesta.annual_compensation,
            },
            "cambio": {
                "compensation_change": comp_change,
                "compensation_change_pct": comp_change_pct,
            }
        }
