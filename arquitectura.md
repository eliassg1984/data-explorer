# Reglas del proyecto (aprendidas de bugs reales)

Bitácora append-only: cada entrada es una lección que costó un bug de
verdad, con la medición que la respalda. **No se lee de arriba a abajo — se
busca.** Para eso está el índice de acá abajo.

El mapa del proyecto (tabla de ficheros, pipeline de datos, configuración de
`REPORTES`) vive en **`mapa.md`**, y ése sí se lee entero.

> Al agregar una regla: `test_docs.py` verifica que no repitas número, que
> no dejes huecos, que toda cita `#NNN` apunte a algo que exista y que el
> índice quede en sync. Regenerá el índice con
> `python herramientas/indice_reglas.py`.

<!-- INDICE:INICIO — generado por herramientas/indice_reglas.py, no editar a mano -->

## Índice por tema

181 reglas. Una misma regla aparece bajo todos los temas que le corresponden — por eso los totales suman más que el total.

**CSS y estilos** (66)

- **#1** — Colores desde la paleta central — DOS fuentes coordinadas
- **#3** — Nada de formateo % en plantillas JS/CSS de components.html
- **#4** — Altura del grid: fijo + inyección
- **#6** — CSS por key: acotar al widget, nunca colgar del contenedor
- **#7** — Antes de estilar o agregar un widget, grep estilos/ por el prefijo de key del contenedor…
- **#13** — Verificar el layout SIEMPRE al ancho real del usuario
- **#15** — @st.cache_data sobre una función que concatena constantes de submódulos NO se invalida cuando…
- **#16** — Keys "de reporte" vs keys "de componente compartido": no confundir al scopear CSS con :has()
- **#17** — La franja transparente + fecha-pill-izquierda + chips-centrados-blancos es el DEFAULT para…
- **#28** — Los paneles "Columnas" y "Modo pivote" abrían VACÍOS la primera vez
- **#30** — Ensanchar un st.popover (o cualquier botón) a width:100% dentro de un st.container(key=...)…
- **#31** — Botón inline-flex (trigger de st.popover) dentro de un contenedor en flujo block: el WRAPPER…
- **#36** — margin de un go.Heatmap no se respeta al píxel — medir, no calcular
- **#38** — El margin-top: -80px de [class*="st-key-ajuste_graf_card_izq_"] (estilos/_20_compras_rail.py)…
- **#47** — Un width/height con !important no alcanza para redimensionar un item flex — hacen falta 3…
- **#48** — st.pills/segmented_control/st.popover/st.button guardan la key en un WRAPPER de layout — lo…
- **#49** — Borrar código Python deja CSS huérfano, y nada en el .py lo señala
- **#50** — Un inject_* cuyo elemento ya no existe NO es código muerto inerte — cuesta
- **#51** — var(--x, #hex) es un #hex suelto disfrazado
- **#55** — Al partir una función gigante, el orden lo decide el ACOPLAMIENTO, no el tamaño
- **#59** — help= en un st.popover cambia cuántos niveles de <div> hay entre [data-testid="stPopover"] y…
- **#64** — El stepper del corte NO va dentro de fecha_ajuste_pill (2026-08-09)
- **#66** — go.Heatmap no tiene bordes por celda porque no son celdas — es una sola imagen (2026-08-09)
- **#68** — El texto de un st.button no está en el <button>: está en un <p> con su propio font-size…
- **#77** — Tarjeta der desalineada con la izq (2026-08-10) — bug preexistente en…
- **#81** — Drill lateral en vez de apilado (2026-08-10, mismo día) — el detalle del click-drill (regla…
- **#90** — Para mover UN widget, el ancla es la key del PROPIO widget — no hace falta (ni conviene)…
- **#93** — El cuadradito de color ES el checkbox — cómo estilar la caja de st.checkbox sin depender de…
- **#96** — El item del rail viaja en ?vista=, y el detector de solapamientos tenía que mirar los TRES…
- **#99** — El rail (navegacion.py) reserva su columna con margin-left en .stApp, no con left/padding —…
- **#101** — El presupuesto vertical: una tarjeta = una pantalla, y graficos/alturas.py es su único dueño…
- **#102** — Un height en CSS sobre un bloque de Streamlit NO HACE NADA, y height="stretch" no llega al…
- **#104** — La franja de controles necesita CONTENIDO arriba para poder tener línea superior (2026-08-13)
- **#105** — El presupuesto vertical contaba la figura pero NO la franja de controles (2026-08-13)
- **#106** — El alto de una figura SÍ puede salir del CSS — la regla #102 estaba mal (2026-08-13)
- **#107** — La franja de controles con VARIOS grupos: separadores colgados del grupo, anchos por caso, y…
- **#110** — st.toggle comparte data-testid="stCheckbox" con st.checkbox — no existe un testid "stToggle"…
- **#111** — Un st.popover no empuja layout NUNCA, esté flotando o no — por eso es la herramienta correcta…
- **#115** — Un return temprano NO borra las tarjetas que ya estaban: hay que dibujarlas siempre y decidir…
- **#116** — Un drill APILADO empuja el gráfico fuera de la pantalla; uno REPARTIDO no
- **#117** — Python emite alturas de CONTENIDO; las RESTAS las hace el CSS
- **#118** — Los rails se pliegan cambiando UN ancho — y lo que cambia por :has() se DECLARA en la regla…
- **#120** — Un dashboard puede "aparecer" en la franja superior sin que app.py sepa nada de él — mismo…
- **#121** — El patrón "título fantasma en la franja" se generalizó (helper titulo_en_franja en…
- **#123** — Para ensanchar un contenedor de Streamlit con margin negativo + width: calc(100% + Npx), hay…
- **#124** — compras_prov_drill_wrap (drill de Proveedor) pasó de 2 a 3 columnas (ranking / tabla resumen…
- **#127** — hovermode="x unified" de Plotly renderiza su caja de hover con la clase SVG .legend —…
- **#128** — Compras › Producto (2026-08-17) fusiona 3 vistas en 1, y deja 3 lecciones reusables
- **#129** — Se eliminó el drill "Familia" (Familia→Subfamilia→productos, compras/familia.py) por…
- **#132** — El rail de navegación dejó de ser una columna izquierda de 90px y pasó a ser una franja…
- **#138** — El rail subió a la altura de la franja (2026-08-19), y eso obligó a recortar la banda blanca
- **#145** — La GRILLA tiene un dueño, igual que el color y el alto
- **#146** — Compras invierte la figura y el fondo: página blanca, tarjetas tenues
- **#147** — El rail de Compras en formato LISTA (icono + nombre + chevron)
- **#151** — Modo diseño fase C — insertar elementos de mentira ("mocks") para ver cómo se vería algo que…
- **#152** — En una herramienta para PROBAR, el 0 de un slider es un valor, no un "sin cambio"
- **#153** — Fase D del modo diseño: paleta de superficie, revertir por propiedad, y "Copiar CSS" para…
- **#154** — destinosDeEstilo necesitaba DOS niveles de redirección, no uno — y el guard de cantidad de la…
- **#156** — Un transform en un ancestro CAPTURA a sus hijos position: fixed — y por eso…
- **#157** — El modo diseño sólo sabía agarrar elementos con st-key-*, y la mitad de lo que uno quiere…
- **#167** — El fondo general de la app no se podía editar con el modo diseño: el lienzo es el único…
- **#169** — El CSS que exporta el modo diseño es una FOTO DE PÍXELES, no la intención: pegarlo tal cual…
- **#172** — help= en un st.button() rompe cualquier selector CSS que escriba .stButton > button (hijo…
- **#174** — Al invertir QUÉ dibuja un contenedor compartido (regla #170: compras_tabs_row pasó de Vistas…
- **#175** — Las manijas de resize del modo diseño (regla #46) redimensionan CUALQUIER elemento salvo un…
- **#177** — "COMPRAS: PÁGINA BLANCA, TARJETAS TENUES" (regla #16 y media docena de "vueltas" entre…

**Layout y alturas** (17)

- **#13** — Verificar el layout SIEMPRE al ancho real del usuario
- **#38** — El margin-top: -80px de [class*="st-key-ajuste_graf_card_izq_"] (estilos/_20_compras_rail.py)…
- **#60** — "Aparece/desaparece en :hover pero sin empujar nada de abajo" se anima con…
- **#101** — El presupuesto vertical: una tarjeta = una pantalla, y graficos/alturas.py es su único dueño…
- **#104** — La franja de controles necesita CONTENIDO arriba para poder tener línea superior (2026-08-13)
- **#105** — El presupuesto vertical contaba la figura pero NO la franja de controles (2026-08-13)
- **#108** — st.empty() BORRA su contenido al crearse: un placeholder que se rellena tarde es un salto de…
- **#115** — Un return temprano NO borra las tarjetas que ya estaban: hay que dibujarlas siempre y decidir…
- **#116** — Un drill APILADO empuja el gráfico fuera de la pantalla; uno REPARTIDO no
- **#117** — Python emite alturas de CONTENIDO; las RESTAS las hace el CSS
- **#120** — Un dashboard puede "aparecer" en la franja superior sin que app.py sepa nada de él — mismo…
- **#137** — La franja y las tarjetas comparten UNA sola línea izquierda (2026-08-19), y el ancla es la…
- **#139** — Drill "Documentos SUNAT" de Compras (2026-08-19): un dashboard cuyo dato NO sale del parquet
- **#145** — La GRILLA tiene un dueño, igual que el color y el alto
- **#161** — Un número de píxeles escrito en un comentario no se entera de que el layout cambió: el eje X…
- **#177** — "COMPRAS: PÁGINA BLANCA, TARJETAS TENUES" (regla #16 y media docena de "vueltas" entre…
- **#178** — Mover un control de "flotando sobre el marco compartido" a "adentro de una tarjeta" no es un…

**Plotly y figuras** (40)

- **#5** — _LAYOUT_BASE de graficos.py no se puede desempacar con `
- **#9** — Un bloque que aparece/desaparece necesita un *instance id* en las keys de sus hijos
- **#11** — go.Heatmap NO es una traza seleccionable: on_select nunca recibe sus puntos
- **#12** — El clic de Plotly no se puede simular desde JS
- **#20** — Boxplot/histograma con datos mayoritariamente en cero: filtrar el cero ANTES de graficar, no…
- **#23** — showspikes en subplots hay que pedirlo en CADA eje X, no en uno solo
- **#35** — Fila/columna "TOTAL" en un go.Heatmap — categoría extra, no subplot
- **#36** — margin de un go.Heatmap no se respeta al píxel — medir, no calcular
- **#37** — Columna fija mientras el resto scrollea, mezclando HTML propio + un gráfico de Plotly: se…
- **#42** — _graf_heatmap_ajuste (Mapa de calor de Ajuste) tiene DOS modos — Ajuste Valorizado (signado)…
- **#43** — st.plotly_chart(..., selection_mode="points") NO agrega las herramientas de caja/lazo al…
- **#44** — go.Histogram — selectabilidad NO verificada, mismo riesgo que la regla #11 (go.Heatmap)
- **#58** — _graf_heatmap_ajuste (Mapa de calor de Ajuste) suma un selector de Vista — Mapa / Flujo…
- **#60** — "Aparece/desaparece en :hover pero sin empujar nada de abajo" se anima con…
- **#66** — go.Heatmap no tiene bordes por celda porque no son celdas — es una sola imagen (2026-08-09)
- **#72** — Para poner el valor continuo de un px.histogram en el eje VERTICAL, se pasa y=col en vez de…
- **#73** — La barra de Plotly (modebar) por default trae 10 botones, casi invisible…
- **#74** — go.Candlestick (drill Volatilidad de insumos, graficos/compras/volatilidad.py) — sin…
- **#76** — Click-drill en Por área/Por familia (2026-08-10) — mismo patrón que compras/familia.py, con…
- **#78** — "Buscar producto" (grupo/Subfamilia) mostraba ítems sin stock y en orden equivocado…
- **#79** — Click-drill (regla #76) obligaba a hacer scroll para ver el detalle (2026-08-10, mismo día)
- **#80** — Barra negativa dibujada a la izquierda descentraba el ranking (2026-08-10, mismo día)
- **#81** — Drill lateral en vez de apilado (2026-08-10, mismo día) — el detalle del click-drill (regla…
- **#83** — _ficha_subfamilia deja de desglosar por área (2026-08-10, mismo día) — pasa de barra apilada…
- **#85** — El candlestick de "Resumen ejecutivo" (regla #84) se dio de baja el mismo día —…
- **#91** — Un legend de Plotly que "no se ve" casi nunca está apagado: está compitiendo con otra cosa en…
- **#92** — Fechas horizontales en un eje categórico: el arreglo no es tickangle=0, es partir la etiqueta…
- **#95** — herramientas/ver_figura.py: ver un gráfico sin navegador, y por qué hacía falta (2026-08-12)
- **#102** — Un height en CSS sobre un bloque de Streamlit NO HACE NADA, y height="stretch" no llega al…
- **#103** — El title= de una figura y la leyenda horizontal de _compras_layout se pelean el MISMO…
- **#106** — El alto de una figura SÍ puede salir del CSS — la regla #102 estaba mal (2026-08-13)
- **#109** — La franja de controles se propagó a Compras › Familia — y de paso se extrajo el helper…
- **#112** — go.Heatmap NO es seleccionable en Plotly: el box-select no emite nada
- **#122** — El texto del hover de Plotly casi no se veía — no era un problema de estilos/, sino de…
- **#125** — El scroll interno de un st.plotly_chart (8 filas fijas + scroll, drill de Proveedor) necesita…
- **#126** — El ranking (barras Plotly) y la tabla resumen del drill de Proveedor —dos vistas de los…
- **#127** — hovermode="x unified" de Plotly renderiza su caja de hover con la clase SVG .legend —…
- **#161** — Un número de píxeles escrito en un comentario no se entera de que el layout cambió: el eje X…
- **#165** — Al agregar una barra de modos quedaron DOS controles del mismo estado, uno encima del otro —…
- **#175** — Las manijas de resize del modo diseño (regla #46) redimensionan CUALQUIER elemento salvo un…

**AgGrid y tablas** (26)

- **#2** — Estilos de paneles AgGrid siempre ACOTADOS por panel
- **#4** — Altura del grid: fijo + inyección
- **#18** — Los 8 reportes usan el rail derecho (_render_rail) desde 2026-08-04
- **#25** — Tabla dinámica de Ajuste — reescrita 2026-08-07 como AG Grid real
- **#26** — GridOptionsBuilder.configure_column() PISA el headerName cada vez que se lo llama sin…
- **#27** — La fila de totales suma por DEFAULT toda columna numérica; la lista negra es la excepción
- **#28** — Los paneles "Columnas" y "Modo pivote" abrían VACÍOS la primera vez
- **#29** — No reposicionar a mano los ítems de una lista virtual de AG Grid: hay que declararle el alto…
- **#32** — El coste por rerun de la tabla se paga en CADA cambio de filtro, no solo al abrir
- **#33** — Dónde se va el tiempo de la tabla, medido (2026-08-06, 10k filas, Ajuste con sus 5 niveles de…
- **#34** — Los chips de Ajuste filtran en el NAVEGADOR, no en Python
- **#40** — renderizar_aggrid_desktop es COMPARTIDO por todos los reportes — un if True: ahí adentro es…
- **#45** — inject_maximize_aggrid — el botón ⛶ desaparecía para siempre al cambiar de columnas en…
- **#50** — Un inject_* cuyo elemento ya no existe NO es código muerto inerte — cuesta
- **#52** — Un flag booleano fijado a True a mano se vuelve invisible en un mes
- **#54** — Un callback inyectado necesita UNA firma, no una por llamador
- **#57** — configure_column(..., hide=True) oculta la columna de la GRILLA, no de los paneles laterales…
- **#58** — _graf_heatmap_ajuste (Mapa de calor de Ajuste) suma un selector de Vista — Mapa / Flujo…
- **#74** — go.Candlestick (drill Volatilidad de insumos, graficos/compras/volatilidad.py) — sin…
- **#75** — Inventario Valorizado v3 (2026-08-10) — de 4 vistas a 3, más un buscador que reemplaza a la…
- **#82** — _panel_top pasa de 2 pestañas de mini-gráficos a UNA tabla AgGrid ordenable, con barra de…
- **#130** — Ranking de Volatilidad (compras/volatilidad.py + tablas/compras_volatilidad.py): cabeceras…
- **#136** — El ranking de Proveedor pasó de st.dataframe a AgGrid para sacarle los checkbox (2026-08-19)…
- **#148** — Maximizar un AgGrid necesita DOS mitades: soltar el ancho y re-repartir las columnas
- **#159** — Cuadrados negros en vez de iconos en Chrome < 120: AG Grid 34 emite mask-image sin la…
- **#163** — arquitectura.md creció hasta ser un documento que nadie podía abrir: 115k tokens, y CLAUDE.md…

**Streamlit** (54)

- **#6** — CSS por key: acotar al widget, nunca colgar del contenedor
- **#7** — Antes de estilar o agregar un widget, grep estilos/ por el prefijo de key del contenedor…
- **#8** — Nunca align-items: center en un stHorizontalBlock que hace de fila de tabla
- **#9** — Un bloque que aparece/desaparece necesita un *instance id* en las keys de sus hijos
- **#12** — El clic de Plotly no se puede simular desde JS
- **#14** — st.date_input dibuja UN solo mes y no hay forma de desdoblarlo
- **#30** — Ensanchar un st.popover (o cualquier botón) a width:100% dentro de un st.container(key=...)…
- **#31** — Botón inline-flex (trigger de st.popover) dentro de un contenedor en flujo block: el WRAPPER…
- **#162** — st.markdown(..., unsafe_allow_html=True) cuyo HTML arranca con un tag de bloque (<div>, no…
- **#37** — Columna fija mientras el resto scrollea, mezclando HTML propio + un gráfico de Plotly: se…
- **#39** — Inspector (?debug=1): clic derecho solo FIJABA el tooltip, nunca copiaba — y encima el…
- **#42** — _graf_heatmap_ajuste (Mapa de calor de Ajuste) tiene DOS modos — Ajuste Valorizado (signado)…
- **#48** — st.pills/segmented_control/st.popover/st.button guardan la key en un WRAPPER de layout — lo…
- **#49** — Borrar código Python deja CSS huérfano, y nada en el .py lo señala
- **#55** — Al partir una función gigante, el orden lo decide el ACOPLAMIENTO, no el tamaño
- **#59** — help= en un st.popover cambia cuántos niveles de <div> hay entre [data-testid="stPopover"] y…
- **#61** — Panorama de compras (recetaventa.py, 2026-08-09): 5ª vista del rail de Receta Venta, la…
- **#62** — El corte es un CONJUNTO de días, no un intervalo — por eso tiene su propio modo en el…
- **#68** — El texto de un st.button no está en el <button>: está en un <p> con su propio font-size…
- **#70** — Un bloque condicional dentro de un @st.fragment deja elementos HUÉRFANOS: Streamlit no limpia…
- **#71** — st.pills/st.segmented_control fuera de una corrida real de Streamlit siempre devuelve su…
- **#72** — Para poner el valor continuo de un px.histogram en el eje VERTICAL, se pasa y=col en vez de…
- **#76** — Click-drill en Por área/Por familia (2026-08-10) — mismo patrón que compras/familia.py, con…
- **#82** — _panel_top pasa de 2 pestañas de mini-gráficos a UNA tabla AgGrid ordenable, con barra de…
- **#84** — [SUPERADA por la regla #85 — el candlestick de esta regla se dio de baja el mismo día]…
- **#90** — Para mover UN widget, el ancla es la key del PROPIO widget — no hace falta (ni conviene)…
- **#91** — Un legend de Plotly que "no se ve" casi nunca está apagado: está compitiendo con otra cosa en…
- **#93** — El cuadradito de color ES el checkbox — cómo estilar la caja de st.checkbox sin depender de…
- **#95** — herramientas/ver_figura.py: ver un gráfico sin navegador, y por qué hacía falta (2026-08-12)
- **#97** — Unificación Receta Base + Receta Venta bajo un solo ítem de nav "Recetas" (2026-08-13)
- **#100** — "Nueva Receta": tercer miembro de grupo_nav: "Recetas", y por qué es tool: True en vez de una…
- **#107** — La franja de controles con VARIOS grupos: separadores colgados del grupo, anchos por caso, y…
- **#108** — st.empty() BORRA su contenido al crearse: un placeholder que se rellena tarde es un salto de…
- **#110** — st.toggle comparte data-testid="stCheckbox" con st.checkbox — no existe un testid "stToggle"…
- **#111** — Un st.popover no empuja layout NUNCA, esté flotando o no — por eso es la herramienta correcta…
- **#112** — go.Heatmap NO es seleccionable en Plotly: el box-select no emite nada
- **#119** — Nada de transition sobre algo que un rerun pueda pillar a media animación
- **#123** — Para ensanchar un contenedor de Streamlit con margin negativo + width: calc(100% + Npx), hay…
- **#125** — El scroll interno de un st.plotly_chart (8 filas fijas + scroll, drill de Proveedor) necesita…
- **#126** — El ranking (barras Plotly) y la tabla resumen del drill de Proveedor —dos vistas de los…
- **#128** — Compras › Producto (2026-08-17) fusiona 3 vistas en 1, y deja 3 lecciones reusables
- **#131** — Se unificaron "Precio vs año pasado" y "Cantidad vs año pasado" (categorías separadas…
- **#133** — Compras › Proveedor perdió el botón "✕ Quitar foco" del ranking (2026-08-18, a pedido): ahora…
- **#136** — El ranking de Proveedor pasó de st.dataframe a AgGrid para sacarle los checkbox (2026-08-19)…
- **#150** — Mover un widget de sitio cuando su KEY es el estado: el pill de fecha de la franja
- **#154** — destinosDeEstilo necesitaba DOS niveles de redirección, no uno — y el guard de cantidad de la…
- **#157** — El modo diseño sólo sabía agarrar elementos con st-key-*, y la mitad de lo que uno quiere…
- **#171** — Los KPIs del rail (regla #170) se rehicieron a las pocas horas: "no se ve bien" con una…
- **#172** — help= en un st.button() rompe cualquier selector CSS que escriba .stButton > button (hijo…
- **#173** — El overlay del modo diseño tiene pointer-events:none a propósito (para poder ver/medir lo de…
- **#176** — st.markdown/st.caption aceptan help= en este Streamlit (1.59.2) — no hace falta inventar un…
- **#178** — Mover un control de "flotando sobre el marco compartido" a "adentro de una tarjeta" no es un…
- **#179** — Un atajo de fecha (nuevo o viejo) no sobrevive cambiar de REPORTE y volver — mismo mecanismo…
- **#180** — Un widget DENTRO de un @st.fragment que escribe estado consumido AFUERA no cambia nada en…

**Datos, R2 y DuckDB** (19)

- **#10** — Ajuste SÍ se puede verificar en local desde 2026-08-05
- **#19** — @st.cache_data NO debe envolver la función que devuelve None/vacío ante un fallo transitorio:…
- **#21** — Columnas reales de salidas.parquet confirmadas 2026-08-04
- **#22** — Un dashboard puede cargar el parquet de OTRO reporte — primer caso: "Venta vs Compra" en…
- **#32** — El coste por rerun de la tabla se paga en CADA cambio de filtro, no solo al abrir
- **#41** — Un .clear() sobre una función cacheada solo existe si ESA función tiene el @st.cache_data…
- **#65** — Datos demo que no tienen la FORMA del dato real no verifican nada (2026-08-09)
- **#86** — Comparativo diario vs Año Pasado (graficos/ventas_comparativo.py, 2026-08-11) — "la misma…
- **#88** — Modo "Descomposición" y drill a platos (2026-08-11) — la identidad Venta = Pax × Ticket es lo…
- **#94** — persist="disk" en la caché de datos, y por qué una descarga lenta se volvía "R2 caído"…
- **#97** — Unificación Receta Base + Receta Venta bajo un solo ítem de nav "Recetas" (2026-08-13)
- **#98** — Unificación Requerimientos + Salidas bajo un solo ítem de nav "Movimientos" (2026-08-13), y…
- **#100** — "Nueva Receta": tercer miembro de grupo_nav: "Recetas", y por qué es tool: True en vez de una…
- **#113** — Las horas de un turno no se ordenan por número, y el eje NO puede ser numérico
- **#114** — Descuentos en ventas.parquet: la venta ya viene NETA, y sólo una de las dos columnas de…
- **#134** — Piloto de "cada gráfico elige su rango" (2026-08-18): el módulo graficos/periodo.py y su…
- **#143** — Cruce SIRE ↔ parquet de Compras: la clave serie-número sola produce falsos positivos si no se…
- **#160** — El registro del SIRE pasó de consulta EN VIVO a parquet en R2, y eso cambia lo que se le…
- **#170** — Se invirtieron Reportes y Vistas: Reportes al rail vertical izquierdo, Vistas a la franja…

**SUNAT y SIRE** (9)

- **#139** — Drill "Documentos SUNAT" de Compras (2026-08-19): un dashboard cuyo dato NO sale del parquet
- **#140** — El flujo de descarga documentado por SUNAT para el SIRE Compras está roto, y el que funciona…
- **#141** — Documentos SUNAT se ordena por FECHA DE EMISIÓN, no por período tributario — y la razón es un…
- **#142** — El PDF/XML ORIGINAL del proveedor (no la ficha renderizada) llega por un camino totalmente…
- **#143** — Cruce SIRE ↔ parquet de Compras: la clave serie-número sola produce falsos positivos si no se…
- **#160** — El registro del SIRE pasó de consulta EN VIVO a parquet en R2, y eso cambia lo que se le…
- **#144** — Pedir un original a demanda: el mismo mecanismo de señales que ya tenía la app, aplicado a…
- **#149** — Documentos SUNAT: de dos columnas a APILADO
- **#163** — arquitectura.md creció hasta ser un documento que nadie podía abrir: 115k tokens, y CLAUDE.md…

**Fechas, rangos y cortes** (5)

- **#24** — Un reporte puede necesitar MÁS DE UNA clave de rango de fecha, una por "familia" de gráfico
- **#62** — El corte es un CONJUNTO de días, no un intervalo — por eso tiene su propio modo en el…
- **#63** — Dos controles del MISMO concepto no se pisan el estado, pero igual es un bug (2026-08-09)
- **#65** — Datos demo que no tienen la FORMA del dato real no verifican nada (2026-08-09)
- **#179** — Un atajo de fecha (nuevo o viejo) no sobrevive cambiar de REPORTE y volver — mismo mecanismo…

**Asistente IA** (2)

- **#64** — El stepper del corte NO va dentro de fecha_ajuste_pill (2026-08-09)
- **#69** — El asistente IA consulta los datos con tool calling — y las trampas son de SEMÁNTICA, no de…

**Herramientas de desarrollo** (14)

- **#39** — Inspector (?debug=1): clic derecho solo FIJABA el tooltip, nunca copiaba — y encima el…
- **#46** — inject_diseno_visual (inyecciones/diseno.py) lee estado de inspector.py sin que inspector.py…
- **#56** — Al sacar un blob de JS/CSS embebido a su módulo: NO lo pases a raw string, y verifica el…
- **#151** — Modo diseño fase C — insertar elementos de mentira ("mocks") para ver cómo se vería algo que…
- **#153** — Fase D del modo diseño: paleta de superficie, revertir por propiedad, y "Copiar CSS" para…
- **#155** — Navegar la jerarquía de contenedores era de solo lectura — texto plano para copiar, sin forma…
- **#156** — Un transform en un ancestro CAPTURA a sus hijos position: fixed — y por eso…
- **#158** — Las cinco herramientas de diagnóstico vivían en tres URLs y dos scripts que había que pegar a…
- **#165** — Al agregar una barra de modos quedaron DOS controles del mismo estado, uno encima del otro —…
- **#166** — El contorno del modo diseño se dibujaba ENCIMA del borde real del elemento — así que para ver…
- **#167** — El fondo general de la app no se podía editar con el modo diseño: el lienzo es el único…
- **#168** — Las manijas del modo diseño quedaban FUERA DE LA PANTALLA cuando el elemento tocaba un borde
- **#173** — El overlay del modo diseño tiene pointer-events:none a propósito (para poder ver/medir lo de…
- **#181** — Un bloqueo de interacción SIN acuse de recibo es indistinguible de una app rota — el que…

**Decisiones de diseño y UX** (33)

- **#17** — La franja transparente + fecha-pill-izquierda + chips-centrados-blancos es el DEFAULT para…
- **#18** — Los 8 reportes usan el rail derecho (_render_rail) desde 2026-08-04
- **#20** — Boxplot/histograma con datos mayoritariamente en cero: filtrar el cero ANTES de graficar, no…
- **#61** — Panorama de compras (recetaventa.py, 2026-08-09): 5ª vista del rail de Receta Venta, la…
- **#67** — "Preservar el comportamiento anterior" no es lo mismo que "revisar el mockup" — la regla #66…
- **#75** — Inventario Valorizado v3 (2026-08-10) — de 4 vistas a 3, más un buscador que reemplaza a la…
- **#77** — Tarjeta der desalineada con la izq (2026-08-10) — bug preexistente en…
- **#79** — Click-drill (regla #76) obligaba a hacer scroll para ver el detalle (2026-08-10, mismo día)
- **#84** — [SUPERADA por la regla #85 — el candlestick de esta regla se dio de baja el mismo día]…
- **#85** — El candlestick de "Resumen ejecutivo" (regla #84) se dio de baja el mismo día —…
- **#87** — Todo comparativo período-contra-período tiene que recortar el período EN CURSO — si no, el…
- **#88** — Modo "Descomposición" y drill a platos (2026-08-11) — la identidad Venta = Pax × Ticket es lo…
- **#89** — Styler.format(...) NO aplica el formateador a los None de una columna object: los pinta como…
- **#96** — El item del rail viaja en ?vista=, y el detector de solapamientos tenía que mirar los TRES…
- **#99** — El rail (navegacion.py) reserva su columna con margin-left en .stApp, no con left/padding —…
- **#109** — La franja de controles se propagó a Compras › Familia — y de paso se extrajo el helper…
- **#118** — Los rails se pliegan cambiando UN ancho — y lo que cambia por :has() se DECLARA en la regla…
- **#119** — Nada de transition sobre algo que un rerun pueda pillar a media animación
- **#124** — compras_prov_drill_wrap (drill de Proveedor) pasó de 2 a 3 columnas (ranking / tabla resumen…
- **#131** — Se unificaron "Precio vs año pasado" y "Cantidad vs año pasado" (categorías separadas…
- **#133** — Compras › Proveedor perdió el botón "✕ Quitar foco" del ranking (2026-08-18, a pedido): ahora…
- **#135** — El rail de vistas pasó del borde derecho al IZQUIERDO (2026-08-18) — y lo caro no fue…
- **#137** — La franja y las tarjetas comparten UNA sola línea izquierda (2026-08-19), y el ancla es la…
- **#138** — El rail subió a la altura de la franja (2026-08-19), y eso obligó a recortar la banda blanca
- **#147** — El rail de Compras en formato LISTA (icono + nombre + chevron)
- **#149** — Documentos SUNAT: de dos columnas a APILADO
- **#150** — Mover un widget de sitio cuando su KEY es el estado: el pill de fecha de la franja
- **#164** — El botón Refrescar dejó de vivir en la franja superior de navegación y pasó al pie del rail…
- **#166** — El contorno del modo diseño se dibujaba ENCIMA del borde real del elemento — así que para ver…
- **#168** — Las manijas del modo diseño quedaban FUERA DE LA PANTALLA cuando el elemento tocaba un borde
- **#169** — El CSS que exporta el modo diseño es una FOTO DE PÍXELES, no la intención: pegarlo tal cual…
- **#170** — Se invirtieron Reportes y Vistas: Reportes al rail vertical izquierdo, Vistas a la franja…
- **#181** — Un bloqueo de interacción SIN acuse de recibo es indistinguible de una app rota — el que…

**Mantenimiento y trampas del lenguaje** (6)

- **#21** — Columnas reales de salidas.parquet confirmadas 2026-08-04
- **#43** — st.plotly_chart(..., selection_mode="points") NO agrega las herramientas de caja/lazo al…
- **#53** — ruff --fix sobre F401 puede romper re-exports deliberados
- **#54** — Un callback inyectado necesita UNA firma, no una por llamador
- **#56** — Al sacar un blob de JS/CSS embebido a su módulo: NO lo pases a raw string, y verifica el…
- **#132** — El rail de navegación dejó de ser una columna izquierda de 90px y pasó a ser una franja…

<!-- INDICE:FIN -->

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

162. **`st.markdown(..., unsafe_allow_html=True)` cuyo HTML arranca con un tag
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
    - **El área SOLA no alcanza: falta un corte por CANTIDAD** (encontrado
      2026-08-21 pineando el rail, `compras_tabs_row`). El rail son ~12
      `st.button` apilados con `use_container_width=True`, cada uno casi
      tan ancho como la tarjeta: la SUMA de anchos daba ~2.400px contra 230
      de ancho del contenedor (ratio ≈10), así que el `>=60%` daba
      verdadero SIEMPRE. Resultado: el contorno violeta marcaba la tarjeta
      y los sliders escribían en los 12 items — el único síntoma era un
      cambio que aparecía donde no se esperaba. La suma de anchos supone
      botones repartiéndose UNA fila; en una columna no significa nada.
      **Arreglo (dos cortes, en orden):** primero cantidad — varios botones
      SUELTOS (fuera de un `[data-testid="stButtonGroup"]`) = el elemento
      es una LISTA de botones y no se redirige; después el área de siempre,
      que ahora solo decide entre "pills de un mismo grupo" y "un botón
      suelto en su wrapper". Sospecha para la próxima vez: cualquier
      criterio que sume una dimensión asume implícitamente un EJE (fila);
      probarlo también contra el caso apilado antes de confiar.
    - **Y el contorno no puede mentir:** el overlay trackea siempre el
      elemento pineado (`trackear(res.el)`), no el destino del estilo, así
      que cuando la redirección aplica hay dos objetivos distintos en
      pantalla y uno solo dibujado. El panel ahora abre con una línea
      `Estilo → N botones internos. Tamaño y posición → el contorno.`
      cuando `destinosDeEstilo(elemento)[0] !== elemento`.
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

100. **"Nueva Receta": tercer miembro de `grupo_nav: "Recetas"`, y por qué
     es `tool: True` en vez de una tercera entrada con `archivo`
     (2026-08-13).** El pedido: un formulario para armar y costear una
     receta de venta a mano y dejarla como propuesta para que otra persona
     la vea — sin agregar un ícono nuevo al rail. La regla #97 ya había
     resuelto "varias entradas, un ícono" para Base/Venta; acá el reto
     distinto era sumar una TERCERA entrada al mismo grupo que **no lee
     ningún parquet propio** (no tiene `fecha`/`archivo` — arma su tabla en
     memoria contra `inventariovalorizado.parquet`, que ya carga otro
     reporte).

     **Encaja en el grupo sin tocar `navegacion.py`.** El agrupado por
     `grupo_nav` (regla #97) ya es genérico: dibuja un botón por valor de
     `grupo_nav`, sin asumir cuántos miembros tiene ni si son reportes de
     parquet. Sumar "Nueva Receta" a `REPORTES` con
     `"grupo_nav": "Recetas"` alcanzó — cero cambios en
     `navegacion.py::inject_navegacion`.

     **Pero SÍ necesita `"tool": True`.** Un miembro de grupo normal
     (Base/Venta) espera pasar por el pipeline de `app.py` (`cargar()`,
     filtro de fecha, `fecha_ultima_actualizacion`, botón de refresco) — no
     hay parquet propio para ese pipeline acá. Con `tool: True`, app.py lo
     desvía ANTES de ese pipeline (mismo bloque que ya usaba Inspector,
     visto en regla previa de `_TOOLS`). Efecto práctico: `formulario_receta.py`
     se ocupa de cargar `inventariovalorizado.parquet` por su cuenta
     (`data.cargar()` directo, mismo precedente que
     `graficos/recetaventa.py`/`recetas_comun.py` cruzando contra
     `compras.parquet`).

     **`app.py` pasó de un import fijo a un dict `_TOOLS`.** Hasta este
     commit, `if cfg.get("tool"):` importaba `render_inspector` a mano —
     funcionaba con una sola herramienta porque **cualquier** reporte con
     `tool: True` disparaba SIEMPRE el mismo render. Con una segunda
     herramienta hacía falta elegir cuál — `_TOOLS = {"Inspector": ...,
     "Nueva Receta": ...}; _TOOLS[reporte]()`, mismo espíritu que
     `_DASHBOARDS` en `graficos/__init__.py` (dict, no cadena de if/elif).

     **`_chip_fuente` (regla #97) suma un tercer segmento sin tocar su
     mecanismo.** El chip ya navegaba escribiendo
     `session_state["_nav_reporte"]` + `st.rerun()` — el mismo camino que
     usa el rail. Agregar `"Nueva Receta": "+ Nueva"` al diccionario de
     etiquetas alcanzó; clic en "+ Nueva" desde Base o Venta navega igual
     que clic en cualquier ítem del rail, y `formulario_receta.py` llama al
     mismo `_chip_fuente("Nueva Receta")` arriba de todo para poder volver.

     **Guardar es una PROPUESTA en R2, nunca una escritura a
     `recetaventa.parquet`.** Mismo principio que `solicitar_refresco()`:
     la webapp no genera datos fuente, solo señales que un proceso humano o
     externo revisa después. `formulario_receta.py::_guardar_propuesta()`
     reusa `get_s3_cliente()` + `put_object()` tal cual, apuntando a
     `_recetas_propuestas/<uuid>.json` en vez de `_solicitudes_refresco/`.
     Sin secrets de R2 (modo demo), no escribe nada — muestra con
     `st.json()` el payload que se habría guardado, mismo criterio que
     `secrets_disponibles()` ya usa en el resto de `data.py`.

     **Columna `Activo` de `inventariovalorizado.parquet`: NO se asumió.**
     A diferencia de la regla #97 (los 4 formatos de activo de
     recetabase/recetaventa, confirmados contra R2 real), este parquet no
     se verificó — `_resolver()` con candidatos razonables
     (`"Activo"`/`"ACTIVO"`/`"Estado"`) y degradación silenciosa (sin
     insignia) si no aparece ninguno. Contra R2 real de producción, ningún
     candidato matcheó — la insignia simplemente no se muestra, sin error.
     Si en algún momento se confirma el nombre real, sumarlo a la lista de
     candidatos es todo el cambio que hace falta.

     **Alcance v1, a propósito — ver docstring de `formulario_receta.py`
     para el detalle completo:** solo pestaña Receta de Venta. Quedan
     afuera de este commit: Combo, crear Receta Base desde acá, envío por
     correo (sin `SMTP_USER`/`SMTP_APP_PASSWORD` en secrets todavía),
     exportar a Excel/PDF, un visor de las propuestas ya guardadas en R2, y
     Grupo/SubGrupo (sin fuente real definida para esa taxonomía).

     **Actualización (mismo día): se sumó Combo como segundo modo.** Un
     `st.segmented_control` propio DENTRO de "Nueva Receta" (no confundir
     con el chip Base/Venta/Nueva de arriba, que elige entre reportes)
     alterna "Receta de venta" / "Combo". Combo arma su línea con
     PRODUCTOS DE VENTA, no insumos: catálogo derivado en vivo de
     `recetaventa.parquet`, agrupado por `Nomb Plato` con `_activo()` ya
     aplicado (igual criterio que `_panorama_compras_venta`), costo =
     suma de `Total` de sus ítems. Toda la lógica de línea/tabla/costeo/
     guardado (`_agregar_linea`, `_tabla_lineas`, `_mostrar_pricing`,
     `_guardar_propuesta`) se parametrizó por `modo` en vez de duplicarse
     — mismo espíritu que `graficos/recetas_comun.py` con Base/Venta
     (regla #97): ambos catálogos se normalizan a las mismas 5 columnas
     (`cod`/`nombre`/`unidad`/`precio`/`activo`) para que el buscador y la
     tabla no necesiten saber de qué parquet vino cada uno.

     **Trampa nueva, para la lista de CLAUDE.md:** el preview local
     tampoco recoge en caliente los cambios de un módulo `.py` normal si
     el server ya estaba corriendo de una sesión anterior — mismo síntoma
     que ya está documentado para `estilos/`, pero acá se manifestó en
     `formulario_receta.py`: un mensaje corregido en el código seguía
     saliendo viejo en el navegador hasta reiniciar el server. Reiniciar
     (no solo recargar la pestaña) es el fix, igual que para estilos.

     **Verificación:** `ruff check` + `test_graficos.py` +
     `test_asistente_datos.py` en verde. `streamlit run` contra R2 real
     (no demo): nav agrupado sin ícono nuevo, chip con el 3er segmento
     "+ Nueva", búsqueda de insumos contra `inventariovalorizado.parquet`
     real ("pollo" → 8 resultados reales, con código/unidad/precio),
     alta de línea y costeo correctos (Pechuga De Pollo S/ 12.62 → costo
     total S/ 12.62 con 1 unidad). El botón Guardar NO se probó en vivo a
     propósito, para no escribir un registro de prueba en el R2 de
     producción — su código reusa `get_s3_cliente()`/`put_object()` sin
     modificar, ya probado en producción por `solicitar_refresco()`.

     **Actualización (mismo día): visor "Guardadas" + primera escritura
     real en R2 + un crash real que solo aparece con datos de
     producción.** El picker de modo pasó a 3 opciones (`Receta de venta` /
     `Combo` / `Guardadas`). `_listar_propuestas_guardadas()` (cacheada,
     TTL 60s) hace `list_objects_v2` sobre `_recetas_propuestas/` y lee
     cada JSON con `get_object` — un objeto individual corrupto/parcial se
     salta con `try/except` en vez de tirar abajo la lista completa (puede
     pasar si alguien mira la carpeta mientras otra persona está
     guardando). `_render_guardadas()` es de solo lectura: un
     `st.expander` por propuesta con guardado_por/fecha/porciones/precio y
     la tabla de líneas — cargar-para-editar queda para después.

     **Esta vez sí se probó Guardar de verdad contra R2 de producción**
     (la entrada de arriba decía explícitamente que no, para no ensuciar
     datos reales) — con nombres `TEST ... (borrar)` para poder
     identificar y borrar los objetos de prueba después (script de un solo
     uso con el mismo `get_s3_cliente()`, filtrando por
     `nombre.startswith("TEST")`, corrido al terminar — 0 objetos quedaron
     bajo `_recetas_propuestas/`). Confirmó el circuito completo: guardar
     → aparece en Guardadas incluso con el server reiniciado de cero (o
     sea que es R2 de verdad, no session_state) → cifras (costo, % de
     costo, margen) coinciden con lo calculado en el formulario.

     **Bug real encontrado así, que ningún test automático iba a agarrar:**
     `inventariovalorizado.parquet` trae **más de una fila para el mismo
     código de producto** (confirmado en vivo: "Sal De Mesa" 0000460
     aparece dos veces). `_buscador_catalogo` arma un botón "Agregar" por
     fila con `key=_key(modo, f"add_{cod}")` — dos filas con el mismo
     `cod` dentro del mismo resultado de búsqueda ⇒
     `StreamlitDuplicateElementKey`, la app revienta. La búsqueda amplia
     ("sal", 8 resultados con muchos códigos distintos) nunca lo mostró
     porque el cupo de 8 se llenaba con otros productos antes de que
     entraran las dos filas duplicadas — hizo falta una búsqueda
     ESPECÍFICA ("sal de mesa") para que ambas cayeran en el mismo
     resultado y colisionaran. **Fix:** `.drop_duplicates(subset="cod",
     keep="first")` en `_catalogo_insumos_cacheado()` (y, preventivo, lo
     mismo en `_catalogo_productos_venta_cacheado()`, por si un
     `COD PLATO` se reusara entre dos platos con nombre distinto — el
     `groupby` de ahí ya deduplica por nombre, pero no por código).
     **Lección:** un dataset de producción puede tener filas duplicadas
     por código aunque nada en el pipeline lo espere; cualquier catálogo
     que alimente un `key=` de Streamlit armado con un campo
     "identificador" necesita su propio `drop_duplicates` explícito — no
     asumir que el campo es único solo porque se llama código.

     **`_limpiar_modo(modo)` deja `guardado_por` sin tocar, a propósito**
     — nombre/porciones/precio son de ESA receta, pero quien guarda
     probablemente guarde varias seguidas y no quiere reescribir su
     nombre cada vez. Ojo con la trampa al VERIFICAR esto en el
     navegador: cambiar de pestaña (Receta de venta → Combo → Receta de
     venta) **también** vacía los widgets de texto/número aunque no se
     haya guardado nada — no es `_limpiar_modo`, es Streamlit limpiando el
     session_state de un widget que no se instanció en el run anterior.
     La lista `lineas` (session_state plano, no pasa por `key=` de ningún
     widget) no sufre este efecto y sobrevive el cambio de pestaña sin
     problema. Nota aparte: como `_limpiar_modo` no llama `st.rerun()`, el
     run que procesa el clic en "Guardar" ya dibujó los widgets arriba con
     los valores viejos antes de llegar al `if st.button(...)` — el
     mensaje de éxito aparece, pero el formulario recién se ve vacío en la
     SIGUIENTE interacción (buscar el próximo insumo, por ejemplo). No es
     un bug — agregar `st.rerun()` ahí se consideró y se descartó SIN
     probarlo (no llegó a escribirse): `st.rerun()` justo después de
     `st.success()` es un patrón conocido de Streamlit para tragarse el
     mensaje de éxito (la rerun reemplaza la salida antes de que se
     alcance a ver); el reemplazo correcto sería `st.toast()`, que sí está
     documentado para sobrevivir un rerun — queda pendiente para si el lag
     visual molesta en el uso real.

     **Verificación (esta ronda):** `ruff check` + `test_graficos.py` +
     `test_asistente_datos.py` en verde otra vez. Server reiniciado en
     puerto nuevo (no solo recargado) por la trampa de la entrada
     anterior. Guardado real x2, visor Guardadas mostrando ambas con
     cifras correctas, reproducción y fix del crash de código duplicado
     con el mismo caso real que lo disparó, y limpieza posterior de los 2
     objetos de prueba en R2.

101. **El presupuesto vertical: una tarjeta = una pantalla, y `graficos/alturas.py`
     es su único dueño (2026-08-13).** El pedido era simple —"que la tarjeta
     del gráfico se vea completa en desktop"— y la app estaba lejos: el alto
     de cada figura era un literal escrito a mano (**41 números en 15
     ficheros**, más 19 fórmulas por nº de filas de las cuales **7 no tenían
     tope superior** y crecían sin límite con los datos reales). Nada leía el
     tamaño de la pantalla. Medido en el navegador antes de tocar nada: **9 de
     24 vistas** obligaban a scrollear en 1536x864 y **19 de 24** en un laptop
     de 1366x768; el Resumen ejecutivo de Ventas medía 1364px y se veía al
     37%.

     **El cromo fijo son 156px** (58 de `--cab-offset-contenido` + 16 de
     margen + 66 de `--franja-inf-reserva` + 16 de margen inferior), así que
     el presupuesto es `viewport − 156`. Verificado dos veces contra el DOM:
     con viewport 864 el presupuesto da 708 y la vista "Matriz" (742px)
     desbordaba **exactamente** 34px; con viewport 657 da 501 y "Por día"
     (584px) desbordaba **exactamente** 83px.

     **Dos dueños, uno por mundo, como los colores de la regla #1:**
     - **`graficos/alturas.py`** (Python) — el alto de las FIGURAS. Roles
       semánticos `PROTAGONISTA` (430) / `APOYO` (380) / `MINI` (240), más
       `por_filas()` y `apilado()`. Regla: **nunca un alto suelto**, gemela de
       «nunca un `#hex` suelto».
     - **`--alto-util`** en `estilos/_00_base.py` (CSS) — el MARCO de la
       tarjeta, derivado de las variables de las franjas para que el
       presupuesto las siga si alguna cambia de alto.

     Los dos cuentan la misma geometría y nada los une salvo
     `test_graficos.py::_pruebas_presupuesto_vertical`, que falla si se
     desincronizan **o si reaparece un literal** en `graficos/`.

     **La estrategia es ENCUADRAR, no comprimir.** La tarjeta se clampea a
     `--alto-util` y lo que no entra scrollea DENTRO de ella
     (`estilos/_80_cards.py`). Comprimir todo a una pantalla se evaluó y se
     descartó: el Resumen ejecutivo son 5 KPIs y 3 gráficos, y meterlos en
     501px da tres gráficos de ~150px — se cambiaba "hay que scrollear" por
     "no se lee nada". Con el encuadre el scroll de página quedó en **0 en
     todas las vistas** de los 4 dashboards medidos.

     **Trampa al migrar:** `ventas_resumen.py` tenía una variable local
     llamada `alturas` (proporciones de `row_heights`) que tapaba al módulo
     dentro de la función; `alturas.MINI` habría reventado con `AttributeError`
     sobre una lista. Lo cazó `ruff` (F401: el import quedaba "sin usar"), no
     una prueba — es la razón de pasar `ruff` antes de dar por buena una
     migración masiva.

102. **Un `height` en CSS sobre un bloque de Streamlit NO HACE NADA, y
     `height="stretch"` no llega al SVG de Plotly (2026-08-13).** Dos
     hallazgos de un banco de pruebas levantado a propósito, ambos
     contraintuitivos y ambos capaces de quemar una tarde:

     - **Los bloques son flex items con `flex: 1 1 0%`.** En un contenedor
       flex de columna el tamaño principal lo fija `flex-basis`, no `height`,
       así que una regla `.st-key-x { height: calc(...) !important }` se
       ignora en silencio (medido: seguía en 406px en vez de los 501 pedidos;
       con `flex: 0 0 auto` pasó a 501). **`max-height` sí clampea** al flex
       item — y además es lo correcto aquí, porque con `height` las tarjetas
       cortas se estirarían a pantalla completa (Volatilidad mide 88px).

     - **Plotly no llena su contenedor en este stack** (Streamlit 1.59 +
       Plotly 6.9). `st.plotly_chart(fig, height="stretch")` estira el wrapper
       de Streamlit (medido: 738px) pero el SVG se queda en 450. Con
       `autosize:true`, la cadena de contenedores forzada a `height:100%` y un
       `Plotly.Plots.resize()` explícito: **sigue en 450**. Sólo
       `fig.layout.height` manda (`Plotly.relayout(gd, {height:700})` → 700
       exactos). Por eso el alto de las figuras se decide en Python y no con
       `dvh`, y por eso `fig.layout.height` hay que QUITARLO si algún día se
       quiere que `stretch` funcione: cuando está puesto, gana siempre.

103. **El `title=` de una figura y la leyenda horizontal de `_compras_layout`
     se pelean el MISMO espacio, y se dibujan encimados (2026-08-13).**
     `_compras_layout` (graficos/base.py) fija dos cosas que no se pueden
     cumplir a la vez:

     ```python
     margin=dict(l=10, r=10, t=30, b=10),
     legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
     ```

     Plotly dibuja el título DENTRO del margen superior, pegado a la
     izquierda; la leyenda horizontal en `y=1.02 / x=0` cae en esa misma
     banda de 30px y arranca en el mismo borde. Con las dos cosas puestas,
     el título y las etiquetas de las series se superponen — se leyó en
     producción como `Venta bruta por día` tachado por `■ Venta ■ Costo`.

     No da error, no lo caza `test_graficos.py` (la figura se construye
     perfecta) y en el DOM los dos textos existen y son legibles por
     separado: es exactamente el caso de la regla #91 — el SVG "funciona"
     pero no "se ve". Sólo aparece midiendo las cajas
     (`herramientas/auditar_graficos.js`) o mirando el gráfico.

     **Regla:** en un gráfico con leyenda visible, el título NO va dentro de
     la figura. Va como cabecera de la tarjeta, arriba de la franja de
     controles. Ver `graficos/ventas.py::_ventas_grafico_dia`, que además
     usa esa cabecera como el techo de la franja (regla #104).

     Quedan sin auditar los otros `title=` de nivel figura
     (`graficos/compras/__init__.py`, `ajuste/_evolucion.py`,
     `ajuste/_distribucion.py`, `movimientos_comun.py`, `ventas.py:261` y
     `:1268`): chocan sólo si además muestran leyenda con más de una serie.

104. **La franja de controles necesita CONTENIDO arriba para poder tener
     línea superior (2026-08-13).** Los toggles de Ventas › Por día vivían
     sobre una sola línea (el `<hr>` de abajo). Al pedir la franja cerrada
     por dos líneas — como la de un gráfico bursátil — la de arriba no tenía
     dónde ir: el toggle está a 4px del borde de la tarjeta
     (`margin-top` negativo + `padding: 16px 18px`), así que una línea ahí
     se lee como un doble borde de la propia tarjeta, no como el techo de
     una banda.

     La solución fue meterle el título del gráfico (que además había que
     sacar de la figura por la regla #103): **título → línea → tabs → línea
     → gráfico**. Medido en el navegador a 1280x720, tarjeta de 957px:

     | pieza          | y (desde el tope de la tarjeta) |
     |----------------|---------------------------------|
     | título         | 10                              |
     | línea superior | 41.8                            |
     | tabs           | 47.8 – 79.8                     |
     | línea inferior | 88.3                            |
     | gráfico        | 111.8                           |

     Aire de 6px arriba de los tabs y 8.5px abajo — no son simétricos a
     propósito: el botón trae 4px de padding propio, así que el TEXTO queda
     a 10px de la línea de arriba y el SUBRAYADO del activo a 8.5px de la de
     abajo, que es lo que se ve.

     **Tres números acoplados** (si se toca uno, medir los otros dos): el
     `margin: -6px -18px 0` de la cabecera, el `margin-top: 6px` del toggle
     en `estilos/_80_cards.py` y el `margin: -15px -18px 14px` del `<hr>`.
     Los `-18px` + `width: calc(100% + 36px)` de cabecera y `<hr>` compensan
     el padding horizontal de la tarjeta para que las líneas toquen el borde
     REAL; sin eso quedan cortas por los dos lados.

     **Trampa al medir:** si la tarjeta desborda y scrollea por dentro, la
     barra se come ~10px y las dos líneas miden 10px menos de ancho que la
     tarjeta. No es un bug de las líneas — desaparece cuando la tarjeta
     entra completa.

105. **El presupuesto vertical contaba la figura pero NO la franja de
     controles (2026-08-13).** `alturas.py` afirmaba `PROTAGONISTA + padding
     = 462 <= 501` y el assert daba verde mientras la tarjeta real medía
     558px. Faltaba un sumando: los controles que van ARRIBA de la figura
     dentro de la misma tarjeta.

     Consecuencia medida en el laptop objetivo (1366x657, `--alto-util` =
     501): la tarjeta desbordaba 57px por dentro y **el eje X quedaba 25.7px
     por debajo del borde** — invisible sin scrollear dentro de la tarjeta.
     El peor modo de fallo posible: el gráfico se ve perfecto, sólo que sin
     eje, así que nadie sospecha del alto.

     Se arregla pidiendo `alturas.con_franja()` en vez de
     `alturas.PROTAGONISTA` cuando la tarjeta tiene franja: 469 de contenido
     - 96 de franja = 373px de figura, y 373 + 96 + 32 = 501 exacto.

     **Lo que este arreglo NO resuelve** (escrito acá para que nadie lo lea
     como cerrado):

     - `FRANJA_CONTROLES = 96` es un número MEDIDO A MANO. Nada lo deriva y
       ningún test lo compara contra el DOM real: si alguien toca el
       `font-size` del título o el padding de los tabs, queda obsoleto en
       silencio. El assert sólo verifica la aritmética interna.
     - Sólo se aplicó a Ventas › Por día. Los ~15 módulos que dibujan
       `st.pills` encima de su figura siguen pidiendo `PROTAGONISTA` como si
       la figura fuera sola. Sin auditar.
     - **La raíz sigue ahí:** el MARCO es CSS (`--alto-util`, `100dvh`, se
       adapta a cualquier pantalla) pero el alto de la FIGURA es una
       constante de Python calibrada para UNA pantalla (657px de viewport
       útil). En 1920x1080 la figura se queda en 373 y desperdicia ~300px;
       en cualquier pantalla menor al objetivo vuelve a desbordar. La causa
       es la regla #102 (Plotly no llena su contenedor en este stack, así
       que el alto sale de Python) y Python nunca se entera del viewport.
       El arreglo de verdad es meter `window.innerHeight` en session_state
       una vez por sesión (vía `components.html`, que sí ejecuta JS — a
       diferencia de `st.markdown`, regla de CLAUDE.md) y derivar
       `PRESUPUESTO` de ahí en vez del 657 hardcodeado.

106. **El alto de una figura SÍ puede salir del CSS — la regla #102 estaba
     mal (2026-08-13).** Un banco de pruebas nuevo, esta vez quitando
     `fig.layout.height` en vez de dejarlo puesto, dio lo contrario de lo
     que decía #102:

     | viewport | hueco del contenedor | SVG |
     |----------|----------------------|-----|
     | 1920x1000 | 602 | **602** |
     | 1600x950  | 552 | **544** |
     | 1366x657  | 259 | **251** |

     Sin `fig.layout.height`, Plotly lee el alto de su contenedor CSS. El
     desfase constante de 8px es el modebar. Lo que #102 midió — "el SVG se
     queda en 450" — era el default de Plotly cuando la cadena de
     contenedores no tiene alto, no una incapacidad de Plotly.

     **Lo que sí sigue siendo cierto, y es la limitación real:** lo lee UNA
     vez, al MONTAR. Nada lo recalcula después. Medido, los cuatro caminos:

     | intento sobre el gráfico ya montado | resultado |
     |---|---|
     | evento `resize` de la ventana | sin cambio |
     | `config={'responsive': True}` | sin cambio |
     | `Plotly.Plots.resize(gd)` | sin cambio |
     | `Plotly.relayout(gd, {height: N})` | **sin cambio** |
     | rerun de Streamlit (clic en un widget) | sin cambio |

     Ojo con la penúltima: #102 afirma que `Plotly.relayout(gd,
     {height:700})` da 700 exactos. Con Streamlit 1.59 + Plotly 6.9, y con
     el `hueco` bien calculado y `window.Plotly` presente, es un **no-op**
     (`_fullLayout.height` no se mueve). Eso mata la salida elegante — un
     `ResizeObserver` que le avise a Plotly — y deja sólo dos caminos para
     reaccionar a un resize: **remontar el componente** (cambiar su `key`
     desde Python, conserva `session_state`) o **recargar la página**
     (descartado: borra los filtros, que viven en `session_state` y no en la
     URL).

     **Cómo se pide:** `alturas.ELASTICO` como `alto=` + `height="stretch"`
     en `st.plotly_chart` + el CSS de `estilos/_80_cards.py`. Los tres son
     necesarios; con dos no alcanza.

     **Tres trampas del CSS, las tres medidas:**

     - `flex: 0 0 auto` en la tarjeta es OBLIGATORIO antes de darle `height`
       (regla #101), si no se ignora en silencio.
     - `min-height: 0` en el elemento del gráfico: sin él, el `min-height:
       auto` de un flex item le impide ENCOGER por debajo de su contenido y
       la tarjeta desborda en pantallas chicas.
     - **NUNCA `> div { height: 100% }`** sobre el bloque de la tarjeta: le
       pega a TODOS los hijos y el flex les reparte el alto en partes
       iguales — medido en el banco, título, tabs y gráfico quedaban en
       214.7px cada uno. Hay que acotar a la key del gráfico.

     **Ancla `:has()`, no la key de la tarjeta:**
     `ajuste_graf_card_izq_ventas` la comparten TODAS las vistas de Ventas,
     así que darle alto fijo estiraría también el Resumen ejecutivo (1364px,
     largo a propósito). El selector cuelga de la key del PROPIO gráfico:
     `div[class*="st-key-ajuste_graf_card_"]:has([class*="st-key-ventas_g_dia"])`.
     Verificado: en Resumen la regla no matchea (`flex` sigue en `1 1 0%`).

     **Resultado en Ventas › Por día:**

     | | 1366x657 | 1920x1000 |
     |---|---|---|
     | antes (373 fijos) | figura 373, eje OK | figura 373, **343px desperdiciados** |
     | ahora (ELASTICO) | figura 373, eje OK | figura **716**, **0 desperdiciados** |

     **Pendiente:** sólo se migró esta tarjeta, y falta el paso 2 (remontar
     por `key` al cambiar el viewport). Hasta que exista, arrastrar la
     ventana entre dos pantallas deja el gráfico del tamaño anterior hasta
     el siguiente F5. En móvil el bloque no aplica (va dentro del
     `@media (min-width: 769px)`) y Plotly usa su default de 450px, que con
     scroll de página es correcto.

107. **La franja de controles con VARIOS grupos: separadores colgados del
     grupo, anchos por caso, y la regla #70 mordiendo otra vez
     (2026-08-13).** Ventas › Año Pasado tenía cuatro grupos de toggles
     sueltos ARRIBA de la tarjeta (`st.columns` + un `st.pills` de "Vista"
     en su propia fila). Se metieron dentro de la misma franja de dos líneas
     que Por día (#104). Tres cosas que costaron medición:

     - **Separadores colgados del GRUPO, no de la posición.** Los tres
       grupos de la izquierda ("cómo corto el tiempo") van separados por
       hairlines verticales; cada uno dibuja el suyo a su IZQUIERDA con un
       `::before` colgado de su key. Con una regla por posición, al
       desaparecer "alinear por" (sólo existe en granularidad Día) quedaría
       una línea suelta anunciando un grupo que no está. "Vista" es el otro
       eje y NO lleva separador: se separa con espacio.

     - **Los anchos de columna dependen de la granularidad.** Con los anchos
       de Día, en Semana/Mes las etiquetas de "Ventana" pasan de "7 días" a
       "12 semanas", no entran y ENVUELVEN: la franja pasaba de 52px a
       143px. El ancho que sobra al no haber alineación es justo el que
       necesita Ventana, así que la lista de ratios se elige por caso.

     - **El `st.container(key=...)` de la tarjeta retenía el layout viejo.**
       Al pasar de Día a Semana, Python quedaba correcto (el título decía
       "semana a semana" y Ventana traía opciones de semanas) pero el DOM
       conservaba las CINCO columnas de Día y el pills de "alinear por"
       seguía ahí, huérfano, envolviendo a dos filas — franja de 156px. Es
       la regla #70 otra vez, ahora disparada por meter contenido
       CONDICIONAL dentro de un contenedor con key. Se arregla metiendo la
       granularidad en la key de la tarjeta
       (`_card(f"ventas_comparativo_{grano}")`): al variar, remonta limpia.
       Reproducido con Semana y con Mes; medido antes y después.

     **Y una que NO se pudo hacer con CSS:** alinear "Vista" a la derecha con
     `justify-content: flex-end` no funciona. El div flex interno del
     `stButtonGroup` se queda en su ancho de contenido (165px) aunque se le
     fuerce `width: 100% !important` en los TRES niveles de la cadena
     (element container, stButtonGroup y el div). Lo empuja una **columna
     espaciadora vacía**, que además degrada sola cuando la tarjeta se
     angosta.

     **Orden de rendering:** la franja se dibuja antes de que existan sus
     propios valores, así que hay tres huecos reservados —
     `_ph_hdr` (el título depende de grano/modo/vista), `_ph_vista` ("Vista"
     depende de `hay_pax`, que depende de los datos, que dependen de los
     controles de la misma franja) y `_slot_graf`. Los placeholders son lo
     que rompe la circularidad sin re-indentar las ~400 líneas de cálculo
     que hay en el medio.

     Medido a 1366x657, tarjeta de 997px — franja de **52px** en los tres
     granos, sin envolver, y "Vista" a menos de 1px del borde derecho.

     **Corrección el mismo día:** el ajuste de "Vista" no tenía margen. El
     contenedor se shrink-wrappea a su contenido (`display: block` +
     `flex-wrap: wrap` en su hijo, sin `width` propio), así que su ancho es
     SIEMPRE el mínimo necesario para el texto — "Montos" + gap +
     "Descomposición" medían 165px, y la columna que lo alojaba en el caso
     de trabajo tenía justo 165px de sobra: **0px de margen.** Cualquier
     ventana un poco más angosta que la usada al medir empuja la columna por
     debajo de esos 165px, y ahí el shrink-wrap dejó de poder darle todo el
     ancho que pedía: el texto cae a dos líneas. Reproducido bajando el
     viewport a 1100px (tarjeta 731px): las dos opciones se apilaban.

     Se arregla con `flex-wrap: nowrap` en el `stButtonGroup` interno de
     "Vista" — nunca vuelve a apilar; en el peor caso, sale unos px a la
     derecha de su columna en vez de crecer en alto, y sigue dentro del
     borde de la tarjeta (verificado: a 731px de tarjeta, el último botón
     termina en 715px). Además se le movieron 0.2 de ratio al espaciador
     vecino, que no lo necesita. Verificado sin apilar en 1366, 950, 881,
     731 y 581px de tarjeta — por debajo de ~880px empiezan a envolver los
     OTROS tres grupos (grano/ventana/alineación), que es una degradación
     aparte y esperable en ventanas angostas, no el bug reportado.

     **Segunda corrección el mismo día — más grave, dead CSS desde el primer
     commit:** el estado "activo" (negrita + color + subrayado) de los
     cuatro grupos JAMÁS se pintó. La regla usaba
     `button[data-variant="pills"][aria-pressed="true"]`, copiada del
     patrón de "Por día" — pero ese widget es `selection_mode="multi"` y
     Streamlit lo marca con `role="checkbox"` + `aria-pressed`. Los cuatro
     de esta franja son single-select (sin `selection_mode=`, el default),
     y ahí Streamlit usa `role="radio"` + `aria-checked` + `data-selected`
     — verificado con `outerHTML` en el navegador: el botón activo por
     defecto ("Día") no tenía `aria-pressed` en NINGÚN valor. El selector
     nunca matcheaba, así que los cuatro grupos se veían siempre "apagados"
     — visualmente correctos en el mockup, muertos en el código real.

     **Lección:** copiar un selector de `[atributo="valor"]` entre dos
     widgets del mismo tipo (`st.pills`) sin verificar el `selection_mode`
     de cada uno es exactamente el tipo de bug que no truena — no hay
     error, no hay warning, el CSS "existe" y hasta pasa lint. Sólo se ve
     mirando el `outerHTML` real o clickeando en el navegador. Corregido a
     `[data-selected="true"]`; verificado con clic real en los cuatro
     grupos (incluida la combinación "Semana" + "8 semanas" del caso
     degradado): `font-weight` pasa de 400 a 600, el color a
     `rgb(73,56,184)` y el `border-bottom` a `rgb(108,92,231)`.

108. **`st.empty()` BORRA su contenido al crearse: un placeholder que se
     rellena tarde es un salto de layout en cada clic (2026-08-13).** La
     franja de Año Pasado (#107) reservaba la cabecera con `_ph_hdr =
     st.empty()` al abrir la tarjeta y la rellenaba al FINAL del script,
     después de traer las dos series de R2. En cada clic sobre cualquier
     toggle eso producía:

     - la cabecera quedaba vacía durante toda la carga → el título
       desaparecía y todo lo de abajo subía ~42px, para volver a bajar
       cuando llegaba;
     - la tarjeta colapsaba a ~90px (sólo la franja) y volvía a ~470 cuando
       aparecía el gráfico.

     Reportado por el usuario como "hace como un refresco y se mueve como si
     subiese y bajase el gráfico".

     **Ojo con el diagnóstico fácil:** NO era falta de `@st.fragment` —
     `_ventas_comparativo` ya era fragment desde antes, así que el rerun ya
     estaba acotado. Era el orden de relleno de los placeholders, que es
     invisible leyendo el código: sólo se ve muestreando el DOM durante el
     clic (`setInterval` cada 50ms sobre el alto de la tarjeta).

     **Arreglo, dos partes:**

     - La cabecera se pinta DOS veces: una provisional apenas se conocen los
       controles, leyendo `vista` de `session_state` (su valor del rerun
       anterior, que acierta casi siempre), y otra al final con el valor
       real. Si coinciden, Streamlit no toca el DOM. De ahí que el título
       viva en `_titulo_comparativo()` y el pintado en `_pintar_cabecera()`:
       se llaman desde dos sitios.
     - `min-height` en la tarjeta, para que no colapse mientras carga:
       32 de padding + 42 de cabecera + 52 de franja + 340 de figura = 466.
       `min-height` y no `height` — el caption y el panel "Detalle" pueden
       hacerla más alta.

     **Medido con muestreo cada 50-60ms durante el clic:**

     | | antes | después |
     |---|---|---|
     | frames sin título | muchos | **0** |
     | frames sin gráfico | muchos | **0** (cambio de ventana) |
     | tarjeta ausente | — | **0** |
     | salto de alto (cambio de ventana) | ~380px | **0** |

     **Lo que NO quedó resuelto:** al cambiar de GRANULARIDAD sigue habiendo
     un transitorio de ~600ms con un salto de 104px (573 → 677 → 573) y un
     frame sin gráfico. Es inherente a que ese caso REMONTA la tarjeta a
     propósito — la key lleva la granularidad para no arrastrar el layout
     viejo (#107) — así que la franja y el caption se re-maquetan antes de
     que vuelva la figura. Cambiar ventana o vista, que no remontan, ya no
     saltan nada.

109. **La franja de controles se propagó a Compras › Familia — y de paso se
     extrajo el helper compartido que #104/#107/#108 dejaron pendiente
     (2026-08-13).** Tres decisiones de esta migración que no son obvias
     mirando sólo el resultado:

     - **`franja_cabecera()` / `franja_linea_inferior()` en `graficos/base.py`
       son la 3ª implementación del patrón, ahora compartida.** Las dos
       anteriores (Por día, Año Pasado) ya habían drifteado entre sí sin que
       nadie lo pidiera — el `<hr>` de una usaba `margin:-15px -18px 14px` y
       el de la otra `-6px -18px 12px`. Escribir una copia más a mano
       hubiera sido la tercera variante. Las dos primeras NO se retocaron
       (funcionan, están probadas, tocar dos features ya en producción para
       des-duplicar es un riesgo que no pagaba la pena en esta pasada) —
       queda anotado acá como candidato a una consolidación futura.

     - **Familia no necesitó el `min-height` de la regla #108, y la razón
       importa.** En Año Pasado el salto de layout salía de DOS llamadas a
       `data.cargar_rango()` (red, ~1-3s) entre pintar la cabecera
       provisional y la final. En Familia no hay ninguna llamada a red
       dentro del dashboard — `d` ya llega cargado del caller — así que la
       reescritura de la cabecera con el `gran` real ocurre a milisegundos
       de la provisional, antes de que se arme siquiera la figura. Verificado
       muestreando el alto de la tarjeta durante un clic: 0 frames sin
       título, 0 frames con tarjeta ausente. La lección para el próximo
       dashboard: el fix de #108 (placeholder + `min-height`) sólo hace
       falta si hay una espera real (red) entre el pintado provisional y el
       final: si todo el cálculo es en memoria, alcanza con reescribir la
       cabecera lo antes posible después de resolver el control del que
       depende.

     - **Los 3 pills de Familia (Agrupar por / Vista / Top) usaron
       `[data-selected="true"]` desde el primer commit**, no
       `[aria-pressed="true"]`. La lección de Año Pasado (single-select usa
       `role="radio"` + `data-selected`, no `aria-pressed`, que es de
       multi-select) se aplicó de entrada — verificado con clic real: el
       activo por defecto ("Mes") ya salía en `font-weight:600` y color de
       acento sin necesitar una segunda pasada de corrección.

     El 4º control (popover de series) NO lleva el tratamiento de tab/
     subrayado — es un control distinto (abre una lista, no alterna un
     valor único) — sólo se alinea en la misma fila con un separador a su
     izquierda, igual criterio que "Vista" en Año Pasado con el otro eje.

     El `title=` de la figura se sacó (vivía en `fig.update_layout`, ahora
     en la cabecera) aunque este gráfico no tenía el choque de la regla
     #103 (`showlegend=False`, sin leyenda que pelee el espacio) — se movió
     por CONSISTENCIA con el resto de los dashboards migrados, no porque
     hubiera un bug puntual acá.

     Verificado: la key de tarjeta (`ajuste_graf_card_izq_compras`) la
     comparten 6 vistas de Compras — probado que "Personalizado" (misma
     key) no hereda nada de esta franja, igual que se verificó con
     "Resumen" en Ventas (#106).

110. **`st.toggle` comparte `data-testid="stCheckbox"` con `st.checkbox` —
     no existe un testid "stToggle" propio (2026-08-13, panel "Detalle" de
     `graficos/ventas_comparativo.py`).** Verificado en el DOM real, no en
     la documentación de Streamlit: al cambiar el widget de la fila
     Venta/Pax/Ticket promedio de checkbox a toggle (pedido del usuario,
     con referencia visual el panel "Comparar con" de un gráfico de
     índices), el único cambio en el HTML es `<input role="switch">` y la
     estructura interna — track + thumb anidados (dos `<div>`) en vez de
     un cuadrado único con SVG de tilde. El selector `label > div:not(
     [data-testid])` (la caja visual) sigue apuntando al mismo lugar en
     ambos casos, así que las reglas CSS de `estilos/_80_cards.py` no
     necesitaron cambiar de testid, sólo de forma (pill 20×11 + thumb 7px
     en vez de cuadrado 12×12) y de posición del thumb (`justify-content`
     en el track en vez de pelear con el `transform` que Streamlit le pone
     a su propia clase con hash).

     Se mantuvo la regla ya documentada arriba (checkbox del panel
     Detalle): el switch sigue siendo la ÚNICA pieza por fila — no se
     agregó un botón "×" aparte para sacar una serie del todo, aunque la
     referencia visual sí lo tenía. La referencia (tipo comparador de
     índices) permite AGREGAR series sueltas y por eso tiene sentido poder
     sacarlas una a una; acá las tres filas son fijas (no hay forma de
     agregar una cuarta), así que un "×" sin "+" para volver a traerla de
     vuelta sería un callejón sin salida — se lo dejó fuera y se avisó al
     usuario en el chat en vez de agregarlo en silencio.

111. **Un `st.popover` no empuja layout NUNCA, esté flotando o no — por
     eso es la herramienta correcta para "que al expandirse no empuje el
     gráfico" (2026-08-14, panel "Detalle" de `graficos/ventas_comparativo.py`,
     de nuevo con referencia visual el panel "Comparar con" de un gráfico
     de índices).** El panel venía en un `st.expander` EN FLUJO: abrirlo
     empujaba hacia abajo el caption "Ventana: ...". Dos cambios
     independientes que es fácil confundir en uno solo:

     - **`st.expander` → `st.popover` arregla el empuje POR SÍ SOLO**,
       incluso sin ninguna línea de CSS: el contenido abierto de un
       popover (`[data-testid="stPopoverBody"]`) se renderiza en un
       PORTAL fuera del árbol del trigger — no es un hijo en flujo que
       empuje a sus hermanos. Mismo mecanismo ya usado por
       `ai_float_wrap` (`estilos/_85_asistente.py`) y `fecha_panel`
       (`estilos/_50_fecha.py`). Si el pedido hubiera sido SÓLO "que no
       empuje", este único cambio de widget alcanzaba.

     - **Que el TRIGGER quede flotando arriba-izquierda DEL PLOT (no
       "en algún lugar arriba de la tarjeta") es un problema aparte, de
       posicionamiento CSS** — el popover resuelve el contenido, no
       dónde vive el botón que lo abre. Se le dio una key propia a
       `_slot_graf` (antes `st.container()` a secas) para tener un
       ancla `position: relative` scopeada AL GRÁFICO, no a toda la
       tarjeta — así `top`/`left` no dependen de cuánto mida la franja
       de controles (grano/ventana/alinear/vista) que vive arriba.
       Verificado en vivo (demo local, `getBoundingClientRect`): abrir
       el popover no mueve ni un píxel el rect del `.js-plotly-plot`
       (mismos `x`/`y`/`h` antes y después de abrir).

     - **El tono "gris transparente" pedido salió de `--bg-primary`**
       (el "lienzo general" de la paleta, `_00_base.py`) con
       `color-mix(..., transparent)` + `backdrop-filter: blur()` — el
       mismo recurso que la franja "cristal esmerilado"
       (`_40_ajuste_franja.py`), pero con el gris neutro de
       `--bg-primary` en vez del tinte lavanda de `--accent-tint` (la
       referencia visual era gris, no violeta). El trigger CERRADO y el
       panel ABIERTO comparten el mismo tono para leerse como una sola
       pieza de vidrio.

     - **Trampa del scopeo**: como el panel es un portal, no se puede
       apuntar por ancestro (`.st-key-X .stPopoverBody`) — hay que
       envolver el CONTENIDO del popover en un `st.container(key=...)`
       propio y en CSS usar `[data-testid="stPopoverBody"]:has(.st-key-
       ese-container)`. Sin esa ancla, el selector `stPopoverBody` a
       secas pintaría TODOS los popovers de la página del mismo gris
       (rompería Proveedores, el asistente IA, los filtros de fecha).

     - **Móvil**: mismo criterio que `prov_pop_float`/`gran_float` en
       `graficos/compras/_css_proveedor.py` — por debajo de 640px el
       trigger deja de flotar (`position: static`, ancho 100%) porque un
       chip absoluto sobre la esquina de un plot angosto tapa barras. El
       popover sigue sin empujar nada al abrirse pase lo que pase con el
       trigger; sólo cambia dónde vive cerrado. Verificado con
       `resize_window` a 375px: la regla se activa sola, sin recargar
       (es CSS puro, no depende de `_es_movil()`/User-Agent).

     - **Corrección del mismo día, con captura del usuario**: el
       `st.container(..., width=400)` que agrupa las 3 filas se heredó
       tal cual del `st.expander` viejo, donde 400px era razonable (la
       tarjeta entera medía ~880px). Flotando, ese mismo ancho hacía un
       popover de ~448px — **casi la mitad** de la tarjeta, exactamente
       la palabra que usó el usuario, y medible: `bodyRect.w` pasó de
       448px a 320px al bajar el `width` interno a 260 (con un
       `max-width: 300px !important` en el propio `stPopoverBody` como
       tope, no sólo en el contenido). De paso, `border-radius: 999px`
       (cápsula completa, trigger Y panel) bajó a 8px/10px — la
       referencia es una tarjeta de esquinas suaves, no un chip/pill.
       **La transparencia sí funcionaba en local** (verificado,
       `color-mix()` se aplicaba) pero el reporte del usuario ("no tiene
       transparencia") se tomó en serio igual: si `color-mix()` no está
       soportado, la declaración es INVÁLIDA Y SE IGNORA ENTERA — sin
       una declaración de `background` previa y válida, cae al blanco
       opaco default de Streamlit, que es exactamente "no tiene
       transparencia". Se agregó un `rgba(246, 246, 248, 0.9x)` (mismo
       número que `--bg-primary`, a mano porque CSS no permite sacarle
       los canales R/G/B a una var() sin relative color syntax) COMO
       PRIMERA declaración de `background`, con el `color-mix()` después
       pisándola donde sí hay soporte — dos declaraciones de la misma
       propiedad en la misma regla no es un error, es progressive
       enhancement: el navegador se queda con la última que entienda.

     - **3ra vuelta (mismo día, 2da captura del usuario): `st.popover` se
       DESCARTÓ del todo.** Un popover, no importa cuánto CSS se le
       ponga, es estructuralmente DOS piezas: un botón (`stPopover`) y
       su contenido abierto, que Streamlit renderiza en un PORTAL
       (`stPopoverBody`) aparte, con su propio offset y su propia sombra
       — no hay forma de que se vean como una sola tarjeta sin costura,
       porque NO son un solo elemento en el DOM. Reportado con captura,
       comparando contra la referencia: "así se ve el tuyo, como un
       toggle, del cual sale otro toggle, usando más espacio". La
       referencia (la tarjeta "Comparar con") es a la inversa: título y
       filas viven en el MISMO rectángulo.

       La solución NO fue más CSS — fue dejar de usar `st.popover` y
       volver a un patrón manual, igual que el pestillo `latch_docs` de
       `graficos/compras/_css_proveedor.py` pero flotando: un
       `st.button` hace de título+chevron (con CSS que le saca todo
       rastro de "soy un botón" — sin borde, sin fondo, sin sombra
       propia, hereda el vidrio del contenedor) y `st.session_state`
       guarda si está abierto. Las filas se dibujan (o no) DENTRO del
       MISMO `st.container(key="ventas_comp_detalle_float")` que ya
       tenía `position:absolute` desde la vuelta anterior — ese
       contenedor no cambia de posición ni sale del flujo en NINGÚN
       estado, así que expandirlo (Python agrega las 3 filas adentro)
       sigue sin mover nada alrededor, exactamente la garantía que daba
       el portal del popover, pero sin la costura de dos piezas.
       Verificado en vivo, ciclo completo abrir→cerrar: el rect de
       `_slot_graf` midió IDÉNTICO (879×461.5625, y=201.8) antes de
       abrir, con el panel abierto (280×100 el contenedor flotante) y
       después de cerrar.

       **Trampa nueva, específica de este patrón**: el ícono (chevron)
       del botón se decide ANTES de saber si ESTE click lo tocó — un
       `st.button(icon=...)` ya se dibujó con el ícono viejo para cuando
       su propio `if st.button(...):` devuelve `True` en la misma
       pasada. Con `if st.button(...): flip()` el chevron queda UN CLIC
       ATRASADO (probado: abría el panel pero seguía mostrando la
       flecha de "cerrado"). El fix es `on_click=flip` en vez de leer el
       `return`: los callbacks de Streamlit corren ANTES de que el
       script vuelva a ejecutarse de arriba, así que para cuando el
       botón se arma de nuevo `session_state` ya tiene el valor nuevo.

     - **4ta vuelta: "no lo veo que tenga nada de transparencia" incluso
       CON el fallback rgba de la 2da vuelta.** No era un problema de
       soporte de `color-mix()`/`backdrop-filter` (verificado con
       `CSS.supports()` en local: los dos soportados) — era el MISMO bug
       que ya está documentado en `_40_ajuste_franja.py`: un tinte
       CASI-BLANCO a opacidad ALTA sobre una tarjeta que YA es casi
       blanca (`--bg-card`) es indistinguible del blanco opaco a simple
       vista, más allá de que la declaración se aplique perfecto. Ahí
       `--bg-primary` (#f6f6f8) al 92% es, en los hechos, blanco con
       nombre de variable gris. La franja resolvió esto cambiando de
       TINTE (blanco → `--accent-tint`, lavanda) — acá el pedido
       explícito era gris, no lavanda, así que en vez de cambiar de
       color se bajó la opacidad y se subió el "cuerpo" del gris:
       `--text-secondary` (#71717a, gris medio) a **16%** (no 92%), con
       blur más fuerte (14px, iguala a la franja) para que lo que se ve
       DETRÁS quede suavizado en vez de ruidoso. Lección: para que un
       "vidrio esmerilado" se LEA transparente, lo que importa no es
       sólo el alfa — es el CONTRASTE entre el tinte y la superficie
       sobre la que flota. Blanco-sobre-blanco no se nota ni al 92%;
       gris-medio-sobre-blanco se nota incluso al 16%.

     - **5ta vuelta: "esto se ve descuadrado" / "aún se ve espacio
       vacío" — dos bugs de padding DISTINTOS, encontrados con el propio
       inspector del proyecto (`?debug=1`, "Copiar para IA").** El dump
       trae "Layout del padre" y "Box del padre" con los valores
       computados reales, así que en vez de adivinar se pudo hacer la
       cuenta exacta:
       1. El contenedor flotante tenía `padding: 2px 0 5px` (2 arriba,
          5 abajo — asimétrico A PROPÓSITO, pensado para el estado
          ABIERTO). Sumado al padding parejo del botón (3px arriba y
          abajo), el total daba 6px arriba pero 9px abajo — 3px de más
          SÓLO abajo, y como el estado por defecto es CERRADO (una sola
          línea), esa asimetría era lo único que se veía siempre.
          Fix: `padding: 2px 0` (parejo) en el contenedor; el aire
          extra que necesitan las filas al abrir se movió al
          `padding-bottom` DEL PANEL, no del contenedor — así el estado
          cerrado (el más visto) queda centrado y el abierto sigue
          respirando.
       2. `stVerticalBlock` (el contenedor flotante ES uno, sin
          `border=True`) trae `gap: 16px` de fábrica — invisible con un
          solo hijo (cerrado), pero con dos (botón + panel, abierto)
          metía una franja vacía de 16px entre el título y la primera
          fila — exactamente lo que la captura con flechas mostraba.
          Fix: `gap: 0 !important` en el contenedor; el
          `padding-top: 4px` del panel es ahora TODA la separación
          título↔filas.
       Verificado en vivo antes/después con `getBoundingClientRect`:
       cerrado, arriba y abajo del texto quedaron en 3px/4.5px (bajó de
       ~6px/~9px); abierto, el hueco título→primera fila bajó de ~16px
       a 1.5px.

     - **6ta vuelta — el 1.5px residual SÍ importaba, y la explicación
       que quedó escrita en la vuelta anterior era EQUIVOCADA.** Ahí
       decía "sale de algún margen propio de `stElementContainer` sin
       identificar, por debajo del pixel perceptible". Falso en las dos
       mitades: era el **baseline gap** del botón (Streamlit lo rinde
       `inline-flex`, y todo hijo inline deja debajo el hueco de
       descendente de su línea), y sí se percibía — el usuario lo
       reportó como "la letra parece no estar centrada". El fix es una
       línea: `display: flex !important` en el botón (block-level, sin
       línea que genere el hueco). Medido después: `topGap == bottomGap
       == 2px` exacto, y el centro del `<p>` contra el centro del ícono
       dio diferencia **0**. Lección doble: (a) ante un desbalance
       vertical de 1-4px en un widget de Streamlit, sospechar del
       baseline gap ANTES que de un margen; (b) no cerrar un residuo
       como "imperceptible" sin que lo mire un humano — acá el humano
       lo vio de una.

       En la misma vuelta, el resto de "se ve regordete, como un
       gusano... el pestillo es casi imperceptible":
       · **Ancho FIJO (`width: 280px`, no `auto`)**: cerrado se encogía
         al texto (138px) y abierto saltaba a 280px. En la referencia la
         barra colapsada mide lo mismo que el panel abierto y sólo crece
         hacia abajo. Esto es lo que más cambió la lectura: una cápsula
         corta y gruesa pasó a barra larga y fina.
       · **`line-height: 1.35`** (heredaba 1.6): en una tarjeta cerrada
         de una sola línea, la caja de línea del texto ES casi todo el
         alto, así que el interlineado adelgaza más que el padding.
         Alto total 32.7px → 26.2px.
       · **`border-radius: 6px`** (era 10px): 10px sobre 26px de alto
         redondea casi a cápsula — de ahí "gusano".
       · **Chevron 17px + `--text-primary`** (era 13px + `--accent`):
         13px contra un texto de 12px no es jerarquía, y el violeta
         sobre vidrio gris translúcido pierde contraste. En la
         referencia el chevron se lee ANTES que el label, porque es la
         señal de "esto se abre".

     - **7ma vuelta: "las filas de detalle y el switch se ven no
       alineados entre sí" — y la primera hipótesis, aun siendo CIERTA,
       no era la causa.** Medido: el track quedaba 6.75px por encima del
       centro del texto, idéntico en las 3 filas (sistemático). Primera
       hipótesis: los textos heredaban `line-height: 1.6`, o sea una
       caja de 20.8px contra una fila de 13.5px. Era verdad — pero al
       bajarlo a `1` la caja pasó a 13px y **el delta siguió clavado en
       -6.75**. Ahí es donde midiendo la CADENA DE PADRES entera
       (`getBoundingClientRect` + `getComputedStyle` subiendo de nodo en
       nodo hasta la fila) aparecieron las dos causas reales, ninguna
       visible desde el elemento en sí:

       1. **`stMarkdownContainer` trae `margin-bottom: -16px`** —
          negativo, del tamaño de su propia línea. Con eso la COLUMNA
          ENTERA del texto colapsa a `height: 0` (verificado:
          `stColumn`, `stVerticalBlock`, `stElementContainer` y
          `stMarkdown` los cuatro en 0). Y una caja de alto 0 que
          `align-items:center` "centra" queda clavada en el centro de la
          fila, con el texto pintándose DESDE ahí hacia abajo — medio
          renglón más abajo que el switch.
       2. **El track del switch trae `margin-top: 2.5px`** (de
          Streamlit, para alinearlo con un label de texto al lado — que
          acá va `collapsed`), lo que lo deja pegado al fondo de su caja
          y 1.25px bajo el centro.

       Las dos se anulan con un `margin: 0`/`margin-bottom: 0` scopeado
       al panel. Resultado medido: **delta 0.00 exacto** en las 3 filas
       contra las 3 celdas de texto (nombre, valor y %Δ).

       Lección de método, que es la que vale para el próximo caso: ante
       un desalineado que se repite IGUAL en todas las filas, medir la
       cadena de padres completa antes de tocar nada. Las tres veces que
       este panel dio un problema de alineación vertical (baseline gap
       del botón en la 6ta, estas dos acá) la causa estaba en un ancestro
       o en un default de Streamlit, NUNCA en el elemento que se ve
       torcido — y las tres veces la primera hipótesis "razonable"
       miraba al elemento equivocado.

112. **`go.Heatmap` NO es seleccionable en Plotly: el box-select no emite
     nada.** Es la primera piedra con la que choca cualquier "arrastrá
     sobre el mapa para elegir un bloque". El heatmap dibuja, pero
     `plotly_selected` no dispara sobre sus celdas, así que
     `st.plotly_chart(on_select=...)` devuelve una selección vacía por
     mucho que se arrastre. La solución que usa `graficos/ventas_horario.py`
     es una **capa `go.Scatter` transparente encima**, un marcador por
     celda (`color="rgba(0,0,0,0)"`), que sí soporta box y lasso y devuelve
     en su `customdata` a qué panel/columna/hora corresponde cada punto.
     Como bonus, es la capa que lleva el hover: en el heatmap sólo habría
     `z`, acá se puede mostrar venta, pax, ticket y descuento juntos.

     Tres cosas más que hacen falta para que el gesto funcione, y que no
     son obvias hasta que fallan:

     · **`fig.update_layout(dragmode="select")`**, o el arrastre hace zoom.
     · **Selección VACÍA no significa "borrá las marcas".** Con
       `dragmode="select"` un clic al vacío devuelve una selección vacía;
       si las marcas se derivaran del evento en vez de acumularse en
       `session_state`, un clic torpe limpiaría el panel entero.
     · **La `key` del chart lleva la firma de las marcas** (misma familia
       que la regla #63 y que el `foco` del comparativo). Con key estática
       la misma selección se re-procesa en cada rerun. Corolario que NO se
       puede evitar: **re-arrastrar sobre una marca existente no la quita**,
       porque `on_select` sólo dispara cuando la selección CAMBIA — por eso
       quitar marcas es cosa de las pastillas de abajo del mapa. Un toggle
       "clic para poner, clic para sacar" se ve razonable en un mockup de
       JS y en Streamlit no existe.

113. **Las horas de un turno no se ordenan por número, y el eje NO puede
     ser numérico.** Medido en la app con datos reales de R2 (2026-08-14):
     el eje del mapa por hora traía `[0, 13, 14, …, 23]`. Las 00h son el
     final de la noche anterior, no el principio del día — un restaurante
     que cierra a la 1am las tiene siempre. Dos fallos distintos salían de
     ahí:

     1. **Orden.** Con el orden numérico crudo, las 00h quedaban ARRIBA de
        todo, antes de las 13h. `_orden_horas()` busca el hueco más grande
        del círculo de 24 horas y arranca justo después: con `{0, 13..23}`
        el hueco mayor es 01h→12h, así que el orden sale 13, 14, …, 23, 0
        — el turno tal como se vive.
     2. **Eje.** En un eje numérico ese salto se dibuja como doce filas
        vacías en el medio. El eje va `type="category"` con las horas que
        HAY. Consecuencia: las shapes de las marcas se dibujan con
        ÍNDICES de categoría (`±0.5` son los bordes de la fila), no con la
        hora, que en ese eje no significa nada.

     Y la trampa que se lleva el premio: **`h0 <= hora <= h1` es incorrecto
     en cuanto el turno cruza la medianoche.** "De 23h a 0h" son DOS horas;
     con la comparación numérica son las veinticuatro (0 ≤ h ≤ 23), o sea
     que una marca que tocara la medianoche se comía el día entero **en
     silencio**, sin error ni pista visual. Por eso el tramo entre dos
     horas se resuelve con `_horas_entre()` (posiciones en el orden de
     servicio + `isin`) y los extremos de una marca se toman por POSICIÓN,
     nunca con `min`/`max` de los números.

114. **Descuentos en `ventas.parquet`: la venta ya viene NETA, y sólo una
     de las dos columnas de descuento es el monto.** Verificado con DuckDB
     contra R2 el 2026-08-14 sobre los últimos 30 días:
     `PRECIO OFICIAL ITEM DDOCUMENTO * CANTIDAD ITEM DDOCUMENTO = VENTA +
     DESCUENTO` da EXACTO (383.540 = 342.153 + 41.387). O sea:

     · `VENTA ITEM DDOCUMENTO` ya tiene el descuento aplicado — **no se
       resta otra vez**, se suma aparte para reconstruir el precio de lista.
     · `DESCUENTO ITEM DDOCUMENTO` es el monto de la LÍNEA (ya
       multiplicado por la cantidad). Es el que se suma.
     · `PRECIO DESCUENTO ITEM DDOCUMENTO` es el descuento **unitario**:
       sumarlo directo da 37.512 en vez de 41.387. Nombre parecido,
       resultado equivocado, cero errores en pantalla.
     · `NOMBRE DESCUENTO` trae el tipo (13 distintos; nulo = sin
       descuento) y vive en la MISMA línea que el plato, así que
       relacionar un plato con la promo que se le aplicó **no necesita
       ningún join**: es un `groupby` más. Es lo que da el cuarto nivel del
       árbol del drill (Grupo › Sub Grupo › Plato › Descuento).

     Peso real, para dimensionar: 36% de las líneas descontadas, 10,8% del
     precio de lista, y `DSCT BCP 50% TP-100` sola explica 17.668 de
     41.387. También existe `MOTIVO CORTESIA`, sin explotar todavía.

     Detalle de pandas que costó un test: **`astype(str)` PRESERVA los
     nulos desde pandas 2.1** (no escribe "None"). Sin un `fillna` ANTES,
     la línea sin descuento se quedaba con NaN y en el árbol habría colgado
     de un nodo fantasma en vez de caer en «Sin descuento» — que no es
     relleno, es lo que se vendió a precio de lista.

115. **Un `return` temprano NO borra las tarjetas que ya estaban: hay que
     dibujarlas siempre y decidir por DENTRO.** Corolario práctico de la
     regla #70, medido el 2026-08-14 en Ventas › Por hora: al cambiar la
     granularidad, las marcas se limpian (una columna de "Semana" no es
     una de "Mes"), el `if not marcas: return` se saltaba las dos tarjetas
     del drill... y las tarjetas **seguían en pantalla con los números de
     la granularidad anterior**. Un `st.container(key=...)` que deja de
     renderizarse RETIENE sus hijos, y variar su key no ayuda: el huérfano
     se queda con la key vieja.

     La forma que sí funciona es abrir la tarjeta SIEMPRE y poner el `if`
     adentro. El precio es cero: una `chartcard_` vacía dentro de la card
     de Ventas no se ve (el CSS de `estilos/_80_cards.py` le quita borde y
     sombra), y sólo ocupa los ~32px de su padding.

116. **Un drill APILADO empuja el gráfico fuera de la pantalla; uno
     REPARTIDO no.** Ventas › Por hora, 2026-08-14. El detalle (tabla de
     medidas + árbol) vivía debajo del mapa en el flujo normal del
     documento, así que abrir una marca mandaba el mapa hacia arriba y
     fuera de la vista: **1.312px de scroll medidos** en el navegador,
     justo cuando el usuario está comparando el detalle CONTRA el
     gráfico. Pedido textual: "que no pierda enfoque en el gráfico
     principal y que haga el mínimo scroll".

     La solución es la de cualquier terminal bursátil: el gráfico y el
     panel se REPARTEN el alto de la pantalla y cada uno scrollea por
     dentro. Dos piezas:

     · `alturas.reparto(alto_figura, franja, extra)` — lo que le queda al
       panel del presupuesto de contenido. Es aritmética de una línea,
       pero vive en `alturas.py` porque es el dueño del alto (regla
       «nunca un alto suelto»).
     · La figura se COMPRIME cuando el panel está abierto: 22px por hora
       en reposo, 15 con el drill. `st.container(height=N)` scrollea por
       dentro sin CSS extra.

     Medido después, viewport 720: franja 61 + mapa 246 + pastillas 44 +
     panel 150 = 501, el contenido exacto del presupuesto; la tarjeta
     entera mide 544 contra un marco de 596, con **cero scroll de página
     y cero scroll de tarjeta**. El panel guarda 899px de detalle
     adentro.

     Lo que NO se puede: agrandar la tarjeta para que entre todo. La
     tarjeta ya mide exactamente una pantalla (`--alto-util`); hacerla
     más alta es devolverle el scroll a la página, que es el problema
     que se estaba resolviendo. Y tampoco se puede estirar el panel al
     alto real de la ventana: su alto sale de Python (pantalla objetivo
     1366x768) mientras el marco sale del CSS (`100dvh`), así que en
     monitores grandes sobran ~50px al pie. Es la misma tensión que
     documenta el docstring de `alturas.py`, no un olvido.

117. **Python emite alturas de CONTENIDO; las RESTAS las hace el CSS.**
     La regla que faltaba, y que explica los tres bugs de layout del
     2026-08-14/15. Formulada así porque el enunciado ingenuo —"Python y
     CSS no se ven"— no es accionable; el problema real es más preciso:

     > alguien restó contra una pantalla SUPUESTA.

     `alturas.py` arranca con `VIEWPORT_OBJETIVO = 657` y de ahí salen
     `PRESUPUESTO`, `CONTENIDO` y todo lo que tenga forma de "lo que
     queda después de descontar X". Una resta contra un viewport
     hipotético es correcta en exactamente un monitor. En el del usuario
     sobraban 350px; el panel del drill se quedaba en 150 con la ventana
     a 1000px de alto.

     LA LÍNEA no es Python vs CSS, es CONTENIDO vs CONTINENTE:

       · alto de una FIGURA → Python (filas × px). No hay alternativa:
         Plotly ignora su contenedor y sólo obedece a `fig.layout.height`
         (regla #102).
       · alto de un CONTENEDOR → CSS, porque `100dvh` es lo único que
         conoce la ventana de verdad.

     Para que el CSS pueda restar, Python PUBLICA lo que sabe:

         publicar_alto_css("vh-alto-arriba", 390)     # graficos/base.py
         max-height: calc(var(--alto-util) - var(--vh-alto-arriba));

     Medido con eso puesto: el panel pasa a 383px en una ventana de 1000
     y a 150 en una de 660, recalculado por el navegador, sin que Python
     sepa nada de la pantalla.

     TRES GUARDAS, porque documentar no alcanza:

       1. `test_graficos.py` falla si aparece un `st.container(height=…)`
          en `graficos/` — o sea un CONTENEDOR dimensionado desde Python.
          Es el gemelo del test que prohíbe `alto=430` sueltos. Escape
          hatch explícito: `# alto-fijo-justificado: <por qué>`.
       2. `auditar_layout.js` reporta HOLGURA además de desborde: "panel
          de 150px con 350 libres". El caso que no rompe nada y por eso
          no se ve.
       3. Los comentarios quedan fuera del grep del test: media docena
          citan la llamada prohibida para explicar la regla, y una guarda
          que salta con su propia documentación es una guarda que alguien
          termina desactivando.

     LO QUE QUEDA SUPUESTO, y es honesto que quede: acotar una FIGURA a
     la pantalla (`con_franja()`, el `rol=` de `por_filas`) sí necesita
     saber la pantalla en Python. Ese es el único argumento para leer el
     viewport real algún día — hoy sólo se lee el User-Agent
     (`_es_movil`), no las dimensiones. Todo lo demás ya no lo necesita.

118. **Los rails se pliegan cambiando UN ancho — y lo que cambia por
     `:has()` se DECLARA en la regla del `:has()`.**
     Los dos rails (navegación a la izquierda, vistas a la derecha) se
     comen ~240px que la tarjeta principal no puede usar. Desde el
     2026-08-15 tienen pestillo: `pestillos.py` guarda el estado, dibuja
     el botón y deja un marcador invisible en el DOM; el CSS
     (`estilos/_25_rails_pestillo.py`) lo detecta con
     `:root:has(style.rail-izq-plegado)` y redefine `--rail-izq-w`.

     Eso solo es posible porque antes se hizo el paso aburrido: los
     anchos, que vivían escritos a mano en SEIS sitios que se derivaban
     entre sí (el margen de la app, el `left` de la franja inferior, el
     `padding-right` del contenido, los `right` de la fecha, los chips y
     los atajos — o sea la regla #17, la parte más frágil de este CSS),
     pasaron a ser variables en `_00_base.py` con todo lo demás derivado
     por `calc()`. Plegar es literalmente una línea por rail. Hay guarda:
     `test_graficos.py` falla si `--rail-*-w` o `--rail-der-res` aparecen
     declaradas fuera de esos dos módulos, o si `--rail-der-res` deja de
     derivarse del ancho.

     DOS GESTOS, a propósito distintos (es el patrón de VS Code/Notion):

       · cursor sobre la lengüeta → VISTAZO. El rail es `position:fixed`,
         así que se despliega SUPERPUESTO: `:hover` puro, sin rerun, y la
         tarjeta no se mueve ni un píxel (medido: x=104 y w=1083 antes y
         durante el vistazo).
       · clic en el pestillo → FIJA. Rerun, y la tarjeta se ensancha.
         Medido a 1280px: 957 → 1083 (+126, +13%), el Plotly igual, sin
         scroll de página.

     Los ítems del rail se ESCONDEN con `display:none`, no se dejan de
     renderizar: un widget que deja de dibujarse pierde su estado y al
     desplegar el rail volvería a la primera vista.

     LA TRAMPA, que costó una hora: `:root:has(…) .st-key-nav_rail`
     aplicaba `min-height`, `overflow` y `border-radius` pero NO el
     `width` que venía heredado por variable — el rail se quedaba en 90px
     mientras el margen de la app, la franja inferior y hasta los botones
     de dentro del propio rail (`calc(var(--rail-izq-w) - 16px)`, que
     medía 8px) sí se movían. Heredar una variable sirve para lo que está
     LEJOS; para el elemento que la propia regla toca, declararlo directo.
     Corolario del móvil: si lo declaras directo, también hay que
     deshacerlo directo en el `@media` (si no, el rail plegado en
     escritorio llega al teléfono convertido en una lengüeta de 24px
     encima de la barra inferior).

119. **Nada de `transition` sobre algo que un rerun pueda pillar a media
     animación.**
     Gemela de la anterior y descubierta en el mismo rato. El ancho del
     rail se quedaba clavado en el valor viejo PARA SIEMPRE — no
     "tardaba", no llegaba nunca, y era inmune a cualquier cascada
     posterior: ni un `width:24px !important` inline lo movía. Solo se
     despertaba tocando la variable a mano en la consola. La transición
     arranca, el rerun de Streamlit reconstruye el DOM a mitad y el valor
     queda congelado en el primer fotograma. Después pasó exactamente lo
     mismo con la sombra del vistazo, que también estaba transicionada.

     Que el síntoma no se parezca a la causa es lo que la hace cara: se
     descarta la cascada, la especificidad, la variable y el `:has()`
     antes de mirar la única propiedad que tenía `transition`.

     Regla: en esta app, animar propiedades que disparan layout (`width`,
     `height`, `top`…) sobre elementos que sobreviven a un rerun es
     apostar. Si hace falta animación, `transform` u `opacity`, que no
     dependen del layout y no pueden quedarse a medias. Hoy los rails
     abren y cierran de golpe — que además es lo que hacen los de VS Code
     y Notion.

120. **Un dashboard puede "aparecer" en la franja superior sin que app.py
     sepa nada de él — mismo truco que ya usaban los chips, ahora aplicado
     a un título.**
     Ventas › Comparativo (`graficos/ventas_comparativo.py`) pedía mover
     su título de dentro de la tarjeta a la franja superior, y correr la
     fecha/chips a la derecha para hacerle sitio — solo en esa vista, no
     en los otros 7 reportes ni en el resto de Ventas.

     `fecha_ajuste_pill` (app.py) y `chips_ajuste_tabla` (cada dashboard)
     ya probaban que un contenedor puede vivir en CUALQUIER parte del DOM
     y aun así "aparecer" en la franja: alcanza con `position:fixed` y un
     `top`/`left` que apunte ahí. El título usa el mismo truco —
     `ventas_comp_titulo_franja`, creado DENTRO del fragment de
     `_ventas_comparativo` (ni siquiera necesita vivir fuera de un
     `@st.fragment`) — así que no hizo falta tocar la firma del
     dispatcher (`graficos/__init__.py::renderizar_graficos_reporte`) ni
     `app.py`. `test_graficos.py` verifica esa firma; agregar un
     parámetro nuevo ahí habría obligado a tocar los 8 dashboards para
     que el test de arity siguiera pasando.

     Para que el corrimiento de fecha/chips sea EXCLUSIVO de esa vista
     (y no un shift global que le robe espacio a los otros 7 reportes),
     el CSS se scopea por PRESENCIA, no por reporte: `:has()` sobre el
     prefijo de key que arma `_card()` (`chartcard_ventas_comparativo_`),
     no sobre `st-key-app_reporte_ventas` — ese marcador es del REPORTE
     entero, y el título solo existe en una de sus vistas. Ver
     estilos/_50_fecha.py, bloque "TÍTULO DE VENTAS › COMPARATIVO".

     Medido en vivo (regla de oro del proyecto: nunca a ojo) el ancho que
     hacía falta reservarle al título chocaba con los 4 chips de Ventas
     (Grupo/Sub Grupo/Canal/Servicio, ~410px de contenido real): a
     380px de reserva, los chips se comprimían/superponían ya a 1280px.
     Con 260px (truncando los títulos largos con ellipsis + `title=`
     como tooltip) el corrimiento entero deja de caber cómodo por debajo
     de ~1220px. En vez de aceptar chips ilegibles ahí, el bloque entero
     va detrás de `@media (min-width: 1220px)` — no los 901px que usa el
     resto de la franja — y por debajo el título se oculta y la fecha/
     chips vuelven a su posición de siempre (misma idea que
     `fecha_corte_nav`, oculto hasta 1400px por el mismo motivo: sin
     dato es mejor que dato ilegible).

     Como el título dejó de vivir DENTRO de la tarjeta, el `min-height`
     de reserva de esa tarjeta (estilos/_80_cards.py, evita el colapso
     mientras cargan los dos rangos de R2) perdió el término "42 de
     cabecera" que traía: 466px → 424px. Un número que cita piezas
     reales (padding + franja + figura) hay que recalcularlo cuando una
     de esas piezas se muda, o queda reservando alto para algo que ya no
     está.

     TRAMPA aparte, encontrada al pedido de "esto desperdicia espacio,
     subilo": un `position:fixed` colapsa a 0px de alto — pero SOLO el
     elemento que lo tiene, no su wrapper. `ventas_comp_titulo_franja` se
     dibuja como HERMANO de la tarjeta (mismo bloque vertical), y aunque
     el título en sí no ocupa alto, el wrapper que Streamlit le pone
     alrededor sigue siendo un flex item más del bloque que los contiene
     — y el `gap:16px` de ese flex se aplica IGUAL entre "un item de 0px"
     y el siguiente. La tarjeta apareció 16px más abajo de lo que estaba
     antes de que el título tuviera un hermano invisible, aun con
     `position:fixed` puesto correctamente. Medido (`getBoundingClientRect`
     antes/después) y cancelado con `margin-top:-16px` en la tarjeta. Si
     un futuro placeholder-fantasma (position:fixed, escapa a la franja)
     se agrega como HERMANO de algo en vez de vivir DENTRO de ello, contar
     con este mismo 16px de sobra.

121. **El patrón "título fantasma en la franja" se generalizó (helper
     `titulo_en_franja` en graficos/base.py) y se portó a Compras › Familia
     — con dos diferencias que no eran obvias de la 1ra vez (Ventas
     Comparativo, regla #120).**

     Compras › Familia no tiene una tarjeta INTERNA propia (`_card()`) para
     la sección de arriba — a diferencia de Ventas, donde el título vivía
     hermano de `chartcard_ventas_comparativo_*` DENTRO de un wrapper
     exterior compartido, acá el título es hermano DIRECTO de la fila de
     controles, ambos dentro del wrapper único `ajuste_graf_card_izq_
     compras` (que además reusan TODAS las demás vistas de Compras, así
     que no se le puede colgar un margin-top propio sin afectarlas). Se
     resolvió envolviendo SOLO la fila de controles en un contenedor nuevo
     y liviano (`compras_fam_controles_row`, sin `border`, solo ancla de
     CSS) y aplicándole el mismo `margin-top:-16px` — el resto de la
     función (breadcrumb, gráfico, paneles `fam_comp`/`fam_top`) no
     necesitó tocarse: el gap nuevo es SOLO el primero (entre el título y
     lo que antes era el primer hijo), los demás gaps preexistentes entre
     hermanos siguientes no cambiaron.

     Scope del corrimiento de fecha/chips: Ventas se scopeaba por el key de
     la tarjeta interna (`chartcard_ventas_comparativo_*`, único de esa
     vista). Compras › Familia no tiene ese ancla — TODAS las vistas de
     Compras comparten el mismo key de wrapper. Se scopeó por la
     PRESENCIA DEL PROPIO TÍTULO (`:has(.st-key-compras_fam_titulo_
     franja)`) en cambio: más simple, y funciona igual porque el título
     solo lo dibuja esa vista.

     Presupuesto horizontal: Compras tiene solo 2 chips (Familia/
     Subfamilia) contra los 4 de Ventas, pero cada uno lleva
     `min-width:230px` FORZADO (el addendum de Compras/Inventario/Salidas
     en estilos/_50_fecha.py — reportes con EXACTAMENTE 2 chips). El
     contenido real (230+230+8=468px) termina siendo MÁS ancho que el de
     Ventas (~410px sin forzar), así que el umbral por debajo del cual el
     título se oculta tuvo que subir: 1220px (Ventas) no alcanzaba acá
     (medido: los 2 chips se superponían), 1310px sí. Ni el ancho del
     título (260px) ni los tres números acoplados (175/451/667) cambiaron
     — son los MISMOS que en Ventas, coincidencia de haber usado el mismo
     ancho de reserva, no algo que haya que mantener igual a propósito.

122. **El texto del hover de Plotly casi no se veía — no era un problema de
     `estilos/`, sino de `layout.font` no llegando al tooltip.**

     Reportado sobre el gráfico de Evolución de Compras › Proveedor (con
     captura y flechas sobre los puntos): el hover se disparaba (la
     spikeline vertical se veía) pero el texto era casi ilegible. Medido en
     el DOM (`hoverlayer` > `text.legendtext`): `fill: rgb(128,132,149)`
     sobre fondo blanco — 3.7:1 de contraste, no pasa AA (mínimo 4.5:1) —
     pese a que `_compras_layout` ya fija `font.color=TEXTO_PRINCIPAL` para
     TODO el resto del gráfico. `layout.font` no alcanza al hover: Plotly
     le pone su propio gris por defecto, y ese default gana siempre que no
     se pise explícito con `layout.hoverlabel`.

     Se fijó en `_compras_layout` (graficos/base.py), no en cada dashboard:
     al ser compartida por compras, ventas, inventario, salidas,
     requerimientos y constructor, el mismo contraste bajo estaba latente
     en los 18 ficheros de `graficos/` que usan `hovertemplate`, aunque
     solo se reportó en uno. `hoverlabel=dict(bgcolor=BLANCO,
     bordercolor=GRIS_BORDE, font=dict(color=TEXTO_PRINCIPAL, ...))`
     verificado con el mismo truco de simulación de hover que ya documenta
     este archivo (disparar `mousemove`/`mouseover` sobre `.nsewdrag`, leer
     `hoverlayer` del DOM) en dos gráficos distintos del mismo drill
     (ranking horizontal y evolución) para confirmar que un solo cambio
     centralizado alcanzó a ambos.

123. **Para ensanchar un contenedor de Streamlit con `margin` negativo +
     `width: calc(100% + Npx)`, hay que pisar TAMBIÉN `max-width` — si no,
     el ancho nuevo se clampea en silencio.**

     Pedido: ensanchar `compras_prov_drill_wrap` (el contenedor del drill
     de Proveedor) para que entraran 3 columnas en vez de 2. La receta
     obvia — `margin-left:-60px; width:calc(100% + 104px)` con
     `!important` — no hacía NADA: medido en vivo
     (`getBoundingClientRect`), el ancho volvía siempre a 1107px pese al
     `!important`. La causa no era especificidad ni orden de cascada (los
     sospechosos habituales): Streamlit le pone a TODO `stVerticalBlock`
     su propio CSS emotion con `max-width: 100%` (sin `!important`, pero
     `max-width` no compite CON `width` — son propiedades distintas que el
     motor de layout aplica en secuencia, así que un `width` más grande
     simplemente se vuelve a recortar después). La regla ganaba el pulso
     de `width` y perdía la partida igual, porque nunca competía por
     `max-width`.

     Se encontró iterando `document.styleSheets` y filtrando las reglas
     cuyo selector matcheaba el nodo (`el.matches(rule.selectorText)`) —
     más rápido que adivinar por especificidad a ojo. Fix: repetir el
     mismo `calc(100% + Npx)` también en `max-width`. Aplica a cualquier
     intento futuro de ensanchar un `st.container()`/bloque vertical más
     allá de su 100% con CSS puro.

124. **`compras_prov_drill_wrap` (drill de Proveedor) pasó de 2 a 3
     columnas (ranking / tabla resumen / evolución) — el ensanche de la
     regla #123 solo alcanza en DESKTOP, y las columnas necesitan su
     propio piso de ancho para no apretarse antes de apilarse.**

     Dos guardas nuevas en este cambio, ambas con número medido, no a ojo:

     - El ensanche (`margin-left:-60px` + `width:calc(100% + 104px)`,
       estilos/_20_compras_rail.py) va detrás de `@media (min-width:
       901px)`. Sin el guard rompe en móvil: `nav_rail` (navegacion.py)
       deja de ser el rail izquierdo de 90px y pasa a barra INFERIOR
       recién por debajo de **768px** — un breakpoint DISTINTO al que ya
       usa `compras_tabs_row` (rail derecho, 900px, en este mismo
       fichero). Entre 769 y 900px los dos rails siguen en su forma de
       escritorio, así que 901 es el corte correcto para no dejar una
       franja intermedia sin decidir. Por debajo de 901, sin rail del que
       "recuperar" espacio, tirar la tarjeta 60px a la izquierda la saca
       del viewport (verificado: sin el guard, a 850px de ancho la
       tarjeta arrancaba en x=46 con el rail izquierdo terminando en
       x=90 — 44px de la tarjeta tapados debajo del rail).

     - Las 3 columnas (`st.columns([1.2, 1, 1])`, proveedor.py) usan
       `flex-wrap:wrap`, default de Streamlit en `stHorizontalBlock` —
       pero SOLO apilan cuando no entran a su ancho NATURAL, que puede
       ser bastante angosto antes de eso. Medido en vivo: sin piso propio,
       a 800-850px de viewport las 3 quedaban lado a lado en ~186-200px
       cada una, y la tabla (grid con 168px fijos entre columnas
       numéricas) le dejaba ~20-30px al nombre del proveedor — ilegible.
       Fix: `min-width:300px` por columna
       (`.st-key-cp_chart_wrap [data-testid="stColumn"]`,
       graficos/compras/_css_proveedor.py) — por debajo de ese piso,
       `flex-wrap` las apila a ancho completo en vez de apretarlas.

     Con las dos guardas juntas, el resultado medido: 3 en fila recién de
     ~1160px de viewport en adelante (donde el ensanche ya dio ancho de
     sobra), apiladas por debajo — incluida la franja 641-900px que con
     el layout viejo de 2 columnas ya venía algo justa y ahora queda
     prolija. La tabla resumen (antes apilada DEBAJO del ranking, dentro
     de la misma columna) truncaba nombres a 34 caracteres
     (`_compras_truncar`); al pasar a columna propia y angosta bajó a 20.

125. **El scroll interno de un `st.plotly_chart` (8 filas fijas + scroll,
     drill de Proveedor) necesita DOS contenedores, no uno: si el nodo que
     Streamlit usa para su propio ResizeObserver del plot queda con el
     alto acotado, Plotly se ENCOGE a ese alto en vez de crecer y dejar
     que el de AFUERA recorte con scroll.**

     Pedido: que el ranking (y la tabla resumen, al lado) del drill de
     Proveedor mostraran 8 filas fijas con scroll para el resto, en vez de
     crecer sin techo con la cantidad de proveedores. La receta obvia —
     `alto=alturas.por_filas(n, ..., enmarcada=True)` en Python (para que
     la FIGURA dibuje las N filas sin comprimirlas, hasta el techo de 900
     de `_TOPE_ENMARCADA`) + `max-height:248px; overflow-y:auto` en el
     contenedor de `_css_proveedor.py` (`cp_chart_scroll`, que envuelve
     `st.plotly_chart`) — no hizo lo pedido: medido en vivo
     (`gd.layout.height`, `gd._fullLayout.height` del div de Plotly), la
     figura llegaba al navegador con `height:248`, no los 456px que pedía
     Python para 16 proveedores (26px × 16 + 40 de extra). El ranking
     terminaba comprimiendo las 16 filas en el frame en vez de dibujarlas
     todas y scrollear — el resultado opuesto al pedido, y silencioso: sin
     leer el `layout` de Plotly en el DOM, se ve simplemente "el chart no
     creció".

     La causa: el `max-height`/`overflow-y` estaba puesto TANTO en
     `.st-key-cp_chart_scroll` (el contenedor propio de este proyecto)
     COMO en su hijo directo `[data-testid="stElementContainer"]` (el nodo
     que Streamlit envuelve alrededor del componente Plotly) — ese hijo es
     el que Streamlit mide para decidir el tamaño del plot. Con el hijo
     acotado a 248, Streamlit redibujaba la figura a 248, pisando
     `fig.layout.height` exactamente como si Python nunca hubiera pedido
     456.

     Fix: sacar `max-height`/`overflow-y` del hijo (`stElementContainer`,
     que se deja SIN acotar) y dejarlo solo en el padre
     (`cp_chart_scroll`). Sin el hijo acotado, Streamlit deja crecer la
     figura a su alto real; el padre es quien la recorta a 248px visibles
     con scroll — que es lo que se pidió. Mismo síntoma de fondo que la
     regla #123 (algo vuelve solo a un tamaño más chico pese al ajuste
     explícito), causa distinta: ahí era CSS puro (`max-width` compitiendo
     con `width`); acá es el propio JS de Streamlit reaccionando al
     tamaño de SU contenedor. La tabla resumen de al lado (HTML plano, sin
     Plotly de por medio) no tuvo este problema — su `.cp-rk-tabla-body`
     con `max-height` funcionó a la primera; solo hizo falta ajustar el
     número (248 → 274px) porque su fila mide más que los 26px/barra del
     gráfico, así que "8 de lo suyo" no es el mismo px que "8 filas" del
     ranking — cada frame mide 8 en SU propia unidad, no un mismo número
     compartido.

     Addendum 2026-08-17 (mismo día): el ranking en barras que esta regla
     describe se UNIÓ con la tabla resumen (regla #126) y `st-key-cp_
     chart_scroll`/`.cp-rk-tabla-body` ya no existen en el código. La
     LECCIÓN sigue valiendo para cualquier `st.plotly_chart` futuro al que
     se le quiera aplicar el mismo patrón "8 filas + scroll" — por eso
     queda, aunque el selector puntual ya no se pueda grepear.

126. **El ranking (barras Plotly) y la tabla resumen del drill de
     Proveedor —dos vistas de los mismos números, una al lado de la
     otra— se UNEN en una sola tabla (`st.dataframe` con `ProgressColumn`
     haciendo de barra). Al pasar de `st.plotly_chart` a `st.dataframe`
     para la interacción de foco, dos cosas se rompen si se copia el
     patrón viejo tal cual.**

     Pedido: "la información del ranking y de la tabla se parece, únelas,
     conservando la barra y el clic". El resultado son 2 columnas en vez
     de 3 (tabla-ranking unida | evolución), con la MISMA lógica de "leer
     la selección ANTES de dibujar" que ya usaba el ranking en barras
     (regla evitar doble rerun / parpadeo) — pero aplicada a
     `st.session_state[key]["selection"]["rows"]` de un `st.dataframe` en
     vez de `_first_point()` de un `st.plotly_chart`. Dos gotchas nuevos,
     los dos verificados en vivo (no a ojo):

     1. **Reclickear la MISMA fila ya seleccionada NO dispara un nuevo
        rerun.** El ranking en barras SÍ tenía un toggle "clic en la misma
        barra → desenfoca" (comparando `_clicked == prov_focus` a mano).
        Con `st.dataframe`, el valor del widget no cambia entre el primer
        y el segundo clic sobre la misma fila, así que Streamlit no manda
        el evento — el `if _rows_sel:` nunca se re-ejecuta y el foco queda
        pegado. Confirmado con clics sintéticos reales (`PointerEvent`
        sobre el canvas, ver punto 3): clic en fila 2 enfoca; clic de
        nuevo en fila 2, sin cambios. Fix: un botón explícito "✕ Quitar
        foco" (mismo patrón que "↩ Todas" en el breadcrumb de Compras ›
        Familia, familia.py) en vez de depender del reclic.

     2. **El orden de `_rk_nombres` cambió de ASCENDENTE a DESCENDENTE** al
        borrar el paso `_ord = sorted(...)` que existía SOLO porque Plotly
        dibuja barras horizontales de abajo hacia arriba (así que había
        que invertir la lista para que el mayor quedara arriba). Una
        tabla no tiene esa restricción — orden natural (mayor primero,
        que ya traía `orden_provs`). Pero el default de "sin foco, mostrar
        el proveedor de mayor valor" en el gráfico de evolución leía
        `_reales[-1]` (el ÚLTIMO de la lista ascendente = el mayor). Con
        la lista ahora descendente, `_reales[-1]` pasó a ser el MENOR —
        bug real, encontrado al probar (la evolución por defecto mostraba
        al proveedor más chico, MIFARMA S.A.C. en vez de VIBEJ COLIBRI
        SAC). Fix: `_reales[0]`. Cualquier código que asuma el orden de
        `_rk_nombres` hay que revisarlo cuando ese orden cambie — no hay
        garantía de tipo que lo avise.

     3. **Verificar un `st.dataframe` con clics automatizados en este
        entorno necesita DOS rodeos, no uno.** (a) El grid
        (`stDataFrameGlideDataEditor`, glide-data-grid) NO pinta su
        `<canvas>` hasta que el contenedor entra en viewport — medido:
        recién montado, `.stDataFrameGlideDataEditor` es un
        `<div></div>` vacío y no hay canvas de tamaño real en la página;
        tras `scrollIntoView()` + esperar, aparecen 2 canvases con el
        tamaño real (uno para el header, uno para las filas). Sin el
        scroll, cualquier intento de clic (real o sintético) cae sobre
        nada. (b) El grid no reacciona a un `MouseEvent` sintético con
        `type:'pointerdown'` — necesita un `PointerEvent` DE VERDAD
        (`pointerId`, `pointerType:'mouse'`, `isPrimary:true`
        explícitos), disparado como `pointermove` → `pointerdown` →
        `pointerup` sobre el `<canvas>` con `clientX/clientY` calculados
        contra su `getBoundingClientRect()`. Con `?debug=1` activo, el
        inspector propio del proyecto también intercepta el clic (queda
        clicable el tooltip, no la fila) — hay que probar SIN `?debug=1`.

127. **`hovermode="x unified"` de Plotly renderiza su caja de hover con la
     clase SVG `.legend` — cualquier CSS que apunte a `.legend` pensando
     "la leyenda del gráfico" también atrapa el hover unificado de
     CUALQUIER otro gráfico que comparta el mismo contenedor scopeado.**

     Reportado: "la etiqueta [del hover] casi no se ve, como si fuese
     transparente" sobre el gráfico de Evolución de Compras › Proveedor.
     La regla venía de ANTES del merge de la regla #126: cuando el
     ranking todavía era un `go.Bar` con leyenda propia, `_css_proveedor.py`
     tenía `.st-key-compras_prov_card_chart .js-plotly-plot .legend {
     opacity: 0.1 !important; } ...:hover { opacity: 1 !important; }` —
     la leyenda del ranking se hacía casi invisible en reposo y opaca solo
     al pasar el cursor DIRECTO sobre ella. El ranking se unió a la tabla
     (regla #126) y su leyenda desapareció con él, pero la regla CSS
     quedó — y sigue matcheando, porque el selector es por CONTENEDOR
     (`.st-key-compras_prov_card_chart`), no por gráfico: la evolución
     vive en el mismo contenedor, y su hover unificado, al llevar también
     `class="legend"` (verificado en el DOM: `hoverlayer > g.legend`),
     heredaba el `opacity: 0.1` — quedaba al 10%, "casi transparente",
     todo el tiempo salvo que el cursor cayera justo sobre la cajita del
     hover (que sigue al dato, no al cursor, así que casi nunca coincide).

     Verificado en vivo: simular hover (`mouseover`/`mousemove` sobre
     `.nsewdrag`, técnica ya documentada en este archivo) y leer
     `getComputedStyle` del grupo `.legend` DENTRO de `.hoverlayer` — no
     de sus hijos, que reportan `opacity:1` cada uno aunque el padre esté
     al 10% (la opacidad de un `<g>` en SVG se compone visualmente pero no
     cambia el `computedStyle` propio de los descendientes). Antes del
     fix: `0.1`. Después de borrar la regla (ya no tenía target propio):
     `1`.

     Lección: un CSS "para el gráfico X" que en realidad apunta a una
     clase GENÉRICA de Plotly (`.legend`, `.hoverlayer`, `.modebar`...)
     dentro de un contenedor que hospeda VARIOS gráficos, sigue vivo para
     todos ellos aunque el gráfico que lo motivó desaparezca. Al borrar un
     gráfico, grepear su contenedor por reglas CSS de alcance amplio antes
     de darlo por limpio.

128. **Compras › Producto (2026-08-17) fusiona 3 vistas en 1, y deja 3
     lecciones reusables.** El pedido original era fusionar "Precio top 10"
     + "Precio por compra" (dos líneas de precio, una promediada por mes y
     otra con el precio real de cada compra) en una sola vista "Producto";
     en la conversación creció a fusionar también "Cantidad por producto"
     (`cantidad.py`, borrado) — las tres eran, en el fondo, la misma
     pregunta ("¿cómo le fue a ESTE producto?") respondida con tres
     gráficos y tres pantallas distintas.

     **1) Selector de texto plano = `st.pills` + CSS propio, no una clase
     compartida.** El pedido fue explícito: nada de cápsula/pill, solo
     texto con el activo en violeta y negrita — para no ocupar sitio en la
     columna angosta del panel de detalle. `st.pills` en esta versión de
     Streamlit renderiza `div[data-testid="stButtonGroup"] > button
     [role="radio"]`, con el atributo `data-selected` SOLO en el botón
     activo (documentado en `estilos/__init__.py` § Sobre st.pills) — eso
     alcanza para pelarlo a texto plano con `background/border: none` +
     `color` distinto en `[data-selected]`. El título de la tabla-ranking
     (`.cp-rank-tit` en `_css_proveedor.py`) casi se reusó tal cual, pero
     esa clase SOLO se inyecta cuando se renderiza el drill de Proveedor
     (`st.markdown(CSS_PROVEEDOR,...)` vive DENTRO de
     `_compras_proveedor_drill`): reusar el nombre de clase sin
     redeclarar su CSS habría dejado el título de Producto sin estilo.
     Se declaró de nuevo con nombre propio (`.cp-prod-rank-tit`) en
     `producto.py`. Regla general: una clase CSS que otro módulo inyecta
     condicionalmente NO es reusable sin traerse también su inyección.

     **2) Línea de período + puntos reales en el MISMO gráfico: eje de
     FECHA real, no de categorías.** El primer mockup (HTML/SVG, para
     mostrarlo en el chat) tuvo que inventarse a mano la conversión entre
     "índice de bucket" (mes/semana/año) y "posición continua" para que
     los puntos de compra real no aparecieran corridos del bucket que les
     tocaba — un bug real que se coló en ese mockup antes de notarse. En
     Plotly esto no hace falta: agregar el promedio por
     bucket indexado por la FECHA de inicio del bucket (lunes de la
     semana, día 1 del mes, 1 de enero del año) y graficar los puntos
     reales en su fecha exacta los deja en el MISMO eje de fecha sin
     ninguna conversión — Plotly resuelve la posición continua solo.
     Ver `_prod_serie_periodo` en `producto.py`.

     **3) Categoría vacía (Familia) se agrupa como "Sin familia", nunca
     se descarta.** Si se descartaran, el total del ranking por familia
     dejaría de sumar lo mismo que el ranking de productos de arriba —
     mismo criterio que ya usa `_vol_candidatos` en `volatilidad.py` con
     `min_gasto`/`min_cobertura` (filtrar es una decisión explícita, no
     un efecto secundario de agrupar).

     Por lo demás, `producto.py` copia el patrón de ranking de
     `proveedor.py` casi literal: `st.dataframe` con `column_config.
     ProgressColumn` para la barra de Valor, clic-para-enfocar procesado
     ANTES de construir la tabla (mismo dedup con `_last_click` en
     session_state, mismo problema de que reclickear la fila enfocada no
     dispara `on_select` — de ahí el botón "✕ Quitar foco") y el marco
     fijo de 8 filas (`alturas.por_filas(8, px_fila=35, extra=45,
     minimo=0)`) con scroll interno para el resto.

129. **Se eliminó el drill "Familia" (Familia→Subfamilia→productos,
     `compras/familia.py`) por redundante — y borrarlo costó grepear
     TRES ficheros aparte del suyo.** Con la vista Producto ya arriba
     (regla #128), Compras tenía dos formas de ver "compras por
     familia": el drill completo (gráfico en el tiempo + paneles de
     composición/Top N) y la tarjeta "Compras por familia" nueva
     (ranking + mini ranking al clic). El usuario pidió borrar el
     primero, "el que dice Familia, el primero" del rail — confirmado
     explícitamente antes de tocar nada, porque había ambigüedad real
     entre esas dos cosas.

     El código Python fue lo fácil (import, entrada de
     `_COMPRAS_RAIL_CATEGORIAS`, `opciones`, la rama `if graf ==
     "Familia":` y el archivo). El CSS fue la parte que casi se escapa:
     `compras/familia.py` no inyectaba su propio CSS (a diferencia de
     Proveedor con `_css_proveedor.py`) — sus estilos vivían reglas
     sueltas en DOS módulos de `estilos/` que nada en `producto.py` ni
     en `__init__.py` delata:
       - `estilos/_80_cards.py` — el bloque "FRANJA DE CONTROLES DE
         COMPRAS › FAMILIA" completo (tabs de texto con subrayado para
         Agrupar por/Vista/Top + separadores + el popover de series),
         ~95 líneas.
       - `estilos/_50_fecha.py` — el bloque "TÍTULO DE COMPRAS › FAMILIA
         EN LA FRANJA" (el título que vive fuera de la tarjeta,
         anclado por `position:fixed` vía `:has()`), ~50 líneas.
     Ninguno de los dos se detecta compilando ni corriendo
     `test_graficos.py` — son reglas CSS huérfanas, no código Python
     roto: siguen siendo sintácticamente válidas, solo que ya no
     matchean nada porque el key que las activaba (`compras_fam_*`) no
     lo escribe más ningún `st.container`. La única forma de encontrarlas
     es grepear el prefijo de key (`compras_fam_`) en TODO `estilos/`,
     no asumir que vive en el mismo archivo que el código que se borró
     — mismo método que ya pedía la regla #127 para el caso de una
     clase CSS genérica, acá aplicado a un prefijo de key completo.

     De paso, tres comentarios en otros archivos (`proveedor.py`,
     `inventario.py`, y la propia línea del mapa de ficheros de arriba)
     citaban a `familia.py` como referencia de patrón ("mismo patrón que
     el breadcrumb de Compras › Familia") — se reescribieron para
     apuntar a un ejemplo que sigue existiendo. Un comentario que cita a
     un archivo por nombre es una referencia que puede quedar colgando;
     grepear el nombre del archivo borrado en todo el repo (no solo en
     `graficos/` y `estilos/`) antes de dar el borrado por completo.

130. **Ranking de Volatilidad (`compras/volatilidad.py` +
     `tablas/compras_volatilidad.py`): cabeceras con fecha real,
     buscador, tooltip de precio por celda y clic-en-fila** — a pedido,
     sobre la tabla que ya existía (regla #74). Pasó por DOS versiones en
     la misma sesión; queda documentada la final (AgGrid), con las
     razones del cambio.

     **Cabeceras.** `cols_sem` son `_vol_fmt_rango_semana(semanas[i+1])`,
     función pura nueva (testeada en `test_graficos.py`) que da
     `"15-21 Jun"` si la semana cae en un solo mes y `"29 Jun - 5 Jul"`
     si cruza de mes. Los nombres de columna del DataFrame SON las
     etiquetas visibles.

     **Por qué AgGrid y no `st.dataframe`.** La primera versión iba
     sobre `pandas.Styler` + `st.dataframe(..., on_select="rerun",
     selection_mode="single-row")` — confirmado en vivo que Styler y
     selección de fila SÍ conviven ahí, sin errores (duda real antes de
     tocar código: ningún drill de este proyecto había combinado ambas
     cosas). Pero el pedido sumó tooltip de precio por celda, y
     `st.dataframe` (glide-data-grid, canvas) no tiene NINGUNA API en
     Python para eso — solo `column_config.*Column(help=...)`, que es
     tooltip de CABECERA de columna, no de celda. AgGrid sí, vía
     `tooltipValueGetter` (mismo mecanismo que ya corre en producción en
     `tablas/compras.py`) — así que la tabla completa se migró: el
     semáforo y la barra de Volatilidad pasaron de `Styler.map`/`.apply`
     a `cellStyle` JsCode (patrón que ya usan `ajuste_pivote.py`/
     `compras.py`).

     **Bonus no buscado: sin checkbox.** `st.dataframe` con
     `selection_mode="single-row"` fuerza un checkbox nativo por fila —
     confirmado en el bundle de Streamlit (`DataFrame.*.js`):
     `rowMarkers:{kind:"checkbox", ...}` en cuanto la selección de fila
     está activa, sin parámetro Python para sacarlo. AgGrid con
     `configure_selection(selection_mode="single", use_checkbox=False)`
     (el default de `use_checkbox`) selecciona con un clic en cualquier
     parte de la fila SIN checkbox — confirmado con 0 checkboxes en el
     DOM tras clickear.

     **`.selected_rows` de st_aggrid identifica la fila por CONTENIDO,
     no por índice** (cada nodo trae su `data` completa, columnas
     ocultas incluidas). Por eso el buscador de arriba pre-filtra
     `ranking` en Python SIN ningún truco de key dinámica: no existe un
     índice de fila que pueda desalinearse contra la lista filtrada —
     al revés de lo que hubiera hecho falta con `st.dataframe`
     (selección por índice de fila, ahí sí un problema real si se
     filtra después de clickear).

     **El tooltip necesita precio, no solo el %.** Cada columna-semana
     de `tv` trae dos columnas ocultas hermanas, `__prev_i`/`__cur_i`
     (cierre de la semana anterior / de esta semana), que el
     `tooltipValueGetter` de esa columna lee vía
     `params.data['__prev_i']` — el delta que muestra la celda es cierre
     a cierre, NO apertura/cierre de la MISMA semana (eso ya lo muestra
     el candlestick de abajo al hacer clic en la fila). `__insumo_full`
     (nombre sin truncar) cumple el mismo rol para identificar sin
     ambigüedad la fila clickeada.

     **Verificación real en el navegador, con dos resultados distintos
     para clic y hover.** El CLIC sí se pudo probar de punta a punta: un
     `click` sintético sobre una fila que no era la primera ("Zapallo
     Loche") disparó el rerun de Streamlit y la tarjeta de detalle
     cambió de insumo correctamente — a diferencia de `st.dataframe`/
     Plotly (reglas #74/#12), el clic de AgGrid SÍ responde a eventos
     sintéticos en este entorno. El HOVER del tooltip, no:
     `mouseover`/`pointerover`/`mouseenter` sintéticos sobre una celda
     no hicieron aparecer `.ag-tooltip` — probablemente el manejador de
     tooltip de AG Grid exige un evento *trusted* (real), a diferencia
     del manejador de selección de fila. Confirmado indirectamente en
     vez de en vivo: el `tooltipValueGetter` es el mismo mecanismo que
     ya corre en producción en `tablas/compras.py`, y el grid se
     construyó sin errores de JS (un JsCode mal formado rompe el build
     del grid entero, no falla en silencio — no fue el caso). **Falta un
     smoke test manual real después de deployar**: pasar el cursor sobre
     un % y confirmar que aparece el tooltip con el precio.

     **Card de detalle, a pedido: candlestick y compras de la semana uno
     al lado del otro (`st.columns([1, 1], gap="small")`), no apiladas.**
     El candlestick baja de `alturas.APOYO` (380) a `alturas.MINI`
     (240) — mismo criterio que el gráfico de evolución de Producto,
     que también comparte fila con una tabla (regla #128). Verificado
     por `getBoundingClientRect()`: las dos cajas quedan en la misma
     fila (mismo rango de Y), 426px de ancho cada una, sin superponerse
     — la tarjeta completa bajó de lo que hubiera sido candlestick(380)
     + tabla apilada debajo a 377px de alto total.

131. **Se unificaron "Precio vs año pasado" y "Cantidad vs año pasado"
     (categorías separadas "Precios"/"Cantidad" del rail) en un solo
     drill nuevo, `graficos/compras/vs_ano_pasado.py`**, con un selector
     "Ver: Precio / Cantidad" y un producto en común — mismo espíritu que
     la unificación de Producto (regla #128), a pedido explícito después
     de mostrar el código de las dos vistas viejas.

     **A propósito, Precio y Cantidad NO comparten granularidad.** Precio
     sigue siendo la serie diaria de compras reales (un punto = una
     compra); Cantidad sigue siendo suma mensual. Unificar SOLO la
     pantalla (selector + producto + tarjeta) y no la lógica de cada
     métrica fue una decisión deliberada para no ampliar el pedido: el
     usuario pidió juntar dos pantallas, no rediseñar cómo se agrega cada
     métrica.

     **"(Todos los productos)" queda asimétrico a propósito:** solo
     aparece en el selector cuando `modo == "Cantidad"` — sumar cantidad
     de todos los productos es una magnitud real; promediar o sumar
     PRECIO de productos distintos no lo es. La consecuencia práctica es
     un caso que hay que blindar: si el usuario elige "(Todos)" en
     Cantidad y pasa a Precio, `session_state["compras_vap_prod"]` ya no
     está en la nueva lista de `options` del `st.selectbox` — Streamlit
     **revienta** si el valor guardado no está en `options` al momento
     de instanciar el widget. La guarda va ANTES del `st.selectbox`, no
     con `index=` (que solo aplica en el primer render, no en reruns
     donde `session_state` ya tiene un valor):
     ```python
     if st.session_state.get("compras_vap_prod") not in _opciones_prod:
         st.session_state["compras_vap_prod"] = _opciones_prod[0]
     prod_sel = st.selectbox("Producto", _opciones_prod, key="compras_vap_prod")
     ```
     Mismo problema de fondo que "el foco en la key" (reglas #120/#124/
     #130), pero la solución acá es la contraria: ahí se evitaba con una
     key dinámica; acá la key es fija (`compras_vap_prod`, se comparte
     entre modos a propósito para que el producto sobreviva el cambio de
     Ver) y en cambio se corrige el VALOR antes de que el widget lo lea.

     **Al remover "Cantidad vs año pasado" de la categoría "Cantidad"
     del rail, la categoría quedaba vacía** (era su único ítem) — se
     borró la categoría entera en vez de dejarla con cabecera y sin
     botones. El nuevo ítem único "Vs año pasado" pasó a la categoría
     "Precios", que ya tenía sitio (le quedó "Volatilidad" al lado).

     **No se pudo verificar por UI el caso "(Todos)" → cambiar a
     Precio"** en el navegador de este entorno: el combobox de
     `st.selectbox` (BaseWeb Select) no respondió ni a `type` + Enter ni
     a `form_input` — el valor tipeado se queda en el input sin
     confirmarse como selección real (mismo tipo de fricción de
     automatización que host los clics en canvas, pero acá aplica a un
     `<input>` normal, no a un canvas). Se verificó por lectura de
     código en cambio: la guarda corre siempre, antes de construir el
     widget, sin condición que la salte. **Falta un smoke test manual
     real después de deployar**: en modo Cantidad elegir "(Todos)",
     cambiar a Precio, confirmar que no revienta y cae a un producto
     real.

     **Segunda vuelta, mismo commit tipo: se sumó un tercer modo "Valor"
     que absorbe al drill separado "Vs año anterior"** (gasto por
     Familia, sin selector de producto — nunca lo tuvo, porque es
     agregado). El patrón se repite limpio: `if modo == "Valor": ...
     return` ANTES de construir el selector de producto — ese selector
     directamente no se arma en este modo, no se esconde con CSS. Se
     verificó en el navegador real esta vez (a diferencia del caso
     "(Todos)" de arriba, clickear pills SÍ respondió a eventos
     sintéticos): Valor muestra "Compra por familia: este año vs año
     anterior" con las Familias reales y sin selector; volver a Cantidad
     restaura el producto que estaba elegido antes de entrar a Valor,
     sin excepción. Al borrar el `elif graf == "Vs año anterior"` de
     `__init__.py`, `ACENTO` quedó sin uso ahí (su único consumidor era
     ese bloque) — lo sacó `ruff check`, no una relectura manual.

132. **El rail de navegación dejó de ser una columna izquierda de 90px y
     pasó a ser una franja horizontal de 40px arriba, solo texto
     (2026-08-18).** Pedido con referencia concreta (la barra de MSN
     Dinero) y con el argumento correcto: casi toda webapp de reportes
     financieros ordena la jerarquía de arriba hacia abajo, no de
     izquierda a derecha. Los ítems son etiquetas de texto (`label_corto`
     o el nombre del grupo), sin ícono; el activo se marca con subrayado
     de acento —el mismo tab-subrayado que ya usan las franjas dentro de
     las tarjetas (`_80_cards.py`)—, no con píldora.

     **El cambio no es de un archivo, es de un EJE.** Lo que el rail
     reservaba en ANCHO (90px) pasó a reservarse en ALTO (40px), y todo
     lo que estaba anclado a un borde se movió:

     - **Los `left` bajaron 90px.** `chips_ajuste_tabla` 154→64,
       `fecha_ajuste_pill` 175→85, chips desktop 391→301, y la cadena de
       Ventas › Comparativo (451→361, 667→577). La misma cadena existe
       DUPLICADA en `graficos/compras/_css_proveedor.py` (título
       Proveedor 175→85, pill 287→197, chips 503→413): si se toca una,
       tocar la otra. La franja inferior (`_90`) pasó a `left: 0` y el
       toast/aviso (`_70`) de 100 a 16.
     - **Los `top` se corren `var(--nav-top-alto)`.** La banda de
       `_40_ajuste_franja` (`top: 0` → la variable), los cuatro
       `top: 8px` de `_50_fecha`, el `prov_pop_float` y el rail derecho
       de vistas (`top: 74px` → `calc(var(--nav-top-alto) + 74px)`, ídem
       su `max-height`).
     - **El presupuesto vertical baja 40px**: `--cab-offset-contenido`
       40→80 y su gemelo `_CAB_OFFSET` en `graficos/alturas.py`
       (`PRESUPUESTO` 553→513). La variable va LITERAL, no `calc()`:
       `test_graficos.py` la lee con un regex de `\d+px`.
     - **En móvil `--nav-top-alto` vale 0** (`_99_movil.py`) y los seis
       `calc()` vuelven solos a los valores de siempre, porque allá la
       barra se va abajo. Un solo override en vez de seis.

     **Lo que se retiró:** `--rail-izq-w` / `--rail-izq-full`, el pestillo
     izquierdo entero (`_25_rails_pestillo.py` quedó con un solo lado, y
     `pestillos.py` con una sola constante) — una franja horizontal no le
     quita ancho a la tarjeta, así que no hay nada que recuperar
     plegándola — y el `#nav-topbar`, que llevaba tiempo muerto: salía
     siempre vacío y con `display:none` desde el CSS de la cabecera.

     **Tres trampas medidas en el navegador, ninguna visible en el
     código:**

     1. **El botón medía lo que su TEXTO, no la franja.** Con `help=`,
        Streamlit envuelve el botón en `div > span.stTooltipIcon >
        span.stTooltipHoverTarget` y NINGUNA capa hereda el alto: el
        botón se quedaba en 14px dentro de una franja de 40, así que el
        subrayado del activo y el tinte del hover salían como una tira
        fina a media altura. En el rail vertical no se notaba porque
        allá el alto lo ponía el propio botón (50px fijos). Hay que
        estirar las tres capas. El de Refrescar necesita DOS más
        (`stLayoutWrapper > stVerticalBlock`): vive en un `st.fragment`.
     2. **La copia fantasma.** Dentro de un mismo `stButton` con `help=`
        hay DOS hijos: el botón envuelto en el tooltip y una copia
        suelta. No la esconde nada — medía 0x0 sólo porque su alto salía
        del contenido. En cuanto la franja le dio alto y ancho
        explícitos, **cada reporte apareció DOS VECES**, uno al lado del
        otro. Se oculta con
        `[data-testid="stButton"]:has(.stTooltipIcon) > div:not(:has(.stTooltipIcon))`.
     3. **Los `{}` de un f-string.** El CSS de `navegacion.py` vive en un
        `f"""…"""`, así que toda llave va DOBLE. Un bloque nuevo con
        llaves simples da `NameError: name 'align' is not defined` al
        importar — y **ni `ruff` ni los tests lo ven**: `ruff` acepta la
        f-string y `test_graficos.py` no importa `navegacion`. Lo cazó el
        log del server. Si se toca ese CSS, levantar la app.

     **Verificado midiendo el DOM** (el preview no compone frames para
     screenshot, así que se mide, no se mira) en Compras › Proveedor,
     Ventas y Ajuste a 1366x768, y en 375x812: franja en y=0..40, banda
     en 40..86, fecha/chips en y=48, rail derecho en y=114, cero scroll
     horizontal, y el clic entre reportes cambiando el marcador
     `st-key-app_reporte_*` con el ítem activo correcto.

133. **Compras › Proveedor perdió el botón "✕ Quitar foco" del ranking
     (2026-08-18, a pedido): ahora el foco se limpia DESTILDANDO el
     checkbox de la fila.** El botón existía por una limitación real —
     reclickear la fila YA seleccionada de un `st.dataframe` no vuelve a
     disparar `on_select`, porque el valor del widget no cambia y
     Streamlit no manda rerun (ver regla #128, donde `producto.py` copia
     este mismo patrón y **conserva** sus botones: el cambio fue sólo en
     Proveedor). Quitarlo sin más habría dejado el foco sin salida: el
     drill A/B se abre con el foco y no se cerraría nunca.

     Lo que lo reemplaza es el caso que faltaba procesar. El bloque de
     "procesar clic ANTES de dibujar" de `graficos/compras/proveedor.py`
     sólo miraba `if _rows_sel:` (selección con fila). Se le sumó el
     `elif st.session_state.get("compras_prov_last_click") is not None:`
     → limpia `compras_prov_focus` / `prodfocus` / `perfocus` /
     `last_click`. Funciona porque destildar SÍ cambia el valor del
     widget (`rows: [i]` → `[]`) y por lo tanto sí dispara `on_select` —
     es exactamente el caso que el reclic de la misma fila no puede
     producir.

     Efecto lateral aceptado: si Streamlit resetea la selección de la
     tabla (p. ej. al cambiar chips y remontarse con otros datos), el
     foco se limpia con ella. Es coherente — si la fila ya no está
     marcada en la tabla, el drill de abajo no debería seguir abierto
     apuntándole.

     De paso desaparece el `st.columns([3, 1])` que partía el título:
     ambas mitades eran `[data-testid="stColumn"]` dentro de
     `cp_chart_wrap`, y comían el `min-width: 300px !important` que
     `_css_proveedor.py` pone ahí para que la tabla y la evolución no se
     apreten. El título "Ranking de proveedores" ahora va a ancho
     completo, con el mismo `.cp-rank-tit`.

134. **Piloto de "cada gráfico elige su rango" (2026-08-18): el módulo
     `graficos/periodo.py` y su primera adopción, la evolución de Compras ›
     Proveedor.** Nace de una observación del usuario: los webapps de
     finanzas no ponen un calendario como puerta de entrada, ponen períodos.
     La decisión fue pilotear en UN reporte antes de extenderlo.

     **La mitad que ya era cierta.** "Cargar el parquet entero y filtrar en
     memoria" no era una propuesta nueva: ya pasa en 7 de los 8 archivos.
     El único con `carga_por_rango` es Ventas, y medido el 2026-08-18 se
     entiende por qué: 11.5 MB en R2 → 222.391 filas × 59 columnas → **173 MB
     de RAM** y 37s en frío (11s tibio). El resto es chico: ajusteinventario
     235k×19 = 60 MB en 5s, requerimientos 144k×15 = 32 MB, compras 51k×27 =
     18 MB. Las 10 columnas más pesadas de Ventas son llaves de texto
     (`LLAVE LOCAL DOCUMENTO ITEM`, 7.4 MB) que ningún gráfico dibuja: si
     algún día hay que cargarlo entero, el `SELECT` acotado es la palanca —
     `.astype("category")` NO lo es, las columnas de texto ya vienen con el
     dtype `str` de pandas 3 y el ahorro medido fue cero.

     **La dependencia entre las dos mitades es real y va en un solo sentido:
     rango por gráfico EXIGE carga total.** Mientras el loader de R2 dependa
     del rango de la franja, una vista que pida su propia ventana pediría
     datos que nadie descargó.

     **Lo que hace el módulo.** `ventana()` y `recortar()` son puras (las fija
     `test_graficos.py`, 16 asserts) y `selector()` es lo único que toca
     Streamlit. La opción `HEREDA` ("Rango") no recorta nada: es el default
     heredable, así que la franja sigue siendo el dueño del rango global.

     **El ancla son los datos, no el calendario.** `estado_rango.atajos_rango`
     ancla a `hoy` y hace bien (ahí el usuario elige fechas de calendario y
     "Este mes" ES este mes). Una ventana relativa anclada a `hoy` es un error
     caro: los parquets se regeneran de madrugada y los documentos entran con
     retraso, así que "últimos 12 meses" terminaría en un tramo final vacío
     que se lee como una caída del negocio. El ancla es el ÚLTIMO DÍA CON
     DATOS. Hay un assert dedicado a esto.

     **Qué reemplazó en Proveedor.** La evolución YA tenía ventana propia,
     pero implícita: si el rango de la franja daba menos de 2 períodos,
     conmutaba sola al histórico completo con un `tail(12)` fijo, y el usuario
     se enteraba después por el sufijo "· todo el histórico". Acertaba y era
     inauditable. Ahora la ventana es un control suyo (Rango · 3m · 12m · 24m
     · Todo, default 12m) y el `tail(12)` se fue: contradecía al selector
     (pedir 24m y ver 12 puntos). Las flechas de ventana (`_sl`) siguen siendo
     del RANGO, así que sólo aplican cuando la tarjeta hereda.

     **Dos trampas que costaron una vuelta cada una:**

     1. **El aviso "1 solo período" NO puede ser un `st.caption`.** Con la
        heurística muda fuera, elegir "Rango" sobre 15 días vuelve a dar un
        punto suelto — y hay que decirlo, no corregirlo a escondidas. Como
        caption medía **41px** (dos líneas en una columna de 399) y empujaba
        la tarjeta de 556 a 576px = su `max-height`, con `scrollHeight` 615
        contra `clientHeight` 574: scroll interno, o sea el aviso de que algo
        no se ve tapando lo que sí se veía. Va en el sufijo del título, donde
        cuesta cero alto y queda pegado a las pills que lo resuelven.
     2. **La fila de pills sale del presupuesto vertical** (`alturas.
        FRANJA_PILLS = 30`, medido: 24 de botón + 6 de margen). La figura de
        al lado se lo resta (`_ALTO_EVO = _ALTO_FRAME - FRANJA_PILLS`) para
        que las dos columnas terminen a la misma altura. El primer valor fue
        42 a ojo y sobraba 12px: se corrigió MIDIENDO en el navegador, que es
        la única forma que funciona acá.

     **Y una lección de método, no de código:** verificando esto apareció un
     número que no cerraba (agosto daba S/ 2.104 donde el parquet dice 8.821).
     Antes de tocar nada se comprobó por el camino VIEJO (la opción "Rango",
     que no pasa por el módulo nuevo) y daba lo mismo → no era el cambio. Era
     el server local sirviendo un snapshot viejo de `compras.parquet`: su
     atajo "Todo" decía `1 ene 2023 – 9 ago 2026` cuando el parquet ya llega
     al 15. `data.cargar()` desde un proceso nuevo SÍ devuelve los datos
     frescos, y `limpiar_cache()` desde otro proceso NO borra el `.memo`
     persistido. En Cloud no pasa (`_vigilar_refresco` limpia al cambiar el
     LastModified de R2), pero **en local los números pueden ir atrasados sin
     avisar**: antes de dar por bueno un total de la app local, contrastarlo
     contra el parquet.

135. **El rail de vistas pasó del borde derecho al IZQUIERDO (2026-08-18) —
     y lo caro no fue moverlo, fue lo que estaba MEDIDO contra él.** Mover el
     rail son dos líneas (`right: 15px` → `left: 15px` y la reserva
     `padding-right` → `padding-left`). Lo que costó la vuelta son los cinco
     sitios que daban por hecho de qué lado estaba:

     1. **El jalón de la tarjeta.** `compras_prov_drill_wrap` llevaba
        `margin-left: -16px`, un número medido cuando el lado libre era el
        izquierdo. Reflejado quedaba corrido 18px: la tarjeta arrancaba a
        38px del rail (tenía 20 del otro lado) y dejaba 46px al borde (tenía
        64). Con -34 el layout es el de antes, espejado: 20 y 64.
     2. **El pill flotante "Proveedores"** se anclaba con
        `right: calc(var(--rail-der-res) + 10px)` — derivado del rail para
        seguirlo al plegarse. Con el rail del otro lado esa variable dejó de
        decir nada sobre ese borde. Pasó a `right: 64px`, el borde derecho
        real de la tarjeta. De paso se arregló solo un desfase viejo: medido,
        el pill quedaba 44px adentro del borde que su propio comentario
        decía alinear.
     3. **La sombra del "vistazo"** (`box-shadow: -6px 0`) caía sobre el
        contenido. El contenido cambió de lado: ahora es `6px 0`.
     4. **El chevron del pestillo.** Apunta al DESTINO, no al estado
        (`pestillos.py`), así que las dos flechas se dan vuelta.
     5. **El reset de móvil, que es el que casi se escapa.** Decía
        `padding-right: 1rem` para anular la reserva; al mudarse la reserva a
        `padding-left`, dejó de anular nada y los 153px se quedaban puestos
        en un viewport de 375 — 40% de la pantalla comida por un rail que en
        móvil ni siquiera es una columna. Se arregló anulando **los dos
        lados**: así la regla no vuelve a tocarse si el rail cambia de borde
        otra vez. Sólo apareció por mirar en 375px; en escritorio todo se
        veía perfecto.

     **Lo que NO hubo que tocar** vale igual de documentarlo: la franja
     superior (pill de fecha, chips) no se movió ni un píxel. Vive en
     y=48..74 y el rail arranca en y=114 — nunca se cruzan, así que el lado
     le da igual. Se verificó midiendo, no suponiendo.

     Las variables siguen llamándose `--rail-der-*`. El nombre quedó
     histórico: renombrarlas toca ~15 sitios en 4 ficheros más un assert de
     `test_graficos.py`, y se prefirió dejarlo anotado en `_00_base.py` a
     hacer medio renombre dentro del commit que mueve el layout. Si alguien
     lo hace, que sea completo y en un commit propio.

136. **El ranking de Proveedor pasó de `st.dataframe` a AgGrid para sacarle
     los checkbox (2026-08-19) — y la barra NO necesitó un `cellRenderer`.**
     El pedido era "que funcione con clic en la fila, sin los check". Con
     `st.dataframe` es imposible: su columna de selección no tiene parámetro
     que la oculte (revisada la firma en Streamlit 1.59.2) y tampoco se puede
     esconder por CSS, porque la grilla se dibuja en un **canvas** — no hay
     nodo que tocar. Cambiar de widget era la única salida.

     **La barra es el FONDO de la celda.** Lo que hacía `column_config.
     ProgressColumn` lo hace un `cellStyle` con `linear-gradient(90deg,
     ACENTO 0 W%, LAVANDA_CHIP W% 100%)`, donde W sale de una columna oculta
     (`_barra`, el % contra el mayor — que NO es la columna "%", esa es sobre
     el total del rango). Tres caminos se descartaron con motivo:
     los **sparklines** de AG Grid son Enterprise; un **`cellRenderer`**
     propio obliga a la clase `init()/getGui()` de la regla #25; y el
     gradiente no necesita ninguno de los dos.

     **Los colores van desde `tema.py`, nunca `var(--accent)`:** el grid vive
     en un iframe propio y las variables CSS del documento padre no llegan
     ahí. Es el mismo motivo por el que `custom_css` de AgGrid ya recibía
     hex de `tema.py` (CLAUDE.md § Colores).

     **El toggle hay que escribirlo.** AG Grid, con `rowSelection: {mode:
     "singleRow"}`, no deselecciona al reclickear la fila ya seleccionada
     (pide Ctrl+clic, que nadie descubre). Se resuelve con
     `enableClickSelection: false` + un `onRowClicked` que hace
     `e.node.setSelected(!e.node.isSelected(), true)` — el segundo argumento
     limpia las demás, así sigue siendo selección única. Con eso el gesto
     queda igual al que había con el checkbox, pero en toda la fila.

     **El clic dejó de procesarse ANTES de dibujar.** Con `st.dataframe` la
     selección se leía de `session_state[key]` de la interacción previa, con
     un dedup (`compras_prov_last_click`) para no reprocesar el mismo clic en
     cada rerun. AgGrid DEVUELVE su selección en la llamada: el foco se
     resuelve justo después de dibujar el grid y el dedup desapareció — la
     selección ES el estado, no un evento que se repite. Todo lo que se
     dibuja después (evolución, paneles A/B) ve el foco nuevo en el mismo
     run, así que no hay doble rerun ni parpadeo.

     **Key nueva al cambiar de widget.** Se renombró
     `compras_prov_rank_tab` → `compras_prov_rank_grid`: la vieja quedaba en
     `session_state` con la forma del `st.dataframe` (`{"selection":
     {"rows": [...]}}`) y una sesión abierta se la habría pasado al
     componente nuevo.

     **Al verificar, dos falsos negativos que conviene reconocer:** el grid
     se ve como un `stSkeleton` con el iframe en 0x0 durante los primeros
     segundos (no es un error: es la negociación de alto del componente), y
     una medición tomada a mitad de rerun mostró los paneles A/B con el
     proveedor ANTERIOR mientras el título ya tenía el nuevo. Las dos veces
     el diagnóstico correcto fue esperar y volver a medir, no tocar código.
     Para mirar dentro del componente: `iframe.contentDocument` es
     accesible (mismo origen) y ahí se ven `.ag-row` y los estilos ya
     resueltos.

     **Addendum del mismo día — la primera barra no se leía.** Reportado con
     captura: (1) la pista tintada (`LAVANDA_CHIP`) hacía que la columna
     entera se leyera como un bloque lavanda, "una sombra", compitiendo con
     las barras y tapando las bandas de fila; (2) el monto caía ENCIMA del
     morado, texto oscuro sobre fondo oscuro. Lo segundo tiene una causa que
     no es obvia: el `display:flex` de la propia regla ANULA el alineado a la
     derecha que trae `type: "numericColumn"`, así que el número se iba a la
     izquierda, justo donde está la barra. Arreglo: pista `transparent`,
     `justifyContent: flex-end`, y la barra escalada al **62%** del ancho de
     la celda para que el texto tenga siempre su franja libre. El 62% no
     falsea nada —todas las barras se escalan igual, las proporciones entre
     filas se mantienen— y medido deja 23px entre el fin de la barra más
     larga y el inicio del número más ancho.

     Pendiente deliberado: el Panel A y los dos rankings de `producto.py`
     siguen con `st.dataframe` y sus checkbox. Se convierten con este mismo
     patrón cuando toque.

137. **La franja y las tarjetas comparten UNA sola línea izquierda
     (2026-08-19), y el ancla es la reserva del rail.** Vino de comparar con
     MSN Dinero: ahí la barra lateral ocupa su columna y la franja de
     contexto empieza **a su derecha**, sobre el mismo borde que las tarjetas
     de abajo. En esta app las cuatro capas ya existían (franja de
     navegación → franja de contexto → rail → tarjetas) pero la franja
     cruzaba por encima de la columna del rail: arrancaba en x=85 y las
     tarjetas en 119.

     **El 85 era un fósil.** Todos los anclajes de la franja eran "85 + algo"
     (chips 301 = 85+216; con título de vista: 197 = 85+112 y 413 = 85+328;
     Ventas Comparativo: 361 = 85+276 y 577 = 85+492), y ese 85 venía de
     `175 - 90 del rail retirado` — un número heredado de dos layouts atrás.
     Ahora la cadena entera cuelga de `var(--rail-der-res)`, que es lo que el
     contenido le reserva al rail. Dos cosas salen gratis de derivarlo:
     la franja arranca donde arrancan las tarjetas en cualquier viewport, y
     **al plegar el rail las dos se mueven juntas** (medido: 153 → 93 las
     dos).

     **La tarjeta de Compras soltó su jalón.** Tenía `margin-left` negativo y
     `width: calc(100% + 60px)` para ganar ancho; lo ganaba rompiendo la
     reja. Se quitó entero, incluido el ensanche a la derecha: medido, ese
     `calc(100% + 16px)` NO daba el mismo sobrante en 1280 que en 1440 (el
     `max-width` resuelve su 100% contra otra caja), así que el borde derecho
     bailaba y nada podía alinearse con él. La tarjeta ES la caja de
     contenido; paga ~34px de ancho y a cambio todo cae en la misma reja.

     **La trampa del final: `position: fixed` y la barra de scroll.** El pill
     flotante "Proveedores" quedaba 10px fuera del borde derecho de la
     tarjeta, y el desfase cambiaba con el viewport. No era un cálculo mal
     hecho: el pill es `fixed`, así que se posiciona contra el VIEWPORT
     (1440 medido), mientras que la tarjeta vive dentro del contenedor, que
     mide lo que queda descontada la barra de scroll (1430). Por eso su
     `right` es 90 y no 80 — los 10 son la barra. Cualquier elemento `fixed`
     que quiera alinear con contenido en flujo tiene este problema; si algún
     día se saca el scroll de página, ese sumando vuelve a cero.

     Verificado midiendo en 1280 y 1440, en Compras y en Ajuste: borde
     izquierdo y derecho idénticos entre franja y tarjeta, cero desborde
     horizontal, y el plegado del rail mueve las dos capas a la vez.

138. **El rail subió a la altura de la franja (2026-08-19), y eso obligó a
     recortar la banda blanca.** Cierre del modelo de MSN Dinero que empezó
     la regla #137: allá la barra lateral ocupa su columna DESDE ARRIBA y la
     franja de contexto vive a su derecha. Acá el rail arrancaba 66px más
     abajo que los controles de la franja (`top: calc(--nav-top-alto +
     74px)`); ahora usa el mismo `+ 8px` que ellos, así que rail y controles
     empiezan en la misma línea (y=48 medido).

     **Los dos cambios van juntos o no van.** La banda blanca de la franja
     (`.st-key-fila_ajuste_top::before`, `position: fixed`, y=40..86) iba de
     **borde a borde** — `left: 0`, decisión deliberada de 2026-08-12 para
     que no quedara un filo sin pintar. Eso no chocaba con nada mientras el
     rail arrancara por debajo de ella. Al subirlo, la banda le pasaría por
     detrás y se vería el rail —una tarjeta blanca con borde— montado sobre
     la barra. Por eso la banda ahora arranca en `var(--rail-der-res)`, la
     misma reserva que usan la franja y las tarjetas: **una sola línea
     izquierda para las tres capas**, y las tres siguen al rail cuando se
     pliega.

     El recorte va acotado con `:root:has(.st-key-compras_tabs_row)`, el
     mismo criterio que la reserva de ancho: donde no hay rail, la banda
     sigue tocando los dos bordes. (Al verificar apareció que hoy **todos**
     los reportes medidos —Compras, Ajuste, Ventas, Inventario Valorizado—
     dibujan el rail: el comentario de `_20_compras_rail.py` que decía "no en
     Ventas / Inventario / Requerimientos" quedó viejo. El `:has()` se
     mantiene igual: es la guarda correcta, no una optimización.)

     Lo que NO se tocó: los `margin-top` negativos de las tarjetas. Estaban
     calibrados para que tarjeta y rail arrancaran en la misma línea, y ese
     objetivo cambió a propósito — en el modelo de referencia la barra
     lateral empieza ARRIBA y las tarjetas más abajo, debajo de la franja.

139. **Drill "Documentos SUNAT" de Compras (2026-08-19): un dashboard cuyo
     dato NO sale del parquet.** Nuevo módulo `sunat.py` (capa de datos,
     hermano de `data.py` pero contra la API del SIRE Compras de SUNAT en
     vez de R2) + `graficos/compras/documentos_sunat.py` (la vista, un item
     más del rail de Compras). Deja dos trampas documentadas para no
     repetirlas:

     **Un iframe con un PDF embebido no se ve — nunca, en este stack.**
     Chrome no renderiza un `data:application/pdf` dentro de un `<iframe
     sandbox>`, y Streamlit monta TODOS sus iframes con sandbox (`st.iframe`
     y `components.html` por igual). Se probó: el frame carga con el alto
     correcto, sin error en consola, pero `contentDocument` queda en `null`
     — un rectángulo en blanco que parece un bug de CSS y no lo es. No hay
     combinación de altura/CSS que lo arregle. La solución fue dejar de
     intentarlo: la ficha en PANTALLA es HTML (`_ficha_html`, texto nítido,
     funciona en móvil), y el PDF solo existe para DESCARGAR
     (`sunat.ficha_pdf`, con matplotlib — ya era dependencia del proyecto).
     Ambas representaciones salen de una sola fuente, `sunat.campos_ficha()`,
     para que no puedan divergir.

     **Un bloque de controles fuera de las tarjetas rompe el presupuesto
     vertical de TODAS las vistas de la app, no solo la propia.** Esta app
     no tiene scroll de PÁGINA (el main lo recorta); cada tarjeta se clampea
     a `--alto-util` con scroll INTERNO (`estilos/_80_cards.py`), pero ese
     clamp da por sentado que la tarjeta arranca donde arranca cualquier
     otra vista (la franja global de siempre, ~y=144). El primer intento de
     este drill puso período/vista/KPIs en una fila PROPIA arriba de las dos
     columnas — medido en el navegador: la tarjeta pasó a arrancar en y=266
     (o más, con el aviso de credenciales en su propio renglón) y su borde
     inferior terminaba en 990 con un viewport de 900: 90px inalcanzables,
     sin error ni aviso, indistinguibles de "el gráfico está cortado".
     Arreglo: los controles se movieron ADENTRO de la tarjeta izquierda —
     mismo patrón que ya usaba "Semanal" con su selector "La semana
     empieza" (`graficos/compras/__init__.py`) — así el offset externo
     vuelve a ser el de siempre y lo que sobra scrollea DENTRO de la
     tarjeta, no empuja nada hacia afuera. Regla general: en un dashboard
     con rail, cualquier control que no viva ya en la franja global va
     DENTRO de una tarjeta con `max-height: var(--alto-util)`, nunca en un
     bloque suelto entre la franja y las tarjetas.

     El SIRE Compras devuelve el REGISTRO del comprobante (proveedor,
     fecha, importes) — no el PDF ni el XML que emitió el proveedor; eso
     vive en otro servicio (descarga masiva de CPE) con otras credenciales,
     hoy sin conectar. `sunat.py` lo dice en su docstring para que nadie lo
     de por hecho leyendo solo la UI.

140. **El flujo de descarga documentado por SUNAT para el SIRE Compras
     está roto, y el que funciona no está en ningún manual** (2026-08-19,
     verificado contra el RUC 20605204300 real, con datos de producción).

     El manual oficial («Manual de servicios Web Api - SIRE_Compras v22»)
     documenta un flujo ASÍNCRONO de 3 pasos para bajar el detalle de la
     propuesta: `exportacioncomprobantepropuesta` (pide un ticket) →
     `consultaestadotickets` (se sondea hasta que termina) →
     `archivoreporte` (baja el ZIP). Se implementó tal cual el manual y
     **nunca funcionó**: el ticket se procesa, termina con estado 06 (OK),
     entrega un nombre de archivo… y `archivoreporte` responde que ese
     archivo no existe:

         422 · cod 2244 "El archivo solicitado no existe."
         500 · com.mongodb.MongoGridFSException: No file found with the
               filename: <RUC>-<fecha>-propuesta.zip and revision: -1

     Se probaron las dos rutas de descarga que documenta el manual
     (`gestionprocesosmasivos/web/masivo/archivoreporte` y una variante),
     `codOrigenEnvio` 1 (portal) y 2 (API), y todos los valores de
     `codTipoArchivoReporte` que tienen sentido (00, 0, 1, 2, null, vacío)
     — siempre el mismo resultado. SUNAT nunca escribe el archivo que su
     propio ticket anuncia. No es un parámetro mal puesto de este lado.

     De paso, otro bug real de SUNAT que costó tiempo: la respuesta de
     `consultaestadotickets` trae el campo **mal escrito**,
     `codTipoAchivoReporte` (sin la primera "r" de "Archivo") — y el propio
     manual repite el typo al citarlo. Leer el nombre bien escrito
     devuelve `None` en silencio y arrastra el error de arriba con una
     causa falsa (parecía un problema de parámetro, no de disponibilidad
     del archivo).

     **Lo que sí funciona** se encontró mirando la pestaña Network del
     navegador mientras el propio portal del SIRE (`e-menu.sunat.gob.pe` →
     Empresas → Sistema Integrado de Registros Electrónicos → Registro de
     Compras Electronico → Gestión de Compras → pestaña "Propuesta del
     RCE") pintaba su tabla paginada: un GET síncrono a

         …/rce/propuesta/web/propuesta/{periodo}/busqueda
             ?codTipoOpe=1&page={page}&perPage={perPage}

     que devuelve el detalle completo en JSON — sin ticket, sin ZIP, sin
     encolar nada. Responde en segundos. No está en el manual v22 (ni se
     encontró en ninguna doc pública); es el mismo endpoint que consume el
     frontend del SIRE. **Riesgo aceptado a propósito**: al no ser un
     contrato público, SUNAT puede cambiarlo sin aviso. El día que empiece
     a fallar, repetir el mismo diagnóstico (DevTools → Network → filtrar
     XHR → reproducir la acción en el portal) antes de asumir que es un
     bug nuestro.

     **Y el propio endpoint bueno tiene DOS bugs más, encontrados recién
     al comparar los totales contra el portal:**

     - `perPage` tiene un TOPE DE 100 no documentado. Pedir 150 o 200 da
       422 (`JerseyViolationException`). Se probó subirlo a 200 "para
       hacer menos llamadas" sin verificar primero, y falló — quedó
       comentado en `sunat.py::FILAS_POR_PAGINA` como advertencia para no
       repetir el mismo apuro.
     - **La paginación se SOLAPA.** El offset (`page`) avanza bien, pero
       el límite de filas que devuelve cada página es `page * perPage`, no
       `perPage`. Pidiendo `perPage=100` sobre 323 comprobantes reales:
       `page=1` → 100 filas, `page=2` → **200** filas (les 100 de la
       página 1 más 100 nuevas), `page=3` → 123, `page=4` → 23. Acumular
       las páginas a ciegas da 446 filas y un total un 38% más alto que el
       real — un número que se ve perfectamente plausible en un dashboard
       de compras y está mal. `sunat.py::obtener_comprobantes` deduplica
       por `codCar` (el identificador único de la anotación en SUNAT) y
       corta cuando junta el `totalRegistros` que la propia API declara.
       Verificado al cierre: con el fix, los 323 documentos, la base
       imponible (S/ 160.147,83) y el IGV (S/ 27.493,38) coinciden EXACTOS
       con la tabla "Resumen de CP" del portal, al centavo.

     **Lección para la próxima vez que se integre una API de SUNAT sin
     SDK oficial**: no confiar en que "el ticket dice OK" o "la respuesta
     vino 200" significa que el dato está completo — verificar el TOTAL contra
     una fuente independiente (acá, la tabla del propio portal) antes de
     dar por buena una integración. El bug de paginación no daba NINGÚN
     error; el número simplemente estaba mal.


141. **Documentos SUNAT se ordena por FECHA DE EMISIÓN, no por período
     tributario — y la razón es un bug de datos que un usuario cazó mirando
     la pantalla** (2026-08-19/20). El selector de período `yyyymm` que
     tenía la vista se sacó entero; ahora responde al rango de la franja
     superior, como Proveedor y Producto.

     **El hallazgo que lo motivó:** con el selector de período, un usuario
     notó algo que no cuadraba — el período decía "08/2026" pero la tabla
     mostraba documentos con fecha de emisión de octubre de 2025. Verificado
     contra el dato CRUDO de SUNAT (no un bug de parseo de fechas: la API
     manda `fecEmision` en ISO, sin ambigüedad): la propuesta de un período
     **No Presentado** (abierto) no es "lo del mes" — es una ventana de
     **12 meses** de comprobantes pendientes de anotar, porque en Perú el
     crédito fiscal se puede tomar hasta 12 meses después de la emisión.
     Medido: el período 202608 (abierto) devolvió 1.033 documentos con
     fechas desde 2025-08 hasta 2026-08, contra 323 del período 202607 ya
     **Presentado** (cerrado), que sólo trae lo de ese mes.

     **La trampa doble, y por qué un solo período no alcanza:** los
     documentos emitidos en julio están repartidos en DOS períodos
     distintos y sin superposición. Verificado por `codCar` (el
     identificador único de SUNAT): de lo emitido en julio, 290 documentos
     viven en el período 202607 (ya registrados) y otros 88 —completamente
     DISTINTOS, cero coincidencia— sólo aparecen en la propuesta del
     período 202608 (abierto, pendientes de anotar). Pedir un solo período
     deja agujeros en cualquiera de los dos sentidos: sólo 202607 pierde
     los 88 pendientes; sólo 202608 pierde los 290 ya registrados.

     **La solución:** `sunat.obtener_comprobantes_rango(fecha_ini,
     fecha_fin)` calcula qué períodos hacen falta
     (`periodos_a_consultar`: desde el período de `fecha_ini` hasta el más
     reciente disponible), los trae todos, deduplica por `codCar` — un
     documento no debería repetirse entre períodos, pero si SUNAT
     alguna vez lo hiciera, gana el "Registrado" por ser el estado más
     definitivo — y RECIÉN AHÍ filtra por `fecha_emision` dentro del
     rango pedido. Cada fila queda marcada con `situacion`
     ("Registrado"/"Pendiente"), que sale gratis (ya se sabe de qué
     período vino) y es información accionable: un "Pendiente" es una
     compra que SUNAT ve y el contribuyente todavía no anotó — crédito
     fiscal sin tomar. La vista lo resalta en ámbar y lo suma en los KPIs
     ("N pendientes (S/ monto)"), y ofrece un filtro Todos/Registrados/
     Pendientes.

     Verificado al cierre contra ABRASA S.A.C.: el rango de julio completo
     da 378 documentos (290 Registrados + 88 Pendientes), todos con fecha
     de emisión dentro de julio — sin las filtraciones de meses vecinos
     que tenía el enfoque por período.

     **Lección repetida de la regla #140**: el bug no dio ningún error.
     Un total plausible bajo un título que sugería otra cosa. Lo cazó un
     usuario mirando la pantalla con atención, no un test ni una excepción
     — motivo de más para que cualquier vista que agregue datos externos
     muestre de dónde salió cada número, no sólo el total.

142. **El PDF/XML ORIGINAL del proveedor (no la ficha renderizada) llega por
     un camino totalmente distinto al resto de `sunat.py`, y a propósito
     vive FUERA de la webapp** (2026-08-19).

     El disparador: un usuario trajo el zip de un proyecto de terceros
     (`app-sire`, escritorio Tkinter + Playwright) que resuelve justo el
     hueco que el docstring de `sunat.py` venía marcando desde la regla
     #139 — el original no tiene API pública, sólo se consigue con los
     mismos clics que una persona en el portal SOL (Consulta de
     Comprobantes de Pago). Ese proyecto también trae el flujo de
     tickets/ZIP de la regla #140 (mismo hallazgo: roto del lado de
     SUNAT) y una GUI de escritorio completa — de ahí sólo se rescató la
     pieza que faltaba, el downloader de Playwright.

     **Por qué no se integró en vivo a la webapp:** esa pieza abre un
     Chromium real con técnicas anti-detección activas (esconde
     `navigator.webdriver`, user-agent de navegador real) para que el
     login pase — Streamlit Community Cloud no da un entorno confiable
     para instalarlo/correrlo, y aunque lo diera, exponerlo a que
     cualquier clic de cualquier visita dispare un login al portal SOL de
     SUNAT es un patrón mucho más "bot" que las llamadas OAuth2 que ya
     hace `sunat.py` — más plausible que la cuenta quede señalada. Mismo
     tipo de riesgo aceptado que el endpoint no documentado de la regla
     #140, un escalón más arriba.

     **La solución — separar buscar de servir, mismo patrón que ya usa
     toda la app con R2:**
       · `herramientas/sunat_originales_sync.py` corre LOCAL, a mano. Usa
         `sunat.py` para listar los comprobantes del rango, Playwright
         para bajar cada PDF/XML del portal SOL, y sube ambos a R2 con la
         clave que arma `sunat._clave_original`
         (`sunat_originales/<ruc_proveedor>/<serie>-<numero>.<ext>`).
         Salta lo que ya está subido (backfill incremental; `--forzar`
         para repetir).
       · `sunat.originales(doc)` sólo LEE esas claves de R2
         (`_leer_original`, cacheada 1h). Nunca lanza: no encontrar nada
         es el estado normal de un documento que el sync todavía no tocó,
         no un error.
       · `graficos/compras/documentos_sunat.py::_panel_documento` muestra
         los botones de descarga del original SÓLO si `sunat.originales`
         trajo bytes; si no, se queda con la ficha renderizada de siempre
         (`ficha_pdf`, que no depende de ningún sync y sigue funcionando
         para el 100% de los documentos). Los dos estados conviven — no es
         un reemplazo, es un enriquecimiento cuando existe.

     **Una mejora deliberada sobre el proyecto original, no una copia
     literal:** el downloader de terceros abre navegador y se loguea DE
     NUEVO por cada comprobante — para un período de cientos de
     documentos son cientos de logins contra el mismo portal. El script
     de este repo loguea UNA vez por corrida y reutiliza la sesión para
     todos los documentos pendientes: más rápido y una señal de bot mucho
     más chica.

     **Verificado en vivo (2026-08-20), y costó tres arreglos que vale
     anotar porque son la clase de cosa que vuelve a morder:**
       · El login fallaba con "Error en la invocación" hasta que se
         visitó `sunat.gob.pe` ANTES y se mandó `referer` explícito.
         Saltar directo a la URL profunda no alcanza. La URL en sí era
         correcta desde el principio — se sospechó de ella y se la
         cambió por una peor (`AutenticaMenuInternet.htm` sin
         parámetros, que es la página de VUELTA post-login, no un punto
         de entrada). Un usuario copió la URL real de su sesión y
         resultó idéntica a la original.
       · Al pasar al 2º documento, el panel "Resultado" del anterior
         tapaba el menú → reset con `goto` a la URL del menú antes de
         cada documento.
       · "Nueva Consulta de comprobantes de pago" resolvía a un acceso
         de **Favoritos oculto** que SUNAT agrega tras el primer uso:
         con `.first` se agarraba el escondido. `_click_texto_visible`
         recorre todas las coincidencias y clickea la visible.
     Resultado: **3 de 3 documentos en una sola sesión**, con PDF y XML,
     cero errores. Los archivos en R2 quedaron como corresponde: PDF
     válidos y XML planos con su detalle de líneas (1, 2, 3 y 14 líneas
     según el comprobante).

143. **Cruce SIRE ↔ parquet de Compras: la clave `serie-número` sola
     produce falsos positivos si no se acota por fecha primero**
     (2026-08-20). `graficos/compras/documentos_sunat.py::cruzar_con_parquet`
     compara cada comprobante del SIRE contra `compras.parquet` por
     Fecha de emisión, RUC, Proveedor, Base imponible y Total, y marca
     cada uno **Coincide / Diferencia / Solo SUNAT / Solo sistema**. (En
     el momento en que se escribió este párrafo el parquet no traía RUC
     — solo `COD_PROVEEDOR`/`LLAVE_PROVEEDOR`, un código interno —; el
     addendum de abajo cuenta qué cambió cuando se agregó.)

     **El bug que casi se publica:** el primer intento cruzó por
     `documento` (`serie-número`, ej. `"E001-1"`) contra el parquet
     COMPLETO (3 años de historial). Contra el RUC 20605204300, julio
     2026, dio diferencias de hasta **S/18.632** en documentos que la
     tabla mostraba como "coincidentes". Verificado con los nombres de
     proveedor de cada lado: eran empresas Y AÑOS completamente distintos
     (2023-2025) que compartían la clave por pura casualidad — `"E001"`
     es la serie por defecto de miles de emisores electrónicos, y el
     número es un correlativo interno de CADA proveedor, así que colisiona
     seguido en un historial de 14.000+ documentos.

     **La corrección:** `_parquet_agrupado_por_documento` acota el parquet
     al MISMO rango de fechas que se está comparando, ANTES de armar la
     clave — no es una optimización, es lo que hace confiable el cruce.
     Medido el efecto: el promedio de diferencia bajó de S/372 a S/6,9 y
     el máximo de S/18.632 a S/1.199. Lo que queda ya son diferencias
     reales (redondeo, líneas no cargadas — la más chica real medida fue
     S/34,21), no colisiones de clave.

     **Ni acotando por fecha la clave es 100% única**: 3 de 269 claves de
     julio tenían más de un proveedor compartiendo `serie-número` DENTRO
     del mismo mes. `cruzar_con_parquet` no colapsa a ciegas — cuando una
     clave tiene varios candidatos, se queda con el que coincide por
     NOMBRE (normalizado con `utils._norm`); si ninguno es plausible, NO
     fuerza el emparejamiento. El candidato descartado no se pierde: queda
     como su propio "Solo sistema" — mejor dos filas sin cruzar que una
     cruzada contra la factura de otro proveedor. Cubierto en
     `test_graficos.py` con el caso mínimo que reproduce la ambigüedad.

     Verificado al cierre contra ABRASA S.A.C., julio 2026: 411 filas —
     154 Coincide, 85 Diferencia (S/336 en total, montos chicos y
     plausibles), 139 Solo SUNAT (**S/125.550** sin cargar — el hallazgo
     de negocio real de esta función), 33 Solo sistema (S/8.034).

     **Lección, otra vez repetida** (regla #140, #141): ninguno de estos
     bugs —el de la descarga rota, el de la paginación solapada, el de
     esta colisión de clave— dio jamás un error. Todos eran un número
     plausible en el lugar equivocado. La única defensa real es verificar
     agregados contra una fuente independiente antes de confiar en un
     cruce, no confiar en que "no hay excepción" signifique "está bien".

     **Addendum (mismo día, unas horas después): el parquet sumó RUC, y
     eso destapó un segundo bug de agregación.** El usuario agregó
     `INDICADOR TRIBUTARIO` a `compras.parquet` — el RUC del proveedor,
     que hasta entonces no existía ahí (solo `COD_PROVEEDOR`, un código
     interno). Con RUC de los dos lados, `cruzar_con_parquet` pasó a
     emparejar por **RUC exacto primero** y recién si no hay uno usa el
     nombre como red de seguridad — verificado al cierre: de 85 filas
     "Diferencia" contra ABRASA S.A.C., **0 tienen RUC distinto entre
     SUNAT y el sistema**. Antes, con solo el nombre, no había forma de
     afirmar eso con la misma certeza.

     Antes de usarlo tal cual, dos detalles reales del dato:
     - `INDICADOR TRIBUTARIO` trae ~24% de sus filas con un **espacio
       final** (`"20609456052 "`, 12 caracteres en vez de 11) — contado
       sobre el parquet real. `_parquet_agrupado_por_documento` siempre
       lo pasa por `.str.strip()`; comparar crudo habría hecho fallar el
       match por RUC en 1 de cada 4 filas, en silencio.
     - `_parquet_agrupado_por_documento` agrupa por (documento, RUC,
       **proveedor**) y no solo por (documento, RUC): cuando el RUC viene
       vacío en dos filas de proveedores DISTINTOS que comparten
       documento — pasa, es la misma flojera de origen del punto
       anterior —, agrupar sin el proveedor las fusiona bajo la clave
       `("...", "")` y SUMA los montos de dos compras distintas como si
       fueran una. Lo cazó un test, no una corrida real: al escribir el
       caso mínimo para probar el fallback por nombre, la clave de
       "ya emparejado" de `cruzar_con_parquet` (que en ese momento era
       solo `(documento, ruc)`) descartaba en silencio al segundo
       candidato con RUC vacío en vez de dejarlo como su propio "Solo
       sistema" — mismo síntoma de siempre: ningún error, un número
       (acá, un conteo de filas) que daba 6 en vez de 7. Se corrigió
       trackeando la tripleta completa, que es la clave real que arma
       la agrupación.

     **Addendum 2 (mismo día, otra ronda): el parquet sumó `TOTAL
     DOCUMENTO`, y el "Total" del cruce estaba comparando contra un
     proxy.** El usuario también agregó `TOTAL DOCUMENTO` — antes no
     existía, y `total_pq` salía de sumar `VALOR_BRUTO_COMPRA_MN` (un
     valor POR LÍNEA de producto) para todas las líneas del documento.
     Es una aproximación razonable la mayoría de las veces, pero no el
     total real: es una reconstrucción, sujeta a redondeo y a que ninguna
     línea falte.

     `TOTAL DOCUMENTO` es un campo de CABECERA — se repite igual en cada
     línea del mismo documento (0 de 515 documentos con más de un valor
     distinto, verificado agrupando por documento+RUC+proveedor en una
     ventana de 60 días sobre datos reales de ABRASA) —, así que
     `_parquet_agrupado_por_documento` lo agrega con `"first"`, nunca
     `"sum"`: sumarlo multiplicaría el total por la cantidad de líneas del
     documento (`COL_TOTAL_PARQUET`). `base_pq` sigue sumando
     `VALOR_COMPRA`, que sí es por línea — no cambia.

     Medido el efecto sobre el mismo cierre de julio 2026 (ABRASA): los 4
     estados no se movieron (154/85/139/33) y la suma de diferencias de
     "Diferencia" tampoco (S/335,85) — la vieja reconstrucción por línea
     ya era casi exacta cuando el cruce está bien acotado por
     fecha+RUC+proveedor (ver arriba). El cambio no es cosmético igual:
     es la fuente correcta ahora que existe, deja de depender de que
     todas las líneas de un documento estén cargadas y sin ese error de
     redondeo acumulado, y sin él un documento con una línea faltante
     habría mostrado una "Diferencia" que no es tal.

     Trae red de seguridad: si `TOTAL DOCUMENTO` no está en el parquet
     (columnas viejas, entorno sin propagar), `_parquet_agrupado_por_documento`
     cae al proxy de siempre (`sum(VALOR_BRUTO_COMPRA_MN)`) en vez de
     reventar. Cubierto en `test_graficos.py`: un caso con dos líneas del
     mismo documento donde la suma por línea (70) y el total real (59)
     **difieren a propósito**, para que el test falle si algún día alguien
     "simplifica" la agregación de vuelta a `"sum"`.

     **Addendum 3 (mismo día, tercera ronda): mismo arreglo para la Base
     imponible, con `TOTAL NETO`.** El usuario agregó `TOTAL NETO` y
     `TOTAL IGV` a `compras.parquet` — hasta entonces `base_pq` salía de
     sumar `VALOR_COMPRA` por línea, el mismo defecto que tenía `total_pq`
     antes del Addendum 1. Mismo patrón: `TOTAL NETO` es de CABECERA (0 de
     515 documentos con más de un valor distinto, misma ventana de
     verificación de 60 días sobre ABRASA), se agrega con `"first"`. Cuadra
     con el resto: `TOTAL NETO + TOTAL IGV == TOTAL DOCUMENTO` en 512 de
     515 grupos (el resto, redondeo de centavos). `_parquet_agrupado_por_documento`
     quedó simétrico — un solo bloque que elige columna+agregación para
     base y total en vez de si/else duplicado por campo (`COL_BASE_PARQUET`
     junto a `COL_TOTAL_PARQUET`), con la misma red de seguridad si la
     columna no está.

     Un hallazgo real, aparte, salió de remedir contra ABRASA julio 2026
     con la Base ya corregida: varios documentos de proveedores como
     "LA CESTA S.A.C." muestran `base_sunat = 0` con `total_sunat ≈
     total_sistema` (diferencia de centavos). No es un bug del cruce —
     el registro crudo del SIRE trae `no_gravado` (no `base_imponible`)
     con el importe completo: son compras SIN IGV (ej. alimentos sin
     procesar, exonerados), y SUNAT separa "base gravada" de "no gravado"
     en dos campos distintos, mientras que `TOTAL NETO` del parquet no
     distingue uno de otro. El Total sigue cuadrando (por eso el propio
     KPI de "con diferencia" —que solo suma `dif_total`, no `dif_base`—
     no se movió: 85 filas, S/335,85 antes y después de este addendum).
     Queda anotado para una eventual mejora (sumar `no_gravado` al lado
     SUNAT de la Base antes de comparar), no resuelto en esta pasada:
     tocar cómo se arma `base_imponible` en `sunat._normalizar_registro`
     es una decisión de diseño aparte, no un bug de la agregación que
     pedía esta tanda.

     **Addendum 4 (mismo día, cuarta ronda): resuelto — el usuario
     confirmó la equivalencia y la diferencia de S/22.889 desapareció.**
     El usuario aclaró en el mensaje siguiente: **"total neto = base
     imponible"** — para su sistema, `TOTAL NETO` es el neto del
     documento completo, gravado o no, sin distinguir. La comparación
     correcta entonces no es `base_pq` vs `base_imponible` del SIRE, es
     `base_pq` vs `base_imponible + no_gravado` (ambos campos ya salían
     de `sunat._normalizar_registro`, solo faltaba sumarlos en el cruce —
     no hizo falta tocar `sunat.py`). `cruzar_con_parquet` ahora arma
     `base_sunat = base_imponible + no_gravado`.

     Medido el efecto sobre el mismo cierre de ABRASA julio 2026 — antes
     vs después de este addendum:
     | | Coincide | Diferencia | Solo SUNAT | Solo sistema |
     |---|---|---|---|---|
     | Antes (solo `base_imponible`) | 154 | 85 (S/335,85 total · **S/22.889,45 base**) | 139 | 33 |
     | Después (`+ no_gravado`) | **218** | **21** (S/335,72 total · **S/436,83 base**) | 139 | 33 |

     **64 documentos** que mostraban "Diferencia" únicamente por el
     split gravado/no-gravado pasaron a "Coincide" — eran falsos
     positivos, no diferencias de negocio. Los 21 que quedan son reales
     (ej. `F001-2400` de LA CESTA S.A.C., -S/202,00, ya visto en el
     Addendum 1). El total nunca se movió (S/335,85→S/335,72, la
     diferencia es solo redondeo) porque el Total nunca tuvo este
     problema — solo la Base, que es justamente el campo que el KPI
     compacto (`_kpis_cruce`) NO resume en soles (solo cuenta filas), así
     que el error de S/22.889 en agregado no se veía en pantalla — otro
     caso de "ningún error, un número plausible en el lugar equivocado"
     (regla #140/#141), esta vez escondido por no estar en el resumen
     visible.


160. **El registro del SIRE pasó de consulta EN VIVO a parquet en R2, y
     eso cambia lo que se le puede pedir a la vista** (2026-08-20;
     renumerada el 2026-08-22 — nació con el mismo número que la regla
     de arriba y las referencias externas a "#143" quedaban ambiguas).

     Hasta acá el drill «Documentos SUNAT» llamaba a la API del SIRE en
     cada visita. Andaba, pero pagaba dos costos que sólo se ven con
     datos reales:

     - **Escala con el ancho del rango, no con el resultado.** La API
       sólo habla por período mensual: un rango de 3 años son 38 llamadas
       encadenadas de ~9 seg — **~6 minutos** con el usuario esperando.
       Medido contra el parquet, mismo rango: **0,02 seg**. Y es PLANO —
       8 meses y 3 años cuestan lo mismo, porque el filtro es sobre un df
       ya cargado. La diferencia crece justo donde más molesta.
     - **Heredaba la disponibilidad de SUNAT**, que no es buena.
       Verificado en vivo el mismo día: "Error del Servidor — reintentar
       en 5 minutos". En vivo eso es un error en pantalla; con parquet el
       usuario ve la corrida anterior y no se entera.

     **La forma:** `herramientas/sunat_registro_sync.py` corre de
     madrugada en la CPU local (la misma que ya extrae del SQL Server —
     no se apaga y ya tiene credenciales de R2), trae los 38 períodos y
     sube `sunat_compras.parquet`. La webapp sólo lee. Es el MISMO trato
     que el resto de la app tiene con sus datos, y el mismo que se le dio
     a los originales PDF/XML en la regla #142: **la webapp nunca busca
     datos afuera, sólo los lee de R2.**

     Medido en la primera corrida real: **16.577 comprobantes** (jul-2023
     a ago-2026), 11.054 pendientes, 654 proveedores, **734 KB** de
     parquet, **4,3 minutos** de proceso. Verificado que el parquet
     devuelve EXACTAMENTE lo mismo que la API para el mismo rango —
     mismo conteo, mismo total al centavo, mismo conjunto de `car`.

     **`sunat.comprobantes_rango()` es la puerta, y devuelve `(df,
     origen)`** — prefiere el parquet y cae a la API si todavía no
     existe. Ese fallback no es adorno: hace que la vista funcione igual
     ANTES de la primera corrida del sync, así que el cambio se puede
     desplegar sin coordinar con nada. `test_sunat.py` cubre el contrato
     de la tupla, porque la vista lo desestructura y devolver un df
     pelado la rompería con un ValueError que no señala la causa.

     **El origen se MUESTRA en pantalla**, como un ítem más de la tira de
     KPIs (`_sello_origen`): "hoy" / "ayer" / "hace N días", en ámbar
     pasadas 36 h. Un proceso de madrugada sin alertas tiene un agujero
     conocido —si deja de correr nadie se entera, y el dato viejo se ve
     igual de plausible que el fresco— y esta es la versión barata de
     taparlo: la misma lección de las reglas #140/#141, donde lo que
     falló no dio ningún error, sólo un número creíble.

     **Lo que el parquet NO trae:** el detalle de líneas (qué se compró,
     cuánto, a qué precio unitario). Una fila = un DOCUMENTO. El detalle
     vive dentro del XML, o sea del lado caro (regla #142). Esa asimetría
     es la que ordena todo el diseño: **cabecera barata y completa desde
     el día 1; detalle caro y parcial, que se llena de a poco.**


144. **Pedir un original a demanda: el mismo mecanismo de señales que ya
     tenía la app, aplicado a otra cosa** (2026-08-20).

     La corrida nocturna de originales (regla #142) baja de lo más nuevo
     hacia atrás y tarda **semanas** en cubrir la ventana: medido con
     datos reales, 9.821 documentos dentro de los 24 meses que SUNAT
     sirve, a ~30 seg cada uno — ~41 noches a 2 h por noche. Mientras
     tanto, un comprobante viejo simplemente no está, y esperar semanas a
     que le llegue el turno no sirve cuando alguien lo necesita hoy.

     **La solución no fue inventar nada:** el proyecto YA tenía un
     mecanismo de señales para refrescar parquets bajo demanda
     (`data.py::solicitar_refresco` escribe un JSON en R2, la CPU local
     lo levanta y lo atiende). Acá se usa el mismo patrón con otro
     prefijo: `sunat.solicitar_original()` deja la señal en
     `_solicitudes_sunat/`, y `herramientas/atender_solicitudes_sunat.py`
     la levanta, baja ESE comprobante y borra la señal. El usuario espera
     menos de un minuto en vez de semanas.

     **La webapp nunca abre un navegador ni habla con el portal SOL.**
     Sólo pide. Es la misma línea que separa las reglas #142 y #160: la
     app lee de R2 y deja pedidos; el trabajo sucio pasa en la máquina
     local. Eso es lo que permite que todo esto conviva con Streamlit
     Community Cloud, donde Playwright no entra.

     Cuatro decisiones que parecen detalles y no lo son:

     - **La clave de la señal es determinista**
       (`_solicitudes_sunat/<ruc>_<serie>-<numero>.json`): dos clics sobre
       el mismo documento pisan la misma señal en vez de encolar dos
       pedidos idénticos que harían bajar el comprobante dos veces.
     - **Prefijo PROPIO, separado de `sunat_originales/`.** Si la señal
       cayera bajo el prefijo de los originales, `_claves_ya_en_r2` la
       contaría como archivo sincronizado y el sync nocturno saltearía
       ese documento **para siempre**, sin error ni aviso. Hay test.
     - **La señal se borra SIEMPRE**, salga bien o mal. Si no, un
       comprobante que SUNAT no puede servir (fuera de ventana, dado de
       baja) dejaría a la webapp mostrando "⏳ pedido" eternamente y al
       script reintentándolo en cada pasada. Que el usuario vea de nuevo
       el botón y decida es mejor que un bucle mudo.
     - **Varios pedidos, UN solo login.** Abrir Chromium y loguearse
       cuesta ~15 seg, más que consultar un comprobante: si hay 3
       pedidos, se abre el navegador una vez y se atienden los 3 en la
       misma sesión. Y una pasada SIN pedidos sale en ~1 seg sin abrir
       nada, así que es barato programarla cada minuto.

     El panel del documento ahora tiene tres estados en vez de dos:
     original disponible (botones de descarga), pedido en curso (aviso de
     espera), o no sincronizado (botón para pedirlo). La ficha
     renderizada del registro sigue estando siempre, en los tres.

145. **La GRILLA tiene un dueño, igual que el color y el alto**
     (`graficos/compras/_comun.py::COLUMNAS_DRILL`). Tercera cara del mismo
     patrón que `tema.py` (color) y `alturas.py` (alto vertical): el EJE
     HORIZONTAL de una vista tampoco puede escribirse a mano en cada fila.

     El bug (2026-08-21, reportado con captura). El drill de Proveedor tenía
     dos filas de dos columnas y cada una partía en un sitio distinto: la de
     arriba con `st.columns([1.6, 1])` (61.5%) y la de abajo con
     `st.columns(2)` (50%). Los dos números son correctos leídos por
     separado — y por eso nadie los miraba juntos. Medido en el navegador,
     viewport 1536x864: el canal gris entre columnas caía en x=949 arriba y
     en x=800 abajo, o sea el eje de la página saltaba ~150px a media
     altura. La vista dejaba de leerse como una grilla.

     Encima venían dos asimetrías más, que son la misma enfermedad:

     - **La fila de abajo bailaba con los datos.** El ranking de arriba
       tiene el alto congelado (`_ALTO_FRAME` = 8 filas = 325px, lo que
       sobra scrollea dentro), pero la tabla del Panel A lo sacaba de
       `por_filas(len(tv), ..., minimo=0)`: 80px con 1 producto, 430 con 12.
       Cada clic en el ranking cambiaba el alto de la tarjeta y empujaba la
       tabla de documentos de abajo. Ahora usa el MISMO `_ALTO_FRAME`.
     - **Arriba dos tarjetas, abajo una.** Los paneles A/B eran UNA tarjeta
       ancha (`compras_prov_card_paneles`) con dos `_card` transparentes
       adentro, mientras la fila de arriba son dos bloques
       `compras_prov_card_*` separados por el gris del app. Ahora son cuatro
       bloques sobre la misma grilla y la vista se lee como un 2x2.

     **El piso de una fila, además del techo.** `estilos/_80_cards.py` ya
     clampeaba las tarjetas a una pantalla (`max-height: var(--alto-util)`,
     regla #101). Faltaba lo contrario: que dos tarjetas de la MISMA fila
     midan lo mismo aunque una tenga menos contenido. Medido: Productos
     393px contra Proveedores-del-producto 182px, 211px de escalón, y
     cambiando en cada clic porque el panel derecho es una lista elástica.

     Por qué hace falta CSS y no basta el flexbox de Streamlit — medido
     elemento por elemento: las COLUMNAS sí se estiran solas
     (`stHorizontalBlock` trae `align-items: stretch`, las dos miden 393).
     Lo que no se estira es el **contenedor de elemento** que Streamlit mete
     entre la columna y la tarjeta: nace con `flex: 0 1 auto`. La tarjeta ya
     trae `flex: 1 1 0%`, así que basta con hacer crecer a ese intermedio:

     ```css
     .stColumn > .stVerticalBlock
     > div:has(> div[class*="st-key-compras_prov_card_"]) { flex: 1 1 auto; }
     ```

     `:has()` porque es el único modo de alcanzar al PADRE de la tarjeta. Un
     navegador sin soporte ignora la regla y vuelve al escalón: degrada, no
     rompe. Va dentro del mismo `@media (min-width: 769px)` que el techo —
     en móvil las columnas se apilan y la regla no tendría sentido.

     La guarda: `test_graficos.py::_pruebas_grilla_horizontal`. Verifica que
     ninguna fila de `proveedor.py` vuelva a partirse con un literal, que las
     dos filas usen `COLUMNAS_DRILL`, y que nadie redeclare la constante
     fuera de `_comun.py`. Escape hatch para las subdivisiones DENTRO de una
     tarjeta (el chart y su pila de KPIs, una botonera): un comentario
     `# columnas-internas: <por qué>` en la línea o en las 3 de encima —
     mismo idioma que el `# alto-fijo-justificado:` de la regla del
     presupuesto vertical.

     **PENDIENTE.** La guarda cubre `proveedor.py`, que es donde se arregló.
     El resto de los drills de Compras siguen con literales y entre ellos hay
     cuatro ejes distintos: 1.6/1 (`producto.py` x2, `documentos_sunat.py`),
     1.7/1 (`compras/__init__.py`) y 1/1 (`volatilidad.py`). El esqueleto de
     la página salta al navegar por el rail. Al unificarlos, ampliar
     `_ARCHIVOS` en la guarda a todo `graficos/compras`.

146. **Compras invierte la figura y el fondo: página blanca, tarjetas
     tenues.** El resto de la app usa el reparto normal — lienzo
     `--bg-primary` (#f6f6f8) y tarjetas `--bg-card` (#ffffff) recortadas
     contra él. Compras había invertido sólo la mitad (regla de la "4ta
     vuelta" en `estilos/_50_fecha.py`): toda la página pasó al blanco de
     las tarjetas para que no quedara un rectángulo recortado bajo la
     franja. El resultado era blanco sobre blanco, con la separación
     colgando de un hairline de 1px y nada más.

     Desde 2026-08-21 la inversión está completa: la página se queda
     blanca y el gris pasa a las tarjetas, vía `--bg-card-tenue` en el
     `:root` de `estilos/_00_base.py`. **Es un alias de `--bg-primary`, no
     un hex nuevo** — el contraste entre esos dos tonos ya está probado en
     todos los demás reportes, sólo que al revés. Retocar el tinte de
     Compras = cambiar esa línea, y sólo esa.

     Tres cosas que no son obvias:

     - **La regla va al FINAL de `_80_cards.py`.** Las familias
       (`ajuste_graf_card_`, `compras_prov_card_`, `compras_prod_card_`,
       `sunat_card_`) ya se pintan más arriba en ese mismo módulo con
       `background: var(--bg-card) !important`. Con `!important` en ambos
       lados gana la que aparece DESPUÉS — misma mecánica que el orden de
       `_SECCIONES` (ver CLAUDE.md).
     - **Scopeado por el marker `st-key-app_reporte_compras`.** Las mismas
       familias existen en Inventario, Salidas, Ventas y Requerimientos
       (`ajuste_graf_card_izq_inv`, `..._sal`, ...). Verificado en el
       navegador: Inventario sigue con página #f6f6f8 y tarjetas #ffffff.
     - **Las superficies de DATOS se quedan blancas a propósito**: el
       AgGrid del ranking, el `st.dataframe` de productos y las fichas
       `.pb-card` del panel B. Tabla blanca sobre marco gris es el patrón
       (es lo que hace que la tabla resalte), no un olvido.

     Los KPIs de la tarjeta de evolución no hicieron falta tocarlos y vale
     la pena saber por qué: su fondo es `rgba(113,113,122,.06)`, o sea
     TRANSLÚCIDO. Sobre blanco daban ~#f7f7f8 y sobre el gris dan ~#eeeef0
     — el mismo escalón de 8 puntos en los dos casos. Un fondo opaco
     habría necesitado retoque; uno translúcido sigue al contenedor solo.

     **Consecuencia que apareció al día siguiente: la barra de herramientas
     de elemento.** Streamlit monta al hover un chip sobre cada gráfico,
     tabla o componente. Medido: fondo BLANCO opaco, radio 8px y sombra
     `1px 2px 8px rgba(0,0,0,.08)`. Mientras las tarjetas de Compras también
     eran blancas era blanco sobre blanco y no se notaba; con el tinte pasó
     a leerse como un cuadrado blanco sobre el gris. El tinte no lo creó, lo
     destapó — vale para cualquier chrome opaco que herede el color viejo.

     Se TIÑE, no se esconde:

     ```css
     :root:has(.st-key-app_reporte_compras)
     [data-testid="stElementToolbarButtonContainer"] {
         background: var(--bg-card-tenue) !important;
         box-shadow: none !important;
     }
     ```

     El proyecto ya esconde esa barra en siete contenedores puntuales
     (`grep -rn stElementToolbar estilos/ graficos/`) y extenderlo a todo
     Compras era la opción obvia — hasta CONTAR los botones. En un
     `st.plotly_chart` o en un AgGrid la barra trae sólo Fullscreen, pero en
     un `st.dataframe` trae cuatro: **Show/hide columns, Download as CSV,
     Search y Fullscreen**. En Compras hay cinco `st.dataframe`
     (Proveedor › Productos, Producto › ranking y por familia, Documentos
     SUNAT › líneas del comprobante, Volatilidad › precios), así que
     esconder la barra les sacaba la descarga a CSV para arreglar un
     problema que era de color. Las de AgGrid no dependían de ella: traen su
     propio menú de columna con filtro, orden y export.

     La regla general que deja: **antes de esconder chrome de Streamlit,
     contar qué hay adentro.** Un `display: none` sobre un contenedor
     genérico se lleva puestas funciones que nadie enumeró.

147. **El rail de Compras en formato LISTA (icono + nombre + chevron).**
     A pedido 2026-08-21, tomando como referencia el rail de MSN Dinero. El
     rail era una columna de 84px con etiquetas de 11px; pasa a ser una lista
     de filas de 47px, cada vista con su icono Material, su nombre y un
     chevron, separadas por hairlines.

     **El icono es un parámetro, no un hack.** Streamlit 1.59 acepta
     `st.button(icon=":material/tune:")`, así que no hace falta HTML dentro
     del botón. `_COMPRAS_RAIL_CATEGORIAS` pasó de tuplas `(id, label)` a
     `(id, label, icono)` y `_render_rail` lee el tercer elemento como
     OPCIONAL — el rail es COMPARTIDO con Ajuste (regla #16) y sus tuplas de
     2 siguen funcionando igual. Cuidado con lo que eso implica: cualquier
     código que recorra `items` con `for oid, label in …` revienta con las
     tuplas de 3. Ya pasó al escribirlo: `_todos` se armaba así y hubo que
     cambiarlo a `item[0]`.

     Los nombres de icono se validan contra
     `streamlit.string_util.validate_material_icon`. Si uno no existe,
     Streamlit tira `StreamlitAPIException` **al dibujar el rail**, o sea que
     se cae la pantalla entera, no sólo el icono. Los ocho de hoy están
     verificados uno por uno.

     **El ancho: pisar `--rail-der-full`, nunca `--rail-der-w`.** 84 → 230px.
     `--rail-der-w` es la variable VIGENTE y la reescribe el pestillo al
     plegar (`_25_rails_pestillo.py`); pisándola, el rail se queda ancho y
     plegar deja de funcionar. Pisando la DESPLEGADA, todo lo demás se deriva
     solo. Verificado en el navegador: desplegado da rail 230 / contenido en
     x=299; plegado da `--rail-der-w: 24px`, rail 24 / contenido en x=93, y
     al desplegar vuelve a 230.

     Y la excepción vive en `estilos/_00_base.py`, junto al valor base, no en
     `_20_compras_rail.py` donde está el resto del formato. No es capricho:
     `test_graficos.py` tiene una guarda de que los anchos de rail se
     declaran en un solo sitio (nació de tenerlos en seis que se derivaban
     entre sí) — **y la guarda saltó** cuando se escribió acá por primera
     vez. Funcionó como debía.

     **Dos scopes distintos, a propósito:**
     - El formato va scopeado a `app_reporte_compras`: es una decisión del
       REPORTE. Verificado que Ajuste sigue con su rail de 84px, sin iconos,
       sin chevron y con fuente de 11px.
     - Todo el bloque va dentro de `@media (min-width: 901px)` y al FINAL del
       módulo. La media, para no pisar el bloque móvil (`max-width: 900px`),
       donde el rail deja de ser columna y pasa a ser una tira horizontal de
       chips: ahí ni el chevron ni los hairlines significan nada. El final
       del módulo, para ganarle por orden a las reglas de arriba que estilan
       estos mismos botones.

     Los iconos SÍ aparecen en la tira móvil, porque salen de Python y no del
     CSS. Es deliberado: un chip con icono se lee mejor y la tira scrollea en
     horizontal, así que el ancho extra no rompe nada (medido: sin desborde a
     375px).

     **Lo que NO se puede portar de la referencia:** la fila de puntitos de
     score de cada ítem. En MSN son una calificación (Valoración 3/6, Estado
     4/6); acá los ítems del rail son destinos de navegación, no entidades
     puntuadas. No hay dato que poner ahí sin inventarlo.

148. **Maximizar un AgGrid necesita DOS mitades: soltar el ancho y
     re-repartir las columnas.** El botón ⛶ (`inject_maximize_aggrid`)
     existía desde antes y "funcionaba": la tabla entraba en pantalla
     completa. Pero al ponerlo en Documentos SUNAT (2026-08-21) el usuario
     reportó con captura que no servía de nada — la tabla ocupaba los
     1365px de alto y el grid seguía con el ancho de la tarjeta angosta,
     media pantalla vacía a la derecha y los encabezados igual de cortados
     (`F...`, `D...`, `E...`).

     **Mitad 1 — el CSS forzaba alto y NUNCA ancho.** `_FS_CSS_IFRAME`
     (`inyecciones/_fragmentos.py`) ponía `height: 100vh` en toda la cadena
     `#root > div > .ag-theme-* > .ag-root-wrapper` y ni una regla de
     `width`. No se nota en una tabla que ya ocupa el ancho de la página
     (el caso para el que nació, la pivote de Proveedor); se nota mucho en
     una que vive en media columna. Medido en el navegador: con el iframe
     llevado a 1600px, el `body` del iframe pasaba a 1600 y
     `.ag-root-wrapper` se quedaba clavado en 474 — st_aggrid le fija al
     contenedor un ancho en PÍXELES, medido al montar contra su tarjeta.

     **Mitad 2 — soltar el ancho no mueve las columnas.** Con el
     contenedor ya en 1600px las columnas seguían sumando 457: AG Grid da
     más lienzo pero no re-reparte solo. Hace falta `sizeColumnsToFit()`,
     y el sitio correcto para llamarlo es el evento `gridSizeChanged`, que
     dispara justo al entrar y al salir de pantalla completa. Se declara
     desde Python, no desde el JS de la inyección:

     ```python
     gb.configure_grid_options(
         onGridSizeChanged=JsCode("function(p){ p.api.sizeColumnsToFit(); }"))
     ```

     **Por qué es seguro en el estado angosto**, que es la trampa: la
     tabla del cruce declara a propósito `fit_columns_on_grid_load=False`
     porque son 10 columnas y forzarlas al ancho de la tarjeta las deja
     ilegibles. Un `sizeColumnsToFit()` incondicional rompería justo eso.
     La salida NO es un umbral de píxeles a ojo: es darle `minWidth` a cada
     columna. `sizeColumnsToFit` respeta los mínimos — si no entran, deja
     cada una en su mínimo y scrollea, en vez de aplastar. Así el mismo
     handler sirve para los dos estados sin ninguna condición.

     **Cómo se verificó, porque el entorno no deja probar fullscreen.**
     `requestFullscreen()` no corre en el panel de preview, y el
     `ResizeObserver` de AG Grid tampoco dispara con la pestaña oculta
     (misma familia de límites que las animaciones CSS, regla del
     `getAnimations().finish()`). Se probó por partes, sin simular nada:
     inyectando el `_FS_CSS_IFRAME` REAL del proyecto + la clase
     `fs-activo` (`.ag-root-wrapper` 474 → 1600, o sea la mitad 1 anda), y
     después recuperando el handler VERDADERO del grid con
     `api.getGridOption('onGridSizeChanged')` para invocarlo — columnas de
     457 a 1583px, Proveedor de 190 a 366. La API del grid se alcanza
     caminando el fiber de React desde el div del tema
     (`__reactFiber$…` → `.return` × 2 → `stateNode.api`); `st_aggrid` no
     la expone de otra forma —`__ag_grid_instance` es sólo un id numérico.

     Ese camino (fiber → `stateNode.api` → `getGridOption`) es la forma de
     verificar CUALQUIER handler de AgGrid desde el navegador acá, sin
     depender de que el evento llegue a dispararse solo.

149. **Documentos SUNAT: de dos columnas a APILADO** (2026-08-21, a
     pedido). La tabla vivía en `st.columns([1.6, 1])` con la ficha del
     comprobante al costado — ~474px útiles para 7 columnas, y medido en el
     navegador `fit_columns_on_grid_load` aplastaba Fecha a 36px y
     Situación a 43. Ahora la tabla toma el ancho entero del canvas y la
     ficha pasa DEBAJO, también a lo ancho.

     **El camino descartado importa tanto como el elegido.** Antes de
     apilar se probó resolverlo con el ⛶ de pantalla completa
     (`inject_maximize_aggrid`), que ya existía para la pivote de
     Proveedor. Se descartó a pedido con una razón que no estaba en la
     mesa: *"no deseo una pantalla completa, ya que oculta todo"*. Un modo
     que tapa el resto de la vista no sirve para trabajar comparando — y
     eso no se deduce midiendo píxeles. El botón se retiró de este drill;
     sigue en Proveedor, donde la tabla es el único contenido.

     Lo que SÍ quedó de ese intento, porque son arreglos reales:
     `_FS_CSS_IFRAME` ahora suelta el ancho además del alto (regla #148), y
     las dos tablas declaran `onGridSizeChanged` + `minWidth` por columna.
     Apilada, ese handler ya no sirve para fullscreen sino para los dos
     casos que quedan: plegar el rail y redimensionar la ventana.
     `fit_columns_on_grid_load` sólo actúa una vez, al cargar.

     **La ficha necesitó su propio arreglo, y es el que casi se pasa por
     alto.** Mover un panel de una columna angosta a todo el ancho no es
     gratis: sus filas son `display:flex; justify-content:space-between`,
     así que a 1147px la etiqueta y el valor quedaban separados por medio
     metro de vacío, en una lista vertical larguísima. `_ficha_html` pasó a
     envolver cada GRUPO (`sunat.campos_ficha` ya los devuelve agrupados)
     en su propio bloque, y los bloques van en
     `grid-template-columns: repeat(auto-fit, minmax(260px, 1fr))`. Sin
     número fijo de columnas a propósito: medido, da 3 lado a lado en
     desktop (Emisor · Documento · Importes, 348px cada uno, mismo `top`) y
     1 en móvil a 375px, sin desborde.

     La regla general: **cambiar el ANCHO de un contenedor puede romper el
     contenido aunque el contenido no se toque.** Un `space-between` es
     correcto en 400px y absurdo en 1150px.

150. **Mover un widget de sitio cuando su KEY es el estado: el pill de fecha
     de la franja.** A pedido 2026-08-21, Compras › Documentos SUNAT dibuja
     el selector de fecha DENTRO de su tarjeta: ahi la fecha no es contexto
     global sino EL filtro de la tabla (el rango que se le consulta al SIRE),
     y vivia lejos de lo que filtra.

     **Por que no se puede copiar.** El `st.date_input` del panel usa como
     key la clave canonica del rango (`clave_rango(...)`). O sea el widget no
     es una vista del estado: ES el estado. De ahi que:
       · dos widgets no puedan compartir key, y
       · escribir esa clave desde afuera despues de instanciar el widget tire
         `StreamlitAPIException`.
     "Mover la fecha" solo puede significar mover la LLAMADA. Por eso el
     panel salio de `app.py` a `franja_fecha.py`: para que la misma llamada
     se pueda hacer desde dos sitios, uno por render, nunca los dos.

     **El contexto se PUBLICA, no se pasa por parametro.** El panel necesita
     nueve valores que solo `app.py` conoce (bounds, cortes, corte vigente,
     claves de estado...). Enhebrarlos por la firma del dispatcher hasta el
     drill serian tres capas de parametros que ninguna otra vista usa.
     `app.py` los publica con `franja_fecha.publicar()` y quien dibuje llama
     a `render()` — mismo patron que `publicar_contexto_ia()`.

     **El problema de ORDEN, que es el que costo caro.** La franja se dibuja
     en `app.py` ~600 lineas antes de que el rail exista, asi que cuando
     decide su layout no sabe que vista esta activa. Se resolvio con
     `graficos.base.vista_activa()`, que aplica el MISMO criterio que
     `_render_rail` (y es llamada por el, para que no haya dos copias):
     lo guardado si sigue siendo valido, si no el `?vista=` normalizado, si
     no el primer item. Leer `session_state` a secas NO alcanza: en la
     primera carga de un deep-link la clave todavia no existe.

     **Y el problema de FRAGMENTO, que es peor y no se ve venir.**
     `_render_contenido` es un `@st.fragment`. Un clic en el rail rerunea
     SOLO el fragmento: `app.py` no se vuelve a ejecutar, asi que la franja
     se queda con la decision de la vista ANTERIOR. Medido en el navegador,
     los dos sintomas:
       · entrando a SUNAT  -> dos pills a la vez (uno `fixed` en la franja,
         otro `static` en la tarjeta), porque la franja ya lo habia dibujado
         en el ultimo render completo y su DOM sobrevive al rerun parcial;
       · saliendo de SUNAT -> NINGUN pill, porque la franja no lo dibujo y
         el drill que se lo quedaba ya no esta.
     La reconciliacion vive en `renderizar_graficos_compras`: `app.py` deja
     en `_franja_dibujo_fecha` quien lo dibujo, y si no coincide con lo que
     la vista activa quiere, se fuerza `st.rerun(scope="app")`. Cuesta un
     render extra al cruzar esa frontera y nada el resto del tiempo.

     **La regla que deja, y vale para cualquier control de la franja:**
     antes de mover algo de la franja a un dashboard, mirar DOS cosas — si
     su key es el estado (no se puede duplicar) y si quien decide corre
     dentro de un fragmento (la franja se entera un render tarde).

     El CSS tambien hay que devolverlo al flujo: el pill arrastra el
     `position: fixed` + coordenadas que le ponen `_40_ajuste_franja.py` y
     `_50_fecha.py`, asi que dentro de la tarjeta se neutraliza con
     `position: static` scopeado a `sunat_card_izq` (`estilos/_30_filtros.py`)
     — la misma key sigue anclada a la franja en todos los demas reportes.


151. **Modo diseño fase C — insertar elementos de mentira ("mocks") para
     ver cómo se vería algo que todavía no existe** (2026-08-21). El modo
     diseño sabía editar lo que YA estaba en pantalla; no había forma de
     preguntarse "¿y si acá hubiera un título, una línea, una franja?"
     sin escribir Python, pushear y esperar el deploy.
     - **El truco que lo hace barato: el mock nace con la clase
       `st-key-<key>`.** `elementoPineado()` resuelve por
       `.st-key-<key>` y el inspector saca la key del `className` con el
       mismo regex (`/st-key-([A-Za-z0-9_]+)/`), así que un `<div>`
       inyectado a mano se fija con clic derecho igual que un widget real
       y hereda TODO el panel — tipografía, color, borde, sombra, mover,
       resize — sin una línea de código extra. No hubo que tocar
       `inspector.py` ni duplicar controles: la key ES la interfaz.
     - **Cuatro tipos** (`TIPOS_MOCK`): Texto (`contenteditable`, se
       escribe en el lugar — el atajo `C` del inspector ya ignora
       `isContentEditable`, así que tipear no dispara "copiar para IA"),
       Línea, Barra y Espacio. El Espacio se marca con `outline` y no con
       `border`: `border` ocupa layout y falsearía el alto que se está
       probando. Los colores salen de `PALETA` por NOMBRE
       (`colorPaleta('Acento')`), no por índice ni por hex suelto.
     - **Anclaje relativo al pineado** (`antes` / `dentro` / `después`):
       sin elemento fijado no hay dónde insertar, y el panel de espera lo
       dice. Un mock puede anclarse a otro mock, así se apilan.
     - **Sobreviven al rerun igual que los estilos inline, pero por otra
       vía:** los cambios de estilo aguantan porque Streamlit reconcilia
       por key y el nodo no se toca; un mock, en cambio, NO existe para
       React y desaparece en cuanto Streamlit re-renderiza esa rama. Por
       eso `sync()` llama a `reponerMocks()` ANTES de resolver el pin (un
       mock puede SER el pineado): si el nodo no está, se re-inserta desde
       el registro y se le reaplican `cambios` + `transformState`. El
       texto tipeado vive en el registro (se guarda en el evento `input`),
       nunca se reescribe en cada tick — hacerlo mataría el cursor.
     - **Nunca persiste.** Un mock no es un widget: no está en el código
       ni en `estilos/`, y muere al recargar. El panel lo dice con un
       aviso arriba de los controles cuando el pineado es uno, para que
       nadie lo busque después en el repo.

152. **En una herramienta para PROBAR, el 0 de un slider es un valor, no un
     "sin cambio"** (2026-08-21, del pedido "¿puedo ver las puntas en
     ángulo en vez de redondeadas?"). Los cuatro sliders de caja del modo
     diseño (radio, padding, borde, sombra) mandaban `null` en su mínimo, y
     `null` en `establecerCambioEstilo()` significa *sacar el override y
     volver a lo que dice `estilos/`*. O sea: arrastrar "Radio de borde" a
     0 sobre el rail RESTAURABA sus 12px en vez de cuadrar las esquinas. El
     síntoma es el peor de todos, "el control no hace nada", y encima
     justo en el caso que más se quiere previsualizar: quitar. Lo mismo
     pasaba con borde 0 (volvía el hairline del CSS) y sombra 0.
     **Arreglo:** 0 se aplica como valor real — `0px` para radio/padding/
     letter-spacing y `none` para borde/sombra. Volver al original no se
     perdió: es exactamente lo que hace el botón "Ver original", que
     restaura `cssTextOriginal` y sigue funcionando como A/B.
     **Regla general:** un centinela que se solapa con un valor legítimo
     del rango se rompe siempre en el extremo del rango; si hace falta
     distinguir "sin cambio" de "cero", el estado va aparte del valor
     (acá, `registro.cambios[prop]` existe o no), nunca dentro.

153. **Fase D del modo diseño: paleta de superficie, revertir por
     propiedad, y "Copiar CSS" para cerrar el circuito** (2026-08-21, del
     pedido "¿qué mejoras le harías al panel?"). Cuatro cambios chicos que
     comparten un mismo hilo — el panel sabía PREVISUALIZAR pero se quedaba
     corto en tres puntos concretos.
     - **La paleta era solo de DATO** (acento, semáforo, ajuste ±): once
       colores, ninguno de superficie. Probar "¿este gris de tarjeta o el
       lienzo?" —el pedido que motivó la sesión— era literalmente
       imposible: ese gris no estaba en la lista. Se sumaron
       `GRIS_FONDO`/`GRIS_BORDE`/`GRIS_LINEA`/`GRIS_TEXTO_SUAVE`/
       `LAVANDA_FONDO` de `tema.py`, más un swatch "Transparente"
       (checkerboard, manda el valor CSS `transparent`) para Fondo y un
       `<input type=color>` libre para Texto y Fondo — antes solo lo tenía
       Borde completo.
     - **Deshacer era todo o nada.** "Ver original" apaga los N cambios
       juntos; arrepentirse de uno solo obligaba a rehacer el resto. Cada
       fila con valor editable ahora tiene un botón "↺" que llama a
       `establecerCambioEstilo` con el tercer argumento en `null` SOLO para
       esa propiedad (mismo `null` que la regla #152 le sacó a los sliders
       de su mínimo — acá no hay overload porque es una acción explícita,
       no un valor del rango) y reconstruye el panel. Los compuestos (Borde
       completo, Sombra) también resetean su variable de estado
       (`bordeAncho`/`sombraNivel`) para que el slider vuelva a cero y no
       quede leyendo un número sin efecto.
     - **Margen**, hermano de Padding con el mismo tratamiento (mismo
       rango, mismo revert) — pedido explícito: "un poco más de aire
       arriba" era el ajuste más común y no había forma de probarlo.
     - **"Copiar CSS" — la que cambia el flujo.** Hasta acá el panel
       sabía mostrar pero no sabía entregar: bajar los cambios a
       `estilos/` era leerlos a ojo del panel y dictarlos. `registro.cambios`
       ya tenía todo lo necesario; `construirBloqueCSS()` solo lo junta:
       separa geometría (siempre va a `div[class*="st-key-<key>"]`) de
       estilo (puede ir redirigido, mismo criterio que `destinosDeEstilo` —
       si redirige, arma DOS bloques con selectores distintos) y formatea
       cada propiedad cambiada como declaración CSS.
       **El fallback de "Ctrl+C" mentía** en el primer intento: a
       diferencia del inspector (que ya tiene un `<pre>` visible para
       seleccionar cuando el Clipboard API y `execCommand` fallan los dos
       — caso real en Streamlit Cloud, iframe anidado, regla #39), el botón
       nuevo no mostraba el CSS en ningún lado — decía "seleccionado:
       Ctrl+C" sin haber nada seleccionado. Se agregó un `<textarea>` en el
       panel que aparece y se autoselecciona SOLO cuando el copiado
       automático falla.
     - **El bug que costó más diagnosticar: una secuencia de escape sin
       doblar rompe TODO el script, no solo la línea.** Al construir el
       bloque de texto con saltos de línea reales usé, en el fuente Python
       de `_diseno_js.py`, un solo backslash antes de la ene donde hacían
       falta dos. Ese archivo es un string Python NO-raw (lo dice el propio
       docstring: "NO CONVERTIR A RAW STRING"), así que Python colapsó cada
       una de esas secuencias a un byte de salto de línea real ANTES de que
       el JS la viera — y un salto de línea crudo metido dentro de una
       cadena JS de comillas simples es `SyntaxError: Invalid or unexpected
       token`. Como es un IIFE completo, el error mata el `<script>`
       ENTERO: nada de diseño (overlay, panel, pin) se ejecuta, sin dejar
       pista de cuál línea — el pin seguía funcionando (lo pone
       `inspector.py`, OTRO script) así que el síntoma parecía "el panel no
       aparece" y no "hay un error de sintaxis". Mismo patrón ya vivido en
       esta misma sesión con el texto de `panelEspera()` — la lección no
       prendió a la primera, y hasta esta propia regla se rompió así una
       vez al redactarla (un heredoc de bash volvió a colapsar la secuencia
       antes de llegar al archivo). **Diagnóstico que sirvió:** un
       tokenizer chico en Python que recorre el JS ya parseado carácter por
       carácter, trackeando si al final de cada línea seguís "dentro" de
       una comilla simple/doble sin cerrar — eso apunta la línea exacta sin
       ejecutar nada en el navegador. **Regla:** en `_diseno_js.py`/
       `_inspector_js.py`, cualquier salto de línea intencional dentro de
       un string JS necesita DOS backslashes en el fuente Python (uno
       colapsa a uno solo, que es lo que JS necesita ver) — y al escribir
       el fix con una herramienta de texto (heredoc, editor), verificar el
       archivo YA ESCRITO, nunca el texto fuente que se cree haber tipeado.

154. **`destinosDeEstilo` necesitaba DOS niveles de redirección, no uno —
     y el guard de cantidad de la regla #48 tenía un falso positivo con
     `st.button(help=...)`** (2026-08-21, del pedido "¿por qué el tamaño de
     letra no aumenta?" sobre `navbtn_Compras`, un botón del nav-rail).
     - **Falso positivo del guard de cantidad:** `st.button(..., help=grupo)`
       renderiza un SEGUNDO `<button>` con el mismo testid y texto, de
       0×0px — un fantasma de medición/accesibilidad de Streamlit, no un
       botón real. El guard de la regla #48 (`candidatos.length > 1` →
       "es una lista, no redirijas") lo contaba igual que un botón real:
       "1 real + 1 fantasma" pasaba como 2 y el guard, pensado para el
       rail (12 botones reales apilados), bloqueaba la redirección
       también acá — el font-size se aplicaba al DIV contenedor
       (`st-key-navbtn_Compras`) en vez de al `<button>`, sin efecto
       visible. **Arreglo:** filtrar candidatos con `getBoundingClientRect()`
       de 0×0 ANTES de contar — no son botones "de mentira" a propósito
       como el fantasma, son simplemente invisibles y no deben pesar en
       la cuenta.
     - **El segundo nivel, más de fondo:** aun con la redirección al
       `<button>` corregida, cambiar el tamaño de letra seguía sin efecto
       visible. Causa: `navegacion.py` envuelve el label de los botones
       del nav-rail en `[data-testid="stMarkdownContainer"] p` y le fija
       SU PROPIO `font-size`/`font-weight` con `!important`
       (`.st-key-nav_rail [class*="st-key-navbtn_"] button p`) — un
       elemento con su propio valor explícito no hereda el del padre, así
       que aplicar `font-size` al `<button>` nunca iba a mover un píxel
       el texto que realmente se ve. **Arreglo:** `PROPS_TEXTO` (font-size,
       font-weight, text-align, text-decoration, letter-spacing, color) se
       separó de las demás props de "estilo" (border-radius, padding,
       margin, border, box-shadow — el "chrome" del botón, deliberadamente
       NO extendido: ponerlas también en el `<p>` duplicaría bordes/relleno
       visualmente). `extenderATexto(destinos)` agrega, para cada destino
       que tenga un `[data-testid="stMarkdownContainer"] p` adentro, ESE
       `<p>` como destino ADICIONAL (no en reemplazo) solo para
       `PROPS_TEXTO` — en `establecerCambioEstilo`, en el reaplicado
       defensivo de `aplicarEstado`, y en la LECTURA inicial de los
       sliders (`lecturaTexto`, así "Tamaño de letra" arranca mostrando el
       13.5px real del `<p>` y no el 16px default del `<button>`) y en
       `construirBloqueCSS` (el bloque copiado usa el selector del `<p>`
       para esas props, no el del botón — si no, pegarlo en `estilos/` se
       vería "no hace nada", el mismo bug otra vez pero esta vez en el
       código que el usuario pega).
     - **El patrón general que deja:** "redirigir del wrapper al botón" no
       es necesariamente el fondo del pozo — un widget puede anidar un
       nivel MÁS que carga su propio override explícito de una propiedad
       puntual. La señal es la misma que en la regla #48: un control que
       no tiene efecto visible pese al inline `!important` confirmado
       presente. El panel ahora lo dice con una segunda línea de aviso
       ("Tipografía/color de texto → el `<p>` del label...") cuando
       `lecturaTexto !== lectura`, para no depender de que alguien vuelva
       a diagnosticarlo a mano.

155. **Navegar la jerarquía de contenedores era de solo lectura — texto
     plano para copiar, sin forma de SALTAR** (2026-08-21, del pedido de
     entender 5 capturas de tooltip anidadas del drill de Proveedor:
     "¿qué relación tienen, cómo los veo de forma más amplia?"). Tres
     agregados, ninguno toca `estilos/`:
     - **Migas de pan clicables en el inspector**
       (`inyecciones/_inspector_js.py`): la línea "Cadena de contenedores
       st-key (elemento -> raíz)" ya vivía en `bloqueParaIA()` como texto
       — para saltar a un ancestro había que ubicarlo A OJO en la
       pantalla y clic-derecho ahí. `pintarMigas(keysCad)` reusa la MISMA
       lista como una fila de `<button>` reales, insertada en un
       `<div id="el-inspector-migas">` nuevo entre el btnrow y el
       `<pre>`. `saltarAAncestro(key)` resuelve `.st-key-<key>`, arma un
       objeto plano `{target, clientX, clientY}` (no un `MouseEvent` de
       verdad — el handler solo lee esas tres props, ver el propio
       mousemove handler) y lo pasa DIRECTO a
       `win.__inspectorMouseMoveHandler`, el mismo truco liviano que
       `__inspectorContextMenuHandler` ya usaba para "recalcular en la
       posición actual" sin simular un evento real de DOM. Soltar-antes-
       de-saltar y re-fijar-después es necesario: el handler tiene
       `if (win.__inspectorPinned) return;` al principio (fijado =
       congelado a propósito), y sin re-fijar al final el próximo
       mousemove real (el cursor sigue en su posición vieja) pisaría el
       salto al instante.
     - **Árbol vertical en el modo diseño**
       (`inyecciones/_diseno_js.py`): mismo mecanismo, complementario en
       vez de redundante — la miga del inspector es horizontal y lee
       elemento→raíz; el árbol de diseño es vertical, indentado por
       profundidad, y lee RAÍZ→elemento (mismo orden en que aparece en el
       código). `cadenaKeysDiseno()` duplica A PROPÓSITO
       `cadenaKeys()`/`keyDeElemento()` del inspector — mismo criterio
       que `copiarTextoDiseno()` con `copiarTexto()` (arquitectura.md
       docstring de `diseno.py`): son dos realms/iframes distintos y
       "ninguna función depende de otra" es la regla del paquete. Saltar
       (`saltarADiseno`) pasa por las MISMAS funciones que expone el
       inspector en `win` — el modo diseño no tiene su propio pin, lee
       `win.__inspectorPinned`/`__inspectorUltimo` de solo lectura (regla
       #46), y esto extiende esa lectura a también invocar
       `__inspectorMouseMoveHandler`/`__inspectorTogglePin`, ya
       establecido como categoría de acoplamiento por el botón "Soltar"
       (que ya llamaba `__inspectorTogglePin` antes de este agregado).
     - **Diagrama de UN caso concreto, no una herramienta**: para "ver de
       manera más amplia" la cadena completa `compras_prov_drill_wrap` →
       `compras_prov_marco` → `cp_chart_wrap` → `compras_prov_card_ranking`
       → `compras_prov_rank_grid`, un artifact aparte (fuera del repo)
       documentó esa jerarquía puntual con su archivo:línea, su CSS y el
       aviso de familia wildcard — sirve como referencia externa, no
       reemplaza al inspector.
     - **Lo que quedó afuera a propósito:** el árbol de diseño NO marca
       qué ancestros están bajo una regla wildcard-por-familia (lo que sí
       hace el tooltip del inspector, `AVISO - ... reglas WILDCARD`) — esa
       lectura requiere `selectoresCompartidos()`, una función de solo
       inspector.py, cara (recorre TODAS las hojas de estilo) y no
       expuesta en `win`. Si hace falta ese aviso en el árbol de diseño,
       exponerla ahí es el próximo paso, no reimplicarla.

156. **Un `transform` en un ancestro CAPTURA a sus hijos `position: fixed`
     — y por eso mover/redimensionar con el modo diseño NO es una vista
     previa fiel** (2026-08-22, de la pregunta "achiqué la franja, ¿qué
     efecto tiene?"). Es comportamiento estándar de CSS, pero muerde
     fuerte acá porque este proyecto usa `position: fixed` a propósito y
     en cantidad — los "títulos fantasma" y los controles que suben a la
     franja (regla #120) — y el modo diseño mueve con `transform`.

     Un elemento con `transform` deja de ser transparente para el
     posicionamiento: pasa a ser el bloque contenedor de todo descendiente
     `fixed`, que abandona el viewport y se ancla a él. Medido en vivo
     sobre `fila_ajuste_top` (viewport 1912, app real, sin modo diseño vs
     con `translate(574px,46px)` aplicado a mano):

     | | sin transform | con transform |
     |---|---|---|
     | `::before` (la banda blanca) | 981px de ancho, left 299 | 592px, left 1172 |
     | `fecha_ajuste_pill` | left 299 | left 1172 |

     El pill saltó 873px sin que nadie tocara SU CSS: sólo cambió quién
     era su marco de referencia. Y la banda se recalcula contra la caja
     del ancestro, así que **achicar el contenedor colapsa la banda** —
     con `left: 299` y `right: 0` contra una caja de 236px el ancho da
     negativo y se clampea a 0, o sea la franja blanca desaparece. La
     aritmética cierra exacta: `width = ancho_caja - 299`,
     `bottom = alto_caja - 40 - 46`.

     Consecuencia práctica: **al mover o redimensionar un contenedor que
     tenga hijos `fixed`, se ven DOS cambios mezclados** — el pedido y el
     colateral de que sus hijos flotantes dejaron de ser libres. Para
     elementos sin hijos `fixed` la previsualización sí es fiel. Es la
     contracara de la regla #48 ("nada de esto persiste"): además de
     efímero, en este caso puntual es *distinto* de lo que produciría el
     mismo CSS escrito a mano.

     De acá salió **`herramientas/rayos_x.js`**, el cuarto auditor (con
     `auditar_layout.js`, `auditar_graficos.js` y `ver_figura.py`). Los
     otros tres miden y reportan en texto, y el inspector marca UN
     elemento por vez; ninguno respondía "¿qué caja es cada cosa de las
     que veo?". `rayosX()` pinta la estructura en una capa aparte
     (`pointer-events:none`, no toca la página) y distingue las tres
     cosas que a simple vista son indistinguibles: cajas EN EL FLUJO
     (línea llena, color por nivel de anidado), ESCAPADOS (`fixed`/
     `absolute`, línea cortada, con una línea trazada hasta el padre al
     que pertenecen en el CÓDIGO) y PSEUDO-ELEMENTOS (línea de puntos —
     los que pintan bandas que uno busca en el árbol y no encuentra
     porque no están en el HTML). Calcula las cajas de los escapados
     contra su ancestro transformado si lo hay, justamente por esta
     regla: sin eso, con el modo diseño abierto los recuadros salen
     corridos. Medido en Compras > Proveedor: 35 cajas en el flujo, 8
     escapados, 1 pseudo.

157. **El modo diseño sólo sabía agarrar elementos con `st-key-*`, y la
     mitad de lo que uno quiere mover no tiene key** (2026-08-22, del
     pedido "¿por qué esto no puedo moverlo con mi herramienta de
     diseño?" sobre el título "Ranking de proveedores" del drill de
     Proveedor).
     - **El síntoma:** clic derecho sobre `<div class="cp-rank-tit">`
       (`graficos/compras/proveedor.py:396`, un `st.markdown` con HTML) y
       arrastrar la manija "Mover" corría los 929×388 px de la TARJETA
       entera (`compras_prov_card_ranking`). El título no se movía ni un
       píxel DENTRO de ella. No se lee como un bug del pin: se lee como
       "la herramienta no puede mover esto".
     - **La causa:** `elementoPineado()` resolvía SIEMPRE
       `doc.querySelector('.st-key-' + key)`, y la key viene del
       inspector, que ancla al contenedor con `st-key-*` más cercano
       (`contenedorConKey`, `_inspector_js.py`). Un nodo sin key propia
       nunca era direccionable: el pin subía al ancestro y todos los
       controles —geometría, transform, estilo— iban a parar ahí. El
       volcado del tooltip ya lo delataba y nadie lo leía así:
       `Tamaño actual: 929 x 388 px` y `padding=16px 18px` son la
       tarjeta, no un título de 18px de alto.
     - **El arreglo — sub-pin.** `win.__disenoState.sub` guarda
       `{key, clase}`: la CLASE del hijo, nunca el nodo (un rerun lo
       recrea igual que al widget con key, y la regla de este módulo es
       re-resolver siempre). `elementoPineado()` devuelve ahora
       `{key, sub, id, el}`, donde `id = 'key .clase'` — y **el `id`, no
       la key, es el índice de `win.__disenoState.porKey`**: la tarjeta y
       cada hijo pineable llevan su propio juego de cambios y no se
       pisan. El sub muere solo cuando el pin salta a otra key (si no, su
       clase podría existir allá adentro y bajar a un hijo distinto sin
       aviso), y si el hijo no está en este render se cae a
       `panelPerdido` en vez de volver al contenedor — aplicar los
       cambios del hijo a la tarjeta entera sería peor que no aplicar
       nada.
     - **Cómo se llega:** el árbol de jerarquía de la regla #155 suma
       hojas — los hijos con clase **de autor** del widget pineado, en
       azul y prefijadas con `.` para distinguirlas de las keys. Clic
       para bajar; clic en la fila de la key (que con un sub activo deja
       de ser "la actual" y vuelve a ser clicable) para subir.
     - **Qué es una clase "de autor" y por qué importa:** las que escribe
       ESTE proyecto (`cp-rank-tit`, `cp-evo-kpis`) sirven como selector
       para pegar en `estilos/`; las de Streamlit no. Se filtran cuatro
       familias: `st-*` (incluye `st-key-*` y `st-emotion-cache-*`),
       `st[A-Z]` (`stMarkdown`, `stVerticalBlock`), `ag-*` (internos de
       AgGrid, que se estilan por su `custom_css`) y —la menos obvia, que
       apareció recién al probarlo en vivo— la clase *target* que
       `@emotion/babel-plugin` le pone a cada componente **sin prefijo
       alguno**: `e1rw0b1u1`, `eqmt79k2`, `etxdrby0`. Sin ese corte se
       colaban tres de ésas ANTES de `.cp-rank-tit` en el árbol, y
       cambian con cada build de Streamlit. También se saltan los nodos
       SVG (un Plotly sin key propia inunda la lista con
       `main-svg`/`trace`/`point`) y todo lo que viva dentro de otro
       `st-key-` más adentro: eso es otro widget y se pinea por su key.
     - **Los dos acoplamientos que había que seguir hasta el final**, o
       el sub-pin quedaba a medias: `construirBloqueCSS` emite
       `div[class*="st-key-K"] .cp-rank-tit` (si no, pegar el bloque
       movería la tarjeta — el mismo "pegarlo no hace lo que probé" de la
       regla #154, esta vez en el código que el usuario copia), y los
       mocks de la regla #151 guardan `anclaSub`: insertar "antes" de un
       título y "antes" de la tarjeta que lo contiene son dos lugares
       distintos.
     - **Verificado en vivo** (no sólo por lectura): con el sub activo,
       arrastrar "Mover" 40×25 px dejó
       `transform: translate(40px, 25px)` en el `.cp-rank-tit` y el
       `style.transform` de la tarjeta VACÍO, y el bloque copiado salió
       anclado al hijo.

158. **Las cinco herramientas de diagnóstico vivían en tres URLs y dos
     scripts que había que pegar a mano — ahora hay UNA barra**
     (2026-08-22, del pedido "me gustaría verlas todas en la misma
     visualización, con la opción de cambiar de modo"). El síntoma que lo
     disparó: `rayos_x.js` se creó ese mismo día y la primera pregunta
     fue "¿dónde la veo?" — no había dónde, había que abrir DevTools.

     `inyecciones/herramientas.py` + `_herramientas_js.py`. Se activa con
     `?debug=1`, el flag que ya existía: no hay uno nuevo que recordar.
     Cinco botones — Inspector, Diseño, Rayos X, Layout, Gráficos.

     - **Cada modo es un query param**, no una variable en memoria
       (`?diseno=1`, `?rayosx=1`). Así la combinación queda compartible y
       marcable, sobrevive el rerun de Streamlit sin estado extra, y es el
       mismo idiom que el Alt+I del inspector ya usaba. Salir con Alt+I
       CONSERVA `?rayosx=1`: al volver a entrar, los modos se restauran.
     - **Los modos son combinables a propósito.** Rayos X + Inspector es
       justo la combinación útil (estructura pintada + detalle al hover).
       Cuando dos se estorban se AVISA en la barra en vez de bloquearlos:
       hoy el único par es Diseño + Rayos X (regla #156).
     - **UNA SOLA FUENTE para los auditores.** Este módulo no
       reimplementa nada: LEE los ficheros de `herramientas/*.js` y los
       embebe. Siguen siendo pegables en consola — dos formas de correr el
       mismo código, sin dos copias que se desincronicen (riesgo real:
       `auditar_layout.js` ya cambió cuatro veces). Se ejecutan inyectando
       un `<script>` en el documento del PADRE y no en el iframe de
       `components.html`: están escritos para la consola y usan
       `document`/`window` directo, así que corriéndolos en el iframe
       medirían un DOM vacío. Efecto lateral bueno: quedan definidos en
       `win`, o sea llamables a mano desde la consola sin pegar nada.
     - **El botón Inspector NO toca `?debug=1`** — ese flag es el que hace
       visible a la barra, apagarlo la mataría a ella también. Alterna el
       silenciador que `inspector.py` ya exponía
       (`__inspectorTooltipSilenciado` / `__inspectorAlternarSilenciado`),
       segunda dependencia de solo lectura hacia ese módulo después de la
       del modo diseño (#46).
     - **Espacio compartido, y la trampa que dejó** (Regla viva #4): la
       barra ocupa `bottom:10px; left:72px`, que era del badge
       "Inspector ON". Se probó primero subir el badge a una constante
       (`bottom:46px`) y **se superponían igual**: la barra mide 36px, no
       28, y encima CRECE cuando muestra el aviso de conflicto. La versión
       que quedó lo mide y escribe `badge.style.bottom` en cada repintado
       — verificado: barra 36→38px mueve el badge 54→56px y el hueco se
       mantiene en 8px. Moraleja repetida de la regla #145: dos números
       coordinados a mano en ficheros distintos se desincronizan; si uno
       depende del otro, que lo lea.

     Verificado en vivo (Compras > Proveedor, viewport 1912): la barra
     monta sus 5 botones, las 3 fuentes se cargan en el realm del padre,
     Rayos X pinta 71 recuadros, el panel de Layout arma 3 tablas / 75
     filas, y Alt+I limpia barra + panel + capa de una. El auditor de
     gráficos encontró de paso un solape real que nadie había reportado:
     `CP_EVO_MES_VIBEJ-COLIBRI-SAC` pisa "may 26" con "ago 26" por 4px.

159. **Cuadrados negros en vez de iconos en Chrome < 120: AG Grid 34 emite
     `mask-image` sin la variante `-webkit-`** (2026-08-22). La Theming API
     de AG Grid 34 dibuja TODOS sus iconos igual: un cuadrado de
     `background-color: currentcolor` del tamaño del icono, recortado con
     `mask-image: url("data:image/svg+xml,...")`. En el bundle de
     `st_aggrid` hay **192 `mask-image` y CERO `-webkit-mask-image`** (sí
     está `-webkit-mask-size`, que solo no alcanza).

     Chrome y Edge entienden `mask-image` sin prefijo recién desde la 120
     (diciembre 2023). En una versión anterior el navegador DESCARTA la
     declaración, el recorte nunca se aplica y queda el cuadrado entero
     pintado: un **rectángulo negro** en cada chevron de grupo, cada icono
     de cabecera y cada botón del sidebar. Windows 7/8.1 se quedaron en
     Chrome 109, así que "que actualicen el navegador" no siempre es una
     opción.

     `tablas/_config.py::_parchar_iconos` **no trae los SVG de vuelta**:
     copia las reglas que el propio tema ya puso en su `<style>` y las
     reemite con el prefijo. Por eso no envejece si `st_aggrid` sube de
     versión — no conoce ningún icono concreto, sólo reescribe la
     propiedad. En un navegador moderno no hace absolutamente nada:
     `CSS.supports('mask-image','none')` corta en la primera línea.

     **Se engancha al primer hook LIBRE, no a uno fijo**, porque cada
     renderizador ya usa los suyos: `desktop.py` ocupa `onGridReady` Y
     `onFirstDataRendered`, `compras.py` sólo el segundo y
     `ajuste_pivote.py` sólo el primero. Los tres disparan después de que
     el tema inyectó su `<style>`, que es lo único que el parche necesita.
     Si algún día los tres de `_HOOKS_PARCHE` están ocupados, **lanza
     `RuntimeError` en vez de fallar en silencio** — un parche que no se
     engancha se vería como "los cuadrados negros volvieron", sin pista.

     Va después de `gb.build()` y no antes: así ve los handlers que el
     renderizador realmente declaró. Los cinco renderizadores de `tablas/`
     lo llaman (`desktop`, `movil`, `compras`, `compras_volatilidad`,
     `ajuste_pivote`) — si se agrega una grilla nueva, va también.

     **Ojo con la referencia cruzada:** el código citaba "regla #150" en
     seis lugares, pero la #150 es la del pill de fecha de Documentos
     SUNAT. Se corrigió a ésta al documentarla.

161. **Un número de píxeles escrito en un comentario no se entera de que el
     layout cambió: el eje X de la evolución de Proveedor pedía 5 etiquetas
     donde entran 4** (2026-08-22, encontrado por `auditarGraficos()` desde
     la barra nueva — nadie lo había reportado a ojo).

     El código decía:

     ```python
     _paso_evo = max(1, -(-len(_evo_x) // 6))     # "nunca más de ~6"
     ```

     y el comentario de arriba, *"con 12 períodos en **~380px** las
     '2026-08' se pisan"*. Pero esa figura **mide 206px**: el 2026-08-19 su
     columna se partió en `[2.6, 1]` para poner los KPIs al costado (ver el
     comentario de ese cambio, que documenta la partición pero no revisó el
     divisor que dependía del ancho viejo). El `6` quedó calibrado contra un
     gráfico que ya no existía.

     Medido en el navegador: 5 etiquetas de 41-45px en 206px → las **cuatro**
     parejas pisándose entre -1 y -5px. El auditor sólo marcó UNA porque su
     umbral es 3px: **una herramienta con umbral no dice "está bien", dice
     "no pasó el umbral"** — al ir a mirar el caso reportado aparecieron los
     otros tres.

     **La corrección de fondo no fue el número sino la duplicación.** Había
     TRES implementaciones del mismo cálculo:
     - `ventas_horario.py::_paso_etiquetas` — la buena (deriva del ancho)
     - `ventas_comparativo.py::MAX_ETIQUETAS` — un tope fijo de 14
     - `compras/proveedor.py` — el `// 6` suelto, sin ancho ninguno

     La buena vivía PRIVADA en un dashboard de Ventas, así que un drill de
     Compras no podía usarla sin un import cruzado feo. Se movió a
     `graficos/base.py::paso_etiquetas` (gemela horizontal de
     `alturas.por_filas`: ahí el alto sale de los px por fila, acá la
     densidad de etiquetas sale de los px por etiqueta).

     **Y al moverla apareció que la fórmula buena tampoco era correcta.**
     Calculaba `ceil(total * px_etiqueta / ancho)`, que redondea DOS veces
     —una ahí y otra en el `ceil(total / paso)` implícito al filtrar— y el
     sobrante se va siempre para el lado de dibujar etiquetas de MÁS. A
     770px el error queda diluido y por eso nunca se vio; a 206px daba 5
     donde entran 4.4. La forma correcta es contar primero **cuántas
     entran** (`ancho // px_etiqueta`) y recién después cada cuántas saltar.

     No era sólo teórico: con la fórmula vieja, `ventas_horario` a 70
     columnas pedía 24 etiquetas × 33px = **792px en 770** — el mismo bug
     esperando a ~2,3 meses de datos. La nueva da 18 (594px). Verificado que
     los tres casos reales de ese módulo (13, 31 y 124 columnas) devuelven
     el paso idéntico al anterior: se arregla un latente sin mover lo que
     ya andaba.

     **`ancho` es obligatorio a propósito.** Era un default de módulo
     (`_ANCHO_UTIL = 770`) y por eso nadie notó que Proveedor había pasado a
     206. Que cada llamador tenga que escribir su ancho lo obliga a mirarlo.
     El de Proveedor va como `_ANCHO_EVO = 206` con su medición al lado, y
     no sale de una cuenta porque su columna cuelga de dos repartos anidados
     (`COLUMNAS_DRILL` y el `[2.6, 1]` interno) sobre un ancho que Python no
     conoce.

     Resultado medido: 4 etiquetas, huecos +12/+13/+11px, cero solapes, y la
     fuente de 13px intacta (bajarla a 11 también resolvía, pero deshacía la
     decisión de que sea el único texto legible sin hover).

163. **`arquitectura.md` creció hasta ser un documento que nadie podía
     abrir: 115k tokens, y `CLAUDE.md` mandaba "ante la duda, ábrelo"**
     (2026-08-22). No es teoría: en UNA sesión, tres pares de reglas
     terminaron con el mismo número (#33, #143, #157) y un parche citó la
     #150 —que es de otro tema— porque verificar la cita costaba recorrer
     7.200 renglones. Una instrucción que no se puede cumplir se incumple en
     silencio.

     **Qué NO se hizo: segmentar por temas.** Se midió antes de decidir, y
     los tres números iban en contra:
     - 143 referencias cruzadas entre reglas; el 50% cita a otra. Repartirlas
       parte un grafo conectado.
     - El 19% de las reglas cae en más de un tema y muchas en ninguno limpio
       (una regla sobre el CSS de un widget de Streamlit dentro de un AgGrid
       ¿dónde vive?). Casi la mitad del corpus habría necesitado un hogar
       arbitrario.
     - 166 citas `arquitectura.md #NNN` en el código, y `#161` dejaría de
       decir en qué fichero está la regla.

     **Qué sí: partir por la costura real, que era MAPA contra BITÁCORA.** Ya
     eran dos documentos pegados con vidas distintas — el mapa describe el
     estado ACTUAL y se corrige; la bitácora es historia append-only y se
     agrega. La asimetría hizo la decisión: extraer el mapa costó **1**
     referencia, extraer las reglas habría costado **168**. Así que el mapa
     se fue a `mapa.md` (~130 líneas, legible entero) y las reglas se
     quedaron con el nombre viejo.

     **Y un índice temático, que para este corpus es MEJOR que los ficheros,
     no un sustituto pobre:** como una regla puede pertenecer a varios temas,
     el índice la lista bajo todos; un fichero la obliga a elegir uno. Lo
     genera `herramientas/indice_reglas.py` entre marcadores (nunca toca el
     cuerpo de las reglas) y `test_docs.py` verifica que no se desincronice.

     Dos cosas que costaron diagnóstico al construirlo, y que valen para
     cualquier clasificador por palabras clave:
     - **Un umbral único no sirve.** Con 3 apariciones exigidas quedaban 39
       reglas (24%) sin tema pese a tenerlo obvio; con 1 entraba cualquier
       mención de pasada y salían 601 entradas para 162 reglas. Quedó en dos
       patrones por tema —DECISIVO (nombra la tecnología, con una alcanza) y
       CONTEXTO (pistas débiles, hacen falta 2)— más un puntaje que conserva
       sólo los 2 temas más fuertes de cada regla. Resultado: 258 entradas,
       1,6 temas por regla, cero sin clasificar.
     - **Las palabras genéricas del castellano son ruido, no señal.**
       `columna` mandaba a AgGrid toda regla de gráficos y `período` mandaba
       a SUNAT toda regla con fechas. Hay que elegir términos que sólo
       aparezcan en su tema.
     - **La última regla se comía todo lo que viniera después.** El extractor
       cortaba cada regla en la siguiente, así que la final absorbía la nota
       del pie — y como esa nota nombra la serie de SUNAT, la #161 (que es de
       Plotly) salía indexada bajo SUNAT. Se arregló con un marcador
       explícito `<!-- REGLAS:FIN -->`.

164. **El botón Refrescar dejó de vivir en la franja superior de navegación
     y pasó al pie del rail de vistas** (2026-08-22, a pedido). Hasta ese
     día `navegacion.py::inject_navegacion` dibujaba el botón como el ítem
     final de `nav_rail` (`_fragment_boton_refresco`, empujado al extremo
     derecho con `margin-left:auto`) — una acción mezclada en una franja que
     por lo demás es una lista pura de reportes.

     Ahora lo dibuja `graficos/base.py::_render_rail` (renombrado a
     `boton_refresco`, sin parámetros), al pie de CADA rail de vistas —
     Compras, Ajuste, Ventas, Inventario, Salidas, Requerimientos, Receta
     Base/Venta: los ocho dashboards que llaman a `_render_rail` heredan el
     botón de una sola vez, igual que antes lo heredaban los ocho reportes
     de la franja superior.

     **El truco: `_render_rail` no sabe qué archivo/reporte activo hay que
     refrescar** (esa información la resuelve `inject_navegacion`, que corre
     en `app.py:129`, casi 900 líneas antes de que `_render_contenido()`
     dibuje el rail). En vez de encadenar el dato por parámetro a través de
     los ocho dashboards, `inject_navegacion` lo deja en
     `st.session_state["_ctx_refresco"]` y `boton_refresco()` lo lee al
     dibujarse — incluso quedó sin argumentos.

     El botón se dibuja FUERA de `graf_tipo_chips` (misma razón que el
     pestillo, regla #6): ese contenedor estila a todo lo que cuelga de él
     como ítem de la lista de vistas, y Refrescar no lo es. Hereda el
     esconder/mostrar del pestillo plegado (`estilos/_25_rails_pestillo.py`)
     con el mismo criterio que `graf_tipo_chips` — mismo `:has(style.rail-
     der-plegado)`, misma reaparición en el `:hover` de vistazo, mismo
     forzado-visible en el `@media (max-width:900px)` que ya deshace el
     plegado en móvil.

     **Regla:** una acción (no una vista) que vive dentro de un componente
     de layout COMPARTIDO por N pantallas no necesita que las N pantallas se
     enteren de sus datos — puede leerlos de `session_state`, escrito por
     quien sí los tiene a mano en ese momento del run.

165. **Al agregar una barra de modos quedaron DOS controles del mismo
     estado, uno encima del otro — y se desincronizaban** (2026-08-22, de la
     pregunta "¿es lógico tener esto, ahora que ya hay un toggle abajo?").

     La barra unificada (#158) puso un botón "🔍 Inspector" que alterna el
     silenciador del tooltip. Pero el badge "Inspector ON" de `inspector.py`
     ya tenía su propio botón "👁 Ocultar tooltip", que alterna EXACTAMENTE
     lo mismo — y quedó apilado 8px encima. Dos pastillas de acento, con
     aspecto de control las dos, para un único booleano.

     **No era sólo redundancia visual: mentían.** La barra se repinta en
     `construirBarra()`, que corre después de SUS clics. El botón del badge
     llamaba a `__inspectorAlternarSilenciado` directo, así que el estado
     cambiaba y el botón de la barra **se quedaba con el color viejo** hasta
     el siguiente rerun de Streamlit. Dos caminos al mismo estado, uno de
     ellos mostrando lo contrario de la verdad.

     Arreglo, en dos partes:
     - **El badge deja de ser control y deja de ser estado.** Se le sacan el
       botón y el rótulo "Inspector ON" —eso ahora lo dice el color del botón
       de la barra— y queda SÓLO con lo único que aportaba y no vive en
       ningún otro lado: los atajos (`C copiar · clic-derecho fija y copia ·
       T oculta tooltip · Alt+I salir`). Se reestiliza como texto de ayuda
       (gris translúcido, `pointer-events: none`) en vez de pastilla de
       acento: si no se puede clickear, no tiene que parecer clickeable.
       Bajó de 31px a 20px y la huella del par, de 75px a 64px.
     - **`Alt+T` también repinta la barra.** Era el OTRO camino al
       silenciador y tenía el mismo problema que el botón del badge. El
       handler de la barra ya interceptaba `Alt+I`; ahora hace lo propio con
       `Alt+T`.

     La regla general, que es la que vale para la próxima: **cuando una
     superficie nueva absorbe una función, la vieja tiene que soltarla — no
     quedarse "por las dudas".** Un estado con dos dueños se desincroniza
     siempre; la pregunta no es si va a pasar sino cuándo. Y si el control
     duplicado tiene su propio camino de teclado, ése también cuenta como
     dueño.

     Verificado en la app: alternando por la barra Y por `Alt+T`, el booleano
     y el color del botón quedan siempre de acuerdo; el badge tiene 0 botones
     y `pointer-events: none`.

166. **El contorno del modo diseño se dibujaba ENCIMA del borde real del
     elemento — así que para ver "Borde completo" había que soltar el pin**
     (2026-08-22, reportado con captura: "veo enorme el cuadrado y pequeño
     lo que contiene... al seleccionar todo el marco se colorea y debo
     deseleccionarlo para ver el cambio").

     `trackear()` posicionaba el `overlay` con el `getBoundingClientRect()`
     EXACTO del elemento, `box-sizing: border-box`. Sus 2px de borde violeta
     caían justo sobre el borde propio del widget — que es precisamente lo
     que uno está ajustando con el control "Borde completo" del panel. El
     único jeito de ver el resultado real era soltar el pin (con lo que se
     perdía el panel de edición) y volver a fijar para seguir.

     Dos cambios, ninguno toca cómo se mide el elemento en sí:
     - **El contorno se separa 4px** (`SEPARACION_CONTORNO`) del rect real en
       vez de coincidir con él. Las manijas de resize son hijas del overlay,
       así que se corren con él — pero `iniciarArrastre()` mide
       `ctx.el.getBoundingClientRect()`, nunca el overlay, así que el
       redimensionado no cambió (verificado: +40px pedidos, +40px reales).
     - **Botón para ocultar el contorno del todo, sin soltar el pin.** La
       separación de 4px alcanza para ver un borde fino, pero para juzgar
       color/sombra/el look final hace falta la vista completamente limpia.
       El botón nuevo (`▣`/`□`) vive en la cabecera del panel, junto a
       "Soltar" — la diferencia es que éste SÍ mantiene el panel de edición
       abierto y el pin activo.

     La regla, para la próxima herramienta de overlay que se agregue: **una
     capa de selección que coincide exactamente con la caja de lo
     seleccionado tapa lo único para lo que existe** — bordes, sombras, cualquier
     cosa que se dibuje sobre el perímetro. Necesita margen propio, y
     además una forma de apagarse sin perder el estado de edición.

167. **El fondo general de la app no se podía editar con el modo diseño:
     el lienzo es el único contenedor que no tiene `st-key-*`** (2026-08-22,
     del pedido "quiero con mi herramienta de diseño poder editar el color
     de fondo").

     Todo el sistema de pin resuelve por esa convención: `contenedorConKey()`
     (inspector) sube desde el elemento hasta `body` buscando la primera
     clase `st-key-*`, y el modo diseño re-resuelve con
     `doc.querySelector('.st-key-' + key)`. Pero los cuatro contenedores del
     lienzo —`stApp`, `stAppViewContainer`, `stMain`,
     `stMainBlockContainer`— los genera Streamlit, no un
     `st.container(key=...)`, así que **ninguno tiene key**. Medido en la app
     antes del arreglo: clic derecho sobre cualquier zona vacía resolvía a
     `null`, no abría el panel, y el control "Fondo" quedaba inalcanzable
     justo para lo único que la mayoría quiere cambiar ahí.

     **Arreglo: una key SINTÉTICA, no tocar la lógica del pin.**
     `marcarLienzo()` en `_inspector_js.py` le agrega
     `st-key-app_lienzo` a `stAppViewContainer`. Con eso
     `contenedorConKey()` lo encuentra solo y el modo diseño lo re-resuelve
     con su `.st-key-<key>` de siempre — **cero cambios en la lógica de
     ninguno de los dos módulos**, que es lo que hace el arreglo barato y
     difícil de romper.

     Detalles que sí importan:
     - **El nombre se eligió después de verificar los wildcards.** Los
       selectores por familia de `estilos/` van todos con prefijo propio
       (`app_reporte_`, `chartcard_`, `grid_`, …) y **no hay ninguno genérico
       `[class*="st-key-"]`**; `app_lienzo` no matchea ninguno. Es
       exactamente la trampa que advierte CLAUDE.md, y acá se comprobó ANTES
       de elegir el nombre, no después de un bug.
     - **Sólo con el inspector activo** (`inspectorActivo()`): en producción
       el DOM queda intacto, sin clases de mentira.
     - **El cambio se ve en toda la pantalla** porque el lienzo la cubre
       entera (medido: 1280×720 de 1280×720). El modo diseño aplica con
       `!important`, así que gana sobre
       `[data-testid="stAppViewContainer"] { background: var(--bg-primary); }`
       de `_00_base.py`, que no lo lleva.

     **Ojo con lo que esto NO hace: no persiste.** Como todo el modo diseño,
     es DOM efímero y muere al recargar. Para dejar el fondo cambiado de
     verdad hay que tocar las DOS caras de la paleta (regla #1):
     `GRIS_FONDO` en `tema.py` y `--bg-primary` en `estilos/_00_base.py`. El
     flujo pensado es probar el color en vivo, apretar "Copiar CSS" y pegar
     el valor en esos dos sitios.

168. **Las manijas del modo diseño quedaban FUERA DE LA PANTALLA cuando el
     elemento tocaba un borde** (2026-08-22, reportado con captura: "¿cómo
     puedo hacer clic cuando la perilla para arrastrar está fuera de la
     pantalla?").

     Las cuatro manijas cuelgan del contorno con offsets NEGATIVOS a
     propósito —viven por fuera del elemento para no taparlo—: la perilla de
     mover en `top:-13px; left:-13px`, las de resize en `-5`/`-6`. Con el
     contorno además 4px afuera (regla #166), un elemento pegado al borde
     superior deja la perilla en **y = -17**: inalcanzable, y sin ninguna
     alternativa para moverlo. Pasó con `nav_rail`, que vive en `top: 0`.

     `clampManijas()` las mete ADENTRO cuando no hay sitio afuera. Dos
     detalles que no son obvios:
     - **El clamp se calcula contra el viewport ABSOLUTO, no contra el
       contorno.** Con el contorno ya 4px afuera, el atajo de "ponerle 2px"
       la dejaba igual medio fuera de la pantalla (y = -2). Hay que resolver
       el mínimo en coordenadas de ventana.
     - **El PANEL lateral también tapa**, y el síntoma es idéntico. Un
       elemento ancho (`nav_rail` mide 1264px) llega por debajo suyo y sus
       manijas derechas quedan *dentro* del viewport pero incliqueables — el
       primer arreglo no las cubría, lo destapó medir `elementFromPoint`
       sobre el centro de cada manija en vez de mirar sólo el rect. Se toma
       el borde izquierdo del panel como límite derecho real, y **sólo
       cuando el panel se cruza verticalmente con el elemento**: si no, un
       panel colapsado abajo a la derecha recortaría manijas que se ven bien.

     Verificado con `nav_rail` (top:0, 1264px de ancho): las cuatro manijas
     pasan a estar dentro y clicables — la perilla de mover de y=-17 a la
     caja (4,4)-(28,28), y las derechas corridas a x≈1046 con el panel
     empezando en 1050. Y con una tarjeta en medio de la pantalla los
     offsets vuelven a los negativos originales: **el clamp no se activa
     cuando no hace falta.**

     Queda un caso vecino que NO es esto y tiene salida propia: el TOOLTIP
     del inspector puede tapar una manija (medido: un `<pre>` sobre la manija
     inferior). Se resuelve con la tecla `T`, que lo oculta.

169. **El CSS que exporta el modo diseño es una FOTO DE PÍXELES, no la
     intención: pegarlo tal cual rompe las variables que hacen funcionar la
     app** (2026-08-22, de un "Copiar CSS" del rail que traía cinco
     propiedades y sólo dos eran deseadas).

     El bloque copiado sobre `compras_tabs_row` (la key del rail COMPARTIDO
     por 8 dashboards) decía:

     ```css
     flex: none; max-width: none; max-height: none;
     height: 688px; width: 270px;
     transform: translate(4px,-10px) rotate(0deg);
     ```

     Qué habría roto cada línea, y por qué la herramienta no puede saberlo:
     - **`width: 270px`** pisa `var(--rail-der-w)`, que el PESTILLO reescribe
       al plegar (`_25_rails_pestillo.py`). Con un ancho fijo el rail deja de
       plegarse. Lo correcto es mover `--rail-der-full` (230 → 270): el
       pestillo sigue vivo y `--rail-der-res` —la reserva que el contenido le
       hace al rail— **se recalcula sola**. Verificado: pasa a
       `calc(270px + 15px + 54px)` sin tocar nada más.
     - **`height: 688px`** es el alto que el rail tenía EN ESA PANTALLA. El
       CSS real usa `height: auto` a propósito y documentado (regla #99: "el
       rail debe reducirse, no ser tan largo"). Un alto fijo se rompe en
       cualquier otro monitor.
     - **`max-height: none`** mata la red que activa el scroll interno si
       algún día hay más vistas de las que entran.
     - **`transform: translate(...)`** sobre un elemento que YA es
       `position: fixed` es redundante y encima captura a sus hijos `fixed`
       (regla #156). Se traduce al `top`/`left` que el rail ya tiene.
     - **`flex: none` y `max-width: none`** ni siquiera son del usuario: los
       agrega la herramienta para poder redimensionar un flex item (regla
       #47). Copiarlos propaga andamiaje interno al CSS de producción.

     **La regla de uso, que es lo que hay que recordar:** el "Copiar CSS" es
     un punto de partida para CONVERSAR sobre el cambio, no un parche para
     pegar. Antes de aplicarlo hay que preguntarse, propiedad por propiedad,
     si detrás hay una variable, una regla documentada o simple andamiaje —
     y traducir la intención, no los píxeles. Acá de cinco propiedades
     sobrevivieron dos, y ninguna en la forma en que venía escrita.

     Verificado tras traducir: ancho 270 con el ciclo del pestillo intacto
     (270 → 24 → 270), `top`/`left` aplicados sin `transform`, y el alto
     seguido midiendo el contenido con su `max-height` de red.

170. **Se invirtieron Reportes y Vistas: Reportes al rail vertical
     izquierdo, Vistas a la franja horizontal superior — y de paso, un KPI
     chico por reporte en el rail** (2026-08-22, a pedido explícito). Es la
     reversión de la regla #99 (2026-08-18: Reportes bajó de rail a franja,
     referencia MSN Dinero) — documentada acá porque revertir una decisión
     razonada no es volver al código viejo sin más: la razón original
     ("una franja horizontal no compite por ancho") ahora aplica a Vistas,
     y hay que releerla desde ese lado.

     **Enfoque: contenedor por POSICIÓN, no por contenido** — mismo patrón
     que el repo ya usó con `--rail-der-*` tras el flip del 2026-08-18
     (nombre histórico, comportamiento actual). `compras_tabs_row` sigue
     siendo LA KEY DEL RAIL VERTICAL (hoy dibuja Reportes); `nav_rail` sigue
     siendo LA KEY DE LA FRANJA HORIZONTAL (hoy dibuja Vistas). Con esto,
     `estilos/_00_base.py` (las 5 variables), `_25_rails_pestillo.py`,
     `pestillos.py` y los dos asserts de geometría de `test_graficos.py`
     quedaron **sin tocar una línea** — apuntan a la key del contenedor, no
     a lo que dibuja adentro.

     **Por qué `inject_navegacion()` y los 9 `_render_rail(...)` NO se
     movieron de sitio en el script**, aunque cambiaron de contenedor —
     esto es lo más importante de la regla, lo que un "mové el dibujo
     nomás" se hubiera comido crudo: `reporte`/`cfg`/`df_f` se calculan en
     `app.py` ANTES del `@st.fragment` que envuelve `_render_contenido()`,
     y quedan capturados en su closure. Si Reportes se dibujara DENTRO del
     fragment (junto a Vistas), un clic en un reporte sólo re-ejecutaría el
     fragment: el botón se vería activo pero `df_f` quedaría **congelado
     en el reporte anterior** — bug silencioso, no un error visible, del
     tipo que se descubre días después con una captura de pantalla que "no
     tiene nada raro". `inject_navegacion()` se sigue llamando en
     `app.py:129`, mismo punto de siempre; sólo cambió qué `key=` de
     contenedor abre.

     **El CSS Compras-específico de lista (ícono+chevron+hairline,
     `estilos/_20_compras_rail.py`, nacido 2026-08-21) se GENERALIZÓ, no se
     borró.** Estaba scopeado `:has(.st-key-app_reporte_compras)` porque
     antes vestía las VISTAS de Compras, activas sólo cuando ese reporte
     lo estaba. Como ahora vive en `compras_tabs_row`/`graf_tipo_chips`
     dibujando REPORTES — presentes SIEMPRE, no condicionados a qué
     reporte esté activo — se le sacó el scope. El pedido era "ícono +
     texto"; reusar este formato ya hecho lo cumple de sobra.

     **La defensa "tooltip fantasma"** (`help=` deja una copia suelta sin
     envolver dentro del mismo `stButton`, invisible mientras nada le da
     alto/ancho explícitos) viajó de `navegacion.py` a
     `estilos/_20_compras_rail.py`: Reportes usa `help=` (tooltip con el
     nombre completo) y se mudó al rail; Vistas nunca lo usó. Verificado
     con la copia real: `getBoundingClientRect()` da `0×0` — oculta de
     verdad, no por casualidad de layout como en el hallazgo original.

     **Los KPIs, agregados DuckDB baratos** (mirror de
     `data.py::rango_fechas`, no descargan el parquet completo):
     `REPORTES[x]["kpis"]` declara `(etiqueta, columna, agregación)`,
     resuelto contra el ESQUEMA REAL de cada parquet (consultado con
     `DESCRIBE` contra R2, no adivinado — los nombres de columna de
     `REPORTES[x]["fecha"]` vienen en Title Case por el `buscar_columna`
     tolerante que los resuelve en tiempo de carga; el nombre CRUDO del
     parquet puede ser otro — Salidas/Requerimientos son
     `"FECHA REGISTRO"` en mayúsculas contra el parquet, no
     `"Fecha registro"` como dice su propio `REPORTES[x]["fecha"]`).
     `kpi_dedup` resuelve el caso Ventas (Pax se repite por LÍNEA de venta,
     no por pedido — sin dedup, sumarlo infla el conteo): agrupa por
     `LLAVE LOCAL PEDIDO` ANTES de agregar, en la misma consulta.

     Tres bugs que sólo aparecieron verificando en el navegador, no antes:
     - **`fmt_k` no manejaba negativos** (`utils.py`): Ajuste Valorizado
       puede ser negativo (merma), y `v >= 1_000` es SIEMPRE falso para un
       negativo — "S/ -56320" salía sin abreviar ni agrupar en vez de
       "S/ -56.3k". La magnitud (`abs(v)`) decide el corte, no `v` directo.
       Agregado a `test_graficos.py`.
     - **La línea de KPIs no sobrevivía el paso a fila en mobile**
       (`nav-kpis`, pensada para apilarse BAJO su botón en columna):
       medido en 375px, se convertía en un flex-item más DE LA MISMA FILA
       que los chips, flotando arriba en vez de bajo su reporte. Se oculta
       en `@media(max-width:900px)`, mismo criterio que ya ocultaba
       categorías/separadores ahí. Ojo con la ESPECIFICIDAD al ocultarla:
       la regla base (`navegacion.py::_CSS_KPIS`) y el override móvil
       tienen la MISMA especificidad nominal, y `estilos/` se inyecta
       ANTES que `inject_navegacion()` — a igual especificidad gana la que
       va DESPUÉS en el DOM, así que el override perdía en silencio hasta
       duplicar la clase del contenedor (mismo truco que ya usa el resto
       del archivo).
     - **El hairline entre ítems vivía en el `<button>`, y un
       `button[kind="primary"]` global de `_00_base.py` (`border: none`)
       le ganaba en especificidad** al ítem ACTIVO específicamente (los
       inactivos sí mostraban la línea — sólo el reporte activo la
       perdía). La causa de fondo no era la especificidad sino el DISEÑO:
       la línea tiene que separar UN REPORTE del siguiente, no el
       ícono+label de su propia línea de KPIs un renglón más abajo. Se
       movió el hairline del `<button>` al `<div>` contenedor (evita la
       pelea de especificidad por completo) y se apaga selectivamente en
       el div del botón cuando el siguiente hermano es su propio
       `.nav-kpis` — así la línea cierra el PAR completo
       (ícono+label+KPIs), no corta en el medio.

     Verificado en la app real con datos de R2 (no demo): switch de
     reporte dispara rerun completo y los datos cambian de verdad (probado
     Compras→Ventas: la franja pasó de 8 vistas de Compras a 11 de Ventas
     propias); switch de vista es rápido —fragment, ~6s vs ~30-40s de un
     reporte con `carga_por_rango`—; pestillo pliega 270→24→270px; mobile
     con los DOS breakpoints ya existentes (768px franja→bottom-nav, 900px
     rail→tira horizontal) sin solape; deep-link en frío
     (`?reporte=Ajuste de Inventario`, sin `?vista=`) resuelve al primer
     ítem sin excepciones. Sin errores de servidor en toda la sesión de
     pruebas.

171. **Los KPIs del rail (regla #170) se rehicieron a las pocas horas:
     "no se ve bien" con una captura, y una segunda con la referencia
     exacta — el panel "Vistos recientemente" de MSN Money: nombre a la
     izquierda, valor grande alineado a la derecha EN LA MISMA FILA, y un
     dato secundario chico debajo de cada uno.** La primera versión
     dibujaba los KPIs como una tercera línea suelta debajo del botón — un
     `st.markdown` hermano — y el resultado se leía flotando entre dos
     filas, sin quedar claro de cuál era. El problema no era de tipografía
     ni de color: era que texto en un renglón propio, por definición, NO
     comparte fila con nada.

     **`st.button()` escapa el HTML de su label — verificado en vivo, no
     asumido.** Se armó un server descartable de una línea
     (`st.button('<span style="color:red">rojo</span>')`) y el resultado
     fue el texto literal `&lt;span...&gt;`, no HTML renderizado. Cerrada
     esa puerta, la única forma de que nombre y valores compartan fila es
     SUPERPONERLOS: cada ítem del rail pasa a envolverse en su propio
     `st.container(key=f"navitem_{slug}")` (botón + su `st.markdown` de
     valores, juntos) — ese contenedor es el ancla real de
     `position:absolute` que los dos elementos necesitaban y no tenían
     (antes eran hermanos sueltos sin ancestro en común más cercano que
     `graf_tipo_chips`, compartido por TODOS los ítems).

     **Trampa que costó un diagnóstico propio: Streamlit le da
     `position:relative` a TODO `stElementContainer` por defecto** (para
     sus propias decoraciones internas — toolbar, etc.), y ese wrapper del
     `st.markdown` —alto 0, más CERCANO en el DOM a `.nav-kpis-valores`
     que el propio `navitem_`— se colaba como ancla de
     `position:absolute` antes de llegar a `navitem_`. Medido: el bloque
     de valores aparecía centrado contra una caja de 0px de alto en vez
     del botón de 40px, corrido ~20px hacia abajo — con la caja del ancla
     equivocada, "centrado verticalmente" da un resultado que SE VE
     centrado sobre algo, sólo que sobre lo que no es. Se apaga con
     `position:static` SÓLO en el `stElementContainer` que envuelve a
     `.nav-kpis-valores` (con `:has()`, no en todos los del `navitem_` — el
     del botón necesita el suyo).

     **El chevron (›) se sacó**, no se reubicó: ocupaba la misma esquina
     derecha que ahora ocupan los valores, y entre los dos el valor es el
     que aporta información — el chevron sólo decía "hay más", que ya lo
     dice el propio hover de un ítem de lista.

     **El hairline se simplificó de rebote.** La versión anterior (regla
     #170) necesitaba lógica de hermanos (`:has(+ div .nav-kpis)`) porque
     botón y KPI eran hijos SUELTOS de `graf_tipo_chips`, y había que
     decidir cuál de los dos cerraba la línea de cada reporte. Con los dos
     adentro de un único `navitem_`, cada reporte vuelve a ser exactamente
     un hijo directo — un hairline por hijo, apagado en el último, sin
     `:has()` ni casos especiales.

     Verificado en vivo, con los 6 reportes reales: los 6 items dan
     `centrado:true` (centro del valor vs. centro del botón, tolerancia
     2px); ningún label choca con su valor (el hueco más chico, Ventas
     con 3 datos en el secundario, da 12px libres); el activo (Compras)
     colorea sus valores en `--accent-deep` sobre el fondo `accent-light`,
     igual que el label; hairline limpio en los 5 primeros, apagado en el
     último; mobile sigue ocultando los valores (0 visibles de 4 en DOM,
     `position:static` — el layout de fila no tiene "debajo" donde
     superponer nada).

172. **`help=` en un `st.button()` rompe cualquier selector CSS que escriba `.stButton > button` (hijo directo): TODO el look propio del rail de Reportes llevaba desde la regla #170 corriendo con el default de Streamlit, sin que se notara.** El pedido que lo destapó fue simple —"quiero `border-radius:0` en todos los botones del rail, como ya lo tiene Compras"— pero medir en vivo (misma disciplina que ya había hecho falta tres veces en la regla #171: no confiar en la especificidad de memoria) mostró algo peor que lo pedido: ni el activo NI los inactivos tenían `border-radius:0`, tenían 10px/8px — el `border-radius:0 !important` de `_20_compras_rail.py` no ganaba, **no aplicaba**. Tampoco el padding (`10px 16px` por defecto de Streamlit en vez de `1px 10px 1px 7px`), ni el fondo/color propios (activo se veía "parecido" solo porque el `background: var(--accent) !important` global de `_00_base.py` para `button[kind="primary"]` da un morado que a simple vista pasa por bueno).

     Causa: los botones de Reportes usan `help=grupo`/`help=nombre` (`navegacion.py`, para el tooltip con el nombre completo cuando el label se trunca) desde que existen. `help=` hace que Streamlit envuelva el `<button>` real en `div > span.stTooltipIcon > span.stTooltipHoverTarget` — el mismo wrapper que la regla #164 ya había documentado como origen de la "copia fantasma" del tooltip. Un selector `[data-testid="stButton"] > button` (combinador HIJO) exige que `<button>` sea hijo directo de `stButton`; con el wrapper de por medio, deja de serlo, y la regla entera no matchea NUNCA — no es un problema de especificidad (que sí se puede perder contra otra regla), es que el selector no encuentra el elemento.

     El bug es silencioso porque el resultado "por accidente" no se ve roto: un botón `kind="primary"` de Streamlit sin estilizar YA es morado con texto blanco (el chrome global de `_00_base.py`), y uno `kind="secondary"` ya es blanco con texto oscuro — visualmente pasable como "rail con estado activo/inactivo" aunque ninguno de los ~10 selectors específicos del rail (`_20_compras_rail.py`, ~9 bloques: base, `::before`, wrappers de label, `p`, `:hover`, `[kind="primary"]`, más los mismos 3 repetidos dentro de `@media max-width:900px`, más otros 3 en `@media min-width:901px` para padding/gap/tamaño de ícono) estuviera aplicando una sola declaración.

     Fix: cambiar el combinador de hijo (`>`) a descendiente (` `, espacio) en las ~12 declaraciones afectadas — `.stButton button` en vez de `.stButton > button` (y análogo para `[data-testid="stButton"] > button`). Es seguro porque `.stButton` sólo envuelve UN botón (con o sin wrapper de tooltip en el medio), así que el descendiente no puede matchear de más. Las declaraciones que apuntan a hijos DEL botón (`> button > div`, `> button p`) conservan su propio `>` — el combinador roto era sólo el primero, entre `.stButton`/`stButton"]` y `button`.

     Verificado en vivo tras el fix, en desktop (1280px, fuera de ambos breakpoints móviles): activo y 5 inactivos dan `border-radius:0px` (antes 10px/8px), padding `10px 12px 10px 9px` (antes `10px 16px` default), `border-left` 3px acento en el activo / 3px transparente en los demás, fondo `accent-light`/gris propio (no el morado/blanco default), ícono a 19px, label `<p>` a 13px, hairline 1px entre ítems apagado en el último, y los bloques de KPI (regla #171) siguen centrados y alineados a la derecha sin corrimiento — el fix no tocó su selector porque `.nav-kpis-valores` es un `st.markdown`, no un `st.button`, y nunca tuvo el problema. `.st-key-rail_refresh button` (Refrescar, también con `help=`) ya usaba descendiente desde el principio y no necesitó cambio — por eso nunca se notó ahí.

     Moraleja para el resto del código: cualquier `st.button(..., help=...)` existente o futuro necesita que su CSS lo apunte con descendiente, no con hijo directo, si el selector menciona el `<button>` mismo (no sus hijos). `graficos/base.py::_render_rail` (Vistas, franja horizontal) no usa `help=` — su CSS con `>` sigue siendo correcto tal cual.

173. **El overlay del modo diseño tiene `pointer-events:none` a propósito
     (para poder ver/medir lo de abajo), así que un click normal SIEMPRE
     seguía de largo hasta el widget real — en un botón del rail eso
     disparaba `on_click` → `session_state["_nav_reporte"]` → Streamlit
     cambiaba de reporte a mitad de una sesión de diseño y todo lo que se
     estaba ajustando (keys de OTRO reporte) desaparecía.** Pedido directo
     2026-08-23, con dos síntomas reportados que se sospechó eran la misma
     causa: (1) "seleccionar" un elemento del rail para diseñarlo a veces
     navegaba a otro reporte y perdía el trabajo, y (2) después de pinear
     algo, un click posterior "desactivaba" el panel lateral
     (`el-diseno-panel`, 230×720 fijo a la derecha — distinto del toolbar
     inferior de la regla #158, que en este proyecto se sigue llamando
     "la barra").

     El (2) no es un bug propio del panel: `sync()` (el poll de 150ms) lo
     oculta cada vez que `disenoActivo()` da `false`, y esa función relee
     el URL fresco en cada tick, nunca lo cachea. Verificado en vivo que
     un click en un `st.button` nativo del rail (`navegacion.py`, sin
     iframes) SÍ dispara su `on_click` con `?diseno=1` puesto, y que
     `st.query_params["reporte"] = reporte` (app.py) preserva `debug`/
     `diseno` en el merge — así que probando el (2) tal cual se reportó
     (pinear `navbtn_Compras`, click en otro ítem del rail) NO se llegó a
     reproducir con ese mecanismo. Lo que sí se confirmó, reproducible al
     100%, fue el (1): el reporte cambia por debajo del panel pineado.

     Fix: `_diseno_js.py` agrega un listener de `click` en CAPTURA sobre
     `document` (el documento PADRE, no el iframe de `components.html`),
     activo solo si `disenoActivo()`. Para cualquier objetivo que NO sea
     parte de la UI propia (`el-diseno-overlay` —cubre manijas y "mover",
     son hijos suyos—, `el-diseno-panel`, `herr-barra`, `herr-panel`,
     `el-inspector-tip`, `el-inspector-badge`) llama
     `preventDefault()+stopPropagation()` ANTES de que el evento baje al
     árbol de React de Streamlit — el listener delegado de React vive más
     abajo en el DOM, así que nunca se entera del click. El clic derecho
     (pin, `contextmenu`) no se toca: sigue siendo la única forma de
     seleccionar, y sigue funcionando exactamente igual.

     Verificado en vivo (Compras, viewport 1280×720, con datos reales de
     R2): con diseño activo, un click en "Recetas" del rail ya NO cambia
     `st-key-app_reporte_*` (antes del fix sí navegaba); con un elemento
     pineado, ese mismo click deja `pinned`, `diseno=1` y el panel
     (230×720) intactos; los controles DENTRO del panel (colapsar con
     "Ocultar panel", swatches de color, árbol de jerarquía) siguen
     recibiendo sus clicks normalmente por estar adentro de
     `el-diseno-panel`; y apagando "Diseño" desde la barra, un click en el
     rail vuelve a navegar como siempre — el bloqueo relee el flag en cada
     evento, no queda pegado.

     Efecto colateral encontrado y NO corregido (fuera de alcance de este
     pedido): con `st.query_params["reporte"] = reporte` de por medio,
     `debug`/`diseno` pueden RESUCITAR después de apagarlos a mano desde
     la barra, porque el snapshot de query params que guarda el backend de
     Streamlit es el de la conexión inicial (cuando `?debug=1&diseno=1`
     sí estaba en la URL) y cualquier escritura de Python a
     `st.query_params` reenvía ESE snapshot completo al navegador. Sólo
     importa para quien apaga el modo diseño a mano y sigue navegando por
     la app esperando que quede apagado.

174. **Al invertir QUÉ dibuja un contenedor compartido (regla #170: `compras_tabs_row` pasó de Vistas a Reportes), una excepción CSS que asumía el contenido VIEJO se queda pisando el reporte equivocado — no se cae sola.** Pedido directo 2026-08-23: "quiero que todos los reportes tengan el mismo rail izquierdo". Causa: `estilos/_00_base.py` definía `--rail-der-full: 84px` como default y sólo lo pisaba a `270px` bajo `:root:has(.st-key-app_reporte_compras)` — una excepción del 2026-08-15 (antes de la regla #170), cuando este rail dibujaba VISTAS y el contenido variaba de verdad por reporte (una columna de etiquetas angosta en casi todos, una lista icono+nombre+chevron sólo en Compras). Desde la regla #170 el rail dibuja siempre REPORTES —la MISMA lista de 6 ítems, sin importar cuál esté activo (regla #171)— así que la condición `:has(.st-key-app_reporte_compras)` dejó de tener sentido, pero nadie la tocó porque **no rompía nada visiblemente en Compras**: sólo se notaba navegando a cualquier OTRO reporte, donde el rail se quedaba en 84px (angosto para "S/ -56.3k" o el nombre más largo) y saltaba de 270→84px al cambiar de reporte.

     Verificado en vivo (preview local, datos reales, viewport 1280×800 — ojo, un viewport de ~857px cae en el breakpoint de 900px que vuelve el rail horizontal, regla #132, y da lecturas que parecen el mismo bug sin serlo): con la excepción, `.st-key-compras_tabs_row` medía 270px en Compras y 84px en Ajuste de Inventario/Ventas/Receta Base — mismo contenedor, mismos 6 ítems, sólo cambiaba el ancho. Fix: se sube `270px` al default único de `:root` y se borra el bloque `:has(.st-key-app_reporte_compras)` entero (no se deja como comentario "removido" — CLAUDE.md). Los tres reportes dan 270px después del cambio, medido de nuevo en la misma sesión.

     Moraleja para el resto del código: cuando un contenedor cambia de DUEÑO de contenido (no sólo este caso — cualquier `:has(.st-key-app_reporte_X)` o similar), hay que grepear ese contenedor por selectores condicionados a un reporte específico y volver a preguntar si la condición sigue significando lo mismo. El bug no tira error ni se ve mal en el reporte que la excepción sí cubre — se ve mal en todos los demás, que es donde nadie mira primero.

175. **Las manijas de resize del modo diseño (regla #46) redimensionan CUALQUIER elemento salvo un Plotly o un AgGrid — para esos dos, agrandar el contenedor no movía un píxel el contenido de adentro.** Pedido directo 2026-08-23: "necesito alguna forma... para poder cambiar el tamaño de los gráficos y tablas". Verificado en vivo ANTES del fix (`.js-plotly-plot` real de la app, no un mock): fijar `width`/`height` en el contenedor del gráfico con `!important` —exactamente lo que hace `iniciarArrastre()`— dejaba el `<svg class="main-svg">` clavado en su tamaño viejo; `Plotly.Plots.resize(gd)` (la API "pensada para esto") tampoco hacía nada. CLAUDE.md ya avisaba la causa ("Plotly no llena su contenedor"): estos gráficos declaran `width`/`height` EXPLÍCITOS en `fig.layout` (nunca `autosize`, es el contrato de `graficos/alturas.py`), así que Plotly no tiene ninguna razón para mirar el tamaño del contenedor. Lo que sí funciona, confirmado en vivo: `Plotly.relayout(gd, {width, height})`.

     AgGrid es peor — tres cajas con tamaño fijo, en cascada, cada una ciega a que la de afuera cambió: el `<iframe>` del custom component trae un `height=` HTML (Streamlit se lo pone vía el protocolo de `Streamlit.setFrameHeight()`, no CSS) y, DENTRO del iframe —mismo origen que la app, se entra sin CORS—, el propio React de `st_aggrid` le clava `style="width:...px;height:...px"` a su `#gridContainer`. Medido en vivo: agrandar sólo el wrapper de afuera dejaba el iframe Y el `#gridContainer` exactamente en su tamaño de antes. Una vez que las tres capas ceden (wrapper, `iframe.style` con `!important`, y `#gridContainer.style` con `!important` adentro del iframe), ag-grid SÍ se reacomoda solo — tiene su propio `ResizeObserver` interno, a diferencia de Plotly no hace falta pedirle nada.

     Fix, todo en `_diseno_js.py`: `contenidoRedimensionable(elemento)` detecta si el pineado ES o CONTIENE un `.js-plotly-plot` o un `iframe[title="st_aggrid.AgGrid.agGrid"]`; `sincronizarContenidoRedimensionable(elemento, ancho, alto)` aplica el mecanismo que corresponda, llamada desde `onMove()` (en vivo, arrastrando) y desde `aplicarEstado()` (el reaplicado defensivo de cada 150ms — un rerun real vuelve a montar el gráfico con su tamaño de Python, y sin este segundo llamado el resize "saltaría" de vuelta hasta el próximo drag). El panel suma un aviso cuando el pineado es de este tipo: el tamaño que se ve arrastrando NO sale de CSS (así que "Copiar CSS" no lo va a incluir) — el número real hay que llevarlo a mano a `graficos/alturas.py`/`fig.update_layout` o al `height=` de `tablas/`.

     **Bug aparte, encontrado mientras se armaba esto (no hipotético — bloqueaba probar el fix en el gráfico real de "Evolución · proveedor"):** `keyDeElemento()` (`_inspector_js.py`, la función que toda esta herramienta usa para saber QUÉ está pineado) leía la key con `/st-key-([A-Za-z0-9_]+)/` — sin guion en la clase de caracteres. Una key armada desde un dato real (`cp_evo_Mes_VIBEJ-COLIBRI-SAC`, el nombre del proveedor con espacios convertidos a `-`, no a `_` como `_slug()`) se leía truncada en `cp_evo_Mes_VIBEJ`, `doc.querySelector('.st-key-' + key)` no encontraba nada, y el pin quedaba en `panelPerdido()` — mudo, sin decir por qué. Fix: agregar `-` a la clase de caracteres. Sólo se tocó esa función (`keyDeElemento`, la que resuelve pines) — las otras dos ocurrencias del mismo patrón en el archivo (`archivoDeSelector`, `selectoresCompartidos`) matchean selectores ESCRITOS A MANO en `estilos/*.py`, que siguen la convención `_slug()` de guion bajo y nunca traen `-`; tocarlas no arregla nada y son un cambio sin verificar de más.

     Verificado en vivo, extremo a extremo (evento real de `mousedown`+`mousemove`+`mouseup` sobre la manija `el-diseno-rh-se`, no una llamada directa a la función): el gráfico de Evolución pasó de 192×277 a 342×377 CON el drag, en el mismo frame que el contenedor; la tabla Ranking de proveedores pasó de 472×333 a 652×483 y su `.ag-root-wrapper` interno confirmó el mismo tamaño tras el `ResizeObserver`. Pineando un botón común (`navitem_Compras`) el aviso nuevo NO aparece y el resize normal sigue igual — sin regresión.

176. **`st.markdown`/`st.caption` aceptan `help=` en este Streamlit (1.59.2) — no hace falta inventar un widget para un ícono ⓘ de "solo contexto".** Pedido directo 2026-08-23 ("minimalista, solo contexto") sobre el título de "Ranking de proveedores" (`graficos/compras/proveedor.py`, un `st.markdown` con HTML crudo, sin label propio). Antes de asumir que hacía falta un widget con `label=`/`help=` puesto al lado (como `periodo.selector()` ya hace con `st.pills`), se comprobó la firma instalada con `inspect.signature(st.markdown)`: trae `help: str | None = None` desde hace rato. Con eso, el ⓘ sale del MISMO elemento — cero layout nuevo, cero widget nuevo, mismo patrón visual que "Help for Período" en el resto de la app. Moraleja: antes de armar un widget-señuelo solo para colgarle un tooltip, revisar si el elemento que ya está ahí acepta `help=` directo — cada vez son más los que lo aceptan.

     **Corrección en el mismo día, del propio usuario ("no ocurre nada al hacer clic aquí, hazlo como el segundo"):** `help=` es HOVER-only — no responde a clic, y el usuario esperaba que el ⓘ se abriera como un popover (comparó contra la pill 📅 de al lado, que si SE PERCIBÍA como "andando" — aunque por dentro usa el mismo mecanismo nativo de tooltip). Antes de tocar nada se verificó en vivo que el `help=` de hecho SÍ funcionaba (`document.getAnimations()` mostraba la animación de fade-in con `playState:"running"` pero `currentTime:0` clavado — el mismo síntoma de `document.hidden` ya documentado en la memoria de sesión (no es una regla de ESTE repo, es del entorno de pruebas); forzándola con `.finish()` la opacidad SÍ llegaba a 1 con el texto correcto). O sea: `help=` no estaba roto, pero tampoco era lo que se había pedido — un tooltip por hover, cuando lo que hacía falta era un disparador por CLIC. Se preguntó para no adivinar mal dos veces seguidas, y la respuesta confirmó: clic, como un popover. Fix: `st.popover(":material/info:", key=..., use_container_width=False)` — mismo patrón de botón-solo-ícono que `pestillos.py::pestillo`, con el texto adentro como `st.caption`. La columna angosta que lo aloja (`st.columns([16, 1])`) necesitó su propio `# columnas-internas:` — sin la marca, `test_graficos.py` la confunde con un split del eje de la página (regla de la "grilla", ver más arriba) y frena el push.

     De paso, en el mismo pedido: **cambiar el TEXTO visible de una opción de `st.pills` sin tocar su VALOR** (la pill "Rango" de `periodo.selector()` pasó a mostrar "📅", pero `periodo.HEREDA` sigue siendo la cadena `"Rango"` en todas las comparaciones) se resuelve con el `format_func` que `st.pills` ya trae — se le agregó el parámetro a `periodo.selector()` (antes no lo exponía) y el call site pasa `format_func=lambda o: "📅" if o == periodo.HEREDA else o`. Ningún otro caller de `periodo.selector()` existe hoy (grepeado), así que no hay riesgo de que un tercero dependa del texto "Rango" tal cual.

     **Decisión de diseño, no bug: "agreguemos los toggles Día/Semana/Mes/Año y Auto/Todo para el gráfico de Evolución" NO se resolvió duplicando esos widgets.** Ya existen (`gran_float`/`win_nav` en `_css_proveedor.py`, flotando `position:absolute` sobre `compras_prov_marco`) y YA gobiernan la curva de Evolución — medido en vivo a 1557px (el viewport real del pedido, vía "Copiar para IA"): ambos caen horizontalmente DENTRO del ancho de `compras_prov_card_evo` (1045–1467px), a solo 9–24px de su borde superior — visualmente ya están "encima" de ese gráfico, no del ranking. `gran` (compartido) entra en `_agregar_periodo()` para las dos columnas por igual, así que un segundo `st.pills` con su propia key escribiendo la MISMA idea sería dos fuentes de verdad para un solo estado — la clase de bug que `session_state` con key única existe para evitar. Se optó por un `st.caption(f"Agrupado por {gran.lower()}")` de solo lectura, pegado a las pills propias de Evolución (Rango/3m/12m/24m/Todo): sin estado nuevo, sin riesgo de desincronización, responde "¿esto también me afecta?" desde adentro de la tarjeta que preguntaba.

     Cuarto cambio del mismo pedido, sin código propio — CSS puro: **ocultar el pill de fecha de la franja (`fecha_ajuste_pill`, `franja_fecha.py`) solo en el drill de Proveedor, agregando la regla a `_css_proveedor.py::CSS_PROVEEDOR`.** No hizo falta un `:has()` — ese bloque YA se inyecta nada más que cuando `_compras_proveedor_drill()` se dibuja (docstring del módulo, "el drill lo inyecta cuando toca"), así que la regla es naturalmente inerte en cualquier otra vista. Se ocultó, no se dejó de llamar `franja_fecha.render()`: el `date_input` de adentro ES la clave canónica del rango (CLAUDE.md § Streamlit), esconderlo del árbol se la habría borrado. Verificado en vivo: con el pill oculto en Proveedor, cambiar a la vista Producto lo vuelve a mostrar con el MISMO rango ("1 ago – 9 ago 2026") — el estado sobrevivió el ciclo ocultar/mostrar.

177. **"COMPRAS: PÁGINA BLANCA, TARJETAS TENUES" (regla #16 y media docena de "vueltas" entre 2026-08-16 y 2026-08-21) se REVIRTIÓ completa — Compras vuelve al mismo lienzo gris + tarjetas blancas que usan los otros 7 reportes.** Pedido directo 2026-08-23: "apliquemos el mismo color de fondo del reporte de Ajuste, para todos los reportes" — con captura de Ajuste (gris visible entre el rail y la tarjeta) y otra de Compras (blanco ahí mismo) señalando la diferencia con flechas. Medido ANTES de tocar nada (`getComputedStyle` en vivo, no a ojo): `html`/`body`/`[data-testid="stAppViewContainer"]` daban `rgb(246,246,248)` en Ajuste y Ventas, pero `rgb(255,255,255)` en Compras — la única diferencia real, ninguna otra reportada por el usuario existía en el código (se descartó a mano comparando Ajuste vs. Ventas primero, que SÍ coincidían, antes de sospechar de Compras).

     La causa era una decisión vieja e intencional, no un bug: Compras invertía el reparto normal (lienzo gris + tarjeta blanca) a "página blanca + tarjeta `--bg-card-tenue`", partida en DOS mitades gemelas que hay que revertir juntas o queda blanco-sobre-blanco (mitad página) o gris-sobre-gris (mitad tarjetas):
     - `estilos/_50_fecha.py`, ~110 líneas ("3ra a 6ta vuelta"): pintaba `:root:has(.st-key-app_reporte_compras)` (y `body`/`stAppViewContainer` del mismo `:has()`) con `background: var(--bg-card)`, aplanaba `fila_ajuste_top::before` a opaco sin blur, le devolvía un hairline compensatorio a `nav_rail` (que sin la página blanca no le hace falta — su borde/sombra de base, `navegacion.py`, ya alcanza) y aplanaba `compras_prov_card_*` con hairline en vez de sombra.
     - `estilos/_80_cards.py`, ~65 líneas ("COMPRAS: PÁGINA BLANCA, TARJETAS TENUES", iba al FINAL del módulo a propósito para ganar por orden de `!important` — ver CLAUDE.md): pintaba esas mismas familias de tarjeta con `--bg-card-tenue`, y encima teñía `stElementToolbarButtonContainer` (el chip de Fullscreen/Download que Streamlit monta al hover) porque blanco-sobre-blanco lo volvía invisible.

     Las dos mitades se borraron juntas (no se dejaron como comentario "// removed" — CLAUDE.md), con una nota corta en cada archivo señalando a esta regla en vez de repetir la historia completa. El propio comentario de la "3ra vuelta" ya anticipaba una generalización, pero en el sentido CONTRARIO ("generalizar a los 8 reportes es sacar este `:has()`" — o sea, llevar el blanco de Compras a todos): el pedido real fue al revés, llevar el default de siempre (el de Ajuste) a Compras. Un comentario que anticipa una dirección no ata la decisión futura — quien pide define el sentido, no el código viejo.

     Verificado en vivo tras el cambio, Compras vs. Ajuste con los mismos selectores: `html`/`body`/`stAppViewContainer` → `rgb(246,246,248)` en los dos; tarjetas (`compras_prov_card_ranking`, `compras_prov_card_evo`) → blanco, `border-radius:20px`, sombra `0 1px 4px rgba(16,16,20,.06)` en los dos; `fila_ajuste_top::before` → mismo blanco al 88% + `blur(14px)` + borde lavanda de 2px en los dos. Sin errores de consola nuevos (sólo el watermark de licencia de AG Grid, preexistente). `test_graficos.py` sigue en verde: ninguna de las dos mitades tenía un `alto`/`ancho` propio que ese test vigile, sólo color y sombra.

178. **Mover un control de "flotando sobre el marco compartido" a "adentro de una tarjeta" no es un cambio de CSS solo — hay que devolverle a `alturas.py` el alto que dejó de regalar gratis.** Pedido directo 2026-08-23: `gran_float` (Día/Semana/Mes/Año) y `win_nav` (‹ Auto/N/Todo ›) — los mismos dos controles de la regla #176, que quedaron flotando sobre `compras_prov_marco` porque duplicarlos adentro de Evolución hubiera sido dos widgets escribiendo el mismo estado — pasaron a vivir DENTRO de `compras_prov_card_evo`, arriba del `st.plotly_chart`, junto a `cp_evo_periodo` (📅/3m/12m/24m/Todo). La razón de fondo para NO duplicarlos seguía siendo válida; lo que cambió es que "adentro de la tarjeta" ya no significa clonar el widget — es MOVER el único que hay, cortando el bloque de Python de donde estaba y pegándolo más abajo, con la MISMA key (`gran_float`, `win_nav` se quedan con el nombre aunque ya no floten — mismo criterio que `--rail-der-*`).

     El movimiento de Python es seguro sin más: los callbacks de `st.button`/`st.pills` corren ANTES del script en el próximo rerun (no en el momento de click), así que DÓNDE se dibuja el widget en el árbol no cambia CUÁNDO ni CON QUÉ VALORES corre su callback — mismo scope de función, mismas variables (`_win_ini`, `_ventana`, etc.) ya calculadas más arriba. Verificado en vivo con clicks reales (no simulados a medias): clickear "Semana" actualizó el eje X, el título del KPI ("Último mes" → "Última semana"), Y el pie de página ("Detalle de documentos... vista Mes" → "...vista Semana") — la propagación a session_state funciona idéntica a cuando el widget flotaba.

     Lo que SÍ había que arreglar: `_ALTO_EVO` (`graficos/compras/proveedor.py`) restaba `FRANJA_PILLS` (el presupuesto de altura de `cp_evo_periodo`) para que la figura le devolviera esos píxeles a la tarjeta — pero `gran_float`/`win_nav` NUNCA habían estado adentro de una tarjeta antes: flotando, no le costaban un píxel a nadie. Medido en vivo ANTES de tocar la fórmula: la tarjeta de Evolución pasó de 407px (su alto de antes de esta sesión) a 473px — 66px de más, EXACTOS a la suma de las dos filas nuevas (22+8 de `gran_float`, 28+8 de `win_nav`) — y la de Ranking se estiró igual para empatarla (`_80_cards.py`, "dos tarjetas de la misma fila miden lo mismo"), dejando aire de sobra al fondo de su AgGrid. Fix: dos constantes nuevas en `graficos/alturas.py` (`FRANJA_GRAN = 30`, `FRANJA_WIN_NAV = 36`, mismo patrón y misma disciplina de medición que `FRANJA_PILLS`) restadas también en `_ALTO_EVO`.

     La resta no devolvió los 66px completos: `_ALTO_EVO` pegó contra el piso `alturas.MINI = 240` (240 < 211, el resultado teórico de restar las tres franjas), así que la tarjeta quedó en 436px — 29px más que el original 407px, el precio de no dejar que el gráfico se encoja por debajo del mínimo legible. No se persiguió ese resto: `MINI` es un piso a propósito (regla viva de `alturas.py`), no un número para forzar. 29px de aire de más es más barato que un gráfico ilegible.

179. **Un atajo de fecha (nuevo o viejo) no sobrevive cambiar de REPORTE y volver — mismo mecanismo que "un widget que deja de renderizarse pierde su estado" (CLAUDE.md § Streamlit), cruzando reportes en vez de modos.** Al agregar los atajos minimalistas dentro de la tarjeta de Ranking ("Este mes"/"Últimos 30 días"/"Este año", reusando `estado_rango.atajos_rango()`/`aplicar_atajo()` — pedido 2026-08-23, "si agregalos de manera minimalista dentro de la tarjeta"), medir el resultado con el panel de siempre llevó a una falsa alarma. `debug_estado_rango()` (el panel de `?diagnostico=1`, que vive en `app.py` FUERA de `@st.fragment`) no mostraba ningún cambio tras clickear un atajo, ni siquiera forzando un rerun completo (cambiar a Ventas y volver a Compras) — parecía que el `on_click` no escribía nada.

     Antes de sospechar del callback se agregó un `st.caption` de diagnóstico TEMPORAL dentro del propio fragment, leyendo `franja_fecha.contexto()` + `st.session_state.get(k_rango)`. Ese sí mostró el valor nuevo (`(2026, 1, 1)` tras clickear "Este año") de inmediato. La discrepancia era de DÓNDE se medía, no de si el click funcionaba: `debug_estado_rango()` no re-ejecuta en un rerun de solo-fragmento — el mismo problema que ya describe el docstring de `navegacion.py` para el cambio de vista, con otro disparador. Medir el estado de un fragment exige un elemento que viva DENTRO de ese mismo fragment; un panel de afuera muestra la foto del último rerun completo, no el estado real.

     Confirmado que la escritura sí ocurre, quedaba la pregunta real: ¿sobrevive un rerun COMPLETO? Repitiendo la prueba con un `st.write` temporal en `app.py` justo antes y después de `asegurar_rango()`: tras clickear "Este año" en Ranking y navegar Compras→Ventas→Compras, `asegurar_rango` recibía `valor=None` — la clave había DESAPARECIDO de `session_state`, no solo revertido a un valor viejo. La causa: `_k_rango_franja` es POR REPORTE (`clave_rango()` arma `f"rango_franja_{reporte}"`), y mientras se ve OTRO reporte no se instancia ningún `st.date_input` con esa key en ningún punto del árbol — Streamlit descarta el estado de un widget que un run entero no reclama, la misma regla que CLAUDE.md ya documenta para los 3 modos de fecha ("esconderlo borraría la clave del rango del reporte"), solo que acá el límite que dispara el olvido es el REPORTE completo, no el modo dentro de un reporte.

     Para descartar que fuera un bug introducido por los atajos nuevos, se repitió el experimento con un mecanismo VIEJO y no relacionado: la pill global de Ajuste (`ajuste_rango_aplicado_visual`), clickeando "Últimos 30 días" (cambia a `25 jul – 5 ago 2026`, confirmado en el `debug_estado_rango()` de AFUERA porque ese botón sí vive fuera de cualquier fragment — no hace falta el truco del caption interno) y repitiendo Ajuste→Compras→Ajuste: mismo reset, al mismo default (`1 ago – 5 ago 2026`). Es una propiedad general y preexistente de tener una key de rango por reporte, no algo que los atajos de Ranking rompieron — arreglarlo (persistir el rango de cada reporte cruzando navegación entre reportes) es un cambio de arquitectura aparte, fuera de lo pedido. En el uso real no se nota: cambiar de VISTA dentro de Compras (Familia/Proveedor/Producto/…) no dispara este reset, porque `franja_fecha.render()` se llama sin condición para cualquier vista de Compras salvo Documentos SUNAT (regla #176) — el widget queda montado todo el tiempo que uno se queda adentro del reporte, y sólo se desmonta al salir de Compras del todo.

180. **Un widget DENTRO de un `@st.fragment` que escribe estado consumido AFUERA no cambia nada en pantalla hasta que alguien pida `st.rerun(scope="app")` — y verificar "cambió `session_state`" NO prueba que el reporte cambió.** Los atajos de fecha que la regla #179 metió en la tarjeta de Ranking (`graficos/compras/proveedor.py`) escribían el rango correctamente y aun así la vista no se movía: reportado por el usuario ("cuando hago click, parece que no cambia nada"). El filtro que consume ese rango está en `app.py:619`, fuera del fragment; `_compras_proveedor_drill` recibe `d` YA filtrado por el último rerun COMPLETO. Un clic adentro re-ejecuta sólo el fragment, que vuelve a dibujar exactamente el mismo `d`. Los atajos del pill original (`franja_fecha.render()`) nunca tuvieron el problema porque se dibujan desde `app.py`, fuera de todo fragment — su clic ya es un rerun completo.

     **La lección de método es más cara que el fix.** Al cerrar la #179 se dio por verificado el feature midiendo `st.session_state[k_rango]` con un `st.caption` de diagnóstico: cambiaba de `(2026,8,1)` a `(2026,1,1)` y eso se leyó como "funciona". La medición era correcta y la conclusión falsa — probaba que el `on_click` ESCRIBÍA, no que la pantalla RE-FILTRARA. En la misma sesión el texto de la página ya mostraba "Total compra S/ 2,104" idéntico antes y después del clic, y pasó desapercibido por estar mirando la métrica equivocada. Regla de verificación: para un control que filtra, la evidencia es el DATO (filas del grid, KPIs, conteo de períodos), nunca el estado intermedio. Acá la prueba buena fueron tres señales a la vez: el ranking pasó de 16 a 24 proveedores, `win_nav` de "Todo 1" a "Todo 8", y ambas volvieron al clickear "Este mes".

     Fix: `_aplicar_atajo_rank()` como `on_click` — delega en `aplicar_atajo` (el dueño único sigue siendo `estado_rango`, no se duplica la escritura) y deja `_cp_rank_atajo_pendiente = True`; al inicio del fragment, `if st.session_state.pop(...): st.rerun(scope="app")`. La bandera no es ceremonia: el `on_click` corre como CALLBACK, antes del rerun del fragment, y `st.rerun()` hay que pedirlo desde el CUERPO. Y no se puede saltear el callback escribiendo el rango desde el cuerpo, porque `k_rango` es la key del `date_input` que `app.py` ya instanció en ese mismo run — escribirla después del widget es `StreamlitAPIException` (el invariante de `estado_rango.py`). O sea: la escritura sólo es legal en el callback, y el rerun sólo es posible en el cuerpo; hacen falta los dos. Mismo patrón que `graficos/compras/__init__.py:216`, que ya cruzaba esta misma frontera por otro motivo (quién dibuja el pill de fecha).

181. **Un bloqueo de interacción SIN acuse de recibo es indistinguible de una app rota — el que bloquea tiene que decir que bloqueó.** El click-blocker del modo diseño (regla #173) hace exactamente lo que se pidió: mientras se diseña, un clic fuera de la UI de diseño no llega al widget, así no se pierde el trabajo por navegar sin querer. Pero lo hacía en SILENCIO. Reportado 2026-08-23 como bug de la app: "tengo problema para seleccionar la visualización Proveedor, esta no se sombrea" — con captura del rail y flecha roja. El usuario había dejado `?diseno=1` prendido de una sesión anterior; el clic del rail se lo comía el blocker y no pasaba absolutamente nada visible.

     Reproducido con la tabla de verdad completa antes de tocar nada, porque el sospechoso obvio era otro (el `st.rerun(scope="app")` de la #180, recién agregado en el mismo drill): con `?debug=1&diseno=1` el clic en "Proveedor" deja el rail en "Producto" y la vista sin cambiar; sacando `diseno=1` de la URL el mismo clic pasa a `primary` y renderiza el drill. Se probó además la secuencia sospechosa de la #180 (atajo → Producto → Proveedor) SIN diseño: funciona perfecto. O sea el rerun nuevo no tenía nada que ver — el blocker sí, al 100%.

     Fix: se conserva el bloqueo (es la función pedida, no un accidente) y se le agrega `avisarBloqueo(x, y)` — un cartelito fijo junto al cursor, "🎨 Modo diseño: navegación bloqueada · apagalo en la barra de abajo", que se desvanece a los 1.2s y se borra a los 1.6s. Tres detalles que no son cosméticos: va en `doc.body` y no en el árbol de Streamlit (un rerun lo borraría a mitad de la animación), lleva `pointer-events:none` (si no, se come el clic siguiente), y se remueve el anterior antes de crear uno nuevo (clickear repetido apilaba carteles).

     La lección general, más allá de esta herramienta: cuando se agrega un guard que descarta eventos del usuario, el costo real no es implementarlo sino que su modo de falla es MUDO. El usuario no tiene forma de distinguir "esto está deshabilitado a propósito" de "esto está roto", y va a reportar lo segundo — como pasó acá, contra una feature que él mismo había pedido dos días antes.

<!-- REGLAS:FIN — lo de abajo no es una regla -->

> **Ojo con el próximo número: la #160 YA está usada.** No vive al final:
> está entre la #143 y la #144 (el registro del SIRE en parquet). Nació
> duplicando el número de la #143 y se renumeró el 2026-08-22 sin moverla
> de sitio, para no partir la serie de SUNAT, que se lee seguida. La
> próxima regla nueva es la **#182**.
>
> **La #162 tampoco vive al final:** está entre la #32 y la #33 (el
> `margin-bottom: -16px` de `st.markdown` con HTML de bloque). Nació
> duplicando el número de la #33 y se renumeró el 2026-08-22 con el mismo
> criterio que la #160 — se movió el NÚMERO, no la regla: de las dos #33,
> la que conservó el número es la del `window.__agApi`, porque es a la que
> apuntan las seis referencias que hay en el código.
