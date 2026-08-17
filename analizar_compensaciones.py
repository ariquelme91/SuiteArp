"""Script para analizar estructura de compensaciones del archivo Excel"""

import pandas as pd
import openpyxl
from pathlib import Path

archivo = r"C:\Users\ariquelme\OneDrive - Dercorp\ANALISIS COMPENSACIONES.xlsx"

try:
    # Leer todas las hojas
    xls = pd.ExcelFile(archivo)
    print("=" * 100)
    print("HOJAS DISPONIBLES:")
    print("=" * 100)
    for sheet in xls.sheet_names:
        print(f"  - {sheet}")

    # Leer cada hoja
    for sheet in xls.sheet_names:
        print(f"\n{'='*100}")
        print(f"HOJA: {sheet}")
        print(f"{'='*100}")

        df = pd.read_excel(archivo, sheet_name=sheet)
        print(f"\nDimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
        print(f"Columnas: {list(df.columns)}")
        print("\nPrimeras filas:")
        print(df.to_string())

        # Si la hoja tiene fórmulas, intentar leerlas
        try:
            wb = openpyxl.load_workbook(archivo)
            ws = wb[sheet]

            print(f"\n\nFÓRMULAS ENCONTRADAS:")
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str) and cell.value.startswith('='):
                        print(f"  {cell.coordinate}: {cell.value}")
        except Exception as e:
            print(f"  No se pudieron leer fórmulas: {e}")

except Exception as e:
    print(f"Error: {e}")
    print(f"\nIntentando buscar el archivo...")
    for root, dirs, files in Path(r"C:\Users\ariquelme\OneDrive - Dercorp").walk() if hasattr(Path, 'walk') else []:
        for file in files:
            if 'compensacion' in file.lower() and file.endswith('.xlsx'):
                print(f"Encontrado: {root}/{file}")
