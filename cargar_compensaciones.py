"""
Script para cargar datos de compensaciones desde Excel.

Estructura esperada en Excel:
- Columna A: Nivel (número)
- Columna B: Mercado Financiero (monto)
- Columna C: Mercado Seguros (monto)
- Columna D: Descripción (opcional)

Ejemplo:
Nivel | Mercado Financiero | Mercado Seguros | Descripción
  7   |    1.234.567       |    1.100.000    | Junior
  8   |    1.450.000       |    1.300.000    | Senior
  ...
"""

import os
import pandas as pd
from dotenv import load_dotenv
from src.analysis.db_manager import AnalysisDBManager

load_dotenv()

def cargar_compensaciones_desde_excel(ruta_archivo: str):
    """Carga datos de compensaciones desde un archivo Excel."""

    print(f"Cargando compensaciones desde: {ruta_archivo}")

    # Validar que el archivo existe
    if not os.path.exists(ruta_archivo):
        print(f"❌ Error: Archivo no encontrado: {ruta_archivo}")
        return

    try:
        # Leer Excel
        df = pd.read_excel(ruta_archivo)

        print(f"\nArchivo cargado: {len(df)} filas")
        print(f"Columnas encontradas: {list(df.columns)}")

        # Inicializar BD
        db_manager = AnalysisDBManager()

        # Procesar cada fila
        insertados = 0
        errores = 0

        for idx, row in df.iterrows():
            try:
                nivel = int(row.iloc[0])  # Columna A
                mercado_financiero = float(row.iloc[1]) if len(row) > 1 and pd.notna(row.iloc[1]) else None
                mercado_seguros = float(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else None
                descripcion = str(row.iloc[3]) if len(row) > 3 and pd.notna(row.iloc[3]) else None

                if db_manager.upsert_compensation_level(nivel, mercado_financiero, mercado_seguros, descripcion):
                    print(f"  ✓ Nivel {nivel}: Fin=${mercado_financiero:,.0f} | Seg=${mercado_seguros:,.0f}")
                    insertados += 1
                else:
                    print(f"  ✗ Nivel {nivel}: Error al insertar")
                    errores += 1

            except Exception as e:
                print(f"  ✗ Fila {idx + 2}: Error - {str(e)}")
                errores += 1

        print(f"\n✅ Carga completada:")
        print(f"   - Insertados: {insertados}")
        print(f"   - Errores: {errores}")

    except Exception as e:
        print(f"❌ Error cargando archivo: {str(e)}")


if __name__ == "__main__":
    # Ejemplo de uso
    archivo = "compensaciones_data.xlsx"

    if os.path.exists(archivo):
        cargar_compensaciones_desde_excel(archivo)
    else:
        print(f"⚠️  No se encontró {archivo}")
        print("\nCrea un archivo Excel con estructura:")
        print("Nivel | Mercado Financiero | Mercado Seguros | Descripción")
        print("  7   |    1.234.567       |    1.100.000    | Junior")
        print("  8   |    1.450.000       |    1.300.000    | Senior")
        print("\nY ejecuta: python cargar_compensaciones.py")
