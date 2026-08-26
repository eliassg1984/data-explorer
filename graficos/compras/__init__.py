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
    _resolver, publicar_contexto_ia, seccion_perezosa,
    renderizar_graficos_genericos, vista_activa,
)
from graficos.compras._comun import (  # noqa: F401  (re-export)
    COLUMNAS_DRILL, GAP_DRILL,
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
                   ("Tabla",            "Tabla",         ":material/table_rows:"))),
)

# Vistas de Compras que se quedan el selector de fecha DENTRO de su tarjeta
# en vez de dejarlo en la franja superior. Hoy solo Documentos SUNAT: ahi la
# fecha no es contexto global sino EL filtro de la tabla (es el rango que se
# le consulta al SIRE), asi que vivia lejos de lo que filtra.
#
# `Semanal` estuvo aca un dia (2026-08-24) con un calendario propio de dos
# meses, y se saco al apilar las vistas: con las seis dibujandose en la MISMA
# corrida, dos duenos de la clave del rango no pueden convivir —
# `st.session_state` no se puede reescribir despues de que el widget de esa
# key ya se instancio— y Compras reventaba en cada carga. Ver regla #203.
#
# La leccion general, y el motivo de que la lista siga teniendo un solo
# miembro: en una pagina APILADA el rango es del REPORTE, no de la vista.
# Ver el analisis de la regla #210.
_VISTAS_CON_FECHA_PROPIA = {"Documentos SUNAT"}

# Subconjunto del anterior: las que ademas necesitan OTROS topes de
# calendario que los del parquet de Compras. Se separa a proposito — atar
# los bounds a `_VISTAS_CON_FECHA_PROPIA` haria que cualquier vista nueva
# que se quede la fecha heredara los limites del SIRE sin pedirlos.
_VISTAS_CON_BOUNDS_SUNAT = {"Documentos SUNAT"}

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail.
#
# Los dos datos viven en la MISMA tupla a propósito. El scrollspy tiene que
# saber qué botón encender cuando una sección entra en pantalla, y la
# tentación es deducirlo del nombre (`compras_sec_<slug>` ↔ `graf_btn_lat_
# <slug>`). No sirve: `_slug("Vs año pasado")` conserva la ñ y da
# `vs_año_pasado`, así que el que escribe la clave de la sección a mano
# escribe `vs_ano_pasado` y el apareo se rompe en silencio — sólo en esa
# vista, sólo en el resaltado. Emparejando acá, el slug del botón lo calcula
# quien lo dibuja y nadie tiene que adivinarlo.
#
# Fuera de la pila: `Documentos SUNAT`, que se lleva prestado el único
# selector de fecha de la app.
_PILA = (
    ("compras_sec_proveedor",     "Proveedor"),
    ("compras_sec_producto",      "Producto"),
    ("compras_sec_vs_ano_pasado", "Vs año pasado"),
    ("compras_sec_volatilidad",   "Volatilidad"),
    ("compras_sec_semanal",       "Semanal"),
    ("compras_sec_tabla",         "Tabla"),
)


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


def bounds_fecha_de_la_vista():
    """`(min, max)` que la vista activa necesita en el calendario, o None.

    Gemela de `vista_quiere_fecha_propia` y con el mismo cliente: la
    consulta `app.py` antes de sembrar/recortar el rango. Devuelve None
    para el resto de las vistas — cada una se queda con los topes de su
    propio dato, incluida la Semanal, que filtra el parquet de Compras
    como todas las demas y por lo tanto NO quiere los topes del SIRE.

    Documentos SUNAT es la excepción porque no filtra el parquet de
    Compras: le pregunta al SIRE. Y los dos extremos salen de sitios
    distintos a propósito:

      · el PISO, de `sunat.limites_registro()` — antes de la primera
        factura del registro no hay nada que pedir;
      · el TECHO, de HOY — no del tope del parquet. Un techo puesto en
        "hasta donde llegó el último sync" siempre atrasa lo que tarde en
        correr el sync, así que el día de HOY nunca se puede elegir. Eso
        fue el bug: 2026-08-24, con comprobantes del 24 ya visibles en
        SUNAT, el calendario cortaba en el 21. `comprobantes_rango` sabe
        pedir en vivo los días que el parquet todavía no trajo. Ver
        `arquitectura.md` regla #197.
    """
    if vista_activa(_COMPRAS_RAIL_CATEGORIAS,
                    "compras_graf_tipo") not in _VISTAS_CON_BOUNDS_SUNAT:
        return None
    import datetime
    import zoneinfo

    import sunat

    # HOY en Lima, no en UTC: Streamlit Cloud corre en UTC y a partir de
    # las 19:00 de Perú ya está en el día siguiente — el calendario
    # ofrecería un mañana que SUNAT todavía no puede tener.
    hoy = datetime.datetime.now(zoneinfo.ZoneInfo("America/Lima")).date()
    limites = sunat.limites_registro()
    return (limites[0] if limites else None), hoy


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
                "Documentos SUNAT", "Semanal", "Tabla"]

    # Rail vertical fijo al borde DERECHO (componente compartido _render_rail):
    # selector de tipo de gráfico agrupado por categoría. El activo se marca
    # con type="primary"; la selección se persiste en compras_graf_tipo.
    # `secciones`: la pila de esta página. Con eso el rail vertical de la
    # izquierda sabe qué botón encender según lo que haya en pantalla, y
    # aparece a partir de la segunda sección. Ver `base.py::_render_rail`.
    graf = _render_rail(_COMPRAS_RAIL_CATEGORIAS, "compras_graf_tipo",
                        secciones=_PILA)
    if graf not in opciones:
        graf = opciones[0]

    # ── Quien dibuja el selector de fecha: la franja o el drill ─────────
    # Hay DOS vistas que se lo quedan (Documentos SUNAT y Semanal, ver
    # `_VISTAS_CON_FECHA_PROPIA`). El problema es de
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
    # ── Vistas que siguen siendo un DESTINO propio ───────────────────────
    # Una excepción a la pila de abajo: Documentos SUNAT se lleva prestado
    # el ÚNICO selector de fecha de la app (`franja_fecha.render()`, la
    # misma función que llama `app.py`). Si estuviera siempre en pantalla,
    # las demás vistas se quedarían sin control de fecha arriba. Entra a la
    # pila cuando tenga rango propio — ver `vista_quiere_fecha_propia`.
    if graf == "Documentos SUNAT":
        # Import local a propósito: arrastra `sunat.py` y, con él,
        # `requests` — no hay por qué pagarlo al importar Compras si nadie
        # abre esta vista.
        from graficos.compras.documentos_sunat import renderizar_documentos_sunat
        with st.container(key="compras_sunat_drill_wrap"):
            renderizar_documentos_sunat(d, col_fecha)
        return

    # ══ LA PILA ══════════════════════════════════════════════════════════
    # Las vistas de Compras no se reemplazan: se apilan y se leen bajando.
    # El rail de la izquierda deja de ELEGIR contenido y pasa a MARCAR la
    # sección que está en pantalla (scrollspy, ver `base.py::_render_rail`).
    #
    # Cada sección va envuelta en `compras_sec_<slug>`, y ese slug es el
    # mismo que el de su botón del rail (`_slug` sobre el id de la vista):
    # así el observador de JS puede aparear sección con botón sin una tabla
    # de correspondencias que se desincronice.
    #
    # Sobre el costo: cada drill es un `@st.fragment`, así que construirlos
    # todos se paga UNA vez al entrar — un clic dentro de Proveedor
    # re-ejecuta su fragment y no toca a los demás.
    #
    # OJO con las keys de tarjeta: Volatilidad y Semanal usaban las dos
    # `ajuste_graf_card_izq_compras`. No chocaban porque nunca coexistían;
    # apiladas serían dos widgets con la misma key, que en Streamlit es una
    # excepción. Cada una lleva ahora su sufijo, y el prefijo
    # `ajuste_graf_card_` se conserva porque de él cuelga el CSS de tarjeta
    # (el clamp de una pantalla en `estilos/_80_cards.py`).

    # ── LA PILA, PEREZOSA ────────────────────────────────────────────────
    # Cada sección se dibuja en su propio `@st.fragment` y arranca en
    # ESQUELETO. El `IntersectionObserver` de `base.py::_render_rail` aprieta
    # su botón invisible cuando te acercás, y sólo ese fragment se
    # re-ejecuta — las otras cinco no se tocan.
    #
    # Por qué no se construyen todas de una, que era la versión anterior:
    # saturaba el hilo principal del navegador (~10 Plotly + 2 AgGrid a la
    # vez) y en Cloud salía "la página no responde". El servidor nunca fue el
    # problema. Ver `base.py::seccion_perezosa` y arquitectura.md #211.
    #
    # Los `def` de acá abajo son closures sobre las columnas ya resueltas:
    # el fragment necesita poder llamarlas MÁS TARDE, en su propio rerun,
    # cuando el cuerpo del dispatcher ya terminó.

    def _dib_proveedor():
            # Drill Proveedor→productos→proveedores del prod. Sin borde externo:
            # cada uno de sus 4 bloques internos lleva el suyo.
            with st.container(key="compras_prov_drill_wrap"):
                _compras_proveedor_drill(d, col_prov, col_prod, col_cant, col_valor,
                                         col_punit, col_um, col_fecha, col_docu,
                                         d_full=d_full)

    def _dib_producto():
            with st.container(key="compras_prod_drill_wrap"):
                _compras_producto_drill(d, col_prod, col_fam, col_valor, col_cant,
                                        col_punit, col_um, col_fecha, col_prov)

    def _dib_vs_ano_pasado():
            # Serie mensual + puente precio/cantidad + tabla de detalle. Es el
            # ÚNICO drill que recibe `d_full` además de `d`: su ventana de tiempo
            # es propia (arranca en "Todo") y el año pasado lo calcula
            # desplazando 12 meses su propio histórico, así que necesita el
            # histórico entero aunque la franja esté en un rango corto. Ver el
            # docstring del módulo, decisiones 1 y 2.
            with st.container(key="compras_vap_drill_wrap"):
                _compras_vs_ano_pasado_drill(d, col_prod, col_cant, col_fecha,
                                             col_valor, col_fam=col_fam,
                                             col_subfam=col_subfam, col_um=col_um,
                                             d_full=d_full)

    def _dib_volatilidad():
            with st.container(border=True, key="ajuste_graf_card_izq_vol"):
                _compras_volatilidad_drill(d, col_prod, col_prov, col_punit, col_fecha,
                                           col_valor, col_cant, col_um, col_moneda,
                                           d_full=d_full)

    def _dib_semanal():
            # La fila parte con COLUMNAS_DRILL como el resto de la página. Antes
            # era `[1.7, 1]`, uno de los cuatro ejes distintos que anotaba
            # `test_graficos.py`: alternando por el rail se notaba poco, apilado
            # el canal gris se corría a media página. Ver `_comun.py`.
            col_izq, col_der = st.columns(COLUMNAS_DRILL, gap=GAP_DRILL)

            with col_izq:
                with st.container(border=True, key="ajuste_graf_card_izq_sem"):
                    if col_prod and col_fecha:
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
                with st.container(border=True, key="ajuste_graf_card_der_sem"):
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

    def _dib_tabla():
            # Cierra la página con el detalle: el mismo AgGrid de la vista
            # Tabla. `d` ya viene filtrado por los chips Familia/Subfamilia.
            from tablas import renderizar_aggrid_compras as _render_tabla_compras
            from estilos import TAM_FUENTE
            _font_px = TAM_FUENTE.get(st.session_state.get("tabla_tam", "Mediano"), 14)
            _render_tabla_compras(d, _font_px)

    _DIBUJANTES = {
        "compras_sec_proveedor":     _dib_proveedor,
        "compras_sec_producto":      _dib_producto,
        "compras_sec_vs_ano_pasado": _dib_vs_ano_pasado,
        "compras_sec_volatilidad":   _dib_volatilidad,
        "compras_sec_semanal":       _dib_semanal,
        "compras_sec_tabla":         _dib_tabla,
    }

    # El contenedor con la key va AFUERA del fragment a propósito: es el que
    # observan el scrollspy y la precarga, y tiene que sobrevivir a que el
    # fragment de adentro se re-dibuje. Si llevara la key el fragment, cada
    # activación reemplazaría el nodo observado y los dos observadores se
    # quedarían mirando un elemento que ya no está en el documento.
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
