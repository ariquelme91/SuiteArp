# 📡 Referencia API Buk Chile

Documentación de referencia para la integración con API Buk.

## Configuración Base

**URL Base:**
```
https://{SUBDOMAIN}.buk.cl/api/v1/chile
```

**Headers Requeridos:**
```
auth_token: {BUK_AUTH_TOKEN}
Content-Type: application/json
```

⚠️ **Nota**: Se usa `auth_token` en header, NO Bearer Token.

---

## Autenticación

### Obtener Token

1. Acceder a Portal Buk: https://portal.buk.cl
2. Ir a **Configuración** → **API** → **Personal Access Tokens**
3. Crear nuevo token con permisos:
   - ✓ Lectura de Empleados
   - ✓ Datos Sensibles (sueldos, contacto)
   - ✓ Información de Contratos
4. Copiar el token generado

### Validación de Token

```
GET /employees?page_size=1
```

Si retorna:
- `200 OK` → Token válido
- `401 Unauthorized` → Token inválido/expirado
- `403 Forbidden` → Permisos insuficientes

---

## Endpoints

### 1. Buscar Colaborador por RUT

```
GET /employees?rut={rut}
```

**Parámetros:**
- `rut` (string): RUT sin formato (123456789)

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "emp_123abc",
      "person": {
        "id": "per_456def",
        "rut": "12.345.678-9",
        "full_name": "Juan Pérez García",
        "email": "juan.perez@empresa.com",
        "phone": "+56912345678"
      },
      "current_job": {
        "id": "job_789ghi",
        "start_date": "2020-01-15",
        "contract_type": "indefinido",
        "company": {
          "id": "cmp_111jkl",
          "name": "Empresa LTDA"
        },
        "role": {
          "id": "rol_222mno",
          "name": "Gerente Ventas"
        },
        "boss": {
          "id": "emp_333pqr",
          "full_name": "María García López"
        },
        "salary": {
          "base_salary": 1500000,
          "currency": "CLP"
        },
        "items": [
          {
            "id": "item_444stu",
            "name": "Colación",
            "amount": 200000,
            "is_taxable": false
          },
          {
            "id": "item_555vwx",
            "name": "Movilización",
            "amount": 150000,
            "is_taxable": false
          },
          {
            "id": "item_666yza",
            "name": "Bono Desempeño",
            "amount": 500000,
            "is_taxable": true
          }
        ]
      },
      "status": "active"
    }
  ]
}
```

**Errores Comunes:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Employee not found"
  }
}
```

---

### 2. Listar Colaboradores (Paginado)

```
GET /employees?page={page}&page_size={page_size}
```

**Parámetros:**
- `page` (int, opcional): Número de página (default: 1)
- `page_size` (int, opcional): Registros por página (default: 50, máx: 200)

**Response (200 OK):**
```json
{
  "data": [
    { "id": "emp_001", "person": {...}, "current_job": {...} },
    { "id": "emp_002", "person": {...}, "current_job": {...} },
    ...
  ],
  "meta": {
    "page": 1,
    "page_size": 50,
    "total": 256,
    "total_pages": 6
  }
}
```

---

## Mapeo de Campos

| Campo Buk | Uso en App | Tipo | Notas |
|-----------|-----------|------|-------|
| `person.rut` | RUT del colaborador | string | Formateado con puntos y guión |
| `person.full_name` | Nombre completo | string | Usado en reportes |
| `person.email` | Email contacto | string | Informativo |
| `current_job.start_date` | Fecha ingreso | date | ISO format (YYYY-MM-DD) |
| `current_job.contract_type` | Tipo contrato | enum | "indefinido" \| "plazo_fijo" |
| `current_job.company.name` | Razón social | string | Para comparativa |
| `current_job.role.name` | Cargo actual | string | Para comparativa |
| `current_job.boss.full_name` | Jefe directo | string | Para comparativa |
| `current_job.salary.base_salary` | Sueldo base actual | number | En pesos CLP |
| `current_job.items` | Asignaciones | array | Colación, movilización, bonos |
| `item.is_taxable` | ¿Es imponible? | boolean | Afecta cálculos de descuentos |

---

## Campos Requeridos para Cálculos

La aplicación **requiere** como mínimo:

```python
{
  "rut": str,                    # RUT
  "full_name": str,              # Nombre
  "contract_type": str,          # indefinido | plazo_fijo
  "base_salary": float,          # Sueldo base
  "company_name": str,           # Empresa (puede faltar)
  "job_title": str,              # Cargo (puede faltar)
}
```

---

## Limitaciones y Consideraciones

### Rate Limiting
- Máximo 1000 requests/hora por token
- Si se excede: `429 Too Many Requests`
- Solución: Implementar retry con backoff exponencial

### Paginación
- Máximo 200 registros por página
- Para listar toda la empresa, hacer múltiples requests
- Usar `meta.total_pages` para saber cuántas solicitudes hacer

### Datos Desactualizados
- API puede tener latencia de hasta 1 minuto
- No aceptar cambios de Buk mientras se crea propuesta
- Revalidar antes de exportar a Excel

### Seguridad
- Token es secreto: NO loguear, NO exponer en URLs
- HTTPS obligatorio
- Token expira después de 90 días (regenerar periódicamente)

---

## Ejemplos de Uso en la Aplicación

### Buscar por RUT

```python
from src.buk_client import BukClient

client = BukClient(
    auth_token="pk_live_...",
    subdomain="empresa"
)

# Búsqueda simple
employee = client.search_employee("12.345.678-9")

if employee:
    print(f"Encontrado: {employee.full_name}")
    print(f"Sueldo Base: ${employee.base_salary:,.0f}")
else:
    print("Colaborador no encontrado")
```

### Listar Empleados

```python
# Página 1
employees = client.list_employees(page=1, page_size=50)

for emp in employees:
    print(f"{emp.rut} - {emp.full_name} - {emp.job_title}")

# Página siguiente
employees = client.list_employees(page=2, page_size=50)
```

### Test de Conexión

```python
if client.test_connection():
    print("✓ Conexión exitosa")
else:
    print("✗ Token inválido o permisos insuficientes")
```

---

## Manejo de Errores

### Errores HTTP Comunes

| Código | Significado | Acción |
|--------|------------|--------|
| 200 | OK | Procesar respuesta normalmente |
| 400 | Bad Request | Validar parámetros (RUT formato) |
| 401 | Unauthorized | Token inválido, regenerar |
| 403 | Forbidden | Permisos insuficientes |
| 404 | Not Found | Colaborador no existe en Buk |
| 429 | Too Many Requests | Esperar y reintentar con backoff |
| 500 | Server Error | Reintentar más tarde |
| 503 | Service Unavailable | API en mantenimiento |

### Implementación en BukClient

```python
try:
    response = self.session.get(
        f"{self.base_url}/employees",
        params={"rut": rut_clean},
        timeout=10
    )
    response.raise_for_status()
    
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        logger.error("Token inválido o sin permisos de datos sensibles")
    elif e.response.status_code == 404:
        logger.warning(f"Colaborador no encontrado: {rut}")
    # ... más manejadores
    
except requests.exceptions.Timeout:
    logger.error("Timeout en consulta a API Buk")
    
except requests.exceptions.ConnectionError:
    logger.error("Error de conexión con API Buk")
```

---

## Troubleshooting

### "Token inválido"

```
Soluciones:
1. Verificar token en .env es correcto (sin espacios)
2. Token puede estar expirado (regenerar cada 90 días)
3. Copiar token directamente del portal (sin caracteres extra)
4. Verificar permisos incluyen "Datos Sensibles"
```

### "Colaborador no encontrado"

```
Soluciones:
1. Verificar RUT en formato correcto: XX.XXX.XXX-X
2. RUT puede no existir en esta instancia de Buk
3. Colaborador puede estar inactivo (revisar filtro "status")
4. Permisos del token solo ven empleados activos
```

### "Timeout"

```
Soluciones:
1. Revisar conexión a internet
2. Aumentar timeout en cliente (por defecto 10s)
3. Buk API puede estar lento - reintentar
4. Usar VPN si es necesario
```

### "Too Many Requests (429)"

```
Soluciones:
1. Reducir velocidad de consultas
2. Implementar caché local de empleados
3. Usar paginación más eficiente
4. No hacer búsquedas en loop sin control
```

---

## Actualización de la Integración

Si Buk cambia su API:

1. **Verificar changelog** en Portal Buk
2. **Actualizar mapeo de campos** en `buk_client._parse_employee()`
3. **Validar que datos requeridos sigan existiendo**
4. **Ejecutar `test_example.py`** para validar
5. **Revisar logs** en `app.log` para errores

---

## Recursos Externos

- **Portal Buk**: https://portal.buk.cl
- **Documentación API Buk**: https://buk.cl/docs/api (requiere login)
- **Estado API**: https://status.buk.cl

---

**Última actualización**: Agosto 2026
**Versión API**: v1 (chile)
