"""graficos.compras._comun - helpers compartidos por los drills de Compras.

Cosas chicas que usan dos o mas drills: deteccion de movil, lectura de
la seleccion de un plotly_chart, mini barras horizontales y etiquetas de
periodo segun granularidad.

Y la GRILLA (`COLUMNAS_DRILL` / `GAP_DRILL`): la proporcion con la que parte
en dos una fila de un drill. Vive aca y no en cada modulo porque el eje
vertical tiene que caer en el mismo sitio en TODAS las filas de una vista.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO, TEXTO_PRINCIPAL
from graficos.base import _compras_truncar, _slug
# REEXPORT, no import muerto: `_es_movil` vivía definida acá y se movió a
# graficos/base.py (2026-08-07, ver su docstring) porque graficos/ajuste.py
# la necesitó también. Este import la reexpone bajo el mismo nombre, así que
# proveedor.py y compras/__init__.py siguen haciendo
# `from graficos.compras._comun import _es_movil` sin enterarse. Este módulo
# NO la usa, de ahí el noqa: sin él, `ruff --fix` la borraría y rompería a
# sus dos consumidores.
from graficos.base import _es_movil  # noqa: F401
from graficos import alturas


# ===========================================================================
# LA GRILLA: UNA SOLA PROPORCIÓN POR VISTA
# ===========================================================================
# Hermana de `tema.py` (dueño del color) y `alturas.py` (dueño del alto): el
# EJE VERTICAL de una vista tampoco puede escribirse a mano en cada fila.
#
# POR QUÉ EXISTE (2026-08-21). El drill de Proveedor tenía dos filas de dos
# columnas y cada una partía en un sitio distinto: la de arriba con
# `st.columns([1.6, 1])` (61.5%) y la de abajo con `st.columns(2)` (50%). Con
# ~1750px de ancho útil eso son ~200px de salto — el canal gris que baja entre
# las columnas se cortaba a media página y la vista dejaba de leerse como una
# grilla. No lo cazaba nada: los dos números son correctos por separado.
#
# La regla: la proporción que parte una FILA de un drill sale de acá. Las
# subdivisiones DENTRO de una tarjeta (el chart y su pila de KPIs, una
# botonera) son otra cosa y siguen siendo literales — se marcan con un
# comentario `# columnas-internas: <por qué>` y `test_graficos.py` las
# distingue por esa marca.
COLUMNAS_DRILL = [1.6, 1]
"""Proporción izq./der. de una fila de dos columnas en un drill de Compras.

1.6/1 y no 1/1: la columna izquierda lleva siempre la tabla con nombres
largos (proveedores, productos) y la derecha un panel de apoyo. El Panel B
aguanta el apretón: desde el 2026-09-11 su lista es una FILA por proveedor
—nombre, precio unitario y última compra, y el resto en un `<details>`— en
vez de una tarjeta con una grilla de 4 métricas que había que colapsar a
2x2. Ver regla #377.

Ojo con lo que ese 1 significa en píxeles: medido con datos reales, el Panel
B mide 289px en una pantalla de 1280 y 535px en una de 1920. Cualquier cosa
que reaccione al ancho de ESE panel se consulta por `@container`, no por
`@media` — el viewport no distingue esos dos casos. Ver regla #317."""

COLUMNAS_DRILL_ESPEJO = COLUMNAS_DRILL[::-1]
"""`COLUMNAS_DRILL` al revés: el panel de apoyo a la IZQUIERDA y la tabla
a la derecha.

Nació el 2026-09-12 con el drill de Producto, a pedido («el gráfico del
producto, pongámoslo al lado izquierdo y las tablas al lado derecho»). Es
la MISMA proporción espejada y no otra a propósito: la tabla se sigue
llevando el 1.6 por la razón de arriba (nombres largos, ocho columnas en el
ranking de productos), y la figura el 1, el ancho que ya tenía. Poner la
figura en el 1.6 habría dejado a Familia | Subfamilia en ~200px cada una.

Lo que se paga: el canal gris cae en el espejo del de Proveedor (38% en vez
de 62%), así que las dos filas apiladas de Compras dejan de compartir eje y
se leen en zigzag. Es la forma del pedido, no un descuido — y como es una
constante derivada, si `COLUMNAS_DRILL` cambia, ésta cambia con ella. Ver
regla #382."""

COLUMNAS_COTEJO = [1, 1]
"""Proporción de una fila que COMPARA dos fuentes, no que parte una tabla
de su panel de apoyo.

`COLUMNAS_DRILL` es 1.6/1 porque su izquierda lleva siempre una tabla con
nombres largos y su derecha un panel que la acompaña — hay una jerarquía.
En una comparación no la hay: los dos lados son pares y cualquier
asimetría se lee como que uno importa más. Se estrenó el 2026-08-28 en
«Documentos SUNAT», cuando la ficha del comprobante pasó de ser una
tarjeta con cuatro columnas (campo | SUNAT | sistema | Δ) a DOS tarjetas
hermanas, a pedido.

Existe como constante y no como `st.columns(2)` suelto por lo mismo que
`COLUMNAS_DRILL`: el conversor de ese mismo drill parte sus dos mitades
por la mitad, y si una fila comparara 1.6/1 y la otra 1/1, el eje
vertical de la página se correría a media pantalla — que es exactamente
el bug que hizo nacer la regla #145."""

GAP_DRILL = "small"
"""Gap entre las columnas de un drill. Va con `COLUMNAS_DRILL`: si las dos
filas parten en el mismo sitio pero con gaps distintos, el canal gris cambia
de ancho a media página y el salto se ve igual."""

# ── El LOOK de una tabla-ranking de Compras ──────────────────────────
# Cuarta cara del mismo patrón que ya tienen el color (`tema.py`), el alto
# de figura (`alturas.py`) y la grilla (`COLUMNAS_DRILL`): un número que
# vivía en UNA tabla y describe a TODAS.
ALTO_FILA_RANK = 24
"""Alto de fila, en px, de las tablas-ranking de los drills de Compras.

Nació inline en `proveedor.py` el 2026-08-28 ("las filas un poco más
delgadas", junto con el blanco, el cuerpo de 11.5px y las minúsculas de
`CSS_RANKING_GRID`), y el comentario que lo acompañaba anticipaba este
día: «si algún día se unifican, es 24 + `CSS_RANKING_GRID` lo que tiene
que viajar para allá». El 2026-09-11 viajó — los tres paneles del drill
Familia › Subfamilia › Producto se pidieron "similares al de Ranking de
Proveedores" —, así que el número deja de ser de una tabla y pasa a ser
el de todas.

Va SIEMPRE con `_css_proveedor.CSS_RANKING_GRID`: el alto solo, sin el
cuerpo de 11.5px, aprieta el texto de 12px contra las líneas."""

ALTO_HEADER_RANK = 32
"""Alto de la cabecera de esas mismas tablas. Acompaña a `ALTO_FILA_RANK`
y no se elige aparte: 38px sobre filas de 24 queda cabezona (era el doble
de una fila)."""

CROMO_GRID_RANK = ALTO_HEADER_RANK + 7
"""Todo lo que mide un grid de ranking y NO son sus filas de datos: la
cabecera + su borde inferior de 1px + ~5.5px de cromo del tema. Medido en
el DOM, no a ojo. Es el `extra=` con el que `alturas.por_filas` dimensiona
el `height=` del AgGrid; una tabla que además lleve fila TOTAL o una
franja de atajos encima le suma lo suyo (ver `proveedor.py`)."""

PARR = "\n\n"
"""Salto de párrafo para el markdown de un popover de ayuda.

Vivía en `vs_ano_pasado.py` hasta el 2026-09-07, cuando «Volatilidad»
estrenó el suyo (el mismo popover de sólo ícono). Dos cadenas iguales
escritas en dos módulos no driftean solas, pero el CRITERIO sí: si
mañana el popover pasa a separar con `---`, cambia en un sitio."""


def _first_point(evt):
    """Primer punto de una selección de st.plotly_chart(on_select=...).
    Devuelve el dict del punto o None (tolerante a formatos/errores)."""
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        pts = (sel or {}).get("points", [])
        return pts[0] if pts else None
    except Exception:
        return None


def _compras_mini_barras(serie, titulo, fmt="S/ {:,.0f}", alto=alturas.APOYO):
    """Mini gráfico de barras horizontales top-N (mayor arriba)."""
    if serie is None or serie.empty:
        st.info("Sin datos para este top.")
        return
    d = serie.sort_values(ascending=True)
    fig = go.Figure(go.Bar(
        x=d.values,
        y=[_compras_truncar(i) for i in d.index],
        orientation="h",
        marker=dict(color=ACENTO, opacity=0.85),
        text=[fmt.format(v) for v in d.values],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=alto,
        margin=dict(l=4, r=40, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=11),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True,
                    key=f"compras_mini_{_slug(titulo)}")


def _periodo_serie(fe, gran):
    """Serie de etiquetas de periodo (ordenables) según granularidad."""
    if gran == "Día":
        return fe.dt.strftime("%Y-%m-%d")
    if gran == "Semana":
        iso = fe.dt.isocalendar()
        return (iso["year"].astype("Int64").astype(str) + "-S"
                + iso["week"].astype("Int64").astype(str).str.zfill(2))
    if gran == "Año":
        return fe.dt.year.astype("Int64").astype(str)
    return fe.dt.to_period("M").astype(str)  # Mes


# ===========================================================================
# EL NÚMERO DE DOCUMENTO: EN EL PARQUET ESTÁ CODIFICADO
# ===========================================================================
# `NUM_DOCUMENTO` NO es lo que dice el papel. Son 15 caracteres siempre
# (verificado sobre las 51.574 filas del parquet: una sola longitud), con la
# forma `"F0" + serie(4) + numero(9 con ceros a la izquierda)`:
#
#     F0E001000001328  ->  E001-1328
#     F0F001000016855  ->  F001-16855
#
# `_llave_documento_parquet` nació en `documentos_sunat.py` como CLAVE DE
# CRUCE contra el registro del SIRE (que trae `documento` ya sin los ceros).
# Subió acá el 2026-09-08, cuando el drill Semanal la pidió para MOSTRAR el
# número en su tabla de detalle. Son los dos lados de la misma decodificación
# y no puede haber dos: si se separaran, la tabla y el cruce dirían números
# distintos del mismo comprobante. `documentos_sunat.py` la reexporta con su
# nombre de siempre.


# VIVE ACÁ Y NO EN `__init__.py` por el ciclo de imports: la usan los cinco
# drills, y `__init__.py` los importa a ellos. Este módulo es el que ya
# importan todos, así que es el único sitio donde puede estar sin que nadie
# importe hacia arriba. `__init__.py` la reexporta.
# ── QUÉ SECCIÓN TIENE RANGO PROPIO ────────────────────────────────────────
# 2026-09-08, a pedido. Hasta este día los cinco selectores de fecha de las
# cabeceras escribían UNA sola clave (`rango_franja_Compras`), así que mover
# la fecha en una tarjeta la movía en las otras cuatro. Estaba puesto a
# propósito y era razonable mientras el control fuera un ATAJO a la píldora
# de la franja; el 2026-09-06 la franja perdió el calendario y el atajo pasó
# a ser EL control, con la semántica vieja. Se reportó como se ve: "pensé
# que cada tarjeta, su selector, solo afectaba a su tarjeta".
#
# La categoría entra en `clave_rango(reporte, ..., categoria=)` y sale una
# clave por sección. Cuatro entradas para seis secciones, y las dos que
# faltan no son un olvido:
#
#   · «Vs año pasado» y «Tabla» NO tienen este selector. Tienen el OTRO —
#     el desplegable Rango/3m/12m/24m/Todo de `graficos/periodo.py`, que ya
#     era por tarjeta. Meterlas acá les daría dos controles de fecha que se
#     pisan, que es justo el enredo que este cambio viene a deshacer.
#   · «Documentos SUNAT» está fuera de la pila y dibuja el pill entero de
#     la franja, cuya key ES la clave canónica. Ése no se puede mover sin
#     mover el widget, y no es lo que se pidió.
#
# PROVEEDOR ES UNA SOLA CATEGORÍA PARA DOS SECCIONES, y eso es deliberado:
# «Ranking de proveedores» y «Detalle de documentos por proveedor» se
# calculan sobre el MISMO `base`/`top_provs` (ver
# `_documentos_proveedor.render_seccion`). Con rangos distintos la tabla
# mostraría documentos de proveedores rankeados en otro período — un
# desacuerdo silencioso entre dos cosas que dicen ser lo mismo. Ver regla
# #363.
#
# Hasta el 2026-09-09 eran una sola SECCIÓN con dos tarjetas, así que el
# rango compartido salía gratis. Al separarlas —«Detalle de documentos» pasó
# a ser la última sección del reporte, a pedido— el mapa las vuelve a atar a
# mano: dos claves, un solo valor. `_d_sec` memoiza por CATEGORÍA, así que
# además comparten el recorte y no lo calculan dos veces.
CATEGORIA_SEC = {
    "compras_sec_proveedor":   "sec_proveedor",
    "compras_sec_documentos":  "sec_proveedor",
    "compras_sec_producto":    "sec_producto",
    "compras_sec_volatilidad": "sec_volatilidad",
    "compras_sec_semanal":     "sec_semanal",
}


# ── CON QUÉ RANGO ABRE CADA SECCIÓN ───────────────────────────────────────
# 2026-09-11, a pedido, señalando el trigger del Ranking de Proveedores:
# «este selector de fecha debe mostrar lo del mes presente por defecto».
#
# EL DEFAULT DEL REPORTE NO SE TOCA: siguen siendo los últimos 12 meses
# desde el 2026-09-06 (ver el comentario largo de `app.py`). Ése es lo que
# ve una sección SIN selector propio, y ahí un mes es una mentira por
# omisión. Lo que cambia acá es con qué abre una sección que SÍ tiene su
# selector en la cabecera: el ranking contesta "quién pesa más ACÁ", y ese
# "acá" por defecto es el mes en curso. Los 12 meses siguen a un clic desde
# su propio trigger.
#
# LA CATEGORÍA Y NO LA SECCIÓN, igual que en `CATEGORIA_SEC` y por el mismo
# motivo: «Detalle de documentos por proveedor» comparte la categoría de
# Proveedor, así que abre con el mismo mes — que es justo lo que se quiere,
# porque lista los documentos de los proveedores que rankeó el gráfico.
#
# EL MES LO CALCULA `app.py` Y LO PUBLICA EN EL CONTEXTO
# (`rango_default_cat`), no esta tupla: acá sólo se declara CUÁL de los dos
# defaults quiere cada categoría. Una segunda cuenta del mismo mes es
# exactamente lo que evita `rango_default` desde el 2026-09-08.
#
# 2026-09-12, a pedido, se suman dos: «el selector de fecha de la tabla de
# compras por familia debe mostrar el mes actual seleccionado» (Producto) y
# la vista Semanal, «seleccionado el mes actual en su selector de fecha
# inicialmente» — que además abre en «Por documento» (`_GRAN_DEFAULT` en
# semanal.py). Quedan en los 12 meses del reporte Volatilidad, que tiene su
# propia ventana, y las secciones sin selector.
#
# Lo que NO cambia con esto: el gráfico de evolución de Producto mira su
# VENTANA propia (abre en 3 meses, `producto.py`), no esta fecha — salvo
# que se elija «Rango de las tablas». Un mes de ranking al lado de 3 meses
# de evolución es a propósito: el ranking contesta "qué compré ahora", la
# evolución "cómo viene el precio".
SEC_ABRE_EN_EL_MES = ("sec_proveedor", "sec_producto", "sec_semanal")


# ===========================================================================
# LA BASE DEL DRILL DE PROVEEDOR
# ===========================================================================
# Salieron de `proveedor.py` el 2026-09-09, cuando «Detalle de documentos por
# proveedor» dejo de ser la ultima fila de ese drill y paso a ser su PROPIA
# seccion, al final del reporte. Las dos secciones necesitan exactamente el
# mismo df normalizado y la misma lista de periodos: si cada una lo armara
# por su lado, la tabla y el ranking podrian discrepar sin que nada avise
# — que es el mismo argumento por el que comparten rango (ver
# `CATEGORIA_SEC`, mas arriba).
#
# Son funciones PURAS: no dibujan, no leen `session_state`. La granularidad
# entra por parametro justamente por eso — en `proveedor.py` `gran` era una
# variable de la funcion y `_agregar_periodo` una closure sobre ella.

def base_normalizada(d, col_prov, col_prod, col_cant, col_valor, col_punit,
                     col_um, col_fecha, col_docu):
    """El df del drill de Proveedor: nombres de columna FIJOS.

    Traduce las columnas del parquet (cuyos nombres cambian) a las ocho que
    el drill usa en todos lados: prov/prod/cant/valor/punit/um/fecha/docu.
    Las columnas que no existen entran con su vacio (`0.0`, `NaN`, `""`,
    `NaT`) en vez de faltar: asi el resto del drill no tiene que preguntar
    por cada una antes de tocarla.

    Filtra las filas SIN proveedor, incluida la cadena `"nan"` — que no es
    paranoia: `astype(str)` sobre un `NaN` da exactamente eso, y sin el
    filtro aparece como un proveedor mas, con su color y su fila en el
    ranking.
    """
    b = pd.DataFrame({
        "prov":  d[col_prov].astype(str).values,
        "prod":  (d[col_prod].astype(str).values if col_prod else "—"),
        "cant":  (pd.to_numeric(d[col_cant],  errors="coerce").fillna(0).values
                  if col_cant else 0.0),
        "valor": pd.to_numeric(d[col_valor], errors="coerce").fillna(0).values,
        "punit": (pd.to_numeric(d[col_punit], errors="coerce").values
                  if col_punit else np.nan),
        "um":    (d[col_um].astype(str).values if col_um else ""),
        "fecha": (pd.to_datetime(d[col_fecha], errors="coerce").values
                  if col_fecha else pd.NaT),
        "docu":  (d[col_docu].astype(str).values if col_docu else ""),
    })
    return b[b["prov"].notna() & (b["prov"] != "nan")]


def agregar_periodo(df, gran):
    """`df` con dos columnas mas: `per` (el rotulo) y `_per_sort` (su orden).

    Estan separadas porque el rotulo NO ordena: en granularidad Semana
    `per` es «01Sep-07Sep», que alfabeticamente pone agosto despues de
    abril. `_per_sort` lleva la fecha ISO del lunes y es la que manda.

    Los meses van en espanol a mano (`_mes_es`) y no por locale: el locale
    del server no es el del usuario, y en Cloud es el del contenedor.
    Misma decision que `cortes.MESES_ABR_ES` (regla #241), con la que
    conviene no desincronizarse.

    Se aplica TAMBIEN al historico completo, que es lo que alimenta el
    grafico de evolucion: con el rango de la franja puede haber un solo
    periodo, y una linea de un punto no dibuja ninguna evolucion
    (reportado con captura: en granularidad Ano se veia un punto suelto en
    medio de la nada). De ahi que sea una funcion y no dos lineas inline.
    """
    _fe = pd.to_datetime(df["fecha"], errors="coerce")
    _mes_es = {'Jan': 'Ene', 'Apr': 'Abr', 'Aug': 'Ago', 'Dec': 'Dic'}
    if gran == "Día":
        df["_per_sort"] = _fe.dt.strftime("%Y-%m-%d")
        _p = _fe.dt.strftime("%d %b")
        for _en, _es in _mes_es.items():
            _p = _p.str.replace(_en, _es)
        df["per"] = _p
    elif gran == "Semana":
        _ws = (_fe - pd.to_timedelta(_fe.dt.weekday, unit="D")).dt.normalize()
        _we = _ws + pd.Timedelta(days=6)
        df["_per_sort"] = _ws.dt.strftime("%Y-%m-%d")   # clave de orden
        _p = _ws.dt.strftime("%d%b") + "-" + _we.dt.strftime("%d%b")
        for _en, _es in _mes_es.items():
            _p = _p.str.replace(_en, _es)
        df["per"] = _p
    elif gran == "Año":
        df["_per_sort"] = _fe.dt.year.astype("Int64").astype(str)
        df["per"] = df["_per_sort"]
    else:  # Mes
        df["_per_sort"] = _fe.dt.to_period("M").astype(str)
        df["per"] = df["_per_sort"]
    return df[df["per"].notna() & (df["per"] != "<NA>")]


def periodos_ordenados(base):
    """Los periodos de `base`, deduplicados y en orden CRONOLOGICO.

    Fija el orden de las columnas del pivote de documentos y del eje X de
    la evolucion. Sin `_per_sort` (que solo falta si `base` viene de otro
    sitio) cae al alfabetico, que para «Mes» y «Año» coincide.
    """
    if "_per_sort" in base.columns:
        _orden = (base[["_per_sort", "per"]].drop_duplicates()
                  .sort_values("_per_sort")["per"].tolist())
        return list(dict.fromkeys(_orden))
    return sorted(base["per"].dropna().unique())


def _llave_documento_parquet(num_documento):
    """`"{serie}-{numero}"` desde `NUM_DOCUMENTO` del parquet de Compras.

    Se le sacan los ceros de más para que calce con `documento` del SIRE
    (`sunat._normalizar_registro`, que ya viene sin ellos)."""
    s = num_documento.astype(str)
    serie = s.str[2:6]
    numero = s.str[6:].str.lstrip("0")
    numero = numero.where(numero != "", "0")   # el raro caso numero="000..."
    return serie + "-" + numero


def documento_legible(num_documento):
    """Lo mismo, pero para MOSTRAR: decodifica sólo lo que tiene la forma
    del parquet y deja pasar el resto tal cual.

    La guarda no es defensiva por las dudas, cubre un caso que corre todos
    los días: el modo demo de `data.py` genera `"F0001-123"` —ya legible, 9
    caracteres— y `_llave_documento_parquet` a ciegas lo cortaría en
    `"01-1 23"`. Cualquier valor que no sea `"F0"` + 13 caracteres se
    devuelve entero, que es la única respuesta honesta cuando el formato no
    es el que se sabe decodificar."""
    s = num_documento.astype(str).str.strip()
    _codificado = (s.str.len() == 15) & s.str.startswith("F0")
    return s.where(~_codificado, _llave_documento_parquet(s))


# ===========================================================================
# EL SELECTOR DE FECHA DE UNA TARJETA — vive en graficos/base.py
# ===========================================================================
# Nació dentro del Ranking de Proveedores (2026-08-23 → 08-26, cuatro vueltas
# de pedido), se mudó ACÁ el 2026-08-26 cuando lo pidió el Ranking de
# Productos, y SUBIÓ a `graficos/base.py` el 2026-09-05, cuando lo pidió la
# Evolución de Movimientos ("un selector de fecha, igual que el ranking de
# proveedores"). Tercera vez que un tercero lo pide: el criterio no cambió,
# cambió el alcance — ya no es un helper de Compras, es del proyecto, y vive
# al lado de `selector_escala`, que es la pieza que abre adentro.
#
# REEXPORT, no import muerto: `proveedor.py`, `producto.py` y `semanal.py`
# siguen haciendo `from graficos.compras._comun import selector_fecha_tarjeta`
# sin enterarse de la mudanza. Mismo patrón —y mismo `noqa`— que `_es_movil`
# acá arriba: sin él, `ruff --fix` lo borra y rompe a sus tres importadores.
from graficos.base import selector_fecha_tarjeta  # noqa: F401


def filtro_proveedores(clave, provs_ordenados, pie=None):
    """Filtro de proveedores para una tarjeta de Compras.

    Devuelve `(seleccion, dibujar)`:

    · `seleccion` es la lista de proveedores marcados (o TODOS los reales si
      el usuario destildó hasta el último — el default y el fallback tienen
      que decir lo mismo, o "limpiar" cambiaría el default).
    · `dibujar` es un CALLABLE para el hook `extra=` de
      `selector_fecha_tarjeta`, que lo mete en la fila del título.

    Los dos por separado a propósito: la selección se LEE temprano, para
    armar la figura y el ranking, y el popover se DIBUJA tarde, dentro de la
    tarjeta. Es el patrón de UN rerun que ya usaba cuando flotaba, y no
    cambia por mudarse de sitio.

    Nació el 2026-09-02 extrayendo el popover que vivía inline en
    `proveedor.py`, al pedirse el mismo control para el Ranking de Productos
    ("añadamos el de proveedor"). Copiarlo hubiera sido duplicar ~100 líneas
    y, peor, dos sitios donde arreglar el próximo detalle — el mismo
    argumento que ya había traído acá a `selector_fecha_tarjeta`.

    `clave` es el prefijo de TODAS las keys, así que las dos vistas
    coexisten en la página apilada sin chocar. El CSS de cada prefijo se
    lista EXPLÍCITO en `_css_proveedor.py`: nada de wildcards por familia
    (ver el aviso de CLAUDE.md).

    `pie` es un callable opcional que se dibuja al final del panel; hoy lo
    usa Proveedor para su toggle "Nombres en barras", que es de esa vista y
    no del filtro.
    """
    reales = [p for p in provs_ordenados if p != "Otros"]
    # Por defecto se muestran TODOS los del rango, no los N más grandes: la
    # lista sale de un `d` ya filtrado por fecha, así que "todos" significa
    # "todos los que compraron en el período" y cambia sólo con la fecha.
    # "Otros" arranca DESTILDADO: no es un proveedor, agrupa a los que
    # quedaron fuera del top, y encenderlo por defecto metería una fila
    # que no se puede enfocar.
    for _p in provs_ordenados:
        _k = f"{clave}_cb::{_p}"
        if _k not in st.session_state:
            st.session_state[_k] = (_p in reales)

    def _set_topn(_n):
        """Marca sólo los primeros _n proveedores (por valor). _n=0 → limpiar."""
        for _pp in provs_ordenados:
            st.session_state[f"{clave}_cb::{_pp}"] = (_pp in reales[:_n])

    seleccion = [p for p in provs_ordenados
                 if st.session_state.get(f"{clave}_cb::{p}")] or reales

    def dibujar():
        with st.container(key=f"{clave}_pop_float"):
            _sel_now = [p for p in provs_ordenados
                        if st.session_state.get(f"{clave}_cb::{p}")]
            # El número va como badge por CSS var (un `::after` lo pinta).
            # Sin cuenta → badge vacío. La var vive scopeada al contenedor.
            st.markdown(
                f"<style>.st-key-{clave}_pop_float "
                f"{{ --cp-prov-count: '{len(_sel_now)}'; }}</style>",
                unsafe_allow_html=True,
            )
            with st.popover("Proveedores", icon=":material/groups:"):
                # Panel COMPACTO. El detalle de por qué cada pieza es como
                # es —los 175px de aire que se midieron antes de tocarlo, el
                # `st.columns(5)` que imponía 382px de ancho, el
                # `st.divider()` de 49— está en arquitectura.md regla #272.
                # columnas-internas: botonera del popover, no el eje de la vista.
                with st.container(horizontal=True, gap="small",
                                  key=f"{clave}_atajos"):
                    st.button("Top 3", key=f"{clave}_topn3", type="tertiary",
                              on_click=_set_topn, args=(3,))
                    st.button("5", key=f"{clave}_topn5", type="tertiary",
                              on_click=_set_topn, args=(5,))
                    st.button("10", key=f"{clave}_topn10", type="tertiary",
                              on_click=_set_topn, args=(10,))
                    st.button("Todos", key=f"{clave}_topnall", type="tertiary",
                              on_click=_set_topn, args=(len(reales),))
                    st.button("Ninguno", key=f"{clave}_topnclr", type="tertiary",
                              on_click=_set_topn, args=(0,))
                _q = st.text_input("Buscar", key=f"{clave}_q",
                                   placeholder="Buscar proveedor...",
                                   label_visibility="collapsed").strip().lower()
                _vistos = [p for p in provs_ordenados
                           if not _q or _q in str(p).lower()]
                if not _vistos:
                    st.caption("Sin coincidencias.")
                # La lista scrollea DENTRO en vez de estirar el panel, y su
                # alto es dinámico: `st.container(height=N)` reserva N aunque
                # haya dos filas. NO son N filas iguales — los proveedores
                # son razones sociales completas y ENVUELVEN. Medido clonando
                # filas reales en los 200px de texto útil del panel: 1 línea =
                # 24px, 2 = 30, 3 = 45 (~15 por línea + 9 de caja). 190 es el
                # techo: por encima el panel vuelve a comerse media pantalla.
                _CHARS_LINEA = 30      # a 12px en 200px de ancho útil, medido
                _alto_lista = min(190, sum(
                    (-(-len(str(_p)) // _CHARS_LINEA) or 1) * 15 + 13
                    for _p in _vistos) or 28)
                with st.container(height=_alto_lista, border=False,  # alto-fijo-justificado: líneas x px de la lista, no una resta contra la pantalla
                                  key=f"{clave}_lista"):
                    for _p in _vistos:
                        # `width="stretch"`: el default de `st.checkbox` es
                        # `content`, o sea la fila —y con ella el área
                        # clicable— medía lo que el nombre. En una lista, la
                        # fila entera tiene que ser el blanco.
                        st.checkbox(_p, key=f"{clave}_cb::{_p}",
                                    width="stretch")
                if pie is not None:
                    pie()

    return seleccion, dibujar
