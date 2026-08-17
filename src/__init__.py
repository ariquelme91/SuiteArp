"""Módulo de Propuestas de Renta - Sistema integrado con Buk."""

from .buk_client import BukClient, Employee
from .payroll_engine import PayrollEngine, PayrollCalculation
from .simulator import Simulator, ComparisonResult
from .exporter import ExcelExporter
from .ui import InteractiveUI

__all__ = [
    "BukClient",
    "Employee",
    "PayrollEngine",
    "PayrollCalculation",
    "Simulator",
    "ComparisonResult",
    "ExcelExporter",
    "InteractiveUI",
]

__version__ = "1.0.0"
