"""
Diagnóstico: herramientas para entender qué está pasando con los datos y
encontrar rápido por qué una tabla se ve vacía o rota.

La idea: tu app es una línea de montaje. Los datos pasan por etapas
(cargar → reconocer columnas → filtrar → elegir columnas → tabla AgGrid).
Cuando algo falla, estas herramientas te dicen EN QUÉ ETAPA se cae, en vez
de tener que adivinar.

Este es el único hogar del diagnóstico: si más adelante creas otra
herramienta para revisar datos, ponla aquí.
"""


# ===========================================================================
# CÓMO CONECTARLO (3 ediciones en app.py)
# ===========================================================================
#
# 1) Arriba de app.py, junto a los otros imports, agrega:
#
#        import diagnostico
#
# 2) Reemplaza el bloque de debug que hoy está suelto en app.py
#    (el que empieza con `if st.query_params.get("debug"):` y hace `st.json({...})`)
#    por esta sola línea:
#
#        diagnostico.panel_entorno(modo_demo, reporte)
#
# 3) Justo ANTES del bloque "VERIFICACIÓN DE DATOS VACÍOS"
#    (la línea `if df_f.empty:`), agrega:
#
#        diagnostico.mostrar_panel_etapas(reporte, df, df_f, faltantes_aviso)
#
# Listo. Los paneles solo aparecen cuando abres la página con ?debug=1 en la
# URL; en uso normal no se ven. (La función aviso_rapido de más abajo es
# OPCIONAL y siempre visible; sus instrucciones están junto a ella.)
#
# ===========================================================================

import streamlit as st
import pandas as pd


# ===========================================================================
# CHEQUEO DE SALUD (función pura, reutilizable)
# ===========================================================================

def revisar_datos(df):
    """
    Revisa un DataFrame y devuelve una lista de hallazgos sobre cosas que
    suelen impedir que AgGrid muestre las filas. Es PURA: no dibuja nada,
    solo devuelve la lista para que otra parte la muestre.

    Cada hallazgo es un dict: {"nivel": "alerta" | "info", "mensaje": "..."}.
    Lista vacía = no se detectó nada raro.
    """
    hallazgos = []

    if df is None:
        hallazgos.append({"nivel": "alerta",
                          "mensaje": "No hay datos (el DataFrame es None)."})
        return hallazgos

    n_filas = len(df)

    # --- 1) Columnas con el MISMO nombre -----------------------------------
    # Dos columnas que se llaman igual suelen dejar la tabla AgGrid en blanco,
    # aunque una tabla simple (como el Inspector) las muestre sin problema.
    duplicadas = df.columns[df.columns.duplicated()].unique().tolist()
    for nombre in duplicadas:
        veces = int((df.columns == nombre).sum())
        hallazgos.append({
            "nivel": "alerta",
            "mensaje": (f"Columna repetida: «{nombre}» aparece {veces} veces. "
                        "AgGrid suele mostrar la tabla vacía. "
                        "Solución: renombrar o eliminar la columna repetida."),
        })

    # Recorremos por POSICIÓN para que funcione aunque haya nombres repetidos
    # (df[c] sería ambiguo en ese caso; df.iloc[:, i] siempre da una columna).
    columnas_vacias = []
    columnas_texto_numerico = []

    for i in range(df.shape[1]):
        nombre = df.columns[i]
        serie = df.iloc[:, i]

        # --- 2) Columnas de fecha (datetime) -------------------------------
        # AgGrid puede no renderizar las filas cuando hay columnas de fecha
        # sin un trato especial (Requerimientos ya las maneja aparte).
        try:
            if pd.api.types.is_datetime64_any_dtype(serie):
                hallazgos.append({
                    "nivel": "alerta",
                    "mensaje": (f"«{nombre}» es de tipo fecha (datetime). Puede impedir "
                                "que AgGrid muestre las filas. Solución: convertirla a texto "
                                "antes de la tabla, o desactivarle el filtro (como Requerimientos)."),
                })
                continue
        except Exception:
            pass

        # --- 3) Columnas 100% vacías ---------------------------------------
        try:
            if n_filas > 0 and serie.isna().all():
                columnas_vacias.append(str(nombre))
                continue
        except Exception:
            pass

        # --- 4) Texto que en realidad parece numérico ----------------------
        try:
            if serie.dtype == object:
                muestra = serie.dropna().astype(str).head(200)
                if len(muestra) >= 5:
                    limpios = muestra.str.replace(",", "", regex=False)
                    proporcion = pd.to_numeric(limpios, errors="coerce").notna().mean()
                    if proporcion >= 0.9:
                        columnas_texto_numerico.append((str(nombre), proporcion))
        except Exception:
            pass

    # Resúmenes (para no llenar la pantalla si hay muchas columnas)
    if columnas_vacias:
        lista = ", ".join(f"«{c}»" for c in columnas_vacias)
        hallazgos.append({
            "nivel": "info",
            "mensaje": f"Columnas 100% vacías (todos los valores nulos): {lista}.",
        })

    for nombre, proporcion in columnas_texto_numerico:
        hallazgos.append({
            "nivel": "info",
            "mensaje": (f"«{nombre}» es texto pero parece numérica "
                        f"({proporcion * 100:.0f}% de los valores son números). "
                        "Si debería sumar o filtrarse como número, conviértela a número."),
        })

    return hallazgos


# ===========================================================================
# PANEL DE ETAPAS  (solo aparece con ?debug=1)
# ===========================================================================

def mostrar_panel_etapas(reporte, df_cargado, df_final, columnas_faltantes=None):
    """
    Muestra, para el reporte actual, cuántas filas y columnas hay en cada
    etapa del recorrido de los datos, y avisa de cosas que pueden romper la
    tabla AgGrid. Sirve para ver de un vistazo (tú o la IA) en qué punto se
    cae algo. Solo se ve si abres la página con ?debug=1 en la URL.

    Parámetros:
        reporte            : nombre del reporte actual.
        df_cargado         : el DataFrame recién cargado (datos crudos).
        df_final           : el DataFrame ya filtrado, justo antes de la tabla.
        columnas_faltantes : lista de columnas que no se encontraron (opcional).
    """
    if not st.query_params.get("debug"):
        return

    filas_carga = 0 if df_cargado is None else len(df_cargado)
    cols_carga = 0 if df_cargado is None else df_cargado.shape[1]
    filas_final = 0 if df_final is None else len(df_final)
    cols_final = 0 if df_final is None else df_final.shape[1]

    estado_cols = "✅" if not columnas_faltantes else \
        "⚠️ faltan: " + ", ".join(str(c) for c in columnas_faltantes)

    etapas = [
        {"Etapa": "1 · Carga (datos crudos)",
         "Filas": f"{filas_carga:,}", "Columnas": cols_carga,
         "Estado": "✅" if filas_carga > 0 else "⚠️ sin datos"},
        {"Etapa": "2 · Columnas reconocidas",
         "Filas": "—", "Columnas": "—",
         "Estado": estado_cols},
        {"Etapa": "3 · Después de filtros",
         "Filas": f"{filas_final:,}", "Columnas": "—",
         "Estado": "✅" if filas_final > 0 else "⚠️ los filtros vaciaron todo"},
        {"Etapa": "4-5 · Datos que recibe la tabla",
         "Filas": f"{filas_final:,}", "Columnas": cols_final,
         "Estado": "✅" if filas_final > 0 else "⚠️ tabla vacía"},
    ]

    with st.expander("🔬 Diagnóstico por etapas", expanded=True):
        st.caption(f"Reporte: **{reporte}**  ·  recorrido de los datos hasta la tabla")
        st.dataframe(pd.DataFrame(etapas), use_container_width=True, hide_index=True)

        st.markdown("**Chequeo de la tabla (AgGrid):**")
        hallazgos = revisar_datos(df_final)
        if not hallazgos:
            st.success("Sin problemas detectados para AgGrid. ✅")
        else:
            for h in hallazgos:
                if h["nivel"] == "alerta":
                    st.warning(h["mensaje"])
                else:
                    st.info(h["mensaje"])


# ===========================================================================
# PANEL DE ENTORNO  (versiones; solo aparece con ?debug=1)
# ===========================================================================

def panel_entorno(modo_demo, reporte):
    """
    Muestra las versiones del entorno (python, streamlit, etc.). Es lo que
    antes estaba suelto en app.py; ahora vive aquí para tener todo el
    diagnóstico en un solo lugar. Solo se ve con ?debug=1 en la URL.
    """
    if not st.query_params.get("debug"):
        return

    import sys
    from importlib.metadata import version, PackageNotFoundError

    def _ver(paquete):
        try:
            return version(paquete)
        except PackageNotFoundError:
            return "?"

    with st.expander("🔧 Diagnóstico de entorno", expanded=False):
        st.json({
            "python": sys.version.split()[0],
            "streamlit": _ver("streamlit"),
            "streamlit-aggrid": _ver("streamlit-aggrid"),
            "pandas": _ver("pandas"),
            "plotly": _ver("plotly"),
            "duckdb": _ver("duckdb"),
            "modo_demo": modo_demo,
            "reporte": reporte,
        })


# ===========================================================================
# AVISO RÁPIDO  (OPCIONAL — siempre visible, no depende de ?debug)
# ===========================================================================

def aviso_rapido(df):
    """
    OPCIONAL. Llámala justo antes de dibujar la tabla. Si detecta algo que
    típicamente deja la tabla en blanco (columnas repetidas o de fecha),
    muestra un aviso corto. Si todo está bien, no muestra nada.

    Úsala si quieres que la app te avise SOLA, sin tener que abrir ?debug=1.
    Para conectarla, agrega esta línea en app.py justo antes de llamar a
    renderizar_aggrid_desktop:

        diagnostico.aviso_rapido(df_f)
    """
    alertas = [h for h in revisar_datos(df) if h["nivel"] == "alerta"]
    if alertas:
        st.warning("⚠️ Posible causa de tabla vacía — " + alertas[0]["mensaje"])
