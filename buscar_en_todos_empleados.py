"""Buscar nuestro RUT en TODOS los empleados y encontrar donde tiene haberes/descuentos"""
import os
import json
import requests
import re
from dotenv import load_dotenv

load_dotenv()

token = os.getenv('BUK_API_TOKEN')
subdomain = os.getenv('BUK_SUBDOMAIN')

base_url = f"https://{subdomain}.buk.cl/api/v1/chile"
headers = {
    "auth_token": token,
    "Content-Type": "application/json"
}

mi_rut = "17771319-8"
rut_formato1 = re.sub(r'[.-]', '', mi_rut).upper()  # 177713198
rut_formato2 = re.sub(r'[.-]', '', mi_rut)  # 177713198 (sin mayuscula)

print("="*100)
print(f"BUSCANDO EMPLEADO {mi_rut} EN TODOS LOS REGISTROS")
print("="*100)

# 1. Obtener todos los empleados
print("\n1. OBTENIENDO TODOS LOS EMPLEADOS...")
try:
    response = requests.get(
        f"{base_url}/employees?limit=1000",
        headers=headers,
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        empleados = data.get("data", data) if isinstance(data, dict) else data

        if isinstance(empleados, list):
            print(f"   ✓ Total de empleados: {len(empleados)}")

            # Buscar nuestro RUT
            print(f"\n2. BUSCANDO RUT {mi_rut}...")
            encontrados = []

            for emp in empleados:
                if isinstance(emp, dict):
                    rut_emp = emp.get("rut", "")
                    nombre = emp.get("full_name", "")

                    # Comparar en diferentes formatos
                    if (rut_emp == mi_rut or
                        re.sub(r'[.-]', '', rut_emp).upper() == rut_formato1 or
                        re.sub(r'[.-]', '', rut_emp) == rut_formato2 or
                        rut_emp == rut_formato1 or
                        rut_emp == rut_formato2):

                        print(f"\n   ✓✓✓ ENCONTRADO: {nombre}")
                        print(f"       RUT en API: {rut_emp}")
                        print(f"       Email: {emp.get('email')}")
                        print(f"       Status: {emp.get('status')}")

                        encontrados.append(emp)

                        # Analizar datos de este empleado
                        print(f"\n       ANÁLISIS DE DATOS:")

                        # Buscar current_job
                        current_job = emp.get("current_job")
                        if current_job:
                            print(f"       ✓ current_job existe")
                            print(f"         - Status: {current_job.get('status')}")
                            print(f"         - Empresa: {current_job.get('company_name')}")
                            print(f"         - Cargo: {current_job.get('name')}")

                            fixed_items = current_job.get("fixed_items", [])
                            discounts = current_job.get("discounts", [])

                            print(f"         - fixed_items: {len(fixed_items)}")
                            for item in fixed_items:
                                print(f"            • {item.get('name')}: {item.get('value')}")

                            print(f"         - discounts: {len(discounts)}")
                            for disc in discounts:
                                print(f"            • {disc.get('name')}: {disc.get('value')}")

                            # Buscar attributes
                            if "attributes" in current_job:
                                print(f"         - attributes:")
                                attrs = current_job["attributes"]
                                if isinstance(attrs, dict):
                                    for key, val in attrs.items():
                                        print(f"            • {key}: {val}")
                                else:
                                    print(f"            {attrs}")
                        else:
                            print(f"       ✗ No tiene current_job")

                        # Buscar jobs (historial)
                        if "jobs" in emp:
                            jobs = emp["jobs"]
                            if isinstance(jobs, list):
                                print(f"\n       HISTORIAL DE EMPLEOS: {len(jobs)} fichas")
                                for idx, job in enumerate(jobs):
                                    print(f"\n         Ficha {idx}:")
                                    print(f"         - Status: {job.get('status')}")
                                    print(f"         - Empresa: {job.get('company_name')}")
                                    print(f"         - Fecha inicio: {job.get('start_date')}")
                                    print(f"         - Fecha fin: {job.get('end_date')}")

                                    fixed_items = job.get("fixed_items", [])
                                    discounts = job.get("discounts", [])

                                    if fixed_items:
                                        print(f"         - fixed_items: {len(fixed_items)}")
                                        for item in fixed_items:
                                            print(f"            • {item.get('name')}: {item.get('value')}")

                                    if discounts:
                                        print(f"         - discounts: {len(discounts)}")
                                        for disc in discounts:
                                            print(f"            • {disc.get('name')}: {disc.get('value')}")

                        # Buscar salary_history
                        if "salary_history" in emp:
                            salary_history = emp["salary_history"]
                            print(f"\n       HISTORIAL DE SUELDOS: {len(salary_history)} periodos")
                            for idx, periodo in enumerate(salary_history[:3]):
                                print(f"         Período {idx}:")
                                print(json.dumps(periodo, indent=12, default=str)[:300])

            if not encontrados:
                print(f"\n   ✗ NO ENCONTRADO con RUT {mi_rut}")
                print(f"\n   MOSTRANDO PRIMEROS 5 EMPLEADOS PARA REFERENCIA:")
                for emp in empleados[:5]:
                    print(f"      - {emp.get('full_name')} ({emp.get('rut')})")

except Exception as e:
    print(f"   ✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*100)
print("FIN BÚSQUEDA")
print("="*100)
