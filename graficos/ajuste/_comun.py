"""graficos.ajuste._comun - helpers compartidos del dashboard de Ajuste.

Layout propio del rail, formato de fechas de corte y calculo de periodos.
Lo que usan dos o mas vistas del dashboard; nada de esto dibuja nada por
si solo.

Los "cortes" NO son calendario fijo: son rachas de fechas consecutivas
(ver _cortes_por_racha), porque un inventario se abre y se cierra en
dias sueltos. De ahi que tengan su propio calculo en vez de reusar
_periodo_serie de compras.
"""


import pandas as pd

from graficos.base import (
    _layout,
)
# _periodo_serie vive en graficos/compras/_comun.py; se reusa desde acá vía
# graficos.compras (que ya la re-exporta para test_graficos.py) en vez de
# duplicar el cálculo de granularidad Semana/Mes (Corte tiene su propio
# cálculo, ver _cortes_por_racha: no es calendario fijo, son rachas).
from graficos.compras import _periodo_serie


def _layout_aj(**overrides):
    """`_layout` con el look del estándar del rail (igual que Compras).

    Solo cambia dos cosas respecto al `_layout` genérico para que los gráficos
    de Ajuste combinen con la tarjeta como en Compras:
      · plot_bgcolor TRANSPARENTE — funde con el fondo de la tarjeta en vez de
        pintar una caja blanca dentro.
      · grilla del eje X oculta (Compras solo conserva la del eje Y).
    La paleta ya es común (PALETA_SERIES). El color SEMÁNTICO de cada gráfico
    (verde/rojo del waterfall, colorscale del mapa de calor, etc.) se conserva:
    es propio del tipo de gráfico, no del tema. No se toca el `_layout`
    compartido para no restilizar Ventas/Inventario/Receta."""
    lay = _layout(**overrides)
    lay["plot_bgcolor"] = "rgba(0,0,0,0)"
    _xaxis = dict(lay.get("xaxis", {}))
    _xaxis["showgrid"] = False
    lay["xaxis"] = _xaxis
    return lay


_MESES_ABR_ES = ("ene", "feb", "mar", "abr", "may", "jun",
                 "jul", "ago", "set", "oct", "nov", "dic")


def _fmt_corte(fecha):
    """'02-ago' en vez de '02-Aug' — strftime('%b') usa el locale del
    sistema (inglés en Streamlit Cloud), y esta app es en español."""
    _ts = pd.Timestamp(fecha)
    return f"{_ts.day:02d}-{_MESES_ABR_ES[_ts.month - 1]}"


_CORTE_MAX_SALTO_DIAS = 4
"""Una sesión de conteo real puede durar varios días NO estrictamente
seguidos (fin de semana de por medio, un área que se retoma dos días
después). Mientras el salto al día siguiente con movimiento sea ≤ a
esto, sigue siendo el MISMO corte; más que esto, arranca uno nuevo.
Número fijado a pedido explícito (no es un ajuste fino, es una regla de
negocio) — si cambia, es UNA constante."""


def _etiqueta_corte(inicio, fin):
    """'1-4 ago' si el corte no cruza de mes; '30 jul - 2 ago' si cruza.
    Un corte de un solo día no muestra rango: '15 ago'."""
    _di, _mi = inicio.day, inicio.month
    _df, _mf = fin.day, fin.month
    if inicio == fin:
        return f"{_di} {_MESES_ABR_ES[_mi - 1]}"
    if _mi == _mf:
        return f"{_di}-{_df} {_MESES_ABR_ES[_mi - 1]}"
    return f"{_di} {_MESES_ABR_ES[_mi - 1]} - {_df} {_MESES_ABR_ES[_mf - 1]}"


def _cortes_por_racha(fechas):
    """Agrupa fechas en "cortes": rachas de días con movimiento donde el
    salto de un día al siguiente es ≤ _CORTE_MAX_SALTO_DIAS (ver esa
    constante). Reemplaza a "Día" -- una sesión de conteo real casi nunca
    es un solo día suelto, y agrupar por calendario partía una sesión de
    varios días en columnas sin relación entre sí.
    Devuelve (clave, etiqueta) igual que las demás granularidades, para
    que _armar_tabla_pivote_ajuste no necesite saber la diferencia -- a
    diferencia de Semana/Mes (donde cada fecha resuelve su clave sola),
    acá hace falta la lista COMPLETA de fechas únicas primero para saber
    dónde están los saltos, así que se arma un mapa fecha→(clave,
    etiqueta) y se aplica con `.map()`."""
    dias = fechas.dt.normalize()
    unicos = sorted(dias.dropna().unique())
    if not unicos:
        return dias.astype(str), dias.astype(str)

    rachas = []
    actual = [unicos[0]]
    for d in unicos[1:]:
        salto = (pd.Timestamp(d) - pd.Timestamp(actual[-1])).days
        if salto > _CORTE_MAX_SALTO_DIAS:
            rachas.append(actual)
            actual = [d]
        else:
            actual.append(d)
    rachas.append(actual)

    mapa_clave, mapa_etq = {}, {}
    for i, racha in enumerate(rachas):
        _clave = f"corte_{i:03d}"
        _etq = _etiqueta_corte(pd.Timestamp(racha[0]), pd.Timestamp(racha[-1]))
        for d in racha:
            mapa_clave[d] = _clave
            mapa_etq[d] = _etq

    return dias.map(mapa_clave), dias.map(mapa_etq)


def _periodo_pivote_ajuste(fechas, gran):
    """Clave ordenable + etiqueta corta de periodo para la tabla dinámica
    de Ajuste, en las 3 granularidades del selector (Corte/Semana/Mes).
    Corte agrupa por rachas de días (`_cortes_por_racha`); Semana/Mes
    reusan `_periodo_serie` (graficos/compras/_comun.py, re-exportada vía
    graficos.compras — "reusar desde ahí, no duplicar" per
    arquitectura.md) para la clave, con etiqueta propia porque acá el mes
    va abreviado en español (_MESES_ABR_ES)."""
    if gran == "Corte":
        return _cortes_por_racha(fechas)
    clave = _periodo_serie(fechas, gran)
    if gran == "Semana":
        etiqueta = "S" + fechas.dt.isocalendar().week.astype(str).str.zfill(2)
    else:
        etiqueta = fechas.dt.month.map(lambda m: _MESES_ABR_ES[m - 1])
    return clave, etiqueta
