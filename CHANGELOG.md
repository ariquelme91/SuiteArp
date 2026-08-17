# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [1.0.0] - 2026-08-14

### ✅ Agregado

- **Integración API Buk Chile**
  - Búsqueda de colaboradores por RUT
  - Listado con paginación
  - Autenticación y manejo de errores
  - Validación de formato RUT chileno

- **Motor de Cálculo de Nómina Chilena**
  - Cálculo de haberes (sueldo base + gratificación legal Art. 50)
  - Descuentos: AFP (10% + comisión), Salud (7%), AFC, IUSC
  - Aportes empleador: SIS, AFC Empleador, Mutual
  - Topes previsionales (84.3 UF, 126.6 UF)
  - Tabla de impuesto único con tramos SII
  - Cálculo inverso: Ingresar líquido objetivo → calcular base requerida

- **Simulador Comparativo**
  - Comparación Actual vs Propuesta
  - Cálculo de variaciones ($ y %)
  - Análisis de impacto para empleado y empresa
  - Soporte para cambios organizacionales (empresa, cargo, jefe)

- **Interfaz Interactiva**
  - CLI con Rich para visualización mejorada
  - Menú interactivo con Inquirer
  - Búsqueda amigable de colaboradores
  - Flujo paso a paso para crear propuestas
  - Visualización de comparativas en tabla ejecutiva

- **Exportación a Excel**
  - Generación de reportes .xlsx formateados
  - Estilos profesionales con colores temáticos
  - Tabla de comparación completa
  - Resumen de impacto económico
  - Sección de observaciones legales
  - Archivos guardados con timestamp para trazabilidad

- **Configuración Parametrizable**
  - UF, UTM, IMM configurables en JSON
  - Topes previsionales editables
  - Tasas de descuentos y aportes actualizables
  - Tabla de impuesto único configurable

- **Documentación Completa**
  - README.md con guía de instalación y uso
  - QUICKSTART.md para inicio rápido
  - ARCHITECTURE.md con diseño técnico detallado
  - BUK_API_REFERENCE.md con referencia de API
  - Comentarios en código con Type Hints

- **Validación y Testing**
  - Script test_example.py con 4 pruebas de validación
  - Manejo robusto de excepciones
  - Logs detallados de operaciones
  - Validación de parámetros mensuales

### 🎯 Características Principales

- ✓ Modular y extensible
- ✓ Tipado con Type Hints
- ✓ Manejo prolijo de errores HTTP
- ✓ CLI interactivo y amigable
- ✓ Reportes ejecutivos en Excel
- ✓ Cálculos completos normativa chilena
- ✓ Seguridad (variables sensibles en .env)

### 📝 Normativa Implementada

- Artículo 50 Código del Trabajo - Gratificación Legal
- Ley 19.728 - Sistema AFP
- Decreto Ley 3.500 - Sistema de Pensiones
- Ley 18.418 - Seguro de Cesantía (AFC)
- Código Tributario - Impuesto Único Segunda Categoría
- Ley 18.834 - Mutual de Seguridad

---

## [Roadmap] - Versiones Futuras

### Planeado v1.1

- [ ] Interfaz de configuración de parámetros en UI
- [ ] Actualización automática de UF/UTM desde API Mindicador
- [ ] Almacenamiento de propuestas en base de datos local
- [ ] Historial de propuestas por colaborador
- [ ] Comparación de múltiples propuestas

### Planeado v1.2

- [ ] Importación de CSV para propuestas en lote
- [ ] Generación de múltiples reportes Excel en un batch
- [ ] Estadísticas agregadas de impacto de propuestas
- [ ] Gráficos de comparación (matplotlib/plotly)
- [ ] Filtrado avanzado de colaboradores

### Planeado v1.3

- [ ] Interfaz web con Streamlit
- [ ] Autenticación de usuarios
- [ ] Integración con RRHM Suite (si aplica)
- [ ] Notificaciones por email de propuestas
- [ ] Revisión y aprobación de propuestas en flujo

### Planeado v1.4

- [ ] Base de datos PostgreSQL/SQLite
- [ ] API REST para integración externa
- [ ] Reportes analíticos avanzados
- [ ] Auditoría y logging detallado
- [ ] Soporte multi-empresa

---

## Notas Importantes

### Seguridad

- **NUNCA** commitear `.env` con credenciales reales
- **NUNCA** loguear tokens de API
- **SIEMPRE** usar HTTPS para comunicación
- Variables sensibles se protegen automáticamente con `.gitignore`

### Mantenimiento Mensual

Cada mes, actualizar `config/parameters.json`:
- [ ] UF Value (consultar Mindicador.cl)
- [ ] UTM Value (consultar Tesorería Chile)
- [ ] Tasa SIS (revisar SII)
- [ ] Tasa Mutual (según póliza)
- [ ] Tabla Impuesto Único (SII)

### Validación de Cambios

Después de actualizar código:
```bash
python test_example.py  # Valida cálculos básicos
python main.py          # Prueba interfaz
```

---

## Estructura de Versiones

- **v1.0.0**: MVP funcional completo
- **v1.1.x**: Mejoras interfaz y parámetros dinámicos
- **v1.2.x**: Procesamiento en lote y analytics
- **v1.3.x**: Web UI y flujo de aprobación
- **v1.4.x**: Enterprise features (DB, API, auditoría)

---

**Última actualización**: 2026-08-14
**Mantenedor**: Equipo RRHH
