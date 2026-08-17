"""Punto de entrada de la aplicación Propuestas de Renta."""

import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)
console = Console()

# Cargar variables de entorno
load_dotenv()


def load_parameters() -> dict:
    """Carga parámetros mensuales desde config/parameters.json."""
    parameters_file = Path("config/parameters.json")

    if not parameters_file.exists():
        console.print("[red]Error: No se encontró config/parameters.json[/red]")
        sys.exit(1)

    try:
        with open(parameters_file, "r", encoding="utf-8") as f:
            parameters = json.load(f)
        logger.info("Parámetros cargados correctamente")
        return parameters
    except Exception as e:
        console.print(f"[red]Error cargando parámetros: {e}[/red]")
        sys.exit(1)


def validate_environment() -> bool:
    """Valida que las variables de entorno estén configuradas."""
    auth_token = os.getenv("BUK_AUTH_TOKEN")
    subdomain = os.getenv("BUK_SUBDOMAIN")

    if not auth_token or not subdomain:
        console.print(
            "[red]Error: Variables BUK_AUTH_TOKEN y BUK_SUBDOMAIN no están configuradas[/red]"
        )
        console.print(
            "[yellow]Configure el archivo .env con sus credenciales de Buk[/yellow]"
        )
        console.print("[cyan]Ejemplo:[/cyan]")
        console.print("BUK_AUTH_TOKEN=tu_token_aqui")
        console.print("BUK_SUBDOMAIN=tu_subdominio")
        return False

    return True


def main():
    """Función principal."""
    console.print("[bold cyan]SISTEMA DE PROPUESTAS DE RENTA - Buk Chile[/bold cyan]\n")

    # Validar configuración
    if not validate_environment():
        sys.exit(1)

    # Cargar parámetros
    parameters = load_parameters()

    # Inicializar componentes
    from src.buk_client import BukClient
    from src.payroll_engine import PayrollEngine
    from src.ui import InteractiveUI

    buk_client = BukClient(
        auth_token=os.getenv("BUK_AUTH_TOKEN"),
        subdomain=os.getenv("BUK_SUBDOMAIN"),
    )

    # Prueba de conexión
    console.print("[cyan]Validando conexión con API Buk...[/cyan]")
    if not buk_client.test_connection():
        console.print("[red]Error: No se pudo conectar con la API Buk[/red]")
        console.print("[yellow]Verifique:[/yellow]")
        console.print("  - Token de autenticación válido")
        console.print("  - Subdominio correcto")
        console.print("  - Conexión a internet")
        sys.exit(1)

    console.print("[green]✓ Conexión exitosa[/green]\n")

    # Inicializar motor de cálculo
    payroll_engine = PayrollEngine(parameters)

    # Inicializar interfaz
    ui = InteractiveUI(buk_client, payroll_engine)

    # Ejecutar sesión interactiva
    try:
        ui.run_interactive_session()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operación cancelada por el usuario[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error inesperado: {e}[/red]")
        logger.exception("Error en ejecución principal")
        sys.exit(1)


if __name__ == "__main__":
    main()
