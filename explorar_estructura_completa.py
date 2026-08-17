"""Script para explorar TODA la estructura de datos disponible en Buk"""
import os
import json
from dotenv import load_dotenv
from src.buk_client import BukClient

load_dotenv()

buk = BukClient(os.getenv('BUK_API_TOKEN'), os.getenv('BUK_SUBDOMAIN'))

rut = "13531650-4"

print("="*80)
print(f"EXPLORACIÓN COMPLETA DE ESTRUCTURA - RUT: {rut}")
print("="*80)

try:
    # Buscar empleado
    employee = buk.search_employee(rut=rut)

    if not employee:
        print("Empleado no encontrado")
        exit()

    print(f"\n✓ Empleado: {employee.full_name}\n")

    # ===== EXPLORAR EMPLOYEE OBJECT =====
    print("\n" + "="*80)
    print("1. EMPLOYEE OBJECT - Todos los atributos y métodos")
    print("="*80)

    for attr in dir(employee):
        if not attr.startswith('_'):
            try:
                value = getattr(employee, attr)
                if not callable(value):
                    print(f"\n{attr}:")
                    if isinstance(value, dict):
                        print(json.dumps(value, indent=2, default=str, ensure_ascii=False))
                    else:
                        print(f"  {value}")
            except Exception as e:
                print(f"{attr}: [ERROR: {str(e)}]")

    # ===== EXPLORAR CURRENT_JOB =====
    if employee.current_job:
        print("\n" + "="*80)
        print("2. CURRENT_JOB - Estructura completa")
        print("="*80)
        print(json.dumps(employee.current_job, indent=2, default=str, ensure_ascii=False))

    # ===== EXPLORAR JOB HISTORY =====
    print("\n" + "="*80)
    print("3. JOB HISTORY - Primeros 2 registros")
    print("="*80)
    jobs = buk.get_job_history(rut)
    if jobs:
        for i, job in enumerate(jobs[:2], 1):
            print(f"\nPuesto {i}:")
            print(json.dumps(job, indent=2, default=str, ensure_ascii=False))

    # ===== EXPLORAR SALARY HISTORY =====
    print("\n" + "="*80)
    print("4. SALARY HISTORY - Primeros 2 registros")
    print("="*80)
    salary_hist = buk.get_salary_history(rut)
    if salary_hist:
        for i, sal in enumerate(salary_hist[:2], 1):
            print(f"\nPeríodo {i}:")
            print(json.dumps(sal, indent=2, default=str, ensure_ascii=False))

    # ===== LISTAR MÉTODOS DISPONIBLES =====
    print("\n" + "="*80)
    print("5. MÉTODOS DISPONIBLES EN BUKCLIENT")
    print("="*80)
    methods = [m for m in dir(buk) if not m.startswith('_') and callable(getattr(buk, m))]
    for method in methods:
        print(f"  - {method}")

except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
