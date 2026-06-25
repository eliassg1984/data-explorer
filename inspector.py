"""
Inspector de datos: herramienta para verificar el contenido CRUDO de los
archivos parquet (sin pivote ni agregación).

Funciones para el usuario:
- Elegir cualquier archivo de datos y ver sus filas tal como vienen del parquet.
- Conteo de control: cuántas filas tiene en total y cuántas coinciden.
- Radiografía de columnas: tipo, nulos y rango de fechas.
- Aviso de posibles problemas para la tabla (AgGrid): columnas repetidas, de fecha, etc.
- Búsqueda por columna (exacta o contiene, ignorando mayúsculas y espacios).
- Filtro por fecha (rango desde / hasta) sobre una columna de fecha.
- Descargar las coincidencias a CSV.
"""

import pandas as pd
import streamlit as st

from data import REPORTES, cargar
import diagnostico


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------
def _reportes_datos():
    """Reportes que son archivos de datos (excluye herramientas como este)."""
    return {
        n: c for n, c in REPORTES.items()
        if c.get("archivo") and not c.get("tool")
    }


def _columnas_fecha(df):
    """Columnas que parecen de fecha (por tipo datetime o por nombre)."""
    cols = []
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            cols.append(c)
        elif "fecha" in str(c).lower() or "date" in str(c).lower():
            cols.append(c)
    return list(dict.fromkeys(cols))  # sin duplicados, manteniendo orden


def _primer_valor(serie):
    s = serie.dropna()
    return "" if s.empty else str(s.iloc[0])[:40]


# ---------------------------------------------------------------------------
# Vista principal
# ---------------------------------------------------------------------------
def render_inspector():
    st.markdown(
        '<p style="font-size:22px;font-weight:700;color:#1e293b;'
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

    # ── Conteo de control ───────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    c1.metric("📄 Filas totales", f"{total:,}")
    c2.metric("🧱 Columnas", f"{df.shape[1]}")

    # ── Radiografía de columnas ─────────────────────────────────────────────
    with st.expander("🩺 Radiografía de columnas (tipos, nulos, rango de fechas)"):
        info = pd.DataFrame({
            "Columna": list(df.columns),
            "Tipo": [str(df[c].dtype) for c in df.columns],
            "Nulos": [int(df[c].isna().sum()) for c in df.columns],
            "% Nulos": [round(float(df[c].isna().mean()) * 100, 1) for c in df.columns],
            "Ejemplo": [_primer_valor(df[c]) for c in df.columns],
        })
        st.dataframe(info, use_container_width=True, hide_index=True)
        for c in _columnas_fecha(df):
            serie = pd.to_datetime(df[c], errors="coerce").dropna()
            if not serie.empty:
                st.caption(f"📅 {c}: {serie.min():%d/%m/%Y} → {serie.max():%d/%m/%Y}")

    # ── ¿Esto puede romper la tabla (AgGrid)? ───────────────────────────────
    # Revisa el archivo y avisa de lo que típicamente deja la tabla en blanco
    # (columnas repetidas, de fecha, 100% vacías, o texto que parece número).
    hallazgos = diagnostico.revisar_datos(df)
    with st.expander("🚦 ¿Esto puede romper la tabla?", expanded=bool(hallazgos)):
        if not hallazgos:
            st.success("No se detectaron problemas para AgGrid. ✅")
        else:
            for h in hallazgos:
                if h["nivel"] == "alerta":
                    st.warning(h["mensaje"])
                else:
                    st.info(h["mensaje"])

    st.divider()

    # ── Filtros ─────────────────────────────────────────────────────────────
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
        cols_fecha = _columnas_fecha(df)
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

    # Aplicar búsqueda por columna sobre lo que quede tras el filtro de fecha
    if texto.strip():
        objetivo = texto.strip()
        serie_txt = df_f[col_busc].astype(str).str.strip()
        if modo == "Exacta":
            mask = serie_txt.str.lower() == objetivo.lower()
        else:
            mask = serie_txt.str.contains(objetivo, case=False, na=False, regex=False)
        df_f = df_f[mask.values]

    # ── Resultados ──────────────────────────────────────────────────────────
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
        st.dataframe(df_f, use_container_width=True, height=480)
        st.download_button(
            "⬇️ Descargar coincidencias (CSV)",
            data=df_f.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"inspector_{archivo.replace('.parquet', '')}.csv",
            mime="text/csv",
        )
