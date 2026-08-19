"""Planificación y control de dotación por empresa y área.

El plan se guarda aparte de la dotación real: la real sale de
`employee_analysis` (lo que vino de Buk en la última carga) y el plan es
lo que define RR.HH. en `plan_dotacion`. Cruzar ambos da el control.

El costo de una posición no es el sueldo bruto: se calcula con
`PayrollEngine`, que suma gratificación legal y los aportes del empleador
(SIS, AFC y mutual).
"""

import logging
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

MERCADOS = ("Mercado Seguros", "Mercado Financiero")

# Estados del control de dotación.
COMPLETA = "Completa"
VACANTES = "Con vacantes"
SOBRE = "Sobredotación"


@dataclass
class CostoPosicion:
    """Costo mensual de una posición para la empresa."""
    sueldo_base: float
    costo_empresa: float          # bruto + gratificación + aportes patronales
    origen: str                   # "manual" | "banda" | "sin estimar"
    detalle: str = ""

    @property
    def estimable(self) -> bool:
        return self.origen != "sin estimar"


class DotacionManager:
    """Gestor del plan de dotación."""

    def __init__(self, db_manager, payroll_engine=None):
        """
        Args:
            db_manager: AnalysisDBManager, del que se toma la ruta de la BD.
            payroll_engine: PayrollEngine para costear. Si es None, el costo
                no se calcula y las posiciones quedan "sin estimar".
        """
        self.db_path = db_manager.db_path
        self.payroll = payroll_engine
        self._crear_tabla()

    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _crear_tabla(self):
        try:
            with self._conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS plan_dotacion (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        empresa TEXT NOT NULL,
                        area TEXT NOT NULL,
                        cargo TEXT NOT NULL,
                        nivel_hay TEXT,
                        cantidad INTEGER NOT NULL DEFAULT 1,
                        sueldo_referencia REAL,
                        target_rentas REAL DEFAULT 0,
                        mercado TEXT DEFAULT 'Mercado Seguros',
                        periodo TEXT NOT NULL,
                        notas TEXT,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(empresa, area, cargo, periodo)
                    )
                """)
        except sqlite3.Error as e:
            logger.error(f"Creando plan_dotacion: {e}")

    # ------------------------------------------------------------------
    # Plan
    # ------------------------------------------------------------------

    def guardar_posicion(self, empresa: str, area: str, cargo: str, cantidad: int,
                         periodo: str, nivel_hay: str = None,
                         sueldo_referencia: float = None, target_rentas: float = 0,
                         mercado: str = "Mercado Seguros",
                         notas: str = None) -> tuple:
        """Crea o actualiza una línea del plan.

        La combinación empresa+área+cargo+período es única: volver a guardar
        la misma reemplaza la cantidad en vez de duplicar la línea.
        """
        if not empresa or not area or not cargo:
            return False, "Empresa, área y cargo son obligatorios"
        if cantidad < 1:
            return False, "La cantidad debe ser al menos 1"

        try:
            with self._conn() as conn:
                conn.execute("""
                    INSERT INTO plan_dotacion
                        (empresa, area, cargo, nivel_hay, cantidad, sueldo_referencia,
                         target_rentas, mercado, periodo, notas)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(empresa, area, cargo, periodo) DO UPDATE SET
                        nivel_hay = excluded.nivel_hay,
                        cantidad = excluded.cantidad,
                        sueldo_referencia = excluded.sueldo_referencia,
                        target_rentas = excluded.target_rentas,
                        mercado = excluded.mercado,
                        notas = excluded.notas,
                        fecha_actualizacion = CURRENT_TIMESTAMP
                """, (empresa, area, cargo, nivel_hay, cantidad, sueldo_referencia,
                      target_rentas, mercado, periodo, notas))
            return True, f"Posición '{cargo}' guardada en {area}"
        except sqlite3.Error as e:
            logger.error(f"Guardando posición: {e}")
            return False, f"Error: {e}"

    def eliminar_posicion(self, posicion_id: int) -> tuple:
        try:
            with self._conn() as conn:
                cur = conn.execute("DELETE FROM plan_dotacion WHERE id = ?", (posicion_id,))
            if cur.rowcount == 0:
                return False, "La posición ya no existe"
            return True, "Posición eliminada del plan"
        except sqlite3.Error as e:
            logger.error(f"Eliminando posición: {e}")
            return False, f"Error: {e}"

    def obtener_plan(self, empresa: str, periodo: str) -> List[Dict]:
        try:
            with self._conn() as conn:
                filas = conn.execute("""
                    SELECT * FROM plan_dotacion
                    WHERE empresa = ? AND periodo = ?
                    ORDER BY area, cargo
                """, (empresa, periodo)).fetchall()
            return [dict(f) for f in filas]
        except sqlite3.Error as e:
            logger.error(f"Leyendo plan: {e}")
            return []

    def periodos_disponibles(self, empresa: str) -> List[str]:
        try:
            with self._conn() as conn:
                filas = conn.execute(
                    "SELECT DISTINCT periodo FROM plan_dotacion WHERE empresa = ? "
                    "ORDER BY periodo DESC", (empresa,)).fetchall()
            return [f[0] for f in filas]
        except sqlite3.Error:
            return []

    # ------------------------------------------------------------------
    # Dotación real (desde la última carga de Buk)
    # ------------------------------------------------------------------

    def dotacion_real(self, empresa: str) -> Dict[str, int]:
        """Personas por área."""
        try:
            with self._conn() as conn:
                filas = conn.execute("""
                    SELECT area, COUNT(*) n FROM employee_analysis
                    WHERE empresa = ? GROUP BY area
                """, (empresa,)).fetchall()
            return {f["area"]: f["n"] for f in filas}
        except sqlite3.Error as e:
            logger.error(f"Leyendo dotación real: {e}")
            return {}

    def dotacion_real_por_cargo(self, empresa: str) -> Dict[tuple, int]:
        """Personas por (área, cargo)."""
        try:
            with self._conn() as conn:
                filas = conn.execute("""
                    SELECT area, cargo_actual, COUNT(*) n FROM employee_analysis
                    WHERE empresa = ? GROUP BY area, cargo_actual
                """, (empresa,)).fetchall()
            return {(f["area"], f["cargo_actual"]): f["n"] for f in filas}
        except sqlite3.Error as e:
            logger.error(f"Leyendo dotación por cargo: {e}")
            return {}

    def areas_de(self, empresa: str) -> List[str]:
        try:
            with self._conn() as conn:
                filas = conn.execute(
                    "SELECT DISTINCT area FROM employee_analysis "
                    "WHERE empresa = ? AND area IS NOT NULL ORDER BY area",
                    (empresa,)).fetchall()
            return [f[0] for f in filas]
        except sqlite3.Error:
            return []

    def cargos_de(self, empresa: str, area: str = None) -> List[str]:
        try:
            sql = ("SELECT DISTINCT cargo_actual FROM employee_analysis "
                   "WHERE empresa = ? AND cargo_actual IS NOT NULL")
            params = [empresa]
            if area:
                sql += " AND area = ?"
                params.append(area)
            with self._conn() as conn:
                filas = conn.execute(sql + " ORDER BY cargo_actual", params).fetchall()
            return [f[0] for f in filas]
        except sqlite3.Error:
            return []

    def niveles_hay_de(self, empresa: str, area: str, cargo: str) -> Optional[str]:
        """Nivel HAY más frecuente entre quienes ya ocupan ese cargo.

        Sirve para proponer un nivel al planificar una posición nueva.
        """
        try:
            with self._conn() as conn:
                fila = conn.execute("""
                    SELECT nivel_hay, COUNT(*) n FROM employee_analysis
                    WHERE empresa = ? AND area = ? AND cargo_actual = ?
                      AND nivel_hay IS NOT NULL
                      AND TRIM(CAST(nivel_hay AS TEXT)) NOT IN ('', 'None', '0')
                    GROUP BY nivel_hay ORDER BY n DESC LIMIT 1
                """, (empresa, area, cargo)).fetchone()
            return str(fila["nivel_hay"]) if fila else None
        except sqlite3.Error:
            return None

    # ------------------------------------------------------------------
    # Costeo
    # ------------------------------------------------------------------

    def _mediana_nivel(self, nivel_hay: str, mercado: str) -> Optional[float]:
        """Compensación anual mediana del nivel HAY en ese mercado."""
        if not nivel_hay:
            return None
        columna = "mercado_financiero" if "Financiero" in (mercado or "") else "mercado_seguros"
        try:
            with self._conn() as conn:
                fila = conn.execute(
                    f"SELECT {columna} FROM compensation_levels WHERE nivel = ?",
                    (str(nivel_hay),)).fetchone()
            return float(fila[0]) if fila and fila[0] else None
        except (sqlite3.Error, TypeError, ValueError):
            return None

    def costo_posicion(self, nivel_hay: str = None, mercado: str = "Mercado Seguros",
                       target_rentas: float = 0, sueldo_referencia: float = None,
                       colacion: float = 0, movilizacion: float = 0) -> CostoPosicion:
        """Costo mensual para la empresa de una posición.

        El sueldo base sale de dos fuentes, en este orden:

        1. `sueldo_referencia`, si RR.HH. ya definió cuánto pagará.
        2. La banda de mercado del nivel HAY. Como la banda está expresada
           en compensación anual y ésta es `base × (12 + target)`, se
           invierte esa fórmula para llegar al sueldo base mensual.
        """
        if sueldo_referencia and sueldo_referencia > 0:
            base = float(sueldo_referencia)
            origen, detalle = "manual", "Sueldo definido manualmente"
        else:
            mediana = self._mediana_nivel(nivel_hay, mercado)
            if not mediana:
                return CostoPosicion(0, 0, "sin estimar",
                                     "Sin nivel HAY ni sueldo de referencia")
            meses = 12 + float(target_rentas or 0)
            base = mediana / meses
            detalle = (f"Mediana {mercado} nivel {nivel_hay}: "
                       f"${mediana:,.0f} anual / {meses:g} rentas")
            origen = "banda"

        if self.payroll is None:
            return CostoPosicion(base, 0, "sin estimar", "Motor de nómina no disponible")

        try:
            liq = self.payroll.calculate(
                base_salary=base, collation=colacion, mobility=movilizacion,
                contract_type="indefinido",
            )
            return CostoPosicion(base, liq.total_employer_cost, origen, detalle)
        except Exception as e:
            logger.error(f"Costeando posición: {e}")
            return CostoPosicion(base, 0, "sin estimar", f"Error de cálculo: {e}")

    def costo_nomina_actual(self, empresa: str) -> Dict:
        """Costo empresa de la dotación que ya está trabajando.

        Se calcula sobre `sueldo_actual` de cada persona con el mismo criterio
        que las vacantes (base + gratificación legal + aportes patronales),
        para que ambas cifras sean sumables.

        Los datos de Buk no traen colación ni movilización, así que quedan
        fuera de los dos lados por igual.
        """
        vacio = {"total": 0.0, "por_area": {}, "personas": 0, "sin_sueldo": 0}
        if self.payroll is None:
            return vacio

        try:
            with self._conn() as conn:
                filas = conn.execute("""
                    SELECT area, sueldo_actual FROM employee_analysis
                    WHERE empresa = ?
                """, (empresa,)).fetchall()
        except sqlite3.Error as e:
            logger.error(f"Leyendo sueldos: {e}")
            return vacio

        por_area, total, personas, sin_sueldo = {}, 0.0, 0, 0
        # Sueldos repetidos son frecuentes (bandas), así que se cachea el
        # cálculo por monto en vez de rehacerlo por persona.
        cache: Dict[float, float] = {}

        for fila in filas:
            base = fila["sueldo_actual"]
            if not base or base <= 0:
                sin_sueldo += 1
                continue

            base = float(base)
            if base not in cache:
                try:
                    cache[base] = self.payroll.calculate(
                        base_salary=base, contract_type="indefinido"
                    ).total_employer_cost
                except Exception as e:
                    logger.error(f"Costeando sueldo {base}: {e}")
                    cache[base] = 0.0

            costo = cache[base]
            por_area[fila["area"]] = por_area.get(fila["area"], 0.0) + costo
            total += costo
            personas += 1

        return {"total": total, "por_area": por_area,
                "personas": personas, "sin_sueldo": sin_sueldo}

    # ------------------------------------------------------------------
    # Control: plan contra realidad
    # ------------------------------------------------------------------

    def control_por_area(self, empresa: str, periodo: str) -> List[Dict]:
        """Compara plan y realidad por área.

        Incluye las áreas que existen hoy aunque no estén en el plan: si
        alguien no planificó un área que sí tiene gente, eso también es
        información que hay que ver.
        """
        plan = self.obtener_plan(empresa, periodo)
        real = self.dotacion_real(empresa)

        planificado, posiciones = {}, {}
        for p in plan:
            planificado[p["area"]] = planificado.get(p["area"], 0) + p["cantidad"]
            posiciones.setdefault(p["area"], []).append(p)

        filas = []
        for area in sorted(set(planificado) | set(real)):
            plan_area = planificado.get(area, 0)
            real_area = real.get(area, 0)
            brecha = plan_area - real_area

            if plan_area == 0:
                estado = "Sin planificar"
            elif brecha > 0:
                estado = VACANTES
            elif brecha < 0:
                estado = SOBRE
            else:
                estado = COMPLETA

            filas.append({
                "area": area,
                "planificado": plan_area,
                "real": real_area,
                "vacantes": max(0, brecha),
                "exceso": max(0, -brecha),
                "estado": estado,
                "posiciones": posiciones.get(area, []),
            })
        return filas

    def vacantes_detalladas(self, empresa: str, periodo: str) -> List[Dict]:
        """Vacantes por cargo, cada una con su costo estimado.

        La vacante se calcula a nivel de cargo, no de área: un área puede
        estar completa en número y aun así faltarle un cargo concreto
        mientras le sobra otro.
        """
        plan = self.obtener_plan(empresa, periodo)
        real = self.dotacion_real_por_cargo(empresa)

        detalle = []
        for p in plan:
            ocupadas = real.get((p["area"], p["cargo"]), 0)
            faltan = p["cantidad"] - ocupadas
            if faltan <= 0:
                continue

            costo = self.costo_posicion(
                nivel_hay=p["nivel_hay"], mercado=p["mercado"],
                target_rentas=p["target_rentas"] or 0,
                sueldo_referencia=p["sueldo_referencia"],
            )
            detalle.append({
                "id": p["id"], "area": p["area"], "cargo": p["cargo"],
                "nivel_hay": p["nivel_hay"], "planificado": p["cantidad"],
                "ocupadas": ocupadas, "vacantes": faltan,
                "sueldo_base": costo.sueldo_base,
                "costo_unitario": costo.costo_empresa,
                "costo_total": costo.costo_empresa * faltan,
                "origen": costo.origen, "detalle_costo": costo.detalle,
            })
        return detalle

    def resumen(self, empresa: str, periodo: str) -> Dict:
        """Cifras de cabecera para el panel.

        Incluye las tres cifras de costo que interesan juntas: lo que ya se
        paga hoy, lo que sumaría cubrir el plan, y el total proyectado.
        """
        control = self.control_por_area(empresa, periodo)
        vacantes = self.vacantes_detalladas(empresa, periodo)
        nomina = self.costo_nomina_actual(empresa)

        costo_vacantes = sum(v["costo_total"] for v in vacantes)
        costo_actual = nomina["total"]
        costo_total = costo_actual + costo_vacantes
        sin_estimar = sum(v["vacantes"] for v in vacantes if v["origen"] == "sin estimar")

        return {
            "planificado": sum(f["planificado"] for f in control),
            "real": sum(f["real"] for f in control),
            "vacantes": sum(v["vacantes"] for v in vacantes),
            "exceso": sum(f["exceso"] for f in control),
            "areas": len(control),
            "costo_actual": costo_actual,
            "costo_vacantes": costo_vacantes,
            "costo_total": costo_total,
            "costo_total_anual": costo_total * 12,
            "variacion_pct": (costo_vacantes / costo_actual * 100) if costo_actual else 0.0,
            "costo_por_area": nomina["por_area"],
            "personas_costeadas": nomina["personas"],
            "sin_sueldo": nomina["sin_sueldo"],
            "vacantes_sin_estimar": sin_estimar,
        }
