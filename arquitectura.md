# Arquitectura del proyecto — mapa y reglas

Webapp Streamlit (Community Cloud) que lee parquets desde Cloudflare R2 con
DuckDB y los muestra en tablas AgGrid con estética propia (paleta lavanda).

Este fichero existe para que cualquier persona **o IA** entienda el proyecto
en 2 minutos y no rompa nada al modificarlo. Si cambias la estructura,
actualiza este documento en el mismo commit.

> **Nota sobre el uso con IA:** los asistentes cargan `CLAUDE.md`
> automáticamente en cada sesión; este fichero **no**, solo lo leen si van a
> buscarlo. Por eso `CLAUDE.md` es un resumen corto que apunta aquí. Lo que
> deba conocerse *siempre* va en `CLAUDE.md`; el detalle completo vive aquí.
> Si agregas una regla nueva abajo y es de las que muerden seguido, deja una
> línea en `CLAUDE.md` que apunte a ella.

## Mapa de ficheros

| Fichero | Trabajo (uno solo) |
|---|---|
| `app.py` | Orquestador: navegación, filtros, fragmentos, llama a los renderizadores. |
| `data.py` | Carga de datos: DuckDB + httpfs leyendo parquets de R2 (secrets). Sistema de refresco bajo demanda vía R2. |
| `tablas/` | **Paquete de tablas AgGrid** (refactor 2026-08-01; antes un `tablas.py` de 2.028 líneas). `__init__.py` re-exporta la API pública. `_css.py` (CSS de grid y paneles), `_config.py` (estilos de celda/fila, sidebar, totales), `desktop.py` (`renderizar_aggrid_desktop`), `movil.py` (`renderizar_aggrid_movil`), `compras.py` (`renderizar_aggrid_compras` + `renderizar_tabla_compras`, esta última legacy y sin uso). |
| `graficos/` | **Paquete de dashboards de gráficos** (refactor Fase 2, 2026-07-25). `__init__.py` es solo el dispatcher: dict `_DASHBOARDS = {reporte: render_fn}` (no cadena de if/elif), más `renderizar_graficos_reporte` (entry point). `render_vista_pills` (pestañas Gráficos/Tabla sueltas en la franja) se ELIMINÓ 2026-08-04: ver regla #18. Cada dashboard vive en su archivo: `base.py` (infraestructura compartida: cards nativos, motor genérico, resolución de columnas, helpers de layout), `ajuste.py` (ojo: la **cascada NO es un gráfico Plotly** sino una tabla de filas — `st.columns` por familia + HTML en `st.markdown`, con una columna de barras flotantes que encadenan la cascada; ver reglas #8 y #10), `ventas.py`, `inventario.py` (v2), `salidas.py` (evolución con granularidad Día/Semana/Mes/Año + composición por subalmacén/tipo de descargo), `constructor.py` (Power BI, usado por Compras), `legacy.py` (Inventario v1, respaldo no re-exportado). **`compras/` es a su vez un paquete** (refactor 2026-08-01; antes un `compras.py` de 2.835 líneas): un drill por archivo — `_comun.py` (helpers, incluye `_periodo_serie` para granularidad temporal — reusar desde ahí, no duplicar), `proveedor.py`, `familia.py`, `cantidad.py`, `evolucion.py` — y `__init__.py` con la config del rail y `renderizar_graficos_compras`. Cuando un dashboard crezca así, partirlo del mismo modo. **Agregar un dashboard nuevo = crear `graficos/<nombre>.py` + 1 línea en `_DASHBOARDS`.** |
| `estilos/` | **Paquete del CSS global** (refactor 2026-08-01; antes un `estilos.py` de 1.700 líneas). `__init__.py` mantiene la API pública (`TAM_FUENTE`, `get_css`, `inject_css`) y concatena las secciones. Una sección por módulo, con prefijo numérico que marca el orden: `_00_base`, `_10_vista`, `_20_compras_rail`, `_30_filtros`, `_40_ajuste_franja`, `_50_fecha`, `_60_calendario`, `_70_chrome`, `_80_cards`, `_90_franja_inferior`, `_99_movil`. **El orden de `_SECCIONES` es parte del comportamiento**: hay `!important` en ambos lados de varios conflictos, así que gana la regla que va DESPUÉS — por eso `_99_movil` cierra. |
| `navegacion.py` | Rail lateral, topbar y CSS por sección (`_CSS_AJUSTE`). Botón de refresco aislado en su propio `@st.fragment`. |
| `inyecciones/` | **Paquete de JS/HTML inyectado** (refactor 2026-08-01; antes un `inyecciones.py` de 1.813 líneas). `_fragmentos.py` (CSS/JS compartido), `grid.py` (salud, altura, maximizar, panel de columnas), `paginacion.py`, `inspector.py` (herramienta de desarrollo), `varios.py` (overlay de errores, fullscreen, footer, calendario). Ninguna función depende de otra: las únicas dependencias internas apuntan a las constantes de `_fragmentos.py`. |
| `tema.py` | **Paleta de colores con nombre, definida UNA vez.** Todos los demás importan de aquí. |
| `inspector.py` | Herramienta de verificación de datos crudos: busca, filtra por fecha, radiografía de columnas, detección de columnas duplicadas. |
| `perf.py` | Diagnóstico de rendimiento por rerun (activado con `?debug=1`). Singleton `perf` con fases, fragments y BroadcastChannel hacia el navegador. |
| `utils.py` | Normalización de texto (`_norm`), búsqueda de columnas (`buscar_columna`, `buscar_columna_fecha`, `resolver_columnas`), traducciones de AgGrid (`LOCALE_ES`). |

> Los dos ficheros de abajo **no corren en Streamlit Cloud**: viven en una
> máquina Windows aparte (Programador de tareas) y se conectan a la webapp
> solo a través de R2. Ver sección "Pipeline de datos".

| Fichero (backend, fuera de Streamlit Cloud) | Trabajo (uno solo) |
|---|---|
| `Extraer a parquet.py` | Extractor diario: TODAS las consultas del Sheet → SQL Server → TODOS los parquets a R2. |
| `atender_solicitudes.py` | Atiende refrescos puntuales bajo demanda: SOLO la consulta/parquet pedido desde la webapp. |

## Pipeline de datos — dos modos de actualización

La webapp **nunca** escribe en SQL Server ni genera parquets: solo LEE
parquets ya generados desde R2 (`data.py::cargar`). La generación vive en
dos scripts aparte, que corren en una máquina Windows (fuera de este repo),
coordinados por un sistema de locks en R2 (carpeta `_locks/`):

| Script | Cuándo corre | Qué hace |
|---|---|---|
| `Extraer a parquet.py` | 1 vez al día (Programador de tareas, madrugada) | Lee TODAS las consultas activas del Google Sheet, las ejecuta contra SQL Server y sube TODOS los parquets a R2. |
| `atender_solicitudes.py` | Cada pocos minutos (Programador de tareas, en paralelo) | Vigila `_solicitudes_refresco/` en R2; si hay una señal, regenera y sube SOLO ese parquet puntual. |

**Requisito de acoplamiento:** `atender_solicitudes.py` debe vivir en la
MISMA carpeta que `Extraer a parquet.py` (su nombre exacto, con espacios,
va en `NOMBRE_ARCHIVO_EXTRACTOR`), porque lo carga dinámicamente vía
`importlib.util` — un nombre con espacios impide un `import` normal.

### Cómo se dispara un refresco puntual

1. El usuario pulsa el botón refrescar (rail, `navegacion.py::_fragment_boton_refresco`).
   El botón vive en su **propio `@st.fragment`** para que su clic no dispare
   un rerun completo de `app.py`.
2. `navegacion.py` llama a `data.py::solicitar_refresco(archivo, reporte)`:
   escribe un JSON en R2 `_solicitudes_refresco/{archivo}.json` con
   `{reporte, archivo, solicitado_en}`. **NO limpia el caché aquí** — el
   parquet en R2 todavía no cambió en este instante; limpiar aquí solo
   lograría re-descargar y re-cachear el dato viejo.
3. `app.py` monta `_vigilar_refresco` como fragment con `run_every=4` desde
   el inicio (incondicionalmente, para que esté listo antes del primer clic).
   Ese fragment llama `data.py::hay_dato_nuevo()` comparando `LastModified`
   del parquet en R2 contra la fecha capturada justo antes de pedir el refresco.
4. Cuando `hay_dato_nuevo()` devuelve `True`, el fragment limpia el caché
   con `cargar.clear(archivo)` y hace `st.rerun(scope="app")`.
5. Mientras espera (periodo de gracia de 8 s): sin aviso visible. Después:
   muestra `st.info` en el contenedor `aviso_refresco` (posicionado por CSS
   junto al rail). Pasados 120 s sin dato nuevo: cambia a `st.warning`.
6. `atender_solicitudes.py` recoge la señal en su próximo ciclo, ejecuta
   SOLO esa consulta, sube SOLO ese parquet, borra la señal y libera el lock.

### Locks (evitan que los dos procesos pisen el mismo parquet)

- Carpeta R2 `_locks/`, un JSON por archivo: `{proceso, inicio}`.
- TTL de 10 min (`LOCK_TTL_SEGUNDOS`): pasado ese tiempo el lock se
  considera abandonado (crash de algún proceso) y cualquiera puede tomarlo.
- Si `atender_solicitudes.py` no consigue el lock → **no borra la señal**,
  se reintenta sola en el siguiente ciclo (unos minutos después).
- Si el extractor diario no consigue el lock → **omite ese archivo hoy**,
  se recoge en la corrida de mañana.
- Las funciones (`lock_vigente`, `adquirir_lock`, `liberar_lock`) viven en
  `Extraer a parquet.py`; `atender_solicitudes.py` las reusa tal cual (vía
  el módulo cargado dinámicamente) para que ambos hablen el mismo protocolo.

### Resultado vacío (0 filas)

Si una consulta puntual devuelve 0 filas, `atender_solicitudes.py` no sube
nada (deja el parquet anterior intacto en R2) pero SÍ borra la señal: se
considera un resultado válido, no un error para reintentar por siempre.

## Configuración de reportes (data.py::REPORTES)

Cada entrada en el dict `REPORTES` admite estas claves (todas opcionales
salvo `icono`):

| Clave | Tipo | Efecto |
|---|---|---|
| `archivo` | str | Nombre del parquet en R2. Sin esta clave, el reporte es una herramienta (`tool`). |
| `icono` | str | Nombre Bootstrap del icono; `navegacion.py` lo traduce a Material Symbols. |
| `tool` | bool | Si `True`, `app.py` delega a `inspector.py` en vez de intentar cargar un parquet. |
| `columnas` | list | Columnas a mostrar (en orden). Si no existe, se muestran todas. |
| `filtros_cat` | list | Columnas categóricas que aparecen como multiselect en el popover de filtros. |
| `buscador` | str | Columna que alimenta el buscador de productos del popover. |
| `fecha` | str o None | Columna de fecha explícita. `None` = sin filtro de fecha. Ausente = auto-detectar. |
| `agrupar` | list | Columnas disponibles en el selector "Agrupar por" del popover. |
| `graficos` | list | Lista de dicts de configuración para `crear_grafico()` (tipo, x, y, color, título…). |
| `columnas_movil` | list | Columnas visibles en vista móvil. |
| `columnas_fijas_movil` | int | Número de columnas fijadas a la izquierda en vista móvil. |

## Reglas del proyecto (aprendidas de bugs reales)

1. **Colores desde la paleta central — DOS fuentes coordinadas.** Nunca pegar
   `#xxxxxx` suelto en el código. Hay dos "caras" de la MISMA paleta, según
   el mundo (Python o CSS):
   - **`tema.py`** (Python) — para colores usados desde código Python:
     `navegacion.py` (f-strings), `graficos.py` (Plotly), diccionarios
     `custom_css` de AgGrid. Se importa: `from tema import ACENTO, ...`.
   - **`:root` de `estilos/_00_base.py`** (CSS) — para el CSS global inyectado
     como string. Ese bloque define variables (`--accent`, `--border`...) y
     todos los demás módulos de `estilos/` las usan con `var(--...)`. Es la
     fuente única del CSS.
   Ambas tienen los MISMOS valores a propósito. No se pueden fusionar en una
   sola (Python y CSS son mundos distintos; el CSS de `estilos/` no es
   f-string y meter Python exigiría escapar todas las llaves `{}`).
   **Regla al cambiar un color:** actualizarlo en las DOS caras si aplica a
   ambas. Motivo del refactor: había 100+ colores repetidos a mano; cambiar
   la marca era imposible sin desentonar algo.

2. **Estilos de paneles AgGrid siempre ACOTADOS por panel.** Los paneles
   Columnas y Modo pivote comparten el componente interno
   (`agColumnsToolPanel`), así que un selector "desnudo" como
   `.ag-column-select-column` afecta a AMBOS. Prefijar siempre:
   - Columnas: `.ag-side-bar[data-active-panel='columns'] ...`
   - Pivote:   `.ag-side-bar[data-active-panel='pivotePanel'] ...`
   Motivo: un estilo sin prefijo rompió el panel Pivote al estilar Columnas.

3. **Nada de formateo `%` en plantillas JS/CSS de `components.html`.** El
   CSS/JS legítimo contiene `%` (p.ej. `height: 100%`) y choca con el
   operador `%` de Python (TypeError en producción). Insertar valores con
   una línea `config_js = f"var X = {valor};"` concatenada, dejando el
   bloque grande como literal puro.

4. **Altura del grid: fijo + inyección.** `AgGrid(height=600)` queda como
   red de seguridad; `inject_dynamic_grid_height()` la estira al viewport
   con UNA medición (sin listener de resize continuo, que provoca el bucle
   setFrameHeight→resize→re-medición y el error React #185). Para revertir:
   comentar la llamada en `tablas.py`.
   **Interacción documentada:** dentro del iframe se fija la cadena COMPLETA
   (`html, body {margin:0}` y `.ag-root-wrapper` a px fijo vía
   `<style id="dynh-css">`). Se usa px fijo —no `100%`— porque `100%`
   encadenado provoca reflow en hover de AgGrid y la tabla parpadea o colapsa.
   El px se actualiza en cada llamada a `aplicarAltura()`.
   Regla general: si dos `inject_*` comparten espacio o elemento, la
   interacción se documenta en ambas (comentario en el código + aquí).

5. **`_LAYOUT_BASE` de graficos.py no se puede desempacar con `**` cuando el
   `update_layout` define sus propias claves `xaxis` o `yaxis`.** Python lanza
   `TypeError: got multiple values for keyword argument 'xaxis'`. Solución:
   filtrar las claves conflictivas antes de desempacar:
   ```python
   _layout = {k: v for k, v in _LAYOUT_BASE.items() if k not in ("xaxis", "yaxis")}
   fig.update_layout(**_layout, xaxis=dict(...), yaxis=dict(...))
   ```

6. **CSS por key: acotar al widget, nunca colgar del contenedor.** En
   `estilos/` las reglas matchean por prefijo de key. Un selector
   descendiente como
   `div[class*="st-key-<contenedor>_"] [data-testid="stButtonGroup"]`
   captura **todo** widget de ese tipo dentro del contenedor, incluidos los
   que se agreguen meses después — y desde el `.py` no hay ninguna pista de
   que ese acoplamiento existe.
   Motivo (bug real, 2026-08-01): una regla escrita para unos "chips de tipo
   de gráfico" siguió viva después de que esos chips se eliminaran, y le
   impuso forma de globo al selector "Top 5/10/20" del drill de la cascada.
   Cambiar `st.pills` por `st.segmented_control` no cambió nada: ambos rinden
   el mismo DOM `stButtonGroup`, así que la regla los alcanzaba igual.
   **Regla:** el estilo de un widget puntual se acota a SU key
   (`.st-key-<key_del_widget>`). Solo cuelga del contenedor lo que de verdad
   deba aplicar a todos sus descendientes, presentes y futuros.
   Es la misma lección que la regla #2 (paneles AgGrid), en otro escenario:
   un selector sin acotar termina pisando algo que no era su objetivo.

7. **Antes de estilar o agregar un widget, `grep` `estilos/` por el prefijo
   de key del contenedor donde vive.** Es el paso que convierte la regla #6 en
   costumbre. Si un cambio de widget "no se ve", casi siempre hay una regla
   del contenedor ganándole.

8. **Nunca `align-items: center` en un `stHorizontalBlock` que hace de fila
   de tabla.** Con `center` las `stColumn` dejan de estirarse y colapsan a la
   altura del hijo más chico — en el bug real, 6px de columna con 30px de
   contenido adentro. Como el overflow queda `visible`, el texto se sigue
   viendo pero **las filas se pisan entre sí**, y en el DOM la altura muere
   varios niveles arriba del contenido (la cadena entera reporta 6px mientras
   `stMarkdownContainer` reporta 30px), así que el síntoma no apunta a la
   causa.
   **Regla:** el alto de la fila lo fija `min-height` en el
   `stHorizontalBlock`; el centrado vertical va DENTRO de cada celda
   (`stMarkdownContainer` con `display:flex; justify-content:center`), que es
   HTML propio y no pelea con el layout de Streamlit.
   Motivo (bug real, 2026-08-01): la cascada de Ajuste como tabla de filas.

9. **Un bloque que aparece/desaparece necesita un *instance id* en las keys
   de sus hijos.** Al pasar de cerrado a abierto, Streamlit reusa los nodos
   DOM; Plotly y AgGrid no re-miden el ancho del contenedor y salen vacíos o
   con columnas colapsadas. Se incrementa un contador en `session_state` en
   cada apertura y se anexa a la key de cada hijo para forzar remount limpio.
   Está en el drill de Proveedor de Compras (`compras/proveedor.py`) y en el
   de la cascada de Ajuste (`ajuste.py`).

10. **Los datos demo no traen las columnas de Ajuste** (`AJUSTE VALORIZADO`
    y compañía), así que la vista cae al explorador genérico y la cascada no
    se puede verificar levantando la app. Para tocarla, montar un harness
    con datos sintéticos que llame directo a `_graf_waterfall_ajuste` y
    levantarlo como segunda config en `.claude/launch.json`. Medir con JS
    (`getBoundingClientRect` + `scrollHeight`) encuentra los colapsos de
    layout que una captura de pantalla no delata.

11. **`go.Heatmap` NO es una traza seleccionable: `on_select` nunca recibe
    sus puntos.** El cableado se ve correcto (`on_select="rerun"`,
    `selection_mode="points"`, lectura de `selection.points`) y aun así el
    clic no hace nada — no hay error, simplemente la selección llega vacía
    siempre. Lo mismo vale para otras trazas no seleccionables.
    **Solución:** superponer un `go.Scatter` con un punto por celda y
    `marker.opacity = 0`, que sí es seleccionable. Va acompañado de:
    - `hoverinfo="skip"` en el heatmap y el `hovertemplate` rico en el
      scatter, para que el tooltip lo sirva una sola capa;
    - `hovermode="closest"` en el layout y un `marker.size` generoso
      (~28), que es lo que define el radio de captura del clic — chico deja
      zonas muertas entre celdas;
    - leer el valor del `pivot` con la familia/área clicadas, **no** del
      evento: los puntos de un scatter no traen `z`.
    Implementado en `_graf_heatmap_ajuste` (`ajuste.py`).

12. **El clic de Plotly no se puede simular desde JS.** Su hitbox no
    reacciona a `dispatchEvent(new MouseEvent('click'))`, así que un drill
    basado en `on_select` no se verifica desde el navegador con las
    herramientas de inspección. Lo que sí funciona: llamar a la función de
    render desde Python con `st.plotly_chart` monkeypatcheado para devolver
    una selección falsa (`{'points': [{'x': ..., 'y': ...}]}`) y capturar
    lo que se dibuja. Eso valida toda la lógica del drill; lo único que
    queda sin cubrir es que el evento real llegue, que es exactamente lo
    que la regla #11 explica cómo romper.

13. **Verificar el layout SIEMPRE al ancho real del usuario.** Un intento de
    calendario propio de dos meses (revertido, 2026-08-02) se veía perfecto
    midiendo a 1280px y llegaba roto al usuario, que trabaja con la ventana
    a media pantalla. Antes de dar por bueno un layout, `resize_window` al
    ancho chico *y* al grande. Lo que se aprendió de ese intento, por si
    alguien vuelve a construir una grilla de widgets:
    - **`st.columns` admite UN solo nivel de anidado.** No se puede hacer
      `columns(2)` y dentro `columns(7)`. Hay que aplanar a una sola fila
      con todas las columnas.
    - **Por debajo de ~640px de viewport Streamlit APILA todas las
      `st.columns`** (su propio breakpoint). Una grilla se convierte en una
      lista vertical salvo que se fuerce `flex-direction: row`.
    - **El `gap` entre columnas es 1rem aun con `gap="small"`.** Con 15
      columnas son ~224px que se comen el ancho útil.
    - **Apilar elementos dentro de cada columna desalinea las filas**:
      cualquier diferencia de alto se acumula. Una `st.columns` por fila.
    - **`:has()` baja a CUALQUIER profundidad**, así que
      `columna:has(.marcador)` también matchea la columna contenedora y
      desaparece todo. Hay que usar cadenas de hijo directo con la
      profundidad exacta, medida en el DOM.
    - **La detección móvil por User-Agent y los `@media` por ancho de
      ventana DIVERGEN** en una ventana angosta de escritorio: el UA dice
      "desktop" y el CSS aplica el tope móvil. El layout se decide por CSS,
      nunca por UA (ya estaba en `CLAUDE.md`; acá costó un rediseño entero).

14. **`st.date_input` dibuja UN solo mes y no hay forma de desdoblarlo:** es
    un componente React precompilado. Las librerías externas
    (`streamlit-date-picker` y similares) sí muestran dos meses, pero
    Streamlit las encierra en un iframe dimensionado al input (~398x60) y su
    desplegable (~576x330) queda recortado. Y con la ventana a media
    pantalla dos meses no entran de ninguna manera: necesitan ~600px. Si el
    requisito vuelve a aparecer, la pregunta previa es a qué ancho de
    ventana trabaja quien lo pide.

15. **`@st.cache_data` sobre una función que concatena constantes de
    submódulos NO se invalida cuando esas constantes cambian.** El hash mira
    los args (aquí ninguno) y el source de la función misma, no el contenido
    de los `_CSS_*` importados. Resultado en el preview: se edita
    `estilos/_20_compras_rail.py`, se guarda, el navegador rerender —
    y `get_css()` devuelve el string del proceso anterior. El CSS "nuevo"
    nunca se inyecta, así que la regla parece no aplicar cuando en realidad
    ni siquiera se sirvió. Por eso `get_css()` en `estilos/__init__.py` **no
    lleva caché**: el join de 11 strings es microsegundos y ganar recarga en
    caliente vale más. Si alguien ve el decorador y quiere "optimizar",
    releer esta regla antes.
    Motivo (bug real, 2026-08-03): un `margin-top` cambiado en
    `_20_compras_rail.py` no se veía y el diagnóstico apuntó al padre
    keyed / al inspector — cuando el problema era el cache sirviendo CSS
    viejo.

16. **Keys "de reporte" vs keys "de componente compartido": no confundir al
    scopear CSS con `:has()`.** Varias keys tienen nombres que sugieren un
    reporte (`compras_tabs_row`, `chips_ajuste_tabla`, `fila_ajuste_top`)
    pero en realidad son de componentes REUSADOS entre reportes:
    - `compras_tabs_row` es la key del rail COMPARTIDO — desde 2026-08-04
      lo usan los 8 reportes (antes solo Compras + Ajuste), ver el
      docstring en `graficos/base.py::_render_rail` y la regla #17.
    - `chips_ajuste_tabla` es el contenedor de chips-filtro y se usa en
      TODOS los reportes (Compras, Ajuste, Ventas, Inventario…).
    - `fila_ajuste_top` es la franja superior de todos los reportes.

    Consecuencia: un `:has(.st-key-compras_tabs_row) .st-key-chips_ajuste_tabla { transform: translateX(-50%) }`
    pensado como "solo Compras" también matchea Ajuste y desplaza los chips
    246px a la izquierda en el reporte equivocado (bug real 2026-08-03).

    **Regla:** para scopear una regla a un reporte específico, usar el
    marker `.st-key-app_reporte_<slug>` que `app.py` inyecta después de
    determinar el reporte activo (`compras`, `ajuste_de_inventario`,
    `ventas`, `inventario`, `requerimientos`). Ejemplo:
    ```css
    [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_compras)
        .st-key-chips_ajuste_tabla { ... }
    ```
    Cuando la regla SÍ es del componente compartido (p.ej. el rail en
    móvil), sí conviene mantener `:has(.st-key-compras_tabs_row)` porque
    describe "cuando el rail existe", no "cuando estamos en Compras" —
    documentar el intent en el comentario para el próximo lector.

17. **La franja transparente + fecha-pill-izquierda + chips-centrados-blancos
    es el DEFAULT para los 8 reportes desde 2026-08-04** (`estilos/_40_ajuste_franja.py`
    y `estilos/_50_fecha.py`), no una particularidad de Compras/Ajuste. Antes
    había dos bloques casi-duplicados scopeados con `:has(.st-key-app_reporte_compras)`
    y `:has(.st-key-app_reporte_ajuste_de_inventario)`; se colapsaron en uno
    solo (gated `@media (min-width: 901px)`, sin scope de reporte) porque los
    8 reportes comparten los mismos containers (regla #16). Compras,
    Inventario Valorizado y Salidas (desde 2026-08-04) conservan un addendum
    propio — cada uno sabe que tiene exactamente 2 chips-popover de filtro
    (Compras: Familia/Subfamilia; Inventario: Área/Familia; Salidas: Sub
    Almacén/Familia) y les fuerza `min-width:230px`; el resto deja que cada
    chip mida su contenido, porque puede haber más de 2 (Ajuste tiene 4,
    Ventas tiene 4). El móvil (`max-width:900px`) no se tocó en esta
    generalización: sigue siendo el estilo "tab" original en todos los
    reportes.
    **Regla:** si agregás una regla que hoy solo aplica a Compras o Ajuste
    sobre `fila_ajuste_top`/`fecha_ajuste_pill`/`chips_ajuste_tabla`,
    preguntate primero si en realidad es universal (va en el bloque sin
    scope) antes de scopearla con `:has(.st-key-app_reporte_*)` — scopear de
    más es cómo se llega a los casi-duplicados que se acaban de eliminar.

18. **Los 8 reportes usan el rail derecho (`_render_rail`) desde 2026-08-04**
    — antes solo Compras y Ajuste. `render_vista_pills` (pestañas Gráficos/
    Tabla sueltas en la franja) se ELIMINÓ de `graficos/__init__.py`: ya no
    tiene caller. Si un reporte tiene dashboard propio (Ajuste, Compras,
    Ventas, Inventario Valorizado, Receta Venta, Salidas — desde 2026-08-04),
    "Tabla" es un item más del rail. Si NO tiene dashboard (Receta Base), el
    rail tiene 2 items genéricos ("Gráficos" → `renderizar_graficos_reporte`
    sin entrada en `_DASHBOARDS`, cae al explorador; "Tabla" → AgGrid).
    Requerimientos (tabla pivote propia, sin graficos) tiene un rail de 1
    solo item.
    **El callback `tabla_cb` no tiene firma fija — cada dashboard documenta
    la suya en su docstring:**
    - Sin chips propios (Ajuste, Receta Venta): `tabla_cb()` sin args — usan
      los filtros genéricos que arma app.py (`_filtros_chips_franja`).
    - Con chips propios (Ventas, Inventario Valorizado, Salidas): `tabla_cb(d)`
      — se les pasa el df YA filtrado por sus propios chips (definidos dentro
      del módulo del dashboard), para que la Tabla no tenga un estado de
      filtros distinto al de los gráficos. Ver
      `graficos/__init__.py::renderizar_graficos_reporte`.
    **Antes de agregar un dashboard nuevo:** decidí si va a tener chips de
    filtro propios (entonces `tabla_cb(d)`) o no (entonces `tabla_cb()`) —
    mezclar los dos estilos en un mismo dashboard es la fuente de bugs más
    probable acá.

19. **`@st.cache_data` NO debe envolver la función que devuelve `None`/vacío
    ante un fallo transitorio: cachea el fracaso.** `cache_data` guarda
    CUALQUIER return, indexado por los args. Si `cargar(archivo)` capturaba la
    excepción y devolvía `None`, ese `None` quedaba cacheado `ttl=3600` → el
    reporte se veía vacío **1 hora entera**, sin reintentar R2, aunque el
    parquet ya estuviera perfecto. Y como `app.py` hace `st.stop()` cuando
    `df is None`, el corte se lleva puesto también el rail derecho y las
    franjas — el síntoma parece "se rompió media app" cuando es solo un
    `None` pegajoso en cache.
    **Regla:** separar la lectura en dos capas:
    - `_*_cacheable()` con `@st.cache_data`: cachea SOLO el éxito. Si algo
      falla, **lanza** (una corrida que lanza excepción no se cachea).
    - wrapper público SIN cache: llama a la interna en `try/except` y traduce
      el fallo a `None` (contrato histórico de los callers). Como el fallo vive
      en el wrapper no cacheado, cada rerun reintenta de verdad: F5 recupera.
    Aplica a `cargar`, `cargar_rango`, `rango_fechas` en `data.py`. Ojo con la
    distinción fino: un `None` que es RESULTADO válido (p.ej. `rango_fechas`
    cuando el parquet no tiene fechas) SÍ es cacheable — solo la EXCEPCIÓN debe
    quedar fuera del cache.
    Motivo (bug real, 2026-08-04): un blip de R2 (o el parquet
    re-escribiéndose justo al leerlo) dejó Ajuste y Compras en blanco, sin
    rail, durante una hora. Es la hermana de la regla #15: las dos son formas
    en que `cache_data` sirve algo que ya no corresponde.

20. **Boxplot/histograma con datos mayoritariamente en cero: filtrar el cero
    ANTES de graficar, no después.** En `_graf_distribucion_ajuste`
    (`graficos/ajuste.py`), como en un inventario normal la mayoría de
    productos NO tiene diferencia, `AJUSTE VALORIZADO` viene con >50% ceros.
    Eso rompe dos tipos de gráfico de forma distinta:
    - `px.box`: si q1 = mediana = q3 = 0 (el caso típico con >50% ceros), la
      caja tiene ancho cero y es invisible — Plotly clasifica como "outlier"
      cualquier punto fuera de una cerca (`fence`) calculada sobre un rango
      intercuartílico de 0, así que hasta diferencias chicas (S/ 50) se
      dibujan como puntos sueltos flotando. El usuario ve una nube de puntos
      sin caja y no entiende qué está viendo.
    - `go.Histogram`: el bin de 0 concentra la mayoría de las filas y
      domina la escala; las líneas verticales de Cero/Media/Mediana caen casi
      en el mismo x y sus anotaciones de texto quedan superpuestas e
      ilegibles.
    **Regla:** para vistas de "distribución", excluir las filas en cero ANTES
    de construir la figura (`df[df[col] != 0]`), no confiar en que el tipo de
    gráfico las absorba. El conteo de filas excluidas se muestra como texto
    (`st.caption`) aparte, no se pierde. De paso, un boxplot con vocabulario
    de cuartiles/outliers tampoco lo lee un usuario de negocio sin
    entrenamiento — reemplazado por un strip plot (`px.strip`) coloreado por
    signo (rojo = faltante, verde = sobrante), sin estadística que explicar.

21. **Columnas reales de `salidas.parquet` confirmadas 2026-08-04** (antes
    `data.py` traía un supuesto sin verificar, con nota explícita de que
    podía estar mal): `Fecha registro`, `Cant Salida`, `Valor Neto`,
    `Tipo Descargo`, `Sub Almacen`, `Nombre Producto`, `Nombre Familia`,
    `Nombre SubFamilia` (jerarquía `Nombre Familia` > `Nombre SubFamilia` >
    `Nombre Producto`, igual que en Inventario). **No hay columna
    `Nombre Area` en Salidas** — el destino de la salida es `Sub Almacen`
    (a diferencia de Inventario/Ajuste, que sí usan `Nombre Area`).
    `Nombre SubFamilia` no tiene chip propio (el pedido original era
    filtro de Área/Familia nada más) pero sí está en `agrupar`, para que
    la Tabla pueda agruparse por ella.
    Con esas columnas, Salidas pasó de explorador genérico de un solo
    gráfico a dashboard propio (`graficos/salidas.py`, mismo patrón que
    `inventario.py`: chips Sub Almacén/Familia en la franja + toggle de
    métrica Cantidad/Valorizado + rail con Evolución/Subalmacén/Tipo
    descargo/Cruce/Top productos + Tabla). La granularidad Día/Semana/Mes/Año
    de la vista Evolución reusa `_periodo_serie` de
    `graficos/compras/_comun.py` (importado vía `graficos.compras`, que ya
    la re-exporta para `test_graficos.py`) en vez de reimplementar el
    cálculo de periodo.
    **Datos demo:** `_datos_demo` (`data.py`) no tenía rama propia para
    `salidas.parquet` — caía en la rama genérica con columnas que YA NO
    coinciden (`Cantidad`/`Importe Total`/`Nombre Area` en vez de los
    nombres reales de arriba), lo que hacía imposible probar el dashboard
    en el preview local sin datos reales. Se agregó una rama dedicada
    (mismo criterio que `inventariovalorizado.parquet`) con las columnas
    reales, incluida `Tipo Descargo` con 3 valores de ejemplo (Consumo
    Interno/Merma/Transferencia). **Si agregás un dashboard nuevo con
    columnas propias, sumale su rama en `_datos_demo` en el mismo commit**
    — si no, nadie puede verificar el layout en local sin secrets R2 (ver
    "Auditar el layout" en `CLAUDE.md`).
