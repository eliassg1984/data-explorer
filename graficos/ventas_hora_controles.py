"""Contexto compartido por Patrones, Comparar y Franjas de Análisis por Hora.

Los filtros de datos viven aquí; la representación del mapa y la selección
del horario pertenecen a cada modo. Cambiar de modo conserva el rango, los
canales, el ámbito y la base temporal.
"""

from functools import partial

import pandas as pd
import streamlit as st

from data import REPORTES, cargar_rango
from graficos.base import (_resolver, ctx_rango_propio, rango_tarjeta,
                           seleccion_multiple, selector_fecha_tarjeta)
from inyecciones._iframe import inyectar_html

CATEGORIA = "vt_hora"
BASES = ("Hora del pedido", "Hora del comprobante")
TODOS = "Toda la carta"
KEYS = ("vh_canal", "vh_ambito", "vh_op_hora", "vh_raros")
FILTROS_ABIERTOS = "_vh_filtros_abiertos"
AMPLIADO = "_vh_detalle_ampliado"


def alternar_filtros():
    st.session_state[FILTROS_ABIERTOS] = not st.session_state.get(FILTROS_ABIERTOS, False)


def alternar_ampliado():
    st.session_state[AMPLIADO] = not st.session_state.get(AMPLIADO, False)


def actualizar_estado(holder, ampliado=None):
    """Clases locales: los widgets siguen montados al plegar o ampliar."""
    if ampliado is not None:
        st.session_state[AMPLIADO] = bool(ampliado)
    clases = ["vh-estado"]
    if not st.session_state.get(FILTROS_ABIERTOS, False):
        clases.append("vh-filtros-cerrados")
    if st.session_state.get(AMPLIADO, False):
        clases.append("vh-detalle-ampliado")
    holder.markdown(f'<span class="{" ".join(clases)}"></span>',
                     unsafe_allow_html=True)


def filtrar(df, *, canales=(), ambito=TODOS, incluir=True):
    """Recorta ítems sin cambiar la definición común de venta del reporte."""
    if df is None or df.empty:
        return df
    canal = _resolver(df, ["Canal Venta", "Canal_Venta", "Canal"])
    grupo = _resolver(df, ["Grupo"])
    sub = _resolver(df, ["Sub Grupo", "Sub_Grupo", "Subgrupo"])
    mask = pd.Series(True, index=df.index)
    if canales:
        mask &= df[canal].isin(canales) if canal else False
    if ambito != TODOS:
        prefijo, _, valor = ambito.partition(": ")
        columna = {"Grupo": grupo, "Subgrupo": sub}.get(prefijo)
        mask &= df[columna].astype(str).eq(valor) if columna else False
    if not incluir and grupo:
        mask &= ~df[grupo].isin(("Venta Interna", "Eventos"))
    return df.loc[mask]


def _aplicar(df, original, **filtros):
    return filtrar(original(df) if original is not None else df, **filtros)


def medir_cabecera():
    """La resta del detalle usa el alto real, también si los filtros se envuelven."""
    inyectar_html("""<script>
    (() => {
      const doc = window.parent.document;
      const node = doc.querySelector('.st-key-vh_controles');
      if (!node) return;
      const update = () => {
        const value = Math.ceil(node.getBoundingClientRect().height) + 'px';
        if (doc.documentElement.style.getPropertyValue('--vh-cab-alto') !== value)
          doc.documentElement.style.setProperty('--vh-cab-alto', value);
      };
      const obs = new ResizeObserver(update);
      obs.observe(node); update();
      window.addEventListener('pagehide', () => obs.disconnect(), {once:true});
    })();
    </script>""")


def medir_panel():
    """Reserva el espacio desde el borde real del detalle hasta la ventana."""
    inyectar_html("""<script>
    (() => {
      const doc = window.parent.document;
      let pending = false;
      const update = () => {
        pending = false;
        const panel = doc.querySelector('.st-key-vh_panel_drill');
        if (!panel) return;
        const value = Math.max(0, window.parent.innerHeight -
          Math.max(0, panel.getBoundingClientRect().top) - 16) + 'px';
        if (panel.style.getPropertyValue('--vh-panel-disponible') !== value)
          panel.style.setProperty('--vh-panel-disponible', value);
      };
      const schedule = () => {
        // El iframe es invisible: su propio RAF puede quedar suspendido.
        if (!pending) { pending = true; window.parent.requestAnimationFrame(update); }
      };
      const obs = new ResizeObserver(schedule);
      const section = doc.querySelector('.st-key-vt_sec_hora');
      obs.observe(section || doc.body);
      const changes = new MutationObserver(schedule);
      changes.observe(section || doc.body, {childList:true, subtree:true,
                                            attributes:true, attributeFilter:['class']});
      window.parent.addEventListener('resize', schedule);
      doc.addEventListener('scroll', schedule, true);
      update();
      window.addEventListener('pagehide', () => {
        obs.disconnect();
        changes.disconnect();
        window.parent.removeEventListener('resize', schedule);
        doc.removeEventListener('scroll', schedule, true);
      }, {once:true});
    })();
    </script>""")


def cabecera(d, col_fecha, col_pedido, ancla, filtrar_cb, interruptor):
    """Dibuja título, modo y filtros, y devuelve su contexto para el cuerpo."""
    with st.container(horizontal=True, vertical_alignment="center",
                      gap="medium", key="vh_cabecera"):
        with st.container(key="vh_titulo_caja", width="content"):
            st.markdown('<h3 class="vh-titulo">Análisis por hora</h3>',
                        unsafe_allow_html=True)
        with st.container(key="vh_navegacion", width="content"):
            interruptor()

    ctx = ctx_rango_propio()
    st.session_state.pop("vh_fecha_cambio", None)
    rng = (rango_tarjeta(CATEGORIA, ctx) if ctx else None) or (
        ancla.replace(day=1), ancla)
    rng = (rng[0], min(rng[1], ancla))
    ss = st.session_state
    estado = st.empty()
    actualizar_estado(estado)
    # Conserva la base y las marcas de las sesiones abiertas antes del cambio
    # de nombre: esa hora siempre fue la del comprobante, no la del pago.
    for key in ("vh_op_hora", "vh_hora_aplicada"):
        if ss.get(key) == "Hora del cobro":
            ss[key] = BASES[1]
    if ss.get("vh_op_hora") not in BASES:
        ss["vh_op_hora"] = BASES[0] if col_pedido else BASES[1]
    if not col_pedido:
        ss["vh_op_hora"] = BASES[1]

    # El listado sale del rango de ESTA vista, antes de sus filtros locales.
    # El mismo loader cacheado sirve luego al mapa: no se consulta el histórico.
    col_tiempo = col_pedido if ss["vh_op_hora"] == BASES[0] else col_fecha
    cfg = REPORTES.get("Ventas", {})
    with st.spinner("Preparando los filtros…"):
        opciones = cargar_rango(cfg.get("archivo", "ventas.parquet"),
                                col_tiempo, *rng)
        if opciones is None:
            opciones = d
        if filtrar_cb is not None:
            opciones = filtrar_cb(opciones)
    canal = _resolver(opciones, ["Canal Venta", "Canal_Venta", "Canal"])
    canales = sorted(opciones[canal].dropna().astype(str).unique()) if canal else []
    # Una selección sin ventas sigue siendo un filtro, no vuelve a «todos».
    canales = sorted(set(canales) | set(ss.get("vh_canal") or []))
    ambitos = [TODOS]
    for nombres, rotulo in ((["Grupo"], "Grupo"),
                            (["Sub Grupo", "Sub_Grupo", "Subgrupo"], "Subgrupo")):
        col = _resolver(opciones, nombres)
        if col:
            ambitos.extend(f"{rotulo}: {v}" for v in
                           sorted(opciones[col].dropna().astype(str).unique()))
    elegido = ss.get("vh_ambito", TODOS)
    if elegido not in ambitos:
        ambitos.append(elegido)

    with st.container(horizontal=True, vertical_alignment="center",
                      key="vh_resumen_contexto"):
        with st.container(width="stretch"):
            resumen_canal = ", ".join(ss.get("vh_canal") or []) or "Todos los canales"
            especiales = ("Incluye Venta Interna y Eventos"
                          if ss.get("vh_raros", ss.get("_vh_raros_valor", True))
                          else "Excluye Venta Interna y Eventos")
            st.caption(f"{rng[0]:%d/%m/%Y} – {rng[1]:%d/%m/%Y} · "
                       f"{resumen_canal} · {elegido} · {ss['vh_op_hora']} · {especiales}")
        st.button("Filtros", key="vh_ver_filtros", icon=":material/tune:",
                  on_click=alternar_filtros)
    with st.container(key="vh_datos"):
        with st.container(horizontal=True, vertical_alignment="bottom",
                          gap="medium", key="vh_filtros"):
            fecha = st.container(key="vh_filtro_fecha", width=220)
            with fecha:
                st.caption("Fechas")
                if ctx:
                    selector_fecha_tarjeta("vh_fecha", "vh_fecha_cambio",
                                           categoria=CATEGORIA, ctx=ctx)
                else:
                    st.caption(f"{rng[0]:%d/%m/%Y} – {rng[1]:%d/%m/%Y}")
            with st.container(key="vh_filtro_canal", width=195):
                seleccion_multiple("vh_canal", canales, conservar=True)
                canal_sel = st.multiselect("Canal", canales, key="vh_canal",
                                           placeholder="Todos los canales")
            with st.container(key="vh_filtro_ambito", width=230):
                ambito = st.selectbox("Ámbito", ambitos, key="vh_ambito")
            with st.container(key="vh_filtro_base", width=185):
                hora = st.selectbox("Base temporal", BASES, key="vh_op_hora",
                                    disabled=not col_pedido,
                                    help="Pedido: apertura del pedido, no la hora "
                                         "de cada plato. Comprobante: fecha y "
                                         "hora de registro del documento.")
        with st.container(horizontal=True, vertical_alignment="center",
                          gap="medium", key="vh_contexto"):
            incluir = st.toggle("Incluir Venta Interna y Eventos",
                                value=bool(ss.get("_vh_raros_valor", True)),
                                key="vh_raros")
            ss["_vh_raros_valor"] = incluir
            st.caption("Venta atribuida a la apertura del pedido" if hora == BASES[0]
                       else "Venta atribuida al registro del comprobante")
    filtros = dict(canales=tuple(canal_sel), ambito=ambito, incluir=incluir)
    return {"rango": rng, "hora": hora, "incluir": incluir,
            "filtrar": partial(_aplicar, original=filtrar_cb, **filtros),
            "fecha_container": fecha, "canales": canal_sel, "ambito": ambito,
            "estado": estado}
