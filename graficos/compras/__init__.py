"""graficos.compras - dashboard de Compras (5 drills).

Este modulo era un unico compras.py de 2.835 lineas; desde el refactor de
2026-08-01 es un paquete con un drill por archivo, igual que graficos/ tiene
un dashboard por archivo.

    _comun.py         helpers compartidos (movil, seleccion, mini barras)
    proveedor.py      drill de Proveedor (el mas grande)
    producto.py       drill de Producto: ranking + precio/cantidad/valor
                      (incluye el ranking por Familia — ver docstring propio)
    volatilidad.py    drill de Volatilidad: ranking (AgGrid, tooltip +
                      clic en fila) + candlestick + compras de la semana
    vs_ano_pasado.py  drill "Vs año pasado": Precio o Cantidad de un
                      producto en comun, o Valor por Familia (sin
                      selector), cada uno contra su serie del año
                      pasado/anterior

Punto de entrada publico: renderizar_graficos_compras (lo consume el
dispatcher de graficos/__init__.py). Vive aca abajo junto a la config del
rail derecho, que es lo que decide que drill se muestra.

_first_point y _periodo_serie se re-exportan porque test_graficos.py los
importa desde graficos.compras.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import GRIS_BORDE
from utils import _norm
from graficos.base import (
    PALETA_CALLAI, _compras_layout, _compras_truncar, _render_rail,
    _resolver, publicar_contexto_ia, renderizar_graficos_genericos,
    vista_activa,
)
from graficos.constructor import _constructor_grafico
from graficos.compras._comun import (  # noqa: F401  (re-export)
    _compras_mini_barras, _es_movil, _first_point, _periodo_serie,
)
from graficos.compras.proveedor import _compras_proveedor_drill
from graficos.compras.producto import _compras_producto_drill
from graficos.compras.volatilidad import _compras_volatilidad_drill
from graficos.compras.vs_ano_pasado import _compras_vs_ano_pasado_drill
from graficos import alturas




# Rail de Compras — cabecera "Compras / Gráficos" + secciones agrupadas por
# categoría (variante 2). Cada tupla es (id, label, icono):
#   · id     — el string que consume el resto del dashboard.
#   · label  — lo que se pinta en el botón del rail.
#   · icono  — shortcode Material que va al `icon=` de st.button.
# El icono es el TERCER elemento y `_render_rail` lo trata como opcional, así
# que los otros rails (Ajuste) siguen con tuplas de 2 sin enterarse. Nombres
# validados contra `streamlit.string_util.validate_material_icon`: si uno no
# existe, Streamlit tira StreamlitAPIException al dibujar el rail, o sea la
# pantalla entera. Ver arquitectura.md regla #147.
_COMPRAS_RAIL_CATEGORIAS = (
    ("Dimensión", (("Proveedor",        "Proveedor",     ":material/local_shipping:"),
                   ("Producto",         "Producto",      ":material/inventory_2:"))),
    ("Precios",   (("Vs año pasado",    "Vs año pasado", ":material/compare_arrows:"),
                   ("Volatilidad",      "Volatilidad",   ":material/candlestick_chart:"))),
    ("SUNAT",     (("Documentos SUNAT", "Documentos",    ":material/receipt_long:"),)),
    ("Más",       (("Semanal",          "Semanal",       ":material/calendar_view_week:"),
                   ("Personalizado",    "Personalizado", ":material/tune:"),
                   ("Tabla",            "Tabla",         ":material/table_rows:"))),
)

# Vistas de Compras que dibujan el selector de fecha DENTRO de su tarjeta en
# vez de dejarlo en la franja superior. Hoy solo Documentos SUNAT: ahi la
# fecha no es contexto global sino EL filtro de la tabla (es el rango que se
# le consulta al SIRE), asi que vivia lejos de lo que filtra.
_VISTAS_CON_FECHA_PROPIA = {"Documentos SUNAT"}


def vista_quiere_fecha_propia():
    """True si la vista activa de Compras se queda el pill de fecha.

    La consulta `app.py` ANTES de dibujar la franja, para saber si le toca
    dibujarlo a el o al drill — el widget no se puede duplicar (su key es la
    clave canonica del rango, ver `franja_fecha`). Se resuelve sin dibujar el
    rail con `vista_activa`, que usa el mismo criterio que el rail usara
    despues, deep-link incluido.
    """
    return vista_activa(_COMPRAS_RAIL_CATEGORIAS,
                        "compras_graf_tipo") in _VISTAS_CON_FECHA_PROPIA


def renderizar_graficos_compras(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard dedicado de Compras: 5 gráficos con pestañas + 5 mini-tops.

    `tabla_cb` se acepta por uniformidad de firma con el resto de
    dashboards (ver graficos/__init__.py) pero NO se usa: la vista Tabla
    de Compras es un item más de su propio rail y la arma este módulo,
    con los mismos chips Familia/Subfamilia que los gráficos."""
    col_fam    = _resolver(df_f, ["Familia", "Nombre Familia"])
    col_subfam = _resolver(df_f, ["Subfamilia", "Nombre Subfamilia"])
    col_prov   = _resolver(df_f, ["Nombre_proveedor", "Nombre proveedor", "Proveedor"])
    col_prod   = _resolver(df_f, ["Nombre_producto", "Nombre producto", "Producto"])
    col_um     = _resolver(df_f, ["Unidad de Ingreso", "Unidad_de_ingreso",
                                  "Unidad Ingreso", "Unidad Kardex", "Unidad_medida",
                                  "Unidad medida", "Unidad de medida", "Unidad_compra",
                                  "Unidad compra", "Unidad", "UM", "Und"])
    col_cant   = _resolver(df_f, ["Cantidad_compra", "Cantidad compra", "Cantidad"])
    col_valor  = _resolver(df_f, ["Valor_compra", "Valor compra", "Importe Total", "Valorizado"])
    col_val_aa = _resolver(df_f, ["Valor_ano_anterior", "Valor año anterior"])
    col_punit  = _resolver(df_f, ["Precio_unit", "Precio unit", "Precio Unitario"])
    col_punit_ant = _resolver(df_f, ["Ultimo_precio_unit", "Ultimo precio unit",
                                     "Ultimo_anterior", "Ultimo anterior"])
    col_fecha  = _resolver(df_f, ["Fecha_documento", "Fecha documento",
                                  "Fecha_registro", "Fecha registro", "FECHA"])
    col_docu   = _resolver(df_f, ["Num Documento", "Num_Documento",
                                  "Numero Documento", "Numero_documento",
                                  "Nro Documento", "Nro_Documento", "Num Doc",
                                  "N Documento", "Documento", "Comprobante"])
    # Solo la usa el drill Volatilidad (mezclar monedas en una misma serie de
    # precio sería incorrecto). Ninguna otra vista de Compras la resuelve, y
    # el demo local no la trae — por eso el drill la trata como opcional.
    col_moneda = _resolver(df_f, ["Tipo_moneda", "Tipo Moneda", "Moneda"])
    if not col_fecha:
        for _c in df_f.columns:
            if pd.api.types.is_datetime64_any_dtype(df_f[_c]) or "fecha" in _norm(str(_c)):
                col_fecha = _c
                break

    if not col_valor:
        st.warning("No se encontró la columna de valor de compra. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Familia / Subfamilia como chips en la FRANJA blanca ──────
    fam_sel, sub_sel = [], []
    with st.container(key="chips_ajuste_tabla"):
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if col_fam and col_fam in df_f.columns:
                fams = sorted(df_f[col_fam].dropna().astype(str).unique().tolist())
                if fams:
                    _n = len(st.session_state.get("compras_graf_filtro_fam") or [])
                    _lbl = f"Familia :violet-badge[{_n}]" if _n else "Familia"
                    with st.popover(_lbl, use_container_width=True):
                        fam_sel = st.pills(
                            "Familia", fams, selection_mode="multi",
                            key="compras_graf_filtro_fam",
                            label_visibility="collapsed",
                        ) or []
        with c2:
            if col_subfam and col_subfam in df_f.columns:
                _d_sub = df_f
                if fam_sel and col_fam:
                    _d_sub = _d_sub[_d_sub[col_fam].astype(str).isin(fam_sel)]
                subs = sorted(_d_sub[col_subfam].dropna().astype(str).unique().tolist())
                if subs:
                    _n = len(st.session_state.get("compras_graf_filtro_sub") or [])
                    _lbl = f"Subfamilia :violet-badge[{_n}]" if _n else "Subfamilia"
                    with st.popover(_lbl, use_container_width=True):
                        sub_sel = st.pills(
                            "Subfamilia", subs, selection_mode="multi",
                            key="compras_graf_filtro_sub",
                            label_visibility="collapsed",
                        ) or []

    d = df_f
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]
    if sub_sel and col_subfam:
        d = d[d[col_subfam].astype(str).isin(sub_sel)]

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Compras", d,
                         {"Familia": fam_sel, "Subfamilia": sub_sel})

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    # Data SIN filtro de fecha (para el toggle "Todo el histórico" del Panel B
    # del drill Proveedor). Se le aplican los mismos chips Familia/Subfamilia,
    # que no son de fecha. Si no llega df_full, cae a df_f (mismo comportamiento).
    d_full = df_full if df_full is not None else df_f
    if fam_sel and col_fam and col_fam in d_full.columns:
        d_full = d_full[d_full[col_fam].astype(str).isin(fam_sel)]
    if sub_sel and col_subfam and col_subfam in d_full.columns:
        d_full = d_full[d_full[col_subfam].astype(str).isin(sub_sel)]

    _valor = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)

    opciones = ["Proveedor", "Producto", "Vs año pasado", "Volatilidad",
                "Documentos SUNAT", "Semanal", "Personalizado", "Tabla"]

    # Rail vertical fijo al borde DERECHO (componente compartido _render_rail):
    # selector de tipo de gráfico agrupado por categoría. El activo se marca
    # con type="primary"; la selección se persiste en compras_graf_tipo.
    graf = _render_rail(_COMPRAS_RAIL_CATEGORIAS, "compras_graf_tipo")
    if graf not in opciones:
        graf = opciones[0]

    # ── Quien dibuja el pill de fecha: la franja o el drill ──────────────
    # Hay UNA vista que se lo queda (Documentos SUNAT). El problema es de
    # ORDEN: la franja de `app.py` se dibuja mucho antes que este rail, y
    # ademas `_render_contenido` es un `@st.fragment`, asi que un clic aca
    # NO re-ejecuta `app.py`. En ese rerun parcial la franja sigue con la
    # decision de la vista ANTERIOR:
    #   · entrando a SUNAT  -> la franja ya dibujo la fecha Y el drill la
    #     dibujaria de nuevo: dos widgets con la misma key -> excepcion.
    #   · saliendo de SUNAT -> no la dibujo ninguno de los dos y la vista
    #     se queda sin selector de fecha (medido: eso pasaba).
    # Cuando no coinciden se fuerza un rerun COMPLETO, que es la unica
    # forma de que `app.py` vuelva a decidir. Cuesta un render extra al
    # cruzar esa frontera y nada el resto del tiempo.
    _quiere_propia = graf in _VISTAS_CON_FECHA_PROPIA
    if st.session_state.get("_franja_dibujo_fecha", True) == _quiere_propia:
        st.rerun(scope="app")

    # Tabla: usa el mismo AgGrid de la vista Tabla, pero como una opción más
    # del selector. `d` ya viene filtrado por los chips Familia/Subfamilia.
    if graf == "Tabla":
        from tablas import renderizar_aggrid_compras as _render_tabla_compras
        from estilos import TAM_FUENTE
        _font_px = TAM_FUENTE.get(st.session_state.get("tabla_tam", "Mediano"), 14)
        _render_tabla_compras(d, _font_px)
        return

    # Constructor: ancho completo, sin panel de mini-tops.
    if graf == "Personalizado":
        with st.container(border=True, key="ajuste_graf_card_izq_compras"):
            _constructor_grafico(d, "compras")
        return

    # Producto: ancho completo (ranking de todos los productos + evolución
    # del producto en foco + ranking por familia). Sin borde externo, igual
    # que Proveedor: cada bloque interno lleva su propio borde.
    if graf == "Producto":
        with st.container(key="compras_prod_drill_wrap"):
            _compras_producto_drill(d, col_prod, col_fam, col_valor, col_cant,
                                    col_punit, col_um, col_fecha, col_prov)
        return

    # Proveedor: ancho completo (drill Proveedor→productos→proveedores del prod.).
    # Sin borde externo: cada uno de los 4 bloques internos (gráfico, panel A,
    # panel B, tabla AgGrid) lleva su propio borde para separación visual
    # limpia sin cajas anidadas.
    if graf == "Proveedor":
        with st.container(key="compras_prov_drill_wrap"):
            _compras_proveedor_drill(d, col_prov, col_prod, col_cant, col_valor,
                                     col_punit, col_um, col_fecha, col_docu,
                                     d_full=d_full)
        return

    # Volatilidad: ranking de insumos por variación de precio semanal +
    # candlestick del insumo elegido + compras de la semana clickeada.
    if graf == "Volatilidad":
        with st.container(border=True, key="ajuste_graf_card_izq_compras"):
            _compras_volatilidad_drill(d, col_prod, col_prov, col_punit, col_fecha,
                                       col_valor, col_cant, col_um, col_moneda)
        return

    # Documentos SUNAT: los comprobantes que los proveedores emitieron hacia
    # nuestro RUC, traídos del SIRE. `d`/`col_fecha` van reservados para el
    # cruce contra el parquet de Compras (ver docstring de
    # renderizar_documentos_sunat); hoy el dato mostrado sale entero de
    # SUNAT. Import local a propósito: arrastra `sunat.py` y, con él,
    # `requests` — no hay por qué pagarlo al importar Compras si nadie abre
    # esta vista.
    if graf == "Documentos SUNAT":
        from graficos.compras.documentos_sunat import renderizar_documentos_sunat
        with st.container(key="compras_sunat_drill_wrap"):
            renderizar_documentos_sunat(d, col_fecha)
        return

    # Vs año pasado: Precio, Cantidad o Valor (selector "Ver") — unifica los
    # tres drills que antes vivían separados en el rail (Precios/Cantidad/
    # Más). Valor es por Familia (col_fam/col_val_aa), sin selector de
    # producto: era el drill aparte "Vs año anterior".
    if graf == "Vs año pasado":
        with st.container(key="compras_vap_drill_wrap"):
            _compras_vs_ano_pasado_drill(d, col_prod, col_punit, col_cant,
                                         col_fecha, col_valor, col_fam, col_val_aa)
        return

    col_izq, col_der = st.columns([1.7, 1])

    with col_izq:
        with st.container(border=True, key="ajuste_graf_card_izq_compras"):
            if graf == "Semanal" and col_prod and col_fecha:
                # Compra por SEMANA: barras apiladas (valor) por producto
                # (top 8 + Otros); el hover muestra valor y cantidad.
                _dias_ini = {"Lunes": 0, "Sábado": 5, "Domingo": 6}
                _cd, _ = st.columns([1, 2.2])
                with _cd:
                    _dini = st.selectbox("La semana empieza:",
                                         list(_dias_ini.keys()),
                                         key="compras_sem_inicio")
                _off = _dias_ini[_dini]
                _fe = pd.to_datetime(d[col_fecha], errors="coerce")
                _sem_ini = (_fe - pd.to_timedelta(
                    (_fe.dt.weekday - _off) % 7, unit="D")).dt.date
                _cnt = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
                        if col_cant else pd.Series(0, index=d.index))
                top = _valor.groupby(d[col_prod].astype(str)).sum().nlargest(8).index
                _pr = d[col_prod].astype(str).where(
                    d[col_prod].astype(str).isin(top), "Otros")
                dd = pd.DataFrame({"sem": _sem_ini, "prod": _pr,
                                   "valor": _valor, "cant": _cnt}).dropna(subset=["sem"])
                g = dd.groupby(["sem", "prod"], as_index=False)[["valor", "cant"]].sum()
                g = g.sort_values("sem")
                g["sem_lbl"] = pd.to_datetime(g["sem"]).dt.strftime("Sem %d/%m")
                fig = go.Figure()
                _prods = ([p_ for p_ in top if p_ in set(g["prod"])] +
                          (["Otros"] if (g["prod"] == "Otros").any() else []))
                for _i, _p in enumerate(_prods):
                    gg = g[g["prod"] == _p]
                    fig.add_bar(
                        x=gg["sem_lbl"], y=gg["valor"],
                        name=_compras_truncar(_p, 22),
                        marker=dict(color=(GRIS_BORDE if _p == "Otros"
                                    else PALETA_CALLAI[_i % len(PALETA_CALLAI)])),
                        customdata=gg["cant"],
                        hovertemplate=("%{fullData.name}<br>%{x}"
                                       "<br>Valor: S/ %{y:,.2f}"
                                       "<br>Cantidad: %{customdata:,.1f}"
                                       "<extra></extra>"),
                    )
                _compras_layout(fig, alto=alturas.PROTAGONISTA)
                fig.update_layout(
                    title="Compra por semana — valor por producto (top 8 + Otros)",
                    barmode="stack",
                    legend=dict(orientation="h", y=-0.22, x=0,
                                font=dict(size=10)),
                )
                fig.update_xaxes(type="category")
                st.plotly_chart(fig, use_container_width=True, key="compras_g_semanal")

            else:
                st.info("No hay columnas suficientes para este gráfico.")

    with col_der:
        with st.container(border=True, key="ajuste_graf_card_der_compras"):
            tabs = st.tabs(["Prod. valor", "Proveedores", "Cantidad",
                            "Frecuencia", "Alzas precio"])
            with tabs[0]:
                if col_prod:
                    _compras_mini_barras(
                        _valor.groupby(d[col_prod].astype(str)).sum().nlargest(10),
                        "prod_valor")
            with tabs[1]:
                if col_prov:
                    _compras_mini_barras(
                        _valor.groupby(d[col_prov].astype(str)).sum().nlargest(10),
                        "prov_valor")
            with tabs[2]:
                if col_prod and col_cant:
                    _cnt = pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
                    _compras_mini_barras(
                        _cnt.groupby(d[col_prod].astype(str)).sum().nlargest(10),
                        "prod_cant", fmt="{:,.0f}")
            with tabs[3]:
                if col_prod:
                    _compras_mini_barras(
                        d[col_prod].astype(str).value_counts().head(10),
                        "prod_freq", fmt="{:,.0f}")
            with tabs[4]:
                if col_prod and col_punit and col_punit_ant:
                    _pu  = pd.to_numeric(d[col_punit], errors="coerce")
                    _pa  = pd.to_numeric(d[col_punit_ant], errors="coerce")
                    base = pd.DataFrame({"prod": d[col_prod].astype(str),
                                         "pu": _pu, "pa": _pa}).dropna()
                    base = base[base["pa"] > 0]
                    if base.empty:
                        st.info("Sin datos de precio anterior.")
                    else:
                        g = base.groupby("prod")[["pu", "pa"]].mean()
                        alza = ((g["pu"] - g["pa"]) / g["pa"] * 100)
                        alza = alza[alza > 0].nlargest(10)
                        _compras_mini_barras(alza, "alzas", fmt="+{:,.1f}%")
                else:
                    st.info("Sin columnas de precio anterior.")
