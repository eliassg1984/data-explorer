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


from graficos.movil import css_movil, js_movil
from pathlib import Path

import numpy as np
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
from cortes import fecha_operativa, sesiones_inventario, ultimo_cierre
from estado_rango import atajo_de, atajos_meses
import franja_fecha
from tema import ACENTO, GRIS_BORDE, GRIS_TEXTO, LAVANDA_SELECCION
from graficos.base import (
    _layout, _slug, filtro_pills, k_rango_tarjeta, rango_tarjeta,
    selector_fecha_tarjeta, sembrar_seleccion,
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


# ── EL MES DE UN CIERRE: el operativo o el del registro (regla #613) ─────
# El cierre de fin de mes se registra del 1 al 7 del siguiente
# (`cortes.DIA_CIERRE_OPERATIVO`). Con «Mes operativo» (el default) los
# meses de Evolución, de la tabla dinámica y de Distribución «Por meses» lo
# cuentan en el mes que cierra; con «Fecha de registro», en el del sistema.
# Las sesiones no cambian: una sesión es un conteo y sus días son los de
# verdad.
#
# Desde el 2026-10-11 (regla #632) se elige al PIE DEL PANEL DE MESES de
# cada vista, no en «Filtros»: es el único lugar donde cambia algo. Sigue
# siendo UN valor para todo el reporte —esta clave, que ya no es la key de
# ningún widget—: con Evolución en «operativo» y la tabla en «registro»,
# setiembre valdría dos cifras en la misma página.
CLAVE_MES = "ajuste_mes"
MES_OPERATIVO = "Mes operativo"
MES_REGISTRO = "Fecha de registro"


def mes_operativo_activo():
    """True si Ajuste fecha los cierres por su mes operativo (el default)."""
    return st.session_state.get(CLAVE_MES, MES_OPERATIVO) == MES_OPERATIVO


def fechas_del_mes(fechas, operativo):
    """`fechas` tal cual, o en su mes operativo si `operativo`."""
    return fecha_operativa(fechas) if operativo else fechas


# ── LOS MESES DE UNA VISTA (regla #632) ──────────────────────────────────
# Evolución, la tabla dinámica y Distribución «Por meses» eligen su rango
# con el MISMO panel que las tarjetas de Compras (`selector_fecha_tarjeta`
# + `graficos/panel_fecha.py`), en modo «sólo meses» y con los atajos de
# `estado_rango.atajos_meses`. Cada vista guarda su rango en su categoría
# (`rango_cat_Ajuste de Inventario_<vista>_<op|reg>`): con el modo en la
# clave, cambiar el mes del cierre no deja un rango leído en la otra regla.
# Recortan SUS datos dentro de su sección, que es un fragment: cambiar la
# fecha recalcula esa vista sola.
_K_MES_RECARGA = "_ajuste_mes_recarga"
# Las vistas que todavía tienen que LLEVAR su rango al otro modo después de
# un cambio de «Mes del cierre» (ver `_llevar_rango`).
_K_MES_LLEVAR = "_ajuste_mes_llevar"
_VISTAS_MESES = ("evo", "det", "dist")


def fechas_referencia(fechas):
    """Las fechas con las que se cuentan los meses: las operativas o las de
    registro, según «Mes del cierre»."""
    f = pd.to_datetime(fechas, errors="coerce")
    return fecha_operativa(f) if mes_operativo_activo() else f


def _topes(fechas):
    """Del primer día del primer mes al último día con datos, o None."""
    f = fechas.dropna()
    if f.empty:
        return None
    return f.min().date().replace(day=1), f.max().date()


def _cat_meses(vista, operativo):
    return f"{vista}_{'op' if operativo else 'reg'}"


def ctx_meses(vista, fechas, defecto="mm12"):
    """El `ctx` del panel de meses de la vista `vista` («evo», «det»,
    «dist»): los topes de `fechas` leídas con el mes del cierre vigente y el
    atajo `defecto` («Últimos 12 meses») como rango de entrada. Lo leen el
    recorte (`rango_meses`) y el botón (`selector_meses`): con el mismo ctx
    nombran la misma clave."""
    base = franja_fecha.contexto()
    if not base or fechas is None:
        return None
    topes = _topes(fechas_referencia(fechas))
    if not topes:
        return None
    cat = _cat_meses(vista, mes_operativo_activo())
    r_def = next((r for c, _n, _g, r in atajos_meses(topes[1], topes)
                  if c == defecto), None)
    ctx = {**base, "fecha_min": topes[0], "fecha_max": topes[1],
           "rango_default_cat": {cat: r_def} if r_def else {},
           "atajos_fn": atajos_meses, "solo_meses": True,
           "categoria_meses": cat}
    llevar = st.session_state.get(_K_MES_LLEVAR) or {}
    if vista in llevar.get("vistas", ()):
        llevar["vistas"] = [x for x in llevar["vistas"] if x != vista]
        _llevar_rango(vista, fechas, llevar.get("de"), ctx)
    return ctx


def _llevar_rango(vista, fechas, de, ctx):
    """Después de cambiar «Mes del cierre», la vista conserva lo que tenía:
    el MISMO atajo («Año pasado» sigue siendo «Año pasado», contado con la
    otra regla) o, si eligió meses a mano, los mismos meses. Sin esto cada
    modo abría en su propio default y lo elegido se perdía."""
    op_viejo = de == MES_OPERATIVO
    f = pd.to_datetime(fechas, errors="coerce")
    topes_v = _topes(fecha_operativa(f) if op_viejo else f)
    r_v = st.session_state.get(k_rango_tarjeta(_cat_meses(vista, op_viejo), ctx))
    if not (topes_v and isinstance(r_v, (tuple, list)) and len(r_v) == 2
            and all(r_v)):
        return
    topes_n = (ctx["fecha_min"], ctx["fecha_max"])
    clave = atajo_de(tuple(r_v), atajos_meses(topes_v[1], topes_v))
    if clave:
        r_n = next((r for c, _n, _g, r in atajos_meses(topes_n[1], topes_n)
                    if c == clave), None)
    else:
        r_n = (max(min(r_v), topes_n[0]), min(max(r_v), topes_n[1]))
    if r_n and r_n[0] <= r_n[1]:
        st.session_state[k_rango_tarjeta(ctx["categoria_meses"], ctx)] = tuple(r_n)


def rango_meses(ctx_m):
    """`(inicio, fin EXCLUSIVO)` de la vista, en Timestamps, o None."""
    if not ctx_m:
        return None
    r = rango_tarjeta(ctx_m["categoria_meses"], ctx_m)
    if not r:
        return None
    return pd.Timestamp(r[0]), pd.Timestamp(r[1]) + pd.Timedelta(days=1)


def recortar_meses(d, col_fecha, rng):
    """`d` en el rango `rng`, contado con las fechas de referencia. Sin
    rango (o sin columna), entero."""
    if d is None or rng is None or not col_fecha or col_fecha not in d.columns:
        return d
    f = fechas_referencia(d[col_fecha])
    return d[(f >= rng[0]) & (f < rng[1])]


def _cambiar_mes_cierre(k):
    v = st.session_state.get(k)
    previo = st.session_state.get(CLAVE_MES, MES_OPERATIVO)
    if v in (MES_OPERATIVO, MES_REGISTRO) and v != previo:
        st.session_state[CLAVE_MES] = v
        st.session_state[_K_MES_RECARGA] = True
        st.session_state[_K_MES_LLEVAR] = {"de": previo,
                                           "vistas": list(_VISTAS_MESES)}


def _pie_mes_cierre(prefijo):
    """«Mes del cierre», al pie del panel de meses. Una key por panel y por
    valor: tres paneles no pueden compartir key, y un widget dentro de un
    popover cerrado no se entera de lo que Python le escribe (#467), así
    que cuando el valor cambia la key cambia con él y el widget nace con el
    valor nuevo."""
    actual = st.session_state.get(CLAVE_MES, MES_OPERATIVO)
    if actual not in (MES_OPERATIVO, MES_REGISTRO):
        actual = MES_OPERATIVO
    k = f"{prefijo}_mescierre_{_slug(actual)}"
    # Rótulo y control en UN renglón: apilados, el `st.markdown` se metía
    # debajo de los botones.
    with st.container(key=f"{prefijo}_mcfila", horizontal=True,
                      vertical_alignment="center", gap="small"):
        st.markdown('<div class="ajf-pie-rot">Mes del cierre</div>',
                    unsafe_allow_html=True)
        st.segmented_control(
            "Mes del cierre", [MES_OPERATIVO, MES_REGISTRO], default=actual,
            required=True, key=k, label_visibility="collapsed",
            on_change=_cambiar_mes_cierre, args=(k,))
    st.caption(
        "**Mes operativo**: lo registrado del 1 al 7 cuenta en el mes "
        "anterior, el que cierra. **Fecha de registro**: en el día en que se "
        "abrió en el Almacén. Vale para todo el reporte.")


def selector_meses(prefijo, ctx_m):
    """El botón de meses de una vista, con «Mes del cierre» al pie. Las keys
    llevan el prefijo `ajf_`, de donde cuelga su CSS (`estilos/_80_cards.py`,
    el mismo de los botones de fecha de Movimientos)."""
    if not ctx_m:
        return
    selector_fecha_tarjeta(prefijo, None, categoria=ctx_m["categoria_meses"],
                           ctx=ctx_m, pie=lambda: _pie_mes_cierre(prefijo))


def recargar_si_cambio_mes():
    """Si «Mes del cierre» cambió en esta corrida, una corrida COMPLETA: el
    widget vive en el fragment de UNA vista y el valor manda sobre tres. Se
    llama DESPUÉS de dibujar la vista entera —en el dibujante de la sección—
    para que ningún widget quede sin registrar (regla #373)."""
    if st.session_state.pop(_K_MES_RECARGA, False):
        st.rerun(scope="app")


# ── LA SESIÓN DE UNA VISTA: el selector con flechas (reglas #632 y #634) ──
# Por familia, Familia × Área y Distribución miran UNA sesión de inventario
# —un cierre de mes o un parcial, ver `cortes.sesiones_inventario`—, y cada
# una elige la suya («cambia sólo esa», a pedido). El botón es la píldora de
# los botones de fecha de Compras; a los costados, ‹ › van a la sesión
# anterior o siguiente sin abrir nada. Abren en el ÚLTIMO CIERRE de mes, no
# en la última sesión. Las keys llevan el prefijo de la vista
# (`ajses_<vista>`), de donde cuelga el CSS (`estilos/_80_cards.py`).
#
# EL PANEL ES UNA PIEZA PROPIA (regla #634), como el de fechas de Compras:
# `panel_sesion.js` + `panel_sesion.css`, un `st.components.v2` sin iframe.
# La primera versión eran botones de Streamlit, y un botón no tiene dos
# renglones: la lista no podía decir el neto ni el detalle de cada sesión,
# que es lo que distingue un cierre de un recuento sin abrirlo. A Python le
# llega sólo el trigger «accion».
_AQUI = Path(__file__).parent
_PANEL_SESION = st.components.v2.component(
    "panel_sesion_ajuste",
    css=css_movil((_AQUI / "panel_sesion.css").read_text(encoding="utf-8")),
    js=js_movil((_AQUI / "panel_sesion.js").read_text(encoding="utf-8")),
)
_ARCHIVO_AJUSTE = "ajusteinventario.parquet"


def sesiones_de(df_full, col_fecha):
    """Las sesiones de inventario del parquet entero, o []."""
    if df_full is None or not col_fecha or col_fecha not in df_full.columns:
        return []
    return sesiones_inventario(pd.to_datetime(df_full[col_fecha],
                                              errors="coerce"))


def _codigos(serie, limpiar=False):
    """Un entero por valor distinto (-1 el nulo). Con `limpiar`, sin los
    espacios de los bordes: «CAVA » y «CAVA» son la misma área (#424). Se
    limpian los valores DISTINTOS, no las 250.000 filas."""
    c, u = pd.factorize(serie)
    if limpiar and len(u):
        c2, _ = pd.factorize(pd.Index(u).astype(str).str.strip())
        c = np.where(c >= 0, c2[c], -1)
    return c


def stats_sesiones(df, col_fecha, col_area, col_valor, col_producto, sesiones):
    """`{clave: (neto, áreas, productos)}` de cada sesión: el ajuste
    valorizado neto, cuántas áreas se contaron y cuántos productos cerraron
    con diferencia. Pura. Con enteros y `bincount`, no con `groupby` sobre
    texto: así eran 634 ms por vista sobre el parquet real, así 218."""
    n = len(sesiones)
    vacio = {s["clave"]: (0.0, 0, 0) for s in sesiones}
    if not n or df is None or df.empty or not col_fecha \
            or col_fecha not in df.columns:
        return vacio
    dia = pd.to_datetime(df[col_fecha], errors="coerce").dt.normalize()
    cod_dia, dias = pd.factorize(dia)
    de_dia = {pd.Timestamp(d): i for i, s in enumerate(sesiones)
              for d in s["dias"]}
    idx = np.array([de_dia.get(pd.Timestamp(d), -1) for d in dias], dtype=int)
    ses = np.where(cod_dia >= 0, idx[cod_dia] if len(idx) else -1, -1)
    ok = ses >= 0
    v = (pd.to_numeric(df[col_valor], errors="coerce").fillna(0.0).to_numpy()
         if col_valor and col_valor in df.columns else np.zeros(len(df)))
    neto = np.bincount(ses[ok], weights=v[ok], minlength=n)

    def _distintos(col, filas, limpiar=False):
        if not col or col not in df.columns:
            return np.zeros(n, dtype=int)
        c = _codigos(df[col], limpiar)
        par = pd.DataFrame({"s": ses[filas], "c": c[filas]})
        par = par[par["c"] >= 0].drop_duplicates()
        return np.bincount(par["s"].to_numpy(), minlength=n)

    areas = _distintos(col_area, ok, limpiar=True)
    prods = _distintos(col_producto, ok & (v != 0))
    return {s["clave"]: (float(neto[i]), int(areas[i]), int(prods[i]))
            for i, s in enumerate(sesiones)}


@st.cache_data(show_spinner=False, max_entries=24)
def _stats_cacheable(sello, familias, columnas, _df, _sesiones):
    """`stats_sesiones` por versión del parquet y familias elegidas: las tres
    vistas abren con las mismas cinco familias y lo calcula una sola. El df y
    las sesiones no entran en la clave (`_`): los identifica el `sello`
    (regla #367)."""
    return stats_sesiones(_df, *columnas, _sesiones)


def stats_de_vista(df_full, sesiones, col_fecha, col_area, col_valor,
                   col_producto, col_familia=None, familias=()):
    """Las cuentas de cada sesión con las FAMILIAS de la vista: el neto del
    panel tiene que ser el total que la vista muestra."""
    d = df_full
    if familias and col_familia and col_familia in getattr(d, "columns", ()):
        d = d[d[col_familia].astype(str).isin(familias)]
    try:
        from data import sello_datos
        sello = sello_datos(_ARCHIVO_AJUSTE)
    except Exception:  # sin secrets (modo demo) o sin red: sin caché fina
        sello = ""
    return _stats_cacheable(sello, tuple(sorted(familias or ())),
                            (col_fecha, col_area, col_valor, col_producto),
                            d, sesiones)


def texto_familias(familias):
    """De quién es el neto del panel: «las cinco familias de entrada»,
    «las 3 familias elegidas», «Alimentos», «todas las familias»."""
    fam = list(familias or ())
    if not fam:
        return "todas las familias"
    if set(fam) == set(FAMILIAS_DE_ENTRADA):
        return "las cinco familias de entrada"
    if len(fam) == 1:
        return fam[0].capitalize()
    return f"las {len(fam)} familias elegidas"


def _k_solo(k):
    return f"{k}__solo"


def sesion_vigente(k, sesiones):
    """La sesión elegida en `k` o, si no hay o ya no existe, el último
    cierre de mes (y la deja escrita)."""
    s = next((x for x in sesiones if x["clave"] == st.session_state.get(k)),
             None)
    if s is None:
        s = ultimo_cierre(sesiones)
        if s is not None:
            st.session_state[k] = s["clave"]
    return s


def sesiones_elegidas(k, sesiones, k_varias=None, k_multi=None):
    """Las sesiones que mira la vista: la de `k` o, con «Varias» prendido
    (`k_multi`), las de `k_varias` en orden. Nunca vacía si hay sesiones."""
    actual = sesion_vigente(k, sesiones)
    if not (k_multi and st.session_state.get(k_multi)):
        return [actual] if actual else []
    marcadas = set(st.session_state.get(k_varias) or [])
    elegidas = [x for x in sesiones if x["clave"] in marcadas]
    if not elegidas and actual:
        elegidas = [actual]
        st.session_state[k_varias] = [actual["clave"]]
    return elegidas


def _paso_sesion(k, orden, visibles, paso):
    """Callback de ‹ ›: la sesión anterior o siguiente de las que se ven
    (con «Sólo cierres», de cierre en cierre)."""
    pos = {c: i for i, c in enumerate(orden)}
    i = pos.get(st.session_state.get(k), len(orden) - 1)
    cand = [c for c in visibles if (pos[c] < i if paso < 0 else pos[c] > i)]
    if cand:
        st.session_state[k] = cand[-1] if paso < 0 else cand[0]


def _poner_multi(k_multi, k_varias, k, valor):
    """«Una» / «Varias». Al prender, arranca con la sesión de `k`; al
    apagar, la vista vuelve a la más nueva de las marcadas."""
    st.session_state[k_multi] = valor
    if valor:
        st.session_state[k_varias] = [st.session_state.get(k)]
    else:
        marcadas = st.session_state.get(k_varias) or []
        if marcadas:
            st.session_state[k] = marcadas[-1]


def _anio_sesion(s):
    """El año con que se agrupa una sesión: el del mes que CIERRA, no el de
    su registro. El cierre de diciembre de 2025 va con 2025 aunque se haya
    contado el 2 de enero."""
    return s["mes"][0]


def detalle_sesion(s, stats=None):
    """El segundo renglón de una sesión en el panel: «registrado el 1 y 6
    oct (se juntan 2 conteos) · 13 áreas · 751 productos con diferencia»."""
    if s["tipo"] == "cierre":
        partes = [f"registrado el {s['etiqueta']}"
                  + (f" (se juntan {s['juntas']} conteos)" if s["juntas"] > 1
                     else "")]
    else:
        partes = [f"{s['n_dias']} día" + ("s" if s["n_dias"] > 1 else "")]
    if stats:
        _neto, areas, prods = stats
        partes.append(f"{areas} área" + ("s" if areas != 1 else ""))
        partes.append(f"{prods:,} producto"
                      + ("s" if prods != 1 else "") + " con diferencia")
    return " · ".join(partes)


def datos_panel_sesion(sesiones, actual, marcadas, multi, con_multi, solo,
                       stats=None, familias_txt="las familias de esta vista",
                       pie=None, meta=None):
    """Lo que recibe `panel_sesion.js`. Pura (la prueba `test_graficos.py`).

    `pie` y `meta` (`{clave: texto}`) reemplazan el pie y el segundo
    renglón de cada sesión cuando el neto NO es el ajuste: Movimientos ›
    «Sin plato, cierre por cierre» lista los cierres con lo que salió sin
    plato (regla #645)."""
    stats = stats or {}
    meta = meta or {}
    return {
        "sesiones": [{"k": s["clave"], "tipo": s["tipo"],
                      "nombre": s["nombre"], "anio": _anio_sesion(s),
                      "meta": meta.get(s["clave"])
                      or detalle_sesion(s, stats.get(s["clave"])),
                      "neto": (stats[s["clave"]][0] if s["clave"] in stats
                               else None)}
                     for s in sesiones],
        "actual": actual["clave"] if actual else None,
        "marcadas": sorted(marcadas),
        "multi": bool(multi), "con_multi": bool(con_multi),
        "solo": bool(solo),
        "pie": pie or [f"Neto de {familias_txt}. Las flechas ‹ › recorren "
                       "esta misma lista"
                       + (", de cierre en cierre." if solo else "."),
                       "Elegir acá cambia sólo esta tarjeta."],
        "pie_varias": ["Marca las sesiones que quieras: se suman como si "
                       "fueran una.",
                       "Con más de una, las flechas se apagan."],
    }


def selector_sesion(prefijo, k, sesiones, k_varias=None, k_multi=None,
                    stats=None, familias_txt="las familias de esta vista",
                    pie=None, meta=None):
    """‹ [sesión] › y su panel (`panel_sesion.js`). `prefijo` es el de TODAS
    sus keys (`ajses_<vista>`); `stats`, lo de `stats_de_vista`; `pie` y
    `meta`, ver `datos_panel_sesion`."""
    if not sesiones:
        st.caption("Sin sesiones de inventario.")
        return
    multi = bool(k_multi and st.session_state.get(k_multi))
    solo = bool(st.session_state.get(_k_solo(k)))
    actual = sesion_vigente(k, sesiones)
    elegidas = sesiones_elegidas(k, sesiones, k_varias, k_multi)
    orden = [x["clave"] for x in sesiones]
    visibles = [x["clave"] for x in sesiones
                if not solo or x["tipo"] == "cierre"]
    i = orden.index(actual["clave"])
    hay_ant = not multi and any(orden.index(c) < i for c in visibles)
    hay_sig = not multi and any(orden.index(c) > i for c in visibles)
    if multi and len(elegidas) > 1:
        etiqueta = f"{len(elegidas)} sesiones sumadas"
    else:
        etiqueta = (elegidas[0] if multi else actual)["corto"]
    k_panel = f"{prefijo}_panels"

    def _al_accion():
        # Un callback de componente no recibe argumentos: lo elegido se lee
        # de su key. Corre ANTES del rerun de la vista.
        a = (st.session_state.get(k_panel) or {}).get("accion") or {}
        tipo = a.get("tipo")
        if tipo == "elegir" and a.get("k") in orden:
            st.session_state[k] = a["k"]
        elif tipo == "varias" and k_varias:
            ks = [x for x in (a.get("ks") or []) if x in orden]
            if ks:
                st.session_state[k_varias] = ks
        elif tipo == "solo":
            st.session_state[_k_solo(k)] = bool(a.get("v"))
        elif tipo == "multi" and k_multi:
            _poner_multi(k_multi, k_varias, k, bool(a.get("v")))

    with st.container(key=f"{prefijo}_fila", horizontal=True, gap="small",
                      vertical_alignment="center"):
        st.button("‹", key=f"{prefijo}_ant", disabled=not hay_ant,
                  help=("Con varias sesiones las flechas se apagan" if multi
                        else "Sesión anterior"),
                  on_click=_paso_sesion, args=(k, orden, visibles, -1))
        with st.popover(etiqueta, key=f"{prefijo}_pop"):
            _PANEL_SESION(
                key=k_panel,
                data=datos_panel_sesion(
                    sesiones, actual, {x["clave"] for x in elegidas}, multi,
                    bool(k_multi), solo, stats, familias_txt, pie, meta),
                on_accion_change=_al_accion, width="content")
        st.button("›", key=f"{prefijo}_sig", disabled=not hay_sig,
                  help=("Con varias sesiones las flechas se apagan" if multi
                        else "Sesión siguiente"),
                  on_click=_paso_sesion, args=(k, orden, visibles, 1))


def _periodo_pivote_ajuste(fechas, gran):
    """Clave ordenable + etiqueta corta de periodo para la tabla dinámica
    de Ajuste, en las 2 granularidades del selector (Corte/Mes). Corte
    agrupa por rachas de días (`_cortes_por_racha`); Mes reusa
    `_periodo_serie` (graficos/compras/_comun.py, re-exportada vía
    graficos.compras — "reusar desde ahí, no duplicar" per
    arquitectura.md) para la clave, con etiqueta propia porque acá el mes
    va abreviado en español (_MESES_ABR_ES). «Semana» se quitó el
    2026-10-02: el ajuste se mide por conteo, no por semana (regla #585)."""
    if gran == "Corte":
        return _cortes_por_racha(fechas)
    clave = _periodo_serie(fechas, gran)
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


def filtro_area_en_titulo(col, df, col_area, col_ajuste_val, clave, key_ctrl):
    """El filtro de Área de una vista de Tiempo, en la fila de su TÍTULO.

    Mismo disparador minimalista que Cascada/Mapa/Distribución (la etiqueta
    ES el valor vigente: «todas las áreas», «barra», «3 áreas»; lo estila
    `css_filtros_vista` por el prefijo de `key_ctrl`) y mismas opciones: las
    áreas que MOVIERON algo en lo que la vista ya tiene (#424). Nació el
    2026-09-23 al mudar el Área del compartimento de arriba de la pila a
    cada vista de Tiempo (regla #505), así que la selección es de ESTA
    vista, en su propia `clave`.

    `col` es la columna donde va el disparador: el llamador decide la
    posición (en Streamlit la da el orden en que se CREA el contenedor).
    Devuelve `df` ya filtrado, con el área normalizada (sin el espacio de
    «CAVA »): `filtro_pills` compara contra el valor crudo.
    """
    if not col_area or col_area not in df.columns:
        return df
    df = df.assign(**{col_area: df[col_area].astype(str).str.strip()})
    areas = areas_con_ajuste(df, col_area, col_ajuste_val)
    sel = [a for a in (st.session_state.get(clave) or []) if a in areas]
    etq = ("todas las áreas" if not sel
           else sel[0].lower() if len(sel) == 1 else f"{len(sel)} áreas")
    with col.container(key=key_ctrl):
        with st.popover(f":material/apartment: {etq}",
                        use_container_width=True):
            if areas:
                df, _ = filtro_pills(df, col_area, clave, "Área",
                                     valores=areas)
            else:
                st.caption("Ninguna área movió algo en este rango.")
    return df


def estado_filtros_vista(df, df_full, col_fecha, col_familia, col_area,
                         col_ajuste_val, k_corte, k_familia, k_area,
                         familias=FAMILIAS_DE_ENTRADA, historial=0,
                         anio_cortes=False, col_producto=None):
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
    distinto no compara nada. Lo usa la Cascada para la COBERTURA (cuantas
    areas se contaron en los ultimos N cortes) — regla #441.

    `anio_cortes=True` trae TODOS los cortes del AÑO del corte elegido (no
    los ultimos N: la pestaña «Por corte» los quiere todos, del mas nuevo
    al mas viejo), en `cortes_anio`, y sus filas en `d_anio` con la misma
    columna `_corte_clave` y el mismo filtrado que `d_historial`. El año
    sale del corte elegido y no de `today()`: quien mira un corte de 2025
    quiere los cortes de 2025, no los del calendario en curso. Ver regla
    #483.

    Es UN filtrado y no N: se toma la union de los dias de los N cortes de
    una sola pasada y despues se etiqueta cada fila con su corte. Opt-in
    igual, porque el Mapa de calor no lo necesita.

    Desde el 2026-10-11 (regla #632) un «corte» es una SESIÓN de
    inventario (`cortes.sesiones_inventario`): un cierre de mes —todo lo
    registrado del 1 al 7, aunque sean dos conteos— o un parcial. La lista
    es la del parquet entero, por años, y la vista abre en el ÚLTIMO CIERRE,
    no en la última sesión. El año de una sesión es el del mes que cierra.

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
        _todos = sesiones_de(df_full, col_fecha)
        cortes = _todos
    corte = corte_prev = None
    hist_cortes = []
    cortes_anio, base_anio = [], None
    if cortes:
        # Abre en el ÚLTIMO CIERRE de mes (regla #632): lo que se revisa es
        # el cierre, no el recuento suelto que vino después.
        corte = sesion_vigente(k_corte, cortes)
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
        if anio_cortes:
            # TODOS los cortes del año del elegido, mismo etiquetado por día
            # que el historial. Se calcula sobre `base` (aún = df_full) antes
            # de recortarla al corte elegido, unas líneas abajo.
            _anio = _anio_sesion(corte)
            cortes_anio = [c for c in _todos if _anio_sesion(c) == _anio]
            _de_dia_a = {_d: _c["clave"] for _c in cortes_anio
                         for _d in _c["dias"]}
            base_anio = base[_fechas.isin(_de_dia_a)].assign(
                _corte_clave=_fechas[_fechas.isin(_de_dia_a)].map(_de_dia_a))
        base = base[_fechas.isin(set(corte["dias"]))]

    # NORMALIZAR EL AREA, no solo la lista de opciones: `filtro_pills`
    # compara la seleccion contra el valor CRUDO, y el maestro trae
    # "CAVA " con espacio al final. Ver arquitectura.md regla #424.
    def _normalizar(x):
        if x is None or not col_area or col_area not in x.columns:
            return x
        return x.assign(**{col_area: x[col_area].astype(str).str.strip()})

    base, base_hist = _normalizar(base), _normalizar(base_hist)
    base_anio = _normalizar(base_anio)
    # Las opciones las decide el corte ELEGIDO, nunca el anterior: ofrecer
    # un area que no movio nada ahora es ofrecer una pastilla que deja la
    # vista vacia, y de eso se trata `areas_con_ajuste` (#424).
    areas = areas_con_ajuste(base, col_area, col_ajuste_val)
    # Un área elegida en otro corte que en éste no movió nada se suelta
    # ANTES de filtrar: la selección sobrevive al cambio de corte (#467), y
    # sin esto la vista saldría vacía una corrida — hasta que el recorte de
    # `filtro_pills`, que corre al dibujar, la alcanzara.
    sel_area = [a for a in sel_area if a in areas]
    # LAS FAMILIAS SALEN DEL PARQUET ENTERO, no del corte elegido. La semilla
    # se sembraba con las del corte con que ABRE la vista, que es el último:
    # el 15 set 2026 no trajo ENVASES Y EMBALAJES, así que la selección
    # nacía con cuatro y al pasar al 2 set seguía en cuatro — con el TOTAL de
    # la tabla sumando sin Envases y sin nada que lo avisara. Con las
    # opciones fijas la selección es la misma en todos los cortes, y una
    # familia sin líneas en un corte simplemente no aparece en la tabla. Las
    # ÁREAS sí siguen al corte, a propósito (#424). Ver regla #442.
    _src_fam = df_full if (df_full is not None and col_familia
                           and col_familia in df_full.columns) else base
    opc_fam = (sorted(_src_fam[col_familia].dropna().astype(str).unique())
               if col_familia and col_familia in _src_fam.columns else [])
    if opc_fam:
        sembrar_seleccion(pd.DataFrame({col_familia: opc_fam}), col_familia,
                          k_familia, list(familias))
    sel_fam = [f for f in (st.session_state.get(k_familia) or [])
               if f in opc_fam]

    def _aplicar(x):
        if x is None:
            return None
        if sel_area and col_area and col_area in x.columns:
            x = x[x[col_area].astype(str).isin(sel_area)]
        if sel_fam and col_familia and col_familia in x.columns:
            x = x[x[col_familia].astype(str).isin(sel_fam)]
        return x

    # Lo que dice el panel de cada sesión —neto, áreas, productos con
    # diferencia— con las familias de ESTA vista (regla #634).
    stats = (stats_de_vista(df_full, cortes, col_fecha, col_area,
                            col_ajuste_val, col_producto, col_familia, sel_fam)
             if cortes else {})

    return {"base": base, "d": _aplicar(base), "corte": corte,
            "cortes": cortes, "corte_prev": corte_prev,
            "stats_sesiones": stats, "familias_txt": texto_familias(sel_fam),
            "historial_cortes": hist_cortes, "d_historial": _aplicar(base_hist),
            "cortes_anio": cortes_anio, "d_anio": _aplicar(base_anio),
            "areas": areas, "familias": opc_fam,
            "sel_fam": sel_fam, "sel_area": sel_area,
            "col_familia": col_familia, "col_area": col_area,
            "k_corte": k_corte, "k_familia": k_familia, "k_area": k_area}


def render_filtros_vista(cols, est, prefijo_ses):
    """Los tres controles, uno por columna: sesión · familia · area.

    Reciben las columnas ya creadas y no las crean ellos porque el
    llamador decide en que zona van: en Streamlit la posicion la da el
    orden en que se CREA el contenedor, no el orden en que se escribe
    en el. `est` es lo que devolvio `estado_filtros_vista`.

    La sesión es `selector_sesion` desde el 2026-10-11 (regla #632): la
    píldora de los botones de fecha de Compras con ‹ › a los costados y la
    lista por años. Hasta ese día era un popover con las últimas doce, y
    cada clic hacía un `st.rerun()` de la página entera; ahora es un
    callback y recalcula sólo la vista. `prefijo_ses` es el de sus keys
    (`ajses_<vista>`).
    """
    with cols[0]:
        selector_sesion(prefijo_ses, est["k_corte"], est["cortes"],
                        stats=est.get("stats_sesiones"),
                        familias_txt=est.get("familias_txt",
                                             "las familias de esta vista"))
    with cols[1]:
        _n_fam = len(est["sel_fam"])
        _et_fam = ("todas las familias" if not _n_fam
                   else est["sel_fam"][0].lower() if _n_fam == 1
                   else f"{_n_fam} familias")
        with st.popover(f":material/category: {_et_fam}",
                        use_container_width=True):
            filtro_pills(est["base"], est["col_familia"], est["k_familia"],
                         "Familia", valores=est["familias"] or None)
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
