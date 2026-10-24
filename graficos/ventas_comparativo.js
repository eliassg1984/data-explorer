// Ventas › Comparativo, pieza propia (regla #717). `_xlsx.js` va antepuesto.
// Fechas y ventanas: ayudantes originales de Python. Cuentas: las mismas
// de _series_por_rangos, _por_que y _explica_diferencia. Ningún control
// devuelve un trigger: ni el tramo, ni el detalle, ni sus filtros.
const CD = { dia: 0, ped: 1, doc: 2, canal: 3, grupo: 4, venta: 5, neto: 6, pos: 7, neg: 8 };
const CP = { dia: 0, prod: 1, grupo: 2, sub: 3, canal: 4, venta: 5, neto: 6, cant: 7, n: 8 };
const DIA_C = 864e5;
const diaC = s => Date.parse(s + 'T00:00:00Z') / DIA_C;
const isoC = n => new Date(n * DIA_C).toISOString().slice(0, 10);
const fechaC = n => { const s = isoC(n); return `${s.slice(8)}/${s.slice(5, 7)}/${s.slice(0, 4)}`; };
const semanaC = n => (new Date(n * DIA_C).getUTCDay() + 6) % 7;
const pctC = (a, b) => a != null && b != null && Number.isFinite(a) && b > 0 ? (a / b - 1) * 100 : null;
const finC = v => v != null && Number.isFinite(v);
const raroC = s => s === 'Eventos' || s === 'Venta Interna';
const escC = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const formatosC = new Map();
function numeroC(v, dec = 0) {
  if (!finC(v)) return '—';
  if (!formatosC.has(dec)) formatosC.set(dec, new Intl.NumberFormat('en-US', {minimumFractionDigits:dec, maximumFractionDigits:dec}));
  return formatosC.get(dec).format(v);
}
const solesC = (v, dec = 0) => finC(v) ? `${v < 0 ? '−' : ''}S/ ${numeroC(Math.abs(v), dec)}` : '—';
const cambioC = v => !finC(v) ? '—' : `${v > 0 ? '+' : v < 0 ? '−' : ''}${numeroC(Math.abs(v), Math.abs(v) < 10 ? 1 : 0)}%`;
const signoC = v => `${v > 0.5 ? '+' : ''}${solesC(v)}`;
const colorC = v => !finC(v) || Math.abs(v) < .005 ? 'var(--text-secondary)' : v > 0 ? 'var(--success)' : 'var(--danger)';
const compactoC = v => Math.abs(v) >= 1e6 ? `${numeroC(v / 1e6, 1)}M` : Math.abs(v) >= 1000 ? `${numeroC(v / 1000, 0)}k` : numeroC(v);

function leerC(P) {
  const base = diaC(P.base);
  const indexar = rows => {
    const m = new Map();
    rows.forEach(row => { const r = [...row]; r[0] = base + r[0]; if (!m.has(r[0])) m.set(r[0], []); m.get(r[0]).push(r); });
    return m;
  };
  return {P, docs:indexar(P.docs), productos:indexar(P.productos), feriados:new Set(P.feriados.map(diaC)),
    ppto:new Map(P.presupuesto.map(r => [diaC(r[0]), r.slice(1)])),
    planes:Object.fromEntries(Object.entries(P.planes).map(([k, p]) => [k, {...p,
      actual:p.actual.map(r => r.map(diaC)), ap:p.ap.map(r => r.map(diaC))}]))};
}
function filasC(index, rangos, filtro) {
  const days = new Set();
  for (const [a, b] of rangos) for (let f = a; f <= b; f++) days.add(f);
  const out = [];
  for (const f of days) for (const r of index.get(f) || []) if (!filtro || filtro(r)) out.push(r);
  return out;
}
function clientesC(rows, conDoc) {
  const pedidos = new Map();
  for (const r of rows) {
    let p = pedidos.get(r[CD.ped]);
    if (!p) { p = {pos:0, neg:0, dp:new Set(), dn:new Set()}; pedidos.set(r[CD.ped], p); }
    p.pos = Math.max(p.pos, r[CD.pos]); p.neg = Math.min(p.neg, r[CD.neg]);
    if (r[CD.pos] > 0) p.dp.add(r[CD.doc]);
    if (r[CD.neg] < 0) p.dn.add(r[CD.doc]);
  }
  let sum = 0;
  for (const p of pedidos.values()) sum += conDoc ? p.dp.size > p.dn.size ? p.pos : p.dp.size < p.dn.size ? p.neg : 0 : p.pos + p.neg;
  return sum;
}
function totalC(B, rows, st, elegibles) {
  const monto = st.neto ? CD.neto : CD.venta;
  const t = {venta:0, neto:0, cli:B.P.hay_pax ? 0 : null, pax:B.P.hay_pax ? clientesC(rows, B.P.hay_doc) : null, raro:0, canales:{}, dias:{}};
  for (const r of rows) {
    const v = r[monto], canal = B.P.canales[r[CD.canal]];
    t.venta += v; t.neto += r[CD.neto];
    if (B.P.hay_pax && elegibles.has(r[CD.canal])) t.cli += v;
    if (raroC(B.P.grupos[r[CD.grupo]])) t.raro += v;
    t.canales[canal] = (t.canales[canal] || 0) + v;
    t.dias[r[CD.dia]] = (t.dias[r[CD.dia]] || 0) + v;
  }
  return t;
}
function ladoC(B, rangos, ok, st) {
  const filtro = r => !st.excluir || !raroC(B.P.grupos[r[CD.grupo]]);
  const envelope = [[Math.min(...rangos.map(r => r[0])), Math.max(...rangos.map(r => r[1]))]];
  const elegibles = new Set(filasC(B.docs, envelope, filtro).filter(r => r[CD.pos] > 0).map(r => r[CD.canal]));
  // Sin columna de canal el ayudante original con_clientes acepta todo.
  if (!B.P.hay_canal) B.P.canales.forEach((_, i) => elegibles.add(i));
  const barras = rangos.map(r => totalC(B, filasC(B.docs, [r], filtro), st, elegibles));
  const validos = rangos.filter((_, i) => !ok || ok[i]);
  const total = totalC(B, filasC(B.docs, validos, filtro), st, elegibles);
  total.n = validos.length;
  return {barras, total, elegibles};
}
function puenteC(a, p) {
  if (!(a?.pax && p?.pax)) return null;
  const ta = a.cli / a.pax, tp = p.cli / p.pax;
  return {d:a.venta - p.venta, clientes:(a.pax - p.pax) * tp,
    ticket:(ta - tp) * a.pax, sin_clientes:(a.venta - a.cli) - (p.venta - p.cli)};
}
function calendarioC(ra, rp, dias) {
  let v = 0, efecto = 0;
  const na = Array(7).fill(0), np = Array(7).fill(0), vp = Array(7).fill(0);
  for (let d = ra[0]; d <= ra[1]; d++) na[semanaC(d)]++;
  for (let d = rp[0]; d <= rp[1]; d++) { const w = semanaC(d); np[w]++; vp[w] += dias[d] || 0; v += dias[d] || 0; }
  if (v <= 0) return null;
  for (let w = 0; w < 7; w++) if (np[w]) efecto += (na[w] - np[w]) * vp[w] / np[w];
  return efecto / v * 100;
}
function efectosC(v, vp, q, qp) {
  const d = v - vp;
  let cantidad = d, precio = 0;
  if (!(vp <= 0 && v > 0) && !(v <= 0 && vp > 0) && q > 0 && qp > 0) {
    cantidad = (q - qp) * vp / qp; precio = (v / q - vp / qp) * q;
  }
  const que = vp <= 0 && v > 0 ? 'nuevo' : v <= 0 && vp > 0 ? 'ya no se vende' : Math.abs(d) < 1 ? 'igual' :
    Math.abs(precio) > Math.abs(cantidad) ? precio > 0 ? 'más caro' : 'más barato' : cantidad > 0 ? 'vende más' : 'vende menos';
  return {ef_cant:cantidad, ef_precio:precio, que};
}
function detalleC(B, ra, rp, st) {
  const filtro = r => (!st.excluir || !raroC(B.P.grupos[r[CP.grupo]])) &&
    (st.canal == null || r[CP.canal] === st.canal);
  const monto = st.neto ? CP.neto : CP.venta;
  const agg = rangos => {
    const m = new Map(), grupos = new Map(), canales = new Map();
    for (const r of filasC(B.productos, rangos, filtro)) {
      const id = r[CP.prod]; let p = m.get(id);
      if (!p) { p = {id, venta:0, cant:0, grupos:new Map(), subs:new Map()}; m.set(id, p); }
      p.venta += r[monto]; p.cant += r[CP.cant];
      p.grupos.set(r[CP.grupo], (p.grupos.get(r[CP.grupo]) || 0) + r[CP.n]);
      p.subs.set(r[CP.sub], (p.subs.get(r[CP.sub]) || 0) + r[CP.n]);
      grupos.set(r[CP.grupo], (grupos.get(r[CP.grupo]) || 0) + r[monto]);
      canales.set(r[CP.canal], (canales.get(r[CP.canal]) || 0) + r[monto]);
    }
    return {m, grupos, canales};
  };
  const a = agg(ra), p = agg(rp), rows = [];
  const moda = m => [...m].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0]?.[0];
  for (const id of new Set([...a.m.keys(), ...p.m.keys()])) {
    const aa = a.m.get(id), pp = p.m.get(id), jer = aa || pp;
    const venta = aa?.venta || 0, venta_ap = pp?.venta || 0, cant = aa?.cant || 0, cant_ap = pp?.cant || 0;
    rows.push({id, prod:B.P.platos[id], fam:B.P.grupos[moda(jer.grupos)] || '—', sub:B.P.subgrupos[moda(jer.subs)] || '—',
      venta, venta_ap, cant, cant_ap, d:venta - venta_ap, var:pctC(venta, venta_ap),
      precio:venta > 0 && cant > 0 ? venta / cant : 0, precio_ap:venta_ap > 0 && cant_ap > 0 ? venta_ap / cant_ap : 0,
      ...efectosC(venta, venta_ap, cant, cant_ap)});
  }
  rows.sort((a, b) => Math.abs(b.d) - Math.abs(a.d) || b.venta - a.venta || (a.prod < b.prod ? -1 : a.prod > b.prod ? 1 : 0));
  const combinar = k => [...new Set([...a[k].keys(), ...p[k].keys()])].map(id => ({id, venta:a[k].get(id) || 0, venta_ap:p[k].get(id) || 0,
    d:(a[k].get(id) || 0) - (p[k].get(id) || 0)})).sort((a, b) => Math.abs(b.d) - Math.abs(a.d) || a.id - b.id);
  // La jerarquía es la moda ACTUAL del producto (AP sólo si desapareció).
  // Un cambio de grupo no puede partirlo en dos productos ni borrar su AP.
  const gm = new Map();
  for (const r of rows) {
    const id = B.P.grupos.indexOf(r.fam);
    if (!gm.has(id)) gm.set(id, {id, venta:0, venta_ap:0, d:0});
    const g = gm.get(id); g.venta += r.venta; g.venta_ap += r.venta_ap; g.d += r.d;
  }
  return {rows:st.grupo == null ? rows : rows.filter(r => r.fam === B.P.grupos[st.grupo]),
    grupos:[...gm.values()].sort((a,b) => Math.abs(b.d)-Math.abs(a.d) || a.id-b.id), canales:combinar('canales')};
}
function buscarC(rows, texto) {
  const q = (texto || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  return rows.filter(r => !q || `${r.prod} ${r.fam} ${r.sub} ${r.que}`.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().includes(q));
}
function visiblesC(rows, st) {
  let rs = buscarC(rows, st.q);
  if (st.orden) { const {col, dir} = st.orden; rs.sort((a, b) => (typeof a[col] === 'string' ? a[col].localeCompare(b[col], 'es') : (a[col] ?? -Infinity) - (b[col] ?? -Infinity)) * dir); }
  if (st.resto || rs.length <= 16) return rs;
  const rest = rs.slice(15), r = {id:'resto', prod:`Resto · ${rest.length} productos`, fam:'', sub:'', que:'', resto:true};
  for (const k of ['venta','venta_ap','cant','cant_ap','d','ef_cant','ef_precio']) r[k] = rest.reduce((s, a) => s + a[k], 0);
  r.var = pctC(r.venta, r.venta_ap); r.precio = null; r.precio_ap = null;
  return [...rs.slice(0, 15), r];
}
function calcularC(B, st) {
  const clave = JSON.stringify([st.gran, st.ventana, st.modo, st.neto, st.excluir, st.sel]);
  if (B._clave === clave) return {...B._resultado, detalle:st.sel ? detalleC(B, B._resultado.ra, B._resultado.rp, st) : null};
  const plan = B.planes[`${st.gran}|${st.ventana}|${st.gran === 'Día' ? st.modo : 'semana'}`];
  const a = ladoC(B, plan.actual, plan.ok, st), p = ladoC(B, plan.ap, plan.ok, st);
  const dias = Object.assign({}, ...p.barras.map(t => t.dias));
  const cal = plan.actual.map((r, i) => plan.ok[i] ? calendarioC(r, plan.ap[i], dias) : null);
  const selected = st.sel ? plan.actual.map((_, i) => i).filter(i => i >= st.sel[0] && i <= st.sel[1]) : plan.actual.map((_, i) => i);
  const indices = selected.filter(i => plan.ok[i]);
  const ra = indices.map(i => plan.actual[i]), rp = indices.map(i => plan.ap[i]);
  const ta = st.sel && ra.length ? ladoC(B, ra, null, st).total : a.total;
  const tp = st.sel && rp.length ? ladoC(B, rp, null, st).total : p.total;
  const valorAp = indices.reduce((s, i) => s + p.barras[i].venta, 0);
  const calTotal = valorAp > 0 ? indices.reduce((s, i) => s + (cal[i] || 0) * p.barras[i].venta, 0) / valorAp : null;
  const ppto = plan.actual.map(([i, f]) => {
    if (st.excluir) return null;
    let sum = 0, tiene = false;
    for (let d = i; d <= f; d++) if (B.ppto.has(d)) { tiene = true; sum += B.ppto.get(d)[st.neto ? 1 : 0]; }
    return tiene ? sum : null;
  });
  const acum = Object.entries(B.P.acumulados).map(([nombre, ranges]) => {
    const [aa, pp] = ranges.map(r => r.map(diaC));
    const va = ladoC(B, [aa], null, st).total.venta, vp = ladoC(B, [pp], null, st).total.venta;
    return {nombre, actual:va, ap:vp, rango:[aa, pp], var:pctC(va, vp)};
  });
  B._clave = clave;
  B._resultado = {plan, a:a.barras, p:p.barras, ta, tp, indices, ra, rp, cal, calTotal, ppto, acum, puente:puenteC(ta, tp)};
  return {...B._resultado, detalle:st.sel ? detalleC(B, ra, rp, st) : null};
}
window.__vcCalc = {leer:leerC, calcular:calcularC, lado:ladoC, clientes:clientesC, puente:puenteC, efectos:efectosC,
  detalle:detalleC, visibles:visiblesC, calendario:calendarioC};

// ── Interfaz ────────────────────────────────────────────────────────────
const VENTANAS_C = {'Día':[7,14,30], 'Semana':[4,8,13], 'Mes':[3,6,12]};
const DEF_C = {'Día':14,'Semana':8,'Mes':6};
const UNIDAD_C = {'Día':'días','Semana':'semanas','Mes':'meses'};
function inicialC() { return {gran:'Día', ventana:14, modo:'semana', neto:false, vista:'Montos', excluir:false,
  sel:null, grupo:null, canal:null, q:'', resto:false, orden:null, ayuda:false, leyenda:false,
  series:{venta:true,pax:true,ticket:true}, limite:150}; }
const botonC = (a, v, t, on=false, titulo='') => `<button type="button" data-acc="${a}" data-v="${escC(v)}" class="${on?'on':''}" aria-pressed="${on}" title="${escC(titulo)}">${escC(t)}</button>`;
const segmentoC = (a, opciones, valor, rotulo) => `<div class="vcc-seg" role="group" aria-label="${rotulo}">${opciones.map(([v,t])=>botonC(a,v,t,v===valor)).join('')}</div>`;
function rangosTxtC(rs) { return rs.length ? `${fechaC(rs[0][0])} – ${fechaC(rs[rs.length-1][1])}` : 'sin período comparable'; }
function kpiC(rot, val, sub='', color='') { return `<div class="vcc-kpi"><span>${escC(rot)}</span><strong${color?` style="color:${color}"`:''}>${escC(val)}</strong>${sub?`<small>${escC(sub)}</small>`:''}</div>`; }
function lecturaC(V, st) {
  const a=V.ta, p=V.tp, out=[];
  if (V.puente) out.push(`Clientes ${signoC(V.puente.clientes)} · ticket ${signoC(V.puente.ticket)} · canales sin clientes ${signoC(V.puente.sin_clientes)}`);
  if (!st.neto && p.neto > 0 && p.venta > 0 && Math.abs((a.neto/p.neto)/(a.venta/p.venta)-1)>=.005)
    out.push(`Sin IGV ni recargo: ${cambioC(pctC(a.neto,p.neto))}`);
  if (Math.abs(V.calTotal || 0)>=.5) out.push(`Calendario: ${cambioC(V.calTotal)}`);
  if (!st.excluir && (Math.abs(a.raro)>=1 || Math.abs(p.raro)>=1) && p.venta-p.raro>0)
    out.push(`Sin Eventos ni Venta interna: ${cambioC(pctC(a.venta-a.raro,p.venta-p.raro))}`);
  for (const c of new Set([...Object.keys(a.canales),...Object.keys(p.canales)])) {
    const va=a.canales[c]||0, vp=p.canales[c]||0;
    if ((va>=1)!==(vp>=1)) out.push(`${c}: sólo ${va>=1?'actual':'año pasado'} (${solesC(Math.max(va,vp))})`);
  }
  return out.map(t=>`<span>${escC(t)}</span>`).join('');
}
function presupuestoC(V, st) {
  if (st.vista!=='Montos') return '';
  const ids=V.indices.filter(i=>V.ppto[i]!=null);
  if (!ids.length) return '';
  const p=ids.reduce((s,i)=>s+V.ppto[i],0), a=ids.reduce((s,i)=>s+V.a[i].venta,0);
  return `<span title="${escC(`Venta ${solesC(a,2)} / presupuesto ${solesC(p,2)}. Sólo ${ids.length} períodos con presupuesto.`)}">Presupuesto: <b>${p>0?numeroC(a/p*100,1)+'%':'—'}</b> · ${ids.length}/${V.indices.length} períodos</span>`;
}
function renderC(G) {
  if (!G.root?.isConnected) return;
  const root=G.root, B=G.B, st=G.st, V=calcularC(B,st); G.V=V;
  const hayDesc=B.P.hay_pax&&V.a.some(a=>a.pax>0)&&V.p.some(p=>p.pax>0);
  if(!hayDesc)st.vista='Montos';
  const focus=root.shadowRoot?.activeElement || root.getRootNode().activeElement;
  const buscando=focus?.matches?.('[data-acc="buscar"]'), cursor=buscando?focus.selectionStart:0;
  const comparable=V.indices.length>0, a=V.ta, p=V.tp, cambio=comparable?pctC(a.venta,p.venta):null;
  const paxPct=pctC(a.pax,p.pax), ticket=a.pax?a.cli/a.pax:null, ticketP=p.pax?p.cli/p.pax:null;
  root.innerHTML=`<section class="vcc-card vcc-main" aria-label="Comparativo de ventas">
    <header class="vcc-head"><h3>Comparativo de ventas</h3><span class="vcc-muted">Hasta ${fechaC(diaC(B.P.ancla))}</span><div class="vcc-push"></div>${botonC('ayuda','', 'Cómo comparar',st.ayuda)}${botonC('excel','','↓ Excel')}</header>
    <div class="vcc-controls">
      ${segmentoC('gran',['Día','Semana','Mes'].map(v=>[v,v]),st.gran,'Granularidad')}
      ${segmentoC('ventana',VENTANAS_C[st.gran].map(v=>[v,`${v} ${UNIDAD_C[st.gran]}`]),st.ventana,'Ventana')}
      ${st.gran==='Día'?segmentoC('modo',[['semana','Mismo día de semana'],['calendario','Misma fecha']],st.modo,'Alineación'):''}
      <div class="vcc-push"></div>${B.P.hay_neto?segmentoC('neto',[[false,'Venta'],[true,'Neto']],st.neto,'Monto'):''}
      ${hayDesc?segmentoC('vista',[['Montos','Montos'],['Descomposición','Descomposición']],st.vista,'Vista'):''}
    </div>
    <div class="vcc-context"><label><input type="checkbox" data-acc="excluir" ${st.excluir?'checked':''}> Excluir Eventos y Venta interna</label>
      <span>${st.sel?'Tramo elegido':'Ventana completa'} · ${V.indices.length}/${V.plan.actual.length} períodos comparables</span>${st.sel?botonC('soltar','','Ver ventana completa'):''}
      <div class="vcc-push"></div>${st.vista==='Montos'?'<span class="vcc-key vcc-ap">Año pasado</span><span class="vcc-key vcc-actual">Actual</span>':
        ['venta','pax','ticket'].map(k=>`<label class="vcc-key vcc-${k}"><input type="checkbox" data-acc="serie" data-v="${k}" ${st.series[k]?'checked':''}>${{venta:'Venta',pax:'Clientes',ticket:'Ticket'}[k]}</label>`).join('')}
    </div>
    <div class="vcc-kpis">${kpiC('Actual',solesC(comparable?a.venta:null),st.sel?rangosTxtC(V.ra):'Períodos comparables','var(--accent-deep)')}
      ${kpiC('Año pasado',solesC(comparable?p.venta:null),st.sel?rangosTxtC(V.rp):'Mismos tramos')}
      ${kpiC('Diferencia',solesC(comparable?a.venta-p.venta:null),cambioC(cambio),colorC(cambio))}
      ${B.P.hay_pax?kpiC('Clientes',numeroC(comparable?a.pax:null),cambioC(paxPct))+kpiC('Ticket',solesC(comparable?ticket:null,2),cambioC(pctC(ticket,ticketP))):''}</div>
    <div class="vcc-reading">${lecturaC(V,st)}</div>
    <div class="vcc-plot" aria-label="Actual y año pasado por período"></div>
    <div class="vcc-bottom"><span class="vcc-muted">Clic: un período · arrastrar: un tramo${V.plan.parciales.length?' · «en curso»: mismos días del período anterior':''}</span>
      <div class="vcc-push"></div>${botonC('detalle','','Qué explica la diferencia ↓')}</div>
    <div class="vcc-extra">${presupuestoC(V,st)}${V.acum.map(x=>`<span title="${escC(`${rangosTxtC([x.rango[0]])} contra ${rangosTxtC([x.rango[1]])} · ${solesC(x.actual,2)} / ${solesC(x.ap,2)}`)}">${x.nombre}: <b style="color:${colorC(x.var)}">${cambioC(x.var)}</b></span>`).join('')}</div>
    ${!V.plan.ok.every(Boolean)?`<div class="vcc-notice">Sin histórico equivalente: ${escC(V.plan.sin_dato)}. Fuera de ambos totales; no se considera una venta de cero.</div>`:''}
    ${st.ayuda?`<div class="vcc-help"><b>Comparación justa</b><p>${st.gran==='Día'&&st.modo==='calendario'?'Misma fecha del calendario; el día de semana puede cambiar.':st.gran==='Mes'?'Mismo mes del año anterior. «cal.» estima el efecto de tener más o menos días de cada día de semana.':'Mismos días de semana, 364 días antes (52 semanas).'} El período en curso se compara con la misma cantidad de días. El ticket usa la venta de los canales que registran clientes. Las notas de crédito restan y las cuentas divididas cuentan una mesa.</p><p>La cascada reparte la diferencia en clientes, ticket y canales sin clientes. Calendario es una referencia aparte; no se vuelve a restar de la cascada. Las bandas grises son fines de semana y las ámbar, feriados de Perú.</p></div>`:''}
  </section>${st.sel?detalleHtmlC(G):''}`;
  graficoC(G);
  if (st.sel&&V.indices.length) { puenteSvgC(G); tablaC(G); }
  else {G.rows=[];G.tableCols=[];}
  if (buscando) { const input=root.querySelector('[data-acc="buscar"]'); input?.focus({preventScroll:true}); input?.setSelectionRange(cursor,cursor); }
}
function graficoC(G) {
  const {B,st,V,root}=G, plot=root.querySelector('.vcc-plot');
  const w=Math.max(280,plot.clientWidth), h=Math.max(150,plot.clientHeight), l=45,r=10,t=43,b=43, pw=w-l-r, ph=h-t-b, n=V.a.length, step=pw/n;
  const desc=st.vista==='Descomposición';
  const series=V.a.map((a,i)=>({venta:V.plan.ok[i]?pctC(a.venta,V.p[i].venta):null, pax:V.plan.ok[i]?pctC(a.pax,V.p[i].pax):null,
    ticket:V.plan.ok[i]?pctC(a.pax?a.cli/a.pax:null,V.p[i].pax?V.p[i].cli/V.p[i].pax:null):null}));
  const vals=desc?series.flatMap(s=>Object.keys(s).filter(k=>st.series[k]).map(k=>s[k]).filter(finC)):
    [...V.a.map(a=>a.venta),...V.p.filter((_,i)=>V.plan.ok[i]).map(a=>a.venta),...V.ppto.filter(finC)];
  let max=Math.max(0,...vals), min=Math.min(0,...vals); if(max===min) max=min+1;
  const span=max-min; max+=span*.08; if(min<0) min-=span*.08;
  const y=v=>t+(max-v)/(max-min)*ph, x=i=>l+(i+.5)*step, zero=y(0);
  G.geom={l,step,n,w,plot};
  let svg=`<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${desc?'Variación de venta, clientes y ticket':'Venta actual frente al año pasado'}"><defs><pattern id="vcc-parcial" width="6" height="6" patternUnits="userSpaceOnUse"><path d="M-1 1L1-1M0 6L6 0M5 7L7 5" stroke="var(--accent-deep)" stroke-opacity=".35"/></pattern></defs>`;
  for(let i=0;i<4;i++){const v=min+(max-min)*i/3, yy=y(v);svg+=`<line x1="${l}" x2="${w-r}" y1="${yy}" y2="${yy}" class="vcc-grid"/><text x="${l-6}" y="${yy+3}" text-anchor="end" class="vcc-axis">${desc?numeroC(v)+'%':compactoC(v)}</text>`;}
  svg+=`<line x1="${l}" x2="${w-r}" y1="${zero}" y2="${zero}" class="vcc-zero"/>`;
  const ancho=Math.min(32,step*.29), labels=n<=14&&step>=48, pasoTick=Math.max(1,Math.ceil(55/step));
  for(let i=0;i<n;i++){
    const xx=x(i), [da]=V.plan.actual[i], selected=!st.sel||i>=st.sel[0]&&i<=st.sel[1], parcial=V.plan.parciales.includes(i), ferA=contarFerC(B,V.plan.actual[i]),ferP=contarFerC(B,V.plan.ap[i]);
    if(st.gran==='Día' && (semanaC(da)>=5||ferA)) svg+=`<rect x="${xx-step/2}" y="${t-8}" width="${step}" height="${ph+8}" fill="${ferA?'var(--warning)':'var(--text-secondary)'}" fill-opacity=".075"/>`;
    svg+=`<g opacity="${selected?1:.28}">`;
    if(desc){const v=series[i].venta;if(st.series.venta&&finC(v))svg+=rectC(xx-ancho/2,y(Math.max(0,v)),ancho,Math.abs(y(v)-zero),colorC(v));}
    else {
      if(V.plan.ok[i])svg+=rectC(xx-ancho-1,y(Math.max(0,V.p[i].venta)),ancho,Math.abs(y(V.p[i].venta)-zero),'var(--border-lavender)');
      svg+=rectC(xx+1,y(Math.max(0,V.a[i].venta)),ancho,Math.abs(y(V.a[i].venta)-zero),'var(--accent)');
      if(parcial)svg+=rectC(xx+1,y(Math.max(0,V.a[i].venta)),ancho,Math.abs(y(V.a[i].venta)-zero),'url(#vcc-parcial)');
      if(labels) svg+=`<text x="${xx}" y="${Math.min(y(V.a[i].venta),y(V.plan.ok[i]?V.p[i].venta:0))-17}" text-anchor="middle" class="vcc-value">${compactoC(V.a[i].venta)}</text>`;
    }
    if(labels&&(!desc||st.series.venta)&&finC(series[i].venta)) svg+=`<text x="${xx}" y="${desc?Math.max(13,y(Math.max(0,series[i].venta))-9):Math.min(y(V.a[i].venta),y(V.p[i].venta))-4}" text-anchor="middle" style="fill:${colorC(series[i].venta)}" class="vcc-value">${cambioC(series[i].venta)}</text>`;
    if(!V.plan.ok[i])svg+=`<text x="${xx}" y="${t-21}" text-anchor="middle" class="vcc-axis">sin AP</text>`;
    if(step>=45&&st.gran!=='Día'&&ferA!==ferP)svg+=`<text x="${xx}" y="${h-4}" text-anchor="middle" class="vcc-warning">${ferA>ferP?'+':''}${ferA-ferP} fer.</text>`;
    else if(step>=45&&st.gran==='Día'&&(ferA||ferP))svg+=`<text x="${xx}" y="${h-4}" text-anchor="middle" class="vcc-warning">${ferA?'feriado':'feriado AP'}</text>`;
    if(i===n-1||(i%pasoTick===0&&(i===0||(n-1-i)*step>=50)))svg+=`<text x="${xx}" y="${h-26}" text-anchor="middle" class="vcc-axis">${escC(V.plan.etiquetas[i])}</text>`;
    if(parcial)svg+=`<text x="${xx}" y="${h-14}" text-anchor="middle" class="vcc-axis">en curso</text>`;
    if(step>=55&&!desc&&Math.abs(V.cal[i]||0)>=.5)svg+=`<text x="${xx}" y="${t-31}" text-anchor="middle" class="vcc-axis">cal. ${cambioC(V.cal[i])}</text>`;
    svg+='</g>';
  }
  if(desc) for(const [k,c] of [['pax','var(--serie-2)'],['ticket','var(--serie-5)']]) if(st.series[k]){
    let path=''; for(let i=0;i<n;i++){const v=series[i][k]; if(!finC(v)){path='';continue;} const xx=x(i),yy=y(v); if(path)svg+=`<line x1="${path[0]}" y1="${path[1]}" x2="${xx}" y2="${yy}" stroke="${c}" stroke-width="2"/>`;svg+=`<circle cx="${xx}" cy="${yy}" r="3" fill="${c}"/>`;path=[xx,yy];}
  }
  if(!desc) for(let i=0;i<n;i++) if(V.ppto[i]!=null)svg+=`<line x1="${x(i)-step*.4}" x2="${x(i)+step*.4}" y1="${y(V.ppto[i])}" y2="${y(V.ppto[i])}" stroke="var(--text-primary)" stroke-width="2" stroke-dasharray="4 3"/>`;
  for(let i=0;i<n;i++)svg+=`<rect class="vcc-hit${st.sel&&i>=st.sel[0]&&i<=st.sel[1]?' chosen':''}" data-bar="${i}" role="button" tabindex="0" aria-label="${escC(V.plan.etiquetas[i])}, actual ${solesC(V.a[i].venta,2)}, año pasado ${V.plan.ok[i]?solesC(V.p[i].venta,2):'sin dato'}" x="${l+i*step}" y="0" width="${step}" height="${h}"/>`;
  plot.innerHTML=svg+'</svg><div class="vcc-tip" hidden></div>';
  if(desc){
    const last=n-1,a=V.a[last],p=V.p[last];
    const values={venta:[a.venta,p.venta,'Venta'],pax:[a.pax,p.pax,'Clientes'],ticket:[a.pax?a.cli/a.pax:null,p.pax?p.cli/p.pax:null,'Ticket promedio']};
    plot.insertAdjacentHTML('beforeend',`<div class="vcc-last">${botonC('leyenda','',`Detalle · ${V.plan.etiquetas[last]}`,st.leyenda)}${st.leyenda?`<div class="vcc-last-panel">${Object.entries(values).map(([k,[va,vp,nombre]])=>`<label><input type="checkbox" data-acc="serie" data-v="${k}" ${st.series[k]?'checked':''}><span>${nombre}</span><b>${k==='pax'?numeroC(va):solesC(va,k==='ticket'?2:0)}</b><small style="color:${colorC(pctC(va,vp))}">${cambioC(pctC(va,vp))}</small></label>`).join('')}</div>`:''}</div>`);
  }
}
const rectC=(x,y,w,h,c)=>`<rect x="${x}" y="${y}" width="${w}" height="${Math.max(.5,h)}" rx="2" fill="${c}"/>`;
function contarFerC(B,[a,b]){let n=0;for(let d=a;d<=b;d++)if(B.feriados.has(d))n++;return n;}
function tipC(G,i){
  const plot=G.root.querySelector('.vcc-plot'), tip=plot.querySelector('.vcc-tip');
  if(i==null){tip.hidden=true;return;}
  const {V,st}=G,a=V.a[i],p=V.p[i], ok=V.plan.ok[i];
  tip.innerHTML=`<b>${escC(V.plan.etiquetas[i])}${V.plan.parciales.includes(i)?' · en curso':''}</b><div>Actual · ${rangosTxtC([V.plan.actual[i]])}<strong>${solesC(a.venta,2)}</strong></div>
    <div>Año pasado · ${rangosTxtC([V.plan.ap[i]])}<strong>${ok?solesC(p.venta,2):'sin datos comparables'}</strong></div>
    ${ok?`<div>Diferencia <strong style="color:${colorC(a.venta-p.venta)}">${signoC(a.venta-p.venta)} · ${cambioC(pctC(a.venta,p.venta))}</strong></div>`:''}
    ${G.B.P.hay_pax?`<div>Clientes ${numeroC(a.pax)} / ${ok?numeroC(p.pax):'—'} · ticket ${solesC(a.pax?a.cli/a.pax:null,2)} / ${ok?solesC(p.pax?p.cli/p.pax:null,2):'—'}</div>`:''}
    ${V.ppto[i]!=null&&st.vista==='Montos'?`<div>Presupuesto ${solesC(V.ppto[i],2)}</div>`:''}${Math.abs(V.cal[i]||0)>=.5?`<div>Referencia de calendario: ${cambioC(V.cal[i])}</div>`:''}
    ${contarFerC(G.B,V.plan.actual[i])||contarFerC(G.B,V.plan.ap[i])?`<div>Feriados: ${contarFerC(G.B,V.plan.actual[i])} actual / ${contarFerC(G.B,V.plan.ap[i])} año pasado</div>`:''}`;
  tip.style.left=`${Math.max(0,Math.min(plot.clientWidth-285,G.geom.l+(i+.5)*G.geom.step-140))}px`;tip.hidden=false;
}
function detalleHtmlC(G){
  const {B,st,V}=G;
  if(!V.indices.length){
    const actual=V.a.filter((_,i)=>i>=st.sel[0]&&i<=st.sel[1]).reduce((s,a)=>s+a.venta,0);
    return `<section class="vcc-card" aria-label="Sin histórico comparable"><header class="vcc-head"><h3>Sin histórico comparable</h3><div class="vcc-push"></div>${botonC('soltar','','Cerrar ×')}</header><p>La venta actual de este tramo es ${solesC(actual,2)}. No hay histórico equivalente para calcular su diferencia; no se considera una venta de cero.</p></section>`;
  }
  const overview=detalleC(B,V.ra,V.rp,{...st,grupo:null,canal:null});
  const barras=(titulo,key,rows,names)=>`<div class="vcc-break"><b>${titulo} · Δ S/</b>${rows.slice(0,5).map(r=>`<button type="button" data-acc="${key}" data-v="${r.id}" class="${st[key]===r.id?'on':''}" title="${escC(`${names[r.id]} · actual ${solesC(r.venta,2)} / AP ${solesC(r.venta_ap,2)}`)}"><span>${escC(names[r.id]||'Sin grupo')}</span><strong style="color:${colorC(r.d)}">${signoC(r.d)}</strong></button>`).join('')}</div>`;
  return `<section class="vcc-card vcc-detail" aria-label="Qué explica la diferencia"><header class="vcc-head"><h3>Qué explica la diferencia</h3><span>${rangosTxtC(V.ra)}</span><div class="vcc-push"></div>${botonC('soltar','','Cerrar ×')}</header>
    <div class="vcc-detail-context">Año pasado ${rangosTxtC(V.rp)} · ${solesC(V.tp.venta)} → ${solesC(V.ta.venta)} · <b style="color:${colorC(V.ta.venta-V.tp.venta)}">${signoC(V.ta.venta-V.tp.venta)}</b></div>
    <div class="vcc-analysis"><div class="vcc-bridge"><b>De año pasado a actual</b><div class="vcc-bridge-plot"></div></div>${barras('Por grupo','grupo',overview.grupos,B.P.grupos)}${barras('Por canal','canal',overview.canales,B.P.canales)}</div>
    <div class="vcc-search"><input type="search" data-acc="buscar" aria-label="Buscar platos" placeholder="Buscar plato, grupo o qué cambió…" value="${escC(st.q)}">
      ${st.grupo!=null?botonC('grupo',st.grupo,`${B.P.grupos[st.grupo]} ×`,true):''}${st.canal!=null?botonC('canal',st.canal,`${B.P.canales[st.canal]} ×`,true):''}
      ${st.resto?botonC('resto','','Sólo principales'):''}<div class="vcc-push"></div>${botonC('excel','','↓ Excel')}</div>
    <div class="vcc-table-scroll" tabindex="0" aria-label="Productos que explican la diferencia"></div><div class="vcc-table-foot"></div></section>`;
}
const COLS_C=[['fam','Grupo'],['prod','Producto'],['que','Qué cambió'],['d','Δ S/'],['var','%Var'],['ef_cant','Por cantidad'],['ef_precio','Por precio'],['venta_ap','Venta AP'],['venta','Venta actual'],['cant_ap','Cant AP'],['cant','Cant actual'],['precio_ap','Precio AP'],['precio','Precio actual']];
const AYUDA_C={que:'Lo que más pesó: unidades o precio promedio.',ef_cant:'Unidades de más o de menos al precio del año pasado.',ef_precio:'Cambio de precio promedio sobre las unidades actuales. Por cantidad + por precio = Δ S/.'};
function valorCeldaC(r,k){
  if(k==='var')return r.venta_ap<=0&&r.venta>0?'nuevo':r.venta_ap<=0?'—':cambioC(r.var);
  if(k==='cant'||k==='cant_ap')return numeroC(r[k],2);
  if(k==='precio'||k==='precio_ap')return r[k]?solesC(r[k],2):'—';
  if(['d','ef_cant','ef_precio'].includes(k))return signoC(r[k]);
  if(k==='venta'||k==='venta_ap')return solesC(r[k]);
  return r[k]||'';
}
function tablaC(G){
  const rs=visiblesC(G.V.detalle.rows,G.st); G.rows=rs;
  const wrap=G.root.querySelector('.vcc-table-scroll'), old=wrap.scrollTop;
  wrap.innerHTML=`<table><thead><tr>${COLS_C.filter(([k])=>G.B.P.hay_cant||!['cant','cant_ap','precio','precio_ap','ef_cant','ef_precio','que'].includes(k)).map(([k,t])=>`<th><button type="button" data-acc="orden" data-v="${k}" title="${escC(AYUDA_C[k]||`Ordenar por ${t}`)}">${t}${G.st.orden?.col===k?(G.st.orden.dir>0?' ↑':' ↓'):''}</button></th>`).join('')}</tr></thead><tbody></tbody></table>`;
  G.tableCols=COLS_C.filter(([k])=>G.B.P.hay_cant||!['cant','cant_ap','precio','precio_ap','ef_cant','ef_precio','que'].includes(k));
  G.tableN=0; agregarFilasC(G);
  wrap.scrollTop=old;
  wrap.addEventListener('scroll',()=>{if(wrap.scrollTop+wrap.clientHeight>=wrap.scrollHeight-100)agregarFilasC(G);},{passive:true});
  const total=rs.reduce((s,r)=>s+r.d,0);
  const cuantos=buscarC(G.V.detalle.rows,G.st.q).length;
  G.root.querySelector('.vcc-table-foot').innerHTML=`<span>${cuantos} producto${cuantos===1?'':'s'}${G.st.q?' · búsqueda aplicada':''}${G.st.grupo!=null||G.st.canal!=null?' · tabla filtrada':''} · Δ de las filas: <b style="color:${colorC(total)}">${signoC(total)}</b></span><span>${G.st.resto?'Todos los resultados':G.st.orden?'Orden elegido; «Resto» abre los demás':'Principales por |Δ S/|; «Resto» abre los demás'}</span>`;
}
function agregarFilasC(G){
  const tbody=G.root.querySelector('.vcc-table-scroll tbody');if(!tbody)return;
  const end=Math.min(G.rows.length,G.tableN+150);
  tbody.insertAdjacentHTML('beforeend',G.rows.slice(G.tableN,end).map(r=>`<tr class="${r.resto?'vcc-rest':''}">${G.tableCols.map(([k])=>`<td class="${typeof r[k]==='number'||['var','precio','precio_ap'].includes(k)?'vcc-num':''}"${['d','var','ef_cant','ef_precio'].includes(k)?` style="color:${colorC(r[k])}"`:''}>${k==='prod'&&r.resto?botonC('resto','',r.prod):escC(valorCeldaC(r,k))}</td>`).join('')}</tr>`).join(''));
  G.tableN=end;
}
function puenteSvgC(G){
  const plot=G.root.querySelector('.vcc-bridge-plot'), {V}=G;
  if(!V.puente){plot.innerHTML='<p class="vcc-muted">Sin clientes comparables: no se puede descomponer en clientes y ticket.</p>';return;}
  const w=Math.max(250,plot.clientWidth), h=122, left=8,top=25,bottom=29;
  const steps=[['Año pasado',V.tp.venta,true],['Clientes',V.puente.clientes,false],['Ticket',V.puente.ticket,false],['Sin clientes',V.puente.sin_clientes,false],['Actual',V.ta.venta,true]];
  let acc=0;const bars=steps.map(([name,v,total])=>{const a=total?0:acc,b=total?v:acc+v;acc=b;return {name,v,a,b,total};});
  let lo=Math.min(0,...bars.flatMap(b=>[b.a,b.b])),hi=Math.max(1,...bars.flatMap(b=>[b.a,b.b]));
  const y=v=>top+(hi-v)/(hi-lo)*(h-top-bottom), step=(w-left*2)/5,bw=step*.64;
  plot.innerHTML=`<svg width="${w}" height="${h}" role="img" aria-label="Cascada de año pasado a actual">${bars.map((b,i)=>{
    const x=left+(i+.5)*step,c=b.total?'var(--accent)':colorC(b.v);
    return `${i&&i<4?`<line x1="${x-step+bw/2}" x2="${x-bw/2}" y1="${y(b.a)}" y2="${y(b.a)}" class="vcc-grid"/>`:''}${rectC(x-bw/2,y(Math.max(b.a,b.b)),bw,Math.abs(y(b.a)-y(b.b)),c)}<text x="${x}" y="${y(Math.max(b.a,b.b))-6}" text-anchor="middle" class="vcc-value">${b.total?'':b.v>0?'+':''}${compactoC(b.v)}</text><text x="${x}" y="${h-11}" text-anchor="middle" class="vcc-axis">${b.name}</text>`;
  }).join('')}</svg>`;
}
function excelC(G){
  const {B,st,V}=G, ids=st.sel?V.plan.actual.map((_,i)=>i).filter(i=>i>=st.sel[0]&&i<=st.sel[1]):V.plan.actual.map((_,i)=>i);
  const head=['Período','Desde actual','Hasta actual','Desde AP','Hasta AP','Comparable','En curso','Venta AP','Venta actual','Δ S/','%Var','Clientes AP','Clientes actual','Ticket AP','Ticket actual','Presupuesto','Calendario %'];
  const data=ids.map(i=>{const a=V.a[i],p=V.p[i],ok=V.plan.ok[i];return [V.plan.etiquetas[i],...V.plan.actual[i].map(isoC),...V.plan.ap[i].map(isoC),ok?'Sí':'Sin histórico',V.plan.parciales.includes(i)?'Sí':'No',ok?p.venta:null,a.venta,ok?a.venta-p.venta:null,ok?pctC(a.venta,p.venta):null,ok?p.pax:null,a.pax,ok&&p.pax?p.cli/p.pax:null,a.pax?a.cli/a.pax:null,V.ppto[i],V.cal[i]];});
  const hojas=[{nombre:'Comparativo',cabeza:head,filas:data}];
  if(st.sel&&V.indices.length)hojas.push({nombre:'Productos',cabeza:G.tableCols.map(c=>c[1]),filas:G.rows.map(r=>G.tableCols.map(([k])=>k==='var'&&r.venta_ap<=0?r.venta>0?'nuevo':null:['precio','precio_ap'].includes(k)&&!r[k]?null:r[k]??null))});
  const contexto=[['Hasta',B.P.ancla],['Granularidad',st.gran],['Ventana',st.ventana],['Alineación',st.gran==='Mes'?'Mismo mes':st.modo==='calendario'?'Misma fecha':'364 días antes'],['Monto',st.neto?'Neto sin IGV ni recargo':'Venta'],['Vista',st.vista],['Excluir Eventos y Venta interna',st.excluir?'Sí':'No'],['Rango actual',rangosTxtC(V.ra)],['Rango AP',rangosTxtC(V.rp)],['Grupo de la tabla',st.grupo==null?'Todos':B.P.grupos[st.grupo]],['Canal de la tabla',st.canal==null?'Todos':B.P.canales[st.canal]],['Buscar',st.q],...Object.entries(B.P.filtros).map(([k,v])=>[k,Array.isArray(v)?v.join(', '):String(v)])];
  hojas.push({nombre:'Contexto',cabeza:['Ajuste','Valor'],filas:contexto});
  bajar(archivo(`Comparativo_${B.P.ancla}_${st.gran}`)+'.xlsx',libro(hojas));
}
function elegirC(G,a,b){
  const lo=Math.min(a,b),hi=Math.max(a,b), prev=G.st.sel;
  G.st.sel=a===b&&prev&&prev[0]===lo&&prev[1]===hi?null:[lo,hi];
  G.st.grupo=null;G.st.canal=null;G.st.q='';G.st.resto=false;G.st.orden=null;
  renderC(G);
}
function enlazarC(G){
  const root=G.root;
  root.addEventListener('click',ev=>{
    const el=ev.target.closest('[data-acc]');if(!el||el.tagName==='INPUT')return;
    const a=el.dataset.acc,v=el.dataset.v,st=G.st;
    if(a==='gran'){st.gran=v;st.ventana=DEF_C[v];st.sel=null;}
    else if(a==='ventana'){st.ventana=+v;st.sel=null;}
    else if(a==='modo'){st.modo=v;st.sel=null;}
    else if(a==='neto')st.neto=v==='true';
    else if(a==='vista')st.vista=v;
    else if(a==='soltar'){st.sel=null;st.grupo=null;st.canal=null;}
    else if(a==='grupo'||a==='canal'){st[a]=st[a]===+v?null:+v;st.resto=false;}
    else if(a==='orden'){const prev=st.orden,dir=['fam','prod','que'].includes(v)?1:-1;st.orden=!prev||prev.col!==v?{col:v,dir}:prev.dir===dir?{col:v,dir:-dir}:null;}
    else if(a==='resto')st.resto=!st.resto;
    else if(a==='ayuda')st.ayuda=!st.ayuda;
    else if(a==='leyenda')st.leyenda=!st.leyenda;
    else if(a==='detalle'){if(!st.sel)st.sel=[0,G.V.a.length-1];renderC(G);root.querySelector('.vcc-detail')?.scrollIntoView({block:'start',behavior:'smooth'});return;}
    else if(a==='excel'){excelC(G);return;}
    else return;
    renderC(G);
  });
  root.addEventListener('change',ev=>{
    const e=ev.target;if(e.dataset.acc==='excluir'){G.st.excluir=e.checked;G.st.grupo=null;G.st.canal=null;renderC(G);}
    else if(e.dataset.acc==='serie'){G.st.series[e.dataset.v]=e.checked;renderC(G);}
  });
  root.addEventListener('input',ev=>{if(ev.target.dataset.acc==='buscar'){G.st.q=ev.target.value;renderC(G);}});
  root.addEventListener('pointerover',ev=>{const b=ev.target.closest('[data-bar]');if(b)tipC(G,+b.dataset.bar);});
  root.addEventListener('pointerout',ev=>{if(ev.target.closest('[data-bar]')&&!ev.relatedTarget?.closest?.('[data-bar]'))tipC(G,null);});
  root.addEventListener('keydown',ev=>{const b=ev.target.closest('[data-bar]');if(b&&(ev.key==='Enter'||ev.key===' ')){ev.preventDefault();elegirC(G,+b.dataset.bar,+b.dataset.bar);}if(ev.key==='Escape'&&G.st.ayuda){G.st.ayuda=false;renderC(G);}});
  root.addEventListener('pointerdown',ev=>{const b=ev.target.closest('[data-bar]');if(b&&ev.button===0){G.drag={a:+b.dataset.bar,b:+b.dataset.bar};ev.preventDefault();}});
  G.abort?.abort();G.abort=new AbortController();
  window.addEventListener('pointermove',ev=>{
    if(!G.drag||!G.root.isConnected)return;
    const g=G.geom, rect=g.plot.getBoundingClientRect(),i=Math.max(0,Math.min(g.n-1,Math.floor((ev.clientX-rect.left-g.l)/g.step)));
    G.drag.b=i;G.root.querySelectorAll('[data-bar]').forEach(b=>b.classList.toggle('chosen',+b.dataset.bar>=Math.min(G.drag.a,i)&&+b.dataset.bar<=Math.max(G.drag.a,i)));
    tipC(G,i);
  },{signal:G.abort.signal});
  window.addEventListener('pointerup',()=>{if(G.drag){const d=G.drag;G.drag=null;elegirC(G,d.a,d.b);}},{signal:G.abort.signal});
  window.addEventListener('pointercancel',()=>{G.drag=null;},{signal:G.abort.signal});
  G.observer?.disconnect();let width=0,height=0;
  G.observer=new ResizeObserver(()=>{if(!G.root.isConnected)return;const w=root.clientWidth,h=root.querySelector('.vcc-plot')?.clientHeight||0;if(Math.abs(w-width)>2||Math.abs(h-height)>2){width=w;height=h;if(G.B){graficoC(G);if(G.st.sel&&G.V.indices.length)puenteSvgC(G);}}});
  G.observer.observe(root);
}
window.__vcUI={inicial:inicialC,render:renderC,excel:excelC};
export default function(component){
  const {data,parentElement}=component;if(!data||data.parte!=='comparativo')return;
  const G=window.__vtComparativo||(window.__vtComparativo={st:inicialC()});
  let root=parentElement.querySelector('.vcc'),nuevo=!root;
  if(nuevo){root=document.createElement('div');root.className='vcc';parentElement.appendChild(root);G.root=root;enlazarC(G);}else G.root=root;
  if(G.sello!==data.sello){G.B=leerC(data);G.sello=data.sello;G.st.sel=null;G.st.grupo=null;G.st.canal=null;G.st.q='';G.st.resto=false;G.st.orden=null;}
  else if(!nuevo)return;
  if(!data.hay_neto)G.st.neto=false;
  root.style.setProperty('--vcc-fig',`${data.alto_fig||276}px`);
  renderC(G);
}
