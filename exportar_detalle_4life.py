"""
Script para exportar detalle de compensación para 4Life Seguros de Vida S.A.
"""

import pandas as pd
from src.analysis.db_manager import AnalysisDBManager
from src.analysis.compensation_calculator import CompensationCalculator
from datetime import datetime
import json

# Parámetros
with open("config/parameters.json") as f:
    params = json.load(f)
imm_value = params.get("imm_value", 553_553)

db = AnalysisDBManager()
calculator = CompensationCalculator(db, imm_value=imm_value)

# Empresa específica
empresa = "4Life Seguros de Vida S.A."

print(f"Procesando: {empresa}")

# Obtener empleados de la empresa
empleados = db.get_analysis_by_empresa_area(empresa=empresa)

if not empleados:
    print(f"❌ No hay empleados cargados para {empresa}")
    exit(1)

# Mes actual para UF
mes_actual = datetime.now().strftime("%Y-%m")

print(f"Total de empleados encontrados: {len(empleados)}")

# Procesar cada empleado
datos_detalle = []

for emp in empleados:
    try:
        rut = emp.get("rut")
        nombre = emp.get("nombre")
        nivel_hay = emp.get("nivel_hay", "N/A")
        area = emp.get("area", "N/A")
        sueldo_base = emp.get("sueldo_actual", 0)
        target = float(emp.get("target", 1.0)) if emp.get("target") else 1.0

        if sueldo_base <= 0:
            continue

        # Calcular componentes
        componentes = calculator.calcular_componentes(
            sueldo_base=sueldo_base,
            target=target,
            mes=mes_actual,
            incluir_target=True
        )

        # Desglose anualizado
        datos_detalle.append({
            "RUT": rut,
            "Nombre": nombre,
            "Área": area,
            "Nivel HAY": nivel_hay,
            "Sueldo Base (Mensual)": round(sueldo_base, 2),
            "Sueldo Base (Anual)": round(componentes["sueldo_anual"], 2),
            "Gratificación (Mensual)": round(componentes["gratificacion"], 2),
            "Gratificación (Anual)": round(componentes["gratificacion_anual"], 2),
            "Colación (Mensual)": round(componentes["colacion"], 2),
            "Colación (Anual)": round(componentes["colacion_anual"], 2),
            "Movilización (Mensual)": round(componentes["movilizacion"], 2),
            "Movilización (Anual)": round(componentes["movilizacion_anual"], 2),
            "Target (Rentas)": target,
            "Target (Anual)": round(componentes["target"], 2),
            "COMPENSACIÓN TOTAL ANUAL": round(componentes["total"], 2),
            "UF Utilizado": round(componentes["uf_usado"], 2),
        })

    except Exception as e:
        print(f"⚠️ Error procesando {nombre}: {e}")
        continue

# Crear DataFrame
df = pd.DataFrame(datos_detalle)

if df.empty:
    print("❌ No se pudo procesar ningún empleado")
    exit(1)

# Crear Excel con múltiples hojas
nombre_archivo = f"detalle_compensacion_4life_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
    # Hoja 1: Resumen Ejecutivo
    df_resumen = df[[
        "RUT", "Nombre", "Área", "Nivel HAY",
        "Sueldo Base (Mensual)", "Gratificación (Mensual)",
        "Colación (Mensual)", "Movilización (Mensual)",
        "Target (Rentas)", "COMPENSACIÓN TOTAL ANUAL"
    ]].copy()

    df_resumen.to_excel(writer, sheet_name='Resumen Ejecutivo', index=False)

    # Hoja 2: Detalle Completo (para validación)
    df_detalle = df[[
        "RUT", "Nombre", "Área", "Nivel HAY",
        "Sueldo Base (Mensual)", "Sueldo Base (Anual)",
        "Gratificación (Mensual)", "Gratificación (Anual)",
        "Colación (Mensual)", "Colación (Anual)",
        "Movilización (Mensual)", "Movilización (Anual)",
        "Target (Rentas)", "Target (Anual)",
        "COMPENSACIÓN TOTAL ANUAL"
    ]].copy()

    df_detalle.to_excel(writer, sheet_name='Detalle Completo', index=False)

    # Hoja 3: Análisis por Nivel HAY
    df_por_nivel = df.groupby("Nivel HAY").agg({
        "RUT": "count",
        "Sueldo Base (Mensual)": ["mean", "min", "max"],
        "COMPENSACIÓN TOTAL ANUAL": ["mean", "min", "max"]
    }).round(2)

    df_por_nivel.columns = [
        "Cantidad Empleados",
        "Sueldo Base Prom", "Sueldo Base Mín", "Sueldo Base Máx",
        "Comp Total Prom", "Comp Total Mín", "Comp Total Máx"
    ]

    df_por_nivel.to_excel(writer, sheet_name='Análisis por Nivel')

# Mostrar resumen
print(f"\n✅ Detalle exportado a: {nombre_archivo}")
print(f"\nResumen General:")
print(f"  Total de empleados: {len(df)}")
print(f"  Sueldo base promedio (mensual): ${df['Sueldo Base (Mensual)'].mean():,.0f}")
print(f"  Compensación total anual promedio: ${df['COMPENSACIÓN TOTAL ANUAL'].mean():,.0f}")
print(f"  Compensación total anual (mínima): ${df['COMPENSACIÓN TOTAL ANUAL'].min():,.0f}")
print(f"  Compensación total anual (máxima): ${df['COMPENSACIÓN TOTAL ANUAL'].max():,.0f}")

print(f"\nResumen por Nivel HAY:")
resumen_nivel = df.groupby("Nivel HAY").agg({
    "RUT": "count",
    "COMPENSACIÓN TOTAL ANUAL": ["mean", "min", "max"]
}).round(0)

for nivel in sorted(df["Nivel HAY"].unique()):
    df_nivel = df[df["Nivel HAY"] == nivel]
    cant = len(df_nivel)
    prom = df_nivel['COMPENSACIÓN TOTAL ANUAL'].mean()
    print(f"  Nivel {nivel}: {cant} empleados | Promedio: ${prom:,.0f}")
