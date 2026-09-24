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

from tema import (ACENTO, ADVERTENCIA, ERROR, EXITO, GRIS_BORDE, GRIS_TEXTO,
                  PALETA_SERIES, SERIE_PRINCIPAL, TEXTO_PRINCIPAL)
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


def _html_kpi_canales(total, n_dias, canales):
    """La fila de KPI de la tarjeta: el total de la vista y lo de cada canal.

    Mismo dibujo que la de «Compras por período»
    (`semanal._html_kpi_vista`), con canales en vez de familias. `canales`
    es `[(nombre, valor), …]` de mayor a menor. Con un solo canal no se
    desglosa nada: el total ya es ese canal."""
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
    return '<div class="vt-kpis">' + "".join(partes) + "</div>"


def _colores_de(n):
    """Un color por canal, en el orden de la pila (el que más vende primero)."""
    return [_COLORES_CANAL[_i % len(_COLORES_CANAL)] for _i in range(n)]


@st.fragment
def _ventas_resumen(d, col_venta, col_fecha, col_pax, col_pedido, col_prod,
                    col_cant, col_fam=None, col_serv=None, col_canal=None,
                    col_mesero=None):
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

    # UN ÍTEM SE CUENTA UNA VEZ (2026-09-24, regla #516). `ventas.parquet`
    # trae una fila por ítem Y POR FORMA DE PAGO del comprobante: pagado con
    # cheque + tarjeta, cada plato sale dos veces con su venta entera.
    # Medido en septiembre 2026: 8.198 filas para 6.991 ítems, S/ 390.272
    # sumando filas contra S/ 332.807 reales (+17 %). La llave del ítem es
    # única por plato del comprobante, así que se queda la primera fila de
    # cada una. Las demás vistas de Ventas siguen sumando filas.
    col_item = _resolver(d, ["Llave Local Documento Item"])
    if col_item:
        d = d.drop_duplicates(subset=[col_item])

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

    if grupo_sel:
        d = d[d[col_fam].astype(str).str.strip().isin(grupo_sel)]
    if serv_sel:
        d = d[d[col_serv].astype(str).str.strip().isin(serv_sel)]
    if canal_sel:
        d = d[_canal_legible(d[col_canal]).isin(canal_sel)]
    if tdoc_sel:
        d = d[d[col_tdoc].astype(str).str.strip().isin(tdoc_sel)]
    if d is None or d.empty:
        st.info("No hay ventas para los filtros elegidos.")
        return

    fecha = pd.to_datetime(d[col_fecha], errors="coerce")
    cols = {"dia": fecha.dt.normalize(), "fecha": fecha,
            "venta": pd.to_numeric(d[col_venta], errors="coerce")}
    if col_prod:
        cols["prod"] = d[col_prod].astype(str)
    if col_cant:
        cols["cant"] = pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
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
    tabla = pd.DataFrame(cols).dropna(subset=["dia", "venta"])
    if tabla.empty:
        st.info("Sin datos en el rango cargado.")
        return

    # En Día, los últimos `MAX_DIAS` días con ventas: más barras que eso no
    # se leen. En las otras granularidades manda el rango de la fecha.
    _nota_recorte = ""
    if gran == "Día":
        dias_disp = sorted(tabla["dia"].unique())
        if len(dias_disp) > MAX_DIAS:
            tabla = tabla[tabla["dia"].isin(dias_disp[-MAX_DIAS:])]
            _nota_recorte = (f" Recortado a los últimos {MAX_DIAS} días con "
                             "ventas: para ver más, agrupá por semana o mes.")
    tabla = tabla.sort_values("fecha")
    tabla["clave"] = _periodo_serie(tabla["fecha"], gran)

    # ── Total por período ─────────────────────────────────────────────────
    g = (tabla.groupby("clave", as_index=False)["venta"].sum()
         .rename(columns={"venta": "total"})
         .sort_values("clave").reset_index(drop=True))

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
                if _partida else []), unsafe_allow_html=True)

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
        _tramos = [pd.DataFrame({"valor": por_canal[c].to_numpy()})
                   for c in canales]
        _textos_tr = (_etiqueta_en_la_punta(_tramos, _textos) if _plan_etq
                      else [None] * len(canales))
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
        _rng_y = (_techo_etiquetas(float(g["total"].max()), 0.0, _alto_fig,
                                   _alto_etq) if _plan_etq else None)
        fig.update_layout(
            showlegend=bool(vol_label) or _partida,
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
                          gran, _ctx, _pie, _rng, _nota_recorte)
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
                  canales, gran, ctx, pie, rango, nota_recorte):
    """El gráfico escrito como tabla: una fila por barra, más el total. Un
    clic en una fila abre su Detalle, como un clic en su barra."""
    tot = g["total"].astype(float)
    tot_vista = float(tot.sum())
    datos = {
        "periodo": fila,
        "valor": tot.round(2).tolist(),
        "parte": [(t / tot_vista if tot_vista else 0.0) for t in tot],
    }
    cols_canal = []
    for _i, c in enumerate(canales):
        datos[f"canal_{_i}"] = por_canal[c].astype(float).round(2).tolist()
        cols_canal.append((f"canal_{_i}", c))
    if vol_label:
        datos["pax"] = g["pax"].astype(float).tolist()
        datos["ticket"] = [None if pd.isna(t) else round(float(t), 2)
                           for t in g["ticket"]]
    datos["variacion"] = [(_v[1] if _v[0] == "ok" else None)
                          for _v in variaciones]
    datos["__vtxt"] = [("parcial" if _v[0] == "parcial" else "—")
                       for _v in variaciones]
    datos["__nota"] = [_nota_var_venta(_v, fila[_v[2]] if _v[2] is not None
                                       else "") for _v in variaciones]
    datos["__clave"] = claves
    datos["__sel"] = [c == foco for c in claves]
    tp = pd.DataFrame(datos)

    n = len(claves)
    uni = _UNIDAD_GRAN[gran][0 if n == 1 else 1]
    total = {"periodo": f"Total · {n:,} {uni}", "valor": f"S/ {tot_vista:,.2f}",
             "parte": "100%", "variacion": ""}
    for _col, c in cols_canal:
        total[_col] = fmt_k(float(por_canal[c].sum()))
    if vol_label:
        _tp = float(g["pax"].sum())
        total["pax"] = f"{_tp:,.0f}"
        total["ticket"] = f"S/ {tot_vista / _tp:,.2f}" if _tp else "—"

    # La key lleva lo que cambia las FILAS y un contador que se estrena cada
    # vez que un clic en una fila lleva al Detalle: así la grilla vuelve sin
    # la selección vieja (regla #471). NO lleva el foco.
    n_res = st.session_state.get("vt_resumen_nres", 0)
    with st.container(key="vt_resumen_resumen"):
        clic_fila = renderizar_dias_venta(
            tp, altura=_ALTO_TABLA,
            key="vt_resumen_res_grid_" + _clave_grilla(ctx, n_res),
            rotulo_periodo=gran, canales=cols_canal, vol_label=vol_label,
            total=total)
    pie.caption(
        f"**{_del_al(pd.Series(pd.to_datetime(list(rango))))}** · agrupado "
        f"por {gran.lower()} — una fila por barra; un clic en una fila (o "
        "en su barra) abre sus pedidos." + nota_recorte)
    if clic_fila in set(claves):
        st.session_state["_vt_resumen_ir_detalle"] = clic_fila
        st.session_state["vt_resumen_nres"] = n_res + 1
        st.rerun(scope=scope_rerun())


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
