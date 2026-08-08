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
| `estado_rango.py` | **Dueño único** del rango de fechas de la franja superior (`clave_rango`, `asegurar_rango`, `atajos_rango`, `aplicar_atajo`). Nadie escribe la clave del rango fuera de este módulo — ver regla #24. |
| `data.py` | Carga de datos: DuckDB + httpfs leyendo parquets de R2 (secrets). Sistema de refresco bajo demanda vía R2. |
| `tablas/` | **Paquete de tablas AgGrid** (refactor 2026-08-01; antes un `tablas.py` de 2.028 líneas). `__init__.py` re-exporta la API pública. `_css.py` (CSS de grid y paneles), `_config.py` (estilos de celda/fila, sidebar, totales), `desktop.py` (`renderizar_aggrid_desktop`), `movil.py` (`renderizar_aggrid_movil`), `compras.py` (`renderizar_aggrid_compras` + `renderizar_tabla_compras`, esta última legacy y sin uso), `ajuste_pivote.py` (`renderizar_aggrid_pivote_ajuste`, tabla "Por fecha" de Ajuste de Inventario — ver regla #25). |
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

10. **Ajuste SÍ se puede verificar en local desde 2026-08-05.**
    `data.py::_datos_demo` tiene rama propia para `ajusteinventario.parquet`
    (240 filas, columnas en MAYÚSCULAS como el parquet real, fecha con hora
    al minuto). Antes no la tenía: sin `AJUSTE VALORIZADO` la vista caía al
    explorador genérico y el item "Tabla" del rail no llegaba a existir, así
    que ni la cascada ni la tabla se podían mirar levantando la app.
    Al agregar o cambiar un demo, **reiniciar el server**: `@st.cache_data`
    envuelve `_cargar_cacheable`, no `_datos_demo`, así que editar el demo
    no invalida nada y se sigue sirviendo el df viejo.
    Medir con JS (`getBoundingClientRect` + `scrollHeight`) encuentra los
    colapsos de layout que una captura de pantalla no delata.

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

    **2026-08-06 — la franja dejó de ser transparente.** `fecha_ajuste_pill`
    y `chips_ajuste_tabla` son `position:fixed` sin fondo propio; sin nada
    detrás quedaban flotando sobre la tabla al hacer scroll (reportado con
    capturas — se veían "en el aire"). El `::before` de `fila_ajuste_top`
    (`estilos/_40_ajuste_franja.py`) ahora es "cristal esmerilado": blanco
    translúcido (`rgba(255,255,255,.62)`) + `backdrop-filter: blur(14px)`.

    **2026-08-06, misma tarde — de franja de borde a borde a tarjeta
    centrada.** El cristal esmerilado gustó, pero iba `left:90px` a
    `right:0` y dejaba dos zonas SIEMPRE vacías con fondo blanco encima
    (antes del pill de fecha — ahí viviría el título, oculto por pedido,
    ver `app.py::col_titulo` — y después del cluster de chips, que en
    desktop vive centrado, no pegado al borde). Ahora `right` es
    `calc(50vw - 300px)`, la misma lógica de centrado que ya usa
    `chips_ajuste_tabla`, y las esquinas de abajo se redondean (cuelga del
    borde superior en vez de ser una franja). El override de Compras
    (`_20_compras_rail.py`) perdió su `right:84px` propio: por ser más
    específico le ganaba al `calc()` nuevo y anulaba el achique en el
    reporte que más lo pidió — ahora solo ajusta `height` (34px) y hereda
    `right` del default. Móvil (`_99_movil.py`) fija su propio `right:0`
    porque el `calc()` da negativo por debajo de los ~600px de ancho.
    Sigue valiendo "si es universal, va en la regla base" — pero ojo: un
    override "de más" en un selector más específico puede anular un ajuste
    nuevo de la regla base sin que se note hasta mirar la especificidad.

    **2026-08-06, 3ra vuelta — alinear con la tarjeta, no adivinar.** El
    `calc(50vw - 300px)` de la vuelta anterior era una aproximación
    (centrar con `chips_ajuste_tabla`); se pidió alinear en cambio con el
    borde real de `.st-key-ajuste_graf_card_izq_<reporte>` (el contenedor
    del gráfico). En vez de sumar otro número a ojo, se midió en vivo con
    el preview local (`getBoundingClientRect` + `getComputedStyle`, Compras
    y Ventas, 2 anchos de viewport): el borde de esa tarjeta es
    `left:170px` / `right:163px` — dos CONSTANTES fijas (90px rail + 80px
    padding-left default de `.block-container` que pone Streamlit solo;
    153px padding-right del rail + ~10px de margen exterior), no un
    cálculo relativo al viewport. Confirmado con `getComputedStyle` en 2
    reportes × 2 anchos: coincide exacto en los 4 casos. Moraleja para la
    próxima vez que se "sienta" que algo no está alineado: medir el
    elemento real con JS en el preview ANTES de proponer otro número —
    ver `arquitectura.md`/CLAUDE.md § "Auditar el layout antes de proponer
    píxeles".

    **2026-08-07 — la franja de 34px de Compras se universalizó.** Compras
    tenía su propia franja más baja (34px en vez de 50px) con `top:3px` en
    `fecha_ajuste_pill`/`chips_ajuste_tabla` para que no asomaran por el
    borde inferior (ver el fix del 2026-08-06 arriba). Se pidió el mismo
    look para los 8 reportes: ahora `.st-key-fila_ajuste_top::before` es
    `34px` en desktop (`_40_ajuste_franja.py`, dentro de un
    `@media(min-width:901px)` — **fijo en px, no se tocó la variable
    `--cab-altura`**, que sigue en 50px porque también alimenta el pill
    "tab" de la franja 769-900px) y `top:3px` vive en el bloque
    `@media(min-width:901px)` de `_50_fecha.py` para ambos elementos. El
    override propio de Compras en `_20_compras_rail.py` se eliminó (quedó
    idéntico al default); solo le queda su `padding-top:2px` en el
    wrapper, que es otra cosa (espaciado del rail, no la franja). **Los
    dos números (34px / top:3px) van acoplados** — si se vuelve a tocar
    uno, revisar el otro.

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

22. **Un dashboard puede cargar el parquet de OTRO reporte — primer caso:
    "Venta vs Compra" en Ventas (2026-08-04)** (`graficos/ventas.py`).
    Hasta ahora cada dashboard vivía enteramente dentro de los datos de su
    propio reporte (`df_f`); esta vista es la primera excepción: llama
    `data.cargar("compras.parquet")` directamente (no hay `df_f` de Compras
    disponible en el contexto de Ventas) y agrega el valor de compra por
    día, acotado al rango de fechas que ya tiene la vista de Ventas
    (`_ventas_cargar_compra_diaria`). **Es un cruce por FECHA únicamente**
    — Compras y Ventas no comparten ninguna llave — así que "Compra" es el
    gasto TOTAL en compras ese día, NO el costo de lo que se vendió ese día
    (una compra de insumos no se vende necesariamente el mismo día). Si
    compras.parquet no tiene datos en el rango, o le faltan las columnas
    de fecha/valor, la serie se omite en silencio (con un `st.caption`
    explicando por qué) — no rompe el resto del gráfico. Como `cargar()`
    ya cachea con `@st.cache_data`, este segundo load no es más caro que
    visitar el reporte Compras por separado.
    La vista es NUEVA (`("Venta vs Compra", "Vs Compra")` en
    `_VENTAS_RAIL_CATEGORIAS`), no reemplaza "Venta por día" — mismo
    espíritu que un gráfico bursátil (líneas de Venta/Costo/Compra arriba,
    Pax en barras en un subplot separado abajo, vía
    `plotly.subplots.make_subplots`), a diferencia de "Venta por día" que
    usa barras agrupadas + Pax en eje secundario. Con Costo/Compra/Pax
    ausentes, cae a un gráfico de una sola línea (Venta) sin romperse.
    **Datos demo de Ventas:** no existían (`ventas.parquet` caía en la
    rama genérica y por eso el dashboard entero mostraba el explorador
    genérico en modo demo — un gap preexistente, no de este cambio). Se
    agregó una rama dedicada con las columnas reales (`Fec Reg Documento`,
    `Venta Item Ddocumento`, `Precio Costo`, `Cant Pax`, `Llave Local
    Pedido`, `Grupo`, `Sub Grupo`, `Nomb Item Venta`,
    `Cantidad Item Ddocumento`) — con una particularidad: **Ventas usa
    `carga_por_rango`, así que a diferencia de TODOS los demás datos demo
    (fechas fijas en 2024/2025), este ancla las fechas a `pd.Timestamp.now()`**.
    Si no fuera así, la carga inicial (rango por defecto "01-del-mes-actual
    → hoy") no encontraría ninguna fila y la app cortaría con "no se
    pudieron cargar los datos" antes de llegar a ningún dashboard.
    **Bug preexistente descubierto de paso (no corregido, solo documentado):**
    `data.py::_cargar_rango_cacheable`, rama demo, filtra por una columna
    llamada literalmente `"Fecha"` (`col = "Fecha" if "Fecha" in df.columns
    else None`) — funciona por coincidencia con la rama demo genérica
    (que sí se llama así) pero NO reconoce `"Fec Reg Documento"` (el
    nombre real de Ventas) ni ninguna otra variante. Efecto: en modo demo,
    el date-picker de Ventas es cosmético — la carga siempre devuelve el
    dataset completo sin importar el rango elegido. No afecta producción
    (ahí si usa el nombre real de columna vía DuckDB). Si alguna vez hace
    falta que el rango sí filtre en demo, hay que resolver la columna con
    `buscar_columna`/`_resolver` en vez de comparar el string fijo
    `"Fecha"`.

23. **`showspikes` en subplots hay que pedirlo en CADA eje X, no en uno
    solo** (`graficos/ventas.py::_ventas_venta_compra_dia`). Con
    `make_subplots(shared_xaxes=True)` los ejes X quedan "matched" (mismo
    rango/zoom), pero cada uno decide por su cuenta si DIBUJA su propia
    línea de crosshair — pedir `showspikes=True` solo en la fila de abajo
    (donde vive el formato de fecha/ticks compartido) hace que la cruz
    vertical no aparezca al pasar el mouse por el panel de arriba. Hay que
    separar el `fig.update_xaxes(...)` en dos llamadas: una con `row=` para
    lo que sí debe ser exclusivo de una fila (formato de fecha, ticks), y
    otra SIN `row=` (aplica a todos los ejes X del figure) para
    `showspikes`/`spikemode="across"`/`spikedash`. Se verificó disparando
    un `mousemove` sintético sobre el `.js-plotly-plot` y contando
    `.spikeline` en el DOM — con un solo eje configurado aparecía 1 línea
    (solo en el panel de abajo); con los dos, aparecen 2 (una por panel,
    cruzando el gráfico entero como en la referencia bursátil).
    De paso: **Venta/Costo/Compra se normalizan a % de variación desde el
    primer valor != 0 del rango** (no S/), con un `fig.add_annotation`
    (badge de color, sin bordes redondeados — Plotly no los soporta en
    anotaciones) al final de cada línea mostrando el % acumulado — mismo
    propósito que el "Comparar con" de un gráfico bursátil: Venta/Costo/
    Compra tienen escalas en soles muy distintas entre sí, así que
    compararlas en valor absoluto en el mismo eje no dice mucho; en % desde
    el mismo punto de partida sí. Los badges "flotantes que siguen al
    cursor" de la referencia (el valor cambia en tiempo real sobre cada
    línea al mover el mouse) NO tienen equivalente nativo en Plotly — eso
    requeriría JS custom enganchado al evento `plotly_hover`, que este
    proyecto no usa en ningún lado (`st.markdown` no ejecuta `<script>`,
    ver regla de `CLAUDE.md`). Lo que sí es nativo y se usó en su lugar:
    `hovermode="x unified"` — un único tooltip con el valor de cada serie
    en la fecha del cursor, agrupado junto al cursor en vez de flotando en
    el borde derecho.

24. **Un reporte puede necesitar MÁS DE UNA clave de rango de fecha, una
    por "familia" de gráfico** (`estado_rango.py::clave_rango` +
    `graficos/ajuste.py::categoria_rango_ajuste`). Ajuste de Inventario
    tiene gráficos que solo dicen algo con un período acotado (Cascada,
    Mapa de calor, Distribución — snapshot de un mes) y otros que solo
    dicen algo con varios meses o un año (Evolución, Comparativa mensual —
    tendencia). Antes compartían una única clave (`ajuste_rango_aplicado`)
    y cambiar de pestaña en el rail les pisaba el rango entre sí. Se separó
    en `ajuste_rango_aplicado_visual` / `_tiempo`, elegida por
    `categoria_rango_ajuste(ajuste_graf_tipo)` — cada categoría del rail
    recuerda su propio rango. `categoria_rango_ajuste` deriva la categoría
    de `_AJUSTE_RAIL_CATEGORIAS` (única fuente de verdad: agregar un ítem
    nuevo al rail no exige tocar el mapeo).
    **Al tocar esto de nuevo, grepear el nombre viejo de la clave antes de
    borrarlo** — no todos los lugares que la leen pasan por la variable
    calculada: `app.py` tenía un `st.session_state.pop("ajuste_rango_
    aplicado", ...)` hardcodeado al cambiar de reporte, y una función
    `_calcular_ajuste_ambito_auto()` que la leía con el string suelto (esa
    función resultó ser código muerto — sin ningún caller en todo el
    repo — y se eliminó en el mismo commit). `estado_rango.py` es DUEÑO
    ÚNICO precisamente porque este tipo de lectura hardcodeada, suelta en
    otro archivo, es la fuente histórica de los desyncs (overlay ≠
    calendario ≠ datos) que el módulo existe para evitar.

25. **Tabla dinámica de Ajuste — reescrita 2026-08-07 como AG Grid real**
    (`graficos/ajuste.py::_tabla_pivote_fecha_ajuste` +
    `tablas/ajuste_pivote.py::renderizar_aggrid_pivote_ajuste`, rail "Por
    fecha de corte"). Antes era HTML a mano (`st.columns` + `st.markdown`,
    árbol con sets en `session_state`) con flecha de tendencia vs. el
    corte anterior; se reemplazó por Familia > Subfamilia > Producto como
    `rowGroup` nativo (árbol expandible de AG Grid, ya no botones ▸/▾
    hechos a mano) + columnas por periodo (Día/Semana/Mes, `st.pills`) con
    Ajuste Valorizado + Ajuste en una celda compacta. Pre-pivotea con
    pandas (`_armar_tabla_pivote_ajuste`) a un dataframe WIDE — una fila
    por Familia+Subfamilia+Producto, columnas `ajv_i`/`aj_i` por periodo —
    y deja que AG Grid agrupe y sume; con Mes arma las 12 columnas del año
    FIJAS (meses futuros vacíos) para que la tabla no cambie de forma mes
    a mes, con Semana/Día solo las que ya tienen datos (sin el tope de 6
    columnas de la versión vieja: el scroll horizontal nativo banca
    bastantes más). Ignora a propósito el rango de fecha de la franja
    superior — parte siempre de `df_full` acotado al año EN CURSO, mismo
    patrón que la rama "Histórico" del mismo archivo.

    **Se pierde la flecha de tendencia a propósito**: un pivote de verdad
    agrega por columna, no compara una columna contra su vecina — esa
    comparación necesitaría un cellRenderer con acceso a la columna de al
    lado, el acoplamiento frágil que esta reescritura evita. Si hace falta
    de nuevo, es una vista aparte, no un parche acá.

    **No usa `pivotMode` nativo**: cada celda de periodo combina DOS
    números (Ajuste Valorizado grande + Ajuste chico) de DOS columnas
    fuente fijas por Python — pivotear de verdad con 2 valores activos da
    2 columnas SEPARADAS por periodo (una opción de diseño descartada:
    más nativa, pero el doble de columnas y sin la celda compacta). En
    cambio cada periodo es una columna SINTÉTICA (`colId` propio, sin
    `field`, agregada a mano a `grid_options["columnDefs"]` después de
    `gb.build()` — `configure_column` exige que la columna YA exista como
    field, regla #26) con `valueGetter` (arma `{ajv, aj}` por fila hoja) +
    `aggFunc` propio en JS (suma ambos al agrupar, no el `"sum"` nativo) +
    `comparator` propio (ordena por `.ajv` — el comparador default hace
    `<`/`>`, que no sirve contra un objeto). El panel "Modo pivote" del
    sidebar queda AFUERA a propósito (no solo apagado): arrastrar algo ahí
    rompería la relación fija entre la columna y su periodo.

    **`api.getValue(colKey, rowNode)` YA NO EXISTE** en la versión de AG
    Grid de este proyecto (34.3.1, ver warning de consola con el número).
    El diseño original leía la columna hermana oculta desde el
    cellRenderer con esa llamada — tiraba "Component Error: params.api.getValue
    is not a function", visible solo DENTRO del iframe del componente
    (`doc.body.innerText` del iframe, no la consola de la ventana
    principal). La reescritura con valueGetter+aggFunc de arriba no
    depende de leer una columna vecina en absoluto, así que tampoco se
    rompe si el reemplazo documentado (`api.getCellValue({colKey, rowNode})`)
    cambia de nombre otra vez.

    **Un cellRenderer-función que devuelve un STRING de HTML no se trata
    como HTML acá — se ve como texto escapado** (los `<div style=...>`
    literales en pantalla, confirmado leyendo `.innerHTML` del cell real:
    el hijo es un text node, no un elemento). Devolver un `HTMLElement`
    directo (`document.createElement(...)`) tampoco sirve: revienta con
    "Minified React error #31: objects are not valid as a React child".
    `st_aggrid` usa `ag-grid-react`, y ahí el atajo "vanilla" de AG Grid
    puro (`function(params){ return 'string o Node'; }`) no está
    soportado — hace falta la interfaz de Component completa: una
    `class` con `init(params)` que arma `this.eGui` (con
    `document.createElement` + `textContent`/`style.xxx`, nunca un string
    de HTML) y `getGui()` que lo devuelve (`refresh` puede devolver
    `false` sin drama). Mismo problema y misma solución hacía falta para
    `groupRowRendererParams.innerRenderer` (pinta "ALIMENTOS (3) ·
    S/ 260" en la fila de grupo).
    **OJO — sospecha sin confirmar:** `tablas/desktop.py` tiene un
    `innerRenderer` con el patrón viejo (función que devuelve un string)
    para Inventario Valorizado; no se tocó en este cambio pero por este
    mismo motivo es candidato a mostrar el HTML escapado en vez del
    "Familia (n) · S/ valor" esperado — nadie lo había mirado de cerca
    (mismo motivo que la regla #40: la mayoría navega por Gráficos, no
    "Tabla"). Pendiente de verificar contra un grid real.

    **`groupRowRendererParams.innerRenderer` va en las opciones del
    grid, NO en `autoGroupColumnDef.cellRendererParams`.** Con
    `groupDisplayType: "groupRows"` las filas de grupo se pintan con un
    renderer de ANCHO COMPLETO aparte (`agGroupRowRenderer`); el
    `cellRendererParams` de `autoGroupColumnDef` solo aplicaría con
    `groupDisplayType: "singleColumn"`. Puesto en el lugar equivocado no
    tira ningún error — la celda de grupo simplemente muestra el valor
    crudo sin formatear, fácil de no notar si no se mira de cerca.

    **Con 3 columnas en `rowGroup` (Familia, Subfamilia, Producto),
    Producto queda como grupo de UN solo hijo** — un nivel más para
    expandir sin información nueva (el "grupo" Producto solo contiene la
    fila real, hay que abrirlo para ver lo mismo que ya decía su nombre).
    Con Familia+Subfamilia como `rowGroup` y Producto como columna PROPIA
    pinneada a la izquierda (no vía `autoGroupColumnDef.field`), el árbol
    termina en el producto como fila hoja real. Se intentó primero
    `autoGroupColumnDef.field=col_producto` para que la hoja mostrara el
    nombre sin una columna extra: con `groupDisplayType: "groupRows"` las
    filas hoja NO terminan pintando el auto-group column en absoluto
    (queda en blanco, `getAllGridColumns()` ni siquiera lo lista) —
    verificado en vivo, no se pudo confirmar por qué, solo que no
    funciona.

    **Verificación**: el demo de `ajusteinventario.parquet` tiene fechas
    fijas en 2024 (regla #10) y esta vista filtra a propósito por año EN
    CURSO — con el sistema en 2026 el demo no tiene ninguna fila que pase
    el filtro, así que la vista "feliz" (con datos) no se puede ejercer
    navegando la app real en este momento; solo el estado vacío
    ("Sin datos de 2026...") se verificó ahí. Las dos mitades se
    verificaron por separado: un script standalone (pandas puro, sin
    Streamlit) que llama a `_armar_tabla_pivote_ajuste` con fechas 2026
    sintéticas y compara sumas contra el dataframe original en las 3
    granularidades; y una app Streamlit aislada de un archivo (temporal,
    con su propio puerto en `.claude/launch.json`, borrada al terminar —
    técnica de la regla #12) que llama a `renderizar_aggrid_pivote_ajuste`
    directo con un dataframe wide armado a mano, inspeccionada vía
    `window.__agApiPivoteAjuste` (expuesto en `onGridReady`, mismo
    espíritu que `window.__agApi` de la regla #33) porque simular clics
    de expandir con `dispatchEvent(new MouseEvent(...))` deja el estado
    interno (`node.expanded`) en `true` pero NO recalcula las filas
    mostradas (`getDisplayedRowCount()` no cambiaba) — hace falta
    `api.onGroupExpandedOrCollapsed()` después de `setExpanded()` cuando
    se llama a la API a mano en vez de por un clic real; un clic real del
    usuario sí dispara ese refresh solo. No se pudo confirmar la
    integración completa con datos 2026 reales dentro de la app (eso
    recién se ve en Cloud, o cambiando la fecha del sistema).

    **2026-08-07, misma tarde — el año como grupo de columna.** Pedido
    real de uso: con solo "ene"/"feb"/... en la cabecera no quedaba claro
    de qué año, aunque la vista solo muestre uno a la vez. En vez de
    repetir el año en cada columna (`renderizar_aggrid_pivote_ajuste`
    recibe `anio` opcional), va UNA vez como grupo de columna (`children`
    en el colDef, la manera estándar de AG Grid de agrupar cabeceras) por
    encima de los periodos — Total queda AFUERA del grupo a propósito, no
    es "del año", es el cierre de la fila. `.ag-header-group-cell` no
    tenía estilo propio en `tablas/_css.py` (nadie había agrupado columnas
    en este grid todavía): se agregó lavanda (`LAVANDA_CABECERA_GRUPO`,
    literal "fondo de cabeceras de grupo de columnas" en `tema.py`) SOLO
    en `tablas/ajuste_pivote.py`, no en el CSS compartido — si otro grid
    empieza a agrupar columnas y quiere el mismo look, recién ahí vale la
    pena subirlo a `_css.py`.

    **2026-08-07, misma tarde — "Día" reemplazado por "Corte": agrupar
    por RACHA de días, no por calendario** (`graficos/ajuste.py::
    _cortes_por_racha`). Motivo (pedido real de negocio): una sesión de
    conteo de inventario puede durar varios días — 1/2/3, después un
    salto, 15/16, después un salto grande, 1/2/3/4 del mes siguiente — y
    "Día" calendario mostraba cada uno como columna suelta sin relación
    entre sí, cuando en realidad son 3 sesiones ("cortes") de duración
    distinta. `_cortes_por_racha` ordena las fechas únicas y corta un
    corte nuevo cuando el salto al día siguiente con movimiento supera
    `_CORTE_MAX_SALTO_DIAS = 4` (constante fijada a pedido explícito, no
    a ojo — tolera huecos cortos tipo fin de semana dentro de UNA misma
    sesión). Etiqueta: `"1-3 ago"` (rango dentro del mismo mes), `"15
    ago"` (corte de un solo día, sin rango), `"30 jul - 2 ago"` (corte
    que cruza de mes — se nombra el mes en los DOS extremos solo cuando
    difieren, si no se repite innecesariamente).
    A diferencia de Semana/Mes (cada fecha resuelve su clave sola, sin
    mirar las demás), Corte necesita la lista COMPLETA de fechas únicas
    ANTES de poder asignarle una clave a ninguna — no hay forma de saber
    si el día 16 abre un corte nuevo sin haber visto ya el día 15. Por
    eso `_cortes_por_racha` arma un mapa fecha→(clave, etiqueta) aparte y
    lo aplica con `.map()`, en vez de la cuenta vectorizada de una sola
    pasada que alcanza para Semana/Mes.
    No se reemplazó el pill por agregar una 4ta opción a propósito: un
    día suelto sin sesión sigue siendo su propio corte (una racha de 1),
    así que "Corte" cubre el mismo caso que "Día" cubría antes y no hacía
    falta la opción extra.
    Verificado con pandas puro (sin Streamlit) contra el escenario exacto
    de arriba más los bordes del umbral (salto de 4 días exactos sigue
    siendo el mismo corte, salto de 5+ corta) y el cruce de mes — la
    parte de render (AgGrid) no cambió nada: sigue recibiendo la misma
    forma de `periodos`/`wide` sin importar cómo se calculó la clave.

26. **`GridOptionsBuilder.configure_column()` PISA el `headerName` cada vez
    que se lo llama sin `header_name`.** No hace merge parcial: reconstruye
    el colDef con `{"headerName": field, "field": field}` y recién después
    aplica los kwargs. O sea, cualquier `configure_column(c, loQueSea=...)`
    posterior devuelve la cabecera al nombre crudo del campo.
    **Regla:** el loop que pone las cabeceras en español (`_titulo_es`) va
    ÚLTIMO en `tablas/desktop.py`, después de todo otro `configure_column`.
    Motivo (bug real, 2026-08-05): el loop de `suppressFiltersToolPanel`
    corría después y dejaba `AJUSTE`, `AJUSTE VALORIZADO`, `AREA` y
    `FAMILIA` en MAYÚSCULAS mientras el resto de la tabla salía en "Nombre
    Propio" — se veía en la cabecera y en las pastillas de "Modo pivote".

27. **La fila de totales suma por DEFAULT toda columna numérica; la lista
    negra es la excepción.** `_fila_totales` clasificaba por palabra clave
    (valorizado/total/…, precio/promedio/…, stock) y lo que no matcheaba
    quedaba en `None` → celda vacía. Así, `AJUSTE` —la métrica que da
    nombre al reporte— no tenía total. Ahora el default de una numérica es
    sumar y `_NO_SUMABLE` (códigos y partes de fecha) decide qué no.
    La comparación es por **palabra completa**, no por "contiene": con
    substring `Cantidad` matchea `id` y `Tamaño` matchea `ano`. Y los
    acentos se quitan ANTES de partir en palabras, o `Año` se parte en
    ("A", "o") y nunca matchea.
    Pendiente conocido: la fila es `pinnedTopRowData`, dato estático — los
    filtros internos de AG Grid (panel "Filtros", cabecera) no la
    recalculan. Los chips de arriba sí, porque filtran el df en Python.

28. **Los paneles "Columnas" y "Modo pivote" abrían VACÍOS la primera vez.**
    AG Grid dibuja su lista virtual una sola vez, con el panel todavía
    `display:none` (viewport de alto 0) → calcula 0 filas visibles y no la
    redibuja al abrirlo. El contenedor sí sabe cuántas hay
    (`aria-label="Column List 15 Columnas"`), pero no renderiza ítems.
    No era el CSS del proyecto: se reproduce con el `custom_css`
    deshabilitado, y pasaba en todos los reportes, no solo Ajuste.
    **Solución** (en `inject_fix_column_panel_ajuste`): si el panel abre sin
    ítems, un `dispatchEvent(new Event('scroll'))` sobre
    `.ag-virtual-list-viewport` fuerza el `drawVirtualRows` con el alto ya
    real. Importa porque `cols_visibles` oculta columnas a propósito y ese
    panel es la única vía para reactivarlas.

29. **No reposicionar a mano los ítems de una lista virtual de AG Grid: hay
    que declararle el alto de fila y dejarla trabajar.** La lista está
    VIRTUALIZADA — al scrollear descarta los ítems fuera de pantalla y
    reposiciona el resto con SU alto de fila. Un JS que mida las pastillas y
    reescriba `top`/`height` pelea contra eso en cada scroll.
    Síntoma (bug real, 2026-08-05): el scroll del panel Columnas "se
    resistía". Lo que pasaba: AG Grid virtualizaba a 24px y el JS apilaba a
    38px; al scrollear AG Grid se quedaba con ~7 ítems, el JS los re-apilaba
    desde `top:0` (así que la lista arrancaba por la mitad) y encogía el
    contenedor a 266px — por debajo del viewport de 375px, o sea sin
    overflow → **`scrollTop` volvía a 0 solo** y las primeras filas
    desaparecían.
    **Solución:** `--ag-list-item-height` (ver `_ALTO_FILA_PANEL` en
    `tablas/desktop.py`) y borrar el reposicionado. Las pastillas ya son de
    alto fijo (label con `nowrap` + `ellipsis`), así que un valor uniforme
    es correcto; si algún día tuvieran alto variable, la respuesta NO es
    volver al JS, es forzarlas a alto fijo.
    **Dónde va la variable — esto es lo que cuesta encontrar:** AG Grid la
    lee de un div `.ag-measurement-container` que cuelga del div de TEMA
    (`ag-theme-params-N`), no del `.ag-root-wrapper` ni del `.ag-side-bar`.
    Puesta en cualquiera de esos dos no la ve. Y tampoco alcanza con
    ponerla en `html`/`body`: el div de tema DECLARA la variable, y una
    declaración propia le gana a lo heredado sin importar la especificidad
    del ancestro. Hay que pisarla en ese mismo elemento, y como el sufijo
    `-N` se genera por instancia, se matchea por prefijo:
    `[class*="ag-theme-params-"]` (especificidad 0,1,0 contra el `:where()`
    de 0,0,0 del tema).
    **Cómo verificarlo** sin adivinar: leer
    `getComputedStyle(document.querySelector('.ag-measurement-container'))
    .getPropertyValue('--ag-list-item-height')` dentro del iframe. Si no
    dice lo que pusiste, AG Grid tampoco lo está viendo.

30. **Ensanchar un `st.popover` (o cualquier botón) a `width:100%` dentro de
    un `st.container(key=...)` choca con DOS anchos que Streamlit fija por
    su cuenta, en capas distintas:**
    - El `<button>` de todo popover trae `[data-testid="stPopover"] button
      { min-width: 180px !important }` — una regla global (usada por los
      popovers de filtros). Un `width:100% !important` propio NO le gana:
      `min-width` puede vencer a `width` aunque ambos sean `!important`.
      Hace falta `min-width: 0 !important` explícito en el propio botón.
    - El envoltorio `[data-testid="stLayoutWrapper"]` (hijo directo de
      `st.container`) trae `width: fit-content` — con eso, `align-items:
      stretch` en el flex-column padre NO HACE NADA: `stretch` solo gana
      cuando el ancho del hijo es `auto`, y `fit-content` no es `auto`.
      Hace falta `width: 100% !important` explícito en el propio
      `stLayoutWrapper`.
    Sin las dos correcciones, el botón queda del ancho de su texto (medido
    por `getBoundingClientRect`, no por `getComputedStyle` — ver
    [[flujo-trabajo-ui]] sobre transiciones) aunque el CSS "debería" haberlo
    estirado. Caso real: el trigger del asistente (`asistente.py`,
    `.st-key-ai_float_wrap`) reposicionado como cabecera del rail de
    Compras/Ajuste — medía 68px con el `width:100%` puesto solo en el
    `<button>`; los 84px (ancho real del rail) solo llegaron tras fijar
    `min-width:0` en el botón y `width:100%` en el `stLayoutWrapper`.

31. **Botón `inline-flex` (trigger de `st.popover`) dentro de un contenedor
    en flujo `block`: el WRAPPER mide más de alto que el `<button>`, aunque
    el botón tenga `height` fija.** `height: 26px !important` en el
    `<button>` fija SU altura, no la del contenedor que lo envuelve.
    Streamlit intercala un `div` sin key (ni testid) entre
    `[data-testid="stPopover"]` y el `<button>`, y ese div queda en
    `display:block`: un hijo inline-level (el botón, aunque sea
    `inline-flex`) dentro de un flujo en bloque arma su propia línea de
    texto (strut) con el `line-height` HEREDADO — 1.6 por defecto acá —
    que agrega aire arriba/abajo del botón sin que el botón mismo lo
    reporte. Solo se detecta midiendo el WRAPPER (el nodo con la key, o
    `[data-testid="stPopover"]`) con `getBoundingClientRect`; el `<button>`
    solo sigue reportando los 26px que su CSS le pide.
    Motivo (bug real, 2026-08-06): `.st-key-ajcas_excl_wrap` ("Excluir
    productos" de la cascada de Ajuste) — botón a 26px por CSS, wrapper a
    33px por el strut heredado; 7px de aire "invisibles" que lo hacían ver
    más alto de lo que su propio CSS pedía.
    **Regla:** `line-height: 0` en el ancestro `[data-testid="stPopover"]`
    (se hereda hacia el div anónimo intermedio sin tener que tocarlo).
    Complementaria: sin `white-space: nowrap` en el `<p>` del label, el
    mismo botón compacto puede partir el texto en 2 líneas si la columna
    que lo aloja se angosta (`st.columns([N, 1])` no reserva un ancho
    mínimo) — ahí la `height` fija de verdad se rompe: el contenido
    desborda el box de 26px y el wrapper mide bastante más (44px
    verificado forzando la columna a 70px) en vez de recortar o
    mantenerse en una línea. Los dos ajustes viven juntos en
    `graficos/ajuste.py::_graf_waterfall_ajuste`.

32. **El coste por rerun de la tabla se paga en CADA cambio de filtro, no
    solo al abrir.** Medido a 10k filas en Ajuste (2026-08-06): un chip
    dispara un rerun del fragment, la fecha dispara uno COMPLETO (re-ejecuta
    las 8 inyecciones de nivel superior — cada `components.html` es un
    iframe que se vuelve a montar —, navegación y asistente), y en ambos
    casos el df entero se vuelve a serializar y AG Grid rearma su árbol de
    grupos desde cero. Tres trampas de Python que salieron de ahí, las tres
    reutilizables:
    - **`@st.cache_data` hashea CADA argumento.** Pasarle el DataFrame a una
      función que solo mira nombres de columna costaba 126 ms por rerun;
      pasándole `tuple(df.columns)` baja a ~1 ms. Si la función no necesita
      los datos, no le pases los datos.
    - **`.dt.date` en un filtro materializa un `datetime.date` de Python por
      fila.** El filtro de rango pasó de 27 ms a 3,7 ms comparando contra
      `pd.Timestamp`. El límite superior va como `< fin + 1 día` (no
      `<= fin`) para que el rango siga siendo inclusivo cuando la columna
      trae hora, que es el caso de `FECHA APERTURA INVENTARIO`.
    - **`pd.to_datetime()` recorre igual una columna que YA es datetime**
      (38 ms): guarda con `is_datetime64_any_dtype` antes.
    Y una que va al revés de lo que uno supondría: para derivar el mes,
    `dt.to_period("M").astype(str)` (18 ms) le gana por lejos a
    `dt.strftime("%Y-%m")` (396 ms); para el día es al revés, `strftime`
    (14 ms) le gana a `dt.date.astype(str)` (61 ms). No unificarlos.

33. **`st.markdown(..., unsafe_allow_html=True)` cuyo HTML arranca con un tag
    de bloque (`<div>`, no `<span>`/`<p>`) hereda un `margin-bottom: -16px`
    nativo de Streamlit en `stMarkdownContainer`, pensado para cancelar el
    margen de un `<p>` que en este caso no existe.** CommonMark reconoce
    `<div ...>` al inicio de la línea como "bloque HTML crudo" y NO lo
    envuelve en `<p>` — el `-16px` que Streamlit aplica (para neutralizar el
    `margin-bottom` de ~1em que traería un `<p>` normal) no tiene nada que
    cancelar ahí, y resta 16px directo a la altura que ve el
    `stElementContainer` padre. El contenido se sigue pintando a su alto
    real (`overflow: visible`), pero el flex padre reparte su `row-gap`
    según la altura que CREE que tiene ese hijo — si el `row-gap` del
    contenedor es menor a 16px, el resultado es overlap real sobre el
    siguiente hermano, no solo espacio apretado.
    Motivo (bug real, 2026-08-06): cabecera de la tabla de Ajuste (`Familia
    | Ajuste | Cascada acumulada | …`, `graficos/ajuste.py`) — con el
    `row-gap` de la card en el default de Streamlit (16px) el número daba 0
    y nadie lo notó; al bajar `row-gap` a 6px (regla "aire sobre el
    título", mismo archivo) el bug pasó a pintar el `border-bottom` de la
    cabecera 10px DENTRO de la primera fila. Medido con
    `getBoundingClientRect`: `stElementContainer` reportaba 6.4px de alto
    con contenido de 22.4px pintado encima.
    **Regla:** si el HTML de un `st.markdown` empieza con un tag de bloque
    y esa card usa un `row-gap` propio (no el default de Streamlit), sumale
    una clase propia al tag raíz (sobrevive el sanitizador, igual que
    `.ajcas-tip`) y anulá el `-16px` nativo apuntando a
    `[data-testid="stMarkdownContainer"]:has(> .tu-clase) { margin-bottom:
    0 !important; }`. Verificar SIEMPRE midiendo `stElementContainer` (el
    flex-item real que consume el `row-gap`), no el div visual — el div
    visual miente porque su `overflow` es `visible` por default.

33. **Dónde se va el tiempo de la tabla, medido (2026-08-06, 10k filas,
    Ajuste con sus 5 niveles de agrupación).** Los números salieron de la
    API real de AG Grid, expuesta como `window.__agApi` en `onGridReady`
    (`tablas/desktop.py`) — sin ese handle no hay forma de medir: la api
    vive en el state de React del componente.

    | operación | ms |
    |---|---|
    | **clic de chip hoy** — re-empujar `rowData` | **700–900** |
    | `setFilterModel()` sin tocar los datos | **120–150** |
    | primera carga (en frío) | ~1.800 |
    | `autoSizeAllColumns()` (solo 1ª vez) | 50–145 |
    | `sizeColumnsToFit()` | 0,3–1,3 |
    | `pivotMode` ON vs OFF | **sin diferencia** |

    Conclusiones que contradicen lo que parecía a simple vista:
    - **`pivotMode: True` no cuesta nada.** Parecía sospechoso porque se
      fija incondicionalmente sin columnas pivoteadas; medido, da igual.
    - **Lo caro es reagrupar cuando cambia la identidad de las filas.**
      st_aggrid define `getRowId` sobre `::auto_unique_id::`, un contador
      posicional. Empujar los MISMOS datos cuesta ~10-20 ms (AG Grid
      reusa los nodos por id); empujar un subconjunto filtrado —donde el
      id 0 ya es otro producto— cuesta 700-900 ms.
    - Por eso filtrar en Python es caro y filtrar con `setFilterModel` es
      5-6× más barato: el segundo no toca la identidad de las filas.

    **Trampa al medir esto:** si generás filas sintéticas clonando una
    existente con `Object.assign`, todas heredan el mismo
    `::auto_unique_id::` y AG Grid las colapsa en UNA sola. El grid
    reporta 10.000 filas empujadas y 1 hoja, y los tiempos que salen no
    significan nada. Hay que renumerar el id a mano.

34. **Los chips de Ajuste filtran en el NAVEGADOR, no en Python.** Es el
    cambio de 2026-08-06 contra la lentitud al tocar un filtro. Python sigue
    dibujando los mismos chips en el mismo lugar; lo que cambió es qué se
    hace con la selección.

    **El flujo:** `_filtros_chips_ajuste_tabla` devuelve `(df_filtrado,
    spec)`. El `df_filtrado` alimenta SOLO la fila de totales; a la grilla le
    llega el df SIN filtrar y el `spec` viaja por un BroadcastChannel
    (`inject_filtros_grid` → `onGridReady`), que lo deja en
    `window.__filtroExterno` y llama a `onFilterChanged()`.

    **Por qué el canal y no `gridOptions`:** el frontend de st_aggrid solo
    re-aplica `gridOptions` cuando cambió `gridOptions.rowData`, y con
    serialización Arrow rowData NUNCA viaja ahí (va como argumento aparte).
    Un `filterModel` puesto en `gridOptions` se ignora en silencio.
    Verificado leyendo su `componentDidUpdate`.

    **Por qué filtro EXTERNO y no `setFilterModel`:** las columnas de los
    chips (AREA, FAMILIA) son `rowGroup` + `hide`, y en ese caso AG Grid
    DESCARTA el modelo de un set filter — llamando `setFilterModel` a mano,
    `getFilterModel()` devuelve `{}`. El filtro externo no depende de
    columnas, y de yapa COMPONE con los filtros propios de la grilla en vez
    de reemplazarlos.

    **Top N:** no hay predicado "las n mayores", así que Python calcula el
    umbral (`|valor| >= t`) y filtra con ESE MISMO criterio. Así el total y
    la tabla no pueden discrepar; el precio es que con empates justo en el
    borde pueden entrar más de n filas.

    **Contra la falla silenciosa:** un filtro que no se aplica es peor que
    uno lento — el usuario ve números que cree filtrados. El grid acusa
    recibo por un segundo canal y el emisor reintenta 40 veces cada 150 ms
    (el primer render puede llegar antes del `onGridReady`); si tras 6 s no
    hay acuse, pinta un aviso rojo fijo en la página.

    **El sello** (md5 del spec) evita re-aplicar el filtro en los reruns que
    no lo cambiaron: `onFilterChanged` cuesta ~130 ms y la mayoría de los
    reruns no tocan los chips.

    Verificado con 240 filas: los datos NO se reenvían (240 hojas en el grid
    con el filtro puesto), Top 10 deja pasar exactamente 10, y la fila de
    totales de Python coincide al céntimo con la suma de las filas que pasan
    el filtro en el navegador.

35. **Fila/columna "TOTAL" en un `go.Heatmap` — categoría extra, no
    subplot.** Para sumar un resumen de fila/columna sin `make_subplots`
    (heatmap + barras con ejes compartidos es frágil: si el trace de barras
    no referencia las MISMAS categorías en el MISMO orden, no calzan), la
    fila/columna "TOTAL" se agrega como una categoría más en `x`/`y` con
    `z=None` en esa posición. Plotly le reserva un carril del mismo ancho
    que cualquier otra categoría — el total queda alineado sin calcular un
    solo píxel a mano. `z=None` (no un valor real) es la parte que importa:
    si el total entrara al cálculo de `zmin`/`zmax`, una fila que suma
    varias celdas podría superar a la celda individual más extrema y le
    robaría saturación al resto del mapa. El total se dibuja aparte
    (anotaciones en negrita + una línea divisoria con `xref="x"` /
    `yref="paper"` — así cubre toda la altura del área de trazado sin
    importar cuántas categorías haya).

    **Atenuar celdas sin tocar los datos:** un SEGUNDO trace `go.Heatmap`
    semitransparente (un solo color en el `colorscale`, `z=1` donde hay que
    atenuar y `z=None` donde no) encima del trace base, compartiendo eje
    (misma categoría por NOMBRE — no hace falta el mismo orden de trace) y
    mismos `xgap`/`ygap`. Más robusto que N `add_shape`: un trace en vez de
    una lista de rects que hay que reposicionar a mano si cambia el número
    de filas o columnas.

    **Tendencia en el hover: texto, no gráfico.** `hovertemplate` de Plotly
    es SOLO texto — la regla de siempre (`st.markdown` no ejecuta
    `<script>`) también tumba la idea de un sparkline SVG dentro del
    tooltip nativo sin un componente propio. Un sparkline de bloques
    Unicode (`▁▂▃▄▅▆▇█`) calculado en Python y metido en `customdata` sí
    funciona: es una cadena más para el hovertemplate. El detalle rico
    (línea real, con fecha en el eje) va en el panel de click-drill, que ya
    es contenido Streamlit normal y no pelea con esa limitación.

    Ver `graficos/ajuste.py::_graf_heatmap_ajuste` (totales + resalte del
    top 3 + tendencia, las tres capas conviven en el mismo trace/mismo
    click-drill).

36. **`margin` de un `go.Heatmap` no se respeta al píxel — medir, no
    calcular.** Con `margin=dict(t=50, b=18)` explícito y `automargin=False`
    en el eje que lo estaba pisando, el rect de fondo del heatmap (medido
    con `getBoundingClientRect()` en vivo) arrancaba en `y=42` (no 50) y
    medía 16px más de alto que `height - margin.t - margin.b`. Patrón: cada
    margen pedido queda ~8px más chico que el valor puesto, así que el área
    de trazado real crece por los dos lados combinados. Si algo depende de
    que una fila/columna del heatmap mida un número exacto de píxeles (ver
    regla #35, la columna de familia en HTML del mapa de calor en móvil),
    hay que restar ese excedente del `height`/`width` pedido, NO asumir
    `height - margin.t - margin.b` — y volver a medir si cambia la versión
    de Plotly o `_layout_aj`, no dar por sentado que el offset sigue siendo
    16.

37. **Columna fija mientras el resto scrollea, mezclando HTML propio + un
    gráfico de Plotly: se arman como flex-items hermanos, no como capas
    superpuestas.** El mapa de calor de Ajuste en móvil (11 áreas no entran
    en ~345px) resuelve "que la familia no se pierda de vista al scrollear"
    así:
    - La columna de familia se saca del heatmap (`yaxis.showticklabels =
      False`) y se arma aparte en un `st.markdown` con divs de altura fija
      (mismo `_ROWPX`/`_TOPM` que usa el layout del gráfico — ver regla
      #36 para por qué esos números no son los que uno pondría a ojo).
    - Ambos —la columna HTML y el `st.plotly_chart` (con
      `use_container_width=False` y ancho explícito, para que desborde a
      propósito)— viven como hijos DIRECTOS de un mismo
      `st.container(key=...)`, forzado a `display:flex; flex-direction:row;
      overflow-x:auto` por CSS. Un elemento simple (`st.markdown`,
      `st.plotly_chart`) cuelga su `stElementContainer` directo del
      `st.container` padre sin el wrapper intermedio que sí aparece cuando
      se anida un `st.container(key=...)` DENTRO de otro (ver regla #25) —
      por eso acá el sticky sí engancha poniéndolo en el propio
      `stElementContainer` (vía `:has()` sobre una clase marcador metida en
      el HTML, no una key nueva).
    - Verificación real, no de estilo computado (misma lección que la regla
      #25): `scrollEl.scrollLeft = N` y comparar `getBoundingClientRect()`
      de la columna antes/después. Si el dataset de la sesión no alcanza a
      desbordar, forzar un `<div>` ancho de prueba para poder mover
      `scrollLeft` y confirmar que la columna no se mueve mientras el resto
      sí.

38. **El `margin-top: -80px` de `[class*="st-key-ajuste_graf_card_izq_"]`
    (`estilos/_20_compras_rail.py`) asume que arriba de esa tarjeta NO hay
    contenido en flujo — solo chips.** Nació para Ajuste/Compras: tras quitar
    la vieja barra de pestañas horizontal, quedaba un hueco vacío entre los
    chips fijos y la tarjeta, y el negativo lo recuperaba subiendo la
    tarjeta bajo el rail (que es `position:fixed`, no ocupa espacio en el
    flujo). El selector es un wildcard por prefijo de key
    (`ajuste_graf_card_izq_<reporte>`), así que aplica a TODOS los
    dashboards que comparten ese patrón de tarjeta — hoy Ajuste, Compras,
    Ventas, Inventario y Salidas.
    Salidas (agregado 2026-08-04, después de que naciera el -80px) metió
    una fila de KPIs (`st.metric` × 3) EN FLUJO justo arriba de la tarjeta.
    Ahí sí hay contenido real donde antes había hueco vacío: el -80px se
    comía la fila de KPIs y el título del gráfico (visible p. ej. en el
    donut de "Tipo descargo") quedaba pintado encima de REGISTROS/
    CANTIDAD/VALORIZADO. Fix: selector de la MISMA especificidad
    (`.st-key-ajuste_graf_card_izq_sal` en vez del wildcard) puesto DESPUÉS
    del wildcard en el mismo archivo, `margin-top: 0`. Con `!important` en
    ambos lados, gana el que va después — no hace falta subir
    especificidad.
    **Corolario:** si un dashboard nuevo (o uno existente) agrega contenido
    en flujo entre los chips y su `ajuste_graf_card_izq_<reporte>` bajo el
    rail compartido, hay que repetir esta excepción para su key — el
    wildcard no lo sabe y el solape se repite. Verificación real (no visual):
    `getBoundingClientRect()` de la fila de KPIs vs. la tarjeta — el `top`
    de la tarjeta debe caer DESPUÉS del `bottom` de lo que esté arriba, con
    margen positivo.

39. **Inspector (`?debug=1`): clic derecho solo FIJABA el tooltip, nunca
    copiaba — y encima el copiado automático puede fallar silencioso.**
    Bug real (2026-08-07): un usuario reportó "clic derecho para copiar no
    copia". El código nunca prometió eso: clic derecho llamaba a
    `__inspectorTogglePin()` (congela el tooltip para poder llegar al botón
    sin que desaparezca), y copiar era SOLO tecla `C` o el botón "Copiar
    para IA" — la pista estaba en el badge inferior ("clic-derecho fija"),
    pero es un texto de 11px fácil de no leer. Fix: clic derecho ahora fija
    Y COPIA en el mismo gesto (`win.__inspectorEjecutarCopia`, extraída del
    listener del botón para que la compartan botón/tecla `C`/clic derecho;
    ver comentario "se reasigna en `win` en cada rerun" un poco más abajo
    en el archivo — mismo motivo que `TogglePin`/`ContextMenuHandler`). El
    botón "Fijar" standalone se dejó pin-only a propósito, para cuando se
    quiere mirar sin copiar todavía.
    Segundo hallazgo, verificado en vivo (no en local: solo se reproduce en
    Streamlit Cloud, que envuelve la app en un iframe propio — el
    `components.html` de `inspector.py` agrega un SEGUNDO nivel anidado):
    `navigator.clipboard.writeText()` puede rechazar con
    `NotAllowedError: Document is not focused`, y el fallback a
    `execCommand('copy')` está sujeto a la misma restricción de foco — así
    que ambas capas de `copiarTexto()` pueden fallar juntas por la misma
    causa. Antes, ese fallo total solo dejaba un mensaje de 3s ("abre
    consola") y el texto en `console.log`. Ahora, si las dos fallan, el
    texto del `<pre>` queda SELECCIONADO (`window.getSelection()` +
    `Range`) para que un `Ctrl+C` físico del usuario funcione siempre — un
    gesto real de teclado no está sujeto a la misma gate de foco/activación
    que una llamada scripteada.
    **Regla:** en cualquier fallback de clipboard dentro de un iframe
    anidado (Streamlit Cloud SIEMPRE mete uno; `components.html` agrega
    otro), no asumir que `execCommand` salva a `writeText` — ambos dependen
    de foco de documento. El único fallback verdaderamente robusto es dejar
    el texto seleccionado y pedir el atajo de teclado real.

40. **`renderizar_aggrid_desktop` es COMPARTIDO por todos los reportes —
    un `if True:` ahí adentro es "para todos", no "para Ajuste", aunque el
    contenido de adentro sea 100% de Ajuste.** Bug real (2026-08-07,
    encontrado auditando la tabla de Inventario Valorizado antes de
    agregarle checkbox de selección): el bloque de agrupación por defecto
    (`_grupos_ini`: Familia/Subfamilia/Producto/Unidad Medida/Area →
    `rowGroup=True`) y `pivotMode=True` forzado — pensados para la cascada
    de **Ajuste de Inventario** — vivían bajo `if True:` en vez de
    `if es_ajuste:`. El comentario que justificaba el `if True:` ("el
    atributo data-active-panel... se marca en todos los reportes") era
    cierto solo para el callback `onToolPanelVisibleChanged` que abre ese
    bloque — pero el resto del código quedó adentro por accidente de cómo
    estaba organizado el `if`, no porque debiera aplicar a todos.
    Consecuencia, verificada en vivo con `getDisplayedRowCount()`/
    `getAllDisplayedColumns()` vía la API expuesta en `onGridReady`
    (`window.__agApi`, ver regla #33): con `pivotMode=True` y CERO
    `rowGroup` reales (las columnas de Ventas/Inventario Valorizado no
    matchean "Familia"/"Producto"/etc. de Ajuste), AG Grid colapsa la
    grilla a solo las columnas con `aggFunc` activo — Ventas quedaba en
    **0 columnas, 0 filas mostradas** (con 18 filas reales en el modelo);
    Inventario Valorizado en **1 sola fila agregada** (con 60 reales).
    Nadie lo había notado porque la mayoría de los reportes se navegan por
    Gráficos, no por "Tabla".
    Fix: separar el `if True:` en 3 partes — `onToolPanelVisibleChanged`
    queda universal (es lo único que el comentario original pedía);
    `_grupos_ini`/`_valores_ini`/`pivotMode=True`/`groupDefaultExpanded=0`
    pasan a `if es_ajuste:`; `suppressFiltersToolPanel` (columnas con chip
    externo) y el header-casing a "Nombre Propio" quedan universales (son
    genuinamente aplicables a cualquier reporte, no son el bug).
    **Regla:** un `if True:`/flag "unificado" dentro de una función
    compartida por reportes es sospechoso por definición — antes de
    ensancharlo, verificar CADA sub-bloque de adentro contra el reporte
    para el que nació, no asumir que el comentario de arriba cubre todo lo
    que sigue. Verificación real: `getDisplayedRowCount()` +
    `getAllDisplayedColumns()`/`isPivotMode()` vía `window.__agApi`, no
    "se ve bien" a ojo — con 0-1 filas visibles el grid renderiza sin
    error ninguno, no hay excepción que lo delate.

41. **Un `.clear()` sobre una función cacheada solo existe si ESA función
    tiene el `@st.cache_data` puesto encima — no alcanza con que el nombre
    suene a "la función de carga".** Bug real (2026-08-07): `9b47294`
    partió `cargar()` en `_cargar_cacheable()` (con `@st.cache_data`) +
    `cargar()` wrapper sin decorar (para no cachear un `None` transitorio,
    ver regla #19). `app.py::_vigilar_refresco` y
    `navegacion.py::_fragment_boton_refresco` seguían llamando
    `cargar.clear(archivo)` — `cargar` ya no tenía `.clear`, un método que
    Streamlit inyecta solo en la función decorada. `AttributeError` en
    producción, pero solo en la rama que corre cuando el refresco
    confirma dato nuevo en R2 (o, en demo, al pulsar "Refrescar"), así que
    no saltó hasta que un usuario lo disparó.
    Fix: `data.py::limpiar_cache(archivo)` — único punto público que sabe
    cuál es la función cacheada real (`_cargar_cacheable`) y la limpia; los
    dos call sites llaman a esa función en vez de tocar `_cargar_cacheable`
    directo.
    **Regla:** tras partir una función cacheada en capa-cacheada +
    wrapper, `grep` por `<nombre_wrapper>.clear(` en todo el repo — cada
    call site quedó apuntando a un objeto sin `.clear`, y no tira error de
    import ni de tipos: revienta recién en la rama que ejecuta ese
    `.clear()`, en producción.

42. **`_graf_heatmap_ajuste` (Mapa de calor de Ajuste) tiene DOS modos —
    Ajuste Valorizado (signado) y Valorizado Total (magnitud) — elegidos
    con un `st.pills` (key `hm_ajuste_modo`) que solo aparece si
    `col_valorizado` existe en el df.** Agregado 2026-08-07 a pedido: el
    heatmap original asumía signo siempre (colorscale divergente
    ERROR→LAVANDA→EXITO, semáforo rojo/verde en la franja TOTAL y en el
    drill). El toggle resuelve una única `col_metrica` (= col_ajuste_val o
    col_valorizado según el modo) ANTES de construir el pivot, y de ahí en
    adelante toda la función lee `col_metrica` — no debería quedar ningún
    uso directo de `col_ajuste_val` después de esa línea (verificar con
    grep si se retoca).
    Lo que cambia con el modo (todo gateado por `_modo_val`):
      · colorscale/zmin/zmax/zmid del trace base — divergente centrada en
        cero vs. `ESCALA_CONTINUA` (la misma escala que ya usan los mapas
        de calor de Compras en `constructor.py`) anclada en cero.
      · título del colorbar y del card ("Ajuste S/"/"Mapa Ajuste
        Valorizado" vs. "Valorizado S/"/"Mapa Valorizado Total").
      · color de fila/columna TOTAL, anillo del top-3 y popup del drill:
        semáforo DANGER_TEXT/CELDA_POS_TEXTO en modo Ajuste,
        ACENTO/ACENTO_TEXTO_OSCURO (neutro) en modo Valorizado — un total
        siempre positivo no es "bueno", es una magnitud, y leerlo en verde
        confundiría las dos ideas.
      · leyenda móvil Faltante/Sobrante: se omite en modo Valorizado (no
        hay negativos que explicar).
      · drill de producto: split Faltantes/Sobrantes (modo Ajuste) vs. un
        solo ranking "Top productos" (modo Valorizado) — en Valorizado
        `_neg` siempre sale vacío, así que mantener el split ahí sería un
        panel muerto.
    El top-3 resaltado (`_top_pos`/`_top_neg`) NO necesitó rama: con
    `col_valorizado` siempre ≥ 0, `_top_neg` da vacío solo y `_top_pos` ya
    es "los 3 valores más altos" — el mismo código sirve para los dos
    modos sin tocarlo.
    Verificado con clicks reales en el preview local (ambos modos,
    desktop y móvil, leyendo `gd.data`/`gd.layout` del `.js-plotly-plot`
    vía JS) y con `st.plotly_chart`/`st.pills` monkeypatcheados para
    ejercitar el drill sin depender de un clic real sobre Plotly (regla
    #12) — `test_graficos.py` sigue pasando con la llamada posicional
    vieja (sin `col_valorizado`), que es justamente el fallback cuando el
    df no trae esa columna.

43. **`st.plotly_chart(..., selection_mode="points")` NO agrega las
    herramientas de caja/lazo al modebar — solo habilita clic en UN punto
    individual.** Bug real (2026-08-07), encontrado recién al probar en el
    navegador (no en `test_graficos.py`, que no ejecuta JS): el strip plot
    de `_graf_distribucion_ajuste` (Distribución) quedó con
    `on_select="rerun", selection_mode="points"` para armar una tabla de
    detalle a partir de una selección — funcionaba para clic simple, pero
    el modebar no mostraba "Box Select" ni "Lasso Select" (se verificó
    leyendo `gd.querySelectorAll('.modebar-btn')` vía JS: solo aparecían
    Zoom/Pan/Autoscale). `selection_mode` acepta una lista — hay que pedir
    explícitamente los modos de arrastre: `selection_mode=["points", "box",
    "lasso"]`. Con eso, el modebar sí ofrece Box/Lasso Select y arrastrar
    selecciona múltiples puntos superpuestos (caso de uso real: clusters
    densos como ALIMENTOS en el strip, donde un clic no alcanza para
    distinguir puntos).
    **Regla:** si el objetivo es dejar seleccionar un GRUPO de puntos
    (no un solo clic), `selection_mode` tiene que incluir `"box"` y/o
    `"lasso"` explícitamente — `"points"` solo no los agrega. Verificar
    con un drag real (o simulando `mousedown`/`mousemove`/`mouseup` sobre
    `gd.querySelector('.nsewdrag')` vía JS si no se puede hacer clic real),
    no alcanza con que `test_graficos.py` pase — ese test solo construye
    la figura, no ejercita el modebar.

44. **`go.Histogram` — selectabilidad NO verificada, mismo riesgo que la
    regla #11 (`go.Heatmap`).** Al agregar click/selección al "Histograma
    de frecuencias" de Ajuste (Distribución, 2026-08-07), no se pudo
    confirmar si `on_select` sobre una traza `go.Histogram` recibe algo
    real o queda silenciosamente vacío como el Heatmap: el panel Browser
    de esa sesión no compone frames, así que `computer{action:
    "screenshot"}` tira timeout y por lo tanto `left_click`/
    `left_click_drag` por coordenada fallan ("requires a prior
    screenshot"). Solo los clics por `ref` de `read_page` funcionan, y las
    barras de un histograma no aparecen como refs individuales en el
    árbol de accesibilidad (son `<path>` de SVG sin rol ARIA) — no hay
    forma de ejercitar un clic o arrastre real sobre una barra concreta
    en ese entorno.
    **Solución: reusar la regla #11 sin modificarla.** Overlay de
    `go.Scatter` invisible (`marker.opacity=0`, `size=20`), un punto por
    bin calculado a mano (`pd.cut` sobre bordes fijos) — el `go.Histogram`
    visible recibe esos mismos bordes vía `xbins=dict(start,end,size)`
    explícito (NO `nbinsx`) para que el overlay coincida pixel a pixel
    con las barras. Cada punto va a **media altura de su propio bin**, no
    al tope: al tope, solo un arrastre que llega hasta arriba lo atrapa;
    a mitad de altura tolera un rango más amplio de arrastre vertical
    (compromiso simple sin apilar varios puntos por bin). El `customdata`
    de cada punto lleva el rango `[lo, hi]` de ESE bin; al seleccionar se
    filtra `df_nz` por ese rango directo en pandas — no depende de que
    Plotly devuelva las filas originales de una traza agregada.
    **Lo que sí se pudo verificar sin browser real:** `test_graficos.py`
    (construcción, ambas ramas) + un script aparte con `st.plotly_chart`
    monkeypatcheado para devolver `{'points': [{'customdata': (lo, hi)}]}`
    (método de la regla #12), que confirmó que el filtro pandas aísla
    exactamente la fila esperada. Lo que queda sin cubrir, igual que en
    la regla #12: que el evento de selección real llegue del navegador al
    clickear/arrastrar sobre el overlay — verificar a mano en Cloud tras
    el deploy antes de asumirlo funcionando.

45. **`inject_maximize_aggrid` — el botón ⛶ desaparecía para siempre al
    cambiar de columnas en caliente (`inyecciones/grid.py`), arreglado
    con un `MutationObserver` en vez de un inserto único.** Encontrado en
    la tabla "Por fecha" de Ajuste (2026-08-07): cambiar el pill
    Corte/Semana/Mes reconfigura `columnDefs` del MISMO grid (sin recargar
    la página) y AG Grid reconstruye su `.ag-side-buttons` interno como
    parte de ese cambio — lo que borra cualquier nodo insertado a mano
    que no sea suyo, incluido el botón ⛶ que `anclarEnRiel` había puesto
    con un `insertBefore` de una sola vez.
    **Por qué no se auto-reparaba solo:** `inject_maximize_aggrid()` es un
    `components.html(...)` de contenido FIJO (no depende de `gran` ni de
    nada que cambie entre reruns) — Streamlit no vuelve a cargar ese
    iframe si el HTML es idéntico al del run anterior, así que el script
    de anclaje nunca se re-ejecuta después del primer montaje. El
    `check()` que sí corrió una vez ya agotó sus reintentos (o encontró
    el riel y paró) mucho antes de que el usuario tocara el pill. Sin el
    grid en sí recargándose, nada vuelve a intentar poner el botón.
    Verificado en vivo (`_test_pivote_aislado.py`, técnica de la regla
    #12): esperando 21+ segundos después de cambiar de pill, el botón
    seguía sin aparecer — no era cuestión de esperar más, estaba
    genuinamente roto.
    **Fix:** `anclarEnRiel` instala (una sola vez, con un flag en el
    propio `fdoc.__maximizeObsInstalado` — no en una variable del
    closure, que se perdería si el script llegara a re-ejecutarse) un
    `MutationObserver` sobre `fdoc.body` que reinserta el botón cada vez
    que detecta que `.ag-side-buttons` existe pero el botón no. Es
    autosuficiente: no importa CUÁNTAS veces AG Grid reconstruya su
    sidebar de ahí en más, ni si el components.html de arranque nunca
    vuelve a correr. Verificado con 3 cambios de pill seguidos
    (Mes→Corte→Semana→Mes): el botón sobrevive los tres, reapareciendo
    en ≤2s cada vez.
    **Por qué el fix es seguro para el resto de la app:** `inject_maximize_aggrid()`
    no cambió de firma (cero args, igual que antes) — los demás callers
    (`tablas/desktop.py`, `tablas/compras.py`, `tablas/movil.py`) no
    necesitan tocarse y se benefician del mismo self-heal automáticamente
    si alguna vez sus columnas también cambiaran en caliente (hoy no lo
    hacen, así que para ellos el observer simplemente queda inerte).
    **Sospecha para la próxima vez:** cualquier otro `inject_*` que haga
    un `insertBefore`/`appendChild` de una sola vez sin observer, en un
    grid cuyas columnas puedan cambiar dentro de la misma sesión (sin
    recargar la página), es candidato al mismo bug — el síntoma es
    "funciona la primera vez, desaparece con la segunda interacción y no
    vuelve nunca".
