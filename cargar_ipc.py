"""Script para cargar datos de IPC en la BD"""
from src.analysis.db_manager import AnalysisDBManager

db = AnalysisDBManager()

# Datos de IPC (mes: valor_ipc)
ipc_data = {
    "2026-07": 0.0240,
    "2026-03": 0.0050,
    "2025-11": 0.0140,
    "2025-07": 0.0050,
    "2025-03": 0.0150,
    "2024-11": 0.0210,
    "2024-07": 0.0110,
    "2024-03": 0.0151,
    "2023-11": 0.0160,
    "2023-07": 0.0140,
    "2023-03": 0.0200,
    "2022-11": 0.0403,
    "2022-07": 0.0550,
    "2022-03": 0.0280,
    "2021-11": 0.0370,
    "2021-07": 0.0387,
    "2021-03": 0.0390,
    "2020-11": 0.0221,
    "2020-07": 0.0256,
    "2020-03": 0.0262,
    "2019-11": 0.0193,
    "2019-07": 0.0203,
    "2019-03": 0.0194,
    "2018-11": 0.0126,
    "2018-07": 0.0259,
    "2018-03": 0.0280,
    "2017-11": 0.0161,
    "2017-07": 0.0262,
    "2016-11": 0.0257,
    "2016-07": 0.0244,
}

print("Cargando datos de IPC...")
for mes, valor in ipc_data.items():
    db.upsert_ipc(mes, valor)
    print(f"  ✓ {mes}: {valor*100:.2f}%")

print(f"\n✅ {len(ipc_data)} registros de IPC cargados exitosamente")
