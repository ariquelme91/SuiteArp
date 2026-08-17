"""
Script para exportar promedios de compensación interna a Excel.
"""

import pandas as pd
from src.analysis.db_manager import AnalysisDBManager
from datetime import datetime

# Obtener promedios de BD
db = AnalysisDBManager()
promedios = db.get_compensation_averages()

if not promedios:
    print("❌ No hay promedios calculados en BD")
    exit(1)

# Convertir a DataFrame
df = pd.DataFrame([
    {
        "Nivel HAY": p["nivel_hay"],
        "Cantidad Empleados": p["cantidad_empleados"],
        "Promedio Anualizado": f"${p['promedio_anualizado']:,.0f}",
        "Promedio (Valor)": p["promedio_anualizado"],
        "Mínimo": f"${p['minimo_anualizado']:,.0f}",
        "Mínimo (Valor)": p["minimo_anualizado"],
        "Máximo": f"${p['maximo_anualizado']:,.0f}",
        "Máximo (Valor)": p["maximo_anualizado"],
        "Desviación Estándar": f"${p['desviacion_std']:,.0f}",
        "Desviación (Valor)": p["desviacion_std"],
        "Fecha Cálculo": p["fecha_calculo"]
    }
    for p in sorted(promedios, key=lambda x: int(x["nivel_hay"]))
])

# Crear Excel
nombre_archivo = f"promedios_competitividad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
    # Hoja principal
    df_display = df[["Nivel HAY", "Cantidad Empleados", "Promedio Anualizado", "Mínimo", "Máximo", "Desviación Estándar"]]
    df_display.to_excel(writer, sheet_name='Promedios', index=False)

    # Hoja con datos numéricos para análisis
    df_numeric = df[["Nivel HAY", "Cantidad Empleados", "Promedio (Valor)", "Mínimo (Valor)", "Máximo (Valor)", "Desviación (Valor)"]]
    df_numeric.to_excel(writer, sheet_name='Datos Numéricos', index=False)

print(f"✅ Promedios exportados a: {nombre_archivo}")
print(f"   Total de niveles: {len(df)}")
print(f"   Total de empleados: {df['Cantidad Empleados'].sum()}")
