// Recetas › «Costo recetas base» (regla #706).
//
// La monta graficos/recetas_base_costo.py::render_costo_recetas_base con
// st.components.v2 (sin iframe, estilos en un shadow root). Es la forma del
// boceto aprobado (https://claude.ai/artifact/8Mgy71Rs9TC4TirzoE8pSo): el
// renglón del título con el período, el área, «Con | Sin órdenes» y el
// buscador; seis indicadores que filtran; la lista y, al costado, la ficha
// de la elegida con su veredicto y cuatro pestañas (Receta, Producciones,
// Dónde se usa, Cambios). Python manda las cuatro ventanas de una vez: nada
// de esto pide una corrida.
//
// Python manda en `data`: `fin`, `ventana`, `filas` (una por receta: lo que
// no depende de la ventana), `tablas` ({ventana: {cod: CAMPOS_TABLA}}),
// `donde` ({ventana: {cod: [CAMPOS_DONDE]}}), `ordenes` ({cod:
// [CAMPOS_ORDEN]}), `meses`, `recetas` ({cod: [CAMPOS_ING]}, por 1 unidad de
// entrada), `padres`, `semanas`, `descarga` ({cod: [líneas, por insumo]}),
// `ediciones`, `hay_log` y `umbral`. Las listas se leen POR POSICIÓN (las
// constantes de abajo); el test fija los órdenes.
//
// LAS SEÑALES: producido ÷ usado fuera de 50–150 % (sin contar las recetas
// que todas sus líneas descargan por insumo: no llevan orden); una receta
// «DD» con líneas que la descargan como producto (regla #648); una suba de
// 20 % o más en 12 meses; y la receta de hoy contra la última orden de los
// últimos 6 meses, a más de 25 %.

const T_PLATOS = 0, T_VENDIDOS = 1, T_USADO = 2, T_ORDENES = 3, T_PRODUCIDO = 4;
const O_FECHA = 0, O_ORDEN = 1, O_AREA = 2, O_CANT = 3, O_PUNIT = 4, O_VALOR = 5, O_ATIPICO = 6;
const I_COD = 0, I_INSUMO = 1, I_CANT = 2, I_UNID = 3, I_COSTO_UNIT = 4, I_UNID_COMPRA = 5, I_COSTO = 6, I_ES_BASE = 7, I_FACTOR = 8;
const W_PLATO = 0, W_USADO = 1, W_VENDIDOS = 2, W_DIRECTO = 3;
const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const VENT = [['30', '30 días'], ['90', '90 días'], ['182', '6 meses'], ['365', '12 meses']];
const NIVELES = 4;

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const sinTilde = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const fn = (v, d = 0) => (v == null || !isFinite(v) ? '—' : v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }));
const cant = (v) => (!v || !isFinite(v) ? '—' : Math.abs(v) >= 100 ? fn(v) : Math.abs(v) >= 10 ? fn(v, 1) : fn(v, 2));
const soles = (v) => (!v || !isFinite(v) ? '—' : v < 1000 ? `S/ ${fn(v, 2)}` : `S/ ${fn(v)}`);
const pc = (v) => (v == null || !isFinite(v) ? '—' : `${fn(v * 100)} %`);
const varTxt = (v) => (v == null || !isFinite(v) ? '' : `${v >= 0 ? '+' : '−'}${fn(Math.abs(v) * 100)} %`);
const mesTxt = (s) => { const [y, m] = s.split('-').map(Number); return `${MES[m - 1]} ${String(y).slice(2)}`; };
const dias = (a, b) => (new Date(b) - new Date(a)) / 86400000;

function armarDatos(D) {
  // Lo derivado de `data`, una vez por cada `data` nueva.
  const F = new Map(D.filas.map((f) => [f.cod, f]));
  const anio = Number(D.fin.slice(0, 4));
  return {
    D, F, U: D.umbral, anio,
    areas: [...new Set(D.filas.map((f) => f.area).filter(Boolean))].sort(),
    activas: D.filas.filter((f) => f.activa).length,
  };
}

function dibujar(raiz) {
  const { st: S } = raiz.__d, X = raiz.__d.x, { D, F, U } = X;
  const q = (sel) => raiz.querySelector(sel);
  // Los gráficos se dibujan al ancho real de la ficha: con un viewBox fijo,
  // la letra crece o se achica con la pantalla.
  const anchoGraf = () => Math.max(280, (q('[data-zona="ficha"]').clientWidth || 486) - 24);
  const fecha = (s) => { const [y, m, d] = s.slice(0, 10).split('-').map(Number); return `${d} ${MES[m - 1]}${y !== X.anio ? ' ' + String(y).slice(2) : ''}`; };

  // ── Las cuentas de cada receta en la ventana ───────────────────────────
  function fila(cod) {
    const f = F.get(cod), t = (D.tablas[S.vent] || {})[cod] || [0, 0, 0, 0, 0];
    const platos = t[T_PLATOS] || 0, vendidos = t[T_VENDIDOS] || 0, usado = t[T_USADO] || 0, ordenes = t[T_ORDENES] || 0, producido = t[T_PRODUCIDO] || 0;
    const desc = D.descarga[cod];
    const porInsumo = !!desc && desc[1] === desc[0];
    const ddProd = /\bDD\b/.test(f.nombre) && !!desc && desc[1] < desc[0];
    const cob = f.con_ordenes && usado > 0 && !porInsumo ? producido / usado : null;
    const reciente = f.f_ultimo && dias(f.f_ultimo, D.fin) <= U.dias_orden;
    const brecha = f.ultimo && f.costo_hoy && reciente ? f.costo_hoy / f.ultimo - 1 : null;
    return { ...f, platos, vendidos, usado, ordenes, producido, cob, porInsumo, ddProd, desc, brecha };
  }
  const IND = [
    ['uso', 'En uso', (x) => x.usado > 0, () => `de ${fn(X.activas)} activas`, false],
    ['menos', 'Se produce de menos', (x) => x.cob != null && x.cob < U.cob_baja, () => `producido < ${fn(U.cob_baja * 100)} % de lo usado`, true],
    ['mas', 'Se produce de más', (x) => x.cob != null && x.cob > U.cob_alta, () => `producido > ${fn(U.cob_alta * 100)} % de lo usado`, true],
    ['dd', '«DD» como producto', (x) => x.ddProd, () => 'líneas que piden una orden', true],
    ['sube', `Costo subió ≥ ${fn(U.var * 100)} %`, (x) => x.var != null && x.var >= U.var, () => 'primer mes → último, 12 m', true],
    ['cuadra', 'Receta ≠ orden', (x) => x.brecha != null && Math.abs(x.brecha) > U.brecha, () => `hoy vs. última orden > ${fn(U.brecha * 100)} %`, true],
  ];
  const visible = (x) => x.activa || x.usado > 0 || x.ordenes > 0;
  const xs = D.filas.map((f) => fila(f.cod));

  function filtradas() {
    let r = xs.filter(visible);
    if (S.area) r = r.filter((x) => x.area === S.area);
    if (S.prod === 'con') r = r.filter((x) => x.con_ordenes); else if (S.prod === 'sin') r = r.filter((x) => !x.con_ordenes);
    if (S.q.trim()) { const b = sinTilde(S.q); r = r.filter((x) => sinTilde(x.nombre).includes(b)); }
    if (S.ind) { const t = IND.find((i) => i[0] === S.ind); r = r.filter(t[2]); }
    const k = { vendidos: (x) => -x.vendidos, usado: (x) => -x.usado, producido: (x) => -x.producido, cob: (x) => (x.cob == null ? 9 : x.cob), ultimo: (x) => -(x.ultimo || 0) }[S.orden];
    return r.sort((a, b) => k(a) - k(b) || a.nombre.localeCompare(b.nombre));
  }

  // ── Cabecera e indicadores ─────────────────────────────────────────────
  function cabecera() {
    // Mientras se escribe en el buscador no se rehace: se perdería el cursor.
    // (Sin buscador todavía, `activeElement` también es null: no es «enfocado».)
    const b = q('[data-acc="buscar"]');
    if (b && raiz.getRootNode().activeElement === b) return;
    q('[data-zona="cab"]').innerHTML = `<span class="tit">Costo recetas base</span>
      <div class="seg">${VENT.map(([k, r]) => `<button type="button" data-vent="${k}" class="${S.vent === k ? 'on' : ''}">${r}</button>`).join('')}</div>
      <select class="sel" data-acc="area" aria-label="Área"><option value="">Todas las áreas</option>${X.areas.map((a) => `<option${S.area === a ? ' selected' : ''}>${esc(a)}</option>`).join('')}</select>
      <select class="sel" data-acc="prod" aria-label="Órdenes de producción"><option value="todas"${S.prod === 'todas' ? ' selected' : ''}>Todas las recetas</option><option value="con"${S.prod === 'con' ? ' selected' : ''}>Con órdenes</option><option value="sin"${S.prod === 'sin' ? ' selected' : ''}>Sin órdenes</option></select>
      <span class="sp"></span>
      <input class="buscar" data-acc="buscar" placeholder="Buscar receta" value="${esc(S.q)}" aria-label="Buscar receta">`;
  }
  function indicadores() {
    const base = xs.filter(visible).filter((x) => !S.area || x.area === S.area);
    q('[data-zona="kpis"]').innerHTML = IND.map(([k, rot, fnc, sub, alerta]) => {
      const n = base.filter(fnc).length;
      return `<button type="button" class="kpi${S.ind === k ? ' on' : ''}${alerta && n ? ' alerta' : ''}" data-ind="${k}" title="${S.ind === k ? 'Tocá para ver todas' : 'Tocá para ver sólo éstas'}"><span class="r">${esc(rot)}</span><span class="v">${fn(n)}</span><span class="s">${esc(sub())}</span></button>`;
    }).join('');
  }

  // ── La lista ───────────────────────────────────────────────────────────
  function spark(vals, w = 62, h = 20) {
    const v = (vals || []).filter((x) => x != null);
    if (v.length < 2) return '<span class="gris">—</span>';
    const mn = Math.min(...v), mx = Math.max(...v), r = mx - mn || 1;
    const pts = v.map((x, i) => `${(2 + i * (w - 4) / (v.length - 1)).toFixed(1)},${(h - 3 - (x - mn) / r * (h - 6)).toFixed(1)}`).join(' ');
    const sube = v[v.length - 1] > v[0] * (1 + U.var), baja = v[v.length - 1] < v[0] * (1 - U.var);
    return `<svg class="spk" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts}" fill="none" style="stroke:${sube ? 'var(--warning)' : baja ? 'var(--success)' : 'var(--accent)'}" stroke-width="1.6"/></svg>`;
  }
  function barraCob(x) {
    if (x.porInsumo) return '<span class="chip ins" title="Todas las líneas que la nombran la descargan por insumo: no lleva orden">por insumo</span>';
    if (!x.con_ordenes) return '<span class="gris" title="Nunca la produjo una orden: sale de un porcionamiento o no se registra">sin órdenes</span>';
    if (x.cob == null) return '<span class="gris">—</span>';
    const w = Math.min(100, x.cob / 2 * 100), cls = x.cob < U.cob_baja ? 'baja' : x.cob > U.cob_alta ? 'alta' : '';
    return `<span class="cob"><span class="b" title="producido ÷ usado; la rayita es 100 %"><i class="${cls}" style="width:${w.toFixed(0)}%"></i><u></u></span><span class="${cls ? 'ambar' : ''}">${pc(x.cob)}</span></span>`;
  }
  function lista() {
    const r = filtradas();
    if (!r.some((x) => x.cod === S.sel) && !S.pila.length) S.sel = r[0]?.cod ?? null;
    const ind = S.ind ? IND.find((i) => i[0] === S.ind)[1] : null;
    q('[data-zona="lcab"]').innerHTML = `<span>${fn(r.length)} recetas${ind ? ` · <b>${esc(ind)}</b> <button type="button" class="volver" data-ind="${S.ind}">quitar</button>` : ''}</span><span>ventas hasta el ${fecha(D.fin)} · ${VENT.find((v) => v[0] === S.vent)[1]}</span>`;
    const th = (k, t, tip) => `<th data-orden="${k}" class="${S.orden === k ? 'ord' : ''}" title="${esc(tip)}">${t}${S.orden === k ? ' ▾' : ''}</th>`;
    q('[data-zona="lista"]').innerHTML = `<table class="l"><thead><tr><th>Receta base</th>${th('vendidos', 'Vendidos', 'Unidades vendidas de los platos que la llevan (directo o adentro de otra receta base)')}${th('usado', 'Usado', 'Lo que usaron esas ventas, en la unidad de la receta')}${th('producido', 'Producido', 'Lo que produjeron las órdenes procesadas')}${th('cob', 'Prod. ÷ uso', `Producido ÷ usado. En ámbar debajo de ${fn(U.cob_baja * 100)} % o arriba de ${fn(U.cob_alta * 100)} %`)}${th('ultimo', 'Último costo', 'Costo por unidad de la última orden; la variación, de los últimos 12 meses')}<th title="El costo de cada mes con órdenes, últimos 12">12 m</th></tr></thead><tbody>
      ${r.slice(0, 250).map((x) => `<tr data-cod="${esc(x.cod)}" class="${x.cod === S.sel ? 'on' : ''}">
        <td><span class="nom" title="${esc(x.nombre)}">${esc(x.nombre)}</span><span class="sub">${esc(x.area || '—')} · ${esc(x.unid)}${x.ddProd ? '<span class="chip dd">DD como producto</span>' : ''}${x.activa ? '' : '<span class="chip inac">inactiva</span>'}</span></td>
        <td>${cant(x.vendidos)}<div class="sub">${x.platos ? `${fn(x.platos)} platos` : ''}</div></td>
        <td>${cant(x.usado)}</td>
        <td>${x.con_ordenes && !x.producido ? '0' : cant(x.producido)}<div class="sub">${x.con_ordenes ? `${fn(x.ordenes)} órd.` : ''}</div></td>
        <td>${barraCob(x)}</td>
        <td>${soles(x.ultimo)}<span class="var ${x.var >= U.var ? 'ambar' : x.var <= -U.var ? 'verde' : 'gris'}">${varTxt(x.var)}</span></td>
        <td>${spark(x.linea)}</td></tr>`).join('')}</tbody></table>${r.length > 250 ? '<div class="nota" style="margin:8px">Se ven las primeras 250: buscá o filtrá para las demás.</div>' : ''}${r.length ? '' : '<div class="nota" style="margin:8px">Ninguna receta base con este filtro.</div>'}`;
  }

  // ── La ficha ───────────────────────────────────────────────────────────
  function veredicto(x) {
    const u = x.unid, p = [];
    if (x.ddProd) p.push(`Se llama <b>DD</b> (se descarga por insumo) pero <b>${x.desc[0] - x.desc[1]} de sus ${x.desc[0]} líneas</b> la descargan como producto: esas líneas piden una orden que nadie hace. Revisar <code>T DESCARG</code> en esas recetas (regla #648).`);
    if (x.cob != null && x.cob < U.cob_baja) p.push(`Las ventas usaron <b>${cant(x.usado)} ${esc(u)}</b> y las órdenes produjeron <b>${cant(x.producido)}</b> (${pc(x.cob)}): se produce sin registrar, sale de otro lado o el kardex queda en negativo.`);
    if (x.cob != null && x.cob > U.cob_alta) p.push(`Se produjo <b>${fn(x.cob, 1)} veces</b> lo que pidieron las ventas: stock que se acumula, merma, o se usa en algo que no es venta.`);
    if (x.var != null && x.var >= U.var) {
      const eds = (D.ediciones[x.cod] || []).length;
      p.push(`Su costo por unidad <b>subió ${pc(x.var)}</b> en 12 meses${eds ? ` y la receta se editó ${eds} ${eds === 1 ? 'vez' : 'veces'} (▼ en Producciones)` : D.hay_log ? ': no hubo ediciones, es el precio de sus insumos' : ''}.`);
    }
    if (x.brecha != null && Math.abs(x.brecha) > U.brecha) p.push(`La receta hoy cuesta <b>${soles(x.costo_hoy)}</b> por ${esc(u)} y la última orden (${fecha(x.f_ultimo)}) <b>${soles(x.ultimo)}</b>: revisar la cantidad de esa orden o el factor de un insumo.`);
    if (x.porInsumo) p.push('Todas las líneas que la nombran la descargan <b>por insumo</b>: no lleva orden de producción, y producido ÷ usado no aplica.');
    if (!p.length) return `<div class="veredicto">${x.usado > 0 ? `Sin señales: las ventas usaron ${cant(x.usado)} ${esc(u)}${x.cob != null ? ` y se produjo ${pc(x.cob)} de eso` : ''}.` : 'No la usó ninguna venta en el período.'}</div>`;
    return `<div class="veredicto alerta">${p.join('<br>')}</div>`;
  }
  function filasReceta(cod, escala, nivel, ruta) {
    // Las de adentro se abren EN SU LUGAR, con lo que lleva la de afuera.
    let out = [];
    for (const l of D.recetas[cod] || []) {
      const c = l[I_COD], key = ruta + '>' + c, esBase = !!l[I_ES_BASE] && !!D.recetas[c], abierto = S.abiertos.has(key);
      out.push({ c, ins: l[I_INSUMO], q: (l[I_CANT] || 0) * escala, un: l[I_UNID], cu: l[I_COSTO_UNIT], uc: l[I_UNID_COMPRA], co: (l[I_COSTO] || 0) * escala, esBase, nivel, key, abierto });
      if (esBase && abierto && nivel < NIVELES) out = out.concat(filasReceta(c, l[I_FACTOR] > 0 ? ((l[I_CANT] || 0) * escala) / l[I_FACTOR] : 0, nivel + 1, key));
    }
    return out;
  }
  function pestReceta(x) {
    const fs = filasReceta(x.cod, 1, 0, x.cod);
    if (!fs.length) return '<div class="nota">Esta receta base no tiene ingredientes cargados.</div>';
    const tot = fs.filter((r) => r.nivel === 0).reduce((a, r) => a + r.co, 0) || 1;
    const nb = fs.filter((r) => r.nivel === 0 && r.esBase).length;
    return `<div class="bl"><div class="bl-t">Por 1 ${esc(x.unid)}, precios de hoy<span>${nb ? `${nb} ${nb === 1 ? 'receta base' : 'recetas base'} adentro: ▸ la abre acá` : 'todo se compra o se porciona'}</span></div>
      <table class="r"><thead><tr><th>Insumo</th><th>Cantidad</th><th>Costo unit.</th><th>Costo</th><th>%</th></tr></thead><tbody>
      ${fs.map((r) => `<tr class="${r.esBase ? 'base' : ''}${r.nivel ? ' hijo' : ''}" ${r.esBase ? `data-abrir="${esc(r.key)}"` : ''}>
        <td style="padding-left:${6 + r.nivel * 14}px">${r.esBase ? (r.abierto ? '▾ ' : '▸ ') : ''}${esc(r.ins)}${r.esBase && F.has(r.c) ? ` <button type="button" class="abrir" data-ir="${esc(r.c)}" title="Ver su ficha, con su receta por 1 unidad">abrir</button>` : ''}</td>
        <td>${cant(r.q)} ${esc(r.un)}</td><td>${r.cu ? `S/ ${fn(r.cu, 2)} / ${esc(r.uc)}` : '—'}</td><td>S/ ${fn(r.co, 2)}</td>
        <td>${r.nivel ? '' : `${fn(r.co / tot * 100)}%<span class="pct"><i style="width:${(r.co / tot * 100).toFixed(0)}%"></i></span>`}</td></tr>`).join('')}
      <tr class="tot"><td>Total de la receta</td><td></td><td></td><td>S/ ${fn(tot, 2)}</td><td></td></tr></tbody></table>
      <div class="ley">Las de adentro van con lo que lleva la de afuera: su costo ya está en la línea que las nombra. «abrir» la muestra por 1 unidad suya.</div></div>`;
  }
  function grafEvo(x) {
    const O = D.ordenes[x.cod] || [], M = D.meses[x.cod] || [], E = D.ediciones[x.cod] || [];
    if (!O.length) return '<div class="nota">Nunca la produjo una orden de producción: si se usa, sale de un porcionamiento o no se registra.</div>';
    const desde = O[0][O_FECHA], t0 = new Date(desde.slice(0, 7) + '-01'), t1 = new Date(D.fin);
    const W = anchoGraf(), H = 160, L = 46, R = 8, T = 10, B = 34;
    const tx = (s) => L + (W - L - R) * (new Date(s) - t0) / Math.max(1, t1 - t0);
    const normales = O.filter((o) => !o[O_ATIPICO] && o[O_PUNIT] > 0);
    const tope = Math.max(...normales.map((o) => o[O_PUNIT]), ...M.map((m) => m[1]), x.costo_hoy || 0, 0.01) * 1.12;
    const ty = (v) => T + (H - T - B) * (1 - Math.min(v, tope) / tope);
    let s = `<svg class="evo" viewBox="0 0 ${W} ${H}" role="img" aria-label="Costo por unidad en el tiempo">`;
    [0, 0.5, 1].forEach((p) => { const v = tope * p, y = ty(v); s += `<line x1="${L}" x2="${W - R}" y1="${y}" y2="${y}" style="stroke:var(--line-soft)"/><text x="${L - 4}" y="${y + 3}" text-anchor="end" class="eje">S/ ${fn(v, tope < 20 ? 2 : 0)}</text>`; });
    // Los meses se cuentan con números: un Date que suma meses en la hora
    // local se corre de día (31 → 1) y de mes al pasarlo a ISO.
    const meses = [], [y1, m1] = D.fin.slice(0, 7).split('-').map(Number);
    for (let [y, m] = desde.slice(0, 7).split('-').map(Number); y < y1 || (y === y1 && m <= m1); m === 12 ? (y++, m = 1) : m++) meses.push(`${y}-${String(m).padStart(2, '0')}`);
    const paso = Math.max(1, Math.ceil(meses.length / 7));
    meses.forEach((m, i) => { if (i % paso === 0 && tx(m + '-01') < W - R - 30) s += `<text x="${tx(m + '-01')}" y="${H - B + 13}" class="eje">${mesTxt(m)}</text>`; });
    if (x.costo_hoy) s += `<line x1="${L}" x2="${W - R}" y1="${ty(x.costo_hoy)}" y2="${ty(x.costo_hoy)}" style="stroke:var(--text-muted)" stroke-dasharray="3 3"/><text x="${L + 4}" y="${ty(x.costo_hoy) - 4}" class="eje rotulo">receta hoy S/ ${fn(x.costo_hoy, 2)}</text>`;
    normales.forEach((o) => { s += `<circle cx="${tx(o[O_FECHA])}" cy="${ty(o[O_PUNIT])}" r="3" class="pto" data-tip="${esc(`<b>${fecha(o[O_FECHA])} · orden ${o[O_ORDEN]}</b>${cant(o[O_CANT])} ${x.unid} · S/ ${fn(o[O_PUNIT], 2)} por ${x.unid}<br>${o[O_AREA]}`)}"/>`; });
    if (M.length) s += `<polyline points="${M.map((m) => `${tx(m[0] + '-15')},${ty(m[1])}`).join(' ')}" fill="none" style="stroke:var(--accent-deep)" stroke-width="2"/>` + M.map((m) => `<circle cx="${tx(m[0] + '-15')}" cy="${ty(m[1])}" r="2.5" style="fill:var(--accent-deep)" data-tip="${esc(`<b>${mesTxt(m[0])}</b>S/ ${fn(m[1], 2)} por ${x.unid} · ${m[2]} ${m[2] === 1 ? 'orden' : 'órdenes'}`)}"/>`).join('');
    O.filter((o) => o[O_ATIPICO]).forEach((o) => { const arriba = !(o[O_PUNIT] > 0) || o[O_PUNIT] > tope; s += `<text x="${tx(o[O_FECHA])}" y="${arriba ? T + 8 : ty(o[O_PUNIT]) + 4}" text-anchor="middle" class="rara" data-tip="${esc(`<b>${fecha(o[O_FECHA])} · orden ${o[O_ORDEN]}</b>S/ ${fn(o[O_PUNIT], 2)} por ${x.unid}<br><i>fuera de escala: no entra en el costo del mes</i>`)}">▲</text>`; });
    E.forEach((e) => { if (e[0].slice(0, 10) >= desde) s += `<text x="${tx(e[0].slice(0, 10))}" y="${H - B - 2}" text-anchor="middle" class="edic" data-tip="${esc(`<b>${fecha(e[0])} · receta editada</b>${e[1] ? 'por ' + e[1] + '<br>' : ''}${e[2] != null ? `costo ${e[2] >= 0 ? '+' : '−'}S/ ${fn(Math.abs(e[2]), 2)} por ${x.unid}` : ''}`)}">▼</text>`; });
    return s + '</svg>';
  }
  function grafSemanas(x) {
    const u = D.semanas.usado[x.cod] || [], p = D.semanas.prod[x.cod] || [], L0 = D.semanas.lunes;
    if (!u.some((v) => v) && !p.some((v) => v)) return '';
    const W = anchoGraf(), H = 74, L = 6, B = 14, n = L0.length, cw = (W - L * 2) / n, mx = Math.max(...u, ...p, 0.001);
    let s = `<svg class="sem" viewBox="0 0 ${W} ${H}" role="img" aria-label="Producido contra usado, por semana">`;
    for (let i = 0; i < n; i++) {
      const x0 = L + i * cw, hu = (H - B - 4) * (u[i] || 0) / mx, hp = (H - B - 4) * (p[i] || 0) / mx;
      s += `<rect x="${x0 + cw * 0.14}" y="${H - B - hu}" width="${cw * 0.34}" height="${hu}" rx="1.5" class="b-usado"/><rect x="${x0 + cw * 0.52}" y="${H - B - hp}" width="${cw * 0.34}" height="${hp}" rx="1.5" style="fill:var(--accent)"/>`;
      s += `<rect x="${x0}" y="0" width="${cw}" height="${H}" fill="transparent" data-tip="${esc(`<b>semana del ${fecha(L0[i])}</b>usado ${cant(u[i])} ${x.unid} · producido ${cant(p[i])}`)}"/>`;
      if (i % 3 === 0) s += `<text x="${x0 + cw / 2}" y="${H - 2}" text-anchor="middle" class="eje">${fecha(L0[i])}</text>`;
    }
    return `<div class="bl"><div class="bl-t">${n} semanas<span>usado por las ventas · producido por órdenes</span></div>${s}</svg><div class="ley"><span><i class="b-usado"></i>usado</span><span><i style="background:var(--accent)"></i>producido</span></div></div>`;
  }
  function pestProducciones(x) {
    const O = (D.ordenes[x.cod] || []).slice().reverse();
    const raras = O.filter((o) => o[O_ATIPICO]).length;
    return `<div class="bl"><div class="bl-t">Costo por unidad<span>${O.length ? `${fn(O.length)} órdenes desde ${fecha(O[O.length - 1][O_FECHA])}` : ''}</span></div>${grafEvo(x)}
        ${O.length ? `<div class="ley"><span><i class="pto-ley"></i>una orden</span><span><i style="background:var(--accent-deep)"></i>costo del mes</span><span>┄ receta hoy</span><span class="ambar">▲ fuera de escala${raras ? ` (${raras})` : ''}</span>${D.hay_log ? '<span class="edic-ley">▼ receta editada</span>' : ''}</div>` : ''}</div>
      ${grafSemanas(x)}
      ${O.length ? `<div class="bl"><div class="bl-t">Órdenes<span>de la más nueva</span></div><table class="r"><thead><tr><th>Fecha</th><th>Área</th><th>Cant.</th><th>S/ por ${esc(x.unid)}</th><th>Valor</th></tr></thead><tbody>
        ${O.slice(0, 60).map((o) => `<tr class="${o[O_ATIPICO] ? 'rara' : ''}"><td>${fecha(o[O_FECHA])}</td><td>${esc(o[O_AREA])}</td><td>${cant(o[O_CANT])}</td><td>${o[O_PUNIT] > 0 ? fn(o[O_PUNIT], 2) : '—'}</td><td>${soles(o[O_VALOR])}</td></tr>`).join('')}</tbody></table>${O.length > 60 ? `<div class="ley">Las 60 más nuevas de ${fn(O.length)}.</div>` : ''}</div>` : ''}`;
  }
  function pestDonde(x) {
    const P = (D.donde[S.vent] || {})[x.cod] || [], padres = (D.padres[x.cod] || []).filter(([p]) => F.has(p));
    const mx = Math.max(...P.map((r) => r[W_USADO] || 0), 0.001), ind = P.filter((r) => !r[W_DIRECTO]).length;
    let h = `<div class="bl"><div class="bl-t">Platos vendidos que la llevan<span>${VENT.find((v) => v[0] === S.vent)[1]} · lo que usó cada uno</span></div>`;
    h += P.length ? `<div class="mini">${P.map((r) => `<span title="${esc(r[W_PLATO])}${r[W_DIRECTO] ? '' : ' · adentro de otra receta base'}">${esc(r[W_PLATO])}${r[W_DIRECTO] ? '' : ' <span class="gris">↳</span>'}</span><span class="b"><i style="width:${(100 * (r[W_USADO] || 0) / mx).toFixed(0)}%"></i></span><span class="d">${cant(r[W_USADO])} ${esc(x.unid)}</span><span class="d">${fn(r[W_VENDIDOS])} vend.</span>`).join('')}</div>${ind ? `<div class="ley">↳ la lleva adentro de otra receta base (${ind} de ${P.length})</div>` : ''}` : '<div class="nota">Ningún plato vendido la llevó en el período.</div>';
    h += '</div>';
    if (padres.length) h += `<div class="bl"><div class="bl-t">Recetas base que la llevan adentro<span>cuánto por unidad de la de afuera</span></div><div class="mini">${padres.map(([p, c]) => { const pf = F.get(p); return `<span><button type="button" class="abrir sin" data-ir="${esc(p)}">${esc(pf.nombre)}</button></span><span></span><span class="d">${cant(c)} ${esc(x.unid)}</span><span class="d">por ${esc(pf.unid)}</span>`; }).join('')}</div></div>`;
    if (x.desc) h += `<div class="bl"><div class="bl-t">Cómo la descargan<span>${x.desc[0]} líneas de recetas la nombran</span></div><div class="nota">${x.desc[1]} por insumo · ${x.desc[0] - x.desc[1]} como producto${x.ddProd ? ' — siendo DD, las de producto piden una orden que nadie hace' : ''}.</div></div>`;
    return h;
  }
  function pestCambios(x) {
    if (!D.hay_log) return '<div class="nota">El log de ediciones del Almacén no está en R2 (faltan las filas «recetabaselog» y «recetabaselogdet» del Sheet).</div>';
    const E = (D.ediciones[x.cod] || []).slice().reverse();
    if (!E.length) return '<div class="nota">El log del Almacén no tiene ediciones de esta receta.</div>';
    return `<div class="bl"><div class="bl-t">Ediciones de la receta<span>el costo, con los precios de antes de cada una</span></div>
      ${E.map(([t, usr, d, cs]) => `<div class="ed"><div class="t"><b>${fecha(t)} · ${t.slice(11)}</b><span>${esc(usr || '')}${d != null ? ` · <span class="${d > 0 ? 'ambar' : 'verde'}">${d >= 0 ? '+' : '−'}S/ ${fn(Math.abs(d), 2)} por ${esc(x.unid)}</span>` : ''}</span></div>
        ${cs.length ? `<ul>${cs.map(([ins, a, b, so]) => `<li>${esc(ins)}: ${!a ? `agregado, ${cant(b)}` : !b ? `quitado (era ${cant(a)})` : `${cant(a)} → ${cant(b)}`}${so ? ` · ${so >= 0 ? '+' : '−'}S/ ${fn(Math.abs(so), 2)}` : ''}</li>`).join('')}</ul>` : ''}</div>`).join('')}
      <div class="ley">Todas las de la cocina, con filtros por insumo y usuario, en «Cambios Recetas Base», la vista de abajo.</div></div>`;
  }
  function ficha() {
    const z = q('[data-zona="ficha"]');
    if (!S.sel || !F.has(S.sel)) { z.innerHTML = '<div class="fcuerpo"><div class="nota">Ninguna receta con este filtro.</div></div>'; return; }
    const x = fila(S.sel);
    const nE = (D.ediciones[x.cod] || []).length, nO = (D.ordenes[x.cod] || []).length;
    const tabs = [['receta', 'Receta'], ['prod', 'Producciones', nO], ['donde', 'Dónde se usa'], ['cambios', 'Cambios', nE]];
    const cuerpo = { receta: pestReceta, prod: pestProducciones, donde: pestDonde, cambios: pestCambios }[S.tab](x);
    z.innerHTML = `<div class="fcab">
        ${S.pila.length ? `<button type="button" class="volver" data-volver="1">← volver a ${esc((F.get(S.pila[S.pila.length - 1]) || {}).nombre || '')}</button>` : ''}
        <div class="fnom"><span>${esc(x.nombre)}</span><small>${esc(x.area || '—')} · por ${esc(x.unid)}${x.activa ? '' : ' · inactiva'}</small></div>
        <div class="cifs"><div class="cif"><span>Última orden</span><b>${soles(x.ultimo)}</b><small>${x.f_ultimo ? fecha(x.f_ultimo) : 'nunca'}</small></div>
          <div class="cif"><span>Receta hoy</span><b>${soles(x.costo_hoy)}</b><small>${x.brecha != null ? `${varTxt(x.brecha)} vs. la orden` : 'precios de hoy'}</small></div>
          <div class="cif"><span>12 meses</span><b class="${x.var >= U.var ? 'ambar' : x.var <= -U.var ? 'verde' : ''}">${varTxt(x.var) || '—'}</b><small>${x.linea.length ? `${x.linea.length} meses con órdenes` : 'sin órdenes'}</small></div></div></div>
      <div class="tabs">${tabs.map(([k, r, n]) => `<button type="button" data-tab="${k}" class="${S.tab === k ? 'on' : ''}">${r}${n ? `<sup>${n}</sup>` : ''}</button>`).join('')}</div>
      <div class="fcuerpo">${veredicto(x)}${cuerpo}</div>`;
  }

  cabecera(); indicadores(); lista(); ficha();
  const l = q('[data-zona="lista"]'), on = l.querySelector('tr.on');
  if (on && raiz.__d.llevar) { const r = on.getBoundingClientRect(), c = l.getBoundingClientRect(); if (r.top < c.top + 24 || r.bottom > c.bottom) l.scrollTop += r.top - c.top - 60; }
  raiz.__d.llevar = false;
}

function enlazar(raiz) {
  const tip = () => raiz.querySelector('[data-zona="tip"]');
  raiz.addEventListener('click', (ev) => {
    const S = raiz.__d.st, t = ev.target;
    const v = t.closest('[data-vent]'); if (v) { S.vent = v.dataset.vent; dibujar(raiz); return; }
    const k = t.closest('[data-ind]'); if (k) { S.ind = S.ind === k.dataset.ind ? null : k.dataset.ind; dibujar(raiz); return; }
    const o = t.closest('[data-orden]'); if (o) { S.orden = o.dataset.orden; dibujar(raiz); return; }
    const ir = t.closest('[data-ir]');
    if (ir) {
      ev.stopPropagation();
      if (raiz.__d.x.F.has(ir.dataset.ir)) { S.pila.push(S.sel); S.sel = ir.dataset.ir; S.tab = 'receta'; Object.assign(S, { ind: null, q: '', area: '', prod: 'todas' }); raiz.__d.llevar = true; dibujar(raiz); }
      return;
    }
    if (t.closest('[data-volver]')) { S.sel = S.pila.pop(); raiz.__d.llevar = true; dibujar(raiz); return; }
    const ab = t.closest('[data-abrir]'); if (ab) { const key = ab.dataset.abrir; if (S.abiertos.has(key)) S.abiertos.delete(key); else S.abiertos.add(key); dibujar(raiz); return; }
    const tb = t.closest('[data-tab]'); if (tb) { S.tab = tb.dataset.tab; dibujar(raiz); return; }
    const tr = t.closest('tr[data-cod]'); if (tr) { S.sel = tr.dataset.cod; S.pila = []; dibujar(raiz); }
  });
  raiz.addEventListener('change', (ev) => {
    const S = raiz.__d.st, a = ev.target.dataset.acc;
    if (a === 'area') S.area = ev.target.value; else if (a === 'prod') S.prod = ev.target.value; else return;
    dibujar(raiz);
  });
  raiz.addEventListener('input', (ev) => {
    if (ev.target.dataset.acc !== 'buscar') return;
    raiz.__d.st.q = ev.target.value;
    dibujar(raiz);
  });
  raiz.addEventListener('mousemove', (ev) => {
    const t = tip(), e = ev.target.closest('[data-tip]');
    if (!t) return;
    if (!e) { t.style.display = 'none'; return; }
    t.innerHTML = e.dataset.tip; t.style.display = 'block';
    const r = raiz.getBoundingClientRect(), w = t.offsetWidth, h = t.offsetHeight;
    let left = ev.clientX - r.left + 14, top = ev.clientY - r.top + 14;
    if (left + w > r.width - 4) left = ev.clientX - r.left - w - 14;
    if (ev.clientY + 14 + h > window.innerHeight - 4) top = ev.clientY - r.top - h - 14;
    t.style.left = `${Math.max(0, left)}px`; t.style.top = `${Math.max(0, top)}px`;
  });
  raiz.addEventListener('mouseleave', () => { const t = tip(); if (t) t.style.display = 'none'; });
}

export default function (component) {
  const { data, parentElement } = component;
  if (!data || !data.filas) return;
  let raiz = parentElement.querySelector('.rb');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'rb';
    raiz.innerHTML = `<div class="cab" data-zona="cab"></div><div class="kpis" data-zona="kpis"></div>
      <div class="cuerpo"><div class="caja lista"><div class="lista-cab" data-zona="lcab"></div><div class="lista-w" data-zona="lista"></div></div>
      <aside class="caja ficha" data-zona="ficha" aria-label="Ficha de la receta"></aside></div>
      <div class="tip" data-zona="tip"></div>`;
    parentElement.appendChild(raiz);
    raiz.__d = { st: { vent: data.ventana || '90', area: '', prod: 'todas', q: '', ind: null, orden: 'vendidos', sel: null, tab: 'receta', abiertos: new Set(), pila: [] } };
    enlazar(raiz);
  }
  if (raiz.__d.data !== data) { raiz.__d.data = data; raiz.__d.x = armarDatos(data); }
  dibujar(raiz);
}
