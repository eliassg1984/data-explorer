// Recetas › «Recetas vs porcionado» (regla #703).
//
// La monta graficos/recetas_revisar.py::render_revisar_recetas con
// st.components.v2 (sin iframe, estilos en un shadow root). Es la forma del
// boceto aprobado (https://claude.ai/artifact/RLrWanQHM37CAcJBnysFxz): el
// título con 30 | 90 días, los indicadores que filtran, la lista agrupada
// por el insumo del que sale cada corte y la ficha del elegido. La cuenta
// es `revisar()` de Python, para las dos ventanas: acá no se reclasifica
// nada. Vuelve a Python sólo `carta`: el salto a un plato en Costo de Carta.
//
// LA CUENTA DEL STOCK de la ficha: stock al empezar (kardex) + porcionado +
// comprado − lo que piden las ventas = lo que debería quedar, contra el
// stock al terminar. «Kardex en negativo» es un corte que terminó debajo
// de cero: el POS descargó lo que no había.
//
// Python manda en `data`: `ventanas` ([{dias, rot, ini, fin, filas}], una
// fila por corte con cod, grupo_cod, grupo, corte, unid, que, clase, porc,
// ped, valor, ultimo, salio, platos, porcs, comprado, semP, semD, stIni,
// stFin), `sems` (los lunes de las semanas) y `codigos` ({plato en
// minúsculas: código de Costo de Carta}).

const CLAVE = 'rec_rev_est';
const COLOR = { sin: 'var(--warning)', falta: 'var(--danger)', viejo: 'var(--text-muted)', salida: 'var(--accent)' };
const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const CORTA = { KILOS: 'kg', LITROS: 'L', UND: 'und', UNIDAD: 'und', PORCION: 'porc' };

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento */ } }
const sinTilde = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const un = (x) => CORTA[String(x).toUpperCase()] || String(x).toLowerCase();
function cant(q, u) {
  if (q == null) return '—';
  const a = Math.abs(q), d = a >= 100 || Math.abs(q - Math.round(q)) < 1e-9 ? 0 : (a >= 10 ? 1 : 2);
  return `${q < -1e-9 ? '−' : ''}${a.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })} ${un(u)}`;
}
const soles = (v) => `S/ ${Math.round(v).toLocaleString('en-US')}`;
function fecha(s, anio) {
  if (!s) return '—';
  const [y, m, d] = s.split('-').map(Number);
  return `${d} ${MES[m - 1]}${anio && y !== anio ? ` ${y}` : ''}`;
}
// «(P) Lomo trozos saltado 170gr (produccion)» → «Lomo trozos saltado 170gr»: en la lista, lo que distingue.
const corto = (s) => String(s).replace(/^\(P\)\s*/, '').replace(/\s*\((produccion|parrilla)\)\s*$/i, '');
const negativo = (f) => f.stFin != null && f.stFin < -0.005;

function ventana(raiz) {
  const { data: d, st } = raiz.__d;
  return d.ventanas.find((v) => v.dias === st.dias) || d.ventanas[0];
}
function pasa(st, f) {
  if (st.filtro === 'neg' && !negativo(f)) return false;
  if (st.filtro && st.filtro !== 'neg' && f.clase !== st.filtro) return false;
  if (st.q) {
    const q = sinTilde(st.q);
    if (!sinTilde(f.corte).includes(q) && !sinTilde(f.grupo).includes(q) && !f.platos.some((p) => sinTilde(p[0]).includes(q))) return false;
  }
  return true;
}

// ── Las partes ───────────────────────────────────────────────────────────
function htmlCab(raiz) {
  const { data: d } = raiz.__d, v = ventana(raiz), anio = Number(v.fin.slice(0, 4));
  return `<span class="rr-tit">Recetas vs porcionado</span>
    <div class="seg" role="group">${d.ventanas.map((w) => `<button type="button" data-acc="dias" data-id="${w.dias}" class="${w.dias === v.dias ? 'on' : ''}">${esc(w.rot)}</button>`).join('')}</div>
    <span class="rr-per">Del ${fecha(v.ini, anio)} al ${fecha(v.fin)} ${anio} · hasta el último pedido con venta</span>`;
}
function htmlKpis(raiz) {
  const { st } = raiz.__d, t = ventana(raiz).filas;
  const de = (k) => t.filter((f) => f.clase === k);
  const sum = (x) => x.reduce((a, f) => a + f.valor, 0);
  const k = (id, rot, color, v, s, tip) => `<button type="button" class="kpi${st.filtro === id ? ' on' : ''}" data-acc="filtro" data-id="${id}" title="${esc(tip)}"><span class="r"><i style="background:${color}"></i>${esc(rot)}</span><span class="v">${v}</span><span class="s">${esc(s)}</span></button>`;
  const falta = de('falta'), sin = de('sin');
  return [
    k('falta', 'Piden más de lo porcionado', COLOR.falta, falta.length, `faltaron ${soles(sum(falta))}`, 'Las recetas de lo vendido piden más del doble de lo que se porcionó y se compró. «Faltaron»: lo que faltó porcionar, al precio promedio de hoy'),
    k('sin', 'Ninguna receta lo usa', COLOR.sin, sin.length, `${soles(sum(sin))} porcionados`, 'Se porcionó y ni una receta de venta o receta base activas, ni un directo de la carta, ni una venta, ni otro porcionamiento lo nombra'),
    k('neg', 'Kardex en negativo al final', 'var(--danger-text)', t.filter(negativo).length, 'se descargó lo que no había', 'El corte terminó el período con stock debajo de cero en el kardex (todas las áreas): es lo que después sale como sobrante y faltante en el Ajuste'),
    k('viejo', 'Ya no se porciona', COLOR.viejo, de('viejo').length, 'suele ser un código viejo', 'Sin receta y sin porcionamientos en los últimos 14 días del período: el código viejo de un cambio de receta'),
    k('salida', 'Sale por notas de salida', COLOR.salida, de('salida').length, 'comida del personal, bajas', 'Las notas de salida cubren al menos la mitad de lo porcionado: no es un tema de receta'),
  ].join('');
}
function htmlLista(raiz) {
  const { st } = raiz.__d, v = ventana(raiz), anio = Number(v.fin.slice(0, 4));
  const t = v.filas.filter((f) => pasa(st, f));
  const grupos = new Map();
  for (const f of t) { if (!grupos.has(f.grupo_cod)) grupos.set(f.grupo_cod, []); grupos.get(f.grupo_cod).push(f); }
  const gs = [...grupos.values()];
  const enjuego = (g) => g.reduce((a, f) => a + (f.clase === 'salida' ? 0 : f.valor), 0);
  // «Por valor» es el orden de Python (lo que está en juego por insumo); A–Z, por el insumo.
  if (st.orden === 'nombre') gs.sort((a, b) => a[0].grupo.localeCompare(b[0].grupo, 'es'));
  const n = `${t.length} corte${t.length === 1 ? '' : 's'} · ${gs.length} insumo${gs.length === 1 ? '' : 's'}`;
  if (!t.length) return [n, '<div class="vacio">Nada para revisar con este filtro.</div>'];
  const mx = Math.max(1e-9, ...t.map((f) => Math.max(f.porc, f.ped)));
  const w = (x) => `${(100 * x / mx).toFixed(1)}%`;
  const html = gs.map((g) => {
    // Un par del mismo insumo y la misma unidad —uno de cada señal— suele ser UNA receta que apunta al corte equivocado.
    const falta = g.filter((f) => f.clase === 'falta'), sin = g.filter((f) => f.clase === 'sin' || f.clase === 'viejo');
    const par = falta.some((a) => sin.some((b) => a.unid === b.unid));
    return `<div class="grupo"><div class="gcab"><span>Sale de <b>${esc(g[0].grupo)}</b>${par ? ' · <span class="par" title="Uno que se porciona y ninguna receta usa, y otro que las recetas piden y no se porciona, en la misma unidad: suele ser una receta que apunta al corte equivocado">posible receta equivocada</span>' : ''}</span><span>${soles(enjuego(g))} en juego</span></div>` +
      g.map((f) => {
        const sub = f.platos.length ? `lo piden: ${f.platos.slice(0, 2).map((p) => p[0]).join(' · ')}`
          : (Object.keys(f.salio).length ? `salió por: ${Object.keys(f.salio).join(', ')}` : 'ninguna receta activa lo nombra');
        return `<div class="f${st.sel === f.cod ? ' sel' : ''}" data-acc="sel" data-id="${esc(f.cod)}" role="button" tabindex="0">
          <span class="c"><b title="${esc(f.corte)}">${esc(corto(f.corte))}</b><span title="${esc(sub)}">${esc(sub)}</span></span>
          <span class="ch"><span class="chip ch-${f.clase}" title="${esc(f.que)}"><i></i>${esc(f.que)}</span></span>
          <span class="barras b"><div><span>porcionado</span><s><i style="width:${w(f.porc)};background:var(--accent)"></i></s></div><div><span>piden</span><s><i style="width:${w(f.ped)};background:var(--danger)"></i></s></div></span>
          <span class="v" title="${f.clase === 'falta' ? 'Lo que faltó porcionar, al precio de hoy' : 'Lo porcionado, al costo del porcionamiento'}">${soles(f.valor)}</span>
          <span class="u" title="Último porcionamiento">${fecha(f.ultimo, anio)}</span></div>`;
      }).join('') + '</div>';
  }).join('');
  return [n, html];
}

function semanas(d, f) {
  const W = 330, H = 86, n = d.sems.length;
  const semP = f.semP.length ? f.semP : new Array(n).fill(0), semD = f.semD.length ? f.semD : new Array(n).fill(0);
  const mx = Math.max(1e-9, ...semP, ...semD);
  const x = (k) => 6 + ((W - 12) * (k + 0.5)) / n, y = (v) => 8 + (H - 26) * (1 - v / mx), bw = ((W - 12) / n) * 0.55;
  let s = `<svg class="sem" viewBox="0 0 ${W} ${H}" role="img" aria-label="Porcionado y pedido por semana">`;
  s += `<line x1="0" x2="${W}" y1="${y(0)}" y2="${y(0)}" style="stroke:var(--border)"/>`;
  const sem = (k) => { const [, m, dd] = d.sems[k].split('-').map(Number); return `${dd} ${MES[m - 1]}`; };
  semP.forEach((v, k) => { if (v > 0) s += `<rect x="${x(k) - bw / 2}" y="${y(v)}" width="${bw}" height="${y(0) - y(v)}" rx="1.5" style="fill:var(--accent)"><title>Semana del ${sem(k)}: porcionado ${cant(v, f.unid)}</title></rect>`; });
  if (semD.some((v) => v > 0)) {
    let dd = '';
    semD.forEach((v, k) => { dd += `${dd ? 'L' : 'M'}${x(k).toFixed(1)},${y(v).toFixed(1)}`; });
    s += `<path d="${dd}" fill="none" style="stroke:var(--danger)" stroke-width="1.8"/>`;
    semD.forEach((v, k) => { s += `<circle cx="${x(k)}" cy="${y(v)}" r="2.4" style="fill:var(--danger)"><title>Semana del ${sem(k)}: piden ${cant(v, f.unid)}</title></circle>`; });
  }
  [0, Math.floor(n / 2), n - 1].forEach((k) => { s += `<text x="${x(k)}" y="${H - 3}" text-anchor="middle" style="font-size:10px;fill:var(--text-secondary)">${sem(k)}</text>`; });
  return s + '</svg>';
}
function veredicto(f) {
  const u = f.unid;
  if (f.clase === 'falta') {
    if (negativo(f)) return ['rojo', `Las ventas pidieron <b>${cant(f.ped, u)}</b> y se porcionaron <b>${cant(f.porc, u)}</b>. El kardex terminó en <b>${cant(f.stFin, u)}</b>: el POS descargó lo que no estaba. Ese negativo sale después como sobrante de otro corte y faltante de éste.`];
    if (f.stIni != null && f.stIni + f.porc + f.comprado >= f.ped * 0.9) return ['gris', `Alcanzó con el stock que había al empezar (${cant(f.stIni, u)}): puede ser sólo que se porciona por tandas.`];
    return ['', `Las ventas pidieron <b>${cant(f.ped, u)}</b> y se porcionaron <b>${cant(f.porc, u)}</b>${f.stIni != null ? ', y no alcanzaba con el stock de inicio' : ''}.${f.stFin != null ? ` El kardex terminó en ${cant(f.stFin, u)}: algo más lo repuso, o la receta pide de más.` : ''}`];
  }
  if (f.clase === 'sin') {
    return ['', f.stFin != null && f.stFin > 0.005
      ? `Se porcionaron <b>${cant(f.porc, u)}</b> y ninguna receta lo descarga: se acumula en el kardex (<b>${cant(f.stFin, u)}</b> al terminar). Si la cocina lo usa, alguna receta pide otro código.`
      : `Se porcionaron <b>${cant(f.porc, u)}</b> y ninguna receta activa lo nombra. El stock no se acumula: sale por otro lado (notas, ajustes).`];
  }
  if (f.clase === 'viejo') return ['gris', `Se dejó de porcionar el ${fecha(f.ultimo)} y ninguna receta de hoy lo usa: suele ser el código viejo de un cambio de receta.${f.stFin ? ` Le quedan ${cant(f.stFin, u)} en el kardex.` : ''}`];
  return ['gris', `Salió por notas de salida (${Object.entries(f.salio).map(([k, v]) => `${esc(k)} ${cant(v, u)}`).join(', ')}): no es un tema de receta.`];
}
const QUE_HACER = {
  falta: 'Mirá la receta de los platos de abajo: probablemente piden este corte y la cocina porciona otro, o porciona menos de lo que la receta dice. Si es eso, se corrige en el POS editando la receta; si se porcionó y no se registró, falta el porcionamiento.',
  sin: 'Buscá qué receta debería usarlo. Si es un subproducto (retazos, grasa), decidí si va a una receta o a una nota de salida.',
  viejo: 'Si ya no se usa, desactivalo en el maestro y ajustá su stock en el próximo cierre.',
  salida: 'Nada que corregir en recetas.',
};
function htmlFicha(raiz) {
  const { data: d, st } = raiz.__d, v = ventana(raiz), anio = Number(v.fin.slice(0, 4));
  const f = v.filas.find((x) => x.cod === st.sel);
  if (!f) return '<div class="vacio">Tocá un corte para ver su cuenta, semana a semana, y qué receta mirar.</div>';
  const u = f.unid, [cls, ver] = veredicto(f);
  const conStock = f.stIni != null && f.stFin != null;
  const esperado = (f.stIni ?? 0) + f.porc + f.comprado - f.ped;
  const plat = f.platos.map((p) => `<span title="${esc(p[0])}">${esc(p[0])}</span><span class="d">${cant(p[1], u)}</span><span class="d">${p[2].toLocaleString('en-US')} vend.</span>`).join('');
  const porcs = f.porcs.map((p) => `<span title="${esc(p[1])}">${fecha(p[0], anio)} · de ${esc(corto(p[1]))}</span><span class="d">${cant(p[2], u)}</span><span></span>`).join('');
  const hermanos = v.filas.filter((x) => x.grupo_cod === f.grupo_cod && x.cod !== f.cod);
  const cod = f.platos.map((p) => [p[0], d.codigos[String(p[0]).trim().toLowerCase()]]).find((p) => p[1]);
  return `
    <div class="fi-cab"><span class="chip ch-${f.clase}" style="justify-self:start"><i></i>${esc(f.que)}</span><span class="fi-nom">${esc(f.corte)}</span><span class="fi-de">Sale de ${esc(f.grupo)} · último porcionamiento ${fecha(f.ultimo, anio)}</span></div>
    <div class="veredicto ${cls}">${ver}</div>
    <div class="bl"><div class="bl-t">La cuenta del período<span>en ${esc(un(u))}</span></div>
      <div class="cuenta">${conStock ? `<span>Stock al empezar (kardex)</span><span>${cant(f.stIni, u)}</span>` : ''}<span>${conStock ? '+ ' : ''}Porcionado</span><span>${cant(f.porc, u)}</span>
      ${f.comprado ? `<span>+ Comprado</span><span>${cant(f.comprado, u)}</span>` : ''}<span>− Piden las ventas</span><span>${cant(f.ped, u)}</span>
      ${conStock ? `<span class="t">= Debería quedar</span><span class="t">${cant(esperado, u)}</span><span>Stock al ${fecha(v.fin, anio)} (kardex)</span><span class="${negativo(f) ? 'rojo' : ''}">${cant(f.stFin, u)}</span>` : '<span class="gris">El kardex no se pudo leer: falta el stock.</span><span></span>'}</div></div>
    <div class="bl"><div class="bl-t">Semana a semana<span>${d.sems.length} semanas</span></div>${semanas(d, f)}<div class="ley"><span><i style="background:var(--accent)"></i>porcionado</span><span><i style="background:var(--danger)"></i>piden las ventas</span></div></div>
    ${plat ? `<div class="bl"><div class="bl-t">Recetas que lo piden<span>en el período</span></div><div class="mini">${plat}</div></div>` : ''}
    ${porcs ? `<div class="bl"><div class="bl-t">Últimos porcionamientos</div><div class="mini">${porcs}</div></div>` : ''}
    ${hermanos.length ? `<div class="bl"><div class="bl-t">Del mismo insumo</div><div class="mini">${hermanos.map((h) => `<span title="${esc(h.corte)}">${esc(corto(h.corte))}</span><span class="d">${esc(h.que)}</span><span></span>`).join('')}</div></div>` : ''}
    <div class="que-hacer"><b>Qué hacer</b>${QUE_HACER[f.clase] || ''}</div>
    ${cod ? `<div class="acc"><button type="button" class="btn" data-acc="carta" data-id="${esc(cod[1])}">Ver «${esc(cod[0])}» en Costo de Carta ›</button></div>` : ''}`;
}

// ── Dibujar ──────────────────────────────────────────────────────────────
function dibujar(raiz, solo) {
  const { st } = raiz.__d;
  if (!raiz.querySelector('.cuerpo')) {
    raiz.innerHTML = `<div class="rr-cab" data-zona="cab"></div><div class="kpis" data-zona="kpis"></div>
      <div class="cuerpo"><div class="caja lista"><div class="lcab"><input data-acc="buscar" placeholder="Buscar un corte, insumo o plato…" aria-label="Buscar un corte, insumo o plato">
      <div class="seg" role="group" data-zona="orden"></div><span class="n" data-zona="n"></span></div><div class="filas" data-zona="filas"></div></div>
      <aside class="caja ficha" data-zona="ficha" aria-label="Ficha del corte"></aside></div>`;
  }
  const z = (n) => raiz.querySelector(`[data-zona="${n}"]`);
  const v = ventana(raiz);
  if (st.sel === null || !v.filas.some((f) => f.cod === st.sel && pasa(st, f))) {
    const prim = v.filas.find((f) => pasa(st, f));
    st.sel = prim ? prim.cod : null;
  }
  if (solo !== 'sel') {
    z('cab').innerHTML = htmlCab(raiz);
    z('kpis').innerHTML = htmlKpis(raiz);
    z('orden').innerHTML = [['valor', 'Por valor'], ['nombre', 'A–Z']].map(([id, r]) => `<button type="button" data-acc="orden" data-id="${id}" class="${st.orden === id ? 'on' : ''}">${r}</button>`).join('');
  }
  const y = z('filas').scrollTop;
  const [n, html] = htmlLista(raiz);
  z('n').textContent = n;
  z('filas').innerHTML = html;
  if (solo === 'sel') z('filas').scrollTop = y;
  z('ficha').innerHTML = htmlFicha(raiz);
  if (solo !== 'sel') z('ficha').scrollTop = 0;
}

function enlazar(raiz) {
  const elegir = (b) => {
    const { st } = raiz.__d, id = b.dataset.id, acc = b.dataset.acc;
    if (acc === 'sel') { if (st.sel === id) return; st.sel = id; dibujar(raiz, 'sel'); raiz.querySelector('[data-zona="ficha"]').scrollTop = 0; return; }
    if (acc === 'carta') { raiz.__d.enviar('carta', { cod: id, n: Date.now() }); return; }
    if (acc === 'dias') st.dias = Number(id);
    else if (acc === 'filtro') { st.filtro = st.filtro === id ? null : id; st.sel = null; }
    else if (acc === 'orden') st.orden = id;
    else return;
    guardar(CLAVE, { dias: st.dias, orden: st.orden });
    dibujar(raiz);
  };
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b) || b.tagName === 'INPUT') return;
    elegir(b);
  });
  raiz.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter' && ev.key !== ' ') return;
    const b = ev.target.closest('.f[data-acc="sel"]');
    if (b) { ev.preventDefault(); elegir(b); }
  });
  raiz.addEventListener('input', (ev) => {
    if (ev.target.dataset.acc !== 'buscar') return;
    raiz.__d.st.q = ev.target.value;
    raiz.__d.st.sel = null;
    dibujar(raiz, 'buscar');
  });
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  if (!data || !data.ventanas || !data.ventanas.length) return;
  let raiz = parentElement.querySelector('.rr');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'rr';
    parentElement.appendChild(raiz);
    raiz.__d = { st: Object.assign({ dias: data.ventanas[0].dias, orden: 'valor' }, leer(CLAVE, {}), { filtro: null, q: '', sel: null }) };
    enlazar(raiz);
  }
  raiz.__d.enviar = setTriggerValue;
  raiz.__d.data = data;
  if (!data.ventanas.some((v) => v.dias === raiz.__d.st.dias)) raiz.__d.st.dias = data.ventanas[0].dias;
  dibujar(raiz);
}
