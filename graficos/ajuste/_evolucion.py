"""graficos.ajuste._evolucion - la categoria Tiempo de Ajuste, en UNA vista.

Hasta el 2026-09-23 la categoria Tiempo eran TRES items del rail que
miraban el mismo cubo de datos —ajuste valorizado x tiempo x familia/
producto— con tres formas distintas:

    Evolucion             lineas, una por familia, por fecha de apertura
    Comparativa mensual   barras del neto por mes (sin comparar nada)
    Por fecha de corte    la tabla pivote, con el año en curso FIJO

Comparativa era la fila Total de la tabla con «Mes»; Evolucion, su nivel
Familia con «Corte». Y las tres sumaban el NETO: un mes con +S/ 105k de
sobrante y -S/ 116k de faltante (set 2026, medido) salia como -S/ 11k, o
sea como un mes tranquilo, cuando es el peor del año. Se fusionaron a
pedido («creo que dan similar informacion») en esta vista:

    1. La SERIE: sobrante hacia arriba, faltante hacia abajo y el neto como
       linea encima. Lo que se cancela se VE.
    2. Los MINI-GRAFICOS por familia (small multiples), la misma serie una
       vez por familia, cada uno con su escala. Reemplazan a las lineas
       enredadas de la Evolucion vieja.
    3. La TABLA pivote de siempre (`_pivote.py`), con los MISMOS periodos
       (`periodos_ajuste`, de aca).

Serie y familias van en UNA tarjeta, con el grano y el periodo en foco en
su cabecera; la tabla, desde el mismo dia, es su propia vista del rail
(«Detalle por producto»), con su propio grano: de esta tarjeta solo
recibia una marca de columna que casi no se veia (regla #504). Las dos
miran el mismo rango: el de la franja, que para esta categoria abre en los
ultimos 12 meses (`app.py`, regla #501).

SIN MODO «%», Y NO POR OLVIDO. Se propuso un «% de merma» (ajuste sobre
el valor del periodo, a la manera de la tasa de shrink del National Retail
Security Survey de la NRF, que alla va sobre ventas) y se descarto al
medirlo contra el parquet real (2026-09-23, 5 familias, oct 25 - set 26):

  · sobre el valor CONTADO (stock declarado x precio): ago 26 da -65 %. Si
    falta casi todo, lo contado es casi cero y el cociente se dispara.
  · sobre el valor EN SISTEMA (stock al cierre x precio): set 26 da -99 %.
    10.188 filas tienen stock en sistema NEGATIVO y restan del denominador.
  · y el 73 % del sobrante (S/ 358k de 487k) sale de esas filas: no es
    mercaderia que aparecio, es el conteo corrigiendo un stock negativo.

Con el dato asi, cualquier % le miente a quien lo lea. El valor contado
queda en el hover del neto como contexto, no como denominador.
"""

import math

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from tema import (
    AJUSTE_NEG, AJUSTE_POS, GRIS_BORDE, GRIS_TEXTO, TEXTO_PRINCIPAL,
)
from graficos.base import publicar_contexto_ia
from graficos import alturas
from graficos.ajuste._comun import (
    FAMILIAS_DE_ENTRADA, _MESES_ABR_ES, _layout_aj, _periodo_pivote_ajuste,
    css_filtros_vista, filtro_area_en_titulo,
)
from utils import fmt_k

GRANOS = ("Corte", "Semana", "Mes")

_K_GRAN = "ajuste_evo_gran"
_K_FOCO = "ajuste_evo_foco"
# Contador de la key de la serie: la seleccion de `on_select` PERSISTE
# entre reruns, asi que se lee ANTES de dibujar y la key cambia tras cada
# clic procesado. Misma receta que `compras_sem_nclic` (regla #399).
_K_NCLIC = "ajuste_evo_nclic"

# Mas periodos que esto y los rotulos del neto se pisan entre si: se
# apagan y el valor queda en el hover.
_MAX_ROTULOS = 16

# Opacidad de los periodos que NO estan en foco.
_APAGADO = 0.3


# ── DATOS (puros: sin Streamlit, los prueba test_graficos.py) ────────────

def periodos_ajuste(d, col_fecha, gran):
    """Asigna a cada fila su periodo y arma la lista ORDENADA de periodos.

    Devuelve `(d_con_clave, orden)`: `d` con la columna `_clave`, y un
    DataFrame con `_clave`, `etq` (rotulo corto: la cabecera de la tabla,
    que ya dice el año en su grupo de columnas), `eje` (rotulo del eje de la
    serie: lleva el año cuando el rango cruza de año, porque «2 set» de 2025
    y de 2026 serian la MISMA categoria) y `anio`.

    En «Mes» se rellenan los meses sin conteo entre el primero y el ultimo:
    un mes sin sesion de inventario es un dato («no se conto»), y saltearlo
    pegaria dos meses que no son vecinos. En Semana y Corte no: con uno a
    tres conteos por mes, rellenar semanas dejaria tres de cada cuatro
    columnas vacias.
    """
    d = d.copy()
    d[col_fecha] = pd.to_datetime(d[col_fecha], errors="coerce")
    d = d.dropna(subset=[col_fecha])
    cols = ["_clave", "etq", "eje", "anio"]
    if d.empty:
        return d.assign(_clave=pd.Series(dtype=str)), pd.DataFrame(columns=cols)

    clave, etq = _periodo_pivote_ajuste(d[col_fecha], gran)
    d["_clave"] = clave.astype(str).values
    d["_etq"] = etq.astype(str).values

    # El año de un periodo es el de su ULTIMO dia: un corte de fin de
    # diciembre que termina en enero es un conteo de enero.
    orden = (d.groupby("_clave", as_index=False)
              .agg(etq=("_etq", "first"), fin=(col_fecha, "max")))
    orden["anio"] = orden["fin"].dt.year.astype(int)

    if gran == "Mes":
        meses = pd.period_range(d[col_fecha].min().to_period("M"),
                                d[col_fecha].max().to_period("M"), freq="M")
        orden = pd.DataFrame({
            "_clave": [str(m) for m in meses],
            "etq": [_MESES_ABR_ES[m.month - 1] for m in meses],
            "anio": [int(m.year) for m in meses],
        })
    else:
        orden = orden.sort_values("_clave").reset_index(drop=True)

    varios_anios = orden["anio"].nunique() > 1
    orden["eje"] = [f"{e} {str(a)[2:]}" if varios_anios else e
                    for e, a in zip(orden["etq"], orden["anio"])]
    return d.drop(columns=["_etq"]), orden[cols].reset_index(drop=True)


def serie_ajuste(d, orden, col_ajuste_val, col_valorizado=None, col_grupo=None):
    """Sobrante, faltante, neto y valor contado por periodo (y por grupo).

    Una fila por periodo de `orden` —o por periodo x grupo—, INCLUIDOS los
    periodos sin datos (con NaN: la barra no se dibuja y la linea se corta,
    que es lo honesto). `contado` es la suma de `VALORIZADO TOTAL` (stock
    declarado x precio) de las filas contadas: contexto para el hover, NO
    el inventario del local — sumado sobre un mes con cuatro sesiones cuenta
    el stock cuatro veces.

    Se agrupa por COLUMNAS con nombre y se devuelve por nombre: una clave
    suelta en el groupby da otra forma en pandas 2 que en 3 (regla #481).
    """
    base = ["_clave", "etq", "eje", "anio"]
    medidas = ["sobrante", "faltante", "neto", "contado"]
    v = pd.to_numeric(d[col_ajuste_val], errors="coerce").fillna(0.0)
    x = pd.DataFrame({
        "_clave": d["_clave"].values,
        "sobrante": v.clip(lower=0).values,
        "faltante": v.clip(upper=0).values,
        "neto": v.values,
        "contado": (pd.to_numeric(d[col_valorizado], errors="coerce")
                    .fillna(0.0).values
                    if col_valorizado and col_valorizado in d.columns
                    else 0.0),
    })
    llaves = ["_clave"]
    if col_grupo:
        x["grupo"] = d[col_grupo].astype(str).values
        # 122 filas del parquet no traen familia: sin esto serian un panel
        # «Nan».
        x = x[d[col_grupo].notna().values]
        llaves.append("grupo")
    agg = x.groupby(llaves, as_index=False)[medidas].sum()

    esqueleto = orden[base]
    if col_grupo:
        grupos = pd.DataFrame({"grupo": sorted(agg["grupo"].unique())})
        esqueleto = esqueleto.merge(grupos, how="cross")
    s = esqueleto.merge(agg, on=llaves, how="left")
    return s[base + (["grupo"] if col_grupo else []) + medidas]


def _fmt(v):
    """Rotulo compacto del neto: «S/ -11.2k»."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return fmt_k(v)


def _trazas(s, foco, leyenda=True, rotulos=True):
    """Las tres trazas de una serie: dos barras y la linea del neto.

    Las comparten la serie grande y cada mini-grafico, asi los dos dicen lo
    mismo con la misma forma. `foco` apaga los otros periodos."""
    opac = [1.0 if foco is None or k == foco else _APAGADO
            for k in s["_clave"]]
    fmt_hover = "S/ %{y:,.0f}"
    sobr = go.Bar(
        x=s["eje"], y=s["sobrante"], name="Sobrante",
        marker=dict(color=AJUSTE_POS, opacity=opac),
        showlegend=leyenda, legendgroup="sobrante",
        hovertemplate=f"Sobrante: {fmt_hover}<extra></extra>",
    )
    falt = go.Bar(
        x=s["eje"], y=s["faltante"], name="Faltante",
        marker=dict(color=AJUSTE_NEG, opacity=opac),
        showlegend=leyenda, legendgroup="faltante",
        hovertemplate=f"Faltante: {fmt_hover}<extra></extra>",
    )
    neto_y = s["neto"]
    con_texto = rotulos and len(s) <= _MAX_ROTULOS
    neto = go.Scatter(
        x=s["eje"], y=neto_y, name="Neto",
        mode="lines+markers+text" if con_texto else "lines+markers",
        text=[_fmt(v) for v in neto_y] if con_texto else None,
        textposition="top center",
        textfont=dict(size=10, color=TEXTO_PRINCIPAL),
        line=dict(color=TEXTO_PRINCIPAL, width=1.6),
        marker=dict(size=5, color=TEXTO_PRINCIPAL, opacity=opac),
        connectgaps=False,
        showlegend=leyenda, legendgroup="neto",
        # Contado en el hover del neto: cuanto valor se conto para producir
        # ese ajuste. Contexto, no denominador (ver el docstring del modulo).
        customdata=s[["contado"]].to_numpy(),
        hovertemplate=(f"<b>Neto: {fmt_hover}</b><br>"
                       "Valor contado: S/ %{customdata[0]:,.0f}<extra></extra>"),
    )
    return sobr, falt, neto


def _marcas_eje(ejes, maximo):
    """Uno de cada `paso` rótulos del eje de categorías, para que entren.

    Plotly NO ralea los rótulos de un eje de categorías con `tickangle=0`
    (que `_layout` fija para todos): con 22 cortes en la serie, o 12 meses
    en un panel de un tercio de tarjeta, salían pegados — «oct 25nov 25dic
    25». La última marca se corre al último periodo, que es el más mirado;
    queda a más de `paso` de la anterior, así que no se pisan."""
    ejes = list(ejes)
    paso = max(1, math.ceil(len(ejes) / maximo))
    marcas = ejes[::paso]
    if ejes and ejes[-1] not in marcas:
        marcas[-1] = ejes[-1]
    return marcas


# Cuántos rótulos entran en el eje X: la serie ocupa el ancho de la tarjeta
# (~1.200px a 1366) y el rótulo más largo de un corte, «15-17 set 26», mide
# ~75px; un panel de familia es un tercio de eso.
_ROTULOS_SERIE = 12
_ROTULOS_PANEL = 4

# Ancho de UN panel de familia. A 1366 la tarjeta deja ~1.230px útiles:
# entran tres paneles enteros y el cuarto asoma, que es lo que avisa que la
# fila se desliza (regla #505).
PX_PANEL = 400


def fig_serie(s, foco=None, alto=alturas.APOYO):
    """La serie grande: barras divergentes + neto, en eje de CATEGORIAS.

    `type="category"` explicito: sin el, «2025» o «S05 26» pueden parsearse
    como numero o fecha y el eje cambia de tipo en silencio (reglas #325 y
    #448)."""
    fig = go.Figure(_trazas(s, foco))
    fig.update_layout(**_layout_aj(
        barmode="relative",
        bargap=0.35,
        hovermode="x unified",
        height=alto,
        # Sin leyenda: la dice la fila del título (`_leyenda_html`), que ya
        # existía — una leyenda de Plotly arriba del trazo costaba ~30px de
        # un alto que no alcanza para entrar en la laptop (regla #505).
        showlegend=False,
        margin=dict(l=10, r=10, t=18, b=10),
        xaxis=dict(type="category", gridcolor=GRIS_BORDE),
        yaxis=dict(gridcolor=GRIS_BORDE, zeroline=False),
    ))
    _marcas = _marcas_eje(s["eje"], _ROTULOS_SERIE)
    fig.update_xaxes(tickmode="array", tickvals=_marcas, ticktext=_marcas)
    fig.add_hline(y=0, line_color=GRIS_TEXTO, line_width=1)
    return fig


def orden_familias(sf):
    """Las familias en el orden en que se leen los paneles.

    Primero las de `FAMILIAS_DE_ENTRADA`, en SU orden —Alimentos, las dos
    bebidas, Vinos, Envases—, a pedido (2026-09-23: «mostrando primero
    alimentos, luego bebidas y luego vinos»): es el orden en que se piensa
    el negocio, y con la fila deslizable lo primero que se ve es lo que más
    se mira. Las demás (Costos producción, si el filtro la trae) van
    después, de mayor a menor ajuste BRUTO (|sobrante| + |faltante|)."""
    presentes = set(sf["grupo"])
    fijas = [f for f in FAMILIAS_DE_ENTRADA if f in presentes]
    resto = (sf[~sf["grupo"].isin(fijas)]
             .assign(_b=lambda x: x["sobrante"].fillna(0) - x["faltante"].fillna(0))
             .groupby("grupo", as_index=False)["_b"].sum()
             .sort_values("_b", ascending=False)["grupo"].tolist())
    return fijas + resto


def fig_familias(sf, foco=None):
    """Mini-graficos (small multiples): la misma serie, una vez por familia,
    en UNA fila que se desliza de costado (el ancho lo fuerza el CSS de
    `vista_evolucion_ajuste`, `PX_PANEL` por familia).

    UNA FILA y no una rejilla de tres, a pedido (2026-09-23): con dos filas
    la tarjeta medía 840px y no entraba en la laptop; con una, los paneles
    se leen de izquierda a derecha en el orden de `orden_familias` y el
    alto es el de un solo panel (regla #505).

    CADA UNO CON SU ESCALA, a proposito: la pregunta es como se MUEVE cada
    familia, y con la escala compartida el ajuste de Alimentos —~20 veces
    el de Vinos— deja a las demás como lineas planas. Por eso los ticks del
    eje Y SI se ven aca (contra la convencion de `_layout`): con escalas
    distintas, una figura sin numeros compararia alturas que no son
    comparables. La magnitud entre familias la da el titulo de cada panel
    (su neto del rango)."""
    grupos = orden_familias(sf)
    n = max(1, len(grupos))
    titulos = [f"<b>{g.capitalize()}</b> · neto "
               f"{fmt_k(sf.loc[sf['grupo'] == g, 'neto'].sum())}"
               for g in grupos]
    # El hueco entre paneles en PÍXELES, no en fracción: la figura mide
    # `n * PX_PANEL` y una fracción fija daría huecos distintos con 2 o 6
    # familias. 44px es lo que piden los ticks del eje Y del panel de la
    # derecha («-50k»).
    fig = make_subplots(rows=1, cols=n, subplot_titles=titulos,
                        horizontal_spacing=min(0.2, 44 / (n * PX_PANEL)))
    for i, g in enumerate(grupos):
        sg = sf[sf["grupo"] == g]
        for t in _trazas(sg, foco, leyenda=False, rotulos=False):
            fig.add_trace(t, row=1, col=i + 1)

    fig.update_layout(**_layout_aj(
        barmode="relative",
        bargap=0.3,
        hovermode="x unified",
        showlegend=False,
        height=alturas.por_filas(1, px_fila=alturas.FILA_MULTIPLOS,
                                 extra=alturas.EXTRA_MULTIPLOS,
                                 minimo=alturas.FILA_MULTIPLOS),
        margin=dict(l=10, r=10, t=24, b=6),
    ))
    _marcas = _marcas_eje(sf.drop_duplicates("_clave")["eje"], _ROTULOS_PANEL)
    fig.update_xaxes(type="category", showgrid=False, tickangle=0,
                     tickfont=dict(size=9), tickmode="array",
                     tickvals=_marcas, ticktext=_marcas)
    fig.update_yaxes(showticklabels=True, nticks=4, tickfont=dict(size=9),
                     gridcolor=GRIS_BORDE, zeroline=True,
                     zerolinecolor=GRIS_TEXTO, zerolinewidth=1,
                     tickformat="~s")
    for a in fig.layout.annotations:
        a.font = dict(size=11, color=TEXTO_PRINCIPAL)
    return fig


# ── LA VISTA ─────────────────────────────────────────────────────────────

def _titulo(texto, sub=""):
    st.markdown(
        f"<div style='font-size:14px;font-weight:600;color:{TEXTO_PRINCIPAL};"
        f"line-height:1.3'>{texto}"
        + (f"<span style='font-weight:400;color:{GRIS_TEXTO};font-size:12px'>"
           f" · {sub}</span>" if sub else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def _leyenda_html():
    """La leyenda de la serie y de los paneles, escrita en la fila del
    título: dos cuadritos y una raya, con los MISMOS colores de las trazas.
    Reemplaza a las dos leyendas de Plotly (una por figura), que se comían
    ~60px de alto entre las dos (regla #505)."""
    def _item(muestra, texto):
        return (f"<span style='display:inline-flex;align-items:center;"
                f"gap:4px;margin-left:12px'>{muestra}"
                f"<span style='font-size:11.5px;color:{GRIS_TEXTO};"
                f"font-weight:400'>{texto}</span></span>")
    _cuad = ("<span style='width:9px;height:9px;border-radius:2px;"
             "background:{c};display:inline-block'></span>")
    _raya = (f"<span style='width:14px;height:2px;background:{TEXTO_PRINCIPAL};"
             "display:inline-block'></span>")
    return (_item(_cuad.format(c=AJUSTE_POS), "Sobrante")
            + _item(_cuad.format(c=AJUSTE_NEG), "Faltante")
            + _item(_raya, "Neto"))


def _soltar_foco():
    """Callback de la pastilla «jul 26 ✕»: suelta el periodo en foco.

    Sube además el contador de la key de la serie: la seleccion de
    `on_select` persiste en la key vieja, y sin el cambio el rerun volveria
    a leer el clic y a poner el foco que se acaba de soltar (#399)."""
    st.session_state[_K_FOCO] = None
    st.session_state[_K_NCLIC] = st.session_state.get(_K_NCLIC, 0) + 1


_K_AREA = "ajuste_evo_filtro_area"


def vista_evolucion_ajuste(d, col_fecha, col_familia, col_area,
                           col_ajuste_val, col_valorizado):
    """UNA tarjeta: la serie y, debajo, quien la explica (las familias).

    Son una sola superficie a proposito (2026-09-23, a pedido, regla #504):
    dependen de verdad —el grano, el área y el periodo en foco mandan en
    las dos— y la dependencia tiene que VERSE. Por eso los controles van en
    la cabecera, arriba de las dos, y el periodo en foco se escribe en una
    pastilla «jul 26 ✕»: el filtro activo queda dicho, no hay que deducirlo
    de las barras apagadas.

    ENTRA EN UNA LAPTOP (regla #505): la leyenda va en la fila del título,
    la serie mide `alturas.EVO_SERIE` y los paneles son UNA fila que se
    desliza de costado. Medía 840px; ahora cabe en el `--alto-util` de
    1366x768.

    `d` ya viene recortado por el rango de la franja y por la Familia del
    compartimento de arriba de la pila. El Área la filtra la propia vista.
    """
    if not col_fecha or col_fecha not in d.columns:
        st.info("Sin columna de fecha: no se puede armar la evolución.")
        return

    st.markdown(f"<style>{css_filtros_vista('ajevo_ctrl_', 'ajevo_corte_')}"
                "</style>", unsafe_allow_html=True)

    # Sin techo de alto (`estilos/_80_cards.py`): si la ventana es más baja
    # que una laptop, lo que sobra lo scrollea la PÁGINA y no la tarjeta.
    with st.container(border=True, key="ajuste_graf_card_izq_evo"):
        # Los controles se dibujan ANTES de calcular nada: en Streamlit el
        # orden de ejecucion es el orden en que se leen los valores. Las
        # columnas se crean aca y la pastilla se llena mas abajo, cuando ya
        # se sabe si hay foco.
        c_tit, c_area, c_foco, c_gran = st.columns(
            [2.5, 0.95, 0.75, 1.1],  # columnas-internas: titulo | area | foco | grano
            vertical_alignment="center")
        with c_gran:
            gran = st.segmented_control(
                "Agrupar por", GRANOS, default="Mes", key=_K_GRAN,
                label_visibility="collapsed",
                help="Agrupa la serie y los mini-gráficos por familia. "
                     "«Corte» es cada sesión de inventario.",
            ) or "Mes"
        d = filtro_area_en_titulo(c_area, d, col_area, col_ajuste_val,
                                  _K_AREA, "ajevo_ctrl_area")
        # El asistente IA tiene que ver lo que ESTA tarjeta muestra (CLAUDE.md
        # § El asistente IA): el Área ya no está en el compartimento.
        publicar_contexto_ia("Ajuste de Inventario", d, {
            "Familia": st.session_state.get("ajuste_graf_filtro_familia"),
            "Área": st.session_state.get(_K_AREA)})

        dp, orden = periodos_ajuste(d, col_fecha, gran)
        if orden.empty:
            with c_tit:
                _titulo("Sobrante, faltante y neto")
            st.info("Sin datos en el rango y el área seleccionados.")
            return

        # El clic se resuelve ANTES de dibujar (regla #399).
        eje_a_clave = dict(zip(orden["eje"], orden["_clave"]))
        foco = st.session_state.get(_K_FOCO)
        k_fig = f"ajuste_evo_serie_{st.session_state.get(_K_NCLIC, 0)}"
        _ev = st.session_state.get(k_fig) or {}
        _pts = (_ev.get("selection") or {}).get("points") or []
        if _pts:
            _cl = eje_a_clave.get(_pts[0].get("x"))
            foco = None if _cl is None or _cl == foco else _cl
            st.session_state[_K_FOCO] = foco
            st.session_state[_K_NCLIC] = st.session_state.get(_K_NCLIC, 0) + 1
            k_fig = f"ajuste_evo_serie_{st.session_state[_K_NCLIC]}"
        if foco not in set(orden["_clave"]):
            # Otro grano u otro rango: el periodo en foco ya no existe.
            foco = None
            st.session_state[_K_FOCO] = None

        with c_tit:
            st.markdown(
                f"<div style='font-size:14px;font-weight:600;"
                f"color:{TEXTO_PRINCIPAL};line-height:1.3;white-space:nowrap' "
                f"title='Clic en una barra para resaltar ese período'>"
                f"Sobrante, faltante y neto{_leyenda_html()}</div>",
                unsafe_allow_html=True)
        if foco is not None:
            with c_foco:
                st.button(
                    orden.loc[orden["_clave"] == foco, "eje"].iloc[0],
                    icon=":material/close:", key="ajuste_evo_soltar",
                    on_click=_soltar_foco,
                    help="Período resaltado en la serie y en las familias. "
                         "Clic para soltarlo.",
                )

        s = serie_ajuste(dp, orden, col_ajuste_val, col_valorizado)
        st.plotly_chart(
            fig_serie(s, foco, alto=alturas.EVO_SERIE),
            use_container_width=True, key=k_fig,
            on_select="rerun", selection_mode="points",
            config={"displayModeBar": False},
        )

        # ── Debajo, en la MISMA tarjeta: quien explica cada periodo ──────
        if (col_familia and col_familia in dp.columns
                and dp[col_familia].nunique() > 1):
            sf = serie_ajuste(dp, orden, col_ajuste_val, col_valorizado,
                              col_grupo=col_familia)
            _n = sf["grupo"].nunique()
            _desliza = " · deslizá para ver las demás →" if _n > 3 else ""
            st.markdown(
                f'<div class="ajevo-divisor">Por familia · cada panel con su '
                f'propia escala{_desliza}</div>', unsafe_allow_html=True)
            # El ancho de la fila lo fuerza el CSS sobre el CONTENEDOR:
            # `st.plotly_chart` pisa `fig.layout.width` con el de su
            # contenedor, y agrandando el contenedor el ResizeObserver de
            # Streamlit redimensiona la figura (mismo camino que
            # `_distribucion._forzar_ancho`, regla #494). El `overflow-x`
            # del envoltorio deja deslizar lo que sobra. Sin guard de «una
            # sola vez» (regla #59).
            st.markdown(
                "<style>.st-key-ajevo_multiplos [data-testid='stPlotlyChart'],"
                ".st-key-ajevo_multiplos [data-testid='stFullScreenFrame']"
                f"{{width:max(100%, {_n * PX_PANEL}px) !important;}}</style>",
                unsafe_allow_html=True)
            with st.container(key="ajevo_multiplos"):
                st.plotly_chart(fig_familias(sf, foco),
                                use_container_width=True,
                                key="ajuste_evo_familias",
                                config={"displayModeBar": False})
