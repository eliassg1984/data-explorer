"""
graficos.ventas_resumen — vista "Resumen ejecutivo" del dashboard de Ventas:
venta total por día (barras partidas por canal de venta, con el total y la
variación día-a-día encima) + volumen de Pax, ticket promedio diario y top
platos.

Nació como un candlestick (mockup tipo "panel bursátil" para restaurantes)
con apertura/cierre = primera/última línea de venta del día — se reemplazó
por barras el 2026-08-11 porque esa apertura/cierre comparaba dos ventas
básicamente al azar (sin relación real entre sí, a diferencia de un precio
de acción) y el color resultante no tenía señal. Ver arquitectura.md
regla #85 para el detalle de por qué se dio de baja.

2026-09-22 — TRES AGREGADOS a pedido (mirando la vista publicada):
  1. Un SELECTOR DE FECHA propio, el mismo trigger-con-rango-escrito de
     Compras (`base.selector_fecha_tarjeta`). No es un filtro paralelo: con
     `categoria=None` escribe la MISMA clave canónica que la píldora de la
     franja, o sea que mover la fecha acá RECARGA el parquet del rango
     nuevo desde R2 (Ventas usa `carga_por_rango`, ver `app.py`). Es la
     segunda puerta al mismo dato — cómoda porque cae en la vista y no
     arriba de todo. De ahí el `st.rerun(scope="app")` del arranque: sin la
     corrida completa el `d` que recibe esta función seguiría siendo el del
     rango viejo.
  2. Dos filtros LOCALES de la vista, Grupo y Servicio, que recortan el `d`
     de esta tarjeta (los de la franja siguen existiendo y se COMPONEN con
     estos — el usuario pidió tenerlos a mano en la vista).
  3. Las barras de "Tendencia diaria" son CLICKEABLES, con un toggle
     Resumen/Detalle debajo — el mismo par que la vista «Compras por
     período» (arquitectura.md regla #476): «Resumen» es el gráfico escrito
     como tabla (una fila por día + total), «Detalle» es el desglose del
     día que se toca (sus platos). El clic sigue el patrón de foco-en-la-key
     de `ventas_comparativo.py` (regla #399): la selección de
     `st.plotly_chart(on_select=...)` persiste entre reruns, así que la key
     lleva el foco y cada clic procesado dispara un rerun de fragment.

2026-09-24 — LA VISTA SE VOLVIÓ LA DE «COMPRAS POR PERÍODO» (reglas #515 y
#516): la barra partida por canal, granularidad Día/Semana/Mes/Año, filtros
de Canal y Tipo de documento, y la zona de abajo (Resumen | Detalle de
pedidos y platos) DENTRO de la tarjeta, con la figura que se acorta cuando
aparece la tabla. Y un ítem se cuenta una vez: el parquet lo repite por
forma de pago.

El detalle profundo por producto (FoodCost, sparklines, %Var vs Año Pasado)
sigue viviendo en "Ranking & FoodCost" — este panel es la foto rápida de un
vistazo, no su reemplazo.
"""

from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cortes
from tema import (ACENTO, ADVERTENCIA, ADVERTENCIA_TEXTO, ERROR, EXITO,
                  GRIS_BORDE, GRIS_TEXTO, LAVANDA_BORDE, PALETA_SERIES,
                  SERIE_PRINCIPAL, TEXTO_PRINCIPAL)
from graficos.base import (
    _card, _compras_layout, _compras_truncar, _resolver, preservar_widgets,
    scope_rerun, selector_fecha_tarjeta,
)
from graficos.compras._comun import (
    GAP_DRILL, _UNIDAD_GRAN, _clave_grilla, _first_point, _limites_periodo,
    _periodo_serie, _variaciones,
)
# LA BARRA PARTIDA POR CANAL ES LA DE «COMPRAS POR PERÍODO» (2026-09-24, a
# pedido: «similar estilo y tamaño»). No se copian las cuentas, se importan:
# el alto de la figura, dónde va la leyenda y el plan de las etiquetas de
# encima de la barra son UNA cuenta (`semanal._alto_area_trazo`), y dos
# copias se desincronizan a la primera que se toque. Regla #515.
from graficos.compras.semanal import (
    _ALTO_FIG_SOLO, _ALTO_TABLA, _ETQ_FUENTE, _ETQ_SEP, _LEYENDA_Y, _LIENZO_PX,
    _del_al, _etiqueta_en_la_punta, _plan_etiquetas, _rotulo_periodo, _techo_etiquetas,
)
from graficos import alturas
from tablas.movimientos_periodo import renderizar_lineas_mov
from tablas.ventas_resumen import (
    renderizar_dias_venta, renderizar_pedidos_venta,
)
from utils import fmt_k

MAX_DIAS = 30    # tope de barras legibles. Mismo espíritu que MAX_SEMANAS de
                 # compras/volatilidad.py (arquitectura.md regla #74): el
                 # filtro de fecha de la franja es un TECHO, no la ventana en
                 # sí — con un rango de "todo el año" cargado, esta vista
                 # sigue mostrando solo los últimos 30 días CON datos.

# Los controles propios de la vista, para que la recarga de fecha
# (`st.rerun(scope="app")`) no se los lleve. Es el mismo mecanismo que
# `_KEYS_WIDGET` de `compras/semanal.py` (arquitectura.md regla #373): ese
# rerun aborta la corrida antes de que estos widgets se registren, y
# Streamlit recolecta el estado de todo widget del fragment que no se
# dibujó. `preservar_widgets` los re-escribe sobre sí mismos antes de
# escalar.
_KEYS_WIDGET_RESUMEN = ("vt_resumen_gran", "vt_resumen_grupo",
                        "vt_resumen_serv", "vt_resumen_canal",
                        "vt_resumen_tdoc", "vt_resumen_modo",
                        "ventas_resumen_top_metrica")

# Las granularidades de «Compras por período», sin «Documento»: en Ventas
# una barra por comprobante son ~60 por día y no se lee ninguna. Abre en
# Día, que es lo que la vista mostraba antes de tener granularidad
# («Tendencia diaria»): quien vuelve la encuentra igual.
_GRAN_OPCIONES = ("Día", "Semana", "Mes", "Año")
_GRAN_DEFAULT = "Día"

_MODO_DETALLE = "Detalle"
_MODO_RESUMEN = "Resumen"
_MODO_OPCIONES = (_MODO_RESUMEN, _MODO_DETALLE)
_MODO_DEFAULT = _MODO_RESUMEN   # "Resumen" no necesita un día en foco: la
                                # tabla del día completo se ve al abrir, y el
                                # clic queda para pasar a "Detalle".

_AYUDA_MODO = (
    "Qué se ve debajo del gráfico. **Resumen**: una fila por barra —su "
    "venta, su peso, lo de cada canal, clientes, ticket y la variación "
    "contra la barra anterior— más el total. **Detalle**: los pedidos de la "
    "barra que toques y, al costado, los platos del que elijas."
)

# Abreviaturas en español para el eje/tabla — Plotly y pandas rotulan en
# inglés si no se les dice otra cosa (misma trampa que arquitectura.md #241).
_DIAS_ABR_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# Opacidad de las barras SIN foco cuando hay un día clickeado. Misma que
# `compras/semanal.py::_ATENUADO` y por el mismo motivo (regla #476).
_ATENUADO = 0.2

# ── Los colores de los canales ─────────────────────────────────────────────
# Son CATEGORÍAS (local, Rappi, Pedidos Ya…), no tramos ordenados, así que
# van con hues distintos de `PALETA_SERIES` y no con la rampa `SERIE_TRAMOS`.
# Se saltan el naranja y el verde: el naranja ya es la línea del Ticket, y
# el verde dice «subió» en la etiqueta de la barra. El primero —el canal
# que más vende, abajo de la pila— es el morado de la marca.
_COLORES_CANAL = [PALETA_SERIES[_i] for _i in (0, 1, 2, 5, 6, 7)]

_SIN_CANAL = "Sin canal"

_KPI_CANALES = 4
"""Canales con tarjeta propia en la fila de KPI; el resto va sumado. Medido
el 2026-09-24 en `ventas.parquet`: son cuatro en todo el histórico (En el
Local 97 %, Rappi 3 %, Pedidos Ya y Para Llevar casi nada), así que hoy el
«N más» no aparece — está para el día que se sume un quinto."""


def _con_alpha(_hex, _a):
    """`#rrggbb` → `rgba(r,g,b,a)`. El foco se atenúa por COLOR y no con
    `marker.opacity` por punto: esa lista sobre barras crashea Plotly en el
    navegador. Copia de `compras/semanal.py::_con_alpha` (regla #476)."""
    _h = _hex.lstrip("#")
    _r, _g, _b = (int(_h[_i:_i + 2], 16) for _i in (0, 2, 4))
    return f"rgba({_r},{_g},{_b},{_a})"


def _fmt_dia(dt):
    """`Timestamp` → «Sáb 20/09», con el día de semana en español."""
    return f"{_DIAS_ABR_ES[dt.weekday()]} {dt.day:02d}/{dt.month:02d}"


def _canal_legible(s):
    """La columna de canal como texto, con los nulos nombrados. Pasa por
    `object` antes del `where` porque el parquet puede traerla como
    categórica, y a una categórica no se le escribe un valor que no tenía."""
    s = s.astype("object")
    return s.where(s.notna(), _SIN_CANAL).astype(str).str.strip()


def _fmt_var_venta(pct):
    """`(texto, color)` de una variación: «+12%» verde, «−4.7%» rojo.

    El formato de `compras._comun._fmt_variacion` (un decimal debajo del
    10 %, el menos tipográfico, «0%» gris) con el color al revés: en
    VENTAS subir es la buena noticia; en Compras, gastar más es rojo."""
    dec = 1 if abs(pct) < 10 else 0
    if round(abs(pct), dec) == 0:
        return "0%", GRIS_TEXTO
    txt = f"{abs(pct):.{dec}f}%"
    return ("+" + txt, EXITO) if pct > 0 else ("−" + txt, ERROR)


def _renglones_barra(total, var):
    """Los renglones de la etiqueta de una barra, como `(plano, html)`: el
    total y la variación contra la barra anterior (`var` es la tupla de
    `_variaciones`). Misma forma que `semanal._renglones_etiqueta`: un
    período que el rango corta dice «parcial» en vez de un porcentaje."""
    if not total:
        return []
    _t = fmt_k(total)
    salida = [(_t, _t)]
    estado, pct, _ = var
    if estado == "ok":
        _v, _c = _fmt_var_venta(pct)
        salida.append((_v, f"<span style='color:{_c}'><b>{_v}</b></span>"))
    elif estado == "parcial":
        salida.append(("parcial", f"<span style='color:{GRIS_TEXTO}'>"
                                  "<i>parcial</i></span>"))
    return salida


def _hover_var_venta(var, nombre_ant):
    """El renglón del hover con la variación, o POR QUÉ no la hay. Empieza
    con `<br>`. Es `compras._comun._hover_variacion` con el color de Ventas
    y sin contar días (el «parcial» ya lo dice la etiqueta)."""
    estado, pct, _ = var
    if estado == "ok":
        _t, _c = _fmt_var_venta(pct)
        return (f"<br>vs {nombre_ant}: "
                f"<span style='color:{_c}'><b>{_t}</b></span>")
    if estado == "parcial":
        return "<br><i>Período incompleto en el rango: sin variación</i>"
    if estado == "ant_parcial":
        return (f"<br><i>Sin variación: la barra anterior ({nombre_ant}) "
                "está incompleta en el rango</i>")
    if estado == "sin_base":
        return f"<br><i>Sin variación: {nombre_ant} no vendió</i>"
    return "<br><i>Primera barra: sin anterior para comparar</i>"


def _nota_var_venta(var, nombre_ant):
    """Lo mismo que `_hover_var_venta`, en texto plano: el tooltip de la
    columna «Variación» de la tabla (AG Grid no entiende HTML)."""
    estado, pct, _ = var
    if estado == "ok":
        return f"vs {nombre_ant}: {_fmt_var_venta(pct)[0]}"
    if estado == "parcial":
        return "Período incompleto en el rango: sin variación"
    if estado == "ant_parcial":
        return (f"Sin variación: la barra anterior ({nombre_ant}) está "
                "incompleta en el rango")
    if estado == "sin_base":
        return f"Sin variación: {nombre_ant} no vendió"
    return "Primera barra: sin anterior para comparar"


def _html_kpi_canales(total, n_dias, canales, extras=()):
    """La fila de KPI de la tarjeta: el total de la vista y lo de cada canal.

    Mismo dibujo que la de «Compras por período»
    (`semanal._html_kpi_vista`), con canales en vez de familias. `canales`
    es `[(nombre, valor), …]` de mayor a menor. Con un solo canal no se
    desglosa nada: el total ya es ese canal.

    `extras` son las tarjetas que siguen a los canales (regla #518):
    `(rótulo, valor, sub, clase, tooltip)` ya escritos."""
    def _tarjeta(rotulo, valor, sub, clase="", tip=""):
        return (f'<div class="vt-kpi {clase}" title="{escape(tip or rotulo)}">'
                f'<span class="vt-kpi-rot">{escape(rotulo)}</span>'
                f'<span class="vt-kpi-val">{escape(valor)}'
                f'<span class="vt-kpi-sub">{escape(sub)}</span></span></div>')

    _n = f"{n_dias:,} día" + ("" if n_dias == 1 else "s")
    partes = [_tarjeta("Venta de la vista", fmt_k(total), _n, "vt-kpi-total",
                       f"Venta de la vista: S/ {total:,.2f} · {_n}")]
    if len(canales) > 1:
        for (nom, v), color in zip(canales[:_KPI_CANALES],
                                   _colores_de(len(canales))):
            p = v / total if total else 0.0
            partes.append(
                f'<div class="vt-kpi" style="--vt-kpi-color:{color}" '
                f'title="{escape(nom)}: S/ {v:,.2f} · {p:.1%}">'
                f'<span class="vt-kpi-rot">{escape(nom)}</span>'
                f'<span class="vt-kpi-val">{escape(fmt_k(v))}'
                f'<span class="vt-kpi-sub">{p:.0%}</span></span></div>')
        resto = canales[_KPI_CANALES:]
        if resto:
            _v = sum(v for _, v in resto)
            _p = _v / total if total else 0.0
            partes.append(_tarjeta(
                f"{len(resto)} más", fmt_k(_v), f"{_p:.0%}", "",
                f"{len(resto)} canales más: S/ {_v:,.2f} · {_p:.1%}"))
    for rot, val, sub, clase, tip in extras:
        partes.append(_tarjeta(rot, val, sub, clase, tip))
    return '<div class="vt-kpis">' + "".join(partes) + "</div>"


def _colores_de(n):
    """Un color por canal, en el orden de la pila (el que más vende primero)."""
    return [_COLORES_CANAL[_i % len(_COLORES_CANAL)] for _i in range(n)]


@st.fragment
def _ventas_resumen(d, col_venta, col_fecha, col_pax, col_pedido, col_prod,
                    col_cant, col_fam=None, col_serv=None, col_canal=None,
                    col_mesero=None, d_pagos=None):
    """"Resumen ejecutivo": selector de fecha + granularidad + filtros de
    Grupo/Servicio/Canal/Tipo de documento + la venta por período partida
    por canal, con su Resumen/Detalle debajo + top platos, todas las piezas
    sobre el MISMO recorte para que cuenten la misma historia.
    """
    # ── 0) La fecha cambió: recargar el parquet del rango nuevo ───────────
    # El selector escribe la clave canónica del rango (`categoria=None`), que
    # es la que lee `carga_por_rango` en `app.py`. Como el `d` de esta
    # función ya está materializado con el rango VIEJO, hay que escalar a una
    # corrida completa para que se vuelva a bajar. Va PRIMERO —antes de
    # dibujar nada— porque el rerun aborta lo que venga después, y
    # `preservar_widgets` salva los controles de la vista de la recolección.
    if st.session_state.pop("vt_resumen_fecha_flag", False):
        preservar_widgets(_KEYS_WIDGET_RESUMEN)
        st.rerun(scope="app")

    if not (col_venta and col_fecha):
        st.info("Faltan columnas (Venta, Fecha) para el resumen ejecutivo.")
        return
    col_tdoc = _resolver(d, ["Tipo Doc", "Tipo Documento", "Nomb Tipo Doc"])
    col_doc = _resolver(d, ["Numero Documento", "Nro Documento"])
    # Las columnas de la tabla ampliada (regla #518). Todas opcionales: sin
    # ellas (el demo, un parquet viejo) la columna no se dibuja.
    col_carta = _resolver(d, ["Precio Oficial Item Ddocumento"])
    col_neto = _resolver(d, ["Neto Total Item Ddocumento"])
    col_desc = _resolver(d, ["Descuento Item Ddocumento"])
    col_pcosto = _resolver(d, ["Precio Costo"])
    col_estado = _resolver(d, ["Estado Documento"])
    col_cort = _resolver(d, ["Motivo Cortesia"])
    col_ldoc = _resolver(d, ["Llave Local Documento"])

    # UN ÍTEM SE CUENTA UNA VEZ (reglas #516 y #517). `ventas.py` ya manda
    # `d` deduplicado (`unico_por_item`); esto queda por si otro llamador no
    # lo hace, y no cuesta nada cuando ya viene limpio.
    col_item = _resolver(d, ["Llave Local Documento Item"])
    if col_item:
        d = d[~(d[col_item].duplicated() & d[col_item].notna())]

    # ── 1) Fila de controles: granularidad · filtros · … · fecha ──────────
    # La granularidad es la de «Compras por período» (2026-09-24, a pedido:
    # «al gráfico de barras le falta granularidad»), sin «Documento»: en
    # Ventas una barra por comprobante son cientos por día. Los cuatro
    # filtros son LOCALES de esta vista y se componen con los chips de la
    # franja; Canal y Tipo de documento se sumaron el mismo día, a pedido.
    # La fecha es el trigger de Compras: al aplicar un atajo recarga (ver 0).
    _ctrl = st.columns([2.2, 1.25, 1.25, 1.25, 1.25, 2.1],
                       vertical_alignment="center")
    with _ctrl[0]:
        gran = st.segmented_control(
            "Agrupar por", _GRAN_OPCIONES, default=_GRAN_DEFAULT,
            required=True, key="vt_resumen_gran",
            label_visibility="collapsed") or _GRAN_DEFAULT

    def _filtro(slot, col, key, rotulo):
        """Un multiselect de la fila, si el parquet trae la columna."""
        if not (col and col in d.columns):
            return []
        with _ctrl[slot]:
            if col == col_canal:
                _ops = sorted(_canal_legible(d[col]).unique().tolist())
            else:
                _ops = sorted(d[col].dropna().astype(str).str.strip()
                              .unique().tolist())
            return st.multiselect(rotulo, _ops, key=key,
                                  placeholder=f"{rotulo}: todos",
                                  label_visibility="collapsed")

    grupo_sel = _filtro(1, col_fam, "vt_resumen_grupo", "Grupo")
    serv_sel = _filtro(2, col_serv, "vt_resumen_serv", "Servicio")
    canal_sel = _filtro(3, col_canal, "vt_resumen_canal", "Canal")
    tdoc_sel = _filtro(4, col_tdoc, "vt_resumen_tdoc", "Documento")
    with _ctrl[5]:
        selector_fecha_tarjeta("vt_resumen", "vt_resumen_fecha_flag",
                               categoria=None)

    def _recorte(df):
        """Los cuatro filtros de la fila, a cualquier df de ventas: al de un
        ítem por fila y al de filas por pago (la propina)."""
        if df is None:
            return None
        if grupo_sel and col_fam in df.columns:
            df = df[df[col_fam].astype(str).str.strip().isin(grupo_sel)]
        if serv_sel and col_serv in df.columns:
            df = df[df[col_serv].astype(str).str.strip().isin(serv_sel)]
        if canal_sel and col_canal in df.columns:
            df = df[_canal_legible(df[col_canal]).isin(canal_sel)]
        if tdoc_sel and col_tdoc in df.columns:
            df = df[df[col_tdoc].astype(str).str.strip().isin(tdoc_sel)]
        return df

    d = _recorte(d)
    d_pagos = _recorte(d_pagos)
    if d is None or d.empty:
        st.info("No hay ventas para los filtros elegidos.")
        return

    def _num(col):
        return pd.to_numeric(d[col], errors="coerce").fillna(0.0)

    fecha = pd.to_datetime(d[col_fecha], errors="coerce")
    cols = {"dia": fecha.dt.normalize(), "fecha": fecha,
            "venta": pd.to_numeric(d[col_venta], errors="coerce")}
    if col_prod:
        cols["prod"] = d[col_prod].astype(str)
    if col_cant:
        cols["cant"] = _num(col_cant)
    _cant = cols.get("cant", pd.Series(1.0, index=d.index))
    if col_pax:
        cols["pax"] = pd.to_numeric(d[col_pax], errors="coerce")
    if col_pedido:
        cols["ped"] = d[col_pedido].astype(str)
    if col_canal and col_canal in d.columns:
        cols["canal"] = _canal_legible(d[col_canal])
    if col_mesero and col_mesero in d.columns:
        cols["mesero"] = d[col_mesero].fillna("").astype(str).str.strip()
    if col_doc:
        cols["doc"] = d[col_doc].fillna("").astype(str)
    # Los cuatro precios (regla #518): carta y costo vienen POR UNIDAD y se
    # multiplican por la cantidad; neto y descuento ya son de la línea
    # (medido: «Sudado a la leña» ×2, precio carta 59, descuento de línea
    # 11,77 = 2 × 5,88).
    if col_carta:
        cols["po"] = _num(col_carta)
        cols["carta"] = cols["po"] * _cant
    if col_neto:
        cols["neto"] = _num(col_neto)
    if col_desc:
        cols["desc"] = _num(col_desc)
    if col_pcosto:
        cols["pc"] = _num(col_pcosto)
        cols["costo"] = cols["pc"] * _cant
    if col_ldoc:
        cols["ldoc"] = d[col_ldoc].astype(str)
    # CORTESÍAS Y ANULADOS NO SON VENTA (regla #518). Las cortesías llegan
    # como comprobantes tipo CORTESIA valorizados a PRECIO CARTA dentro de
    # `VENTA ITEM` (S/ 15.025 del 25 ago al 23 set 2026), y los anulados
    # también suman (S/ 6.521). La vista los saca de la venta —del gráfico,
    # los KPIs y la tabla— y muestra las cortesías en su propio bloque.
    _es_cort = pd.Series(False, index=d.index)
    if col_tdoc:
        _es_cort |= d[col_tdoc].astype(str).str.strip().str.upper() == "CORTESIA"
    if col_cort:
        _es_cort |= d[col_cort].notna() & (d[col_cort].astype(str).str.strip()
                                           != "")
    cols["es_cort"] = _es_cort
    cols["anul"] = (d[col_estado].astype(str).str.strip().str.upper()
                    == "ANULADO") if col_estado else False
    todo = pd.DataFrame(cols).dropna(subset=["dia", "venta"])
    tabla = todo[~todo["es_cort"] & ~todo["anul"]]
    cortesias = todo[todo["es_cort"] & ~todo["anul"]]
    if tabla.empty:
        st.info("Sin ventas en el rango cargado (sólo cortesías o anulados).")
        return

    # En Día, los últimos `MAX_DIAS` días con ventas: más barras que eso no
    # se leen. En las otras granularidades manda el rango de la fecha.
    _nota_recorte = ""
    if gran == "Día":
        dias_disp = sorted(tabla["dia"].unique())
        if len(dias_disp) > MAX_DIAS:
            _desde = dias_disp[-MAX_DIAS]
            tabla = tabla[tabla["dia"] >= _desde]
            cortesias = cortesias[cortesias["dia"] >= _desde]
            _nota_recorte = (f" Recortado a los últimos {MAX_DIAS} días con "
                             "ventas: para ver más, agrupá por semana o mes.")
    tabla = tabla.sort_values("fecha").copy()
    tabla["clave"] = _periodo_serie(tabla["fecha"], gran)
    cortesias = cortesias.assign(
        clave=_periodo_serie(cortesias["fecha"], gran))
    _claves_ok = set(tabla["clave"])
    cortesias = cortesias[cortesias["clave"].isin(_claves_ok)]

    # ── Total por período, y lo que cuelga de él ──────────────────────────
    _sumas = {"total": ("venta", "sum")}
    for _c in ("carta", "neto", "desc", "costo"):
        if _c in tabla.columns:
            _sumas[_c] = (_c, "sum")
    g = (tabla.groupby("clave", as_index=False).agg(**_sumas)
         .sort_values("clave").reset_index(drop=True))

    def _pegar(df):
        """Suma `df` (indexado por clave) a `g`, en cero donde falte."""
        nonlocal g
        g = g.merge(df, left_on="clave", right_index=True, how="left")
        for _c in df.columns:
            g[_c] = g[_c].fillna(0)

    if "ldoc" in tabla.columns:
        _docs = tabla.groupby("clave")["ldoc"].nunique().rename("n_docs")
        _pegar(_docs.to_frame())
        if "desc" in tabla.columns:
            _pegar(tabla[tabla["desc"] > 0].groupby("clave")["ldoc"]
                   .nunique().rename("n_desc").to_frame())
    if "carta" in cortesias.columns:
        _cg = cortesias.groupby("clave")
        _c = _cg["carta"].sum().rename("cort_s").to_frame()
        if "ldoc" in cortesias.columns:
            _c["n_cort"] = _cg["ldoc"].nunique()
        if "costo" in cortesias.columns:
            _c["costo_cort"] = _cg["costo"].sum()
        _pegar(_c)
    if "pc" in tabla.columns:
        # Lo que se vendió SIN costo cargado: 1.191 de 8.706 líneas en el
        # rango medido. El % de costo sale más bajo de lo real y el bloque
        # del costo dice cuánto de la venta está en esa situación.
        _pegar(tabla[tabla["pc"] <= 0].groupby("clave")["venta"].sum()
               .rename("venta_sin_costo").to_frame())

    # PROPINA: una por PAGO, no por plato (regla #517). Sale de las filas por
    # pago (`d_pagos`), tomando cada pago una vez; los anulados no cuentan.
    _col_prop = _resolver(d_pagos, ["Monto Propina", "Propina"]) \
        if d_pagos is not None else None
    _col_pago = _resolver(d_pagos, ["Llave Local Documento Correlativo Pago"]) \
        if d_pagos is not None else None
    if _col_prop and _col_pago and not d_pagos.empty:
        _pg = pd.DataFrame({
            "pago": d_pagos[_col_pago].astype(str),
            "fecha": pd.to_datetime(d_pagos[col_fecha], errors="coerce"),
            "prop": pd.to_numeric(d_pagos[_col_prop],
                                  errors="coerce").fillna(0.0),
            "anul": ((d_pagos[col_estado].astype(str).str.strip().str.upper()
                      == "ANULADO") if col_estado in d_pagos.columns
                     else False),
        }).dropna(subset=["fecha"]).drop_duplicates("pago")
        _pg = _pg[~_pg["anul"]]
        _pg["clave"] = _periodo_serie(_pg["fecha"], gran)
        _pg = _pg[_pg["clave"].isin(_claves_ok)]
        _pgg = _pg.groupby("clave")["prop"]
        _pegar(pd.DataFrame({"propina": _pgg.sum(),
                             "n_prop": _pgg.apply(lambda s: int((s > 0).sum()))}))

    # El plato que dispara el costo: el de mayor exceso de costo sobre su
    # precio de carta en el período. Sale en el bloque del costo cuando el
    # período queda marcado «revisar» (medido: «Menu Sapiens SAT 2026» con
    # costo S/ 765,31 contra precio S/ 175 llevó el 12/09 al 117 %).
    culpables = {}
    if {"pc", "po", "prod"} <= set(tabla.columns):
        _ex = tabla[(tabla["po"] > 0) & (tabla["pc"] > tabla["po"])]
        if not _ex.empty:
            _ex = _ex.assign(exceso=(_ex["pc"] - _ex["po"]) * _cant.loc[_ex.index])
            for _k, _grp in _ex.groupby("clave"):
                _top = _grp.sort_values("exceso", ascending=False).iloc[0]
                culpables[_k] = (_top["prod"], float(_top["pc"]),
                                 float(_top["po"]))

    # ── Volumen: Pax por período (dedup por pedido, mismo criterio que
    # ventas.py::_ventas_grafico_dia) o, sin Pax, pedidos distintos ────────
    vol_label = None
    if col_pax:
        if col_pedido:
            vol = (tabla.groupby(["clave", "ped"], as_index=False)["pax"].max()
                   .groupby("clave", as_index=False)["pax"].sum())
        else:
            vol = tabla.groupby("clave", as_index=False)["pax"].sum()
        g = g.merge(vol, on="clave", how="left")
        g["pax"] = g["pax"].fillna(0)
        vol_label = "Clientes"
    elif col_pedido:
        vol = (tabla.groupby("clave", as_index=False)["ped"].nunique()
               .rename(columns={"ped": "pax"}))
        g = g.merge(vol, on="clave", how="left")
        g["pax"] = g["pax"].fillna(0)
        vol_label = "Pedidos"
    if vol_label:
        g["ticket"] = g["total"] / g["pax"].replace(0, np.nan)
    if "costo" in g.columns and "neto" in g.columns:
        g["pcosto"] = g["costo"] / g["neto"].replace(0, np.nan)

    claves = g["clave"].tolist()
    n_per = len(claves)
    # Cómo se nombra cada período: corto en el eje, largo en el hover y el
    # caption, y de fila en la tabla. Los de Semana y Mes son los de Compras.
    if gran == "Día":
        _dias = [pd.Timestamp(c) for c in claves]
        eje = [f"{_x:%d/%m}" for _x in _dias]
        largo = [f"{_fmt_dia(_x)}/{_x.year}" for _x in _dias]
        fila = [_fmt_dia(_x) for _x in _dias]
    else:
        _rot = [_rotulo_periodo(c, gran) for c in claves]
        eje = [_r[0] for _r in _rot]
        largo = [_r[1] for _r in _rot]
        fila = ([f"{_e} {_limites_periodo(c, gran)[1].year}"
                 for _e, c in zip(eje, claves)] if gran == "Semana"
                else largo)

    # La variación contra la barra anterior, con la regla de Compras (#470):
    # un período que el rango de datos corta dice «parcial» y no un
    # porcentaje — un mes en curso contra uno entero daría «−40 %» sin que
    # nada haya cambiado.
    _rng = (tabla["fecha"].min().date(), tabla["fecha"].max().date())
    _vars = _variaciones(claves, g["total"].tolist(), gran, _rng)
    _var_hov = [_hover_var_venta(_v, largo[_v[2]] if _v[2] is not None
                                 else "") for _v in _vars]

    # Venta por período × canal, ALINEADA a `claves` y con las columnas por
    # NOMBRE, no por posición (regla #481). Los canales en orden de venta:
    # el que más vende abajo de la pila.
    if "canal" in tabla.columns:
        por_canal = (tabla.pivot_table(index="clave", columns="canal",
                                       values="venta", aggfunc="sum")
                     .reindex(claves).fillna(0.0))
        _tot_canal = por_canal.sum().sort_values(ascending=False)
        canales = [c for c in _tot_canal.index if _tot_canal[c] != 0]
    else:
        por_canal = pd.DataFrame({"Venta": g["total"].to_numpy()},
                                 index=claves)
        _tot_canal = por_canal.sum()
        canales = ["Venta"]
    _partida = len(canales) > 1
    _colores = _colores_de(len(canales)) if _partida else [SERIE_PRINCIPAL]

    # El reparto del período, al final del hover de CADA tramo: el hover de
    # un tramo dice su canal, pero la pregunta es «¿y los otros?».
    if _partida:
        _reparto = []
        for _j, _t in enumerate(g["total"]):
            _ls = [f"{c}: S/ {por_canal[c].iloc[_j]:,.0f}"
                   + (f" · {por_canal[c].iloc[_j] / _t:.0%}" if _t else "")
                   for c in canales if por_canal[c].iloc[_j]]
            _reparto.append(f"<br><span style='color:{GRIS_TEXTO}'>"
                            "Por canal</span><br>" + "<br>".join(_ls))
    else:
        _reparto = [""] * n_per

    # ── Foco, modo y clic: se resuelven ANTES de dibujar (#398, #399) ─────
    # Todo como en «Compras por período» (regla #516): la figura CEDE su
    # sitio a la tabla de abajo, así que su alto depende del modo y del
    # foco, y los dos tienen que estar resueltos antes de armarla. El foco
    # es la CLAVE del período, no su posición: una posición sobrevive a un
    # cambio de rango apuntando a otro período. Cambiar la granularidad o un
    # filtro lo suelta — una clave de «Semana» no existe en «Mes».
    _ctx = (gran, tuple(grupo_sel), tuple(serv_sel), tuple(canal_sel),
            tuple(tdoc_sel), claves[0], claves[-1])
    if st.session_state.get("vt_resumen_ctx_prev") != _ctx:
        st.session_state["vt_resumen_ctx_prev"] = _ctx
        st.session_state["vt_resumen_foco"] = None
        st.session_state["vt_resumen_ped"] = None
    # Un clic en una FILA del Resumen pidió abrir su Detalle en la corrida
    # anterior: la grilla se dibuja DEBAJO del toggle de modo, y la key de
    # un widget ya dibujado no se puede escribir — el pedido viaja hasta
    # acá, que es antes del toggle. Mismo arreglo que Movimientos.
    _ir = st.session_state.pop("_vt_resumen_ir_detalle", None)
    if _ir is not None:
        st.session_state["vt_resumen_foco"] = _ir
        st.session_state["vt_resumen_ped"] = None
        st.session_state["vt_resumen_modo"] = _MODO_DETALLE
    # EL MODO SE LEE DE `session_state` Y NO DEL WIDGET: el toggle se
    # dibuja debajo de la figura y el alto de la figura depende de él.
    _modo = st.session_state.get("vt_resumen_modo")
    if _modo not in _MODO_OPCIONES:
        _modo = _MODO_DEFAULT
    _foco_antes = st.session_state.get("vt_resumen_foco")
    # LA KEY DEL GRÁFICO ES UN CONTADOR (regla #399): el clic se lee de la
    # key que se DIBUJÓ la corrida anterior, y el contador sube en la misma
    # corrida en que se lee, así que el gráfico ya se dibuja con la key
    # donde se va a buscar el próximo clic.
    _nclic = st.session_state.get("vt_resumen_nclic", 0)
    _key_base = f"ventas_g_resumen_{gran}"
    _pt = _first_point(st.session_state.get(f"{_key_base}_{_nclic}"))
    if _pt is not None:
        _nclic += 1
        st.session_state["vt_resumen_nclic"] = _nclic
        # Todas las trazas (los tramos, Clientes y Ticket) comparten el eje
        # de períodos, así que el índice del punto ES el período.
        _pi = _pt.get("point_index", _pt.get("point_number"))
        _clic = (claves[_pi] if isinstance(_pi, int) and 0 <= _pi < len(claves)
                 else None)
        if _clic is None:
            pass
        elif _modo == _MODO_RESUMEN:
            # Desde Resumen el clic ABRE el Detalle de esa barra (el gesto es
            # «mostrame ésta»), como en Compras (regla #476).
            st.session_state["vt_resumen_ped"] = None
            st.session_state["vt_resumen_foco"] = _clic
            st.session_state["vt_resumen_modo"] = _MODO_DETALLE
            _modo = _MODO_DETALLE
        elif st.session_state.get("vt_resumen_ped"):
            # Con un pedido elegido, la barra SUBE un nivel (vuelve al
            # período entero) en vez de apagarlo todo.
            st.session_state["vt_resumen_ped"] = None
            st.session_state["vt_resumen_foco"] = _clic
        else:
            st.session_state["vt_resumen_foco"] = (
                None if _foco_antes == _clic else _clic)
    foco = st.session_state.get("vt_resumen_foco")
    _foco_ok = foco in set(claves)
    _con_tabla = _modo == _MODO_RESUMEN or _foco_ok
    # Resumen no atenúa: su tabla son TODAS las barras (regla #476).
    _foco_ix = (claves.index(foco)
                if _foco_ok and _modo == _MODO_DETALLE else None)

    _titulo = {"Día": "Tendencia diaria de venta",
               "Semana": "Venta por semana", "Mes": "Venta por mes",
               "Año": "Venta por año"}[gran]
    with _card("ventas_resumen_dia", _titulo, titulo_arriba=True):
        # La fila de KPI: el total de la vista y lo de cada canal. Misma
        # pieza que la de «Compras por período», con canales por familias.
        with st.container(key="vt_resumen_kpi"):
            st.markdown(_html_kpi_canales(
                float(g["total"].sum()), int(tabla["dia"].nunique()),
                [(c, float(_tot_canal[c])) for c in canales]
                if _partida else [], _kpis_extra(g)),
                unsafe_allow_html=True)

        # UNA sola figura (no make_subplots): la selección por clic de
        # `st.plotly_chart(on_select=...)` NO llega a las trazas de un
        # subplot —medido el 2026-09-22, `evt.selection.points` volvía
        # SIEMPRE vacío al clickear una barra de un `make_subplots`, y con
        # eso el drill no abría nunca—. Todas las vistas clickeables del
        # repo son figuras únicas (semanal, comparativo, volatilidad); acá
        # el volumen baja de subplot propio a una línea punteada sobre un
        # eje Y secundario, que es como `ventas.py::_ventas_grafico_dia`
        # dibuja Pax. Ver arquitectura.md regla #488.
        _hay_ticket = vol_label and "ticket" in g.columns
        # LA FIGURA SE ACORTA CUANDO HAY TABLA (regla #516): los mismos dos
        # altos que «Compras por período» — el suyo entero sin tabla y
        # COMPACTO con ella, que le deja a la grilla `_ALTO_TABLA`.
        _alto_fig = alturas.COMPACTO if _con_tabla else _ALTO_FIG_SOLO

        # ── La etiqueta de encima: total + variación (plan de Compras) ──
        # `_plan_etiquetas` decide la forma (derecha / girada / unida) y
        # cuántos renglones entran, contra los píxeles de cada barra; lo que
        # no entra sigue en el hover.
        _reng = [_renglones_barra(t, v) for t, v in zip(g["total"], _vars)]
        _plan_etq, _k_etq, _alto_etq = _plan_etiquetas(
            len(g), [[_p for _p, _ in _r] for _r in _reng], _alto_fig)
        _textos = [None] * len(g)
        if _plan_etq:
            _sep = _ETQ_SEP if _plan_etq == "unida" else "<br>"
            _textos = [(_sep.join(_h for _, _h in _r[:_k_etq]) or None)
                       for _r in _reng]
        # LA TAPA DEL DESCUENTO (regla #518): encima de la venta, lo que
        # faltó para llegar a precio carta. La barra entera mide la carta y
        # la parte llena, lo cobrado. La etiqueta sube a la punta de la tapa
        # (`_etiqueta_en_la_punta` la pone en el tramo más alto con valor).
        _hay_tapa = "carta" in g.columns and float(g["carta"].sum()) > 0
        _tapa = ((g["carta"] - g["total"]).clip(lower=0).to_numpy()
                 if _hay_tapa else None)
        _tramos = [pd.DataFrame({"valor": por_canal[c].to_numpy()})
                   for c in canales]
        if _hay_tapa:
            _tramos.append(pd.DataFrame({"valor": _tapa}))
        _textos_tr = (_etiqueta_en_la_punta(_tramos, _textos) if _plan_etq
                      else [None] * len(_tramos))
        # `constraintext="none"`: sin él Plotly ENCOGE la etiqueta que no
        # entra en la barra en vez de dejarla afuera a su tamaño.
        _estilo_etq = dict(
            textposition="outside", cliponaxis=False, constraintext="none",
            textangle=-90 if _plan_etq in ("girada", "unida") else 0,
            textfont=dict(size=_ETQ_FUENTE, color=TEXTO_PRINCIPAL))

        fig = go.Figure()
        # El eje es LINEAL por índice, como el de Compras (su comentario
        # «EL EJE ES LINEAL, Y NO POR GUSTO»): una clave como «2025» en un
        # eje de categorías Plotly la lee como número (#448), y las
        # punteadas de los lunes caen en `i − 0.5`.
        _xs = list(range(n_per))
        _rot_total = {"Día": "Total del día", "Semana": "Total de la semana",
                      "Mes": "Total del mes", "Año": "Total del año"}[gran]
        _cd = list(zip(largo, g["total"], _var_hov, _reparto))
        for _i, (c, _col) in enumerate(zip(canales, _colores)):
            # AL HACER CLIC, ESE PERÍODO SE ILUMINA Y EL RESTO SE ATENÚA — el
            # mismo gesto que «Compras por período» (regla #476): por COLOR
            # (alfa `_ATENUADO`), nunca con `marker.opacity` por punto, que
            # sobre barras con texto encima crashea Plotly. Cada canal
            # conserva su tono; lo que se marca es el PERÍODO entero.
            _color = ([_col if _j == _foco_ix else _con_alpha(_col, _ATENUADO)
                       for _j in range(n_per)] if _foco_ix is not None
                      else _col)
            fig.add_trace(go.Bar(
                x=_xs, y=por_canal[c].to_numpy(), name=c, yaxis="y",
                marker=dict(color=_color), customdata=_cd,
                hovertemplate=(
                    "%{customdata[0]}"
                    + (f"<br><b>{escape(c)}</b>: S/ %{{y:,.0f}}"
                       if _partida else "")
                    + f"<br>{_rot_total}: S/ %{{customdata[1]:,.0f}}"
                    "%{customdata[2]}%{customdata[3]}<extra></extra>"),
            ))
            if _plan_etq:
                fig.data[-1].update(text=_textos_tr[_i], **_estilo_etq)
        if _hay_tapa:
            _pdesc = [(t / c if c else 0.0)
                      for t, c in zip(_tapa, g["carta"])]
            fig.add_trace(go.Bar(
                x=_xs, y=_tapa, name="Descuento", yaxis="y",
                marker=dict(color=(
                    [LAVANDA_BORDE if _j == _foco_ix
                     else _con_alpha(LAVANDA_BORDE, _ATENUADO)
                     for _j in range(n_per)] if _foco_ix is not None
                    else LAVANDA_BORDE)),
                customdata=list(zip(largo, g["carta"], _pdesc)),
                hovertemplate=("%{customdata[0]}<br><b>Descuentos</b>: "
                               "S/ %{y:,.0f} · %{customdata[2]:.1%} de la "
                               "carta<br>A precio carta: "
                               "S/ %{customdata[1]:,.0f}<extra></extra>"),
            ))
            if _plan_etq:
                fig.data[-1].update(text=_textos_tr[-1], **_estilo_etq)
        fig.update_layout(barmode="stack")
        if vol_label:
            fig.add_trace(go.Scatter(
                x=_xs, y=g["pax"], name=vol_label, mode="lines",
                line=dict(color=GRIS_TEXTO, width=1.5, dash="dot"),
                yaxis="y2", customdata=largo,
                hovertemplate=("%{customdata}<br>" + vol_label
                               + ": %{y:,.0f}<extra></extra>"),
            ))
        # Ticket promedio como línea + puntos sobre un TERCER eje (soles,
        # pero otra escala que la venta: ~S/ 180 contra ~S/ 25.000). Va en su
        # propio eje a la derecha —igual que `ventas.py::_ventas_grafico_dia`
        # con Pax/Venta— para que las escalas no se aplasten. Antes era una
        # tarjeta aparte; se subió acá a pedido el 2026-09-22.
        if _hay_ticket:
            fig.add_trace(go.Scatter(
                x=_xs, y=g["ticket"], name="Ticket", mode="lines+markers",
                line=dict(color=ADVERTENCIA, width=2), marker=dict(size=5),
                yaxis="y3", customdata=largo,
                hovertemplate=("%{customdata}<br>Ticket: S/ %{y:,.2f}"
                               "<extra></extra>"),
            ))

        # FIN DE SEMANA Y FERIADO (regla #518): la banda de «Comparativo vs
        # año pasado» (`ventas_comparativo.py`), mismos colores y mismo
        # rótulo. En Día se sombrea el día; en Semana/Mes/Año no hay día que
        # sombrear y se cuenta cuántos feriados trae el período.
        _feriados = _feriados_de(claves, gran)
        if gran == "Día":
            for _i, _x in enumerate(_dias):
                _fer = _x.date() in _feriados
                if not (_fer or _x.weekday() >= 5):
                    continue
                fig.add_vrect(
                    x0=_i - 0.5, x1=_i + 0.5, layer="below", line_width=0,
                    fillcolor=ADVERTENCIA_TEXTO if _fer else GRIS_TEXTO,
                    opacity=0.10 if _fer else 0.07)
                if _fer:
                    fig.add_annotation(
                        x=_i, y=1.0, yref="paper", yanchor="bottom",
                        showarrow=False, text="feriado",
                        font=dict(size=10, color=ADVERTENCIA_TEXTO))
        else:
            for _i, c in enumerate(claves):
                _n = sum(1 for _f in _feriados
                         if _limites_periodo(c, gran)[0] <= _f
                         <= _limites_periodo(c, gran)[1])
                if _n:
                    fig.add_annotation(
                        x=_i, y=1.0, yref="paper", yanchor="bottom",
                        showarrow=False,
                        text=f"{_n} feriado" + ("" if _n == 1 else "s"),
                        font=dict(size=10, color=ADVERTENCIA_TEXTO))

        # División sutil entre semanas, sólo en Día (un lunes = arranca
        # semana nueva): línea punteada gris clara que cruza la figura, entre
        # la barra del lunes y la anterior. No en el primer día mostrado:
        # una línea pegada al borde izquierdo no divide nada.
        if gran == "Día":
            for _i, _x in enumerate(_dias):
                if _i and _x.weekday() == 0:
                    fig.add_shape(
                        type="line", xref="x", yref="paper",
                        x0=_i - 0.5, x1=_i - 0.5, y0=0, y1=1,
                        line=dict(color=GRIS_BORDE, width=1, dash="dot"),
                        opacity=0.8, layer="below",
                    )

        # El alto es el de la figura de «Compras por período» (pedido:
        # «similar tamaño»), y la leyenda va DEBAJO como allá: el techo de
        # las etiquetas se calcula con esa leyenda en ese lugar
        # (`semanal._LEYENDA_Y`). `_xright` recorta el dominio del eje X
        # para hacerle lugar al tercer eje (el del ticket) a la derecha,
        # como `_ventas_grafico_dia`.
        _xright = 0.88 if _hay_ticket else 1.0
        _compras_layout(fig, alto=_alto_fig)
        _rng_y = (_techo_etiquetas(
            float(g["carta"].max() if _hay_tapa else g["total"].max()), 0.0,
            _alto_fig, _alto_etq) if _plan_etq else None)
        fig.update_layout(
            showlegend=bool(vol_label) or _partida or _hay_tapa,
            # `traceorder="normal"`: con barras apiladas Plotly invierte la
            # leyenda por defecto, y salía «Ticket · Clientes · Rappi · En
            # el Local» — el canal principal al final.
            # `yanchor="top"`: con `y` negativo Plotly ancla la leyenda por
            # ABAJO («auto» debajo de 1/3), así que crece hacia el eje y en
            # COMPACTO se comía los rótulos (medido: 15px encima).
            legend=dict(orientation="h", y=-_LEYENDA_Y, yanchor="top", x=0,
                        font=dict(size=10), traceorder="normal"),
            margin=dict(l=10, r=(70 if _hay_ticket else 50 if vol_label else 10),
                        t=30, b=10),
            yaxis=dict(tickprefix="S/ ", gridcolor=GRIS_BORDE,
                       **({"range": _rng_y} if _rng_y else {})),
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        title=vol_label or "", tickformat=",.0f",
                        visible=bool(vol_label)),
            yaxis3=dict(overlaying="y", side="right", anchor="free",
                        position=1.0, showgrid=False, tickprefix="S/ ",
                        tickformat=",.0f", title="Ticket",
                        visible=bool(_hay_ticket)),
        )
        # Un rótulo por período sólo mientras entren HORIZONTALES: girados
        # a −45° se metían en la leyenda de abajo con la figura en COMPACTO.
        # Cuántos entran sale del rótulo más largo, con la cuenta del eje de
        # Compras (6.3px por carácter a 12px + 12 de aire, `semanal.py`)
        # contra el lienzo que deja el eje del ticket.
        _lienzo = _LIENZO_PX * _xright
        _caben = max(1, int(_lienzo // (max(map(len, eje)) * 6.3 + 12)))
        _paso = max(1, -(-n_per // _caben))
        _tv = list(range(0, n_per, _paso))
        fig.update_xaxes(
            domain=[0.0, _xright], type="linear", tickmode="array",
            tickvals=_tv, ticktext=[eje[_i] for _i in _tv],
            range=[-0.5, n_per - 0.5], tickangle=0, tickfont=dict(size=10),
        )
        # MODO CLIC, no "select": al poner `on_select`, Streamlit deja el
        # dragmode en "select" (caja), y con eso un clic SUELTO no selecciona
        # nada (arquitectura.md regla #388). En "pan" Streamlit pone
        # clickmode="event+select" y el clic vuelve a abrir el detalle; los
        # ejes fijos dejan quieto el arrastre. Medido el 2026-09-22: sin esto
        # `evt.selection.points` volvía siempre vacío al clickear una barra.
        fig.update_layout(dragmode="pan")
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)
        # Lo que devuelve se IGNORA: el clic ya se leyó arriba, antes de
        # armar la figura (ver «Foco, modo y clic»).
        st.plotly_chart(
            fig, use_container_width=True, key=f"{_key_base}_{_nclic}",
            on_select="rerun", selection_mode="points",
            config={"displaylogo": False, "displayModeBar": False})

        # ── LA FILA QUE ELIGE QUÉ SE VE ABAJO, DENTRO de la tarjeta ──────
        # El toggle y, al lado, el caption que nombra el ámbito: la fila
        # `cp_sem_pie` de Compras. Hasta el 2026-09-24 el toggle vivía
        # afuera de la tarjeta y la explicación de colores era un caption
        # propio; los colores los dice ahora la etiqueta de cada barra.
        with st.container(horizontal=True, gap="small", key="vt_resumen_pie"):
            st.segmented_control(
                "Qué se ve abajo", _MODO_OPCIONES, default=_MODO_DEFAULT,
                required=True, key="vt_resumen_modo",
                label_visibility="collapsed", help=_AYUDA_MODO)
            _pie = st.empty()

        if _modo == _MODO_RESUMEN:
            _zona_resumen(g, claves, fila, _vars, foco if _foco_ok else None,
                          vol_label, por_canal, canales if _partida else [],
                          gran, _ctx, _pie, _rng, _nota_recorte,
                          feriados=_feriados, culpables=culpables)
        elif not _foco_ok:
            # El `st.empty()` sólo en esta rama, como en Compras (regla
            # #471): borra las grillas al soltar el foco sin re-montarlas en
            # cada corrida mientras hay detalle.
            st.empty()
            _pie.caption("Tocá una barra —o una fila del Resumen— para ver "
                         "sus pedidos.")
        else:
            _zona_detalle(tabla, foco, largo[claves.index(foco)], gran,
                          _partida, _ctx, _nclic, _pie)

    # (La tarjeta «Ticket promedio diario» que vivía acá se quitó el
    # 2026-09-22: el ticket es ahora la línea naranja del gráfico de arriba.)

    # ── Top platos (Ingreso / Cantidad) ──────────────────────────────────
    if col_prod:
        with _card("ventas_resumen_top", "Top platos vendidos", titulo_arriba=True):
            agg = {"ingreso": ("venta", "sum")}
            agg["cantidad"] = ("cant", "sum") if col_cant else ("venta", "count")
            top = tabla.groupby("prod").agg(**agg).reset_index()

            metrica = st.pills(
                "Métrica", ["Ingreso", "Cantidad"], default="Ingreso",
                key="ventas_resumen_top_metrica", label_visibility="collapsed",
            ) or "Ingreso"
            campo = "ingreso" if metrica == "Ingreso" else "cantidad"
            top = top.sort_values(campo, ascending=False).head(8).sort_values(campo)

            if top.empty:
                st.info("Sin datos de productos en el rango.")
            else:
                _txt = ([f"S/ {v:,.0f}" for v in top[campo]] if metrica == "Ingreso"
                        else [f"{v:,.0f} uds" for v in top[campo]])
                fig_p = go.Figure(go.Bar(
                    x=top[campo], y=[_compras_truncar(p, 26) for p in top["prod"]],
                    orientation="h", marker=dict(color=ACENTO),
                    text=_txt, textposition="outside", cliponaxis=False,
                    hovertemplate=("%{y}<br>" + ("S/ %{x:,.0f}" if metrica == "Ingreso"
                                                 else "%{x:,.0f} unidades")
                                  + "<extra></extra>"),
                ))
                _compras_layout(fig_p, alto=alturas.por_filas(
                    len(top), px_fila=40, minimo=240, extra=60,
                    rol=alturas.APOYO))
                fig_p.update_layout(
                    showlegend=False, margin=dict(l=10, r=90, t=10, b=10),
                    xaxis=dict(tickprefix="S/ " if metrica == "Ingreso" else ""),
                )
                st.plotly_chart(fig_p, use_container_width=True,
                                key="ventas_g_resumen_top")


# ===========================================================================
# LA ZONA DE ABAJO: Resumen y Detalle (2026-09-24, regla #516)
# ===========================================================================
# Las de «Compras por período», adentro de la tarjeta y a `_ALTO_TABLA`:
# la figura baja a COMPACTO cuando están, así que la tarjeta mide lo mismo
# en Resumen y en Detalle. Las grillas viven en `tablas/ventas_resumen.py`.

def _zona_resumen(g, claves, fila, variaciones, foco, vol_label, por_canal,
                  canales, gran, ctx, pie, rango, nota_recorte,
                  feriados=frozenset(), culpables=None):
    """El gráfico escrito como tabla, en la forma «B» del mockup (regla
    #518): nueve columnas y, al hacer clic en una fila, una franja con los
    canales, las propinas, los descuentos, las cortesías y el detalle del
    costo. «Ver pedidos» en la franja abre el Detalle de ese período."""
    culpables = culpables or {}
    n = len(claves)
    tot = g["total"].astype(float).tolist()
    tot_vista = float(sum(tot))
    hay = set(g.columns)

    def _col(nombre):
        return (g[nombre].astype(float).tolist() if nombre in hay
                else [None] * n)

    carta, neto, costo = _col("carta"), _col("neto"), _col("costo")
    pcosto, pax, ticket = _col("pcosto"), _col("pax"), _col("ticket")
    desc, n_desc, n_docs = _col("desc"), _col("n_desc"), _col("n_docs")
    cort, n_cort, costo_cort = _col("cort_s"), _col("n_cort"), _col("costo_cort")
    prop, n_prop = _col("propina"), _col("n_prop")
    sin_costo = _col("venta_sin_costo")

    def _ratio(a, b):
        return [(x / y if (x is not None and y) else None)
                for x, y in zip(a, b)]

    pdesc, pcort, pprop = _ratio(desc, carta), _ratio(cort, carta), _ratio(prop, tot)

    def _pp(serie, i):
        """El cambio de un % contra la barra anterior, en puntos."""
        if not i or serie[i] is None or serie[i - 1] is None:
            return None
        return (serie[i] - serie[i - 1]) * 100

    def _var(serie, i):
        """La variación de un MONTO contra la barra anterior; sólo cuando la
        de la venta es comparable (un período cortado no se compara)."""
        v = variaciones[i]
        if v[0] != "ok" or serie[i] is None or not serie[v[2]]:
            return None
        return (serie[i] - serie[v[2]]) / serie[v[2]] * 100

    def _txt_pp(p, malo_si_sube=True):
        """`(texto, clase)` de un cambio en pp."""
        if p is None:
            return "", ""
        if abs(p) < 0.05:
            return "±0 pp", "vr-neutro"
        malo = p > 0 if malo_si_sube else p < 0
        return (f"{'+' if p > 0 else '−'}{abs(p):.1f} pp",
                "vr-baja" if malo else "vr-sube")

    def _txt_var(v):
        if v is None:
            return "", ""
        if abs(v) < 0.5:
            return "0%", "vr-neutro"
        return (f"{'+' if v > 0 else '−'}{abs(v):.0f}%",
                "vr-sube" if v > 0 else "vr-baja")

    def _span(txt, clase):
        return f'<span class="vr-nota {clase}">{escape(txt)}</span>' if txt else ""

    def _bloque(titulo, grande, fino, aviso=False):
        # El número va en el renglón del título: un renglón menos por
        # bloque, y la franja entra en la grilla de `_ALTO_TABLA`.
        return (f'<div class="vr-b{" vr-aviso" if aviso else ""}">'
                f'<span class="vr-cab"><span class="vr-h">{escape(titulo)}'
                f'</span><span class="vr-g">{grande}</span></span>'
                f'<span class="vr-f">{fino}</span></div>')

    def _franja(i):
        partes = []
        if canales:
            _ls = []
            for c, color in zip(canales, _colores_de(len(canales))):
                v = float(por_canal[c].iloc[i])
                sh = v / tot[i] if tot[i] else 0.0
                sh_ant = (float(por_canal[c].iloc[i - 1]) / tot[i - 1]
                          if i and tot[i - 1] else None)
                _p = _txt_pp((sh - sh_ant) * 100 if sh_ant is not None
                             else None, malo_si_sube=False)
                _v = _txt_var(_var(por_canal[c].astype(float).tolist(), i))
                _ls.append(
                    f'<span class="vr-canal"><i style="background:{color}">'
                    f'</i><b>{escape(c)}</b>S/ {v:,.0f} · {sh:.0%}'
                    f'{_span(*_p)}{_span(*_v)}</span>')
            partes.append(
                '<div class="vr-b vr-ancho" title="Monto · % de la venta del '
                'período · cambio de ese % en pp · variación del monto contra '
                'la barra anterior"><span class="vr-h">Venta por canal</span>'
                + "".join(_ls) + "</div>")
        if prop[i] is not None:
            _v = _txt_var(_var(prop, i))
            _pc = f"S/ {prop[i] / pax[i]:,.2f}/cliente · " if pax[i] else ""
            partes.append(_bloque(
                "Propinas", f"S/ {prop[i]:,.0f}{_span(*_v)}",
                f"{pprop[i]:.1%} de la venta{_span(*_txt_pp(_pp(pprop, i), False))}"
                f" · {_pc}{int(n_prop[i] or 0)} pagos"))
        if pdesc[i] is not None:
            _cuantos = (f" · {int(n_desc[i] or 0)} de {int(n_docs[i] or 0)} "
                        "comprobantes" if n_docs[i] else "")
            partes.append(_bloque(
                "Descuentos", f"{pdesc[i]:.1%}{_span(*_txt_pp(_pp(pdesc, i)))}",
                f"S/ {desc[i]:,.0f} bajo la carta{_cuantos}"))
        if pcort[i] is not None:
            _cc = (f" · costaron S/ {costo_cort[i]:,.0f}"
                   if costo_cort[i] else "")
            partes.append(_bloque(
                "Cortesías", f"{pcort[i]:.1%}{_span(*_txt_pp(_pp(pcort, i)))}",
                f"{int(n_cort[i] or 0)} comp. · S/ {cort[i]:,.0f} a "
                f"carta{_cc}"))
        if pcosto[i] is not None:
            _fino = f"S/ {costo[i]:,.0f} sobre S/ {neto[i]:,.0f} de neto"
            if sin_costo[i]:
                _fino += (f" · {sin_costo[i] / tot[i]:.0%} de la venta sin "
                          "costo cargado")
            partes.append(_bloque(
                "Costo", f"{pcosto[i]:.1%}{_span(*_txt_pp(_pp(pcosto, i)))}",
                _fino, aviso=pcosto[i] > _COSTO_ROTO))
        # El plato que dispara el costo va en el renglón del botón y no en su
        # bloque: adentro alargaba la franja a 156px (medido en el 12/09) en
        # una grilla de 191. El renglón del botón existe igual.
        _cul = culpables.get(claves[i])
        _aviso = ""
        if pcosto[i] is not None and pcosto[i] > _COSTO_ROTO and _cul:
            _aviso = (f'<span class="vr-revisar">Revisar «{escape(_cul[0])}»: '
                      f'costo S/ {_cul[1]:,.2f} por unidad contra precio '
                      f'S/ {_cul[2]:,.2f}</span>')
        partes.append(f'<div class="vr-pie">{_aviso}<button class="vr-ver" '
                      f'type="button">Ver pedidos de {escape(fila[i])} →'
                      '</button></div>')
        return "".join(partes)

    filas = []
    for i, c in enumerate(claves):
        v = variaciones[i]
        r = {"periodo": fila[i], "__tip": fila[i]}
        if gran == "Día" and pd.Timestamp(c).date() in feriados:
            r["__v_periodo"], r["__vc_periodo"] = "feriado", "vr-alto"
        for k, serie in (("carta", carta), ("valor", tot), ("neto", neto),
                         ("costo", costo)):
            if serie[i] is not None:
                r[k] = round(serie[i], 2)
        if pcosto[i] is not None:
            r["pcosto"] = round(pcosto[i], 4)
            r["__t_pcosto"] = f"{pcosto[i]:.1%}"
            r["__c_pcosto"] = ("vr-roto" if pcosto[i] > _COSTO_ROTO
                               else "vr-alto" if pcosto[i] > _COSTO_ALTO else "")
            r["__v_pcosto"], r["__vc_pcosto"] = _txt_pp(_pp(pcosto, i))
            if pcosto[i] > _COSTO_ROTO:
                r["__b_pcosto"] = "revisar"
        if vol_label:
            r["pax"] = pax[i]
            r["ticket"] = None if ticket[i] is None or pd.isna(ticket[i]) \
                else round(ticket[i], 2)
            r["__t_ticket"] = ("—" if r["ticket"] is None
                               else f"S/ {r['ticket']:,.2f}")
            _vt = (None if (v[0] != "ok" or r["ticket"] is None
                            or not ticket[v[2]] or pd.isna(ticket[v[2]]))
                   else (ticket[i] - ticket[v[2]]) / ticket[v[2]] * 100)
            r["__v_ticket"], r["__vc_ticket"] = _txt_var(_vt)
        r["variacion"] = v[1] if v[0] == "ok" else None
        r["__vtxt"] = "parcial" if v[0] == "parcial" else "—"
        r["__nota"] = _nota_var_venta(v, fila[v[2]] if v[2] is not None else "")
        r["__html"] = _franja(i)
        r["__id"] = r["__clave"] = c
        r["__sel"] = c == foco
        filas.append(r)
    tp = pd.DataFrame(filas)

    uni = _UNIDAD_GRAN[gran][0 if n == 1 else 1]
    total = {"__id": "__total", "periodo": f"Total · {n:,} {uni}",
             "valor": f"S/ {tot_vista:,.0f}", "variacion": ""}
    for k in ("carta", "neto", "costo"):
        if k in hay:
            total[k] = f"S/ {float(g[k].sum()):,.0f}"
    if "pcosto" in hay and float(g["neto"].sum()):
        total["pcosto"] = f"{float(g['costo'].sum()) / float(g['neto'].sum()):.1%}"
    if vol_label:
        _tp = float(g["pax"].sum())
        total["pax"] = f"{_tp:,.0f}"
        total["ticket"] = f"S/ {tot_vista / _tp:,.2f}" if _tp else "—"

    n_res = st.session_state.get("vt_resumen_nres", 0)
    with st.container(key="vt_resumen_resumen"):
        clic_fila = renderizar_dias_venta(
            tp, altura=_ALTO_TABLA,
            key="vt_resumen_res_grid_" + _clave_grilla(ctx, n_res),
            rotulo_periodo=gran, vol_label=vol_label, total=total)
    pie.caption(
        f"**{_del_al(pd.Series(pd.to_datetime(list(rango))))}** · agrupado "
        f"por {gran.lower()} — clic en una fila para ver canales, propinas, "
        "descuentos, cortesías y costo; «Ver pedidos» abre el Detalle."
        + nota_recorte)
    if clic_fila in set(claves):
        st.session_state["_vt_resumen_ir_detalle"] = clic_fila
        st.session_state["vt_resumen_nres"] = n_res + 1
        st.rerun(scope=scope_rerun())


_COSTO_ALTO = 0.45
"""% de costo sobre el neto a partir del cual la celda va en ámbar."""

_COSTO_ROTO = 0.70
"""Y a partir del cual el período sale con «revisar»: por encima de eso no es
un día caro, es un costo mal cargado (medido: el 12/09 llegó al 117 % por
un menú con costo S/ 765,31 y precio S/ 175)."""


def _feriados_de(claves, gran):
    """Los feriados nacionales que caen entre la primera y la última barra."""
    if not claves:
        return frozenset()
    ini = _limites_periodo(claves[0], gran)[0]
    fin = _limites_periodo(claves[-1], gran)[1]
    fer = set()
    for a in range(ini.year, fin.year + 1):
        fer |= cortes.feriados_peru(a)
    return frozenset(f for f in fer if ini <= f <= fin)


def _kpis_extra(g):
    """Las tarjetas de KPI que siguen a los canales: propinas, descuentos,
    cortesías y costo sobre neto. Sólo las que el parquet permite."""
    out = []
    tot = float(g["total"].sum())
    if "pax" in g.columns and float(g["pax"].sum()):
        _x = float(g["pax"].sum())
        out.append(("Clientes", f"{_x:,.0f}", f"ticket S/ {tot / _x:,.2f}", "",
                     f"{_x:,.0f} clientes · ticket promedio S/ {tot / _x:,.2f}"))
    if "propina" in g.columns and tot:
        _p = float(g["propina"].sum())
        out.append(("Propinas", fmt_k(_p), f"{_p / tot:.1%}", "",
                    f"Propinas: S/ {_p:,.2f} · {_p / tot:.1%} de la venta"))
    if "desc" in g.columns and "carta" in g.columns and float(g["carta"].sum()):
        _d, _c = float(g["desc"].sum()), float(g["carta"].sum())
        out.append(("Descuentos", fmt_k(_d), f"{_d / _c:.1%}", "",
                    f"Descuentos: S/ {_d:,.2f} · {_d / _c:.1%} de la carta"))
    if "cort_s" in g.columns:
        _k = float(g["cort_s"].sum())
        _n = int(g["n_cort"].sum()) if "n_cort" in g.columns else 0
        out.append(("Cortesías", fmt_k(_k), f"{_n:,} comp.", "",
                    f"Cortesías: S/ {_k:,.2f} a precio carta · {_n:,} "
                    "comprobantes. No suman a la venta"))
    if "pcosto" in g.columns and float(g["neto"].sum()):
        _pc = float(g["costo"].sum()) / float(g["neto"].sum())
        _rev = int((g["pcosto"] > _COSTO_ROTO).sum())
        out.append(("Costo / neto", f"{_pc:.1%}",
                    f"{_rev} a revisar" if _rev else "",
                    "vt-kpi-alerta" if (_rev or _pc > _COSTO_ALTO) else "",
                    f"Costo de receta ÷ venta neta: {_pc:.1%}"
                    + (f" · {_rev} períodos con un costo mayor al precio"
                       if _rev else "")))
    return out


def _zona_detalle(tabla, foco, nombre, gran, partida, ctx, nclic, pie):
    """Los PEDIDOS del período en foco a la izquierda y, al costado, los
    platos del elegido — la pareja documentos | líneas de Compras."""
    amb = tabla[tabla["clave"] == foco]
    if "ped" not in amb.columns:
        # Sin pedido en el parquet, cada comprobante —o cada línea— es su
        # propio pedido: la tabla sigue diciendo algo.
        amb = amb.assign(ped=(amb["doc"] if "doc" in amb.columns
                              else amb.index.astype(str)))
    agg = {"fecha": ("fecha", "min"), "platos": ("venta", "size"),
           "valor": ("venta", "sum")}
    for _c in ("doc", "mesero", "canal"):
        if _c in amb.columns:
            agg[_c] = (_c, "first")
    if "pax" in amb.columns:
        agg["pax"] = ("pax", "max")
    peds = (amb.groupby("ped", as_index=False).agg(**agg)
               .sort_values(["valor", "ped"], ascending=[False, True])
               .reset_index(drop=True))
    if peds.empty:
        st.empty()
        pie.caption(f"**{nombre}** — sin pedidos.")
        return

    # QUÉ PEDIDO muestra la tabla de al lado: el elegido con un clic; si no
    # hay, el MAYOR del período, que es la primera fila. Así la tabla de al
    # lado nunca está vacía (el criterio de Compras).
    sel = st.session_state.get("vt_resumen_ped")
    if sel not in set(peds["ped"]):
        sel = peds["ped"].iloc[0]

    # La hora viaja en ISO, que ordenado como texto ES el orden del tiempo;
    # la grilla la escribe «14:16» en Día (todas las filas son del mismo
    # día) y «03/09 14:16» en los períodos largos.
    tp_peds = pd.DataFrame({
        "hora": peds["fecha"].dt.strftime("%Y-%m-%d %H:%M"),
        "mesero": (peds["mesero"].replace("", "—") if "mesero" in peds
                   else "—"),
        "canal": peds["canal"] if "canal" in peds else "",
        "pax": (peds["pax"].fillna(0).astype(int) if "pax" in peds else 0),
        "platos": peds["platos"].astype(int),
        "valor": peds["valor"].astype(float).round(2),
        "__doc": peds["doc"] if "doc" in peds else "",
        "__ped": peds["ped"],
        "__sel": peds["ped"] == sel,
    })
    n_p = len(peds)
    tot_peds = {
        "hora": "Total", "mesero": f"{n_p:,} pedido" + ("" if n_p == 1 else "s"),
        "canal": "", "pax": f"{int(tp_peds['pax'].sum()):,}",
        "platos": f"{int(peds['platos'].sum()):,}",
        "valor": f"S/ {peds['valor'].sum():,.2f}",
    }

    lin = amb[amb["ped"] == sel].sort_values("venta", ascending=False)
    _cant = (pd.to_numeric(lin["cant"], errors="coerce") if "cant" in lin
             else pd.Series(1.0, index=lin.index))
    tp_lin = pd.DataFrame({
        "prod": lin["prod"] if "prod" in lin else "—",
        "cant": _cant.round(3),
        "punit": (lin["venta"] / _cant.where(_cant != 0)).round(2),
        "valor": lin["venta"].astype(float).round(2),
    })
    n_l = len(tp_lin)
    tot_lin = {"prod": f"Total · {n_l} plato" + ("" if n_l == 1 else "s"),
               "cant": "", "punit": "",
               "valor": f"S/ {lin['venta'].sum():,.2f}"}

    with st.container(key="vt_resumen_detalle"):
        # columnas-internas: las dos tablas del detalle, DENTRO de la
        # tarjeta, con el reparto de «Compras por período» (la de pedidos
        # lleva seis columnas contra cuatro).
        c_peds, c_lin = st.columns([1.15, 1], gap=GAP_DRILL)
        # La key lleva lo que cambia las FILAS y el contador de clics del
        # gráfico, no el pedido elegido: el orden que eligió el usuario
        # sobrevive al clic (regla #471).
        k_tablas = _clave_grilla(ctx, foco, nclic)
        with c_peds:
            clic = renderizar_pedidos_venta(
                tp_peds, altura=_ALTO_TABLA,
                key=f"vt_resumen_ped_grid_{k_tablas}",
                ver_canal=partida, ver_mesero="mesero" in peds,
                solo_hora=gran == "Día", total=tot_peds)
        with c_lin:
            renderizar_lineas_mov(tp_lin, altura=_ALTO_TABLA,
                                  key=f"vt_resumen_lin_grid_{k_tablas}",
                                  total=tot_lin)
    pie.caption(f"**{nombre}** — clic en un pedido para ver sus platos al "
                "costado.")

    # La selección VIGENTE de la grilla: se actúa sólo si difiere del pedido
    # que ya se muestra, y el rerun redibuja la marca y los platos.
    if clic is None or clic == sel or clic not in set(peds["ped"]):
        return
    st.session_state["vt_resumen_ped"] = clic
    st.rerun(scope=scope_rerun())
