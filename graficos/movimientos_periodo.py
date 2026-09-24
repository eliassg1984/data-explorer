"""graficos.movimientos_periodo - las tres tarjetas «por período» de
Movimientos: «Requerimientos por período», «Salidas por período» y
«Porcionamientos».

Nació el 2026-09-23 con la de requerimientos, a pedido: «poner en primera
vista una tarjeta como la que tengo para la vista compras por período […]
donde el gráfico de barra sea de los requerimientos. Y abajo pueda alternar
entre una vista resumida y detallado». Reemplazó a «Top productos ·
requerim.»: qué productos se piden más lo contesta el selector de Producto
de la tarjeta («Top 5/10/20 por valor») y la tabla de productos al pie de
«Por sub almacén». El mismo día llegó la de salidas: «hagamos algo así para
salidas, en reemplazo de la vista Tipo Descargo, debe mostrar el área del
cual se da la descarga» — el área la trae desde entonces la consulta de
`salidas.parquet` (`AREA`, de `vArea` por `MSUBSALIDA.tCodigoArea`) y el
tipo de descargo quedó como filtro y como columna del Detalle.

UNA SOLA TARJETA, TRES LADOS. Lo que las distingue —los nombres, el género
(«anulado» / «anulada»), las keys y el filtro de tipo de descargo— vive en
un `Lado` (`REQUERIMIENTOS`, `SALIDAS`, `PORCIONAMIENTOS`); todo lo demás es
el mismo código. Dos copias de mil líneas se habrían separado al primer
retoque.

EL TERCER LADO MIDE OTRA COSA (2026-09-24, a pedido: «agrega como una vista
"Porcionamientos", quizás pueda manejar el mismo diseño, estilo,
funcionalidad e interacción que tengo con mi vista por período»; aprobado
sobre un mockup con los datos reales). `porcionamientos.parquet` trae una
fila por CORTE con la cabecera del porcionamiento repetida en cada una, y la
barra no mide un valorizado sino la MERMA EN SOLES: lo que se perdió al
limpiar y porcionar. Por eso ese lado lleva `merma=True`, que en esta
tarjeta decide cinco cosas y nada más —cómo se leen las filas
(`lineas_porcionamientos`), el segundo renglón de la etiqueta (el % de
merma en vez de la cuenta), la KPI de lo porcionado, y las grillas del
Resumen y del Detalle, que listan porcionamientos y sus cortes—. El filtro
de tipo lo ocupa el Usuario que porcionó, y no hay Familia: la consulta no
la trae. Ver `arquitectura.md` regla #510.

ES LA GEMELA DE «COMPRAS POR PERÍODO» (graficos/compras/semanal.py), y a
propósito comparte sus cuentas en vez de copiarlas: el plan de las
etiquetas, el techo del eje, los nombres de los períodos, el calendario del
eje en Día y la variación contra la barra anterior salen de allá y de
`graficos/compras/_comun.py`. Si una de esas cambia, cambia en las tres
tarjetas — que es lo que se quiere: se leen igual. También mide lo que
aquélla (`alturas.SEMANAL_*`), con la misma zona de abajo: «Resumen», una
fila por barra, y «Detalle», los documentos del período en foco con las
líneas del elegido al costado (`tablas/movimientos_periodo.py`).

LO QUE LAS HACE DISTINTAS, medido contra los dos parquets el 2026-09-23
(`arquitectura.md` reglas #508 y #509):

  · Cada documento —requerimiento o salida— tiene UNA sola área, UN estado
    y UNA fecha de registro (los 20.086 requerimientos y las 5.579 salidas,
    sin excepción). El área es al documento lo que el proveedor a una
    compra, y por eso la barra se PARTE POR ÁREA (las tres mayores de la
    vista y «Resto»): quién pidió, o quién dio de baja. El color sigue al
    área, no a su puesto (`colores_area`), y es el MISMO en las dos
    tarjetas: las dos reciben el orden del histórico de requerimientos.
  · Los ANULADOS no suman en barras ni totales y se cuentan en la columna
    Estado, que escribe SÓLO la excepción (regla #239: el 97-98 % está
    procesado). Valen poco pero no cero: los requerimientos anulados de
    2026 suman S/ 15.868, el 0,9 % del año.
  · Los documentos SIN ÍTEMS —una línea sin producto, cantidad ni valor—
    no se cuentan: son el 15 % de los requerimientos del histórico (casi
    todos de GASTOS) y 91 salidas, 48 de ellas sin procesar, que todavía no
    movieron el kardex. Los nombra la fila de KPI y se LISTAN en el Detalle.
  · Sin granularidad «Por documento» (la de Compras): un mes son ~480
    requerimientos, o sea ~480 barras.

NO TIENEN FRAGMENT PROPIO, a diferencia de la de Compras: aquélla lo
necesita por su selector de fecha, que escala a una corrida completa (regla
#311). Éstas siguen a la fecha de la franja, así que corren dentro del
fragment de su sección (`seccion_perezosa`) y ningún control suyo escala.

Puntos de entrada: `tarjeta_requerimientos_periodo()`,
`tarjeta_salidas_periodo()` y `tarjeta_porcionamientos_periodo()`. Lo demás
son las piezas puras que las arman, y que `test_graficos.py` prueba sin
navegador.
"""

from dataclasses import dataclass
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cortes
from tema import GRIS_TEXTO, GRIS_TEXTO_SUAVE, PALETA_SERIES, TEXTO_PRINCIPAL
from graficos import alturas
from graficos.base import _compras_layout, _compras_truncar, scope_rerun
from graficos.compras._comun import (
    GAP_DRILL, _UNIDAD_GRAN, _clave_grilla, _first_point, _fmt_variacion,
    _hover_variacion, _nota_variacion, _periodo_serie, _variaciones,
)
# LAS CUENTAS DE LA GEMELA. Privadas de allá, y a propósito: estas tarjetas
# tienen que leerse igual que «Compras por período», y dos copias de «cuánto
# entra en la etiqueta de una barra» se separan al primer retoque.
from graficos.compras.semanal import (
    _AGRUPADO_GRAN, _ATENUADO, _ETQ_FUENTE, _ETQ_SEP, _LIENZO_PX,
    _TICK_AIRE, _TICK_PX_CARACTER, _anio_semana, _calendario_del_eje,
    _clave_del_clic, _con_alpha, _del_al, _plan_etiquetas, _rotulo_periodo,
    _techo_etiquetas,
)
from graficos.movimientos_comun import _rango_vigente
from tablas.movimientos_periodo import (
    ESTADO_OK, renderizar_cortes_mov, renderizar_documentos_mov,
    renderizar_lineas_mov, renderizar_periodos_mov, renderizar_periodos_porc,
    renderizar_porcionamientos_mov,
)
from utils import fmt_k


# ===========================================================================
# LOS DOS LADOS
# ===========================================================================

@dataclass(frozen=True)
class Lado:
    """Todo lo que distingue a una tarjeta de las otras dos.

    `k` es el prefijo de las keys de widget y de estado; `c`, el de los
    contenedores de los que cuelga el CSS (`_css`); `card`, la key de la
    tarjeta, que `estilos/_80_cards.py` saca del techo de alto. `fem` decide
    «anulado» o «anulada». `rotulo_tipo` es la dimensión extra del lado —el
    tipo de descargo de las salidas, el usuario de los porcionamientos—:
    vacío si no la hay; `tipo_todos` es su centinela y `ayuda_tipo`, su
    ayuda. `medida` y `top` nombran lo que mide la barra en las ayudas y en
    el «Top N por …» del selector de Producto. `con_familia` en False
    cuando el parquet no trae la familia (no se dibuja un filtro que no
    filtra nada). `merma` marca el lado de porcionamientos: ver el docstring
    del módulo y la regla #510."""
    k: str
    c: str
    card: str
    sing: str
    plur: str
    corto: str
    fem: bool
    titulo: str
    accion: str
    rotulo_tipo: str = ""
    tipo_todos: str = "Todos los tipos"
    ayuda_tipo: str = ""
    medida: str = "valorizado"
    top: str = "valor"
    rot_total: str = "Total de la vista"
    con_familia: bool = True
    merma: bool = False

    def cuenta(self, n):
        """«1 requerimiento», «3 salidas»."""
        return f"{n:,} " + (self.sing if n == 1 else self.plur)

    def anulados(self, n):
        """«1 anulado», «3 anuladas»."""
        base = "anulada" if self.fem else "anulado"
        return f"{n:,} {base}" + ("" if n == 1 else "s")

    def anulado_rotulo(self):
        """Lo que escribe la celda del valor de un anulado."""
        return "Anulada" if self.fem else "Anulado"


REQUERIMIENTOS = Lado(
    k="mov_per", c="mp", card="ajuste_graf_card_izq_mov_periodo",
    sing="requerimiento", plur="requerimientos", corto="req.", fem=False,
    titulo="Valorizado requerido", accion="pidió")

SALIDAS = Lado(
    k="mov_psal", c="mps", card="ajuste_graf_card_izq_mov_sal_periodo",
    sing="salida", plur="salidas", corto="sal.", fem=True,
    titulo="Valorizado dado de baja", accion="dio de baja",
    rotulo_tipo="Tipo de descargo",
    ayuda_tipo="Acota la tarjeta a un tipo de descargo (Bajas, Comida "
               "personal, Uso en el área…). Ofrece los del área elegida, "
               "por valorizado.")

PORCIONAMIENTOS = Lado(
    k="mov_pporc", c="mpp", card="ajuste_graf_card_izq_mov_porc_periodo",
    sing="porcionamiento", plur="porcionamientos", corto="porc.", fem=False,
    titulo="Merma de porcionamiento", accion="porcionó",
    rotulo_tipo="Usuario", tipo_todos="Todos los usuarios",
    ayuda_tipo="Acota la tarjeta a quien registró el porcionamiento. "
               "Ofrece los del área elegida, por merma.",
    medida="merma en soles", top="merma", rot_total="Merma de la vista",
    con_familia=False, merma=True)


# ===========================================================================
# CENTINELAS, OPCIONES Y ESTADOS
# ===========================================================================
# Los centinelas se comparan por igualdad contra lo que devuelve el widget,
# como en Compras: ninguna área, tipo, usuario, familia ni producto del
# parquet empieza con «Todas las», «Todos los» ni «Top ». El del tipo es de
# cada lado —«Todos los tipos», «Todos los usuarios»—: `Lado.tipo_todos`.
_AREA_TODAS = "Todas las áreas"
_FAM_TODAS = "Todas las familias"
_PROD_TODOS = "Todos los productos"
_TOPS = (5, 10, 20)
"""Los «Top N por valor» del selector de producto — los de Compras. Son lo
que reemplaza a la vista «Top productos · requerim.»: el top ya no es un
gráfico aparte sino un recorte de la tarjeta."""

_GRAN_OPCIONES = ("Día", "Semana", "Mes", "Año")
_GRAN_DEFAULT = "Semana"
"""Abre por semana, como Compras (2026-09-20). Sobre el rango de la franja
—por defecto el mes en curso— son cuatro o cinco barras."""

_GRAN_VARIACION = ("Día", "Semana", "Mes")
"""Dónde la etiqueta dice cuánto cambió contra la barra anterior: las de
Compras. Año no: con el rango de entrada es una barra sola."""

_MODO_RESUMEN = "Resumen"
_MODO_DETALLE = "Detalle"
_MODO_OPCIONES = (_MODO_RESUMEN, _MODO_DETALLE)
_MODO_DEFAULT = _MODO_RESUMEN
"""Abre en Resumen, al revés que Compras: el Resumen nunca está vacío y el
Detalle, sin una barra elegida, sí. Una tarjeta NUEVA puede elegir con qué
abre; la de Compras abre en Detalle porque era lo que hacía antes de tener
modos."""

_ANULADO = "ANULADO"
_GENERADO = "GENERADO"
"""Los estados de los dos parquets (`vEstadoDocumento`): PROCESADO, ANULADO
y GENERADO. GENERADO no tiene `FECHA PROCESADO` en ninguna línea de ninguno
de los dos, así que la tarjeta lo llama «sin procesar» — es lo único que se
sabe de él. En salidas, además, no tiene ítems: sus líneas salen del
kardex, y una salida sin procesar todavía no lo movió."""

_EST_ANULADO = "anulado"
_EST_SIN_PROC = "sin procesar"
_EST_SIN_ITEMS = "sin ítems"
"""Lo que viaja en `__estado` de cada fila del Detalle: la grilla colorea y
explica por estos tres valores, y los tres son neutros de género."""

_AREAS_TRAZA = 3
"""Áreas con color propio en la barra; el resto se suma en «Resto». Con
cuatro o menos en la vista van todas, sin «Resto»: sería un tramo de una
sola área con otro nombre. Medido en el último mes de requerimientos: Cocina
y Producción son el 84 % del valorizado y la tercera, Barra, el 5 %."""

_ALTO_FIG_SOLO = alturas.SEMANAL_SOLO - alturas.FRANJA_MODO_SEMANAL
_ALTO_TABLA = alturas.SEMANAL_TABLA - alturas.FRANJA_MODO_SEMANAL
"""La tarjeta mide lo que «Compras por período», con el mismo reparto: la
fila de modo la paga la figura cuando no hay tabla y la tabla cuando la hay
(regla #476)."""


def _oracion(txt, vacio=""):
    """«LIMPIEZA Y MANTENIMIENTO» → «Limpieza y mantenimiento».

    El ERP escribe áreas y familias en mayúsculas, y en una fila de KPI o un
    hover eso se lee a los gritos — el mismo criterio que
    `semanal._nombre_familia`."""
    t = str(txt or "").strip()
    return t[:1].upper() + t[1:].lower() if t else vacio


def _nombre_area(area):
    return _oracion(area, "Sin área")


# ===========================================================================
# LAS PIEZAS PURAS (las prueba `test_graficos.py`, sin Streamlit)
# ===========================================================================

def _texto(d, col, vacio=""):
    """La columna `col` como texto limpio, o `vacio` si falta o viene vacía."""
    if not col or col not in d.columns:
        return pd.Series(vacio, index=d.index, dtype=object)
    s = d[col].fillna("").astype(str).str.strip()
    return s.mask(s == "", vacio)


def lineas_documentos(d, *, fecha, doc, area, estado, fam, prod, cant, val,
                      punit=None, tipo=None):
    """Las líneas de un parquet de Movimientos con los nombres de la tarjeta.

    Una fila por línea: `fecha`, `doc` (el código), `area`, `tipo`, `estado`
    (en mayúsculas), `fam`, `prod`, `cant`, `punit`, `valor` y `vacio` —
    True en la línea SIN PRODUCTO, que es la forma de un documento sin ítems
    (regla #508). Los argumentos son los NOMBRES de columna del parquet, ya
    resueltos; el que falta cae a un valor neutro en vez de romper: sin
    código cada fila es su propio documento, sin estado todos cuentan como
    procesados, sin área todo es «Sin área».

    Sin precio unitario (salidas.parquet no lo trae) se DESPEJA de la línea:
    valor ÷ cantidad, y vacío donde la cantidad no es positiva — 106 líneas
    de salidas vienen con cantidad 0."""
    idx = d.index
    nan = pd.Series(float("nan"), index=idx)
    valor = pd.to_numeric(d[val], errors="coerce").fillna(0.0)
    cantidad = pd.to_numeric(d[cant], errors="coerce") if cant else nan
    if punit:
        precio = pd.to_numeric(d[punit], errors="coerce")
    else:
        precio = (valor / cantidad).where(cantidad > 0)
    out = pd.DataFrame({
        "fecha": pd.to_datetime(d[fecha], errors="coerce"),
        "doc": (_texto(d, doc) if doc and doc in d.columns
                else pd.Series(idx.astype(str), index=idx)),
        "area": _texto(d, area, "Sin área"),
        "tipo": _texto(d, tipo),
        "estado": _texto(d, estado, "PROCESADO").str.upper(),
        "fam": _texto(d, fam),
        "prod": _texto(d, prod),
        "cant": cantidad,
        "punit": precio,
        "valor": valor,
    })
    out["vacio"] = out["prod"] == ""
    return out.dropna(subset=["fecha"])


_UNIDAD_CORTA = {"KILOS": "kg", "KILO": "kg", "KG": "kg", "GRAMOS": "g",
                 "UND": "und", "UNIDAD": "und", "UNIDADES": "und",
                 "LITROS": "L", "LITRO": "L", "LT": "L", "PORCION": "porc."}
"""Cómo se escribe la unidad al lado de una cantidad. El Almacén la da en
palabras y en mayúsculas («KILOS», «UND»); en una celda angosta, «21 kg»."""


def unidad_corta(u):
    """«KILOS» → «kg». La que no está en la tabla va en minúsculas."""
    t = str(u or "").strip()
    return _UNIDAD_CORTA.get(t.upper(), t.lower())


def fmt_cant(v):
    """«21», «12.175», «0.675»: la cantidad con los decimales que tiene
    (hasta tres), como la escribe la grilla (`_JS_CANT_MOV`)."""
    if v is None or pd.isna(v):
        return ""
    return f"{v:,.3f}".rstrip("0").rstrip(".")


def lineas_porcionamientos(d, *, fecha, doc, area, tipo, prod, unid, cant,
                           merma, fin, cant_fin, unid_fin, pprom, peso):
    """`(base, cortes)`: porcionamientos.parquet con los nombres de la tarjeta.

    EL GRANO ES LA TRAMPA (regla #510). El parquet trae una fila por CORTE
    —cada producto que salió del porcionamiento— con la cabecera REPETIDA en
    cada una: la cantidad, la merma, el área, el usuario y el producto
    inicial. Sumar la merma por fila la multiplica por los cortes; medido
    sobre el histórico, el lomo fino da 5.734 kg contra 1.342 reales (x4,3).
    Así que `base` tiene UNA fila por porcionamiento —la cabecera se toma
    una vez— y la forma de `lineas_documentos`, para que el resto de la
    tarjeta no distinga el lado: `doc` es el código, `tipo` el usuario,
    `valor` la MERMA EN SOLES, `estado` siempre PROCESADO y `vacio` siempre
    False (la consulta trae sólo los procesados, estado 02). Suma cuatro
    columnas propias: `costo` (lo porcionado, en soles), `merma_cant` (la
    merma en la unidad del producto inicial), `unid` y `cortes`.

    EL COSTO SALE DE LOS CORTES: `cant_fin × pprom`, sumado. El Almacén le
    carga a cada corte su parte del costo del producto inicial —merma
    incluida—, así que esa suma ES lo que costó lo que entró. Medido contra
    lo pagado en compras.parquet en los 60 días previos, sobre 2.666
    porcionamientos del último año: mediana 1,00 y el 82 % dentro de ±10 %.
    La merma en soles es la parte de ese costo que se fue: `costo × merma ÷
    cant`. Un porcionamiento sin cortes cuesta 0 y no pierde nada, pero
    cuenta.

    `cortes` son las filas del parquet con producto final, una por corte:
    `doc`, `fin`, `cant`, `unid` (la del corte), `pprom`, `peso` (en la
    unidad del producto INICIAL: es la parte de lo que entró que fue a ese
    corte) y `valor` (`cant × pprom`)."""
    idx = d.index
    nan = pd.Series(float("nan"), index=idx)

    def _num(col):
        return pd.to_numeric(d[col], errors="coerce") if col else nan

    t = pd.DataFrame({
        "doc": (_texto(d, doc) if doc and doc in d.columns
                else pd.Series(idx.astype(str), index=idx)),
        "fecha": pd.to_datetime(d[fecha], errors="coerce"),
        "area": _texto(d, area, "Sin área"),
        "tipo": _texto(d, tipo),
        "prod": _texto(d, prod),
        "unid": _texto(d, unid),
        "cant": _num(cant),
        "merma_cant": _num(merma),
        "fin": _texto(d, fin),
        "cant_fin": _num(cant_fin),
        "unid_fin": _texto(d, unid_fin),
        "pprom": _num(pprom),
        "peso": _num(peso),
    }).dropna(subset=["fecha"])
    t["valor_fin"] = (t["cant_fin"] * t["pprom"]).fillna(0.0)
    t["con_fin"] = t["fin"] != ""

    # La cabecera, UNA vez por porcionamiento; el costo y los cortes, sumados.
    g = t.groupby("doc", sort=False)
    base = pd.DataFrame({
        "fecha": g["fecha"].first(),
        "area": g["area"].first(),
        "tipo": g["tipo"].first(),
        "prod": g["prod"].first(),
        "unid": g["unid"].first(),
        "cant": g["cant"].first(),
        "merma_cant": g["merma_cant"].first(),
        "costo": g["valor_fin"].sum(),
        "cortes": g["con_fin"].sum().astype(int),
    }).rename_axis("doc").reset_index()
    positiva = base["cant"] > 0
    base["punit"] = (base["costo"] / base["cant"]).where(positiva)
    base["valor"] = ((base["costo"] * base["merma_cant"] / base["cant"])
                     .where(positiva).fillna(0.0))
    base["estado"] = "PROCESADO"
    base["fam"] = ""
    base["vacio"] = False

    cortes = t.loc[t["con_fin"], ["doc", "fin", "cant_fin", "unid_fin",
                                  "pprom", "peso", "valor_fin"]]
    cortes = cortes.rename(columns={"cant_fin": "cant", "unid_fin": "unid",
                                    "valor_fin": "valor"})
    return base, cortes.reset_index(drop=True)


def orden_areas(df, col_area, col_val):
    """Las áreas de `df` de mayor a menor valorizado: el orden ESTABLE con
    el que `colores_area` reparte los colores. Se le pasa el parquet
    entero de REQUERIMIENTOS, no el rango, y a las DOS tarjetas: el color de
    Cocina no puede cambiar porque un mes Producción pidió más, ni ser otro
    en la tarjeta de salidas."""
    if (df is None or not col_area or not col_val
            or col_area not in df.columns or col_val not in df.columns):
        return []
    t = pd.DataFrame({
        "area": df[col_area].fillna("").astype(str).str.strip(),
        "valor": pd.to_numeric(df[col_val], errors="coerce").fillna(0.0),
    })
    return (t.groupby("area")["valor"].sum().sort_values(ascending=False)
             .index.tolist())


def colores_area(orden, nombres):
    """`{área: color}` para las áreas de `nombres`, con el color que les
    toca por su puesto en `orden` —el histórico— y no por su puesto en la
    vista: filtrar no puede repintar (el color sigue a la entidad). Si dos
    de las que se dibujan juntas caen en el mismo color de la paleta, la
    segunda toma el siguiente libre."""
    ix = {a: i for i, a in enumerate(orden)}
    usados, salida = set(), {}
    for a in nombres:
        i = ix.get(a, len(orden) + len(salida))
        c = PALETA_SERIES[i % len(PALETA_SERIES)]
        while c in usados and len(usados) < len(PALETA_SERIES):
            i += 1
            c = PALETA_SERIES[i % len(PALETA_SERIES)]
        usados.add(c)
        salida[a] = c
    return salida


def _validas(bl):
    """Las líneas que SUMAN: con producto y de un documento no anulado."""
    return bl[~bl["vacio"] & (bl["estado"] != _ANULADO)]


def resumen_por_periodo(bl):
    """Una fila por período —la columna `clave` de `bl`—, en orden.

    `bl` son TODAS las líneas del recorte, las vacías incluidas. Columnas,
    por NOMBRE: `valor`, `lineas`, `docs` y `areas` de las líneas VÁLIDAS
    (`_validas`), y `anulados` y `sin_procesar`, que se cuentan en
    documentos y sobre todas: un anulado sin ítems también es un anulado.
    Un período que sólo tiene documentos que no suman no tiene barra y no
    sale; sus documentos siguen en el total de la fila de KPI.

    Las líneas de porcionamientos (`lineas_porcionamientos`) traen además
    `costo` y `cortes`, y salen sumadas con esos mismos nombres: lo
    porcionado y los cortes del período (regla #510)."""
    dv = _validas(bl)
    g = (dv.groupby("clave")
           .agg(valor=("valor", "sum"), lineas=("valor", "size"),
                docs=("doc", "nunique"), areas=("area", "nunique"))
           .sort_index())
    for extra in ("costo", "cortes"):
        if extra in dv.columns:
            g[extra] = dv.groupby("clave")[extra].sum().reindex(g.index)
    an = bl[bl["estado"] == _ANULADO].groupby("clave")["doc"].nunique()
    sp = bl[bl["estado"] == _GENERADO].groupby("clave")["doc"].nunique()
    g["anulados"] = an.reindex(g.index).fillna(0).astype(int)
    g["sin_procesar"] = sp.reindex(g.index).fillna(0).astype(int)
    return g


def no_suman(bl):
    """`(anulados, sin procesar, sin ítems)`: los documentos del recorte que
    no suman en la barra, contados una sola vez cada uno.

    Anulado manda sobre todo lo demás; «sin procesar» es el GENERADO que
    además no tiene ítems (el que sí los tiene SUMA, y lo dice la columna
    Estado); «sin ítems» es el resto de los documentos vacíos."""
    por_doc = (bl.groupby("doc")
                 .agg(estado=("estado", "first"), vacio=("vacio", "all")))
    anul = por_doc["estado"] == _ANULADO
    sin_proc = ~anul & por_doc["vacio"] & (por_doc["estado"] == _GENERADO)
    sin_items = ~anul & por_doc["vacio"] & (por_doc["estado"] != _GENERADO)
    return int(anul.sum()), int(sin_proc.sum()), int(sin_items.sum())


def trazas_por_area(dv, ord_claves, orden):
    """`[(nombre, color, [valor por período]), …]`: los tramos de la barra.

    Las `_AREAS_TRAZA` mayores de la VISTA, de abajo hacia arriba, y
    «Resto» con lo que falta para el total de cada período — el resto no se
    vuelve a sumar por área, así la barra cierra por construcción. Con
    cuatro áreas o menos van todas y no hay «Resto». Un área que suma 0 no
    tiene tramo (seguiría contando en «Áreas»)."""
    tot = dv.groupby("area")["valor"].sum().sort_values(ascending=False)
    tot = tot[tot > 0]
    if tot.empty:
        return []
    por = (dv.groupby(["clave", "area"])["valor"].sum()
             .unstack("area").reindex(ord_claves).fillna(0.0))
    nombres = (list(tot.index) if len(tot) <= _AREAS_TRAZA + 1
               else list(tot.index[:_AREAS_TRAZA]))
    col = colores_area(orden, nombres)
    trazas = [(a, col[a], [float(v) for v in por[a]]) for a in nombres]
    if len(nombres) < len(tot):
        totales = dv.groupby("clave")["valor"].sum().reindex(ord_claves)
        acum = por[nombres].sum(axis=1)
        trazas.append(("Resto", GRIS_TEXTO_SUAVE,
                       [max(float(t) - float(a), 0.0)
                        for t, a in zip(totales.fillna(0.0), acum)]))
    return trazas


def _texto_estado(anulados, sin_procesar, lado):
    """`(texto, clase)` de la columna Estado: sólo la excepción (#239)."""
    partes = []
    if anulados:
        partes.append(lado.anulados(anulados))
    if sin_procesar:
        partes.append(f"{sin_procesar:,} sin procesar")
    if not partes:
        return ESTADO_OK, "ok"
    return " · ".join(partes), ("sinp" if sin_procesar else "anul")


def _etiqueta_arriba(trazas, textos):
    """El texto de cada TRAMO, con la etiqueta del total sólo en el de más
    arriba que tenga valor: Plotly pone el `outside` de una barra apilada
    sólo en la que termina la pila (lo mismo que resuelve
    `semanal._etiqueta_en_la_punta` para sus tramos)."""
    salida = [[None] * len(textos) for _ in trazas]
    for j, txt in enumerate(textos):
        for i in range(len(trazas) - 1, -1, -1):
            if trazas[i][2][j]:
                salida[i][j] = txt
                break
    return salida


def _renglones(total, n_doc, var, gran, lado, segundo=None):
    """Los renglones de la etiqueta de UNA barra como `(plano, html)`: el
    total, los documentos y la variación — la etiqueta de Compras con
    «req.» o «sal.» donde aquélla dice «docs». `segundo` reemplaza al
    renglón de los documentos: en porcionamientos es el % de merma (#510),
    porque una semana con más porcionamientos pierde más soles sin que se
    trabaje peor, y el % separa las dos cosas."""
    if not total:
        return []
    salida = [(total, total)]
    _r = segundo if segundo is not None else f"{n_doc:,} {lado.corto}"
    salida.append((_r, f"<span style='color:{GRIS_TEXTO}'>{_r}</span>"))
    if gran in _GRAN_VARIACION and var:
        estado, pct, _ = var
        if estado == "ok":
            _t, _c = _fmt_variacion(pct)
            salida.append((_t, f"<span style='color:{_c}'><b>{_t}</b></span>"))
        elif estado == "parcial":
            salida.append(("parcial",
                           f"<span style='color:{GRIS_TEXTO}'><i>parcial</i>"
                           "</span>"))
    return salida


def vista_periodos(bl, gran, rango=None, orden=(), lado=REQUERIMIENTOS):
    """Todo lo que la tarjeta dibuja de un recorte, sin dibujar nada.

    `bl` son TODAS las líneas del recorte (las vacías incluidas: cuentan en
    Estado) con su `clave` de período; `rango` es `(primer día, último día)`
    como `date`, para saber qué período quedó cortado; `orden`, el de
    `orden_areas`. Devuelve un dict con los períodos en orden (`claves`),
    sus rótulos (`eje`, `hover`, `fila`), el resumen (`res`), los tramos
    (`trazas`), las variaciones y sus notas. Vacío (`claves == []`) si no
    hay nada válido que dibujar."""
    res = resumen_por_periodo(bl)
    claves = res.index.tolist()
    v = {"claves": claves, "res": res, "gran": gran, "rango": rango,
         "lado": lado}
    if not claves:
        return v
    rot = {c: _rotulo_periodo(c, gran) for c in claves}
    if gran == "Día":
        dias = [pd.Timestamp(c).date() for c in claves]
        fer = set()
        for _a in {d.year for d in dias}:
            fer |= cortes.feriados_peru(_a)
        hover = [f"{cortes.DIAS_ABR_ES[d.weekday()].capitalize()} "
                 f"{d:%d/%m/%Y}" + (" · feriado" if d in fer else "")
                 for d in dias]
        corto = [f"{cortes.DIAS_ABR_ES[d.weekday()].capitalize()} {d:%d/%m}"
                 for d in dias]
        fila = hover
    else:
        dias = None
        hover = [rot[c][1] for c in claves]
        corto = [rot[c][0] for c in claves]
        if gran == "Semana":
            fila = [f"{rot[c][0]} {_anio_semana(c)}" for c in claves]
        else:
            fila = list(hover)
    tot = [float(x) for x in res["valor"]]
    variaciones = (_variaciones(claves, tot, gran, rango)
                   if gran in _GRAN_VARIACION else [None] * len(claves))

    def _ant(var):
        return corto[var[2]] if var and var[2] is not None else ""

    dv = _validas(bl)
    v.update(
        eje=[rot[c][0] for c in claves], hover=hover, corto=corto, fila=fila,
        dias=dias, tot=tot, variaciones=variaciones,
        var_hover=[_hover_variacion(_v, gran, c, _ant(_v), rango,
                                    sustantivo=lado.plur)
                   for c, _v in zip(claves, variaciones)],
        var_nota=[_nota_variacion(_v, gran, c, _ant(_v), rango,
                                  sustantivo=lado.plur)
                  for c, _v in zip(claves, variaciones)],
        trazas=trazas_por_area(dv, claves, orden),
    )
    # Qué áreas hay en cada período, de mayor a menor: el tooltip de la
    # columna «Áreas» del Resumen.
    _pa = (dv.groupby(["clave", "area"])["valor"].sum().reset_index()
             .sort_values(["clave", "valor"], ascending=[True, False]))
    _nombres = _pa.groupby("clave")["area"].agg(
        lambda s: ", ".join(_nombre_area(a) for a in s))
    v["areas_txt"] = [_nombres.get(c, "") for c in claves]
    return v


def figura_periodos(v, alto_fig, titulo="", foco=None):
    """La figura de la tarjeta a partir de `vista_periodos`.

    `foco` es la clave del período en foco (o None): lo demás se atenúa
    por COLOR, no con `marker.opacity` — esa lista sobre barras con texto
    `outside` crashea Plotly en el navegador (regla #476). El eje es
    LINEAL con los rótulos a mano, como el de Compras: el calendario de
    Día y la traducción del clic hablan en índices."""
    claves, gran, lado = v["claves"], v["gran"], v["lado"]
    n = len(claves)
    res = v["res"]
    fig = go.Figure()
    if not n:
        return fig
    trazas = v["trazas"] or [("Valorizado", PALETA_SERIES[0], v["tot"])]
    docs = res["docs"].astype(int).tolist()

    # ── La etiqueta de cada barra: lo que ENTRA (`_plan_etiquetas`) ──────
    # En porcionamientos el segundo renglón es el % de merma del período
    # (sobre lo porcionado, `costo`) y no la cuenta: regla #510.
    costos = ([float(c) for c in res["costo"]] if lado.merma
              else [None] * n)
    segundos = [(f"{t / c:.0%} merma" if (lado.merma and c) else None)
                for t, c in zip(v["tot"], costos)]
    reng = [_renglones(fmt_k(t) if t else None, r, var, gran, lado, s)
            for t, r, var, s in zip(v["tot"], docs, v["variaciones"],
                                    segundos)]
    plan, k_etq, alto_etq = _plan_etiquetas(
        n, [[p for p, _ in r] for r in reng], alto_fig)
    textos = [None] * n
    if plan:
        sep = _ETQ_SEP if plan == "unida" else "<br>"
        textos = [(sep.join(h for _, h in r[:k_etq]) or None) for r in reng]
    txt_tr = (_etiqueta_arriba(trazas, textos) if plan
              else [[None] * n for _ in trazas])
    estilo = dict(textposition="outside", cliponaxis=False,
                  constraintext="none",
                  textangle=-90 if plan in ("girada", "unida") else 0,
                  textfont=dict(size=_ETQ_FUENTE, color=TEXTO_PRINCIPAL))

    # ── El hover: el período, el tramo, el total y lo que lo forma ───────
    if lado.merma:
        det = [f"<br>{r:,} {lado.corto} · {int(ct):,} corte{'' if ct == 1 else 's'}"
               f" · {int(a):,} área{'' if a == 1 else 's'}"
               f"<br>{(t / c if c else 0):.1%} de merma sobre S/ {c:,.2f}"
               " porcionados"
               for r, ct, a, t, c in zip(docs, res["cortes"], res["areas"],
                                         v["tot"], costos)]
    else:
        det = [f"<br>{r:,} {lado.corto} · {int(ln):,} línea{'' if ln == 1 else 's'}"
               f" · {int(a):,} área{'' if a == 1 else 's'}"
               for r, ln, a in zip(docs, res["lineas"], res["areas"])]
    anul = [(f"<br><i>{lado.anulados(int(x))} aparte</i>" if x else "")
            for x in res["anulados"]]
    xs = list(range(n))
    for i, (nombre, color, vals) in enumerate(trazas):
        rot = nombre if nombre == "Resto" else _nombre_area(nombre)
        if foco is not None and foco in claves:
            color = [color if c == foco else _con_alpha(color, _ATENUADO)
                     for c in claves]
        fig.add_bar(
            x=xs, y=vals, name=rot, marker=dict(color=color),
            customdata=list(zip(v["hover"], [rot] * n, v["tot"], det,
                                v["var_hover"], anul)),
            hovertemplate=("%{customdata[0]}"
                           "<br><b>%{customdata[1]}</b>: S/ %{y:,.2f}"
                           "<br>Total: S/ %{customdata[2]:,.2f}"
                           "%{customdata[3]}%{customdata[4]}%{customdata[5]}"
                           "<extra></extra>"),
        )
        if plan:
            fig.data[-1].update(text=txt_tr[i], **estilo)
    if len(trazas) > 1:
        fig.update_layout(barmode="stack")

    _compras_layout(fig, alto=alto_fig)
    if plan:
        _y = _techo_etiquetas(max(v["tot"]), min(0.0, min(v["tot"])),
                              alto_fig, alto_etq)
        if _y:
            fig.update_yaxes(range=_y)
    # SIN LEYENDA, a diferencia de Compras: la fila de KPI de la cabecera
    # ya nombra cada tramo con su color, su monto y su % (`_html_kpi`), así
    # que es la leyenda dicha con números. La de Plotly, además, se montaba
    # sobre los rótulos del eje con la figura en COMPACTO (medido: los
    # rótulos de dos renglones de Semana y de Día la alcanzan). Las cuentas
    # de las etiquetas siguen suponiendo la leyenda (`semanal._LEYENDA_Y`),
    # o sea que calculan con un área de trazo MENOR que la real: sobra aire,
    # nada se pisa.
    fig.update_layout(title=titulo, hovermode="closest", showlegend=False)

    # ── El eje: el calendario en Día, un rótulo cada tanto en el resto ───
    ticks = (_calendario_del_eje(fig, v["dias"], sep="semana")
             if gran == "Día" else None)
    if ticks is None:
        eje = v["eje"]
        largo = max((len(t) for t in eje), default=1)
        caben = max(1, int(_LIENZO_PX // (largo * _TICK_PX_CARACTER
                                          + _TICK_AIRE)))
        paso = max(1, -(-n // caben))
        tv = list(range(0, n, paso))
        tt = [eje[i] for i in tv]
        if gran == "Semana":
            ult = None
            for j, i in enumerate(tv):
                a = _anio_semana(claves[i])
                if a != ult:
                    tt[j] += f"<br>{a}"
                    ult = a
        ticks = (tv, tt)
    fig.update_xaxes(type="linear", tickmode="array", tickvals=ticks[0],
                     ticktext=ticks[1], range=[-0.5, n - 0.5])
    return fig


def tabla_resumen(v, foco=None):
    """`(filas, total)` de la grilla del Resumen: una fila por barra."""
    res, gran, lado = v["res"], v["gran"], v["lado"]
    tot_vista = float(sum(v["tot"])) or 0.0
    estados = [_texto_estado(int(a), int(s), lado)
               for a, s in zip(res["anulados"], res["sin_procesar"])]
    filas = pd.DataFrame({
        "periodo": v["fila"],
        "docs": res["docs"].astype(int).tolist(),
        "lineas": res["lineas"].astype(int).tolist(),
        "areas": res["areas"].astype(int).tolist(),
        "valor": [round(t, 2) for t in v["tot"]],
        "parte": [(t / tot_vista if tot_vista else 0.0) for t in v["tot"]],
        "variacion": [(_v[1] if _v and _v[0] == "ok" else None)
                      for _v in v["variaciones"]],
        "estado": [e for e, _ in estados],
        "__vtxt": [("parcial" if _v and _v[0] == "parcial" else "—")
                   for _v in v["variaciones"]],
        "__nota": v["var_nota"],
        "__anota": v["areas_txt"],
        "__eclase": [c for _, c in estados],
        "__clave": v["claves"],
        "__sel": [c == foco for c in v["claves"]],
    })
    n = len(v["claves"])
    uni = _UNIDAD_GRAN[gran][0 if n == 1 else 1]
    e_tot, c_tot = _texto_estado(int(res["anulados"].sum()),
                                 int(res["sin_procesar"].sum()), lado)
    total = {
        "periodo": f"Total · {n:,} {uni}",
        "docs": f"{int(res['docs'].sum()):,}",
        "lineas": f"{int(res['lineas'].sum()):,}",
        "areas": "", "valor": f"S/ {tot_vista:,.2f}", "parte": "100%",
        "variacion": "", "estado": e_tot, "__eclase": c_tot,
    }
    return filas, total


def tabla_documentos(amb, sel, lado=REQUERIMIENTOS):
    """`(filas, total)` de la lista de documentos del período en foco.

    `amb` son TODAS las líneas del período. Se LISTAN todos sus documentos
    —los anulados, los sin procesar y los sin ítems también: quien abre un
    período con «3 anuladas» en el Resumen tiene que poder ver cuáles
    fueron—, pero la fila TOTAL suma sólo los que suman, que es la misma
    cuenta que la barra."""
    docs = (amb.assign(_con=~amb["vacio"])
               .groupby("doc", as_index=False)
               .agg(fecha=("fecha", "min"), area=("area", "first"),
                    tipo=("tipo", "first"), estado=("estado", "first"),
                    lineas=("_con", "sum"), valor=("valor", "sum")))
    vacio = docs["lineas"] == 0
    anul = docs["estado"] == _ANULADO
    sin_proc = ~anul & (docs["estado"] == _GENERADO)
    estado = pd.Series("", index=docs.index, dtype=object)
    estado[vacio & ~anul] = _EST_SIN_ITEMS
    estado[sin_proc] = _EST_SIN_PROC
    estado[anul] = _EST_ANULADO
    # Lo que la celda del valor escribe EN LUGAR del monto: el anulado y el
    # documento que no tiene ítems (con o sin procesar). El que tiene ítems
    # y está sin procesar muestra su valor, en ámbar: sí suma.
    rotulo = pd.Series("", index=docs.index, dtype=object)
    rotulo[vacio & ~anul] = "Sin ítems"
    rotulo[vacio & sin_proc] = "Sin procesar"
    rotulo[anul] = lado.anulado_rotulo()
    filas = pd.DataFrame({
        "registro": docs["fecha"].dt.strftime("%Y-%m-%d %H:%M"),
        "codigo": docs["doc"],
        "area": docs["area"].map(_nombre_area),
        "tipo": docs["tipo"],
        "lineas": docs["lineas"].astype(int),
        "valor": docs["valor"].astype(float).round(2),
        "__estado": estado,
        "__elbl": rotulo,
        "__doc": docs["doc"],
        "__sel": docs["doc"] == sel,
    })
    suman = ~anul & ~vacio
    n_val, n_fuera = int(suman.sum()), int((~suman).sum())
    # El total sale de los valores SIN redondear, como la barra y el
    # Resumen: sumar los de la columna (redondeados a céntimos de a uno)
    # daba 6 céntimos de diferencia con la fila del Resumen en una semana
    # de 150 requerimientos — dos números que tienen que ser el mismo.
    total = {
        "registro": "Total",
        "codigo": f"{n_val:,} {lado.corto}",
        "area": f"+{n_fuera:,} no suman" if n_fuera else "",
        "tipo": "",
        "lineas": f"{int(filas.loc[suman, 'lineas'].sum()):,}",
        "valor": f"S/ {docs.loc[suman, 'valor'].sum():,.2f}",
    }
    return filas, total


def tabla_resumen_porc(v, foco=None):
    """`(filas, total)` del Resumen de PORCIONAMIENTOS: una fila por barra.

    La de `tabla_resumen` con lo que este lado mide: los porcionamientos,
    sus cortes, lo porcionado (`costo`, en soles), la merma (la barra) y su
    % sobre lo porcionado. Sin Estado: la consulta trae sólo procesados, y
    una columna que diría «✓» en todas las filas no dice nada (#239)."""
    res, gran = v["res"], v["gran"]
    tot_vista = float(sum(v["tot"])) or 0.0
    costos = [float(c) for c in res["costo"]]
    filas = pd.DataFrame({
        "periodo": v["fila"],
        "docs": res["docs"].astype(int).tolist(),
        "cortes": res["cortes"].astype(int).tolist(),
        "areas": res["areas"].astype(int).tolist(),
        "costo": [round(c, 2) for c in costos],
        "valor": [round(t, 2) for t in v["tot"]],
        "pm": [(t / c if c else None) for t, c in zip(v["tot"], costos)],
        "parte": [(t / tot_vista if tot_vista else 0.0) for t in v["tot"]],
        "variacion": [(_v[1] if _v and _v[0] == "ok" else None)
                      for _v in v["variaciones"]],
        "__vtxt": [("parcial" if _v and _v[0] == "parcial" else "—")
                   for _v in v["variaciones"]],
        "__nota": v["var_nota"],
        "__anota": v["areas_txt"],
        "__clave": v["claves"],
        "__sel": [c == foco for c in v["claves"]],
    })
    n = len(v["claves"])
    uni = _UNIDAD_GRAN[gran][0 if n == 1 else 1]
    costo_vista = sum(costos)
    total = {
        "periodo": f"Total · {n:,} {uni}",
        "docs": f"{int(res['docs'].sum()):,}",
        "cortes": f"{int(res['cortes'].sum()):,}",
        "areas": "", "costo": f"S/ {costo_vista:,.2f}",
        "valor": f"S/ {tot_vista:,.2f}",
        "pm": f"{tot_vista / costo_vista:.1%}" if costo_vista else "",
        "parte": "100%", "variacion": "",
    }
    return filas, total


def tabla_porcionamientos(amb, sel):
    """`(filas, total)` de la lista de porcionamientos del período en foco.

    `amb` son las filas de `lineas_porcionamientos` del período —una por
    porcionamiento—. La cantidad viaja cruda y su unidad aparte (`__unid`),
    para que la columna se ordene por número y la celda diga «21 kg». El %
    del total es merma ÷ lo porcionado en soles, que es el mismo de la
    etiqueta de la barra."""
    positiva = amb["cant"] > 0
    filas = pd.DataFrame({
        "registro": amb["fecha"].dt.strftime("%Y-%m-%d %H:%M"),
        "prod": amb["prod"],
        "area": amb["area"].map(_nombre_area),
        "tipo": amb["tipo"],
        "cant": amb["cant"].astype(float).round(3),
        "pm": (amb["merma_cant"] / amb["cant"]).where(positiva),
        "valor": amb["valor"].astype(float).round(2),
        "__unid": amb["unid"].map(unidad_corta),
        "__doc": amb["doc"],
        "__sel": amb["doc"] == sel,
    })
    costo, merma = float(amb["costo"].sum()), float(amb["valor"].sum())
    total = {
        "registro": "Total", "prod": f"{len(amb):,} porc.", "area": "",
        "tipo": "", "cant": "",
        "pm": f"{merma / costo:.1%}" if costo else "",
        "valor": f"S/ {merma:,.2f}",
    }
    return filas, total


def tabla_cortes(cortes, unid_inicial):
    """`(filas, total)` de los cortes de UN porcionamiento, de mayor a menor
    valor. `peso` es la parte de lo que entró que fue a cada corte, en la
    unidad del producto inicial (`unid_inicial`): sumado, es lo que se
    aprovechó. `valor` suma el costo de lo que entró, merma incluida."""
    c = cortes.sort_values("valor", ascending=False)
    u_ini = unidad_corta(unid_inicial)
    filas = pd.DataFrame({
        "fin": c["fin"],
        "cant": c["cant"].astype(float).round(3),
        "peso": c["peso"].astype(float).round(3),
        "pprom": c["pprom"].astype(float).round(4),
        "valor": c["valor"].astype(float).round(2),
        "__unid": c["unid"].map(unidad_corta),
        "__unid_ini": u_ini,
    })
    n = len(filas)
    peso = float(c["peso"].sum())
    total = {
        "fin": f"Total · {n} corte" + ("" if n == 1 else "s"),
        "cant": "", "pprom": "",
        "peso": f"{fmt_cant(peso)} {u_ini}".strip(),
        "valor": f"S/ {float(c['valor'].sum()):,.2f}",
    }
    return filas, total


def _mayor_valido(amb):
    """El código del documento válido de mayor valor del período: el que la
    tabla de líneas muestra si nadie eligió otro (el criterio de Compras: la
    de al lado nunca está vacía)."""
    v = _validas(amb)
    if v.empty:
        v = amb
    s = v.groupby("doc")["valor"].sum().sort_values(ascending=False)
    return s.index[0] if len(s) else None


def _html_kpi(total, n_docs, trazas, tot_area, nota, lado, costo=None,
              costo_area=None):
    """La fila de KPI: el total de la vista y una tarjeta por TRAMO de la
    barra, con el color del tramo. Es también la leyenda del gráfico, dicha
    con números. `nota` es `(corto, largo)` de lo que no suma, o None.

    En porcionamientos (#510) llegan además `costo` —lo porcionado en la
    vista, que cierra la fila con su % de merma— y `costo_area`, `{área:
    lo porcionado}`, para que el tooltip de cada área diga cuánto pierde de
    lo que ELLA porciona: la parte de la merma total y la propia no son lo
    mismo (Producción concentra la merma porque porciona casi todo)."""
    def _t(rot, val, sub, clase="", tip="", color=None):
        sw = (f'<span class="mp-kpi-sw" style="background:{color}"></span>'
              if color else "")
        return (f'<div class="mp-kpi {clase}" title="{escape(tip or rot)}">'
                f'<span class="mp-kpi-rot">{sw}{escape(rot)}</span>'
                f'<span class="mp-kpi-val">{escape(val)}'
                f'<span class="mp-kpi-sub">{escape(sub)}</span></span></div>')

    _n = lado.cuenta(n_docs)
    partes = [_t(lado.rot_total, fmt_k(total), _n, "mp-kpi-total",
                 f"{lado.rot_total}: S/ {total:,.2f} · {_n}")]
    if len(trazas) > 1:
        for nombre, color, vals in trazas:
            v = float(sum(vals))
            p = v / total if total else 0.0
            propio = ""
            if nombre == "Resto":
                n_resto = len(tot_area) - (len(trazas) - 1)
                rot = f"{n_resto} área" + ("" if n_resto == 1 else "s") + " más"
            else:
                rot = _nombre_area(nombre)
                c_area = (costo_area or {}).get(nombre)
                if c_area:
                    propio = (f" · su merma es el {v / c_area:.1%} de lo que "
                              "porcionó")
            partes.append(_t(rot, fmt_k(v), f"{p:.0%}",
                             tip=f"{rot}: S/ {v:,.2f} · {p:.1%}{propio}",
                             color=color))
    if costo is not None:
        _pm = f"{total / costo:.1%}" if costo else "—"
        partes.append(_t("Porcionado", fmt_k(costo), f"{_pm} merma",
                         "mp-kpi-porc",
                         f"Costo de lo porcionado: S/ {costo:,.2f} · la "
                         f"merma es el {_pm}"))
    if nota:
        partes.append(_t("No suman", nota[0], "", "mp-kpi-nota", nota[1]))
    return '<div class="mp-kpis">' + "".join(partes) + "</div>"


def nota_no_suman(bl_scope, lado, vacios_nombrables=True):
    """`(corto, largo)` de lo que no suma en la vista, o None.

    `bl_scope` son las líneas del recorte (todas). Con un filtro de familia
    o de producto puesto, los documentos sin ítems no son de la vista —no
    tienen ni una ni otro— y no se nombran (`vacios_nombrables=False`)."""
    n_an, n_sp, n_vac = no_suman(bl_scope)
    if not vacios_nombrables:
        n_sp = n_vac = 0
    if not (n_an or n_sp or n_vac):
        return None
    corto, largo = [], []
    if n_an:
        corto.append(lado.anulados(n_an))
        largo.append(lado.anulados(n_an) + " (se ven en Estado y en el "
                     "Detalle)")
    if n_sp:
        corto.append(f"{n_sp:,} sin procesar")
        largo.append(f"{n_sp:,} sin procesar que todavía no tienen ítems")
    if n_vac:
        # De qué área son casi todos —en requerimientos, GASTOS—: es lo que
        # hace que el número se entienda.
        por_doc = bl_scope.groupby("doc").agg(
            area=("area", "first"), vacio=("vacio", "all"),
            estado=("estado", "first"))
        vac = por_doc[por_doc["vacio"] & (por_doc["estado"] != _ANULADO)
                      & (por_doc["estado"] != _GENERADO)]
        _pa = vac["area"].value_counts()
        corto.append(f"{n_vac:,} sin ítems")
        largo.append(lado.cuenta(n_vac) + " sin ítems —vienen sin producto, "
                     "cantidad ni valor"
                     + (f"; {int(_pa.iloc[0]):,} de {_nombre_area(_pa.index[0])}"
                        if len(_pa) else "") + "—")
    return (" · ".join(corto),
            "No suman en las barras ni en los totales: " + " y ".join(largo)
            + ".")


# ===========================================================================
# EL CSS DE LAS TARJETAS
# ===========================================================================
# Vive acá y no en `estilos/` por lo mismo que el de Compras vive en
# `graficos/compras/_css_proveedor.py`: sus reglas cuelgan de las keys de
# ESTAS tarjetas y sólo tienen sentido cuando se dibujan. Se inyecta en cada
# corrida, sin guarda de «una sola vez» (regla #59). Es UN molde con los
# prefijos de cada lado (`__C__` de los contenedores, `__K__` de los
# widgets): las dos tarjetas conviven en la página y sus keys no pueden ser
# las mismas. Las medidas son las de la cabecera de «Compras por período»:
# desplegables y toggles a 32px, la fila de KPI en su propio renglón.
_CSS_MOLDE = """<style>
/* La cabecera: el toggle de granularidad y los filtros en un flex que
   parte renglón si no entra; la fila de KPI ocupa siempre el suyo. El item
   del flex es el `stLayoutWrapper` que envuelve a cada key (regla #272),
   de ahí el `:has` con la clase de la key adentro, y nada más (#469). */
.st-key-__C___fila {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    align-items: center !important;
    gap: 10px !important;
    width: 100% !important;
}
.st-key-__C___fila > [data-testid="stLayoutWrapper"]:has(> .st-key-__C___hdr_area),
.st-key-__C___fila > [data-testid="stLayoutWrapper"]:has(> .st-key-__C___hdr_tipo),
.st-key-__C___fila > [data-testid="stLayoutWrapper"]:has(> .st-key-__C___hdr_familia) {
    flex: 1 1 150px !important;
    min-width: 0 !important;
    width: auto !important;
    max-width: 200px !important;
}
.st-key-__C___fila > [data-testid="stLayoutWrapper"]:has(> .st-key-__C___hdr_producto) {
    flex: 1 1 150px !important;
    min-width: 0 !important;
    width: auto !important;
    max-width: 260px !important;
}
.st-key-__C___fila > [data-testid="stLayoutWrapper"]:has(> .st-key-__C___kpi) {
    flex: 1 1 100% !important;
    min-width: 0 !important;
    width: auto !important;
}
.st-key-__C___fila [data-testid="stElementToolbar"] { display: none; }
.st-key-__C___hdr_area,
.st-key-__C___hdr_tipo,
.st-key-__C___hdr_familia,
.st-key-__C___hdr_producto,
.st-key-__C___kpi { width: 100% !important; }
.st-key-__C___hdr_area > [data-testid="stElementContainer"],
.st-key-__C___hdr_tipo > [data-testid="stElementContainer"],
.st-key-__C___hdr_familia > [data-testid="stElementContainer"],
.st-key-__C___hdr_producto > [data-testid="stElementContainer"],
.st-key-__C___kpi > [data-testid="stElementContainer"] { width: 100% !important; }
/* Los desplegables a la altura del toggle, con las tres piezas que mide la
   regla #477: el envoltorio, la caja que se ve y su input y su flecha. */
.st-key-__C___hdr_area .react-aria-ComboBox,
.st-key-__C___hdr_tipo .react-aria-ComboBox,
.st-key-__C___hdr_familia .react-aria-ComboBox,
.st-key-__C___hdr_producto .react-aria-ComboBox,
.st-key-__C___hdr_area .react-aria-ComboBox > div,
.st-key-__C___hdr_tipo .react-aria-ComboBox > div,
.st-key-__C___hdr_familia .react-aria-ComboBox > div,
.st-key-__C___hdr_producto .react-aria-ComboBox > div {
    min-height: 32px !important;
    height: 32px !important;
}
.st-key-__C___hdr_area .react-aria-ComboBox input,
.st-key-__C___hdr_tipo .react-aria-ComboBox input,
.st-key-__C___hdr_familia .react-aria-ComboBox input,
.st-key-__C___hdr_producto .react-aria-ComboBox input,
.st-key-__C___hdr_area .react-aria-ComboBox > div > button,
.st-key-__C___hdr_tipo .react-aria-ComboBox > div > button,
.st-key-__C___hdr_familia .react-aria-ComboBox > div > button,
.st-key-__C___hdr_producto .react-aria-ComboBox > div > button {
    height: 30px !important;
    min-height: 30px !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
.st-key-__C___hdr_area .react-aria-ComboBox input,
.st-key-__C___hdr_tipo .react-aria-ComboBox input,
.st-key-__C___hdr_familia .react-aria-ComboBox input,
.st-key-__C___hdr_producto .react-aria-ComboBox input { font-size: 12px !important; }
/* Los dos toggles —granularidad arriba, modo abajo— acotados a SU key y no
   al contenedor (CLAUDE.md: una regla colgada del contenedor captura los
   widgets que se agreguen después). */
.st-key-__K___gran [data-testid="stButtonGroup"] button,
.st-key-__K___modo [data-testid="stButtonGroup"] button {
    min-height: 32px !important;
    height: 32px !important;
    padding: 0 12px !important;
    font-size: 12px !important;
}
/* La fila de KPI: el total y un tramo por tarjeta, con su color. */
.st-key-__C___kpi [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.st-key-__C___kpi .mp-kpis {
    display: flex;
    flex-wrap: wrap;
    align-items: stretch;
    gap: 2px 0;
}
.st-key-__C___kpi .mp-kpi {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
    max-width: 150px;
    padding: 0 12px;
    line-height: 1.2;
    border-left: 1px solid var(--border);
}
.st-key-__C___kpi .mp-kpi:first-child {
    padding-left: 0;
    border-left: none;
    max-width: none;
}
.st-key-__C___kpi .mp-kpi-rot {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 10px;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.st-key-__C___kpi .mp-kpi-sw {
    flex: 0 0 auto;
    width: 8px;
    height: 8px;
    border-radius: 2px;
}
.st-key-__C___kpi .mp-kpi-val {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
}
.st-key-__C___kpi .mp-kpi-sub {
    margin-left: 4px;
    font-size: 10px;
    font-weight: 400;
    color: var(--text-secondary);
}
.st-key-__C___kpi .mp-kpi-total .mp-kpi-val {
    color: var(--accent-deep);
    font-weight: 700;
}
.st-key-__C___kpi .mp-kpi-nota { max-width: 300px; }
.st-key-__C___kpi .mp-kpi-nota .mp-kpi-val {
    font-size: 12px;
    font-weight: 400;
    color: var(--text-secondary);
}
/* La fila de modo: el toggle y, al lado, el caption que nombra el ámbito. */
.st-key-__C___pie { align-items: center !important; }
.st-key-__C___pie [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
/* Un iframe es inline y se apoya en la línea base: sin esto la grilla del
   Resumen le suma a la tarjeta el hueco del descendente (medido en Compras:
   7.6px). Y las dos del Detalle TAMBIÉN: se creía que el `st.columns` las
   dejaba en un flex, pero cada columna es `display: block` — medido el
   2026-09-24, 198.6px de zona para grillas de 191, y la tarjeta crecía
   7.6px al pasar de Resumen a Detalle en los tres lados (regla #510). */
.st-key-__C___resumen .stCustomComponentV1,
.st-key-__C___detalle .stCustomComponentV1 { display: block !important; }
</style>"""


def _css(lado):
    """El `<style>` de la tarjeta de `lado`, del molde con sus prefijos."""
    return _CSS_MOLDE.replace("__C__", lado.c).replace("__K__", lado.k)


# ===========================================================================
# LAS TARJETAS
# ===========================================================================

def tarjeta_requerimientos_periodo(d, *, cols, orden=()):
    """Requerimientos por período: barras, Resumen y Detalle.

    `d` son las líneas de requerimientos ya recortadas por la fecha de la
    franja y por sus chips (Sub Almacén, Familia); `cols` los nombres de
    columna resueltos (`fecha`, `doc`, `area`, `estado`, `fam`, `prod`,
    `cant`, `punit`, `val`); `orden` el de `orden_areas`, que reparte los
    colores por área."""
    _tarjeta(d, REQUERIMIENTOS, cols, orden)


def tarjeta_salidas_periodo(d, *, cols, orden=()):
    """Salidas por período: la misma tarjeta sobre `salidas.parquet`, con el
    tipo de descargo como filtro y como columna del Detalle (`cols["tipo"]`).
    Sin precio unitario en el parquet, se despeja de cada línea."""
    _tarjeta(d, SALIDAS, cols, orden)


def tarjeta_porcionamientos_periodo(d, *, cols, orden=()):
    """Porcionamientos: la misma tarjeta sobre `porcionamientos.parquet`,
    con la MERMA EN SOLES en la barra (regla #510).

    `cols` son los nombres resueltos que pide `lineas_porcionamientos`
    (`fecha`, `doc`, `area`, `tipo` —el usuario—, `prod`, `unid`, `cant`,
    `merma`, `fin`, `cant_fin`, `unid_fin`, `pprom`, `peso`). `orden` es el
    de requerimientos, como en las otras dos: el color de un área es el
    mismo en las tres tarjetas."""
    _tarjeta(d, PORCIONAMIENTOS, cols, orden)


def _tarjeta(d, lado, cols, orden):
    k, c = lado.k, lado.c
    with st.container(border=True, key=lado.card):
        st.markdown(_css(lado), unsafe_allow_html=True)
        requeridas = (("fecha", "cant", "merma") if lado.merma
                      else ("fecha", "val"))
        if not all(cols.get(x) for x in requeridas):
            st.info("No hay columnas suficientes para este gráfico.")
            return
        # Porcionamientos: una fila por PORCIONAMIENTO y sus cortes aparte,
        # no una por fila del parquet (el grano, regla #510).
        if lado.merma:
            base, cortes_todos = lineas_porcionamientos(d, **cols)
        else:
            base, cortes_todos = lineas_documentos(d, **cols), None
        lin = base[~base["vacio"]]
        valida = lin["estado"] != _ANULADO
        con_tipo = bool(lado.rotulo_tipo and cols.get("tipo"))

        def _rank(columna, mascara):
            s = (lin.loc[mascara & valida].groupby(columna)["valor"].sum()
                    .sort_values(ascending=False))
            return [x for x in s.index if x]

        def _opciones(centinela, columna, mascara, key):
            """`(opciones, previo, máscara siguiente)` de un desplegable.

            Del valor vigente en `session_state`, que es lo que el widget va
            a mostrar: cada lista ofrece lo que dejan los filtros de su
            izquierda, ordenado por valor. Lo elegido que dejó de estar (el
            rango se angostó) se AGREGA al final en vez de resetearse: la
            vista sale vacía y un cartel dice por qué — el criterio de
            Producto en Compras."""
            ops = [centinela] + _rank(columna, mascara)
            prev = st.session_state.get(key)
            if prev is not None and prev not in ops:
                ops.append(prev)
            sig = mascara.copy()
            if prev not in (None, centinela):
                sig &= lin[columna] == prev
            return ops, sig

        # ── Las opciones, ANTES de dibujar los widgets ────────────────────
        todo = pd.Series(True, index=lin.index)
        ops_area, m_area = _opciones(_AREA_TODAS, "area", todo, f"{k}_area")
        if con_tipo:
            ops_tipo, m_tipo = _opciones(lado.tipo_todos, "tipo", m_area,
                                         f"{k}_tipo")
        else:
            ops_tipo, m_tipo = [lado.tipo_todos], m_area
        if lado.con_familia:
            ops_fam, m_fam = _opciones(_FAM_TODAS, "fam", m_tipo,
                                       f"{k}_familia")
        else:
            ops_fam, m_fam = [_FAM_TODAS], m_tipo
        prods = _rank("prod", m_fam)
        etq_top = {f"Top {_n} por {lado.top}": _n for _n in _TOPS}
        ops_prod = ([_PROD_TODOS]
                    + [_e for _e, _n in etq_top.items() if _n < len(prods)]
                    + prods)
        _p_prev = st.session_state.get(f"{k}_producto")
        if _p_prev is not None and _p_prev not in ops_prod:
            # Los centinelas «Top N» sí se resetean: «Top 20» no significa
            # nada en un recorte donde quedan 8 productos.
            if _p_prev == _PROD_TODOS or _p_prev in etq_top:
                st.session_state[f"{k}_producto"] = _PROD_TODOS
            else:
                ops_prod.append(_p_prev)

        # ── La cabecera: granularidad, los filtros y la fila de KPI ───────
        tipo_sel = lado.tipo_todos
        fam_sel = _FAM_TODAS
        with st.container(horizontal=True, gap="small", key=f"{c}_fila"):
            gran = st.segmented_control(
                "Agrupar por", _GRAN_OPCIONES, default=_GRAN_DEFAULT,
                required=True, key=f"{k}_gran",
                label_visibility="collapsed")
            with st.container(key=f"{c}_hdr_area"):
                area_sel = st.selectbox(
                    "Área", ops_area, key=f"{k}_area",
                    format_func=lambda a: (a if a == _AREA_TODAS
                                           else _nombre_area(a)),
                    label_visibility="collapsed",
                    help=f"Acota ESTA tarjeta al área que {lado.accion}, "
                         "encima de los chips de la franja. Ordenadas por "
                         f"{lado.medida} en el rango.")
            if con_tipo:
                with st.container(key=f"{c}_hdr_tipo"):
                    tipo_sel = st.selectbox(
                        lado.rotulo_tipo, ops_tipo, key=f"{k}_tipo",
                        label_visibility="collapsed",
                        help=lado.ayuda_tipo or None)
            # Sin familia en el parquet (porcionamientos) no hay filtro: un
            # desplegable con una sola opción no filtra nada.
            if lado.con_familia:
                with st.container(key=f"{c}_hdr_familia"):
                    fam_sel = st.selectbox(
                        "Familia", ops_fam, key=f"{k}_familia",
                        format_func=lambda f: (f if f == _FAM_TODAS
                                               else _oracion(f)),
                        label_visibility="collapsed",
                        help="Acota la tarjeta a una familia de productos. "
                             "Ofrece las de los filtros de su izquierda.")
            with st.container(key=f"{c}_hdr_producto"):
                prod_sel = st.selectbox(
                    "Producto", ops_prod, key=f"{k}_producto",
                    label_visibility="collapsed",
                    help=f"Ordenados por {lado.medida} en el rango: el primero "
                         f"es el de mayor {lado.top}. «Top N por {lado.top}» "
                         "suma los N mayores en una sola serie. Se puede "
                         "escribir para buscar.")
            with st.container(key=f"{c}_kpi"):
                kpi = st.empty()
        gran = gran or _GRAN_DEFAULT
        area_sel = area_sel or _AREA_TODAS
        tipo_sel = tipo_sel or lado.tipo_todos
        fam_sel = fam_sel or _FAM_TODAS
        prod_sel = prod_sel or _PROD_TODOS

        # ── El recorte de la tarjeta, sobre TODAS las líneas ──────────────
        # Las vacías entran con los filtros de la cabecera (área y tipo son
        # del documento); con familia o producto puestos quedan afuera
        # solas, porque no tienen ni una ni otro.
        m = pd.Series(True, index=base.index)
        if area_sel != _AREA_TODAS:
            m &= base["area"] == area_sel
        if con_tipo and tipo_sel != lado.tipo_todos:
            m &= base["tipo"] == tipo_sel
        if fam_sel != _FAM_TODAS:
            m &= base["fam"] == fam_sel
        if prod_sel in etq_top:
            m &= base["prod"].isin(prods[:etq_top[prod_sel]])
        elif prod_sel != _PROD_TODOS:
            m &= base["prod"] == prod_sel
        bl = base[m].copy()
        bl["clave"] = _periodo_serie(bl["fecha"], gran)

        _amb = [x for x in (
            None if area_sel == _AREA_TODAS else _nombre_area(area_sel),
            None if tipo_sel == lado.tipo_todos else tipo_sel,
            None if fam_sel == _FAM_TODAS else _oracion(fam_sel),
            (None if prod_sel == _PROD_TODOS
             else _compras_truncar(prod_sel)))
            if x]
        # El ÁMBITO va al título, como en Compras: con los filtros de la
        # tarjeta y los chips de la franja, «por semana» a secas no deja
        # saber de qué son esas barras.
        titulo = (f"{lado.titulo} por {_AGRUPADO_GRAN[gran]}"
                  + (" · " + " · ".join(_amb) if _amb else ""))

        # Sin columna de área la barra no se puede partir por quién pidió o
        # dio de baja: todo queda en «Sin área». Pasa con un parquet de
        # salidas anterior a la consulta que trae `AREA` (2026-09-23), y se
        # dice en vez de dibujar un gráfico que parece roto.
        if not cols.get("area"):
            st.caption(f"`{lado.plur}` todavía no trae la columna del área: "
                       "sin ella la barra no se parte. Se agrega en su "
                       "consulta y llega con «Refrescar».")

        rng = _rango_vigente()
        rango = ((rng[0].date(), (rng[1] - pd.Timedelta(days=1)).date())
                 if rng else None)
        v = vista_periodos(bl, gran, rango, orden, lado)
        if not v["claves"]:
            st.info(f"**{titulo}** — sin {lado.plur} que mostrar. Ampliá el "
                    "rango de fechas (en la franja de arriba) o soltá algún "
                    "filtro de la tarjeta.")
            return
        claves = v["claves"]

        # ── Lo que NO suma, dicho en la fila de KPI ───────────────────────
        nota = nota_no_suman(
            bl, lado,
            vacios_nombrables=fam_sel == _FAM_TODAS and prod_sel == _PROD_TODOS)
        dv = _validas(bl)
        # Porcionamientos cierra la fila con lo porcionado y le da a cada
        # área su % de merma PROPIO en el tooltip (#510).
        kw_kpi = (dict(costo=float(dv["costo"].sum()),
                       costo_area=dv.groupby("area")["costo"].sum().to_dict())
                  if lado.merma else {})
        kpi.markdown(
            _html_kpi(float(sum(v["tot"])), int(dv["doc"].nunique()),
                      v["trazas"],
                      dv.groupby("area")["valor"].sum().loc[lambda s: s > 0],
                      nota, lado, **kw_kpi),
            unsafe_allow_html=True)

        # ── Foco, modo y clic: se resuelven ANTES de dibujar (#398, #399) ─
        # Todo como en Compras: cambiar la granularidad o un filtro suelta el
        # foco; el modo se lee de `session_state` porque el alto de la
        # figura depende de él; el clic de la barra se lee de la key que se
        # DIBUJÓ la corrida anterior, con un contador en la key.
        ctx = (gran, area_sel, tipo_sel, fam_sel, prod_sel)
        if st.session_state.get(f"{k}_ctx_prev") != ctx:
            st.session_state[f"{k}_ctx_prev"] = ctx
            st.session_state[f"{k}_focus"] = None
            st.session_state[f"{k}_doc"] = None
        # Un clic en una FILA del Resumen pidió abrir su Detalle en la
        # corrida anterior: la grilla se dibuja debajo del toggle de modo, y
        # la key de un widget ya dibujado no se puede escribir — así que el
        # pedido viaja hasta acá, que es antes del toggle.
        _ir = st.session_state.pop(f"_{k}_ir_detalle", None)
        if _ir is not None:
            st.session_state[f"{k}_focus"] = _ir
            st.session_state[f"{k}_doc"] = None
            st.session_state[f"{k}_modo"] = _MODO_DETALLE
        modo = st.session_state.get(f"{k}_modo")
        if modo not in _MODO_OPCIONES:
            modo = _MODO_DEFAULT
        foco_antes = st.session_state.get(f"{k}_focus")
        nclic = st.session_state.get(f"{k}_nclic", 0)
        key_base = f"{k}_graf_{gran}"
        pt = _first_point(st.session_state.get(f"{key_base}_{nclic}"))
        if pt is not None:
            nclic += 1
            st.session_state[f"{k}_nclic"] = nclic
            clic = _clave_del_clic(pt.get("x"), claves)
            if clic is None:
                pass
            elif modo == _MODO_RESUMEN:
                # Desde Resumen el clic ABRE el Detalle de esa barra (el
                # gesto es «mostrame ésta»), como en Compras (regla #476).
                st.session_state[f"{k}_doc"] = None
                st.session_state[f"{k}_focus"] = clic
                st.session_state[f"{k}_modo"] = _MODO_DETALLE
                modo = _MODO_DETALLE
            else:
                st.session_state[f"{k}_doc"] = None
                st.session_state[f"{k}_focus"] = (
                    None if foco_antes == clic else clic)
        foco = st.session_state.get(f"{k}_focus")
        foco_ok = foco in set(claves)
        con_tabla = modo == _MODO_RESUMEN or foco_ok
        alto_fig = alturas.COMPACTO if con_tabla else _ALTO_FIG_SOLO

        fig = figura_periodos(
            v, alto_fig, titulo=titulo,
            foco=foco if (foco_ok and modo == _MODO_DETALLE) else None)
        # Lo que devuelve se ignora: el clic ya se leyó arriba.
        st.plotly_chart(fig, use_container_width=True, on_select="rerun",
                        selection_mode="points",
                        key=f"{key_base}_{nclic}")

        if lado.merma:
            ayuda_modo = ("Qué se ve debajo del gráfico. **Resumen**: una "
                          "fila por barra —sus porcionamientos, cortes, "
                          "áreas, lo porcionado, la merma y su %, y la "
                          "variación— más el total. **Detalle**: los "
                          "porcionamientos de la barra que toques y, al "
                          "costado, los cortes del que elijas.")
        else:
            ayuda_modo = (f"Qué se ve debajo del gráfico. **Resumen**: una fila "
                          f"por barra —sus {lado.plur}, líneas, áreas, "
                          "valorizado, variación y estado— más el total. "
                          f"**Detalle**: los {lado.plur} de la barra que toques "
                          "y, al costado, las líneas del que elijas.")
        with st.container(horizontal=True, gap="small", key=f"{c}_pie"):
            st.segmented_control(
                "Qué se ve abajo", _MODO_OPCIONES, default=_MODO_DEFAULT,
                required=True, key=f"{k}_modo",
                label_visibility="collapsed", help=ayuda_modo)
            pie = st.empty()

        # ── RESUMEN: el gráfico escrito como tabla ────────────────────────
        if modo == _MODO_RESUMEN:
            # La key lleva lo que cambia las FILAS y un contador que se
            # estrena cada vez que un clic en una fila lleva al Detalle: así
            # la grilla vuelve sin la selección vieja (regla #471).
            n_res = st.session_state.get(f"{k}_nres", 0)
            k_res = f"{k}_res_grid_" + _clave_grilla(gran, ctx, rango, n_res)
            with st.container(key=f"{c}_resumen"):
                if lado.merma:
                    filas, total = tabla_resumen_porc(v, foco if foco_ok else None)
                    clic_fila = renderizar_periodos_porc(
                        filas, altura=_ALTO_TABLA, key=k_res,
                        rotulo_periodo=_AGRUPADO_GRAN[gran].capitalize(),
                        ver_variacion=gran in _GRAN_VARIACION, total=total)
                else:
                    filas, total = tabla_resumen(v, foco if foco_ok else None)
                    clic_fila = renderizar_periodos_mov(
                        filas, altura=_ALTO_TABLA, key=k_res,
                        rotulo_periodo=_AGRUPADO_GRAN[gran].capitalize(),
                        rotulo_docs=lado.plur.capitalize(),
                        ver_variacion=gran in _GRAN_VARIACION, total=total)
            pie.caption(
                f"**{_del_al(dv['fecha'])}** · agrupado por "
                f"{_AGRUPADO_GRAN[gran]} — una fila por barra; un clic en "
                "una fila (o en su barra) abre su detalle.")
            if clic_fila in set(claves):
                st.session_state[f"_{k}_ir_detalle"] = clic_fila
                st.session_state[f"{k}_nres"] = n_res + 1
                st.rerun(scope=scope_rerun())
            return

        # ── DETALLE sin barra elegida: la zona queda vacía y lo dice ──────
        # El `st.empty()` sólo en esta rama, como en Compras (regla #471):
        # borra las grillas al soltar el foco sin re-montarlas en cada
        # corrida mientras hay detalle.
        if not foco_ok:
            st.empty()
            pie.caption("Tocá una barra —o una fila del Resumen— para ver "
                        f"sus {lado.plur}.")
            return
        hueco = st.container(key=f"{c}_detalle")

        # ── DETALLE: los documentos del período y las líneas del elegido ──
        amb = bl[bl["clave"] == foco]
        sel = st.session_state.get(f"{k}_doc")
        if sel not in set(amb["doc"]):
            sel = _mayor_valido(amb)
        if lado.merma:
            # Los porcionamientos del período y los CORTES del elegido, que
            # viven aparte (`lineas_porcionamientos`): no son filas de `amb`.
            filas_doc, total_doc = tabla_porcionamientos(amb, sel)
            p_sel = amb[amb["doc"] == sel].iloc[0]
            filas_lin, total_lin = tabla_cortes(
                cortes_todos[cortes_todos["doc"] == sel], p_sel["unid"])
        else:
            filas_doc, total_doc = tabla_documentos(amb, sel, lado)
            lin_sel = (amb[(amb["doc"] == sel) & ~amb["vacio"]]
                       .sort_values("valor", ascending=False))
            filas_lin = pd.DataFrame({
                "prod": lin_sel["prod"],
                "cant": pd.to_numeric(lin_sel["cant"], errors="coerce").round(3),
                "punit": pd.to_numeric(lin_sel["punit"], errors="coerce").round(4),
                "valor": lin_sel["valor"].astype(float).round(2),
            })
            _nl = len(filas_lin)
            total_lin = {
                "prod": f"Total · {_nl} línea" + ("" if _nl == 1 else "s"),
                "cant": "", "punit": "",
                "valor": f"S/ {lin_sel['valor'].sum():,.2f}",
            }
        with hueco:
            # columnas-internas: las dos tablas del detalle, DENTRO de la
            # tarjeta, con el reparto de «Compras por período» (la lista
            # lleva cinco o seis columnas contra cuatro). La de porciona-
            # mientos lleva siete y tres son nombres: medido a 1366px, con
            # 1.15 el producto, el área y el usuario salían en «Prod…».
            c_doc, c_lin = st.columns([1.3, 1] if lado.merma else [1.15, 1],
                                      gap=GAP_DRILL)
            # La key lleva lo que cambia las FILAS —el período, los filtros,
            # el rango— y el contador de clics del gráfico, no el documento
            # elegido: así el orden que eligió el usuario sobrevive al clic
            # (regla #471).
            k_tablas = _clave_grilla(gran, foco, ctx, rango, nclic)
            with c_doc:
                if lado.merma:
                    clic_doc = renderizar_porcionamientos_mov(
                        filas_doc, altura=_ALTO_TABLA,
                        key=f"{k}_doc_grid_{k_tablas}", total=total_doc)
                else:
                    clic_doc = renderizar_documentos_mov(
                        filas_doc, altura=_ALTO_TABLA,
                        key=f"{k}_doc_grid_{k_tablas}",
                        rotulo_tipo=lado.rotulo_tipo if con_tipo else "",
                        total=total_doc)
            with c_lin:
                if lado.merma:
                    renderizar_cortes_mov(
                        filas_lin, altura=_ALTO_TABLA,
                        key=f"{k}_lin_grid_{k_tablas}", total=total_lin)
                else:
                    renderizar_lineas_mov(
                        filas_lin, altura=_ALTO_TABLA,
                        key=f"{k}_lin_grid_{k_tablas}", total=total_lin)
        _i = claves.index(foco)
        if lado.merma:
            # El RENDIMIENTO del elegido, que es lo que la tabla de cortes no
            # dice sola: cuánto entró, cuánto quedó útil y cuánto costó la
            # merma.
            u = unidad_corta(p_sel["unid"])
            cant_p, merma_p = float(p_sel["cant"]), float(p_sel["merma_cant"])
            util = cant_p - merma_p
            rend = f" ({util / cant_p:.0%})" if cant_p > 0 else ""
            # El período va en su forma CORTA («14–20 set 2026»): con la
            # larga del hover, el renglón partía en dos y la tarjeta crecía
            # 7px al abrir el Detalle (medido a 1366px).
            pie.caption(
                f"**{v['fila'][_i]}** — "
                f"**{_compras_truncar(p_sel['prod'], 28)}**: "
                f"{fmt_cant(cant_p)} {u} → {fmt_cant(util)} {u} útiles{rend}, "
                f"merma S/ {float(p_sel['valor']):,.2f}. Clic en otro para ver "
                "sus cortes.")
        else:
            pie.caption(f"**{v['hover'][_i]}** — clic en {'una' if lado.fem else 'un'} "
                        f"{lado.sing} para ver sus líneas al costado.")

        # El clic en la lista: la selección VIGENTE, así que se actúa sólo
        # si difiere de la que ya se muestra. El rerun redibuja la marca de
        # la lista y las líneas de al lado (regla #306 para el scope).
        if clic_doc is None or clic_doc == sel or clic_doc not in set(amb["doc"]):
            return
        st.session_state[f"{k}_doc"] = clic_doc
        st.rerun(scope=scope_rerun())
