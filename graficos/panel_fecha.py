"""
graficos.panel_fecha — el PANEL del selector de fecha de una tarjeta.

Lo que se abre al apretar el botón con las fechas (`base.py::
selector_fecha_tarjeta`): la «opción A» que eligió el usuario el 2026-10-08
sobre un mockup (https://claude.ai/artifact/8uSazby41NyvTc68DzJuB9). A la
izquierda los atajos, escritos enteros y agrupados («En curso», «Hacia
atrás», «Completos»); a la derecha los años como pestañas y los meses —o,
con «Días», un calendario— como casilleros. Un clic elige un mes; un clic en
otro suma los del medio, aunque estén en años distintos.

Reemplazó a la escala de tiempo con línea deslizante (`selector_escala`,
reglas #211-#222 y #298-#300), que tenía tres problemas de fondo, medidos:
  · la línea vivía dentro de UN mes (Días) o UN año (Meses): no se podía
    elegir un rango que cruzara de mes o de año;
  · los atajos se anclaban a hoy y la tarjeta abría en un rango que no era
    ninguno de ellos, así que nada decía cuál estaba puesto;
  · cada tirador que se soltaba recalculaba la página entera.

ES UNA PIEZA PROPIA (`st.components.v2`): HTML, CSS y JavaScript sin
compilar nada y SIN IFRAME —va en el DOM de la página, con sus estilos en un
shadow root, que hereda las variables de color de `estilos/_00_base.py`—.
Todo lo que pasa adentro es del navegador: cambiar de año, de mes, pasar el
cursor. A Python le llega sólo el rango elegido, como el trigger `rango`
(`{"a": "2026-09-08", "b": "2026-10-07"}`), y eso lo escribe
`estado_rango.aplicar_atajo` en la MISMA clave de siempre (`ctx["k_rango"]`):
para el resto de la app no cambió nada. El JS y el CSS viven al lado, en
`panel_fecha.js` y `panel_fecha.css`.

UN AVISO POR ELECCIÓN. Un atajo avisa enseguida. Un mes (o un día) suelto
espera un poco antes de avisar (`ESPERA_MS` en el JS): si llega el segundo
clic, se avisa UNA vez el rango entero en vez de recalcular la tarjeta dos
veces. Si el panel se cierra con la espera corriendo, avisa al cerrarse.

CICLO DE VIDA, medido el 2026-10-08 con un prototipo dentro de un popover y
un fragment: el componente se MONTA al abrir el popover y se DESMONTA al
cerrarlo (y un trigger mandado desde esa limpieza sí llega a Python);
mientras está abierto, cada corrida le vuelve a llamar la función con los
datos nuevos SIN rehacer el DOM. Por eso el estado del panel —qué año se ve,
el primer clic de un rango— vive en su elemento raíz, y lo que llega de
Python no lo pisa mientras hay un aviso pendiente.

Regla #616.
"""

import datetime
from pathlib import Path

import streamlit as st

from cortes import DIAS_ABR_ES, DIAS_LARGOS_ES, MESES_ABR_ES, MESES_LARGOS_ES
from estado_rango import aplicar_atajo, atajo_de, atajos_tarjeta

_AQUI = Path(__file__).parent
_COMPONENTE = st.components.v2.component(
    "panel_fecha",
    css=(_AQUI / "panel_fecha.css").read_text(encoding="utf-8"),
    js=(_AQUI / "panel_fecha.js").read_text(encoding="utf-8"),
)


def ancla_atajos(ctx):
    """El último día con datos, que es hasta donde cuentan los atajos. Nunca
    después de hoy: un tope ensanchado no puede inventar días por venir."""
    fin = ctx.get("fecha_max")
    hoy = ctx.get("hoy")
    if fin and hoy:
        return min(fin, hoy)
    return fin or hoy


def _dia_mes(d, con_anio=False):
    return f"{d.day} {MESES_ABR_ES[d.month - 1]}" + (f" {d.year}" if con_anio else "")


def fmt_rango(ini, fin, con_anio=True):
    """«8 set – 7 oct 2026», «1–7 oct 2026», «8 oct 2025 – 7 oct 2026». Sin
    año (`con_anio=False`) cuando los dos extremos caen en el mismo: lo pone
    el contexto. Con «set», como el resto de la app (`cortes.MESES_ABR_ES`)."""
    anio = f" {fin.year}" if con_anio else ""
    if ini == fin:
        return _dia_mes(fin) + anio
    if ini.year != fin.year:
        return f"{_dia_mes(ini, True)} – {_dia_mes(fin, True)}"
    if ini.month == fin.month:
        return f"{ini.day}–{fin.day} {MESES_ABR_ES[fin.month - 1]}{anio}"
    return f"{_dia_mes(ini)} – {_dia_mes(fin)}{anio}"


def _rango_del_atajo(clave, r):
    """Las fechas de un atajo como las dice el BOTÓN: «8 set – 7 oct»,
    «setiembre», «2025»."""
    ini, fin = r
    if clave == "mes_ant":
        return MESES_LARGOS_ES[ini.month - 1]
    if clave == "anio_ant":
        return str(ini.year)
    if clave == "todo":
        return f"desde {MESES_ABR_ES[ini.month - 1]} {ini.year}"
    return fmt_rango(ini, fin, con_anio=False)


def _pista_del_atajo(clave, r, ancla):
    """Las fechas de un atajo como las dice la LISTA del panel: sólo dónde
    empieza («desde 8 set»), porque todos los que no son «completos» terminan
    en el ancla, y el pie del panel lo dice una vez."""
    ini, fin = r
    if clave in ("mes_ant", "anio_ant", "todo") or fin != ancla:
        return _rango_del_atajo(clave, r)
    if clave == "semana":
        return f"desde el {DIAS_ABR_ES[ini.weekday()]} {ini.day}"
    return "desde " + _dia_mes(ini, con_anio=ini.year != ancla.year)


def _ctx_valido(ctx):
    return bool(ctx and ctx.get("fecha_min") and ctx.get("fecha_max"))


def _rango_vigente(ctx):
    r = st.session_state.get(ctx["k_rango"])
    if isinstance(r, (tuple, list)) and len(r) == 2 and all(r):
        return (min(r), max(r))
    return None


def etiqueta_disparador(ctx):
    """El texto del botón que abre el panel, para el rango vigente de `ctx`."""
    return etiqueta_de(_rango_vigente(ctx) if _ctx_valido(ctx) else None, ctx)


def etiqueta_de(rango, ctx):
    """El atajo y sus fechas («Últimos 30 días · 8 set – 7 oct») o, si
    `rango` no es un atajo, las fechas con el año («15 set – 7 oct 2026»).
    Pura: la fija `test_graficos.py::_pruebas_panel_fecha`."""
    if not rango or not _ctx_valido(ctx):
        return "Elegir fechas"
    atajos = atajos_tarjeta(ancla_atajos(ctx), (ctx["fecha_min"], ctx["fecha_max"]))
    clave = atajo_de(rango, atajos)
    if clave:
        nombre, r = next((n, r) for c, n, _g, r in atajos if c == clave)
        return f"{nombre} · {_rango_del_atajo(clave, r)}"
    return fmt_rango(*rango)


def _fecha_iso(texto):
    try:
        return datetime.date.fromisoformat(str(texto))
    except (TypeError, ValueError):
        return None


def panel_fecha(clave, ctx, bandera=None):
    """Dibuja el panel y aplica lo que se elija en `ctx["k_rango"]`.

    `clave` es el prefijo de la tarjeta (el mismo de `selector_fecha_tarjeta`):
    el componente va con la key `{clave}_panelf`. `bandera`, si viene, se
    prende al aplicar —es la escalada a un rerun completo que esperan las
    tarjetas de Compras y de Ventas, ver `_aplicar_escala` en la historia de
    `base.py`—; una tarjeta que recorta sus datos dentro de su propio
    fragment no la necesita."""
    if not _ctx_valido(ctx):
        return
    bounds = (ctx["fecha_min"], ctx["fecha_max"])
    ancla = ancla_atajos(ctx)
    atajos = atajos_tarjeta(ancla, bounds)
    rango = _rango_vigente(ctx)
    hoy = ctx.get("hoy")
    nota = (f"Los atajos cuentan hasta el último día con datos: "
            f"{DIAS_LARGOS_ES[ancla.weekday()]} {ancla.day} de "
            f"{MESES_LARGOS_ES[ancla.month - 1]}"
            + (f" de {ancla.year}" if hoy and ancla.year != hoy.year else "") + ".")
    data = {
        "min": bounds[0].isoformat(),
        "max": bounds[1].isoformat(),
        "a": rango[0].isoformat() if rango else None,
        "b": rango[1].isoformat() if rango else None,
        "atajos": [{"k": c, "nombre": n, "grupo": g,
                    "a": r[0].isoformat(), "b": r[1].isoformat(),
                    "pista": _pista_del_atajo(c, r, ancla)}
                   for c, n, g, r in atajos],
        "nota": nota,
    }
    k_panel = f"{clave}_panelf"

    def _al_elegir():
        # Un callback de componente no recibe argumentos: el valor se lee de
        # su key. Corre ANTES del rerun, que es cuando se puede escribir la
        # clave del rango aunque un `st.date_input` la use de key.
        valor = (st.session_state.get(k_panel) or {}).get("rango") or {}
        ini, fin = _fecha_iso(valor.get("a")), _fecha_iso(valor.get("b"))
        if not (ini and fin):
            return
        ini, fin = min(ini, fin), max(ini, fin)
        ini = min(max(ini, bounds[0]), bounds[1])
        fin = min(max(fin, bounds[0]), bounds[1])
        aplicar_atajo(ctx["k_rango"], (ini, fin), ctx["reporte"],
                      ctx["usa_carga_rango"])
        if bandera:
            st.session_state[bandera] = True

    _COMPONENTE(key=k_panel, data=data, on_rango_change=_al_elegir,
                width="content")
