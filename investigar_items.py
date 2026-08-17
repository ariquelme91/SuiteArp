"""Investigación profunda de dónde están los bonos y descuentos en Buk"""
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

rut = "17771319-8"
rut_formatted = re.sub(r'[.-]', '', rut).upper()

print("="*100)
print(f"INVESTIGACIÓN PROFUNDA: Búsqueda de BONOS y DESCUENTOS")
print("="*100)

# 1. Obtener datos completos del empleado
print("\n1. OBTENIENDO DATOS COMPLETOS DEL EMPLEADO...")
response = requests.get(
    f"{base_url}/employees/{rut_formatted}",
    headers=headers,
    timeout=10
)
employee_data = response.json().get("data", response.json())

print(f"   Empleado: {employee_data.get('full_name')}")
print(f"   Status: {employee_data.get('status')}")

# 2. PROBAR TODOS LOS ENDPOINTS POSIBLES DE ITEMS
print("\n2. PROBANDO ACCESO A BONOS CON IDs SECUENCIALES...")
bono_ids_encontrados = []
for i in range(1, 50):
    try:
        response = requests.get(
            f"{base_url}/bonos/{i}",
            headers=headers,
            timeout=3
        )
        if response.status_code == 200:
            data = response.json().get("data", response.json())
            bono_ids_encontrados.append((i, data.get("name", "Sin nombre")))
            print(f"   ✓ /bonos/{i} => {data.get('name')}")
    except:
        pass

# 3. PROBAR DESCUENTOS CON IDs SECUENCIALES
print("\n3. PROBANDO ACCESO A DESCUENTOS CON IDs SECUENCIALES...")
descuento_ids_encontrados = []
for i in range(1, 50):
    try:
        response = requests.get(
            f"{base_url}/descuentos/{i}",
            headers=headers,
            timeout=3
        )
        if response.status_code == 200:
            data = response.json().get("data", response.json())
            descuento_ids_encontrados.append((i, data.get("name", "Sin nombre")))
            print(f"   ✓ /descuentos/{i} => {data.get('name')}")
    except:
        pass

# 4. PROBAR ENDPOINTS ALTERNATIVOS
print("\n4. PROBANDO ENDPOINTS ALTERNATIVOS...")
endpoints_alternativos = [
    f"/employees/{rut_formatted}/salary-history",
    f"/employees/{rut_formatted}/payroll",
    f"/employees/{rut_formatted}/compensation",
    f"/employees/{rut_formatted}/fixed-compensations",
    f"/payroll/employees/{rut_formatted}",
    f"/compensation/employees/{rut_formatted}",
    "/bonos",
    "/descuentos",
    "/fixed-items",
    "/fixed-compensations",
]

for endpoint in endpoints_alternativos:
    try:
        response = requests.get(
            f"{base_url}{endpoint}",
            headers=headers,
            timeout=5
        )
        status = response.status_code

        if status == 200:
            data = response.json()
            if isinstance(data, dict) and "data" in data:
                count = len(data.get("data", []))
            elif isinstance(data, list):
                count = len(data)
            else:
                count = 1
            print(f"   ✓ {endpoint} => Status 200, {count} items")

            # Mostrar primeros items
            if status == 200:
                try:
                    respuesta = response.json()
                    if isinstance(respuesta, dict) and "data" in respuesta:
                        items = respuesta["data"]
                    elif isinstance(respuesta, list):
                        items = respuesta
                    else:
                        items = [respuesta]

                    if items and isinstance(items, list) and len(items) > 0:
                        print(f"      Primeros items: {json.dumps(items[:2], indent=4, default=str)[:200]}")
                except:
                    pass
        elif status != 404:
            print(f"   - {endpoint} => Status {status}")
    except Exception as e:
        pass

# 5. BUSCAR EN LA ESTRUCTURA COMPLETA DEL EMPLEADO
print("\n5. BUSCANDO CLAVES QUE CONTENGAN 'ITEM', 'BONO', 'HABER', 'DESCUENTO'...")

def buscar_claves(obj, nivel=0, max_nivel=5):
    """Busca recursivamente claves que contienen palabras clave"""
    resultados = []
    if nivel > max_nivel:
        return resultados

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = key.lower()
            if any(kw in key_lower for kw in ["item", "bono", "haber", "descuento", "allowance", "deduction", "benefit", "fixed", "compensation"]):
                resultados.append((key, type(value).__name__, str(value)[:100]))

            if isinstance(value, (dict, list)):
                resultados.extend(buscar_claves(value, nivel+1, max_nivel))

    elif isinstance(obj, list):
        for item in obj[:3]:  # Solo primeros 3 items
            if isinstance(item, (dict, list)):
                resultados.extend(buscar_claves(item, nivel+1, max_nivel))

    return resultados

hallazgos = buscar_claves(employee_data)
if hallazgos:
    for key, tipo, valor in hallazgos:
        print(f"   > {key} ({tipo}): {valor}")
else:
    print("   (No se encontraron claves relevantes)")

# 6. VERIFICAR SI CURRENT_JOB EXISTE Y QUÉ CONTIENE
print("\n6. ANÁLISIS DE CURRENT_JOB...")
current_job = employee_data.get("current_job")
if current_job:
    print(f"   ✓ current_job existe")
    print(f"   Claves en current_job: {list(current_job.keys())}")

    if "fixed_items" in current_job:
        print(f"   - fixed_items: {len(current_job['fixed_items'])} items")
    if "discounts" in current_job:
        print(f"   - discounts: {len(current_job['discounts'])} items")
    if "attributes" in current_job:
        print(f"   - attributes: {current_job['attributes']}")
else:
    print(f"   ✗ current_job NO EXISTE")

# 7. BUSCAR OTRAS FICHAS O HISTÓRICOS
print("\n7. BUSCANDO OTRAS FICHAS O HISTÓRICOS...")
for key in ["jobs", "historical_jobs", "previous_jobs", "job_history", "employment_history"]:
    if key in employee_data:
        jobs = employee_data[key]
        if isinstance(jobs, list):
            print(f"   ✓ {key}: {len(jobs)} fichas")
            for idx, job in enumerate(jobs):
                print(f"      Job {idx}: status={job.get('status')}, items={len(job.get('fixed_items', []))}, descuentos={len(job.get('discounts', []))}")

print("\n" + "="*100)
print("FIN INVESTIGACIÓN")
print("="*100)

if bono_ids_encontrados:
    print(f"\nBONOS ENCONTRADOS: {bono_ids_encontrados}")
if descuento_ids_encontrados:
    print(f"DESCUENTOS ENCONTRADOS: {descuento_ids_encontrados}")
