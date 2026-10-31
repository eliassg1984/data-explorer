// Ventas › Comparativo, pieza propia (reglas #717 y #768). `_xlsx.js` y
// `ventas_sin_fecha.js` van antepuestos.
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
  detalle:detalleC, visibles:visiblesC, calendario:calendarioC, clase:r=>claseC(r), porSemana:V=>porSemanaC(V)};

// ── Interfaz (regla #768) ───────────────────────────────────────────────
// Una fila de controles, cuatro indicadores y UNA zona por pestaña, con «Por qué»
// siempre al costado: lo que explica la diferencia ya no espera a un botón.
const VENTANAS_C = {'Día':[7,14,30], 'Semana':[4,8,13], 'Mes':[3,6,12]};
const DEF_C = {'Día':14,'Semana':8,'Mes':6};
const UNIDAD_C = {'Día':'días','Semana':'semanas','Mes':'meses'};
const TABS_C = [['Montos','Montos'],['Variacion','Variación %'],['Acumulado','Acumulado'],['Semana','Día de semana'],['Platos','Platos']];
const DIAS_C = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'];
function inicialC() { return {gran:'Día', ventana:14, modo:'semana', neto:false, excluir:false, tab:'Montos', med:'venta', cifras:'Clave', clase:'todos', ampl:false, menu:null,
  sel:null, grupo:null, canal:null, q:'', resto:false, orden:null, ayuda:false,
  series:{venta:true,pax:true,ticket:true}, limite:150}; }
const botonC = (a, v, t, on=false, titulo='') => `<button type="button" data-acc="${a}" data-v="${escC(v)}" class="${on?'on':''}" aria-pressed="${on}" title="${escC(titulo)}">${escC(t)}</button>`;
const segmentoC = (a, opciones, valor, rotulo) => `<div class="vcc-seg" role="group" aria-label="${rotulo}">${opciones.map(([v,t])=>botonC(a,v,t,v===valor)).join('')}</div>`;
function rangosTxtC(rs) { return rs.length ? `${fechaC(rs[0][0])} – ${fechaC(rs[rs.length-1][1])}` : 'sin período comparable'; }
const medC = (t, m) => !t ? null : m==='venta' ? t.venta : m==='pax' ? t.pax : t.pax ? t.cli/t.pax : null;
const fmtMedC = (v, m) => m==='pax' ? numeroC(v) : m==='ticket' ? solesC(v,2) : solesC(v);
const claseC = r => r.venta_ap<=0&&r.venta>0 ? 'nuevo' : r.venta<=0&&r.venta_ap>0 ? 'dejado' : r.venta>0&&r.venta_ap>0 ? 'ambos' : 'otro';
function chispaC(vals) {
  const v=vals.map(x=>finC(x)?x:0), lo=Math.min(...v), hi=Math.max(...v), n=v.length;
  return v.map((y,i)=>`${(n>1?i/(n-1)*100:50).toFixed(1)},${(28-(y-lo)/((hi-lo)||1)*26).toFixed(1)}`).join(' ');
}
function menuC(id, texto, st, contenido, activo=false) {
  return `<div class="vcc-m"><button type="button" class="vcc-mb${activo?' on':''}" aria-expanded="${st.menu===id}" data-acc="menu" data-v="${id}">${escC(texto)} <i>▾</i></button>${st.menu===id?`<div class="vcc-pop">${contenido}</div>`:''}</div>`;
}
function filaControlesC(G) {
  const {B,st}=G, opcion=(a,v,t,on)=>`<button type="button" class="${on?'on':''}" data-acc="${a}" data-v="${escC(v)}">${escC(t)}</button>`;
  const ventanas=VENTANAS_C[st.gran].map(v=>opcion('ventana',v,`Últimos ${v} ${UNIDAD_C[st.gran]}`,v===st.ventana)).join('');
  const contra=st.gran==='Día'?menuC('contra',`Contra: ${st.modo==='calendario'?'Misma fecha':'Mismo día de semana'}`,st,opcion('modo','semana','Mismo día de semana',st.modo==='semana')+opcion('modo','calendario','Misma fecha',st.modo==='calendario'))
    :`<span class="vcc-fijo" title="${st.gran==='Mes'?'Mismo mes del año anterior':'Mismos días de semana, 364 días antes'}">Contra: Año pasado</span>`;
  const alcance=menuC('alcance',`Venta: ${st.excluir?'sin eventos':'toda'}`,st,`<label><input type="checkbox" data-acc="excluir" ${st.excluir?'checked':''}> Excluir Eventos y Venta interna</label>`,st.excluir);
  const ayuda=st.ayuda?`<div class="vcc-help"><b>Comparación justa</b><p>${st.gran==='Día'&&st.modo==='calendario'?'Misma fecha del calendario; el día de semana puede cambiar.':st.gran==='Mes'?'Mismo mes del año anterior. El calendario estima el efecto de tener más o menos días de cada día de semana.':'Mismos días de semana, 364 días antes (52 semanas).'} El período en curso se compara con la misma cantidad de días. El ticket usa la venta de los canales que registran clientes. Las notas de crédito restan y las cuentas divididas cuentan una mesa.</p><p>«Por qué» reparte la diferencia en clientes, ticket y canales sin clientes. El calendario es una referencia aparte: no se vuelve a restar. Las bandas grises son fines de semana y las ámbar, feriados de Perú.</p><p>«Carta nueva» y «Ya no están» se separan por el nombre del plato: uno renombrado cuenta en las dos.</p></div>`:'';
  return `<div class="vcc-fila">${segmentoC('gran',['Día','Semana','Mes'].map(v=>[v,v]),st.gran,'Granularidad')}${menuC('ventana',`Últimos ${st.ventana} ${UNIDAD_C[st.gran]}`,st,ventanas,true)}${contra}${alcance}<div class="vcc-push"></div>
    ${B.P.hay_neto?`<span class="vcc-rot">Medir</span>${segmentoC('neto',[[false,'Venta'],[true,'Neto']],st.neto,'Monto')}`:''}
    <span class="vcc-rel">${botonC('ayuda','','Cálculo',st.ayuda,'Cómo se compara')}${ayuda}</span>${botonC('excel','','Excel')}</div>`;
}
function presupuestoC(V) {
  const ids=V.indices.filter(i=>V.ppto[i]!=null);
  if(!ids.length)return null;
  const p=ids.reduce((s,i)=>s+V.ppto[i],0), a=ids.reduce((s,i)=>s+V.a[i].venta,0);
  return {pct:p>0?a/p*100:null, tip:`Venta ${solesC(a,2)} / presupuesto ${solesC(p,2)}. ${ids.length} de ${V.indices.length} períodos con presupuesto.`};
}
function indicadoresC(G) {
  const {B,st,V}=G, comparable=V.indices.length>0, a=V.ta, p=V.tp;
  const kpi=(id,rot,m)=>{
    const va=comparable?medC(a,m):null, vp=comparable?medC(p,m):null, pct=pctC(va,vp), on=st.med===m;
    return `<button type="button" class="vcc-kpi${on?' on':''}" data-acc="med" data-v="${m}" aria-pressed="${on}"><span class="vcc-kt"><span class="vcc-kr">${rot}</span><strong>${escC(fmtMedC(va,m))}</strong><small><b style="color:${colorC(pct)}">${escC(cambioC(pct))}</b> ${m==='venta'?`· ${escC(solesC(vp))} el año pasado`:'vs año pasado'}</small></span>
      <svg class="vcc-ks" viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true"><polyline points="${chispaC(V.a.map(t=>medC(t,m)))}"/></svg></button>`;
  };
  const anio=V.acum.find(x=>x.nombre.startsWith('Año')), mes=V.acum.find(x=>x.nombre.startsWith('Mes')), pp=presupuestoC(V);
  const tipA=x=>x?`${rangosTxtC([x.rango[0]])} contra ${rangosTxtC([x.rango[1]])} · ${solesC(x.actual,2)} / ${solesC(x.ap,2)}`:'';
  const fecha=`<div class="vcc-kpi fijo"><span class="vcc-kt"><span class="vcc-kr">A la fecha</span><strong title="${escC(tipA(anio))}">${anio?`Año <span style="color:${colorC(anio.var)}">${escC(cambioC(anio.var))}</span>`:'—'}</strong><small title="${escC(tipA(mes))}">${mes?`Mes <b style="color:${colorC(mes.var)}">${escC(cambioC(mes.var))}</b> vs año pasado`:''}</small></span>
    ${pp&&pp.pct!=null?`<span class="vcc-kc" title="${escC(pp.tip)}">Presupuesto <b>${numeroC(pp.pct)}%</b><span class="vcc-prog"><i style="width:${Math.min(100,pp.pct).toFixed(1)}%"></i></span></span>`:''}</div>`;
  return `<div class="vcc-kpis">${kpi('v',st.neto?'Neto':'Venta','venta')}${B.P.hay_pax?kpi('c','Clientes','pax')+kpi('t','Ticket','ticket'):''}${fecha}</div>`;
}
function leyendaC(G) {
  const {B,st}=G;
  if(st.tab==='Montos')return `<span class="vcc-key vcc-ap">Año pasado</span><span class="vcc-key vcc-actual">Actual</span>${st.med==='venta'&&G.V.ppto.some(finC)?'<span class="vcc-key vcc-ppto">Presupuesto</span>':''}`;
  if(st.tab==='Variacion')return ['venta',...(B.P.hay_pax?['pax','ticket']:[])].map(k=>`<label class="vcc-key vcc-${k}"><input type="checkbox" data-acc="serie" data-v="${k}" ${st.series[k]?'checked':''}>${{venta:'Venta',pax:'Clientes',ticket:'Ticket'}[k]}</label>`).join('');
  if(st.tab==='Acumulado')return '<span class="vcc-key vcc-dif">Diferencia del período</span><span class="vcc-key vcc-acum">Brecha acumulada</span>';
  return '';
}
function filaTabsC(G) {
  const {B,st}=G, grafico=['Montos','Variacion','Acumulado'].includes(st.tab);
  const tabs=`<div class="vcc-tabs" role="tablist" aria-label="Qué se ve">${TABS_C.map(([v,t])=>`<button type="button" role="tab" aria-selected="${st.tab===v}" class="${st.tab===v?'on':''}" data-acc="tab" data-v="${v}">${t}</button>`).join('')}</div>`;
  const busca=st.tab==='Platos'?`<div class="vcc-search"><input type="search" data-acc="buscar" aria-label="Buscar platos" placeholder="Buscar plato, grupo o qué cambió…" value="${escC(st.q)}">${st.grupo!=null?botonC('grupo',st.grupo,`${B.P.grupos[st.grupo]} ×`,true):''}${st.canal!=null?botonC('canal',st.canal,`${B.P.canales[st.canal]} ×`,true):''}${st.resto?botonC('resto','','Sólo principales'):''}</div>`:'';
  const cifras=grafico?segmentoC('cifras',[['Clave','Clave'],['Todas','Todas']],st.cifras,'Cifras sobre las barras'):'';
  const ampliar=`<button type="button" class="vcc-amp" data-acc="ampl" aria-pressed="${st.ampl}" title="${st.ampl ? 'Volver a poner el panel al costado' : 'Esconder el panel y usar todo el ancho'}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${st.ampl ? 'M3 9h6V3M21 9h-6V3M3 15h6v6M21 15h-6v6' : 'M9 3H3v6M15 3h6v6M9 21H3v-6M15 21h6v-6'}"/></svg>${st.ampl ? 'Con panel' : 'Ampliar'}</button>`;
  return `<div class="vcc-fila">${tabs}${leyendaC(G)}${busca}<div class="vcc-push"></div>${cifras}${ampliar}</div>`;
}
// ── «Por qué», siempre al costado ───────────────────────────────────────
function filasPanelC(filas, acc) {
  const mx=Math.max(1,...filas.map(f=>Math.abs(f.d)));
  return filas.map(f=>{
    const cuerpo=`<span class="vcc-pn-n">${escC(f.n)}</span><span class="vcc-pn-b"><i style="width:${(Math.abs(f.d)/mx*100).toFixed(0)}%;background:${colorC(f.d)}"></i></span><strong style="color:${colorC(f.d)}">${escC(signoC(f.d))}</strong>`;
    return acc?`<button type="button" class="vcc-pn-f${f.on?' on':''}" data-acc="${acc}" data-v="${f.id}" title="${escC(f.tip||f.n)}">${cuerpo}</button>`:`<div class="vcc-pn-f" title="${escC(f.tip||f.n)}">${cuerpo}</div>`;
  }).join('');
}
function panelC(G) {
  const {B,st,V}=G, unaVez=st.sel&&st.sel[0]===st.sel[1];
  const titulo=st.sel?(unaVez?V.plan.etiquetas[st.sel[0]]:`${V.plan.etiquetas[st.sel[0]]} a ${V.plan.etiquetas[st.sel[1]]}`):'';
  const quitar=st.sel?`<button type="button" class="vcc-lnk" data-acc="soltar">Ver todo ✕</button>`:'';
  if(!V.indices.length){
    const actual=st.sel?V.a.filter((_,i)=>i>=st.sel[0]&&i<=st.sel[1]).reduce((s,a)=>s+a.venta,0):V.a.reduce((s,a)=>s+a.venta,0);
    return `<div class="vcc-pn-t"><b>${escC(titulo||'Sin histórico comparable')}</b>${quitar}</div><p class="vcc-frase">La venta actual de este tramo es ${solesC(actual,2)}. No hay histórico equivalente para calcular su diferencia; no se considera una venta de cero.</p>`;
  }
  const a=V.ta,p=V.tp,d=a.venta-p.venta,pu=V.puente,gen=detalleC(B,V.ra,V.rp,{...st,grupo:null,canal:null});
  const cas=pu?[{n:'Clientes',l:'clientes',d:pu.clientes},{n:'Ticket',l:'ticket',d:pu.ticket},{n:'Rappi y otros',l:'Rappi y otros canales sin clientes',d:pu.sin_clientes,tip:'Canales que no registran clientes'}]:[];
  const orden=cas.slice().sort((x,y)=>Math.abs(y.d)-Math.abs(x.d));
  const pesa=orden.length?` Lo que más pesa: ${orden[0].l} (${signoC(orden[0].d)})${orden[1]?`; después, ${orden[1].l} (${signoC(orden[1].d)})`:''}.`:' Sin clientes comparables: no se puede repartir en clientes y ticket.';
  const frase=`${st.neto?'El neto fue':'Se vendió'} ${solesC(Math.abs(d))} ${d<0?'menos':'más'} que el año pasado (${cambioC(pctC(a.venta,p.venta))}).${pesa}`;
  const notas=lecturaC(V,st);
  let h=`<div class="vcc-pn-t"><b>${escC(titulo||`Por qué: ${signoC(d)}`)}</b>${quitar}</div><p class="vcc-frase">${escC(frase)}</p>${notas.length?`<div class="vcc-notas" title="${escC(notas.join(' · '))}">${escC(notas.join(' · '))}</div>`:''}`;
  if(cas.length)h+=`<div class="vcc-pn-s">De ${escC(solesC(p.venta))} a ${escC(solesC(a.venta))}</div>${filasPanelC(cas)}`;
  const grupos=gen.grupos.map(g=>({id:g.id,n:B.P.grupos[g.id]||'Sin grupo',d:g.d,on:st.grupo===g.id,tip:`${B.P.grupos[g.id]} · actual ${solesC(g.venta,2)} / AP ${solesC(g.venta_ap,2)}`}));
  h+=`<div class="vcc-pn-s">Por grupo</div><div class="vcc-break">${filasPanelC(grupos.slice(0,3),'grupo')}</div>`;
  if(st.sel){
    const bajan=gen.rows.filter(r=>r.d<0).slice(0,3).map(r=>({n:r.prod,d:r.d,tip:`${r.prod}: ${r.que}`}));
    if(bajan.length)h+=`<div class="vcc-pn-s">Platos que más bajan</div>${filasPanelC(bajan)}`;
  } else {
    const canales=gen.canales.map(g=>({id:g.id,n:B.P.canales[g.id],d:g.d,on:st.canal===g.id,tip:`${B.P.canales[g.id]} · actual ${solesC(g.venta,2)} / AP ${solesC(g.venta_ap,2)}`}));
    h+=`<div class="vcc-pn-s">Por canal</div><div class="vcc-break">${filasPanelC(canales.slice(0,3),'canal')}</div>`;
  }
  return h;
}
function lecturaC(V, st) {
  const a=V.ta, p=V.tp, out=[];
  if (!st.neto && p.neto > 0 && p.venta > 0 && Math.abs((a.neto/p.neto)/(a.venta/p.venta)-1)>=.005)
    out.push(`Sin IGV ni recargo: ${cambioC(pctC(a.neto,p.neto))}`);
  if (Math.abs(V.calTotal || 0)>=.5) out.push(`Calendario: ${cambioC(V.calTotal)}`);
  if (!st.excluir && (Math.abs(a.raro)>=1 || Math.abs(p.raro)>=1) && p.venta-p.raro>0)
    out.push(`Sin Eventos ni Venta interna: ${cambioC(pctC(a.venta-a.raro,p.venta-p.raro))}`);
  for (const c of new Set([...Object.keys(a.canales),...Object.keys(p.canales)])) {
    const va=a.canales[c]||0, vp=p.canales[c]||0;
    if ((va>=1)!==(vp>=1)) out.push(`${c}: sólo ${va>=1?'actual':'año pasado'} (${solesC(Math.max(va,vp))})`);
  }
  return out;
}
function renderC(G) {
  if (!G.root?.isConnected) return;
  const root=G.root, B=G.B, st=G.st, V=calcularC(B,st); G.V=V;
  if(!B.P.hay_pax)st.med='venta';
  const focus=root.shadowRoot?.activeElement || root.getRootNode().activeElement;
  const buscando=focus?.matches?.('[data-acc="buscar"]'), cursor=buscando?focus.selectionStart:0;
  const graf=['Montos','Variacion','Acumulado'].includes(st.tab);
  const zona=graf?'<div class="vcc-plot" aria-label="Actual y año pasado por período"></div>':st.tab==='Semana'?semanaC_(G):platosHtmlC(G);
  root.innerHTML=`<section class="vcc-main" aria-label="Comparación con el año pasado">${filaControlesC(G)}${indicadoresC(G)}${filaTabsC(G)}
    <div class="vcc-cuerpo"><div class="vcc-zona">${zona}</div>${st.ampl?'':`<aside class="vcc-pn" aria-label="Por qué">${panelC(G)}</aside>`}</div>
    ${!V.plan.ok.every(Boolean)?`<div class="vcc-notice">Sin histórico equivalente: ${escC(V.plan.sin_dato)}. Fuera de ambos totales; no se considera una venta de cero.</div>`:''}</section>`;
  if(graf)graficoC(G);
  if(st.tab==='Platos'&&V.indices.length)tablaC(G); else {G.rows=[];G.tableCols=[];}
  if (buscando) { const input=root.querySelector('[data-acc="buscar"]'); input?.focus({preventScroll:true}); input?.setSelectionRange(cursor,cursor); }
}
// ── La zona: el gráfico ─────────────────────────────────────────────────
function graficoC(G){
  const {B,st,V,root}=G, plot=root.querySelector('.vcc-plot'); if(!plot)return;
  const w=Math.max(280,plot.clientWidth), h=Math.max(150,plot.clientHeight), l=54,r=10,t=30,b=36, pw=w-l-r, ph=h-t-b, n=V.a.length, step=pw/n, tab=st.tab;
  const okV=i=>V.plan.ok[i];
  const series=V.a.map((a,i)=>({venta:okV(i)?pctC(a.venta,V.p[i].venta):null, pax:okV(i)?pctC(a.pax,V.p[i].pax):null,
    ticket:okV(i)?pctC(medC(a,'ticket'),medC(V.p[i],'ticket')):null}));
  const dif=V.a.map((a,i)=>okV(i)?a.venta-V.p[i].venta:null);
  let acc=0; const acum=dif.map(d=>{if(d==null)return null;acc+=d;return acc;});
  const med=st.med, vA=V.a.map(a=>medC(a,med)), vP=V.p.map((a,i)=>okV(i)?medC(a,med):null);
  let vals;
  if(tab==='Montos')vals=[...vA,...vP,...(med==='venta'?V.ppto:[])];
  else if(tab==='Variacion')vals=series.flatMap(s=>Object.keys(s).filter(k=>st.series[k]).map(k=>s[k]));
  else vals=[...dif,...acum];
  vals=vals.filter(finC);
  let max=Math.max(0,...vals), min=Math.min(0,...vals); if(max===min) max=min+1;
  const span=max-min; max+=span*.1; if(min<0) min-=span*.1;
  const y=v=>t+(max-v)/(max-min)*ph, x=i=>l+(i+.5)*step, zero=y(0);
  const ejeY=v=>tab==='Variacion'?numeroC(v)+'%':tab==='Acumulado'?`${v<0?'−':''}S/ ${compactoC(Math.abs(v))}`:med==='pax'?numeroC(v):`S/ ${compactoC(v)}`;
  G.geom={l,step,n,w,plot};
  let svg=`<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${tab==='Variacion'?'Variación de venta, clientes y ticket':tab==='Acumulado'?'Diferencia y brecha acumulada':'Actual frente al año pasado'}">`;
  for(let i=0;i<4;i++){const v=min+(max-min)*i/3, yy=y(v);svg+=`<line x1="${l}" x2="${w-r}" y1="${yy}" y2="${yy}" class="vcc-grid"/><text x="${l-6}" y="${yy+3}" text-anchor="end" class="vcc-axis">${ejeY(v)}</text>`;}
  if(min<0)svg+=`<line x1="${l}" x2="${w-r}" y1="${zero}" y2="${zero}" class="vcc-zero"/>`;
  // Las bandas y, DETRÁS de las barras, el presupuesto: encima pisaba las cifras.
  for(let i=0;i<n;i++){const ferA=contarFerC(B,V.plan.actual[i]),[da]=V.plan.actual[i],xx=x(i);
    if(st.gran==='Día'&&(semanaC(da)>=5||ferA))svg+=`<rect x="${xx-step/2}" y="${t}" width="${step}" height="${ph}" fill="${ferA?'var(--warning)':'var(--text-secondary)'}" fill-opacity=".075"/>`;
    if(tab==='Montos'&&med==='venta'&&V.ppto[i]!=null)svg+=`<line x1="${xx-step*.42}" x2="${xx+step*.42}" y1="${y(V.ppto[i])}" y2="${y(V.ppto[i])}" class="vcc-ppto-l"/>`;}
  const ancho=Math.min(36,step*.34), tope=[];
  for(let i=0;i<n;i++){
    const xx=x(i), elegida=!st.sel||i>=st.sel[0]&&i<=st.sel[1], parcial=V.plan.parciales.includes(i), ferA=contarFerC(B,V.plan.actual[i]),ferP=contarFerC(B,V.plan.ap[i]);
    svg+=`<g opacity="${elegida?1:.3}">`;
    if(tab==='Montos'){
      if(finC(vP[i]))svg+=rectC(xx-ancho-1,y(Math.max(0,vP[i])),ancho,Math.abs(y(vP[i])-zero),'var(--border-lavender)');
      if(finC(vA[i])){svg+=rectC(xx+1,y(Math.max(0,vA[i])),ancho,Math.abs(y(vA[i])-zero),'var(--accent)');
        if(parcial)svg+=`<rect x="${xx+1}" y="${y(Math.max(0,vA[i]))}" width="${ancho}" height="${Math.max(.5,Math.abs(y(vA[i])-zero))}" rx="2" class="vcc-parc"/>`;}
      tope[i]=Math.min(finC(vA[i])?y(vA[i]):h,finC(vP[i])?y(vP[i]):h);
    } else {
      const v=tab==='Variacion'?(st.series.venta?series[i].venta:null):dif[i], bw=Math.min(40,step*.56);
      if(finC(v))svg+=rectC(xx-bw/2,y(Math.max(0,v)),bw,Math.abs(y(v)-zero),`color-mix(in srgb,var(--${v<0?'danger':'success'}) ${tab==='Acumulado'?30:60}%,transparent)`);
      tope[i]=finC(v)?y(Math.max(0,v)):zero;
    }
    if(!okV(i))svg+=`<text x="${xx}" y="${t-6}" text-anchor="middle" class="vcc-axis">sin AP</text>`;
    if(step>=45&&st.gran!=='Día'&&ferA!==ferP)svg+=`<text x="${xx}" y="${h-4}" text-anchor="middle" class="vcc-warning">${ferA>ferP?'+':''}${ferA-ferP} fer.</text>`;
    else if(step>=40&&st.gran==='Día'&&(ferA||ferP))svg+=`<text x="${xx}" y="${h-4}" text-anchor="middle" class="vcc-warning">${ferA?'feriado':'feriado AP'}</text>`;
    if(parcial)svg+=`<text x="${xx}" y="${h-4}" text-anchor="middle" class="vcc-axis">en curso</text>`;
    svg+='</g>';
  }
  // Las líneas.
  if(tab==='Variacion') for(const [k,c] of [['pax','var(--serie-2)'],['ticket','var(--serie-5)']]) if(st.series[k]&&B.P.hay_pax){
    const pts=series.map((s,i)=>finC(s[k])?[x(i),y(s[k])]:null).filter(Boolean);
    svg+=`<polyline points="${pts.map(p=>p.join(',')).join(' ')}" fill="none" stroke="${c}" stroke-width="2"/>`+pts.map(([a,b_])=>`<circle cx="${a}" cy="${b_}" r="3" fill="${c}"/>`).join('');
  }
  if(tab==='Acumulado'){
    const pts=acum.map((v,i)=>finC(v)?[x(i),y(v)]:null).filter(Boolean);
    svg+=`<polyline points="${pts.map(p=>p.join(',')).join(' ')}" fill="none" stroke="var(--accent-deep)" stroke-width="2.4" stroke-linejoin="round"/>`;
  }
  // Las cifras: sólo las que dicen algo («Todas» vuelve a una por barra).
  const base=tab==='Montos'?vA:tab==='Variacion'?series.map(s=>s.venta):dif;
  const lejos=Math.max(1,Math.ceil(70/step)), hay=base.map((v,i)=>finC(v)?i:-1).filter(i=>i>=0);
  let etq=[];
  if(st.cifras==='Todas') etq=step>=46?hay:hay.filter(i=>(n-1-i)%Math.ceil(46/step)===0);
  else if(hay.length){
    const mx=hay.reduce((a_,i)=>base[i]>base[a_]?i:a_,hay[0]), mn=hay.reduce((a_,i)=>base[i]<base[a_]?i:a_,hay[0]);
    [hay[hay.length-1],mx,mn,...(st.sel?[st.sel[0],st.sel[1]]:[])].forEach(i=>{if(etq.every(u=>Math.abs(u-i)>=lejos))etq.push(i);});
  }
  etq.forEach(i=>{
    const xx=Math.min(Math.max(x(i),l+26),w-r-26); let uno,dos='',col='';
    if(tab==='Montos'){uno=med==='ticket'?`S/ ${numeroC(vA[i])}`:med==='pax'?numeroC(vA[i]):`S/ ${compactoC(vA[i])}`;dos=med==='venta'?cambioC(series[i].venta):cambioC(pctC(vA[i],vP[i]));col=colorC(pctC(vA[i],vP[i]));}
    else if(tab==='Variacion'){uno=cambioC(series[i].venta);}
    else {uno=`${dif[i]<0?'−':'+'}S/ ${compactoC(Math.abs(dif[i]))}`;}
    const yy=tope[i]-4;
    if(dos&&dos!=='—')svg+=`<text x="${xx}" y="${yy-12}" text-anchor="middle" class="vcc-et">${escC(uno)}</text><text x="${xx}" y="${yy}" text-anchor="middle" class="vcc-et" style="fill:${col}">${escC(dos)}</text>`;
    else svg+=`<text x="${xx}" y="${yy}" text-anchor="middle" class="vcc-et">${escC(uno)}</text>`;
  });
  if(tab==='Acumulado'&&acum.some(finC)){
    const u=acum.map((v,i)=>finC(v)?i:-1).filter(i=>i>=0).pop();
    svg+=`<text x="${Math.min(x(u),w-r-40)}" y="${y(acum[u])+15}" text-anchor="middle" class="vcc-et" style="fill:var(--accent-deep)">acum. ${acum[u]<0?'−':'+'}S/ ${compactoC(Math.abs(acum[u]))}</text>`;
  }
  const pasoTick=Math.max(1,Math.ceil(58/step));
  const rotulo=e=>n>14&&st.gran==='Día'?String(e).split(' ').pop():e;
  for(let i=0;i<n;i++) if((n-1-i)%pasoTick===0) svg+=`<text x="${x(i)}" y="${h-19}" text-anchor="middle" class="vcc-axis">${escC(rotulo(V.plan.etiquetas[i]))}</text>`;
  for(let i=0;i<n;i++)svg+=`<rect class="vcc-hit${st.sel&&i>=st.sel[0]&&i<=st.sel[1]?' chosen':''}" data-bar="${i}" role="button" tabindex="0" aria-label="${escC(V.plan.etiquetas[i])}, actual ${solesC(V.a[i].venta,2)}, año pasado ${okV(i)?solesC(V.p[i].venta,2):'sin dato'}" x="${l+i*step}" y="0" width="${step}" height="${h}"/>`;
  plot.innerHTML=svg+'</svg><div class="vcc-tip" hidden></div>';
}
const rectC=(x,y,w,h,c)=>`<rect x="${x}" y="${y}" width="${w}" height="${Math.max(.5,h)}" rx="2" fill="${c}"/>`;
function contarFerC(B,[a,b]){let n=0;for(let d=a;d<=b;d++)if(B.feriados.has(d))n++;return n;}
function tipC(G,i){
  const plot=G.root.querySelector('.vcc-plot'); if(!plot)return;
  const tip=plot.querySelector('.vcc-tip');
  if(i==null){tip.hidden=true;return;}
  const {V,st}=G,a=V.a[i],p=V.p[i], ok=V.plan.ok[i];
  tip.innerHTML=`<b>${escC(V.plan.etiquetas[i])}${V.plan.parciales.includes(i)?' · en curso':''}</b><div>Actual · ${rangosTxtC([V.plan.actual[i]])}<strong>${solesC(a.venta,2)}</strong></div>
    <div>Año pasado · ${rangosTxtC([V.plan.ap[i]])}<strong>${ok?solesC(p.venta,2):'sin datos comparables'}</strong></div>
    ${ok?`<div>Diferencia <strong style="color:${colorC(a.venta-p.venta)}">${signoC(a.venta-p.venta)} · ${cambioC(pctC(a.venta,p.venta))}</strong></div>`:''}
    ${G.B.P.hay_pax?`<div>Clientes ${numeroC(a.pax)} / ${ok?numeroC(p.pax):'—'} · ticket ${solesC(a.pax?a.cli/a.pax:null,2)} / ${ok?solesC(p.pax?p.cli/p.pax:null,2):'—'}</div>`:''}
    ${V.ppto[i]!=null&&st.tab==='Montos'?`<div>Presupuesto ${solesC(V.ppto[i],2)}</div>`:''}${Math.abs(V.cal[i]||0)>=.5?`<div>Referencia de calendario: ${cambioC(V.cal[i])}</div>`:''}
    ${contarFerC(G.B,V.plan.actual[i])||contarFerC(G.B,V.plan.ap[i])?`<div>Feriados: ${contarFerC(G.B,V.plan.actual[i])} actual / ${contarFerC(G.B,V.plan.ap[i])} año pasado</div>`:''}`;
  tip.style.left=`${Math.max(0,Math.min(plot.clientWidth-285,G.geom.l+(i+.5)*G.geom.step-140))}px`;tip.hidden=false;
}
// ── La zona: día de semana ──────────────────────────────────────────────
function porSemanaC(V){
  const s=Array.from({length:7},()=>({a:0,p:0,na:0,np:0}));
  for(const i of V.indices){
    const [a0,a1]=V.plan.actual[i],[p0,p1]=V.plan.ap[i];
    for(let d=a0;d<=a1;d++){const w=semanaC(d);s[w].a+=V.a[i].dias[d]||0;s[w].na++;}
    for(let d=p0;d<=p1;d++){const w=semanaC(d);s[w].p+=V.p[i].dias[d]||0;s[w].np++;}
  }
  return s.map(x=>({prom:x.na?x.a/x.na:0,promAp:x.np?x.p/x.np:0,n:x.na,nAp:x.np}));
}
function semanaC_(G){
  const s=porSemanaC(G.V), mx=Math.max(1,...s.flatMap(x=>[x.prom,x.promAp]));
  const hay=s.map((x,i)=>({i,v:pctC(x.prom,x.promAp)})).filter(x=>finC(x.v)).sort((a,b)=>a.v-b.v);
  const nota=hay.length>1?`Lo más flojo: ${DIAS_C[hay[0].i].toLowerCase()} (${cambioC(hay[0].v)}); lo mejor: ${DIAS_C[hay[hay.length-1].i].toLowerCase()} (${cambioC(hay[hay.length-1].v)}).`:'';
  return `<div class="vcc-sem"><div class="vcc-sem-f cab"><span>Día</span><span>Promedio por día: año pasado y actual</span><span class="vcc-num">Promedio actual</span><span class="vcc-num">Δ S/</span><span class="vcc-num">Var.</span></div>
    ${s.map((x,i)=>{const v=pctC(x.prom,x.promAp);return `<div class="vcc-sem-f" title="${x.n} ${DIAS_C[i].toLowerCase()}(s) actuales, ${x.nAp} del año pasado"><b>${DIAS_C[i]}</b><span class="vcc-sem-b"><i class="ap" style="width:${(x.promAp/mx*100).toFixed(1)}%"></i><i style="width:${(x.prom/mx*100).toFixed(1)}%"></i></span><span class="vcc-num">${solesC(x.prom)}</span><span class="vcc-num" style="color:${colorC(v)}">${signoC(x.prom-x.promAp)}</span><b class="vcc-num" style="color:${colorC(v)}">${cambioC(v)}</b></div>`;}).join('')}
    <div class="vcc-sem-n">Promedio de cada día en lo que se compara. ${nota}</div></div>`;
}
// ── La zona: los platos ─────────────────────────────────────────────────
function detalleZonaC(G){ const {B,st,V}=G; return detalleC(B,V.ra,V.rp,st); }
function platosHtmlC(G){
  const {st,V}=G;
  if(!V.indices.length)return '<div class="vcc-vacio">Sin período comparable: no hay platos que comparar.</div>';
  const rows=detalleZonaC(G).rows, suma=(l,k)=>l.reduce((s,r)=>s+r[k],0), de=c=>rows.filter(r=>claseC(r)===c);
  const am=de('ambos'),nu=de('nuevo'),dj=de('dejado');
  const c=(id,rot,v,col,tip)=>`<button type="button" class="vcc-cl${st.clase===id?' on':''}" data-acc="clase" data-v="${id}" aria-pressed="${st.clase===id}" title="${escC(tip)}"><span>${escC(rot)}</span><strong style="color:${col}">${escC(signoC(v))}</strong></button>`;
  return `<div class="vcc-cls">${c('todos','Toda la diferencia',suma(rows,'d'),colorC(suma(rows,'d')),`${rows.length} platos`)}
      ${c('ambos',`Mismos platos · ${am.length}`,suma(am,'d'),colorC(suma(am,'d')),`Se vendieron en los dos períodos. Por cantidad ${signoC(suma(am,'ef_cant'))}; por precio ${signoC(suma(am,'ef_precio'))}`)}
      ${c('nuevo',`Carta nueva · ${nu.length}`,suma(nu,'venta'),'var(--success)','Se vendieron ahora y no el año pasado, por nombre: un plato renombrado cuenta como nuevo')}
      ${c('dejado',`Ya no están · ${dj.length}`,-suma(dj,'venta_ap'),'var(--danger)','Se vendieron el año pasado y no ahora, por nombre')}</div>
    <div class="vcc-table-scroll" tabindex="0" aria-label="Platos que explican la diferencia"></div><div class="vcc-table-foot"></div>`;
}
const COLS_C=[['fam','Grupo'],['prod','Producto'],['que','Qué cambió'],['d','Δ S/'],['var','%Var'],['ef_cant','Por cantidad'],['ef_precio','Por precio'],['venta_ap','Venta AP'],['venta','Venta actual'],['cant_ap','Cant AP'],['cant','Cant actual'],['precio_ap','Precio AP'],['precio','Precio actual']];
const VER_C=[['prod','Plato'],['que','Qué cambió'],['venta_ap','Año pasado'],['venta','Actual'],['d','Δ S/'],['ef_cant','Por cantidad'],['ef_precio','Por precio']];
const AYUDA_C={que:'Lo que más pesó: unidades o precio promedio.',ef_cant:'Unidades de más o de menos al precio del año pasado.',ef_precio:'Cambio de precio promedio sobre las unidades actuales. Por cantidad + por precio = Δ S/.'};
const SIN_CANT_C=['cant','cant_ap','precio','precio_ap','ef_cant','ef_precio','que'];
function valorCeldaC(r,k){
  if(k==='var')return r.venta_ap<=0&&r.venta>0?'nuevo':r.venta_ap<=0?'—':cambioC(r.var);
  if(k==='cant'||k==='cant_ap')return numeroC(r[k],2);
  if(k==='precio'||k==='precio_ap')return r[k]?solesC(r[k],2):'—';
  if((k==='ef_cant'||k==='ef_precio')&&!r.resto&&claseC(r)!=='ambos')return '—';
  if(['d','ef_cant','ef_precio'].includes(k))return signoC(r[k]);
  if(k==='venta'||k==='venta_ap')return r[k]?solesC(r[k]):'—';
  return r[k]||'';
}
function filasPlatosC(G){
  const {st}=G, rows=detalleZonaC(G).rows;
  return st.clase==='todos'?rows:rows.filter(r=>claseC(r)===st.clase);
}
function tablaC(G){
  const base=filasPlatosC(G), rs=visiblesC(base,G.st); G.rows=rs;
  const conCant=([k])=>G.B.P.hay_cant||!SIN_CANT_C.includes(k);
  G.tableCols=COLS_C.filter(conCant); G.verCols=VER_C.filter(conCant);
  const wrap=G.root.querySelector('.vcc-table-scroll'), old=wrap.scrollTop;
  wrap.innerHTML=`<table><thead><tr>${G.verCols.map(([k,t])=>`<th class="${['prod','que'].includes(k)?'':'vcc-num'}"><button type="button" data-acc="orden" data-v="${k}" title="${escC(AYUDA_C[k]||`Ordenar por ${t}`)}">${t}${G.st.orden?.col===k?(G.st.orden.dir>0?' ↑':' ↓'):''}</button></th>`).join('')}</tr></thead><tbody></tbody></table>`;
  G.tableN=0; agregarFilasC(G);
  wrap.scrollTop=old;
  wrap.addEventListener('scroll',()=>{if(wrap.scrollTop+wrap.clientHeight>=wrap.scrollHeight-100)agregarFilasC(G);},{passive:true});
  const total=rs.reduce((s,r)=>s+r.d,0), cuantos=buscarC(base,G.st.q).length;
  G.root.querySelector('.vcc-table-foot').innerHTML=`<span>${cuantos} producto${cuantos===1?'':'s'}${G.st.q?' · búsqueda aplicada':''}${G.st.grupo!=null||G.st.canal!=null?' · tabla filtrada':''} · Δ de las filas: <b style="color:${colorC(total)}">${signoC(total)}</b></span><span>${G.st.resto?'Todos los resultados':G.st.orden?'Orden elegido; «Resto» abre los demás':'Principales por |Δ S/|; «Resto» abre los demás'}</span>`;
}
function agregarFilasC(G){
  const tbody=G.root.querySelector('.vcc-table-scroll tbody');if(!tbody)return;
  const end=Math.min(G.rows.length,G.tableN+150);
  tbody.insertAdjacentHTML('beforeend',G.rows.slice(G.tableN,end).map(r=>`<tr class="${r.resto?'vcc-rest':''}" title="${r.resto?'':escC(`${r.fam} › ${r.sub} · ${numeroC(r.cant_ap,1)} → ${numeroC(r.cant,1)} unid. · ${r.precio_ap?solesC(r.precio_ap,2):'—'} → ${r.precio?solesC(r.precio,2):'—'}`)}">${G.verCols.map(([k])=>`<td class="${['prod','que'].includes(k)?'':'vcc-num'}"${['d','ef_cant','ef_precio'].includes(k)&&valorCeldaC(r,k)!=='—'?` style="color:${colorC(r[k])}"`:''}>${k==='prod'&&r.resto?botonC('resto','',r.prod):escC(valorCeldaC(r,k))}</td>`).join('')}</tr>`).join(''));
  G.tableN=end;
}
function excelC(G){
  const {B,st,V}=G, ids=st.sel?V.plan.actual.map((_,i)=>i).filter(i=>i>=st.sel[0]&&i<=st.sel[1]):V.plan.actual.map((_,i)=>i);
  const head=['Período','Desde actual','Hasta actual','Desde AP','Hasta AP','Comparable','En curso','Venta AP','Venta actual','Δ S/','%Var','Clientes AP','Clientes actual','Ticket AP','Ticket actual','Presupuesto','Calendario %'];
  const data=ids.map(i=>{const a=V.a[i],p=V.p[i],ok=V.plan.ok[i];return [V.plan.etiquetas[i],...V.plan.actual[i].map(isoC),...V.plan.ap[i].map(isoC),ok?'Sí':'Sin histórico',V.plan.parciales.includes(i)?'Sí':'No',ok?p.venta:null,a.venta,ok?a.venta-p.venta:null,ok?pctC(a.venta,p.venta):null,ok?p.pax:null,a.pax,ok&&p.pax?p.cli/p.pax:null,a.pax?a.cli/a.pax:null,V.ppto[i],V.cal[i]];});
  const hojas=[{nombre:'Comparativo',cabeza:head,filas:data}];
  if(V.indices.length){
    const cols=COLS_C.filter(([k])=>B.P.hay_cant||!SIN_CANT_C.includes(k));
    const rows=visiblesC(filasPlatosC(G),{...st,resto:true});
    hojas.push({nombre:'Productos',cabeza:cols.map(c=>c[1]),filas:rows.map(r=>cols.map(([k])=>k==='var'&&r.venta_ap<=0?r.venta>0?'nuevo':null:['precio','precio_ap'].includes(k)&&!r[k]?null:r[k]??null))});
  }
  const contexto=[['Hasta',B.P.ancla],['Granularidad',st.gran],['Ventana',st.ventana],['Alineación',st.gran==='Mes'?'Mismo mes':st.modo==='calendario'?'Misma fecha':'364 días antes'],['Monto',st.neto?'Neto sin IGV ni recargo':'Venta'],['Vista',st.tab],['Excluir Eventos y Venta interna',st.excluir?'Sí':'No'],['Rango actual',rangosTxtC(V.ra)],['Rango AP',rangosTxtC(V.rp)],['Platos',st.clase],['Grupo de la tabla',st.grupo==null?'Todos':B.P.grupos[st.grupo]],['Canal de la tabla',st.canal==null?'Todos':B.P.canales[st.canal]],['Buscar',st.q],...Object.entries(B.P.filtros).map(([k,v])=>[k,Array.isArray(v)?v.join(', '):String(v)])];
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
    const el=ev.target.closest('[data-acc]'), st=G.st;
    if(st.menu&&!ev.target.closest('.vcc-pop')&&!(el&&el.dataset.acc==='menu')){st.menu=null;if(!el){renderC(G);return;}}
    if(!el||el.tagName==='INPUT')return;
    const a=el.dataset.acc,v=el.dataset.v;
    if(a==='menu')st.menu=st.menu===v?null:v;
    else if(a==='gran'){st.gran=v;st.ventana=DEF_C[v];st.sel=null;}
    else if(a==='ventana'){st.ventana=+v;st.sel=null;st.menu=null;}
    else if(a==='modo'){st.modo=v;st.sel=null;st.menu=null;}
    else if(a==='neto')st.neto=v==='true';
    else if(a==='tab')st.tab=v;
    else if(a==='med')st.med=v;
    else if(a==='cifras')st.cifras=v;
    else if(a==='ampl')st.ampl=!st.ampl;
    else if(a==='clase'){st.clase=v;st.resto=false;}
    else if(a==='soltar'){st.sel=null;st.grupo=null;st.canal=null;}
    else if(a==='grupo'||a==='canal'){st[a]=st[a]===+v?null:+v;st.resto=false;if(st[a]!=null)st.tab='Platos';}
    else if(a==='orden'){const prev=st.orden,dir=['fam','prod','que'].includes(v)?1:-1;st.orden=!prev||prev.col!==v?{col:v,dir}:prev.dir===dir?{col:v,dir:-dir}:null;}
    else if(a==='resto')st.resto=!st.resto;
    else if(a==='ayuda')st.ayuda=!st.ayuda;
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
  root.addEventListener('keydown',ev=>{const b=ev.target.closest('[data-bar]');if(b&&(ev.key==='Enter'||ev.key===' ')){ev.preventDefault();elegirC(G,+b.dataset.bar,+b.dataset.bar);}if(ev.key==='Escape'&&(G.st.ayuda||G.st.menu)){G.st.ayuda=false;G.st.menu=null;renderC(G);}});
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
  G.observer=new ResizeObserver(()=>{if(!G.root.isConnected)return;const w=root.clientWidth,h=root.querySelector('.vcc-plot')?.clientHeight||0;if(Math.abs(w-width)>2||Math.abs(h-height)>2){width=w;height=h;if(G.B)graficoC(G);}});
  G.observer.observe(root);
}
window.__vcUI={inicial:inicialC,render:renderC,excel:excelC};
export default function(component){
  const {data,parentElement}=component;if(!data||data.parte!=='comparativo')return;
  const G=window.__vtComparativo||(window.__vtComparativo={st:inicialC()});
  let root=parentElement.querySelector('.vcc'),nuevo=!root;
  if(nuevo){root=document.createElement('div');root.className='vcc';parentElement.appendChild(root);G.root=root;enlazarC(G);}else G.root=root;
  sinFechaFranja(root);
  if(G.sello!==data.sello){G.B=leerC(data);G.sello=data.sello;G.st.sel=null;G.st.grupo=null;G.st.canal=null;G.st.q='';G.st.resto=false;G.st.orden=null;}
  else if(!nuevo)return;
  if(!data.hay_neto)G.st.neto=false;
  root.style.setProperty('--vcc-fig',`${data.alto_fig||276}px`);
  renderC(G);
}
