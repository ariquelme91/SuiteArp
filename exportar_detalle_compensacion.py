"""
Script para exportar detalle de compensación por empleado.
Muestra: Sueldo Base, Gratificación, Colación, Movilización, Target y Compensación Total Anualizada.
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

# Obtener empresa
empresas = db.get_empresas()
print("Empresas disponibles:")
for i, emp in enumerate(empresas, 1):
    print(f"  {i}. {emp}")

try:
    opcion = int(input("\nSelecciona número de empresa: ")) - 1
    empresa = empresas[opcion]
except (ValueError, IndexError):
    print("❌ Opción inválida")
    exit(1)

print(f"\nProcessando: {empresa}")

# Obtener empleados de la empresa
empleados = db.get_analysis_by_empresa_area(empresa=empresa)

if not empleados:
    print(f"❌ No hay empleados cargados para {empresa}")
    exit(1)

# Mes actual para UF
mes_actual = datetime.now().strftime("%Y-%m")

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
            "Sueldo Base Mensual": sueldo_base,
            "Sueldo Base Anual": componentes["sueldo_anual"],
            "Gratificación Mensual": componentes["gratificacion"],
            "Gratificación Anual": componentes["gratificacion_anual"],
            "Colación Mensual": componentes["colacion"],
            "Colación Anual": componentes["colacion_anual"],
            "Movilización Mensual": componentes["movilizacion"],
            "Movilización Anual": componentes["movilizacion_anual"],
            "Target (Rentas)": target,
            "Target Anual": componentes["target"],
            "Compensación Total Anual": componentes["total"],
            "UF Usado": componentes["uf_usado"],
            "Tope Gratificación": componentes["tope_gratificacion"]
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
nombre_archivo = f"detalle_compensacion_{empresa.replace(' ', '_').replace('.', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
    # Hoja 1: Resumen simplificado
    df_resumen = df[[
        "RUT", "Nombre", "Área", "Nivel HAY",
        "Sueldo Base Mensual", "Gratificación Mensual",
        "Colación Mensual", "Movilización Mensual",
        "Target (Rentas)", "Compensación Total Anual"
    ]].copy()

    df_resumen.to_excel(writer, sheet_name='Resumen Simplificado', index=False)

    # Hoja 2: Detalle completo
    df.to_excel(writer, sheet_name='Detalle Completo', index=False)

    # Hoja 3: Análisis por Nivel HAY
    df_por_nivel = df.groupby("Nivel HAY").agg({
        "RUT": "count",
        "Sueldo Base Mensual": ["mean", "min", "max"],
        "Compensación Total Anual": ["mean", "min", "max"]
    }).round(2)

    df_por_nivel.columns = [
        "Cantidad Empleados",
        "Sueldo Base Prom", "Sueldo Base Mín", "Sueldo Base Máx",
        "Comp Total Prom", "Comp Total Mín", "Comp Total Máx"
    ]

    df_por_nivel.to_excel(writer, sheet_name='Análisis por Nivel')

# Mostrar resumen
print(f"\n✅ Detalle exportado a: {nombre_archivo}")
print(f"\nResumen:")
print(f"  Total de empleados: {len(df)}")
print(f"  Sueldo base promedio: ${df['Sueldo Base Mensual'].mean():,.0f}")
print(f"  Compensación total anual promedio: ${df['Compensación Total Anual'].mean():,.0f}")
print(f"\nPor Nivel HAY:")
for nivel in sorted(df["Nivel HAY"].unique()):
    df_nivel = df[df["Nivel HAY"] == nivel]
    print(f"  Nivel {nivel}: {len(df_nivel)} empleados, Promedio: ${df_nivel['Compensación Total Anual'].mean():,.0f}")
