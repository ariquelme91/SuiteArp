"""
Motor de cálculo de compensaciones.
"""

from typing import Dict, Any, Optional
from src.analysis.db_manager import AnalysisDBManager


class CompensationCalculator:
    """Calcula compensaciones basadas en componentes."""

    # Constantes de fórmulas
    GRATIFICATION_PERCENT = 0.25  # Gratificación = 25% del sueldo (con tope)
    GRATIFICATION_TOPE_FACTOR = 4.75  # Tope = IMM * 4.75
    COLACION_FIXED_MONTHLY = 130_000  # Colación fija mensual
    MOBILIZATION_MULTIPLIER = 2.44  # Movilización = 2.44 * UF (mensual)

    def __init__(self, db_manager: AnalysisDBManager, imm_value: float = 553_553):
        """
        Inicializa el calculador.

        Args:
            db_manager: Gestor de BD
            imm_value: Valor del IMM para calcular tope de gratificación
        """
        self.db_manager = db_manager
        self.imm_value = imm_value

    def calcular_componentes(
        self,
        sueldo_base: float,
        target: float,
        mes: str,
        incluir_target: bool = True
    ) -> Dict[str, float]:
        """
        Calcula los componentes de compensación (anualizados).

        Args:
            sueldo_base: Sueldo base MENSUAL del empleado
            target: Target (multiplicador, ej: 5.5 = 550%)
            mes: Mes en formato YYYY-MM para obtener UF
            incluir_target: Si incluir el target en el total

        Returns:
            Dict con desglose mensual y total anualizado
        """
        # Obtener UF del mes
        uf = self.db_manager.get_uf(mes)
        if uf is None:
            raise ValueError(f"No hay UF registrada para el mes {mes}")

        # === CÁLCULOS MENSUALES ===
        # Gratificación = MIN(25% sueldo, IMM * 4.75/12)
        gratificacion_sin_tope = sueldo_base * self.GRATIFICATION_PERCENT
        tope_gratificacion = (self.imm_value * self.GRATIFICATION_TOPE_FACTOR) / 12
        gratificacion_mensual = min(gratificacion_sin_tope, tope_gratificacion)

        # Colación y Movilización (mensuales)
        colacion_mensual = self.COLACION_FIXED_MONTHLY
        movilizacion_mensual = self.MOBILIZATION_MULTIPLIER * uf

        # === CÁLCULOS ANUALES ===
        sueldo_anual = sueldo_base * 12
        gratificacion_anual = gratificacion_mensual * 12
        colacion_anual = colacion_mensual * 12
        movilizacion_anual = movilizacion_mensual * 12
        target_amount = sueldo_base * target  # Ya está anualizado (sueldo_base es mensual)

        # Total anual
        total_anual = sueldo_anual + gratificacion_anual + colacion_anual + movilizacion_anual
        if incluir_target:
            total_anual += target_amount

        return {
            # Desglose mensual (para mostrar)
            "sueldo_base": round(sueldo_base, 2),
            "gratificacion": round(gratificacion_mensual, 2),
            "colacion": round(colacion_mensual, 2),
            "movilizacion": round(movilizacion_mensual, 2),

            # Anuales (para cálculos y comparativa)
            "sueldo_anual": round(sueldo_anual, 2),
            "gratificacion_anual": round(gratificacion_anual, 2),
            "colacion_anual": round(colacion_anual, 2),
            "movilizacion_anual": round(movilizacion_anual, 2),
            "target": round(target_amount, 2) if incluir_target else 0,

            # Total anualizado
            "total": round(total_anual, 2),
            "uf_usado": round(uf, 2),
            "tope_gratificacion": round(tope_gratificacion, 2)
        }

    def comparar_con_mercado(
        self,
        compensacion_calculada: float,
        nivel_actual: int,
        mercado: str = "mercado_seguros",
        sueldo_base: float = 0,
        target: float = 0,
        uf_valor: float = 40873.77
    ) -> Dict[str, Any]:
        """
        Compara compensación con referencia de mercado.
        Separa imponibles (Sueldo + Target) de no imponibles (Colación, Movilización).

        Args:
            compensacion_calculada: Total de compensación (todos los componentes)
            nivel_actual: Nivel HAY actual
            mercado: "mercado_financiero" o "mercado_seguros"
            sueldo_base: Sueldo base mensual (para cálculo de Total Cash)
            target: Target en rentas (para cálculo de Total Cash)
            uf_valor: Valor de UF para haberes no imponibles

        Returns:
            Dict con comparativa y desglose
        """
        nivel_key = "mercado_financiero" if "financiero" in mercado.lower() else "mercado_seguros"

        # Obtener referencia de mercado
        info_nivel = self.db_manager.get_compensation_by_level(nivel_actual)
        if not info_nivel:
            raise ValueError(f"No hay datos para el nivel {nivel_actual}")

        valor_nivel = info_nivel.get(nivel_key) or 0

        # SEPARACIÓN DE COMPONENTES (metodología Hay)
        # Total Cash (imponibles): Sueldo Base + Target
        total_cash_anual = (sueldo_base * 12) + target

        # Haberes no imponibles: Colación + Movilización (no se comparan en metodología Hay)
        colacion_anual = self.COLACION_FIXED_MONTHLY * 12
        movilizacion_anual = self.MOBILIZATION_MULTIPLIER * uf_valor * 12
        haberes_no_imponibles = colacion_anual + movilizacion_anual

        # COMPA RATIO: Usa Total Cash (metodología estándar Hay)
        compa_ratio = (total_cash_anual / valor_nivel) * 100 if valor_nivel > 0 else 0

        # Matriz de percentiles
        p25_valor = valor_nivel * 0.80
        p50_valor = valor_nivel
        p75_valor = valor_nivel * 1.20

        # POSICIÓN EN BANDA: Penetración real en la escala P25-P75
        # Fórmula: (Actual - Mín) / (Máx - Mín) × 100
        rango = p75_valor - p25_valor
        posicion_en_banda_pct = ((total_cash_anual - p25_valor) / rango) * 100 if rango > 0 else 50
        # Clampar entre 0 y 100
        posicion_en_banda_pct = max(0, min(100, posicion_en_banda_pct))

        # Determinar banda y estado
        if compa_ratio < 90:
            estado = "🔴 BAJO MERCADO"
            banda = "Bajo (80-90%)"
            color = "red"
        elif compa_ratio <= 105:
            estado = "🟢 EN BANDA"
            banda = "Competitivo (90-105%)"
            color = "green"
        else:
            estado = "🔵 SOBRE PAGADO"
            banda = "Premium (105%+)"
            color = "blue"

        # Salary Spread
        salary_spread = ((p75_valor - p25_valor) / p50_valor) * 100

        # Cálculo de incremento sugerido para entrar en banda
        incremento_recomendado = 0
        if compa_ratio < 90:
            target_ratio = 92.5  # Mitad de banda
            incremento_recomendado = (target_ratio - compa_ratio) * (valor_nivel / 100)
            recomendacion = f"Incremento de ${incremento_recomendado:,.0f} anual"
            prioridad = "ALTA"
        elif compa_ratio < 95:
            incremento_recomendado = ((95 - compa_ratio) * (valor_nivel / 100))
            recomendacion = f"Incremento de ${incremento_recomendado:,.0f} anual"
            prioridad = "MEDIA"
        elif compa_ratio <= 105:
            incremento_recomendado = 0
            recomendacion = "Mantener (dentro de banda)"
            prioridad = "BAJA"
        else:
            incremento_recomendado = 0
            recomendacion = "Revisar estructura"
            prioridad = "MEDIA"

        return {
            "nivel_encontrado": nivel_actual,
            "valor_nivel": round(valor_nivel, 2),
            "compensacion_calculada": round(compensacion_calculada, 2),
            # Desglose de componentes
            "total_cash_anual": round(total_cash_anual, 2),
            "haberes_no_imponibles": round(haberes_no_imponibles, 2),
            "colacion_anual": round(colacion_anual, 2),
            "movilizacion_anual": round(movilizacion_anual, 2),
            # Análisis
            "compa_ratio": round(compa_ratio, 2),
            "posicion_en_banda_pct": round(posicion_en_banda_pct, 2),
            "incremento_recomendado": round(incremento_recomendado, 2),
            "estado": estado,
            "banda": banda,
            "color": color,
            "descripcion_nivel": info_nivel.get("descripcion", ""),
            "mercado": mercado,
            # Percentiles
            "p25": round(p25_valor, 2),
            "p50": round(p50_valor, 2),
            "p75": round(p75_valor, 2),
            "salary_spread": round(salary_spread, 2),
            "recomendacion": recomendacion,
            "prioridad": prioridad
        }

    def comparativa_completa(
        self,
        sueldo_base: float,
        nivel_actual: int,
        target: float,
        mes: str,
        mercado: str = "mercado_seguros"
    ) -> Dict[str, Any]:
        """
        Realiza análisis completo de compensación con desglose de componentes.
        """
        # Calcular componentes
        componentes = self.calcular_componentes(sueldo_base, target, mes)

        # Obtener UF para análisis
        uf_valor = self.db_manager.get_uf(mes) or 40873.77

        # Comparar con mercado (pasando sueldo_base y target para desglose correcto)
        comparativa = self.comparar_con_mercado(
            compensacion_calculada=componentes["total"],
            nivel_actual=nivel_actual,
            mercado=mercado,
            sueldo_base=sueldo_base,
            target=target,
            uf_valor=uf_valor
        )

        # Combinar resultados
        return {
            **componentes,
            **comparativa
        }
