# 📋 Mejores Prácticas y Recomendaciones

Guía para usar la aplicación de Propuestas de Renta de forma segura, eficiente y correcta.

## 🔐 Seguridad

### Credenciales y Tokens

✅ **HACER:**
```
✓ Guardar .env en carpeta segura, NO compartir
✓ Regenerar tokens cada 90 días
✓ Usar token específico solo para esta app
✓ Revisar permisos ("Datos Sensibles" requerido)
✓ Cambiar credenciales si empleado se va del equipo
```

❌ **NO HACER:**
```
✗ Commitear .env a Git/GitHub
✗ Compartir token por email o Slack
✗ Usar mismo token en múltiples apps
✗ Loguear o imprimir credenciales
✗ Guardar token en documentos Word/Excel
```

### Archivos Generados

```
✓ Guardar reportes Excel en carpeta RRHH encriptada
✓ Usar contraseña al compartir archivos sensibles
✓ Eliminar reportes temporales después de uso
✓ Auditar acceso a carpeta de propuestas
✓ Tener backup de archivos importantes
```

---

## 📊 Datos y Parámetros

### Actualización Mensual de Parámetros

**Cada mes, ANTES de crear propuestas**, validar:

```json
{
  "periodo": "2026-09",              // Actualizar mes
  "uf_value": 38_XXX,                // Consultar UF actual
  "utm_value": 67_XXX,               // Consultar UTM actual
  "imm_value": 500_XXX,              // Actualizar IMM
  "sis_percent": 1.49,               // Revisar en SII
  "tasa_mutual_base": 0.93           // Revisar en póliza
}
```

**Fuentes Oficiales:**
- 📍 UF/UTM: https://mindicador.cl
- 📍 IMM: https://www.tesoreria.cl
- 📍 SIS, Mutual: Portal Buk o SII

### Validación de Datos

Antes de exportar a Excel:

```
Checklist:
☐ RUT formato correcto (XX.XXX.XXX-X)
☐ Nombre del colaborador coincide con Buk
☐ Sueldo base es razonable
☐ Tipo contrato es correcto (indefinido/plazo)
☐ Colación y movilización tienen sentido
☐ Propuesta es más alta/igual que actual (o justificada)
☐ Fecha aplicación es futura
☐ Parámetros son del mes actual
```

---

## 💰 Cálculos y Validaciones

### Revisar Resultados

Después de crear propuesta, validar:

```
Sueldo Líquido:
  ✓ Debe ser positivo
  ✓ Debe ser menor que Total Haberes
  ✓ Debe ser mayor que IMM ($500k) en la mayoría de casos
  
Descuentos:
  ✓ AFP debe ser ~11.97% del imponible
  ✓ Salud debe ser 7% del imponible
  ✓ Impuesto debe aumentar con sueldo base
  ✓ AFC solo en contrato indefinido
  
Aportes Empleador:
  ✓ SIS + Mutual ~2.4% del imponible
  ✓ AFC según tipo contrato
  ✓ Total costo > Total haberes
```

### Discrepancias Comunes

| Síntoma | Causa Posible | Solución |
|---------|----------------|----------|
| Cálculos diferentes a nómina | UF/UTM desactualizadas | Actualizar parámetros |
| AFP muy alto | Comisión estimada 1.97% vs real | Validar con AFP elegida |
| Impuesto 0 | Sueldo muy bajo | Correcto si < 13.5 UTM |
| AFC muy bajo | Contrato plazo fijo | Correcto: 0% en plazo |
| Costo empresa muy alto | Mutual base elevada | Revisar póliza de empresa |

---

## 🎯 Proceso de Propuesta

### Paso 1: Preparación

```
1. Obtener aprobación de propuesta antes de hacer cálculos
2. Validar que Buk esté actualizado con datos del empleado
3. Tener claro:
   - Nuevo sueldo base (o líquido objetivo)
   - Fecha aplicación
   - Cambios organizacionales (si existen)
```

### Paso 2: Búsqueda de Colaborador

```
✓ Usar RUT con formato XX.XXX.XXX-X
✓ Si no se encuentra, verificar:
  - Colaborador existe en Buk
  - RUT es correcto
  - Colaborador está activo
✓ Si persiste, permitir ingreso manual de datos
```

### Paso 3: Revisión de Datos Actuales

```
Antes de continuar, verificar:
☐ Nombre correcto
☐ Cargo correcto
☐ Empresa/jefatura correcta
☐ Sueldo base coincide con nómina
☐ Tipo contrato correcto
☐ Fecha ingreso correcta
```

### Paso 4: Definición de Propuesta

```
Opciones:
A) Ingresar Sueldo Base directamente
B) Ingresar Líquido Objetivo y dejar que se calcule

Recomendación:
- Opción A: Si ya tiene aprobado el sueldo base
- Opción B: Si solo sabe cuánto "neto" debe recibir
```

### Paso 5: Validación de Cambios

```
Cambios no típicos (revisar):
☐ Sueldo baja mucho (¿demotivación?)
☐ Sueldo sube > 50% (¿aprobado?)
☐ Cambio de empresa (revisar beneficios)
☐ Cambio de jefatura (comunicar)
```

### Paso 6: Exportación a Excel

```
Antes de exportar:
☐ Tabla de comparación se ve correcta
☐ Impacto es realista
☐ Archivo no se sobrescribe con timestamp

Después de exportar:
☐ Validar que archivo se abrió en Excel
☐ Revisar que estilos/colores se aplicaron
☐ Guardar en carpeta final segura
☐ Mantener log de reportes generados
```

---

## 📈 Cálculo Inverso (Líquido Objetivo)

### Cuándo Usar

Usar cálculo inverso cuando:
- ✓ Solo tienes "Debe recibir $X mensual"
- ✓ Necesitas despejar automáticamente el sueldo base
- ✓ Quieres evitar iteraciones manuales

### Validación

Después de calcular base inversa:

```python
Resultado:
  Sueldo Base Calculado: $1,750,000
  
Validación automática:
  ✓ Sueldo Líquido Resultante ≈ Objetivo
  ✓ Error < 0.1% (aceptable)
  ✓ Si error > 0.1%, reintentar con iteraciones
```

### Ejemplo Uso

```
Objetivo: Empleado debe recibir $1,800,000 líquido

1. Seleccionar opción "Calcular Base para Líquido Objetivo"
2. Ingresar: 1,800,000
3. Sistema calcula: Sueldo Base = $2,118,500 aprox.
4. Validar: Con ese base, líquido es $1,799,999 ✓

Luego usar ese base para propuesta
```

---

## 🐛 Troubleshooting Cálculos

### "Mis cálculos no coinciden con Buk"

**Causas Posibles:**

1. **UF/UTM desactualizadas**
   - Solución: Actualizar `config/parameters.json`
   - Verificar en https://mindicador.cl

2. **Bonos o descuentos no capturados**
   - Solución: Revisar si hay items en Buk no capturados
   - Agregar manualmente en "Otros Haberes"

3. **AFP diferentes comisiones**
   - Solución: Validar % comisión real de AFP elegida
   - Puede variar de 1.19% a 2.40%
   - Ajustar en `payroll_engine.py` si es necesario

4. **Isapre vs Fonasa**
   - Si es Isapre: Puede haber % diferente a 7%
   - Solución: Ajustar `salud_percent` en parámetros

5. **Descuentos adicionales**
   - Créditos, embargos, o descuentos especiales
   - Solución: Ingresar en "Otros Descuentos"

### "Parámetros obsoletos"

Si reportes no coinciden:

```bash
# 1. Verificar fecha en parámetros
cat config/parameters.json | grep periodo

# 2. Si es mes anterior, actualizar:
# Editar config/parameters.json con valores vigentes

# 3. Ejecutar test para validar
python test_example.py

# 4. Si aún hay errores, revisar logs
tail -50 app.log
```

---

## 📞 Comunicación con Stakeholders

### Con Colaborador

```
"Su propuesta de renta es de $X sueldo base.
 Esto representa $X líquido mensual (después de AFP, impuestos, etc).
 Vigente desde [fecha].
 Cambios principales: [listar]"
```

### Con Gerencia/Finanzas

```
"Impacto de propuesta:
 - Costo empresa: +$X mensual = +$X anuales
 - Beneficio retención: Mantener talento clave
 - Justificación: Mercado, desempeño, antigüedad"
```

### Archivo Excel a Enviar

Siempre incluir:
- ✓ Tabla clara de actual vs propuesta
- ✓ Resumen de impacto monetario
- ✓ Observaciones legales
- ✓ Fecha de aplicación
- ✓ Datos de quién preparó

---

## 📋 Checklist Pre-Envío

Antes de entregar propuesta a firma:

```
Completitud:
☐ Datos del colaborador correctos y actualizados
☐ Todos los campos de haberes completados
☐ Tipo contrato correcto
☐ Fecha aplicación válida y coordinada

Precisión Técnica:
☐ Parámetros (UF/UTM) son del mes actual
☐ Cálculos validados con test_example.py
☐ Comparativa muestra cambios reales
☐ Impacto costo empresa incluye todos aportes

Presentación:
☐ Excel tiene estilos profesionales
☐ Tabla es legible y clara
☐ Colores resaltan información importante
☐ Observaciones legales incluidas

Seguridad:
☐ Archivo tiene nombre descriptivo y fecha
☐ Archivos guardados en carpeta segura
☐ Si se comparte, usar método seguro
☐ Original en carpeta RRHH, respaldo hacer

Aprobaciones:
☐ Revisado por Gerencia
☐ Revisado por Finanzas
☐ Revisado por Abogado/Legal (si aplica)
☐ Aprobado por HR Manager
```

---

## ⏰ Frecuencia de Uso Recomendada

### Cuando Crear Propuestas

- ✓ Nuevas incorporaciones
- ✓ Ascensos y cambios de posición
- ✓ Revisiones salariales anuales (typically July-Aug)
- ✓ Reconocimientos por desempeño
- ✓ Retenciones clave
- ✓ Cambios organizacionales
- ✓ Alineación con mercado

### Cuándo NO Crear

- ✗ Cambios menores sin justificación
- ✗ Propuestas duplicadas al mismo empleado
- ✗ Sin presupuesto aprobado

---

## 📚 Documentación Recomendada

Tener a mano:

1. **README.md** - Guía general
2. **QUICKSTART.md** - Para usuarios nuevos
3. **BUK_API_REFERENCE.md** - Si hay problemas Buk
4. **ARCHITECTURE.md** - Para entender el sistema
5. **config/parameters.json** - Verificar cada mes
6. **app.log** - Debug de errores

---

## 🎓 Training para Nuevos Usuarios

### Sesión 1 (30 min)
- [ ] Instalación y setup (.env)
- [ ] Ejecutar test_example.py
- [ ] Ver QUICKSTART.md

### Sesión 2 (1 hora)
- [ ] Crear primera propuesta con supervisión
- [ ] Validar cálculos vs nómina actual
- [ ] Exportar a Excel y revisar formato

### Sesión 3 (30 min)
- [ ] Actualizar parámetros mensuales
- [ ] Troubleshooting común
- [ ] Preguntas y casos especiales

### Sesión 4 (Optional, 1 hora)
- [ ] Leer ARCHITECTURE.md
- [ ] Revisar código fuente
- [ ] Posibles customizaciones

---

## 📈 Métricas de Éxito

Monitorear:

```
✓ Tiempo promedio por propuesta (meta: 5-10 min)
✓ % Propuestas sin errores (meta: 100%)
✓ Accuracy vs nómina (meta: ±100 pesos)
✓ Satisfacción usuarios (feedback)
✓ Problemas/issues reportados (meta: 0)
```

---

**Última actualización**: Agosto 2026
**Versión**: 1.0.0
