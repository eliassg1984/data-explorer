// «Control» de Documentos SUNAT (regla #759): la app contra la lista de SUNAT y
// contra lo presentado, mes por mes, y los XML que faltan con su motivo.
//
// La monta graficos/compras/sunat_control_pieza.py (sin iframe, estilos en un
// shadow root). Python manda los meses —con cada documento presentado— y lo que
// falta de XML: filtrar, elegir un mes, abrir el archivo y bajar el Excel son del
// navegador. A Python vuelven sólo tres triggers: `verificar` (consulta a SUNAT un
// mes), `zip` (arma el ZIP de un mes) y `pedir` (deja los pedidos de XML).

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const ent = (v) => Math.round(Number(v) || 0).toLocaleString('en-US');
const f2 = (x) => (x == null ? '—' : Number(x).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const mil = (v) => { const s = Math.abs(Number(v) || 0); return 'S/ ' + (s >= 1e6 ? (s / 1e6).toFixed(2) + 'M' : s >= 1e3 ? (s / 1e3).toFixed(1) + 'k' : Math.round(s)); };
const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const nomMes = (p) => MESES[+String(p).slice(4) - 1] + ' ' + String(p).slice(0, 4);
const ETIQ = { falta: 'No están en la app', usd: 'Sin convertir', otro_mes: 'En otro mes', monto: 'Monto distinto', otra_anot: 'Otra anotación', igual: 'Igual' };
const TONO_FILA = { falta: 'c', usd: 'c', otro_mes: 'b', monto: 'b', otra_anot: 'g', igual: 'a' };
const ORDEN = ['falta', 'usd', 'otro_mes', 'monto', 'otra_anot'];
const ESTADO = { ok: ['Igual a la lista', 'a'], tar: ['Igual · Diners', 'a'], act: ['Aún no llegan', 'c'], dos: ['SUNAT no coincide', 'b'], sol: ['Monto distinto', 'b'], fallo: ['No se actualizó', 'c'] };
const X = { fecha: 0, tipo: 1, doc: 2, prov: 3, base: 4, igv: 5, ng: 6, total: 7, mon: 8, est: 9, pApp: 10, app: 11 };

// El estado de un mes con lo que ya se consultó en vivo.
function estadoDe(m, verif) {
  const v = verif[m.p];
  if (m.e === 'fallo') return 'fallo';
  if (v && !v.error && v.fa.length) return 'act';
  return m.e;
}

function fechaRevision(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return '';
  const hoy = new Date(), dias = Math.floor((new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()) - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 864e5);
  const hora = d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
  return (dias === 0 ? 'hoy ' : dias === 1 ? 'ayer ' : 'hace ' + dias + ' días, ') + hora;
}

function kpi(k, rot, val, nota, activo) {
  return `<button class="kpi${activo ? ' on' : ''}" data-a="${k[0]}" data-v="${esc(k[1])}" aria-pressed="${activo}"><span class="r">${esc(rot)}</span><span class="v">${esc(val)}</span><span class="d" title="${esc(nota)}">${esc(nota)}</span></button>`;
}

function dibujarMeses(P, st) {
  const M = P.meses, conEst = M.map((m) => Object.assign({}, m, { e2: estadoDe(m, P.verif) }));
  const cuenta = (f) => conEst.filter(f).length;
  const ok = cuenta((m) => m.e2 === 'ok' || m.e2 === 'tar'), rev = cuenta((m) => m.e2 === 'dos' || m.e2 === 'sol');
  const act = conEst.reduce((a, m) => a + (P.verif[m.p] && P.verif[m.p].fa ? P.verif[m.p].fa.length : 0), 0);
  const actS = conEst.reduce((a, m) => a + (P.verif[m.p] && P.verif[m.p].fa ? P.verif[m.p].fa.reduce((b, x) => b + x[3], 0) : 0), 0);
  const vAb = P.verif[P.abierto];
  const faltaN = M.reduce((a, m) => a + m.falta, 0), faltaS = M.reduce((a, m) => a + m.falta_s, 0), conReg = cuenta((m) => m.r4);
  const notaAct = !vAb ? 'consultando el mes abierto…' : vAb.error ? 'SUNAT no respondió' : act ? 'documentos · ' + mil(actS) + ' · los trae la próxima actualización' : 'el mes abierto está al día';
  const kpis = [
    kpi(['fil', 'ok'], 'Igual a la lista de SUNAT', ok + ' de ' + M.length, 'meses: la app tiene lo mismo', st.cfil === 'ok'),
    kpi(['fil', 'act'], 'Aún no llegan a la app', vAb && !vAb.error ? ent(act) : '—', notaAct, st.cfil === 'act'),
    kpi(['fil', 'rev'], 'Cifras distintas', ent(rev), 'meses, con su documento o su causa', st.cfil === 'rev'),
    kpi(['fil', 'reg'], 'Presentados, no están en la app', ent(faltaN), 'documentos · ' + mil(faltaS) + ' · en ' + conReg + ' meses', st.cfil === 'reg'),
  ].join('');
  const pasa = (m) => !st.cfil || (st.cfil === 'ok' ? m.e2 === 'ok' || m.e2 === 'tar' : st.cfil === 'act' ? m.e2 === 'act' : st.cfil === 'rev' ? m.e2 === 'dos' || m.e2 === 'sol' : m.falta > 0);
  const vis = conEst.filter(pasa).reverse();
  const el = vis.find((m) => m.p === st.csel) || vis[0] || conEst[conEst.length - 1];
  const doc = st.cmed === 'doc';
  const v2 = (par) => (par == null ? '—' : doc ? ent(par[0]) : f2(par[1]));
  const filas = vis.map((m) => { const r4 = m.r4 && m.r4.tot, mas = r4 && r4[0] !== m.app[0]; const [e, c] = ESTADO[m.e2]; return `<tr class="${m.p === el.p ? 'on' : ''}"><td class="i"><button data-a="mes" data-v="${m.p}" aria-pressed="${m.p === el.p}">${nomMes(m.p)}</button></td><td>${v2(m.app)}</td><td>${v2(m.r1 && m.r1.tot)}</td><td class="${mas ? 'reg' : 'neu'}">${r4 ? v2(r4) : '—'}</td><td class="i"><span class="est ${c}">${e}</span></td></tr>`; }).join('');
  const chip = st.cfil ? `<button class="quita" data-a="fil" data-v="">✕ ${esc({ ok: 'Igual a la lista', act: 'Aún no llegan', rev: 'Cifras distintas', reg: 'Presentados, no están' }[st.cfil])}</button>` : '';
  return `<div class="kpis">${kpis}</div><div class="cuerpo"><div class="izq">
    <div class="fl"><span class="seg" role="group" aria-label="Medir en">${[['doc', 'Documentos'], ['sol', 'Soles']].map(([k, n]) => `<button class="${st.cmed === k ? 'on' : ''}" data-a="med" data-v="${k}">${n}</button>`).join('')}</span><span class="esp"></span>${chip}</div>
    <div class="caja"><table><thead><tr><th class="i">Mes</th><th>En la app</th><th title="Los comprobantes que SUNAT reunió por su cuenta">Lista de SUNAT</th><th title="La lista, con lo que se agregó o corrigió al presentarla">Lo presentado</th><th class="i">La app contra la lista</th></tr></thead><tbody>${filas}</tbody></table></div>
  </div>${fichaMes(P, st, el, v2)}</div>`;
}

function fichaMes(P, st, el, v2) {
  const N = P.nom, nom = (c) => N[c] || c;
  const r1 = el.r1 || {}, r4 = el.r4 || {}, t1 = r1.tot, t4 = r4.tot, v = P.verif[el.p];
  let frase = 'La app tiene lo mismo que la lista de SUNAT.', cls = 'ok';
  if (el.e2 === 'fallo') { frase = 'SUNAT no respondió al actualizarlo: son los datos de la corrida anterior, y pueden estar incompletos.'; cls = 'ojo'; }
  else if (el.e2 === 'act') { frase = 'Faltan ' + v.fa.length + ' documentos que SUNAT ya tiene: llegaron después de la última actualización. La próxima los trae.'; cls = 'ojo'; }
  else if (el.e2 === 'dos') { frase = 'El detalle de SUNAT da ' + ent(el.det ?? el.app[0]) + ', igual que la app, pero su resumen dice ' + ent(t1 && t1[0]) + '. Las dos cuentas de SUNAT no coinciden entre sí, y ese resumen no baja a documentos.'; cls = 'lav'; }
  else if (el.e2 === 'sol') { frase = 'SUNAT da otro total en ' + el.docs.length + (el.docs.length === 1 ? ' documento: la app suma sus partes.' : ' documentos: la app suma sus partes.'); cls = 'lav'; }
  const tipos = [...new Set([...Object.keys(el.a), ...Object.keys(r1.por || {}), ...Object.keys(r4.por || {})])].sort();
  const filas = tipos.map((c) => { const a = el.a[c], p = (r1.por || {})[c], r = (r4.por || {})[c], dif = r && (!a || r[0] !== a[0]); return `<tr class="${dif ? 'si' : ''}"><td class="i">${esc(nom(c))}</td><td>${v2(a)}</td><td>${v2(p)}</td><td class="${dif ? 'mal' : ''}">${t4 ? v2(r) : '—'}</td></tr>`; }).join('');
  const totDif = t4 && t4[0] !== el.app[0];
  let nota = t4 ? '' : 'SUNAT no entrega lo presentado de este mes.';
  if (Math.abs(el.t42 - el.a42) > 1) nota = (nota ? nota + ' ' : '') + 'Diners: la app muestra la comisión (S/ ' + f2(el.a42) + '). El total en SUNAT, S/ ' + f2(el.t42) + ', parece ser lo vendido con esa tarjeta.';
  const ln = (a, b, val) => `<div class="ln"><span title="${esc(a)}">${esc(a)}<small>${esc(b)}</small></span><b>${esc(val)}</b></div>`;
  const docs = el.docs.length ? `<p class="tit">Los documentos con monto distinto</p>` + el.docs.map((x) => ln(x[2], x[1] + ' · ' + x[0] + ' · sus partes suman S/ ' + f2(x[4]), f2(x[3]))).join('') : '';
  let ver = '';
  if (st.espera.has(el.p)) ver = `<div class="causa gris">Consultando a SUNAT…</div>`;
  else if (v && v.error) ver = `<div class="causa ojo">${esc(v.error)}</div>`;
  else if (v) {
    const dif = v.fa.length || v.so.length;
    ver = `<div class="causa ${dif ? 'ojo' : 'ok'}">Consultado ${esc(v.h)}: SUNAT tiene ${ent(v.vivo)} documentos; la app, ${ent(v.app)}. ${dif ? (v.fa.length ? 'Faltan ' + v.fa.length + ' en la app. ' : '') + (v.so.length ? 'SUNAT ya no lista ' + v.so.length + '.' : '') : 'Todos coinciden uno por uno.'}</div>`
      + v.fa.slice(0, 40).map((x) => ln(x[2], x[1] + ' · ' + x[0], f2(x[3]))).join('');
  }
  const cu = {}; el.filas.forEach((x) => { cu[x[X.est]] = (cu[x[X.est]] || 0) + 1; });
  const grupos = ORDEN.filter((k) => cu[k]);
  const est = grupos.includes(st.cest) ? st.cest : grupos[0];
  const sub = (x) => x[X.doc] + ' · ' + x[X.fecha] + (x[X.est] === 'otro_mes' ? ' · en la app, en ' + nomMes(x[X.pApp]).toLowerCase() : x[X.est] === 'usd' ? ' · la app lo tiene sin convertir a soles' : x[X.est] === 'monto' ? ' · en la app, S/ ' + f2(x[X.app]) : x[X.est] === 'otra_anot' ? ' · con otra anotación' : ' · ' + nom(x[X.tipo]));
  const lista = el.filas.filter((x) => x[X.est] === est).sort((a, b) => Math.abs(b[X.total]) - Math.abs(a[X.total])).slice(0, 30);
  const pres = el.filas.length ? `<p class="tit">Lo presentado, comparado con la app</p>
    ${grupos.length ? `<span class="seg ch" role="group" aria-label="Qué pasa con lo presentado">${grupos.map((k) => `<button class="${k === est ? 'on' : ''}" data-a="grupo" data-v="${k}">${ETIQ[k]} ${cu[k]}</button>`).join('')}</span>` : '<p class="nota">Todo lo presentado está igual en la app.</p>'}
    ${lista.map((x) => ln(x[X.prov], sub(x), f2(x[X.total]))).join('')}
    <button class="ir" data-a="archivo" data-v="${el.p}">Ver el archivo de SUNAT ↗</button>` : '';
  return `<div class="panel"><h3>${nomMes(el.p)}</h3><div class="sub">En la app ${ent(el.app[0])}${t4 ? ' · presentados ' + ent(t4[0]) : ''}</div>
    <div class="causa ${cls}">${esc(frase)}</div>
    <table class="tipos"><thead><tr><th class="i">Tipo</th><th>App</th><th>Lista</th><th>Presentado</th></tr></thead><tbody>${filas}<tr class="tot"><td class="i">Total</td><td>${v2(el.app)}</td><td>${v2(t1)}</td><td class="${totDif ? 'mal' : ''}">${t4 ? v2(t4) : '—'}</td></tr></tbody></table>
    ${nota ? `<p class="nota">${esc(nota)}</p>` : ''}${docs}
    <button class="ir prim" data-a="verificar" data-v="${el.p}"${st.espera.has(el.p) ? ' disabled' : ''}>Verificar con SUNAT</button>${ver}${pres}</div>`;
}

function dibujarArchivo(P, st) {
  const el = P.meses.find((m) => m.p === st.csel) || P.meses[P.meses.length - 1], N = P.nom;
  const cu = {}; el.filas.forEach((x) => { cu[x[X.est]] = (cu[x[X.est]] || 0) + 1; });
  const vis = st.archf ? el.filas.filter((x) => x[X.est] === st.archf) : el.filas;
  const texto = (x) => (x[X.est] === 'otro_mes' ? 'En ' + nomMes(x[X.pApp]).toLowerCase() : x[X.est] === 'usd' ? 'Sin convertir a soles' : x[X.est] === 'monto' ? 'Distinto: S/ ' + f2(x[X.app]) : ETIQ[x[X.est]]);
  const t4 = el.r4 && el.r4.tot;
  const igual = t4 && t4[0] === el.filas.length;
  const filtros = [['', 'Todos ' + el.filas.length]].concat([...ORDEN, 'igual'].filter((k) => cu[k]).map((k) => [k, ETIQ[k] + ' ' + cu[k]]));
  return `<div class="lado"><div class="fl"><button class="amp" data-a="volver">← Volver</button><b>El archivo de SUNAT · ${nomMes(el.p)}</b><span class="esp"></span><span class="seg ch" role="group" aria-label="Filtrar">${filtros.map(([k, n]) => `<button class="${st.archf === k ? 'on' : ''}" data-a="archf" data-v="${k}">${esc(n)}</button>`).join('')}</span><button class="pil" data-a="excel" data-v="${el.p}">Bajar a Excel</button></div>
    <div class="causa ${igual ? 'ok' : 'ojo'}">Archivo oficial de SUNAT: ${ent(el.filas.length)} documentos${igual ? ', igual que su resumen (' + ent(t4[0]) + ')' : t4 ? ', y su resumen dice ' + ent(t4[0]) : ''}. Pedido por su servicio de exportación${el.ticket ? ', ticket ' + esc(el.ticket) : ''}.</div>
    <div class="caja"><table><thead><tr><th class="i">Fecha</th><th class="i">Tipo</th><th class="i">Documento</th><th class="i">Proveedor</th><th>Base</th><th>IGV</th><th>No gravado</th><th>Total</th><th class="i">Mon.</th><th class="i">En la app</th></tr></thead><tbody>${vis.map((x) => `<tr><td class="i">${esc(x[X.fecha])}</td><td class="i tr" title="${esc(N[x[X.tipo]] || x[X.tipo])}">${esc(N[x[X.tipo]] || x[X.tipo])}</td><td class="i">${esc(x[X.doc])}</td><td class="i tr" title="${esc(x[X.prov])}">${esc(x[X.prov])}</td><td>${f2(x[X.base])}</td><td>${f2(x[X.igv])}</td><td>${f2(x[X.ng])}</td><td>${f2(x[X.total])}</td><td class="i">${esc(x[X.mon])}</td><td class="i"><span class="est ${TONO_FILA[x[X.est]]}">${esc(texto(x))}</span></td></tr>`).join('')}</tbody></table></div></div>`;
}

const GRUPO_XML = { banco: 'Banco o financiera: no publica el XML', nunca: 'SUNAT nunca entrega de este proveedor', fallo: 'Falló al pedirlo: se reintenta desde su ficha', pedido: 'Ya pedido, en espera', reciente: 'Reciente: lo baja la corrida nocturna', pedir: 'Se puede pedir' };
const TONO_XML = { banco: 'g', nunca: 'g', fallo: 'c', pedido: 'b', reciente: 'b', pedir: 'e' };

function filasXml(P, st) {
  const q = st.xq.trim().toLowerCase();
  return P.xml.falt.filter((r) => (!st.xgr || r[4] === st.xgr || (st.xgr === 'pedir' && r[4] === 'reciente') || (st.xgr === 'fallo' && r[4] === 'nunca')) && (!q || (r[1] + ' ' + r[2]).toLowerCase().includes(q)));
}

function tablaXml(P, st) {
  return filasXml(P, st).slice(0, 300).map((r) => `<tr><td class="i">${esc(r[0])}</td><td class="i">${esc(r[1])}</td><td class="i tr" title="${esc(r[2])}">${esc(r[2])}</td><td>${f2(r[3])}</td><td class="i"><span class="est ${TONO_XML[r[4]]}">${esc(GRUPO_XML[r[4]])}</span></td></tr>`).join('');
}

function dibujarXml(P, st) {
  const x = P.xml, cu = (...g) => x.falt.filter((r) => g.includes(r[4])).length, so = (...g) => x.falt.filter((r) => g.includes(r[4])).reduce((a, r) => a + r[3], 0);
  const kpis = [
    kpi(['xgr', ''], 'XML bajados', ent(x.con), 'de ' + ent(x.total) + ' · ' + (x.total ? (x.con / x.total * 100).toFixed(1) : '0') + ' % de los últimos 12 meses', !st.xgr),
    kpi(['xgr', 'pedir'], 'Se pueden pedir', ent(cu('pedir', 'reciente')), mil(so('pedir', 'reciente')) + ' · sus proveedores sí los entregan', st.xgr === 'pedir'),
    kpi(['xgr', 'banco'], 'Bancos y financieras', ent(cu('banco')), mil(so('banco')) + ' · no publican sus XML', st.xgr === 'banco'),
    kpi(['xgr', 'fallo'], 'SUNAT no los dio', ent(cu('fallo', 'nunca')), mil(so('fallo', 'nunca')) + ' · fallaron, o el proveedor nunca los entrega', st.xgr === 'fallo'),
  ].join('');
  const pct = (m) => (m[1] ? m[2] / m[1] * 100 : 0);
  const zipListo = P.zip && P.zip.mes === st.xmes;
  const opc = x.por_mes.slice().reverse().map((m) => `<option value="${m[0]}"${m[0] === st.xmes ? ' selected' : ''}>${nomMes(m[0])} · ${m[2]} de ${m[1]} XML</option>`).join('');
  return `<div class="kpis">${kpis}</div><div class="cuerpo"><div class="izq">
    <div class="fl"><input class="bus" placeholder="Documento o proveedor…" aria-label="Buscar XML faltante" value="${esc(st.xq)}"></div>
    <div class="caja"><table><thead><tr><th class="i">Fecha</th><th class="i">Documento</th><th class="i">Proveedor</th><th>Total S/</th><th class="i">Por qué no está</th></tr></thead><tbody class="xfilas">${tablaXml(P, st)}</tbody></table></div>
  </div><div class="panel"><h3>Descargar los XML</h3><div class="sub">Un mes por vez: lleva los XML y la lista de los que no trae.</div>
    <label class="lb">Mes <select data-a="xmes" aria-label="Mes del ZIP">${opc}</select></label>
    <button class="ir prim" data-a="zip" data-v="${st.xmes}"${st.zipEspera ? ' disabled' : ''}>${st.zipEspera ? 'Preparando el ZIP…' : '⬇ Preparar el ZIP'}</button>
    ${zipListo ? `<div class="causa ok">Listo: ${ent(P.zip.n)} XML y ${ent(P.zip.falt)} faltantes en «faltantes.xlsx». Bájalo con el botón de arriba.</div>` : ''}
    <button class="ir" data-a="pedir"${x.pedibles ? '' : ' disabled'}>Pedir ${ent(Math.min(x.pedibles, x.tope))} XML${x.pedibles > x.tope ? ' de ' + ent(x.pedibles) : ''}</button>
    ${P.aviso ? `<p class="nota">${esc(P.aviso)}</p>` : ''}
    <p class="tit">XML bajados, mes a mes</p>
    <div class="xmes">${x.por_mes.map((m) => `<i style="height:${pct(m).toFixed(0)}%" title="${esc(nomMes(m[0]) + ': ' + m[2] + ' de ' + m[1])}"></i>`).join('')}</div>
    <div class="xeje">${x.por_mes.map((m) => `<span>${MESES[+m[0].slice(4) - 1].slice(0, 1)}</span>`).join('')}</div>
  </div></div>`;
}

function excelArchivo(P, p) {
  const el = P.meses.find((m) => m.p === p); if (!el) return;
  const cab = ['Fecha', 'Tipo', 'Documento', 'Proveedor', 'Base', 'IGV', 'No gravado', 'Total', 'Moneda', 'En la app', 'Mes en la app', 'Monto en la app'];
  bajar('sunat_presentado_' + p + '.xlsx', libro([{ nombre: nomMes(p), cabeza: cab, filas: el.filas.map((x) => [x[X.fecha], P.nom[x[X.tipo]] || x[X.tipo], x[X.doc], x[X.prov], x[X.base], x[X.igv], x[X.ng], x[X.total], x[X.mon], ETIQ[x[X.est]], x[X.pApp], x[X.app]]), decimales: 2 }]));
}

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  if (!data) return;
  let raiz = parentElement.querySelector('.sc');
  if (!raiz) { raiz = parentElement.ownerDocument.createElement('div'); raiz.className = 'sc'; parentElement.append(raiz); }
  // En `window` y no en la raíz: si Streamlit vuelve a montar la pieza, no se
  // pierde la pestaña ni lo elegido (una pieza no tiene iframe, regla #704).
  const st = window.__sunatControl || (window.__sunatControl = { tab: 'reg', cfil: null, csel: null, cmed: 'doc', cest: null, arch: false, archf: '', xgr: '', xq: '', xmes: null, espera: new Set(), zipEspera: false, n: 0 });
  raiz.__P = data;
  const P = data;
  if (!st.xmes && P.xml.por_mes.length) st.xmes = P.xml.por_mes[P.xml.por_mes.length - 1][0];
  Object.keys(P.verif).forEach((p) => st.espera.delete(p));
  if (P.zip && P.zip.mes === st.xmes) st.zipEspera = false;
  if (P.zip && P.zip.error) st.zipEspera = false;
  const enviar = (que, v) => { st.n += 1; setTriggerValue(que, Object.assign({ t: Date.now() + '-' + st.n }, v)); };

  const dibujar = () => {
    const scroll = [...raiz.querySelectorAll('.caja,.panel')].map((e) => e.scrollTop);
    const aviso = P.fallidos.length ? `<div class="causa ojo">SUNAT no respondió al actualizar ${P.fallidos.map((p) => nomMes(p).toLowerCase()).join(', ')}. Se muestran sus datos de la corrida anterior; se vuelve a intentar en la próxima. Sus cifras pueden estar incompletas.</div>` : '';
    raiz.innerHTML = `<div class="fl cab"><span class="seg ch" role="group" aria-label="Qué controlar">${[['reg', 'Documentos'], ['xml', 'XML']].map(([k, n]) => `<button class="${st.tab === k ? 'on' : ''}" data-a="tab" data-v="${k}">${n}</button>`).join('')}</span><span class="nota explica">SUNAT reúne una lista de tus comprobantes; lo presentado es esa lista, con lo que se agregó o corrigió.</span><span class="esp"></span><span class="nota">Revisado ${esc(fechaRevision(P.generado))}</span></div>${aviso}`
      + (st.tab === 'xml' ? dibujarXml(P, st) : st.arch ? dibujarArchivo(P, st) : dibujarMeses(P, st));
    [...raiz.querySelectorAll('.caja,.panel')].forEach((e, i) => { if (scroll[i]) e.scrollTop = scroll[i]; });
  };

  if (!raiz.__listo) {
    raiz.__listo = true;
    raiz.addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-a]'); if (!b || b.tagName === 'SELECT') return;
      const a = b.dataset.a, v = b.dataset.v, Q = raiz.__P;
      if (a === 'tab') st.tab = v;
      else if (a === 'fil') { st.cfil = !v || st.cfil === v ? null : v; st.csel = null; st.cest = null; }
      else if (a === 'med') st.cmed = v;
      else if (a === 'mes') { st.csel = v; st.cest = null; }
      else if (a === 'grupo') st.cest = v;
      else if (a === 'archivo') { st.arch = true; st.csel = v; st.archf = ''; }
      else if (a === 'volver') st.arch = false;
      else if (a === 'archf') st.archf = v;
      else if (a === 'excel') { excelArchivo(Q, v); return; }
      else if (a === 'xgr') { st.xgr = v; }
      else if (a === 'verificar') { st.espera.add(v); enviar('verificar', { p: v }); }
      else if (a === 'zip') { st.zipEspera = true; enviar('zip', { mes: v }); }
      else if (a === 'pedir') { enviar('pedir', {}); return; }
      else return;
      raiz.__dibujar();
    });
    raiz.addEventListener('change', (ev) => {
      if (ev.target.matches('select[data-a="xmes"]')) { st.xmes = ev.target.value; raiz.__dibujar(); }
    });
    // Buscar repinta sólo las filas: rehacer el input le quita el foco (#731).
    raiz.addEventListener('input', (ev) => {
      if (!ev.target.matches('.bus')) return;
      st.xq = ev.target.value;
      const t = raiz.querySelector('.xfilas'); if (t) t.innerHTML = tablaXml(raiz.__P, st);
    });
  }
  raiz.__dibujar = dibujar;
  raiz.classList.toggle('conzip', !!(P.zip && P.zip.n != null));
  // El mes abierto se consulta solo, una vez por sesión: es el único que puede
  // haber cambiado desde la madrugada, y no hace esperar a la primera pantalla.
  if (P.abierto && !P.verif[P.abierto] && !st.auto) {
    st.auto = true; st.espera.add(P.abierto);
    setTimeout(() => enviar('verificar', { p: P.abierto }), 300);
  }
  dibujar();
}
