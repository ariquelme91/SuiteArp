"""
Módulo para análisis de competitividad interna por nivel HAY.
Calcula promedios de compensación basándose en empleados cargados.
"""

from typing import Dict, List, Any, Optional
from src.analysis.db_manager import AnalysisDBManager
from src.analysis.compensation_calculator import CompensationCalculator
from datetime import datetime
import statistics
import json


class InternalCompetitivenessCalculator:
    """Calcula y administra promedios de compensación por nivel HAY."""

    def __init__(self, db_manager: AnalysisDBManager, imm_value: float = 553_553):
        """
        Inicializa el calculador.

        Args:
            db_manager: Gestor de BD
            imm_value: Valor del IMM para cálculos
        """
        self.db_manager = db_manager
        self.imm_value = imm_value
        self.calculator = CompensationCalculator(db_manager, imm_value=imm_value)

    def calcular_promedios(self, mes: str = None, empresa: str = None) -> Dict[str, Any]:
        """
        Calcula promedios de compensación para cada nivel HAY.

        Args:
            mes: Mes en formato YYYY-MM (si no se proporciona, usa mes actual)
            empresa: Empresa específica para filtrar (si no se proporciona, usa todas)

        Returns:
            Dict con resultados por nivel
        """
        if mes is None:
            mes = datetime.now().strftime("%Y-%m")

        # Obtener empleados (filtrados por empresa si se especifica)
        empleados = self.db_manager.get_analysis_by_empresa_area(empresa=empresa)

        if not empleados:
            return {"error": "No hay empleados cargados"}

        # Agrupar por nivel HAY
        por_nivel = {}
        for emp in empleados:
            nivel = emp.get("nivel_hay")
            if not nivel:
                continue

            nivel_str = str(nivel)
            if nivel_str not in por_nivel:
                por_nivel[nivel_str] = []

            # Calcular compensación total anualizada para este empleado
            try:
                sueldo_base = emp.get("sueldo_actual", 0)
                target = float(emp.get("target", 1.0))

                if sueldo_base <= 0:
                    continue

                componentes = self.calculator.calcular_componentes(
                    sueldo_base=sueldo_base,
                    target=target,
                    mes=mes,
                    incluir_target=True
                )

                por_nivel[nivel_str].append({
                    "rut": emp.get("rut"),
                    "nombre": emp.get("nombre"),
                    "compensacion_anual": componentes["total"]
                })

            except Exception as e:
                # Si falla el cálculo para un empleado, continuar
                continue

        # Calcular estadísticas por nivel
        resultados = {}
        for nivel, empleados_nivel in por_nivel.items():
            if not empleados_nivel:
                continue

            compensaciones = [e["compensacion_anual"] for e in empleados_nivel]

            resultados[nivel] = {
                "nivel_hay": nivel,
                "cantidad_empleados": len(empleados_nivel),
                "promedio_anualizado": round(statistics.median(compensaciones), 2),
                "minimo_anualizado": round(min(compensaciones), 2),
                "maximo_anualizado": round(max(compensaciones), 2),
                "desviacion_std": round(statistics.stdev(compensaciones), 2) if len(compensaciones) > 1 else 0,
                "empleados_detalle": empleados_nivel
            }

        return resultados

    def guardar_promedios(self, resultados: Dict[str, Any]) -> bool:
        """
        Guarda los promedios calculados en la BD.

        Args:
            resultados: Dict con resultados del método calcular_promedios()

        Returns:
            True si fue exitoso
        """
        try:
            guardados = 0
            for nivel, datos in resultados.items():
                if "error" in datos:
                    continue

                try:
                    success = self.db_manager.upsert_compensation_average(
                        nivel_hay=datos["nivel_hay"],
                        cantidad_empleados=datos["cantidad_empleados"],
                        promedio_anualizado=datos["promedio_anualizado"],
                        minimo_anualizado=datos["minimo_anualizado"],
                        maximo_anualizado=datos["maximo_anualizado"],
                        desviacion_std=datos["desviacion_std"]
                    )
                    if success:
                        guardados += 1
                except Exception as e:
                    print(f"Error guardando nivel {nivel}: {e}")
                    continue

            print(f"Guardados {guardados}/{len([d for d in resultados.values() if 'error' not in d])} promedios")
            return guardados > 0

        except Exception as e:
            print(f"Error guardando promedios: {e}")
            return False

    def comparar_empleado_vs_promedio(
        self,
        rut: str,
        nivel_hay: str,
        compensacion_anual: float
    ) -> Dict[str, Any]:
        """
        Compara la compensación de un empleado contra el promedio de su nivel.

        Args:
            rut: RUT del empleado
            nivel_hay: Nivel HAY del empleado
            compensacion_anual: Compensación anualizada del empleado

        Returns:
            Dict con análisis comparativo
        """
        promedio = self.db_manager.get_compensation_average_by_level(nivel_hay)

        if not promedio:
            return {
                "error": f"No hay promedio calculado para nivel {nivel_hay}",
                "empleado_anual": compensacion_anual
            }

        prom_valor = promedio["promedio_anualizado"]
        diferencia = compensacion_anual - prom_valor
        diferencia_pct = (diferencia / prom_valor * 100) if prom_valor > 0 else 0

        # Posición respecto a min/max
        rango = promedio["maximo_anualizado"] - promedio["minimo_anualizado"]
        posicion_en_rango = (
            (compensacion_anual - promedio["minimo_anualizado"]) / rango * 100
        ) if rango > 0 else 50

        # Análisis
        if compensacion_anual < promedio["minimo_anualizado"]:
            estado = "BAJO DEL RANGO"
            color = "red"
        elif compensacion_anual <= promedio["promedio_anualizado"]:
            estado = "BAJO PROMEDIO"
            color = "orange"
        elif compensacion_anual <= promedio["maximo_anualizado"]:
            estado = "SOBRE PROMEDIO"
            color = "lightgreen"
        else:
            estado = "SOBRE RANGO"
            color = "blue"

        return {
            "nivel_hay": nivel_hay,
            "empleado_anual": round(compensacion_anual, 2),
            "promedio_nivel": round(prom_valor, 2),
            "minimo_nivel": round(promedio["minimo_anualizado"], 2),
            "maximo_nivel": round(promedio["maximo_anualizado"], 2),
            "desviacion_std": round(promedio["desviacion_std"], 2),
            "diferencia": round(diferencia, 2),
            "diferencia_pct": round(diferencia_pct, 2),
            "posicion_en_rango_pct": round(posicion_en_rango, 2),
            "cantidad_empleados_en_nivel": promedio["cantidad_empleados"],
            "estado": estado,
            "color": color
        }
