"""
graficos.ventas — dashboard de Ventas: el dispatcher de sus vistas, y la que vive acá (Venta vs Compra).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import definicion_venta as dv
from data import cargar as _cargar_reporte
from tema import ACENTO, GRIS_BORDE
from graficos.base import (
    compartimento_filtros, contar_filtros, filtro_pills,
    PALETA_CALLAI, _compras_layout, _render_rail,
    _resolver, pila_sin_tablas, publicar_contexto_ia, rail_sin_tablas,
    renderizar_graficos_genericos, seccion_perezosa,
)
from graficos.ventas_resumen import _ventas_resumen
from graficos.ventas_comparativo import _ventas_comparativo
from graficos.ventas_horario import _ventas_horario
from graficos.ventas_mix import _ventas_mix
from graficos.ventas_platos import _ventas_platos
from graficos.ventas_meseros import _ventas_meseros
from graficos import alturas

def unico_por_item(df):
    """Una fila por ÍTEM del comprobante (regla #517 de arquitectura.md).

    `ventas.parquet` trae una fila por ítem Y POR FORMA DE PAGO: pagado con
    cheque + tarjeta, cada plato sale dos veces con su venta, su costo y su
    cantidad enteros. Sumar filas infla — medido en septiembre 2026, S/
    390.272 contra S/ 332.807 reales (+17 %); en el histórico, +22 %.

    Se queda con la primera fila de cada `Llave Local Documento Item`. Las
    filas SIN llave (22 en todo el histórico) se conservan todas: no hay con
    qué decir que son la misma. No toca el parquet ni el df cargado —
    devuelve otro df—, así que lo que analiza FORMAS DE PAGO o PROPINAS
    (Meseros, el asistente IA) sigue recibiendo las filas por pago.

    Sin la columna (demo, otro parquet) devuelve el df tal cual."""
    if df is None or df.empty:
        return df
    col = _resolver(df, ["Llave Local Documento Item"])
    if not col:
        return df
    llave = df[col]
    repetida = llave.duplicated() & llave.notna()
    return df[~repetida] if repetida.any() else df

# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py) — reemplaza el st.pills que vivia ANTES en medio
# del dashboard. Mismo patron que Compras/Ajuste.
#
# La «Tabla» esta OCULTA desde el 2026-09-23, con las de los demas reportes:
# `rail_sin_tablas` aca y `pila_sin_tablas` en `_PILA`, de a par (#507).
#
# «Mix de carta» entro el 2026-09-25 en el lugar de «Venta por dia», y ese
# mismo dia se fue «Familia/Subfamilia semanal»: la barra semanal partida por
# familia es la del Mix, que ademas baja a Subgrupo y Producto (regla #527).
# «Analisis de platos» entro ese mismo dia en lugar del Top platos del
# Resumen (#528): el ranking entre hasta 4 periodos (regla #529).
# «Historica subfamilia» se fue el 2026-09-26: la lee el mapa de calor del
# Mix en granularidad Mes (regla #541). Y ese mismo dia «Matriz agrupada»:
# su tabla es la del Mix, y lo unico que tenia propio —el % de costo por
# periodo— paso ahi (reglas #543 y #544). Y tambien «Ranking & FoodCost»: lo
# unico suyo —los platos de toda la carta con su costo al lado— paso a
# «Analisis de platos» (reglas #545 y #546).
_VENTAS_RAIL_CATEGORIAS = rail_sin_tablas((
    ("Resumen",  (("Resumen ejecutivo", "Resumen", ":material/summarize:"),)),
    ("Tiempo",   (("Mix de carta",               "Mix",        ":material/stacked_bar_chart:"),
                  ("Mapa por hora",               "Por hora",   ":material/schedule:"),
                  ("Comparativo vs Año Pasado",   "Año Pasado", ":material/compare_arrows:"),
                  ("Venta vs Compra",            "Vs Compra",  ":material/balance:"))),
    ("Análisis", (("Análisis de platos",  "Platos",  ":material/restaurant_menu:"),
                  ("Meseros",             "Meseros", ":material/groups:"))),
    ("Datos",    (("Tabla",  "Tabla", ":material/table_rows:"),)),
))

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA
# tupla (el porqué está en `graficos/compras/__init__.py::_PILA`).
#
# Las 8 van en UNA sola pila: a diferencia de Ajuste, acá las categorías
# del rail ("Resumen"/"Tiempo"/"Análisis") son sólo agrupación visual y no
# separan la clave del rango — Ventas usa `carga_por_rango`, o sea UNA
# clave por reporte, la misma que decide qué se baja de R2. El rail aplana
# las categorías igual que siempre, así que la pila las lee seguidas.
_PILA = pila_sin_tablas((
    ("vt_sec_resumen",    "Resumen ejecutivo"),
    ("vt_sec_mix",        "Mix de carta"),
    ("vt_sec_hora",       "Mapa por hora"),
    ("vt_sec_ano_pasado", "Comparativo vs Año Pasado"),
    ("vt_sec_vs_compra",  "Venta vs Compra"),
    ("vt_sec_platos",     "Análisis de platos"),
    ("vt_sec_meseros",    "Meseros"),
    ("vt_sec_tabla",      "Tabla"),
))


def _ventas_cargar_compra_diaria(dia_min, dia_max):
    """Compra por día, acotada a [dia_min, dia_max] (el rango de días que
    ya tiene la vista de Ventas). Carga compras.parquet APARTE — Ventas y
    Compras son reportes independientes, sin llave compartida más que la
    fecha, así que esto es el gasto TOTAL en compras ese día, no el costo
    de lo que se vendió ese día (una compra de insumos no se vende
    necesariamente el mismo día). Sirve para comparar flujo de compra vs
    venta, no como margen exacto por transacción. Los chips de Ventas
    (Grupo/Sub Grupo/Canal/Servicio) no aplican acá: son categorías de
    venta, sin equivalente en compras.parquet.
    Retorna None si compras.parquet no está disponible o le faltan las
    columnas de fecha/valor (mismo criterio de resolución que
    graficos/compras/__init__.py)."""
    df_c = _cargar_reporte("compras.parquet")
    if df_c is None or df_c.empty:
        return None
    col_fecha_c = _resolver(df_c, ["Fecha_documento", "Fecha documento",
                                   "Fecha_registro", "Fecha registro", "FECHA"])
    col_valor_c = _resolver(df_c, ["Valor_compra", "Valor compra",
                                   "Importe Total", "Valorizado"])
    if not col_fecha_c or not col_valor_c:
        return None
    _fe = pd.to_datetime(df_c[col_fecha_c], errors="coerce").dt.normalize()
    _val = pd.to_numeric(df_c[col_valor_c], errors="coerce").fillna(0)
    g_c = pd.DataFrame({"dia": _fe, "compra": _val}).dropna(subset=["dia"])
    g_c = g_c[(g_c["dia"] >= dia_min) & (g_c["dia"] <= dia_max)]
    if g_c.empty:
        return None
    return g_c.groupby("dia", as_index=False)["compra"].sum()


@st.fragment
def _ventas_venta_compra_dia(g, hay_costo, hay_compra, hay_pax):
    """'Venta vs Compra' — línea de Venta/Costo/Compra arriba (normalizadas
    a % de variación desde el primer día del rango, con badge de color al
    final de cada línea) + barras de Pax abajo en un subplot separado.
    Mismo espíritu que un gráfico bursátil: % arriba con crosshair, volumen
    abajo. Normaliza a % —Venta/Costo/Compra tienen escalas muy distintas
    en soles—, así que compararlas desde el mismo punto de partida es lo
    que las hace legibles juntas."""
    _opts = ["Venta"]
    if hay_costo:
        _opts.append("Costo")
    if hay_compra:
        _opts.append("Compra")
    sel = st.pills(
        "Métricas", _opts, selection_mode="multi", default=list(_opts),
        key="ventas_vc_metricas", label_visibility="collapsed",
    ) or ["Venta"]

    rows = 2 if hay_pax else 1
    row_heights = [0.72, 0.28] if hay_pax else [1.0]
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                        row_heights=row_heights, vertical_spacing=0.06)

    _colores = {"Venta": ACENTO, "Costo": PALETA_CALLAI[1], "Compra": PALETA_CALLAI[2]}
    for _serie, _col in (("Venta", "venta"), ("Costo", "costo"), ("Compra", "compra")):
        if _serie in sel and _col in g.columns:
            serie = g[_col]
            # % de variación desde el primer valor != 0 del rango (si todo
            # el rango es cero, no hay base válida: se muestra plano en 0%
            # en vez de dividir por cero).
            _base = next((v for v in serie if v), None)
            pct = (serie / _base - 1) * 100 if _base else serie * 0
            fig.add_trace(go.Scatter(
                x=g["dia"], y=pct, name=_serie, mode="lines",
                line=dict(color=_colores[_serie], width=2.2),
                hovertemplate=("%{x|%d/%m/%Y}<br>" + _serie
                               + ": %{y:+.2f}%<extra></extra>"),
            ), row=1, col=1)
            # Badge de color al final de la línea con el % acumulado del
            # rango — como el "+110,71%" de la referencia. Sin bordes
            # redondeados (Plotly no los soporta en anotaciones), pero
            # mismo color de fondo que la línea + texto blanco.
            fig.add_annotation(
                x=g["dia"].iloc[-1], y=pct.iloc[-1], row=1, col=1,
                text=f"{pct.iloc[-1]:+.2f}%", showarrow=False,
                xanchor="left", xshift=8, align="left",
                bgcolor=_colores[_serie], borderpad=4,
                font=dict(color="white", size=11, family="DM Sans, sans-serif"),
            )

    if hay_pax:
        fig.add_trace(go.Bar(
            x=g["dia"], y=g["pax"], name="Pax",
            marker=dict(color=GRIS_BORDE),
            hovertemplate="%{x|%d/%m/%Y}<br>Pax: %{y:,.0f}<extra></extra>",
        ), row=2, col=1)

    _compras_layout(fig, alto=alturas.PROTAGONISTA if hay_pax else 460)
    fig.update_layout(
        title="Venta vs Compra por día (% de variación desde el inicio del rango)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=64, t=30, b=10),
        # Crosshair al pasar el mouse: línea vertical punteada que cruza
        # ambos paneles (spikemode="across") + fecha en el eje X + un
        # tooltip único con el valor de cada serie en esa fecha
        # (hovermode="x unified"). Es la aproximación nativa de Plotly al
        # crosshair-con-badges-en-el-borde de la referencia: los badges de
        # la imagen SIGUEN al cursor en tiempo real, algo que Plotly no
        # ofrece sin JS custom (ver arquitectura.md — CLAUDE.md prohíbe JS
        # inyectado por markdown; haría falta un componente aparte). Este
        # tooltip unificado da la misma información (fecha + % de cada
        # serie), agrupada en un solo cuadro junto al cursor en vez de
        # flotando en el borde derecho.
        hovermode="x unified",
    )
    fig.update_xaxes(
        type="date", tickmode="linear", tick0=g["dia"].min(),
        dtick=86400000.0, tickformat="%d/%m", tickangle=-45,
        tickfont=dict(size=10), row=rows, col=1,
    )
    # Spikes en TODAS las filas (no solo la de abajo): con shared_xaxes las
    # X están "matched", pero cada eje decide por su cuenta si dibuja su
    # propia línea de crosshair — si solo se lo pedís al de abajo, pasar el
    # mouse por el panel de arriba (Venta/Costo/Compra) no muestra la cruz.
    fig.update_xaxes(
        showspikes=True, spikemode="across", spikesnap="cursor",
        spikedash="dot", spikethickness=1, spikecolor=GRIS_BORDE,
    )
    fig.update_yaxes(ticksuffix="%", tickformat=",.2f", zeroline=True,
                     zerolinecolor=GRIS_BORDE, row=1, col=1)
    if hay_pax:
        fig.update_yaxes(tickformat=",.0f", title="Pax", row=2, col=1)
    if not hay_compra:
        st.caption("Sin datos de Compra para este rango de fechas (o a "
                   "compras.parquet le faltan las columnas de fecha/valor) "
                   "— se omite esa serie.")
    st.plotly_chart(fig, use_container_width=True, key="ventas_g_vc_dia")


def renderizar_graficos_ventas(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Ventas: resumen ejecutivo, mix de carta por período,
    mapa por hora, año pasado, venta vs compra, análisis de platos y
    meseros. Columnas reales del parquet de ventas.

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py — igual que
    Ajuste). Se le pasa `d`, el df YA filtrado por los chips propios de
    Ventas (Grupo/Sub Grupo/Canal/Servicio) — reusarlo evita que la Tabla
    tenga un estado de filtros distinto al de los gráficos."""
    col_venta = _resolver(df_f, ["Venta Item Ddocumento", "Venta_Item_Ddocumento",
                                 "Neto Total Item Ddocumento", "Venta"])
    col_fam   = _resolver(df_f, ["Grupo"])
    col_sub   = _resolver(df_f, ["Sub Grupo", "Sub_Grupo", "Subgrupo"])
    col_fecha = _resolver(df_f, ["Fec Reg Documento", "Fec_Reg_Documento",
                                 "Fecha Registro", "FECHA"])
    # El costo de la LÍNEA (unitario × cantidad) que arma `definicion_venta`
    # (regla #524): «Precio Costo» es POR UNIDAD, y sumarlo suelto daba un
    # FoodCost de 24 % donde era 29 % (#542). Queda de respaldo para un df
    # sin preparar.
    col_costo  = _resolver(df_f, ["Costo Venta", "Precio Costo",
                                  "Costo Item Ddocumento", "Costo"])
    col_pax    = _resolver(df_f, ["Cant Pax", "Cantidad Pax", "Pax"])
    col_pedido = _resolver(df_f, ["Llave Local Pedido", "Llave_Local_Pedido",
                                  "Nro Pedido", "Numero Pedido"])
    col_prod   = _resolver(df_f, ["Nomb Item Venta", "Nombre Producto",
                                  "Producto", "Descripcion"])
    col_cant   = _resolver(df_f, ["Cantidad Item Ddocumento", "Cantidad",
                                  "Cant Item", "Unidades"])
    col_canal  = _resolver(df_f, ["Canal Venta", "Canal_Venta",
                                  "Nomb Canal Venta", "Canal"])
    col_serv   = _resolver(df_f, ["Servicio", "Tipo Servicio",
                                  "Nomb Servicio", "Nombre Servicio"])
    col_mesero  = _resolver(df_f, ["Nombre Mesero", "Nomb Mesero"])
    col_ldoc    = _resolver(df_f, ["Llave Local Documento"])
    if not col_fecha:
        for _c in df_f.columns:
            if pd.api.types.is_datetime64_any_dtype(df_f[_c]):
                col_fecha = _c
                break

    if not col_venta:
        st.warning("No se encontró la columna de venta. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros: el compartimento único de la franja ────────────────────
    # Aplican a TODOS los gráficos de Ventas.
    # Canal Venta y Servicio solo aparecen si su columna existe en el parquet
    # (Servicio no siempre está — se salta silenciosamente).
    # Los CUATRO en el compartimento único de la franja. Hasta el 2026-08-31
    # eran cuatro popovers en fila y un `_filtro_popover` local que existía
    # sólo para no repetirlos — ese helper es hoy `base.filtro_pills`, que
    # además dejó de necesitar el wrapper `chipwrap_<key>_on|off`: el estado
    # activo lo marca ahora el compartimento entero, no cada filtro.
    with compartimento_filtros(contar_filtros(
            "ventas_graf_filtro_fam", "ventas_graf_filtro_sub",
            "ventas_graf_filtro_canal", "ventas_graf_filtro_serv")):
        _, fam_sel = filtro_pills(df_f, col_fam,
                                  "ventas_graf_filtro_fam", "Grupo")
        # CASCADA: Sub Grupo sólo ofrece los que quedan bajo el Grupo elegido.
        _dd = df_f
        if fam_sel and col_fam:
            _dd = _dd[_dd[col_fam].astype(str).isin(fam_sel)]
        _, sub_sel = filtro_pills(_dd, col_sub,
                                  "ventas_graf_filtro_sub", "Sub Grupo")
        _, canal_sel = filtro_pills(df_f, col_canal,
                                    "ventas_graf_filtro_canal", "Canal Venta")
        _, serv_sel = filtro_pills(df_f, col_serv,
                                   "ventas_graf_filtro_serv", "Servicio")

    def _aplicar_chips(df):
        """Aplica los chips de la franja a CUALQUIER df de ventas, no solo al
        del rango cargado. Existe como función (y no inline) porque el
        comparativo "Año Pasado" trae su propio df desde R2 y tiene que
        quedar filtrado IGUAL que la vista actual — si no, se comparan
        barras filtradas contra barras sin filtrar. Defensiva con las
        columnas: el df del año pasado sale del mismo parquet, pero si
        alguna faltara, ese filtro se saltea en vez de reventar."""
        for _col, _sel in ((col_fam, fam_sel), (col_sub, sub_sel),
                           (col_canal, canal_sel), (col_serv, serv_sel)):
            if _sel and _col and _col in df.columns:
                df = df[df[_col].astype(str).isin(_sel)]
        return df

    # DOS GRANOS DEL MISMO df (regla #517). `d_pagos` es el parquet tal
    # cual: una fila por ítem Y por forma de pago. `d` es una fila por
    # ítem, y es lo que reciben TODAS las vistas que suman venta, costo o
    # cantidad. Sólo dos cosas miran `d_pagos`: Meseros (la propina es del
    # PAGO) y el asistente IA (que también responde por formas de pago, y
    # recibe la nota del grano en `asistente_datos.nota_de_grano`).
    #
    # Y UNA DEFINICIÓN DE VENTA (regla #524): `df_f` llega de
    # `data.cargar_rango` con la columna `CLASE VENTA` y las notas de
    # crédito como ítems negativos. `d` es sólo lo que ES venta —sin
    # cortesías ni anulados, con las notas restando— y es lo que suman las
    # vistas. `d_todo` conserva todas las clases: lo usa el Resumen, que
    # muestra cortesías y anulados aparte y arma el puente de la venta.
    if dv.columna(df_f, dv.CLASE) is None:
        # Un df que no vino de `data.cargar_rango` (los tests, una
        # herramienta): la definición se aplica acá, igual.
        df_f = dv.preparar(df_f)
    d_pagos = _aplicar_chips(df_f)
    d_todo = unico_por_item(d_pagos)
    d = dv.solo_venta(d_todo)

    def _filtrar_items(df):
        """`_aplicar_chips` + un ítem una vez + sólo venta, para los df que
        las vistas traen APARTE de R2 (Año Pasado, Mapa por hora): sin los
        dos últimos pasos, esas vistas volverían a sumar filas por pago,
        cortesías y anulados."""
        return dv.solo_venta(unico_por_item(_aplicar_chips(df)))

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Ventas", d_pagos, {
        "Grupo": fam_sel, "Sub Grupo": sub_sel,
        "Canal": canal_sel, "Servicio": serv_sel,
    })

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    _venta = pd.to_numeric(d[col_venta], errors="coerce").fillna(0)

    # El rail ya no ELIGE: con `secciones` marca dónde estás y scrollea.
    _render_rail(_VENTAS_RAIL_CATEGORIAS, "ventas_graf_tipo",
                 btn_prefix="ventas_rail_btn_", secciones=_PILA)

    # La cadena `if graf == ...` de abajo NO se toca: pasa de vivir dentro
    # de un `with st.container(...)` compartido por las diez vistas de
    # gráfico a ser el cuerpo de esta función, que cada sección llama con
    # SU nombre de vista. Mismo movimiento que en salidas.py y
    # requerimientos.py, y por el mismo motivo: en un if/elif de 200 líneas
    # con diez cuerpos pesados, la migración segura es la que NO los toca.
    def _cuerpo_grafico(graf):

        # ── 0) Resumen ejecutivo: KPIs + candlestick diario + ticket + top
        # platos (graficos/ventas_resumen.py). Vive DENTRO de esta misma
        # card compartida (no arriba, entre chips y card) a propósito: así
        # no hace falta repetir la excepción de margin-top de la regla #38
        # de arquitectura.md — esa regla solo aplica a contenido en flujo
        # POR FUERA de `ajuste_graf_card_izq_ventas`.
        if graf == "Resumen ejecutivo":
            _ventas_resumen(d_todo, col_venta, col_fecha, col_pax, col_pedido,
                            col_prod, col_cant, col_fam=col_fam,
                            col_serv=col_serv, col_canal=col_canal,
                            col_mesero=col_mesero, d_pagos=d_pagos)

        # ── 1) Mix de carta: la venta por período partida por Grupo ›
        # Sub Grupo › Producto (graficos/ventas_mix.py, regla #527). Le pasa
        # `_filtrar_items` como a Año Pasado: el Detalle trae el año pasado
        # aparte de R2 y tiene que quedar filtrado igual que `d`.
        elif graf == "Mix de carta":
            _ventas_mix(d, filtrar_cb=_filtrar_items)

        # ── 1a-bis) Mapa de calor día × hora, hasta 4 períodos ───────────
        # Trae sus propios tramos (uno por período comparado) con
        # data.cargar_rango y les aplica _filtrar_items, igual que el
        # comparativo: el `d` de acá está acotado al rango de la franja y los
        # períodos que se comparan pueden caer fuera de él.
        elif graf == "Mapa por hora":
            _ventas_horario(d, col_venta, col_fecha, col_pax=col_pax,
                            col_pedido=col_pedido, col_prod=col_prod,
                            col_cant=col_cant, col_fam=col_fam,
                            col_sub=col_sub, filtrar_cb=_filtrar_items)

        # ── 1a) Comparativo día a día vs Año Pasado ──────────────────────
        # Trae su propio df del año pasado (data.cargar_rango) y le pasa
        # _filtrar_items para que quede filtrado igual que `d`.
        elif graf == "Comparativo vs Año Pasado":
            _ventas_comparativo(d, col_venta, col_fecha, col_pax=col_pax,
                                col_pedido=col_pedido, col_prod=col_prod,
                                col_cant=col_cant, col_fam=col_fam,
                                col_sub=col_sub, filtrar_cb=_filtrar_items)

        # ── 1b) Venta vs Compra por día (líneas arriba, Pax en barras abajo) ─
        # Vista aparte de "Venta por día": mismo espíritu que un gráfico
        # bursátil (precio arriba, volumen abajo). Compra viene de
        # compras.parquet, un reporte independiente — ver el docstring de
        # _ventas_cargar_compra_diaria sobre qué significa (y qué NO significa)
        # cruzarlo por fecha con Venta.
        elif graf == "Venta vs Compra" and col_fecha:
            _fe = pd.to_datetime(d[col_fecha], errors="coerce").dt.normalize()

            _base = pd.DataFrame({"dia": _fe, "venta": _venta})
            if col_costo:
                _base["costo"] = pd.to_numeric(d[col_costo], errors="coerce").fillna(0)
            _base = _base.dropna(subset=["dia"])
            _agg = {c: "sum" for c in _base.columns if c != "dia"}
            g = _base.groupby("dia", as_index=False).agg(_agg).sort_values("dia")

            if col_pax:
                _pdf = pd.DataFrame({
                    "dia": _fe,
                    "pax": pd.to_numeric(d[col_pax], errors="coerce").fillna(0),
                })
                if col_pedido:
                    # Un valor por pedido, y el de una nota de crédito
                    # resta (regla #524): ver `definicion_venta.pax_por`.
                    _pdf["ped"] = d[col_pedido].astype(str)
                    if col_ldoc:
                        _pdf["doc"] = d[col_ldoc].astype(str)
                    _pdf = _pdf.dropna(subset=["dia"])
                    _pax_dia = (dv.pax_por(_pdf, "ped", "pax",
                                           doc="doc" if col_ldoc else None,
                                           por="dia")
                                .rename("pax").reset_index())
                else:
                    _pdf = _pdf.dropna(subset=["dia"])
                    _pax_dia = _pdf.groupby("dia", as_index=False)["pax"].sum()
                g = g.merge(_pax_dia, on="dia", how="left")
                g["pax"] = g["pax"].fillna(0)

            if g.empty:
                st.info("Sin fechas válidas en el rango.")
            else:
                g_compra = _ventas_cargar_compra_diaria(g["dia"].min(), g["dia"].max())
                hay_compra = g_compra is not None
                if hay_compra:
                    g = g.merge(g_compra, on="dia", how="left")
                    g["compra"] = g["compra"].fillna(0)
                _ventas_venta_compra_dia(
                    g, hay_costo=bool(col_costo), hay_compra=hay_compra,
                    hay_pax=bool(col_pax))

        # ── 3) Análisis de platos: el ranking entre hasta 4 períodos
        # (graficos/ventas_platos.py, regla #529). Trae sus períodos aparte
        # de R2, así que recibe `_filtrar_items` como Año Pasado.
        elif graf == "Análisis de platos":
            _ventas_platos(d, filtrar_cb=_filtrar_items)

        # ── 4) Meseros: las propinas por mesero, como los reportes del POS
        # (graficos/ventas_meseros.py, regla #553). Recibe las filas POR
        # PAGO —la propina es del pago (#517)— y, para lo que trae aparte de
        # R2 (el mes anterior, los 12 meses), sólo los chips: los dos granos
        # los arma la vista. `firma` identifica esos chips para guardar lo
        # traído en la sesión.
        elif graf == "Meseros":
            _ventas_meseros(d_pagos, filtrar_cb=_aplicar_chips,
                            firma=(tuple(fam_sel or ()), tuple(sub_sel or ()),
                                   tuple(canal_sel or ()),
                                   tuple(serv_sel or ())))
        else:
            st.info("No hay columnas suficientes para este gráfico.")

    def _seccion(slug, nombre):
        """Envuelve una vista de gráfico en su propia tarjeta.

        Conserva el prefijo `ajuste_graf_card_` (de ahí cuelga el CSS de
        tarjeta, `estilos/_80_cards.py`) y suma el sufijo de la vista:
        antes las diez compartían `ajuste_graf_card_izq_ventas`, lo que
        funcionaba porque nunca coexistían. Apiladas serían diez widgets
        con la misma key = excepción de Streamlit."""
        def _f():
            with st.container(border=True,
                              key=f"ajuste_graf_card_izq_ventas_{slug}"):
                _cuerpo_grafico(nombre)
        return _f

    def _dib_tabla():
        with st.container(border=True, key="ajuste_graf_card_izq_ventas_tabla"):
            if tabla_cb is not None:
                tabla_cb(d)
            else:
                st.info("La tabla no está disponible en este contexto.")

    _DIBUJANTES = {
        # El Resumen arma SU tarjeta (regla #521): envuelto en una
        # `ajuste_graf_card_` se leía junto con la del Top platos, que se
        # quitó el 2026-09-25 (regla #528).
        "vt_sec_resumen":    lambda: _cuerpo_grafico("Resumen ejecutivo"),
        "vt_sec_mix":        _seccion("mix", "Mix de carta"),
        "vt_sec_hora":       _seccion("hora", "Mapa por hora"),
        "vt_sec_ano_pasado": _seccion("ano_pasado", "Comparativo vs Año Pasado"),
        "vt_sec_vs_compra":  _seccion("vs_compra", "Venta vs Compra"),
        # Como el Resumen, arma SUS tarjetas: la del ranking y, con un
        # plato en foco, la de su evolución debajo (regla #529).
        "vt_sec_platos":     lambda: _cuerpo_grafico("Análisis de platos"),
        # Como Platos, arma SUS tarjetas: la de la tabla, la planilla y el
        # detalle del mesero elegido (regla #553).
        "vt_sec_meseros":    lambda: _cuerpo_grafico("Meseros"),
        "vt_sec_tabla":      _dib_tabla,
    }

    # El contenedor con la key va AFUERA del fragment: es el que observan el
    # scrollspy y la precarga. Con ocho secciones —y las de Ventas son las
    # más pesadas de la app— la carga perezosa de `seccion_perezosa` deja de
    # ser una optimización y pasa a ser lo que hace la página viable: ver su
    # docstring y arquitectura.md #211 (construir todo de una dejaba al
    # navegador sin responder en Cloud).
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
