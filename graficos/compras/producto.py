"""graficos.compras.producto - drill de Producto.

Ranking de TODOS los productos comprados (valor, cantidad, UM, precio real
de inicio/fin de periodo y su variación) con el mismo patrón de tabla-
ranking + clic-para-enfocar que graficos/compras/proveedor.py. El producto
en foco muestra su evolución (Precio / Cantidad / Valor, con granularidad
Semana / Mes / Año) fusionando el promedio del período con el precio real
de cada compra en un solo gráfico. Esa tarjeta tiene VENTANA PROPIA
(`periodo.selector`, default 12m) desde el 2026-08-26: heredando el rango
de la franja —~24 días— cualquier granularidad daba UN solo período y la
"línea" de promedio era un punto suelto.

Reemplaza a los antiguos drills "Precio top 10", "Precio por compra" y
"Cantidad por producto" (graficos/compras/cantidad.py, eliminado 2026-08-17):
las tres separaban precio-promedio, precio-real y cantidad/valor de UN mismo
producto en tres pantallas distintas — acá conviven en una, con un selector
de texto plano en vez de tabs/pills con caja (a pedido, para no ocupar sitio).

Debajo, un segundo ranking agrupa las mismas compras por Familia; un clic
abre el mini ranking de productos de esa familia. Panel B es una tabla
AgGrid (mismo patrón barra-en-celda que la tabla de la izquierda, 2026-08-26
— antes un `_compras_mini_barras` de Plotly), a pedido para que las dos
mitades de la fila se lean como una sola grilla y no como tabla+gráfico.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from st_aggrid import AgGrid, JsCode

from tema import ACENTO, ERROR, EXITO, GRIS_TEXTO, TEXTO_PRINCIPAL
from graficos.base import _compras_layout, _compras_truncar, _slug
from graficos.compras._comun import COLUMNAS_DRILL, GAP_DRILL
from graficos import alturas, periodo

_ALTO_FILA = 28
"""Filas "algo delgadas" a pedido (2026-08-24) para los dos rankings de este
drill — el mismo número que usa el `rowHeight` de AgGrid en Proveedor/
Inventario (antes era el `row_height=` de `st.dataframe`; con el pase a
AgGrid del mismo día, la constante es `rowHeight` en `gridOptions`). Con un
alto de fila explícito, `_ALTO_FRAME` tiene que usar el mismo número: si no,
el frame se calcula para un alto y las filas reales dibujan otro, dejando
aire de sobra abajo (o de más, si `_ALTO_FRAME` quedara más chico que 8
filas reales)."""

_ALTO_FRAME = alturas.por_filas(8, px_fila=_ALTO_FILA, extra=45, minimo=0)

# Eje X por granularidad: forzado a propósito. Con pocos puntos (rango de
# fecha corto, o un producto con 1-2 compras) Plotly no tiene de dónde sacar
# un paso de tick razonable y cae en sub-segundos ("23:59:59.9995 Jul 31,
# 2026") — visto en vivo con un solo bucket de Mes. `dtick` fija el paso al
# calendario real (mes/año) y `tickformat` la etiqueta, sin importar cuántos
# puntos haya.
_EJE_X_GRAN = {
    "Semana": dict(dtick=7 * 24 * 60 * 60 * 1000, tickformat="%d %b"),
    "Mes": dict(dtick="M1", tickformat="%b %Y"),
    "Año": dict(dtick="M12", tickformat="%Y"),
}


def _eje_x_kwargs(gran, agg):
    """`_EJE_X_GRAN[gran]`, con `tick0` anclado al primer bucket real de
    ESTE gráfico para "Semana". "M1"/"M12" (Mes/Año) se alinean solos al
    calendario sin importar `tick0`, pero un paso semanal en milisegundos
    no: sin un `tick0` que caiga sobre un bucket real, con pocos datos
    Plotly puede no dibujar NINGÚN tick semanal (rango angosto, ninguna
    posición de la grilla cae dentro) — visto en vivo con una sola semana
    de compras."""
    kw = dict(_EJE_X_GRAN[gran])
    if gran == "Semana" and not agg.empty:
        kw["tick0"] = agg.index.min()
    return kw


# Selector de texto plano (Semana/Mes/Año, Precio/Cantidad/Valor): mismo
# st.pills que el resto de la app (radiogroup accesible, estado en
# session_state), pero sin la cápsula — a pedido, para que no ocupe sitio
# dentro de la columna angosta del panel de detalle. El DOM de st.pills es
# fijo (ver estilos/__init__.py § Sobre st.pills): stButtonGroup > button
# [role="radio"], con `data-selected` SOLO en el activo.
_CSS_SELECTOR_TEXTO = f"""
<style>
.st-key-compras_prod_gran [data-testid="stButtonGroup"],
.st-key-compras_prod_modo [data-testid="stButtonGroup"] {{
    gap: 10px !important;
}}
.st-key-compras_prod_gran [data-testid="stButtonGroup"] button[role="radio"],
.st-key-compras_prod_modo [data-testid="stButtonGroup"] button[role="radio"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 1px 0 !important;
    min-height: 0 !important;
    font-size: 12.5px !important;
    font-weight: 400 !important;
    color: {GRIS_TEXTO} !important;
}}
.st-key-compras_prod_gran [data-testid="stButtonGroup"] button[role="radio"][data-selected],
.st-key-compras_prod_modo [data-testid="stButtonGroup"] button[role="radio"][data-selected] {{
    color: {ACENTO} !important;
    font-weight: 600 !important;
}}
/* Título sobre cada tabla-ranking: mismo lenguaje visual que
   `.cp-rank-tit` de graficos/compras/_css_proveedor.py, pero declarado acá
   — ese CSS solo se inyecta cuando se renderiza el drill de Proveedor, así
   que reusar la clase sin redeclararla dejaría el título sin estilo en
   Producto. Nombre propio a propósito (evita cualquier acople). */
.cp-prod-rank-tit {{
    /* 16px, en sync con `.cp-rank-tit` de _css_proveedor.py — el
       comentario de arriba explica por que son dos declaraciones. */
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    padding-left: 2px;
    margin: 0 0 4px;
}}
</style>
"""


# ── AgGrid: los dos rankings de este drill, sin checkbox ──────────────────
# 2026-08-24, a pedido ("como en Proveedor, sin el check de selección, y
# con filas delgadas"): mismo patrón que la regla #136/#192 de
# arquitectura.md — `st.dataframe` dibuja su columna de selección en un
# CANVAS (glide-data-grid), no hay nodo DOM por celda, así que no hay CSS
# que apunte "sólo esa columna". Cambiar a AgGrid es la única salida.
#
# Los dos rankings de este archivo (Producto y Familia) comparten el mismo
# toggle y los mismos formatters — se definen UNA vez a nivel de módulo
# (mismo criterio que `_EJE_X_GRAN`, arriba) en vez de recrear los `JsCode`
# en cada corrida del fragment.
_js_toggle_prod = JsCode(
    "function(e){ e.node.setSelected(!e.node.isSelected(), true); }")

# La barra es el FONDO de la celda (regla #136): un `linear-gradient`
# cortado en el % de LLENADO contra el MAYOR valor de la lista (`_barra`,
# columna oculta) — no contra el total, que es lo que ya muestra la
# columna "%".
_js_barra_prod = JsCode(
    "function(p){"
    " var w = Math.max(0, Math.min(100, p.data._barra||0))"
    " * 0.62;"
    " return {'background': 'linear-gradient(90deg,"
    f" {ACENTO} 0 ' + w + '%, transparent ' + w"
    " + '% 100%)',"
    " 'display':'flex','alignItems':'center',"
    " 'justifyContent':'flex-end',"
    f" 'color':'{TEXTO_PRINCIPAL}'"
    "};"
    "}")

# Montos GRANDES (Valor): redondeado, CON separador de miles.
_js_soles0_prod = JsCode(
    "function(p){ return p.value==null ? '' :"
    " 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")

# Precios UNITARIOS (Inicio/Fin): 2 decimales, SIN separador de miles —
# mismo criterio que el `format="S/ %.2f"` que tenían como
# `column_config.NumberColumn`: un precio unitario no necesita agrupar.
_js_soles2_prod = JsCode(
    "function(p){ return p.value==null ? '' :"
    " 'S/ ' + p.value.toFixed(2); }")

_js_pct_prod = JsCode(
    "function(p){ return p.value==null ? '' :"
    " Math.round(p.value) + '%'; }")

# Var: con signo y 1 decimal (`%+.1f%%` en Python). `toFixed` ya antepone
# el signo "-" en un negativo; sólo hace falta el "+" del lado positivo.
_js_pct_signed_prod = JsCode(
    "function(p){ if(p.value==null) return '';"
    " return (p.value>=0?'+':'') + p.value.toFixed(1) + '%'; }")

# Conteos (Cant./Productos): redondeado, CON separador de miles — mismo
# criterio que "Valor", consistente con el resto de las tablas AgGrid de
# este drill (Proveedor).
_js_num0_prod = JsCode(
    "function(p){ return p.value==null ? '' :"
    " Math.round(p.value).toLocaleString('es-PE'); }")


# ── Funciones puras ───────────────────────────────────────────────────────

def _prod_ranking(dd, col_prod, col_fecha, col_valor, col_cant, col_punit, col_um):
    """Un producto por fila: valor y cantidad totales del rango, UM (moda),
    y precio real de la primera y última compra del período (sin promediar
    — mismo criterio que "Por compra") con su % de variación. Ordenado por
    valor descendente."""
    filas = []
    for prod, g in dd.groupby(col_prod):
        valor = float(g[col_valor].sum())
        cantidad = float(g[col_cant].sum()) if col_cant else 0.0
        um = ""
        if col_um and col_um in g.columns:
            _u = g[col_um].dropna()
            if not _u.empty:
                um = str(_u.mode().iat[0])
        gp = g.dropna(subset=[col_punit])
        gp = gp[gp[col_punit] > 0].sort_values(col_fecha)
        if gp.empty:
            inicio = fin = var_pct = None
        else:
            inicio = float(gp[col_punit].iloc[0])
            fin = float(gp[col_punit].iloc[-1])
            var_pct = ((fin - inicio) / inicio * 100) if inicio else None
        filas.append({"producto": str(prod), "valor": valor, "cantidad": cantidad,
                      "um": um, "inicio": inicio, "fin": fin, "var_pct": var_pct})
    out = pd.DataFrame(filas).sort_values("valor", ascending=False).reset_index(drop=True)
    tot = out["valor"].sum() or 1.0
    out["pct"] = out["valor"] / tot * 100
    return out


def _prod_serie_periodo(g, col_fecha, col_punit, col_cant, col_valor, gran):
    """Serie por período (Semana/Mes/Año) de UN producto ya filtrado: precio
    promedio (relleno hacia adelante y hacia atrás en los huecos, para que
    la línea no corte), cantidad total y valor total. Indexada por la fecha
    de INICIO del período (eje real, no etiquetas de texto), así el
    promedio y las compras reales conviven en el mismo eje sin importar la
    granularidad elegida."""
    fe = pd.to_datetime(g[col_fecha], errors="coerce")
    if gran == "Semana":
        bucket = (fe - pd.to_timedelta(fe.dt.weekday, unit="D")).dt.normalize()
    elif gran == "Año":
        bucket = pd.to_datetime(fe.dt.year.astype("Int64").astype(str) + "-01-01",
                                errors="coerce")
    else:  # Mes
        bucket = fe.dt.to_period("M").dt.to_timestamp()
    base = pd.DataFrame({
        "bucket": bucket,
        "precio": pd.to_numeric(g[col_punit], errors="coerce"),
        "cantidad": (pd.to_numeric(g[col_cant], errors="coerce").fillna(0)
                     if col_cant else 0.0),
        "valor": pd.to_numeric(g[col_valor], errors="coerce").fillna(0),
    }).dropna(subset=["bucket"])
    if base.empty:
        return base.set_index("bucket")
    agg = base.groupby("bucket").agg(precio=("precio", "mean"),
                                     cantidad=("cantidad", "sum"),
                                     valor=("valor", "sum")).sort_index()
    agg["precio"] = agg["precio"].ffill().bfill()
    return agg


def _fam_normalizada(dd, col_fam):
    """Columna de familia como texto, con vacíos/NaN unificados en "Sin
    familia" — no se descartan, o el total de este ranking dejaría de
    cuadrar con el de productos."""
    return dd[col_fam].astype(str).replace({"": "Sin familia", "nan": "Sin familia"})


def _fam_ranking(dd, col_fam, col_prod, col_valor):
    """Una familia por fila: valor total y Nº de productos distintos."""
    g = dd.copy()
    g[col_fam] = _fam_normalizada(g, col_fam)
    out = g.groupby(col_fam).agg(valor=(col_valor, "sum"),
                                 productos=(col_prod, "nunique"))
    out = out.sort_values("valor", ascending=False).reset_index()
    out = out.rename(columns={col_fam: "familia"})
    tot = out["valor"].sum() or 1.0
    out["pct"] = out["valor"] / tot * 100
    return out


# ── Vista principal ──────────────────────────────────────────────────────

@st.fragment
def _prod_stats(g, col_fecha, col_punit, col_cant, col_valor, col_um):
    """Las cifras del encabezado del panel de detalle, sobre EL MISMO df
    que dibujan los puntos.

    Nace el 2026-08-26 con la ventana propia de la tarjeta: antes salían de
    la fila del ranking, que se calcula sobre el rango de la franja. Con
    dos ventanas distintas eso sería un número describiendo un período y
    unos puntos dibujando otro.

    Devuelve también `minimo`/`maximo`, que el ranking no tiene: con
    `var` = primera contra última compra, un producto que arrancó y terminó
    en el mismo precio da 0.0% aunque en el medio haya oscilado 39% — el
    caso real que motivó el pedido. El rango min-max es lo que la persona
    está viendo en los puntos, así que se dice.
    """
    _r = g.dropna(subset=[col_punit])
    _r = _r[_r[col_punit] > 0].sort_values(col_fecha)
    if _r.empty:
        return None
    _p = _r[col_punit]
    _ini, _fin = float(_p.iloc[0]), float(_p.iloc[-1])
    return {
        "inicio": _ini, "fin": _fin,
        "var_pct": ((_fin - _ini) / _ini * 100.0) if _ini else None,
        "minimo": float(_p.min()), "maximo": float(_p.max()),
        "n": int(len(_r)),
        "um": (str(_r[col_um].iloc[-1]) if col_um and col_um in _r.columns
               else ""),
        "cantidad": (float(pd.to_numeric(g[col_cant], errors="coerce")
                           .fillna(0).sum()) if col_cant else 0.0),
        "valor": float(pd.to_numeric(g[col_valor], errors="coerce")
                       .fillna(0).sum()),
    }


def _compras_producto_drill(d, col_prod, col_fam, col_valor, col_cant, col_punit,
                            col_um, col_fecha, col_prov=None, d_full=None):
    """Ranking de productos → evolución del producto en foco (Precio /
    Cantidad / Valor). Debajo, ranking por Familia → mini ranking de sus
    productos."""
    if not (col_prod and col_valor and col_punit and col_fecha):
        st.info("Faltan columnas (Producto, Valor, Precio unitario o Fecha) "
                "para este gráfico.")
        return

    dd = d.copy()
    dd[col_fecha] = pd.to_datetime(dd[col_fecha], errors="coerce")
    dd[col_punit] = pd.to_numeric(dd[col_punit], errors="coerce")
    dd[col_valor] = pd.to_numeric(dd[col_valor], errors="coerce").fillna(0)
    dd = dd.dropna(subset=[col_fecha, col_prod])
    dd = dd[dd[col_prod].astype(str).str.strip() != ""]
    if dd.empty:
        st.info("Sin datos en el rango seleccionado.")
        return

    st.markdown(_CSS_SELECTOR_TEXTO, unsafe_allow_html=True)

    ranking = _prod_ranking(dd, col_prod, col_fecha, col_valor, col_cant,
                            col_punit, col_um)
    if ranking.empty:
        st.info("Sin productos con precio válido en el rango.")
        return

    # ── Card 1: ranking de productos + evolución del producto en foco ────
    with st.container(border=True, key="compras_prod_card_ranking"):
        prod_focus = st.session_state.get("compras_prod_focus")
        if prod_focus not in set(ranking["producto"]):
            prod_focus = None

        col_tabla, col_detalle = st.columns(COLUMNAS_DRILL, gap=GAP_DRILL)
        with col_tabla:
            st.markdown('<div class="cp-prod-rank-tit">Ranking de productos</div>',
                       unsafe_allow_html=True)

            # SIN el punto en "Cant": AG Grid resuelve `field` con notación
            # de PATH ("a.b" -> row.a.b), así que un campo "Cant." se parte
            # en ["Cant", ""] y la celda sale vacía en silencio, sin ningún
            # error (arquitectura.md regla #192). El punto vuelve como
            # `headerName` en el columnDef, así que el rótulo no cambia.
            disp = ranking.rename(columns={
                "producto": "Producto", "valor": "Valor", "pct": "%",
                "cantidad": "Cant", "um": "UM", "inicio": "Inicio",
                "fin": "Fin", "var_pct": "Var",
            })
            _val_max_prod = float(ranking["valor"].max()) if len(ranking) else 1.0
            disp["_barra"] = disp["Valor"] / _val_max_prod * 100
            _resp_prod = AgGrid(
                disp[["Producto", "Valor", "%", "Cant", "UM", "Inicio",
                     "Fin", "Var", "_barra"]],
                gridOptions={
                    # Ocho columnas visibles, y NINGUNA lleva `flex`: se
                    # probó (Producto/Valor con flex:2/1.3 + minWidth) y
                    # `st_aggrid` le clava `width: 200` a cada columna que
                    # no trae un `width` propio — verificado con
                    # `api.getColumnDefs()`, que devolvía flex Y width:200
                    # JUNTOS en el mismo colDef resuelto. AG Grid prioriza
                    # el `width` explícito para el tamaño inicial, así que
                    # el flex nunca llegaba a repartir nada: a 1280px
                    # Producto+Valor se comían 400px fijos y "Var" quedaba
                    # fuera del viewport, con una scrollbar de 1px. Ancho
                    # fijo en las OCHO columnas —mismo criterio que ya
                    # usaban las seis angostas— saca el problema de raíz.
                    "columnDefs": [
                        {"field": "Producto", "width": 150,
                         "tooltipField": "Producto"},
                        {"field": "Valor", "width": 96,
                         "type": "numericColumn",
                         "cellStyle": _js_barra_prod,
                         "valueFormatter": _js_soles0_prod},
                        {"field": "%", "width": 52,
                         "type": "numericColumn",
                         "valueFormatter": _js_pct_prod},
                        {"field": "Cant", "headerName": "Cant.",
                         "width": 60, "type": "numericColumn",
                         "valueFormatter": _js_num0_prod},
                        {"field": "UM", "width": 56},
                        {"field": "Inicio", "width": 72,
                         "type": "numericColumn",
                         "valueFormatter": _js_soles2_prod},
                        {"field": "Fin", "width": 72,
                         "type": "numericColumn",
                         "valueFormatter": _js_soles2_prod},
                        {"field": "Var", "width": 60,
                         "type": "numericColumn",
                         "valueFormatter": _js_pct_signed_prod},
                        {"field": "_barra", "hide": True},
                    ],
                    "rowSelection": {"mode": "singleRow",
                                     "checkboxes": False,
                                     "enableClickSelection": False},
                    "onRowClicked": _js_toggle_prod,
                    "rowHeight": _ALTO_FILA,
                    "headerHeight": 38,
                    "suppressCellFocus": True,
                    "suppressMovableColumns": True,
                },
                allow_unsafe_jscode=True,
                theme="streamlit",
                height=_ALTO_FRAME,
                update_on=["selectionChanged"],
                key="compras_prod_rank_tab",
            )
            # AgGrid devuelve la selección VIGENTE en cada corrida (no un
            # evento) — comparar contra `prod_focus` alcanza, sin dedup.
            # Selección vacía (reclic en la fila ya elegida, el toggle de
            # `_js_toggle_prod`) TAMBIÉN limpia el foco.
            _sel_prod = getattr(_resp_prod, "selected_rows", None)
            if _sel_prod is not None and len(_sel_prod):
                _fila_sel = (_sel_prod.iloc[0] if hasattr(_sel_prod, "iloc")
                            else _sel_prod[0])
                _clicked = str(_fila_sel["Producto"])
            else:
                _clicked = None
            if _clicked != prod_focus:
                prod_focus = _clicked
                st.session_state["compras_prod_focus"] = prod_focus
            st.caption("UM = unidad de kardex · Inicio/Fin = primera y última "
                      "compra real del período · % es sobre el total del rango.")

        with col_detalle:
            prod_foco = prod_focus if prod_focus is not None else ranking.iloc[0]["producto"]

            st.markdown(f'<div style="font-size:13.5px;font-weight:700;">'
                       f'{_compras_truncar(prod_foco, 40)}</div>',
                       unsafe_allow_html=True)

            # ── VENTANA PROPIA DE ESTA TARJETA ───────────────────────────
            # 2026-08-26, a pedido ("creo que no es entendible para el
            # usuario"), y es la CAUSA de que no lo fuera: el eje salía del
            # rango de la franja —~24 días por defecto— así que pedirle
            # "agrupá por Mes" o "por Año" a 24 días sólo podía dar UN
            # grupo. Medido: con el default, la traza "Promedio mes" tenía
            # 1 punto y el eje un solo tick ("Aug 2026"); en Año, 1 punto
            # anclado al 1-ene mientras las compras eran de agosto, y las
            # 11 compras reales apiladas en 18px de los ~300 del gráfico.
            #
            # Con ventana propia (mismo `periodo.selector` que Evolución en
            # proveedor.py y que Volatilidad) "Mes" da 12 puntos y la línea
            # existe de verdad. El caso de UN período sigue siendo posible
            # (elegir "Año" sobre 12 meses) y se dibuja distinto, más
            # abajo — no se esconde la opción: que una granularidad
            # aparezca y desaparezca según el rango confunde más que
            # dibujar bien el caso degenerado.
            # No es una fila de drill (COLUMNAS_DRILL no aplica): el
            # selector ocupa el tercio izquierdo de la columna de detalle
            # y deja respirar el resto. Mismo gesto y misma proporción
            # que el de Volatilidad.
            # columnas-internas: selector de ventana, dentro de la tarjeta.
            _c_per = st.columns([1, 2])[0]
            with _c_per:
                _op_prod = periodo.selector("compras_prod_periodo",
                                            widget="lista")
            _src_evo = dd
            if _op_prod != periodo.HEREDA and d_full is not None:
                _rec = periodo.recortar(d_full, col_fecha, _op_prod)
                _rec = _rec.copy()
                _rec[col_fecha] = pd.to_datetime(_rec[col_fecha], errors="coerce")
                _rec[col_punit] = pd.to_numeric(_rec[col_punit], errors="coerce")
                _rec[col_valor] = pd.to_numeric(_rec[col_valor], errors="coerce").fillna(0)
                _src_evo = _rec.dropna(subset=[col_fecha, col_prod])

            g = _src_evo[_src_evo[col_prod].astype(str) == prod_foco]
            # Las cifras del encabezado salen de `g`, o sea de la MISMA
            # ventana que los puntos. Antes salían de `ranking`, que se
            # calcula sobre el rango de la franja: con ventana propia eso
            # sería un número describiendo un período y unos puntos
            # dibujando otro.
            fila = _prod_stats(g, col_fecha, col_punit, col_cant, col_valor,
                               col_um)

            with st.container(key="compras_prod_gran"):
                gran = st.pills("Agrupar por", ["Semana", "Mes", "Año"], default="Mes",
                                key="compras_prod_gran_pills",
                                label_visibility="collapsed") or "Mes"
            with st.container(key="compras_prod_modo"):
                modo = st.pills("Ver", ["Precio", "Cantidad", "Valor"], default="Precio",
                                key="compras_prod_modo_pills",
                                label_visibility="collapsed") or "Precio"

            agg = _prod_serie_periodo(g, col_fecha, col_punit, col_cant, col_valor, gran)
            fig = go.Figure()
            gw = gran.lower()

            if modo == "Precio":
                if agg.empty or fila is None:
                    st.info("Sin compras con precio válido para este producto.")
                else:
                    # UN SOLO PERÍODO → EL PROMEDIO ES UN NIVEL, NO UNA
                    # TENDENCIA, y se dibuja como tal.
                    #
                    # Con `mode="lines+markers"` y un punto, Plotly dibuja
                    # sólo el marcador: la leyenda decía "Promedio año" y
                    # el caption "LÍNEA = promedio", prometiendo una línea
                    # que no existía. Peor en "Año", donde ese único punto
                    # se ancla al 1-ene (la etiqueta del período) mientras
                    # las compras son de agosto — se leía como que el
                    # precio "venía" de enero.
                    #
                    # Una `hline` es lo que un promedio de un período
                    # REALMENTE es: un nivel de referencia a lo ancho. No
                    # tiene x, así que el problema del ancla desaparece
                    # solo, y el gráfico pasa a leerse sin ayuda ("puntos =
                    # cada compra, raya = su promedio").
                    _un_periodo = len(agg) < 2
                    if _un_periodo:
                        fig.add_hline(
                            y=float(agg["precio"].iloc[0]),
                            line=dict(color=ACENTO, width=2.4),
                            annotation_text=f"promedio {gw}",
                            annotation_position="top left",
                            annotation_font=dict(size=10, color=ACENTO))
                    else:
                        fig.add_scatter(
                            x=agg.index, y=agg["precio"], mode="lines+markers",
                            name=f"Promedio {gw}", line=dict(color=ACENTO, width=2.4),
                            marker=dict(size=6),
                            hovertemplate="%{x|%d/%m/%Y}: S/ %{y:,.2f}<extra>Promedio</extra>",
                        )
                    _real = g.dropna(subset=[col_punit])
                    _real = _real[_real[col_punit] > 0].sort_values(col_fecha)
                    _cd = (_real[col_prov].astype(str).values
                           if col_prov and col_prov in _real.columns else None)
                    fig.add_scatter(
                        x=_real[col_fecha], y=_real[col_punit], mode="markers",
                        name="Compra real",
                        marker=dict(size=7, color="white",
                                   line=dict(color=ACENTO, width=1.5)),
                        customdata=_cd,
                        hovertemplate=(
                            "%{x|%d/%m/%Y}: S/ %{y:,.2f}"
                            + ("<br>%{customdata}" if _cd is not None else "")
                            + "<extra>Compra</extra>"),
                    )
                    # "+0.0% EN EL PERÍODO" NO ERA LO QUE PARECÍA. `var`
                    # es primera COMPRA contra última, así que un producto
                    # que arrancó y terminó en S/ 74.50 daba +0.0% aunque
                    # los puntos fueran de 72 a 100 — se leía como "no pasó
                    # nada" al lado de un gráfico que gritaba lo contrario.
                    # Ahora el % se rotula por lo que ES ("1ª → última") y
                    # al lado va el rango min-max, que es el dato que la
                    # persona tiene delante de los ojos.
                    var_pct = fila["var_pct"]
                    color_var = (ERROR if var_pct and var_pct > 0.05
                                else (EXITO if var_pct and var_pct < -0.05 else GRIS_TEXTO))
                    _um = f"/{fila['um']}" if fila["um"] else ""
                    _rango_txt = ""
                    if fila["maximo"] > fila["minimo"]:
                        _rango_txt = (f' · entre <b>S/ {fila["minimo"]:,.2f}</b>'
                                      f' y <b>S/ {fila["maximo"]:,.2f}</b>')
                    st.markdown(
                        f'<div style="font-size:12px;color:{GRIS_TEXTO};margin:2px 0 6px;">'
                        f'actual <b>S/ {fila["fin"]:,.2f}{_um}</b> · '
                        f'<b style="color:{color_var};">'
                        f'{"+" if (var_pct or 0) >= 0 else "−"}{abs(var_pct or 0):.1f}%'
                        f'</b> 1ª → última{_rango_txt}</div>',
                        unsafe_allow_html=True)
                    _compras_layout(fig, alto=alturas.MINI)
                    fig.update_layout(legend=dict(orientation="h", y=-0.25, x=0,
                                                  font=dict(size=10)))
                    fig.update_xaxes(**_eje_x_kwargs(gran, agg))
                    st.plotly_chart(fig, use_container_width=True,
                                    key=f"compras_g_prod_precio_{gran}")
                    # El caption dice lo que el gráfico DIBUJA, que no es
                    # lo mismo en los dos casos: con un solo período no hay
                    # tendencia que leer, hay un nivel.
                    st.caption(
                        (f"Puntos = precio real de cada compra · la raya es "
                         f"su promedio ({gw} único en la ventana elegida).")
                        if _un_periodo else
                        (f"Línea = promedio {gw} · puntos = precio real de "
                         f"cada compra."))
            else:
                col_serie = "cantidad" if modo == "Cantidad" else "valor"
                total = float((fila or {}).get(
                    "cantidad" if modo == "Cantidad" else "valor", 0.0))
                if agg.empty or fila is None:
                    st.info("Sin compras para este producto en el rango.")
                else:
                    _pref = "" if modo == "Cantidad" else "S/ "
                    _tpl = "%{y:,.0f}" if modo == "Cantidad" else "S/ %{y:,.2f}"
                    fig.add_bar(x=agg.index, y=agg[col_serie], marker_color=ACENTO,
                               hovertemplate="%{x|%d/%m/%Y}<br>" + _tpl + "<extra></extra>")
                    _um = f" {fila['um']}" if (modo == "Cantidad" and fila["um"]) else ""
                    _prom = total / len(agg) if len(agg) else 0.0
                    st.markdown(
                        f'<div style="font-size:12px;color:{GRIS_TEXTO};margin:2px 0 6px;">'
                        f'total <b>{_pref}{total:,.0f}{_um}</b> · '
                        f'promedio <b>{_pref}{_prom:,.0f}{_um}/{gw}</b></div>',
                        unsafe_allow_html=True)
                    _compras_layout(fig, alto=alturas.MINI)
                    fig.update_layout(showlegend=False,
                                      yaxis=dict(tickprefix=_pref, tickformat=",.0f"))
                    fig.update_xaxes(**_eje_x_kwargs(gran, agg))
                    st.plotly_chart(fig, use_container_width=True,
                                    key=f"compras_g_prod_{modo}_{gran}")
                    _etq = "cantidad comprada" if modo == "Cantidad" else "valor comprado"
                    st.caption(f"Barras = {_etq} por {gw}.")

    # ── Card 2: ranking por familia + mini ranking de sus productos ──────
    if not col_fam or col_fam not in dd.columns:
        return

    with st.container(border=True, key="compras_prod_card_familia"):
        fam_ranking = _fam_ranking(dd, col_fam, col_prod, col_valor)
        fam_focus = st.session_state.get("compras_prod_fam_focus")
        if fam_focus not in set(fam_ranking["familia"]):
            fam_focus = None

        # columnas-internas: Panel B pasó de gráfico a tabla (ver docstring
        # del módulo) y ya no necesita el ancho extra que un gráfico de
        # barras reclamaba para sus etiquetas de texto afuera.
        col_famtabla, col_famdet = st.columns([1.3, 1], gap=GAP_DRILL)
        with col_famtabla:
            st.markdown('<div class="cp-prod-rank-tit">Compras por familia</div>',
                       unsafe_allow_html=True)

            disp_fam = fam_ranking.rename(columns={
                "familia": "Familia", "valor": "Valor", "pct": "%",
                "productos": "Productos",
            })
            _val_max_fam = (float(fam_ranking["valor"].max())
                           if len(fam_ranking) else 1.0)
            disp_fam["_barra"] = disp_fam["Valor"] / _val_max_fam * 100
            _resp_fam = AgGrid(
                disp_fam[["Familia", "Valor", "%", "Productos", "_barra"]],
                gridOptions={
                    # Sin `flex`: mismo motivo que el ranking de arriba
                    # (`st_aggrid` le clava `width: 200` a toda columna sin
                    # `width` propio, y ese `width` le gana al `flex`).
                    "columnDefs": [
                        {"field": "Familia", "width": 210,
                         "tooltipField": "Familia"},
                        {"field": "Valor", "width": 100,
                         "type": "numericColumn",
                         "cellStyle": _js_barra_prod,
                         "valueFormatter": _js_soles0_prod},
                        {"field": "%", "width": 56,
                         "type": "numericColumn",
                         "valueFormatter": _js_pct_prod},
                        {"field": "Productos", "width": 80,
                         "type": "numericColumn",
                         "valueFormatter": _js_num0_prod},
                        {"field": "_barra", "hide": True},
                    ],
                    "rowSelection": {"mode": "singleRow",
                                     "checkboxes": False,
                                     "enableClickSelection": False},
                    "onRowClicked": _js_toggle_prod,
                    "rowHeight": _ALTO_FILA,
                    "headerHeight": 38,
                    "suppressCellFocus": True,
                    "suppressMovableColumns": True,
                },
                allow_unsafe_jscode=True,
                theme="streamlit",
                height=_ALTO_FRAME,
                update_on=["selectionChanged"],
                key="compras_prod_fam_rank_tab",
            )
            _sel_fam = getattr(_resp_fam, "selected_rows", None)
            if _sel_fam is not None and len(_sel_fam):
                _fila_fam = (_sel_fam.iloc[0] if hasattr(_sel_fam, "iloc")
                            else _sel_fam[0])
                _clicked_fam = str(_fila_fam["Familia"])
            else:
                _clicked_fam = None
            if _clicked_fam != fam_focus:
                fam_focus = _clicked_fam
                st.session_state["compras_prod_fam_focus"] = fam_focus
            st.caption("% sobre el total comprado en el rango.")

        with col_famdet:
            fam_foco = fam_focus if fam_focus is not None else fam_ranking.iloc[0]["familia"]
            st.markdown(f'<div class="cp-prod-rank-tit">{_compras_truncar(fam_foco, 40)}</div>',
                       unsafe_allow_html=True)
            serie_fam = (dd[_fam_normalizada(dd, col_fam) == fam_foco]
                        .groupby(col_prod)[col_valor].sum().nlargest(10))
            if serie_fam.empty:
                st.info("Sin productos para esta familia.")
            else:
                disp_prodfam = (serie_fam.rename_axis("Producto")
                               .reset_index(name="Valor"))
                _val_max_prodfam = float(disp_prodfam["Valor"].max())
                disp_prodfam["_barra"] = disp_prodfam["Valor"] / _val_max_prodfam * 100
                AgGrid(
                    disp_prodfam[["Producto", "Valor", "_barra"]],
                    gridOptions={
                        # Mismos anchos/renderers que la tabla de Familia:
                        # panel A y B deben leerse como una sola grilla.
                        "columnDefs": [
                            {"field": "Producto", "width": 210,
                             "tooltipField": "Producto"},
                            {"field": "Valor", "width": 100,
                             "type": "numericColumn",
                             "cellStyle": _js_barra_prod,
                             "valueFormatter": _js_soles0_prod},
                            {"field": "_barra", "hide": True},
                        ],
                        "rowHeight": _ALTO_FILA,
                        "headerHeight": 38,
                        "suppressCellFocus": True,
                        "suppressMovableColumns": True,
                    },
                    allow_unsafe_jscode=True,
                    theme="streamlit",
                    height=_ALTO_FRAME,
                    key=f"compras_prod_fam_det_tab_{_slug(fam_foco)}",
                )
            st.caption("Top 10 productos de la familia, por valor comprado.")
