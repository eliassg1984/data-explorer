"""graficos.compras.vs_ano_pasado - drill "Vs año pasado" de Compras.

Compara el gasto/cantidad/precio de compra contra el MISMO mes del año
anterior, y explica la diferencia: cuánto es porque compramos más y cuánto
porque nos cobraron más caro.

La pantalla son dos filas:

  · arriba, la SERIE mensual (este año vs año pasado) y, al lado, el
    PUENTE precio/cantidad que descompone la diferencia total;
  · abajo, la TABLA de detalle: la misma cuenta abierta ítem por ítem
    (`tablas/compras_vs_ano_pasado.py`). Clic en una fila enfoca la serie
    de arriba en ese ítem.

────────────────────────────────────────────────────────────────────────────
TRES DECISIONES QUE COSTARON DATOS EQUIVOCADOS
────────────────────────────────────────────────────────────────────────────

1. ESTA VISTA NO OBEDECE AL FILTRO DE FECHA DE LA FRANJA (2026-08-24).
   Lo pidió el usuario y tiene razón de fondo: la franja responde "quién
   pesa más ACÁ", que es la pregunta de un ranking; ésta pregunta "cómo
   viene esto contra el año pasado", y un rango de 15 días da un punto
   contra otro punto. Peor: el rango de la franja suele arrancar en el mes
   corriente, así que la vista se pasaba la vida comparando un mes
   incompleto contra un año entero.
   La ventana es ahora un control PROPIO de la tarjeta
   (`graficos/periodo.py`, el mismo que usa la Evolución de Proveedor) y
   arranca en "Todo". La opción `periodo.HEREDA` ("Rango") sigue ahí para
   el que quiera volver a atarla a la franja — no se le quita nada a nadie,
   se cambia el default.

2. LAS COLUMNAS `*_ANO_ANTERIOR` DEL PARQUET NO SE SUMAN. ESTA VISTA YA NO
   LAS USA.
   `VALOR_ANO_ANTERIOR` / `CANTIDAD_ANO_ANTERIOR` no son un dato POR FILA:
   son el total de ESE producto en ESE mes del año pasado, REPETIDO en cada
   fila del producto-mes. Verificado contra R2 el 2026-08-24: constantes en
   los 4.269 grupos producto+mes, y sobre 8.204 pares mes/mes-12 la
   diferencia contra el total real es exactamente 0.
   El código anterior hacía `.sum()` sobre ellas. Eso multiplica el año
   pasado por la cantidad de filas del producto-mes: medido, **x4.9**
   (2025 daba S/ 11.98M contra S/ 2.46M reales). El gráfico "Compra por
   familia: este año vs año anterior" mostraba un año pasado casi cinco
   veces más grande que el real, siempre.
   Se podría arreglar deduplicando, pero el año pasado se calcula mejor
   DESDE EL PROPIO HISTÓRICO: la serie mensual desplazada 12 meses
   (`_con_ano_pasado`). Da lo mismo que la columna donde la columna existe,
   y además cubre lo que la columna no puede: los ítems que se compraban
   el año pasado y este año NO — ésos no tienen fila este año, así que su
   gasto del año pasado se perdía entero. `PRECIO_UNIT_ANO_ANTERIOR`
   tampoco se usa: es un promedio SIMPLE de precios (verificado, coincide
   al 100%), y con promedios simples el puente de abajo no cierra.

3. EL ÚLTIMO MES SUELE ESTAR INCOMPLETO, Y COMPARARLO ENTERO ES UNA CAÍDA
   FALSA.
   El parquet corta el día que se generó (p. ej. el 21). Ese mes contra el
   mes completo del año pasado da siempre una baja que no existe. Por eso
   el mes espejo se recorta al MISMO día del mes (`_mensual(recorte=...)`)
   y la barra parcial se dibuja con trama. Es el único mes que se recorta:
   los demás están completos de los dos lados.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import (
    ACENTO, ERROR, EXITO, GRIS_BORDE, GRIS_TEXTO, LAVANDA_BORDE,
    TEXTO_PRINCIPAL,
)
from graficos.base import _card, _compras_layout, _compras_truncar
from graficos import alturas, periodo
from graficos.compras._comun import COLUMNAS_DRILL, GAP_DRILL
from tablas.compras_vs_ano_pasado import renderizar_detalle_vs_ano_pasado

# Alto de la fila de controles que comparte tarjeta con la serie: métrica
# (izq.) y ventana (der.) en UN renglón. Mismo criterio que
# `alturas.FRANJA_CTRL_EVO` — los píxeles de un control nuevo salen de la
# figura, o la tarjeta crece y su eje X se va debajo del borde.
_FRANJA_VAP = alturas.FRANJA_CTRL_EVO

_CSS = f"""
<style>
/* Franja de controles de la tarjeta: métrica a la izquierda, ventana a la
   derecha, MISMO renglón. El alto total está presupuestado en `_FRANJA_VAP`
   y la figura ya se lo restó — si acá se le agrega aire, hay que mover esa
   constante o la tarjeta empuja su borde. */

/* ── Métrica: tabs de TEXTO, no pastillas ────────────────────────────────
   Mismo lenguaje que las franjas de Ventas y el rail de Proveedor: el
   activo se marca con color y peso, no con un relleno.
   `[data-selected]` y NO `[aria-pressed]`: son single-select, que Streamlit
   marca con role="radio" + data-selected (arquitectura.md #107). */
.st-key-compras_vap_modo [data-testid="stButtonGroup"] {{
    border: none !important;
    background: transparent !important;
}}
/* El gap REAL va en el hijo directo del stButtonGroup (que es display:block),
   no en el grupo — mismo hallazgo que en Ventas y en Proveedor. */
.st-key-compras_vap_modo [data-testid="stButtonGroup"] > div {{
    gap: 14px !important;
}}
.st-key-compras_vap_modo [data-testid="stButtonGroup"] button[role="radio"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 1px 0 !important;
    min-height: 0 !important;
    font-size: 12.5px !important;
    font-weight: 400 !important;
    color: {GRIS_TEXTO} !important;
}}
.st-key-compras_vap_modo [data-testid="stButtonGroup"] button[role="radio"][data-selected] {{
    color: {ACENTO} !important;
    font-weight: 600 !important;
}}

/* ── Ventana propia de la tarjeta: un texto que despliega, no una caja ───
   Misma receta (y mismo hallazgo medido) que `cp_evo_ctrl` en
   `_css_proveedor.py`: la CAJA del selectbox no la lleva ni el
   `stSelectbox` ni el `input`, sino el `div[role="group"]` que hay entre
   los dos, y el ALTO lo fija el `input`. Estilar el ancestro no alcanza.
   OJO: en esta versión de Streamlit el selectbox es `react-aria-ComboBox`,
   NO `div[data-baseweb="select"]` — un selector con baseweb no matchea
   nada y el control sale con su caja de 40px (medido acá el 2026-08-24). */
.st-key-compras_vap_ventana {{
    display: flex !important;
    /* `flex-direction: row` EXPLÍCITO: el stVerticalBlock de Streamlit es
       `column`, así que sin esto `justify-content` alinea en el eje
       VERTICAL y el `align-items: center` es el que manda en el
       horizontal — el control salía centrado en su columna, 214px antes
       del borde derecho (medido acá el 2026-08-24). */
    flex-direction: row !important;
    justify-content: flex-end !important;
    align-items: center !important;
    padding: 0 !important; margin: 0 !important;
}}
.st-key-compras_vap_ventana [data-testid="stElementContainer"] {{
    width: auto !important;
    padding: 0 !important; margin: 0 !important;
}}
.st-key-compras_vap_ventana [data-testid="stSelectbox"] {{
    max-width: 130px !important;
}}
.st-key-compras_vap_ventana [data-testid="stSelectbox"] div[role="group"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}
.st-key-compras_vap_ventana [data-testid="stSelectbox"] input,
.st-key-compras_vap_ventana [data-testid="stSelectbox"] div[role="group"],
.st-key-compras_vap_ventana [data-testid="stSelectbox"] .react-aria-ComboBox {{
    height: 22px !important;
    min-height: 0 !important;
}}
.st-key-compras_vap_ventana [data-testid="stSelectbox"] input {{
    padding: 0 !important;
    height: auto !important;
    font-size: 12.5px !important;
    font-weight: 600 !important;
    color: {GRIS_TEXTO} !important;
    text-align: right !important;
    cursor: pointer !important;
}}
/* El chevron se conserva, y en acento: sin ninguna affordance, un texto que
   despliega una lista no se distingue de una etiqueta muerta. */
.st-key-compras_vap_ventana [data-testid="stSelectbox"] svg {{
    width: 14px !important; height: 14px !important;
    fill: {ACENTO} !important; color: {ACENTO} !important;
}}
.st-key-compras_vap_ventana [data-testid="stSelectbox"] button[aria-haspopup] {{
    width: 16px !important; min-width: 0 !important;
}}
.st-key-compras_vap_ventana [data-testid="stSelectbox"]:hover input {{
    color: {ACENTO} !important;
}}

/* ── Controles de la tabla de abajo: agrupador y buscador, compactos ─────
   El buscador queda con su caja (es un campo de escritura y tiene que
   parecerlo); el agrupador se aplana igual que la ventana de arriba. */
.st-key-compras_vap_agrupar [data-testid="stSelectbox"] div[role="group"] {{
    border-color: {LAVANDA_BORDE} !important;
}}
.st-key-compras_vap_q input {{
    font-size: 12.5px !important;
}}
</style>
"""

_MODOS = ("Valor", "Cantidad", "Precio")
_AGRUPADORES = ("Producto", "Familia", "Subfamilia")


# ===========================================================================
# FUNCIONES PURAS (las fija test_graficos.py)
# ===========================================================================

def _mensual(d, col_prod, col_fecha, col_valor, col_cant, col_grupo=None,
             recorte=None):
    """Una fila por (prod, mes) con `valor`, `cant` y `grupo`.

    `mes` es un `pandas.Period[M]`, para poder sumarle 12 y caer en el mismo
    mes del año siguiente sin aritmética de calendario a mano.

    `recorte` es `(Period, dia)`: ese mes —y sólo ése— se suma hasta ese día
    del mes inclusive. Lo usa el mes ESPEJO del último mes parcial (ver la
    decisión 3 del docstring del módulo); el resto de los meses se suman
    enteros.

    `grupo` es la columna con la que la tabla de abajo puede agrupar
    (Familia/Subfamilia). Cae al propio producto si no se pasa una.
    """
    if d is None or getattr(d, "empty", True) or not (col_prod and col_fecha):
        return pd.DataFrame(columns=["prod", "grupo", "mes", "valor", "cant"])
    fe = pd.to_datetime(d[col_fecha], errors="coerce")
    base = pd.DataFrame({
        "prod": d[col_prod].astype(str).values,
        "grupo": (d[col_grupo].astype(str).values
                  if col_grupo and col_grupo in d.columns
                  else d[col_prod].astype(str).values),
        "fecha": fe.values,
        "valor": (pd.to_numeric(d[col_valor], errors="coerce").fillna(0).values
                  if col_valor else 0.0),
        "cant": (pd.to_numeric(d[col_cant], errors="coerce").fillna(0).values
                 if col_cant else 0.0),
    }).dropna(subset=["fecha"])
    if base.empty:
        return pd.DataFrame(columns=["prod", "grupo", "mes", "valor", "cant"])
    base["mes"] = base["fecha"].dt.to_period("M")
    if recorte is not None:
        mes_rec, dia_rec = recorte
        fuera = (base["mes"] == mes_rec) & (base["fecha"].dt.day > dia_rec)
        base = base[~fuera]
    g = (base.groupby(["prod", "mes"], as_index=False)
             .agg(valor=("valor", "sum"), cant=("cant", "sum"),
                  grupo=("grupo", "first")))
    return g[["prod", "grupo", "mes", "valor", "cant"]]


def _con_ano_pasado(g_actual, g_fuente=None):
    """`g_actual` + las columnas `valor_aa`/`cant_aa` del mismo mes del año
    anterior, tomadas de `g_fuente` (por defecto, de sí mismo).

    Las dos fuentes se separan por el mes parcial: `g_actual` nunca se
    recorta (es lo que se compró de verdad) y `g_fuente` sí, para que el
    espejo del mes parcial mida los mismos días.

    El `merge` es OUTER a propósito: un ítem que se compraba el año pasado y
    este año no, no tiene fila en `g_actual` — y es justamente la baja que
    hay que ver. Sale con `valor` 0 y `valor_aa` > 0.

    Descarta los meses ANTERIORES al primero comparable (primer mes con dato
    + 12): ahí no hay año pasado que mirar, y dibujarlos con un 0 se lee
    como "ese año no compramos nada", que es una mentira distinta.
    """
    cols = ["prod", "grupo", "mes", "valor", "cant", "valor_aa", "cant_aa"]
    if g_actual is None or g_actual.empty:
        return pd.DataFrame(columns=cols)
    fuente = g_actual if g_fuente is None else g_fuente
    prev = fuente[["prod", "mes", "valor", "cant"]].copy()
    prev["mes"] = prev["mes"] + 12
    prev = prev.rename(columns={"valor": "valor_aa", "cant": "cant_aa"})

    out = g_actual.merge(prev, on=["prod", "mes"], how="outer")
    # `grupo` viaja pegado al producto, no al mes: las filas que aporta el
    # outer (bajas) lo traen vacío y se rellena desde el mapa del producto.
    mapa = (g_actual.dropna(subset=["grupo"])
                    .drop_duplicates("prod").set_index("prod")["grupo"])
    out["grupo"] = out["grupo"].fillna(out["prod"].map(mapa)).fillna(out["prod"])
    for c in ("valor", "cant", "valor_aa", "cant_aa"):
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    # PISO: el primer mes comparable (primer mes con dato + 12). Antes de
    # eso no hay año pasado que mirar, y pintar esos meses con un 0 se lee
    # como "ese año no compramos nada", que es una mentira distinta.
    # TECHO: el último mes con compras REALES. El merge es outer, así que el
    # desplazamiento de 12 meses también inventa filas DESPUÉS del final del
    # histórico (medido: llegaba hasta 2027-08 con `valor` 0 y `valor_aa` >
    # 0). Eso no es una baja, es un mes que todavía no pasó.
    piso = fuente["mes"].min() + 12
    techo = g_actual["mes"].max()
    out = out[(out["mes"] >= piso) & (out["mes"] <= techo)]
    return out[cols].sort_values(["mes", "prod"]).reset_index(drop=True)


def _puente(valor, cant, valor_aa, cant_aa):
    """`(efecto_precio, efecto_cantidad)` de la diferencia contra el año
    pasado. Los dos SIEMPRE suman `valor - valor_aa`.

        Δ = (p − p_aa)·q + (q − q_aa)·p_aa,   con p = valor/cant

    Con `cant_aa` en 0 no hay precio del otro lado (el ítem es nuevo): el
    efecto es 100% cantidad. Con `cant` en 0 pasa lo mismo del otro lado (el
    ítem se dejó de comprar). En los dos casos el precio no explica nada, y
    forzar un efecto precio ahí sería inventarlo.
    """
    delta = float(valor) - float(valor_aa)
    if cant_aa <= 0 or cant <= 0:
        return 0.0, delta
    p_aa = float(valor_aa) / float(cant_aa)
    ef_precio = float(valor) - p_aa * float(cant)
    return ef_precio, delta - ef_precio


def _por_item(g, llave="prod"):
    """`g` agregado por `llave`, con el puente ya calculado y sumado.

    EL PUENTE SE CALCULA SIEMPRE A NIVEL PRODUCTO, y recién después se suma
    al grupo. Calcularlo sobre el agregado da un número que CIERRA pero que
    no significa nada: el "precio" de un grupo sería `Σvalor / Σcantidad`,
    o sea kilos, litros, unidades y servicios sumados en el mismo
    denominador. Medido con el parquet real el 2026-08-24, la familia
    GASTOS VENTAS daba efecto precio −540.105 y efecto cantidad +504.339
    para explicar un Δ de −35.766: dos cifras quince veces más grandes que
    lo que explicaban, que se cancelaban entre sí.

    Sumar los efectos por producto sí es correcto y sigue cerrando: cada
    sumando es un Δ real de un ítem con UNA unidad, y
    Σ(ef_precio + ef_cant) = Σ(valor − valor_aa) = Δ del grupo.

    `n_items` (cuántos productos hay detrás) viaja en el resultado porque es
    lo único que la tabla puede decir del "precio" de un grupo.
    """
    cols = ["valor", "cant", "valor_aa", "cant_aa"]
    base = g.groupby(["prod"] if llave == "prod" else ["prod", llave],
                     as_index=False)[cols].sum()
    efectos = [_puente(r.valor, r.cant, r.valor_aa, r.cant_aa)
               for r in base.itertuples()]
    base["ef_precio"] = [e[0] for e in efectos]
    base["ef_cant"] = [e[1] for e in efectos]
    base["n_items"] = 1
    if llave == "prod":
        return base.rename(columns={"prod": "item"})
    return (base.groupby(llave, as_index=False)[
        cols + ["ef_precio", "ef_cant", "n_items"]].sum()
        .rename(columns={llave: "item"}))


def _mes_parcial(fechas):
    """`(Period del último mes, día de corte)` si el último mes con datos
    está incompleto; `None` si cierra en fin de mes.

    "Incompleto" se mide contra el propio dato, no contra hoy: el parquet se
    regenera de madrugada y los documentos entran con retraso, así que el
    último día CON DATOS es la única referencia honesta (mismo criterio que
    el ancla de `graficos/periodo.py`).
    """
    fechas = pd.to_datetime(fechas, errors="coerce").dropna()
    if fechas.empty:
        return None
    fin = fechas.max()
    if fin.day == fin.days_in_month:
        return None
    return fin.to_period("M"), int(fin.day)


def _etiqueta_mes(periodo_m):
    """"ago 25" — corto, porque el eje puede llevar 30 de éstos."""
    _MES = ("ene", "feb", "mar", "abr", "may", "jun",
            "jul", "ago", "sep", "oct", "nov", "dic")
    return f"{_MES[periodo_m.month - 1]} {periodo_m.year % 100:02d}"


# ===========================================================================
# GRÁFICOS
# ===========================================================================

def _fig_serie(g, modo, parcial):
    """Serie mensual: este año contra el mismo mes del año pasado.

    Valor y Cantidad van en barras agrupadas (son magnitudes que se suman y
    la comparación es de altura contra altura). Precio va en líneas: es un
    ratio, no se apila, y lo que interesa es la FORMA de la curva.
    """
    por_mes = g.groupby("mes", as_index=False)[
        ["valor", "cant", "valor_aa", "cant_aa"]].sum().sort_values("mes")
    if por_mes.empty:
        st.info("Sin meses comparables en esta ventana.")
        return None

    if modo == "Valor":
        y_act, y_aa, fmt = por_mes["valor"], por_mes["valor_aa"], "S/ %{y:,.0f}"
    elif modo == "Cantidad":
        y_act, y_aa, fmt = por_mes["cant"], por_mes["cant_aa"], "%{y:,.1f}"
    else:
        # `.where(> 0)` y no `replace(0, NA)`: sobre una serie float, NA
        # la vuelve object y Plotly deja de saber que es un eje numérico.
        y_act = por_mes["valor"] / por_mes["cant"].where(por_mes["cant"] > 0)
        y_aa = por_mes["valor_aa"] / por_mes["cant_aa"].where(
            por_mes["cant_aa"] > 0)
        fmt = "S/ %{y:,.2f}"

    etiquetas = [_etiqueta_mes(m) for m in por_mes["mes"]]
    # El mes parcial se marca en la BARRA (trama) y en su etiqueta, no en un
    # caption al pie: el que lo tiene que ver está mirando la última barra.
    es_parcial = [parcial is not None and m == parcial[0] for m in por_mes["mes"]]

    fig = go.Figure()
    if modo == "Precio":
        fig.add_scatter(x=etiquetas, y=y_aa, mode="lines", name="Año pasado",
                        line=dict(color=GRIS_TEXTO, width=2, dash="dot"),
                        hovertemplate=fmt + "<extra>Año pasado</extra>")
        fig.add_scatter(x=etiquetas, y=y_act, mode="lines+markers",
                        name="Este año", line=dict(color=ACENTO, width=2.4),
                        marker=dict(size=6),
                        hovertemplate=fmt + "<extra>Este año</extra>")
    else:
        fig.add_bar(x=etiquetas, y=y_aa, name="Año pasado",
                    marker=dict(color=GRIS_BORDE),
                    hovertemplate=fmt + "<extra>Año pasado</extra>")
        fig.add_bar(
            x=etiquetas, y=y_act, name="Este año",
            marker=dict(
                color=ACENTO,
                # Trama sólo en el mes parcial: Plotly acepta un patrón por
                # punto, así que no hace falta una traza aparte que además
                # rompería la leyenda en dos "Este año".
                pattern=dict(shape=["/" if p else "" for p in es_parcial],
                             fgcolor="#ffffff", size=4, solidity=0.35),
            ),
            hovertemplate=fmt + "<extra>Este año</extra>")

    _compras_layout(fig, alto=alturas.con_franja(alturas.COMPACTO, _FRANJA_VAP))
    # SIN `title`: el ámbito vive en la cabecera de la tarjeta desde el
    # 2026-09-02 (ver el `st.empty()` del drill). Lo que gana la figura no
    # es sólo el alto del texto — Plotly reserva margen superior para el
    # título aunque esté vacío, así que el margen se fija explícito abajo.
    fig.update_layout(
        barmode="group", bargap=0.28, bargroupgap=0.08,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.04, x=0, font=dict(size=11)),
    )
    fig.update_xaxes(type="category", tickangle=0)
    return fig


def _fig_puente(valor, valor_aa, ef_precio, ef_cant):
    """Puente: año pasado → efecto precio → efecto cantidad → este año.

    `go.Waterfall` ignora `bargap` (CLAUDE.md § Plotly): el grosor se
    controla con `waterfallgap`.
    """
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=["Año<br>pasado", "Precio", "Cantidad", "Este<br>año"],
        y=[valor_aa, ef_precio, ef_cant, 0],
        text=[f"S/ {v:,.0f}" for v in (valor_aa, ef_precio, ef_cant, valor)],
        textposition="outside",
        cliponaxis=False,
        # Es un COSTO: subir es malo. Rojo/verde invertidos respecto de la
        # convención bursátil, igual que el semáforo de Volatilidad.
        increasing=dict(marker=dict(color=ERROR)),
        decreasing=dict(marker=dict(color=EXITO)),
        totals=dict(marker=dict(color=ACENTO)),
        connector=dict(line=dict(color=GRIS_BORDE, width=1)),
        hovertemplate="%{x}: S/ %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(waterfallgap=0.45)
    # Menos alto que la serie de al lado, y por eso terminan a la misma
    # altura: encima de esta figura va la línea de veredicto, que la empuja
    # hacia abajo (`alturas.FRANJA_VEREDICTO`, medida en el navegador).
    _compras_layout(fig, alto=(alturas.con_franja(alturas.COMPACTO, _FRANJA_VAP)
                               - alturas.FRANJA_VEREDICTO))
    # `title=""` y NO `title=None`: con None, Plotly.js pinta la cadena
    # literal "undefined" donde iría el título (medido en el navegador,
    # 2026-08-24 — salía sobre el waterfall). El título de esta figura
    # sobra: la línea de resumen de arriba y las etiquetas del propio eje
    # ("Año pasado → Precio → Cantidad → Este año") ya la nombran.
    fig.update_layout(showlegend=False, title="",
                      margin=dict(l=10, r=10, t=44, b=10))
    fig.update_yaxes(showticklabels=False)
    return fig


# ===========================================================================
# UI
# ===========================================================================

def _resumen_html(delta, pct, ef_precio, ef_cant):
    """Una línea con el veredicto, arriba del puente. Es texto y no `st.metric`
    porque tres métricas nativas ocupan 90px de la tarjeta para decir lo que
    el propio waterfall ya dibuja debajo."""
    color = ERROR if delta > 0 else (EXITO if delta < 0 else GRIS_TEXTO)
    signo = "+" if delta >= 0 else "−"
    # Con artículo: "el precio" / "la cantidad" — sin él salía "la precio".
    culpa = ("el precio" if abs(ef_precio) > abs(ef_cant) else "la cantidad")
    return (
        f'<div style="font:600 19px/1.2 DM Sans,sans-serif;color:{color};'
        f'margin:0 0 2px">{signo}S/ {abs(delta):,.0f}'
        f'<span style="font:400 13px/1 DM Sans,sans-serif;color:{GRIS_TEXTO};'
        f'margin-left:8px">{signo}{abs(pct):.1f}% vs año pasado</span></div>'
        f'<div style="font:400 12px/1.35 DM Sans,sans-serif;color:{GRIS_TEXTO};'
        f'margin:0 0 6px">Lo explica sobre todo <b style="color:'
        f'{TEXTO_PRINCIPAL}">{culpa}</b></div>'
    )


def _tabla_detalle(g, agrupar_por, col_um_valores, key_grid):
    """Tabla de abajo: una fila por ítem, con el puente abierto.

    Devuelve el ítem clickeado en esta corrida (o None). El orden por defecto
    es |Δ S/| descendente —lo que más movió la aguja arriba de todo—, no
    alfabético: la pregunta de esta tabla es "qué explica la diferencia".
    """
    llave = "prod" if agrupar_por == "Producto" else "grupo"
    ag = _por_item(g, llave)
    if ag.empty:
        st.info("Sin ítems comparables en esta ventana.")
        return None
    # Cantidad y precio sólo se muestran cuando la fila ES un producto: la
    # cantidad de una familia suma kilos con litros y con servicios, y el
    # precio que salga de ese denominador no significa nada (ver `_por_item`).
    # En una familia, lo que se puede decir es cuántos productos la componen.
    _es_prod = llave == "prod"

    filas = []
    for _, r in ag.iterrows():
        delta = r["valor"] - r["valor_aa"]
        filas.append({
            "Item": _compras_truncar(str(r["item"]), 42),
            "__item_full": str(r["item"]),
            "Este año": float(r["valor"]),
            "Año pasado": float(r["valor_aa"]),
            "Δ S/": float(delta),
            "Δ %": (float(delta / r["valor_aa"] * 100)
                    if r["valor_aa"] else None),
            "Efecto precio": float(r["ef_precio"]),
            "Efecto cantidad": float(r["ef_cant"]),
            "__cant": float(r["cant"]) if _es_prod else None,
            "__cant_aa": float(r["cant_aa"]) if _es_prod else None,
            "__p": (float(r["valor"] / r["cant"])
                    if _es_prod and r["cant"] else None),
            "__p_aa": (float(r["valor_aa"] / r["cant_aa"])
                       if _es_prod and r["cant_aa"] else None),
            "__um": col_um_valores.get(str(r["item"]), "") if _es_prod else "",
            "__n": int(r["n_items"]),
        })
    tv = pd.DataFrame(filas)
    tv = tv.reindex(tv["Δ S/"].abs().sort_values(ascending=False).index)
    tv = tv.reset_index(drop=True)

    return renderizar_detalle_vs_ano_pasado(
        tv, agrupar_por,
        # ENMARCADA: la tabla crece con los datos (1.578 productos en el
        # parquet real), así que su alto lo pone el marco y lo que no entra
        # scrollea DENTRO del grid.
        #
        # El techo era `MARCO` (553px, una pantalla completa) hasta
        # 2026-08-26, a pedido ("Vs año pasado es muy largo... al igual que
        # Detalle ítem por ítem"): esta tabla va DEBAJO de la fila de
        # gráficos, así que MARCO + esa fila sumaban bien más de una
        # pantalla de scroll para ver la vista completa. Bajó a `APOYO` —
        # el mismo rol que usaban los gráficos de arriba, no un número
        # inventado: la vista queda de DOS bloques de alto parecido en vez
        # de uno chico y uno casi entero.
        #
        # 2026-09-02, SEGUNDA vuelta del mismo pedido ("podemos hacerlos
        # menos altos, o sea reducirlos verticalmente"): los dos bloques
        # bajan juntos de `APOYO` a `COMPACTO`, el rol que nació ese día
        # justamente para esta forma de vista (ver `alturas.py`). Medido
        # antes: la sección entera daba 1.155px en 1366x700, o sea 1,9
        # pantallas. El `extra` pasa de 44 a 47, que es el cromo MEDIDO por
        # resta en el navegador (grid 380 − `.ag-body-viewport` 333, o sea
        # cabecera 45 + 2 de borde) en vez de sumado a ojo — regla #277.
        altura=alturas.por_filas(len(tv), px_fila=30, extra=47,
                                 minimo=200, rol=alturas.COMPACTO),
        key=key_grid,
    )


@st.fragment
def _compras_vs_ano_pasado_drill(d, col_prod, col_cant, col_fecha, col_valor,
                                 col_fam=None, col_subfam=None, col_um=None,
                                 d_full=None):
    """Serie mensual + puente precio/cantidad + tabla de detalle.

    Esta firma perdió dos columnas que la versión anterior sí recibía, y no
    por prolijidad: `col_punit` (`PRECIO_UNIT`) y `col_val_aa`
    (`VALOR_ANO_ANTERIOR`) ya no las lee nadie acá. El precio sale ponderado
    (valor/cantidad, para que el puente cierre) y el año pasado del propio
    histórico desplazado 12 meses. Dejarlas puestas "por si acaso" es lo que
    la regla #53 del proyecto llama un símbolo sin consumidor: nada avisa de
    que están muertas, y la próxima lectura del módulo asume que se usan.
    Ver las decisiones 2 y 3 del docstring del módulo.
    """
    if not (col_prod and col_fecha and col_valor and col_cant):
        st.info("Faltan columnas (Producto, Fecha, Valor o Cantidad) "
                "para este gráfico.")
        return

    st.markdown(_CSS, unsafe_allow_html=True)

    # 2026-09-02, a pedido: el ámbito ("Todas las compras · últimos 3 meses",
    # o el nombre del ítem en foco) DEJA de ser el `title` de la figura y
    # sube a la fila del título de la tarjeta, al lado de "Vs año pasado".
    #
    # Va por un HUECO (`st.empty()`) y no por el parámetro `titulo` de
    # `_card`: la cabecera se dibuja arriba de todo, pero el ámbito recién
    # se sabe ~100 líneas más abajo (depende del foco, de la ventana y de
    # los datos que sobrevivan a las dos). El hueco reserva el sitio en el
    # orden del DOM y se rellena cuando el dato existe. Se escribe DOS
    # veces a propósito: la primera, sólo "Vs año pasado", para que los
    # `return` tempranos de más abajo —sin meses comparables, sin datos—
    # no dejen la tarjeta sin cabecera.
    with _card("compras_vap"):
        _hdr = st.empty()
        _pinta_hdr = lambda amb=None: _hdr.markdown(  # noqa: E731
            '<p class="chart-card-hdr vap-hdr">Vs año pasado'
            + (f'<span>{amb}</span>' if amb else "")
            + '</p>', unsafe_allow_html=True)
        _pinta_hdr()
        c_modo, c_vent = st.columns([1, 1])  # columnas-internas: los dos
        # controles de la tarjeta (métrica y ventana) comparten renglón,
        # uno pegado a cada borde. No parte una FILA del drill.
        with c_modo:
            with st.container(key="compras_vap_modo"):
                modo = st.pills("Ver", list(_MODOS), default="Valor",
                                key="compras_vap_modo_pills",
                                label_visibility="collapsed") or "Valor"
        with c_vent:
            with st.container(key="compras_vap_ventana"):
                # Default "Todo" — el cambio pedido: esta vista mira el
                # histórico, no el rango de la franja (decisión 1).
                ventana = periodo.selector("compras_vap_periodo",
                                           default="Todo", widget="lista")

        # `d_full` es el histórico SIN el filtro de fecha de la franja (los
        # chips Familia/Subfamilia sí vienen aplicados). Con la opción
        # El CÁLCULO sale SIEMPRE del histórico, en las cinco opciones —
        # incluida HEREDA. Ésa es la trampa que se midió acá el 2026-08-24:
        # el año pasado se saca desplazando la propia serie 12 meses, así
        # que calcularlo sobre `d` (lo que dejó pasar la franja) deja al
        # desplazamiento sin fuente. Con la franja en su default —el mes
        # corriente— "Rango" daba un solo mes, el piso caía 12 meses más
        # adelante que el techo y la vista salía vacía SIEMPRE. La ventana
        # elige qué meses se MUESTRAN, no de dónde salen los números.
        fuente = d_full if d_full is not None else d
        if fuente is None or fuente.empty:
            st.info("No hay datos para los filtros seleccionados.")
            return

        parcial = _mes_parcial(fuente[col_fecha])
        # Dos agregados: el real (nunca recortado) y el que alimenta al año
        # pasado (con el mes espejo recortado al mismo día). Ver decisión 3.
        g_act = _mensual(fuente, col_prod, col_fecha, col_valor, col_cant,
                         col_grupo=None)
        g_src = g_act if parcial is None else _mensual(
            fuente, col_prod, col_fecha, col_valor, col_cant,
            recorte=(parcial[0] - 12, parcial[1]))
        g = _con_ano_pasado(g_act, g_src)
        if g.empty:
            st.info("El histórico no llega a un año completo todavía: "
                    "no hay mes con el mismo mes del año anterior para "
                    "comparar.")
            return

        # El recorte va DESPUÉS de calcular el año pasado: recortar antes
        # dejaría sin fuente a los primeros 12 meses de la ventana.
        if ventana == periodo.HEREDA:
            # "Rango" = los meses que TOCA el rango de la franja, cada uno
            # completo. El mes es la unidad de comparación (el año pasado se
            # mide mes contra mes), así que media docena de días sueltos no
            # se puede comparar contra "el mismo mes del año pasado" sin
            # recortar los dos lados — y eso ya se hace, pero sólo para el
            # último mes, que es el único donde el recorte es inevitable.
            _fe_d = pd.to_datetime(d[col_fecha], errors="coerce").dropna()
            if not _fe_d.empty:
                g = g[(g["mes"] >= _fe_d.min().to_period("M"))
                      & (g["mes"] <= _fe_d.max().to_period("M"))]
        else:
            # El ancla es el ÚLTIMO día del último mes, no el primero: con el
            # primero, `periodo.ventana` devuelve un inicio que cae dentro del
            # mes 12 hacia atrás y "12m" termina mostrando 13 barras.
            v = periodo.ventana(ventana,
                                g["mes"].max().to_timestamp(how="end"),
                                minimo=g["mes"].min().to_timestamp())
            if v is not None:
                ini, fin = v
                g = g[(g["mes"] >= ini.to_period("M"))
                      & (g["mes"] <= fin.to_period("M"))]
        if g.empty:
            st.info("Sin meses comparables en esta ventana. El histórico "
                    "arranca un año antes del primer mes que se puede "
                    "comparar.")
            return

        # ── Foco: el ítem clickeado en la tabla de abajo ─────────────────
        agrupar_por = st.session_state.get("compras_vap_agrupar", "Producto")
        foco = st.session_state.get("compras_vap_foco")
        llave_foco = "prod" if agrupar_por == "Producto" else "grupo"
        g_foco = g if foco is None else g[g[llave_foco].astype(str) == foco]
        if foco is not None and g_foco.empty:      # cambió el agrupador
            foco, g_foco = None, g

        # Precio es un RATIO: promediarlo sobre productos distintos (y
        # unidades distintas) no es una magnitud real. Sin foco, la curva
        # se calcula sobre el ítem de mayor gasto y el título lo dice.
        if modo == "Precio" and foco is None:
            _top = (g.groupby(llave_foco)["valor"].sum().sort_values()
                    .index.tolist())
            if _top:
                g_foco = g[g[llave_foco].astype(str) == str(_top[-1])]
                foco_titulo = str(_top[-1])
            else:
                foco_titulo = None
        else:
            foco_titulo = foco

        # Mismo criterio que la tabla: el puente se suma desde los
        # productos, nunca se calcula sobre el agregado (ver `_por_item`).
        _items = _por_item(g_foco)
        tot = _items[["valor", "valor_aa", "ef_precio", "ef_cant"]].sum()
        ef_p, ef_c = float(tot["ef_precio"]), float(tot["ef_cant"])
        delta = tot["valor"] - tot["valor_aa"]
        pct = (delta / tot["valor_aa"] * 100) if tot["valor_aa"] else 0.0

        _et = periodo.etiqueta(ventana)
        _amb = (_compras_truncar(foco_titulo, 34) if foco_titulo
                else "Todas las compras")
        _tit = _amb + (f" · {_et}" if _et else "")
        _pinta_hdr(_tit)

        col_g, col_p = st.columns(COLUMNAS_DRILL, gap=GAP_DRILL)
        with col_g:
            fig = _fig_serie(g_foco, modo, parcial)
            if fig is not None:
                st.plotly_chart(fig, use_container_width=True,
                                key=f"compras_g_vap_{modo.lower()}")
        with col_p:
            st.markdown(_resumen_html(delta, pct, ef_p, ef_c),
                        unsafe_allow_html=True)
            st.plotly_chart(_fig_puente(tot["valor"], tot["valor_aa"],
                                        ef_p, ef_c),
                            use_container_width=True, key="compras_g_vap_puente")

        if parcial is not None:
            st.caption(
                f"El último mes va hasta el día {parcial[1]} (es lo que trae "
                f"el parquet): su barra sale con trama y se compara contra "
                f"los mismos días del año pasado, no contra el mes entero.")

    # ── Tabla de detalle, ancho completo debajo ──────────────────────────
    with _card("compras_vap_detalle", "Detalle ítem por ítem",
               titulo_arriba=True):
        # columnas-internas: agrupador y buscador de la propia tabla, no una
        # fila del drill. La tercera columna es un espaciador: sin ella el
        # buscador se estiraba a 745px (medido) — un campo de una palabra
        # con el ancho de media pantalla se lee como un error de layout.
        c_ag, c_q, _ = st.columns([1, 1.4, 2.6])
        with c_ag:
            _ops_ag = [a for a in _AGRUPADORES
                       if a == "Producto"
                       or (a == "Familia" and col_fam)
                       or (a == "Subfamilia" and col_subfam)]
            # Si el reporte viene sin Familia/Subfamilia, un valor guardado
            # de otra sesión ya no está en `options` y Streamlit revienta.
            if st.session_state.get("compras_vap_agrupar") not in _ops_ag:
                st.session_state["compras_vap_agrupar"] = _ops_ag[0]
            agrupar_nuevo = st.selectbox(
                "Agrupar por", _ops_ag, key="compras_vap_agrupar",
                label_visibility="collapsed",
                help="Proveedor no está: el año pasado se compara por "
                     "producto y mes, así que repartirlo entre proveedores "
                     "le atribuiría a uno lo que compró otro.")
        with c_q:
            q = st.text_input("Buscar", key="compras_vap_q",
                              placeholder="Buscar ítem…",
                              label_visibility="collapsed").strip().lower()

        # El agrupador manda sobre la columna que se agrega: se recalcula el
        # `grupo` de `g` cuando no es el producto.
        if agrupar_nuevo != "Producto":
            _cg = col_fam if agrupar_nuevo == "Familia" else col_subfam
            _mapa = (fuente[[col_prod, _cg]].astype(str)
                     .drop_duplicates(col_prod)
                     .set_index(col_prod)[_cg])
            g = g.copy()
            g["grupo"] = g["prod"].map(_mapa).fillna(g["prod"])

        g_tabla = g if not q else g[
            g["prod" if agrupar_nuevo == "Producto" else "grupo"]
            .astype(str).str.lower().str.contains(q, regex=False)]
        if g_tabla.empty:
            st.info(f"Ningún ítem coincide con «{q}».")
            return

        # Unidad de medida por ítem, sólo para el tooltip. `mode()` y no el
        # primero: un producto puede tener alguna fila con la unidad mal
        # cargada y la moda la ignora.
        ums = {}
        if col_um and col_um in fuente.columns:
            _llave_um = col_prod if agrupar_nuevo == "Producto" else (
                col_fam if agrupar_nuevo == "Familia" else col_subfam)
            _m = (fuente[[_llave_um, col_um]].astype(str)
                  .groupby(_llave_um)[col_um]
                  .agg(lambda s: s.mode().iat[0] if not s.mode().empty else ""))
            ums = _m.to_dict()

        clic = _tabla_detalle(g_tabla, agrupar_nuevo, ums,
                              "compras_vap_detalle_grid")
        st.caption("Δ = este año − mismo período del año pasado. "
                   "**Efecto precio** es lo que costó pagar distinto por lo "
                   "mismo; **efecto cantidad**, lo que costó comprar más (o "
                   "menos). Los dos suman el Δ exacto. "
                   "Clic en una fila para enfocar el gráfico de arriba.")

        # UNA sola comparación, igual que el ranking de Proveedor: AG Grid
        # conserva su selección entre reruns del fragment, así que `clic`
        # vuelve igual mientras nadie toque la tabla y esto no dispara nada.
        # Deseleccionar (clic en la fila activa) devuelve None y vuelve a
        # "todas las compras" — es un gesto explícito, se respeta.
        if clic != st.session_state.get("compras_vap_foco"):
            st.session_state["compras_vap_foco"] = clic
            st.rerun(scope="fragment")
