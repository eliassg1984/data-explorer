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
| `data.py` | Carga de datos: DuckDB + httpfs leyendo parquets de R2 (secrets). |
| `tablas.py` | Renderizado de tablas AgGrid (desktop, móvil, compras). |
| `graficos.py` | Renderizado de gráficos por reporte. |
| `estilos.py` | CSS global de la app Streamlit (chips, tabs, píldora de fecha...). |
| `navegacion.py` | Rail lateral, topbar y CSS por sección (`_CSS_AJUSTE`...). |
| `inyecciones.py` | Funciones `inject_*`: JS/HTML inyectado (fullscreen, paginación, altura dinámica, overlays). |
| `tema.py` | **Paleta de colores con nombre, definida UNA vez.** Todos los demás importan de aquí. |
| `inspector.py`, `perf.py`, `utils.py` | Herramientas de apoyo (inspector de elementos, medición, utilidades). |

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
   (`html, body {margin:0}`, contenedor de tema y `.ag-root-wrapper` al 100%,
   vía `<style id="dynh-css">`). Motivo: `inject_pagination_v2()` agranda la
   barra de paginación y el body trae margen por defecto; con solo el wrapper
   al 100% el contenido excedía al iframe y la paginación se veía CORTADA.
   Regla general: si dos `inject_*` comparten espacio o elemento, la
   interacción se documenta en ambas (comentario en el código + aquí).

5. **Un cambio a la vez, verificado.** Antes de subir:
   `python -m py_compile <ficheros tocados>`. Sin salida = bien.
   (El SyntaxWarning de `inyecciones.py:358` es preexistente e inofensivo.)

6. **Ocultar ≠ eliminar función.** Reglas con `display:none` (toolbar de
   Streamlit, fullscreen nativo) quitan ACCESO visual, no funcionalidad;
   documentar el porqué junto a la regla.

## Convenciones de estilo AgGrid

- El CSS del grid vive en el diccionario `custom_css` (hoy dentro de
  `tablas.py`; destino: `estilos_grid.py`).
- Estética compartida de los 3 paneles laterales: pastillas redondeadas
  (`border-radius: 999px`, fondo `GRIS_FONDO`, borde `GRIS_BORDE`, hover
  lavanda) — "en juego" con el panel Modo pivote.
- Variantes por reporte (`es_requerimientos`, `es_ajuste`) se aplican DESPUÉS
  del CSS base, nunca mezcladas dentro de él.

## Cómo verificar tras cualquier cambio

```bash
python -m py_compile app.py tablas.py estilos.py inyecciones.py navegacion.py tema.py
```

Luego recargar la app y revisar: tabla Ajuste de Inventario (desktop),
paneles Columnas / Filtros / Modo pivote, botón maximizar y paginación.

## Jerarquía de layout — quién manda sobre cada contenedor

El `padding-top` del contenedor principal (`block-container`) tiene TRES
niveles en cascada. No es duplicación: es una jerarquía deliberada.

| Nivel | Dónde vive | Valor | Cuándo aplica |
|---|---|---|---|
| 1. Default global | `estilos.py` | 1.5rem | Toda la app |
| 2. Override por sección | `navegacion.py` (`_CSS_AJUSTE`...) | 0.85rem | Solo esa sección; gana vía prefijo `html body` |
| 3. Override móvil | `estilos.py` (`@media max-width:768px`) | 0.5rem | Pantallas chicas |

**Regla de propiedad** (dueño único por contenedor):

- Layout de página (`block-container`, header, topbar, por sección) →
  dueño **`navegacion.py`** para overrides de sección; `estilos.py` solo
  guarda el default global y la variante móvil.
- Contenedores con key (`.st-key-fila_ajuste_top`, `.st-key-vistatabs_*`,
  `.st-key-fecha_ajuste_pill`, `.st-key-fch_ajuste_inline`...) →
  dueño **`estilos.py`**. Nadie más los estila.
- **`inyecciones.py` = solo comportamiento (JS).** Nunca estética de
  contenedores. (El viejo `inject_boton_calendario_ajuste`, que violaba
  esto y además era código muerto, fue eliminado en la Fase 1.5.)

Para cambiar el espacio superior de UNA sección: editar su bloque en
`navegacion.py`. Editar el default de `estilos.py` NO tendrá efecto en las
secciones con override (el nivel 2 gana) — es el error clásico a evitar.

## Gráficos — estado y dirección

El motor de gráficos (`crear_grafico(df, conf)` + `_resolver()` en
`graficos.py`) es la pieza más madura: genera figuras Plotly desde una
CONFIGURACIÓN (dict con tipo/x/y/color), no con código repetido. Añadir un
gráfico = añadir una config, no una función. Esto es lo que hace que mejorar
los gráficos escale: se mejora el motor una vez y todos mejoran a la vez.

Dos conceptos de color DISTINTOS (no mezclar):
- **Color de interfaz** (fondos, grillas, texto) → `tema.py`, sección normal.
- **Color de dato / serie** (barras, escalas, semáforos) → `tema.py`, sección
  `PALETA_SERIES` aparte. Hoy están sueltos en `graficos.py` (`#6c5ce7` x8,
  `"blues"` x6, la paleta `PALETA_CALLAI`, la escala semáforo
  `['#ef4444','#f97316','#16a34a']`); se centralizan en la Fase 2 de gráficos.

Techo actual: la estructura es potente, pero la superficie es convencional
(tooltips de fábrica, sin formato de soles, casi sin interactividad). Subir
el nivel NO requiere reescribir: se le añaden capacidades al motor (ver Fase 5).

## Refactor en curso (fases)

- [x] Fase 1 — `tema.py` + este documento (aditivo, riesgo cero).
- [x] Fase 1.5 — Propiedad de contenedores: jerarquía de layout documentada,
      comentarios cruzados en `estilos.py`/`navegacion.py`, y eliminado el
      código muerto `inject_boton_calendario_ajuste` (tercer "dueño" de la
      píldora de fecha).
- [ ] Fase 2 — Reemplazar colores pegados por constantes de `tema.py`
      (mecánico; verificar CSS/figuras resultantes idénticos). Se hace
      fichero por fichero. En `graficos.py`, esta fase ADEMÁS mueve los
      colores de serie a `PALETA_SERIES` en `tema.py` (una sola pasada,
      no dos).
- [ ] Fase 3 — Trocear `renderizar_aggrid_desktop` (~1,146 líneas) en
      helpers: `_construir_opciones_grid()`, `_css_base()`,
      `_css_requerimientos()`, `_css_ajuste()`.
- [ ] Fase 4 — Mover el CSS del grid a `estilos_grid.py`.
- [ ] Fase 5 — Profundidad de gráficos (se apoya en el motor por config):
      `hovertemplate` con formato de soles (S/ y miles), hover unificado,
      ejes con separador de miles, y `facet` opcional para comparativas.
      Un solo lugar de definición del "look" de figura → mejora todos.
