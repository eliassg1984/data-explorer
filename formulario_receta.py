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
from graficos.base import _resolver
# El catálogo de insumos y el nombre de SU parquet viajan juntos, y viven
# allá desde el 2026-09-17 — ver el comentario de `_catalogo_insumos_
# cacheado` más abajo.
from graficos.recetas_comun import (
    ARCHIVO_INVENTARIO as _ARCHIVO_INVENTARIO,
    _activo, catalogo_insumos,
)

_ARCHIVO_RECETAVENTA = "recetaventa.parquet"
_IGV = 1.18
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


def _buscador_catalogo(modo, df_cat, *, etiqueta, placeholder,
                       etiqueta_nuevo, unidad_nueva="unidad"):
    """Buscador SUGESTIVO: `st.selectbox` con `index=None`, filtra a medida
    que el usuario escribe (client-side, sin Enter). Al elegir una opción,
    la línea entra a la tabla y el widget se resetea vía key incremental
    (`_key(modo, "buscador_v<n>")`): Streamlit borra el estado del widget
    anterior y el próximo render arranca en None.

    Reemplaza al esquema anterior de `st.text_input` + fila de resultados
    con un botón "Agregar" cada una — el text_input pedía Enter/blur para
    aceptar cada carácter, así que el catálogo no se filtraba hasta que la
    persona confirmaba. Motivo del cambio: pedido de 2026-09-22 («la opción
    para búsqueda y selección de insumos o platos debe ser sugestiva al
    digitar, no debe esperar Enter»).

    La rama de «Agregar como nuevo» (para un insumo/plato que todavía no
    está en el catálogo) sobrevive como un input aparte compacto debajo,
    porque el selectbox sólo devuelve opciones existentes — sin este puente
    se pierde el flujo de dar de alta un ítem que va a la propuesta con
    precio 0 para que después alguien lo complete."""
    contador_key = _key(modo, "buscador_ver")
    st.session_state.setdefault(contador_key, 0)
    ver = st.session_state[contador_key]

    lineas_actuales = {l["cod"] for l in st.session_state[_key_lineas(modo)]}
    opciones = []
    meta = {}
    for _, fila in df_cat.iterrows():
        cod = fila["cod"]
        if cod in lineas_actuales:
            continue  # ya está en la tabla, no ofrecerlo de vuelta
        nombre, unidad, precio = fila["nombre"], fila["unidad"], float(fila["precio"])
        activo = _es_activo_valor(fila)
        etiqueta_fila = f"{nombre} · {cod} · {unidad} · {_fmt(precio)}"
        if activo is False:
            etiqueta_fila += " · Inactivo"
        opciones.append(etiqueta_fila)
        meta[etiqueta_fila] = (cod, nombre, unidad, precio, activo)

    if opciones:
        elegido = st.selectbox(
            etiqueta, opciones, index=None, placeholder=placeholder,
            key=_key(modo, f"buscador_v{ver}"),
        )
        if elegido:
            cod, nombre, unidad, precio, activo = meta[elegido]
            _agregar_linea(modo, cod, nombre, unidad, precio, activo, "almacen")
            st.session_state[contador_key] = ver + 1
            st.rerun()
    else:
        st.caption("Todos los ítems del catálogo ya están agregados.")

    with st.expander(f"¿No está en la lista? Agregar como {etiqueta_nuevo}", expanded=False):
        c_txt, c_btn = st.columns([4, 1])
        with c_txt:
            nuevo_nombre = st.text_input(
                "Nombre", key=_key(modo, f"nuevo_nombre_v{ver}"),
                placeholder="nombre del ítem nuevo…", label_visibility="collapsed",
            ).strip()
        with c_btn:
            if st.button("Agregar", key=_key(modo, "add_nuevo"),
                         disabled=not nuevo_nombre, use_container_width=True):
                st.session_state["form_receta_contador_nuevo"] += 1
                n = st.session_state["form_receta_contador_nuevo"]
                _agregar_linea(modo, f"NUEVO-{n}", nuevo_nombre, unidad_nueva, 0.0, None, "nuevo")
                st.session_state[contador_key] = ver + 1
                st.rerun()


def _tabla_lineas(modo):
    """Devuelve las líneas YA sincronizadas con lo que el usuario haya
    editado en el data_editor durante ESTE mismo rerun (no hace falta un
    st.rerun() extra: el propio data_editor ya disparó el rerun que llegó
    hasta acá; el llamador usa el valor devuelto, no una copia vieja)."""
    lineas = st.session_state[_key_lineas(modo)]
    if not lineas:
        st.info("Todavía no agregaste ítems. Buscá uno arriba para empezar.")
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
        column_config={
            "Quitar": st.column_config.CheckboxColumn(width="small"),
            "Cantidad": st.column_config.NumberColumn(min_value=0.0, step=0.01, format="%.2f"),
            "Precio unit. (S/)": st.column_config.NumberColumn(min_value=0.0, step=0.01, format="%.2f"),
            "Unidad": st.column_config.TextColumn(width="small"),
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
                st.rerun()
    with c2:
        if st.button("Vaciar", key=_key(modo, "vaciar")):
            st.session_state[_key_lineas(modo)] = []
            st.session_state.pop(editor_key, None)
            st.rerun()

    return lineas


def _mostrar_pricing(costo_base, precio_venta, *, msg_sin_base="Agregá ítems para poder calcular esto."):
    """costo_base: costo por porción (Receta de Venta) o costo del combo
    entero (Combo, no hay porciones que dividir ahí) — al llamador le toca
    decidir cuál de los dos pasar y qué mensaje mostrar mientras no hay
    costo_base (los dos modos tienen motivos distintos para no tenerlo
    todavía: a Receta de Venta le faltan las porciones, a Combo le faltan
    ítems agregados)."""
    if costo_base is None:
        st.caption(msg_sin_base)
        return
    if not precio_venta:
        st.caption("Ingresá un precio de venta para calcular el precio neto y el % de costo.")
        return

    precio_neto = precio_venta / _IGV
    pct = costo_base / precio_neto * 100 if precio_neto else 0.0
    margen = precio_neto - costo_base

    p1, p2, p3 = st.columns(3)
    p1.metric("Precio neto (sin IGV 18%)", _fmt(precio_neto))
    p2.metric("% de costo", f"{pct:.1f}%")
    p3.metric("Margen", _fmt(margen))
    if pct <= _UMBRAL_COSTO_OK:
        st.caption("🟢 % de costo muy bueno (referencia orientativa, no una regla del negocio).")
    elif pct <= _UMBRAL_COSTO_WARN:
        st.caption("🟠 % de costo aceptable (referencia orientativa).")
    else:
        st.caption("🔴 % de costo alto para la mayoría de restaurantes (referencia orientativa).")


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
    seguidas) pero limpia nombre/porciones/precio — son de ESTA receta, y
    dejarlos puestos invita a re-guardar por error con el título viejo."""
    st.session_state[_key_lineas(modo)] = []
    st.session_state.pop(_key(modo, "editor"), None)
    st.session_state.pop(_key(modo, "nombre"), None)
    st.session_state.pop(_key(modo, "porciones"), None)
    st.session_state.pop(_key(modo, "precio_venta"), None)


# ─── Receta de venta ─────────────────────────────────────────────────────
def _render_receta_venta():
    modo = "venta"
    df_cat = _catalogo_insumos_cacheado()
    if df_cat is None:
        st.error(
            f"No se pudo leer {_ARCHIVO_INVENTARIO} o le faltan columnas clave "
            "(Código Producto / Nombre Producto / Precio Promedio)."
        )
        return

    # Fila única: nombre + porciones + buscador. Antes eran tres renglones
    # (nombre/porciones en uno, buscador aparte); apilada en el rail junto a
    # las nueve secciones del reporte, cada línea de arriba empuja el resto
    # fuera de la primera pantalla — pedido de 2026-09-22 («todo el proceso
    # entre en una sola ventana de la pantalla de una laptop»).
    c_nom, c_por, c_buscar = st.columns([3, 1, 4])
    with c_nom:
        nombre = st.text_input("Nombre de la receta", key=_key(modo, "nombre"),
                               placeholder="nombre de la receta…")
    with c_por:
        porciones = st.number_input("Porciones", min_value=0, step=1, value=0,
                                    key=_key(modo, "porciones"))
    with c_buscar:
        _buscador_catalogo(
            modo, df_cat, etiqueta="Buscar artículo del almacén",
            placeholder="empezá a escribir para filtrar…",
            etiqueta_nuevo="artículo nuevo",
        )

    lineas = _tabla_lineas(modo)

    total = _total_lineas(lineas)
    costo_porcion = (total / porciones) if porciones > 0 else None

    # Costos + precio + pricing en una sola franja, sin dividers: cada
    # `st.divider` cobraba unos 30-40px y multiplicaba lo que había que
    # scrollear para llegar al botón de Guardar.
    c_total, c_porc, c_precio = st.columns(3)
    c_total.metric("Costo total", _fmt(total))
    c_porc.metric("Costo por porción",
                  _fmt(costo_porcion) if costo_porcion is not None else "—")
    with c_precio:
        precio_venta = st.number_input(
            "Precio de venta (por porción, con IGV)",
            min_value=0.0, step=0.10, key=_key(modo, "precio_venta"),
        )

    _mostrar_pricing(
        costo_porcion, precio_venta,
        msg_sin_base="Ingresá las porciones (arriba) para poder calcular esto.",
    )

    c_guarda, c_boton = st.columns([3, 1])
    with c_guarda:
        guardado_por = st.text_input("Guardado por (tu nombre)",
                                     key=_key(modo, "guardado_por"),
                                     placeholder="tu nombre…")
    with c_boton:
        st.write("")  # alinea el botón con el input
        guardar = st.button("💾 Guardar propuesta", type="primary",
                            key=_key(modo, "guardar"), use_container_width=True)
    if guardar:
        if not nombre.strip():
            st.warning("Ponele un nombre a la receta.")
        elif not guardado_por.strip():
            st.warning("Decime quién la guarda (campo 'Guardado por').")
        elif not lineas:
            st.warning("Agregá al menos un ingrediente.")
        elif _guardar_propuesta(
            "Receta de Venta", nombre.strip(), guardado_por.strip(), lineas,
            extra={"porciones": porciones, "precio_venta": precio_venta},
        ):
            st.success(f"«{nombre}» se guardó como propuesta.")
            _limpiar_modo(modo)


# ─── Combo ───────────────────────────────────────────────────────────────
def _render_combo():
    modo = "combo"
    df_prod = _catalogo_productos_venta_cacheado()
    if df_prod is None:
        st.error(
            f"No se pudo armar el catálogo de productos de venta desde "
            f"{_ARCHIVO_RECETAVENTA} (¿faltan columnas, o no hay platos activos?)."
        )
        return

    # Fila única: nombre + buscador (Combo no tiene "porciones" — un combo
    # se costea entero, no por porción). Mismo criterio compacto que
    # `_render_receta_venta`.
    c_nom, c_buscar = st.columns([3, 4])
    with c_nom:
        nombre = st.text_input("Nombre del combo", key=_key(modo, "nombre"),
                               placeholder="nombre del combo…")
    with c_buscar:
        _buscador_catalogo(
            modo, df_prod, etiqueta="Buscar producto de venta",
            placeholder="empezá a escribir el nombre del plato…",
            etiqueta_nuevo="producto nuevo", unidad_nueva="porción",
        )

    lineas = _tabla_lineas(modo)

    total = _total_lineas(lineas)
    c_total, c_precio = st.columns(2)
    c_total.metric("Costo total del combo", _fmt(total))
    with c_precio:
        precio_venta = st.number_input(
            "Precio de venta del combo (con IGV)",
            min_value=0.0, step=0.10, key=_key(modo, "precio_venta"),
        )

    _mostrar_pricing(total if lineas else None, precio_venta)

    c_guarda, c_boton = st.columns([3, 1])
    with c_guarda:
        guardado_por = st.text_input("Guardado por (tu nombre)",
                                     key=_key(modo, "guardado_por"),
                                     placeholder="tu nombre…")
    with c_boton:
        st.write("")
        guardar = st.button("💾 Guardar propuesta", type="primary",
                            key=_key(modo, "guardar"), use_container_width=True)
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
        st.rerun()

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
def render_formulario_receta():
    """Entrada del formulario, tal como lo consume `graficos/recetas.py` desde
    su sección "Nueva receta". Sin `st.subheader` propio ni caption largo: la
    tarjeta blanca la aporta el dispatcher (`st.container(border=True,
    key="rec_card_nueva")`) y el título de la sección ya lo pone el rail —
    un h2 acá sumaba unos 60px y sacaba al buscador de la primera pantalla
    en una laptop (pedido 2026-09-22)."""
    _init_estado()

    modo_label = st.segmented_control(
        "Tipo", ["Receta de venta", "Combo", "Guardadas"],
        default="Receta de venta", key="form_receta_modo",
        label_visibility="collapsed",
    )

    if modo_label == "Combo":
        _render_combo()
    elif modo_label == "Guardadas":
        _render_guardadas()
    else:
        _render_receta_venta()
