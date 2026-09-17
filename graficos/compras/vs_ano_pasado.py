"""graficos.compras.vs_ano_pasado - drill "Vs año pasado" de Compras.

Compara el gasto/cantidad/precio de compra contra el MISMO mes del año
anterior, y explica la diferencia: cuánto es porque compramos más y cuánto
porque nos cobraron más caro.

La pantalla son cuatro tarjetas (desde el 2026-09-14, regla #420; hasta
ese día, una sola superficie), en este orden:

  · la CABECERA: el título y los siete controles, que mandan sobre las
    tres de abajo;
  · la SERIE mensual (este año vs año pasado) y, al lado, el PUENTE
    precio/cantidad que descompone la diferencia total;
  · la TABLA de detalle: la misma cuenta abierta ítem por ítem
    (`tablas/compras_vs_ano_pasado.py`). Clic en una fila enfoca la serie
    de arriba en ese ítem.

────────────────────────────────────────────────────────────────────────────
TRES DECISIONES QUE COSTARON DATOS EQUIVOCADOS
────────────────────────────────────────────────────────────────────────────

1. ESTA VISTA NO OBEDECE AL FILTRO DE FECHA DE LA FRANJA (2026-08-24).
   Lo pidió el usuario y tiene razón de fondo: la franja responde "quién
   pesa más ACÁ", que es la pregunta de un ranking; ésta pregunta "cómo
   viene esto contra el año pasado", y un rango de 15 días da un punto
   contra otro punto. Peor: el rango de la franja suele arrancar en el mes
   corriente, así que la vista se pasaba la vida comparando un mes
   incompleto contra un año entero.
   La ventana es ahora un control PROPIO de la tarjeta
   (`graficos/periodo.py`, el mismo que usa la Evolución de Proveedor). La
   opción `periodo.HEREDA` ("Rango") sigue ahí para el que quiera volver a
   atarla a la franja — no se le quita nada a nadie, se cambia el default.

   ARRANCA EN 3 MESES desde el 2026-09-13, a pedido («debe mostrar
   inicialmente 3 meses»). Es el mismo camino que hizo la Evolución de
   Producto el día anterior (12m → 3m): la tarjeta abre en la foto
   reciente y el año largo queda a un clic. De ahí también las etiquetas
   de valor sobre cada columna (ver `_etiquetas_serie`): con tres meses
   son seis barras anchas y el número entra entero; con doce, no.

   Entre el 2026-09-07 y ese día arrancó en 12 MESES, y antes en "Todo".
   Lo que sigue es por qué se dejó "Todo" — sigue valiendo contra
   cualquier default largo:
   "Todo" era el parche correcto mientras la franja abría en el MES EN
   CURSO: la vista comparaba un mes incompleto contra un año entero, o
   salía vacía. El 2026-09-06 la franja de Compras perdió el calendario y
   el reporte pasó a abrir en los últimos 12 meses (`app.py`, "COMPRAS ABRE
   EN LOS ÚLTIMOS 12 MESES"), así que el motivo se venció — y el default se
   quedó, descolgado de las otras tres tarjetas de gráfico, que abren todas
   en 12m.
   No es cosmético: la ventana decide qué dice el TITULAR. Medido contra el
   parquet real con los cinco chips de familia de entrada (2026-09-07):

       3m    jun-ago 26     S/  323.733  vs S/  515.828    -37,2 %
       12m   sep 25-ago 26  S/1.682.347  vs S/2.140.459    -21,4 %
       24m                  S/3.822.806  vs S/3.821.385     +0,0 %
       Todo  ene 24-ago 26  S/5.092.773  vs S/4.970.192     +2,5 %

   Los cuatro números son ciertos. Con "Todo" la tarjeta abría diciendo
   "+2,5 %" —el promedio de 32 meses, donde el crecimiento 24→25 tapa la
   caída 25→26— mientras el último año venía 21 % abajo. Y de paso dibujaba
   32 pares de barras en 660px, con el eje de meses amontonado en un
   borrón.

2. LAS COLUMNAS `*_ANO_ANTERIOR` DEL PARQUET NO SE SUMAN. ESTA VISTA YA NO
   LAS USA.
   `VALOR_ANO_ANTERIOR` / `CANTIDAD_ANO_ANTERIOR` no son un dato POR FILA:
   son el total de ESE producto en ESE mes del año pasado, REPETIDO en cada
   fila del producto-mes. Verificado contra R2 el 2026-08-24: constantes en
   los 4.269 grupos producto+mes, y sobre 8.204 pares mes/mes-12 la
   diferencia contra el total real es exactamente 0.
   El código anterior hacía `.sum()` sobre ellas. Eso multiplica el año
   pasado por la cantidad de filas del producto-mes: medido, **x4.9**
   (2025 daba S/ 11.98M contra S/ 2.46M reales). El gráfico "Compra por
   familia: este año vs año anterior" mostraba un año pasado casi cinco
   veces más grande que el real, siempre.
   Se podría arreglar deduplicando, pero el año pasado se calcula mejor
   DESDE EL PROPIO HISTÓRICO: la serie mensual desplazada 12 meses
   (`_con_ano_pasado`). Da lo mismo que la columna donde la columna existe,
   y además cubre lo que la columna no puede: los ítems que se compraban
   el año pasado y este año NO — ésos no tienen fila este año, así que su
   gasto del año pasado se perdía entero. `PRECIO_UNIT_ANO_ANTERIOR`
   tampoco se usa: es un promedio SIMPLE de precios (verificado, coincide
   al 100%), y con promedios simples el puente de abajo no cierra.

3. EL ÚLTIMO MES SUELE ESTAR INCOMPLETO, Y COMPARARLO ENTERO ES UNA CAÍDA
   FALSA.
   El parquet corta el día que se generó (p. ej. el 21). Ese mes contra el
   mes completo del año pasado da siempre una baja que no existe. Por eso
   el mes espejo se recorta al MISMO día del mes (`_mensual(recorte=...)`)
   y la barra parcial se dibuja con trama. Es el único mes que se recorta:
   los demás están completos de los dos lados.
"""

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import (
    ACENTO, ACENTO_TEXTO, ERROR, EXITO, GRIS_BORDE, GRIS_TEXTO,
    LAVANDA_BORDE, TEXTO_PRINCIPAL,
)
from graficos.base import (
    _compras_layout, _compras_truncar, scope_rerun,
)
from graficos import alturas, periodo
from graficos.compras._comun import (
    COLUMNAS_DRILL, GAP_DRILL, PARR, _first_point, unidad_corta,
)
from tablas.compras_vs_ano_pasado import (
    _ALTO_FILA as _ALTO_FILA_DETALLE,
    _ALTO_SUB_HDR as _ALTO_SUB_HDR_DETALLE,
    _ALTO_TIT_HDR as _ALTO_TIT_HDR_DETALLE,
    renderizar_detalle_vs_ano_pasado,
)

# Alto de la fila de controles que comparte tarjeta con la serie: métrica
# (izq.) y ventana (der.) en UN renglón. Mismo criterio que
# `alturas.FRANJA_CTRL_EVO` — los píxeles de un control nuevo salen de la
# figura, o la tarjeta crece y su eje X se va debajo del borde.
_LEYENDA_VAP = 26
"""Alto de la leyenda que la serie mensual dibujaba ARRIBA de las barras
("Año pasado" gris / "Este año" acento), MEDIDA en el navegador.

Se retiró el 2026-09-02, a pedido. No hacía falta: los dos colores son la
convención de toda la app (gris = lo que pasó, acento = lo vigente), el
título de la tarjeta ya dice "Vs año pasado", y el hover —`hovermode:
x unified`— nombra las dos series al pasar por encima.

El número sigue existiendo porque se le RESTA a la figura: sin la resta, la
leyenda desaparecía y su hueco quedaba de aire. Es el mismo mecanismo que
las `alturas.FRANJA_*`, pero al revés — no se descuenta lo que ocupa otro
bloque, se descuenta lo que la figura dejó de necesitar."""

_FAM_TODAS = "Todas"
"""Primera opción del filtro de Familia de la cabecera: no filtrar.

Es un CENTINELA, no una familia: se compara por igualdad contra lo que
elige el usuario y nunca llega al filtro del df. Convive con los nombres
del parquet porque ésos vienen en MAYÚSCULAS ("ALIMENTOS", "VINOS Y
ESPUMANTES"); una familia que se llamara literalmente "Todas" lo
rompería."""

_FRANJA_VAP = alturas.FRANJA_CTRL_EVO

_ALTO_CONTENIDO_VAP = (alturas.con_franja(alturas.COMPACTO, _FRANJA_VAP)
                       - _LEYENDA_VAP)
"""Lo que mide el CONTENIDO de cada una de las dos tarjetas de la fila.

Son 214px, y de acá salen los dos altos de abajo. La cuenta se hace UNA
vez y en este nivel porque las dos tarjetas tienen que terminar en la
misma línea, y cada una gasta sus 214 en cosas distintas:

    serie    fila de controles (47)  +  figura (167)
    cascada  nombre (21) + fila rótulo+corte (30) + % (24)
             + cascada (139)

El error que esto evita es restar dos veces: si el alto de la cascada
saliera del de la SERIE, se comería también los 47 de una fila de
controles que la cascada no tiene, y la columna derecha terminaría 47px
más arriba."""

_ALTO_FIG_VAP = _ALTO_CONTENIDO_VAP - alturas.FRANJA_CTRL_SERIE
"""Alto de la SERIE mensual: el contenido de su tarjeta menos la fila de
controles que lleva encima desde el 2026-09-17 (regla #445).

OJO con el `_FRANJA_VAP` de la cuenta: hoy no muerde. `con_franja` devuelve
`min(rol, CONTENIDO - franja)` y con COMPACTO en 240 gana siempre el rol
(537 - 30 = 507). Se conserva porque el día que el rol suba, la resta
vuelve a decidir."""

_ALTO_CASCADA = (_ALTO_CONTENIDO_VAP - alturas.FRANJA_VEREDICTO
                 - alturas.FRANJA_ROTULO - alturas.FRANJA_NOMBRE_CASCADA)
"""Alto de la cascada, sea cuál sea el corte que dibuje.

De un solo sitio y no calculado en cada `_fig_*`: las tres cascadas se
turnan en la MISMA tarjeta, así que si una midiera distinto la fila
dejaría de terminar en la misma línea al cambiar de corte — el defecto que
`FRANJA_VEREDICTO` existe para evitar, pero disparado por un clic en vez
de por el layout.

Son 139px (214 − 21 − 30 − 24) y NO cambian con la fila de controles de la
serie —ésa se le resta sólo a su figura—. De ahí sale el `_TOPE_CASCADA`: el ancho de
la columna que resulta es lo que decide cuántos caracteres entran en el
rótulo de cada barra."""

_CSS = f"""
<style>
/* Retoques de los dos controles que mandan sobre la TABLA de abajo: el
   agrupador y el buscador. Es lo ÚNICO que queda acá.

   EL ESTILO DE LA CABECERA NO ESTÁ EN ESTE FICHERO. La fila del título
   —sus cinco controles, los anchos medidos uno por uno y el alto de 36px—
   se estila desde `estilos/_80_cards.py`, colgada de `.st-key-vap_fila_hdr`
   y de los cinco `.st-key-vap_hdr_*`. Si venís buscando el ancho de un
   desplegable, es allá. Ojo: el agrupador y el buscador TAMBIÉN se dibujan
   en esa fila desde el 2026-09-02 — lo que queda acá es su color y su
   cuerpo de letra, no su sitio ni su ancho.

   Acá vivían además dos bloques que el rearmado de la cabecera del
   2026-09-02 dejó muertos, y que se borraron el 2026-09-07 tras
   verificarlos contra el DOM: `compras_vap_modo` (la métrica, cuando era
   `st.pills` con sus reglas de `stButtonGroup` — hoy es un `st.selectbox`
   con key `compras_vap_modo_sel`, y un selector de CLASE no matchea por
   prefijo, así que no la alcanzaba) y `compras_vap_ventana` (una key que
   ni existe: el contenedor es `vap_hdr_ventana` y el widget,
   `compras_vap_periodo`). El segundo traía un `max-width: 130px` que era
   justo lo que mandaba a buscar acá el ancho del desplegable.

   El buscador conserva su caja —es un campo de escritura y tiene que
   parecerlo—; del agrupador se toca sólo el borde. Los dos van por su key
   PROPIA y no por la del contenedor: ése ya está estilado desde
   `_80_cards.py`, y una regla colgada de él alcanzaría a los demás
   controles de la fila. */
.st-key-compras_vap_agrupar [data-testid="stSelectbox"] div[role="group"] {{
    border-color: {LAVANDA_BORDE} !important;
}}
.st-key-compras_vap_q input {{
    font-size: 12.5px !important;
}}
</style>
"""

_MODOS = ("Valor", "Cantidad", "Precio")
_AGRUPADORES = ("Producto", "Familia", "Subfamilia")

_TITULO = "Compra Vs Año Pasado"
"""Cómo se llama la tarjeta EN PANTALLA.

"Vs año pasado" hasta el 2026-09-17: se renombró a pedido, para que el
título diga de qué son las compras y no sólo contra qué se comparan.

El nombre de la SECCIÓN del rail sigue siendo el corto ("Vs año pasado",
en `graficos/compras/__init__.py::_PILA`) y la clave interna también
(`compras_sec_vs_ano_pasado`). No es un descuido: el rail reparte su ancho
entre siete ítems y ahí el nombre largo se trunca, mientras que en la
cabecera es el elástico de la fila y tiene sitio. Un título de tarjeta y
una etiqueta de navegación no tienen por qué medir lo mismo.

Cuesta ancho: de ~110px a ~175 en la fuente de la fila. Lo paga el hueco
del título, que es `flex: 1 1 auto` — y el ⛶ que se fue el mismo día
devolvió 36, así que la fila sigue entrando en un renglón."""

_CORTES = ("Por qué", "Quién", "Cuándo")
"""Con qué eje se parte el Δ de la cascada. Los tres son la MISMA resta —
este año menos el año pasado— mirada de tres maneras:

  · «Por qué»  → efecto precio + efecto cantidad (la cascada de siempre);
  · «Quién»    → los ítems que explican la diferencia;
  · «Cuándo»   → los meses que la explican.

No son tres gráficos distintos que compiten por el sitio: son tres cortes
del mismo número, y por eso viven en UN control y no en tres. Ver
`_cortes_disponibles`, que es donde está la parte que importa."""

_CORTE_DEFAULT = _CORTES[0]

_COLS_PUENTE = [2.86, 1]
"""Cómo se parte la fila de arriba de la cascada: veredicto | corte.

No es un `COLUMNAS_DRILL` disfrazado —eso rige el eje de la PÁGINA— sino
una subdivisión interna, de las que el proyecto marca con
`# columnas-internas:`. Sale de una cuenta: la tarjeta mide 434px, su
contenido 402, el `gap="small"` se lleva 16 y el desplegable necesita 100
(el mismo ancho MEDIDO que tenía en la cabecera). Quedan 286 para el
texto, y 286/100 = 2.86."""

_K_FOCO_TOCADO = "compras_vap_foco_tocado"
"""Si el usuario ya tocó la selección de la tabla, en cualquier sentido.

Existe para distinguir los dos "sin foco" que `compras_vap_foco` no
distingue: **nadie eligió todavía** (hay que sembrar el primer ítem) y
**el usuario soltó el foco** (hay que respetarlo y mostrar todas las
compras). Sin esta marca, soltar el foco sería imposible: el rerun
siguiente lo volvería a sembrar. Ver la regla #445."""

_K_CORTE = "compras_vap_corte"
"""El corte elegido, ESPEJO de la key del selector.

El widget vive en `compras_vap_corte_sel` y no se dibuja cuando ningún
corte aplica (modo Precio). Un widget que deja de renderizarse pierde su
estado, así que la preferencia se guarda acá, donde nadie la recolecta.
Ver el bloque «CON QUÉ EJE SE PARTE EL Δ» de la cabecera."""

_K_MES = "compras_vap_mes"
"""La etiqueta del mes elegido en la serie ("ago 26"), o None.

Es ÁMBITO, no filtro: recorta lo que explica la cascada de la derecha, y
no toca ni la serie ni la tabla — las dos siguen mostrando la ventana
entera, porque el clic es una pregunta sobre un mes, no un zoom."""

_K_NCLIC = "compras_vap_nclic"
"""Cuántos clics de mes se atendieron. Va en la key del gráfico para que
cada uno nazca sin selección (regla #399, receta del contador)."""

_OPACIDAD_APAGADA = 0.35
"""Cuánto queda de un mes que NO es el que explica la cascada.

0.35 y no menos: por debajo de ~0.3 una barra gris sobre fondo blanco deja
de distinguirse de la cuadrícula, y la serie tiene que seguir leyéndose
como serie — el mes elegido se destaca, los otros no desaparecen."""

_KEY_SERIE = "compras_g_vap_serie"
"""Base de la key de la serie mensual, SIN el modo.

Hasta el 2026-09-16 era `compras_g_vap_{modo}`, una key por métrica. Con el
clic de mes eso no sirve: la key tiene que resolverse arriba de todo, antes
de que se sepa el modo, y además el contador ya garantiza que cada clic
estrene widget. Una key por modo, encima, tiraba el mes elegido al cambiar
de métrica — y el mes es ortogonal a la métrica."""


def _cortes_disponibles(modo, un_item, un_mes, unidad=""):
    """`(los cortes que aplican, {corte descartado: por qué})`.

    UN CORTE SE OFRECE SÓLO SI LA MAGNITUD ES ADITIVA EN ESE EJE Y EL
    ÁMBITO TIENE MÁS DE UN ELEMENTO. De esa sola regla salen los cinco
    casos, y ninguno es una excepción escrita a mano:

      · En **Precio** no se salva ninguno. Un precio es un RATIO: la suma
        de los precios de tres meses no es el precio del trimestre, ni la
        de dos productos el de la familia. Partirlo por cualquier eje da
        barras que no suman al total — es la misma trampa que `_por_item`
        evita desde el 2026-08-24 (ver su docstring: efecto precio
        −540.105 y efecto cantidad +504.339 para explicar un Δ de −35.766).
      · En **Cantidad** se cae «Por qué», porque en kilos no hay un efecto
        precio que separar: el Δ de cantidad ES la cantidad.
      · «Quién» se cae con un solo ítem y «Cuándo» con un solo mes, por lo
        mismo que no se dibuja una torta de una porción.

    LOS DESCARTADOS SE DEVUELVEN CON SU MOTIVO, no se tragan: el llamador
    los escribe en el `help` del control. Un control que ofrece tres cosas
    hoy y una mañana, sin decir por qué, se lee como un bug — es el mismo
    criterio que la opción «Todas» del filtro de Familia, que existe para
    que el campo diga siempre qué está haciendo (ver `_FAM_TODAS`).

    `unidad` es la corta ("kg"): entra en el motivo de Cantidad para que
    diga "en kg no hay efecto precio" y no una frase de manual.
    """
    fuera = {}
    if modo == "Precio":
        return (), {c: "un precio no se suma" for c in _CORTES}
    if modo == "Cantidad":
        fuera["Por qué"] = f"en {unidad or 'unidades'} no hay efecto precio"
    if un_item:
        fuera["Quién"] = "ya hay un solo ítem"
    if un_mes:
        fuera["Cuándo"] = "ya hay un solo mes"
    return tuple(c for c in _CORTES if c not in fuera), fuera


def _ayuda_corte(fuera):
    """El `help` del selector de corte: qué quedó afuera y por qué.

    Vacío si no falta ninguno — un `help` que dice "no pasa nada" es ruido
    en una fila que ya tiene siete controles."""
    if not fuera:
        return ("Con qué eje se parte la diferencia contra el año pasado: "
                "por efecto precio/cantidad, por ítem o por mes.")
    return "Con qué eje se parte la diferencia. Ahora no aplican: " + "; ".join(
        f"«{c}», {fuera[c]}" for c in _CORTES if c in fuera) + "."

_ETIQ_VENTANA = {
    periodo.HEREDA: "📅 Rango",
    "3m": "📅 Últimos 3 meses",
    "12m": "📅 Últimos 12 meses",
    "24m": "📅 Últimos 24 meses",
    "Todo": "📅 Todo el histórico",
}
"""Cómo se LEE cada opción de la ventana en esta cabecera. Sólo texto.

`periodo.OPCIONES` viene en el idioma corto de una fila de pastillas ("3m",
"12m"), que es lo que la fila de Volatilidad o la de Producto necesitan. Acá
el desplegable comparte renglón con otros cuatro que tampoco tienen etiqueta
—métrica, familia, agrupador, buscador—, y "12m" suelto no dice de qué
habla: reportado el 2026-09-07, pidiendo "el selector de fecha" para una
tarjeta que ya lo tenía a la vista.

El ícono no es adorno: es lo único que separa a este control de los otros
cuatro de un vistazo. Ojo con el ancho — la fila los reparte a lo fijo en
`estilos/_80_cards.py`, y el hueco de éste se agrandó a la vez que estas
etiquetas. `proveedor.py` tuvo que sacar su emoji por eso mismo, pero su
fila mide 279px; ésta es el ancho entero de la tarjeta.

Un `dict` y no un `format_func` con `if`: la lista de opciones la manda
`periodo.OPCIONES`, así que una opción nueva allá aparece acá con su nombre
crudo en vez de reventar."""


def _etiq_ventana(opcion):
    """`format_func` del selector de ventana. Ver `_ETIQ_VENTANA`.

    Cae al nombre crudo si la opción no está mapeada — el valor que devuelve
    el widget es SIEMPRE la cadena de `periodo.OPCIONES`, así que esto no
    puede desincronizar las comparaciones (`ventana == periodo.HEREDA`)."""
    return _ETIQ_VENTANA.get(opcion, str(opcion))


# ===========================================================================
# FUNCIONES PURAS (las fija test_graficos.py)
# ===========================================================================

def _mensual(d, col_prod, col_fecha, col_valor, col_cant, col_grupo=None,
             recorte=None):
    """Una fila por (prod, mes) con `valor`, `cant` y `grupo`.

    `mes` es un `pandas.Period[M]`, para poder sumarle 12 y caer en el mismo
    mes del año siguiente sin aritmética de calendario a mano.

    `recorte` es `(Period, dia)`: ese mes —y sólo ése— se suma hasta ese día
    del mes inclusive. Lo usa el mes ESPEJO del último mes parcial (ver la
    decisión 3 del docstring del módulo); el resto de los meses se suman
    enteros.

    `grupo` es la columna con la que la tabla de abajo puede agrupar
    (Familia/Subfamilia). Cae al propio producto si no se pasa una.
    """
    if d is None or getattr(d, "empty", True) or not (col_prod and col_fecha):
        return pd.DataFrame(columns=["prod", "grupo", "mes", "valor", "cant"])
    fe = pd.to_datetime(d[col_fecha], errors="coerce")
    base = pd.DataFrame({
        "prod": d[col_prod].astype(str).values,
        "grupo": (d[col_grupo].astype(str).values
                  if col_grupo and col_grupo in d.columns
                  else d[col_prod].astype(str).values),
        "fecha": fe.values,
        "valor": (pd.to_numeric(d[col_valor], errors="coerce").fillna(0).values
                  if col_valor else 0.0),
        "cant": (pd.to_numeric(d[col_cant], errors="coerce").fillna(0).values
                 if col_cant else 0.0),
    }).dropna(subset=["fecha"])
    if base.empty:
        return pd.DataFrame(columns=["prod", "grupo", "mes", "valor", "cant"])
    base["mes"] = base["fecha"].dt.to_period("M")
    if recorte is not None:
        mes_rec, dia_rec = recorte
        fuera = (base["mes"] == mes_rec) & (base["fecha"].dt.day > dia_rec)
        base = base[~fuera]
    g = (base.groupby(["prod", "mes"], as_index=False)
             .agg(valor=("valor", "sum"), cant=("cant", "sum"),
                  grupo=("grupo", "first")))
    return g[["prod", "grupo", "mes", "valor", "cant"]]


def _con_ano_pasado(g_actual, g_fuente=None):
    """`g_actual` + las columnas `valor_aa`/`cant_aa` del mismo mes del año
    anterior, tomadas de `g_fuente` (por defecto, de sí mismo).

    Las dos fuentes se separan por el mes parcial: `g_actual` nunca se
    recorta (es lo que se compró de verdad) y `g_fuente` sí, para que el
    espejo del mes parcial mida los mismos días.

    El `merge` es OUTER a propósito: un ítem que se compraba el año pasado y
    este año no, no tiene fila en `g_actual` — y es justamente la baja que
    hay que ver. Sale con `valor` 0 y `valor_aa` > 0.

    Descarta los meses ANTERIORES al primero comparable (primer mes con dato
    + 12): ahí no hay año pasado que mirar, y dibujarlos con un 0 se lee
    como "ese año no compramos nada", que es una mentira distinta.
    """
    cols = ["prod", "grupo", "mes", "valor", "cant", "valor_aa", "cant_aa"]
    if g_actual is None or g_actual.empty:
        return pd.DataFrame(columns=cols)
    fuente = g_actual if g_fuente is None else g_fuente
    prev = fuente[["prod", "mes", "valor", "cant"]].copy()
    prev["mes"] = prev["mes"] + 12
    prev = prev.rename(columns={"valor": "valor_aa", "cant": "cant_aa"})

    out = g_actual.merge(prev, on=["prod", "mes"], how="outer")
    # `grupo` viaja pegado al producto, no al mes: las filas que aporta el
    # outer (bajas) lo traen vacío y se rellena desde el mapa del producto.
    mapa = (g_actual.dropna(subset=["grupo"])
                    .drop_duplicates("prod").set_index("prod")["grupo"])
    out["grupo"] = out["grupo"].fillna(out["prod"].map(mapa)).fillna(out["prod"])
    for c in ("valor", "cant", "valor_aa", "cant_aa"):
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    # PISO: el primer mes comparable (primer mes con dato + 12). Antes de
    # eso no hay año pasado que mirar, y pintar esos meses con un 0 se lee
    # como "ese año no compramos nada", que es una mentira distinta.
    # TECHO: el último mes con compras REALES. El merge es outer, así que el
    # desplazamiento de 12 meses también inventa filas DESPUÉS del final del
    # histórico (medido: llegaba hasta 2027-08 con `valor` 0 y `valor_aa` >
    # 0). Eso no es una baja, es un mes que todavía no pasó.
    piso = fuente["mes"].min() + 12
    techo = g_actual["mes"].max()
    out = out[(out["mes"] >= piso) & (out["mes"] <= techo)]
    return out[cols].sort_values(["mes", "prod"]).reset_index(drop=True)


def _puente(valor, cant, valor_aa, cant_aa):
    """`(efecto_precio, efecto_cantidad)` de la diferencia contra el año
    pasado. Los dos SIEMPRE suman `valor - valor_aa`.

        Δ = (p − p_aa)·q + (q − q_aa)·p_aa,   con p = valor/cant

    Con `cant_aa` en 0 no hay precio del otro lado (el ítem es nuevo): el
    efecto es 100% cantidad. Con `cant` en 0 pasa lo mismo del otro lado (el
    ítem se dejó de comprar). En los dos casos el precio no explica nada, y
    forzar un efecto precio ahí sería inventarlo.
    """
    delta = float(valor) - float(valor_aa)
    if cant_aa <= 0 or cant <= 0:
        return 0.0, delta
    p_aa = float(valor_aa) / float(cant_aa)
    ef_precio = float(valor) - p_aa * float(cant)
    return ef_precio, delta - ef_precio


def _por_item(g, llave="prod"):
    """`g` agregado por `llave`, con el puente ya calculado y sumado.

    EL PUENTE SE CALCULA SIEMPRE A NIVEL PRODUCTO, y recién después se suma
    al grupo. Calcularlo sobre el agregado da un número que CIERRA pero que
    no significa nada: el "precio" de un grupo sería `Σvalor / Σcantidad`,
    o sea kilos, litros, unidades y servicios sumados en el mismo
    denominador. Medido con el parquet real el 2026-08-24, la familia
    GASTOS VENTAS daba efecto precio −540.105 y efecto cantidad +504.339
    para explicar un Δ de −35.766: dos cifras quince veces más grandes que
    lo que explicaban, que se cancelaban entre sí.

    Sumar los efectos por producto sí es correcto y sigue cerrando: cada
    sumando es un Δ real de un ítem con UNA unidad, y
    Σ(ef_precio + ef_cant) = Σ(valor − valor_aa) = Δ del grupo.

    `n_items` (cuántos productos hay detrás) viaja en el resultado porque es
    lo único que la tabla puede decir del "precio" de un grupo.
    """
    cols = ["valor", "cant", "valor_aa", "cant_aa"]
    base = g.groupby(["prod"] if llave == "prod" else ["prod", llave],
                     as_index=False)[cols].sum()
    efectos = [_puente(r.valor, r.cant, r.valor_aa, r.cant_aa)
               for r in base.itertuples()]
    base["ef_precio"] = [e[0] for e in efectos]
    base["ef_cant"] = [e[1] for e in efectos]
    base["n_items"] = 1
    if llave == "prod":
        return base.rename(columns={"prod": "item"})
    return (base.groupby(llave, as_index=False)[
        cols + ["ef_precio", "ef_cant", "n_items"]].sum()
        .rename(columns={llave: "item"}))


_ETQ_BORDES = ("Año<br>pasado", "Este<br>año")
"""Las dos barras de los bordes de cualquier cascada, cuando no se sabe de
qué años se está hablando. Es el fallback de `_etq_anios`."""


def _etq_anios(meses):
    """`("2025", "2026")` para las barras de los bordes de la cascada.

    2026-09-17, a pedido: *«cuando la cascada diga año pasado y este año,
    deberá mostrar el año en número»*. «Este año» no es un año calendario
    sino LA VENTANA de la tarjeta, así que el número sale de los meses que
    hay en pantalla y no de `today().year`:

        3 meses  jul–sep 26   →  «2025»      «2026»
        12 meses oct 25–sep 26 → «2024-25»   «2025-26»

    Con la ventana a caballo de dos años calendario decir «2026» sería
    falso — y es el caso del default anterior (12m) y de «Todo». Sin meses
    cae a los rótulos de siempre: un año inventado es peor que la palabra.
    """
    anios = sorted({m.year for m in meses}) if len(meses) else []
    if not anios:
        return _ETQ_BORDES
    if len(anios) == 1:
        return (str(anios[0] - 1), str(anios[0]))
    a, b = anios[0], anios[-1]
    return (f"{a - 1}-{str(b - 1)[-2:]}", f"{a}-{str(b)[-2:]}")


def _llano(etq):
    """La etiqueta de una barra sin el `<br>` con que se parte en dos
    renglones: lo que va en el EJE lleva el salto, lo que va en el TOOLTIP
    no — ahí un `<br>` parte la frase a la mitad."""
    return str(etq).replace("<br>", " ")


_TOPE_CASCADA = 3
"""Cuántas barras NOMBRADAS entran en una cascada de «Quién» o «Cuándo».

NO ES UN GUSTO, Y LA PRIMERA CUENTA ESTABA MAL. Medido en el navegador el
2026-09-16 con la vista ya dibujada (viewport 1280): el área de trazo del
puente mide **378px**, y el eje rotula en **12px**, no en los 9 que yo
había supuesto — o sea ~6,9px por carácter. Con 4 nombradas son 7 columnas
de 54px para rótulos de 67-69px: **cinco de los seis pares se pisaban**,
contados uno por uno en el DOM.

Con 3 son 6 columnas de 63px, y con el eje bajado a `_FUENTE_EJE_CASCADA`
el rótulo más ancho mide 59: entra con 4px de holgura. Es el mismo
criterio de la regla #325 —medir el rótulo contra la columna REAL, no
contra la declarada— y su corolario de la #352: cuántas columnas caben lo
decide el dato más ancho.

Se paga en información: la barra «otros N» se lleva más Δ. Por eso el
nombre entero de cada barra va en el hover (`_hover_cascada`), que es
gratis en píxeles."""

_FUENTE_EJE_CASCADA = 11
"""Tamaño del rótulo del eje en las cascadas de «Quién» y «Cuándo».

Un punto menos que el resto de la app (12px, el de `_compras_layout`), y
sólo acá: es lo que hace entrar 10 caracteres en una columna de 63px
(medido: 59px contra 63). Bajarlo a 10 daba 6px más de holgura y se leía
peor; a 12 no entra. `_fig_puente` NO lo toca — sus cuatro rótulos son
fijos y cortos ("Efecto precio"), así que no tiene por qué encoger."""


def _pasos_cascada(partes, valor_aa, valor, tope=_TOPE_CASCADA,
                   cronologico=False, resto="otros", bordes=_ETQ_BORDES):
    """Los pasos de una cascada de contribuyentes, con la cola sumada.

    `partes` es `[(nombre, delta)]`. Entran las `tope` de mayor |Δ| y todo
    lo demás se suma en UNA barra «otros N».

    ESA BARRA NO ES RELLENO, es el veredicto sobre esta forma de mirar:
    dice cuánto del Δ no llegó a nombrarse. Medido contra el parquet el
    2026-09-16, con la ventana por defecto y las cuatro familias de
    entrada, el reparto cambia el juicio según el mes:

        jul 26   los 5 nombrados explican el 31 % del Δ del mes
        ago 26                                18 %
        sep 26                                58 %
        trimestre                             27 %

    O sea que «Quién» es una LECTURA CORRECTA en septiembre y una lista de
    inocentes en agosto. Por eso es un corte a elección y no la forma fija
    de la tarjeta — y por eso el llamador escribe ese porcentaje al lado.

    `cronologico` es para «Cuándo»: los meses se ELIGEN por |Δ| (si no
    entran todos) pero se DIBUJAN en orden de calendario. Una cascada de
    tiempo con los meses barajados por tamaño no se puede leer.
    """
    orden = sorted(range(len(partes)), key=lambda i: -abs(partes[i][1]))
    cabeza = orden[:tope]
    if cronologico:
        cabeza = sorted(cabeza)
    cola = [i for i in range(len(partes)) if i not in set(cabeza)]
    pasos = [{"label": bordes[0], "medida": "absolute",
              "valor": float(valor_aa)}]
    for i in cabeza:
        pasos.append({"label": _etq_barra(partes[i][0]), "medida": "relative",
                      "valor": float(partes[i][1])})
    if cola:
        pasos.append({"label": f"{resto}<br>{len(cola)}", "medida": "relative",
                      "valor": float(sum(partes[i][1] for i in cola))})
    pasos.append({"label": bordes[1], "medida": "total",
                  "valor": float(valor)})
    return pasos


_ANCHO_ETQ_BARRA = 10
"""Caracteres por renglón del rótulo de una barra de la cascada.

MEDIDO, y la primera versión de esta función estaba mal: cortaba a 12 el
SEGUNDO renglón pero dejaba el primero de hasta 22 ("Magret De Pato Macho
x"), así que el rótulo medía 138px donde la columna mide 54 y **cinco de
los seis pares de rótulos se pisaban** (contados en el DOM el 2026-09-16
con el eje ya dibujado: 378px de área de trazo / 7 barras).

10 caracteres son ~50px en la fuente del eje (9px), o sea el ancho de una
columna. Va con nombre propio porque es la contraparte de
`_TOPE_CASCADA`: cuántas barras entran y cuánto mide cada rótulo son el
mismo presupuesto mirado por los dos lados."""


def _etq_barra(nombre, ancho=_ANCHO_ETQ_BARRA):
    """El rótulo de una barra de la cascada: corto y en DOS renglones.

    Parte por la última palabra que ENTRA en el renglón, no a la mitad de
    una — y si la primera palabra ya no entra, trunca con "…" para que el
    recorte se VEA (misma convención que `_compras_truncar` en el resto de
    la app: un nombre cortado en seco se lee como un nombre distinto)."""
    s = str(nombre).strip()
    if len(s) <= ancho:
        return s
    corte = s.rfind(" ", 0, ancho + 1)
    if corte <= 0:
        return _compras_truncar(s, ancho)
    return f"{s[:corte]}<br>{_compras_truncar(s[corte + 1:], ancho)}"


def _pasos_simple(valor_aa, valor, etq="Δ", bordes=_ETQ_BORDES):
    """Cascada de TRES barras: de dónde a dónde, sin partir nada.

    Es lo que queda cuando ningún corte aplica (ver `_cortes_disponibles`):
    en Precio siempre, y en Cantidad con un mes elegido. No es un gráfico
    degradado por accidente — es el techo honesto de esa magnitud, y
    dibujarlo así lo dice mejor que un párrafo."""
    return [{"label": bordes[0], "medida": "absolute",
             "valor": float(valor_aa)},
            {"label": etq, "medida": "relative",
             "valor": float(valor) - float(valor_aa)},
            {"label": bordes[1], "medida": "total", "valor": float(valor)}]


def _mes_parcial(fechas):
    """`(Period del último mes, día de corte)` si el último mes con datos
    está incompleto; `None` si cierra en fin de mes.

    "Incompleto" se mide contra el propio dato, no contra hoy: el parquet se
    regenera de madrugada y los documentos entran con retraso, así que el
    último día CON DATOS es la única referencia honesta (mismo criterio que
    el ancla de `graficos/periodo.py`).
    """
    fechas = pd.to_datetime(fechas, errors="coerce").dropna()
    if fechas.empty:
        return None
    fin = fechas.max()
    if fin.day == fin.days_in_month:
        return None
    return fin.to_period("M"), int(fin.day)


def _etiqueta_mes(periodo_m):
    """"ago 25" — corto, porque el eje puede llevar 30 de éstos."""
    _MES = ("ene", "feb", "mar", "abr", "may", "jun",
            "jul", "ago", "sep", "oct", "nov", "dic")
    return f"{_MES[periodo_m.month - 1]} {periodo_m.year % 100:02d}"


def _rango_meses(m0, m1):
    """"oct 25 – sep 26", para el subtítulo de la cabecera de la tabla.

    Un solo mes no se escribe dos veces ("sep 26", no "sep 26 – sep 26"):
    la ventana "Rango" puede tocar uno solo.
    """
    a, b = _etiqueta_mes(m0), _etiqueta_mes(m1)
    return a if a == b else f"{a} – {b}"


# ── Etiquetas de valor sobre la serie mensual ───────────────────────────────
# 2026-09-13, a pedido: «colocar etiquetas visibles en las columnas, tanto en
# la vista de cantidad, valor y precio». Hasta ese día la serie no llevaba
# ningún número: el valor sólo salía en el hover.
#
# "Visibles" es la palabra que manda, y por eso esto es una CUENTA y no un
# `text=` suelto: Plotly no oculta una etiqueta que no entra, la ENCOGE (con
# `constraintext`) o la pisa con la vecina (sin él) — sigue en el DOM y ya
# no se lee. Es la trampa de la regla #91, y la de la Evolución de Producto
# (`producto.py`, "LA ETIQUETA ROTA SI NO ENTRA"). Así que la forma de la
# etiqueta sale de los PÍXELES que hay por columna, que dependen de cuántos
# meses muestra la ventana: 3 (el default) no se parece a 32 ("Todo").
# Ver `arquitectura.md` regla #400.

_ETQ_FUENTE = 10
"""Cuerpo de letra de las etiquetas, en px. El mismo de las de Producto."""

_ETQ_PX_CARACTER = 5.4
"""Ancho medio de un carácter de etiqueta a `_ETQ_FUENTE` en DM Sans,
MEDIDO en el navegador con `measureText` sobre etiquetas reales
(2026-09-13): "S/ 107.9k" 40px (4,4 por carácter), "S/ 12.35" 36px (4,5),
"S/ 480" y "245.0k" 32px (5,3 — las cortas pesan más por carácter). Se usa
el techo: sobrar un píxel sólo gira antes una etiqueta que entraba
derecha; faltar uno las encima."""

_ETQ_ALTO_LINEA = 13
"""Alto de UNA línea de etiqueta a `_ETQ_FUENTE` (medido: ascent + descent
= 13px). Es lo que ocupa una etiqueta derecha hacia arriba, y lo que ocupa
GIRADA hacia el costado."""

_ETQ_AIRE = 4
"""Separación entre etiquetas vecinas, y entre la etiqueta y el borde."""

_ANCHO_PLOT_VAP = 675
"""Ancho del ÁREA DE TRAZO de la serie mensual (`.nsewdrag`), MEDIDO a
1366x768 con la tarjeta en la pila (2026-09-13; figura 730 de ancho) — el
caso angosto: en modo solo (⛶) la tarjeta crece y sobra lugar. En
ventanas más angostas que 1366 las etiquetas pueden rozarse; el hover
sigue diciendo el número exacto."""

_ALTO_PLOT_VAP = 149
"""Alto del área de trazo de la serie mensual, MEDIDO en el navegador
(figura 214 − márgenes 30+10 − rótulos del eje X). Es contra lo que se
reparte el techo que necesitan las etiquetas (`_techo_con_etiquetas`)."""

_BARGAP_VAP = 0.28
"""`bargap` de la serie. Vive acá y no sólo en el `update_layout` porque
decide cuánto espacio hay entre dos columnas del mismo mes, que es contra
lo que se mide si una etiqueta entra derecha."""


def _fmt_etiqueta(v, modo, unidad=None):
    """El número que va ENCIMA de la columna (o del punto, en Precio).

    Compacto en Valor y Cantidad —"S/ 107.9k" entra donde "S/ 107,911" no—,
    con UN decimal en los miles para que tres meses parecidos no se lean
    iguales ("S/ 107.9k" vs "S/ 108.4k"; con "S/ 108k" los dos lo serían).
    El número exacto sigue en el hover. Precio va entero con sus dos
    decimales: es un precio unitario, y "S/ 12.3" no es el precio de nada.

    `None` para un cero o un vacío: una columna que no existe no lleva
    rótulo, y un "S/ 0" flotando sobre el eje se lee como una marca más.
    """
    if v is None or pd.isna(v) or float(v) == 0:
        return None
    v = float(v)
    u = str(unidad or "").strip()
    if modo == "Precio":
        # Con unidad es el precio POR esa unidad ("S/ 12.35/kg"): así lo
        # usa el segundo renglón de Valor y Cantidad.
        return f"S/ {v:,.2f}/{u}" if u else f"S/ {v:,.2f}"
    a = abs(v)
    if modo == "Cantidad" and u:
        # Con unidad, ENTERA hasta los 100 mil — "4,300 kg", el ejemplo del
        # pedido. Compacta sería "4.3k kg": dos sufijos pegados, y el "k"
        # de miles al lado del "kg" de kilos se lee como un error de tipeo.
        if a >= 100_000:
            return f"{v / 1_000:,.1f}k {u}"
        if a < 10 and v != round(v):
            return f"{v:,.1f} {u}"
        return f"{v:,.0f} {u}"
    pre = "S/ " if modo == "Valor" else ""
    if a >= 1_000_000:
        return f"{pre}{v / 1_000_000:,.2f}M"
    if a >= 1_000:
        return f"{pre}{v / 1_000:,.1f}k"
    if modo == "Cantidad" and a < 10 and v != round(v):
        return f"{pre}{v:,.1f}"
    return f"{pre}{v:,.0f}"


def _plan_etiquetas(n, largo_max, modo, ancho_plot=_ANCHO_PLOT_VAP,
                    largo_sec=0):
    """Cómo se dibujan las etiquetas de `n` meses cuya etiqueta más larga
    tiene `largo_max` caracteres. Devuelve un dict:

      · `girar`: la etiqueta va vertical (sólo barras).
      · `ambas`: rotulan las DOS series; si no, sólo "Este año".
      · `paso`: se rotula uno de cada `paso` meses (1 = todos).
      · `sec`: la etiqueta lleva el SEGUNDO renglón (el precio unitario,
        `largo_sec` caracteres). Es lo primero que cede: con 12 meses las
        dos series siguen rotuladas y el precio pasa al hover, porque el
        gráfico es una COMPARACIÓN y perder la etiqueta del año pasado es
        perder la mitad de la lectura. Sólo con "Este año" solo (24m,
        Todo) vuelve, si entra girado en el mes entero.

    Barras: dos columnas del MISMO mes están a `grupo·(1−bargap)/2` px de
    centro a centro, y ése es el apretón que manda. Derecha si la etiqueta
    entra en ese hueco; si no, girada (ocupa `_ETQ_ALTO_LINEA` de ancho);
    si ni así, sólo "Este año", girada, cuyas vecinas están a un mes
    entero de distancia. Con 3 meses sale derecha, con 12 girada, con 32
    ("Todo") sólo este año.

    Precio: los dos puntos de un mes se rotulan uno arriba y otro abajo
    (ver `_fig_serie`), así que no chocan entre sí: chocan con el mes de al
    lado, que está a `grupo` px. Si no entran, queda sólo "Este año",
    arriba, uno de cada `paso` meses.
    NO se alterna arriba/abajo, y se probó: con 24 meses daba 3 choques
    medidos en el navegador. Dos vecinas en lados OPUESTOS siguen a un mes
    de distancia, y cuando la línea salta la de abajo del mes alto cae
    justo sobre la de arriba del mes bajo — la alternancia sólo separa las
    del mismo lado, y el choque venía del otro.

    El `paso` es el último recurso, para históricos tan largos que ni eso
    alcanza: mejor la mitad de los números legibles que todos encimados.
    """
    plan = {"girar": False, "ambas": True, "paso": 1, "sec": False}
    if n <= 0:
        return plan
    grupo = ancho_plot / n
    txt_px = largo_max * _ETQ_PX_CARACTER + _ETQ_AIRE
    lin_px = _ETQ_ALTO_LINEA + _ETQ_AIRE
    if modo == "Precio":
        if txt_px <= grupo:
            return plan
        plan.update(ambas=False, paso=max(1, math.ceil(txt_px / grupo)))
        return plan
    hueco = grupo * (1 - _BARGAP_VAP) / 2
    lin2_px = 2 * _ETQ_ALTO_LINEA + _ETQ_AIRE
    if largo_sec:
        txt2_px = max(largo_max, largo_sec) * _ETQ_PX_CARACTER + _ETQ_AIRE
        if txt2_px <= hueco:
            return dict(plan, sec=True)
        if lin2_px <= hueco:
            return dict(plan, girar=True, sec=True)
    if txt_px <= hueco:
        return plan
    plan["girar"] = True
    if lin_px <= hueco:
        return plan
    plan["ambas"] = False
    if largo_sec and lin2_px <= grupo:
        return dict(plan, sec=True)
    plan["paso"] = max(1, math.ceil(lin_px / grupo))
    return plan


_ETQ_FUENTE_SEC = 9
"""Cuerpo del segundo renglón (el precio): un punto menos que el principal
y en gris, para que se lea como dato de apoyo y no como otra serie."""


def _con_segundo(principal, segundo):
    """El principal y, debajo, el segundo renglón en chico y apagado.

    Sin principal no hay etiqueta (la columna no existe) y sin segundo queda
    el principal solo — p. ej. un mes con valor pero sin cantidad cargada,
    donde el precio no se puede calcular. El `<span style>` lo entiende el
    texto de una traza de Plotly: es su subconjunto de HTML, el mismo del
    `<br>`."""
    if not principal or not segundo:
        return principal
    return (f"{principal}<br><span style='font-size:{_ETQ_FUENTE_SEC}px;"
            f"color:{GRIS_TEXTO}'>{segundo}</span>")


def _ralear(etiquetas, paso):
    """Deja una de cada `paso` etiquetas, contando DESDE EL FINAL: el último
    mes —el que se está mirando— lleva número siempre."""
    if paso <= 1:
        return etiquetas
    n = len(etiquetas)
    return [t if (n - 1 - i) % paso == 0 else None
            for i, t in enumerate(etiquetas)]


def _techo_con_etiquetas(hi, lo, alto_etq, simetrico=False,
                         alto_plot=_ALTO_PLOT_VAP):
    """`[ymin, ymax]` del eje Y con lugar para `alto_etq` px de etiqueta.

    `textposition="outside"` NO agranda el rango solo: la etiqueta de la
    columna más alta queda contra el borde y se corta (medido en Producto,
    mismo motivo del `range` de allá). La cuenta es en píxeles: si el área
    de trazo mide `alto_plot` y la etiqueta necesita `alto_etq`, el dato
    tiene que ocupar `alto_plot − alto_etq` y el rango crece en esa
    proporción.

    `simetrico` es Precio: sus etiquetas van arriba Y abajo de la línea, y
    el eje no arranca en 0 (es un ratio, lo que se lee es la forma).
    """
    alto_etq = min(alto_etq, alto_plot * 0.45)
    if not simetrico:
        base = min(0.0, lo)
        span = hi - base
        if span <= 0:
            return None
        return [base, base + span * alto_plot / (alto_plot - alto_etq)]
    span = hi - lo
    if span <= 0:
        span = abs(hi) * 0.2 or 1.0
    pad = span * alto_etq / (alto_plot - 2 * alto_etq)
    return [lo - pad, hi + pad]


# ===========================================================================
# GRÁFICOS
# ===========================================================================

def _fig_serie(g, modo, parcial, unidad=None, con_precio=False, mes_sel=None):
    """Serie mensual: este año contra el mismo mes del año pasado.

    `unidad` ("kg") va pegada a la etiqueta de Cantidad, y `con_precio`
    agrega debajo de cada etiqueta de Valor/Cantidad el precio unitario de
    ese mes. Los dos los decide el llamador, que es el que sabe si la serie
    es UN producto con UNA unidad (ver regla #401): esta función no puede
    distinguir 4.300 kg de 4.300 "cosas".

    Valor y Cantidad van en barras agrupadas (son magnitudes que se suman y
    la comparación es de altura contra altura). Precio va en líneas: es un
    ratio, no se apila, y lo que interesa es la FORMA de la curva.

    `mes_sel` es la etiqueta del mes que está explicando la cascada de al
    lado ("ago 26"). Los demás se APAGAN al 35 %, y ésa es toda la marca:
    la serie no se recorta ni se reordena, porque el clic es una pregunta
    sobre un mes y no un zoom — si se recortara, no quedaría dónde hacer el
    clic siguiente. Con la selección nativa de Plotly no alcanzaba: la
    pinta el gráfico al seleccionar y se va en el rerun, y acá el gráfico
    nace SIN selección a propósito (regla #399, receta del contador).
    """
    por_mes = g.groupby("mes", as_index=False)[
        ["valor", "cant", "valor_aa", "cant_aa"]].sum().sort_values("mes")
    if por_mes.empty:
        st.info("Sin meses comparables en esta ventana.")
        return None

    if modo == "Valor":
        y_act, y_aa, fmt = por_mes["valor"], por_mes["valor_aa"], "S/ %{y:,.0f}"
    elif modo == "Cantidad":
        # El hover dice la unidad igual que la etiqueta: "225.0" pelado, en
        # una tarjeta de soles, se lee como soles (regla #335).
        y_act, y_aa = por_mes["cant"], por_mes["cant_aa"]
        fmt = "%{y:,.1f}" + (f" {unidad}" if unidad else "")
    else:
        # `.where(> 0)` y no `replace(0, NA)`: sobre una serie float, NA
        # la vuelve object y Plotly deja de saber que es un eje numérico.
        y_act = por_mes["valor"] / por_mes["cant"].where(por_mes["cant"] > 0)
        y_aa = por_mes["valor_aa"] / por_mes["cant_aa"].where(
            por_mes["cant_aa"] > 0)
        fmt = "S/ %{y:,.2f}"

    etiquetas = [_etiqueta_mes(m) for m in por_mes["mes"]]
    # El mes parcial se marca en la BARRA (trama) y en su etiqueta, no en un
    # caption al pie: el que lo tiene que ver está mirando la última barra.
    es_parcial = [parcial is not None and m == parcial[0] for m in por_mes["mes"]]

    # ── Etiquetas de valor (2026-09-13, a pedido). La forma sale de los
    # píxeles por mes: ver `_plan_etiquetas` y regla #400.
    #
    # Segunda vuelta del pedido, el mismo día: Cantidad dice su UNIDAD
    # ("4,300 kg") y Valor y Cantidad llevan un SEGUNDO renglón con el
    # precio unitario del mes ("S/ 12.35/kg"). Precio no cambia: su número
    # ya es el precio, y "/kg" le haría perder la etiqueta del año pasado
    # desde los 12 meses.
    _um_etq = unidad if modo == "Cantidad" else None
    etq_act = [_fmt_etiqueta(v, modo, _um_etq) for v in y_act]
    etq_aa = [_fmt_etiqueta(v, modo, _um_etq) for v in y_aa]
    sec_act = sec_aa = [None] * len(por_mes)
    _con_sec = con_precio and modo != "Precio"
    if _con_sec:
        _p = por_mes["valor"] / por_mes["cant"].where(por_mes["cant"] > 0)
        _p_aa = por_mes["valor_aa"] / por_mes["cant_aa"].where(
            por_mes["cant_aa"] > 0)
        sec_act = [_fmt_etiqueta(p, "Precio", unidad) for p in _p]
        sec_aa = [_fmt_etiqueta(p, "Precio", unidad) for p in _p_aa]
    _largo = max((len(t) for t in etq_act + etq_aa if t), default=0)
    _largo_sec = max((len(t) for t in sec_act + sec_aa if t), default=0)
    plan = _plan_etiquetas(len(por_mes), _largo, modo, largo_sec=_largo_sec)
    if plan["sec"]:
        etq_act = [_con_segundo(t, s) for t, s in zip(etq_act, sec_act)]
        etq_aa = [_con_segundo(t, s) for t, s in zip(etq_aa, sec_aa)]
    etq_act = _ralear(etq_act, plan["paso"])
    etq_aa = _ralear(etq_aa, plan["paso"]) if plan["ambas"] else None
    # El precio va SIEMPRE en el hover, haya entrado o no en la etiqueta:
    # es donde queda cuando el segundo renglón cede su sitio (12 meses).
    _hov = "  ·  %{customdata}" if _con_sec else ""
    _cd_act = [s or "" for s in sec_act]
    _cd_aa = [s or "" for s in sec_aa]
    # "Este año" en el color del texto y "Año pasado" apagado: la misma
    # jerarquía que las dos columnas (acento contra gris).
    _fnt_act = dict(size=_ETQ_FUENTE, color=TEXTO_PRINCIPAL)
    _fnt_aa = dict(size=_ETQ_FUENTE, color=GRIS_TEXTO)

    # El mes que está explicando la cascada queda entero y el resto se
    # apaga. Una lista por punto y no una traza aparte: partir la serie en
    # dos trazas rompe el `barmode="group"` (cada traza pide su ranura, así
    # que el mes elegido se corría de su columna) y duplicaría las
    # entradas del hover unificado.
    _op = ([1.0 if e == mes_sel else _OPACIDAD_APAGADA for e in etiquetas]
           if mes_sel in list(etiquetas) else None)

    fig = go.Figure()
    if modo == "Precio":
        # Cada etiqueta va del lado de AFUERA de su línea: la del precio
        # más alto arriba, la del más bajo abajo. Con las dos del mismo
        # lado se pisan justo en los meses donde las líneas se cruzan, que
        # son los que más interesan.
        # Sin la otra serie rotulada no hay lado que ceder: arriba siempre.
        _act_arriba = [not (plan["ambas"] and pd.notna(a) and pd.notna(b)
                            and a < b)
                       for a, b in zip(y_act, y_aa)]
        _pos_act = ["top center" if up else "bottom center"
                    for up in _act_arriba]
        _pos_aa = ["bottom center" if up else "top center"
                   for up in _act_arriba]
        fig.add_scatter(x=etiquetas, y=y_aa, name="Año pasado",
                        mode="lines+text" if etq_aa else "lines",
                        line=dict(color=GRIS_TEXTO, width=2, dash="dot"),
                        text=etq_aa, textposition=_pos_aa, textfont=_fnt_aa,
                        cliponaxis=False,
                        hovertemplate=fmt + "<extra>Año pasado</extra>")
        fig.add_scatter(x=etiquetas, y=y_act, mode="lines+markers+text",
                        name="Este año", line=dict(color=ACENTO, width=2.4),
                        # En líneas el apagado va en el MARCADOR: bajarle la
                        # opacidad al trazo apagaría la curva entera, que es
                        # lo único que esta vista tiene para mostrar.
                        marker=dict(size=6, opacity=_op),
                        text=etq_act, textposition=_pos_act,
                        textfont=_fnt_act, cliponaxis=False,
                        hovertemplate=fmt + "<extra>Este año</extra>")
    else:
        # `constraintext="none"`: sin él Plotly ENCOGE la etiqueta que no
        # entra en vez de avisar (regla #91) — la cuenta de `_plan_etiquetas`
        # ya decidió que entra, así que no hay nada que achicar.
        _kw_etq = dict(textposition="outside", cliponaxis=False,
                       constraintext="none",
                       textangle=-90 if plan["girar"] else 0)
        fig.add_bar(x=etiquetas, y=y_aa, name="Año pasado",
                    marker=dict(color=GRIS_BORDE, opacity=_op),
                    text=etq_aa, textfont=_fnt_aa, **_kw_etq,
                    customdata=_cd_aa,
                    hovertemplate=fmt + _hov + "<extra>Año pasado</extra>")
        fig.add_bar(
            x=etiquetas, y=y_act, name="Este año",
            marker=dict(
                color=ACENTO, opacity=_op,
                # Trama sólo en el mes parcial: Plotly acepta un patrón por
                # punto, así que no hace falta una traza aparte que además
                # rompería la leyenda en dos "Este año".
                pattern=dict(shape=["/" if p else "" for p in es_parcial],
                             fgcolor="#ffffff", size=4, solidity=0.35),
            ),
            text=etq_act, textfont=_fnt_act, **_kw_etq,
            customdata=_cd_act,
            hovertemplate=fmt + _hov + "<extra>Este año</extra>")

    _compras_layout(fig, alto=_ALTO_FIG_VAP)
    # SIN `title`: el ámbito vive en la cabecera de la tarjeta desde el
    # 2026-09-02 (ver el `st.empty()` del drill). Lo que gana la figura no
    # es sólo el alto del texto — Plotly reserva margen superior para el
    # título aunque esté vacío, así que el margen se fija explícito abajo.
    fig.update_layout(
        barmode="group", bargap=_BARGAP_VAP, bargroupgap=0.08,
        hovermode="x unified",
        # La leyenda se fue (ver `_LEYENDA_VAP`): gris = año pasado, acento
        # = este año es la convención de la app, y el hover unificado nombra
        # las dos series al pasar por encima.
        showlegend=False,
    )
    fig.update_xaxes(type="category", tickangle=0)
    # Techo para las etiquetas: `textposition="outside"` no agranda el
    # rango solo, y la de la columna más alta se cortaba contra el borde.
    # Girada ocupa su LARGO hacia arriba; derecha, una línea.
    _vis = [v for v in list(y_act) + list(y_aa) if pd.notna(v)]
    if _vis:
        # Con el segundo renglón, derecha ocupa DOS líneas y girada ocupa
        # lo que el más largo de los dos.
        _largo_vis = max(_largo, _largo_sec) if plan["sec"] else _largo
        _renglones = 2 if plan["sec"] else 1
        _alto_etq = ((_largo_vis * _ETQ_PX_CARACTER) if plan["girar"]
                     else _renglones * _ETQ_ALTO_LINEA) + _ETQ_AIRE
        _rng = _techo_con_etiquetas(max(_vis), min(_vis), _alto_etq,
                                    simetrico=modo == "Precio")
        if _rng:
            fig.update_yaxes(range=_rng)
    return fig


def _unidades_por(fuente, llave, col_um):
    """`{valor de llave: unidad}` — la unidad de medida de cada ítem.

    `mode()` y no el primero: un producto puede tener alguna fila con la
    unidad mal cargada y la moda la ignora. Medido el 2026-09-06 sobre
    `compras.parquet`: 1.588 productos, CERO con más de una
    `UNIDAD_DE_INGRESO`, así que a nivel producto la moda es el único
    valor. La red está por las agrupaciones (Familia/Subfamilia), donde sí
    conviven unidades distintas.
    """
    if not (col_um and llave and col_um in fuente.columns
            and llave in fuente.columns):
        return {}
    return (fuente[[llave, col_um]].astype(str).groupby(llave)[col_um]
            .agg(lambda s: s.mode().iat[0] if not s.mode().empty else "")
            .to_dict())


def _fig_puente(valor, valor_aa, ef_precio, ef_cant,
                cant=None, cant_aa=None, unidad="",
                bordes=_ETQ_BORDES):
    """Puente: año pasado → efecto precio → efecto cantidad → este año.

    `go.Waterfall` ignora `bargap` (CLAUDE.md § Plotly): el grosor se
    controla con `waterfallgap`.
    """
    # Las DOS barras del medio se miden en SOLES, así que su rótulo tiene que
    # nombrar algo que se mida en soles: "Precio" a secas se lee como si la
    # barra FUERA un precio (reportado 2026-09-06, con el tooltip diciendo
    # "Precio: S/ 44,845"). Son "Efecto precio"/"Efecto cantidad", que además
    # es como ya las nombran la tabla de abajo y el popover de ayuda de esta
    # misma tarjeta — el gráfico era el único que le decía distinto al mismo
    # concepto. Ver `arquitectura.md` regla #335.
    def _signo(v):
        return f"{'+' if v >= 0 else '−'}S/ {abs(v):,.0f}"

    # La cantidad sólo se muestra con su unidad al lado. Ver el comentario
    # largo del `hovertext`: "246" a secas, en una tarjeta donde todo lo
    # demás está en soles, se lee como soles.
    _um = str(unidad or "").strip().lower()
    _con_cant = cant is not None and cant_aa is not None and bool(_um)

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "total"],
        x=[bordes[0], "Efecto<br>precio", "Efecto<br>cantidad",
           bordes[1]],
        y=[valor_aa, ef_precio, ef_cant, 0],
        # Con signo las dos del medio (son diferencias: "+" costó más, "−"
        # costó menos) y sin signo las dos de los bordes, que son totales.
        text=[f"S/ {valor_aa:,.0f}", _signo(ef_precio), _signo(ef_cant),
              f"S/ {valor:,.0f}"],
        textposition="outside",
        cliponaxis=False,
        # Es un COSTO: subir es malo. Rojo/verde invertidos respecto de la
        # convención bursátil, igual que el semáforo de Volatilidad.
        increasing=dict(marker=dict(color=ERROR)),
        decreasing=dict(marker=dict(color=EXITO)),
        totals=dict(marker=dict(color=ACENTO)),
        connector=dict(line=dict(color=GRIS_BORDE, width=1)),
        # `%{y}` en un Waterfall NO es el alto de la barra: es el ACUMULADO
        # corrido. Medido el 2026-09-06: la barra rotulada "S/ 2,012" abría
        # un tooltip que decía "S/ 44,845" (= 42,833 + 2,012), o sea el
        # gráfico se contradecía consigo mismo. El texto va armado desde
        # Python en `hovertext` para que diga exactamente lo mismo que la
        # etiqueta, y de paso qué significa cada barra.
        #
        # Y el tooltip nombra el PIVOTE, que es el número que la frase
        # "pagar distinto por lo mismo" escondía: preguntado el 2026-09-06,
        # *"¿a qué dato es «lo mismo»?"*. «Lo mismo» es la cantidad de ESTE
        # año, y lo que vale esa cantidad a precios del año pasado
        # (`valor - ef_precio`) no aparece en ninguna parte de la pantalla,
        # aunque es la bisagra entre los dos efectos:
        #     valor_aa  ──(cantidad)──▶  pivote  ──(precio)──▶  valor
        #
        # Y con el pivote pasó lo mismo DOS veces más, que es de lo que sale
        # la forma final de abajo:
        #
        #   · "lo de este año" es OTRO pronombre (preguntado: *"¿qué es «lo
        #     de este año»?"*). Cambiar un pronombre por otro no arregla
        #     nada.
        #   · y decir sólo el número tampoco: *"los 246 ¿qué? ¿soles?
        #     ¿kilos? ¿documentos?"*. Una cantidad SIN SU UNIDAD, en una
        #     tarjeta donde todo lo demás está en soles, se lee como soles.
        #
        # Así que el tooltip escribe la CUENTA, con la unidad pegada a cada
        # cantidad y el mismo número repetido donde los dos efectos se
        # tocan (el pivote). No queda nada que interpretar: la resta de los
        # dos renglones ES la barra.
        #
        # La rama sin cantidades no es un caso raro, es el caso normal
        # (Familia, o sin foco): ahí no hay UNA unidad —sumar kilos con
        # litros y con servicios es la trampa que evita `_por_item`— y se
        # dice todo en plata, que sí se puede sumar entre unidades. Se cae
        # también si falta la unidad: un número pelado es justo lo que se
        # reportó, así que sin unidad no se muestra cantidad.
        hovertext=[
            f"{_llano(bordes[0])}: S/ {valor_aa:,.0f}",
            f"Efecto precio: {_signo(ef_precio)}<br>"
            "<span style='font-size:11px'>"
            + (f"{cant:,.0f} {_um} × precio de este año = "
               f"S/ {valor:,.0f}<br>"
               f"{cant:,.0f} {_um} × precio del año pasado = "
               f"S/ {valor - ef_precio:,.0f}"
               if _con_cant else
               f"compras de este año, a precio de este año = "
               f"S/ {valor:,.0f}<br>"
               f"compras de este año, a precios del año pasado = "
               f"S/ {valor - ef_precio:,.0f}")
            + "</span>",
            f"Efecto cantidad: {_signo(ef_cant)}<br>"
            "<span style='font-size:11px'>"
            + (f"{cant:,.0f} {_um} × precio del año pasado = "
               f"S/ {valor - ef_precio:,.0f}<br>"
               f"{cant_aa:,.0f} {_um} × precio del año pasado = "
               f"S/ {valor_aa:,.0f}"
               if _con_cant else
               f"compras de este año, a precios del año pasado = "
               f"S/ {valor - ef_precio:,.0f}<br>"
               f"compras del año pasado, a esos mismos precios = "
               f"S/ {valor_aa:,.0f}")
            + "</span>",
            f"{_llano(bordes[1])}: S/ {valor:,.0f}",
        ],
        hovertemplate="%{hovertext}<extra></extra>",
    ))
    fig.update_layout(waterfallgap=0.45)
    # Menos alto que la serie de al lado, y por eso terminan a la misma
    # altura: encima de esta figura va la línea de veredicto —y desde el
    # 2026-09-16 el rótulo que la nombra—, que la empujan hacia abajo
    # (`_ALTO_CASCADA`, las dos franjas medidas en el navegador).
    _compras_layout(fig, alto=_ALTO_CASCADA)
    # `title=""` y NO `title=None`: con None, Plotly.js pinta la cadena
    # literal "undefined" donde iría el título (medido en el navegador,
    # 2026-08-24 — salía sobre el waterfall). El título de esta figura
    # sobra: la línea de resumen de arriba y las etiquetas del propio eje
    # ("Año pasado → Efecto precio → Efecto cantidad → Este año") ya la
    # nombran.
    # `t=16` y no 44 (2026-09-02, reportado: "esto me quita mucho espacio").
    # Medido antes de tocarlo: el área de trazo del waterfall empezaba 36px
    # por debajo del borde de la figura y ocupaba 97 de los 176 de alto —
    # menos de la mitad. Esos 36 eran una banda vacía ENTRE el veredicto y
    # la primera barra, o sea el hueco que se señaló. El margen estaba para
    # las etiquetas `textposition="outside"`, pero con `cliponaxis=False` y
    # el veredicto justo encima, 44px era doble aire.
    fig.update_layout(showlegend=False, title="",
                      margin=dict(l=10, r=10, t=16, b=10))
    fig.update_yaxes(showticklabels=False)
    # `type="category"` NO ES OPCIONAL desde que los bordes dicen el año en
    # número (#448). Sin esto Plotly parsea "2025" y "2026" como NÚMEROS,
    # el eje sale `linear` —con un tick "2,025.5" en el medio— y las dos
    # barras de efectos, cuyas x son texto, no se dibujan: la cascada
    # quedaba en dos barras sueltas. Es la trampa de la #325 vista de
    # nuevo, y esta figura se salvaba sólo porque sus cuatro rótulos eran
    # palabras. Reportado con captura el 2026-09-17.
    fig.update_xaxes(type="category", tickangle=0)
    return fig


def _fig_cascada(pasos, fmt, hover=None):
    """La cascada de un corte que NO es «Por qué»: «Quién», «Cuándo», o las
    tres barras de `_pasos_simple`.

    `_fig_puente` se quedó aparte y no se generalizó a ésta a propósito: su
    `hovertext` escribe la CUENTA de cada efecto con la unidad pegada a
    cada cantidad (seis renglones de reglas ganadas a pulso, ver su
    docstring y la regla #335). Acá cada barra es un Δ y punto — meterlas
    en la misma función obligaba a un `if` por renglón de tooltip para no
    perder ninguna de las dos formas.

    `fmt(valor, medida)` escribe la etiqueta de la barra; lo pasa el
    llamador porque la MAGNITUD cambia con el modo (soles, kilos o S/ por
    kilo) y la cascada no tiene por qué saber en cuál está.
    """
    medidas = [p["medida"] for p in pasos]
    valores = [0.0 if p["medida"] == "total" else p["valor"] for p in pasos]
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=medidas,
        x=[p["label"] for p in pasos],
        y=valores,
        text=[fmt(p["valor"], p["medida"]) for p in pasos],
        textposition="outside",
        cliponaxis=False,
        # Mismo semáforo invertido que `_fig_puente`: es un COSTO, así que
        # subir es rojo. Cambiarlo de una cascada a la otra haría que el
        # mismo gesto —elegir otro corte— diera vuelta los colores sin que
        # el dato se moviera.
        increasing=dict(marker=dict(color=ERROR)),
        decreasing=dict(marker=dict(color=EXITO)),
        totals=dict(marker=dict(color=ACENTO)),
        connector=dict(line=dict(color=GRIS_BORDE, width=1)),
        **({"hovertext": hover, "hovertemplate": "%{hovertext}<extra></extra>"}
           if hover else {}),
    ))
    # `waterfallgap` y no `bargap` (CLAUDE.md § Plotly). Más angosto que el
    # 0.45 de `_fig_puente`: ahí son cuatro barras y acá hasta siete, y con
    # el gap grande se vuelven rayas.
    fig.update_layout(waterfallgap=0.3)
    _compras_layout(fig, alto=_ALTO_CASCADA)
    fig.update_layout(showlegend=False, title="",
                      margin=dict(l=10, r=10, t=16, b=10))
    fig.update_yaxes(showticklabels=False)
    # El eje de esta cascada son NOMBRES, no fechas ni números: sin
    # `type="category"` un rótulo como "2026" se parsea como número y el
    # eje sale `linear` con ticks inventados (la trampa de la regla #325).
    #
    # Y un punto más chico que el resto de la app: es lo que hace entrar el
    # rótulo en la columna (ver `_FUENTE_EJE_CASCADA`, medido).
    fig.update_xaxes(type="category", tickangle=0,
                     tickfont=dict(size=_FUENTE_EJE_CASCADA))
    return fig


# ===========================================================================
# UI
# ===========================================================================

def _causa(delta, ef_precio, ef_cant):
    """"por comprar menos" / "por precio más alto": el efecto que manda,
    CON su dirección. Vacío si no hay diferencia que explicar.

    La dirección siempre coincide con el signo de `delta`: si |a| > |b| y
    a + b = Δ, Δ tiene el signo de a. Así que la frase no puede contradecir
    el color del número de al lado.
    """
    if round(delta) == 0:
        return ""
    if abs(ef_precio) > abs(ef_cant):
        return "por precio más alto" if ef_precio > 0 else "por precio más bajo"
    return "por comprar más" if ef_cant > 0 else "por comprar menos"


def _fmt_soles(v):
    """"S/ 16,660", sin signo. El signo lo pone quien arma la frase."""
    return f"S/ {abs(v):,.0f}"


def _fmt_cant(v, unidad):
    """"592.5 kg", sin signo. Un decimal hasta el millar y ninguno arriba.

    El decimal no es adorno: media docena de productos del parquet se
    compran en fracciones de kilo, y "0 kg" para 0.4 es un dato borrado.
    Pasado el millar la fracción no aporta y el número se hace largo, que
    en una barra de ~41px se paga en rótulos pisados."""
    a = abs(float(v))
    return f"{a:,.{1 if a < 1000 else 0}f} {unidad}".strip()


def _fmt_precio(v, unidad):
    """"S/ 74.68/kg", sin signo. DOS decimales siempre: un precio unitario
    redondeado al sol pierde justo la diferencia que esta vista busca."""
    a = abs(float(v))
    return f"S/ {a:,.2f}/{unidad}" if unidad else f"S/ {a:,.2f}"


def _etq_cascada(valor, medida, fmt):
    """La etiqueta de una barra: con signo las del medio, sin signo los
    bordes. Misma convención que `_fig_puente` — los extremos son TOTALES y
    las del medio, diferencias."""
    if medida == "relative":
        return ("+" if valor >= 0 else "−") + fmt(valor)
    return fmt(valor)


def _hover_cascada(pasos, partes, fmt, delta_total):
    """El tooltip de cada barra, o None si no hay nada que agregar.

    Dice DOS cosas que la etiqueta no puede:

      · el nombre ENTERO del ítem o del mes, que en el eje va cortado a 12
        caracteres (`_etq_barra`);
      · y en la barra del resto, CUÁNTO DEL Δ NO SE NOMBRÓ. Ése es el
        número que decide si mirar por «Quién» sirve: medido el 2026-09-16
        sobre el parquet, los cinco nombrados explican el 58 % del Δ de
        septiembre y el 18 % del de agosto. Sin ese porcentaje la misma
        figura se lee como una acusación en los dos casos.

    Va al hover y no a un `st.caption` porque la tarjeta no tiene 20px que
    darle: la cascada ya quedó en `_ALTO_CASCADA` (163px).
    """
    if not partes:
        return None
    nombres = {_etq_barra(n): n for n, _ in partes}
    hov = []
    for p in pasos:
        etq, val = p["label"], p["valor"]
        if p["medida"] != "relative":
            hov.append(f"{etq.replace('<br>', ' ')}: {fmt(val)}")
            continue
        if etq.startswith("otros") and delta_total:
            hov.append(
                f"El resto: {_etq_cascada(val, 'relative', fmt)}<br>"
                f"<span style='font-size:11px'>lo nombrado explica el "
                f"{abs((delta_total - val) / delta_total) * 100:.0f} % "
                f"de la diferencia</span>")
        else:
            hov.append(f"{nombres.get(etq, etq.replace('<br>', ' '))}: "
                       f"{_etq_cascada(val, 'relative', fmt)}")
    return hov


def _nombre_serie_html(item, auto=False):
    """El nombre del ítem que dibuja la serie, en su propia tarjeta.

    Vacío cuando no hay foco: la serie muestra todas las compras y no hay
    nada que aclarar — un rótulo que dijera «todas» ocuparía el renglón
    para decir que no hay recorte. El hueco igual se reserva, porque el
    renglón lo comparte con los dos controles.

    `auto` marca el ítem que eligió la VISTA y no el usuario (Cantidad y
    Precio sin foco, ver regla #401): sin ese aviso, un producto solo en el
    gráfico se lee como un clic que nadie hizo.
    """
    if not item:
        return ""
    return (
        f'<div style="font:600 13px/1.3 DM Sans,sans-serif;'
        f'color:{TEXTO_PRINCIPAL};white-space:nowrap;overflow:hidden;'
        f'text-overflow:ellipsis">{_compras_truncar(str(item), 38)}'
        + (f'<span style="font:400 11px/1 DM Sans,sans-serif;'
           f'color:{GRIS_TEXTO};margin-left:7px">· mayor gasto</span>'
           if auto else "")
        + '</div>'
    )


def _nombre_cascada_html(ambito):
    """El ítem que explica la cascada: NEGRO y centrado, en su propia línea.

    2026-09-17, a pedido: *«el nombre al que refiere, o sea si es un
    producto o subfamilia o familia, debería estar en color negro, al medio
    de la tarjeta»*. Salió del rótulo —donde iba en gris, pegado con un «·»
    y recortándose contra el selector de corte— y pasó a ser un título.

    Vacío sin foco: ahí la cascada es de todas las compras y un renglón que
    dijera «todas» ocuparía sitio para decir que no hay recorte. Mismo
    criterio que el nombre de la tarjeta de las barras."""
    if not ambito:
        return ""
    return (
        f'<div style="font:600 13.5px/1.25 DM Sans,sans-serif;'
        f'color:{ACENTO_TEXTO};text-align:center;margin:0;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
        f'{_compras_truncar(str(ambito), 46)}</div>'
    )


def _resumen_html(delta, pct, ef_precio, ef_cant, valor, valor_aa,
                  magnitud="", fmt=_fmt_soles, causa=None, solo=None):
    """El veredicto de la cascada, en DOS renglones bajo el nombre del ítem.

        Δ VALORIZADO DE COMPRA  −S/ 16,660      ← `solo="monto"`
        −62.6% vs año pasado · por comprar menos ← `solo="pct"`

    `solo` los separa porque NO se dibujan juntos: el de arriba comparte
    renglón con el selector de corte —así que va dentro de una columna— y
    el de abajo va al ancho entero de la tarjeta. Sin el parámetro habría
    que armar el HTML dos veces con la mitad de los datos cada vez.

    CUATRO VERSIONES EN TRES SEMANAS, y cada una arregló lo que la
    anterior no veía:

      · 2026-09-02, «más minimalista»: de dos renglones a UNO.
      · 2026-09-14, con el inspector encima del sufijo: *«¿no es fácil leer
        de dónde sale?»*. «−62.6% · la cantidad» se leía «la cantidad bajó
        62.6%» cuando ese 62.6% era del GASTO. Cada pedazo pasó a decir qué
        es: «vs año pasado» pegado al %, y la causa con verbo y dirección,
        que no se puede leer como el sujeto del porcentaje. Regla #414.
      · 2026-09-17, con captura: *«no se ve bien»*. El nombre subió, el
        monto se puso AL LADO de su rótulo —etiqueta y número juntos es lo
        que los hace legibles— y el % se fue a su propio renglón.
      · El mismo día: el monto baja de 15px a 13 (*«el valor en letra más
        chica»*). El número grande peleaba con el nombre del ítem por ser
        el título de la tarjeta, y el título es el nombre.

    `pct` en None cuando el año pasado no hubo compras: un "+0.0%" ahí
    diría que no cambió nada, y es un ítem nuevo.

    `fmt` y `causa` existen porque la tarjeta no mide siempre soles: con
    «Ver» en Cantidad mide kilos y en Precio, S/ por kilo. UN VEREDICTO EN
    SOLES ENCIMA DE UNA CASCADA EN KILOS ES UNA CONTRADICCIÓN. `causa=""`
    apaga el sufijo donde no hay un efecto precio que nombrar (#443).
    """
    if causa is None:
        causa = _causa(delta, ef_precio, ef_cant)
    color = ERROR if delta > 0 else (EXITO if delta < 0 else GRIS_TEXTO)
    signo = "+" if delta >= 0 else "−"

    if solo == "pct":
        _vs = (f"{signo}{abs(pct):.1f}% vs año pasado" if pct is not None
               else "vs año pasado")
        return (
            f'<div style="font:400 11.5px/1.3 DM Sans,sans-serif;'
            f'color:{GRIS_TEXTO};margin:0;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis">{_vs}'
            + (f'<span style="margin-left:7px">· {causa}</span>'
               if causa else "")
            + '</div>'
        )

    # El `title` escribe la resta con los dos totales de la cascada: la
    # cuenta entera, para el que quiera verla sin hacerla.
    _cuenta = (f"Este año {fmt(valor)} − año pasado {fmt(valor_aa)}"
               f" = {signo}{fmt(delta)}")
    # `align-items: baseline` y no `center`: dos tamaños de letra centrados
    # por su caja se ven desalineados; lo que el ojo alinea es la línea de
    # base.
    return (
        f'<div title="{_cuenta}" style="display:flex;align-items:baseline;'
        f'gap:7px;margin:0;white-space:nowrap;overflow:hidden">'
        f'<span style="font:500 10.5px/1.3 DM Sans,sans-serif;'
        f'letter-spacing:.06em;text-transform:uppercase;color:{GRIS_TEXTO};'
        f'flex:0 1 auto;overflow:hidden;text-overflow:ellipsis">{magnitud}'
        f'</span>'
        f'<span style="font:600 13px/1.25 DM Sans,sans-serif;color:{color};'
        f'flex:none">{signo}{fmt(delta)}</span></div>'
    )


def _tabla_detalle(g, agrupar_por, col_um_valores, key_grid, rangos=None):
    """Tabla de abajo: una fila por ítem, con el puente abierto.

    Devuelve el ítem clickeado en esta corrida (o None). El orden por defecto
    es |Δ S/| descendente —lo que más movió la aguja arriba de todo—, no
    alfabético: la pregunta de esta tabla es "qué explica la diferencia".

    `rangos` es `(este_año, año_pasado)` ya formateado, para el subtítulo de
    esas dos cabeceras. Llega de afuera y no se calcula de `g` porque acá
    `g` YA pasó por el buscador: si el ítem que quedó no compró en todos los
    meses, la cabecera anunciaría una ventana más corta que la de la cuenta.
    """
    llave = "prod" if agrupar_por == "Producto" else "grupo"
    ag = _por_item(g, llave)
    if ag.empty:
        st.info("Sin ítems comparables en esta ventana.")
        return None
    # Cantidad y precio sólo se muestran cuando la fila ES un producto: la
    # cantidad de una familia suma kilos con litros y con servicios, y el
    # precio que salga de ese denominador no significa nada (ver `_por_item`).
    # En una familia, lo que se puede decir es cuántos productos la componen.
    _es_prod = llave == "prod"

    filas = []
    for _, r in ag.iterrows():
        delta = r["valor"] - r["valor_aa"]
        filas.append({
            "Item": _compras_truncar(str(r["item"]), 42),
            "__item_full": str(r["item"]),
            "Este año": float(r["valor"]),
            "Año pasado": float(r["valor_aa"]),
            "Δ S/": float(delta),
            "Δ %": (float(delta / r["valor_aa"] * 100)
                    if r["valor_aa"] else None),
            "Efecto precio": float(r["ef_precio"]),
            "Efecto cantidad": float(r["ef_cant"]),
            "__cant": float(r["cant"]) if _es_prod else None,
            "__cant_aa": float(r["cant_aa"]) if _es_prod else None,
            "__p": (float(r["valor"] / r["cant"])
                    if _es_prod and r["cant"] else None),
            "__p_aa": (float(r["valor_aa"] / r["cant_aa"])
                       if _es_prod and r["cant_aa"] else None),
            "__um": col_um_valores.get(str(r["item"]), "") if _es_prod else "",
            "__n": int(r["n_items"]),
        })
    tv = pd.DataFrame(filas)
    tv = tv.reindex(tv["Δ S/"].abs().sort_values(ascending=False).index)
    tv = tv.reset_index(drop=True)

    return renderizar_detalle_vs_ano_pasado(
        tv, agrupar_por,
        # ENMARCADA: la tabla crece con los datos (1.578 productos en el
        # parquet real), así que su alto lo pone el marco y lo que no entra
        # scrollea DENTRO del grid.
        #
        # El techo era `MARCO` (553px, una pantalla completa) hasta
        # 2026-08-26, a pedido ("Vs año pasado es muy largo... al igual que
        # Detalle ítem por ítem"): esta tabla va DEBAJO de la fila de
        # gráficos, así que MARCO + esa fila sumaban bien más de una
        # pantalla de scroll para ver la vista completa. Bajó a `APOYO` —
        # el mismo rol que usaban los gráficos de arriba, no un número
        # inventado: la vista queda de DOS bloques de alto parecido en vez
        # de uno chico y uno casi entero.
        #
        # 2026-09-02, SEGUNDA vuelta del mismo pedido ("podemos hacerlos
        # menos altos, o sea reducirlos verticalmente"): los dos bloques
        # bajan juntos de `APOYO` a `COMPACTO`, el rol que nació ese día
        # justamente para esta forma de vista (ver `alturas.py`). Medido
        # antes: la sección entera daba 1.155px en 1366x700, o sea 1,9
        # pantallas. El `extra` pasa de 44 a 47, que es el cromo MEDIDO por
        # resta en el navegador (grid 380 − `.ag-body-viewport` 333, o sea
        # cabecera 45 + 2 de borde) en vez de sumado a ojo — regla #277.
        #
        # `+ _ALTO_SUB_HDR_DETALLE` desde el 2026-09-08: el subtítulo de las
        # cabeceras las hizo más altas y `autoHeaderHeight` las crece SOLO,
        # pero este `extra` es un número escrito a mano que no se entera.
        # Vuelto a medir con el subtítulo puesto: cromo 60 = cabecera 58 + 2
        # de borde, o sea 47 + 13. Regla #361. Y `+ _ALTO_TIT_HDR_DETALLE`
        # desde el 2026-09-12: los títulos a 14px la llevaron a 62 (#392).
        altura=alturas.por_filas(len(tv), px_fila=_ALTO_FILA_DETALLE,
                                 extra=(47 + _ALTO_SUB_HDR_DETALLE
                                        + _ALTO_TIT_HDR_DETALLE),
                                 minimo=200, rol=alturas.COMPACTO),
        key=key_grid,
        rango_act=rangos[0] if rangos else None,
        rango_aa=rangos[1] if rangos else None,
    )


@st.fragment
def _tarjeta_cascada(items, ums_prod, unidad_serie, modo, tot, foco_titulo,
                     mes_sel, ef_p, ef_c, g_casc, g_foco, llave_foco):
    """La tarjeta de la cascada: rótulo, corte, veredicto y el waterfall.

    UN FRAGMENT DENTRO DEL FRAGMENT DEL DRILL, igual que
    `volatilidad.py::_tarjeta_compras_semana` y por la misma queja
    (2026-09-17): *«veo que hace rerun en las tres tarjetas, ¿podemos
    hacer que sólo sea en la que afecta?»*. Las cuatro superficies eran un
    solo `@st.fragment`, así que cambiar «Partir por» —que no le toca nada
    a la serie ni a la tabla— re-corría la sección entera y el velo de
    `data-stale` (#366) cubría las tres.

    Streamlit re-ejecuta esta función con los argumentos de la última
    corrida del drill, que es exactamente lo que hace falta: el corte no
    cambia ni un dato de los que entran por acá.

    Lo que SÍ tiene que refrescar las tres sigue en el drill: la ventana,
    la familia, el agrupador, «Ver», el clic en un mes y el clic en una
    fila. Ver la regla #447.
    """
    # La CANTIDAD sólo viaja si `items` es un producto solo: ahí
    # hay UNA unidad y el número se puede decir ("246 kilos"). Con
    # varios productos sumaría kilos con litros y con servicios —
    # la misma trampa que `_por_item` evita para el precio del
    # grupo. Sin cantidad el tooltip lo dice todo en plata.
    #
    # Y va con su UNIDAD o no va: `_fig_puente` ignora la cantidad
    # si la unidad viene vacía. Un "246" pelado en una tarjeta de
    # soles se lee como soles (reportado el 2026-09-06, regla #335).
    _uno = len(items) == 1
    _um_puente = (ums_prod.get(str(items["item"].iloc[0]), "")
                  if _uno else "")
    _um_corta = unidad_corta(_um_puente) or unidad_serie or ""

    # ── LA MAGNITUD, DE UN SOLO SITIO ────────────────────────────
    # El rótulo, el veredicto y las etiquetas de la cascada tienen
    # que hablar de lo MISMO. Antes daba igual porque siempre eran
    # soles; desde que la tarjeta sigue a «Ver», un veredicto en
    # soles encima de una cascada en kilos es una contradicción
    # escrita en la misma tarjeta. Sale de acá, una vez.
    #
    # EMPIEZA CON Δ (2026-09-17, a pedido: «a veces sale en negativo y ya
    # no es lógico el nombre»). El rótulo nombra la tarjeta pero está
    # pegado arriba del VEREDICTO, que es una resta: «VALORIZADO DE
    # COMPRA: −S/ 16,660» no existe. Con el Δ delante, sí.
    # El símbolo y no la palabra por ancho MEDIDO: «DIFERENCIA DE
    # VALORIZADO DE COMPRA» pide 311px y su columna da 291 a 1280 de
    # viewport — se recortaba el rótulo nuevo el día que nació. Además es
    # el idioma que la tabla de abajo ya usa en «Δ S/» y «Δ %».
    if modo == "Cantidad" and _um_corta:
        _magnitud = f"Δ Cantidad comprada ({_um_corta})"
        _fmt_mag = lambda v: _fmt_cant(v, _um_corta)  # noqa: E731
        _v1, _v0 = float(tot["cant"]), float(tot["cant_aa"])
    elif modo == "Precio" and _um_corta and tot["cant"] and tot["cant_aa"]:
        _magnitud = f"Δ Precio (S/ por {_um_corta})"
        _fmt_mag = lambda v: _fmt_precio(v, _um_corta)  # noqa: E731
        _v1 = float(tot["valor"]) / float(tot["cant"])
        _v0 = float(tot["valor_aa"]) / float(tot["cant_aa"])
    else:
        # También el caso «Cantidad sin unidad»: sin unidad no se
        # escribe una cantidad (regla #335), así que la tarjeta se
        # queda en soles y el rótulo lo dice.
        _magnitud = "Δ Valorizado de compra"
        _fmt_mag = _fmt_soles
        _v1, _v0 = float(tot["valor"]), float(tot["valor_aa"])
    _d_mag = _v1 - _v0
    _pct_mag = (_d_mag / _v0 * 100) if _v0 else None
    # El ÍTEM va solo, en su propia línea negra y centrada; el MES, si lo
    # hay, se le pega — es parte de "sobre qué" y no de "qué se mide".
    # Sin foco no se escribe nada (ver `_nombre_cascada_html`).
    _ambito = foco_titulo or ""
    if mes_sel:
        _ambito = f"{_ambito} · {mes_sel}" if _ambito else mes_sel

    # ── EL CORTE, AL LADO DEL VEREDICTO ──────────────────────────
    # 2026-09-17, segunda mudanza del día: «hagamos que ese corte
    # ahora esté en la tarjeta de las cascadas, ya no en el
    # izquierdo». Tiene razón y es su único consumidor — `corte` se
    # lee en UN sitio, el `if` de acá abajo.
    #
    # VA EN LA FILA DEL VEREDICTO Y NO EN UNA PROPIA, y eso no es
    # estética: una fila propia le costaría a la cascada los 47px
    # de `FRANJA_CTRL_SERIE` sobre 163 — más de la cuarta parte del
    # dibujo, en la figura más chica de la vista. Acá el alto ya
    # existe (el bloque de texto mide 27 y el desplegable 26), así
    # que el control entra en el hueco que había a la derecha y
    # cuesta CERO.
    #
    # Lo que sí cuesta es ANCHO: el veredicto pasa de ~402px de
    # columna a ~286, y con el monto de todas las compras se le
    # recorta la causa con "…". Es el mismo `ellipsis` que ya
    # gobierna este texto en pantallas angostas (regla #414) — se
    # VE recortado, no se parte el renglón ni se sale de la
    # tarjeta.
    #
    # VA EN LA LÍNEA DEL RÓTULO Y NO EN LA DEL VEREDICTO, y esto
    # se midió las dos veces. Con el control al lado del veredicto
    # la columna del texto caía a 287px y el veredicto pide 350:
    # se recortaba en «−S/ 16,660 −62.6% vs año pasado · por co…»,
    # o sea que el pedazo que se comía era LA CAUSA — el único que
    # explica algo. El rótulo, en cambio, mide 10,5px, es
    # secundario, y su ámbito ya lo dice la tarjeta de al lado en
    # 13px negrita: ahí el recorte no cuesta nada.
    #
    # RENGLÓN 1: el nombre, a todo el ancho y centrado EN LA TARJETA
    # (2026-09-17: «el nombre debe estar más arriba y al medio de la
    # tarjeta»). Compartía fila con el selector, así que se centraba
    # dentro de SU columna —287 de 402— y quedaba corrido a la izquierda.
    # Ahora el selector baja al renglón del monto, que es texto chico y se
    # banca perder ancho.
    st.markdown(_nombre_cascada_html(_ambito), unsafe_allow_html=True)

    # columnas-internas: el corte al lado del MONTO, para que no le saque
    # alto a la cascada ni ancho al nombre.
    _c_rot, _c_corte = st.columns(_COLS_PUENTE, gap="small",
                                  vertical_alignment="center")

    # `_un_item` mira el foco YA resuelto —a diferencia de cuando el
    # control vivía en la cabecera, donde había que adivinarlo de
    # `session_state`—, así que acá los cortes que se ofrecen son
    # exactos: éste es el sitio donde el estado ya está completo.
    _ops_corte, _fuera_corte = _cortes_disponibles(
        modo, foco_titulo is not None, mes_sel is not None,
        unidad=_um_corta)
    corte = None
    if _ops_corte:
        # ESPEJO, y no la key del widget a secas: en Precio no
        # aplica ningún corte y el selector NO SE DIBUJA — y un
        # widget que deja de renderizarse pierde su estado
        # (CLAUDE.md). Sin el espejo, pasar por Precio y volver
        # tiraba el corte elegido. Misma forma que el
        # `{k_rango}__eco` de `app.py`.
        _pref = st.session_state.get(_K_CORTE, _CORTE_DEFAULT)
        if st.session_state.get("compras_vap_corte_sel") \
                not in _ops_corte:
            st.session_state["compras_vap_corte_sel"] = (
                _pref if _pref in _ops_corte else _ops_corte[0])
        with _c_corte, st.container(key="vap_puente_corte"):
            corte = st.selectbox(
                "Partir por", list(_ops_corte),
                key="compras_vap_corte_sel",
                label_visibility="collapsed",
                help=_ayuda_corte(_fuera_corte))
        st.session_state[_K_CORTE] = corte

    # RENGLÓN 2 (izquierda): el rótulo con su monto al lado. Sin efecto
    # precio que nombrar no se inventa una causa: en kilos el Δ ES la
    # cantidad, y un precio no se parte.
    _causa_mag = None if _fmt_mag is _fmt_soles else ""
    _c_rot.markdown(
        _resumen_html(_d_mag, _pct_mag, ef_p, ef_c, _v1, _v0,
                      magnitud=_magnitud, fmt=_fmt_mag, causa=_causa_mag,
                      solo="monto"),
        unsafe_allow_html=True)

    # RENGLÓN 3: el %, a todo el ancho. Los tres renglones son bloques
    # distintos —el del medio vive en una columna— así que el aire entre
    # ellos NO se arregla con márgenes uno por uno, sino con el `gap` de la
    # tarjeta entera (`estilos/_80_cards.py`, `compras_vap_card_puente`).
    st.markdown(
        _resumen_html(_d_mag, _pct_mag, ef_p, ef_c, _v1, _v0,
                      fmt=_fmt_mag, causa=_causa_mag, solo="pct"),
        unsafe_allow_html=True)

    # Los bordes de la cascada dicen el AÑO en número (2026-09-17, a
    # pedido). Sale de `g_casc` —los meses que la cascada explica, ya
    # recortados por el mes elegido— y no de la fecha de hoy: «este año» es
    # la ventana de la tarjeta, que puede ir a caballo de dos calendarios.
    _bordes = _etq_anios(g_casc["mes"].unique() if not g_casc.empty else [])

    # ── QUÉ CASCADA SE DIBUJA ────────────────────────────────────
    # «Por qué» sigue siendo `_fig_puente` y no un caso de
    # `_fig_cascada`: es la única que tiene algo que explicar
    # además del número (su `hovertext` escribe la cuenta de los
    # dos efectos, regla #335). Las otras dos son la misma figura
    # con otros pasos.
    if corte == _CORTE_DEFAULT and _fmt_mag is _fmt_soles:
        _fig_p = _fig_puente(
            tot["valor"], tot["valor_aa"], ef_p, ef_c,
            cant=float(items["cant"].iloc[0]) if _uno else None,
            cant_aa=float(items["cant_aa"].iloc[0]) if _uno else None,
            unidad=_um_puente, bordes=_bordes)
    else:
        _partes = None
        if corte == "Quién":
            _por = _por_item(g_casc, llave_foco)
            _partes = [(str(r.item), float(r.valor - r.valor_aa))
                       for r in _por.itertuples()]
            _pasos = _pasos_cascada(_partes, _v0, _v1, resto="otros",
                                    bordes=_bordes)
        elif corte == "Cuándo":
            _pm = (g_foco.groupby("mes", as_index=False)
                   [["valor", "cant", "valor_aa", "cant_aa"]].sum()
                   .sort_values("mes"))
            _col = "cant" if _fmt_mag is not _fmt_soles else "valor"
            _partes = [(_etiqueta_mes(r.mes),
                        float(getattr(r, _col)
                              - getattr(r, f"{_col}_aa")))
                       for r in _pm.itertuples()]
            _pasos = _pasos_cascada(_partes, _v0, _v1, cronologico=True,
                                    resto="otros", bordes=_bordes)
        else:
            _pasos = _pasos_simple(_v0, _v1, bordes=_bordes)
        _fig_p = _fig_cascada(
            _pasos, lambda v, med: _etq_cascada(v, med, _fmt_mag),
            hover=_hover_cascada(_pasos, _partes, _fmt_mag,
                                 _v1 - _v0))
    st.plotly_chart(_fig_p, use_container_width=True,
                    key="compras_g_vap_puente")


@st.fragment
def _compras_vs_ano_pasado_drill(d, col_prod, col_cant, col_fecha, col_valor,
                                 col_fam=None, col_subfam=None, col_um=None,
                                 d_full=None):
    """Serie mensual + puente precio/cantidad + tabla de detalle.

    Esta firma perdió dos columnas que la versión anterior sí recibía, y no
    por prolijidad: `col_punit` (`PRECIO_UNIT`) y `col_val_aa`
    (`VALOR_ANO_ANTERIOR`) ya no las lee nadie acá. El precio sale ponderado
    (valor/cantidad, para que el puente cierre) y el año pasado del propio
    histórico desplazado 12 meses. Dejarlas puestas "por si acaso" es lo que
    la regla #53 del proyecto llama un símbolo sin consumidor: nada avisa de
    que están muertas, y la próxima lectura del módulo asume que se usan.
    Ver las decisiones 2 y 3 del docstring del módulo.
    """
    if not (col_prod and col_fecha and col_valor and col_cant):
        st.info("Faltan columnas (Producto, Fecha, Valor o Cantidad) "
                "para este gráfico.")
        return

    st.markdown(_CSS, unsafe_allow_html=True)

    # ── EL CLIC EN UN MES SE RESUELVE ANTES DE DIBUJAR NADA ──────────────
    # 2026-09-16: la serie de la izquierda pasa a ser clickeable y acota la
    # cascada de al lado a ESE mes. Es el gesto que faltaba para que el
    # puente dejara de ser una tarjeta quieta — reportado como *«no es muy
    # interesante que toda la vista tenga una tarjeta siempre fija»*.
    #
    # ACÁ ARRIBA Y NO DONDE SE DIBUJA EL GRÁFICO, por dos razones que se
    # suman:
    #
    #   · La selección de `st.plotly_chart(on_select=...)` PERSISTE entre
    #     reruns. Con key estática, cada rerun re-lee el mismo clic y lo
    #     togglea para siempre (parpadeo). La cura es la receta de
    #     CLAUDE.md: leer el clic de `session_state[key]` ANTES de dibujar
    #     y dibujar con una key NUEVA después de cada uno, con un CONTADOR
    #     (`_K_NCLIC`) — así el gráfico nace sin selección y un clic sobre
    #     el mes que ya estaba elegido también se atiende. Reglas #76 y
    #     #399.
    #   · El mes elegido decide qué CORTES ofrece la cabecera («Cuándo» se
    #     cae con un solo mes), y la cabecera se dibuja ~120 líneas más
    #     arriba que la serie. Resolverlo donde está el gráfico dejaba al
    #     selector hablando del rerun anterior — el mismo defecto que ya
    #     costó una mudanza con `agrupar_por` (ver su comentario más
    #     abajo).
    #
    # Se guarda la ETIQUETA del mes ("ago 26") y no su posición: la ventana
    # de la tarjeta cambia con un desplegable, y una posición apunta a otro
    # mes en cuanto la ventana se mueve. Es la misma lección que la #399 le
    # dejó al foco de Volatilidad. Si la etiqueta ya no está en la ventana,
    # el foco se cae solo más abajo, como el del ítem.
    _nclic = st.session_state.get(_K_NCLIC, 0)
    _pt = _first_point(st.session_state.get(f"{_KEY_SERIE}_{_nclic}"))
    if _pt is not None and _pt.get("x") is not None:
        _m_clic = str(_pt["x"])
        st.session_state[_K_MES] = (
            None if st.session_state.get(_K_MES) == _m_clic else _m_clic)
        _nclic += 1
        st.session_state[_K_NCLIC] = _nclic
    _key_serie = f"{_KEY_SERIE}_{_nclic}"

    # 2026-09-02, a pedido: el ámbito ("Todas las compras · últimos 3 meses",
    # o el nombre del ítem en foco) DEJA de ser el `title` de la figura y
    # sube a la fila del título de la tarjeta, al lado de "Vs año pasado".
    #
    # Va por un HUECO (`st.empty()`) y no por el parámetro `titulo` de
    # `_card`: la cabecera se dibuja arriba de todo, pero el ámbito recién
    # se sabe ~100 líneas más abajo (depende del foco, de la ventana y de
    # los datos que sobrevivan a las dos). El hueco reserva el sitio en el
    # orden del DOM y se rellena cuando el dato existe. Se escribe DOS
    # veces a propósito: la primera, sólo "Vs año pasado", para que los
    # `return` tempranos de más abajo —sin meses comparables, sin datos—
    # no dejen la tarjeta sin cabecera.
    #
    # CUATRO TARJETAS Y NO UNA (2026-09-14, a pedido: «separar en tarjetas
    # la vista Vs año pasado, así como está separada Volatilidad; no me
    # refiero al orden, sino solo a ponerlo en tarjetas»). El orden es el de
    # siempre —cabecera, serie | puente, tabla— y cada bloque va en su
    # superficie: `compras_vap_card_hdr`, `_serie`, `_puente` y `_tabla`,
    # con el look de las de Producto y Volatilidad (`estilos/_80_cards.py`).
    # Hasta ese día era `_card("compras_vap")`, una sola.
    #
    # La cabecera va SOLA en la suya, y no por gusto: sus siete controles
    # ocupan ~720px medidos (ver `_80_cards.py`), más de lo que mide la
    # tarjeta de la serie, y mandan sobre las TRES de abajo —ventana y
    # familia recortan todo, el agrupador decide las filas de la tabla y
    # qué enfoca la serie—, así que no pertenece a ninguna. Los avisos de
    # «no hay datos» van en ella: salen al lado del control que los arregla.
    #
    # Sin re-indentar, como Volatilidad (#415): la cabecera cuelga de
    # `_tarj_hdr.container(...)`, las dos del medio de `with col_x,
    # st.container(...)` y la tabla de `_tarj_tabla`. Regla #420.
    with st.container(key="compras_vap_cuerpo"):
        _tarj_hdr = st.container(key="compras_vap_card_hdr")
        with _tarj_hdr.container(key="vap_fila_hdr"):
            _hdr = st.empty()
            # EL TÍTULO YA NO LLEVA EL ÁMBITO (2026-09-17). Nombra la
            # VISTA; el ítem en foco lo dice cada tarjeta por su cuenta —
            # la serie en su fila de controles y la cascada en su rótulo
            # (#443)—, que es adónde mira el que lo necesita. Sigue yendo
            # por un `st.empty()` y no por el parámetro `titulo` de la
            # tarjeta porque los tres `return` tempranos de más abajo
            # escriben avisos en este mismo contenedor.
            _hdr.markdown(f'<p class="chart-card-hdr vap-hdr">{_TITULO}</p>',
                          unsafe_allow_html=True)

            # ═══ LA FILA VA DE LO GLOBAL A LO LOCAL, EN TRES TRAMOS ═══
            # 2026-09-17, a pedido: «creo tener muchos filtros en una sola
            # franja y quizás no todos afecten a las 3 tarjetas».
            #
            # Y era cierto: de los siete controles, sólo DOS mandan sobre
            # las tres tarjetas de abajo. El orden que había —Ver, Partir
            # por, ventana, Familia, agrupador, buscador— iba 2 → 1 → 3 →
            # 3 → 1 → 1, o sea ninguno. Ahora se lee de afuera hacia
            # adentro, y el orden ES la jerarquía:
            #
            #   QUÉ ENTRA       ventana, Familia    → las tres tarjetas
            #   QUÉ SE COMPARA  Ver, Partir por     → la serie y la cascada
            #   EL DETALLE      agrupador, buscador → la tabla
            #
            # EL ORDEN DE ESTOS BLOQUES ES EL ORDEN EN PANTALLA, igual que
            # `_SECCIONES` en `estilos/`: la fila es un flex y Streamlit
            # los apila en el orden en que se crean. Mover uno de tramo es
            # moverlo acá, no en el CSS — allá sólo viven el ancho de cada
            # uno, el rótulo del tramo y la línea que los separa (los dos
            # últimos son pseudo-elementos, así que no ocupan un ítem del
            # flex ni pueden desordenarlo). Ver la regla #444.
            #
            # Los rótulos son TRES y no seis, uno por control: el texto
            # más largo del filtro de Familia («BEBIDAS CON ALCOHOL») ya
            # pide 190px, y «Familia: BEBIDAS CON ALCOHOL» pediría ~245 en
            # una fila que suma 784 de controles sobre 1113. Un rótulo por
            # tramo cuesta un renglón de 13px en ESTA tarjeta, que es la
            # de la cabecera y no la de ninguna figura.

            # ── TRAMO 1: QUÉ ENTRA (manda sobre las tres tarjetas) ───────
            with st.container(key="vap_hdr_ventana"):
                # Default "3m" desde el 2026-09-13, a pedido («debe mostrar
                # inicialmente 3 meses»); antes "12m", y antes del
                # 2026-09-07 "Todo". Ver la decisión 1 del docstring del
                # módulo. Es el DEFAULT, no una ventana fija: las otras
                # cuatro opciones siguen ahí (memoria «fijo en X»).
                #
                # `format_func`: el texto largo con el ícono de calendario.
                # Es el ÚNICO control de la fila que nombra un período, y
                # con "12m" suelto no se distinguía de los otros cinco
                # desplegables — reportado el 2026-09-07 ("¿quizás es mejor
                # tener el selector de fecha?", sobre un selector de fecha
                # que ya estaba ahí). Los rótulos de tramo del 2026-09-17
                # ayudan pero no lo reemplazan: «Qué entra» dice de qué
                # MANDA el tramo, no que éste sea el del calendario.
                # Cambia el TEXTO, nunca el valor: las comparaciones
                # `ventana == periodo.HEREDA` de más abajo siguen viendo la
                # cadena literal (ver el docstring de `periodo.selector`).
                ventana = periodo.selector("compras_vap_periodo",
                                           default="3m", widget="lista",
                                           format_func=_etiq_ventana)

            # ── Familia: filtro PROPIO de la tarjeta ─────────────────────
            # 2026-09-05, a pedido. No le disputa nada a los chips de la
            # franja: se aplica ENCIMA de ellos y sus opciones salen de lo
            # que los chips dejaron pasar, así que acá no se puede elegir
            # una familia que arriba está filtrada — la lista no la ofrece,
            # y no hay forma de que los dos controles se contradigan.
            #
            # UNA OPCIÓN "Todas" Y NO UN CAMPO VACÍO (`index=None` +
            # `placeholder=`), aunque el vacío sea el idioma del buscador
            # de al lado. Son 18px MEDIDOS: con un valor elegido Streamlit
            # agrega una ✕ para soltarlo y el cromo del campo salta de 34
            # a 52, así que "BEBIDAS CON ALCOHOL" —el nombre más largo del
            # parquet— necesitaría 200px de fila para leerse entero en vez
            # de 182, y esa fila ya está llena. Con "Todas" el campo dice
            # siempre qué está haciendo, igual que los otros tres
            # selectores de la fila, y volver a todas es un clic.
            fam_vap = None
            _src_fam = d_full if d_full is not None else d
            if (col_fam and _src_fam is not None
                    and col_fam in _src_fam.columns):
                _ops_fam = [_FAM_TODAS] + sorted(
                    _src_fam[col_fam].dropna().astype(str).unique())
                # Misma defensa que el agrupador de acá abajo: un valor
                # guardado de otra sesión que ya no está en `options`
                # revienta Streamlit. Vuelve a "Todas" y no a otra
                # familia — el default de este control es no filtrar.
                if st.session_state.get("compras_vap_familia") not in _ops_fam:
                    st.session_state["compras_vap_familia"] = _FAM_TODAS
                with st.container(key="vap_hdr_familia"):
                    _fam_sel = st.selectbox(
                        "Familia", _ops_fam, key="compras_vap_familia",
                        label_visibility="collapsed",
                        help="Acota ESTA tarjeta a una familia, encima de "
                             "los chips de la franja. La lista ofrece sólo "
                             "las que los chips dejan pasar.")
                    fam_vap = None if _fam_sel == _FAM_TODAS else _fam_sel


            # ── TRAMO 3: EL DETALLE (la tabla) ───────────────────────────
            # Agrupador y buscador subieron a la fila del título el
            # 2026-09-02, a pedido. Vivían en la tarjeta de abajo, que era
            # la de la tabla; al fusionarse las dos esa tarjeta ya no tiene
            # cabecera propia donde apoyarse.
            #
            # SON LOS DOS MÁS LOCALES DE LA FILA, y por eso van últimos
            # desde el 2026-09-17: el buscador toca SÓLO las filas de la
            # tabla, y el agrupador las decide (a las otras dos tarjetas
            # las alcanza de rebote, por lo que significa un clic y por lo
            # que nombra la cascada en el corte «Quién»).
            #
            # Dibujarlos en la cabecera es de paso un arreglo: `agrupar_por`
            # se lee de `session_state` ~150 líneas más abajo para resolver
            # el foco, y mientras el widget se dibujaba DESPUÉS ese valor
            # era el del rerun anterior. Ahora los dos hablan del mismo run
            # — y el reordenamiento no lo rompe, porque «abajo» sigue
            # estando abajo.
            _ops_ag = [a for a in _AGRUPADORES
                       if a == "Producto"
                       or (a == "Familia" and col_fam)
                       or (a == "Subfamilia" and col_subfam)]
            # Si el reporte viene sin Familia/Subfamilia, un valor guardado de
            # otra sesión ya no está en `options` y Streamlit revienta.
            if st.session_state.get("compras_vap_agrupar") not in _ops_ag:
                st.session_state["compras_vap_agrupar"] = _ops_ag[0]
            with st.container(key="vap_hdr_agrupar"):
                agrupar_nuevo = st.selectbox(
                    "Agrupar por", _ops_ag, key="compras_vap_agrupar",
                    label_visibility="collapsed",
                    help="Proveedor no está: el año pasado se compara por "
                         "producto y mes, así que repartirlo entre proveedores "
                         "le atribuiría a uno lo que compró otro.")
            with st.container(key="vap_hdr_buscar"):
                q = st.text_input("Buscar", key="compras_vap_q",
                                  placeholder="Buscar ítem…",
                                  label_visibility="collapsed").strip().lower()
            # ── Cómo se lee la vista: un ícono, no dos captions ──────────
            # 2026-09-02, a pedido ("aprovechar el espacio"). Acá había DOS
            # `st.caption` EN FLUJO —uno bajo los gráficos y otro bajo la
            # tabla— que sumaban ~90px de la sección para explicar algo que
            # se lee UNA vez y después estorba. Pasan a un popover de sólo
            # ícono, el mismo patrón que la ayuda del Ranking de Proveedores
            # (label = shortcode de material, sin texto).
            #
            # La línea del MES PARCIAL va por un hueco: depende de
            # `parcial`, que se calcula ~40 líneas más abajo. Mismo
            # mecanismo que el ámbito del título, y por el mismo motivo.
            with st.container(key="vap_hdr_ayuda"):
                with st.popover(":material/info:",
                                use_container_width=False):
                    with st.container(key="vap_ayuda_panel"):
                        st.markdown(
                            "**Δ** = este año − el mismo período del año "
                            "pasado." + PARR
                            # "pagar distinto por lo mismo" escondía CUÁL es
                            # lo mismo (preguntado el 2026-09-06). Es la
                            # cantidad de ESTE año: se la valoriza a los dos
                            # precios y la resta es el efecto precio. Ver
                            # regla #335.
                            + "**Efecto precio**: las CANTIDADES que "
                            "compraste este año, valorizadas al precio de "
                            "este año y al del pasado — la resta. **Efecto "
                            "cantidad**: esas cantidades contra las del año "
                            "pasado, las dos a precios del año pasado. Los "
                            "dos suman el Δ exacto." + PARR
                            + "**Clic en una fila** de la tabla enfoca el "
                            "gráfico de arriba; volver a clickearla lo "
                            "devuelve a todas las compras." + PARR
                            + "**Clic en un mes** de la serie hace que la "
                            "cascada explique SÓLO ese mes; los demás se "
                            "apagan y otro clic lo suelta. La serie y la "
                            "tabla no se recortan: el mes es una pregunta, "
                            "no un zoom." + PARR
                            + "**Partir por** elige con qué eje se abre esa "
                            "diferencia: por efecto precio/cantidad, por "
                            "ítem o por mes. Sólo ofrece los que aplican — "
                            "los que no, y por qué, están en su ayuda.")
                        _ayuda_parcial = st.empty()

            # (ACÁ VIVÍA EL ⛶ DEL MODO "SOLO", hasta el 2026-09-17. Se
            # quitó a pedido, en la misma vuelta que le dio jerarquía a
            # esta fila: era el octavo ítem de un renglón que ya tenía
            # siete, y devolverlo suma 36px —26 del botón y 10 del gap—
            # justo cuando el título creció de "Vs año pasado" a "Compra
            # Vs Año Pasado".
            #
            # EL MECANISMO SIGUE ENTERO y no es código muerto por
            # descuido: `compras_pila_solo` lo lee el bucle de
            # `graficos/compras/__init__.py` y de él cuelgan las reglas de
            # `estilos/_20_compras_rail.py` que sueltan `--rail-der-res`.
            # Lo que falta es QUIEN LO ENCIENDA. Se conserva porque sus
            # comentarios guardan mediciones hechas contra Cloud que no se
            # recuperan borrándolas y volviéndolas a hacer; para
            # reactivarlo alcanza con un `st.button` que escriba esa clave
            # con la key de la sección y haga `st.rerun(scope="app")`.
            #
            # Lo que se pierde: esta vista parte la fila con
            # `COLUMNAS_DRILL`, así que en una laptop angosta la tarjeta
            # del puente cae a ~290px y el ⛶ era la única salida para
            # darle ancho. Ver la regla #444.
        # (Acá vivía el renglón `st.columns([1, 1])` con la métrica y la
        # ventana, uno pegado a cada borde. Los dos subieron a la fila del
        # título el 2026-09-02 y el renglón se fue con ellos: son los ~56px
        # —fila más gap— que suben los gráficos.)

        # `d_full` es el histórico SIN el filtro de fecha de la franja (los
        # chips Familia/Subfamilia sí vienen aplicados). Con la opción
        # El CÁLCULO sale SIEMPRE del histórico, en las cinco opciones —
        # incluida HEREDA. Ésa es la trampa que se midió acá el 2026-08-24:
        # el año pasado se saca desplazando la propia serie 12 meses, así
        # que calcularlo sobre `d` (lo que dejó pasar la franja) deja al
        # desplazamiento sin fuente. Con la franja en su default —el mes
        # corriente— "Rango" daba un solo mes, el piso caía 12 meses más
        # adelante que el techo y la vista salía vacía SIEMPRE. La ventana
        # elige qué meses se MUESTRAN, no de dónde salen los números.
        fuente = d_full if d_full is not None else d
        # El filtro de Familia de la cabecera se aplica ACÁ, sobre el
        # histórico y ANTES de que se calcule nada: el año pasado sale de
        # la PROPIA serie desplazada 12 meses (decisión 2 del docstring),
        # así que recortar después dejaría al desplazamiento comparando
        # contra meses de otras familias.
        #
        # `d` NO se filtra, a propósito: lo único que se le lee es qué
        # meses TOCA el rango de la franja (la opción "Rango" de más
        # abajo), y esa ventana es la misma se mire la familia que se
        # mire. Filtrarlo la haría encogerse hasta desaparecer cuando la
        # familia elegida no compró nada en el rango — y ahí el `if` de
        # abajo la ignora y la vista mostraría el histórico entero sin
        # decir por qué.
        if fam_vap and col_fam and col_fam in fuente.columns:
            fuente = fuente[fuente[col_fam].astype(str) == fam_vap]
        if fuente is None or fuente.empty:
            _tarj_hdr.info("No hay datos para los filtros seleccionados.")
            return

        parcial = _mes_parcial(fuente[col_fecha])
        # Dos agregados: el real (nunca recortado) y el que alimenta al año
        # pasado (con el mes espejo recortado al mismo día). Ver decisión 3.
        g_act = _mensual(fuente, col_prod, col_fecha, col_valor, col_cant,
                         col_grupo=None)
        g_src = g_act if parcial is None else _mensual(
            fuente, col_prod, col_fecha, col_valor, col_cant,
            recorte=(parcial[0] - 12, parcial[1]))
        g = _con_ano_pasado(g_act, g_src)
        if g.empty:
            _tarj_hdr.info("El histórico no llega a un año completo todavía: "
                    "no hay mes con el mismo mes del año anterior para "
                    "comparar.")
            return

        # El recorte va DESPUÉS de calcular el año pasado: recortar antes
        # dejaría sin fuente a los primeros 12 meses de la ventana.
        if ventana == periodo.HEREDA:
            # "Rango" = los meses que TOCA el rango de la franja, cada uno
            # completo. El mes es la unidad de comparación (el año pasado se
            # mide mes contra mes), así que media docena de días sueltos no
            # se puede comparar contra "el mismo mes del año pasado" sin
            # recortar los dos lados — y eso ya se hace, pero sólo para el
            # último mes, que es el único donde el recorte es inevitable.
            _fe_d = pd.to_datetime(d[col_fecha], errors="coerce").dropna()
            if not _fe_d.empty:
                g = g[(g["mes"] >= _fe_d.min().to_period("M"))
                      & (g["mes"] <= _fe_d.max().to_period("M"))]
        else:
            # El ancla es el ÚLTIMO día del último mes, no el primero: con el
            # primero, `periodo.ventana` devuelve un inicio que cae dentro del
            # mes 12 hacia atrás y "12m" termina mostrando 13 barras.
            v = periodo.ventana(ventana,
                                g["mes"].max().to_timestamp(how="end"),
                                minimo=g["mes"].min().to_timestamp())
            if v is not None:
                ini, fin = v
                g = g[(g["mes"] >= ini.to_period("M"))
                      & (g["mes"] <= fin.to_period("M"))]
        if g.empty:
            _tarj_hdr.info("Sin meses comparables en esta ventana. El histórico "
                    "arranca un año antes del primer mes que se puede "
                    "comparar.")
            return

        # ── El agrupador manda sobre la columna que se agrega ────────────
        # `_mensual` deja `grupo` = el propio producto; cuando el agrupador
        # es Familia o Subfamilia hay que remapearlo.
        #
        # ESTE BLOQUE VIVÍA 80 LÍNEAS MÁS ABAJO, junto a la tabla, y ahí
        # estaba el bug (2026-09-02, reportado: "cuando elijo Familia o
        # Subfamilia no permite seleccionar en la tabla de abajo"). El clic
        # SÍ se guardaba, pero en el rerun siguiente el foco se resolvía
        # ACÁ —contra un `grupo` que todavía era el nombre del PRODUCTO—,
        # el filtro daba vacío y la línea de abajo lo tiraba a la basura
        # como si el agrupador hubiera cambiado. Resultado: la fila se
        # clickeaba y no pasaba nada, siempre, con esos dos agrupadores.
        #
        # El guard de "cambió el agrupador" es legítimo y se queda —al
        # pasar de Familia a Producto el foco viejo no existe en la columna
        # nueva—, pero estaba TAPANDO esto: un guard que se dispara siempre
        # no es una red, es el camino normal.
        agrupar_por = st.session_state.get("compras_vap_agrupar", "Producto")
        if agrupar_por != "Producto":
            _cg = col_fam if agrupar_por == "Familia" else col_subfam
            _mapa = (fuente[[col_prod, _cg]].astype(str)
                     .drop_duplicates(col_prod)
                     .set_index(col_prod)[_cg])
            g = g.copy()
            g["grupo"] = g["prod"].map(_mapa).fillna(g["prod"])

        # ═══ LA FILA DE TARJETAS SE ABRE ACÁ, NO DONDE SE DIBUJA ═══
        # 2026-09-17, a pedido: «coloquemos los widget de valor y cuándo en
        # la tarjeta de las barras». Los dos controles de «Qué se compara»
        # bajaron de la cabecera compartida a la tarjeta de la serie, que
        # es la que gobiernan (con su vecina: «Partir por» dibuja la
        # cascada de al lado — las dos tarjetas son UNA unidad de lectura,
        # como el ranking y su detalle en Proveedor).
        #
        # Y POR ESO LAS COLUMNAS SE CREAN ACÁ ARRIBA. En Streamlit el orden
        # de EJECUCIÓN es el orden en que se leen los widgets: `modo` hace
        # falta ~80 líneas más abajo (el auto-foco, la magnitud, la
        # figura), así que su `selectbox` tiene que correr ANTES. Como el
        # widget ahora vive dentro de la tarjeta de la serie, la tarjeta
        # tiene que existir ANTES. Leerlo de `session_state` y dibujarlo
        # después NO sirve: es exactamente el bug que ya se pagó con
        # `agrupar_por` —el valor que llega es el del rerun anterior— y
        # está documentado veinte líneas más arriba.
        #
        # Que las columnas se creen acá no cambia el DOM: los tres `return`
        # tempranos de más arriba escriben en `_tarj_hdr`, no en el punto
        # de ejecución, así que ninguno puede dejar estas tarjetas a medio
        # dibujar. Después de este punto ya no hay returns hasta que las
        # dos están llenas.
        col_g, col_p = st.columns(COLUMNAS_DRILL, gap=GAP_DRILL)
        _tarj_serie = col_g.container(key="compras_vap_card_serie")
        _tarj_puente = col_p.container(key="compras_vap_card_puente")

        with _tarj_serie.container(key="vap_serie_hdr"):
            # El nombre del ítem va por un HUECO: depende del foco, que se
            # resuelve abajo. Mismo mecanismo que el ámbito del título
            # cuando vivía en la cabecera, y por el mismo motivo.
            _nom_serie = st.empty()

            # `st.pills` -> `st.selectbox` (2026-09-02): tres pastillas de
            # texto ocupaban el ancho de media tarjeta para una elección
            # que casi nunca se toca.
            with st.container(key="vap_serie_modo"):
                modo = st.selectbox(
                    "Ver", list(_MODOS), key="compras_vap_modo_sel",
                    label_visibility="collapsed",
                    help="Qué se compara contra el año pasado. Cantidad y "
                         "Precio se leen sobre UN producto —kilos y litros "
                         "no se suman—: sin uno elegido en la tabla, el de "
                         "mayor gasto.") or "Valor"
            # («Partir por» estuvo acá unas horas el 2026-09-17 y se mudó a
            # la tarjeta de la cascada el mismo día, preguntado: «el por
            # qué, quién y cuándo entiendo que afecta solo al gráfico
            # derecho, ¿verdad?». Sí — es su único consumidor, así que
            # vive donde dibuja. Ver la regla #446.)

        # ── Foco: el ítem clickeado en la tabla de abajo ─────────────────
        foco = st.session_state.get("compras_vap_foco")
        llave_foco = "prod" if agrupar_por == "Producto" else "grupo"
        g_foco = g if foco is None else g[g[llave_foco].astype(str) == foco]
        # El foco se cae solo cuando el ítem que nombra ya no está en `g`:
        # cambió el agrupador (un producto no existe en la columna Familia)
        # o cambió el filtro de Familia de la cabecera (el ítem quedó
        # afuera). Los dos casos se sueltan igual — volver a "todas".
        if foco is not None and g_foco.empty:
            foco, g_foco = None, g

        # ── LA VISTA ABRE CON EL PRIMER ÍTEM ELEGIDO ─────────────────────
        # 2026-09-17, a pedido: «cuando se elija la opción de "El detalle"
        # Producto, inicialmente debe seleccionarse el primero, y el nombre
        # del producto debe aparecer en la tarjeta de barras».
        #
        # "El primero" es el primero DE LA TABLA, que se ordena por |Δ S/|
        # descendente (ver `_tabla_detalle`): el que más movió la aguja. No
        # el de mayor gasto — ése es el que elige `_auto` para Cantidad y
        # Precio, y son dos preguntas distintas.
        #
        # ES UN DEFAULT, NO UN CANDADO: volver a clickear la fila lo suelta
        # y la vista vuelve a "todas las compras", como siempre. Lo que
        # distingue "nadie eligió todavía" de "el usuario soltó el foco" es
        # `_K_FOCO_TOCADO`, que lo pone el handler de la tabla en cuanto
        # hay un clic — en los DOS sentidos.
        #
        # Y LA SIEMBRA NO ESCRIBE `compras_vap_foco`. Esa clave es el
        # espejo de lo que tiene SELECCIONADO la grilla, y la grilla no
        # sabe nada de esta siembra: al final de la corrida devuelve None,
        # el `if clic != ...` de abajo lo lee como una deselección, escribe
        # None y llama a `st.rerun` — que vuelve a sembrar, y otra vez. Se
        # vio como un bucle de reruns que terminaba reventando el fragment
        # con «Could not find current_fragment_id in fragment_id_queue»
        # (2026-09-17, en la primera pasada de este cambio). El foco
        # sembrado vive SÓLO en la variable local de este run.
        _tocado = st.session_state.get(_K_FOCO_TOCADO, False)
        if foco is None and not _tocado and not g.empty:
            _orden = _por_item(g, llave_foco)
            if not _orden.empty:
                _prim = str(_orden.loc[
                    (_orden["valor"] - _orden["valor_aa"]).abs().idxmax(),
                    "item"])
                _g_prim = g[g[llave_foco].astype(str) == _prim]
                if not _g_prim.empty:
                    foco, g_foco = _prim, _g_prim

        # Precio es un RATIO y Cantidad suma UNIDADES: sobre todas las
        # compras ninguno de los dos es una magnitud real. Medido el
        # 2026-09-13 (últimos 3 meses): la barra de Cantidad sumaba 26.461
        # KILOS + 28.687 UND + 2.204 LITROS en un solo número. Sin foco, las
        # dos se calculan sobre el PRODUCTO de mayor gasto y la cabecera lo
        # dice. Precio lo hacía desde antes; Cantidad, desde que pasó a
        # escribir la unidad («debe decir la unidad, por ejemplo 4300 kg»),
        # a elección del usuario entre tres salidas (regla #401).
        #
        # Por PRODUCTO y no por `llave_foco`: con el agrupador en Familia,
        # el "ítem de mayor gasto" era una familia, o sea otra vez kilos
        # con litros. Valor no entra acá: la plata sí se suma entre
        # unidades, y "todas las compras" es su lectura natural.
        _auto = False
        if modo in ("Precio", "Cantidad") and foco is None:
            _top = (g.groupby("prod")["valor"].sum().sort_values()
                    .index.tolist())
            if _top:
                g_foco = g[g["prod"].astype(str) == str(_top[-1])]
                foco_titulo = str(_top[-1])
                _auto = True
            else:
                foco_titulo = None
        else:
            foco_titulo = foco

        # Unidad y precio de la SERIE que se va a dibujar. La unidad se
        # escribe si todos sus productos comparten UNA (una familia toda en
        # kilos suma kilos de verdad); el precio, sólo si la serie es UN
        # producto — el precio por kilo de una familia se mueve con la
        # mezcla aunque nada haya subido (la trampa de `_por_item`).
        _ums_prod = _unidades_por(fuente, col_prod, col_um)
        _ums_serie = {_ums_prod.get(p, "")
                      for p in g_foco["prod"].astype(str).unique()} - {""}
        unidad_serie = (unidad_corta(next(iter(_ums_serie)))
                        if len(_ums_serie) == 1 else None)
        un_producto = g_foco["prod"].nunique() == 1

        # Mismo criterio que la tabla: el puente se suma desde los
        # productos, nunca se calcula sobre el agregado (ver `_por_item`).
        # EL MES ELEGIDO ACOTA LA CASCADA, NO LA VISTA. La serie sigue
        # dibujando la ventana entera —si no, el clic sería un zoom y no
        # habría dónde hacer el siguiente— y la tabla también, porque es el
        # detalle de la serie. Lo único que se recorta es lo que el puente
        # explica.
        #
        # Y se cae solo si el mes ya no está: pasar de 12m a 3m deja
        # "sep 25" apuntando a un mes que la ventana no muestra. Mismo
        # criterio que el foco del ítem doce líneas más arriba.
        _meses_serie = [_etiqueta_mes(m)
                        for m in sorted(g_foco["mes"].unique())]
        mes_sel = st.session_state.get(_K_MES)
        if mes_sel is not None and mes_sel not in _meses_serie:
            mes_sel = None
            st.session_state[_K_MES] = None
        g_casc = (g_foco if mes_sel is None
                  else g_foco[g_foco["mes"].map(_etiqueta_mes) == mes_sel])

        # Mismo criterio que la tabla: el puente se suma desde los
        # productos, nunca se calcula sobre el agregado (ver `_por_item`).
        _items = _por_item(g_casc)
        tot = _items[["valor", "cant", "valor_aa", "cant_aa",
                      "ef_precio", "ef_cant"]].sum()
        ef_p, ef_c = float(tot["ef_precio"]), float(tot["ef_cant"])
        # El Δ y su % ya no se calculan acá: los arma la tarjeta del puente
        # EN SU MAGNITUD (soles, kilos o S/ por kilo), que desde el
        # 2026-09-16 no siempre es la misma. Ver «LA MAGNITUD, DE UN SOLO
        # SITIO» más abajo.

        # El ámbito dice SÓLO el ítem en foco (2026-09-02, a pedido:
        # "eliminemos el texto que dice Todas las compras, que ya no
        # exista"). Los dos pedazos que se fueron eran ruido de distinta
        # clase:
        #   · "Todas las compras" nombraba el estado por DEFECTO — o sea,
        #     ocupaba el renglón para decir que no había nada elegido.
        #   · "· últimos 3 meses" repetía lo que dice la lista de ventana.
        # El criterio sobrevivió a la mudanza del 2026-09-17: sin foco no
        # se escribe nada, acá tampoco.
        # EL NOMBRE VIVE EN LA TARJETA DE LAS BARRAS, no al lado del título
        # (2026-09-17, a pedido). El título de la cabecera quedó solo:
        # nombra la VISTA, y el ámbito es de cada tarjeta — la cascada ya
        # lo decía en su rótulo desde la #443, y la serie no lo decía en
        # ninguna parte. Sin foco no se escribe nada: cuando no hay
        # recorte, no hay nada que aclarar.
        _nom_serie.markdown(
            _nombre_serie_html(foco_titulo, auto=_auto),
            unsafe_allow_html=True)

        # Las dos tarjetas de la fila ya están abiertas (ver «LA FILA DE
        # TARJETAS SE ABRE ACÁ»): acá se RELLENAN. `COLUMNAS_DRILL` las ata
        # al mismo eje que las de Proveedor y Producto, y el piso de alto de
        # `estilos/_80_cards.py` (#145) las hace terminar en la misma línea.
        with _tarj_serie:
            fig = _fig_serie(g_foco, modo, parcial, unidad=unidad_serie,
                             con_precio=un_producto, mes_sel=mes_sel)
            if fig is not None:
                # `on_select` y no un widget aparte: el mes se elige donde
                # se lo ve. El clic ya se resolvió ARRIBA DE TODO (ver «EL
                # CLIC EN UN MES SE RESUELVE ANTES DE DIBUJAR NADA»), así
                # que lo que devuelve esta llamada no se lee, a propósito.
                st.plotly_chart(fig, use_container_width=True,
                                on_select="rerun", selection_mode="points",
                                key=_key_serie)
        with _tarj_puente:
            _tarjeta_cascada(
                items=_items, ums_prod=_ums_prod,
                unidad_serie=unidad_serie, modo=modo, tot=tot,
                foco_titulo=foco_titulo, mes_sel=mes_sel,
                ef_p=ef_p, ef_c=ef_c, g_casc=g_casc, g_foco=g_foco,
                llave_foco=llave_foco)

        if parcial is not None:
            # El aviso del mes parcial deja de ser un caption en flujo y
            # entra en el popover de ayuda de la cabecera (ver el hueco de
            # más arriba). La señal EN PANTALLA sigue siendo la trama de la
            # última barra, que es donde mira el que tiene que verla.
            _ayuda_parcial.markdown(
                "---" + PARR
                + f"El **último mes** va hasta el día {parcial[1]} (es lo "
                f"que trae el parquet): su barra sale con trama y se compara "
                f"contra los mismos días del año pasado, no contra el mes "
                f"entero.")

        # ── La tabla de detalle ──────────────────────────────────────────
        # (Desde el 2026-09-14 vuelve a tener tarjeta PROPIA —
        # `compras_vap_card_tabla`, #420—, pero SIN título ni cabecera: lo
        # que se deshizo fue la superficie compartida, no lo de abajo.)
        #
        # 2026-09-02, a pedido: "que la tarjeta de la tabla se fusione con
        # la de arriba, y que desaparezca el título 'Detalle ítem por
        # ítem'". Acá había un segundo `_card(...)` con su propia cabecera.
        #
        # El título sobraba de verdad, no sólo estéticamente: la tabla ES el
        # detalle del gráfico de arriba —mismo `g`, mismo período, y el clic
        # en una fila enfoca la serie— así que anunciarla como otra cosa
        # partía en dos algo que se lee de corrido. Con los dos controles ya
        # mudados a la fila del título, la cabecera propia se quedaba sin
        # nada que sostener.
        #
        # El bloque de `st.columns([1, 1.4, 2.6])` que repartía agrupador y
        # buscador también se fue: en la fila del título los reparte el flex
        # de `vap_fila_hdr`, sin espaciador que inventar.

        # (El remap de `grupo` ya corrió arriba, antes de resolver el foco.
        # `agrupar_nuevo` y `agrupar_por` son el mismo valor: el widget se
        # dibuja en la cabecera, así que su lectura de `session_state` de
        # más arriba ve el valor de ESTE run.)

        # Su tarjeta se abre ACÁ y no arriba con las otras: la posición en
        # pantalla la decide el orden en que se crean los contenedores, y
        # ésta va debajo de la fila de la serie. El aviso del buscador sale
        # adentro, donde iba la tabla.
        _tarj_tabla = st.container(key="compras_vap_card_tabla")
        g_tabla = g if not q else g[
            g["prod" if agrupar_nuevo == "Producto" else "grupo"]
            .astype(str).str.lower().str.contains(q, regex=False)]
        if g_tabla.empty:
            _tarj_tabla.info(f"Ningún ítem coincide con «{q}».")
            return

        # Unidad de medida por ítem, para el tooltip de la tabla. Misma
        # resolución que la del puente de arriba (`_unidades_por`), que es
        # por qué son una función y no dos bloques parecidos: el día que la
        # moda deje de ser el criterio, tiene que cambiar en un solo sitio.
        _llave_um = col_prod if agrupar_nuevo == "Producto" else (
            col_fam if agrupar_nuevo == "Familia" else col_subfam)
        ums = _unidades_por(fuente, _llave_um, col_um)

        # Los rangos salen de `g` (la ventana entera) y no de `g_tabla` (ya
        # filtrado por el buscador): la cabecera describe la CUENTA, que es
        # la misma se busque lo que se busque. Ver `_tabla_detalle`.
        _m0, _m1 = g["mes"].min(), g["mes"].max()
        with _tarj_tabla:
            clic = _tabla_detalle(g_tabla, agrupar_nuevo, ums,
                                  "compras_vap_detalle_grid",
                                  rangos=(_rango_meses(_m0, _m1),
                                          _rango_meses(_m0 - 12, _m1 - 12)))

        # UNA sola comparación, igual que el ranking de Proveedor: AG Grid
        # conserva su selección entre reruns del fragment, así que `clic`
        # vuelve igual mientras nadie toque la tabla y esto no dispara nada.
        # Deseleccionar (clic en la fila activa) devuelve None y vuelve a
        # "todas las compras" — es un gesto explícito, se respeta.
        if clic != st.session_state.get("compras_vap_foco"):
            st.session_state["compras_vap_foco"] = clic
            # Desde acá la siembra del primer ítem no vuelve a correr: el
            # usuario ya eligió, y "sin foco" pasa a significar "soltó el
            # foco" y no "todavía no eligió" (ver `_K_FOCO_TOCADO`).
            st.session_state[_K_FOCO_TOCADO] = True
            # EL SCOPE SE DECIDE, no se fija. `scope="fragment"` sólo es
            # legal durante un rerun DE fragment; en una corrida completa
            # del script Streamlit lo prohíbe y se cae la pantalla entera
            # (regla #306). Acá reventó de verdad el 2026-09-04:
            #
            #   StreamlitInvalidLayoutContextError
            #     .../graficos/compras/vs_ano_pasado.py:1165
            #
            # Era latente —una corrida completa la dispara cualquier cambio
            # de fecha o de chips en `app.py`, con la selección de AG Grid
            # todavía viva— y el ⛶ del modo solo la volvió frecuente: cada
            # entrada y cada salida es un `st.rerun(scope="app")`.
            #
            # No se puede arreglar como la #306 (dejar de rerunear): allá el
            # único consumidor del foco se dibujaba DESPUÉS en la misma
            # corrida. Acá el consumidor es el gráfico de ARRIBA, que en
            # esta pasada ya se dibujó — hace falta otra sí o sí.
            st.rerun(scope=scope_rerun())
