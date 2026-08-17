"""
Analizador de historial salarial y cambios de cargo.
Procesa datos de get_salary_history() para detectar cambios y calcular métricas.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from src.buk_client import BukClient, Employee
import logging

logger = logging.getLogger(__name__)


@dataclass
class SalaryPeriod:
    """Período de un cargo con sueldos."""
    job_title: str
    start_date: str
    end_date: Optional[str]
    initial_salary: float
    final_salary: float
    salary_increase: float
    salary_increase_pct: float
    months_count: int
    salary_changes: int  # Cantidad de cambios dentro del período


@dataclass
class EmployeeAnalysis:
    """Análisis completo de un empleado."""
    rut: str
    name: str
    company_name: str
    job_title_current: str
    start_date: str
    salary_initial: float
    salary_current: float
    total_increase: float
    total_increase_pct: float
    months_in_company: int
    salary_periods: List[SalaryPeriod]
    total_salary_changes: int
    age: Optional[int] = None
    months_in_current_position: Optional[int] = None


class SalaryAnalyzer:
    """Analizador de cambios salariales y de cargo."""

    def __init__(self, buk_client: BukClient):
        self.buk_client = buk_client

    def analyze_employee(self, rut: str, employee_data: Optional[Dict] = None) -> Optional[EmployeeAnalysis]:
        """
        Analiza un empleado: historial de sueldos, cambios de cargo, métricas.

        Args:
            rut: RUT del empleado
            employee_data: Datos crudos del empleado (opcional, para evitar consultas adicionales)

        Returns:
            EmployeeAnalysis con todas las métricas, o None si no se encuentra
        """
        try:
            # Obtener información del empleado
            employee = self.buk_client.search_employee(rut=rut)
            if not employee:
                logger.warning(f"Empleado no encontrado: {rut}")
                return None

            # Obtener historial de sueldos
            salary_history = self.buk_client.get_salary_history(rut=rut)
            if not salary_history:
                logger.warning(f"Sin historial de sueldos: {rut}")
                return None

            # Procesar períodos de cargo
            salary_periods = self._detect_job_periods(salary_history)

            # Calcular métricas
            salary_initial = salary_history[-1]["base_wage"]  # El más antiguo
            salary_current = salary_history[0]["base_wage"]   # El más reciente
            total_increase = salary_current - salary_initial
            total_increase_pct = (
                (total_increase / salary_initial * 100)
                if salary_initial > 0
                else 0
            )

            # Calcular meses en la empresa
            start_date = salary_history[-1]["start_date"]  # Fecha más antigua
            months_in_company = self._calculate_months(start_date)

            # Calcular edad
            age = None
            if employee_data and employee_data.get("birthday"):
                age = self._calculate_age(employee_data["birthday"])

            # Calcular antigüedad en puesto actual
            months_in_current_position = None
            if employee_data and employee_data.get("current_job"):
                current_job_start = employee_data["current_job"].get("start_date")
                if current_job_start:
                    months_in_current_position = self._calculate_months(current_job_start)

            analysis = EmployeeAnalysis(
                rut=employee.rut,
                name=employee.full_name,
                company_name=employee.company_name,
                job_title_current=employee.job_title,
                start_date=start_date,
                salary_initial=salary_initial,
                salary_current=salary_current,
                total_increase=total_increase,
                total_increase_pct=total_increase_pct,
                months_in_company=months_in_company,
                salary_periods=salary_periods,
                total_salary_changes=len(salary_history) - 1,
                age=age,
                months_in_current_position=months_in_current_position,
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analizando empleado {rut}: {e}")
            return None

    def _detect_job_periods(self, salary_history: List[Dict]) -> List[SalaryPeriod]:
        """
        Detecta cambios de cargo agrupando por períodos.

        En Buk, los cambios de cargo se detectan cuando hay cambios
        en la estructura (análisis manual o por comparación de patrones).
        Aquí agrupamos por períodos contiguos.

        Args:
            salary_history: Historial de sueldos

        Returns:
            Lista de SalaryPeriod
        """
        if not salary_history:
            return []

        # Para esta versión, cada período es el rango completo
        # (asumimos un solo cargo, o detectamos por fecha de cambio)

        # Ordenar de más antiguo a más reciente
        sorted_history = sorted(
            salary_history,
            key=lambda x: x["start_date"] if x["start_date"] else "",
        )

        # Crear un período agrupado
        period = SalaryPeriod(
            job_title="Sin dato de cargo",  # No tenemos cambio de cargo real
            start_date=sorted_history[0]["start_date"],
            end_date=sorted_history[-1]["end_date"],
            initial_salary=sorted_history[0]["base_wage"],
            final_salary=sorted_history[-1]["base_wage"],
            salary_increase=sorted_history[-1]["base_wage"]
            - sorted_history[0]["base_wage"],
            salary_increase_pct=(
                (
                    (sorted_history[-1]["base_wage"] - sorted_history[0]["base_wage"])
                    / sorted_history[0]["base_wage"]
                    * 100
                )
                if sorted_history[0]["base_wage"] > 0
                else 0
            ),
            months_count=len(sorted_history),
            salary_changes=len(sorted_history) - 1,
        )

        return [period]

    def _calculate_months(self, start_date: str) -> int:
        """Calcula meses desde start_date hasta hoy."""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            today = datetime.now()
            months = (today.year - start.year) * 12 + (today.month - start.month)
            return max(0, months)
        except:
            return 0

    def _calculate_age(self, birthday: str) -> Optional[int]:
        """Calcula edad desde fecha de nacimiento."""
        try:
            birth = datetime.strptime(birthday, "%Y-%m-%d")
            today = datetime.now()
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            return age if age >= 0 else None
        except:
            return None

    def format_analysis_for_display(self, analysis: EmployeeAnalysis) -> Dict[str, Any]:
        """Formatea el análisis para mostrar en UI."""
        return {
            "RUT": analysis.rut,
            "Nombre": analysis.name,
            "Empresa": analysis.company_name,
            "Cargo Actual": analysis.job_title_current,
            "Fecha Ingreso": analysis.start_date,
            "Meses en Empresa": analysis.months_in_company,
            "Sueldo Inicial": f"${analysis.salary_initial:,.0f}",
            "Sueldo Actual": f"${analysis.salary_current:,.0f}",
            "Aumento Total ($)": f"${analysis.total_increase:,.0f}",
            "Aumento Total (%)": f"{analysis.total_increase_pct:.1f}%",
            "Cambios Salariales": analysis.total_salary_changes,
            "Promedio Aumento Anual": f"${(analysis.total_increase / max(1, analysis.months_in_company / 12)):,.0f}",
        }
