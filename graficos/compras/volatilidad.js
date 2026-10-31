// Compras > Precios, la vieja Volatilidad (#718, #770). El Excel compartido se antepone a este módulo.
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

function vpuentePlot(G){
  const el=G.root.querySelector('.cv-bridge-plot');if(!el)return;
  const p=G.D.puente,w=el.clientWidth||440,h=170,L=24,T=22,bot=h-29;
  const puntos=[{n:'Anterior',a:0,b:p.previo.valor,total:true},{n:'Cantidad',a:p.previo.valor,b:p.previo.valor+p.cantidad},
    {n:'Precio',a:p.previo.valor+p.cantidad,b:p.actual.valor},{n:'Actual',a:0,b:p.actual.valor,total:true}];
  const max=Math.max(1,...puntos.flatMap(r=>[r.a,r.b])), min=Math.min(0,...puntos.flatMap(r=>[r.a,r.b])), y=v=>bot-(v-min)/(max-min)*(bot-T),step=(w-L-12)/4;
  el.innerHTML=`<svg width="${w}" height="${h}">${puntos.map((r,i)=>{const x=L+i*step+8,valor=r.total?r.b:r.b-r.a,col=r.total?'var(--accent)':vcolor(valor);return `<rect x="${x}" y="${Math.min(y(r.a),y(r.b))}" width="${step-16}" height="${Math.max(1,Math.abs(y(r.a)-y(r.b)))}" fill="${col}" opacity=".8"/><text class="cv-price" text-anchor="middle" x="${x+(step-16)/2}" y="${Math.min(y(r.a),y(r.b))-7}">${vnum(valor,0)}</text><text class="cv-axis" text-anchor="middle" x="${x+(step-16)/2}" y="${h-9}">${r.n}</text>`;}).join('')}</svg>`;
}
// ── «Precios» (regla #770): lista por impacto en soles y ficha al costado ────
// La base es la de Compras › Producto (`volatilidad_datos.precios`): en soles, con
// su habitual y su marca. «Se mueve» y «En semanas» siguen saliendo de `vbase`.
const VCOL=['var(--serie-0)','var(--serie-1)','var(--serie-2)','var(--serie-3)','var(--serie-4)','var(--serie-5)','var(--serie-6)'];
const MESES_C=['ene','feb','mar','abr','may','jun','jul','ago','set','oct','nov','dic'];
function pleer(B){
  if(B.PR!==undefined)return B.PR;const X=B.P.precios;if(!X){B.PR=null;return null;}
  const base=vdia(X.base),L=X.filas.map(r=>{const p=X.prods[r[0]];return {p:r[0],nom:p[0],fam:p[1],sub:p[2],um:p[3],d:base+r[1],prov:r[2],doc:r[3],c:r[4]||0,v:r[5]||0,ref:r[6],fl:r[7]||0};});
  const por=new Map();for(const l of L){if(!por.has(l.p))por.set(l.p,[]);por.get(l.p).push(l);}
  for(const a of por.values())a.sort((x,y)=>x.d-y.d);
  B.PR={L,por,provs:X.provs,docs:X.docs,prods:X.prods,desde:base};return B.PR;
}
const pok=l=>l.fl===0&&l.c>0;
const paño=n=>{const t=new Date(n*VDIA),y=t.getUTCFullYear(),m=t.getUTCMonth(),d=t.getUTCDate();return Math.min(Date.UTC(y-1,m,d),Date.UTC(y-1,m+1,0))/VDIA;};
const pmeses=fin=>{const t=new Date(fin*VDIA),y=t.getUTCFullYear(),m=t.getUTCMonth(),o=[];for(let i=12;i>=0;i--){const a=Date.UTC(y,m-i,1)/VDIA,b=Date.UTC(y,m-i+1,0)/VDIA,x=new Date(a*VDIA);o.push([a,b,`${MESES_C[x.getUTCMonth()]} ${String(x.getUTCFullYear()).slice(2)}`]);}return o;};
// Una fila por producto del rango: las cuentas de `producto._resumen`.
function pfilas(B,st){
  const PR=pleer(B);if(!PR)return {rows:[],sube:[],baja:[],rev:[],n80:0,total:0};
  const [R0,R1]=B.planes[st.op]||B.planes['12m'],dias=R1-R0+1,con=st.contra||'hab';
  const [bA,bB]=con==='ant'?[R0-dias,R0-1]:con==='ano'?[paño(R0),paño(R1)]:[null,null],hayB=con==='hab'||bA>=PR.desde;
  const meses=pmeses(R1),met=new Map();
  for(const r of vbase(B,st.op).rank)met.set(String(r.nombre).trim(),r);
  const rows=[];
  for(const [p,ls] of PR.por){
    const rg=ls.filter(l=>l.d>=R0&&l.d<=R1);if(!rg.length)continue;
    const bu=rg.filter(pok),val=vsuma(rg,'v'),cOk=vsuma(bu,'c'),vOk=vsuma(bu,'v'),pp=cOk>0?vOk/cOk:null;let ref=null,im=null,pct=null;
    if(con==='hab'){const cr=bu.filter(l=>l.ref!=null),rc=cr.reduce((s,l)=>s+l.ref*l.c,0),vr=vsuma(cr,'v'),cc=vsuma(cr,'c');if(rc>0){ref=rc/cc;im=vr-rc;pct=vr/rc-1;}}
    else if(hayB){const bs=ls.filter(l=>l.d>=bA&&l.d<=bB&&pok(l)),c0=vsuma(bs,'c'),v0=vsuma(bs,'v');if(c0>0&&pp!=null){ref=v0/c0;im=(pp-ref)*cOk;pct=pp/ref-1;}}
    const prs=bu.map(l=>l.v/l.c),serie=meses.map(([a,b])=>{const w=ls.filter(l=>l.d>=a&&l.d<=b&&pok(l)),c=vsuma(w,'c');return c>0?vsuma(w,'v')/c:null;}),m=met.get(String(rg[0].nom).trim());
    rows.push({p,n:rg[0].nom,fam:rg[0].fam,sub:rg[0].sub,um:rg[0].um,val,cOk,pp,ref,im,pct,min:prs.length?Math.min(...prs):null,max:prs.length?Math.max(...prs):null,
      nfl:rg.filter(l=>l.fl).length,rg,serie,nl:rg.length,disp:m?m.dispersion:null,vol:m?m.volatilidad:null});
  }
  rows.sort((a,b)=>b.val-a.val);
  const total=vsuma(rows,'val');let ac=0;for(const r of rows){r.a80=ac/(total||1)<.8;ac+=r.val;}
  const sube=rows.filter(r=>r.im!=null&&r.im>=1),baja=rows.filter(r=>r.im!=null&&r.im<=-1),rev=rows.filter(r=>r.nfl);
  return {rows,sube,baja,rev,n80:rows.filter(r=>r.a80).length,total,up:vsuma(sube,'im'),dn:vsuma(baja,'im'),R0,R1,meses};
}
window.__cvCalc.precios=pfilas;
function vinicial(op='12m'){return {op,q:'',orden:'volatilidad',verVol:false,verDisp:false,verImpacto:false,prod:null,u:null,
  gran:'Semana',sel:null,foco:null,finSem:null,finCompra:null,prov:null,tab:'Compras',modo:'Elegida',limite:150,ayuda:false,
  contra:'hab',ver:'80',kpi:'todos',ord:{k:'im',d:-1},p:null,ptab:'curva',pgran:'Compra',amp:null,tr:null,off:{},menu:null};}
const pcv=v=>!vok(v)?'':v>.5?'rojo':v<-.5?'verde':'';
const ps0=v=>vok(v)?`${v<-.5?'−':''}S/ ${vnum(Math.abs(v))}`:'—';
const pd0=v=>vok(v)?`${v>.5?'+':v<-.5?'−':''}S/ ${vnum(Math.abs(v))}`:'—';
const pp2=v=>vnum(v,2);
const pq=v=>vok(v)?new Intl.NumberFormat('en-US',{maximumFractionDigits:2}).format(v):'—';
const ppc=x=>!vok(x)?'—':Math.abs(x)<.0005?'0 %':`${x>0?'+':'−'}${vnum(Math.abs(x*100),Math.abs(x)<.1?1:0)} %`;
const pfc=n=>{const t=new Date(n*VDIA);return `${t.getUTCDate()} ${MESES_C[t.getUTCMonth()]}`;};
const pn=(n,t='producto')=>`${n} ${t}${n===1?'':'s'}`;
const pcontra={hab:'contra su precio habitual',ant:'contra el período anterior',ano:'contra el año pasado'};
const pcurvaK=h=>{if(!h?.length)return '';const a=Math.min(...h),b=Math.max(...h),r=b-a||1;return `<svg viewBox="0 0 100 34" preserveAspectRatio="none" aria-hidden="true"><polyline points="${h.map((v,i)=>`${(i*100/(h.length-1)).toFixed(1)},${(31-(v-a)/r*28).toFixed(1)}`).join(' ')}"/></svg>`;};
const pmini=s=>{const ix=s.map((x,i)=>[x,i]).filter(x=>x[0]!=null);if(!ix.length)return '';const v=ix.map(x=>x[0]),a=Math.min(...v),b=Math.max(...v),r=b-a,y=x=>r?18-(x-a)/r*16:10;return `<svg viewBox="0 0 68 20" aria-hidden="true"><polyline points="${ix.map(([x,i])=>`${(2+i*64/(s.length-1)).toFixed(1)},${y(x).toFixed(1)}`).join(' ')}"/></svg>`;};
function pmenuFam(B,st){const P=B.P.familias;if(!P)return '';const el=new Set(P.elegidas),n=P.elegidas.length||P.todas.length,ab=st.menu==='fam';
  return `<div class="cp-ms"><button class="cp-pil" data-acc="pmenu" data-v="fam" aria-expanded="${ab}">${n===P.todas.length?'Todas las familias':`Familias: ${n} de ${P.todas.length}`} ▾</button>${ab?`<div class="cp-pop">${P.todas.map(([f,v])=>`<label><input type="checkbox" data-acc="pfam" value="${vesc(f)}"${el.has(f)||!el.size?' checked':''}><span>${vesc(f.charAt(0)+f.slice(1).toLowerCase())}</span><small>${vesc(ps0(v))}</small></label>`).join('')}<p>Vale para todas las vistas de Compras.</p></div>`:''}</div>`;}
function pkpis(G,C){const {st,B}=G,neto=C.up+C.dn,PR=pleer(B),m=C.meses||[];
  if(!G.efMes||G.efKey!==B.P.sello+st.op){G.efKey=B.P.sello+st.op;G.efMes={net:[],up:[],dn:[]};for(const [a,b] of m){let n=0,u=0,d=0;for(const l of PR.L)if(l.d>=a&&l.d<=b&&pok(l)&&l.ref!=null){const e=l.v-l.ref*l.c;n+=e;if(e>0)u+=e;else d+=e;}G.efMes.net.push(n);G.efMes.up.push(u);G.efMes.dn.push(d);}}
  const k=(id,rot,val,cls,sub,h,tip)=>`<button class="cp-kpi${st.kpi===id?' on':''}" data-acc="pkpi" data-v="${id}" aria-pressed="${st.kpi===id}" title="${vesc(tip)}">${pcurvaK(h)}<span class="r">${vesc(rot)}</span><span class="v ${cls}">${vesc(val)}</span><span class="d">${vesc(sub)}</span></button>`;
  const may=(a,f)=>a.length?pd0(f(...a.map(r=>r.im))):'—';
  return k('todos','Efecto del precio',pd0(neto),pcv(neto),`${pcontra[st.contra]} · ${ps0(vsuma(C.sube,'val')+vsuma(C.baja,'val'))} comprados`,G.efMes.net,'Lo pagado menos lo que hubiera costado al precio de referencia, producto por producto, sin las compras para revisar.')
    +k('sube','Subieron',pd0(C.up),'rojo',`${pn(C.sube.length)} · el mayor ${may(C.sube,Math.max)}`,G.efMes.up,'Un clic deja sólo estos.')
    +k('baja','Bajaron',pd0(C.dn),'verde',`${pn(C.baja.length)} · el mayor ${may(C.baja,Math.min)}`,G.efMes.dn,'Un clic deja sólo estos.')
    +k('rev','Para revisar',pn(C.rev.length),C.rev.length?'nar':'',`${pn(vsuma(C.rev,'nfl'),'compra')} con precio raro, fuera de la cuenta`,null,'Una compra de S/ 50 o más a 2,5 veces su habitual o a menos de 0,4, o con decimales en una unidad que se cuenta entera.');}
function plista(G,C){const {st}=G,q=(st.q||'').trim().toLocaleLowerCase('es');
  let vis=C.rows.filter(r=>st.kpi==='todos'||(st.kpi==='sube'?r.im!=null&&r.im>=1:st.kpi==='baja'?r.im!=null&&r.im<=-1:r.nfl>0));
  if(q)vis=vis.filter(r=>q.split(/\s+/).every(w=>r.n.toLocaleLowerCase('es').normalize('NFD').replace(/[̀-ͯ]/g,'').includes(w.normalize('NFD').replace(/[̀-ͯ]/g,''))));
  else if(st.ver==='80'&&st.kpi==='todos')vis=vis.filter(r=>r.a80);
  const o=st.ord,kv=r=>({n:r.n,pp:r.pp,pct:r.pct,mv:r.disp,vo:r.vol,va:r.val,im:r.im}[o.k]);
  vis=[...vis].sort((a,b)=>{const x=kv(a),y=kv(b);if(x==null&&y==null)return b.val-a.val;if(x==null)return 1;if(y==null)return -1;return (typeof x==='string'?x.localeCompare(y):x-y)*o.d;});
  G.vis=vis;const amp=st.amp==='lista';
  const h=(k,t,tip='')=>`<button data-acc="pord" data-v="${k}" title="${vesc(tip)}">${vesc(t)}${o.k===k?(o.d>0?' ↑':' ↓'):''}</button>`;
  const fila=r=>`<tr class="${st.p===r.p?'chosen':''}"><td class="i" title="${vesc(r.n)}"><button class="cp-tn" data-acc="pprod" data-v="${r.p}"><span>${vesc(r.n)}</span></button></td><td>${pp2(r.pp)}</td><td>${pp2(r.ref)}</td><td class="${pcv(r.im)}">${ppc(r.pct)}</td><td class="fuerte ${pcv(r.im)}">${r.im==null?'—':pd0(r.im)}</td><td class="tenue" title="${r.disp==null?'Menos de cinco compras en el rango':`Mín – máx: ${pp2(r.min)} – ${pp2(r.max)}`}">${r.disp==null?'—':`±${vnum(r.disp*100)} %`}</td>${amp?`<td class="tenue">${r.min==null?'—':r.min===r.max?pp2(r.min):`${pp2(r.min)} – ${pp2(r.max)}`}</td><td class="tenue">${r.vol?`${vnum(r.vol)} %`:'—'}</td><td>${pq(r.cOk)} ${vesc(r.um)}</td><td>${ps0(r.val)}</td><td>${r.nl}</td>`:''}<td class="t">${pmini(r.serie)}${r.nfl?'<i class="cp-punto" title="Con compras para revisar"></i>':''}</td></tr>`;
  const tI=vis.reduce((s,r)=>s+(r.im||0),0);
  return `<div class="cp-fl"><div class="cp-seg" role="group" aria-label="Qué productos">${[['80','Los que hacen el 80 %',`${C.n80} productos que suman el 80 % de lo comprado`],['todos','Todos','Todos los productos comprados en el rango']].map(([k,t,tp])=>`<button class="${st.ver===k?'on':''}" data-acc="pver" data-v="${k}" title="${vesc(tp)}" aria-pressed="${st.ver===k}">${vesc(t)}</button>`).join('')}</div><span class="cp-sub">${pn(vis.length)}</span>${st.kpi!=='todos'?`<button class="cp-quita" data-acc="pkpi" data-v="${st.kpi}">${({sube:'Subieron',baja:'Bajaron',rev:'Para revisar'})[st.kpi]} ✕</button>`:''}<span class="cp-esp"></span><button class="cp-pil" data-acc="pamp" data-v="lista">${amp?'Ver la ficha':'Ampliar'}</button></div>
    <div class="cp-wrap"><table><thead><tr><th class="i">${h('n','Producto')}</th><th class="w-pr">${h('pp','Ahora','Precio ponderado del rango: soles ÷ cantidad, sin las compras para revisar')}</th><th class="w-pr">Contra</th><th class="w-pc">${h('pct','%')}</th><th class="w-im">${h('im','Impacto')}</th><th class="w-mv">${h('mv','Se mueve','Dispersión: cuánto se aleja el precio de cada compra de su promedio. Pide cinco compras.')}</th>${amp?`<th class="w-mm">Mín – máx</th><th class="w-x">${h('vo','En semanas','Volatilidad: suma de los cambios de precio de una semana a otra, en %')}</th><th class="w-x">Cantidad</th><th class="w-x">${h('va','Valor')}</th><th class="w-mv">Compras</th>`:''}<th class="w-t">13 meses</th></tr></thead><tbody><tr class="tot"><td class="i">Total · ${pn(vis.length)}</td><td></td><td></td><td></td><td class="fuerte ${pcv(tI)}">${pd0(tI)}</td><td></td>${amp?`<td></td><td></td><td></td><td>${ps0(vsuma(vis,'val'))}</td><td></td>`:''}<td></td></tr>${vis.slice(0,st.limite).map(fila).join('')}</tbody></table>${vis.length?'':'<p class="cp-aviso">Nada que mostrar con estos filtros.</p>'}</div>`;}
function pficha(G,C){const {st,B}=G,PR=pleer(B),P=st.p!=null?C.rows.find(r=>r.p===st.p):null,cif=(r,v,s='',c='')=>`<div class="cp-cf"><span>${vesc(r)}</span><b class="${c}">${vesc(v)}</b><small>${vesc(s)}</small></div>`;
  if(!P){const top=(a,f)=>[...a].sort(f).slice(0,5).map(r=>`<button class="cp-fi" data-acc="pprod" data-v="${r.p}"><span class="n" title="${vesc(r.n)}">${vesc(r.n)}</span><small>${ppc(r.pct)}</small><b class="${pcv(r.im)}">${pd0(r.im)}</b></button>`).join('');
    const may=[...C.sube].sort((a,b)=>b.im-a.im)[0],fr=st.kpi==='rev'?'Estas compras tienen un precio a 2,5 veces su habitual o a menos de 0,4, o decimales en una unidad entera: suelen ser errores de tipeo o de unidad, y no entran en ningún precio.':`${pn(C.sube.length)} ${C.sube.length===1?'subió':'subieron'} ${pcontra[st.contra]} y ${C.sube.length===1?'costó':'costaron'} ${ps0(C.up)} de más; ${C.baja.length} ${C.baja.length===1?'bajó y ahorró':'bajaron y ahorraron'} ${ps0(-C.dn)}.${may?` El que más pesa: ${may.n}, ${pd0(may.im)}.`:''}`;
    return `<div class="cp-fcab"><div class="cp-ftit"><span class="cp-miga">Todos los productos</span><h3>${({todos:'Qué pasó con los precios',sube:'Los que subieron',baja:'Los que bajaron',rev:'Para revisar'})[st.kpi]}</h3><span class="cp-miga">${pn(C.rows.length)} · ${C.n80} hacen el 80 %</span></div></div><p class="cp-frase">${vesc(fr)}</p><div class="cp-bloque">Los que más costaron de más</div><div class="cp-lista">${top(C.sube,(a,b)=>b.im-a.im)}</div><div class="cp-bloque">Los que más ahorraron</div><div class="cp-lista">${top(C.baja,(a,b)=>a.im-b.im)}</div>`;}
  const hl=PR.por.get(P.p),ult=[...P.rg].filter(pok).sort((a,b)=>b.d-a.d)[0];
  const fr=(P.im==null?'Sin precio de referencia para comparar.':`${P.im>=1?`Subió ${ppc(P.pct).replace('+','')} ${pcontra[st.contra]}: ${ps0(P.im)} de más`:P.im<=-1?`Bajó ${ppc(P.pct).replace('−','')} ${pcontra[st.contra]}: ${ps0(-P.im)} de ahorro`:`Igual ${pcontra[st.contra]}`} en ${pq(P.cOk)} ${P.um}.`)+(ult?` Última compra: ${pfc(ult.d)} a S/ ${pp2(ult.v/ult.c)}, con ${PR.provs[ult.prov]}.`:'');
  const tabs=[['curva','Curva'],['prov','Proveedores'],['comp','Compras'],['sem','Semanas'],['gasto','Cambio del gasto']];
  let body;
  if(st.ptab==='curva')body=pcurva(G,P,hl);else if(st.ptab==='prov')body=pprovs(G,P);else if(st.ptab==='comp')body=pcompras(G,P,hl);else if(st.ptab==='sem')body=psemanas(G,P);else body=pgasto(G,P);
  return `<div class="cp-fcab"><div class="cp-ftit"><span class="cp-miga">${vesc(P.fam)} › ${vesc(P.sub)}</span><h3 title="${vesc(P.n)}">${vesc(P.n)}</h3><span class="cp-miga">${P.nl} compras en el rango · ${ps0(P.val)}</span></div><button class="cp-pil" data-acc="pamp" data-v="ficha">${st.amp==='ficha'?'Ver la lista':'Ampliar'}</button><button class="cp-quita" data-acc="psoltar">Soltar</button></div>
    <div class="cp-cifras">${cif('Precio ahora',`S/ ${pp2(P.pp)}`,`por ${P.um}`)}${cif('Contra',`S/ ${pp2(P.ref)}`,({hab:'su habitual',ant:'período anterior',ano:'año pasado'})[st.contra])}${cif('Impacto',P.im==null?'—':pd0(P.im),ppc(P.pct),pcv(P.im))}${cif('Mín – máx',P.min==null?'—':`${pp2(P.min)} – ${pp2(P.max)}`,P.disp!=null?`se mueve ±${vnum(P.disp*100)} % · ${vnum(P.vol)} % en semanas`:P.vol?`${vnum(P.vol)} % en semanas · menos de 5 compras`:'')}</div>
    <p class="cp-frase">${vesc(fr)}</p><div class="cp-fl"><div class="cp-seg" role="group" aria-label="Qué mirar">${tabs.map(([k,t])=>`<button class="${st.ptab===k?'on':''}" data-acc="ptab" data-v="${k}" aria-pressed="${st.ptab===k}">${t}</button>`).join('')}</div></div><div class="cp-zona">${body}</div>`;}
function pcurva(G,P,hl){const {st,B}=G,PR=pleer(B),esC=st.pgran==='Compra',off=st.off[P.p]||[],R1=(B.planes[st.op]||B.planes['12m'])[1];
  const provOrd=[...new Set([...P.rg].sort((a,b)=>b.v-a.v).map(l=>l.prov))],colP=k=>VCOL[Math.max(0,provOrd.indexOf(k))%VCOL.length];
  const prev=new Map();{let u=null;for(const l of hl){prev.set(l,u);if(pok(l))u=l.v/l.c;}}
  let items;
  if(esC)items=[...P.rg].filter(l=>l.c>0&&!off.includes(l.prov)).sort((a,b)=>a.d-b.d).map(l=>({l,y:l.v/l.c,h:l.ref,et:pfc(l.d)}));
  else{const pers=st.pgran==='Mes'?pmeses(R1):Array.from({length:26},(_,i)=>{const u=vlunes(R1)-7*(25-i);return [u,u+6,pfc(u)];});
    items=pers.map(([a,b,et])=>{const w=hl.filter(l=>l.d>=a&&l.d<=b),g=w.filter(pok),c=vsuma(g,'c'),gr=g.filter(l=>l.ref!=null),rc=vsuma(gr,'c');return {a,b,et,y:c>0?vsuma(g,'v')/c:null,h:rc>0?gr.reduce((s,l)=>s+l.ref*l.c,0)/rc:null,fl:w.some(l=>l.fl),n:w.length};});}
  const vals=items.flatMap(x=>[x.y,x.h]).filter(vok),a=vals.length?Math.min(...vals):0,b=vals.length?Math.max(...vals):1,r=(b-a)||1,n=Math.max(1,items.length-1);
  const X=i=>esC?(items.length<2?50:4+i*92/n):i*100/n,Y=v=>90-(v-a)/r*78;
  G.curva={n,esC,items,X,P,prev,idx:x=>Math.max(0,Math.min(items.length-1,Math.round((esC?(x-.04)/.92:x)*n)))};
  const lin=k=>items.map((x,i)=>x[k]==null?null:`${X(i).toFixed(2)},${Y(x[k]).toFixed(2)}`).filter(Boolean).join(' ');
  const maxQ=Math.max(1,...items.map(x=>x.l?x.l.c:0)),conR=items.length<=14;
  const pts=esC?items.map((x,i)=>`<span class="cp-bola${x.l.fl?' fl':''}" data-i="${i}" style="left:${X(i).toFixed(2)}%;top:${Y(x.y).toFixed(2)}%;width:${Math.round(8+Math.sqrt(x.l.c/maxQ)*12)}px;height:${Math.round(8+Math.sqrt(x.l.c/maxQ)*12)}px;background:${colP(x.l.prov)}"></span>${conR?`<span class="cp-prt" style="left:${X(i).toFixed(2)}%;top:${Y(x.y).toFixed(2)}%">${pp2(x.y)}</span>`:''}`).join(''):items.map((x,i)=>x.y==null?'':`<span class="cp-pto${x.fl?' fl':''}" data-i="${i}" style="left:${X(i).toFixed(2)}%;top:${Y(x.y).toFixed(2)}%"></span>`).join('');
  const paso=esC?Math.ceil(items.length/8):st.pgran==='Mes'?3:5,rot=items.map((x,i)=>({x,i})).filter(({i})=>(esC&&items.length<=10)||i===0||i===n||(i%paso===0&&i<n-1)).map(({x,i})=>`<span class="${i===0&&items.length>1?'':i===n&&items.length>1?'fin':'med'}" style="left:${X(i).toFixed(2)}%">${vesc(x.et)}</span>`).join('');
  let tramo='',res='';
  if(st.tr&&st.tr[1]<items.length){const [i0,i1]=st.tr,bw=n?(esC?46:50)/n:50,x0=Math.max(0,X(i0)-bw),x1=Math.min(100,X(i1)+bw);tramo=`<span class="cp-tramo" style="left:${x0.toFixed(2)}%;width:${(x1-x0).toFixed(2)}%"></span>`;
    const ll=esC?items.slice(i0,i1+1).map(x=>x.l):hl.filter(l=>l.d>=items[i0].a&&l.d<=items[i1].b),gg=ll.filter(pok),cc=vsuma(gg,'c'),vv=vsuma(gg,'v'),sb=vsobre(gg.map(l=>({p:l.v/l.c,q:l.c}))),dsp=vdisp(gg.map(l=>({p:l.v/l.c})));
    res=`<div class="cp-cifras borde"><div class="cp-cf"><span>Precio del tramo</span><b>${cc>0?`S/ ${pp2(vv/cc)}`:'—'}</b><small>${gg.length} compras</small></div><div class="cp-cf"><span>Cantidad</span><b>${pq(cc)} ${vesc(P.um)}</b></div><div class="cp-cf"><span>Valor</span><b>${ps0(vv)}</b></div><div class="cp-cf" title="Suma de (precio − mínimo del tramo) × cantidad. Techo teórico: supone que el mínimo estuvo siempre disponible."><span>Sobrecosto</span><b>${ps0(sb.sobre)} (${vnum(sb.pct,1)} %)</b><small>${dsp!=null?`se mueve ±${vnum(dsp*100)} %`:'contra el mínimo del tramo'}</small></div></div>`;}
  const nota=(esC?(items.length?'Cada punto es una compra del rango: el color dice el proveedor y el tamaño, la cantidad. ':'Sin compras con estos proveedores. ')+'Arrastrá sobre el gráfico para elegir un tramo.':`Precio ponderado de cada ${st.pgran==='Mes'?'mes':'semana'}, sin las compras para revisar. El sobrecosto de un tramo es un techo teórico.`)+' La línea punteada es el habitual: la mediana de los 90 días anteriores a cada compra.';
  return `<div class="cp-evcab"><div class="cp-seg" role="group" aria-label="Agrupar">${['Compra','Semana','Mes'].map(t=>`<button class="${st.pgran===t?'on':''}" data-acc="pgran" data-v="${t}">${t}</button>`).join('')}</div>${st.tr?'<button class="cp-quita" data-acc="ptramo">Quitar el tramo ✕</button>':''}</div>
    <div class="cp-curva${st.amp==='ficha'?' grande':''}" data-curva="1" role="img" aria-label="Precio del producto en el tiempo">${tramo}<span class="cp-guia" hidden></span><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polyline class="h" points="${lin('h')}"/><polyline class="${esC?'tenue':'p'}" points="${lin('y')}"/></svg>${pts}<div class="cp-tip" hidden></div></div><div class="cp-cm">${rot}</div>
    ${esC?`<div class="cp-ley">${provOrd.map(k=>`<button class="${off.includes(k)?'off':''}" data-acc="pley" data-v="${k}" title="Mostrar u ocultar"><i style="background:${colP(k)}"></i>${vesc(PR.provs[k])}</button>`).join('')}</div>`:''}${res}<p class="cp-nota">${vesc(nota)}</p>`;}
function ptip(G,i){const c=G.curva,P=c.P,PR=pleer(G.B),x=c.items[i];
  const f=(n,v)=>`<span><i>${vesc(n)}</i>${vesc(v)}</span>`;
  if(c.esC){const l=x.l,pu=l.v/l.c,an=c.prev.get(l);return `<b>${pfc(l.d)} · S/ ${pp2(pu)} / ${vesc(P.um)}</b>${f('Proveedor',PR.provs[l.prov])}${f('Documento',PR.docs[l.doc])}${f('Cantidad · valor',`${pq(l.c)} ${P.um} · ${ps0(l.v)}`)}${f('Vs. compra anterior',an?ppc(pu/an-1):'—')}${f('Vs. su habitual',l.ref!=null?`${ppc(pu/l.ref-1)} (S/ ${pp2(l.ref)})`:'—')}${l.fl?f('Marca','Para revisar'):''}`;}
  return `<b>${vesc(x.et)}${x.y!=null?` · S/ ${pp2(x.y)}`:' · sin compras'}</b>${f('Habitual',x.h!=null?`S/ ${pp2(x.h)}`:'—')}${f('Compras',String(x.n))}${x.fl?f('Marca','Con compras para revisar'):''}`;}
function pmostrarTip(G,el,i){const t=el.querySelector('.cp-tip'),gu=el.querySelector('.cp-guia');if(i==null){t.hidden=true;gu.hidden=true;el.querySelectorAll('.foco').forEach(e=>e.classList.remove('foco'));return;}
  const c=G.curva,x=c.X(i);t.innerHTML=ptip(G,i);t.hidden=false;gu.hidden=false;gu.style.left=`${x}%`;t.style.left=x>55?`calc(${x}% - ${t.offsetWidth+12}px)`:`calc(${x}% + 12px)`;
  el.querySelectorAll('[data-i]').forEach(e=>e.classList.toggle('foco',+e.dataset.i===i));}
function pprovs(G,P){const PR=pleer(G.B),m=new Map();for(const l of P.rg)if(pok(l)){const x=m.get(l.prov)||{c:0,v:0};x.c+=l.c;x.v+=l.v;m.set(l.prov,x);}
  const pl=[...m].map(([k,x])=>({n:PR.provs[k],c:x.c,v:x.v,p:x.v/x.c})).sort((a,b)=>b.v-a.v),bar=pl.length?Math.min(...pl.map(x=>x.p)):0,bn=pl.find(x=>x.p===bar),ah=pl.reduce((s,x)=>s+(x.p-bar)*x.c,0);
  return `<div class="cp-tabla"><table><thead><tr><th class="l">Proveedor</th><th>Cant.</th><th>Precio</th><th>Vs. más barato</th><th>Valor</th></tr></thead><tbody>${pl.map(x=>`<tr><td class="l" title="${vesc(x.n)}">${vesc(x.n)}</td><td>${pq(x.c)} ${vesc(P.um)}</td><td>S/ ${pp2(x.p)}</td><td class="${x.p===bar?'verde':''}">${x.p===bar?'más barato':ppc(x.p/bar-1)}</td><td>${ps0(x.v)}</td></tr>`).join('')}</tbody></table></div><p class="cp-nota">${pl.length>1&&ah>=1?`Todo a S/ ${pp2(bar)}, de ${vesc(bn.n)}, habría costado ${ps0(ah)} menos. Cálculo propio: no mira calidad, corte ni disponibilidad.`:'Un solo proveedor en el rango.'}</p>`;}
function pcompras(G,P,hl){const PR=pleer(G.B),prev=new Map();{let u=null;for(const l of hl){prev.set(l,u);if(pok(l))u=l.v/l.c;}}
  return `<div class="cp-tabla"><table><thead><tr><th class="l">Fecha</th><th class="l">Proveedor</th><th class="l">Documento</th><th>Cant.</th><th>Precio</th><th>Vs. anterior</th></tr></thead><tbody>${[...P.rg].sort((a,b)=>b.d-a.d).map(l=>{const pu=l.c>0?l.v/l.c:null,an=prev.get(l),dv=pu!=null&&an?pu/an-1:null;return `<tr><td class="l">${pfc(l.d)}</td><td class="l" title="${vesc(PR.provs[l.prov])}">${vesc(PR.provs[l.prov])}</td><td class="l">${vesc(PR.docs[l.doc])}</td><td>${pq(l.c)}</td><td class="${l.fl?'nar':''}">${pp2(pu)}</td><td class="${l.fl?'nar':vok(dv)&&dv>.005?'rojo':vok(dv)&&dv<-.005?'verde':''}">${l.fl?'revisar':ppc(dv)}</td></tr>`;}).join('')}</tbody></table></div><p class="cp-nota">En naranja, las compras para revisar: no entran en el precio.</p>`;}
function psemanas(G,P){const {B,st}=G,R=vbase(B,st.op),id=B.P.prods.findIndex(x=>String(x).trim()===String(P.n).trim());if(id<0)return '<p class="cp-aviso">Sin compras en soles para este producto.</p>';
  const info=R.rank.find(r=>r.id===id),hist=(B.prods.get(id)||[]).filter(r=>!info||r.u===info.u),rows=vrango(hist,...R.rango).filter(r=>r.p>0),previo=hist.filter(r=>r.f<(R.sems[0]??0)&&r.p>0).at(-1)?.p??null,sem=vsemanas(rows,R.sems,previo).filter(w=>w.rows.length).reverse();
  return `<div class="cp-tabla"><table><thead><tr><th class="l">Semana</th><th>Primera → última</th><th>Cambio</th><th>Mín – máx</th><th>Compras</th></tr></thead><tbody>${sem.map(w=>{const dv=w.antes>0?w.c/w.antes-1:null;return `<tr><td class="l">${pfc(w.f)} – ${pfc(Math.min(w.f+6,R.rango[1]))}</td><td>${pp2(w.o)} → ${pp2(w.c)}</td><td class="${vok(dv)&&dv>.005?'rojo':vok(dv)&&dv<-.005?'verde':''}">${ppc(dv)}</td><td>${pp2(w.l)} – ${pp2(w.h)}</td><td>${w.rows.length}</td></tr>`;}).join('')||'<tr><td class="l" colspan="5">Sin compras.</td></tr>'}</tbody></table></div><p class="cp-nota">El cambio es contra el cierre de la semana anterior con compras. En soles y en la unidad más comprada.</p>`;}
function pgasto(G,P){const {B,st}=G,R=vbase(B,st.op),id=B.P.prods.findIndex(x=>String(x).trim()===String(P.n).trim()),info=R.rank.find(r=>r.id===id);if(!info)return '<p class="cp-aviso">Sin compras en soles para este producto.</p>';
  const hist=(B.prods.get(id)||[]).filter(r=>r.u===info.u),[a,b]=R.rango,ip=a-(b-a+1),p=vcambio(vrango(hist,a,b),vrango(hist,ip,a-1),ip>=vdia(B.P.historia[0]));G.D={puente:p};
  return p.precio==null?'<p class="cp-aviso">Sin base comparable en el período anterior.</p>':`<div class="cv-bridge-plot"></div><p class="cp-nota">Cuánto del cambio del gasto contra el período anterior es cantidad y cuánto es precio: ${pd0(p.cantidad)} y ${pd0(p.precio)}.</p>`;}
function vpintar(G){
  const {root,B,st}=G,C=pfilas(B,st);G.C=C;
  if(st.p!=null&&!C.rows.some(r=>r.p===st.p))st.p=null;
  if(st.amp==='ficha'&&st.p==null)st.amp=null;
  const y=root.querySelector('.cp-wrap')?.scrollTop||0;
  root.querySelector('.cp-cab-din').innerHTML=pmenuFam(B,st);
  root.querySelector('.cp-kpis').innerHTML=pkpis(G,C);
  const iz=root.querySelector('.cp-izq'),fi=root.querySelector('.cp-ficha');iz.hidden=st.amp==='ficha';fi.hidden=st.amp==='lista';
  iz.innerHTML=plista(G,C);fi.innerHTML=pficha(G,C);
  root.querySelector('.cp-cuerpo').dataset.amp=st.amp||'';
  const w=root.querySelector('.cp-wrap');if(w)w.scrollTop=y;
  vpuentePlot(G);
}
function ppintarFicha(G){const fi=G.root.querySelector('.cp-ficha');fi.innerHTML=pficha(G,G.C);G.root.querySelectorAll('.cp-izq tr').forEach(tr=>{const b=tr.querySelector('[data-acc=pprod]');if(b)tr.classList.toggle('chosen',+b.dataset.v===G.st.p);});vpuentePlot(G);}
function vexcel(G){
  const {B,st,C}=G,vis=G.vis||[],PR=pleer(B),P=st.p!=null?C.rows.find(r=>r.p===st.p):null;
  const hojas=[{nombre:'Precios',cabeza:['Producto','Familia','Subfamilia','Unidad','Precio ahora','Precio contra','Cambio %','Impacto S/','Se mueve (dispersión)','En semanas (volatilidad)','Mínimo','Máximo','Cantidad','Valor S/','Compras','Para revisar'],
    filas:vis.map(r=>[r.n,r.fam,r.sub,r.um,r.pp,r.ref,r.pct==null?null:r.pct*100,r.im,r.disp,r.vol,r.min,r.max,r.cOk,r.val,r.nl,r.nfl]),decimales:6}];
  if(P)hojas.push({nombre:'Compras',cabeza:['Fecha','Proveedor','Documento','Cantidad','Valor S/','Precio','Habitual','Para revisar'],filas:[...P.rg].sort((a,b)=>b.d-a.d).map(l=>[vfecha(l.d),PR.provs[l.prov],PR.docs[l.doc],l.c,l.v,l.c>0?l.v/l.c:null,l.ref,l.fl?'Sí':'No']),decimales:6});
  const filas=[['Rango',`${viso(C.R0)} / ${viso(C.R1)}`],['Contra',pcontra[st.contra]],['Buscar',st.q],['Ver',st.ver==='80'?'Los que hacen el 80 %':'Todos'],['Moneda','Soles'],['Precio ponderado','Soles ÷ cantidad, sin las compras para revisar'],['Efecto del precio','Lo pagado menos lo que hubiera costado al precio de referencia'],['Se mueve','Dispersión: desvío ÷ promedio de los precios; pide cinco compras'],['En semanas','Volatilidad: suma de los cambios semanales, en %']];
  for(const [rot,vs] of Object.entries(B.P.filtros||{}))filas.push([rot,vs.length?vs.join(' / '):'Todos']);
  hojas.push({nombre:'Contexto',cabeza:['Dato','Valor'],filas});
  bajar(`Precios_${archivo(P?P.n:'productos')}.xlsx`,libro(hojas));
}
function pavisar(G){if(G.pagina){const v=G.pagina;G.pagina=null;G.enviar?.('familias',v);}}
function vconectar(G){
  const {root}=G,signal=G.abort.signal;
  root.addEventListener('click',ev=>{
    const e=ev.target.closest('[data-acc]');if(!e||!root.contains(e)||e.matches('input,select'))return;
    const {acc,v}=e.dataset,{st}=G;
    if(acc==='pkpi'){st.kpi=st.kpi===v?'todos':v;st.ord=st.kpi==='baja'?{k:'im',d:1}:{k:'im',d:-1};st.p=null;st.limite=150;}
    else if(acc==='pver'){st.ver=v;st.limite=150;}
    else if(acc==='pord'){st.ord={k:v,d:st.ord.k===v?-st.ord.d:v==='n'?1:-1};}
    else if(acc==='pamp'){st.amp=st.amp===v?null:v;}
    else if(acc==='pprod'){const n=+v;st.tr=null;st.p=st.p===n?null:n;if(st.amp==='lista')st.amp=null;else if(st.amp!=='ficha'){ppintarFicha(G);return;}}
    else if(acc==='psoltar'){st.p=null;st.tr=null;if(st.amp==='ficha')st.amp=null;}
    else if(acc==='ptab'){st.ptab=v;ppintarFicha(G);return;}
    else if(acc==='pgran'){st.pgran=v;st.tr=null;ppintarFicha(G);return;}
    else if(acc==='ptramo'){st.tr=null;ppintarFicha(G);return;}
    else if(acc==='pley'){const k=+v,o=st.off[st.p]||[];st.off[st.p]=o.includes(k)?o.filter(x=>x!==k):[...o,k];st.tr=null;ppintarFicha(G);return;}
    else if(acc==='pmenu'){st.menu=st.menu===v?null:v;if(!st.menu)pavisar(G);}
    else if(acc==='excel'){vexcel(G);return;}
    else return;
    vpintar(G);
  });
  root.addEventListener('input',ev=>{if(ev.target.dataset.acc==='q'){G.st.q=ev.target.value;G.st.limite=150;vpintar(G);}});
  root.addEventListener('change',ev=>{
    const e=ev.target,{acc}=e.dataset,{st,B}=G;
    if(acc==='pcontra'){st.contra=e.value;vpintar(G);}
    else if(acc==='pfam'){const P=B.P.familias,el=P.elegidas.length?P.elegidas:P.todas.map(x=>x[0]);P.elegidas=e.checked?[...el,e.value]:el.filter(x=>x!==e.value);G.pagina=P.elegidas.slice();vpintar(G);}
  });
  root.addEventListener('scroll',ev=>{const el=ev.target;if(!el.matches?.('.cp-wrap'))return;if(el.scrollTop+el.clientHeight>=el.scrollHeight-80&&G.st.limite<(G.vis?.length||0)){G.st.limite+=150;vpintar(G);}},true);
  // El gráfico: el detalle al pasar el cursor y el tramo arrastrado, sin redibujar.
  const enCurva=ev=>{const el=ev.target.closest?.('[data-curva]');return el&&root.contains(el)?el:null;};
  const pos=(el,ev)=>{const b=el.getBoundingClientRect();return G.curva.idx((ev.clientX-b.left)/b.width);};
  root.addEventListener('pointermove',ev=>{const el=enCurva(ev);if(!el||!G.curva||!G.curva.items.length)return;const i=pos(el,ev);pmostrarTip(G,el,i);
    if(G.drag!=null){G.drag.j=i;const [a,b]=[Math.min(G.drag.i,i),Math.max(G.drag.i,i)],c=G.curva,bw=c.n?(c.esC?46:50)/c.n:50,x0=Math.max(0,c.X(a)-bw),x1=Math.min(100,c.X(b)+bw);let t=el.querySelector('.cp-tramo');if(!t){t=document.createElement('span');t.className='cp-tramo';el.prepend(t);}t.style.left=`${x0}%`;t.style.width=`${x1-x0}%`;}});
  root.addEventListener('pointerleave',()=>{},true);
  root.addEventListener('mouseout',ev=>{const el=enCurva(ev);if(el&&!el.contains(ev.relatedTarget)&&G.curva)pmostrarTip(G,el,null);});
  root.addEventListener('pointerdown',ev=>{const el=enCurva(ev);if(!el||ev.button!==0||!G.curva?.items.length)return;const i=pos(el,ev);G.drag={i,j:i,t:ev.pointerType};pmostrarTip(G,el,i);});
  window.addEventListener('pointerup',()=>{const d=G.drag;G.drag=null;if(!d||!root.isConnected)return;if(d.i===d.j)return;G.st.tr=[Math.min(d.i,d.j),Math.max(d.i,d.j)];ppintarFicha(G);},{signal});
  document.addEventListener('pointerdown',ev=>{if(!G.st.menu||ev.composedPath().some(n=>n.classList&&n.classList.contains('cp-ms')))return;G.st.menu=null;vpintar(G);pavisar(G);},{signal});
  document.addEventListener('keydown',ev=>{if(ev.key==='Escape'&&G.st.menu){G.st.menu=null;vpintar(G);pavisar(G);}},{signal});
}
window.__cvUI={inicial:vinicial,pintar:vpintar};
export default function(component){
  const {data:P,parentElement,setTriggerValue}=component;if(!P)return;
  let G=window.__cpVol,st=G?.st||vinicial(P.inicial);
  G?.abort?.abort();G?.observer?.disconnect();
  if(G&&G.B.P.sello!==P.sello){
    const nombre=G.B.P.precios?.prods?.[st.p]?.[0],id=P.precios?.prods?P.precios.prods.findIndex(x=>x[0]===nombre):-1;st.p=id<0?null:id;
    st.tr=null;st.off={};st.op=P.inicial||st.op;st.limite=150;
  }
  let root=parentElement.querySelector('.cvol');
  if(!root){root=document.createElement('div');root.className='cvol';
    root.innerHTML=`<div class="cp-cab"><h2 class="cp-tit">Precios</h2><span class="cp-lugar" aria-hidden="true"></span><span class="cp-cab-din"></span><select class="cp-men" data-acc="pcontra" aria-label="Contra qué precio"><option value="hab">Contra: su precio habitual</option><option value="ant">Contra: el período anterior</option><option value="ano">Contra: el año pasado</option></select><span class="cp-esp"></span><input class="cp-busca" type="search" data-acc="q" placeholder="Buscar producto…" aria-label="Buscar producto"><button class="cp-pil" data-acc="excel" title="Baja lo que se ve">Excel ↓</button></div><div class="cp-kpis"></div><div class="cp-cuerpo"><section class="cp-izq"></section><aside class="cp-ficha" aria-label="Ficha"></aside></div>`;
    parentElement.appendChild(root);}
  const nuevo=!G||G.root!==root;
  G={root,st,B:G?.B.P.sello===P.sello?G.B:vleer(P),abort:new AbortController(),enviar:setTriggerValue};window.__cpVol=G;
  root.querySelector('[data-acc=q]').value=st.q||'';root.querySelector('[data-acc=pcontra]').value=st.contra;
  const fb=document.querySelector('.st-key-cp_vol_fecha');if(fb&&fb.offsetWidth)root.style.setProperty('--cp-fecha',`${fb.offsetWidth+8}px`);
  vconectar(G);vpintar(G);
  let ancho=root.clientWidth;
  G.observer=new ResizeObserver(()=>{if(Math.abs(root.clientWidth-ancho)<2)return;ancho=root.clientWidth;if(root.isConnected)vpuentePlot(G);});G.observer.observe(root);
}
