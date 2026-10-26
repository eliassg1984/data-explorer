"""Presentación móvil compartida de las piezas v2, dentro de su shadow root.

No cambia datos, firmas públicas ni eventos del reporte. La adaptación de
controles se monta después del render original y se revierte en escritorio.
"""

from pathlib import Path
import re

_DIR = Path(__file__).parent
_CSS = (_DIR / "movil.css").read_text(encoding="utf-8")
_JS = (_DIR / "movil.js").read_text(encoding="utf-8")
_EXPORT = re.compile(r"export\s+default\s+function\s*\(")


def css_movil(css):
    """Añade sólo reglas bajo el breakpoint móvil a la hoja de cada pieza."""
    return css + "\n" + _CSS


def js_movil(js):
    """Conserva el montaje y su retorno; observa sus renders posteriores."""
    if not _EXPORT.search(js):
        return js
    original = _EXPORT.sub("function __movilRenderOriginal(", js, count=1)
    return original + "\n" + _JS + """
export default function(component) {
  const resultado = __movilRenderOriginal(component);
  const limpiarMovil = __movilAdaptar(component.parentElement);
  return () => {
    if (typeof resultado === 'function') resultado();
    if (limpiarMovil) limpiarMovil();
  };
}
"""
