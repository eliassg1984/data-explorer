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

Afuera de este commit a propósito (quedan para commits siguientes):
  - Crear/editar una Receta Base desde acá.
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
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import envio_receta

from data import cargar as _cargar_reporte
from data import get_s3_cliente, secrets_disponibles
from graficos import alturas
from graficos.base import _resolver, una_vez_por_corrida
from tema import (
    ACENTO, ADVERTENCIA, ERROR, EXITO, GRIS_TEXTO, GRIS_TEXTO_SUAVE,
    PALETA_SERIES, TEXTO_PRINCIPAL,
)
# El catálogo de insumos y el nombre de SU parquet viajan juntos, y viven
# allá desde el 2026-09-17 — ver el comentario de `_catalogo_insumos_
# cacheado` más abajo.
from graficos.recetas_comun import (
    ARCHIVO_INVENTARIO as _ARCHIVO_INVENTARIO,
    _activo, catalogo_insumos,
)

_ARCHIVO_RECETAVENTA = "recetaventa.parquet"
_ZONA_LIMA = ZoneInfo("America/Lima")   # Cloud corre en UTC
_IGV = 0.18       # 18 %
_RECARGO = 0.10   # 10 % servicio, convención de restaurantes en Perú
_UMBRAL_COSTO_OK = 30
_UMBRAL_COSTO_WARN = 35

_MODOS = ("venta", "combo", "modificar")
# Rótulo del segmented control → modo interno. «Guardadas» no arma nada.
_MODO_DE_ROTULO = {"Receta de venta": "venta", "Combo": "combo",
                   "Modificar": "modificar"}

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
_CROMO_TARJETA_RECETA = 245
_FILAS_MODIFICAR = 83
_CROMO_TARJETA_PRECIO = 412
_ALTO_TABLA = alturas.PRESUPUESTO - _CROMO_TARJETA_RECETA
_ALTO_TORTA = alturas.PRESUPUESTO - _CROMO_TARJETA_PRECIO


def _alto_tabla(modo):
    return _ALTO_TABLA - (_FILAS_MODIFICAR if modo == "modificar" else 0)


def _fmt(v):
    return f"S/ {v:,.2f}"


def _key(modo, sufijo):
    return f"form_receta_{modo}_{sufijo}"


def _key_lineas(modo):
    return _key(modo, "lineas")


def _init_estado():
    for modo in _MODOS:
        st.session_state.setdefault(_key_lineas(modo), [])
        # El precio de venta es un `st.number_input` con esta key: vacío
        # (None) hasta que alguien escribe uno o se importa un plato.
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


def _agregar_linea(modo, cod, nombre, unidad, precio, activo, tipo):
    lineas = st.session_state[_key_lineas(modo)]
    if any(l["cod"] == cod for l in lineas):
        return
    lineas.append({
        "cod": cod, "nombre": nombre, "unidad": unidad or "unidad",
        "precio": float(precio), "cantidad": 1.0, "activo": activo, "tipo": tipo,
    })


_SENTINEL_NUEVO = "➕  Agregar un ítem nuevo (no está en la lista)…"


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
    d["precio_fmt"] = d["precio_num"].map(lambda p: f"S/ {p:,.2f}")
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


def _buscador_catalogo(modo, kind, c_main, c_btn, *, placeholder,
                       unidad_nueva="unidad"):
    """Buscador SUGESTIVO unificado con el alta de ítem nuevo.

    `kind` es el nombre del catálogo (`"insumos"` o `"productos_venta"`)
    para `_opciones_precomputadas`, que ya trae la lista y el meta en un
    formato listo para el selectbox — pre-2026-09-23 iteraba con
    `df.iterrows()` en cada rerun y era el bottleneck del "+".

    Una sola fila: `st.selectbox` con los ítems del catálogo MÁS la opción
    centinela `_SENTINEL_NUEVO` al final. El widget filtra client-side a
    medida que el usuario tipea (sin Enter). El botón «+» al costado
    confirma la línea.

    Dos modos, alternados por session_state[`modo_nuevo`]:
      · **buscar** (default): selectbox de opciones + «+». Elegir la
        opción centinela lleva a buscar → nuevo.
      · **nuevo**: mismo lugar, pero un `st.text_input` para el nombre
        del ítem que no está + «+». Un enlace «← volver a buscar» debajo
        vuelve a buscar.

    Reemplaza al esquema anterior (`st.expander` aparte con su propio
    input) del pedido de 2026-09-23: «"¿No está en la lista?" debe ser
    una funcionalidad del buscador de artículos de almacén de arriba, no
    un cuadrante aparte. Al escribir un producto nuevo, debe consultarte
    si lo creamos como un artículo nuevo». `st.selectbox` no expone al
    Python el texto tipeado en el filtro (el filtrado es puro
    client-side), así que la señal «acá no hay nada» la da el usuario
    eligiendo la opción centinela desde el mismo dropdown.

    La key del widget lleva un contador incremental por modo, para que
    después de cada agregado el widget arranque limpio (Streamlit descarta
    el estado de la key vieja). Sin eso, la última opción marcada queda
    "pegada" y no se puede volver a elegir. Historia completa en
    `arquitectura.md` regla #497."""
    contador_key = _key(modo, "buscador_ver")
    st.session_state.setdefault(contador_key, 0)
    ver = st.session_state[contador_key]

    modo_nuevo_key = _key(modo, "modo_nuevo")
    modo_nuevo = st.session_state.get(modo_nuevo_key, False)

    lineas_actuales = {l["cod"] for l in st.session_state[_key_lineas(modo)]}
    todas_opciones, meta_total, cod_por_etiq = _opciones_precomputadas(kind)
    if not todas_opciones:
        # Catálogo vacío o no disponible: nada que ofrecer.
        opciones = []
        meta = {}
    else:
        # Filtrado O(N) sobre listas Python: sin `df.iterrows()` en la ruta caliente.
        opciones = [op for op in todas_opciones if cod_por_etiq[op] not in lineas_actuales]
        meta = meta_total  # el meta completo alcanza; sólo iteramos las opciones filtradas

    # Las dos columnas las abre el llamador, en la MISMA fila que el nombre
    # de la receta (mockup del 2026-09-24): nombre · buscador · «+».
    if modo_nuevo:
        with c_main:
            nuevo_nombre = st.text_input(
                "Nombre del nuevo ítem",
                key=_key(modo, f"nuevo_nombre_v{ver}"),
                placeholder="nombre del ítem nuevo (no está en el almacén)…",
                label_visibility="collapsed",
            ).strip()
        with c_btn:
            agregar_n = st.button(
                "➕", key=_key(modo, "add_nuevo"),
                disabled=not nuevo_nombre, use_container_width=True,
                help="Confirmar como ítem nuevo (precio 0, se completa después)",
            )
        with c_main:
            if st.button("← Volver a buscar", key=_key(modo, "cancel_nuevo"),
                         type="tertiary" if hasattr(st, "tertiary") else "secondary"):
                st.session_state[modo_nuevo_key] = False
                st.session_state[contador_key] = ver + 1
                st.rerun(scope="fragment")
        if agregar_n and nuevo_nombre:
            st.session_state["form_receta_contador_nuevo"] += 1
            n = st.session_state["form_receta_contador_nuevo"]
            _agregar_linea(modo, f"NUEVO-{n}", nuevo_nombre, unidad_nueva, 0.0, None, "nuevo")
            st.session_state[modo_nuevo_key] = False
            st.session_state[contador_key] = ver + 1
            st.rerun(scope="fragment")
        return

    opciones_completas = opciones + [_SENTINEL_NUEVO]
    with c_main:
        elegido = st.selectbox(
            "Buscar", opciones_completas, index=None, placeholder=placeholder,
            key=_key(modo, f"buscador_v{ver}"),
            label_visibility="collapsed",
        )
    with c_btn:
        agregar = st.button(
            "➕", key=_key(modo, "add_sel"),
            disabled=elegido is None or elegido == _SENTINEL_NUEVO,
            use_container_width=True,
            help="Agregar el ítem seleccionado a la lista",
        )
    if elegido == _SENTINEL_NUEVO:
        # Cambia de modo: en el próximo render aparece el input de nombre
        # en el mismo lugar del buscador.
        st.session_state[modo_nuevo_key] = True
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
        o = orig.get(l["cod"])
        if o is None:
            n += 1
        elif abs(l["cantidad"] - o[0]) > 1e-9 or abs(l["precio"] - o[1]) > 1e-9:
            n += 1
    presentes = {l["cod"] for l in lineas}
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
    las filas donde se cambió."""
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
    filas = []
    for l in lineas:
        subtotal = l["cantidad"] * l["precio"]
        pct = (subtotal / total * 100) if total > 0 else 0.0
        badges = []
        if l["tipo"] == "nuevo":
            badges.append("🆕 Nuevo")
        elif origen and l["cod"] not in orig:
            badges.append("agregado")
        if l.get("activo") is False:
            badges.append("🔸 Inactivo")
        nombre_mostrado = l["nombre"] + (f"  ({', '.join(badges)})" if badges else "")
        fila = {
            "Quitar": False,
            "Código": l["cod"],
            "Producto": nombre_mostrado,
            "Unidad": l["unidad"],
        }
        if origen:
            o = orig.get(l["cod"])
            cambio = o is not None and abs(l["cantidad"] - o[0]) > 1e-9
            fila["Antes"] = _tachado(_num(o[0])) if cambio else ""
        # Se MUESTRAN redondeados a 4 decimales; al leer de vuelta sólo
        # cuenta como edición lo que difiere de lo mostrado (ver abajo).
        fila["Cantidad"] = round(l["cantidad"], 4)
        fila["Precio unit. (S/)"] = round(l["precio"], 4)
        fila["Subtotal (S/)"] = round(subtotal, 2)
        fila["% del total"] = round(pct, 1)
        filas.append(fila)
    df_show = pd.DataFrame(filas)
    datos = df_show
    if origen:
        # El Styler sólo pinta columnas NO editables: alcanza para «Antes».
        datos = df_show.style.set_properties(
            subset=["Antes"], **{"color": GRIS_TEXTO_SUAVE})

    editor_key = _key(modo, "editor")
    editado = st.data_editor(
        datos,
        key=editor_key,
        hide_index=True,
        use_container_width=True,
        height=_alto_tabla(modo),
        disabled=["Código", "Producto", "Antes", "Subtotal (S/)", "% del total"],
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
            "Código": st.column_config.TextColumn("Cód.", width=64),
            "Producto": st.column_config.TextColumn("Producto", width=190),
            "Unidad": st.column_config.TextColumn(
                "Und.", width=62, help="Unidad"),
            "Antes": st.column_config.TextColumn(
                "Antes", width=52,
                help="Cantidad que tiene hoy el sistema, si la cambiaste"),
            "Cantidad": st.column_config.NumberColumn(
                "Cant.", width=64, help="Cantidad", min_value=0.0),
            "Precio unit. (S/)": st.column_config.NumberColumn(
                "P. unit.", width=72, help="Precio unitario (S/)",
                min_value=0.0),
            "Subtotal (S/)": st.column_config.NumberColumn(
                "Subtot.", width=66, help="Subtotal (S/)", format="%.2f"),
            "% del total": st.column_config.NumberColumn(
                "%", width=46, help="% del costo total", format="%.1f"),
        },
    )

    for i, l in enumerate(lineas):
        fila = editado.iloc[i]
        # Lo mostrado está redondeado: pisar el valor guardado con lo que
        # volvió del editor, sin más, le cambiaría el costo a toda línea
        # de más de 4 decimales al primer clic en cualquier celda.
        for campo, col in (("cantidad", "Cantidad"), ("precio", "Precio unit. (S/)")):
            v = float(fila[col]) if pd.notna(fila[col]) else 0.0
            if abs(v - df_show.iloc[i][col]) > 1e-9:
                l[campo] = v
        l["unidad"] = str(fila["Unidad"]) or "unidad"

    marcadas = {i for i, v in enumerate(editado["Quitar"].tolist()) if v}
    return lineas, marcadas


def _desglose(pv):
    """(precio neto, monto de recargo, monto de IGV) del precio de venta
    `pv`. UNA sola copia de la fórmula: la usan el panel de precios y el
    envío por correo (`_resumen_envio`), y dos copias divergen."""
    if pv <= 0:
        return 0.0, 0.0, 0.0
    base = pv / ((1 + _RECARGO) * (1 + _IGV))
    m_recargo = base * _RECARGO
    return base, m_recargo, (base + m_recargo) * _IGV


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
        if origen["dup"]:
            dup = ", ".join(origen["dup"])
            nota += (f" {dup} {'venía' if len(origen['dup']) == 1 else 'venían'}"
                     " en dos líneas; al importar se juntaron en una.")
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
        st.session_state.pop(_key(modo, "plato_sel"), None)


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


def _panel_precio(modo, costo, origen=None):
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
    k_pv = _key(modo, "pv")
    pv = float(st.session_state.get(k_pv) or 0.0)
    N = _cuentas(costo, pv)
    A = _cuentas(origen["costo"], origen["pv"]) if origen else None
    hay_n = pv > 0

    st.markdown(
        '<div class="fr-cab"><span class="fr-titulo">Precio de venta</span>'
        f'<span class="fr-sub">IGV {_IGV*100:.0f} % · recargo al consumo '
        f'{_RECARGO*100:.0f} %</span></div>', unsafe_allow_html=True)

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
                    "Precio de venta", key=k_pv, min_value=0.0, step=0.5,
                    format="%.2f", placeholder="0.00",
                    label_visibility="collapsed",
                    help="Precio de carta, con IGV y recargo incluidos",
                )

        filas = [
            ("Precio neto (base)", "transparent", "base", False),
            ("Utilidad (neto − costo)", _COLOR_UTIL, "util", True),
            (f"Recargo al consumo ({_RECARGO*100:.0f} %)", _COLOR_RECARGO, "recargo", False),
            (f"IGV ({_IGV*100:.0f} %)", _COLOR_IGV, "igv", False),
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
    st.markdown(
        f'<div class="fr-semaforo">% de costo sobre el neto: {semaforo}</div>'
        f'<div class="fr-pista">✎ {pista}</div>', unsafe_allow_html=True)

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
        (f"Recargo {_RECARGO*100:.0f} %", T["recargo"], _COLOR_RECARGO),
        (f"IGV {_IGV*100:.0f} %", T["igv"], _COLOR_IGV),
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


def _resumen_envio(tipo, nombre, autor, lineas, precio_venta):
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
        "pct_recargo": _RECARGO * 100, "pct_igv": _IGV * 100,
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


def _botones_envio(modo, cols, tipo, nombre, guardado_por, lineas, precio_venta):
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
                             lineas, precio_venta)
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
    st.session_state.pop(_key(modo, "origen"), None)
    st.session_state.pop(_key(modo, "plato_sel"), None)


# ─── Modificar: importar una receta del sistema ─────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _platos_sistema():
    """{COD PLATO: plato} de los platos ACTIVOS de recetaventa.parquet, con
    su receta lista para cargar en la tabla.

    Cada plato trae nombre, subgrupo, precio de salón (`P.VENTA SALON`),
    costo y sus líneas `{COD INS: (cantidad, precio unit.)}` en la unidad
    de COSTEO del sistema (`UNID COSTO`, casi siempre gramos, con
    `P.UNIT COSTO` por gramo) — no en la unidad de kardex del buscador:
    es la que tiene la receta, y convertirla sería inventar un factor.

    Sólo insumos activos, mismo criterio que el catálogo de Combo. Y un
    insumo que el sistema trae en DOS líneas (Lomo a la Pimienta: Sal
    Maldon ×2, 2026-09-24) se junta en una, sumando la cantidad: el costo
    no cambia y la tabla no repite el código — que además es la clave con
    la que se compara cada línea contra el sistema."""
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
        veces = g["_ins"].value_counts()
        lineas = (g.groupby("_ins", sort=False)
                  .agg(nombre=(c_ins_nom, "first"),
                       unidad=("_und", "first"),
                       cant=("_cant", "sum"), pu=("_pu", "first"))
                  .reset_index())
        lineas["sub"] = lineas["cant"] * lineas["pu"]
        lineas = lineas.sort_values("sub", ascending=False)
        platos[cod] = {
            "cod": cod,
            "nombre": str(g[c_nom].iloc[0]).strip(),
            "subgrupo": str(g[c_sub].iloc[0]) if c_sub else "",
            "pv": float(g["_pv"].iloc[0]),
            "costo": float(lineas["sub"].sum()),
            "lineas": [
                {"cod": r["_ins"], "nombre": str(r["nombre"]),
                 "unidad": str(r["unidad"]).strip().lower() or "unidad",
                 "cantidad": float(r["cant"]), "precio": float(r["pu"])}
                for _, r in lineas.iterrows()
            ],
            "dup": [str(g.loc[g["_ins"] == c, c_ins_nom].iloc[0])
                    for c in veces[veces > 1].index],
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
        "costo": plato["costo"], "dup": list(plato["dup"]),
        "lineas": {l["cod"]: (l["cantidad"], l["precio"]) for l in plato["lineas"]},
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
            placeholder=("Buscar producto de venta (plato)…" if es_combo
                         else "Buscar artículo del almacén…"),
            unidad_nueva="porción" if es_combo else "unidad",
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
            _botones_envio(modo, (c_pdf, c_xls, c_mail), tipo, nombre,
                           guardado_por, lineas, precio_venta)
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
        _panel_precio(modo, _total_lineas(lineas), origen)


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
