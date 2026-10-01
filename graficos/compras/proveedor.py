"""graficos.compras.proveedor - drill de Proveedor.

Ranking de proveedores como tabla (nombre + barra de valor + documentos +
%). Clic en una fila fija el foco y filtra las otras tres tarjetas.

Desde el 2026-10-01 (reglas #578 y #579) son dos filas:

    [ Ranking de proveedores ][ Productos del proveedor           ]
    [ Documentos      ][ Evolución                               ]

Los proveedores de cada producto se despliegan DEBAJO de su fila en la
tabla de Productos (no hay tarjeta «Proveedores de»), y Documentos y
Productos se pueden agrupar con los períodos de la Evolución. La fila de
abajo mide seis filas, para que la vista entre en una laptop.

Las columnas se crean ARRIBA, antes de llenar ninguna, porque el orden en
que se calculan no es el de la pantalla: el Ranking fija el foco que leen
las demás, y Documentos y Productos usan los períodos de la Evolución,
así que se dibujan después de ella.

Es el drill mas grande del dashboard. Incluye un bloque largo de CSS
inyectado con st.markdown para los controles flotantes sobre el grafico;
vive aca (y no en estilos/) porque esta scopeado a las keys de este drill.
"""

import html
import zlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from st_aggrid import AgGrid, JsCode

from tema import (ACENTO, ACENTO_TEXTO_OSCURO, ERROR, EXITO, GRIS_BORDE,
                  GRIS_TEXTO, LAVANDA_CHIP,
                  TEXTO_PRINCIPAL)
from inyecciones import inject_hover_kpis, inyectar_html
from graficos.base import (
    PALETA_CALLAI, _card, _compras_layout, _compras_truncar,
    paso_etiquetas, preservar_widgets,
)
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CATEGORIA_SEC, COLUMNAS_DRILL_TABLAS,
    COLUMNAS_DRILL_ABAJO, CROMO_GRID_RANK, GAP_DRILL, agregar_periodo,
    base_normalizada, documento_legible, filtro_proveedores, moda_por_grupo,
    periodos_ordenados, selector_fecha_tarjeta,
)
from graficos.compras._css_proveedor import (
    CSS as CSS_PROVEEDOR, CSS_RANKING_GRID,
)
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos import alturas, periodo


_KEYS_WIDGET = (
    "compras_prov_gran", "cp_prov_win_size", "cp_evo_periodo",
    "cp_prov_show_names", "cp_prov_docs_modo", "cp_prov_prods_modo",
    "cp_evo_medida", "cp_prov_prods_medida",
    "cp_prov_q", "cp_prov_cb::*",
)
"""Los controles de esta sección, para que la escalada no se los lleve.

La consume `preservar_widgets` en el `st.rerun(scope="app")` de más abajo:
ese rerun aborta la corrida antes de dibujarlos y Streamlit recolecta lo
que no se dibujó, así que sin esta tupla mover la fecha de la cabecera
devolvía la granularidad a «Mes», apagaba «Nombres en barras» y volvía a
marcar a TODOS los proveedores. Ver `graficos/base.py::preservar_widgets` y
`arquitectura.md` regla #373.

Las dos últimas son del filtro de proveedores (`_comun.py`), que dibuja una
checkbox por razón social — de ahí el prefijo con `*`. Los cinco botones de
atajo (`cp_prov_topn3`…) NO van: un `st.button` no guarda nada."""


def _prov_mayor(src, col_prov, col_valor):
    """El proveedor de mayor valor comprado en `src`, o None.

    Lo usa la tarjeta de Evolución para elegir a QUIÉN grafica cuando nadie
    clickeó un proveedor todavía. Recibe el histórico (`d_full`) a
    propósito — ver el comentario del llamador."""
    if src is None or not col_prov or col_prov not in src.columns:
        return None
    _v = pd.to_numeric(src[col_valor], errors="coerce").fillna(0)
    _g = _v.groupby(src[col_prov].astype(str)).sum()
    _g = _g[(_g.index.notna()) & (_g.index != "nan") & (_g.index != "")]
    return str(_g.idxmax()) if len(_g) else None


_GRAN_POR = {"Día": "Por día", "Semana": "Por semana", "Mes": "Por mes",
             "Año": "Por año"}
"""Rótulo del modo «agrupado» de los Documentos y los Productos: dice la
granularidad de la Evolución, que es la que manda sobre ese modo."""


def _var_pct(cur, prev):
    """Variación % de `cur` contra `prev`, con `inf` cuando no hay contra
    qué comparar (no hay anterior, o el anterior es cero).

    `inf` y no NaN: nació para un `st.dataframe`, donde un vacío se pinta
    «None» aunque el Styler diga otra cosa (regla #529); desde que las
    tablas son HTML sólo importa que `_fmt_var` lo escribe «—». Desde cero no hay porcentaje: el mismo
    criterio que los KPIs de la Evolución (`_var_txt`)."""
    if prev is None or pd.isna(prev) or float(prev) <= 0:
        return np.inf
    return (float(cur) - float(prev)) / float(prev) * 100


def _fmt_var(v):
    """«▲ 12.3%», «▼ 4.0%», «0.0%» o «—». Mismos umbrales que `_var_txt`
    de la Evolución: por debajo del 0,05 % no hay flecha."""
    if not np.isfinite(v):
        return "—"
    if abs(v) < 0.05:
        return "0.0%"
    return f"{'▲' if v > 0 else '▼'} {abs(v):.1f}%"


_MEDIDAS = {"valor": "Soles", "cant": "Cantidad", "precio": "Precio"}
"""Lo que pueden medir la Evolución y los Productos «por período»
(2026-10-01, a pedido: «un selector Soles / Cantidad / Precio»). Regla
#579. Cantidad y Precio sólo tienen sentido sobre UN producto en la
Evolución: sumar kilos de mantequilla con litros de aceite no da nada que
se pueda leer."""


def _serie_medida(df, orden, medida):
    """La medida de `df` por período, en el orden de `orden` (los que no
    tienen compras salen en cero, o vacíos en Precio).

    El precio es el PROMEDIO PONDERADO del período —lo pagado sobre lo
    comprado—, no el promedio de los precios de cada compra: una compra
    grande pesa lo que pesó en la caja. Sin cantidad no hay precio, y queda
    vacío (NaN) en vez de en cero, que se leería como «gratis»."""
    g = (df.groupby("per").agg(valor=("valor", "sum"), cant=("cant", "sum"))
           .reindex(orden).fillna(0.0))
    if medida == "cant":
        return g["cant"]
    if medida == "precio":
        return g["valor"] / g["cant"].where(g["cant"] > 0)
    return g["valor"]


def _fmt_medida(v, medida, um=""):
    """Un valor de la medida, como se lee: «S/ 4,421», «112 KILOS»,
    «S/ 39.41» (el precio con céntimos: es lo único que se compara al
    céntimo) o «—»."""
    if v is None or pd.isna(v):
        return "—"
    if medida == "cant":
        return f"{v:,.0f}" + (f" {um}" if um else "")
    if medida == "precio":
        return f"S/ {v:,.2f}"
    return f"S/ {v:,.0f}"


def _fila_var(v):
    """La celda «Var. %» de las tablas HTML: el texto de `_fmt_var` con el
    color de Compras (rojo si subió el gasto, verde si bajó, sin color por
    debajo del 0,5 %)."""
    _cls = ("" if not np.isfinite(v) or abs(v) < 0.5
            else (" sube" if v > 0 else " baja"))
    return f'<span class="var{_cls}">{_fmt_var(v)}</span>'


def _cant_txt(c):
    """Una cantidad sin ceros de más: «112», «2.5», «0.75»."""
    return f"{c:,.2f}".rstrip("0").rstrip(".")


def _html_docs_por_documento(sub, alto_lista):
    """«Por documento»: una fila por comprobante, que se DESPLIEGA en sus
    productos con cantidad, precio unitario y valor. Devuelve
    `(html, n_documentos, total)`. `sub` son las líneas del proveedor en el
    rango del Ranking, con número de documento."""
    docs = (sub.groupby("docu", as_index=False)
               .agg(fecha=("fecha", "min"), valor=("valor", "sum"),
                    prods=("prod", "nunique"))
               .sort_values(["fecha", "docu"], ascending=False, kind="stable")
               .reset_index(drop=True))
    docs["leg"] = documento_legible(docs["docu"]).to_numpy()
    # Las líneas de cada documento, sumadas por producto (un producto puede
    # venir en dos líneas del mismo comprobante). El precio es lo pagado
    # sobre lo comprado; sin cantidad, «—».
    lin = (sub.groupby(["docu", "prod"], as_index=False)
              .agg(cant=("cant", "sum"), valor=("valor", "sum"),
                   um=("um", "first"))
              .sort_values(["docu", "valor"], ascending=[True, False],
                           kind="stable"))
    cuerpos = {}
    for docu, ls in lin.groupby("docu", sort=False):
        # Sólo arma TEXTO: lo calculado ya está arriba (regla #537).
        filas = []
        for r in ls.itertuples(index=False):
            um = "" if str(r.um) in ("", "nan", "None") else _esc(r.um)
            pu = (f"S/ {r.valor / r.cant:,.2f}" if r.cant else "—")
            filas.append(
                f'<div class="cp-dl-lin"><span class="nm" title="{_esc(r.prod)}">'
                f'{_esc(r.prod)}</span><span class="r">{_cant_txt(r.cant)}'
                f'{" " + um if um else ""}</span>'
                f'<span class="r">{pu}</span>'
                f'<span class="r">S/ {r.valor:,.0f}</span></div>')
        cuerpos[docu] = "".join(filas)
    vals = docs["valor"].to_numpy(dtype=float)
    filas = []
    for i, r in enumerate(docs.itertuples(index=False)):
        # Ordenado del más nuevo al más viejo: el anterior es el de ABAJO.
        var = _var_pct(vals[i], vals[i + 1] if i + 1 < len(vals) else None)
        fec = "—" if pd.isna(r.fecha) else pd.Timestamp(r.fecha).strftime("%d/%m/%y")
        filas.append(
            f'<details class="cp-dl-row"><summary>'
            f'<span>{fec}</span><span class="nm">{_esc(r.leg)}</span>'
            f'<span class="r">{int(r.prods)}</span>'
            f'<span class="r">S/ {r.valor:,.0f}</span>{_fila_var(var)}</summary>'
            f'<div class="cp-dl-det"><div class="cp-dl-lin cab"><span>Producto</span>'
            f'<span class="r">Cant.</span><span class="r">P. unit.</span>'
            f'<span class="r">Valor</span></div>{cuerpos.get(r.docu, "")}</div>'
            f'</details>')
    _ayuda = ("El rango del Ranking. Var. %: contra el documento anterior "
              "(el de abajo).")
    html_ = ('<div class="cp-dl cp-dl-doc"><div class="cp-dl-head">'
             '<span>Fecha</span><span>Documento</span>'
             '<span class="r" title="Productos distintos en el documento">Prods</span>'
             '<span class="r">Valor</span>'
             f'<span class="r ayuda" title="{_ayuda}">Var. %</span></div>'
             f'<div class="cp-pl-lista" style="max-height:{alto_lista}px">'
             + "".join(filas) + '</div></div>')
    return html_, len(docs), float(vals.sum())


def _html_docs_por_periodo(sp, per_orden, etq, alto_lista):
    """«Por <granularidad>»: una fila por período de la ventana de la
    Evolución, que se DESPLIEGA en sus documentos —número, fecha, cuántas
    filas (líneas) trae y su total—. Devuelve `(html, n_documentos,
    total)`. `sp` son las líneas del proveedor en esa ventana."""
    _sp = sp[sp["docu"].astype(str).str.strip() != ""]
    g = (sp.groupby("per")["valor"].sum().reindex(per_orden).fillna(0.0))
    n_docs = _sp.groupby("per")["docu"].nunique().reindex(per_orden).fillna(0)
    docs = (_sp.groupby(["per", "docu"], as_index=False)
               .agg(fecha=("fecha", "min"), valor=("valor", "sum"),
                    filas=("valor", "size"))
               .sort_values(["per", "fecha", "docu"],
                            ascending=[True, False, False], kind="stable"))
    docs["leg"] = documento_legible(docs["docu"]).to_numpy()
    cuerpos = {}
    for per, ds in docs.groupby("per", sort=False):
        # Sólo arma TEXTO (regla #537).
        cuerpos[per] = "".join(
            f'<div class="cp-dl-lin per"><span>'
            f'{"—" if pd.isna(r.fecha) else pd.Timestamp(r.fecha).strftime("%d/%m/%y")}'
            f'</span><span class="nm">{_esc(r.leg)}</span>'
            f'<span class="r">{int(r.filas)}</span>'
            f'<span class="r">S/ {r.valor:,.0f}</span></div>'
            for r in ds.itertuples(index=False))
    vals = g.to_numpy(dtype=float)
    filas = []
    for i in range(len(per_orden) - 1, -1, -1):
        p = per_orden[i]
        var = _var_pct(vals[i], vals[i - 1] if i else None)
        cuerpo = cuerpos.get(p)
        cab = ('<div class="cp-dl-lin per cab"><span>Fecha</span>'
               '<span>Documento</span><span class="r">Filas</span>'
               '<span class="r">Total</span></div>')
        filas.append(
            f'<details class="cp-dl-row"><summary>'
            f'<span class="nm"><b>{_esc(etq(p))}</b></span>'
            f'<span class="r">{int(n_docs.iloc[i])}</span>'
            f'<span class="r">S/ {vals[i]:,.0f}</span>{_fila_var(var)}</summary>'
            f'<div class="cp-dl-det">'
            + (cab + cuerpo if cuerpo
               else '<div class="cp-pl-vacio">Sin documentos en el período.</div>')
            + '</div></details>')
    _ayuda = ("Los períodos de la Evolución (su ventana). Var. %: contra el "
              "período anterior.")
    html_ = ('<div class="cp-dl cp-dl-per"><div class="cp-dl-head">'
             '<span>Período</span><span class="r">Docs</span>'
             '<span class="r">Valor</span>'
             f'<span class="r ayuda" title="{_ayuda}">Var. %</span></div>'
             f'<div class="cp-pl-lista" style="max-height:{alto_lista}px">'
             + "".join(filas) + '</div></div>')
    return html_, int(n_docs.sum()), float(vals.sum())


def _tarjeta_documentos(base, prov, alto, gran, src_per, per_orden, etq):
    """La tarjeta «Documentos · <proveedor>», abajo a la izquierda.

    Nació el 2026-10-01, a pedido (regla #578), y el mismo día ganó, de a
    pedidos (regla #579): el modo AGRUPADO según la Evolución, la variación
    % contra la fila anterior, el total al pie, la columna «Prods» y el
    DESPLIEGUE de cada fila:

    - **Por documento**: un comprobante por fila, del RANGO DEL RANKING
      (`base` ya viene recortado), con su fecha, su número, cuántos
      productos distintos trae, su valor y la variación contra el documento
      anterior (el de abajo). Se despliega en sus productos con cantidad,
      precio unitario y valor.
    - **Por <granularidad de la Evolución>**: un período por fila, de LA
      VENTANA de la Evolución (`src_per`/`per_orden`, también los que
      quedaron en cero; el Ranking abre en un mes y agrupado daba una o dos
      filas), con cuántos documentos y cuánto valor. Se despliega en sus
      documentos: número, fecha, cuántas filas trae y su total.

    Desde que se despliega es HTML (`<details>`) y no `st.dataframe`, que no
    tiene filas que se abran: abre al instante, sin rerun. La nota de cada
    modo es el TOOLTIP de la cabecera «Var. %» (un `title`: a pedido, «que
    sólo aparezca al pasar el cursor por la cabecera»), y el total va al pie.

    `alto` son las seis filas de la fila de abajo (`_ALTO_DOCS`): la lista
    scrollea a partir de ahí.
    """
    _tit = ("Documentos" if prov is None
            else f"Documentos · {_compras_truncar(nombre_propio(prov), 24)}")
    _por = _GRAN_POR.get(gran, "Por período")
    with st.container(border=True, key="compras_prov_card_docsprov"):
        with _card("prov_docsprov", _tit, titulo_arriba=True):
            # Las pastillas flotan en la fila del título (`cp_modo_*`, en
            # `_css_proveedor.py`). Valores ESTABLES y el rótulo por
            # `format_func`: el de «agrupado» cambia con la granularidad de
            # la Evolución, y un `st.pills` cuyo valor guardado no está entre
            # sus opciones revienta.
            if st.session_state.get("cp_prov_docs_modo") not in (None, "doc",
                                                                 "per"):
                del st.session_state["cp_prov_docs_modo"]
            with st.container(key="cp_modo_docs"):
                _modo = st.pills(
                    "Agrupar documentos", ["doc", "per"], default="doc",
                    format_func=lambda o: "Por documento" if o == "doc" else _por,
                    key="cp_prov_docs_modo", label_visibility="collapsed",
                ) or "doc"
            if prov is None:
                return
            if _modo == "per":
                if src_per is None or not per_orden:
                    st.caption("La Evolución no tiene períodos que agrupar.")
                    return
                _html, _n_docs, _tot = _html_docs_por_periodo(
                    src_per[src_per["prov"] == prov], per_orden, etq, alto)
            else:
                _sub = base[(base["prov"] == prov)
                            & (base["docu"].astype(str).str.strip() != "")]
                if _sub.empty:
                    st.caption("Sin números de documento para este "
                               "proveedor en el rango.")
                    return
                _html, _n_docs, _tot = _html_docs_por_documento(_sub, alto)
            # El TOTAL, al pie: el lavanda y la negrita de la fila TOTAL del
            # Ranking.
            _html += (f'<div class="cp-docs-total"><span>Total · {_n_docs:,} '
                      f'{"documento" if _n_docs == 1 else "documentos"}</span>'
                      f'<span>S/ {_tot:,.0f}</span></div>')
            # Remontaje por contenido, como la tabla de Productos (#377).
            _k = zlib.crc32(_html.encode("utf-8"))
            with st.container(key=f"cp_dl_{_k:08x}"):
                st.markdown(_html, unsafe_allow_html=True)


def _esc(t):
    return html.escape(str(t), quote=True)


def _filas_proveedores(src, prods, color_map):
    """`{producto: html}` con la lista de proveedores de cada producto de
    `prods` en `src` (el df NORMALIZADO, `base_normalizada`): el último
    precio unitario y su fecha, y en el desplegable de cada uno, la
    cantidad con su unidad y el total. Es la lista que hasta el 2026-10-01
    vivía en la tarjeta «Proveedores de» (regla #377), con las mismas clases
    `pb-*`.

    TODO de una vez, con un `groupby` por (producto, proveedor) y no un
    bucle por grupo (regla #537). El último precio es el de la compra más
    reciente CON precio, en orden estable (las compras del mismo día
    desempatan por su orden en el parquet)."""
    s = src[src["prod"].isin(prods)]
    if s.empty:
        return {}
    g = (s.groupby(["prod", "prov"], as_index=False)
          .agg(total=("valor", "sum"), cant=("cant", "sum")))
    ult = (s.dropna(subset=["fecha"]).sort_values("fecha", kind="stable")
            .groupby(["prod", "prov"], as_index=False)
            .agg(ult_p=("punit", "last"), ult_f=("fecha", "last")))
    g = g.merge(ult, on=["prod", "prov"], how="left")
    _um = s[~s["um"].astype(str).isin(("", "nan", "None"))]
    if len(_um):
        _llave = _um["prod"] + "\x1f" + _um["prov"]
        um = moda_por_grupo(_um.assign(_k=_llave), "_k", "um")
        g["um"] = (g["prod"] + "\x1f" + g["prov"]).map(um).fillna("")
    else:
        g["um"] = ""
    g = g.sort_values(["prod", "total"], ascending=[True, False],
                      kind="stable")
    g["pmin"] = g.groupby("prod")["ult_p"].transform("min")
    g["tope"] = g.groupby("prod")["total"].transform("max")
    out = {}
    for prod, filas in g.groupby("prod", sort=False):
        # Sólo arma TEXTO: los cálculos ya se hicieron arriba, sobre todas
        # las filas a la vez (y sin `_` al frente en las columnas:
        # `itertuples` las renombra). (`_pruebas_compras_sin_bucles_por_grupo` mira
        # que adentro de un bucle así no haya un sort, un filtro ni un
        # `mode()`.)
        html_filas = []
        for r in filas.itertuples(index=False):
            es_min = pd.notna(r.ult_p) and r.ult_p == r.pmin
            pu = "—" if pd.isna(r.ult_p) else f"S/ {r.ult_p:,.2f}"
            fec = "—" if pd.isna(r.ult_f) else pd.Timestamp(r.ult_f).strftime("%d/%m/%Y")
            peso = (r.total / r.tope * 100) if r.tope else 0.0
            cant = f"{r.cant:,.0f}" + (f" {_esc(r.um)}" if r.um else "")
            tot = (f"S/ {r.total/1000:.1f}k" if r.total >= 1000
                   else f"S/ {r.total:,.0f}")
            nom = _esc(nombre_propio(r.prov))
            html_filas.append(
                f'<details class="pb-row{" is-min" if es_min else ""}"><summary>'
                f'<span class="peso" style="width:{peso:.1f}%"></span>'
                f'<span class="sw" style="background:{color_map.get(r.prov, GRIS_BORDE)}"></span>'
                f'<span class="name" title="{nom}">{nom}</span>'
                f'<span class="pu{" pu-min" if es_min else ""}">{pu}</span>'
                f'<span class="fec">{fec}</span></summary>'
                f'<div class="mas"><span class="cell"><span class="lab">Cant.</span>'
                f'<span class="val">{cant}</span></span><span class="cell">'
                f'<span class="lab">Total</span><span class="val tot">{tot}</span>'
                f'</span></div></details>')
        out[prod] = (len(html_filas), "".join(html_filas))
    return out


_K_RELEVO_PROD = "cp_prov_prod_relevo"
"""El `st.text_input` oculto por el que un clic en un producto (HTML, sin
widget propio) llega a Python. Ver `_relevo_producto`."""

_SEP_RELEVO = "@@"
"""Separa el producto de un sello de tiempo en el valor del relevo: sin
él, clickear dos veces el MISMO producto escribiría el mismo texto y el
`on_change` no correría la segunda vez."""


def _relevo_producto():
    """`on_change` del relevo: el producto clickeado pasa a ser el foco de
    la Evolución, y clickear el que ya estaba en foco lo suelta.

    El patrón es el del riel de Días (`graficos/base.py::_aplicar_pan_riel`,
    regla #217): un `st.text_input` invisible que el JS llena y CONFIRMA con
    un Enter de teclado de verdad — `input`/`change` no alcanzan."""
    raw = st.session_state.get(_K_RELEVO_PROD) or ""
    prod = raw.rsplit(_SEP_RELEVO, 1)[0]
    if not prod:
        return
    actual = st.session_state.get("compras_prov_prodfocus")
    st.session_state["compras_prov_prodfocus"] = (None if prod == actual
                                                  else prod)


_JS_CLIC_PRODUCTO = f"""<script>
(function () {{
  // Un clic en una fila de producto (la de «Total del rango» o la de
  // «Por período») escribe su nombre en el relevo y lo confirma con un
  // Enter de verdad (regla #217). Escucha en el DOCUMENTO, delegado: la
  // tabla se rehace en cada corrida y un listener por fila se perdería.
  // Se reemplaza en cada inyección para no dejar uno colgado de un iframe
  // que ya no existe.
  var w = window.parent, doc = w.document;
  if (w.__cpProdClic) doc.removeEventListener('click', w.__cpProdClic, true);
  w.__cpProdClic = function (ev) {{
    var t = ev.target && ev.target.closest && ev.target.closest('[data-prod]');
    if (!t || !t.closest('.st-key-compras_prov_card_prods')) return;
    var relevo = doc.querySelector('.st-key-{_K_RELEVO_PROD} input');
    if (!relevo) return;
    var setter = w.Object.getOwnPropertyDescriptor(
      w.HTMLInputElement.prototype, 'value').set;
    relevo.focus({{preventScroll: true}});
    setter.call(relevo, t.getAttribute('data-prod') + '{_SEP_RELEVO}' + w.Date.now());
    relevo.dispatchEvent(new w.Event('input', {{bubbles: true}}));
    var o = {{key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
             bubbles: true, cancelable: true}};
    relevo.dispatchEvent(new w.KeyboardEvent('keydown', o));
    relevo.dispatchEvent(new w.KeyboardEvent('keyup', o));
  }};
  doc.addEventListener('click', w.__cpProdClic, true);
}})();
</script>"""


def _tarjeta_productos(base, prov, prod_foco, gran, src_per, per_orden,
                       evo_x, etq, d_full, cols, color_map, alto_ranking):
    """La tarjeta «Productos · <proveedor>», arriba a la derecha.

    Desde el 2026-10-01 (regla #579) es una tabla HTML con dos modos, en las
    pastillas de la cabecera:

    - **Total del rango**: los productos comprados al proveedor en el rango
      del Ranking, con su barra de valor, % del proveedor, cantidad y UM.
      Clic en un producto despliega DEBAJO de su fila sus proveedores —lo
      que hasta ese día era la tarjeta «Proveedores de», abajo a la
      derecha—: los del año en curso, y en un segundo desplegable, los de
      todo el histórico. Es un `<details>` nativo: abre al instante, sin
      rerun, y se pueden abrir varios a la vez.
    - **Por <granularidad de la Evolución>**: cómo varió cada producto, en
      los últimos (hasta cuatro) períodos que muestra la Evolución, con una
      tira de barritas de tendencia y la variación % del último contra el
      anterior.

    HTML y no AgGrid: el despliegue debajo de una fila en AgGrid Community
    pide filas de dos tipos y `postSortRows` (lo que hace Inventario,
    regla #466), y lo que se ganaba —ordenar por columna— no compensa una
    grilla más (1,28 MB, regla #540). La tabla viene ordenada por valor.

    `alto_ranking` es la grilla del Ranking de al lado: la lista scrollea
    DENTRO a partir de ahí, para que las dos tarjetas de arriba midan lo
    mismo con un producto desplegado o sin él.

    **Un clic en un producto lo pone además en la Evolución** (2026-10-01,
    a pedido: «cuando se haga clic en un producto, el gráfico de abajo
    muestre lo relacionado al producto»). Las filas son HTML, sin widget:
    el clic viaja por un `st.text_input` oculto (`_K_RELEVO_PROD`) que un
    script llena y confirma con Enter. `prod_foco` vuelve marcado —en
    «Total», con su despliegue ABIERTO, para que el rerun no lo cierre— y
    clickearlo de nuevo lo suelta.
    """
    (col_prov, col_prod, col_cant, col_valor, col_punit, col_um, col_fecha,
     col_docu) = cols
    _tit = ("Productos" if prov is None
            else f"Productos · {_compras_truncar(nombre_propio(prov), 24)}")
    _por = _GRAN_POR.get(gran, "Por período")
    # Lo que la lista puede crecer antes de scrollear: la grilla del
    # Ranking menos lo que esta tarjeta mide de más (la nota de 18px y la
    # cabecera de la tabla, que va fuera del scroll). Medido con Playwright
    # a 1358×800: con 30 las dos tarjetas de arriba miden 313px; con 20, la
    # de Productos pedía 323 y estiraba al Ranking.
    _alto_lista = max(120, alto_ranking - 30)
    with st.container(border=True, key="compras_prov_card_prods"):
        with _card("prov_prods", _tit, titulo_arriba=True):
            if st.session_state.get("cp_prov_prods_modo") not in (None, "tot",
                                                                  "per"):
                del st.session_state["cp_prov_prods_modo"]
            with st.container(key="cp_modo_prods"):
                _modo = st.pills(
                    "Ver productos", ["tot", "per"], default="tot",
                    format_func=lambda o: "Total del rango" if o == "tot" else _por,
                    key="cp_prov_prods_modo", label_visibility="collapsed",
                ) or "tot"
            if prov is None:
                return
            st.text_input("Producto en foco", key=_K_RELEVO_PROD,
                          label_visibility="collapsed",
                          on_change=_relevo_producto)
            if _modo == "per":
                # La medida de la matriz (2026-10-01, a pedido): sólo en
                # este modo, en el renglón de la nota, a la derecha. Es SUYA
                # y no la de la Evolución: acá cada fila es un producto, así
                # que Cantidad y Precio tienen sentido sin elegir ninguno.
                with st.container(key="cp_modo_medida"):
                    _medida = st.pills(
                        "Medida de los productos", list(_MEDIDAS),
                        default="valor", format_func=_MEDIDAS.get,
                        key="cp_prov_prods_medida",
                        label_visibility="collapsed") or "valor"
                _html = _html_productos_por_periodo(
                    prov, src_per, per_orden, evo_x, etq, gran, _alto_lista,
                    prod_foco, _medida)
            else:
                _html = _html_productos_total(
                    base, prov, d_full, cols, color_map, _alto_lista,
                    prod_foco)
            # REMONTAJE POR CONTENIDO (regla #377): un `<details>` guarda
            # abierto/cerrado en el DOM y ese nodo sobrevive al rerun. Con
            # la key atada al contenido, otro proveedor estrena los nodos y
            # todo abre cerrado; el mismo contenido conserva lo que abrió
            # el usuario.
            _k = zlib.crc32(_html.encode("utf-8"))
            with st.container(key=f"cp_pl_{_k:08x}"):
                st.markdown(_html, unsafe_allow_html=True)
    inyectar_html(_JS_CLIC_PRODUCTO)


def _html_productos_total(base, prov, d_full, cols, color_map, alto_lista,
                          prod_foco=None):
    """La tabla de productos «Total del rango», con el despliegue de sus
    proveedores debajo de cada fila. Ver `_tarjeta_productos`."""
    (col_prov, col_prod, col_cant, col_valor, col_punit, col_um, col_fecha,
     col_docu) = cols
    sub = base[base["prov"] == prov]
    agg = (sub.groupby("prod", as_index=False)
              .agg(valor=("valor", "sum"), cant=("cant", "sum"))
              .sort_values("valor", ascending=False, kind="stable"))
    if agg.empty:
        return '<div class="cp-modo-nota">Sin productos para este proveedor.</div>'
    _um_ok = sub[~sub["um"].astype(str).isin(("", "nan", "None"))]
    um = (moda_por_grupo(_um_ok, "prod", "um") if len(_um_ok)
          else pd.Series(dtype=object))
    prods = agg["prod"].tolist()
    # Las dos fuentes del despliegue: el año en curso y todo el histórico,
    # las dos sobre `d_full` (sin el filtro de fecha del Ranking), como la
    # tarjeta de antes. Se recorta a ESTOS productos antes de normalizar.
    if d_full is not None and col_prod and col_prod in d_full.columns:
        _df = d_full[d_full[col_prod].astype(str).isin(prods)]
        todo = base_normalizada(_df, col_prov, col_prod, col_cant, col_valor,
                                col_punit, col_um, col_fecha, col_docu)
    else:
        todo = base
    if col_fecha:
        ano = todo[pd.to_datetime(todo["fecha"]).dt.year
                   == pd.Timestamp.now().year]
    else:
        ano = todo
    prov_ano = _filas_proveedores(ano, prods, color_map)
    prov_todo = _filas_proveedores(todo, prods, color_map)
    tot = float(sub["valor"].sum()) or 1.0
    vmax = float(agg["valor"].max()) or 1.0
    filas = []
    for r in agg.itertuples(index=False):
        nom = _esc(r.prod)
        n_a, h_a = prov_ano.get(r.prod, (0, ""))
        n_t, h_t = prov_todo.get(r.prod, (0, ""))
        cuerpo = (f'<div class="cp-pl-sub">Año actual · {n_a} '
                  f'{"proveedor" if n_a == 1 else "proveedores"} · último precio</div>'
                  + (f'<div class="pb-cards">{h_a}</div>' if n_a
                     else '<div class="cp-pl-vacio">Sin compras este año.</div>')
                  + f'<details class="cp-pl-todo"><summary>Todo el histórico · '
                  f'{n_t} {"proveedor" if n_t == 1 else "proveedores"}</summary>'
                  f'<div class="pb-cards">{h_t}</div></details>')
        _foco = r.prod == prod_foco
        filas.append(
            f'<details class="cp-pl-row{" foco" if _foco else ""}"'
            f'{" open" if _foco else ""}><summary data-prod="{nom}">'
            f'<span class="nm" title="{nom}">{nom}</span>'
            f'<span class="vb"><span class="bar" style="width:{r.valor / vmax * 62:.1f}%"></span>'
            f'<span class="v">S/ {r.valor:,.0f}</span></span>'
            f'<span class="n">{r.valor / tot * 100:.0f}%</span>'
            f'<span class="n">{r.cant:,.0f}</span>'
            f'<span class="um">{_esc(um.get(r.prod, ""))}</span></summary>'
            f'<div class="cp-pl-provs">{cuerpo}</div></details>')
    return ('<div class="cp-modo-nota">El rango del Ranking · clic en un '
            'producto: sus proveedores</div>'
            '<div class="cp-pl"><div class="cp-pl-head"><span>Producto</span>'
            '<span class="r">Valor</span><span class="r">%</span>'
            '<span class="r">Cant.</span><span>UM</span><span></span></div>'
            f'<div class="cp-pl-lista" style="max-height:{alto_lista}px">'
            + "".join(filas) + '</div></div>')


def _html_productos_por_periodo(prov, src_per, per_orden, evo_x, etq, gran,
                                alto_lista, prod_foco=None, medida="valor"):
    """La tabla de productos «Por <granularidad>»: cada producto en los
    últimos (hasta cuatro) períodos de la Evolución, en la `medida` que se
    elija (Soles, Cantidad o Precio promedio del período). Ver
    `_tarjeta_productos`."""
    if src_per is None or not per_orden or "prod" not in src_per.columns:
        return ('<div class="cp-modo-nota">La Evolución no tiene períodos '
                'que mostrar.</div>')
    # Hasta CUATRO: con cinco, en una laptop, al nombre del producto le
    # quedaban ~85px («Producto dem…»). Son los últimos que muestra la
    # Evolución, y el anterior al primero se lee igual para la variación.
    vis = list(evo_x)[-4:] or list(per_orden)[-4:]
    _i0 = per_orden.index(vis[0]) if vis[0] in per_orden else 0
    ant = per_orden[_i0 - 1] if _i0 > 0 else None
    cols_p = ([ant] if ant is not None else []) + vis
    sp = src_per[(src_per["prov"] == prov) & src_per["per"].isin(cols_p)]
    # Soles Y cantidad siempre: el orden de las filas y qué productos entran
    # salen de lo pagado, sea cual sea la medida (una tabla que se reordena
    # al cambiar de Soles a Precio deja de leerse como la misma tabla).
    _v = (sp.groupby(["prod", "per"])["valor"].sum().unstack("per")
            .reindex(columns=cols_p).fillna(0.0))
    _c = (sp.groupby(["prod", "per"])["cant"].sum().unstack("per")
            .reindex(index=_v.index, columns=cols_p).fillna(0.0))
    _v = _v[_v[vis].sum(axis=1) > 0]
    if medida == "cant":
        m = _c.loc[_v.index]
    elif medida == "precio":
        # Precio PONDERADO del período (lo pagado / lo comprado); sin
        # cantidad no hay precio (NaN → «—»). Ver `_serie_medida`.
        m = _v / _c.loc[_v.index].where(_c.loc[_v.index] > 0)
    else:
        m = _v
    um = pd.Series(dtype=object)
    if medida != "valor" and "um" in sp.columns:
        _u = sp[~sp["um"].astype(str).isin(("", "nan", "None"))]
        if len(_u):
            um = moda_por_grupo(_u, "prod", "um")
    if m.empty:
        return ('<div class="cp-modo-nota">Sin compras a este proveedor en '
                'los períodos de la Evolución.</div>')
    m = m.loc[_v[vis].sum(axis=1).sort_values(ascending=False,
                                              kind="stable").index]
    n = len(vis)
    head = "".join(f'<span class="r">{_esc(etq(p))}</span>' for p in vis)
    filas = []
    for prod, fila in m.iterrows():
        # NaN (Precio sin cantidad) cuenta como cero para dibujar, y se
        # escribe «—».
        vals = [0.0 if pd.isna(fila[p]) else float(fila[p]) for p in vis]
        tope = max(vals) or 1.0
        # La tendencia: una barrita por período, escalada contra el mayor
        # de la fila. HTML y no SVG: lo que dibuja `st.markdown` está
        # probado con cajas y `<details>` (regla #377), no con SVG.
        barras = "".join(
            f'<i class="{"z" if not v else ""}" '
            f'style="height:{max(8, v / tope * 100):.0f}%"></i>' for v in vals)
        _dec = 2 if medida == "precio" else 0
        celdas = "".join(
            f'<span class="c{" z" if not v else ""}" style="--t:{v / tope * 28:.0f}%">'
            f'{f"{v:,.{_dec}f}" if v else "—"}</span>' for v in vals)
        # El último período contra el anterior: el de al lado si hay dos o
        # más en pantalla; si hay uno solo, el que quedó fuera del cuadro.
        if n > 1:
            prev = vals[-2]
        else:
            prev = float(fila[ant]) if ant is not None else None
        var = _var_pct(vals[-1], prev)
        _cls = ("" if not np.isfinite(var) or abs(var) < 0.5
                else (" sube" if var > 0 else " baja"))
        nom = _esc(prod)
        # En Cantidad y Precio, la unidad al lado del nombre: «112» no dice
        # nada sin saber si son kilos o unidades.
        _u = _esc(um.get(prod, "")) if medida != "valor" else ""
        filas.append(
            f'<div class="cp-pm-fila{" foco" if prod == prod_foco else ""}"'
            f' data-prod="{nom}">'
            f'<span class="nm" title="{nom}">{nom}'
            f'{f"<small>{_u}</small>" if _u else ""}</span>'
            f'<span class="sp">{barras}</span>{celdas}'
            f'<span class="var{_cls}">{_fmt_var(var)}</span></div>')
    _contra = _esc(etq(vis[-2])) if n > 1 else (_esc(etq(ant)) if ant else "")
    _que = {"valor": "Soles", "cant": "Cantidad",
            "precio": "Precio promedio (S/ por unidad)"}[medida]
    return (f'<div class="cp-modo-nota con-medida">{_que} por {_esc(gran.lower())} · '
            f'los períodos de la Evolución · Var. % contra {_contra or "el anterior"}</div>'
            # Las columnas las arma el CSS (`.cp-pm`, con cuántos períodos
            # hay en `--n`), porque una tarjeta angosta saca la de Tendencia
            # con una container query, y eso no se puede contra un estilo
            # inline.
            f'<div class="cp-pm" style="--n:{n}"><div class="cp-pm-head">'
            f'<span>Producto</span><span class="sp">Tendencia</span>{head}'
            f'<span class="r">Var. %</span></div>'
            f'<div class="cp-pl-lista" style="max-height:{alto_lista}px">'
            + "".join(filas) + '</div></div>')


@st.fragment
def _compras_proveedor_drill(d, col_prov, col_prod, col_cant, col_valor,
                             col_punit, col_um, col_fecha, col_docu=None,
                             d_full=None):
    """Dashboard de Proveedor.

    Tabla-ranking (arriba a la izq.): un proveedor por fila, ordenados por
    valor, con la barra de "Valor" pintada como FONDO de la celda (un
    `linear-gradient` cortado en el % del valor — ver el bloque del AgGrid).
    Clic en una fila la enfoca y filtra las demás tarjetas; clic en la MISMA
    fila quita el foco. Sin checkbox: el gesto es la fila entera.

    Panel A (arriba a la der.): los productos comprados al proveedor en foco.
    Abajo, de izquierda a derecha: sus documentos (fecha, número, valor), la
    evolución del proveedor y el Panel B, los proveedores del producto
    seleccionado en el Panel A.
    """
    # ── Escalada a rerun COMPLETO tras un atajo de fecha ───────────────────
    # Los atajos del Ranking (más abajo) escriben el rango con
    # `aplicar_atajo`, pero el FILTRO que consume ese rango vive en
    # `app.py:619`, FUERA de este fragment. Un clic acá solo re-ejecuta el
    # fragment, que recibe `d` YA filtrado por el último rerun completo:
    # sin escalar, el estado cambia y la pantalla no — botón que responde,
    # datos quietos. Mismo patrón y mismo motivo que
    # `graficos/compras/__init__.py:216`. Va ANTES de dibujar nada para no
    # gastar un render que se va a descartar. Ver arquitectura.md #180.
    # `preservar_widgets` porque el rerun aborta ACÁ: los controles de la
    # sección todavía no se registraron y Streamlit recolecta el estado de
    # todo widget de este fragment que no se dibujó (ver `_KEYS_WIDGET`).
    if st.session_state.pop("_cp_rank_atajo_pendiente", False):
        preservar_widgets(_KEYS_WIDGET)
        st.rerun(scope="app")
    if not (col_prov and col_valor):
        st.info("Faltan columnas (Proveedor, Valor) para este gráfico.")
        return

    # ── Controles ──────────────────────────────────────────────────────────
    # Calcular lista de proveedores ANTES de dibujar los controles
    _todos_provs_temp = (d.groupby(col_prov)[col_valor].sum()
                          .sort_values(ascending=False).index.tolist()
                          if col_prov and col_valor else [])
    # Agregar "Otros" al final si hay proveedores fuera del top
    _otros_mask_temp = ~d[col_prov].astype(str).isin(_todos_provs_temp[:20])
    if _otros_mask_temp.any():
        _todos_provs_temp = _todos_provs_temp + ["Otros"]
    _real_provs = [p for p in _todos_provs_temp if p != "Otros"]  # sin "Otros"
    # 2026-08-16, a pedido: por defecto se muestran TODOS los proveedores del
    # Nombres sobre las barras: TRUE por defecto (filtro principal para el
    # usuario). El seed corre una vez por sesión — bumping el key del flag
    # resetea sesiones antiguas que hayan quedado con False.
    if not st.session_state.get("_cp_show_names_seed_v2"):
        st.session_state["cp_prov_show_names"] = True
        st.session_state["_cp_show_names_seed_v2"] = True

    # La granularidad se lee aquí (de session_state), pero su selector se
    # DIBUJA flotando sobre su gráfico (más abajo).
    gran = st.session_state.get("compras_prov_gran") or "Mes"

    # El filtro de proveedores vive en `_comun.py::filtro_proveedores` desde
    # el 2026-09-02, al pedirse el MISMO control para el Ranking de Productos.
    # Devuelve sus dos mitades por separado porque se usan en momentos
    # distintos: la selección se lee ACÁ (arriba, para armar el figure y el
    # ranking) y el popover se dibuja MÁS ABAJO, dentro de la fila del título
    # de la tarjeta. Ese desfase es el patrón de UN rerun que ya usaba cuando
    # el popover flotaba, y no cambia por mudarse de sitio.
    #
    # El toggle "Nombres en barras" entra por `pie=`: es de ESTA vista (las
    # barras son suyas), no del filtro, y por eso no viajó al helper.
    prov_multisel, _pop_proveedores = filtro_proveedores(
        "cp_prov", _todos_provs_temp,
        pie=lambda: st.toggle(
            "Nombres en barras", key="cp_prov_show_names",
            help="Muestra el nombre del proveedor sobre cada barra. "
                 "Se abrevia segun el ancho disponible."))

    # ── Preparar base de datos ─────────────────────────────────────────────
    # Vive en `_comun.py` desde el 2026-09-09: la sección «Detalle de
    # documentos por proveedor» se separó de este drill y necesita el MISMO
    # df normalizado. Ver el bloque «LA BASE DEL DRILL DE PROVEEDOR» de allá.
    base = base_normalizada(d, col_prov, col_prod, col_cant, col_valor,
                            col_punit, col_um, col_fecha, col_docu)
    if base.empty or base["valor"].sum() == 0:
        # SIN FILAS SE VACÍA EL CONTENIDO, NO LA VISTA (2026-09-07). Este
        # `return` salía ANTES de la tarjeta — o sea, antes del selector de
        # fecha de su cabecera, que desde el 2026-09-06 es el único control
        # de rango que tiene la sección (la franja ya no dibuja calendario).
        # El cartel decía "ampliá el rango" y se llevaba puesto el widget
        # con el que se amplía. Es la regla #115 aplicada a la cabecera:
        # la tarjeta se dibuja SIEMPRE y lo que se decide adentro es el
        # contenido. Ver regla #354.
        #
        # El CSS se inyecta ACÁ y no sólo abajo por el mismo motivo:
        # `CSS_PROVEEDOR` estila los CUATRO prefijos `cp_*` (rank, prod,
        # sem, vol) y lo inyecta este drill, que es el primero de la pila.
        # Saliendo antes, los selectores de fecha de Semanal y Volatilidad
        # se dibujaban sin estilo en la pantalla vacía.
        st.markdown(CSS_PROVEEDOR, unsafe_allow_html=True)
        # Misma key de FAMILIA que la tarjeta real (`compras_prov_card_`,
        # el wildcard de `estilos/_80_cards.py`) para heredar fondo, radio
        # y padding; y el MISMO prefijo de widget (`cp_rank`), que acá no
        # choca porque la tarjeta real no se dibujó — así el rango elegido
        # desde este cartel sigue puesto cuando la vista vuelve con datos.
        with st.container(border=True, key="compras_prov_card_vacio"):
            selector_fecha_tarjeta(
                "cp_rank", "_cp_rank_atajo_pendiente",
                titulo_html='<div class="cp-rank-tit">Ranking de '
                            'proveedores</div>',
                categoria=CATEGORIA_SEC["compras_sec_proveedor"])
            # EL CARTEL COMPLETO DEL REPORTE VIVE ACÁ, no en un `st.info`
            # suelto arriba de la pila: ése no cabe (el jalón de -104px que
            # sube esta tarjeta bajo la franja se lo comería, ver el
            # comentario de la guarda en `__init__.py`). Y esta tarjeta es
            # la primera de la pila, así que decirlo acá es decirlo arriba.
            #
            # Nombra las DOS salidas —la fecha de esta cabecera y el filtro
            # de Familia— y avisa de lo que SÍ tiene datos más abajo: sin
            # esa última línea, el usuario lee "no hay nada" y no baja a
            # las dos vistas que abren sobre el histórico.
            st.info("Sin compras en el rango seleccionado. Ampliá el rango "
                    "desde la fecha de la cabecera, o soltá el filtro de "
                    "Familia. «Vs año pasado» y «Volatilidad», más abajo, "
                    "tienen ventana propia y siguen mostrando datos.")
        return

    # ── Calcular periodo ──────────────────────────────────────────────────
    # `agregar_periodo` vive en `_comun.py` (misma mudanza que `base`, y por
    # el mismo motivo). Acá queda como closure sobre `gran` porque este drill
    # se lo aplica DOS veces —a `base` y al histórico completo que alimenta
    # la evolución— y la granularidad es la misma en las dos.
    def _agregar_periodo(_df):
        return agregar_periodo(_df, gran)

    base = _agregar_periodo(base)

    # Proveedores a dibujar (gobiernan la paleta, el filtro y el cuadro de
    # control de la izquierda).
    _tot_all  = base["valor"].sum() or 1.0
    top_provs = [p for p in prov_multisel if p in set(base["prov"].unique())]
    if not top_provs:
        # 2026-08-16: sin seleccion propia se muestran TODOS los del rango de
        # fechas (a pedido), no los 5 mas grandes. Ordenados por valor para
        # que la paleta siga asignando los colores mas fuertes a los que mas
        # pesan, igual que antes. Con "todos" ya no hay resto: la serie gris
        # "Otros" desaparece sola, porque _otros_mask queda vacia.
        top_provs = (base.groupby("prov")["valor"].sum()
                         .sort_values(ascending=False).index.tolist())

    # Asignar color por proveedor (los que no están en top → "Otros" en gris)
    base["prov_label"] = base["prov"].where(base["prov"].isin(top_provs), "Otros")

    periodos = periodos_ordenados(base)

    # ── Estado de foco ────────────────────────────────────────────────────
    # (Hasta el 2026-10-01 había además un foco de PRODUCTO,
    # `compras_prov_prodfocus`, que leía la tarjeta «Proveedores de». Esa
    # tarjeta se fue: los proveedores de cada producto se despliegan debajo
    # de su fila sin pasar por el servidor, regla #579.)
    prov_focus = st.session_state.get("compras_prov_focus")
    if prov_focus not in set(base["prov"].unique()):
        prov_focus = None

    orden_provs = top_provs  # de mayor a menor valor total

    # ── Ventana de periodos (paginacion server-side) ──────────────────────
    # En vez de zoom client-side (rangeslider), la cantidad de agrupaciones
    # visibles se decide en Python y el desplazamiento vive en session_state.
    # Ventaja clave: clicar una barra dispara un rerun, pero la ventana NO se
    # pierde (el zoom del rangeslider si se perdia, porque era estado del
    # navegador y Streamlit remonta el componente en cada rerun).
    #
    # El tamano por defecto se adapta a la cantidad de series para que el
    # ancho de barra siga siendo legible: mas proveedores -> menos
    # agrupaciones a la vez. (~1200px de plot / 16px minimos por barra) /
    # n_series, acotado a 4..12. El usuario puede fijarlo a mano desde el
    # popover de navegacion (cp_prov_win_size; None = automatico).
    _otros_mask = ~base["prov"].isin(top_provs)
    _hay_otros = _otros_mask.any()
    _otros_seleccionado = "Otros" in prov_multisel
    _n_series = len(orden_provs) + (1 if (_hay_otros and _otros_seleccionado) else 0)
    _n_per = len(periodos)
    _ventana_auto = max(4, min(12, int(1200 / (16 * max(1, _n_series)))))
    # Opciones de la ventana. La lista es DINÁMICA (depende de cuántos
    # períodos haya), y desde 2026-08-23 la consume un `st.selectbox`: si el
    # valor guardado no está entre ellas, Streamlit revienta al construir el
    # widget. Con los botones de antes no pasaba —escribían cualquier int y
    # `_ventana` lo clampeaba— así que el clamp tiene que subir de nivel:
    # ahora se corrige el ESTADO, no sólo el número derivado. Va acá, lejos
    # del widget pero antes que él, que es lo único que importa (CLAUDE.md,
    # "el clamp de bounds va justo antes del widget").
    _ops_win = ([None] + [o for o in (1, 2, 3, 6, 12, 24) if o < _n_per]
                + [_n_per])
    if st.session_state.get("cp_prov_win_size") not in _ops_win:
        st.session_state["cp_prov_win_size"] = None
    _win_size_sel = st.session_state.get("cp_prov_win_size")   # None = auto
    _ventana = (_ventana_auto if _win_size_sel is None
                else min(int(_win_size_sel), _n_per))
    _ventana = max(1, min(_ventana, _n_per))
    _ini_max = max(0, _n_per - _ventana)
    # Al cambiar granularidad / rango / densidad, reanclar al tramo mas
    # reciente (lo habitual en series de tiempo: interesa lo ultimo).
    _win_sig = f"{gran}|{_n_per}|{_ventana}"
    if st.session_state.get("cp_prov_win_sig") != _win_sig:
        st.session_state["cp_prov_win_sig"] = _win_sig
        st.session_state["cp_prov_win_ini"] = _ini_max
    # Clamp de bounds justo antes de usarlo (el rango pudo cambiar de tamano).
    _win_ini = min(max(0, st.session_state.get("cp_prov_win_ini", _ini_max)),
                   _ini_max)
    st.session_state["cp_prov_win_ini"] = _win_ini
    _per_vis = periodos[_win_ini:_win_ini + _ventana]
    _sl = slice(_win_ini, _win_ini + _ventana)

    # Total por proveedor sobre TODO el rango (el ranking no mira períodos).
    _tot_por_prov = (base[base["prov"].isin(orden_provs)]
                     .groupby("prov")["valor"].sum()
                     .reindex(orden_provs, fill_value=0))
    _rk_nombres = list(_tot_por_prov.index)
    _rk_valores = [float(v) for v in _tot_por_prov.values]
    _rk_colores = [PALETA_CALLAI[i % len(PALETA_CALLAI)]
                   for i in range(len(_rk_nombres))]
    if _hay_otros and _otros_seleccionado:
        _rk_nombres.append("Otros")
        _rk_valores.append(float(base[_otros_mask]["valor"].sum()))
        _rk_colores.append(GRIS_BORDE)
    # Orden: DESCENDENTE (mayor primero) — `orden_provs` ya viene así, y es
    # el orden natural de una TABLA (a diferencia del ranking en Plotly que
    # había antes, que necesitaba la lista al revés por cómo dibuja barras
    # horizontales de abajo hacia arriba; con la tabla eso ya no aplica).

    # ── El foco del ranking ───────────────────────────────────────────────
    # 2026-08-19: el ranking pasó de `st.dataframe` a AgGrid, y con eso
    # cambió DE DÓNDE sale el clic. Antes había que leer
    # `session_state[key]` ANTES de dibujar la tabla (la selección de un
    # st.dataframe queda ahí de la interacción previa) y llevar un dedup con
    # `compras_prov_last_click` para no reprocesar el mismo clic en cada
    # rerun. AgGrid DEVUELVE su selección en la llamada, así que el foco se
    # resuelve justo después de dibujar el grid, más abajo — y el dedup
    # desaparece: la selección ES el estado, no un evento que se repite.
    # Key NUEVA al cambiar de widget: la vieja ("compras_prov_rank_tab")
    # quedó en session_state con la forma del `st.dataframe` (un dict con
    # {"selection": {"rows": [...]}}), y una sesión abierta que la reusara le
    # pasaría ese valor al componente nuevo, que espera otra cosa.
    _rank_tab_key = "compras_prov_rank_grid"

    # ── Tabla-ranking: datos que consume ────────────────────────────────
    # 2026-08-17, a pedido: el ranking se UNE con la tabla resumen — eran
    # dos vistas de los mismos números (barra horizontal vs. fila de tabla)
    # una al lado de la otra. Pasa a ser una sola tabla (`st.dataframe`,
    # más abajo) con una `ProgressColumn` haciendo de barra — conserva la
    # lectura de ranking sin duplicar la información. El eje de tiempo no
    # se pierde: vive en el gráfico de evolución de al lado, que muestra el
    # proveedor elegido.
    #
    # Nivel 2 del mockup (heredado de la versión en barras): monto y % del
    # total del rango. OJO con el %: es sobre el total del RANGO, no del
    # período — con eje de tiempo "12%" podía leerse como "12% de ese mes";
    # acá es "12% de todo lo comprado en el rango".
    _rk_pct = [v / _tot_all * 100 for v in _rk_valores]
    if "docu" in base.columns and (base["docu"].astype(str) != "").any():
        _docs_prov = base.groupby("prov")["docu"].nunique()
    else:
        _docs_prov = None
    _rk_docs = [int(_docs_prov.get(p, 0)) if _docs_prov is not None else 0
                for p in _rk_nombres]

    # ── Acá vivió `_ALTO_FRAME` ──────────────────────────────────────────
    # Un frame de "8 filas de 35px" (325px) que servía a la vez a la figura
    # de Evolución, a la tabla de Panel A y al clamp de la lista de Panel B.
    # Se fue el 2026-09-02, después de que sus tres consumidores se
    # independizaran, cada uno por un pedido distinto:
    #   · Evolución  → mide contra la tarjeta del Ranking (`_ALTO_EVO`).
    #   · Panel A    → mide sus propias filas (`_ALTO_PRODS`, más abajo).
    #   · Panel B    → se clampea contra Panel A, que ahora es un número que
    #                  depende de los datos; por eso `publicar_var_px` se
    #                  mudó al lado del cálculo, dentro del panel.
    # No era un frame compartido por diseño: era el único que había.
    # Filas del RANKING, más delgadas a pedido — 28px el 2026-08-24, 24px el
    # 2026-08-28 ("las filas un poco más delgadas", junto con el blanco y el
    # cuerpo más chico de `CSS_RANKING_GRID`).
    #
    # Desde el 2026-09-02 este número —y el `_ALTO_HEADER_RANK` de abajo— NO
    # son sólo del Ranking: la tabla de productos de Panel A los consume
    # también, a pedido ("del mismo tamaño y delgadez que el de ranking de
    # proveedores"). Se dejan con el nombre `_RANK` a propósito, porque esa
    # ES la relación: Panel A no eligió 24, eligió SEGUIR al Ranking. Si
    # mañana el Ranking cambia, Panel A cambia con él — que es lo pedido.
    #
    # OJO — hasta el 2026-08-28 esto era "el mismo número que
    # graficos/compras/producto.py::_ALTO_FILA" (28). Ya NO: el pedido fue
    # sobre ESTA tabla. Los dos rankings viven apilados en la misma página,
    # así que si algún día se unifican, es 24 + `CSS_RANKING_GRID` lo que
    # tiene que viajar para allá, no 28 lo que vuelve para acá.
    #
    # 2026-09-11: los dos números se mudaron a `_comun.py`. El drill de
    # Producto pidió sus tres paneles "similares al de Ranking de
    # Proveedores", así que ese día dejaron de describir ESTA tabla y
    # pasaron a describir a todas — que es lo que el párrafo de arriba
    # venía anticipando. Acá quedan los alias locales: los consumen ocho
    # líneas de este archivo y renombrarlas no aportaba nada. El 2026-09-12
    # el Ranking de productos también se sumó (el 28 de allá se fue): hoy
    # los dos rankings apilados de Compras dibujan a 24 (regla #381).
    _ALTO_FILA_RANK = ALTO_FILA_RANK
    _ALTO_HEADER_RANK = ALTO_HEADER_RANK
    # `extra` es TODO lo que el grid mide y no son las filas de datos:
    #   · el alto fijo del propio grid: la cabecera + su borde inferior de
    #     1px + ~5.5px de chrome del tema. Medido en el DOM, no a ojo.
    #   · +_ALTO_FILA_RANK: `pinnedBottomRowData` (la fila TOTAL, más abajo)
    #     reserva su espacio DENTRO del `height=` del grid, así que sin este
    #     sumando la fila total le comería una fila a las de datos.
    #   · +alturas.FRANJA_ATAJOS: unas líneas más abajo, `_ALTO_RANK` le
    #     resta esa misma cantidad al grid para hacerle lugar a la fila de
    #     atajos que se dibuja ARRIBA — y esa resta ya corría antes de que
    #     existiera la fila total. Sin pre-compensarla acá, la resta se
    #     comería las filas de datos por partida doble.
    # Verificado midiendo el grid entero: root 297 = cabecera 39 +
    # body-viewport 225 + fila TOTAL 28 + 5 de chrome, con los números
    # viejos. Con los nuevos: 33 + 192 + 24 + 5 = 254.
    _CROMO_GRID_RANK = CROMO_GRID_RANK
    # Cuántas filas RESERVA el grid. 8 es el TECHO, no el alto: hasta el
    # 2026-09-01 era un 8 fijo y el grid medía lo mismo con 2 proveedores
    # que con 20 — reportado con captura ("la tabla es muy larga hacia
    # abajo, hay espacio vacío"). Medido en el navegador con 2 proveedores:
    # `.ag-body-viewport` 196px contra 48px de filas, o sea 148px de hueco
    # BLANCO entre la última fila y la fila TOTAL, que hace leer la tabla
    # como rota (la fila de cierre despegada de sus datos).
    #
    # El techo se queda en 8 y no sube a las ~10 que hoy entrarían en la
    # tarjeta: el alto de la fila lo manda la Evolución de al lado (el
    # `:has()` de _80_cards.py), así que subirlo sólo cambia dónde empieza
    # el scroll interno, y 8 es el número con el que se dimensionó el resto
    # de la vista.
    #
    # El piso de 1 es por el caso vacío: `max(1, ...)` deja la cabecera y la
    # fila TOTAL con una fila de aire en vez de un grid de 0 filas, que AG
    # Grid dibuja recortando su propio overlay de "sin datos".
    # 2026-10-01: el techo baja de 8 a 7, a pedido («reduzcamos 1 fila a
    # cada una, y que suba un poco las tarjetas de abajo»). La lista de
    # Productos de al lado mide contra esta grilla, así que pierde la suya
    # sola. Regla #579.
    _FILAS_RANK = min(7, max(1, len(_rk_nombres)))
    _ALTO_FRAME_RANK = alturas.por_filas(
        _FILAS_RANK, px_fila=_ALTO_FILA_RANK,
        extra=_CROMO_GRID_RANK + _ALTO_FILA_RANK + alturas.FRANJA_ATAJOS,
        minimo=0)
    # La fila de atajos le come FRANJA_ATAJOS al AgGrid: se dibuja ARRIBA,
    # dentro de la misma tarjeta, y hasta que existió nadie le hacía lugar.
    # Se resuelve ACÁ y no junto al grid (que es donde vivía) porque desde
    # el 2026-09-01 este número es también el que dimensiona la figura de
    # Evolución — ver `_ALTO_EVO`, unas líneas más abajo.
    _ALTO_RANK = _ALTO_FRAME_RANK - alturas.FRANJA_ATAJOS
    # ── HISTORIA (hasta el 2026-09-01) ────────────────────────────────
    # La evolución comparte su columna con el selector de período Y con el
    # cromo de su propia tarjeta (2026-08-18: son dos bloques, no uno), así
    # que su figura mide eso menos que la tabla de al lado. La tabla no paga
    # el cromo: su columna tenía 119px de aire medidos, y hasta esta fecha
    # la evolución era la que MANDABA el alto de la fila — hoy es al revés,
    # ver el bloque de abajo.
    # 2026-08-23: se le suman dos filas más — `gran_float` y
    # `win_nav` se mudaron DENTRO de esta tarjeta (antes flotaban afuera, sin
    # costarle alto a nadie). Sin restarlas, la tarjeta de Evolución crecía
    # 66px y la de Ranking se estiraba igual para empatarla (regla de
    # _80_cards.py "dos tarjetas de la misma fila miden lo mismo") —
    # verificado en vivo: las dos daban 473px de alto en vez de la fila
    # "natural" de Ranking, dejando aire de más al fondo.
    # Más tarde el mismo día, en dos vueltas: primero la granularidad y
    # después la navegación de ventana dejaron de tener fila propia — las
    # tres viven en un solo renglón (`cp_evo_ctrl`, abajo). De las tres
    # constantes que hubo (FRANJA_PILLS, FRANJA_GRAN, FRANJA_WIN_NAV) queda
    # una, `FRANJA_CTRL_EVO`, y los ~66px de las dos filas que desaparecieron
    # volvieron a la figura.
    #
    # 2026-09-01, a pedido ("la tarjeta del gráfico de evolución que está al
    # costado, también que sea del mismo tamaño"). La figura DEJA de medirse
    # contra `_ALTO_FRAME` (8 filas de 35px, un número que no mira los datos)
    # y pasa a medirse contra la tarjeta DE AL LADO: el Ranking, que desde
    # que mide sus propias filas (`_FILAS_RANK`) es quien manda el alto de la
    # fila. Sin esto la Evolución seguía pidiendo 383px mientras el Ranking
    # pedía 313 con 7 proveedores, y la fila salía en escalón.
    #
    # Las dos constantes son el CROMO de cada tarjeta: todo lo que mide y no
    # es la figura ni el grid. MEDIDAS en el navegador el 2026-09-01, no
    # deducidas — el título de la Evolución ocupa 12px de flujo y 28 de caja
    # (el `margin-bottom: -16px` de `st.markdown` con HTML de bloque, regla
    # #162), que es justo la clase de detalle que una cuenta de servilleta
    # no acierta:
    #   Ranking:   padding 32 + fila del título 26 + gap 16 + 8 del wrapper
    #              del componente = 82
    #   Evolución: padding 32 + cabecera 30 + gap 16 = 78
    # Con eso, `tarjeta_ranking = 82 + _ALTO_RANK` y
    # `tarjeta_evo = 78 + _ALTO_EVO`: igualarlas es la resta de abajo, y el
    # `:has()` de _80_cards.py ya no tiene nada que estirar.
    #
    # 2026-09-09: la Evolución baja de 106 a 78. El título y los controles
    # eran DOS filas (28 + 30) y pasaron a ser una sola —«Evolución» a la
    # izquierda, los tres desplegables y las flechas a la derecha, ver
    # `cp_evo_cab`—, así que los 28px de la fila que desapareció vuelven a
    # la figura. Medido en el navegador con el cambio puesto: la tarjeta
    # llegaba a 309px de contenido natural contra los 337 del Ranking, y la
    # diferencia se la comía el piso del `:has()` en forma de blanco al pie.
    _CROMO_CARD_RANK = 82
    _CROMO_CARD_EVO = 78
    # Piso de la figura, y NO es `alturas.MINI` (240) ni un número elegido a
    # ojo: es el alto de la PILA DE KPIs que comparte fila con ella (Total
    # compra / % del total / Cantidad / Documentos, más su caption). MEDIDO
    # en el navegador el 2026-09-01: 200px, y es estable porque son cuatro
    # celdas fijas.
    #
    # Por qué ése y no otro: la figura y los KPIs son las dos columnas de un
    # `stHorizontalBlock`, así que la fila mide `max(figura, KPIs)`. Bajar la
    # figura de 200 NO achica la tarjeta —la sostienen los KPIs— y sólo
    # abre blanco al lado de ellos. Con `alturas.MINI` (240) pasaría lo
    # contrario: la tarjeta pediría 346 contra los 313-337 que pide el
    # Ranking con los 7-8 proveedores del caso real, y el piso de
    # _80_cards.py volvería a estirar al Ranking, devolviéndole el blanco
    # que se le acaba de sacar.
    #
    # Consecuencia práctica, con el tope de 8 filas del ranking: de 7
    # proveedores para arriba las dos tarjetas miden EXACTAMENTE lo mismo;
    # de 6 para abajo la fila se apoya en los KPIs (tarjeta de 306px) y el
    # Ranking se estira hasta ahí. Para bajar de 306 habría que achicar la
    # pila de KPIs, que es otro pedido.
    _MIN_EVO = 200
    # ── La fila de ABAJO mide SEIS filas (2026-10-01, a pedido: «que las
    # tarjetas de abajo sólo sean de 6 filas, para que se pueda ver toda la
    # vista en una pantalla de laptop»). Regla #579.
    #
    # Manda la tabla de Documentos: seis filas de `_ALTO_FILA_DOCS` (la
    # lista que scrollea, `_ALTO_LISTA_DOCS`) más su cabecera y su total.
    # Desde que la tabla es HTML (se despliega, regla #579) las filas son de
    # 26px. La Evolución se mide contra esa tarjeta con la resta de cromos
    # de siempre; con seis filas la cuenta da por debajo de `_MIN_EVO`, así
    # que en la práctica la figura queda en su piso (el de la pila de KPIs)
    # y la tarjeta de Documentos se estira lo que falte (el piso de
    # `_80_cards.py`).
    _FILAS_ABAJO = 6
    _ALTO_FILA_DOCS = 26
    _ALTO_LISTA_DOCS = _FILAS_ABAJO * _ALTO_FILA_DOCS
    # Cabecera de la tabla (28) + total (24): lo que la tarjeta mide además
    # de la lista y de su cromo de tarjeta (`_CROMO_CARD_DOCS`).
    _ALTO_DOCS = _ALTO_LISTA_DOCS + 28 + 24
    _CROMO_CARD_DOCS = 64
    _ALTO_EVO = max(_MIN_EVO,
                    _ALTO_DOCS + _CROMO_CARD_DOCS - _CROMO_CARD_EVO)
    # Ancho de la figura de evolución, MEDIDO en el navegador (viewport 1912,
    # rails desplegados). No sale de una cuenta porque su columna cuelga de
    # dos repartos anidados —COLUMNAS_DRILL_ABAJO (hasta el 2026-10-01,
    # COLUMNAS_DRILL; reglas #578 y #579) y el [2.6, 1] de acá abajo— sobre
    # un ancho que Python no conoce. Lo consume `paso_etiquetas` para decidir
    # cuántas etiquetas entran en el eje X; es el número que quedó obsoleto
    # (era ~380 cuando la figura ocupaba la columna entera) y nadie revisó al
    # partirla. Si se cambia el reparto de columnas, volver a medir: con
    # ?debug=1 → Rayos X, o auditarGraficos() desde la misma barra.
    # 2026-10-01: de 206 a 400. La Evolución pasó a la fila de abajo y a la
    # mitad del ancho (la simetría con la fila de arriba, regla #579);
    # medido con Playwright, la figura mide 404px a 1358 de ventana y 604 a
    # 1912. Va el de la laptop: con el más angosto, las etiquetas entran
    # también en el más ancho.
    _ANCHO_EVO = 400

    # ── Selector de granularidad FLOTANTE sobre el gráfico ────────────────
    # El contenedor "compras_prov_marco" es posición relativa; dentro, las
    # pills se posicionan en absoluto arriba-derecha, superpuestas al gráfico.
    st.markdown(CSS_PROVEEDOR, unsafe_allow_html=True)

    # El titulo fantasma "Proveedor" se retiro el 2026-08-25: decia el
    # nombre de la VISTA, que ya lo dice la pestana activa de la franja, y
    # desde que esa franja bajo a la fila 2 quedaban uno encima del otro
    # ("PrProveedoroveedor"). La esquina que ocupaba la usa ahora el titulo
    # de app + reporte que dibuja `navegacion.py`.

    # `_rank_tab_key` es ESTABLE (no depende del foco): el clic se procesa
    # arriba, antes de construir la tabla, así el rerun que abre el drill ya
    # sale con el foco correcto (sin doble rerun = sin parpadeo).
    # 2026-08-18: este contenedor DEJÓ de ser una tarjeta. Antes era el
    # bloque blanco que envolvía tabla + gráfico; ahora cada columna tiene el
    # suyo y éste queda solo como MARCO: el `position: relative` contra el que
    # flotan los tres controles (popover de proveedores, granularidad, flechas
    # de ventana), que siguen sirviendo a las dos columnas.
    #
    # Por eso también cambió de nombre. La key vieja empezaba con
    # `compras_prov_card_`, que es un wildcard por familia en
    # estilos/_80_cards.py: mientras la llevara, seguía pintándose de blanco
    # con padding y sombra ENCIMA de las dos tarjetas nuevas (bloque blanco
    # dentro de bloque blanco). Sacarlo de la familia es lo que lo vuelve
    # invisible, sin pelearle a la regla con overrides.
    # (Acá vivió `_pop_proveedores`, ~110 líneas de popover inline. Se fue
    # el 2026-09-02 a `_comun.py::filtro_proveedores`, al pedirse el mismo
    # control para el Ranking de Productos: copiarlo hubiera dejado dos
    # sitios donde arreglar el próximo detalle. Se instancia arriba, junto
    # con la selección que hay que leer temprano.)

    with st.container(key="compras_prov_marco"):
        # 2026-08-23: la pill Día/Semana/Mes/Año (key `gran_float`) se movió
        # DENTRO de la tarjeta de Evolución, a pedido — ver ese bloque más
        # abajo (justo debajo de `cp_evo_periodo`). Se queda el nombre de
        # la key aunque ya no flote (mismo criterio que `--rail-der-*`
        # después de que el rail cambió de lado: renombrar 15 sitios en 4
        # ficheros por una etiqueta no paga el riesgo).

        # El scroll horizontal y el ancho mínimo por barra que vivían acá se
        # fueron con las barras verticales: existían porque muchas series en
        # pocos períodos se apretaban a lo ancho. El ranking horizontal no
        # tiene ese problema.
        # (Acá vivió una animación de @keyframes para el alto del chart al
        # cambiar el filtro de proveedores — se sacó 2026-08-17: con el
        # frame fijo de 8 filas de arriba, el bloque ya no cambia de alto
        # entre reruns, así que no queda nada que animar.)

        # ── Las DOS filas, creadas antes de llenar ninguna ─────────────
        # 2026-10-01, a pedido (reglas #578 y #579): arriba el Ranking y
        # los Productos del proveedor en foco; abajo sus Documentos y la
        # Evolución. Los Proveedores de un producto ya no son una tarjeta:
        # se despliegan debajo del producto, en la tabla de arriba. Hasta
        # ese día eran [Ranking | Evolución] arriba y [Productos |
        # Proveedores de] abajo.
        #
        # Las cuatro columnas nacen ACÁ y se llenan después, cada una
        # cuando su dato está listo: en Streamlit el orden de ejecución es
        # el orden en que se leen los valores, y no coincide con el de la
        # pantalla — el Ranking fija el foco que leen las otras tres, y los
        # Documentos y los Productos se agrupan con los períodos de la
        # Evolución, así que se dibujan DESPUÉS de ella aunque los
        # Documentos vayan a su izquierda. Con un `with` sobre la columna,
        # lo que se dibuja tarde cae igual en su sitio.
        #
        # Las keys de las filas se quedaron: `cp_chart_wrap` y
        # `paneles_row` cuelgan CSS en `_css_proveedor.py` (el piso de
        # 300px por columna, el margen entre las filas) que sigue valiendo
        # para la fila nueva.
        _fila_arriba = st.container(key="cp_chart_wrap")
        _fila_abajo = st.container(key="paneles_row")
        with _fila_arriba:
            _c_tabla, _c_prods = st.columns(COLUMNAS_DRILL_TABLAS,
                                            gap=GAP_DRILL)
        with _fila_abajo:
            _c_docs, _c_evo = st.columns(COLUMNAS_DRILL_ABAJO,
                                         gap=GAP_DRILL)
        with _fila_arriba:
            # ── Ranking (arriba a la izq.) ──────────────────────────────
            # 2026-08-16: el cuadro de control de proveedores DESAPARECE.
            # Listaba color + nombre + monto + %, y con el ranking horizontal
            # los nombres pasaron a ser el eje: tenerlos también en una
            # columna aparte era mostrar lo mismo dos veces, a media pantalla
            # de distancia.
            # A su lado, la EVOLUCIÓN del proveedor elegido: es donde vive
            # el eje de tiempo que el ranking no tiene.
            # 2026-08-17, a pedido: el ranking (barras) y la tabla resumen
            # —antes dos columnas separadas mostrando los mismos números—
            # se UNEN acá en una sola tabla con `ProgressColumn` haciendo de
            # barra. Muestra hasta 8 filas (`_ALTO_FRAME_RANK`, que desde
            # el 2026-09-01 sigue a los datos) y scrollea el resto por
            # dentro.
            with _c_tabla:
                # ── BLOQUE 1: el ranking ─────────────────────────
                # 2026-08-18, a pedido: lo que era UNA tarjeta con la
                # tabla y el gráfico adentro pasa a ser DOS bloques
                # separados por el gris del app. El prefijo de la key
                # (`compras_prov_card_`) no es decorativo: es lo que les
                # da el fondo blanco, el radio y el clamp a una pantalla
                # con scroll interno (estilos/_80_cards.py, regla por
                # FAMILIA de key). Renombrarlas fuera de ese prefijo las
                # deja sin marco.
                with st.container(border=True,
                                  key="compras_prov_card_ranking"):
                    # 2026-08-23, segunda vuelta: el `help=` de st.markdown
                    # (primer intento) es hover-only — el usuario esperaba
                    # que abriera con CLIC, como un popover. `st.popover`
                    # con el label como shortcode de ícono (sin texto) es
                    # un botón de solo-ícono, sin nada más en el `with`.
                    #
                    # 2026-08-25, 4ta vuelta: el ícono se MUDA a la fila de
                    # atajos (más abajo, `cp_rank_fila`) — dos
                    # razones, verificadas en el DOM, no a ojo:
                    #
                    #   1. Colisión real. Vivía en su propia columna angosta
                    #      (`st.columns([16, 1])`), pero ese "1" es una
                    #      FRACCIÓN del ancho de la fila entera y por eso
                    #      queda pegado al borde DERECHO de la tarjeta —no
                    #      al título, como decía este comentario antes—. La
                    #      fila de atajos (`position: absolute; right:
                    #      18px`) ancla al MISMO borde. Con la escala de
                    #      tiempo agregada ese mismo día, su desplegable
                    #      terminaba justo debajo: medido, el chevron del
                    #      selectbox (864-877px) se comía 8px del chevron de
                    #      este popover (869-885px) — "veo doble pestillo
                    #      hacia abajo" fue el reporte que lo destapó.
                    #   2. Un solo flex row en vez de dos anclas
                    #      independientes adivinando no pisarse. Correr la
                    #      fila de atajos con un `right` a mano (a ojo,
                    #      "+30px") hubiera sido FRÁGIL: el ancho de esa
                    #      columna es PROPORCIONAL al ancho de la tarjeta,
                    #      así que en una tarjeta más ancha el número
                    #      cambia y el choque vuelve. En el MISMO
                    #      contenedor flex, el `gap: 6px` que ya existe los
                    #      separa siempre, sea cual sea el ancho.
                    #
                    # Va PRIMERO en esa fila (antes del ícono de escala) a
                    # propósito: la fila crece hacia la IZQUIERDA desde su
                    # ancla derecha, así que lo primero en el `with` termina
                    # más cerca del título — "pegado", que era la intención
                    # original y ahora sí se cumple.
                    # El título ya NO se dibuja acá: se lo pasa al
                    # selector, que lo mete dentro de su propia fila para
                    # que compartan renglón (2026-09-01, a pedido, desde un
                    # arrastre del modo diseño que lo subía al costado del
                    # título). Antes eran dos renglones: título de ancho
                    # completo arriba, control debajo. Medido: la grilla
                    # sube de y=315 a y=285, o sea 30px que gana la tabla.
                    # 2026-08-23 → 08-26, cuatro vueltas de pedido: el
                    # selector de fecha de esta tarjeta. Vive en
                    # `_comun.py::selector_fecha_tarjeta` desde que se pidió
                    # "el mismo selector" para el Ranking de Productos —
                    # copiarlo hubiera sido duplicar ~190 líneas y, peor,
                    # dos sitios donde arreglar el próximo detalle.
                    #
                    # No es un filtro paralelo: escribe la MISMA clave
                    # canónica del rango que la píldora de la franja. La
                    # bandera hace que el fragment escale a
                    # `st.rerun(scope="app")`, porque el filtro que lee ese
                    # rango vive en app.py, fuera de este fragment.
                    _ctx_fecha = selector_fecha_tarjeta(
                        "cp_rank", "_cp_rank_atajo_pendiente",
                        titulo_html='<div class="cp-rank-tit">Ranking de '
                                    'proveedores</div>',
                        extra=_pop_proveedores,
                        categoria=CATEGORIA_SEC["compras_sec_proveedor"])
                    # `_ALTO_RANK` (la resta de FRANJA_ATAJOS) se calcula
                    # arriba, con `_ALTO_FRAME_RANK`: la figura de Evolución
                    # lo necesita antes de llegar acá. La fila de atajos
                    # SIEMPRE se dibuja desde el 2026-08-25 (por el ícono de
                    # ayuda que se mudó a ella), así que el hueco se reserva
                    # siempre, no sólo cuando además hay atajos relativos.
                    # ── El ranking es un AgGrid, no un `st.dataframe` ──────
                    # 2026-08-19, a pedido: los checkbox de selección se van y
                    # el gesto pasa a ser "clic en la fila". No era posible con
                    # `st.dataframe`: su columna de selección no se puede
                    # ocultar (no hay parámetro en 1.59) ni esconder por CSS,
                    # porque la grilla se dibuja en un CANVAS y no hay nodo que
                    # tocar. Cambiar de widget era la única salida.
                    #
                    # La barra de "Valor" NO necesitó un `cellRenderer` (ni la
                    # clase `init()/getGui()` de la regla #25, ni los
                    # sparklines de AG Grid, que son Enterprise): es el FONDO
                    # de la celda, un `linear-gradient` cortado en el % del
                    # valor. Los colores salen de `tema.py` y no de
                    # `var(--accent)` a propósito — el grid vive en un iframe
                    # propio y las variables CSS del documento padre no llegan.
                    _rk_max = float(max(_rk_valores)) if _rk_valores else 1.0
                    _rk_df = pd.DataFrame({
                        # Lo que se VE es el nombre en capitalización de
                        # nombre propio (a pedido, 2026-08-28): el ERP los
                        # manda gritados y ocho filas de mayúsculas se leen
                        # como un bloque. Ver `nombre_propio`, que explica
                        # por qué esto NO se puede hacer con CSS.
                        "Proveedor": [nombre_propio(n) for n in _rk_nombres],
                        "Valor": _rk_valores,
                        "Docs": _rk_docs,
                        "%": _rk_pct,
                        # Columna oculta: el % de LLENADO de la barra (contra
                        # el mayor), que no es el mismo número que la columna
                        # "%" (esa es sobre el total del rango).
                        "_barra": [v / _rk_max * 100 for v in _rk_valores],
                        # Columna oculta: el nombre COMO VIENE del parquet.
                        # El de arriba ya no sirve para identificar la fila
                        # — es texto para leer. Éste es la clave contra la
                        # que compara todo lo demás del drill (el foco, el
                        # popover, el color de la serie de Evolución), y es
                        # el que lee la selección unas líneas más abajo.
                        "_prov_raw": _rk_nombres,
                    })
                    # Fila de TOTAL, a pedido (2026-08-25). Mismo mecanismo
                    # que ya usa `tablas/ajuste_pivote.py`: un dict calculado
                    # en PYTHON + `pinnedBottomRowData`, no el
                    # `"grandTotalRow"` nativo — ese modo en este repo sólo
                    # está probado junto a `pivotMode=True` (Requerimientos,
                    # el pivote de documentos de acá abajo), y esta tabla no
                    # es pivote: es plana, una fila por proveedor.
                    #
                    # Suma lo que la tabla MUESTRA (`_rk_valores`/`_rk_docs`/
                    # `_rk_pct`), no `_tot_all` (el total de TODO el rango,
                    # que usa el % de cada fila): si el usuario deselecciona
                    # proveedores del multiselect de arriba y no incluye
                    # "Otros", la tabla ya muestra menos del 100% a propósito
                    # — el total tiene que sumar esas filas, no prometer un
                    # número que no está en pantalla.
                    #
                    # "Docs" suma los nunique POR PROVEEDOR: puede sobrecontar
                    # si un mismo documento trajera líneas de dos proveedores
                    # distintos, algo que no ocurre en este dominio (un
                    # documento de compra es de un proveedor). Sumar es
                    # correcto en la práctica y evita un segundo cálculo
                    # (`base["docu"].nunique()`) que exigiría re-filtrar por
                    # los proveedores visibles para dar el mismo número.
                    _rk_fila_total = {
                        "Proveedor": "TOTAL",
                        "Valor": round(sum(_rk_valores), 2),
                        "Docs": int(sum(_rk_docs)),
                        "%": round(sum(_rk_pct), 2),
                    }
                    # Dos decisiones de legibilidad, las dos aprendidas
                    # mirando la primera versión (2026-08-19):
                    #
                    # 1. La pista va TRANSPARENTE, no tintada. Con un color de
                    #    fondo la columna entera se leía como un bloque
                    #    lavanda —"una sombra"— compitiendo con las barras y
                    #    tapando las bandas de fila del resto de la tabla.
                    #    Sin pista, lo único que se ve es el dato.
                    # 2. La barra llega hasta el 62% de la celda, no al 100%,
                    #    y el texto va alineado a la DERECHA: así nunca se
                    #    pisan. Antes el monto caía encima del morado y quedaba
                    #    texto oscuro sobre fondo oscuro. El 62% no falsea la
                    #    lectura: todas las barras se escalan igual, así que
                    #    las proporciones entre filas se mantienen.
                    #    (`justifyContent` es obligatorio: el `display:flex`
                    #    de esta misma regla anula el alineado a la derecha
                    #    que trae `type: numericColumn`.)
                    _js_barra = JsCode(
                        "function(p){"
                        # La fila TOTAL no dibuja barra: no hay `_barra`
                        # contra qué escalarla (sería 100% de sí misma,
                        # una barra llena sin información) y el fondo lo
                        # pone `getRowStyle` — un `background` acá se lo
                        # comería, porque la celda pinta ENCIMA de la fila.
                        " if (p.node.rowPinned) return {'display':'flex',"
                        " 'alignItems':'center','justifyContent':'flex-end',"
                        " 'fontWeight':'700'};"
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
                    # Misma paleta que la fila TOTAL del pivote de documentos
                    # de más abajo (`_documentos_proveedor.py`) — dos filas
                    # de cierre del mismo drill, mismo idioma visual.
                    #
                    # SIN `borderTop` desde el 2026-09-09. Acá había un
                    # `2px solid ACENTO` que se APILABA con la línea que el
                    # tema dibuja en `.ag-floating-bottom`: dos rayas
                    # pegadas de distinto color. El rediseño del marco
                    # (`CSS_RANKING_GRID`) deja la tabla sin línea sobre los
                    # totales — la separa el fondo lavanda, que ya lo hacía.
                    # Se saca ACÁ y no con un `!important` en el CSS a
                    # propósito: un estilo inline sólo se apaga tapándolo, y
                    # el que viene a leer esta función tiene que ver lo que
                    # de verdad se dibuja.
                    _js_fila_total = JsCode(
                        "function(p){ if(p.node.rowPinned){ return {"
                        f"'fontWeight':'700','background':'{LAVANDA_CHIP}',"
                        f"'color':'{ACENTO_TEXTO_OSCURO}'"
                        "}; } }")
                    _js_soles = JsCode(
                        "function(p){ return p.value==null ? '' :"
                        " 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")
                    _js_pct = JsCode(
                        "function(p){ return p.value==null ? '' :"
                        " Math.round(p.value) + '%'; }")
                    # Clic en la fila = TOGGLE. `enableClickSelection` va en
                    # False y la selección la maneja este handler: AG Grid, por
                    # sí solo, NO deselecciona al reclickear la fila ya
                    # seleccionada (pide Ctrl+clic, que nadie descubre).
                    # `setSelected(valor, true)` limpia las demás → sigue
                    # siendo selección única.
                    # `rowPinned` afuera: sin este guard, clickear la fila
                    # TOTAL la "selecciona" como si fuera un proveedor real
                    # y el drill de abajo intentaría enfocar un proveedor
                    # llamado "TOTAL" que no existe en los datos.
                    _js_toggle = JsCode(
                        "function(e){ if (e.node.rowPinned) return;"
                        " e.node.setSelected(!e.node.isSelected(),"
                        " true); }")
                    _resp_rank = AgGrid(
                        _rk_df,
                        gridOptions={
                            "columnDefs": [
                                {"field": "Proveedor", "flex": 2,
                                 "tooltipField": "Proveedor"},
                                {"field": "Valor", "flex": 2,
                                 "type": "numericColumn",
                                 "cellStyle": _js_barra,
                                 "valueFormatter": _js_soles},
                                {"field": "Docs", "width": 80,
                                 "type": "numericColumn"},
                                {"field": "%", "width": 80,
                                 "type": "numericColumn",
                                 "valueFormatter": _js_pct},
                                {"field": "_barra", "hide": True},
                                {"field": "_prov_raw", "hide": True},
                            ],
                            "rowSelection": {"mode": "singleRow",
                                             "checkboxes": False,
                                             "enableClickSelection": False},
                            "onRowClicked": _js_toggle,
                            "rowHeight": _ALTO_FILA_RANK,
                            "headerHeight": _ALTO_HEADER_RANK,
                            "suppressCellFocus": True,
                            "suppressMovableColumns": True,
                            "pinnedBottomRowData": [_rk_fila_total],
                            "getRowStyle": _js_fila_total,
                        },
                        allow_unsafe_jscode=True,
                        theme="streamlit",
                        # Filas blancas, cuerpo más chico y minúsculas — el
                        # único camino es `custom_css=`: el grid es un iframe
                        # y el `<style>` del padre (`CSS_PROVEEDOR`) no entra.
                        custom_css=CSS_RANKING_GRID,
                        height=_ALTO_RANK,
                        update_on=["selectionChanged"],
                        key=_rank_tab_key,
                    )
                    # ── El foco sale de la selección del grid ──────────────
                    # AgGrid devuelve la selección VIGENTE en cada run (no un
                    # evento), así que no hace falta dedup: alcanza con
                    # comparar contra el foco guardado. Selección vacía = el
                    # usuario reclickeó la fila (el toggle de arriba) y se
                    # quita el foco. "Otros" no es un proveedor real —agrupa a
                    # los que quedaron fuera— así que no abre drill.
                    # `_prov_raw` y no `Proveedor`: la columna visible pasa
                    # por `nombre_propio()` y ya no matchea contra los datos.
                    _sel_rank = getattr(_resp_rank, "selected_rows", None)
                    if _sel_rank is not None and len(_sel_rank):
                        _fila = (_sel_rank.iloc[0] if hasattr(_sel_rank, "iloc")
                                 else _sel_rank[0])
                        _clicked = str(_fila["_prov_raw"])
                    else:
                        _clicked = None
                    if _clicked == "Otros":
                        _clicked = prov_focus          # ignorar: no cambia nada
                    if _clicked != prov_focus:
                        prov_focus = _clicked
                        st.session_state["compras_prov_focus"] = prov_focus
                        # El producto en foco es de ESTE proveedor: otro
                        # proveedor lo suelta (regla #579).
                        st.session_state["compras_prov_prodfocus"] = None
            # ── El SUJETO de los Documentos y los Productos ─────────────────
            # Sin foco, el proveedor de mayor valor del rango — la primera
            # fila del Ranking (mismo df, mismo orden). Se calcula UNA vez,
            # acá, y lo leen las dos tarjetas: si cada una eligiera el suyo,
            # bastaría un desempate distinto para que los Productos y los
            # Documentos de abajo hablaran de dos proveedores. NO se
            # persiste en session_state: el foco real lo sigue fijando el
            # clic. La Evolución tiene su propio fallback (el mayor de SU
            # ventana, ver su bloque): con ella la diferencia es a propósito.
            _prov_ver = prov_focus
            if _prov_ver is None and not base.empty:
                _prov_ver = base.groupby("prov")["valor"].sum().idxmax()
            # ── El PRODUCTO en foco (2026-10-01, regla #579) ────────────
            # Un clic en un producto de la tabla de Productos lo pone acá
            # (por el relevo `cp_prov_prod_relevo`, ver `_tarjeta_productos`)
            # y la Evolución pasa a dibujar ESE producto de ESE proveedor.
            # Sólo vale si el producto está entre los de `_prov_ver` en el
            # rango: un producto que ya no está en la tabla no puede mandar
            # sobre el gráfico.
            _prod_evo = st.session_state.get("compras_prov_prodfocus")
            if _prod_evo is not None and (
                    _prov_ver is None
                    or _prod_evo not in set(
                        base.loc[base["prov"] == _prov_ver, "prod"])):
                _prod_evo = None
            # Los PERÍODOS de la Evolución, que los Documentos y los
            # Productos usan para agruparse «como Evolución» (regla #579).
            # Los llena el bloque de la Evolución; estos son los valores
            # para cuando no dibuja serie (no hay proveedor en su ventana).
            _src_evo, _per_evo, _evo_x = None, [], []
            _etq_evo = str
            with _c_evo:
                # ── BLOQUE 2: la evolución, con su propio período ──
                # Desde el 2026-10-01 vive en la fila de ABAJO, a la
                # derecha de los Documentos (reglas #578 y #579), y su alto
                # sale de las SEIS filas de esa fila (`_ALTO_EVO`).
                with st.container(border=True,
                                  key="compras_prov_card_evo"):
                    # Sin elección del usuario cae al primero del ranking (el de
                    # mayor valor) — mismo criterio que el Panel B de abajo.
                    # `_rk_nombres` viene ordenado DESCENDENTE (mayor primero,
                    # el orden natural de la tabla-ranking de al lado), así que
                    # el mayor es directamente el primero.
                    _prov_evo = prov_focus
                    if _prod_evo is not None:
                        # Con un producto en foco, el proveedor es el de la
                        # tabla de Productos, que es de donde salió el clic.
                        _prov_evo = _prov_ver
                    if _prov_evo is None:
                        # SIN FOCO, EL SUJETO SALE DEL HISTÓRICO, no del
                        # ranking de al lado. A pedido, 2026-08-26: "el
                        # selector de fecha del ranking no debe afectar el
                        # gráfico de evolución".
                        #
                        # Su VENTANA ya era independiente (esta tarjeta
                        # tiene su propio `periodo.selector`, default 12m,
                        # que recorta sobre `d_full` salteándose el filtro
                        # de fecha), y sin embargo la tarjeta SÍ cambiaba al
                        # mover la fecha — medido: pasar de "1-24 ago" a
                        # "3-9 ago" la llevaba de DOBLE G (S/ 13,363) a
                        # LEON MEDRANO (S/ 10,362), con el eje de 12 meses
                        # quieto. La ventana no era el problema: el SUJETO
                        # sí, porque el fallback tomaba el primero de
                        # `_rk_nombres`, que está ordenado sobre el df
                        # filtrado por la franja.
                        #
                        # El mayor DE SU PROPIA VENTANA, no del histórico
                        # entero: se probó con el histórico y el sujeto
                        # salía con el gráfico vacío (VITTORY MEATS SAC,
                        # S/ 0 — es el mayor de todos los tiempos pero no
                        # compró nada en los últimos 12 meses). El sujeto y
                        # la ventana tienen que salir de la MISMA fuente o
                        # la tarjeta se contradice sola.
                        #
                        # La opción de período se lee de `session_state`
                        # porque su widget se instancia más abajo (línea
                        # ~1050); leerla antes es legal, escribirla no.
                        # Mismo default que el selector, para que el primer
                        # render coincida con lo que ese widget va a
                        # elegir.
                        _op_prev = st.session_state.get("cp_evo_periodo", "12m")
                        _src_def = d_full
                        if (_op_prev != periodo.HEREDA and d_full is not None
                                and col_fecha):
                            _src_def = periodo.recortar(d_full, col_fecha,
                                                        _op_prev)
                        _prov_evo = _prov_mayor(_src_def, col_prov, col_valor)
                        # Con eso, la tarjeta sólo cambia de proveedor
                        # cuando el usuario clickea uno — que es el drill, y
                        # ese sí tiene que seguir mandando.
                    if _prov_evo is None:
                        # Sin histórico (el dispatcher puede no pasarlo),
                        # se vuelve al comportamiento de antes.
                        _reales = [p for p in _rk_nombres if p != "Otros"]
                        _prov_evo = _reales[0] if _reales else None
                    if _prov_evo is None:
                        st.caption("Sin proveedores en el rango.")
                    else:
                        # ── El período de ESTA tarjeta, elegido por el usuario ──
                        # Antes acá había una heurística muda: si el rango de la
                        # franja daba menos de 2 períodos (un mes, o un año en
                        # granularidad Año), la evolución se pasaba sola al
                        # histórico completo — una línea de un punto no dibuja
                        # ninguna evolución (reportado con captura). Acertaba,
                        # pero el usuario se enteraba DESPUÉS, por el caption.
                        #
                        # Desde 2026-08-18 la ventana es un control suyo
                        # (`graficos/periodo.py`): el ranking de al lado sigue
                        # mirando el rango de la franja y la evolución mira lo
                        # que le pidan. Son dos preguntas distintas —"quién pesa
                        # más ACÁ" y "cómo viene este proveedor"— y ahora cada
                        # una tiene su eje de tiempo, en vez de compartir uno y
                        # corregirlo a escondidas.
                        # 2026-09-09, a pedido: el título dice «Evolución»
                        # y NADA MÁS. Antes traía además el proveedor y la
                        # ventana («Evolución · Vibej Colibri SAC · últimos 3
                        # meses»), y las dos se fueron por el mismo motivo:
                        # repetían algo que ya está a la vista tres píxeles
                        # más allá. La ventana la dice el desplegable de su
                        # misma fila; el proveedor pasó DENTRO del gráfico,
                        # como anotación del color de su propia línea (ver
                        # `add_annotation`, más abajo).
                        #
                        # Con eso deja de ser un texto que sólo se puede
                        # escribir al final —ya no nombra nada que dependa de
                        # los controles— y vuelve a ser una constante: se
                        # dibuja acá, en su sitio, sin el `st.empty()` que se
                        # reservaba arriba y se rellenaba 300 líneas después.
                        #
                        # `cp_evo_cab` es la CABECERA de la tarjeta: el título
                        # a la izquierda y la fila de controles pegada a la
                        # derecha, en un solo renglón. Envuelve a
                        # `cp_evo_ctrl` en vez de reemplazarlo para no tocar
                        # nada del reparto horizontal de los tres
                        # desplegables, que está medido al píxel (ver su
                        # bloque en `_css_proveedor.py`).
                        # 2026-08-23 (3), a pedido ("que sea una lista
                        # desplegable, minimalista... y que esté en una
                        # línea, no una debajo de otra"): las DOS filas de
                        # pills que había acá —la ventana (📅/3m/12m/24m/
                        # Todo) y la granularidad (Día/Semana/Mes/Año)—
                        # pasan a `st.selectbox` aplanados a texto y
                        # comparten un solo renglón (`cp_evo_ctrl`, flex
                        # row; mismo recurso que `win_nav`, no `st.columns`
                        # — es una fila DENTRO de una tarjeta).
                        #
                        # Lo que se gana son los ~30px de la fila que
                        # desaparece, y van a la figura (ver `_ALTO_EVO`,
                        # arriba: `FRANJA_CTRL_EVO` reemplazó a las dos
                        # constantes que había). Lo que se paga es que las
                        # opciones dejan de verse hasta el clic — aceptado
                        # explícitamente al elegir esta opción sobre un
                        # popover.
                        #
                        # El ícono 📅 vuelve a ser texto: como pastilla se
                        # entendía porque las cinco se veían juntas, pero
                        # como valor CERRADO de un desplegable un emoji
                        # solo no dice nada. Igual la granularidad, que
                        # pasa a "Por mes" — es la información que daba el
                        # caption "Agrupado por X" que se quitó cuando el
                        # control estaba a la vista.
                        def _win_mover(_delta):
                            st.session_state["cp_prov_win_ini"] = min(
                                max(0, _win_ini + _delta), _ini_max)

                        def _fmt_win(_o):
                            """Etiqueta de una opción de ventana. `None` es
                            automático y `_n_per` es "todas": los dos llevan
                            el número al lado porque el usuario elige CUÁNTOS
                            períodos ve, y sin la cifra "Auto" no dice nada.

                            El número de "Todo" se cae a partir de 3 dígitos,
                            y no por gusto: el control mide 64px (48 para el
                            texto) y "Todo 730" —granularidad Día sobre todo
                            el histórico, un caso que pasa— pide 50. Medido
                            con `measureText` a 11px/600, que es la fuente
                            real. "Auto" no necesita el corte: su número sale
                            de `_ventana_auto`, acotado a 4..12."""
                            if _o is None:
                                return f"Auto {_ventana_auto}"
                            if _o == _n_per:
                                return f"Todo {_n_per}" if _n_per < 100 else "Todo"
                            return str(_o)

                        with st.container(key="cp_evo_cab"):
                            st.markdown('<div class="cp-evo-tit">Evolución</div>',
                                        unsafe_allow_html=True)
                            with st.container(key="cp_evo_ctrl"):
                                # 2026-08-23 (4), a pedido ("que entre en la
                                # misma línea que el resto"): `win_nav` era la
                                # TERCERA fila de controles de tiempo de esta
                                # tarjeta y se parte en dos para caber en el
                                # renglón compartido:
                                #
                                #   · el TAMAÑO de la ventana (cuántos períodos
                                #     se ven a la vez) pasa a ser el tercer
                                #     desplegable, hermano de los otros dos;
                                #   · las FLECHAS ‹ › se quedan como están —
                                #     mover una ventana es navegación de un
                                #     clic, y meterla en una lista la volvería
                                #     de dos.
                                #
                                # El emoji 📅 del primero se fue en la misma
                                # vuelta: medidos los textos a 11px, los tres
                                # desplegables más las flechas suman ~270px en
                                # una fila de 279.5, y con el emoji se pasaban.
                                # Era decorativo; "Rango" solo dice lo mismo.
                                # La MEDIDA (2026-10-01, regla #579):
                                # Soles, Cantidad o Precio. Las dos últimas
                                # piden un producto en foco; sin él, la
                                # línea sigue en soles y lo dice en su
                                # rótulo.
                                with st.container(key="evo_medida"):
                                    _medida_pedida = st.selectbox(
                                        "Medida", list(_MEDIDAS),
                                        key="cp_evo_medida",
                                        format_func=_MEDIDAS.get,
                                        label_visibility="collapsed")
                                _medida_evo = (_medida_pedida
                                               if _prod_evo is not None
                                               else "valor")
                                _op_evo = periodo.selector(
                                    "cp_evo_periodo", widget="lista")
                                # Se resuelve ACÁ y no después del bloque porque
                                # los dos controles de ventana de más abajo lo
                                # necesitan para saber si les toca estar vivos.
                                _evo_hist = _op_evo != periodo.HEREDA
                                # `gran_float` conserva la key aunque ya no
                                # flote ni sea pills (mismo criterio que
                                # --rail-der-* tras el flip de lado): la nombra
                                # arquitectura.md #178 y la usa el bloque móvil
                                # de _css_proveedor.py.
                                with st.container(key="gran_float"):
                                    # El label va COLAPSADO, así que sólo lo
                                    # ve un lector de pantalla — y por eso
                                    # dejó de llamarse "Periodo": ahora que
                                    # comparte renglón con `cp_evo_periodo`
                                    # (cuyo label ES "Período"), dos controles
                                    # vecinos se anunciaban casi igual.
                                    st.selectbox(
                                        "Agrupar por",
                                        ["Día", "Semana", "Mes", "Año"],
                                        index=2, key="compras_prov_gran",
                                        format_func=lambda g: f"Por {g.lower()}",
                                        label_visibility="collapsed")
                                # El TAMAÑO de la ventana. El widget es dueño
                                # DIRECTO de `cp_prov_win_size`, la misma clave
                                # que antes escribían los `on_click` de los
                                # botones: no hace falta callback ni una clave
                                # espejo. Por eso desapareció `_win_size()`, y
                                # con él el `st.markdown` con un `<style>` que
                                # pintaba de acento el botón activo — un
                                # desplegable ya muestra cuál está elegido.
                                # El clamp de `_ops_win` vive arriba, donde se
                                # calcula la ventana: la lista es dinámica y un
                                # valor viejo fuera de ella rompe el widget.
                                # La ventana es del RANGO: `_sl` sólo se aplica
                                # cuando la tarjeta hereda el rango de la franja
                                # (ver el bloque de `_evo_x`, más abajo, que ya
                                # era así). Hasta ahora eso no se veía: con una
                                # ventana propia elegida, estos dos controles
                                # seguían habilitados y no hacían nada. Con el
                                # rango de franja corto las flechas salían
                                # apagadas por sus propios topes y disimulaba,
                                # pero con un rango ancho quedaban encendidas y
                                # muertas. Mismo criterio que el bloqueo de
                                # clicks del modo diseño: si no va a pasar nada,
                                # decirlo antes, no después.
                                _ayuda_win = ("Sólo cuando la tarjeta hereda el "
                                              "rango de la franja (opción "
                                              "«Rango»)")
                                with st.container(key="win_size"):
                                    st.selectbox(
                                        "Períodos visibles", _ops_win,
                                        index=0, key="cp_prov_win_size",
                                        format_func=_fmt_win, disabled=_evo_hist,
                                        help=_ayuda_win if _evo_hist else None,
                                        label_visibility="collapsed")
                                # Las flechas se quedan como botones: son
                                # navegación de UN clic. `win_nav` conserva la
                                # key, y ahora le queda mejor que antes — mover
                                # la ventana es lo único que hace, el tamaño
                                # nunca fue "navegación".
                                with st.container(key="win_nav"):
                                    st.button("‹", key="cp_win_prev",
                                              disabled=_evo_hist or _win_ini <= 0,
                                              help=(_ayuda_win if _evo_hist
                                                    else "Periodos anteriores"),
                                              on_click=_win_mover,
                                              args=(-_ventana,))
                                    st.button("›", key="cp_win_next",
                                              disabled=(_evo_hist
                                                        or _win_ini >= _ini_max),
                                              help=(_ayuda_win if _evo_hist
                                                    else "Periodos siguientes"),
                                              on_click=_win_mover,
                                              args=(_ventana,))
                        # ALCANCE de los tres controles de tiempo de esta
                        # tarjeta, que NO es el mismo (corregido 2026-08-23:
                        # el comentario anterior afirmaba que `gran` era
                        # "compartido con el Ranking para las dos columnas"
                        # y citaba la regla #176, que es la de `help=` en
                        # st.markdown — las dos cosas estaban mal):
                        #
                        #   · `cp_evo_periodo` → sólo esta tarjeta, y
                        #     además MANDA sobre los dos controles de
                        #     ventana (`win_size`/`win_nav`): con una
                        #     ventana propia elegida quedan deshabilitados.
                        #   · `gran` → esta tarjeta, `win_nav` (cuántos
                        #     períodos entran en la ventana) y la tabla
                        #     pivotable de documentos del fondo del drill,
                        #     cuyas COLUMNAS son los períodos
                        #     (`_documentos_proveedor.py`).
                        #   · `win_nav` → sólo esta tarjeta.
                        #
                        # El Ranking de al lado NO mira períodos: suma por
                        # proveedor sobre todo el rango (ver el comentario
                        # de `_tot_por_prov`, arriba). `_agregar_periodo()`
                        # se le aplica a `base`, que alimenta a las dos
                        # columnas, pero lo único que hace además de crear
                        # `per` es descartar filas con fecha inválida — y
                        # una fecha inválida lo es en las cuatro
                        # granularidades por igual. Ver arquitectura.md #178.

                        _src_evo = base
                        if _evo_hist and d_full is not None and col_fecha:
                            # La ventana se recorta sobre `d_full` (sin el filtro
                            # de fecha de la franja) ANTES de agrupar por período:
                            # recortar después dejaría los períodos del borde
                            # partidos a la mitad.
                            _d_evo = periodo.recortar(d_full, col_fecha, _op_evo)
                            # `cant` y `docu` no los usa la línea, pero sí el
                            # resumen de abajo: tiene que poder sumar sobre la
                            # MISMA fuente que el gráfico que resume.
                            _bf = pd.DataFrame({
                                "prov":  _d_evo[col_prov].astype(str).values,
                                "valor": pd.to_numeric(_d_evo[col_valor],
                                                       errors="coerce").fillna(0).values,
                                "cant":  (pd.to_numeric(_d_evo[col_cant],
                                                        errors="coerce").fillna(0).values
                                          if col_cant else 0.0),
                                # `prod`, para la vista «por período»
                                # de los Productos (regla #579).
                                "prod":  (_d_evo[col_prod].astype(str).values
                                          if col_prod else "—"),
                                "docu":  (_d_evo[col_docu].astype(str).values
                                          if col_docu else ""),
                                # La unidad, para la Cantidad (regla #579).
                                "um":    (_d_evo[col_um].astype(str).values
                                          if col_um else ""),
                                "fecha": pd.to_datetime(_d_evo[col_fecha],
                                                        errors="coerce").values,
                            })
                            _bf = _agregar_periodo(
                                _bf[_bf["prov"].notna() & (_bf["prov"] != "nan")])
                            if not _bf.empty:
                                _src_evo = _bf
                            else:
                                _evo_hist = False
                        _per_evo = (_src_evo[["_per_sort", "per"]].drop_duplicates()
                                    .sort_values("_per_sort")["per"].tolist())
                        _per_evo = list(dict.fromkeys(_per_evo))
                        # Las filas que dibuja la línea: las del proveedor y,
                        # con un producto en foco, sólo las de ese producto.
                        _m_evo = _src_evo["prov"] == _prov_evo
                        if _prod_evo is not None:
                            _m_evo &= _src_evo["prod"] == _prod_evo
                        _serie_evo = _serie_medida(_src_evo[_m_evo], _per_evo,
                                                   _medida_evo)
                        # La unidad del producto en foco (la más usada en
                        # sus compras), para rotular la Cantidad.
                        _um_evo = ""
                        if _medida_evo == "cant" and "um" in _src_evo.columns:
                            _ums = _src_evo.loc[_m_evo, "um"].astype(str)
                            _ums = _ums[~_ums.isin(("", "nan", "None"))]
                            _um_evo = _ums.mode().iat[0] if len(_ums) else ""
                        # Con ventana propia se dibuja lo que el usuario pidió,
                        # entero: acá vivía un `tail(12)` fijo que tenía sentido
                        # cuando la fuente era "todo el histórico" y nadie la
                        # había elegido, pero ahora contradiría al selector (pedir
                        # 24m y ver 12 puntos). Las flechas de ventana (`_sl`) son
                        # del RANGO, así que solo se aplican cuando la tarjeta
                        # hereda el rango.
                        if _evo_hist:
                            _evo_x = list(_serie_evo.index)
                            _evo_y = [float(v) for v in _serie_evo.values]
                        else:
                            _evo_x = list(_serie_evo.index)[_sl]
                            _evo_y = [float(v) for v in _serie_evo.values[_sl]]
                        _color_evo = dict(zip(_rk_nombres, _rk_colores)).get(
                            _prov_evo, ACENTO)
                        fig_evo = go.Figure(go.Scatter(
                            x=_evo_x, y=_evo_y,
                            mode="lines+markers",
                            line=dict(color=_color_evo, width=2.5),
                            marker=dict(color=_color_evo, size=7),
                            # En Precio, sin relleno: el área bajo un precio
                            # no suma nada, y con meses sin compras (huecos)
                            # se dibujaba como una banda suelta.
                            fill=("none" if _medida_evo == "precio"
                                  else "tozeroy"),
                            fillcolor=_color_evo.replace(")", ", 0.10)").replace(
                                "rgb(", "rgba(") if _color_evo.startswith("rgb")
                                else None,
                            hovertemplate=(
                                "%{x}<br>S/ %{y:,.0f}<extra></extra>"
                                if _medida_evo == "valor" else
                                "%{x}<br>S/ %{y:,.2f}<extra></extra>"
                                if _medida_evo == "precio" else
                                "%{x}<br>%{y:,.0f} " + str(_um_evo)
                                + "<extra></extra>"),
                            # Un período sin compras no tiene precio: la
                            # línea lo salta en vez de caer a cero.
                            connectgaps=True,
                        ))
                        # Etiquetas del eje X: las "2026-08" se pisan entre sí
                        # y quedan ilegibles (reportado con captura). Dos cosas
                        # juntas: se acortan a "ago 26" y se muestra UNA CADA N.
                        # El punto sin etiqueta sigue estando en el hover, que
                        # trae el período completo.
                        _MES_AB = ("ene", "feb", "mar", "abr", "may", "jun",
                                   "jul", "ago", "sep", "oct", "nov", "dic")

                        def _etq_evo(_p):
                            _t = str(_p)
                            if gran == "Mes" and len(_t) == 7 and _t[4] == "-":
                                try:
                                    return f"{_MES_AB[int(_t[5:]) - 1]} {_t[2:4]}"
                                except (ValueError, IndexError):
                                    return _t
                            return _t

                        # El paso sale del ANCHO real, no de un divisor fijo.
                        # Acá había un `// 6` calibrado contra los ~380px que
                        # medía esta figura antes de que el 2026-08-19 su
                        # columna se partiera en [2.6, 1] para poner los KPIs
                        # al costado. Nadie revisó el número: quedó pidiendo 5
                        # etiquetas en 206px, y las CUATRO parejas se pisaban
                        # (-1 a -5px, medido en el navegador). Con el ancho de
                        # verdad da 4 y el peor hueco pasa a +11px.
                        _tickf_evo = 13
                        _etqs_evo = [_etq_evo(x) for x in _evo_x]
                        _paso_evo = paso_etiquetas(
                            len(_evo_x),
                            max((len(e) for e in _etqs_evo), default=1),
                            ancho=_ANCHO_EVO, px_fuente=_tickf_evo)
                        _tickv = [x for i, x in enumerate(_evo_x)
                                  if i % _paso_evo == 0]
                        # La fila de pills sale del MISMO presupuesto que la
                        # figura (alturas.py § LO QUE LA FIGURA NO ES): sin la
                        # resta, la columna de la evolución crece 42px contra la
                        # del ranking y la tarjeta empuja su propio borde.
                        _compras_layout(fig_evo, alto=_ALTO_EVO)
                        fig_evo.update_layout(
                            margin=dict(l=10, r=10, t=6, b=10),
                            # size=10 (reportado "casi no se ven"): es el mismo
                            # oscuro que el resto de la app (rgb(49,51,63), sin
                            # problema de contraste — medido), pero en una caja
                            # de 32x13px era chico de mas. 13, no 10, para que
                            # sean el UNICO texto legible de este grafico sin
                            # pasar el mouse (el eje Y va sin numeros a
                            # proposito, el valor de cada punto vive en el
                            # hover).
                            xaxis=dict(type="category", tickangle=0,
                                       tickmode="array", tickvals=_tickv,
                                       ticktext=[_etq_evo(x) for x in _tickv],
                                       tickfont=dict(size=13)),
                            # Acá el eje Y SÍ son valores, así que se respeta la
                            # convención del proyecto y va sin etiquetas: cada
                            # punto trae su monto en el hover.
                            yaxis=dict(showticklabels=False),
                            showlegend=False,
                            hovermode="x unified",
                        )
                        # ── QUIÉN es esta línea: DENTRO del gráfico ──────
                        # 2026-09-09, a pedido. El nombre del proveedor vivía
                        # en el título de la tarjeta; ahora es una anotación
                        # en el papel de la propia figura, DEL COLOR DE SU
                        # LÍNEA — el mismo que le tocó en el ranking de al
                        # lado. Ahí dice dos cosas de una: quién, y cuál de
                        # las barras de la tabla vecina es.
                        #
                        # Arriba a la IZQUIERDA y en coordenadas de papel
                        # (`xref/yref="paper"`), que es lo único estable: el
                        # eje X es `type="category"` y el Y arranca en 0 con
                        # `fill="tozeroy"`, así que anclarla a un dato la
                        # movería con cada cambio de ventana. La esquina
                        # superior izquierda es la que más veces queda
                        # vacía —el área pintada crece desde abajo— y el
                        # fondo translúcido cubre el caso en que no.
                        #
                        # `nombre_propio` ANTES de truncar, para que los
                        # puntos suspensivos caigan sobre el texto que se ve.
                        _tit_evo = _compras_truncar(nombre_propio(_prov_evo), 26)
                        if _prod_evo is None and _medida_pedida != "valor":
                            # Pidió Cantidad o Precio sin un producto: se
                            # dibuja en soles, y se dice por qué.
                            _tit_evo += ('<br><span style="font-size:10px;'
                                         f'font-weight:400;color:{GRIS_TEXTO}">'
                                         'en soles · clic en un producto para '
                                         f'ver su {_MEDIDAS[_medida_pedida].lower()}'
                                         '</span>')
                        if _prod_evo is not None:
                            # El producto primero —es lo que cambió— y el
                            # proveedor detrás, más chico.
                            _tit_evo = (
                                f"{_compras_truncar(str(_prod_evo), 28)}"
                                f'<span style="font-weight:400;font-size:10.5px">'
                                f" · {_compras_truncar(nombre_propio(_prov_evo), 22)}"
                                "</span>")
                        # Un punto suelto no dibuja ninguna evolución. Antes eso
                        # se corregía solo (se saltaba al histórico sin avisar);
                        # ahora la ventana la eligió el usuario, así que la salida
                        # correcta es DECIRLO y dejarle los controles que lo
                        # arreglan, no pasar por encima de lo que pidió. Iba en
                        # el sufijo del título de la tarjeta; se muda con el
                        # nombre, en segundo renglón y apagado — sigue costando
                        # cero alto (es papel de la figura, no una fila más) y
                        # queda a la vista de los controles que lo resuelven.
                        # NO se va con el resto del sufijo: la ventana la dice
                        # el desplegable, pero "no hay nada que dibujar" no lo
                        # dice nadie más.
                        if len(_evo_x) < 2:
                            _tit_evo += ('<br><span style="font-size:10px;'
                                         f'color:{GRIS_TEXTO}">'
                                         '1 solo período</span>')
                        fig_evo.add_annotation(
                            xref="paper", yref="paper",
                            x=0, y=1, xanchor="left", yanchor="top",
                            text=f"<b>{_tit_evo}</b>", showarrow=False,
                            align="left",
                            font=dict(size=12, color=_color_evo),
                            bgcolor="rgba(255,255,255,0.72)", borderpad=2,
                        )
                        # 2026-08-19, a pedido: el resumen deja de ir DEBAJO
                        # del gráfico y pasa a su COSTADO, en columna. Gana el
                        # gráfico (recupera los ~97px de alto que le comía el
                        # bloque) y gana el resumen (4 cifras en vertical se
                        # leen de un barrido, no en un 2x2 que obliga a saltar
                        # en zigzag). Es un nivel de anidado de columnas —
                        # Streamlit permite exactamente uno, así que acá se
                        # agota: si algún día hay que subdividir otra vez,
                        # tiene que ser con contenedores, no con más columnas.
                        # 2.6/1 y no 2/1: medido, con 2/1 el gráfico quedaba
                        # en 243px para 13 puntos y la columna de cifras
                        # sobraba (la más ancha, "S/ 20,711", pide ~86 y
                        # tenía 117). El gráfico es el protagonista.
                        # columnas-internas: el chart y su pila de KPIs parten
                        # DENTRO de una tarjeta. No es el eje de la página,
                        # que lo manda COLUMNAS_DRILL_ABAJO.
                        _c_graf, _c_kpi = st.columns([2.6, 1], gap="small")
                        with _c_graf:
                            st.plotly_chart(
                                fig_evo, width="stretch",
                                key=f"cp_evo_{gran}_{_prov_evo}_{_prod_evo}",
                                config={"displayModeBar": False},
                            )
                        # ── Resumen del proveedor ───────────────────────────
                        # Resume UN período de la granularidad vigente. En
                        # reposo, el ÚLTIMO —el último punto de la línea de
                        # arriba, o sea "cómo le fue el último mes / semana /
                        # año"—; con el cursor sobre un punto del gráfico, ESE
                        # (2026-09-09, a pedido). El período se imprime en el
                        # encabezado: sin eso "S/ 2,104" no dice contra qué, y
                        # menos todavía si el número cambia solo al pasar el
                        # mouse.
                        #
                        # Sale de `_src_evo`, la MISMA fuente que la línea (rango
                        # o histórico según el caso). Un resumen pegado a un
                        # gráfico tiene que sumar lo que ese gráfico muestra, o
                        # los números contradicen a la curva que tienen encima.
                        #
                        # Los 4 valores se calculan para TODOS los períodos
                        # dibujados, no sólo para el último: el hover no puede
                        # ir al servidor (`st.plotly_chart` sólo reporta
                        # selección, no hover, y aunque la reportara un rerun
                        # de esta app tarda 3-6s — ver `estilos/_88_cargando.py`),
                        # así que la tabla entera viaja con el gráfico y el
                        # intercambio lo hace el navegador. Son 4 cifras por
                        # punto y el eje tiene a lo sumo unas decenas.
                        if _evo_x:
                            _dprov = _src_evo[_m_evo]
                            # `reindex(_evo_x)`: el eje manda. Un período sin
                            # compras de ESTE proveedor tiene que salir en 0,
                            # no faltar — si no, el índice del punto que
                            # reporta Plotly deja de coincidir con la fila.
                            _g_val = (_dprov.groupby("per")["valor"].sum()
                                      .reindex(_evo_x, fill_value=0.0))
                            # La MEDIDA elegida, para la primera cifra y la
                            # variación (en soles es la misma `_g_val`).
                            _g_med = _serie_medida(_dprov, _evo_x, _medida_evo)
                            # El «% del total»: contra todos los proveedores;
                            # con un producto en foco, contra lo comprado a
                            # ESE proveedor («% del proveedor»).
                            _src_tot = (_src_evo if _prod_evo is None
                                        else _src_evo[_src_evo["prov"] == _prov_evo])
                            _g_tot = (_src_tot.groupby("per")["valor"].sum()
                                      .reindex(_evo_x, fill_value=0.0))
                            # El período ANTERIOR a cada uno de los dibujados,
                            # para la variación. Sale de `_per_evo` (todos los
                            # períodos de `_src_evo`) y no de `_evo_x` (los que
                            # se ven): con las flechas de ventana, el primero
                            # de la pantalla SÍ tiene uno antes, sólo que fuera
                            # de cuadro. `_evo_x` es un tramo contiguo de
                            # `_per_evo`, así que basta con saber dónde
                            # empieza.
                            _g_todo = _serie_medida(_dprov, _per_evo, _medida_evo)
                            _pos0 = (_per_evo.index(_evo_x[0])
                                     if _evo_x[0] in _per_evo else 0)
                            if "docu" in _dprov.columns:
                                # Mismo criterio que la versión de un solo
                                # período: el documento vacío no cuenta.
                                # `nunique()` ya descarta los NA.
                                _g_docs = (_dprov.assign(
                                    _d=_dprov["docu"].replace("", pd.NA))
                                    .groupby("per")["_d"].nunique()
                                    .reindex(_evo_x, fill_value=0))
                            else:
                                _g_docs = pd.Series(0, index=_evo_x)
                            # Encabezado por período: sólo el último lleva
                            # "Último/Última" — en los demás sería mentira.
                            # ("Semana" es femenino y las otras tres no: sin
                            # esto salía "Último semana".)
                            _ult_art = "Última" if gran == "Semana" else "Último"

                            def _var_txt(_i, _g=_g_todo, _p0=_pos0):
                                """`(texto, color)` de la variación del punto
                                `_i` contra el período de antes.

                                Tres casos y ninguno es cosmético:

                                · **Sin período anterior** (el primero del
                                  histórico) o con el anterior en CERO: «—».
                                  Un % de variación desde cero no existe, y
                                  fabricar un «+100%» sería inventarlo. Mismo
                                  criterio que `_delta` en
                                  `graficos/compras/__init__.py`, que
                                  directamente no devuelve nada con `ant <= 0`.
                                · **Redondea a 0.0%**: sin flecha. Una flecha
                                  sobre un «0.0%» dice que se movió cuando lo
                                  que se ve es que no.
                                · **Por debajo del 0,5%**: flecha sí, color no
                                  — es el umbral de ruido de `_delta`, que a
                                  esa altura ni dibuja la flecha.

                                El COLOR no se elige acá: en Compras GASTAR
                                MÁS es rojo, y eso lo fija `_delta` (y el
                                drill «Vs año pasado»). Dos sitios de la
                                misma pantalla no pueden decir lo contrario
                                del mismo signo.
                                """
                                _j = _p0 + _i - 1
                                if _j < 0:
                                    return "—", ""
                                _ant = float(_g.iloc[_j])
                                # `not >` y no `<=`: en Precio un período
                                # sin compras es NaN, y NaN <= 0 da False.
                                if not _ant > 0 or pd.isna(_g.iloc[_p0 + _i]):
                                    return "—", ""
                                _v = (float(_g.iloc[_p0 + _i]) - _ant) / _ant * 100
                                if abs(_v) < 0.05:
                                    return "0.0%", ""
                                _flecha = "▲" if _v > 0 else "▼"
                                _color = ("" if abs(_v) < 0.5
                                          else (ERROR if _v > 0 else EXITO))
                                return f"{_flecha} {abs(_v):.1f}%", _color

                            _kpis_evo = []
                            for _i, _p in enumerate(_evo_x):
                                _r_val = float(_g_val.iloc[_i])
                                # El % se mide contra lo comprado a TODOS los
                                # proveedores en ese mismo período: "de lo que
                                # gasté este mes, tanto fue con este proveedor".
                                _r_pct = _r_val / (float(_g_tot.iloc[_i]) or 1.0) * 100
                                _r_var, _r_var_col = _var_txt(_i)
                                _kpis_evo.append({
                                    "tit": (f"{_ult_art} {gran.lower()}"
                                            if _i == len(_evo_x) - 1
                                            else gran)
                                           + f" · {_etq_evo(_p)}",
                                    "vals": [_fmt_medida(float(_g_med.iloc[_i]),
                                                         _medida_evo, _um_evo),
                                             # En Cantidad y Precio, la
                                             # segunda cifra es lo pagado:
                                             # un % de kilos no se lee.
                                             f"{_r_pct:.1f}%"
                                             if _medida_evo == "valor"
                                             else f"S/ {_r_val:,.0f}",
                                             _r_var,
                                             f"{int(_g_docs.iloc[_i]):,.0f}"],
                                    # Un color por celda, en el mismo orden.
                                    # Vacío = el que ya pone el CSS.
                                    "cols": ["", "", _r_var_col, ""],
                                })
                            # "Vs. anterior" y no "Vs. mes anterior": la celda
                            # da 63px de texto a 10px (medido) y el rótulo
                            # largo pide 63 en «mes» y 78 en «semana», o sea
                            # que envolvería a dos renglones y estiraría la
                            # pila —que es el piso de alto de la figura de al
                            # lado (`_MIN_EVO`)—. Cuál es el anterior lo dice
                            # el encabezado, que nombra el período.
                            _rotulos_kpi = ({"valor": "Total compra",
                                             "cant": "Cantidad",
                                             "precio": "Precio prom."}[_medida_evo],
                                            # «% del prov.» y no «% del
                                            # proveedor»: tiene el largo de
                                            # «% del total», que es lo que
                                            # entra en la celda (ver abajo).
                                            "% del total" if _prod_evo is None
                                            else "% del prov."
                                            if _medida_evo == "valor"
                                            else "Valor compra",
                                            "Vs. anterior", "Documentos")
                            with _c_kpi:
                                _base_kpi = _kpis_evo[-1]
                                st.markdown(
                                    f'<div class="cp-evo-kpis-tit">'
                                    f'{_base_kpi["tit"]}</div>'
                                    '<div class="cp-evo-kpis">'
                                    # El color va INLINE, igual que lo escribe
                                    # el JS del hover: si el de reposo saliera
                                    # de una clase y el del hover de un
                                    # `style`, el primer hover cambiaría el
                                    # color y el `unhover` no podría
                                    # devolverlo.
                                    + "".join(
                                        f'<div><span>{_k}</span>'
                                        f'<b{f" style=\'color:{_c}\'" if _c else ""}>'
                                        f'{_v}</b></div>'
                                        for _k, _v, _c in zip(_rotulos_kpi,
                                                              _base_kpi["vals"],
                                                              _base_kpi["cols"]))
                                    + '</div>', unsafe_allow_html=True)
                                # El que cambia las cifras al pasar el mouse.
                                # Va DENTRO de la columna de los KPIs a
                                # propósito (es su comportamiento) y no cuesta
                                # alto: `navegacion.py` le pone `display:none`
                                # al contenedor de cualquier iframe, así que ni
                                # el gap del bloque vertical paga.
                                inject_hover_kpis("compras_prov_card_evo",
                                                  _kpis_evo)
            with _c_docs:
                # ── Los documentos del proveedor en foco (abajo a la izq.) ──
                # Va DESPUÉS de la Evolución aunque se vea a su izquierda:
                # agrupado, usa sus períodos (`_src_evo`/`_per_evo`).
                _tarjeta_documentos(base, _prov_ver, _ALTO_LISTA_DOCS, gran,
                                    _src_evo, _per_evo, _etq_evo)
        # 2026-08-23: `win_nav` (‹ Auto/N/Todo ›, navegación de la ventana de
        # períodos) se movió DENTRO de la tarjeta de Evolución, junto con
        # `gran_float` — ver ese bloque, debajo de `cp_evo_periodo`. Sigue
        # siendo lectura/escritura de `_win_ini`/`_ventana`/etc., calculados
        # arriba: mover DÓNDE se dibuja el control no cambia CUÁNDO corren
        # sus callbacks (Streamlit los corre antes del script, no en el
        # orden de render) ni qué valores ve — Python normal, un solo scope.

    # ── Los Productos del proveedor en foco (arriba a la derecha) ────────
    # Se dibujan al FINAL, aunque se vean arriba: en el modo «por período»
    # usan los períodos de la Evolución. Hasta el 2026-10-01 eran una
    # AgGrid con una tarjeta hermana abajo, «Proveedores de», que mostraba
    # los proveedores del producto clickeado; desde ese día la tabla es
    # HTML y los proveedores se despliegan debajo de cada producto, sin
    # pasar por el servidor (regla #579).
    with _c_prods:
        _tarjeta_productos(
            base, _prov_ver, _prod_evo, gran, _src_evo, _per_evo, _evo_x,
            _etq_evo,
            d_full, (col_prov, col_prod, col_cant, col_valor, col_punit,
                     col_um, col_fecha, col_docu),
            {p: PALETA_CALLAI[i % len(PALETA_CALLAI)]
             for i, p in enumerate(top_provs)},
            _ALTO_RANK)

