"""
graficos.ventas_alcance — el filtro «Venta» de cada tarjeta de Ventas
(regla #755).

Desde el 2026-10-29 Grupo y Sub Grupo dejaron el «Filtros» de la franja:
una elección arriba movía TODAS las vistas, y mirar los vinos en el Mix
dejaba a «Venta por Periodo» sin el total de lo vendido. Ahora cada tarjeta
trae su filtro, con el mismo dibujo en todas, y lo que se elige en una no
toca a las otras. Boceto aprobado:
https://claude.ai/artifact/NbofNqpVLXrz5ZQvCPe3Us (pantallas 5 y 6).

Los grupos van en tres BLOQUES:

  · Carta    — todo lo que no es de los otros dos (un grupo nuevo del POS
               cae acá, que es lo más probable).
  · Eventos  — los menús de evento.
  · Otros    — Venta interna, Otros (descorche, vales, desechos,
               donaciones, movilidad) y No Show.

Y tres ATAJOS: toda la venta, Carta + Eventos y sólo carta. «Como en
Costos» NO es un atajo fijo: Costos suma Venta interna sólo si su casilla
está marcada (viene apagada), así que un atajo con los grupos de
`costo_ventas` mentía para quien no la marcó. Lo trae el enlace de Costos,
con las casillas de ese momento (`extra`), y dura lo que dure ese pedido.

Cada tarjeta dice con cuál ABRE (`abre`), y la ✕ del botón vuelve ahí:

  · Venta por Periodo — toda la venta («cuánto se vendió»).
  · Mix de carta      — Carta + Eventos («cuánto por grupo»).

La cuenta y el dibujo viven en `ventas_alcance.js` + `.css`, que cada pieza
antepone a lo suyo: no es una pieza aparte, es un módulo
(`window.VentasAlcance`). Lo vigila `test_ventas_alcance.py`.
"""

from pathlib import Path

CARTA, EVENTOS, OTROS = "Carta", "Eventos", "Otros"
BLOQUES = (CARTA, EVENTOS, OTROS)

_EVENTOS = frozenset({"EVENTOS"})
_OTROS = frozenset({"VENTA INTERNA", "OTROS", "NO SHOW"})
"""Los grupos que no son la carta, por nombre normalizado. Lo que no está
acá es Carta."""

TODA, CARTA_EVENTOS, SOLO_CARTA = "Toda la venta", "Carta + Eventos", "Sólo carta"
COMO_COSTOS = "Como en Costos"
"""El nombre del atajo que trae el enlace de Costos (`datos(extra=…)`)."""

_AQUI = Path(__file__).parent


def _norm(grupo):
    return str(grupo).strip().upper().replace("_", " ")


def bloque(grupo):
    """El bloque de un grupo: Carta, Eventos u Otros."""
    g = _norm(grupo)
    if g in _EVENTOS:
        return EVENTOS
    if g in _OTROS:
        return OTROS
    return CARTA


def datos(grupos, subs=None, abre=TODA, extra=None):
    """Lo que el filtro necesita, para el `data` de una pieza.

    `grupos`: los nombres que trae la tarjeta; `subs`: `{grupo: [subgrupos]}`
    si la tarjeta los tiene (sin ellos, el filtro es sólo de grupos);
    `abre`: el nombre del atajo con que abre la tarjeta; `extra`: atajos
    de un pedido (`[[nombre, lista]]`), que van al final.

    Una elección viaja como lista de `[grupo]` (el grupo entero) o
    `[grupo, subgrupo]`; `None` es toda la venta."""
    gs = sorted({str(g).strip() for g in grupos
                 if g is not None and str(g).strip()}, key=str.lower)
    bloques = [[b, [g for g in gs if bloque(g) == b]] for b in BLOQUES]
    bloques = [b for b in bloques if b[1]]
    sub_de = {}
    for g in gs:
        s = sorted({str(x).strip() for x in (subs or {}).get(g, ())
                    if x is not None and str(x).strip()}, key=str.lower)
        if s:
            sub_de[g] = s

    def lista(pred):
        return [[g] for g in gs if pred(g)]

    atajos = [
        [TODA, None],
        [CARTA_EVENTOS, lista(lambda g: bloque(g) in (CARTA, EVENTOS))],
        [SOLO_CARTA, lista(lambda g: bloque(g) == CARTA)],
    ]
    # Un atajo de un pedido igual a uno fijo no se agrega: dos fichas con
    # lo mismo y distinto nombre confunden, y el botón ya dice cuál es.
    vistos = [None if l is None else sorted(map(tuple, l)) for _, l in atajos]
    for nombre, pedida in extra or ():
        l = [[str(x[0]).strip(), *x[1:]] for x in pedida or ()]
        clave = sorted(map(tuple, (x for x in l if x[0] in gs)))
        if clave == sorted(map(tuple, (x for x in lista(lambda g: True)))):
            continue
        if clave not in vistos:
            atajos.append([nombre, l])
    if abre not in {a[0] for a in atajos}:
        abre = TODA
    return {"bloques": bloques, "subs": sub_de, "atajos": atajos, "abre": abre}


def js():
    """El módulo del navegador, para anteponerlo al `.js` de una pieza."""
    return (_AQUI / "ventas_alcance.js").read_text(encoding="utf-8")


def css():
    """Sus estilos, para sumarlos al `.css` de una pieza (shadow root)."""
    return (_AQUI / "ventas_alcance.css").read_text(encoding="utf-8")
