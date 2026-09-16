"""graficos.ajuste._cascada - vista Cascada: TABLA DE FAMILIAS + DETALLE.

OJO CON EL NOMBRE: la vista se sigue llamando "Cascada" (`?vista=cascada`,
este archivo, el prefijo `ajcas_`) y hace rato que no dibuja una. Cambiarle
el nombre toca la URL, las keys y el CSS; es un cambio aparte.

HISTORIA, porque explica la forma.

  · Hasta el 2026-09-14 era una tabla de filas con barras encadenadas: una
    cascada de verdad, que se partió en tarjetas (reglas #421 a #423).
  · Del 14 al 15 fueron tarjetas por familia: una protagonista con el drill
    y un riel de minis, cada una con el monto grande, un chip, una barra
    desde el cero y un minigráfico de seis cortes (#436 a #439).
  · El 2026-09-16 se rehízo como TABLA + DETALLE (regla #441). Se reportó
    «los gráficos de barras no dicen mucho», y medido era cierto: los cuatro
    canales de cada tarjeta dibujaban el mismo número, el SALDO del corte,
    que es la varianza NETA — faltantes y sobrantes cancelándose. En
    ALIMENTOS el 2 set 2026 el saldo era +6.072 sobre 115.657 de
    diferencias (5,3 %). Tres intentos de dibujar lo que faltaba fracasaron
    por la misma razón: apiladas, las piezas ocupaban más que el detalle
    («no es posible que el KPI ocupe más tamaño que el detalle»);
    comprimidas en una fila, eran motitas de 6px («mucho ruido, casi
    imperceptible»). A 283px por familia un gráfico no entra y un número
    sí. Lo que quedó son NÚMEROS en columnas que se comparan hacia abajo, y
    cada cabecera dice de qué estándar sale («la tabla la leen
    profesionales»).

EL GRANO ES LA LÍNEA (producto × área), no el producto. Es lo que se cuenta
en un inventario, y es lo que hace que la fila de arriba sea la suma de las
listas de abajo: con el producto neteado entre áreas, un faltante en
Almacén Central y un sobrante en Cocina del mismo producto se cancelaban y
desaparecían de las dos listas — el mismo problema del saldo, un nivel más
abajo.
"""

import hashlib

import pandas as pd
import streamlit as st

from tema import (
    AJUSTE_NEG_TEXTO, AJUSTE_POS_TEXTO, GRIS_BORDE, GRIS_TEXTO,
    GRIS_TEXTO_SUAVE, TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos.base import _es_movil, _resolver, _slug
# La ÚNICA del repo: hubo dos y diferían en 48 de 773 nombres (regla #379).
from graficos.compras._etiquetas_proveedor import nombre_propio
# Los tres filtros propios (corte · familia · área) viven en `_comun.py`
# desde el 2026-09-15: el Mapa de calor pidió los mismos, y dos copias de
# "con qué abre la vista" se desincronizan a la primera corrección.
from graficos.ajuste._comun import (
    FAMILIAS_DE_ENTRADA, css_filtros_vista, estado_filtros_vista,
    render_filtros_vista,
)
from tablas.ajuste_familias import (
    ALTO_BARRA_MOVIL, renderizar_desglose_ajuste, renderizar_familias_ajuste,
)
from tablas.compras_semanal import CROMO
from tablas.compras_volatilidad import ALTO_FILA


# Cuántos cortes lista la pestaña «Por corte», del más viejo al elegido.
_N_HISTORIAL = 6
# Cuántas filas reserva una grilla de desglose antes de scrollear por dentro:
# el techo de las tablas-ranking del repo (`drill_tablas.FILAS_RANK`).
_FILAS_DESGLOSE = 8
# Las listas de faltantes y sobrantes muestran menos: comparten la pantalla
# con el resumen y con la fila de pestañas. Medido a 1365x653 con cinco
# familias, seis filas más la TOTAL dejan las tarjetas dentro de la pantalla.
_FILAS_LISTA = 6

# «Productos 80 %»: el corte del análisis ABC (Pareto). Ver
# `tablas.ajuste_familias.FUENTES`.
_PARETO = 0.80

# LA TOLERANCIA DE LA EXACTITUD, declarada. Cero: una línea es exacta sólo si
# su ajuste valorizado es exactamente 0. La práctica usa tolerancias en
# cantidad (±5 % es la típica) o un monto fijo, y el número cambia mucho con
# eso — medido el 2026-09-16 sobre ALIMENTOS: 2,9 % con tolerancia cero,
# 22,7 % con «menos de S/ 5». Se dejó en cero porque no se eligió otra, y
# por eso la cabecera la declara: una exactitud sin su tolerancia no dice
# nada (regla #441). Cambiarla es tocar estas dos líneas.
_TOL_EXACTITUD = 0.0
_TOL_TEXTO = "cero — cualquier diferencia en valorizado cuenta"
_EPS = 1e-9

# Las columnas de stock, para separar las líneas CONTADAS de las que el
# parquet lista en cero y cero: el maestro trae cada producto en cada área,
# y en ALIMENTOS 4.699 de 5.674 filas del 2 set eran eso. Contarlas como
# "exactas" daba 83 % donde había 3 %.
_COL_SISTEMA = ["STOCK AL CIERRE", "Stock al Cierre", "STOCK SISTEMA"]
_COL_FISICO = ["STOCK DECLARADO", "Stock Declarado", "STOCK FISICO"]

_MODOS = ("Por producto", "Por área", "Por corte")

_K_FOCO = "ajuste_cascada_focus"
_K_AREA = "ajcas_filtro_area"
_K_FAMILIA = "ajcas_filtro_familia"
# El corte de ESTA vista. No usa `estado_rango.clave_corte`, que es el
# estado de la FRANJA del reporte: ahi el corte lo comparten las cuatro
# vistas de la categoria "visual" y ademas arrastra el rango, que es la key
# de un `st.date_input`. Aca la vista se filtra sola desde `df_full`, asi
# que le alcanza con recordar que clave de corte eligio. Ver regla #427.
_K_CORTE = "ajcas_corte"
# El modo del detalle, con su ESPEJO: un clic en la tabla de familias hace
# `st.rerun()` antes de que el selector se dibuje, y eso se lleva su estado
# (regla #211). El espejo no es la key del widget, así que sobrevive.
_K_MODO = "ajcas_detalle_modo"
_K_MODO_ECO = "ajcas_detalle_modo__eco"

# UNA KEY POR CONTROL. `st.popover` no emite `st-key-*` propio: el inspector
# y el modo diseno resuelven hacia arriba hasta el `st-key-*` mas cercano,
# que sin esto era la tarjeta ENTERA. Ver arquitectura.md #431.
_K_CTRL = ("ajcas_ctrl_fecha", "ajcas_ctrl_familia", "ajcas_ctrl_area")


# ── Las cuentas (puras: las prueba `test_graficos.py`) ───────────────────

def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def lineas_con_stock(d, col_sistema, col_fisico):
    """Las líneas que tienen stock en el sistema o en el conteo.

    Sin las dos columnas devuelve `d` entero: la vista sigue andando (el
    demo no las trae), y la exactitud se calcula sobre todas las filas."""
    if not (col_sistema and col_fisico and col_sistema in d.columns
            and col_fisico in d.columns):
        return d
    return d[(_num(d[col_sistema]).abs() > _EPS)
             | (_num(d[col_fisico]).abs() > _EPS)]


def productos_pareto(valores, productos, umbral=_PARETO):
    """`(n, de)`: cuántos productos explican `umbral` del total absoluto, y
    de cuántos con diferencia. Suma el absoluto de cada LÍNEA del producto:
    un producto que faltó en un área y sobró en otra pesa las dos cosas."""
    a = valores.abs().groupby(productos).sum()
    a = a[a > _EPS].sort_values(ascending=False)
    if a.empty:
        return 0, 0
    acum = a.cumsum() / a.sum()
    return int((acum < umbral - _EPS).sum()) + 1, len(a)


def metricas(d, col_val, col_prod, col_sistema, col_fisico):
    """Las columnas de una fila de la tabla, para el recorte `d`."""
    v = _num(d[col_val])
    falto = float(v[v < 0].sum())
    sobro = float(v[v > 0].sum())
    n80 = de = None
    if col_prod and col_prod in d.columns:
        n80, de = productos_pareto(v, d[col_prod].astype(str))
    cs = lineas_con_stock(d, col_sistema, col_fisico)
    n_cs = len(cs)
    n_dif = int((_num(cs[col_val]).abs() > _TOL_EXACTITUD + _EPS).sum())
    return {"falto": falto, "sobro": sobro, "total": abs(falto) + sobro,
            "saldo": falto + sobro, "n80": n80, "de": de,
            "lineas": n_cs, "dif": n_dif,
            "exact": (n_cs - n_dif) / n_cs * 100 if n_cs else None}


def resumen_familias(d, grp_col, col_val, col_prod, col_sistema, col_fisico):
    """Una fila por familia, de la que más descuadró a la que menos.

    Una familia sin diferencias pero con líneas contadas SE QUEDA: su 100 %
    de exactitud es un dato. Sólo se va la que no tiene nada."""
    filas = []
    for fam, g in d.groupby(d[grp_col].astype(str), sort=False):
        m = metricas(g, col_val, col_prod, col_sistema, col_fisico)
        if m["total"] > _EPS or m["lineas"]:
            filas.append({"familia": fam, **m})
    return sorted(filas, key=lambda f: (-f["total"], f["familia"]))


def desglose_areas(d, col_area, col_val, col_sistema, col_fisico):
    """La familia en foco partida por área, de la que más descuadró."""
    if not col_area or col_area not in d.columns:
        return []
    filas = []
    for area, g in d.groupby(d[col_area].astype(str).str.strip()):
        m = metricas(g, col_val, None, col_sistema, col_fisico)
        if m["total"] > _EPS:
            filas.append({"area": area, **m})
    return sorted(filas, key=lambda f: (-f["total"], f["area"]))


def desglose_cortes(d_hist, cortes, col_area, col_val, col_sistema,
                    col_fisico):
    """Los últimos cortes de la familia en foco, del más viejo al elegido.

    «Áreas contadas» son las que tienen alguna línea con stock: es lo que
    deja ver un conteo parcial. El 16-18 ago 2026 se contaron 2 áreas de
    13, y su sobrante da cero en las cinco familias; sin esta columna, esa
    fila se lee como una mejora."""
    filas = []
    for c in cortes:
        g = d_hist[d_hist["_corte_clave"] == c["clave"]]
        m = metricas(g, col_val, None, col_sistema, col_fisico)
        cs = lineas_con_stock(g, col_sistema, col_fisico)
        m["areas"] = (int(cs[col_area].astype(str).str.strip().nunique())
                      if col_area and col_area in cs.columns else 0)
        filas.append({"corte": c["etiqueta_anio"], **m})
    return filas


def productos_espejo(d, col_prod, col_area, col_val):
    """`(n, faltó, sobró)` de los productos que en el MISMO corte faltaron
    en un área y sobraron en otra.

    Es un conteo, no una conclusión: la pantalla no dice qué significa.
    Sobre ALIMENTOS del 2 set 2026, el caso más grande fue Almacén Central
    contra Cocina (regla #441)."""
    if not (col_prod and col_area and col_prod in d.columns
            and col_area in d.columns):
        return 0, 0.0, 0.0
    neto = _num(d[col_val]).groupby(
        [d[col_prod].astype(str), d[col_area].astype(str).str.strip()]).sum()
    neg = neto[neto < -_EPS]
    pos = neto[neto > _EPS]
    ambos = (set(neg.index.get_level_values(0))
             & set(pos.index.get_level_values(0)))
    if not ambos:
        return 0, 0.0, 0.0
    return (len(ambos),
            float(neg[neg.index.get_level_values(0).isin(ambos)].sum()),
            float(pos[pos.index.get_level_values(0).isin(ambos)].sum()))


def _clave(*partes):
    """Sufijo corto y estable para la key de una grilla (el de Semanal)."""
    txt = "|".join(str(p) for p in partes)
    return hashlib.md5(txt.encode("utf-8")).hexdigest()[:10]


def _alto_grilla(n_filas):
    """Alto de una grilla de la vista (`n_filas` cuenta la fila TOTAL si la
    hay). En el celular suma la barra horizontal, que ahí vuelve a verse
    (`tablas.ajuste_familias._css`)."""
    return alturas.por_filas(
        max(1, n_filas), px_fila=ALTO_FILA,
        extra=CROMO + (ALTO_BARRA_MOVIL if _es_movil() else 0), minimo=0)


def _atar_alto(key, alto):
    """El alto de una grilla que CONSERVA su key, atado desde el documento.

    st_aggrid le reporta a Streamlit un alto medido que termina INLINE sobre
    el iframe y le gana al `height=`; en una grilla que no se estrena queda
    el que reportó la primera vez. Los dos nodos, porque Streamlit lo
    escribe en los dos. Ver regla #410."""
    st.markdown(
        f"<style>div.st-key-{key}, div.st-key-{key} iframe "
        f"{{ height: {alto}px !important; }}</style>",
        unsafe_allow_html=True)


def _css():
    _CSS_FILTROS = css_filtros_vista("ajcas_ctrl_", "ajcas_corte_")
    return f"""<style>
    /* ── Buscador de Faltantes/Sobrantes (2026-08-08, a pedido): reemplaza
       el titulo fijo -- filtra los productos de esa zona en vez de solo
       etiquetarla. data-testid="stTextInputRootElement" es la caja real;
       hay que aplanar la caja, no el <input>. */
    div[class*="st-key-ajcas_buscar_"] [data-testid="stTextInputRootElement"] {{
        height: auto !important; background: transparent !important;
        border: none !important; border-radius: 0 !important;
        border-bottom: 1px solid {GRIS_BORDE} !important;
        transition: border-color .12s ease; }}
    div[class*="st-key-ajcas_buscar_neg_"] [data-testid="stTextInputRootElement"]:focus-within {{
        border-bottom-color: {AJUSTE_NEG_TEXTO} !important; }}
    div[class*="st-key-ajcas_buscar_pos_"] [data-testid="stTextInputRootElement"]:focus-within {{
        border-bottom-color: {AJUSTE_POS_TEXTO} !important; }}
    div[class*="st-key-ajcas_buscar_"] [data-testid="stTextInputRootElement"] input {{
        height: auto !important; padding: 2px 2px 4px 2px !important;
        font-size: 11.5px !important; color: {TEXTO_PRINCIPAL} !important; }}
    div[class*="st-key-ajcas_buscar_"] [data-testid="stTextInputRootElement"] input::placeholder {{
        color: {GRIS_TEXTO_SUAVE} !important; opacity: 1 !important; }}
    /* ── SUBIR LA VISTA ───────────────────────────────────────────────
       -108px deja la primera tarjeta en y=40, a 4px de la franja fija de
       arriba: 96 son el `row-gap` de seis hijos de altura cero (el rail y
       la nav, que pintan `fixed`) y 12 se los come al `padding-top` del
       contenedor. Es el PISO: la franja es opaca y cualquier valor mayor
       mete la tarjeta debajo. MARGIN y no transform: un transform en un
       ancestro captura a los hijos `fixed` (regla #156), y el popover de
       los filtros lo es. Ver arquitectura.md regla #426. */
    div[class*="st-key-aj_sec_cascada"] {{
        margin-top: -108px !important; }}

    /* ── LOS TRES CONTROLES, EN LA FILA DE ARRIBA DE LA TABLA ────────
       Las reglas del trigger y de la lista de cortes las escribe
       `_comun.css_filtros_vista`, scopeadas al prefijo de key de ESTA
       vista -- el Mapa de calor usa las mismas con el suyo. */
    {_CSS_FILTROS}

    /* ── LAS DOS TARJETAS ─────────────────────────────────────────────
       Blancas con `var(--bg-card)` (regla #1: el color sale de la paleta),
       el mismo borde gris y el mismo radio. */
    div[class*="st-key-ajcas_card_"] {{
        background: var(--bg-card) !important;
        border: 1px solid {GRIS_BORDE} !important;
        border-radius: 12px !important;
        padding: 12px 16px 14px 16px !important;
        gap: 8px !important; }}

    /* El CUERPO que las contiene es transparente y solo aporta el hueco.
       Mismo idioma que `compras_vap_cuerpo` (#420): las tarjetas son las
       superficies, el cuerpo es el aire entre ellas. */
    div[class*="st-key-ajcas_cuerpo"] {{
        background: transparent !important; border: none !important;
        gap: 11px !important; }}
    div[class*="st-key-ajcas_cuerpo"] > div {{ border: none !important; }}

    /* El iframe de una grilla nace `display: inline` y su contenedor le
       suma debajo el hueco de los descendentes (regla #440). */
    div[class*="st-key-ajcas_grid_"] iframe {{ display: block !important; }}

    /* El selector del detalle, a la talla de los rotulos de la tarjeta y
       no a la del cuerpo -- el mismo recorte que el de Volatilidad. */
    div.st-key-{_K_MODO} [data-testid="stButtonGroup"] button {{
        min-height: 26px !important; height: 26px !important;
        padding: 0 10px !important; font-size: 12px !important; }}
    /* AL BORDE DERECHO, que es el de las tarjetas de abajo. El contenedor
       con la key mide lo que su contenido (249px) y su columna lo apoya a la
       izquierda: medido, terminaba en 1151 con la fila en 1323. Un
       `justify-content` sobre el `stButtonGroup` no mueve nada, porque ese
       nodo ya mide lo mismo que sus botones; lo que se corre es el
       contenedor, con margen automático. */
    div.st-key-{_K_MODO} {{ margin-left: auto !important; }}
    </style>"""


def _graf_waterfall_ajuste(df, col_familia, col_area, col_ajuste_val,
                           col_producto=None, col_valorizado=None,
                           col_cantidad=None, df_full=None, col_fecha=None,
                           col_unidad=None):
    """Resumen de las familias del corte (tabla) y detalle de la que está en
    foco, cada uno en su tarjeta.

    `df` llega SIN los chips del reporte y la vista se filtra sola desde
    `df_full`: corte propio, área y familia propias (`_comun`). Las columnas
    de stock no llegan por parámetro: se resuelven acá, sobre `df`, porque
    cambiar la firma obligaría a tocar `__init__` en el mismo push.

    `col_valorizado` ya no se usa (era el «% de su stock» de la tarjeta);
    queda en la firma porque la pasa el dispatcher.

    `col_unidad` es la unidad de Kardex por producto (Kg, Und, Lt...) -- se
    usa solo en el texto de las listas; si no se resuelve, la cantidad va
    sin sufijo (nunca el generico "und").
    """
    grp_col = col_familia or col_area
    if not grp_col:
        st.info("Se necesita columna de familia o área para esta vista.")
        return

    st.markdown(_css(), unsafe_allow_html=True)

    # ESTADO PRIMERO, WIDGETS DESPUES: los controles van en la fila de arriba
    # de la tabla, y la tabla sale de aplicar esos mismos filtros.
    _est = estado_filtros_vista(
        df, df_full, col_fecha, col_familia, col_area, col_ajuste_val,
        k_corte=_K_CORTE, k_familia=_K_FAMILIA, k_area=_K_AREA,
        familias=FAMILIAS_DE_ENTRADA, historial=_N_HISTORIAL)
    d = _est["d"]
    col_sis = _resolver(d, _COL_SISTEMA)
    col_fis = _resolver(d, _COL_FISICO)
    fams = (resumen_familias(d, grp_col, col_ajuste_val, col_producto,
                             col_sis, col_fis) if not d.empty else [])

    with st.container(key="ajcas_cuerpo"):
        with st.container(border=True, key="ajcas_card_resumen"):
            # columnas-internas: los tres filtros y la cobertura del corte.
            # El reparto de los filtros es el de antes (tres de ~156px, que
            # es lo que pide "todas las áreas", regla #434).
            _cf = st.columns([1, 1, 1, 3.4], gap="small",
                             vertical_alignment="center")
            render_filtros_vista([c.container(key=k)
                                  for c, k in zip(_cf, _K_CTRL)], _est)
            if not fams:
                # Sin datos la tarjeta se dibuja IGUAL: sin ella se irían
                # los tres controles y no habría forma de deshacer el
                # filtro que la dejó vacía.
                st.caption("Ninguna familia tiene líneas con estos filtros.")
                return
            with _cf[3]:
                st.markdown(_cobertura(d, _est, col_area, col_sis, col_fis),
                            unsafe_allow_html=True)

            nombres = [f["familia"] for f in fams]
            foco = st.session_state.get(_K_FOCO)
            if foco not in nombres:
                # Sin foco válido, la que más descuadró: la tabla abre
                # ordenada por esa columna y el detalle nunca queda vacío.
                foco = nombres[0]
                st.session_state[_K_FOCO] = foco
            _clic = _tabla_familias(d, fams, foco, _est, grp_col,
                                    col_ajuste_val, col_producto,
                                    col_sis, col_fis)
            if _clic and _clic != foco and _clic in nombres:
                # El rerun hace falta: la tabla ya se dibujó con la marca
                # vieja (regla #440).
                st.session_state[_K_FOCO] = _clic
                st.rerun()

        # El detalle dibuja sus propias tarjetas: una en «Por área» y «Por
        # corte», DOS en «Por producto» (faltantes | sobrantes).
        _detalle(foco, d, _est, grp_col, col_ajuste_val, col_producto,
                 col_area, col_cantidad, col_unidad, col_sis, col_fis)


def _cobertura(d, est, col_area, col_sis, col_fis):
    """Cuánto abarcó el conteo del corte, a la derecha de los filtros.

    Los totales NO van acá: los dice la fila TOTAL de la tabla, y el mismo
    número en dos sitios de la misma tarjeta es la regla #238 al revés."""
    cs = lineas_con_stock(d, col_sis, col_fis)
    _txt = f"{len(cs):,} líneas con stock"
    if col_area and col_area in d.columns:
        _n = cs[col_area].astype(str).str.strip().nunique()
        _dh = est.get("d_historial")
        _m = (lineas_con_stock(_dh, col_sis, col_fis)[col_area]
              .astype(str).str.strip().nunique()
              if _dh is not None and col_area in _dh.columns else _n)
        _txt = (f"{_n} de {max(_m, _n)} áreas con stock"
                f"&nbsp;&nbsp;·&nbsp;&nbsp;{_txt}")
    return (f"<div style='text-align:right;font-size:11.5px;"
            f"color:{GRIS_TEXTO}' title='Las áreas se cuentan sobre los "
            f"últimos {_N_HISTORIAL} cortes. Una línea con stock tiene stock "
            f"en el sistema o en el conteo.'>{_txt}</div>")


def _tabla_familias(d, fams, foco, est, grp_col, col_val, col_prod,
                    col_sis, col_fis):
    """La tabla del resumen. Devuelve la familia seleccionada, o None."""
    _tot = metricas(d, col_val, col_prod, col_sis, col_fis)

    # SIN REDONDEAR ACÁ: el formato de la grilla redondea al entero, y
    # redondear antes a dos decimales cambia el resultado. Medido: el saldo
    # de ALIMENTOS del 2 set es 6.072,498 -> 6.072,50 -> «+S/ 6,073».
    def _fila(nom, m, sel):
        return {"familia": nom, "falto": m["falto"], "sobro": m["sobro"],
                "total": m["total"], "saldo": m["saldo"], "n80": m["n80"],
                "exact": m["exact"], "__de": m["de"], "__sel": sel}

    tp = pd.DataFrame([
        {**_fila(nombre_propio(f["familia"]), f, f["familia"] == foco),
         "__crudo": f["familia"]}
        for f in fams])
    # «TOTAL» no pasa por `nombre_propio`: no es un nombre del ERP.
    total = _fila("TOTAL", _tot, False)
    total.pop("__sel")
    # La key lleva los DATOS y no el foco: una grilla que se estrena en cada
    # clic le borraría al usuario el orden que eligió (docstring de
    # `tablas.ajuste_familias`).
    _key = "ajcas_grid_familias_" + _clave(
        (est["corte"] or {}).get("clave"), est["sel_fam"], est["sel_area"])
    _alto = _alto_grilla(len(tp) + 1)
    _atar_alto(_key, _alto)
    return renderizar_familias_ajuste(tp, total, _alto, _key, _TOL_TEXTO,
                                      movil=_es_movil())


def _detalle(foco, d, est, grp_col, col_val, col_prod, col_area,
             col_cantidad, col_unidad, col_sis, col_fis):
    """Abajo del resumen: la familia en foco, en tres cortes posibles.

    MISMO FORMATO QUE LA TABLA DE ARRIBA (2026-09-16, a pedido: «darle
    similar formato que la de arriba, manteniendo sus dos tarjetas
    independientes»). Hasta ese día «Por producto» eran dos listas HTML con
    barritas dentro de UNA tarjeta, con el selector flotando a media fila.
    Ahora son dos grillas iguales a la del resumen, cada una en su tarjeta,
    y el título con las pestañas va en su propia fila, sin tarjeta. Ver
    regla #442."""
    _det = d[d[grp_col].astype(str) == foco]
    _m = metricas(_det, col_val, col_prod, col_sis, col_fis)

    with st.container(key="ajcas_detalle_cab"):
        # columnas-internas: el título del detalle y su selector
        _ct, _cm = st.columns([3, 1.6], vertical_alignment="center")
        with _ct:
            st.markdown(
                f"<div style='display:flex;align-items:baseline;gap:10px;"
                f"flex-wrap:wrap;padding-left:2px'>"
                f"<span style='font-size:12px;font-weight:700;"
                f"letter-spacing:.05em;text-transform:uppercase;"
                f"color:{TEXTO_PRINCIPAL}'>Detalle · {nombre_propio(foco)}"
                f"</span><span style='font-size:11.5px;color:{GRIS_TEXTO}'>"
                f"{_m['dif']:,} de {_m['lineas']:,} líneas con stock "
                f"cerraron con diferencia</span></div>",
                unsafe_allow_html=True)
        with _cm:
            _previo = st.session_state.get(_K_MODO_ECO, _MODOS[0])
            modo = st.segmented_control(
                "Detalle por", _MODOS, default=_previo, key=_K_MODO,
                label_visibility="collapsed") or _previo
            st.session_state[_K_MODO_ECO] = modo

    _id = _clave((est["corte"] or {}).get("clave"), est["sel_fam"],
                 est["sel_area"], foco)
    if modo == "Por producto":
        _listas(foco, _det, _id, col_val, col_prod, col_area, col_cantidad,
                col_unidad)
        return

    with st.container(border=True, key="ajcas_card_drill"):
        if modo == "Por área":
            _por_area(_det, _m, _id, col_val, col_prod, col_area,
                      col_sis, col_fis)
        else:
            _por_corte(foco, est, _id, grp_col, col_val, col_area,
                       col_sis, col_fis)


def _titulo_tarjeta(texto, n, color):
    """El rótulo de una tarjeta de lista: el nombre y cuántas líneas trae
    — sin el número, una tabla que scrollea no deja ver si son 12 o 400."""
    return (f"<div style='display:flex;align-items:baseline;gap:7px;"
            f"padding-left:2px'><span style='font-size:12px;font-weight:700;"
            f"letter-spacing:.05em;text-transform:uppercase;color:{color}'>"
            f"{texto}</span><span style='font-size:11.5px;"
            f"color:{GRIS_TEXTO_SUAVE}'>{n:,} líneas</span></div>")


def _listas(foco, _det, _id, col_val, col_prod, col_area, col_cantidad,
            col_unidad):
    """«Por producto»: faltantes y sobrantes, cada uno en su tarjeta.

    Una fila por LÍNEA (producto × área): así la fila TOTAL de faltantes es
    el «Faltó» de la tabla de arriba y la de sobrantes su «Sobró». Con el
    producto neteado entre áreas, el mismo producto faltando en una y
    sobrando en otra se cancelaba y no aparecía en ninguna.

    TODAS las líneas, no un top-N: la tabla se ordena, y un top-N ordenable
    miente (ordenar por cantidad reordena esos N, no las líneas). El scroll
    lo hace la grilla (regla #403). El buscador filtra ANTES de dibujar, así
    que una línea que calza aparece aunque esté al fondo."""
    if not col_prod or col_prod not in _det.columns:
        with st.container(border=True, key="ajcas_card_drill"):
            st.caption("No se encontró la columna de producto.")
        return
    _has_area = bool(col_area and col_area in _det.columns
                     and col_area != col_prod)
    _has_cant = bool(col_cantidad and col_cantidad in _det.columns)
    _has_um = bool(col_unidad and col_unidad in _det.columns
                   and col_unidad != col_prod)

    _vacia = pd.Series("", index=_det.index)
    _base = pd.DataFrame({
        "producto": _det[col_prod].astype(str).str.strip(),
        "area": (_det[col_area].astype(str).str.strip() if _has_area
                 else _vacia),
        "valor": _num(_det[col_val]),
        "cantidad": (_num(_det[col_cantidad]) if _has_cant
                     else pd.Series(0.0, index=_det.index)),
        "um": (_det[col_unidad].astype(str).str.strip() if _has_um
               else _vacia),
    })
    _base["um"] = _base["um"].mask(
        _base["um"].str.lower().isin(("nan", "none")), "")
    _g = (_base.groupby(["producto", "area"], as_index=False)
          .agg(valor=("valor", "sum"), cantidad=("cantidad", "sum"),
               um=("um", "first"))
          .rename(columns={"um": "__um"}))

    # columnas-internas: las dos listas, cada una en su tarjeta
    _ca, _cb = st.columns(2, gap="small")
    for _col, signo, nombre, clase, orden, color, k in (
            (_ca, -1, "Faltantes", "falto", "asc", AJUSTE_NEG_TEXTO, "neg"),
            (_cb, 1, "Sobrantes", "sobro", "desc", AJUSTE_POS_TEXTO, "pos")):
        _pool = _g[_g["valor"] * signo > _EPS]
        with _col, st.container(border=True, key=f"ajcas_card_{k}"):
            # columnas-internas: el rótulo de la lista y su buscador
            _t, _b = st.columns([1, 1.3], vertical_alignment="center")
            with _t:
                st.markdown(_titulo_tarjeta(nombre, len(_pool), color),
                            unsafe_allow_html=True)
            with _b:
                _q = st.text_input(
                    f"Buscar en {nombre.lower()}",
                    key=f"ajcas_buscar_{k}_{_slug(foco)}",
                    placeholder="Buscar producto o área…",
                    label_visibility="collapsed").strip().lower()
            if _q:
                _txt = (_pool["producto"].str.lower() + " "
                        + _pool["area"].str.lower())
                _pool = _pool[_txt.str.contains(_q, regex=False)]
            if _pool.empty:
                st.caption("Sin coincidencias." if _q
                           else f"Sin {nombre.lower()} en esta familia.")
                continue
            tp = _pool.sort_values("valor", ascending=signo < 0).assign(
                __sel=False)
            _cols = [("producto", "Producto", "nombre")]
            if _has_area:
                _cols.append(("area", "Área", "texto"))
            if _has_cant:
                _cols.append(("cantidad", "Cantidad", "cantidad"))
            _cols.append(("valor", "Valor", clase, orden))
            # La key lleva el foco y el corte, NO la búsqueda: escribir no
            # estrena grilla, así el orden elegido sobrevive a cada letra.
            _key = f"ajcas_grid_{k}_{_id}"
            _alto = _alto_grilla(min(_FILAS_LISTA, len(tp)) + 1)
            _atar_alto(_key, _alto)
            renderizar_desglose_ajuste(
                tp, _cols, _alto, _key, movil=_es_movil(),
                total={"producto": "TOTAL",
                       "valor": float(tp["valor"].sum())})


def _por_area(_det, _m, _id, col_val, col_prod, col_area, col_sis, col_fis):
    """«Por área»: la familia en foco partida por área."""
    filas = desglose_areas(_det, col_area, col_val, col_sis, col_fis)
    if not filas:
        st.caption("Sin áreas con diferencia en esta familia.")
        return
    tp = pd.DataFrame([{
        "area": f["area"], "falto": f["falto"], "sobro": f["sobro"],
        "total": f["total"], "saldo": f["saldo"], "lineas": f["dif"],
        "__sel": False} for f in filas])
    _key = f"ajcas_grid_areas_{_id}"
    _alto = _alto_grilla(min(_FILAS_DESGLOSE, len(tp)) + 1)
    _atar_alto(_key, _alto)
    renderizar_desglose_ajuste(
        tp, [("area", "Área", "nombre"), ("falto", "Faltó", "falto"),
             ("sobro", "Sobró", "sobro"),
             ("total", "Faltó + sobró", "total"),
             ("saldo", "Saldo", "saldo"),
             ("lineas", "Líneas con dif.", "entero")],
        _alto, _key, movil=_es_movil(),
        # La misma fila TOTAL que la familia en la tabla de arriba: las
        # áreas suman exactamente eso.
        total={"area": "TOTAL", "falto": _m["falto"], "sobro": _m["sobro"],
               "total": _m["total"], "saldo": _m["saldo"],
               "lineas": _m["dif"]})
    _n, _neg, _pos = productos_espejo(_det, col_prod, col_area, col_val)
    if _n:
        st.caption(
            f"{_n} producto{'s' if _n != 1 else ''} faltaron en un área y "
            f"sobraron en otra en este mismo corte: "
            f"−S/ {abs(_neg):,.0f} contra +S/ {_pos:,.0f}.")


def _por_corte(foco, est, _id, grp_col, col_val, col_area, col_sis, col_fis):
    """«Por corte»: los últimos cortes de la familia en foco. Sin fila
    TOTAL: sumar seis cortes no es una medida de nada."""
    _dh = est.get("d_historial")
    _cortes = est.get("historial_cortes") or []
    if _dh is None or not _cortes:
        st.caption("Sin historial de cortes para comparar.")
        return
    _dh = _dh[_dh[grp_col].astype(str) == foco]
    filas = desglose_cortes(_dh, _cortes, col_area, col_val, col_sis, col_fis)
    _ult = len(filas) - 1
    tp = pd.DataFrame([{
        "corte": f["corte"], "areas": f["areas"], "lineas": f["dif"],
        "falto": f["falto"], "sobro": f["sobro"], "saldo": f["saldo"],
        "__sel": i == _ult} for i, f in enumerate(filas)])
    _key = f"ajcas_grid_cortes_{_id}"
    _alto = _alto_grilla(min(_FILAS_DESGLOSE, len(tp)))
    _atar_alto(_key, _alto)
    renderizar_desglose_ajuste(
        tp, [("corte", "Corte", "nombre"),
             ("areas", "Áreas con stock", "entero"),
             ("lineas", "Líneas con dif.", "entero"),
             ("falto", "Faltó", "falto"), ("sobro", "Sobró", "sobro"),
             ("saldo", "Saldo", "saldo")],
        _alto, _key, movil=_es_movil())
