"""
graficos.recetaventa — la RECETA de un plato: la mitad de platos de Recetas.

Cada fila de recetaventa.parquet es un ÍTEM de un plato:
    Nomb Plato · Ins Rv · Cantidad · Total
    (plato)      (insumo)  (cant.)   (costo del insumo en el plato)

Desde el 2026-09-28 (regla #556) lo que vive acá es el panel de la receta
que se abre al elegir un producto en la Carta costeada
(`graficos/carta_costeada.py`): la receta, la dona
Costo/Utilidad y el Sankey del plato. Hasta el 2026-09-28 vivía también la
resolución de columnas del «Panorama de compras · platos», que se fue ese
día con Ingredientes clave (regla #559): repartía lo comprado entre los
platos según la receta y no según lo vendido, y sólo reconocía un insumo
si la receta lo nombraba tal cual — el lomo fino, que llega al plato por
un porcionamiento, le salía «sin vincular».

«Composición del plato» y «Costeo Receta Venta» fueron vistas propias hasta
ese día. Medido contra R2: la tabla de Composición era la Carta costeada
filtrada a los platos con receta —425 de 425 con el mismo precio, costo y %
al céntimo, y mismo grupo, subgrupo y última venta—, y Costeo sumaba el
mismo costo por plato sin descartar los inactivos (414 de sus 855 filas;
sus 15 primeros puestos, shots de whisky dados de baja). Lo único propio de
Composición era este panel, y ahora cuelga de la Carta. La historia de las
dos tablas —el ranking que fue gráfico y después tabla, el Sankey que se dio
de baja y volvió como pestaña, el radio «Medir por» que se sacó— está en
`arquitectura.md`, reglas #205, #236, #253, #451, #452 y #556.
"""

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# El ÚNICO uso del paquete en el repo, y está acotado a este Sankey: es el
# único gráfico del proyecto que necesita clic y que
# `st.plotly_chart(on_select=)` no puede escuchar (regla #452).
#
# BAJO `try`, Y NO ES PARANOIA DE MANUAL: el paquete no se toca desde 2021
# y trae su propio frontend bundleado. Un `import` suelto arriba de este
# módulo lo convierte en requisito de ARRANQUE del reporte Recetas entero
# —`graficos/__init__.py` importa este módulo—, así que el día que su
# instalación falle en Cloud no se cae el Sankey: se cae la página, con un
# `ImportError` de una línea y sin nada que pushear (regla #357). Con el
# guard, lo que se pierde es el CLIC, y el Sankey vuelve a dibujarse con
# `st.plotly_chart` — que es exactamente lo que había antes.
try:
    from streamlit_plotly_events import plotly_events
except Exception:                                      # pragma: no cover
    plotly_events = None

from tema import (
    ACENTO, BLANCO, EXITO, GRIS_LINEA, PALETA_SERIES, TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos.base import _card, _resolver
from graficos.recetas_comun import _hex_a_rgba


# ─── El panel de la receta de un plato ─────────────────────────────────────
# Lo abre un clic en la Carta costeada (regla #556); hasta el 2026-09-28 lo
# abría la tabla de «Composición», que es de donde vienen estas medidas:
#
# P.VENTA SALON / CST SALON / %CST SALON son atributos del PLATO, no del
# ítem-insumo: los 850 platos del catálogo tienen un único valor de los tres
# por COD PLATO, repetido en cada fila-insumo (regla #205). Y CST SALON ==
# suma de TOTAL de los ítems de ese plato, sin filtrar por INS ACTIVO: la
# receta de este panel suma lo mismo que el costo de la fila de la Carta
# (medido de nuevo el 2026-09-28: 424 de 425; la excepción es un shot cuyo
# único insumo trae TOTAL 0).
#
# El insumo se lee de INS RV, no de ITEM RV: ITEM RV es el número de LÍNEA
# dentro de la receta (001, 002…), no una identidad de insumo — el mismo
# COD INS aparece como "001" en un plato y "019" en otro. INS RV es el texto
# descriptivo, estable 1:1 contra COD INS.
#
# El panel son dos tarjetas: la receta y, al
# lado, la dona Costo/Utilidad y el Sankey plato→insumo del plato en foco.


# ─── «Simular» ya no vive acá (regla #656) ─────────────────────────────────
# Desde el 2026-09-17 este panel tenía un simulador: la tabla de la receta
# pasaba a `st.data_editor` y se editaban la cantidad y el precio de cada
# línea de PRIMER nivel. Desde el 2026-10-15 lo reemplaza
# `graficos/simulador_plato.py` (una modal con su propio componente): abre las
# recetas base, edita el precio por la unidad de compra, la merma y el peso de
# los porcionados y el precio de venta, y recalcula mientras se escribe. Acá
# quedó la receta de LECTURA, que es lo que la Carta costeada pide.

def _precios_y_pesos(r):
    """Completa una receta con `Precio` unitario y `%` del costo total.

    `Precio` sale de `Costo / Cantidad` (ver el comentario de arriba sobre
    por qué es seguro), y `Costo` se recalcula como `Cantidad * Precio` en
    el camino de vuelta — no al revés."""
    r = r.copy()
    cant = pd.to_numeric(r["Cantidad"], errors="coerce").fillna(0.0)
    costo = pd.to_numeric(r["Costo"], errors="coerce").fillna(0.0)
    r["Cantidad"] = cant
    r["Costo"] = costo
    r["Precio"] = (costo / cant.where(cant > 0)).fillna(0.0)
    total = costo.sum() or 1.0
    r["%"] = costo / total * 100
    return r


def _receta_original(df_f, foco, col_cod_plato, col_ins, col_cant, col_total,
                     col_cod_ins=None, col_factor=None):
    """La receta tal como está en el parquet. `None` si faltan columnas.

    Con `col_cod_ins`/`col_factor` suma `Cod` (el código de almacén del
    insumo) y `Factor` (cuántas unidades de la receta hay en una del
    kardex): con eso la Carta costeada reconoce un insumo que es RECETA BASE
    y la abre proporcionada a lo que usa el plato (regla #572)."""
    if not (col_ins and col_total):
        return None
    items = df_f[df_f[col_cod_plato].astype(str) == foco].reset_index(drop=True)
    r = pd.DataFrame({
        "Insumo": items[col_ins].astype(str),
        "Cantidad": (pd.to_numeric(items[col_cant], errors="coerce").fillna(0.0)
                     if col_cant else 0.0),
        "Costo": pd.to_numeric(items[col_total], errors="coerce").fillna(0.0),
    })
    if col_cod_ins:
        r["Cod"] = items[col_cod_ins].astype("string").fillna("").str.strip()
    if col_factor:
        r["Factor"] = pd.to_numeric(items[col_factor], errors="coerce").fillna(0.0)
    r = _precios_y_pesos(r)
    return r.sort_values("Costo", ascending=False).reset_index(drop=True)


def _panel_receta(df_f, foco, nombre_foco, col_cod_plato, col_ins, col_cant,
                  col_total, col_cod_ins=None, col_factor=None, titulo=True,
                  dibujar_lectura=None):
    """La tarjeta de la receta del plato en foco, de lectura.

    La Carta costeada la pide sin título al pie (`titulo=False`: el nombre ya
    está arriba) y con su propia tabla (`dibujar_lectura(orig)`), que se puede
    clicar para abrir una receta base (regla #572).

    Devuelve `(r, None)`: la receta del parquet y, en el segundo lugar, lo
    que era el costo del borrador del simulador viejo —siempre `None` desde
    la regla #656, y se mantiene para que la dona y el Sankey no cambien de
    firma—."""
    orig = _receta_original(df_f, foco, col_cod_plato, col_ins, col_cant,
                            col_total, col_cod_ins, col_factor)
    rotulo = f"Receta · {nombre_foco}" if nombre_foco else "Receta"
    with _card("rv_comp_receta", rotulo if titulo else ""):
        if orig is None:
            st.info("No se reconoció la columna de insumo (INS RV) o "
                    "de costo (TOTAL) para mostrar la receta.")
            return None, None
        if dibujar_lectura is not None:
            dibujar_lectura(orig)
            return orig, None
        # El alto de SUS filas, hasta MINI: desde que la receta va al
        # costado de la tabla de la carta (regla #570), la de un solo
        # insumo —un trago, un directo con receta— dejaba cinco filas
        # vacías empujando el gráfico hacia abajo. Filas de 35 (las de
        # `st.dataframe` sin `row_height`) y 38 de cabecera y bordes.
        st.dataframe(
            orig[["Insumo", "Cantidad", "Costo", "%"]],
            hide_index=True, use_container_width=True,
            height=alturas.por_filas(len(orig), px_fila=35, extra=38,
                                     minimo=0, rol=alturas.MINI),
            # Anchos fijos que suman ~400: al costado de la tabla el panel
            # mide ~420 a 1366px, y con los anchos automáticos el número
            # del «%» quedaba cortado contra el borde (medido).
            column_config={
                "Insumo": st.column_config.TextColumn(width=150),
                "Cantidad": st.column_config.NumberColumn(format="%.3f",
                                                          width=72),
                "Costo": st.column_config.NumberColumn(format="S/ %.2f",
                                                       width=68),
                "%": st.column_config.ProgressColumn(
                    format="%.1f%%", min_value=0, max_value=100,
                    width=106),
            },
        )
        return orig, None


def _dib_torta_costo_utilidad(neto, costo, pct, foco, costo_sim=None,
                              alto=alturas.MINI):
    """Mini donut Costo/Utilidad del plato en foco: el costo contra
    (precio neto − costo). Si el costo supera al precio neto —pasa de
    verdad: arquitectura.md regla #205 mide bebidas premium con %Costo de
    300–950%, porque el costo es la BOTELLA entera y el precio la COPA— la
    Utilidad da negativa y un donut no puede dibujar eso (una porción no
    puede ser "menos que nada"): se avisa el monto en vez de forzar un
    gráfico que mentiría.

    `neto`, `costo` y `pct` (en %) son los de la fila de la Carta.
    `costo_sim`: el costo del BORRADOR del simulador, cuando hay uno. El
    %Costo se RECALCULA contra el precio neto en vez de usar `pct` — si
    no, mover una cantidad cambiaba el tamaño de la porción y dejaba el
    número del medio quieto, que es justo la contradicción que el velo de
    la app existe para evitar."""
    neto = float(neto or 0.0)
    if costo_sim is None:
        costo = float(costo or 0.0)
        pct = float(pct or 0.0)
    else:
        costo = float(costo_sim)
        pct = (costo / neto * 100) if neto else 0.0
    utilidad = neto - costo
    if costo <= 0 and utilidad <= 0:
        st.info("Sin costo ni precio para graficar.")
        return
    if utilidad < 0:
        st.warning(
            f"Se vende a pérdida: el costo (S/ {costo:,.2f}) supera el "
            f"precio neto (S/ {neto:,.2f}) en S/ {abs(utilidad):,.2f}."
        )
    # `sort=False`: mantiene el orden Costo/Utilidad de `labels` —
    # Plotly, por defecto, reordena las porciones por valor descendente,
    # lo que dejaría el color de cada una saltando de plato en plato.
    fig = go.Figure(go.Pie(
        labels=["Costo", "Utilidad"],
        values=[costo, max(utilidad, 0.0)],
        hole=0.55, sort=False,
        marker=dict(colors=[ACENTO, EXITO]),
        textinfo="label+percent",
        hovertemplate="%{label}: S/ %{value:,.2f}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"{pct:.0f}%<br>costo", showarrow=False,
        font=dict(size=13, color=TEXTO_PRINCIPAL, family="DM Sans, sans-serif"),
    )
    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=11),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"rv_comp_torta_{foco}")


# ─── El Sankey, que acá también es un CONTROL ──────────────────────
# 2026-09-17. `st.plotly_chart(on_select=...)` NO VE un Sankey — medido, y
# no es que el evento no exista: Plotly SÍ emite `plotly_click` sobre un
# enlace, y sobre un nodo también si el `arrangement` no lo deja arrastrar.
# Lo que no pasa es la traducción a selección de Streamlit, que se arma de
# `plotly_selected`/`plotly_deselect` y un Sankey no tiene selección. Se
# verificó con un `go.Bar` de control en la misma página, que sí llegó.
# Detalle en la regla #452.
#
# De ahí `streamlit-plotly-events`, que trae su propio frontend. Tres cosas
# suyas que hay que respetar:
#
#   1. `arrangement="fixed"` Y NO `"snap"`. Con snap el nodo es
#      ARRASTRABLE y el drag se come el clic: medido, cero eventos sobre
#      los nodos y las etiquetas cambiadas de sitio. De paso se arregla algo
#      que ya molestaba — hasta hoy, un clic en una barrita la movía.
#   2. El payload es `{curveNumber, pointNumber}` y NADA MÁS: no dice si se
#      clickeó un nodo o un enlace, y el índice de uno no es el del otro.
#      Por eso el nodo del PLATO va ÚLTIMO y los insumos ocupan 0..N-1: así
#      `link j` apunta a `node j` y las dos lecturas nombran al mismo
#      insumo. Verificado clickeando el nodo y su cinta: los dos devuelven
#      el mismo número.
#   3. Re-emite el ÚLTIMO clic en CADA rerun (la trampa de la #399). Por eso
#      la key lleva un contador que sube cada vez que se procesa uno.
_K_SANKEY_FOCO = "rv_comp_sankey_foco"
_K_SANKEY_NCLIC = "rv_comp_sankey_nclic"


def _indice_clickeado(bruto):
    """El índice del punto clickeado en el Sankey, o `None` si no hubo clic.

    **LO QUE `plotly_events` DEJA EN `session_state` ES UN STRING JSON, NO
    UNA LISTA.** El paquete hace el `loads()` recién en su valor de
    retorno; lo que guarda bajo la key es lo crudo, y su `default` es el
    string `"[]"`. O sea que un `if ev: ev[0].get(...)` —que es lo natural
    de escribir— revienta con `AttributeError` apenas se carga la vista:
    `"[]"` es un string NO vacío, así que entra al `if`, y `ev[0]` es el
    carácter `'['`. Se veía leyendo la fuente del paquete, no probando el
    camino feliz.

    Acepta las dos formas igual (string o lista ya parseada) para no
    depender de un detalle interno de un paquete sin mantenimiento desde
    2021."""
    if isinstance(bruto, str):
        try:
            bruto = json.loads(bruto)
        except ValueError:
            return None
    if not bruto:
        return None
    try:
        return int(bruto[0]["pointNumber"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _dib_sankey_insumo_costo(r, nombre_foco, foco, simulando=False,
                             alto=alturas.MINI):
    """Mini Sankey plato→insumo del plato en foco, ancho del flujo
    proporcional al costo del insumo — mismo cálculo que tenía
    `_sankey_contenedor` (recetas_comun.py, borrada el 2026-08-30 al
    quedarse sin llamadores), reescrito acá a tamaño MINI: ya no es una
    vista propia, es una pestaña de este panel.

    Y desde el 2026-09-17 es además un CONTROL: clic en un insumo (su
    barrita o su cinta) lo enfoca y reclic lo suelta. Los atajos −10 %,
    +10 % y quitar del simulador viejo se fueron con él (regla #656):
    `simulando` se acepta y se ignora."""
    if r is None:
        st.info("No se reconoció la columna de insumo o de costo para "
               "graficar.")
        return
    r_pos = r[r["Costo"] > 0]
    if r_pos.empty:
        st.info("Este plato no tiene insumos con costo positivo para graficar.")
        return
    insumos = r_pos["Insumo"].tolist()
    valores = [float(v) for v in r_pos["Costo"].tolist()]
    n = len(insumos)

    # EL CLIC SE LEE ANTES DE DIBUJAR, con el contador en la key: el
    # componente devuelve el último clic en cada pasada, así que leerlo
    # después de dibujar re-procesaría el mismo gesto para siempre.
    nclic = st.session_state.get(_K_SANKEY_NCLIC, 0)
    key_sankey = f"rv_comp_sankey_{foco}_{nclic}"
    idx = _indice_clickeado(st.session_state.get(key_sankey))
    if idx is not None:
        if 0 <= idx < n:
            elegido = insumos[idx]
            # Toggle: reclic en el mismo insumo lo suelta.
            st.session_state[_K_SANKEY_FOCO] = (
                None if st.session_state.get(_K_SANKEY_FOCO) == elegido
                else elegido)
        else:
            # El nodo del plato (índice n) no es un insumo: suelta el foco.
            st.session_state[_K_SANKEY_FOCO] = None
        st.session_state[_K_SANKEY_NCLIC] = nclic + 1
        nclic += 1
        key_sankey = f"rv_comp_sankey_{foco}_{nclic}"

    en_foco = st.session_state.get(_K_SANKEY_FOCO)
    if en_foco not in insumos:
        en_foco = None

    # EL PLATO VA DE ÚLTIMO — ver el comentario de arriba, punto 2.
    labels = insumos + [nombre_foco or "Plato"]
    base = [PALETA_SERIES[i % len(PALETA_SERIES)] for i in range(n)]
    if en_foco is None:
        node_colors = base + [ACENTO]
        link_colors = [_hex_a_rgba(c, 0.45) for c in base]
    else:
        # Con algo en foco, el resto se apaga en vez de taparse: lo que
        # importa es la comparación, no esconder los otros.
        node_colors = [c if insumos[i] == en_foco else GRIS_LINEA
                       for i, c in enumerate(base)] + [ACENTO]
        link_colors = [_hex_a_rgba(c, 0.75 if insumos[i] == en_foco else 0.12)
                       for i, c in enumerate(base)]

    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        node=dict(
            label=labels, color=node_colors, pad=12, thickness=12,
            line=dict(color=BLANCO, width=0.5),
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=[n] * n, target=list(range(n)),
            value=valores, color=link_colors,
            hovertemplate="%{target.label}<br>S/ %{value:,.2f}<extra></extra>",
        ),
    ))
    fig.update_layout(
        height=alto,
        margin=dict(l=6, r=6, t=6, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=10),
    )
    if plotly_events is None:
        # Sin el componente, el Sankey es el de siempre: se ve igual y no
        # escucha. Se avisa en vez de dejar un gráfico que no responde a un
        # clic que el pie invita a dar.
        st.plotly_chart(fig, use_container_width=True, key=key_sankey)
        st.caption("El clic sobre el Sankey no está disponible "
                   "(falta `streamlit-plotly-events`).")
        return

    plotly_events(fig, click_event=True, hover_event=False, select_event=False,
                  override_height=alto, key=key_sankey)

    if en_foco is None:
        st.caption("Clic en un insumo para enfocarlo.")
        return

    fila = r_pos[r_pos["Insumo"] == en_foco].iloc[0]
    st.caption(f"**{en_foco}** · S/ {float(fila['Costo']):,.2f} · "
               f"{float(fila['%']):.1f} % del costo")


# ─── Lo que usa la Carta costeada ──────────────────────────────────────────
def columnas_receta(df):
    """Las columnas de recetaventa.parquet que usa el panel de la receta,
    resueltas contra `df` (`None` la que falte)."""
    if df is None:
        return {"cod": None, "ins": None, "cant": None, "total": None,
                "cod_ins": None, "factor": None}
    return {
        "cod": _resolver(df, ["COD PLATO", "Cod Plato"]),
        "ins": _resolver(df, ["INS RV", "Ins Rv"]),
        "cant": _resolver(df, ["CANTIDAD", "Cantidad"]),
        "total": _resolver(df, ["TOTAL", "Total"]),
        "cod_ins": _resolver(df, ["COD INS", "Cod Ins"]),
        "factor": _resolver(df, ["FACTOR", "Factor"]),
    }


def receta_del_plato(df_rv, cod, nombre, **opciones):
    """La tarjeta de la receta del plato `cod`, de lectura.

    Devuelve `(r, None)` como `_panel_receta`: la receta del parquet, que
    usan la dona y el Sankey de al lado. «Simular» es otra pieza desde la
    regla #656 (`graficos/simulador_plato.py`). `opciones` van tal cual a
    `_panel_receta` (`titulo`, `dibujar_lectura`)."""
    c = columnas_receta(df_rv)
    if not c["cod"]:
        with _card("rv_comp_receta", "Receta"):
            st.info("No se pudo leer recetaventa.parquet para mostrar la "
                    "receta.")
        return None, None
    return _panel_receta(df_rv, str(cod), nombre, c["cod"], c["ins"],
                         c["cant"], c["total"], c["cod_ins"], c["factor"],
                         **opciones)
