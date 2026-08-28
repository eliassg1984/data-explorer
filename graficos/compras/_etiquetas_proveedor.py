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

import re

import pandas as pd

from utils import fmt_k  # noqa: F401 -- reexport, lo consume test_graficos.py (_ep.fmt_k)

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

# ── Vocabulario de `nombre_propio` ──────────────────────────────────
# Los dos conjuntos salen de CONTAR los 767 proveedores de compras.parquet
# (2026-08-28), no de imaginar que podria aparecer. El 99.9% de los nombres
# llega TODO EN MAYUSCULAS desde el ERP.
#
# Formas juridicas SIN puntos. Las que llevan punto (S.A.C. 222 veces,
# E.I.R.L. 79, S.A. 32, S.R.L. 14, S.A.A. 3, S.C.R.L. 2...) no necesitan
# lista: se reconocen por el punto.
_SIGLAS_RAZON_SOCIAL = frozenset({
    "SAC", "SA", "SAA", "SRL", "SRLTDA", "SCRL", "EIRL", "LTDA",
})

# Lo que va en minuscula DENTRO de un nombre propio: preposiciones y
# conjunciones. Los ARTICULOS no estan, a proposito: en castellano el
# articulo que forma parte del nombre lleva mayuscula ("Agricola La
# Chacra"), la preposicion no ("Luz del Sur", "Seguros y Reaseguros").
# Medido sobre los mismos 767: de 34, y 26, del 18, e 4, en 3.
_PALABRAS_MENORES = frozenset({"de", "del", "y", "e", "en"})

# Rachas de LETRAS dentro de un token, para capitalizar cada una por
# separado. `[^\W\d_]` es "alfabetico unicode" -- \w menos digitos y menos
# guion bajo -- asi que la Ñ y las tildes entran ("COMPAÑIA" -> "Compañia").
#
# Hace falta porque el separador NO siempre es un espacio, y con datos
# reales eso da dos resultados feos: "E&R" -> "E&r" y "(PERU)" -> "(peru)"
# (ahí el primer caracter es "(", y ponerlo en mayuscula no hace nada
# mientras el resto se va a minuscula). Con las rachas salen "E&R" y
# "(Peru)". Vistos los dos en compras.parquet.
_RACHA_LETRAS = re.compile(r"[^\W\d_]+")


def _capitalizar_rachas(token):
    return _RACHA_LETRAS.sub(
        lambda m: m.group(0)[0].upper() + m.group(0)[1:].lower(), token)


def nombre_propio(nombre):
    '''"DOBLE G REPRESENTACIONES S.A.C." -> "Doble G Representaciones S.A.C."

    Los nombres de proveedor llegan gritados desde el ERP y una tabla entera
    de mayusculas se lee como un bloque. Esto los baja a capitalizacion de
    nombre propio, que es lo que se pidio el 2026-08-28 ("minuscula pero
    como nombre propio").

    POR QUE NO ES CSS, que fue el primer intento: `text-transform:
    lowercase` deja "doble g representaciones s.a.c." y `capitalize` NO baja
    el resto de la palabra, asi que sobre un texto que YA viene en
    mayusculas no hace absolutamente nada. Y las dos juntas tampoco: sobre
    un mismo texto se aplica una sola declaracion de `text-transform`;
    encadenarlas pediria un elemento por palabra.

    POR QUE NO SE TOCA EL DATO: el nombre es la clave con la que el drill
    compara -- el foco del ranking, el popover de proveedores y el
    `dict(zip(...))` que le da color a la serie de Evolucion. Esto es para
    MOSTRAR; el llamador guarda el original al lado (`proveedor.py`, columna
    oculta `_prov_raw`).

    Los casos, EN ESTE ORDEN (el orden importa: "Y" es a la vez conjuncion
    y una inicial posible, y gana la conjuncion cuando no es la primera):
      · token con punto            -> tal cual  ("S.A.C.", "E.I.R.L.", "Y.R.")
      · token en las siglas        -> tal cual  ("SAC", "EIRL")
      · palabra menor, no primera  -> minuscula ("de", "del", "y")
      · resto                      -> cada racha de letras, Capitalizada

    No hay caso especial para las letras sueltas: una racha de un solo
    caracter ya sale en mayuscula sola, que es lo que corresponde tanto a
    la inicial de una persona como a las siglas partidas que hay en los
    datos ("LINDAS TELAS S A").

    Lo que esto NO puede hacer, y no se intento: reconocer un acronimo sin
    puntos que no este en la lista. "PCF PERU" sale "Pcf Peru" y "EY
    ASESORES" sale "Ey Asesores". Distinguirlos de un apellido corto pide
    un diccionario, no una regla.
    '''
    s = str(nombre).strip()
    if not s:
        return s
    salida = []
    for i, t in enumerate(s.split()):
        if "." in t or t.upper() in _SIGLAS_RAZON_SOCIAL:
            salida.append(t)
        elif i and t.lower() in _PALABRAS_MENORES:
            salida.append(t.lower())
        else:
            salida.append(_capitalizar_rachas(t))
    return " ".join(salida)

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
