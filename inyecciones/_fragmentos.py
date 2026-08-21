"""inyecciones._fragmentos - CSS y JS compartido por varias inyecciones.

_JS_BUSCAR_IFRAME_FN es el localizador de iframes que usan las inyecciones
que tienen que alcanzar el documento del AgGrid. Los _*_CSS_* son bloques de
estilo que se insertan dentro de ese iframe.

No formatear con % en estas plantillas (arquitectura.md #3): el CSS legitimo
trae % y choca con el operador de Python.
"""

from tema import (
    ACENTO, ACENTO_FUERTE,
    BLANCO, EXIT_HOVER,
    GRIS_BORDE, GRIS_FONDO, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_SUAVE,
    ICON_MUTED, LAVANDA_CABECERA_GRUPO, LAVANDA_FONDO,
    LAVANDA_FOCO, SCROLL_THUMB, TEXTO_PRINCIPAL,
)


_JS_BUSCAR_IFRAME_FN = """
        function buscarIframe() {
            var frames = doc.querySelectorAll('iframe[src*="st_aggrid"]');
            if (!frames.length) frames = doc.querySelectorAll('iframe');
            for (var i = 0; i < frames.length; i++) {
                try {
                    var d = frames[i].contentDocument;
                    if (d && d.querySelector('.ag-root-wrapper')) return frames[i];
                } catch(e) {}
            }
            return null;
        }
"""
_PAG_CSS_BASE = f"""
.ag-status-bar {{
  background: {GRIS_FONDO} !important;
  border-top: 1px solid {GRIS_BORDE} !important;
  color: {GRIS_TEXTO} !important;
  padding: 4px 16px !important;
  font-size: 12px !important;
  background-image: none !important;
  background-color: {GRIS_FONDO} !important;
}}
.ag-status-bar * {{
  background-image: none !important;
}}
.ag-status-name-value {{ color: {GRIS_TEXTO} !important; font-size: 12px !important; }}
.ag-status-name-value-value {{ color: {TEXTO_PRINCIPAL} !important; font-weight: 600 !important; }}

/* Barra INTEGRADA al pie de la tabla: mismo marco que el grid (sin
   tarjeta aparte), solo un divisor arriba y las esquinas inferiores
   del propio card. */
.ag-paging-panel {{
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  background: {BLANCO} !important;
  background-image: none !important;
  border: none !important;
  border-top: 1px solid {GRIS_BORDE} !important;
  border-radius: 0 0 12px 12px !important;
  margin-top: 0 !important;
  padding: 8px 16px !important;
  min-height: 44px !important;
  font-size: 12px !important;
  color: {ICON_MUTED} !important;
}}

/* AUTO-OCULTAR con una sola página: si ‹ y › están ambos deshabilitados
   no hay nada que paginar. Cubre la paginación nativa y la v2 (que solo
   mueve los botones fuera de pantalla; sus estados disabled siguen
   actualizándose). AgGrid moderno marca los botones con data-ref; se
   mantiene la variante ref por compatibilidad con versiones previas. */
.ag-paging-panel:has([ref="btPrevious"].ag-disabled):has([ref="btNext"].ag-disabled),
.ag-paging-panel:has([data-ref="btPrevious"].ag-disabled):has([data-ref="btNext"].ag-disabled) {{
  display: none !important;
}}

.ag-paging-page-size {{ order: -1 !important; margin-right: auto !important; }}
.ag-paging-page-size .ag-label {{ color: {ICON_MUTED} !important; font-size: 12px !important; margin-right: 6px !important; }}
.ag-paging-page-size .ag-select, .ag-paging-page-size select {{
  border: 1px solid {GRIS_BORDE} !important;
  border-radius: 6px !important;
  background: {BLANCO} !important;
  color: {TEXTO_PRINCIPAL} !important;
  font-size: 12px !important;
  padding: 2px 6px !important;
}}

.ag-filter-toolpanel {{
  border: none !important;
  border-radius: 0 !important;
  margin: 0 !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
}}
.ag-filter-toolpanel::-webkit-scrollbar {{ width: 8px; }}
.ag-filter-toolpanel::-webkit-scrollbar-track {{ background: transparent; }}
.ag-filter-toolpanel::-webkit-scrollbar-thumb {{ background: {SCROLL_THUMB}; border-radius: 4px; }}
"""
_PAG_CSS_NATIVA = f"""
.ag-paging-row-summary-panel {{ color: {ICON_MUTED} !important; font-size: 12px !important; }}
.ag-paging-row-summary-panel-number {{ color: {TEXTO_PRINCIPAL} !important; font-weight: 600 !important; }}

.ag-paging-description {{ color: {ICON_MUTED} !important; font-size: 12px !important; }}

.ag-paging-button {{
  width: 28px !important; height: 28px !important;
  border: 1px solid {GRIS_BORDE} !important;
  border-radius: 6px !important;
  background: {BLANCO} !important;
  color: {GRIS_TEXTO} !important;
  font-size: 14px !important;
  margin: 0 2px !important;
  cursor: pointer !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  transition: all 0.15s ease !important;
  position: relative !important;
}}
.ag-paging-button span, .ag-paging-button .ag-icon {{
  display: none !important;
}}
.ag-paging-button[ref="btFirst"]::after,
.ag-paging-button[data-ref="btFirst"]::after  {{ content: "«" !important; }}
.ag-paging-button[ref="btPrevious"]::after,
.ag-paging-button[data-ref="btPrevious"]::after {{ content: "‹" !important; }}
.ag-paging-button[ref="btNext"]::after,
.ag-paging-button[data-ref="btNext"]::after   {{ content: "›" !important; }}
.ag-paging-button[ref="btLast"]::after,
.ag-paging-button[data-ref="btLast"]::after   {{ content: "»" !important; }}
.ag-paging-button::after {{
  font-size: 16px !important;
  line-height: 1 !important;
  color: {GRIS_TEXTO} !important;
}}
.ag-paging-button:hover:not(.ag-disabled) {{
  background: {LAVANDA_FONDO} !important;
  border-color: {LAVANDA_FOCO} !important;
}}
.ag-paging-button:hover:not(.ag-disabled)::after {{
  color: {ACENTO_FUERTE} !important;
}}
.ag-paging-button.ag-disabled {{
  border-color: {GRIS_LINEA} !important;
  background: {GRIS_FONDO} !important;
  cursor: default !important;
  opacity: 0.4 !important;
}}
"""
_PGV2_CSS_IFRAME = f"""
.ag-paging-panel {{ position: relative !important; justify-content: center !important; }}
.ag-paging-panel .ag-paging-page-size {{
  position: absolute !important; left: 16px !important;
  top: 50% !important; transform: translateY(-50%) !important; margin: 0 !important;
}}
.ag-paging-panel .ag-paging-row-summary-panel,
.ag-paging-description,
.ag-paging-button {{
  position: absolute !important; left: -9999px !important; width: 1px !important;
  height: 1px !important; overflow: hidden !important;
}}
#pgv2 {{
  display: inline-flex; align-items: center; gap: 14px; margin: 0 auto;
  font: 13px -apple-system, BlinkMacSystemFont, sans-serif; color: {ICON_MUTED};
}}
#pgv2 .pgv2-pages {{ display: inline-flex; align-items: center; gap: 6px; }}
#pgv2 button {{
  min-width: 30px; height: 30px; padding: 0 8px;
  border: 1px solid {GRIS_BORDE};
  border-radius: 8px; background: {BLANCO}; color: {GRIS_TEXTO}; font-size: 13px;
  cursor: pointer; display: inline-flex; align-items: center;
  justify-content: center; transition: all .15s;
}}
#pgv2 button:hover:not(:disabled) {{
  background: {LAVANDA_FONDO};
  border-color: {LAVANDA_FOCO};
  color: {ACENTO_FUERTE};
}}
#pgv2 button:disabled {{ opacity: .4; cursor: default; }}
#pgv2 button.pgv2-on {{
  background: {ACENTO_FUERTE};
  border-color: {ACENTO_FUERTE};
  color: {BLANCO}; font-weight: 500;
}}
#pgv2 .pgv2-dots {{ color: {GRIS_TEXTO_SUAVE}; padding: 0 2px; }}
#pgv2 .pgv2-jump {{ display: inline-flex; align-items: center; gap: 7px; color: {GRIS_TEXTO}; }}
#pgv2 .pgv2-jump input {{
  width: 48px; height: 30px;
  border: 1px solid {GRIS_BORDE}; border-radius: 8px;
  text-align: center; color: {TEXTO_PRINCIPAL}; font-size: 13px;
  background: {BLANCO}; outline: none; -moz-appearance: textfield;
}}
#pgv2 .pgv2-jump input:focus {{
  border-color: {ACENTO_FUERTE};
  box-shadow: 0 0 0 2px {LAVANDA_CABECERA_GRUPO};
}}
#pgv2 .pgv2-jump input::-webkit-outer-spin-button,
#pgv2 .pgv2-jump input::-webkit-inner-spin-button {{
  -webkit-appearance: none; margin: 0;
}}
"""
_FS_CSS_IFRAME = f"""
html.fs-activo, html.fs-activo body {{
  margin: 0 !important;
  height: 100vh !important;
  min-height: 100vh !important;
  max-height: 100vh !important;
  overflow: hidden !important;
}}
/* ANCHO, no solo alto. Hasta 2026-08-21 este bloque forzaba `height:
   100vh` en toda la cadena y NUNCA tocaba el ancho: st_aggrid le fija al
   contenedor del grid un ancho en PIXELES, medido al montar contra la
   tarjeta donde vive. Resultado, reportado con captura: en pantalla
   completa la tabla ocupaba los 1365px de alto pero el grid seguia en los
   ~474px de la tarjeta angosta -- media pantalla vacia a la derecha y las
   columnas igual de cortadas que antes. Medido en el navegador: el body
   del iframe pasaba a 1600px y `.ag-root-wrapper` se quedaba en 474.
   Con el ancho suelto, el ResizeObserver de AG Grid dispara
   `gridSizeChanged` y ahi re-reparte las columnas quien lo haya declarado
   (ver `onGridSizeChanged` en graficos/compras/documentos_sunat.py). Las
   dos mitades hacen falta: sin el ancho no hay evento, y sin el handler
   hay lienzo pero las columnas no se mueven. */
html.fs-activo #root {{
  height: 100vh !important;
  width: 100vw !important;
  overflow: hidden !important;
}}
html.fs-activo #root > div {{
  height: 100vh !important;
  width: 100% !important;
}}
html.fs-activo #root [class*="ag-theme-"]:not(.ag-dnd-ghost):not(.ag-popup) {{
  height: 100vh !important;
  width: 100% !important;
}}
html.fs-activo .ag-dnd-ghost,
html.fs-activo .ag-popup,
html.fs-activo body > [class*="ag-theme-"]:not(#gridContainer) {{
  height: auto !important;
  min-height: 0 !important;
}}
html.fs-activo .ag-root-wrapper {{
  height: 100% !important; width: 100% !important; border-radius: 0 !important;
}}
html.fs-activo .ag-column-panel,
html.fs-activo .ag-filter-toolpanel {{
  height: 100% !important; overflow-y: auto !important;
}}
html.fs-activo .ag-column-drop-vertical {{
  flex: 0 0 auto !important;
  min-height: 3.2em !important;
}}
/* ── ⛶ integrado en el riel de pestañas ── */
/* El tema de AgGrid da al riel un padding-top de 24px que empujaba el ⛶
   hacia abajo; sin él, el botón queda al tope, alineado con la cabecera. */
.ag-side-buttons {{ padding-top: 0 !important; }}
#aggrid-maximize-btn {{
  width: 100%;
  height: 36px;
  border: none;
  border-bottom: 1px solid {ACENTO};
  background: {LAVANDA_FONDO};
  color: {ACENTO_FUERTE};
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  writing-mode: horizontal-tb;
  line-height: 1;
  transition: background .15s, color .15s;
}}
#aggrid-maximize-btn:hover {{
  background: {LAVANDA_FONDO};
  color: {ACENTO_FUERTE};
}}
/* En fullscreen ocultamos el ⛶ (ya hay ✕ de salida). */
html.fs-activo #aggrid-maximize-btn {{ display: none; }}
/* ── Botón de salida ✕ ── */
#aggrid-exit-fs-btn {{
  position: fixed;
  top: 12px;
  right: 44px;
  z-index: 99999;
  width: 30px;
  height: 30px;
  border: 1px solid {GRIS_TEXTO};
  border-radius: 6px;
  background: {TEXTO_PRINCIPAL};
  color: {GRIS_FONDO};
  font-size: 14px;
  cursor: pointer;
  display: none;
  align-items: center;
  justify-content: center;
  line-height: 1;
}}
html.fs-activo #aggrid-exit-fs-btn {{ display: flex; }}
#aggrid-exit-fs-btn:hover {{ background: {EXIT_HOVER}; }}
"""
