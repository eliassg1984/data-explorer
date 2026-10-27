"""graficos.costos — dashboard del reporte «Costos».

REPORTE NUEVO EL 2026-10-09, a pedido, sobre un boceto con datos reales
(https://claude.ai/artifact/3NYnyS7axe6u5woDiyiZBD) y la planilla con la
que el usuario ya llevaba el costo a mano. Una vista: «Costo de ventas», el
estado mensual de inventario inicial + compras − inventario final, las
salidas que no se vendieron, el consumo operativo y el consumo carta, y la
comparación del consumo carta contra el costo que dice el POS.

Va como reporte propio y no como vista de otro porque cruza CUATRO fuentes y
ninguna es su dueña: los cierres de inventario (el `archivo` del reporte),
las compras, las notas de salida y la venta por grupo de carta. La cuenta
vive en `costo_ventas.py` (pura, con su test); este módulo la arma, la
cachea y la entrega.

LA TABLA ES UNA PIEZA PROPIA (`st.components.v2`, como el panel de fecha de
la regla #616): HTML, CSS y JavaScript sin iframe, en `costos_tabla.js` y
`costos_tabla.css`. Todo lo que se elige ahí —familias, Eventos y Venta
interna, qué salidas restar, qué fila abrir— lo resuelve el navegador: los
datos son pocos (meses × filas × cuatro familias) y viajan enteros, así que
nada de eso recalcula la página.

SIN PILA, como Documentos SUNAT (regla #577): una tarjeta, `secciones=()`.
La tarjeta no lleva techo de alto (`estilos/_80_cards.py`): al abrir una
fila la tabla crece, y con techo la tarjeta sacaría barra propia (#382).

Regla #622.
"""

from graficos.movil import css_movil, js_movil
import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

import convenios_descuento
import presupuesto_ventas
import costo_ventas
import costos_enlaces
import navegacion_retorno
import costos_calidad
import data
import definicion_venta
import kardex
from graficos.base import (
    _render_rail, pila_sin_tablas, publicar_contexto_ia, rail_sin_tablas,
)

# Una sola vista: «Costo de ventas», con descuentos comerciales separados
# desde el 2026-10-19 (regla #676). El id sigue siendo «Costo de
# ventas»: renombrar es cambiar sólo el rótulo. El rail se declara igual —con `rail_sin_tablas`, como
# todos (regla #507)— porque de él salen el panel del reporte en la columna
# (`graficos/__init__.py::_RAILS`, regla #568) y el rótulo de la franja.
#
# Desde el 2026-10-21, dos vistas (regla #686): «Consistencia de datos»
# es un DESTINO APARTE, como las de Documentos SUNAT (#683) —el rail elige
# cuál se dibuja—, no una pila: cada una es una tarjeta alta.
_COSTOS_RAIL_CATEGORIAS = rail_sin_tablas((
    ("Costos", (("Costo de ventas", "Costo de ventas", ":material/calculate:"),
                ("Consistencia de datos", "Consistencia de datos",
                 ":material/rule:"))),
))

# Vacía y no ausente: `_render_rail` distingue `secciones=()` («destino
# aparte») de `secciones=None`. Ver `graficos/sunat_reporte.py`.
_PILA = pila_sin_tablas(())

_ARCHIVOS = ("compras.parquet", "salidas.parquet", "ventas.parquet",
             "notascreditocompras.parquet", "inventariovalorizado.parquet", kardex.ARCHIVO)

K_MES_DESDE_RESUMEN = "_costos_mes_desde_resumen"
"""El mes con que abre «Costo de ventas» al llegar desde la portada de
Inicio, con su ámbito (regla #745). Se lee una vez."""

_AQUI = Path(__file__).parent
_TABLA = st.components.v2.component(
    "costos_tabla",
    css=css_movil((_AQUI / "costos_tabla.css").read_text(encoding="utf-8")),
    # Un solo módulo: los paneles y las dos vistas de arriba (regla #679)
    # definen funciones que usa `costos_tabla.js`, que exporta el default.
    js=js_movil("\n".join((_AQUI / f).read_text(encoding="utf-8")
                  for f in ("costos_paneles.js", "costos_vistas.js", "costos_tabla.js"))),
)


def _ultimo_dia_completo(fotos, ventas):
    """El último día con datos ENTEROS en el kardex y en la venta: el día
    anterior al menor de sus topes (la corrida de la madrugada trae algo del
    día en curso)."""
    topes = [pd.to_datetime(fotos["fecha"]).max(), pd.to_datetime(ventas["dia"]).max()]
    topes = [t for t in topes if pd.notna(t)]
    return min(topes).date() - dt.timedelta(days=1) if topes else None


@st.cache_data(ttl=3600, show_spinner=False)
def _datos(_ajuste, sellos, version, convenios=None):
    """Los tres granos de la tabla: `{"granos": {"mes": …, "quincena": …,
    "semana": …}}`. El mes, con los cierres (`costo_ventas.armar`); la
    quincena y la semana, con el kardex (`armar_kardex`). Si falta compras,
    salidas o ventas, LANZA: una tabla con la venta en cero no se cachea.
    Sin kardex o sin maestro sigue sólo con el mes.

    `_ajuste` no entra en la clave (el guion bajo): lo identifica su sello,
    que va en `sellos` junto con los de los demás, y `version` lleva las de
    la cuenta, la definición de venta y el kardex. Sólo en memoria: lo
    pesado —cada parquet— ya está en la caché de disco de `data.py`.

    `convenios` es la tabla de `convenios_descuento` (regla #665): entra en
    la clave, así que guardarla recalcula la tabla, sin volver a la venta."""
    compras = data.cargar("compras.parquet")
    salidas = data.cargar("salidas.parquet")
    ventas = data.venta_por_grupo_dia()
    faltan = [n for n, d in (("compras", compras), ("salidas", salidas),
                             ("ventas", ventas)) if d is None]
    if faltan:
        raise RuntimeError("no se pudo leer: " + ", ".join(faltan))
    granos = {"mes": costo_ventas.armar(_ajuste, compras, salidas, ventas,
                                        convenios)}
    fotos = data.kardex_fotos()
    maestro = data.cargar("inventariovalorizado.parquet")
    if fotos is not None and not fotos.empty and maestro is not None and not ventas.empty:
        # Lo activo, la misma regla que Stock (#598).
        from graficos.inventario import separar_activos
        base = costo_ventas.base_activa(separar_activos(maestro)[0])
        hasta = _ultimo_dia_completo(fotos, ventas)
        if hasta:
            for grano in ("quincena", "semana"):
                granos[grano] = costo_ventas.armar_kardex(
                    grano, fotos, base, compras, salidas, ventas, hasta, convenios)
    return {"granos": granos}


@st.cache_data(ttl=3600, show_spinner=False)
def _cobertura_documental(periodos, sellos, version=1):
    """Mismo cruce de Documentos SUNAT, sólo del registro cargado; sin XML/API.

    Fallar lanza y no se cachea como cero. Los documentos se comparan con
    compras brutas más sus notas propias, antes de filtrar estados/familias.
    """
    from graficos.compras import documentos_sunat as documentos
    registro = data.cargar("sunat_compras.parquet")
    compras = data.cargar("compras.parquet", notas_credito=False)
    notas = data.notas_credito_compras()
    if registro is None or compras is None or notas is None:
        raise RuntimeError("No se pudo leer el control documental")
    if registro.empty or "fecha_emision" not in registro:
        return {}
    fechas = pd.to_datetime(registro["fecha_emision"], errors="coerce")
    resultado = {}
    for clave in periodos:
        mes = pd.Period(clave, freq="M")
        ini, fin = mes.start_time.date(), mes.end_time.date()
        reg = registro[fechas.dt.to_period("M") == mes]
        if reg.empty:
            resultado[clave] = {"disponible": False}
            continue
        agrupado = documentos._parquet_agrupado_por_documento(
            compras, "FECHA_EMISION_DOC", ini, fin, notas=notas)
        resultado[clave] = costos_calidad.cobertura_documental(
            documentos.cruzar_con_parquet(reg, agrupado))
    return resultado


def renderizar_graficos_costos(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard «Costos»: el rail de una vista + la tabla del costo de ventas.

    `df_f` son los cierres de inventario (`ajusteinventario.parquet`, el
    `archivo` del reporte), sin filtro de fecha: el reporte no tiene. El
    resto lo trae `_datos`. `tabla_cb` se acepta por la firma única del
    dispatcher y no se usa: el reporte no tiene vista «Tabla»."""
    vista = _render_rail(_COSTOS_RAIL_CATEGORIAS, "costos_graf_tipo", secciones=_PILA)
    if vista == "Consistencia de datos":
        from graficos import costos_consistencia
        costos_consistencia.renderizar()
        return
    ajuste = df_full if df_full is not None else df_f
    sellos = (data.sello_datos("ajusteinventario.parquet"),
              *(data.sello_datos(a) for a in _ARCHIVOS))
    version = (costo_ventas.VERSION, definicion_venta.VERSION, kardex.VERSION)
    convenios = convenios_descuento.leer()
    with st.container(border=True, key="ajuste_graf_card_izq_costos"):
        try:
            # La primera vez de cada versión de los parquets baja la venta
            # entera para agruparla (unos 15 s); después sale de la caché.
            with st.spinner("Calculando el costo de ventas…"):
                datos = _datos(ajuste, sellos, version, convenios)
            mes = datos["granos"]["mes"]
        except Exception as e:
            st.warning(f"No se pudo armar el costo de ventas ({e}). "
                       "Reintentá en unos segundos.")
            return
        if not mes["periodos"]:
            st.info("No hay meses desde 2024 con inventario inicial, final "
                    "y cobertura de ventas para calcular este reporte.")
            return
        documental = {}
        if data.secrets_disponibles():
            try:
                archivos = ("sunat_compras.parquet", "compras.parquet",
                            "notascreditocompras.parquet")
                documental = _cobertura_documental(
                    tuple(p["k"] for p in mes["periodos"]),
                    tuple(data.sello_datos(a) for a in archivos))
            except Exception:
                # Su falta no transforma documentos pendientes en cero y
                # tampoco impide leer el estado de costos.
                documental = {}
        # El asistente responde sobre lo que suma la tabla, no sobre los
        # cierres sueltos que llegan en `df_f`.
        publicar_contexto_ia("Costos", costo_ventas.tabla_larga(mes))
        # Enlace del Resumen: abre Mes con el período y los defaults que
        # resume la portada. No altera las preferencias guardadas de Costos.
        # Desde la regla #745 la portada salta en la MISMA pestaña: deja el
        # mes una vez en `K_MES_DESDE_RESUMEN`, que la tabla toma al montarse.
        salto = st.session_state.pop(K_MES_DESDE_RESUMEN, None)
        mes_enlace = salto or st.query_params.get("mes", "")
        desde_resumen = ((salto is not None or st.query_params.get("desde_resumen") == "1")
                          and any(p["k"] == mes_enlace for p in mes["periodos"]))
        _TABLA(key="costos_tabla", data=dict(
            datos, documental=documental, enlaces=costos_enlaces.enlaces(datos["granos"]),
            retorno=navegacion_retorno.enlace_desde_aqui(),
            mes_inicial=mes_enlace if desde_resumen else None,
            desde_resumen=desde_resumen), width="stretch")
    # Los dos editores, lado a lado y no como franjas a todo el ancho
    # (regla #679): cerrados son dos renglones cortos.
    # columnas-internas: dos desplegables de configuración, no un drill.
    c_conv, c_ppto = st.columns(2)
    with c_conv:
        _editor_convenios(convenios)
    with c_ppto:
        _editor_presupuesto()


_ACUSE_CONVENIOS = "_costos_conv_acuse"
_ACUSE_PPTO = "_costos_ppto_acuse"
_MESES = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set",
          "Oct", "Nov", "Dic")


def _editor_presupuesto():
    """El presupuesto de venta por mes y servicio (regla #669): lo compara
    Ventas › Comparación Año Pasado. Mismo patrón que los convenios: se
    edita acá, se guarda en R2 (`presupuesto_ventas`), el acuse va por
    `session_state` (#474) y la key del editor lleva la huella."""
    t = presupuesto_ventas.leer()
    with st.expander(f"Presupuesto de venta · {t['anio'].nunique()} años"
                     if len(t) else "Presupuesto de venta · sin cargar",
                     expanded=False, key="costos_ppto"):
        acuse = st.session_state.pop(_ACUSE_PPTO, None)
        if acuse:
            (st.success if acuse[0] else st.error)(acuse[1])
        st.caption(
            "Venta bruta y neta presupuestada, por mes y servicio. Ventas › "
            "Comparación Año Pasado la muestra al lado de la venta: el mes "
            "exacto, la semana y el día repartidos según la venta de cada "
            "día de la semana en ese mes del año anterior.")
        tabla = pd.DataFrame({
            "Año": t["anio"].astype(int), "Mes": [_MESES[m - 1] for m in t["mes"]],
            "Servicio": t["servicio"].str.capitalize(),
            "Venta bruta": t["bruta"], "Venta neta": t["neta"],
        })
        editada = st.data_editor(
            tabla, key=f"costos_ppto_ed_{presupuesto_ventas.huella(t)}",
            num_rows="dynamic", hide_index=True, width="stretch",
            column_config={
                "Año": st.column_config.NumberColumn(
                    "Año", min_value=2020, max_value=2100, step=1, format="%d",
                    required=True),
                "Mes": st.column_config.SelectboxColumn(
                    "Mes", options=list(_MESES), required=True),
                "Servicio": st.column_config.SelectboxColumn(
                    "Servicio", options=["Almuerzo", "Cena", "Desayuno"],
                    required=True),
                "Venta bruta": st.column_config.NumberColumn(
                    "Venta bruta", min_value=0, format="%,.2f"),
                "Venta neta": st.column_config.NumberColumn(
                    "Venta neta", min_value=0, format="%,.2f"),
            })
        if not data.secrets_disponibles():
            st.caption("Sin conexión a R2: la tabla no se puede guardar.")
            return
        if st.button("Guardar presupuesto", key="costos_ppto_guardar",
                     type="primary"):
            filas = [{"anio": r[0], "mes": _MESES.index(r[1]) + 1
                      if r[1] in _MESES else None, "servicio": r[2],
                      "bruta": r[3], "neta": r[4]}
                     for r in editada.itertuples(index=False)]
            ok = presupuesto_ventas.guardar(filas)
            n = len(presupuesto_ventas.normalizar(filas))
            st.session_state[_ACUSE_PPTO] = (
                ok, f"Guardadas {n} filas de presupuesto." if ok else
                "No se pudo guardar en R2. Reintentá en unos segundos.")
            st.rerun()


def _rotulo(cod, nombre):
    return f"{cod} · {nombre}" if nombre else cod


def _editor_convenios(convenios):
    """La tabla de convenios con devolución del banco (regla #665): qué
    parte de un descuento le devuelve el banco al restaurante. Se edita
    acá y se guarda en R2 (`convenios_descuento`); el costo de descuentos
    de la tabla de arriba ya la descuenta.

    El acuse del guardado viaja por `session_state` y lo pinta la corrida
    siguiente: un `st.toast` antes de un `st.rerun` no se ve nunca (#474).
    La key del editor lleva la huella de la tabla, así que después de
    guardar arranca de lo guardado y no de lo que quedó tipeado."""
    cat = convenios_descuento.catalogo()
    for r in convenios.itertuples():
        cat.setdefault(r.codigo, r.nombre)
    rotulos = [_rotulo(c, n) for c, n in sorted(cat.items())]
    por_rotulo = {_rotulo(c, n): (c, n) for c, n in cat.items()}
    n = len(convenios)
    with st.expander(f"Convenios con devolución del banco · {n}",
                     expanded=False, key="costos_conv"):
        acuse = st.session_state.pop(_ACUSE_CONVENIOS, None)
        if acuse:
            (st.success if acuse[0] else st.error)(acuse[1])
        st.caption(
            "Lo que el banco le devuelve al restaurante de un descuento de "
            "convenio: si devuelve la mitad, un plato al 50 % regala un "
            "cuarto de su costo y no la mitad. Baja el «Costo de descuentos» de la tabla "
            "y entra en el «% costo» de Ventas › Mix de carta. «Desde» y "
            "«Hasta» vacíos: sin límite. El POS no guarda este dato.")
        tabla = pd.DataFrame({
            "Descuento": [_rotulo(r.codigo, cat.get(r.codigo) or r.nombre)
                          for r in convenios.itertuples()],
            "% devolución": [round(float(r.devolucion) * 100, 2)
                             for r in convenios.itertuples()],
            "Desde": [r.desde for r in convenios.itertuples()],
            "Hasta": [r.hasta for r in convenios.itertuples()],
        })
        tabla["Desde"] = pd.to_datetime(tabla["Desde"])
        tabla["Hasta"] = pd.to_datetime(tabla["Hasta"])
        editada = st.data_editor(
            tabla, key=f"costos_conv_ed_{convenios_descuento.huella(convenios)}",
            num_rows="dynamic", hide_index=True, width="stretch",
            column_config={
                "Descuento": st.column_config.SelectboxColumn(
                    "Descuento", options=rotulos, required=True, width="large",
                    help="El descuento del POS, por su código"),
                "% devolución": st.column_config.NumberColumn(
                    "% devolución", min_value=0, max_value=100, step=1,
                    format="%.0f %%", required=True,
                    help="Qué parte del descuento devuelve el banco"),
                "Desde": st.column_config.DateColumn("Desde", format="DD/MM/YYYY"),
                "Hasta": st.column_config.DateColumn("Hasta", format="DD/MM/YYYY"),
            })
        if not data.secrets_disponibles():
            st.caption("Sin conexión a R2: la tabla no se puede guardar.")
            return
        if st.button("Guardar convenios", key="costos_conv_guardar",
                     type="primary"):
            filas = []
            for r in editada.itertuples(index=False):
                cod, nombre = por_rotulo.get(r[0], (None, None))
                if cod is None or pd.isna(r[1]):
                    continue
                filas.append({"codigo": cod, "nombre": nombre,
                              "devolucion": float(r[1]) / 100.0,
                              "desde": r[2], "hasta": r[3]})
            ok = convenios_descuento.guardar(filas)
            st.session_state[_ACUSE_CONVENIOS] = (
                ok, f"Guardados {len(filas)} convenios." if ok else
                "No se pudo guardar en R2. Reintentá en unos segundos.")
            st.rerun()
