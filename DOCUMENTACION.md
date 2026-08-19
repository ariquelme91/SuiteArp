# Suite ARP IA — Documentación técnica

Sistema de compensaciones de Dercorp. Calcula liquidaciones chilenas, analiza
aumentos de renta históricos y genera propuestas salariales, tomando los datos
de empleados desde la API de Buk.

- **Producción:** https://suitearia.streamlit.app
- **Repositorio:** https://github.com/ariquelme91/SuiteArp
- **Stack:** Python 3.11+ · Streamlit · SQLite · API Buk

> Los documentos `README.md`, `ARCHITECTURE.md`, `QUICKSTART.md` y demás son
> anteriores al sistema de autenticación (agosto 2026) y contienen referencias
> desactualizadas. **Este archivo es la referencia vigente.**

---

## 1. Arquitectura

```
                    ┌──────────────────┐
                    │   API de Buk     │  empleados, sueldos, cargos
                    └────────┬─────────┘
                             │ HTTPS (token)
                    ┌────────▼─────────┐
                    │  BukClient       │  src/buk_client.py
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐ ┌─────▼──────┐ ┌────▼─────────┐
       │ DataLoader  │ │PayrollEngine│ │  Simulator   │
       │ (ETL a BD)  │ │(liquidación)│ │ (propuestas) │
       └──────┬──────┘ └─────────────┘ └──────────────┘
              │
       ┌──────▼────────────┐
       │  analysis.db      │  SQLite: 12 tablas
       │  (AnalysisDBManager)│
       └───────────────────┘
              │
       ┌──────▼──────────────────────────────────┐
       │            app.py (Streamlit)           │
       │  login → rol → pestañas según permisos  │
       └─────────────────────────────────────────┘
```

**Decisión clave:** la app no consulta Buk en cada pantalla. `DataLoader` hace
una carga masiva bajo demanda (botón *Cargar Empleados* en ANÁLISIS) y todo lo
demás lee de SQLite. Por eso la app responde rápido y funciona aunque Buk esté
lento, a costa de que los datos sean del último refresco.

---

## 2. Autenticación y roles

### Dos orígenes de usuarios

| Entorno | Origen | Escritura |
|---|---|---|
| **Producción** (Streamlit Cloud) | `st.secrets["usuarios"]` | Solo lectura → se edita en el panel de Secrets |
| **Local** (desarrollo) | `src/analysis/data/auth.db` | Completa desde la UI |

`AuthManager` detecta el modo solo: si existe la sección `[usuarios]` en los
Secrets la usa; si no, cae a SQLite. El motivo es que **el disco de Streamlit
Cloud es efímero** — se borra en cada redeploy, así que un usuario creado en
runtime se perdía. Los Secrets sobreviven.

### Formato en los Secrets

```toml
BUK_API_TOKEN = "..."          # las claves sueltas van ANTES de la sección
BUK_SUBDOMAIN = "dercorp"

[usuarios]
Ariquelme = { password_hash = "pbkdf2$260000$<sal>$<hash>", rol = "admin" }
Pcuadra   = { password_hash = "pbkdf2$260000$<sal>$<hash>", rol = "user" }
```

⚠️ **No agregar claves nuevas debajo de `[usuarios]`** — quedarían dentro de esa
sección y romperían la lectura.

### Contraseñas

PBKDF2-HMAC-SHA256, sal aleatoria de 16 bytes, 260.000 iteraciones. El hash
completo mide **111 caracteres**; si queda cortado al copiarlo, la pantalla de
login lo detecta y muestra un error de configuración explícito en vez de un
genérico "contraseña inválida".

La verificación acepta también hashes SHA256 antiguos, así que bases locales
previas siguen funcionando.

### Agregar o cambiar un usuario en producción

1. Entrar como admin → **GESTIÓN DE USUARIOS → Agregar / Cambiar Clave**
2. Completar nombre, clave y rol → *Generar línea*
3. Copiar la línea completa en **Manage app → Settings → Secrets**, dentro de `[usuarios]`
4. Guardar — Streamlit reinicia sola

Para cambiar una clave, se reemplaza la línea existente de esa persona.

### Permisos por rol

| Pestaña | USER | ADMIN |
|---|:--:|:--:|
| 🧮 CALCULADORA | ✅ | ✅ |
| 📊 ANÁLISIS | ✅ | ✅ |
| 📝 PROPUESTAS | ✅ | ✅ |
| 💰 COMPENSACIONES | ✅ | ✅ |
| ⚙️ CONFIGURACIÓN | ❌ | ✅ |
| 👥 GESTIÓN DE USUARIOS | ❌ | ✅ |

El control es de servidor: para un USER las pestañas restringidas **no se
crean** (`app.py`, función `main()`), no se ocultan con CSS.

---

## 3. Estructura del código

### Aplicación web

| Archivo | Qué hace |
|---|---|
| `app.py` | Punto de entrada. Login, roles, y las 6 pestañas |
| `src/auth_manager.py` | Autenticación, hashing, lectura de Secrets |
| `src/login_page.py` | Pantalla de login |
| `src/user_management.py` | Pantalla de gestión de usuarios (2 modos) |

### Núcleo de negocio

| Archivo | Qué hace |
|---|---|
| `src/buk_client.py` | Cliente HTTP de Buk: empleados, historial salarial y de cargos |
| `src/payroll_engine.py` | Liquidación chilena: AFP, salud, AFC, impuesto único, gratificación |
| `src/simulator.py` | Compara escenarios de propuesta |
| `src/compensation_comparator.py` | Compensación anual actual vs propuesta |

### Análisis (`src/analysis/`)

| Archivo | Qué hace |
|---|---|
| `db_manager.py` | Acceso a `analysis.db` (34 métodos públicos) |
| `data_loader.py` | ETL desde Buk hacia SQLite |
| `salary_analyzer.py` | Historial de sueldos y cambios de cargo |
| `metrics_calculator.py` | Métricas del dashboard |
| `compensation_calculator.py` | Cálculo de compensaciones por nivel HAY |
| `internal_competitiveness.py` | Competitividad interna por nivel |
| `streamlit_ui.py` | Pestaña ANÁLISIS |
| `compensaciones_ui.py` | Pestaña COMPENSACIONES |
| `proposal_simulator_ui.py` | Simulador de propuestas |

### Exportadores

`src/exporter.py` y `src/analysis/excel_exporter.py` (Excel);
`src/pdf_exporter.py`, `src/pdf_exporter_calc.py`,
`src/analysis/pdf_compensation_exporter.py`,
`src/analysis/proposal_pdf_exporter.py` (PDF).

### CLI

`main.py` + `src/ui.py` — interfaz de terminal con Rich e Inquirer,
independiente de la app web.

### Scripts sueltos de la raíz

`debug_*.py`, `explorar_*.py`, `extraer_*.py`, `exportar_*.py`, `cargar_*.py`
son utilidades puntuales de exploración de la API. **No son parte de la app** y
pueden borrarse sin afectarla.

---

## 4. Modelo de datos

`data/analysis.db` (SQLite, ~300 KB):

| Tabla | Filas | Contenido |
|---|--:|---|
| `employee_analysis` | 244 | Tabla central: empleado, sueldos, aumentos, nivel HAY |
| `compensation_levels` | 16 | Bandas de mercado por nivel HAY |
| `compensation_averages` | 12 | Promedios calculados por nivel |
| `ipc_history` | 10 | IPC mensual |
| `employee_manual_values` | 2 | Nivel HAY y target cargados a mano |
| `uf_history` | 1 | Valor UF |
| `company_cache`, `supervisor_cache`, `area_cache` | — | Caché de nombres desde Buk |
| `compensation_proposals` | 0 | Propuestas guardadas |
| `salary_periods` | 0 | Períodos salariales |
| `export_logs` | 0 | Bitácora de exportaciones |

`src/analysis/data/auth.db` — solo la tabla `usuarios`, y solo se usa en local.

### Parámetros previsionales

`config/parameters.json` — valores que cambian con la normativa y se editan
desde la pestaña CONFIGURACIÓN:

```
periodo, uf_value, utm_value, imm_value
tope_afp_uf, tope_afc_uf, afp_rates (por AFP), salud_percent
afc_trabajador_*, afc_empleador_*, sis_percent, tasa_mutual_base
gratificacion_max_percent, tabla_impuesto_unico
```

> Estos valores **no se actualizan solos**. Hay que revisarlos cuando cambia la
> UF, la UTM o el ingreso mínimo.

---

## 5. Variables de entorno

| Variable | Para qué | Dónde |
|---|---|---|
| `BUK_API_TOKEN` | Token de la API de Buk | `.env` (local) / Secrets (nube) |
| `BUK_SUBDOMAIN` | Subdominio de la empresa (`dercorp`) | `.env` (local) / Secrets (nube) |

⚠️ Documentos antiguos del repo mencionan `BUK_AUTH_TOKEN`. **El nombre correcto
es `BUK_API_TOKEN`** — es el que lee `app.py`.

El token se genera en Portal Buk → Configuración → API → Personal Access Tokens.

---

## 6. Levantar en local

```bash
git clone https://github.com/ariquelme91/SuiteArp.git
cd SuiteArp
pip install -r requirements.txt
```

Crear `.env`:

```
BUK_API_TOKEN=tu_token
BUK_SUBDOMAIN=dercorp
```

```bash
streamlit run app.py
```

Sin Secrets configurados arranca en modo local y crea `auth.db` con los usuarios
por defecto.

---

## 7. Despliegue

Streamlit Cloud está conectado a la rama `main`: **cada push redespliega solo**
(1–2 minutos). No hay pipeline ni build.

Consecuencia a tener presente: **el disco se borra en cada redeploy.** Todo lo
que deba persistir va en los Secrets o en la BD versionada en git.

---

## 8. Respaldos

```bash
python backup.py                      # datos y configuración
python backup.py --incluir-secretos   # además credenciales
```

Genera `backups/suitearp_backup_<fecha>.zip` con `MANIFIESTO.json` (sha256 y
conteo de filas por tabla) e instrucciones de restauración. Las BD se copian con
la API de backup de SQLite, así que el respaldo es consistente aunque la app
esté corriendo.

Ver [MIGRACION.md](MIGRACION.md) para el procedimiento completo.

---

## 9. Deudas técnicas conocidas

Ninguna impide operar, pero conviene tenerlas a la vista:

1. **`app.py` tiene 2.650 líneas** con toda la UI. Partirlo por pestaña
   facilitaría el mantenimiento.
2. **`calculate_compensation_metrics` está duplicada** en `app.py` (líneas 160 y
   1026). La segunda anula a la primera — hay que verificar cuál es la vigente
   antes de tocarla.
3. **Tabla de ANÁLISIS construida fila por fila.** Cada empleado genera ~24
   elementos de Streamlit; por eso está paginada a 25 filas. Sin la paginación,
   244 empleados saturaban el render y dejaban en blanco las pestañas
   siguientes. Un `st.dataframe` sería más liviano, pero se pierden los botones
   por fila.
4. **`use_container_width` está deprecado** en Streamlit y deja de funcionar
   después del 31-12-2025. Hay que migrarlo a `width='stretch'`.
5. **Documentos antiguos desactualizados** (`ARCHITECTURE.md`, `README.md`,
   etc.): son previos a la autenticación y nombran mal la variable del token.
6. **Scripts sueltos en la raíz** — más de 20 utilidades de exploración
   mezcladas con el código de la app.
