"""Script de DEBUG para probar acceso directo a API de Buk"""
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

rut = "17771319-8"  # Tu RUT
rut_formatted = re.sub(r'[.-]', '', rut).upper()

print("="*80)
print(f"DEBUG - Extrayendo datos de: {rut}")
print("="*80)

# 1. Obtener ficha completa
print("\n1. OBTENIENDO FICHA COMPLETA...")
response = requests.get(
    f"{base_url}/employees/{rut_formatted}",
    headers=headers,
    timeout=10
)
employee_data = response.json().get("data", response.json())

print(f"   Status: {employee_data.get('status')}")
print(f"   Nombre: {employee_data.get('full_name')}")

current_job = employee_data.get("current_job", {})
print(f"\n   Current Job Status: {current_job.get('status')}")
print(f"   Sueldo Base: {current_job.get('base_wage')}")

# 2. Ver estructura de fixed_items
print("\n2. ESTRUCTURA DE FIXED ITEMS...")
fixed_items = current_job.get("fixed_items", [])
print(f"   Total de fixed items: {len(fixed_items)}")
for i, item in enumerate(fixed_items, 1):
    print(f"\n   Item {i}:")
    print(json.dumps(item, indent=4, default=str))

# 3. Ver estructura de discounts
print("\n3. ESTRUCTURA DE DISCOUNTS...")
discounts = current_job.get("discounts", [])
print(f"   Total de discounts: {len(discounts)}")
for i, discount in enumerate(discounts, 1):
    print(f"\n   Discount {i}:")
    print(json.dumps(discount, indent=4, default=str))

# 4. Intentar acceder a endpoints de bonos
print("\n4. PROBANDO ENDPOINTS DE BONOS...")
if fixed_items:
    for item in fixed_items[:2]:  # Solo 2 primeros
        item_id = item.get("id")
        print(f"\n   Intentando: /bonos/{item_id}")
        try:
            response = requests.get(f"{base_url}/bonos/{item_id}", headers=headers, timeout=5)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Datos: {json.dumps(response.json(), indent=4, default=str)[:500]}")
            else:
                print(f"   Error: {response.text[:200]}")
        except Exception as e:
            print(f"   Exception: {str(e)}")

# 5. Intentar acceder a endpoints de descuentos
print("\n5. PROBANDO ENDPOINTS DE DESCUENTOS...")
if discounts:
    for discount in discounts[:2]:  # Solo 2 primeros
        discount_id = discount.get("id")
        print(f"\n   Intentando: /descuentos/{discount_id}")
        try:
            response = requests.get(f"{base_url}/descuentos/{discount_id}", headers=headers, timeout=5)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Datos: {json.dumps(response.json(), indent=4, default=str)[:500]}")
            else:
                print(f"   Error: {response.text[:200]}")
        except Exception as e:
            print(f"   Exception: {str(e)}")

# 6. Intentar otros endpoints posibles
print("\n6. PROBANDO OTROS ENDPOINTS POSIBLES...")
endpoints_to_try = [
    f"/employees/{rut_formatted}/fixed-items",
    f"/employees/{rut_formatted}/discounts",
    f"/employees/{rut_formatted}/bonos",
    f"/employees/{rut_formatted}/haberes",
    f"/fixed-items",
    f"/descuentos",
]

for endpoint in endpoints_to_try:
    print(f"\n   Intentando: {endpoint}")
    try:
        response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✓ ENCONTRADO - Primeros 300 chars:")
            data = response.json()
            print(json.dumps(data, indent=2, default=str)[:300])
    except Exception as e:
        print(f"   Error: {str(e)[:100]}")

print("\n" + "="*80)
print("FIN DEBUG")
print("="*80)
