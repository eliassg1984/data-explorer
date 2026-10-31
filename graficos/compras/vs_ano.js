/* Compras › Vs año pasado (reglas #725, #749 y #771). Python manda cada producto-mes
   una vez —lo comprado y, si el mes tuvo compras después del día del mes
   parcial, lo comprado hasta ese día—. El navegador arma las parejas contra
   el período de «Contra», parte la diferencia en precio, volumen, lo que se
   dejó de comprar y lo nuevo, y arma las listas. La fecha es el panel de meses de
   Python, puesto en el hueco de la cabecera. El filtro de familias es el de la
   página: viaja todo el histórico y se filtra acá, para decir lo que queda fuera. */
const VAP=(()=>{
  const ALL='__todas__',MODOS=['Valor','Cantidad','Precio'];
  const TABS=[['precio','Subieron de precio'],['volumen','Se compró menos'],['cambio','Dejaron de comprarse y nuevos'],['todos','Todos']];
  const SENTIDOS={precio:[['sube','Subieron'],['baja','Bajaron']],volumen:[['baja','Se compró menos'],['sube','Se compró más']]};
  const CONTRAS=[['aa','el mismo período del año pasado',12,'el año pasado'],['aa2','el mismo período de hace dos años',24,'hace dos años'],['ant','el período anterior',null,'el período anterior']];
  const COBERTURAS=['Todos','En ambos','Sólo actual','Sólo anterior','Sin precio comparable'];
  const n0=new Intl.NumberFormat('en-US',{maximumFractionDigits:0}),n1=new Intl.NumberFormat('en-US',{maximumFractionDigits:1}),
    n2=new Intl.NumberFormat('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}),qf=new Intl.NumberFormat('en-US',{maximumFractionDigits:3});
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normal=v=>String(v??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
  const cmp=(a,b)=>a<b?-1:a>b?1:0;
  const sum=(rs,k)=>{let s=0,c=0;for(const r of rs){const v=(r[k]||0)-c,t=s+v;c=t-s-v;s=t;}return s;};
  function grupos(rs,k){const m=new Map();for(const r of rs){const v=typeof k==='function'?k(r):r[k];if(!m.has(v))m.set(v,[]);m.get(v).push(r);}return m;}
  // Cifras sin decimales: «S/ 17,860», «−22 %». Los precios por unidad, con dos.
  const signo=v=>v<0?'−':v>0?'+':'';
  const entero=v=>n0.format(Math.abs(Math.round(v)));
  const soles=v=>v==null||!isFinite(v)?'—':`${Math.round(v)<0?'−':''}S/ ${entero(v)}`;
  const ssol=v=>v==null||!isFinite(v)?'—':`${signo(Math.round(v))}S/ ${entero(v)}`;
  const sg=v=>`${signo(Math.round(v))}${entero(v)}`;
  const pct=v=>v==null||!isFinite(v)?'—':`${signo(Math.round(v))}${entero(v)} %`;
  const mil=v=>{const a=Math.abs(v);return a<1000?sg(v):`${v<0?'−':''}${(a<100000?n1:n0).format(a/1000)} mil`;};
  const milS=v=>{const a=Math.abs(v);return a<1000?entero(v):`${(a<100000?n1:n0).format(a/1000)} mil`;};
  const precio=v=>v==null||!isFinite(v)?'—':`S/ ${n2.format(v)}`;
  const cant=v=>v==null||!isFinite(v)?'—':qf.format(v);
  const clase=v=>v>.5?'sube':v<-.5?'baja':'';
  const num=m=>{const[y,mm]=String(m).split('-').map(Number);return y*12+mm-1;};
  const str=n=>`${Math.floor(n/12)}-${String(n%12+1).padStart(2,'0')}`;
  const etq=(P,m)=>{if(!m)return'';const[y,mm]=m.split('-');return`${(P.etq_meses||[])[mm-1]||mm} ${y.slice(2)}`;};
  function inicial(v={}){const s={fam:ALL,agrupar:'Producto',q:'',modo:'Valor',foco:null,focoPor:null,meses:[],ancla:null,corte:'Por qué',vista:'Cascada',
    prodSerie:null,detalleMeses:false,cobertura:'Todos',orden:null,contra:'aa',sentido:{precio:'sube',volumen:'baja'},
    kpi:'compra',zona:'graf',medir:'soles',sel:null,sub:null,lado:'dej',amp:null,magn:'Soles',lim:150,menu:null,...v};
    if(s.focoPor==null)s.focoPor=s.agrupar;return s;}
  function leer(P){const rows=(P.filas||[]).map(r=>{const t=r.length>4;return{p:r[0],mes:r[1],v:r[2],q:r[3],vd:t?(r[4]??0):r[2],qd:t?(r[5]??0):r[3],hd:!t||r[4]!=null};});
    const porMes=new Map();for(const r of rows){if(!porMes.has(r.mes))porMes.set(r.mes,[]);porMes.get(r.mes).push(r);}
    return{rows,porMes,mapas:P.mapas||{},unidades:P.unidades||{}};}
  // «Contra» es cuántos meses atrás está la base: 12, 24, el largo de la ventana o hasta el mes elegido.
  function contraK(s,n,ini){const c=CONTRAS.find(x=>x[0]===s.contra);if(c)return c[2]??Math.max(1,n);
    if(typeof s.contra==='string'&&s.contra.startsWith('m:')&&ini!=null){const k=ini-num(s.contra.slice(2));if(k>=1)return k;}
    return 12;}
  function ventana(P,s){
    if(!P.primero||!P.techo)return{k:12,n:0,meses:[],base:[],meses0:[],antes:0,piso:null};
    const lo=num(P.primero),hi=num(P.techo),r=P.rango||[P.primero,P.techo],a=Math.max(lo,num(r[0])),b=Math.min(hi,num(r[1])),m0=[];
    for(let m=a;m<=b;m++)m0.push(m);
    const k=contraK(s,m0.length,m0[0]),piso=lo+k,ms=m0.filter(m=>m>=piso);
    return{k,n:m0.length,meses:ms.map(str),base:ms.map(m=>str(m-k)),meses0:m0.map(str),antes:m0.length-ms.length,piso:str(piso)};}
  // La pareja de cada producto en cada mes, como `_con_ano_pasado` con k meses: outer, y el mes parcial contra los mismos días de su espejo.
  function emparejar(plan,V,P){const out=[],par=P.parcial?.[0];
    V.meses.forEach((m,i)=>{const trunc=par===m,by=new Map();
      for(const r of plan.porMes.get(m)||[])by.set(r.p,{p:r.p,mes:m,v:r.v,q:r.q,va:0,qa:0,ha:true,hb:false});
      for(const r of plan.porMes.get(V.base[i])||[]){if(trunc&&!r.hd)continue;let o=by.get(r.p);
        if(!o){o={p:r.p,mes:m,v:0,q:0,va:0,qa:0,ha:false,hb:false};by.set(r.p,o);}
        o.va=trunc?r.vd:r.v;o.qa=trunc?r.qd:r.q;o.hb=true;}
      out.push(...by.values());});
    return out;}
  // Un producto comprado en los dos períodos se parte en precio y volumen con la cantidad PROMEDIO de los dos (Bennet):
  // el precio no depende de qué período se tome de base. Uno que sólo está de un lado es nuevo o se dejó de comprar.
  function claseDe(r){if(r.q>0&&r.qa>0)return'ambos';if(Math.abs(r.va)<.005&&r.v>.005)return'nuevo';if(Math.abs(r.v)<.005&&r.va>.005)return'dejado';
    return Math.abs(r.v-r.va)<.005?'igual':'otro';}
  const SUMAS=['v','va','delta','ep','ev','nue','dej','otr','nAmbos','nNue','nDej','nOtr','soloA','soloB','ambos','sinBase'];
  function porProducto(rs,P,plan){return[...grupos(rs,'p')].map(([p,g])=>{
    const v=sum(g,'v'),q=sum(g,'q'),va=sum(g,'va'),qa=sum(g,'qa'),delta=v-va,c=claseDe({v,q,va,qa});
    const ep=c==='ambos'?.5*(q+qa)*(v/q-va/qa):0,ev=c==='ambos'?delta-ep:0,ha=g.some(r=>r.ha),hb=g.some(r=>r.hb);
    return{p,item:P.productos[p],v,q,va,qa,delta,ep,ev,nue:c==='nuevo'?delta:0,dej:c==='dejado'?delta:0,otr:c==='otro'||c==='igual'?delta:0,
      clase:c,n:1,nAmbos:+(c==='ambos'),nNue:+(c==='nuevo'),nDej:+(c==='dejado'),nOtr:+(c==='otro'),ha,hb,soloA:+(ha&&!hb),soloB:+(hb&&!ha),ambos:+(ha&&hb),
      sinBase:+(q<=0||qa<=0),pa:qa>0?va/qa:null,pn:q>0?v/q:null,um:plan.unidades[p]||'',fam:plan.mapas.Familia?.[p]||'',sub:plan.mapas.Subfamilia?.[p]||''};});}
  function agrupar(rs,P,plan,por){const prods=porProducto(rs,P,plan);if(por==='Producto')return prods;
    const mapa=plan.mapas[por]||{};return[...grupos(prods,r=>mapa[r.p]??r.item)].map(([item,g])=>{
      const o={item,n:g.length,q:null,qa:null,pa:null,pn:null,um:'',ha:g.some(r=>r.ha),hb:g.some(r=>r.hb),fam:por==='Subfamilia'?g[0].fam:'',sub:''};
      for(const k of SUMAS)o[k]=sum(g,k);o.clase='grupo';return o;});}
  function motivo(r){if(r.clase==='nuevo')return'Nuevo';if(r.clase==='dejado')return'Dejó de comprarse';if(r.clase==='otro')return'Sin cantidad comparable';if(r.clase==='igual')return'Igual';
    const ps=[[r.ep,r.ep>0?'Subió de precio':'Bajó de precio'],[r.ev,r.ev<0?'Se compró menos':'Se compró más'],[r.nue,'Nuevos'],[r.dej,'Dejaron de comprarse'],[r.otr,'Sin cantidad comparable']];
    const m=ps.reduce((a,b)=>Math.abs(b[0])>Math.abs(a[0])?b:a);return Math.abs(m[0])<.5?'Igual':m[1];}
  function totales(ps){const o={};for(const k of SUMAS)o[k]=sum(ps,k);
    const am=ps.filter(r=>r.clase==='ambos');let pq=0,pqa=0;for(const r of am){pq+=r.va/r.qa*r.q;pqa+=r.v/r.q*r.qa;}
    const sv=sum(am,'v'),sva=sum(am,'va');o.paasche=pq>0?sv/pq-1:null;o.laspeyres=sva>0?pqa/sva-1:null;o.pct=o.va>0?o.delta/o.va*100:null;return o;}
  // La compra contra la venta: sólo meses completos con venta en los dos lados. Es un cálculo propio, no el costo de ventas.
  function ventaRatio(P,V,g){if(P.venta==null)return{estado:P.venta_pendiente?'pendiente':'sin'};const vm=P.venta;if(!Object.keys(vm).length)return{estado:'sin'};
    const ok=[];V.meses.forEach((m,i)=>{if(m!==P.parcial?.[0]&&vm[m]>0&&vm[V.base[i]]>0)ok.push([m,V.base[i]]);});
    if(!ok.length)return{estado:'sinmeses'};
    const okm=new Set(ok.map(x=>x[0])),gs=g.filter(r=>okm.has(r.mes)),cn=sum(gs,'v'),ca=sum(gs,'va');
    const vn=ok.reduce((a,x)=>a+vm[x[0]],0),va=ok.reduce((a,x)=>a+vm[x[1]],0);
    return{estado:'ok',n:ok.length,meses:ok.map(x=>x[0]),cn,ca,vn,va,rn:cn/vn,ra:ca/va,dv:vn/va-1};}
  function magnitud(r,modo,anterior=false){const v=anterior?r.va:r.v,q=anterior?r.qa:r.q;return modo==='Precio'?(q>0?v/q:null):modo==='Cantidad'?q:v;}
  // Las familias del filtro de la página, con el nombre que llevan los mapas.
  function pagSet(P){const pa=P.pagina;if(!pa?.elegidas?.length)return null;const m=new Map(pa.todas);return new Set(pa.elegidas.map(f=>m.get(f)??f));}
  function calcular(P,s,cache={}){
    if(cache.P!==P){cache.P=P;cache.plan=leer(P);cache.key=null;}
    const plan=cache.plan,V=ventana(P,s),pag=pagSet(P),key=JSON.stringify([V.k,V.meses,P.pagina?.elegidas||null]);
    if(cache.key!==key){cache.key=key;cache.todoAll=emparejar(plan,V,P);cache.todo=pag?cache.todoAll.filter(r=>pag.has((plan.mapas.Familia||{})[r.p])):cache.todoAll;cache.fams=null;}
    const famDe=plan.mapas.Familia||{},subDe=plan.mapas.Subfamilia||{},todo=cache.todo;
    if(!cache.fams){const m=new Map();for(const r of todo){const f=famDe[r.p]??'';if(!m.has(f))m.set(f,[]);m.get(f).push(r);}
      cache.fams=[...m].filter(([f])=>f).map(([fam,rs])=>({fam,v:sum(rs,'v'),va:sum(rs,'va')})).filter(f=>Math.abs(f.v)>.005||Math.abs(f.va)>.005)
        .sort((a,b)=>b.va-a.va||b.v-a.v||cmp(a.fam,b.fam));}
    const g=todo.filter(r=>(s.fam===ALL||famDe[r.p]===s.fam)&&(!s.sub||subDe[r.p]===s.sub)),prodsAll=porProducto(g,P,plan),tot=totales(prodsAll),venta=ventaRatio(P,V,g);
    const focoPor=s.focoPor||s.agrupar,mapaF=focoPor==='Producto'?null:plan.mapas[focoPor]||{};
    const nombreF=r=>mapaF?mapaF[r.p]??P.productos[r.p]:P.productos[r.p];
    const foco=s.foco!=null&&g.some(r=>nombreF(r)===s.foco)?s.foco:null;
    let gf=foco==null?g:g.filter(r=>nombreF(r)===foco);
    const productos=porProducto(gf,P,plan).sort((a,b)=>b.v-a.v||cmp(b.item,a.item));
    // Cantidad y Precio son de UN producto: sin foco no se ofrecen (no se suman kilos con unidades).
    const modo=foco==null?'Valor':s.modo;let referencia=null;
    if(modo!=='Valor'){referencia=productos.find(r=>r.item===s.prodSerie)||productos[0]||null;gf=referencia?gf.filter(r=>r.p===referencia.p):[];}
    const serie=[...grupos(gf,'mes')].sort((a,b)=>cmp(a[0],b[0])).map(([mes,rs])=>({mes,base:V.base[V.meses.indexOf(mes)],v:sum(rs,'v'),q:sum(rs,'q'),va:sum(rs,'va'),qa:sum(rs,'qa'),ha:rs.some(r=>r.ha),hb:rs.some(r=>r.hb)}));
    const vm=P.venta||{};for(const r of serie)r.ratio=foco==null&&modo==='Valor'&&r.mes!==P.parcial?.[0]&&vm[r.mes]>0?100*r.v/vm[r.mes]:null;
    const meses=s.meses.filter(m=>serie.some(r=>r.mes===m)),gc=meses.length?gf.filter(r=>meses.includes(r.mes)):gf;
    const productosC=porProducto(gc,P,plan),totC={...totales(productosC),q:sum(productosC,'q'),qa:sum(productosC,'qa')};
    const a=magnitud(totC,modo),b=magnitud(totC,modo,true),delta=a==null||b==null?null:a-b,pc=b>0&&delta!=null?delta/b*100:null;
    const ops=modo==='Precio'?[]:[...(modo==='Valor'?['Por qué']:[]),...(foco==null&&modo==='Valor'?['Quién']:[]),...(serie.length>1&&meses.length!==1?['Cuándo']:[])];
    const corte=ops.includes(s.corte)?s.corte:ops[0]||null;let partes=[];
    if(corte==='Por qué'){
      if(totC.nAmbos)partes.push({nombre:'Precio',valor:totC.ep,clave:'ep'},{nombre:totC.ev<0?'Se compró menos':'Se compró más',valor:totC.ev,clave:'ev'});
      if(totC.nDej)partes.push({nombre:totC.nDej===1&&productosC.length===1?'Dejó de comprarse':'Dejaron de comprarse',valor:totC.dej,clave:'dej',n:totC.nDej});
      if(totC.nNue)partes.push({nombre:totC.nNue===1&&productosC.length===1?'Nuevo':'Nuevos',valor:totC.nue,clave:'nue',n:totC.nNue});
      if(Math.abs(totC.otr)>=.5)partes.push({nombre:'Sin cantidad comparable',valor:totC.otr,clave:'otr',n:totC.nOtr});
    }else if(corte==='Quién')partes=agrupar(gc,P,plan,s.agrupar).map(r=>({nombre:r.item,valor:r.delta}));
    else if(corte==='Cuándo')partes=serie.filter(r=>!meses.length||meses.includes(r.mes)).map(r=>({nombre:etq(P,r.mes),valor:magnitud(r,modo)-magnitud(r,modo,true),mes:r.mes}));
    else if(delta!=null)partes=[{nombre:'Variación',valor:delta}];
    if(partes.length>P.max_pasos&&(corte==='Quién'||corte==='Cuándo')){
      const orden=partes.map((r,i)=>({...r,i})).sort((x,y)=>Math.abs(y.valor)-Math.abs(x.valor)||x.i-y.i),top=orden.slice(0,P.max_pasos),resto=orden.slice(P.max_pasos);
      partes=(corte==='Cuándo'?top.sort((x,y)=>x.i-y.i):top).concat([{nombre:`Otros (${resto.length})`,valor:sum(resto,'valor')}]);}
    const tg=s.detalleMeses&&meses.length?g.filter(r=>meses.includes(r.mes)):g,q=normal(s.q),busca=r=>!q||normal(r.item).includes(q);
    const det=agrupar(tg,P,plan,s.agrupar).filter(busca),prodDet=s.agrupar==='Producto'?det:porProducto(tg,P,plan).filter(busca);
    const conPrecio=r=>s.agrupar==='Producto'?r.clase==='ambos':r.nAmbos>0,sp=s.sentido?.precio||'sube',sv=s.sentido?.volumen||'baja';
    const precioL=det.filter(r=>conPrecio(r)&&(sp==='sube'?r.ep>.5:r.ep<-.5)).sort((x,y)=>sp==='sube'?y.ep-x.ep:x.ep-y.ep);
    const volumenL=det.filter(r=>conPrecio(r)&&(sv==='baja'?r.ev<-.5:r.ev>.5)).sort((x,y)=>sv==='baja'?x.ev-y.ev:y.ev-x.ev);
    const dejados=prodDet.filter(r=>r.clase==='dejado').sort((x,y)=>y.va-x.va||cmp(x.item,y.item)),nuevos=prodDet.filter(r=>r.clase==='nuevo').sort((x,y)=>y.v-x.v||cmp(x.item,y.item));
    const reemplazos=[...grupos(dejados.concat(nuevos),r=>r.sub||r.fam||'Sin subfamilia')].map(([sub,rs])=>({sub,fam:rs[0].fam,dej:sum(rs,'dej'),nue:sum(rs,'nue'),nd:rs.filter(r=>r.clase==='dejado').length,nn:rs.filter(r=>r.clase==='nuevo').length}))
      .filter(r=>r.nd&&r.nn).sort((x,y)=>Math.min(Math.abs(y.dej),y.nue)-Math.min(Math.abs(x.dej),x.nue)).slice(0,6);
    const tabla=det.filter(r=>s.cobertura==='Todos'||s.cobertura==='En ambos'&&r.ha&&r.hb||s.cobertura==='Sólo actual'&&r.ha&&!r.hb||s.cobertura==='Sólo anterior'&&r.hb&&!r.ha||s.cobertura==='Sin precio comparable'&&r.sinBase>0)
      .map(r=>({...r,pct:r.va>0?r.delta/r.va*100:null,motivo:motivo(r)})).sort((x,y)=>Math.abs(y.delta)-Math.abs(x.delta)||cmp(x.item,y.item));
    return{plan,V,g,gf,gc,tot,venta,familias:cache.fams,todoTot:{v:sum(todo,'v'),va:sum(todo,'va')},foco,focoPor,productos,referencia,modo,serie,meses,totC,a,b,delta,pct:pc,ops,corte,partes,
      det,precio:precioL,volumen:volumenL,dejados,nuevos,reemplazos,tabla,um:referencia?referencia.um:(new Set(gf.map(r=>r.p)).size===1?plan.unidades[gf[0]?.p]||'':''),
      parcial:P.parcial,grupos:['Producto',...Object.keys(plan.mapas)]};}
  const c=(k,n,t='')=>({k,n,t});
  function rangoTxt(P,ms){if(!ms.length)return'Sin meses';const ks=[...new Set(ms)].sort(),a=etq(P,ks[0]),b=etq(P,ks.at(-1));return a===b?a:`${a} – ${b}`;}
  function contraTxt(G){const{s,D,P}=G;if(s.contra==='aa')return'un año antes';if(s.contra==='aa2')return'dos años antes';
    if(s.contra==='ant')return'el período anterior';return rangoTxt(P,D.V.base);}
  function nombreBase(G){const s=G.s;return s.contra==='aa'?'Año pasado':s.contra==='aa2'?'Hace dos años':s.contra==='ant'?'Período anterior':'Base';}
  function opcionesContra(G){const{P,D,s}=G,ini=D.V.meses0[0],ops=CONTRAS.map(([k,,,n])=>`<option value="${k}" ${s.contra===k?'selected':''}>Contra: ${esc(n)}</option>`);
    if(ini&&P.primero){const lo=num(P.primero),hasta=num(ini)-1,ms=[];for(let m=hasta;m>=lo;m--)ms.push(str(m));
      if(ms.length)ops.push(`<optgroup label="Desde otro mes">${ms.map(m=>`<option value="m:${m}" ${s.contra==='m:'+m?'selected':''}>${esc(`Desde ${etq(P,m)}`)}</option>`).join('')}</optgroup>`);}
    return ops.join('');}
  function colsDetalleExcel(G){const prod=G.s.agrupar==='Producto';return[c('item',G.s.agrupar),...(prod?[c('sub','Subfamilia'),c('fam','Familia')]:[c('n','Productos')]),c('motivo','Motivo'),c('v','Valor este período'),c('va','Valor de la base'),c('delta','Δ S/'),c('pct','Δ %'),
    c('ep','Efecto precio'),c('ev','Efecto volumen'),c('dej','Dejaron de comprarse'),c('nue','Nuevos'),c('otr','Sin cantidad comparable'),...(prod?[c('um','Unidad'),c('q','Cantidad este período'),c('qa','Cantidad de la base'),c('pn','Precio este período'),c('pa','Precio de la base')]:[])];}
  function exportar(G){const{P,s,D}=G,hoja=(nombre,cols,filas)=>({nombre,cabeza:cols.map(x=>x.n),decimales:6,filas:filas.map(r=>cols.map(x=>r[x.k]??''))});
    const unaUnidad=new Set(D.gf.map(r=>r.p)).size===1,vm=P.venta||{};
    const serie=D.serie.map(r=>({mes:r.mes,base:r.base,v:r.v,va:r.va,q:unaUnidad?r.q:null,qa:unaUnidad?r.qa:null,pa:unaUnidad?magnitud(r,'Precio'):null,paa:unaUnidad?magnitud(r,'Precio',true):null,
      venta:vm[r.mes]??null,ventab:vm[r.base]??null,ratio:r.ratio}));
    const scols=[c('mes','Mes'),c('base','Mes de la base'),c('v','Valor del mes'),c('va','Valor de la base'),c('q','Cantidad del mes'),c('qa','Cantidad de la base'),c('pa','Precio medio del mes'),c('paa','Precio medio de la base'),c('venta','Venta neta del mes'),c('ventab','Venta neta de la base'),c('ratio','Compra por S/ 100 vendidos')];
    const t=D.tot,v=D.venta,contexto=[['Vista','Compras vs año pasado'],['Meses comparados',rangoTxt(P,D.V.meses)],['Meses de la base',rangoTxt(P,D.V.base)],['Contra',CONTRAS.find(x=>x[0]===s.contra)?.[1]||rangoTxt(P,D.V.base)],
      ['Meses que se corren',`${D.V.k} meses atrás`],['Familia propia',s.fam===ALL?'Todas':s.fam],...Object.entries(P.contexto||{}).map(([k,x])=>[k,x.join(', ')||'Todas']),['Agrupación del detalle',s.agrupar],
      ['Magnitud de la serie',D.modo],['Foco',D.foco||'Todas las compras'],['Producto de referencia',D.referencia?.item||'No aplica'],['Unidad',D.um||'Sin dato / varias unidades'],
      ['Meses explicados',D.meses.length?D.meses.map(m=>etq(P,m)).join(' · '):'Todos'],['Meses aplicados al detalle',s.detalleMeses?'Sí':'No'],['Buscar',s.q],['Cobertura de registros',s.cobertura],
      ['Mes parcial',P.parcial?`${P.parcial[0]} hasta el día ${P.parcial[1]}; su base se recorta igual`:'Sin mes parcial'],
      ['Comparación','Cada mes contra el mes que está tantos meses atrás como pide «Contra». No se usan las columnas de año anterior repetidas del parquet.'],
      ['Precio','Media ponderada valor / cantidad. Efecto precio = (precio de ahora − precio de la base) × cantidad promedio de los dos períodos, producto por producto, antes de sumar.'],
      ['Volumen','Lo que queda de la variación de los productos comprados en los dos períodos, una vez quitado el efecto precio.'],
      ['Dejaron de comprarse y nuevos','Productos con valor de un solo lado. Sin cantidad comparable: productos con cantidad cero o negativa en un lado.'],
      ['Compra por S/ 100 vendidos','Cálculo propio: compras del alcance ÷ venta neta de ventas.parquet × 100, sólo en meses completos con venta en los dos lados. No es el costo de ventas: no mira el inventario.'],
      ['Valor del período',t.v],['Valor de la base',t.va],['Efecto precio',t.ep],['Efecto volumen',t.ev],['Dejaron de comprarse',t.dej],['Nuevos',t.nue],['Sin cantidad comparable',t.otr],
      ['Mismos productos (Paasche)',t.paasche],['Mismos productos (Laspeyres)',t.laspeyres],['Venta neta del período (meses completos)',v.vn??''],['Venta neta de la base',v.va??'']];
    return[hoja('Detalle',colsDetalleExcel(G),D.tabla),
      hoja('Serie mensual',scols,serie),{nombre:'Descomposición',cabeza:['Parte','Variación'],decimales:6,filas:D.partes.map(r=>[r.nombre,r.valor])},
      hoja('Familias',[c('fam','Familia'),c('v','Valor del período'),c('va','Valor de la base')],D.familias),
      {nombre:'Contexto',cabeza:['Dato','Selección'],decimales:6,filas:contexto}];}
  // ── La pantalla (regla #771): cuatro indicadores que suman la diferencia, una
  // zona (Gráfico o Productos) y, al costado, el porqué o la ficha del producto.
  // Las cuentas son las de arriba; `calcular` corre sin foco y con los meses
  // elegidos aplicados a todo: elegir un mes cambia la pantalla entera.
  const fS=v=>v==null||!isFinite(v)?'—':`${v<-.5?'−':''}S/ ${entero(v)}`;
  const fD=v=>v==null||!isFinite(v)?'—':`${v>.5?'+':v<-.5?'−':''}S/ ${entero(v)}`;
  const f2=v=>v==null||!isFinite(v)?'—':n2.format(v);
  const fQ=v=>v==null||!isFinite(v)?'—':n1.format(v);
  const fP=x=>x==null||!isFinite(x)?'—':`${x>.0005?'+':x<-.0005?'−':''}${Math.abs(x*100).toFixed(Math.abs(x)<.1?1:0)} %`;
  const fF=x=>x==null||!isFinite(x)?'—':`${x>.0005?'▲ ':x<-.0005?'▼ ':''}${Math.abs(x*100).toFixed(Math.abs(x)<.1?1:0)} %`;
  const fK=v=>{const a=Math.abs(v);return`${v<0?'−':''}S/ ${a>=1e6?`${(a/1e6).toFixed(2)} M`:a>=1e5?`${Math.round(a/1e3)}k`:a>=1e3?`${(a/1e3).toFixed(1)}k`:Math.round(a)}`;};
  const rojoVerde=v=>v==null?'':v>.5?'rojo':v<-.5?'verde':'';
  const nP=(n,t='producto')=>`${n0.format(n)} ${t}${n===1?'':'s'}`;
  function baseMin(G){const b=nombreBase(G);return G.s.contra==='aa'||G.s.contra==='ant'||G.s.contra==='aa2'?b.toLowerCase():'la base';}
  function juntar(rs,por){if(por==='Producto')return rs;
    return[...grupos(rs,r=>(por==='Familia'?r.fam:r.sub)||'Sin grupo')].map(([item,g])=>{const o={item,n:g.length,clase:'grupo',grupo:true,fam:por==='Subfamilia'?g[0].fam:'',sub:''};for(const k of SUMAS)o[k]=sum(g,k);o.pct=o.va>0?o.delta/o.va*100:null;return o;});}
  // Trece meses hasta el último dato, cada uno contra su espejo: las curvas de los indicadores, el detalle al cursor y la ficha.
  function trece(P,s,D,cache){const key=JSON.stringify([D.V.k,s.fam,s.sub||'']);if(cache.tKey===key&&cache.tP===P)return cache.t;
    const plan=D.plan,hi=num(P.techo),lo=num(P.primero)+D.V.k,ms=[];for(let m=hi-12;m<=hi;m++)if(m>=lo)ms.push(m);
    const V={meses:ms.map(str),base:ms.map(m=>str(m-D.V.k))},pg=pagSet(P),fm=plan.mapas.Familia||{},sb=plan.mapas.Subfamilia||{};
    const pares=emparejar(plan,V,P).filter(r=>(!pg||pg.has(fm[r.p]))&&(s.fam===ALL||fm[r.p]===s.fam)&&(!s.sub||sb[r.p]===s.sub));
    const porMes={};for(const m of V.meses)porMes[m]=totales(porProducto(pares.filter(r=>r.mes===m),P,plan));
    cache.tKey=key;cache.tP=P;cache.t={...V,pares,porMes};return cache.t;}
  // Lo que queda en el filtro de la página y lo que no, con su base: sin ella, el % de arriba engaña.
  function fueraDePagina(P,D,cache){const pg=pagSet(P),fm=D.plan.mapas.Familia||{},por=new Map(),fuera=new Map();
    for(const r of cache.todoAll||[]){const f=fm[r.p]||'';por.set(f,(por.get(f)||0)+r.v);if(pg&&!pg.has(f)){const x=fuera.get(f)||{f,v:0,va:0};x.v+=r.v;x.va+=r.va;fuera.set(f,x);}}
    return{por,fuera:[...fuera.values()].sort((a,b)=>b.va-a.va)};}
  function curvaKpi(vs){if(vs.length<2)return'';const a=Math.min(...vs),b=Math.max(...vs),r=b-a||1,n=vs.length-1;
    return`<svg viewBox="0 0 100 34" preserveAspectRatio="none" aria-hidden="true"><polyline points="${vs.map((v,i)=>`${(i*100/n).toFixed(1)},${(31-(v-a)/r*28).toFixed(1)}`).join(' ')}"/></svg>`;}
  const cartaDe=t=>t.dej+t.nue+t.otr;
  function kpisHtml(G,t,T){const{s}=G,inf=[t.paasche,t.laspeyres].filter(x=>x!=null).sort((a,b)=>a-b),base=baseMin(G);
    const rango=!inf.length?'—':Math.round(inf[0]*100)===Math.round(inf.at(-1)*100)?fP(inf[0]):`${fP(inf[0])} a ${fP(inf.at(-1))}`,v=f=>T.meses.map(m=>f(T.porMes[m]));
    const k=(id,rot,val,cls,sub,serie,tip)=>`<button class="vap-kpi${s.kpi===id?' on':''}" data-a="kpi" data-v="${id}" aria-pressed="${s.kpi===id}" title="${esc(tip)}">${curvaKpi(serie)}<span class="r">${esc(rot)}</span><span class="v ${cls}">${esc(val)}</span><span class="d">${esc(sub)}</span></button>`;
    return k('compra','Compra',fS(t.v),'',`${fF(t.va>0?t.delta/t.va:null)} contra ${fS(t.va)} · ${fD(t.delta)}`,v(x=>x.v),`Toda la compra del alcance contra ${base}. Las tres de al lado suman esta diferencia.`)
      +k('precio','Precio',fD(t.ep),rojoVerde(t.ep),`${nP(t.nAmbos)} en los dos · ${rango}`,v(x=>x.ep),'El cambio de precio por la cantidad promedio de los dos períodos, producto por producto.')
      +k('cantidad','Cantidad',fD(t.ev),'',`${t.ev<0?'se compró menos':'se compró más'} de esos mismos productos`,v(x=>x.ev),'Lo que queda de esos productos una vez quitado el precio. Comprar menos no es bueno ni malo: por eso no va en verde.')
      +k('carta','Dejados y nuevos',fD(cartaDe(t)),'',`${n0.format(t.nDej)} dejados ${fD(t.dej)} · ${n0.format(t.nNue)} nuevos ${fD(t.nue)}`,v(cartaDe),'Productos comprados de un solo lado. Suele ser un cambio de carta o de proveedor.');}
  function cuanto(t){const inf=[t.paasche,t.laspeyres].filter(x=>x!=null).sort((a,b)=>a-b);if(!inf.length)return'';const a=inf[0],b=inf.at(-1),n=x=>`${Math.abs(x*100).toFixed(Math.abs(x)<.1?1:0)} %`;
    if(Math.round(a*100)===Math.round(b*100))return`${n(a)} ${a>=0?'más':'menos'}`;if(a>=0)return`entre ${n(a)} y ${n(b)} más`;if(b<=0)return`entre ${n(b)} y ${n(a)} menos`;return`entre ${fP(a)} y ${fP(b)}`;}
  function fraseDe(G,t,prods){const{D,s}=G,v=D.venta,sube=prods.filter(r=>r.clase==='ambos'&&r.ep>.5),baja=prods.filter(r=>r.clase==='ambos'&&r.ep<-.5),menos=prods.filter(r=>r.clase==='ambos'&&r.ev<-.5),mas=prods.filter(r=>r.clase==='ambos'&&r.ev>.5),q=cuanto(t);
    if(s.kpi==='precio')return`${nP(sube.length)} ${sube.length===1?'subió':'subieron'} ${fD(sum(sube,'ep'))} y ${n0.format(baja.length)} ${baja.length===1?'bajó':'bajaron'} ${fD(sum(baja,'ep'))}.${q?` En conjunto, los mismos productos costaron ${q}.`:''}`;
    if(s.kpi==='cantidad')return`De esos mismos productos, ${n0.format(menos.length)} se compraron menos (${fD(sum(menos,'ev'))}) y ${n0.format(mas.length)} más (${fD(sum(mas,'ev'))}).${v.estado==='ok'?` La venta de los meses completos cambió ${fP(v.dv)}.`:''}`;
    if(s.kpi==='carta')return`${nP(t.nDej)} se ${t.nDej===1?'dejó':'dejaron'} de comprar (${fD(t.dej)}) y ${n0.format(t.nNue)} ${t.nNue===1?'es nuevo':'son nuevos'} (${fD(t.nue)}). Suele ser un cambio de carta o de proveedor, no un ahorro.`;
    let h=`Compraste ${Math.abs(Math.round(t.pct||0))} % ${t.delta<0?'menos':'más'} que ${contraTxt(G)}`;
    if(v.estado==='ok')h+=` y vendiste ${Math.abs(Math.round(v.dv*100))} % ${v.dv<0?'menos':'más'}: por cada S/ 100 vendidos, S/ ${entero(100*v.rn)} contra S/ ${entero(100*v.ra)}`;
    h+='.';if(q)h+=` Los mismos productos costaron ${q}${t.ep>0&&t.ev<0&&t.paasche>0&&t.laspeyres>0?': subió el precio y bajó la cantidad.':'.'}`;
    if(v.estado==='pendiente')h+=' Cargando la venta…';return h;}
  // La lista de cada indicador: filas ya hechas por `calcular`, el orden que eligió el usuario y sus columnas.
  function listaDe(G,prods){const{D,s}=G,por=s.agrupar,q=normal(s.q),busca=r=>!q||normal(r.item).includes(q);let filas,medida,defecto;
    if(s.kpi==='precio'){filas=D.precio;medida='ep';}
    else if(s.kpi==='cantidad'){filas=D.volumen;medida='ev';}
    else if(s.kpi==='carta'){const lado=s.lado||'dej';medida=lado;filas=juntar(lado==='dej'?D.dejados:lado==='nue'?D.nuevos:prods.filter(r=>r.clase==='otro'&&busca(r)),por);defecto=(a,b)=>Math.abs(b[medida])-Math.abs(a[medida]);}
    else{filas=D.tabla;medida='delta';}
    const id=`${s.kpi}|${s.kpi==='carta'?s.lado||'dej':s.kpi==='precio'?s.sentido.precio:s.sentido.volumen}|${por}`,o=s.orden?.id===id?s.orden:null;
    const valor=(r,k)=>k==='cambioP'?(r.pa>0&&r.pn!=null?r.pn/r.pa-1:null):k==='cambioQ'?(r.qa>0?r.q/r.qa-1:null):r[k];
    filas=[...filas];if(o)filas.sort((a,b)=>{const x=valor(a,o.k),y=valor(b,o.k);if(x==null)return y==null?0:1;if(y==null)return-1;return(typeof x==='string'?cmp(x,y):x-y)*o.d;});else if(defecto)filas.sort(defecto);
    return{id,filas,medida,o,valor};}
  function columnas(G,medida){const{s}=G,gr=s.agrupar!=='Producto',base=nombreBase(G),amp=s.amp==='izq',lado=s.lado||'dej';
    const C=(k,t,w,f,cl,tip='')=>({k,t,w,f,cl,tip}),cV=C('v','Este período','w-x',r=>fS(r.v)),cA=C('va',base,'w-x',r=>fS(r.va));
    if(gr)return[C('n','Productos','w-x',r=>n0.format(r.n)),C(medida,s.kpi==='compra'?'Diferencia':'Impacto','w-im',r=>fD(r[medida]),r=>medida==='ep'?rojoVerde(r.ep):'')];
    if(s.kpi==='precio')return[C('pa','Antes','w-pr',r=>f2(r.pa)),C('pn','Ahora','w-pr',r=>f2(r.pn)),C('cambioP','%','w-pc',r=>fP(r.pn/r.pa-1),r=>rojoVerde(r.ep)),C('ep','Impacto','w-im',r=>fD(r.ep),r=>rojoVerde(r.ep),'Cambio de precio × la cantidad promedio de los dos períodos'),...(amp?[cV,cA]:[])];
    if(s.kpi==='cantidad')return[C('qa','Antes','w-x',r=>`${fQ(r.qa)} ${r.um.toLowerCase()}`),C('q','Ahora','w-x',r=>`${fQ(r.q)} ${r.um.toLowerCase()}`),C('cambioQ','%','w-pc',r=>fP(r.q/r.qa-1)),C('ev','Impacto','w-im',r=>fD(r.ev),null,'Lo que cambió el gasto por comprar más o menos, a precio promedio'),...(amp?[cV,cA]:[])];
    if(s.kpi==='carta')return lado==='dej'?[C('va',`Se compró en ${baseMin(G)}`,'w-xx',r=>fS(r.va))]:lado==='nue'?[C('v','Se compró ahora','w-xx',r=>fS(r.v))]:[cA,cV,C('otr','Efecto','w-im',r=>fD(r.otr))];
    return[cV,cA,C('delta','Dif.','w-im',r=>fD(r.delta)),C('pct','%','w-pc',r=>r.pct==null?'—':fP(r.pct/100)),C('ep','Precio','w-im',r=>r.clase==='ambos'?fD(r.ep):'—',r=>rojoVerde(r.ep)),C('ev','Cantidad','w-im',r=>r.clase==='ambos'?fD(r.ev):'—'),...(amp?[C('motivo','Motivo','w-mo',r=>esc(r.motivo),()=>'vap-mo')]:[])];}
  function tablaHtml(G,L){const{s}=G,cols=columnas(G,L.medida),vis=L.filas,o=L.o,gr=s.agrupar!=='Producto',flecha=k=>o?.k===k?(o.d>0?' ↑':' ↓'):'';
    G.lista={L,cols};
    const th=c=>`<th class="${c.w}" title="${esc(c.tip)}"><button data-a="orden" data-v="${c.k}">${esc(c.t)}${flecha(c.k)}</button></th>`;
    const tot=c=>['v','va','delta','ep','ev','dej','nue','otr'].includes(c.k)?(()=>{const x=sum(vis,c.k);return`<td class="${c.k==='ep'?rojoVerde(x):''}">${c.k==='v'||c.k==='va'?fS(x):fD(x)}</td>`;})():'<td></td>';
    return`<div class="vap-wrap" data-tabla="lista"><table><thead><tr><th class="i"><button data-a="orden" data-v="item">${esc(gr?s.agrupar:'Producto')}${flecha('item')}</button></th>${cols.map(th).join('')}</tr></thead><tbody><tr class="tot"><td class="i">Total · ${gr?`${n0.format(vis.length)} ${vis.length===1?'grupo':'grupos'}`:nP(vis.length)}</td>${cols.map(tot).join('')}</tr>${filasHtml(G,0,s.lim)}</tbody></table>${vis.length?'':'<p class="vap-vacio">Nada que mostrar con estos filtros.</p>'}</div>`;}
  function filasHtml(G,a,b){const{L,cols}=G.lista,{s}=G;return L.filas.slice(a,b).map(r=>`<tr class="${!r.grupo&&r.item===s.sel?'on':''}"><td class="i" title="${esc(r.grupo?r.item:[r.item,[r.sub,r.fam].filter(Boolean).join(' · ')].join(' · '))}"><button class="vap-tn" data-a="${r.grupo?'grupo':'item'}" data-v="${esc(r.item)}">${esc(r.item)}</button></td>${cols.map(c=>`<td class="${c.cl?c.cl(r):''}${c.k===L.medida?' fuerte':''}">${c.f(r)}</td>`).join('')}</tr>`).join('');}
  function puntosMes(G,T){const{P,D,s}=G,vm=P.venta||{},par=P.parcial?.[0],vta=s.medir==='venta';
    return D.V.meses.map((m,i)=>{const x=T.porMes[m]||totales([]),b=D.V.base[i],ok=m!==par&&vm[m]>0&&vm[b]>0;return{m,b,x,a:vta?(ok?100*x.v/vm[m]:null):x.v,c:vta?(ok?100*x.va/vm[b]:null):x.va};});}
  function barrasHtml(G,T){const{P,D,s}=G,pts=puntosMes(G,T);G.pts=pts;const tope=Math.max(1e-9,...pts.flatMap(p=>[p.a||0,p.c||0])),rot=pts.length<=8,vta=s.medir==='venta',par=P.parcial?.[0];
    const cols=pts.map((p,i)=>{const h=Math.max(0,(p.a||0)/tope*88),gh=Math.max(0,(p.c||0)/tope*88),on=!D.meses.length||D.meses.includes(p.m);
      return`<button class="vap-col${on?'':' dim'}${D.meses.includes(p.m)?' foco':''}" data-a="mes" data-v="${p.m}" data-i="${i}" aria-label="${esc(etq(P,p.m))}">${p.c>0?`<i class="g" style="height:${gh.toFixed(2)}%"></i>`:''}<i class="s${p.m===par&&!vta?' par':''}" style="height:${h.toFixed(2)}%"></i>${rot&&p.a!=null?`<span class="rot" style="bottom:${(h+1).toFixed(2)}%">${esc(vta?`S/ ${Math.round(p.a)}`:fK(p.a))}</span>`:''}</button>`;}).join('');
    return`<div class="vap-plot" data-plot="mes">${cols}<div class="vap-tip" hidden></div></div><div class="vap-ejes">${pts.map(p=>`<span>${esc(etq(P,p.m))}${p.m===par?'*':''}</span>`).join('')}</div>`;}
  function tipMes(G,i){const{P,s}=G,p=G.pts?.[i];if(!p)return'';const x=p.x,base=nombreBase(G),f=(n,v)=>`<span><i>${esc(n)}</i>${esc(v)}</span>`,par=p.m===P.parcial?.[0]?'*':'';
    if(s.medir==='venta')return`<b>${esc(etq(P,p.m))}${par} · ${p.a==null?'sin venta del mes completo':`S/ ${Math.round(p.a)} por S/ 100`}</b>${f(`${base} (${etq(P,p.b)})`,p.c==null?'—':`S/ ${Math.round(p.c)}`)}${f('Venta del mes',fS(P.venta?.[p.m]))}${f('Compra del mes',fS(x.v))}`;
    return`<b>${esc(etq(P,p.m))}${par} · ${esc(fS(x.v))}</b>${f(`${base} (${etq(P,p.b)})`,fS(x.va))}${f('Diferencia',`${fD(x.delta)} · ${x.pct==null?'—':fP(x.pct/100)}`)}${f('Precio',fD(x.ep))}${f('Cantidad',fD(x.ev))}${f('Dejados y nuevos',fD(cartaDe(x)))}`;}
  function fichaHtml(G,P1,T){const{P,s,D}=G,base=nombreBase(G),um=P1.um.toLowerCase(),por=new Map(T.pares.filter(r=>r.p===P1.p).map(r=>[r.mes,r]));
    const mag=(r,ant)=>{if(!r)return null;const v=ant?r.va:r.v,q=ant?r.qa:r.q;return s.magn==='Cantidad'?q:s.magn==='Precio'?(q>0?v/q:null):v;};
    const tope=Math.max(1e-9,...T.meses.flatMap(m=>{const r=por.get(m);return[mag(r)||0,mag(r,true)||0];})),enR=new Set(D.meses.length?D.meses:D.V.meses),n=T.meses.length,par=P.parcial?.[0];
    G.ficha={T,por,mag,fmt:v=>v==null?'—':s.magn==='Cantidad'?`${fQ(v)} ${um}`:s.magn==='Precio'?`S/ ${f2(v)}`:fS(v)};
    const cols=T.meses.map((m,i)=>{const r=por.get(m),a=mag(r),b=mag(r,true);return`<div class="vap-col sinclic" data-i="${i}">${b>0?`<i class="g" style="height:${(b/tope*90).toFixed(2)}%"></i>`:''}<i class="s${m===par?' par':''}${enR.has(m)?'':' fuera'}" style="height:${(Math.max(0,a||0)/tope*90).toFixed(2)}%"></i></div>`;}).join('');
    const cif=(r,v,d,c='')=>`<div class="vap-cf"><span>${esc(r)}</span><b class="${c}">${esc(v)}</b><small>${esc(d)}</small></div>`,ambos=P1.clase==='ambos',cp=P1.pa>0&&P1.pn!=null?P1.pn/P1.pa-1:null,cq=P1.qa>0?P1.q/P1.qa-1:null;
    const fr=ambos?(Math.abs(P1.ep)>=Math.abs(P1.ev)?`Lo que más pesa es el precio: ${P1.ep>0?'subió':'bajó'} ${fP(cp).replace(/[+−]/,'')}, ${fD(P1.ep)}. La cantidad movió ${fD(P1.ev)}.`:`Lo que más pesa es la cantidad: se compró ${P1.ev<0?'menos':'más'} (${fP(cq)}), ${fD(P1.ev)}. El precio movió ${fD(P1.ep)}.`)
      :P1.clase==='nuevo'?`No se compró en ${baseMin(G)}: los ${fS(P1.v)} son todos nuevos.`:P1.clase==='dejado'?`En ${baseMin(G)} se compraron ${fS(P1.va)} y en este período nada.`:'Con cantidad cero o negativa en un lado (notas de crédito o ajustes): no se puede partir en precio y cantidad.';
    return`<div class="vap-fcab"><div class="vap-ftit"><span class="vap-miga">${esc([P1.fam,P1.sub].filter(Boolean).join(' › '))}</span><h3 title="${esc(P1.item)}">${esc(P1.item)}</h3><span class="vap-miga">${esc(ambos?'Comprado en los dos períodos':P1.clase==='nuevo'?`Nuevo: no se compró en ${baseMin(G)}`:P1.clase==='dejado'?'Se dejó de comprar':'Sin cantidad comparable')}</span></div><button class="vap-pil" data-a="amp" data-v="panel">${s.amp==='panel'?'Ver la lista':'Ampliar'}</button><button class="vap-quita" data-a="soltar">Soltar</button></div>
      <div class="vap-cifras">${cif('Compra',fS(P1.v),`antes ${fS(P1.va)}`)}${cif('Precio',P1.pn!=null?`S/ ${f2(P1.pn)}`:'—',P1.pa!=null?`antes S/ ${f2(P1.pa)} · ${fP(cp)}`:'',rojoVerde(P1.ep))}${cif('Cantidad',`${fQ(P1.q)} ${um}`,`antes ${fQ(P1.qa)} ${um}`)}${cif('Diferencia',fD(P1.delta),ambos?`precio ${fD(P1.ep)} · cantidad ${fD(P1.ev)}`:'')}</div>
      <p class="vap-frase">${esc(fr)}</p><div class="vap-fl"><div class="vap-seg" role="group" aria-label="Qué medir">${['Soles','Cantidad','Precio'].map(m=>`<button class="${s.magn===m?'on':''}" data-a="magn" data-v="${m}" aria-pressed="${s.magn===m}">${m}</button>`).join('')}</div><span class="vap-sub">13 meses · oscuro: el rango</span><span class="vap-esp"></span><span class="vap-ley"><i></i> ${esc(baseMin(G))}</span></div>
      <div class="vap-plot chica${s.amp==='panel'?' grande':''}" data-plot="ficha">${cols}<div class="vap-tip" hidden></div></div><div class="vap-ejes chicos">${T.meses.map((m,i)=>`<span>${i%2===(n-1)%2?esc((P.etq_meses||[])[+m.slice(5)-1]||''):''}</span>`).join('')}</div>`;}
  function tipFicha(G,i){const F=G.ficha,{P}=G;if(!F)return'';const m=F.T.meses[i],r=F.por.get(m),f=(n,v)=>`<span><i>${esc(n)}</i>${esc(v)}</span>`;
    return`<b>${esc(etq(P,m))}</b>${f('Este período',F.fmt(F.mag(r)))}${f(`${nombreBase(G)} (${etq(P,F.T.base[i])})`,F.fmt(F.mag(r,true)))}`;}
  function cascadaHtml(G,t){const{s}=G,base=nombreBase(G),carta=cartaDe(t),sube='var(--vap-sube)',baja='var(--vap-baja)',neu='var(--vap-tono)';
    const pasos=[{n:base,d:0,h:t.va,tot:'g'},{n:'Precio',d:t.va,h:t.va+t.ep,k:'precio',col:t.ep>=0?sube:baja,val:t.ep},{n:'Cantidad',d:t.va+t.ep,h:t.va+t.ep+t.ev,k:'cantidad',col:neu,val:t.ev},{n:'Dejados y nuevos',d:t.va+t.ep+t.ev,h:t.v,k:'carta',col:neu,val:carta},{n:'Este período',d:0,h:t.v,tot:'a'}];
    const top=Math.max(1e-9,...pasos.flatMap(p=>[p.d,p.h]));
    return`<div class="vap-casc">${pasos.map(p=>{const lo=Math.min(p.d,p.h),hi=Math.max(p.d,p.h),y=lo/top*84,h=Math.max(.8,(hi-lo)/top*84),col=p.tot==='g'?'var(--vap-gris)':p.tot==='a'?'var(--accent)':p.col;
      return`<${p.k?`button data-a="kpi" data-v="${p.k}"`:'div'} class="vap-cp${p.k&&s.kpi===p.k?' on':''}" title="${esc(`${p.n}: ${p.tot?fS(p.h):fD(p.val)}`)}"><i style="bottom:${y.toFixed(2)}%;height:${h.toFixed(2)}%;background:${col}"></i><span class="val" style="bottom:${(y+h+1).toFixed(2)}%">${esc(p.tot?fK(p.h):fD(p.val).replace('S/ ',''))}</span></${p.k?'button':'div'}>`;}).join('')}</div><div class="vap-cascn">${pasos.map(p=>`<span>${esc(p.n)}</span>`).join('')}</div>`;}
  function panelHtml(G,t,prods,F){const{P,D,s}=G,TIT={compra:'Qué explica la diferencia',precio:'Qué pasó con el precio',cantidad:'Qué pasó con la cantidad',carta:'Dejados y nuevos'};
    const med={compra:x=>x.delta,precio:x=>x.ep,cantidad:x=>x.ev,carta:cartaDe}[s.kpi],pg=pagSet(P),fm=D.plan.mapas.Familia||{},todo=(G.cache.todo||[]).filter(r=>!D.meses.length||D.meses.includes(r.mes)),porF=grupos(todo,r=>fm[r.p]||'');
    const fams=[...porF].filter(([f])=>f).map(([f,rs])=>({f,t:totales(porProducto(rs,P,D.plan))})).filter(x=>Math.abs(x.t.v)>.005||Math.abs(x.t.va)>.005).sort((a,b)=>b.t.va-a.t.va||b.t.v-a.t.v);
    const fila=x=>`<button class="vap-fi${s.fam===x.f?' on':''}" data-a="fam" data-v="${esc(x.f)}"><span class="n" title="${esc(x.f)}">${esc(x.f)}</span><small>${esc(s.kpi==='compra'?fF(x.t.va>0?x.t.delta/x.t.va:null):s.kpi==='precio'?(x.t.paasche==null?'':fP(x.t.paasche)):s.kpi==='carta'?`${x.t.nDej} dejados · ${x.t.nNue} nuevos`:'')}</small><b class="${s.kpi==='precio'?rojoVerde(med(x.t)):''}">${esc(fD(med(x.t)))}</b></button>`;
    const ambito=`${s.sub||(s.fam===ALL?'Todas las compras':s.fam)} · ${rangoTxt(P,D.meses.length?D.meses:D.V.meses)}`;
    let h=`<div class="vap-fcab"><div class="vap-ftit"><span class="vap-miga">${esc(ambito)}</span><h3>${esc(TIT[s.kpi])}</h3><span class="vap-miga">${esc(`${fS(t.va)} → ${fS(t.v)} · ${fD(t.delta)} (${t.pct==null?'—':fP(t.pct/100)})`)}</span></div></div><p class="vap-frase">${esc(fraseDe(G,t,prods))}</p>`;
    if(s.kpi==='compra')h+=cascadaHtml(G,t);
    const titF=s.kpi==='compra'?'Por familia':s.kpi==='precio'?'Precio, por familia':s.kpi==='cantidad'?'Cantidad, por familia':'Dejados y nuevos, por familia';
    h+=`<div class="vap-bloque">${titF}</div><div class="vap-lista" data-lista="panel">${fams.map(fila).join('')}`;
    if(s.kpi==='carta'&&D.reemplazos.length)h+=`<div class="vap-bloque" style="margin:8px 0 2px">Dónde se reemplazó</div>${D.reemplazos.map(r=>`<button class="vap-fi" data-a="subf" data-v="${esc(r.sub)}" title="${esc(`${r.nd} dejados ${fD(r.dej)} · ${r.nn} nuevos ${fD(r.nue)}`)}"><span class="n">${esc(r.sub)}</span><small>${r.nd} dejados · ${r.nn} nuevos</small><b>${esc(fD(r.dej+r.nue))}</b></button>`).join('')}`;
    h+='</div>';
    if(s.kpi==='compra'&&F.fuera.length){const a=sum(F.fuera,'v'),b=sum(F.fuera,'va');if(Math.abs(a)>.5||Math.abs(b)>.5)h+=`<div class="vap-fuera"><span>Fuera de esta cuenta: ${esc(fS(a))} de ${esc(F.fuera.slice(0,2).map(x=>x.f).join(', '))}${F.fuera.length>2?'…':''} (${esc(baseMin(G))}: ${esc(fS(b))})</span><button class="vap-quita" data-a="sumar">Sumarlas</button></div>`;}
    return h;}
  function menuFamilias(G,F){const{P,s}=G,pa=P.pagina;if(!pa?.todas?.length)return'';const el=new Set(pa.elegidas),n=pa.elegidas.length||pa.todas.length,ab=s.menu==='fam';
    return`<div class="vap-ms"><button class="vap-pil" data-a="menu" data-v="fam" aria-expanded="${ab}">${n===pa.todas.length?'Todas las familias':`Familias: ${n} de ${pa.todas.length}`} ▾</button>${ab?`<div class="vap-pop">${[...pa.todas].sort((a,b)=>(F.por.get(b[1])||0)-(F.por.get(a[1])||0)).map(([r,nom])=>`<label><input type="checkbox" data-a="pfam" value="${esc(r)}"${el.has(r)||!el.size?' checked':''}><span>${esc(nom)}</span><small>${esc(fS(F.por.get(nom)||0))}</small></label>`).join('')}<p>Vale para todas las vistas de Compras.</p></div>`:''}</div>`;}
  function pasarFecha(G){const fb=document.querySelector('.st-key-cp_vap_nativa_fecha'),lg=G.root.querySelector('.vap-lugar');if(!fb||!fb.offsetWidth||!lg)return;
    const w=`${fb.offsetWidth+8}px`;if(G.root.style.getPropertyValue('--vap-fecha')!==w)G.root.style.setProperty('--vap-fecha',w);
    const padre=fb.offsetParent;if(!padre||!lg.offsetWidth)return;const x=`${Math.round(lg.getBoundingClientRect().left-padre.getBoundingClientRect().left)}px`;if(fb.style.left!==x)fb.style.left=x;}
  function dibujar(G){const{P,s,root}=G;const D=G.D=calcular(P,{...s,foco:null,modo:'Valor',corte:'Por qué',detalleMeses:true,cobertura:'Todos'},G.cache);s.meses=D.meses;
    const active=root.querySelector('input[type=search]:focus'),f=active?[active.selectionStart,active.selectionEnd]:null,y=root.querySelector('.vap-wrap')?.scrollTop||0,yl=root.querySelector('.vap-lista')?.scrollTop||0;
    const V=D.V,tituloC=s.contra==='aa'?'Compras vs año pasado':s.contra==='aa2'?'Compras vs hace dos años':s.contra==='ant'?'Compras vs período anterior':`Compras vs desde ${etq(P,String(s.contra).slice(2))}`;
    const F=fueraDePagina(P,D,G.cache);
    let html=`<div class="vap-cab"><h2 class="vap-tit">${esc(tituloC)}</h2><span class="vap-lugar" aria-hidden="true"></span>${menuFamilias(G,F)}<select class="vap-men" data-select="contra" aria-label="Contra qué período">${opcionesContra(G)}</select><span class="vap-esp"></span><input class="vap-busca" type="search" data-input="q" placeholder="Buscar producto…" aria-label="Buscar producto" value="${esc(s.q)}"><button class="vap-pil" data-a="excel" ${!D.g.length?'disabled':''} title="Baja lo que se ve">Excel ↓</button></div>`;
    if(!V.meses.length){const base=baseMin(G);root.innerHTML=html+`<p class="vap-vacio">No hay meses para comparar: ${V.n?`el rango termina antes de ${esc(etq(P,V.piso))}, el primer mes con ${esc(base)} en los datos`:'el rango elegido no tiene compras'}. Probá con otra fecha u otro «Contra».</p>`;pasarFecha(G);return;}
    const T=trece(P,s,D,G.cache),t=D.totC,prods=porProducto(D.gc,P,D.plan),P1=s.sel!=null?prods.find(r=>r.item===s.sel)||null:null;if(!P1){s.sel=null;if(s.amp==='panel')s.amp=null;}
    const verIzq=s.amp!=='panel',verPanel=s.amp!=='izq',L=listaDe(G,prods),par=P.parcial?.[0],base=baseMin(G);
    const nS=prods.filter(r=>r.clase==='ambos'&&r.ep>.5).length,nB=prods.filter(r=>r.clase==='ambos'&&r.ep<-.5).length,nM=prods.filter(r=>r.clase==='ambos'&&r.ev<-.5).length,nM2=prods.filter(r=>r.clase==='ambos'&&r.ev>.5).length,nO=prods.filter(r=>r.clase==='otro').length;
    const SENT={precio:[['sube',`Subieron · ${nS}`],['baja',`Bajaron · ${nB}`]],cantidad:[['baja',`Se compró menos · ${nM}`],['sube',`Se compró más · ${nM2}`]],carta:[['dej',`Dejaron · ${t.nDej}`],['nue',`Nuevos · ${t.nNue}`],...(nO?[['otr',`Sin cantidad · ${nO}`]]:[])]}[s.kpi]||[];
    const actSent=s.kpi==='precio'?s.sentido.precio:s.kpi==='cantidad'?s.sentido.volumen:s.lado||'dej';
    const chips=[...D.meses.map(m=>`<button class="vap-quita" data-a="quita-mes" data-v="${m}">${esc(etq(P,m))}${m===par?'*':''} ✕</button>`),...(s.fam!==ALL?[`<button class="vap-quita" data-a="quita-fam">${esc(s.fam)} ✕</button>`]:[]),...(s.sub?[`<button class="vap-quita" data-a="quita-sub">${esc(s.sub)} ✕</button>`]:[])].join('');
    html+=`<div class="vap-kpis">${kpisHtml(G,t,T)}</div><div class="vap-cuerpo" data-amp="${s.amp||''}">`;
    if(verIzq){const graf=s.zona==='graf',vta=s.medir==='venta';
      html+=`<section class="vap-izq"><div class="vap-fl"><div class="vap-seg" role="group" aria-label="Qué mirar">${[['graf','Gráfico'],['prod',SENT.length?'Productos':`Productos · ${n0.format(L.filas.length)}`]].map(([k,x])=>`<button class="${s.zona===k?'on':''}" data-a="zona" data-v="${k}" aria-pressed="${s.zona===k}">${esc(x)}</button>`).join('')}</div>`
        +(!graf&&SENT.length?`<div class="vap-seg" role="group" aria-label="Cuáles">${SENT.map(([k,x])=>`<button class="${actSent===k?'on':''}" data-a="sent" data-v="${k}" aria-pressed="${actSent===k}">${esc(x)}</button>`).join('')}</div>`:'')+chips+'<span class="vap-esp"></span>'
        +(graf?`<select class="vap-men" data-select="medir" aria-label="Qué medir"><option value="soles"${vta?'':' selected'}>Medir: Soles</option><option value="venta"${vta?' selected':''}>Medir: por S/ 100 vendidos</option></select>`:`<select class="vap-men" data-select="agrupar" aria-label="Ver por">${D.grupos.map(g=>`<option value="${esc(g)}"${s.agrupar===g?' selected':''}>Ver por: ${esc(g)}</option>`).join('')}</select>`)
        +`<button class="vap-pil" data-a="amp" data-v="izq">${s.amp==='izq'?'Ver la ficha':'Ampliar'}</button></div>`;
      if(graf){const hayPar=V.meses.includes(par);
        html+=`<div class="vap-fl"><span class="vap-sub"><b>${vta?'Compra por cada S/ 100 vendidos':'Compra por mes'}</b> · ${vta?'cálculo propio: no es el costo de ventas':`sin IGV${hayPar?` · * hasta el día ${P.parcial[1]}, en los dos lados`:''}`}</span><span class="vap-esp"></span><span class="vap-ley"><i></i> ${esc(base)}</span></div>${barrasHtml(G,T)}<p class="vap-nota">${V.antes?`${V.antes} ${V.antes===1?'mes del rango no tiene':'meses del rango no tienen'} ${esc(base)} en los datos y no se comparan. `:''}${vta?(P.venta==null?'Cargando la venta…':'Sólo meses completos con venta en los dos lados.'):'Un clic en un mes explica sólo ese mes; Mayús + clic suma varios. Cada mes se parte contra su espejo: mes a mes el precio no suma exacto lo del período.'}</p>`;
      }else html+=`${tablaHtml(G,L)}<p class="vap-nota">${s.kpi==='precio'?'Impacto = cambio de precio × cantidad promedio de los dos períodos: no depende de cuál se tome de base.':s.kpi==='cantidad'?'Los mismos productos, comprados en los dos períodos. Cada uno en su unidad de compra: no se suman kilos con unidades.':s.kpi==='carta'?'Se empareja por nombre: un producto que cambió de nombre aparece en los dos lados.':'Precio y cantidad sólo existen si el producto se compró en los dos períodos.'}</p>`;
      html+='</section>';}
    if(verPanel)html+=`<aside class="vap-panel" aria-label="Ficha">${P1?fichaHtml(G,P1,T):panelHtml(G,t,prods,F)}</aside>`;
    root.innerHTML=html+'</div>';
    const w=root.querySelector('.vap-wrap');if(w)w.scrollTop=y;const li=root.querySelector('.vap-lista');if(li)li.scrollTop=yl;
    if(f){const e=root.querySelector('input[type=search]');if(e){e.focus({preventScroll:true});e.setSelectionRange(f[0],f[1]);}}
    pasarFecha(G);}
  function avisarFamilias(G){if(G.pagina){const v=G.pagina;G.pagina=null;G.enviar?.('familias',v);}}
  function montar({data:P,parentElement,setTriggerValue}){const old=window.__comprasAno;old?.abort.abort();let root=parentElement.querySelector('.vap');if(!root){root=document.createElement('div');root.className='vap';parentElement.appendChild(root);}
    const s=old?.s||inicial(P.inicial);
    if(s.fam!==ALL&&!(P.familias||[]).includes(s.fam))s.fam=ALL;if(s.sub&&!Object.values(P.mapas?.Subfamilia||{}).includes(s.sub))s.sub=null;if(s.agrupar!=='Producto'&&!(P.mapas||{})[s.agrupar])s.agrupar='Producto';
    const G={P,s,root,cache:{},abort:new AbortController(),enviar:setTriggerValue,pedido:old?.pedido||false};window.__comprasAno=G;const signal=G.abort.signal;
    root.addEventListener('click',e=>{const b=e.target.closest('[data-a]');if(!b||b.disabled||b.matches('input'))return;const{a,v}=b.dataset;
      if(a==='kpi'){s.kpi=v;if(v!=='compra')s.zona='prod';s.sel=null;s.amp=null;s.lim=150;s.orden=null;}
      else if(a==='zona')s.zona=v;
      else if(a==='sent'){if(s.kpi==='precio')s.sentido={...s.sentido,precio:v};else if(s.kpi==='cantidad')s.sentido={...s.sentido,volumen:v};else s.lado=v;s.lim=150;s.orden=null;}
      else if(a==='item'){s.sel=s.sel===v?null:v;if(s.amp==='izq')s.amp=null;}
      else if(a==='grupo'){if(s.agrupar==='Familia')s.fam=v;else s.sub=v;s.agrupar='Producto';s.orden=null;s.lim=150;}
      else if(a==='fam'){s.fam=s.fam===v?ALL:v;s.sub=null;s.sel=null;}
      else if(a==='subf'){s.sub=v;s.agrupar='Producto';s.zona='prod';s.lim=150;}
      else if(a==='quita-mes'){s.meses=s.meses.filter(m=>m!==v);}
      else if(a==='quita-fam'){s.fam=ALL;s.sub=null;}
      else if(a==='quita-sub')s.sub=null;
      else if(a==='mes'){if(e.shiftKey&&s.ancla){const ks=G.D.V.meses,i=ks.indexOf(s.ancla),j=ks.indexOf(v);s.meses=i>=0&&j>=0?ks.slice(Math.min(i,j),Math.max(i,j)+1):[v];}else{s.meses=s.meses.length===1&&s.meses[0]===v?[]:[v];s.ancla=v;}s.sel=null;}
      else if(a==='amp'){s.amp=s.amp===v?null:v;if(v==='izq')s.sel=null;}
      else if(a==='soltar'){s.sel=null;s.amp=null;}
      else if(a==='magn')s.magn=v;
      else if(a==='orden'){const id=listaDe(G,porProducto(G.D.gc,P,G.D.plan)).id,o=s.orden;s.orden={id,k:v,d:o?.id===id&&o.k===v?-o.d:v==='item'?1:-1};}
      else if(a==='menu')s.menu=s.menu===v?null:v;
      else if(a==='sumar'){const pa=P.pagina;pa.elegidas=pa.todas.map(x=>x[0]);G.pagina=pa.elegidas.slice();avisarFamilias(G);}
      else if(a==='excel'){bajar('Compras_vs_ano_pasado.xlsx',libro(exportar(G)));return;}
      else return;
      if(a==='menu'&&!s.menu)avisarFamilias(G);
      dibujar(G);
    },{signal});
    root.addEventListener('change',e=>{const t=e.target,k=t.dataset.select;
      if(k==='contra'){s.contra=t.value;s.meses=[];s.ancla=null;s.sel=null;}else if(k==='medir'){s.medir=t.value;s.zona='graf';}else if(k==='agrupar'){s.agrupar=t.value;s.orden=null;s.lim=150;}
      else if(t.dataset.a==='pfam'){const pa=P.pagina,el=pa.elegidas.length?pa.elegidas:pa.todas.map(x=>x[0]);pa.elegidas=t.checked?[...el,t.value]:el.filter(x=>x!==t.value);G.pagina=pa.elegidas.slice();G.cache={};s.fam=ALL;s.sub=null;}
      else return;dibujar(G);},{signal});
    root.addEventListener('input',e=>{if(e.target.dataset.input==='q'){s.q=e.target.value;s.zona='prod';s.lim=150;dibujar(G);}},{signal});
    root.addEventListener('scroll',e=>{const el=e.target;if(!el.matches?.('.vap-wrap')||!G.lista)return;if(el.scrollTop+el.clientHeight>=el.scrollHeight-160&&s.lim<G.lista.L.filas.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',filasHtml(G,s.lim,s.lim+150));s.lim+=150;}},{signal,capture:true});
    // El detalle al pasar el cursor, sin redibujar.
    root.addEventListener('pointermove',e=>{const pl=e.target.closest?.('[data-plot]');if(!pl)return;const col=e.target.closest('[data-i]'),tip=pl.querySelector('.vap-tip');if(!col){tip.hidden=true;return;}const i=+col.dataset.i;
      tip.innerHTML=pl.dataset.plot==='mes'?tipMes(G,i):tipFicha(G,i);tip.hidden=false;const bx=col.getBoundingClientRect(),bp=pl.getBoundingClientRect(),x=bx.left-bp.left+bx.width*.6;tip.style.left=`${Math.max(0,x+tip.offsetWidth>bp.width?x-tip.offsetWidth-8:x)}px`;},{signal});
    root.addEventListener('mouseout',e=>{const pl=e.target.closest?.('[data-plot]');if(pl&&!pl.contains(e.relatedTarget))pl.querySelector('.vap-tip').hidden=true;},{signal});
    document.addEventListener('pointerdown',e=>{if(!s.menu||e.composedPath().some(n=>n.classList?.contains('vap-ms')))return;s.menu=null;dibujar(G);avisarFamilias(G);},{signal});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&s.menu){s.menu=null;dibujar(G);avisarFamilias(G);}},{signal});
    dibujar(G);
    // La venta se pide después de dibujar: sin caché tarda, y las compras no la esperan.
    if(P.venta_pendiente&&P.venta==null&&typeof setTriggerValue==='function'&&!G.pedido){G.pedido=true;setTimeout(()=>{if(!signal.aborted)setTriggerValue('venta',Date.now());},120);}
    return()=>{G.abort.abort();};}
  return{montar,inicial,leer,ventana,emparejar,calcular,porProducto,agrupar,magnitud,exportar,dibujar,motivo,trece,totales,pagSet};
})();
window.__vapDatos=VAP;
export default function(component){return VAP.montar(component);}
