# PROPUESTAS DE RENTA - Sistema Automático Buk Chile

Sistema modular e interactivo para automatizar el proceso de **Propuestas de Renta** integrándose directamente con la API de Buk y calculando la estructura salarial chilena completa.

> ⚠️ **Este documento es anterior al sistema de autenticación (agosto 2026).**
> La referencia vigente es **[DOCUMENTACION.md](DOCUMENTACION.md)**; para
> respaldos y cambios de hosting, **[MIGRACION.md](MIGRACION.md)**.

## 📋 Características

✅ **Integración API Buk** - Consulta datos de colaboradores en tiempo real
✅ **Motor de Cálculo Completo** - Nómina chilena con normativa vigente:
   - Sueldo Base + Gratificación Legal (Art. 50)
   - Descuentos: AFP, Salud, AFC, IUSC
   - Aportes Empleador: SIS, AFC Empleador, Mutual
   - Topes previsionales actualizables

✅ **Interfaz Interactiva** - CLI amigable con Rich e Inquirer
✅ **Simulación Comparativa** - Actual vs Propuesta en un cuadro ejecutivo
✅ **Exportación Excel** - Reportes formateados listos para presentar
✅ **Cálculo Inverso** - Ingresar líquido objetivo y despejar sueldo base requerido

## 🏗️ Estructura del Proyecto

```
propuesta_renta_buk/
├── .env.example              # Plantilla de configuración
├── .env                      # Configuración (NO commitear)
├── requirements.txt          # Dependencias Python
├── README.md                 # Este archivo
├── main.py                   # Punto de entrada
├── config/
│   └── parameters.json       # Parámetros mensuales (UF, UTM, etc.)
├── src/
│   ├── __init__.py
│   ├── buk_client.py         # Cliente API Buk
│   ├── payroll_engine.py     # Motor de cálculo de nómina
│   ├── simulator.py          # Lógica comparativa
│   ├── exporter.py           # Generador de reportes Excel
│   └── ui.py                 # Interfaz interactiva
└── app.log                   # Log de ejecuciones
```

## ⚙️ Instalación y Configuración

### Requisitos Previos

- Python 3.8+
- pip (gestor de paquetes)
- Credenciales válidas de Buk (Auth Token y Subdominio)

### Paso 1: Clonar o Descargar el Proyecto

```bash
cd propuesta_renta_buk
```

### Paso 2: Crear Entorno Virtual (Recomendado)

```bash
python -m venv venv

# En Windows
venv\Scripts\activate

# En macOS/Linux
source venv/bin/activate
```

### Paso 3: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Configurar Credenciales Buk

1. Copiar `.env.example` a `.env`:
   ```bash
   cp .env.example .env
   ```

2. Editar `.env` con sus credenciales:
   ```env
   BUK_API_TOKEN=your_auth_token_here
   BUK_SUBDOMAIN=your_subdomain_here
   DEBUG=False
   APP_MODE=cli
   ```

   **Dónde obtener las credenciales:**
   - `BUK_API_TOKEN`: Generar en Portal Buk → Configuración → API → Personal Access Tokens
   - `BUK_SUBDOMAIN`: El subdominio de su empresa en Buk (ej: si accede a `empresa.buk.cl`, use `empresa`)

### Paso 5: Validar Parámetros Mensuales

Editar `config/parameters.json` con los valores del mes actual:
- `uf_value`: Valor UF actual
- `utm_value`: Valor UTM actual
- `imm_value`: Ingreso Mínimo Mensual
- Tasas de descuentos y aportes según normativa vigente

## 🚀 Uso

### Ejecutar la Aplicación

```bash
python main.py
```

La aplicación se abrirá en modo interactivo con un menú principal:

```
¿Qué desea hacer?
1. Buscar Colaborador por RUT
2. Listar Colaboradores
3. Configurar Parámetros
4. Salir
```

### Flujo de Creación de una Propuesta

1. **Seleccionar Colaborador**
   - Opción 1: Buscar por RUT (ej: 12.345.678-9)
   - Opción 2: Listar y seleccionar de página

2. **Revisar Información Actual**
   - Se muestra tarjeta con datos contractuales y sueldo actual

3. **Crear Propuesta**
   - Responder preguntas sobre cambios organizacionales (empresa, cargo, jefe)
   - Ingresar fecha de aplicación
   - Ingresar nuevos haberes (colación, movilización, etc.)
   - **Opción de cálculo inverso**: Ingresar sueldo líquido deseado y el sistema calcula automáticamente el sueldo base requerido

4. **Ver Comparativa**
   - Tabla completa con concepto, actual, propuesta, variación ($), variación (%)
   - Resumen de impacto económico para empleado y empresa

5. **Exportar a Excel**
   - Generar archivo con formato ejecutivo listo para presentar a gerencia
   - Archivo guardado con timestamp para trazabilidad

## 📊 Cálculos Implementados

### Haberes Mensual

```
Total Imponible = Sueldo Base + Gratificación + Bonos
Total No Imponible = Colación + Movilización + Asignaciones Exentas
Total Haberes = Total Imponible + Total No Imponible
```

### Descuentos Trabajador

```
AFP = 10% + Comisión (≈1.97%) sobre base topada en 84.3 UF
Salud = 7% sobre base topada en 84.3 UF (o Isapre pactada)
AFC = 0.6% (indefinido) ó 0.0% (plazo fijo) sobre base topada en 126.6 UF
Impuesto Único = Aplicar tabla SII según UTM (con factor y rebaja)

Base Tributable = Total Imponible - AFP - Salud - AFC
```

### Aportes Empleador

```
SIS = 1.49% sobre base topada en 84.3 UF
AFC Empleador = 2.4% (indefinido) ó 3.0% (plazo fijo) sobre base topada en 126.6 UF
Mutual = 0.93% (tasa básica) sobre base topada en 84.3 UF

Costo Empresa = Total Haberes + SIS + AFC Empleador + Mutual
```

### Sueldo Líquido

```
Sueldo Líquido = Total Haberes - (AFP + Salud + AFC + Impuesto Único + Otros Descuentos)
```

## 🔧 Parámetros Configurables

Editar `config/parameters.json`:

```json
{
  "periodo": "2026-08",
  "uf_value": 38500,           // Valor UF actual
  "utm_value": 67000,          // Valor UTM actual
  "imm_value": 500000,         // Ingreso Mínimo Mensual
  "tope_afp_uf": 84.3,         // Tope AFP en UF
  "tope_afc_uf": 126.6,        // Tope AFC en UF
  "afp_percent": 10.0,         // % AFP obligatorio
  "salud_percent": 7.0,        // % Salud (7% legal)
  "afc_trabajador_indefinido": 0.6,
  "afc_trabajador_plazo_fijo": 0.0,
  "afc_empleador_indefinido": 2.4,
  "afc_empleador_plazo_fijo": 3.0,
  "sis_percent": 1.49,         // % SIS empleador
  "tasa_mutual_base": 0.93,    // % Mutual base
  "tabla_impuesto_unico": [...]  // Tabla de tramos SII
}
```

## 📝 Ejemplos de Uso

### Ejemplo 1: Búsqueda Simple

```bash
$ python main.py
> 1 (Buscar Colaborador)
> 12.345.678-9
> Sí (crear propuesta)
> No (no cambio de empresa)
> No (no cambio de cargo)
> No (no cambio de jefe)
> [Ingresar fecha y haberes propuestos]
```

### Ejemplo 2: Cálculo Inverso de Sueldo

```bash
> Buscar colaborador...
> Crear propuesta
> [Seleccionar opción "Calcular Base para Líquido Objetivo"]
> Ingresar Sueldo Líquido Objetivo: $2.500.000
> [Sistema calcula automáticamente el Sueldo Base requerido]
```

## 🐛 Troubleshooting

### Error: `BUK_API_TOKEN` no está configurado

```
Solución: Crear archivo .env con credenciales válidas
```

### Error: No se puede conectar a la API Buk

```
Verifique:
1. Token es válido (no expirado, no revocado)
2. Subdominio es correcto
3. Conexión a internet activa
4. Token tiene permisos de "Datos Sensibles"
```

### Error: Colaborador no encontrado

```
Verifique:
1. RUT está en formato correcto (ej: 12.345.678-9)
2. Colaborador existe en su base de datos Buk
3. Token tiene permisos de lectura de empleados
```

### Cálculos no coinciden con nómina actual

```
Posibles causas:
1. Parámetros (UF, UTM) desactualizados
2. Descuentos adicionales o bonos no capturados
3. Afiliación a Isapre especial (no 7% estándar)
4. Comisión AFP diferente a estimada (1.97%)

Solución: Ajustar parámetros en config/parameters.json
```

## 📈 Actualizaciones Mensuales Recomendadas

Cada mes, actualizar en `config/parameters.json`:

1. **UF Value** - Consultar en [Mindicador.cl](https://mindicador.cl/uf)
2. **UTM Value** - Consultar en [Tesorería Chile](https://www.tesoreria.cl)
3. **Tasa SIS** - Verificar en SII
4. **Tasa Mutual** - Según póliza de empresa
5. **Tabla de Impuesto Único** - Actualizar según tramos vigentes del SII

## 📄 Exportación de Reportes

Los reportes Excel generados incluyen:

- ✅ Información del colaborador (RUT, nombre, cargo, empresa)
- ✅ Fecha de aplicación de propuesta
- ✅ Tabla comparativa completa con colores
- ✅ Resumen de impacto (mensual y anualizado)
- ✅ Sección de observaciones legales
- ✅ Formato ejecutivo listo para presentar

Los archivos se guardan con timestamp para evitar sobrescrituras:
```
Propuesta_Renta_12345678-9_20260814_143022.xlsx
```

## 🔐 Seguridad

⚠️ **IMPORTANTE:**
- Nunca commitear el archivo `.env` a Git
- No compartir `BUK_API_TOKEN` por canales inseguros
- El archivo `.gitignore` debe incluir:
  ```
  .env
  *.log
  __pycache__/
  *.xlsx
  venv/
  ```
- Los datos de empleados son sensibles - almacenar archivos Excel en carpeta segura

## 📞 Soporte y Mantenimiento

Para reportar problemas o sugerencias:

1. Revisar archivo `app.log` para detalles de errores
2. Contactar a equipo de Recursos Humanos
3. Validar parámetros mensuales sean correctos
4. Actualizar librerías: `pip install --upgrade -r requirements.txt`

## 📋 Normativa Legal Implementada

✅ Artículo 50 Código del Trabajo - Gratificación Legal
✅ Ley 19.728 - Sistema AFP
✅ Decreto Ley 3.500 - Sistema de Pensiones
✅ Ley 18.418 - Seguro de Cesantía (AFC)
✅ Código Tributario - Impuesto Único Segunda Categoría
✅ Ley 18.834 - Mutual de Seguridad

## 📄 Licencia

Uso interno - Empresa

---

**Versión:** 1.0.0
**Última actualización:** Agosto 2026
