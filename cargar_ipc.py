"""Script para cargar datos de IPC en la BD.

La fuente de verdad es config/ipc_history.json (comiteado en git), que es el
mismo archivo del que se siembra la BD en un contenedor nuevo y el que
actualiza el botón "Cargar histórico completo" de Configuración.
"""
from src.analysis.db_manager import AnalysisDBManager

db = AnalysisDBManager()
ipc_data = db.leer_ipc_seed_desde_archivo()

if not ipc_data:
    print("No se encontraron datos en config/ipc_history.json")
    raise SystemExit(1)

print("Cargando datos de IPC...")
for mes, valor in sorted(ipc_data.items()):
    db.upsert_ipc(mes, valor)
    print(f"  OK {mes}: {valor * 100:.2f}%")

print(f"\n{len(ipc_data)} registros de IPC cargados exitosamente")
