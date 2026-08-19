# Guía de migración y respaldo

Qué llevarse, en qué orden y qué cambia según a dónde se migre.
Referencia técnica completa en [DOCUMENTACION.md](DOCUMENTACION.md).

---

## 1. Qué compone el sistema

El proyecto son cuatro cosas, y solo la primera está en git:

| Pieza | Dónde vive | ¿En git? | Se recupera con |
|---|---|:--:|---|
| **Código** | GitHub | ✅ | `git clone` |
| **Datos** | `data/analysis.db` | ✅ | `git clone` o el respaldo |
| **Configuración** | `config/*.json` | ✅ | `git clone` o el respaldo |
| **Credenciales** | Secrets de Streamlit / `.env` | ❌ | **Solo respaldo manual** |

> El punto crítico es el cuarto: las credenciales **no están en ningún lado
> versionado**. Si se pierde el acceso a la cuenta de Streamlit Cloud, hay que
> regenerar el token de Buk y volver a crear los usuarios.

---

## 2. Antes de migrar: asegurar lo irrecuperable

```bash
python backup.py --incluir-secretos
```

Deja `backups/suitearp_backup_<fecha>.zip` con datos, configuración y
credenciales. **Ese ZIP contiene el token de Buk y los hashes de contraseñas** —
guardarlo en un gestor de contraseñas o unidad cifrada, nunca por correo ni chat.

Aparte, copiar a mano el contenido de los Secrets de producción:
**Manage app → Settings → Secrets** → copiar todo el bloque tal cual.

Verificar que el respaldo sirve antes de confiar en él:

```bash
python -c "import zipfile,json; z=zipfile.ZipFile('backups/<archivo>.zip'); print(json.loads(z.read('MANIFIESTO.json'))['archivos'])"
```

El `MANIFIESTO.json` trae el sha256 y el conteo de filas por tabla de cada BD.

---

## 3. Escenarios

### A. Otra cuenta de Streamlit Cloud

El más simple: **no se toca una línea de código.**

1. Transferir o forkear el repo en GitHub
2. En la cuenta nueva: *New app* → apuntar a `app.py` de la rama `main`
3. Cargar los Secrets (token de Buk + sección `[usuarios]`)
4. Verificar: entrar con un usuario admin y otro user; confirmar que el admin ve
   6 pestañas y el user 4

Downtime: minutos. La URL cambia salvo que se configure un dominio propio.

---

### B. Servidor propio (VPS, on-premise)

Streamlit corre como un proceso normal.

```bash
git clone https://github.com/ariquelme91/SuiteArp.git
cd SuiteArp
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Restaurar el respaldo (descomprimir el ZIP sobre la raíz respetando rutas) y
crear `.env`:

```
BUK_API_TOKEN=...
BUK_SUBDOMAIN=dercorp
```

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

**Lo que cambia respecto de la nube:**

- El disco **deja de ser efímero**. Ya no hace falta el modo Secrets: si no se
  define la sección `[usuarios]`, `AuthManager` usa `auth.db` y la gestión de
  usuarios vuelve a funcionar completa desde la app (crear, cambiar rol,
  desactivar), sin copiar líneas a mano.
- Hay que resolver por fuera: HTTPS (nginx o Caddy como proxy inverso),
  arranque automático (systemd) y respaldo periódico de `data/`.

⚠️ **Streamlit no trae HTTPS.** Sin proxy inverso con TLS, las contraseñas
viajan en texto plano por la red.

---

### C. Contenedor / Docker

No hay `Dockerfile`. El repo trae `.devcontainer/devcontainer.json`
(Python 3.11) que sirve de base:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Montar `data/` como volumen para que la BD sobreviva al recrear el contenedor, y
pasar las credenciales por variables de entorno o secretos del orquestador.

---

### D. Cambiar SQLite por Postgres

Solo vale la pena si se necesita **escritura concurrente de varios usuarios**.
Hoy la app es de lectura casi pura: la carga masiva la dispara una persona a la
vez. SQLite aguanta bien ese uso.

El trabajo se concentra en `src/analysis/db_manager.py` (34 métodos con SQL
directo). Los tipos de SQLite son laxos y los de Postgres no, así que hay que
revisar fechas y numéricos uno por uno. No es un cambio de una tarde.

---

## 4. Verificación post-migración

Recorrer esto antes de dar por buena la migración:

- [ ] **Login** — usuario válido entra; clave incorrecta muestra error
- [ ] **Roles** — admin ve 6 pestañas; user ve 4 (sin CONFIGURACIÓN ni GESTIÓN)
- [ ] **Logout** — vuelve al login y limpia la sesión
- [ ] **CALCULADORA** — calcular una liquidación de prueba
- [ ] **ANÁLISIS** — carga la tabla; el conteo de empleados coincide con el
      `MANIFIESTO.json` del respaldo
- [ ] **Paginación** — la tabla de ANÁLISIS muestra el selector de página
- [ ] **PROPUESTAS y COMPENSACIONES** — abren con contenido (si aparecen en
      blanco, revisar el volumen que renderiza ANÁLISIS)
- [ ] **CONFIGURACIÓN** — los parámetros previsionales están cargados
- [ ] **Conexión a Buk** — buscar un empleado por RUT trae datos frescos
- [ ] **Exportar** — generar un Excel y un PDF

---

## 5. Dependencias externas

| Dependencia | Riesgo si falla | Plan B |
|---|---|---|
| **API de Buk** | No se refrescan datos ni se buscan empleados | La app sigue operando con lo último cargado en `analysis.db` |
| **Streamlit Cloud** | La app queda fuera de línea | Levantarla en local o en un VPS con el respaldo (escenario B) |
| **GitHub** | Se pierde el historial | El respaldo tiene datos y configuración, pero **no el código** — conviene un remoto espejo |

---

## 6. Rutina de respaldo sugerida

| Cuándo | Qué |
|---|---|
| Antes de cada cambio grande | `python backup.py` |
| Mensual | `python backup.py --incluir-secretos` a unidad cifrada |
| Al cambiar credenciales | Copiar los Secrets al gestor de contraseñas |

Los ZIP viven en `backups/`. Conviene excluir esa carpeta de git —
especialmente si se corre con `--incluir-secretos`.
