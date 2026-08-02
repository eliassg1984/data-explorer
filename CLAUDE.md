# CLAUDE.md — léeme antes de tocar nada

Webapp Streamlit (Community Cloud) que lee parquets de Cloudflare R2 con
DuckDB y los muestra en tablas AgGrid y dashboards Plotly.

> **`arquitectura.md` es el documento principal.** Tiene el mapa completo de
> ficheros, el pipeline de datos, la config de `REPORTES` y las reglas
> aprendidas de bugs reales. Este fichero es solo el atajo: lo que más
> se rompe, en una pantalla. Ante la duda, abre `arquitectura.md`.

## Flujo de trabajo

- Push directo a `main`. No hay staging: se valida en Streamlit Cloud.
- El preview local **no toma cambios de `estilos/`** al navegar — hay que
  reiniciar el server para verificar estilos.
- Cada cambio se pushea y se confirma explícitamente. Si algo NO se pusheó,
  decirlo — si no, se diagnostican "conflictos" que no existen.

## El CSS vive en `estilos/`, una sección por módulo

`estilos/` es un paquete (antes era un `estilos.py` de 1.700 líneas). La API
pública no cambió: `from estilos import TAM_FUENTE, inject_css`.

Cada sección tiene su módulo, con prefijo numérico que marca el orden:
`_00_base` → `_10_vista` → `_20_compras_rail` → `_30_filtros` →
`_40_ajuste_franja` → `_50_fecha` → `_60_calendario` → `_70_chrome` →
`_80_cards` → `_90_franja_inferior` → `_99_movil`.

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

Antes de discutir por qué "algo se ve grande", medir. `auditar()` responde
en 10 segundos y evita ida-y-vuelta de deploys + capturas.

También existe el inspector propio: **`?debug=1` en la URL o `Alt+I`**
activa `inject_element_inspector` (tooltip con selectores y estilos al
pasar el cursor). El inspector NO agrega elementos visibles en la página
— se ve como producción. Para los paneles de diagnóstico de
entorno/performance usar **`?diagnostico=1`** (independiente de debug).
Se pueden combinar: `?debug=1&diagnostico=1`. El tooltip incluye
`codigo` (archivo:línea donde está declarada la key, buscado en `app.py`
+ `graficos/` + `tablas/`), `estilos` (archivos de `estilos/` que
matchean el prefijo de la key), `padre` y `hermanos` (contenedores
`st-key-*` adyacentes en el DOM). Tecla **C** copia todo eso al
portapapeles como un bloque listo para pegar a la IA.

## Al terminar un cambio estructural

Actualiza `arquitectura.md` en el mismo commit. Si el cambio enseñó algo que
volvería a morder, súmalo a sus "Reglas del proyecto" — esa lista está hecha
de bugs reales, no de teoría.
