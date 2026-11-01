// Recetas › «Costo de Carta» (reglas #696, #746 y #775).
//
// La monta graficos/carta_costeada.py con st.components.v2 (sin iframe,
// estilos en un shadow root); `_xlsx.js` (libro, bajar, archivo) y
// `ficha_plato.js` (FichaPlato: la receta, la evolución, «Costo y
// utilidad», el reparto y los porcionados) van antepuestos. Desde la regla
// #746, sobre el boceto aprobado
// (https://claude.ai/artifact/WwfU8asEK7P6S97C1nrir7): una fila de
// desplegables, cuatro indicadores que filtran, la lista ordenada por lo que
// cuesta en soles y UNA ficha al costado con Resumen | Receta | Evolución |
// Canales. Hasta ese día el plato salía tres veces —la fila, la ficha del
// costado y la de abajo— con cifras de canales distintos.
//
// Todo lo que se elige acá lo resuelve el navegador. A Python vuelven:
// `elegir` (el producto: trae su receta y su evolución, que la ficha espera
// con su aviso), `simular` ({cod, estado, n}), `cambios` ({cod, n}),
// `nuevo_costeo` ({cod, n}) y `produccion` ({destino, cod, n}).
//
// Python manda en `data`: `filas` (ver carta_costeada.armar_pieza),
// `canales` ([nombre, unidades vendidas en el rango]), `divisor` (precio →
// neto), `rango`, `sel`, `sin_precio`, `umbrales` ([30, 35]), `grupo_vi`,
// `ayuda` y `ficha` (armar_ficha del elegido, o null).

const F = { cod: 0, grupo: 1, sub: 2, prod: 3, tipo: 4, activo: 5, oferta: 6, desc: 7, receta: 8, ultima: 9,
  precios: 10, costos: 11, vend: 12, vneto: 13, vcosto: 14, sinc: 15, combo: 16, otros: 17 };
const CLAVE = 'cc_est_v2';
const MAX_FILAS = 800;
const ESPERA_TECLADO = 350;
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const TIPOS = ['Receta', 'Directo', 'Combo', 'Sin enlace', 'No aplica'];
const PESTANAS = [['resumen', 'Resumen'], ['receta', 'Receta'], ['evo', 'Evolución'], ['canales', 'Canales']];
const COLUMNAS_EXTRA = [['costo', 'Costo y precio'], ['margen', 'Margen por plato'], ['receta', 'Receta guardada']];
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento */ } }
const sinTilde = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
function dinero(v, dec = 2) {
  if (v == null || !isFinite(v)) return '—';
  const s = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  return `${v < 0 ? '−' : ''}S/ ${s}`;
}
const pct = (v) => (v == null || !isFinite(v) ? '—' : `${v.toFixed(1)} %`);
const num = (n) => Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 1 });
const signo = (v) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(1)} %`;
function fecha(s) {
  if (!s) return '—';
  const [y, m, d] = s.split('-');
  return `${+d} ${MESES[+m - 1]} ${y.slice(2)}`;
}

// ── Lo de un producto en un canal ────────────────────────────────────────
// Lo vendido en el canal 0 («En el Local») es el total menos los otros.
function vendidoCanal(f, c) {
  const otros = f[F.otros] || {};
  if (c > 0) {
    const v = otros[c];
    return v ? { u: v[0], neto: v[1], costo: v[2] } : { u: 0, neto: 0, costo: 0 };
  }
  let u = f[F.vend], neto = f[F.vneto], costo = f[F.vcosto];
  Object.values(otros).forEach(([ou, on, oc]) => { u -= ou; neto -= on; costo -= oc; });
  return { u: Math.max(0, u), neto: Math.max(0, neto), costo: Math.max(0, costo) };
}
function enCanal(d, f, c) {
  const precio = f[F.precios][c], costo = f[F.costos][c];
  const neto = precio ? precio / d.divisor : 0;
  const v = vendidoCanal(f, c);
  return {
    precio, neto, costo, sinCosto: !(costo > 0), seVende: precio > 0,
    // «Sin descargo» en el POS: su costo ES cero, no se observa (regla #761).
    sinDescargo: f[F.tipo] === 'No aplica',
    pct: precio && costo > 0 ? costo / neto * 100 : null,
    margen: precio && costo > 0 ? neto - costo : null,
    u: v.u, vneto: v.neto, vcosto: v.costo,
    pctV: v.neto > 0.5 && v.costo > 0 ? v.costo / v.neto * 100 : null,
  };
}
// Lo que se pagó de más en el rango por estar sobre la meta: el costo de hoy
// de lo vendido menos la meta sobre lo COBRADO (con sus descuentos), no sobre
// el precio de carta. Pura: la lee test_costo_carta.py.
function exceso(d, x) {
  if (x.sinCosto || !(x.u > 0)) return 0;
  return Math.max(0, x.costo * x.u - d.umbrales[0] / 100 * x.vneto);
}
function nivel(d, p) {
  if (p == null) return 'nulo';
  return p > d.umbrales[1] ? 'rojo' : p > d.umbrales[0] ? 'ambar' : '';
}
const haceSeis = (() => { const h = new Date(); h.setMonth(h.getMonth() - 6); return h.toISOString().slice(0, 10); })();
const vieja = (f) => f[F.tipo] === 'Receta' && f[F.receta] && f[F.receta] < haceSeis;

// ── Qué filas entran ─────────────────────────────────────────────────────
function base(d, st) {
  return d.filas.filter((f) => (st.inactivos || f[F.activo])
    && (st.vi || f[F.grupo].toLowerCase() !== d.grupo_vi.toLowerCase())
    && (st.modo !== 'combos' || f[F.tipo] === 'Combo'));
}
function filtrar(d, st, filas) {
  const q = sinTilde(st.q.trim()), c = st.canal;
  return filas.filter((f) => {
    if (st.grupo && f[F.grupo] !== st.grupo) return false;
    if (st.tipo && f[F.tipo] !== st.tipo) return false;
    if (st.oferta != null && f[F.oferta] !== st.oferta) return false;
    if (q && !sinTilde(f[F.prod]).includes(q) && !f[F.cod].includes(q)) return false;
    const x = enCanal(d, f, c);
    if ((st.alerta || st.ver === 'novend') && !x.seVende) return false;
    if (st.ver === 'novend' && x.u > 0) return false;
    if (st.ver === 'vieja' && !vieja(f)) return false;
    if (st.alerta === 'ex' && !(exceso(d, x) > 0)) return false;
    if (st.alerta === 'sobre' && !(x.pct > d.umbrales[1])) return false;
    if (st.alerta === 'datos' && !((x.sinCosto && !x.sinDescargo) || f[F.sinc] > 0 || x.pct > 60)) return false;
    return true;
  });
}
const ORDEN = {
  pct: (d, f, c) => enCanal(d, f, c).pct ?? -1, costo: (d, f, c) => f[F.costos][c],
  margen: (d, f, c) => enCanal(d, f, c).margen ?? -1e9, vend: (d, f, c) => enCanal(d, f, c).u,
  vneto: (d, f, c) => enCanal(d, f, c).vneto, receta: (d, f) => f[F.receta] || '0',
  ex: (d, f, c) => exceso(d, enCanal(d, f, c)), prod: (d, f) => sinTilde(f[F.prod]),
};
function ordenar(d, st, filas) {
  const k = ORDEN[st.orden] || ORDEN.ex, dir = st.asc ? 1 : -1;
  // Empates (lo mucho que no se pasa de la meta) por la venta neta.
  return filas.map((f) => [k(d, f, st.canal), enCanal(d, f, st.canal).vneto, f])
    .sort((a, b) => (a[0] < b[0] ? -dir : a[0] > b[0] ? dir : b[1] - a[1])).map((x) => x[2]);
}

// ── Indicadores: cada uno filtra la lista ────────────────────────────────
function htmlKpis(d, st, filas) {
  const c = st.canal, [u0, u1] = d.umbrales;
  let costoU = 0, netoU = 0, vc = 0, vn = 0, sobre = 0, sobreV = 0, entre = 0, sinC = 0, sinCN = 0, raros = 0;
  const ex = [];
  filas.forEach((f) => {
    const x = enCanal(d, f, c);
    if (!x.seVende) return;
    if (!x.sinCosto && x.u > 0) { costoU += x.costo * x.u; netoU += x.vneto; }
    vc += x.vcosto; vn += x.vneto;
    if (x.pct > u1) { sobre++; if (x.u > 0) sobreV++; } else if (x.pct > u0) entre++;
    if (x.sinCosto && !x.sinDescargo) sinC++;
    if (x.pct > 60) raros++;
    sinCN += f[F.sinc];
    const e = exceso(d, x);
    if (e > 0) ex.push(e);
  });
  ex.sort((a, b) => b - a);
  const exT = ex.reduce((s, v) => s + v, 0), arriba = ex.slice(0, 7).reduce((s, v) => s + v, 0);
  const hoy = netoU ? costoU / netoU * 100 : null, vend = vn > 0.5 ? vc / vn * 100 : null;
  const kpi = (id, rot, val, sub, cls, extra = '', tit = '') => `<button type="button" class="cc-kpi${st.alerta === id && id ? ' on' : ''}" data-acc="alerta" data-id="${id}" ${id ? '' : 'disabled'} title="${esc(tit)}">
      <span class="cc-kpi-rot">${rot}</span><span class="cc-kpi-lin"><span class="cc-kpi-val ${cls || ''}">${val}</span>${extra}</span><span class="cc-kpi-sub">${sub}</span></button>`;
  const meta = hoy != null ? `<span class="cc-meta" aria-hidden="true"><i class="${nivel(d, hoy) || 'ok'}" style="width:${Math.min(100, hoy * 2)}%"></i><b style="left:${u0 * 2}%"></b></span>` : '';
  return [
    kpi('', '% costo · meta 30 %', pct(hoy), `${vend != null ? `se vendió al ${pct(vend)}` : 'sin ventas en el rango'} · meta ${u0} %`, nivel(d, hoy), meta,
      'Costo de hoy de lo vendido ÷ lo cobrado, en el canal. «Se vendió al»: con el costo que guardó el POS en cada pedido.'),
    kpi('ex', `Sobre el ${u0} %, en soles`, dinero(exT, 0),
      ex.length ? `${ex.length} ${ex.length === 1 ? 'plato' : 'platos'} · ${Math.min(7, ex.length)} son el ${Math.round(arriba / exT * 100)} %` : `ningún plato vendido sobre el ${u0} %`,
      exT ? 'rojo' : '', '', `Costo de hoy × vendidos − ${u0} % de lo cobrado, en el rango y el canal: lo que se pagó de más por estar sobre la meta. Un clic deja esos platos, de mayor a menor.`),
    kpi('sobre', `Sobre ${u1} %`, String(sobre), `${sobreV} con ventas · ${entre} entre ${u0} y ${u1} %`, sobre ? 'rojo' : '', '',
      `Platos con precio en el canal cuyo costo de hoy pasa el ${u1} % del neto, se vendan o no.`),
    kpi('datos', 'Datos para revisar', String(sinC + raros), `${sinC} sin costo en el POS · ${raros} sobre 60 % · ${dinero(sinCN, 0)} a costo 0`,
      sinC + raros ? 'ambar' : '', '', 'Sin costo en el POS, vendidos a costo 0 o con un costo que pasa el 60 % del neto: casi seguro un error de receta o de factor.'),
  ].map((h, i) => '<div class="cc-kpi-zona">' + h + '<button type="button" class="cc-info" data-acc="info" data-id="' + ['costo','ex','sobre','datos'][i] + '" aria-label="Explicar indicador ' + (i + 1) + '">ⓘ</button></div>').join('');
}

// ── Una fila de desplegables ─────────────────────────────────────────────
function htmlFiltros(d, st, b) {
  const c = st.canal;
  const opt = (v, t, sel) => `<option value="${esc(v)}"${String(v) === String(sel ?? '') ? ' selected' : ''}>${esc(t)}</option>`;
  const sel = (acc, rot, opciones, valor, on) => `<label class="cc-sel${on ? ' on' : ''}"><span>${rot}</span><select data-acc="${acc}" aria-label="${rot}">${opciones.map(([v, t]) => opt(v, t, valor)).join('')}</select></label>`;
  const canales = d.canales.map(([n, u], i) => [i, `${n}${u ? ` · ${num(u)}` : ' · sin ventas'}`]);
  // El % de cada grupo: costo de hoy × lo vendido ÷ lo vendido, en el canal.
  const g = new Map();
  b.forEach((f) => {
    const x = enCanal(d, f, c);
    const a = g.get(f[F.grupo]) || { n: 0, c: 0, v: 0 };
    a.n++;
    if (!x.sinCosto && x.u > 0) { a.c += x.costo * x.u; a.v += x.vneto; }
    g.set(f[F.grupo], a);
  });
  const grupos = [['', `Todos · ${num(b.length)}`], ...[...g].sort((x, y) => y[1].n - x[1].n).map(([nombre, a]) => {
    const p = a.v ? a.c / a.v * 100 : null;
    return [nombre, `${nombre} · ${a.n}${p != null ? ` · ${pct(p)}` : ''}`];
  })];
  const out = [sel('canal', 'Canal', canales, c, c > 0), sel('grupo', 'Grupo', grupos, st.grupo, !!st.grupo)];
  if (st.modo !== 'combos') {
    const tipos = TIPOS.map((t) => [t, b.filter((f) => f[F.tipo] === t).length]).filter(([, n]) => n);
    out.push(sel('tipo', 'Tipo', [['', 'Todos'], ...tipos.map(([t, n]) => [t, `${t} · ${n}`])], st.tipo, !!st.tipo));
    if (d.filas.some((f) => f[F.oferta] >= 0)) {
      out.push(sel('oferta', 'Carta', [['', 'Impresa y no impresa'], [1, 'Carta impresa'], [0, 'No impresa']], st.oferta, st.oferta != null));
    }
  }
  const sinVer = filtrar(d, Object.assign({}, st, { alerta: null, ver: '' }), b);
  const nNovend = sinVer.filter((f) => { const x = enCanal(d, f, c); return x.seVende && !(x.u > 0); }).length;
  const nVieja = sinVer.filter(vieja).length;
  out.push(sel('ver', 'Ver', [['', 'Todos'], ['novend', `No se vendieron en el rango · ${nNovend}`],
    ['vieja', `Receta sin tocar hace 6 meses · ${nVieja}`]], st.ver, !!st.ver));
  out.push(sel('incluir', 'Incluir', [['', 'Sólo activos'], ['i', 'Con inactivos'], ['v', 'Con venta interna'],
    ['iv', 'Con inactivos y venta interna']], `${st.inactivos ? 'i' : ''}${st.vi ? 'v' : ''}`, st.inactivos || st.vi));
  const n = [c > 0, st.grupo, st.tipo, st.oferta != null, st.ver, st.inactivos || st.vi, st.alerta].filter(Boolean).length;
  if (n) out.push(`<button type="button" class="cc-link" data-acc="limpiar">Quitar filtros (${n})</button>`);
  return out.join('');
}

// ── La lista ─────────────────────────────────────────────────────────────
function cabeza(st, cols) {
  return cols.map(([id, r, cls, ayuda]) => `<th class="${cls || ''}">${id ? `<button type="button" data-acc="orden" data-id="${id}" class="${st.orden === id ? 'on' : ''}" title="${esc(ayuda || '')}">${r}${st.orden === id ? (st.asc ? ' ↑' : ' ↓') : ''}</button>` : r}</th>`).join('');
}
function chipFila(d, f, x) {
  if (x.pct > 60) return '<span class="cc-tag rojo" title="El costo de hoy pasa el 60 % del neto: casi seguro un error de receta o de factor.">revisar costo</span>';
  if (x.sinCosto && !x.sinDescargo) return '<span class="cc-tag ambar" title="El POS no le tiene costo: lo vendido entra al FoodCost a costo 0.">sin costo</span>';
  if (!f[F.activo]) return '<span class="cc-tag">inactivo</span>';
  if (f[F.tipo] !== 'Receta') return `<span class="cc-tag" title="${esc(f[F.desc] || '')}">${esc(f[F.tipo].toLowerCase())}</span>`;
  return '';
}
function htmlMenuColumnas(st) {
  if (!st.menuCols) return '';
  return `<div class="cc-colmenu" role="menu" aria-label="Columnas de la lista">${COLUMNAS_EXTRA.map(([k, r]) =>
    `<button type="button" role="menuitemcheckbox" aria-checked="${!!st.cols[k]}" data-acc="col" data-id="${k}"><i>${st.cols[k] ? '✓' : ''}</i>${r}</button>`).join('')}</div>`;
}
function htmlLista(d, st, filas) {
  const c = st.canal, [u0, u1] = d.umbrales;
  const total = filas.length, vista = filas.slice(0, MAX_FILAS);
  const pie = `<div class="cc-lpie"><span>${num(total)} productos${total > MAX_FILAS ? ` · se muestran ${MAX_FILAS}` : ''}${d.sin_precio ? ` · ${d.sin_precio} no se muestran` : ''} <button type="button" class="cc-info" data-acc="info" data-id="lista" aria-label="Qué queda fuera de esta cuenta">ⓘ</button></span>
    ${st.modo === 'combos' ? '' : `<button type="button" class="cc-link" data-acc="cols" aria-expanded="${!!st.menuCols}">Columnas ▾</button>`}</div>`;
  if (!total) return `<div class="cc-vacio">Ningún producto con estos filtros.</div>${pie}`;
  if (st.modo === 'combos') {
    const cols = [['prod', 'Combo'], ['', 'Cómo se costeó'], ['costo', 'Costo usado', 'num'], ['pct', '% costo', 'num'],
      ['', 'Mínimo', 'num'], ['', 'Promedio', 'num'], ['', 'Esperado', 'num'], ['', 'Máximo', 'num'],
      ['', 'Real 90 días', 'num'], ['vend', 'Vend.', 'num']];
    const filasH = vista.map((f) => {
      const x = enCanal(d, f, c), b = f[F.combo] || ['', '', 0, 0, 0, 0, 0, 0];
      return `<tr class="cc-f${x.pct > 60 ? ' cc-raro' : ''}${f[F.cod] === st.sel ? ' sel' : ''}" data-acc="elegir" data-cod="${esc(f[F.cod])}">
        <td class="cc-prod"><b>${esc(f[F.prod])}</b><span>${esc(b[0] || 'Combo')}</span></td><td class="cc-sub">${esc(b[1] || '—')}</td>
        <td class="num">${dinero(x.costo)}</td><td class="num"><span class="pill ${nivel(d, x.pct)}">${pct(x.pct)}</span></td>
        ${b.slice(2, 7).map((v) => `<td class="num">${v ? dinero(v) : '—'}</td>`).join('')}<td class="num">${num(x.u)}</td></tr>`;
    }).join('');
    return `<div class="cc-tabla cc-combos" tabindex="0" aria-label="Combos: flechas arriba y abajo para recorrer"><table><thead><tr>${cabeza(st, cols)}</tr></thead><tbody>${filasH}</tbody></table></div>${pie}`;
  }
  const xs = vista.map((f) => [f, enCanal(d, f, c)]);
  const maxV = Math.max(1, ...xs.map(([, x]) => x.vneto)), maxE = Math.max(1, ...xs.map(([, x]) => exceso(d, x)));
  const cols = [['prod', 'Producto', '', 'Ordenar por nombre'],
    ['pct', '% costo', 'num', 'Costo de hoy ÷ neto del canal. Debajo, al que se VENDIÓ en el rango, si se aparta 5 puntos o más'],
    ['ex', `Sobre el ${u0} %`, 'num', `Costo de hoy × vendidos − ${u0} % de lo cobrado, en el rango y el canal`],
    ['vneto', 'Venta neta', '', 'Lo vendido en el rango en este canal, sin IGV. En ámbar, lo que entró al FoodCost a costo 0'],
    ['vend', 'Vend.', 'num', 'Unidades vendidas en el rango, en este canal']];
  if (st.cols.costo) cols.push(['costo', 'Costo', 'num', 'Costo de hoy y precio del canal']);
  if (st.cols.margen) cols.push(['margen', 'Margen', 'num', 'Lo que deja cada unidad hoy: neto − costo']);
  if (st.cols.receta) cols.push(['receta', 'Receta', 'num', 'Última vez que se guardó la receta en el POS']);
  const filasH = xs.map(([f, x]) => {
    const difV = x.pctV != null && x.pct != null && Math.abs(x.pctV - x.pct) >= 5;
    const e = exceso(d, x);
    return `<tr class="cc-f${f[F.cod] === st.sel ? ' sel' : ''}${x.seVende ? '' : ' apagada'}" data-acc="elegir" data-cod="${esc(f[F.cod])}">
      <td class="cc-prod"><div><button type="button" class="cc-plato" data-acc="elegir" data-cod="${esc(f[F.cod])}" title="${esc(f[F.prod])}">${esc(f[F.prod])}</button>${st.detail || x.sinCosto || x.pct > 60 || !f[F.activo] ? chipFila(d, f, x) : ''}${!st.detail && f[F.sinc] > 0 ? '<span class="cc-dot" role="img" aria-label="Se vendió a costo cero" title="Se vendió a costo cero"></span>' : ''}</div>
        <span>${st.detail ? esc(f[F.grupo]) + ' › ' : ''}${esc(f[F.sub])}${st.detail ? (f[F.oferta] === 1 ? ' · carta impresa' : '') : ' · ' + num(x.u) + ' vendidos'}</span></td>
      <td class="num">${x.seVende ? `<span class="pill ${nivel(d, x.pct)}">${pct(x.pct)}</span>` : '<span class="cc-sub">no se vende</span>'}
        ${difV ? `<span class="cc-v ambar">${x.pctV > x.pct ? '▲' : '▼'} se vendió al ${pct(x.pctV)}</span>` : ''}</td>
      <td class="num">${e > 0 ? `<div class="cc-bar ex"><i style="width:${Math.max(2, e / maxE * 44)}px"></i><span class="num">${dinero(e, 0)}</span></div>` : '<span class="cc-sub">—</span>'}</td>
      <td><div class="cc-bar"><i style="width:${Math.max(2, x.vneto / maxV * 40)}px"></i><span class="num">${x.vneto ? dinero(x.vneto, 0) : 'sin ventas'}</span></div>
        ${f[F.sinc] > 0 ? `<span class="cc-v ambar">${dinero(f[F.sinc], 0)} a costo 0</span>` : ''}</td>
      <td class="num">${x.u ? num(x.u) : '—'}</td>
      ${st.cols.costo ? `<td class="num">${x.sinCosto ? '—' : dinero(x.costo)}<span class="cc-v">de ${x.precio ? dinero(x.precio, x.precio % 1 ? 2 : 0) : '—'}</span></td>` : ''}
      ${st.cols.margen ? `<td class="num${x.margen != null && x.margen < 10 ? ' rojo' : ''}">${x.margen == null ? '—' : dinero(x.margen)}</td>` : ''}
      ${st.cols.receta ? `<td class="num cc-sub">${f[F.tipo] === 'Receta' ? fecha(f[F.receta]) : '—'}</td>` : ''}</tr>`;
  }).join('');
  const compacta = !st.detail && !Object.values(st.cols).some(Boolean);
  return `<div class="cc-tabla${compacta ? ' cc-compacta' : ''}" tabindex="0" aria-label="Productos de la carta: flechas arriba y abajo para recorrer"><table><thead><tr>${cabeza(st, cols)}</tr></thead><tbody>${filasH}</tbody></table></div>${htmlMenuColumnas(st)}${pie}`;

}

// ── La ficha del elegido ─────────────────────────────────────────────────
function fichaCargada(raiz) {
  const { data: d, st } = raiz.__d;
  return d.ficha && d.ficha.plato && d.ficha.plato.cod === st.sel ? d.ficha : null;
}
const cargando = (txt = 'Armando la receta y la evolución…') => `<div class="cc-cargando" role="status">${txt}</div>`;

// El aviso del Resumen: lo que hay que mirar primero de este plato.
function aviso(d, st, f, x, fd) {
  const c = st.canal;
  if (!x.seVende) return ['', `No tiene precio en «${esc(d.canales[c][0])}»: no se vende por ese canal.`];
  if (x.sinDescargo) return ['', 'Está «Sin descargo» en el POS: no baja nada del almacén y su costo es cero. Lo vendido suma en la venta.'];
  if (x.sinCosto) return ['ambar', `El POS no le tiene costo: ${dinero(f[F.sinc], 0)} de lo vendido en el rango entraron al FoodCost a costo 0, y así quedan guardados.`];
  if (x.pct > 60) return ['rojo', `Hoy cuesta el ${pct(x.pct)} del neto${x.pctV != null ? ` y se vendió al ${pct(x.pctV)}` : ''}: deja ${dinero(x.margen)} por unidad. Revisar la receta o el factor de su insumo principal antes de tocar el precio.`];
  if (x.pctV != null && Math.abs(x.pctV - x.pct) >= 3) {
    const pico = fd ? FichaPlato.picoDelRango(fd) : null;
    const porque = x.pctV > x.pct
      ? (pico ? `en el rango el costo guardado fue más alto que el de hoy. ${esc(pico.x)}` : 'en algún momento el costo guardado fue más alto que el de hoy: la pestaña Evolución dice cuándo.')
      : 'la receta de hoy es más cara que la que se vendió.';
    return [pico ? 'ambar' : '', `Hoy cuesta el ${pct(x.pct)} y en el rango se vendió al ${pct(x.pctV)}: ${porque}`];
  }
  if (x.pctV != null) return ['', `Hoy cuesta el ${pct(x.pct)} y se vendió al ${pct(x.pctV)}: el costo del POS y el de la receta van parejos.`];
  return ['', `Hoy cuesta el ${pct(x.pct)}. No se vendió en el rango por este canal.`];
}

const key = (label,value) => '<div class="b-key"><span>'+label+'</span><strong>'+value+'</strong></div>';
function fold(st,id,title,body){return '<section class="b-fold"><button type="button" class="cursor-interaction" data-acc="b-fold" data-id="'+id+'" aria-expanded="'+(st.fold===id)+'"><span>'+title+'</span>'+(st.fold===id?'⌃':'⌄')+'</button><div class="b-fold-body"'+(st.fold!==id?' hidden':'')+'>'+body+'</div></section>';}
function pricing(d,x,fd){if(!x.seVende||x.sinCosto)return '<p class="b-caption">Primero se necesita un precio y un costo registrado en este canal.</p>';let out=d.umbrales.map(u=>{const p=Math.ceil(x.costo/(u/100)*d.divisor),dif=p-x.precio;return '<div class="b-price-option"><strong>Para quedar en '+u+' %</strong><strong class="num">'+dinero(p,0)+'</strong><small>o bajar el costo a '+dinero(x.neto*u/100)+'</small><small class="num">'+(dif===0?'sin cambio':(dif>0?'+':'−')+dinero(Math.abs(dif),0))+'</small></div>';}).join('');out+='<div class="b-price-option"><strong>Como está</strong><strong class="num">'+dinero(x.precio,0)+'</strong><small>deja '+dinero(x.margen)+' por unidad</small><small class="num">'+(x.u?dinero(x.margen*x.u,0)+' en el rango':'sin ventas')+'</small></div>';if(fd?.q?.pct_hab!=null)out+='<div class="b-note">Con '+esc(FichaPlato.corto(fd.q.nombre))+' a lo habitual: '+pct(fd.q.pct_hab)+' al precio de En el Local.</div>';return out;}
function htmlResumen(d,st,f,fd){const x=enCanal(d,f,st.canal),e=exceso(d,x),cf=fd?FichaPlato.cifras(fd):null,mm=cf?.mm;const per=x.sinCosto?null:Math.max(0,x.costo-x.neto*d.umbrales[0]/100);let basics=key('Precio neto',x.precio?dinero(x.neto)+' (÷ '+(+d.divisor.toFixed(3))+')':'no se vende')+key('Margen por plato',x.margen==null?'—':dinero(x.margen))+key('Vendidos en el rango',num(x.u))+key('Venta neta',dinero(x.vneto,0))+key('Se vendió al',pct(x.pctV))+key('Al vender, mes a mes',mm?dinero(mm.a)+' → '+dinero(mm.b)+' · '+MESES[+mm.ma.slice(5)-1]+' → '+MESES[+mm.mb.slice(5)-1]+' ('+signo(mm.var)+')':'sin dos meses con costo')+key('Sobre la meta por plato · carta',per==null?'—':dinero(per));
    let core='<div class="b-top-summary"><div class="b-measures"><div class="b-measure"><small>Costo hoy · '+pct(x.pct)+'</small><strong>'+(x.sinCosto?(x.sinDescargo?'Sin descargo':'Sin costo'):dinero(x.costo))+'</strong></div><div class="b-measure"><small>Precio de venta</small><strong>'+(x.precio?dinero(x.precio):'No se vende')+'</strong></div></div>'+(x.seVende&&!x.sinCosto?'<div class="b-gauge" role="img" aria-label="Costo '+pct(x.pct)+'; metas 30 y 35 por ciento"><i style="width:'+Math.min(100,x.pct)+'%"></i><b style="left:30%"></b><b style="left:35%"></b></div>':'')+'<div class="b-range-note">'+(x.sinCosto?(x.sinDescargo?'El POS lo tiene sin descargo.':'Costo pendiente de revisar.'):(e>0?dinero(e,0)+' sobre la meta en lo vendido del rango':'Dentro de la meta en lo vendido del rango'))+'</div>';
    if(f[F.sinc]>0)core+='<button type="button" class="b-signal cursor-interaction" data-acc="b-signal"><span>'+dinero(f[F.sinc],0)+' entró al FoodCost con costo 0</span><span>Por qué</span></button>';
    else if(!x.seVende||x.sinCosto||x.pct>60){const [cls,text]=aviso(d,st,f,x,fd);core+='<div class="b-note '+cls+'">'+text+'</div>';}
    core+='</div>';let folds=fold(st,'cifras','Más cifras del plato',basics)+fold(st,'precio','Qué hacer con el precio en «'+esc(d.canales[st.canal][0])+'»',pricing(d,x,fd));
    if(fd?.q)folds+=fold(st,'mueve','Qué mueve el costo de hoy',FichaPlato.htmlAvisos(fd,{sinNota:true}));
    if(f[F.combo]){const b=f[F.combo];folds+=fold(st,'combo','Combo · '+esc(b[0]||'Banda de costos'),'<p class="b-caption">'+esc(b[1])+'</p><table class="b-mini"><tbody>'+[['Mínimo',2],['Promedio',3],['Esperado',4],['Máximo',5],['Real 90 días',6]].map(([label,i])=>'<tr><td>'+label+'</td><td class="num">'+(b[i]?dinero(b[i]):'—')+'</td></tr>').join('')+'</tbody></table><p class="b-caption">El POS no costea el combo: la consulta de la carta calcula esta banda.</p>');}
    folds+=fold(st,'utilidad','Costo y utilidad por plato',fd?'<p class="b-caption">Al precio de En el Local · hoy y lo vendido</p>'+FichaPlato.htmlUtil(fd,{conObjetivos:false}):'<div class="b-note">Cargando la receta y la evolución…</div>');return '<div class="b-summary-grid">'+core+'<div class="b-folds">'+folds+'</div></div>';}

function htmlCanales(d, st, f) {
  const c = st.canal;
  const canales = d.canales.map(([n, uTot], i) => {
    const y = enCanal(d, f, i);
    return `<tr class="${i === c ? 'on' : ''}${uTot ? '' : ' apagado'}" data-acc="canal" data-id="${i}" title="${uTot ? `${num(uTot)} vendidos por este canal en el rango, toda la carta` : 'Sin ventas en el rango'}"><td>${esc(n)}${uTot ? '' : ' <small>sin ventas</small>'}</td>
      <td class="num">${y.precio ? dinero(y.precio, y.precio % 1 ? 2 : 0) : '—'}</td>
      <td class="num">${y.seVende ? `<span class="pill ${nivel(d, y.pct)}">${pct(y.pct)}</span>` : '—'}</td>
      <td class="num">${y.margen == null ? '—' : dinero(y.margen)}</td>
      <td class="num">${y.u ? num(y.u) : '—'}</td><td class="num">${pct(y.pctV)}</td></tr>`;
  }).join('');
  const difCosto = new Set(f[F.costos].filter((v) => v > 0).map((v) => v.toFixed(2))).size > 1;
  return `<div class="cc-fbloque"><div class="cc-frot"><span>${difCosto ? 'El costo cambia según el canal' : 'El costo es el mismo en los cinco canales: cambia el precio'}</span><span>vendido en el rango</span></div>
      <table class="cc-mini cc-canal-t"><thead><tr><th>Canal</th><th class="num">Precio</th><th class="num">% costo</th><th class="num">Margen</th><th class="num">Vend.</th><th class="num">% vend.</th></tr></thead><tbody>${canales}</tbody></table>
      <div class="cc-fpie">Un clic en un canal lo elige para toda la vista. «% vend.»: el costo que guardó el POS ÷ lo cobrado por ese canal.</div></div>`;
}

function htmlReceta(raiz, fd, W) {
  const fs = raiz.__d.fs;
  if (!fd.filas.length) return FichaPlato.htmlDescarga(fd);
  const hayPorc = Object.keys(fd.cortes).length > 0;
  const formas = [['lista', 'Lista'], ['rep', 'Reparto del precio'], ...(hayPorc ? [['porc', 'Porcionados']] : [])];
  if (fs.rec === 'porc' && !hayPorc) fs.rec = 'lista';
  const seg = `<div class="fp-tabs" role="tablist" aria-label="Forma de la receta">${formas.map(([k, r]) => `<button type="button" role="tab" aria-selected="${fs.rec === k}" class="${fs.rec === k ? 'on' : ''}" data-acc="rec" data-id="${k}">${r}</button>`).join('')}</div>`;
  const cuerpo = fs.rec === 'rep' ? FichaPlato.htmlRep(fd, fs, W) : fs.rec === 'porc' ? FichaPlato.htmlPorc(fd, fs) : FichaPlato.htmlReceta(fd, fs);
  return `${seg}<div class="fp-vista">${cuerpo}</div>`;
}

function htmlFicha(raiz, W) {
  const { data: d, st } = raiz.__d;
  const f = d.filas.find((x) => x[F.cod] === st.sel);
  if (!f) return '<div class="cc-vacio">Elige un producto de la lista para abrir su ficha.</div>';
  const fd = fichaCargada(raiz), receta = f[F.tipo] === 'Receta';
  const ruta = [f[F.grupo] + ' › ' + f[F.sub], f[F.tipo], st.detail && f[F.receta] ? 'receta guardada el ' + fecha(f[F.receta]) : '', st.detail && fd ? FichaPlato.lineas(fd) : ''].filter(Boolean).join(' · ');
  const menu = st.fmenu ? '<div class="cc-menu" role="menu"><button type="button" role="menuitem" data-acc="cambios" data-cod="'+esc(f[F.cod])+'">Ver cambios del precio y la receta</button>' + (receta ? '<button type="button" role="menuitem" data-acc="nuevo">Copiar receta a Nuevo Costeo</button>' : '') + '</div>' : '';
  const tabs = PESTANAS.map(([k,r]) => '<button type="button" role="tab" aria-selected="'+(st.ftab===k)+'" class="'+(st.ftab===k?'on':'')+'" data-acc="ftab" data-id="'+k+'">'+r+'</button>').join('');
  let panel;
  if (st.ftab === 'canales') panel = htmlCanales(d,st,f);
  else if (st.ftab === 'receta') panel = fd ? htmlReceta(raiz,fd,W) : cargando();
  else if (st.ftab === 'evo') panel = fd ? FichaPlato.htmlEvo(fd,raiz.__d.fs,W) : cargando();
  else panel = htmlResumen(d,st,f,fd);
  return '<div class="cc-fcab"><span class="cc-fruta">'+esc(ruta)+'</span><div class="cc-ftit"><h3>'+esc(f[F.prod])+'</h3><div class="cc-facc"><button type="button" class="cc-icon" data-acc="ampliar" aria-label="'+(st.expanded?'Volver a la lista':'Ampliar ficha')+'" title="'+(st.expanded?'Volver a la lista':'Ampliar ficha')+'">'+(st.expanded?'↙':'⤢')+'</button><button type="button" class="cc-icon" data-acc="soltar" aria-label="Soltar plato" title="Soltar plato">×</button></div></div></div>'
    + '<div class="cc-ftabs" role="tablist" aria-label="Del plato">'+tabs+'</div><div class="cc-fpanel" role="tabpanel">'+panel+'</div>'
    + '<div class="cc-fbottom">'+(receta?'<button type="button" class="cc-btn prim" data-acc="simular" data-cod="'+esc(f[F.cod])+'">Simular</button>':'')+'<button type="button" class="cc-btn soft" data-acc="cambios" data-cod="'+esc(f[F.cod])+'">Ver cambios del precio y la receta</button><span class="cc-menu-ancla"><button type="button" class="cc-icon" data-acc="fmenu" aria-expanded="'+!!st.fmenu+'" aria-label="Más acciones">⋯</button>'+menu+'</span></div>';
}

// ── El Excel: la lista que se ve, con los cinco canales ──────────────────
function excel(d, st, filas) {
  const cab = ['Código', 'Grupo', 'Subgrupo', 'Producto', 'Tipo', 'Activo', 'Carta', 'Descarga'];
  d.canales.forEach(([n]) => cab.push(`Precio ${n}`, `Neto ${n}`, `Costo ${n}`, `% costo ${n}`, `Margen ${n}`, `Vendidos ${n}`, `Venta neta ${n}`));
  cab.push('Vendidos (total)', 'Venta neta (total)', '% vendido (total)', 'Vendido sin costo', 'Receta guardada', 'Última venta',
    `Sobre el ${d.umbrales[0]} % (${d.canales[st.canal][0]})`);
  const filasX = filas.map((f) => {
    const r = [f[F.cod], f[F.grupo], f[F.sub], f[F.prod], f[F.tipo], f[F.activo] ? 'Sí' : 'No',
      f[F.oferta] === 1 ? 'Impresa' : f[F.oferta] === 0 ? 'No impresa' : '', f[F.desc]];
    d.canales.forEach((_, i) => {
      const x = enCanal(d, f, i);
      r.push(x.precio || null, x.precio ? x.neto : null, x.sinCosto ? null : x.costo, x.pct, x.margen, x.u || null, x.vneto || null);
    });
    r.push(f[F.vend] || null, f[F.vneto] || null, f[F.vneto] > 0.5 && f[F.vcosto] > 0 ? f[F.vcosto] / f[F.vneto] * 100 : null,
      f[F.sinc] || null, f[F.receta], f[F.ultima], exceso(d, enCanal(d, f, st.canal)) || null);
    return r;
  });
  const hojas = [{ nombre: st.modo === 'combos' ? 'Combos' : 'Carta', cabeza: cab, filas: filasX }];
  if (st.modo === 'combos') {
    hojas.push({ nombre: 'Banda de combos', cabeza: ['Código', 'Combo', 'Tipo', 'Cómo se costeó', 'Mínimo', 'Promedio', 'Esperado', 'Máximo', 'Real 90 días', 'Vendidos (consulta)'],
      filas: filas.filter((f) => f[F.combo]).map((f) => [f[F.cod], f[F.prod], ...f[F.combo]]) });
  }
  const nombre = `costo_de_carta_${archivo(d.canales[st.canal][0])}${d.rango ? '_' + archivo(d.rango) : ''}.xlsx`;
  bajar(nombre, libro(hojas));
}

// ── Dibujar ──────────────────────────────────────────────────────────────
function dibujar(raiz, zonas) {
  const { data: d, st } = raiz.__d;
  if (!raiz.querySelector('.cc-arriba')) {
    raiz.innerHTML = '<div class="cc-arriba"><div class="cc-cab"><div class="cc-tabs" role="tablist" aria-label="Ver" data-zona="modo"></div><div class="cc-der"><label class="cc-switch"><input type="checkbox" data-acc="detalle" role="switch">Detalle</label><button type="button" class="cc-link" data-acc="excel">Excel ↓</button><button type="button" class="cc-info" data-acc="info" data-id="calculo" aria-label="Cómo se calcula">ⓘ</button></div></div>'
      + '<div class="cc-filterline"><span class="cc-fecha-lugar" aria-hidden="true"></span><div class="cc-filtros" data-zona="filtros"></div><button type="button" class="cc-filter-button" data-acc="filtros" aria-expanded="false">Más filtros ▾</button><label class="cc-buscar"><input type="search" data-acc="buscar" placeholder="Buscar producto o código" aria-label="Buscar producto o código"></label></div><div class="cc-kpis" data-zona="kpis"></div></div>'
      + '<div class="cc-return"><button type="button" class="cc-link" data-acc="ampliar">← Volver a la lista</button></div><div class="cc-cuerpo"><div class="cc-lista" data-zona="lista"></div><div class="cc-ficha" data-zona="ficha"></div></div><div class="cc-pop" role="dialog" aria-label="Opciones de Costo de Carta" hidden></div>';
  }
  raiz.classList.toggle('cc-detail',!!st.detail);
  raiz.classList.toggle('cc-expanded',!!st.expanded);
  raiz.classList.toggle('cc-sin-ficha',!st.sel);
  const z=n=>raiz.querySelector('[data-zona="'+n+'"]');
  raiz.querySelector('[data-acc="detalle"]').checked=!!st.detail;
  raiz.querySelector('[data-acc="filtros"]').setAttribute('aria-expanded',String(st.pop==='filtros'));
  const count=[st.tipo,st.oferta!=null,st.ver,st.inactivos||st.vi].filter(Boolean).length;
  raiz.querySelector('[data-acc="filtros"]').textContent='Más filtros'+(count?' · '+count:'')+' ▾';
  z('modo').innerHTML=[['carta','Carta'],['combos','Combos']].map(([id,r])=>'<button type="button" role="tab" aria-selected="'+(st.modo===id)+'" class="'+(st.modo===id?'on':'')+'" data-acc="modo" data-id="'+id+'">'+r+'</button>').join('');
  const b=base(d,st), filas=ordenar(d,st,filtrar(d,st,b));
  raiz.__d.filas=filas;
  z('kpis').innerHTML=htmlKpis(d,st,filtrar(d,Object.assign({},st,{alerta:null}),b));
  if (!zonas || zonas.includes('filtros')) {
    const temp=document.createElement('div');temp.innerHTML=htmlFiltros(d,st,b);
    z('filtros').replaceChildren(...[...temp.children].filter(el=>['canal','grupo'].includes(el.querySelector('select')?.dataset.acc)));
  }
  const lista=z('lista'), old=lista.querySelector('.cc-tabla'), top=old?.scrollTop||0, left=old?.scrollLeft||0;
  lista.innerHTML=htmlLista(d,st,filas);
  const table=lista.querySelector('.cc-tabla');
  if (table && zonas && !zonas.includes('arriba')) {table.scrollTop=top;table.scrollLeft=left;}
  dibujarFicha(raiz); dibujarPop(raiz); medir(raiz);
}

function dibujarPop(raiz, anchor) {
  const {data:d,st}=raiz.__d,pop=raiz.querySelector('.cc-pop');
  if (!st.pop) {pop.hidden=true;return;}
  let title='',body='';
  if(st.pop==='filtros') {
    title='Más filtros';const temp=document.createElement('div');temp.innerHTML=htmlFiltros(d,st,base(d,st));
    body='<div class="cc-advanced">'+[...temp.children].filter(el=>!['canal','grupo'].includes(el.querySelector('select')?.dataset.acc)).map(el=>el.outerHTML).join('')+'</div><button type="button" class="cc-btn" data-acc="cerrar">Listo</button>';
  } else if (st.pop==='senal') {
    const f=d.filas.find(r=>r[F.cod]===st.sel),fd=fichaCargada(raiz);title='Vendido a costo 0';
    body='<div class="cc-pop-val">'+dinero(f?.[F.sinc],0)+'</div><p>'+esc(fd?.plato.sin_causa||'El POS guardó este importe vendido sin costo.')+'. El registro histórico se conserva aunque cambie el costo de hoy.</p>';
  } else if(st.pop==='calculo') {title='Cómo se calcula';body='<p>'+esc(d.ayuda)+'</p>';
  } else if(st.pop==='lista') {title='Qué muestra esta cuenta';body='<p>'+num(raiz.__d.filas.length)+' productos con los filtros actuales; '+num(d.filas.length)+' en la carta con precio válido, incluidos inactivos y venta interna.</p><p>'+num(d.sin_precio)+' con precio de Salón de S/ 1 o menos quedan fuera. Detalle añade venta neta, unidades, costo al vender y señales; Columnas añade costo, margen y fecha de receta.</p>';
  } else {
    const idx={costo:0,ex:1,sobre:2,datos:3}[st.pop],k=raiz.querySelectorAll('.cc-kpi')[idx];
    if(!k){st.pop=null;pop.hidden=true;return;}
    title=k.querySelector('.cc-kpi-rot').textContent;
    body='<div class="cc-pop-val">'+k.querySelector('.cc-kpi-val').textContent+'</div><p>'+esc(k.querySelector('.cc-kpi-sub').textContent)+'</p><p>'+esc(k.title)+'</p>';
  }
  pop.innerHTML='<div class="cc-pop-head"><strong>'+title+'</strong><button type="button" class="cc-icon" data-acc="cerrar" aria-label="Cerrar">×</button></div>'+body;
  pop.hidden=false;
  const r=raiz.getBoundingClientRect(),a=anchor?.getBoundingClientRect();
  const x=Math.max(12,Math.min((a?a.right-r.left:r.width-24)-pop.offsetWidth,r.width-pop.offsetWidth-12));
  const y=Math.max(12,Math.min(a?a.bottom-r.top+8:80,r.height-pop.offsetHeight-12));
  pop.style.left=x+'px';pop.style.top=y+'px';
}


// Sólo la ficha: un clic adentro, otro elegido o la ficha que llega de Python.
function dibujarFicha(raiz) {
  const s = raiz.__d, fd = fichaCargada(raiz);
  if (fd && (!s.fs || s.fs.cod !== fd.plato.cod)) s.fs = FichaPlato.estadoInicial(fd);
  const z = raiz.querySelector('[data-zona="ficha"]');
  if (!z) return;
  const llave = `${s.st.sel}|${s.st.ftab}`, panel = z.querySelector('.cc-fpanel');
  const scroll = panel && s.llaveFicha === llave ? panel.scrollTop : 0;
  const W = anchoFicha(raiz);
  z.innerHTML = htmlFicha(raiz, W);
  s.anchoF = W;
  s.llaveFicha = llave;
  const nuevo = z.querySelector('.cc-fpanel');
  if (nuevo) nuevo.scrollTop = scroll;
}
function anchoFicha(raiz) {
  const z = raiz.querySelector('[data-zona="ficha"]');
  const w = z ? z.clientWidth - 30 : 420;
  return Math.max(260, Math.floor(w));
}

function marcarFila(raiz, mostrar) {
  const sel = raiz.__d.st.sel;
  raiz.querySelectorAll('tr.cc-f').forEach((tr) => {
    const on = tr.dataset.cod === sel;
    if (tr.classList.contains('sel') !== on) tr.classList.toggle('sel', on);
    if (on && mostrar) tr.scrollIntoView({ block: 'nearest' });
  });
}

// Elegir un producto: la lista y la ficha cambian YA, con lo que la pieza
// tiene; la receta y la evolución las pide a Python. Con el teclado espera a
// que se deje de recorrer, para no pedir una corrida por fila.
function elegir(raiz, cod, espera, mostrar) {
  const s = raiz.__d;
  s.suelto = false;
  s.st.sel = cod;
  s.st.fold = "";
  raiz.classList.remove("cc-sin-ficha");
  s.st.fmenu = false;
  marcarFila(raiz, mostrar);
  dibujarFicha(raiz);
  clearTimeout(s.tElegir);
  s.pedido = cod;
  const mandar = () => s.enviar('elegir', cod);
  if (espera) s.tElegir = setTimeout(mandar, espera); else mandar();
}

function medir(raiz) {
  const arriba=raiz.querySelector('.cc-arriba');
  if(!arriba)return;
  const cab=document.querySelector('.st-key-rec_carta_cab'),slot=raiz.querySelector('.cc-fecha-lugar');
  if(cab && slot && cab.offsetWidth) {
    const ancho=(cab.offsetWidth+8)+'px';
    if(raiz.style.getPropertyValue('--cc-fecha')!==ancho)raiz.style.setProperty('--cc-fecha',ancho);
    const padre=cab.offsetParent;
    if(padre){const a=slot.getBoundingClientRect(),p=padre.getBoundingClientRect();
      const x=Math.round(a.left-p.left)+'px',y=Math.round(a.top-p.top+(a.height-cab.offsetHeight)/2)+'px';
      if(cab.style.left!==x)cab.style.left=x;if(cab.style.top!==y)cab.style.top=y;
      const hidden=raiz.__d.st.expanded?'hidden':'visible';if(cab.style.visibility!==hidden)cab.style.visibility=hidden;
    }
  }
  const alto=Math.ceil(arriba.getBoundingClientRect().height);
  if(raiz.__d.arriba!==alto){raiz.__d.arriba=alto;raiz.style.setProperty('--cc-arriba',alto+'px');}
}


function recordar(st) {
  guardar(CLAVE, { modo: st.modo, canal: st.canal, grupo: st.grupo, tipo: st.tipo, oferta: st.oferta, ver: st.ver,
    inactivos: st.inactivos, vi: st.vi, orden: st.orden, asc: st.asc, ftab: st.ftab, cols: st.cols, detail: st.detail, expanded: st.expanded });
}

function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b && !ev.target.closest('.cc-pop') && raiz.__d.st.pop) {
      raiz.__d.st.pop = null;
      dibujarPop(raiz);
      raiz.querySelector('[data-acc="filtros"]').setAttribute('aria-expanded', 'false');
    }
    if (!b || !raiz.contains(b) || b.tagName === 'SELECT' || b.tagName === 'INPUT') return;
    const s = raiz.__d, { data: d, st } = s;
    const acc = b.dataset.acc, id = b.dataset.id, n = Date.now();
    if(acc==='cerrar'){st.pop=null;dibujarPop(raiz);raiz.querySelector('[data-acc="filtros"]').setAttribute('aria-expanded','false');return;}
    if(acc==='filtros'||acc==='info'||acc==='b-signal'){
      const k=acc==='filtros'?'filtros':acc==='b-signal'?'senal':id;
      st.pop=st.pop===k?null:k;dibujarPop(raiz,b);raiz.querySelector('[data-acc="filtros"]').setAttribute('aria-expanded',String(st.pop==='filtros'));return;
    }
    if(acc==='b-fold'){st.fold=st.fold===id?'':id;dibujarFicha(raiz);return;}
    if(acc==='ampliar'){st.expanded=!st.expanded;st.pop=null;recordar(st);dibujar(raiz,['lista']);return;}
    if(acc==='soltar'){st.sel=null;st.expanded=false;st.pop=null;s.pedido=null;s.suelto=true;recordar(st);dibujar(raiz,['lista']);return;}
    if(st.pop && !b.closest('.cc-pop')){st.pop=null;dibujarPop(raiz);}

    // La ficha.
    if (acc === 'ftab') { st.ftab = id; recordar(st); dibujarFicha(raiz); return; }
    if (acc === 'fmenu') { st.fmenu = !st.fmenu; dibujarFicha(raiz); return; }
    if (acc === 'simular') { s.enviar('simular', { cod: b.dataset.cod, estado: null, n }); return; }
    if (acc === 'nuevo') { st.fmenu = false; s.enviar('nuevo_costeo', { cod: st.sel, n }); return; }
    if (acc === 'cambios') { st.fmenu = false; s.enviar('cambios', { cod: b.dataset.cod, n }); return; }
    const fd = fichaCargada(raiz);
    if (fd && s.fs) {
      const r = FichaPlato.accion(s.fs, fd, acc, id, b);
      if (r && r.enviar) { s.enviar(...r.enviar); return; }
      if (r === 'receta') { st.ftab = 'receta'; recordar(st); dibujarFicha(raiz); return; }
      if (r) { dibujarFicha(raiz); return; }
    }
    // La lista.
    if (acc === 'elegir') { s.suelto=false; elegir(raiz, b.dataset.cod, 0, false); return; }
    if (acc === 'excel') { excel(d, st, s.filas || []); return; }
    if (acc === 'cols') { st.menuCols = !st.menuCols; dibujar(raiz, ['lista']); return; }
    if (acc === 'col') { st.cols = Object.assign({}, st.cols, { [id]: !st.cols[id] }); recordar(st); dibujar(raiz, ['lista']); return; }
    if (acc === 'modo') { st.modo = id; st.tipo = null; st.alerta = null; }
    else if (acc === 'canal') st.canal = +id;
    else if (acc === 'alerta') {
      st.alerta = st.alerta === id ? null : id;
      if (st.alerta === 'ex') { st.orden = 'ex'; st.asc = false; }
    } else if (acc === 'limpiar') {
      Object.assign(st, { canal: 0, grupo: null, tipo: null, oferta: null, ver: '', inactivos: false, vi: false, alerta: null });
    } else if (acc === 'orden') {
      if (st.orden === id) st.asc = !st.asc;
      else { st.orden = id; st.asc = id === 'prod' || id === 'receta'; }
    } else return;
    recordar(st);
    dibujar(raiz, ['filtros', 'arriba']);
  });
  raiz.addEventListener('change', (ev) => {
    if(ev.target.dataset.acc==='detalle'){raiz.__d.st.detail=ev.target.checked;recordar(raiz.__d.st);dibujar(raiz,['lista']);return;}
    const el = ev.target.closest('select[data-acc]');
    if (!el || !raiz.contains(el)) return;
    const st = raiz.__d.st, v = el.value;
    const acc = el.dataset.acc;
    if (acc === 'canal') st.canal = +v;
    else if (acc === 'grupo') st.grupo = v || null;
    else if (acc === 'tipo') st.tipo = v || null;
    else if (acc === 'oferta') st.oferta = v === '' ? null : +v;
    else if (acc === 'ver') st.ver = v;
    else if (acc === 'incluir') { st.inactivos = v.includes('i'); st.vi = v.includes('v'); }
    else return;
    st.pop=null;
    recordar(st);
    dibujar(raiz, ['filtros', 'arriba']);
  });
  // Buscar redibuja la lista: el campo no pierde el foco.
  raiz.addEventListener('input', (ev) => {
    if (ev.target.dataset.acc !== 'buscar') return;
    raiz.__d.st.q = ev.target.value;
    dibujar(raiz, ['arriba']);
  });
  // ↑ ↓ recorren la lista; la ficha cambia en el momento.
  raiz.addEventListener('keydown', (ev) => {
    if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
    if (!ev.target.closest || !ev.target.closest('.cc-tabla')) return;
    const filas = (raiz.__d.filas || []).slice(0, MAX_FILAS);
    if (!filas.length) return;
    ev.preventDefault();
    const i = filas.findIndex((f) => f[F.cod] === raiz.__d.st.sel);
    const j = Math.max(0, Math.min(filas.length - 1, i + (ev.key === 'ArrowDown' ? 1 : -1)));
    if (j !== i) elegir(raiz, filas[j][F.cod], ESPERA_TECLADO, true);
  });
  raiz.addEventListener('keydown',(ev)=>{if(ev.key==='Escape'){raiz.__d.st.pop=null;dibujarPop(raiz);}});
  const resize=()=>medir(raiz);window.addEventListener('resize',resize);raiz.__d.resize=resize;
  // Un ancho nuevo redibuja los SVG de la ficha al ancho real.
  if (typeof ResizeObserver !== 'undefined') {
    let pendiente = false;
    const observer = new ResizeObserver(() => {
      if (pendiente) return;
      pendiente = true;
      requestAnimationFrame(() => {
        pendiente = false;
        if (raiz.__d && raiz.__d.data && raiz.__d.anchoF !== anchoFicha(raiz)) dibujarFicha(raiz);
      });
    });observer.observe(raiz);raiz.__d.observer=observer;
  }
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  if (!data || !data.filas) return;
  let raiz = parentElement.querySelector('.cc');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'cc';
    parentElement.appendChild(raiz);
    const g = leer(CLAVE, {});
    raiz.__d = { st: Object.assign({ modo: 'carta', canal: 0, grupo: null, tipo: null, oferta: null, inactivos: false,
      vi: false, ver: '', orden: 'ex', asc: false, alerta: null, q: '', sel: null, ftab: 'resumen',
      cols: { costo: false, margen: false, receta: false }, menuCols: false, fmenu: false, detail: false, expanded: false, fold: '', pop: null }, g) };
    const st = raiz.__d.st;
    if (!(st.canal >= 0 && st.canal < data.canales.length)) st.canal = 0;
    if (!PESTANAS.some(([k]) => k === st.ftab)) st.ftab = 'resumen';
    st.cols = Object.assign({ costo: false, margen: false, receta: false }, st.cols || {});
    enlazar(raiz);
  }
  const s = raiz.__d;
  s.observer?.observe(raiz);
  if(s.resize)window.addEventListener('resize',s.resize);
  s.enviar = setTriggerValue;
  // La misma carta (otra corrida del fragment, la que trae la ficha): no se
  // rehace la lista, que conserva su scroll, su orden y lo escrito en buscar.
  const firma = [data.rango, data.filas.length, data.sin_precio, data.canales.map((c) => c[1]).join(',')].join('|');
  const misma = s.firma === firma && raiz.querySelector('.cc-arriba');
  s.firma = firma;
  s.data = data;
  // El elegido de Python manda, salvo que la pieza haya pedido otro y la
  // corrida que llega sea la de un pedido anterior.
  if (s.pedido && s.pedido !== data.sel) { /* sigue el que se pidió */ } else {
    s.pedido = null;
    if (data.sel && !s.suelto) s.st.sel = data.sel;
  }
  if (misma) { marcarFila(raiz, false); dibujarFicha(raiz); medir(raiz); } else dibujar(raiz);
  return () => {clearTimeout(s.tElegir);s.observer?.disconnect();window.removeEventListener('resize',s.resize);};
}
