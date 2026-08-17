"""
Script para crear archivo Excel de ejemplo con datos de compensaciones.
"""

import pandas as pd
from datetime import datetime

# Datos de ejemplo - puedes modificar estos valores
data = {
    'Nivel': [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
    'Mercado Financiero': [
        1_300_000, 1_450_000, 1_600_000, 13_559_036, 15_912_175, 18_821_162,
        23_286_312, 32_572_058, 43_812_418, 58_879_636, 81_512_109, 108_045_466,
        155_095_693, 185_959_129, 258_178_977, 327_561_961, 425_947_536, 450_274_520,
        602_008_936
    ],
    'Mercado Seguros': [
        1_200_000, 1_320_000, 1_450_000, 15_379_008, 16_775_556, 18_668_364,
        23_177_592, 23_707_560, 45_809_460, 58_376_400, 78_929_772, 100_453_488,
        140_332_392, 173_646_336, 249_915_672, 316_485_888, 417_204_960, 431_653_824,
        None  # Sin dato para nivel 25 en mercado seguros
    ],
    'Descripcion': [
        'Junior', 'Junior', 'Junior', 'Mid', 'Mid', 'Mid',
        'Senior', 'Senior', 'Senior', 'Senior', 'Lead', 'Lead',
        'Manager', 'Manager', 'Senior Manager', 'Director', 'Senior Director', 'VP', 'C-Level'
    ]
}

# Crear DataFrame
df = pd.DataFrame(data)

# Guardar a Excel
filename = 'compensaciones_data.xlsx'
df.to_excel(filename, index=False, engine='openpyxl')

print(f"✅ Archivo creado: {filename}")
print(f"\nDatos cargados: {len(df)} niveles")
print("\nEstructura:")
print(df.to_string(index=False))
print(f"\nPara cargar estos datos, ejecuta:")
print(f"  python cargar_compensaciones.py")
