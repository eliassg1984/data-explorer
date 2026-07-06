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

1. **Colores solo desde `tema.py`.** Nunca pegar `#xxxxxx` en otro fichero.
   Motivo: había 100+ colores repetidos a mano; cambiar la marca era
   imposible sin desentonar algo.

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

## Refactor en curso (fases)

- [x] Fase 1 — `tema.py` + este documento (aditivo, riesgo cero).
- [x] Fase 1.5 — Propiedad de contenedores: jerarquía de layout documentada,
      comentarios cruzados en `estilos.py`/`navegacion.py`, y eliminado el
      código muerto `inject_boton_calendario_ajuste` (tercer "dueño" de la
      píldora de fecha).
- [ ] Fase 2 — Reemplazar colores pegados por constantes de `tema.py`
      (mecánico; verificar CSS resultante idéntico).
- [ ] Fase 3 — Trocear `renderizar_aggrid_desktop` (1,146 líneas) en
      helpers: `_construir_opciones_grid()`, `_css_base()`,
      `_css_requerimientos()`, `_css_ajuste()`.
- [ ] Fase 4 — Mover el CSS del grid a `estilos_grid.py`.
