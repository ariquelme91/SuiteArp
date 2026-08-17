# ⚡ Inicio Rápido

## 1️⃣ Instalación (5 minutos)

```bash
# Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Instalar dependencias
pip install -r requirements.txt
```

## 2️⃣ Configuración (2 minutos)

Crear archivo `.env` en la raíz del proyecto:

```env
BUK_AUTH_TOKEN=Pegar_tu_token_aqui
BUK_SUBDOMAIN=tu_subdominio_buk
DEBUG=False
APP_MODE=cli
```

**¿Cómo obtener credenciales?**
- Ir a Portal Buk
- Configuración → API → Personal Access Tokens
- Copiar Token y Subdominio de su empresa

## 3️⃣ Ejecutar (1 minuto)

```bash
python main.py
```

¡Listo! La interfaz interactiva te guiará paso a paso.

## 🎯 Primera Propuesta

1. **Opción 1: Buscar Colaborador por RUT**
   - Ingrese RUT (ej: `12.345.678-9`)

2. **Completar Datos Propuesta**
   - ¿Cambios organizacionales? (empresa, cargo, jefe)
   - Nuevos haberes (colación, movilización)
   - Nuevo sueldo base

3. **Ver Comparativa**
   - Tabla Actual vs Propuesta automáticamente

4. **Exportar a Excel**
   - Generar reporte ejecutivo

## 📌 Notas Importantes

✅ **Parámetros Mensuales**: Editar `config/parameters.json` cada mes
- UF Value
- UTM Value  
- Tasas de AFP, Salud, Impuesto

✅ **Primer Uso**: Validar que conexión a Buk funcione
- La app automáticamente prueba la conexión al iniciar

✅ **Seguridad**: Nunca compartir credenciales en `.env`
- Archivo `.gitignore` ya está configurado

## 🆘 Problemas Comunes

| Problema | Solución |
|----------|----------|
| `401 Unauthorized` | Token inválido o expirado. Regenerar en Portal Buk |
| `Colaborador no encontrado` | Verificar RUT formato `XX.XXX.XXX-X` |
| `Cálculos no coinciden` | Actualizar UF/UTM en `config/parameters.json` |

## 📚 Documentación Completa

Ver `README.md` para guía detallada.

---

**¿Necesita ayuda?** Revisar logs en `app.log`
