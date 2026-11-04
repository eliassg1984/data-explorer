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
// Los productos que faltan en un área y sobran en otra (#814: el quinto contador).
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
// ── La presentación (reglas #748 y #769) ─────────────────────────────────
// Divulgación progresiva, en una pantalla: cuatro indicadores; «Productos» con
// faltantes y sobrantes lado a lado y, al costado, la lectura del cierre; un
// clic en un producto abre su ficha, y lo demás espera en pestañas. Los
// insumos de operación van APARTE, no afuera.
const CTOL=5;
const csol=v=>v==null?'—':`${Math.round(v)<0?'−':''}S/ ${cn(Math.abs(v))}`;
const cint=v=>v==null?'—':`${Math.round(v)<0?'−':Math.round(v)>0?'+':''}${cn(Math.abs(v))}`;
const cnn=(n,t)=>`${cn(n)} ${t}${n===1?'':'s'}`;
const cpct=(a,b)=>b?`${Math.round(100*a/b)} %`:'—';
const ccant=v=>v==null?'—':Number(v).toLocaleString('en-US',{maximumFractionDigits:3});
// #818: la unidad corta en pantalla, como Consumo (consumo.js::corta); la entera queda en el
// title y en el Excel. Y el código entero, con los ceros de la izquierda en gris claro: no
// distinguen un producto de otro, y en cada fila eran seis caracteres de ruido.
const cum=u=>{const s=String(u??'').trim();return {KILOS:'kg',LITROS:'L',UND:'und',UNIDAD:'und',PORCION:'porc'}[s.toUpperCase()]||s.toLowerCase();};
const ccod=c=>{const s=String(c??''),z=(s.match(/^0+(?=.)/)||[''])[0];return z?`<i class="ajc-z">${z}</i>${cesc(s.slice(z.length))}`:cesc(s);};
const CMENOR=new Set(['de','del','y','e','la','las','el','los','con','sin','a','x']);
const cnom=s=>/^\d+ áreas$/.test(String(s??''))?String(s):String(s??'').toLocaleLowerCase('es').split(/(\s+)/).map((w,i)=>i&&CMENOR.has(w)?w:w.charAt(0).toLocaleUpperCase('es')+w.slice(1)).join('');
const CCORTO={'ALIMENTOS':'Alimentos','VINOS Y ESPUMANTES':'Vinos','ENVASES Y EMBALAJES':'Envases','BEBIDAS CON ALCOHOL':'Con alcohol','BEBIDAS SIN ALCOHOL':'Sin alcohol','COSTOS PRODUCCION':'Operación'};
const ccorto=f=>CCORTO[String(f).trim().toUpperCase()]||cnom(String(f).split(' ')[0]);
// #819: «Productos», no «Qué faltó»: la pestaña muestra también lo que sobró, y las
// demás se llaman por lo que listan.
const ctabs=[['listas','Productos'],['familias','Familias y áreas'],['cierres','12 cierres'],['comparar','Contra el anterior'],['lineas','Líneas']];

function cinicial(P){const cruce=P.perspectiva==='Familia × Área';return {c:P.inicial,prev:cprev(P,P.inicial),fams:[],areas:[],fam:null,area:null,
  vf:cruce?'cruce':'lista',medida:'val',vg:'graf',tab:cruce?'familias':'listas',orden:'monto',juntas:true,lado:'ambos',sel:null,ampl:false,
  q:'',status:'Recurrente',limite:150,abiertos:[],elegido:null,ordenTabla:{}};}
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
// Cuántos de los últimos 6 cierres faltó cada producto (por nombre) y su neto en cada uno.
function crepite(G){const {st,B}=G,P=B.P,clave=JSON.stringify(['repite',st.c,st.fams,st.areas,st.fam,st.area]);
  if(B.cache.has(clave))return B.cache.get(clave);
  const idx=P.sesiones.map((s,i)=>i).filter(i=>i<=st.c&&P.sesiones[i].tipo==='cierre').slice(-6),foco=cfoco(st),n=new Map(),h=new Map(),hq=new Map();
  idx.forEach((i,j)=>{for(const [prod,g] of cgroup(cfiltrar(B.cortes[i]||[],st).filter(foco),r=>r.prod.trim())){const v=csum(g,'val');
    if(v<-1)n.set(prod,(n.get(prod)||0)+1);
    if(!h.has(prod)){h.set(prod,idx.map(()=>null));hq.set(prod,idx.map(()=>null));}h.get(prod)[j]=v;
    // La cantidad sólo si es una sola unidad: no se suman kilos con litros.
    if(new Set(g.map(r=>r.um)).size===1)hq.get(prod)[j]={q:csum(g,'dif'),um:g[0].um};}});
  const out={n,h,hq,de:idx.length,nombres:idx.map(i=>P.sesiones[i].corto)};B.cache.set(clave,out);return out;
}
const cbtn=(act,v,txt,sel=false,tip='',cls='')=>`<button type="button" data-act="${act}" data-v="${cesc(v)}" class="${sel?'selected ':''}${cls}" title="${cesc(tip)}" aria-pressed="${sel}">${cesc(txt)}</button>`;
const cseg=(act,ops,sel,label)=>`<span class="ajc-seg" role="group" aria-label="${cesc(label)}">${ops.map(([v,t])=>cbtn(act,v,t,v===sel)).join('')}</span>`;
// Cápsula (#812): un ajuste —cómo se cuenta o se muestra— se pliega y muestra sólo lo
// elegido; el cursor o el foco lo despliegan hacia abajo. Las pestañas, no: llevan a otra
// cosa y van a la vista (#795).
const ccap=(act,ops,sel,label)=>{const el=ops.find(([v])=>v===sel)||ops[0];return `<span class="ajc-cap" data-cap="${act}" role="group" aria-label="${cesc(label)}"><button type="button" class="ajc-cap-b" aria-haspopup="true" title="${cesc(label)}">${cesc(el[1])}<i aria-hidden="true">▾</i></button><span class="ajc-cap-op">${ops.map(([v,t])=>cbtn(act,v,t,v===sel)).join('')}</span></span>`;};
const cselect=(act,ops,sel,label)=>`<label>${cesc(label)} <select data-change="${act}" aria-label="${cesc(label)}">${ops.map(([v,t])=>`<option value="${cesc(v)}" ${v===sel?'selected':''}>${cesc(t)}</option>`).join('')}</select></label>`;
const ckpi=(label,value,sub='',tip='',cls='',extra='')=>`<div class="ajc-kpi ${extra}" title="${cesc(tip)}"><span>${cesc(label)}</span><b class="${cls}">${cesc(value)}</b><small>${cesc(sub)}</small></div>`;
const cclase=v=>v<-.5?'neg':v>.5?'pos':'';
const ctipo=(B,rep,r)=>{const n=rep.n.get(r.prod)||0;return B.oper.has(r.fam)?'oper':n>=3?'rein':n<=1?'una':'otros';};
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
function cstockprods(G,D){const {st}=D;
  const ps=[...cgroup(D.rs,r=>JSON.stringify([r.id,r.um])).values()].map(g=>({...g[0],fis:csum(g,'fis'),stock:csum(g,'stock'),areas:new Set(g.map(r=>r.area)).size})).sort((a,b)=>b.stock-a.stock);
  G.exportar={nombre:'Stock de productos',cabeza:['Código','Producto','Unidad','Conteo','Stock valorizado S/'],filas:ps.map(r=>[r.cod,r.prod,r.um,r.fis,r.stock]),decimales:6};
  return `<h4 class="ajc-h">Productos por stock valorizado</h4>${ctabla(['Producto','Unidad','Contado','Stock','Áreas'],ps.slice(0,st.limite).map(r=>`<tr><td>${cesc(r.prod)}<small>${cesc(r.cod)}</small></td><td>${cesc(r.um)}</td><td>${cn(r.fis,3)}</td><td>${csol(r.stock)}</td><td>${r.areas}</td></tr>`))}`;
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
      <p class="ajc-pie">Un punto: sin registros en esa área y familia; un 0, registros que suman cero. Un clic en una celda, una familia o un área lleva a «Productos» con ese foco.</p>${st.medida==='stock'?cstockprods(G,D):''}`;}
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
  return `<div class="ajc-graf" data-k="graf" aria-label="Faltó y sobró de los últimos 12 cierres"></div>`;
}
const cleyenda=D=>`<div class="ajc-ley"><span><i class="pos"></i>Sobró</span><span><i class="neg"></i>Faltó</span><span><i class="pto"></i>Neto</span>${D.hayOper?'<span><i class="op"></i>Insumos de operación</span>':''}</div>`;
function cgrafico(G){const caja=G.root.querySelector('[data-k=graf]');if(!caja)return;
  const W=Math.round(caja.clientWidth),H=Math.round(caja.clientHeight)||220;if(!W)return;
  const S=cserie(G).cierres,n=S.length;if(!n){caja.innerHTML='<p class="ajc-pie">Sin cierres para estos filtros.</p>';return;}
  const vals=S.flatMap(r=>[r.c.sobro,r.c.falto,r.o.saldo,0]),hi=Math.max(...vals),lo=Math.min(...vals),T=22,B=30,an=(W-8)/n;
  const y=v=>T+(hi-v)/((hi-lo)||1)*(H-T-B);
  let s=`<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Faltó y sobró de los últimos ${n} cierres">`;
  S.forEach((r,j)=>{const x=4+an*j,w=an*.34,x1=x+an*.14,x2=x1+w+2,[m,a]=r.s.corto.replace(/^Cierre /,'').split(' ');
    if(r.i===G.st.c)s+=`<rect class="sel" x="${x+1}" y="${T-6}" width="${an-2}" height="${H-T-B+10}" rx="6"/><text class="etq" x="${x+an/2}" y="${Math.max(11,y(r.c.sobro)-5)}" text-anchor="middle">${cesc(csol(r.c.saldo))}</text>`;
    s+=`<rect class="pos" x="${x1}" y="${y(r.c.sobro)}" width="${w}" height="${Math.max(1,y(0)-y(r.c.sobro))}" rx="2"/><rect class="neg" x="${x1}" y="${y(0)}" width="${w}" height="${Math.max(1,y(r.c.falto)-y(0))}" rx="2"/>`;
    if(Math.abs(r.o.saldo)>.5)s+=`<rect class="op" x="${x2}" y="${Math.min(y(0),y(r.o.saldo))}" width="${w*.7}" height="${Math.max(1,Math.abs(y(r.o.saldo)-y(0)))}" rx="2"/>`;
    s+=`<circle class="pto" cx="${x1+w/2}" cy="${y(r.c.saldo)}" r="3.2"/><text x="${x+an/2}" y="${H-16}" text-anchor="middle">${cesc(m||'')}</text><text x="${x+an/2}" y="${H-4}" text-anchor="middle">${cesc((a||'').slice(2))}</text>`;
    s+=`<rect class="toque" data-act="corte" data-v="${r.i}" data-j="${j}" x="${x}" y="0" width="${an}" height="${H}"><title>${cesc(`${r.s.corto} · ${r.s.etiqueta_anio}\nFaltó ${csol(r.c.falto)} · sobró ${csol(r.c.sobro)} · neto ${csol(r.c.saldo)}\n${r.areas} áreas, ${cn(r.c.lineas)} líneas${Math.abs(r.o.saldo)>.5?`\nOperación ${csol(r.o.saldo)}`:''}`)}</title></rect>`;});
  caja.innerHTML=s+`<line class="cero" x1="4" x2="${W-4}" y1="${y(0)}" y2="${y(0)}"/></svg>`;
}
// ── Arriba: el cierre, los indicadores y las pestañas ────────────────────
function cfilacorte(G,D){
  const {P}=G.B,{st}=D,base=G.B.cortes[st.c]||[],areas=[...new Set(base.filter(r=>r.val!==0&&r.area&&r.area!=='---').map(r=>r.area))].sort();
  const ses=P.sesiones[st.c],cob=new Set(D.scope.filter(r=>r.flags&1).map(r=>r.area)).size,ops=P.sesiones.map((s,i)=>[i,`${s.corto} · ${s.etiqueta_anio}`]);
  const foco=[st.fam&&cnom(st.fam),st.area&&cnom(st.area)].filter(Boolean).join(' · ');
  const nota=ses?`${ses.nombre} · contado el ${ses.etiqueta_anio} · ${ses.n_dias} ${ses.n_dias===1?'día':'días'} · ${ses.juntas} ${ses.juntas===1?'conteo':'conteos'} · ${cn(D.rs.length)} registros · ${cn(cob)} áreas con stock${P.sin_fecha?` · ${cn(P.sin_fecha)} líneas sin fecha excluidas`:''}`:'Sin sesiones disponibles';
  const tabs=`<nav class="ajc-tabs" role="tablist">${ctabs.map(([t,n])=>`<button type="button" role="tab" data-act="tab" data-v="${t}" aria-selected="${st.tab===t}" class="${st.tab===t?'selected':''}">${n}</button>`).join('')}</nav>`;
  return `<div class="ajc-fila ajc-f2 ajc-fnav">${tabs}<span class="ajc-push"></span><span class="ajc-ses">${cbtn('mover',-1,'‹',false,'Corte anterior','ajc-flecha')}${cselect('corte',ops,st.c,'Corte')}${cbtn('mover',1,'›',false,'Corte siguiente','ajc-flecha')}</span>
    ${ses?ckpicap(G,D,nota):'<span class="ajc-note">Sin sesiones disponibles</span>'}${cfiltros(G,areas)}${foco?`<span class="ajc-chip">${cesc(foco)}${cbtn('limpiar','','✕',false,'Quitar el foco')}</span>`:''}</div>`;
}
// Áreas y Familias en UN botón (#815): valen para toda la vista, y juntos ocupan la mitad.
function cfiltros(G,areas){const {P}=G.B,st=G.st,n=(st.areas.length?1:0)+(st.fams.length?1:0);
  const sec=(k,label,opciones)=>`<div class="ajc-fsec"><div class="ajc-fsec-t"><b>${cesc(label)}</b>${cbtn('todos',k,'Todas')}${k==='fams'?cbtn('inicial',k,'Las cinco de antes','','Alimentos, bebidas, vinos y envases: el filtro con que abría hasta la regla #748'):''}</div>${opciones.map(v=>`<label><input type="checkbox" data-filter="${k}" value="${cesc(v)}" ${st[k].includes(v)?'checked':''}>${cesc(cnom(v)||'Sin nombre')}</label>`).join('')}</div>`;
  const tip=[st.areas.length?`Áreas: ${st.areas.map(cnom).join(', ')}`:'',st.fams.length?`Familias: ${st.fams.map(cnom).join(', ')}`:''].filter(Boolean).join(' · ')||'Áreas y familias: todas';
  return `<details class="ajc-filter ajc-filtros"><summary title="${cesc(tip)}">Filtros${n?` · ${n}`:''}</summary><div class="ajc-options"><small>Valen para toda la vista.</small>${sec('areas','Áreas',areas)}${sec('fams','Familias',P.dic.fam)}</div></details>`;
}
// Los números del cierre en una CÁPSULA (#814, a pedido: Ajuste es para analizar). Muestra
// uno —el elegido— y al pasar el cursor despliega los cuatro con su explicación y, debajo,
// la lectura del cierre, que dejó de ocupar un panel al costado. Son del cierre entero: no
// siguen a la búsqueda, y por eso lo dicen («del cierre»).
function ckpicap(G,D,nota){const {mc,mo}=D,st=G.st,sel=st.kpiv||'saldo';
  const it=[['falto','Faltó',mc.falto,'neg',D.hayOper?'sin los insumos de operación':'suma de las líneas negativas',''],
    ['sobro','Sobró',mc.sobro,'pos','suele ser stock que estaba en negativo',''],
    ['saldo','Neto',mc.saldo,cclase(mc.saldo),`sin compensar ${csol(mc.total)} · ${cpct(mc.tol,mc.lineas)} dentro de ±S/ 5`,''],
    D.hayOper?['oper','Operación, aparte',mo.saldo,'op','ninguna receta los descarga',' ajc-aparte']:['total','Sin compensar',mc.total,'','faltó + sobró','']];
  const el=it.find(x=>x[0]===sel)||it[2];
  const op=it.map(([id,r,v,cls,sub,ex])=>`<button type="button" data-act="kpiv" data-v="${id}" class="ajc-kci${id===el[0]?' selected':''}${ex}" aria-pressed="${id===el[0]}"><span><small>${cesc(r)}</small><b class="${cls}">${csol(v)}</b></span><small>${cesc(sub)}</small></button>`).join('');
  return `<span class="ajc-cap ajc-kcap" data-cap="kpi" role="group" aria-label="Números del cierre"><button type="button" class="ajc-cap-b ajc-kcap-b" aria-haspopup="true"><small>${cesc(el[1].split(',')[0])} del cierre</small><b class="${el[3]}">${csol(el[2])}</b><i aria-hidden="true">▾</i></button><span class="ajc-cap-op ajc-kcap-op">${op}<span class="ajc-kcap-l">${clectura(G,D)}<small class="ajc-kcap-n">${cesc(nota)}</small></span></span></span>`;
}
// ── Nivel 3: la barra de la lista. Todo lo que cambia la lista, junto a la lista (#815):
//    los contadores, la búsqueda como pastilla, cómo ver, el buscador y Excel. ───────────
// Una cápsula con varias secciones: «Lado a lado · por monto» es UN ajuste de cómo se ve.
const ccapm=(id,secs,label)=>`<span class="ajc-cap" data-cap="${id}" role="group" aria-label="${cesc(label)}"><button type="button" class="ajc-cap-b" aria-haspopup="true" title="${cesc(label)}">${cesc(secs.map(([, , ops,sel,corto],i)=>i&&sel===ops[0][0]?'':(corto||ops.find(([v])=>v===sel)||ops[0])[1]).filter(Boolean).join(' · '))}<i aria-hidden="true">▾</i></button><span class="ajc-cap-op">${secs.map(([tit,act,ops,sel])=>`<small class="ajc-cap-t">${cesc(tit)}</small>${ops.map(([v,t])=>cbtn(act,v,t,v===sel)).join('')}`).join('')}</span></span>`;
function cbarra(G,D,izq=''){const {st}=D,X=G.lista;
  let caps='',buscar=`<input class="ajc-search" type="search" aria-label="Buscar producto o área" placeholder="Buscar…" value="${cesc(st.q)}" data-input="buscar">`;
  if(st.tab==='listas'){const NOMBRE={ambos:'Lado a lado',f:'Faltantes',s:'Sobrantes',tabla:'Consolidado'};
    const lado=['Qué lista','lado',[['ambos','Lado a lado'],['f',`Faltantes ${csol(X.tf)}`],['s',`Sobrantes ${csol(X.ts)}`],['tabla','Consolidado']],st.lado,[st.lado,NOMBRE[st.lado]]];
    caps=ccapm('lado',[lado,st.lado==='tabla'?['Agrupar','cagr',[['','Sin agrupar'],['fam','Por familia'],['sub','Por subfamilia'],['area','Por área']],st.cagr||'']:['Orden','orden',[['monto','Por monto'],['pareto','Pareto']],st.orden]],'Cómo ver la lista');}
  else if(st.tab==='lineas')caps=ccap('juntas',[['si','Áreas juntas'],['no','Áreas separadas']],st.juntas?'si':'no','Áreas');
  else if(st.tab==='familias'){caps=`${ccap('vf',[['lista','Familias'],['areas','Áreas'],['cruce','Cruce']],st.vf,'Cómo ver')}${st.vf==='cruce'&&G.B.P.hay.stock?ccap('medida',[['val','Ajuste'],['stock','Stock']],st.medida,'Qué mide el cruce'):''}`;buscar='';}
  else if(st.tab==='cierres'){caps=ccap('vg',[['graf','Gráfico'],['tabla','Tabla con parciales']],st.vg,'Gráfico o tabla');buscar=st.vg==='graf'?cleyenda(D):'';}
  // La búsqueda es una pastilla más: recorta las listas y los contadores, no los números del cierre.
  const qp=st.q&&st.tab==='listas'?`<button type="button" class="ajc-qp" data-act="quitarq" title="La búsqueda recorta las listas y los contadores; los números del cierre no cambian. Clic para quitarla.">«${cesc(st.q)}» ✕</button>`:'';
  const excel=`<details class="ajc-filter ajc-excel"><summary>Excel</summary><div class="ajc-options">${cbtn('excel','resumen','El resumen: familias y cortes')}${cbtn('excel','detalle','Lo que se ve en esta pestaña')}</div></details>`;
  const sw=st.tab==='listas'&&st.lado!=='tabla'?`<button type="button" class="ajc-sw${st.det6?' on':''}" data-act="det6" role="switch" aria-checked="${!!st.det6}" title="Mostrar los últimos ${X.rep.de} cierres de cada producto y cuántas veces faltó"><i aria-hidden="true"></i>${X.rep.de} cierres</button>`:'';
  return `<div class="ajc-barra">${qp}${izq}<span class="ajc-push"></span>${sw}${caps}${buscar}${excel}</div>`;
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
function cdatoslista(G,D){const {st}=D,{B}=G,rep=crepite(G);
  const todas=clistas(D.scope,true),L=todas.filter(r=>cbuscar(r,st.q)),neg=r=>r.val<0,pos=r=>r.val>0;
  const cl={oper:{n:0,v:0},rein:{n:0,v:0},una:{n:0,v:0},otros:{n:0,v:0}};
  for(const r of L.filter(neg)){const c=cl[ctipo(B,rep,r)];c.n++;c.v+=r.val;}
  const cls={oper:{n:0,v:0},rein:{n:0,v:0},una:{n:0,v:0},otros:{n:0,v:0}};
  for(const r of todas.filter(neg)){const c=cls[ctipo(B,rep,r)];c.n++;c.v+=r.val;}
  // #819: sin los contadores que recortaban la lista por tipo (Se repiten, Operación,
  // Nuevos, Falta y sobra): «Todo» repetía el total del pie y los tipos se leen en la
  // cápsula de los números. Las listas son el faltante y el sobrante enteros.
  const f=L.filter(neg),s=L.filter(pos);
  const par=st.orden==='pareto'?{f:new Map(cpareto(D.scope,'Faltantes').map(r=>[r.prod.trim(),r])),s:new Map(cpareto(D.scope,'Sobrantes').map(r=>[r.prod.trim(),r]))}:null;
  if(par){f.sort((a,b)=>(par.f.get(a.prod)?.acum??999)-(par.f.get(b.prod)?.acum??999));s.sort((a,b)=>(par.s.get(a.prod)?.acum??999)-(par.s.get(b.prod)?.acum??999));}
  return {todas,L,f,s,rep,cl,cls,par,tf:csum(L.filter(neg),'val'),ts:csum(L.filter(pos),'val'),tfTodo:csum(todas.filter(neg),'val')};
}
function cbarritas(h){const mx=Math.max(1,...h.map(v=>Math.abs(v||0)));
  return h.map(v=>{const a=Math.max(v==null?0:1.5,Math.abs(v||0)/mx*10);return `<span class="ajc-b"><i class="${v==null?'':v<-1?'neg':v>1?'pos':'cero'}" style="top:${(v||0)<0?11:11-a}px;height:${a}px"></i></span>`;}).join('');}
function cfilaprod(G,X,r,l,una){const {st}=G,det=!!st.det6,key=`${l}|${r.prod}`,n=X.rep.n.get(r.prod)||0,pp=X.par&&X.par[l].get(r.prod);
  const qty=r.dif==null?'varias unidades':`${ccant(r.dif)} ${r.um}`,qtyC=r.dif==null?qty:`${ccant(r.dif)} ${cum(r.um)}`;
  const medio=X.par?`<span class="ajc-acum" title="El % de este producto sobre el neto de su lado, y el acumulado">${pp?`${cp(pp.pct)} · acum. ${cp(pp.acum)}`:'—'}</span>`:`<span class="ajc-6" title="Los últimos ${X.rep.de} cierres">${cbarritas(X.rep.h.get(r.prod)||[])}</span>`;
  return `<button type="button" class="ajc-p${st.sel===key?' on':''}" data-act="prod" data-v="${cesc(key)}" aria-pressed="${st.sel===key}" title="${cesc(`${r.cod?r.cod+' · ':''}${r.prod} · ${cnom(r.area)} · ${qty}`)}"><span class="ajc-pc">${r.cod?ccod(r.cod):'—'}</span><span class="ajc-pnom">${cesc(r.prod)}</span>${una?`<span class="ajc-pa">${cesc(cnom(r.area))}</span>`:''}<span class="ajc-pq">${cesc(qtyC)}</span><b>${csol(r.val)}</b>${det||X.par?medio:''}${det?`<span class="ajc-rep${l==='f'&&n>=3?' fuerte':''}">${l==='f'?`${n} de ${X.rep.de}`:''}</span>`:''}</button>`;
}
// «Consolidado» (#808, a pedido): todas las líneas del cierre, producto por área, con
// sus cantidades y valores, como la tabla de «Detalle docs.» de Compras. Agrupa por
// familia, subfamilia o área con subtotales; se ordena por cualquier columna.
// [clave, nombre (Excel y title), tipo, rótulo corto en pantalla] — #810: los valores con
// rótulos cortos para que la tabla entre sin deslizarse de lado.
const CCOLS=[['cod','Código','c','Código'],['fam','Familia','t','Familia'],['sub','Subfamilia','t','Subfamilia'],['prod','Producto','t','Producto'],['um','Unidad','t','Unid.'],
  ['precio','Precio promedio (S/)','p','Precio'],['sis','Stock al cierre (sistema)','q','Sistema'],['dif','Ajuste (cantidad)','q','Ajuste'],['fis','Stock declarado (contado)','q','Contado'],['val','Ajuste valorizado (S/)','v','Ajuste S/'],['stock','Valorizado total (S/)','v','Total S/']];
const CNUM=['sis','dif','fis','val','stock'];
const cprecio=r=>Math.abs(r.dif)>CEPS?r.val/r.dif:Math.abs(r.fis)>CEPS?r.stock/r.fis:null;
// Un renglón por PRODUCTO (#811, a pedido: «el área no debe estar como columna»). Con más
// de un área, ▸ abre sus áreas debajo, cada una con sus cifras. El Excel sigue por línea.
function cprodcons(g){const r0=g[0],o={key:JSON.stringify([r0.cod||r0.prod,r0.um]),cod:r0.cod,fam:r0.fam,sub:r0.sub,prod:r0.prod,um:r0.um,lineas:g,areas:[...new Set(g.map(r=>r.area))]};
  for(const k of CNUM)o[k]=csum(g,k);o.precio=cprecio(o);return o;}
function cconsolidado(G,D){const {st}=D,q=st.q||'';
  const rs=D.scope.filter(r=>cbuscar(r,q)).map(r=>({...r,precio:cprecio(r)}));
  const o=st.corden||{k:'val',d:1},sig=o.d,ab=new Set(st.cabre||[]);
  const ord=(a,b)=>{const x=a[o.k],y=b[o.k];if(typeof x==='string'||typeof y==='string')return String(x??'').localeCompare(String(y??''),'es')*sig;return((x??-Infinity)-(y??-Infinity))*sig;};
  const prods=g=>[...cgroup(g,r=>JSON.stringify([r.cod||r.prod,r.um])).values()].map(cprodcons).sort(ord);
  // Familia y subfamilia como nombre, no en mayúsculas (#810); el producto, como viene.
  const fmt=(t,v,k)=>t==='c'?(v?ccod(v):'—'):t==='t'?cesc(v==null||v===''?'—':['fam','sub'].includes(k)?cnom(v):k==='um'?cum(v):v):t==='v'?cn(v,0):t==='p'?(v==null?'—':cn(v,2)):ccant(v);
  const cls=(k,v)=>k==='val'||k==='dif'?(v<-CEPS?' neg':v>CEPS?' pos':''):'';
  const celdas=(r,prod)=>CCOLS.map(([k,,t])=>`<td class="ck-${k} ${t==='t'?'':t==='c'?'ajc-cc':'n'}${cls(k,r[k])}" title="${t==='t'&&k!=='prod'?cesc(r[k]??''):''}">${k==='prod'?prod:fmt(t,r[k],k)}</td>`).join('');
  const filaProd=p=>{const varias=p.areas.length>1,abierto=varias&&ab.has(p.key);
    const nom=`${varias?`<span class="ajc-tg">${abierto?'▾':'▸'}</span>`:'<span class="ajc-tg"></span>'}<span class="ajc-cn" title="${cesc(p.prod)}">${cesc(p.prod)}</span><small class="ajc-car">${varias?`${p.areas.length} áreas`:cesc(cnom(p.areas[0]))}</small>`;
    let h=`<tr class="ajc-pr${varias?' abre':''}${abierto?' on':''}"${varias?` data-act="cabre" data-v="${cesc(p.key)}"`:''}>${celdas(p,nom)}</tr>`;
    if(abierto)for(const r of [...p.lineas].sort((a,b)=>a.val-b.val))h+=`<tr class="ajc-ar">${celdas({...r,cod:'',fam:'',sub:''},`<span class="ajc-tg"></span><span class="ajc-cn">${cesc(cnom(r.area))}</span>`).replace(/<td class="ck-(cod|fam|sub) [^"]*"[^>]*>—<\/td>/g,'<td></td>')}</tr>`;
    return h;};
  const tot=(nom,g,np)=>{const t={cod:'',fam:nom,sub:'',um:'',precio:null,sis:null,dif:null,fis:null,val:csum(g,'val'),stock:csum(g,'stock')};return `<tr class="ajc-sub">${celdas(t,`${cn(np)} productos`)}</tr>`;};
  const agr=st.cagr||'';let cuerpo='',n=0,nprod=0;
  if(agr){const gs=[...cgroup(rs,r=>r[agr]||'—')].sort((a,b)=>csum(a[1],'val')-csum(b[1],'val'));
    for(const [k,g] of gs){const ps=prods(g);nprod+=ps.length;if(n>=st.limite)continue;cuerpo+=tot(agr==='area'?cnom(k):cnom(k),g,ps.length);for(const p of ps){if(n++>=st.limite)break;cuerpo+=filaProd(p);}}}
  else{const ps=prods(rs);nprod=ps.length;cuerpo=ps.slice(0,st.limite).map(filaProd).join('');}
  G.nfilas=nprod;
  const LX=[...CCOLS.slice(0,5),['area','Área','t'],...CCOLS.slice(5)];
  G.exportar={nombre:'Consolidado',cabeza:LX.map(c=>c[1]),filas:rs.map(r=>LX.map(([k])=>r[k]??'')),decimales:6};
  const mk=k=>o.k===k?(o.d>0?' ↑':' ↓'):'';
  const th=CCOLS.map(([k,t,ti,c])=>`<th class="${ti==='t'||ti==='c'?'':'n'}" title="${cesc(t)}">${cbtn('corden',k,`${c}${mk(k)}`)}</th>`).join('');
  const T={val:csum(rs,'val'),stock:csum(rs,'stock')};
  const pie=`<tr class="ajc-tot"><td colspan="5">Total · ${cn(nprod)} productos · ${cn(rs.length)} líneas</td><td></td><td></td><td></td><td></td><td class="n${cls('val',T.val)}">${csol(T.val)}</td><td class="n">${csol(T.stock)}</td></tr>`;
  G.sub=`${cn(nprod)} productos · ajuste ${csol(T.val)} · valorizado ${csol(T.stock)}${nprod>st.limite?` · se ven ${cn(Math.min(st.limite,nprod))}`:''} · ▸ abre las áreas`;
  return `<div class="ajc-cons"><div class="ajc-scroll"><table class="ajc-ctab"><thead><tr>${th}</tr></thead><tbody>${pie}${cuerpo}</tbody></table></div></div>`;
}
function clistashtml(G,D){const {st}=D,X=G.lista,{B}=G;
  if(st.lado==='tabla')return `<div class="ajc-zl">${cbarra(G,D)}${cconsolidado(G,D)}</div>`;
  G.exportar={nombre:'Listas',cabeza:cprodheads,filas:X.L.map(cprodvals),decimales:6};
  // #818, con la forma de la tabla de Compras › Período: UN renglón de encabezado (el lado,
  // con su punto de color, en lugar de «Producto»), los montos en tinta normal —el lado ya
  // lo dicen el punto y el «−»— y el total al pie, que es lo único con color.
  const extra=(l,cab)=>`${st.det6||X.par?`<span class="${X.par?'ajc-acum':'ajc-6'}">${cab?(X.par?'Pareto':`${X.rep.de} cierres`):''}</span>`:''}${st.det6?`<span class="ajc-rep">${cab&&l==='f'?'Faltó':''}</span>`:''}`;
  const cab=(una,l)=>`<div class="ajc-p cab"><span class="ajc-pc">Código</span><span class="ajc-pnom"><i class="ajc-dot ${l==='f'?'neg':'pos'}"></i>${l==='f'?'Faltantes':'Sobrantes'}</span>${una?'<span class="ajc-pa">Área</span>':''}<span class="ajc-pq">Cantidad</span><b>Ajuste</b>${extra(l,true)}</div>`;
  const filas=(ps,l,una)=>ps.slice(0,st.limite).map(r=>cfilaprod(G,X,r,l,una)).join('')||'<p class="ajc-pie">Ninguno con estos filtros.</p>';
  // La suma sale de TODAS las filas de la lista, no de las dibujadas (#769), y sigue al
  // buscador y al contador elegido.
  const pie=(una,l,ps)=>`<div class="ajc-p ajc-ptot"><span class="ajc-ptl">Total · ${cnn(ps.length,'producto')}</span>${una?'<span class="ajc-pa"></span>':''}<span class="ajc-pq"></span><b class="${l==='f'?'neg':'pos'}">${csol(csum(ps,'val'))}</b>${extra(l,false)}</div>`;
  const col=(l,ps,una,cls)=>`<section class="ajc-col${cls?` ${cls}`:''}"><div class="ajc-scroll">${cab(una,l)}${filas(ps,l,una)}</div>${pie(una,l,ps)}</section>`;
  const cuerpo=st.lado==='ambos'?col('f',X.f,false,'neg')+col('s',X.s,false,'pos')
    :col(st.lado,st.lado==='s'?X.s:X.f,true,'');
  G.nfilas=Math.max(st.lado==='s'?0:X.f.length,st.lado==='f'?0:X.s.length);
  const n80=ps=>{const vs=ps.map(r=>Math.abs(r.val)).sort((a,b)=>b-a),t=vs.reduce((a,v)=>a+v,0);let acc=0,n=0;for(const v of vs){n++;acc+=v;if(acc/t>=.8-CEPS)break;}return {n,de:vs.length};};
  const a=n80(X.f),b=n80(X.s),comp=cmetricas(D.scope,B.P.hay).falto-X.tfTodo;
  const dF=`Faltantes: ${a.n} de ${a.de} explican el 80 %`,dS=`sobrantes: ${b.n} de ${b.de}`,dC=Math.abs(comp)>.5?` · ${csol(Math.abs(comp))} del faltante se compensó con sobrantes de otra área`:'';
  G.sub=st.lado==='s'?`Sobrantes: ${b.n} de ${b.de} explican el 80 %`:st.lado==='f'?`${dF}${dC}`:`${dF} · ${dS}${dC}`;
  return `<div class="ajc-zl">${cbarra(G,D)}<div class="ajc-lists ${st.lado==='ambos'?'dos':'una'}${X.par?' pareto':''}${st.det6?'':' sin6'}">${cuerpo}</div></div>`;
}
// ── La ficha del producto, en una ventana (#814) ─────────────────────────
const CVAC=new Set('con sin para del los las und unid unidad unidades kg kgs kilo kilos grs gramos ml lts litro litros por caja cajas bolsa paquete pqt botella bot frasco sac eirl produccion calientes frios pasteleria parrilla parrillas cocina arroces bar limpio limpia'.split(' '));
const CGEN=new Set('vino vinos tinto blanco rosado salsa chocolate pisco cerveza aceite queso harina azucar agua leche crema pasta papa pan sal jugo fruta carne pollo pescado whisky vodka ron gin licor huevo huevos verde rojo roja amarillo negro negra fresco fresca organico extra entero entera premium'.split(' '));
function cpalabras(t){t=String(t||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\([^)]*\)/g,' ');
  return [new Set((t.match(/[a-z]+/g)||[]).filter(w=>w.length>=3&&!CVAC.has(w))),new Set((t.match(/\d+/g)||[]).filter(x=>x.length>=2))];}
const cmisma=(a,b)=>{if(a===b)return true;const [c,l]=a.length<=b.length?[a,b]:[b,a];return c.length>=5&&l.startsWith(c)&&l.length-c.length<=3;};
function cparecido([pw,pn],[dw,dn]){if(!pw.size)return null;if(pn.size&&dn.size&&![...pn].some(x=>dn.has(x)))return null;
  const hay=[...pw].filter(w=>[...dw].some(t=>cmisma(w,t)));
  if(pw.size===1){const w=[...pw][0];if(!hay.length||w.length<6||![...dw].every(t=>CGEN.has(t)||cmisma(t,w)))return null;return 1;}
  if(hay.length<2||hay.length/pw.size<.75||hay.every(w=>CGEN.has(w)))return null;return hay.length/pw.size;}
const cparecidos=(prod,otros)=>{const a=cpalabras(prod);return otros.filter(x=>x.prod!==prod).filter(x=>{const b=cpalabras(x.prod);return cparecido(a,b)!=null||cparecido(b,a)!=null;}).sort((x,y)=>Math.abs(y.val)-Math.abs(x.val)).slice(0,6);};
const cnavlista=(X,l)=>l==='f'?X.f:X.s;
// Por área: lo que decía el sistema (el conteo anterior más lo que entró, menos lo que salió),
// lo que se contó y el ajuste que lleva el stock a lo contado. Sin sumar unidades distintas.
function ccuenta(D,prod){const g=[...cgroup(D.scope.filter(r=>r.prod.trim()===prod),r=>JSON.stringify([r.area,r.um])).values()].map(x=>({area:x[0].area,um:x[0].um,sis:csum(x,'sis'),fis:csum(x,'fis'),dif:csum(x,'dif'),val:csum(x,'val')})).filter(a=>Math.abs(a.val)>.005||Math.abs(a.dif)>1e-9||Math.abs(a.sis)>1e-9).sort((a,b)=>Math.abs(b.val)-Math.abs(a.val));
  const q=(v,um)=>`${ccant(v)} <small>${cesc(um)}</small>`,una=new Set(g.map(a=>a.um)).size===1;
  const fila=(a,tot)=>`<span class="ar${tot?' tot':''}">${tot?'Total':cesc(cnom(a.area))}</span><span class="n">${q(a.sis,a.um)}</span><span class="n">${q(a.fis,a.um)}</span><span class="n ${cclase(a.dif)}">${q(a.dif,a.um)}</span><b class="n ${cclase(a.val)}">${csol(a.val)}</b>`;
  const T=g.length>1&&una?{area:'',um:g[0].um,sis:csum(g,'sis'),fis:csum(g,'fis'),dif:csum(g,'dif'),val:csum(g,'val')}:null;
  return `<div class="ajc-areas-de ajc-cuenta"><span class="cab" title="Lo que quedaba según el sistema al cierre: el conteo anterior más lo que entró, menos lo que salió">Área</span><span class="cab n" title="Lo que quedaba según el sistema al cierre: el conteo anterior más lo que entró, menos lo que salió">Decía el sistema</span><span class="cab n" title="Lo que se contó: es lo que queda en el inventario">Se contó</span><span class="cab n" title="Lo contado menos lo que decía el sistema">Ajuste</span><span class="cab n">Ajuste S/</span>${g.map(a=>fila(a,false)).join('')}${T?fila(T,true):''}</div>`;}
// ── Al costado: la lectura del cierre o la ficha del producto ────────────
function cficha(G,D){const {st}=D,X=G.lista,{B}=G;if(st.tab!=='listas'||!st.sel)return '';
  const i=st.sel.indexOf('|'),l=st.sel.slice(0,i),prod=st.sel.slice(i+1),r=X.todas.find(x=>x.prod===prod);if(!r||(l==='f'?r.val>=0:r.val<=0))return '';
  const areas=careasPareto(D.scope.filter(x=>x.prod.trim()===prod).map(x=>({...x,prod})),prod).filter(a=>Math.abs(a.val)>.005||Math.abs(a.dif)>1e-9);
  const otra=areas.filter(a=>l==='f'?a.val>.5:a.val<-.5).reduce((s,a)=>s+a.val,0),n=X.rep.n.get(prod)||0,de=X.rep.de,destino=cporque(D,prod,l),h=X.rep.h.get(prod)||[];
  const lectura=B.oper.has(r.fam)?'Insumo de operación: ninguna receta lo descarga, y su consumo aparece recién al contar.'
    :l==='s'?'Un sobrante suele ser stock que estaba en negativo, no mercadería que apareció.'
    :n>=3?`Faltó en ${n} de los últimos ${de} cierres: apunta a un proceso más que a un descuido del mes.`
    :n<=1?`No faltó en ninguno de los otros ${Math.max(0,de-1)} cierres: es lo nuevo de este cierre.`:`Faltó en ${n} de los últimos ${de} cierres.`;
  const alto=Math.max(0,...h.map(v=>v||0)),bajo=Math.min(0,...h.map(v=>v||0)),rango=(alto-bajo)||1,eje=alto/rango*100,pp=X.par&&X.par[l].get(prod);
  const mes=s=>{const [m,a]=String(s).replace(/^Cierre /,'').split(' ');return `${m}${a?` ${a.slice(-2)}`:''}`;};
  const barras=h.map((v,j)=>{const a=Math.abs(v||0)/rango*100;return `<span title="${cesc(`${X.rep.nombres[j]}: ${v==null?'sin registro':csol(v)}`)}"><i class="${v==null?'':v<0?'neg':'pos'}" style="top:${(v||0)<0?eje:eje-a}%;height:${v==null?0:Math.max(1.5,a)}%"></i></span>`;}).join('');
  // El monto y la cantidad de cada cierre, sobre su barra (#814, a pedido).
  const hq=X.rep.hq?.get(prod)||[],vals=h.map((v,j)=>`<span><b class="${v==null?'':cclase(v)}">${v==null?'—':csol(v)}</b><small>${hq[j]?`${ccant(hq[j].q)} ${cesc(hq[j].um)}`:''}</small></span>`).join('');
  const nav=cnavlista(X,l),pos=nav.findIndex(x=>x.prod===prod),otros=X.todas.filter(x=>l==='f'?x.val>CEPS:x.val<-CEPS),par=cparecidos(prod,otros);
  const parecidos=par.length?`<div class="ajc-fs">${l==='f'?'Sobrantes':'Faltantes'} con nombre parecido</div><div class="ajc-par"><span class="cab">Código</span><span class="cab">Producto</span><span class="cab n">Cantidad</span><span class="cab">Unidad</span><span class="cab n">Valorizado</span>${par.map(x=>`<span class="c">${cesc(x.cod||'—')}</span><span class="p" title="${cesc(x.prod)}">${cesc(x.prod)}</span><span class="n">${x.dif==null?'—':cesc(ccant(x.dif))}</span><span>${cesc(x.dif==null?'varias':x.um)}</span><b class="n ${cclase(x.val)}">${csol(x.val)}</b>`).join('')}</div>`:'';
  return `<div class="ajc-ft"><span>${cesc(r.cod||'')}${r.cod?' · ':''}${cesc(cnom(r.fam))}${r.sub?` › ${cesc(cnom(r.sub))}`:''}</span><span class="ajc-nav">${cbtn('nav',-1,'‹',false,'Producto anterior (←)','ajc-flecha')}<small>${pos>=0?`${cn(pos+1)} de ${cn(nav.length)}`:''}</small>${cbtn('nav',1,'›',false,'Producto siguiente (→)','ajc-flecha')}</span>${cbtn('soltar','','✕ Cerrar',false,'Cerrar (Esc)','ajc-lnk')}</div>
    <h4 class="ajc-fn">${cesc(prod)}</h4><div class="ajc-fv"><b class="${l==='f'?'neg':'pos'}">${csol(r.val)}</b><span>${r.dif==null?'varias unidades':`${cesc(ccant(r.dif))} ${cesc(r.um)}`}</span>${pp?`<small>${cp(pp.pct)} · acum. ${cp(pp.acum)}</small>`:''}</div>
    <p class="ajc-fl">${lectura}${Math.abs(otra)>.5?` ${l==='f'?'Sobró':'Faltó'} ${csol(Math.abs(otra))} en otra área.`:''}</p>
    <div class="ajc-fs">Cómo se llegó a la cantidad</div>${ccuenta(D,prod)}
    <div class="ajc-fs">Últimos ${de} cierres</div><div class="ajc-fvals">${vals}</div><div class="ajc-fh"><i class="eje" style="top:${eje}%"></i>${barras}</div><div class="ajc-fm">${X.rep.nombres.map(n=>`<span>${cesc(mes(n))}</span>`).join('')}</div>
    ${parecidos}${destino?`<button type="button" class="ajc-porque" data-act="porque" data-v="${cesc(JSON.stringify({...destino,lado:l}))}">¿Por qué? Ver en Análisis →</button>`:''}`;
}
function clectura(G,D){const X=G.lista,cl=X.cls,e=cespejos(D.scope),t=X.tfTodo,pc=v=>t?`${Math.round(100*v/t)} %`:'—',rep=X.rep.de;
  // Se leen, no filtran (#819): los contadores que recortaban la lista por tipo se fueron.
  const bl=(tit,txt)=>`<div class="ajc-bl"><b>${cesc(tit)}</b><span>${cesc(txt)}</span></div>`;
  const hay=Math.abs(t)>.5;
  return `<p class="ajc-frase">${cfrase(G,D)}</p>
    ${hay?bl(`Se repite: ${pc(cl.rein.v)}`,`${cn(cl.rein.n)} productos faltaron en 3 o más de los últimos ${rep} cierres (${csol(cl.rein.v)}).`):''}
    ${hay&&cl.oper.n?bl(`Operación: ${csol(cl.oper.v)}`,'Ninguna receta los descarga: su consumo aparece recién al contar.'):''}
    ${hay?bl(`Sólo este cierre: ${pc(cl.una.v)}`,`${cn(cl.una.n)} productos (${csol(cl.una.v)}): por ahí conviene empezar.`):''}
    ${e.n?bl(`Falta acá y sobra allá: ${cn(e.n)}`,`${csol(e.falto)} / ${csol(e.sobro)}.`):''}`;
}
function ctabcomparar(G,D){
  const {st}=D,clave=JSON.stringify([st.c,st.prev,st.fams,st.areas,st.fam,st.area]);
  if(!G.B.compare.has(clave)){if(G.B.compare.size>10)G.B.compare.clear();G.B.compare.set(clave,ccomparar(D.scope,D.prev,D.hist));}
  const comp=G.B.compare.get(clave),counts=Object.fromEntries(cestados.slice(1).map(s=>[s,comp.filter(r=>r.estado===s).length]));
  const rows=cordenar(comp.filter(r=>(st.status==='Todas'||r.estado===st.status)&&cbuscar(r,st.q)),st,'comparar',r=>[r.estado,r.prod,r.area,r.anterior?.observada?r.anterior.val:null,r.actual?.observada?r.actual.val:null,r.delta,r.de?r.con/r.de:null,r.signo||r.motivo]);G.comp=rows;G.nfilas=rows.length;
  const comparables=comp.filter(r=>r.comparable),delta=csum(comparables,'delta'),heads=['Estado','Código','Producto','Familia','Área','Unidad','Anterior neto S/','Actual neto S/','Diferencia anterior cantidad','Diferencia actual cantidad','Anterior absoluto S/','Actual absoluto S/','Cambio absoluto S/','Recurrencias','Cortes con stock','Observación'];
  G.exportar={nombre:'Comparación',cabeza:heads,filas:rows.map(r=>[r.estado,r.cod,r.prod,r.fam,r.area,r.um,r.anterior?.observada?r.anterior.val:null,r.actual?.observada?r.actual.val:null,G.B.P.hay.dif&&r.anterior?.observada?r.anterior.dif:null,G.B.P.hay.dif&&r.actual?.observada?r.actual.dif:null,r.anterior?.observada?r.abs_anterior:null,r.actual?.observada?r.abs_actual:null,r.delta,r.con,r.de,r.motivo+(r.signo?` · ${r.signo}`:'')]),decimales:6};
  G.comparacion=comp;const n=cmetricas(D.scope,G.B.P.hay);
  G.sub='Un clic en un estado abre su historial. Nueva, Recurrente y Resuelta piden stock y datos completos en los dos cortes; una ausencia o un stock cero/cero queda «Sin base»: no es una mejora.';
  const orden=['Recurrente','Nueva','Resuelta','Sin diferencia','Sin base','Todas'];
  return `<div class="ajc-toolbar">${cselect('prev',G.B.P.sesiones.map((s,i)=>[i,s.corto+' · '+s.etiqueta_anio]).filter(([i])=>i<st.c),st.prev,'Contra')}
      <span class="ajc-chips" role="group" aria-label="Estado">${orden.map(s=>cbtn('estado',s,s==='Todas'?`Todas ${cn(comp.length)}`:`${s} ${cn(counts[s])}`,st.status===s,'',s==='Sin base'?'ajc-tenue':'')).join('')}</span></div>
    <p class="ajc-resumen">${st.prev<0?'No hay un corte anterior para comparar.':`${cn(comparables.length)} de ${cn(comp.length)} combinaciones comparables · cambio absoluto en esas líneas: ${csol(delta)} · total actual del detalle: ${csol(n.total)}`}</p>
    <div class="ajc-scroll ajc-detail">${ctabla(['Estado','Producto','Área · Unidad','Anterior neto','Actual neto','Δ absoluto','Repite'],rows.slice(0,st.limite).map(r=>`<tr class="${r.key===st.elegido?'chosen':''}" title="${cesc(r.motivo)}"><td>${cbtn('elegido',r.key,r.estado,r.key===st.elegido)}</td><td class="ajc-td-prod"><span>${cesc(r.prod)}</span><small>${cesc(r.cod)}${r.signo?` · ${cesc(r.signo)}`:''}${!r.comparable&&r.motivo?` · ${cesc(r.motivo)}`:''}</small></td><td>${cesc(cnom(r.area))} · ${cesc(r.um)}</td>
      <td title="${cesc(r.anterior?`Faltó ${csol(r.anterior.falto)} · sobró ${csol(r.anterior.sobro)}`:'Sin registro')}">${r.anterior?.observada?csol(r.anterior.val)+(G.B.P.hay.dif?`<small class="ajc-qty">${cn(r.anterior.dif,3)} ${cesc(r.um)}</small>`:''):'—'}</td>
      <td title="${cesc(r.actual?`Faltó ${csol(r.actual.falto)} · sobró ${csol(r.actual.sobro)}`:'Sin registro')}">${r.actual?.observada?csol(r.actual.val)+(G.B.P.hay.dif?`<small class="ajc-qty">${cn(r.actual.dif,3)} ${cesc(r.um)}</small>`:''):'—'}</td>
      <td>${csol(r.delta)}</td><td title="Cortes con diferencia / cortes con stock hasta el elegido, por producto × área × unidad">${r.con} / ${r.de}</td></tr>`),'ajc-comp',"comparar")}</div>`;
}
function chistoria(G,D){const r=G.comp?.find(x=>x.key===D.st.elegido);if(!r)return '';
  /* Al costado, en lista: cada corte con su neto. */
  return `<aside class="ajc-history"><b>${cesc(r.prod)} · ${cesc(cnom(r.area))} · ${cesc(r.um)}</b><div>${D.hist.map((rows,i)=>{const g=cgrupos(rows.filter(x=>x.key===r.key)).get(r.key);return `<span title="${cesc(G.B.P.sesiones[i].etiqueta_anio)}">${cesc(G.B.P.sesiones[i].corto)}<strong class="${g?.observada?cclase(g.val):''}">${g?.observada?csol(g.val):'Sin base'}</strong></span>`;}).join('')}</div></aside>`;
}
function ctabareas(G,D){const {st}=D,{B}=G,P=B.P;
  const oper=new Map([...cgroup(D.scope.filter(r=>B.oper.has(r.fam)),r=>r.area)].map(([a,g])=>[a,csum(g,'val')]));
  const rows=cordenar(cresumen(D.scope,'area',P.hay).filter(r=>r.total>CEPS),st,'areas',r=>[r.nombre,r.falto,r.sobro,r.saldo,r.total,r.lineas,r.dif,r.exact,r.lineas?r.tol/r.lineas:null,oper.get(r.nombre)??0]);
  const heads=['Área','Faltó S/','Sobró S/','Neto S/','Absoluto S/','Líneas con stock','Con diferencia','Exactitud %','Dentro de ±S/ 5 %','Operación S/'];
  G.exportar={nombre:'Áreas',cabeza:heads,filas:rows.map(r=>[r.nombre,r.falto,r.sobro,r.saldo,r.total,r.lineas,r.dif,r.exact,r.lineas?100*r.tol/r.lineas:null,oper.get(r.nombre)??0]),decimales:6};
  G.sub='Todas las familias de los filtros, con lo que es de los insumos de operación aparte. Un clic en un área lleva a «Productos» con ese foco.';
  return ctabla(['Área','Faltó','Sobró','Neto','Sin compensar','Líneas','Con diferencia','Exactas','±S/ 5','de ello, operación'],rows.map(r=>`<tr class="${st.area===r.nombre?'chosen':''}"><td>${cbtn('area',r.nombre,cnom(r.nombre),st.area===r.nombre)}</td><td class="neg">${cint(r.falto)}</td><td class="pos">${cint(r.sobro)}</td><td><b class="${cclase(r.saldo)}">${cint(r.saldo)}</b></td><td>${cn(r.total)}</td><td>${cn(r.lineas)}</td><td>${cn(r.dif)}</td><td>${cp(r.exact)}</td><td>${cpct(r.tol,r.lineas)}</td><td class="${(oper.get(r.nombre)||0)<-.5?'op':''}">${Math.abs(oper.get(r.nombre)||0)>.5?cint(oper.get(r.nombre)):'—'}</td></tr>`),'','areas');
}
function ctablineas(G,D){
  const {st}=D,prods=cordenar(cproductos(D.scope,st.juntas).filter(r=>cbuscar(r,st.q)),st,'lineas',cprodvals);G.exportar={nombre:'Productos',cabeza:cprodheads,filas:prods.flatMap(r=>[cprodvals(r),...(r.hijos||[]).map(cprodvals)]),decimales:6};
  const fila=(r,hijo=false)=>`<tr class="${hijo?'ajc-child':''}"><td>${!hijo&&r.hijos?.length?cbtn('abrir',r.id,st.abiertos.includes(r.id)?'▾':'▸',st.abiertos.includes(r.id),'Ver sus áreas','ajc-abre'):'<span class="ajc-abre"></span>'}<span title="${cesc(r.compensado?'Falta en un área y sobra en otra. Abra las áreas para revisarlo.':'')}">${cesc(r.prod)}${r.compensado?' ↔':''}</span><small>${cesc(r.cod)} · ${cesc(cnom(r.fam))}${r.sub?` · ${cesc(cnom(r.sub))}`:''}</small></td>
    <td>${cesc(cnom(r.area))}</td><td>${cesc(r.varias_um?'Varias unidades':r.um)}</td>${[r.varias_um?null:r.sis,r.varias_um?null:r.fis,r.varias_um?null:r.dif].map(v=>`<td>${ccant(v)}</td>`).join('')}<td class="${cclase(r.val)}">${csol(r.val)}</td></tr>`;
  const filas=[];for(const r of prods.slice(0,st.limite)){filas.push(fila(r));if(st.abiertos.includes(r.id))filas.push(...(r.hijos||[]).map(x=>fila(x,true)));}
  G.nfilas=prods.length;G.sub='Cada línea del cierre. Con «Áreas juntas», ▸ abre las áreas de un producto; la subfamilia va debajo del nombre.';
  return `<div class="ajc-scroll ajc-detail">${`<table class="ajc-lineas"><thead><tr>${['Producto','Área','Unidad','Sistema','Contado','Diferencia','Ajuste'].map((t,i)=>`<th>${cbtn('ordentab',`lineas|${[3,5,4,6,8,7,9][i]}`,t+' ↕')}</th>`).join('')}</tr></thead><tbody>${filas.join('')}</tbody></table>`}</div>`;
}
function czona(G,D){const {st}=D;
  G.exportar=null;G.nfilas=0;G.sub='';G.pieExtra='';
  let contenido='';
  if(st.tab==='listas')contenido=clistashtml(G,D);
  else if(st.tab==='comparar')contenido=ctabcomparar(G,D);
  else if(st.tab==='lineas')contenido=ctablineas(G,D);
  else if(st.tab==='cierres'){contenido=ccortes(G,D);if(st.vg==='tabla')G.sub='Todas las familias de los filtros.';}
  else if(st.vf==='areas')contenido=`<div class="ajc-scroll ajc-detail">${ctabareas(G,D)}</div>`;
  else contenido=`<div class="ajc-scroll">${D.rs.length?cfamilias(G,D):'<p class="ajc-pie">No hay líneas para estos filtros.</p>'}</div>`;
  if(st.tab!=='listas')contenido=cbarra(G,D)+contenido;
  // En las listas, lo que no entra llega al deslizar: el pie es para la frase.
  const mas=(st.tab!=='listas'||st.lado==='tabla')&&G.nfilas>st.limite;
  const pie=G.sub||G.pieExtra||mas?`<footer>${G.pieExtra}<span title="${cesc(G.sub)}">${cesc(G.sub)}</span>${mas?cbtn('mas','',`Ver más (${Math.min(st.limite,G.nfilas)} / ${G.nfilas})`):''}</footer>`:'';
  return `${contenido||'<p class="ajc-pie">No hay diferencias para este detalle.</p>'}${pie}`;
}
function ccontexto(G,D){const {P}=G.B,{st}=D;return {nombre:'Contexto',cabeza:['Criterio','Valor'],filas:[
  ['Vista',st.vf==='cruce'?'Familia × Área':'Por familia'],['Corte actual',P.sesiones[st.c]?.corto],['Días actual',P.sesiones[st.c]?.etiqueta_anio],['Corte de comparación',P.sesiones[st.prev]?.corto||'Sin anterior'],['Días comparación',P.sesiones[st.prev]?.etiqueta_anio||''],
  ['Familias',st.fams.join(' / ')||'Todas'],['Áreas',st.areas.join(' / ')||'Todas'],['Familia en foco',st.fam||'Todas'],['Área en foco',st.area||'Todas'],['Pestaña',(ctabs.find(([t])=>t===st.tab)||[])[1]],['Orden de las listas',st.orden==='pareto'?'Pareto':'Por monto'],['Áreas de productos',st.juntas?'Juntas':'Separadas'],['Medida del cruce',st.medida==='val'?'Ajuste valorizado':'Stock valorizado'],['Estado',st.status],['Búsqueda',st.q],
  ['Insumos de operación',(P.operacion||[]).join(' / ')||'Ninguna familia'],['Resumen','Faltó, Sobró y Neto de los indicadores: alimentos y bebidas, sin los insumos de operación, que van aparte. La tabla suma las dos en «Todo el cierre».'],
  ['Dentro de ±S/ 5','Líneas con stock cuya diferencia valorizada es de S/ 5 o menos. Exactitud: sin diferencia valorizada (tolerancia 0).'],
  ['Comparabilidad','Código (o nombre sin código), área y unidad iguales. Stock no cero y números completos en ambos cortes. Ausente/cero-cero: Sin base.'],['Recurrencias','Cortes con diferencia / cortes con stock y datos completos, hasta el actual.'],['Unidades','Cantidades numéricas con seis decimales. No se suman unidades diferentes.'],['Exportación','Resumen: filtros completos, con los cortes. Detalle: foco, pestaña, búsqueda y estado seleccionados. Todas sus filas, sin límite de pantalla.']]};}
function cexportar(G,tipo){const D=G.D;let hojas=[G.exportar];
  if(tipo==='resumen'||!G.exportar){
    const {st}=D;let hoja;
    if(st.vf!=='cruce'){hoja={nombre:'Familias',cabeza:['Familia','Faltó S/','Sobró S/','Absoluto S/','Neto S/','Líneas con stock','Con diferencia','Exactitud %','Dentro de ±S/ 5 %','Productos 80 %','Productos con diferencia','Stock valorizado S/','Insumos de operación'],filas:D.fams.map(r=>[r.nombre,r.falto,r.sobro,r.total,r.saldo,r.lineas,r.dif,r.exact,r.lineas?100*r.tol/r.lineas:null,r.n80,r.de,r.valorizado,G.B.oper.has(r.nombre)?'Sí':'No']),decimales:6};}
    else{const m=cmatriz(D.rs,st.medida),cs=new Map(m.cells.map(r=>[JSON.stringify([r.fam,r.area]),r.valor]));hoja={nombre:'Familia y área',cabeza:['Familia',...m.areas,'Total'],filas:m.familias.map(f=>[f,...m.areas.map(a=>cs.get(JSON.stringify([f,a]))??null),m.cells.filter(r=>r.fam===f).reduce((s,r)=>s+r.valor,0)]),decimales:6};}
    const S=cserie(G).tabla;
    hojas=[hoja,{nombre:'Cortes',cabeza:['Corte','Días registrados','Tipo','Faltó S/','Sobró S/','Absoluto S/','Neto S/','Áreas con stock','Líneas con stock','Exactitud %','Alimentos y bebidas neto S/','Insumos de operación neto S/'],filas:S.map(r=>[r.s.corto,r.s.etiqueta_anio,r.s.tipo,r.m.falto,r.m.sobro,r.m.total,r.m.saldo,r.areas,r.m.lineas,r.m.exact,r.c.saldo,r.o.saldo]),decimales:6}];
  }
  return libro([...hojas.filter(Boolean).length?hojas.filter(Boolean):[{nombre:'Sin filas',cabeza:['Sin datos'],filas:[]}],ccontexto(G,D)]);
}
function cpintar(G){
  const main=G.root.querySelector('.ajc-main'),guardado=G.tabPintada===G.st.tab?[...main.querySelectorAll('.ajc-scroll')].map(e=>[e.scrollTop,e.scrollLeft]):[];
  const D=G.D=cdatos(G);G.lista=cdatoslista(G,D);
  const zona=czona(G,D),panel=D.st.tab==='comparar'&&D.st.elegido?chistoria(G,D):'';
  // La ficha de un producto va en una ventana encima de la vista (#814): las listas no se
  // achican. El costado queda sólo para el historial de «Contra el anterior».
  const ven=D.st.tab==='listas'&&D.st.lado!=='tabla'&&D.st.sel?cficha(G,D):'';
  main.innerHTML=`${cfilacorte(G,D)}<div class="ajc-cuerpo"><div class="ajc-zona">${zona}</div>${panel?`<aside class="ajc-pn" aria-label="Historial">${panel}</aside>`:''}</div>${ven?`<button type="button" class="ajc-velo" data-act="soltar" aria-label="Cerrar la ficha"></button><div class="ajc-ven" role="dialog" aria-label="Ficha del producto">${ven}</div>`:''}`;
  main.querySelectorAll('.ajc-scroll').forEach((e,i)=>{if(guardado[i]){e.scrollTop=guardado[i][0];e.scrollLeft=guardado[i][1];}});
  G.tabPintada=G.st.tab;
  cgrafico(G);
}
// ‹ › de la ventana: el producto anterior o siguiente de la MISMA lista, en su orden.
function cnavegar(G,d){const st=G.st;if(!st.sel)return false;const i=st.sel.indexOf('|'),l=st.sel.slice(0,i),prod=st.sel.slice(i+1),L=cnavlista(G.lista,l);
  if(!L.length)return false;const k=L.findIndex(x=>x.prod===prod),n=L[((k<0?0:k)+d+L.length)%L.length];st.sel=`${l}|${n.prod}`;return true;}
function ccambiarcorte(G,i){const {st}=G,P=G.B.P;if(!(i>=0&&i<P.sesiones.length))return;st.c=i;st.prev=cprev(P,i);st.area=null;st.elegido=null;st.sel=null;st.limite=150;
  const areas=new Set((G.B.cortes[i]||[]).filter(r=>r.val!==0&&r.area&&r.area!=='---').map(r=>r.area));st.areas=st.areas.filter(a=>areas.has(a));}
function cenlazar(G){const root=G.root;
  root.addEventListener('click',ev=>{const b=ev.target.closest('[data-act]');
    if(!ev.target.closest('details'))root.querySelectorAll('details[open]').forEach(d=>d.open=false);
    if(!b||!root.contains(b))return;const {act,v}=b.dataset,st=G.st;
    if(act==='vf'){st.vf=v;st.limite=150;if(v!=='cruce')st.medida='val';}
    else if(act==='corte'||act==='mover')ccambiarcorte(G,act==='corte'?+v:st.c+(+v));
    else if(act==='vg')st.vg=v;
    // Elegir una familia, un área o una celda lleva a sus productos.
    else if(act==='familia'){st.fam=st.fam===v&&!st.area?null:v;st.area=null;if(st.fam)st.tab='listas';st.sel=null;}
    else if(act==='celda'){const [f,a]=JSON.parse(v);if(st.fam===f&&st.area===a){st.fam=null;st.area=null;}else{st.fam=f;st.area=a;st.tab='listas';}st.sel=null;}
    else if(act==='area'){st.area=st.area===v&&!st.fam?null:v;st.fam=null;if(st.area)st.tab='listas';st.sel=null;}
    else if(act==='medida')st.medida=v;
    else if(act==='todos'){st[v]=[];st.fam=null;st.area=null;}
    else if(act==='inicial'){st.fams=[...G.B.P.familias_iniciales];st.fam=null;st.area=null;}
    else if(act==='limpiar'){st.fam=null;st.area=null;st.sel=null;}
    else if(act==='tab'){st.tab=v;st.limite=150;st.elegido=null;}
    else if(act==='lado'){st.lado=v;st.limite=150;}
    else if(act==='corden'){const o=st.corden||{k:'val',d:1};st.corden={k:v,d:o.k===v?-o.d:(['cod','fam','sub','prod','um','area'].includes(v)?1:-1)};}
    else if(act==='cagr'){st.cagr=v;st.limite=150;}
    else if(act==='cabre'){const x=new Set(st.cabre||[]);if(x.has(v))x.delete(v);else x.add(v);st.cabre=[...x];}
    else if(act==='prod')st.sel=st.sel===v?null:v;
    else if(act==='soltar')st.sel=null;
    else if(act==='kpiv')st.kpiv=v;
    else if(act==='det6'){st.det6=!st.det6;try{localStorage.setItem('aj_dif_6',st.det6?'1':'0');}catch(e){/* sólo esta vez */}}
    else if(act==='quitar'){st.q='';st.limite=150;}
    else if(act==='quitarq'){st.q='';st.limite=150;}
    else if(act==='nav'){if(!cnavegar(G,+v))return;}
    else if(act==='ampl')st.ampl=!st.ampl;
    else if(act==='juntas')st.juntas=v==='si';else if(act==='orden')st.orden=v;
    else if(act==='estado'){st.status=v;st.limite=150;st.elegido=null;}else if(act==='elegido')st.elegido=st.elegido===v?null:v;
    else if(act==='ordentab'){const [t,i]=v.split('|'),o=st.ordenTabla[t];st.ordenTabla[t]={i:+i,d:o?.i===+i?-o.d:1};}
    else if(act==='abrir')st.abiertos=st.abiertos.includes(v)?st.abiertos.filter(x=>x!==v):[...st.abiertos,v];
    else if(act==='mas')st.limite+=150;
    else if(act==='porque'){if(G.enviar)G.enviar('porque',{...JSON.parse(v),ses:G.B.P.sesiones[st.c]?.clave,n:Date.now()});return;}
    else if(act==='excel'){bajar(`diferencias_${archivo(G.B.P.sesiones[st.c]?.corto||'cierre')}_${v}.xlsx`,cexportar(G,v));return;}
    cpintar(G);
  });
  root.addEventListener('change',ev=>{const el=ev.target,st=G.st,f=el.dataset.filter;
    if(f){st[f]=el.checked?[...st[f],el.value]:st[f].filter(x=>x!==el.value);st.fam=null;st.area=null;st.sel=null;const th=el.dataset.thdd;cpintar(G);root.querySelector(th?'details[data-thdd]':`input[data-filter="${f}"]`)?.closest('details')?.setAttribute('open','');return;}
    if(el.dataset.change==='corte'){ccambiarcorte(G,+el.value);cpintar(G);}
    else if(el.dataset.change==='prev'){st.prev=+el.value;st.elegido=null;cpintar(G);}
  });
  root.addEventListener('input',ev=>{const e=ev.target;if(e.dataset.input!=='buscar')return;const pos=e.selectionStart;G.st.q=e.value;G.st.limite=150;cpintar(G);const n=root.querySelector('.ajc-search');n.focus();if(pos!=null)n.setSelectionRange(pos,pos);});
  root.addEventListener('keydown',ev=>{if(ev.key==='Escape')root.querySelectorAll('details[open]').forEach(d=>d.open=false);});
  root.addEventListener('scroll',ev=>{const e=ev.target,st=G.st;if(e.matches?.('.ajc-zona .ajc-scroll')&&e.scrollTop+e.clientHeight>e.scrollHeight-70&&st.limite<G.nfilas){st.limite+=150;cpintar(G);}},true);
}
window.__ajCierreDatos={leer:cleer,metricas:cmetricas,resumen:cresumen,matriz:cmatriz,productos:cproductos,pareto:cpareto,areasPareto:careasPareto,listas:clistas,espejos:cespejos,comparar:ccomparar,grupos:cgrupos};
window.__ajCierreUI={inicial:cinicial,pintar:cpintar,exportar:cexportar,serie:cserie};
export default function(component){const {data:P,parentElement,setTriggerValue}=component;if(!P)return;
  const old=window.__ajCierre;old?.observer?.disconnect();old?.abort?.abort();
  const mismo=old?.B.P.sello===P.sello,st=mismo&&old.st&&'lado' in old.st?old.st:cinicial(P);
  if(st.det6===undefined){try{st.det6=localStorage.getItem('aj_dif_6')==='1';}catch(e){st.det6=false;}}
  if(old&&old.semilla!==P.perspectiva){st.vf=P.perspectiva==='Familia × Área'?'cruce':'lista';if(st.vf==='cruce')st.tab='familias';}
  let root=parentElement.querySelector('.ajc');if(root)root.remove();root=document.createElement('div');root.className='ajc';root.innerHTML='<section class="ajc-main"></section>';parentElement.appendChild(root);
  const B=mismo?old.B:cleer(P);B.oper=new Set(P.operacion||[]);
  const G={root,st,B,semilla:P.perspectiva,enviar:setTriggerValue,abort:new AbortController()};window.__ajCierre=G;cenlazar(G);cpintar(G);
  let ancho=0;G.observer=new ResizeObserver(es=>{const w=Math.round(es[0].contentRect.width);if(w&&w!==ancho){ancho=w;cgrafico(G);}});G.observer.observe(root.querySelector('.ajc-main'));
  document.addEventListener('pointerdown',ev=>{if(!ev.composedPath().includes(root))root.querySelectorAll('details[open]').forEach(d=>d.open=false);},{signal:G.abort.signal});
  document.addEventListener('keydown',ev=>{if(!root.isConnected||!G.st.sel||!root.querySelector('.ajc-ven'))return;const t=ev.composedPath()[0];if(t&&t.matches?.('input,select,textarea'))return;
    if(ev.key==='Escape'){G.st.sel=null;cpintar(G);}else if(ev.key==='ArrowLeft'||ev.key==='ArrowRight'){ev.preventDefault();if(cnavegar(G,ev.key==='ArrowLeft'?-1:1))cpintar(G);}},{signal:G.abort.signal});
}
