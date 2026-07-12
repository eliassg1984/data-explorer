# Arquitectura del proyecto — mapa y reglas

Webapp Streamlit (Community Cloud) que lee parquets desde Cloudflare R2 con
DuckDB y los muestra en tablas AgGrid con estética propia (paleta lavanda).

Este fichero existe para que cualquier persona **o IA** entienda el proyecto
en 2 minutos y no rompa nada al modificarlo. Si cambias la estructura,
actualiza este documento en el mismo commit.

## Mapa de ficheros

| Fichero | Trabajo (uno solo) |
|---|---|
| `app.py` | Orquestador: navegación, filtros, fragmentos, llama a los renderizadores. |
| `data.py` | Carga de datos: DuckDB + httpfs leyendo parquets de R2 (secrets). Sistema de refresco bajo demanda vía R2. |
| `tablas.py` | Renderizado de tablas AgGrid: `renderizar_aggrid_desktop`, `renderizar_aggrid_movil`, `renderizar_aggrid_compras`, `renderizar_tabla_compras` (legacy). |
| `graficos.py` | Renderizado de gráficos: motor genérico config-driven (`crear_grafico`), dashboard de Inventario Valorizado (`renderizar_graficos`), gráficos dedicados de Ajuste de Inventario (`renderizar_graficos_ajuste` y sus 4 helpers privados), y explorador genérico (`renderizar_graficos_genericos`). |
| `estilos.py` | CSS global de la app Streamlit (chips, tabs, píldora de fecha, iframes, toasts...). |
| `navegacion.py` | Rail lateral, topbar y CSS por sección (`_CSS_AJUSTE`). Botón de refresco aislado en su propio `@st.fragment`. |
| `inyecciones.py` | Funciones `inject_*`: JS/HTML inyectado (overlay de errores, inspector de elementos, health-check del grid, paginación v2 con números y salto, maximizar AgGrid con Fullscreen API, altura dinámica del grid, fix panel columnas de Ajuste). |
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
   - **`:root` de `estilos.py`** (CSS) — para el CSS global inyectado como
     string. Ese bloque define variables (`--accent`, `--border`...) y el
     resto del fichero las usa con `var(--...)`. Es la fuente única del CSS.
   Ambas tienen los MISMOS valores a propósito. No se pueden fusionar en una
   sola (Python y CSS son mundos distintos; el CSS de `estilos.py` no es
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
   Aplica especialmente en `_graf_evolucion_ajuste` (range-selector + range-slider).

6. **Un cambio a la vez, verificado.** Antes de subir:
   `python -m py_compile <ficheros tocados>`. Sin salida = bien.
   (El SyntaxWarning de `inyecciones.py:358` es preexistente e inofensivo.)

7. **Ocultar ≠ eliminar función.** Reglas con `display:none` (toolbar de
   Streamlit, fullscreen nativo) quitan ACCESO visual, no funcionalidad;
   documentar el porqué junto a la regla.

8. **`renderizar_tabla_compras` es código legacy.** La función existe en
   `tablas.py` pero ya no se llama desde `app.py`: fue reemplazada por
   `renderizar_aggrid_compras` (mismo estilo que Ajuste de Inventario, con
   modo pivote, sidebar lavanda y todas las inyecciones). Si en algún momento
   se quiere limpiar el fichero, es seguro eliminarla.

## Funciones de inyección JS (inyecciones.py)

Todas usan `components.html(..., height=0)` para inyectar JS en el documento
padre sin ocupar espacio visible. Cada una tiene un propósito único:

| Función | Qué hace |
|---|---|
| `inject_error_overlay()` | Captura errores JS y los muestra en panel rojo fijo. Filtra ruido de extensiones del navegador. |
| `inject_element_inspector()` | Tooltip enriquecido al pasar el cursor (activado con `?debug=1` o Alt+I). |
| `inject_grid_health_check()` | Verifica que el `.ag-root-wrapper` se montó. Inyecta CSS de paginación dentro del iframe. |
| `inject_pagination_v2()` | Barra de paginación con números de página y campo de salto directo. |
| `inject_maximize_aggrid()` | Botón ⛶ para pantalla completa nativa (Fullscreen API sobre el iframe). Si hay sidebar, se ancla en `.ag-side-buttons`; si no, botón flotante. |
| `inject_dynamic_grid_height()` | Estira el iframe de AgGrid a `window.innerHeight - offset_px` con una sola medición puntual (no listener continuo). |
| `inject_fix_column_panel_ajuste()` | Recalcula `top` y `height` de cada `.ag-virtual-list-item` en los paneles Columnas y Pivote cuando las pastillas miden más que el slot por defecto (32px). Usa MutationObserver para re-ejecutar al cambiar de panel. |
| `inject_sidebar_toggle()` | Botón flotante ☰ para abrir/cerrar el sidebar nativo de Streamlit (no se usa en la versión con rail). |

## Gráficos de Ajuste de Inventario (graficos.py)

`renderizar_graficos_ajuste(df_f, nombre_reporte)` es el punto de entrada.
Muestra 4 KPIs y luego 4 tabs, cada uno delegando en un helper privado:

| Tab | Helper | Qué muestra |
|---|---|---|
| Evolución temporal | `_graf_evolucion_ajuste` | Líneas por familia + range-selector + range-slider + expander con eje dual (barras ajuste / línea valorizado). |
| Cascada por familia | `_graf_waterfall_ajuste` | Waterfall por familia/área + tabla top-5 faltantes y sobrantes. |
| Mapa de calor | `_graf_heatmap_ajuste` | Heatmap Familia × Área con escala divergente centrada en 0 + tabla pivot expandible. |
| Distribución | `_graf_distribucion_ajuste` | Box plot con outliers + histograma con líneas de media/mediana + tabla productos en el 5% inferior. |

Al final hay un expander con el explorador libre (`renderizar_graficos_genericos`).

**Regla crítica para estos gráficos:** `_LAYOUT_BASE` define `xaxis` y `yaxis`.
Los helpers que necesitan sobreescribir esas claves deben filtrarlas antes de
desempacar (ver Regla 5 de este documento).

## Convenciones de estilo AgGrid

- El CSS del grid vive en el diccionario `custom_css`, construido por
  `_css_base(font_px)` en `tablas.py`. Esta función ensambla 5 secciones:
  `_css_grid`, `_css_sidebar_marco`, `_css_panel_columnas`,
  `_css_panel_filtros`, `_css_panel_pivote`.
- Estética compartida de los 3 paneles laterales: pastillas redondeadas
  (`border-radius: 999px`, fondo `GRIS_FONDO`, borde `GRIS_BORDE`, hover
  lavanda) — "en juego" con el panel Modo pivote.
- Variantes por reporte (`es_requerimientos`, `es_ajuste`, `es_inventario`)
  se aplican DESPUÉS del CSS base mediante `.update()`, nunca mezcladas
  dentro de él.
- El tema de AgGrid varía por reporte: `"balham"` (por defecto),
  `"material"` para Inventario Valorizado, Ajuste de Inventario y Compras.

## Cómo verificar tras cualquier cambio

```bash
python -m py_compile app.py tablas.py estilos.py inyecciones.py navegacion.py tema.py graficos.py
```

Luego recargar la app y revisar: tabla Ajuste de Inventario (desktop),
paneles Columnas / Filtros / Modo pivote, botón maximizar y paginación,
vista Gráficos de Ajuste (tabs Evolución / Cascada / Mapa de calor / Distribución).

## Jerarquía de layout — quién manda sobre cada contenedor

El `padding-top` del contenedor principal (`block-container`) tiene TRES
niveles en cascada. No es duplicación: es una jerarquía deliberada.

| Nivel | Dónde vive | Valor | Cuándo aplica |
|---|---|---|---|
| 1. Default global | `estilos.py` | 1.5rem | Toda la app |
| 2. Override por sección | `navegacion.py` (`_CSS_AJUSTE`...) | 0.85rem | Solo esa sección; gana vía prefijo `html body` |
| 3. Override móvil | `estilos.py` (`@media max-width:768px`) | 0.5rem | Pantallas chicas |

**Caso especial — Ajuste de Inventario:** `_CSS_AJUSTE` en `navegacion.py`
hace cuatro cosas adicionales que ningún otro reporte necesita:
- Oculta `#nav-topbar` (en este reporte va vacío, la franja quedaba en blanco).
- Elimina el `padding-top:48px` que el rail reserva para el topbar.
- Baja el padding del contenedor principal a 0.85rem (nivel 2).
- Colapsa con `display:none` los contenedores "invisibles" que se apilan
  arriba (`<style>` inyectados, iframes de overlay/inspector, wrapper del
  topbar) — cada uno aporta un "gap" del bloque vertical; sumar 4-5 de ellos
  forma una franja blanca visible.

**Regla de propiedad** (dueño único por contenedor):

- Layout de página (`block-container`, header, topbar, por sección) →
  dueño **`navegacion.py`** para overrides de sección; `estilos.py` solo
  guarda el default global y la variante móvil.
- Contenedores con key (`.st-key-fila_ajuste_top`, `.st-key-vistatabs_*`,
  `.st-key-fecha_ajuste_pill`, `.st-key-fch_ajuste_inline`...) →
  dueño **`estilos.py`**. Nadie más los estila.
- **`inyecciones.py` = solo comportamiento (JS).** Nunca estética de
  contenedores.

Para cambiar el espacio superior de UNA sección: editar su bloque en
`navegacion.py`. Editar el default de `estilos.py` NO tendrá efecto en las
secciones con override (el nivel 2 gana) — es el error clásico a evitar.

## Motor de gráficos genérico (graficos.py)

`crear_grafico(df, conf)` genera figuras Plotly desde un dict de configuración.
Añadir un gráfico a un reporte = añadir una entrada en `REPORTES[reporte]['graficos']`,
no escribir una función nueva.

Claves del dict de configuración:

| Clave | Efecto |
|---|---|
| `tipo` | `"bar"`, `"line"`, `"area"`, `"scatter"`, `"histogram"`, `"box"`, `"treemap"` |
| `x` / `y` / `color` / `size` | Lista de candidatos de columna; se resuelve con `buscar_columna()` |
| `path` | Solo para `treemap`: lista de listas de candidatos |
| `titulo` | Título del gráfico |
| `barmode` | `"group"` (default), `"stack"`, `"relative"` |
| `tickangle` | Rotación de etiquetas del eje X |
| `etiquetas` | `True` para mostrar etiquetas de datos sobre las barras/líneas |
| `x_categorico` | `True` para forzar el eje X como categórico (útil con texto) |
| `nbins` | Número de bins para histogramas |

Dos conceptos de color DISTINTOS (no mezclar):
- **Color de interfaz** (fondos, grillas, texto) → `tema.py`, sección normal.
- **Color de dato / serie** (barras, escalas, semáforos) → `tema.py`, sección
  `PALETA_SERIES`, `SERIE_PRINCIPAL`, `ESCALA_CONTINUA`, `ESCALA_SEMAFORO`.

## Sistema de diagnóstico de rendimiento (perf.py)

Se activa con `?debug=1` en la URL. Sin ese parámetro, todas las llamadas
son no-op y no añaden overhead.

- `perf.start()` / `perf.end()` — marcan el inicio y fin del rerun completo.
- `perf.phase("nombre")` — context manager para medir una fase concreta.
- `perf.start_phase("nombre")` / `perf.end_phase("nombre")` — alternativa
  sin `with`, para bloques grandes que no conviene reindentar.
- `perf.fragment_start("nombre")` / `perf.fragment_end()` — para funciones
  decoradas con `@st.fragment`; detectan si el rerun es completo o aislado.
- `perf.set_df_info(df, label)` — registra filas, columnas y tamaño estimado
  del JSON que irá a AgGrid.
- `perf.render_panel()` — panel Python con métricas, desglose de fases e
  historial de últimos reruns.
- `perf.render_browser_panel()` — panel HTML/JS que escucha eventos de AgGrid
  (`gridReady`, `firstDataRendered`, `modelUpdated`) vía
  `BroadcastChannel('_perf_aggrid')`. El canal lo alimenta `tablas.py` desde
  los callbacks `onGridReady`, `onFirstDataRendered` y `onModelUpdated`.

## Refactor en curso (fases)

- [x] Fase 1 — `tema.py` + este documento (aditivo, riesgo cero).
- [x] Fase 1.5 — Propiedad de contenedores: jerarquía de layout documentada,
      comentarios cruzados en `estilos.py`/`navegacion.py`, y eliminado el
      código muerto `inject_boton_calendario_ajuste`.
- [x] Fase 2 — Colores centralizados en la paleta. Los 5 ficheros conectados.
      PATRÓN CLAVE: DÓNDE vive el CSS decide CÓMO se centraliza.
      - CSS del documento PADRE → usa `var(--x)` del `:root`.
      - CSS DENTRO del iframe de AgGrid (`custom_css`) → NO ve el `:root`;
        usa constantes de `tema.py` resueltas en Python (f-strings).
      - Python puro (graficos.py/Plotly, navegacion.py) → constantes.
      ⚠️ LECCIÓN: al convertir a f-string un bloque con JS/CSS con llaves,
      escapar como `{{ }}`, dejando llaves simples SOLO para `{CONSTANTE}`.
- [x] Fase 3 — Trocear `renderizar_aggrid_desktop`. Extraídos 5 helpers:
      `_css_base(font_px)` (ensamblada a su vez por 5 sub-funciones),
      `_estilos_celda`, `_estilo_fila`, `_config_sidebar`, `_fila_totales`.
- [x] Fase 5 (parcial) — Profundidad de gráficos.
      HECHO en el motor genérico: `_hover_fmt`, `hovertemplate` con formato
      peruano (S/ para moneda, miles para stock), `hovermode="x unified"`,
      eje Y con `tickformat=",.0f"`.
      HECHO como módulo dedicado: `renderizar_graficos_ajuste` con 4 tabs
      (evolución temporal con range-selector/eje-dual, cascada waterfall,
      mapa de calor divergente, distribución con box plot e histograma).
      PENDIENTE: hover propio para treemap/sunburst/box, `facet` para
      comparativas.
- [ ] Fase 4 — Mover el CSS del grid a `estilos_grid.py`. OPCIONAL/cosmético:
      el CSS ya está encapsulado en `_css_base()` tras la Fase 3; moverlo de
      fichero aporta orden pero poco valor. Dejar para limpieza futura.
