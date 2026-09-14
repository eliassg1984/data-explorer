"""graficos.ajuste._cascada - vista Cascada: UNA TARJETA POR FAMILIA.

OJO: NO es un grafico Plotly. Son tarjetas de Streamlit con HTML adentro.

HISTORIA, porque explica la forma. Hasta el 2026-09-14 esto era una TABLA
de filas (st.columns + HTML) con una columna de barras encadenadas que
dibujaban una cascada de verdad: cada barra arrancaba donde terminaba la
anterior. Se rehizo por tres cosas medidas en la app corriendo:

  1. El chevron que abria el drill media 16 x 36 px dentro de una fila de
     1081 x 46 -- el 1,16 % de la superficie. La fila ENTERA se pintaba de
     lavanda al pasar el mouse (o sea, prometia ser clickeable) pero el
     cursor seguia siendo flecha y el 98,84 % no hacia nada. Reportado como
     "hago clic y a veces no pasa nada". Ver arquitectura.md regla #421.
  2. Los tres tintes de renglon por severidad (critico/alerta/sobrante)
     estaban al 8-9 % de opacidad: compuestos sobre el blanco de la card
     daban #FCF4F4, #F7F3EE y #F4F8F5. Indistinguibles entre si. El color
     no era poco intuitivo: no llegaba a verse. Ver regla #422.
  3. El tinte, la pastilla de Estado, el "65 % del total" y el largo de la
     barra codificaban TODOS el mismo numero (el peso de la familia en el
     ajuste total). Cuatro canales para una variable, mientras el dato que
     si alarma -- cuanto se fue contra el stock que la familia tiene --
     vivia en una columna sin rotulo, como "-177.9 %".

La cascada encadenada no sobrevive a la particion en tarjetas: encadenar
exige un eje continuo compartido. La reemplaza una barra desde el CERO, con
el cero en el mismo sitio horizontal en todas las tarjetas, asi que los
largos se siguen comparando de un vistazo. El orden entre familias era
arbitrario igual (se ordenaba por valor con signo), asi que el acumulado no
contaba ninguna historia.

DISPOSICION: protagonista + riel. La familia con foco ocupa el bloque
grande con sus faltantes y sobrantes; el resto queda como mini-tarjetas
apiladas al costado. Se eligio sobre "va primero" porque el lugar del
protagonista NO se mueve -- solo cambia lo que tiene adentro -- y con
reruns de 3-6s un reordenamiento de seis tarjetas sin animacion se lee como
que la pagina se rompio. Animarlo no es opcion: cada rerun crea nodos DOM
nuevos y `st.markdown` no ejecuta <script>. Ver regla #423.
"""


import streamlit as st

from tema import (
    ACENTO, GRIS_BORDE, GRIS_FONDO,
    TEXTO_PRINCIPAL,
    BLANCO, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
    LAVANDA_SELECCION,
    AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_POS, AJUSTE_POS_TEXTO,
    AJUSTE_CRIT_FONDO, AJUSTE_SOB_FONDO,
)
from graficos.base import (
    _slug, filtro_pills, sembrar_seleccion,
)


# Con que familias ABRE la vista. A pedido (2026-09-14): "alimentos,
# bebidas, vinos y envases" -- o sea todas menos COSTOS PRODUCCION, que es
# el 65 % del ajuste del ultimo corte y cuyas areas mas pesadas (GASTOS,
# LIMPIEZA Y MANTENIMIENTO) tienen valorizado CERO, asi que su ratio contra
# stock propio no significa nada.
#
# Es un DEFAULT, no un filtro fijo: la familia sigue estando en el
# compartimento a un clic de distancia. Ver la memoria del proyecto sobre
# "fijo en X es un default".
FAMILIAS_DE_ENTRADA = (
    "ALIMENTOS",
    "BEBIDAS CON ALCOHOL",
    "BEBIDAS SIN ALCOHOL",
    "VINOS Y ESPUMANTES",
    "ENVASES Y EMBALAJES",
)

_TOPN_DRILL = 30
_K_FOCO = "ajuste_cascada_focus"
_K_AREA = "ajcas_filtro_area"
_K_FAMILIA = "ajcas_filtro_familia"


def areas_con_ajuste(df, col_area, col_ajuste_val):
    """Las areas que MOVIERON algo, en orden alfabetico.

    El filtro de Area ofrecia las 20 areas del parquet, pero en un corte
    cualquiera la mitad tiene ajuste 0 en todas sus filas -- son areas que
    existen en el maestro y no participaron de esa sesion de inventario.
    Ofrecerlas es ofrecer pastillas que dejan la vista vacia.

    De paso se lleva puestas dos porquerias del dato que se veian como
    opciones legitimas: un area llamada "---" y otra "CAVA " con un espacio
    al final (indistinguible de "CAVA" en una pastilla). Las dos tienen
    ajuste en algun corte, asi que NO se filtran por nombre: se normaliza
    el texto al construir la lista y el filtrado compara igual. Ver
    arquitectura.md regla #424.
    """
    if not col_area or col_area not in df.columns:
        return []
    if not col_ajuste_val or col_ajuste_val not in df.columns:
        return sorted({str(a).strip() for a in df[col_area].dropna()
                       if str(a).strip() and str(a).strip() != "---"})
    _mov = df[df[col_ajuste_val].fillna(0) != 0]
    return sorted({str(a).strip() for a in _mov[col_area].dropna()
                   if str(a).strip() and str(a).strip() != "---"})


def _tono(v):
    return ((AJUSTE_POS_TEXTO, AJUSTE_POS) if v > 0
            else (AJUSTE_NEG_TEXTO, AJUSTE_NEG))


def _frase_ratio(val, base):
    """"falto 1,8x su stock" / "sobro 18 % de su stock", o None.

    Reemplaza a la pastilla Critico/Alerta/Menor/OK, que se calculaba con
    el PESO (la parte del ajuste total que explica la familia) y no con la
    gravedad -- por eso ENVASES Y EMBALAJES salia "OK" con -157,3 %: le
    falto vez y media su propio stock, pero como eran S/ 876 pesaba 3 %.

    Un multiplo se entiende; un "-177.9 %" se lee como error de calculo.
    Arriba de 100 % se dice en "x", abajo en porcentaje.
    """
    if not base or abs(base) < 1e-6:
        return None
    _pct = val / base * 100
    _verbo = "faltó" if val < 0 else "sobró"
    _m = abs(_pct) / 100
    if _m >= 1:
        return f"{_verbo} <b>{_m:.1f}×</b> su stock"
    return f"{_verbo} <b>{abs(_pct):.0f}%</b> de su stock"


def _barra_cero(val, esc):
    """Barra desde el cero central: izquierda falta, derecha sobra.

    `esc` es el semiancho en % (0-50) ya normalizado contra el mayor
    |ajuste| de las familias visibles, asi que el largo ES comparable entre
    tarjetas -- que es lo unico que la cascada encadenada hacia bien y que
    habia que no perder al partir en tarjetas.
    """
    _col = _tono(val)[1]
    _lado = "right:50%" if val < 0 else "left:50%"
    return (
        f"<div style='position:relative;height:18px;margin:10px 0 4px'>"
        f"<div style='position:absolute;left:0;right:0;top:50%;height:1px;"
        f"background:{GRIS_FONDO}'></div>"
        f"<div style='position:absolute;top:0;bottom:0;left:50%;width:1px;"
        f"background:{GRIS_BORDE}'></div>"
        f"<div style='position:absolute;top:50%;transform:translateY(-50%);"
        f"{_lado};width:{max(esc, 0.4):.2f}%;height:11px;"
        f"border-radius:999px;background:{_col}'></div></div>"
        f"<div style='display:flex;justify-content:space-between;"
        f"font-size:9.5px;color:{GRIS_BORDE};letter-spacing:.04em'>"
        f"<span>falta</span><span>0</span><span>sobra</span></div>")


def _css():
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
    /* Scroll propio por columna, con scrollbar invisible hasta el hover.
       No hay forma 100% CSS de mostrarla solo mientras se arrastra
       (necesitaria JS, y st.markdown no lo ejecuta). */
    .ajcas-lista-scroll {{
        max-height: 260px; overflow-y: auto;
        scrollbar-width: thin; scrollbar-color: transparent transparent;
        transition: scrollbar-color .15s ease; }}
    .ajcas-lista-scroll:hover {{
        scrollbar-color: {GRIS_TEXTO_SUAVE} transparent; }}
    .ajcas-lista-scroll::-webkit-scrollbar {{ width: 5px; }}
    .ajcas-lista-scroll::-webkit-scrollbar-track {{ background: transparent; }}
    .ajcas-lista-scroll::-webkit-scrollbar-thumb {{
        background: transparent; border-radius: 999px;
        transition: background-color .15s ease; }}
    .ajcas-lista-scroll:hover::-webkit-scrollbar-thumb {{
        background: {GRIS_TEXTO_SUAVE}; }}

    /* ── TARJETA DE CABECERA ──────────────────────────────────────────
       Es una tarjeta propia arriba de las de familia, a pedido. Junta el
       titulo, los KPIs del conjunto y el compartimento de filtros. */
    div[class*="st-key-ajcas_cab"] {{
        border-radius: 12px !important;
        padding: 14px 16px 10px 16px !important;
        margin-bottom: 12px !important; }}

    /* ── MINI-TARJETA DEL RIEL ────────────────────────────────────────
       EL BOTON CUBRE LA TARJETA ENTERA. Es el fix del pestillo de 16x36:
       el contenedor pasa a `relative`, el stElementContainer del boton a
       `static` (asi el absolute ancla en la tarjeta y no en el), y el
       <button> se estira a inset:0 por encima del HTML. Verificado en la
       app: 100 % de la superficie clickeable, el texto se sigue viendo
       debajo. Coste conocido: el texto deja de ser seleccionable.
       Ver arquitectura.md regla #421. */
    div[class*="st-key-ajcas_mini_"] {{
        position: relative !important;
        border: 1px solid {GRIS_BORDE}; border-radius: 10px;
        padding: 9px 11px; margin-bottom: 8px; cursor: pointer;
        background: {BLANCO};
        transition: border-color .12s ease, background .12s ease; }}
    div[class*="st-key-ajcas_mini_"]:hover {{
        border-color: {ACENTO}; background: {LAVANDA_SELECCION}; }}
    div[class*="st-key-ajcas_btnmini_"] {{ position: static !important; }}
    div[class*="st-key-ajcas_btnmini_"] button {{
        position: absolute !important; inset: 0 !important;
        width: 100% !important; height: 100% !important;
        min-height: 0 !important; padding: 0 !important;
        border: none !important; background: transparent !important;
        color: transparent !important; box-shadow: none !important;
        z-index: 3 !important; border-radius: 10px !important; }}
    div[class*="st-key-ajcas_btnmini_"] button:hover,
    div[class*="st-key-ajcas_btnmini_"] button:focus {{
        background: transparent !important; color: transparent !important;
        border: none !important; box-shadow: none !important; }}
    div[class*="st-key-ajcas_btnmini_"] button:focus-visible {{
        outline: 2px solid {ACENTO} !important; outline-offset: 1px; }}
    div[class*="st-key-ajcas_mini_"] [data-testid="stMarkdownContainer"] p {{
        margin: 0 !important; }}

    /* ── TARJETA PROTAGONISTA ─────────────────────────────────────────── */
    div[class*="st-key-ajcas_prota"] {{
        border: 2px solid {ACENTO} !important; border-radius: 12px !important;
        padding: 17px 20px 18px 20px !important; }}

    /* El compartimento de filtros de la tarjeta: sin la caja de formulario
       que Streamlit le pone al popover trigger. */
    div[class*="st-key-ajcas_filtros_"] button[data-testid="stPopoverButton"] {{
        border-radius: 8px !important; }}
    </style>"""


def _graf_waterfall_ajuste(df, col_familia, col_area, col_ajuste_val,
                           col_producto=None, col_valorizado=None,
                           col_cantidad=None, df_full=None, col_fecha=None,
                           col_unidad=None):
    """Cascada por familia: tarjeta de cabecera + una tarjeta por familia.

    `df` llega SIN los chips del reporte: esta vista filtra con los suyos
    (2026-09-14, a pedido). Los de arriba de la pila siguen gobernando Mapa
    de calor, Distribucion y Tabla.

    `col_unidad` es la unidad de Kardex por producto (Kg, Und, Lt...) -- se
    usa solo en el texto de las barras del drill; si no se resuelve, la
    barra muestra la cantidad sin sufijo (nunca el generico "und").
    """
    grp_col = col_familia or col_area
    if not grp_col:
        st.info("Se necesita columna de familia o área para la cascada.")
        return

    st.markdown(_css(), unsafe_allow_html=True)

    # ── Filtros PROPIOS de esta tarjeta ───────────────────────────────────
    # Van arriba de todo porque `filtro_pills` recorta el df que alimenta
    # a las tarjetas de abajo. Las opciones de Area salen de las que
    # movieron algo; las de Familia, del df entero.
    #
    # NORMALIZAR LA COLUMNA, no solo la lista de opciones. `filtro_pills`
    # filtra con `df[col].astype(str).isin(sel)`, o sea compara la
    # seleccion contra el valor CRUDO: con la pastilla diciendo "CAVA" y la
    # celda valiendo "CAVA " (con espacio al final, asi viene del maestro),
    # elegirla filtraba a CERO filas. Detectado al verificar en la app, no
    # en los tests. Ver arquitectura.md regla #424.
    if col_area and col_area in df.columns:
        df = df.assign(**{col_area: df[col_area].astype(str).str.strip()})
    _areas = areas_con_ajuste(df, col_area, col_ajuste_val)
    if col_familia and col_familia in df.columns:
        # Sembrar ANTES de dibujar el compartimento: el badge de "Filtros"
        # se calcula como argumento, o sea antes de que el widget exista.
        sembrar_seleccion(df, col_familia, _K_FAMILIA,
                          list(FAMILIAS_DE_ENTRADA))

    d = df
    _sel_area, _sel_fam = [], []
    with st.container(border=True, key="ajcas_cab"):
        _c_tit, _c_fil = st.columns([1, 1])  # columnas-internas: título vs. controles
        with _c_tit:
            st.markdown(
                f"<div style='font-size:15.5px;font-weight:600;"
                f"color:{GRIS_TEXTO_MEDIO};padding-top:2px'>"
                f"Ajuste valorizado por {grp_col.lower()}</div>",
                unsafe_allow_html=True)
        with _c_fil:
            with st.container(key="ajcas_filtros_wrap"):
                _n = sum(bool(st.session_state.get(k))
                         for k in (_K_AREA, _K_FAMILIA))
                _lbl = (f":material/filter_alt: Filtros :violet-badge[{_n}]"
                        if _n else ":material/filter_alt: Filtros")
                with st.popover(_lbl, use_container_width=True):
                    if _areas:
                        d, _sel_area = filtro_pills(
                            d, col_area, _K_AREA, "Área", valores=_areas)
                    d, _sel_fam = filtro_pills(
                        d, col_familia, _K_FAMILIA, "Familia")

        # El agregado y los KPIs viven en la MISMA tarjeta que el título,
        # así que se calculan acá adentro: el neto de abajo tiene que ser
        # el de lo que efectivamente se dibuja, ya filtrado.
        agg = (d.groupby(grp_col, as_index=False)[col_ajuste_val]
               .sum())
        if not agg.empty:
            agg["_abs"] = agg[col_ajuste_val].abs()
            agg = (agg[agg["_abs"] > 0]
                   .sort_values("_abs", ascending=False))
        if agg.empty:
            st.info("No hay datos para los filtros seleccionados.")
            return

        _total = float(agg[col_ajuste_val].sum())
        _base_tot = 0.0
        if col_valorizado and col_valorizado in d.columns:
            _base_tot = float(d[col_valorizado].sum() or 0)

        def _capsula(fg, bg, contenido):
            return (f"<span style='display:inline-flex;align-items:baseline;"
                    f"gap:6px;background:{bg};border-radius:8px;"
                    f"padding:4px 10px;color:{fg}'>{contenido}</span>")

        _fg = AJUSTE_POS_TEXTO if _total > 0 else AJUSTE_NEG_TEXTO
        _bg = AJUSTE_SOB_FONDO if _total > 0 else AJUSTE_CRIT_FONDO
        _kpis = _capsula(_fg, _bg, (
            f"<span style='font-size:11.5px;color:{_fg};opacity:.65'>neto"
            f"</span> <span style='font-size:15px;font-weight:700;"
            f"font-variant-numeric:tabular-nums'>"
            f"{'+' if _total > 0 else '−'}S/ {abs(_total):,.0f}</span>"))
        if abs(_base_tot) > 1e-6:
            _p = _total / _base_tot * 100
            _fgp = AJUSTE_POS_TEXTO if _p > 0 else AJUSTE_NEG_TEXTO
            _bgp = AJUSTE_SOB_FONDO if _p > 0 else AJUSTE_CRIT_FONDO
            _kpis += _capsula(_fgp, _bgp, (
                f"<span style='font-size:15px;font-weight:700;"
                f"font-variant-numeric:tabular-nums'>{_p:+.1f}%</span> "
                f"<span style='font-size:11.5px;color:{_fgp};opacity:.65'>"
                f"s/ total</span>"))
        st.markdown(
            f"<div style='display:flex;justify-content:flex-end;gap:10px;"
            f"flex-wrap:wrap;margin-top:-30px;padding-bottom:4px'>"
            f"{_kpis}</div>", unsafe_allow_html=True)

    # ── Datos por familia ────────────────────────────────────────────────
    _vv = (d.groupby(grp_col)[col_valorizado].sum()
           if col_valorizado and col_valorizado in d.columns else None)
    _abs_sum = float(agg["_abs"].sum()) or 1.0
    _max_abs = float(agg["_abs"].max()) or 1.0

    _fams = []
    for _i in range(len(agg)):
        _nom = str(agg[grp_col].iloc[_i])
        _v = float(agg[col_ajuste_val].iloc[_i])
        _base = float(_vv.get(_nom, 0) or 0) if _vv is not None else 0.0
        _fams.append({
            "cat": _nom, "val": _v, "base": _base,
            "peso": abs(_v) / _abs_sum * 100,
            "esc": abs(_v) / _max_abs * 50,
            "tt": (_v / _base_tot * 100) if abs(_base_tot) > 1e-6 else None,
        })

    _nombres = [f["cat"] for f in _fams]
    foco = st.session_state.get(_K_FOCO)
    if foco not in _nombres:
        # Sin foco valido, manda la familia que mas pesa. La vista nunca
        # queda sin protagonista: un riel solo no dice nada.
        foco = _nombres[0]
        st.session_state[_K_FOCO] = foco

    _act = [f for f in _fams if f["cat"] == foco][0]
    _resto = [f for f in _fams if f["cat"] != foco]

    # columnas-internas: protagonista vs. riel de las demás familias
    _c_pro, _c_riel = st.columns([3.2, 1])

    with _c_pro:
        with st.container(border=True, key="ajcas_prota"):
            _render_protagonista(
                _act, d, grp_col, col_ajuste_val, col_producto, col_area,
                col_cantidad, col_unidad)

    with _c_riel:
        for _f in _resto:
            _render_mini(_f)


def _render_mini(f):
    """Una familia del riel: nombre, monto y su barra desde el cero.

    El boton va ADENTRO del mismo contenedor que el HTML y el CSS lo estira
    a toda la tarjeta (ver `_css`). Label de un espacio: el texto se
    esconde con `color: transparent` porque un label vacio deja el boton
    sin caja que estirar.
    """
    _col = _tono(f["val"])[0]
    _sig = "+" if f["val"] > 0 else "−"
    with st.container(key=f"ajcas_mini_{_slug(f['cat'])}"):
        st.markdown(
            f"<div style='font-size:11px;font-weight:600;"
            f"color:{GRIS_TEXTO_MEDIO};white-space:nowrap;overflow:hidden;"
            f"text-overflow:ellipsis'>{f['cat']}</div>"
            f"<div style='font-size:14px;font-weight:600;color:{_col};"
            f"font-variant-numeric:tabular-nums;letter-spacing:-.02em;"
            f"margin-top:1px'>{_sig}S/ {abs(f['val']):,.0f}</div>"
            f"{_barra_cero(f['val'], f['esc'])}",
            unsafe_allow_html=True)
        if st.button(" ", key=f"ajcas_btnmini_{_slug(f['cat'])}",
                     help=f"Ver el detalle de {f['cat']}"):
            st.session_state[_K_FOCO] = f["cat"]
            st.rerun()


def _render_protagonista(f, d, grp_col, col_ajuste_val, col_producto,
                         col_area, col_cantidad, col_unidad):
    """La familia con foco: monto grande, barra, frase y su drill."""
    _col = _tono(f["val"])[0]
    _sig = "+" if f["val"] > 0 else "−"
    _peso = ("&lt;1%" if f["peso"] < 0.5 else f"{f['peso']:.0f}%")
    st.markdown(
        f"<div style='display:flex;align-items:baseline;gap:8px;"
        f"flex-wrap:wrap'>"
        f"<span style='font-size:16px;font-weight:600;"
        f"color:{TEXTO_PRINCIPAL};letter-spacing:-.01em'>{f['cat']}</span>"
        f"<span style='font-size:10.5px;color:{GRIS_TEXTO_SUAVE}'>"
        f"{_peso} del ajuste del período</span></div>"
        f"<div style='font-size:36px;font-weight:600;color:{_col};"
        f"font-variant-numeric:tabular-nums;letter-spacing:-.03em;"
        f"line-height:1.15;margin-top:4px'>"
        f"{_sig}S/ {abs(f['val']):,.0f}</div>"
        f"{_barra_cero(f['val'], f['esc'])}",
        unsafe_allow_html=True)

    _pie = []
    if f["tt"] is not None:
        _pie.append(f"<span style='color:{GRIS_TEXTO}'>"
                    f"{f['tt']:+.1f}% del inventario del período</span>")
    _fr = _frase_ratio(f["val"], f["base"])
    if _fr:
        _pie.append(f"<span style='color:{_col};font-weight:500'>{_fr}</span>")
    if _pie:
        st.markdown(
            f"<div style='font-size:12px;margin-top:8px;display:flex;"
            f"gap:14px;flex-wrap:wrap'>{' · '.join(_pie)}</div>",
            unsafe_allow_html=True)

    _drill(f["cat"], d, grp_col, col_ajuste_val, col_producto, col_area,
           col_cantidad, col_unidad)


def _drill(focus_cat, d, grp_col, col_ajuste_val, col_producto, col_area,
           col_cantidad, col_unidad):
    """Faltantes y sobrantes de la familia con foco, en dos columnas."""
    _det = d[d[grp_col].astype(str) == focus_cat]
    dim = col_producto or (col_area if grp_col != col_area else None)
    if not dim or dim not in _det.columns:
        return

    _has_cant = bool(col_cantidad and col_cantidad in _det.columns)
    _has_area = bool(col_area and col_area in _det.columns
                     and col_area != dim and col_area != grp_col)
    _has_um = bool(col_unidad and col_unidad in _det.columns
                   and col_unidad != dim)
    _agg_map = {col_ajuste_val: "sum"}
    if _has_cant:
        _agg_map[col_cantidad] = "sum"
    if _has_um:
        _agg_map[col_unidad] = "first"
    _agg_dim = _det.groupby(dim, as_index=False).agg(_agg_map)
    if _has_area:
        # "first" mostraba el área de la primera fila del producto, sin
        # importar si ahí el ajuste era 0 — con varias áreas por producto
        # etiquetaba con la que no tenía movimiento. Se toma el área de la
        # fila con mayor |ajuste|, que es la que explica el monto mostrado.
        _area_top = (_det[[dim, col_area, col_ajuste_val]]
                     .assign(_abs=lambda x: x[col_ajuste_val].abs())
                     .sort_values("_abs", ascending=False)
                     .drop_duplicates(subset=[dim])[[dim, col_area]])
        _agg_dim = _agg_dim.merge(_area_top, on=dim, how="left")

    if _agg_dim.empty or _agg_dim[col_ajuste_val].abs().sum() == 0:
        return

    st.markdown(
        f"<div style='border-top:1px solid {GRIS_FONDO};margin-top:14px;"
        f"padding-top:2px'></div>", unsafe_allow_html=True)

    def _filas_html(_df, color_bar):
        """Mini barras de progreso (riel + relleno), no un gráfico Plotly.
        El relleno normaliza contra el mayor |ajuste| de ESTE sub-listado
        (no del total de la familia)."""
        _max_abs = float(_df[col_ajuste_val].abs().max()) or 1.0
        _out = []
        for _, _r in _df.iterrows():
            _nom = str(_r[dim])
            if len(_nom) > 32:
                _nom = _nom[:31] + "…"
            _sub = (f"<div style='font-size:9.5px;color:{GRIS_TEXTO_SUAVE};"
                    f"white-space:nowrap;overflow:hidden;"
                    f"text-overflow:ellipsis'>{_r[col_area]}</div>"
                    if _has_area else "")
            _pct = max(abs(float(_r[col_ajuste_val])) / _max_abs * 100, 3)
            _t = f"S/ {_r[col_ajuste_val]:,.0f}"
            if _has_cant:
                _t += f" · {_r[col_cantidad]:,.1f}"
                _um = str(_r[col_unidad]).strip() if _has_um else ""
                if _um and _um.lower() != "nan":
                    _t += f" {_um}"
            _tcol = _tono(float(_r[col_ajuste_val]))[0]
            _out.append(
                f"<div style='display:flex;align-items:center;gap:8px;"
                f"padding:3px 0'>"
                f"<div style='width:38%;min-width:0;flex-shrink:0;"
                f"overflow:hidden'>"
                f"<div style='font-size:11.5px;color:{TEXTO_PRINCIPAL};"
                f"white-space:nowrap;overflow:hidden;"
                f"text-overflow:ellipsis'>{_nom}</div>{_sub}</div>"
                f"<div style='flex:1;position:relative;height:16px;"
                f"min-width:0'>"
                f"<div style='position:absolute;left:0;right:0;top:50%;"
                f"transform:translateY(-50%);height:7px;"
                f"background:{GRIS_FONDO};border-radius:999px'></div>"
                f"<div style='position:absolute;left:0;width:{_pct:.1f}%;"
                f"top:50%;transform:translateY(-50%);height:7px;"
                f"background:{color_bar};border-radius:999px'></div></div>"
                f"<div style='flex-shrink:0;text-align:right;font-size:11px;"
                f"font-weight:600;color:{_tcol};"
                f"font-variant-numeric:tabular-nums;white-space:nowrap'>"
                f"{_t}</div></div>")
        return "".join(_out)

    def _buscador(placeholder, key):
        """Filtra _agg_dim ANTES del top _TOPN_DRILL, no la lista ya
        recortada -- si no, un producto fuera del top actual no aparecería
        nunca por más que calzara con la búsqueda."""
        return st.text_input(placeholder, key=key, placeholder=placeholder,
                             label_visibility="collapsed").strip().lower()

    _pa, _pb = st.columns(2)  # columnas-internas: faltantes vs. sobrantes
    with _pa:
        _q = _buscador("Buscar en faltantes…",
                       f"ajcas_buscar_neg_{_slug(focus_cat)}")
        _pool = _agg_dim[_agg_dim[col_ajuste_val] < 0]
        if _q:
            _pool = _pool[_pool[dim].astype(str).str.lower()
                          .str.contains(_q, regex=False)]
        # ascending=True: el más negativo primero en el DataFrame -> primero
        # en el HTML -> arriba de la lista.
        _neg = (_pool.nsmallest(_TOPN_DRILL, col_ajuste_val)
                .sort_values(col_ajuste_val, ascending=True))
        if _neg.empty:
            st.caption("Sin coincidencias." if _q
                       else "Sin faltantes en esta familia.")
        else:
            st.markdown(f"<div class='ajcas-lista-scroll'>"
                        f"{_filas_html(_neg, AJUSTE_NEG)}</div>",
                        unsafe_allow_html=True)
    with _pb:
        _q = _buscador("Buscar en sobrantes…",
                       f"ajcas_buscar_pos_{_slug(focus_cat)}")
        _pool = _agg_dim[_agg_dim[col_ajuste_val] > 0]
        if _q:
            _pool = _pool[_pool[dim].astype(str).str.lower()
                          .str.contains(_q, regex=False)]
        _pos = (_pool.nlargest(_TOPN_DRILL, col_ajuste_val)
                .sort_values(col_ajuste_val, ascending=False))
        if _pos.empty:
            st.caption("Sin coincidencias." if _q
                       else "Sin sobrantes en esta familia.")
        else:
            st.markdown(f"<div class='ajcas-lista-scroll'>"
                        f"{_filas_html(_pos, AJUSTE_POS)}</div>",
                        unsafe_allow_html=True)
