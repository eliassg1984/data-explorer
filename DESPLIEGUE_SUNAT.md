# Despliegue de los procesos de SUNAT en el servidor

Qué instalar y programar en la **CPU del SQL Server** (la que no se apaga y
ya corre el extractor a parquet) para que la webapp tenga los datos de
SUNAT sin depender de ninguna máquina personal.

Son **tres procesos**. Los tres suben a R2; ninguno guarda nada
permanente en el disco del servidor.

| Proceso | Cuándo | Dura | Navegador |
|---|---|---|---|
| `sunat_registro_sync.py` | 1 vez al día | ~4 min | No |
| `sunat_originales_sync.py` | 1 vez al día | tope configurable (2 h) | Sí |
| `atender_solicitudes_sunat.py` | cada minuto | ~1 seg si no hay pedidos | Sólo si hay pedidos |

---

## 1. Requisitos previos

- **Python 3.9+** — ya está, porque corre el extractor actual.
- **Git** — sólo si se clona el repo (ver alternativa abajo).
- **~250 MB de disco**: repo 7 MB + Playwright 40 MB + Chromium 200 MB.
- **Salida a internet** hacia `*.sunat.gob.pe` y `*.r2.cloudflarestorage.com`.

## 2. Traer el código

```bash
git clone https://github.com/eliassg1984/data-explorer.git
cd data-explorer
```

Los scripts importan `sunat.py` y `data.py`, por eso hace falta el repo
entero y no los archivos sueltos.

> **Alternativa sin git:** copiar la carpeta por red. Funciona, pero hay
> que acordarse de re-copiarla en cada cambio — si el servidor se queda
> con una copia vieja de `sunat.py`, la webapp y el proceso nocturno
> pueden decir cosas distintas **sin ningún error que lo delate**.
> Con git, actualizar es `git pull`.

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
playwright install chromium
```

`requirements-dev.txt` y `playwright install` son sólo para los dos
procesos que usan navegador. Si por ahora se despliega únicamente el
registro (proceso 1), alcanza con `requirements.txt`.

## 4. Credenciales

Crear `.streamlit/secrets.toml` dentro de la carpeta del repo:

```toml
# SUNAT — Clave SOL de la empresa
SUNAT_RUC = "20..."
SUNAT_USUARIO_SOL = "..."
SUNAT_CLAVE_SOL = "..."
SUNAT_CLIENT_ID = "..."
SUNAT_CLIENT_SECRET = "..."

# Cloudflare R2 — las mismas que ya usa el extractor actual
R2_ACCOUNT_ID = "..."
R2_ACCESS_KEY = "..."
R2_SECRET_KEY = "..."
R2_BUCKET = "..."
```

**Este archivo NO va al repo** (está en `.gitignore`) y queda en texto
plano en el disco. Contiene la Clave SOL, que da acceso completo a la
cuenta tributaria: se puede declarar, rectificar y ver todo el historial.
Si al servidor entran varias personas, conviene **restringir la carpeta
por permisos de Windows** al usuario que corre las tareas.

Comprobar que quedó bien, antes de programar nada:

```bash
python herramientas/sunat_registro_sync.py --dry-run
```

Construye todo y reporta, sin subir nada a R2.

## 5. Programar las tareas

En el Programador de tareas de Windows, **con el usuario que tenga acceso
a la carpeta** y con "Iniciar en" apuntando a la carpeta del repo.

### Tarea 1 — Registro del SIRE a parquet

Diaria, **encadenada después del extractor de SQL Server** (para no
competir por red). Si el extractor corre 03:00, ésta 03:30.

```bash
python herramientas/sunat_registro_sync.py
```

Sale con código **2** si algún período falló y quedó fuera del parquet —
sirve para distinguir "terminó bien" de "terminó incompleto".

### Tarea 2 — Originales PDF/XML (backfill nocturno)

Diaria, después de la tarea 1.

```bash
python herramientas/sunat_originales_sync.py --minutos 120
```

Va de lo más nuevo hacia atrás y corta sola a las 2 horas. Con ~9.800
documentos pendientes dentro de la ventana de 24 meses que sirve SUNAT,
tarda ~41 noches en cubrirlos. Para ir más rápido al principio, subir a
`--minutos 240` unas semanas.

### Tarea 3 — Atender pedidos de la webapp

Cada minuto. Una pasada sin pedidos sale en ~1 segundo y **no abre el
navegador**, así que es barata.

```bash
python herramientas/atender_solicitudes_sunat.py
```

> Si se prefiere un proceso continuo —como el poller de solicitudes que ya
> corre ahí— usar `--vigilar` en vez de programarlo. Hay que asegurarse de
> que arranque solo tras un reinicio.

## 6. Verificar que funciona

Después de la primera corrida:

- **El parquet:** que `sunat_compras.parquet` exista en R2 y su fecha sea
  de hoy.
- **En la webapp:** abrir Compras → Documentos SUNAT. La tira de KPIs
  muestra "hoy" al final. Si dice "hace N días" en ámbar, el proceso dejó
  de correr.
- **Los originales:** abrir un documento reciente; deben aparecer los
  botones "📄 PDF original" y "🧾 XML".
- **Los pedidos:** abrir un documento viejo, clickear "⬇ Traer el original
  de SUNAT", esperar un minuto y volver a entrar.

## 7. Qué mirar cada tanto

Estos procesos hablan con el portal de SUNAT navegándolo como lo haría una
persona. **No es un contrato público**: el día que SUNAT cambie un
selector, la tarea 2 y la 3 van a fallar — y van a fallar **en silencio**,
salvo que alguien lea el log.

Conviene guardar la salida a un archivo y revisarla de vez en cuando:

```bash
python herramientas/sunat_originales_sync.py --minutos 120 >> log_sunat.txt 2>&1
```

Para diagnosticar cuando falle: correr con `--ver` (abre la ventana del
navegador y se ve dónde se traba). Detalle de los tres arreglos que ya
costó este flujo, en `arquitectura.md` regla #142.

La tarea 1 no tiene ese riesgo: usa la API REST del SIRE, no el portal.
