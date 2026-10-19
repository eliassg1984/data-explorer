"""Detalle contextual de una celda de Platos, Grupos o Áreas.

Trabaja sobre el mismo tramo filtrado del mapa: nunca vuelve a cargar otro
rango ni asigna personas a los ítems de un pedido.
"""

import html
from hashlib import sha1

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from graficos import alturas
from tema import ACENTO, GRIS_CUADRICULA, GRIS_TEXTO, TEXTO_PRINCIPAL

MEDIDAS = {"venta": "Venta", "cant": "Unidades", "desc": "Descuento"}
DIAS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")


def preparar(tramo, que, nombre, hora=None, medida="venta", por_dia=False):
    """Cuentas de una celda o del perfil completo (``hora=None``).

    El divisor incluye los días con venta del ámbito, también aquellos sin
    ese plato ni esa hora: es exactamente el de la matriz del mapa.
    """
    if medida not in MEDIDAS:
        raise ValueError("La medida debe pertenecer a los ítems de venta")
    if tramo is None:
        tramo = pd.DataFrame(columns=[que, "hora", "dia", "dow",
                                      "venta", "cant", "desc"])
    base = tramo.copy()
    dias = pd.DatetimeIndex(pd.to_datetime(base["dia"].dropna().unique())).sort_values()
    n_dias = len(dias)
    divisor = max(1, n_dias) if por_dia else 1
    objeto = base.loc[base[que].eq(nombre)] if que in base else base.iloc[:0]
    contexto = base if hora is None else base.loc[base["hora"].eq(hora)]
    filas = objeto if hora is None else objeto.loc[objeto["hora"].eq(hora)]
    totales = {m: float(filas[m].sum()) for m in MEDIDAS}
    valores = {m: v / divisor for m, v in totales.items()}
    importe_base = float(contexto[medida].sum())
    participacion = (totales[medida] / importe_base * 100
                     if importe_base else None)
    diario = (filas.groupby("dia")[medida].sum().reindex(dias, fill_value=0)
              .rename_axis("Fecha").rename(MEDIDAS[medida]))
    horario = objeto.groupby("hora")[medida].sum() / divisor
    semanal = objeto.groupby("dow")[medida].sum().reindex(range(7), fill_value=0)
    if por_dia:
        cuenta = base.drop_duplicates("dia")["dow"].value_counts()
        den = pd.Series([cuenta.get(w, 0) for w in range(7)], index=range(7))
        semanal = semanal.div(den.replace(0, np.nan)).fillna(0)
    ranking = (contexto.groupby(que)[medida].sum().rank(ascending=False, method="min")
               if que in contexto else pd.Series(dtype=float))
    puesto = int(ranking[nombre]) if nombre in ranking else None
    platos = _agrupar(filas, "prod", medida, divisor)
    canales = _agrupar(filas, "canal", medida, divisor)
    pedidos = _pedidos(filas)
    return {"filas": filas, "dias": n_dias, "divisor": divisor,
            "totales": totales, "valores": valores,
            "participacion": participacion, "puesto": puesto,
            "diario": diario, "horario": horario, "semanal": semanal,
            "platos": platos, "canales": canales, "pedidos": pedidos}


def _agrupar(filas, columna, medida, divisor):
    columnas = ["Nombre", "Valor", "Unidades", "Participación"]
    if columna not in filas:
        return pd.DataFrame(columns=columnas)
    g = filas.groupby(columna, as_index=False).agg(
        Valor=(medida, "sum"), Unidades=("cant", "sum"))
    g = g.rename(columns={columna: "Nombre"}).sort_values("Valor", ascending=False)
    total = float(g["Valor"].sum())
    g["Participación"] = g["Valor"] / total * 100 if total else np.nan
    g[["Valor", "Unidades"]] = g[["Valor", "Unidades"]] / divisor
    return g[columnas].reset_index(drop=True)


def _pedidos(filas):
    # Los importes son sólo los ítems del contexto, no el total del pedido.
    columnas = ["Fecha", "Hora", "Pedido", "Canal", "Plato", "Unidades", "Venta"]
    if "ped" not in filas:
        return pd.DataFrame(columns=columnas)
    x = filas.copy()
    for c in ("canal", "prod"):
        if c not in x:
            x[c] = "—"
    g = x.groupby(["dia", "hora", "ped", "canal", "prod"], as_index=False).agg(
        Unidades=("cant", "sum"), Venta=("venta", "sum"))
    g = g.rename(columns={"dia": "Fecha", "hora": "Hora", "ped": "Pedido",
                          "canal": "Canal", "prod": "Plato"})
    return g[columnas].sort_values(["Fecha", "Hora", "Venta"],
                                   ascending=[False, False, False])


def formato(v, medida, por_dia=False):
    if v is None or not np.isfinite(v):
        return "—"
    return ((f"S/ {v:,.1f}" if por_dia else f"S/ {v:,.0f}")
            if medida in ("venta", "desc") else
            f"{v:,.1f}" if por_dia else f"{v:,.0f}")


def _grafico(x, y, titulo, medida, *, por_dia=False, foco=None):
    color = [ACENTO if str(v) == str(foco) else GRIS_TEXTO for v in x]
    fig = go.Figure(go.Bar(x=list(x), y=list(y), marker_color=color,
                           hovertemplate="%{x}<br>%{y:,.1f}<extra></extra>"))
    fig.update_layout(
        height=alturas.MINI, margin=dict(l=10, r=10, t=30, b=10),
        title=dict(text=titulo, font=dict(size=12)), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11, color=TEXTO_PRINCIPAL), dragmode=False)
    fig.update_xaxes(type="category", fixedrange=True)
    unidad = "S/" if medida in ("venta", "desc") else "Unidades"
    fig.update_yaxes(title=unidad + (" / día" if por_dia else ""),
                     fixedrange=True, gridcolor=GRIS_CUADRICULA)
    return fig


def _tabla_grupo(datos, medida, por_dia, al_producto, key):
    if datos.empty:
        st.caption("Sin platos en esta selección.")
        return
    tabla = datos.rename(columns={"Nombre": "Plato", "Valor": MEDIDAS[medida]})
    fmt = {MEDIDAS[medida]: ("S/ {:,.1f}" if por_dia else "S/ {:,.0f}")
            if medida != "cant" else "{:,.1f}" if por_dia else "{:,.0f}",
           "Unidades": "{:,.1f}" if por_dia else "{:,.0f}",
           "Participación": "{:.1f}%"}
    # Si la medida ya es Unidades no se repite esa columna.
    tabla = tabla.loc[:, ~tabla.columns.duplicated()]

    def elegir():
        seleccion = st.session_state[key].selection.rows
        if seleccion:
            al_producto(str(datos.iloc[seleccion[0]]["Nombre"]))

    st.dataframe(tabla.style.format(fmt, na_rep="—"), hide_index=True,
                 use_container_width=True,
                 on_select=elegir, selection_mode="single-row", key=key,
                 height=alturas.por_filas(len(tabla), px_fila=30, extra=40,
                                          rol=alturas.MINI, minimo=70))
    st.caption("Elige un plato para ver su detalle en este mismo contexto.")


def dibujar(tramo, *, que, nombre, hora, periodo, base_temporal, medida,
            horas, por_dia, perfil, al_perfil, al_cerrar, al_ampliar,
            ampliado, al_producto, referencia=None):
    datos = preparar(tramo, que, nombre, None if perfil else hora,
                      medida, por_dia)
    # Una fila seleccionada en otra hora/período no vuelve a abrirse sola.
    firma = sha1(repr((que, nombre, hora, periodo, perfil, medida, por_dia))
                 .encode()).hexdigest()[:12]
    esc = html.escape
    hora_txt = f"{hora % 12 or 12} {'am' if hora < 12 else 'pm'}"
    alcance = "todas las horas" if perfil else hora_txt
    with st.container(horizontal=True, vertical_alignment="center",
                      key="vh_fila_cabecera"):
        with st.container(width="stretch"):
            st.markdown(f'<p class="vh-fila-titulo">{esc(nombre)} · '
                        f'{alcance}</p>', unsafe_allow_html=True)
        st.button("Volver a la celda" if perfil else "Ver perfil completo",
                  key="vh_fila_perfil_btn", on_click=al_perfil,
                  icon=":material/arrow_back:" if perfil else ":material/insights:")
        st.button("Volver al mapa" if ampliado else "Ampliar",
                  key="vh_detalle_ampliar", on_click=al_ampliar,
                  icon=":material/close_fullscreen:" if ampliado else
                       ":material/open_in_full:")
        st.button("Cerrar", key="vh_fila_cerrar", on_click=al_cerrar,
                  icon=":material/close:")
    calculo = "Promedio por día con venta" if por_dia else "Total"
    st.caption(f"{periodo} · {datos['dias']} días con venta · {calculo} · "
               f"{base_temporal}")
    extra = "del período filtrado" if perfil else "de esta hora filtrada"
    otro = "venta" if medida == "cant" else "cant"
    parte = datos["participacion"]
    st.markdown(
        '<div class="vh-fila-kpis">'
        f'<span>{MEDIDAS[medida]} <b>{formato(datos["valores"][medida], medida, por_dia)}</b></span>'
        f'<span>{MEDIDAS[otro]} <b>{formato(datos["valores"][otro], otro, por_dia)}</b></span>'
        f'<span>{extra} <b>{f"{parte:.1f}%" if parte is not None else "—"}</b></span>'
        '</div>', unsafe_allow_html=True)
    if referencia is not None and not perfil:
        previo = preparar(referencia["tramo"], que, nombre, hora, medida, por_dia)
        delta = datos["valores"][medida] - previo["valores"][medida]
        st.caption(f"Diferencia frente a {referencia['periodo']}: "
                   f"{'+' if delta > 0 else '−' if delta < 0 else ''}"
                   f"{formato(abs(delta), medida, por_dia)}")
    opciones = ["Perfil del período" if perfil else "Resumen"]
    if que != "prod":
        opciones.append("Platos del grupo" if que == "grupo" else "Platos del área")
    opciones.append("Pedidos")
    if st.session_state.get("vh_fila_tab") not in opciones:
        st.session_state["vh_fila_tab"] = opciones[0]
    vista = st.pills("Contenido", opciones, key="vh_fila_tab",
                     label_visibility="collapsed") or opciones[0]
    if vista == "Pedidos":
        st.caption("Cada fila contiene los ítems seleccionados de un pedido; "
                   "sus importes son totales, sin promediar.")
        tabla = datos["pedidos"].copy()
        tabla["Hora"] = tabla["Hora"].map(lambda h: f"{h % 12 or 12} "
                                          f"{'am' if h < 12 else 'pm'}")
        st.dataframe(tabla, hide_index=True, use_container_width=True,
                     column_config={"Venta": st.column_config.NumberColumn(format="S/ %.2f")},
                     height=alturas.por_filas(len(tabla), px_fila=30, extra=40,
                                              rol=alturas.APOYO, minimo=70))
        return
    if vista.startswith("Platos del"):
        _tabla_grupo(datos["platos"], medida, por_dia, al_producto,
                      f"vh_fila_platos_tabla_{firma}")
        return
    a, b = st.columns([1.05, 1], gap="medium")
    if perfil:
        curva = datos["horario"].reindex(horas, fill_value=0)
        etq = [f"{h % 12 or 12} {'am' if h < 12 else 'pm'}" for h in horas]
        with a:
            st.plotly_chart(_grafico(etq, curva, "Distribución por hora", medida,
                                     por_dia=por_dia, foco=hora_txt),
                            use_container_width=True, key="vh_fila_curva",
                            config={"displayModeBar": False})
        with b:
            st.plotly_chart(_grafico(DIAS, datos["semanal"],
                                     "Distribución por día de semana", medida,
                                     por_dia=por_dia),
                            use_container_width=True, key="vh_fila_semana",
                            config={"displayModeBar": False})
        puesto = datos["puesto"]
        st.caption(f"Puesto {'#'+str(puesto) if puesto else '—'} por "
                   f"{MEDIDAS[medida].lower()} en el período filtrado. "
                   f"Hora de la celda conservada: {hora_txt}.")
        return
    with a:
        serie = datos["diario"]
        st.plotly_chart(_grafico([pd.Timestamp(d).strftime("%d/%m") for d in serie.index],
                                 serie, f"{MEDIDAS[medida]} a las {hora_txt} · por fecha",
                                 medida), use_container_width=True,
                        key="vh_fila_diario", config={"displayModeBar": False})
        st.caption("Cada barra es una fecha con venta del ámbito; se incluyen "
                   "los días sin venta de este elemento en esa hora.")
    with b:
        if que != "prod":
            st.caption("Platos que explican esta hora")
            _tabla_grupo(datos["platos"].head(5), medida, por_dia,
                          al_producto, f"vh_fila_platos_resumen_{firma}")
        else:
            st.caption("Canal de venta · misma hora y período")
            canales = datos["canales"].rename(columns={"Nombre": "Canal",
                                                       "Valor": MEDIDAS[medida]})
            canales = canales.loc[:, ~canales.columns.duplicated()]
            fmt = {MEDIDAS[medida]: ("S/ {:,.1f}" if por_dia else "S/ {:,.0f}")
                   if medida != "cant" else "{:,.1f}" if por_dia else "{:,.0f}",
                   "Unidades": "{:,.1f}" if por_dia else "{:,.0f}",
                   "Participación": "{:.1f}%"}
            st.dataframe(canales.style.format(fmt, na_rep="—"),
                         hide_index=True, use_container_width=True)
