"""
Gestor de Base de Datos SQLite para análisis de salarios.
"""

import sqlite3
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)


class AnalysisDBManager:
    """Gestor de BD SQLite para análisis de salarios."""

    def __init__(self, db_path: str = "data/analysis.db"):
        """
        Inicializa el gestor de BD.

        Args:
            db_path: Ruta a la base de datos SQLite
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Inicializa las tablas de la BD."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Tabla de análisis de empleados
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS employee_analysis (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rut TEXT UNIQUE NOT NULL,
                        nombre TEXT NOT NULL,
                        empresa TEXT,
                        area TEXT,
                        cargo_actual TEXT,
                        fecha_ingreso TEXT,
                        meses_en_empresa INTEGER,
                        edad INTEGER,
                        meses_en_puesto INTEGER,
                        sueldo_inicial REAL,
                        sueldo_actual REAL,
                        aumento_total REAL,
                        aumento_total_pct REAL,
                        cambios_salariales INTEGER,
                        promedio_aumento_anual REAL,
                        sin_aumento_real BOOLEAN,
                        nivel_hay TEXT,
                        target TEXT,
                        datos_json TEXT,
                        fecha_carga TEXT,
                        fecha_actualizacion TEXT
                    )
                    """
                )

                # Agregar columnas si no existen (para tablas existentes)
                try:
                    cursor.execute("ALTER TABLE employee_analysis ADD COLUMN nivel_hay TEXT")
                except sqlite3.OperationalError:
                    pass  # La columna ya existe

                try:
                    cursor.execute("ALTER TABLE employee_analysis ADD COLUMN target TEXT")
                except sqlite3.OperationalError:
                    pass  # La columna ya existe

                # Tabla de períodos de cargo
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS salary_periods (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rut TEXT NOT NULL,
                        cargo TEXT,
                        fecha_inicio TEXT,
                        fecha_fin TEXT,
                        sueldo_inicial REAL,
                        sueldo_final REAL,
                        aumento REAL,
                        aumento_pct REAL,
                        meses INTEGER,
                        cambios INTEGER,
                        FOREIGN KEY (rut) REFERENCES employee_analysis(rut)
                    )
                    """
                )

                # Tabla de logs de exportación
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS export_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha_exportacion TEXT,
                        empresa TEXT,
                        area TEXT,
                        cantidad_empleados INTEGER,
                        archivo TEXT,
                        tipo TEXT
                    )
                    """
                )

                # Tabla de IPC histórico
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ipc_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        mes TEXT UNIQUE NOT NULL,
                        valor_ipc REAL NOT NULL,
                        fecha_creacion TEXT,
                        fecha_actualizacion TEXT
                    )
                    """
                )

                # Tabla de Compensaciones por Nivel (valores totales de referencia)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS compensation_levels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nivel INTEGER UNIQUE NOT NULL,
                        mercado_financiero REAL,
                        mercado_seguros REAL,
                        descripcion TEXT,
                        fecha_creacion TEXT,
                        fecha_actualizacion TEXT
                    )
                    """
                )

                # Tabla de UF histórica (para cálculos de movilización)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS uf_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        mes TEXT UNIQUE NOT NULL,
                        valor_uf REAL NOT NULL,
                        fecha_creacion TEXT,
                        fecha_actualizacion TEXT
                    )
                    """
                )

                # Tabla de Promedios de Compensación por Nivel HAY (para competitividad interna)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS compensation_averages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nivel_hay TEXT UNIQUE NOT NULL,
                        cantidad_empleados INTEGER,
                        promedio_anualizado REAL,
                        minimo_anualizado REAL,
                        maximo_anualizado REAL,
                        desviacion_std REAL,
                        fecha_calculo TEXT,
                        fecha_actualizacion TEXT
                    )
                    """
                )

                # Tabla de valores manuales de Nivel HAY y Target
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS employee_manual_values (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rut TEXT UNIQUE NOT NULL,
                        nivel_hay_manual TEXT,
                        target_manual TEXT,
                        fecha_creacion TEXT,
                        fecha_actualizacion TEXT
                    )
                    """
                )

                # Tabla de propuestas de compensación (Actual vs Propuesta)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS compensation_proposals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rut TEXT NOT NULL,
                        empleado_nombre TEXT,
                        fecha_propuesta TEXT,
                        actual_base_salary REAL,
                        actual_target_rentas REAL,
                        actual_nivel_hay TEXT,
                        actual_mercado TEXT,
                        actual_annual_comp REAL,
                        propuesta_base_salary REAL,
                        propuesta_target_rentas REAL,
                        propuesta_nivel_hay TEXT,
                        propuesta_mercado TEXT,
                        propuesta_annual_comp REAL,
                        cambio_comp REAL,
                        cambio_comp_pct REAL,
                        comentarios TEXT,
                        pdf_path TEXT,
                        fecha_creacion TEXT,
                        fecha_actualizacion TEXT
                    )
                    """
                )

                conn.commit()
                logger.info(f"Base de datos inicializada: {self.db_path}")

        except Exception as e:
            logger.error(f"Error inicializando BD: {e}")
            raise

    def insert_employee_analysis(self, analysis: Dict[str, Any]) -> bool:
        """
        Inserta o actualiza un análisis de empleado.

        Args:
            analysis: Diccionario con datos del análisis

        Returns:
            True si fue exitoso
        """
        try:
            from datetime import datetime

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO employee_analysis (
                        rut, nombre, empresa, area, cargo_actual,
                        fecha_ingreso, meses_en_empresa, edad, meses_en_puesto, sueldo_inicial,
                        sueldo_actual, aumento_total, aumento_total_pct,
                        cambios_salariales, promedio_aumento_anual, sin_aumento_real,
                        nivel_hay, target, datos_json, fecha_carga, fecha_actualizacion
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        analysis["rut"],
                        analysis["nombre"],
                        analysis.get("empresa"),
                        analysis.get("area"),
                        analysis.get("cargo_actual"),
                        analysis.get("fecha_ingreso"),
                        analysis.get("meses_en_empresa"),
                        analysis.get("edad"),
                        analysis.get("meses_en_puesto"),
                        analysis.get("sueldo_inicial"),
                        analysis.get("sueldo_actual"),
                        analysis.get("aumento_total"),
                        analysis.get("aumento_total_pct"),
                        analysis.get("cambios_salariales"),
                        analysis.get("promedio_aumento_anual"),
                        analysis.get("sin_aumento_real", False),
                        analysis.get("nivel_hay"),
                        analysis.get("target"),
                        json.dumps(analysis),
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                    ),
                )

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error insertando análisis: {e}")
            return False

    def get_empresas(self) -> List[str]:
        """Obtiene lista de empresas únicas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT empresa FROM employee_analysis WHERE empresa IS NOT NULL ORDER BY empresa")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo empresas: {e}")
            return []

    def get_areas(self, empresa: Optional[str] = None) -> List[str]:
        """Obtiene lista de áreas únicas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if empresa:
                    cursor.execute(
                        "SELECT DISTINCT area FROM employee_analysis WHERE area IS NOT NULL AND empresa = ? ORDER BY area",
                        (empresa,),
                    )
                else:
                    cursor.execute("SELECT DISTINCT area FROM employee_analysis WHERE area IS NOT NULL ORDER BY area")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo áreas: {e}")
            return []

    def get_analysis_by_empresa_area(
        self, empresa: Optional[str] = None, area: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Obtiene análisis filtrados por empresa y área."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = "SELECT * FROM employee_analysis WHERE 1=1"
                params = []

                if empresa:
                    query += " AND empresa = ?"
                    params.append(empresa)

                if area:
                    query += " AND area = ?"
                    params.append(area)

                query += " ORDER BY aumento_total DESC"

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Error obteniendo análisis: {e}")
            return []

    def get_employee_by_rut(self, rut: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos de análisis de un empleado por RUT.

        Args:
            rut: RUT del empleado (con o sin formato)

        Returns:
            Dict con datos del empleado (incluyendo nivel_hay y target) o None si no existe
        """
        try:
            rut_input = rut.strip()
            rut_clean = rut_input.replace(".", "").replace("-", "").strip()

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Intentar primero búsqueda exacta con el formato original
                cursor.execute(
                    "SELECT * FROM employee_analysis WHERE rut = ? LIMIT 1",
                    (rut_input,)
                )
                row = cursor.fetchone()

                # Si no encuentra, intentar con búsqueda flexible
                if not row:
                    cursor.execute(
                        "SELECT * FROM employee_analysis WHERE rut LIKE ? LIMIT 1",
                        (f"%{rut_clean}%",)
                    )
                    row = cursor.fetchone()

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Error obteniendo empleado por RUT {rut}: {e}")
            return None

    def get_summary_metrics(
        self, empresa: Optional[str] = None, area: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calcula métricas resumidas."""
        try:
            analyses = self.get_analysis_by_empresa_area(empresa, area)

            if not analyses:
                return {}

            total_employees = len(analyses)
            total_increase = sum(a["aumento_total"] for a in analyses)
            avg_increase_pct = sum(a["aumento_total_pct"] for a in analyses) / total_employees if total_employees > 0 else 0

            return {
                "total_empleados": total_employees,
                "aumento_total_invertido": total_increase,
                "aumento_promedio_pct": avg_increase_pct,
                "aumento_promedio_monto": total_increase / total_employees if total_employees > 0 else 0,
                "empleado_mayor_aumento": max(analyses, key=lambda x: x["aumento_total"]) if analyses else None,
                "empleado_menor_aumento": min(analyses, key=lambda x: x["aumento_total"]) if analyses else None,
            }

        except Exception as e:
            logger.error(f"Error calculando métricas: {e}")
            return {}

    def clear_data(self) -> bool:
        """Limpia todos los datos de la BD."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM salary_periods")
                cursor.execute("DELETE FROM employee_analysis")
                conn.commit()
                logger.info("Base de datos limpiada")
                return True
        except Exception as e:
            logger.error(f"Error limpiando BD: {e}")
            return False

    def upsert_ipc(self, mes: str, valor_ipc: float) -> bool:
        """Inserta o actualiza un valor de IPC."""
        try:
            from datetime import datetime

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO ipc_history (mes, valor_ipc, fecha_creacion, fecha_actualizacion)
                    VALUES (?, ?, ?, ?)
                    """,
                    (mes, valor_ipc, datetime.now().isoformat(), datetime.now().isoformat())
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error insertando IPC: {e}")
            return False

    def get_ipc_history(self) -> List[Dict[str, Any]]:
        """Obtiene el historial de IPC."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT mes, valor_ipc FROM ipc_history ORDER BY mes DESC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo IPC: {e}")
            return []

    def get_ipc(self, mes: str) -> Optional[float]:
        """Obtiene el IPC para un mes específico (formato YYYY-MM)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT valor_ipc FROM ipc_history WHERE mes = ?", (mes,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error obteniendo IPC: {e}")
            return None

    def upsert_compensation_level(self, nivel: int, mercado_financiero: float = None, mercado_seguros: float = None, descripcion: str = None) -> bool:
        """Inserta o actualiza un nivel de compensación."""
        try:
            from datetime import datetime

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO compensation_levels (nivel, mercado_financiero, mercado_seguros, descripcion, fecha_creacion, fecha_actualizacion)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (nivel, mercado_financiero, mercado_seguros, descripcion, datetime.now().isoformat(), datetime.now().isoformat())
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error insertando compensación: {e}")
            return False

    def get_compensation_levels(self) -> List[Dict[str, Any]]:
        """Obtiene todos los niveles de compensación."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM compensation_levels ORDER BY nivel ASC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo compensaciones: {e}")
            return []

    def get_compensation_by_level(self, nivel: int) -> Optional[Dict[str, Any]]:
        """Obtiene compensación por nivel específico."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM compensation_levels WHERE nivel = ?", (nivel,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error obteniendo compensación: {e}")
            return None

    def upsert_uf(self, mes: str, valor_uf: float) -> bool:
        """Inserta o actualiza un valor de UF."""
        try:
            from datetime import datetime

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO uf_history (mes, valor_uf, fecha_creacion, fecha_actualizacion)
                    VALUES (?, ?, ?, ?)
                    """,
                    (mes, valor_uf, datetime.now().isoformat(), datetime.now().isoformat())
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error insertando UF: {e}")
            return False

    def get_uf(self, mes: str) -> Optional[float]:
        """Obtiene el UF para un mes específico (formato YYYY-MM)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT valor_uf FROM uf_history WHERE mes = ?", (mes,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error obteniendo UF: {e}")
            return None

    def get_uf_history(self) -> List[Dict[str, Any]]:
        """Obtiene el historial de UF."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT mes, valor_uf FROM uf_history ORDER BY mes DESC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo historial UF: {e}")
            return []

    def upsert_compensation_average(
        self,
        nivel_hay: str,
        cantidad_empleados: int,
        promedio_anualizado: float,
        minimo_anualizado: float,
        maximo_anualizado: float,
        desviacion_std: float
    ) -> bool:
        """Inserta o actualiza promedio de compensación por nivel HAY."""
        try:
            from datetime import datetime

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO compensation_averages
                    (nivel_hay, cantidad_empleados, promedio_anualizado, minimo_anualizado,
                     maximo_anualizado, desviacion_std, fecha_calculo, fecha_actualizacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        nivel_hay,
                        cantidad_empleados,
                        promedio_anualizado,
                        minimo_anualizado,
                        maximo_anualizado,
                        desviacion_std,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    )
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error insertando promedio de compensación: {e}")
            return False

    def get_compensation_averages(self) -> List[Dict[str, Any]]:
        """Obtiene todos los promedios de compensación por nivel."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT nivel_hay, cantidad_empleados, promedio_anualizado, minimo_anualizado, "
                    "maximo_anualizado, desviacion_std, fecha_calculo FROM compensation_averages "
                    "ORDER BY CAST(nivel_hay AS INTEGER) ASC"
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo promedios de compensación: {e}")
            return []

    def get_compensation_average_by_level(self, nivel_hay: str) -> Optional[Dict[str, Any]]:
        """Obtiene promedio de compensación para un nivel HAY específico."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT nivel_hay, cantidad_empleados, promedio_anualizado, minimo_anualizado, "
                    "maximo_anualizado, desviacion_std FROM compensation_averages WHERE nivel_hay = ?",
                    (nivel_hay,)
                )
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error obteniendo promedio de compensación: {e}")
            return None

    def save_manual_values(self, rut: str, nivel_hay: Optional[str], target: Optional[str]) -> bool:
        """Guarda valores manuales de Nivel HAY y Target para un empleado."""
        try:
            from datetime import datetime

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO employee_manual_values (
                        rut, nivel_hay_manual, target_manual, fecha_creacion, fecha_actualizacion
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (rut, nivel_hay, target, now, now)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error guardando valores manuales: {e}")
            return False

    def get_manual_values(self, rut: str) -> Optional[Dict[str, Any]]:
        """Obtiene valores manuales de un empleado."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT rut, nivel_hay_manual, target_manual FROM employee_manual_values WHERE rut = ?",
                    (rut,)
                )
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error obteniendo valores manuales: {e}")
            return None

    def get_all_manual_values(self) -> List[Dict[str, Any]]:
        """Obtiene todos los valores manuales guardados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT rut, nivel_hay_manual, target_manual, fecha_actualizacion FROM employee_manual_values ORDER BY fecha_actualizacion DESC"
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo valores manuales: {e}")
            return []

    def save_compensation_proposal(self, rut: str, empleado_nombre: str,
                                   actual: Dict[str, Any], propuesta: Dict[str, Any],
                                   cambio_comp: float, cambio_comp_pct: float,
                                   comentarios: str = "", pdf_path: str = "") -> bool:
        """Guarda una propuesta de compensación."""
        try:
            from datetime import datetime

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                cursor.execute(
                    """
                    INSERT INTO compensation_proposals (
                        rut, empleado_nombre, fecha_propuesta,
                        actual_base_salary, actual_target_rentas, actual_nivel_hay, actual_mercado, actual_annual_comp,
                        propuesta_base_salary, propuesta_target_rentas, propuesta_nivel_hay, propuesta_mercado, propuesta_annual_comp,
                        cambio_comp, cambio_comp_pct, comentarios, pdf_path,
                        fecha_creacion, fecha_actualizacion
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rut, empleado_nombre, now,
                        actual.get("base_salary"), actual.get("target_rentas"),
                        actual.get("nivel_hay"), actual.get("mercado"), actual.get("annual_compensation"),
                        propuesta.get("base_salary"), propuesta.get("target_rentas"),
                        propuesta.get("nivel_hay"), propuesta.get("mercado"), propuesta.get("annual_compensation"),
                        cambio_comp, cambio_comp_pct, comentarios, pdf_path,
                        now, now
                    )
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error guardando propuesta de compensación: {e}")
            return False

    def get_compensation_proposals(self, rut: str = None) -> List[Dict[str, Any]]:
        """Obtiene propuestas de compensación."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if rut:
                    cursor.execute(
                        "SELECT * FROM compensation_proposals WHERE rut = ? ORDER BY fecha_creacion DESC",
                        (rut,)
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM compensation_proposals ORDER BY fecha_creacion DESC"
                    )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error obteniendo propuestas: {e}")
            return []
