// Ventas > Meseros (#719). Pedidos y pagos ya separados por Python (#517).
// La búsqueda y la ficha no cambian la población del pozo ni la planilla.
const MP={ped:0,mesero:1,dia:2,hora:3,turno:4,venta:5,items:6,pax:7,propina:8,tarjeta:9,efectivo:10,desc:11,doc:12};
const MIT={ped:0,mesero:1,dia:2,turno:3,prod:4,grupo:5,cant:6,venta:7};
const MDIA=864e5, MCORTES=[.001,5,9.5,10.5,15,Infinity];
const mdia=s=>Date.parse(s+'T00:00:00Z')/MDIA;
const miso=n=>new Date(n*MDIA).toISOString().slice(0,10);
const mfecha=n=>{const s=miso(n);return `${s.slice(8)}/${s.slice(5,7)}/${s.slice(0,4)}`;};
const mdm=n=>mfecha(n).slice(0,5);
const msem=n=>(new Date(n*MDIA).getUTCDay()+6)%7;
const mesc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const mok=v=>v!=null&&Number.isFinite(v);
const mfmt=[0,1,2,3].map(d=>new Intl.NumberFormat('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}));
const mnum=(v,d=0)=>mok(v)?mfmt[d].format(v):'—';
const msol=(v,d=2)=>mok(v)?`${v<0?'−':''}S/ ${mnum(Math.abs(v),d)}`:'—';
const mdiv=(a,b)=>b>0?a/b:null;
const mpct=v=>mok(v)?`${mnum(v*100,1)}%`:'—';
const mvar=(a,b)=>b>0?a/b-1:null;
const mdelta=v=>mok(v)?`${v>0?'+':v<0?'−':''}${mnum(Math.abs(v)*100)}%`:'sin base';
const mcolor=v=>!mok(v)||Math.abs(v)<1e-8?'var(--text-secondary)':v>0?'var(--success)':'var(--danger)';
const msum=(rs,k)=>rs.reduce((s,r)=>s+(r[k]||0),0);
function mleer(P){
  const base=mdia(P.base),leer=rows=>rows.map(r=>({id:r[MP.ped],ms:r[MP.mesero],f:base+r[MP.dia],hora:r[MP.hora],turn:r[MP.turno],
    venta:r[MP.venta],items:r[MP.items],personas:r[MP.pax],propina:r[MP.propina],tarjeta:r[MP.tarjeta],solo_efectivo:r[MP.efectivo],desc:r[MP.desc],doc:r[MP.doc]}));
  const items=P.items.map(r=>({ped:r[MIT.ped],ms:r[MIT.mesero],f:base+r[MIT.dia],turn:r[MIT.turno],prod:r[MIT.prod],grupo:r[MIT.grupo],cant:r[MIT.cant],venta:r[MIT.venta]}));
  return {P,rows:leer(P.actual),prev:leer(P.previo),items,cache:new Map()};
}
const mturno=(B,rs,t)=>t==='Todo el día'?rs:rs.filter(r=>B.P.turnos[r.turn]===t);
function mresumen(rows){
  const m=new Map();for(const r of rows){if(!m.has(r.ms))m.set(r.ms,{id:r.ms,dias:0,mesas:0,personas:0,venta:0,items:0,propina:0,tarjeta:0,sin_propina:0,solo_efectivo:0,days:new Set()});
    const a=m.get(r.ms);for(const k of ['venta','items','propina','personas'])a[k]+=r[k];
    if(r.venta>0){a.days.add(r.f);a.mesas++;if(r.tarjeta){a.tarjeta++;if(r.propina<=0)a.sin_propina++;}if(r.solo_efectivo)a.solo_efectivo++;}}
  return [...m.values()].map(r=>{r.dias=r.days.size;delete r.days;return r;});
}
function mpozo(B,rows){
  const m=new Map(), grupos=new Map();
  for(const r of rows){if(r.ms===B.P.sin_mesero)continue;const k=`${r.f}|${r.turn}|${r.ms}`;
    if(!m.has(k))m.set(k,{dia:r.f,turno:r.turn,mesero:r.ms,mesas:0,propia:0});const a=m.get(k);a.mesas+=r.venta>0?1:0;a.propia+=r.propina;}
  for(const a of m.values()){const k=`${a.dia}|${a.turno}`;if(!grupos.has(k))grupos.set(k,{pozo:0,n:0});const g=grupos.get(k);g.pozo+=a.propia;if(a.mesas>0)g.n++;}
  return [...m.values()].map(a=>{const g=grupos.get(`${a.dia}|${a.turno}`);return {...a,...g,parte:g.n?(a.mesas>0?g.pozo/g.n:0):a.propia};})
    .sort((a,b)=>a.dia-b.dia||a.turno-b.turno||a.mesero-b.mesero);
}
function mplanilla(z,modo){
  const dias=[...new Set(z.map(r=>r.dia))].sort((a,b)=>a-b),m=new Map(),campo=modo==='Pozo común'?'parte':'propia';
  for(const r of z){if(!m.has(r.mesero))m.set(r.mesero,{id:r.mesero,valores:[],mesas:[],total:0,propia:0,diferencia:0});const a=m.get(r.mesero),i=dias.indexOf(r.dia);
    a.valores[i]=(a.valores[i]||0)+r[campo];a.mesas[i]=(a.mesas[i]||0)+r.mesas;a.total+=r[campo];a.propia+=r.propia;}
  const filas=[...m.values()].map(r=>({...r,valores:dias.map((_,i)=>r.valores[i]||0),mesas:dias.map((_,i)=>r.mesas[i]||0),diferencia:r.total-r.propia})).sort((a,b)=>b.total-a.total||a.id-b.id);
  return {dias,filas,totales:dias.map((_,i)=>filas.reduce((s,r)=>s+r.valores[i],0)),total:msum(filas,'total')};
}
function mdistribucion(B,rows){
  const m=new Map();for(const r of rows){if(!r.tarjeta||r.venta<=0||r.ms===B.P.sin_mesero)continue;const p=100*r.propina/r.venta;if(p<=-.01)continue;
    const i=MCORTES.findIndex(x=>p<=x);if(!m.has(r.ms))m.set(r.ms,Array(6).fill(0));m.get(r.ms)[i]++;}
  return [...m].map(([id,tramos])=>({id,tramos}));
}
function mvendido(B,items){
  const agrupar=rs=>{const m=new Map();for(const r of rs){if(!m.has(r.prod))m.set(r.prod,{id:r.prod,u:0,venta:0});const a=m.get(r.prod);a.u+=r.cant;a.venta+=r.venta;}return [...m.values()].sort((a,b)=>b.u-a.u||b.venta-a.venta||a.id-b.id);};
  const gs=new Map();for(const r of items)gs.set(r.grupo,(gs.get(r.grupo)||0)+r.cant);
  return {platos:agrupar(items.filter(r=>B.P.grupos[r.grupo]==='Alimentos')).slice(0,8),bebidas:agrupar(items.filter(r=>/bebida|vino|espumante/i.test(B.P.grupos[r.grupo]))).slice(0,5),grupos:[...gs].filter(([,u])=>u>0).sort((a,b)=>b[1]-a[1]||a[0]-b[0])};
}
function mequipo(B,turno){
  if(B.cache.has(turno))return B.cache.get(turno);
  const rows=mturno(B,B.rows,turno),prev=mturno(B,B.prev,turno),R=mresumen(rows),R0=mresumen(prev),z=mpozo(B,rows);
  const rep=new Map();for(const r of z){if(!rep.has(r.mesero))rep.set(r.mesero,{propia:0,pozo:0,diferencia:0});const a=rep.get(r.mesero);a.propia+=r.propia;a.pozo+=r.parte;a.diferencia=a.pozo-a.propia;}
  const team=R.filter(r=>r.id!==B.P.sin_mesero),old=R0.filter(r=>r.id!==B.P.sin_mesero),tot=rs=>Object.fromEntries(['mesas','personas','venta','items','propina','tarjeta','sin_propina','solo_efectivo'].map(k=>[k,msum(rs,k)]));
  const rank=team.filter(r=>r.mesas>0).sort((a,b)=>b.propina-a.propina||a.id-b.id);
  const compare=Object.fromEntries(['Almuerzo','Cena'].map(t=>[t,mresumen(mturno(B,B.rows,t))]));
  const out={rows,prev,R,R0,z,rep,team,rank,t:tot(team),t0:tot(old),compare,distribucion:mdistribucion(B,rows)};B.cache.set(turno,out);return out;
}
function mscope(B,T,st){
  const match=r=>(st.ms===-1?r.ms!==B.P.sin_mesero:r.ms===st.ms)&&(!st.celda||((st.celda.f==null||r.f===st.celda.f)&&(st.celda.turn==null||r.turn===st.celda.turn)))&&(st.weekday==null||msem(r.f)===st.weekday);
  const all=T.rows.filter(match),xs=all.filter(r=>{
    if(st.filtro==='Tarjeta sin propina')return r.venta>0&&r.tarjeta&&r.propina<=0;
    if(st.filtro==='Con descuento')return r.desc>0;
    if(st.filtro==='Sin descuento')return r.desc<=0;
    if(st.filtro==='Sólo efectivo')return r.solo_efectivo;
    return true;
  });
  const ids=new Set(xs.map(r=>r.id)),items=mturno(B,B.items,st.turno).filter(r=>ids.has(r.ped)&&(st.ms===-1||r.ms===st.ms));
  return {all,rows:xs,items,vendido:mvendido(B,items)};
}
function mhistoria(B,st){
  const m=new Map();for(const [mes,ms,turn,p,v] of B.P.historia){if(ms===B.P.sin_mesero||(st.turno!=='Todo el día'&&B.P.turnos[turn]!==st.turno))continue;
    if(!m.has(mes))m.set(mes,{mes,propina:0,venta:0,equipo:0});const a=m.get(mes);a.equipo+=p;a.venta+=v;if(st.ms===-1||ms===st.ms)a.propina+=p;}
  return [...m.values()].sort((a,b)=>a.mes.localeCompare(b.mes));
}
window.__mesCalc={leer:mleer,resumen:mresumen,pozo:mpozo,planilla:mplanilla,distribucion:mdistribucion,vendido:mvendido,equipo:mequipo,scope:mscope,historia:mhistoria};

function minicial(){return {turno:'Todo el día',modo:'Por mesero',ms:null,q:'',orden:'propina',dir:-1,mas:false,tab:'Propinas',filtro:'Todos',celda:null,weekday:null,pedido:null,limite:150,mapa:'Por mesa',ayuda:false};}
const mboton=(a,v,t,on=false,tip='')=>`<button type="button" data-acc="${a}" data-v="${mesc(v)}" class="${on?'on':''}" aria-pressed="${on}" title="${mesc(tip)}">${mesc(t)}</button>`;
const msegmento=(a,ops,v)=>`<div class="ms-seg" role="group">${ops.map(x=>mboton(a,x,x,x===v)).join('')}</div>`;
const mkpi=(n,v,sub='',tip='',color='')=>`<div class="ms-kpi" title="${mesc(tip)}"><span>${mesc(n)}</span><strong${color?` style="color:${color}"`:''}>${mesc(v)}</strong><small>${mesc(sub)}</small></div>`;
const mtabla=(heads,rows,cls='')=>`<div class="ms-scroll ${cls}"><table><thead><tr>${heads.map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
function mlimpiar(st){st.celda=null;st.weekday=null;st.pedido=null;st.filtro='Todos';st.limite=150;}
function mpintar(G){
  const {B,st,root}=G,T=mequipo(B,st.turno);G.T=T;
  if(st.ms==null||st.ms!==-1&&!T.R.some(r=>r.id===st.ms))st.ms=T.rank[0]?.id??-1;
  G.S=mscope(B,T,st);G.plan=mplanilla(T.z,st.modo);
  const oldScroll=root.querySelector('.ms-pay-scroll'),left=oldScroll?.scrollLeft||0;
  const focus=root.getRootNode().activeElement,search=focus?.matches?.('[data-acc="buscar"]'),cursor=search?focus.selectionStart:0;
  const t=T.t,t0=T.t0,pct=mdiv(t.propina,t.venta),vp=B.P.hay_anterior?mvar(t.propina,t0.propina):null;
  const corte=B.P.corte_ms!=null&&B.P.corte_ms<20*3600e3?` · último día hasta ${String(Math.floor(B.P.corte_ms/3600e3)).padStart(2,'0')}:${String(Math.floor(B.P.corte_ms/60000)%60).padStart(2,'0')}`:'';
  const sin=T.R.find(r=>r.id===B.P.sin_mesero);
  root.innerHTML=`<section class="ms-card ms-overview"><div class="ms-head ms-native-space"><h3>Propinas por mesero</h3>${msegmento('turno',['Todo el día','Almuerzo','Cena'],st.turno)}${mboton('ayuda','','?',st.ayuda,'Cuentas y alcance')}</div>
    <div class="ms-caption">${B.P.rango.map(s=>mfecha(mdia(s))).join('–')} · comparación: ${B.P.anterior.map(s=>mfecha(mdia(s))).join('–')}${corte}${!B.P.hay_anterior?' · sin datos anteriores disponibles':''}</div>
    <div class="ms-kpis">${mkpi('Propinas',msol(t.propina,0),mdelta(vp),'Propina registrada; sin «Sin mesero»',mcolor(vp))}${mkpi('% de la venta',mpct(pct),B.P.hay_anterior&&t0.venta>0?`${mnum((pct-t0.propina/t0.venta)*100,1)} pp vs anterior`:'Propina / venta')}${mkpi('Por mesa',msol(mdiv(t.propina,t.mesas)),`${t.mesas} mesas`)}${mkpi('Por persona',msol(mdiv(t.propina,t.personas)),`${mnum(t.personas)} adultos`)}<button class="ms-kpi ms-kpi-button" data-acc="sinpropina">${mkpi('Tarjeta sin propina',mpct(mdiv(t.sin_propina,t.tarjeta)),`${t.sin_propina} de ${t.tarjeta} · ver mesas`)}</button>${mkpi('Sólo efectivo',`${t.solo_efectivo} mesas`,'Propina no registrada en POS')}</div>
    <div class="ms-panes"><div class="ms-list"><div class="ms-toolbar"><input type="search" data-acc="buscar" aria-label="Buscar mesero en la lista" placeholder="Buscar mesero…" value="${mesc(st.q)}">${mboton('mas','','Más datos',st.mas)}${mboton('equipo','','Equipo',st.ms===-1)}</div>${mrank(G)}<div class="ms-caption">Comparación Almuerzo/Cena: % de la venta de cada turno. La búsqueda acota la lista.</div>${sin?.mesas?`<div class="ms-caption">${mboton('sinmesero','','Sin mesero: '+sin.mesas+' pedidos')} · ${msol(sin.venta,0)}</div>`:''}</div>${mficha(G)}</div>
    ${st.ayuda?`<div class="ms-help">${mboton('ayuda','','Cerrar')}<p>Mesas = pedidos con venta; personas = adultos. Cada ítem suma venta una vez y cada pago suma propina una vez. El día es el del comprobante.</p><p>La propina se registra con tarjeta. Efectivo puede incluir una propina que el POS no registra. El % usa la venta de la mesa; los descuentos se explican en la ficha.</p><p>Pozo común: partes iguales por día y turno entre meseros con al menos una mesa. Es la regla supuesta de esta vista. El rango y el turno fijan el reparto; búsqueda, selección y filtros de ficha son análisis.</p><p>La comparación conserva los mismos días del mes anterior y la hora de corte del último día. Las muestras y los importes describen lo registrado.</p></div>`:''}
  </section>${mplan(G)}`;
  const sc=root.querySelector('.ms-pay-scroll');if(sc)sc.scrollLeft=left;
  if(search){const e=root.querySelector('[data-acc="buscar"]');e.focus({preventScroll:true});e.setSelectionRange(cursor,cursor);}
  msvg(G);
}
function mrank(G){
  const {B,st,T}=G;
  const rs=T.rank.filter(r=>B.P.meseros[r.id].toLocaleLowerCase('es').includes(st.q.toLocaleLowerCase('es'))).map(r=>({...r,tasa:mdiv(r.propina,r.venta),por_mesa:mdiv(r.propina,r.mesas),sin_pct:mdiv(r.sin_propina,r.tarjeta),var:B.P.hay_anterior?mvar(r.propina,T.R0.find(a=>a.id===r.id)?.propina):null,pozo:T.rep.get(r.id)?.pozo}));
  rs.sort((a,b)=>((a[st.orden]??-Infinity)-(b[st.orden]??-Infinity))*st.dir||a.id-b.id);
  const cols=[['id','Mesero'],['propina','Propina'],['tasa','% venta'],['mesas','Mesas'],['por_mesa','Por mesa'],['sin_pct','Sin prop.'],['var','vs anterior'],...(st.mas?[['dias','Días'],['personas','Personas'],['items','Productos'],['venta','Venta'],['pozo','Pozo común']]:[])];
  return mtabla(cols.map(([k,v])=>mboton('orden',k,v,st.orden===k)),rs.map(r=>{
    const ant=T.R0.find(a=>a.id===r.id),rep=T.rep.get(r.id),v=B.P.hay_anterior?mvar(r.propina,ant?.propina):null;
    const turnos=['Almuerzo','Cena'].map(t=>{const a=T.compare[t].find(a=>a.id===r.id);return `${t==='Almuerzo'?'Alm.':'Cena'} ${mpct(a?mdiv(a.propina,a.venta):null)}`;}).join(' · ');
    return `<tr data-acc="mesero" data-v="${r.id}" tabindex="0" role="button" aria-label="Ver ${mesc(B.P.meseros[r.id])}" class="${r.id===st.ms?'chosen':''}"><td class="ms-sticky"><b>${mesc(B.P.meseros[r.id])}</b><small>${turnos}</small></td><td class="ms-num">${msol(r.propina)}</td><td class="ms-num">${mpct(r.tasa)}</td><td class="ms-num">${r.mesas}</td><td class="ms-num">${msol(r.por_mesa)}</td><td class="ms-num">${mpct(mdiv(r.sin_propina,r.tarjeta))}</td><td class="ms-num" style="color:${mcolor(v)}">${!B.P.hay_anterior?'—':v==null?'nuevo':mdelta(v)}</td>${st.mas?`<td>${r.dias}</td><td>${mnum(r.personas)}</td><td>${mnum(r.items)}</td><td>${msol(r.venta,0)}</td><td>${msol(rep?.pozo)}</td>`:''}</tr>`;
  }), 'ms-rank-scroll');
}
function mficha(G){
  const {B,st,S,T}=G,nom=st.ms===-1?'Equipo':B.P.meseros[st.ms];
  const contexto=[st.celda?.f!=null?mfecha(st.celda.f):'',st.celda?.turn!=null?B.P.turnos[st.celda.turn]:'',st.weekday!=null?['lunes','martes','miércoles','jueves','viernes','sábado','domingo'][st.weekday]:''].filter(Boolean).join(' · ');
  let body='';
  if(st.pedido!=null){
    const r=S.rows.find(r=>r.id===st.pedido);if(!r)st.pedido=null;
    else {const its=S.items.filter(i=>i.ped===r.id);body=`<div class="ms-toolbar">${mboton('volver','','‹ Mesas')}<b>Pedido ${mesc(B.P.pedidos[r.id])}</b></div><p class="ms-caption">${mesc(B.P.docs[r.doc]||'Sin número de comprobante')} · ${mfecha(r.f)} · ${B.P.turnos[r.turn]}</p><div class="ms-kpis ms-small-kpis">${mkpi('Venta',msol(r.venta))}${mkpi('Propina',msol(r.propina),mpct(mdiv(r.propina,r.venta)))}${mkpi('Descuento',msol(r.desc))}</div>`+
      mtabla(['Producto','Unidades','Venta'],its.slice(0,st.limite).map(i=>`<tr><td>${mesc(B.P.prods[i.prod])}</td><td>${mnum(i.cant,2)}</td><td>${msol(i.venta)}</td></tr>`));}
  }
  if(!body&&st.tab==='Propinas'){
    const distrib=mdistribucion(B,S.all),selected=distrib;
    const counts=Array(6).fill(0),team=Array(6).fill(0);for(const r of selected)r.tramos.forEach((n,i)=>counts[i]+=n);for(const r of T.distribucion)r.tramos.forEach((n,i)=>team[i]+=n);
    G.tramos={counts,team};
    body='<h4>Cómo dejan propina sus mesas</h4><div class="ms-tramos"></div><p class="ms-caption">Mesas con tarjeta por tramo de propina / venta. La marca es el equipo.</p>';
    if(B.P.hay_descuento){body+='<h4>Con y sin descuento</h4>'+mtabla(['Mesas','N','% venta','% antes desc.'],[true,false].map(con=>{const rr=S.all.filter(r=>r.venta>0&&(r.desc>0)===con),tip=msum(rr,'propina'),v=msum(rr,'venta'),desc=msum(rr,'desc');return `<tr data-acc="descuento" data-v="${con?'Con descuento':'Sin descuento'}" tabindex="0" role="button"><td>${con?'Con descuento':'Sin descuento'}</td><td>${rr.length}</td><td>${mpct(mdiv(tip,v))}</td><td>${mpct(mdiv(tip,v+desc))}</td></tr>`;}));}
  }else if(!body&&st.tab==='Mesas'){
    const filtros=['Todos','Tarjeta sin propina',...(B.P.hay_descuento?['Con descuento','Sin descuento']:[]),'Sólo efectivo'];
    body=`<div class="ms-toolbar"><select data-acc="filtro" aria-label="Filtrar mesas">${filtros.map(v=>`<option${st.filtro===v?' selected':''}>${v}</option>`).join('')}</select>${mboton('excelmesas','','Excel mesas')}</div>`+
      mtabla(['Fecha','Pedido','Mesero','Venta','Propina','% venta','Pago'],[...S.rows].sort((a,b)=>b.f-a.f||b.hora-a.hora||b.id-a.id).slice(0,st.limite).map(r=>`<tr data-acc="pedido" data-v="${r.id}" tabindex="0" role="button"><td>${mdm(r.f)}</td><td title="${mesc(B.P.docs[r.doc])}">${mesc(B.P.pedidos[r.id])}</td><td>${mesc(B.P.meseros[r.ms])}</td><td>${msol(r.venta)}</td><td>${msol(r.propina)}</td><td>${mpct(mdiv(r.propina,r.venta))}</td><td>${r.tarjeta?'Tarjeta':r.solo_efectivo?'Efectivo':'Otro'}${r.desc>0?' · desc.':''}</td></tr>`),'ms-mesas-scroll')+`<div class="ms-caption">${S.rows.length} pedidos y ajustes · clic para ver el comprobante y sus ítems.</div>`;
  }else if(!body&&st.tab==='12 meses'){
    G.meses=mhistoria(B,st);body='<h4>Propina por mes</h4><div class="ms-legend"><span><i class="ms-own"></i>Seleccionado</span><span><i class="ms-team"></i>Equipo</span></div><div class="ms-meses"></div><p class="ms-caption">El asterisco marca el último mes hasta la fecha del rango.</p>';
    if(!B.P.hay_historia)body='<p class="ms-empty">No se pudo cargar el histórico. Reintentá con la fecha o el refresco de datos.</p>';
  }else if(!body){
    const v=S.vendido;body=`<div class="ms-chips">${v.grupos.map(([g,q])=>`<span>${mesc(B.P.grupos[g]||'Sin grupo')} · ${mnum(q)} u</span>`).join('')}</div>`+
      mtabla(['Producto','Unidades','Venta'],[...v.platos.map(r=>({...r,tipo:'Plato'})),...v.bebidas.map(r=>({...r,tipo:'Bebida'}))].map(r=>`<tr><td>${mesc(B.P.prods[r.id])}<small>${r.tipo}</small></td><td>${mnum(r.u,2)}</td><td>${msol(r.venta,0)}</td></tr>`));
  }
  return `<div class="ms-ficha"><div class="ms-toolbar"><h4>${mesc(nom)}</h4>${contexto?mboton('limpiar','','Quitar selección'):''}</div>${contexto?`<div class="ms-caption">${contexto}</div>`:''}${msegmento('tab',['Propinas','Mesas','12 meses','Lo que vendió'],st.tab)}${body}</div>`;
}
function mplan(G){
  const {B,st,T,plan}=G,ultimo=B.P.rango[0].slice(0,4)!==B.P.rango[1].slice(0,4),col=st.modo==='Pozo común'?'parte':'propia';
  if(!plan.filas.length)return '<section class="ms-card ms-pay"><h3>Planilla de propinas</h3><p class="ms-empty">Sin meseros con registros en este turno.</p></section>';
  const max=Math.max(1,...plan.filas.flatMap(r=>r.valores));
  const color=v=>`color-mix(in srgb,var(--accent) ${Math.round(5+Math.max(0,v)/max*40)}%,var(--bg-card))`;
  const fila=r=>`<tr><td class="ms-sticky">${mesc(B.P.meseros[r.id])}</td>${plan.dias.map((d,i)=>{const v=r.valores[i],con=r.mesas[i]>0||v!==0;return `<td style="background:${color(v)}">${mboton('celda',`${r.id}|${d}|`,con?mnum(v,2):'·',st.ms===r.id&&st.celda?.f===d,`${B.P.meseros[r.id]} · ${mfecha(d)}: ${msol(v)} · ${r.mesas[i]} mesas`)}</td>`;}).join('')}<td class="ms-num ms-total">${msol(r.total)}</td>${st.modo==='Pozo común'?`<td class="ms-num" style="color:${mcolor(r.diferencia)}">${msol(r.diferencia)}</td>`:''}</tr>`;
  const turns=[...new Set(T.z.map(r=>r.turno))].sort((a,b)=>a-b);
  const bandas=turns.map(t=>`<tr class="ms-band"><td class="ms-sticky">Equipo · ${mesc(B.P.turnos[t])}</td>${plan.dias.map(d=>{const xs=T.z.filter(r=>r.dia===d&&r.turno===t),v=msum(xs,col);return `<td>${xs.length?mboton('celda',`-1|${d}|${t}`,mnum(v,2),false,`${mfecha(d)} · ${B.P.turnos[t]} · ver mesas del equipo`):'·'}</td>`;}).join('')}<td>${msol(msum(T.z.filter(r=>r.turno===t),col))}</td>${st.modo==='Pozo común'?'<td></td>':''}</tr>`).join('');
  const tabla=mtabla(['Mesero',...plan.dias.map(d=>`${['lun','mar','mié','jue','vie','sáb','dom'][msem(d)]}<br>${ultimo?mfecha(d):mdm(d)}`),'Total',...(st.modo==='Pozo común'?['Diferencia']:[])],[...plan.filas.map(fila),`<tr class="ms-total"><td class="ms-sticky">Total del día</td>${plan.totales.map(v=>`<td class="ms-num">${mnum(v,2)}</td>`).join('')}<td>${msol(plan.total)}</td>${st.modo==='Pozo común'?'<td>0.00</td>':''}</tr>`,bandas],'ms-pay-scroll');
  return `<section class="ms-card ms-pay"><div class="ms-head"><h3>Planilla de propinas · ${mesc(st.turno)}</h3>${msegmento('modo',['Por mesero','Pozo común'],st.modo)}${mboton('excelplan','','Excel planilla')}</div>
    <div class="ms-caption">${st.modo==='Pozo común'?'Partes iguales por día y turno entre meseros con mesas; regla supuesta de la vista.':'Propina propia por día del comprobante.'} Un clic en una celda abre sus mesas en la ficha.</div>${tabla}
    <div class="ms-toolbar"><h4>Día de semana × turno</h4>${msegmento('mapa',['Por mesa','% venta','Propinas'],st.mapa)}</div>${mmapa(G,turns)}
    <div class="ms-caption">La planilla y su Excel incluyen el rango y turno completos. Cada pago se conserva con su importe; el pozo mantiene los decimales de la división.</div></section>`;
}
function mmapa(G,turns){
  const {T,st,B}=G;const cells=turns.map(turn=>Array.from({length:7},(_,w)=>{const rs=T.rows.filter(r=>r.ms!==B.P.sin_mesero&&r.turn===turn&&msem(r.f)===w),t=mresumen(rs),p=msum(t,'propina'),v=msum(t,'venta'),n=msum(t,'mesas');return {turn,w,p,v,n,val:st.mapa==='Propinas'?p:st.mapa==='% venta'?mdiv(p,v):mdiv(p,n)};}));
  const max=Math.max(1e-9,...cells.flat().map(r=>r.val||0));
  return `<div class="ms-map"><table><thead><tr><th>Turno</th>${['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'].map(t=>`<th>${t}</th>`).join('')}</tr></thead><tbody>${cells.map(rs=>`<tr><th>${mesc(B.P.turnos[rs[0].turn])}</th>${rs.map(r=>`<td style="background:color-mix(in srgb,var(--accent) ${Math.round(5+(r.val||0)/max*40)}%,var(--bg-card))">${mboton('weekday',`${r.w}|${r.turn}`,r.n?(st.mapa==='% venta'?mpct(r.val):msol(r.val,st.mapa==='Propinas'?0:2)):'—',st.weekday===r.w&&st.celda?.turn===r.turn,`${r.n} mesas · ${msol(r.p)} de propina`)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function msvg(G){
  const {root,B,st}=G,tr=root.querySelector('.ms-tramos');
  if(tr&&G.tramos){const {counts,team}=G.tramos,n=counts.reduce((a,b)=>a+b,0),nt=team.reduce((a,b)=>a+b,0),w=tr.clientWidth||430,h=154,L=72,R=60,span=w-L-R;
    tr.innerHTML=n?`<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${counts.map((v,i)=>{const p=n?v/n:0,t=nt?team[i]/nt:0,y=i*24+10;return `<text class="ms-axis" x="${L-8}" y="${y+10}" text-anchor="end">${mesc(B.P.tramos[i])}</text><rect x="${L}" y="${y}" width="${span*p}" height="14" rx="2" fill="var(--accent)"/><line x1="${L+span*t}" x2="${L+span*t}" y1="${y-2}" y2="${y+16}" stroke="var(--text-primary)" stroke-width="2"/><text class="ms-value" x="${L+span*p+5}" y="${y+11}">${mpct(p)} · ${v}</text>`;}).join('')}</svg>`:'<p class="ms-empty">Sin mesas con tarjeta para estos criterios.</p>';}
  const el=root.querySelector('.ms-meses');if(el){const rs=G.meses||[],w=el.clientWidth||430,h=235,L=35,T=25,bot=h-28;if(!rs.length){el.innerHTML='<p class="ms-empty">Sin datos del histórico para este turno.</p>';return;}
    const min=Math.min(0,...rs.flatMap(r=>[r.propina,r.equipo])),max=Math.max(1,...rs.flatMap(r=>[r.propina,r.equipo])),y=v=>bot-(v-min)/(max-min)*(bot-T),step=(w-L-9)/rs.length;
    el.innerHTML=`<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${rs.map((r,i)=>{const x=L+step*i+4,an=Math.max(3,step-8),parcial=r.mes===B.P.rango[1].slice(0,7),txt=['ene','feb','mar','abr','may','jun','jul','ago','set','oct','nov','dic'][+r.mes.slice(5)-1]+(parcial?'*':'');return `<rect x="${x}" y="${Math.min(y(0),y(r.equipo))}" width="${an}" height="${Math.abs(y(0)-y(r.equipo))}" fill="var(--border-lavender)"/><rect x="${x+an*.18}" y="${Math.min(y(0),y(r.propina))}" width="${an*.64}" height="${Math.abs(y(0)-y(r.propina))}" fill="var(--accent)"/><text class="ms-axis" x="${x+an/2}" y="${h-9}" text-anchor="middle">${txt}</text><rect x="${L+i*step}" y="0" width="${step}" height="${h}" fill="transparent"><title>${r.mes}: seleccionado ${msol(r.propina)}, equipo ${msol(r.equipo)}, ${mpct(mdiv(r.equipo,r.venta))} de la venta</title></rect>`;}).join('')}<line x1="${L}" x2="${w-3}" y1="${y(0)}" y2="${y(0)}" stroke="var(--border)"/></svg>`;}
}
function mexcelPlan(G){
  const {B,st}=G,b64=B.P.libros[`${st.turno}|${st.modo}`];if(!b64)return;
  const data=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));bajar(`Propinas_${archivo(st.turno)}_${archivo(st.modo)}.xlsx`,new Blob([data],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}));
}
function mexcelMesas(G){
  const {B,S,st}=G,contexto=[['Desde',B.P.rango[0]],['Hasta',B.P.rango[1]],['Turno',st.turno],['Mesero',st.ms===-1?'Equipo':B.P.meseros[st.ms]],['Filtro de mesas',st.filtro],['Fecha elegida',st.celda?.f!=null?miso(st.celda.f):'Todo el rango'],['Turno elegido',st.celda?.turn!=null?B.P.turnos[st.celda.turn]:'Todos'],['Día de semana',st.weekday==null?'Todos':['lun','mar','mié','jue','vie','sáb','dom'][st.weekday]]];
  for(const [k,vs] of Object.entries(B.P.filtros))contexto.push([k,vs.length?vs.join(' / '):'Todos']);
  bajar('Mesas_propinas.xlsx',libro([{nombre:'Mesas',cabeza:['Fecha','Pedido','Comprobantes','Mesero','Turno','Venta','Personas','Propina','Propina (% venta)','Descuento','Pago'],filas:S.rows.map(r=>[mfecha(r.f),B.P.pedidos[r.id],B.P.docs[r.doc],B.P.meseros[r.ms],B.P.turnos[r.turn],r.venta,r.personas,r.propina,r.venta>0?r.propina/r.venta*100:null,r.desc,r.tarjeta?'Tarjeta':r.solo_efectivo?'Efectivo':'Otro'])},{nombre:'Contexto',cabeza:['Dato','Valor'],filas:contexto}]));
}
function menlazar(G){
  const {root,st}=G;
  root.addEventListener('click',ev=>{const e=ev.target.closest('[data-acc]');if(!e||!root.contains(e)||e.matches('input,select'))return;const {acc,v}=e.dataset;
    if(acc==='turno'){st.turno=v;mlimpiar(st);}
    else if(acc==='modo'||acc==='mapa')st[acc]=v;
    else if(acc==='mesero'){st.ms=+v;mlimpiar(st);}
    else if(acc==='equipo'){st.ms=-1;mlimpiar(st);}
    else if(acc==='sinmesero'){st.ms=G.B.P.sin_mesero;mlimpiar(st);st.tab='Mesas';}
    else if(acc==='sinpropina'){st.ms=-1;mlimpiar(st);st.tab='Mesas';st.filtro='Tarjeta sin propina';}
    else if(acc==='tab'){st.tab=v;st.pedido=null;st.limite=150;if(v!=='Mesas')st.filtro='Todos';if(v==='12 meses')mlimpiar(st);}
    else if(acc==='descuento'){st.tab='Mesas';st.filtro=v;st.pedido=null;}
    else if(acc==='pedido')st.pedido=+v;
    else if(acc==='volver')st.pedido=null;
    else if(acc==='limpiar')mlimpiar(st);
    else if(acc==='mas')st.mas=!st.mas;
    else if(acc==='ayuda')st.ayuda=!st.ayuda;
    else if(acc==='orden'){if(v==='id'){st.orden='id';st.dir=st.dir===1?-1:1;}else if(['propina','tasa','mesas','por_mesa','sin_pct','dias','personas','items','venta','var','pozo'].includes(v)){st.dir=st.orden===v?-st.dir:-1;st.orden=v;}}
    else if(acc==='celda'){const [m,f,t]=v.split('|');st.ms=+m;mlimpiar(st);st.celda={f:+f,turn:t===''?null:+t};st.tab='Mesas';}
    else if(acc==='weekday'){const [w,t]=v.split('|');st.ms=-1;mlimpiar(st);st.weekday=+w;st.celda={f:null,turn:+t};st.tab='Mesas';}
    else if(acc==='excelplan'){mexcelPlan(G);return;}
    else if(acc==='excelmesas'){mexcelMesas(G);return;}
    else return;
    mpintar(G);
    if(['celda','weekday','sinpropina','sinmesero'].includes(acc))root.querySelector('.ms-ficha')?.scrollIntoView({block:'nearest',behavior:'smooth'});
  });
  root.addEventListener('input',ev=>{if(ev.target.dataset.acc==='buscar'){st.q=ev.target.value;mpintar(G);}});
  root.addEventListener('change',ev=>{if(ev.target.dataset.acc==='filtro'){st.filtro=ev.target.value;st.pedido=null;st.limite=150;mpintar(G);}});
  root.addEventListener('keydown',ev=>{if(ev.key==='Escape'){if(st.ayuda)st.ayuda=false;else st.pedido=null;mpintar(G);}const r=ev.target.closest('tr[data-acc]');if(r&&(ev.key==='Enter'||ev.key===' ')){ev.preventDefault();r.click();}});
  root.addEventListener('scroll',ev=>{const e=ev.target;if(e.matches('.ms-mesas-scroll')&&e.scrollTop+e.clientHeight>e.scrollHeight-70&&st.limite<G.S.rows.length){const y=e.scrollTop,x=e.scrollLeft;st.limite+=150;mpintar(G);const next=root.querySelector('.ms-mesas-scroll');next.scrollTop=y;next.scrollLeft=x;}},true);
}
window.__mesUI={inicial:minicial,pintar:mpintar};
export default function(component){
  const {data:P,parentElement}=component;if(!P)return;
  const old=window.__vtMes,st=old?.st||minicial();old?.observer?.disconnect();clearTimeout(old?.resizeTimer);
  if(old&&old.B.P.sello!==P.sello){const nombre=old.B.P.meseros[st.ms];st.ms=st.ms===-1?-1:P.meseros.indexOf(nombre);if(st.ms<0)st.ms=-1;mlimpiar(st);}
  let root=parentElement.querySelector('.msp');if(!root){root=document.createElement('div');root.className='msp';parentElement.appendChild(root);}
  const G={root,st,B:old?.B.P.sello===P.sello?old.B:mleer(P)};window.__vtMes=G;
  // Un remontaje sobre la misma raíz no acumula manejadores.
  if(old?.root===root){root.replaceWith(root.cloneNode(false));G.root=parentElement.querySelector('.msp');}
  menlazar(G);mpintar(G);let ancho=G.root.clientWidth;
  G.observer=new ResizeObserver(()=>{if(Math.abs(G.root.clientWidth-ancho)<2)return;ancho=G.root.clientWidth;clearTimeout(G.resizeTimer);G.resizeTimer=setTimeout(()=>{if(G.root.isConnected)msvg(G);},80);});G.observer.observe(G.root);
}
