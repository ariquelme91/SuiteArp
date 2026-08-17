"""Investigación exhaustiva de endpoints de Buk"""
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
print("INVESTIGACIÓN EXHAUSTIVA DE ENDPOINTS")
print("="*100)

# 1. Obtener todas las empresas
print("\n1. OBTENIENDO LISTA DE EMPRESAS...")
try:
    response = requests.get(
        f"{base_url}/companies",
        headers=headers,
        timeout=10
    )
    if response.status_code == 200:
        companies_data = response.json().get("data", response.json())
        if isinstance(companies_data, list):
            companies = companies_data
        else:
            companies = [companies_data]

        print(f"   ✓ Empresas encontradas: {len(companies)}")
        for company in companies[:5]:
            company_id = company.get("id")
            company_name = company.get("name")
            print(f"      - ID: {company_id}, Nombre: {company_name}")
except Exception as e:
    print(f"   ✗ Error: {str(e)}")
    companies = []

# 2. Probar LISTADOS de bonos y descuentos (sin ID)
print("\n2. PROBANDO LISTADOS DE BONOS Y DESCUENTOS...")

endpoints_listados = [
    "/bonos",
    "/descuentos",
    "/fixed-items",
    "/fixed-compensations",
    "/allowances",
    "/deductions",
    "/benefits",
    "/payroll/items",
]

for endpoint in endpoints_listados:
    try:
        response = requests.get(
            f"{base_url}{endpoint}",
            headers=headers,
            timeout=5
        )
        status = response.status_code

        if status == 200:
            data = response.json()
            items = data.get("data", data) if isinstance(data, dict) else data

            if isinstance(items, list):
                print(f"   ✓ {endpoint} => {len(items)} items")
                for item in items[:3]:
                    if isinstance(item, dict):
                        name = item.get("name", item.get("description", "Sin nombre"))
                        item_id = item.get("id", "")
                        print(f"      • {name} (ID: {item_id})")
            else:
                print(f"   ✓ {endpoint} => Estructura diferente")
        else:
            print(f"   - {endpoint} => Status {status}")
    except Exception as e:
        pass

# 3. Para cada empresa, buscar al empleado y sus datos de nómina
print("\n3. BUSCANDO EMPLEADO EN CADA EMPRESA Y DATOS DE NÓMINA...")

for company in companies[:3]:  # Solo primeras 3 empresas
    company_id = company.get("id")
    company_name = company.get("name")
    print(f"\n   Empresa: {company_name} (ID: {company_id})")

    # Intentar obtener empleado con company_id
    try:
        # Probar endpoint con company_id
        endpoints_por_empresa = [
            f"/companies/{company_id}/employees/{rut_formatted}",
            f"/companies/{company_id}/employees",
            f"/payroll/{company_id}/employees/{rut_formatted}",
        ]

        for endpoint in endpoints_por_empresa:
            try:
                response = requests.get(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"      ✓ {endpoint} => Status 200")
                    # Mostrar estructura
                    if isinstance(data, dict) and "data" in data:
                        print(f"         Contiene 'data' con {len(data['data']) if isinstance(data['data'], list) else 1} items")
            except:
                pass
    except Exception as e:
        print(f"      Error: {str(e)}")

# 4. Probar endpoints de PAYROLL específicos
print("\n4. PROBANDO ENDPOINTS DE PAYROLL...")

payroll_endpoints = [
    f"/payroll/employees/{rut_formatted}",
    f"/payroll/employees/{rut_formatted}/compensation",
    f"/payroll/employees/{rut_formatted}/items",
    f"/employees/{rut_formatted}/payroll",
    f"/employees/{rut_formatted}/payroll-items",
    f"/employees/{rut_formatted}/compensation-items",
    f"/salary/{rut_formatted}",
    f"/salary/employees/{rut_formatted}",
]

for endpoint in payroll_endpoints:
    try:
        response = requests.get(
            f"{base_url}{endpoint}",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ {endpoint}")
            # Mostrar primeros 500 chars
            print(f"      {json.dumps(data, indent=2, default=str)[:500]}")
    except:
        pass

# 5. Acceder directamente a los IDs que el usuario mencionó (1475, 404)
print("\n5. PROBANDO IDs ESPECÍFICOS QUE MENCIONASTE (1475, 404)...")

ids_especificos = [1475, 404, 1, 2, 3, 4, 5, 10, 100, 200]

print("   Bonos:")
for id_bono in ids_especificos:
    try:
        response = requests.get(
            f"{base_url}/bonos/{id_bono}",
            headers=headers,
            timeout=3
        )
        if response.status_code == 200:
            data = response.json().get("data", response.json())
            print(f"      ✓ /bonos/{id_bono} => {data.get('name')}")
    except:
        pass

print("   Descuentos:")
for id_desc in ids_especificos:
    try:
        response = requests.get(
            f"{base_url}/descuentos/{id_desc}",
            headers=headers,
            timeout=3
        )
        if response.status_code == 200:
            data = response.json().get("data", response.json())
            print(f"      ✓ /descuentos/{id_desc} => {data.get('name')}")
    except:
        pass

# 6. Probar obtener TODA la información disponible sin filtros
print("\n6. PROBANDO ENDPOINTS SIN FILTROS...")

endpoints_globales = [
    "/employees",
    "/bonos?limit=1000",
    "/descuentos?limit=1000",
    "/fixed-compensations?limit=1000",
]

for endpoint in endpoints_globales:
    try:
        response = requests.get(
            f"{base_url}{endpoint}",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", data) if isinstance(data, dict) else data

            if isinstance(items, list):
                print(f"   ✓ {endpoint} => {len(items)} items en total")
                # Buscar items que contengan las palabras que el usuario mencionó
                for item in items:
                    if isinstance(item, dict):
                        name = item.get("name", "").lower()
                        if any(keyword in name for keyword in ["home", "movilizacion", "colacion", "salud", "seguro"]):
                            print(f"      >> ENCONTRADO: {item.get('name')} (ID: {item.get('id')})")
            else:
                print(f"   - {endpoint} => Estructura diferente")
    except Exception as e:
        print(f"   ✗ {endpoint} => Error: {str(e)}")

print("\n" + "="*100)
print("FIN INVESTIGACIÓN EXHAUSTIVA")
print("="*100)
