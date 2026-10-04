"""
graficos.inventario_movimientos — la sección «Movimientos» de Stock e
Inventario: POR QUÉ cambió el stock entre dos fechas (2026-10-03, regla #602).

Pedido: «una vista de tipos de movimientos», sobre el kardex del Almacén
(MKARDEX y MSUBKARDEX con los tipos de TTIPODOCUMENTO: descargo de ventas,
porcionamiento, orden de producción…). Va en Stock y no en el reporte
Movimientos porque contesta una pregunta del stock —de dónde salió la
diferencia entre el 31 de agosto y el 30 de septiembre— con el mismo kardex
que «Ver a una fecha» de Productos (regla #601).

LA CUENTA. Stock al principio + lo que movió cada grupo de tipos
(`kardex.GRUPOS`) + VALORIZACIÓN = stock al final. Las dos puntas son la foto
del kardex (`data.stock_al`), y los movimientos, su `nValor`: las compras a su
costo, lo interno al precio promedio del momento. La valorización es lo que
cambió el valor sin que se moviera la cantidad, y existe porque el kardex
recalcula el precio promedio con cada ingreso: con stock negativo —se vendió
antes de recibir— o con el precio en cero, la salida sale barata y la
diferencia aparece al reponer. No es un error de la cuenta: la cantidad cierra
exacta en 13.722 de 13.817 áreas × producto (las otras 95, por hora de corte).
Medido en septiembre 2026: −S/ 10.126, 85 % en Cocina.

EL ÁMBITO es el del reporte: lo ACTIVO (regla #598) y los chips de la franja,
más los filtros propios de la tarjeta. El kardex se cruza con `d` por código
de área y de producto, así que lo inactivo no entra ni en los movimientos ni
en las fotos.

Dos vistas en la MISMA tarjeta: «Por tipo» (la cascada y la tabla por tipo de
documento) y «Por área» (la misma cuenta, una fila por área: «Entre áreas»
suma cero en el total y es lo que explica cada área). Y un aviso cuando hay
ventas que salieron SIN COSTO.

`armar_movimientos` es pura y la vigila `test_graficos.py::_pruebas_kardex`.
"""

import datetime as dt
import html
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data
import kardex
from cortes import MESES_ABR_ES
from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, ADVERTENCIA_BORDE, ADVERTENCIA_FONDO,
    AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_POS, AJUSTE_POS_TEXTO, BLANCO,
    GRIS_BORDE, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
    LAVANDA_BORDE, TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos.base import _compras_layout, recortar_seleccion, seleccion_en_panel
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos.inventario_productos import (
    _etiqueta, _plano, _rotulo_area, css_filtros, filtro_en_panel,
)

_K_RANGO = "inv_mov_rango"
_K_AREAS = "inv_mov_areas"
_K_FAMILIAS = "inv_mov_familias"
_K_BUSCAR = "inv_mov_buscar"
_K_VISTA = "inv_mov_vista"

_VISTAS = ("Por tipo", "Por área")
_EPS = 1e-9
_NOMBRE_GRUPO = dict(kardex.GRUPOS)
_ORDEN_GRUPO = {g: i for i, (g, _) in enumerate(kardex.GRUPOS)}


# ═══════════════════════════════════════════════════════════════════════
# DATOS — puras, sin Streamlit
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Movimientos:
    """El resultado de `armar_movimientos`.

    `por_tipo`: una fila por tipo de documento (`grupo`, `tipo`, `nombre`,
    `val_in`, `val_out`, `neto`, `movs`, `anul`, `movs_sin_costo`), en el
    orden de `kardex.GRUPOS`. `por_area`: una fila por área con `ini`, el
    neto de cada grupo (una columna por grupo, por NOMBRE), `valorizacion`
    y `fin`. `sin_costo`: los productos que salieron por ventas sin costo,
    con su valor a precio de hoy."""
    ini: float
    fin: float
    por_tipo: pd.DataFrame
    por_area: pd.DataFrame
    sin_costo: pd.DataFrame

    @property
    def netos(self):
        """El neto de cada grupo, en el orden de `kardex.GRUPOS`."""
        n = self.por_tipo.groupby("grupo")["neto"].sum()
        return {g: float(n.get(g, 0.0)) for g, _ in kardex.GRUPOS}

    @property
    def valorizacion(self):
        return self.fin - self.ini - sum(self.netos.values())

    @property
    def movs(self):
        return int(self.por_tipo["movs"].sum())


def _texto(serie):
    return serie.astype("string").fillna("").str.strip()


def _valor_por_area(foto, base):
    """Σ stock × precio de la foto, por NOMBRE de área, sólo en las
    combinaciones de `base`."""
    if foto is None or foto.empty:
        return pd.Series(dtype=float)
    f = pd.DataFrame({
        "area_cod": _texto(foto["area"]), "cod": _texto(foto["cod"]),
        "v": (pd.to_numeric(foto["stock"], errors="coerce").fillna(0)
              * pd.to_numeric(foto["precio"], errors="coerce").fillna(0)),
    })
    f = f.merge(base[["area_cod", "cod", "area"]], on=["area_cod", "cod"],
                how="inner")
    return f.groupby("area")["v"].sum()


def armar_movimientos(d, mov, foto_ini, foto_fin, *, col_cod_area, col_cod,
                      col_area, col_prod, col_fam=None, col_punit=None,
                      areas=(), familias=(), texto=""):
    """El stock al principio y al final, y lo que movió cada tipo de
    documento en el medio, dentro del ámbito de `d` (una fila por área ×
    producto, la del reporte) y los recortes (`areas` y `familias` son
    listas de nombres, vacía = todas; `texto`, palabras que tienen que
    estar en el nombre o el código del producto).

    `mov` es lo de `kardex.sql_movimientos`; `foto_ini` y `foto_fin`, lo de
    `kardex.sql_stock_al` en las dos puntas. Pura."""
    base = pd.DataFrame({
        "area_cod": _texto(d[col_cod_area]), "cod": _texto(d[col_cod]),
        "area": _texto(d[col_area]), "producto": _texto(d[col_prod]),
        "familia": _texto(d[col_fam]) if col_fam else "",
        "precio_hoy": (pd.to_numeric(d[col_punit], errors="coerce")
                       if col_punit else np.nan),
    })
    if areas:
        base = base[base["area"].isin(list(areas))]
    if familias:
        base = base[base["familia"].isin(list(familias))]
    palabras = _plano(texto).split()
    if palabras:
        pajar = [_plano(f"{n} {c}") for n, c in zip(base["producto"],
                                                     base["cod"])]
        base = base[[all(p in h for p in palabras) for h in pajar]]
    base = base.drop_duplicates(["area_cod", "cod"])

    m = pd.DataFrame({
        "area_cod": _texto(mov["area"]), "cod": _texto(mov["cod"]),
        "tipo": _texto(mov["tipo"]), "nombre": _texto(mov["nombre"]),
        **{c: pd.to_numeric(mov[c], errors="coerce").fillna(0)
           for c in ("val_in", "val_out", "movs", "anul", "cant_sin_costo",
                     "movs_sin_costo")},
    }).merge(base, on=["area_cod", "cod"], how="inner")
    m["grupo"] = m["tipo"].map(kardex.grupo_de)
    m["neto"] = m["val_in"] - m["val_out"]

    por_tipo = (m.groupby(["grupo", "tipo"], as_index=False, sort=False)
                .agg(nombre=("nombre", "first"), val_in=("val_in", "sum"),
                     val_out=("val_out", "sum"), neto=("neto", "sum"),
                     movs=("movs", "sum"), anul=("anul", "sum"),
                     movs_sin_costo=("movs_sin_costo", "sum")))
    por_tipo["_o"] = por_tipo["grupo"].map(_ORDEN_GRUPO)
    por_tipo = (por_tipo.sort_values(["_o", "tipo"], kind="stable")
                .drop(columns="_o").reset_index(drop=True))

    ini_a = _valor_por_area(foto_ini, base)
    fin_a = _valor_por_area(foto_fin, base)
    netos_a = m.groupby(["area", "grupo"])["neto"].sum().unstack("grupo")
    areas_todas = sorted(set(ini_a.index) | set(fin_a.index)
                         | set(netos_a.index))
    por_area = pd.DataFrame({"area": areas_todas})
    por_area["ini"] = por_area["area"].map(ini_a).fillna(0.0)
    for g, _ in kardex.GRUPOS:
        por_area[g] = (por_area["area"].map(netos_a[g]).fillna(0.0)
                       if g in netos_a.columns else 0.0)
    por_area["fin"] = por_area["area"].map(fin_a).fillna(0.0)
    grupos = [g for g, _ in kardex.GRUPOS]
    por_area["valorizacion"] = (por_area["fin"] - por_area["ini"]
                                - por_area[grupos].sum(axis=1))
    # Primero las áreas que más se movieron; un área sin stock en ninguna
    # punta y sin movimientos no dice nada.
    bruto = por_area[grupos].abs().sum(axis=1)
    hay = (bruto > 0.5) | (por_area["ini"].abs() > 0.5) | (por_area["fin"].abs() > 0.5)
    por_area = (por_area[hay].assign(_b=bruto[hay], _f=por_area["fin"].abs()[hay])
                .sort_values(["_b", "_f"], ascending=False, kind="stable")
                .drop(columns=["_b", "_f"]).reset_index(drop=True))

    sc = m[m["cant_sin_costo"] > _EPS]
    sin_costo = (sc.groupby(["producto", "area"], as_index=False, sort=False)
                 .agg(cant=("cant_sin_costo", "sum"),
                      movs=("movs_sin_costo", "sum"),
                      precio_hoy=("precio_hoy", "first")))
    sin_costo["valor_hoy"] = (sin_costo["cant"]
                              * sin_costo["precio_hoy"].fillna(0))
    sin_costo = sin_costo.sort_values(["valor_hoy", "movs"], ascending=False,
                                      kind="stable").reset_index(drop=True)

    return Movimientos(float(ini_a.sum()), float(fin_a.sum()), por_tipo,
                       por_area, sin_costo)


def periodo_por_defecto(desde_min, tope):
    """El mes pasado ENTERO, contado desde el último día con movimientos:
    «¿cómo se movió septiembre?» es la pregunta de siempre, y es la misma
    fecha con que abre «Ver a una fecha». Si el kardex no llega a un mes
    entero, todo lo que hay."""
    fin = tope.replace(day=1) - dt.timedelta(days=1)
    ini = fin.replace(day=1)
    if ini < desde_min:
        return desde_min, tope
    return ini, fin


def _fecha_corta(f, con_ano=False):
    return (f"{f.day} {MESES_ABR_ES[f.month - 1]}"
            + (f" {f.year}" if con_ano else ""))


def _soles(v, signo=False):
    if abs(v) < 0.5:
        return "S/ 0"
    s = "−" if v < 0 else ("+" if signo else "")
    return f"{s}S/ {abs(v):,.0f}"


# ═══════════════════════════════════════════════════════════════════════
# PRESENTACIÓN
# ═══════════════════════════════════════════════════════════════════════

_RENGLON_GRUPO = {
    "compras": "Compras",
    "ventas": "Ventas",
    "ajustes": "Ajustes de<br>inventario",
    "salidas": "Notas de<br>salida",
    "produccion": "Producción y<br>porcion.",
    "entre": "Entre<br>áreas",
    "otros": "Otros",
}


def fig_cascada(M, rot_ini, rot_fin):
    """Stock al principio → cada grupo → valorización → stock al final.
    «Entre áreas» va siempre, aunque sume cero: que no mueva el total es la
    respuesta; «Otros», sólo si suma algo."""
    netos = M.netos
    pasos = [(f"Stock al<br>{rot_ini}", M.ini, "absolute",
              "El valor del stock al cerrar el día anterior.")]
    for g, nombre in kardex.GRUPOS:
        if g == "otros" and abs(netos[g]) < 0.5:
            continue
        pasos.append((_RENGLON_GRUPO[g], netos[g], "relative",
                      f"{nombre}: lo que entró menos lo que salió."))
    pasos.append(("Valori-<br>zación", M.valorizacion, "relative",
                  "Lo que cambió el valor sin que se moviera la cantidad: "
                  "el precio promedio que se recalcula con stock negativo "
                  "o con ventas que salen sin costo."))
    pasos.append((f"Stock al<br>{rot_fin}", 0.0, "total",
                  "El valor del stock al cerrar el último día."))
    textos = [_soles(v) if med != "relative" else _soles(v, signo=True)
              for _, v, med, _ in pasos]
    textos[-1] = _soles(M.fin)
    hover = [f"<b>{x.replace('<br>', ' ').replace('- ', '')}</b>: {t}<br>"
             f"<span style='font-size:11px'>{h}</span>"
             for (x, _, _, h), t in zip(pasos, textos)]
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=[p[2] for p in pasos],
        x=[p[0] for p in pasos],
        y=[p[1] for p in pasos],
        text=textos, textposition="outside", cliponaxis=False,
        # Un solo cuerpo: Plotly achica el rótulo de afuera según la barra,
        # y «S/ 0» salía más grande que «+S/ 154,493».
        textfont=dict(size=11, color=GRIS_TEXTO_MEDIO), constraintext="none",
        # Es STOCK, no costo: entrar es verde y salir rojo (al revés que la
        # cascada de Compras, que mide un gasto).
        increasing=dict(marker=dict(color=AJUSTE_POS)),
        decreasing=dict(marker=dict(color=AJUSTE_NEG)),
        totals=dict(marker=dict(color=ACENTO)),
        connector=dict(line=dict(color=GRIS_BORDE, width=1)),
        hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
    ))
    # `waterfallgap` y no `bargap` (CLAUDE.md § Plotly).
    fig.update_layout(waterfallgap=0.3)
    _compras_layout(fig, alto=alturas.STOCK_MOVIMIENTOS)
    fig.update_layout(showlegend=False, title="",
                      margin=dict(l=6, r=6, t=22, b=6))
    fig.update_yaxes(showticklabels=False, gridcolor=GRIS_LINEA,
                     zeroline=True, zerolinecolor=GRIS_BORDE)
    # Nombres, no números: sin `type="category"` un rótulo que parezca un
    # número cambia el tipo del eje (regla #325).
    fig.update_xaxes(type="category", tickangle=0,
                     tickfont=dict(size=11, color=GRIS_TEXTO_MEDIO))
    return fig


CSS_MOVIMIENTOS = f"""
.inv-mov-caja {{ max-height: {alturas.STOCK_MOVIMIENTOS}px; overflow-y: auto;
    border-top: 1px solid {GRIS_BORDE}; }}
.inv-mov-t {{ width: 100%; border-collapse: collapse; font-size: 12px;
    font-variant-numeric: tabular-nums; color: {TEXTO_PRINCIPAL}; }}
.inv-mov-t th, .inv-mov-t td {{ border: 0 !important; }}
.inv-mov-t th {{ position: sticky; top: 0; z-index: 1; background: {BLANCO};
    font-size: 11px; font-weight: 600; color: {GRIS_TEXTO}; text-align: right;
    padding: 6px 6px; border-bottom: 1px solid {GRIS_BORDE} !important;
    line-height: 1.2;
    vertical-align: bottom; }}
.inv-mov-t th:first-child, .inv-mov-t td:first-child {{ text-align: left; }}
.inv-mov-t td {{ padding: 3px 6px; border-bottom: 1px solid {GRIS_LINEA} !important;
    text-align: right; white-space: nowrap; }}
.inv-mov-t td:first-child {{ overflow: hidden; text-overflow: ellipsis;
    max-width: 230px; }}
.inv-mov-t tr.g td {{ font-size: 10px; font-weight: 700; letter-spacing: .05em;
    text-transform: uppercase; color: {GRIS_TEXTO_SUAVE}; padding-top: 7px;
    border-bottom: 0 !important; }}
.inv-mov-t tr.tot td {{ position: sticky; bottom: 0; background: {BLANCO};
    font-weight: 700; border-top: 1px solid {LAVANDA_BORDE} !important;
    border-bottom: 0 !important; }}
.inv-mov-t tr:nth-child(even) {{ background: transparent; }}
.inv-mov-t tr.alerta td {{ background: {ADVERTENCIA_FONDO}; }}
.inv-mov-t .pos {{ color: {AJUSTE_POS_TEXTO}; }}
.inv-mov-t .neg {{ color: {AJUSTE_NEG_TEXTO}; }}
.inv-mov-t .cero {{ color: {GRIS_TEXTO_SUAVE}; }}
.inv-mov-t .punta {{ color: {ACENTO_TEXTO_OSCURO}; font-weight: 600; }}
.inv-mov-t .nota {{ color: {GRIS_TEXTO}; font-size: 11px; }}
.inv-mov-nota {{ font-size: 11.5px !important; line-height: 1.45;
    color: {GRIS_TEXTO_MEDIO}; }}
.st-key-inv_mov_alerta {{ background: {ADVERTENCIA_FONDO};
    border: 1px solid {ADVERTENCIA_BORDE}; border-radius: 8px;
    padding: 6px 10px; box-sizing: border-box !important; }}
.inv-mov-pop td:first-child {{ max-width: none; }}
.st-key-inv_mov_alerta p {{ font-size: 12px !important; margin: 0; }}
.st-key-inv_mov_alerta button[data-testid="stPopoverButton"] {{
    min-height: 30px !important; padding: 0 10px !important;
    min-width: 0 !important; width: 100% !important; }}
.st-key-inv_mov_rango [data-testid="stDateInputField"],
.st-key-inv_mov_rango [data-baseweb="input"] {{ background: {BLANCO} !important; }}
"""


def _clase(v):
    return "cero" if abs(v) < 0.5 else ("pos" if v > 0 else "neg")


def tabla_tipos_html(M):
    """La tabla por tipo de documento, con un renglón por grupo."""
    esc = html.escape
    filas = []
    for g, nombre in kardex.GRUPOS:
        t = M.por_tipo[M.por_tipo["grupo"] == g]
        if t.empty:
            continue
        filas.append(f'<tr class="g"><td colspan="5">{esc(nombre)}</td></tr>')
        for r in t.itertuples():
            notas = []
            if r.movs_sin_costo:
                notas.append(f"{int(r.movs_sin_costo):,} sin costo")
            if r.anul:
                notas.append(f"{int(r.anul):,} anulad"
                             + ("as" if r.anul != 1 else "a"))
            nota = (f' <span class="nota">· {" · ".join(notas)}</span>'
                    if notas else "")
            clase = ' class="alerta"' if r.movs_sin_costo else ""
            ent = _soles(r.val_in) if abs(r.val_in) >= 0.5 else "—"
            sal = _soles(r.val_out) if abs(r.val_out) >= 0.5 else "—"
            filas.append(
                f'<tr{clase}><td title="{esc(nombre_propio(r.nombre))}">'
                f'{esc(nombre_propio(r.nombre) or r.tipo)}{nota}</td>'
                f'<td>{ent}</td><td>{sal}</td>'
                f'<td class="{_clase(r.neto)}">{_soles(r.neto, True)}</td>'
                f'<td class="nota">{int(r.movs):,}</td></tr>')
    pt = M.por_tipo
    filas.append(
        f'<tr class="tot"><td>TOTAL</td><td>{_soles(pt["val_in"].sum())}</td>'
        f'<td>{_soles(pt["val_out"].sum())}</td>'
        f'<td class="{_clase(pt["neto"].sum())}">'
        f'{_soles(pt["neto"].sum(), True)}</td>'
        f'<td>{int(pt["movs"].sum()):,}</td></tr>')
    return ('<div class="inv-mov-caja"><table class="inv-mov-t"><thead><tr>'
            '<th>Tipo de documento</th><th>Entró</th><th>Salió</th>'
            '<th>Neto</th><th>Movs.</th></tr></thead><tbody>'
            + "".join(filas) + "</tbody></table></div>")


_COLS_AREA = (("compras", "Compras"), ("entre", "Entre áreas"),
              ("produccion", "Producción y porcion."), ("ventas", "Ventas"),
              ("ajustes", "Ajustes"), ("salidas", "Notas de salida"),
              ("otros", "Otros"))


def tabla_areas_html(M, rot_ini, rot_fin):
    """La misma cuenta, una fila por área: cada fila suma de izquierda a
    derecha. «Otros» sólo si alguna área lo tiene."""
    esc = html.escape
    pa = M.por_area
    cols = [(g, n) for g, n in _COLS_AREA
            if g != "otros" or pa[g].abs().sum() >= 0.5]
    cab = ("<th>Área</th>"
           f'<th class="punta">Stock {esc(rot_ini)}</th>'
           + "".join(f"<th>{esc(n)}</th>" for _, n in cols)
           + "<th>Valori&shy;zación</th>"
           f'<th class="punta">Stock {esc(rot_fin)}</th>')

    def celdas(r, total=False):
        out = [f'<td class="punta">{_soles(r["ini"])}</td>']
        out += [f'<td class="{_clase(r[g])}">'
                f'{_soles(r[g], True) if abs(r[g]) >= 0.5 else "—"}</td>'
                for g, _ in cols]
        out.append(f'<td class="{_clase(r["valorizacion"])}">'
                   f'{_soles(r["valorizacion"], True)}</td>')
        out.append(f'<td class="punta">{_soles(r["fin"])}</td>')
        return "".join(out)

    filas = [f'<tr><td title="{esc(nombre_propio(r["area"]))}">'
             f'{esc(nombre_propio(r["area"]))}</td>{celdas(r)}</tr>'
             for _, r in pa.iterrows()]
    tot = {"ini": M.ini, "fin": M.fin, "valorizacion": M.valorizacion,
           **M.netos}
    filas.append(f'<tr class="tot"><td>TOTAL</td>{celdas(tot, True)}</tr>')
    return ('<div class="inv-mov-caja"><table class="inv-mov-t"><thead><tr>'
            + cab + "</tr></thead><tbody>" + "".join(filas)
            + "</tbody></table></div>")


def _aviso_sin_costo(M):
    """La franja que acusa las ventas que salieron sin costo, con la lista
    en un panel. Nada si no hubo."""
    sc = M.sin_costo
    if sc.empty:
        return
    n_movs = int(sc["movs"].sum())
    valor = float(sc["valor_hoy"].sum())
    n_prods = int(sc["producto"].nunique())
    with st.container(key="inv_mov_alerta"):
        # columnas-internas: el texto del aviso y su botón, en un renglón
        # (en un contenedor horizontal el texto pide el ancho entero y el
        # botón bajaba a una fila propia).
        c_txt, c_btn = st.columns([7, 1.3], vertical_alignment="center")
    with c_txt:
        st.markdown(
            f"**Vendido sin costo:** {n_movs:,} ventas de {n_prods} "
            f"producto{'s' if n_prods != 1 else ''} salieron del kardex a "
            f"S/ 0 —se vendieron antes de recibirlos, con el precio en "
            f"cero—. A su precio de hoy, ≈ {_soles(valor)} que no llegaron "
            f"al costo del período.")
    with c_btn:
        with st.popover("Ver productos", key="inv_mov_pop_sin_costo",
                        use_container_width=True):
            filas = "".join(
                f"<tr><td>{html.escape(r.producto)}</td>"
                f"<td>{html.escape(nombre_propio(r.area))}</td>"
                f"<td>{int(r.movs):,}</td><td>{r.cant:,.2f}</td>"
                f"<td>{_soles(r.valor_hoy)}</td></tr>"
                for r in sc.itertuples())
            st.markdown(
                '<table class="inv-mov-t inv-mov-pop"><thead><tr><th>Producto</th>'
                "<th>Área</th><th>Ventas</th><th>Cantidad</th>"
                "<th>A precio de hoy</th></tr></thead><tbody>"
                + filas + "</tbody></table>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# LA SECCIÓN
# ═══════════════════════════════════════════════════════════════════════

def seccion_movimientos(d, *, col_cod_area, col_cod, col_area, col_prod,
                        col_fam=None, col_punit=None):
    """La tarjeta entera: la fila de filtros (período, áreas, familias,
    buscador y Por tipo / Por área), el título y la vista."""
    st.markdown("<style>" + css_filtros("inv_mov", _K_BUSCAR)
                + CSS_MOVIMIENTOS + "</style>", unsafe_allow_html=True)
    if not (col_cod_area and col_cod and col_area and col_prod):
        st.info("El parquet de stock no trae los códigos de área y de "
                "producto: sin ellos no hay cómo cruzarlo con el kardex.")
        return
    rango = data.rango_fechas(kardex.ARCHIVO, kardex.COL_FECHA)
    if not rango:
        st.info("Falta el kardex: la consulta «kardex» del Sheet todavía no "
                "llegó a la app.")
        return
    desde_min, tope = max(rango[0], kardex.INICIO), rango[1]
    if _K_RANGO not in st.session_state:
        st.session_state[_K_RANGO] = periodo_por_defecto(desde_min, tope)
    # El valor de un `date_input` tiene que caer entre sus límites: el
    # kardex nuevo puede correr el tope.
    _v = tuple(st.session_state[_K_RANGO] or ())
    st.session_state[_K_RANGO] = tuple(min(max(f, desde_min), tope)
                                       for f in _v) or (desde_min, tope)

    ops_area = sorted(set(_texto(d[col_area])) - {""})
    ops_fam = sorted(set(_texto(d[col_fam])) - {""}) if col_fam else []
    recortar_seleccion(_K_AREAS, ops_area)
    recortar_seleccion(_K_FAMILIAS, ops_fam)

    # columnas-internas: los cinco controles de la tarjeta, en su renglón
    # de arriba, como la fila de Productos.
    c_per, c_area, c_fam, c_q, c_vista = st.columns(
        [1.5, 1.35, 1.5, 1.9, 1.55], vertical_alignment="center")
    with c_per:
        sel = st.date_input("Período", key=_K_RANGO, min_value=desde_min,
                            max_value=tope, format="DD/MM/YYYY",
                            label_visibility="collapsed")
    filtro_en_panel(
        c_area, "area",
        _etiqueta(st.session_state.get(_K_AREAS), "áreas", nombre_propio),
        lambda: seleccion_en_panel(st.pills, "Área", _K_AREAS, ops_area,
                                   selection_mode="multi",
                                   format_func=_rotulo_area,
                                   label_visibility="collapsed"),
        prefijo="inv_mov")
    if col_fam:
        filtro_en_panel(
            c_fam, "familia",
            _etiqueta(st.session_state.get(_K_FAMILIAS), "familias",
                      nombre_propio),
            lambda: seleccion_en_panel(st.pills, "Familia", _K_FAMILIAS,
                                       ops_fam, selection_mode="multi",
                                       format_func=nombre_propio,
                                       label_visibility="collapsed"),
            prefijo="inv_mov")
    with c_q:
        texto = st.text_input("Buscar producto", key=_K_BUSCAR,
                              placeholder="Buscar producto o código…",
                              label_visibility="collapsed")
    with c_vista:
        vista = st.segmented_control(
            "Ver", _VISTAS, default=_VISTAS[0], key=_K_VISTA,
            label_visibility="collapsed") or _VISTAS[0]

    # Mientras se elige el rango, el calendario devuelve una sola fecha:
    # se lee como un día.
    sel = tuple(sel) if isinstance(sel, (list, tuple)) else (sel,)
    if not sel:
        return
    desde, hasta = sel[0], sel[-1]
    mov = data.movimientos_kardex(desde, hasta)
    foto_ini = data.stock_al(kardex.momento(desde - dt.timedelta(days=1), 23))
    foto_fin = data.stock_al(kardex.momento(hasta, 23))
    if mov is None or foto_ini is None or foto_fin is None:
        st.info("No se pudo leer el kardex. Probá de nuevo en un momento.")
        return
    M = armar_movimientos(
        d, mov, foto_ini, foto_fin, col_cod_area=col_cod_area, col_cod=col_cod,
        col_area=col_area, col_prod=col_prod, col_fam=col_fam,
        col_punit=col_punit, areas=st.session_state.get(_K_AREAS) or [],
        familias=st.session_state.get(_K_FAMILIAS) or [], texto=texto)

    dia_ini = desde - dt.timedelta(days=1)
    rot_ini = _fecha_corta(dia_ini, con_ano=dia_ini.year != hasta.year)
    rot_fin = _fecha_corta(hasta)
    n_areas = int((M.por_area[[g for g, _ in kardex.GRUPOS]].abs()
                   .sum(axis=1) > 0.5).sum())
    st.markdown(
        f'<div class="inv-rank-tit" style="margin:0">'
        f'{"Por qué cambió el stock" if vista == _VISTAS[0] else "Por qué cambió el stock, área por área"}'
        f' <span class="inv-rank-tit-n">del {rot_ini} al '
        f'{_fecha_corta(hasta, con_ano=True)} · {M.movs:,} movimientos · '
        f'{n_areas} área{"s" if n_areas != 1 else ""}</span></div>',
        unsafe_allow_html=True)

    if M.por_tipo.empty and abs(M.ini) < 0.5 and abs(M.fin) < 0.5:
        st.info("Nada que mostrar con estos filtros.")
        return

    if vista == _VISTAS[0]:
        # columnas-internas: la cascada y su tabla, en la misma tarjeta.
        c_fig, c_tab = st.columns([1.05, 1], gap="medium")
        with c_fig:
            st.plotly_chart(fig_cascada(M, rot_ini, rot_fin),
                            key="inv_mov_cascada",
                            config={"displaylogo": False,
                                    "displayModeBar": False})
        with c_tab:
            st.markdown(tabla_tipos_html(M), unsafe_allow_html=True)
    else:
        st.markdown(tabla_areas_html(M, rot_ini, rot_fin),
                    unsafe_allow_html=True)
        st.markdown(
            '<div class="inv-mov-nota"><b>Entre áreas</b> suma cero en el '
            "total y explica cada área. <b>Valorización</b>: lo que cambió el "
            "valor sin que se moviera la cantidad (el precio promedio, con "
            "stock negativo o en cero).</div>", unsafe_allow_html=True)
    _aviso_sin_costo(M)
