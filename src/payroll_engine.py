"""Motor de cálculo de nómina chilena."""

import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PayrollCalculation:
    """Resultado del cálculo de nómina."""
    # Haberes
    base_salary: float
    gratification: float
    collation: float
    mobility: float
    other_taxable: float
    other_non_taxable: float
    total_taxable: float
    total_non_taxable: float
    total_earnings: float

    # Descuentos
    afp_discount: float
    health_discount: float
    afc_discount: float  # Seguro de Cesantía
    income_tax: float  # Impuesto a la Renta de Segunda Categoría
    other_discounts: float
    total_discounts: float

    # Sueldo líquido
    net_salary: float

    # Costos empresa
    employer_sis: float
    employer_afc: float
    employer_mutual: float
    total_employer_cost: float

    # Detalle adicional
    taxable_base: float
    afp_taxable_base: float
    afc_taxable_base: float


class PayrollEngine:
    """Motor de cálculo de nómina chilena con normativa vigente."""

    # Tasas de AFP vigentes en Chile (incluyen fondo 10% + comisión)
    AFP_RATES = {
        "capital": 11.44,
        "cuprum": 11.44,
        "habitat": 11.27,
        "planvital": 11.16,
        "provida": 11.45,
        "modelo": 10.58,
        "uno": 10.46,
    }

    def __init__(self, parameters: Dict):
        """
        Inicializa motor con parámetros mensuales.

        Args:
            parameters: Dict con UF, UTM, topes, tasas, tabla de impuesto
        """
        self.uf_value = parameters.get("uf_value", 40873.77)
        self.utm_value = parameters.get("utm_value", 67000)
        self.imm_value = parameters.get("imm_value", 500000)
        self.tope_afp_uf = parameters.get("tope_afp_uf", 90.0)
        self.tope_afc_uf = parameters.get("tope_afc_uf", 126.6)
        self.afp_percent = parameters.get("afp_percent", 10.0)
        self.salud_percent = parameters.get("salud_percent", 7.0)
        self.afc_trabajador_indefinido = parameters.get("afc_trabajador_indefinido", 0.6)
        self.afc_trabajador_plazo_fijo = parameters.get("afc_trabajador_plazo_fijo", 0.0)
        self.afc_empleador_indefinido = parameters.get("afc_empleador_indefinido", 2.4)
        self.afc_empleador_plazo_fijo = parameters.get("afc_empleador_plazo_fijo", 3.0)
        self.sis_percent = parameters.get("sis_percent", 1.49)
        self.tasa_mutual_base = parameters.get("tasa_mutual_base", 0.93)
        self.gratificacion_max_percent = parameters.get("gratificacion_max_percent", 25.0)
        self.tabla_impuesto = parameters.get("tabla_impuesto_unico", [])

        # Calcular topes en pesos
        self.tope_afp_pesos = self.tope_afp_uf * self.uf_value
        self.tope_afc_pesos = self.tope_afc_uf * self.uf_value

    def calculate(
        self,
        base_salary: float,
        collation: float = 0,
        mobility: float = 0,
        other_taxable: float = 0,
        other_non_taxable: float = 0,
        contract_type: str = "indefinido",
        other_discounts: float = 0,
        pension_fund: str = None
    ) -> PayrollCalculation:
        """
        Calcula liquidación completa de un colaborador.

        Args:
            base_salary: Sueldo base mensual
            collation: Asignación de colación
            mobility: Asignación de movilización
            other_taxable: Otros haberes imponibles
            other_non_taxable: Otros haberes no imponibles
            contract_type: "indefinido" o "plazo_fijo"
            other_discounts: Otros descuentos legales
            pension_fund: Fondo de pensión (AFP) del empleado

        Returns:
            PayrollCalculation con todos los montos desglosados
        """
        # 1. Calcular haberes
        gratification = self._calculate_gratification(base_salary)
        total_taxable = base_salary + gratification + other_taxable
        total_non_taxable = collation + mobility + other_non_taxable
        total_earnings = total_taxable + total_non_taxable

        # 2. Calcular bases para descuentos
        afp_taxable_base = min(total_taxable, self.tope_afp_pesos)
        afc_taxable_base = min(total_taxable, self.tope_afc_pesos)

        # 3. Calcular descuentos
        afp_discount = self._calculate_afp(afp_taxable_base, pension_fund)
        health_discount = self._calculate_health(afp_taxable_base)

        afc_percent = (
            self.afc_trabajador_indefinido
            if contract_type == "indefinido"
            else self.afc_trabajador_plazo_fijo
        )
        afc_discount = afc_taxable_base * (afc_percent / 100)

        # 4. Calcular base tributable para impuesto único
        taxable_base = (
            total_taxable
            - afp_discount
            - health_discount
            - afc_discount
        )

        income_tax = self._calculate_income_tax(taxable_base)

        total_discounts = (
            afp_discount + health_discount + afc_discount + income_tax + other_discounts
        )

        net_salary = total_earnings - total_discounts

        # 5. Calcular aportes empleador
        employer_sis = self._calculate_employer_sis(afp_taxable_base)

        afc_empleador_percent = (
            self.afc_empleador_indefinido
            if contract_type == "indefinido"
            else self.afc_empleador_plazo_fijo
        )
        employer_afc = afc_taxable_base * (afc_empleador_percent / 100)

        employer_mutual = self._calculate_employer_mutual(afp_taxable_base)

        total_employer_cost = (
            total_earnings + employer_sis + employer_afc + employer_mutual
        )

        return PayrollCalculation(
            base_salary=base_salary,
            gratification=gratification,
            collation=collation,
            mobility=mobility,
            other_taxable=other_taxable,
            other_non_taxable=other_non_taxable,
            total_taxable=total_taxable,
            total_non_taxable=total_non_taxable,
            total_earnings=total_earnings,
            afp_discount=afp_discount,
            health_discount=health_discount,
            afc_discount=afc_discount,
            income_tax=income_tax,
            other_discounts=other_discounts,
            total_discounts=total_discounts,
            net_salary=net_salary,
            taxable_base=taxable_base,
            afp_taxable_base=afp_taxable_base,
            afc_taxable_base=afc_taxable_base,
            employer_sis=employer_sis,
            employer_afc=employer_afc,
            employer_mutual=employer_mutual,
            total_employer_cost=total_employer_cost
        )

    def _calculate_gratification(self, base_salary: float) -> float:
        """Calcula gratificación legal (Art. 50 CT)."""
        max_gratification = (4.75 * self.imm_value) / 12
        calculated_gratification = base_salary * (self.gratificacion_max_percent / 100)
        return min(calculated_gratification, max_gratification)

    def _calculate_afp(self, taxable_base: float, pension_fund: str = None) -> float:
        """Calcula descuento AFP con tasa total (fondo + comisión)."""
        # Obtener tasa total según el fondo de pensión
        afp_rate = 11.27  # Default (Habitat)
        if pension_fund:
            pension_fund_lower = pension_fund.lower().strip()
            afp_rate = self.AFP_RATES.get(pension_fund_lower, 11.27)

        return taxable_base * (afp_rate / 100)

    def _calculate_health(self, taxable_base: float) -> float:
        """Calcula descuento de Salud (7% o Isapre)."""
        return taxable_base * (self.salud_percent / 100)

    def _calculate_income_tax(self, taxable_base: float) -> float:
        """Calcula Impuesto Único de Segunda Categoría.

        Tabla está en UTM y se convierte automáticamente a PESOS
        según el utm_value configurado (se actualiza mensualmente).
        """
        if taxable_base <= 0:
            return 0

        # Convertir base tributable a UTM para buscar el tramo
        tramo_utm = taxable_base / self.utm_value

        for tramo in self.tabla_impuesto:
            desde_utm = tramo.get("desde_utm", 0)
            hasta_utm = tramo.get("hasta_utm", -1)

            # Verificar si la base está en este tramo
            if hasta_utm == -1 or (desde_utm <= tramo_utm <= hasta_utm):
                factor = tramo.get("factor", 0)
                rebaja_utm = tramo.get("rebaja_utm", 0)

                # Impuesto = (base * factor%) - (rebaja_utm * utm_value)
                impuesto = taxable_base * (factor / 100)
                rebaja_pesos = rebaja_utm * self.utm_value
                impuesto = max(0, impuesto - rebaja_pesos)

                return impuesto

        return 0

    def _calculate_employer_sis(self, taxable_base: float) -> float:
        """Calcula aporte SIS del empleador."""
        return taxable_base * (self.sis_percent / 100)

    def _calculate_employer_mutual(self, taxable_base: float) -> float:
        """Calcula aporte Mutual de Seguridad."""
        return taxable_base * (self.tasa_mutual_base / 100)

    def reverse_calculate_base_salary(
        self,
        target_net_salary: float,
        collation: float = 0,
        mobility: float = 0,
        contract_type: str = "indefinido",
        pension_fund: str = None,
        has_parking: bool = False,
        iterations: int = 10
    ) -> float:
        """
        Calcula el sueldo base necesario para alcanzar un líquido objetivo.

        Usa iteración porque los descuentos dependen del sueldo base.

        Args:
            target_net_salary: Sueldo líquido objetivo (incluyendo otros descuentos como estacionamiento)
            collation: Asignación de colación
            mobility: Asignación de movilización
            contract_type: Tipo de contrato
            pension_fund: Fondo de pensión (AFP) del empleado
            has_parking: Si hay descuento de estacionamiento (100% de movilización)
            iterations: Número de iteraciones para convergencia

        Returns:
            Sueldo base aproximado
        """
        # Estimación inicial aproximada
        estimated_base = target_net_salary * 1.35

        for _ in range(iterations):
            calc = self.calculate(
                base_salary=estimated_base,
                collation=collation,
                mobility=mobility,
                contract_type=contract_type,
                pension_fund=pension_fund
            )

            # Calcular el descuento de estacionamiento (100% de movilización si aplica)
            parking_discount = mobility if has_parking else 0

            # Líquido final después de otros descuentos
            final_net_salary = calc.net_salary - parking_discount

            # Ajustar proporcionalmente
            if final_net_salary > 0:
                ratio = target_net_salary / final_net_salary
                estimated_base = estimated_base * ratio
            else:
                break

        return max(0, round(estimated_base))
