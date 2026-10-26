"""
graficos.ventas_mix — vista «Mix de carta» del dashboard de Ventas: la venta
por período partida por lo que se vendió —Grupo › Sub Grupo › Producto, o
Área › Sub Grupo › Producto—, con el Resumen, Qué movió, el Mapa de la
carta, Mix y costo y el Cálculo debajo.

Nació el 2026-09-25 de un mockup aprobado (regla #527) y ese mismo día se
fueron dos vistas: «Venta por día» y «Familia/Subfamilia semanal».

DESDE EL 2026-10-22 ES UNA PIEZA PROPIA (regla #702): `ventas_mix.js` +
`.css` (`st.components.v2`), sobre el boceto aprobado
(https://claude.ai/artifact/7V1JFc8uhBouVgd4dXkR8T). Python carga el rango,
arma la base (la definición de venta ya aplicada, un ítem una vez, los
convenios del banco) y manda las sumas POR PRODUCTO Y PERÍODO; el navegador
suma lo demás. Bajar de nivel, fijar un período, Soles | Unidades, la
escala, Carta | Área, las pestañas y la ficha no piden corrida. Vuelven a
Python sólo cuatro cosas, cada una porque carga algo:

  · `gran`    — otra granularidad: las sumas son por período.
  · `ap`      — «Año pasado»: el mismo rango un año antes, de R2, una vez.
  · `lineas`  — Cálculo de un producto, venta por venta (las líneas no
                viajan enteras).
  · `carta`   — el salto a Recetas › Costo de Carta.

LAS CUENTAS PURAS DE ACÁ SIGUEN SIENDO LA REFERENCIA: `pct_costo` (costo ÷
base, sin cociente donde no hay costo o el neto no llega a medio sol),
`tramos` (siete con color y «Resto (N)», nunca «Resto (1)») y `calculo`
(la tabla de dónde sale cada %). El `.js` las rehace igual, y el test busca
las fórmulas escritas igual.

«RESTO» Y NO «OTROS»: en `ventas.parquet` hay un Grupo que se llama
«Otros», y un tramo que juntara a los chicos con ese nombre se leía como si
fuera él.
"""

from graficos.movil import css_movil, js_movil
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import convenios_descuento
from cortes import MESES_ABR_ES
from data import REPORTES
from tema import ADVERTENCIA_TEXTO, ERROR, PALETA_SERIES, SCROLL_THUMB
from graficos.base import _resolver, selector_fecha_tarjeta
from graficos.compras._comun import (_cobertura, _limites_periodo,
                                     _periodo_serie)
from graficos.compras.semanal import _rotulo_periodo
from graficos.ventas_comparativo import _cargar_tramo
from graficos.ventas_horario import nombre_area
from graficos.ventas_resumen import (MAX_DIAS, _COSTO_ALTO, _COSTO_ROTO,
                                     _fmt_dia, cambios_de_igv, nota_igv)

_GRAN_OPCIONES = ("Día", "Semana", "Mes", "Año")
_GRAN_DEFAULT = "Semana"
"""Las granularidades del Resumen ejecutivo. Abre en Semana y no en Día: con
el mes corrido con que abre Ventas son cuatro o cinco barras, y una barra
diaria partida en siete tramos no se lee."""

_MEDIDAS = ("Soles", "Unidades")
_TIP_COSTO = ("Costo ÷ venta neta más lo que el banco devuelve de los "
              "descuentos de convenio (Costos › Convenios). Lo vendido sin "
              "costo cargado no entra")
_AYUDA_SIN_DESC = (
    "El costo ÷ la venta neta que habría dado a precio de CARTA, sin "
    "descuentos. La distancia con «% costo» es lo que pesan los "
    "descuentos: el plato cuesta lo mismo y se cobra menos. Power BI lo "
    "llama «%FC Receta».")
"""Qué dicen las celdas de «% costo» y «% sin desc.» (reglas #544 y #664).
Viajan a la pieza como ayuda de sus cabeceras."""

_EJE_CARTA, _EJE_AREA = "Carta", "Área"
"""Por dónde se abre la venta (regla #595): el árbol de la carta (Grupo ›
Subgrupo › Producto) o el de la cocina (Área › Subgrupo › Producto), con el
área de producción a la que el POS manda cada plato. `base` deja el área en
su columna `area` siempre (la pieza cambia de árbol sin corrida) y, con
`eje` = Área, también en `grupo`. El segundo nivel es el SUBGRUPO y no el
grupo: casi toda área prepara un solo grupo («Cocina» es Alimentos), y
abrirla mostraba una barra entera de lo mismo."""
_NOMBRES_EJE = {
    _EJE_CARTA: (("Grupos", "Subgrupos", "Productos"),
                 ("grupo", "subgrupo", "producto"), "Todos los grupos"),
    _EJE_AREA: (("Áreas", "Subgrupos", "Productos"),
                ("área", "subgrupo", "producto"), "Todas las áreas"),
}
"""Cómo se llaman los niveles de cada árbol. La pieza los recibe tal cual."""

_MAX_TRAMOS = 7
"""Tramos con color en la barra; el resto va junto. Con 8 se muestran los 8:
juntar uno solo en «Resto (1)» es esconderlo sin ganar nada."""

_COLORES = tuple(PALETA_SERIES[:_MAX_TRAMOS])
"""Uno por tramo, en orden de venta. La pieza los pinta con su espejo CSS,
`--serie-0…6` (`estilos/_00_base.py`), que cruza el shadow root."""

_COLOR_RESTO = SCROLL_THUMB
"""El gris del tramo «Resto». Su espejo es `--scroll-thumb`."""


# ===========================================================================
# LOS DATOS
# ===========================================================================

def columnas(d):
    """Las columnas que usa la vista, resueltas contra `d`. `costo` es el de
    la LÍNEA que arma `definicion_venta` (el unitario suelto daba un % de
    costo de 24 donde era 29: reglas #524 y #542)."""
    return {
        "fecha": _resolver(d, ["Fec Reg Documento", "Fecha Registro", "FECHA"]),
        "grupo": _resolver(d, ["Grupo"]),
        "sub": _resolver(d, ["Sub Grupo", "Sub_Grupo", "Subgrupo"]),
        "area": _resolver(d, ["Area Produccion"]),
        "prod": _resolver(d, ["Nomb Item Venta", "Nombre Producto",
                              "Producto", "Descripcion"]),
        "venta": _resolver(d, ["Venta Item Ddocumento", "Venta"]),
        "cant": _resolver(d, ["Cantidad Item Ddocumento", "Cantidad"]),
        "costo": _resolver(d, ["Costo Venta", "Costo Item Ddocumento"]),
        "neto": _resolver(d, ["Neto Total Item Ddocumento"]),
        # El precio de CARTA por unidad: de él sale «% sin desc.» (#664).
        "carta": _resolver(d, ["Precio Oficial Item Ddocumento"]),
        # El descuento y su código: lo que devuelve el banco de un convenio
        # entra en la base del «% costo» (#665).
        "desc": _resolver(d, ["Descuento Item Ddocumento"]),
        "cod_desc": _resolver(d, ["Codigo Descuento"]),
        # Sólo para la zona «Cálculo» (#666): de dónde sale cada %.
        "recargo": _resolver(d, ["Recargo Item Ddcoumento",
                                 "Recargo Item Ddocumento"]),
        "nom_desc": _resolver(d, ["Nombre Descuento"]),
        # De él sale la tasa de IGV, que marca el período en que cambió y
        # movió el % de costo sin tocar ningún costo (regla #590).
        "igv": _resolver(d, ["Igv Item Ddocumento"]),
    }


def base(d, cols, eje=_EJE_CARTA, convenios=None):
    """Una fila por ítem vendido con los tres niveles de la carta y sus
    sumas, con nombres FIJOS: todo lo de abajo agrupa por columna de verdad
    y renombra por nombre (regla #481, pandas 2 contra pandas 3). `igv` va
    en cero si `cols` no lo trae (un llamador viejo de `columnas`).

    Con `eje` = Área los niveles son Área › Subgrupo › Producto, en las
    MISMAS columnas (`grupo` lleva el área): todo lo de abajo sigue igual.
    El área está además, con cualquier `eje`, en `area`.

    Un nivel vacío se nombra («(sin grupo)») en vez de caerse: esa venta
    existe y tiene que sumar en algún lado.

    `convenios` (la tabla de `convenios_descuento`) llena `devol`: lo que el
    banco devuelve del descuento de cada línea, sin impuestos (#665). Sin
    ella, cero."""
    def _num(col):
        if not col or col not in d.columns:
            return pd.Series(0.0, index=d.index)
        return pd.to_numeric(d[col], errors="coerce").fillna(0.0)

    def _txt(col, vacio):
        if not col or col not in d.columns:
            return pd.Series(vacio, index=d.index)
        s = d[col].astype("object")
        s = s.where(s.notna(), vacio).astype(str).str.strip()
        return s.where(s != "", vacio)

    b = pd.DataFrame({
        "fecha": pd.to_datetime(d[cols["fecha"]], errors="coerce"),
        "grupo": _txt(cols["grupo"], "(sin grupo)"),
        "sub": _txt(cols["sub"], "(sin subgrupo)"),
        "prod": _txt(cols["prod"], "(sin nombre)"),
        "venta": _num(cols["venta"]),
        "cant": _num(cols["cant"]),
        "costo": _num(cols["costo"]),
        "neto": _num(cols["neto"]),
        "igv": _num(cols.get("igv")),
    })
    b["neto_carta"] = neto_a_carta(b, _num(cols.get("carta")))
    b["desc"] = _num(cols.get("desc"))
    b["rec"] = _num(cols.get("recargo"))
    b["tipo_desc"] = _txt(cols.get("nom_desc"), "")
    b["dev_pct"] = 0.0
    if convenios is not None and len(convenios) and cols.get("cod_desc"):
        b["dev_pct"] = convenios_descuento.devolucion_por_linea(
            d[cols["cod_desc"]], b["fecha"], convenios)
    b["devol"] = b["desc"] * b["dev_pct"] * _tasa_neta(b)
    # Lo vendido SIN COSTO CARGADO no entra en ningún % de costo (#666): no
    # saberlo no es costar cero (#524), y su venta en el divisor bajaba el
    # % de todo su grupo. Una nota de crédito (venta negativa) sí entra.
    sin_costo = (b["venta"] > 0.005) & (b["costo"] <= 0)
    b["venta_sin_costo"] = b["venta"].where(sin_costo, 0.0)
    b["base_costo"] = (b["neto"] + b["devol"]).where(~sin_costo, 0.0)
    b["neto_carta"] = b["neto_carta"].where(~sin_costo, 0.0)
    # El área va SIEMPRE en su columna: la pieza cambia de árbol sin
    # corrida (regla #702). Con `eje` = Área, además en `grupo`.
    b["area"] = (nombre_area(d[cols["area"]])
                 if cols.get("area") and cols["area"] in d.columns
                 else "Sin área")
    if eje == _EJE_AREA:
        b["grupo"] = b["area"]
    return b.dropna(subset=["fecha"])


def alcance(b, ruta):
    """`b` recortado al nivel en pantalla: `ruta` es `()`, `(grupo,)` o
    `(grupo, sub)`, por nombre."""
    if len(ruta) >= 1:
        b = b[b["grupo"] == ruta[0]]
    if len(ruta) >= 2:
        b = b[b["sub"] == ruta[1]]
    return b


def ruta_valida(b, ruta):
    """La parte de `ruta` que sigue existiendo en `b`. Un chip de la franja
    puede sacar el grupo en el que el usuario estaba parado."""
    ruta = tuple(ruta or ())[:2]
    if ruta and ruta[0] not in set(b["grupo"]):
        return ()
    if len(ruta) == 2 and ruta[1] not in set(
            b.loc[b["grupo"] == ruta[0], "sub"]):
        return ruta[:1]
    return ruta


_SUMAS = ("venta", "cant", "costo", "neto", "neto_carta", "devol",
          "base_costo", "venta_sin_costo")
"""Lo que `matriz` suma por período (no confundir con `_MEDIDAS`, lo que
mide el gráfico)."""


def neto_a_carta(b, carta_unit):
    """La venta neta que habría dado cada línea A PRECIO DE CARTA, sin
    descuentos: carta × cantidad, sin IGV ni recargo (#664). Es el
    denominador de «% sin desc.», que con «% costo» al lado dice cuánto
    del costo pesa por los descuentos: un plato al 50 % cuesta lo mismo y
    se cobra la mitad.

    Los impuestos salen de la propia línea (neto ÷ venta: el IGV y el
    recargo no son parejos, Aceite Quemado no lleva recargo); una línea
    regalada entera no tiene venta de dónde sacarlos y usa los de todo `b`.
    Sin la columna del precio de carta, cero: `pct_costo` lo escribe «—».

    Es lo que Power BI llama «%FC Receta» en su página de Productos: costo
    ÷ esto, cuadrado al décimo en 11 de 11 platos (febrero 2026)."""
    return (carta_unit * b["cant"] * _tasa_neta(b)).fillna(0.0)


def _tasa_neta(b):
    """Por línea, neto ÷ venta: lo que queda de un sol cobrado sin IGV ni
    recargo. Una línea sin venta (regalada entera) usa la de todo `b`."""
    con_venta = b["venta"].abs() > 0.005
    tasa = (b["neto"] / b["venta"]).where(con_venta)
    v = float(b.loc[con_venta, "venta"].sum())
    return tasa.fillna(float(b.loc[con_venta, "neto"].sum()) / v if v else 0.0)


def matriz(b, col, claves):
    """Por miembro del nivel (`col`) y período: `{medida: DataFrame}`, con los
    miembros en filas y las claves de período en columnas, EN ORDEN y con
    cero donde no hubo venta. Agrupa por dos columnas de verdad y arma cada
    tabla por nombre (regla #481)."""
    ag = (b.groupby([col, "clave"], as_index=False)
          [list(_SUMAS)].sum())
    salida = {}
    for m in _SUMAS:
        t = ag.pivot_table(index=col, columns="clave", values=m,
                           aggfunc="sum")
        salida[m] = t.reindex(columns=list(claves)).fillna(0.0)
    return salida


_NETO_MIN = 0.5
"""Medio sol. Un neto menor no es una venta: los platos de cortesía que el
POS cobra a S/ 0 dentro de una boleta («Chirimoya a la Brasa - Cortesia»,
«Encurtido de Vegetales») dejan un residuo de coma flotante —S/ 0,00002
por línea— que, dividido, daba un % de costo de 10.930.554 (regla #547).
Ninguna venta de verdad de un plato suma tan poco, y un total de grupo o de
período no se acerca."""


def pct_costo(costo, neto):
    """Costo ÷ neto, la cuenta del Resumen («Costo ÷ Neto»), para un número,
    una Serie o una tabla entera de `matriz()` (regla #544).

    Es NaN —y la celda dice «—»— donde no hay costo cargado: no saberlo no
    es costar cero (regla #524). Y también donde el neto no llega a
    `_NETO_MIN`: una nota de crédito que cae en otro período que su venta lo
    deja negativo, y una cortesía a S/ 0 lo deja en un residuo; en los dos
    casos el cociente sale con signo cambiado o gigante sin medir nada."""
    if np.isscalar(costo):
        return costo / neto if (costo > 0 and neto > _NETO_MIN) else np.nan
    return costo.where(costo > 0) / neto.where(neto > _NETO_MIN)


def tramos(orden, prod_foco=None, sub=None):
    """Cómo se parte la barra: `[(nombre, miembros, es_resto)]` de abajo hacia
    arriba. Siete con nombre y los demás en «Resto (N)»; con un producto en
    foco, ese producto contra el resto de su subgrupo."""
    orden = list(orden)
    if prod_foco is not None and prod_foco in orden:
        resto = [n for n in orden if n != prod_foco]
        salida = [(prod_foco, [prod_foco], False)]
        if resto:
            salida.append((f"Resto de {sub}" if sub else "Resto", resto, True))
        return salida
    if len(orden) <= _MAX_TRAMOS + 1:
        return [(n, [n], False) for n in orden]
    resto = orden[_MAX_TRAMOS:]
    return ([(n, [n], False) for n in orden[:_MAX_TRAMOS]]
            + [(f"Resto ({len(resto)})", resto, True)])


def rango_ano_pasado(clave, gran, rango):
    """`(ini, fin)` del mismo período un año antes, recortado a los días que
    el rango cubre de ESTE: un mes en curso (1–23 set) se compara contra el
    1–23 set del año pasado, no contra el mes entero.

    Día y Semana corren 364 días —el mismo día de la semana, que en un
    restaurante es lo que manda (`ventas_comparativo.py`, «Mismo día»)—; Mes
    y Año, la misma fecha del calendario."""
    ini, fin = _limites_periodo(clave, gran)
    if rango:
        ini, fin = max(ini, rango[0]), min(fin, rango[1])
    if gran in ("Día", "Semana"):
        return ini - timedelta(days=364), fin - timedelta(days=364)

    def _un_ano_antes(x):
        try:
            return x.replace(year=x.year - 1)
        except ValueError:                 # 29 de febrero
            return date(x.year - 1, x.month, 28)
    return _un_ano_antes(ini), _un_ano_antes(fin)


def _rotulos(claves, gran, rango=None):
    """`(eje, largo)`: cómo se nombra cada período en el eje y en el hover.
    Los de Semana y Mes son los de Compras —con `rango`, una semana cortada
    se nombra por sus días, regla #619—; Día, los del Resumen."""
    if gran == "Día":
        dias = [pd.Timestamp(c) for c in claves]
        return ([f"{x:%d/%m}" for x in dias],
                [f"{_fmt_dia(x)}/{x.year}" for x in dias])
    rot = [_rotulo_periodo(c, gran, rango) for c in claves]
    return [r[0] for r in rot], [r[1] for r in rot]


def _nombre_rango(ini, fin):
    """«15–21 set 2025», «31 ago–6 set 2026», «20 set 2025»: los días de un
    tramo, con el año, como los nombra el eje de Compras. Es lo que dice el
    Detalle cuando compara contra el año pasado: ahí el período NO es el del
    eje, son sus mismos días un año antes."""
    m = MESES_ABR_ES
    if ini == fin:
        return f"{ini.day} {m[ini.month - 1]} {ini.year}"
    if (ini.year, ini.month) == (fin.year, fin.month):
        return f"{ini.day}–{fin.day} {m[fin.month - 1]} {fin.year}"
    if ini.year == fin.year:
        return (f"{ini.day} {m[ini.month - 1]}–{fin.day} {m[fin.month - 1]} "
                f"{fin.year}")
    return (f"{ini.day} {m[ini.month - 1]} {ini.year}–{fin.day} "
            f"{m[fin.month - 1]} {fin.year}")


CALCULO_LINEAS = ("Fecha", "Cant.", "Venta", "IGV", "Recargo", "Descuento",
                  "Tipo de descuento", "Devol. banco", "Base", "Costo",
                  "% costo", "% sin desc.")
CALCULO_PRODUCTOS = ("Producto", "Cant.", "Venta", "IGV", "Recargo",
                     "Descuento", "Devol. banco", "Base", "Costo", "% costo",
                     "% sin desc.", "Sin costo")


def calculo(bp, por_linea):
    """De dónde sale el % de costo (#666): `bp` son las líneas de la base
    (`base`) que se miran. Con `por_linea`, una fila por venta (el producto
    en foco); si no, una por producto. La primera fila es el TOTAL.

    Venta − IGV − Recargo = neto; Base = neto + lo que devuelve el banco
    (#665), cero si la línea se vendió sin costo cargado; % costo = Costo ÷
    Base; % sin desc. = Costo ÷ el neto a precio de carta (#664). Columnas
    por nombre (#481)."""
    cols_num = ["cant", "venta", "igv", "rec", "desc", "devol", "base_costo",
                "costo", "neto_carta", "venta_sin_costo"]
    if por_linea:
        g = bp.sort_values("fecha", ascending=False, kind="stable")
        g = g.assign(Fecha=g["fecha"].dt.strftime("%d/%m/%Y %H:%M"),
                     _tipo=g["tipo_desc"].where(g["desc"].abs() > 0.005, ""))
    else:
        g = (bp.groupby("prod", as_index=False)[cols_num].sum()
             .sort_values("venta", ascending=False, kind="stable"))
    tot = bp[cols_num].sum()
    pc = lambda c, n: pct_costo(c, n)  # noqa: E731
    filas = pd.DataFrame({
        ("Fecha" if por_linea else "Producto"):
            (g["Fecha"] if por_linea else g["prod"]).to_numpy(),
        "Cant.": g["cant"].to_numpy(), "Venta": g["venta"].to_numpy(),
        "IGV": g["igv"].to_numpy(), "Recargo": g["rec"].to_numpy(),
        "Descuento": g["desc"].to_numpy(),
        **({"Tipo de descuento": g["_tipo"].to_numpy()} if por_linea else {}),
        "Devol. banco": g["devol"].to_numpy(), "Base": g["base_costo"].to_numpy(),
        "Costo": g["costo"].to_numpy(),
        "% costo": pc(g["costo"], g["base_costo"]).to_numpy(),
        "% sin desc.": pc(g["costo"], g["neto_carta"]).to_numpy(),
        **({} if por_linea else {"Sin costo": g["venta_sin_costo"].to_numpy()}),
    })
    total = {filas.columns[0]: "Total", "Cant.": tot["cant"], "Venta": tot["venta"],
             "IGV": tot["igv"], "Recargo": tot["rec"], "Descuento": tot["desc"],
             "Devol. banco": tot["devol"], "Base": tot["base_costo"],
             "Costo": tot["costo"],
             "% costo": pct_costo(float(tot["costo"]), float(tot["base_costo"])),
             "% sin desc.": pct_costo(float(tot["costo"]), float(tot["neto_carta"]))}
    if por_linea:
        total["Tipo de descuento"] = ""
    else:
        total["Sin costo"] = tot["venta_sin_costo"]
    salida = pd.concat([pd.DataFrame([total]), filas], ignore_index=True)
    return salida[list(CALCULO_LINEAS if por_linea else CALCULO_PRODUCTOS)]


def _estilo_costo(v):
    """El color de un % de costo: los umbrales y los colores del Resumen
    (`ventas_resumen._COSTO_ALTO`/`_COSTO_ROTO`, y `.vr-alto`/`.vr-roto` de
    `tablas/ventas_resumen.py`), importados y no copiados, para que el mismo
    número se pinte igual en las dos vistas (regla #544)."""
    if pd.isna(v):
        return ""
    if v > _COSTO_ROTO:
        return f"color: {ERROR}; font-weight: 700"
    if v > _COSTO_ALTO:
        return f"color: {ADVERTENCIA_TEXTO}; font-weight: 600"
    return ""


# ===========================================================================
# LA PIEZA (regla #702)
# ===========================================================================

_PIEZA = st.components.v2.component(
    "ventas_mix",
    css=css_movil((Path(__file__).parent / "ventas_mix.css").read_text(encoding="utf-8")),
    js=js_movil((Path(__file__).parent / "ventas_mix.js").read_text(encoding="utf-8")),
)
_K_PIEZA = "vt_mix_pieza"
_K_GRAN = "vt_mix_gran"
_K_AP = "vt_mix_con_ap"
"""Pedido una vez «Año pasado», la vista lo sigue trayendo en la sesión: la
carga de R2 queda en la caché de `cargar_rango`."""
_K_LINEAS = "vt_mix_lineas"
_MAX_LINEAS = 400
"""Ventas de un producto que viajan al Cálculo. Un plato de todos los días
en un año son ~2.000; arriba va el TOTAL, que sí las cuenta a todas."""

METRICAS = ("venta", "cant", "costo", "base_costo", "neto_carta",
            "venta_sin_costo", "igv", "rec", "desc", "devol")
"""Lo que viaja por producto y período, EN ESTE ORDEN: el `.js` lo lee por
posición (`V, Q, C, B, NC, SC, IGV, REC, DESC, DEV`)."""

_LLAVE = ("grupo", "sub", "prod", "area")


def periodos(b, gran):
    """`(b con su clave de período, claves, nota)`. En Día, los últimos
    `MAX_DIAS` días con ventas, como el Resumen: más barras que eso no se
    leen, y una por día con un año cargado congelaba la página (regla
    #523)."""
    b = b.assign(clave=_periodo_serie(b["fecha"], gran))
    nota = ""
    if gran == "Día":
        dias = sorted(b["fecha"].dt.normalize().unique())
        if len(dias) > MAX_DIAS:
            b = b[b["fecha"] >= dias[-MAX_DIAS]]
            nota = f"Los últimos {MAX_DIAS} días con ventas."
    return b, sorted(b["clave"].unique()), nota


def _sumas(b, j_de):
    """Por producto (`_LLAVE`) y período (`j`): las `METRICAS`, agrupando
    por columnas de verdad (regla #481)."""
    g = (b.assign(j=b["clave"].map(j_de)).dropna(subset=["j"])
         .groupby([*_LLAVE, "j"], as_index=False)[list(METRICAS)].sum())
    return g


def armar_mix(b, claves, gran, rango, b_ap=None, ap_nombres=None, nota="",
              lineas=None, hay_area=True, codigos=None, igv_notas=None):
    """Lo que recibe la pieza. Pura: la lee el test.

    `b` es la `base` con su `clave` de período; `b_ap`, la base del año
    pasado con `j`, el período de ESTE rango con el que se compara cada
    fila (o None si no se pidió); `ap_nombres`, por período, cómo se
    llaman esos días un año antes, o None si no hay. Un producto:
    [grupo, subgrupo, nombre, área]; una fila: [producto, período, *las
    METRICAS redondeadas a céntimo], sin las que son todo cero."""
    j_de = {k: j for j, k in enumerate(claves)}
    g = _sumas(b, j_de)
    g_ap = None
    if b_ap is not None and not b_ap.empty:
        g_ap = (b_ap.groupby([*_LLAVE, "j"], as_index=False)
                [list(METRICAS)].sum())
    llaves = pd.concat([x[list(_LLAVE)] for x in (g, g_ap) if x is not None])
    prods = llaves.drop_duplicates().reset_index(drop=True)
    pi_de = {tuple(r): i for i, r in enumerate(prods.itertuples(index=False,
                                                                name=None))}

    def _filas(t):
        if t is None:
            return []
        num = t[list(METRICAS)].round(2)
        vivas = num.abs().sum(axis=1) > 0.004
        pis = [pi_de[x] for x in t.loc[vivas, list(_LLAVE)].itertuples(
            index=False, name=None)]
        js = t.loc[vivas, "j"].astype(int).tolist()
        return [[p, j, *v] for p, j, v in zip(pis, js,
                                               num[vivas].to_numpy().tolist())]

    rot_eje, rot_largo = _rotulos(claves, gran, rango)
    igv_notas = igv_notas or [None] * len(claves)
    codigos = codigos or {}
    return {
        "gran": gran, "grans": list(_GRAN_OPCIONES),
        "periodos": [{
            "clave": str(k), "eje": e, "largo": lg,
            "parcial": bool(rango) and _es_parcial(k, gran, rango),
            "igv": igv_notas[j],
        } for j, (k, e, lg) in enumerate(zip(claves, rot_eje, rot_largo))],
        "prods": prods.to_numpy().tolist(),
        "codigos": [codigos.get(str(p).strip().lower(), "")
                    for p in prods["prod"]],
        "filas": _filas(g),
        "ap": (None if b_ap is None else
               {"filas": _filas(g_ap), "nombres": list(ap_nombres or [])}),
        "lineas": lineas, "nota": nota, "hay_area": bool(hay_area),
        "niveles": {k: [list(v[0]), list(v[1]), v[2]]
                    for k, v in _NOMBRES_EJE.items()},
        "umbrales": [_COSTO_ALTO, _COSTO_ROTO], "tramos": _MAX_TRAMOS,
        "ayuda": {"costo": _TIP_COSTO, "sin_desc": _AYUDA_SIN_DESC},
    }


def _es_parcial(clave, gran, rango):
    """El rango corta el período: tiene menos días adentro que los suyos."""
    n, m = _cobertura(clave, gran, rango)
    return n < m


def ano_pasado(b_ap, claves, gran, rango):
    """`(b_ap con j, nombres)`: cada fila del año pasado con el período de
    ESTE rango contra el que se compara (`rango_ano_pasado`: los mismos días,
    un mes en curso contra el mismo tramo), y cómo se llaman esos días. Un
    período sin nada un año antes —el parquet empieza el 1-ene-2025— no es
    «cero ventas»: su nombre es None y la pieza dice «sin año pasado»."""
    fechas = b_ap["fecha"].dt.date
    j = pd.Series(np.nan, index=b_ap.index)
    nombres = []
    for i, k in enumerate(claves):
        ini, fin = rango_ano_pasado(k, gran, rango)
        dentro = (fechas >= ini) & (fechas <= fin)
        j = j.mask(dentro, i)
        nombres.append(_nombre_rango(ini, fin) if dentro.any() else None)
    return b_ap.assign(j=j).dropna(subset=["j"]), nombres


def _cargar_ano_pasado(claves, gran, rango, filtrar_cb, convenios):
    """La base del año pasado de TODO el rango, en UNA carga de R2."""
    tramos = [rango_ano_pasado(k, gran, rango) for k in claves]
    cfg = REPORTES.get("Ventas", {})
    df = _cargar_tramo(cfg.get("archivo", "ventas.parquet"),
                       cfg.get("carga_por_rango", "FEC REG DOCUMENTO"),
                       min(t[0] for t in tramos), max(t[1] for t in tramos),
                       filtrar_cb)
    if df is None:
        return None, [None] * len(claves)
    return ano_pasado(base(df, columnas(df), convenios=convenios),
                      claves, gran, rango)


def lineas_de(b, pedido):
    """Cálculo de un producto, venta por venta (#666): `pedido` es lo que
    mandó la pieza —{l0, sub, prod, eje, claves}—. Devuelve lo que la pieza
    reconoce como la respuesta a SU pedido (`clave`), con el TOTAL arriba y
    las ventas más nuevas debajo, hasta `_MAX_LINEAS`."""
    if not pedido or not pedido.get("prod"):
        return None
    col0 = "area" if pedido.get("eje") == _EJE_AREA else "grupo"
    bp = b[(b[col0] == pedido.get("l0")) & (b["sub"] == pedido.get("sub"))
           & (b["prod"] == pedido.get("prod"))]
    if pedido.get("claves"):
        bp = bp[bp["clave"].astype(str).isin(pedido["claves"])]
    salida = {"clave": pedido.get("clave"), "n": int(len(bp)), "filas": []}
    if bp.empty:
        return salida
    t = calculo(bp, por_linea=True).head(_MAX_LINEAS + 1)
    t = t.astype(object).where(t.notna(), None)
    salida["filas"] = [[(round(v, 4) if isinstance(v, float) else v)
                        for v in fila] for fila in t.to_numpy().tolist()]
    return salida


def _codigos_carta():
    """{plato en minúsculas: código} de la carta costeada, para el salto a
    Costo de Carta: el mismo de «Análisis de platos»."""
    try:
        from data import sello_datos
        from graficos.ventas_platos import _codigos_carta as _cc
        return _cc(sello_datos("cartacosteada.parquet"))
    except Exception:
        return {}


def _ir_a_carta(cod):
    """«Ver en Costo de Carta»: deja el plato elegido allá y pide el salto a
    Recetas, que necesita una corrida COMPLETA (ver `_ventas_mix`). Con un
    `graficos` viejo en Cloud (regla #357), no hace nada."""
    try:
        import navegacion
        from graficos.carta_costeada import _K_FOCO
        from navegacion_retorno import capturar_origen
        capturar_origen()
        st.session_state[_K_FOCO] = cod
        navegacion._ir_a_vista("Recetas", "rec_graf_tipo", "Carta costeada")
        st.session_state["_vt_mix_ir_carta"] = 1
    except (ImportError, AttributeError):
        return


def _ventas_mix(d, filtrar_cb=None):
    """«Mix de carta»: la venta por período partida por Grupo › Sub Grupo ›
    Producto. `d` es el df de la vista —sólo venta, un ítem una vez, con los
    chips de la franja—, y `filtrar_cb` lo que se le aplica al df del año
    pasado que la vista trae aparte de R2 (el `_filtrar_items` de
    `ventas.py`), para que los dos lados se comparen igual filtrados."""
    ss = st.session_state
    # La fecha cambió: recargar el parquet del rango nuevo. Igual que el
    # Resumen: el selector escribe la clave CANÓNICA del rango
    # (`categoria=None`), y el `d` que llegó es el del rango viejo. Y el
    # salto a Costo de Carta: otro reporte, una corrida completa.
    if ss.pop("vt_mix_fecha_flag", False) or ss.pop("_vt_mix_ir_carta", None):
        st.rerun(scope="app")

    with st.container(horizontal=True, gap="small", vertical_alignment="center",
                      key="vt_mix_cab"):
        st.markdown('<p class="chart-card-hdr">Mix de carta</p>',
                    unsafe_allow_html=True)
        with st.container(key="vt_mix_cab_fecha", width="content"):
            # «vt_mixf» y no «vt_mix»: el selector arma SUS keys con ese
            # prefijo (`_fila`, `_escala`, `_escala_panel`, `_panelf`).
            selector_fecha_tarjeta("vt_mixf", "vt_mix_fecha_flag",
                                   categoria=None)

    cols = columnas(d)
    if not (cols["fecha"] and cols["venta"] and cols["grupo"]):
        st.info("Faltan columnas (Fecha, Venta, Grupo) para el mix de carta.")
        return
    convenios = convenios_descuento.leer()
    b = base(d, cols, convenios=convenios)
    if b.empty:
        st.info("Sin ventas en el rango cargado.")
        return

    gran = ss.get(_K_GRAN)
    if gran not in _GRAN_OPCIONES:
        gran = ss[_K_GRAN] = _GRAN_DEFAULT
    b, claves, nota = periodos(b, gran)
    rango = (b["fecha"].min().date(), b["fecha"].max().date())

    # El período en que cambió la tasa de IGV (regla #590): la pieza marca
    # su columna cuando las celdas dicen el % de costo.
    j_de = {k: j for j, k in enumerate(claves)}
    dia_clave = dict(zip(b["fecha"].dt.normalize(), b["clave"]))
    igv_notas = [None] * len(claves)
    for dia, antes, despues in cambios_de_igv(b["fecha"], b["igv"], b["neto"]):
        j = j_de.get(dia_clave.get(dia))
        if j is not None:
            igv_notas[j] = nota_igv(dia, antes, despues)

    b_ap, ap_nombres = None, None
    if ss.get(_K_AP):
        with st.spinner("Trayendo el año pasado…"):
            b_ap, ap_nombres = _cargar_ano_pasado(claves, gran, rango,
                                                  filtrar_cb, convenios)
        if b_ap is None:
            b_ap = b.iloc[0:0].assign(j=0)

    def _al_gran():
        v = (ss.get(_K_PIEZA) or {}).get("gran")
        if v in _GRAN_OPCIONES:
            ss[_K_GRAN] = v

    def _al_ap():
        ss[_K_AP] = True

    def _al_lineas():
        v = (ss.get(_K_PIEZA) or {}).get("lineas")
        if isinstance(v, dict):
            ss[_K_LINEAS] = v

    def _a_la_carta():
        v = (ss.get(_K_PIEZA) or {}).get("carta")
        if v and v.get("cod"):
            _ir_a_carta(v["cod"])

    _PIEZA(key=_K_PIEZA,
           data=armar_mix(b, claves, gran, rango, b_ap, ap_nombres, nota,
                          lineas_de(b, ss.get(_K_LINEAS)),
                          hay_area=bool(cols.get("area")),
                          codigos=_codigos_carta(), igv_notas=igv_notas),
           on_gran_change=_al_gran, on_ap_change=_al_ap,
           on_lineas_change=_al_lineas, on_carta_change=_a_la_carta,
           width="stretch")
