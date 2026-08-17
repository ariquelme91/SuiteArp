"""
Script para cargar UF actual desde configuración a la BD.
"""

import json
from src.analysis.db_manager import AnalysisDBManager

# Cargar configuración
with open("config/parameters.json") as f:
    params = json.load(f)

periodo = params.get("periodo", "2026-08")
uf_value = params.get("uf_value")

if not periodo or not uf_value:
    print("❌ Error: No se encontraron periodo o UF en configuración")
    exit(1)

# Cargar en BD
db = AnalysisDBManager()

if db.upsert_uf(periodo, uf_value):
    print(f"OK - UF cargada en BD:")
    print(f"   Periodo: {periodo}")
    print(f"   Valor: ${uf_value:,.2f}")
else:
    print("ERROR - Error al cargar UF en BD")
