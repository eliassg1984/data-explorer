// Compras > Volatilidad (#718). El Excel compartido se antepone a este módulo.
const VL = { dia:0, hora:1, prod:2, prov:3, doc:4, um:5, precio:6, cant:7, valor:8 };
const VDIA = 864e5;
const vdia = s => Date.parse(s + 'T00:00:00Z') / VDIA;
const viso = n => new Date(n * VDIA).toISOString().slice(0,10);
const vfecha = n => { const s=viso(n); return `${s.slice(8)}/${s.slice(5,7)}/${s.slice(0,4)}`; };
const vdm = n => vfecha(n).slice(0,5);
const vlunes = n => n - (new Date(n * VDIA).getUTCDay()+6)%7;
const vok = v => v!=null && Number.isFinite(v);
const vesc = s => String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const vfmt = [0,1,2,3,4].map(d=>new Intl.NumberFormat('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}));
const vnum = (v,d=0) => vok(v)?vfmt[d].format(v):'—';
const vsol = (v,d=2) => vok(v)?`${v<0?'−':''}S/ ${vnum(Math.abs(v),d)}`:'—';
const vpct = (a,p) => vok(a)&&p>0?(a/p-1)*100:null;
const vpor = v => vok(v)?`${v>.05?'+':v<-.05?'−':''}${vnum(Math.abs(v),1)}%`:'—';
const vcolor = v => !vok(v)||Math.abs(v)<.005?'var(--text-secondary)':v>0?'var(--danger)':'var(--success)';
const vsuma = (rs,k) => rs.reduce((s,r)=>s+(r[k]||0),0);
const vrango = (rs,a,b) => rs.filter(r=>r.f>=a&&r.f<=b);
const vpal = ['var(--serie-0)','var(--serie-1)','var(--serie-2)','var(--serie-3)','var(--serie-4)','var(--serie-5)','var(--serie-6)'];

function vleer(P) {
  const base=vdia(P.base), prods=new Map();
  const rows=P.lineas.map((r,id)=>({id,f:base+r[VL.dia],t:r[VL.hora],prod:r[VL.prod],prov:r[VL.prov],doc:r[VL.doc],u:r[VL.um],p:r[VL.precio],q:r[VL.cant],v:r[VL.valor]}));
  rows.sort((a,b)=>a.f-b.f||a.t-b.t||a.id-b.id);
  for(const r of rows){if(!prods.has(r.prod))prods.set(r.prod,[]);prods.get(r.prod).push(r);}
  return {P,rows,prods,planes:Object.fromEntries(Object.entries(P.planes).map(([k,r])=>[k,r.map(vdia)])),cache:new Map()};
}
function vscore(cs) {
  let s=0;
  for(let i=1;i<cs.length;i++)if(cs[i-1]>0&&vok(cs[i]))s+=Math.abs((cs[i]/cs[i-1]-1)*100);
  // El puntaje se muestra con una décima, como _vol_score de Python.
  return Math.round((s+Number.EPSILON)*10)/10;
}
function vdisp(rs) {
  const ps=rs.filter(r=>r.p>0).map(r=>r.p);
  if(ps.length<5)return null;
  const m=ps.reduce((s,p)=>s+p,0)/ps.length;
  return Math.sqrt(ps.reduce((s,p)=>s+(p-m)**2,0)/(ps.length-1))/m;
}
function vtotal(rs) {
  const validos=rs.filter(r=>r.p>0&&r.q>0), q=vsuma(validos,'q');
  const valor=validos.reduce((s,r)=>s+r.p*r.q,0);
  return {cant:q,valor,precio:q?valor/q:null,n:validos.length,omitidas:rs.length-validos.length,registrado:vsuma(rs,'v')};
}
function vcambio(a,p,completo=true) {
  const actual=vtotal(a), previo=vtotal(p), bien=completo&&actual.cant>0&&previo.cant>0;
  return {actual,previo,precio:bien?(actual.precio-previo.precio)*actual.cant:null,
    cantidad:bien?(actual.cant-previo.cant)*previo.precio:null,delta:bien?actual.valor-previo.valor:null,completo};
}
function vsobre(rs) {
  const xs=rs.filter(r=>r.p>0&&vok(r.q));
  if(!xs.length)return {sobre:0,gasto:0,pct:0};
  const min=Math.min(...xs.map(r=>r.p)), gasto=xs.reduce((s,r)=>s+r.p*r.q,0);
  const sobre=xs.reduce((s,r)=>s+(r.p-min)*r.q,0);
  return {sobre,gasto,pct:gasto?sobre/gasto*100:0};
}
function vmoda(rs) {
  const m=new Map();for(const r of rs)m.set(r.u,(m.get(r.u)||0)+1);
  return [...m].sort((a,b)=>b[1]-a[1]||a[0]-b[0])[0]?.[0];
}
function vsemanas(rs,sems,previo=null) {
  const m=new Map();for(const r of rs)if(r.p>0){const s=vlunes(r.f);if(!m.has(s))m.set(s,[]);m.get(s).push(r);}
  let c=previo;
  return sems.map(s=>{const rows=m.get(s)||[], ps=rows.map(r=>r.p), antes=c;
    if(ps.length)c=ps[ps.length-1];
    return {f:s,o:ps.length?ps[0]:c,c,h:ps.length?Math.max(...ps):c,l:ps.length?Math.min(...ps):c,rows,antes};});
}
function vbase(B,op) {
  if(B.cache.has(op))return B.cache.get(op);
  const rango=B.planes[op]||B.planes['12m'], [a,b]=rango, rows=vrango(B.rows,a,b);
  const sems=[...new Set(rows.map(r=>vlunes(r.f)))].sort((a,b)=>a-b), ult=sems.slice(-5), rank=[];
  const ri=ult.length?Math.max(a,ult[0]):a, rf=ult.length?Math.min(b,ult[ult.length-1]+6):b, ip=ri-(rf-ri+1);
  for(const [id,hist] of B.prods){
    const xs=vrango(hist,a,b);if(!xs.length)continue;
    const rec=xs.filter(r=>ult.includes(vlunes(r.f))), u=vmoda(rec.length?rec:xs);
    const uno=xs.filter(r=>r.u===u), rr=rec.filter(r=>r.u===u), cs=vsemanas(uno,sems).map(w=>w.c);
    const gasto=vsuma(rec,'v'), cobertura=new Set(rec.map(r=>vlunes(r.f))).size;
    const puente=vcambio(vrango(hist.filter(r=>r.u===u),ri,rf),vrango(hist.filter(r=>r.u===u),ip,ri-1),ip>=vdia(B.P.historia[0]));
    rank.push({id,nombre:B.P.prods[id],u,unidades:[...new Set(xs.map(r=>r.u))],cierres:cs,
      volatilidad:vscore(cs.slice(-ult.length)),dispersion:vdisp(rr),gasto,cobertura,ventana:vsuma(xs,'v'),
      candidato:gasto>=400&&cobertura>=.75*ult.length,impacto:puente.precio,puente});
  }
  const R={rango,rows,sems,ult,ri,rf,ip,rank};B.cache.set(op,R);return R;
}
function vranking(B,st) {
  const R=vbase(B,st.op), q=(st.q||'').trim().toLocaleLowerCase('es');
  const match=r=>!q||r.nombre.toLocaleLowerCase('es').includes(q);
  const candidatos=R.rank.filter(r=>r.candidato).sort((a,b)=>{
    if(st.orden==='dispersion')return (b.dispersion??-1)-(a.dispersion??-1)||b.volatilidad-a.volatilidad||a.id-b.id;
    if(st.orden==='impacto')return (b.impacto??-Infinity)-(a.impacto??-Infinity)||b.gasto-a.gasto||a.id-b.id;
    if(st.orden==='gasto')return b.gasto-a.gasto||a.id-b.id;
    return b.volatilidad-a.volatilidad||a.id-b.id;
  });
  const fuera=q?R.rank.filter(r=>!r.candidato&&match(r)).sort((a,b)=>b.ventana-a.ventana||a.id-b.id):[];
  return {...R,visibles:[...candidatos.filter(match),...fuera],n:candidatos.length};
}
function vproveedores(rs) {
  const grupos=new Map();for(const r of rs){if(!grupos.has(r.prov))grupos.set(r.prov,[]);grupos.get(r.prov).push(r);}
  return [...grupos].map(([id,xs])=>({id,...vtotal(xs),n_compras:xs.length,
    primera:xs[0].f,ultima:xs[xs.length-1].f,ultimo:xs.filter(r=>r.p>0).at(-1)?.p??null}))
    .sort((a,b)=>(a.precio??Infinity)-(b.precio??Infinity)||a.id-b.id);
}
function vdetalle(B,R,st) {
  const info=R.rank.find(r=>r.id===st.prod);if(!info)return null;
  const u=st.u??info.u, hist=(B.prods.get(info.id)||[]).filter(r=>r.u===u);
  const rows=vrango(hist,...R.rango).filter(r=>r.p>0), previo=hist.filter(r=>r.f<R.sems[0]&&r.p>0).at(-1)?.p??null;
  let weeks=vsemanas(rows,R.sems,previo), k=weeks.findIndex(w=>w.c!=null);weeks=k<0?[]:weeks.slice(k);
  const compra=st.gran==='Compra', items=compra?rows:weeks, n=Math.min(compra?8:4,items.length);
  const fin=Math.min(items.length-1,Math.max(n-1,st[compra?'finCompra':'finSem']??items.length-1)), ini=Math.max(0,fin-n+1);
  const vista=items.slice(ini,fin+1);
  if(!vista.length)return {info,u,rows,weeks,vista,scope:[],proveedores:[],vacio:true};
  let foco=st.foco;
  if(foco==null||foco<ini||foco>fin){
    foco=ini;
    for(let i=ini;i<=fin;i++){
      const score=j=>compra?Math.abs(vpct(rows[j].p,rows[j-1]?.p??previo)||0):Math.abs(weeks[j].c-weeks[j].o);
      if(score(i)>score(foco))foco=i;
    }
  }
  const rr=st.sel||[vista[0].f,compra?vista.at(-1).f:vista.at(-1).f+6];
  const rango=[Math.max(rr[0],R.rango[0]),Math.min(rr[1],R.rango[1])], ip=rango[0]-(rango[1]-rango[0]+1), fp=rango[0]-1;
  const todos=vrango(hist,...rango), scope=todos.filter(r=>st.prov==null||r.prov===st.prov);
  const pa=vrango(hist,ip,fp).filter(r=>st.prov==null||r.prov===st.prov);
  const elegido=compra?[rows[foco]]:weeks[foco].rows;
  const tabla=(st.modo==='Elegida'?elegido:scope).filter(r=>st.prov==null||r.prov===st.prov);
  return {info,u,hist,rows,weeks,items,vista,ini,fin,n,foco,rango,ip,fp,todos,scope,tabla,
    total:vtotal(scope),sobre:vsobre(scope),dispersion:vdisp(scope),proveedores:vproveedores(todos),
    puente:vcambio(scope,pa,ip>=vdia(B.P.historia[0])),previo};
}
window.__cvCalc={leer:vleer,base:vbase,ranking:vranking,detalle:vdetalle,score:vscore,dispersion:vdisp,
  total:vtotal,cambio:vcambio,sobre:vsobre,semanas:vsemanas,proveedores:vproveedores};

function vinicial(op='12m'){return {op,q:'',orden:'volatilidad',verVol:false,verDisp:false,verImpacto:false,prod:null,u:null,
  gran:'Semana',sel:null,foco:null,finSem:null,finCompra:null,prov:null,tab:'Compras',modo:'Elegida',limite:150,ayuda:false};}
function vbot(acc,v,t,on=false,title=''){return `<button type="button" data-acc="${acc}" data-v="${vesc(v)}" class="${on?'on':''}" title="${vesc(title)}" aria-pressed="${on}">${vesc(t)}</button>`;}
const vseg=(acc,ops,val)=>`<div class="cv-seg" role="group">${ops.map(x=>vbot(acc,x,x,x===val)).join('')}</div>`;
const vkpi=(rot,v,sub='',color='')=>`<div class="cv-kpi"><span>${vesc(rot)}</span><b${color?` style="color:${color}"`:''}>${vesc(v)}</b><small>${vesc(sub)}</small></div>`;
const vsel=(acc,ops,val,rot)=>`<label>${vesc(rot)} <select data-acc="${acc}" aria-label="${vesc(rot)}">${ops.map(([v,t])=>`<option value="${vesc(v)}"${v===val?' selected':''}>${vesc(t)}</option>`).join('')}</select></label>`;
function vreset(st){Object.assign(st,{sel:null,foco:null,finSem:null,finCompra:null,prov:null,limite:150});}
function vpintar(G){
  const {root,B,st}=G, R=vranking(B,st);G.R=R;
  if(!R.visibles.some(r=>r.id===st.prod)){st.prod=R.visibles[0]?.id??null;st.u=null;vreset(st);}
  const D=R.sems.length>=4?vdetalle(B,R,st):null;G.D=D;
  const old=root.querySelector('.cv-ranking-scroll'), sx=old?.scrollLeft, sy=old?.scrollTop;
  const input=root.querySelector('[data-acc="q"]'), focus=input===root.getRootNode().activeElement, cursor=input?.selectionStart;
  const opciones=[['Rango','Fecha elegida'],['3m','Últimos 3 meses'],['12m','Últimos 12 meses'],['24m','Últimos 24 meses'],['Todo','Todo el histórico']];
  // Cambiar el grano, tramo o proveedor no sustituye miles de celdas del ranking.
  const rankKey=JSON.stringify([st.op,st.q,st.orden,st.verVol,st.verDisp,st.verImpacto,st.ayuda,st.limite]);
  const lower=D?`<div class="cv-lower">${vrenderDetalle(G)}${vrenderAnalisis(G)}</div>`:'';
  if(rankKey!==G.rankKey){root.innerHTML=`<section class="cv-card cv-rank">
    <div class="cv-head cv-native-space"><h3>Volatilidad de insumos</h3>${vsel('op',opciones,st.op,'Ventana')}${vbot('ayuda','', '?',st.ayuda,'Cómo se calcula')}</div>
    <div class="cv-toolbar"><input type="search" data-acc="q" aria-label="Buscar insumo" placeholder="Buscar cualquier insumo…" value="${vesc(st.q)}">
      ${vsel('orden',[['volatilidad','Volatilidad'],['dispersion','Dispersión'],['gasto','Gasto'],['impacto','Impacto del precio · S/']],st.orden,'Ordenar por')}
      <label><input type="checkbox" data-acc="verVol"${st.verVol?' checked':''}>Volatilidad</label><label><input type="checkbox" data-acc="verDisp"${st.verDisp?' checked':''}>Dispersión</label>
      <label><input type="checkbox" data-acc="verImpacto"${st.verImpacto?' checked':''}>Impacto S/</label><span class="cv-push"></span>${vbot('excel','', 'Excel')}</div>
    <div class="cv-caption">${vfecha(R.rango[0])}–${vfecha(R.rango[1])} · El ranking mide ${R.ult.length} semanas: ${R.ult.length?vfecha(R.ri)+'–'+vfecha(R.rf):'sin compras'} · ${R.n} insumos regulares.</div>
    ${st.ayuda?`<div class="cv-help">${vbot('ayuda','','Cerrar')}<p>Volatilidad: suma de los cambios absolutos del cierre semanal. Dispersión: desvío muestral / promedio de los precios; necesita cinco compras válidas.</p><p>El ranking exige S/ 400 de gasto y compras en el 75% de las últimas cinco semanas. El buscador incluye también los demás insumos y explica el motivo.</p><p>La historia se desliza horizontalmente; las columnas resaltadas suman al puntaje. Semana dibuja primera, última, mínimo y máximo; una semana sin compras repite el cierre previo. Compra conserva cada operación, incluso las del mismo día.</p><p>Arrastrá en el gráfico para analizar un tramo. En Compra se seleccionan días completos. Proveedores y el puente separan unidades; precio ponderado = suma(precio × cantidad) / cantidad. Impacto del precio compara contra el tramo anterior de igual duración y se informa sin base cuando falta historia.</p></div>`:''}
    ${R.sems.length<4?'<p class="cv-empty">Se necesitan al menos cuatro semanas con compras. Ampliá la ventana o elegí otras fechas.</p>':vrenderRank(G)}
    <div class="cv-foot"><span>${R.visibles.length} resultados${st.q?' · incluye coincidencias fuera del ranking':''}</span><span>Historia ${vbot('hist',-1,'‹')}${vbot('hist',1,'›')} · últimas columnas resaltadas</span></div>
  </section>${lower}`;G.rankKey=rankKey;}
  else {const actual=root.querySelector('.cv-lower');if(actual)actual.outerHTML=lower;else if(lower)root.insertAdjacentHTML('beforeend',lower);}
  root.querySelectorAll('.cv-ranking-scroll tr[data-acc="prod"]').forEach(e=>e.classList.toggle('chosen',+e.dataset.v===st.prod));
  const scroll=root.querySelector('.cv-ranking-scroll');
  if(scroll){scroll.scrollLeft=G.rankOp!==st.op||sx==null?scroll.scrollWidth:sx;scroll.scrollTop=sy||0;G.rankOp=st.op;}
  if(focus){const el=root.querySelector('[data-acc="q"]');el.focus({preventScroll:true});el.setSelectionRange(cursor,cursor);}
  vplot(G);vpuentePlot(G);
}
function vrenderRank(G){
  const {R,st,B}=G;
  if(!R.visibles.length)return '<p class="cv-empty">Ningún insumo coincide en esta ventana. Probá una ventana más amplia.</p>';
  const columnas=R.sems.slice(1), esc=(s,i)=>i>=columnas.length-(R.ult.length-1)?' class="cv-measured"':'';
  const metrics=(tag,r)=>`${st.verVol?`<${tag} class="cv-num">${r?vnum(r.volatilidad,1):'Volatilidad'}</${tag}>`:''}${st.verDisp?`<${tag} class="cv-num">${r?vok(r.dispersion)?vnum(r.dispersion*100)+'%':'—':'Dispersión'}</${tag}>`:''}${st.verImpacto?`<${tag} class="cv-num">${r?vsol(r.impacto,0):'Impacto S/'}</${tag}>`:''}`;
  return `<div class="cv-ranking-scroll cv-scroll"><table><thead><tr><th class="cv-sticky">Insumo</th>${metrics('th')}${columnas.map((s,i)=>`<th${esc(s,i)} title="${i>=columnas.length-(R.ult.length-1)?'Suma al puntaje':'Historia; no suma al puntaje'}">${vdm(s)}–${vdm(s+6)}</th>`).join('')}</tr></thead>
    <tbody>${R.visibles.slice(0,st.limite).map(r=>{
      const pide=Math.ceil(.75*R.ult.length-1e-9), motivo=r.candidato?'':`Fuera del ranking: ${r.cobertura} de ${R.ult.length} semanas (pide ${pide}); gasto ${vsol(r.gasto,0)} (pide S/ 400)`;
      return `<tr data-acc="prod" data-v="${r.id}" class="${r.id===st.prod?'chosen':''}" tabindex="0" role="button" aria-label="Ver ${vesc(r.nombre)}"><td class="cv-sticky" title="${vesc(motivo||`${r.nombre} · volatilidad ${vnum(r.volatilidad,1)}`)}"><b>${vesc(r.nombre)}</b>${!r.candidato?'<small>Fuera del ranking</small>':''}${r.unidades.length>1?`<small>Varias unidades · serie en ${vesc(B.P.um_c[r.u])}</small>`:''}</td>${metrics('td',r)}${columnas.map((s,i)=>{const p=r.cierres[i], c=r.cierres[i+1], d=vpct(c,p);return `<td${esc(s,i)} title="Cierre del ${vfecha(s-7)}: ${vsol(p)}; cierre del ${vfecha(s)}: ${vsol(c)}"><span style="color:${vcolor(d)}">${vok(d)?vpor(d):'—'}</span> <small>${vnum(p,2)} → ${vnum(c,2)}</small></td>`;}).join('')}</tr>`;
    }).join('')}</tbody></table></div>`;
}
function vrenderDetalle(G){
  const {D,R,st,B}=G, {info}=D;
  const nombres=info.unidades.map(u=>[String(u),B.P.um_c[u]]), cs=vsemanas(vrango(D.hist||[],...R.rango),R.sems).map(w=>w.c).slice(-R.ult.length), cambio=vpct(cs.at(-1),cs[0]);
  const ulabel=B.P.um_c[D.u], mixto=info.unidades.length>1;
  return `<section class="cv-card cv-detail"><div class="cv-head"><h3 title="${vesc(info.nombre)}">${vesc(info.nombre)}</h3><span class="cv-push"></span>${mixto?vsel('u',nombres,String(D.u),'Unidad'):`<span>${vesc(ulabel)}</span>`}</div>
    <div class="cv-caption">${mixto?'La serie se separa por unidad. ':''}Indicadores del ranking · ${vfecha(R.ri)}–${vfecha(R.rf)}</div>
    <div class="cv-kpis">${vkpi('Último cierre',vsol(cs.at(-1)),`por ${B.P.um_c[D.u]}`)}${vkpi('Cambio',vpor(cambio),'entre cierres',vcolor(cambio))}${vkpi('Volatilidad',vnum(vscore(cs),1),`${R.ult.length-1} variaciones`)}</div>
    <div class="cv-toolbar">${vseg('gran',['Semana','Compra'],st.gran)}<span class="cv-push"></span>${vbot('limpiar','','Restablecer tramo',!!st.sel)}</div>
    ${D.vacio?'<p class="cv-empty">Sin compras con precio válido en esta unidad.</p>':`<div class="cv-navigate">${vbot('nav',-1,'‹')}<input type="range" data-acc="fin" aria-label="Mover la historia" min="${D.n-1}" max="${D.items.length-1}" value="${D.fin}">${vbot('nav',1,'›')}</div><div class="cv-plot"></div><div class="cv-legend"></div>
    <div class="cv-caption">Arrastrá para elegir un tramo · ${vfecha(D.rango[0])}–${vfecha(D.rango[1])} · ${D.scope.length} compras (días completos)${st.prov!=null?' · proveedor filtrado':''}</div>
    <div class="cv-kpis cv-scope-kpis">${vkpi('Precio ponderado',vsol(D.total.precio),`por ${vesc(ulabel)}`)}${vkpi('Cantidad',vnum(D.total.cant,2),ulabel)}${vkpi('Compra valorizada',vsol(D.total.valor,0),'precio × cantidad')}</div>
    <div class="cv-caption" title="Suma de (precio − mínimo del tramo) × cantidad. Techo teórico: supone que el mínimo estuvo siempre disponible.">Sobrecosto: <b>${vsol(D.sobre.sobre,0)} (${vnum(D.sobre.pct,1)}%)</b> · Dispersión: ${vok(D.dispersion)?vnum(D.dispersion*100)+'%':'sin cinco compras válidas'}</div>`}
    <div class="cv-foot">${D.total?.omitidas?`${D.total.omitidas} compras sin precio o cantidad positiva quedan fuera del ponderado y del puente.`:'La comparación usa precios unitarios en soles.'} El sobrecosto es un techo teórico.</div></section>`;
}
function vtabla(headers,rows){return `<div class="cv-scroll cv-analysis-scroll"><table><thead><tr>${headers.map(h=>`<th>${vesc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;}
function vrenderAnalisis(G){
  const {st,D,B}=G;
  if(D.vacio)return '<section class="cv-card cv-analysis"><p class="cv-empty">Elegí otra unidad para consultar sus compras.</p></section>';
  let cuerpo='';
  if(st.tab==='Compras'){
    const cab=['Fecha',...(B.P.hay_doc?['Documento']:[]),'Proveedor',`Cantidad (${B.P.um_c[D.u]})`,'Precio unitario','vs anterior'];
    const filas=D.tabla.map(r=>{const i=D.rows.findIndex(x=>x.id===r.id),prev=D.rows[i-1]?.p??D.previo,d=i>=0?vpct(r.p,prev):null;
      return {r,d};});
    G.exportTable={nombre:'Compras',cabeza:cab,filas:filas.map(({r,d})=>[vfecha(r.f),...(B.P.hay_doc?[B.P.docs[r.doc]]:[]),B.P.provs[r.prov],r.q,r.p,d])};
    const elegido=D.items[D.foco].f;
    const titulo=st.gran==='Semana'?`Semana ${vdm(elegido)}–${vdm(Math.min(elegido+6,G.R.rango[1]))}`:`Compra del ${vfecha(elegido)}`;
    cuerpo=`<div class="cv-toolbar">${vseg('modo',['Elegida','Tramo'],st.modo)}<small>${st.modo==='Elegida'?titulo:'Todas las compras del tramo'}</small></div>`+
      vtabla(cab,filas.slice(0,st.limite).map(({r,d})=>`<tr><td>${vdm(r.f)}</td>${B.P.hay_doc?`<td>${vesc(B.P.docs[r.doc])}</td>`:''}<td title="${vesc(B.P.provs[r.prov])}">${vesc(B.P.provs[r.prov])}</td><td class="cv-num">${vnum(r.q,2)}</td><td class="cv-num">${vsol(r.p)}</td><td class="cv-num" style="color:${vcolor(d)}">${vpor(d)}</td></tr>`));
  }else if(st.tab==='Proveedores'){
    const cab=['Proveedor',`Precio pond./${B.P.um_c[D.u]}`,'Cantidad','Valorizado','Compras','Última'];
    G.exportTable={nombre:'Proveedores',cabeza:[...cab,'Último precio'],filas:D.proveedores.map(r=>[B.P.provs[r.id],r.precio,r.cant,r.valor,r.n_compras,vfecha(r.ultima),r.ultimo])};
    cuerpo='<p class="cv-caption">Un clic filtra las compras y el puente a ese proveedor. El precio ponderado pesa cada cantidad; una muestra pequeña se indica.</p>'+
      vtabla(cab,D.proveedores.map(r=>`<tr data-acc="prov" data-v="${r.id}" tabindex="0" role="button" aria-label="Filtrar ${vesc(B.P.provs[r.id])}" class="${st.prov===r.id?'chosen':''}"><td>${vesc(B.P.provs[r.id])}${r.n<5?`<small>Muestra de ${r.n} compras válidas</small>`:''}</td><td class="cv-num">${vsol(r.precio)}</td><td class="cv-num">${vnum(r.cant,2)}</td><td class="cv-num">${vsol(r.valor,0)}</td><td class="cv-num">${r.n_compras}</td><td>${vdm(r.ultima)}<small>${vsol(r.ultimo)}</small></td></tr>`));
  }else{
    const p=D.puente;
    G.exportTable={nombre:'Cambio gasto',cabeza:['Concepto','Soles'],filas:[['Anterior valorizado',p.previo.valor],['Por cantidad',p.cantidad],['Por precio',p.precio],['Actual valorizado',p.actual.valor],['Variación total',p.delta]]};
    cuerpo=`<p class="cv-caption">${vfecha(D.ip)}–${vfecha(D.fp)} → ${vfecha(D.rango[0])}–${vfecha(D.rango[1])}. Tramos de igual duración (${D.rango[1]-D.rango[0]+1} días).</p>`+
      (p.delta==null?`<p class="cv-empty">${!p.completo?'El histórico no cubre todo el tramo anterior.':'Sin compras con precio y cantidad positiva en ambos tramos.'} No hay base comparable para separar precio y cantidad.</p>`:
      `<div class="cv-bridge-plot"></div><div class="cv-kpis">${vkpi('Por precio',vsol(p.precio,0),'(precio actual − anterior) × cantidad actual',vcolor(p.precio))}${vkpi('Por cantidad',vsol(p.cantidad,0),'(cantidad actual − anterior) × precio anterior',vcolor(p.cantidad))}</div><p class="cv-caption">Anterior: ${vnum(p.previo.cant,2)} ${vesc(B.P.um_c[D.u])} a ${vsol(p.previo.precio)} · Actual: ${vnum(p.actual.cant,2)} a ${vsol(p.actual.precio)}.</p>`)+
      `<p class="cv-caption">Valorizado = precio unitario × cantidad; puede diferir del valor registrado (${vsol(p.actual.registrado,0)} en el tramo actual). No representa un ahorro disponible.</p>`;
  }
  return `<section class="cv-card cv-analysis"><div class="cv-head"><h3>Análisis del tramo</h3><span class="cv-push"></span>${vbot('excel','','Excel')}</div>${vseg('tab',['Compras','Proveedores','Cambio del gasto'],st.tab)}
    <div class="cv-caption">${vfecha(D.rango[0])}–${vfecha(D.rango[1])} · ${vesc(B.P.um_c[D.u])}${st.prov!=null?' · '+vesc(B.P.provs[st.prov]):''}</div>
    ${st.prov!=null?`<div>${vbot('prov',st.prov,'Quitar filtro: '+B.P.provs[st.prov],true)}</div>`:''}${cuerpo}
    <div class="cv-foot">${st.tab==='Compras'?`${D.tabla.length} compras${st.prov!=null?' · proveedor filtrado':''}`:st.tab==='Proveedores'?`${D.proveedores.length} proveedores · cantidades positivas para el ponderado`:'La suma de ambos efectos es el cambio del valorizado.'}</div></section>`;
}
function vplot(G){
  const el=G.root.querySelector('.cv-plot'),{D,st,B}=G;if(!el||D?.vacio)return;
  const w=el.clientWidth||450,h=Math.max(145,el.clientHeight||200), L=44,T=27,bot=h-30,step=(w-L-12)/D.vista.length;
  const compra=st.gran==='Compra', lo=Math.min(...D.vista.map(r=>compra?r.p:r.l)), hi=Math.max(...D.vista.map(r=>compra?r.p:r.h));
  const pad=Math.max((hi-lo)*.12,hi*.04,.05), ymin=Math.max(0,lo-pad), ymax=hi+pad,y=v=>bot-(v-ymin)/(ymax-ymin)*(bot-T),x=i=>L+step*(i+.5);
  const ventas=new Map();for(const r of D.vista.flatMap(r=>compra?[r]:r.rows))ventas.set(r.prov,(ventas.get(r.prov)||0)+(r.p*r.q||0));
  const cols=new Map([...ventas].sort((a,b)=>b[1]-a[1]||a[0]-b[0]).map(([id],i)=>[id,vpal[i%vpal.length]]));
  const leyenda=G.root.querySelector('.cv-legend');if(leyenda)leyenda.innerHTML=compra?[...cols].map(([id,c])=>`<span title="${vesc(B.P.provs[id])}"><i style="background:${c}"></i>${vesc(B.P.provs[id])}</span>`).join(''):'Primera y última compra; mínimo y máximo de la semana.';
  let html='';
  for(let i=0;i<4;i++){const v=ymin+(ymax-ymin)*i/3, yy=y(v);html+=`<line class="cv-grid" x1="${L}" x2="${w-6}" y1="${yy}" y2="${yy}"/><text class="cv-axis" text-anchor="end" x="${L-6}" y="${yy+3}">${vnum(v,hi<10?2:0)}</text>`;}
  const maxG=Math.max(1,...D.vista.map(r=>compra?r.p*r.q||0:0));
  D.vista.forEach((r,i)=>{
    const xx=x(i), selected=st.sel?r.f<=st.sel[1]&&(compra?r.f:r.f+6)>=st.sel[0]:i+D.ini===D.foco;
    if(selected)html+=`<rect x="${xx-step/2}" y="${T-16}" width="${step}" height="${bot-T+16}" fill="var(--accent)" opacity=".065"/>`;
    if(compra){const col=cols.get(r.prov),rad=3+7*Math.sqrt(Math.max(0,r.p*r.q||0)/maxG);html+=`<circle cx="${xx}" cy="${y(r.p)}" r="${rad}" fill="${col}" stroke="var(--bg-card)" stroke-width="1.5"/>`;}
    else{const col=r.c>r.o?'var(--danger)':r.c<r.o?'var(--success)':'var(--text-secondary)', ancho=Math.min(34,step*.44),bh=Math.abs(y(r.o)-y(r.c));
      html+=`<line x1="${xx}" x2="${xx}" y1="${y(r.h)}" y2="${y(r.l)}" stroke="${col}" stroke-width="1.4"/>`;
      html+=bh<1?`<line x1="${xx-ancho/2}" x2="${xx+ancho/2}" y1="${y(r.c)}" y2="${y(r.c)}" stroke="${col}" stroke-width="1.8"/>`:`<rect x="${xx-ancho/2}" y="${Math.min(y(r.o),y(r.c))}" width="${ancho}" height="${bh}" rx="1" fill="${col}"/>`;
    }
    const precio=compra?r.p:r.c;if(D.vista.length<=8)html+=`<text class="cv-price" text-anchor="middle" x="${xx}" y="${y(compra?r.p:r.h)-12}">${vnum(precio,2)}</text>`;
    html+=`<text class="cv-axis" text-anchor="middle" x="${xx}" y="${h-10}">${compra?vdm(r.f):vdm(r.f)+'–'+vdm(r.f+6)}</text>`;
    const tip=compra?`${vfecha(r.f)} · ${B.P.provs[r.prov]} · ${vsol(r.p)} · ${vnum(r.q,2)} ${B.P.um_c[D.u]}`:r.rows.length?`Semana ${vfecha(r.f)}: primera ${vsol(r.o)}, última ${vsol(r.c)}, mínimo ${vsol(r.l)}, máximo ${vsol(r.h)}`:`Semana ${vfecha(r.f)}: sin compras; se repite ${vsol(r.c)}`;
    html+=`<rect data-hit="${i}" x="${xx-step/2}" y="0" width="${step}" height="${h}" fill="transparent" tabindex="0" role="button" aria-label="${vesc(tip)}"><title>${vesc(tip)}</title></rect>`;
  });
  el.innerHTML=`<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-label="Evolución de precio por ${st.gran.toLowerCase()}">${html}</svg>`;
  G.geometry={el,L,step};
}
function vpuentePlot(G){
  const el=G.root.querySelector('.cv-bridge-plot');if(!el)return;
  const p=G.D.puente,w=el.clientWidth||440,h=170,L=24,T=22,bot=h-29;
  const puntos=[{n:'Anterior',a:0,b:p.previo.valor,total:true},{n:'Cantidad',a:p.previo.valor,b:p.previo.valor+p.cantidad},
    {n:'Precio',a:p.previo.valor+p.cantidad,b:p.actual.valor},{n:'Actual',a:0,b:p.actual.valor,total:true}];
  const max=Math.max(1,...puntos.flatMap(r=>[r.a,r.b])), min=Math.min(0,...puntos.flatMap(r=>[r.a,r.b])), y=v=>bot-(v-min)/(max-min)*(bot-T),step=(w-L-12)/4;
  el.innerHTML=`<svg width="${w}" height="${h}">${puntos.map((r,i)=>{const x=L+i*step+8,valor=r.total?r.b:r.b-r.a,col=r.total?'var(--accent)':vcolor(valor);return `<rect x="${x}" y="${Math.min(y(r.a),y(r.b))}" width="${step-16}" height="${Math.max(1,Math.abs(y(r.a)-y(r.b)))}" fill="${col}" opacity=".8"/><text class="cv-price" text-anchor="middle" x="${x+(step-16)/2}" y="${Math.min(y(r.a),y(r.b))-7}">${vnum(valor,0)}</text><text class="cv-axis" text-anchor="middle" x="${x+(step-16)/2}" y="${h-9}">${r.n}</text>`;}).join('')}</svg>`;
}
function vexcel(G){
  const {B,st,R,D}=G;
  const hojas=[{nombre:'Ranking',cabeza:['Insumo','Unidad de la serie','Volatilidad','Dispersión','Gasto últimas semanas','Impacto del precio','Fuera del ranking'],
    filas:R.visibles.map(r=>[r.nombre,B.P.um_c[r.u],r.volatilidad,r.dispersion,r.gasto,r.impacto,!r.candidato])}];
  if(D&&!D.vacio&&G.exportTable)hojas.push(G.exportTable);
  const filas=[['Ventana',st.op],['Fecha inicial',viso(R.rango[0])],['Fecha final',viso(R.rango[1])],['Buscar',st.q],['Orden',st.orden],
    ['Ranking mide',`${viso(R.ri)} / ${viso(R.rf)}`],['Moneda','Soles; se excluyen dólares'],['Precio ponderado','Suma(precio unitario × cantidad) / cantidad; sólo cantidades positivas'],
    ['Sobrecosto','Techo teórico contra el mínimo observado; no es un ahorro disponible']];
  for(const [rot,vs] of Object.entries(B.P.filtros||{}))filas.push([rot,vs.length?vs.join(' / '):'Todos']);
  if(D&&!D.vacio)filas.push(['Producto',D.info.nombre],['Unidad',B.P.ums[D.u]],['Tramo actual',`${viso(D.rango[0])} / ${viso(D.rango[1])}`],
    ['Tramo anterior',`${viso(D.ip)} / ${viso(D.fp)}`],['Proveedor',st.prov==null?'Todos':B.P.provs[st.prov]],['Tabla',st.tab],['Compras',st.modo],
    ['Compras omitidas del ponderado',D.total.omitidas],['Base anterior completa',D.puente.completo]);
  hojas.push({nombre:'Contexto',cabeza:['Dato','Valor'],filas});
  bajar(`Volatilidad_${archivo(D?.info.nombre||'ranking')}.xlsx`,libro(hojas));
}
function vconectar(G){
  const {root}=G;
  root.addEventListener('click',ev=>{
    const e=ev.target.closest('[data-acc]');if(!e||!root.contains(e)||e.matches('input,select'))return;
    const {acc,v}=e.dataset,{st,D}=G;
    if(acc==='prod'){if(st.prod!==+v){st.prod=+v;st.u=null;vreset(st);}}
    else if(acc==='gran'){st.gran=v;st.sel=null;st.foco=null;st.modo=v==='Compra'?'Tramo':'Elegida';}
    else if(acc==='nav'){st[st.gran==='Compra'?'finCompra':'finSem']=Math.max(D.n-1,Math.min(D.items.length-1,D.fin+(+v)*D.n));st.sel=null;st.foco=null;}
    else if(acc==='limpiar'){st.sel=null;st.foco=null;}
    else if(acc==='prov'){st.prov=st.prov===+v?null:+v;}
    else if(acc==='tab'||acc==='modo'){st[acc]=v;st.limite=150;}
    else if(acc==='ayuda')st.ayuda=!st.ayuda;
    else if(acc==='excel'){vexcel(G);return;}
    else if(acc==='hist'){const s=root.querySelector('.cv-ranking-scroll');s?.scrollBy({left:(+v)*Math.max(120,s.clientWidth-200),behavior:'smooth'});return;}
    else return;
    vpintar(G);
  });
  root.addEventListener('input',ev=>{
    const e=ev.target,{acc}=e.dataset,{st,D}=G;
    if(acc==='q'){st.q=e.value;st.limite=150;vpintar(G);}
    if(acc==='fin'){st[st.gran==='Compra'?'finCompra':'finSem']=+e.value;st.sel=null;st.foco=null;vpintar(G);}
  });
  root.addEventListener('change',ev=>{
    const e=ev.target,{acc}=e.dataset,{st}=G;
    if(acc==='op'){st.op=e.value;st.u=null;vreset(st);}
    else if(acc==='orden'){st.orden=e.value;if(st.orden==='dispersion')st.verDisp=true;if(st.orden==='impacto')st.verImpacto=true;}
    else if(['verVol','verDisp','verImpacto'].includes(acc)){st[acc]=e.checked;if(acc==='verDisp')st.orden=e.checked?'dispersion':'volatilidad';}
    else if(acc==='u'){st.u=+e.value;vreset(st);}
    else return;
    vpintar(G);
  });
  root.addEventListener('keydown',ev=>{
    if(ev.key==='Escape'&&G.st.ayuda){G.st.ayuda=false;vpintar(G);}
    const row=ev.target.closest('tr[data-acc]');if(row&&(ev.key==='Enter'||ev.key===' ')){ev.preventDefault();row.click();}
    const hit=ev.target.closest('[data-hit]');if(hit&&(ev.key==='Enter'||ev.key===' ')){ev.preventDefault();velegir(G,+hit.dataset.hit,+hit.dataset.hit);}
  });
  root.addEventListener('scroll',ev=>{
    const el=ev.target;if(!el.matches('.cv-scroll'))return;
    if(el.scrollTop+el.clientHeight>=el.scrollHeight-80&&G.st.limite<(el.matches('.cv-ranking-scroll')?G.R.visibles.length:G.D?.tabla?.length||0)){
      const x=el.scrollLeft,y=el.scrollTop,clase=el.matches('.cv-ranking-scroll')?'.cv-ranking-scroll':'.cv-analysis-scroll';
      G.st.limite+=150;vpintar(G);const nuevo=root.querySelector(clase);if(nuevo){nuevo.scrollLeft=x;nuevo.scrollTop=y;}
    }
  },true);
  root.addEventListener('pointerdown',ev=>{
    const h=ev.target.closest('[data-hit]');if(!h||ev.button!==0)return;
    G.drag={i:+h.dataset.hit,j:+h.dataset.hit,x:ev.clientX,y:ev.clientY,id:ev.pointerId};
  });
  const signal=G.abort.signal;
  window.addEventListener('pointermove',ev=>{
    if(!G.drag||!root.isConnected)return;
    const {el,L,step}=G.geometry,b=el.getBoundingClientRect();
    G.drag.j=Math.max(0,Math.min(G.D.vista.length-1,Math.floor((ev.clientX-b.left-L)/step)));
    // No sustituir el SVG durante el arrastre: el puntero conserva su blanco.
    root.querySelectorAll('[data-hit]').forEach(h=>h.classList.toggle('cv-drag',+h.dataset.hit>=Math.min(G.drag.i,G.drag.j)&&+h.dataset.hit<=Math.max(G.drag.i,G.drag.j)));
  },{signal});
  window.addEventListener('pointerup',ev=>{
    const d=G.drag;G.drag=null;if(!d||!root.isConnected)return;
    if(ev.pointerType==='touch'&&Math.abs(ev.clientY-d.y)>20&&Math.abs(ev.clientY-d.y)>Math.abs(ev.clientX-d.x))return;
    velegir(G,d.i,d.j);
  },{signal});
  window.addEventListener('pointercancel',()=>{G.drag=null;root.querySelectorAll('.cv-drag').forEach(h=>h.classList.remove('cv-drag'));},{signal});
}
function velegir(G,i,j){
  const {D,st}=G,a=D.vista[Math.min(i,j)],b=D.vista[Math.max(i,j)];if(!a||!b)return;
  st.sel=[a.f,st.gran==='Compra'?b.f:b.f+6];st.foco=D.ini+j;st.modo=i===j?'Elegida':'Tramo';vpintar(G);
}
window.__cvUI={inicial:vinicial,pintar:vpintar};
export default function(component){
  const {data:P,parentElement}=component;if(!P)return;
  let G=window.__cpVol,st=G?.st||vinicial(P.inicial);
  const rangoAnterior=G?.B.P.planes.Rango.join('|');
  G?.abort?.abort();G?.observer?.disconnect();if(G?.resizeTimer)clearTimeout(G.resizeTimer);
  if(G&&G.B.P.sello!==P.sello){
    const nombre=G.B.P.prods[st.prod], id=P.prods.indexOf(nombre);st.prod=id<0?null:id;
    vreset(st);st.u=null;if(rangoAnterior!==P.planes.Rango.join('|'))st.op='Rango';
  }
  let root=parentElement.querySelector('.cvol');if(!root){root=document.createElement('div');root.className='cvol';parentElement.appendChild(root);}
  G={root,st,B:G?.B.P.sello===P.sello?G.B:vleer(P),abort:new AbortController()};window.__cpVol=G;
  vconectar(G);vpintar(G);
  let ancho=root.clientWidth;
  G.observer=new ResizeObserver(()=>{if(Math.abs(root.clientWidth-ancho)<2)return;ancho=root.clientWidth;clearTimeout(G.resizeTimer);G.resizeTimer=setTimeout(()=>{if(root.isConnected){vplot(G);vpuentePlot(G);}},80);});G.observer.observe(root);
}
