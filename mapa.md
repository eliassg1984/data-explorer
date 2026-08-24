# Mapa del proyecto — ficheros, pipeline y configuración

Qué hay y cómo encaja. Es el documento que se lee **entero** (unas 130
líneas): describe el estado ACTUAL del proyecto.

Su gemelo es **`arquitectura.md`**, la bitácora de reglas: 162 lecciones
sacadas de bugs reales, que se lee por BÚSQUEDA y no de arriba a abajo.
Los dos vivían en un solo fichero hasta el 2026-08-22; se partieron porque
tienen vidas distintas —este se corrige, aquel se agrega— y porque juntos
daban 115k tokens, o sea un documento que nadie podía abrir de verdad.

Las reglas se quedaron con el nombre `arquitectura.md` a propósito: hay 166
citas en el código con la forma `arquitectura.md #NNN`, y renombrarlo
obligaba a reescribirlas todas. Extraer ESTA mitad costó una sola.

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
| `estado_rango.py` | **Dueño único** del eje temporal de la franja superior: rango (`clave_rango`, `asegurar_rango`, `atajos_rango`, `aplicar_atajo`) **y corte** (`clave_corte`, `clave_modo`, `modo_fecha`, `corte_vigente`, `aplicar_corte`, `volver_a_rango`). Nadie escribe esas claves fuera de este módulo — ver reglas #24 y #62. Su hermano chico es `graficos/periodo.py`, el rango POR VISTA (regla #133): no le disputa nada — la franja sigue mandando y una vista que no lo importe se comporta igual que antes. |
| `cortes.py` | Agrupa fechas en **cortes**: las rachas de días de una misma sesión de inventario (salto ≤ `CORTE_MAX_SALTO_DIAS`). Un corte es un CONJUNTO de días, no un intervalo — ver regla #62. Sin dependencias de streamlit ni de `graficos/`, porque lo consumen los dos lados: la franja de `app.py` y `graficos/ajuste/_comun.py` (que lo reexporta con los nombres privados de siempre). |
| `data.py` | Carga de datos: DuckDB + httpfs leyendo parquets de R2 (secrets). Sistema de refresco bajo demanda vía R2. |
| `sunat.py` | **Capa de datos del SIRE Compras (RCE) de SUNAT** (2026-08-19), hermana de `data.py` pero contra la API de SUNAT en vez de R2: OAuth2 (`obtener_token`), listado paginado y SÍNCRONO del detalle vía un endpoint NO documentado (`obtener_comprobantes` → `URL_BUSQUEDA`, descubierto por DevTools — ver regla #140), aplanado del JSON anidado de SUNAT (`_normalizar_registro`) y la ficha del comprobante en dos formatos (`campos_ficha`, fuente única; `ficha_pdf`, con matplotlib). `obtener_comprobantes_rango` + `periodos_a_consultar` + `periodos_con_estado` (2026-08-20) unen los períodos que hagan falta para cubrir un rango por FECHA DE EMISIÓN y marcan cada fila Registrado/Pendiente — ver regla #141. Modo demo sin credenciales, igual criterio que `data.py::_datos_demo`. Devuelve el REGISTRO del comprobante, no el PDF/XML del proveedor — ver regla #139. El original SÍ se puede leer (`originales`/`claves_original`, 2026-08-19) pero sólo lo que subió aparte `herramientas/sunat_originales_sync.py` (Playwright contra el portal SOL, corre local) — ver regla #142. `comprobantes_rango` (2026-08-20) lee el registro del parquet `sunat_compras.parquet` que deja `herramientas/sunat_registro_sync.py`, y cae a la API en vivo si todavía no existe — ver regla #160. Testeado sin red en `test_sunat.py`. |
| `tablas/` | **Paquete de tablas AgGrid** (refactor 2026-08-01; antes un `tablas.py` de 2.028 líneas). `__init__.py` re-exporta la API pública. `_css.py` (CSS de grid y paneles), `_config.py` (estilos de celda/fila, sidebar, totales), `desktop.py` (`renderizar_aggrid_desktop`), `movil.py` (`renderizar_aggrid_movil`), `compras.py` (`renderizar_aggrid_compras`), `ajuste_pivote.py` (`renderizar_aggrid_pivote_ajuste`, tabla "Por fecha" de Ajuste de Inventario — ver regla #25). `renderizar_tabla_compras` se borró el 2026-08-08 (llevaba desde 2026-08-01 sin llamadores). |
| `graficos/` | **Paquete de dashboards de gráficos** (refactor Fase 2, 2026-07-25). `__init__.py` es solo el dispatcher: dict `_DASHBOARDS = {reporte: render_fn}` (no cadena de if/elif), más `renderizar_graficos_reporte` (entry point) y `tiene_dashboard(reporte)` (para que `app.py` no enumere reportes ni importe `_DASHBOARDS`; ver regla #50). `render_vista_pills` (pestañas Gráficos/Tabla sueltas en la franja) se ELIMINÓ 2026-08-04: ver regla #18. Cada dashboard vive en su archivo: `base.py` (infraestructura compartida: cards nativos, motor genérico, resolución de columnas, helpers de layout), **`ajuste/` es un paquete** (refactor 2026-08-08; antes un `ajuste.py` de 2.607 líneas — el fichero con MÁS churn del repo, 80 de los últimos 200 commits): una vista por módulo — `_comun.py` (layout del rail, fechas de corte, periodos), `_evolucion.py`, `_pivote.py`, `_cascada.py`, `_panel_analisis.py`, `_heatmap.py`, `_distribucion.py` — y `__init__.py` con la config del rail, `categoria_rango_ajuste` y el entry point. Ojo: la **cascada NO es un gráfico Plotly** sino una tabla de filas — `st.columns` por familia + HTML en `st.markdown`, con una columna de barras flotantes que encadenan la cascada; ver reglas #8 y #10, `ventas.py` (`ventas_resumen.py` aporta su vista "Resumen ejecutivo" — KPIs + venta diaria coloreada por tendencia + ticket promedio + top platos; nació con un candlestick, ver por qué se dio de baja en la regla #85) y `ventas_comparativo.py` (vista "Año Pasado": barras agrupadas Actual vs Año Pasado en día/semana/mes, con toggle de alineación fecha-calendario / día-de-semana en día, feriados y findes marcados, recorte del período en curso, modo "Descomposición" (%Δ venta/pax/ticket en un solo eje) y drill por clic al ranking de platos del período — ver reglas #86, #87 y #88), **`ventas_horario.py`** (2026-08-14, vista "Por hora": mapa de calor día × hora de hasta 4 períodos comparados en franjas, marcas rectangulares por arrastre —una por panel tocado—, drill con medidas a elección y árbol Grupo › Sub Grupo › Plato › **Tipo de descuento**; reusa los helpers de calendario de `ventas_comparativo` en vez de duplicarlos y sólo agrega la granularidad Año — ver reglas #112 a #115. Abre SIEMPRE en el período EN CURSO (uno solo: comparar es explícito y tiene su botón), recortado al último día con datos; los períodos a comparar NO tienen que ser consecutivos ni recientes — la lista es el atajo y el `date_input` abre el calendario entero. El eje de horas va en am/pm, y en el eje de días los fines de semana van en negro y los feriados en ámbar, con el MISMO calendario `_feriados_peru` que pinta las bandas de la vista Año Pasado), `inventario.py` (v2), `salidas.py` (evolución con granularidad Día/Semana/Mes/Año + composición por subalmacén/tipo de descargo), `constructor.py` (Power BI, usado por Compras). **`recetas_comun.py`** (2026-08-13) tiene la ÚNICA copia de los 5 gráficos que comparten Receta Base y Receta Venta (Sankey/Composición/Ranking/Ítems clave/Panorama de compras) más `_activo()` y `_chip_fuente()` — ver regla #97. `recetabase.py` y `recetaventa.py` son capas finas sobre ese módulo: resuelven columnas reales + llaman a lo compartido. `requerimientos.py` (2026-08-13, dashboard nuevo: evolución + sub almacén + estado, mismo layout que `salidas.py`) y **`movimientos_comun.py`** (chip Requerimiento/Salidas + vista "Comparativo" que cruza los dos parquets — ver regla #98) comparten nav ("Movimientos") con `salidas.py`. `legacy.py` (Inventario v1) se borró el 2026-08-08: 421 líneas sin un solo import. **`compras/` es a su vez un paquete** (refactor 2026-08-01; antes un `compras.py` de 2.835 líneas): un drill por archivo — `_comun.py` (helpers, incluye `_periodo_serie` para granularidad temporal — reusar desde ahí, no duplicar), `proveedor.py`, `producto.py` (2026-08-17, reemplaza a "Precio top 10" + "Precio por compra" + `cantidad.py`/"Cantidad por producto", que se borraron ese día: ranking de TODOS los productos —valor, cantidad, UM, precio real de inicio/fin de período y su variación— con el mismo patrón tabla-ranking + clic-para-enfocar que `proveedor.py`; el producto en foco muestra su evolución con un selector de texto plano Precio/Cantidad/Valor × Semana/Mes/Año que fusiona el promedio del período con el precio real de cada compra en un solo gráfico; debajo, un segundo ranking agrupa por Familia con mini ranking al clic — ver regla #128), `volatilidad.py` (`evolucion.py` —la vista "Evolución prov." del rail— se borró el 2026-08-16 a pedido: 377 líneas que quedaron sin un solo import al sacar la dimensión del rail; su pregunta la responde ahora el gráfico de evolución que vive DENTRO del drill de Proveedor) (ranking de insumos por volatilidad de precio → candlestick semanal → compras de la semana clickeada; ver regla #74) — y `__init__.py` con la config del rail y `renderizar_graficos_compras`. `_COMPRAS_RAIL_CATEGORIAS` movió "Producto" a la categoría Dimensión (junto a Proveedor): al cubrir precio+cantidad+valor a la vez ya no es una vista de "Precios". El drill "Familia" (Familia→Subfamilia→productos) se eliminó el mismo día por redundante con el ranking por Familia que ya trae Producto — ver regla #129. El drill de Proveedor se siguió partiendo el 2026-08-08 (era una función de 1.577 líneas): `_css_proveedor.py` (sus 527 líneas de CSS, que NO van a `estilos/` a propósito — ver su docstring), `_etiquetas_proveedor.py` (texto de las barras: `fmt_k`, `abrev_nombre`, `etiqueta_serie`, `sufijo_granularidad`; puras y con asserts de valor en `test_graficos.py`) y `_documentos_proveedor.py` (`tabla_documentos`, la AgGrid pivote del pie). **`_calendario.py`** (2026-08-24) es el selector de fecha de DOS MESES que la vista "Semanal" dibuja DENTRO de su tarjeta, plegado en un popover, en vez del pill de la franja: `st.date_input` sabe dibujar un solo mes (no recibe `monthsShown`), así que la grilla se arma con `st.button` + CSS generado por key, mismo patrón que `ajuste/_heatmap.py`. Escribe el rango por `estado_rango.aplicar_atajo` — no inventa estado— y tiene que PINEAR la clave, porque al no dibujarse el `date_input` Streamlit la descarta y el rango vuelve al default. Ver regla #203. Quedó en 791 líneas; el resto NO se siguió cortando a propósito — ver regla #55. `documentos_sunat.py` (2026-08-19, drill "Documentos SUNAT": los comprobantes que los proveedores emitieron hacia el RUC, vía `sunat.py` — el único drill de Compras cuyo dato no sale del parquet, y el único que NO respeta los chips Familia/Subfamilia; ver regla #139) es el drill más nuevo, y el único con una vista "Cruce" que SÍ vuelve a tocar el parquet: `cruzar_con_parquet` compara cada comprobante del SIRE contra `compras.parquet` por documento, acotando por fecha antes de armar la clave para no colisionar entre proveedores que reusan la misma serie — ver regla #143. Cuando un dashboard crezca así, partirlo del mismo modo. **Agregar un dashboard nuevo = crear `graficos/<nombre>.py` + 1 línea en `_DASHBOARDS`.** |
| `estilos/` | **Paquete del CSS global** (refactor 2026-08-01; antes un `estilos.py` de 1.700 líneas). `__init__.py` mantiene la API pública (`TAM_FUENTE`, `get_css`, `inject_css`) y concatena las secciones. Una sección por módulo, con prefijo numérico que marca el orden: `_00_base`, `_20_compras_rail`, `_30_filtros`, `_40_ajuste_franja`, `_50_fecha`, `_60_calendario`, `_70_chrome`, `_80_cards`, `_90_franja_inferior`, `_99_movil`. (`_10_vista` existió hasta el 2026-08-08: estilaba el selector Gráficos/Tabla y quedó 100% huérfano al borrarse ese widget — ver regla #49.) **El orden de `_SECCIONES` es parte del comportamiento**: hay `!important` en ambos lados de varios conflictos, así que gana la regla que va DESPUÉS — por eso `_99_movil` cierra. |
| `navegacion.py` | **Rail vertical izquierdo de Reportes** (ícono + label + KPIs, key `compras_tabs_row`) + el CSS de la franja horizontal donde `graficos/base.py::_render_rail` dibuja Vistas (key `nav_rail`, contenedor por POSICIÓN — ver regla #170) + el CSS de la cabecera fija (`_CSS_AJUSTE`, se inyecta en TODOS los reportes). Botón de refresco y pestillo al pie del rail, cada uno en su propio `@st.fragment`. En móvil el rail fluye como tira horizontal de chips (900px) y la franja de Vistas baja a bottom-nav (768px). Fue franja horizontal solo-texto de 2026-08-18 a 2026-08-22 (regla #132) — la #170 revirtió a rail vertical y sumó íconos/KPIs. |
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

1. El usuario pulsa el botón refrescar (pie del rail de Reportes —
   `navegacion.py::inject_navegacion` llama a `boton_refresco` en el mismo
   archivo, ver arquitectura.md regla #170; antes lo llamaba
   `graficos/base.py::_render_rail`, regla #164, cuando el rail vertical
   dibujaba Vistas). El botón vive en su **propio `@st.fragment`** para que
   su clic no dispare un rerun completo de `app.py`.
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
| `icono` | str | Shortcode Material Symbols (`":material/nombre:"`) para el rail de Reportes. Estuvo sin usar 2026-08-18→2026-08-22 mientras Reportes era la franja horizontal solo-texto (regla #132); la #170 lo devolvió a la navegación con los valores traducidos de Bootstrap Icons a Material. |
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
