// Ventas > Meseros (#719). Pedidos y pagos ya separados por Python (#517).
// La búsqueda y la ficha no cambian la población del pozo ni la planilla.
const MP={ped:0,mesero:1,dia:2,hora:3,turno:4,venta:5,items:6,pax:7,propina:8,tarjeta:9,efectivo:10,desc:11,doc:12};
const MIT={ped:0,mesero:1,dia:2,turno:3,prod:4,grupo:5,cant:6,venta:7,sub:8};
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
  const items=P.items.map(r=>({ped:r[MIT.ped],ms:r[MIT.mesero],f:base+r[MIT.dia],turn:r[MIT.turno],prod:r[MIT.prod],grupo:r[MIT.grupo],cant:r[MIT.cant],venta:r[MIT.venta],sub:r[MIT.sub]??0}));
  const carta=(P.carta||[]).map(r=>({prod:r[0],grupo:r[1],sub:r[2]}));
  return {P,rows:leer(P.actual),prev:leer(P.previo),items,carta,cache:new Map()};
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
// «Venta por mesero» (#852): lo vendido (grupo, subgrupo o plato) × mesero,
// con el turno de arriba y su propio filtro de grupo. Cada ítem una vez (#517).
// #853: Grupo y Subgrupo como columnas, filtro de subgrupo, «Precio unitario»
// (venta ÷ unidades de cada celda) y filas elegidas a mano («Solo elegidos»).
// #855: «Unidades y venta» (dos columnas por mesero), secciones por subgrupo,
// platos sin venta (carta activa y elegidos) y el panel con los pedidos de una celda.
const MDIMS=['Grupo','Subgrupo','Plato'],MMEDS=['Unidades y venta','Venta','Unidades','Precio unitario','% de su venta'];
const mnorm=s=>String(s??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLocaleLowerCase('es');
const mgnom=(B,g)=>B.P.grupos[g]||'Sin grupo',msnom=(B,s)=>(B.P.subs||[])[s]||'Sin subgrupo';
// Con «Unidades y venta» se ordena y se pinta por la venta.
const mmedOrden=st=>st.vmed==='Unidades y venta'?'Venta':st.vmed;
const msecciones=st=>st.vdim==='Plato'&&st.vsec!==false;
// Los platos que pueden ir en cero: los vendidos en cualquier turno del rango y los de la carta activa.
function mpozoPlatos(B){
  if(!B.platos){B.platos=new Map();for(const r of B.items)if(!B.platos.has(r.prod))B.platos.set(r.prod,{prod:r.prod,grupo:r.grupo,sub:r.sub});
    for(const r of B.carta||[])if(!B.platos.has(r.prod))B.platos.set(r.prod,r);}
  return B.platos;
}
function mcruce(B,st){
  const g=st.vgrupo??-1,s=st.vsub??-1,dim=st.vdim||'Grupo',pasa=r=>(g<0||r.grupo===g)&&(s<0||r.sub===s);
  const items=mturno(B,B.items,st.turno).filter(pasa);
  const fil=new Map(),col=new Map(),det=new Map(),tot={u:0,v:0},suma=(a,r)=>{a.u+=r.cant;a.v+=r.venta;};
  const clave=r=>dim==='Grupo'?String(r.grupo):dim==='Subgrupo'?`${r.grupo}|${r.sub}`:String(r.prod);
  const nueva=r=>{const k=clave(r);
    // nom: la clave por NOMBRE de la fila, la que guardan las elegidas (sobrevive a otra fecha).
    if(!fil.has(k)){const gn=mgnom(B,r.grupo),sn=msnom(B,r.sub),label=dim==='Grupo'?gn:dim==='Subgrupo'?sn:B.P.prods[r.prod];
      fil.set(k,{k,label,gn,sn,nom:dim==='Subgrupo'?`${gn}|${sn}`:label,
      sub:dim==='Grupo'?'':dim==='Subgrupo'?gn:`${gn}${B.P.subs?.[r.sub]?' › '+B.P.subs[r.sub]:''}`,cel:new Map(),u:0,v:0});}
    return fil.get(k);};
  for(const r of items){
    const k=clave(r),f=nueva(r);if(!f.cel.has(r.ms))f.cel.set(r.ms,{u:0,v:0});suma(f.cel.get(r.ms),r);suma(f,r);
    if(!col.has(r.ms))col.set(r.ms,{u:0,v:0});suma(col.get(r.ms),r);suma(tot,r);
    const kd=`${r.ms}|${r.prod}|${r.grupo}|${r.sub}`;if(!det.has(kd))det.set(kd,{ms:r.ms,prod:r.prod,grupo:r.grupo,sub:r.sub,fila:k,u:0,v:0});suma(det.get(kd),r);
  }
  // Sin venta, en cero: todo, con «Con los que no se vendieron»; si no, sólo las filas elegidas.
  const sel=melegidas(st),vendidas=fil.size;
  for(const r of mpozoPlatos(B).values()){if(!pasa(r))continue;const k=clave(r);if(fil.has(k))continue;
    const gn=mgnom(B,r.grupo),sn=msnom(B,r.sub),nom=dim==='Grupo'?gn:dim==='Subgrupo'?`${gn}|${sn}`:B.P.prods[r.prod];
    if(st.vsin||sel.has(nom))nueva(r);}
  const cols=[...col].sort(([a,x],[b,y])=>(a===B.P.sin_mesero)-(b===B.P.sin_mesero)||y.v-x.v||a-b).map(([id])=>id);
  return {dim,cols,col,tot,filas:[...fil.values()],det:[...det.values()],pasa,clave,vendidas};
}
// La medida de una celda; el % es sobre lo que vendió ese mesero (su columna).
// El precio unitario es venta ÷ unidades de la celda: lo que cobró en promedio.
function mvalor(med,c,ct){if(!c)return null;return med==='Unidades'?c.u:med==='Precio unitario'?mdiv(c.v,c.u):med==='% de su venta'?mdiv(c.v,ct?.v):c.v;}
const melegidas=st=>new Set((st.vsel||{})[st.vdim||'Grupo']||[]);
function mvisibles(st,C){
  const q=mnorm(st.vq),o=st.vorden??'t',d=st.vdir??-1,sel=melegidas(st),solo=st.vsolo&&sel.size;
  const vs=C.filas.filter(f=>(!solo||sel.has(f.nom))&&(!q||mnorm(f.label).includes(q)||mnorm(f.sub).includes(q)));
  const texto={nombre:'label',grupo:'gn',subg:'sn'}[o],med=mmedOrden(st),sec=msecciones(st);
  const clave=f=>o==='t'?mvalor(med,f,C.tot):mvalor(med,f.cel.get(+o),C.col.get(+o));
  // Con secciones, primero el grupo y el subgrupo; adentro, el orden elegido.
  return vs.sort((a,b)=>{if(sec){const x=a.gn.localeCompare(b.gn,'es')||a.sn.localeCompare(b.sn,'es');if(x)return x;}if(texto)return (a[texto].localeCompare(b[texto],'es')||a.label.localeCompare(b.label,'es'))*d;const x=clave(a),y=clave(b);return ((x??-Infinity)-(y??-Infinity))*d||b.v-a.v||a.label.localeCompare(b.label,'es');});
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
window.__mesCalc={pedidosDe:(B,st,C,vis)=>mpedidos(B,st,C,vis),leer:mleer,resumen:mresumen,pozo:mpozo,planilla:mplanilla,distribucion:mdistribucion,vendido:mvendido,cruce:mcruce,valor:mvalor,visibles:mvisibles,equipo:mequipo,scope:mscope,historia:mhistoria};

function minicial(){return {turno:'Todo el día',modo:'Por mesero',ms:null,q:'',vdim:'Grupo',vmed:'Unidades y venta',vgrupo:-1,vsub:-1,vsel:{},vsolo:false,vsin:false,vsec:true,vdet:null,vdetPed:null,vq:'',vorden:'t',vdir:-1,orden:'propina',dir:-1,mas:false,tab:'Propinas',filtro:'Todos',celda:null,weekday:null,pedido:null,limite:150,mapa:'Por mesa',ayuda:false};}
const mboton=(a,v,t,on=false,tip='')=>`<button type="button" data-acc="${a}" data-v="${mesc(v)}" class="${on?'on':''}" aria-pressed="${on}" title="${mesc(tip)}">${mesc(t)}</button>`;
// ⤢ amplía la lista o la ficha a todo el ancho; ↙ o Esc vuelven (#788, como Recetas).
const mamp=(st,cual)=>{const on=st.amp===cual;return `<button type="button" class="ms-amp" data-acc="amp" data-v="${cual}" aria-pressed="${on}" title="${on?'Volver a las dos columnas (Esc)':'Ampliar '+(cual==='lista'?'la lista':'la ficha')+' a todo el ancho'}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${on?'M3 9h6V3M21 9h-6V3M3 15h6v6M21 15h-6v6':'M9 3H3v6M15 3h6v6M9 21H3v-6M15 21h6v-6'}"/></svg></button>`;};
const msegmento=(a,ops,v)=>`<div class="ms-seg" role="group">${ops.map(x=>mboton(a,x,x,x===v)).join('')}</div>`;
const mkpi=(n,v,sub='',tip='',color='')=>`<div class="ms-kpi" title="${mesc(tip)}"><span>${mesc(n)}</span><strong${color?` style="color:${color}"`:''}>${mesc(v)}</strong><small>${mesc(sub)}</small></div>`;
const mtabla=(heads,rows,cls='')=>`<div class="ms-scroll ${cls}"><table><thead><tr>${heads.map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
function mlimpiar(st){st.celda=null;st.weekday=null;st.pedido=null;st.filtro='Todos';st.limite=150;}
function mpintar(G){
  const {B,st,root}=G,T=mequipo(B,st.turno);G.T=T;
  if(st.ms==null||st.ms!==-1&&!T.R.some(r=>r.id===st.ms))st.ms=T.rank[0]?.id??-1;
  G.S=mscope(B,T,st);G.plan=mplanilla(T.z,st.modo);
  const oldScroll=root.querySelector('.ms-pay-scroll'),left=oldScroll?.scrollLeft||0,vOld=root.querySelector('.ms-vt-scroll'),vPos=[vOld?.scrollLeft||0,vOld?.scrollTop||0];
  const focus=root.getRootNode().activeElement,search=focus?.matches?.('[data-acc="buscar"],[data-acc="vbuscar"]')?focus.dataset.acc:null,cursor=search?focus.selectionStart:0;
  const t=T.t,t0=T.t0,pct=mdiv(t.propina,t.venta),vp=B.P.hay_anterior?mvar(t.propina,t0.propina):null;
  const corte=B.P.corte_ms!=null&&B.P.corte_ms<20*3600e3?` · último día hasta ${String(Math.floor(B.P.corte_ms/3600e3)).padStart(2,'0')}:${String(Math.floor(B.P.corte_ms/60000)%60).padStart(2,'0')}`:'';
  const sin=T.R.find(r=>r.id===B.P.sin_mesero);
  root.innerHTML=`<section class="ms-card ms-overview"><div class="ms-head ms-native-space"><h3>Propinas por mesero</h3>${msegmento('turno',['Todo el día','Almuerzo','Cena'],st.turno)}${mboton('ayuda','','?',st.ayuda,'Cuentas y alcance')}</div>
    <div class="ms-caption">${B.P.rango.map(s=>mfecha(mdia(s))).join('–')} · comparación: ${B.P.anterior.map(s=>mfecha(mdia(s))).join('–')}${corte}${!B.P.hay_anterior?' · sin datos anteriores disponibles':''}</div>
    <div class="ms-kpis">${mkpi('Propinas',msol(t.propina,0),mdelta(vp),'Propina registrada; sin «Sin mesero»',mcolor(vp))}${mkpi('% de la venta',mpct(pct),B.P.hay_anterior&&t0.venta>0?`${mnum((pct-t0.propina/t0.venta)*100,1)} pp vs anterior`:'Propina / venta')}${mkpi('Por mesa',msol(mdiv(t.propina,t.mesas)),`${t.mesas} mesas`)}${mkpi('Por persona',msol(mdiv(t.propina,t.personas)),`${mnum(t.personas)} adultos`)}<button class="ms-kpi ms-kpi-button" data-acc="sinpropina">${mkpi('Tarjeta sin propina',mpct(mdiv(t.sin_propina,t.tarjeta)),`${t.sin_propina} de ${t.tarjeta} · ver mesas`)}</button>${mkpi('Sólo efectivo',`${t.solo_efectivo} mesas`,'Propina no registrada en POS')}</div>
    <div class="ms-panes${st.amp?' amp-'+st.amp:''}"><div class="ms-list"><div class="ms-toolbar"><input type="search" data-acc="buscar" aria-label="Buscar mesero en la lista" placeholder="Buscar mesero…" value="${mesc(st.q)}">${mboton('mas','','Más datos',st.mas)}${mboton('equipo','','Equipo',st.ms===-1)}${mamp(st,'lista')}</div>${mrank(G)}<div class="ms-caption">Comparación Almuerzo/Cena: % de la venta de cada turno. La búsqueda acota la lista.</div>${sin?.mesas?`<div class="ms-caption">${mboton('sinmesero','','Sin mesero: '+sin.mesas+' pedidos')} · ${msol(sin.venta,0)}</div>`:''}</div>${mficha(G)}</div>
    ${st.ayuda?`<div class="ms-help">${mboton('ayuda','','Cerrar')}<p>Mesas = pedidos con venta; personas = adultos. Cada ítem suma venta una vez y cada pago suma propina una vez. El día es el del comprobante.</p><p>La propina se registra con tarjeta. Efectivo puede incluir una propina que el POS no registra. El % usa la venta de la mesa; los descuentos se explican en la ficha.</p><p>Pozo común: partes iguales por día y turno entre meseros con al menos una mesa. Es la regla supuesta de esta vista. El rango y el turno fijan el reparto; búsqueda, selección y filtros de ficha son análisis.</p><p>La comparación conserva los mismos días del mes anterior y la hora de corte del último día. Las muestras y los importes describen lo registrado.</p></div>`:''}
  </section>${mplan(G)}${mventa(G)}`;
  const sc=root.querySelector('.ms-pay-scroll');if(sc)sc.scrollLeft=left;
  const vs=root.querySelector('.ms-vt-scroll');if(vs){vs.scrollLeft=vPos[0];vs.scrollTop=vPos[1];}
  if(search){const e=root.querySelector(`[data-acc="${search}"]`);e.focus({preventScroll:true});e.setSelectionRange(cursor,cursor);}
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
  return `<div class="ms-ficha"><div class="ms-toolbar"><h4>${mesc(nom)}</h4>${contexto?mboton('limpiar','','Quitar selección'):''}${mamp(st,'ficha')}</div>${contexto?`<div class="ms-caption">${contexto}</div>`:''}${msegmento('tab',['Propinas','Mesas','12 meses','Lo que vendió'],st.tab)}${body}</div>`;
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
// La celda que se eligió para ver sus pedidos: «ms~fila», con ms = id o 't' (todos)
// y fila = 'k:<clave de fila>', 's:<grupo|subgrupo>' (una sección) o 't' (lo visible).
function mfilasDe(fila,vis){
  if(fila==='t')return new Set(vis.map(f=>f.k));
  if(fila.startsWith('s:')){const s=fila.slice(2);return new Set(vis.filter(f=>`${f.gn}|${f.sn}`===s).map(f=>f.k));}
  return new Set([fila.slice(2)]);
}
// Los pedidos detrás de una celda: cada ítem una vez (#517), con el turno y los filtros de la tarjeta.
function mpedidos(B,st,C,vis){
  if(!st.vdet)return null;
  const [ms,fila]=st.vdet.split('~'),keys=mfilasDe(fila,vis);
  if(!B.porPed)B.porPed=new Map(B.rows.map(r=>[r.id,r]));
  const m=new Map();
  for(const r of mturno(B,B.items,st.turno)){
    if(!C.pasa(r)||!keys.has(C.clave(r))||(ms!=='t'&&r.ms!==+ms))continue;
    if(!m.has(r.ped)){const p=B.porPed.get(r.ped);m.set(r.ped,{ped:r.ped,f:r.f,ms:r.ms,hora:p?.hora??null,doc:p?B.P.docs[p.doc]:'',pax:p?.personas??null,u:0,v:0,lineas:0});}
    const a=m.get(r.ped);a.u+=r.cant;a.v+=r.venta;a.lineas++;
  }
  const lista=[...m.values()].sort((a,b)=>b.f-a.f||(b.hora??0)-(a.hora??0)||b.ped-a.ped);
  const nombre=fila==='t'?'Todo lo visible':fila.startsWith('s:')?fila.slice(2).split('|').reverse().join(' · '):(vis.find(f=>f.k===fila.slice(2))?.label??C.filas.find(f=>f.k===fila.slice(2))?.label??'');
  return {ms,fila,nombre,mesero:ms==='t'?'Todos los meseros':B.P.meseros[+ms],lista,u:msum(lista,'u'),v:msum(lista,'v')};
}
const mhora=ms=>ms==null?'—':`${String(Math.floor(ms/3600e3)).padStart(2,'0')}:${String(Math.floor(ms/60000)%60).padStart(2,'0')}`;
function mdetalle(G){
  const {B,st}=G,D=G.D;if(!D)return '';
  const und=v=>mnum(v,Math.abs(v-Math.round(v))<1e-6?0:2);
  const conMs=D.ms==='t',keys=mfilasDe(D.fila,G.Cvis||[]);
  const filas=D.lista.map(p=>{const abierto=st.vdetPed===p.ped;
    const lineas=abierto?B.items.filter(r=>r.ped===p.ped).sort((a,b)=>b.venta-a.venta):[];
    const sub=abierto?`<tr class="ms-vt-det-lin"><td colspan="${conMs?7:6}"><table><tbody>${lineas.map(r=>`<tr class="${keys.has(G.C.clave(r))&&(conMs||r.ms===+D.ms)?'on':''}"><td>${mesc(B.P.prods[r.prod])}</td><td class="ms-num">${und(r.cant)}</td><td class="ms-num">${mnum(r.venta,2)}</td></tr>`).join('')}</tbody></table>
      <div class="ms-caption">Todo el pedido: ${lineas.length} líneas · S/ ${mnum(msum(lineas,'venta'),2)}${p.pax?` · ${mnum(p.pax)} adultos`:''}. En color, lo de esta celda.</div></td></tr>`:'';
    return `<tr data-acc="vdetped" data-v="${p.ped}" tabindex="0" class="${abierto?'on':''}" title="Ver todo el pedido"><td>${mdm(p.f)}</td><td>${mhora(p.hora)}</td><td>${mesc(p.doc||B.P.pedidos[p.ped])}</td>${conMs?`<td>${mesc(B.P.meseros[p.ms])}</td>`:''}<td class="ms-num">${und(p.u)}</td><td class="ms-num">${mnum(p.v,2)}</td><td class="ms-num">${p.u>0?mnum(p.v/p.u,2):'—'}</td></tr>${sub}`;}).join('');
  return `<aside class="ms-vt-det" role="dialog" aria-label="Pedidos de la celda"><div class="ms-head"><h3>${mesc(D.nombre)}</h3>${mboton('excelped','','Excel')}${mboton('vdetcerrar','','✕',false,'Cerrar (Esc)')}</div>
    <div class="ms-caption">${mesc(D.mesero)} · ${mesc(st.turno)} · ${B.P.rango.map(s=>mfecha(mdia(s))).join('–')}</div>
    <div class="ms-vt-det-sum"><b>${und(D.u)}</b> und · <b>S/ ${mnum(D.v,2)}</b> · ${D.lista.length} pedido${D.lista.length===1?'':'s'}${D.u>0?` · S/ ${mnum(D.v/D.u,2)} c/u`:''}</div>
    ${D.lista.length?`<div class="ms-scroll ms-vt-det-scroll"><table><thead><tr><th>Fecha</th><th>Hora</th><th>Comprobante</th>${conMs?'<th>Mesero</th>':''}<th>Und</th><th>S/</th><th>P. unit.</th></tr></thead><tbody>${filas}</tbody></table></div>
    <div class="ms-caption">Un clic en un pedido muestra todo lo que se pidió en él.</div>`:'<p class="ms-empty">Sin pedidos: esta celda no tuvo venta con estos filtros.</p>'}</aside>`;
}
function mventa(G){
  const {B,st}=G,C=mcruce(B,st),vis=mvisibles(st,C);G.C=C;G.Cvis=vis;
  const med=st.vmed,both=med==='Unidades y venta',pct=med==='% de su venta',pu=med==='Precio unitario',mt=mmedOrden(st);
  const und=v=>v==null?'·':mnum(v,Math.abs(v-Math.round(v))<1e-6?0:2);
  const fmt=v=>v==null?'·':pct?mpct(v):pu?mnum(v,2):mt==='Unidades'?und(v):mnum(v,both?2:0);
  const dim=st.vdim,sec=msecciones(st);
  const extra=sec?[]:dim==='Plato'?[['grupo','Grupo','gn'],['subg','Subgrupo','sn']]:dim==='Subgrupo'?[['grupo','Grupo','gn']]:[];
  const sel=melegidas(st),todasVis=vis.length>0&&vis.every(f=>sel.has(f.nom));
  const cols=C.cols,acum=fs=>{const m=new Map(cols.map(id=>[id,{u:0,v:0}])),t={u:0,v:0};for(const f of fs){for(const [id,c] of f.cel){const a=m.get(id);a.u+=c.u;a.v+=c.v;}t.u+=f.u;t.v+=f.v;}return [m,t];};
  const [vt,vtot]=acum(vis);
  const max=Math.max(1e-9,...vis.flatMap(f=>cols.map(id=>Math.abs(mvalor(mt,f.cel.get(id),C.col.get(id))||0))));
  const tono=v=>v==null?'':` style="background:color-mix(in srgb,var(--accent) ${Math.round(Math.min(1,Math.abs(v)/max)*30)}%,var(--bg-card))"`;
  // Una celda (o dos, con «Unidades y venta»); un clic abre sus pedidos.
  const celdas=(c,ct,ms,fila,cls,tip,pinta=true)=>{if(c&&!c.u&&!c.v)c=null;const d=`data-acc="vcel" data-v="${ms}~${mesc(fila)}" title="${mesc(tip)} · ver pedidos"`,on=st.vdet===`${ms}~${fila}`?' ms-vt-on':'';
    if(both){const v=c?c.v:null;return `<td class="ms-num ms-vt-u${cls}${on}" ${d}>${und(c?c.u:null)}</td><td class="ms-num${cls}${on}"${pinta?tono(v):''} ${d}>${fmt(v)}</td>`;}
    const v=mvalor(med,c,ct);return `<td class="ms-num${cls}${on}"${pinta?tono(v):''} ${d}>${fmt(v)}</td>`;};
  const colOn=id=>id===st.ms?' ms-col-on':'';
  const flecha=k=>String(st.vorden)===String(k)?(st.vdir===1?' ▲':' ▼'):'';
  const rs=both?' rowspan="2"':'',cs=both?' colspan="2"':'';
  const th=(k,t,tip,cls='',span='')=>`<th class="${cls}"${span}>${mboton('vorden',k,t+flecha(k),String(st.vorden)===String(k),tip)}</th>`;
  const grupos=[...new Set(B.items.map(r=>r.grupo))].sort((a,b)=>mgnom(B,a).localeCompare(mgnom(B,b),'es'));
  const g=st.vgrupo??-1,subs=[...new Set(B.items.filter(r=>g<0||r.grupo===g).map(r=>r.sub))].sort((a,b)=>msnom(B,a).localeCompare(msnom(B,b),'es'));
  const marca=`<input type="checkbox" data-acc="vselvis" aria-label="Elegir todo lo visible" title="Elegir todo lo visible"${todasVis?' checked':''}>`;
  const head=`<tr><th class="ms-sticky"${rs}><span class="ms-vt-nom">${marca}${mboton('vorden','nombre',dim+flecha('nombre'),st.vorden==='nombre','Ordenar por nombre')}</span></th>${extra.map(([k,t])=>th(k,t,`Ordenar por ${t.toLowerCase()}`,'ms-vt-txt',rs)).join('')}${cols.map(id=>th(id,B.P.meseros[id],`Ordenar por ${B.P.meseros[id]}${both?' (venta)':''}`,`ms-vt-ms${colOn(id)}`,cs)).join('')}${th('t','Total','Ordenar por el total','ms-vt-tot ms-vt-ms',cs)}</tr>`
    +(both?`<tr class="ms-vt-sub">${cols.map(id=>`<th class="ms-vt-u${colOn(id)}">Und</th><th class="${colOn(id).trim()}">S/</th>`).join('')}<th class="ms-vt-u ms-vt-tot">Und</th><th class="ms-vt-tot">S/</th></tr>`:'');
  const fila=f=>`<tr class="${sel.has(f.nom)?'ms-vt-sel':''}${f.u||f.cel.size?'':' ms-vt-cero'}"><td class="ms-sticky"><label class="ms-vt-nom"><input type="checkbox" data-acc="vsel" data-v="${mesc(f.nom)}" aria-label="Elegir ${mesc(f.label)}"${sel.has(f.nom)?' checked':''}><b>${mesc(f.label)}</b></label></td>${extra.map(([,,c])=>`<td class="ms-vt-txt">${mesc(f[c])}</td>`).join('')}${cols.map(id=>celdas(f.cel.get(id),C.col.get(id),id,'k:'+f.k,colOn(id),`${B.P.meseros[id]} · ${f.label}`)).join('')}${celdas(f,C.tot,'t','k:'+f.k,' ms-vt-tot',`Todos · ${f.label}`)}</tr>`;
  // Secciones por subgrupo, como una planilla: la banda lleva el subtotal.
  let body='';
  if(sec){const grupos2=new Map();for(const f of vis){const k=`${f.gn}|${f.sn}`;if(!grupos2.has(k))grupos2.set(k,[]);grupos2.get(k).push(f);}
    for(const [k,fs] of grupos2){const [m,t]=acum(fs),[gn,sn]=k.split('|');
      body+=`<tr class="ms-vt-secc"><td class="ms-sticky"><b>${mesc(sn)}</b> <small>${mesc(gn)}</small></td>${cols.map(id=>celdas(m.get(id),C.col.get(id),id,'s:'+k,colOn(id),`${B.P.meseros[id]} · ${sn}`,false)).join('')}${celdas(t,C.tot,'t','s:'+k,' ms-vt-tot',`Todos · ${sn}`,false)}</tr>`+fs.map(fila).join('');}}
  else body=vis.map(fila).join('');
  const pie=`<tr><td class="ms-sticky">${pu?'Promedio':'Total'}${vis.length<C.filas.length?' de lo visible':''}</td>${extra.map(()=>'<td></td>').join('')}${cols.map(id=>celdas(vt.get(id),C.col.get(id),id,'t',colOn(id),`${B.P.meseros[id]} · total`,false)).join('')}${celdas(vtot,C.tot,'t','t',' ms-vt-tot','Todo lo visible',false)}</tr>`;
  const tabla=!C.filas.length?'<p class="ms-empty">Sin ventas para este turno, grupo y subgrupo.</p>':!vis.length?`<p class="ms-empty">${st.vsolo&&sel.size?'Ninguna de las elegidas está con estos filtros.':'Nada coincide con la búsqueda.'}</p>`:
    `<div class="ms-scroll ms-vt-scroll"><table class="${both?'ms-vt-doble':''}"><thead>${head}</thead><tbody>${body}</tbody><tfoot>${pie}</tfoot></table></div>`;
  G.D=mpedidos(B,st,C,vis);
  const nota=both?'Unidades y venta en S/ de cada mesero; se ordena y se colorea por la venta.':pct?'% de su venta: qué parte de lo que vendió cada mesero (con el turno y los filtros elegidos) fue cada fila.':pu?'Precio unitario: venta ÷ unidades de cada celda, en S/ (lo cobrado en promedio, con descuentos).':med==='Venta'?'Venta en S/, como en el resto de Ventas: notas de crédito restadas, sin cortesías ni anulados.':'Unidades vendidas; una devolución resta.';
  const ceros=C.filas.length-C.vendidas;
  return `<section class="ms-card ms-vt"><div class="ms-head"><h3>Venta por mesero · ${mesc(st.turno)}</h3>${mboton('excelventa','','Excel venta')}</div>
    <div class="ms-toolbar"><span class="ms-rot">Filas</span>${msegmento('vdim',MDIMS,st.vdim)}<span class="ms-rot">Medida</span>${msegmento('vmed',MMEDS,med)}</div>
    <div class="ms-toolbar"><select data-acc="vgrupo" aria-label="Filtrar por grupo"><option value="-1"${st.vgrupo<0?' selected':''}>Todos los grupos</option>${grupos.map(g=>`<option value="${g}"${st.vgrupo===g?' selected':''}>${mesc(mgnom(B,g))}</option>`).join('')}</select>
      <select data-acc="vsub" aria-label="Filtrar por subgrupo"><option value="-1"${st.vsub<0?' selected':''}>Todos los subgrupos</option>${subs.map(x=>`<option value="${x}"${st.vsub===x?' selected':''}>${mesc(msnom(B,x))}</option>`).join('')}</select>
      <input type="search" data-acc="vbuscar" aria-label="Buscar en las filas" placeholder="Buscar ${st.vdim==='Plato'?'plato':st.vdim==='Grupo'?'grupo':'subgrupo'}…" value="${mesc(st.vq)}">
      ${dim==='Plato'?mboton('vsec','','Secciones',sec,'Agrupar los platos por subgrupo, con su subtotal'):''}${mboton('vsin','','Con los que no se vendieron',!!st.vsin,'Sumar en cero los platos activos de la carta (y los vendidos en el otro turno)')}
      <span class="ms-vt-eleg">${sel.size?`${mboton('vsolo','',st.vsolo?`Ver todas`:`Solo elegidas (${sel.size})`,!!st.vsolo,st.vsolo?'Volver a todas las filas':'Ver sólo las filas marcadas')}${mboton('vlimpiar','','✕',false,'Quitar las elegidas')}`:'<span class="ms-rot">Marca filas para compararlas solas</span>'}</span></div>
    <div class="ms-caption">${vis.length} de ${C.filas.length} filas${ceros?` (${ceros} sin venta)`:''} · ${cols.length} meseros, de más a menos venta${cols.includes(B.P.sin_mesero)?'; «Sin mesero» al final':''}. El turno es el de arriba. ${nota} Un clic en un número muestra sus pedidos.</div>${tabla}${mdetalle(G)}</section>`;
}
function mexcelVenta(G){
  const {B,st,C}=G,vis=G.Cvis||[],med=st.vmed,both=med==='Unidades y venta',pct=med==='% de su venta',x=v=>v==null?null:pct?v*100:v,sec=msecciones(st);
  const extra=st.vdim==='Plato'?[['Grupo','gn'],['Subgrupo','sn']]:st.vdim==='Subgrupo'?[['Grupo','gn']]:[];
  const cab=[st.vdim,...extra.map(([t])=>t),...(both?C.cols.flatMap(id=>[`${B.P.meseros[id]} · Und`,`${B.P.meseros[id]} · S/`]):C.cols.map(id=>B.P.meseros[id])),...(both?['Total · Und','Total · S/']:['Total'])];
  const vals=(c,ct)=>both?[c?c.u:null,c?c.v:null]:[x(mvalor(med,c,ct))];
  const acum=fs=>{const m=new Map(C.cols.map(id=>[id,{u:0,v:0}])),t={u:0,v:0};for(const f of fs){for(const [id,c] of f.cel){m.get(id).u+=c.u;m.get(id).v+=c.v;}t.u+=f.u;t.v+=f.v;}return [m,t];};
  const fila=(nom,info,m,t)=>[nom,...info,...C.cols.flatMap(id=>vals(m.get?m.get(id):m(id),C.col.get(id))),...vals(t,C.tot)];
  const filas=[];
  const filaDe=f=>fila(f.label,extra.map(([,c])=>f[c]),id=>f.cel.get(id),f);
  if(sec){const gs=new Map();for(const f of vis){const k=`${f.gn}|${f.sn}`;if(!gs.has(k))gs.set(k,[]);gs.get(k).push(f);}
    for(const [k,fs] of gs){const [m,t]=acum(fs),[gn,sn]=k.split('|');filas.push(fila(`${sn} (subtotal)`,[gn,sn],m,t));for(const f of fs)filas.push(filaDe(f));}}
  else for(const f of vis)filas.push(filaDe(f));
  const [vt,vtot]=acum(vis);filas.push(fila(med==='Precio unitario'?'Promedio':'Total',extra.map(()=>''),vt,vtot));
  const keys=new Set(vis.map(f=>f.k));
  const det=C.det.filter(r=>keys.has(r.fila)).sort((a,b)=>B.P.meseros[a.ms].localeCompare(B.P.meseros[b.ms],'es')||b.v-a.v).map(r=>[B.P.meseros[r.ms],mgnom(B,r.grupo),msnom(B,r.sub),B.P.prods[r.prod],r.u,r.v]);
  const contexto=[['Desde',B.P.rango[0]],['Hasta',B.P.rango[1]],['Turno',st.turno],['Filas',st.vdim],['Medida',pct?'% de la venta de cada mesero':med==='Precio unitario'?'Precio unitario (S/, venta ÷ unidades)':med],['Grupo',st.vgrupo<0?'Todos':mgnom(B,st.vgrupo)],['Subgrupo',st.vsub<0?'Todos':msnom(B,st.vsub)],['Búsqueda',st.vq||'—'],['Filas elegidas',st.vsolo&&melegidas(st).size?[...melegidas(st)].join(' / '):'Todas'],['Sin venta',st.vsin?'Incluidos en cero (carta activa)':'Sólo los elegidos'],['Venta','Notas de crédito restadas; sin cortesías ni anulados; cada ítem una vez']];
  for(const [k,vs] of Object.entries(B.P.filtros))contexto.push([k,vs.length?vs.join(' / '):'Todos']);
  bajar(`Venta_por_mesero_${archivo(st.vdim)}_${archivo(st.turno)}.xlsx`,libro([{nombre:`${st.vdim} × mesero`,cabeza:cab,filas},{nombre:'Detalle',cabeza:['Mesero','Grupo','Subgrupo','Plato','Unidades','Venta'],filas:det},{nombre:'Contexto',cabeza:['Dato','Valor'],filas:contexto}]));
}
function mexcelPedidos(G){
  const {B,st,D}=G;if(!D)return;
  const lineas=D.lista.flatMap(p=>B.items.filter(r=>r.ped===p.ped).map(r=>[mfecha(p.f),mhora(p.hora),p.doc||B.P.pedidos[p.ped],B.P.meseros[r.ms],B.P.prods[r.prod],mgnom(B,r.grupo),msnom(B,r.sub),r.cant,r.venta]));
  bajar(`Pedidos_${archivo(D.nombre)}_${archivo(D.mesero)}.xlsx`,libro([
    {nombre:'Pedidos',cabeza:['Fecha','Hora','Comprobante','Mesero','Unidades','Venta','Precio unitario'],filas:D.lista.map(p=>[mfecha(p.f),mhora(p.hora),p.doc||B.P.pedidos[p.ped],B.P.meseros[p.ms],p.u,p.v,p.u>0?p.v/p.u:null])},
    {nombre:'Pedidos enteros',cabeza:['Fecha','Hora','Comprobante','Mesero','Plato','Grupo','Subgrupo','Unidades','Venta'],filas:lineas},
    {nombre:'Contexto',cabeza:['Dato','Valor'],filas:[['Celda',D.nombre],['Mesero',D.mesero],['Turno',st.turno],['Desde',B.P.rango[0]],['Hasta',B.P.rango[1]],['Unidades',D.u],['Venta',D.v]]}]));
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
    else if(acc==='amp')st.amp=st.amp===v?null:v;
    else if(acc==='ayuda')st.ayuda=!st.ayuda;
    else if(acc==='orden'){if(v==='id'){st.orden='id';st.dir=st.dir===1?-1:1;}else if(['propina','tasa','mesas','por_mesa','sin_pct','dias','personas','items','venta','var','pozo'].includes(v)){st.dir=st.orden===v?-st.dir:-1;st.orden=v;}}
    else if(acc==='celda'){const [m,f,t]=v.split('|');st.ms=+m;mlimpiar(st);st.celda={f:+f,turn:t===''?null:+t};st.tab='Mesas';}
    else if(acc==='weekday'){const [w,t]=v.split('|');st.ms=-1;mlimpiar(st);st.weekday=+w;st.celda={f:null,turn:+t};st.tab='Mesas';}
    else if(acc==='excelplan'){mexcelPlan(G);return;}
    else if(acc==='excelmesas'){mexcelMesas(G);return;}
    else if(acc==='excelventa'){mexcelVenta(G);return;}
    else if(acc==='vdim'){st.vdim=v;st.vq='';st.vdet=null;st.vdetPed=null;}
    else if(acc==='vmed')st.vmed=v;
    else if(acc==='vorden'){st.vdir=st.vorden===v?-st.vdir:(['nombre','grupo','subg'].includes(v)?1:-1);st.vorden=v;}
    else if(acc==='vcel'){st.vdet=st.vdet===v?null:v;st.vdetPed=null;}
    else if(acc==='vdetcerrar'){st.vdet=null;st.vdetPed=null;}
    else if(acc==='vdetped')st.vdetPed=st.vdetPed===+v?null:+v;
    else if(acc==='excelped'){mexcelPedidos(G);return;}
    else if(acc==='vsec')st.vsec=!msecciones(st);
    else if(acc==='vsin')st.vsin=!st.vsin;
    else if(acc==='vsolo'){st.vsolo=!st.vsolo;if(st.vsolo)st.vq='';}
    else if(acc==='vlimpiar'){st.vsel={...st.vsel,[st.vdim]:[]};st.vsolo=false;}
    else return;
    mpintar(G);
    if(['celda','weekday','sinpropina','sinmesero'].includes(acc))root.querySelector('.ms-ficha')?.scrollIntoView({block:'nearest',behavior:'smooth'});
  });
  // Esc en el document: el redibujo se lleva el botón que tenía el foco.
  document.addEventListener('keydown',ev=>{if(ev.key!=='Escape'||!root.isConnected)return;if(st.vdet){st.vdet=null;st.vdetPed=null;mpintar(G);}else if(st.amp){st.amp=null;mpintar(G);}});
  root.addEventListener('input',ev=>{const a=ev.target.dataset.acc;if(a==='buscar'){st.q=ev.target.value;mpintar(G);}else if(a==='vbuscar'){st.vq=ev.target.value;mpintar(G);}});
  root.addEventListener('change',ev=>{const a=ev.target.dataset.acc;if(a==='filtro'){st.filtro=ev.target.value;st.pedido=null;st.limite=150;mpintar(G);}else if(a==='vgrupo'){st.vgrupo=+ev.target.value;st.vsub=-1;mpintar(G);}else if(a==='vsub'){st.vsub=+ev.target.value;mpintar(G);}
    // Elegir filas: por nombre y por corte (Grupo, Subgrupo o Plato), sin tope.
    else if(a==='vsel'||a==='vselvis'){const s=melegidas(st),noms=a==='vsel'?[ev.target.dataset.v]:(G.Cvis||[]).map(f=>f.nom);
      for(const n of noms){if(ev.target.checked)s.add(n);else s.delete(n);}st.vsel={...st.vsel,[st.vdim]:[...s]};if(!s.size)st.vsolo=false;mpintar(G);}});
  root.addEventListener('keydown',ev=>{if(ev.key==='Escape'){if(st.ayuda)st.ayuda=false;else st.pedido=null;mpintar(G);}const r=ev.target.closest('tr[data-acc]');if(r&&(ev.key==='Enter'||ev.key===' ')){ev.preventDefault();r.click();}});
  root.addEventListener('scroll',ev=>{const e=ev.target;if(e.matches('.ms-mesas-scroll')&&e.scrollTop+e.clientHeight>e.scrollHeight-70&&st.limite<G.S.rows.length){const y=e.scrollTop,x=e.scrollLeft;st.limite+=150;mpintar(G);const next=root.querySelector('.ms-mesas-scroll');next.scrollTop=y;next.scrollLeft=x;}},true);
}
window.__mesUI={inicial:minicial,pintar:mpintar};
export default function(component){
  const {data:P,parentElement}=component;if(!P)return;
  const old=window.__vtMes,st=old?.st||minicial();old?.observer?.disconnect();clearTimeout(old?.resizeTimer);
  if(old&&old.B.P.sello!==P.sello){const nombre=old.B.P.meseros[st.ms];st.ms=st.ms===-1?-1:P.meseros.indexOf(nombre);if(st.ms<0)st.ms=-1;mlimpiar(st);
    if(st.vgrupo>=0)st.vgrupo=P.grupos.indexOf(old.B.P.grupos[st.vgrupo]);
    if(st.vsub>=0)st.vsub=(P.subs||[]).indexOf((old.B.P.subs||[])[st.vsub]);
    st.vdet=null;st.vdetPed=null;}
  let root=parentElement.querySelector('.msp');if(!root){root=document.createElement('div');root.className='msp';parentElement.appendChild(root);}
  const G={root,st,B:old?.B.P.sello===P.sello?old.B:mleer(P)};window.__vtMes=G;
  // Un remontaje sobre la misma raíz no acumula manejadores.
  if(old?.root===root){root.replaceWith(root.cloneNode(false));G.root=parentElement.querySelector('.msp');}
  menlazar(G);mpintar(G);let ancho=G.root.clientWidth;
  G.observer=new ResizeObserver(()=>{if(Math.abs(G.root.clientWidth-ancho)<2)return;ancho=G.root.clientWidth;clearTimeout(G.resizeTimer);G.resizeTimer=setTimeout(()=>{if(G.root.isConnected)msvg(G);},80);});G.observer.observe(G.root);
}
