// Diferencias del cierre (#720, #748). Todo es local salvo «¿Por qué?», que pide
// a Python el salto a la línea en «Análisis de diferencias».
const CJ={c:0,fam:1,area:2,prod:3,cod:4,sub:5,um:6,val:7,dif:8,sis:9,fis:10,stock:11,flags:12};
const CEPS=1e-9;
const cesc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cfmt=[0,1,2,3,4,5,6].map(d=>new Intl.NumberFormat('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}));
const cn=(v,d=0)=>v==null?'—':cfmt[d].format(v);
const cs=v=>v==null?'—':`${v<0?'−':''}S/ ${cn(Math.abs(v),2)}`;
const cp=v=>v==null?'—':`${cn(v,1)}%`;
const ccolor=v=>v<-CEPS?'var(--danger)':v>CEPS?'var(--success)':'var(--text-secondary)';
// groupby.sum de pandas usa suma compensada; evita un signo fantasma al
// cancelar conteos de un producto en el Pareto.
const csum=(rs,k)=>{let s=0,c=0;for(const r of rs){const y=(r[k]||0)-c,t=s+y;c=t-s-y;s=t;}return s;};
const cgroup=(rs,key)=>{const m=new Map();for(const r of rs){const k=key(r);if(!m.has(k))m.set(k,[]);m.get(k).push(r);}return m;};
function cleer(P){
  const cortes=P.sesiones.map(()=>[]);
  const rows=P.filas.map(z=>{const r={};for(const k of ['c','val','dif','sis','fis','stock','flags'])r[k]=z[CJ[k]];
    for(const k of ['fam','area','prod','cod','sub','um'])r[k]=P.dic[k][z[CJ[k]]];
    r.id=r.cod?`c:${r.cod}`:`n:${r.prod.trim()}`;r.key=JSON.stringify([r.id,r.area,r.um]);cortes[r.c]?.push(r);return r;});
  return {P,rows,cortes,cache:new Map(),compare:new Map()};
}
function cmetricas(rows,hay={prod:true,stock:true}){
  let falto=0,sobro=0,lineas=0,dif=0,tol=0,stock=0;const pr=new Map();
  for(const r of rows){if(r.val<0)falto+=r.val;else sobro+=r.val;stock+=r.stock;
    if(r.flags&1){lineas++;if(r.flags&2)dif++;if(Math.abs(r.val)<=CTOL)tol++;}pr.set(r.prod,(pr.get(r.prod)||0)+Math.abs(r.val));}
  const vs=[...pr.values()].filter(v=>v>CEPS).sort((a,b)=>b-a),total=vs.reduce((s,v)=>s+v,0);let acum=0,n80=0;
  for(const v of vs){n80++;acum+=v;if(acum/total>=.8-CEPS)break;}
  return {falto,sobro,total:Math.abs(falto)+sobro,saldo:falto+sobro,lineas,dif,tol,exact:lineas?100*(lineas-dif)/lineas:null,
    n80:hay.prod?n80:null,de:hay.prod?vs.length:null,valorizado:hay.stock?stock:null};
}
const cfiltrar=(rows,st)=>rows.filter(r=>(!st.fams.length||st.fams.includes(r.fam))&&(!st.areas.length||st.areas.includes(r.area)));
function cresumen(rows,key,hay){return [...cgroup(rows,r=>r[key])].map(([nombre,rs])=>({nombre,...cmetricas(rs,hay)})).filter(r=>r.total>CEPS||r.lineas).sort((a,b)=>b.total-a.total||a.nombre.localeCompare(b.nombre));}
function cespejos(rows){
  let n=0,falto=0,sobro=0;for(const rs of cgroup(rows,r=>r.prod).values()){
    const vs=[...cgroup(rs,r=>r.area).values()].map(g=>csum(g,'val'));if(vs.some(v=>v<-CEPS)&&vs.some(v=>v>CEPS)){n++;falto+=vs.filter(v=>v<-CEPS).reduce((s,v)=>s+v,0);sobro+=vs.filter(v=>v>CEPS).reduce((s,v)=>s+v,0);}}
  return {n,falto,sobro};
}
function cmatriz(rows,medida){
  const familias=[...new Set(rows.map(r=>r.fam))],areas=[...new Set(rows.map(r=>r.area))].sort(),cells=[];
  for(const [key,g] of cgroup(rows,r=>JSON.stringify([r.fam,r.area]))){const [fam,area]=JSON.parse(key);cells.push({fam,area,n:g.length,valor:csum(g,medida),...cmetricas(g)});}
  const total=f=>cells.filter(r=>r.fam===f).reduce((s,r)=>s+r.valor,0);familias.sort((a,b)=>Math.abs(total(b))-Math.abs(total(a))||a.localeCompare(b));
  return {familias,areas,cells,total:csum(cells,'valor')};
}
function cproductos(rows,juntas=true){
  const areas=[...cgroup(rows,r=>JSON.stringify([r.id,r.area])).values()].map(g=>({
    ...g[0],val:csum(g,'val'),dif:csum(g,'dif'),sis:csum(g,'sis'),fis:csum(g,'fis'),stock:csum(g,'stock'),
    // La tabla histórica agrupa código × área. La comparación conserva unidad.
    varias_um:new Set(g.map(r=>r.um)).size>1}));
  const tiene=r=>Math.abs(r.dif)>CEPS||Math.abs(r.val)>CEPS;
  if(!juntas)return areas.filter(tiene).sort((a,b)=>Math.abs(b.val)-Math.abs(a.val));
  const out=[];
  for(const g of cgroup(areas,r=>r.id).values()){
    if(!g.some(tiene))continue;
    const vivos=g.filter(r=>['sis','fis','dif','val'].some(k=>Math.abs(r[k])>CEPS)),mixed=new Set(vivos.map(r=>r.um)).size>1||vivos.some(r=>r.varias_um);
    out.push({...g[0],val:csum(g,'val'),dif:mixed?null:csum(g,'dif'),sis:mixed?null:csum(g,'sis'),fis:mixed?null:csum(g,'fis'),stock:csum(g,'stock'),
      um:mixed?'Varias unidades':g[0].um,area:vivos.length>1?`${vivos.length} áreas`:vivos[0]?.area||'',
      compensado:g.some(r=>r.val<-.005)&&g.some(r=>r.val>.005),hijos:vivos.length>1?vivos.sort((a,b)=>Math.abs(b.val)-Math.abs(a.val)):[]});
  }
  return out.sort((a,b)=>Math.abs(b.val)-Math.abs(a.val));
}
function cpareto(rows,lado='Faltantes'){
  const prods=[...cgroup(rows,r=>r.prod)].map(([prod,g])=>({prod,neto:csum(g,'val')}))
    .filter(r=>lado==='Faltantes'?r.neto<0:r.neto>0).map(r=>({...r,valor:Math.abs(r.neto)})).sort((a,b)=>b.valor-a.valor||a.prod.localeCompare(b.prod));
  const total=csum(prods,'valor');let acum=0;return prods.map(r=>{acum+=r.valor;return {...r,pct:100*r.valor/total,acum:100*acum/total};});
}
function careasPareto(rows,prod){return [...cgroup(rows.filter(r=>r.prod===prod),r=>JSON.stringify([r.area,r.um])).values()].map(g=>({area:g[0].area,um:g[0].um,dif:csum(g,'dif'),val:csum(g,'val')})).sort((a,b)=>Math.abs(b.val)-Math.abs(a.val));}
function clistas(rows,juntas){
  const claves=r=>JSON.stringify(juntas?[r.prod.trim()]:[r.prod.trim(),r.area]);
  return [...cgroup(rows,claves).values()].map(g=>{const mixed=new Set(g.map(r=>r.um)).size>1,areas=new Set(g.map(r=>r.area));
    return {...g[0],prod:g[0].prod.trim(),cod:new Set(g.map(r=>r.cod)).size>1?'Varios códigos':g[0].cod,
      area:areas.size>1?`${areas.size} áreas`:g[0].area,um:mixed?'Varias unidades':g[0].um,
      val:csum(g,'val'),dif:mixed?null:csum(g,'dif'),sis:mixed?null:csum(g,'sis'),fis:mixed?null:csum(g,'fis')};
  }).filter(r=>Math.abs(r.val)>CEPS).sort((a,b)=>Math.abs(b.val)-Math.abs(a.val));
}
function cgrupos(rows){
  return new Map([...cgroup(rows,r=>r.key)].map(([key,g])=>[key,{...g[0],n:g.length,val:csum(g,'val'),dif:csum(g,'dif'),
    sis:csum(g,'sis'),fis:csum(g,'fis'),falto:csum(g.filter(r=>r.val<0),'val'),sobro:csum(g.filter(r=>r.val>0),'val'),
    activa:g.some(r=>r.flags&4),observada:g.every(r=>r.flags&8)&&g.some(r=>r.flags&1)&&!['','---','nan','none'].includes(g[0].area.toLowerCase())&&!!g[0].um&&(!!g[0].cod||!['','nan','none'].includes(g[0].prod.trim().toLowerCase())),
    contado:g.some(r=>r.flags&1)}]));
}
function ccomparar(actual,anterior,historia=[]){
  const a=cgrupos(actual),b=cgrupos(anterior),hist=new Map();
  for(const rows of historia){for(const [key,g] of cgrupos(rows)){if(!g.observada)continue;
    if(!hist.has(key))hist.set(key,{con:0,de:0});const h=hist.get(key);h.de++;if(g.activa)h.con++;}}
  const out=[];
  for(const key of new Set([...a.keys(),...b.keys()])){
    const x=a.get(key),y=b.get(key),r=x||y,comparable=!!(x?.observada&&y?.observada);
    const estado=!comparable?'Sin base':x.activa?(y.activa?'Recurrente':'Nueva'):(y.activa?'Resuelta':'Sin diferencia');
    let motivo='Mismo producto, área y unidad con stock en ambos cortes';
    if(!x)motivo='Sin registro en el corte actual';else if(!y)motivo='Sin registro en el corte anterior';
    else if(!r.um)motivo='Unidad ausente';else if(!r.area)motivo='Área ausente';
    else if(!r.cod&&['','nan','none'].includes(r.prod.trim().toLowerCase()))motivo='Producto sin identificador';
    else if(!x.observada||!y.observada)motivo='Stock cero/cero o datos incompletos: no prueba un recuento';
    const absx=x?Math.abs(x.falto)+x.sobro:null,absy=y?Math.abs(y.falto)+y.sobro:null;
    if(comparable&&((x.activa&&absx<=CEPS)||(y.activa&&absy<=CEPS)))motivo='Diferencia de cantidad sin importe en uno de los cortes';
    out.push({key,id:r.id,cod:r.cod,prod:r.prod,fam:r.fam,sub:r.sub,area:r.area,um:r.um,actual:x||null,anterior:y||null,
      comparable,estado,motivo,delta:comparable?absx-absy:null,abs_actual:absx,abs_anterior:absy,
      signo:comparable&&x.activa&&y.activa&&x.val*y.val<0?'Cambió de signo':'',...(hist.get(key)||{con:0,de:0})});
  }
  return out.sort((a,b)=>Math.max(b.abs_actual||0,b.abs_anterior||0)-Math.max(a.abs_actual||0,a.abs_anterior||0)||a.prod.localeCompare(b.prod));
}
const cestados=['Todas','Nueva','Recurrente','Resuelta','Sin base','Sin diferencia'];
const cprev=(P,c)=>{for(let i=c-1;i>=0;i--)if(P.sesiones[c].tipo!=='cierre'||P.sesiones[i].tipo==='cierre')return i;return c>0?c-1:-1;};
// ── La presentación (regla #748) ─────────────────────────────────────────
// Arriba el cierre: una frase, cinco indicadores, las familias (o el cruce
// con las áreas) y los últimos 12 cierres. Abajo, qué productos: cuatro
// pestañas. Los insumos de operación van APARTE, no afuera.
const CTOL=5;
const csol=v=>v==null?'—':`${Math.round(v)<0?'−':''}S/ ${cn(Math.abs(v))}`;
const cint=v=>v==null?'—':`${Math.round(v)<0?'−':Math.round(v)>0?'+':''}${cn(Math.abs(v))}`;
const cpct=(a,b)=>b?`${Math.round(100*a/b)} %`:'—';
const ccant=v=>v==null?'—':Number(v).toLocaleString('en-US',{maximumFractionDigits:3});
const CMENOR=new Set(['de','del','y','e','la','las','el','los','con','sin','a','x']);
const cnom=s=>/^\d+ áreas$/.test(String(s??''))?String(s):String(s??'').toLocaleLowerCase('es').split(/(\s+)/).map((w,i)=>i&&CMENOR.has(w)?w:w.charAt(0).toLocaleUpperCase('es')+w.slice(1)).join('');
const CCORTO={'ALIMENTOS':'Alimentos','VINOS Y ESPUMANTES':'Vinos','ENVASES Y EMBALAJES':'Envases','BEBIDAS CON ALCOHOL':'Con alcohol','BEBIDAS SIN ALCOHOL':'Sin alcohol','COSTOS PRODUCCION':'Operación'};
const ccorto=f=>CCORTO[String(f).trim().toUpperCase()]||cnom(String(f).split(' ')[0]);
const ctabs=[['listas','Faltantes y sobrantes'],['comparar','Comparar cierres'],['areas','Por área'],['lineas','Todas las líneas']];

function cinicial(P){return {c:P.inicial,prev:cprev(P,P.inicial),fams:[],areas:[],fam:null,area:null,
  vf:P.perspectiva==='Familia × Área'?'cruce':'lista',medida:'val',vg:'graf',tab:'listas',orden:'monto',juntas:true,
  q:'',status:'Recurrente',limite:150,abiertos:[],abiertas:[],elegido:null,ordenTabla:{}};}
const cfoco=st=>r=>(!st.fam||r.fam===st.fam)&&(!st.area||r.area===st.area);
function cdatos(G){const {st,B}=G,P=B.P;
  const clave=JSON.stringify([st.c,st.prev,st.fams,st.areas,st.fam,st.area]);
  if(B.cache.has(clave))return {...B.cache.get(clave),st};
  const rs=cfiltrar(B.cortes[st.c]||[],st),fams=cresumen(rs,'fam',P.hay);
  if(st.fam&&!fams.some(r=>r.nombre===st.fam))st.fam=null;
  const foco=cfoco(st),scope=rs.filter(foco),op=r=>B.oper.has(r.fam);
  const hist=B.cortes.slice(0,st.c+1).map(rows=>cfiltrar(rows,st).filter(foco));
  const prev=cfiltrar(B.cortes[st.prev]||[],st).filter(foco);
  const datos={rs,fams,scope,hist,prev,m:cmetricas(rs,P.hay),mc:cmetricas(rs.filter(r=>!op(r)),P.hay),mo:cmetricas(rs.filter(op),P.hay),
    hayOper:B.oper.size>0&&(!st.fams.length||st.fams.some(f=>B.oper.has(f)))};
  if(B.cache.size>30)B.cache.clear();B.cache.set(clave,datos);return {...datos,st};
}
// Los últimos 12 cierres hasta el corte elegido, con los filtros y el foco;
// y la tabla con los parciales del mismo tramo.
function cserie(G){const {st,B}=G,P=B.P,clave=JSON.stringify(['serie',st.c,st.fams,st.areas,st.fam,st.area]);
  if(B.cache.has(clave))return B.cache.get(clave);
  const idx=P.sesiones.map((s,i)=>i).filter(i=>i<=st.c&&P.sesiones[i].tipo==='cierre').slice(-12),desde=idx.length?idx[0]:st.c,foco=cfoco(st);
  const fila=i=>{const rs=cfiltrar(B.cortes[i]||[],st).filter(foco),op=r=>B.oper.has(r.fam);
    return {i,s:P.sesiones[i],c:cmetricas(rs.filter(r=>!op(r)),P.hay),o:cmetricas(rs.filter(op),P.hay),m:cmetricas(rs,P.hay),areas:new Set(rs.filter(r=>r.flags&1).map(r=>r.area)).size};};
  const out={cierres:idx.map(fila),tabla:P.sesiones.map((s,i)=>i).filter(i=>i>=desde&&i<=st.c).reverse().map(fila)};
  B.cache.set(clave,out);return out;
}
// Cuántos de los últimos 6 cierres faltó cada producto (por nombre).
function crepite(G){const {st,B}=G,P=B.P,clave=JSON.stringify(['repite',st.c,st.fams,st.areas,st.fam,st.area]);
  if(B.cache.has(clave))return B.cache.get(clave);
  const idx=P.sesiones.map((s,i)=>i).filter(i=>i<=st.c&&P.sesiones[i].tipo==='cierre').slice(-6),foco=cfoco(st),n=new Map();
  for(const i of idx)for(const [prod,g] of cgroup(cfiltrar(B.cortes[i]||[],st).filter(foco),r=>r.prod.trim()))if(csum(g,'val')<-1)n.set(prod,(n.get(prod)||0)+1);
  const out={n,de:idx.length};B.cache.set(clave,out);return out;
}
const cbtn=(act,v,txt,sel=false,tip='',cls='')=>`<button type="button" data-act="${act}" data-v="${cesc(v)}" class="${sel?'selected ':''}${cls}" title="${cesc(tip)}" aria-pressed="${sel}">${cesc(txt)}</button>`;
const cseg=(act,ops,sel,label)=>`<span class="ajc-seg" role="group" aria-label="${cesc(label)}">${ops.map(([v,t])=>cbtn(act,v,t,v===sel)).join('')}</span>`;
const cselect=(act,ops,sel,label)=>`<label>${cesc(label)} <select data-change="${act}" aria-label="${cesc(label)}">${ops.map(([v,t])=>`<option value="${cesc(v)}" ${v===sel?'selected':''}>${cesc(t)}</option>`).join('')}</select></label>`;
const ckpi=(label,value,sub='',tip='',cls='',extra='')=>`<div class="ajc-kpi ${extra}" title="${cesc(tip)}"><span>${cesc(label)}</span><b class="${cls}">${cesc(value)}</b><small>${cesc(sub)}</small></div>`;
const cclase=v=>v<-.5?'neg':v>.5?'pos':'';
function cfiltro(G,k,label,opciones){const vs=G.st[k];
  return `<details class="ajc-filter"><summary>${cesc(label)}: ${!vs.length?'todas':vs.length===1?cesc(cnom(vs[0])):vs.length}</summary><div class="ajc-options"><div>${cbtn('todos',k,'Todas')}${k==='fams'?cbtn('inicial',k,'Sólo las cinco de antes','','Alimentos, bebidas, vinos y envases: el filtro con que abría hasta la regla #748'):''}</div>${opciones.map(v=>`<label><input type="checkbox" data-filter="${k}" value="${cesc(v)}" ${vs.includes(v)?'checked':''}>${cesc(cnom(v)||'Sin nombre')}</label>`).join('')}</div></details>`;
}
function cordenar(rows,st,clave,valor){const o=st.ordenTabla[clave];if(!o)return rows;
  return [...rows].sort((a,b)=>{const x=valor(a)[o.i],y=valor(b)[o.i];if(x==null)return y==null?0:1;if(y==null)return -1;return o.d*(typeof x==='number'&&typeof y==='number'?x-y:String(x).localeCompare(String(y)));});}
function ctabla(cabeza,filas,clase='',orden=null){return `<table class="${clase}"><thead><tr>${cabeza.map((t,i)=>`<th>${orden?cbtn('ordentab',`${orden}|${i}`,t+' ↕'):cesc(t)}</th>`).join('')}</tr></thead><tbody>${filas.join('')}</tbody></table>`;}

function cfrase(G,D){const {P}=G.B,s=P.sesiones[D.st.c],{mc,mo}=D;if(!s)return '';
  const quien=D.st.fam?cnom(D.st.fam):'alimentos y bebidas';
  let t=`En <b>${cesc(s.nombre.charAt(0).toLocaleLowerCase('es')+s.nombre.slice(1))}</b>${D.st.area?` en <b>${cesc(cnom(D.st.area))}</b>`:''}, ${cesc(quien)} `;
  t+=mc.lineas||Math.abs(mc.total)>CEPS?`perdieron <b class="neg">${csol(-mc.falto)}</b> y encontraron <b class="pos">${csol(mc.sobro)}</b>: neto <b class="${cclase(mc.saldo)}">${csol(mc.saldo)}</b>.`:'no tuvieron diferencias.';
  if(D.hayOper&&(mo.lineas||Math.abs(mo.total)>CEPS))t+=` Los insumos de operación, que ninguna receta descarga, dejaron aparte <b class="op">${csol(mo.saldo)}</b>.`;
  return t;
}
function cfamilias(G,D){const {B}=G,P=B.P,{st}=D;
  if(st.vf==='cruce'){const mat=cmatriz(D.rs,st.medida),fams=[...mat.familias].sort((a,b)=>B.oper.has(a)-B.oper.has(b)),map=new Map(mat.cells.map(r=>[JSON.stringify([r.fam,r.area]),r]));
    const tot=a=>mat.cells.filter(r=>r.area===a).reduce((s,r)=>s+r.valor,0),areas=[...mat.areas].sort((a,b)=>st.medida==='stock'?tot(b)-tot(a):tot(a)-tot(b)),max=Math.max(...mat.cells.map(r=>Math.abs(r.valor)),1);
    const fmt=v=>st.medida==='stock'?cn(v):cint(v);
    const celda=(f,a)=>{const r=map.get(JSON.stringify([f,a]));if(!r)return '<td class="ajc-nada" title="Sin registros">·</td>';
      const pct=Math.round(100*Math.min(.85,.12+.73*Math.abs(r.valor)/max)),color=st.medida==='stock'?'--accent':r.valor<0?'--danger':'--success';
      return `<td>${`<button type="button" data-act="celda" data-v="${cesc(JSON.stringify([f,a]))}" class="${st.fam===f&&st.area===a?'selected':''}" style="background:color-mix(in srgb,var(${color}) ${Math.abs(r.valor)>CEPS?pct:0}%,transparent)" title="${cesc(`${cnom(f)} · ${cnom(a)}: ${csol(r.valor)} · ${r.n} líneas`)}">${Math.abs(r.valor)>CEPS?fmt(r.valor):'0'}</button>`}</td>`;};
    return `<table class="ajc-cruce"><thead><tr><th>Área</th>${fams.map(f=>`<th>${cbtn('familia',f,ccorto(f),st.fam===f&&!st.area,cnom(f))}</th>`).join('')}<th>${st.medida==='stock'?'Stock':'Neto'}</th></tr></thead>
      <tbody>${areas.map(a=>`<tr><td>${cbtn('area',a,cnom(a),st.area===a&&!st.fam)}</td>${fams.map(f=>celda(f,a)).join('')}<td><b>${fmt(tot(a))}</b></td></tr>`).join('')}</tbody>
      <tfoot><tr><td>Total</td>${fams.map(f=>`<td>${fmt(mat.cells.filter(r=>r.fam===f).reduce((s,r)=>s+r.valor,0))}</td>`).join('')}<td>${fmt(mat.total)}</td></tr></tfoot></table>
      <p class="ajc-pie">Un punto: sin registros en esa área y familia; un 0, registros que suman cero. Un clic en una celda, una familia o un área enfoca el detalle.</p>`;}
  const valor=r=>[r.nombre,r.falto,r.sobro,r.saldo,r.lineas?r.tol/r.lineas:null,r.exact,r.n80,r.total,r.valorizado];
  const carta=cordenar(D.fams.filter(r=>!B.oper.has(r.nombre)),st,'familias',valor),oper=D.fams.filter(r=>B.oper.has(r.nombre)),max=Math.max(...D.fams.map(r=>Math.abs(r.saldo)),1);
  const fila=(r,op=false)=>`<tr class="${st.fam===r.nombre&&!st.area?'chosen':''}" title="${cesc(`Sin compensar ${csol(r.total)}${r.valorizado!=null?` · stock ${csol(r.valorizado)}`:''}`)}"><td>${cbtn('familia',r.nombre,cnom(r.nombre),st.fam===r.nombre&&!st.area)}</td>
    <td class="neg">${cint(r.falto)}</td><td class="pos">${cint(r.sobro)}</td><td><span class="ajc-neto"><span class="ajc-eje"><i class="${op?'op':r.saldo<0?'neg':'pos'}" style="${r.saldo<0?'right':'left'}:50%;width:${Math.min(50,50*Math.abs(r.saldo)/max)}%"></i></span><b>${cint(r.saldo)}</b></span></td>
    <td>${cpct(r.tol,r.lineas)}</td><td>${cp(r.exact)}</td><td>${r.n80??'—'} / ${r.de??'—'}</td></tr>`;
  const total=(nombre,m)=>`<tr class="ajc-tot"><td>${cesc(nombre)}</td><td>${cint(m.falto)}</td><td>${cint(m.sobro)}</td><td>${cint(m.saldo)}</td><td>${cpct(m.tol,m.lineas)}</td><td>${cp(m.exact)}</td><td>${m.n80??'—'} / ${m.de??'—'}</td></tr>`;
  let aparte='';
  if(oper.length){const subs=[...cgroup(D.rs.filter(r=>B.oper.has(r.fam)),r=>r.sub)].map(([s,g])=>[s,csum(g,'val')]).filter(([,v])=>v<-.5).sort((a,b)=>a[1]-b[1]).slice(0,3);
    aparte=`<tr class="ajc-sep"><td colspan="7">Aparte: insumos de operación. Ninguna receta los descarga: su consumo aparece recién al contar.${subs.length?` ${subs.map(([s,v])=>`${cesc(cnom(s))} ${csol(v)}`).join(' · ')}.`:''}</td></tr>${oper.map(r=>fila(r,true)).join('')}${total('Todo el cierre',D.m)}`;}
  const heads=['Familia','Faltó','Sobró','Neto','±S/ 5','Exactas','80 %'];
  return `<table class="ajc-familias"><thead><tr>${heads.map((t,i)=>`<th title="${i===4?'Líneas con stock cuya diferencia es de S/ 5 o menos':i===6?'Cuántos productos explican el 80 % de la diferencia':''}">${cbtn('ordentab',`familias|${i}`,t+' ↕')}</th>`).join('')}</tr></thead>
    <tbody>${carta.map(r=>fila(r)).join('')}${total(oper.length?'Alimentos y bebidas':'Total de los filtros',oper.length?D.mc:D.m)}${aparte}</tbody></table>`;
}
function ccortes(G,D){const {st}=D,S=cserie(G);
  if(st.vg==='tabla'){
    return `<div class="ajc-scroll">${ctabla(['Corte','Faltó','Sobró','Neto','Áreas','Líneas','Exactas','±S/ 5'],S.tabla.map(r=>`<tr class="${r.s.tipo==='cierre'?'':'ajc-parcial'}${r.i===st.c?' chosen':''}"><td>${cbtn('corte',r.i,r.s.corto.replace(/ \d{4}$/,''),r.i===st.c)}<small>${cesc(r.s.etiqueta_anio)}</small></td>
      <td class="neg">${cint(r.m.falto)}</td><td class="pos">${cint(r.m.sobro)}</td><td><b>${cint(r.m.saldo)}</b></td><td>${r.areas}</td><td>${cn(r.m.lineas)}</td><td>${cp(r.m.exact)}</td><td>${cpct(r.m.tol,r.m.lineas)}</td></tr>`),'ajc-compacta')}</div>
      <p class="ajc-pie">Todas las familias de los filtros. Un parcial cuenta pocas áreas: un neto chico en un parcial no es una mejora, y las áreas y líneas con stock lo dicen.</p>`;}
  return `<div class="ajc-graf" data-k="graf" aria-label="Faltó y sobró de los últimos 12 cierres"></div>
    <div class="ajc-ley"><span><i class="pos"></i>Sobró</span><span><i class="neg"></i>Faltó</span><span><i class="pto"></i>Neto</span>${D.hayOper?'<span><i class="op"></i>Insumos de operación</span>':''}</div>`;
}
function cgrafico(G){const caja=G.root.querySelector('[data-k=graf]');if(!caja)return;
  const W=Math.round(caja.clientWidth),H=Math.round(caja.clientHeight)||220;if(!W)return;
  const S=cserie(G).cierres,n=S.length;if(!n){caja.innerHTML='<p class="ajc-pie">Sin cierres para estos filtros.</p>';return;}
  const vals=S.flatMap(r=>[r.c.sobro,r.c.falto,r.o.saldo,0]),hi=Math.max(...vals),lo=Math.min(...vals),T=10,B=30,an=(W-8)/n;
  const y=v=>T+(hi-v)/((hi-lo)||1)*(H-T-B);
  let s=`<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Faltó y sobró de los últimos ${n} cierres">`;
  S.forEach((r,j)=>{const x=4+an*j,w=an*.34,x1=x+an*.14,x2=x1+w+2,[m,a]=r.s.corto.replace(/^Cierre /,'').split(' ');
    if(r.i===G.st.c)s+=`<rect class="sel" x="${x+1}" y="${T-6}" width="${an-2}" height="${H-T-B+10}" rx="6"/>`;
    s+=`<rect class="pos" x="${x1}" y="${y(r.c.sobro)}" width="${w}" height="${Math.max(1,y(0)-y(r.c.sobro))}" rx="2"/><rect class="neg" x="${x1}" y="${y(0)}" width="${w}" height="${Math.max(1,y(r.c.falto)-y(0))}" rx="2"/>`;
    if(Math.abs(r.o.saldo)>.5)s+=`<rect class="op" x="${x2}" y="${Math.min(y(0),y(r.o.saldo))}" width="${w*.7}" height="${Math.max(1,Math.abs(y(r.o.saldo)-y(0)))}" rx="2"/>`;
    s+=`<circle class="pto" cx="${x1+w/2}" cy="${y(r.c.saldo)}" r="3.2"/><text x="${x+an/2}" y="${H-16}" text-anchor="middle">${cesc(m||'')}</text><text x="${x+an/2}" y="${H-4}" text-anchor="middle">${cesc((a||'').slice(2))}</text>`;
    s+=`<rect class="toque" data-act="corte" data-v="${r.i}" data-j="${j}" x="${x}" y="0" width="${an}" height="${H}"><title>${cesc(`${r.s.corto} · ${r.s.etiqueta_anio}\nFaltó ${csol(r.c.falto)} · sobró ${csol(r.c.sobro)} · neto ${csol(r.c.saldo)}\n${r.areas} áreas, ${cn(r.c.lineas)} líneas${Math.abs(r.o.saldo)>.5?`\nOperación ${csol(r.o.saldo)}`:''}`)}</title></rect>`;});
  caja.innerHTML=s+`<line class="cero" x1="4" x2="${W-4}" y1="${y(0)}" y2="${y(0)}"/></svg>`;
}
function cprimera(G,D){
  const {P}=G.B,{st,mc,mo,m}=D,base=G.B.cortes[st.c]||[],areas=[...new Set(base.filter(r=>r.val!==0&&r.area&&r.area!=='---').map(r=>r.area))].sort();
  const ses=P.sesiones[st.c],cob=new Set(D.scope.filter(r=>r.flags&1).map(r=>r.area)).size,ops=P.sesiones.map((s,i)=>[i,`${s.corto} · ${s.etiqueta_anio}`]);
  const kpi5=D.hayOper?ckpi('Insumos de operación',csol(mo.saldo),`faltó ${csol(-mo.falto)} · aparte`,'Costos Producción: ninguna receta los descarga','op','ajc-aparte')
    :ckpi('Diferencia absoluta',csol(mc.total),'faltó + sobró sin compensar');
  const foco=[st.fam&&cnom(st.fam),st.area&&cnom(st.area)].filter(Boolean).join(' · ');
  return `<header><h3>Diferencias del cierre</h3><span class="ajc-ses">${cbtn('mover',-1,'‹',false,'Corte anterior','ajc-flecha')}${cselect('corte',ops,st.c,'Corte')}${cbtn('mover',1,'›',false,'Corte siguiente','ajc-flecha')}</span>
    <div class="ajc-der">${cfiltro(G,'areas','Áreas',areas)}${cfiltro(G,'fams','Familias',P.dic.fam)}${cbtn('excel','resumen','Excel del resumen')}</div></header>
    <p class="ajc-note">${ses?cesc(`${ses.nombre} · contado el ${ses.etiqueta_anio} · ${ses.n_dias} ${ses.n_dias===1?'día':'días'} · ${ses.juntas} ${ses.juntas===1?'conteo':'conteos'} · ${cn(D.rs.length)} registros · ${cn(cob)} áreas con stock`):'Sin sesiones disponibles'}${P.sin_fecha?` · ${cn(P.sin_fecha)} líneas sin fecha excluidas`:''}</p>
    ${ses?`<p class="ajc-frase">${cfrase(G,D)}</p>`:''}
    <div class="ajc-kpis">${ckpi('Faltó',csol(mc.falto),'suma de las líneas negativas','','neg')}${ckpi('Sobró',csol(mc.sobro),'suma de las líneas positivas','','pos')}${ckpi('Neto',csol(mc.saldo),`sin compensar: ${csol(mc.total)}`,'Saldo de los ajustes',cclase(mc.saldo))}${ckpi('Dentro de ±S/ 5',cpct(mc.tol,mc.lineas),`${cn(mc.tol)} de ${cn(mc.lineas)} líneas · exactas ${cp(mc.exact)}`,'Líneas con stock cuya diferencia es de S/ 5 o menos. Exactas: sin diferencia valorizada.')}${kpi5}</div>
    <div class="ajc-cuerpo">
      <section class="ajc-panel"><div class="ajc-phead"><h4>${st.vf==='cruce'?'Familia × Área':'Por familia'}</h4>${st.vf==='cruce'&&P.hay.stock?cseg('medida',[['val','Ajuste'],['stock','Stock']],st.medida,'Qué mide el cruce'):''}${cseg('vf',[['lista','Lista'],['cruce','Cruce con áreas']],st.vf,'Cómo ver las familias')}</div>
        <div class="ajc-scroll">${D.rs.length?cfamilias(G,D):'<p class="ajc-pie">No hay líneas para estos filtros.</p>'}</div></section>
      <section class="ajc-panel"><div class="ajc-phead"><h4>Los últimos 12 cierres${foco?` · ${cesc(foco)}`:''}</h4><span class="ajc-pista">${st.vg==='graf'?'un clic elige el cierre':''}</span>${cseg('vg',[['graf','Gráfico'],['tabla','Tabla con parciales']],st.vg,'Gráfico o tabla')}</div>
        ${ccortes(G,D)}</section>
    </div>`;
}
// ── Abajo: qué productos ─────────────────────────────────────────────────
const cbuscar=(r,q)=>!q||[r.cod,r.prod,r.fam,r.area,r.sub].join(' ').toLocaleLowerCase().includes(q.toLocaleLowerCase());
const cprodheads=['Código','Familia','Subfamilia','Producto','Unidad kardex','Área','Stock sistema','Diferencia','Conteo','Ajuste S/'];
const cprodvals=r=>[r.cod,r.fam,r.sub,r.prod,r.um,r.area,r.varias_um?null:r.sis,r.varias_um?null:r.dif,r.varias_um?null:r.fis,r.val];
function cporque(D,prod,lado){
  // La línea de más peso del lado elegido: un producto puede faltar en un área y sobrar en otra.
  const rs=D.scope.filter(r=>r.prod.trim()===prod&&(lado==='f'?r.val<0:r.val>0)),g=[...cgroup(rs,r=>JSON.stringify([r.area,r.cod]))].map(([k,x])=>({k:JSON.parse(k),v:csum(x,'val'),fam:x[0].fam})).sort((a,b)=>Math.abs(b.v)-Math.abs(a.v))[0];
  return g&&g.k[1]?{area:g.k[0],cod:g.k[1],fam:g.fam}:null;
}
function clistashtml(G,D){const {st}=D,{B}=G,P=B.P;
  if(st.vf==='cruce'&&st.medida==='stock'){
    const ps=[...cgroup(D.scope,r=>JSON.stringify([r.id,r.um])).values()].map(g=>({...g[0],fis:csum(g,'fis'),stock:csum(g,'stock'),areas:new Set(g.map(r=>r.area)).size})).filter(r=>cbuscar(r,st.q)).sort((a,b)=>b.stock-a.stock);
    G.exportar={nombre:'Stock de productos',cabeza:['Código','Producto','Unidad','Conteo','Stock valorizado S/'],filas:ps.map(r=>[r.cod,r.prod,r.um,r.fis,r.stock]),decimales:6};G.nfilas=ps.length;
    G.sub='Top productos: con el cruce en «Stock», el stock valorizado y la cantidad contada de cada producto.';
    return ctabla(['Producto','Unidad','Contado','Stock','Áreas'],ps.slice(0,st.limite).map(r=>`<tr><td>${cesc(r.prod)}<small>${cesc(r.cod)}</small></td><td>${cesc(r.um)}</td><td>${cn(r.fis,3)}</td><td>${csol(r.stock)}</td><td>${r.areas}</td></tr>`));
  }
  const listas=clistas(D.scope,true).filter(r=>cbuscar(r,st.q)),rep=crepite(G),par={f:new Map(cpareto(D.scope,'Faltantes').map(r=>[r.prod.trim(),r])),s:new Map(cpareto(D.scope,'Sobrantes').map(r=>[r.prod.trim(),r]))};
  G.exportar={nombre:'Listas',cabeza:cprodheads,filas:listas.map(cprodvals),decimales:6};
  const lado=l=>{const ps=listas.filter(r=>l==='f'?r.val<0:r.val>0);
    if(st.orden==='pareto')ps.sort((a,b)=>(par[l].get(a.prod)?.acum??999)-(par[l].get(b.prod)?.acum??999));
    return ps;};
  const item=(r,l)=>{const areas=careasPareto(D.scope.filter(x=>x.prod.trim()===r.prod).map(x=>({...x,prod:r.prod})),r.prod).filter(a=>Math.abs(a.val)>.005||Math.abs(a.dif)>1e-9);
    const otra=areas.filter(a=>l==='f'?a.val>.5:a.val<-.5).reduce((s,a)=>s+a.val,0),key=l+'|'+r.prod,abierto=st.abiertas.includes(key),n=rep.n.get(r.prod)||0,pp=par[l].get(r.prod),destino=cporque(D,r.prod,l);
    return `<div class="ajc-item"><span class="ajc-n" title="${cesc(r.prod)}">${areas.length>1?cbtn('abrirlista',key,abierto?'▾':'▸',abierto,'Ver sus áreas','ajc-abre'):'<span class="ajc-abre"></span>'}${cesc(r.prod)}</span>
      <span class="ajc-v ${l==='f'?'neg':'pos'}">${csol(r.val)}${st.orden==='pareto'&&pp?`<small>${cp(pp.pct)} · acum. ${cp(pp.acum)}</small>`:''}</span>
      <span class="ajc-d">${cesc(r.area)} · ${r.dif==null?'varias unidades':`${ccant(r.dif)} ${cesc(r.um)}`}${B.oper.has(r.fam)?'<span class="ajc-tag op">operación</span>':''}${l==='f'&&n>=3?`<span class="ajc-tag rep">faltó ${n} de ${rep.de} cierres</span>`:''}${Math.abs(otra)>.5?`<span class="ajc-tag">${l==='f'?'sobró':'faltó'} ${csol(Math.abs(otra))} en otra área</span>`:''}</span>
      ${destino?`<button type="button" class="ajc-porque" data-act="porque" data-v="${cesc(JSON.stringify({...destino,lado:l}))}">¿Por qué? →</button>`:'<span></span>'}
      ${abierto?`<span class="ajc-areas-de">${areas.map(a=>`<span><span>${cesc(cnom(a.area))} · ${ccant(a.dif)} ${cesc(a.um)}</span><b class="${cclase(a.val)}">${csol(a.val)}</b></span>`).join('')}</span>`:''}</div>`;};
  const f=lado('f'),s=lado('s'),tf=csum(f,'val'),ts=csum(s,'val'),m=cmetricas(D.scope,P.hay),comp=m.falto-tf;
  // El 80 % de la MISMA lista que se ve (por nombre, áreas juntas).
  const n80=ps=>{const vs=ps.map(r=>Math.abs(r.val)).sort((a,b)=>b-a),t=vs.reduce((a,v)=>a+v,0);let acc=0,n=0;for(const v of vs){n++;acc+=v;if(acc/t>=.8-CEPS)break;}return {n,de:vs.length};};
  const nf=n80(f),ns=n80(s),opf=csum(f.filter(r=>B.oper.has(r.fam)),'val');G.nfilas=Math.max(f.length,s.length);
  const e=cespejos(D.scope);G.sub=e.n?`${e.n} productos faltan en un área y sobran en otra (${csol(e.falto)} / ${csol(e.sobro)}). Es una coincidencia de signos, no una causa: «¿Por qué?» abre la línea en «Análisis de diferencias».`:'«¿Por qué?» abre la línea en «Análisis de diferencias», la vista de abajo.';
  return `<div class="ajc-toolbar">${cseg('orden',[['monto','Por monto'],['pareto','Pareto']],st.orden,'Orden')}<span class="ajc-pista">${st.orden==='pareto'?'el % de cada producto sobre el neto de su lado, y el acumulado':'▸ abre las áreas de un producto'}</span></div>
    <div class="ajc-lists"><section><h4>Faltantes · <span class="neg">${csol(tf)}</span></h4><p class="ajc-resumen">${cn(f.length)} productos, áreas juntas.${Math.abs(opf)>.5?` De ello, insumos de operación ${csol(opf)}.`:''}${Math.abs(comp)>.5?` ${csol(Math.abs(comp))} del faltante por línea se compensó con sobrantes del mismo producto en otra área.`:''} ${nf.n} de ${nf.de} explican el 80 %.</p>
      <div class="ajc-scroll">${f.slice(0,st.limite).map(r=>item(r,'f')).join('')||'<p class="ajc-pie">Ninguno con estos filtros.</p>'}</div></section>
    <section><h4>Sobrantes · <span class="pos">${csol(ts)}</span></h4><p class="ajc-resumen">${cn(s.length)} productos. ${ns.n} de ${ns.de} explican el 80 %. Un sobrante suele ser stock que estaba en negativo, no mercadería que apareció.</p>
      <div class="ajc-scroll">${s.slice(0,st.limite).map(r=>item(r,'s')).join('')||'<p class="ajc-pie">Ninguno con estos filtros.</p>'}</div></section></div>`;
}
function ctabcomparar(G,D){
  const {st}=D,clave=JSON.stringify([st.c,st.prev,st.fams,st.areas,st.fam,st.area]);
  if(!G.B.compare.has(clave)){if(G.B.compare.size>10)G.B.compare.clear();G.B.compare.set(clave,ccomparar(D.scope,D.prev,D.hist));}
  const comp=G.B.compare.get(clave),counts=Object.fromEntries(cestados.slice(1).map(s=>[s,comp.filter(r=>r.estado===s).length]));
  const rows=cordenar(comp.filter(r=>(st.status==='Todas'||r.estado===st.status)&&cbuscar(r,st.q)),st,'comparar',r=>[r.estado,r.prod,r.area,r.anterior?.observada?r.anterior.val:null,r.actual?.observada?r.actual.val:null,r.delta,r.de?r.con/r.de:null,r.signo||r.motivo]);G.comp=rows;G.nfilas=rows.length;
  const comparables=comp.filter(r=>r.comparable),delta=csum(comparables,'delta'),heads=['Estado','Código','Producto','Familia','Área','Unidad','Anterior neto S/','Actual neto S/','Diferencia anterior cantidad','Diferencia actual cantidad','Anterior absoluto S/','Actual absoluto S/','Cambio absoluto S/','Recurrencias','Cortes con stock','Observación'];
  G.exportar={nombre:'Comparación',cabeza:heads,filas:rows.map(r=>[r.estado,r.cod,r.prod,r.fam,r.area,r.um,r.anterior?.observada?r.anterior.val:null,r.actual?.observada?r.actual.val:null,G.B.P.hay.dif&&r.anterior?.observada?r.anterior.dif:null,G.B.P.hay.dif&&r.actual?.observada?r.actual.dif:null,r.anterior?.observada?r.abs_anterior:null,r.actual?.observada?r.abs_actual:null,r.delta,r.con,r.de,r.motivo+(r.signo?` · ${r.signo}`:'')]),decimales:6};
  G.comparacion=comp;const n=cmetricas(D.scope,G.B.P.hay);
  G.sub='Nueva / Recurrente / Resuelta requieren stock y datos completos en ambos cortes. Recurrencias: cortes con diferencia / cortes con stock hasta el seleccionado, por producto × área × unidad. Un clic en un estado abre su historial.';
  const orden=['Recurrente','Nueva','Resuelta','Sin diferencia','Sin base','Todas'];
  return `<div class="ajc-toolbar">${cselect('prev',G.B.P.sesiones.map((s,i)=>[i,s.corto+' · '+s.etiqueta_anio]).filter(([i])=>i<st.c),st.prev,'Comparar con')}
      <span class="ajc-chips" role="group" aria-label="Estado">${orden.map(s=>cbtn('estado',s,s==='Todas'?`Todas ${cn(comp.length)}`:`${s} ${cn(counts[s])}`,st.status===s,'',s==='Sin base'?'ajc-tenue':'')).join('')}</span></div>
    <p class="ajc-resumen">${st.prev<0?'No hay un corte anterior para comparar.':`${cn(comparables.length)} de ${cn(comp.length)} combinaciones comparables · cambio absoluto en esas líneas: ${csol(delta)}.`} El total actual del detalle es ${csol(n.total)}. Una ausencia o stock cero/cero queda «Sin base»: no es una mejora.</p>
    <div class="ajc-scroll ajc-detail">${ctabla(['Estado','Producto','Área · Unidad','Anterior neto','Actual neto','Δ absoluto','Repite / con stock','Observación'],rows.slice(0,st.limite).map(r=>`<tr class="${r.key===st.elegido?'chosen':''}" title="${cesc(r.motivo)}"><td>${cbtn('elegido',r.key,r.estado,r.key===st.elegido)}</td><td>${cesc(r.prod)}<small>${cesc(r.cod)}</small></td><td>${cesc(cnom(r.area))} · ${cesc(r.um)}</td>
      <td title="${cesc(r.anterior?`Faltó ${csol(r.anterior.falto)} · sobró ${csol(r.anterior.sobro)}`:'Sin registro')}">${r.anterior?.observada?csol(r.anterior.val)+(G.B.P.hay.dif?`<small class="ajc-qty">${cn(r.anterior.dif,3)} ${cesc(r.um)}</small>`:''):'—'}</td>
      <td title="${cesc(r.actual?`Faltó ${csol(r.actual.falto)} · sobró ${csol(r.actual.sobro)}`:'Sin registro')}">${r.actual?.observada?csol(r.actual.val)+(G.B.P.hay.dif?`<small class="ajc-qty">${cn(r.actual.dif,3)} ${cesc(r.um)}</small>`:''):'—'}</td>
      <td>${csol(r.delta)}</td><td>${r.con} / ${r.de}</td><td class="ajc-obs">${cesc(r.signo||(r.comparable?'':r.motivo))}</td></tr>`),'ajc-comp',"comparar")}</div>`;
}
function chistoria(G,D){const r=G.comp?.find(x=>x.key===D.st.elegido);if(!r)return '';
  return `<aside class="ajc-history"><b>${cesc(r.prod)} · ${cesc(cnom(r.area))} · ${cesc(r.um)}</b><div>${D.hist.map((rows,i)=>{const g=cgrupos(rows.filter(x=>x.key===r.key)).get(r.key);return `<span title="${cesc(G.B.P.sesiones[i].etiqueta_anio)}">${cesc(G.B.P.sesiones[i].corto)}<strong class="${g?.observada?cclase(g.val):''}">${g?.observada?csol(g.val):'Sin base'}</strong></span>`;}).join('')}</div></aside>`;
}
function ctabareas(G,D){const {st}=D,{B}=G,P=B.P;
  const oper=new Map([...cgroup(D.scope.filter(r=>B.oper.has(r.fam)),r=>r.area)].map(([a,g])=>[a,csum(g,'val')]));
  const rows=cordenar(cresumen(D.scope,'area',P.hay).filter(r=>r.total>CEPS),st,'areas',r=>[r.nombre,r.falto,r.sobro,r.saldo,r.total,r.lineas,r.dif,r.exact,r.lineas?r.tol/r.lineas:null,oper.get(r.nombre)??0]);
  const heads=['Área','Faltó S/','Sobró S/','Neto S/','Absoluto S/','Líneas con stock','Con diferencia','Exactitud %','Dentro de ±S/ 5 %','Operación S/'];
  G.exportar={nombre:'Áreas',cabeza:heads,filas:rows.map(r=>[r.nombre,r.falto,r.sobro,r.saldo,r.total,r.lineas,r.dif,r.exact,r.lineas?100*r.tol/r.lineas:null,oper.get(r.nombre)??0]),decimales:6};
  G.sub='Todas las familias de los filtros, con lo que es de los insumos de operación aparte. Un clic en un área enfoca el detalle.';
  return ctabla(['Área','Faltó','Sobró','Neto','Sin compensar','Líneas','Con diferencia','Exactas','±S/ 5','de ello, operación'],rows.map(r=>`<tr class="${st.area===r.nombre?'chosen':''}"><td>${cbtn('area',r.nombre,cnom(r.nombre),st.area===r.nombre)}</td><td class="neg">${cint(r.falto)}</td><td class="pos">${cint(r.sobro)}</td><td><b class="${cclase(r.saldo)}">${cint(r.saldo)}</b></td><td>${cn(r.total)}</td><td>${cn(r.lineas)}</td><td>${cn(r.dif)}</td><td>${cp(r.exact)}</td><td>${cpct(r.tol,r.lineas)}</td><td class="${(oper.get(r.nombre)||0)<-.5?'op':''}">${Math.abs(oper.get(r.nombre)||0)>.5?cint(oper.get(r.nombre)):'—'}</td></tr>`),'','areas');
}
function ctablineas(G,D){
  const {st}=D,prods=cordenar(cproductos(D.scope,st.juntas).filter(r=>cbuscar(r,st.q)),st,'lineas',cprodvals);G.exportar={nombre:'Productos',cabeza:cprodheads,filas:prods.flatMap(r=>[cprodvals(r),...(r.hijos||[]).map(cprodvals)]),decimales:6};
  const fila=(r,hijo=false)=>`<tr class="${hijo?'ajc-child':''}"><td>${!hijo&&r.hijos?.length?cbtn('abrir',r.id,st.abiertos.includes(r.id)?'▾':'▸',st.abiertos.includes(r.id),'Ver sus áreas','ajc-abre'):'<span class="ajc-abre"></span>'}<span title="${cesc(r.compensado?'Falta en un área y sobra en otra. Abra las áreas para revisarlo.':'')}">${cesc(r.prod)}${r.compensado?' ↔':''}</span><small>${cesc(r.cod)} · ${cesc(cnom(r.fam))}${r.sub?` · ${cesc(cnom(r.sub))}`:''}</small></td>
    <td>${cesc(cnom(r.area))}</td><td>${cesc(r.varias_um?'Varias unidades':r.um)}</td>${[r.varias_um?null:r.sis,r.varias_um?null:r.fis,r.varias_um?null:r.dif].map(v=>`<td>${ccant(v)}</td>`).join('')}<td class="${cclase(r.val)}">${csol(r.val)}</td></tr>`;
  const filas=[];for(const r of prods.slice(0,st.limite)){filas.push(fila(r));if(st.abiertos.includes(r.id))filas.push(...(r.hijos||[]).map(x=>fila(x,true)));}
  G.nfilas=prods.length;G.sub='Cada línea del cierre. Con «Áreas juntas», ▸ abre las áreas de un producto; la subfamilia va debajo del nombre.';
  return `<div class="ajc-toolbar">${cseg('juntas',[['si','Áreas juntas'],['no','Áreas separadas']],st.juntas?'si':'no','Áreas')}</div>
    <div class="ajc-scroll ajc-detail">${`<table class="ajc-lineas"><thead><tr>${['Producto','Área','Unidad','Sistema','Contado','Diferencia','Ajuste'].map((t,i)=>`<th>${cbtn('ordentab',`lineas|${[3,5,4,6,8,7,9][i]}`,t+' ↕')}</th>`).join('')}</tr></thead><tbody>${filas.join('')}</tbody></table>`}</div>`;
}
function csegunda(G,D){const {st}=D,{P}=G.B;
  G.exportar=null;G.nfilas=0;G.sub='';
  let contenido='';
  if(st.tab==='listas')contenido=clistashtml(G,D);
  else if(st.tab==='comparar')contenido=ctabcomparar(G,D);
  else if(st.tab==='areas')contenido=`<div class="ajc-scroll ajc-detail">${ctabareas(G,D)}</div>`;
  else contenido=ctablineas(G,D);
  const foco=[st.fam&&cnom(st.fam),st.area&&cnom(st.area)].filter(Boolean).join(' · ');
  return `<header><h3>Qué productos · ${cesc(P.sesiones[st.c]?.corto||'')}</h3>${foco?`<span class="ajc-chip">${cesc(foco)}${cbtn('limpiar','','✕',false,'Quitar el foco')}</span>`:''}
      <div class="ajc-der"><input class="ajc-search" type="search" aria-label="Buscar en el detalle" placeholder="Buscar código, producto o área" value="${cesc(st.q)}" data-input="buscar">${cbtn('excel','detalle','Excel del detalle')}</div></header>
    <nav class="ajc-tabs" role="tablist">${ctabs.map(([t,n])=>`<button type="button" role="tab" data-act="tab" data-v="${t}" aria-selected="${st.tab===t}" class="${st.tab===t?'selected':''}">${n}</button>`).join('')}</nav>
    ${contenido||'<p class="ajc-pie">No hay diferencias para este detalle.</p>'}${st.tab==='comparar'?chistoria(G,D):''}<footer><span>${cesc(G.sub)}</span>${G.nfilas>st.limite?cbtn('mas','',`Ver más (${Math.min(st.limite,G.nfilas)} / ${G.nfilas})`):''}</footer>`;
}
function ccontexto(G,D){const {P}=G.B,{st}=D;return {nombre:'Contexto',cabeza:['Criterio','Valor'],filas:[
  ['Vista',st.vf==='cruce'?'Familia × Área':'Por familia'],['Corte actual',P.sesiones[st.c]?.corto],['Días actual',P.sesiones[st.c]?.etiqueta_anio],['Corte de comparación',P.sesiones[st.prev]?.corto||'Sin anterior'],['Días comparación',P.sesiones[st.prev]?.etiqueta_anio||''],
  ['Familias',st.fams.join(' / ')||'Todas'],['Áreas',st.areas.join(' / ')||'Todas'],['Familia en foco',st.fam||'Todas'],['Área en foco',st.area||'Todas'],['Pestaña',(ctabs.find(([t])=>t===st.tab)||[])[1]],['Orden de las listas',st.orden==='pareto'?'Pareto':'Por monto'],['Áreas de productos',st.juntas?'Juntas':'Separadas'],['Medida del cruce',st.medida==='val'?'Ajuste valorizado':'Stock valorizado'],['Estado',st.status],['Búsqueda',st.q],
  ['Insumos de operación',(P.operacion||[]).join(' / ')||'Ninguna familia'],['Resumen','Faltó, Sobró y Neto de los indicadores: alimentos y bebidas, sin los insumos de operación, que van aparte. La tabla suma las dos en «Todo el cierre».'],
  ['Dentro de ±S/ 5','Líneas con stock cuya diferencia valorizada es de S/ 5 o menos. Exactitud: sin diferencia valorizada (tolerancia 0).'],
  ['Comparabilidad','Código (o nombre sin código), área y unidad iguales. Stock no cero y números completos en ambos cortes. Ausente/cero-cero: Sin base.'],['Recurrencias','Cortes con diferencia / cortes con stock y datos completos, hasta el actual.'],['Unidades','Cantidades numéricas con seis decimales. No se suman unidades diferentes.'],['Exportación','Resumen: filtros completos, con los cortes. Detalle: foco, pestaña, búsqueda y estado seleccionados. Todas sus filas, sin límite de pantalla.']]};}
function cexportar(G,tipo){const D=G.D;let hojas=[G.exportar];
  if(tipo==='resumen'){
    const {st}=D;let hoja;
    if(st.vf!=='cruce'){hoja={nombre:'Familias',cabeza:['Familia','Faltó S/','Sobró S/','Absoluto S/','Neto S/','Líneas con stock','Con diferencia','Exactitud %','Dentro de ±S/ 5 %','Productos 80 %','Productos con diferencia','Stock valorizado S/','Insumos de operación'],filas:D.fams.map(r=>[r.nombre,r.falto,r.sobro,r.total,r.saldo,r.lineas,r.dif,r.exact,r.lineas?100*r.tol/r.lineas:null,r.n80,r.de,r.valorizado,G.B.oper.has(r.nombre)?'Sí':'No']),decimales:6};}
    else{const m=cmatriz(D.rs,st.medida),cs=new Map(m.cells.map(r=>[JSON.stringify([r.fam,r.area]),r.valor]));hoja={nombre:'Familia y área',cabeza:['Familia',...m.areas,'Total'],filas:m.familias.map(f=>[f,...m.areas.map(a=>cs.get(JSON.stringify([f,a]))??null),m.cells.filter(r=>r.fam===f).reduce((s,r)=>s+r.valor,0)]),decimales:6};}
    const S=cserie(G).tabla;
    hojas=[hoja,{nombre:'Cortes',cabeza:['Corte','Días registrados','Tipo','Faltó S/','Sobró S/','Absoluto S/','Neto S/','Áreas con stock','Líneas con stock','Exactitud %','Alimentos y bebidas neto S/','Insumos de operación neto S/'],filas:S.map(r=>[r.s.corto,r.s.etiqueta_anio,r.s.tipo,r.m.falto,r.m.sobro,r.m.total,r.m.saldo,r.areas,r.m.lineas,r.m.exact,r.c.saldo,r.o.saldo]),decimales:6}];
  }
  return libro([...hojas.filter(Boolean).length?hojas.filter(Boolean):[{nombre:'Sin filas',cabeza:['Sin datos'],filas:[]}],ccontexto(G,D)]);
}
function cpintar(G,soloDetalle=false){
  G.D=cdatos(G);if(!soloDetalle){G.root.querySelector('.ajc-main').innerHTML=cprimera(G,G.D);cgrafico(G);}
  G.root.querySelector('.ajc-bottom').innerHTML=csegunda(G,G.D);
}
function ccambiarcorte(G,i){const {st}=G,P=G.B.P;if(!(i>=0&&i<P.sesiones.length))return;st.c=i;st.prev=cprev(P,i);st.area=null;st.elegido=null;st.limite=150;
  const areas=new Set((G.B.cortes[i]||[]).filter(r=>r.val!==0&&r.area&&r.area!=='---').map(r=>r.area));st.areas=st.areas.filter(a=>areas.has(a));}
function cenlazar(G){const root=G.root;
  root.addEventListener('click',ev=>{const b=ev.target.closest('[data-act]');if(!b||!root.contains(b))return;const {act,v}=b.dataset,st=G.st;let detalle=true;
    if(act==='vf'){st.vf=v;st.limite=150;detalle=false;}
    else if(act==='corte'){ccambiarcorte(G,+v);detalle=false;}
    else if(act==='mover'){ccambiarcorte(G,st.c+(+v));detalle=false;}
    else if(act==='vg'){st.vg=v;detalle=false;}
    else if(act==='familia'){st.fam=st.fam===v&&!st.area?null:v;st.area=null;detalle=false;}
    else if(act==='celda'){const [f,a]=JSON.parse(v);if(st.fam===f&&st.area===a){st.fam=null;st.area=null;}else{st.fam=f;st.area=a;}detalle=false;}
    else if(act==='area'){st.area=st.area===v&&!st.fam?null:v;st.fam=null;detalle=false;}
    else if(act==='medida'){st.medida=v;detalle=false;}
    else if(act==='todos'){st[v]=[];st.fam=null;st.area=null;detalle=false;}
    else if(act==='inicial'){st.fams=[...G.B.P.familias_iniciales];st.fam=null;st.area=null;detalle=false;}
    else if(act==='limpiar'){st.fam=null;st.area=null;detalle=false;}
    else if(act==='tab'){st.tab=v;st.limite=150;st.elegido=null;}
    else if(act==='juntas')st.juntas=v==='si';else if(act==='orden')st.orden=v;
    else if(act==='estado'){st.status=v;st.limite=150;st.elegido=null;}else if(act==='elegido')st.elegido=st.elegido===v?null:v;
    else if(act==='ordentab'){const [t,i]=v.split('|'),o=st.ordenTabla[t];st.ordenTabla[t]={i:+i,d:o?.i===+i?-o.d:1};detalle=t!=='familias';}
    else if(act==='abrir')st.abiertos=st.abiertos.includes(v)?st.abiertos.filter(x=>x!==v):[...st.abiertos,v];
    else if(act==='abrirlista')st.abiertas=st.abiertas.includes(v)?st.abiertas.filter(x=>x!==v):[...st.abiertas,v];
    else if(act==='mas')st.limite+=150;
    else if(act==='porque'){if(G.enviar)G.enviar('porque',{...JSON.parse(v),ses:G.B.P.sesiones[st.c]?.clave,n:Date.now()});return;}
    else if(act==='excel'){bajar(`diferencias_${archivo(G.B.P.sesiones[st.c]?.corto||'cierre')}_${v}.xlsx`,cexportar(G,v));return;}
    cpintar(G,detalle);
  });
  root.addEventListener('change',ev=>{const el=ev.target,st=G.st,f=el.dataset.filter;
    if(f){st[f]=el.checked?[...st[f],el.value]:st[f].filter(x=>x!==el.value);st.fam=null;st.area=null;cpintar(G);root.querySelector(`input[data-filter="${f}"]`)?.closest('details').setAttribute('open','');return;}
    if(el.dataset.change==='corte'){ccambiarcorte(G,+el.value);cpintar(G);}
    else if(el.dataset.change==='prev'){st.prev=+el.value;st.elegido=null;cpintar(G,true);}
  });
  root.addEventListener('input',ev=>{const e=ev.target;if(e.dataset.input!=='buscar')return;const pos=e.selectionStart;G.st.q=e.value;G.st.limite=150;cpintar(G,true);const n=root.querySelector('.ajc-search');n.focus();if(pos!=null)n.setSelectionRange(pos,pos);});
  root.addEventListener('keydown',ev=>{if(ev.key==='Escape')root.querySelectorAll('details[open]').forEach(d=>d.open=false);});
  root.addEventListener('scroll',ev=>{const e=ev.target,st=G.st;if(e.matches?.('.ajc-bottom .ajc-scroll')&&e.scrollTop+e.clientHeight>e.scrollHeight-70&&st.limite<G.nfilas){const y=e.scrollTop,x=e.scrollLeft,i=[...root.querySelectorAll('.ajc-bottom .ajc-scroll')].indexOf(e);st.limite+=150;cpintar(G,true);const n=root.querySelectorAll('.ajc-bottom .ajc-scroll')[i];if(n){n.scrollTop=y;n.scrollLeft=x;}}},true);
}
window.__ajCierreDatos={leer:cleer,metricas:cmetricas,resumen:cresumen,matriz:cmatriz,productos:cproductos,pareto:cpareto,areasPareto:careasPareto,listas:clistas,espejos:cespejos,comparar:ccomparar,grupos:cgrupos};
window.__ajCierreUI={inicial:cinicial,pintar:cpintar,exportar:cexportar,serie:cserie};
export default function(component){const {data:P,parentElement,setTriggerValue}=component;if(!P)return;
  const old=window.__ajCierre;old?.observer?.disconnect();old?.abort?.abort();
  const mismo=old?.B.P.sello===P.sello,st=mismo&&old.st&&'vf' in old.st?old.st:cinicial(P);
  if(old&&old.semilla!==P.perspectiva)st.vf=P.perspectiva==='Familia × Área'?'cruce':'lista';
  let root=parentElement.querySelector('.ajc');if(root)root.remove();root=document.createElement('div');root.className='ajc';root.innerHTML='<section class="ajc-card ajc-main"></section><section class="ajc-card ajc-bottom"></section>';parentElement.appendChild(root);
  const B=mismo?old.B:cleer(P);B.oper=new Set(P.operacion||[]);
  const G={root,st,B,semilla:P.perspectiva,enviar:setTriggerValue,abort:new AbortController()};window.__ajCierre=G;cenlazar(G);cpintar(G);
  let ancho=0;G.observer=new ResizeObserver(es=>{const w=Math.round(es[0].contentRect.width);if(w&&w!==ancho){ancho=w;cgrafico(G);}});G.observer.observe(root.querySelector('.ajc-main'));
  document.addEventListener('pointerdown',ev=>{if(!ev.composedPath().includes(root))root.querySelectorAll('details[open]').forEach(d=>d.open=false);},{signal:G.abort.signal});
}
