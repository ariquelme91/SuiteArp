# 🏗️ Arquitectura de la Aplicación

## Visión General

```
┌─────────────────────────────────────────────────────────────┐
│                      USUARIO (CLI)                          │
│                    (rich + inquirer)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   UI.PY (Interfaz)                          │
│  - Menú principal                                           │
│  - Búsqueda interactiva                                     │
│  - Captura de propuesta                                     │
│  - Visualización de comparativas                           │
└──────┬──────────────────────────┬──────────────────────────┘
       │                          │
       │                          │
┌──────▼────────────┐    ┌────────▼────────────────────────┐
│ BUK_CLIENT.PY     │    │ PAYROLL_ENGINE.PY               │
│                   │    │                                 │
│ - API Integration │    │ - Motor de cálculo              │
│ - Autenticación   │    │ - Descuentos legales            │
│ - Consultas       │    │ - Aportes empleador             │
│ - Manejo errores  │    │ - Impuesto único                │
│                   │    │ - Cálculo inverso               │
└───────────────────┘    └─────────────────────────────────┘
                                   │
                         ┌─────────▼─────────┐
                         │ SIMULATOR.PY      │
                         │                   │
                         │ - Comparaciones   │
                         │ - Impacto neto    │
                         │ - Análisis        │
                         └─────────┬─────────┘
                                   │
                         ┌─────────▼─────────┐
                         │ EXPORTER.PY       │
                         │                   │
                         │ - Excel reports   │
                         │ - Formato ejecutivo
                         │ - Estilos         │
                         └───────────────────┘
                                   │
                                   ▼
                            [ARCHIVO .XLSX]
```

## Componentes Principales

### 1. `buk_client.py` - Cliente API Buk

**Responsabilidades:**
- Gestionar autenticación y conexión con API Buk
- Consultar datos de colaboradores
- Validar formato de RUT chileno
- Manejar errores HTTP (401, 404, timeouts)
- Parsear respuestas de API

**Clases:**
- `Employee`: Dataclass con información de colaborador
- `BukClient`: Cliente HTTP con métodos:
  - `search_employee(rut)` - Busca por RUT
  - `list_employees(page, page_size)` - Listado con paginación
  - `test_connection()` - Prueba validez del token
  - `_parse_employee()` - Extrae datos relevantes

**Flujo:**
```
Usuario ingresa RUT
      ↓
BukClient.search_employee(rut)
      ↓
Validar formato RUT
      ↓
GET /employees?rut=XXX
      ↓
Parsear respuesta → Employee
      ↓
Retornar datos al UI
```

---

### 2. `payroll_engine.py` - Motor de Cálculo

**Responsabilidades:**
- Implementar normativa tributaria chilena completa
- Calcular haberes, descuentos y aportes
- Aplicar topes previsionales
- Calcular impuesto único con tabla SII
- Permitir cálculo inverso (líquido → base)

**Clases:**
- `PayrollCalculation`: Dataclass con resultado completo
- `PayrollEngine`: Motor con métodos:
  - `calculate()` - Liquidación completa
  - `reverse_calculate_base_salary()` - Inverso
  - `_calculate_gratification()` - Art. 50 CT
  - `_calculate_afp()` - AFP + comisión
  - `_calculate_unique_tax()` - IUSC según tramos

**Cálculos:**

```
HABERES
├── Base Salary: Ingreso del usuario
├── Gratification: MIN(25% * Base, (4.75 * IMM) / 12)
├── Collation: Asignación colación
├── Mobility: Asignación movilización
└── Total Earnings: Suma de todo

DESCUENTOS
├── AFP: (10% + 1.97% comisión) × Tope AFP
├── Salud: 7% × Tope AFP
├── AFC: (0.6% indefinido | 0.0% plazo) × Tope AFC
└── Impuesto Único: Tabla SII según UTM

APORTES EMPLEADOR
├── SIS: 1.49% × Tope AFP
├── AFC Empleador: (2.4% indefinido | 3.0% plazo) × Tope AFC
└── Mutual: 0.93% × Tope AFP
```

**Parámetros:**
Los parámetros (`uf_value`, `utm_value`, etc.) se cargan de `config/parameters.json` y actualizan mensualmente.

---

### 3. `simulator.py` - Simulador Comparativo

**Responsabilidades:**
- Comparar situación actual vs propuesta
- Calcular variaciones ($ y %)
- Analizar impacto económico
- Preparar datos para exportación

**Clases:**
- `ComparisonResult`: Dataclass con resultados
- `Simulator`: Orquestador con métodos:
  - `compare()` - Comparativa completa
  - `get_impact_summary()` - Resumen de variaciones
  - `calculate_net_impact()` - Impacto neto

**Datos de Entrada:**
```python
Simulator.compare(
    employee_name="Juan Pérez",
    employee_rut="12.345.678-9",
    change_date="01/09/2026",
    # Situación actual
    current_base_salary=1_500_000,
    current_collation=200_000,
    current_mobility=150_000,
    # Propuesta
    proposal_base_salary=1_750_000,  # Puede ser diferente
    proposal_collation=200_000,
    proposal_mobility=150_000,
    contract_type="indefinido"
)
```

**Salida:**
```
ComparisonResult {
    current: PayrollCalculation,   # Situación actual
    proposal: PayrollCalculation,  # Situación propuesta
    change_date: str,
    employee_name: str,
    employee_rut: str
}
```

---

### 4. `exporter.py` - Generador de Reportes

**Responsabilidades:**
- Generar archivos Excel con formato ejecutivo
- Aplicar estilos y colores profesionales
- Insertar tablas de comparación
- Crear secciones de impacto y observaciones

**Clases:**
- `ExcelExporter`: Generador con métodos:
  - `export_comparison()` - Exporta ComparisonResult a .xlsx
  - `_add_header()` - Encabezado empresa
  - `_add_comparison_table()` - Tabla principal
  - `_add_impact_summary()` - Resumen de impacto
  - `_add_observations()` - Observaciones legales

**Estilos:**
- Encabezados: Azul oscuro (#1F4E78)
- Secciones: Azul claro (#D9E1F2)
- Totales: Verde claro (#E2EFDA)
- Positivos: Verde (#C6EFCE)
- Negativos: Rojo (#FFC7CE)

**Archivo Generado:**
```
Propuesta_Renta_12345678-9_20260814_143022.xlsx
├── Encabezado con nombre empresa
├── Datos del colaborador
├── Tabla de comparación con colores
├── Resumen de impacto
└── Observaciones legales
```

---

### 5. `ui.py` - Interfaz Interactiva

**Responsabilidades:**
- Presentar menú principal interactivo
- Capturar datos de usuario
- Orquestar flujo de propuesta
- Mostrar resultados de forma clara

**Clases:**
- `InteractiveUI`: Interfaz con métodos:
  - `show_welcome()` - Pantalla inicial
  - `show_main_menu()` - Menú de opciones
  - `search_employee_by_rut()` - Búsqueda interactiva
  - `list_employees()` - Listado paginado
  - `create_proposal()` - Flujo de propuesta
  - `display_comparison()` - Mostrar resultados
  - `export_to_excel()` - Exportar reporte
  - `run_interactive_session()` - Loop principal

**Flujo Principal:**
```
┌─────────────────────┐
│  show_welcome()     │
└────────┬────────────┘
         ▼
┌──────────────────────────┐
│  show_main_menu()        │
│  1. Buscar por RUT       │
│  2. Listar empleados     │
│  3. Configurar params    │
│  4. Salir                │
└────────┬────────────────┘
         │
    ┌────┴────┬──────┬──────┐
    ▼         ▼      ▼      ▼
  [1]       [2]    [3]    [4]
   │         │      │      │
   ▼         ▼      │      └─→ EXIT
BUK API   BUK API   │
   │         │      └─→ Parámetros (v2)
   ▼         ▼
Employee  Seleccionar
   │         │
   └────┬────┘
        ▼
   ¿Crear propuesta?
        │ SÍ
        ▼
  create_proposal()
        │
        ├─ ¿Cambios org? (empresa/cargo/jefe)
        ├─ Nuevos haberes
        ├─ Opción cálculo inverso
        └─ Calcular comparativa
           │
           ▼
      simulator.compare()
           │
           ▼
      display_comparison()
           │
           ▼
      ¿Exportar Excel?
           │ SÍ
           ▼
      export_to_excel()
           │
           ▼
          .xlsx
```

---

## Flujo de Datos

### Búsqueda Simple

```
Usuario: "12.345.678-9"
    ↓
UI.search_employee_by_rut()
    ↓
BukClient.search_employee()
    ↓
GET https://empresa.buk.cl/api/v1/chile/employees?rut=123456789
    ↓
Parsear response → Employee
    ↓
UI.display_employee_card()
```

### Creación de Propuesta

```
Employee (actual) + Datos Propuesta
    ↓
Simulator.compare(
    current_base_salary,
    proposal_base_salary,
    ...
)
    ↓
PayrollEngine.calculate() × 2
    ├─ calculate(base=1.5M, ...)  → current
    └─ calculate(base=1.75M, ...) → proposal
    ↓
ComparisonResult
    ├─ current: PayrollCalculation
    ├─ proposal: PayrollCalculation
    └─ metadata
    ↓
UI.display_comparison()
    ├─ Rich Table
    └─ Impact Summary
    ↓
ExcelExporter.export_comparison()
    ↓
propuesta_renta_xxx.xlsx
```

### Cálculo Inverso

```
Target Liquid: $1,800,000
    ↓
PayrollEngine.reverse_calculate_base_salary()
    ├─ Estimación inicial: $1,800,000 × 1.35
    ├─ Iteración 1: calculate() → ajustar ratio
    ├─ Iteración 2: calculate() → ajustar ratio
    ├─ ... (hasta convergencia)
    └─ Retornar base_salary
    ↓
Validación:
calculate(base_salary_calculated)
    → net_salary ≈ $1,800,000 ✓
```

---

## Estructuras de Datos

### Employee (desde Buk)

```python
@dataclass
class Employee:
    rut: str                      # 12.345.678-9
    full_name: str               # Juan Pérez García
    email: Optional[str]
    start_date: Optional[str]
    company_name: Optional[str]  # Empresa LTDA
    job_title: Optional[str]     # Gerente Ventas
    supervisor: Optional[str]    # María García
    base_salary: float           # 1,500,000
    contract_type: str           # "indefinido" | "plazo_fijo"
    fixed_items: List[Dict]      # Ítems adicionales de Buk
```

### PayrollCalculation (Resultado)

```python
@dataclass
class PayrollCalculation:
    # Haberes
    base_salary: float
    gratification: float
    collation: float
    mobility: float
    total_taxable: float
    total_non_taxable: float
    total_earnings: float
    
    # Descuentos
    afp_discount: float
    health_discount: float
    afc_discount: float
    unique_tax: float
    total_discounts: float
    
    # Neto
    net_salary: float
    
    # Aportes Empleador
    employer_sis: float
    employer_afc: float
    employer_mutual: float
    total_employer_cost: float
    
    # Bases para descuentos
    taxable_base: float
    afp_taxable_base: float
    afc_taxable_base: float
```

### ComparisonResult (Comparativa)

```python
@dataclass
class ComparisonResult:
    current: PayrollCalculation   # Situación actual
    proposal: PayrollCalculation  # Situación propuesta
    change_date: str              # "01/09/2026"
    employee_name: str
    employee_rut: str
```

---

## Consideraciones Técnicas

### Validación de Datos

- **RUT**: Formato `XX.XXX.XXX-X`, se normaliza a número
- **Montos**: Validar que sean positivos
- **Fechas**: Formato `DD/MM/YYYY`
- **Contrato**: Solo `"indefinido"` o `"plazo_fijo"`

### Manejo de Errores

1. **Conexión Buk**:
   - 401: Token inválido → Solicitar recredencialización
   - 404: Colaborador no encontrado → Permitir reintentar
   - Timeout: → Reintentar con backoff
   - SSL/Certificados: → Log y notificar

2. **Cálculos**:
   - Montos negativos: → Setear a 0
   - Divisiones por cero: → Manejo explícito
   - Convergencia inversa: → Máximo 10 iteraciones

3. **Excel**:
   - Permisos de escritura: → Validar ruta
   - Archivo bloqueado: → Generar nombre único con timestamp
   - Formato incompatible: → Usar `openpyxl`

### Performance

- **Búsqueda Buk**: ~200-500ms (cachear si es posible)
- **Cálculo Nómina**: <10ms (matemática pura)
- **Generación Excel**: ~100-200ms
- **Cálculo Inverso**: ~50ms (10 iteraciones)

### Seguridad

- No loguear tokens/credenciales
- Variables sensibles en `.env` (nunca en código)
- Validar inputs antes de usar
- No exponer rutas internas en mensajes de error

---

## Extensibilidad Futura

### v1.1: Parámetros Dinámicos
```python
# Actualizar parámetros desde UI
UI.configure_parameters()
  └─ Guardar en config/parameters.json
```

### v1.2: Multi-colaborador
```python
# Procesar propuestas en lote
UI.import_csv()
  └─ Generar múltiples reportes Excel
```

### v1.3: Integración Streamlit
```python
# UI web local
streamlit run src/streamlit_app.py
```

### v1.4: Base de Datos
```python
# Persistencia de propuestas
DB.save_proposal(comparison)
DB.load_proposal(proposal_id)
```

---

## Testing

Ejecutar pruebas de validación:

```bash
python test_example.py
```

Esto valida:
- ✓ Cálculos de nómina
- ✓ Cálculo inverso (convergencia)
- ✓ Comparativas
- ✓ Parámetros cargados

---

**Diagrama de Dependencias:**

```
main.py
  ├─ config/parameters.json
  ├─ .env
  └─ src/
      ├─ __init__.py
      ├─ ui.py ────┬─ buk_client.py
      │            ├─ payroll_engine.py ─ parameters.json
      │            ├─ simulator.py ─────┘
      │            └─ exporter.py (openpyxl)
      ├─ buk_client.py (requests)
      ├─ payroll_engine.py
      ├─ simulator.py
      └─ exporter.py
```

**Dependencias Externas:**
- `requests`: HTTP client para Buk API
- `openpyxl`: Generación de Excel
- `pandas`: Manipulación de datos (reservado para v1.2+)
- `rich`: Terminal UI con estilos
- `inquirer`: Prompts interactivos
- `python-dotenv`: Variables de entorno
