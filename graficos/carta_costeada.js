// Recetas › «Costo de Carta» (regla #696).
//
// La monta graficos/carta_costeada.py con st.components.v2 (sin iframe,
// estilos en un shadow root); `_xlsx.js` va antepuesto (libro, bajar,
// archivo). Es la forma del boceto aprobado
// (https://claude.ai/artifact/SHeSJotXSbn5n5UCZBRdnz): indicadores que
// filtran, grupos con su % de costo, la lista y la ficha del elegido con
// sus CINCO CANALES. Todo lo que se elige acá —canal, filtros, orden,
// buscar, el Excel— lo resuelve el navegador. A Python vuelven sólo dos
// cosas: `elegir` (el producto: dibuja abajo su receta y su evolución) y
// `simular` (abre la modal del simulador). Y `cambios` ({cod, n}): «Ver
// cambios» lleva a «Cambios en recetas» filtrada en el producto (#707).
//
// Python manda en `data`: `filas` (ver carta_costeada.armar_pieza),
// `canales` ([nombre, unidades vendidas en el rango]), `divisor` (precio →
// neto), `rango`, `sel`, `sin_precio`, `umbrales` ([30, 35]), `grupo_vi` y
// `ayuda`.

const F = { cod: 0, grupo: 1, sub: 2, prod: 3, tipo: 4, activo: 5, oferta: 6, desc: 7, receta: 8, ultima: 9,
  precios: 10, costos: 11, vend: 12, vneto: 13, vcosto: 14, sinc: 15, combo: 16, otros: 17 };
const CLAVE = 'cc_est';
const MAX_FILAS = 800;
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const TIPOS = ['Receta', 'Directo', 'Combo', 'Sin enlace', 'No aplica'];
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
    pct: precio && costo > 0 ? costo / neto * 100 : null,
    margen: precio && costo > 0 ? neto - costo : null,
    u: v.u, vneto: v.neto, vcosto: v.costo,
    pctV: v.neto > 0.5 && v.costo > 0 ? v.costo / v.neto * 100 : null,
  };
}
function nivel(d, p) {
  if (p == null) return 'nulo';
  return p > d.umbrales[1] ? 'rojo' : p > d.umbrales[0] ? 'ambar' : '';
}
const haceSeis = (() => { const h = new Date(); h.setMonth(h.getMonth() - 6); return h.toISOString().slice(0, 10); })();

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
    if (st.alerta && !x.seVende) return false;
    if (st.alerta === 'sobre' && !(x.pct > d.umbrales[1])) return false;
    if (st.alerta === 'sincosto' && !(x.sinCosto || f[F.sinc] > 0)) return false;
    if (st.alerta === 'novend' && x.u > 0) return false;
    if (st.alerta === 'vieja' && !(f[F.tipo] === 'Receta' && f[F.receta] && f[F.receta] < haceSeis)) return false;
    return true;
  });
}
const ORDEN = {
  pct: (d, f, c) => enCanal(d, f, c).pct ?? -1, costo: (d, f, c) => f[F.costos][c],
  margen: (d, f, c) => enCanal(d, f, c).margen ?? -1e9, vend: (d, f, c) => enCanal(d, f, c).u,
  vneto: (d, f, c) => enCanal(d, f, c).vneto, receta: (d, f) => f[F.receta] || '0',
  prod: (d, f) => sinTilde(f[F.prod]),
};
function ordenar(d, st, filas) {
  const k = ORDEN[st.orden] || ORDEN.vneto, dir = st.asc ? 1 : -1;
  return filas.map((f) => [k(d, f, st.canal), f]).sort((a, b) => (a[0] < b[0] ? -dir : a[0] > b[0] ? dir : 0)).map((x) => x[1]);
}

// ── Indicadores ──────────────────────────────────────────────────────────
function htmlKpis(d, st, filas) {
  const c = st.canal;
  let costoU = 0, netoU = 0, vc = 0, vn = 0, sobre = 0, entre = 0, sinC = 0, sinCN = 0, novend = 0, vieja = 0, conPrecio = 0;
  filas.forEach((f) => {
    const x = enCanal(d, f, c);
    if (!x.seVende) return;
    conPrecio++;
    if (!x.sinCosto && x.u > 0) { costoU += x.costo * x.u; netoU += x.vneto; }
    vc += x.vcosto; vn += x.vneto;
    if (x.pct > d.umbrales[1]) sobre++;
    else if (x.pct > d.umbrales[0]) entre++;
    if (x.sinCosto) sinC++;
    sinCN += f[F.sinc];
    if (!x.u) novend++;
    if (f[F.tipo] === 'Receta' && f[F.receta] && f[F.receta] < haceSeis) vieja++;
  });
  const hoy = netoU ? costoU / netoU * 100 : null, vend = vn > 0.5 ? vc / vn * 100 : null;
  const kpi = (id, rot, val, sub, cls) => `<button type="button" class="cc-kpi${st.alerta === id && id ? ' on' : ''}" data-acc="alerta" data-id="${id}" ${id ? '' : 'disabled'}>
      <span class="cc-kpi-rot">${rot}</span><span class="cc-kpi-lin"><span class="cc-kpi-val ${cls || ''}">${val}</span><span class="cc-kpi-sub">${sub}</span></span></button>`;
  return [
    kpi('', '% costo · ponderado por lo vendido', pct(hoy), vend != null ? `se vendió al ${pct(vend)}` : 'sin ventas en el rango', nivel(d, hoy)),
    kpi('sobre', `Sobre ${d.umbrales[1]} %`, String(sobre), `${entre} más entre ${d.umbrales[0]} y ${d.umbrales[1]} %`, sobre ? 'rojo' : ''),
    kpi('sincosto', 'Sin costo en el POS', String(sinC), sinCN > 0 ? `${dinero(sinCN, 0)} vendidos a costo 0` : 'nada vendido a costo 0', sinC ? 'ambar' : ''),
    kpi('novend', 'No se vendieron en el rango', String(novend), `de ${conPrecio} con precio en el canal`),
    kpi('vieja', 'Receta sin tocar hace 6 meses', String(vieja), 'guardada antes del ' + fecha(haceSeis)),
  ].join('');
}

// ── Canal, grupos, tipos ─────────────────────────────────────────────────
function htmlFiltros(d, st, filas) {
  const canales = d.canales.map(([n, u], i) => `<button type="button" class="cc-canal${st.canal === i ? ' on' : ''}${u ? '' : ' apagado'}" data-acc="canal" data-id="${i}" title="${u ? `${num(u)} unidades vendidas en el rango` : 'Sin ventas en el rango'}">${esc(n)}${u ? '' : ' <small>sin ventas</small>'}</button>`).join('');
  // El % de cada grupo: costo de hoy × lo vendido ÷ lo vendido, en el canal.
  const g = new Map();
  filas.forEach((f) => {
    const x = enCanal(d, f, st.canal);
    const a = g.get(f[F.grupo]) || { n: 0, c: 0, v: 0 };
    a.n++;
    if (!x.sinCosto && x.u > 0) { a.c += x.costo * x.u; a.v += x.vneto; }
    g.set(f[F.grupo], a);
  });
  const grupos = [...g].sort((a, b) => b[1].n - a[1].n).map(([nombre, a]) => {
    const p = a.v ? a.c / a.v * 100 : null;
    return `<button type="button" class="cc-chip${st.grupo === nombre ? ' on' : ''}" data-acc="grupo" data-id="${esc(nombre)}">${esc(nombre)} · ${a.n}${p != null ? ` <b class="${nivel(d, p)}">${pct(p)}</b>` : ''}</button>`;
  }).join('');
  const tipos = st.modo === 'combos' ? '' : TIPOS.map((t) => {
    const n = filas.filter((f) => f[F.tipo] === t).length;
    return n ? `<button type="button" class="cc-chip${st.tipo === t ? ' on' : ''}" data-acc="tipo" data-id="${t}">${t} · ${n}</button>` : '';
  }).join('');
  const hayOferta = d.filas.some((f) => f[F.oferta] >= 0);
  const oferta = hayOferta && st.modo !== 'combos' ? [[1, 'Carta impresa'], [0, 'No impresa']].map(([v, r]) =>
    `<button type="button" class="cc-chip${st.oferta === v ? ' on' : ''}" data-acc="oferta" data-id="${v}">${r}</button>`).join('') : '';
  return `<div class="cc-fila"><span class="cc-rot">Canal</span><div class="cc-canales" role="group" aria-label="Canal">${canales}</div>
      ${tipos ? `<span class="cc-rot">Tipo</span>${tipos}` : ''}${oferta ? `<span class="cc-rot">Carta</span>${oferta}` : ''}</div>
    <div class="cc-fila"><span class="cc-rot">Grupo</span>${grupos}
      <span class="cc-mas">Mostrar también:
        <button type="button" class="cc-link${st.inactivos ? ' on' : ''}" data-acc="inactivos" aria-pressed="${st.inactivos}">inactivos</button> ·
        <button type="button" class="cc-link${st.vi ? ' on' : ''}" data-acc="vi" aria-pressed="${st.vi}">venta interna</button></span></div>`;
}

// ── La lista ─────────────────────────────────────────────────────────────
function cabeza(st, cols) {
  return cols.map(([id, r, cls, ayuda]) => `<th class="${cls || ''}">${id ? `<button type="button" data-acc="orden" data-id="${id}" class="${st.orden === id ? 'on' : ''}" title="${esc(ayuda || '')}">${r}${st.orden === id ? (st.asc ? ' ↑' : ' ↓') : ''}</button>` : r}</th>`).join('');
}
function chipFila(d, f, x) {
  if (x.pct > 60) return '<span class="cc-tag rojo" title="El costo de hoy pasa el 60 % del neto: casi seguro un error de receta o de factor.">revisar costo</span>';
  if (x.sinCosto) return '<span class="cc-tag ambar" title="El POS no le tiene costo: lo vendido entra al FoodCost a costo 0.">sin costo</span>';
  if (!f[F.activo]) return '<span class="cc-tag">inactivo</span>';
  if (f[F.tipo] !== 'Receta') return `<span class="cc-tag" title="${esc(f[F.desc] || '')}">${esc(f[F.tipo].toLowerCase())}</span>`;
  return '';
}
function htmlLista(d, st, filas) {
  const c = st.canal;
  const total = filas.length, vista = filas.slice(0, MAX_FILAS);
  const pie = `<div class="cc-lpie"><span>${num(total)} productos${total > MAX_FILAS ? ` · se muestran ${MAX_FILAS}: buscá o filtrá para ver el resto` : ''}${d.sin_precio ? ` · ${d.sin_precio} sin precio de Salón (S/ 1 o menos) no se muestran` : ''}</span>
    <span>% de costo: <b class="ambar">ámbar &gt; ${d.umbrales[0]} %</b>, <b class="rojo">rojo &gt; ${d.umbrales[1]} %</b></span></div>`;
  if (!total) return `<div class="cc-vacio">Ningún producto con estos filtros.</div>${pie}`;
  if (st.modo === 'combos') {
    const cols = [['prod', 'Combo'], ['', 'Cómo se costeó'], ['costo', 'Costo usado', 'num'], ['pct', '% costo', 'num'],
      ['', 'Mínimo', 'num'], ['', 'Promedio', 'num'], ['', 'Esperado', 'num'], ['', 'Máximo', 'num'],
      ['', 'Real 90 días', 'num'], ['vend', 'Vend.', 'num']];
    const filasH = vista.map((f) => {
      const x = enCanal(d, f, c), b = f[F.combo] || ['', '', 0, 0, 0, 0, 0, 0];
      return `<tr class="cc-f${f[F.cod] === st.sel ? ' sel' : ''}" data-acc="elegir" data-cod="${esc(f[F.cod])}">
        <td class="cc-prod"><b>${esc(f[F.prod])}</b><span>${esc(b[0] || 'Combo')}</span></td><td class="cc-sub">${esc(b[1] || '—')}</td>
        <td class="num">${dinero(x.costo)}</td><td class="num"><span class="pill ${nivel(d, x.pct)}">${pct(x.pct)}</span></td>
        ${b.slice(2, 7).map((v) => `<td class="num">${v ? dinero(v) : '—'}</td>`).join('')}<td class="num">${num(x.u)}</td></tr>`;
    }).join('');
    return `<div class="cc-tabla"><table><thead><tr>${cabeza(st, cols)}</tr></thead><tbody>${filasH}</tbody></table></div>${pie}`;
  }
  const maxV = Math.max(1, ...vista.map((f) => enCanal(d, f, c).vneto));
  const cols = [['prod', 'Producto', '', 'Ordenar por nombre'], ['pct', '% costo', 'num', 'Costo de hoy ÷ neto del canal. Debajo, al que se VENDIÓ en el rango'],
    ['costo', 'Costo', 'num', 'Costo de hoy y precio del canal'], ['margen', 'Margen', 'num', 'Lo que deja cada unidad hoy: neto − costo'],
    ['vend', 'Vend.', 'num', 'Unidades vendidas en el rango, en este canal'],
    ['vneto', 'Venta neta', '', 'Lo vendido en el rango en este canal, sin IGV. En ámbar, lo que entró al FoodCost a costo 0'],
    ['receta', 'Receta', 'num', 'Última vez que se guardó la receta en el POS']];
  const filasH = vista.map((f) => {
    const x = enCanal(d, f, c);
    const difV = x.pctV != null && x.pct != null && Math.abs(x.pctV - x.pct) >= 5;
    return `<tr class="cc-f${f[F.cod] === st.sel ? ' sel' : ''}${x.seVende ? '' : ' apagada'}" data-acc="elegir" data-cod="${esc(f[F.cod])}">
      <td class="cc-prod"><div><b title="${esc(f[F.prod])}">${esc(f[F.prod])}</b>${chipFila(d, f, x)}</div>
        <span>${esc(f[F.grupo])} › ${esc(f[F.sub])}${f[F.oferta] === 1 ? ' · carta impresa' : ''}</span></td>
      <td class="num">${x.seVende ? `<span class="pill ${nivel(d, x.pct)}">${pct(x.pct)}</span>` : '<span class="cc-sub">no se vende</span>'}
        <span class="cc-v${difV ? ' ambar' : ''}">${x.u ? `vendido ${pct(x.pctV)}` : 'sin ventas'}</span></td>
      <td class="num">${x.sinCosto ? '—' : dinero(x.costo)}<span class="cc-v">de ${x.precio ? dinero(x.precio, x.precio % 1 ? 2 : 0) : '—'}</span></td>
      <td class="num${x.margen != null && x.margen < 10 ? ' rojo' : ''}">${x.margen == null ? '—' : dinero(x.margen)}</td>
      <td class="num">${x.u ? num(x.u) : '—'}</td>
      <td><div class="cc-bar"><i style="width:${Math.max(2, x.vneto / maxV * 48)}px"></i><span class="num">${x.vneto ? dinero(x.vneto, 0) : '—'}</span></div>
        ${f[F.sinc] > 0 ? `<span class="cc-v ambar">${dinero(f[F.sinc], 0)} a costo 0</span>` : ''}</td>
      <td class="num cc-sub">${f[F.tipo] === 'Receta' ? fecha(f[F.receta]) : '—'}</td></tr>`;
  }).join('');
  return `<div class="cc-tabla"><table><thead><tr>${cabeza(st, cols)}</tr></thead><tbody>${filasH}</tbody></table></div>${pie}`;
}

// ── La ficha del elegido ─────────────────────────────────────────────────
function htmlFicha(d, st, f) {
  if (!f) return '<div class="cc-vacio">Elegí un producto de la lista.</div>';
  const c = st.canal, x = enCanal(d, f, c);
  const sim = `<div class="cc-facc"><button type="button" class="cc-btn" data-acc="cambios" data-cod="${esc(f[F.cod])}" title="Lo que cambió en su precio, su receta y las recetas base que lleva">Ver cambios</button>${f[F.tipo] === 'Receta' ? `<button type="button" class="cc-btn prim" data-acc="simular" data-cod="${esc(f[F.cod])}">Simular</button>` : ''}</div>`;
  const cifra = (r, v, cls = '') => `<div><span>${r}</span><b class="num ${cls}">${v}</b></div>`;
  let aviso;
  if (!x.seVende) aviso = ['', `No tiene precio en «${esc(d.canales[c][0])}»: no se vende por ese canal.`];
  else if (x.sinCosto) aviso = ['ambar', `El POS no le tiene costo: ${dinero(f[F.sinc], 0)} de lo vendido en el rango entraron al FoodCost a costo 0, y así quedan guardados.`];
  else if (x.pct > 60) aviso = ['rojo', `Hoy cuesta el ${pct(x.pct)} del neto${x.pctV != null ? ` y se vendió al ${pct(x.pctV)}` : ''}: deja ${dinero(x.margen)} por unidad. Revisar la receta o el factor de su insumo principal antes de tocar el precio.`];
  else if (x.pctV != null && Math.abs(x.pctV - x.pct) >= 3) aviso = ['', `Hoy cuesta el ${pct(x.pct)} y en el rango se vendió al ${pct(x.pctV)}: ${x.pctV > x.pct ? 'en algún momento el costo guardado fue más alto que el de hoy — la evolución, abajo, dice cuándo.' : 'la receta de hoy es más cara que la que se vendió.'}`];
  else if (x.pctV != null) aviso = ['', `Hoy cuesta el ${pct(x.pct)} y se vendió al ${pct(x.pctV)}: el costo del POS y el de la receta van parejos.`];
  else aviso = ['', `Hoy cuesta el ${pct(x.pct)}. No se vendió en el rango por este canal.`];
  const canales = d.canales.map(([n], i) => {
    const y = enCanal(d, f, i);
    return `<tr class="${i === c ? 'on' : ''}" data-acc="canal" data-id="${i}"><td>${esc(n)}</td>
      <td class="num">${y.precio ? dinero(y.precio, y.precio % 1 ? 2 : 0) : '—'}</td>
      <td class="num">${y.seVende ? `<span class="pill ${nivel(d, y.pct)}">${pct(y.pct)}</span>` : '—'}</td>
      <td class="num">${y.margen == null ? '—' : dinero(y.margen)}</td>
      <td class="num">${y.u ? num(y.u) : '—'}</td><td class="num">${pct(y.pctV)}</td></tr>`;
  }).join('');
  const difCosto = new Set(f[F.costos].filter((v) => v > 0).map((v) => v.toFixed(2))).size > 1;
  const precioPara = (obj) => Math.ceil(x.costo / (obj / 100) * d.divisor);
  const precios = x.seVende && !x.sinCosto ? d.umbrales.map((u, i) => {
    const p = precioPara(u), dif = p - x.precio;
    return `<div class="cc-opc${i === 0 ? ' prop' : ''}"><b>Para quedar en ${u} %</b><b class="num">${dinero(p, 0)}</b>
      <span>precio de carta, redondeado</span><span class="num">${dif === 0 ? 'sin cambio' : `${dif > 0 ? '+' : '−'}${dinero(Math.abs(dif), 0)}`}</span></div>`;
  }).join('') + `<div class="cc-opc"><b>Como está</b><b class="num">${dinero(x.precio, x.precio % 1 ? 2 : 0)}</b><span>deja ${dinero(x.margen)} por unidad</span><span class="num">${x.u ? `${dinero(x.margen * x.u, 0)} en el rango` : ''}</span></div>` : '';
  const combo = f[F.combo] ? `<div class="cc-fbloque"><div class="cc-frot">Combo ${esc((f[F.combo][0] || '').toLowerCase())} · ${esc(f[F.combo][1] || 'sin método')}</div>
      <table class="cc-mini"><tbody>${[['Mínimo', 2], ['Promedio', 3], ['Esperado', 4], ['Máximo', 5], ['Real 90 días', 6]].map(([r, k]) => `<tr><td>${r}</td><td class="num">${f[F.combo][k] ? dinero(f[F.combo][k]) : '—'}</td></tr>`).join('')}</tbody></table>
      <div class="cc-fpie">El POS no costea los combos: la banda la calcula la consulta del Sheet (regla #548).</div></div>` : '';
  return `<div class="cc-fcab"><div><span>${esc(f[F.grupo])} › ${esc(f[F.sub])} · ${esc(f[F.tipo])}${f[F.desc] && f[F.tipo] !== 'Receta' ? ` · ${esc(f[F.desc])}` : ''}</span><h3>${esc(f[F.prod])}</h3></div>${sim}</div>
    ${x.seVende && !x.sinCosto ? `<div class="cc-barra"><i class="${nivel(d, x.pct) || 'ok'}" style="width:${Math.min(100, x.pct)}%"></i><i class="margen" style="width:${Math.max(0, 100 - x.pct)}%"></i></div>` : ''}
    <div class="cc-cifras">${cifra('Precio', x.precio ? dinero(x.precio) : '—')}${cifra(`Neto (÷ ${d.divisor.toFixed(3)})`, x.precio ? dinero(x.neto) : '—')}
      ${cifra('Costo de hoy', x.sinCosto ? '—' : `${dinero(x.costo)} · ${pct(x.pct)}`, nivel(d, x.pct))}${cifra('Margen', x.margen == null ? '—' : dinero(x.margen))}</div>
    <div class="cc-aviso ${aviso[0]}">${aviso[1]}</div>
    <div class="cc-fbloque"><div class="cc-frot"><span title="${difCosto ? 'El costo cambia según el canal' : 'El costo es el mismo en los cinco canales: cambia el precio'}">Por canal${difCosto ? '' : ' · mismo costo'}</span><span>vendido en el rango</span></div>
      <table class="cc-mini cc-canal-t"><thead><tr><th>Canal</th><th class="num">Precio</th><th class="num">% costo</th><th class="num">Margen</th><th class="num">Vend.</th><th class="num">% vend.</th></tr></thead><tbody>${canales}</tbody></table></div>
    ${precios ? `<div class="cc-fbloque"><div class="cc-frot">Qué hacer con el precio en «${esc(d.canales[c][0])}»</div>${precios}</div>` : ''}
    ${combo}
    <div class="cc-fpie">La receta y la evolución del costo, debajo de la lista.</div>`;
}

// ── El Excel: la lista que se ve, con los cinco canales ──────────────────
function excel(d, st, filas) {
  const cab = ['Código', 'Grupo', 'Subgrupo', 'Producto', 'Tipo', 'Activo', 'Carta', 'Descarga'];
  d.canales.forEach(([n]) => cab.push(`Precio ${n}`, `Neto ${n}`, `Costo ${n}`, `% costo ${n}`, `Margen ${n}`, `Vendidos ${n}`, `Venta neta ${n}`));
  cab.push('Vendidos (total)', 'Venta neta (total)', '% vendido (total)', 'Vendido sin costo', 'Receta guardada', 'Última venta');
  const filasX = filas.map((f) => {
    const r = [f[F.cod], f[F.grupo], f[F.sub], f[F.prod], f[F.tipo], f[F.activo] ? 'Sí' : 'No',
      f[F.oferta] === 1 ? 'Impresa' : f[F.oferta] === 0 ? 'No impresa' : '', f[F.desc]];
    d.canales.forEach((_, i) => {
      const x = enCanal(d, f, i);
      r.push(x.precio || null, x.precio ? x.neto : null, x.sinCosto ? null : x.costo, x.pct, x.margen, x.u || null, x.vneto || null);
    });
    r.push(f[F.vend] || null, f[F.vneto] || null, f[F.vneto] > 0.5 && f[F.vcosto] > 0 ? f[F.vcosto] / f[F.vneto] * 100 : null,
      f[F.sinc] || null, f[F.receta], f[F.ultima]);
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
    raiz.innerHTML = `<div class="cc-arriba">
        <div class="cc-cab"><div class="cc-izq">
            <div class="cc-tabs" role="tablist" aria-label="Ver" data-zona="modo"></div>
            <span class="cc-ayuda" data-zona="ayuda">?</span></div>
          <div class="cc-der"><label class="cc-buscar"><input type="search" data-acc="buscar" placeholder="Buscar producto" aria-label="Buscar producto"></label>
            <button type="button" class="cc-btn" data-acc="excel">Excel</button></div></div>
        <div class="cc-kpis" data-zona="kpis"></div>
        <div class="cc-filtros" data-zona="filtros"></div></div>
      <div class="cc-cuerpo"><div class="cc-lista" data-zona="lista"></div><div class="cc-ficha" data-zona="ficha"></div></div>`;
  }
  const z = (n) => raiz.querySelector(`[data-zona="${n}"]`);
  z('ayuda').title = d.ayuda + (d.rango ? ` Lo vendido: ${d.rango}.` : '');
  z('modo').innerHTML = [['carta', 'Carta'], ['combos', 'Combos']].map(([id, r]) =>
    `<button type="button" role="tab" aria-selected="${st.modo === id}" class="${st.modo === id ? 'on' : ''}" data-acc="modo" data-id="${id}">${r}</button>`).join('');
  const b = base(d, st);
  const filas = ordenar(d, st, filtrar(d, st, b));
  raiz.__d.filas = filas;
  const todas = !zonas;
  z('kpis').innerHTML = htmlKpis(d, st, filtrar(d, Object.assign({}, st, { alerta: null }), b));
  if (todas || zonas.includes('filtros')) z('filtros').innerHTML = htmlFiltros(d, st, b);
  const lista = z('lista'), scroll = lista.querySelector('.cc-tabla')?.scrollTop || 0;
  lista.innerHTML = htmlLista(d, st, filas);
  const t = lista.querySelector('.cc-tabla');
  if (t && zonas && !zonas.includes('arriba')) t.scrollTop = scroll;
  const f = d.filas.find((x) => x[F.cod] === st.sel);
  z('ficha').innerHTML = htmlFicha(d, st, f);
  medir(raiz);
}

function medir(raiz) {
  const arriba = raiz.querySelector('.cc-arriba');
  if (!arriba) return;
  const alto = Math.ceil(arriba.getBoundingClientRect().height);
  if (raiz.__d.arriba !== alto) {
    raiz.__d.arriba = alto;
    raiz.style.setProperty('--cc-arriba', `${alto}px`);
  }
}

function recordar(st) {
  guardar(CLAVE, { modo: st.modo, canal: st.canal, grupo: st.grupo, tipo: st.tipo, oferta: st.oferta,
    inactivos: st.inactivos, vi: st.vi, orden: st.orden, asc: st.asc });
}

function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b)) return;
    const { data: d, st } = raiz.__d;
    const acc = b.dataset.acc, id = b.dataset.id;
    if (acc === 'elegir') {
      st.sel = b.dataset.cod;
      dibujar(raiz, ['lista']);
      raiz.__d.enviar('elegir', st.sel);
      return;
    }
    if (acc === 'simular') { raiz.__d.enviar('simular', b.dataset.cod); return; }
    if (acc === 'cambios') { raiz.__d.enviar('cambios', { cod: b.dataset.cod, n: Date.now() }); return; }
    if (acc === 'excel') { excel(d, st, raiz.__d.filas || []); return; }
    if (acc === 'modo') { st.modo = id; st.tipo = null; st.alerta = null; }
    else if (acc === 'canal') st.canal = +id;
    else if (acc === 'alerta') st.alerta = st.alerta === id ? null : id;
    else if (acc === 'grupo') st.grupo = st.grupo === id ? null : id;
    else if (acc === 'tipo') st.tipo = st.tipo === id ? null : id;
    else if (acc === 'oferta') st.oferta = st.oferta === +id ? null : +id;
    else if (acc === 'inactivos') st.inactivos = !st.inactivos;
    else if (acc === 'vi') st.vi = !st.vi;
    else if (acc === 'orden') {
      if (st.orden === id) st.asc = !st.asc;
      else { st.orden = id; st.asc = id === 'prod' || id === 'receta'; }
    } else return;
    recordar(st);
    dibujar(raiz, ['filtros', 'arriba']);
  });
  // Buscar redibuja la lista: el campo no pierde el foco.
  raiz.addEventListener('input', (ev) => {
    if (ev.target.dataset.acc !== 'buscar') return;
    raiz.__d.st.q = ev.target.value;
    dibujar(raiz, ['arriba']);
  });
  window.addEventListener('resize', () => medir(raiz));
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
      vi: false, orden: 'vneto', asc: false, alerta: null, q: '', sel: null }, g) };
    if (!(raiz.__d.st.canal >= 0 && raiz.__d.st.canal < data.canales.length)) raiz.__d.st.canal = 0;
    enlazar(raiz);
  }
  raiz.__d.enviar = setTriggerValue;
  raiz.__d.data = data;
  // El elegido de Python manda sólo si la pieza no eligió otro (la ficha de
  // abajo es la de `data.sel`).
  if (!raiz.__d.st.sel || raiz.__d.st.sel !== data.sel) raiz.__d.st.sel = data.sel;
  dibujar(raiz);
}
