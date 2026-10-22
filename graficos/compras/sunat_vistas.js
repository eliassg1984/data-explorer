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

// Las notas de crédito dentro de lo que falta cargar (a pedido): la
// fidelidad las suma en valor absoluto, y sin decirlo el monto se lee como
// compra real. `ncFalta` va debajo de la cifra de «Falta cargar»; `ncSub`,
// en el renglón de un proveedor. El NETO resta la nota en vez de sumarla:
// una factura anulada por una nota del mismo monto, las dos sin cargar,
// es S/ 0 que falta, no el doble.
//
// Con «Notas de crédito: Aparte» (regla #694) las notas SIN CARGAR salen
// del total y de lo que falta cargar: la fidelidad mide sólo facturas,
// boletas y demás. Lo lee todo el Cruce por `v()`, nunca `f[m][k]` suelto.
let NC_APARTE = false;

function v(f, m, k) {
  const x = f[m][k];
  if (!NC_APARTE || (k !== 'sunat' && k !== 'falta')) return x;
  const nc = f.nc || {};
  return x - (m === 'doc' ? nc.falta || 0 : nc.falta_s || 0);
}

function ncFalta(f, m) {
  const nc = f.nc || {};
  if (!nc.falta) return '';
  const notas = nc.falta === 1 ? 'nota' : 'notas';
  if (NC_APARTE) {
    const q = m === 'doc' ? `sin ${nc.falta} ${notas} de crédito` : `sin ${soles(nc.falta_s)} en ${notas} de crédito`;
    return `<small class="nc-txt" title="Las notas de crédito sin cargar están aparte: no cuentan en el total ni en lo que falta">${q}</small>`;
  }
  const q = m === 'doc' ? `${nc.falta} ${nc.falta === 1 ? 'es nota' : 'son notas'} de crédito`
    : `incl. ${soles(nc.falta_s)} en ${notas} de crédito · neto ${soles(f.soles.falta - 2 * nc.falta_s)}`;
  return `<small class="nc-txt" title="Notas de crédito sin cargar: el proveedor devuelve o anula, no es compra">${q}</small>`;
}
const ncSub = (f) => {
  const n = (f.nc || {}).falta;
  return n ? `${n} ${n === 1 ? 'nota' : 'notas'} de crédito` : '';
};

function pct(f, m) {
  const b = v(f, m, 'sunat');
  return b ? (v(f, m, 'cuadran') / b) * 100 : null;
}
const pctTxt = (p) => (p === null || p === undefined ? '—' : p.toFixed(1) + ' %');
const val = (x, m) => (m === 'doc' ? ent(x) : soles(x));

function delta(a, b) {
  if (a === null || b === null || a === undefined || b === undefined) return '<span class="gris">—</span>';
  const d = Math.round((a - b) * 10) / 10;
  if (d > 0) return `▲ ${d.toFixed(1)}`;
  if (d < 0) return `▼ ${Math.abs(d).toFixed(1)}`;
  return '=';
}

// El texto de la ficha de un tramo (a pedido: «al pasar el cursor o hacer
// clic, que diga cuánto y qué %»). Las DOS medidas, cada una con su %:
// lo que se mide en pantalla primero.
function ficha(f, k, nombre, rotulo, m) {
  const lin = (mm) => {
    const b = v(f, mm, 'sunat');
    const x = v(f, mm, k);
    const p = b ? ((x / b) * 100).toFixed(1) + ' %' : '—';
    return mm === 'doc' ? `${ent(x)} ${x === 1 ? 'documento' : 'documentos'} · ${p} de los documentos`
      : `${soles(x)} · ${p} de los soles`;
  };
  const out = [`${nombre} — ${rotulo}`].concat(m === 'doc' ? [lin('doc'), lin('soles')] : [lin('soles'), lin('doc')]);
  const nc = f.nc || {};
  if (k === 'falta' && nc.falta) {
    out.push(NC_APARTE ? `Aparte: ${ent(nc.falta)} notas de crédito sin cargar (${soles(nc.falta_s)})`
      : `De eso, ${ent(nc.falta)} ${nc.falta === 1 ? 'es nota' : 'son notas'} de crédito (${soles(nc.falta_s)})`);
  }
  return out.join('\n');
}

// Las barras. El tramo de notas de crédito sin cargar va rayado al final de
// lo que falta: son pocas, así que se le da un ancho mínimo para que se vea
// (la cifra exacta está en la columna y en la ficha).
function barra(f, m, chica, rotulo) {
  const b = v(f, m, 'sunat');
  if (!b) return `<div class="barra${chica ? ' chica' : ''} vacia"></div>`;
  const w = (x) => (x / b) * 100;
  const nc = f.nc || {};
  const ncV = NC_APARTE ? 0 : (m === 'doc' ? nc.falta || 0 : nc.falta_s || 0);
  const wN = ncV ? Math.min(Math.max(w(ncV), 0.8), w(v(f, m, 'falta'))) : 0;
  const wF = Math.max(w(v(f, m, 'falta')) - wN, 0);
  const tramo = (cls, ancho, k, nombre) => (ancho > 0
    ? `<i class="${cls}" style="width:${ancho.toFixed(2)}%" data-tip="${esc(ficha(f, k, nombre, rotulo || '', m))}"></i>` : '');
  return `<div class="barra${chica ? ' chica' : ''}">` +
    tramo('c', w(v(f, m, 'cuadran')), 'cuadran', 'Cuadran') +
    tramo('d', w(v(f, m, 'diferencia')), 'diferencia', 'Con diferencia') +
    tramo('f', wF, 'falta', 'Falta cargar') +
    tramo('n', wN, 'falta', 'Falta cargar') + '</div>';
}

function seg(nombre, opciones, actual) {
  return `<div class="campo"><span class="rot">${esc(nombre)}</span><div class="seg">` +
    opciones.map(([x, t]) => `<button type="button" data-seg="${esc(nombre)}" data-v="${esc(x)}" class="${x === actual ? 'on' : ''}">${esc(t)}</button>`).join('') +
    '</div></div>';
}

const leyenda = () => '<span class="ley"><i class="c"></i>Cuadran</span><span class="ley"><i class="d"></i>Con diferencia</span>' +
  '<span class="ley"><i class="f"></i>Falta cargar</span>' + (NC_APARTE ? '' : '<span class="ley"><i class="n"></i>de eso, nota de crédito</span>');

// ── Cruce con SUNAT ────────────────────────────────────────────────────
//
// Regla #694 (el boceto «D» aprobado): los años se eligen con píldoras
// («Comparar con») y TODO se compara con los años a la vista: abrir un tipo
// lo muestra año por año, «Por año» abre cada año por tipo y «Tipo × año»
// pone las seis tarjetas juntas. El «vs» de una fila es contra el año
// visible que le sigue. Las filas de detalle son filas de LA MISMA tabla
// (no una tabla adentro de una celda), para que sus barras caigan en la
// misma columna y midan lo mismo que la de arriba.

const COLS = '<colgroup><col style="width:24%"><col style="width:104px"><col style="width:60px"><col style="width:22%">' +
  '<col style="width:80px"><col style="width:128px"><col style="width:84px"><col style="width:100px"><col style="width:26px"></colgroup>';

function aniosVisibles(st) {
  return st.data.anios.filter((a) => a.actual || !st.ocultos.includes(a.id));
}

// El `f` de un tipo en un año (o el total del año con id '__total').
function fDe(a, id) {
  if (id === '__total') return a.f;
  const x = (a.det || []).find((t) => t.id === id);
  return x ? x.f : null;
}

// El «vs» contra el año visible siguiente.
function vsSig(vis, i, id, m) {
  const a = vis[i], b = vis[i + 1];
  if (!b) return '<span class="gris">—</span>';
  const fa = fDe(a, id), fb = fDe(b, id);
  return fa && fb ? delta(pct(fa, m), pct(fb, m)) : '<span class="gris">—</span>';
}

function celdas(f, m, rotulo, chica) {
  return `<td class="n">${soles(v(f, 'soles', 'sunat'))}</td><td class="n gris">${ent(v(f, 'doc', 'sunat'))}</td>` +
    `<td>${barra(f, m, chica, rotulo)}</td><td class="n${chica ? '' : ' fuerte'}">${pctTxt(pct(f, m))}</td>` +
    `<td class="n">${v(f, m, 'falta') ? val(v(f, m, 'falta'), m) + ncFalta(f, m) : '<span class="gris">—</span>'}</td>`;
}

function cruce(raiz) {
  const st = raiz.__st, d = st.data, m = st.medida, modo = st.modo;
  NC_APARTE = st.nc === 'aparte';
  const vis = aniosVisibles(st);
  const t = d.total, pT = pct(t.f, m);
  const otros = vis.slice(1).map((a) => `${pctTxt(pct(a.f, m))} en ${esc(a.anio)}`).join(' · ');
  const nc = t.f.nc || {};
  const que = m === 'doc' ? 'documentos de SUNAT' : 'facturados en SUNAT';
  let h = '<div class="cab">' +
    `<div class="kpi"><div class="rot">Fidelidad respecto de SUNAT${m === 'soles' ? ' · en soles' : ' · en documentos'}</div>` +
    `<div class="fila-kpi"><span class="grande">${pctTxt(pT)}</span>${otros ? `<span class="chip-kpi">${otros}</span>` : ''}</div>` +
    `<div class="sub">${v(t.f, m, 'sunat') ? `${val(v(t.f, m, 'cuadran'), m)} de los ${val(v(t.f, m, 'sunat'), m)} ${que} están cargados y cuadran` : 'SUNAT no tiene documentos en el período'} · ${esc(d.rango)}</div>` +
    (nc.falta ? `<div class="sub">${NC_APARTE
      ? `${ent(nc.falta)} notas de crédito sin cargar (${soles(nc.falta_s)}) quedan aparte: el % mide sólo facturas, boletas y demás`
      : `De lo que falta cargar, ${ent(nc.falta)} ${nc.falta === 1 ? 'es nota' : 'son notas'} de crédito (${soles(nc.falta_s)}): el proveedor devuelve o anula, no es compra`}</div>` : '') +
    '</div>' +
    seg('Filas', [['tipo', 'Por tipo'], ['anio', 'Por año'], ['tipoxanio', 'Tipo × año']], modo) +
    seg('Notas de crédito sin cargar', [['incluir', 'En lo que falta'], ['aparte', 'Aparte']], st.nc) +
    seg('Medir en', [['soles', 'Soles'], ['doc', 'Documentos']], m) + '</div>';

  // Los años a comparar: el actual fijo, los demás se suman o se quitan.
  h += '<div class="chips"><span class="rot">Comparar con</span>' +
    `<span class="chip fijo">${esc(d.anios[0].anio)} · actual</span>` +
    d.anios.slice(1).map((a) => {
      const on = !st.ocultos.includes(a.id);
      return `<button type="button" class="chip${on ? ' on' : ''}" data-anio="${esc(a.id)}" aria-pressed="${on}" title="${esc(a.sub)}">${on ? '✓' : '+'} ${esc(a.anio)}</button>`;
    }).join('') + '</div>';

  if (modo === 'tipoxanio') h += tarjetas(st, vis, m);
  else h += tabla(st, vis, m);

  const notas = [leyenda()];
  const rec = d.recientes || {};
  if (rec.doc && v(t.f, m, 'falta')) {
    notas.push(`↳ ${val(m === 'doc' ? rec.doc : rec.soles, m)} de lo que falta cargar es de los últimos ${rec.dias || 7} días: puede ser sólo demora de carga.`);
  }
  notas.push('Pasá el cursor o hacé clic en una barra para ver cuánto es cada parte.');
  notas.push('Fuera de SUNAT = cargado en el sistema sin comprobante en SUNAT; no suma al 100 %.');
  (d.avisos || []).forEach((a) => notas.push(a));
  h += '<div class="notas">' + notas.map((n, i) => (i === 0 ? n : `<span>${esc(n)}</span>`)).join('') + '</div>';
  return h;
}

function tabla(st, vis, m) {
  const d = st.data, modo = st.modo, t = d.total;
  const vsTxt = vis[1] ? (modo === 'tipo' ? `vs ${esc(vis[1].anio)}` : 'vs año antes') : 'vs —';
  let h = `<div class="marco"><table class="t-cruce">${COLS}<thead><tr>` +
    `<th>${modo === 'tipo' ? `Qué se compró · ${esc(d.anios[0].anio)}` : 'Período'}</th><th class="n">En SUNAT</th><th class="n">Docs</th><th>Qué pasó con lo de SUNAT</th>` +
    `<th class="n">Fidelidad</th><th class="n">Falta cargar</th><th class="n" title="Diferencia de fidelidad, en puntos">${vsTxt}</th><th class="n" title="Cargado en el sistema sin comprobante en SUNAT: no suma al 100 %">Fuera de SUNAT</th><th></th></tr></thead><tbody>`;

  if (modo === 'tipo') {
    [t].concat(d.tipos).forEach((r) => {
      const esTotal = r.id === '__total';
      const ab = st.abierto === r.id;
      const sub = r.sub || (t.f.soles.sunat ? ((r.f.soles.sunat / t.f.soles.sunat) * 100).toFixed(1) + ' % de lo comprado' : '');
      h += `<tr class="fila${esTotal ? ' total' : ''}${ab ? ' abierta' : ''}" tabindex="0" data-abre="${esc(r.id)}">` +
        `<td><b>${esc(r.nombre)}</b>${sub ? `<small>${esc(sub)}</small>` : ''}</td>` +
        celdas(r.f, m, `${r.nombre} · ${vis[0].anio}`, false) +
        `<td class="n">${vsSig(vis, 0, r.id, m)}</td><td class="n gris">${r.f[m].fuera ? '+' + val(r.f[m].fuera, m) : '0'}</td>` +
        `<td class="flecha">${ab ? '▾' : '▸'}</td></tr>`;
      if (ab) h += anioPorAnio(st, vis, r, m);
    });
  } else {
    vis.forEach((a, i) => {
      const ab = st.abierto === a.id;
      h += `<tr class="fila${a.actual ? ' total' : ''}${ab ? ' abierta' : ''}" tabindex="0" data-abre="${esc(a.id)}">` +
        `<td><b>${esc(a.actual ? `${a.nombre} · ${a.anio}` : a.nombre)}</b><small>${esc(a.sub)}</small></td>` +
        celdas(a.f, m, a.anio, false) +
        `<td class="n">${vsSig(vis, i, '__total', m)}</td><td class="n gris">${a.f[m].fuera ? '+' + val(a.f[m].fuera, m) : '0'}</td>` +
        `<td class="flecha">${ab ? '▾' : '▸'}</td></tr>`;
      if (ab) h += porTipo(vis, i, m);
    });
  }
  return h + '</tbody></table></div>';
}

// Un tipo (o el total) año por año, y debajo quién le baja la fidelidad.
function anioPorAnio(st, vis, r, m) {
  let h = `<tr class="det-cab-fila"><td colspan="9"><div class="det-cab"><b>${esc(r.nombre)} · año por año</b>` +
    '<span class="gris">el mismo rango, corrido un año y dos atrás</span></div></td></tr>';
  vis.forEach((a, i) => {
    const f = fDe(a, r.id);
    if (!f) {
      h += `<tr class="sub-fila quieta"><td>${esc(a.anio)}</td><td colspan="8" class="gris">Sin documentos de ${esc(r.nombre)} en ${esc(a.sub)}</td></tr>`;
      return;
    }
    h += `<tr class="sub-fila quieta anio"><td><span${a.actual ? ' class="fuerte"' : ''}>${esc(a.anio)}</span><small>${esc(a.sub)}</small></td>` +
      celdas(f, m, `${r.nombre} · ${a.anio}`, true) +
      `<td class="n">${vsSig(vis, i, r.id, m)}</td><td class="n gris">${f[m].fuera ? '+' + val(f[m].fuera, m) : '0'}</td><td></td></tr>`;
  });
  if (r.id === '__total') return h;
  h += `<tr class="det-cab-fila"><td colspan="9"><div class="det-cab"><b>Quién le baja la fidelidad a ${esc(r.nombre)}</b><span class="gris">proveedores con documentos sin cargar o con diferencia · ${esc(vis[0].anio)}</span>` +
    `<button type="button" class="ir" data-ir="${esc(JSON.stringify({ tipo: r.id, estados: PEND }))}">Ver estos documentos →</button></div></td></tr>`;
  if (!r.det.length) return h + '<tr class="sub-fila quieta"><td colspan="9" class="vacio">Todo lo de este tipo está cargado y cuadra.</td></tr>';
  for (const p of r.det) {
    const n = p.f.doc;
    const nnc = ncSub(p.f);
    const sub = [n.falta ? `${n.falta} sin cargar${nnc ? ` (${nnc})` : ''}` : '', n.diferencia ? `${n.diferencia} con diferencia` : ''].filter(Boolean).join(' · ');
    h += `<tr class="sub-fila" tabindex="0" data-ir="${esc(JSON.stringify({ tipo: r.id, estados: PEND, prov: p.k }))}" title="Ver sus documentos pendientes en la tabla">` +
      `<td>${esc(p.nombre)}<small>${esc(sub)}</small></td>` + celdas(p.f, m, `${p.nombre} · ${vis[0].anio}`, true) +
      `<td class="n gris">${p.f[m].diferencia ? 'dif. ' + val(p.f[m].diferencia, m) : ''}</td><td></td><td class="flecha">→</td></tr>`;
  }
  return h;
}

// Un año por tipo de compra.
function porTipo(vis, i, m) {
  const a = vis[i];
  let h = `<tr class="det-cab-fila"><td colspan="9"><div class="det-cab"><b>Cómo se reparte ${esc(a.anio)}</b><span class="gris">por tipo de compra</span>` +
    (a.actual ? `<button type="button" class="ir" data-ir="${esc(JSON.stringify({ estados: PEND }))}">Ver lo pendiente →</button>` : '') + '</div></td></tr>';
  for (const x of a.det) {
    const ir = a.actual ? ` tabindex="0" data-ir="${esc(JSON.stringify({ tipo: x.id, estados: PEND }))}" title="Ver lo pendiente de este tipo en la tabla"` : '';
    h += `<tr class="sub-fila${a.actual ? '' : ' quieta'}"${ir}><td>${esc(x.nombre)}</td>` + celdas(x.f, m, `${x.nombre} · ${a.anio}`, true) +
      `<td class="n">${vsSig(vis, i, x.id, m)}</td><td></td><td class="flecha">${a.actual ? '→' : ''}</td></tr>`;
  }
  return h;
}

// «Tipo × año»: una tarjeta por tipo, una barra por año.
function tarjetas(st, vis, m) {
  const d = st.data;
  const ids = [{ id: '__total', nombre: 'Total del período' }].concat(d.tipos.map((x) => ({ id: x.id, nombre: x.nombre })));
  let h = '<div class="tarjetas">';
  for (const r of ids) {
    h += `<div class="tarjeta${r.id === '__total' ? ' ancha' : ''}"><b>${esc(r.nombre)}</b>`;
    vis.forEach((a, i) => {
      const f = fDe(a, r.id);
      if (!f) {
        h += `<div class="t-anio"><span class="gris">${esc(a.anio)}</span><span class="gris todo">sin documentos</span></div>`;
        return;
      }
      h += `<div class="t-anio"><span class="${a.actual ? 'fuerte' : 'gris'}">${esc(a.anio)}</span>` +
        `<span class="n gris">${val(v(f, m, 'sunat'), m)}</span>${barra(f, m, !a.actual, `${r.nombre} · ${a.anio}`)}` +
        `<span class="n fuerte">${pctTxt(pct(f, m))}</span>` +
        `<span class="n">${v(f, m, 'falta') ? val(v(f, m, 'falta'), m) + ncFalta(f, m) : '<span class="gris">—</span>'}</span>` +
        `<span class="n gris">${vsSig(vis, i, r.id, m)}</span></div>`;
    });
    h += '</div>';
  }
  return h + '</div>';
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
      `<td class="n ${s.falta ? 'alerta' : 'gris'}">${s.falta ? `${soles(s.falta)} · ${n.falta}${ncFalta(r.f, 'soles')}` : '—'}</td>` +
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
    `<span class="n">${solesC(x.total)}</span><span class="est ${CHIP[x.est] || ''}">${x.total < 0 ? '<b class="nc">NC</b>' : ''}${esc(x.est)}</span></button>`).join('')
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
    NC_APARTE = false;
    raiz.innerHTML = provCab(raiz);
    cuerpoProv(raiz);
  }
  // La ficha de las barras sobrevive al redibujo: es el mismo nodo.
  st.tipFijo = false;
  raiz.__tip.hidden = true;
  raiz.appendChild(raiz.__tip);
}

// La ficha de un tramo de barra: al pasar el cursor, y fija con un clic
// (en un celular no hay cursor). Va en la raíz y no en la tabla, que la
// recortaría con su `overflow`.
function mostrarTip(raiz, s, fijo) {
  const tip = raiz.__tip;
  const [tit, ...resto] = s.dataset.tip.split('\n');
  tip.replaceChildren();
  const b = document.createElement('b');
  b.textContent = tit;
  tip.appendChild(b);
  for (const l of resto) {
    const d = document.createElement('div');
    d.textContent = l;
    tip.appendChild(d);
  }
  tip.hidden = false;
  const r = s.getBoundingClientRect(), base = raiz.getBoundingClientRect();
  const x = Math.min(Math.max(r.left + r.width / 2 - base.left, tip.offsetWidth / 2 + 4), base.width - tip.offsetWidth / 2 - 4);
  tip.style.left = x + 'px';
  tip.style.top = (r.top - base.top - 6) + 'px';
  raiz.__st.tipFijo = !!fijo;
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
    const tp = e.target.closest('[data-tip]');
    if (tp) { mostrarTip(raiz, tp, true); return; }
    if (st.tipFijo) { st.tipFijo = false; raiz.__tip.hidden = true; }
    const s = e.target.closest('button[data-seg]');
    if (s) {
      const x = s.dataset.v, nom = s.dataset.seg;
      if (nom === 'Filas') {
        st.modo = x;
        st.abierto = x === 'tipo' ? ((st.data.tipos || [])[0] || {}).id || null : x === 'anio' ? 'actual' : null;
      } else if (nom === 'Medir en') st.medida = x;
      else if (nom === 'Notas de crédito sin cargar') st.nc = x;
      else if (nom === 'Agrupar por') { st.agrupar = x; st.abierto = null; st.orden = x === 'prov' ? 'falta' : 'fecha'; }
      dibujar(raiz);
      return;
    }
    const an = e.target.closest('button[data-anio]');
    if (an) {
      const id = an.dataset.anio;
      st.ocultos = st.ocultos.includes(id) ? st.ocultos.filter((y) => y !== id) : st.ocultos.concat([id]);
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
  raiz.addEventListener('mouseover', (e) => {
    const s = e.target.closest && e.target.closest('[data-tip]');
    if (s) mostrarTip(raiz, s, false);
  });
  raiz.addEventListener('mouseout', (e) => {
    const s = e.target.closest && e.target.closest('[data-tip]');
    if (s && !raiz.__st.tipFijo) raiz.__tip.hidden = true;
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
    // `ocultos`: los años que el usuario sacó de «Comparar con» (abre con
    // todos, a pedido). `nc`: las notas de crédito sin cargar, en «Falta
    // cargar» o aparte.
    raiz.__st = { modo: 'tipo', medida: 'soles', abierto: null, agrupar: 'prov', buscar: '', soloPend: false, orden: 'falta',
      ocultos: [], nc: 'incluir', tipFijo: false };
    raiz.__tip = document.createElement('div');
    raiz.__tip.className = 'tip';
    raiz.__tip.hidden = true;
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
