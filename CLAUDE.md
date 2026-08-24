# CLAUDE.md — léeme antes de tocar nada

Webapp Streamlit (Community Cloud) que lee parquets de Cloudflare R2 con
DuckDB y los muestra en tablas AgGrid y dashboards Plotly.

> **Dos documentos, y se usan distinto.** Este fichero es el atajo: lo que
> más se rompe, en una pantalla.
>
> - **`mapa.md`** — qué hay y cómo encaja: tabla de ficheros, pipeline de
>   datos, config de `REPORTES`. Son ~130 líneas y se lee ENTERO. Ante la
>   duda de "¿dónde vive esto?", empieza acá.
> - **`arquitectura.md`** — la bitácora: 162 reglas sacadas de bugs reales.
>   Son 7.100 líneas: **no se lee de arriba a abajo, se busca**. Arranca con
>   un índice por tema para eso. Ante la duda de "¿esto ya me mordió?",
>   busca ahí.
>
> Estaban en un solo fichero hasta el 2026-08-22; se partieron porque juntos
> daban 115k tokens — un "documento principal" que nadie podía abrir. Las
> reglas conservaron el nombre `arquitectura.md` porque hay 166 citas
> `arquitectura.md #NNN` en el código. Ver regla #163.

## Flujo de trabajo

- Push directo a `main`. No hay staging: se valida en Streamlit Cloud.
- El preview local **no siempre toma cambios al navegar/rerunear** si el
  server ya estaba corriendo de antes — confirmado con `estilos/`, y
  también con un módulo de herramienta normal (`formulario_receta.py`,
  2026-08-13: un texto corregido en el código seguía saliendo viejo en el
  navegador). Ante cualquier duda de "¿esto ya se ve actualizado?",
  reiniciar el server en vez de asumir.
- Cada cambio se pushea y se confirma explícitamente. Si algo NO se pusheó,
  decirlo — si no, se diagnostican "conflictos" que no existen.

Antes de pushear, dos comandos (segundos, no minutos):

```bash
python -m ruff check . && python test_graficos.py && python test_asistente_datos.py && python test_docs.py
```

`ruff` usa `ruff.toml`: solo reglas **`F`** (pyflakes) a propósito — las de
estilo marcarían cientos de líneas de CSS embebido y el ruido haría que
nadie mire la salida. Se instala con `pip install -r requirements-dev.txt`
(NO está en `requirements.txt`: Streamlit Cloud lo instalaría en cada
deploy para nada).

**Cuidado con `ruff check --fix` sobre F401:** hay módulos que importan un
símbolo solo para reexportarlo (`graficos/compras/_comun.py` con
`_es_movil`). Van con `# noqa: F401` **y un comentario que diga quién los
consume** — sin eso, el fix automático los borra y rompe a sus
importadores. Ver `arquitectura.md` regla #53.

`test_graficos.py` construye todas las figuras + verifica los contratos del
dispatcher (que cada dashboard acepte `tabla_cb`, la aridad de la llamada, y
que no haya vuelto a aparecer una lista de reportes hardcodeada).

`test_docs.py` verifica que la documentación no se contradiga con el código:
numeración de las reglas (sin duplicados ni huecos), referencias cruzadas
`#NNN` que apunten a una regla que exista, y que lo que ESTE fichero afirma
del código siga siendo cierto (los módulos de `estilos/` y su orden, los
símbolos que nombra, las herramientas que manda usar). Nació el 2026-08-22:
`arquitectura.md` pasó los 7.200 renglones y a ese tamaño los duplicados y
las citas equivocadas ya no se ven a ojo — había TRES pares de reglas con el
mismo número (#33, #143, #157) y un parche citando una regla ajena. No juzga
el contenido de las reglas, sólo lo que tiene respuesta objetiva.

`test_asistente_datos.py` cubre la capa de datos del asistente IA: validación
del SQL que escribe el modelo (blocklist, una sola sentencia, `LIMIT`
automático) y la guarda de **columnas con espacios sin comillas** — que no es
cosmética: `SELECT AJUSTE VALORIZADO` no da error, DuckDB lo lee como
`SELECT AJUSTE AS VALORIZADO` y devuelve la columna equivocada en silencio.
Corre sin API key ni navegador. Ver `arquitectura.md` regla #69.

## El asistente IA no adivina: consulta

`asistente.py` (prompt + bucle de tool calling + UI del popover) y
`asistente_datos.py` (esquema, SQL con DuckDB sobre el df en memoria,
herramientas). Dos cosas que ya costaron bugs:

- **El df que ve el modelo es el POST-CHIPS**, publicado por cada dashboard
  con `graficos.base.publicar_contexto_ia()` tras aplicar sus filtros. El
  `df_f` que pasa `app.py` está filtrado por fecha pero NO por Área/Familia:
  usarlo hacía que el asistente respondiera totales que contradecían la
  pantalla. Si agregas un dashboard con chips, llama a esa función.
- **Su CSS vive en `estilos/_85_asistente.py`**, no inline en el módulo. Un
  `st.markdown` de estilos con guard "inyectar una sola vez" DESAPARECE en el
  rerun siguiente (regla #59).

## El CSS vive en `estilos/`, una sección por módulo

`estilos/` es un paquete (antes era un `estilos.py` de 1.700 líneas). La API
pública no cambió: `from estilos import TAM_FUENTE, inject_css`.

Cada sección tiene su módulo, con prefijo numérico que marca el orden:
`_00_base` → `_20_compras_rail` → `_25_rails_pestillo` → `_30_filtros` →
`_40_ajuste_franja` → `_50_fecha` → `_60_calendario` → `_70_chrome` →
`_80_cards` → `_85_asistente` → `_90_franja_inferior` → `_99_movil`.

**El orden de `_SECCIONES` en `__init__.py` es parte del comportamiento**, no
estética: hay `!important` en ambos lados de varios conflictos, así que gana
la regla que aparece DESPUÉS. `_99_movil` va último a propósito.

Para cambiar un estilo, ubica la sección por el nombre del módulo. Para
agregar una, crea el módulo y súmalo a `_SECCIONES` en la posición correcta.

## Antes de agregar un widget dentro de una tarjeta: grep `estilos/`

El CSS de la app **matchea por prefijo de key**, no por widget. Muchas reglas
son selectores descendientes:

```css
div[class*="st-key-<prefijo>_"] [data-testid="stButtonGroup"] button { ... }
```

Eso captura **todo** widget descendiente, incluidos los que agregues después.
Un `st.pills` nuevo dentro de esa tarjeta hereda el estilo sin que nada en el
`.py` lo insinúe.

**Regla:** antes de agregar o restilizar un widget, `grep` en `estilos/` por
el prefijo de key del contenedor donde vive. Si el estilo es para un widget
puntual, acótalo a su key propia, no al contenedor.

Corolario: si cambias `st.pills` → `st.segmented_control` y se ve idéntico,
no es el widget — es una regla CSS del contenedor. Ambos rinden el mismo DOM
(`[data-testid="stButtonGroup"]`).

## Colores: nunca un `#hex` suelto

Dos caras de la misma paleta, hay que mantener ambas:
- `tema.py` (Python) → Plotly, f-strings, `custom_css` de AgGrid.
- `:root` en `estilos/_00_base.py` (CSS) → todo el CSS global, vía `var(--...)`.

Detalle en `arquitectura.md` § Reglas #1.

## Alturas: nunca un alto suelto

Gemela de la regla de los colores, y con la misma forma de dos caras:
- `graficos/alturas.py` (Python) → el alto de las FIGURAS, con roles
  (`PROTAGONISTA`/`APOYO`/`MINI`, `por_filas()`, `apilado()`).
- `--alto-util` en `estilos/_00_base.py` (CSS) → el MARCO de la tarjeta.

**Ningún `alto=430` ni `height=560` en `graficos/`**: `test_graficos.py`
falla si reaparece uno, o si el cromo de CSS y el de Python se
desincronizan.

Una tarjeta = una pantalla: se clampea con `max-height: var(--alto-util)` y
lo que no entra scrollea DENTRO (`estilos/_80_cards.py`). Dos trampas que
ya están medidas y documentadas en `arquitectura.md` reglas #101 y #102:
**`height` en CSS no aplica** a un bloque de Streamlit (son flex items con
`flex: 1 1 0%`; hay que usar `max-height`), y **Plotly no llena su
contenedor** — `height="stretch"` estira el wrapper pero el SVG se queda
en 450px, así que el alto sale de `fig.layout.height`, o sea de Python.

## Grilla: nunca un `st.columns([...])` suelto en un drill

Tercera cara del mismo patrón (color / alto / **eje horizontal**). La
proporción que parte en dos una fila de un drill de Compras sale de
`graficos/compras/_comun.py::COLUMNAS_DRILL`, no de un literal.

Nació de un bug con captura: el drill de Proveedor partía la fila de arriba
con `[1.6, 1]` y la de abajo con `st.columns(2)`. Los dos números son
correctos por separado; juntos corren el eje de la página ~150px a media
altura y la vista deja de leerse como una grilla.

Las subdivisiones **dentro** de una tarjeta (un chart y su pila de KPIs, una
botonera) sí son literales: se marcan con `# columnas-internas: <por qué>`
en la línea o en las 3 de encima. `test_graficos.py` distingue por esa marca
— mismo idioma que el `# alto-fijo-justificado:` del presupuesto vertical.

Y la gemela vertical de eso: **dos tarjetas de la misma fila miden lo
mismo**. El techo lo pone `max-height: var(--alto-util)`; el piso, una regla
con `:has()` en `estilos/_80_cards.py`. Las columnas de Streamlit sí se
estiran solas, pero el contenedor de elemento que mete entre la columna y la
tarjeta nace con `flex: 0 1 auto`. Detalle en `arquitectura.md` regla #145,
que también lista los cuatro ejes distintos que quedan pendientes en el
resto de `graficos/compras/`.

## Streamlit — trampas que ya costaron bugs

- **`st.markdown` no ejecuta `<script>`.** Animaciones y DOM se hacen con CSS
  sobre `.st-key-*`. Nada de JS inyectado por markdown.
- **La selección de `st.plotly_chart(on_select=...)` persiste entre reruns.**
  Con `key` estática, cada rerun re-procesa el mismo clic → toggle infinito
  (parpadeo). Incluir el foco en la key: `key=f"..._{focus or 'none'}"`.
- **Widget + display auxiliar del mismo valor:** UNA sola key compartida (sin
  `value=`, sin key dinámica). El clamp de bounds va justo antes del widget.
- **Detección móvil server-side:** para texto que Plotly dibuja en servidor,
  User-Agent vía `st.context.headers`. El layout va por CSS `@media`.
- **Un widget que deja de renderizarse pierde su estado.** Por eso el
  `date_input` de la franja se dibuja en los TRES modos: esconderlo
  borraría la clave del rango del reporte.

## El eje temporal tiene TRES modos, y un solo dueño

El calendario de la franja tiene tres modos: **Rango** (intervalo),
**Corte** (el conjunto exacto de días de una sesión de inventario, que no
tiene por qué ser contiguo) y **Varios** (suma varias sesiones en un
solo período).
`cortes.py` calcula los cortes; `estado_rango.py` es el dueño de los tres
estados (rango, corte, modo) y nadie los escribe fuera.

Corte y Varios comparten estado: solo cambia si el clic reemplaza o
alterna. "Varios" nombra la unidad elegida; el verbo (suma) va en el
caption de la lista, no en la pastilla. `_fusionar` une N cortes en un estado con la misma forma que uno,
así el filtro `isin(dias)` no distingue el caso.

`aplicar_corte` escribe el corte **y** el rango — el rango lo leen el
`date_input`, el label del pill y el loader de R2, que no saben qué es un
corte. Detalle y trampas en `arquitectura.md` reglas #62 a #65.

## Plotly — específicos de este proyecto

- **`go.Waterfall` ignora `bargap`.** Usa `waterfallgap` (mayor = barras más
  finas). `go.Bar` sí usa `bargap`.
- **`_layout()` oculta los ticks del eje Y a propósito** (convención: la
  cuadrícula se ve, los valores no). En barras **horizontales** el eje Y son
  NOMBRES, no valores: hay que pasar `showticklabels=True` + `automargin=True`
  o las etiquetas no aparecen.
- En barras horizontales, grosor y separación dependen ambos de los píxeles
  por fila (`height / n`). Para filas compactas, altura proporcional
  (`height = k * n + margen`), no `bargap`.
- `_LAYOUT_BASE` no se puede desempacar con `**` si el `update_layout` define
  su propio `xaxis`/`yaxis`. Ver `arquitectura.md` § Reglas #5.

## AgGrid — específicos de este proyecto

- **Un `cellRenderer`/`innerRenderer` que devuelve un string de HTML no
  pinta HTML acá — se ve como texto escapado.** `st_aggrid` usa
  `ag-grid-react`; el atajo "vanilla" de AG Grid puro (función que
  devuelve `'<div>...</div>'` o un `HTMLElement`) no está soportado (el
  segundo caso directamente revienta con React error #31). Hace falta la
  interfaz de Component: una `class` con `init(params)` que arma
  `this.eGui` a mano (`createElement`/`textContent`) y `getGui()` que lo
  devuelve. Detalle y ejemplo en `arquitectura.md` § Reglas #25.
- **`api.getValue(colKey, rowNode)` no existe** en la versión de AG Grid
  de este proyecto (34.3.1). Si un cellRenderer necesita el valor de OTRA
  columna, resolverlo con `valueGetter` + `aggFunc` propio en vez de leer
  una columna vecina en tiempo de render.

## Dashboards de gráficos

`graficos/` es un paquete. `__init__.py` es solo el dispatcher
(`_DASHBOARDS = {reporte: render_fn}`). **Agregar un dashboard = crear
`graficos/<nombre>.py` + 1 línea en `_DASHBOARDS`.** No cadenas de if/elif.

## Auditar el layout antes de proponer píxeles

La app **sí corre en local** en modo demo (`data.py::_datos_demo` cuando no
hay secrets R2). Levantarla con `streamlit run app.py` o el preview del
editor y usar `herramientas/auditar_layout.js`:

1. En DevTools → Console, pegar el contenido del archivo.
2. Llamar `auditar()`. Reporta ancho útil, contenedores por altura, alertas
   de los que superan umbrales, outliers dentro de una misma familia de key
   y desborde horizontal — todo con selectores para saltar al elemento.

> **Atajo: no hace falta pegar nada.** Con **`?debug=1`** aparece abajo a la
> izquierda una **barra con las cinco herramientas** — Inspector, Diseño,
> Rayos X, Layout y Gráficos — y los dos auditores muestran su resultado en
> un panel DENTRO de la app, sin abrir DevTools. Los modos se combinan y
> cada uno es un query param (`?rayosx=1`), así que la combinación se puede
> compartir por URL. La barra lee los `.js` de `herramientas/` (una sola
> fuente: siguen siendo pegables en consola). Detalle en `arquitectura.md`
> regla #158. Lo de abajo describe cada herramienta y sus trampas, que
> valen igual desde la barra.

Antes de discutir por qué "algo se ve grande", medir. `auditar()` responde
en 10 segundos y evita ida-y-vuelta de deploys + capturas.

**Para saber si un gráfico se pisa o se corta: pegá
`herramientas/auditar_graficos.js` en la consola y llamá `auditarGraficos()`.**
Mide las cajas de TODOS los textos de cada figura Plotly. Ojo con dos cosas
que ya dieron resultados falsos: recorre los **tres** `svg.main-svg` (las
anotaciones viven en el segundo, no en el primero), y hay que **recargar
después de cambiar el tamaño de la ventana** o reporta recortes que no
existen. Ver `arquitectura.md` regla #96.

**Para VER la ESTRUCTURA (qué caja es cada cosa): pegá
`herramientas/rayos_x.js` y llamá `rayosX()`.** Los otros auditores miden y
reportan en texto; el inspector marca un elemento por vez. Éste pinta la
página entera en una capa aparte y separa las tres cosas que a simple vista
son indistinguibles: **cajas en el flujo** (línea llena, color = nivel de
anidado), **escapados** (`fixed`/`absolute`, línea cortada, con una línea
trazada hasta el padre al que pertenecen en el código) y
**pseudo-elementos** (línea de puntos: pintan bandas que no existen en el
HTML). Ojo con la trampa que motivó la herramienta: **un `transform` en un
ancestro captura a sus hijos `fixed`**, así que mover/redimensionar con el
modo diseño NO es vista previa fiel si el contenedor tiene hijos flotantes
— ver `arquitectura.md` regla #156.

**Para VER un gráfico sin levantar la app: `herramientas/ver_figura.py`.**
Vuelca a PNG lo que dibuja un dashboard, sin navegador:

```bash
python herramientas/ver_figura.py Ventas -s "ventas_graf_tipo=Comparativo vs Año Pasado" -s ventas_comp_vista=Descomposición
```

`-s key=valor` fuerza cualquier widget o el item del rail por su key (las
muestra el inspector). Existe porque medir el DOM prueba que un gráfico
**funciona**, nunca que **se ve**: así se escapó un legend legible-en-el-DOM
e invisible en pantalla (regla #91). Necesita `kaleido` de
`requirements-dev.txt` y, una vez por máquina,
`python -c "import kaleido; kaleido.get_chrome_sync()"`.
Ojo: los **márgenes** del PNG no son fieles (el export fuerza `automargin`
porque kaleido no expande solo como el navegador) — para juzgar recortes,
el navegador manda.

También existe el inspector propio: **`?debug=1` en la URL o `Alt+I`**
activa `inject_element_inspector` (tooltip con selectores y estilos al
pasar el cursor). El inspector NO agrega elementos visibles en la página
— se ve como producción. Con un elemento fijado, la línea "Cadena de
contenedores st-key" del tooltip es clicable: **migas de pan** que saltan
el pin a cualquier ancestro sin ir a buscarlo a ojo en la pantalla. Para
los paneles de diagnóstico de entorno/performance usar **`?diagnostico=1`**
(independiente de debug).
Y con **`?debug=1&diseno=1`** se suma el **modo diseño**: fijás un elemento
con clic derecho y un panel lateral lo edita en vivo (caja, tipografía,
color, mover/redimensionar, **alto de fila** si es una tabla AgGrid, con
"↺" por fila para revertir solo esa propiedad), o **inserta**
texto/línea/barra/espacio de mentira para ver
"cómo se vería" algo que todavía no existe. El panel abre con un **árbol
de jerarquía** (raíz → elemento, clicable igual que las migas del
inspector — misma idea, orientación vertical en vez de horizontal), y sus
hojas azules bajan el pin a un **hijo sin key propia** (un
`<div class="cp-rank-tit">` de un `st.markdown`): sin eso, "Mover" corría
la tarjeta entera y el título de adentro no se movía — regla #157. La
paleta cubre dato Y superficie (grises/lavanda de `tema.py`, más
transparente y un picker libre), y el botón **"Copiar CSS"** arma el
bloque listo para pegar en `estilos/` — ya no hace falta leer los valores
a ojo del panel. Si al redimensionar no pasa nada en pantalla, mirá la
fila **"Recortado por"**: el elemento SÍ creció, pero un ancestro con
`overflow` recortante se come lo que sobresale. Nada de esto persiste: es
DOM efímero, muere al recargar y no toca `estilos/` hasta que vos pegás el
bloque copiado. Detalle en `arquitectura.md` reglas #46 a #48, #151, #153,
#154, #155 y #188.
Se pueden combinar: `?debug=1&diagnostico=1`. El tooltip incluye
`codigo` (archivo:línea donde está declarada la key, buscado en `app.py`
+ `graficos/` + `tablas/`), `estilos` (archivos de `estilos/` que
matchean el prefijo de la key), `padre` y `hermanos` (contenedores
`st-key-*` adyacentes en el DOM), los **pseudo-elementos `::before`/
`::after` computados** (clave para las bandas que se pintan enteras en un
pseudo, que `el.matches()` no puede alcanzar), el **reporte activo real**
leído del marker `st-key-app_reporte_<slug>` del DOM (no del query
`?reporte=`, que suele faltar), y las **franjas fijas** superior/inferior
(pseudo + `pointer-events:none`) vía fallback por coordenadas.

**Para decidir DÓNDE estilar** (agregado 2026-08-12, ver `arquitectura.md`
regla #90) el tooltip abre con tres líneas hechas para eso:
`ANCLA PROPIA` (el selector que estila SOLO ese widget — todo
`st.X(key="K")` emite `st-key-K`, así que casi nunca hace falta crear un
container), `Contenedores que lo ENVUELVEN` (con cuántos widgets tiene
cada uno adentro) y, al copiar, un `AVISO` si alguna regla que estila al
ancestro es un **wildcard por familia** (`[class*="st-key-pre_"]`) —
editarla toca a todos sus miembros. Nacieron de un bug real: para "subir
un poco este toggle" se tocó el margen del ancestro y se movió el reporte
entero.

Al copiar con **C** se agregan además las **variables CSS** que usa el
elemento con su **valor numérico actual** resuelto
(`--cab-altura = 50px`). Tecla **C**
copia todo eso al portapapeles como un bloque listo para pegar a la IA;
**clic derecho** sobre el elemento hace lo mismo en un solo gesto (fija el
tooltip y copia — el botón "Fijar" standalone solo fija). Si el copiado
automático falla (frecuente en Streamlit Cloud: la app corre en un iframe
propio y `components.html` mete un segundo nivel anidado — ver
`arquitectura.md` § Reglas #39), el texto queda seleccionado para un
`Ctrl+C` manual en vez de fallar en silencio.

## Al terminar un cambio estructural

Actualiza `arquitectura.md` en el mismo commit. Si el cambio enseñó algo que
volvería a morder, súmalo a sus "Reglas del proyecto" — esa lista está hecha
de bugs reales, no de teoría.
