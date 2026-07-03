"""
Inspector de datos: herramienta para verificar el contenido CRUDO de los
archivos parquet (sin pivote ni agregación).

Funciones:
- Elegir cualquier archivo y ver sus filas tal como vienen del parquet.
- Vista previa rápida (primeras filas sin filtros).
- Conteo de control: cuántas filas totales y cuántas coinciden.
- Radiografía de columnas: tipo, nulos, ejemplo y nombre normalizado.
- Detección de columnas duplicadas (rompen AgGrid).
- Valores únicos de cualquier columna con su conteo.
- Búsqueda por columna (exacta o contiene).
- Filtro por fecha (rango).
- Descargar coincidencias a CSV.
"""

import pandas as pd
import streamlit as st

from utils import _norm, buscar_columna, buscar_columna_fecha
from data import REPORTES, cargar


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
LIMITE_FILAS = 10_000
VISTA_PREVIA_N = 10


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------
def _reportes_datos():
    """Reportes que son archivos de datos (excluye herramientas)."""
    return {
        n: c for n, c in REPORTES.items()
        if c.get("archivo") and not c.get("tool")
    }


def _todas_fechas(df):
    """Columnas que parecen de fecha (usa _norm de utils para consistencia)."""
    cols = []
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            cols.append(c)
        elif "fecha" in _norm(c) or "date" in _norm(c):
            cols.append(c)
    return list(dict.fromkeys(cols))


def _ejemplos(serie, n=3):
    """Retorna hasta n valores no nulos de una serie, como texto corto."""
    vals = serie.dropna().astype(str).head(n).tolist()
    return " | ".join(v[:30] for v in vals) if vals else "(vacía)"


def _columnas_duplicadas(df):
    """Detecta columnas con el mismo nombre (rompen AgGrid)."""
    duplicadas = df.columns[df.columns.duplicated()].unique().tolist()
    resultado = []
    for nombre in duplicadas:
        veces = int((df.columns == nombre).sum())
        posiciones = [i for i, c in enumerate(df.columns) if c == nombre]
        resultado.append({
            "nombre": nombre,
            "veces": veces,
            "posiciones": posiciones,
        })
    return resultado


# ---------------------------------------------------------------------------
# Vista principal
# ---------------------------------------------------------------------------
def render_inspector():
    st.markdown(
        '<p style="font-size:22px;font-weight:700;color:#18181d;'
        'margin:0 0 0.4rem 0;">🔍 Inspector de datos</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Verifica el contenido **crudo** de cualquier archivo (sin pivote ni "
        "agregación). Sirve para confirmar si un registro existe realmente en "
        "el parquet, más allá de lo que muestren las tablas filtradas."
    )

    datos = _reportes_datos()
    if not datos:
        st.warning("No hay archivos de datos configurados para inspeccionar.")
        return

    nombre = st.selectbox("Archivo a inspeccionar", list(datos.keys()), key="insp_rep")
    archivo = datos[nombre]["archivo"]

    df = cargar(archivo)
    if df is None or df.empty:
        st.warning(f"No se pudieron cargar los datos de **{nombre}** ({archivo}).")
        return

    total = len(df)

    # ── Métricas de control ────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("📄 Filas totales", f"{total:,}")
    c2.metric("🧱 Columnas", f"{df.shape[1]}")
    c3.metric("📍 Columnas de fecha", f"{len(_todas_fechas(df))}")

    # ── Alerta: columnas duplicadas ────────────────────────────────────────
    duplicadas = _columnas_duplicadas(df)
    if duplicadas:
        for d in duplicadas:
            st.warning(
                f"⚠️ Columna repetida: «{d['nombre']}» aparece {d['veces']} veces "
                f"en posiciones {d['posiciones']}. AgGrid muestra la tabla vacía "
                f"cuando hay columnas duplicadas."
            )

    # ── Vista previa (sin filtros) ───────────────────────────────────────
    with st.expander("👁️ Vista previa (primeras filas sin filtros)", expanded=False):
        st.caption(f"Mostrando las primeras {VISTA_PREVIA_N} filas tal como vienen del parquet:")
        vista = df.head(VISTA_PREVIA_N).reset_index()
        vista.rename(columns={"index": "fila"}, inplace=True)
        vista["fila"] = vista["fila"] + 1
        st.dataframe(vista, use_container_width=True, hide_index=True, height=320)

    # ── Radiografía de columnas ──────────────────────────────────────────
    with st.expander("🩺 Radiografía de columnas"):
        info = pd.DataFrame({
            "Columna": list(df.columns),
            "Normalizado": [_norm(c) for c in df.columns],
            "Tipo": [str(df[c].dtype) for c in df.columns],
            "Nulos": [int(df[c].isna().sum()) for c in df.columns],
            "% Nulos": [round(float(df[c].isna().mean()) * 100, 1) for c in df.columns],
            "Ejemplos": [_ejemplos(df[c], 3) for c in df.columns],
        })
        st.dataframe(info, use_container_width=True, hide_index=True)

        fechas = _todas_fechas(df)
        if fechas:
            st.markdown("**Rango de fechas:**")
            for c in fechas:
                serie = pd.to_datetime(df[c], errors="coerce").dropna()
                if not serie.empty:
                    st.caption(f"  📅 {c}: {serie.min():%d/%m/%Y} → {serie.max():%d/%m/%Y}")
                else:
                    st.caption(f"  📅 {c}: sin fechas válidas")

    # ── Valores únicos de una columna ────────────────────────────────────
    with st.expander("📋 Valores únicos por columna"):
        col_unique = st.selectbox("Selecciona columna", list(df.columns), key="insp_unique")
        unicos = df[col_unique].value_counts(dropna=False)
        st.caption(f"{len(unicos):,} valores distintos en «{col_unique}»")

        if len(unicos) > LIMITE_FILAS:
            st.warning(
                f"Esta columna tiene {len(unicos):,} valores distintos. "
                f"Mostrando los primeros {LIMITE_FILAS:,}."
            )
            unicos = unicos.head(LIMITE_FILAS)

        df_unicos = unicos.reset_index()
        df_unicos.columns = [col_unique, "conteo"]
        df_unicos.insert(0, "fila", range(1, len(df_unicos) + 1))
        st.dataframe(df_unicos, use_container_width=True, hide_index=True, height=400)

    st.divider()

    # ── Filtros ───────────────────────────────────────────────────────────
    df_f = df
    fcol1, fcol2 = st.columns(2)

    with fcol1:
        st.markdown("**🔎 Búsqueda por columna**")
        col_busc = st.selectbox("Columna", list(df.columns), key="insp_col")
        modo = st.radio(
            "Coincidencia", ["Contiene", "Exacta"],
            horizontal=True, key="insp_modo",
        )
        texto = st.text_input("Valor a buscar", key="insp_txt")

    with fcol2:
        st.markdown("**📅 Filtro por fecha**")
        cols_fecha = _todas_fechas(df)
        if cols_fecha:
            col_fecha = st.selectbox(
                "Columna de fecha", ["(ninguna)"] + cols_fecha, key="insp_fcol",
            )
            if col_fecha != "(ninguna)":
                serie_fch = pd.to_datetime(df_f[col_fecha], errors="coerce")
                fmin, fmax = serie_fch.min(), serie_fch.max()
                if pd.notna(fmin) and pd.notna(fmax):
                    rango = st.date_input(
                        "Rango (desde / hasta)",
                        value=(fmin.date(), fmax.date()),
                        min_value=fmin.date(), max_value=fmax.date(),
                        format="DD/MM/YYYY", key="insp_fch",
                    )
                    if isinstance(rango, (tuple, list)) and len(rango) == 2:
                        ini, fin = rango
                        m = (serie_fch.dt.date >= ini) & (serie_fch.dt.date <= fin)
                        df_f = df_f[m.values]
                else:
                    st.caption("La columna elegida no tiene fechas válidas.")
        else:
            st.caption("Este archivo no tiene columnas de fecha detectables.")

    # Aplicar búsqueda
    if texto.strip():
        objetivo = texto.strip()
        serie_txt = df_f[col_busc].astype(str).str.strip()
        if modo == "Exacta":
            mask = serie_txt.str.lower() == objetivo.lower()
        else:
            mask = serie_txt.str.contains(objetivo, case=False, na=False, regex=False)
        df_f = df_f[mask.values]

    # ── Resultados ───────────────────────────────────────────────────────
    st.divider()
    coincidencias = len(df_f)
    pct = (coincidencias / total * 100) if total else 0
    r1, r2 = st.columns(2)
    r1.metric("✅ Coincidencias", f"{coincidencias:,}")
    r2.metric("Sobre el total", f"{total:,}", f"{pct:.1f}%")

    if coincidencias == 0:
        st.info(
            "No hay filas que cumplan los filtros. Si esperabas resultados, "
            "revisa la grafía exacta, espacios de más, o si el dato cae fuera "
            "del rango de fechas elegido."
        )
    else:
        # Límite de filas para no colgar el navegador
        mostrar = df_f
        if len(df_f) > LIMITE_FILAS:
            st.warning(
                f"⚠️ Mostrando {LIMITE_FILAS:,} de {len(df_f):,} filas. "
                f"Descarga el CSV para ver todas."
            )
            mostrar = df_f.head(LIMITE_FILAS)

        resultado = mostrar.reset_index()
        resultado.rename(columns={"index": "fila"}, inplace=True)
        # Para filas que ya tenían índice numérico del reset anterior,
        # mostrar el índice original del DataFrame
        if "fila" in resultado.columns and resultado["fila"].dtype == object:
            try:
                resultado["fila"] = resultado["fila"].apply(
                    lambda x: int(x.split("(")[1].replace(")", "")) + 1
                    if "(" in str(x) else x
                )
            except Exception:
                pass
        else:
            resultado["fila"] = resultado["fila"] + 1

        st.dataframe(resultado, use_container_width=True, hide_index=True, height=480)
        st.download_button(
            "⬇️ Descargar coincidencias (CSV)",
            data=df_f.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"inspector_{archivo.replace('.parquet', '')}.csv",
            mime="text/csv",
        )
