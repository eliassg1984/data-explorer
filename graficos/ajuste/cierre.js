// Diferencias del cierre (#720). Ningún control pide una corrida de Python.
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
  let falto=0,sobro=0,lineas=0,dif=0,stock=0;const pr=new Map();
  for(const r of rows){if(r.val<0)falto+=r.val;else sobro+=r.val;stock+=r.stock;
    if(r.flags&1){lineas++;if(r.flags&2)dif++;}pr.set(r.prod,(pr.get(r.prod)||0)+Math.abs(r.val));}
  const vs=[...pr.values()].filter(v=>v>CEPS).sort((a,b)=>b-a),total=vs.reduce((s,v)=>s+v,0);let acum=0,n80=0;
  for(const v of vs){n80++;acum+=v;if(acum/total>=.8-CEPS)break;}
  return {falto,sobro,total:Math.abs(falto)+sobro,saldo:falto+sobro,lineas,dif,exact:lineas?100*(lineas-dif)/lineas:null,
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
function cinicial(P){const estado=()=>({c:P.inicial,prev:cprev(P,P.inicial),fams:[...P.familias_iniciales],areas:[],fam:null,area:null,tab:'Por producto',
  medida:'val',juntas:true,modo:'Tabla',lado:'Faltantes',q:'',status:'Todas',limite:150,abiertos:[],elegido:null,parProd:null,orden:{}});
  return {vista:P.perspectiva==='Familia × Área'?1:0,vistas:[estado(),estado()]};}
function cdatos(G){const st=G.st.vistas[G.st.vista],{B}=G,P=B.P;
  const clave=JSON.stringify([st.c,st.prev,st.fams,st.areas,st.fam,st.area]);
  if(B.cache.has(clave))return {...B.cache.get(clave),st};
  const rs=cfiltrar(B.cortes[st.c]||[],st),fams=cresumen(rs,'fam',P.hay);
  if(st.fam&&!fams.some(r=>r.nombre===st.fam))st.fam=null;
  const scope=rs.filter(r=>(!st.fam||r.fam===st.fam)&&(!st.area||r.area===st.area));
  const hist=B.cortes.slice(0,st.c+1).map(rows=>cfiltrar(rows,st).filter(r=>(!st.fam||r.fam===st.fam)&&(!st.area||r.area===st.area)));
  const prev=cfiltrar(B.cortes[st.prev]||[],st).filter(r=>(!st.fam||r.fam===st.fam)&&(!st.area||r.area===st.area));
  const datos={rs,fams,scope,hist,prev,m:cmetricas(rs,P.hay)};
  if(B.cache.size>30)B.cache.clear();B.cache.set(clave,datos);return {...datos,st};
}
const cbtn=(act,v,txt,sel=false,tip='')=>`<button type="button" data-act="${act}" data-v="${cesc(v)}" class="${sel?'selected':''}" title="${cesc(tip)}" aria-pressed="${sel}">${cesc(txt)}</button>`;
const cselect=(act,ops,sel,label)=>`<label>${cesc(label)} <select data-change="${act}" aria-label="${cesc(label)}">${ops.map(([v,t])=>`<option value="${cesc(v)}" ${v===sel?'selected':''}>${cesc(t)}</option>`).join('')}</select></label>`;
const ckpi=(label,value,sub='',tip='')=>`<div class="ajc-kpi" title="${cesc(tip)}"><span>${cesc(label)}</span><b>${cesc(value)}</b><small>${cesc(sub)}</small></div>`;
function cfiltro(G,k,label,opciones){const st=G.st.vistas[G.st.vista],vs=st[k];
  return `<details class="ajc-filter"><summary>${cesc(label)}: ${!vs.length?'todas':vs.length===1?cesc(vs[0]):vs.length}</summary><div class="ajc-options"><div>${cbtn('todos',k,'Todas')}${k==='fams'?cbtn('inicial',k,'Iniciales'):''}</div>${opciones.map(v=>`<label><input type="checkbox" data-filter="${k}" value="${cesc(v)}" ${vs.includes(v)?'checked':''}>${cesc(v||'Sin nombre')}</label>`).join('')}</div></details>`;
}
function cprimera(G,D){
  const {P}=G.B,{st,m}=D,base=G.B.cortes[st.c]||[],areas=[...new Set(base.filter(r=>r.val!==0&&r.area&&r.area!=='---').map(r=>r.area))].sort();
  const opciones=P.sesiones.map((s,i)=>[i,`${s.corto} · ${s.etiqueta_anio}`]);
  const ses=P.sesiones[st.c],cob=new Set(D.scope.filter(r=>r.flags&1).map(r=>r.area)).size;
  let tabla='';
  if(!G.st.vista){const familias=cordenar(D.fams,{...st,tab:'Resumen'},r=>[r.nombre,r.falto,r.sobro,r.total,r.saldo,r.exact,r.n80,r.valorizado]);const max=Math.max(...familias.map(r=>r.total),1);
    tabla=`<table class="ajc-families"><thead><tr>${["Familia · clic para el detalle","Faltó","Sobró","Diferencia absoluta","Neto","Exactitud","80 %","Stock valorizado"].map((t,i)=>`<th>${cbtn("ordenres",i,t+" ↕")}</th>`).join("")}</tr></thead><tbody>${familias.map(r=>`<tr class="${st.fam===r.nombre?'chosen':''}"><td>${cbtn('familia',r.nombre,r.nombre,st.fam===r.nombre)}</td><td class="neg">${cs(r.falto)}</td><td class="pos">${cs(r.sobro)}</td><td class="ajc-bar" style="--barra:${100*r.total/max}%">${cs(r.total)}</td><td style="color:${ccolor(r.saldo)}">${cs(r.saldo)}</td><td title="${r.lineas-r.dif} de ${r.lineas} líneas con stock sin diferencia valorizada">${cp(r.exact)}</td><td>${r.n80??'—'} / ${r.de??'—'}</td><td>${cs(r.valorizado)}</td></tr>`).join('')}</tbody><tfoot><tr><th>Total de los filtros</th><td>${cs(m.falto)}</td><td>${cs(m.sobro)}</td><td>${cs(m.total)}</td><td>${cs(m.saldo)}</td><td>${cp(m.exact)}</td><td>${m.n80??'—'} / ${m.de??'—'}</td><td>${cs(m.valorizado)}</td></tr></tfoot></table>`;
  }else{const mat=cmatriz(D.rs,st.medida),max=Math.max(...mat.cells.map(r=>Math.abs(r.valor)),1),map=new Map(mat.cells.map(r=>[JSON.stringify([r.fam,r.area]),r]));
    tabla=`<div class="ajc-toolbar">${cbtn('medida','val','Ajuste valorizado',st.medida==='val')}${P.hay.stock?cbtn('medida','stock','Stock valorizado',st.medida==='stock'):''}<small>Las celdas vacías no tienen registros. Clic en familia: todas sus áreas.</small></div><table class="ajc-matrix"><thead><tr><th>Familia × Área</th>${mat.areas.map(a=>`<th>${cesc(a)}</th>`).join('')}<th>Total neto</th></tr></thead><tbody>${mat.familias.map(f=>`<tr><th>${cbtn('familia',f,f,st.fam===f&&!st.area)}</th>${mat.areas.map(a=>{const r=map.get(JSON.stringify([f,a]));return `<td>${!r?'<span title="Sin registros">—</span>':`<button data-act="celda" data-v="${cesc(JSON.stringify([f,a]))}" class="${st.fam===f&&st.area===a?'selected':''}" style="--celda:${st.medida==='stock'?'var(--accent)':ccolor(r.valor)};--barra:${100*Math.abs(r.valor)/max}%" title="${cesc(`${f} · ${a}: ${cs(r.valor)} · ${r.n} líneas`)}">${Math.abs(r.valor)>CEPS?cs(r.valor):'0.00'}</button>`}</td>`;}).join('')}<td>${cs(mat.cells.filter(r=>r.fam===f).reduce((s,r)=>s+r.valor,0))}</td></tr>`).join('')}</tbody><tfoot><tr><th>Total</th>${mat.areas.map(a=>`<td>${cs(mat.cells.filter(r=>r.area===a).reduce((s,r)=>s+r.valor,0))}</td>`).join('')}<td>${cs(mat.total)}</td></tr></tfoot></table>`;
  }
  return `<header><h3>Diferencias del cierre</h3><nav>${cbtn('vista',0,'Por familia',!G.st.vista)}${cbtn('vista',1,'Familia × Área',!!G.st.vista)}</nav></header>
    <div class="ajc-toolbar ajc-filters">${cselect('corte',opciones,st.c,'Corte')}${cfiltro(G,'fams','Familia',P.dic.fam)}${cfiltro(G,'areas','Área',areas)}${cbtn('excel','resumen','Excel del resumen')}</div>
    <p class="ajc-note">${ses?cesc(`${ses.nombre} · ${ses.etiqueta_anio} · ${ses.n_dias} días · ${ses.juntas} conteos`):'Sin sesiones disponibles'}${P.sin_fecha?` · ${cn(P.sin_fecha)} líneas sin fecha excluidas`:''}</p>
    <div class="ajc-kpis">${ckpi('Faltó',cs(m.falto),'Suma de líneas negativas')}${ckpi('Sobró',cs(m.sobro),'Suma de líneas positivas')}${ckpi('Diferencia absoluta',cs(m.total),'Faltantes + sobrantes sin compensar')}${ckpi('Neto',cs(m.saldo),'Saldo de los ajustes')}${ckpi('Exactitud',cp(m.exact),`${m.lineas-m.dif} / ${m.lineas} líneas con stock`,'Sin diferencia valorizada mayor a 0.000000001; sistema o físico distintos de cero. Cada registro cuenta una línea.')}</div>
    <div class="ajc-scroll ajc-summary">${D.rs.length?tabla:'<p>No hay líneas para estos filtros.</p>'}</div>
    <footer><span>${cn(D.rs.length)} registros · ${cn(cob)} áreas con stock en el detalle</span><span>El resumen conserva todas las líneas; el detalle sigue la familia o celda.</span></footer>`;
}
function ctabla(cabeza,filas,clase='',ordenable=false){return `<table class="${clase}"><thead><tr>${cabeza.map((t,i)=>`<th>${ordenable?cbtn('orden',i,t+' ↕'):cesc(t)}</th>`).join('')}</tr></thead><tbody>${filas.join('')}</tbody></table>`;}
function cordenar(rows,st,valor){const o=st.orden[st.tab];if(!o)return rows;
  return [...rows].sort((a,b)=>{const x=valor(a)[o.i],y=valor(b)[o.i];if(x==null)return y==null?0:1;if(y==null)return -1;return o.d*(typeof x==='number'&&typeof y==='number'?x-y:String(x).localeCompare(String(y)));});}
const cprodheads=['Código','Familia','Subfamilia','Producto','Unidad kardex','Área','Stock sistema','Diferencia','Conteo','Ajuste S/'];
const cprodvals=r=>[r.cod,r.fam,r.sub,r.prod,r.um,r.area,r.varias_um?null:r.sis,r.varias_um?null:r.dif,r.varias_um?null:r.fis,r.val];
const cbuscar=(r,q)=>!q||[r.cod,r.prod,r.fam,r.area,r.sub].join(' ').toLocaleLowerCase().includes(q.toLocaleLowerCase());
function ctabproductos(G,D){
  const {st}=D,prods=cordenar(cproductos(D.scope,st.juntas).filter(r=>cbuscar(r,st.q)),st,cprodvals);G.exportar={nombre:'Productos',cabeza:cprodheads,filas:prods.flatMap(r=>[cprodvals(r),...(r.hijos||[]).map(cprodvals)]),decimales:6};
  let filas=[];
  const fila=(r,hijo=false)=>{const vs=cprodvals(r);return `<tr class="${hijo?'ajc-child':''}"><td>${!hijo&&r.hijos?.length?cbtn('abrir',r.id,(st.abiertos.includes(r.id)?'▾ ':'▸ ')+r.cod,st.abiertos.includes(r.id)):cesc(r.cod)}</td><td>${cesc(r.fam)}</td><td>${cesc(r.sub)}</td><td title="${cesc(r.compensado?'Falta en un área y sobra en otra. Abra las áreas para revisarlo.':'')}">${cesc(r.prod)}${r.compensado?' ↔':''}</td><td>${cesc(r.varias_um?'Varias unidades':r.um)}</td><td>${cesc(r.area)}</td>${vs.slice(6,9).map(v=>`<td>${cn(v,3)}</td>`).join('')}<td style="color:${ccolor(r.val)}">${cs(r.val)}</td></tr>`;};
  if(st.modo==='Listas'){
    if(G.st.vista&&st.medida==='stock'){
      const ps=[...cgroup(D.scope,r=>JSON.stringify([r.id,r.um])).values()].map(g=>({...g[0],fis:csum(g,'fis'),stock:csum(g,'stock')})).filter(r=>cbuscar(r,st.q)).sort((a,b)=>b.stock-a.stock);
      G.exportar={nombre:'Stock de productos',cabeza:['Código','Producto','Unidad','Conteo','Stock valorizado S/'],filas:ps.map(r=>[r.cod,r.prod,r.um,r.fis,r.stock]),decimales:6};G.nfilas=ps.length;
      return ctabla(G.exportar.cabeza,ps.slice(0,st.limite).map(r=>`<tr><td>${cesc(r.cod)}</td><td>${cesc(r.prod)}</td><td>${cesc(r.um)}</td><td>${cn(r.fis,3)}</td><td>${cs(r.stock)}</td></tr>`));
    }
    const listas=clistas(D.scope,st.juntas).filter(r=>cbuscar(r,st.q));
    const ambos=['Faltantes','Sobrantes'].map(l=>{const ps=listas.filter(r=>l==='Faltantes'?r.val<0:r.val>0);
      return `<section><h4>${l} · ${cs(csum(ps,'val'))}</h4>${ctabla(['Código','Producto','Área','Unidad','Diferencia','Ajuste S/'],ps.slice(0,st.limite).map(r=>`<tr><td>${cesc(r.cod)}</td><td title="${cesc(r.prod)}">${cesc(r.prod)}</td><td title="${cesc(r.area)}">${cesc(r.area)}</td><td>${cesc(r.um)}</td><td>${cn(r.dif,3)}</td><td>${cs(r.val)}</td></tr>`))}</section>`;});
    const ps=listas;G.exportar={nombre:'Listas',cabeza:cprodheads,filas:ps.map(cprodvals),decimales:6};
    G.nfilas=Math.max(...['Faltantes','Sobrantes'].map(l=>ps.filter(r=>l==='Faltantes'?r.val<0:r.val>0).length),0);return `<div class="ajc-lists">${ambos.join('')}</div>`;
  }
  for(const r of prods.slice(0,st.limite)){filas.push(fila(r));if(st.abiertos.includes(r.id))filas.push(...(r.hijos||[]).map(x=>fila(x,true)));}
  G.nfilas=prods.length;return ctabla(cprodheads,filas,'',true);
}
function ctabcomparar(G,D){
  const {st}=D,clave=JSON.stringify([st.c,st.prev,st.fams,st.areas,st.fam,st.area]);
  if(!G.B.compare.has(clave)){if(G.B.compare.size>10)G.B.compare.clear();G.B.compare.set(clave,ccomparar(D.scope,D.prev,D.hist));}
  const comp=G.B.compare.get(clave),counts=Object.fromEntries(cestados.slice(1).map(s=>[s,comp.filter(r=>r.estado===s).length]));
  const rows=cordenar(comp.filter(r=>(st.status==='Todas'||r.estado===st.status)&&cbuscar(r,st.q)),st,r=>[r.estado,r.prod,r.area,r.anterior?.observada?r.anterior.val:null,r.actual?.observada?r.actual.val:null,r.delta,r.de?r.con/r.de:null,r.signo||r.motivo]);G.comp=rows;G.nfilas=rows.length;
  const comparables=comp.filter(r=>r.comparable),delta=csum(comparables,'delta'),heads=['Estado','Código','Producto','Familia','Área','Unidad','Anterior neto S/','Actual neto S/','Diferencia anterior cantidad','Diferencia actual cantidad','Anterior absoluto S/','Actual absoluto S/','Cambio absoluto S/','Recurrencias','Cortes con stock','Observación'];
  G.exportar={nombre:'Comparación',cabeza:heads,filas:rows.map(r=>[r.estado,r.cod,r.prod,r.fam,r.area,r.um,r.anterior?.observada?r.anterior.val:null,r.actual?.observada?r.actual.val:null,G.B.P.hay.dif&&r.anterior?.observada?r.anterior.dif:null,G.B.P.hay.dif&&r.actual?.observada?r.actual.dif:null,r.anterior?.observada?r.abs_anterior:null,r.actual?.observada?r.abs_actual:null,r.delta,r.con,r.de,r.motivo+(r.signo?` · ${r.signo}`:'')]),decimales:6};
  const n80=cmetricas(D.scope,G.B.P.hay);
  G.comparacion=comp;
  return `<div class="ajc-comparison-note">${st.prev<0?'No hay un corte anterior para comparar.':`${comparables.length} de ${comp.length} combinaciones comparables · cambio absoluto en esas líneas: ${cs(delta)}.`} El total actual del detalle es ${cs(n80.total)}. Una ausencia o stock cero/cero queda «Sin base».</div>
    <div class="ajc-toolbar ajc-status">${cestados.map(s=>cbtn('estado',s,s==='Todas'?`Todas (${comp.length})`:`${s} (${counts[s]})`,st.status===s)).join('')}</div>
    ${ctabla(['Estado','Código · Producto','Área · Unidad','Anterior neto','Actual neto','Δ absoluto','Repite / con stock','Observación'],rows.slice(0,st.limite).map(r=>`<tr class="${r.key===st.elegido?'chosen':''}" title="${cesc(r.motivo)}"><td>${cbtn('elegido',r.key,r.estado,r.key===st.elegido)}</td><td>${cesc(r.cod)} · ${cesc(r.prod)}</td><td>${cesc(r.area)} · ${cesc(r.um)}</td><td title="${cesc(r.anterior?`Faltó ${cs(r.anterior.falto)} · sobró ${cs(r.anterior.sobro)}`:'Sin registro')}">${r.anterior?.observada?cs(r.anterior.val)+(G.B.P.hay.dif?`<small class="ajc-qty" title="${cesc(r.anterior.dif)} ${cesc(r.um)}">${cn(r.anterior.dif,3)} ${cesc(r.um)}</small>`:''):'—'}</td><td title="${cesc(r.actual?`Faltó ${cs(r.actual.falto)} · sobró ${cs(r.actual.sobro)}`:'Sin registro')}">${r.actual?.observada?cs(r.actual.val)+(G.B.P.hay.dif?`<small class="ajc-qty" title="${cesc(r.actual.dif)} ${cesc(r.um)}">${cn(r.actual.dif,3)} ${cesc(r.um)}</small>`:''):'—'}</td><td>${cs(r.delta)}</td><td>${r.con} / ${r.de}</td><td>${cesc(r.signo||r.motivo)}</td></tr>`),'',true)}`;
}
function chistoria(G,D){const r=G.comp?.find(x=>x.key===D.st.elegido);if(!r)return '';
  return `<aside class="ajc-history"><b>${cesc(r.prod)} · ${cesc(r.area)} · ${cesc(r.um)}</b><div>${D.hist.map((rows,i)=>{const g=cgrupos(rows.filter(x=>x.key===r.key)).get(r.key);return `<span title="${cesc(G.B.P.sesiones[i].etiqueta_anio)}">${cesc(G.B.P.sesiones[i].corto)}<strong>${g?.observada?cs(g.val):'Sin base'}</strong></span>`;}).join('')}</div></aside>`;
}
function csegunda(G,D){const {st}=D,{P}=G.B,tabs=['Por producto','Por área','Por corte','Pareto','Comparar cierres'];
  G.exportar=null;G.exportarExtra=null;G.nfilas=0;
  let contenido='',controles='',sub='',extra='';
  if(st.tab==='Por producto'){
    controles=`${cbtn('modo','Tabla','Tabla',st.modo==='Tabla')}${cbtn('modo','Listas',G.st.vista&&st.medida==='stock'?'Top productos':'Listas',st.modo==='Listas')}${cbtn('juntas','si','Áreas juntas',st.juntas)}${cbtn('juntas','no','Áreas separadas',!st.juntas)}`;
    contenido=ctabproductos(G,D);const e=cespejos(D.scope);sub=G.st.vista&&st.medida==='stock'?(st.modo==='Tabla'?'Tabla de diferencias del inventario. Top productos muestra el stock valorizado y la cantidad contada.':'Stock valorizado y cantidad contada, por producto y unidad.'):e.n?`${e.n} productos faltan en un área y sobran en otra (${cs(e.falto)} / ${cs(e.sobro)}). Es una coincidencia de signos, no una causa.`:'Las cantidades pertenecen a la unidad de cada producto. Las áreas se abren junto a su producto.';
  }else if(st.tab==='Por área'){
    const rows=cresumen(D.scope,'area',P.hay).filter(r=>r.total>CEPS),heads=['Área','Faltó S/','Sobró S/','Absoluto S/','Neto S/','Líneas con stock','Con diferencia','Exactitud %'];
    G.exportar={nombre:'Áreas',cabeza:heads,filas:rows.map(r=>[r.nombre,r.falto,r.sobro,r.total,r.saldo,r.lineas,r.dif,r.exact]),decimales:6};
    contenido=ctabla(heads,rows.map(r=>`<tr><td>${cbtn('area',r.nombre,r.nombre,st.area===r.nombre)}</td>${[r.falto,r.sobro,r.total,r.saldo].map(cs).map(v=>`<td>${v}</td>`).join('')}<td>${r.lineas}</td><td>${r.dif}</td><td>${cp(r.exact)}</td></tr>`));
  }else if(st.tab==='Por corte'){
    const anio=P.sesiones[st.c]?.mes[0],heads=['Corte','Días registrados','Faltó S/','Sobró S/','Absoluto S/','Neto S/','Áreas con stock','Líneas con stock','Exactitud %'];
    const rows=P.sesiones.map((s,i)=>({s,i,rs:cfiltrar(G.B.cortes[i],st).filter(r=>(!st.fam||r.fam===st.fam)&&(!st.area||r.area===st.area))})).filter(r=>r.s.mes[0]===anio).reverse();
    G.exportar={nombre:'Cortes',cabeza:heads,filas:rows.map(r=>{const m=cmetricas(r.rs,P.hay);return [r.s.corto,r.s.etiqueta_anio,m.falto,m.sobro,m.total,m.saldo,new Set(r.rs.filter(x=>x.flags&1).map(x=>x.area)).size,m.lineas,m.exact];}),decimales:6};
    contenido=ctabla(heads,rows.map((r,i)=>`<tr><td>${cbtn('corte',r.i,r.s.corto,st.c===r.i)}</td><td>${cesc(r.s.etiqueta_anio)}</td>${G.exportar.filas[i].slice(2,6).map(v=>`<td>${cs(v)}</td>`).join('')}<td>${G.exportar.filas[i][6]}</td><td>${G.exportar.filas[i][7]}</td><td>${cp(G.exportar.filas[i][8])}</td></tr>`));
    sub=`Todos los cortes del año ${anio||'sin fecha'} del seleccionado. La cobertura evita confundir un parcial con una mejora.`;
  }else if(st.tab==='Pareto'){
    controles=`${cbtn('lado','Faltantes','Faltantes',st.lado==='Faltantes')}${cbtn('lado','Sobrantes','Sobrantes',st.lado==='Sobrantes')}`;
    const all=cpareto(D.scope,st.lado),rows=all.filter(r=>cbuscar(r,st.q)),n=all.filter(r=>r.acum<80-CEPS).length+(all.length?1:0),max=all[0]?.valor||1;
    G.exportar={nombre:'Pareto',cabeza:['Producto','Magnitud S/','Porcentaje %','Acumulado %'],filas:rows.map(r=>[r.prod,r.valor,r.pct,r.acum]),decimales:6};G.nfilas=rows.length;
    contenido=ctabla(['Producto · clic para sus áreas','Magnitud del neto por producto','%','Acumulado'],rows.slice(0,st.limite).map(r=>`<tr><td>${cbtn('parProd',r.prod,r.prod,st.parProd===r.prod)}</td><td class="ajc-bar" style="--barra:${100*r.valor/max}%">${cs(r.valor)}</td><td>${cp(r.pct)}</td><td>${cp(r.acum)}</td></tr>`));
    if(st.parProd&&all.some(r=>r.prod===st.parProd)){
      const areas=careasPareto(D.scope,st.parProd);G.exportarExtra={nombre:'Áreas del producto',cabeza:['Producto','Área','Unidad','Diferencia','Ajuste S/'],filas:areas.map(r=>[st.parProd,r.area,r.um,r.dif,r.val]),decimales:6};
      extra=`<aside class="ajc-pareto-areas"><b>${cesc(st.parProd)} · sus áreas</b><div class="ajc-scroll">${ctabla(['Área','Unidad','Diferencia','Ajuste S/'],areas.map(r=>`<tr><td>${cesc(r.area)}</td><td>${cesc(r.um)}</td><td>${cn(r.dif,3)}</td><td>${cs(r.val)}</td></tr>`))}</div></aside>`;
    }
    sub=`${Math.min(n,all.length)} de ${all.length} productos explican el 80 % del ${st.lado==='Faltantes'?'faltante':'sobrante'} neto. El Pareto suma el ajuste por nombre de producto, como antes; sus porcentajes usan toda la población.`;
  }else{
    controles=cselect('prev',P.sesiones.map((s,i)=>[i,s.corto+' · '+s.etiqueta_anio]).filter(([i])=>i<st.c),st.prev,'Comparar con');contenido=ctabcomparar(G,D);
    sub='Nueva / Recurrente / Resuelta requieren stock y datos completos en ambos cortes. Recurrencias: cortes con diferencia / cortes con stock hasta el seleccionado, por producto × área × unidad.';
  }
  const foco=[st.fam||'Todas las familias',st.area||'Todas las áreas'].join(' · ');
  return `<header><h3>${cesc(foco)}</h3>${cbtn('limpiar','','Quitar foco')}${cbtn('excel','detalle','Excel del detalle')}</header>
    <nav class="ajc-tabs">${tabs.map(t=>cbtn('tab',t,t,st.tab===t)).join('')}</nav><div class="ajc-toolbar">${controles}<input class="ajc-search" type="search" aria-label="Buscar en el detalle" placeholder="Buscar código, producto o área" value="${cesc(st.q)}" data-input="buscar"></div>
    <div class="ajc-scroll ajc-detail">${contenido||'<p>No hay diferencias para este detalle.</p>'}</div>${extra}${st.tab==='Comparar cierres'?chistoria(G,D):''}<footer><span>${cesc(sub)}</span>${G.nfilas>st.limite?cbtn('mas','',`Ver más (${Math.min(st.limite,G.nfilas)} / ${G.nfilas})`):''}</footer>`;
}
function ccontexto(G,D){const {P}=G.B,{st}=D;return {nombre:'Contexto',cabeza:['Criterio','Valor'],filas:[
  ['Perspectiva',G.st.vista?'Familia × Área':'Por familia'],['Corte actual',P.sesiones[st.c]?.corto],['Días actual',P.sesiones[st.c]?.etiqueta_anio],['Corte de comparación',P.sesiones[st.prev]?.corto||'Sin anterior'],['Días comparación',P.sesiones[st.prev]?.etiqueta_anio||''],
  ['Familias',st.fams.join(' / ')||'Todas'],['Áreas',st.areas.join(' / ')||'Todas'],['Familia en foco',st.fam||'Todas'],['Área en foco',st.area||'Todas'],['Pestaña',st.tab],['Vista de productos',st.modo],['Áreas de productos',st.juntas?'Juntas':'Separadas'],['Medida del mapa',st.medida==='val'?'Ajuste valorizado':'Stock valorizado'],['Lado Pareto',st.lado],['Estado',st.status],['Búsqueda',st.q],
  ['Resumen','Todas las líneas de los filtros; faltantes y sobrantes sin compensar. Exactitud sobre líneas con stock, tolerancia 0.'],['Comparabilidad','Código (o nombre sin código), área y unidad iguales. Stock no cero y números completos en ambos cortes. Ausente/cero-cero: Sin base.'],['Recurrencias','Cortes con diferencia / cortes con stock y datos completos, hasta el actual.'],['Unidades','Cantidades numéricas con seis decimales. No se suman unidades diferentes.'],['Exportación','Resumen: filtros completos. Detalle: foco, pestaña, búsqueda y estado seleccionados. Todas sus filas, sin límite de pantalla.']]};}
function cexportar(G,tipo){const D=G.D;let hoja=G.exportar;
  if(tipo==='resumen'){
    if(!G.st.vista){hoja={nombre:'Familias',cabeza:['Familia','Faltó S/','Sobró S/','Absoluto S/','Neto S/','Líneas con stock','Con diferencia','Exactitud %','Productos 80 %','Productos con diferencia','Stock valorizado S/'],filas:cordenar(D.fams,{...D.st,tab:"Resumen"},r=>[r.nombre,r.falto,r.sobro,r.total,r.saldo,r.exact,r.n80,r.valorizado]).map(r=>[r.nombre,r.falto,r.sobro,r.total,r.saldo,r.lineas,r.dif,r.exact,r.n80,r.de,r.valorizado]),decimales:6};}
    else{const m=cmatriz(D.rs,D.st.medida),cs=new Map(m.cells.map(r=>[JSON.stringify([r.fam,r.area]),r.valor]));hoja={nombre:'Familia y área',cabeza:['Familia',...m.areas,'Total'],filas:m.familias.map(f=>[f,...m.areas.map(a=>cs.get(JSON.stringify([f,a]))??null),m.cells.filter(r=>r.fam===f).reduce((s,r)=>s+r.valor,0)]),decimales:6};}
  }
  return libro([hoja||{nombre:'Sin filas',cabeza:['Sin datos'],filas:[]},...(tipo==='detalle'&&G.exportarExtra?[G.exportarExtra]:[]),ccontexto(G,D)]);
}
function cpintar(G,soloDetalle=false){
  G.D=cdatos(G);if(!soloDetalle)G.root.querySelector('.ajc-main').innerHTML=cprimera(G,G.D);
  G.root.querySelector('.ajc-bottom').innerHTML=csegunda(G,G.D);
}
function ccambiarcorte(G,i){const st=G.st.vistas[G.st.vista];st.c=i;st.prev=cprev(G.B.P,i);st.area=null;st.elegido=null;st.limite=150;
  const areas=new Set((G.B.cortes[i]||[]).filter(r=>r.val!==0&&r.area&&r.area!=='---').map(r=>r.area));st.areas=st.areas.filter(a=>areas.has(a));}
function cenlazar(G){const root=G.root;
  root.addEventListener('click',ev=>{const b=ev.target.closest('[data-act]');if(!b)return;const {act,v}=b.dataset,st=G.st.vistas[G.st.vista];let detalle=true;
    if(act==='vista'){G.st.vista=+v;detalle=false;}else if(act==='corte'){ccambiarcorte(G,+v);detalle=false;}
    else if(act==='familia'){st.fam=st.fam===v&&!st.area?null:v;st.area=null;detalle=false;}
    else if(act==='celda'){[st.fam,st.area]=JSON.parse(v);detalle=false;}
    else if(act==='area'){st.area=st.area===v?null:v;detalle=false;}
    else if(act==='medida'){st.medida=v;detalle=false;}
    else if(act==='todos'){st[v]=[];st.fam=null;st.area=null;detalle=false;}
    else if(act==='inicial'){st.fams=[...G.B.P.familias_iniciales];st.fam=null;st.area=null;detalle=false;}
    else if(act==='limpiar'){st.fam=null;st.area=null;detalle=false;}
    else if(act==='tab'){st.tab=v;st.limite=150;st.elegido=null;}
    else if(act==='juntas')st.juntas=v==='si';else if(act==='modo')st.modo=v;else if(act==='lado')st.lado=v;
    else if(act==='estado'){st.status=v;st.limite=150;st.elegido=null;}else if(act==='elegido')st.elegido=st.elegido===v?null:v;
    else if(act==='orden'){const o=st.orden[st.tab];st.orden[st.tab]={i:+v,d:o?.i===+v?-o.d:1};}
    else if(act==='parProd')st.parProd=st.parProd===v?null:v;
    else if(act==='ordenres'){const o=st.orden.Resumen;st.orden.Resumen={i:+v,d:o?.i===+v?-o.d:1};detalle=false;}
    else if(act==='abrir')st.abiertos=st.abiertos.includes(v)?st.abiertos.filter(x=>x!==v):[...st.abiertos,v];else if(act==='mas')st.limite+=150;
    else if(act==='excel'){bajar(`diferencias_${archivo(G.B.P.sesiones[st.c]?.corto||'cierre')}_${v}.xlsx`,cexportar(G,v));return;}
    cpintar(G,detalle);
  });
  root.addEventListener('change',ev=>{const el=ev.target,st=G.st.vistas[G.st.vista],f=el.dataset.filter;
    if(f){const label=f;st[f]=el.checked?[...st[f],el.value]:st[f].filter(x=>x!==el.value);st.fam=null;st.area=null;cpintar(G);root.querySelector(`input[data-filter="${label}"]`)?.closest('details').setAttribute('open','');return;}
    if(el.dataset.change==='corte'){ccambiarcorte(G,+el.value);cpintar(G);}
    else if(el.dataset.change==='prev'){st.prev=+el.value;st.elegido=null;cpintar(G,true);}
  });
  root.addEventListener('input',ev=>{const e=ev.target;if(e.dataset.input!=='buscar')return;const pos=e.selectionStart,st=G.st.vistas[G.st.vista];st.q=e.value;st.limite=150;cpintar(G,true);const n=root.querySelector('.ajc-search');n.focus();if(pos!=null)n.setSelectionRange(pos,pos);});
  root.addEventListener('keydown',ev=>{if(ev.key==='Escape')root.querySelectorAll('details[open]').forEach(d=>d.open=false);});
  root.addEventListener('scroll',ev=>{const e=ev.target,st=G.st.vistas[G.st.vista];if(e.matches('.ajc-detail')&&e.scrollTop+e.clientHeight>e.scrollHeight-70&&st.limite<G.nfilas){const x=e.scrollLeft,y=e.scrollTop;st.limite+=150;cpintar(G,true);const n=root.querySelector('.ajc-detail');n.scrollTop=y;n.scrollLeft=x;}},true);
}
window.__ajCierreDatos={leer:cleer,metricas:cmetricas,resumen:cresumen,matriz:cmatriz,productos:cproductos,pareto:cpareto,areasPareto:careasPareto,listas:clistas,espejos:cespejos,comparar:ccomparar,grupos:cgrupos};
window.__ajCierreUI={inicial:cinicial,pintar:cpintar,exportar:cexportar};
export default function(component){const {data:P,parentElement}=component;if(!P)return;
  const old=window.__ajCierre;old?.observer?.disconnect();old?.abort?.abort();
  const st=old?.B.P.sello===P.sello?old.st:cinicial(P);
  if(old&&old.semilla!==P.perspectiva)st.vista=P.perspectiva==='Familia × Área'?1:0;
  let root=parentElement.querySelector('.ajc');if(root)root.remove();root=document.createElement('div');root.className='ajc';root.innerHTML='<section class="ajc-card ajc-main"></section><section class="ajc-card ajc-bottom"></section>';parentElement.appendChild(root);
  const G={root,st,B:old?.B.P.sello===P.sello?old.B:cleer(P),semilla:P.perspectiva,abort:new AbortController()};window.__ajCierre=G;cenlazar(G);cpintar(G);
  document.addEventListener('pointerdown',ev=>{if(!ev.composedPath().includes(root))root.querySelectorAll('details[open]').forEach(d=>d.open=false);},{signal:G.abort.signal});
}
