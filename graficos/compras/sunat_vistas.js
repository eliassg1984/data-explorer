// Las dos vistas de resumen de «Documentos SUNAT» (regla #683): «Cruce con
// SUNAT» y «Proveedores y fechas».
//
// Las monta graficos/compras/_sunat_vistas.py::dibujar con st.components.v2
// (sin iframe, estilos en un shadow root). Python manda en `data` todo lo
// que se puede mirar —las dos medidas, las tres agrupaciones, el detalle de
// cada fila— y la pieza lo alterna sola: abrir una fila, pasar de soles a
// documentos, buscar o reordenar no cuesta una corrida. A Python le llega
// un solo trigger, «ir», cuando hay que mostrar documentos en la tabla:
// {desde, tipo, estados, prov, fini, ffin, rotulo, t}.

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const soles = (v) => 'S/ ' + Math.round(Number(v) || 0).toLocaleString('en-US');
const solesC = (v) => 'S/ ' + (Number(v) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const ent = (v) => Math.round(Number(v) || 0).toLocaleString('en-US');
const PEND = ['Solo SUNAT', 'Diferencia'];

function pct(f, m) {
  const b = f[m].sunat;
  return b ? (f[m].cuadran / b) * 100 : null;
}
const pctTxt = (p) => (p === null || p === undefined ? '—' : p.toFixed(1) + ' %');
const val = (v, m) => (m === 'doc' ? ent(v) : soles(v));

function delta(a, b) {
  if (a === null || b === null || a === undefined || b === undefined) return '<span class="gris">—</span>';
  const d = Math.round((a - b) * 10) / 10;
  if (d > 0) return `▲ ${d.toFixed(1)}`;
  if (d < 0) return `▼ ${Math.abs(d).toFixed(1)}`;
  return '=';
}

function barra(f, m, chica) {
  const b = f[m].sunat;
  if (!b) return `<div class="barra${chica ? ' chica' : ''} vacia"></div>`;
  const w = (k) => ((f[m][k] / b) * 100).toFixed(2);
  const tip = (k, n) => `${n}: ${val(f[m][k], m)} · ${((f[m][k] / b) * 100).toFixed(1)} %`;
  return `<div class="barra${chica ? ' chica' : ''}">` +
    `<i class="c" style="width:${w('cuadran')}%" title="${esc(tip('cuadran', 'Cuadran'))}"></i>` +
    `<i class="d" style="width:${w('diferencia')}%" title="${esc(tip('diferencia', 'Con diferencia'))}"></i>` +
    `<i class="f" style="width:${w('falta')}%" title="${esc(tip('falta', 'Falta cargar'))}"></i></div>`;
}

function seg(nombre, opciones, actual) {
  return `<div class="campo"><span class="rot">${esc(nombre)}</span><div class="seg">` +
    opciones.map(([v, t]) => `<button type="button" data-seg="${esc(nombre)}" data-v="${esc(v)}" class="${v === actual ? 'on' : ''}">${esc(t)}</button>`).join('') +
    '</div></div>';
}

const LEYENDA = '<span class="ley"><i class="c"></i>Cuadran</span><span class="ley"><i class="d"></i>Con diferencia</span>' +
  '<span class="ley"><i class="f"></i>Falta cargar</span>';

// ── Cruce con SUNAT ────────────────────────────────────────────────────

function cruce(raiz) {
  const st = raiz.__st, d = st.data, m = st.medida, modo = st.modo;
  const t = d.total, pT = pct(t.f, m);
  const pPrev = t.prev ? t.prev[m] : null;
  let chip = '';
  if (pT !== null && pPrev !== null && pPrev !== undefined) {
    const dd = Math.round((pT - pPrev) * 10) / 10;
    chip = `<span class="chip-kpi">${dd > 0 ? '▲' : dd < 0 ? '▼' : '='} ${Math.abs(dd).toFixed(1)} pts vs ${esc(d.anio_prev)}</span>`;
  }
  const que = m === 'doc' ? 'documentos de SUNAT' : 'facturados en SUNAT';
  let h = '<div class="cab">' +
    `<div class="kpi"><div class="rot">Fidelidad respecto de SUNAT${m === 'soles' ? ' · en soles' : ' · en documentos'}</div>` +
    `<div class="fila-kpi"><span class="grande">${pctTxt(pT)}</span>${chip}</div>` +
    `<div class="sub">${t.f[m].sunat ? `${val(t.f[m].cuadran, m)} de los ${val(t.f[m].sunat, m)} ${que} están cargados y cuadran` : 'SUNAT no tiene documentos en el período'} · ${esc(d.rango)}</div></div>` +
    seg('Filas', [['tipo', 'Por tipo de compra'], ['anio', 'Por año']], modo) +
    seg('Medir en', [['soles', 'Soles'], ['doc', 'Documentos']], m) + '</div>';

  const vsTxt = modo === 'tipo' ? (d.anio_prev ? `vs ${esc(d.anio_prev)}` : 'vs año pasado') : 'vs año antes';
  h += '<div class="marco"><table class="t-cruce"><colgroup><col style="width:24%"><col style="width:104px"><col style="width:60px"><col style="width:20%">' +
    '<col style="width:80px"><col style="width:108px"><col style="width:96px"><col style="width:108px"><col style="width:26px"></colgroup><thead><tr>' +
    `<th>${modo === 'tipo' ? 'Qué se compró' : 'Período'}</th><th class="n">En SUNAT</th><th class="n">Docs</th><th>Qué pasó con lo de SUNAT</th>` +
    `<th class="n">Fidelidad</th><th class="n">Falta cargar</th><th class="n" title="Diferencia de fidelidad, en puntos">${vsTxt}</th><th class="n" title="Cargado en el sistema sin comprobante en SUNAT: no suma al 100 %">Fuera de SUNAT</th><th></th></tr></thead><tbody>`;

  const filas = modo === 'tipo' ? [t].concat(d.tipos) : d.anios;
  filas.forEach((r, i) => {
    const esTotal = r.id === '__total';
    const abierto = !esTotal && st.abierto === r.id;
    let dl;
    if (modo === 'tipo') dl = r.prev ? delta(pct(r.f, m), r.prev[m]) : '<span class="gris">—</span>';
    else dl = filas[i + 1] ? delta(pct(r.f, m), pct(filas[i + 1].f, m)) : '<span class="gris">—</span>';
    const sub = r.sub || (modo === 'tipo' && t.f.soles.sunat ? ((r.f.soles.sunat / t.f.soles.sunat) * 100).toFixed(1) + ' % de lo comprado' : '');
    h += `<tr class="fila${esTotal ? ' total' : ''}${abierto ? ' abierta' : ''}" ${esTotal ? '' : `tabindex="0" data-abre="${esc(r.id)}"`}>` +
      `<td><b>${esc(r.nombre)}</b>${sub ? `<small>${esc(sub)}</small>` : ''}</td>` +
      `<td class="n">${soles(r.f.soles.sunat)}</td><td class="n gris">${ent(r.f.doc.sunat)}</td>` +
      `<td>${barra(r.f, m)}</td><td class="n fuerte">${pctTxt(pct(r.f, m))}</td>` +
      `<td class="n">${r.f[m].falta ? val(r.f[m].falta, m) : '<span class="gris">—</span>'}</td>` +
      `<td class="n">${dl}</td><td class="n gris">${r.f[m].fuera ? '+' + val(r.f[m].fuera, m) : '0'}</td>` +
      `<td class="flecha">${esTotal ? '' : abierto ? '▾' : '▸'}</td></tr>`;
    if (abierto) h += detalleCruce(st, r, modo, m);
  });
  h += '</tbody></table></div>';

  const notas = [LEYENDA];
  const rec = d.recientes || {};
  if (rec.doc && t.f[m].falta) {
    notas.push(`↳ ${val(m === 'doc' ? rec.doc : rec.soles, m)} de lo que falta cargar es de los últimos ${rec.dias || 7} días: puede ser sólo demora de carga.`);
  }
  notas.push('Fuera de SUNAT = cargado en el sistema sin comprobante en SUNAT; no suma al 100 %.');
  (d.avisos || []).forEach((a) => notas.push(a));
  h += '<div class="notas">' + notas.map((n, i) => (i === 0 ? n : `<span>${esc(n)}</span>`)).join('') + '</div>';
  return h;
}

function detalleCruce(st, r, modo, m) {
  let h = '<tr class="det"><td colspan="9"><div class="det-cab">';
  if (modo === 'tipo') {
    h += `<b>Quién le baja la fidelidad a ${esc(r.nombre)}</b><span class="gris">proveedores con documentos sin cargar o con diferencia</span>` +
      `<button type="button" class="ir" data-ir="${esc(JSON.stringify({ tipo: r.id, estados: PEND }))}">Ver estos documentos →</button></div>`;
    if (!r.det.length) return h + '<div class="vacio">Todo lo de este tipo está cargado y cuadra.</div></td></tr>';
    h += '<table class="t-det"><colgroup><col style="width:24%"><col style="width:104px"><col style="width:60px"><col style="width:20%"><col style="width:80px"><col style="width:108px"><col style="width:96px"><col style="width:108px"><col style="width:26px"></colgroup><tbody>';
    for (const p of r.det) {
      const n = p.f.doc;
      const sub = [n.falta ? `${n.falta} sin cargar` : '', n.diferencia ? `${n.diferencia} con diferencia` : ''].filter(Boolean).join(' · ');
      h += `<tr class="sub-fila" tabindex="0" data-ir="${esc(JSON.stringify({ tipo: r.id, estados: PEND, prov: p.k }))}" title="Ver sus documentos pendientes en la tabla">` +
        `<td>${esc(p.nombre)}<small>${esc(sub)}</small></td><td class="n">${soles(p.f.soles.sunat)}</td><td class="n gris">${ent(n.sunat)}</td>` +
        `<td>${barra(p.f, m, true)}</td><td class="n">${pctTxt(pct(p.f, m))}</td>` +
        `<td class="n">${p.f[m].falta ? val(p.f[m].falta, m) : '<span class="gris">—</span>'}</td>` +
        `<td class="n gris">${p.f[m].diferencia ? 'dif. ' + val(p.f[m].diferencia, m) : ''}</td><td></td><td class="flecha">→</td></tr>`;
    }
  } else {
    h += `<b>Cómo se reparte ${esc(r.nombre)}</b><span class="gris">por tipo de compra</span>` +
      (r.actual ? `<button type="button" class="ir" data-ir="${esc(JSON.stringify({ estados: PEND }))}">Ver lo pendiente →</button>` : '') + '</div>';
    h += '<table class="t-det"><colgroup><col style="width:24%"><col style="width:104px"><col style="width:60px"><col style="width:20%"><col style="width:80px"><col style="width:108px"><col style="width:96px"><col style="width:108px"><col style="width:26px"></colgroup><tbody>';
    for (const x of r.det) {
      const ir = r.actual ? ` tabindex="0" data-ir="${esc(JSON.stringify({ tipo: x.id, estados: PEND }))}" title="Ver lo pendiente de este tipo en la tabla"` : '';
      h += `<tr class="sub-fila${r.actual ? '' : ' quieta'}"${ir}><td>${esc(x.nombre)}</td><td class="n">${soles(x.f.soles.sunat)}</td><td class="n gris">${ent(x.f.doc.sunat)}</td>` +
        `<td>${barra(x.f, m, true)}</td><td class="n">${pctTxt(pct(x.f, m))}</td>` +
        `<td class="n">${x.f[m].falta ? val(x.f[m].falta, m) : '<span class="gris">—</span>'}</td><td></td><td></td><td class="flecha">${r.actual ? '→' : ''}</td></tr>`;
    }
  }
  return h + '</tbody></table></td></tr>';
}

// ── Proveedores y fechas ───────────────────────────────────────────────

const CHIP = { 'Solo SUNAT': 'falta', Diferencia: 'dif', Coincide: 'ok', 'Solo sistema': 'fuera' };

function provCab(raiz) {
  const st = raiz.__st, d = st.data;
  const n = { prov: d.prov.length, mes: d.mes.length, dia: d.dia.length }[st.agrupar];
  const que = { prov: 'proveedores', mes: 'meses', dia: 'días' }[st.agrupar];
  return '<div class="cab">' + seg('Agrupar por', [['prov', 'Proveedor'], ['mes', 'Mes'], ['dia', 'Día']], st.agrupar) +
    `<label class="campo"><span class="rot">Buscar</span><input type="search" class="buscar" placeholder="Proveedor o RUC" value="${esc(st.buscar)}"></label>` +
    `<label class="chk"><input type="checkbox" class="pend" ${st.soloPend ? 'checked' : ''}> Sólo con algo pendiente</label>` +
    `<span class="resumen gris">${ent(n)} ${que}</span></div><div class="cuerpo"></div>`;
}

function filasProv(st) {
  const d = st.data;
  let fs = d[st.agrupar].slice();
  const q = (st.buscar || '').trim().toLowerCase();
  if (q) {
    fs = fs.filter((r) => (r.nombre + ' ' + (r.ruc || '') + ' ' + (r.top || []).map((x) => x.nombre).join(' ')).toLowerCase().includes(q));
  }
  if (st.soloPend) fs = fs.filter((r) => r.f.doc.falta || r.f.doc.diferencia);
  const k = st.orden;
  if (st.agrupar === 'prov' || k !== 'fecha') {
    const v = (r) => (k === 'falta' ? r.f.soles.falta + r.f.soles.diferencia : k === 'docs' ? r.f.doc.sunat : r.f.soles.sunat);
    if (k !== 'fecha') fs.sort((a, b) => v(b) - v(a));
  }
  return fs;
}

function provCuerpo(raiz) {
  const st = raiz.__st, d = st.data, ag = st.agrupar;
  const fs = filasProv(st);
  const maxV = Math.max(1, ...d[ag].map((r) => r.f.soles.sunat));
  const tot = d[ag].reduce((a, r) => a + r.f.soles.sunat, 0) || 1;
  const th = (k, t, cls) => `<th class="${cls || ''}${st.orden === k ? ' ord' : ''}" data-orden="${k}" title="Ordenar">${t}${st.orden === k ? ' ↓' : ''}</th>`;
  let h = '<div class="marco"><table class="t-prov"><colgroup><col style="width:26%"><col style="width:56px"><col style="width:108px"><col style="width:14%">' +
    '<col style="width:118px"><col style="width:118px"><col style="width:96px"><col style="width:76px"><col style="width:24px"></colgroup><thead><tr>' +
    `<th>${{ prov: 'Proveedor', mes: 'Mes', dia: 'Día' }[ag]}</th>` + th('docs', 'Docs', 'n') + th('monto', 'En SUNAT', 'n') +
    '<th>% del período</th>' + th('falta', 'Falta cargar', 'n') + '<th class="n">Con diferencia</th>' +
    `<th>${ag === 'prov' ? 'Últimos 6 meses' : 'Proveedores'}</th><th class="n">${ag === 'prov' ? 'Último doc' : ''}</th><th></th></tr></thead><tbody>`;
  if (!fs.length) h += '<tr><td colspan="9" class="vacio">Nada con estos filtros.</td></tr>';
  for (const r of fs) {
    const ab = st.abierto === ag + '|' + r.k;
    const s = r.f.soles, n = r.f.doc;
    let spark = '';
    if (ag === 'prov') {
      const u = r.serie.slice(-6), mx = Math.max(1, ...u);
      spark = '<div class="spark">' + u.map((v, i) => `<i class="${i === u.length - 1 ? 'u' : ''}" style="height:${Math.max(2, Math.round((v / mx) * 22))}px" title="${esc(d.meses[d.meses.length - 6 + i])}: ${soles(v)}"></i>`).join('') + '</div>';
    } else spark = `<span class="gris">${ent(r.nprov)}</span>`;
    const sub = ag === 'prov' ? [r.ruc ? 'RUC ' + r.ruc : '', r.tipo].filter(Boolean).join(' · ') : '';
    h += `<tr class="fila${ab ? ' abierta' : ''}" tabindex="0" data-abre="${esc(ag + '|' + r.k)}">` +
      `<td><b>${esc(r.nombre)}</b>${sub ? `<small>${esc(sub)}</small>` : ''}</td>` +
      `<td class="n gris">${ent(n.sunat)}</td><td class="n">${soles(s.sunat)}</td>` +
      `<td><div class="part"><div class="pista"><i style="width:${((s.sunat / maxV) * 100).toFixed(1)}%"></i></div><span>${((s.sunat / tot) * 100).toFixed(1)} %</span></div></td>` +
      `<td class="n ${s.falta ? 'alerta' : 'gris'}">${s.falta ? `${soles(s.falta)} · ${n.falta}` : '—'}</td>` +
      `<td class="n ${s.diferencia ? 'dif' : 'gris'}">${s.diferencia ? `${soles(s.diferencia)} · ${n.diferencia}` : '—'}</td>` +
      `<td>${spark}</td><td class="n gris">${esc(r.ult || '')}</td><td class="flecha">${ab ? '▾' : '▸'}</td></tr>`;
    if (ab) h += detalleProv(st, r, ag);
  }
  h += '</tbody></table></div>';
  return h;
}

function columnas(vals, labs) {
  const mx = Math.max(1, ...vals);
  const k = (v) => (v >= 1000 ? (v / 1000).toFixed(1) + 'K' : Math.round(v));
  return '<div class="cols">' + vals.map((v, i) =>
    `<div class="col" title="${esc(labs[i])}: ${soles(v)}"><span>${v ? k(v) : ''}</span><i class="${i === vals.length - 1 ? 'u' : ''}" style="height:${Math.max(2, Math.round((v / mx) * 96))}px"></i><small>${esc(labs[i])}</small></div>`).join('') + '</div>';
}

function detalleProv(st, r, ag) {
  const d = st.data;
  let izq;
  if (ag === 'prov') {
    const s = r.serie, u = s[s.length - 1], a = s[s.length - 2];
    const kp = [`<b>${soles(u)}</b> en ${esc(d.meses[d.meses.length - 1])}`];
    if (a) kp.push(`<b>${u >= a ? '+' : ''}${(((u / a) - 1) * 100).toFixed(0)} %</b> vs ${esc(d.meses[d.meses.length - 2])}`);
    izq = `<div class="det-tit">${esc(r.nombre)} · mes a mes, 12 meses</div>${columnas(s, d.meses)}<div class="kps">${kp.join(' · ')}</div>`;
  } else {
    const mx = Math.max(1, ...r.top.map((x) => x.v));
    izq = `<div class="det-tit">Proveedores ${ag === 'mes' ? 'del mes' : 'del día'}</div><div class="hbarras">` +
      r.top.map((x) => `<div class="hb"><span title="${esc(x.nombre)}">${esc(x.nombre)}</span><div class="pista"><i style="width:${((x.v / mx) * 100).toFixed(1)}%"></i></div><b>${soles(x.v)}</b></div>`).join('') + '</div>';
  }
  const ir = ag === 'prov' ? { prov: r.k } : { fini: r.fini, ffin: r.ffin, rotulo: r.nombre };
  const titDocs = ag === 'prov' ? 'Sus documentos del período' : 'Lo pendiente';
  const docs = r.docs.length ? r.docs.map((x) => `<button type="button" class="doc" data-ir="${esc(JSON.stringify(ir))}" title="Ver en la tabla">` +
    `<span class="gris">${esc(x.fe)}</span><span class="nom">${esc(ag === 'prov' ? x.doc : x.prov + ' · ' + x.doc)}</span>` +
    `<span class="n">${solesC(x.total)}</span><span class="est ${CHIP[x.est] || ''}">${esc(x.est)}</span></button>`).join('')
    : '<div class="vacio">Nada pendiente.</div>';
  return `<tr class="det"><td colspan="9"><div class="det-dos"><div>${izq}</div><div>` +
    `<div class="det-cab"><b>${titDocs}</b><button type="button" class="ir" data-ir="${esc(JSON.stringify(ir))}">Ver sus documentos →</button></div>` +
    `<div class="docs">${docs}</div></div></div></td></tr>`;
}

// ── montaje ────────────────────────────────────────────────────────────

function dibujar(raiz) {
  const st = raiz.__st;
  if (st.data.vista === 'cruce') {
    const sc = raiz.querySelector('.marco')?.scrollTop || 0;
    raiz.innerHTML = cruce(raiz);
    const mc = raiz.querySelector('.marco');
    if (mc) mc.scrollTop = sc;
  } else {
    raiz.innerHTML = provCab(raiz);
    cuerpoProv(raiz);
  }
}

function cuerpoProv(raiz) {
  const c = raiz.querySelector('.cuerpo');
  if (!c) return;
  const sc = c.querySelector('.marco')?.scrollTop || 0;
  c.innerHTML = provCuerpo(raiz);
  const mc = c.querySelector('.marco');
  if (mc) mc.scrollTop = sc;
}

function enviar(raiz, ir) {
  const st = raiz.__st;
  st.enviar({ desde: st.data.vista === 'cruce' ? 'Cruce con SUNAT' : 'Proveedores y fechas', ...ir, t: Date.now() });
}

function enlazar(raiz) {
  raiz.addEventListener('click', (e) => {
    const st = raiz.__st;
    const s = e.target.closest('button[data-seg]');
    if (s) {
      const v = s.dataset.v, nom = s.dataset.seg;
      if (nom === 'Filas') { st.modo = v; st.abierto = null; }
      else if (nom === 'Medir en') st.medida = v;
      else if (nom === 'Agrupar por') { st.agrupar = v; st.abierto = null; st.orden = v === 'prov' ? 'falta' : 'fecha'; }
      dibujar(raiz);
      return;
    }
    const ir = e.target.closest('[data-ir]');
    if (ir) { enviar(raiz, JSON.parse(ir.dataset.ir)); return; }
    const o = e.target.closest('th[data-orden]');
    if (o) { st.orden = o.dataset.orden; cuerpoProv(raiz); return; }
    const f = e.target.closest('tr[data-abre]');
    if (f) {
      st.abierto = st.abierto === f.dataset.abre ? null : f.dataset.abre;
      if (st.data.vista === 'cruce') dibujar(raiz); else cuerpoProv(raiz);
    }
  });
  raiz.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    const ir = e.target.closest && e.target.closest('[data-ir]');
    if (ir && ir.tagName === 'TR') { enviar(raiz, JSON.parse(ir.dataset.ir)); return; }
    const f = e.target.closest && e.target.closest('tr[data-abre]');
    if (f) f.click();
  });
  raiz.addEventListener('input', (e) => {
    const st = raiz.__st;
    if (e.target.classList.contains('buscar')) { st.buscar = e.target.value; cuerpoProv(raiz); }
  });
  raiz.addEventListener('change', (e) => {
    const st = raiz.__st;
    if (e.target.classList.contains('pend')) { st.soloPend = e.target.checked; cuerpoProv(raiz); }
  });
}

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  let raiz = parentElement.querySelector('.sv');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'sv';
    parentElement.appendChild(raiz);
    // Lo que el usuario eligió en la pieza vive en su raíz: una corrida que
    // vuelve a llamar con datos nuevos no se lo lleva.
    raiz.__st = { modo: 'tipo', medida: 'soles', abierto: null, agrupar: 'prov', buscar: '', soloPend: false, orden: 'falta' };
    enlazar(raiz);
  }
  const st = raiz.__st;
  const nueva = !st.data || st.data.vista !== (data || {}).vista;
  st.data = data || { vista: 'cruce' };
  if (nueva && st.data.vista === 'cruce' && st.abierto === null && st.data.tipos && st.data.tipos.length) {
    // Abre con el primer tipo desplegado: es lo que más pesa, y así la vista
    // dice de entrada quién le baja la fidelidad.
    st.abierto = st.data.tipos[0].id;
  }
  st.enviar = (v) => setTriggerValue('ir', v);
  dibujar(raiz);
}
