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

Tres modos, un segmented_control propio (interno, no confundir con el chip
Base/Venta/Nueva de arriba, que elige ENTRE reportes):
  - "Receta de venta": insumos de inventariovalorizado.parquet.
  - "Combo": productos de venta = platos de recetaventa.parquet, agrupados
    por Nomb Plato, costo = suma de Total de sus ítems ACTIVOS. Nunca es el
    precio de venta al público — mismo criterio que el resto de la
    herramienta, `precio` es siempre COSTO.
  - "Guardadas": lee de vuelta lo que Guardar escribió en R2 — sin esto,
    "guardar una propuesta para que otra persona la vea" quedaba a medias
    (el archivo existía en R2, pero nadie en el equipo tenía dónde mirarlo
    sin abrir el bucket a mano).

Los dos modos de construcción comparten la misma lógica de línea/tabla/
costeo/guardado (parametrizada por `modo`, mismo espíritu que
graficos/recetas_comun.py con Base/Venta) — evita mantener dos copias del
mismo widget.

Guardar es una PROPUESTA en R2 (_recetas_propuestas/), nunca una escritura
a recetaventa.parquet — mismo principio que solicitar_refresco() en
data.py, que tampoco toca los parquets fuente directamente.

Afuera de este commit a propósito (quedan para commits siguientes):
  - Crear/editar una Receta Base desde acá.
  - Envío por correo (necesita SMTP_USER/SMTP_APP_PASSWORD en secrets).
  - Exportar a Excel/PDF.
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
import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from data import cargar as _cargar_reporte
from data import get_s3_cliente, secrets_disponibles
from graficos.base import _resolver, una_vez_por_corrida
# El catálogo de insumos y el nombre de SU parquet viajan juntos, y viven
# allá desde el 2026-09-17 — ver el comentario de `_catalogo_insumos_
# cacheado` más abajo.
from graficos.recetas_comun import (
    ARCHIVO_INVENTARIO as _ARCHIVO_INVENTARIO,
    _activo, catalogo_insumos,
)

_ARCHIVO_RECETAVENTA = "recetaventa.parquet"
_IGV = 0.18       # 18 %
_RECARGO = 0.10   # 10 % servicio, convención de restaurantes en Perú
_UMBRAL_COSTO_OK = 30
_UMBRAL_COSTO_WARN = 35

_MODOS = ("venta", "combo")


def _fmt(v):
    return f"S/ {v:,.2f}"


def _key(modo, sufijo):
    return f"form_receta_{modo}_{sufijo}"


def _key_lineas(modo):
    return _key(modo, "lineas")


def _init_estado():
    for modo in _MODOS:
        st.session_state.setdefault(_key_lineas(modo), [])
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


def _buscador_catalogo(modo, kind, *, placeholder, unidad_nueva="unidad"):
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

    # Los dos modos comparten el mismo layout: buscador ~40% + «+» ~10%
    # + _pad ~50%, para no comerse el ancho entero de la tarjeta.
    c_main, c_btn, _pad = st.columns([4, 1, 5])

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
        c_hint, _pad2 = st.columns([5, 5])
        with c_hint:
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


def _tabla_lineas(modo):
    """Devuelve las líneas YA sincronizadas con lo que el usuario haya
    editado en el data_editor durante ESTE mismo rerun (no hace falta un
    st.rerun() extra: el propio data_editor ya disparó el rerun que llegó
    hasta acá; el llamador usa el valor devuelto, no una copia vieja).

    Con el listado vacío no se dibuja el `st.info` que había hasta el
    2026-09-23 («Todavía no agregaste ítems…», franja azul a todo el
    ancho): se reportó como «franja fea en azul». La ausencia del data
    editor ya cuenta el estado — el buscador de arriba y el panel de
    precios de la derecha siguen visibles."""
    lineas = st.session_state[_key_lineas(modo)]
    if not lineas:
        return lineas

    total = _total_lineas(lineas)
    filas = []
    for l in lineas:
        subtotal = l["cantidad"] * l["precio"]
        pct = (subtotal / total * 100) if total > 0 else 0.0
        badges = []
        if l["tipo"] == "nuevo":
            badges.append("🆕 Nuevo")
        if l.get("activo") is False:
            badges.append("🔸 Inactivo")
        nombre_mostrado = l["nombre"] + (f"  ({', '.join(badges)})" if badges else "")
        filas.append({
            "Quitar": False,
            "Código": l["cod"],
            "Producto": nombre_mostrado,
            "Unidad": l["unidad"],
            "Cantidad": l["cantidad"],
            "Precio unit. (S/)": l["precio"],
            "Subtotal (S/)": round(subtotal, 2),
            "% del total": round(pct, 1),
        })
    df_show = pd.DataFrame(filas)

    editor_key = _key(modo, "editor")
    editado = st.data_editor(
        df_show,
        key=editor_key,
        hide_index=True,
        use_container_width=True,
        disabled=["Código", "Producto", "Subtotal (S/)", "% del total"],
        # Cabeceras ABREVIADAS y anchos fijos (pedido 2026-09-23: «más
        # angostas las columnas de los insumos»). El data_editor no parte
        # una cabecera en dos renglones, así que se acorta el rótulo y el
        # nombre completo va al `help` (tooltip de la cabecera). Se cambia
        # sólo la ETIQUETA: la columna del df conserva su nombre, que es
        # lo que leen `editado["Cantidad"]` y compañía más abajo. Lo que
        # sobra de ancho lo reparte Streamlit entre todas.
        column_config={
            "Quitar": st.column_config.CheckboxColumn(
                "✕", width=36, help="Marcar para quitar"),
            "Código": st.column_config.TextColumn("Cód.", width=68),
            "Producto": st.column_config.TextColumn("Producto", width=170),
            "Unidad": st.column_config.TextColumn(
                "Und.", width=62, help="Unidad"),
            "Cantidad": st.column_config.NumberColumn(
                "Cant.", width=62, help="Cantidad",
                min_value=0.0, step=0.01, format="%.2f"),
            "Precio unit. (S/)": st.column_config.NumberColumn(
                "P. unit.", width=72, help="Precio unitario (S/)",
                min_value=0.0, step=0.01, format="%.2f"),
            "Subtotal (S/)": st.column_config.NumberColumn(
                "Subtot.", width=72, help="Subtotal (S/)", format="%.2f"),
            "% del total": st.column_config.NumberColumn(
                "%", width=48, help="% del costo total", format="%.1f"),
        },
    )

    for i, l in enumerate(lineas):
        l["cantidad"] = float(editado.iloc[i]["Cantidad"])
        l["precio"] = float(editado.iloc[i]["Precio unit. (S/)"])
        l["unidad"] = str(editado.iloc[i]["Unidad"]) or "unidad"

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Quitar marcadas", key=_key(modo, "quitar")):
            a_quitar = set(editado.index[editado["Quitar"]])
            if a_quitar:
                st.session_state[_key_lineas(modo)] = [l for i, l in enumerate(lineas) if i not in a_quitar]
                st.session_state.pop(editor_key, None)
                st.rerun(scope="fragment")
    with c2:
        if st.button("Vaciar", key=_key(modo, "vaciar")):
            st.session_state[_key_lineas(modo)] = []
            st.session_state.pop(editor_key, None)
            st.rerun(scope="fragment")

    return lineas


def _pricing_panel(modo, costo_total):
    """Panel de precios de la derecha, al COSTADO del ítem-list — pedido
    2026-09-23: «tabla editable al costado, no abajo». Cinco filas:
    Costo total · Precio de venta · Precio neto · Recargo al consumo · IGV.

    De las cinco, sólo **Precio de venta** es el input real del usuario
    (número en soles, con IGV y recargo incluidos, tal como aparece en la
    carta). Las otras cuatro son valores CALCULADOS que se muestran en el
    mismo `st.data_editor` para que la lectura sea de tabla — el usuario
    ve costo total, precio de venta, y su descomposición.

    Fórmula peruana estándar (recargo sobre base, IGV sobre base+recargo):

        Precio de venta = base · (1 + recargo%) · (1 + IGV%)
        Precio neto (base) = Precio de venta / ((1+recargo%) · (1+IGV%))
        Monto recargo = base · recargo%
        Monto IGV = (base + monto_recargo) · IGV%

    con recargo 10 % e IGV 18 % (constantes de módulo).

    **Tabla editable, no editable-de-verdad para todas las filas.**
    `st.data_editor` no soporta editabilidad por celda — sólo por
    columna. Se deja la columna «S/» abierta a la edición para que la
    persona pueda TIPEAR el Precio de venta ahí adentro (más intuitivo
    que un input aparte); si por error edita otra fila, se detecta y se
    revierte bumpeando `pricing_ver` (que es parte de la key del widget)
    → Streamlit descarta el estado del widget viejo y el próximo render
    muestra el valor calculado.

    Devuelve el Precio de venta vigente (para que el llamador lo pase a
    `_guardar_propuesta`)."""
    key_pv = _key(modo, "precio_venta_val")
    key_ver = _key(modo, "pricing_ver")
    st.session_state.setdefault(key_pv, 0.0)
    st.session_state.setdefault(key_ver, 0)
    pv = float(st.session_state[key_pv])
    ver = st.session_state[key_ver]

    if pv > 0:
        base = pv / ((1 + _RECARGO) * (1 + _IGV))
        m_recargo = base * _RECARGO
        m_igv = (base + m_recargo) * _IGV
    else:
        base = m_recargo = m_igv = 0.0

    df = pd.DataFrame([
        {"Concepto": "Costo total",                              "S/": round(costo_total, 2)},
        {"Concepto": "Precio de venta",                          "S/": round(pv, 2)},
        {"Concepto": "Precio neto (base)",                       "S/": round(base, 2)},
        {"Concepto": f"Recargo al consumo ({int(_RECARGO*100)}%)", "S/": round(m_recargo, 2)},
        {"Concepto": f"IGV ({int(_IGV*100)}%)",                    "S/": round(m_igv, 2)},
    ])

    # `row_height` compacta las filas del data_editor — pedido 2026-09-23
    # («hagamos las filas más delgadas»). Streamlit soporta el parámetro
    # desde 1.36 y este proyecto pide `streamlit>=1.39`. Además le pasamos
    # `height` explícito: alto de la cabecera (~35) + 5 filas × 28 + 6 de
    # aire, para que el data_editor NO scrollee interno y muestre las
    # cinco de un vistazo.
    edited = st.data_editor(
        df,
        hide_index=True,
        disabled=["Concepto"],
        column_config={
            "Concepto": st.column_config.TextColumn("Concepto", disabled=True),
            "S/": st.column_config.NumberColumn(
                "S/", format="%.2f", min_value=0.0, step=0.01,
            ),
        },
        key=_key(modo, f"pricing_editor_v{ver}"),
        use_container_width=True,
        row_height=28,
        height=35 + 5 * 28 + 6,
    )

    # Sólo la fila 1 (Precio de venta) es la que persistimos como fuente
    # de verdad. El resto se recalcula.
    nueva_pv = float(edited.iloc[1]["S/"])
    if abs(nueva_pv - pv) > 0.001:
        st.session_state[key_pv] = nueva_pv
        st.session_state[key_ver] = ver + 1
        st.rerun(scope="fragment")

    # Si el usuario edita alguna de las filas calculadas (0, 2, 3, 4), el
    # cambio se descarta bumpeando la key del widget: el próximo render
    # arranca con los valores derivados de `pv`.
    for i in (0, 2, 3, 4):
        if abs(float(edited.iloc[i]["S/"]) - float(df.iloc[i]["S/"])) > 0.001:
            st.session_state[key_ver] = ver + 1
            st.rerun(scope="fragment")

    # Semáforo del % de costo sobre el neto (referencia orientativa, mismo
    # criterio y umbrales que el `_mostrar_pricing` retirado).
    if pv > 0 and base > 0:
        pct = costo_total / base * 100
        if pct <= _UMBRAL_COSTO_OK:
            emoji, texto = "🟢", "muy bueno"
        elif pct <= _UMBRAL_COSTO_WARN:
            emoji, texto = "🟠", "aceptable"
        else:
            emoji, texto = "🔴", "alto"
        st.caption(f"{emoji} % de costo sobre neto: **{pct:.1f}%** ({texto}, orientativo)")
    elif costo_total > 0:
        st.caption("Ingresá un precio de venta para ver la descomposición.")

    return pv


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
    st.session_state.pop(_key(modo, "precio_venta_val"), None)
    # Bumpea la versión del pricing editor para que su widget se resetee.
    st.session_state[_key(modo, "pricing_ver")] = (
        st.session_state.get(_key(modo, "pricing_ver"), 0) + 1
    )


# ─── Receta de venta ─────────────────────────────────────────────────────
def _render_receta_venta(slot_nombre):
    modo = "venta"
    df_cat = _catalogo_insumos_cacheado()
    if df_cat is None:
        st.error(
            f"No se pudo leer {_ARCHIVO_INVENTARIO} o le faltan columnas clave "
            "(Código Producto / Nombre Producto / Precio Promedio)."
        )
        return

    # Fila 1: el nombre va en la MISMA fila que el toggle Receta/Combo/…
    # (`slot_nombre`, lo abre `_fragment_nueva_receta`). El campo
    # «Porciones» se retiró el 2026-09-23 a pedido: el pricing va sobre la
    # RECETA entera, no per-porción.
    with slot_nombre:
        nombre = st.text_input(
            "Nombre de la receta", key=_key(modo, "nombre"),
            placeholder="nombre de la receta…",
            label_visibility="collapsed",
        )

    # Fila 2: buscador del almacén con «+» y sentinel de nuevo (incluye la
    # rama «agregar como nuevo», ya no vive en un expander aparte).
    _buscador_catalogo(
        modo, "insumos",
        placeholder="Buscar artículo del almacén…",
        unidad_nueva="unidad",
    )

    # Fila 3: ítems a la izquierda, panel de precios a la derecha — pedido
    # 2026-09-23: «costo total, precio de venta, precio neto, recargo al
    # consumo, IGV deben estar como una tabla editable al costado, no
    # abajo». Ratio [3, 2] porque el items table tiene 8 columnas y necesita
    # más ancho.
    c_items, c_pricing = st.columns([3, 2])
    with c_items:
        lineas = _tabla_lineas(modo)
    total = _total_lineas(lineas)
    with c_pricing:
        precio_venta = _pricing_panel(modo, total)

    # Fila 4: guardado por + botón (acotado con _pad a la mitad izquierda).
    c_guarda, c_boton, _pad = st.columns([3, 2, 5])
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
    if guardar:
        if not nombre.strip():
            st.warning("Ponele un nombre a la receta.")
        elif not guardado_por.strip():
            st.warning("Decime quién la guarda (campo 'Guardado por').")
        elif not lineas:
            st.warning("Agregá al menos un ingrediente.")
        elif _guardar_propuesta(
            "Receta de Venta", nombre.strip(), guardado_por.strip(), lineas,
            extra={"precio_venta": precio_venta},
        ):
            st.success(f"«{nombre}» se guardó como propuesta.")
            _limpiar_modo(modo)


# ─── Combo ───────────────────────────────────────────────────────────────
def _render_combo(slot_nombre):
    modo = "combo"
    df_prod = _catalogo_productos_venta_cacheado()
    if df_prod is None:
        st.error(
            f"No se pudo armar el catálogo de productos de venta desde "
            f"{_ARCHIVO_RECETAVENTA} (¿faltan columnas, o no hay platos activos?)."
        )
        return

    # Mismo esquema que _render_receta_venta: nombre al lado del toggle,
    # buscador después, ítems a la izquierda + panel de precios al costado,
    # y por último guardar. Combo no tiene "porciones" (un combo se costea
    # entero), así que no hay diferencia estructural con Receta de venta.
    with slot_nombre:
        nombre = st.text_input(
            "Nombre del combo", key=_key(modo, "nombre"),
            placeholder="nombre del combo…",
            label_visibility="collapsed",
        )

    _buscador_catalogo(
        modo, "productos_venta",
        placeholder="Buscar producto de venta (plato)…",
        unidad_nueva="porción",
    )

    c_items, c_pricing = st.columns([3, 2])
    with c_items:
        lineas = _tabla_lineas(modo)
    total = _total_lineas(lineas)
    with c_pricing:
        precio_venta = _pricing_panel(modo, total)

    c_guarda, c_boton, _pad = st.columns([3, 2, 5])
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
    if guardar:
        if not nombre.strip():
            st.warning("Ponele un nombre al combo.")
        elif not guardado_por.strip():
            st.warning("Decime quién lo guarda (campo 'Guardado por').")
        elif not lineas:
            st.warning("Agregá al menos un producto.")
        elif _guardar_propuesta(
            "Combo", nombre.strip(), guardado_por.strip(), lineas,
            extra={"precio_venta": precio_venta},
        ):
            st.success(f"«{nombre}» se guardó como propuesta.")
            _limpiar_modo(modo)


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

    # Nombre y toggle en UNA fila (pedido 2026-09-23): el nombre a la
    # izquierda, acortado, y el toggle al lado. Las columnas se abren ACÁ,
    # antes de saber el modo, porque el toggle decide qué renderer corre y
    # el nombre lo dibuja el renderer (su key es por modo). En «Guardadas»
    # el hueco del nombre queda vacío y el toggle no se mueve de sitio.
    c_nom, c_tipo, _pad = st.columns([3, 3, 4], vertical_alignment="center")
    with c_tipo:
        modo_label = st.segmented_control(
            "Tipo", ["Receta de venta", "Combo", "Guardadas"],
            default="Receta de venta", key="form_receta_modo",
            label_visibility="collapsed",
        )

    if modo_label == "Combo":
        _render_combo(c_nom)
    elif modo_label == "Guardadas":
        _render_guardadas()
    else:
        _render_receta_venta(c_nom)


def render_formulario_receta():
    """Entrada del formulario, tal como lo consume `graficos/recetas.py` desde
    su sección "Nueva receta". Sin `st.subheader` propio ni caption largo: la
    tarjeta blanca la aporta el dispatcher (`st.container(border=True,
    key="rec_card_nueva")`) y el título de la sección ya lo pone el rail —
    un h2 acá sumaba unos 60px y sacaba al buscador de la primera pantalla
    en una laptop (pedido 2026-09-22).

    Es una envoltura fina sobre `_fragment_nueva_receta` — el fragment
    absorbe los reruns del buscador para que el "+" responda en el
    orden de 100 ms en vez de re-ejecutar el reporte entero."""
    _fragment_nueva_receta()
