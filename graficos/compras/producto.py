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
from graficos.ventas_comparativo import _fmt_soles_compacto
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
.st-key-compras_prod_gran [data-testid="stButtonGroup"] {{
    gap: 10px !important;
    justify-content: flex-end !important;
}}
.st-key-compras_prod_gran [data-testid="stButtonGroup"] button[role="radio"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 1px 0 !important;
    min-height: 0 !important;
    font-size: 12.5px !important;
    font-weight: 400 !important;
    color: {GRIS_TEXTO} !important;
}}
.st-key-compras_prod_gran [data-testid="stButtonGroup"] button[role="radio"][data-selected] {{
    color: {ACENTO} !important;
    font-weight: 600 !important;
}}
/* El selector de ventana (3m/12m/…), APLANADO A TEXTO para que haga
   juego con la granularidad de al lado: los dos son texto suelto, no
   una caja contra unas palabras. Misma receta que `cp_evo_ctrl` en
   _css_proveedor.py — se conserva el chevron, que es la única señal de
   que eso despliega. */
.st-key-compras_prod_periodo_wrap [data-testid="stSelectbox"] div[role="group"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    min-height: 0 !important;
    height: 22px !important;
}}
.st-key-compras_prod_periodo_wrap [data-testid="stSelectbox"] input {{
    padding: 0 !important;
    height: auto !important;
    font-size: 12.5px !important;
    font-weight: 400 !important;
    color: {GRIS_TEXTO} !important;
    cursor: pointer !important;
}}
.st-key-compras_prod_periodo_wrap [data-testid="stSelectbox"]:hover input {{
    color: {ACENTO} !important;
}}
.st-key-compras_prod_periodo_wrap [data-testid="stSelectbox"] svg {{
    width: 13px !important;
    height: 13px !important;
    fill: {ACENTO} !important;
    color: {ACENTO} !important;
}}
.st-key-compras_prod_periodo_wrap [data-testid="stSelectbox"]
    button[aria-haspopup] {{
    width: 16px !important;
    min-width: 0 !important;
    height: 22px !important;
    min-height: 0 !important;
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    flex: 0 0 auto !important;
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
            # ── UNA SOLA FILA DE CONTROLES: ventana + granularidad ──────
            # 2026-08-26, a pedido. Antes eran TRES renglones apilados —
            # ventana, granularidad y modo (Precio/Cantidad/Valor)— y el
            # gráfico arrancaba recién debajo. El modo se va del todo (las
            # tres métricas pasan a verse SIEMPRE, como etiqueta de cada
            # barra) y los dos que quedan comparten renglón, alineados.
            # Son ~40px que gana el gráfico.
            # columnas-internas: ventana y granularidad, dentro de la
            # tarjeta. No es una fila de drill: COLUMNAS_DRILL no aplica.
            _c_win, _c_gran = st.columns([1, 1.35],
                                         vertical_alignment="center")
            with _c_win:
                with st.container(key="compras_prod_periodo_wrap"):
                    _op_prod = periodo.selector("compras_prod_periodo",
                                                widget="lista")
            with _c_gran:
                with st.container(key="compras_prod_gran"):
                    gran = st.pills("Agrupar por", ["Semana", "Mes", "Año"],
                                    default="Mes",
                                    key="compras_prod_gran_pills",
                                    label_visibility="collapsed") or "Mes"

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
            # ventana que las barras. Antes salían de `ranking`, que se
            # calcula sobre el rango de la franja: con dos ventanas
            # distintas sería un número describiendo un período y unas
            # barras dibujando otro.
            fila = _prod_stats(g, col_fecha, col_punit, col_cant, col_valor,
                               col_um)
            agg = _prod_serie_periodo(g, col_fecha, col_punit, col_cant,
                                      col_valor, gran)
            gw = gran.lower()

            if agg.empty or fila is None:
                st.info("Sin compras con precio válido para este producto.")
            else:
                var_pct = fila["var_pct"]
                color_var = (ERROR if var_pct and var_pct > 0.05
                            else (EXITO if var_pct and var_pct < -0.05 else GRIS_TEXTO))
                _um = f"/{fila['um']}" if fila["um"] else ""
                _rango_txt = ""
                if fila["maximo"] > fila["minimo"]:
                    _rango_txt = (f' · entre <b>S/ {fila["minimo"]:,.2f}</b>'
                                  f' y <b>S/ {fila["maximo"]:,.2f}</b>')
                st.markdown(
                    f'<div style="font-size:12px;color:{GRIS_TEXTO};margin:0 0 2px;">'
                    f'actual <b>S/ {fila["fin"]:,.2f}{_um}</b> · '
                    f'<b style="color:{color_var};">'
                    f'{"+" if (var_pct or 0) >= 0 else "−"}{abs(var_pct or 0):.1f}%'
                    f'</b> 1ª → última{_rango_txt}</div>',
                    unsafe_allow_html=True)

                # ── BARRAS, con las dos cifras SIEMPRE a la vista ────────
                # Antes había que elegir una de tres (Precio/Cantidad/
                # Valor) con un selector, y las otras dos no existían. Ahora
                # la barra ES el valor comprado del período y encima lleva,
                # fijo, el precio promedio de ese período — que es la
                # pregunta que traía a este panel ("¿a cuánto me salió, y
                # cuánto compré?") respondida de una sola mirada.
                #
                # El valor va COMPACTO (`_fmt_soles_compacto`, nacido para
                # este mismo problema en ventas_comparativo.py): "S/ 11k"
                # entra en una barra angosta donde "S/ 11,268" se corta o
                # se pisa con la vecina. El monto exacto sigue en el hover.
                fig = go.Figure()
                _precio = agg["precio"].tolist()
                _valor = agg["valor"].tolist()
                # LA ETIQUETA ROTA SI NO ENTRA, no se encoge. MEDIDO en
                # vivo: el panel da 312px de ancho y la etiqueta de dos
                # renglones ocupa 34-36px, así que entran hasta ~8 barras.
                # Con 13 (la ventana de 12 meses por Mes) Plotly no la
                # oculta ni la corta: la ESCALA hasta 13px de ancho por 8
                # de alto — sigue en el DOM y ya no se lee. Es la trampa de
                # la regla #91, y la razón de que este umbral esté acá y no
                # a ojo.
                #
                # Rotada, la etiqueta necesita ~10px de ancho en vez de 36,
                # así que entra siempre. Se paga leyéndola de costado, que
                # es mejor que no leerla: el pedido fue "etiqueta SIEMPRE
                # visible".
                _muchas = len(agg) > 8
                if _muchas:
                    _etiquetas = [f"S/ {pr:,.2f} · {_fmt_soles_compacto(v)}"
                                  for pr, v in zip(_precio, _valor)]
                else:
                    _etiquetas = [f"S/ {pr:,.2f}<br>{_fmt_soles_compacto(v)}"
                                  for pr, v in zip(_precio, _valor)]
                fig.add_bar(
                    x=agg.index, y=_valor, marker_color=ACENTO,
                    text=_etiquetas, textposition="outside",
                    textangle=-90 if _muchas else 0,
                    textfont=dict(size=9, color=GRIS_TEXTO),
                    cliponaxis=False, constraintext="none",
                    customdata=_precio,
                    hovertemplate=("%{x|%d/%m/%Y}<br>valor S/ %{y:,.2f}"
                                   "<br>precio prom. S/ %{customdata:,.2f}"
                                   "<extra></extra>"),
                )
                _compras_layout(fig, alto=alturas.MINI)
                fig.update_layout(showlegend=False,
                                  yaxis=dict(showticklabels=False),
                                  bargap=0.35)
                # Techo con aire para que la etiqueta de DOS renglones
                # quepa encima de la barra más alta: `textposition=
                # "outside"` no expande el rango solo, y sin esto la
                # etiqueta del máximo se corta contra el borde.
                # Rotada, la etiqueta ocupa ALTO en vez de ancho, así que
                # el techo tiene que dar más aire.
                if max(_valor) > 0:
                    fig.update_yaxes(
                        range=[0, max(_valor) * (1.75 if _muchas else 1.28)])
                fig.update_xaxes(**_eje_x_kwargs(gran, agg))
                st.plotly_chart(fig, use_container_width=True,
                                key=f"compras_g_prod_{gran}")
                st.caption(f"Barra = valor comprado por {gw} · encima, el "
                           f"precio promedio de ese {gw}.")

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
