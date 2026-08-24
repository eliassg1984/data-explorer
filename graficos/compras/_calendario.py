"""graficos.compras._calendario - calendario de DOS MESES, dentro de la tarjeta.

Lo usa la vista "Semanal" de Compras (2026-08-24, a pedido): ahi el eje de
tiempo ES el tema del grafico, asi que el selector de fecha vive arriba de
la tarjeta en vez de en la franja superior.

Va PLEGADO: el trigger es una linea de 32px con el rango, y los dos meses
salen en un popover. Primero se dibujaba inline y se comia media tarjeta
(reportado el mismo dia). Popover y no `st.expander` porque el expander
EMPUJA lo que tiene debajo, y la tarjeta esta clampeada a `--alto-util`:
al abrirlo el grafico se iba fuera de vista. De yapa, al flotar el panel
deja de estar limitado por el ancho de la columna y la celda recupero sus
~40px.

POR QUE NO ES UN st.date_input
------------------------------
Porque Streamlit dibuja UN SOLO MES y no hay forma de pedirle dos. Medido
en el bundle de 1.59.2 (`static/js/DateInput.CcrfZFeJ.js`): a BaseWeb le
pasa `value / minDate / maxDate / range / clearable` y NUNCA `monthsShown`,
que es el prop que controla cuantos meses dibuja. El segundo mes no esta
oculto: no existe en el DOM, asi que no hay CSS que lo arregle.

QUIEN ES EL DUENO DEL RANGO
---------------------------
Sigue siendo `estado_rango`. Este modulo NO inventa estado: escribe la
clave canonica por `aplicar_atajo`, el mismo callback que ya usan los
botones de atajo de la franja. Al correr como `on_click` (antes del rerun)
no choca con nada.

EL PIN, Y POR QUE NO SE PUEDE SACAR
-----------------------------------
En esta vista el `st.date_input` de la franja NO se dibuja, y Streamlit
descarta el estado de un widget que dejo de renderizarse. Medido con un
spike el 2026-08-24: al primer rerun despues de cruzar la frontera la
clave desaparece y `asegurar_rango` la vuelve a sembrar con el DEFAULT —
o sea el usuario pierde su rango al entrar a la vista.

El cull ocurre UNA sola vez. Reescribir la clave con su propio valor desde
el cuerpo del script la convierte en clave normal de session_state y a
partir de ahi sobrevive sola (verificado a tres reruns). Esa reescritura
es `_pin_rango()`. Sin ella la vista se ve bien y pierde el rango en
silencio, que es la peor forma de fallar.

EL CSS VIVE ACA, NO EN `estilos/`
---------------------------------
Mismo criterio que `_css_proveedor.py`: son reglas scopeadas a las keys de
esta vista y solo tienen sentido cuando se dibuja. Ademas la banda del
rango se GENERA por dia en cada render, asi que no puede ser un bloque
estatico. Dos trampas medidas al construirlo, las dos documentadas abajo
en `_css()`: la especificidad y el nodo de la fuente.
"""

import calendar
import datetime

import streamlit as st

import franja_fecha
from estado_rango import aplicar_atajo
from tema import (ACENTO, ACENTO_FUERTE, ACENTO_TEXTO, GRIS_TEXTO_SUAVE,
                  LAVANDA_BORDE, LAVANDA_FONDO, TEXTO_PRINCIPAL)

# Claves de esta vista. El RANGO no esta aca: es de `estado_rango`.
_K_PEND = "compras_sem_cal_pend"    # 1er clic a la espera del 2do
_K_ANCLA = "compras_sem_cal_ancla"  # (anio, mes) del mes IZQUIERDO
_K_PICK = "compras_sem_cal_pick"    # el selector de mes/ano esta abierto
_K_VISTO = "compras_sem_cal_visto"  # ultimo rango que vio el calendario

_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
_DOW = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]


def _mes_siguiente(anio, mes):
    return (anio + 1, 1) if mes == 12 else (anio, mes + 1)


def _mes_anterior(anio, mes):
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def _meses_disponibles(fmin, fmax):
    """Lista de `(anio, mes)` entre los topes del dato, del mas viejo al mas
    nuevo. Es lo que ofrece el selector del titulo."""
    if not (fmin and fmax):
        hoy = datetime.date.today()
        return [(hoy.year, hoy.month)]
    salida, anio, mes = [], fmin.year, fmin.month
    while (anio, mes) <= (fmax.year, fmax.month):
        salida.append((anio, mes))
        anio, mes = _mes_siguiente(anio, mes)
    return salida


def _etiqueta_mes(t):
    return "%s %d" % (_MESES[t[1] - 1], t[0])


def _pin_rango(k_rango):
    """Convierte la clave del rango en clave NORMAL de session_state.

    Ver el docstring del modulo: sin esto Streamlit la descarta al primer
    rerun sin `st.date_input` y el rango vuelve al default. Es idempotente
    y no cambia el valor — solo lo reescribe.
    """
    r = st.session_state.get(k_rango)
    if isinstance(r, (tuple, list)) and len(r) == 2 and all(r):
        st.session_state[k_rango] = tuple(r)


def _clic_dia(f, k_rango, reporte, usa_carga_rango):
    """Protocolo de dos clics: 1o fija el inicio, 2o cierra el rango.

    El PRIMER clic no toca el rango: solo deja la fecha pendiente. Asi el
    grafico no se redibuja con un rango de un dia entre clic y clic (y en
    un reporte con `carga_por_rango` tampoco se dispara una lectura de R2
    a medio elegir). Un rango completo = una sola escritura.
    """
    pend = st.session_state.get(_K_PEND)
    if pend is None:
        st.session_state[_K_PEND] = f
        return
    ini, fin = (pend, f) if pend <= f else (f, pend)
    st.session_state[_K_PEND] = None
    aplicar_atajo(k_rango, (ini, fin), reporte, usa_carga_rango)


def _abrir_selector():
    st.session_state[_K_PICK] = True


def _elegir_mes(anio, mes):
    st.session_state[_K_ANCLA] = (anio, mes)
    st.session_state[_K_PICK] = False


def _cerrar_selector():
    st.session_state[_K_PICK] = False


def _mover(paso):
    anio, mes = st.session_state[_K_ANCLA]
    st.session_state[_K_ANCLA] = (_mes_anterior(anio, mes) if paso < 0
                                  else _mes_siguiente(anio, mes))


def _css(dias_estado):
    """CSS de la grilla + la banda del rango, generada por dia.

    TRAMPA 1 — especificidad. Las reglas por dia van scopeadas BAJO el
    contenedor. Sueltas no pintan: el reset de abajo
    (`.st-key-compras_sem_cal .stButton button`, dos clases) le gana por
    especificidad a `.st-key-cal_d_YYYYMMDD button` (una clase), y como las
    dos llevan `!important` venir despues no alcanza. Sintoma: todas las
    celdas transparentes y ningun error.

    TRAMPA 2 — el nodo de la fuente. El override apunta a
    `stMarkdownContainer`, NO a `stMarkdown`: ese div ya sale en DM Sans y
    el cambio ocurre un nivel mas adentro. Hace falta porque Streamlit no
    le pone font-family propia a un `st.button` (los numeros heredan la del
    proyecto) pero el markdown SI cae a su Source Sans — sin esto los
    encabezados Lu/Ma/Mi salen en otra tipografia que los numeros. Ver
    `estilos/_00_base.py:305`, que declara la fuente sin `!important`, y
    `graficos/ajuste/_heatmap.py`, que ya se topo con lo mismo.
    """
    reglas = [
        # Gap exterior (fila de navegacion y las dos columnas de mes).
        # Va PRIMERO: la regla de `cal_mes_` de mas abajo tiene la MISMA
        # especificidad y gana por orden para las filas de semana.
        '.st-key-compras_sem_cal [data-testid="stHorizontalBlock"] '
        '{ gap: 6px !important; }',
        # SOLAPE: `st.markdown` con HTML de bloque sale con
        # `margin-bottom: -16px` (arquitectura.md regla #162). Medido aca:
        # el contenedor del titulo colapsaba a 10px de alto mientras el div
        # seguia midiendo 26, asi que "julio 2026" se dibujaba ENCIMA de la
        # fila Lu/Ma/Mi/Ju/Vi/Sa/Do. Afecta igual a las celdas vacias del
        # mes, que tambien son markdown.
        '[class*="st-key-cal_mes_"] [data-testid="stMarkdownContainer"] '
        '{ margin-bottom: 0 !important; }',
        # Sin gap: la banda del tramo intermedio tiene que ser continua.
        # Cada `st.columns()` es un bloque, asi que el gap reaparece entre
        # semana y semana — de ahi las dos reglas.
        '[class*="st-key-cal_mes_"] [data-testid="stHorizontalBlock"] '
        '{ gap: 0 !important; flex-wrap: nowrap !important; }',
        '[class*="st-key-cal_mes_"][class*="stVerticalBlock"] '
        '{ gap: 0 !important; }',
        # Siete columnas que se reparten el ancho EN PARTES IGUALES, sin
        # ancho fijo en px. Fue lo primero que se probo (42px, la medida
        # real de una celda de BaseWeb) y clipeaba: esta tarjeta es la
        # columna izquierda de un `st.columns([1.7, 1])`, o sea ~230px por
        # mes a 1280 de viewport, contra los 7x42 = 294 que pide la fila.
        # Con `overflow-x: hidden` en la tarjeta, sabado y domingo se
        # perdian sin aviso. Un px fijo mas chico solo mueve el ancho de
        # ventana en el que vuelve a pasar; `flex: 1 1 0` + `min-width: 0`
        # no clipea nunca. Scopeado a `cal_mes_` a proposito: la fila de
        # navegacion y las DOS columnas de mes son hermanas de estos
        # contenedores, no descendientes, asi que no las alcanza.
        '[class*="st-key-cal_mes_"] [data-testid="stColumn"] '
        '{ flex: 1 1 0 !important; min-width: 0 !important; }',
        # Los envoltorios TAMBIEN a ancho completo. Sin esto el `width:
        # 100%` del boton se resuelve contra un `.stButton` que es
        # auto-width, o sea contra el ancho del TEXTO: medido, celdas de
        # 16px separadas por 17 de hueco en vez de una fila continua.
        # OJO: aca va UN solo `%` — esta cadena no la cierra ningun
        # operador de formato, a diferencia de la del boton, mas abajo.
        '[class*="st-key-cal_mes_"] [data-testid="stElementContainer"], '
        '[class*="st-key-cal_mes_"] [data-testid="stVerticalBlock"], '
        '[class*="st-key-cal_mes_"] .stButton '
        '{ width: 100% !important; margin: 0 !important; }',
        # El boton trae su propio alto minimo y padding. El ancho es 100%
        # de su columna — asi la banda del rango sigue siendo continua sin
        # depender de cuanto mida la celda.
        #
        # OJO CON SEGUIR ACHICANDO: el panel se compacto en dos vueltas a
        # pedido (620x334 -> 520x278 -> 470x237) y con 26px de alto la
        # celda queda en ~32x26. Es chico pero todavia clickeable en
        # escritorio; por debajo de eso hay que cambiar de forma (un mes
        # por vez, o volver a un input de texto), no seguir bajando px.
        # OJO: `100%%` escapado — esta cadena la cierra un `% TEXTO_PRINCIPAL`
        # y un `%` suelto seguido de espacio revienta en runtime (lo agarro
        # ruff con F509, no un test).
        '.st-key-compras_sem_cal .stButton button { width: 100%% !important; '
        'height: 26px !important; min-height: 26px !important; '
        'padding: 0 !important; border: 0 !important; '
        'border-radius: 0 !important; background: transparent !important; '
        'box-shadow: none !important; color: %s !important; '
        'font-size: 10.5px !important; font-weight: 500 !important; '
        'font-variant-numeric: tabular-nums !important; }' % TEXTO_PRINCIPAL,
        '.st-key-compras_sem_cal .stButton button:hover '
        '{ background: %s !important; border-radius: 8px !important; }'
        % LAVANDA_FONDO,
        # TRAMPA 2, arriba.
        '.st-key-compras_sem_cal [data-testid="stMarkdownContainer"] '
        "{ font-family: 'DM Sans', 'Inter', sans-serif !important; }",
        # El TITULO es un boton, pero tiene que leerse como un titulo:
        # sin marco, sin fondo, centrado. El hover si lo insinua.
        '[class*="st-key-cal_tit_"] button '
        '{ background: transparent !important; border: 0 !important; '
        'box-shadow: none !important; height: 18px !important; '
        'min-height: 18px !important; padding: 0 !important; '
        'font-size: 11px !important; font-weight: 700 !important; '
        'color: %s !important; }' % TEXTO_PRINCIPAL,
        '[class*="st-key-cal_tit_"] button:hover '
        '{ color: %s !important; text-decoration: underline !important; }'
        % ACENTO,
        # Selector de mes/ano: filas compactas de 12 meses por ano.
        '.st-key-cal_pick [data-testid="stHorizontalBlock"] '
        '{ gap: 2px !important; flex-wrap: nowrap !important; }',
        '.st-key-cal_pick [data-testid="stColumn"] '
        '{ min-width: 0 !important; }',
        '.st-key-cal_pick [data-testid="stElementContainer"], '
        '.st-key-cal_pick [data-testid="stVerticalBlock"], '
        '.st-key-cal_pick .stButton '
        '{ width: 100% !important; margin: 0 !important; }',
        '.st-key-cal_pick [data-testid="stMarkdownContainer"] '
        '{ margin-bottom: 0 !important; }',
        '[class*="st-key-cal_pick_2"] button '
        '{ width: 100%% !important; height: 24px !important; '
        'min-height: 24px !important; padding: 0 !important; '
        'border: 0 !important; border-radius: 5px !important; '
        'background: transparent !important; box-shadow: none !important; '
        'font-size: 9.5px !important; font-weight: 600 !important; '
        'color: %s !important; }' % TEXTO_PRINCIPAL,
        '[class*="st-key-cal_pick_2"] button:hover:not([disabled]) '
        '{ background: %s !important; }' % LAVANDA_FONDO,
        '[class*="st-key-cal_pick_2"] button[disabled] '
        '{ color: %s !important; opacity: .45 !important; }' % GRIS_TEXTO_SUAVE,
        '.st-key-cal_pick_volver button '
        '{ height: 26px !important; min-height: 26px !important; '
        'margin-top: 6px !important; font-size: 10.5px !important; '
        'border: 1px solid %s !important; border-radius: 6px !important; '
        'color: %s !important; background: transparent !important; }'
        % (LAVANDA_BORDE, ACENTO_TEXTO),
        # La navegacion son botones tambien, pero fuera de `cal_mes_`: se
        # las devuelve a un tamano normal.
        '.st-key-cal_nav_ant button, .st-key-cal_nav_sig button '
        '{ width: 24px !important; height: 22px !important; '
        'min-height: 22px !important; color: %s !important; '
        'font-size: 13px !important; border-radius: 6px !important; }'
        % ACENTO,
        # El panel FLOTA, asi que su ancho no lo limita la columna de la
        # tarjeta (~230px por mes, que fue lo que obligo a achicar la
        # celda cuando el calendario iba inline). Con 620px cada mes
        # vuelve a tener sus ~42px de celda.
        # El panel FLOTA, asi que su ancho no lo limita la columna de la
        # tarjeta. Y el padding va apretado a mano: Streamlit le pone 23px
        # por defecto, que en un panel que es CASI TODO grilla se lee como
        # un marco vacio (medido: 23 arriba + 36 de navegacion + 16 de gap
        # = 75px antes del primer dia).
        '[data-testid="stPopoverBody"]:has(.st-key-compras_sem_cal) '
        '{ min-width: 430px !important; padding: 8px !important; }',
        # Gap del contenedor: entre la fila de navegacion y los meses
        # alcanza con un respiro, no con los 16px de un bloque normal.
        '.st-key-compras_sem_cal { gap: 2px !important; }',
        # Trigger: pill outline, mismo idioma que el resto de controles de
        # la app. Compacto a proposito — es una linea arriba del grafico,
        # no un encabezado.
        '.st-key-compras_sem_cal_pill [data-testid="stPopover"] button '
        '{ min-height: 32px !important; padding: 4px 12px !important; '
        'border: 1.5px solid %s !important; border-radius: 8px !important; '
        'background: transparent !important; color: %s !important; '
        'font-size: 13px !important; font-weight: 600 !important; '
        'white-space: nowrap !important; }' % (LAVANDA_BORDE, ACENTO_TEXTO),
        '.st-key-compras_sem_cal_pill [data-testid="stPopover"] button:hover '
        '{ background: %s !important; border-color: %s !important; }'
        % (LAVANDA_FONDO, ACENTO),
        '.st-key-compras_sem_cal_pill [data-testid="stIconMaterial"] '
        '{ color: %s !important; font-size: 17px !important; }' % ACENTO,
    ]

    # TRAMPA 1, arriba: cada regla por dia va bajo el contenedor.
    for clave, estado in dias_estado.items():
        sel = ".st-key-compras_sem_cal .st-key-%s button" % clave
        if estado == "fuera":
            reglas.append("%s { color: %s !important; opacity: .5 !important; }"
                          % (sel, GRIS_TEXTO_SUAVE))
        elif estado == "dentro":
            reglas.append("%s { background: %s !important; }"
                          % (sel, LAVANDA_FONDO))
        else:                       # ini / fin / unico / pendiente
            radio = {"ini": "8px 0 0 8px", "fin": "0 8px 8px 0"}.get(estado, "8px")
            reglas.append(
                "%s { background: %s !important; color: #fff !important; "
                "font-weight: 700 !important; border-radius: %s !important; }"
                % (sel, ACENTO, radio))
            reglas.append("%s:hover { background: %s !important; }"
                          % (sel, ACENTO_FUERTE))

    st.markdown("<style>%s</style>" % "".join(reglas), unsafe_allow_html=True)


def _estado_de_los_dias(anio, mes, ini, fin, pend, fmin, fmax):
    """`{clave_de_key: estado}` para cada dia del mes. Puro, sin Streamlit."""
    salida = {}
    for dia in range(1, calendar.monthrange(anio, mes)[1] + 1):
        f = datetime.date(anio, mes, dia)
        clave = "cal_d_%s" % f.strftime("%Y%m%d")
        if (fmin and f < fmin) or (fmax and f > fmax):
            salida[clave] = "fuera"
        elif pend is not None:
            # Mientras espera el 2do clic manda la fecha pendiente: mostrar
            # ADEMAS el rango viejo diria que hay dos selecciones vivas.
            if f == pend:
                salida[clave] = "unico"
        elif ini and fin:
            if f == ini and f == fin:
                salida[clave] = "unico"
            elif f == ini:
                salida[clave] = "ini"
            elif f == fin:
                salida[clave] = "fin"
            elif ini < f < fin:
                salida[clave] = "dentro"
    return salida


def _pintar_mes(anio, mes, lado, fmin, fmax, k_rango, reporte, usa_carga_rango):
    with st.container(key="cal_mes_%s" % lado):
        # El titulo ES el boton que abre el selector de mes/ano (pedido
        # 2026-08-24: "pense que se podia seleccionar mes y ano"). Con
        # solo las flechas, ir a enero del ano pasado son doce clics.
        #
        # POR QUE UN BOTON Y NO UN `st.selectbox`: se probo primero con
        # selectbox y NO FUNCIONA dentro de un `st.popover`. El
        # desplegable es virtualizado y mide su alto al montarse; adentro
        # del popover mide 0, renderiza CERO filas y nunca vuelve a
        # medir. Medido: el listbox abre con el espaciador correcto
        # (1760px = 40 opciones) y el html en 109 caracteres, o sea
        # ninguna opcion; al forzar un `resize` aparecen 12 de golpe. Un
        # `st.button` no tiene ese problema — es lo mismo con lo que esta
        # hecha toda la grilla.
        st.button(_etiqueta_mes((anio, mes)),
                  key="cal_tit_%s" % lado,
                  on_click=_abrir_selector,
                  use_container_width=True,
                  help="Elegir mes y año")
        cab = st.columns(7)
        for i, nombre in enumerate(_DOW):
            with cab[i]:
                st.markdown(
                    "<div style='height:16px;display:flex;align-items:center;"
                    "justify-content:center;font-size:9.5px;font-weight:600;"
                    "color:%s;'>%s</div>" % (GRIS_TEXTO_SUAVE, nombre),
                    unsafe_allow_html=True,
                )
        for semana in calendar.monthcalendar(anio, mes):
            cols = st.columns(7)
            for i, dia in enumerate(semana):
                with cols[i]:
                    if dia == 0:
                        # Mismo alto que el boton, o la fila se descuadra.
                        st.markdown("<div style='height:26px'></div>",
                                    unsafe_allow_html=True)
                        continue
                    f = datetime.date(anio, mes, dia)
                    fuera = (fmin and f < fmin) or (fmax and f > fmax)
                    st.button(
                        str(dia),
                        key="cal_d_%s" % f.strftime("%Y%m%d"),
                        disabled=bool(fuera),
                        on_click=_clic_dia,
                        args=(f, k_rango, reporte, usa_carga_rango),
                    )


def render():
    """Dibuja el calendario y devuelve el rango vigente `(ini, fin)`.

    Lee todo del contexto que `app.py` publica en `franja_fecha` — el mismo
    que usa el drill de Documentos SUNAT. Si no hay contexto (reporte sin
    columna de fecha) no dibuja nada y devuelve None.
    """
    ctx = franja_fecha.contexto()
    if not ctx:
        return None

    k_rango = ctx["k_rango"]
    fmin, fmax = ctx["fecha_min"], ctx["fecha_max"]
    reporte = ctx["reporte"]
    usa_carga_rango = ctx["usa_carga_rango"]

    # Ver el docstring del modulo. Va ANTES de dibujar nada.
    _pin_rango(k_rango)

    rango = st.session_state.get(k_rango)
    ini = fin = None
    if isinstance(rango, (tuple, list)) and len(rango) == 2 and all(rango):
        ini, fin = rango
    pend = st.session_state.get(_K_PEND)

    # Ancla = mes IZQUIERDO, y el mes de referencia va a la DERECHA — o sea
    # se muestra [mes-1, mes], no [mes, mes+1].
    #
    # No es estetico: medido el 2026-08-24 con el parquet real, que termina
    # el 9 de agosto. Anclando el mes de referencia a la izquierda salian
    # agosto + septiembre, y septiembre entero deshabilitado — la mitad del
    # calendario muerta. Con el mes de referencia a la derecha salen julio
    # + agosto y los dos sirven. Ademas es lo que hace cualquier selector
    # de rango: uno casi siempre mira HACIA ATRAS desde una fecha.
    ref = pend or ini or (fmax or datetime.date.today())
    if _K_ANCLA not in st.session_state:
        st.session_state[_K_ANCLA] = _mes_anterior(ref.year, ref.month)
    anio_a, mes_a = st.session_state[_K_ANCLA]
    anio_b, mes_b = _mes_siguiente(anio_a, mes_a)

    # Re-sembrar el ancla SOLO si el rango cambio desde AFUERA (un atajo de
    # otra vista, un deep-link) y ademas quedo fuera de los dos meses a la
    # vista. Las dos condiciones importan:
    #
    #   · sin comparar contra el rango ANTERIOR, la guarda corria en cada
    #     render y pisaba cualquier navegacion deliberada — elegir enero
    #     2025 en el selector volvia solo a julio 2026, y las flechas no
    #     podian alejarse mas de un mes del rango (medido, 2026-08-24);
    #   · sin la segunda, elegir un rango DENTRO del calendario saltaria de
    #     mes al soltar el 2do clic.
    _visto = st.session_state.get(_K_VISTO)
    _actual = (ini, fin)
    if (_visto is not None and _visto != _actual
            and (ref.year, ref.month) not in ((anio_a, mes_a), (anio_b, mes_b))):
        st.session_state[_K_ANCLA] = _mes_anterior(ref.year, ref.month)
        anio_a, mes_a = st.session_state[_K_ANCLA]
        anio_b, mes_b = _mes_siguiente(anio_a, mes_a)
    st.session_state[_K_VISTO] = _actual

    if pend is not None:
        _label = "Elegí la fecha de finalización"
    elif ini and fin:
        _label = franja_fecha.fmt_rango_es(ini, fin)
    else:
        _label = "Seleccionar rango"

    estados = {}
    estados.update(_estado_de_los_dias(anio_a, mes_a, ini, fin, pend, fmin, fmax))
    estados.update(_estado_de_los_dias(anio_b, mes_b, ini, fin, pend, fmin, fmax))

    with st.container(key="compras_sem_cal_pill"):
        # El CSS se inyecta AFUERA del popover a proposito. Streamlit
        # renderiza el cuerpo del popover en un portal que solo existe en
        # el DOM mientras esta abierto: un <style> ahi adentro se lleva
        # puesto el estilo del propio trigger cada vez que se cierra. Un
        # <style> suelto en el documento alcanza igual al portal.
        _css(estados)
        with st.popover(_label, use_container_width=False,
                        icon=":material/calendar_month:"):
            _panel(anio_a, mes_a, anio_b, mes_b, ini, fin, pend,
                   fmin, fmax, k_rango, reporte, usa_carga_rango)

    return (ini, fin) if (ini and fin) else None


def _panel(anio_a, mes_a, anio_b, mes_b, ini, fin, pend, fmin, fmax,
           k_rango, reporte, usa_carga_rango):
    """El contenido del desplegable: navegacion + los dos meses.

    El CSS NO se inyecta aca: lo hace `render()` afuera del popover, ver
    el comentario alla.
    """
    with st.container(key="compras_sem_cal"):
        # Fila de navegacion. Sus columnas son hermanas de `cal_mes_*`, no
        # descendientes, asi que la regla del ancho de celda no las toca.
        c_ant, c_lbl, c_sig = st.columns([1, 6, 1], vertical_alignment="center")
        with c_ant:
            with st.container(key="cal_nav_ant"):
                st.button("‹", key="cal_ant", on_click=_mover, args=(-1,),
                          help="Mes anterior")
        with c_lbl:
            # El rango ya lo dice el trigger del desplegable, que queda a
            # la vista con el panel abierto: repetirlo aca seria decir dos
            # veces lo mismo. Solo se usa para la pista del 2do clic, que
            # es lo unico que el trigger no puede explicar.
            if pend is not None:
                st.markdown(
                    "<div style='text-align:center;font-size:12.5px;"
                    "color:%s;'>Elegí la fecha de finalización</div>" % ACENTO,
                    unsafe_allow_html=True,
                )
        with c_sig:
            with st.container(key="cal_nav_sig"):
                st.button("›", key="cal_sig", on_click=_mover, args=(1,),
                          help="Mes siguiente")

        if st.session_state.get(_K_PICK):
            _selector_mes(anio_a, mes_a, fmin, fmax)
            return

        col_a, col_b = st.columns(2)
        with col_a:
            _pintar_mes(anio_a, mes_a, "a", fmin, fmax, k_rango, reporte,
                        usa_carga_rango)
        with col_b:
            _pintar_mes(anio_b, mes_b, "b", fmin, fmax, k_rango, reporte,
                        usa_carga_rango)


def _selector_mes(anio_ancla, mes_ancla, fmin, fmax):
    """Elegir mes y ano de un golpe: una fila de 12 meses por cada ano con
    datos. Reemplaza a las dos grillas mientras esta abierto.

    Todo con `st.button` a proposito — ver el comentario del titulo en
    `_pintar_mes`: un `st.selectbox` dentro de un `st.popover` abre un
    desplegable VACIO.
    """
    meses = _meses_disponibles(fmin, fmax)
    anios = sorted({a for a, _ in meses})
    disponibles = set(meses)

    with st.container(key="cal_pick"):
        for anio in anios:
            cols = st.columns([1.4] + [1] * 12)
            with cols[0]:
                st.markdown(
                    "<div style='height:24px;display:flex;align-items:center;"
                    "justify-content:flex-end;padding-right:6px;font-size:11px;"
                    "font-weight:700;color:%s;'>%d</div>"
                    % (TEXTO_PRINCIPAL, anio),
                    unsafe_allow_html=True,
                )
            for m in range(1, 13):
                with cols[m]:
                    st.button(
                        _MESES[m - 1][:3],
                        key="cal_pick_%d_%02d" % (anio, m),
                        disabled=(anio, m) not in disponibles,
                        on_click=_elegir_mes, args=(anio, m),
                    )
        st.button("Volver al calendario", key="cal_pick_volver",
                  on_click=_cerrar_selector, use_container_width=True)
