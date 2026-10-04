"""graficos._consumo_html — la página de «Consumo según recetas» (regla #558).

La sección entera —el resumen de arriba, la TABLA DINÁMICA (insumo ›
preparación › plato, por semana, día, mes, día de la semana o turno), el
RESUMEN (la tabla de insumos y la ficha del elegido) y CONTRA COMPRAS (lo
comprado del rango al lado de lo que explican las ventas, regla #560)— es
UN iframe con todo el dato adentro, y todo lo que hace el usuario pasa en el navegador:
desplegar, cambiar columnas, buscar, prender o apagar la venta interna. Nada
de eso vuelve a Python. Es lo que se aprobó sobre el mockup, y es la única
forma de que desplegar sea instantáneo: con widgets, cada clic sería una
corrida de 3 a 6 segundos.

Por qué no AG Grid: las filas desplegables (tree data, master/detail) son de
la versión Enterprise, que está descartada, y cada grilla cuesta 1,28 MB y
un segundo de navegador (regla #540).

EL ALTO LO PONE EL IFRAME MISMO. Mide su documento y se escribe el alto en
el elemento `<iframe>` del padre (mismo origen: `st.iframe` con `srcdoc`),
con `!important` porque `estilos/_00_base.py` fuerza a TODO iframe a alto 0
—son los de las inyecciones invisibles—. La excepción de esta sección vive
en `estilos/_80_cards.py`. Adentro sólo se deslizan las TABLAS: la tarjeta
mide su contenido y lo que sobra lo scrollea la página (regla #382).

Los colores llegan de `tema.py` por `pagina()`: el iframe no hereda las
variables CSS de la app.
"""

import json

import tema

_TOKENS = {
    "acento": tema.ACENTO,
    "acento-texto": tema.ACENTO_TEXTO,
    "lav": tema.LAVANDA_FONDO,
    "lav-borde": tema.LAVANDA_BORDE,
    "lav-fila": tema.LAVANDA_SELECCION,
    "lav-foco": tema.LAVANDA_FOCO,
    "fondo": tema.BLANCO,
    "gris-fondo": tema.GRIS_FONDO,
    "cabecera": tema.GRIS_FONDO_CABECERA,
    "borde": tema.GRIS_BORDE,
    "linea": tema.GRIS_LINEA,
    "texto": tema.TEXTO_PRINCIPAL,
    "texto-2": tema.GRIS_TEXTO_MEDIO,
    "suave": tema.GRIS_TEXTO,
    "suave-2": tema.GRIS_TEXTO_SUAVE,
    "adv-fondo": tema.ADVERTENCIA_FONDO,
    "adv-borde": tema.ADVERTENCIA_BORDE,
    "adv-texto": tema.ADVERTENCIA_TEXTO,
    "ok-fondo": tema.EXITO_FONDO,
    "ok": tema.EXITO,
    "c-receta": tema.ACENTO,
    "c-porc": tema.PALETA_SERIES[6],
    "c-directo": tema.GRIS_TEXTO_SUAVE,
    "c-mixto": tema.LAVANDA_FOCO,
}


def pagina(datos):
    """El HTML completo del iframe, con `datos` (lo que arma
    `movimientos_consumo.datos_de_la_vista`) adentro."""
    raiz = "\n".join(f"  --{k}: {v};" for k, v in _TOKENS.items())
    js = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    # Un «</» adentro de un <script> lo cierra: los nombres de productos no lo
    # traen, pero un nombre con «</script>» no puede romper la página.
    js = js.replace("</", "<\\/")
    return (_HTML.replace("/*__TOKENS__*/", raiz)
                 .replace("/*__DATOS__*/null", js))


_HTML = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap');
:root {
/*__TOKENS__*/
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--fondo); color: var(--texto); }
body { font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; font-size: 14px; line-height: 1.45; overflow: hidden; }
.num { font-variant-numeric: tabular-nums; }
.eyebrow { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--suave); }
.sub { color: var(--suave); font-size: 13px; }
.app { display: grid; gap: 14px; padding: 2px 2px 10px; }
[hidden] { display: none !important; }

/* resumen de arriba */
.resumen { display: grid; grid-template-columns: minmax(200px, 260px) minmax(0, 1fr) minmax(240px, 320px); border: 1px solid var(--borde); border-radius: 10px; }
.resumen > div { padding: 12px 16px; }
.resumen > div + div { border-left: 1px solid var(--borde); }
.grande { font-size: 26px; font-weight: 700; letter-spacing: -0.01em; margin-top: 2px; }
.barra { display: flex; height: 12px; border-radius: 6px; overflow: hidden; background: var(--linea); margin-top: 10px; }
.barra span { display: block; height: 100%; }
.leyenda { display: flex; flex-wrap: wrap; gap: 4px 16px; margin-top: 8px; font-size: 12.5px; color: var(--texto-2); }
.leyenda i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
.leyenda b { font-weight: 600; color: var(--texto); }
.dias-res { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; align-items: end; height: 56px; margin-top: 8px; }
.dr { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 3px; height: 100%; font-size: 11px; color: var(--suave); }
.dr i { display: block; width: 100%; max-width: 26px; border-radius: 3px 3px 0 0; background: var(--c-receta); opacity: 0.4; min-height: 2px; }
.dr.pico i { opacity: 1; }
.dr.pico span { color: var(--texto); font-weight: 600; }
.cuando-txt { margin-top: 6px; font-size: 12.5px; color: var(--texto-2); }

/* barra de pestañas */
.barra-vistas { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 8px 16px; border-bottom: 1px solid var(--borde); }
.vistas { display: flex; gap: 4px; }
.vistas button { height: 36px; padding-inline: 14px; border: 0; border-bottom: 2px solid transparent; margin-bottom: -1px; background: none; color: var(--suave); font: inherit; font-weight: 600; cursor: pointer; }
.vistas button[aria-selected="true"] { color: var(--acento-texto); border-bottom-color: var(--acento); }
.vistas button:focus-visible { outline: 2px solid var(--acento); outline-offset: -2px; }
.der { display: flex; align-items: center; gap: 12px; padding-bottom: 6px; }
.interruptor { position: relative; display: inline-flex; align-items: center; gap: 8px; height: 30px; padding-inline: 10px 12px; border: 1px solid var(--borde); border-radius: 8px; background: var(--fondo); color: var(--texto-2); font-weight: 500; font-size: 13px; cursor: pointer; user-select: none; }
.interruptor input { position: absolute; opacity: 0; width: 1px; height: 1px; margin: 0; }
.interruptor small { color: var(--suave); font-weight: 400; font-size: 12px; }
.riel { position: relative; flex: none; width: 28px; height: 16px; border-radius: 999px; background: var(--borde); }
.riel::after { content: ""; position: absolute; top: 2px; left: 2px; width: 12px; height: 12px; border-radius: 50%; background: var(--fondo); box-shadow: 0 1px 2px rgba(24, 24, 29, 0.25); }
.interruptor input:checked + .riel { background: var(--acento); }
.interruptor input:checked + .riel::after { transform: translateX(12px); }
.interruptor input:focus-visible + .riel { outline: 2px solid var(--acento); outline-offset: 2px; }
@media (prefers-reduced-motion: no-preference) { .riel, .riel::after { transition: background-color 120ms ease, transform 120ms ease; } }

/* controles */
.card-h { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px 16px; }
.card-h h2 { margin: 0; font-size: 15px; font-weight: 600; }
.tit { display: grid; gap: 2px; }
.ctrls { display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; }
.ver { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; }
.seg { display: inline-flex; border: 1px solid var(--borde); border-radius: 8px; overflow: hidden; background: var(--fondo); }
.seg button { height: 30px; padding-inline: 12px; border: 0; background: transparent; color: var(--texto-2); font: inherit; font-size: 13px; cursor: pointer; }
.seg button + button { border-left: 1px solid var(--borde); }
.seg button[aria-pressed="true"] { background: var(--lav); color: var(--acento-texto); font-weight: 600; }
.seg button:focus-visible { outline: 2px solid var(--acento); outline-offset: -2px; }
.filtros { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.buscar { height: 32px; width: 280px; max-width: 100%; padding-inline: 10px; border-radius: 8px; border: 1px solid var(--borde); background: var(--fondo); color: var(--texto); font: inherit; }
.buscar:focus-visible, .chipf:focus-visible { outline: 2px solid var(--acento); outline-offset: 1px; }
.chipf { height: 28px; padding-inline: 10px; border-radius: 999px; border: 1px solid var(--borde); background: var(--fondo); color: var(--texto-2); font: inherit; font-size: 12.5px; cursor: pointer; }
.chipf[aria-pressed="true"] { background: var(--lav); border-color: var(--lav-borde); color: var(--acento-texto); font-weight: 600; }
.pie { color: var(--suave); font-size: 12.5px; }

/* tabla dinámica */
.td-wrap { overflow: auto; max-height: var(--alto-tabla, 520px); border: 1px solid var(--borde); border-radius: 8px; }
table.td { border-collapse: separate; border-spacing: 0; width: max-content; min-width: 100%; }
.td th, .td td { padding: 7px 10px; border-bottom: 1px solid var(--linea); white-space: nowrap; }
.td th { position: sticky; top: 0; z-index: 2; background: var(--cabecera); color: var(--suave); text-align: left; font-size: 11px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; vertical-align: bottom; }
.td th .dsub { display: block; font-weight: 500; color: var(--suave-2); letter-spacing: 0; text-transform: none; }
.td th.b, .td td.b { text-align: right; min-width: 58px; }
.td td.b { font-size: 12.5px; color: var(--texto-2); }
.td td.b.pico { font-weight: 700; color: var(--acento-texto); }
.td .c-nom { position: sticky; left: 0; z-index: 1; width: 360px; min-width: 360px; max-width: 360px; white-space: normal; background: var(--fondo); }
.td .c-tot { position: sticky; left: 360px; z-index: 1; min-width: 116px; text-align: right; background: var(--fondo); box-shadow: inset -1px 0 0 var(--borde); }
.td th.c-nom, .td th.c-tot { z-index: 3; background: var(--cabecera); }
.td tbody tr[data-k] { cursor: pointer; }
.td tr.lv1, .td tr.lv1 td.c-nom, .td tr.lv1 td.c-tot { background: var(--gris-fondo); }
.td tr.lvt, .td tr.lvt td.c-nom, .td tr.lvt td.c-tot { background: var(--lav); font-weight: 700; }
.td tbody tr:hover, .td tbody tr:hover td.c-nom, .td tbody tr:hover td.c-tot { background: var(--lav-fila); }
.td tbody tr:focus-visible { outline: 2px solid var(--acento); outline-offset: -2px; }
.td .fila { display: flex; align-items: flex-start; gap: 6px; }
.td .lv1 .fila { padding-left: 22px; }
.td .lv2 .fila { padding-left: 46px; }
.td .flecha { flex: none; width: 16px; height: 20px; display: inline-flex; align-items: center; justify-content: center; color: var(--suave); }
.td .flecha svg { width: 12px; height: 12px; }
@media (prefers-reduced-motion: no-preference) { .td .flecha svg { transition: transform 120ms ease; } }
.td tr.abierto .flecha svg { transform: rotate(90deg); }
.td .txt { min-width: 0; }
.td .lv0 .nm { font-weight: 600; }
.td .lv2 .nm { color: var(--texto-2); }
.td .meta { display: block; font-size: 12px; color: var(--suave); }
.und { color: var(--suave); font-size: 12px; margin-left: 3px; }
.t-rb, .t-po, .t-di, .t-vi, .t-ed { display: inline-block; margin-left: 6px; padding: 1px 7px; border-radius: 999px; font-size: 11px; font-weight: 600; vertical-align: 1px; }
.t-rb { background: var(--lav); color: var(--acento-texto); }
.t-po { background: var(--adv-fondo); color: var(--adv-texto); }
.t-di { background: var(--linea); color: var(--suave); }
.t-vi { background: var(--adv-fondo); color: var(--adv-texto); }
.t-ed { background: transparent; border: 1px solid var(--adv-borde); color: var(--adv-texto); padding: 0 6px; }

/* resumen: tabla + ficha */
.cuerpo { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 16px; align-items: start; }
.caja { border: 1px solid var(--borde); border-radius: 10px; }
.caja > .card-h { padding: 12px 14px 8px; }
.caja > .filtros { padding: 0 14px 10px; }
.tabla-wrap { max-height: var(--alto-tabla, 520px); overflow: auto; border-top: 1px solid var(--borde); }
.tabla-wrap table { width: 100%; border-collapse: collapse; min-width: 560px; }
.tabla-wrap th { position: sticky; top: 0; z-index: 1; background: var(--cabecera); color: var(--suave); text-align: left; font-size: 11px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; padding: 8px 10px; border-bottom: 1px solid var(--borde); vertical-align: bottom; white-space: nowrap; }
.tabla-wrap th.r, .tabla-wrap td.r { text-align: right; }
.tabla-wrap td { padding: 8px 10px; border-bottom: 1px solid var(--linea); vertical-align: middle; }
.tabla-wrap td.r, .tabla-wrap td.dia { white-space: nowrap; }
.tabla-wrap tbody tr { cursor: pointer; }
.tabla-wrap tbody tr:hover { background: var(--lav-fila); }
.tabla-wrap tbody tr[aria-selected="true"] { background: var(--lav); box-shadow: inset 3px 0 0 var(--acento); }
.tabla-wrap tbody tr:focus-visible { outline: 2px solid var(--acento); outline-offset: -2px; }
.rk { color: var(--suave-2); width: 28px; }
.nom { font-weight: 500; }
.fam { color: var(--suave); font-size: 12px; }
.vi { color: var(--adv-texto); font-weight: 600; }
.costo-sub { color: var(--suave); font-size: 12px; margin-top: 1px; }
.th-sub { font-weight: 500; color: var(--suave-2); margin-top: 2px; }
.spark { display: inline-flex; gap: 2px; align-items: flex-end; height: 22px; }
.spark span { width: 7px; background: var(--c-receta); opacity: 0.55; border-radius: 1.5px 1.5px 0 0; }
th.dia, td.dia { text-align: right; padding-inline: 5px !important; width: 46px; }
td.dia { font-size: 12.5px; color: var(--texto-2); }
td.dia.pico { font-weight: 700; color: var(--acento-texto); }
.tira { display: inline-grid; grid-template-columns: repeat(var(--nh, 13), 9px); gap: 2px; height: 18px; vertical-align: middle; }
.tira span { border-radius: 2px; }
.eje { display: grid; grid-template-columns: repeat(var(--nh, 13), 9px); gap: 2px; margin-top: 4px; font-size: 9.5px; font-weight: 500; letter-spacing: 0; color: var(--suave-2); }
.eje span { display: flex; justify-content: center; white-space: nowrap; }
.det-cab { padding: 14px 16px 12px; border-bottom: 1px solid var(--borde); }
.det-cab h2 { margin: 0; font-size: 17px; font-weight: 700; }
.det-cifras { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 8px 16px; margin-top: 8px; }
.det-cifras .grande { font-size: 24px; }
.det-sec { padding: 12px 16px; border-bottom: 1px solid var(--linea); }
.det-sec:last-child { border-bottom: 0; }
.det-sec h3 { margin: 0 0 10px; font-size: 13px; font-weight: 600; color: var(--texto-2); }
.det-sec h3 small { font-size: 12px; font-weight: 400; color: var(--suave); margin-left: 6px; }
.aviso-vi { background: var(--adv-fondo); }
.aviso-vi p { margin: 0; font-size: 12.5px; color: var(--texto-2); }
.aviso-vi b { color: var(--adv-texto); font-weight: 600; }
.fila-bar { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 10px; align-items: center; margin-bottom: 8px; font-size: 13px; }
.fila-bar .lbl { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fila-bar .val { text-align: right; color: var(--texto-2); white-space: nowrap; }
.fila-bar .bg { grid-column: 1 / -1; height: 6px; border-radius: 3px; background: var(--linea); overflow: hidden; }
.fila-bar .bg span { display: block; height: 100%; border-radius: 3px; }
.semanas { display: grid; grid-template-columns: repeat(var(--n, 5), minmax(0, 1fr)); gap: 6px; align-items: end; height: 110px; }
.sem { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; gap: 4px; font-size: 11px; color: var(--suave); }
.sem .col { width: 100%; max-width: 44px; background: var(--c-receta); border-radius: 4px 4px 0 0; opacity: 0.4; min-height: 2px; }
.sem .v { color: var(--texto-2); font-weight: 600; }
.sem.pico .col { opacity: 1; }
.sem.pico > span:last-child { color: var(--texto); font-weight: 600; }
.nota { font-size: 12.5px; color: var(--suave); margin: 8px 0 0; }
.nota b { color: var(--texto-2); font-weight: 600; }
.turnos { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }
.turnos > div { border: 1px solid var(--borde); border-radius: 8px; padding: 8px 12px; }
.turnos .grande { font-size: 18px; }
.mapa { display: grid; gap: 2px; margin-top: 12px; font-size: 10.5px; color: var(--suave); }
.mapa .mc { height: 16px; border-radius: 2px; }
.mapa .mh { display: flex; justify-content: center; }
.mapa .md { align-self: center; }
.rend { display: grid; gap: 10px; }
.rend-item { border: 1px solid var(--borde); border-radius: 8px; padding: 10px 12px; }
.rend-top { display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.rend-top b { font-weight: 600; }
.rend-meta { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; font-size: 12px; color: var(--suave); }
.tag { display: inline-flex; align-items: center; height: 22px; padding-inline: 8px; border-radius: 999px; font-size: 11.5px; font-weight: 600; }
.tag.ok { background: var(--ok-fondo); color: var(--ok); }
.tag.resp { background: var(--adv-fondo); color: var(--adv-texto); }
.tag.rev { background: var(--adv-fondo); color: var(--adv-texto); border: 1px solid var(--adv-borde); }
.real { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.real > div { border: 1px solid var(--borde); border-radius: 8px; padding: 10px 12px; }
.real .grande { font-size: 20px; }
.metodo { color: var(--suave); font-size: 12.5px; margin: 0; }
.metodo b { color: var(--texto-2); font-weight: 600; }
details.metodo summary { cursor: pointer; color: var(--texto-2); font-weight: 600; }
.cc-res { margin: 0; padding: 0 14px 10px; font-size: 13px; color: var(--texto-2); max-width: 120ch; }
.cc-res b { color: var(--texto); font-weight: 600; }
.tabla-wrap tbody tr.sin-ficha { cursor: default; }
.dif { white-space: nowrap; }
.dif.alta { color: var(--adv-texto); font-weight: 600; }
.nota-ed { font-size: 12.5px; color: var(--adv-texto); margin: 8px 0 0; }
details.metodo p { margin: 6px 0 0; max-width: 120ch; }

@media (max-width: 1100px) {
  .resumen { grid-template-columns: minmax(200px, 260px) minmax(0, 1fr); }
  .resumen > div:nth-child(3) { grid-column: 1 / -1; border-left: 0; border-top: 1px solid var(--borde); }
}
@media (max-width: 900px) {
  .cuerpo, .resumen { grid-template-columns: minmax(0, 1fr); }
  .resumen > div + div { border-left: 0; border-top: 1px solid var(--borde); }
}
@media (max-width: 600px) {
  .td .c-nom { width: 190px; min-width: 190px; max-width: 190px; }
  .td .c-tot { left: 190px; min-width: 92px; }
  .td .lv1 .fila { padding-left: 12px; }
  .td .lv2 .fila { padding-left: 26px; }
}
</style></head>
<body>
<div class="app">
  <section class="resumen" aria-label="Resumen del período">
    <div>
      <div class="eyebrow">Costo de los insumos de compra</div>
      <div class="grande num" id="k-costo"></div>
      <div class="sub num" id="k-sub"></div>
    </div>
    <div>
      <div class="eyebrow">Cómo llegan al plato</div>
      <div class="barra" id="k-barra"></div>
      <div class="leyenda num" id="k-leyenda"></div>
    </div>
    <div>
      <div class="eyebrow">Cuándo se consume · costo por día</div>
      <div class="dias-res" id="k-dias"></div>
      <div class="cuando-txt num" id="k-cuando"></div>
    </div>
  </section>

  <div class="barra-vistas">
    <nav class="vistas" id="vistas" role="tablist" aria-label="Vista">
      <button type="button" role="tab" data-v="tabla">Tabla dinámica</button>
      <button type="button" role="tab" data-v="resumen">Resumen</button>
      <button type="button" role="tab" data-v="compras">Contra compras</button>
    </nav>
    <div class="der">
      <label class="interruptor num" id="vi-lbl"><input type="checkbox" id="vi" checked><span class="riel" aria-hidden="true"></span><span>Venta interna <small id="vi-cuenta"></small></span></label>
    </div>
  </div>

  <section id="dinamica" aria-label="Tabla dinámica">
    <div class="card-h" style="margin-bottom:10px">
      <div class="tit">
        <h2>Insumos de compra</h2>
        <span class="sub">Clic en un insumo: por qué preparaciones llega. Clic en una preparación: en qué platos.</span>
      </div>
      <div class="ctrls">
        <div class="ver"><span class="eyebrow">Columnas</span><div class="seg" role="group" aria-label="Columnas" id="td-cols"></div></div>
        <div class="ver"><span class="eyebrow">Valores</span><div class="seg" role="group" aria-label="Valores" id="td-val">
          <button type="button" data-x="cant">Cantidad</button><button type="button" data-x="soles">Soles</button>
        </div></div>
      </div>
    </div>
    <div class="filtros" style="margin-bottom:10px">
      <input class="buscar" id="td-buscar" type="search" placeholder="Buscar insumo, preparación o plato…" aria-label="Buscar insumo, preparación o plato">
      <div id="td-fams" style="display:flex;flex-wrap:wrap;gap:6px"></div>
      <button class="chipf" type="button" id="td-plegar">Plegar todo</button>
    </div>
    <div class="td-wrap"><table class="td"><thead id="td-cab"></thead><tbody id="td-filas"></tbody></table></div>
    <div class="pie num" id="td-pie" style="margin-top:8px"></div>
  </section>

  <section id="vista-resumen" class="cuerpo" hidden>
    <div class="caja">
      <div class="card-h">
        <div class="tit"><h2>Insumos de compra</h2><span class="sub">Ordenados por costo · clic en una fila para ver su detalle</span></div>
        <div class="ver"><span class="eyebrow">Ver por</span><div class="seg" role="group" aria-label="Ver el consumo por" id="modos">
          <button type="button" data-m="semanas">Semana</button><button type="button" data-m="dias">Día</button><button type="button" data-m="horas">Hora</button>
        </div></div>
      </div>
      <div class="filtros">
        <input class="buscar" id="buscar" type="search" placeholder="Buscar insumo…" aria-label="Buscar insumo" style="width:220px">
        <div id="familias" style="display:flex;flex-wrap:wrap;gap:6px"></div>
      </div>
      <div class="tabla-wrap"><table><thead id="cabeza"></thead><tbody id="filas"></tbody></table></div>
      <div class="pie num" id="pie" style="padding:8px 14px"></div>
    </div>
    <aside class="caja" id="detalle" aria-live="polite"></aside>
  </section>

  <section id="vista-compras" hidden>
    <div class="caja">
      <div class="card-h">
        <div class="tit"><h2>Lo comprado contra lo que explican las ventas</h2><span class="sub" id="cc-sub"></span></div>
      </div>
      <p class="cc-res num" id="cc-resumen"></p>
      <div class="filtros">
        <input class="buscar" id="cc-buscar" type="search" placeholder="Buscar insumo…" aria-label="Buscar insumo" style="width:220px">
        <div id="cc-filtro" style="display:flex;flex-wrap:wrap;gap:6px"></div>
      </div>
      <div class="tabla-wrap"><table><thead id="cc-cabeza"></thead><tbody id="cc-filas"></tbody></table></div>
      <div class="pie num" id="cc-pie" style="padding:8px 14px"></div>
    </div>
  </section>

  <details class="metodo" id="metodo">
    <summary>Cómo se calcula</summary>
    <p id="metodo-txt"></p>
  </details>
</div>

<script>
const D = /*__DATOS__*/null;
const P = D.periodo;
const MESES = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
const DIAS = ['lun','mar','mié','jue','vie','sáb','dom'];
const DIAS_L = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo'];
const fecha = s => { const [a, m, d] = s.slice(0, 10).split('-').map(Number); return { a, m, d }; };
const fCorta = s => { const f = fecha(s); return `${f.d} ${MESES[f.m - 1]}`; };
const fMes = s => { const f = fecha(s); return `${MESES[f.m - 1]} ${f.a}`; };
const corta = u => ({ KILOS: 'kg', LITROS: 'L', UND: 'und', UNIDAD: 'und' }[u] || String(u || '').toLowerCase());
const n0 = v => Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 });
const dec = (v, d) => Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
// Una cantidad o un promedio: los decimales dependen del tamaño, no de la unidad.
const prom = v => !v ? '—' : dec(v, Math.abs(v) >= 100 ? 0 : (Math.abs(v) >= 10 ? 1 : 2));
const sol = v => 'S/ ' + (Math.abs(v) >= 10 ? n0(v) : dec(v, 2));
const fS = v => !v ? '—' : (Math.abs(v) >= 10 ? n0(v) : dec(v, 1));
const pct = (v, t) => t ? dec(100 * v / t, 1) + '%' : '—';
const pct0 = (v, t) => t ? Math.round(100 * v / t) + '%' : '—';
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const cap = s => s ? s[0] + s.slice(1).toLowerCase() : '';
const suma = a => { let s = 0; for (const x of a) s += x; return s; };
const tono = (r, tope, fondo) => r <= 0 ? fondo : `color-mix(in srgb, var(--acento) ${Math.round(tope * r)}%, ${fondo})`;
const esAlmuerzo = h => h >= 6 && h < 17;
const CHEV = '<svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 2.5 8 6l-3.5 3.5"/></svg>';

// ── estado de la vista (se recuerda mientras dure la pestaña) ──
const K_UI = 'consumo_recetas_ui';
let UI = { vista: 'tabla', tdCols: 'semana', tdVal: 'cant', vi: true, modo: 'dias', sel: null };
try { Object.assign(UI, JSON.parse(window.parent.sessionStorage.getItem(K_UI) || '{}')); } catch (e) {}
if (!['tabla', 'resumen', 'compras'].includes(UI.vista)) UI.vista = 'tabla';
const guardar = () => { try { window.parent.sessionStorage.setItem(K_UI, JSON.stringify(UI)); } catch (e) {} };

// ── el alto: lo mide el iframe y se lo escribe a su <iframe> ──
(function () {
  let altoPadre = 800;
  try { altoPadre = window.parent.innerHeight || 800; } catch (e) {}
  document.documentElement.style.setProperty('--alto-tabla', Math.max(320, Math.round(altoPadre * 0.62)) + 'px');
  const fr = window.frameElement;
  if (!fr) return;
  let ultimo = 0;
  const medir = () => {
    const h = Math.ceil(document.documentElement.getBoundingClientRect().height);
    if (Math.abs(h - ultimo) > 1) { ultimo = h; fr.style.setProperty('height', h + 'px', 'important'); }
  };
  new ResizeObserver(medir).observe(document.body);
  medir();
})();

// ── las cubetas ──
const NF = P.finas.length, NM = P.meses.length, NH = D.horas.length;
const dUTC = s => Date.parse(s + 'T00:00:00Z');
const lunesDe = s => { const t = dUTC(s); const d = (new Date(t).getUTCDay() + 6) % 7; return t - d * 864e5; };
// Día por día, la semana de cada día; por semana, cada cubeta ya es una semana.
const LUNES = [...new Set(P.finas.map(lunesDe))].sort((a, b) => a - b);
const semIdx = P.grano === 'dia' ? P.finas.map(f => LUNES.indexOf(lunesDe(f))) : P.finas.map((_, i) => i);
const NS = P.grano === 'dia' ? LUNES.length : NF;
const semLbl = LUNES.map(t => { const s = new Date(t).toISOString().slice(0, 10); return s < P.desde ? P.desde : s; });
const diasSem = LUNES.map(t => { let n = 0; for (let k = 0; k < 7; k++) { const s = new Date(t + k * 864e5).toISOString().slice(0, 10); if (s >= P.desde && s <= P.hasta) n++; } return n; });
const semParcial = i => P.grano === 'dia' ? diasSem[i] < 7 : (i === 0 && lunesDe(P.desde) < dUTC(P.desde)) || (i === NF - 1 && lunesDe(P.hasta) + 6 * 864e5 > dUTC(P.hasta));
const semTitulo = i => P.grano === 'dia' ? semLbl[i] : (i === 0 ? P.desde : P.finas[i]);
const PLATOS = D.platos;
const CAMINOS = D.caminos;
const CAM_GRUPO = c => c === 'directo en el plato' ? 'directo' : (c === 'receta base' ? 'receta' : (c === 'porcionamiento' ? 'porc' : 'mixto'));
const GRUPOS = {
  porc: { txt: 'Por porcionamiento', col: 'var(--c-porc)' },
  receta: { txt: 'Dentro de recetas base', col: 'var(--c-receta)' },
  directo: { txt: 'Directo en el plato', col: 'var(--c-directo)' },
  mixto: { txt: 'Porcionamiento y receta base', col: 'var(--c-mixto)' },
};
const prepNombre = p => p ? (D.preps[p] ? D.preps[p][0] : p) : 'Directo en la receta del plato';
const prepEtiqueta = p => {
  if (!p) return `${esc(prepNombre(p))}<span class="t-di">directo</span>`;
  const t = D.preps[p] ? D.preps[p][1] : '';
  return `${esc(prepNombre(p))}<span class="${t === 'porcionado' ? 't-po' : 't-rb'}">${t || 'preparación'}</span>`;
};

// ── el árbol, con o sin venta interna ──
const ARBOL = {};
const vec = () => ({ v: new Float64Array(NF), m: new Float64Array(NM), ds: new Float64Array(7), t: new Float64Array(2), tot: 0 });
const sumar = (x, f) => {
  for (const [i, q] of f[6]) x.v[i] += q;
  for (const [i, q] of f[7]) x.m[i] += q;
  for (let k = 0; k < 7; k++) x.ds[k] += f[8][k];
  x.t[0] += f[9][0]; x.t[1] += f[9][1];
  x.tot += f[9][0] + f[9][1];
};
function arbolDe(conVI) {
  const k = conVI ? 'si' : 'no';
  if (ARBOL[k]) return ARBOL[k];
  const ins = new Map();
  for (const f of D.filas) {
    const [cod, prep, pid, n1, ci, ui] = f;
    const interna = PLATOS[pid][1];
    if (!conVI && interna) continue;
    let a = ins.get(cod);
    if (!a) ins.set(cod, a = Object.assign(vec(), { cod, preps: new Map(), cam: new Map(), porc: new Map(), vi: 0, pl: new Map() }));
    let b = a.preps.get(prep);
    if (!b) a.preps.set(prep, b = Object.assign(vec(), { prep, platos: new Map() }));
    let c = b.platos.get(pid);
    if (!c) b.platos.set(pid, c = Object.assign(vec(), { pid, n1: new Set() }));
    if (n1) c.n1.add(n1);
    sumar(a, f); sumar(b, f); sumar(c, f);
    const q = f[9][0] + f[9][1];
    const g = CAM_GRUPO(CAMINOS[ci]);
    a.cam.set(g, (a.cam.get(g) || 0) + q);
    if (ui === 2) a.porc.set(prep, (a.porc.get(prep) || 0) + q);
    if (interna) a.vi += q;
    a.pl.set(pid, (a.pl.get(pid) || 0) + q);
  }
  const lista = [...ins.values()].map(a => Object.assign(a, { costo: a.tot * D.insumos[a.cod][2] }))
    .sort((x, y) => y.costo - x.costo);
  return (ARBOL[k] = { ins, lista });
}
let A = arbolDe(UI.vi);

// ── resumen de arriba ──
function pintarResumen() {
  const costo = suma(A.lista.map(a => a.costo));
  document.getElementById('k-costo').textContent = sol(costo);
  document.getElementById('k-sub').textContent =
    `${n0(A.lista.length)} insumos · recetas abiertas hasta ${D.resumen.niveles} niveles` + (UI.vi ? '' : ' · sin venta interna');
  const g = new Map();
  for (const a of A.lista) for (const [k, q] of a.cam) g.set(k, (g.get(k) || 0) + q * D.insumos[a.cod][2]);
  const gr = [...g.entries()].sort((x, y) => y[1] - x[1]);
  const tot = suma(gr.map(x => x[1]));
  document.getElementById('k-barra').innerHTML = gr.map(([k, v]) =>
    `<span style="width:${100 * v / (tot || 1)}%;background:${GRUPOS[k].col}" title="${GRUPOS[k].txt}"></span>`).join('');
  document.getElementById('k-leyenda').innerHTML = gr.map(([k, v]) =>
    `<span><i style="background:${GRUPOS[k].col}"></i>${GRUPOS[k].txt} <b>${pct(v, tot)}</b></span>`).join('');
  const cd = [0, 0, 0, 0, 0, 0, 0]; let al = 0, ce = 0;
  for (const a of A.lista) {
    const pr = D.insumos[a.cod][2];
    for (let k = 0; k < 7; k++) cd[k] += a.ds[k] * pr;
    al += a.t[0] * pr; ce += a.t[1] * pr;
  }
  const cdp = cd.map((v, k) => P.n_dia[k] ? v / P.n_dia[k] : 0);
  const mx = Math.max(...cdp, 1e-9), mn = Math.min(...cdp.filter((_, k) => P.n_dia[k])), ip = cdp.indexOf(mx), im = cdp.indexOf(mn);
  document.getElementById('k-dias').innerHTML = cdp.map((v, i) =>
    `<div class="dr${i === ip ? ' pico' : ''}" title="${DIAS_L[i]}: ${sol(v)} por día en promedio"><i style="height:${Math.max(2, 40 * v / mx)}px"></i><span>${DIAS[i]}</span></div>`).join('');
  document.getElementById('k-cuando').innerHTML =
    `El <b>${DIAS_L[ip]}</b> se consume ${sol(mx)} por día; el ${DIAS_L[im]}, ${sol(mn)}. La cena lleva el ${pct0(ce, al + ce)}.`;
}

// ── la venta interna ──
{
  const vi = D.venta_interna;
  document.getElementById('vi-cuenta').textContent = vi.pedidos ? `· ${vi.platos} plato${vi.platos === 1 ? '' : 's'}` : '· no hubo';
  document.getElementById('vi-lbl').title = vi.pedidos
    ? `${vi.nombres.join(', ')}: lo que se produce en casa para Mayta cuenta el día que se PRODUJO, no el que se facturó; igual va por tanda y corre el patrón de días y horas. Es la misma que apaga Ventas › Por hora.`
    : 'En el período no hubo venta interna.';
  const cb = document.getElementById('vi');
  cb.checked = UI.vi;
  cb.addEventListener('change', () => {
    UI.vi = cb.checked; guardar();
    A = arbolDe(UI.vi);
    if (UI.sel && !A.ins.has(UI.sel)) UI.sel = null;
    pintarTodo();
  });
}

// ── pestañas ──
const tabs = document.getElementById('vistas');
function pintarVista() {
  tabs.querySelectorAll('button').forEach(b => b.setAttribute('aria-selected', b.dataset.v === UI.vista));
  document.getElementById('dinamica').hidden = UI.vista !== 'tabla';
  document.getElementById('vista-resumen').hidden = UI.vista !== 'resumen';
  document.getElementById('vista-compras').hidden = UI.vista !== 'compras';
}
tabs.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  UI.vista = b.dataset.v; guardar(); pintarVista();
  if (UI.vista === 'resumen') { pintarFilas(); pintarDetalle(); }
  else if (UI.vista === 'compras') pintarCompras();
  else pintarDinamica();
});

// ═══ TABLA DINÁMICA ═══
const COLS = [['total', 'Total'], ['semana', 'Semana']];
if (P.grano === 'dia') COLS.push(['dia', 'Día']);
if (NM > 1) COLS.push(['mes', 'Mes']);
COLS.push(['dsem', 'Día de la semana'], ['turno', 'Turno']);
if (!COLS.some(c => c[0] === UI.tdCols)) UI.tdCols = 'semana';
document.getElementById('td-cols').innerHTML = COLS.map(([k, t]) => `<button type="button" data-c="${k}">${t}</button>`).join('');
let tdTxt = '', tdFam = 'Todas';
const tdAbiertos = new Set();
function cubetas(x) {
  switch (UI.tdCols) {
    case 'semana': { const s = new Array(NS).fill(0); for (let i = 0; i < NF; i++) s[semIdx[i]] += x.v[i]; return s; }
    case 'dia': return Array.from(x.v);
    case 'mes': return Array.from(x.m);
    case 'dsem': return Array.from(x.ds, (q, k) => P.n_dia[k] ? q / P.n_dia[k] : 0);
    case 'turno': return [x.t[0], x.t[1]];
    default: return [];
  }
}
function tdCabeza() {
  let cols = [];
  if (UI.tdCols === 'semana') cols = Array.from({ length: NS }, (_, i) => `<th class="b">${fCorta(semTitulo(i))}${semParcial(i) ? '*' : ''}<span class="dsub">semana</span></th>`);
  if (UI.tdCols === 'dia') cols = P.finas.map((f, i) => { const x = fecha(f); const d = (new Date(dUTC(f)).getUTCDay() + 6) % 7; return `<th class="b">${DIAS[d]}<span class="dsub">${i === 0 || x.d === 1 ? fCorta(f) : x.d}</span></th>`; });
  if (UI.tdCols === 'mes') cols = P.meses.map(m => `<th class="b">${fMes(m)}<span class="dsub">mes</span></th>`);
  if (UI.tdCols === 'dsem') cols = DIAS.map((d, j) => `<th class="b">${d}<span class="dsub">prom. de ${P.n_dia[j]}</span></th>`);
  if (UI.tdCols === 'turno') cols = ['<th class="b">Almuerzo<span class="dsub">antes de 17 h</span></th>', '<th class="b">Cena<span class="dsub">desde 17 h</span></th>'];
  document.getElementById('td-cab').innerHTML =
    `<tr><th class="c-nom">Insumo de compra › preparación › plato</th><th class="c-tot">${UI.tdVal === 'soles' ? 'Soles' : 'Cantidad'}<span class="dsub">del período</span></th>${cols.join('')}</tr>`;
}
function celdasTD(x, factor) {
  const cs = cubetas(x).map(q => q * factor);
  if (!cs.length) return '';
  const mx = Math.max(...cs, 1e-12);
  const f = UI.tdVal === 'soles' ? fS : prom;
  return cs.map(q => `<td class="b num${q > 0 && q === mx ? ' pico' : ''}" style="background:${tono(q / mx, 22, 'transparent')}">${f(q)}</td>`).join('');
}
function totTD(x, factor, u) {
  const t = x.tot * factor;
  return UI.tdVal === 'soles' ? sol(t) : `${prom(t)}<span class="und">${esc(corta(u))}</span>`;
}
const coincide = s => !tdTxt || String(s).toLowerCase().includes(tdTxt);
const vendidos = x => !x ? '' : `${x % 1 === 0 ? n0(x) : dec(x, 2)} vendidos`;
// La receta de HOY: un plato cuya receta se editó dentro del rango se calcula
// con la nueva aunque se haya vendido antes (regla #560).
const marcaEditada = ed => !ed ? '' :
  `<span class="t-ed" title="La receta se editó el ${fCorta(ed)}: lo vendido antes de esa fecha se calcula con la receta de hoy.">receta editada ${fCorta(ed)}</span>`;
function pintarDinamica(foco) {
  tdCabeza();
  let lista = A.lista;
  const fams = [...new Set(lista.map(a => D.insumos[a.cod][3]))].filter(Boolean).sort();
  if (tdFam !== 'Todas' && !fams.includes(tdFam)) tdFam = 'Todas';
  document.getElementById('td-fams').innerHTML = ['Todas', ...fams].map(f =>
    `<button class="chipf" type="button" aria-pressed="${f === tdFam}" data-f="${esc(f)}">${esc(f === 'Todas' ? f : cap(f))}</button>`).join('');
  if (tdFam !== 'Todas') lista = lista.filter(a => D.insumos[a.cod][3] === tdFam);
  const filasH = [], visibles = [];
  for (const a of lista) {
    const [nom, u, pr, fam, sub] = D.insumos[a.cod];
    const f = UI.tdVal === 'soles' ? pr : 1;
    const preps = [...a.preps.values()].sort((x, y) => y.tot - x.tot);
    let hijosVis = preps, forzado = false;
    if (tdTxt && !coincide(nom)) {
      hijosVis = preps.filter(b => coincide(prepNombre(b.prep)) || [...b.platos.values()].some(c => coincide(PLATOS[c.pid][0])));
      if (!hijosVis.length) continue;
      forzado = true;
    }
    visibles.push(a);
    const k0 = 'i:' + a.cod, ab0 = forzado || tdAbiertos.has(k0);
    filasH.push(`<tr class="lv0${ab0 ? ' abierto' : ''}" data-k="${esc(k0)}" tabindex="0" aria-expanded="${ab0}">
      <td class="c-nom"><div class="fila"><span class="flecha">${CHEV}</span><span class="txt"><span class="nm">${esc(nom)}</span><span class="meta">${esc(cap(fam))} · ${esc(sub || '')} · ${preps.length} preparaci${preps.length === 1 ? 'ón' : 'ones'}</span></span></div></td>
      <td class="c-tot num">${totTD(a, f, u)}</td>${celdasTD(a, f)}</tr>`);
    if (!ab0) continue;
    for (const b of hijosVis) {
      const k1 = 'p:' + a.cod + '|' + b.prep;
      let platos = [...b.platos.values()].sort((x, y) => y.tot - x.tot);
      let forz1 = false;
      if (forzado && !coincide(prepNombre(b.prep))) { platos = platos.filter(c => coincide(PLATOS[c.pid][0])); forz1 = true; }
      const ab1 = forz1 || tdAbiertos.has(k1);
      filasH.push(`<tr class="lv1${ab1 ? ' abierto' : ''}" data-k="${esc(k1)}" tabindex="0" aria-expanded="${ab1}">
        <td class="c-nom"><div class="fila"><span class="flecha">${CHEV}</span><span class="txt"><span class="nm">${prepEtiqueta(b.prep)}</span><span class="meta">${b.platos.size} plato${b.platos.size === 1 ? '' : 's'}</span></span></div></td>
        <td class="c-tot num">${totTD(b, f, u)}</td>${celdasTD(b, f)}</tr>`);
      if (!ab1) continue;
      for (const c of platos) {
        const [pn, vi, vend, ed] = PLATOS[c.pid];
        const enReceta = c.n1.size ? `<span class="meta">en la receta: ${esc([...c.n1].map(prepNombre).join(' · '))}</span>` : '';
        filasH.push(`<tr class="lv2">
          <td class="c-nom"><div class="fila"><span class="txt"><span class="nm">${esc(pn)}</span>${vi ? '<span class="t-vi">venta interna</span>' : ''}${marcaEditada(ed)}<span class="meta num">${vendidos(vend)}</span>${enReceta}</span></div></td>
          <td class="c-tot num">${totTD(c, f, u)}</td>${celdasTD(c, f)}</tr>`);
      }
    }
  }
  if (UI.tdVal === 'soles') {
    const t = vec();
    for (const a of visibles) {
      const p = D.insumos[a.cod][2];
      for (let i = 0; i < NF; i++) t.v[i] += a.v[i] * p;
      for (let i = 0; i < NM; i++) t.m[i] += a.m[i] * p;
      for (let k = 0; k < 7; k++) t.ds[k] += a.ds[k] * p;
      t.t[0] += a.t[0] * p; t.t[1] += a.t[1] * p; t.tot += a.tot * p;
    }
    filasH.unshift(`<tr class="lvt"><td class="c-nom">Total${tdTxt || tdFam !== 'Todas' ? ' de lo filtrado' : ''} · ${visibles.length} insumos</td>
      <td class="c-tot num">${sol(t.tot)}</td>${celdasTD(t, 1)}</tr>`);
  }
  const tb = document.getElementById('td-filas');
  tb.innerHTML = filasH.join('') || `<tr><td class="c-nom" colspan="2">Nada coincide con «${esc(tdTxt)}».</td></tr>`;
  if (foco) { const tr = tb.querySelector(`tr[data-k="${CSS.escape(foco)}"]`); if (tr) tr.focus({ preventScroll: true }); }
  const expl = {
    total: 'Total del período.',
    semana: 'Total de cada semana' + (Array.from({ length: NS }, (_, i) => semParcial(i)).some(Boolean) ? '; * semana incompleta en el rango.' : '.'),
    dia: 'Total de cada día. Desliza a la derecha: el nombre y el total quedan fijos.',
    mes: 'Total de cada mes del rango.',
    dsem: `Promedio por día: lo de todos los lunes del rango entre ${P.n_dia[0]}, lo de los sábados entre ${P.n_dia[5]}.`,
    turno: `Almuerzo: platos pedidos antes de las 17 h, con la hora de cada plato${D.resumen.hora_de_mesa ? ' (hoy, la de la mesa: el parquet no trae la del plato)' : ''}.`,
  }[UI.tdCols];
  document.getElementById('td-pie').textContent = `${visibles.length} de ${A.lista.length} insumos${UI.vi ? '' : ' (sin venta interna)'}. ${expl}` +
    (UI.tdVal === 'soles' ? ' Soles al precio promedio de hoy.' : ' Cada fila va en la unidad de su insumo, la del kardex.');
}
const pintarSegTD = () => {
  document.querySelectorAll('#td-cols button').forEach(b => b.setAttribute('aria-pressed', b.dataset.c === UI.tdCols));
  document.querySelectorAll('#td-val button').forEach(b => b.setAttribute('aria-pressed', b.dataset.x === UI.tdVal));
};
document.getElementById('td-cols').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; UI.tdCols = b.dataset.c; guardar(); pintarSegTD(); pintarDinamica(); });
document.getElementById('td-val').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; UI.tdVal = b.dataset.x; guardar(); pintarSegTD(); pintarDinamica(); });
document.getElementById('td-fams').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; tdFam = b.dataset.f; pintarDinamica(); });
document.getElementById('td-buscar').addEventListener('input', e => { tdTxt = e.target.value.trim().toLowerCase(); pintarDinamica(); });
document.getElementById('td-plegar').addEventListener('click', () => { tdAbiertos.clear(); pintarDinamica(); });
const alternar = tr => { const k = tr.dataset.k; if (!k) return; tdAbiertos.has(k) ? tdAbiertos.delete(k) : tdAbiertos.add(k); pintarDinamica(k); };
document.getElementById('td-filas').addEventListener('click', e => { const tr = e.target.closest('tr[data-k]'); if (tr) alternar(tr); });
document.getElementById('td-filas').addEventListener('keydown', e => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const tr = e.target.closest('tr[data-k]'); if (tr) { e.preventDefault(); alternar(tr); }
});

// ═══ RESUMEN: la tabla de insumos y la ficha ═══
const modos = document.getElementById('modos');
const pintarModos = () => modos.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', b.dataset.m === UI.modo));
modos.addEventListener('click', e => { const b = e.target.closest('button'); if (!b || b.dataset.m === UI.modo) return; UI.modo = b.dataset.m; guardar(); pintarModos(); pintarCabeza(); pintarFilas(); pintarDetalle(); });
let famSel = 'Todas', txt = '';
const famBox = document.getElementById('familias');
function pintarFams() {
  const fams = [...new Set(A.lista.map(a => D.insumos[a.cod][3]))].filter(Boolean).sort();
  if (famSel !== 'Todas' && !fams.includes(famSel)) famSel = 'Todas';
  famBox.innerHTML = ['Todas', ...fams].map(f =>
    `<button class="chipf" type="button" aria-pressed="${f === famSel}" data-f="${esc(f)}">${esc(f === 'Todas' ? f : cap(f))}</button>`).join('');
}
famBox.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; famSel = b.dataset.f; pintarFams(); pintarFilas(); });
document.getElementById('buscar').addEventListener('input', e => { txt = e.target.value.trim().toLowerCase(); pintarFilas(); });
// Con más de 16 semanas (un rango de meses) la tira y la ficha van MES a mes:
// 53 barras no entran en 500px y sus números se pisan.
const LARGO = NS > 16;
const semanasDe = a => { if (LARGO) return Array.from(a.m); const s = new Array(NS).fill(0); for (let i = 0; i < NF; i++) s[semIdx[i]] += a.v[i]; return s; };
const tituloSerie = i => LARGO ? fMes(P.meses[i]) : fCorta(semTitulo(i)) + (semParcial(i) ? '*' : '');
if (LARGO) document.querySelector('#modos button[data-m="semanas"]').textContent = 'Mes';
const diasDe = a => Array.from(a.ds, (q, k) => P.n_dia[k] ? q / P.n_dia[k] : 0);
function horasDe(a) {
  const h = D.horas_ins[a.cod] || [[], []];
  return Array.from({ length: NH }, (_, j) => ((h[0][j] || 0) + (UI.vi ? (h[1][j] || 0) : 0)) / P.n_dias);
}
function mapaDe(a) {
  const m = D.mapa_ins[a.cod] || [[], []];
  const out = Array.from({ length: 7 }, () => new Array(NH).fill(0));
  for (const [d, j, q] of m[0]) out[d][j] += q;
  if (UI.vi) for (const [d, j, q] of m[1]) out[d][j] += q;
  return out.map((fila, d) => fila.map(q => P.n_dia[d] ? q / P.n_dia[d] : 0));
}
const turnosDe = vals => { let al = 0, ce = 0; vals.forEach((v, j) => { if (esAlmuerzo(D.horas[j])) al += v; else ce += v; }); return { al, ce }; };
const cabeza = document.getElementById('cabeza');
function pintarCabeza() {
  const base = `<th class="rk">#</th><th>Insumo</th>` + (UI.modo === 'semanas'
    ? `<th class="r">Cantidad</th><th class="r">Costo</th>`
    : `<th class="r">Cantidad<div class="th-sub">costo</div></th>`);
  const eje = `<div class="eje" aria-hidden="true" style="--nh:${NH}">${D.horas.map((h, j) => `<span>${j % 4 === 0 ? h : ''}</span>`).join('')}</div>`;
  cabeza.innerHTML = '<tr>' + base + ({
    semanas: `<th class="r">% del total</th><th>${LARGO ? 'Por mes' : 'Por semana'}</th>`,
    dias: DIAS.map(d => `<th class="dia">${d}</th>`).join(''),
    horas: `<th class="r">Almuerzo</th><th class="r">Cena</th><th>Por hora${eje}</th>`,
  })[UI.modo] + '</tr>';
}
const marcaVI = a => (UI.vi && a.tot && a.vi / a.tot >= 0.25) ? ` · <span class="vi">${pct0(a.vi, a.tot)} venta interna</span>` : '';
function celdasModo(a, costoTot) {
  const u = D.insumos[a.cod][1];
  if (UI.modo === 'semanas') {
    const s = semanasDe(a), mx = Math.max(...s, 1e-9);
    return `<td class="r num">${pct(a.costo, costoTot)}</td><td><span class="spark" aria-label="consumo por semana">${s.map(v => `<span style="height:${Math.max(2, 22 * v / mx)}px"></span>`).join('')}</span></td>`;
  }
  if (UI.modo === 'dias') {
    const d = diasDe(a), mx = Math.max(...d, 1e-9);
    return d.map((v, i) => `<td class="dia num${v > 0 && v === mx ? ' pico' : ''}" style="background:${tono(v / mx, 24, 'transparent')}" title="${DIAS_L[i]}: ${prom(v)} ${esc(corta(u))} por día">${prom(v)}</td>`).join('');
  }
  const h = horasDe(a), { al, ce } = turnosDe(h), mx = Math.max(...h, 1e-9);
  return `<td class="r num">${prom(al)}</td><td class="r num">${prom(ce)}</td>
    <td><span class="tira" style="--nh:${NH}" aria-label="consumo por hora">${h.map((v, j) => `<span style="background:${tono(v / mx, 100, 'var(--linea)')}" title="${D.horas[j]} h: ${prom(v)} ${esc(corta(u))} por día"></span>`).join('')}</span></td>`;
}
const filas = document.getElementById('filas');
function pintarFilas() {
  const costoTot = suma(A.lista.map(a => a.costo));
  const vis = A.lista.filter(a => (famSel === 'Todas' || D.insumos[a.cod][3] === famSel) && (!txt || D.insumos[a.cod][0].toLowerCase().includes(txt)));
  if (!UI.sel || !A.ins.has(UI.sel)) UI.sel = (vis[0] || A.lista[0] || {}).cod || null;
  filas.innerHTML = vis.slice(0, 400).map(a => {
    const [nom, u, , fam, sub] = D.insumos[a.cod];
    const rk = A.lista.indexOf(a) + 1;
    const cant = `${prom(a.tot)}<span class="und">${esc(corta(u))}</span>`;
    return `<tr tabindex="0" data-cod="${esc(a.cod)}" aria-selected="${a.cod === UI.sel}">
      <td class="rk num">${rk}</td>
      <td><div class="nom">${esc(nom)}</div><div class="fam">${esc(cap(fam))} · ${esc(sub || '')}${marcaVI(a)}</div></td>
      ${UI.modo === 'semanas' ? `<td class="r num">${cant}</td><td class="r num">${sol(a.costo)}</td>` : `<td class="r num">${cant}<div class="costo-sub">${sol(a.costo)}</div></td>`}
      ${celdasModo(a, costoTot)}
    </tr>`;
  }).join('');
  const s = suma(vis.map(a => a.costo));
  document.getElementById('pie').textContent = `${vis.length} de ${A.lista.length} insumos · suman ${sol(s)} (${pct(s, costoTot)} del costo).` + ({
    semanas: '',
    dias: ` Cada día es un promedio, en la unidad de la fila: lo de los ${P.n_dia[0]} lunes entre ${P.n_dia[0]}, lo de los ${P.n_dia[5]} sábados entre ${P.n_dia[5]}.`,
    horas: ` Almuerzo y cena: promedio por día; el almuerzo son los platos pedidos antes de las 17 h.`,
  })[UI.modo];
}
filas.addEventListener('click', e => { const tr = e.target.closest('tr'); if (tr) elegir(tr.dataset.cod); });
filas.addEventListener('keydown', e => { if (e.key === 'Enter') { const tr = e.target.closest('tr'); if (tr) elegir(tr.dataset.cod); } });
function elegir(cod) { UI.sel = cod; guardar(); filas.querySelectorAll('tr').forEach(tr => tr.setAttribute('aria-selected', tr.dataset.cod === cod)); pintarDetalle(); }
function barras(items, color, fmt) {
  const mx = Math.max(...items.map(i => i[1]), 1e-9);
  return items.map(([lbl, v, col]) => `<div class="fila-bar"><span class="lbl" title="${esc(lbl)}">${esc(lbl)}</span><span class="val num">${fmt(v)}</span>
    <div class="bg"><span style="width:${100 * v / mx}%;background:${col || color}"></span></div></div>`).join('');
}
function mapaHTML(a) {
  const u = corta(D.insumos[a.cod][1]), m = mapaDe(a), todo = m.flat(), mx = Math.max(...todo, 1e-9);
  const k = todo.indexOf(mx), di = Math.floor(k / NH), hj = k % NH;
  const cab = '<span></span>' + D.horas.map(h => `<span class="mh">${h}</span>`).join('');
  const cuerpo = m.map((fila, i) => `<span class="md">${DIAS[i]}</span>` + fila.map((v, j) =>
    `<span class="mc" style="background:${tono(v / mx, 100, 'var(--linea)')}" title="${DIAS_L[i]} ${D.horas[j]} h: ${prom(v)} ${esc(u)} en promedio"></span>`).join('')).join('');
  return `<div class="mapa num" style="grid-template-columns: 30px repeat(${NH}, minmax(0, 1fr))">${cab}${cuerpo}</div>
    <p class="nota num">Día × hora del plato, en promedio por ese día de la semana. Lo más fuerte: el <b>${DIAS_L[di]} a las ${D.horas[hj]} h</b>, ${prom(mx)} ${esc(u)}.</p>`;
}
function seccionCuando(a) {
  const u = D.insumos[a.cod][1];
  if (UI.modo === 'semanas') {
    const s = semanasDe(a), mx = Math.max(...s, 1e-9);
    const hayParcial = !LARGO && s.some((_, i) => semParcial(i));
    return `<div class="det-sec"><h3>${LARGO ? 'Mes a mes' : 'Semana a semana'}<small>en ${esc(corta(u))}</small></h3>
      <div class="semanas" style="--n:${s.length}">${s.map((v, i) => `<div class="sem"><span class="v num">${s.length > 8 ? '' : prom(v)}</span><div class="col" style="height:${Math.max(2, 70 * v / mx)}px;opacity:.85" title="${esc(tituloSerie(i))}: ${prom(v)}"></div><span>${s.length > 8 && i % 2 ? '' : tituloSerie(i)}</span></div>`).join('')}</div>
      ${hayParcial ? '<p class="nota">* semana incompleta en el rango.</p>' : ''}</div>`;
  }
  if (UI.modo === 'dias') {
    const d = diasDe(a), mx = Math.max(...d, 1e-9), pos = d.filter((_, k) => P.n_dia[k]);
    const mn = Math.min(...pos), ip = d.indexOf(mx), im = d.indexOf(mn);
    const veces = mn > 0 ? `El <b>${DIAS_L[ip]}</b> se usa ${dec(mx / mn, 1)} veces lo de un ${DIAS_L[im]}. ` : '';
    return `<div class="det-sec"><h3>Por día de la semana<small>promedio por día, en ${esc(corta(u))}</small></h3>
      <div class="semanas" style="--n:7">${d.map((v, i) => `<div class="sem${i === ip ? ' pico' : ''}"><span class="v num">${prom(v)}</span><div class="col" style="height:${Math.max(2, 70 * v / mx)}px"></div><span>${DIAS[i]}</span></div>`).join('')}</div>
      <p class="nota num">${veces}Lo de los ${P.n_dia[0]} lunes entre ${P.n_dia[0]}, lo de los ${P.n_dia[5]} sábados entre ${P.n_dia[5]}.</p>${mapaHTML(a)}</div>`;
  }
  const h = horasDe(a), mx = Math.max(...h, 1e-9), ip = h.indexOf(mx), { al, ce } = turnosDe(h);
  return `<div class="det-sec"><h3>Por hora del plato<small>promedio por día, en ${esc(corta(u))}</small></h3>
    <div class="semanas" style="--n:${NH};gap:3px">${h.map((v, j) => `<div class="sem${j === ip ? ' pico' : ''}" style="font-size:10.5px"><span class="v num">${v >= 0.5 * mx ? prom(v) : ''}</span><div class="col" style="height:${Math.max(2, 70 * v / mx)}px" title="${D.horas[j]} h: ${prom(v)}"></div><span>${D.horas[j]}</span></div>`).join('')}</div>
    <div class="turnos">
      <div><div class="eyebrow">Almuerzo · antes de las 17 h</div><div class="grande num">${prom(al)} <span class="und">${esc(corta(u))} por día</span></div><div class="sub num">${pct0(al, al + ce)} del consumo</div></div>
      <div><div class="eyebrow">Cena · desde las 17 h</div><div class="grande num">${prom(ce)} <span class="und">${esc(corta(u))} por día</span></div><div class="sub num">${pct0(ce, al + ce)} del consumo</div></div>
    </div>${mapaHTML(a)}</div>`;
}
function pintarDetalle() {
  const det = document.getElementById('detalle');
  const a = A.ins.get(UI.sel);
  if (!a) { det.innerHTML = '<div class="det-sec"><p class="nota">Ningún insumo en el período.</p></div>'; return; }
  const [nom, u, pr, fam, sub, factor, us] = D.insumos[a.cod];
  const costoTot = suma(A.lista.map(x => x.costo));
  const equivalente = (factor && factor !== 1 && us) ? `<div class="sub num">= ${n0(a.tot * factor)} ${esc(us)} en las recetas</div>` : '';
  const cams = [...a.cam.entries()].sort((x, y) => y[1] - x[1]);
  const totCam = suma(cams.map(x => x[1]));
  const platos = [...a.pl.entries()].sort((x, y) => y[1] - x[1]).slice(0, 6);
  const nombresVI = [...a.pl.keys()].filter(p => PLATOS[p][1]).map(p => PLATOS[p][0]).slice(0, 2);
  const avisoVI = (UI.vi && a.tot && a.vi / a.tot >= 0.25)
    ? `<div class="det-sec aviso-vi"><p><b>${pct0(a.vi, a.tot)} sale de venta interna</b> (${esc(nombresVI.join(' y '))}): se produce por tanda, así que su día y su hora son los de la producción, no los del servicio. Apaga «Venta interna» para ver el patrón del salón.</p></div>` : '';
  let rend = '';
  const cortes = [...a.porc.entries()].sort((x, y) => y[1] - x[1]);
  if (cortes.length) {
    rend = `<div class="det-sec"><h3>Cómo se calculó el porcionamiento</h3>
      <p class="nota" style="margin:0 0 10px">Cada corte vendido se pasa a ${esc(corta(u))} de ${esc(nom)} con el rendimiento del último mes del rango.</p>
      <div class="rend">${cortes.map(([cx, q]) => {
        const r = (D.rend[a.cod] || {})[cx];
        const uc = D.preps[cx] ? D.preps[cx][2] : '';
        if (!r) return `<div class="rend-item"><div class="rend-top"><b>${esc(prepNombre(cx))}</b><span class="num">${prom(q)} ${esc(corta(u))}</span></div></div>`;
        const [rv, fuente, n, desde, hasta] = r;
        const base = fuente === 'ventana'
          ? `<span class="tag ok">Últimos 90 días</span><span class="num">${n} cortes · ${fCorta(desde)} – ${fCorta(hasta)}</span>`
          : `<span class="tag resp">Respaldo</span><span class="num">sin porcionamientos en 90 días ni receta: los ${n} más cercanos (${fMes(desde)} – ${fMes(hasta)})</span>`;
        const revisar = D.revisar.includes(cx) ? '<span class="tag rev" title="Al corte se le asignó menos insumo del que pesa: pasa con los subproductos (grasa, retazos, carcasa) a los que la cocina les anota poco peso para cargarles poco costo.">Revisar: pesa más de lo que se le asignó</span>' : '';
        return `<div class="rend-item"><div class="rend-top"><b>${esc(prepNombre(cx))}</b><span class="num">${prom(q)} ${esc(corta(u))}</span></div>
          <div class="rend-meta"><span class="num">${rv.toLocaleString('en-US', { maximumFractionDigits: 4 })} ${esc(corta(u))} por ${esc(corta(uc))}</span>${base}${revisar}</div></div>`;
      }).join('')}</div></div>`;
  }
  let real = '';
  const viaPorc = suma(cortes.map(x => x[1]));
  const pr_real = D.porcionado[a.cod];
  if (pr_real && viaPorc) {
    const dif = pr_real - viaPorc;
    const parte = viaPorc < 0.995 * a.tot ? ' (lo que llega por porcionamiento)' : '';
    real = `<div class="det-sec"><h3>Contra lo que se porcionó de verdad</h3>
      <div class="real"><div><div class="eyebrow">Explican las ventas${parte}</div><div class="grande num">${prom(viaPorc)} <span class="und">${esc(corta(u))}</span></div></div>
      <div><div class="eyebrow">Se porcionaron</div><div class="grande num">${prom(pr_real)} <span class="und">${esc(corta(u))}</span></div></div></div>
      <p class="nota num">${dif >= 0 ? 'Se porcionaron' : 'Las ventas explican'} ${prom(Math.abs(dif))} ${esc(corta(u))} más (${pct(Math.abs(dif), viaPorc)}). Se porciona por tandas: en un mes no tiene por qué cerrar.</p></div>`;
  }
  det.innerHTML = `
    <div class="det-cab">
      <div class="eyebrow">${esc(fam)} › ${esc(sub || '')}</div>
      <h2>${esc(nom)}</h2>
      <div class="det-cifras">
        <div><div class="grande num">${prom(a.tot)} <span class="und" style="font-size:14px">${esc(corta(u))}</span></div>${equivalente}</div>
        <div class="num" style="text-align:right"><div style="font-weight:600;font-size:16px">${sol(a.costo)}</div><div class="sub">${pct(a.costo, costoTot)} del costo del período</div></div>
      </div>
    </div>
    ${avisoVI}
    <div class="det-sec"><h3>Cómo llega al plato</h3>
      <div class="barra" style="margin:0 0 10px">${cams.map(([k, v]) => `<span style="width:${100 * v / (totCam || 1)}%;background:${GRUPOS[k].col}"></span>`).join('')}</div>
      ${barras(cams.map(([k, v]) => [GRUPOS[k].txt, v, GRUPOS[k].col]), null, v => `${prom(v)} ${esc(corta(u))} · ${pct(v, totCam)}`)}
    </div>
    <div class="det-sec"><h3>Platos que más lo usan</h3>
      ${barras(platos.map(([p, v]) => [PLATOS[p][0], v]), 'var(--acento)', v => `${prom(v)} ${esc(corta(u))}`)}
      ${notaEditadas(platos.map(([p]) => p))}
    </div>
    ${seccionCuando(a)}${rend}${real}${contraCompras(a)}`;
}

function notaEditadas(pids) {
  const ed = pids.filter(p => PLATOS[p][3]).map(p => `${PLATOS[p][0]} (${fCorta(PLATOS[p][3])})`);
  if (!ed.length) return '';
  return `<p class="nota-ed">Receta editada en el período: ${esc(ed.join(', '))}. Lo vendido antes de esa fecha se calcula con la receta de hoy.</p>`;
}
function contraCompras(a) {
  const [, u, , fam] = D.insumos[a.cod];
  if (!D.compras_familias.length) return '';
  const c = D.compras[a.cod];
  const u_ = esc(corta(u));
  const titulo = `<h3>Contra lo que se compró<small>del ${fCorta(P.desde)} al ${fCorta(P.hasta)}, por la fecha del documento</small></h3>`;
  if (!c) {
    if (!FAM_C.has(String(fam).toUpperCase())) return '';
    return `<div class="det-sec">${titulo}<p class="nota" style="margin:0">No se compró en el período: lo que se usó salió del stock, o se compra con otro código.</p></div>`;
  }
  const [qc, sc, docs] = c, dif = qc - a.tot;
  const txt = Math.abs(dif) < 1e-9 ? 'Lo mismo que explican las ventas.'
    : (dif > 0 ? `Se compró ${prom(dif)} ${u_} más de lo que explican las ventas (${pct(dif, a.tot)}).`
               : `Las ventas explican ${prom(-dif)} ${u_} más de lo que se compró (${pct(-dif, a.tot)}): salió del stock.`);
  return `<div class="det-sec">${titulo}
    <div class="real"><div><div class="eyebrow">Explican las ventas</div><div class="grande num">${prom(a.tot)} <span class="und">${u_}</span></div></div>
    <div><div class="eyebrow">Se compraron</div><div class="grande num">${prom(qc)} <span class="und">${u_}</span></div><div class="sub num">${sol(sc)} en ${docs} documento${docs === 1 ? '' : 's'}</div></div></div>
    <p class="nota num">${txt} Comprar no es usar: el stock sube y baja entre compras, y hay usos que no pasan por una receta (aceite de freír, comida del personal, pruebas).${UI.vi ? '' : ' Con la venta interna apagada, lo que se compró para ella queda del lado de lo comprado.'}</p></div>`;
}

// ═══ CONTRA COMPRAS: todo lo comprado del rango, al lado de lo que explican las ventas ═══
const FAM_C = new Set((D.compras_familias || []).map(f => String(f).toUpperCase()));
const FAM_DEFECTO = ['ALIMENTOS', 'BEBIDAS CON ALCOHOL', 'BEBIDAS SIN ALCOHOL', 'VINOS Y ESPUMANTES'];
const famsTexto = () => {
  const f = [...FAM_C].sort();
  return f.length === FAM_DEFECTO.length && f.every((x, i) => x === FAM_DEFECTO[i])
    ? 'alimentos y bebidas' : f.map(x => cap(x).toLowerCase()).join(', ');
};
// «Diferencia grande»: más del 25 % de lo que explican las ventas Y más de
// S/ 100. Con el 25 % solo, un mes de septiembre de 2026 marcaba 305 de 417
// insumos (lo chico se compra cada tanto y casi nunca cierra en un mes); con
// los dos, 93, y arriba lo que importa: cachema, bife ancho, naranja, papa.
const DIF_MIN_SOLES = 100;
const FILTROS_C = [['todo', 'Todo'], ['sin', 'Ninguna venta los usó'], ['dif', 'Diferencia grande']];
let ccTxt = '', ccFiltro = 'todo';
function filasCompras() {
  const out = [], vistos = new Set();
  for (const a of A.lista) {
    const [nom, u, , fam, sub] = D.insumos[a.cod];
    if (!FAM_C.has(String(fam).toUpperCase())) continue;
    const c = D.compras[a.cod] || [0, 0, 0];
    out.push({ cod: a.cod, nom, u, fam, sub, usado: a.tot, costo: a.costo, comp: c[0], sComp: c[1], docs: c[2], ficha: true });
    vistos.add(a.cod);
  }
  for (const [cod, c] of Object.entries(D.compras)) {
    if (vistos.has(cod)) continue;
    let nom, u, fam, sub;
    if (D.comprados[cod]) [nom, u, fam, sub] = D.comprados[cod];
    else if (D.insumos[cod]) [nom, u, , fam, sub] = D.insumos[cod];
    else continue;
    out.push({ cod, nom, u, fam, sub, usado: 0, costo: 0, comp: c[0], sComp: c[1], docs: c[2], ficha: A.ins.has(cod) });
  }
  for (const r of out) {
    r.dif = r.comp - r.usado; r.peso = Math.max(r.sComp, r.costo);
    const pr = D.insumos[r.cod] ? D.insumos[r.cod][2] : (r.comp ? r.sComp / r.comp : 0);
    r.sDif = Math.abs(r.dif) * pr;
  }
  return out.sort((x, y) => y.peso - x.peso);
}
const alta = r => r.usado > 0 && Math.abs(r.dif) > 0.25 * r.usado && r.sDif >= DIF_MIN_SOLES;
function pintarCompras() {
  const cab = document.getElementById('cc-cabeza'), tb = document.getElementById('cc-filas');
  if (!D.compras_familias.length) {
    document.getElementById('cc-resumen').textContent = 'No se pudieron leer las compras del período (compras.parquet).';
    cab.innerHTML = ''; tb.innerHTML = ''; document.getElementById('cc-pie').textContent = '';
    return;
  }
  const todas = filasCompras();
  const compradas = todas.filter(r => r.comp > 0);
  const sTot = suma(compradas.map(r => r.sComp));
  const usadas = compradas.filter(r => r.usado > 0), sinUso = compradas.filter(r => r.usado <= 0);
  const sUsadas = suma(usadas.map(r => r.sComp));
  document.getElementById('cc-sub').textContent = `Del ${fCorta(P.desde)} al ${fCorta(P.hasta)} · ${famsTexto()} · compras por la fecha del documento`;
  document.getElementById('cc-resumen').innerHTML =
    `<b>${sol(sTot)}</b> comprados en ${compradas.length} productos. Las ventas del período usan ${usadas.length} de ellos: <b>${sol(sUsadas)}</b> (${pct(sUsadas, sTot)}).` +
    (sinUso.length ? ` <b>${sol(suma(sinUso.map(r => r.sComp)))}</b> en ${sinUso.length} producto${sinUso.length === 1 ? '' : 's'} que ninguna venta del período usó.` : ' Todo lo comprado lo usó alguna venta del período.');
  document.getElementById('cc-filtro').innerHTML = FILTROS_C.map(([k, txt]) =>
    `<button class="chipf" type="button" aria-pressed="${k === ccFiltro}" data-f="${k}"${k === 'dif' ? ` title="Más del 25 % de lo que explican las ventas y más de S/ ${DIF_MIN_SOLES}, ordenado por los soles de la diferencia"` : ''}>${txt}</button>`).join('');
  let vis = todas;
  if (ccFiltro === 'sin') vis = vis.filter(r => r.comp > 0 && r.usado <= 0);
  if (ccFiltro === 'dif') vis = vis.filter(alta).sort((x, y) => y.sDif - x.sDif);
  if (ccTxt) vis = vis.filter(r => r.nom.toLowerCase().includes(ccTxt));
  cab.innerHTML = '<tr><th class="rk">#</th><th>Insumo</th><th class="r">Se compró<div class="th-sub">soles</div></th><th class="r">Explican las ventas<div class="th-sub">costo de hoy</div></th><th class="r">Comprado − usado</th></tr>';
  tb.innerHTML = vis.slice(0, 500).map((r, i) => {
    const u_ = esc(corta(r.u));
    let dif;
    if (r.usado <= 0) dif = '<span class="dif alta">ninguna venta lo usó</span>';
    else if (r.comp <= 0) dif = `<span class="dif${alta(r) ? ' alta' : ''}">no se compró · −${prom(r.usado)} ${u_}</span>`;
    else dif = `<span class="dif${alta(r) ? ' alta' : ''}">${r.dif >= 0 ? '+' : '−'}${prom(Math.abs(r.dif))} ${u_} · ${r.dif >= 0 ? '+' : '−'}${pct0(Math.abs(r.dif), r.usado)}</span>`;
    if (r.usado > 0 && r.sDif >= 0.5) dif += `<div class="costo-sub">${sol(r.sDif)}</div>`;
    return `<tr${r.ficha ? ` tabindex="0" data-cod="${esc(r.cod)}" title="Abrir su ficha en «Resumen»"` : ' class="sin-ficha"'}>
      <td class="rk num">${i + 1}</td>
      <td><div class="nom">${esc(r.nom)}</div><div class="fam">${esc(cap(r.fam))} · ${esc(r.sub || '')}</div></td>
      <td class="r num">${r.comp ? `${prom(r.comp)}<span class="und">${u_}</span><div class="costo-sub">${sol(r.sComp)}</div>` : '—'}</td>
      <td class="r num">${r.usado ? `${prom(r.usado)}<span class="und">${u_}</span><div class="costo-sub">${sol(r.costo)}</div>` : '—'}</td>
      <td class="r num">${dif}</td></tr>`;
  }).join('') || '<tr class="sin-ficha"><td colspan="5">Nada con este filtro.</td></tr>';
  document.getElementById('cc-pie').textContent =
    `${vis.length} de ${todas.length} insumos. Comprar no es usar: el stock del almacén sube y baja entre compras, y hay usos que no pasan por una receta (aceite de freír, comida del personal, pruebas, mermas). Una diferencia chica es normal; una grande en un mes pide mirar (en ámbar: más del 25 % y más de S/ ${DIF_MIN_SOLES}). En la unidad del kardex, la misma de las compras; soles de compra sin IGV, y lo que explican las ventas al costo promedio de hoy.` +
    (UI.vi ? '' : ' Con la venta interna apagada, lo que se compró para ella queda del lado de lo comprado.');
}
document.getElementById('cc-filtro').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; ccFiltro = b.dataset.f; pintarCompras(); });
document.getElementById('cc-buscar').addEventListener('input', e => { ccTxt = e.target.value.trim().toLowerCase(); pintarCompras(); });
const abrirFicha = cod => { UI.vista = 'resumen'; UI.sel = cod; guardar(); pintarVista(); pintarFilas(); pintarDetalle(); };
document.getElementById('cc-filas').addEventListener('click', e => { const tr = e.target.closest('tr[data-cod]'); if (tr) abrirFicha(tr.dataset.cod); });
document.getElementById('cc-filas').addEventListener('keydown', e => { if (e.key === 'Enter') { const tr = e.target.closest('tr[data-cod]'); if (tr) abrirFicha(tr.dataset.cod); } });

// ── cómo se calcula ──
// Lo producido contra lo facturado del período, producto por producto
// (regla #605): la cuenta de arriba sale de lo primero.
function notaProduccion() {
  const pr = (D.venta_interna && D.venta_interna.produccion) || [];
  if (!pr.length) return '';
  const filas = pr.map(([pl, u, prod, fact, masa, parte]) =>
    `${esc(pl)}: ${n0(prod)} ${esc(u)} porcionad${prod === 1 ? 'o' : 'os'}, ${n0(fact)} facturad${fact === 1 ? 'o' : 'os'}${masa ? ' (fechado por su masa)' : ''}${parte < 0.995 ? ` (a la venta interna le toca el ${Math.round(parte * 100)} %)` : ''}`);
  return ' En el período: ' + filas.join(' · ') + '.';
}
{
  const R = D.resumen;
  const partes = [
    '<b>El árbol.</b> Cada plato vendido se abre en los insumos de su receta de venta —el primer nivel, el del POS—. Un insumo que es una preparación baja por su receta base, y así hasta llegar a lo que se compra (hasta ' + R.niveles + ' niveles en el rango). Un corte que sale de un porcionamiento pasa al insumo entero con el rendimiento REAL: los porcionamientos de los 90 días que terminan el último día de cada mes; si no hubo, su receta base; y sólo si tampoco tiene receta, los 10 porcionamientos más cercanos. El reparto entre los cortes de un porcionamiento es por su peso, la regla del propio Almacén.',
    '<b>Unidades y precios.</b> Todo en la unidad del kardex (la de compra), con el factor de cada producto. Recetas y precios promedio: los de HOY — editar una receta cambia el consumo de meses pasados, como en el POS.',
    `<b>El costo.</b> Al primer nivel, el del POS, el período suma ${sol(R.costo_nivel1)}; bajando hasta lo que se compra, ${sol(R.costo)}. Por las recetas base cierra: el Almacén recuesta cada preparación con sus insumos. La diferencia sale de los porcionamientos: las hojas llevan el rendimiento real, y el corte, el costo que le puso el Almacén.`,
    `<b>El día y la hora.</b> El día es el del pedido. La hora es la de cada plato${R.hora_de_mesa ? ' — en este parquet todavía la de la MESA, que no trae la del plato' : ' y no la de la mesa: un postre llega unos 70 minutos después de abierta'}. «Día de la semana» es un promedio: lo de los lunes entre cuántos lunes hubo.`,
    '<b>Venta interna.</b> Lo que se produce en casa para Mayta —el chorizo, la chistorra y la manteca de pato— cuenta el día que se PRODUJO y no el que se facturó: se factura por tanda (en agosto de 2026, nada; el 23 de septiembre, 600 unidades) y así el magret «se usaba» un mes después de comprado. Si sale de porcionar una masa que se hace con orden de producción, la fecha es la de esa orden, que es cuando se usó el magret; si no, la de su porcionamiento. Si también va al salón, la venta interna se lleva su parte de los últimos 12 meses. Lo que se revende tal cual (vinos, panceta) sigue por la factura. El interruptor la saca, como en Ventas › Por hora.' + notaProduccion(),
  ];
  const editadas = PLATOS.filter(p => p[3]);
  if (editadas.length) partes.push(`<b>Recetas editadas.</b> ${editadas.length} plato${editadas.length === 1 ? '' : 's'} del período cambi${editadas.length === 1 ? 'ó' : 'aron'} de receta desde el ${fCorta(P.desde)} (${esc(editadas.slice(0, 4).map(p => `${p[0]}, ${fCorta(p[3])}`).join(' · '))}${editadas.length > 4 ? '…' : ''}): lo vendido antes de esa fecha se calcula con la receta de hoy. La tabla dinámica y la ficha los marcan.`);
  partes.push(`<b>Contra compras.</b> Lo comprado del rango, por la fecha del documento y en la unidad del kardex —la misma de las compras en todas sus líneas—, ${D.compras_familias.length ? 'de ' + famsTexto() : 'que no se pudo leer'}. Comprar no es usar: el stock sube y baja entre compras.`);
  if (R.sin_maestro || R.sin_factor) partes.push(`<b>Lo que no se pudo bajar.</b> ${R.sin_maestro} líneas con un insumo que no está en el maestro y ${R.sin_factor} sin factor de conversión: ${sol(R.costo_sin_convertir)} del primer nivel.`);
  document.getElementById('metodo-txt').innerHTML = partes.join(' ');
}

function pintarTodo() {
  pintarResumen(); pintarSegTD(); pintarDinamica(); pintarFams(); pintarModos(); pintarCabeza();
  if (UI.vista === 'resumen') { pintarFilas(); pintarDetalle(); }
  if (UI.vista === 'compras') pintarCompras();
}
// abre con el primer insumo y su primera preparación desplegados: los tres niveles a la vista
if (A.lista.length) {
  const a0 = A.lista[0];
  const p0 = [...a0.preps.values()].sort((x, y) => y.tot - x.tot)[0];
  tdAbiertos.add('i:' + a0.cod);
  if (p0) tdAbiertos.add('p:' + a0.cod + '|' + p0.prep);
}
pintarVista();
pintarTodo();
</script>
</body></html>
"""
