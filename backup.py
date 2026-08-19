#!/usr/bin/env python3
"""Genera un respaldo completo del estado de la Suite ARP IA.

El código vive en GitHub, así que lo que este script rescata es lo que
*no* está versionado: las bases de datos y la configuración operativa.
Eso es justamente lo que hay que llevarse en una migración.

Uso:
    python backup.py                     # respaldo sin secretos (por defecto)
    python backup.py --incluir-secretos   # agrega .env y secrets.toml
    python backup.py --destino D:/copias  # carpeta de salida distinta

Restaurar: descomprimir el ZIP sobre la raíz del proyecto respetando rutas.
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# Rutas relativas a la raíz del proyecto.
DATOS = [
    ("data/analysis.db", "Base de análisis: empleados, compensaciones, IPC, UF"),
    ("src/analysis/data/auth.db", "Usuarios locales (solo desarrollo; en la nube se usan Secrets)"),
]

CONFIGURACION = [
    ("config/parameters.json", "Parámetros previsionales y tabla de impuesto único"),
    ("config/company_logos.json", "Logos por empresa"),
    ("requirements.txt", "Dependencias de Python"),
]

SECRETOS = [
    (".env", "Credenciales de la API de Buk (uso local)"),
    (".streamlit/secrets.toml", "Usuarios y token de Buk (equivalente a los Secrets de la nube)"),
]


def sha256(ruta: Path) -> str:
    """Huella del archivo, para verificar que el respaldo llegó íntegro."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def resumen_sqlite(ruta: Path) -> dict:
    """Cuenta las filas de cada tabla, para saber qué contiene el respaldo."""
    try:
        conn = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        tablas = {}
        for (nombre,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ):
            try:
                tablas[nombre] = conn.execute(f'SELECT COUNT(*) FROM "{nombre}"').fetchone()[0]
            except sqlite3.Error:
                tablas[nombre] = None
        conn.close()
        return tablas
    except sqlite3.Error as e:
        return {"__error__": str(e)}


def copiar_sqlite_consistente(origen: Path, destino: Path) -> None:
    """Copia una BD SQLite con la API de backup.

    Copiar el archivo a mano puede capturarlo a medio escribir si la app
    está corriendo; esta API entrega siempre un archivo consistente.
    """
    src = sqlite3.connect(f"file:{origen}?mode=ro", uri=True)
    dst = sqlite3.connect(destino)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Respaldo de la Suite ARP IA")
    parser.add_argument(
        "--incluir-secretos",
        action="store_true",
        help="Incluye .env y secrets.toml (contienen credenciales: guardar el ZIP en lugar seguro)",
    )
    parser.add_argument(
        "--destino",
        default=str(RAIZ / "backups"),
        help="Carpeta donde dejar el ZIP (por defecto ./backups)",
    )
    args = parser.parse_args()

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    carpeta_destino = Path(args.destino)
    carpeta_destino.mkdir(parents=True, exist_ok=True)
    ruta_zip = carpeta_destino / f"suitearp_backup_{marca}.zip"

    grupos = [("DATOS", DATOS), ("CONFIGURACION", CONFIGURACION)]
    if args.incluir_secretos:
        grupos.append(("SECRETOS", SECRETOS))

    manifiesto = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "proyecto": "Suite ARP IA",
        "incluye_secretos": args.incluir_secretos,
        "archivos": [],
        "omitidos": [],
    }

    temporales = []
    print(f"Respaldo -> {ruta_zip}\n")

    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for grupo, entradas in grupos:
            print(f"[{grupo}]")
            for rel, descripcion in entradas:
                origen = RAIZ / rel

                if not origen.exists():
                    print(f"  -- {rel}  (no existe, se omite)")
                    manifiesto["omitidos"].append({"ruta": rel, "motivo": "no existe"})
                    continue

                if origen.suffix == ".db":
                    # Snapshot consistente en un temporal, y ese es el que se comprime.
                    temporal = carpeta_destino / f".tmp_{marca}_{origen.name}"
                    copiar_sqlite_consistente(origen, temporal)
                    temporales.append(temporal)
                    a_comprimir = temporal
                    detalle = resumen_sqlite(temporal)
                else:
                    a_comprimir = origen
                    detalle = None

                z.write(a_comprimir, arcname=rel)
                tam = a_comprimir.stat().st_size

                entrada = {
                    "ruta": rel,
                    "descripcion": descripcion,
                    "bytes": tam,
                    "sha256": sha256(a_comprimir),
                }
                if detalle:
                    entrada["tablas"] = detalle
                manifiesto["archivos"].append(entrada)

                extra = ""
                if detalle and "__error__" not in detalle:
                    filas = sum(v for v in detalle.values() if isinstance(v, int))
                    extra = f"  ({len(detalle)} tablas, {filas} filas)"
                print(f"  OK {rel}  {tam/1024:.1f} KB{extra}")
            print()

        if not args.incluir_secretos:
            manifiesto["omitidos"].append({
                "ruta": ".env / .streamlit/secrets.toml",
                "motivo": "excluidos por defecto; usar --incluir-secretos",
            })

        z.writestr("MANIFIESTO.json", json.dumps(manifiesto, indent=2, ensure_ascii=False))
        z.writestr("COMO_RESTAURAR.txt", COMO_RESTAURAR)

    for t in temporales:
        t.unlink(missing_ok=True)

    print(f"Listo: {ruta_zip}  ({ruta_zip.stat().st_size/1024:.1f} KB)")
    if not args.incluir_secretos:
        print(
            "\nNota: no se incluyeron credenciales. El token de Buk y los usuarios\n"
            "      hay que respaldarlos aparte (ver MIGRACION.md), o volver a\n"
            "      correr con --incluir-secretos."
        )
    return 0


COMO_RESTAURAR = """RESTAURAR ESTE RESPALDO
=======================

1. Clonar el código:
       git clone https://github.com/ariquelme91/SuiteArp.git
       cd SuiteArp

2. Descomprimir este ZIP sobre la raíz del proyecto, respetando las rutas.
   Debe quedar:
       data/analysis.db
       config/parameters.json
       config/company_logos.json

3. Instalar dependencias:
       pip install -r requirements.txt

4. Credenciales (si este respaldo NO las incluye):
       - Crear .env con BUK_API_TOKEN y BUK_SUBDOMAIN
       - Para la nube: cargar la sección [usuarios] en los Secrets de Streamlit

5. Levantar:
       streamlit run app.py

Verificar que quedó bien: MANIFIESTO.json trae el conteo de filas por tabla
y el sha256 de cada archivo.
"""


if __name__ == "__main__":
    sys.exit(main())
