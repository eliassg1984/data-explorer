// Stock › «Movimientos por Tipo» (reglas #738 y #747). Vive en el shadow root
// de su componente (graficos/inventario_movimientos_pieza.py). Python manda
// el período ya elegido —con el reloj «De conteo a conteo» o el de las
// «Fechas del calendario»— y todo lo demás se resuelve acá: filtros,
// búsqueda, el área en foco, la cascada, las pestañas, la ficha de un
// producto y el Excel. Lo único que vuelve a Python es «comparar» (traer el
// otro reloj para la pestaña «Los dos relojes»).
//
// STOCKMOV son las cuentas, puras: `calcular` rehace
// `inventario_movimientos.armar_movimientos` y el test las compara.
const STOCKMOV = (() => {
  const sum = (rs, k) => rs.reduce((a, r) => a + (r[k] || 0), 0);
  const cmp = (a, b) => a < b ? -1 : a > b ? 1 : 0;
  const plano = s => String(s ?? '').normalize('NFKD').replace(/[^\x00-\x7F]/g, '').toLowerCase();
  const key = r => r._key || JSON.stringify([r.area_cod, r.cod]);

  function agrupar(rs, fn) {
    const m = new Map();
    for (const r of rs) {
      const k = typeof fn === 'function' ? fn(r) : r[fn];
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(r);
    }
    return m;
  }

  function preparar(P) {
    const df = o => o.filas.map(f => Object.fromEntries(o.columnas.map((c, j) => [c, f[j]])));
    const base = df(P.base), mov = df(P.mov), ini = df(P.ini), fin = df(P.fin);
    for (const r of base) { r._key = key(r); r._needle = plano(r.producto + ' ' + r.cod); }
    for (const r of mov) r._key = key(r);
    for (const r of [...ini, ...fin]) r._key = JSON.stringify([r.area, r.cod]);
    return {P, base, mov, ini, fin};
  }

  // La base se filtra ANTES de elegir una fila por área y producto: un
  // código repetido con otra familia entra por la que pasa el filtro.
  function calcular(B, s) {
    const palabras = plano(s.q || '').split(/\s+/).filter(Boolean), base = [], indice = new Map();
    for (const r of B.base) {
      if (s.areas?.length && !s.areas.includes(r.area) || s.familias?.length && !s.familias.includes(r.familia)
          || !palabras.every(p => r._needle.includes(p))) continue;
      const k = key(r);
      if (!indice.has(k)) { indice.set(k, r); base.push(r); }
    }
    const m = B.mov.filter(r => indice.has(key(r))).map(r => ({...r, ...indice.get(key(r)), neto: r.val_in - r.val_out}));
    const tipos = [...agrupar(m, r => JSON.stringify([r.grupo, r.tipo]))].map(([, rs]) => ({
      grupo: rs[0].grupo, tipo: rs[0].tipo, nombre: rs[0].nombre,
      ...Object.fromEntries(['val_in', 'val_out', 'neto', 'movs', 'anul', 'movs_sin_costo'].map(c => [c, sum(rs, c)]))}));
    const orden = new Map(B.P.grupos.map(([g], j) => [g, j]));
    tipos.sort((a, b) => orden.get(a.grupo) - orden.get(b.grupo) || cmp(a.tipo, b.tipo));
    const puntos = rs => rs.filter(r => indice.has(r._key)).map(r => ({...r, ...indice.get(r._key), v: r.stock * r.precio}));
    const fi = puntos(B.ini), ff = puntos(B.fin), byI = agrupar(fi, 'area'), byF = agrupar(ff, 'area'), byM = agrupar(m, 'area');
    const areas = [...new Set([...byI.keys(), ...byF.keys(), ...byM.keys()])].sort(cmp).map(area => {
      const ls = byM.get(area) || [], r = {area, ini: sum(byI.get(area) || [], 'v'), fin: sum(byF.get(area) || [], 'v')};
      for (const [g] of B.P.grupos) r[g] = sum(ls.filter(l => l.grupo === g), 'neto');
      r.valorizacion = r.fin - r.ini - B.P.grupos.reduce((a, [g]) => a + r[g], 0);
      r.bruto = B.P.grupos.reduce((a, [g]) => a + Math.abs(r[g]), 0);
      return r;
    }).filter(r => r.bruto > .5 || Math.abs(r.ini) > .5 || Math.abs(r.fin) > .5)
      .sort((a, b) => b.bruto - a.bruto || Math.abs(b.fin) - Math.abs(a.fin));
    const netos = Object.fromEntries(B.P.grupos.map(([g]) => [g, sum(tipos.filter(t => t.grupo === g), 'neto')]));
    const ini = sum(fi, 'v'), fin = sum(ff, 'v');
    const sin_costo = [...agrupar(m.filter(r => r.cant_sin_costo > 1e-9), r => JSON.stringify([r.producto, r.area]))].map(([, rs]) => {
      const precio = rs.find(r => r.precio_hoy != null)?.precio_hoy ?? null, cant = sum(rs, 'cant_sin_costo');
      return {producto: rs[0].producto, area: rs[0].area, cant, movs: sum(rs, 'movs_sin_costo'), precio_hoy: precio, valor_hoy: cant * (precio || 0)};
    }).sort((a, b) => b.valor_hoy - a.valor_hoy || b.movs - a.movs);
    return {base, m, fi, ff, ini, fin, tipos, areas, sin_costo, netos,
            valorizacion: fin - ini - Object.values(netos).reduce((a, b) => a + b, 0), movs: sum(tipos, 'movs')};
  }

  // Por producto: al empezar + lo que movió + valorización = al terminar.
  // `neto` trae el conteo adentro; `mov` es lo demás y `ajustes`, el conteo.
  function productos(B, M) {
    const bi = agrupar(M.fi, 'cod'), bf = agrupar(M.ff, 'cod'), bm = agrupar(M.m, 'cod');
    return [...agrupar(M.base, 'cod')].map(([cod, bs]) => {
      const ls = bm.get(cod) || [], ini = sum(bi.get(cod) || [], 'v'), fin = sum(bf.get(cod) || [], 'v'), neto = sum(ls, 'neto');
      const grupos = Object.fromEntries(B.P.grupos.map(([g]) => [g, sum(ls.filter(r => r.grupo === g), 'neto')]));
      return {cod, producto: bs[0].producto, familia: bs[0].familia, ini, fin, neto, ajustes: grupos.ajustes || 0,
              mov: neto - (grupos.ajustes || 0), cambio: fin - ini, valorizacion: fin - ini - neto, movs: sum(ls, 'movs'),
              areas: new Set(bs.map(r => r.area)).size, grupos};
    });
  }

  function cascada(B, M) {
    const rs = [{g: 'ini', nombre: 'Stock inicial', v: M.ini, a: 0, b: M.ini, total: true}];
    let saldo = M.ini;
    for (const [g, nombre] of B.P.grupos) {
      const v = M.netos[g];
      if (g === 'otros' && Math.abs(v) < .5) continue;
      rs.push({g, nombre, v, a: saldo, b: saldo + v});
      saldo += v;
    }
    rs.push({g: 'valorizacion', nombre: 'Valorización', v: M.valorizacion, a: saldo, b: saldo + M.valorizacion});
    rs.push({g: 'fin', nombre: 'Stock final', v: M.fin, a: 0, b: M.fin, total: true});
    return rs;
  }

  // El otro reloj viaja por área y familia (`resumen_por_area`): se filtra
  // por las dos, no por la búsqueda.
  function resumenOtro(P, areas, familias) {
    const o = P.otro;
    if (!o) return null;
    const c = Object.fromEntries(o.columnas.map((k, j) => [k, j])), out = {ini: 0, fin: 0, netos: {}};
    for (const [g] of P.grupos) out.netos[g] = 0;
    for (const f of o.filas) {
      if (areas.length && !areas.includes(f[c.area]) || familias.length && !familias.includes(f[c.familia])) continue;
      out.ini += f[c.ini]; out.fin += f[c.fin];
      for (const [g] of P.grupos) out.netos[g] += f[c[g]] || 0;
    }
    out.valorizacion = out.fin - out.ini - Object.values(out.netos).reduce((a, b) => a + b, 0);
    return out;
  }

  return {preparar, calcular, productos, cascada, resumenOtro, agrupar, sum, plano, cmp};
})();
window.__stockMovDatos = STOCKMOV;

export default function (component) {
  window.__stockMov?.cleanup();
  const P = component.data, B = STOCKMOV.preparar(P), owner = component.parentElement.ownerDocument;
  const abort = new AbortController(), enviar = component.setTriggerValue;
  let root = component.parentElement.querySelector('.imv');
  if (!root) { root = owner.createElement('div'); root.className = 'imv'; component.parentElement.append(root); }

  // ── Formatos: soles sin decimales y con el signo de verdad («−S/ 9,934»).
  const esc = x => String(x ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const ent = v => v == null || !isFinite(v) ? '—' : (Math.round(v) < 0 ? '−' : '') + Math.abs(Math.round(v)).toLocaleString('en-US');
  const soles = v => v == null || !isFinite(v) ? '—' : (Math.round(v) < 0 ? '−' : '') + 'S/ ' + Math.abs(Math.round(v)).toLocaleString('en-US');
  const sg = v => (Math.round(v) < 0 ? '−' : Math.round(v) > 0 ? '+' : '') + Math.abs(Math.round(v)).toLocaleString('en-US');
  const cant = v => v == null ? '—' : Number(v).toLocaleString('en-US', {maximumFractionDigits: 2});
  const mil = (v, corto, entero) => {
    const a = Math.abs(v), s = Math.round(v) < 0 ? '−' : '';
    if (a < 1000) return (Math.round(a) ? s : '') + Math.round(a).toLocaleString('en-US');
    return s + (a / 1000).toLocaleString('en-US', {maximumFractionDigits: a < 100000 && !entero ? 1 : 0}) + (corto ? 'k' : ' mil');
  };
  const cl = v => v < -.5 ? 'neg' : v > .5 ? 'pos' : '';
  const ABR = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
  const fecha = s => { const [y, m, d] = String(s).split('-').map(Number); return `${d} ${ABR[m - 1]} ${y}`; };
  const rot = a => P.rotulos[a] || a;
  const NOMBRE = {ini: 'Al empezar', fin: 'Al terminar', compras: 'Compras', ventas: 'Ventas', ajustes: 'Conteo',
                  salidas: 'Notas de salida', produccion: 'Producción y porc.', entre: 'Entre áreas', otros: 'Otros',
                  valorizacion: 'Valorización'};
  const ORDENES = [['ajustes', 'Lo que dejó el conteo'], ['valorizacion', 'Valorización'], ['cambio', 'Cambio de stock'],
                   ['mov', 'Entradas y salidas'], ['ini', 'Stock al empezar'], ['fin', 'Stock al terminar']];
  const TABS = [['productos', 'Productos'], ['tipos', 'Tipos de documento'], ['sincosto', 'Vendido sin costo'], ['relojes', 'Los dos relojes']];
  const op = P.reloj === 'op', K = 'stock_mov_747';

  // ── Estado: lo elegido se recuerda en la pestaña (sessionStorage).
  let ui = {};
  try { ui = JSON.parse(sessionStorage.getItem(K) || '{}') || {}; } catch (e) {}
  const ini = ui.comun === P.comun ? ui : P.inicial;
  const s = {
    areas: Array.isArray(ini.areas) ? ini.areas.filter(x => P.areas.includes(x)) : [],
    familias: Array.isArray(ini.familias) ? ini.familias.filter(x => P.familias.includes(x)) : [],
    q: typeof ini.q === 'string' ? ini.q : '',
    foco: P.areas.includes(ui.foco) ? ui.foco : null,
    tab: TABS.some(([t]) => t === ui.tab) ? ui.tab : 'productos',
    grupo: null, cod: typeof ui.cod === 'string' ? ui.cod : null,
    porden: ORDENES.some(([o]) => o === ui.porden) ? ui.porden : 'ajustes',
    pedido: false,
  };
  let Mall, M, pr = [], scope = '', limite = 150, detalle = null;
  const guardar = () => {
    try { sessionStorage.setItem(K, JSON.stringify({areas: s.areas, familias: s.familias, q: s.q, foco: s.foco, tab: s.tab,
                                                    cod: s.cod, porden: s.porden, comun: P.comun})); } catch (e) {}
  };

  const filtro = (k, t, ops) => `<details class="imv-filtro" data-filter="${k}"><summary data-resumen="${k}">${t}</summary>
    <div class="imv-pop"><button type="button" data-a="limpiar" data-v="${k}" class="imv-link">Todas</button>
    ${ops.map((v, j) => `<label><input type="checkbox" data-filter="${k}" data-i="${j}">${esc(rot(v))}</label>`).join('')}</div></details>`;

  root.innerHTML = `
    <div class="imv-top">
      <p class="imv-ventana" data-k="ventana"></p>
      <div class="imv-controles">${filtro('areas', 'Áreas', P.areas)}${P.familias.length ? filtro('familias', 'Familias', P.familias) : ''}
        <input type="search" data-k="q" aria-label="Buscar producto o código" placeholder="Buscar producto o código…">
        <button type="button" data-a="excel" class="imv-btn">Excel ↓</button></div>
    </div>
    <div class="imv-aviso" data-k="aviso" hidden></div>
    <div class="imv-kpis" data-k="kpis"></div>
    <div class="imv-cuerpo">
      <section class="imv-panel">
        <div class="imv-phead"><h3 data-k="g-tit">La cuenta del stock</h3><span data-k="chip"></span></div>
        <div class="imv-chart" data-k="chart"></div>
        <p class="imv-pie" data-k="g-pie"></p>
      </section>
      <section class="imv-panel">
        <div class="imv-phead"><h3>Por área</h3><span class="imv-pista">un clic arma su cuenta</span></div>
        <div class="imv-areas" data-k="areas" role="list"></div>
      </section>
    </div>
    <section class="imv-panel imv-abajo">
      <div class="imv-tabs" role="tablist" data-k="tabs"></div>
      <div data-k="tab"></div>
    </section>`;

  const $ = q => root.querySelector(q), out = (k, h) => { $(`[data-k="${k}"]`).innerHTML = h; };
  $('[data-k=q]').value = s.q;

  // ── Lo que cambia con el ámbito y el foco.
  function recalcular() {
    const k = JSON.stringify([s.areas, s.familias, s.q]);
    if (k !== scope || !Mall) { Mall = STOCKMOV.calcular(B, s); scope = k; M = null; }
    if (s.foco && !Mall.areas.some(r => r.area === s.foco)) s.foco = null;
    if (!M || M._foco !== s.foco) {
      M = s.foco ? STOCKMOV.calcular(B, {...s, areas: [s.foco]}) : Mall;
      if (M !== Mall) M._foco = s.foco; else M._foco = null;
      pr = []; detalle = null;
    }
  }

  function ventana() {
    const p = P.periodo;
    if (op && p) {
      const exc = p.excepciones || [];
      // El cierre físico (regla #752): se cuenta el día 1 por la mañana y la
      // apertura en el sistema llega después; lo digitado hasta ella es del
      // mes que cerró.
      const otras = exc.length ? ` Abrió el conteo otro día: ${exc.map(([a, t]) => `${esc(rot(a))}, ${esc(t)}`).join('; ')}.` : '';
      const dias = p.dias.toLocaleString('en-US', {maximumFractionDigits: 1});
      const horas = `title="Se cuenta el día 1 por la mañana; el conteo se abre en el sistema después (la mayoría, el ${p.t0} y el ${p.t1}). Lo digitado hasta la apertura es del mes que cerró; la venta y la compra del mes nuevo registradas antes, del suyo."`;
      const mes = p.desde && p.hasta ? ` · del ${esc(p.desde)} al ${esc(p.hasta)}` : '';
      return p.en_curso
        ? `<span ${horas}>Desde el conteo del <b>${esc(p.cierre_ant)}</b> hasta el último movimiento del kardex (${p.t1})${mes} · ${dias} días.</span> El período sigue abierto: el stock al terminar es el del sistema, todavía sin contar.${otras}`
        : `<span ${horas}>Del conteo del <b>${esc(p.cierre_ant)}</b> al del <b>${esc(p.cierre)}</b>${mes} · ${dias} días · el mes que se contó.</span> Las puntas son lo contado; lo digitado hasta que se abrió el conteo es de este mes.${otras}`;
    }
    return `Del <b>${fecha(P.desde)}</b> al <b>${fecha(P.hasta)}</b>, por la fecha de cada movimiento en el kardex. Las puntas son el stock del sistema al cierre del día anterior y del último día: cuadra con los reportes del POS por fecha.`;
  }

  function aviso() {
    if (op) return '';
    const dentro = P.conteos.filter(c => c.dentro), fuera = P.conteos.filter(c => !c.dentro);
    const neg = Mall.areas.flatMap(a => [...(a.ini < -100 ? [`${esc(rot(a.area))} al empezar (${soles(a.ini)})`] : []),
                                         ...(a.fin < -100 ? [`${esc(rot(a.area))} al terminar (${soles(a.fin)})`] : [])]);
    if (!dentro.length && !fuera.length && !neg.length) return '';
    const partes = [];
    if (dentro.length) partes.push(`Este rango incluye ${dentro.map(c => `<b>${esc(c.nombre)}</b> (${esc(c.etiqueta)})`).join(', ')}: el conteo de ${Mall.netos.ajustes < 0 ? 'faltante' : 'sobrante'} (${soles(Mall.netos.ajustes)}) es de ${dentro.length > 1 ? 'esos conteos' : 'ese conteo'}.`);
    if (fuera.length) partes.push(`${fuera.map(c => `<b>${esc(c.nombre)}</b> (${esc(c.etiqueta)})`).join(', ')} queda afuera: cae en el mes siguiente.`);
    partes.push('Las puntas son el stock del sistema antes de contar' + (neg.length ? `; en negativo: ${neg.slice(0, 4).join(', ')}.` : '.'));
    partes.push('Para leer un mes, elegí «De conteo a conteo» arriba.');
    return partes.join(' ');
  }

  function kpis() {
    const cambio = M.fin - M.ini, aj = M.netos.ajustes || 0, contado = op && !P.periodo?.en_curso;
    const k = (v, t, val, sub, clase = '') => `<button type="button" class="imv-kpi" data-a="paso" data-v="${v}">
      <span class="imv-kpi-rot">${t}</span><span class="imv-kpi-val ${clase}">${val}</span><span class="imv-kpi-sub">${sub}</span></button>`;
    out('kpis', [
      k('ini', 'Stock al empezar', soles(M.ini), op ? 'lo contado al cerrar el mes anterior' : 'lo que decía el sistema', M.ini < -.5 ? 'neg' : ''),
      k('fin', 'Stock al terminar', soles(M.fin), `${sg(cambio)} en el período · ${contado ? 'lo contado' : 'según el sistema'}`, M.fin < -.5 ? 'neg' : ''),
      k('ajustes', 'Lo que dejó el conteo', soles(aj), op ? (aj < -.5 ? 'faltante neto del conteo del mes' : 'sobrante neto del conteo del mes')
        : 'ajustes de los conteos dentro del rango', cl(aj)),
      k('valorizacion', 'Valorización', soles(M.valorizacion), 'cambio de precio sin movimiento'),
    ].join(''));
    out('g-tit', `La cuenta del stock · ${s.foco ? esc(rot(s.foco)) : 'todas las áreas'}`);
    out('chip', s.foco ? `<span class="imv-chip">${esc(rot(s.foco))}<button type="button" data-a="foco" data-v="" aria-label="Ver todas las áreas">✕</button></span>` : '');
  }

  // ── La cascada: al empezar + cada grupo + valorización = al terminar.
  function chart() {
    const caja = $('[data-k=chart]'), W = Math.max(280, Math.round(caja.clientWidth || 640)), H = 236;
    // Angosta (el celular), un nombre corto por barra en dos renglones
    // alternados y las cifras sin decimales: si no, se pisan.
    const rs = STOCKMOV.cascada(B, M), n = rs.length, an = (W - 8) / n, corto = an < 60, angosto = an < 48;
    const vals = rs.flatMap(r => [r.a, r.b]), hi = Math.max(1, ...vals), lo = Math.min(0, ...vals), T = 18, F = 34;
    const y = v => T + (hi - v) / ((hi - lo) || 1) * (H - T - F);
    let h = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Stock al empezar más movimientos y valorización igual a stock al terminar">`;
    h += `<line class="cero" x1="0" x2="${W}" y1="${y(0)}" y2="${y(0)}"/>`;
    rs.forEach((r, j) => {
      const x = 4 + j * an, w = an * .7, x0 = x + an * .15, top = y(Math.max(r.a, r.b)), alto = Math.max(1, Math.abs(y(r.a) - y(r.b)));
      const clase = r.total ? 'b-t' : r.g === 'valorizacion' ? 'b-v' : r.v >= 0 ? 'b-p' : 'b-n';
      const pal = (corto ? {ini: 'Inicio', fin: 'Fin', produccion: 'Prod.', salidas: 'Notas', entre: 'Entre', valorizacion: 'Valoriz.'}[r.g] : null)
        || NOMBRE[r.g] || r.nombre;
      const ws = pal.split(' '), med = Math.ceil(ws.length / 2);
      const [l1, l2] = angosto ? (j % 2 ? ['', pal] : [pal, '']) : [ws.slice(0, med).join(' '), ws.slice(med).join(' ')];
      const etq = r.total || Math.round(r.v) === 0 ? mil(r.v, corto, angosto) : (r.v >= 0 ? '+' : '') + mil(r.v, corto, angosto);
      h += `<g data-a="paso" data-v="${r.g}" data-i="${j}" tabindex="0" role="button" aria-label="${esc(NOMBRE[r.g] || r.nombre)}: ${soles(r.v)}">
        <rect class="toque" x="${x}" y="${T - 14}" width="${an}" height="${H - T - F + 14}"/>
        <rect class="${clase}" x="${x0}" y="${top}" width="${w}" height="${alto}" rx="3"/>
        <text class="v${angosto ? ' chica' : ''}" x="${x0 + w / 2}" y="${Math.max(11, top - 5)}" text-anchor="middle">${etq}</text>
        <text x="${x0 + w / 2}" y="${H - 19}" text-anchor="middle">${esc(l1)}</text><text x="${x0 + w / 2}" y="${H - 7}" text-anchor="middle">${esc(l2)}</text></g>`;
      if (j < n - 1) h += `<line class="con" x1="${x0 + w}" x2="${x0 + an}" y1="${y(r.b)}" y2="${y(r.b)}"/>`;
    });
    caja.innerHTML = h + '</svg><div class="imv-tip" hidden></div>';
    caja._rs = rs; caja._an = an; caja._W = W;
    out('g-pie', op ? 'Al empezar + lo que entró y salió + valorización = al terminar. «Entre áreas» suma cero en el total y explica cada área. Un clic en una barra abre su detalle.'
                    : 'Por calendario, «Conteo» trae los conteos que caen dentro del rango, que suelen ser los del mes anterior. Un clic en una barra abre su detalle.');
  }

  function ficha(r) {
    const t = M.tipos.filter(x => x.grupo === r.g).sort((a, b) => Math.abs(b.neto) - Math.abs(a.neto)).slice(0, 3);
    const de = r.total ? '' : `<br><span class="imv-tenue">de ${soles(r.a)} a ${soles(r.b)}</span>`;
    const tipos = t.length > 1 ? '<br>' + t.map(x => `${esc(x.nombre)}: ${soles(x.neto)}`).join('<br>') : '';
    return `<b>${esc(NOMBRE[r.g] || r.nombre)}</b><br>${soles(r.v)}${de}${tipos}`;
  }

  function areas() {
    const fila = (v, nombre, a, b, c, on) => `<button type="button" class="imv-area${on ? ' on' : ''}" data-a="foco" data-v="${esc(v)}" aria-pressed="${on}" role="listitem">
      <span class="n">${esc(nombre)}</span><span class="d ${a < -50 ? 'neg' : ''}">${ent(a)}</span><span class="d ${b < -50 ? 'neg' : ''}">${ent(b)}</span>
      <span class="d x ${cl(c)}">${Math.abs(c) > .5 ? sg(c) : '—'}</span></button>`;
    out('areas', `<div class="imv-area enc" aria-hidden="true"><span>Área</span><span class="d">Al empezar</span><span class="d">Al terminar</span><span class="d x">Conteo</span></div>`
      + fila('', 'Todas las áreas', Mall.ini, Mall.fin, Mall.netos.ajustes || 0, !s.foco)
      + (Mall.areas.map(a => fila(a.area, rot(a.area), a.ini, a.fin, a.ajustes || 0, s.foco === a.area)).join('')
         || '<p class="imv-vacio">Sin stock ni movimientos con estos filtros.</p>'));
  }

  // ── Las pestañas.
  function tabs() {
    const n = M.sin_costo.length;
    out('tabs', TABS.filter(([t]) => t !== 'sincosto' || n).map(([t, nombre]) =>
      `<button type="button" role="tab" data-a="tab" data-v="${t}" aria-selected="${s.tab === t}">${nombre}${t === 'sincosto' ? ` · ${n}` : ''}</button>`).join(''));
    if (s.tab === 'sincosto' && !n) s.tab = 'productos';
    ({productos: tabProductos, tipos: tabTipos, sincosto: tabSinCosto, relojes: tabRelojes})[s.tab]();
  }

  function lote(k, rs, html, vacio) {
    const tb = $(`[data-k="${k}"]`), wrap = tb.closest('.imv-wrap');
    root.querySelector(`[data-lote="${k}"]`)?.remove();
    tb.innerHTML = rs.length ? '' : `<tr><td colspan="8">${vacio || 'Sin registros.'}</td></tr>`;
    let fin = 0;
    const b = owner.createElement('button');
    b.type = 'button'; b.dataset.lote = k; b.className = 'imv-mas';
    const mas = () => {
      const end = Math.min(fin + 150, rs.length);
      tb.insertAdjacentHTML('beforeend', rs.slice(fin, end).map(html).join(''));
      fin = end; b.hidden = fin >= rs.length; b.textContent = `Mostrar más · ${fin} de ${rs.length}`;
    };
    mas(); wrap.after(b); b.onclick = mas;
    wrap.onscroll = () => { if (!b.hidden && wrap.scrollTop + wrap.clientHeight >= wrap.scrollHeight - 70) mas(); };
    wrap.scrollTop = 0;
  }

  const num = v => `<td class="num ${cl(v)}">${ent(v)}</td>`, liso = v => `<td class="num">${ent(v)}</td>`;

  function listaProductos() {
    return STOCKMOV.productos(B, M).filter(r => Math.abs(r.ini) + Math.abs(r.fin) + Math.abs(r.neto) > .5 || r.movs > 0)
      .sort((a, b) => Math.abs(b[s.porden]) - Math.abs(a[s.porden]) || STOCKMOV.cmp(a.producto, b.producto));
  }

  function tabProductos() {
    out('tab', `<div class="imv-fila"><label class="imv-sel"><span>Ordenar por</span><select data-k="porden">${ORDENES.map(([v, t]) =>
        `<option value="${v}"${v === s.porden ? ' selected' : ''}>${t}</option>`).join('')}</select></label>
        <span class="imv-pista" data-k="productos-pie"></span></div>
      <div class="imv-prod"><div class="imv-lista"><div class="imv-wrap" data-k="prod-wrap"><table><thead><tr><th>Producto</th><th>Al empezar</th>
        <th>Entradas y salidas</th><th>Conteo</th><th>Valorización</th><th>Al terminar</th></tr></thead><tbody data-k="productos-tabla"></tbody></table></div>
        <button type="button" data-a="mas" class="imv-mas"></button></div><div class="imv-ficha" data-k="ficha"></div></div>`);
    pr = listaProductos();
    filasProductos();
    fichaProducto();
  }

  function filasProductos(reset = true) {
    if (reset) {
      detalle = pr.find(r => r.cod === s.cod) || pr[0] || null;
      s.cod = detalle?.cod || null;
      limite = Math.max(150, Math.ceil((pr.indexOf(detalle) + 1) / 150) * 150);
    }
    out('productos-tabla', pr.slice(0, limite).map(r => `<tr data-a="producto" data-v="${esc(r.cod)}" tabindex="0" class="${r.cod === s.cod ? 'on' : ''}" aria-selected="${r.cod === s.cod}">
      <td>${esc(r.producto)}<small>${esc(r.cod)} · ${esc(r.familia)} · ${r.areas} ${r.areas === 1 ? 'área' : 'áreas'}</small></td>
      ${['ini', 'mov', 'ajustes', 'valorizacion', 'fin'].map(k => num(r[k])).join('')}</tr>`).join('')
      || '<tr><td colspan="6">Sin productos con stock o movimientos.</td></tr>');
    const b = $('[data-a=mas]');
    b.hidden = limite >= pr.length; b.textContent = `Mostrar más · ${Math.min(limite, pr.length)} de ${pr.length}`;
    out('productos-pie', `${pr.length.toLocaleString('en-US')} productos · por la mayor diferencia, positiva o negativa`);
  }

  function fichaProducto() {
    if (!detalle) { out('ficha', '<p class="imv-vacio">Elegí un producto de la lista.</p>'); return; }
    const r = detalle, ls = M.m.filter(x => x.cod === r.cod);
    const rs = [...STOCKMOV.agrupar(ls, x => JSON.stringify([x.area, x.tipo]))].map(([, g]) => ({area: g[0].area, tipo: g[0].tipo, nombre: g[0].nombre,
      ...Object.fromEntries(['val_in', 'val_out', 'neto', 'movs'].map(k => [k, STOCKMOV.sum(g, k)]))})).sort((a, b) => Math.abs(b.neto) - Math.abs(a.neto));
    out('ficha', `<h4>${esc(r.producto)}</h4><p class="imv-pista">${esc(r.cod)} · ${esc(r.familia)} · ${r.areas} ${r.areas === 1 ? 'área' : 'áreas'}${s.foco ? ' en ' + esc(rot(s.foco)) : ''}</p>
      <p class="imv-cuenta">Al empezar <b>${soles(r.ini)}</b> + entradas y salidas <b>${soles(r.mov)}</b> + conteo <b>${soles(r.ajustes)}</b>
        + valorización <b>${soles(r.valorizacion)}</b> = al terminar <b>${soles(r.fin)}</b>.</p>
      <p class="imv-pista">La valorización es lo que no explican los movimientos registrados: no es una salida más.</p>
      <div class="imv-wrap"><table><thead><tr><th>Área</th><th class="t">Tipo</th><th>Entró</th><th>Salió</th><th>Neto</th><th>Movs.</th></tr></thead>
      <tbody data-k="producto-tipos"></tbody></table></div>`);
    lote('producto-tipos', rs, x => `<tr><td>${esc(rot(x.area))}</td><td class="t">${esc(x.nombre)}<small>${esc(x.tipo)}</small></td>${liso(x.val_in)}${liso(x.val_out)}${num(x.neto)}<td class="num">${ent(x.movs)}</td></tr>`);
  }

  function tabTipos() {
    const rs = M.tipos.filter(r => !s.grupo || r.grupo === s.grupo), nombreG = g => P.grupos.find(([x]) => x === g)?.[1] || g;
    let grupo = '';
    out('tab', `<div class="imv-fila"><span class="imv-pista">${ent(M.movs)} movimientos${s.foco ? ' en ' + esc(rot(s.foco)) : ''}</span>
      ${s.grupo ? `<span class="imv-chip">${esc(nombreG(s.grupo))}<button type="button" data-a="grupo" aria-label="Ver todos los tipos">✕</button></span>` : ''}</div>
      <div class="imv-wrap"><table><thead><tr><th>Tipo de documento</th><th>Entró</th><th>Salió</th><th>Neto</th><th>Movs.</th></tr></thead><tbody>${rs.map(r => {
        const cab = r.grupo !== grupo ? `<tr class="grupo"><td colspan="5">${esc(nombreG(r.grupo))}</td></tr>` : '';
        grupo = r.grupo;
        return cab + `<tr><td>${esc(r.nombre)}<small>${esc(r.tipo)}${r.movs_sin_costo ? ' · ' + ent(r.movs_sin_costo) + ' sin costo' : ''}${r.anul ? ' · ' + ent(r.anul) + ' anulados' : ''}</small></td>
          ${liso(r.val_in)}${liso(r.val_out)}${num(r.neto)}<td class="num">${ent(r.movs)}</td></tr>`;
      }).join('') || '<tr><td colspan="5">Sin movimientos con estos filtros.</td></tr>'}</tbody>
      <tfoot><tr><td>Total${s.grupo ? ' del grupo' : ''}</td>${liso(STOCKMOV.sum(rs, 'val_in'))}${liso(STOCKMOV.sum(rs, 'val_out'))}${num(STOCKMOV.sum(rs, 'neto'))}
        <td class="num">${ent(STOCKMOV.sum(rs, 'movs'))}</td></tr></tfoot></table></div>`);
  }

  function tabSinCosto() {
    const rs = M.sin_costo, sin = rs.filter(r => r.precio_hoy == null).length;
    out('tab', `<p class="imv-pista">${ent(STOCKMOV.sum(rs, 'movs'))} movimientos · ${new Set(rs.map(r => r.producto)).size} productos ·
      ≈ ${soles(STOCKMOV.sum(rs, 'valor_hoy'))} a precio actual${sin ? ` · ${sin} sin precio actual` : ''}. Estas salidas de ventas se registraron
      a costo cero; el valor a precio actual es para revisarlas y no se suma al balance.</p>
      <div class="imv-wrap"><table><thead><tr><th>Producto</th><th>Área</th><th>Movs.</th><th>Cantidad</th><th>A precio actual</th></tr></thead>
      <tbody data-k="sin-costo-tabla"></tbody></table></div>`);
    lote('sin-costo-tabla', rs, r => `<tr><td>${esc(r.producto)}</td><td>${esc(rot(r.area))}</td><td class="num">${ent(r.movs)}</td>
      <td class="num">${cant(r.cant)}</td><td class="num">${r.precio_hoy == null ? 'Sin precio actual' : ent(r.valor_hoy)}</td></tr>`);
  }

  // ── «Los dos relojes»: el mismo mes con las dos maneras de cortarlo.
  function tabRelojes() {
    const otroNombre = op ? 'Fechas del calendario' : 'De conteo a conteo';
    if (!P.otro) {
      if (!op && !P.comparable) {
        out('tab', `<p class="imv-vacio">Para comparar los dos relojes, elegí un mes entero en el calendario: «De conteo a conteo» corta por meses de conteo.</p>`);
      } else if (P.comparar || s.pedido) {
        out('tab', `<p class="imv-vacio">${s.pedido && !P.comparar ? 'Trayendo el mismo mes con ' + otroNombre.toLowerCase() + '…' : 'No se pudo leer el otro reloj. Probá de nuevo en un momento.'}</p>`);
      } else {
        out('tab', `<p class="imv-pista">Muestra este mismo mes contado de las dos maneras, renglón por renglón. Por calendario, cada mes lleva los ajustes del conteo del mes anterior y sus puntas son el stock del sistema antes de contar; de conteo a conteo, el conteo es el del mes y las puntas, lo contado.</p>
          <button type="button" class="imv-btn prim" data-a="comparar">Traer ${otroNombre.toLowerCase()}</button>`);
      }
      return;
    }
    const areas = s.foco ? [s.foco] : s.areas, este = s.foco || s.areas.length || s.familias.length || s.q
      ? STOCKMOV.calcular(B, {areas, familias: s.familias, q: ''}) : Mall;
    const otro = STOCKMOV.resumenOtro(P, areas, s.familias);
    const [cal, con] = op ? [otro, este] : [este, otro];
    // Las puntas son stock, no un movimiento: sin verde ni rojo.
    const fila = (n, a, b, punta) => `<tr class="${Math.abs(b - a) > 500 ? 'marca' : ''}${punta ? ' fuerte' : ''}"><td>${n}</td>${punta ? liso(a) + liso(b) : num(a) + num(b)}<td class="num ${Math.abs(b - a) > 500 ? '' : 'tenue'}">${sg(b - a)}</td></tr>`;
    const grupos = P.grupos.filter(([g]) => g !== 'otros' || Math.abs(cal.netos[g]) + Math.abs(con.netos[g]) > .5);
    out('tab', `<p class="imv-pista">${esc(P.periodo?.nombre || fecha(P.desde) + ' – ' + fecha(P.hasta))}${s.foco ? ' · ' + esc(rot(s.foco)) : ''}: el otro reloj es ${esc(P.otro.nombre)}.
        Usa las áreas y las familias elegidas, no la búsqueda.</p>
      <div class="imv-wrap"><table class="imv-relojes"><thead><tr><th></th><th>Fechas del calendario</th><th>De conteo a conteo</th><th>Diferencia</th></tr></thead><tbody>
      ${fila('Stock al empezar', cal.ini, con.ini, true)}${grupos.map(([g, n]) => fila(g === 'ajustes' ? 'Conteo' : n, cal.netos[g], con.netos[g])).join('')}
      ${fila('Valorización', cal.valorizacion, con.valorizacion)}${fila('Stock al terminar', cal.fin, con.fin, true)}</tbody></table></div>
      <p class="imv-pista">Lo marcado es lo que más cambia entre los dos: las puntas (el stock del sistema contra lo contado) y el conteo que cae adentro.</p>`);
  }

  // ── Todo junto.
  function render() {
    recalcular();
    for (const k of ['areas', 'familias']) {
      const el = $(`[data-resumen=${k}]`);
      if (el) el.textContent = (k === 'areas' ? 'Áreas' : 'Familias') + (s[k].length ? ' · ' + s[k].length : '');
      root.querySelectorAll(`input[data-filter=${k}]`).forEach(i => { i.checked = s[k].includes(P[k][Number(i.dataset.i)]); });
    }
    out('ventana', ventana());
    const av = aviso();
    $('[data-k=aviso]').hidden = !av; out('aviso', av);
    kpis(); chart(); areas(); tabs(); guardar();
  }

  function enfocar(v) {
    s.foco = v && s.foco !== v ? v : null;
    s.grupo = null;
    recalcular(); kpis(); chart(); areas(); tabs(); guardar();
  }

  function exportar() {
    const hs = [], hoja = (nombre, cabeza, filas) => hs.push({nombre, cabeza, filas, decimales: 6});
    const frame = (nombre, rs, cs) => hoja(nombre, cs, rs.map(r => cs.map(k => r[k])));
    frame('Tipos del recorte', M.tipos, ['grupo', 'tipo', 'nombre', 'val_in', 'val_out', 'neto', 'movs', 'anul', 'movs_sin_costo']);
    frame('Areas del recorte', Mall.areas, ['area', 'ini', ...P.grupos.map(([g]) => g), 'valorizacion', 'fin']);
    frame('Productos del recorte', listaProductos(), ['cod', 'producto', 'familia', 'ini', 'mov', 'ajustes', 'neto', 'valorizacion', 'fin', 'cambio', 'movs', 'areas']);
    frame('Ventas sin costo', M.sin_costo, ['producto', 'area', 'cant', 'movs', 'precio_hoy', 'valor_hoy']);
    hoja('Base recibida', P.base.columnas, P.base.filas);
    const ids = new Set(B.base.map(r => JSON.stringify([r.area_cod, r.cod])));
    frame('Fuente movimientos', B.mov.filter(r => ids.has(JSON.stringify([r.area_cod, r.cod]))), P.mov.columnas);
    const foto = rs => rs.filter(r => ids.has(JSON.stringify([r.area, r.cod])));
    frame('Foto inicial', foto(B.ini), P.ini.columnas);
    frame('Foto final', foto(B.fin), P.fin.columnas);
    frame('Grafico', STOCKMOV.cascada(B, M), ['g', 'nombre', 'v', 'a', 'b', 'total']);
    const p = P.periodo;
    hoja('Contexto', ['Campo', 'Valor'], [
      ['Reloj', op ? 'De conteo a conteo' : 'Fechas del calendario'],
      ...(op && p ? [['Mes', `${p.desde || ''} – ${p.hasta || ''}`], ['Apertura del conteo inicial (mayoría)', p.t0], ['Apertura del conteo final (mayoría)', p.t1], ['Días', p.dias]] : [['Desde incluido', P.desde], ['Hasta incluido', P.hasta]]),
      ['Areas locales', s.areas.join(', ') || 'Todas'], ['Area en foco', s.foco || 'Todas'], ['Familias locales', s.familias.join(', ') || 'Todas'],
      ['Busqueda por palabras', s.q], ['Grupo de detalle', s.grupo || 'Todos'], ['Orden productos', 'Magnitud de ' + s.porden],
      ['Fuentes', 'Sin filtros locales; sólo códigos/áreas presentes en la base recibida. Base conserva sus duplicados para aplicar filtros antes de elegir una fila por código/área.'],
      ['Valorizacion', 'Final - inicial - movimientos netos. No es una salida adicional.'],
      ['Grafico', 'Otros menor a S/ 0.50 se omite del dibujo; las cifras completas permanecen en totales y fuentes.'],
      ['Ventas sin costo', 'Valor a precio actual aproximado, separado del balance y del costo registrado. Precio ausente se identifica.'],
      ['Cantidades', 'No sumar cantidades entre productos.'], ...Object.entries(P.contexto)]);
    bajar(archivo('Movimientos Stock ' + (op && p ? p.nombre : P.desde + ' ' + P.hasta)) + '.xlsx', libro(hs));
  }

  // ── Eventos.
  root.addEventListener('input', e => {
    if (e.target.matches('[data-k=q]')) { s.q = e.target.value; s.grupo = null; render(); }
  }, {signal: abort.signal});
  root.addEventListener('change', e => {
    const el = e.target;
    if (el.matches('input[data-filter]')) {
      const k = el.dataset.filter, v = P[k][Number(el.dataset.i)];
      s[k] = el.checked ? [...new Set([...s[k], v])] : s[k].filter(x => x !== v);
      s.grupo = null; render();
    } else if (el.dataset.k === 'porden') {
      s.porden = el.value; pr = listaProductos(); filasProductos(); fichaProducto(); guardar();
    }
  }, {signal: abort.signal});
  root.addEventListener('click', e => {
    const el = e.composedPath().find(x => x?.dataset?.a);
    if (!el || !root.contains(el)) return;
    const a = el.dataset.a, v = el.dataset.v;
    if (a === 'excel') exportar();
    else if (a === 'limpiar') { s[v] = []; s.grupo = null; render(); }
    else if (a === 'foco') enfocar(v);
    else if (a === 'tab') { s.tab = v; tabs(); guardar(); }
    else if (a === 'grupo') { s.grupo = null; tabTipos(); }
    else if (a === 'mas') { limite += 150; filasProductos(false); }
    else if (a === 'comparar') { s.pedido = true; tabRelojes(); enviar('comparar', P.sello); }
    else if (a === 'producto') {
      s.cod = v; detalle = pr.find(r => r.cod === v);
      for (const tr of root.querySelectorAll('tr[data-a=producto]')) {
        tr.classList.toggle('on', tr.dataset.v === v); tr.setAttribute('aria-selected', tr.dataset.v === v);
      }
      fichaProducto(); guardar();
    } else if (a === 'paso') {
      if (P.grupos.some(([g]) => g === v) && v !== 'ajustes') { s.grupo = s.grupo === v ? null : v; s.tab = 'tipos'; }
      else { s.porden = v === 'ajustes' ? 'ajustes' : v === 'valorizacion' ? 'valorizacion' : v === 'ini' ? 'ini' : 'fin'; s.tab = 'productos'; }
      tabs(); guardar();
      $('[data-k=tabs]').scrollIntoView?.({block: 'nearest', behavior: 'smooth'});
    }
  }, {signal: abort.signal});
  const tip = () => $('[data-k=chart] .imv-tip');
  root.addEventListener('pointerover', e => {
    const g = e.composedPath().find(x => x?.dataset?.a === 'paso' && x.tagName === 'g');
    const caja = $('[data-k=chart]'), t = tip();
    if (!g || !t || !caja._rs) return;
    const r = caja._rs[Number(g.dataset.i)];
    t.innerHTML = ficha(r); t.hidden = false;
    const x = 4 + Number(g.dataset.i) * caja._an, w = t.offsetWidth;
    t.style.left = `${Math.min(caja._W - w, Math.max(0, x))}px`; t.style.top = '0px';
  }, {signal: abort.signal});
  root.addEventListener('pointerout', e => {
    if (e.composedPath().some(x => x?.dataset?.a === 'paso' && x.tagName === 'g')) { const t = tip(); if (t) t.hidden = true; }
  }, {signal: abort.signal});
  root.addEventListener('keydown', e => {
    if (e.key === 'Escape') for (const d of root.querySelectorAll('details.imv-filtro[open]')) d.open = false;
    const el = e.composedPath().find(x => x?.dataset?.a);
    if (el?.matches('tr,g') && ['Enter', ' '].includes(e.key)) {
      e.preventDefault();
      el.dispatchEvent(new MouseEvent('click', {bubbles: true, composed: true}));
    }
  }, {signal: abort.signal});
  root.addEventListener('scroll', e => {
    const w = e.target;
    if (w?.matches?.('[data-k=prod-wrap]') && limite < pr.length && w.scrollTop + w.clientHeight >= w.scrollHeight - 70) {
      limite += 150; filasProductos(false);
    }
  }, {signal: abort.signal, capture: true});

  let ancho = 0;
  const resize = new ResizeObserver(es => {
    const w = es[0].contentRect.width;
    if (Math.abs(w - ancho) > 1) { ancho = w; if (M) chart(); }
  });
  resize.observe($('[data-k=chart]'));

  window.__stockMov = {P, B, s, render, enfocar, get M() { return M; }, get Mall() { return Mall; },
    get productos() { return pr; }, get detalle() { return detalle; },
    cleanup: () => { abort.abort(); resize.disconnect(); }};
  render();
}
