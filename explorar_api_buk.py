"""Script para explorar datos disponibles en API de Buk"""
import os
import json
from dotenv import load_dotenv
from src.buk_client import BukClient

load_dotenv()

buk = BukClient(os.getenv('BUK_API_TOKEN'), os.getenv('BUK_SUBDOMAIN'))

ruts = ["17771310-8", "13531650-4"]

print("=" * 80)
print("EXPLORACIÓN DE DATOS - API BUK")
print("=" * 80)

for rut in ruts:
    print(f"\n{'='*80}")
    print(f"RUT: {rut}")
    print(f"{'='*80}")

    try:
        # Buscar empleado
        employee = buk.search_employee(rut=rut)

        if employee:
            print(f"\n✓ Empleado encontrado: {employee.full_name}")
            print(f"\nDATOS BÁSICOS:")
            print(f"  - RUT: {employee.rut}")
            print(f"  - Nombre: {employee.full_name}")
            print(f"  - Email: {employee.email}")
            print(f"  - Teléfono: {employee.phone}")
            print(f"  - Fecha Nacimiento: {employee.birthdate}")
            print(f"  - Estado Civil: {employee.marital_status}")
            print(f"  - Género: {employee.gender}")

            print(f"\nDATOS LABORALES ACTUALES (Current Job):")
            if employee.current_job:
                cj = employee.current_job
                print(f"  - Cargo: {cj.get('name', 'N/A')}")
                print(f"  - Sueldo Base: ${cj.get('base_wage', 'N/A'):,}")
                print(f"  - Fecha Inicio: {cj.get('start_date', 'N/A')}")
                print(f"  - Empresa ID: {cj.get('company_id', 'N/A')}")
                print(f"  - Área ID: {cj.get('area_id', 'N/A')}")
                print(f"  - Contrato: {cj.get('contract_type', 'N/A')}")
                print(f"  - Jornada: {cj.get('working_day', 'N/A')}")
                print(f"  - Estado: {cj.get('status', 'N/A')}")
                print(f"\n  ALL FIELDS in current_job:")
                for key, value in cj.items():
                    print(f"    - {key}: {value}")
            else:
                print("  ⚠️  Sin datos de puesto actual")

            print(f"\nHISTORIAL DE PUESTOS:")
            jobs = buk.get_job_history(rut)
            if jobs:
                print(f"  Total de puestos: {len(jobs)}")
                for i, job in enumerate(jobs[:3], 1):  # Solo primeros 3
                    print(f"\n  Puesto {i}:")
                    print(f"    - Cargo: {job.get('name', 'N/A')}")
                    print(f"    - Inicio: {job.get('start_date', 'N/A')}")
                    print(f"    - Fin: {job.get('end_date', 'N/A')}")
                    print(f"    - Sueldo: ${job.get('base_wage', 'N/A'):,}")
            else:
                print("  Sin historial de puestos")

            print(f"\nHISTORIAL DE SUELDOS:")
            salary_hist = buk.get_salary_history(rut)
            if salary_hist:
                print(f"  Total de cambios: {len(salary_hist)}")
                for i, sal in enumerate(salary_hist[:3], 1):  # Solo primeros 3
                    print(f"\n  Período {i}:")
                    print(f"    - Inicio: {sal.get('start_date', 'N/A')}")
                    print(f"    - Fin: {sal.get('end_date', 'N/A')}")
                    print(f"    - Sueldo Base: ${sal.get('base_wage', 'N/A'):,}")
            else:
                print("  Sin historial de sueldos")

        else:
            print(f"✗ Empleado no encontrado")

    except Exception as e:
        print(f"✗ Error: {str(e)}")

print(f"\n{'='*80}")
print("FIN DE EXPLORACIÓN")
print(f"{'='*80}\n")
