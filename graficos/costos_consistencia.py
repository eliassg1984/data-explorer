"""graficos.costos_consistencia — Costos › «Consistencia del maestro».

VISTA NUEVA EL 2026-10-21, a pedido («quiero saber si mi sistema a nivel
data maestra es lógico»), sobre un boceto con los datos reales
(https://claude.ai/artifact/JDqYExY3U12yEfTrnewdhJ). Una lista de CONTROLES
—preguntas que el maestro del POS y del Almacén debería poder contestar sin
contradecirse— y, al costado, la ficha del elegido: por qué importa, la
regla, qué hacer y TODOS sus casos, con su CSV.

La cuenta vive en `consistencia_maestro.py` (pura, con su test); la carga,
en `data.consistencia_maestro` (caché de disco con los sellos de catorce
parquets: la primera vez de cada versión tarda alrededor de un minuto). Este
módulo sólo la dibuja.

Cinco grupos: Stock, Recetas, Carta y ventas, Compras y «Movimientos
raros». Los cuatro primeros son el ESTADO del maestro hoy; el quinto junta
EVENTOS con fecha que otros reportes ya marcan de a uno (un cambio de
factor, una merma imposible, un día sin descargo de ventas, las
anulaciones de un usuario): señales, no pruebas.

Regla #686.
"""

import hashlib

import pandas as pd
import streamlit as st

import consistencia_maestro as cm
import data
from graficos import alturas
from tema import (
    AJUSTE_ALERTA_FONDO, AJUSTE_ALERTA_TEXTO, AJUSTE_CRIT_FONDO,
    AJUSTE_CRIT_TEXTO, AJUSTE_POS_TEXTO, EXITO_FONDO, GRIS_TEXTO, LAVANDA_FONDO,
)

_ESTADO = {
    cm.ROJO: ("Revisar ya", AJUSTE_CRIT_TEXTO, AJUSTE_CRIT_FONDO),
    cm.AMBAR: ("Mirar", AJUSTE_ALERTA_TEXTO, AJUSTE_ALERTA_FONDO),
    cm.VERDE: ("En orden", AJUSTE_POS_TEXTO, EXITO_FONDO),
    cm.FALLO: ("No se pudo calcular", GRIS_TEXTO, ""),
}
_TODO = "todo"
_K_DOM = "cm_dominio"
_K = "cm_lista"
_K_FOCO = "cm_foco"


def _soles(v):
    """«S/ 1,234», o «—». Como texto: un NaN en `st.dataframe` se pinta
    «None» aunque el Styler lo formatee (regla #529)."""
    if pd.isna(v):
        return "—"
    return f"{'−' if v < 0 else ''}S/ {abs(v):,.0f}"


def _key_tabla(ids):
    """La key de la lista lleva la firma de sus filas: la selección de un
    `st.dataframe` es de la KEY, no de sus datos (regla #556)."""
    return f"{_K}_" + hashlib.md5("|".join(ids).encode("utf-8")).hexdigest()[:12]


def _fila_elegida(evt):
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        filas = (sel or {}).get("rows", [])
        return filas[0] if filas else None
    except Exception:
        return None


def _leer_eleccion():
    """El control que la lista tenía elegido en la corrida anterior, al foco.
    Se lee ANTES de dibujar: la lista nueva sale con él marcado."""
    ss = st.session_state
    key, ids = ss.get(f"_{_K}_key"), ss.get(f"_{_K}_ids") or []
    fila = _fila_elegida(ss.get(key)) if key else None
    if fila is not None and 0 <= fila < len(ids):
        ss[_K_FOCO] = ids[fila]


def _chip(estado):
    txt, tinta, fondo = _ESTADO[estado]
    return (f'<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
            f'font-size:12px;font-weight:600;color:{tinta};background:{fondo}">{txt}</span>')


def _lista(res, dom):
    """La lista de controles del grupo `dom`, con la fila en foco marcada.
    Devuelve el id del control en foco."""
    vis = res if dom == _TODO else res[res["dominio"] == dom]
    ids = vis["id"].tolist()
    foco = st.session_state.get(_K_FOCO)
    if foco not in ids:
        # Abre en el primero que pide acción; si no hay, en el primero que
        # pide mirar. El verde no tiene nada que ver.
        rojos = vis.loc[vis["estado"] == cm.ROJO, "id"].tolist()
        ambar = vis.loc[vis["estado"] == cm.AMBAR, "id"].tolist()
        foco = (rojos or ambar or ids)[0]
        st.session_state[_K_FOCO] = foco
    pos = ids.index(foco)
    # Cuatro columnas: con el grupo y «se concentra en» la lista no entraba
    # en su mitad a 1323px (medido). Los dos van en la ficha.
    filas = pd.DataFrame({
        "Estado": [_ESTADO[e][0] for e in vis["estado"]],
        "Control": vis["nombre"],
        "Casos": vis["casos"].map(lambda n: f"{n:,}"),
        "S/ en juego": vis["soles"].map(_soles),
    }).reset_index(drop=True)
    estados = vis["estado"].tolist()

    def _fila(r):
        return ([f"background-color: {LAVANDA_FONDO}"] * len(r)
                if r.name == pos else [""] * len(r))

    def _estado(col):
        return [f"color: {_ESTADO[e][1]}; background-color: {_ESTADO[e][2]}; "
                f"font-weight: 600" for e in estados]

    sty = filas.style.apply(_fila, axis=1).apply(_estado, subset=["Estado"])
    ss = st.session_state
    key = _key_tabla(ids)
    ss[f"_{_K}_key"], ss[f"_{_K}_ids"] = key, ids
    st.dataframe(
        sty, key=key, on_select="rerun", selection_mode="single-row-required",
        selection_default={"selection": {"rows": [pos]}},
        hide_index=True, row_height=27,
        height=alturas.por_filas(len(filas), px_fila=27, extra=38, minimo=0,
                                 rol=alturas.CONSISTENCIA_LISTA),
        column_config={
            "Estado": st.column_config.TextColumn(width=100),
            "Control": st.column_config.TextColumn(width="medium"),
            "Casos": st.column_config.TextColumn(width=60),
            "S/ en juego": st.column_config.TextColumn(width=96),
        })
    return foco


def _tabla_casos(c, casos):
    """Los casos de un control con los rótulos de su ficha, sin las columnas
    que el control no llena."""
    col_nombre, col_area, col_dato = c.columnas
    d = pd.DataFrame({
        "Código": casos["codigo"].astype(str),
        col_nombre: casos["nombre"].fillna("").astype(str),
        col_area or "Área": casos["area"].fillna("").astype(str),
        col_dato: casos["dato"].fillna("").astype(str),
        "S/": casos["soles"].map(_soles),
        "Fecha": pd.to_datetime(casos["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
                   .fillna(""),
        "Usuario": casos["quien"].fillna("").astype(str),
    })
    orden = casos["soles"].abs().sort_values(ascending=False, na_position="last").index
    d = d.loc[orden].reset_index(drop=True)
    vacias = [k for k in d.columns if k != col_nombre and (d[k].isin(("", "—"))).all()]
    return d.drop(columns=vacias)


def _ficha(foco, res, casos):
    c = cm.POR_ID[foco]
    fila = res.set_index("id").loc[foco]
    r = casos.get(foco)
    st.markdown(f'{_chip(fila["estado"])} &nbsp;<span style="color:{GRIS_TEXTO};'
                f'font-size:12px">{dict(cm.DOMINIOS)[c.dominio]}</span>',
                unsafe_allow_html=True)
    st.markdown(f"**{c.nombre}**  \n{c.mide}.")
    st.markdown(c.porque)
    if not isinstance(r, pd.DataFrame):
        st.warning(f"Este control no se pudo calcular: {r}")
        return
    linea = f"**{len(r):,} casos**"
    if pd.notna(fila["soles"]):
        linea += f" · {_soles(fila['soles'])} en juego"
    if fila["concentra"]:
        linea += f" · se concentra en {fila['concentra']}"
    st.markdown(linea)
    if not r.empty:
        t = _tabla_casos(c, r)
        st.dataframe(t, hide_index=True, row_height=27,
                     height=alturas.por_filas(len(t), px_fila=27, extra=38, minimo=0,
                                              rol=alturas.CONSISTENCIA_CASOS),
                     column_config={"Código": st.column_config.TextColumn(width=72),
                                    c.columnas[0]: st.column_config.TextColumn(width="medium"),
                                    "S/": st.column_config.TextColumn(width=84)})
        st.download_button(
            "Descargar los casos (CSV)", t.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"consistencia_{c.id}_{c.nombre}.csv".replace(" ", "_"),
            mime="text/csv", key=f"cm_csv_{c.id}")
    st.markdown(f"**Qué hacer:** {c.accion}")
    detalle = f"**La regla:** {c.regla}"
    if c.ya_lo_ve:
        detalle += f"  \n**Ya lo marca:** {c.ya_lo_ve}"
    st.caption(detalle)


def _csv_todo(casos):
    partes = [r.assign(control=cm.POR_ID[k].nombre)
              for k, r in casos.items() if isinstance(r, pd.DataFrame) and len(r)]
    if not partes:
        return b""
    d = pd.concat(partes, ignore_index=True)
    return d[["control", *cm.CASOS]].to_csv(index=False).encode("utf-8-sig")


def renderizar():
    """La vista entera, en su tarjeta. La llama `graficos/costos.py` cuando
    el rail está en «Consistencia del maestro»."""
    with st.container(border=True, key="ajuste_graf_card_izq_cmaestro"):
        with st.spinner("Revisando el maestro… la primera vez del día tarda "
                        "alrededor de un minuto."):
            r = data.consistencia_maestro()
        if not r:
            st.warning("No se pudo revisar el maestro (¿R2 caído?). Reintentá "
                       "en unos segundos.")
            return
        casos = r["casos"]
        res = cm.resumen(casos)
        n = res["estado"].value_counts()
        # columnas-internas: el título y la descarga de todo, en un renglón.
        c_tit, c_csv = st.columns([4, 1], vertical_alignment="bottom")
        with c_tit:
            st.markdown("**¿El maestro del sistema tiene lógica?** "
                        f"{n.get(cm.ROJO, 0)} controles para revisar ya, "
                        f"{n.get(cm.AMBAR, 0)} para mirar y {n.get(cm.VERDE, 0)} "
                        f"en orden.")
            st.caption(f"Corte: {pd.Timestamp(r['hoy']):%d/%m/%Y}, el último día "
                       "del kardex · 90 días hacia atrás (180 para «no se usa», un "
                       "año para los movimientos raros). «Movimientos raros» son "
                       "señales, no pruebas.")
        with c_csv:
            st.download_button("Todos los casos (CSV)", _csv_todo(casos),
                               file_name="consistencia_maestro.csv", mime="text/csv",
                               key="cm_csv_todo", width="stretch")
        opciones = [_TODO, *(d for d, _ in cm.DOMINIOS)]
        rotulos = {_TODO: "Todo", **dict(cm.DOMINIOS)}
        dom = st.segmented_control(
            "Grupo", opciones, default=_TODO, key=_K_DOM,
            format_func=rotulos.get, label_visibility="collapsed") or _TODO
        _leer_eleccion()
        # columnas-internas: la lista y la ficha del control elegido.
        c_lista, c_ficha = st.columns([1.25, 1], gap="medium")
        with c_lista:
            foco = _lista(res, dom)
        with c_ficha:
            _ficha(foco, res, casos)
