#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Debug: buscar Riquelme de múltiples formas."""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

auth_token = os.getenv("BUK_AUTH_TOKEN")
subdomain = os.getenv("BUK_SUBDOMAIN")

base_url = f"https://{subdomain}.buk.cl/api/v1/chile"

session = requests.Session()
session.headers.update({
    "auth_token": auth_token,
    "Content-Type": "application/json"
})

print("\n" + "="*80)
print("DEBUG: BÚSQUEDA DE 'RIQUELME'")
print("="*80 + "\n")

# Primero, obtener TODOS los empleados activos y buscar Riquelme manualmente
print("1. Obteniendo TODOS los empleados activos...\n")

try:
    all_riquelmies = []
    page = 1

    while page <= 5:  # Máximo 5 páginas
        response = session.get(
            f"{base_url}/employees",
            params={"status": "activo", "page": page, "page_size": 100},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            employees = data.get("data", [])

            print(f"Página {page}: {len(employees)} empleados")

            # Buscar Riquelme manualmente
            for emp in employees:
                full_name = emp.get("full_name", "").lower()
                if "riquelme" in full_name:
                    all_riquelmies.append(emp)
                    print(f"  ✓ Encontrado: {emp.get('full_name')} (RUT: {emp.get('rut')})")

            if len(employees) < 100:
                break
        else:
            print(f"Error en página {page}: Status {response.status_code}")
            break

        page += 1

    print(f"\nTotal de Riquelmies encontrados: {len(all_riquelmies)}\n")

    # Ahora probar búsqueda con parámetro search
    print("2. Probando búsqueda con parámetro 'search'...\n")

    response = session.get(
        f"{base_url}/employees",
        params={"search": "Riquelme", "status": "activo", "page_size": 100},
        timeout=5
    )

    if response.status_code == 200:
        data = response.json()
        employees = data.get("data", [])
        print(f"Resultados de búsqueda con search='Riquelme': {len(employees)}")

        riquelme_in_search = [e for e in employees if "riquelme" in e.get("full_name", "").lower()]
        print(f"De los cuales contienen 'Riquelme': {len(riquelme_in_search)}")

        if riquelme_in_search:
            for emp in riquelme_in_search[:5]:
                print(f"  - {emp.get('full_name')} (RUT: {emp.get('rut')})")

    # Probar búsqueda sin status
    print("\n3. Probando búsqueda SIN filtro status...\n")

    response = session.get(
        f"{base_url}/employees",
        params={"search": "Riquelme", "page_size": 100},
        timeout=5
    )

    if response.status_code == 200:
        data = response.json()
        employees = data.get("data", [])
        print(f"Resultados de búsqueda sin status: {len(employees)}")

        riquelme_in_search = [e for e in employees if "riquelme" in e.get("full_name", "").lower()]
        print(f"De los cuales contienen 'Riquelme': {len(riquelme_in_search)}")

        if riquelme_in_search:
            for emp in riquelme_in_search[:5]:
                print(f"  - {emp.get('full_name')} (RUT: {emp.get('rut')}) - Status: {emp.get('status', 'N/A')}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
