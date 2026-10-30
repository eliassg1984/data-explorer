// Las dos vistas de resumen de «Documentos SUNAT» (reglas #683 y #760): «Cruce
// con SUNAT» y «Proveedores y fechas», con lista a la izquierda y ficha del
// elegido al costado.
//
// Las monta graficos/compras/_sunat_vistas.py::dibujar con st.components.v2
// (sin iframe, estilos en un shadow root). Python manda en `data` todo lo
// que se puede mirar —las dos medidas, las tres agrupaciones, el detalle de
// cada fila— y la pieza lo alterna sola: elegir una fila, pasar de soles a
// documentos, buscar o reordenar no cuesta una corrida. A Python le llega
// un solo trigger, «ir»: {desde, tipo, estados, prov, fini, ffin, rotulo, t}
// para mostrar documentos en la tabla, o {destino: 'prov', mes, t} para ir de
// un mes del Cruce a ese mes en «Proveedores y fechas».

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const soles = (v) => 'S/ ' + Math.round(Number(v) || 0).toLocaleString('en-US');
const solesC = (v) => 'S/ ' + (Number(v) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const ent = (v) => Math.round(Number(v) || 0).toLocaleString('en-US');
const mil = (v) => { const s = Math.abs(Number(v) || 0); return 'S/ ' + (s >= 1e6 ? (s / 1e6).toFixed(2) + 'M' : s >= 1e3 ? (s / 1e3).toFixed(1) + 'k' : Math.round(s)); };
const PEND = ['Solo SUNAT', 'Diferencia'];
const MES_ABR = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];

// Las notas de crédito dentro de lo que falta cargar (a pedido): la
// fidelidad las suma en valor absoluto, y sin decirlo el monto se lee como
// compra real. `ncFalta` va debajo de la cifra de «Falta cargar»; `ncSub`,
// en el renglón de un proveedor. El NETO resta la nota en vez de sumarla:
// una factura anulada por una nota del mismo monto, las dos sin cargar,
// es S/ 0 que falta, no el doble.
//
// Con «Notas sin cargar: Aparte» (regla #694) las notas SIN CARGAR salen
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
// En una lista va corto, en un renglón: el texto entero queda en el `title`. Con
// el largo, cada fila medía el doble y en pantalla entraban tres.
function ncCorto(f, m) {
  const nc = f.nc || {};
  if (!nc.falta) return '';
  const largo = /title="([^"]*)"[^>]*>([^<]*)/.exec(ncFalta(f, m));
  const q = m === 'doc' ? `${nc.falta} NC` : `${NC_APARTE ? 'sin' : 'incl.'} ${mil(nc.falta_s)} NC`;
  return `<small class="nc-txt" title="${esc(largo ? largo[2] + '. ' + largo[1] : '')}">${q}</small>`;
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
  if (a === null || b === null || a === undefined || b === undefined) return { t: '—', c: 'gris' };
  const d = Math.round((a - b) * 10) / 10;
  if (d > 0) return { t: `▲ ${d.toFixed(1)}`, c: 'sube' };
  if (d < 0) return { t: `▼ ${Math.abs(d).toFixed(1)}`, c: 'baja' };
  return { t: '=', c: 'gris' };
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
// (la cifra exacta está en la columna y en la ficha). `resalta` apaga los otros
// tramos cuando un indicador está elegido.
function barra(f, m, rotulo, resalta) {
  const b = v(f, m, 'sunat');
  if (!b) return '<div class="barra vacia"></div>';
  const w = (x) => (x / b) * 100;
  const nc = f.nc || {};
  const ncV = NC_APARTE ? 0 : (m === 'doc' ? nc.falta || 0 : nc.falta_s || 0);
  const wN = ncV ? Math.min(Math.max(w(ncV), 0.8), w(v(f, m, 'falta'))) : 0;
  const wF = Math.max(w(v(f, m, 'falta')) - wN, 0);
  const tramo = (cls, ancho, k, nombre) => (ancho > 0
    ? `<i class="${cls}${resalta && resalta !== k ? ' apagado' : ''}" style="width:${ancho.toFixed(2)}%" data-tip="${esc(ficha(f, k, nombre, rotulo || '', m))}"></i>` : '');
  return '<div class="barra">' +
    tramo('c', w(v(f, m, 'cuadran')), 'cuadran', 'Cuadran') +
    tramo('d', w(v(f, m, 'diferencia')), 'diferencia', 'Con diferencia') +
    tramo('f', wF, 'falta', 'Falta cargar') +
    tramo('n', wN, 'falta', 'Falta cargar') + '</div>';
}

function seg(nombre, opciones, actual) {
  return `<span class="seg" role="group" aria-label="${esc(nombre)}">` +
    opciones.map(([x, t]) => `<button type="button" data-seg="${esc(nombre)}" data-v="${esc(x)}" class="${x === actual ? 'on' : ''}">${esc(t)}</button>`).join('') +
    '</span>';
}

function select(nombre, clave, opciones, actual) {
  return `<label class="campo"><span class="rot">${esc(nombre)}</span><select data-sel="${clave}">` +
    opciones.map(([x, t]) => `<option value="${esc(x)}"${x === actual ? ' selected' : ''}>${esc(t)}</option>`).join('') + '</select></label>';
}

const leyenda = () => '<span class="ley"><i class="c"></i>Cuadra</span><span class="ley"><i class="d"></i>Con diferencia</span>' +
  '<span class="ley"><i class="f"></i>Falta cargar</span>' + (NC_APARTE ? '' : '<span class="ley"><i class="n"></i>nota de crédito</span>');

// El `f` de un tipo en un año (o el total del año con id '__total').
function fDe(a, id) {
  if (!a) return null;
  if (id === '__total') return a.f;
  const x = (a.det || []).find((t) => t.id === id);
  return x ? x.f : null;
}

// ── Cruce con SUNAT ────────────────────────────────────────────────────
//
// Regla #760: cuatro indicadores del tipo elegido, cada tipo con su barra, y al
// costado quién le baja la fidelidad o cómo viene año por año. «Tipo × año» (las
// tarjetas de la regla #694) sigue como tercera forma, a todo el ancho.

function kpi(k, rot, val_, vari, varCls, nota, activo) {
  return `<button type="button" class="kpi${activo ? ' on' : ''}" data-kpi="${k}" aria-pressed="${activo}"><span class="r">${esc(rot)}</span><span class="val">${esc(val_)}</span>` +
    `<span class="d">${vari ? `<b class="${varCls}">${esc(vari)}</b> ` : ''}${esc(nota)}</span></button>`;
}

function cruce(raiz) {
  const st = raiz.__st, d = st.data, m = st.medida;
  NC_APARTE = st.nc === 'aparte';
  if (st.modo === 'tipoxanio') return cruceTarjetas(st);
  const porAnio = st.modo === 'anio', anios = d.anios, contra = anios[st.contra] || anios[1];
  const filas = porAnio
    ? anios.map((a) => ({ id: a.id, nombre: a.anio, sub: a.sub, f: a.f, a }))
    : [{ id: '__total', nombre: 'Total del período', sub: d.rango, f: d.total.f, tot: true }].concat(d.tipos.map((t) => ({ id: t.id, nombre: t.nombre, f: t.f, det: t.det,
      sub: d.total.f.soles.sunat ? ((t.f.soles.sunat / d.total.f.soles.sunat) * 100).toFixed(1) + ' % de lo comprado' : '' })));
  const sel = porAnio ? st.selAnio : st.sel;
  const el = filas.find((r) => r.id === sel) || filas[porAnio ? 0 : 1] || filas[0];
  const f = el.f, tot = v(f, m, 'sunat') || 1;
  const dl = porAnio ? { t: '', c: '' } : delta(pct(f, m), contra ? pct(fDe(contra, el.id) || { doc: {}, soles: {} }, m) : null);
  const pc = (k) => ((v(f, m, k) / tot) * 100).toFixed(1) + ' %';
  const otra = m === 'doc' ? 'soles' : 'doc';
  const nd = (k) => (otra === 'doc' ? ent(v(f, 'doc', k)) + ' docs' : mil(v(f, 'soles', k)));
  const cifra = (k) => (m === 'doc' ? ent(v(f, m, k)) : mil(v(f, m, k)));
  const kpis = [
    kpi('', 'Fidelidad · ' + el.nombre, pctTxt(pct(f, m)), dl.t, dl.c, porAnio ? cifra('cuadran') + ' cuadran' : contra ? 'vs ' + contra.anio : '', !st.estado),
    kpi('falta', 'Falta cargar', cifra('falta'), '', '', pc('falta') + ' · ' + nd('falta'), st.estado === 'falta'),
    kpi('diferencia', 'Con diferencia', cifra('diferencia'), '', '', pc('diferencia') + ' · ' + nd('diferencia'), st.estado === 'diferencia'),
    kpi('fuera', 'En el sistema, no en SUNAT', m === 'doc' ? ent(f[m].fuera) : mil(f[m].fuera), '', '', 'aparte: no cuenta en la fidelidad', st.estado === 'fuera'),
  ].join('');
  const resalta = st.estado === 'falta' || st.estado === 'diferencia' ? st.estado : null;
  const listaFilas = filas.map((r) => {
    const on = r.id === el.id, x = r.f;
    const dx = porAnio ? { t: '', c: '' } : delta(pct(x, m), contra ? (() => { const fp = fDe(contra, r.id); return fp ? pct(fp, m) : null; })() : null);
    return `<button type="button" class="fila${on ? ' on' : ''}${r.tot ? ' tot' : ''}" data-sel-fila="${esc(r.id)}" aria-pressed="${on}">` +
      `<span class="nom"><b>${esc(r.nombre)}</b><small>${esc(r.sub || '')}</small></span><span class="n">${val(v(x, m, 'sunat'), m)}</span>` +
      `<span class="ocu">${barra(x, m, r.nombre, resalta)}</span><span class="n"><b>${pctTxt(pct(x, m))}</b></span>` +
      `<span class="n ocu ${dx.c}">${dx.t}</span><span class="n">${v(x, m, 'falta') ? val(v(x, m, 'falta'), m) + ncCorto(x, m) : '<span class="gris">—</span>'}</span></button>`;
  }).join('');
  const rec = d.recientes || {};
  const notas = [];
  if (rec.doc) notas.push(`${ent(rec.doc)} documentos (${soles(rec.soles)}) son de los últimos ${rec.dias || 7} días: quizá todavía se estén ingresando.`);
  (d.avisos || []).forEach((a) => notas.push(a));
  const nc = (d.total.f.nc || {});
  if (nc.falta) notas.push(NC_APARTE ? `${ent(nc.falta)} notas de crédito sin cargar (${soles(nc.falta_s)}) quedan aparte: el % mide sólo facturas, boletas y demás.`
    : `De lo que falta cargar, ${ent(nc.falta)} son notas de crédito (${soles(nc.falta_s)}): el proveedor devuelve o anula, no es compra.`);
  const idMes = porAnio || !d.mes[el.id] ? '__total' : el.id;
  const meses = (d.mes && d.mes[idMes]) || [];
  const topM = Math.max(1, ...meses.map((x) => x.f.soles.sunat));
  const barrasMes = meses.map((x) => {
    const q = x.f.soles, p = (k) => ((q[k] / topM) * 100).toFixed(1), fi = q.sunat ? ((q.cuadran / q.sunat) * 100).toFixed(1) : '0';
    const [an, me] = x.k.split('-');
    return `<button type="button" class="mesc" data-mes="${esc(x.k)}" title="${MES_ABR[+me - 1]} ${an}: ${soles(q.sunat)} en SUNAT, ${fi} % cuadra. Ver el mes en Proveedores y fechas."><span class="pila"><i class="f" style="height:${p('falta')}%"></i><i class="d" style="height:${p('diferencia')}%"></i><i class="c" style="height:${p('cuadran')}%"></i></span><span>${MES_ABR[+me - 1]}</span></button>`;
  }).join('');
  const cab = '<div class="fl">' +
    seg('Filas', [['tipo', 'Por tipo'], ['anio', 'Por año'], ['tipoxanio', 'Tipo × año']], st.modo) +
    seg('Medir en', [['soles', 'Soles'], ['doc', 'Documentos']], m) +
    (porAnio ? '' : select('Contra', 'contra', anios.slice(1).map((a, i) => [String(i + 1), a.anio]), String(st.contra))) +
    select('Notas sin cargar', 'nc', [['incluir', 'En lo que falta'], ['aparte', 'Aparte']], st.nc) +
    `<span class="esp"></span><span class="leys">${leyenda()}</span></div>`;
  return `<div class="kpis">${kpis}</div><div class="cuerpo"><div class="izq">${cab}
    <div class="lista tipos"><div class="cabf"><span>${porAnio ? 'Año' : 'Qué se compró'}</span><span class="n">En SUNAT</span><span class="ocu">Qué pasó</span><span class="n">Fidelidad</span><span class="n ocu">${porAnio || !contra ? '' : 'vs ' + esc(contra.anio)}</span><span class="n">Falta cargar</span></div>${listaFilas}</div>
    ${notas.length ? `<div class="nota">${notas.map(esc).join(' ')}</div>` : ''}
    ${meses.length ? `<div class="tit">Mes a mes${idMes === '__total' ? ', todo lo de SUNAT' : ' · ' + esc(el.nombre)}</div><div class="mesg">${barrasMes}</div>` : ''}
  </div>${panelCruce(st, el, porAnio, m, resalta)}</div>`;
}

function fila2(nombre, sub, valor, f, m, rotulo, ir) {
  const dentro = `<span class="pp-nom"><span title="${esc(nombre)}">${esc(nombre)}</span><small>${esc(sub)}</small></span><b>${esc(valor)}</b>${f ? barra(f, m, rotulo) : ''}`;
  return ir ? `<button type="button" class="pp" data-ir="${esc(JSON.stringify(ir))}" title="Ver sus documentos en la tabla">${dentro}</button>` : `<div class="pp">${dentro}</div>`;
}

function panelCruce(st, el, porAnio, m, resalta) {
  const d = st.data;
  const tab = porAnio ? 'quien' : st.tab;
  const tabs = porAnio ? '' : seg('Ficha', [['quien', 'Quién le baja'], ['anios', 'Año por año']], tab);
  let cuerpo = '', sub = '';
  if (porAnio) {
    sub = 'Los tipos de ' + el.nombre;
    cuerpo = (el.a.det || []).map((t) => fila2(t.nombre, 'En SUNAT ' + val(v(t.f, m, 'sunat'), m) + ' · falta ' + val(v(t.f, m, 'falta'), m), pctTxt(pct(t.f, m)), t.f, m, t.nombre,
      el.a.actual ? { tipo: t.id, estados: PEND } : null)).join('');
  } else if (tab === 'anios') {
    sub = 'El mismo rango, corrido un año y dos atrás';
    cuerpo = d.anios.map((a) => {
      const x = fDe(a, el.id);
      if (!x) return fila2(a.anio, 'Sin documentos en ' + a.sub, '—');
      return fila2(a.anio, a.sub + ' · falta ' + val(v(x, m, 'falta'), m), pctTxt(pct(x, m)), x, m, a.anio);
    }).join('');
  } else {
    const fuente = el.id === '__total' ? d.tipos.flatMap((t) => t.det.map((p) => ({ ...p, tipo: t.id }))) : (d.tipos.find((t) => t.id === el.id) || { det: [] }).det.map((p) => ({ ...p, tipo: el.id }));
    const peso = (x) => (resalta ? x[m][resalta] : x[m].falta + x[m].diferencia);
    const orden = fuente.filter((p) => peso(p.f) > 0).sort((a, b) => peso(b.f) - peso(a.f)).slice(0, 8);
    sub = orden.length ? 'Proveedores con algo sin cargar o con diferencia' : 'Todo lo de este tipo está cargado y cuadra.';
    cuerpo = orden.map((p) => {
      const n = p.f.doc, nnc = ncSub(p.f);
      const s = [n.falta ? `${n.falta} sin cargar${nnc ? ` (${nnc})` : ''}` : '', n.diferencia ? `${n.diferencia} con diferencia` : ''].filter(Boolean).join(' · ');
      return fila2(p.nombre, s, val(peso(p.f), m), p.f, m, p.nombre, { tipo: p.tipo, estados: PEND, prov: p.k });
    }).join('');
  }
  const estados = st.estado === 'diferencia' ? ['Diferencia'] : st.estado === 'falta' ? ['Solo SUNAT'] : st.estado === 'fuera' ? ['Solo sistema'] : PEND;
  const ir = porAnio ? (el.a.actual ? { estados: PEND } : null) : { ...(el.id === '__total' ? {} : { tipo: el.id }), estados };
  return `<div class="panel" aria-label="Lo elegido">${tabs}<h3>${esc(el.nombre)}</h3><div class="sub">${esc(sub)}</div>${cuerpo}` +
    (ir ? `<button type="button" class="ir" data-ir="${esc(JSON.stringify(ir))}">Ver estos documentos →</button>` : '') + '</div>';
}

// «Tipo × año»: una tarjeta por tipo, una barra por año.
function cruceTarjetas(st) {
  const d = st.data, m = st.medida, vis = d.anios;
  const ids = [{ id: '__total', nombre: 'Total del período' }].concat(d.tipos.map((x) => ({ id: x.id, nombre: x.nombre })));
  let h = '<div class="fl">' + seg('Filas', [['tipo', 'Por tipo'], ['anio', 'Por año'], ['tipoxanio', 'Tipo × año']], st.modo) +
    seg('Medir en', [['soles', 'Soles'], ['doc', 'Documentos']], m) + select('Notas sin cargar', 'nc', [['incluir', 'En lo que falta'], ['aparte', 'Aparte']], st.nc) +
    `<span class="esp"></span><span class="leys">${leyenda()}</span></div><div class="tarjetas">`;
  for (const r of ids) {
    h += `<div class="tarjeta${r.id === '__total' ? ' ancha' : ''}"><b>${esc(r.nombre)}</b>`;
    vis.forEach((a, i) => {
      const f = fDe(a, r.id);
      if (!f) { h += `<div class="t-anio"><span class="gris">${esc(a.anio)}</span><span class="gris todo">sin documentos</span></div>`; return; }
      const sig = vis[i + 1] && fDe(vis[i + 1], r.id), dx = sig ? delta(pct(f, m), pct(sig, m)) : { t: '—', c: 'gris' };
      h += `<div class="t-anio"><span class="${a.actual ? 'fuerte' : 'gris'}">${esc(a.anio)}</span><span class="n gris">${val(v(f, m, 'sunat'), m)}</span>${barra(f, m, `${r.nombre} · ${a.anio}`)}` +
        `<span class="n fuerte">${pctTxt(pct(f, m))}</span><span class="n">${v(f, m, 'falta') ? val(v(f, m, 'falta'), m) + ncFalta(f, m) : '<span class="gris">—</span>'}</span><span class="n ${dx.c}">${dx.t}</span></div>`;
    });
    h += '</div>';
  }
  return h + '</div>';
}

// ── Proveedores y fechas ───────────────────────────────────────────────

const CHIP = { 'Solo SUNAT': 'falta', Diferencia: 'dif', Coincide: 'ok', 'Solo sistema': 'fuera' };
const ESTADO_TXT = { 'Solo SUNAT': 'Falta cargar', Diferencia: 'Con diferencia', Coincide: 'Cuadra', 'Solo sistema': 'Sólo en el sistema' };

function filasProv(st) {
  const d = st.data;
  let fs = (d[st.agrupar] || []).slice();
  const q = (st.buscar || '').trim().toLowerCase();
  if (q) fs = fs.filter((r) => (r.nombre + ' ' + (r.ruc || '') + ' ' + (r.top || []).map((x) => x.nombre).join(' ')).toLowerCase().includes(q));
  if (st.soloPend) fs = fs.filter((r) => r.f.doc.falta || r.f.doc.diferencia);
  const k = st.orden;
  if (k !== 'fecha') {
    const w = (r) => (k === 'falta' ? r.f.soles.falta + r.f.soles.diferencia : k === 'docs' ? r.f.doc.sunat : r.f.soles.sunat);
    fs.sort((a, b) => w(b) - w(a));
  }
  return fs;
}

function provCab(raiz) {
  const st = raiz.__st;
  return '<div class="fl">' + seg('Agrupar por', [['prov', 'Proveedor'], ['mes', 'Mes'], ['dia', 'Día']], st.agrupar) +
    `<input type="search" class="buscar" aria-label="Buscar" placeholder="Proveedor o RUC" value="${esc(st.buscar)}">` +
    `<label class="chk"><input type="checkbox" class="pend" ${st.soloPend ? 'checked' : ''}> Sólo con algo pendiente</label>` +
    `<span class="esp"></span><span class="nota cuenta"></span></div><div class="cuerpo"></div>`;
}

function provCuerpo(raiz) {
  const st = raiz.__st, ag = st.agrupar, fs = filasProv(st);
  const vis = fs.slice(0, st.limite), el = fs.find((r) => r.k === st.psel) || fs[0];
  raiz.querySelector('.cuenta').textContent = ent(fs.length) + ' ' + { prov: 'proveedores', mes: 'meses', dia: 'días' }[ag];
  const th = (k, t, cls) => `<button type="button" class="${cls || ''}${st.orden === k ? ' ord' : ''}" data-orden="${k}" title="Ordenar">${t}${st.orden === k ? ' ↓' : ''}</button>`;
  const filas = vis.map((r) => {
    const s = r.f.soles, on = el && r.k === el.k;
    const sub = ag === 'prov' ? [r.ruc ? 'RUC ' + r.ruc : '', r.tipo].filter(Boolean).join(' · ') : (r.nprov ? r.nprov + ' proveedores' : '');
    return `<button type="button" class="fila${on ? ' on' : ''}" data-psel="${esc(r.k)}" aria-pressed="${!!on}"><span class="nom"><b>${esc(r.nombre)}</b><small>${esc(sub)}</small></span>` +
      `<span class="n ocu gris">${ent(r.f.doc.sunat)}</span><span class="n">${soles(s.sunat)}</span><span class="ocu">${barra(r.f, 'soles', r.nombre)}</span>` +
      `<span class="n ${s.falta ? 'alerta' : 'gris'}">${s.falta ? soles(s.falta) + ncCorto(r.f, 'soles') : '—'}</span><span class="n gris">${ag === 'prov' ? esc(r.ult || '') : pctTxt(pct(r.f, 'soles'))}</span></button>`;
  }).join('');
  const mas = fs.length > vis.length ? `<button type="button" class="mas" data-mas="1">Mostrar 80 más · ${ent(vis.length)} de ${ent(fs.length)}</button>` : '';
  const c = raiz.querySelector('.cuerpo');
  const sc = c.querySelector('.lista')?.scrollTop || 0;
  c.innerHTML = `<div class="izq"><div class="lista prov"><div class="cabf"><span>${{ prov: 'Proveedor', mes: 'Mes', dia: 'Día' }[ag]}</span>${th('docs', 'Docs', 'n ocu')}${th('monto', 'En SUNAT', 'n')}<span class="ocu">Qué pasó</span>${th('falta', 'Falta cargar', 'n')}<span class="n">${ag === 'prov' ? 'Último' : 'Fidelidad'}</span></div>${filas || '<div class="vacio">Nada con estos filtros.</div>'}${mas}</div></div>${panelProv(st, el, ag)}`;
  const l = c.querySelector('.lista');
  if (l) l.scrollTop = sc;
}

function panelProv(st, el, ag) {
  const d = st.data;
  if (!el) return '<div class="panel"><h3>Nada con este filtro</h3></div>';
  const fs = el.f.soles, fd = el.f.doc;
  const pr = [['En SUNAT', fs.sunat, fd.sunat], ['Cuadra', fs.cuadran, fd.cuadran], ['Con diferencia', fs.diferencia, fd.diferencia], ['Falta cargar', fs.falta, fd.falta], ['En el sistema, no en SUNAT', fs.fuera, fd.fuera]]
    .map(([r, x, n]) => `<div class="pr"><span>${esc(r)}</span><b>${soles(x)}</b><i>${ent(n)} d.</i></div>`).join('');
  let serie = '';
  if (ag === 'prov') {
    const s = el.serie || [], mx = Math.max(1, ...s), u = s[s.length - 1], a = s[s.length - 2];
    const lectura = a ? ` · ${u >= a ? '+' : ''}${(((u / a) - 1) * 100).toFixed(0)} % vs ${d.meses[d.meses.length - 2]}` : '';
    serie = `<div class="tit">En SUNAT, últimos 12 meses${esc(lectura)}</div><div class="meses">${s.map((y, i) => `<span class="${i === s.length - 1 ? 'u' : ''}" style="height:${Math.max(2, (y / mx) * 100).toFixed(0)}%" title="${esc(d.meses[i])}: ${soles(y)}"></span>`).join('')}</div>` +
      `<div class="ejeM">${s.map((y, i) => `<span>${esc(String(d.meses[i] || '').slice(0, 1))}</span>`).join('')}</div>`;
  } else {
    const mx = Math.max(1, ...(el.top || []).map((x) => x.v));
    serie = `<div class="tit">Los que más pesan</div>` + (el.top || []).map((x) => `<div class="hb"><span title="${esc(x.nombre)}">${esc(x.nombre)}</span><div class="pista"><i style="width:${((x.v / mx) * 100).toFixed(1)}%"></i></div><b>${soles(x.v)}</b></div>`).join('');
  }
  const ir = ag === 'prov' ? { prov: el.k } : { fini: el.fini, ffin: el.ffin, rotulo: el.nombre };
  const docs = (el.docs || []).length ? el.docs.map((x) => `<button type="button" class="doc" data-ir="${esc(JSON.stringify(ir))}" title="Ver en la tabla"><span class="gris">${esc(x.fe)}</span><span class="nomd">${esc(ag === 'prov' ? x.doc : x.prov + ' · ' + x.doc)}</span><span class="n">${solesC(x.total)}</span><span class="est ${CHIP[x.est] || ''}">${x.total < 0 ? '<b class="nc">NC</b> ' : ''}${esc(ESTADO_TXT[x.est] || x.est)}</span></button>`).join('') : '<div class="vacio">Nada pendiente.</div>';
  const sub = ag === 'prov' ? [el.ruc ? 'RUC ' + el.ruc : '', el.tipo, el.ult ? 'último doc. ' + el.ult : ''].filter(Boolean).join(' · ') : (el.nprov ? el.nprov + ' proveedores' : '');
  return `<div class="panel"><h3>${esc(el.nombre)}</h3><div class="sub">${esc(sub)}</div>${barra(el.f, 'soles', el.nombre)}${pr}${serie}` +
    `<div class="tit">${ag === 'prov' ? 'Sus documentos más recientes' : 'Lo pendiente'}</div><div class="docs">${docs}</div>` +
    `<button type="button" class="ir" data-ir="${esc(JSON.stringify(ir))}">Ver sus documentos →</button></div>`;
}

// ── montaje ────────────────────────────────────────────────────────────

function dibujar(raiz) {
  const st = raiz.__st;
  if (st.data.vista === 'cruce') {
    const a = raiz.querySelector('.lista')?.scrollTop || 0, b = raiz.querySelector('.panel')?.scrollTop || 0;
    raiz.innerHTML = cruce(raiz);
    if (raiz.querySelector('.lista')) raiz.querySelector('.lista').scrollTop = a;
    if (raiz.querySelector('.panel')) raiz.querySelector('.panel').scrollTop = b;
  } else {
    NC_APARTE = false;
    raiz.innerHTML = provCab(raiz);
    provCuerpo(raiz);
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

function enviar(raiz, ir) {
  const st = raiz.__st;
  st.enviar({ desde: st.data.vista === 'cruce' ? 'Cruce con SUNAT' : 'Proveedores y fechas', ...ir, t: Date.now() });
}

function enlazar(raiz) {
  raiz.addEventListener('click', (e) => {
    const st = raiz.__st;
    const tp = e.target.closest('[data-tip]');
    // Un clic en la barra de una fila fija la ficha del tramo Y elige la fila.
    if (tp) mostrarTip(raiz, tp, true);
    else if (st.tipFijo) { st.tipFijo = false; raiz.__tip.hidden = true; }
    const s = e.target.closest('button[data-seg]');
    if (s) {
      const x = s.dataset.v, nom = s.dataset.seg;
      if (nom === 'Filas') { st.modo = x; st.estado = null; }
      else if (nom === 'Medir en') st.medida = x;
      else if (nom === 'Ficha') st.tab = x;
      else if (nom === 'Agrupar por') { st.agrupar = x; st.psel = null; st.buscar = ''; st.limite = 80; st.orden = x === 'prov' ? 'falta' : 'fecha'; }
      dibujar(raiz);
      return;
    }
    const k = e.target.closest('button[data-kpi]');
    if (k) { st.estado = !k.dataset.kpi || st.estado === k.dataset.kpi ? null : k.dataset.kpi; dibujar(raiz); return; }
    const me = e.target.closest('button[data-mes]');
    if (me) { enviar(raiz, { destino: 'prov', mes: me.dataset.mes }); return; }
    const ir = e.target.closest('[data-ir]');
    if (ir) { enviar(raiz, JSON.parse(ir.dataset.ir)); return; }
    const o = e.target.closest('button[data-orden]');
    if (o) { st.orden = o.dataset.orden; provCuerpo(raiz); return; }
    const mas = e.target.closest('button[data-mas]');
    if (mas) { st.limite += 80; provCuerpo(raiz); return; }
    const p = e.target.closest('button[data-psel]');
    if (p) { st.psel = p.dataset.psel; provCuerpo(raiz); return; }
    const f = e.target.closest('button[data-sel-fila]');
    if (f) {
      if (st.modo === 'anio') st.selAnio = f.dataset.selFila; else st.sel = f.dataset.selFila;
      dibujar(raiz);
    }
  });
  raiz.addEventListener('mouseover', (e) => {
    const s = e.target.closest && e.target.closest('[data-tip]');
    if (s) mostrarTip(raiz, s, false);
  });
  raiz.addEventListener('mouseout', (e) => {
    const s = e.target.closest && e.target.closest('[data-tip]');
    if (s && !raiz.__st.tipFijo) raiz.__tip.hidden = true;
  });
  // Buscar repinta sólo la lista: rehacer el input le quita el foco (#731).
  raiz.addEventListener('input', (e) => {
    const st = raiz.__st;
    if (e.target.classList.contains('buscar')) { st.buscar = e.target.value; st.limite = 80; provCuerpo(raiz); }
  });
  raiz.addEventListener('change', (e) => {
    const st = raiz.__st;
    if (e.target.classList.contains('pend')) { st.soloPend = e.target.checked; provCuerpo(raiz); return; }
    const c = e.target.dataset && e.target.dataset.sel;
    if (c === 'contra') { st.contra = +e.target.value; dibujar(raiz); }
    else if (c === 'nc') { st.nc = e.target.value; dibujar(raiz); }
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
    raiz.__st = { modo: 'tipo', medida: 'soles', sel: null, selAnio: 'actual', tab: 'quien', estado: null, contra: 1, agrupar: 'prov', buscar: '', soloPend: false,
      orden: 'falta', psel: null, limite: 80, nc: 'incluir', tipFijo: false };
    raiz.__tip = document.createElement('div');
    raiz.__tip.className = 'tip';
    raiz.__tip.hidden = true;
    enlazar(raiz);
  }
  const st = raiz.__st;
  st.data = data || { vista: 'cruce', anios: [], tipos: [], total: { f: { doc: {}, soles: {} } }, mes: {} };
  // Abre en Mercadería: es lo que se carga. El total, a un clic.
  if (st.data.vista === 'cruce' && st.sel === null) st.sel = (st.data.tipos || []).some((t) => t.id === 'Mercadería') ? 'Mercadería' : ((st.data.tipos || [])[0] || {}).id || '__total';
  const ini = st.data.inicial;
  if (ini && ini.t !== st.inicialT) {
    st.inicialT = ini.t;
    st.agrupar = ini.agr || st.agrupar;
    st.psel = ini.k;
    st.orden = st.agrupar === 'prov' ? 'falta' : 'fecha';
    st.buscar = '';
    st.soloPend = false;
    const lista = st.data[st.agrupar] || [], i = lista.findIndex((r) => r.k === ini.k);
    if (i >= st.limite) st.limite = i + 1;
  }
  st.enviar = (x) => setTriggerValue('ir', x);
  dibujar(raiz);
}
