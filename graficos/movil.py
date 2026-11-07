"""Presentación compartida de las piezas v2, dentro de su shadow root.

No cambia datos, firmas públicas ni eventos del reporte. La adaptación de
controles se monta después del render original y se revierte en escritorio.
Las pestañas principales comparten también la tipografía de Diferencias.
"""

from pathlib import Path
import re

_DIR = Path(__file__).parent
_CSS = (_DIR / "movil.css").read_text(encoding="utf-8")
_PESTANAS = (_DIR / "pestanas.css").read_text(encoding="utf-8")
_JS = (_DIR / "movil.js").read_text(encoding="utf-8")
_EXPORT = re.compile(r"export\s+default\s+function\s*\(")


def css_movil(css):
    """Compone las pestañas de escritorio y la adaptación móvil de cada pieza."""
    return css + "\n" + _PESTANAS + "\n" + _CSS


def js_movil(js):
    """Conserva el montaje y su retorno; observa sus renders posteriores."""
    if not _EXPORT.search(js):
        return js
    original = _EXPORT.sub("function __movilRenderOriginal(", js, count=1)
    return original + "\n" + _JS + """
export default function(component) {
  const resultado = window.__retorno
    ? window.__retorno.montar(component, __movilRenderOriginal)
    : __movilRenderOriginal(component);
  const limpiarMovil = __movilAdaptar(component.parentElement);
  return () => {
    if (typeof resultado === 'function') resultado();
    if (limpiarMovil) limpiarMovil();
  };
}
"""
