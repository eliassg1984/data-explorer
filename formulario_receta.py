"""
formulario_receta.py — herramienta "Nueva Receta": arma y costea una receta
de venta a partir del inventario valorizado, y la deja guardada como
propuesta en R2 para que otra persona la revise.

Punto de entrada público: render_formulario_receta().

Vive en el mismo grupo de nav "Recetas" que Receta Base / Receta Venta
(`grupo_nav` en data.py) — el chip de arriba (`_chip_fuente` en
graficos/recetas_comun.py) navega entre las tres. A diferencia de esas dos,
esta NO es un reporte de parquet con fecha/filtros: entra por `tool: True`
(igual que Inspector, ver app.py), no por el pipeline de carga de app.py.

v1 (este commit) — deliberadamente acotado:
  - Solo "Receta de Venta": insumos de inventariovalorizado.parquet,
    costeo en vivo (S/ y % del total), precio de venta -> % de costo y
    margen, Guardar como propuesta JSON en R2 (_recetas_propuestas/).
  - Guardar es una PROPUESTA, no una escritura a recetaventa.parquet: esa
    la controla el pipeline diario (Extraer a parquet.py / SQL Server), no
    la webapp — mismo principio que ya sigue solicitar_refresco() en
    data.py, que tampoco toca los parquets fuente directamente.

Afuera de este commit a propósito (ver mockups de la conversación de
diseño para el alcance completo, quedan para commits siguientes):
  - Pestaña Combo (arma un combo con productos de venta, no con insumos).
  - Crear/editar una Receta Base desde acá.
  - Envío por correo (necesita SMTP_USER/SMTP_APP_PASSWORD en secrets,
    que todavía no existen).
  - Exportar a Excel/PDF.
  - Un visor de las propuestas ya guardadas en R2 (hoy quedan ahí, pero
    no hay una pantalla en la app que las liste).
  - Grupo/SubGrupo de clasificación (no hay una fuente real definida
    todavía para esa taxonomía — no se inventa una acá).

OJO — `Activo` en inventariovalorizado.parquet: a diferencia de
recetabase/recetaventa (con sus 3 formatos confirmados contra R2 real, ver
`_activo()` en recetas_comun.py), NO se verificó si este parquet trae una
columna de activo/inactivo ni en qué formato. `_resolver` con candidatos
razonables + degradación silenciosa (sin insignia) si no aparece — nunca
se asume una columna que no se confirmó.
"""

import json
import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from data import cargar as _cargar_reporte
from data import get_s3_cliente, secrets_disponibles
from graficos.base import _resolver
from graficos.recetas_comun import _chip_fuente

_ARCHIVO_INVENTARIO = "inventariovalorizado.parquet"
_IGV = 1.18
_UMBRAL_COSTO_OK = 30
_UMBRAL_COSTO_WARN = 35


def _fmt(v):
    return f"S/ {v:,.2f}"


def _key_lineas():
    return "form_receta_lineas"


def _init_estado():
    st.session_state.setdefault(_key_lineas(), [])
    st.session_state.setdefault("form_receta_contador_nuevo", 0)


def _total_lineas(lineas):
    return sum(l["cantidad"] * l["precio"] for l in lineas)


@st.cache_data(ttl=300, show_spinner=False)
def _catalogo_insumos_cacheado():
    """Separado de la resolución de columnas para no recalcular _resolver
    en cada rerun — el df en sí ya lo cachea data.cargar(), esto cachea
    además el resultado de la búsqueda de columnas."""
    df = _cargar_reporte(_ARCHIVO_INVENTARIO)
    if df is None or df.empty:
        return None, {}

    col_cod = _resolver(df, ["Codigo Producto", "Código Producto", "COD_PRODUCTO"])
    col_nombre = _resolver(df, ["Nombre Producto", "NOMBRE_PRODUCTO"])
    col_unidad = _resolver(df, ["Unidad Kardex", "UNIDAD_KARDEX", "Unidad"])
    col_precio = _resolver(df, ["Precio Promedio", "PRECIO PROMEDIO", "Precio"])
    col_activo = _resolver(df, ["Activo", "ACTIVO", "Estado"])

    if not (col_cod and col_nombre and col_precio):
        return None, {}

    cols = {"cod": col_cod, "nombre": col_nombre, "precio": col_precio}
    if col_unidad:
        cols["unidad"] = col_unidad
    if col_activo:
        cols["activo"] = col_activo
    return df, cols


def _es_activo(fila, cols):
    """None si el parquet no trae columna de activo (no se sabe -> no se
    muestra insignia). True/False si sí la trae."""
    if "activo" not in cols:
        return None
    val = str(fila[cols["activo"]]).strip().upper()
    return val not in ("INACTIVO", "INACTIVA", "INACTIVE", "NO", "0", "FALSE", "N")


def _agregar_linea(cod, nombre, unidad, precio, activo, tipo):
    lineas = st.session_state[_key_lineas()]
    if any(l["cod"] == cod for l in lineas):
        return
    lineas.append({
        "cod": cod, "nombre": nombre, "unidad": unidad or "unidad",
        "precio": float(precio), "cantidad": 1.0, "activo": activo, "tipo": tipo,
    })


def _buscador_insumos(df_cat, cols):
    """Buscador con botón "Agregar" por resultado — más simple y liviano en
    Streamlit que un dropdown custom (eso tenía sentido en JS para el
    mockup; acá el widget nativo ya resuelve filtro + scroll)."""
    texto = st.text_input(
        "Buscar artículo del almacén", placeholder="nombre o código…",
        key="form_receta_buscador",
    ).strip()

    if not texto:
        return

    mask = (
        df_cat[cols["nombre"]].astype(str).str.contains(texto, case=False, na=False, regex=False)
        | df_cat[cols["cod"]].astype(str).str.contains(texto, case=False, na=False, regex=False)
    )
    resultados = df_cat[mask].head(8)
    lineas_actuales = {l["cod"] for l in st.session_state[_key_lineas()]}

    if resultados.empty:
        st.caption(f"Sin resultados para «{texto}».")
    else:
        for _, fila in resultados.iterrows():
            cod = str(fila[cols["cod"]])
            nombre = str(fila[cols["nombre"]])
            unidad = str(fila[cols["unidad"]]) if "unidad" in cols else "unidad"
            precio = float(fila[cols["precio"]]) if pd.notna(fila[cols["precio"]]) else 0.0
            activo = _es_activo(fila, cols)

            c1, c2 = st.columns([5, 1])
            etiqueta = f"{nombre} · {cod} · {unidad} · {_fmt(precio)}"
            if activo is False:
                etiqueta += " · 🔸 Inactivo"
            c1.write(etiqueta)
            ya_agregado = cod in lineas_actuales
            if c2.button(
                "Agregada" if ya_agregado else "Agregar",
                key=f"form_receta_add_{cod}",
                disabled=ya_agregado,
                use_container_width=True,
            ):
                _agregar_linea(cod, nombre, unidad, precio, activo, "almacen")
                st.rerun()

    if st.button(f"➕ Agregar «{texto}» como artículo nuevo", key="form_receta_add_nuevo"):
        st.session_state["form_receta_contador_nuevo"] += 1
        n = st.session_state["form_receta_contador_nuevo"]
        _agregar_linea(f"NUEVO-{n}", texto, "unidad", 0.0, None, "nuevo")
        st.rerun()


def _tabla_lineas():
    """Devuelve las líneas YA sincronizadas con lo que el usuario haya
    editado en el data_editor durante ESTE mismo rerun (no hace falta un
    st.rerun() extra acá: el propio data_editor ya disparó el rerun que
    llegó hasta este punto; el llamador de esta función usa el valor
    devuelto, no una copia vieja)."""
    lineas = st.session_state[_key_lineas()]
    if not lineas:
        st.info("Todavía no agregaste ingredientes. Buscá un artículo arriba para empezar.")
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

    editado = st.data_editor(
        df_show,
        key="form_receta_editor",
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
        if st.button("Quitar marcadas", key="form_receta_quitar"):
            a_quitar = set(editado.index[editado["Quitar"]])
            if a_quitar:
                st.session_state[_key_lineas()] = [
                    l for i, l in enumerate(lineas) if i not in a_quitar
                ]
                st.session_state.pop("form_receta_editor", None)
                st.rerun()
    with c2:
        if st.button("Vaciar receta", key="form_receta_vaciar"):
            st.session_state[_key_lineas()] = []
            st.session_state.pop("form_receta_editor", None)
            st.rerun()

    return lineas


def _guardar_propuesta(nombre, guardado_por, lineas, porciones, precio_venta):
    """Escribe la propuesta como JSON en R2 (_recetas_propuestas/), mismo
    mecanismo que solicitar_refresco() en data.py (get_s3_cliente() +
    put_object). NUNCA escribe en recetaventa.parquet directamente — eso lo
    genera el pipeline diario a partir de la fuente real."""
    payload = {
        "tipo": "Receta de Venta",
        "nombre": nombre,
        "guardado_por": guardado_por,
        "guardado_en": datetime.now(timezone.utc).isoformat(),
        "porciones": porciones,
        "precio_venta": precio_venta,
        "total": round(_total_lineas(lineas), 2),
        "lineas": [
            {k: l[k] for k in ("cod", "nombre", "unidad", "precio", "cantidad", "tipo")}
            for l in lineas
        ],
    }

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


# ─── Punto de entrada público ───────────────────────────────────────────────
def render_formulario_receta():
    _init_estado()
    _chip_fuente("Nueva Receta")

    st.subheader("Nueva Receta")
    st.caption(
        "Armá una receta con artículos del almacén, mirá el costo en vivo, "
        "y guardala como propuesta para que otra persona la revise."
    )

    df_cat, cols = _catalogo_insumos_cacheado()
    if df_cat is None:
        st.error(
            f"No se pudo leer {_ARCHIVO_INVENTARIO} o le faltan columnas clave "
            "(Código Producto / Nombre Producto / Precio Promedio)."
        )
        return

    c1, c2 = st.columns([3, 1])
    with c1:
        nombre_receta = st.text_input("Nombre de la receta", key="form_receta_nombre")
    with c2:
        porciones = st.number_input("Porciones", min_value=0, step=1, value=0, key="form_receta_porciones")

    _buscador_insumos(df_cat, cols)
    lineas = _tabla_lineas()

    total = _total_lineas(lineas)
    costo_porcion = (total / porciones) if porciones > 0 else None

    m1, m2 = st.columns(2)
    m1.metric("Costo total", _fmt(total))
    m2.metric("Costo por porción", _fmt(costo_porcion) if costo_porcion is not None else "—")

    st.divider()
    precio_venta = st.number_input(
        "Precio de venta (por porción, con IGV)", min_value=0.0, step=0.10,
        key="form_receta_precio_venta",
    )
    if costo_porcion is not None and precio_venta > 0:
        precio_neto = precio_venta / _IGV
        pct_costo = costo_porcion / precio_neto * 100 if precio_neto else 0.0
        margen = precio_neto - costo_porcion
        p1, p2, p3 = st.columns(3)
        p1.metric("Precio neto (sin IGV 18%)", _fmt(precio_neto))
        p2.metric("% de costo", f"{pct_costo:.1f}%")
        p3.metric("Margen por porción", _fmt(margen))
        if pct_costo <= _UMBRAL_COSTO_OK:
            st.caption("🟢 % de costo muy bueno (referencia orientativa, no una regla del negocio).")
        elif pct_costo <= _UMBRAL_COSTO_WARN:
            st.caption("🟠 % de costo aceptable (referencia orientativa).")
        else:
            st.caption("🔴 % de costo alto para la mayoría de restaurantes (referencia orientativa).")
    else:
        st.caption("Ingresá porciones (arriba) y un precio de venta para ver el % de costo.")

    st.divider()
    guardado_por = st.text_input("Guardado por (tu nombre)", key="form_receta_guardado_por")
    if st.button("💾 Guardar como propuesta", type="primary", key="form_receta_guardar"):
        if not nombre_receta.strip():
            st.warning("Ponele un nombre a la receta.")
        elif not guardado_por.strip():
            st.warning("Decime quién la guarda (campo 'Guardado por').")
        elif not lineas:
            st.warning("Agregá al menos un ingrediente.")
        else:
            if _guardar_propuesta(
                nombre_receta.strip(), guardado_por.strip(), lineas, porciones, precio_venta
            ):
                st.success(f"«{nombre_receta}» se guardó como propuesta.")
                st.session_state[_key_lineas()] = []
                st.session_state.pop("form_receta_editor", None)
