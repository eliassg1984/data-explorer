"""
formulario_receta.py — "Nueva receta": arma y costea una receta de venta o
un combo, y los deja guardados como propuesta en R2 para que otra persona
los revise.

Punto de entrada público: render_formulario_receta().

Desde el 2026-09-22 es una VISTA del reporte «Recetas y Costos» (rail
interno, primera sección), no un reporte hermano tool:True. Hasta ese día
era un reporte propio del `grupo_nav: "Recetas"` que el chip `_chip_fuente`
alternaba con el analítico. Se bajó a vista a pedido («deseo que figure
como una vista de mi reporte de recetas») y el chip desapareció con la
mudanza. El punto de entrada sigue siendo el mismo — lo consume ahora
`graficos/recetas.py::_dib_nueva`, no `app.py::_TOOLS`.

Desde el 2026-09-24 son DOS tarjetas a la altura de la pantalla: «Receta»
(buscadores, insumos, guardar y enviar) y «Precio de venta» (tabla con un
punto de color por fila, semáforo del % de costo y la torta). Regla #512.

Cuatro modos, un segmented_control propio en la cabecera de «Receta»:
  - "Receta de venta": insumos de inventariovalorizado.parquet.
  - "Combo": productos de venta = platos de recetaventa.parquet, agrupados
    por Nomb Plato, costo = suma de Total de sus ítems ACTIVOS. Nunca es el
    precio de venta al público — mismo criterio que el resto de la
    herramienta, `precio` es siempre COSTO.
  - "Modificar": importa un plato activo del sistema (su receta en gramos
    y su precio de salón) para editarlo; la tabla de precios compara
    «Actual» contra «Nuevo».
  - "Guardadas": lee de vuelta lo que Guardar escribió en R2 — sin esto,
    "guardar una propuesta para que otra persona la vea" quedaba a medias
    (el archivo existía en R2, pero nadie en el equipo tenía dónde mirarlo
    sin abrir el bucket a mano).

Los tres modos de construcción comparten la misma lógica de línea/tabla/
costeo/guardado (parametrizada por `modo`, mismo espíritu que
graficos/recetas_comun.py con Base/Venta) — evita mantener dos copias del
mismo widget.

Guardar es una PROPUESTA en R2 (_recetas_propuestas/), nunca una escritura
a recetaventa.parquet — mismo principio que solicitar_refresco() en
data.py, que tampoco toca los parquets fuente directamente.

Desde el 2026-09-23 la receta/combo se descarga en PDF y Excel y se manda
«desde mi Gmail» (la fila de Guardar; ver `envio_receta.py` para el porqué
de abrir el Gmail del usuario en vez de mandar desde el servidor).

Desde el 2026-10-03 (regla #597) la receta puede llevar lo que el almacén
TODAVÍA NO TIENE: el buscador acepta un nombre escrito y el panel de la
derecha pregunta qué es —insumo de compra, (P) porcionado o (Rs) receta
base— y deja detallar los dos últimos. El panel alterna entre Precio,
«Dónde se usa» (las recetas activas que llevan cada artículo, también por
recetas base) y una pestaña por cada (P)/(Rs) nuevo. Las cuentas viven en
`articulos_nuevos.py`, puro y con test.

Afuera a propósito (quedan para commits siguientes):
  - Editar una Receta Base que YA existe (acá sólo se arman nuevas, aunque
    se puede partir de una del sistema).
  - "Cargar de vuelta en el editor" desde una propuesta guardada (el visor
    de este commit es de solo lectura).
  - Grupo/SubGrupo (sin fuente real definida para esa taxonomía todavía).

OJO — `Activo` en inventariovalorizado.parquet: a diferencia de
recetabase/recetaventa (con sus 4 formatos confirmados contra R2 real, ver
`_activo()` en recetas_comun.py y arquitectura.md regla #97), NO se
verificó si este parquet trae una columna de activo/inactivo ni en qué
formato. `_resolver` con candidatos razonables + degradación silenciosa
(sin insignia) si no aparece — nunca se asume una columna que no se
confirmó (probado contra R2 real: ningún candidato matcheó, la insignia
simplemente no sale, arquitectura.md regla #100).
"""

import json
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import articulos_nuevos as an
import envio_receta

from data import cargar as _cargar_reporte
from data import get_s3_cliente, secrets_disponibles
from graficos import alturas
from graficos.base import _resolver, una_vez_por_corrida
from tema import (
    ACENTO, ACENTO_TEXTO, ADVERTENCIA, ADVERTENCIA_FONDO, ADVERTENCIA_TEXTO,
    ERROR, EXITO, GRIS_TEXTO, GRIS_TEXTO_SUAVE, LAVANDA_CHIP, PALETA_SERIES,
    TEXTO_PRINCIPAL,
)
# El catálogo de insumos y el nombre de SU parquet viajan juntos, y viven
# allá desde el 2026-09-17 — ver el comentario de `_catalogo_insumos_
# cacheado` más abajo.
from graficos.recetas_comun import (
    ARCHIVO_INVENTARIO as _ARCHIVO_INVENTARIO,
    TASA_RECARGO, _activo, catalogo_insumos, divisor_neto, tasa_igv,
)

_ARCHIVO_RECETAVENTA = "recetaventa.parquet"
_ARCHIVO_RECETABASE = "recetabase.parquet"
_ARCHIVO_PORCIONAMIENTOS = "porcionamientos.parquet"
_ZONA_LIMA = ZoneInfo("America/Lima")   # Cloud corre en UTC
# IGV y recargo al consumo: los del SISTEMA, sumados sobre el neto (hoy
# 10,5 % + 13 %, precio ÷ 1,235). Viven en `recetas_comun` porque
# Composición usa la misma cuenta; regla #514.
_RECARGO = TASA_RECARGO
_UMBRAL_COSTO_OK = 30
_UMBRAL_COSTO_WARN = 35

_MODOS = ("venta", "combo", "modificar")
# Rótulo del segmented control → modo interno. «Guardadas» no arma nada.
_MODO_DE_ROTULO = {"Receta de venta": "venta", "Combo": "combo",
                   "Modificar": "modificar"}

# ─── Lo NUEVO: artículos que el almacén todavía no tiene (regla #597) ────
# Las tres clases del almacén, con lo que se le explica a quien elige. En
# Combo no se pregunta: lo nuevo es un producto de venta, con su costo
# estimado.
_CLASES_NUEVO = {
    "compra": ("Insumo de compra",
               "Se compra a un proveedor: pones su unidad y un precio estimado."),
    "p": ("(P) Porcionado",
          "Sale de porcionar o limpiar un insumo: dices de cuál y cuánto rinde."),
    "rs": ("(Rs) Receta base",
           "Se prepara con otros insumos: cargas sus ingredientes y cuánto rinde."),
}
_PREFIJO_NUEVO = {"p": "(P) ", "rs": "(Rs) "}
_UNIDADES_SALIDA_P = ("UND", "PORCION", "KILOS", "LITROS")
_UNIDADES_RS = ("KILOS", "LITROS", "UND", "PORCION")
_AREAS_RS = ("COCINA", "PRODUCCION", "BARRA")
_UNIDADES_COMPRA = ("KILOS", "LITROS", "UND")
# El color de lo nuevo en las tablas (columna Cód. y «Se usa en»): lavanda
# si su costo está completo, ámbar si es un precio ESTIMADO o le falta el
# detalle. El `data_editor` sólo pinta columnas no editables, y éstas lo son.
_ESTILO_NUEVO_OK = f"background-color: {LAVANDA_CHIP}; color: {ACENTO_TEXTO}; font-weight: 600"
_ESTILO_NUEVO_PEND = (f"background-color: {ADVERTENCIA_FONDO}; color: {ADVERTENCIA_TEXTO}; "
                      "font-weight: 600")

# Los cuatro trozos de la torta y sus puntos en la tabla de precios: el
# MISMO color en los dos sitios (pedido 2026-09-24: «recuerda colocar los
# puntos de color»). Costo y Utilidad son los de la dona de Composición
# (ACENTO/EXITO); Recargo e IGV, los dos siguientes de PALETA_SERIES.
# Validados juntos contra fondo blanco y daltonismo al hacer el mockup.
_COLOR_COSTO = ACENTO
_COLOR_UTIL = EXITO
_COLOR_RECARGO = PALETA_SERIES[1]
_COLOR_IGV = PALETA_SERIES[2]

# Alto de la tabla de insumos y de la torta. Salen de lo que deja la
# tarjeta a la altura de una pantalla (`alturas.PRESUPUESTO`) después de
# su cromo, MEDIDO en el navegador a 1366×768 (regla #512): así las dos
# tarjetas llenan la pantalla sin que ninguna tenga barra propia.
#   · Receta: padding 32 + cabecera 32 + nombre/buscador 40 + botonera 40
#     + pie 53 + 4 gaps de 12 = 245. «Modificar» suma la fila de importar
#     (40 + gap) y la nota contra el sistema (19 + gap): 83 más.
#   · Precio: padding 32 + cabecera 32 + tabla 229 + semáforo 39 + título
#     de la torta 32 + 4 gaps de 12 = 412.
# Re-medido el 2026-10-03, cuando se pidió «iguala en tamaño vertical las
# tarjetas»: a 1323×619 la de Receta medía 628 y la de Precio 597. El pie
# ya no medía 53 sino 68, y el panel de precio 16 menos de lo supuesto. Las
# dos se cuentan otra vez abajo, y además el CSS las estira a la más alta
# (`estilos/_80_cards.py`, el piso de «dos tarjetas en una fila»).
#
# La de la derecha, desde el mismo día, alterna paneles con una fila de
# pestañas (regla #597): todos comparten el cromo de arriba —padding,
# cabecera, pestañas y dos gaps— y cada uno estira SU tabla (o la torta)
# hasta el pie.
_CROMO_TARJETA_RECETA = 260
_FILAS_MODIFICAR = 83
_ALTO_PESTANAS = 32
_CROMO_PANEL = 32 + 32 + _ALTO_PESTANAS + 2 * 12
_ALTO_PANEL = alturas.PRESUPUESTO - _CROMO_PANEL
#   · Precio: tabla 223 + semáforo y pista 39 + título de la torta 22 + 3 gaps.
_ALTO_TORTA = _ALTO_PANEL - (223 + 39 + 22 + 3 * 12)
#   · (P): nombre 42 + «sale de» 40 + la fila con rótulos 68 + nota de
#     dos renglones 34 + resultado 64 + título 22 + 6 gaps.
_ALTO_CORTES_P = _ALTO_PANEL - (42 + 40 + 68 + 34 + 64 + 22 + 6 * 12)
#   · (Rs): nombre 42 + rinde/unidad/área 68 + buscador 40 + quitar y
#     resultado 88 + «partir de» 40 + 5 gaps.
_ALTO_TABLA_RS = _ALTO_PANEL - (42 + 68 + 40 + 88 + 40 + 5 * 12)
#   · Dónde se usa: el artículo 40 + la nota de dos renglones + 2 gaps.
_ALTO_NOTA_USOS = 34
_ALTO_TABLA_USOS = _ALTO_PANEL - (40 + _ALTO_NOTA_USOS + 2 * 12)
_ALTO_TABLA = alturas.PRESUPUESTO - _CROMO_TARJETA_RECETA
# «Se usa en», en la tabla de la receta: «20 platos · 36 bases» entero.
_ANCHO_USOS = 122


def _alto_tabla(modo):
    return _ALTO_TABLA - (_FILAS_MODIFICAR if modo == "modificar" else 0)


def _fmt(v):
    return f"S/ {v:,.2f}"


def _tasa(t):
    """0.105 → «10.5 %», 0.13 → «13 %»."""
    return f"{round(t * 100, 2):g} %"


def _key(modo, sufijo):
    return f"form_receta_{modo}_{sufijo}"


def _key_lineas(modo):
    return _key(modo, "lineas")


def _init_estado():
    for modo in _MODOS:
        st.session_state.setdefault(_key_lineas(modo), [])
        # Lo nuevo de la receta, por el código provisional de su línea
        # («NUEVO-3»): la clase y su detalle (regla #597).
        st.session_state.setdefault(_key(modo, "nuevos"), {})
        # El precio de venta: vacío (None) hasta que alguien escribe uno o
        # se importa un plato. Desde el 2026-10-03 NO es la key de su
        # `st.number_input` (ésa es `pv_w`): el panel de precio alterna con
        # otros, y un widget que no se dibuja pierde su valor (regla #597).
        st.session_state.setdefault(_key(modo, "pv"), None)
    st.session_state.setdefault("form_receta_contador_nuevo", 0)


def _total_lineas(lineas):
    return sum(l["cantidad"] * l["precio"] for l in lineas)


# ─── Catálogos (normalizados a las mismas 5 columnas: cod/nombre/unidad/
# precio/activo, para que _buscador_catalogo y _tabla_lineas no necesiten
# saber de qué parquet vino cada uno) ────────────────────────────────────
# El de insumos ya no vive acá: lo comparte `graficos.recetas_comun`
# desde el 2026-09-17, porque el simulador de Composición ofrece el MISMO
# catálogo para "agregar un insumo" y dos copias divergen (regla #379).
_catalogo_insumos_cacheado = catalogo_insumos


@st.cache_data(ttl=300, show_spinner=False)
def _catalogo_productos_venta_cacheado():
    """Productos de venta que puede usar un combo: cada PLATO de
    recetaventa.parquet, con costo por unidad = suma de Total de sus ítems
    ACTIVOS (mismo criterio que ya usa recetas_comun._activo()). Todo lo
    que entra a este catálogo ya está filtrado a activo -> no hace falta
    columna `activo` propia (a diferencia de inventariovalorizado)."""
    df = _cargar_reporte(_ARCHIVO_RECETAVENTA)
    if df is None or df.empty:
        return None

    col_plato = _resolver(df, ["Nomb Plato", "Nombre Plato", "PLATO", "Plato"])
    col_total = _resolver(df, ["Total", "TOTAL", "Importe", "Costo Total"])
    col_cod_plato = _resolver(df, ["COD PLATO", "Cod Plato"])
    col_activo_plato = _resolver(df, ["ITEM VENTA ACTIVO", "Item Venta Activo"])
    col_activo_ins = _resolver(df, ["INS ACTIVO", "Ins Activo"])
    if not (col_plato and col_total):
        return None

    d = df.copy()
    if col_activo_plato:
        d = d[_activo(d[col_activo_plato])]
    if col_activo_ins:
        d = d[_activo(d[col_activo_ins])]
    if d.empty:
        return None

    d["_total"] = pd.to_numeric(d[col_total], errors="coerce").fillna(0.0)
    if col_cod_plato:
        g = d.groupby(col_plato, as_index=False).agg(
            precio=("_total", "sum"), cod=(col_cod_plato, "first"),
        )
    else:
        g = d.groupby(col_plato, as_index=False).agg(precio=("_total", "sum"))
        g["cod"] = g[col_plato]
    g = g.rename(columns={col_plato: "nombre"})
    g = g[g["precio"] > 0]
    if g.empty:
        return None
    g["unidad"] = "porción"
    g["activo"] = None
    # El groupby de arriba ya deduplica por NOMBRE de plato; esto además
    # protege el mismo `add_<cod>` key de _buscador_catalogo por si un
    # COD PLATO se reutiliza entre dos platos con nombre distinto (mismo
    # crash que _catalogo_insumos_cacheado, ver comentario ahí).
    g = g.drop_duplicates(subset="cod", keep="first").reset_index(drop=True)
    return g[["cod", "nombre", "unidad", "precio", "activo"]]


def _es_activo_valor(fila):
    """activo puede ser True/False/None (bool de numpy o Python) — se
    normaliza a `is False` explícito para no confundir None (no se sabe)
    con False (confirmado inactivo)."""
    v = fila.get("activo")
    return bool(v) if v is not None and not pd.isna(v) else None


def _agregar_linea(modo, cod, nombre, unidad, precio, activo, tipo, lineas=None):
    """Suma una línea a la receta (o a `lineas`, las de una receta base
    nueva), salvo que ese código ya esté."""
    if lineas is None:
        lineas = st.session_state[_key_lineas(modo)]
    if any(l["cod"] == cod for l in lineas):
        return
    lineas.append({
        "cod": cod, "nombre": nombre, "unidad": unidad or "unidad",
        "precio": float(precio), "cantidad": 1.0, "activo": activo, "tipo": tipo,
    })


def _codigo_nuevo():
    """«NUEVO-7»: el código provisional de algo que el almacén no tiene.
    Uno por sesión y sin repetir, aunque la línea se quite."""
    st.session_state["form_receta_contador_nuevo"] += 1
    return f"NUEVO-{st.session_state['form_receta_contador_nuevo']}"


_SENTINEL_NUEVO = "➕  Crear un artículo nuevo (no está en el almacén)…"


@st.cache_data(ttl=300, show_spinner=False)
def _opciones_precomputadas(kind: str):
    """Precomputa la lista de opciones del selectbox una vez por catálogo.

    Antes vivía como `for _, fila in df_cat.iterrows(): …` DENTRO del
    buscador. Con miles de filas, `df.iterrows()` sobre pandas más un
    f-string por fila costaba varios segundos en cada rerun — y como
    `st.rerun()` era `scope="app"` hasta 2026-09-23, cada clic del
    botón «+» pagaba ese costo. Reportado con captura: «al intentar
    agregar un ítem el botón se bloquea y responde después de casi 1
    minuto». Con la vectorización + `scope="fragment"` el ida-y-vuelta
    baja al orden de 100 ms.

    Devuelve una tupla `(opciones_ordenadas, meta_por_etiqueta,
    cod_por_etiqueta)`. Cacheado por `kind` (nombre del catálogo) con
    el mismo TTL de 300 s que usan `catalogo_insumos` y
    `_catalogo_productos_venta_cacheado`."""
    if kind == "insumos":
        df = catalogo_insumos()
    elif kind == "productos_venta":
        df = _catalogo_productos_venta_cacheado()
    else:
        return [], {}, {}
    if df is None or df.empty:
        return [], {}, {}

    d = df.copy()
    d["cod"] = d["cod"].astype(str)
    d["nombre"] = d["nombre"].astype(str)
    d["unidad"] = d["unidad"].astype(str)
    d["precio_num"] = pd.to_numeric(d["precio"], errors="coerce").fillna(0.0)
    # Hasta 4 decimales: el catálogo de insumos va en unidad de COSTEO
    # (S/ 0,0381 el gramo), y con 2 se leía «S/ 0.04».
    d["precio_fmt"] = d["precio_num"].map(lambda p: f"S/ {_num(p)}")
    d["etiq"] = d["nombre"] + " · " + d["cod"] + " · " + d["unidad"] + " · " + d["precio_fmt"]
    if "activo" in d.columns:
        inactivo = d["activo"].apply(
            lambda v: (v is False) or (isinstance(v, bool) and not v)
        )
        d.loc[inactivo, "etiq"] = d.loc[inactivo, "etiq"] + " · Inactivo"

    opciones = d["etiq"].tolist()
    meta = {}
    for cod, nombre, unidad, precio, etiq, activo_val in zip(
        d["cod"].tolist(), d["nombre"].tolist(), d["unidad"].tolist(),
        d["precio_num"].tolist(), d["etiq"].tolist(),
        (d["activo"].tolist() if "activo" in d.columns else [None] * len(d)),
    ):
        # Normaliza el `activo` al mismo espíritu que `_es_activo_valor`.
        if activo_val is None or (isinstance(activo_val, float) and pd.isna(activo_val)):
            activo_norm = None
        else:
            activo_norm = bool(activo_val)
        meta[etiq] = (cod, nombre, unidad, float(precio), activo_norm)
    cod_por_etiq = {etiq: cod for etiq, (cod, *_rest) in meta.items()}
    return opciones, meta, cod_por_etiq


def _buscador_catalogo(modo, kind, c_main, c_btn, *, placeholder):
    """Buscador SUGESTIVO unificado con el alta de lo que NO está.

    `kind` es el nombre del catálogo (`"insumos"` o `"productos_venta"`)
    para `_opciones_precomputadas`, que ya trae la lista y el meta en un
    formato listo para el selectbox — pre-2026-09-23 iteraba con
    `df.iterrows()` en cada rerun y era el bottleneck del "+".

    Una sola fila: `st.selectbox` con los ítems del catálogo y el «+» al
    costado, que confirma la línea. El widget filtra client-side a medida
    que el usuario tipea.

    LO QUE NO ESTÁ (regla #597, 2026-10-03). Hasta ese día `st.selectbox`
    no le pasaba a Python el texto tipeado, así que la señal «acá no hay
    nada» la daba una opción centinela que, al elegirla, cambiaba el
    buscador por un `text_input`. Con `accept_new_options` el texto
    escrito SE PUEDE elegir: escribir «ajo negro» y darle Enter lo devuelve
    tal cual, y eso abre en el panel de la derecha la pestaña «Artículo
    nuevo», que pregunta qué es (compra, (P) o (Rs)). La centinela queda
    al final de la lista para quien la busque sin escribir.

    La key del widget lleva un contador incremental por modo, para que
    después de cada agregado el widget arranque limpio (Streamlit descarta
    el estado de la key vieja). Sin eso, la última opción marcada queda
    "pegada" y no se puede volver a elegir. Historia completa en
    `arquitectura.md` regla #497."""
    contador_key = _key(modo, "buscador_ver")
    st.session_state.setdefault(contador_key, 0)
    ver = st.session_state[contador_key]

    lineas_actuales = {l["cod"] for l in st.session_state[_key_lineas(modo)]}
    todas_opciones, meta, cod_por_etiq = _opciones_precomputadas(kind)
    # Filtrado O(N) sobre listas Python: sin `df.iterrows()` en la ruta caliente.
    opciones = [op for op in todas_opciones if cod_por_etiq[op] not in lineas_actuales]

    # Las dos columnas las abre el llamador, en la MISMA fila que el nombre
    # de la receta (mockup del 2026-09-24): nombre · buscador · «+».
    with c_main:
        elegido = st.selectbox(
            "Buscar", opciones + [_SENTINEL_NUEVO], index=None,
            placeholder=placeholder, accept_new_options=True,
            key=_key(modo, f"buscador_v{ver}"), label_visibility="collapsed",
        )
    es_nuevo = elegido is not None and elegido not in meta
    with c_btn:
        agregar = st.button(
            "➕", key=_key(modo, "add_sel"),
            disabled=elegido is None or es_nuevo,
            use_container_width=True,
            help="Agregar el ítem seleccionado a la lista",
        )
    if es_nuevo:
        _empezar_nuevo(modo, "" if elegido == _SENTINEL_NUEVO else str(elegido).strip())
        st.session_state[contador_key] = ver + 1
        st.rerun(scope="fragment")
    elif agregar and elegido:
        cod, nombre, unidad, precio, activo = meta[elegido]
        _agregar_linea(modo, cod, nombre, unidad, precio, activo, "almacen")
        st.session_state[contador_key] = ver + 1
        st.rerun(scope="fragment")


def _num(v):
    """Cantidad o precio unitario para leer: sin ceros de relleno y con
    hasta 4 decimales. Las recetas del sistema vienen en GRAMOS (3 g de
    pimienta a S/ 0,0381 el gramo): con `%.2f` fijo se leían «0.04»."""
    return f"{round(float(v), 4):,.4f}".rstrip("0").rstrip(".")


def _tachado(texto):
    """El texto con una raya encima, hecha con U+0336. El `data_editor`
    no acepta `text-decoration` (sólo color y fondo, y sólo en columnas
    no editables), así que la raya va en los propios caracteres."""
    return "".join(c + "̶" for c in texto)


def _cambios_vs_sistema(lineas, origen, pv=None):
    """Cuántas cosas cambiaron respecto de la receta importada: cantidad o
    precio unitario distinto, línea agregada, línea del sistema que se
    quitó, o el precio de venta."""
    if not origen:
        return 0
    orig = origen["lineas"]
    n = 1 if pv is not None and abs(pv - origen["pv"]) > 0.004 else 0
    for l in lineas:
        o = orig.get(l.get("sid"))
        if o is None:
            n += 1
        elif abs(l["cantidad"] - o[0]) > 1e-9 or abs(l["precio"] - o[1]) > 1e-9:
            n += 1
    presentes = {l.get("sid") for l in lineas}
    return n + sum(1 for c in orig if c not in presentes)


def _html_vacio(texto, alto):
    """El hueco de la tabla cuando todavía no tiene filas: MIDE lo mismo
    que la tabla, para que la tarjeta no salte al agregar el primer ítem.
    No es un `st.info`: su franja azul a todo el ancho se reportó como
    «franja fea» el 2026-09-23."""
    return (f'<div class="fr-vacio" style="height:{alto}px">'
            f'{html.escape(texto)}</div>')


def _tabla_lineas(modo, origen=None):
    """Devuelve `(lineas, marcadas)`: las líneas YA sincronizadas con lo que el usuario haya
    editado en el data_editor durante ESTE mismo rerun (no hace falta un
    st.rerun() extra: el propio data_editor ya disparó el rerun que llegó
    hasta acá; el llamador usa el valor devuelto, no una copia vieja).

    Alto FIJO (`_alto_tabla`), tenga una fila o cuarenta: la tabla es lo
    que se estira para que la tarjeta llegue al pie de la pantalla, y lo
    que no entra se desliza DENTRO de ella, no en la tarjeta (regla #382).

    `marcadas` son los índices con el ✕ tildado, para «Quitar marcadas».

    `origen` es la receta del sistema que se importó en «Modificar»: con
    él aparece la columna «Antes», con la cantidad del sistema tachada en
    las filas donde se cambió.

    Lo NUEVO (regla #597) no tiene código: su celda dice «NUEVO», en
    lavanda si su costo está completo y en ámbar si es estimado o le falta
    el detalle, y «Se usa en» dice cuál de las dos. En lo del almacén, esa
    columna cuenta las recetas activas que lo llevan, también por recetas
    base; cuáles son, en la pestaña «Dónde se usa». El precio y la unidad
    de un (P)/(Rs) nuevo salen de su detalle: lo que se escriba ahí se
    deshace."""
    lineas = st.session_state[_key_lineas(modo)]
    if not lineas:
        if modo == "modificar":
            vacio = ("Elige un plato del sistema arriba y dale «Importar»: "
                     "su receta aparece acá para editarla.")
        else:
            vacio = ("Busca un artículo arriba y agrégalo con «+»: "
                     "la receta se arma en esta tabla.")
        st.markdown(_html_vacio(vacio, _alto_tabla(modo)), unsafe_allow_html=True)
        return lineas, set()

    orig = origen["lineas"] if origen else {}
    total = _total_lineas(lineas)
    con_usos = modo != "combo"
    filas, estilos, fijos = [], [], set()
    for i, l in enumerate(lineas):
        subtotal = l["cantidad"] * l["precio"]
        pct = (subtotal / total * 100) if total > 0 else 0.0
        badges = []
        nuevo = l["tipo"] == "nuevo"
        if origen and not nuevo and l.get("sid") not in orig:
            badges.append("agregado")
        if l.get("activo") is False:
            badges.append("🔸 Inactivo")
        nombre_mostrado = l["nombre"] + (f"  ({', '.join(badges)})" if badges else "")
        if nuevo:
            completo, usos = _estado_nuevo(modo, l)
            estilos.append(_ESTILO_NUEVO_OK if completo else _ESTILO_NUEVO_PEND)
            if _modelo(modo, l)["clase"] in ("p", "rs"):
                fijos.add(i)
        else:
            usos = an.resumen_usos(_usos(l["cod"])) if con_usos else ""
            estilos.append("")
        fila = {
            "Quitar": False,
            "Código": "NUEVO" if nuevo else l["cod"],
            "Producto": nombre_mostrado,
            "Unidad": l["unidad"],
        }
        if origen:
            o = orig.get(l.get("sid"))
            cambio = o is not None and abs(l["cantidad"] - o[0]) > 1e-9
            fila["Antes"] = _tachado(_num(o[0])) if cambio else ""
        # Se MUESTRAN redondeados a 4 decimales; al leer de vuelta sólo
        # cuenta como edición lo que difiere de lo mostrado (ver abajo).
        fila["Cantidad"] = round(l["cantidad"], 4)
        fila["Precio unit. (S/)"] = round(l["precio"], 4)
        fila["Subtotal (S/)"] = round(subtotal, 2)
        fila["% del total"] = round(pct, 1)
        if con_usos:
            fila["Se usa en"] = usos
        filas.append(fila)
    df_show = pd.DataFrame(filas)
    # El Styler sólo pinta columnas NO editables: alcanza para el código,
    # «Se usa en» y «Antes».
    datos = df_show.style.apply(lambda _c: estilos, subset=["Código"])
    if con_usos:
        datos = datos.apply(
            lambda _c: [e or f"color: {GRIS_TEXTO}" for e in estilos], subset=["Se usa en"])
    if origen:
        datos = datos.set_properties(subset=["Antes"], **{"color": GRIS_TEXTO_SUAVE})

    editor_key = _key(modo, "editor")
    editado = st.data_editor(
        datos,
        key=editor_key,
        hide_index=True,
        use_container_width=True,
        height=_alto_tabla(modo),
        disabled=["Código", "Producto", "Antes", "Subtotal (S/)", "% del total",
                  "Se usa en"],
        # Cabeceras ABREVIADAS y anchos fijos (pedido 2026-09-23: «más
        # angostas las columnas de los insumos»). El data_editor no parte
        # una cabecera en dos renglones, así que se acorta el rótulo y el
        # nombre completo va al `help` (tooltip de la cabecera). Se cambia
        # sólo la ETIQUETA: la columna del df conserva su nombre, que es
        # lo que leen `editado["Cantidad"]` y compañía más abajo. Lo que
        # sobra de ancho lo reparte Streamlit entre todas.
        #
        # Cantidad y precio SIN `format` ni `step`: así el editor muestra
        # hasta 4 decimales sin ceros de relleno (3 g → «3», 0,0381 el
        # gramo → «0.0381»). Con `%.2f` los gramos del sistema se leían
        # «0.04» o, en kilos, «0.00»; y `format="plain"` no sirve: pide 20
        # decimales a numbro y 38.1356 sale «38.135600000000004».
        column_config={
            "Quitar": st.column_config.CheckboxColumn(
                "✕", width=36, help="Marcar para quitar"),
            "Código": st.column_config.TextColumn("Cód.", width=62),
            # Más angosto desde «Se usa en» (regla #597); con «Antes»,
            # además, para que la tabla no desborde a lo ancho: la suma de
            # los anchos no puede pasar de los ~680 de la tabla a 1323 px.
            "Producto": st.column_config.TextColumn(
                "Producto", width=110 if origen else 150 if con_usos else 190),
            "Unidad": st.column_config.TextColumn(
                "Und.", width=72, help="Unidad, tal cual la escribe el sistema"),
            "Antes": st.column_config.TextColumn(
                "Antes", width=52,
                help="Cantidad que tiene hoy el sistema, si la cambiaste"),
            "Cantidad": st.column_config.NumberColumn(
                "Cant.", width=52, help="Cantidad", min_value=0.0),
            "Precio unit. (S/)": st.column_config.NumberColumn(
                "P. unit.", width=62, help="Precio unitario (S/)",
                min_value=0.0),
            "Subtotal (S/)": st.column_config.NumberColumn(
                "Subtot.", width=58, help="Subtotal (S/)", format="%.2f"),
            "% del total": st.column_config.NumberColumn(
                "%", width=42, help="% del costo total", format="%.1f"),
            "Se usa en": st.column_config.TextColumn(
                "Se usa en", width=_ANCHO_USOS,
                help="Recetas ACTIVAS que lo llevan, directo o por una receta "
                     "base. Cuáles, en la pestaña «Dónde se usa» de la derecha."),
        },
    )

    deshacer = False
    for i, l in enumerate(lineas):
        fila = editado.iloc[i]
        # Lo mostrado está redondeado: pisar el valor guardado con lo que
        # volvió del editor, sin más, le cambiaría el costo a toda línea
        # de más de 4 decimales al primer clic en cualquier celda.
        for campo, col in (("cantidad", "Cantidad"), ("precio", "Precio unit. (S/)")):
            v = float(fila[col]) if pd.notna(fila[col]) else 0.0
            if abs(v - df_show.iloc[i][col]) > 1e-9:
                if i in fijos and campo == "precio":
                    deshacer = True
                else:
                    l[campo] = v
        und = str(fila["Unidad"]) or "unidad"
        if i in fijos:
            deshacer = deshacer or und != l["unidad"]
        else:
            l["unidad"] = und
    if deshacer:
        # El precio de un (P)/(Rs) nuevo es el de su detalle: la celda
        # vuelve a lo calculado (si no, mostraría lo tecleado y costaría
        # otra cosa).
        st.session_state.pop(_key(modo, "editor"), None)
        st.rerun(scope="fragment")

    marcadas = {i for i, v in enumerate(editado["Quitar"].tolist()) if v}
    return lineas, marcadas


def _desglose(pv):
    """(precio neto, monto de recargo, monto de IGV) del precio de venta
    `pv`. UNA sola copia de la fórmula: la usan el panel de precios y el
    envío por correo (`_resumen_envio`), y dos copias divergen."""
    if pv <= 0:
        return 0.0, 0.0, 0.0
    # Neto = precio ÷ divisor del sistema; IGV y recargo se calculan los
    # dos sobre el neto, no uno encima del otro (así los cobra el POS).
    base = pv / divisor_neto()
    return base, base * _RECARGO, base * tasa_igv()


def _botonera_tabla(modo, lineas, marcadas, origen=None):
    """Quitar marcadas · Vaciar · (Volver al original) · el resumen a la
    derecha. La fila se dibuja SIEMPRE, con los botones apagados si no hay
    a qué aplicarlos: que aparezca recién con la primera fila movía el pie
    de la tarjeta."""
    pv = float(st.session_state.get(_key(modo, "pv")) or 0.0)
    cambios = _cambios_vs_sistema(lineas, origen, pv)
    # columnas-internas: tres botones al ancho de su texto y el resumen
    # ocupa lo que sobra, alineado a la derecha.
    c_q, c_v, c_o, c_res = st.columns([1.35, 0.8, 1.55, 2.3],
                                      vertical_alignment="center")
    with c_q:
        if st.button("✕ Quitar marcadas", key=_key(modo, "quitar"),
                     disabled=not marcadas, use_container_width=True):
            st.session_state[_key_lineas(modo)] = [
                l for i, l in enumerate(lineas) if i not in marcadas]
            st.session_state.pop(_key(modo, "editor"), None)
            st.rerun(scope="fragment")
    with c_v:
        if st.button("Vaciar", key=_key(modo, "vaciar"), disabled=not lineas,
                     use_container_width=True):
            _vaciar(modo)
            st.rerun(scope="fragment")
    if modo == "modificar":
        with c_o:
            if st.button("↺ Volver al original", key=_key(modo, "original"),
                         disabled=not (origen and cambios),
                         use_container_width=True,
                         help="Deja la receta y el precio como están en el sistema"):
                _importar(origen["cod"], con_nombre=False)
                st.rerun(scope="fragment")
    n = len(lineas)
    if n:
        costo = _total_lineas(lineas)
        with c_res:
            st.markdown(
                f'<div class="fr-resumen">{n} {"ítem" if n == 1 else "ítems"}'
                f' · costo {_fmt(costo)}</div>', unsafe_allow_html=True)

    if modo == "modificar" and not origen:
        # La fila existe igual: su alto está contado en `_FILAS_MODIFICAR`.
        st.markdown('<div class="fr-nota">Importa un plato para ver aquí qué '
                    'cambió respecto del sistema.</div>', unsafe_allow_html=True)
    if origen:
        nota = ("Sin cambios respecto del sistema." if not cambios else
                f"{cambios} {'cambio' if cambios == 1 else 'cambios'} "
                "respecto del sistema.")
        st.markdown(f'<div class="fr-nota">{html.escape(nota)}</div>',
                    unsafe_allow_html=True)


def _vaciar(modo):
    """Deja el modo como recién abierto. En «Modificar» se va también la
    receta importada: vaciar la tabla y seguir mostrando «Actual» de un
    plato que ya no está sería comparar contra nada."""
    st.session_state[_key_lineas(modo)] = []
    st.session_state.pop(_key(modo, "editor"), None)
    if modo == "modificar":
        st.session_state.pop(_key(modo, "origen"), None)
        st.session_state.pop(_key(modo, "nombre"), None)
        st.session_state.pop(_key(modo, "pv"), None)
        st.session_state.pop(_key(modo, "pv_w"), None)
        st.session_state.pop(_key(modo, "plato_sel"), None)
    _soltar_nuevos(modo)


def _soltar_nuevos(modo):
    """Fuera lo nuevo a medio armar: su detalle, el alta en curso y la
    pestaña que lo mostraba."""
    st.session_state[_key(modo, "nuevos")] = {}
    st.session_state[_key(modo, "creando")] = None
    st.session_state[_key(modo, "panel")] = "precio"


def _estado_costo(pct):
    """(color, rótulo) del semáforo del % de costo, mismos umbrales que
    tuvo siempre esta herramienta (orientativos)."""
    if pct <= _UMBRAL_COSTO_OK:
        return EXITO, "muy bueno"
    if pct <= _UMBRAL_COSTO_WARN:
        return ADVERTENCIA, "aceptable"
    return ERROR, "alto"


def _cuentas(costo, pv):
    """Todo lo que la tabla de precios y la torta dicen de UN precio."""
    base, m_recargo, m_igv = _desglose(pv)
    return {
        "costo": costo, "pv": pv, "base": base, "recargo": m_recargo,
        "igv": m_igv, "util": base - costo,
        "pct": (costo / base * 100) if base > 0 else None,
    }


def _html_punto(color):
    return f'<span class="fr-punto" style="background:{color}"></span>'


def _html_fila_precio(concepto, color, valores, *, negativo=None):
    """Una fila de la tabla de precios en HTML: el punto de su color en la
    torta, el concepto y uno o dos montos (Actual/Nuevo)."""
    celdas = "".join(
        f'<div class="fr-p-num{" fr-p-neg" if negativo and negativo[i] else ""}">'
        f'{v}</div>' for i, v in enumerate(valores))
    return (f'<div class="fr-p-fila">'
            f'<div class="fr-p-concepto">{_html_punto(color)}'
            f'<span>{html.escape(concepto)}</span></div>{celdas}</div>')


def _monto(v, hay=True):
    if not hay:
        return "—"
    return f"−{abs(v):,.2f}" if v < -0.004 else f"{v:,.2f}"


def _al_cambiar_pv(modo):
    st.session_state[_key(modo, "pv")] = st.session_state.get(_key(modo, "pv_w"))


def _panel_precio(modo, costo, origen=None, aviso=None):
    """La tarjeta de la derecha: la tabla Costo · Precio · Neto ·
    Utilidad · Recargo · IGV, el semáforo del % de costo y la torta.

    **Por qué no es un `st.data_editor`** (lo fue hasta el 2026-09-24):
    se pidió un punto de color por fila, el mismo de su trozo en la
    torta, y una grilla de Glide sólo pinta texto. Ahora es HTML, salvo la
    celda del precio de venta, que es un `st.number_input` en su fila —
    la única que se escribe. De paso se fue el parche que revertía una
    edición en las filas calculadas: ya no hay dónde escribirlas.

    En «Modificar», con un plato importado, la tabla trae dos columnas:
    **Actual** (el costo de la receta y el precio de salón que tiene hoy el
    sistema) y **Nuevo** (lo que se está armando). Devuelve el precio de
    venta vigente."""
    k_pv, k_w = _key(modo, "pv"), _key(modo, "pv_w")
    pv = float(st.session_state.get(k_pv) or 0.0)
    N = _cuentas(costo, pv)
    A = _cuentas(origen["costo"], origen["pv"]) if origen else None
    hay_n = pv > 0
    # El widget se siembra con el precio guardado en cada corrida: si la
    # pestaña estuvo en otro panel, Streamlit ya le borró el suyo.
    st.session_state[k_w] = st.session_state.get(k_pv)

    cols_cls = "fr-p-dos" if A else "fr-p-una"
    with st.container(key="form_receta_ptabla"):
        cab = ('<div class="fr-p-fila fr-p-cab"><div>Concepto</div>'
               + ('<div class="fr-p-num" title="Lo que tiene hoy el sistema: '
                  'costo de la receta y precio de salón">Actual</div>' if A else "")
               + f'<div class="fr-p-num">{"Nuevo" if A else "S/"}</div></div>')
        fila_costo = _html_fila_precio(
            "Costo de la receta", _COLOR_COSTO,
            ([_monto(A["costo"])] if A else []) + [_monto(N["costo"])])
        st.markdown(f'<div class="{cols_cls}">{cab}{fila_costo}</div>',
                    unsafe_allow_html=True)

        # La fila editable: mismas proporciones que la grilla del HTML
        # (`fr-p-una`/`fr-p-dos` en estilos/_80_cards.py) y sin gap, para
        # que sus celdas caigan en las mismas columnas.
        with st.container(key="form_receta_prow"):
            # columnas-internas: calcan la grilla de la tabla HTML.
            if A:
                c_con, c_act, c_inp = st.columns([2.3, 1, 1.2], gap=None,
                                                 vertical_alignment="center")
            else:
                c_con, c_inp = st.columns([2.3, 1.4], gap=None,
                                          vertical_alignment="center")
            with c_con:
                st.markdown(
                    '<div class="fr-p-concepto">'
                    f'{_html_punto("transparent")}<span>Precio de venta</span></div>',
                    unsafe_allow_html=True)
            if A:
                with c_act:
                    st.markdown(f'<div class="fr-p-num">{_monto(A["pv"])}</div>',
                                unsafe_allow_html=True)
            with c_inp:
                st.number_input(
                    "Precio de venta", key=k_w, min_value=0.0, step=0.5,
                    format="%.2f", placeholder="0.00",
                    label_visibility="collapsed",
                    help="Precio de carta, con IGV y recargo incluidos",
                    on_change=_al_cambiar_pv, args=(modo,),
                )

        filas = [
            ("Precio neto (base)", "transparent", "base", False),
            ("Utilidad (neto − costo)", _COLOR_UTIL, "util", True),
            (f"Recargo al consumo ({_tasa(_RECARGO)})", _COLOR_RECARGO, "recargo", False),
            (f"IGV ({_tasa(tasa_igv())})", _COLOR_IGV, "igv", False),
        ]
        cuerpo = ""
        for concepto, color, campo, puede_neg in filas:
            vals, neg = [], []
            if A:
                vals.append(_monto(A[campo]))
                neg.append(puede_neg and A[campo] < 0)
            vals.append(_monto(N[campo], hay_n))
            neg.append(puede_neg and hay_n and N[campo] < 0)
            cuerpo += _html_fila_precio(concepto, color, vals, negativo=neg)
        st.markdown(f'<div class="{cols_cls}">{cuerpo}</div>',
                    unsafe_allow_html=True)

    # Semáforo: el % de costo sobre el neto, y en Modificar cómo cambia.
    partes = []
    for cuenta in ([A] if A else []) + [N]:
        if cuenta["pct"] is None:
            continue
        color, rotulo = _estado_costo(cuenta["pct"])
        partes.append(f'{_html_punto(color)}<b>{cuenta["pct"]:.1f}%</b> ({rotulo})')
    semaforo = ' <span class="fr-flecha">→</span> '.join(partes) if partes else (
        "escribe un precio para calcularlo")
    pista = ("Escribe el precio nuevo en su celda; lo demás se calcula." if A else
             "Escribe el precio de venta en su celda; lo demás se calcula.")
    # Con algo estimado o sin detalle en la receta, el aviso va en el
    # renglón de la pista (decisión del usuario, 2026-10-03: entra al costo,
    # con aviso). Un renglón, con el texto entero en el tooltip: así la
    # tarjeta no cambia de alto.
    linea = (f'<div class="fr-pista fr-aviso" title="{html.escape(aviso)}">⚠ '
             f'{html.escape(aviso)}</div>' if aviso else
             f'<div class="fr-pista">✎ {pista}</div>')
    st.markdown(
        f'<div class="fr-semaforo">% de costo sobre el neto: {semaforo}</div>{linea}',
        unsafe_allow_html=True)

    _torta(modo, N, A)
    return pv


def _torta(modo, N, A):
    """Cómo se reparte el precio de venta: costo, utilidad, recargo e IGV.
    El total va al CENTRO y no como porción, porque es la torta entera. En
    Modificar se elige qué precio mirar, el nuevo o el del sistema."""
    # columnas-internas: el título a la izquierda y el selector al ancho
    # de sus dos opciones.
    c_tit, c_sel = st.columns([1.6, 1], vertical_alignment="center")
    with c_tit:
        st.markdown('<div class="fr-titulo-2">Cómo se reparte el precio de venta</div>',
                    unsafe_allow_html=True)
    T = N
    if A:
        with c_sel:
            ver = st.segmented_control(
                "Qué precio", ["Nuevo", "Actual"], default="Nuevo",
                key=_key(modo, "torta_ver"), label_visibility="collapsed")
        if ver == "Actual":
            T = A

    if T["pv"] <= 0:
        st.markdown(
            f'<div class="fr-vacio" style="height:{_ALTO_TORTA}px">Escribe un '
            'precio de venta en la tabla para ver cómo se reparte.</div>',
            unsafe_allow_html=True)
        return
    if T["util"] < 0:
        st.markdown(
            '<div class="fr-perdida">Se vende a pérdida: el costo '
            f'({_fmt(T["costo"])}) supera el precio neto ({_fmt(T["base"])}) '
            f'en {_fmt(-T["util"])}. Sube el precio o baja el costo para '
            'ver el reparto.</div>', unsafe_allow_html=True)
        return

    trozos = [
        ("Costo", T["costo"], _COLOR_COSTO),
        ("Utilidad", T["util"], _COLOR_UTIL),
        (f"Recargo {_tasa(_RECARGO)}", T["recargo"], _COLOR_RECARGO),
        (f"IGV {_tasa(tasa_igv())}", T["igv"], _COLOR_IGV),
    ]
    # `sort=False` y sentido horario desde las 12: el orden (y el color)
    # de cada trozo no salta de un precio a otro.
    fig = go.Figure(go.Pie(
        labels=[t[0] for t in trozos], values=[t[1] for t in trozos],
        hole=0.62, sort=False, direction="clockwise", rotation=0,
        marker=dict(colors=[t[2] for t in trozos],
                    line=dict(color="white", width=2)),
        textinfo="none",
        hovertemplate="%{label}: S/ %{value:,.2f} (%{percent})<extra></extra>",
    ))
    fig.add_annotation(
        text=(f"<b>{_fmt(T['pv'])}</b><br>"
              f"<span style='font-size:11px;color:{GRIS_TEXTO}'>precio de venta</span>"),
        showarrow=False,
        font=dict(size=15, color=TEXTO_PRINCIPAL, family="DM Sans, sans-serif"),
    )
    fig.update_layout(
        height=_ALTO_TORTA, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=11),
    )
    # columnas-internas: la dona a su alto y la leyenda con los montos.
    c_dona, c_ley = st.columns([1, 1.35], vertical_alignment="center")
    with c_dona:
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False},
                        key=_key(modo, "torta"))
    with c_ley:
        filas = "".join(
            f'<div class="fr-ley-fila">{_html_punto(color)}'
            f'<span class="fr-ley-rot">{html.escape(rot)}</span>'
            f'<span class="fr-ley-num">S/ {v:,.2f}</span>'
            f'<span class="fr-ley-pct">{v / T["pv"] * 100:.1f}%</span></div>'
            for rot, v, color in trozos)
        total = ('<div class="fr-ley-fila fr-ley-total"><span></span>'
                 '<span class="fr-ley-rot">Precio de venta</span>'
                 f'<span class="fr-ley-num">S/ {T["pv"]:,.2f}</span>'
                 '<span class="fr-ley-pct">100%</span></div>')
        st.markdown(f'<div class="fr-leyenda">{filas}{total}</div>',
                    unsafe_allow_html=True)


def _correo_usuario():
    """El Gmail con el que entró (lo llena el login de Streamlit Cloud), o
    None: en local no hay login, y Cloud a veces lo devuelve vacío (ver
    `aviso_ingreso.py`)."""
    try:
        return getattr(st.user, "email", None) or None
    except Exception:
        return None


def _resumen_envio(tipo, nombre, autor, lineas, precio_venta, nuevos=()):
    """Todo lo que `envio_receta` necesita, COPIADO: el PDF y el Excel se
    arman recién al hacer clic, en otro hilo, y para entonces las líneas de
    `session_state` pueden haber cambiado."""
    base, m_recargo, m_igv = _desglose(precio_venta)
    return {
        "tipo": tipo, "nombre": nombre.strip(), "autor": autor,
        "fecha": datetime.now(_ZONA_LIMA).strftime("%d/%m/%Y %H:%M"),
        "lineas": [dict(l) for l in lineas],
        "costo_total": _total_lineas(lineas), "precio_venta": precio_venta,
        "base": base, "recargo": m_recargo, "igv": m_igv,
        "pct_recargo": _RECARGO * 100, "pct_igv": tasa_igv() * 100,
        # Lo que la receta lleva y el almacén no tiene, dicho en una línea
        # cada uno (regla #597).
        "nuevos": [an.describir(d) for d in nuevos],
    }


def _credenciales_correo():
    """(remitente, contraseña de aplicación) de los secrets, o None si
    faltan — mismo criterio que `aviso_ingreso.py`: un secret ausente no
    rompe nada, sólo apaga el envío automático."""
    try:
        rem = st.secrets.get("GMAIL_REMITENTE")
        clave = st.secrets.get("GMAIL_APP_PASSWORD")
    except Exception:
        return None
    return (rem, clave) if rem and clave else None


def _botones_envio(modo, cols, tipo, nombre, guardado_por, lineas, precio_venta,
                   nuevos=()):
    """PDF · Excel · «Enviar por correo», en las tres columnas `cols` de la
    fila de Guardar.

    Con `GMAIL_REMITENTE` + `GMAIL_APP_PASSWORD` en secrets, el tercer
    botón abre una fila de envío (`_fila_envio`) y la app manda el correo
    ELLA MISMA con el PDF y el Excel adjuntos (pedido: «debe adjuntarlo
    automáticamente»). Sin esos secrets queda el camino anterior: abrir el
    Gmail del usuario con el correo escrito, adjuntando a mano. Por qué
    cada uno, en el docstring de `envio_receta.py` y las reglas #502/#503.

    Los archivos de ⬇ se arman AL HACER CLIC (`data=` recibe una función),
    no en cada corrida: un PDF de matplotlib cuesta cientos de ms y esta
    fila se redibuja con cada «+» del buscador (regla #499)."""
    correo = _correo_usuario()
    listo = bool(nombre.strip()) and bool(lineas)
    falta = ("Ponle nombre y agrega al menos un ítem." if not listo else None)
    resumen = _resumen_envio(tipo, nombre, guardado_por.strip() or correo or "",
                             lineas, precio_venta, nuevos)
    c_pdf, c_xls, c_mail = cols
    with c_pdf:
        st.download_button(
            "⬇ PDF", data=lambda: envio_receta.pdf_receta(resumen),
            file_name=envio_receta.nombre_archivo(resumen, "pdf"),
            mime="application/pdf", key=_key(modo, "dl_pdf"),
            on_click="ignore", disabled=not listo, use_container_width=True,
            help=falta or "Descargar la receta en PDF",
        )
    with c_xls:
        st.download_button(
            "⬇ Excel", data=lambda: envio_receta.excel_receta(resumen),
            file_name=envio_receta.nombre_archivo(resumen, "xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=_key(modo, "dl_xlsx"), on_click="ignore", disabled=not listo,
            use_container_width=True,
            help=falta or "Descargar la receta en Excel",
        )

    cred = _credenciales_correo()
    k_abierto = _key(modo, "envio_abierto")
    with c_mail:
        if cred is None:
            st.link_button(
                "✉ Enviar desde mi Gmail",
                envio_receta.url_gmail(resumen, correo) if listo else "https://mail.google.com",
                disabled=not listo, use_container_width=True,
                help=falta or (
                    f"Abre {'el Gmail de ' + correo if correo else 'tu Gmail'} con "
                    "el correo ya escrito. Escribe a quién, arrastra el PDF y el "
                    "Excel que descargaste y dale Enviar."),
            )
        elif st.button("✉ Enviar por correo", key=_key(modo, "envio_abrir"),
                       disabled=not listo, use_container_width=True,
                       help=falta or "Mandar la receta con el PDF y el Excel adjuntos"):
            st.session_state[k_abierto] = not st.session_state.get(k_abierto, False)

    # El acuse de un envío ya hecho: viaja por session_state porque el
    # envío cierra la fila con un rerun, y lo que se pinta antes de un
    # rerun no se ve nunca (regla #474).
    acuse = st.session_state.pop(_key(modo, "envio_acuse"), None)
    if acuse:
        st.success(acuse)
    if cred is not None and listo and st.session_state.get(k_abierto):
        _fila_envio(modo, resumen, cred, correo)


def _fila_envio(modo, resumen, cred, correo):
    """Para · Enviar · Cancelar, debajo de la fila de Guardar. No es un
    `st.popover`: el CSS global de `_30_filtros.py` vuelve píldora de 180px
    a todo botón de popover, y un widget adentro de uno cerrado no se
    entera de lo que Python le escribe (regla #467)."""
    remitente, clave = cred
    k_ver = _key(modo, "envio_ver")
    ver = st.session_state.setdefault(k_ver, 0)
    # columnas-internas: el campo de destinatarios es lo único que necesita ancho.
    c_para, c_env, c_canc, _pad = st.columns([5, 1.6, 1.2, 2.2],
                                             vertical_alignment="center")
    with c_para:
        para = st.text_input(
            "Para", key=_key(modo, f"envio_para_v{ver}"),
            placeholder="correo@ejemplo.com, otro@ejemplo.com",
            label_visibility="collapsed",
        )
    with c_env:
        enviar = st.button("Enviar", type="primary", key=_key(modo, "envio_ok"),
                           use_container_width=True)
    with c_canc:
        if st.button("Cancelar", key=_key(modo, "envio_cancelar"),
                     type="tertiary", use_container_width=True):
            st.session_state[_key(modo, "envio_abierto")] = False
            st.rerun(scope="fragment")
    st.caption(f"Sale desde **{remitente}** con el PDF y el Excel adjuntos"
               + (f"; las respuestas llegan a {correo}." if correo
                  and correo.lower() != remitente.lower() else "."))
    if not enviar:
        return

    validos, invalidos = envio_receta.separar_destinatarios(para)
    if invalidos:
        st.warning("Revisa estas direcciones: " + ", ".join(invalidos))
        return
    if not validos:
        st.warning("Escribe al menos un destinatario.")
        return
    if len(validos) > envio_receta.MAX_DESTINATARIOS:
        st.warning(f"Máximo {envio_receta.MAX_DESTINATARIOS} destinatarios por envío.")
        return
    try:
        with st.spinner("Enviando…"):
            msg = envio_receta.armar_correo(resumen, remitente, validos,
                                            responder_a=correo)
            envio_receta.enviar_correo(msg, remitente, clave)
    except smtplib.SMTPAuthenticationError:
        st.error("Gmail rechazó la contraseña de aplicación de "
                 f"{remitente}. Revisa GMAIL_APP_PASSWORD en Secrets.")
        return
    except Exception as e:                             # red, SMTP, etc.
        st.error(f"No se pudo enviar: {e}")
        return
    st.session_state[_key(modo, "envio_acuse")] = (
        f"✉ Enviado a {', '.join(validos)} con el PDF y el Excel adjuntos.")
    st.session_state[_key(modo, "envio_abierto")] = False
    st.session_state[k_ver] = ver + 1                  # el «Para» arranca vacío
    st.rerun(scope="fragment")


def _guardar_propuesta(tipo, nombre, guardado_por, lineas, extra=None):
    """Escribe la propuesta como JSON en R2 (_recetas_propuestas/), mismo
    mecanismo que solicitar_refresco() en data.py (get_s3_cliente() +
    put_object). NUNCA escribe en recetaventa.parquet directamente — eso lo
    genera el pipeline diario a partir de la fuente real."""
    payload = {
        "tipo": tipo,
        "nombre": nombre,
        "guardado_por": guardado_por,
        "guardado_en": datetime.now(timezone.utc).isoformat(),
        "total": round(_total_lineas(lineas), 2),
        "lineas": [
            {k: l[k] for k in ("cod", "nombre", "unidad", "precio", "cantidad", "tipo")}
            for l in lineas
        ],
        # Lo nuevo y su detalle van en `articulos_nuevos` (por `extra`).
    }
    if extra:
        payload.update(extra)

    if not secrets_disponibles():
        st.info("🧪 Modo demo: no hay R2 configurado. Esto es lo que se habría guardado:")
        st.json(payload)
        return True

    try:
        s3 = get_s3_cliente()
        clave = f"_recetas_propuestas/{uuid.uuid4().hex}.json"
        s3.put_object(
            Bucket=st.secrets["R2_BUCKET"],
            Key=clave,
            Body=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        return True
    except Exception as e:
        st.error(f"No se pudo guardar la propuesta: {e}")
        return False


def _limpiar_modo(modo):
    """Tras guardar con éxito: vacía la receta/combo actual para la próxima.
    Deja 'guardado_por' tal cual (la persona probablemente guarde varias
    seguidas) pero limpia nombre + precio_venta + estado del pricing
    editor — son de ESTA receta, y dejarlos puestos invita a re-guardar
    por error con el título viejo."""
    st.session_state[_key_lineas(modo)] = []
    st.session_state.pop(_key(modo, "editor"), None)
    st.session_state.pop(_key(modo, "nombre"), None)
    st.session_state.pop(_key(modo, "pv"), None)
    st.session_state.pop(_key(modo, "pv_w"), None)
    st.session_state.pop(_key(modo, "origen"), None)
    st.session_state.pop(_key(modo, "plato_sel"), None)
    _soltar_nuevos(modo)


# ─── Modificar: importar una receta del sistema ─────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _platos_sistema():
    """{COD PLATO: plato} de los platos ACTIVOS de recetaventa.parquet, con
    su receta lista para cargar en la tabla.

    Cada plato trae nombre, subgrupo, precio de salón (`P.VENTA SALON`),
    costo y sus líneas en la unidad de COSTEO del sistema (`UNID COSTO`:
    GRAMOS, MILILITROS, ONZAS, UND…, con `P.UNIT COSTO` por esa unidad),
    la misma en que el buscador ofrece los artículos del almacén
    (`recetas_comun.catalogo_insumos`).

    Sólo insumos activos, mismo criterio que el catálogo de Combo. Las
    líneas van TAL CUAL las trae el sistema, en su orden y con su unidad
    escrita como allá («GRAMOS», «MILILITROS»): un insumo que la receta
    trae en dos líneas (Lomo a la Pimienta: Sal Maldon ×2) queda en dos
    líneas — a pedido, 2026-09-24. Por eso cada línea lleva `sid`, su
    posición en la receta, y es con él (no con el código, que se repite)
    que se compara contra el sistema."""
    df = _cargar_reporte(_ARCHIVO_RECETAVENTA)
    if df is None or df.empty:
        return {}
    c_cod = _resolver(df, ["COD PLATO", "Cod Plato"])
    c_nom = _resolver(df, ["NOMB PLATO", "Nomb Plato", "Nombre Plato"])
    c_sub = _resolver(df, ["SUBGRUPO", "Sub Grupo", "Subgrupo"])
    c_pv = _resolver(df, ["P.VENTA SALON", "P VENTA SALON"])
    c_act = _resolver(df, ["ITEM VENTA ACTIVO", "Item Venta Activo"])
    c_ins_act = _resolver(df, ["INS ACTIVO", "Ins Activo"])
    c_ins = _resolver(df, ["COD INS", "Cod Ins"])
    c_ins_nom = _resolver(df, ["INS RV", "Ins Rv"])
    c_und = _resolver(df, ["UNID COSTO", "Unid Costo"])
    c_cant = _resolver(df, ["CANTIDAD", "Cantidad"])
    c_pu = _resolver(df, ["P.UNIT COSTO", "P UNIT COSTO"])
    if not all((c_cod, c_nom, c_pv, c_ins, c_ins_nom, c_cant, c_pu)):
        return {}

    d = df
    if c_act:
        d = d[_activo(d[c_act])]
    if c_ins_act:
        d = d[_activo(d[c_ins_act])]
    d = d[d[c_ins].notna() & (d[c_ins].astype(str).str.strip() != "")]
    if d.empty:
        return {}
    d = d.assign(
        _cod=d[c_cod].astype(str), _ins=d[c_ins].astype(str),
        _cant=pd.to_numeric(d[c_cant], errors="coerce").fillna(0.0),
        _pu=pd.to_numeric(d[c_pu], errors="coerce").fillna(0.0),
        _pv=pd.to_numeric(d[c_pv], errors="coerce").fillna(0.0),
        _und=d[c_und].astype(str) if c_und else "unidad",
    )

    platos = {}
    for cod, g in d.groupby("_cod", sort=False):
        lineas = [
            {"sid": f"{cod}:{i}", "cod": ins, "nombre": str(nom),
             "unidad": str(und).strip() or "unidad",
             "cantidad": float(cant), "precio": float(pu)}
            for i, (ins, nom, und, cant, pu) in enumerate(zip(
                g["_ins"], g[c_ins_nom], g["_und"], g["_cant"], g["_pu"]))
        ]
        platos[cod] = {
            "cod": cod,
            "nombre": str(g[c_nom].iloc[0]).strip(),
            "subgrupo": str(g[c_sub].iloc[0]) if c_sub else "",
            "pv": float(g["_pv"].iloc[0]),
            "costo": sum(l["cantidad"] * l["precio"] for l in lineas),
            "lineas": lineas,
        }
    return dict(sorted(platos.items(), key=lambda kv: kv[1]["nombre"].lower()))


def _importar(cod_plato, con_nombre=True):
    """Carga en la tabla de «Modificar» la receta del plato tal como está
    en el sistema, y deja el precio de salón como precio nuevo de partida.

    `con_nombre=False` para «Volver al original»: ese botón está DEBAJO
    del campo del nombre, y Streamlit no deja escribir la key de un widget
    que ya se dibujó en esta corrida."""
    plato = _platos_sistema().get(cod_plato)
    if not plato:
        return
    modo = "modificar"
    st.session_state[_key_lineas(modo)] = [
        dict(l, activo=None, tipo="sistema") for l in plato["lineas"]]
    st.session_state[_key(modo, "origen")] = {
        "cod": plato["cod"], "nombre": plato["nombre"],
        "subgrupo": plato["subgrupo"], "pv": plato["pv"],
        "costo": plato["costo"],
        "lineas": {l["sid"]: (l["cantidad"], l["precio"]) for l in plato["lineas"]},
    }
    st.session_state[_key(modo, "pv")] = round(plato["pv"], 2)
    st.session_state.pop(_key(modo, "editor"), None)
    if con_nombre:
        st.session_state[_key(modo, "nombre")] = plato["nombre"]


def _importador():
    """Fila de arriba de «Modificar»: el buscador de platos activos, el
    botón «Importar» y, con uno ya importado, la píldora con cómo está hoy
    en el sistema. Devuelve la receta importada (`origen`) o None."""
    modo = "modificar"
    platos = _platos_sistema()
    origen = st.session_state.get(_key(modo, "origen"))
    if not platos:
        st.error(f"No se pudieron leer las recetas de {_ARCHIVO_RECETAVENTA}.")
        return origen

    # columnas-internas: el buscador se lleva el ancho, «Importar» al de
    # su texto y la píldora del sistema lo que queda.
    c_sel, c_btn, c_chip = st.columns([3.6, 1, 2.6], vertical_alignment="center")
    with c_sel:
        sel = st.selectbox(
            "Receta del sistema", list(platos), index=None,
            format_func=lambda c: (
                f"{platos[c]['nombre']} · {platos[c]['subgrupo']} · "
                f"S/ {platos[c]['pv']:,.2f} · {len(platos[c]['lineas'])} insumos"),
            placeholder=f"Buscar entre los {len(platos)} platos activos…",
            key=_key(modo, "plato_sel"), label_visibility="collapsed",
        )
    pendiente = sel is not None and (not origen or sel != origen["cod"])
    with c_btn:
        importar = st.button(
            "Importar", key=_key(modo, "importar"), disabled=sel is None,
            type="primary" if pendiente else "secondary",
            use_container_width=True,
            help="Llena la tabla con la receta tal como está en el sistema",
        )
    if origen:
        with c_chip:
            st.markdown(
                f'<div class="fr-chip" title="Cómo está hoy en el sistema: '
                f'subgrupo, precio de salón y costo de la receta">Sistema: '
                f'{html.escape(origen["subgrupo"])} · {_fmt(origen["pv"])} · '
                f'costo {origen["costo"]:,.2f}</div>', unsafe_allow_html=True)
    if importar and sel is not None:
        _importar(sel)
        st.rerun(scope="fragment")
    return origen


# ─── Lo nuevo: detalle, cuentas y paneles (regla #597) ──────────────────
# Un artículo NUEVO es una línea con `tipo="nuevo"` y un código provisional
# («NUEVO-3»). Su detalle vive aparte, en `_key(modo, "nuevos")`, con la
# clase (compra, p, rs o, en Combo, producto) y lo que hace falta para
# costearlo. El precio y la unidad de una línea (P) o (Rs) NO se escriben
# en la tabla: los pone `_sincronizar_nuevos` desde su detalle, al
# principio de cada corrida, para que la tabla, el panel de precio, el PDF
# y lo que se guarda digan lo mismo.
#
# Los widgets de los paneles guardan lo que cambian con `on_change`, que
# corre ANTES que la página: la tabla de la izquierda se dibuja primero y
# tiene que ver el detalle ya cambiado. Con el valor leído al dibujar el
# panel, la tabla quedaba una corrida atrás.
def _nuevos(modo):
    return st.session_state[_key(modo, "nuevos")]


def _modelo(modo, linea):
    """El detalle del artículo NUEVO de esta línea, o None si la línea es
    del almacén. Una línea nueva sin detalle —un insumo nuevo adentro de
    una receta base, o una de antes del 2026-10-03— cuenta como compra."""
    if linea.get("tipo") != "nuevo":
        return None
    return _nuevos(modo).get(linea["cod"]) or {"clase": "compra"}


def _semilla(k, valor):
    """Le da a un widget su valor de partida sólo si no tiene uno. Si una
    corrida abortada le borró el estado (regla #373), vuelve del detalle."""
    if k not in st.session_state:
        st.session_state[k] = valor


def _al_cambiar(modo, cod, campo, k):
    m = _nuevos(modo).get(cod)
    if m is not None:
        m[campo] = st.session_state.get(k)


def _corto(texto, n):
    texto = str(texto)
    return texto if len(texto) <= n else texto[:n - 1].rstrip() + "…"


@st.cache_data(ttl=300, show_spinner=False)
def _kardex():
    """{cod: (nombre, unidad de kardex, precio de kardex)} del almacén: de
    qué sale un (P) nuevo y a cuánto el kilo."""
    df = catalogo_insumos()
    if df is None or df.empty:
        return {}
    return {c: (n, u, float(p)) for c, n, u, p in zip(
        df["cod"], df["nombre"], df["unidad_kardex"], df["precio_kardex"])}


def _rotulo_kardex(cod):
    k = _kardex().get(cod)
    if not k:
        return str(cod)
    return f"{k[0]} · {cod} · S/ {k[2]:,.2f} {an.por_unidad(k[1])}"


@st.cache_data(ttl=300, show_spinner=False)
def _historia_porcionado(cod):
    """La merma de `cod` y los cortes que salieron de él en los últimos
    `an.VENTANA_DIAS` días (`articulos_nuevos.merma_y_cortes`)."""
    desde = (datetime.now(_ZONA_LIMA) - timedelta(days=an.VENTANA_DIAS)).date()
    return an.merma_y_cortes(_cargar_reporte(_ARCHIVO_PORCIONAMIENTOS), cod, desde=desde)


@st.cache_data(ttl=300, show_spinner=False)
def _indice_usos():
    """El índice de «dónde se usa» (`articulos_nuevos.indice_usos`) con las
    recetas de venta y base ACTIVAS. Un plato cuenta si están activos él y
    su receta; una receta base, si lo está ella."""
    vacio_rv = pd.DataFrame(columns=["plato", "nombre", "ins", "cant", "unid", "pv", "pct"])
    vacio_rb = pd.DataFrame(columns=["base", "nombre", "ins", "cant", "unid"])
    rv = _cargar_reporte(_ARCHIVO_RECETAVENTA)
    rb = _cargar_reporte(_ARCHIVO_RECETABASE)
    if rv is not None and not rv.empty:
        c = {k: _resolver(rv, v) for k, v in {
            "plato": ["COD PLATO", "Cod Plato"], "nombre": ["NOMB PLATO", "Nomb Plato"],
            "ins": ["COD INS", "Cod Ins"], "cant": ["CANTIDAD", "Cantidad"],
            "unid": ["UNID COSTO", "Unid Costo"], "pv": ["P.VENTA SALON", "P VENTA SALON"],
            "pct": ["%CST SALON", "% CST SALON"], "act": ["ITEM VENTA ACTIVO"],
            "rv_act": ["RV ACTIV", "RV ACTIVO"]}.items()}
        if all(c[k] for k in ("plato", "nombre", "ins", "cant")):
            d = rv
            for k in ("act", "rv_act"):
                if c[k]:
                    d = d[_activo(d[c[k]])]

            def num(col):
                return pd.to_numeric(d[col], errors="coerce").fillna(0.0) if col else 0.0

            vacio_rv = pd.DataFrame({
                "plato": d[c["plato"]].astype(str), "nombre": d[c["nombre"]].astype(str),
                "ins": d[c["ins"]].astype(str), "cant": num(c["cant"]),
                "unid": d[c["unid"]].astype(str) if c["unid"] else "",
                "pv": num(c["pv"]), "pct": num(c["pct"]) * 100})
    if rb is not None and not rb.empty:
        c = {k: _resolver(rb, v) for k, v in {
            "base": ["COD PROD RB"], "nombre": ["RB NOMBRE"], "ins": ["COD INS RB"],
            "cant": ["CANT"], "unid": ["UNID"], "act": ["RB ACT"]}.items()}
        if all(c[k] for k in ("base", "nombre", "ins", "cant")):
            d = rb[_activo(rb[c["act"]])] if c["act"] else rb
            vacio_rb = pd.DataFrame({
                "base": d[c["base"]].astype(str), "nombre": d[c["nombre"]].astype(str),
                "ins": d[c["ins"]].astype(str),
                "cant": pd.to_numeric(d[c["cant"]], errors="coerce").fillna(0.0),
                "unid": d[c["unid"]].astype(str) if c["unid"] else ""})
    return an.indice_usos(vacio_rv, vacio_rb)


def _usos(cod):
    return an.usos_de(_indice_usos(), cod)


@st.cache_data(ttl=300, show_spinner=False)
def _recetas_base_sistema():
    """{COD PROD RB: receta} de recetabase.parquet, activas e inactivas, para
    PARTIR de una al armar una nueva: nombre, unidad de salida, si está
    activa y sus insumos activos, en la unidad y al costo del sistema."""
    df = _cargar_reporte(_ARCHIVO_RECETABASE)
    if df is None or df.empty:
        return {}
    c = {k: _resolver(df, v) for k, v in {
        "cod": ["COD PROD RB"], "nombre": ["RB NOMBRE"], "unid_rb": ["RB UNID"],
        "act": ["RB ACT"], "ins": ["COD INS RB"], "ins_nom": ["INSUMO"], "cant": ["CANT"],
        "unid": ["UNID"], "pu": ["CST UNIT INS"], "ins_act": ["INS ACTIVO"]}.items()}
    if not all(c[k] for k in ("cod", "nombre", "ins", "ins_nom", "cant", "pu")):
        return {}
    d = df[_activo(df[c["ins_act"]])] if c["ins_act"] else df
    activa = _activo(d[c["act"]]) if c["act"] else pd.Series(True, index=d.index)
    d = d.assign(_act=activa, _cant=pd.to_numeric(d[c["cant"]], errors="coerce").fillna(0.0),
                 _pu=pd.to_numeric(d[c["pu"]], errors="coerce").fillna(0.0))
    recetas = {}
    for cod, g in d.groupby(c["cod"], sort=False):
        act = bool(g["_act"].iloc[0])
        nombre = str(g[c["nombre"]].iloc[0])
        recetas[str(cod)] = {
            "nombre": nombre, "activa": act,
            "unidad": str(g[c["unid_rb"]].iloc[0]).strip().upper() if c["unid_rb"] else "KILOS",
            "rotulo": nombre + ("" if act else " · inactiva"),
            "lineas": [{"cod": str(i), "nombre": str(n),
                        "unidad": str(u).strip() if c["unid"] else "unidad",
                        "cantidad": float(q), "precio": float(p), "activo": None,
                        "tipo": "almacen"}
                       for i, n, u, q, p in zip(
                           g[c["ins"]], g[c["ins_nom"]],
                           g[c["unid"]] if c["unid"] else [""] * len(g),
                           g["_cant"], g["_pu"])],
        }
    return dict(sorted(recetas.items(),
                       key=lambda kv: (not kv[1]["activa"], kv[1]["nombre"].lower())))


# ── Las cuentas ──
def _costo_p(m):
    """(insumo de entrada por unidad, costo por unidad de salida) de un (P)
    nuevo; (None, 0.0) mientras no diga de qué sale o le falte el peso."""
    k = _kardex().get(m.get("sale_de") or "")
    if not k:
        return None, 0.0
    ent = an.entrada_por_unidad(k[1], m["salida"], m.get("peso_g"), m.get("merma") or 0)
    if not ent:
        return None, 0.0
    return ent, ent * k[2]


def _costo_rs(m):
    """(costo de la tanda, costo por unidad de salida) de una (Rs) nueva."""
    return an.costo_receta_base(m["lineas"], m["rinde"])


def _falta_detalle(m):
    if m["clase"] == "p":
        return _costo_p(m)[1] <= 0
    if m["clase"] == "rs":
        return _costo_rs(m)[1] <= 0
    return False


def _estado_nuevo(modo, linea):
    """(completo, texto de «Se usa en») de una línea NUEVA. Completo es lo
    que va en lavanda; lo estimado o sin detalle, en ámbar."""
    m = _modelo(modo, linea)
    clase = m["clase"]
    if clase in ("p", "rs"):
        if _falta_detalle(m):
            return False, "falta detalle"
        if clase == "p":
            return True, "porcionado nuevo"
        if any(l.get("tipo") == "nuevo" for l in m["lineas"]):
            return False, "precio estimado"
        return True, "receta base nueva"
    if clase == "producto":
        return False, "costo estimado" if linea["precio"] > 0 else "sin costo"
    return False, "precio estimado" if linea["precio"] > 0 else "sin precio"


def _sincronizar_nuevos(modo):
    """Precio, unidad y nombre de cada línea (P)/(Rs) nueva, desde su
    detalle; y fuera el detalle de lo que ya no está en la receta.

    Si la unidad cambia (una receta base que pasa de KILOS a UND), la
    cantidad vuelve a 1: «180» gramos no son 180 unidades."""
    lineas = st.session_state[_key_lineas(modo)]
    nuevos = _nuevos(modo)
    presentes = {l["cod"] for l in lineas}
    for cod in [c for c in nuevos if c not in presentes]:
        del nuevos[cod]
    for l in lineas:
        m = nuevos.get(l["cod"]) if l.get("tipo") == "nuevo" else None
        if not m or m["clase"] not in ("p", "rs"):
            continue
        if m["clase"] == "p":
            costo, salida = _costo_p(m)[1], m["salida"]
        else:
            costo, salida = _costo_rs(m)[1], m["unidad"]
        und, factor = an.unidad_de_costeo(salida)
        if l["unidad"] != und:
            l["cantidad"] = 1.0
        l.update(unidad=und, precio=costo / factor, nombre=m["nombre"])


def _aviso_pendientes(modo, lineas):
    """La línea del panel de precio cuando el costo lleva algo ESTIMADO o
    sin detalle (decisión del usuario, 2026-10-03: entra al costo, con
    aviso), o None."""
    estimado, falta = [], []
    for l in lineas:
        if l.get("tipo") != "nuevo":
            continue
        m = _modelo(modo, l)
        if m["clase"] in ("p", "rs"):
            if _falta_detalle(m):
                falta.append(l["nombre"])
            elif m["clase"] == "rs" and any(x.get("tipo") == "nuevo" for x in m["lineas"]):
                estimado.append(l["nombre"])
        else:
            (estimado if l["precio"] > 0 else falta).append(l["nombre"])
    if not estimado and not falta:
        return None
    partes = []
    if estimado:
        partes.append("precios ESTIMADOS (" + ", ".join(estimado) + ")")
    if falta:
        partes.append("algo sin detalle que cuenta S/ 0.00 (" + ", ".join(falta) + ")")
    return "El costo lleva " + " y ".join(partes) + "."


def _detalle_nuevos(modo, lineas):
    """Lo que se GUARDA de cada artículo nuevo con la propuesta, y de lo que
    salen el PDF, el Excel y el correo (`articulos_nuevos.describir`)."""
    out = []
    for l in lineas:
        if l.get("tipo") != "nuevo":
            continue
        m = _modelo(modo, l)
        d = {"cod": l["cod"], "clase": m["clase"], "nombre": l["nombre"],
             "unidad": l["unidad"], "precio": l["precio"]}
        if m["clase"] == "compra":
            d.update(unidad_kardex=m.get("unidad_kardex") or l["unidad"],
                     precio_kardex_estimado=round(l["precio"] * m.get("factor", 1.0), 4))
        elif m["clase"] == "p":
            ent, costo = _costo_p(m)
            k = _kardex().get(m.get("sale_de") or "")
            d.update(sale_de=m.get("sale_de"), sale_de_nombre=k[0] if k else None,
                     sale_de_unidad=k[1] if k else None, sale_de_precio=k[2] if k else None,
                     salida=m["salida"], peso_g=m.get("peso_g"), merma_pct=m.get("merma"),
                     entrada_por_unidad=ent, costo_por_unidad=costo)
        elif m["clase"] == "rs":
            tanda, por = _costo_rs(m)
            d.update(rinde=m["rinde"], unidad_rinde=m["unidad"], area=m["area"],
                     costo_tanda=tanda, costo_por_unidad=por,
                     lineas=[{k: x[k] for k in ("cod", "nombre", "unidad", "cantidad",
                                                "precio", "tipo")} for x in m["lineas"]])
        out.append(d)
    return out


# ── Crear ──
def _empezar_nuevo(modo, nombre):
    """Abre la pestaña «Artículo nuevo» del panel con `nombre` escrito. La
    versión en las keys hace que cada alta arranque de cero."""
    ver = st.session_state.get(_key(modo, "creando_ver"), 0) + 1
    st.session_state[_key(modo, "creando_ver")] = ver
    st.session_state[_key(modo, "creando")] = ver
    st.session_state[_key(modo, f"crear_nombre_v{ver}")] = nombre
    st.session_state[_key(modo, "panel")] = "crear"


def _crear(modo, clase, nombre, unidad, precio_kardex):
    """Suma la línea nueva y su detalle. Un (P) o una (Rs) abren su pestaña
    para detallarse; lo demás vuelve al precio."""
    cod = _codigo_nuevo()
    pref = _PREFIJO_NUEVO.get(clase)
    if pref and not nombre.lower().startswith(pref.strip().lower()):
        nombre = pref + nombre
    if clase == "p":
        m = {"clase": "p", "nombre": nombre, "sale_de": None, "salida": "UND",
             "peso_g": 0.0, "merma": 0.0}
        und, precio = "UND", 0.0
    elif clase == "rs":
        m = {"clase": "rs", "nombre": nombre, "rinde": 1.0, "unidad": "KILOS",
             "area": _AREAS_RS[0], "lineas": [], "ver": 0}
        und, precio = "GRAMOS", 0.0
    elif clase == "producto":
        m = {"clase": "producto", "nombre": nombre}
        und, precio = "porción", float(precio_kardex)
    else:
        und, factor = an.unidad_de_costeo(unidad)
        m = {"clase": "compra", "nombre": nombre, "unidad_kardex": unidad, "factor": factor}
        precio = float(precio_kardex) / factor
    _nuevos(modo)[cod] = m
    _agregar_linea(modo, cod, nombre, und, precio, None, "nuevo")
    st.session_state[_key(modo, "creando")] = None
    st.session_state[_key(modo, "panel")] = cod if clase in ("p", "rs") else "precio"


def _panel_crear(modo):
    """«Artículo nuevo»: el nombre escrito en el buscador y QUÉ ES. Una
    compra se agrega con su precio estimado; un (P) o una (Rs) se agregan
    sin costo y abren su pestaña para detallarse."""
    ver = st.session_state.get(_key(modo, "creando"))
    es_combo = modo == "combo"
    nombre = st.text_input(
        "Nombre del artículo nuevo", key=_key(modo, f"crear_nombre_v{ver}"),
        placeholder="nombre del artículo nuevo…")
    if es_combo:
        clase = "producto"
    else:
        # El contenedor con key fija es el ancla del CSS: el `label` global
        # va en versalitas, y las opciones de un radio son `<label>`.
        with st.container(key="form_receta_crear_tipo"):
            clase = st.radio(
                "¿Qué es?", list(_CLASES_NUEVO), key=_key(modo, f"crear_clase_v{ver}"),
                format_func=lambda c: _CLASES_NUEVO[c][0],
                captions=[desc for _, desc in _CLASES_NUEVO.values()])
    unidad, precio = "UND", 0.0
    if clase in ("compra", "producto"):
        # columnas-internas: la unidad a su ancho y el precio con el resto.
        c_u, c_p = st.columns([1, 1.6], vertical_alignment="bottom")
        with c_u:
            unidad = "porción" if es_combo else st.selectbox(
                "Unidad del almacén", _UNIDADES_COMPRA, key=_key(modo, f"crear_und_v{ver}"))
        with c_p:
            precio = st.number_input(
                "Costo estimado (S/ por porción)" if es_combo else
                f"Precio estimado (S/ {an.por_unidad(unidad)})",
                min_value=0.0, step=0.5, format="%.2f", key=_key(modo, f"crear_precio_v{ver}"))
        und, factor = an.unidad_de_costeo(unidad)
        nota = ("Entra al costo con un aviso, hasta que exista en el sistema."
                if es_combo or factor == 1 else
                f"Se costea en {und}: S/ {_num(precio / factor)} {an.por_unidad(und)}. "
                "Entra al costo con un aviso, hasta que el almacén lo cree.")
    else:
        nota = ("Al agregarlo se abre su pestaña para decir de qué insumo sale y "
                "cuánto rinde. Hasta entonces la tabla lo marca «falta detalle»."
                if clase == "p" else
                "Al agregarla se abre su pestaña para cargar sus insumos y cuánto "
                "rinde. Hasta entonces la tabla la marca «falta detalle».")
    st.markdown(f'<div class="fr-nota">{html.escape(nota)}</div>', unsafe_allow_html=True)
    # columnas-internas: los dos botones a su ancho, a la izquierda.
    c_ok, c_no, _pad = st.columns([1.6, 1, 1.2])
    with c_ok:
        agregar = st.button("Agregar a la receta", type="primary",
                            key=_key(modo, f"crear_ok_v{ver}"),
                            disabled=not nombre.strip(), use_container_width=True)
    with c_no:
        cancelar = st.button("Cancelar", key=_key(modo, f"crear_no_v{ver}"),
                             use_container_width=True)
    if cancelar:
        st.session_state[_key(modo, "creando")] = None
        st.session_state[_key(modo, "panel")] = "precio"
        st.rerun(scope="fragment")
    if agregar and nombre.strip():
        _crear(modo, clase, nombre.strip(), unidad, precio)
        st.rerun(scope="fragment")


# ── Detallar ──
def _al_renombrar(modo, cod, k):
    """El nombre de un (P)/(Rs) nuevo lleva su prefijo, como en el almacén."""
    m = _nuevos(modo).get(cod)
    if m is None:
        return
    v = str(st.session_state.get(k) or "").strip()
    pref = _PREFIJO_NUEVO.get(m["clase"], "")
    if pref and not v.lower().startswith(pref.strip().lower()):
        v = pref + v
    m["nombre"] = v
    st.session_state[k] = v


def _campo_nombre(modo, cod, m):
    k = _key(modo, f"{cod}_nombre")
    _semilla(k, m["nombre"])
    # columnas-internas: la píldora a su ancho y el nombre con el resto.
    c_b, c_n = st.columns([0.9, 4], vertical_alignment="center")
    with c_b:
        st.markdown('<span class="fr-nuevo">NUEVO</span>', unsafe_allow_html=True)
    with c_n:
        st.text_input("Nombre", key=k, label_visibility="collapsed",
                      on_change=_al_renombrar, args=(modo, cod, k))


def _al_elegir_entrada(modo, cod, k):
    """Al elegir de qué sale un (P), la merma propuesta es la de ESE insumo
    en sus porcionamientos de los últimos 90 días; sin historia, 0."""
    m = _nuevos(modo).get(cod)
    if m is None:
        return
    m["sale_de"] = st.session_state.get(k)
    h = _historia_porcionado(m["sale_de"]) if m["sale_de"] else None
    m["merma"] = round(h["merma_pct"], 1) if h and h["merma_pct"] is not None else 0.0
    st.session_state[_key(modo, f"{cod}_merma")] = m["merma"]


def _html_caja(filas):
    """La caja lavanda con el resultado de un detalle: (rótulo, valor,
    destacado) por renglón."""
    cuerpo = "".join(
        f'<span class="{"fr-caja-fuerte" if fuerte else ""}">{html.escape(r)}</span>'
        f'<span class="fr-caja-num{" fr-caja-fuerte" if fuerte else ""}">{html.escape(v)}</span>'
        for r, v, fuerte in filas)
    return f'<div class="fr-caja">{cuerpo}</div>'


def _panel_p(modo, cod):
    """Un (P) nuevo, por RENDIMIENTO (decisión del usuario, 2026-10-03): de
    qué insumo sale, cómo sale, lo que pesa una pieza y la merma. Debajo,
    los cortes que ya salen de ese insumo, con su peso REAL — el nombre
    dice lo pedido («Medallon 200gr» pesa 180 g en sus porcionamientos)."""
    m = _nuevos(modo)[cod]
    _campo_nombre(modo, cod, m)
    k_sd = _key(modo, f"{cod}_sale_de")
    _semilla(k_sd, m.get("sale_de"))
    st.selectbox(
        "Sale de", list(_kardex()), index=None, format_func=_rotulo_kardex, key=k_sd,
        placeholder="¿De qué insumo sale? Busca en el almacén…",
        label_visibility="collapsed", on_change=_al_elegir_entrada, args=(modo, cod, k_sd))
    k = _kardex().get(m.get("sale_de") or "")
    pesa = bool(k) and k[1].upper() in an.CONVERSION_ESTANDAR
    por_peso = pesa and m["salida"] in an.POR_PIEZA
    # columnas-internas: cómo sale · cuánto pesa · cuánta merma.
    c_s, c_p, c_m = st.columns([1.1, 1.2, 1])
    with c_s:
        k_sal = _key(modo, f"{cod}_salida")
        _semilla(k_sal, m["salida"])
        st.selectbox("Sale en", _UNIDADES_SALIDA_P, key=k_sal,
                     on_change=_al_cambiar, args=(modo, cod, "salida", k_sal))
    with c_p:
        k_peso = _key(modo, f"{cod}_peso")
        _semilla(k_peso, float(m.get("peso_g") or 0.0))
        st.number_input(
            "Peso (" + ("ml" if k and k[1].upper() == "LITROS" else "g") + ")",
            min_value=0.0, step=5.0, format="%.0f", key=k_peso, disabled=not por_peso,
            help=("Lo que pesa una pieza ya porcionada." if por_peso else
                  "Sólo para piezas (UND, PORCION) que salen de algo que se pesa: "
                  "lo que pesa una ya porcionada."),
            on_change=_al_cambiar, args=(modo, cod, "peso_g", k_peso))
    with c_m:
        k_mer = _key(modo, f"{cod}_merma")
        _semilla(k_mer, float(m.get("merma") or 0.0))
        st.number_input("Merma %", min_value=0.0, max_value=95.0, step=0.5,
                        format="%.1f", key=k_mer,
                        on_change=_al_cambiar, args=(modo, cod, "merma", k_mer))

    h = _historia_porcionado(m["sale_de"]) if k else None
    if not k:
        nota = "Elige de qué insumo del almacén sale: la merma se propone con su historia."
    elif h["merma_pct"] is None:
        nota = (f"{k[0]} no tiene porcionamientos en los últimos {an.VENTANA_DIAS} "
                "días: escribe la merma.")
    else:
        nota = (f"{h['merma_pct']:.1f} % es la merma de {k[0]} en sus {h['n']} "
                f"porcionamientos de los últimos {an.VENTANA_DIAS} días "
                f"({h['porcionado']:,.1f} {k[1].lower()}).")
    st.markdown(f'<div class="fr-nota fr-nota-2">{html.escape(nota)}</div>',
                unsafe_allow_html=True)

    ent, costo = _costo_p(m)
    u_ent = k[1].lower() if k else ""
    una = an.nombre_unidad(m["salida"])
    st.markdown(_html_caja([
        (f"{k[0] if k else 'Insumo'} por {una}", an.cantidad_en(ent, k[1]) if ent else "—", False),
        (f"Costo por {una}", _fmt(costo) if costo else "—", True),
    ]), unsafe_allow_html=True)

    st.markdown(f'<div class="fr-titulo-2">Cortes que ya salen de este insumo · '
                f'{an.VENTANA_DIAS} días</div>', unsafe_allow_html=True)
    cortes = h["cortes"] if h else None
    if cortes is None or cortes.empty:
        st.markdown(_html_vacio("Sin porcionamientos de este insumo en la ventana.",
                                _ALTO_CORTES_P), unsafe_allow_html=True)
        return
    pieza = cortes["unidad"].str.upper().isin(an.POR_PIEZA)
    tabla = pd.DataFrame({
        "Corte": cortes["nombre"],
        "Porc.": cortes["n"],
        "Peso real": [f"{p * 1000:,.0f} g" if es else "—"
                      for p, es in zip(cortes["peso_x_und"], pieza)],
        "Insumo x und": [f"{e:.3f}" for e in cortes["entrada_x_und"]],
        "Costo": [_fmt(e * k[2]) for e in cortes["entrada_x_und"]],
    })
    st.dataframe(
        tabla, hide_index=True, use_container_width=True, height=_ALTO_CORTES_P,
        key=_key(modo, f"{cod}_cortes"),
        column_config={
            "Corte": st.column_config.TextColumn("Corte", width=150),
            "Porc.": st.column_config.NumberColumn(
                "Porc.", width=42, help="Porcionamientos en la ventana"),
            "Peso real": st.column_config.TextColumn(
                "Peso real", width=62, help="Lo que pesó cada pieza, en promedio"),
            "Insumo x und": st.column_config.TextColumn(
                f"{u_ent or 'insumo'}", width=58,
                help="Lo que se gastó del insumo por unidad del corte, en su unidad"),
            "Costo": st.column_config.TextColumn(
                "Costo", width=70, help="Por unidad del corte, al precio de hoy"),
        })


def _al_editar_rs(modo, cod, k):
    """Lo tecleado en la tabla de una (Rs) nueva va a su detalle ANTES de
    dibujar la página (ver el comentario de arriba del bloque)."""
    m = _nuevos(modo).get(cod)
    estado = st.session_state.get(k) or {}
    if m is None:
        return
    for i, cambios in (estado.get("edited_rows") or {}).items():
        i = int(i)
        if i >= len(m["lineas"]):
            continue
        l = m["lineas"][i]
        for col, campo in (("Cantidad", "cantidad"), ("Precio unit. (S/)", "precio")):
            if col in cambios and cambios[col] is not None:
                l[campo] = float(cambios[col])
        if "Unidad" in cambios and l.get("tipo") == "nuevo":
            l["unidad"] = str(cambios["Unidad"] or "unidad")


def _al_partir_de(modo, cod, k):
    """Carga en una (Rs) nueva los insumos de una receta base del sistema."""
    m = _nuevos(modo).get(cod)
    rb = _recetas_base_sistema().get(st.session_state.get(k) or "")
    if m is None or not rb:
        return
    m["lineas"] = [dict(l) for l in rb["lineas"]]
    m["rinde"] = 1.0
    if rb["unidad"] in _UNIDADES_RS:
        m["unidad"] = rb["unidad"]
    st.session_state[_key(modo, f"{cod}_rinde")] = m["rinde"]
    st.session_state[_key(modo, f"{cod}_unidad")] = m["unidad"]
    st.session_state.pop(_key(modo, f"{cod}_editor"), None)
    m["ver"] = m.get("ver", 0) + 1


def _panel_rs(modo, cod):
    """Una (Rs) nueva: cuánto rinde, sus insumos —del almacén, o nuevos con
    precio estimado— y lo que cuesta en este plato. Se puede partir de una
    receta base del sistema, activa o no."""
    m = _nuevos(modo)[cod]
    ver = m.setdefault("ver", 0)
    _campo_nombre(modo, cod, m)
    # columnas-internas: rinde · unidad · área, los tres angostos.
    c_r, c_u, c_a = st.columns([1, 1.1, 1.3])
    with c_r:
        k_r = _key(modo, f"{cod}_rinde")
        _semilla(k_r, float(m["rinde"]))
        st.number_input("Rinde", min_value=0.001, step=0.5, format="%.3f", key=k_r,
                        on_change=_al_cambiar, args=(modo, cod, "rinde", k_r))
    with c_u:
        k_u = _key(modo, f"{cod}_unidad")
        _semilla(k_u, m["unidad"])
        st.selectbox("Unidad", _UNIDADES_RS, key=k_u,
                     on_change=_al_cambiar, args=(modo, cod, "unidad", k_u))
    with c_a:
        k_a = _key(modo, f"{cod}_area")
        _semilla(k_a, m["area"])
        st.selectbox("Área", _AREAS_RS, key=k_a,
                     on_change=_al_cambiar, args=(modo, cod, "area", k_a))

    todas, meta, cod_por_etiq = _opciones_precomputadas("insumos")
    presentes = {l["cod"] for l in m["lineas"]}
    # columnas-internas: el buscador con el ancho y el «+» al de su glifo.
    c_b, c_m = st.columns([6, 0.8], vertical_alignment="center")
    with c_b:
        el = st.selectbox(
            "Insumo de la receta base", [o for o in todas if cod_por_etiq[o] not in presentes],
            index=None, accept_new_options=True, key=_key(modo, f"{cod}_bus_v{ver}"),
            placeholder="Agregar insumo… (o escribe uno que no está)",
            label_visibility="collapsed")
    nuevo = el is not None and el not in meta
    with c_m:
        mas = st.button("➕", key=_key(modo, f"{cod}_add"), disabled=el is None or nuevo,
                        use_container_width=True, help="Agregar el insumo elegido")
    if nuevo and str(el).strip():
        _agregar_linea(modo, _codigo_nuevo(), str(el).strip(), "GRAMOS", 0.0, None,
                       "nuevo", lineas=m["lineas"])
    elif mas and el:
        c, n, u, p, a = meta[el]
        _agregar_linea(modo, c, n, u, p, a, "almacen", lineas=m["lineas"])
    if (nuevo and str(el).strip()) or (mas and el):
        m["ver"] = ver + 1
        st.rerun(scope="fragment")

    marcadas = _tabla_rs(modo, cod, m)
    tanda, por = _costo_rs(m)
    und, factor = an.unidad_de_costeo(m["unidad"])
    linea = next((l for l in st.session_state[_key_lineas(modo)] if l["cod"] == cod), None)
    # columnas-internas: «Quitar» a su ancho y el resultado con el resto.
    c_q, c_res = st.columns([0.9, 2.6], vertical_alignment="top")
    with c_q:
        if st.button("✕ Quitar", key=_key(modo, f"{cod}_quitar"),
                     help="Quitar los insumos marcados con ✕",
                     disabled=not marcadas, use_container_width=True):
            m["lineas"] = [l for i, l in enumerate(m["lineas"]) if i not in marcadas]
            st.session_state.pop(_key(modo, f"{cod}_editor"), None)
            st.rerun(scope="fragment")
    with c_res:
        filas = [(f"Costo de {an.cantidad_en(m['rinde'], m['unidad'])}", _fmt(tanda), False),
                 (f"Costo por {an.nombre_unidad(m['unidad'])}", _fmt(por), False)]
        if linea:
            filas.append((f"En este plato · {an.cantidad_en(linea['cantidad'], und)}",
                          _fmt(linea["cantidad"] * por / factor), True))
        st.markdown(_html_caja(filas), unsafe_allow_html=True)
    rbs = _recetas_base_sistema()
    k_pd = _key(modo, f"{cod}_partir_v{ver}")
    st.selectbox(
        "Partir de", list(rbs), index=None, format_func=lambda c: rbs[c]["rotulo"],
        key=k_pd, placeholder="Partir de una receta base del sistema…",
        label_visibility="collapsed", disabled=bool(m["lineas"]),
        help=("Vacía la tabla para partir de otra receta." if m["lineas"] else
              "Carga sus insumos (activos) para editarlos acá. No toca la del sistema."),
        on_change=_al_partir_de, args=(modo, cod, k_pd))


def _tabla_rs(modo, cod, m):
    """Los insumos de una (Rs) nueva, editables como los de la receta. Lo
    nuevo lleva «NUEVO» en ámbar: su precio lo escribe quien la arma.
    Devuelve las filas marcadas para quitar."""
    lineas = m["lineas"]
    if not lineas:
        st.markdown(_html_vacio(
            "Busca arriba sus insumos (o escribe uno que el almacén no tiene) y "
            "agrégalos con «+». O parte de una receta base del sistema, abajo.",
            _ALTO_TABLA_RS), unsafe_allow_html=True)
        return set()
    df_show = pd.DataFrame([{
        "Quitar": False,
        "Código": "NUEVO" if l.get("tipo") == "nuevo" else l["cod"],
        "Insumo": l["nombre"],
        "Unidad": l["unidad"],
        "Cantidad": round(l["cantidad"], 4),
        "Precio unit. (S/)": round(l["precio"], 4),
        "Subtotal (S/)": round(l["cantidad"] * l["precio"], 2),
    } for l in lineas])
    estilos = [_ESTILO_NUEVO_PEND if l.get("tipo") == "nuevo" else "" for l in lineas]
    k = _key(modo, f"{cod}_editor")
    editado = st.data_editor(
        df_show.style.apply(lambda _c: estilos, subset=["Código"]),
        key=k, hide_index=True, use_container_width=True, height=_ALTO_TABLA_RS,
        disabled=["Código", "Insumo", "Subtotal (S/)"],
        on_change=_al_editar_rs, args=(modo, cod, k),
        column_config={
            "Quitar": st.column_config.CheckboxColumn("✕", width=30, help="Marcar para quitar"),
            "Código": st.column_config.TextColumn("Cód.", width=58),
            "Insumo": st.column_config.TextColumn("Insumo", width=104),
            "Unidad": st.column_config.TextColumn("Und.", width=56),
            "Cantidad": st.column_config.NumberColumn("Cant.", width=48, min_value=0.0),
            "Precio unit. (S/)": st.column_config.NumberColumn(
                "P. unit.", width=56, min_value=0.0, help="Precio unitario (S/)"),
            "Subtotal (S/)": st.column_config.NumberColumn("Subt.", width=52, format="%.2f"),
        })
    return {i for i, v in enumerate(editado["Quitar"].tolist()) if v}


# ── Dónde se usa ──
def _texto_usos(filas):
    """«8 platos (5 directos, 3 por recetas base) · 5 recetas base»."""
    pl = [f for f in filas if f["clase"] == "Plato"]
    rb = [f for f in filas if f["clase"] != "Plato"]
    partes = []
    for grupo, uno, varios in ((pl, "plato", "platos"), (rb, "receta base", "recetas base")):
        if not grupo:
            continue
        ind = sum(1 for f in grupo if f["via"])
        txt = f"{len(grupo)} {uno if len(grupo) == 1 else varios}"
        if ind:
            txt += f" ({len(grupo) - ind} directo{'s' if len(grupo) - ind != 1 else ''}, {ind} por otra receta)"
        partes.append(txt)
    return " · ".join(partes)


def _estilo_pct_uso(v):
    if not isinstance(v, str) or not v.endswith("%"):
        return f"color: {GRIS_TEXTO}"
    pct = float(v.rstrip(" %"))
    color, _ = _estado_costo(pct)
    return f"color: {color}; font-weight: 600"


def _panel_usos(modo, lineas):
    """En qué recetas ACTIVAS se usa cada artículo de esta receta, directo o
    por una receta base (decisión del usuario, 2026-10-03: también los
    indirectos). La tabla principal dice cuántas; acá, cuáles: una celda
    del `data_editor` no puede abrir nada al clic."""
    if not lineas:
        st.markdown(_html_vacio(
            "Agrega artículos a la receta: acá verás en qué otras recetas activas "
            "se usa cada uno.", _ALTO_PANEL - 10), unsafe_allow_html=True)
        return
    por_cod = {l["cod"]: l for l in lineas}
    cods = list(por_cod)
    k = _key(modo, "uso_sel")
    if st.session_state.get(k) not in cods:
        st.session_state[k] = next(
            (c for c in cods if por_cod[c].get("tipo") != "nuevo"), cods[0])

    def rotulo(c):
        l = por_cod[c]
        if l.get("tipo") == "nuevo":
            return f"{l['nombre']} · nuevo"
        return f"{l['nombre']} · {an.resumen_usos(_usos(c))}"

    cod = st.selectbox("Artículo", cods, format_func=rotulo, key=k,
                       label_visibility="collapsed")
    linea = por_cod[cod]
    if linea.get("tipo") == "nuevo":
        m = _modelo(modo, linea)
        k_ent = _kardex().get(m.get("sale_de") or "") if m["clase"] == "p" else None
        if not k_ent:
            st.markdown(_html_vacio("Es nuevo: ninguna receta lo usa todavía.",
                                    _ALTO_TABLA_USOS + _ALTO_NOTA_USOS),
                        unsafe_allow_html=True)
            return
        st.markdown(f'<div class="fr-nota fr-nota-2">Es nuevo: ninguna receta lo usa '
                    f'todavía. Los otros cortes de {html.escape(k_ent[0])} '
                    f'({an.VENTANA_DIAS} días) se usan en:</div>', unsafe_allow_html=True)
        cortes = _historia_porcionado(m["sale_de"])["cortes"]
        filas = []
        for c, n in zip(cortes["cod"], cortes["nombre"]):
            u = _usos(c)
            nombres = ", ".join(f["receta"] for f in u[:6]) + ("…" if len(u) > 6 else "")
            filas.append({"Corte": n, "Se usa en": f"{an.resumen_usos(u)}: {nombres}" if u
                          else "sin usos"})
        st.dataframe(pd.DataFrame(filas, columns=["Corte", "Se usa en"]), hide_index=True,
                     use_container_width=True, height=_ALTO_TABLA_USOS,
                     key=_key(modo, "usos_hermanos"),
                     column_config={"Corte": st.column_config.TextColumn("Corte", width=170)})
        return
    filas = _usos(cod)
    if not filas:
        st.markdown(_html_vacio("Ninguna receta activa lo usa, ni directo ni por "
                                "una receta base.", _ALTO_TABLA_USOS + _ALTO_NOTA_USOS),
                    unsafe_allow_html=True)
        return
    st.markdown(f'<div class="fr-nota fr-nota-2">{html.escape(_texto_usos(filas))}</div>',
                unsafe_allow_html=True)
    tabla = pd.DataFrame({
        "Receta": [f["receta"] for f in filas],
        "Es": ["plato" if f["clase"] == "Plato" else "base" for f in filas],
        "Lleva": [f["cant"] for f in filas],
        "Vía": [f["via"] or "directo" for f in filas],
        "% costo": ["—" if f["pct"] is None else
                    ("en combo" if f["pv"] <= 1 else f"{f['pct']:.1f} %") for f in filas],
    })
    st.dataframe(
        tabla.style.map(_estilo_pct_uso, subset=["% costo"]),
        hide_index=True, use_container_width=True, height=_ALTO_TABLA_USOS,
        key=_key(modo, "usos_tabla"),
        column_config={
            "Receta": st.column_config.TextColumn("Receta", width=140),
            "Es": st.column_config.TextColumn("Es", width=40),
            "Lleva": st.column_config.TextColumn(
                "Lleva", width=56, help="Cuánto lleva del artículo, o de la receta base por la que le llega"),
            "Vía": st.column_config.TextColumn(
                "Vía", width=100, help="«directo», o la receta base por la que le llega"),
            "% costo": st.column_config.TextColumn(
                "% costo", width=62, help="% de costo del plato en el sistema, sobre el neto"),
        })


# ── La tarjeta de la derecha ──
def _opciones_panel(modo, lineas):
    ops = ["precio"] + ([] if modo == "combo" else ["usos"])
    nuevos = _nuevos(modo)
    for l in lineas:
        m = nuevos.get(l["cod"]) if l.get("tipo") == "nuevo" else None
        if m and m["clase"] in ("p", "rs") and l["cod"] not in ops:
            ops.append(l["cod"])
    if st.session_state.get(_key(modo, "creando")):
        ops.append("crear")
    return ops


def _al_elegir_panel(modo):
    v = st.session_state.get(_key(modo, "panel_w"))
    if v is not None:
        st.session_state[_key(modo, "panel")] = v


def _pestanas(modo, lineas):
    """Cabecera de la tarjeta de la derecha y la fila de pestañas: Precio ·
    Dónde se usa · una por cada (P)/(Rs) nuevo · «Nuevo: …» mientras se
    crea uno. Devuelve la elegida.

    La elección vive en `panel` y el widget se SIEMBRA con ella en cada
    corrida: así una pestaña se puede abrir desde Python (crear una (Rs)
    abre la suya) y un clic sobre la ya elegida, que en `st.pills` la
    suelta, no deja el panel sin nada."""
    ops = _opciones_panel(modo, lineas)
    k, kw = _key(modo, "panel"), _key(modo, "panel_w")
    sel = st.session_state.get(k)
    if sel not in ops:
        sel = "precio"
    st.session_state[k] = sel
    st.session_state[kw] = sel
    nuevos = _nuevos(modo)
    ver = st.session_state.get(_key(modo, "creando"))
    creando = st.session_state.get(_key(modo, f"crear_nombre_v{ver}")) or "…"

    def rotulo(o):
        if o == "precio":
            return "Precio"
        if o == "usos":
            return "Dónde se usa"
        if o == "crear":
            return f"Nuevo: {_corto(creando, 16)}"
        m = nuevos[o]
        return _corto(m["nombre"], 14) + (" · falta" if _falta_detalle(m) else "")

    if sel == "precio":
        titulo = "Precio de venta"
        sub = (f"IGV {_tasa(tasa_igv())} · recargo al consumo {_tasa(_RECARGO)}, "
               "sobre el neto")
    elif sel == "usos":
        titulo, sub = "Dónde se usa", "recetas activas, directo o por recetas base"
    elif sel == "crear":
        titulo, sub = "Artículo nuevo", "no está en el almacén"
    else:
        titulo = "Porcionado nuevo" if nuevos[sel]["clase"] == "p" else "Receta base nueva"
        sub = "viaja con la propuesta guardada"
    st.markdown(
        f'<div class="fr-cab"><span class="fr-titulo">{titulo}</span>'
        f'<span class="fr-sub">{html.escape(sub)}</span></div>', unsafe_allow_html=True)
    st.pills("Qué mostrar", ops, selection_mode="single", format_func=rotulo, key=kw,
             on_change=_al_elegir_panel, args=(modo,), label_visibility="collapsed")
    return sel


def _panel_derecho(modo, lineas, origen):
    sel = _pestanas(modo, lineas)
    nuevos = _nuevos(modo)
    if sel == "usos":
        _panel_usos(modo, lineas)
    elif sel == "crear":
        _panel_crear(modo)
    elif sel in nuevos:
        (_panel_p if nuevos[sel]["clase"] == "p" else _panel_rs)(modo, sel)
    else:
        _panel_precio(modo, _total_lineas(lineas), origen,
                      aviso=_aviso_pendientes(modo, lineas))


# ─── Las dos tarjetas ────────────────────────────────────────────────────
_TIPO_GUARDADO = {"venta": "Receta de Venta", "combo": "Combo",
                  "modificar": "Modificación de receta"}


def _render_armado(modo, card_izq, card_der):
    """Receta de venta, Combo y Modificar: la tarjeta «Receta» a la
    izquierda (buscadores, insumos, guardar y enviar) y «Precio de venta»
    a la derecha. Los tres comparten todo; lo que cambia es el catálogo
    del buscador y, en Modificar, la fila de importar."""
    es_combo = modo == "combo"
    if es_combo and _catalogo_productos_venta_cacheado() is None:
        with card_izq:
            st.error(
                f"No se pudo armar el catálogo de productos de venta desde "
                f"{_ARCHIVO_RECETAVENTA} (¿faltan columnas, o no hay platos activos?).")
        return
    if not es_combo and _catalogo_insumos_cacheado() is None:
        with card_izq:
            st.error(
                f"No se pudo leer {_ARCHIVO_INVENTARIO} o le faltan columnas clave "
                "(Código Producto / Nombre Producto / Precio Promedio).")
        return

    with card_izq:
        origen = _importador() if modo == "modificar" else None
        # Precio y unidad de lo nuevo, desde su detalle, ANTES de la tabla.
        _sincronizar_nuevos(modo)

        # Nombre · buscador · «+» en UNA fila (mockup del 2026-09-24).
        # columnas-internas: el nombre al ancho de un nombre de plato, el
        # buscador con lo que queda y el «+» al de su glifo.
        c_nom, c_bus, c_mas = st.columns([2.2, 4.2, 0.55], vertical_alignment="top")
        with c_nom:
            nombre = st.text_input(
                "Nombre", key=_key(modo, "nombre"),
                placeholder="nombre del combo…" if es_combo else "nombre de la receta…",
                label_visibility="collapsed",
            )
        _buscador_catalogo(
            modo, "productos_venta" if es_combo else "insumos", c_bus, c_mas,
            placeholder=("Buscar producto de venta (plato)… o escribe uno nuevo"
                         if es_combo else
                         "Buscar artículo del almacén… o escribe uno nuevo"),
        )

        lineas, marcadas = _tabla_lineas(modo, origen)
        _botonera_tabla(modo, lineas, marcadas, origen)

        # El precio vive en la otra tarjeta, que se dibuja DESPUÉS: acá se
        # lee de la key de su `number_input`, que ya trae lo de esta corrida.
        precio_venta = float(st.session_state.get(_key(modo, "pv")) or 0.0)
        tipo = _TIPO_GUARDADO[modo]
        with st.container(key="form_receta_pie"):
            # columnas-internas: Guardar y los tres de envío comparten la
            # fila del pie de la tarjeta; el nombre de quien guarda es lo
            # más ancho.
            c_guarda, c_boton, c_pdf, c_xls, c_mail = st.columns(
                [2.1, 2.1, 1, 1.1, 2.3], vertical_alignment="center")
            with c_guarda:
                guardado_por = st.text_input(
                    "Guardado por (tu nombre)", key=_key(modo, "guardado_por"),
                    placeholder="tu nombre…", label_visibility="collapsed",
                )
            with c_boton:
                guardar = st.button(
                    "💾 Guardar propuesta", type="primary",
                    key=_key(modo, "guardar"), use_container_width=True,
                )
            nuevos = _detalle_nuevos(modo, lineas)
            _botones_envio(modo, (c_pdf, c_xls, c_mail), tipo, nombre,
                           guardado_por, lineas, precio_venta, nuevos)
        if guardar:
            que = "el combo" if es_combo else "la receta"
            if not nombre.strip():
                st.warning(f"Ponle un nombre a {que}.")
            elif not guardado_por.strip():
                st.warning("Dinos quién la guarda (campo «tu nombre»).")
            elif not lineas:
                st.warning("Agrega al menos un ítem.")
            else:
                extra = {"precio_venta": precio_venta}
                if nuevos:
                    extra["articulos_nuevos"] = nuevos
                if origen:
                    extra.update({
                        "plato_sistema": origen["cod"],
                        "precio_venta_sistema": origen["pv"],
                        "costo_sistema": round(origen["costo"], 4),
                    })
                if _guardar_propuesta(tipo, nombre.strip(), guardado_por.strip(),
                                      lineas, extra=extra):
                    st.success(f"«{nombre}» se guardó como propuesta.")
                    _limpiar_modo(modo)

    with card_der:
        _panel_derecho(modo, lineas, origen)


# ─── Guardadas (visor de solo lectura) ──────────────────────────────────
_PREFIJO_PROPUESTAS = "_recetas_propuestas/"


@st.cache_data(ttl=60, show_spinner="Cargando propuestas guardadas…")
def _listar_propuestas_guardadas():
    """Lee todos los JSON de _recetas_propuestas/ en R2. Un JSON individual
    corrupto/parcial se salta (no tira abajo la lista entera) — puede pasar
    si alguien mira la carpeta mientras otra persona está guardando."""
    if not secrets_disponibles():
        return []
    try:
        s3 = get_s3_cliente()
        bucket = st.secrets["R2_BUCKET"]
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=_PREFIJO_PROPUESTAS)
    except Exception as e:
        st.error(f"No se pudo listar las propuestas guardadas: {e}")
        return []

    propuestas = []
    for obj in resp.get("Contents", []):
        clave = obj["Key"]
        if not clave.endswith(".json"):
            continue
        try:
            body = s3.get_object(Bucket=bucket, Key=clave)["Body"].read()
            data = json.loads(body)
            data["_clave"] = clave
            propuestas.append(data)
        except Exception:
            continue
    propuestas.sort(key=lambda p: p.get("guardado_en", ""), reverse=True)
    return propuestas


def _render_guardadas():
    if not secrets_disponibles():
        st.info("🧪 Modo demo: no hay R2 configurado, no hay nada para listar acá.")
        return

    if st.button("🔄 Actualizar lista", key="form_receta_guardadas_refresh"):
        _listar_propuestas_guardadas.clear()
        st.rerun(scope="fragment")

    propuestas = _listar_propuestas_guardadas()
    if not propuestas:
        st.info("Todavía no hay ninguna propuesta guardada.")
        return

    st.caption(f"{len(propuestas)} propuesta(s) guardada(s) — más nueva primero.")
    for p in propuestas:
        total = p.get("total", 0)
        titulo = f"{p.get('tipo', '?')} · {p.get('nombre', '(sin nombre)')} · {_fmt(total)}"
        with st.expander(titulo):
            fecha = p.get("guardado_en", "")
            st.caption(f"Guardado por **{p.get('guardado_por', '?')}** · {fecha}")

            extra_bits = []
            if p.get("porciones"):
                extra_bits.append(f"{p['porciones']} porciones")
            if p.get("precio_venta"):
                extra_bits.append(f"precio de venta {_fmt(p['precio_venta'])}")
            if extra_bits:
                st.caption(" · ".join(extra_bits))

            lineas = p.get("lineas") or []
            if not lineas:
                st.caption("(sin líneas)")
                continue
            df = pd.DataFrame(lineas)
            df["Subtotal (S/)"] = (df["cantidad"] * df["precio"]).round(2)
            df = df.rename(columns={
                "cod": "Código", "nombre": "Producto", "unidad": "Unidad",
                "cantidad": "Cantidad", "precio": "Precio unit. (S/)",
            })
            st.dataframe(
                df[["Código", "Producto", "Unidad", "Cantidad", "Precio unit. (S/)", "Subtotal (S/)"]],
                hide_index=True, use_container_width=True,
            )
            nuevos = p.get("articulos_nuevos") or []
            if nuevos:
                st.markdown("**Artículos nuevos**")
                for d in nuevos:
                    st.caption("• " + an.describir(d))


# ─── Punto de entrada público ───────────────────────────────────────────────
@una_vez_por_corrida
@st.fragment
def _fragment_nueva_receta():
    """El formulario entero vive dentro de un `@st.fragment` desde el
    2026-09-23. Sin él, cada clic del «+» del buscador dispara un
    `st.rerun()` sin scope → re-ejecuta `app.py` + `graficos/recetas.py`
    entero (rail de 10 secciones + carga de `recetabase.parquet` +
    iteración del catálogo) y el usuario ve un botón trabado durante
    casi un minuto en Cloud (reportado con captura). Todos los
    `st.rerun()` internos usan `scope="fragment"` explícito (el default
    de Streamlit sigue siendo `"app"`).

    Va `@una_vez_por_corrida` encima porque este fragment se llama
    ADENTRO del fragment de `seccion_perezosa` — mismo criterio que las
    tarjetas de Compras (regla #456)."""
    _init_estado()

    # Dos tarjetas desde el 2026-09-24 (mockup aprobado ese día): «Receta»
    # a la izquierda y «Precio de venta» a la derecha, las dos a la altura
    # de la pantalla. El modo se lee ANTES de dibujar su control porque
    # decide si hay una tarjeta o dos: «Guardadas» es una lista a todo el
    # ancho. El segmented_control puede quedar sin nada elegido (un clic
    # sobre el activo lo suelta): eso cuenta como «Receta de venta».
    rotulo = st.session_state.get("form_receta_modo") or "Receta de venta"
    modo = _MODO_DE_ROTULO.get(rotulo)
    if modo is None:
        with st.container(key="form_receta_card_receta"):
            _cabecera("Propuestas guardadas")
            _render_guardadas()
        return

    c_izq, c_der = st.columns([1.6, 1], gap="medium")
    with c_izq:
        card_izq = st.container(key="form_receta_card_receta")
    with c_der:
        card_der = st.container(key="form_receta_card_precio")
    with card_izq:
        _cabecera("Receta")
    _render_armado(modo, card_izq, card_der)


def _cabecera(titulo):
    """Título de la tarjeta izquierda y, a su derecha, qué se va a hacer:
    Receta de venta · Combo · Modificar · Guardadas."""
    # columnas-internas: el título a su ancho y el control a la derecha.
    c_tit, c_tipo = st.columns([1, 2.6], vertical_alignment="center")
    with c_tit:
        st.markdown(f'<div class="fr-titulo">{html.escape(titulo)}</div>',
                    unsafe_allow_html=True)
    with c_tipo:
        st.segmented_control(
            "Tipo", ["Receta de venta", "Combo", "Modificar", "Guardadas"],
            default="Receta de venta", key="form_receta_modo",
            label_visibility="collapsed",
        )


def render_formulario_receta():
    """Entrada del formulario, tal como lo consume `graficos/recetas.py` desde
    su sección "Nueva receta". Sin `st.subheader` propio: el título de la
    sección ya lo pone el rail — un h2 acá sumaba unos 60px y sacaba al
    buscador de la primera pantalla en una laptop (pedido 2026-09-22).
    El `rec_card_nueva` del dispatcher ya no pinta tarjeta (es transparente
    desde el 2026-09-24): las dos tarjetas las pone este módulo.

    Es una envoltura fina sobre `_fragment_nueva_receta` — el fragment
    absorbe los reruns del buscador para que el "+" responda en el
    orden de 100 ms en vez de re-ejecutar el reporte entero."""
    _fragment_nueva_receta()
