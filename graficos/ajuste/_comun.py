"""graficos.ajuste._comun - helpers compartidos del dashboard de Ajuste.

Layout propio del rail, formato de fechas de corte y calculo de periodos.
Lo que usan dos o mas vistas del dashboard; nada de esto dibuja nada por
si solo.

Los "cortes" NO son calendario fijo: son rachas de fechas consecutivas
(ver cortes.py en la raiz), porque un inventario se abre y se cierra en
dias sueltos. De ahi que tengan su propio calculo en vez de reusar
_periodo_serie de compras.

El calculo de cortes YA NO VIVE ACA: subio a `cortes.py` (raiz) el
2026-08-09, cuando el corte paso a ser tambien un modo del calendario de
la franja (app.py, generico a los 8 reportes). Este modulo lo reexporta
con los nombres privados de siempre para no tocar a sus consumidores.
"""


import pandas as pd
import streamlit as st

# Reexports del modulo de raiz. NO son imports muertos: los consumen
#   _MESES_ABR_ES      -> _pivote.py (cabeceras de mes) y _fmt_corte de acá
#   _cortes_por_racha  -> _periodo_pivote_ajuste, acá abajo (el mapa de calor
#     lo usaba para su slider de corte hasta el 2026-09-15; hoy elige el
#     corte con `estado_filtros_vista`, igual que la Cascada)
#   _etiqueta_corte / _CORTE_MAX_SALTO_DIAS -> nadie hoy, pero son la pareja
#     del mismo concepto y separarlos obliga a recordar dos rutas de import.
# Sin el noqa + este comentario, `ruff check --fix` los borra y rompe a sus
# importadores (ver arquitectura.md regla #53).
from cortes import (  # noqa: F401
    CORTE_MAX_SALTO_DIAS as _CORTE_MAX_SALTO_DIAS,
    MESES_ABR_ES as _MESES_ABR_ES,
    cortes_por_racha as _cortes_por_racha,
    etiqueta_corte as _etiqueta_corte,
)
from cortes import corte_contiguo, cortes_disponibles
from tema import ACENTO, GRIS_BORDE, GRIS_TEXTO, LAVANDA_SELECCION
from graficos.base import (
    _layout, _slug, filtro_pills, sembrar_seleccion,
)
# _periodo_serie vive en graficos/compras/_comun.py; se reusa desde acá vía
# graficos.compras (que ya la re-exporta para test_graficos.py) en vez de
# duplicar el cálculo de granularidad Semana/Mes (Corte tiene su propio
# cálculo, ver _cortes_por_racha: no es calendario fijo, son rachas).
from graficos.compras import _periodo_serie


def _layout_aj(**overrides):
    """`_layout` con el look del estándar del rail (igual que Compras).

    Solo cambia dos cosas respecto al `_layout` genérico para que los gráficos
    de Ajuste combinen con la tarjeta como en Compras:
      · plot_bgcolor TRANSPARENTE — funde con el fondo de la tarjeta en vez de
        pintar una caja blanca dentro.
      · grilla del eje X oculta (Compras solo conserva la del eje Y).
    La paleta ya es común (PALETA_SERIES). El color SEMÁNTICO de cada gráfico
    (verde/rojo del waterfall, colorscale del mapa de calor, etc.) se conserva:
    es propio del tipo de gráfico, no del tema. No se toca el `_layout`
    compartido para no restilizar Ventas/Inventario/Receta."""
    lay = _layout(**overrides)
    lay["plot_bgcolor"] = "rgba(0,0,0,0)"
    _xaxis = dict(lay.get("xaxis", {}))
    _xaxis["showgrid"] = False
    lay["xaxis"] = _xaxis
    return lay


def _fmt_corte(fecha):
    """'02-ago' en vez de '02-Aug' — strftime('%b') usa el locale del
    sistema (inglés en Streamlit Cloud), y esta app es en español."""
    _ts = pd.Timestamp(fecha)
    return f"{_ts.day:02d}-{_MESES_ABR_ES[_ts.month - 1]}"


def _periodo_pivote_ajuste(fechas, gran):
    """Clave ordenable + etiqueta corta de periodo para la tabla dinámica
    de Ajuste, en las 3 granularidades del selector (Corte/Semana/Mes).
    Corte agrupa por rachas de días (`_cortes_por_racha`); Semana/Mes
    reusan `_periodo_serie` (graficos/compras/_comun.py, re-exportada vía
    graficos.compras — "reusar desde ahí, no duplicar" per
    arquitectura.md) para la clave, con etiqueta propia porque acá el mes
    va abreviado en español (_MESES_ABR_ES)."""
    if gran == "Corte":
        return _cortes_por_racha(fechas)
    clave = _periodo_serie(fechas, gran)
    if gran == "Semana":
        etiqueta = "S" + fechas.dt.isocalendar().week.astype(str).str.zfill(2)
    else:
        etiqueta = fechas.dt.month.map(lambda m: _MESES_ABR_ES[m - 1])
    return clave, etiqueta


# ── FILTROS PROPIOS DE UNA VISTA: corte · familia · área ─────────────────
#
# Nacieron adentro de la Cascada (2026-09-14/15) y el 2026-09-15 subieron
# acá, cuando el Mapa de calor pidió los mismos tres — "así como está el
# reporte de ajuste por familia". Son UNA pieza, no tres widgets sueltos:
# el corte decide qué filas hay, las áreas que se ofrecen salen de ese
# corte, y la familia se siembra sobre lo que quedó. Copiarla a la segunda
# vista habría dejado dos definiciones de "con qué abre" que se
# desincronizan a la primera corrección.
#
# QUIÉN LOS USA Y QUIÉN NO: las vistas que se filtran solas (Cascada, Mapa
# de calor) NO pasan por los chips Área/Familia de arriba de la pila —
# filtrar dos veces deja la vista mostrando la intersección de dos
# compartimentos con uno solo visible. Las que sí pasan por los chips
# (Distribución, Por fecha de corte) no llaman a nada de acá.
# Ver arquitectura.md regla #425.

# Con qué familias ABRE una vista con filtros propios. A pedido
# (2026-09-14): "alimentos, bebidas, vinos y envases" -- o sea todas menos
# COSTOS PRODUCCION, que es el 65 % del ajuste del ultimo corte y cuyas
# areas mas pesadas (GASTOS, LIMPIEZA Y MANTENIMIENTO) tienen valorizado
# CERO, asi que su ratio contra stock propio no significa nada.
#
# Es un DEFAULT, no un filtro fijo: la familia sigue estando en el
# compartimento a un clic de distancia. Ver la memoria del proyecto sobre
# "fijo en X es un default".
# Cuántos cortes ofrece el popover de fecha. Es la ventana OFRECIDA, no
# la lista completa: `estado_filtros_vista` se guarda todos los cortes del
# parquet aparte, porque el corte ANTERIOR al más viejo de los doce existe
# igual y es contra el que hay que comparar.
MAX_CORTES_OFRECIDOS = 12

FAMILIAS_DE_ENTRADA = (
    "ALIMENTOS",
    "BEBIDAS CON ALCOHOL",
    "BEBIDAS SIN ALCOHOL",
    "VINOS Y ESPUMANTES",
    "ENVASES Y EMBALAJES",
)


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


def estado_filtros_vista(df, df_full, col_fecha, col_familia, col_area,
                         col_ajuste_val, k_corte, k_familia, k_area,
                         familias=FAMILIAS_DE_ENTRADA, historial=0):
    """ESTADO PRIMERO, WIDGETS DESPUES: resuelve los tres filtros sin
    dibujar nada, y devuelve el dict que consume `render_filtros_vista`.

    Existe separado del dibujo porque las dos vistas que lo usan necesitan
    el RESULTADO antes que los controles: la Cascada pone los tres en la
    fila de arriba de su tabla de familias, y esa tabla sale de aplicar
    estos mismos filtros (huevo y gallina). Se rompe leyendo `session_state` ANTES de dibujar:
    los widgets escriben su clave y Streamlit rerunea solo, asi que el
    cambio se ve en la pasada siguiente. Mismo orden que el clic de Plotly
    en Volatilidad y Semanal (regla #399).

    El corte se resuelve sobre `df_full` (el parquet entero) y no sobre el
    `df` que llega ya recortado por la franja: con el df recortado, elegir
    un corte dejaria la lista con ese unico corte y no habria forma de
    volver a los otros -- el clasico filtro que se come su propio selector.
    Es la misma razon por la que `app.py` los calcula antes de aplicar el
    rango. Sin `df_full` (o sin columna de fecha) no hay selector de corte
    y la vista se queda con el `df` que le dieron.

    `historial=N` trae ademas los N cortes que TERMINAN en el elegido (el
    elegido incluido), en `historial_cortes`, y sus filas en
    `d_historial` con una columna `_corte_clave` que dice de cual es cada
    una. Filtradas EXACTAMENTE igual que `d` (misma area, misma familia,
    misma normalizacion), que es todo el punto: comparar cortes filtrados
    distinto no compara nada. Lo usa la Cascada para su pestaña «Por
    corte» (regla #441).

    Es UN filtrado y no N: se toma la union de los dias de los N cortes de
    una sola pasada y despues se etiqueta cada fila con su corte. Opt-in
    igual, porque el Mapa de calor no lo necesita.

    Los cortes del historial salen de la lista COMPLETA, no de los
    `MAX_CORTES_OFRECIDOS` que ofrece el popover: si no, el mas viejo de
    los doce se quedaria sin comparacion por un limite que es de la UI.

    Claves del dict: `base` (el corte entero, sin area ni familia: es lo
    que ofrecen las pastillas), `d` (ya filtrado, lo que dibuja la vista),
    `corte`, `cortes`, `areas`, `sel_fam`, `sel_area`, `corte_prev` (el
    anterior al elegido, o None), `historial_cortes`, `d_historial` y las
    tres keys.
    """
    sel_area = list(st.session_state.get(k_area) or [])

    base = df
    base_hist = None
    cortes, _todos, _fechas = [], [], None
    if df_full is not None and col_fecha and col_fecha in df_full.columns:
        base = df_full
        _fechas = pd.to_datetime(df_full[col_fecha], errors="coerce").dt.date
        _todos = cortes_disponibles(
            pd.to_datetime(df_full[col_fecha], errors="coerce"))
        cortes = _todos[-MAX_CORTES_OFRECIDOS:]
    corte = corte_prev = None
    hist_cortes = []
    if cortes:
        _clave = st.session_state.get(k_corte)
        corte = next((c for c in cortes if c["clave"] == _clave), None)
        if corte is None:
            # Abre en el ULTIMO corte: lo que se mira de Ajuste es una
            # sesion de inventario, no un intervalo de calendario.
            corte = cortes[-1]
            st.session_state[k_corte] = corte["clave"]
        if historial > 0:
            _i = next((i for i, c in enumerate(_todos)
                       if c["clave"] == corte["clave"]), 0)
            hist_cortes = _todos[max(0, _i - historial + 1):_i + 1]
            corte_prev = hist_cortes[-2] if len(hist_cortes) > 1 else None
            # UN filtrado para los N cortes: la union de sus dias, y
            # despues cada fila etiquetada con el corte al que cae.
            _de_dia = {_d: _c["clave"] for _c in hist_cortes
                       for _d in _c["dias"]}
            base_hist = base[_fechas.isin(_de_dia)].assign(
                _corte_clave=_fechas[_fechas.isin(_de_dia)].map(_de_dia))
        base = base[_fechas.isin(set(corte["dias"]))]

    # NORMALIZAR EL AREA, no solo la lista de opciones: `filtro_pills`
    # compara la seleccion contra el valor CRUDO, y el maestro trae
    # "CAVA " con espacio al final. Ver arquitectura.md regla #424.
    def _normalizar(x):
        if x is None or not col_area or col_area not in x.columns:
            return x
        return x.assign(**{col_area: x[col_area].astype(str).str.strip()})

    base, base_hist = _normalizar(base), _normalizar(base_hist)
    # Las opciones las decide el corte ELEGIDO, nunca el anterior: ofrecer
    # un area que no movio nada ahora es ofrecer una pastilla que deja la
    # vista vacia, y de eso se trata `areas_con_ajuste` (#424).
    areas = areas_con_ajuste(base, col_area, col_ajuste_val)
    if col_familia and col_familia in base.columns:
        sembrar_seleccion(base, col_familia, k_familia, list(familias))
    sel_fam = list(st.session_state.get(k_familia) or [])

    def _aplicar(x):
        if x is None:
            return None
        if sel_area and col_area and col_area in x.columns:
            x = x[x[col_area].astype(str).isin(sel_area)]
        if sel_fam and col_familia and col_familia in x.columns:
            x = x[x[col_familia].astype(str).isin(sel_fam)]
        return x

    return {"base": base, "d": _aplicar(base), "corte": corte,
            "cortes": cortes, "corte_prev": corte_prev,
            "historial_cortes": hist_cortes, "d_historial": _aplicar(base_hist),
            "areas": areas, "sel_fam": sel_fam, "sel_area": sel_area,
            "col_familia": col_familia, "col_area": col_area,
            "k_corte": k_corte, "k_familia": k_familia, "k_area": k_area}


def render_filtros_vista(cols, est):
    """Los tres popovers, uno por columna: corte · familia · area.

    Reciben las columnas ya creadas y no las crean ellos porque el
    llamador decide en que zona van: en Streamlit la posicion la da el
    orden en que se CREA el contenedor, no el orden en que se escribe
    en el. `est` es lo que devolvio `estado_filtros_vista`.
    """
    _corte, _cortes = est["corte"], est["cortes"]
    with cols[0]:
        _et = _corte["etiqueta_anio"] if _corte else "Sin cortes"
        with st.popover(f":material/event: {_et}",
                        use_container_width=True):
            if not _cortes:
                st.caption("No hay sesiones de inventario.")
            else:
                st.caption("Sesión de inventario")
                # Del mas reciente al mas viejo: el conteo que se
                # revisa es casi siempre el ultimo.
                for _c in reversed(_cortes):
                    _n = _c["n_dias"]
                    _tramo = (_c["fin"] - _c["ini"]).days + 1
                    # Un corte NO tiene por que ser contiguo: decir
                    # "3 de 5 días" es lo unico que lo deja ver.
                    _dias = (f"{_n} de {_tramo} días"
                             if not corte_contiguo(_c)
                             else f"{_n} día" + ("s" if _n > 1 else ""))
                    _on = bool(_corte and _c["clave"] == _corte["clave"])
                    if st.button(
                            f"{_c['etiqueta_anio']}  ·  {_dias}",
                            key=f"{est['k_corte']}_{_slug(_c['clave'])}",
                            use_container_width=True,
                            type="primary" if _on else "secondary"):
                        st.session_state[est["k_corte"]] = _c["clave"]
                        st.rerun()
    with cols[1]:
        _n_fam = len(est["sel_fam"])
        _et_fam = ("todas las familias" if not _n_fam
                   else est["sel_fam"][0].lower() if _n_fam == 1
                   else f"{_n_fam} familias")
        with st.popover(f":material/category: {_et_fam}",
                        use_container_width=True):
            filtro_pills(est["base"], est["col_familia"], est["k_familia"],
                         "Familia")
    with cols[2]:
        _n_ar = len(est["sel_area"])
        _et_ar = ("todas las áreas" if not _n_ar
                  else est["sel_area"][0].lower() if _n_ar == 1
                  else f"{_n_ar} áreas")
        with st.popover(f":material/apartment: {_et_ar}",
                        use_container_width=True):
            if est["areas"]:
                filtro_pills(est["base"], est["col_area"], est["k_area"],
                             "Área", valores=est["areas"])
            else:
                st.caption("Ninguna área movió algo en este corte.")


def css_filtros_vista(prefijo_ctrl, prefijo_corte):
    """Las reglas del trigger minimalista + la lista de cortes, scopeadas
    al prefijo de key que le toque a cada vista. Devuelve CSS SIN el
    `<style>`, para concatenar con el resto del bloque del modulo.

    `prefijo_ctrl` es el prefijo de los contenedores propios de cada
    control ("ajcas_ctrl_", "hm_ctrl_"); `prefijo_corte` el de los botones
    de la lista de cortes ("ajcas_corte_", "hm_corte_").

    Minimalista = el trigger no se ve como campo de formulario: sin borde,
    sin fondo, del tamano del texto. El VALOR VIGENTE es la etiqueta
    ("2 set 2026", "5 familias"), asi que se lee que hay puesto sin abrir
    nada. Ver regla #427.
    """
    return f"""
    div[class*="st-key-{prefijo_ctrl}"] button[data-testid="stPopoverButton"] {{
        border: none !important; background: transparent !important;
        color: {GRIS_TEXTO} !important;
        min-height: 0 !important; padding: 4px 6px !important;
        /* EL `min-width: 180px` ES DE STREAMLIT, no del contenido. Con los
           tres en fila dentro de una tarjeta de 528, las columnas dan ~156
           y ese piso los hacia desbordar. El texto mas largo ("todas las
           areas") mide ~124 con su icono y su chevron, asi que 156 alcanza
           de sobra. Ver regla #434. */
        min-width: 0 !important;
        border-radius: 7px !important;
        /* LA ETIQUETA VA A LA IZQUIERDA. `st.popover` la centra, y con el
           boton ocupando los 352px de la tarjeta el texto quedaba flotando
           a 137px de su propio borde -- descolgado del neto y de todo lo
           demas, que estan alineados a 391. Medido: el texto arrancaba en
           528. Se reporto como dos intentos de arreglarlo desde el modo
           diseno (`width: 144px` y un `translate(-7px,-8px)`), y ninguno
           podia: el ancho no baja de 180 por el `min-width` propio del
           popover (#430), y el transform mueve el boton entero, no su
           etiqueta. Ver regla #432. */
        justify-content: flex-start !important;
        transition: background .12s ease, color .12s ease !important; }}
    div[class*="st-key-{prefijo_ctrl}"] button[data-testid="stPopoverButton"] p {{
        font-size: 11.5px !important; }}
    div[class*="st-key-{prefijo_ctrl}"] button[data-testid="stPopoverButton"]:hover,
    div[class*="st-key-{prefijo_ctrl}"] button[data-testid="stPopoverButton"][aria-expanded="true"] {{
        background: {LAVANDA_SELECCION} !important;
        color: {ACENTO} !important; }}

    /* La lista de cortes del popover: botones planos, el activo en acento. */
    div[class*="st-key-{prefijo_corte}"] button {{
        border: 1px solid {GRIS_BORDE} !important;
        border-radius: 7px !important; min-height: 0 !important;
        padding: 5px 10px !important; }}
    div[class*="st-key-{prefijo_corte}"] button p {{ font-size: 12px !important; }}
"""
