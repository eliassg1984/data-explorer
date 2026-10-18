"""Enlaces del reporte Costos a sus fuentes, con un contexto inicial validado.

La fecha se escribe mediante estado_rango. Los filtros se siembran una vez,
antes de crear sus widgets; después quedan bajo el control del usuario.
No cambia ninguna definición de venta, consumo ni costo.
"""

import calendar
import datetime as dt
import json
from urllib.parse import urlencode

import costo_ventas as cv


def _rango(grano, clave):
    ini = dt.date.fromisoformat(clave + "-01" if grano == "mes" else clave)
    if grano == "semana":
        fin = ini + dt.timedelta(days=6)
    elif grano == "quincena" and ini.day == 1:
        fin = ini.replace(day=15)
    else:
        fin = ini.replace(day=calendar.monthrange(ini.year, ini.month)[1])
    return ini, fin


def enlaces(granos):
    """URLs por grano, período y fila. Los ajustes monetarios quedan intactos."""
    salida = {}
    for grano, datos in granos.items():
        periodos = {}
        for p in datos["periodos"]:
            ini, fin = _rango(grano, p["k"])
            urls = {}

            def agregar(fila, reporte, vista, nombre, **extra):
                params = dict(reporte=reporte, vista=vista, desde=ini.isoformat(),
                              hasta=fin.isoformat(), desde_costos="1",
                              concepto=fila, **extra)
                urls[fila] = {"url": "?" + urlencode(params), "nombre": nombre}

            for fila, sub in (("v", "Venta"), ("pos", "Costo"),
                              ("pos_aj", "Costo"), ("cort", "Cortesías"),
                              ("desc", "Descuentos")):
                agregar(fila, "Ventas", "resumen_ejecutivo",
                        f"Ventas · {sub}", subvista=sub)
            agregar("c", "Compras", "compras_por_periodo", "Compras por período")
            for tipo in datos.get("salidas", {}):
                fila = "bajas" if tipo == cv.BAJAS else f"s_{tipo}"
                agregar(fila, "Movimientos", "salidas_por_periodo",
                        f"Salidas · {tipo}", tipo_salida=tipo)
            for fila, fecha in (("ii", ini - dt.timedelta(days=1)), ("fi", fin)):
                if grano == "mes":
                    agregar(fila, "Ajuste de Inventario", "diferencias",
                            "Detalle del cierre de inventario",
                            mes_cierre=fecha.strftime("%Y-%m"))
                else:
                    agregar(fila, "Inventario Valorizado", "productos",
                            "Stock histórico por producto", fecha_stock=fecha.isoformat())
            if grano == "mes":
                for fila in ("dif", "falt"):
                    agregar(fila, "Ajuste de Inventario", "diferencias",
                            "Investigar diferencias del cierre",
                            mes_cierre=fin.strftime("%Y-%m"))
            periodos[p["k"]] = urls
        salida[grano] = periodos
    return salida


def _lista(params, nombre, permitidos):
    try:
        valores = json.loads(params.get(nombre, "[]"))
    except (TypeError, ValueError):
        return []
    return [x for x in valores if isinstance(x, str) and x in permitidos] if isinstance(valores, list) else []


def _contexto(params, reporte):
    if params.get("desde_costos") != "1" or params.get("reporte") != reporte:
        return None
    vistas = {"Ventas": "resumen_ejecutivo", "Compras": "compras_por_periodo",
              "Movimientos": "salidas_por_periodo", "Ajuste de Inventario": "diferencias",
              "Inventario Valorizado": "productos"}
    if params.get("vista") != vistas.get(reporte):
        return None
    try:
        ini = dt.date.fromisoformat(params.get("desde", ""))
        fin = dt.date.fromisoformat(params.get("hasta", ""))
    except (TypeError, ValueError):
        return None
    if ini > fin or (fin - ini).days > 366:
        return None
    return ini, fin


def aplicar_contexto(reporte, df=None):
    """Inicializa fechas antes de cargar y filtros después, una vez por URL."""
    import streamlit as st
    from estado_rango import aplicar_atajo, clave_rango, restaurar_eco

    params = st.query_params
    rango = _contexto(params, reporte)
    if rango is None:
        return
    firma = tuple((k, params.get(k, "")) for k in (
        "reporte", "vista", "desde", "hasta", "concepto", "familias", "extras",
        "subvista", "tipo_salida", "mes_cierre", "fecha_stock"))
    fase = "filtros" if df is not None else "fecha"
    marca = f"_costos_enlace_{fase}"
    if st.session_state.get(marca) == firma:
        return
    if df is None:
        categoria = {"Compras": "sec_semanal", "Movimientos": "sal_periodo"}.get(reporte)
        if reporte in ("Ventas", "Compras", "Movimientos"):
            carga = reporte == "Ventas"
            clave = clave_rango(reporte, carga, categoria)
            aplicar_atajo(clave, rango, reporte, carga)
            restaurar_eco(clave)
        st.session_state[marca] = firma
        return

    familias = _lista(params, "familias", cv.CUBETAS)
    extras = _lista(params, "extras", cv.GRUPOS_APARTE.values())
    if reporte == "Movimientos":
        import data
        fuente = data.cargar("salidas.parquet")
    else:
        fuente = df
    if fuente is None:
        return
    mapa = cv.GRUPOS_VENTA if reporte == "Ventas" else cv.FAMILIAS
    columnas = {cv._norm(c): c for c in fuente.columns}
    col = next((columnas[c] for c in (
        "GRUPO CARTA", "GRUPO", "FAMILIA", "NOMBRE FAMILIA") if c in columnas), None)
    if reporte == "Ventas":
        import definicion_venta
        col = definicion_venta.columna(fuente, definicion_venta.GRUPO)
    elegidas = []
    if col:
        elegidas = [v for v in fuente[col].dropna().astype(str).unique()
                    if mapa.get(cv._norm(v)) in familias
                    or (reporte == "Ventas" and cv.GRUPOS_APARTE.get(cv._norm(v)) in extras)]
    if reporte == "Ventas":
        st.session_state["vt_resumen_grupo"] = elegidas
        sub = params.get("subvista", "Venta")
        if sub in ("Venta", "Costo", "Cortesías", "Descuentos"):
            st.session_state["vt_resumen_modo"] = "Resumen"
            st.session_state["vt_resumen_sub"] = sub
            st.session_state["_vt_resumen_sub_eco"] = sub
    elif reporte == "Compras":
        st.session_state["compras_sem_familias"] = elegidas
    elif reporte == "Movimientos":
        st.session_state["mov_psal_familias"] = elegidas
        st.session_state["mov_sal_fecha"] = "Registro"
        tipo_col = columnas.get("TIPO DESCARGO")
        tipo = params.get("tipo_salida", "")
        if tipo_col and tipo in set(fuente[tipo_col].dropna().astype(str).str.strip()):
            st.session_state["mov_psal_tipos"] = [tipo]
    elif reporte == "Ajuste de Inventario":
        st.session_state["ajdif_filtro_familia"] = elegidas
        fecha_col = columnas.get("FECHA APERTURA INVENTARIO")
        if fecha_col:
            from cortes import sesiones_inventario
            mes = params.get("mes_cierre", "")
            sesion = next((s for s in sesiones_inventario(fuente[fecha_col])
                           if s["tipo"] == "cierre" and s["clave"] == f"cierre_{mes}"), None)
            if sesion:
                st.session_state["ajdif_sesion"] = sesion["clave"]
            else:
                st.info(f"El cierre solicitado ({mes}) no aparece entre las sesiones disponibles.")
    elif reporte == "Inventario Valorizado":
        st.session_state["inv_prod_familias"] = elegidas
        st.session_state["inv_prod_areas"] = []
        try:
            fecha = dt.date.fromisoformat(params.get("fecha_stock", ""))
        except (TypeError, ValueError):
            fecha = None
        if fecha:
            st.session_state["inv_prod_a_fecha"] = True
            st.session_state["inv_prod_fecha"] = fecha
            st.session_state["inv_prod_hora"] = 23
    st.session_state[marca] = firma
