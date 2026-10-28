/* Compras › Vs año pasado (reglas #725 y #749). Python manda cada producto-mes
   una vez —lo comprado y, si el mes tuvo compras después del día del mes
   parcial, lo comprado hasta ese día—. El navegador arma las parejas contra
   el período de «Contra», parte la diferencia en precio, volumen, lo que se
   dejó de comprar y lo nuevo, y arma las fichas de familia y las listas. La
   fecha es el panel de meses de Python, puesto encima de la cabecera. */
const VAP=(()=>{
  const ALL='__todas__',MODOS=['Valor','Cantidad','Precio'];
  const TABS=[['precio','Subieron de precio'],['volumen','Se compró menos'],['cambio','Dejaron de comprarse y nuevos'],['todos','Todos']];
  const SENTIDOS={precio:[['sube','Subieron'],['baja','Bajaron']],volumen:[['baja','Se compró menos'],['sube','Se compró más']]};
  const CONTRAS=[['aa','el mismo período del año pasado',12],['aa2','el mismo período de hace dos años',24],['ant','el período anterior',null]];
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
    prodSerie:null,detalleMeses:false,cobertura:'Todos',orden:null,contra:'aa',tab:'precio',sentido:{precio:'sube',volumen:'baja'},...v};
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
  function calcular(P,s,cache={}){
    if(cache.P!==P){cache.P=P;cache.plan=leer(P);cache.key=null;}
    const plan=cache.plan,V=ventana(P,s),key=JSON.stringify([V.k,V.meses]);
    if(cache.key!==key){cache.key=key;cache.todo=emparejar(plan,V,P);cache.fams=null;}
    const famDe=plan.mapas.Familia||{},todo=cache.todo;
    if(!cache.fams){const m=new Map();for(const r of todo){const f=famDe[r.p]??'';if(!m.has(f))m.set(f,[]);m.get(f).push(r);}
      cache.fams=[...m].filter(([f])=>f).map(([fam,rs])=>({fam,v:sum(rs,'v'),va:sum(rs,'va')})).filter(f=>Math.abs(f.v)>.005||Math.abs(f.va)>.005)
        .sort((a,b)=>b.va-a.va||b.v-a.v||cmp(a.fam,b.fam));}
    const g=s.fam===ALL?todo:todo.filter(r=>famDe[r.p]===s.fam),prodsAll=porProducto(g,P,plan),tot=totales(prodsAll),venta=ventaRatio(P,V,g);
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
  function formato(v,t){if(t==='s')return soles(v);if(t==='ss')return ssol(v);if(t==='pct')return pct(v);if(t==='p')return precio(v);if(t==='q')return cant(v);if(t==='n')return v==null?'—':n0.format(v);return v??'';}
  function rangoTxt(P,ms){if(!ms.length)return'Sin meses';const ks=[...new Set(ms)].sort(),a=etq(P,ks[0]),b=etq(P,ks.at(-1));return a===b?a:`${a} – ${b}`;}
  function contraTxt(G){const{s,D,P}=G;if(s.contra==='aa')return'un año antes';if(s.contra==='aa2')return'dos años antes';
    if(s.contra==='ant')return'el período anterior';return rangoTxt(P,D.V.base);}
  function nombreBase(G){const s=G.s;return s.contra==='aa'?'Año pasado':s.contra==='aa2'?'Hace dos años':s.contra==='ant'?'Período anterior':'Base';}
  function opcionesContra(G){const{P,D,s}=G,ini=D.V.meses0[0],ops=CONTRAS.map(([k,n])=>`<option value="${k}" ${s.contra===k?'selected':''}>${esc(n)}</option>`);
    if(ini&&P.primero){const lo=num(P.primero),hasta=num(ini)-1,ms=[];for(let m=hasta;m>=lo;m--)ms.push(str(m));
      if(ms.length)ops.push(`<optgroup label="Desde otro mes">${ms.map(m=>`<option value="m:${m}" ${s.contra==='m:'+m?'selected':''}>${esc(`Desde ${etq(P,m)}`)}</option>`).join('')}</optgroup>`);}
    return ops.join('');}
  function seg(ops,v,a,extra=''){return`<div class="vap-seg" role="group">${ops.map(([x,t])=>`<button data-a="${a}" data-v="${esc(x)}" ${extra} class="${v===x?'on':''}" aria-pressed="${v===x}">${esc(t??x)}</button>`).join('')}</div>`;}
  function select(k,rot,ops,v,labels={}){const vs=ops.slice();if(v!=null&&!vs.includes(v))vs.push(v);return`<label>${esc(rot)}<select data-select="${k}" aria-label="${esc(rot)}">${vs.map(x=>`<option value="${esc(x)}" ${x===v?'selected':''}>${esc(labels[x]??x)}</option>`).join('')}</select></label>`;}
  function kpi(l,v,sub,cls=''){return`<div class="vap-kpi"><span class="l">${l}</span><span class="v ${cls}">${v}</span><span class="s" title="${esc(sub.replace(/<[^>]+>/g,''))}">${sub}</span></div>`;}
  function frase(G){const{D,s}=G,t=D.tot,v=D.venta,inf=[t.paasche,t.laspeyres].filter(x=>x!=null).sort((x,y)=>x-y);
    let h=`Compraste <b>${soles(t.v)}</b>, <b class="${clase(t.delta)}">${pct(t.pct)}</b> que ${esc(contraTxt(G))} (${soles(t.va)}).`;
    if(v.estado==='ok')h+=` La venta de ${v.n===1?'ese mes':`los ${v.n} meses completos`} cambió <b>${pct(100*v.dv)}</b>: por cada S/ 100 vendidos compraste <b>S/ ${entero(100*v.rn)}</b>${s.fam===ALL?'':` de ${esc(s.fam.toLowerCase())}`} (antes S/ ${entero(100*v.ra)}).`;
    if(inf.length){const[x,y]=[inf[0]*100,inf.at(-1)*100],r=Math.round(x)===Math.round(y)?pct(x):`${pct(x)} a ${pct(y)}`;h+=` Los mismos productos costaron <b class="${clase((x+y)/2)}">${r}</b>${x>=0?' más':y<=0?' menos':''}.`;}
    return h;}
  function kpis(G){const{D,s}=G,t=D.tot,v=D.venta,inf=[t.paasche,t.laspeyres].filter(x=>x!=null).sort((x,y)=>x-y),base=nombreBase(G).toLowerCase();
    const venta=v.estado==='ok'?kpi('Vendiste',pct(100*v.dv),`${v.n} ${v.n===1?'mes completo':'meses completos'} · ${soles(v.vn)}`)
      :kpi('Vendiste','—',v.estado==='pendiente'?'cargando la venta…':v.estado==='sinmeses'?'sin meses completos con venta en los dos lados':'sin dato de venta');
    const ratio=v.estado==='ok'?kpi('Compra por S/ 100 vendidos',`S/ ${entero(100*v.rn)}`,`${base}: S/ ${entero(100*v.ra)} · cálculo propio`):kpi('Compra por S/ 100 vendidos','—','cálculo propio');
    const r=inf.length?(Math.round(inf[0]*100)===Math.round(inf.at(-1)*100)?pct(inf[0]*100):`${pct(inf[0]*100)} a ${pct(inf.at(-1)*100)}`):'—';
    return[kpi('Compraste',soles(t.v),`${pct(t.pct)} · ${base}: ${soles(t.va)}`,clase(t.delta)),venta,ratio,
      kpi('Mismos productos',r,`precio de ${n0.format(t.nAmbos)} productos comprados en los dos`,inf.length?clase(inf[0]*100+inf.at(-1)*100):''),
      kpi('Productos que cambiaron',`${n0.format(t.nDej)} · ${n0.format(t.nNue)}`,'dejaron de comprarse · nuevos')].join('');}
  function fichas(G){const{D,s}=G,fs=[{fam:ALL,...D.todoTot},...D.familias];
    return fs.map(f=>{const x=f.va>0?100*(f.v-f.va)/f.va:null;return`<button data-a="fam" data-v="${esc(f.fam)}" class="${s.fam===f.fam?'on':''}" aria-pressed="${s.fam===f.fam}">${esc(f.fam===ALL?'Todas':f.fam)}<small class="${clase(f.v-f.va)}">${x==null?'nueva':pct(x)}</small></button>`;}).join('');}
  function tabla(G,id,cols,rs,accion=''){
    let filas=rs.slice();const o=G.s.orden;
    if(o?.id===id)filas.sort((a,b)=>{const x=a[o.k],y=b[o.k];if(x==null)return y==null?0:1;if(y==null)return-1;return(typeof x==='number'&&typeof y==='number'?x-y:cmp(String(x),String(y)))*o.d;});
    G.tablas[id]={cols,filas,accion,n:150};
    return`<div class="vap-scroll" data-tabla="${id}" tabindex="0"><table><thead><tr>${cols.map(col=>`<th class="${col.t&&col.t!=='txt'?'num':''}"><button data-a="orden" data-id="${id}" data-v="${col.k}">${esc(col.n)}${o?.id===id&&o.k===col.k?o.d===1?' ↑':' ↓':''}</button></th>`).join('')}</tr></thead><tbody>${rows(G,id,0,150)}</tbody></table>${filas.length?'':'<p class="vap-vacio">No hay filas para esta selección.</p>'}</div>`;}
  function celda(G,r,col){
    if(col.k==='item')return`<td><span class="vap-nom">${esc(r.item)}</span>${r.fam||r.sub?`<small>${esc([r.sub,r.fam].filter(Boolean).join(' · '))}</small>`:r.n>1?`<small>${n0.format(r.n)} productos</small>`:''}</td>`;
    if(col.k==='precios')return`<td class="num par">${r.pa==null?'—':`<span>${precio(r.pa)} →</span> <span>${precio(r.pn)}</span>`}${r.um?`<small>por ${esc(r.um.toLowerCase())}</small>`:''}${r.pa>0?`<small class="vap-pct-movil ${clase(r.ep)}">${pct(100*(r.pn/r.pa-1))}</small>`:''}</td>`;
    if(col.k==='cants')return`<td class="num par"><span>${cant(r.qa)} →</span> <span>${cant(r.q)}</span>${r.um?`<small>${esc(r.um.toLowerCase())}</small>`:''}${r.qa>0?`<small class="vap-pct-movil">${pct(100*(r.q/r.qa-1))}</small>`:''}</td>`;
    if(col.k==='cambioP')return`<td class="num ${clase(r.ep)}">${r.pa>0?pct(100*(r.pn/r.pa-1)):'—'}</td>`;
    if(col.k==='cambioQ')return`<td class="num">${r.qa>0?pct(100*(r.q/r.qa-1)):'—'}</td>`;
    // Precio y volumen sólo existen para un producto comprado en los dos períodos.
    if((col.k==='ep'||col.k==='ev')&&r.clase!=='ambos'&&r.clase!=='grupo')return'<td class="num">—</td>';
    const v=r[col.k],txt=formato(v,col.t),cls=['ep','ev','delta','nue','dej','otr'].includes(col.k)?clase(v):'';
    return`<td class="${col.t&&col.t!=='txt'?'num':''} ${cls}" title="${esc(txt)}">${col.k==='ep'||col.k==='ev'||col.k==='delta'?`<b>${esc(txt)}</b>`:esc(txt)}</td>`;}
  function rows(G,id,a,b){const t=G.tablas[id],D=G.D;return t.filas.slice(a,b).map(r=>`<tr ${t.accion?`data-a="${t.accion}" data-v="${esc(r.item)}" data-por="${esc(G.s.agrupar)}" tabindex="0"`:''} class="${r.item===D.foco&&D.focoPor===G.s.agrupar?'on':''}">${t.cols.map(col=>celda(G,r,col)).join('')}</tr>`).join('');}
  function colsTodos(G){const prod=G.s.agrupar==='Producto';return[c('item',G.s.agrupar,'txt'),c('v','Este año','s'),c('va',nombreBase(G),'s'),c('delta','Δ S/','ss'),c('pct','Δ %','pct'),c('ep','Precio','ss'),c('ev','Volumen','ss'),...(prod?[c('motivo','Motivo','txt')]:[c('n','Productos','n'),c('motivo','Lo que más pesa','txt')])];}
  function colsDetalleExcel(G){const prod=G.s.agrupar==='Producto';return[c('item',G.s.agrupar),...(prod?[c('sub','Subfamilia'),c('fam','Familia')]:[c('n','Productos')]),c('motivo','Motivo'),c('v','Valor este período'),c('va','Valor de la base'),c('delta','Δ S/'),c('pct','Δ %'),
    c('ep','Efecto precio'),c('ev','Efecto volumen'),c('dej','Dejaron de comprarse'),c('nue','Nuevos'),c('otr','Sin cantidad comparable'),...(prod?[c('um','Unidad'),c('q','Cantidad este período'),c('qa','Cantidad de la base'),c('pn','Precio este período'),c('pa','Precio de la base')]:[])];}
  function lista(G,rs,lado){if(!rs.length)return'<p class="vap-vacio">Ninguno en esta selección.</p>';
    return`<div class="vap-items" data-lista="${lado}">${rs.slice(0,G.listas?.[lado]||60).map(r=>`<button class="vap-item ${r.item===G.D.foco&&G.D.focoPor==='Producto'?'on':''}" data-a="foco" data-por="Producto" data-v="${esc(r.item)}"><span class="n">${esc(r.item)}</span><b class="${lado==='dej'?'baja':'sube'}">${ssol(lado==='dej'?-r.va:r.v)}</b><small>${esc([r.sub,r.fam].filter(Boolean).join(' · '))}</small></button>`).join('')}
      ${rs.length>(G.listas?.[lado]||60)?`<button class="vap-mas" data-a="mas" data-v="${lado}">Ver ${n0.format(Math.min(60,rs.length-(G.listas?.[lado]||60)))} más de ${n0.format(rs.length)}</button>`:''}</div>`;}
  function detalle(G){const{D,s}=G,prod=s.agrupar==='Producto';let h='';
    if(s.tab==='precio'){h+=`<div class="vap-tabctl">${seg(SENTIDOS.precio,s.sentido.precio,'sentido','data-tab="precio"')}<span class="vap-nota">${n0.format(D.precio.length)} ${prod?'productos':'grupos'} · ${ssol(sum(D.precio,'ep'))}</span></div>`;
      h+=tabla(G,'precio',prod?[c('item','Producto','txt'),c('precios','Precio antes → ahora','r'),c('cambioP','Cambio','r'),c('ep','Impacto','ss')]:[c('item',s.agrupar,'txt'),c('n','Productos','n'),c('ep','Impacto','ss')],D.precio,'foco');
      h+=`<p class="vap-nota">El impacto es el cambio de precio por la cantidad promedio de los dos períodos: no depende de cuál se tome de base. ${prod?'Un clic abre el producto arriba, con Valor | Cantidad | Precio.':'Un clic enfoca el grupo arriba.'}</p>`;}
    else if(s.tab==='volumen'){h+=`<div class="vap-tabctl">${seg(SENTIDOS.volumen,s.sentido.volumen,'sentido','data-tab="volumen"')}<span class="vap-nota">${n0.format(D.volumen.length)} ${prod?'productos':'grupos'} · ${ssol(sum(D.volumen,'ev'))}</span></div>`;
      h+=tabla(G,'volumen',prod?[c('item','Producto','txt'),c('cants','Cantidad antes → ahora','r'),c('cambioQ','Cambio','r'),c('ev','Impacto','ss')]:[c('item',s.agrupar,'txt'),c('n','Productos','n'),c('ev','Impacto','ss')],D.volumen,'foco');
      h+='<p class="vap-nota">Los mismos productos, comprados en los dos períodos, a precio promedio de los dos. La cantidad va en su unidad de compra: no se suman unidades distintas.</p>';}
    else if(s.tab==='cambio'){const dj=sum(D.dejados,'dej'),nu=sum(D.nuevos,'nue');
      h+=`<div class="vap-listas"><section><h4>Dejaron de comprarse · <span class="baja">${ssol(dj)}</span></h4><p class="vap-nota">${n0.format(D.dejados.length)} productos comprados en la base y no ahora.</p>${lista(G,D.dejados,'dej')}</section>
        <section><h4>Nuevos · <span class="sube">${ssol(nu)}</span></h4><p class="vap-nota">${n0.format(D.nuevos.length)} productos comprados ahora y no en la base.</p>${lista(G,D.nuevos,'nue')}</section>
        <section><h4>Dónde se reemplazó</h4><p class="vap-nota">Subfamilias con productos de los dos lados.</p>${D.reemplazos.length?`<div class="vap-reemp">${D.reemplazos.map(r=>`<div><span class="n">${esc(r.sub)}</span><span><span class="baja">${ssol(r.dej)}</span> · <span class="sube">${ssol(r.nue)}</span></span><small>${n0.format(r.nd)} dejados · ${n0.format(r.nn)} nuevos · neto ${ssol(r.dej+r.nue)}</small></div>`).join('')}</div>`:'<p class="vap-vacio">Ninguna subfamilia con productos de los dos lados.</p>'}</section></div>
        <p class="vap-nota">Suele ser un cambio de carta o de proveedor, no un ahorro. Se empareja por nombre, como siempre: un producto que cambió de nombre aparece en los dos lados.</p>`;}
    else{h+=`<div class="vap-tabctl">${select('cobertura','Registros',COBERTURAS,s.cobertura)}<label class="vap-check"><input type="checkbox" data-detallemeses ${s.detalleMeses?'checked':''}> Aplicar meses elegidos</label><span class="vap-nota">${n0.format(D.tabla.length)} filas</span></div>`;
      h+=tabla(G,'todos',colsTodos(G),D.tabla,'foco');
      h+='<p class="vap-nota">Precio y volumen se parten por producto antes de sumar familias. «Sólo actual/anterior» se refiere a registros, no a altas o bajas de productos. Clic en una fila para enfocarla; otro clic la suelta.</p>';}
    return h;}
  function dibujar(G){const{P,s,root}=G;G.D=calcular(P,s,G.cache);const D=G.D;G.tablas={};s.meses=D.meses;if(D.corte!=null)s.corte=D.corte;
    const active=root.querySelector('input:focus'),f=active?[active.dataset.input,active.selectionStart,active.selectionEnd]:null;
    const scroll=[...root.querySelectorAll('[data-tabla],[data-lista]')].map(e=>[e.dataset.tabla?'tabla':'lista',e.dataset.tabla||e.dataset.lista,e.scrollTop,e.scrollLeft]);
    const V=D.V,par=P.parcial&&V.meses.includes(P.parcial[0]),pctx=Object.entries(P.contexto||{}).filter(([,v])=>v.length).map(([k,v])=>v.length>2?`${v.length} ${k.toLowerCase()}`:`${k}: ${v.join(', ')}`);
    const ctxTitulo=Object.entries(P.contexto||{}).filter(([,v])=>v.length).map(([k,v])=>`${k}: ${v.join(', ')}`).join(' · ');
    const ctx=[V.meses.length?`Contra ${rangoTxt(P,V.base)}`:'',...pctx,par?`${etq(P,P.parcial[0])} hasta el día ${P.parcial[1]} en los dos lados`:''].filter(Boolean).join(' · ');
    const nombreFoco=D.foco==null?(s.fam===ALL?'Todas las compras':s.fam):D.foco,base=nombreBase(G);
    let html=`<section class="vap-card vap-top"><header class="vap-cab"><h3>Compras vs año pasado</h3><div class="vap-controles"><label>Contra<select data-select="contra" aria-label="Contra qué período">${opcionesContra(G)}</select></label><button data-a="excel" ${!D.g.length?'disabled':''}>Excel ↓</button></div></header>
      <p class="vap-ctx" title="${esc(ctxTitulo)}">${esc(ctx)}</p>`;
    if(!V.meses.length){html+=`<p class="vap-vacio">No hay meses para comparar: ${V.n?`el período elegido termina antes de ${esc(etq(P,V.piso))}, el primer mes con ${esc(base.toLowerCase())} en los datos`:'el período elegido no tiene compras'}. Probá con otra fecha u otro «Contra».</p></section>`;
      root.innerHTML=html;G.ro?.disconnect();return;}
    html+=`<p class="vap-frase">${frase(G)}</p><div class="vap-fams" role="group" aria-label="Familia">${fichas(G)}</div><div class="vap-kpis">${kpis(G)}</div>`;
    if(V.antes)html+=`<p class="vap-aviso">${n0.format(V.antes)} ${V.antes===1?'mes':'meses'} del período no ${V.antes===1?'tiene':'tienen'} ${esc(base.toLowerCase())} en los datos y no se comparan.</p>`;
    if(D.foco!=null){const pr=D.focoPor==='Producto'?D.productos[0]:null;html+=`<div class="vap-foco"><span>Viendo <b>${esc(D.foco)}</b>${pr?` <small>${esc([pr.sub,pr.fam].filter(Boolean).join(' · '))}</small>`:''}</span>${seg(MODOS.map(m=>[m,m]),D.modo,'modo')}${D.modo!=='Valor'&&D.focoPor!=='Producto'?select('prodSerie','Producto',D.productos.map(r=>r.item),D.referencia?.item||''):''}<button data-a="todo">× Volver al total</button></div>`;}
    const leyRatio=D.serie.some(r=>r.ratio!=null)?'<span class="r">Compra por cada S/ 100 vendidos</span>':'';
    html+=`<div class="vap-dos"><section class="vap-panel vap-serie"><header><h4>Mes a mes</h4><span class="vap-pista">Clic: explicar un mes · Mayús + clic: varios</span>${D.meses.length?'<button data-a="meses">Todos los meses</button>':''}</header>
      <div class="vap-chart"><svg role="img" aria-label="Compras de cada mes contra ${esc(base.toLowerCase())}"></svg></div>
      <div class="vap-ley"><span class="a">${esc(D.modo==='Valor'?'Este período':D.modo==='Cantidad'?`Cantidad${D.um?' en '+D.um.toLowerCase():''}`:`Precio${D.um?' por '+D.um.toLowerCase():''}`)}</span><span class="b">${esc(base)}</span>${leyRatio}${par?`<span>${esc(etq(P,P.parcial[0]))}: hasta el día ${P.parcial[1]}</span>`:''}</div></section>
      <section class="vap-panel vap-explica"><header><h4>Qué explica la diferencia</h4>${D.ops.length>1?seg(D.ops.map(o=>[o,o]),D.corte,'corte'):''}${D.modo==='Precio'?'':seg([['Cascada','Cascada'],['Tabla','Tabla']],s.vista,'vista')}</header>
      <p class="vap-ambito">${esc(nombreFoco)} · ${esc(D.meses.length?D.meses.map(m=>etq(P,m)).join(' · '):rangoTxt(P,V.meses))}</p>
      <div class="vap-resumen"><b class="${clase(D.delta)}">${esc(magnitudTexto(G,D.delta,true))}</b><span>${D.pct==null?'sin base para el %':pct(D.pct)}</span><span>${esc(magnitudTexto(G,D.b))} → ${esc(magnitudTexto(G,D.a))}</span></div>`;
    if(s.vista==='Tabla'||D.modo==='Precio'){const t=D.modo==='Cantidad'?'q':D.modo==='Precio'?'p':'s';
      html+=tabla(G,'mensual',[c('etq','Mes','txt'),c('actual','Este período',t),c('anterior',base,t),c('dif','Δ',t==='s'?'ss':t)],D.serie.map(r=>{const x=magnitud(r,D.modo),y=magnitud(r,D.modo,true);return{item:etq(P,r.mes),etq:etq(P,r.mes),actual:x,anterior:y,dif:x==null||y==null?null:x-y};}));}
    else html+='<div class="vap-waterfall"><svg role="img" aria-label="Qué explica la diferencia"></svg></div>';
    if(D.corte==='Por qué'&&D.modo==='Valor'&&s.vista!=='Tabla'){const t=D.totC;
      html+=`<div class="vap-casc-ley">${t.nAmbos?`<span><b>Precio ${ssol(t.ep)}</b>: el cambio de precio de ${n0.format(t.nAmbos)} ${t.nAmbos===1?'producto comprado':'productos comprados'} en los dos períodos, con la cantidad promedio de los dos.</span><span><b>${t.ev<0?'Se compró menos':'Se compró más'} ${ssol(t.ev)}</b>: la cantidad de esos mismos productos.</span>`:''}${t.nDej||t.nNue?`<span><b>${n0.format(t.nDej)} dejaron de comprarse ${ssol(t.dej)}</b> y <b>${n0.format(t.nNue)} ${t.nNue===1?'nuevo':'nuevos'} ${ssol(t.nue)}</b>: suele ser un cambio de carta o de proveedor.</span>`:''}${Math.abs(t.otr)>=.5?`<span><b>Sin cantidad comparable ${ssol(t.otr)}</b>: ${n0.format(t.nOtr)} productos con cantidad cero o negativa en un lado (notas de crédito, ajustes).</span>`:''}</div>`;}
    html+=`</section></div></section><section class="vap-card vap-detalle"><header><h3>Qué productos</h3><span class="vap-ctx">${esc(s.fam===ALL?'Todas las familias':s.fam)} · ${esc(s.detalleMeses&&D.meses.length?D.meses.map(m=>etq(P,m)).join(' · '):rangoTxt(P,V.meses))}</span>
      <div class="vap-detctl"><input data-input="q" type="search" aria-label="Buscar" placeholder="Buscar ${esc(s.agrupar==='Producto'?'producto':s.agrupar.toLowerCase())}…" value="${esc(s.q)}">${select('agrupar','Ver por',D.grupos,s.agrupar)}</div></header>
      <div class="vap-tabs" role="tablist">${TABS.map(([k,t])=>`<button role="tab" data-a="tab" data-v="${k}" aria-selected="${s.tab===k}" class="${s.tab===k?'on':''}">${esc(t)}</button>`).join('')}</div>
      <div class="vap-tabbody">${detalle(G)}</div></section>`;
    root.innerHTML=html;
    scroll.forEach(([t,id,top,left])=>{const e=root.querySelector(`[data-${t}="${id}"]`);if(e){e.scrollTop=top;e.scrollLeft=left;}});
    if(f){const e=root.querySelector(`[data-input="${f[0]}"]`);if(e){e.focus({preventScroll:true});e.setSelectionRange(f[1],f[2]);}}
    G.ro?.disconnect();G.ro=new ResizeObserver(()=>graficos(G));root.querySelectorAll('.vap-chart,.vap-waterfall').forEach(e=>G.ro.observe(e));graficos(G);}
  function magnitudTexto(G,v,firma=false){const D=G.D,u=D.um?D.um.toLowerCase():'unidad';if(v==null||!isFinite(v))return'—';
    if(D.modo==='Cantidad')return`${firma?signo(v):''}${cant(Math.abs(v))} ${u}`;if(D.modo==='Precio')return`${firma?signo(v):''}${precio(Math.abs(v))} / ${u}`;return firma?ssol(v):soles(v);}
  function eje(D,v){return D.modo==='Precio'?n2.format(v):D.modo==='Cantidad'?(Math.abs(v)>=10?n1:qf).format(v):milS(v);}
  function graficos(G){const D=G.D,P=G.P,box=G.root.querySelector('.vap-chart'),svg=box?.querySelector('svg');if(!svg)return;
    const W=box.clientWidth,H=box.clientHeight;if(W<80||H<65)return;svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('width',W);svg.setAttribute('height',H);
    if(!D.serie.length){svg.innerHTML='';return;}
    const linea=D.serie.filter(r=>r.ratio!=null),L=46,R=linea.length?30:8,T=16,B=24,pw=W-L-R,ph=H-T-B,n=D.serie.length;
    const vs=D.serie.flatMap(r=>[magnitud(r,D.modo),magnitud(r,D.modo,true)]).filter(v=>v!=null),hi=Math.max(1e-9,...vs)*1.12,lo=Math.min(0,...vs)*1.12,span=hi-lo||1,y=v=>T+(hi-v)/span*ph,bw=Math.max(1,Math.min(26,pw/n*.32)),cada=Math.max(1,Math.ceil(n/(pw/52)));
    let h='<defs><pattern id="vap-parcial" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)"><rect width="5" height="5" class="vap-actual"/><rect width="2" height="5" fill="var(--bg-card)" opacity=".5"/></pattern></defs>';
    for(let i=0;i<3;i++){const v=lo+span*i/2.24;h+=`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" class="vap-grid"/><text x="${L-6}" y="${y(v)+4}" text-anchor="end" class="vap-axis">${esc(eje(D,v))}</text>`;}
    D.serie.forEach((r,i)=>{const x=L+(i+.5)*pw/n,actual=magnitud(r,D.modo),anterior=magnitud(r,D.modo,true),on=!D.meses.length||D.meses.includes(r.mes),parc=D.parcial?.[0]===r.mes;h+=`<g opacity="${on?1:.28}">`;
      if(anterior!=null){const yy=y(anterior);h+=`<rect x="${x-bw-1}" y="${Math.min(yy,y(0))}" width="${bw}" height="${Math.max(1,Math.abs(y(0)-yy))}" rx="2" class="vap-aa"/>`;}
      if(actual!=null){const yy=y(actual);h+=`<rect x="${x+1}" y="${Math.min(yy,y(0))}" width="${bw}" height="${Math.max(1,Math.abs(y(0)-yy))}" rx="2" ${parc?'fill="url(#vap-parcial)"':'class="vap-actual"'}/>`;
        if(pw/n>64)h+=`<text x="${x+1+bw/2}" y="${Math.max(11,y(Math.max(actual,anterior??actual))-5)}" text-anchor="middle" class="vap-val">${esc(D.modo==='Valor'?milS(actual):eje(D,actual))}</text>`;}
      if(i%cada===0)h+=`<text x="${x}" y="${H-7}" text-anchor="middle" class="vap-axis">${esc(etq(P,r.mes))}${parc?' ·'+P.parcial[1]:''}</text>`;
      h+=`</g><rect data-a="mes" data-v="${r.mes}" x="${x-pw/n/2}" y="${T-10}" width="${pw/n}" height="${ph+10}" fill="transparent" role="button" tabindex="0" aria-label="${esc(etq(P,r.mes))}"><title>${esc(etq(P,r.mes))}: ${esc(magnitudTexto(G,actual))} · ${esc(nombreBase(G).toLowerCase())} (${esc(etq(P,r.base))}): ${esc(magnitudTexto(G,anterior))}${r.ratio!=null?` · S/ ${entero(r.ratio)} por cada S/ 100 vendidos`:''}</title></rect>`;});
    if(linea.length){const top=Math.max(...linea.map(r=>r.ratio))*1.3,yr=v=>T+(top-v)/top*ph,pts=D.serie.map((r,i)=>r.ratio==null?null:[L+(i+.5)*pw/n,yr(r.ratio)]).filter(Boolean);
      if(pts.length>1)h+=`<polyline class="vap-linea" points="${pts.map(p=>p.join(',')).join(' ')}"/>`;
      pts.forEach(p=>{h+=`<circle class="vap-punto" cx="${p[0]}" cy="${p[1]}" r="3"/>`;});
      const ul=linea.at(-1);h+=`<text x="${W-2}" y="${yr(ul.ratio)+4}" text-anchor="end" class="vap-axis vap-r">${entero(ul.ratio)}</text>`;}
    h+=`<line x1="${L}" x2="${W-R}" y1="${y(0)}" y2="${y(0)}" class="vap-cero"/>`;svg.innerHTML=h;
    const wb=G.root.querySelector('.vap-waterfall'),ws=wb?.querySelector('svg');if(!ws)return;const w=wb.clientWidth,hh=wb.clientHeight;if(w<80||hh<65)return;
    ws.setAttribute('viewBox',`0 0 ${w} ${hh}`);ws.setAttribute('width',w);ws.setAttribute('height',hh);
    const base=nombreBase(G);let acum=D.b||0;const pasos=[{nombre:base,desde:0,hasta:D.b||0,total:true}];
    for(const p of D.partes){pasos.push({nombre:p.nombre,desde:acum,hasta:acum+p.valor,valor:p.valor});acum+=p.valor;}pasos.push({nombre:'Este período',desde:0,hasta:D.a||0,total:true});
    const vals=pasos.flatMap(p=>[p.desde,p.hasta]),high=Math.max(1e-9,...vals)*1.1,low=Math.min(0,...vals)*1.1,ht=hh-46,Y=v=>14+(high-v)/(high-low||1)*ht,step=(w-8)/pasos.length,width=Math.min(64,step*.62);
    ws.innerHTML=pasos.map((p,i)=>{const x=4+i*step+(step-width)/2,yy=Math.min(Y(p.desde),Y(p.hasta)),height=Math.max(1,Math.abs(Y(p.desde)-Y(p.hasta))),ws2=String(p.nombre).split(' '),med=Math.ceil(ws2.length/2);
      const l1=ws2.slice(0,med).join(' '),l2=ws2.slice(med).join(' '),corta=t=>t.length>16?t.slice(0,15)+'…':t,val=p.total?(D.modo==='Valor'?milS(p.hasta):eje(D,p.hasta)):(D.modo==='Valor'?mil(p.valor):`${signo(p.valor)}${eje(D,Math.abs(p.valor))}`);
      return`<rect x="${x}" y="${yy}" width="${width}" height="${height}" rx="3" class="${p.total?'vap-actual':p.valor>=0?'vap-sube':'vap-baja'}"><title>${esc(p.nombre)}: ${esc(magnitudTexto(G,p.total?p.hasta:p.valor,!p.total))}</title></rect>`+
        (i<pasos.length-1?`<line x1="${x+width}" x2="${x+step}" y1="${Y(p.hasta)}" y2="${Y(p.hasta)}" class="vap-con"/>`:'')+
        `<text x="${x+width/2}" y="${Math.max(10,yy-5)}" text-anchor="middle" class="vap-val">${esc(val)}</text><text x="${x+width/2}" y="${hh-19}" text-anchor="middle" class="vap-axis"><title>${esc(p.nombre)}</title>${esc(corta(l1))}</text><text x="${x+width/2}" y="${hh-7}" text-anchor="middle" class="vap-axis">${esc(corta(l2))}</text>`;}).join('');}
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
  function montar({data:P,parentElement,setTriggerValue}){const old=window.__comprasAno;old?.abort.abort();old?.ro?.disconnect();let root=parentElement.querySelector('.vap');if(!root){root=document.createElement('div');root.className='vap';parentElement.appendChild(root);}
    const s=old?.s||inicial(P.inicial);if(!MODOS.includes(s.modo))s.modo='Valor';if(!['Cascada','Tabla'].includes(s.vista))s.vista='Cascada';if(!TABS.some(([k])=>k===s.tab))s.tab='precio';
    if(s.fam!==ALL&&!(P.familias||[]).includes(s.fam))s.fam=ALL;if(s.agrupar!=='Producto'&&!(P.mapas||{})[s.agrupar])s.agrupar='Producto';if(s.focoPor!=='Producto'&&!(P.mapas||{})[s.focoPor])s.focoPor='Producto';
    const G={P,s,root,cache:{},abort:new AbortController(),tablas:{},listas:old?.listas||{},pedido:old?.pedido||false};window.__comprasAno=G;const signal=G.abort.signal;
    root.addEventListener('click',e=>{const b=e.target.closest('[data-a]');if(!b||b.disabled)return;const{a,v,id}=b.dataset;
      if(a==='modo')s.modo=v;else if(a==='vista')s.vista=v;else if(a==='corte')s.corte=v;else if(a==='tab'){s.tab=v;}
      else if(a==='sentido')s.sentido={...s.sentido,[b.dataset.tab]:v};
      else if(a==='fam'){s.fam=v;s.foco=null;s.prodSerie=null;}
      else if(a==='todo'){s.foco=null;s.prodSerie=null;s.modo='Valor';}
      else if(a==='foco'){const por=b.dataset.por||s.agrupar;if(G.D.foco===v&&G.D.focoPor===por)s.foco=null;else{s.foco=v;s.focoPor=por;}s.prodSerie=null;}
      else if(a==='meses'){s.meses=[];s.ancla=null;}
      else if(a==='mes'){
        if(e.shiftKey&&s.ancla){const ks=G.D.serie.map(r=>r.mes),i=ks.indexOf(s.ancla),j=ks.indexOf(v);s.meses=i>=0&&j>=0?ks.slice(Math.min(i,j),Math.max(i,j)+1):[v];}
        else{s.meses=s.meses.length===1&&s.meses[0]===v?[]:[v];s.ancla=v;}
      }else if(a==='mas'){G.listas[v]=(G.listas[v]||60)+60;}
      else if(a==='orden'){const o=s.orden;s.orden={id,k:v,d:o?.id===id&&o.k===v?-o.d:1};}
      else if(a==='excel'){bajar('Compras_vs_ano_pasado.xlsx',libro(exportar(G)));return;}
      dibujar(G);
    },{signal});
    root.addEventListener('change',e=>{const k=e.target.dataset.select;if(k){s[k]=e.target.value;if(k==='contra'){s.meses=[];s.ancla=null;}}else if(e.target.hasAttribute('data-detallemeses'))s.detalleMeses=e.target.checked;else return;dibujar(G);},{signal});
    root.addEventListener('input',e=>{if(e.target.dataset.input==='q'){s.q=e.target.value;dibujar(G);}},{signal});
    root.addEventListener('keydown',e=>{const el=e.target.closest('[data-a=foco],[data-a=mes]');if(el&&(e.key==='Enter'||e.key===' ')){e.preventDefault();el.dispatchEvent(new MouseEvent('click',{bubbles:true,shiftKey:e.shiftKey}));}},{signal});
    root.addEventListener('scroll',e=>{const el=e.target,t=G.tablas[el.dataset?.tabla];if(t&&el.scrollTop+el.clientHeight>=el.scrollHeight-180&&t.n<t.filas.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',rows(G,el.dataset.tabla,t.n,t.n+150));t.n+=150;}},{signal,capture:true});
    dibujar(G);
    // La venta se pide después de dibujar: sin caché tarda, y las compras no la esperan.
    if(P.venta_pendiente&&P.venta==null&&typeof setTriggerValue==='function'&&!G.pedido){G.pedido=true;setTimeout(()=>{if(!signal.aborted)setTriggerValue('venta',Date.now());},120);}
    return()=>{G.abort.abort();G.ro?.disconnect();};}
  return{montar,inicial,leer,ventana,emparejar,calcular,porProducto,agrupar,magnitud,exportar,dibujar,motivo};
})();
window.__vapDatos=VAP;
export default function(component){return VAP.montar(component);}
