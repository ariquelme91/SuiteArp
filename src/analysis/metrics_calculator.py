"""Calculador de métricas avanzadas de compensaciones."""

from typing import List, Dict, Any, Optional
import logging
from statistics import median, stdev

logger = logging.getLogger(__name__)


class AdvancedMetricsCalculator:
    """Calcula métricas avanzadas para análisis de compensaciones."""

    @staticmethod
    def calculate_metrics(analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcula todas las métricas avanzadas.

        Args:
            analyses: Lista de análisis de empleados

        Returns:
            Diccionario con métricas avanzadas
        """
        if not analyses:
            return {}

        try:
            total_employees = len(analyses)

            # Extracto valores relevantes
            aumentos_total = [float(a.get("aumento_total", 0)) for a in analyses]
            aumentos_pct = [float(a.get("aumento_total_pct", 0)) for a in analyses]
            meses_en_puesto = [int(a.get("meses_en_puesto", 0)) for a in analyses if a.get("meses_en_puesto")]
            sueldos_iniciales = [float(a.get("sueldo_inicial", 0)) for a in analyses]

            # 1. Impacto en Masa Salarial (%)
            masa_salarial_previa = sum(sueldos_iniciales)
            aumento_total_invertido = sum(aumentos_total)
            impacto_masa_salarial = (
                (aumento_total_invertido / masa_salarial_previa * 100)
                if masa_salarial_previa > 0
                else 0
            )

            # 2. Costo Anualizado del Ajuste ($)
            costo_anualizado = aumento_total_invertido * 12

            # 3. Concentración del Gasto (% Top 3)
            top_3_aumentos = sum(sorted(aumentos_total, reverse=True)[:3])
            concentracion_top_3 = (
                (top_3_aumentos / aumento_total_invertido * 100)
                if aumento_total_invertido > 0
                else 0
            )

            # 4. Tasa de Cobertura (%)
            empleados_con_aumento = sum(1 for a in aumentos_total if a > 0)
            tasa_cobertura = (empleados_con_aumento / total_employees * 100) if total_employees > 0 else 0

            # 5. Robustez Estadística
            mediana_aumento_monto = median(aumentos_total) if aumentos_total else 0
            mediana_aumento_pct = median(aumentos_pct) if aumentos_pct else 0

            # Percentiles
            aumentos_ordenados = sorted(aumentos_total)
            p25_idx = int(len(aumentos_ordenados) * 0.25)
            p75_idx = int(len(aumentos_ordenados) * 0.75)
            p25_aumento = aumentos_ordenados[p25_idx] if aumentos_ordenados else 0
            p75_aumento = aumentos_ordenados[p75_idx] if aumentos_ordenados else 0

            aumentos_pct_ordenados = sorted(aumentos_pct)
            p25_pct = aumentos_pct_ordenados[p25_idx] if aumentos_pct_ordenados else 0
            p75_pct = aumentos_pct_ordenados[p75_idx] if aumentos_pct_ordenados else 0

            # Desviación estándar
            desv_est_monto = stdev(aumentos_total) if len(aumentos_total) > 1 else 0
            desv_est_pct = stdev(aumentos_pct) if len(aumentos_pct) > 1 else 0

            # 6. Antigüedad Promedio del Último Aumento
            antigüedad_promedio_meses = (
                sum(meses_en_puesto) / len(meses_en_puesto)
                if meses_en_puesto
                else 0
            )

            return {
                "masa_salarial_previa": masa_salarial_previa,
                "aumento_total_invertido": aumento_total_invertido,
                "impacto_masa_salarial_pct": impacto_masa_salarial,
                "costo_anualizado": costo_anualizado,
                "concentracion_top_3_pct": concentracion_top_3,
                "tasa_cobertura_pct": tasa_cobertura,
                "mediana_aumento_monto": mediana_aumento_monto,
                "mediana_aumento_pct": mediana_aumento_pct,
                "p25_aumento_monto": p25_aumento,
                "p75_aumento_monto": p75_aumento,
                "p25_aumento_pct": p25_pct,
                "p75_aumento_pct": p75_pct,
                "desv_est_aumento_monto": desv_est_monto,
                "desv_est_aumento_pct": desv_est_pct,
                "antigüedad_promedio_meses_ultimo_aumento": antigüedad_promedio_meses,
                "total_empleados": total_employees,
                "empleados_con_aumento": empleados_con_aumento,
            }

        except Exception as e:
            logger.error(f"Error calculando métricas avanzadas: {e}")
            return {}
