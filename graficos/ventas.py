"""
graficos.ventas — dashboard de Ventas: el dispatcher de sus vistas.

«Venta vs Compra» vivía acá hasta el 2026-10-09: se quitó a pedido cuando
la reemplazó el reporte «Costos» (regla #622). Normalizaba cada línea al
primer día del rango y cruzaba compra y venta del mismo día, y en
producción ya no dibujaba la compra: buscaba la fecha de `compras.parquet`
por nombres que el parquet no tiene.
"""

import pandas as pd
import streamlit as st

import definicion_venta as dv
from graficos.base import (
    compartimento_filtros, contar_filtros, filtro_pills,
    _render_rail,
    _resolver, pila_sin_tablas, publicar_contexto_ia, rail_sin_tablas,
    renderizar_graficos_genericos, seccion_perezosa,
)
from graficos.ventas_resumen import _ventas_resumen
from graficos.ventas_comparativo import _ventas_comparativo
from graficos.ventas_horario import _ventas_horario
from graficos.ventas_mix import _ventas_mix
from graficos.ventas_platos import _ventas_platos
from graficos.ventas_meseros import _ventas_meseros
from graficos.ventas_control import _ventas_control, cortesias_de

def unico_por_item(df):
    """Una fila por ÍTEM del comprobante (regla #517 de arquitectura.md).

    `ventas.parquet` trae una fila por ítem Y POR FORMA DE PAGO: pagado con
    cheque + tarjeta, cada plato sale dos veces con su venta, su costo y su
    cantidad enteros. Sumar filas infla — medido en septiembre 2026, S/
    390.272 contra S/ 332.807 reales (+17 %); en el histórico, +22 %.

    Se queda con la primera fila de cada `Llave Local Documento Item`. Las
    filas SIN llave (22 en todo el histórico) se conservan todas: no hay con
    qué decir que son la misma. No toca el parquet ni el df cargado —
    devuelve otro df—, así que lo que analiza FORMAS DE PAGO o PROPINAS
    (Meseros, el asistente IA) sigue recibiendo las filas por pago.

    Sin la columna (demo, otro parquet) devuelve el df tal cual."""
    if df is None or df.empty:
        return df
    col = _resolver(df, ["Llave Local Documento Item"])
    if not col:
        return df
    llave = df[col]
    repetida = llave.duplicated() & llave.notna()
    return df[~repetida] if repetida.any() else df

# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py) — reemplaza el st.pills que vivia ANTES en medio
# del dashboard. Mismo patron que Compras/Ajuste.
#
# La «Tabla» esta OCULTA desde el 2026-09-23, con las de los demas reportes:
# `rail_sin_tablas` aca y `pila_sin_tablas` en `_PILA`, de a par (#507).
#
# «Mix de carta» entro el 2026-09-25 en el lugar de «Venta por dia», y ese
# mismo dia se fue «Familia/Subfamilia semanal»: la barra semanal partida por
# familia es la del Mix, que ademas baja a Subgrupo y Producto (regla #527).
# «Analisis de platos» entro ese mismo dia en lugar del Top platos del
# Resumen (#528): el ranking entre hasta 4 periodos (regla #529).
# «Historica subfamilia» se fue el 2026-09-26: la lee el mapa de calor del
# Mix en granularidad Mes (regla #541). Y ese mismo dia «Matriz agrupada»:
# su tabla es la del Mix, y lo unico que tenia propio —el % de costo por
# periodo— paso ahi (reglas #543 y #544). Y tambien «Ranking & FoodCost»: lo
# unico suyo —los platos de toda la carta con su costo al lado— paso a
# «Analisis de platos» (reglas #545 y #546).
#
# Los ROTULOS (segundo elemento) se alargaron el 2026-09-30 a pedido
# («Venta por Periodo», «Mix de Ventas», …); el id (primero) no se toco: es
# el que usan `_PILA`, las keys de los botones y el `?vista=` de la URL.
_VENTAS_RAIL_CATEGORIAS = rail_sin_tablas((
    ("Resumen",  (("Resumen ejecutivo", "Venta por Periodo", ":material/summarize:"),)),
    ("Tiempo",   (("Mix de carta",               "Mix de Ventas",           ":material/stacked_bar_chart:"),
                  ("Mapa por hora",               "Análisis por Hora",       ":material/schedule:"),
                  ("Comparativo vs Año Pasado",   "Comparación Año Pasado",  ":material/compare_arrows:"))),
    ("Análisis", (("Análisis de platos",  "Análisis de Platos",  ":material/restaurant_menu:"),
                  ("Meseros",             "Análisis de Meseros", ":material/groups:"),
                  # Lo que pasa con los pedidos antes de la venta (#594).
                  ("Control de pedidos",  "Control de Pedidos",  ":material/rule:"))),
    ("Datos",    (("Tabla",  "Tabla", ":material/table_rows:"),)),
))

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA
# tupla (el porqué está en `graficos/compras/__init__.py::_PILA`).
#
# Las 8 van en UNA sola pila: a diferencia de Ajuste, acá las categorías
# del rail ("Resumen"/"Tiempo"/"Análisis") son sólo agrupación visual y no
# separan la clave del rango — Ventas usa `carga_por_rango`, o sea UNA
# clave por reporte, la misma que decide qué se baja de R2. El rail aplana
# las categorías igual que siempre, así que la pila las lee seguidas.
_PILA = pila_sin_tablas((
    ("vt_sec_resumen",    "Resumen ejecutivo"),
    ("vt_sec_mix",        "Mix de carta"),
    ("vt_sec_hora",       "Mapa por hora"),
    ("vt_sec_ano_pasado", "Comparativo vs Año Pasado"),
    ("vt_sec_platos",     "Análisis de platos"),
    ("vt_sec_meseros",    "Meseros"),
    ("vt_sec_control",    "Control de pedidos"),
    ("vt_sec_tabla",      "Tabla"),
))


_K_DIA_RECARGA = "_ventas_dia_recarga"


def _selector_dia_venta():
    """Por qué día se fecha la venta (regla #593): el del TURNO de caja
    —el cobro de las 00:25 es del día anterior, como lo cierra el cajero—
    o el de EMISIÓN del comprobante —el del Registro de Ventas de SUNAT—.

    Cambiarlo es cambiar QUÉ se carga (`data.cargar_rango` lee esta misma
    clave), y el panel vive dentro del fragment del contenido: un rerun del
    fragment volvería a dibujar el df viejo. Por eso el cambio pide una
    corrida COMPLETA, después de que el widget quedó registrado."""
    st.markdown('<div class="filtro-rotulo filtro-ventas_dia">Fecha de la '
                'venta</div>', unsafe_allow_html=True)
    st.segmented_control(
        "Fecha de la venta", [dv.DIA_TURNO, dv.DIA_EMISION],
        default=dv.DIA_TURNO, required=True, key=dv.CLAVE_DIA,
        label_visibility="collapsed",
        on_change=lambda: st.session_state.__setitem__(_K_DIA_RECARGA, True),
        help=("**Turno de caja**: lo cobrado pasada la medianoche cuenta en "
              "el día del turno, como el cierre de caja. **Emisión · SUNAT**: "
              "en el día del comprobante, como el Registro de Ventas. Sólo "
              "cambia lo cobrado después de las 00:00 (unos 5 cobros al mes)."))
    if st.session_state.pop(_K_DIA_RECARGA, False):
        st.rerun(scope="app")


def renderizar_graficos_ventas(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Ventas: resumen ejecutivo, mix de carta por período,
    mapa por hora, año pasado, venta vs compra, análisis de platos y
    meseros. Columnas reales del parquet de ventas.

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py — igual que
    Ajuste). Se le pasa `d`, el df YA filtrado por los chips propios de
    Ventas (Grupo/Sub Grupo/Canal/Servicio) — reusarlo evita que la Tabla
    tenga un estado de filtros distinto al de los gráficos."""
    col_venta = _resolver(df_f, ["Venta Item Ddocumento", "Venta_Item_Ddocumento",
                                 "Neto Total Item Ddocumento", "Venta"])
    col_fam   = _resolver(df_f, ["Grupo"])
    col_sub   = _resolver(df_f, ["Sub Grupo", "Sub_Grupo", "Subgrupo"])
    col_fecha = _resolver(df_f, ["Fec Reg Documento", "Fec_Reg_Documento",
                                 "Fecha Registro", "FECHA"])
    col_pax   = _resolver(df_f, ["Cant Pax", "Cantidad Pax", "Pax"])
    col_pedido = _resolver(df_f, ["Llave Local Pedido", "Llave_Local_Pedido",
                                  "Nro Pedido", "Numero Pedido"])
    col_prod   = _resolver(df_f, ["Nomb Item Venta", "Nombre Producto",
                                  "Producto", "Descripcion"])
    col_cant   = _resolver(df_f, ["Cantidad Item Ddocumento", "Cantidad",
                                  "Cant Item", "Unidades"])
    col_canal  = _resolver(df_f, ["Canal Venta", "Canal_Venta",
                                  "Nomb Canal Venta", "Canal"])
    col_serv   = _resolver(df_f, ["Servicio", "Tipo Servicio",
                                  "Nomb Servicio", "Nombre Servicio"])
    col_mesero  = _resolver(df_f, ["Nombre Mesero", "Nomb Mesero"])
    if not col_fecha:
        for _c in df_f.columns:
            if pd.api.types.is_datetime64_any_dtype(df_f[_c]):
                col_fecha = _c
                break

    if not col_venta:
        st.warning("No se encontró la columna de venta. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros: el compartimento único de la franja ────────────────────
    # Aplican a TODOS los gráficos de Ventas.
    # Canal Venta y Servicio solo aparecen si su columna existe en el parquet
    # (Servicio no siempre está — se salta silenciosamente).
    # Los CUATRO en el compartimento único de la franja. Hasta el 2026-08-31
    # eran cuatro popovers en fila y un `_filtro_popover` local que existía
    # sólo para no repetirlos — ese helper es hoy `base.filtro_pills`, que
    # además dejó de necesitar el wrapper `chipwrap_<key>_on|off`: el estado
    # activo lo marca ahora el compartimento entero, no cada filtro.
    # El día de la venta (regla #593) no es un filtro, pero manda sobre las
    # mismas vistas: va en el mismo panel, y fuera del default prende el
    # contador como un filtro más, para que se note con el panel cerrado.
    _dia_otro = (st.session_state.get(dv.CLAVE_DIA, dv.DIA_TURNO)
                 != dv.DIA_TURNO)
    with compartimento_filtros(contar_filtros(
            "ventas_graf_filtro_fam", "ventas_graf_filtro_sub",
            "ventas_graf_filtro_canal", "ventas_graf_filtro_serv")
            + int(_dia_otro)):
        _selector_dia_venta()
        _, fam_sel = filtro_pills(df_f, col_fam,
                                  "ventas_graf_filtro_fam", "Grupo")
        # CASCADA: Sub Grupo sólo ofrece los que quedan bajo el Grupo elegido.
        _dd = df_f
        if fam_sel and col_fam:
            _dd = _dd[_dd[col_fam].astype(str).isin(fam_sel)]
        _, sub_sel = filtro_pills(_dd, col_sub,
                                  "ventas_graf_filtro_sub", "Sub Grupo")
        _, canal_sel = filtro_pills(df_f, col_canal,
                                    "ventas_graf_filtro_canal", "Canal Venta")
        _, serv_sel = filtro_pills(df_f, col_serv,
                                   "ventas_graf_filtro_serv", "Servicio")

    def _aplicar_chips(df):
        """Aplica los chips de la franja a CUALQUIER df de ventas, no solo al
        del rango cargado. Existe como función (y no inline) porque el
        comparativo "Año Pasado" trae su propio df desde R2 y tiene que
        quedar filtrado IGUAL que la vista actual — si no, se comparan
        barras filtradas contra barras sin filtrar. Defensiva con las
        columnas: el df del año pasado sale del mismo parquet, pero si
        alguna faltara, ese filtro se saltea en vez de reventar."""
        for _col, _sel in ((col_fam, fam_sel), (col_sub, sub_sel),
                           (col_canal, canal_sel), (col_serv, serv_sel)):
            if _sel and _col and _col in df.columns:
                df = df[df[_col].astype(str).isin(_sel)]
        return df

    # DOS GRANOS DEL MISMO df (regla #517). `d_pagos` es el parquet tal
    # cual: una fila por ítem Y por forma de pago. `d` es una fila por
    # ítem, y es lo que reciben TODAS las vistas que suman venta, costo o
    # cantidad. Sólo dos cosas miran `d_pagos`: Meseros (la propina es del
    # PAGO) y el asistente IA (que también responde por formas de pago, y
    # recibe la nota del grano en `asistente_datos.nota_de_grano`).
    #
    # Y UNA DEFINICIÓN DE VENTA (regla #524): `df_f` llega de
    # `data.cargar_rango` con la columna `CLASE VENTA` y las notas de
    # crédito como ítems negativos. `d` es sólo lo que ES venta —sin
    # cortesías ni anulados, con las notas restando— y es lo que suman las
    # vistas. `d_todo` conserva todas las clases: lo usa el Resumen, que
    # muestra cortesías y anulados aparte y arma el puente de la venta.
    if dv.columna(df_f, dv.CLASE) is None:
        # Un df que no vino de `data.cargar_rango` (los tests, una
        # herramienta): la definición se aplica acá, igual.
        df_f = dv.preparar(df_f)
    d_pagos = _aplicar_chips(df_f)
    d_todo = unico_por_item(d_pagos)
    d = dv.solo_venta(d_todo)

    def _filtrar_items(df):
        """`_aplicar_chips` + un ítem una vez + sólo venta, para los df que
        las vistas traen APARTE de R2 (Año Pasado, Mapa por hora): sin los
        dos últimos pasos, esas vistas volverían a sumar filas por pago,
        cortesías y anulados."""
        return dv.solo_venta(unico_por_item(_aplicar_chips(df)))

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Ventas", d_pagos, {
        "Grupo": fam_sel, "Sub Grupo": sub_sel,
        "Canal": canal_sel, "Servicio": serv_sel,
    })

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    # El rail ya no ELIGE: con `secciones` marca dónde estás y scrollea.
    _render_rail(_VENTAS_RAIL_CATEGORIAS, "ventas_graf_tipo",
                 btn_prefix="ventas_rail_btn_", secciones=_PILA)

    # La cadena `if graf == ...` de abajo NO se toca: pasa de vivir dentro
    # de un `with st.container(...)` compartido por las diez vistas de
    # gráfico a ser el cuerpo de esta función, que cada sección llama con
    # SU nombre de vista. Mismo movimiento que en salidas.py y
    # requerimientos.py, y por el mismo motivo: en un if/elif de 200 líneas
    # con diez cuerpos pesados, la migración segura es la que NO los toca.
    def _cuerpo_grafico(graf):

        # ── 0) Resumen ejecutivo: KPIs + candlestick diario + ticket + top
        # platos (graficos/ventas_resumen.py). Vive DENTRO de esta misma
        # card compartida (no arriba, entre chips y card) a propósito: así
        # no hace falta repetir la excepción de margin-top de la regla #38
        # de arquitectura.md — esa regla solo aplica a contenido en flujo
        # POR FUERA de `ajuste_graf_card_izq_ventas`.
        if graf == "Resumen ejecutivo":
            _ventas_resumen(d_todo, col_venta, col_fecha, col_pax, col_pedido,
                            col_prod, col_cant, col_fam=col_fam,
                            col_serv=col_serv, col_canal=col_canal,
                            col_mesero=col_mesero, d_pagos=d_pagos)

        # ── 1) Mix de carta: la venta por período partida por Grupo ›
        # Sub Grupo › Producto (graficos/ventas_mix.py, regla #527). Le pasa
        # `_filtrar_items` como a Año Pasado: el Detalle trae el año pasado
        # aparte de R2 y tiene que quedar filtrado igual que `d`.
        elif graf == "Mix de carta":
            _ventas_mix(d, filtrar_cb=_filtrar_items)

        # ── 1a-bis) Mapa de calor día × hora, hasta 4 períodos ───────────
        # Trae sus propios tramos (uno por período comparado) con
        # data.cargar_rango y les aplica _filtrar_items, igual que el
        # comparativo: el `d` de acá está acotado al rango de la franja y los
        # períodos que se comparan pueden caer fuera de él.
        elif graf == "Mapa por hora":
            _ventas_horario(d, col_venta, col_fecha, col_pax=col_pax,
                            col_pedido=col_pedido, col_prod=col_prod,
                            col_cant=col_cant, col_fam=col_fam,
                            col_sub=col_sub, filtrar_cb=_filtrar_items)

        # ── 1a) Comparativo día a día vs Año Pasado ──────────────────────
        # Trae su propio df del año pasado (data.cargar_rango) y le pasa
        # _filtrar_items para que quede filtrado igual que `d`.
        elif graf == "Comparativo vs Año Pasado":
            _ventas_comparativo(d, col_venta, col_fecha, col_pax=col_pax,
                                col_pedido=col_pedido, col_prod=col_prod,
                                col_cant=col_cant, col_fam=col_fam,
                                col_sub=col_sub, filtrar_cb=_filtrar_items)

        # ── 3) Análisis de platos: el ranking entre hasta 4 períodos
        # (graficos/ventas_platos.py, regla #529). Trae sus períodos aparte
        # de R2, así que recibe `_filtrar_items` como Año Pasado.
        elif graf == "Análisis de platos":
            _ventas_platos(d, filtrar_cb=_filtrar_items)

        # ── 4) Meseros: las propinas por mesero, como los reportes del POS
        # (graficos/ventas_meseros.py, regla #553). Recibe las filas POR
        # PAGO —la propina es del pago (#517)— y, para lo que trae aparte de
        # R2 (el mes anterior, los 12 meses), sólo los chips: los dos granos
        # los arma la vista. `firma` identifica esos chips para guardar lo
        # traído en la sesión.
        elif graf == "Meseros":
            _ventas_meseros(d_pagos, filtrar_cb=_aplicar_chips,
                            firma=(tuple(fam_sel or ()), tuple(sub_sel or ()),
                                   tuple(canal_sel or ()),
                                   tuple(serv_sel or ())))

        # ── 5) Control de pedidos: anulaciones, transferencias, tiempos de
        # mesa y ocupación (graficos/ventas_control.py, regla #594). Lee sus
        # parquets; de acá sólo le llegan los pedidos que se facturaron como
        # cortesía (para reconocer lo que se pasó a una cuenta de cortesía)
        # y el filtro de canal.
        elif graf == "Control de pedidos":
            _ventas_control(cortesias=cortesias_de(d_todo),
                            canales=tuple(canal_sel or ()))
        else:
            st.info("No hay columnas suficientes para este gráfico.")

    def _seccion(slug, nombre):
        """Envuelve una vista de gráfico en su propia tarjeta.

        Conserva el prefijo `ajuste_graf_card_` (de ahí cuelga el CSS de
        tarjeta, `estilos/_80_cards.py`) y suma el sufijo de la vista:
        antes las diez compartían `ajuste_graf_card_izq_ventas`, lo que
        funcionaba porque nunca coexistían. Apiladas serían diez widgets
        con la misma key = excepción de Streamlit."""
        def _f():
            with st.container(border=True,
                              key=f"ajuste_graf_card_izq_ventas_{slug}"):
                _cuerpo_grafico(nombre)
        return _f

    def _dib_tabla():
        with st.container(border=True, key="ajuste_graf_card_izq_ventas_tabla"):
            if tabla_cb is not None:
                tabla_cb(d)
            else:
                st.info("La tabla no está disponible en este contexto.")

    _DIBUJANTES = {
        # El Resumen arma SU tarjeta (regla #521): envuelto en una
        # `ajuste_graf_card_` se leía junto con la del Top platos, que se
        # quitó el 2026-09-25 (regla #528).
        "vt_sec_resumen":    lambda: _cuerpo_grafico("Resumen ejecutivo"),
        "vt_sec_mix":        _seccion("mix", "Mix de carta"),
        "vt_sec_hora":       _seccion("hora", "Mapa por hora"),
        "vt_sec_ano_pasado": _seccion("ano_pasado", "Comparativo vs Año Pasado"),
        # Como el Resumen, arma SUS tarjetas: la del ranking y, con un
        # plato en foco, la de su evolución debajo (regla #529).
        "vt_sec_platos":     lambda: _cuerpo_grafico("Análisis de platos"),
        # Como Platos, arma SUS tarjetas: la de la tabla, la planilla y el
        # detalle del mesero elegido (regla #553).
        "vt_sec_meseros":    lambda: _cuerpo_grafico("Meseros"),
        # Arma SU tarjeta, con sus propios parquets (pedidos y
        # transacciones, regla #594).
        "vt_sec_control":    lambda: _cuerpo_grafico("Control de pedidos"),
        "vt_sec_tabla":      _dib_tabla,
    }

    # El contenedor con la key va AFUERA del fragment: es el que observan el
    # scrollspy y la precarga. Con ocho secciones —y las de Ventas son las
    # más pesadas de la app— la carga perezosa de `seccion_perezosa` deja de
    # ser una optimización y pasa a ser lo que hace la página viable: ver su
    # docstring y arquitectura.md #211 (construir todo de una dejaba al
    # navegador sin responder en Cloud).
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
