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
| `estado_rango.py` | **Dueño único** del eje temporal de la franja superior: rango (`clave_rango`, `asegurar_rango`, `atajos_rango`, `aplicar_atajo`) **y corte** (`clave_corte`, `clave_modo`, `modo_fecha`, `corte_vigente`, `aplicar_corte`, `volver_a_rango`). Nadie escribe esas claves fuera de este módulo — ver reglas #24 y #62. |
| `cortes.py` | Agrupa fechas en **cortes**: las rachas de días de una misma sesión de inventario (salto ≤ `CORTE_MAX_SALTO_DIAS`). Un corte es un CONJUNTO de días, no un intervalo — ver regla #62. Sin dependencias de streamlit ni de `graficos/`, porque lo consumen los dos lados: la franja de `app.py` y `graficos/ajuste/_comun.py` (que lo reexporta con los nombres privados de siempre). |
| `data.py` | Carga de datos: DuckDB + httpfs leyendo parquets de R2 (secrets). Sistema de refresco bajo demanda vía R2. |
| `tablas/` | **Paquete de tablas AgGrid** (refactor 2026-08-01; antes un `tablas.py` de 2.028 líneas). `__init__.py` re-exporta la API pública. `_css.py` (CSS de grid y paneles), `_config.py` (estilos de celda/fila, sidebar, totales), `desktop.py` (`renderizar_aggrid_desktop`), `movil.py` (`renderizar_aggrid_movil`), `compras.py` (`renderizar_aggrid_compras`), `ajuste_pivote.py` (`renderizar_aggrid_pivote_ajuste`, tabla "Por fecha" de Ajuste de Inventario — ver regla #25). `renderizar_tabla_compras` se borró el 2026-08-08 (llevaba desde 2026-08-01 sin llamadores). |
| `graficos/` | **Paquete de dashboards de gráficos** (refactor Fase 2, 2026-07-25). `__init__.py` es solo el dispatcher: dict `_DASHBOARDS = {reporte: render_fn}` (no cadena de if/elif), más `renderizar_graficos_reporte` (entry point) y `tiene_dashboard(reporte)` (para que `app.py` no enumere reportes ni importe `_DASHBOARDS`; ver regla #50). `render_vista_pills` (pestañas Gráficos/Tabla sueltas en la franja) se ELIMINÓ 2026-08-04: ver regla #18. Cada dashboard vive en su archivo: `base.py` (infraestructura compartida: cards nativos, motor genérico, resolución de columnas, helpers de layout), **`ajuste/` es un paquete** (refactor 2026-08-08; antes un `ajuste.py` de 2.607 líneas — el fichero con MÁS churn del repo, 80 de los últimos 200 commits): una vista por módulo — `_comun.py` (layout del rail, fechas de corte, periodos), `_evolucion.py`, `_pivote.py`, `_cascada.py`, `_panel_analisis.py`, `_heatmap.py`, `_distribucion.py` — y `__init__.py` con la config del rail, `categoria_rango_ajuste` y el entry point. Ojo: la **cascada NO es un gráfico Plotly** sino una tabla de filas — `st.columns` por familia + HTML en `st.markdown`, con una columna de barras flotantes que encadenan la cascada; ver reglas #8 y #10, `ventas.py` (`ventas_resumen.py` aporta su vista "Resumen ejecutivo" — KPIs + venta diaria coloreada por tendencia + ticket promedio + top platos; nació con un candlestick, ver por qué se dio de baja en la regla #85) y `ventas_comparativo.py` (vista "Año Pasado": barras agrupadas Actual vs Año Pasado en día/semana/mes, con toggle de alineación fecha-calendario / día-de-semana en día, feriados y findes marcados, recorte del período en curso, modo "Descomposición" (%Δ venta/pax/ticket en un solo eje) y drill por clic al ranking de platos del período — ver reglas #86, #87 y #88), `inventario.py` (v2), `salidas.py` (evolución con granularidad Día/Semana/Mes/Año + composición por subalmacén/tipo de descargo), `constructor.py` (Power BI, usado por Compras). **`recetas_comun.py`** (2026-08-13) tiene la ÚNICA copia de los 5 gráficos que comparten Receta Base y Receta Venta (Sankey/Composición/Ranking/Ítems clave/Panorama de compras) más `_activo()` y `_chip_fuente()` — ver regla #97. `recetabase.py` y `recetaventa.py` son capas finas sobre ese módulo: resuelven columnas reales + llaman a lo compartido. `requerimientos.py` (2026-08-13, dashboard nuevo: evolución + sub almacén + estado, mismo layout que `salidas.py`) y **`movimientos_comun.py`** (chip Requerimiento/Salidas + vista "Comparativo" que cruza los dos parquets — ver regla #98) comparten nav ("Movimientos") con `salidas.py`. `legacy.py` (Inventario v1) se borró el 2026-08-08: 421 líneas sin un solo import. **`compras/` es a su vez un paquete** (refactor 2026-08-01; antes un `compras.py` de 2.835 líneas): un drill por archivo — `_comun.py` (helpers, incluye `_periodo_serie` para granularidad temporal — reusar desde ahí, no duplicar), `proveedor.py`, `familia.py`, `cantidad.py`, `evolucion.py`, `volatilidad.py` (ranking de insumos por volatilidad de precio → candlestick semanal → compras de la semana clickeada; ver regla #74) — y `__init__.py` con la config del rail y `renderizar_graficos_compras`. El drill de Proveedor se siguió partiendo el 2026-08-08 (era una función de 1.577 líneas): `_css_proveedor.py` (sus 527 líneas de CSS, que NO van a `estilos/` a propósito — ver su docstring), `_etiquetas_proveedor.py` (texto de las barras: `fmt_k`, `abrev_nombre`, `etiqueta_serie`, `sufijo_granularidad`; puras y con asserts de valor en `test_graficos.py`) y `_documentos_proveedor.py` (`tabla_documentos`, la AgGrid pivote del pie). Quedó en 791 líneas; el resto NO se siguió cortando a propósito — ver regla #55. Cuando un dashboard crezca así, partirlo del mismo modo. **Agregar un dashboard nuevo = crear `graficos/<nombre>.py` + 1 línea en `_DASHBOARDS`.** |
| `estilos/` | **Paquete del CSS global** (refactor 2026-08-01; antes un `estilos.py` de 1.700 líneas). `__init__.py` mantiene la API pública (`TAM_FUENTE`, `get_css`, `inject_css`) y concatena las secciones. Una sección por módulo, con prefijo numérico que marca el orden: `_00_base`, `_20_compras_rail`, `_30_filtros`, `_40_ajuste_franja`, `_50_fecha`, `_60_calendario`, `_70_chrome`, `_80_cards`, `_90_franja_inferior`, `_99_movil`. (`_10_vista` existió hasta el 2026-08-08: estilaba el selector Gráficos/Tabla y quedó 100% huérfano al borrarse ese widget — ver regla #49.) **El orden de `_SECCIONES` es parte del comportamiento**: hay `!important` en ambos lados de varios conflictos, así que gana la regla que va DESPUÉS — por eso `_99_movil` cierra. |
| `navegacion.py` | Rail lateral, topbar y CSS por sección (`_CSS_AJUSTE`). Botón de refresco aislado en su propio `@st.fragment`. |
| `inyecciones/` | **Paquete de JS/HTML inyectado** (refactor 2026-08-01; antes un `inyecciones.py` de 1.813 líneas). `_fragmentos.py` (CSS/JS compartido), `grid.py` (salud, altura, maximizar, panel de columnas), `paginacion.py`, `inspector.py` (herramienta de desarrollo), `diseno.py` (modo de diseño visual, `?debug=1&diseno=1` — lee el pin de `inspector.py`, ver regla #46), `varios.py` (overlay de errores, fullscreen, footer, calendario). Los dos blobs de JS grandes viven aparte desde el 2026-08-08: `_inspector_js.py` (1.381 líneas) y `_diseno_js.py` (794). Sus funciones quedaron en 34 y 5 líneas. **Si tocas esos módulos, lee antes la regla #56** — extraerlos rompió el inspector de una forma que ni `ruff` ni los tests pueden ver. Ninguna función depende de otra (la excepción de solo-lectura de `diseno.py` está documentada en la regla #46): las únicas dependencias internas apuntan a las constantes de `_fragmentos.py`. |
| `asistente.py` | **Asistente IA del reporte activo** (Groq, `gpt-oss-120b`): system prompt, bucle de tool calling y la UI del popover (ícono en la franja + panel de chat). Su CSS vive en `estilos/_85_asistente.py`, NO acá — ver regla #59. Accesorio por diseño: `app.py` lo envuelve en try/except para que un fallo suyo no tumbe el reporte. |
| `asistente_datos.py` | **Capa de datos del asistente, sin LLM ni UI**: esquema para el prompt (`esquema_para_prompt`, incluye los VALORES de las categóricas), ejecución de SQL de solo lectura sobre el df en memoria con DuckDB (`ejecutar_sql`, con blocklist + guarda de columnas con espacios sin comillas) y las definiciones de herramientas. Es Python puro: se testea entero sin API key ni navegador (`test_asistente_datos.py`). Ver regla #69. |
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
| `columnas_iniciales` | list | Columnas que arrancan VISIBLES en la AgGrid de escritorio; el resto se activa desde el panel lateral "Columnas". Ausente = se muestran todas las sugeridas. Se resuelven con `buscar_columna`, así que no hace falta clavar el nombre exacto del parquet. |
| `carga_por_rango` | str | Columna de fecha por la que DuckDB filtra ANTES de materializar el DataFrame (para parquets grandes: nunca se bajan las 100k+ filas). Hoy solo Ventas. |
| `derivar_periodo_pivote` | bool | Crea las columnas `"<fecha> (Mes)"` y `"<fecha> (Día)"` como **string** para el Modo pivote de AG Grid, que pivotea por el valor EXACTO de la columna: con la fecha cruda (que trae hora al minuto) saldría una columna por minuto. Solo lo necesitan los reportes cuya fecha lleva hora. |
| `grupo_nav` | str | Entradas de `REPORTES` que comparten este valor se dibujan como **UN solo botón** en el rail (`navegacion.py::inject_navegacion`), navegando al último miembro visitado (session_state `_ultimo_<grupo>`). Dos grupos hoy: Receta Base/Venta (`"Recetas"`, ver regla #97) y Requerimientos/Salidas (`"Movimientos"`, ver regla #98). Sigue habiendo DOS entradas reales en `REPORTES` por grupo (cada una con su `archivo`/cfg propios); el grupo es puramente de presentación. El ícono del botón agrupado sale del PRIMER miembro del grupo en el orden del dict — por eso conviene que los dos miembros compartan el mismo `icono` (evita que la elección dependa del orden). |

> `columnas_iniciales` y `derivar_periodo_pivote` vivían como
> `if reporte == "..."` dentro de `app.py` hasta el 2026-08-08. Son
> configuración de DATOS, no de despacho — su sitio es este dict. Tras
> moverlas, en `app.py` quedan solo **dos** comparaciones por nombre de
> reporte: `Requerimientos` (rama de despacho real, ver regla #50) y
> `es_ajuste`, que NO es config de columnas sino el discriminante que
> `clave_rango()` necesita para que el rail de Ajuste recuerde un rango por
> categoría — vive en `estado_rango.py`, el dueño único del rango.

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

    **2026-08-09, 5ta vuelta — de tarjeta invisible a BARRA con cara
    propia.** Reportado con captura: "no la veo muy bien". Dos causas, las
    dos reales: (a) blanco al 62% sobre un canvas blanco no se distingue —
    el `backdrop-filter` solo se nota cuando algo pasa por debajo; (b) la
    fecha estaba anclada a la izquierda y los chips CENTRADOS en el ancho
    útil, así que entre ambos quedaba un hueco muerto que crece con el
    monitor. Cambios, todos acoplados entre sí:
    - `::before`: `left:90px` / `right:0` (deja de alinearse con la tarjeta
      del gráfico — los `170/163` medidos en la 3ra vuelta siguen
      documentados en el módulo por si se quiere volver), `border-radius:0`,
      fondo `color-mix(in srgb, var(--accent-tint) 88%, transparent)`,
      `border-bottom: 2px var(--border-lavender)` y ningún borde en los
      otros 3 lados. No choca con el rail derecho: ese arranca en `top:60px`.
    - Alto desktop `34px → 40px → 46px`, y `top:3px → 8px` en
      `fecha_ajuste_pill` y `chips_ajuste_tabla` (el par acoplado de la
      vuelta anterior, movido junto). Los 40px/`top:6px` duraron una pasada:
      se veía "metido a la fuerza" contra la línea inferior porque el aire
      quedaba 6px arriba y **4px abajo**. El error fue calcular el top como
      `(alto − control) / 2` olvidando que el `::before` es `border-box`,
      así que el `border-bottom:2px` descuenta alto por dentro.
      **La fórmula es `top = (alto − borde_inferior − alto_del_control) / 2`**
      — con 46px y control de 28px da los 8px simétricos que hay hoy
      (verificado en el preview: 8 arriba, 8 abajo).
    - **Subir la barra obligó a bajar la tarjeta Y el rail derecho, juntos.**
      Con la barra en 46px la primera tarjeta quedaba en y=57: 11px de aire
      (contra los ~23px de la barra original de 34px) y, peor, **3px más
      arriba que el rail derecho**, que arranca en un `top` propio — se veía
      el escalón en la esquina superior derecha. Ahora los tres números de
      `_20_compras_rail.py` van coordinados para dar el mismo y=66:
      `compras_tabs_row { top: 66px; height: calc(100vh - 66px) }`,
      `compras_prov_drill_wrap { margin-top: -51px }` y
      `ajuste_graf_card_izq_* { margin-top: -56px }` (antes 60/-60/-65).
      Verificado en Ajuste y Compras: tarjeta y rail en y=66, 20px de aire
      bajo la barra. **Regla: si vuelve a cambiar el alto de la barra, no
      alcanza con recalcular el `top` de los controles — hay que mover
      también la tarjeta y el rail, o quedan en líneas distintas.** El
      `margin-top:0` de Salidas es una excepción aparte (tiene una fila de
      KPIs en flujo encima, ver regla #38) y no entra en este ajuste.
    - **Los chips dejaron de estar centrados**: `left:391px` fijo =
      `175px` (left del pill) + `210px` (ancho del pill) + `6px`. Para que
      ese número sea estable el pill tomó **ancho fijo** (`width:210px`, ya
      no `fit-content`) y `app.py::_fmt_rango_es` pasó a mes abreviado con
      el año una sola vez cuando coincide ("1 ago – 5 ago 2026"). Medido:
      el peor caso del formato nuevo ("30 sep 2025 – 31 dic 2026") ocupa
      144px de los 159px útiles del pill, así que nunca hay ellipsis.
      **Son tres piezas de un mismo cambio** — left de los chips, ancho del
      pill y formato del label. Tocar una sola desalinea la barra.
    No se puede resolver con `flex` en vez de coordenadas fijas: la fecha
    vive en `fila_ajuste_top` (app.py) y los chips los renderiza el módulo
    de cada dashboard (6 sitios distintos, todos con la key
    `chips_ajuste_tabla`, ver regla #16), así que no hay un ancestro común
    donde ponerlos en la misma fila. Agrupar de verdad exigiría pasar un
    contenedor-slot creado en la franja a los 6 renderers.
    Verificado en el preview local a 1360/920/375px en Ajuste, Ventas y
    Compras: el caso más apretado es Compras a 920px (2 chips con
    `min-width:230px`), que termina en x=814 contra el rail en x=821 — sin
    scroll horizontal en ningún caso.

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

    **2026-08-07, más tarde — las etiquetas de Corte quedaban cortadas,
    dos vueltas hasta calibrar bien el ancho** (`tablas/ajuste_pivote.py::
    _col_periodo`/`_ancho_header_periodo`). El `minWidth=92` fijo de las
    columnas de periodo estaba pensado para "ene"/"S01" (3 caracteres);
    una etiqueta de Corte como "30 jul - 2 ago" no entraba junto con los
    iconos de orden/filtro/menú de la cabecera y se veía como "1..." — el
    dato de la celda estaba completo, solo la cabecera lo escondía. Se
    agregó de paso `headerTooltip` con el mismo texto.
    **1ra vuelta (insuficiente):** `_ancho_header_periodo` calculaba el
    mínimo a ojo (`base=58 + 7px × carácter`), probado solo con 5-6
    columnas en una ventana ancha — no se veía cortado ahí porque
    `sizeColumnsToFit()` tenía de sobra para estirar todo más allá del
    mínimo. Con datos reales (20+ columnas de Corte, la ventana ya no
    alcanza para estirar de más) el mínimo SÍ se usaba literal, y 9 de
    10 cabeceras salían cortadas — reportado por captura, reproducido en
    `_test_pivote_aislado.py` con muchas columnas antes de tocar nada.
    **2da vuelta (medida, no estimada):** se leyó `scrollWidth` del label
    contra el ancho real de columna en varias etiquetas — los tres
    iconos de cabecera comen **72px fijos** (no 58), y el texto ronda
    **6.3px/carácter** (no muy lejos de la primera estimación, el error
    grande estaba en el chrome de iconos). `base=85`/`por_caracter=7.5`
    deja margen sobre esa medición. Verificado de nuevo con 24 columnas
    (8 meses × 3 cortes) y scroll hasta la última: 0 cabeceras cortadas.
    **Lección:** un ancho "que no se corta" verificado con pocas columnas
    en una ventana ancha no prueba nada — `sizeColumnsToFit()` disimula
    un mínimo insuficiente estirando de más cuando sobra espacio. Solo se
    nota apretado con las columnas reales (muchas, la ventana no da para
    estirar). Medir contra un caso con volumen realista, no el más fácil.

    **2026-08-07, otra vuelta — subtotal por periodo en filas de grupo
    (pedido real: "puedo tener subtotales").** Con `groupDisplayType:
    "groupRows"` las filas de Familia/Subfamilia eran de ANCHO COMPLETO
    (`agGroupRowRenderer`) — solo mostraban nombre + cantidad + el total
    de la fila entera, ninguna columna de periodo se pintaba para ellas
    (quedaban en blanco). Sacar `groupDisplayType` (default =
    "singleColumn") hace que AG Grid pinte cada columna de periodo
    TAMBIÉN para las filas de grupo, con el `aggFunc` propio de esa
    columna sumando los hijos — el mismo cellRenderer compacto que ya
    usan las filas hoja, sin código nuevo del lado de los valores.
    **Lo que sí hubo que mover:** `groupRowRendererParams.innerRenderer`
    (que pinta "ALIMENTOS (n) · S/ total") solo aplica en modo
    "groupRows"; en "singleColumn" el lugar correcto es
    `autoGroupColumnDef.cellRendererParams.innerRenderer` — el espejo
    exacto de la regla ya documentada arriba, para el modo contrario.
    **Efecto colateral no obvio:** al pasar a "singleColumn", el ícono de
    expandir/colapsar vuelve a ser el `agGroupCellRenderer` NATIVO (no el
    renderer de ancho completo), y ESE tiene su PROPIO "(n)" por defecto
    — sin `"suppressCount": true` junto al `innerRenderer`, el conteo
    salía duplicado ("ALIMENTOS (3) · S/ 215**(3)**"). Verificado en vivo
    con `_test_pivote_aislado.py` (apareció el duplicado, se sacó con
    `suppressCount`, se confirmó limpio).
    **De yapa:** este cambio de modo también permitió sacar la columna
    "Producto" separada que existía como workaround (regla de más
    arriba, "las filas hoja NO terminaban pintando el auto-group column
    en 'groupRows'") — en "singleColumn" `autoGroupColumnDef.field`
    SÍ funciona para filas hoja, así que Producto volvió a mostrarse
    dentro del mismo árbol de una sola columna (el diseño original,
    antes del workaround), un poco más simple.

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

    **Intento fallido que NO hay que repetir (2026-08-12):** para "subir un
    poco el toggle de Por día" se tocó `margin-top` de
    `.st-key-ajuste_graf_card_izq_ventas` (de -56px a -60px). Funcionó
    ópticamente, pero esa tarjeta envuelve las **10 vistas del rail de
    Ventas**, así que movió Resumen, Año Pasado, Matriz, Tabla y el resto —
    no el toggle. Revertido. La solución correcta está en la regla #90.

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

46. **`inject_diseno_visual` (`inyecciones/diseno.py`) lee estado de
    `inspector.py` sin que `inspector.py` sepa que existe — y
    `requestAnimationFrame` puede no dispararse NUNCA.** Dos hallazgos del
    modo de diseño visual (`?debug=1&diseno=1`), fase A (esqueleto):
    - **Acoplamiento de solo lectura entre dos `inject_*`.** `diseno.py`
      lee `win.__inspectorPinned`/`win.__inspectorUltimo` (que
      `inspector.py` expone en `window.parent` para sobrevivir el remount
      del iframe) para saber qué elemento está fijado, sin que
      `inspector.py` importe ni llame nada de `diseno.py`. Es la regla
      general del §4 aplicada: dos `inject_*` comparten estado, así que la
      interacción se documenta en ambos módulos (ver docstring de
      `inyecciones/__init__.py` y de `diseno.py`). Si `inspector.py` alguna
      vez renombra esas variables o cambia qué guarda `elemento`/`key` en
      `__inspectorUltimo`, `diseno.py` se rompe en silencio — revisar acá
      primero si el modo diseño deja de reaccionar al pin.
    - **`requestAnimationFrame` no es confiable como ÚNICO mecanismo de
      sync.** Verificado en vivo (Browser pane del editor, agente de
      planning): con la pestaña sin composición activa de frames, una
      sonda `requestAnimationFrame` instalada a mano dio **0 callbacks en
      2 segundos**. Un primer diseño de `diseno.py` que solo reprogramaba
      el tracking de la manija vía `requestAnimationFrame` dejaba el
      overlay CONGELADO en la posición vieja tras un rerun real (la
      tarjeta se movía/cambiaba de alto al expandir una fila, el overlay
      se quedaba clavado donde estaba) — sin ningún error en consola,
      porque no es una excepción, es un callback que simplemente nunca se
      vuelve a agendar en ese contexto. Arreglo: el `setInterval` de
      ~150ms es la fuente de verdad del tracking (llama a la misma
      función `sync()` que hace el resize del overlay), no solo un
      "¿sigue vivo el pin?". En la práctica el arrastre de manijas (fase
      A.2) tampoco necesitó `requestAnimationFrame`: aplicar el cambio
      directo en cada evento `mousemove` ya se ve fluido y es más simple
      — `requestAnimationFrame` queda descartado para este módulo, no
      solo "reservado".

47. **Un `width`/`height` con `!important` no alcanza para redimensionar
    un item flex — hacen falta 3 propiedades más.** Encontrado
    implementando las manijas de resize del modo diseño
    (`inyecciones/diseno.py`, fase A.2) contra `st-key-chartcard_cascada`
    (un `stVerticalBlock` real). Dos bloqueos DISTINTOS, ninguno se ve en
    consola ni se resuelve agregando `!important` a la MISMA propiedad
    que ya lo tiene:
    - **Ancho:** el contenedor trae `max-width: 100%` (default de varios
      wrappers de Streamlit/`estilos/`). `max-width` es una propiedad
      DIFERENTE de `width` — clampea el resultado después de que el
      cascade ya resolvió `width`, así que un `width:692px !important`
      se queda clavado en el `max-width` resuelto (632px en este caso)
      sin importar la prioridad de `width`.
    - **Alto:** el padre es `display:flex; flex-direction:column` y el
      elemento trae `flex: 1 1 0%` (flex-basis 0%). En el eje PRINCIPAL
      del flex (acá vertical, por la columna), `flex-basis` reemplaza a
      `height` en el algoritmo de layout — no es que pierda la cascada,
      es que el layout de flex directamente no consulta `height` cuando
      `flex-basis` no es `auto`.
    - **Diagnóstico que sirvió:** comparar `el.style.getPropertyPriority('width')`
      (confirma que el `!important` SÍ está en el atributo inline) contra
      `getComputedStyle(el).width`/`el.offsetWidth` (el tamaño realmente
      usado) — si difieren pese a la prioridad correcta, el problema no
      es de cascada, es una propiedad hermana (`max-width`/`max-height`)
      o el algoritmo de layout (`flex-basis`) ganándole por fuera del
      cascade.
    - **Arreglo:** antes de tocar `width`/`height`, neutralizar las tres
      con `!important` también: `flex: none`, `max-width: none`,
      `max-height: none`. Con eso, `width`/`height` sí controlan el
      tamaño final. Sospecha para la próxima vez: cualquier control de
      diseño que cambie tamaño/posición sobre un contenedor de Streamlit
      (`stVerticalBlock`/`stColumn`/`stHorizontalBlock`, todos flex por
      default) puede necesitar el mismo trío — no asumir que alcanza con
      la propiedad que el usuario está tocando.

48. **`st.pills`/`segmented_control`/`st.popover`/`st.button` guardan la key
    en un WRAPPER de layout — lo visualmente real (borde, relleno,
    tipografía, color) vive en el/los `<button>` de adentro, que no tienen
    key propia.** Encontrado extendiendo el modo diseño
    (`inyecciones/diseno.py`) contra `st.pills("Vista", ["Agrupado",
    "Apilado"], key="compras_cant_vista")` y contra el popover "Excluir
    productos" (`ajcas_excl_wrap`, `graficos/ajuste.py`). Pinear cualquiera
    de los dos pinea el WRAPPER — un control que solo toca `elemento` no
    tiene efecto visible (el wrapper es invisible) o solo agrega espacio
    vacío alrededor de un botón que sigue viéndose igual.
    - **Criterio de redirección — por ÁREA, no por "hay un botón adentro":**
      una tarjeta grande (`chartcard_cascada`) tiene botones de expandir ▸
      salpicados por sus filas; redirigir ahí por la sola presencia de un
      `<button>` pintaría las flechitas al cambiar el fondo de la tarjeta.
      Solo redirige cuando el/los botones ocupan >=60% del ancho (suma, se
      reparten la fila) o del alto (máximo, comparten la fila) del propio
      elemento pineado — es decir, cuando el elemento ES básicamente el
      botón, no un contenedor mayor que de casualidad tiene alguno adentro.
    - **Padding/tamaño de letra sobre el botón redirigido no crecían nada
      por sí solos:** los botones de Streamlit traen `box-sizing:border-box`
      con `width`/`height` explícitos (`getComputedStyle` los mostraba en
      píxeles concretos, no `auto`) — el padding se comía espacio de
      adentro en vez de agrandar la caja hacia afuera. Liberar a
      `width:auto; height:auto` (con `!important`) recién entonces deja que
      la caja responda al padding/tamaño de letra.
    - **El hallazgo más caro de diagnosticar — `transition: all 0.15s` del
      propio botón peleaba con el `setInterval` de 150ms del modo diseño:**
      un `!important` inline con el valor y la prioridad correctos
      (confirmado leyendo `style.getPropertyPriority` directo, no solo el
      texto de `cssText`) SEGUÍA sin reflejarse en `getComputedStyle` —
      border-radius clavado en `999px`, background-color clavado en blanco,
      padding clavado en el valor original. Se descartaron uno por uno:
      nodo reemplazado (marca custom en el elemento, sigue el mismo tras
      reruns y esperas), Shadow DOM (no hay), CSS `@layer` (no hay ninguna
      en las hojas de estilo). La causa real: la duración de la transición
      del botón (0.15s) coincide casi exacto con el intervalo de reaplicado
      defensivo (150ms) — cada tick REINICIA la transición antes de que
      termine de llegar al valor nuevo, así que el navegador queda
      perpetuamente a mitad de camino, pegado cerca del valor ORIGINAL.
      Nada de esto tira error: se ve como "mi cambio no hizo nada".
      **Arreglo:** `transition: none !important` sobre el/los elementos
      destino ANTES de tocar cualquier propiedad animable — una sola vez
      por key (`registro.transicionNeutralizada`), reaplicado en cada tick
      igual que el resto. Sospecha para la próxima vez: si un control de
      diseño no tiene efecto visible pese a que el inline `!important` está
      confirmado presente con el valor y la prioridad correctos, revisar
      `getComputedStyle(el).transitionProperty/-Duration` antes de seguir
      buscando por el lado de la cascada — el problema puede ser de tiempo
      (reaplicado vs. duración de transición), no de especificidad.

49. **Borrar código Python deja CSS huérfano, y nada en el `.py` lo
    señala.** Al eliminar `_selector_vista()` de `app.py` (widget muerto,
    lo había reemplazado el rail) quedaron sin dueño **el módulo
    `estilos/_10_vista.py` entero** (100 líneas), bloques en
    `_40_ajuste_franja` y `_99_movil`, y la clase `.titulo-ajuste-reporte`.
    El acoplamiento key→CSS que CLAUDE.md advierte para el caso "una regla
    del contenedor captura widgets nuevos" funciona igual al revés: el CSS
    sobrevive al widget que lo justificaba, invisible, porque un selector
    que no matchea nada no da error ni warning.
    **Regla:** al borrar un `st.container(key=...)`, un widget con key, o
    una clase que emitía un `st.markdown`, hacer `grep` de ese nombre en
    `estilos/` e `inyecciones/` en el mismo commit.
    **Cómo confirmarlo sin adivinar** — levantar la app y contar nodos:
    ```js
    document.querySelectorAll('[class*="st-key-<key>"]').length   // 0 = huérfano
    ```
    Ojo con el falso positivo: en modo demo hay elementos que no se pintan
    por falta de datos, no por estar muertos (`.ultima-actualizacion` da 0
    en local porque sin secrets R2 no hay fecha, pero en producción sí se
    emite). Antes de borrar, confirmar que NINGÚN `.py` lo emite.

50. **Un `inject_*` cuyo elemento ya no existe NO es código muerto inerte
    — cuesta.** `inject_alinear_cabecera_ajuste` buscaba
    `.titulo-ajuste-reporte` y `.st-key-ajuste_tabs_top`; los dos habían
    dejado de emitirse, así que su `alinear()` devolvía `false` siempre.
    Pero el patrón "medir con reintentos" seguía corriendo: **40 iteraciones
    cada 400 ms (16 s de polling) dentro de un `components.html`, en CADA
    render de tabla desktop.** No fallaba, no logueaba, solo gastaba.
    **Regla:** las inyecciones con reintentos (`inject_dynamic_grid_height`,
    `inject_maximize_aggrid`, y cualquiera que copie el patrón) deben
    revisarse cuando se toca el DOM que buscan. Si el selector ya no
    existe, la inyección entera sale — no basta con que "no rompa nada".

51. **`var(--x, #hex)` es un `#hex` suelto disfrazado.** El proyecto
    prohíbe hexes fuera de `tema.py`/`:root`, pero el fallback de `var()`
    se colaba: había **28 fallbacks duplicando la paleta**, y 4 ya habían
    DERIVADO del valor real (`var(--accent, #7f77dd)` contra el `#6c5ce7`
    de verdad — otro morado; `var(--cab-offset-contenido, 128px)` contra
    58px). Ninguno se pintaba, porque `_00_base` va primero en
    `_SECCIONES` y todo se inyecta en el MISMO `<style>`: el fallback de
    `var()` solo entra si la variable NO está definida, no si va después.
    Es decir, eran valores muertos que mienten sobre cuál es el color real.
    Peor caso: `--surface-1` / `--surface-2` se usaban **sin haberse
    definido nunca**, así que ahí el fallback sí era lo que se renderizaba
    — un segundo vocabulario para `--bg-primary` / `--bg-card`.
    **Regla:** dentro de la app, `var(--x)` a secas. El fallback se
    justifica solo cuando la variable la setea Python inline por elemento
    y puede faltar de verdad (`--cp-prov-count`, `--periodo-selec` en
    `proveedor.py`, donde `""` es el "sin valor" intencional).
    **Chequeo:** que toda `var(--x)` del código exista en el `:root` de
    `_00_base` — si falta, la propiedad queda inválida y la regla se cae
    en silencio (le pasaba a `background: var(--background-color)` en
    `proveedor.py`, que es un nombre del tema de Streamlit, no nuestro).

52. **Un flag booleano fijado a `True` a mano se vuelve invisible en un
    mes.** Cuando un cambio de diseño unifica reportes, la tentación es
    dejar el flag y ponerlo en `True`. Al momento de la limpieza del
    2026-08-08 había: `envolver_cabeceras`, `quitar_fondos` y
    `es_inventario` en `renderizar_aggrid_desktop`; `mostrar_pivot` y
    `es_ajuste` como parámetros de `_config_sidebar` (los dos llamadores
    pasaban True); y **dos `if True:`** — uno envolviendo 119 líneas de
    `app.py`, otro el panel de pivote en `_config.py`. Cuesta caro por
    tres motivos: (a) las ramas `else` se pudren sin que nadie las
    ejecute — `_estilo_fila` tenía una rama inalcanzable *por partida
    doble*; (b) arrastran dependencias muertas — `max_valorizado` se
    calculaba solo para una barra de gradiente que ya no se usaba; (c)
    `es_inventario` llegó a significar "true para todos", NO "es el
    reporte Inventario Valorizado", y hubo que agregar un comentario para
    aclarar la confusión que el propio flag creaba.
    **Regla:** si un flag queda en `True`, colapsarlo en el mismo commit.
    Git conserva la versión parametrizada. Si algún día vuelve a haber más
    de un caso, el discriminante correcto suele ser `reporte`, no un
    booleano suelto.

53. **`ruff --fix` sobre F401 puede romper re-exports deliberados.** El
    proyecto usa módulos que importan un símbolo SOLO para reexponerlo
    (`graficos/compras/_comun.py` importa `_es_movil` de `graficos.base`
    porque la función se mudó y `proveedor.py`/`compras/__init__.py` la
    siguen importando de ahí). Para ruff eso es un import sin usar, y el
    fix automático lo borra rompiendo a sus consumidores — sin error de
    sintaxis, sin fallo de test: revienta al abrir ese drill.
    **Regla:** todo re-export lleva `# noqa: F401` **con un comentario que
    diga que es un re-export y quién lo consume.** Los `__init__.py` ya
    están cubiertos por `per-file-ignores` en `ruff.toml`; los demás
    módulos no.
    **Antes de un `--fix` masivo,** verificar que cada nombre marcado no
    aparezca en el resto de su archivo (un template `.format()`, un
    docstring, o justamente un re-export). Es un script de 20 líneas y en
    esta limpieza cazó el único caso que habría roto la app, entre 108.

54. **Un callback inyectado necesita UNA firma, no una por llamador.**
    `tabla_cb` (el callback con el que `app.py` le presta la tabla AgGrid
    a los dashboards) tenía DOS aridades: Ajuste y Receta Venta lo
    llamaban `tabla_cb()`, el resto `tabla_cb(d)`. El único sitio donde
    constaba cuál tocaba era un docstring, así que un dashboard nuevo que
    eligiera mal fallaba con `TypeError` **solo en producción y solo al
    hacer clic en "Tabla"** — el peor momento posible. Hoy la firma es
    `tabla_cb(d)` para todos.
    Lo mismo valía para el dispatcher: tenía un `if reporte in ("Ajuste de
    Inventario", "Ventas", ...)` que había que mantener sincronizado a
    mano con `_DASHBOARDS`. Se eliminó haciendo que TODOS los dashboards
    acepten `tabla_cb` (Compras lo ignora, y lo dice en su docstring).
    **Regla:** contratos así se protegen con un test, no con un comentario.
    `test_graficos.py::_pruebas_contratos` recorre `_DASHBOARDS` y verifica
    firma, aridad de la llamada y que el dispatcher no haya vuelto a meter
    una lista de reportes. Cuesta 40 líneas y se ejecuta en un segundo.

55. **Al partir una función gigante, el orden lo decide el ACOPLAMIENTO,
    no el tamaño.** `_compras_proveedor_drill` tenía 1.577 líneas y se
    bajó a 791 en tres cortes (2026-08-08), todos verificables por
    separado, ninguno tocando el núcleo:

    | Corte | Qué salió | Por qué era seguro |
    |---|---|---|
    | `_css_proveedor.py` | 527 líneas de CSS estático | Texto puro. Se comparó **byte a byte** contra git. |
    | `_etiquetas_proveedor.py` | `fmt_k`, `abrev_nombre`, `etiqueta_serie`, `sufijo_granularidad` | Puras o casi: 2 valores de closure pasaron a parámetros. |
    | `_documentos_proveedor.py` | `tabla_documentos` (AgGrid pivote del pie) | Solo 6 valores del scope, y su estado (`cp_docs_*`) no lo lee nadie más. |

    **Lo que queda NO se sigue cortando sin una decisión previa.** Las
    piezas restantes (controles, cálculo de período, ventana de
    paginación, procesar clic, gráfico principal, paneles A/B) comparten
    ~50 locales y accesos a `session_state`. Extraer cualquiera obliga a
    elegir cómo se pasa ese estado — muchos parámetros, un dataclass de
    contexto, o que cada pieza lea `session_state` directo — y esa
    elección cambia el resultado. Es una decisión de diseño, no un
    movimiento mecánico: no la tome quien solo venía a "reducir líneas".

    **Regla general:** en una función así, buscar primero (a) los bloques
    de texto/CSS/JS estático, (b) las funciones anidadas puras, y (c) el
    bloque de UI cuyo estado en `session_state` sea privado. Esos tres
    salen sin decidir nada. El resto ya no es refactor de mover-código.

    **Corolario — las funciones anidadas no se pueden probar.** El valor
    real del corte (b) no fue quitar 100 líneas: fue que `etiqueta_serie`
    y compañía pasaron a tener 19 asserts de valor. Mientras vivían
    dentro del drill, no había forma de llamarlas desde un test. Si una
    función anidada tiene lógica que valga la pena verificar, ya es razón
    suficiente para sacarla.

    **Prerrequisito que costó descubrir:** este drill NO se podía abrir
    en local, porque los datos demo de `compras.parquet` no traían
    `Proveedor` (mostraba "Faltan columnas"). Refactorizar 1.577 líneas
    sin poder ejecutarlas es como se rompen las cosas, así que el primer
    commit de la tanda fue completar `_datos_demo` (ver su bloque de
    `compras.parquet`). **Antes de tocar un dashboard, comprobar que su
    demo lo levante entero** — si no, ese es el primer commit.

    **Al verificar el resultado, ojo con `getComputedStyle`:** el pestillo
    de la tabla de documentos marcaba `rotate(180deg)` estando cerrado,
    lo que parecía un bug recién introducido. No lo era — la propiedad
    tiene `transition: transform .55s` y `getComputedStyle` sobre
    pseudo-elementos animados devuelve valores a mitad de vuelo. La
    verdad estaba en la CASCADA: leyendo las reglas del CSSOM, el
    `<style>` inyectado decía `rotate(0deg)`, que es lo correcto. Mismo
    espíritu que la regla #48.

56. **Al sacar un blob de JS/CSS embebido a su módulo: NO lo pases a raw
    string, y verifica el VALOR PARSEADO, no el texto fuente.** Sacar el
    JS de `inject_element_inspector` (1.381 líneas dentro de un
    `components.html`) rompió el inspector entero, y la verificación que
    hice no lo detectó. Las dos trampas, que van juntas:

    **(a) El raw string duplica los escapes.** El blob vivía en un string
    NORMAL. Ahí, un `\(` escrito en el fuente sobrevive tal cual (no es
    una secuencia de escape válida de Python), y el navegador recibe el
    regex que espera. Al moverlo a `r"""..."""`, los backslashes que el
    string normal colapsaba dejaron de colapsar y el JS quedó con
    `/var\\(\\s*(--[...]+)/g` → `SyntaxError: Invalid regular
    expression: Unterminated group`, con el inspector muerto de entrada.
    **Usa el mismo tipo de literal que el original** (aquí, triple-quote
    normal). El módulo lleva el aviso en su docstring.

    **(b) Comparar el fuente de git contra la constante nueva NO prueba
    nada.** Es exactamente el error que cometí: extraje el blob viejo con
    `git show` + rebanado de líneas (texto FUENTE, con `\\(`) y lo comparé
    contra el `JS` nuevo (valor PARSEADO). Coincidían, porque ambos tenían
    los backslashes sin colapsar — comparaba manzanas con naranjas, y dio
    verde sobre un módulo roto.
    **La comparación correcta es parsed-vs-parsed:**
    ```python
    import ast, subprocess
    src = subprocess.run(["git", "show", "HEAD:ruta/al/modulo.py"],
                         capture_output=True, text=True,
                         encoding="utf-8").stdout
    # El blob es el string constante MAS LARGO. NO lo busques por
    # "contiene __MI_PLACEHOLDER__": el propio literal del .replace()
    # también lo contiene (y mide 15 chars — me pasó, y sobrescribí el
    # módulo con esa basura).
    cands = [n.value for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    blob = max(cands, key=len)
    assert MiModulo.CONSTANTE == blob
    ```
    Con esto, `73.417 chars` idénticos. Y como red final: cargar la app
    con `?debug=1` y mirar la CONSOLA — el fallo era un `Uncaught
    SyntaxError` que ni `py_compile`, ni `ruff`, ni `test_graficos.py`
    pueden ver, porque el error ocurre en el navegador.
    **Ojo con el log de consola después de reiniciar el server:** conserva
    entradas del cargue anterior. Renavegar y volver a leer.

    **De paso, un hallazgo del mismo trabajo:** la cadena de nueve
    `.replace()` sustituía `__MAPA_PREFIJOS__`, un placeholder que **no
    existe en el JS**. Es un no-op: el JS declara siete mapas y busca solo
    por coincidencia exacta (`map[key] || ''`). O sea que la mitad Python
    del fallback por prefijo para keys dinámicas (f-string) está
    construida —incluidos los `_refs_de()` que cuesta calcular— y la mitad
    JS nunca se escribió. Consecuencia real: para las keys armadas con
    f-string (que este repo usa mucho), el tooltip no muestra `codigo` ni
    `snippet` ni `funcion`. Se dejó el `.replace()` con un comentario que
    lo dice, para que el código no mienta, a la espera de decidir entre
    borrar la mitad muerta o terminar la otra mitad.

57. **`configure_column(..., hide=True)` oculta la columna de la GRILLA,
    no de los paneles laterales "Columnas" ni "Filtros".** Ambos paneles
    (`agColumnsToolPanel`, `agFiltersToolPanel`) listan todo colId con
    `field` que exista en `columnDefs`, sin importar `hide` -- por diseño
    (así el usuario puede reactivar algo que Python escondió a propósito,
    ver regla #28). El problema es cuando esa columna oculta no es para el
    usuario en absoluto, sino una fuente interna que solo alimenta un
    `valueGetter` (patrón de columna SINTÉTICA, ver
    `tablas/ajuste_pivote.py`): `ajv_i`/`aj_i`/`tot_ajv`/`tot_aj` nunca
    reciben `header_name`, así que ambos paneles les muestran el field
    crudo como pastilla ("ajv_0", "aj_1"...) -- ruido sin sentido mezclado
    con Familia/Subfamilia/Producto. Se detectó por el panel Columnas
    (bug reportado, 2026-08-08) pero el panel Filtros tiene el mismo
    problema y pasaba desapercibido porque arranca colapsado.
    **Solución:** además de `hide=True`, pasar
    `suppressColumnsToolPanel=True` y `suppressFiltersToolPanel=True` en
    la misma llamada a `configure_column` para toda columna que sea
    puramente interna (alimenta otra columna, no se muestra nunca). Si en
    cambio la columna oculta SÍ debe quedar reactivable por el usuario
    (como Familia/Subfamilia en el árbol nativo), no se le ponen estas
    propiedades -- la distinción es esa, no "está oculta" sino "existe
    para el usuario".

58. **`_graf_heatmap_ajuste` (Mapa de calor de Ajuste) suma un selector de
    Vista — Mapa / Flujo (Sankey) / Tabla — y un selector de Corte real,
    además del Modo de la regla #42.** Agregado 2026-08-09 a pedido: las
    tres vistas leen el MISMO pivot Familia×Área del corte elegido, no
    son gráficos aparte — Mapa es el heatmap de siempre (top-3, totales,
    hover, click-drill, móvil: sin cambios de comportamiento), Flujo un
    `go.Sankey` nuevo, Tabla una grilla HTML con barra-en-celda (mismo
    patrón que `_filas_drill_html`, unas líneas más abajo en el mismo
    archivo — no una AgGrid nueva: un `cellRenderer` con barra-en-celda
    en AgGrid pide la interfaz de Component completa, ver regla #25).

    El corte NO sale de `df` (llega acotado a "más o menos un mes" por la
    franja superior — categoría "visual" de `categoria_rango_ajuste`,
    normalmente 1-2 cortes reales, no hay margen para animar) sino de
    `df_full` acotado a ~180 días, agrupado con `_cortes_por_racha` — la
    MISMA función que ya usa "Por fecha de corte" (`_pivote.py`) — NO
    calendario mes a mes. Sin `df_full`/`col_fecha`, o con menos de 2
    cortes en la ventana, no se ofrece el slider y la función se comporta
    exactamente como antes de este cambio (mismo criterio que el resto de
    los parámetros opcionales de esta función).

    **`df_full` NO trae los chips Área/Familia aplicados — hay que
    reaplicarlos a mano.** Los chips filtran `d` (-> `df`) en
    `graficos/ajuste/__init__.py`, nunca `df_full`. El primer intento de
    este selector armaba el corte directo desde `df_full` sin reaplicar
    `area_sel`/`fam_sel`: los chips seguían viéndose activos en pantalla
    pero el mapa/flujo/tabla del corte volvían a mostrar TODAS las áreas/
    familias apenas había más de un corte disponible (bug reportado en
    producción el mismo día). `_graf_heatmap_ajuste` ahora recibe
    `area_sel`/`fam_sel` igual que `_tabla_pivote_fecha_ajuste` (mismo
    problema, misma solución ya existente) y los reaplica sobre `df_full`
    ANTES de agrupar por corte.

    **Flujo (Sankey) no tiene click-drill, a propósito.** Mismo riesgo
    que la regla #11/#44: `on_select` sobre una traza que no sea
    Bar/Scatter/el Heatmap-con-overlay ya resuelto no está verificado en
    este entorno, y no hay forma de probarlo en vivo (el panel Browser no
    puede screenshotear ni clickear un Plotly, ver regla #44). Flujo se
    queda con hover rico (`customdata` + `hovertemplate`) y sin apostar a
    un click que nadie pudo confirmar que llega. Si hace falta de verdad,
    se verifica aparte antes de construirlo.

59. **`help=` en un `st.popover` cambia cuántos niveles de `<div>` hay
    entre `[data-testid="stPopover"]` y el `<button>` — rompe selectores
    CSS con hijo directo (`> div > button`).** Descubierto al convertir
    el trigger del asistente (`asistente.py`, `.st-key-ai_float_wrap`) de
    tab de texto a botón-ícono: agregar `help="Asistente IA"` hace que
    Streamlit renderice el botón DOS veces (una envuelta en
    `span.stTooltipIcon > span.stTooltipHoverTarget`, otra suelta en un
    `<div>` propio) — ninguna de las dos copias queda a la profundidad
    `div > button` que sí tenía el botón SIN `help=`. Resultado visual:
    el botón vuelve al estilo DEFAULT de Streamlit (pill blanca, 180px de
    `min-width`, flecha `expand_more`) como si el CSS no existiera,
    aunque el selector esté bien escrito — porque literalmente no
    matchea nada. Verificado con `outerHTML` del `[data-testid=
    "stPopover"]` en vivo (preview local): sin `help=`, un solo `<button
    data-testid="stPopoverButton">`; con `help=`, dos.
    **Regla:** para un popover que se estiliza a medida, o no usar
    `help=`, o escribir el selector como DESCENDIENTE (` button`, sin
    `>`) en vez de hijo directo — un descendiente sobrevive a que
    Streamlit intercale niveles nuevos. Antes de asumir que un selector
    "debería" matchear, confirmar la profundidad real con `outerHTML`
    (mismo espíritu que la regla #30, mismo elemento que ya la pisó una
    vez).

    **Aparte, simplificación de diseño (a pedido, 2026-08-09):** el
    trigger del asistente pasó de "tab de texto pegado al borde derecho,
    o cabecera de 84px del rail si `:has(.st-key-compras_tabs_row)`
    matcheaba" a un ÍCONO de 30px fijo en la esquina superior derecha de
    la FRANJA SUPERIOR (`.st-key-fila_ajuste_top`), igual en los 8
    reportes y en los 3 rangos de ancho — cero ramas por `:has()` ni por
    `@media` de rail. `right:15px` en los 3 anchos (mismo eje que el
    rail cuando lo hay; en los reportes sin rail simplemente flota con
    el mismo margen — el ícono vive en la banda 0-46/50px, el rail
    arranca en `top:66px`, nunca se tocan). `top` sí varía en UN punto de
    corte (el mismo `@media (min-width:901px)` que ya usa el resto de la
    franja): `(alto_franja - 30) / 2` → 8px cuando la franja mide 46px
    (desktop), 10px cuando mide 50px (default, cubre tablet 769-900px y
    móvil <=768px). Verificado con `getBoundingClientRect` en 375px,
    850px y 1280px, en reportes con rail grande (Ajuste) y rail de un
    solo ítem (Requerimientos, Receta Base) — mismas coordenadas
    `right`/`top` en los tres.

    **Bug real más grave, mismo día — reportado por el usuario ("el
    ícono desaparece al cambiar de reporte"):** `_inject_css()` tenía un
    guard `if st.session_state.get("_ai_css_inyectado"): return` para
    "inyectar el CSS una sola vez por sesión". Streamlit no funciona así:
    el árbol de elementos se reconstruye a partir de lo que el script
    EMITE en cada rerun — un `st.markdown` que no se vuelve a llamar no
    "queda" de la vez anterior, se BORRA. Con el guard, el `<style>` con
    `.st-key-ai_float_wrap` se inyectaba en el primer render de la sesión
    y desaparecía en el SIGUIENTE rerun (cambiar de reporte, tocar
    cualquier filtro — cualquier interacción de nivel superior): el botón
    volvía al popover DEFAULT de Streamlit (pill blanca, 180px,
    `border-radius:999px`) renderizado en flujo normal (al fondo de la
    página, donde cae `inject_asistente()` en `app.py`) — exactamente la
    captura que había mandado el usuario al pedir este cambio, que en su
    momento se atribuyó (mal) a una versión vieja del deploy. Confirmado
    en vivo simulando un rerun real (click a otro reporte por JS, MISMA
    sesión/WebSocket, sin recargar la página):
    `document.querySelectorAll('style')` pasa de tener 1 bloque con
    "ai_float_wrap" a 0, y el botón mide 180px otra vez.
    **Regla:** un `st.markdown(unsafe_allow_html=True)` que inyecta
    `<style>`/`<script>` que la página necesita VER tiene que llamarse
    SIN CONDICIÓN en cada rerun — mismo patrón que ya usa, sin guard,
    `estilos/__init__.py::inject_css()` (`app.py:74`, docstring de
    `get_css()`: "no vale la pena cachear a cambio de perder recarga").
    Un guard de sesión sí sirve para *cachear el cálculo* de un string
    caro (ó para inicializar un valor una sola vez); nunca para decidir
    si el `st.markdown` que lo *emite* se llama o no — eso siempre.
    Detectarlo requiere probar un RERUN EN LA MISMA SESIÓN (cambiar de
    reporte, tocar un filtro), no solo un reload de página — un reload
    resetea `session_state` y el bug queda invisible (así pasó la
    primera verificación de este mismo cambio).

60. **"Aparece/desaparece en `:hover` pero sin empujar nada de abajo" se
    anima con `opacity`/`visibility`, nunca `max-height`/`padding`/
    `height`.** `.ajcas-head` (cabecera de la tabla de Cascada,
    `graficos/ajuste/_cascada.py`) tuvo dos versiones opuestas en 24
    horas. v1 (2026-08-08, "opción 1" de 6 propuestas, a pedido): oculta
    con `max-height:0` + `padding-bottom:0`, visible en hover animando
    ambas a su valor real — funcionaba, pero `max-height`/`padding` SÍ
    generan layout, así que aparecer/desaparecer corría la primera fila
    de la tabla hacia abajo/arriba ("empuja las filas, mismo
    comportamiento que el mockup aprobado" — el comentario original
    documentaba el push como intencional). v2 (2026-08-09, a pedido
    contrario): mismo reveal en hover, cero desplazamiento de lo que
    sigue.
    **Regla:** si el pedido es "revela sin empujar", el elemento ocupa
    su tamaño real SIEMPRE (oculto o visible — nada de `max-height:0`/
    `display:none`/clamps de padding) y el toggle de hover va solo por
    `opacity`/`visibility` (`opacity:0;visibility:hidden` ↔
    `opacity:1;visibility:visible`, `transition` en ambas) — ninguna de
    las dos genera layout. Iba `visibility` además de `opacity` para que
    el contenido oculto no quede seleccionable ni en el tab order; por
    la regla de animación CSS para propiedades discretas, el fade-out
    sigue viéndose suave (`visibility` se queda en "visible" hasta el
    100% de la transición al ocultar, salta a "visible" en el 0% al
    mostrar) — mismo patrón que ya tenía `.ajcas-tip-txt` en el mismo
    archivo, copiado sin inventar uno nuevo. Si el pedido fuera al revés
    (que SÍ empuje — acordeón, la v1 original), ahí corresponde animar
    una propiedad de layout (`max-height`/`grid-template-rows`), a
    sabiendas de que reserva 0px oculto.
    **Verificación:** mismas dos trampas que regla #44 y #48 (agravadas
    porque acá el panel Browser de esa sesión tampoco componía frames,
    igual que regla #44 — `computer{action:"screenshot"}` con timeout,
    solo funcionan clics/hover por `ref` de `read_page`, no por
    coordenada). `getComputedStyle` sobre `.ajcas-head` mintió tanto en
    reposo como hovereado (devolvía `opacity:1;visibility:visible` sin
    hover real activo, `:hover` global vacío) por tener `transition` —
    mismo síntoma que la regla #48. Verificación que sí sirvió: (1) leer
    la regla real vía `document.styleSheets` → `cssRules` en vez de
    `getComputedStyle`, confirmando que el `<style>` servido solo toca
    `opacity`/`visibility`; (2) un hover REAL disparado con
    `computer{action:"hover", ref:...}` (dispara `:hover` de verdad vía
    CDP; un `dispatchEvent` de JS no activa el pseudo-selector) sobre un
    `ref` de un texto dentro de la cabecera, confirmando por
    `document.querySelectorAll(':hover')` que el ancestro
    `st-key-chartcard_cascada` sí entraba en `:hover`; (3)
    `getBoundingClientRect().top` de la primera fila medido en reposo,
    hovereada y post-hover — idéntico en los tres momentos, prueba de
    cero reflow.

61. **Panorama de compras (`recetaventa.py`, 2026-08-09): 5ª vista del rail
    de Receta Venta, la primera que cruza DOS parquets.** Sankey
    Producto comprado → Plato, agregado (no un plato a la vez como las
    otras 4 vistas). Mismo precedente de carga cruzada que
    `graficos/ventas.py::_compra_por_dia` (`data.cargar("compras.parquet")`
    directo, sin pasar por `df_f`).

    **El join es por código, no por nombre — y las columnas que PARECEN
    la clave no lo son.** `compras.COD_PRODUCTO` ↔ `recetaventa.COD INS`
    (y `recetabase.COD INS RB`) es la clave real, validada con datos
    reales: 31,7% de los códigos de compra matchean, y semánticamente
    tiene sentido (Ají Amarillo → Lomo Saltado, Tomahawk → Tomahawk).
    `LLAVE_PRODUCTO`/`ENLACE`/`RB ART ENLAZADO`/`RB INS ENLAZADO` tienen
    nombre de clave de cruce pero están casi vacías (`ENLACE`: 2 valores
    no nulos en 2.711 filas) — señuelo, no usar. Detalle completo en la
    memoria de proyecto `esquema-real-compras-recetaventa`.

    **`recetaventa.parquet` mezcla platos activos y de baja — filtrar
    ANTES de agrupar, no después.** 54,8% de las filas son
    `ITEM VENTA ACTIVO = 'INACTIV'` (842 platos en el catálogo, solo 418
    activos). Se detectó a ojo: un primer mockup sin este filtro mostraba
    nombres de platos que el usuario reconoció como dados de baja al
    instante ("esos platos no están activos"). `ITEM VENTA ACTIVO='ACTIV'`
    ya implica `RV ACTIV='RV ACT'` (mismo conteo exacto, 1226 filas);
    sumar `INS ACTIVO='ACTIV'` afina un poco más (1226→1200). Con el
    filtro puesto la cobertura compras↔receta baja de 33,7% (mal, sin
    filtro) a 20,9% (la real) — el número más alto era artefacto del
    bug, no una mejora.

    **Sin click-drill sobre los nodos del Sankey — mismo motivo que la
    nota de Flujo/Ajuste más arriba (regla #11/#44), nunca resuelto para
    `go.Sankey` en este entorno.** Interacción vía `st.selectbox` en su
    lugar: uno lista las recetas de un insumo elegido (tabla), otro
    setea `session_state["rv_plato_sel"]` + `session_state["rv_graf_tipo"]
    = "Sankey por plato"` y hace `st.rerun()` para reusar la vista de
    UN plato que ya existía, en vez de duplicar esa lógica. Verificado
    en vivo: funciona, pero el resultado tarda 1-2 reruns en reflejarse
    en `get_page_text`/`read_page` — no dar por "no funcionó" sin volver
    a leer la página después de esperar.

    **Bug de reconciliación descubierto al agregar esta vista (no
    exclusivo de ella): un widget de una vista anterior queda huérfano
    (visible, `data-stale="false"`, funcional) si el código que lo crea
    queda envuelto en un `if` que esta vez no se cumple.** Pasaba con el
    selectbox "Plato" (compartido por Sankey/Composición, key
    `rv_plato_sel`) al entrar a Ranking/Ingredientes/Panorama — y con los
    `st.selectbox` propios de Panorama, al salir hacia Ranking. Los dos
    tenían el MISMO patrón: `if condición: with columna_o_container: ...`.
    **Fix de dos partes, hace falta las dos:**
    1. Invertir el orden — `with columna: if condición: widget(...)` —
       para que Streamlit "visite" esa posición TODOS los runs (vacía o
       no) en vez de saltearla enteramente cuando la condición es falsa.
    2. Envolver el contenido de cada rama del dispatcher en
       `st.container(key=f"rv_graf_body_{graf...}")` — key que VARÍA por
       vista, no fija — mismo espíritu que el contador de remount de la
       regla #9, aplicado al nombre de la vista en vez de a un contador
       de aperturas.
    Con las dos partes, las transiciones entre vistas quedan limpias
    (verificado Panorama→Ranking→Panorama). Quedó un residuo menor: el
    selectbox "Plato" se vio huérfano en la PRIMERA transición después
    de cargar la página (Sankey, la vista default, → cualquier otra) y
    se resolvió solo en la siguiente — no perseguido más a fondo, parece
    un desfasaje de un run en el primer rerun de la sesión. Si se topa
    de nuevo, empezar por ahí.

62. **El corte es un CONJUNTO de días, no un intervalo — por eso tiene su
    propio modo en el calendario y no es un atajo más (2026-08-09).**
    Una sesión de inventario se abre y se cierra en días sueltos: "1-5 ago"
    puede ser {1, 5}, y el 2, 3 y 4 traer ajustes diarios que NO son de ese
    conteo. Verificado con data real: de 12 cortes, la mayoría tiene huecos.

    ```
    rango  →  df[fecha].between(ini, fin)   INTERVALO — arrastra los ajenos
    corte  →  df[fecha].isin(dias)          CONJUNTO  — exacto
    ```

    Un `st.date_input` solo sabe expresar lo primero. De ahí el diseño:
    · `cortes.py` (raíz, sin streamlit ni graficos) calcula las rachas.
      Subió desde `graficos/ajuste/_comun.py`, que ahora lo reexporta con
      los nombres privados de siempre — el cálculo lo necesitan los dos
      lados (la franja de `app.py`, genérica a los 8 reportes, y el mapa
      de calor) y duplicarlo es la forma más fácil de que discrepen sobre
      dónde empieza un corte.
    · `estado_rango.py` es el dueño de los TRES estados (rango, corte,
      modo). `clave_modo` se DERIVA de `clave_corte`, que a su vez espeja
      la partición por categoría de `clave_rango`: una sola partición para
      los tres, así no hay forma de que el modo apunte al corte de otra
      categoría.
    · **`aplicar_corte` escribe el corte Y el rango.** El rango no es
      redundante: lo leen el `date_input`, el label del pill y el loader
      de R2, y ninguno sabe qué es un corte. El corte estrecha; no
      reemplaza el estado.
    · El `date_input` se dibuja en LOS DOS modos. Streamlit descarta el
      estado de un widget que deja de renderizarse: esconderlo en modo
      Cortes borraría la clave del rango del reporte.
    · Tocar el calendario a mano vuelve a modo Rango (`on_change`), y
      cambiar de modo NO borra el corte: lo desactiva. Volver lo restaura.
    · Flag `"cortes": True` en `REPORTES`. Sin él el panel queda idéntico
      — en Ventas o Compras las fechas son continuas y las rachas serían
      ruido.

    **TRES modos, no dos** (2026-08-09, 2ª pasada): `Rango · Corte ·
    Varios`. Corte y Varios comparten estado — el mismo conjunto de días,
    distinto gesto: en Corte el clic REEMPLAZA la selección (revisar un
    conteo, el caso normal), en Varios la ALTERNA.

    El tercer modo se llamó **"Comparar" y era un nombre mentiroso**
    (corregido 2026-08-10, lo detectó el usuario): no compara nada, SUMA.
    Los días de las sesiones elegidas se unen en un conjunto y todo lo de
    abajo muestra el TOTAL de ese conjunto; no hay vista lado a lado por
    ningún lado. "Acumulado" tampoco: en inventario se lee como total
    corrido desde una fecha (YTD) y acá la selección es arbitraria — se
    puede elegir marzo y agosto salteando el medio. Los tres modos son
    SUSTANTIVOS que nombran la unidad de tiempo que se elige; el verbo va
    en el caption de la lista ("Suma las sesiones que elijas"), no en la
    pastilla. Al renombrar un modo, `modo_fecha()` valida contra
    `MODOS_FECHA` y cae a "Rango" si el valor guardado ya no existe: un
    `st.segmented_control` con un `default` fuera de sus opciones no
    falla, arranca sin nada seleccionado y el panel queda mudo. Por eso cambiar de
    uno a otro no pierde nada y `modo_por_cortes()` existe: para que nadie
    escriba la comparación a mano y se olvide de una de las dos ramas.
    `_fusionar()` une N cortes en un estado con la MISMA forma que uno
    solo — `dias` es la unión — así el filtro `isin(dias)` no distingue si
    viene de uno o de cinco y nada río abajo cambió. Verificado con data
    real: 3 sesiones elegidas = rango de 52 días con 6 días de datos, 46
    excluidos. Eso es lo que un `date_input` no puede expresar.

    La primera versión usaba un `st.toggle` "Elegir varios" ADEMÁS del
    segmentado Rango/Cortes: dos controles apilados para una sola
    decisión. Fusionarlos en el segmentado sacó un widget de la pantalla y
    de paso volvió el modo verificable — un `st.toggle` es un React-Aria
    pressable y **no responde a eventos sintéticos** (`.click()` ni
    `KeyboardEvent`), así que no se puede accionar desde la consola; los
    `st.button` y los `stButtonGroup` (pills/segmented) sí. Si hace falta
    poder manejar un control desde `javascript_tool`, que sea uno de esos.

    Las etiquetas de la lista llevan AÑO y no el conteo de días
    (`etiqueta_corte_anio`, a pedido). Es una función aparte de
    `etiqueta_corte` porque esa la consumen las cabeceras de la tabla
    pivote, cuyo ancho se calcula del largo del label
    (`tablas/ajuste_pivote.py::_ancho_header_periodo`): sumarle 5
    caracteres ahí vuelve a truncarlas, que es un bug ya arreglado una vez.

63. **Dos controles del MISMO concepto no se pisan el estado, pero igual
    es un bug (2026-08-09).** El mapa de calor tenía su `select_slider` de
    corte y la franja ganó el suyo. Cada uno con su clave: nada se
    sobrescribía. Pero mostraban cortes DISTINTOS a la vez y no había
    forma de saber cuál mandaba. Regla: **un eje, un dueño.** Con el corte
    global activo, `_graf_heatmap_ajuste` no dibuja su slider y saltea el
    `df_full.copy()` entero. Sin caption que lo explique: el pill de la
    franja ya dice "Corte 1-5 ago" y esa fila de controles se compactó a
    propósito (ver regla #58) — devolverle una línea la desarma.

64. **El stepper del corte NO va dentro de `fecha_ajuste_pill`
    (2026-08-09).** Ese pill tiene ancho FIJO de 210px y los chips se
    anclan a `left: 391px` = 175 (left del pill) + 210 + 6. Son tres
    números acoplados; meter dos botones adentro los rompe. El stepper
    vive en `st-key-fecha_corte_nav`, anclado a `right: 138px` — el hueco
    que el propio pill dejó libre al mudarse a la izquierda en el bloque
    de desktop. Solo se renderiza con un corte activo, así que aparecer y
    desaparecer no mueve nada. Visible recién desde 1400px: entre 901 y
    1400 los chips (que crecen según el reporte) le llegarían encima, y
    abajo de eso la navegación vive en el panel, que siempre tiene la
    lista completa. Verificado a 1600px: pill 175→385, chips 391→627,
    stepper 1286→1462, asistente en 1555. Cero solapes.

65. **Datos demo que no tienen la FORMA del dato real no verifican nada
    (2026-08-09).** El demo de `ajusteinventario.parquet` repartía 240
    filas uniformes sobre 300 días: eso da ~150 días con movimiento
    separados por 1 día y, como un corte admite saltos de hasta 4
    (`cortes.CORTE_MAX_SALTO_DIAS`), TODO el año colapsaba en UN corte.
    Ni el slider del mapa de calor ni el modo Cortes se podían probar en
    local — el mismo bloque ya había tenido el mismo problema con las
    fechas de 2024 y la vista "Por fecha de corte". Ahora genera sesiones
    de 1 a 4 días separadas por 12-28 días, con saltos internos que dejan
    huecos DENTRO de la sesión. Al agregar una vista que dependa de la
    FORMA temporal del dato (no solo de que haya fechas), revisar que el
    demo la reproduzca.

66. **`go.Heatmap` no tiene bordes por celda porque no son celdas — es
    una sola imagen (2026-08-09).** El pedido de "bordes redondeados
    como el resto de la app" en el Mapa de calor de Ajuste no se puede
    resolver con CSS: se verificó por DOM
    (`document.querySelector('.heatmaplayer')`) que Plotly renderiza el
    heatmap completo como UN `<image>` con un PNG en base64 — cero
    `<rect>` por celda, nada que un selector CSS pueda alcanzar. La
    vista "Mapa" (`_heatmap.py`) se reescribió sin `go.Heatmap`: una
    grilla de `st.button` (una celda = un botón), color de fondo
    calculado en Python con `plotly.colors.sample_colorscale` (misma
    colorscale que antes) y aplicado vía `st.markdown` con CSS por key
    (`hm_cell_<i>_<j>`), tooltip vía `help=` en vez del hovertemplate
    (incluye el mismo sparkline de tendencia, ahora como texto plano).
    El radio de borde sale gratis: `button[kind="secondary"]` ya tenía
    `border-radius: 8px !important` global en `_00_base.py` — no hizo
    falta CSS nuevo para eso. El click ya no pasa por `on_select` (regla
    #11: ese era el motivo original del overlay `go.Scatter`, que esta
    reescritura también elimina) sino por el patrón normal de botón de
    Streamlit — `st.session_state["hm_ajuste_focus"]` + `st.rerun()`.
    Todo el resto de la vista se preservó sin cambios de comportamiento
    (top-3 + atenuado, fila/columna TOTAL, click-drill con tendencia
    real y ranking Faltantes/Sobrantes con cantidad+unidad) porque esa
    lógica vive después del pivot, no depende de cómo se dibuja la
    celda. Si otra vista necesita bordes/radios por elemento sobre datos
    tabulares, este es el patrón: HTML/botones en vez de una traza
    Plotly que rasteriza.

67. **"Preservar el comportamiento anterior" no es lo mismo que "revisar
    el mockup" — la regla #66 preservó algo que el mockup nunca tuvo
    (2026-08-09).** El go.Heatmap de antes de la reescritura resaltaba
    el top-3-por-signo a color pleno y atenuaba el resto (mezcla 50%
    hacia lavanda) con un segundo trace semitransparente encima. Al
    reescribir el Mapa sin `go.Heatmap` (regla #66) preservé ese
    top-3/atenuado "sin cambios de comportamiento" — pero sin volver a
    mirar el mockup (`ajuste_ideas_mapa_calor.html`) que motivó todo el
    cambio de layout de esta vista. Ese mockup nunca tuvo la idea: su
    `diverge(v, vmax, stops)` pinta CADA celda a color pleno, proporcional
    a su propio valor, sin concepto de "top N" ni de atenuar el resto.
    El usuario, comparando con el mockup, lo describió como "un marco"
    (el anillo de borde de los top-3) en vez de intensidad de color — y
    tenía razón: con la mayoría de las celdas atenuadas al mismo lavanda
    parejo, el color dejaba de decir nada sobre la magnitud individual;
    solo el anillo distinguía "importante" de "no importante".

    Se sacó el top-3/atenuado entero: `_color_celda` perdió el parámetro
    `atenuar` (siempre color pleno), y el contraste de texto (blanco vs.
    oscuro) pasó a decidirse por luminancia real del color de fondo de
    CADA celda, no por pertenecer al top-3 — antes una celda fuera del
    top-3 jamás tenía texto blanco aunque su fondo fuera oscuro (no podía
    pasar, estaban todas atenuadas hacia el lavanda claro); ahora
    cualquier celda con fondo suficientemente oscuro lo tiene. De paso,
    la columna TOTAL bajó de una fracción de ancho propia (1.1) a la
    misma que una columna de dato (1.0) — en el mockup ocupa el mismo
    `cellW`, más angosta por el margen interno del rect, no por una
    fracción de columna mayor; con 1.1 se notaba visiblemente más larga.

    Regla general para "esto no se parece al mockup": releer el mockup
    de nuevo en ese punto puntual en vez de asumir que el comportamiento
    heredado del código anterior seguía siendo la intención — heredar
    sin revisar es cómo esta vista terminó con una regla que la regla
    #66 documentó como "preservada" y que en realidad nunca debió
    sobrevivir a esa reescritura.

68. **El texto de un `st.button` no está en el `<button>`: está en un
    `<p>` con su propio `font-size` (2026-08-10).** Streamlit envuelve
    el label en `button > div[stMarkdownContainer] > p`, y ese `<p>`
    trae `font-size:14px; font-weight:400` propios. `font-size` NO
    cascadea a través de un elemento que define el suyo, así que
    cualquier `.st-key-x button { font-size: ... }` se ve pisado y no
    hace absolutamente nada sobre el número que el usuario lee. En el
    mapa de calor esto convivió con celdas TOTAL hechas de `<div>`
    (sin `<p>` de por medio, donde el estilo inline SÍ aplica): mismo
    `font-size` declarado en el código, tamaño real distinto en
    pantalla (14px/400 contra 10.5px/600). Se "arregló" una vez
    bajando el valor en la regla del `<button>` — cambio que no movió
    un píxel, porque apuntaba al nodo equivocado.

    El selector correcto es `... button p` (o `button
    [data-testid="stMarkdownContainer"] p`), que es el que YA usaban
    `_20_compras_rail.py` y `_40_ajuste_franja.py` — o sea: el repo ya
    lo sabía, se reinventó mal. `color` sí funciona desde el `<button>`
    (el `<p>` no lo declara, lo hereda), que es justo por qué el color
    de celda venía bien y confundía el diagnóstico.

    **Corolario de método, que es la parte que más costó:** al medir
    con `getComputedStyle` hay que apuntar al nodo que DIBUJA el texto,
    no al contenedor. Medir el `<button>` daba "10.5px" y confirmaba
    una corrección que en realidad no existía. La verificación que sí
    cierra: buscar el elemento HOJA (`el.children.length === 0`) y
    medir el ancho real del glifo con un `Range` sobre su nodo de
    texto — dos textos idénticos ("S/ 403" aparecía como celda de dato
    y como total) que miden 44px y 36px no dejan lugar a interpretación.

69. **El asistente IA consulta los datos con tool calling — y las trampas
    son de SEMÁNTICA, no de sintaxis.** Reescrito 2026-08-09: antes recibía
    un resumen de 7 líneas del df (totales + top 5 de UNA categórica, sin
    los nombres de las columnas) y con eso no podía responder "qué producto
    tuvo más merma". Hoy `asistente_datos.py` le da dos herramientas
    (`consultar_datos(sql)` sobre DuckDB en memoria, `buscar_web(query)` vía
    Tavily) y `asistente.py` corre el bucle de rondas.

    Se midieron 4 modelos de Groq contra datos reales antes de construir:
    `gpt-oss-120b`, `llama-3.3-70b-versatile`, `gpt-oss-20b` y
    `qwen/qwen3.6-27b`. Los 4 soportan tool calling, los 4 citaron bien las
    columnas con espacios y ninguno falló un SQL. **El modelo NO era el
    cuello de botella** — se quedó `gpt-oss-120b`. Lo que sí fallaba, y que
    el system prompt ahora ataja con reglas numeradas:
    - **Agregación:** 3 de 4 respondieron "los 5 PRODUCTOS con más merma"
      con `ORDER BY ... LIMIT 5` sobre filas CRUDAS — o sea los 5
      movimientos, no los 5 productos. Con la regla explícita de
      `GROUP BY` + `SUM`, `gpt-oss-120b` ahora escribe la consulta correcta.
    - **Aritmética en prosa:** `llama-3.3-70b` listó 5 cifras que suman
      −28.907 y afirmó que el total era −30.070. Regla: los totales los
      calcula el SQL. Verificado que el modelo obedece — para una pregunta
      mixta emitió `SELECT SUM("AJUSTE") * 79` en vez de multiplicar a mano.
    - **Signo:** una corrida escribió `S/ 4,864.29` para una merma (que es
      negativa) "porque ya había dicho que era merma". En un reporte
      financiero eso invierte el sentido del número. Regla explícita de
      conservar el signo del SQL.
    - **Año del entrenamiento:** buscaba `precio lomo fino Lima 2024` en
      pleno 2026 y presentaba precios viejos como actuales. El prompt ahora
      inyecta la fecha de hoy (`_hoy_peru()`); el modelo NO la sabe.

    **El peor fallo posible, y es SILENCIOSO:** una columna con espacios sin
    comillas dobles no siempre da error. `SELECT AJUSTE VALORIZADO FROM
    datos` lo lee DuckDB como `SELECT AJUSTE AS VALORIZADO` → devuelve la
    columna de UNIDADES (−10) etiquetada con el nombre de la de SOLES
    (−1000). Sin excepción, sin warning, cifra equivocada por dos órdenes de
    magnitud. Dentro de `SUM(...)` sí revienta, así que el peligro es el
    SELECT/GROUP BY/ORDER BY desnudo — justo donde el modelo lo escribiría.
    `asistente_datos.columnas_sin_comillas()` lo detecta y RECHAZA la
    consulta con instrucciones para que el modelo reintente citando.

    Otras dos cosas que costaron una vuelta:
    - **`_MAX_RONDAS` = 8, no 5.** Una pregunta mixta ("mi merma de lomo,
      ¿cuánto es a precio de mercado hoy?") gasta 3 consultas ubicando el
      producto y su unidad de medida, 1 búsqueda web y 1 cálculo: con 5 se
      quedaba sin rondas justo antes de responder.
    - **Los chips NO llegaban al asistente.** `app.py` pasa `df_f`, que está
      filtrado por FECHA pero no por Área/Familia (esos se aplican sobre una
      copia local dentro de cada dashboard — misma trampa que la #58). El
      asistente respondía totales que contradecían la pantalla. Se resolvió
      con `graficos.base.publicar_contexto_ia(reporte, df, filtros)`, que
      cada dashboard llama tras aplicar sus chips; el asistente valida que
      el reporte publicado sea el activo antes de usarlo, porque si no un
      contexto viejo sobrevive en `session_state` y miente en silencio.

    La capa de datos se testea sin API key ni navegador
    (`test_asistente_datos.py`, 39 casos) — ese es el motivo de haberla
    separado de `asistente.py`.

70. **Un bloque condicional dentro de un `@st.fragment` deja elementos
    HUÉRFANOS: Streamlit no limpia un slot cuyo render siguiente produce
    MENOS elementos.** Caso real (2026-08-09, panel del asistente): el
    bloque de bienvenida (saludo + 3 chips de sugerencia) se dibuja solo
    `if not historial and not pendiente`. Al llegar la primera respuesta la
    condición pasa a False, pero los chips seguían pintados colgando DEBAJO
    de la respuesta. Tres formas probadas, con el resultado MEDIDO en el
    preview (contando `div[class*="st-key-ai_sug_"] button` en el DOM):
    - `if` suelto → sobrevivían **2 de 3** chips.
    - `st.container(key="…")` envolviendo el `if` → **PEOR**: los 3 chips
      *más* el saludo. Un container keyed tiene identidad estable y por eso
      RETIENE a sus hijos; la intuición de "un slot con key se limpia solo"
      es exactamente al revés.
    - `st.empty()` creado SIEMPRE + `with hueco.container():` solo cuando la
      condición se cumple → **0 huérfanos**. `st.empty()` reemplaza su
      contenido en cada render, así que dejarlo sin llenar lo vacía de
      verdad.
    **Regla:** para un bloque que tiene que DESAPARECER (no solo cambiar),
    `st.empty()`. Ni `if` suelto ni container keyed.
    Un `st.rerun(scope="fragment")` después de mutar el estado ayuda pero
    NO alcanza: el bug se reprodujo con el rerun puesto, por el camino del
    `st.chat_input` (el del `on_click` de un botón sí quedaba limpio, lo que
    hace fácil declarar victoria antes de tiempo — hay que probar los DOS
    caminos de entrada).

71. **`st.pills`/`st.segmented_control` fuera de una corrida real de
    Streamlit siempre devuelve su `default`, ignorando lo que haya en
    `session_state`.** Confirmado con un probe suelto: hacer
    `st.session_state[key] = "B"` ANTES de `st.pills(..., key=key,
    default="A")` no cambia nada — el widget igual devuelve `"A"`;
    Streamlit avisa "Session state does not function when running a
    script without `streamlit run`". Consecuencia para `test_graficos.py`
    (que llama a los `_graf_*` fuera de una app real, ver cabecera del
    script): cualquier vista detrás de un pill solo se smoke-testea en su
    rama DEFAULT. Ya pasaba sin que nadie lo hubiera dejado escrito con
    `_vista` de `_graf_heatmap_ajuste` ("Flujo"/"Tabla" nunca se
    construyen en el test) y pasa ahora también con el toggle
    Distribución/Histograma de `_graf_distribucion_ajuste` (regla #72). No
    hay forma de forzar la rama no-default precargando `session_state`
    como si fuera una app real. Si una vista detrás de un pill tiene
    lógica no trivial que valga la pena cubrir, la salida es partirla en
    una función propia que el test llame directo (sin pasar por el pill),
    no pelearse con `session_state`.

72. **Para poner el valor continuo de un `px.histogram` en el eje
    VERTICAL, se pasa `y=col` en vez de `x=col` — no existe un parámetro
    `orientation` aparte que lo haga.** Volteado esto, hay que voltear en
    pareja o el resultado queda mal etiquetado: la línea de referencia pasa
    de `add_vline(x=0, ...)` a `add_hline(y=0, ...)`, y el
    `tickprefix`/`tickformat` de moneda se mueve del override `xaxis=` al
    `yaxis=`. Caso real (`_graf_distribucion_ajuste`, 2026-08-10): la rama
    sin columna de grupo (sin Familia/Área) arma un histograma simple con
    el ajuste ahora en Y, para que combine con el strip de arriba (que ya
    tenía el ajuste en Y) en vez de acostarse cuando antes vivía en X.
    De paso, "Distribución" y "Histograma" dejaron de compartir
    `st.columns(2)` a medias — a media columna el strip amontonaba
    categorías largas y el histograma apretaba sus 30 bins. Ahora es un
    `st.pills` ("Vista distribución") que alterna cuál de las dos se
    dibuja, siempre a ancho completo (ver regla #71 para el límite que
    esto le impone a `test_graficos.py`).

73. **La barra de Plotly (modebar) por default trae 10 botones, casi
    invisible (`displayModeBar="hover"`), Y el modo de arrastre por
    default es "pan" — no "zoom" ni "select".** `on_select`/
    `selection_mode` de `st.plotly_chart` NO tocan ninguna de las dos
    cosas: confirmado con un probe (`gd.layout.dragmode`) sobre
    `_graf_distribucion_ajuste` con `on_select="rerun",
    selection_mode=["points","box","lasso"]` puesto — el dragmode seguía
    en `"pan"`. Consecuencia real (reportada por el usuario, captura con
    flechas sobre la barra): con "pan" de default, arrastrar sobre el
    gráfico CORRE la vista en vez de seleccionar, y con la barra oculta
    hasta que el mouse pasa por encima, no hay pista de que existe un
    botón para cambiar de modo — fácil terminar viendo una sola familia y
    creer que el resto no tiene datos (el caso que motivó esta regla).
    **Arreglo, en `_distribucion.py`:** `fig.update_layout(dragmode=
    "select")` explícito cuando la selección está activa (deja el drag
    listo para usar SIN tocar la barra) + `config` con
    `modeBarButtonsToRemove` recortado a lo que el gráfico realmente
    ofrece (fuera `zoom2d`/`pan2d`/`zoomIn2d`/`zoomOut2d`/`autoScale2d`;
    queda `select2d`/`lasso2d` si el chart soporta lazo, `resetScale2d`,
    `toImage`) + `displayModeBar=True` (visible siempre, no solo al pasar
    el mouse). Cuando la selección está apagada (sin `col_producto`), la
    barra entera se oculta — un botón de selección que no hace nada es
    peor que no tener botón. Esto EXTIENDE el precedente de
    `graficos/compras/proveedor.py` (`_cfg_chart`, ~línea 490): ese caso
    es más simple (`selection_mode="points"`, un click alcanza, así que
    esconde la barra ENTERA en desktop); acá el chart depende de
    arrastrar (`"box"`/`"lasso"`), así que esconder la barra habría
    tapado la única forma de cambiar de modo si `dragmode="select"` no se
    fijara a mano — las dos piezas (dragmode explícito + barra recortada)
    van juntas, ninguna sola alcanza.

74. **`go.Candlestick` (drill Volatilidad de insumos,
    `graficos/compras/volatilidad.py`) — sin precedente de selección
    confiable en este proyecto, igual que `go.Heatmap` (#11) y
    `go.Histogram` (#44): se asume que el clic no llega desde la traza de
    velas y se agrega una `go.Scatter` invisible (`marker.opacity=0`, un
    punto por semana en `(h+l)/2`) como trace 1, con `hoverinfo="skip"`.
    El handler solo procesa el clic si `curve_number == 1` — un clic
    reportado desde la traza 0 (las velas) se ignora. Mismo patrón de
    dedup que `proveedor.py` (key estable por insumo seleccionado +
    `session_state["compras_vol_last_click"]` comparando el
    `point_index` contra el último procesado, para no reabrir/cerrar la
    semana en cada rerun). **No se pudo verificar el clic en sí con el
    navegador del entorno de desarrollo — ver regla #12: esta clase de
    selección de Plotly no se puede simular ahí.** Falta un smoke test
    manual real después de deployar.

    **Bug real ya encontrado y corregido en la misma sesión:** la ventana
    de semanas al principio usaba TODO el rango de fecha que el usuario
    tuviera elegido en la franja (para "respetar" el filtro global). Con
    "Todo" (3.5 años, 189 semanas) el ranking salió dominado por
    `Servicio De Movilidad Y Flete` con 56.602 puntos de "volatilidad" —
    un artefacto: 189 velas no caben en un gráfico legible, y encima
    mezclan huecos de años con movimiento real. **La ventana del
    candlestick SIEMPRE se recorta a las últimas `MAX_SEMANAS=8` semanas
    con datos** (`_vol_semanas_ventana`), sin importar cuánto rango tenga
    seleccionado la franja — el filtro de fecha global es un TECHO, no la
    ventana en sí. Con el recorte puesto, el mismo insumo bajó a 573
    puntos: sigue siendo el más volátil de sus últimas 8 semanas (un
    hallazgo real, no ruido), pero ya no un número que solo se explica
    por el largo del rango.

    El filtro de materialidad (`MIN_GASTO=400` soles gastados en la
    ventana) y de cobertura (`MIN_COBERTURA=0.75`, al menos 75% de las
    semanas con compra) existen por la misma razón que el recorte de
    ventana: sin ellos, insumos comprados en cantidades mínimas (hierbas,
    condimentos) dominan el ranking con "volatilidad" que es ruido de
    redondeo de `VALOR_COMPRA / CANTIDAD_COMPRA`, no un movimiento de
    precio real. Ninguno de los dos filtros excluye por NOMBRE o
    categoría (nada de listas de "esto no es un insumo de mercado") — son
    puramente estadísticos, a propósito: más robusto y menos frágil que
    adivinar qué productos "no cuentan".

    `TIPO_MONEDA` no lo resuelve ningún otro drill de Compras — se
    agregó su propio `_resolver` en `__init__.py` (candidatos
    `["Tipo_moneda", "Tipo Moneda", "Moneda"]`) y el drill lo trata como
    **opcional**: si no resuelve (el demo local no trae esa columna) o no
    está en `d`, no se filtra por moneda en vez de romper. Mezclar
    monedas en una sola serie de precio sería incorrecto, pero preferible
    a que el drill no abra en local.

    Semáforo de la tabla ranking: NO es AgGrid con `cellStyle`/`JsCode`
    (el patrón de `ventas.py` para su ranking de FoodCost) sino
    `st.dataframe` + pandas `Styler` (`.map`/`.apply`), como el otro
    patrón ya usado en `ventas.py` para la tabla de SubGrupo — más simple
    y sin componente JS de por medio. La "barra" de la columna
    Volatilidad no es un cellRenderer: es un `linear-gradient` CSS de dos
    colores en el `background` de la celda, con el corte en `pct%` — el
    mismo truco que un progress-bar falso, sin necesitar Component de
    AG Grid (regla #25 solo aplica si el renderer tiene que devolver HTML
    real; un `background` vía `Styler` es CSS puro).

75. **Inventario Valorizado v3 (2026-08-10) — de 4 vistas a 3, más un
    buscador que reemplaza a la Tabla para "¿cuánto tengo y dónde?".**
    El rail pasó de `Área y familia / Torta familias / Top por área
    (valor) / Top por área (cantidad)` a `Por área / Por familia / Buscar
    producto`. Motivo: el stacked bar de 20 áreas × 8 familias no se leía,
    la torta se rompía apenas una familia concentraba >70% (pasaba de
    verdad con datos reales: `COSTOS PRODUCCION` en ~80%), y Top
    valor/Top cantidad eran la misma vista con un flag `es_valor` interno
    duplicada en el rail — se unificaron en `_grafico_ranking`, reusado por
    Por área y Por familia. El selector de área de la vieja "Top
    por área" ordenaba alfabético y podía arrancar en un valor vacío
    (literalmente `"---"` en datos reales) — el reemplazo (`Buscar
    producto`) no tiene ese selector: lista todo ordenado por valorizado.

    **Ajuste posterior (2026-08-10, mismo día):** el toggle `Valor`/
    `Cantidad` de Por área/Por familia se sacó — ahí solo importa el
    valorizado, y cada barra muestra su % de participación sobre el total
    NETO en su lugar. Los 4 KPIs se consolidaron en 1 solo
    (`Valorizado total`), dentro de la card izquierda y no en una franja
    aparte (se probó así y quedaba la card muy abajo).

    **Buscar producto** resuelve dos preguntas con el mismo bloque
    (`_render_buscar_producto`): un producto puntual (ficha con
    cantidad+valorizado+precio promedio+unidad por área,
    `_ficha_producto`) o un grupo — Subfamilia — completo (todos sus
    productos, barra apilada Producto × Área,` _ficha_subfamilia`). Los
    dos `st.selectbox` (`inv_buscar_producto`/`inv_buscar_subfamilia`)
    son mutuamente excluyentes vía `on_change` que limpia el otro
    ANTES del rerun — mismo patrón que `_rail_set` en `graficos/base.py`.
    No reemplaza la Tabla (sigue siendo lo mejor para exportar o cruzar
    columnas raras): es el atajo de "necesito ver esto AHORA, en una
    reunión", sin abrir el panel de AgGrid ni armar un agrupamiento a
    mano.

    **Panel lateral contextual.** El panel de la derecha
    (`Mayor cantidad`/`Precio más alto`, top-10 genérico) se mantiene
    intacto en Por área/Por familia — ahí complementa el agregado con
    "qué productos puntuales pesan más". En Buscar producto ese mismo
    top-10 quedaba redundante (desconectado de lo que ya se ve a la
    izquierda para el producto elegido), así que se reemplaza por
    `_panel_relacionados`: otros productos de la misma Subfamilia (o
    Familia si no hay Subfamilia) que el seleccionado — nada que mostrar
    todavía si el usuario eligió un grupo completo (ya está todo a la
    izquierda) o no eligió nada.

    **Pendiente, NO implementado:** `Nombre Area` en datos reales mezcla
    ubicaciones físicas (`COCINA`, `SALON`, `CAVA`...) con cuentas
    contables (`GASTOS`, `PRUEBAS`, `BAJAS DE ALMACEN`...) — confirmado
    en vivo: el producto "Planilla De Movilidad" (no es stock físico)
    aparece bajo área `GASTOS`. Un filtro "Solo físicas" necesitaría una
    lista de qué áreas son cuentas, y esa lista es una decisión de
    negocio que no está tomada — no se hardcodeó una lista adivinada.
    Columnas nuevas resueltas (`col_subfam`, `col_unidad`) ya estaban en
    el demo de `_datos_demo` (`data.py`, rama `inventariovalorizado.parquet`)
    desde antes de este cambio — no hizo falta tocar `data.py`.

76. **Click-drill en Por área/Por familia (2026-08-10) — mismo patrón que
    `compras/familia.py`, con la trampa de key ya documentada en la regla
    del `CLAUDE.md` raíz (persistencia de `on_select` entre reruns).**
    `_grafico_ranking` ganó `clic=True`/`state_key`: clic en una barra la
    resalta (`ACENTO_FUERTE` vs `ACENTO`), guarda la categoría en
    `st.session_state[state_key]` (clic de nuevo la quita) y devuelve el
    foco al caller. El caller usa ese foco para (a) filtrar el panel
    derecho (`Mayor cantidad`/`Precio más alto`) a esa categoría — filtra
    `d` y re-alinea `_cant` con `.loc[d_panel.index]`, no recalcula desde
    cero — y (b) mostrar debajo `_grafico_detalle_foco`: el siguiente
    nivel (Área → Familia, Familia → Subfamilia), sin clic propio (dos
    niveles alcanza, y evita competir por la selección con el gráfico de
    arriba).

    **La key del gráfico principal incluye el foco DE ANTES del clic**
    (`f"{key}_{foco or 'none'}"`), no una key estática. Motivo: la
    selección de `st.plotly_chart(on_select=...)` persiste mientras la key
    no cambie, así que con key estática cada rerun posterior re-lee el
    mismo punto seleccionado y vuelve a togglear el foco → parpadeo
    infinito. Al cambiar el foco, la key cambia, el widget es "nuevo" para
    Streamlit y no arrastra la selección vieja — mismo truco que
    `compras_g_fam_time_{focus_fam}_..."` en `compras/familia.py`, solo
    que ahí el foco cambia el DATASET del propio gráfico (la key cambia
    como efecto colateral) y acá el foco no cambia el dataset del ranking
    principal (todas las áreas siguen ahí) — hay que meter el foco en la
    key a propósito, no viene gratis.

    Verificado en el preview local: el entorno de este proyecto no puede
    tomar `screenshot` ni clics por coordenada (pane sin compositing), así
    que el clic real se simuló disparando `gd.emit('plotly_selected',
    {points: [...]})` sobre el nodo `.js-plotly-plot` en DevTools/JS — la
    misma ruta que usa el componente de Streamlit para convertir un clic
    real en `evt.selection.points`. `plotly_click` NO sirve para esto:
    Streamlit registra su handler en `plotly_selected` cuando `on_select`
    trae `selection_mode="points"`, y el punto necesita `data`/`fullData`
    (la traza completa) o el handler revienta leyendo `legendgroup` de
    `undefined`.

77. **Tarjeta der desalineada con la izq (2026-08-10) — bug preexistente en
    `estilos/_20_compras_rail.py`, expuesto por la regla #76, no causado
    por ella.** `[class*="st-key-ajuste_graf_card_izq_"]` lleva
    `margin-top: -56px` para que la tarjeta arranque a la misma altura que
    el rail fijo (`.st-key-compras_tabs_row`, `top: 66px`) — ver comentario
    original de esa regla. La tarjeta der (`ajuste_graf_card_der_*`, usada
    por Compras — vistas Semanal/Vs año anterior — e Inventario) nunca
    tuvo el mismo jalón: en flujo normal las dos arrancan a la misma altura
    porque son hermanas de la misma fila, pero sin el jalón la der queda
    56px más abajo que la izq. No se notaba porque la diferencia es chica
    y ambas tarjetas suelen tener contenido de altura parecida — con el
    click-drill de la regla #76, la izq de Inventario creció mucho (barra +
    caption + gráfico de detalle) y el escalón saltó a la vista.

    Fix: mismo `margin-top: -56px` para `[class*="st-key-ajuste_graf_card_
    der_"]`, y su reset a `0` en el `@media (max-width: 900px)` de más
    abajo — sin el reset, en móvil (donde las columnas se apilan en
    columna) la der se monta encima de la izq. Verificado en vivo en las
    dos vistas reales que usan der (Compras/Semanal e Inventario/Por área
    con foco) y en viewport móvil (375px, sin solape). No es un cambio de
    Inventario: al vivir en `_20_compras_rail.py` (CSS compartido por
    prefijo de key), arregla las dos a la vez.

78. **"Buscar producto" (grupo/Subfamilia) mostraba ítems sin stock y en
    orden equivocado (2026-08-10).** `_ficha_subfamilia` armaba `g` con
    TODOS los productos de la subfamilia, sin filtrar los que no tienen
    nada — en un catálogo real son la mayoría (ej. CARNES: 188 productos
    catalogados, 39 con algo de stock/valorizado). Consecuencias: (a) el
    gráfico se llenaba de barras invisibles (val=0) que solo ensuciaban,
    y (b) como estaban empatadas en 0, `sort_values` las dejaba en el
    orden alfabético del `groupby` en vez de por importe — parecía "sin
    ordenar". Fix: filtrar a `(val != 0) | (cant != 0)` ANTES de calcular
    `orden` — no solo `val != 0`, para no esconder un producto con stock
    real pero precio 0 (dato real observado: "(P) Bife Angosto Arg 500gr"
    con cant>0 y val=0 exacto). Mismo filtro en `_ficha_producto` (ahí son
    ÁREAS sin ese producto, no productos). `k4.metric("Productos", ...)`
    NO se tocó — sigue contando el catálogo completo (188), a propósito:
    es "cuántos productos existen en este grupo", no "cuántos tienen
    barra"; el número más chico del gráfico de al lado es coherente con
    eso, no un bug nuevo.

    **Bug de orden aparte, no relacionado al filtro:** `_ficha_subfamilia`
    usa `px.bar(..., category_orders={"prod": orden})`, a diferencia de
    `_grafico_ranking` que arma un `go.Bar` con `y=lista literal`. Con
    `go.Bar`, el primer elemento del array `y` pinta ABAJO (comentario
    original, confirmado en vivo con la regla #76: la barra más grande
    quedaba arriba con `sort_values(ascending=True)`). Con
    `category_orders` de `px.bar` es AL REVÉS: el primer elemento del
    orden pinta ARRIBA — confirmado midiendo posición en pantalla
    (`getBoundingClientRect().top` de los ticks del eje Y), no leyendo el
    código: con `ascending=True` el producto más chico terminaba arriba y
    el más grande abajo. Con `ascending=False` (mayor primero) queda
    correcto. **No asumir que `category_orders` y un `y=` literal de
    `go.Bar` comparten convención de "primer elemento = dónde" — verificar
    en vivo cada vez que se toque uno de los dos.**

79. **Click-drill (regla #76) obligaba a hacer scroll para ver el detalle
    (2026-08-10, mismo día).** Con foco activo, `_grafico_ranking` seguía
    dibujando el ranking de arriba a tamaño completo (hasta 900px con
    muchas categorías — GASTOS, la más grande del dataset real, tiene 21
    áreas) y el detalle de abajo SUMABA otros ~360-900px: en una pantalla
    de 800px el bloque completo llegaba a ~988px, casi 200px de scroll
    para ver lo que el usuario acababa de pedir con el clic.

    Fix: `_grafico_ranking` gana `compacto` (parámetro explícito, para el
    detalle) y además se achica SOLO cuando `clic and foco` (el ranking ya
    cumplió su función — elegir la categoría — así que no necesita tamaño
    completo).
    - Sin foco / vista normal: `min(900, max(360, 34·n+60))` (el de
      siempre).
    - Ranking CON foco activo, o detalle (`compacto=True`): `min(280,
      max(190, 22·n+50))`.

    Con esto, GASTOS (el caso más grande del dataset real: 21 áreas en el
    ranking + 8 familias en el detalle) pasó de ~988px a ~774px de bloque
    total — para la mayoría de las categorías (menos filas) entra
    completo sin scroll. No hay forma de garantizar CERO scroll para
    absolutamente cualquier cantidad de filas sin sacrificar legibilidad;
    esto reduce el caso común y acota el peor caso, no lo elimina.
    También se acortó el caption de foco a una sola línea (mismo motivo,
    ahorra ~20px). El caption se terminó sacando del todo el mismo día
    (regla #80): el color de la barra en foco + el título del gráfico de
    detalle ya dicen qué está seleccionado.

    **Ajuste posterior, mismo día:** la primera versión usaba DOS fórmulas
    distintas — ranking `min(240, max(140, 20·n+40))` vs. detalle
    `min(420, max(200, 28·n+40))` — pensando en darle más protagonismo al
    detalle. Con pocas categorías en el ranking (Por familia: 8, o un
    Área/Familia filtrado a un puñado) pegaba contra el piso de 140px:
    el título quedaba encimado con la primera barra y el ranking se veía
    roto/mucho más chico que el detalle, no solo "ya cumplió su función".
    Unificadas a UNA sola fórmula para ambos casos — se ven como un par
    consistente, cada uno escalado por su propia cantidad de categorías,
    en vez de una jerarquía artificial de tamaños.

80. **Barra negativa dibujada a la izquierda descentraba el ranking
    (2026-08-10, mismo día).** En `_grafico_ranking`/`_ficha_producto`
    (barras horizontales de una sola serie), un valor negativo (área con
    ajuste/devolución neto negativo, ej. `BARRA: -S/ 1,750`) se pintaba
    hacia la izquierda de x=0 — mientras el resto de las barras arranca en
    x=0 y crece a la derecha. Con una sola barra "flotando" del otro lado,
    el eje quedaba descentrado (el rango tenía que cubrir negativo Y
    positivo) y la barra negativa no se comparaba visualmente contra las
    demás.

    Fix: TODAS las barras dibujan hacia la derecha (`x=np.abs(valores)`,
    largo = magnitud); el signo se lee por COLOR, no por dirección —
    `AJUSTE_NEG` (`#d97a72`, mismo tono que ya usa el heatmap de Ajuste
    para "negativo", `graficos/ajuste/_heatmap.py`) en vez de `ACENTO`, y
    `AJUSTE_NEG_TEXTO` en vez de `ACENTO_FUERTE` cuando esa barra negativa
    está en foco (click-drill de la regla #76). Texto de la barra y hover
    siguen mostrando el valor real CON signo (`_texto` ya usaba
    `serie.values` sin tocar; el hover necesitó `customdata` explícito
    porque el `x` del trazo ahora es el valor absoluto, no el real —
    `%{x}` en un hovertemplate hubiera mostrado el número sin signo).
    `_rango_con_holgura` también pasa a recibir el array de absolutos, así
    el eje arranca en 0 de verdad en vez de dejar hueco para el lado
    negativo que ya no existe.

    No tocado: `_ficha_subfamilia` (barra APILADA por área, color = área,
    no por signo — mismo patrón no aplica sin rediseñar qué representa el
    color ahí, y no era el caso reportado).

81. **Drill lateral en vez de apilado (2026-08-10, mismo día) — el detalle
    del click-drill (regla #76) pasa de col_izq a col_der, y el Top que
    vivía en col_der baja a una franja nueva debajo de las dos columnas.**
    Antes: con foco, `_grafico_detalle_foco` se apilaba DEBAJO del ranking
    en col_izq (regla #79 lo hizo compacto para que entrara sin scroll) y
    col_der seguía mostrando el Top de siempre, sin relación con el foco
    excepto un filtro. Ahora: col_der muestra el DETALLE (lateral, al lado
    del ranking) cuando hay foco, y el Top (`_panel_top`, extraído del
    bloque que antes vivía inline en `renderizar_graficos_inventario`) se
    dibuja en una tercera card (`ajuste_graf_card_abajo_inv`) debajo de
    las dos columnas — SOLO aparece con foco activo en Por área/Por
    familia; sin foco, layout de siempre (ranking en izq, Top en der).

    **Efecto en holgura del eje X:** el detalle ahora renderiza en col_der
    (~307-343px, contra los ~588px de la card izq) — el `factor=0.5` de
    `_rango_con_holgura` que alcanzaba en la card ancha dejaba la etiqueta
    de la barra más larga cortada contra el borde en la angosta (mismo
    síntoma que la regla #44, causa distinta: antes era la barra ocupando
    el 100% del ancho, ahora es la COLUMNA la que es angosta). `factor`
    pasa a `3.2` cuando `compacto=True` (el detalle siempre es
    `compacto`), verificado en vivo midiendo `getBoundingClientRect()` del
    texto vs. el borde del plot — la relación no es lineal (fracción de
    ancho para texto = factor/(1+factor), se acerca a 1 asintóticamente),
    así que se ajustó por prueba y medición en vivo, no por álgebra:
    0.5→47px de corte, 0.9→31px, 2.0→6px, 3.2→sin corte, probado con la
    barra dominante (GASTOS: una barra al 99.7%) y con valores más
    parejos (BARRA: seis barras entre 11% y 102%) para no asumir que
    arreglar un caso alcanza para el otro.

    `ajuste_graf_card_abajo_inv` hereda el estilo de card blanca por el
    selector wildcard `[class*="st-key-ajuste_graf_card_"]` de
    `estilos/_80_cards.py` sin CSS nuevo — y al NO matchear `_izq_` ni
    `_der_`, no hereda el `margin-top: -56px` de la regla #77 (correcto:
    esta card vive en flujo normal, no pegada al rail).

    **Trade-off de altura, a propósito:** el bloque total con foco activo
    creció (~774px → ~1074px en el caso GASTOS) porque el Top —antes en
    paralelo con el ranking, sin sumar altura— ahora se apila DEBAJO de
    las dos columnas. Pedido explícito del usuario (layout lateral +
    "top" abajo); si hace falta compactar el Top también, es un ajuste
    aparte, no implícito en este cambio.

82. **`_panel_top` pasa de 2 pestañas de mini-gráficos a UNA tabla AgGrid
    ordenable, con barra de "Participación %" + checkbox y "Selección %"
    en vivo (2026-08-10, mismo día) — pedido explícito del usuario.** No
    es un componente nuevo: reusa el patrón EXACTO que ya vive en
    `tablas/desktop.py` (líneas ~81-594, sección "Inventario Valorizado: 2
    columnas de % + checkbox de selección") para la vista Tabla de este
    mismo reporte — la barra-gradiente vía `cellStyle` (JsCode, no Styler
    de pandas — ese es el patrón de `compras/volatilidad.py`, sin
    checkbox, ver regla del CLAUDE.md), `configure_selection("multiple",
    use_checkbox=True, header_checkbox=True)`, y el `valueGetter` de
    "Selección %" que recalcula contra `getSelectedNodes()` en el
    navegador — CERO round-trip a Streamlit por click de checkbox.
    Diferencia con el original: "Participación %" es contra el total del
    FOCO actual (el `d_panel` ya filtrado), no el total general del
    reporte — coherente con el % que ya muestran las barras de
    `_grafico_ranking`. Top 20 por Valorizado (antes: dos tops de 10,
    cantidad y precio, por separado) — con columnas ordenables por header,
    "top por cantidad" y "top por precio" son la misma tabla vista con
    otro clic, así que las 2 pestañas quedaron redundantes y se sacaron.

    **Bug real encontrado al verificar (no al leer el código): la última
    columna ("Selección %") nunca renderizaba ninguna celda de dato** —
    el header aparecía, el contenedor central medía el ancho correcto
    para 6 columnas, pero cada fila solo tenía 5 `[role="gridcell"]`; un
    hueco vacío del ancho de una columna quedaba al final. Sobrevivió a
    sacar el `valueGetter` (no era eso), a sacar
    `fit_columns_on_grid_load` (no era eso), a apretar los `minWidth` (no
    era eso) — la causa era virtualización de COLUMNAS: AG Grid calcula
    qué columnas están "en el viewport visible" y probablemente lo hace
    ANTES de que el iframe de `st_aggrid` (un `st.components.v1.html`)
    se asiente en su ancho final dentro de Streamlit, dejando a la última
    columna fuera de ese rango para siempre — ni un `dispatchEvent(new
    Event('resize'))` manual sobre el iframe lo recalculaba. Fix:
    `grid_options["suppressColumnVirtualisation"] = True` — con una
    grilla chica (7 columnas, ~20 filas) no cuesta nada de performance
    desactivar la virtualización horizontal. **Si un AgGrid embebido en
    un panel angosto (no la Tabla principal a pantalla completa) muestra
    menos columnas de las configuradas sin ningún error en consola,
    sospechar de esto primero.**

83. **`_ficha_subfamilia` deja de desglosar por área (2026-08-10, mismo
    día) — pasa de barra apilada Producto × Área a UN bar por producto
    (sumado entre áreas), con precio + unidad + % de participación en la
    propia barra, y solo 2 KPIs.** Pedido explícito del usuario tras ver
    la ficha de un grupo (Subfamilia "AVES"): sacar "Cantidad total" y
    "Precio promedio" del KPI row (mezclaban unidades entre productos —
    kg, und, Lt — el número agregado no representaba nada real ni
    accionable) y tratar el negativo igual que el resto del dashboard
    (regla #80: a la derecha, `AJUSTE_NEG` en vez de `ACENTO`, magnitud
    en `x`, valor real con signo en `customdata`/hover).

    La razón por la que esta ficha había quedado AFUERA de la regla #80
    quince minutos antes ("no tocado: barra apilada por área, color = área,
    no por signo") dejó de aplicar: al sacar el desglose por área, el
    color queda libre para representar signo — ya no hace falta elegir
    entre "colorear por área" y "colorear por signo", esta ficha solo
    necesitaba lo segundo. Cambia de motor: `px.bar(color="area",
    barmode="stack")` → `go.Figure(go.Bar(...))` como el resto de los
    gráficos de este archivo (y la regla #78 sobre `category_orders` de
    `px.bar` pintando el primer elemento ARRIBA, al revés de `y=` literal
    de `go.Bar`, deja de aplicar acá — vuelve a `ascending=True`, mismo
    criterio que `_grafico_ranking`). `import plotly.express as px` se
    sacó del archivo: sin este uso era el último.

    Precio unitario se calcula por PRODUCTO (`valorizado_total /
    cantidad_total` agregados sobre todas sus áreas), no por fila —
    coherente con que la barra ya representa al producto entero. Si
    `cantidad_total` da 0 (valorizado sin stock, ej. un ajuste), el texto
    muestra "—" en la parte del precio en vez de dividir por cero.

84. **[SUPERADA por la regla #85 — el candlestick de esta regla se dio de
    baja el mismo día] "Resumen ejecutivo" de Ventas (2026-08-11) — port de
    un mockup tipo panel bursátil, con el candlestick construido de datos
    REALES, no decorativos.** El mockup original (React/Recharts) dibujaba un
    candlestick con apertura/máx/mín FALSOS (ruido aleatorio alrededor del
    total del día, solo para parecer un gráfico de acciones) y el cierre =
    total de venta del día. Portarlo tal cual habría metido un gráfico que
    miente — justo lo que este proyecto evita (`objetivo-vs-powerbi`: superar
    a un reporte plano con algo MÁS confiable, no más bonito). En cambio,
    `graficos/ventas_resumen.py::_resumen_ohlc_dia` reusa el criterio de
    `graficos/compras/volatilidad.py::_vol_ohlc_semana` (regla #74): OHLC de
    una magnitud REAL dentro de un período — ahí precio unitario/semana,
    acá línea de venta/día (apertura = primera línea del día, cierre =
    última, máx/mín = ticket de línea más caro/barato). Las 4 velas quedan
    en la MISMA unidad (S/ por línea), así que la geometría del candlestick
    es válida (máx ≥ máx(apertura,cierre), mín ≤ mín(...)) — mezclar el
    TOTAL diario (miles de soles) con el ticket de línea (decenas) habría
    roto esa invariante. A propósito, el candlestick NO compara día contra
    día (ese trabajo ya lo hace "Venta por día"): expone el arco propio de
    CADA jornada, de su primera venta a la última. Los KPIs ("Mejor día",
    "Días en alza") sí usan el TOTAL diario real (`g["total"]`, la suma de
    líneas, no el cierre de la vela) — dos señales distintas, cada una
    rotulada para no confundirlas.

    Igual que #74, la ventana se recorta a los últimos `MAX_DIAS=30` días
    CON datos (no calendario): el filtro de fecha de la franja es un TECHO,
    no la ventana en sí — con "Vs Compra"/"Matriz agrupada" ya se vio que
    Ventas admite rangos de más de un año.

    Sin precedente de clic confiable en `go.Candlestick` (regla #74), así
    que esta vista usa solo HOVER (`hovertext` + `hoverinfo="text"`, mismo
    patrón que volatilidad.py) — nada de overlay de captura de clic, y por
    lo tanto nada que requiera el smoke manual post-deploy de esa regla.

    **KPIs adentro de la card compartida, no arriba (a diferencia de la fila
    de Salidas, regla #38).** La fila de `st.metric` vive DENTRO de
    `with st.container(key="ajuste_graf_card_izq_ventas")`, como una rama
    más del `if/elif` que ya usan "Venta por día"/"Matriz agrupada"/etc. —
    no ENTRE los chips y esa card. El `margin-top: -80px` de la regla #38
    solo pisa contenido en flujo POR FUERA de esa card; adentro no aplica, y
    por eso esta vista no necesitó ningún CSS nuevo en `estilos/`.

    **Nueva categoría de rail `("Resumen", ...)` puesta PRIMERA** en
    `_VENTAS_RAIL_CATEGORIAS` (`ventas.py`) — pasa a ser la pestaña por
    default de Ventas (antes "Venta por día"). Decisión de producto, no
    técnica: el mockup original ES un panel de un vistazo pensado como
    landing, así que tiene sentido que sea lo primero que se ve. Fácil de
    revertir (mover la tupla) si no fuera lo que se quería.

    **Verificado en el navegador de desarrollo** (a diferencia del clic de
    #74, acá SÍ aplica: sin selección custom, todo es hover/render): con
    datos reales de R2 (no demo — el entorno tenía secrets configurados),
    los 3 gráficos renderizan sin excepción, los KPIs dan números
    sensatos, y el toggle Ingreso/Cantidad de "Top platos" cambia
    correctamente el ranking (por Cantidad ganan bebidas/hielo, por Ingreso
    platos de fondo — resultado esperado). Al alternar entre "Resumen
    ejecutivo" y otra vista del rail con un `wait` corto (~2s) entre clics
    programáticos, los charts del `@st.fragment` de Resumen quedaban
    HUÉRFANOS junto a los de la vista nueva — pero con un rerun completo
    ya asentado (~4s) el DOM queda limpio en ambos sentidos. Conclusión:
    fue el test disparando el siguiente clic antes de que el rerun de
    Resumen (el más pesado del rail: agrupa OHLC + 3 figuras Plotly)
    terminara de asentarse, no un bug del patrón `if/elif` +
    `@st.fragment` condicional — un usuario real, con foco en la UI en vez
    de JS disparando clics en ráfaga, no lo dispara. Si algún día un
    dashboard nuevo reporta huérfanos reales (reproducibles con clics
    reales, no programáticos), ahí sí aplica el remedio de la regla #70
    (`st.empty()`), pero no hizo falta acá.

85. **El candlestick de "Resumen ejecutivo" (regla #84) se dio de baja el
    mismo día — apertura/cierre "reales" no es lo mismo que apertura/cierre
    ÚTILES.** La regla #84 evitó el candlestick DECORATIVO del mockup
    original (OHLC inventado), pero el reemplazo (OHLC de la primera/última
    línea de venta del día) tenía el mismo problema de fondo por otra
    puerta: la primera y la última venta de un día no tienen ninguna
    relación causal entre sí — a diferencia de un precio de acción (donde
    apertura/cierre resumen el consenso de mercado al inicio/fin de una
    sesión continua), acá es esencialmente un sorteo. El color
    verde/rojo que produce esa comparación no lleva señal real, aunque el
    dato de origen sea 100% real y la geometría sea válida — "construido
    con datos reales" no es lo mismo que "dice algo verdadero". El usuario
    lo detectó solo mirando la explicación ("¿no sería poco útil comparar
    el primer registro con el último?") sin que hiciera falta debatir
    números.

    La mecha (máx/mín = ticket más caro/barato del día) SÍ tenía señal real
    — quedó descartada igual, junto con todo el candlestick, porque no valía
    la pena mantener la infraestructura de OHLC por una sola mitad útil sin
    que nadie la pidiera.

    **Reemplazo:** `go.Bar` de venta TOTAL por día — mismo criterio que ya
    usaba el KPI "Días en alza" (`g["total"].diff()`, hoy vs. ayer) en vez
    de apertura/cierre de transacciones sueltas. Un solo criterio para
    "sube/baja" en toda la vista (antes el candlestick y el KPI usaban
    definiciones DISTINTAS de "alza" sin decirlo — un lector atento podía
    notar que el color de una vela no coincidía con lo que el KPI contaba
    como día positivo). El primer día del rango no tiene día anterior:
    color neutro (`ACENTO`), ni verde ni rojo — no inventa una tendencia
    donde no la hay. `_resumen_ohlc_dia` (y sus 4 tests en
    `test_graficos.py`) se borraron enteros: la agregación diaria pasó a
    un `groupby("dia")["venta"].sum()` de una línea, sin función propia que
    valga la pena testear aparte.

    **Lección para la próxima vez que alguien proponga "candlestick" para
    un dato que no es una serie de precios continua:** preguntar primero
    QUÉ referencia real tienen apertura y cierre entre sí (¿son la MISMA
    magnitud en dos momentos comparables, tipo cierre de ayer → cierre de
    hoy? ¿o dos observaciones sueltas sin relación?). Si la respuesta es
    "dos observaciones sueltas", el candlestick es la forma equivocada
    aunque los 4 números sean reales — un `go.Bar` coloreado por la
    comparación que sí importa (día vs. día anterior, período vs. período)
    dice lo mismo con menos aparato y sin insinuar una relación que no
    existe.

86. **Comparativo diario vs Año Pasado (`graficos/ventas_comparativo.py`,
    2026-08-11) — "la misma fecha del año pasado" es AMBIGUO, y la
    ambigüedad es del negocio, no del código: por eso es un toggle
    visible.** 05/08/2026 es miércoles; 05/08/2025 fue martes. En un
    restaurante el día de semana es la variable que más pesa (viernes y
    sábado contra lunes), así que comparar por fecha calendario mezcla la
    señal que se busca con el ruido de estar comparando días distintos.
    Los dos modos conviven detrás de un `st.pills`:
    - **"Mismo día de semana"** (default): misma semana ISO + mismo día de
      semana del año ISO anterior (`date.fromisocalendar`). La fecha se
      corre ±3 días, el día de semana coincide siempre.
    - **"Misma fecha"**: mismo día/mes del año anterior. Se conserva porque
      es lo que hace cualquier comparativo de calendario (y lo que el
      usuario ve en su Power BI), pero el caption avisa explícitamente que
      el día de semana no coincide.
    Las etiquetas del eje X llevan el día de semana SIEMPRE (`Mié 05/08`,
    `_etiqueta_dia`) — en modo "misma fecha" es justo lo que deja ver el
    desfase de un vistazo, en vez de esconderlo.

    **Dos edge cases reales, con test de valor cada uno** (`test_graficos.py`):
    29-feb no existe en un año no bisiesto (cae al 28) y la semana ISO 53 no
    existe en la mayoría de los años ISO (cae a la 52 —
    `date.fromisocalendar(2025, 53, x)` lanza `ValueError`, no devuelve algo
    razonable). Sin la guarda, el gráfico revienta en unas pocas fechas al
    año: el peor tipo de bug, el que no aparece cuando lo probás.

    **El df del año pasado NO sale de `d`.** Ventas usa `carga_por_rango`
    (ver `REPORTES` en `data.py`), así que `d` trae SOLO el rango de la
    franja — el año pasado no está en memoria salvo que el usuario ensanche
    el rango a mano (que es la limitación que tienen hoy "Matriz agrupada" y
    "Ranking & FoodCost", ambas avisan "amplía el rango" cuando falta el año
    anterior). Acá se trae con `data.cargar_rango()` acotado al tramo
    equivalente (~2 semanas, no el parquet entero), así que el comparativo
    funciona sin pedirle nada al usuario.
    **Y se le aplican LOS MISMOS chips**, vía un `filtrar_cb` que
    `ventas.py` construye donde viven las selecciones (`_aplicar_chips`, que
    de paso reemplazó el filtrado inline — un solo sitio, dos consumidores).
    Sin eso, filtrar por Grupo daría barras actuales filtradas contra barras
    del año pasado SIN filtrar: dos números que no se pueden comparar, en un
    gráfico cuyo único trabajo es compararlos. Misma clase de bug que la
    regla #58 y que el que motivó `publicar_contexto_ia`.

    **Feriados hardcodeados** (`_FERIADOS_FIJOS_PE` + Jueves/Viernes Santo
    vía `_pascua`, algoritmo gregoriano anónimo). Es el calendario NACIONAL
    de Perú: no sabe de cierres del local, aniversarios ni feriados
    regionales. Si eso hace falta, tiene que pasar a ser un dato mantenido
    por el negocio, no una constante en el código — está anotado en el
    módulo. Los tests de `_pascua` clavan fechas conocidas (2024-03-31,
    2025-04-20, 2026-04-05) contra un almanaque real, no contra la propia
    salida de la función.

    **Un día se marca feriado si lo es este año O si lo era el día contra el
    que se compara — y la etiqueta DISTINGUE cuál** ("feriado" vs "feriado
    AP"). Encontrado verificando en el navegador, no razonando: con datos
    reales aparecían dos bandas ámbar y solo una era feriado de 2026. La
    otra era `Mié 05/08/2026`, que en modo día-de-semana se compara contra
    el 06/08/2025 (Batalla de Junín) — información útil (explica una barra
    lavanda anormal) pero que sin distinguir se lee como "hoy es feriado",
    que es falso. Las dos explican barras DISTINTAS: la morada o la lavanda.

    **Es un item propio del rail, no una pieza más del Resumen ejecutivo**
    (categoría "Tiempo", entre "Por día" y "Vs Compra"). El Resumen recién
    se había ajustado para entrar sin scroll (reglas #84/#85); meterle un
    gráfico de barras agrupadas con toggles habría deshecho eso.

    **Verificado en el navegador con datos reales de R2**, los dos modos: en
    "misma fecha" el 01/08/2026 se compara contra 01/08/2025; en "mismo día
    de semana", contra 02/08/2025 (sábado con sábado).

    **Granularidad día / semana / mes (agregado el mismo día).** El toggle de
    alineación aparece SÓLO en día: en semana y mes la pregunta se disuelve
    sola —una semana ISO completa trae un lunes, un viernes y un sábado, y un
    mes también, así que el ruido de día-de-semana se cancela al sumar— y no
    queda una segunda lectura razonable de "semana 32 contra semana 32". Las
    bandas de finde y la punteada de inicio de semana también son exclusivas
    de día (no hay día que sombrear en una barra que ya es un mes).
    Los feriados, en cambio, **no dejan de importar al agregar**: si un
    período tiene un feriado que su equivalente no tenía, el %Var mide con la
    vara torcida. Por eso en semana/mes se marca el DESBALANCE (`+1 fer.` /
    `−1 fer.`) en vez de descartarlos. No es teórico: verificando en el
    navegador apareció `−1 fer.` en S26 y `+1 fer.` en S27 porque San Pedro y
    San Pablo (29/06) cae en la semana 26 de 2025 y en la 27 de 2026. El caso
    grande es Semana Santa, que se muda de marzo a abril según el año —
    `test_graficos.py` lo clava con `_feriados_entre` (2024 en marzo, 2026 en
    abril).

    **Los DOS lados se cargan de R2, no de `d`.** Al agregar mensual quedó a
    la vista que usar `d` no alcanzaba: viene acotado al rango de la franja
    (1 del mes a hoy por defecto), así que pedir 12 meses habría mostrado un
    mes y medio. Ahora ambas series salen de `data.cargar_rango()` con el
    ancla en la última fecha con datos de `d` — la vista sigue mirando donde
    mira el usuario, pero la ventana la manda el selector. Efecto lateral
    bueno y visible: en día ya no se recorta a lo que haya en la franja (con
    9 días cargados y ventana 14, antes mostraba 9; ahora muestra los 14).
    La ventana se pide con `key=f"ventas_comp_ventana_{grano}"` — las
    opciones cambian con el grano y un `st.pills` que conserva un valor fuera
    de su lista nueva se queda sin selección (regla #9).

87. **Todo comparativo período-contra-período tiene que recortar el período
    EN CURSO — si no, el último dato miente y encima miente en grande.**
    Encontrado verificando `ventas_comparativo.py` en granularidad mes: con
    datos hasta el 09/08, "Ago 26" mostraba **−83%** contra agosto del año
    pasado. No era una caída de ventas: eran 9 días contra 31. El resto de
    los meses de la misma pantalla iban entre −15% y −44%, así que el −83%
    saltaba como el peor mes del año cuando en realidad era el artefacto más
    grande del gráfico.
    **Arreglo (`_rangos_comparables`):** cuando el período actual se pasa del
    ancla, se recorta al ancla Y se recorta el del año pasado a la MISMA
    cantidad de días — el "mes a la fecha vs. mismo tramo del año pasado" de
    cualquier BI serio. Con eso agosto pasó de −83% a **−40%**, en línea con
    los meses vecinos. La barra se marca "en curso" igual: la comparación ya
    es justa, pero el usuario tiene que saber que ese mes no está cerrado o
    lo lee como definitivo.
    **Consecuencia de diseño:** la agregación NO puede ser un
    `groupby(clave_de_período)`. La clave del año pasado sigue siendo
    "agosto" pero sólo hay que sumarle 9 días, así que se suma por RANGO
    explícito (`_serie_por_rangos` recibe `(clave, ini, fin)`) — un groupby
    por clave no tiene dónde expresar el recorte. Si alguien "simplifica"
    eso a un groupby, el −83% vuelve.
    El test fija la propiedad que importa —**ambos lados cubren la misma
    cantidad de días**— y no sólo las fechas concretas; es lo que hace justa
    la comparación, las fechas son el medio.
    Aplica igual a semana (una semana en curso son 3 días contra 7) y, en
    principio, a cualquier vista futura que compare períodos: Matriz agrupada
    y Ranking & FoodCost comparan por mes contra Año Pasado y **tienen este
    mismo sesgo sin corregir** en su mes en curso — no se tocaron acá, pero
    queda anotado.

88. **Modo "Descomposición" y drill a platos (2026-08-11) — la identidad
    `Venta = Pax × Ticket` es lo que hace legítimo poner tres series en UN
    eje.** El pedido original era "agregar pax o ticket al gráfico", y la
    respuesta obvia —una línea con eje secundario— es la equivocada acá por
    dos razones concretas, no por dogma: (a) el gráfico ya es una
    comparación año-contra-año, así que una línea de ticket necesitaría DOS
    líneas (actual y AP) para ser comparable, sobre 2 barras + etiquetas de
    valor + %Var + feriados + "en curso"; (b) ticket (S/ 175) y venta
    (S/ 636.000) obligan a un segundo eje.
    La salida es que los tres **porcentajes de variación** viven en la misma
    escala: `%Δventa`, `%Δpax` y `%Δticket` van juntos en un eje de %, sin
    eje secundario. Y contestan la pregunta que sigue a cualquier caída —
    *¿vino menos gente o gastaron menos?*— que son dos problemas distintos
    con soluciones distintas.
    **Validación fuerte y barata:** la identidad tiene que cerrar. Con datos
    reales, un día dio venta −14%, pax −30,4%, ticket +23,6%, y
    `0,696 × 1,236 = 0,860` ✓. Si el dedup de pax estuviera mal, la
    identidad NO cerraría — es un chequeo que detecta el bug más probable de
    esta vista sin necesidad de mirar el gráfico.
    Pax se deduplica por pedido (`max` por `Llave Local Pedido`, después
    suma), igual que en `ventas_resumen.py`: `Cant Pax` se repite por línea,
    sumarla cuenta la misma mesa una vez por plato. **Sin columna de pedido
    no hay dedup posible, así que pax queda VACÍO y el modo Descomposición
    ni se ofrece** — antes que mostrar un pax inflado.
    `_pct` devuelve `None` (no 0) cuando no hay base: un período sin dato del
    año pasado deja un HUECO en la línea; un 0 se leería como "no cambió",
    que es una afirmación falsa.

    **Drill:** clic en una barra → ranking de platos de ESE período, Actual
    vs AP, con `%Var` por producto. Carga sólo los dos tramos del período
    clickeado, no la ventana entera. Los productos que existen de un lado y
    no del otro se conservan con 0 (y `—` en `%Var`): que un plato haya
    entrado o salido de la carta es justamente lo que se quiere ver.
    Sigue el patrón de clic de `proveedor.py`/`volatilidad.py`: `_first_point`
    + dedup del `point_index` contra `session_state`, **y el foco en la key
    del chart** (`ventas_g_comparativo_{vista}_{grano}_{foco}`) — sin eso la
    selección persiste entre reruns, el mismo clic se reprocesa y el panel
    parpadea abriéndose y cerrándose (CLAUDE.md).

    **Qué se verificó y qué no.** El clic en sí **no se pudo probar**
    (regla #12: la selección de Plotly no se simula desde JS, y el
    screenshot no funciona en este entorno — mismo límite que dejó la regla
    #74 pendiente de smoke manual). Lo que SÍ se ejercitó, que es donde
    estaba el riesgo real, fue el camino de datos del drill: un probe suelto
    llamó a `_ranking_platos` con el rango real de agosto contra su
    equivalente 2025 y devolvió 8 productos ordenados, con casos de `AP = 0`
    (platos nuevos) incluidos. **Falta el smoke manual del clic
    post-deploy.**

    **Trampa encontrada al escribir ese probe, que vale para cualquier
    consulta suelta contra estos parquets:** las columnas reales de
    `ventas.parquet` están en MAYÚSCULAS (`VENTA ITEM DDOCUMENTO`,
    `NOMB ITEM VENTA`). El código de la app nunca las hardcodea —
    `buscar_columna` devuelve el nombre tal cual está en el df, así que
    `col_venta` ya viene en mayúsculas y calza con el df crudo de R2. Un
    script de prueba que escriba los nombres a mano en Title Case falla con
    un `None` silencioso que parece un bug de la app y no lo es.

    **La tabla del drill sumó Grupo / Sub Grupo y la cantidad del año
    pasado** (pedido del usuario al verla con datos reales). Dos decisiones
    que NO son obvias:
    - **Grupo/Sub Grupo se resuelven POR PRODUCTO (la moda), no se agregan a
      la clave del `groupby`.** Agrupar por los tres campos parece más
      correcto, pero si un plato cambió de grupo entre los dos años saldría
      partido en dos filas —una con sólo Actual y otra con sólo AP, ambas
      con `—`— que es exactamente lo contrario de lo que el drill busca. La
      jerarquía sale del período actual y, para los platos que ya no
      existen hoy, del año pasado. Se usa la moda y no `first` para que una
      fila mal cargada no decida el grupo del producto.
    - **Orden de columnas:** jerarquía → plata + `%Var` → cantidades. Las
      cantidades van al final a propósito: con dos pares AP/Actual
      intercalados (venta AP, cant AP, venta act, cant act) la tabla se
      vuelve ilegible. Y sirven — con datos reales apareció un plato con
      `+0%` de venta pero 73 → 71 unidades: vendió dos platos menos por más
      plata cada uno, o sea subió el precio. Eso no se ve mirando sólo la
      columna de soles.

89. **`Styler.format(...)` NO aplica el formateador a los `None` de una
    columna `object`: los pinta como el literal `"None"`.** Bug real y
    visible en producción (tabla del drill de `ventas_comparativo.py`): la
    columna `%Var` se armaba con una list comprehension que devolvía
    `float` o `None`, pandas la tipaba como `object`, y el
    `lambda v: "—" if pd.isna(v) else ...` **nunca corría** para los `None`
    — la celda mostraba `None` en la pantalla del usuario. Los valores
    numéricos SÍ se formateaban, así que la columna se veía medio bien y el
    bug pasaba por "dato faltante" en vez de por error de formato.
    **Dos arreglos, y conviene poner los dos:** (a) que la columna sea
    `float` con `NaN` en vez de `object` con `None`
    (`pd.to_numeric(..., errors="coerce")`), y (b) pasar `na_rep="—"` a
    `.format()`, que es el mecanismo explícito de pandas para el faltante y
    no depende de que el formateador lo maneje.
    **Cómo se verifica sin navegador** (es un bug de RENDER, así que mirar
    el DataFrame no alcanza — el df estaba bien): renderizar el Styler a
    HTML en un probe y buscar el literal, `assert ">None<" not in
    sty.to_html()`. Es la misma clase de verificación que la regla #25:
    contra el resultado real, no contra la intención.

90. **Para mover UN widget, el ancla es la key del PROPIO widget — no hace
    falta (ni conviene) envolverlo en un `st.container(key=...)`.**
    Todo `st.pills/button/selectbox/...(key="X")` emite `st-key-X` en su
    element container. Eso YA es un ancla de estilo local y acotada:
    `div[class*="st-key-X"] { margin-top: -4px; }` mueve ese widget y nada
    más. Suena obvio escrito; no lo fue en el momento.

    **Los dos errores encadenados que motivan esta regla (2026-08-12),
    porque el segundo es el instructivo:**
    - **Error 1 — mover el ancestro.** Pedido: "subí un poco el toggle de
      Por día". Se tocó el `margin-top` de `ajuste_graf_card_izq_ventas`
      (la tarjeta), porque era el margen que el inspector mostraba a mano.
      Subió el toggle, sí — y con él las 10 vistas del rail de Ventas. El
      usuario lo detectó preguntando "¿subiste sólo lo que te mencioné o
      subiste más contenedores?".
    - **Error 2 — el diagnóstico equivocado del error 1.** Se concluyó que
      "no existía una palanca local" y que había que **crear** un
      `st.container(key="ventas_dia_toggle")` alrededor del `st.pills`.
      Falso por partida doble: (a) la palanca ya existía
      (`st-key-ventas_dia_metricas`), y (b) el container extra reintrodujo
      la **regla #70** — un contenedor con key tiene identidad estable y
      RETIENE hijos huérfanos. Medido: el wrapper quedó de **250px** de
      alto con 5 hijos (las pills de 32px + **4 `stColumn` sobrevivientes**
      de la fila de KPIs del Resumen ejecutivo, `flex-basis: calc(20% -
      16px)` = las columnas de un `st.columns(5)`), y el `<hr>` separador
      se fue de `top:115` a `top:329`.

    **Regla de decisión, en orden:**
    1. ¿El widget tiene `key`? → estilar `div[class*="st-key-<key>"]`.
       Fin. (Este caso.)
    2. ¿Es un grupo de widgets que se estilan juntos y **siempre** se
       renderizan juntos? → ahí sí un `st.container(key=...)`, sabiendo que
       hereda el riesgo de la regla #70 si el grupo es condicional.
    3. Tocar el margen de un ancestro **sólo** si el ancestro ES lo que hay
       que mover. Antes de hacerlo: mirar la línea "Cadena de contenedores
       st-key" del inspector y preguntarse *qué más vive adentro*.

    **Verificación que distingue un caso del otro** (la que faltó la
    primera vez): medir el ancestro compartido ANTES y DESPUÉS. Si
    `getComputedStyle(tarjeta).marginTop` cambió, movió más que el widget.
    Acá el cierre correcto dio: tarjeta en `-56px` y `top:66` (idénticos a
    antes), ancla del toggle en `-4px`, altura del ancla **32px** (no 250)
    y un solo hijo — o sea, sin huérfanos.

    **El inspector aprendió la lección (mismo día).** Los tres errores de
    arriba fueron todos "elegí el selector equivocado", y el inspector
    tenía los datos para evitarlo pero no los presentaba como decisión: la
    cadena `st-key` salía como texto plano, sin distinguir el ancla propia
    del ancestro ni decir qué había adentro de cada uno. Se agregaron a
    `inyecciones/_inspector_js.py` (`anclaPropia`, `pesoAncestros`,
    `selectoresCompartidos`):
    - `ANCLA PROPIA (estila SOLO este widget): div[class*="st-key-<key>"]`,
      **primera línea** del bloque y antes de la cadena, a propósito.
    - `Contenedores que lo ENVUELVEN: st-key-X (N widgets adentro)` — sólo
      ancestros; contar los hijos del propio contenedor del widget da 0 y
      se lee como "está vacío" (se probó, se corrigió).
    - `AVISO` con las reglas **wildcard por familia** que estilan al
      ancestro. **Trampa al implementarlo:** el primer intento filtraba por
      "captura ≥ 2 elementos en el DOM" — pero la app renderiza UN reporte
      por vez, así que un wildcard que cubre los 5 devuelve 1 y el filtro
      mataba justo el caso a detectar. La señal correcta es el SELECTOR
      (está escrito por prefijo, no por la key), no cuántos matchean ahora.
    Va diferido a la tecla **C** porque recorre `document.styleSheets`,
    misma convención que `conflictos`/`matcheantes` (no en cada mousemove).
    Verificado sobre el mismo toggle del bug: marca
    `ajuste_graf_card_izq_*` y `ajuste_graf_card_*` como familias.

91. **Un legend de Plotly que "no se ve" casi nunca está apagado: está
    compitiendo con otra cosa en la misma franja
    (`graficos/ventas_comparativo.py`, 2026-08-12).** El usuario reportó
    "no veo la funcionalidad para ocultar/mostrar". Eran DOS causas
    distintas encadenadas, y confundirlas costó tres idas y vueltas:
    - **Primero sí estaba apagado**: `showlegend=not es_desc` dejaba la
      vista Descomposición sin legend, con el comentario "el panel Detalle
      lo reemplaza". Pero ese panel era **texto estático** — nunca tuvo el
      clic-para-ocultar. O sea que la capacidad no existía, no es que
      estuviera escondida. Moraleja: si un comentario dice "X reemplaza a
      Y", verificar que X hace lo que Y hacía, no sólo que ocupa su lugar.
    - **Después ya se dibujaba pero era ilegible**: en `y=1.02`, 12px y
      gris, quedaba en la MISMA línea horizontal que las anotaciones
      `feriado`/`feriado AP` (`y=1.0, yref="paper"`) y se leía como una
      anotación más del gráfico. Se subió a `y=1.12` con fondo + borde.

    **Cómo terminó (pedido del usuario): en Descomposición NO hay legend.**
    El control son los checkboxes del panel "Detalle", que además muestran
    el valor absoluto — tener legend Y panel era decir lo mismo dos veces.
    El legend nativo queda sólo en Montos, y el margen superior es
    condicional (`_legend_on`): reservar 95px para un legend que no existe
    es aire muerto.

    **El patrón para que un widget de ABAJO controle una figura de
    ARRIBA:** la figura se arma antes que el panel, así que el valor se lee
    de `st.session_state` (donde el widget lo dejó en el rerun anterior)
    con `.get(clave, default)`, y el default se declara en el **`value=`
    del propio widget**.

    **`st.session_state.setdefault()` NO sirve para sembrar el default de
    un `st.checkbox`** — se intentó primero y falló en silencio: el
    checkbox se dibujaba DESTILDADO mientras la figura mostraba las tres
    series (medido: `plot.data` con `visible: true` en las tres y los tres
    `input.checked === false`). El widget ignora el valor pre-sembrado y
    usa su propio default. Widget y gráfico terminan diciendo cosas
    distintas, que es justo el bug que la regla de "un solo dueño del
    valor" busca evitar. Un solo dueño: el widget (`value=True`), y el
    resto lee con `.get(..., True)`.

    Ojo con el corolario de "un widget que deja de renderizarse
    pierde su estado" (§ regla del `date_input` de la franja): al
    pasar a Montos los checkboxes dejan de renderizarse y su estado se
    purga, así que volver a Descomposición reinicia todo en visible —
    aceptable acá, pero es el comportamiento, no un bug.

    **Al ocultar una serie hay que sacarla también de la ESCALA.** `_tope`
    (que posiciona "en curso" y el %Var) se calcula sólo sobre las series
    visibles: dejar el máximo de una curva oculta reserva aire para algo
    que no se dibuja y aplasta lo que queda.

92. **Fechas horizontales en un eje categórico: el arreglo no es
    `tickangle=0`, es partir la etiqueta (mismo módulo, 2026-08-12).**
    Pedido: "el texto de la fecha no debe estar en diagonal sino
    horizontal". Poner `tickangle=0` solo **se pisa**: medido en el
    navegador, "Mié 29/07" mide ~56px y a 14 barras hubo 5 pares
    solapados. Dos cosas lo resuelven:
    - En día y semana el prefijo baja a su propia línea (`Mié<br>29/07`,
      `S32<br>05/08`): mismo texto, la mitad de ancho. Se arma con
      `tickmode="array"` + `ticktext` y **no** tocando `etiquetas`, que
      siguen siendo la categoría real — meter `<br>` en la categoría lo
      filtraría al header del hover (`hovermode="x unified"`) y a
      `_etiqueta_clave`, que también nombra el panel "Detalle" y está
      clavada en `test_graficos.py`.
    - Con muchas barras se muestra una cada `_paso = ceil(n/MAX_ETIQUETAS)`.
      A 30 días quedan 10 etiquetas, cero solapamientos; a 14 o menos el
      paso es 1 y no cambia nada.
    Verificado midiendo cajas de texto en el DOM a 1912px en día 14, día 30
    y mes: 0 pares pisados y 0 textos cortados.

93. **El cuadradito de color ES el checkbox — cómo estilar la caja de
    `st.checkbox` sin depender de clases con hash (2026-08-12).** El panel
    "Detalle" tenía DOS cosas por fila: un `<span>` pintado a mano (el
    swatch) y un checkbox al lado. El usuario pidió una sola. La caja
    visual de `st.checkbox` es el **único `<div>` hijo del `<label>` que NO
    tiene `data-testid`** (el otro es `stWidgetLabel`) — se ancla por
    ESTRUCTURA, no por su clase `st-emotion-cache-*`, que lleva hash y
    cambia entre versiones:

    ```css
    [data-testid="stCheckbox"] label > div:not([data-testid])
    ```

    El color entra por una variable (`--sw-color`) que fija el container de
    cada fila; marcado = relleno, sin marcar = sólo contorno, vía
    `label:has(input:checked)`. Venta tiene DOS variantes de key
    (`_pos`/`_neg`) porque su color sigue el signo, como su barra: el CSS
    es estático, así que la única forma de un color dinámico es que Python
    elija entre variantes ya escritas. **La key del checkbox NO puede
    llevar el signo** — si cambia, el widget pierde su estado (regla #9);
    el signo va en un container aparte que sólo existe para eso.

    **Al medirlo, `getComputedStyle` mintió** (mismo caso que ya está
    anotado para `letter-spacing`): la caja tiene
    `transition: background-color .1s`, y leer el fondo justo después de un
    cambio devuelve el valor VIEJO — un checkbox destildado seguía
    reportando el color relleno, y hasta un `background-color: magenta
    !important` inline leía cian. Se mide anulando la transición y forzando
    reflow antes de leer:

    ```js
    el.style.setProperty('transition','none','important');
    void el.offsetWidth;
    getComputedStyle(el).backgroundColor;   // ahora sí, el valor real
    ```

    Con eso: marcado → color sólido, sin marcar → `rgba(0,0,0,0)`.

    **Filas juntas:** el aire no estaba en la fila (24px) sino en el **gap
    de 16px** entre bloques, más que la fila misma. `st.container(gap=None)`
    lo saca; con la caja de 12px la fila baja a 15px. De 40px por fila a 15.

94. **`persist="disk"` en la caché de datos, y por qué una descarga lenta se
    volvía "R2 caído" (2026-08-12).** `_cargar_cacheable` /
    `_cargar_rango_cacheable` / `_rango_fechas_cacheable` cacheaban SOLO en
    memoria del proceso. Dos consecuencias que costaron una sesión entera:
    - Cada reinicio del server volvía a bajar el parquet. `ventas.parquet`
      son ~220k filas y ~40s en frío.
    - Peor: si alguien toca algo mientras baja, Streamlit **cancela el run**
      (`StopException`) y la descarga arranca de CERO. Con un navegador
      automatizado clickeando cada pocos segundos, nunca terminaba: la app
      mostraba "No se pudieron cargar los datos o el archivo está vacío" una
      y otra vez. Parecía R2 caído; R2 estaba perfecto (el mismo
      `data.cargar('ventas.parquet')` fuera de Streamlit devolvía las
      220.481 filas, sólo que tardando 40s).
    `persist="disk"` (el `ttl` se sigue respetando, verificado en 1.59) hace
    que sobreviva al reinicio. **No cambia el split cacheada/wrapper** de la
    regla del None cacheado: sólo se persiste el éxito, porque la función
    interna sigue LANZANDO ante un fallo.
    Corolario para diagnosticar: si "no cargan los datos", antes de sospechar
    de R2 probar `python -c "import data; print(len(data.cargar('x.parquet')))"`.
    Si eso trae filas, el problema es cancelación de runs, no la nube.
    (Lo agrava que `perf.py::phase` reviente al desenrollarse una
    `StopException` y REEMPLACE la excepción real por un `TypeError` — queda
    un "Uncaught app execution" que apunta al lugar equivocado.)

95. **`herramientas/ver_figura.py`: ver un gráfico sin navegador, y por qué
    hacía falta (2026-08-12).** Medir el DOM prueba que un gráfico
    **funciona**; nunca que **se ve**. Toda la saga del legend de la regla
    #91 —tres rondas— pasó por eso: el elemento existía, respondía al clic y
    era ilegible. Un PNG lo habría mostrado en 10 segundos.

    El script **no levanta Streamlit**: parchea en caliente las funciones de
    UI del módulo `st` ya importado (widgets → devuelven su default,
    contenedores → un context manager vacío, `plotly_chart` → guarda la
    figura). Se parchea el módulo REAL en vez de reemplazarlo en
    `sys.modules` a propósito: así `st.secrets` y `@st.cache_data` siguen
    siendo los de verdad y los datos salen de R2 como en producción.

    **Tres cosas que no son obvias y costaron intentos:**
    - `st.session_state` no funciona fuera de `streamlit run`, y de ahí sale
      el item activo del rail (`_render_rail` lo lee). Hay que reemplazarlo
      por un dict; se siembra con los `-s` para poder elegir la vista.
    - `@st.fragment` se aplica al IMPORTAR, así que los stubs tienen que
      instalarse **antes** de `import graficos`. El resto de las llamadas se
      resuelven contra el módulo en cada invocación y dan igual.
    - **El tamaño va en el LAYOUT, no como kwarg de `write_image`.** Por
      kwarg, kaleido no ajusta márgenes y RECORTA las etiquetas — el PNG
      mostraba un eje Y sin números que en el navegador está completo
      (comprobado contra el DOM). Aun con el layout hace falta forzar
      `automargin` en ambos ejes, porque los dashboards usan márgenes
      apretados (`l=10, b=10`) confiando en que Plotly los expanda solo, y
      kaleido no lo hace. **Efecto lateral honesto:** los márgenes del PNG
      NO son fieles al píxel. Sirve para composición, colores, solapamientos
      y legibilidad; para juzgar recortes, el navegador manda.

96. **El item del rail viaja en `?vista=`, y el detector de solapamientos
    tenía que mirar los TRES `svg` (2026-08-12).** Dos herramientas del
    mismo día, las dos nacidas de la misma friccion: llegar a una pantalla
    concreta y saber si se ve bien.

    **Deep-link (`graficos/base.py::_render_rail`).** La URL sólo decía el
    reporte; llegar a una vista eran 3-5 clics encadenados, cada uno con su
    rerun, y no había forma de compartir "mirá ESTA pantalla". Ahora el rail
    —que es COMPARTIDO, así que vale para los 6 dashboards con una sola
    edición— lee `?vista=` cuando todavía no hay selección válida y espeja
    la selección a la URL después de dibujar los botones.
    - Se **escribe** con `_slug_url()` (ASCII, sin acentos:
      `comparativo_vs_ano_pasado`) para que se pueda tipear a mano. NO se
      reusó `_slug`, que alimenta keys de widgets y por lo tanto selectores
      de `estilos/`: cambiarlo movería CSS de sitio.
    - Se **lee** con `_norm` (ignora acentos Y separadores), así entra igual
      `comparativo_vs_ano_pasado` que `Comparativo vs Año Pasado`.
    - Cambiar de reporte con un `?vista=` ajeno NO rompe: `_render_rail` ya
      valida contra `_todos` y cae al primer item, y el espejo reescribe la
      URL. Verificado saltando de Ventas (`venta_por_dia`) a Ajuste → queda
      `vista=cascada`.
    - Escribir `st.query_params` no dispara rerun, pero se compara antes:
      reescribir en cada rerun es ruido.

    **`herramientas/auditar_graficos.js`.** El chequeo de "¿algún texto se
    pisa o se corta?" se escribió a mano cinco veces en una sesión. Al
    convertirlo en herramienta aparecieron dos defectos que las versiones
    ad-hoc tenían y que invalidaban parte de lo verificado:
    - **Plotly usa VARIOS `svg.main-svg`** (datos/ejes + un "infolayer" con
      anotaciones, legend y títulos). Mirar sólo el primero deja ciegas a
      las anotaciones — justo `feriado`, `en curso` y el `%Var`. Se detectó
      plantando dos textos en el mismo punto y viendo que el chequeo NO los
      reportaba. En la vista de Ventas eran 48 textos vistos contra 67
      reales: 19 invisibles para el detector, y encima los solapamientos
      entre capas son los más fáciles de producir.
    - **Sólo miraba recorte arriba/abajo**, no por los lados. El eje Y
      cortado por izquierda no lo habría visto nunca.

    **Trampa al usarlo:** después de cambiar el tamaño de la ventana hay que
    RECARGAR. Plotly no re-maquetea solo, el `<svg>` conserva el ancho viejo
    y el chequeo reporta textos "cortados" que están perfectos — pasó con 25
    falsos positivos que desaparecieron con un F5.
    Con todo corregido, el comparativo de Ventas da 0 pisadas y 0 recortes
    sobre los 67 textos, a 1912px y a 1280px.

97. **Unificación Receta Base + Receta Venta bajo un solo ítem de nav
    "Recetas" (2026-08-13).** Hasta acá eran dos reportes sin relación
    visible: Receta Venta tenía dashboard propio (Sankey/Composición/
    Ranking/Ingredientes/Panorama), Receta Base solo tabla. El pedido: un
    ícono, con un chip Base/Venta adentro, y que Base tenga los mismos 5
    gráficos que Venta (paridad).

    **Los dos parquets son el MISMO tipo de dato — un BOM (lista de
    materiales): contenedor → insumos, con cantidad y costo.** Venta es
    `Nomb Plato → Item Rv` (plato vendido → sus insumos); Base es
    `RB NOMBRE → INSUMO` (subpreparación/mise en place → sus insumos).
    Confirmado que NO se cruzan entre sí (0% overlap `COD RB` vs `COD INS`,
    memoria de proyecto `esquema-real-compras-recetaventa`): dos catálogos
    de insumos independientes que cuelgan de `compras.COD_PRODUCTO` cada
    uno por su lado. Por eso la paridad se dio SACANDO la lógica de los 5
    gráficos de `recetaventa.py` a `graficos/recetas_comun.py`,
    parametrizada por nombre de columna (`col_contenedor`/`col_item`/
    `col_valor`) y por las etiquetas de cada dominio ("Plato" vs "Receta
    base", "Ingrediente" vs "Insumo") — UNA sola copia de cada gráfico,
    reusada por `recetaventa.py` y el `recetabase.py` nuevo (ambos capas
    finas: resuelven columnas reales + arman el rail).

    **El "ícono único con chip adentro" NO fusiona los dos reportes en un
    solo `REPORTES[...]` — siguen siendo DOS entradas reales**, cada una
    con su propio `archivo`/`cfg`. La fusión es puramente de PRESENTACIÓN,
    en dos capas:
    - `data.py::REPORTES`: ambas entradas llevan `"grupo_nav": "Recetas"`
      (clave genérica, reusable por cualquier grupo futuro).
    - `navegacion.py::inject_navegacion`: dibuja UN botón por `grupo_nav`
      en vez de uno por entrada, que navega al **último miembro visitado**
      (`session_state["_ultimo_<grupo>"]`, sembrado cada vez que el reporte
      activo pertenece al grupo) — nunca al primero a ciegas, o el rail
      "olvidaría" en qué sub-reporte estaba el usuario.
    - Adentro de cada dashboard, `graficos/recetas_comun.py::_chip_fuente`
      dibuja el segmented control "Receta base / Receta venta". Clic en el
      lado NO activo **NAVEGA** (`session_state["_nav_reporte"] = destino;
      st.rerun()`) — el MISMO mecanismo que el rail — en vez de refiltrar
      un df: como los dos parquets no comparten esquema, "cambiar de
      fuente" tiene que recargar TODO el reporte (cfg, archivo, columnas,
      refresco), no solo repintar. Esto evitó tocar un solo `if` en
      `app.py`: `cfg = REPORTES[reporte]` sigue siendo la única fuente de
      verdad de qué parquet cargar, exactamente como para cualquier otro
      reporte.

    **Por qué la key del chip incluye `reporte_activo`
    (`f"recetas_fuente_chip_{reporte_activo}"`):** si el usuario entra a
    Receta Base por el RAIL (no por el chip) viniendo de otro reporte, una
    key fija dejaría "pegado" el `default=` de la sesión anterior — mismo
    síntoma que la key de `st.plotly_chart(on_select=...)` de la regla de
    Ajuste (ver § Streamlit del CLAUDE.md). Incluir el reporte activo en la
    key fuerza un widget nuevo con el default correcto cada vez.

    **Descubierto al generalizar — TRES formatos de "activo" distintos
    para la MISMA intención, confirmado contra R2 real (no el demo, que
    hasta este cambio no tenía bloque propio para estos dos parquets):**
    | Parquet | Columna | Activo | Inactivo |
    |---|---|---|---|
    | recetaventa | `ITEM VENTA ACTIVO` | `ACTIV` | `INACTIV` |
    | recetaventa | `INS ACTIVO` | `ACTIV` | `INACTIV` (13 filas en blanco) |
    | recetabase | `RB ACT` | `RB.ACTIV` | `RB.INACT` |
    | recetabase | `INS ACTIVO` (**mismo nombre**, formato DISTINTO) | `INS.ACT` | `INS.INAC` |

    El filtro original de Receta Venta (`.str.startswith("ACTIV")`) no
    sirve para los dos de Base — ninguno arranca con "ACTIV" por el
    prefijo. `graficos/recetas_comun.py::_activo()` normaliza los cuatro
    con una sola regla (la sub-cadena `"INAC"` SÍ es estable en los cuatro
    formatos) y trata vacío/`None`/`NaN` como "no confirmado activo" (con
    `serie.isna()`, no un match de texto — `.astype(str)` serializa `None`
    y `NaN` distinto: "None" vs "nan"). Verificado que reproduce EXACTO el
    conteo que ya tenía Receta Venta en producción (1200/2713 filas)
    antes de generalizar. Test de valor en `test_graficos.py` (`_pruebas_puras`),
    fijando los 4 formatos + `None` para que un futuro "simplificar este
    if" no vuelva a romperlo en silencio.

    **Verificación:** `herramientas/ver_figura.py` para las 5 vistas de
    cada dashboard contra R2 real (`-s rb_graf_tipo=...` / `-s
    rv_graf_tipo=...`), incluyendo Panorama de compras (cruce real contra
    `compras.parquet` por `COD INS RB`). Cifras cruzadas con una consulta
    SQL directa a R2 (`RB COSTO` de "(Rs) Cordial De Chirimoya" =
    S/ 2.726,91, idéntico en SQL, PNG de `ver_figura.py` y la app corriendo
    en el navegador). Nav-grouping y el chip verificados en vivo
    (`streamlit run`, no solo el DOM): un ícono "Recetas", clic navega al
    último sub-reporte visitado, el chip cambia de Receta Venta a Receta
    Base con re-render completo (rail con vocabulario propio: "Insumos"
    en vez de "Ingredientes", "RECETA BASE" en vez de "PLATO").

98. **Unificación Requerimientos + Salidas bajo un solo ítem de nav
    "Movimientos" (2026-08-13), y por qué NO es una repetición mecánica de
    la regla #97.** El pedido fue el mismo patrón que Recetas, pero acá los
    dos parquets NO son el mismo tipo de dato con 0% overlap — son las DOS
    MITADES de un flujo real: Requerimiento es lo que Almacén Central le
    entrega a un área de producción (Cocina/Barra/Pastelería/...); Salidas
    es la baja que esa misma área registra después (consumo/merma/evento —
    `Tipo Descargo`). Confirmado con DuckDB directo contra R2 real (no
    demo, que hasta este cambio caía al bloque genérico de `_datos_demo`):
    **726 de los 968 productos de Salidas (75%) también aparecen en
    Requerimientos** — hay overlap real, a diferencia de Receta Base/Venta.
    Eso habilitó una vista adicional que Recetas nunca tuvo: un
    comparativo que cruza los dos parquets.

    **Requerimientos no tenía dashboard de gráficos — era una rama de
    despacho aparte en `app.py::_render_contenido`** (`if reporte ==
    "Requerimientos"`, con una tabla pivote propia, `_render_requerimientos`,
    y su propio flag `es_requerimientos` en `tablas/desktop.py`: deriva
    Mes/Año para el Modo pivote de AG Grid, `grandTotalRow` en vez de fila
    anclada, tema oscuro del side-panel). Para que quedara a la par de
    Salidas (que sí tenía dashboard) se le creó `graficos/requerimientos.py`
    — mismo layout que `salidas.py` (chips Sub Almacén/Familia en la
    franja + rail derecho), pero **NO se tocó ni una línea de la lógica de
    pivote**: se preservó detrás de un callback nuevo,
    `app.py::_cb_requerimientos_tabla`, registrado en `_TABLA_CB["Requerimientos"]`
    en vez de caer en el `_cb_directo` por defecto. `tablas/desktop.py`
    decide su comportamiento especial mirando el string `reporte ==
    "Requerimientos"`, no CÓMO se llegó ahí — por eso mover la Tabla detrás
    de un item de rail (en vez de una rama de despacho aparte) no le rompió
    nada.

    **Columnas reales de `requerimientos.parquet`, confirmadas con DuckDB
    directo (antes indocumentadas — el reporte usaba la config genérica
    de `data.py::REPORTES`, sin `filtros_cat`/`buscador` propios):**
    `Fecha Registro`, `Codigo Producto`, `Nombre Producto`, `Sub Almacen`
    (el área que pide), `Nombre Familia`, `Nombre Subfamilia`, `Cantidad`,
    `Precio Unit`, `Valor Item`, `Nombre Estado Requerimiento`
    (Procesado/Anulado/Generado — 98.8%/0.9%/0.4%). Incidentalmente esto
    también dejó al descubierto que la config de Salidas (`"Sub Almacen"`
    en `filtros_cat`, confirmada "2026-08-04") está **desactualizada**: el
    `salidas.parquet` real de hoy no trae esa columna (solo `LOCAL`,
    constante `"SAPIENS"`) — el chip/agrupar de Sub Almacén en Salidas no
    hace nada, en silencio (diseño defensivo de `_resolver`). No se tocó
    en este cambio (alcance distinto); queda como tarea aparte.

    **`graficos/movimientos_comun.py`** (mismo rol que `recetas_comun.py`
    para Recetas) aporta dos cosas:
    - `_chip_movimientos(reporte_activo)`: idéntico mecanismo a
      `_chip_fuente` — clic en el lado no activo NAVEGA
      (`session_state["_nav_reporte"]` + `st.rerun()`), no filtra.
    - `_comparativo_pedido_baja(key_prefix)`: vista "Pedido vs Baja",
      agregada como un ítem MÁS del rail en AMBOS dashboards (no un
      reporte nuevo en `REPORTES` — precedente: `ventas_comparativo.py`
      también vive como vista del rail de Ventas, no como entrada propia).
      Carga los DOS parquets con `data.cargar()` (mismo precedente de
      carga cruzada que `recetas_comun._cargar_flujo_compras` con
      `compras.parquet`) y trae SUS PROPIOS controles (fecha/familia/
      granularidad/métrica) en vez de heredar los del dashboard anfitrión
      — los dos lados tienen que quedar filtrados exactamente igual.
      **Dos límites reales del dato, no del código:** no hay llave
      documento-a-documento (`COD REQUERIMIENTO`/`COD SALIDA` numeran en
      secuencias independientes) → el cruce es agregado por
      producto/familia/período, nunca transacción a transacción; y
      `salidas.parquet` no trae el área destino → no se puede desglosar
      por Sub Almacén, solo por producto/familia.

    **Bug real encontrado verificando contra R2 (no el demo) — el mismo
    tipo de trampa que ya documenta `_activo()` en la regla #97, con una
    cara nueva:** `Serie.astype(str)` sobre una columna con nulos, cuando
    el dtype que devuelve DuckDB→pandas es el "str" Arrow-backed (no el
    `object` clásico), **no convierte el valor faltante a texto** — deja
    un `float('nan')` suelto adentro de una Series "de texto". No revienta
    en un `.groupby()` (que por defecto descarta claves NaN, en silencio),
    pero sí en `sorted(set(...) | set(...))` para armar la lista de
    familias del comparativo: `TypeError: '<' not supported between
    instances of 'float' and 'str'`. Reproducido y confirmado con
    `NOMBRE FAMILIA` de `requerimientos.parquet` (2.903/143.202 filas en
    blanco). Fix: `.fillna(...)` SIEMPRE antes de `.astype(str)`, nunca
    después — en `_cargar_lado()` de `movimientos_comun.py`.

    **Verificación:** `ruff`/`test_graficos.py`/`test_asistente_datos.py`
    verdes, más `streamlit run` contra R2 real (hay secrets locales): nav
    agrupado en un ícono "Movimientos", KPIs reales en ambos lados del
    chip, comparativo con cifras reales idénticas entrando desde
    Requerimientos o desde Salidas (S/ 8.108.897 requerido vs S/ 581.645
    de baja, 7.2% — la baja es una fracción chica de lo requerido, lo
    esperable: la mayoría de lo requerido se consume/vende, no se da de
    baja), y Tabla de Requerimientos con el AgGrid pivote intacto (sin
    excepciones en los logs del server).

99. **El rail (`navegacion.py`) reserva su columna con `margin-left` en
    `.stApp`, no con `left`/`padding` — esa columna queda FUERA de la caja
    de `.stApp` (2026-08-13).** `stAppViewContainer` pinta el lienzo gris
    (`--bg-primary`, `estilos/_00_base.py`), pero es un DESCENDIENTE de
    `.stApp`: si `.stApp` tiene `margin-left:{RAIL_ANCHO}px`, toda su caja
    —y todo lo que pinta adentro, incluido `stAppViewContainer`— arranca en
    x=90. La franja de 0 a 90px es margen de verdad, no padding: ningún
    hijo de `.stApp` pinta ahí. Confirmado con `elementFromPoint` en esa
    columna → devolvía `<html>` directo, con `background-color` por
    defecto del navegador (blanco), no el gris del lienzo.

    No se notaba porque el rail (`.st-key-nav_rail`, `position:fixed`)
    históricamente cubría esa columna de punta a punta (blanco de rail
    sobre blanco de navegador = invisible). Se hizo visible recién al
    separar el rail de los bordes: primero `height:auto` en vez de
    `100vh` (regla ya documentada arriba, deja un tramo corto debajo del
    último ítem) y luego `top:{RAIL_TOP}px` en vez de `top:0` (bajarlo del
    borde superior por pedido explícito) — cada uno abrió un hueco nuevo
    en esa columna, y ambos huecos salían blancos en vez de grises
    (reportado con screenshot de producción, visible solo con el tema real
    contra R2: el demo local con `.stApp` bien montado no lo delataba a
    simple vista, hacía falta medir `elementFromPoint`, no mirar).

    **Fix:** pintar `html, body` con `background: var(--bg-primary)
    !important` en `_00_base.py`, junto a la regla de `stAppViewContainer`
    — así el fondo por defecto del navegador coincide con el lienzo en
    vez de blanco. Regla general: cualquier reserva de espacio con
    `margin` (no `padding`) en un contenedor que pinta su propio fondo dueño
    del layout deja ese margen sin pintar por los hijos — si algo flota
    fijo encima y no lo cubre entero, hay que pintar el ancestro real
    (`html`/`body` acá) o pasar la reserva a `padding`.
