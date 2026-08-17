"""
Cargador de datos desde Buk hacia la BD SQLite.
"""

from typing import List, Optional, Tuple
from src.buk_client import BukClient
from src.analysis.salary_analyzer import SalaryAnalyzer
from src.analysis.db_manager import AnalysisDBManager
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """Cargador de datos desde Buk a BD."""

    def __init__(self, buk_client: BukClient, db_manager: AnalysisDBManager):
        """
        Inicializa el cargador.

        Args:
            buk_client: Cliente de Buk
            db_manager: Gestor de BD
        """
        self.buk_client = buk_client
        self.db_manager = db_manager
        self.analyzer = SalaryAnalyzer(buk_client)
        self._areas_cache = None  # Cache para mapeo de área_id -> nombre

    def load_all_employees(self, company_ids: Optional[List[int]] = None) -> Tuple[int, int, List[str]]:
        """
        Carga análisis de empleados desde Buk.

        Args:
            company_ids: Lista de IDs de empresas a procesar (None = todas)

        Returns:
            (total_cargados, errores, ruts_con_error)
        """
        logger.info(f"Iniciando carga de empleados desde Buk...")

        # Obtener lista de empresas desde Buk
        companies = self.buk_client.get_companies()
        if not companies:
            logger.error("No se pudieron obtener empresas de Buk")
            return 0, 0, []

        # Filtrar empresas si se especificaron IDs
        if company_ids:
            companies = [c for c in companies if c["id"] in company_ids]
            logger.info(f"Procesando {len(companies)} empresa(s) especificada(s)")
        else:
            logger.info(f"Procesando todas las {len(companies)} empresa(s)")

        total_loaded = 0
        total_errors = 0
        error_ruts = []

        # Por cada empresa, obtener empleados
        for company in companies:
            logger.info(f"Procesando empresa: {company['name']}")

            try:
                # Obtener empleados de esta empresa
                response = self.buk_client.session.get(
                    f"{self.buk_client.base_url}/employees",
                    params={
                        "company_id": company["id"],
                        "status": "activo",
                        "page_size": 100,
                    },
                    timeout=10,
                )
                response.raise_for_status()

                data = response.json()
                employees = data.get("data", [])

                logger.info(f"   Encontrados {len(employees)} empleados")

                # Analizar cada empleado
                for employee_data in employees:
                    try:
                        rut = employee_data.get("rut")
                        if not rut:
                            continue

                        # FILTRO: Solo empleados VIGENTES (activos)
                        status = employee_data.get("status", "").lower()
                        if status != "activo":
                            logger.debug(f"   Omitido (inactivo): {rut}")
                            continue

                        # Analizar empleado (pasar datos completos para calcular edad y antigüedad)
                        analysis = self.analyzer.analyze_employee(rut=rut, employee_data=employee_data)
                        if not analysis:
                            logger.warning(f"   Omitido (sin historial): {rut}")
                            total_errors += 1
                            error_ruts.append(rut)
                            continue

                        # Obtener nombre del área desde el job actual
                        area_id = None
                        nivel_hay = None
                        target = None

                        if "current_job" in employee_data:
                            current_job = employee_data["current_job"]
                            area_id = current_job.get("area_id")

                            # Extraer atributos personalizados
                            custom_attrs = current_job.get("custom_attributes", {})
                            if isinstance(custom_attrs, dict):
                                nivel_hay = custom_attrs.get("Nivel Hay")
                                target = custom_attrs.get("Target")

                        area_name = self._get_area_name(area_id)

                        # Calcular si tiene aumento real
                        sin_aumento_real = self._has_no_real_increase(analysis.total_increase_pct)

                        # Preparar datos para BD
                        analysis_dict = {
                            "rut": analysis.rut,
                            "nombre": analysis.name,
                            "empresa": analysis.company_name,
                            "area": area_name,
                            "cargo_actual": analysis.job_title_current,
                            "fecha_ingreso": analysis.start_date,
                            "meses_en_empresa": analysis.months_in_company,
                            "edad": analysis.age,
                            "meses_en_puesto": analysis.months_in_current_position,
                            "sueldo_inicial": analysis.salary_initial,
                            "sueldo_actual": analysis.salary_current,
                            "aumento_total": analysis.total_increase,
                            "aumento_total_pct": analysis.total_increase_pct,
                            "cambios_salariales": analysis.total_salary_changes,
                            "promedio_aumento_anual": (
                                analysis.total_increase
                                / max(1, analysis.months_in_company / 12)
                            ),
                            "sin_aumento_real": sin_aumento_real,
                            "nivel_hay": nivel_hay,
                            "target": target,
                        }

                        # Insertar en BD
                        if self.db_manager.insert_employee_analysis(analysis_dict):
                            total_loaded += 1
                            logger.debug(f"   ✓ Cargado: {analysis.name}")
                        else:
                            total_errors += 1
                            error_ruts.append(rut)

                    except Exception as e:
                        logger.error(f"   Error procesando empleado: {e}")
                        total_errors += 1
                        error_ruts.append(rut)

            except Exception as e:
                logger.error(f"Error procesando empresa {company['name']}: {e}")

        logger.info(
            f"Carga completada: {total_loaded} cargados, {total_errors} errores"
        )

        return total_loaded, total_errors, error_ruts

    def _get_area_name(self, area_id: Optional[int]) -> Optional[str]:
        """Obtiene nombre del área usando cache."""
        if not area_id:
            return None

        # Cargar cache si no existe
        if self._areas_cache is None:
            areas = self.buk_client.get_areas()
            if areas:
                self._areas_cache = {area.get("id"): area.get("name") for area in areas}
            else:
                self._areas_cache = {}

        return self._areas_cache.get(area_id)

    def load_employee(self, rut: str, employee_data: Optional[dict] = None) -> bool:
        """
        Carga análisis de un empleado específico.

        Args:
            rut: RUT del empleado
            employee_data: Datos del empleado (opcional, para evitar consultas adicionales)

        Returns:
            True si fue exitoso
        """
        try:
            analysis = self.analyzer.analyze_employee(rut=rut, employee_data=employee_data)
            if not analysis:
                logger.warning(f"No se pudo analizar: {rut}")
                return False

            # Obtener nombre del área
            area_name = None
            if employee_data and "current_job" in employee_data:
                area_id = employee_data["current_job"].get("area_id")
                area_name = self._get_area_name(area_id)

            analysis_dict = {
                "rut": analysis.rut,
                "nombre": analysis.name,
                "empresa": analysis.company_name,
                "area": area_name,
                "cargo_actual": analysis.job_title_current,
                "fecha_ingreso": analysis.start_date,
                "meses_en_empresa": analysis.months_in_company,
                "edad": analysis.age,
                "meses_en_puesto": analysis.months_in_current_position,
                "sueldo_inicial": analysis.salary_initial,
                "sueldo_actual": analysis.salary_current,
                "aumento_total": analysis.total_increase,
                "aumento_total_pct": analysis.total_increase_pct,
                "cambios_salariales": analysis.total_salary_changes,
                "promedio_aumento_anual": (
                    analysis.total_increase / max(1, analysis.months_in_company / 12)
                ),
            }

            return self.db_manager.insert_employee_analysis(analysis_dict)

        except Exception as e:
            logger.error(f"Error cargando empleado {rut}: {e}")
            return False

    def _has_no_real_increase(self, total_increase_pct: float) -> bool:
        """
        Determina si el empleado solo ha tenido aumentos por IPC (sin aumento real).

        Args:
            total_increase_pct: Porcentaje de aumento total del empleado

        Returns:
            True si el aumento es menor a 5% (considera solo ajustes por IPC)
        """
        return total_increase_pct < 5.0
