"""Cliente para integración con API de Buk."""

import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
import re
import time

logger = logging.getLogger(__name__)


@dataclass
class Employee:
    """Modelo de Colaborador desde Buk."""
    rut: str
    full_name: str
    email: Optional[str]
    start_date: Optional[str]
    company_name: Optional[str]
    company_id: Optional[int]
    job_title: Optional[str]
    supervisor: Optional[str]
    base_salary: float
    contract_type: str
    fixed_items: List[Dict[str, Any]]
    pension_fund: Optional[str] = None
    nivel_hay: Optional[str] = None
    target: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class BukClient:
    """Cliente para consumir API de Buk Chile."""

    def __init__(self, auth_token: str, subdomain: str):
        """
        Inicializa cliente Buk.

        Args:
            auth_token: Token de autenticación API Buk
            subdomain: Subdominio de la empresa en Buk
        """
        self.auth_token = auth_token
        self.subdomain = subdomain
        self.base_url = f"https://{subdomain}.buk.cl/api/v1/chile"
        self.session = requests.Session()
        self.session.headers.update({
            "auth_token": auth_token,
            "Content-Type": "application/json"
        })

    def _format_rut(self, rut: str) -> str:
        """Formatea RUT chileno (ej: 12345678-9 -> 123456789)."""
        return re.sub(r'[.-]', '', rut).upper()

    def _validate_rut(self, rut: str) -> bool:
        """Valida formato básico de RUT chileno."""
        rut_clean = self._format_rut(rut)
        return len(rut_clean) >= 8

    def search_employees_by_name(self, name: str) -> Optional[List[Employee]]:
        """
        Busca colaboradores por nombre/apellido. Retorna lista de coincidencias.

        Args:
            name: Apellido paterno o nombre del colaborador

        Returns:
            Lista de empleados que coinciden o None en caso de error
        """
        if not name:
            logger.error("Debe proporcionar nombre")
            return None

        try:
            # Obtener todos los empleados activos
            params = {
                "status": "activo",
                "page_size": 100
            }

            response = self.session.get(
                f"{self.base_url}/employees",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            employees_data = data.get("data", [])

            if not employees_data:
                logger.warning(f"No se encontraron empleados activos")
                return None

            name_lower = name.lower().strip()
            matches = []

            # Filtrar por nombre/apellido de forma más específica
            for emp_data in employees_data:
                full_name = emp_data.get("full_name", "").lower()
                first_name = emp_data.get("first_name", "").lower()
                surname = emp_data.get("surname", "").lower()
                second_surname = emp_data.get("second_surname", "").lower()

                # Buscar coincidencia en cualquiera de estos campos
                if (name_lower in full_name or
                    name_lower in first_name or
                    name_lower in surname or
                    name_lower in second_surname):
                    employee = self._parse_employee(emp_data)
                    if employee:
                        matches.append(employee)

            if not matches:
                logger.warning(f"No se encontraron coincidencias para: {name}")
                return None

            return matches

        except Exception as e:
            logger.error(f"Error buscando empleados por nombre: {e}")
            return None

    def search_employee(self, rut: str = None, name: str = None) -> Optional[Employee]:
        """
        Busca colaborador por RUT o nombre. Solo retorna empleados activos.

        Args:
            rut: RUT del colaborador (ej: 12.345.678-9)
            name: Apellido paterno del colaborador

        Returns:
            Employee si se encuentra, None en caso contrario
        """
        if not rut and not name:
            logger.error("Debe proporcionar RUT o nombre")
            return None

        try:
            params = {"status": "activo"}

            if rut:
                if not self._validate_rut(rut):
                    logger.error(f"RUT inválido: {rut}")
                    return None
                params["rut"] = self._format_rut(rut)

            elif name:
                # Búsqueda por apellido: usar parámetro search y filtrar resultados
                params["search"] = name
                params["page_size"] = 100

            response = self.session.get(
                f"{self.base_url}/employees",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            employees_data = data.get("data", [])

            if not employees_data:
                search_term = rut or name
                logger.warning(f"Colaborador no encontrado: {search_term}")
                return None

            # Si es búsqueda por nombre, filtrar resultados por coincidencia en apellido
            if name:
                name_lower = name.lower().strip()
                matches = []

                # Filtrar empleados cuyo nombre contenga el apellido buscado (búsqueda flexible)
                for emp_data in employees_data:
                    full_name = emp_data.get("full_name", "").lower()
                    # Dividir el nombre en palabras y buscar coincidencia
                    name_parts = full_name.split()
                    if any(name_lower in part for part in name_parts):
                        matches.append(emp_data)

                if matches:
                    # Retornar el primero de los coincidentes
                    return self._parse_employee(matches[0])
                else:
                    # Si no hay coincidencia, retornar None
                    logger.warning(f"No se encontró coincidencia para: {name}")
                    return None
            else:
                # Si es RUT, retornar el primero (debe haber solo uno)
                employee_data = employees_data[0]
                return self._parse_employee(employee_data)

        except requests.exceptions.ConnectionError:
            logger.error("Error de conexión con API Buk")
            return None
        except requests.exceptions.Timeout:
            logger.error("Timeout en consulta a API Buk (reintentando...)")
            # Reintentar una vez después de esperar
            try:
                time.sleep(2)
                response = self.session.get(
                    f"{self.base_url}/employees",
                    params=params,
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()
                employees_data = data.get("data", [])

                if not employees_data:
                    return None

                if name:
                    name_lower = name.lower().strip()
                    matches = []
                    for emp_data in employees_data:
                        full_name = emp_data.get("full_name", "").lower()
                        name_parts = full_name.split()
                        if any(name_lower in part for part in name_parts):
                            matches.append(emp_data)
                    if matches:
                        return self._parse_employee(matches[0])
                    return None
                else:
                    return self._parse_employee(employees_data[0])
            except Exception:
                logger.error("Reintento falló")
                return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Token inválido o sin permisos de datos sensibles")
            else:
                logger.error(f"Error HTTP {e.response.status_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return None

    def list_employees(self, page: int = 1, page_size: int = 50) -> Optional[List[Employee]]:
        """
        Lista colaboradores activos con paginación.

        Args:
            page: Número de página (desde 1)
            page_size: Cantidad de registros por página

        Returns:
            Lista de empleados activos o None si hay error
        """
        try:
            response = self.session.get(
                f"{self.base_url}/employees",
                params={"page": page, "page_size": page_size, "status": "activo"},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            employees = []

            for emp_data in data.get("data", []):
                employee = self._parse_employee(emp_data)
                if employee:
                    employees.append(employee)

            return employees

        except requests.exceptions.Timeout:
            logger.error(f"Timeout en listado de empleados (reintentando...)")
            try:
                time.sleep(2)
                response = self.session.get(
                    f"{self.base_url}/employees",
                    params={"page": page, "page_size": page_size, "status": "activo"},
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()
                employees = []
                for emp_data in data.get("data", []):
                    employee = self._parse_employee(emp_data)
                    if employee:
                        employees.append(employee)
                return employees
            except Exception:
                logger.error("Reintento de listado falló")
                return None

        except Exception as e:
            logger.error(f"Error listando empleados: {e}")
            return None

    def _parse_employee(self, data: Dict[str, Any]) -> Optional[Employee]:
        """Extrae datos relevantes de la respuesta de Buk."""
        try:
            # En Buk API v1 Chile, los datos están estructurados de forma diferente
            current_job = data.get("current_job", {})

            # Datos personales están en el nivel raíz
            rut = data.get("rut", "")
            full_name = data.get("full_name", "")
            email = data.get("email")  # Email laboral

            # Datos del contrato (usar active_since para fecha de ingreso a empresa)
            start_date = data.get("active_since") or current_job.get("start_date")
            contract_type = current_job.get("contract_type", "indefinido")
            contract_type = contract_type.lower().replace("indefinido", "indefinido").replace("plazo fijo", "plazo_fijo")

            # Empresa: obtener ID y nombre
            company_id = current_job.get('company_id')
            company_name = self.get_company_name(company_id) if company_id else 'N/A'

            # Cargo
            role = current_job.get("role", {})
            job_title = role.get("name") if isinstance(role, dict) else None

            # Jefe: obtener nombre desde RUT
            boss = current_job.get("boss", {})
            supervisor = None
            if isinstance(boss, dict):
                boss_rut = boss.get("rut")
                if boss_rut:
                    # Intentar obtener nombre del supervisor por RUT
                    supervisor = self.get_supervisor_name(boss_rut)
                    # Si no encuentra nombre, usar el del boss object si existe
                    if not supervisor:
                        supervisor = boss.get("full_name") or boss.get("name")
                    # Si aún no hay nombre, usar el RUT
                    if not supervisor:
                        supervisor = f"RUT: {boss_rut}"

            # Sueldo base está directamente en current_job
            base_salary = current_job.get("base_wage", 0)

            # Fondo de pensión/AFP
            pension_fund = data.get("pension_fund")

            # Items/asignaciones no vienen en este endpoint
            fixed_items = []

            # Extraer custom_attributes (Nivel HAY, Target, etc.)
            custom_attributes = {}
            nivel_hay = None
            target = None

            # Buscar custom_attributes en current_job
            if isinstance(current_job, dict):
                job_custom = current_job.get("custom_attributes", {})
                if isinstance(job_custom, dict):
                    custom_attributes.update(job_custom)

            # También buscar en nivel raíz (si existen)
            root_custom = data.get("custom_attributes", {})
            if isinstance(root_custom, dict):
                custom_attributes.update(root_custom)

            # Extraer específicamente Nivel HAY y Target (probando diferentes nombres de campo)
            nivel_hay_keys = ["nivel_hay", "nivel hay", "Nivel HAY", "Nivel Hay", "nivel_hay_actual"]
            target_keys = ["target", "Target", "target_rentas", "Target Rentas", "rentas"]

            for key in nivel_hay_keys:
                if key in custom_attributes and custom_attributes[key]:
                    nivel_hay = str(custom_attributes[key])
                    break

            for key in target_keys:
                if key in custom_attributes and custom_attributes[key]:
                    target = str(custom_attributes[key])
                    break

            return Employee(
                rut=rut,
                full_name=full_name,
                email=email,
                start_date=start_date,
                company_name=company_name,
                company_id=company_id,
                job_title=job_title,
                supervisor=supervisor,
                base_salary=float(base_salary),
                contract_type=contract_type,
                fixed_items=fixed_items,
                pension_fund=pension_fund,
                nivel_hay=nivel_hay,
                target=target,
                custom_attributes=custom_attributes
            )

        except Exception as e:
            logger.error(f"Error parseando datos de empleado: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def get_companies(self) -> Optional[List[Dict[str, Any]]]:
        """
        Obtiene lista de empresas.

        Returns:
            Lista de empresas con id y name o None si hay error
        """
        try:
            response = self.session.get(
                f"{self.base_url}/companies",
                params={"page_size": 100},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            companies = []

            for comp_data in data.get("data", []):
                company = {
                    "id": comp_data.get("id"),
                    "name": comp_data.get("name") or comp_data.get("full_name", "N/A"),
                }
                companies.append(company)

            return companies

        except Exception as e:
            logger.error(f"Error obteniendo empresas: {e}")
            return None

    def get_company_name(self, company_id: int) -> Optional[str]:
        """
        Obtiene nombre de empresa por ID.

        Args:
            company_id: ID de la empresa

        Returns:
            Nombre de la empresa o None
        """
        try:
            companies = self.get_companies()
            if companies:
                for comp in companies:
                    if comp.get("id") == company_id:
                        return comp.get("name")
        except Exception as e:
            logger.error(f"Error obteniendo nombre de empresa: {e}")

        return None

    def get_supervisor_name(self, supervisor_rut: str) -> Optional[str]:
        """
        Obtiene nombre del supervisor por RUT.

        Args:
            supervisor_rut: RUT del supervisor (sin formato)

        Returns:
            Nombre del supervisor o None
        """
        try:
            if not supervisor_rut:
                return None

            response = self.session.get(
                f"{self.base_url}/employees",
                params={"rut": supervisor_rut, "page_size": 1},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            employees_data = data.get("data", [])

            if employees_data:
                return employees_data[0].get("full_name")

        except Exception as e:
            logger.error(f"Error obteniendo nombre del supervisor: {e}")

        return None

    def get_salary_history(self, rut: str) -> Optional[List[dict]]:
        """
        Obtiene el historial de sueldos de un empleado desde el campo jobs.

        Args:
            rut: RUT del empleado (con o sin puntos/guión)

        Returns:
            Lista de diccionarios con historial de sueldos (fecha inicio, fin, monto)
        """
        try:
            # Buscar empleado por RUT
            employee_data = self.search_employee(rut=rut)
            if not employee_data:
                return None

            # El objeto Employee no tiene campo 'id', pero podemos hacer otra búsqueda
            response = self.session.get(
                f"{self.base_url}/employees",
                params={"rut": self._format_rut(rut), "status": "activo"},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("data"):
                return None

            employee = data["data"][0]
            jobs = employee.get("jobs", [])

            # Procesar jobs para extraer historial de sueldos
            salary_history = []
            for job in jobs:
                if job.get("base_wage"):  # Solo si tiene sueldo base
                    salary_history.append({
                        "start_date": job.get("start_date"),
                        "end_date": job.get("end_date"),
                        "base_wage": job.get("base_wage"),
                        "company_id": job.get("company_id"),
                    })

            # Ordenar por fecha inicio (más reciente primero)
            salary_history.sort(
                key=lambda x: x["start_date"] if x["start_date"] else "",
                reverse=True
            )

            return salary_history

        except Exception as e:
            logger.error(f"Error obteniendo historial de sueldos: {e}")
            return None

    def get_job_history(self, rut: str) -> Optional[List[dict]]:
        """
        Obtiene el historial completo de cargos/empleos de un empleado.

        Args:
            rut: RUT del empleado (con o sin puntos/guión)

        Returns:
            Lista de diccionarios con historial de empleos (cargo, empresa, área, fechas, sueldo)
        """
        try:
            # Buscar empleado por RUT
            response = self.session.get(
                f"{self.base_url}/employees",
                params={"rut": self._format_rut(rut), "status": "activo"},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("data"):
                return None

            employee = data["data"][0]
            jobs = employee.get("jobs", [])

            # Procesar jobs para extraer historial completo de cargos
            job_history = []
            for job in jobs:
                role = job.get("role", {})
                job_title = role.get("name") if isinstance(role, dict) else None

                company = job.get("company", {})
                company_name = company.get("name") if isinstance(company, dict) else None
                company_id = company.get("id") if isinstance(company, dict) else None

                # Intentar obtener área/departamento
                area = job.get("area", {})
                area_name = area.get("name") if isinstance(area, dict) else None

                job_history.append({
                    "start_date": job.get("start_date"),
                    "end_date": job.get("end_date"),
                    "job_title": job_title,
                    "company_name": company_name,
                    "company_id": company_id,
                    "area_name": area_name,
                    "base_wage": job.get("base_wage"),
                })

            # Ordenar por fecha inicio (más reciente primero)
            job_history.sort(
                key=lambda x: x["start_date"] if x["start_date"] else "",
                reverse=True
            )

            return job_history if job_history else None

        except Exception as e:
            logger.error(f"Error obteniendo historial de cargos: {e}")
            return None

    def test_connection(self) -> bool:
        """Prueba la conexión y validez del token."""
        try:
            response = self.session.get(
                f"{self.base_url}/employees",
                params={"page_size": 1},
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Token inválido o expirado")
            return False
        except Exception as e:
            logger.error(f"Error en test de conexión: {e}")
            return False

    def get_areas(self) -> Optional[List[Dict[str, Any]]]:
        """
        Obtiene lista de áreas/departamentos.

        Returns:
            Lista de áreas con id y name o None si hay error
        """
        try:
            areas = []
            page = 1

            while True:
                response = self.session.get(
                    f"{self.base_url}/areas",
                    params={"page": page, "page_size": 100},
                    timeout=10,
                )
                response.raise_for_status()

                data = response.json()
                page_data = data.get("data", [])

                for area_data in page_data:
                    area = {
                        "id": area_data.get("id"),
                        "name": area_data.get("name"),
                        "status": area_data.get("status"),
                        "parent_area": area_data.get("parent_area"),
                    }
                    areas.append(area)

                # Verificar si hay más páginas
                pagination = data.get("pagination", {})
                if not pagination.get("next"):
                    break

                page += 1

            return areas

        except Exception as e:
            logger.error(f"Error obteniendo áreas: {e}")
            return None

    def get_area_name(self, area_id: int) -> Optional[str]:
        """
        Obtiene el nombre de un área por su ID.

        Args:
            area_id: ID del área

        Returns:
            Nombre del área o None
        """
        try:
            areas = self.get_areas()
            if areas:
                for area in areas:
                    if area.get("id") == area_id:
                        return area.get("name")
        except Exception as e:
            logger.error(f"Error obteniendo nombre de área: {e}")

        return None
