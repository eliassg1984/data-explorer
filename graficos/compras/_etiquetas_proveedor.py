"""graficos.compras._etiquetas_proveedor - texto de las barras del drill.

Formato de las etiquetas que Plotly dibuja SOBRE cada barra del drill de
Proveedor: monto compacto, variacion vs el periodo anterior, documentos,
participacion en el periodo y abreviacion del nombre del proveedor.

Vivian como funciones anidadas dentro de _compras_proveedor_drill; se
sacaron el 2026-08-08. Son las candidatas naturales a salir primero
porque casi no dependian del estado del drill: `_fmt_k` y
`_abrev_nombre` ya eran puras, y `_etiqueta_serie` solo cerraba sobre dos
valores (`_gran_suffix` y `_lab_compacta`) que ahora recibe como
parametros explicitos. Al ser puras, se pueden probar con asserts de
valor sin levantar Streamlit -- ver test_graficos.py.

POR QUE se dibujan en el servidor y no con CSS: es texto que Plotly
rasteriza dentro de la figura, asi que no hay media query que valga. El
llamador decide cuanto abreviar a partir del ancho estimado por barra
(que depende del User-Agent, ver graficos.base._es_movil).
"""

import pandas as pd

# Verde/rojo de la variacion. Son de DATO (sube/baja), no de interfaz: no
# salen de tema.py a proposito -- van dentro del <span> que se manda a
# Plotly, y su par en la app son los verdes/rojos de celda del grid.
_VERDE_SUBE = "#0F6E56"
_ROJO_BAJA = "#A32D2D"
_GRIS_PIE = "#6b6b78"

# Palabras que no aportan al abreviar un nombre de proveedor.
_RUIDO_RAZON_SOCIAL = frozenset({
    "de", "del", "la", "el", "los", "las", "y", "e",
    "s.a.c.", "sac", "s.a.", "sa", "e.i.r.l.", "eirl",
})

_SUFIJO_GRAN = {
    "Día": "del Día",
    "Semana": "de la Semana",
    "Mes": "del Mes",
    "Año": "del Año",
}


def sufijo_granularidad(gran):
    """'Mes' -> 'del Mes'. Sufijo de la linea '% del ...' de la etiqueta.

    El usuario ve el nombre del segmento directamente, sin el generico
    'periodo' (que es el fallback si llega una granularidad desconocida).
    """
    return _SUFIJO_GRAN.get(gran, "del período")


def fmt_k(v):
    """Monto compacto para etiquetas angostas: S/ 4.0k, S/ 1.2M."""
    if v >= 1_000_000:
        return f"S/ {v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"S/ {v / 1_000:.1f}k"
    return f"S/ {v:.0f}"


def abrev_nombre(nombre, max_chars):
    """Abrevia el nombre del proveedor segun el ancho disponible.
    - max<2: vacio (barra muy chica)
    - 2:      2 primeras iniciales de palabras
    - 3-5:    iniciales de todas las palabras significativas
    - 6-14:   primera palabra
    - >=15:   nombre completo (truncado con … si excede)
    """
    s = str(nombre).strip()
    if max_chars < 2 or not s:
        return ""
    if len(s) <= max_chars:
        return s
    words = [w for w in s.split()
             if w and w.lower() not in _RUIDO_RAZON_SOCIAL]
    if max_chars <= 5:
        ini = "".join(w[0].upper() for w in words[:max_chars])
        return ini[:max_chars] if len(ini) >= 2 else s[:max_chars]
    if max_chars <= 14 and words:
        first = words[0]
        return first if len(first) <= max_chars else first[:max_chars - 1] + "…"
    return s[:max_chars - 1] + "…"


def etiqueta_serie(vals, gran_suffix, compacta=False,
                   pct_periodo=None, docs=None):
    """Texto por barra: total SIEMPRE encima + variacion vs el periodo
    ANTERIOR del mismo proveedor (▲ verde sube / ▼ rojo baja) + cantidad
    de documentos + % de participacion en el periodo. La 1a barra no
    tiene anterior → solo total + docs + %. Barras en 0 → sin etiqueta.

    gran_suffix: lo que devuelve sufijo_granularidad() para la
        granularidad activa. Antes se leia por closure.
    compacta: omite las dos lineas grises del pie. El llamador la activa
        cuando hay un proveedor en foco (el chart baja a 180px y no hay
        alto) o cuando las barras son angostas (bajo ~78px estimados,
        Plotly recortaria la etiqueta de 4 lineas dejando solo el valor).
        En ambos casos docs y % siguen estando en el hover.
    pct_periodo: lista del mismo largo que vals con el % que la barra
        representa del total del segmento (0-100). None lo omite.
    docs: lista del mismo largo que vals con la cantidad de documentos
        (comprobantes unicos) que respaldan cada barra. None lo omite.
    """
    if compacta:
        docs, pct_periodo = None, None
    _txt = []
    for j, v in enumerate(vals):
        if v <= 0:
            _txt.append("")
            continue
        linea = fmt_k(v)
        if j > 0 and vals[j - 1] > 0:
            chg = (v - vals[j - 1]) / vals[j - 1] * 100
            flecha = "▲" if chg >= 0 else "▼"
            col = _VERDE_SUBE if chg >= 0 else _ROJO_BAJA
            linea += (f"<br><span style='color:{col}'>"
                      f"{flecha}{abs(chg):.0f}%</span>")
        # Tercera linea (gris chico): docs + % del segmento.
        _foot = []
        if docs is not None:
            _n = docs[j]
            if _n is not None and not pd.isna(_n) and _n > 0:
                _n = int(_n)
                _foot.append(f"{_n} doc" if _n == 1 else f"{_n} docs")
        if pct_periodo is not None:
            _pp = pct_periodo[j]
            if _pp is not None and not pd.isna(_pp):
                _foot.append(f"{_pp:.0f}% {gran_suffix}")
        if _foot:
            linea += "".join(
                f"<br><span style='color:{_GRIS_PIE};font-size:11.5px'>{_p}</span>"
                for _p in _foot
            )
        _txt.append(linea)
    return _txt
