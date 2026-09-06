"""
graficos.movimientos_comun — infraestructura COMPARTIDA entre Requerimientos
y Salidas.

Los dos parquets describen las DOS MITADES de un mismo flujo de stock:
Requerimiento es lo que Almacén Central le entrega a un área de producción
(Cocina, Barra, Pastelería...); Salidas es la baja que esa misma área
registra después (consumo, merma, evento — ver "Tipo Descargo"). Comparten
UN ítem de nav ("Movimientos", ver `grupo_nav` en
navegacion.py::inject_navegacion) con un chip Requerimiento/Salidas
(`_chip_movimientos`, mismo mecanismo que
`graficos/recetas_comun.py::_chip_fuente`: clic en el lado no activo NAVEGA,
no filtra).

Acá hay overlap real de producto: 726 de los 968 productos de Salidas (75%)
también aparecen en Requerimientos, confirmado con DuckDB directo contra R2
real 2026-08-13. Por eso este módulo también trae
`_comparativo_pedido_baja`, una vista que carga AMBOS parquets y los cruza
— precedente de carga cruzada entre dashboards:
`recetas_comun.py::_cargar_flujo_compras` ya carga compras.parquet desde
dentro del dashboard de Recetas.

(Acá decía "a diferencia de Receta Base/Venta, que con 0% overlap NUNCA se
cruzan". Ese 0% era una medición contra la columna equivocada y se corrigió
el 2026-09-04 — los dos parquets de receta SÍ se cruzan, y desde entonces
comparten una sola página. Ver `arquitectura.md` regla #303.)

Dos límites reales del DATO, no del código — no se resuelven con más
columnas, hay que diseñar la vista alrededor de ellos:
  - No hay llave documento-a-documento: `COD REQUERIMIENTO` y `COD SALIDA`
    numeran en secuencias independientes. El cruce es agregado por
    producto/familia/período ("¿cuánto entró vs cuánto se dio de baja en
    este mes?"), nunca "este Requerimiento se resolvió con esta Salida".
  - `salidas.parquet` NO trae el área/sub almacén que originó la baja (solo
    Requerimientos tiene esa columna) — el comparativo no puede desglosar
    por área, solo por producto/familia.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import cargar as _cargar_reporte
from tema import ACENTO, AJUSTE_NEG, AJUSTE_POS, GRIS_TEXTO_SUAVE
from graficos.base import (
    _compras_layout, _compras_truncar, _resolver, selector_fecha_tarjeta,
)
from graficos.compras import _periodo_serie
from graficos import alturas
import franja_fecha


# ─── El rango vigente, en una sola función ─────────────────────────────────
def _rango_vigente():
    """`(inicio, fin_EXCLUSIVO)` del rango canónico del reporte, o None.

    El fin viene como `fin + 1 día` y se compara con `<`, NO con `<=`: las
    dos columnas de fecha de estos parquets traen hora en el 100% de sus
    filas, así que un `<=` contra medianoche se come el último día entero
    del rango. Medido, documentado y corregido en la regla #321 — vive acá
    para que los tres sitios que recortan por fecha en esta página (la
    Evolución, el Comparativo y las secciones de Salidas de
    `graficos/movimientos.py`) no puedan volver a escribirlo distinto.

    Devuelve None cuando la franja todavía no publicó su contexto o el rango
    está a medio elegir; el llamador muestra entonces el histórico entero,
    que es lo que ya hacía.
    """
    ctx = franja_fecha.contexto()
    rango = st.session_state.get(ctx["k_rango"]) if ctx else None
    if not (isinstance(rango, (tuple, list)) and len(rango) == 2 and all(rango)):
        return None
    return (pd.Timestamp(rango[0]),
            pd.Timestamp(rango[1]) + pd.Timedelta(days=1))


# ===========================================================================
# EVOLUCIÓN FUSIONADA — requerido y dado de baja en UNA figura
# ===========================================================================
# 2026-09-05, a pedido: "fusionemos los gráficos evolución de requerimientos
# y salidas en un solo gráfico, y que los muestre como barras agrupadas".
#
# Antes eran DOS evoluciones que nunca se veían juntas: la de Requerimientos
# apilada por estado y la de Salidas apilada por tipo de descargo. Cada una
# contestaba "cómo evolucionó LO MÍO"; para comparar había que cambiar de
# lado con el chip y acordarse de la altura de las barras. Ahora la sección
# "Evolución" de los DOS dashboards dibuja la MISMA figura — el mismo
# criterio que ya tenía "Pedido vs Baja", que también es un ítem de los dos
# rieles.
#
# LO QUE HAY QUE SABER ANTES DE LEER EL GRÁFICO: los dos lados no son del
# mismo orden de magnitud. Medido contra R2 el 2026-09-05, sin anulados y
# sobre el histórico entero: S/ 8.242.254 requerido contra S/ 584.374 dado
# de baja — 14 a 1. En barras AGRUPADAS (lo que se pidió, y lo honesto:
# comparten eje, así que las alturas se pueden comparar) la barra de baja es
# un hilo. Por eso la figura lleva el número ENCIMA de cada barra y el
# caption canta el ratio del período: el dato chico se lee aunque no se vea.
# Un eje secundario lo haría "verse" a costa de mentir sobre el tamaño, que
# es peor.
#
# LOS DOS LADOS SE FILTRAN IGUAL, que es la regla de esta pareja de parquets
# (misma doctrina que `_comparativo_pedido_baja`):
#   · La FECHA sale del rango canónico del reporte —el que escriben la
#     píldora de la franja y el selector de esta tarjeta— y se aplica a los
#     dos por igual.
#   · FAMILIA sí se hereda de los chips: la columna existe en los dos.
#   · SUB ALMACÉN no: `salidas.parquet` no trae el área que dio de baja
#     (confirmado contra R2 el 2026-09-05; sus columnas son LOCAL / TIPO
#     DESCARGO). Filtrar por él dejaría UN solo lado filtrado, que es
#     exactamente lo que invalida una comparación. Cuando hay chips de Sub
#     Almacén puestos, el caption lo dice — la app no puede contradecirse en
#     silencio.


_BANDERA_EVO = "_mov_evo_atajo_pendiente"

_GRANS_EVO = ("Día", "Semana", "Mes", "Año")
_GRAN_EVO_DEFAULT = "Mes"
_K_GRAN_ECO = "mov_evo_gran__eco"
"""Espejo de la granularidad en una clave que NO es de widget.

NO es paranoia: sin él el control vuelve solo a "Mes" cada vez que se toca
la fecha. La cadena es la misma que ya documenta `base.py::selector_escala`
para su propio segmented_control, y acá se reprodujo medida en el navegador
el 2026-09-05 — con "Año" elegido, un clic en el atajo "Año" del panel de
fecha dejaba el DOM mostrando «Año» marcado y a Python dibujando el título
"(mes)":

  clic en el atajo → callback → rerun del FRAGMENT → el fragment aborta en
  su primera línea con `st.rerun(scope="app")` (la escalada que necesita el
  filtro, que vive fuera) → en ese run las pills nunca llegaron a dibujarse
  → y un widget que no se dibuja pierde su estado → en el rerun completo
  nacen de cero y toman `default`.

Es la regla de CLAUDE.md ("un widget que deja de renderizarse pierde su
estado") en el caso que no se ve venir: acá no se esconde nada, lo corta un
`rerun` por la mitad. El espejo es una clave normal de session_state, que
nadie recolecta."""

_CSS_SELECTOR_FECHA = """<style>
/* El selector de fecha de esta tarjeta: `graficos/base.py::
   selector_fecha_tarjeta`, el MISMO widget del Ranking de Proveedores.

   ESTO ES UNA COPIA de las reglas de `cp_sem` (la vista Semanal de Compras)
   reapuntadas al prefijo `mov_evo`, más las tres clases globales del riel
   (`.cp-riel-*`, que las emite `selector_escala`). Se generó mecánicamente
   desde `graficos/compras/_css_proveedor.py`, no a ojo.

   POR QUÉ UNA COPIA Y NO UNA LÍNEA MÁS EN AQUEL BLOQUE, que es lo que se
   hizo las dos veces anteriores (cp_prod el 2026-09-02, cp_sem el
   2026-09-04):

     · Aquel bloque lo inyecta `proveedor.py` con `st.markdown` al
       dibujarse. Movimientos no dibuja nada de Compras, así que sumarle el
       prefijo `mov_evo` allá no alcanzaría: el `<style>` no llegaría nunca
       a esta página.
     · Mudarlo a `estilos/` resolvería la inyección pero lo ADELANTA en la
       cascada —`estilos/` se inyecta al arrancar—, y sus propios
       comentarios documentan peleas de orden ya resueltas contra reglas que
       llegan después ("llegaba después y le ganaba al width:100% de
       aquel"). Reordenar 580 renglones afinados del reporte más usado, para
       una vista de otro reporte, es un mal negocio.

   La deuda es real y está anotada: si cambia el LOOK del selector, son DOS
   sitios. Ver arquitectura.md regla #320, que trae el generador para
   regenerar esta copia en vez de editarla a mano.

   Se copia de `cp_sem` y no de `cp_rank` porque es el mismo caso: fila SIN
   título (el nombre de la sección lo pone el rail), dos ítems —las pills de
   granularidad y el trigger de fecha— repartidos por `space-between`. Y por
   eso la píldora blanca cuelga de la key del TRIGGER y no de la fila: el
   otro hijo es el `stButtonGroup` de la granularidad, que tiene su propio
   look y no quiere ser cuatro píldoras blancas (el aviso de CLAUDE.md sobre
   reglas colgadas del contenedor). */
.st-key-mov_evo_fila {
    position: static !important;
    width: 100% !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 10px !important;
    margin: 0 0 4px !important;
}
.st-key-mov_evo_fila .st-key-mov_evo_escala {
    flex: 0 0 auto !important;
}
.st-key-mov_evo_fila [data-testid="stElementContainer"] {
    width: auto !important;
}
.st-key-mov_evo_fila [data-testid="stElementToolbar"] {
    display: none;
}
.st-key-mov_evo_escala button {
    min-width: 0 !important;
    height: 22px !important;
    min-height: 22px !important;
    padding: 0 10px !important;
    border-radius: 999px !important;
    border: 0.5px solid rgba(0,0,0,0.08) !important;
    background: #ffffff !important;
    color: #5a5a6a !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    line-height: 1 !important;
    box-shadow: 0 1px 2px rgba(15,15,30,0.06) !important;
    transition: background .12s, color .12s !important;
}
.st-key-mov_evo_escala button:hover {
    background: #f0edfe !important;
    color: #4d3fb3 !important;
}
.st-key-mov_evo_escala button {
    padding: 0 10px !important;
    font-size: 12px !important;
    white-space: nowrap !important;
}
.st-key-mov_evo_escala button > div > div:has( [data-testid="stIconMaterial"]) {
    display: none !important;
}
[data-testid="stPopoverBody"]:has(.st-key-mov_evo_escala_panel) {
    width: 290px !important;
    min-width: 290px !important;
    padding: 12px 14px !important;
}
.st-key-mov_evo_esc_gran {
    width: 100% !important;
}
.st-key-mov_evo_esc_gran [data-testid="stButtonGroup"],
.st-key-mov_evo_esc_gran [data-testid="stButtonGroup"] > div {
    display: flex !important;
    width: 100% !important;
    max-width: none !important;
}
.st-key-mov_evo_esc_gran [data-testid="stButtonGroup"] button {
    flex: 1 1 0 !important;
}
.st-key-mov_evo_escala_panel [data-testid="stCaptionContainer"] {
    margin-top: -4px !important;
    font-size: 11px !important;
}
[data-testid="stPopoverBody"]:has([class*="st-key-mov_evo_esc_gran"]) {
    padding-top: 8px !important;
    padding-bottom: 8px !important;
}
[data-testid="stPopoverBody"]:has([class*="st-key-mov_evo_esc_gran"]) [data-testid="stVerticalBlock"] {
    gap: 4px !important;
}
[data-testid="stPopoverBody"]:has([class*="st-key-mov_evo_esc_gran"]) [class*="st-key-mov_evo_atajo_sel"] {
    margin-bottom: 0 !important;
}
.cp-riel-mes {
    text-align: center;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--text-primary);
    line-height: 22px;
}
[class*="st-key-mov_evo_esc_mes_prev"] button,
[class*="st-key-mov_evo_esc_mes_sig"] button {
    min-height: 22px !important;
    height: 22px !important;
    padding: 0 !important;
    line-height: 1 !important;
    font-size: 15px !important;
    border-radius: 7px !important;
}
.cp-riel-regla {
    position: relative;
    height: 11px;
    margin: -22px 6px 0;
}
.cp-riel-regla span {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    font-size: 9px;
    color: var(--text-muted);
    white-space: nowrap;
}
.cp-riel-regla span:first-child {
    transform: translateX(0);
}
.cp-riel-regla span:last-child {
    transform: translateX(-100%);
}
.cp-riel-centrada span:first-child,
.cp-riel-centrada span:last-child {
    transform: translateX(-50%);
}
.cp-riel-regla span.on {
    color: var(--accent);
    font-weight: 600;
}
[class*="st-key-mov_evo_esc_"] [data-testid="stSliderTickBar"] {
    display: none !important;
}
[class*="st-key-mov_evo_esc_meses_"] [data-testid="stSliderThumbValue"],
[class*="st-key-mov_evo_esc_anos_"] [data-testid="stSliderThumbValue"] {
    display: none !important;
}
[class*="st-key-mov_evo_esc_"][class*="_pan"] {
    position: absolute !important;
    width: 1px !important;
    height: 1px !important;
    overflow: hidden !important;
    opacity: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
.st-key-mov_evo_atajo_sel [data-testid="stButtonGroup"] {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 0 !important;
    row-gap: 2px !important;
    width: 100% !important;
    max-width: none !important;
}
.st-key-mov_evo_atajo_sel [data-testid="stButtonGroup"] button {
    min-width: 0 !important;
    min-height: 0 !important;
    height: auto !important;
    padding: 0 !important;
    border: none !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    color: var(--accent-deep) !important;
    font-size: 12px !important;
    font-weight: 400 !important;
    line-height: 1.5 !important;
}
.st-key-mov_evo_atajo_sel [data-testid="stButtonGroup"] button:not(:last-child)::after {
    content: "·";
    color: var(--text-muted);
    padding: 0 7px;
    font-weight: 400;
}
.st-key-mov_evo_atajo_sel [data-testid="stButtonGroup"] button:hover {
    text-decoration: underline !important;
}
.st-key-mov_evo_atajo_sel [data-testid="stButtonGroup"] button[aria-checked="true"],
.st-key-mov_evo_atajo_sel [data-testid="stButtonGroup"] button[aria-pressed="true"] {
    background: transparent !important;
    color: var(--accent-deep) !important;
}
.st-key-mov_evo_atajo_sel {
    width: 100% !important;
    max-width: none !important;
    margin-bottom: 8px !important;
}
</style>"""


def _fig_pedido_vs_baja(periodos, valores_req, valores_sal, *, titulo, pref,
                        con_texto=True):
    """La figura compartida: dos barras por período, requerido y baja.

    UNA sola implementación para los DOS sitios que la dibujan —la sección
    "Evolución" y la primera mitad de "Pedido vs Baja"—, así el look no se
    bifurca. `con_texto` apaga los números sobre las barras cuando hay
    demasiados períodos como para que entren.
    """
    _fmt = pref + "{:,.0f}"
    fig = go.Figure([
        go.Bar(name="Requerido", x=periodos, y=valores_req,
               marker_color=ACENTO,
               text=[_fmt.format(v) for v in valores_req] if con_texto else None,
               textposition="outside", cliponaxis=False,
               hovertemplate="Requerido<br>%{x}: " + pref
                             + "%{y:,.0f}<extra></extra>"),
        go.Bar(name="Dado de baja", x=periodos, y=valores_sal,
               marker_color=GRIS_TEXTO_SUAVE,
               text=[_fmt.format(v) for v in valores_sal] if con_texto else None,
               textposition="outside", cliponaxis=False,
               hovertemplate="Dado de baja<br>%{x}: " + pref
                             + "%{y:,.0f}<extra></extra>"),
    ])
    _compras_layout(fig, alto=alturas.PROTAGONISTA)
    fig.update_layout(
        title=titulo, barmode="group", xaxis_title=None, yaxis_title=None,
        legend=dict(orientation="h", y=-0.2, x=0, font=dict(size=10)),
        uniformtext=dict(mode="hide", minsize=8),
    )
    fig.update_traces(textfont_size=10)
    fig.update_xaxes(type="category")
    return fig


def _cargar_los_dos_lados():
    """Los dos parquets del flujo, normalizados y sin anulados.

    Las listas de candidatos viven ACÁ y no repetidas en cada llamador:
    `_comparativo_pedido_baja` y la Evolución fusionada tienen que mirar
    exactamente las mismas columnas, o las dos vistas de la misma página
    dirían números distintos de la misma cosa.
    """
    req = _cargar_lado(
        "requerimientos.parquet",
        col_fecha_cand=["Fecha Registro", "FECHA REGISTRO"],
        col_cod_cand=["Codigo Producto", "CODIGO PRODUCTO"],
        col_prod_cand=["Nombre Producto", "NOMBRE PRODUCTO"],
        col_fam_cand=["Nombre Familia", "NOMBRE FAMILIA"],
        col_valor_cand=["Valor Item", "VALOR ITEM"],
        col_cant_cand=["Cantidad", "CANTIDAD"],
        col_estado_cand=["Nombre Estado Requerimiento",
                         "NOMBRE ESTADO REQUERIMIENTO"],
        estados_excluir=("ANULADO",),
    )
    sal = _cargar_lado(
        "salidas.parquet",
        col_fecha_cand=["Fecha registro", "FECHA REGISTRO"],
        col_cod_cand=["Cod Producto", "COD PRODUCTO", "Codigo Producto"],
        col_prod_cand=["Nombre Producto", "NOMBRE PRODUCTO"],
        col_fam_cand=["Nombre Familia", "NOMBRE FAMILIA"],
        col_valor_cand=["Valor Neto", "VALOR NETO"],
        col_cant_cand=["Cant Salida", "CANT SALIDA"],
        col_estado_cand=["Nombre Estado Salida", "NOMBRE ESTADO SALIDA"],
        estados_excluir=("ANULADO",),
    )
    return req, sal


@st.fragment
def _evolucion_movimientos(*, fam_sel=(), sub_sel=()):
    """Sección "Evolución" de Requerimientos y de Salidas: la misma figura.

    `@st.fragment` PROPIO y no el de `base.py::seccion_perezosa`, por lo
    mismo que `graficos/compras/semanal.py`: el `st.rerun(scope="app")` que
    dispara el selector de fecha, lanzado desde el fragment de la SECCIÓN,
    aborta el render de esa misma sección — la franja y el resto de la
    página se actualizan y la tarjeta se queda un gesto atrás, con el rango
    viejo en el trigger. Con la tarjeta en un fragment aparte, el que aborta
    es el de adentro y el que redibuja es el de afuera.

    `fam_sel`/`sub_sel` son los chips del dashboard anfitrión. Familia se
    aplica a los dos lados; Sub Almacén no se puede (ver el comentario largo
    de arriba) y por eso se avisa en el caption.
    """
    # Va ANTES de dibujar nada, para no gastar un render que se descarta.
    if st.session_state.pop(_BANDERA_EVO, False):
        st.rerun(scope="app")

    st.markdown(_CSS_SELECTOR_FECHA, unsafe_allow_html=True)

    req, sal = _cargar_los_dos_lados()
    if req is None or sal is None:
        st.info(
            "No se pudo armar la evolución: falta requerimientos.parquet "
            "o salidas.parquet, o no traen las columnas esperadas."
        )
        return

    # ── Cabecera: granularidad + el selector de fecha, en UNA fila ────────
    # `extra` es un CALLABLE y no un widget ya dibujado (en Streamlit el
    # contenedor se elige ENTRANDO en él), de ahí la cajita para sacar el
    # valor: la granularidad se necesita más abajo, en el cuerpo.
    _gran_box = {}

    def _pills_gran():
        _previo = st.session_state.get(_K_GRAN_ECO, _GRAN_EVO_DEFAULT)
        if _previo not in _GRANS_EVO:
            _previo = _GRAN_EVO_DEFAULT
        # `_GRANS_EVO` va CON TILDE porque `_periodo_serie` compara contra
        # estos strings exactos ("Día"/"Año"): sin ellas cae siempre al
        # `return` de Mes, en silencio.
        #
        # El `or _previo` no es sólo para el rerun: `st.pills` devuelve None
        # cuando el usuario des-selecciona, y sin esto eso caía al default en
        # vez de quedarse donde estaba.
        _gran_box["v"] = st.pills(
            "Agrupar por", list(_GRANS_EVO), default=_previo,
            key="mov_evo_gran", label_visibility="collapsed") or _previo
        st.session_state[_K_GRAN_ECO] = _gran_box["v"]

    if selector_fecha_tarjeta("mov_evo", _BANDERA_EVO,
                              extra=_pills_gran) is None:
        # El selector no dibuja NADA si la franja todavía no publicó su
        # contexto, y con él se iría también la granularidad, que es de esta
        # vista y no de la fecha. En ese caso se dibuja suelta.
        _pills_gran()
    gran = _gran_box.get("v") or _GRAN_EVO_DEFAULT

    # ── El MISMO filtro que app.py le aplica al df del anfitrión ─────────
    # Se lee el rango canónico del reporte activo (`rango_franja_<reporte>`),
    # que es lo que escriben tanto la píldora de la franja como el selector
    # de acá arriba. Movimientos no tiene modo Cortes (`cfg["cortes"]` sólo
    # lo trae Ajuste), así que el rango es el único eje temporal y no hay que
    # replicar acá el filtro por conjunto de días.
    _rango = _rango_vigente()
    if _rango:
        _ini, _fin = _rango
        req = req[(req["_fecha"] >= _ini) & (req["_fecha"] < _fin)]
        sal = sal[(sal["_fecha"] >= _ini) & (sal["_fecha"] < _fin)]
    if fam_sel:
        req = req[req["_fam"].isin(fam_sel)]
        sal = sal[sal["_fam"].isin(fam_sel)]

    if req.empty and sal.empty:
        st.info("No hay datos para el rango y los filtros seleccionados.")
        return

    g_req = (pd.DataFrame({"per": _periodo_serie(req["_fecha"], gran),
                           "v": req["_valor"]}).groupby("per")["v"].sum())
    g_sal = (pd.DataFrame({"per": _periodo_serie(sal["_fecha"], gran),
                           "v": sal["_valor"]}).groupby("per")["v"].sum())
    periodos = sorted(set(g_req.index) | set(g_sal.index))
    g_req = g_req.reindex(periodos, fill_value=0)
    g_sal = g_sal.reindex(periodos, fill_value=0)

    fig = _fig_pedido_vs_baja(
        periodos, g_req.values, g_sal.values,
        titulo="Requerido vs dado de baja (" + gran.lower() + ")",
        pref="S/ ",
        # Con muchos períodos los números encima de las barras se pisan. 14
        # es lo que entra cómodo en el ancho de la tarjeta; de ahí para
        # arriba manda el hover.
        con_texto=len(periodos) <= 14)
    st.plotly_chart(fig, use_container_width=True, key="mov_evo_fig")

    _tot_req, _tot_sal = float(g_req.sum()), float(g_sal.sum())
    _pct = "{:.1f}%".format(_tot_sal / _tot_req * 100) if _tot_req else "—"
    _pie = ("En el período: S/ {:,.0f} requerido · S/ {:,.0f} dado de baja · "
            "baja/requerido {}. Sin anulados, y agregado por período: no hay "
            "una llave que una un Requerimiento puntual con la Salida que lo "
            "originó.".format(_tot_req, _tot_sal, _pct))
    if sub_sel:
        # La app no puede contradecirse en silencio: el chip está puesto y
        # esta vista NO lo aplica, así que lo dice.
        _pie += (" El filtro de Sub Almacén no entra acá: salidas.parquet no "
                 "trae el área que dio de baja, y filtrar un solo lado "
                 "invalidaría la comparación.")
    st.caption(_pie)


# ─── Comparativo Pedido vs Baja ─────────────────────────────────────────────
def _cargar_lado(archivo, *, col_fecha_cand, col_cod_cand, col_prod_cand,
                 col_fam_cand, col_valor_cand, col_cant_cand, col_estado_cand,
                 estados_excluir):
    """Carga y normaliza un lado (Requerimientos o Salidas) del comparativo:
    resuelve columnas, filtra estados anulados y devuelve un df con columnas
    de trabajo `_fecha/_cod/_prod/_fam/_valor/_cant`, o None si falta alguna
    columna imprescindible (fecha, código de producto, nombre, y al menos
    una métrica)."""
    df = _cargar_reporte(archivo)
    if df is None or df.empty:
        return None
    col_fecha = _resolver(df, col_fecha_cand)
    col_cod = _resolver(df, col_cod_cand)
    col_prod = _resolver(df, col_prod_cand)
    col_fam = _resolver(df, col_fam_cand)
    col_valor = _resolver(df, col_valor_cand)
    col_cant = _resolver(df, col_cant_cand)
    col_estado = _resolver(df, col_estado_cand)
    if not (col_fecha and col_cod and col_prod and (col_valor or col_cant)):
        return None

    d = df.copy()
    if col_estado and estados_excluir:
        excl = {e.upper() for e in estados_excluir}
        # .fillna ANTES de .astype(str): las columnas que trae DuckDB usan un
        # dtype "str" con NA propio (Arrow-backed) donde .astype(str) NO
        # convierte el nulo a texto — deja un float NaN suelto adentro de una
        # Series "de texto" (mismo tipo de trampa que ya documenta
        # `_activo()` en recetas_comun.py). Sin el fillna, un `sorted()` más
        # abajo sobre esos valores revienta comparando float con str.
        d = d[~d[col_estado].fillna("").astype(str).str.upper().isin(excl)]
    d["_fecha"] = pd.to_datetime(d[col_fecha], errors="coerce")
    d["_cod"] = d[col_cod].fillna("").astype(str).str.strip()
    d["_prod"] = d[col_prod].fillna("").astype(str)
    d["_fam"] = d[col_fam].fillna("Sin familia").astype(str) if col_fam else "Sin familia"
    d["_valor"] = pd.to_numeric(d[col_valor], errors="coerce").fillna(0) if col_valor else 0.0
    d["_cant"] = pd.to_numeric(d[col_cant], errors="coerce").fillna(0) if col_cant else 0.0
    return d.dropna(subset=["_fecha"])


def _comparativo_pedido_baja(*, key_prefix):
    """Vista compartida por Requerimientos y Salidas: cuánto se requirió
    (entrada al área) contra cuánto se dio de baja (salida de esa área)
    después, por producto/familia/período — ver límites del dato en el
    docstring del módulo.

    Trae SUS PROPIOS controles (fecha/familia/granularidad/métrica) en vez
    de heredar el rango o los chips del dashboard "anfitrión": los dos
    lados tienen que quedar filtrados exactamente igual para que el
    comparativo sea válido, y `df_f` del anfitrión solo trae SU parquet ya
    filtrado por SU fecha (mismo criterio que
    `recetas_comun._panorama_compras`, que también trae su propio
    `date_input` en vez de heredar el de la franja)."""
    req, sal = _cargar_los_dos_lados()
    if req is None or sal is None:
        st.info(
            "No se pudo armar el comparativo: falta requerimientos.parquet "
            "o salidas.parquet, o no traen las columnas esperadas."
        )
        return

    c1, c2, c3 = st.columns([2, 2, 1.3])
    with c1:
        rango = st.date_input(
            "Rango (vacío = todo el histórico)", value=(),
            format="DD/MM/YYYY", key=f"{key_prefix}_rango",
        )
    fams = sorted(set(req["_fam"].unique()) | set(sal["_fam"].unique()))
    with c2:
        fam_sel = st.multiselect("Familia", fams, key=f"{key_prefix}_fam")
    with c3:
        metrica = st.radio("Medir por", ["Valor (S/)", "Cantidad"],
                           key=f"{key_prefix}_metrica")
    es_valor = (metrica == "Valor (S/)")
    campo = "_valor" if es_valor else "_cant"
    pref = "S/ " if es_valor else ""

    if len(rango) >= 1:
        req = req[req["_fecha"] >= pd.Timestamp(rango[0])]
        sal = sal[sal["_fecha"] >= pd.Timestamp(rango[0])]
    if len(rango) >= 2:
        # `< fin + 1 día` y no `<= fin`: las dos columnas de fecha traen
        # hora, así que el `<=` contra medianoche perdía el último día
        # entero. Ver el comentario largo de `_evolucion_movimientos`, que
        # trae la medición. Corregido el 2026-09-05 — el bug era de acá
        # desde el principio y salió al contrastar la vista nueva contra R2:
        # las dos vistas viven en la misma página y tienen que decir lo
        # mismo del mismo período.
        _fin = pd.Timestamp(rango[1]) + pd.Timedelta(days=1)
        req = req[req["_fecha"] < _fin]
        sal = sal[sal["_fecha"] < _fin]
    if fam_sel:
        req = req[req["_fam"].isin(fam_sel)]
        sal = sal[sal["_fam"].isin(fam_sel)]

    if req.empty and sal.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    # ── KPIs ────────────────────────────────────────────────────────────
    total_req = float(req[campo].sum())
    total_sal = float(sal[campo].sum())
    pct = f"{total_sal / total_req * 100:.1f}%" if total_req else "—"
    k1, k2, k3 = st.columns(3)
    k1.metric("📥 Requerido", f"{pref}{total_req:,.0f}")
    k2.metric("📤 Dado de baja", f"{pref}{total_sal:,.0f}")
    k3.metric("Baja / Requerido", pct, delta_color="off")
    st.caption(
        "Agregado por producto/familia/período — no hay una llave que una "
        "un Requerimiento puntual con la Salida que lo originó."
    )

    # ── Evolución comparada ─────────────────────────────────────────────
    cg1, _sp = st.columns([1.4, 3.6])
    with cg1:
        gran = st.pills(
            "Agrupar por", ["Día", "Semana", "Mes", "Año"], default="Mes",
            key=f"{key_prefix}_gran", label_visibility="collapsed",
        ) or "Mes"

    g_req = (pd.DataFrame({"per": _periodo_serie(req["_fecha"], gran), "v": req[campo]})
             .groupby("per")["v"].sum())
    g_sal = (pd.DataFrame({"per": _periodo_serie(sal["_fecha"], gran), "v": sal[campo]})
             .groupby("per")["v"].sum())
    todos_per = sorted(set(g_req.index) | set(g_sal.index))
    g_req = g_req.reindex(todos_per, fill_value=0)
    g_sal = g_sal.reindex(todos_per, fill_value=0)

    with st.container(border=True, key="mov_cmp_card_evolucion"):
        # MISMO constructor que la sección "Evolución" (`_fig_pedido_vs_baja`):
        # las dos figuras conviven en la página apilada, así que si el look se
        # bifurca se nota a un scroll de distancia. Acá la métrica puede ser
        # Cantidad, de ahí el `pref` variable.
        fig = _fig_pedido_vs_baja(
            todos_per, g_req.values, g_sal.values,
            titulo=f"Requerido vs dado de baja ({gran.lower()})",
            pref=pref, con_texto=len(todos_per) <= 14)
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_evolucion")

    # ── Ranking por producto: mayor diferencia (requerido − baja) ───────
    g_req_p = req.groupby(["_cod", "_prod"])[campo].sum()
    g_sal_p = sal.groupby(["_cod", "_prod"])[campo].sum()
    idx = g_req_p.index.union(g_sal_p.index)
    tabla = pd.DataFrame({
        "requerido": g_req_p.reindex(idx, fill_value=0),
        "baja": g_sal_p.reindex(idx, fill_value=0),
    }).reset_index()
    tabla["dif"] = tabla["requerido"] - tabla["baja"]
    top = tabla.reindex(tabla["dif"].abs().sort_values(ascending=False).index).head(15)
    top = top.sort_values("dif")

    if not top.empty:
        colores = [AJUSTE_POS if v >= 0 else AJUSTE_NEG for v in top["dif"]]
        with st.container(border=True, key="mov_cmp_card_ranking"):
            fig2 = go.Figure(go.Bar(
                x=top["dif"], y=[_compras_truncar(p, 34) for p in top["_prod"]],
                orientation="h", marker_color=colores,
                text=[f"{pref}{v:,.0f}" for v in top["dif"]],
                textposition="outside", cliponaxis=False,
            ))
            _compras_layout(fig2, alto=alturas.por_filas(
                len(top), px_fila=30, minimo=320, extra=120))
            fig2.update_layout(
                title="Mayor diferencia entre lo requerido y lo dado de baja",
                xaxis_title=None, yaxis_title=None, showlegend=False,
            )
            fig2.update_xaxes(visible=False)
            st.plotly_chart(fig2, use_container_width=True, key=f"{key_prefix}_ranking")
            st.caption(
                "🟢 Se requirió más de lo que se dio de baja en el período. "
                "🔴 Se dio de baja más de lo requerido."
            )
