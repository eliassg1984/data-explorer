/* Comparación mensual de compras. Parejas y ventanas preparadas en Python (#725). */
const VAP=(()=>{
  const ALL='__todas__',MODOS=['Valor','Cantidad','Precio'];
  const nf=new Intl.NumberFormat('es-PE',{minimumFractionDigits:2,maximumFractionDigits:2}),qf=new Intl.NumberFormat('es-PE',{maximumFractionDigits:3});
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normal=v=>String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const dinero=v=>v==null?'Sin base':`S/ ${nf.format(v)}`,cmp=(a,b)=>a<b?-1:a>b?1:0;
  const sum=(rs,k)=>{let s=0,c=0;for(const r of rs){const v=(r[k]||0)-c,t=s+v;c=t-s-v;s=t;}return s;};
  function grupos(rs,k){const m=new Map();for(const r of rs){const v=typeof k==='function'?k(r):r[k];if(!m.has(v))m.set(v,[]);m.get(v).push(r);}return m;}
  function inicial(v={}){return{ventana:'3m',fam:ALL,agrupar:'Producto',q:'',modo:'Valor',foco:null,auto:true,
    meses:[],ancla:null,corte:'Por qué',vista:'Cascada',prodSerie:null,detalleMeses:false,cobertura:'Todos',orden:null,...v};}
  function leer(P,fam){const p=P.planes[fam]||{filas:[],mapas:{Producto:{}},unidades:{},ventanas:{}};return{...p,rows:p.filas.map(r=>({p:r[0],mes:r[1],v:r[2],q:r[3],va:r[4],qa:r[5],ha:r[6],hb:r[7]}))};}
  function porProducto(rs,P,plan){return[...grupos(rs,'p')].map(([p,g])=>{
    const v=sum(g,'v'),q=sum(g,'q'),va=sum(g,'va'),qa=sum(g,'qa'),delta=v-va,ep=q>0&&qa>0?v-va/qa*q:0,ha=g.some(r=>r.ha),hb=g.some(r=>r.hb);
    return{p,item:P.productos[p],v,q,va,qa,delta,ep,ec:delta-ep,n:1,ha,hb,soloA:ha&&!hb?1:0,soloB:hb&&!ha?1:0,ambos:ha&&hb?1:0,
      sinBase:q<=0||qa<=0?1:0,sinBaseValor:q<=0||qa<=0?delta:0,um:plan.unidades[p]||''};
  });}
  function agrupar(rs,P,plan,por){const prods=porProducto(rs,P,plan);if(por==='Producto')return prods;
    const mapa=plan.mapas[por]||{};return[...grupos(prods,r=>mapa[r.p]??r.item)].map(([item,g])=>({item,v:sum(g,'v'),q:null,va:sum(g,'va'),qa:null,
      delta:sum(g,'delta'),ep:sum(g,'ep'),ec:sum(g,'ec'),n:g.length,ha:g.some(r=>r.ha),hb:g.some(r=>r.hb),soloA:sum(g,'soloA'),soloB:sum(g,'soloB'),ambos:sum(g,'ambos'),sinBase:sum(g,'sinBase'),sinBaseValor:sum(g,'sinBaseValor'),um:''}));
  }
  const ordenItems=rs=>rs.sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta)||cmp(a.item,b.item));
  function magnitud(r,modo,anterior=false){const v=anterior?r.va:r.v,q=anterior?r.qa:r.q;return modo==='Precio'?(q>0?v/q:null):modo==='Cantidad'?q:v;}
  function calcular(P,s,cache={}){
    if(cache.fam!==s.fam){cache.fam=s.fam;cache.plan=leer(P,s.fam);cache.baseKey=null;}
    const plan=cache.plan,key=JSON.stringify([s.ventana,s.agrupar]);
    if(cache.baseKey!==key){const ms=plan.ventanas[s.ventana]||[],g=plan.rows.filter(r=>ms.includes(r.mes));cache.baseKey=key;cache.g=g;cache.items=ordenItems(agrupar(g,P,plan,s.agrupar));}
    const g=cache.g,items=cache.items,mapa=plan.mapas[s.agrupar]||{},nombre=r=>s.agrupar==='Producto'?P.productos[r.p]:mapa[r.p]??P.productos[r.p];
    let foco=items.some(r=>r.item===s.foco)?s.foco:null;
    if(foco==null&&s.auto&&items.length)foco=items[0].item;
    let gf=foco==null?g:g.filter(r=>nombre(r)===foco);
    const productos=porProducto(gf,P,plan).sort((a,b)=>b.v-a.v||cmp(b.item,a.item));
    let referencia=null;
    if(s.modo!=='Valor'){
      referencia=productos.find(r=>r.item===s.prodSerie)||productos[0]||null;
      gf=referencia?gf.filter(r=>r.p===referencia.p):[];
    }
    const serie=[...grupos(gf,'mes')].sort((a,b)=>cmp(a[0],b[0])).map(([mes,rs])=>({mes,v:sum(rs,'v'),q:sum(rs,'q'),va:sum(rs,'va'),qa:sum(rs,'qa'),ha:rs.some(r=>r.ha),hb:rs.some(r=>r.hb)}));
    const meses=s.meses.filter(m=>serie.some(r=>r.mes===m)),gc=meses.length?gf.filter(r=>meses.includes(r.mes)):gf;
    const productosC=porProducto(gc,P,plan),tot={v:sum(productosC,'v'),q:sum(productosC,'q'),va:sum(productosC,'va'),qa:sum(productosC,'qa'),ep:sum(productosC,'ep'),ec:sum(productosC,'ec'),sinBase:sum(productosC,'sinBase'),sinBaseValor:sum(productosC,'sinBaseValor')};
    const a=magnitud(tot,s.modo),b=magnitud(tot,s.modo,true),delta=a==null||b==null?null:a-b,pct=b>0&&delta!=null?delta/b*100:null;
    const ops=s.modo==='Precio'?[]:[...(s.modo==='Valor'?['Por qué']:[]),...(foco==null&&s.modo==='Valor'?['Quién']:[]),...(serie.length>1&&meses.length!==1?['Cuándo']:[])];
    const corte=ops.includes(s.corte)?s.corte:ops[0]||null;
    let partes=[];
    if(corte==='Por qué')partes=[{nombre:'Precio',valor:tot.ep},{nombre:tot.sinBase?'Cantidad / sin base':'Cantidad',valor:tot.ec}];
    else if(corte==='Quién')partes=agrupar(gc,P,plan,s.agrupar).map(r=>({nombre:r.item,valor:r.delta}));
    else if(corte==='Cuándo')partes=serie.filter(r=>!meses.length||meses.includes(r.mes)).map(r=>({nombre:P.meses[r.mes],valor:magnitud(r,s.modo)-magnitud(r,s.modo,true),mes:r.mes}));
    else if(delta!=null)partes=[{nombre:'Variación',valor:delta}];
    if(partes.length>P.max_pasos&&corte!=='Por qué'){
      const orden=partes.map((r,i)=>({...r,i})).sort((a,b)=>Math.abs(b.valor)-Math.abs(a.valor)||a.i-b.i),top=orden.slice(0,P.max_pasos),resto=orden.slice(P.max_pasos);
      partes=(corte==='Cuándo'?top.sort((a,b)=>a.i-b.i):top).concat([{nombre:`Otros (${resto.length})`,valor:sum(resto,'valor')}]);
    }
    const tg=s.detalleMeses&&meses.length?g.filter(r=>meses.includes(r.mes)):g,q=normal(s.q);
    const tabla=ordenItems(agrupar(tg,P,plan,s.agrupar)).filter(r=>(!q||normal(r.item).includes(q))
      &&(s.cobertura==='Todos'||s.cobertura==='En ambos'&&r.ha&&r.hb||s.cobertura==='Sólo actual'&&r.ha&&!r.hb||s.cobertura==='Sólo anterior'&&r.hb&&!r.ha||s.cobertura==='Sin precio comparable'&&r.sinBase>0));
    return{plan,g,items,foco,gf,gc,serie,meses,productos,referencia,tot,a,b,delta,pct,ops,corte,partes,tabla,
      um:referencia?referencia.um:(new Set(gf.map(r=>r.p)).size===1?plan.unidades[gf[0]?.p]||'':''),
      parcial:plan.parcial,grupos:Object.keys(plan.mapas),noproductos:productosC.length};
  }
  const c=(k,n,t='')=>({k,n,t});
  function colsDetalle(G){return[c('item',G.s.agrupar),c('v','Actual','v'),c('va','Anterior','v'),c('delta','Δ S/','v'),c('pct','Δ %','pct'),c('ep','Efecto precio','v'),c('ec','Efecto cantidad','v'),
    c('sinBase','Sin base de precio','n'),...(G.s.agrupar==='Producto'?[c('um','Unidad'),c('q','Cantidad actual','q'),c('qa','Cantidad anterior','q')]:[c('n','Productos','n')])];}
  function formato(v,t){if(t==='v')return dinero(v);if(t==='pct')return v==null?'Sin base':`${v>0?'+':''}${nf.format(v)} %`;if(t==='q'||t==='n')return v==null?'—':qf.format(v);return v??'';}
  function tabla(G,id,cols,rs,accion=''){
    let filas=rs.map(r=>({...r,pct:r.va>0?r.delta/r.va*100:null}));const o=G.s.orden;
    if(o?.id===id)filas.sort((a,b)=>{const x=a[o.k],y=b[o.k];if(x==null)return y==null?0:1;if(y==null)return-1;return(typeof x==='number'&&typeof y==='number'?x-y:cmp(String(x),String(y)))*o.d;});
    G.tablas[id]={cols,filas,accion,n:150};
    return`<div class="vap-scroll" data-tabla="${id}" tabindex="0"><table><thead><tr>${cols.map(col=>`<th><button data-a="orden" data-id="${id}" data-v="${col.k}">${esc(col.n)}${o?.id===id&&o.k===col.k?o.d===1?' ↑':' ↓':''}</button></th>`).join('')}</tr></thead><tbody>${rows(G,id,0,150)}</tbody></table>${filas.length?'':'<p class="vap-vacio">No hay filas para esta selección.</p>'}</div>`;
  }
  function rows(G,id,a,b){const t=G.tablas[id];return t.filas.slice(a,b).map(r=>`<tr ${t.accion?`data-a="${t.accion}" data-v="${esc(r.item)}" tabindex="0"`:''} class="${r.item===G.D.foco?'on':''}">${t.cols.map(col=>`<td class="${col.t?'num':''}" title="${esc(formato(r[col.k],col.t))}">${esc(formato(r[col.k],col.t))}</td>`).join('')}</tr>`).join('');}
  function select(k,rot,ops,v,labels={}){const vs=ops.slice();if(v!=null&&!vs.includes(v))vs.push(v);return`<label>${rot}<select data-select="${k}" aria-label="${rot}">${vs.map(x=>`<option value="${esc(x)}" ${x===v?'selected':''}>${esc(labels[x]??x)}</option>`).join('')}</select></label>`;}
  function seg(ops,v,a){return`<div class="vap-seg">${ops.map(x=>`<button data-a="${a}" data-v="${esc(x)}" class="${v===x?'on':''}" aria-pressed="${v===x}">${esc(x)}</button>`).join('')}</div>`;}
  function tituloSerie(G){return G.D.referencia?G.D.referencia.item:G.D.foco||'Todas las compras';}
  function ambitoMeses(G){return G.D.meses.length?G.D.meses.map(m=>G.P.meses[m]).join(' · '):'Todos los meses de la serie';}
  function rangoMeses(G,ms,aa=false){if(!ms.length)return 'Sin meses';const etiquetas=aa?G.P.meses_aa:G.P.meses,ks=[...new Set(ms)].sort(),a=etiquetas?.[ks[0]]||ks[0],b=etiquetas?.[ks.at(-1)]||ks.at(-1);return a===b?a:`${a} → ${b}`;}
  function magnitudTexto(G,v){return G.s.modo==='Cantidad'?v==null?'Sin base':`${qf.format(v)} ${G.D.um||'(unidad sin dato)'}`:G.s.modo==='Precio'?v==null?'Sin base':`${dinero(v)} / ${G.D.um||'unidad sin dato'}`:dinero(v);}
  function dibujar(G){const {P,s,root}=G;G.D=calcular(P,s,G.cache);const D=G.D;G.tablas={};s.meses=D.meses;if(D.corte!=null)s.corte=D.corte;
    const active=root.querySelector('input:focus'),f=active?[active.dataset.input,active.selectionStart,active.selectionEnd]:null;
    const scroll=[...root.querySelectorAll('[data-tabla]')].map(e=>[e.dataset.tabla,e.scrollTop,e.scrollLeft]);
    let html=`<section class="vap-card vap-cab"><header><h3>Vs año pasado</h3><span>${esc(Object.entries(P.contexto).filter(([,v])=>v.length).map(([k,v])=>k+': '+v.join(', ')).join(' · '))}</span><button data-a="excel" ${!D.g.length?'disabled':''}>Excel de esta vista ↓</button></header><div class="vap-controles">${select('ventana','Ventana',P.opciones,s.ventana,P.etiquetas)}${select('fam','Familia',[ALL,...P.familias],s.fam,{[ALL]:'Todas'})}${select('agrupar','Detalle',D.grupos,s.agrupar)}<button data-a="todo">Todas las compras</button></div></section><div class="vap-dos"><section class="vap-card vap-serie"><header><h4>${esc(tituloSerie(G))}</h4></header><div class="vap-controles">${seg(MODOS,s.modo,'modo')}</div>`;
    if(s.modo!=='Valor')html+=select('prodSerie','Producto de referencia',D.productos.map(r=>r.item),D.referencia?.item||'');
    html+=`<div class="vap-leyenda"><span>Actual: ${esc(rangoMeses(G,D.serie.map(r=>r.mes)))}</span><span class="anterior">Anterior: ${esc(rangoMeses(G,D.serie.map(r=>r.mes),true))}</span><span>${s.modo==='Precio'?'Precio medio ponderado':s.modo==='Cantidad'?'Cantidad de un producto':'Valorizado de compra'}</span></div><div class="vap-chart"><svg role="img" aria-label="Comparación mensual"></svg></div><p class="vap-nota">Clic: explicar un mes · Mayús + clic: elegir varios.${D.parcial?` ${esc(P.meses[D.parcial[0]]||D.parcial[0])}: hasta el día ${D.parcial[1]}; el mes espejo usa esos mismos días.`:''}</p></section><section class="vap-card vap-explica"><header><h4>Qué explica la diferencia</h4></header><p class="vap-ambito">${esc(tituloSerie(G))} · ${esc(ambitoMeses(G))}</p><div class="vap-resumen"><b>${magnitudTexto(G,D.g.length?D.delta:null)}</b><span>${D.pct==null?'Sin base positiva para calcular %':formato(D.pct,'pct')}</span></div><p class="vap-nota">${magnitudTexto(G,D.g.length?D.b:null)} → ${magnitudTexto(G,D.g.length?D.a:null)}</p><div class="vap-controles">${s.modo==='Precio'?'<span>Detalle mensual · precio medio por unidad</span>':seg(['Cascada','Tabla'],s.vista,'vista')}${s.vista!=='Tabla'&&D.ops.length?select('corte','Partir por',D.ops,D.corte):''}${D.meses.length?'<button data-a="meses">Todos los meses</button>':''}</div>`;
    if(!D.g.length)html+='<p class="vap-vacio">No hay meses con historia comparable en esta familia y ventana. Probá otra selección.</p>';
    else if(s.vista==='Tabla'||s.modo==='Precio')html+=tabla(G,'mensual',[c('etq','Mes'),c('actual','Actual',s.modo==='Cantidad'?'q':'v'),c('anterior','Anterior',s.modo==='Cantidad'?'q':'v'),c('dif','Δ',s.modo==='Cantidad'?'q':'v')],D.serie.map(r=>({etq:P.meses[r.mes],actual:magnitud(r,s.modo),anterior:magnitud(r,s.modo,true),dif:magnitud(r,s.modo)==null||magnitud(r,s.modo,true)==null?null:magnitud(r,s.modo)-magnitud(r,s.modo,true)})));
    else html+='<div class="vap-waterfall"><svg role="img" aria-label="Descomposición de la variación"></svg></div>';
    if(D.tot.sinBase)html+=`<p class="vap-aviso">${D.tot.sinBase} productos sin cantidades positivas en ambos períodos. Su variación (${dinero(D.tot.sinBaseValor)}) queda en «Cantidad / sin base»; no permite atribuirla a un cambio de precio.</p>`;
    html+='</section></div><section class="vap-card vap-detalle"><header><h3>Detalle de la comparación</h3><span>Los filtros de esta lista no cambian la serie ni su foco.</span></header><div class="vap-controles"><input data-input="q" type="search" aria-label="Buscar ítem" placeholder="Buscar ítem…" value="'+esc(s.q)+'">'+select('cobertura','Registros', ['Todos','En ambos','Sólo actual','Sólo anterior','Sin precio comparable'],s.cobertura)+`<label><input type="checkbox" data-detallemeses ${s.detalleMeses?'checked':''}> Aplicar meses elegidos al detalle</label></div><p class="vap-nota">${s.detalleMeses&&D.meses.length?esc(ambitoMeses(G)):'Ventana completa'} · Actual ${esc(rangoMeses(G,D.g.map(r=>r.mes)))} / anterior ${esc(rangoMeses(G,D.g.map(r=>r.mes),true))} · ${D.tabla.length} filas. Sólo actual/anterior se refiere a registros disponibles, no a productos nuevos o eliminados.</p>`+tabla(G,'detalle',colsDetalle(G),D.tabla,'foco')+'<p class="vap-nota">Precio y cantidad se descomponen por producto antes de sumar familias. No se suman cantidades entre unidades distintas. Clic en una fila para enfocar; otro clic la suelta.</p></section>';
    root.innerHTML=html;
    scroll.forEach(([id,top,left])=>{const e=root.querySelector(`[data-tabla="${id}"]`);if(e){e.scrollTop=top;e.scrollLeft=left;}});
    if(f){const e=root.querySelector(`[data-input="${f[0]}"]`);if(e){e.focus({preventScroll:true});e.setSelectionRange(f[1],f[2]);}}
    G.ro?.disconnect();G.ro=new ResizeObserver(()=>graficos(G));root.querySelectorAll('.vap-chart,.vap-waterfall').forEach(e=>G.ro.observe(e));graficos(G);
  }
  function graficos(G){const D=G.D,s=G.s,P=G.P,box=G.root.querySelector('.vap-chart'),svg=box?.querySelector('svg');if(!svg)return;
    const W=box.clientWidth,H=box.clientHeight;if(W<80||H<65)return;svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('width',W);svg.setAttribute('height',H);
    if(!D.serie.length){svg.innerHTML='';return;}
    const L=61,R=10,T=25,B=32,pw=W-L-R,ph=H-T-B,n=D.serie.length;
    const vs=D.serie.flatMap(r=>[magnitud(r,s.modo),magnitud(r,s.modo,true)]).filter(v=>v!=null),hi=Math.max(1,...vs)*1.15,lo=Math.min(0,...vs)*1.15,span=hi-lo,y=v=>T+(hi-v)/span*ph,bw=Math.max(1,pw/n*.3),cada=Math.max(1,Math.ceil(n/(pw/65)));
    let h='<defs><pattern id="vap-parcial" patternUnits="userSpaceOnUse" width="5" height="5"><path d="M0 5L5 0" stroke="var(--text-primary)" opacity=".35"/></pattern></defs>';
    for(let i=0;i<3;i++){const v=lo+span*i/2;h+=`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" class="vap-grid"/><text x="${L-7}" y="${y(v)+4}" text-anchor="end" class="vap-axis">${esc(qf.format(Math.round(v*100)/100))}</text>`;}
    D.serie.forEach((r,i)=>{const x=L+(i+.5)*pw/n,actual=magnitud(r,s.modo),anterior=magnitud(r,s.modo,true),on=!D.meses.length||D.meses.includes(r.mes);h+=`<g opacity="${on?1:.25}">`;
      for(const [v,dx,cls] of [[anterior,-bw,'vap-aa'],[actual,0,'vap-actual']])if(v!=null){const yy=y(v),hh=Math.max(1,Math.abs(y(0)-yy));h+=`<rect x="${x+dx}" y="${Math.min(yy,y(0))}" width="${bw}" height="${hh}" class="${cls}"/>`;if(D.parcial?.[0]===r.mes)h+=`<rect x="${x+dx}" y="${Math.min(yy,y(0))}" width="${bw}" height="${hh}" fill="url(#vap-parcial)"/>`;}
      if(i%cada===0)h+=`<text x="${x}" y="${H-10}" text-anchor="middle" class="vap-axis">${esc(P.meses[r.mes])}</text>`;
      if(pw/n>95&&actual!=null)h+=`<text x="${x}" y="${Math.max(14,y(actual)-7)}" text-anchor="middle" class="vap-axis">${esc(qf.format(actual))}</text>`;
      h+=`</g><rect data-a="mes" data-v="${r.mes}" x="${x-pw/n/2}" y="${T-12}" width="${pw/n}" height="${ph+12}" fill="transparent" role="button" tabindex="0" aria-label="${esc(P.meses[r.mes])}"><title>${esc(P.meses[r.mes])}: actual ${esc(magnitudTexto(G,actual))} · anterior ${esc(magnitudTexto(G,anterior))} · ${r.ha?'con':'sin'} registros actuales; ${r.hb?'con':'sin'} registros anteriores</title></rect>`;
    });svg.innerHTML=h;
    const wb=G.root.querySelector('.vap-waterfall'),ws=wb?.querySelector('svg');if(!ws)return;const w=wb.clientWidth,hh=wb.clientHeight;if(w<80||hh<65)return;
    ws.setAttribute('viewBox',`0 0 ${w} ${hh}`);ws.setAttribute('width',w);ws.setAttribute('height',hh);
    let acum=D.b||0;const pasos=[{nombre:'Anterior',desde:0,hasta:D.b||0,total:true}];for(const p of D.partes){pasos.push({nombre:p.nombre,desde:acum,hasta:acum+p.valor,valor:p.valor});acum+=p.valor;}pasos.push({nombre:'Actual',desde:0,hasta:D.a||0,total:true});
    const high=Math.max(1,...pasos.flatMap(p=>[p.desde,p.hasta]))*1.12,low=Math.min(0,...pasos.flatMap(p=>[p.desde,p.hasta]))*1.12,ww=w-24,ht=hh-65,Y=v=>12+(high-v)/(high-low)*ht,step=ww/pasos.length,width=step*.6;
    ws.innerHTML=pasos.map((p,i)=>{const x=12+i*step+step*.2,yy=Math.min(Y(p.desde),Y(p.hasta)),height=Math.max(1,Math.abs(Y(p.desde)-Y(p.hasta)));return`<rect x="${x}" y="${yy}" width="${width}" height="${height}" class="${p.total?'vap-actual':p.valor>=0?'vap-sube':'vap-baja'}"><title>${esc(p.nombre)}: ${esc(magnitudTexto(G,p.total?p.hasta:p.valor))}</title></rect><text x="${x+width/2}" y="${Math.max(10,yy-6)}" text-anchor="middle" class="vap-axis">${esc(qf.format(p.total?p.hasta:p.valor))}</text><text x="${x+width/2}" y="${hh-31}" text-anchor="middle" class="vap-axis"><title>${esc(p.nombre)}</title>${esc(p.nombre.length>14?p.nombre.slice(0,12)+'…':p.nombre)}</text>`;}).join('');
  }
  function exportar(G){const {P,s,D}=G,hoja=(nombre,cols,filas)=>({nombre,cabeza:cols.map(c=>c.n),decimales:6,filas:filas.map(r=>cols.map(c=>r[c.k]??''))});
    const cols=[c('mes','Mes'),c('v','Valor actual'),c('va','Valor anterior'),c('q','Cantidad actual'),c('qa','Cantidad anterior'),c('pa','Precio medio actual'),c('paa','Precio medio anterior')];
    const unaUnidad=new Set(D.gf.map(r=>r.p)).size===1;
    const serie=D.serie.map(r=>({...r,q:unaUnidad?r.q:null,qa:unaUnidad?r.qa:null,pa:unaUnidad?magnitud(r,'Precio'):null,paa:unaUnidad?magnitud(r,'Precio',true):null}));
    const contexto=[['Vista','Compras Vs año pasado'],['Ventana',P.etiquetas[s.ventana]||s.ventana],['Meses actuales de la serie',rangoMeses(G,D.serie.map(r=>r.mes))],['Meses anteriores de la serie',rangoMeses(G,D.serie.map(r=>r.mes),true)],['Familia propia',s.fam===ALL?'Todas':s.fam],...Object.entries(P.contexto).map(([k,v])=>[k,v.join(', ')||'Todas']),['Agrupación del detalle',s.agrupar],['Magnitud de la serie',s.modo],['Foco',D.foco||'Todas las compras'],['Producto de referencia',D.referencia?.item||'No aplica'],['Unidad',D.um||'Sin dato / varias unidades'],['Meses explicados',ambitoMeses(G)],['Meses aplicados al detalle',s.detalleMeses?'Sí':'No'],['Buscar',s.q],['Cobertura de registros',s.cobertura],['Mes parcial',D.parcial?`${D.parcial[0]} hasta día ${D.parcial[1]}; espejo recortado igual`:'Sin mes parcial'],['Comparación','Mismo mes menos doce meses. No se usan columnas de año anterior repetidas del parquet.'],['Precio','Media ponderada valor / cantidad. La descomposición se calcula por producto antes de sumar.'],['Sin base positiva','Con cantidad actual o anterior no positiva, precio vale cero y la variación queda en efecto cantidad según la regla original.'],['Cobertura','Sólo actual/anterior describe registros de la fuente cargada, no altas o bajas de productos.'],['Importes','Datos numéricos sin redondear al sumar; formato con seis decimales.'],['Valor actual explicado',D.tot.v],['Valor anterior explicado',D.tot.va],['Efecto precio',D.tot.ep],['Efecto cantidad',D.tot.ec]];
    return[hoja('Detalle',colsDetalle(G),G.tablas.detalle.filas),hoja('Serie mensual',cols,serie),
      {nombre:'Descomposición',cabeza:['Parte','Variación'],decimales:6,filas:D.partes.map(r=>[r.nombre,r.valor])},
      {nombre:'Contexto',cabeza:['Dato','Selección'],decimales:6,filas:contexto}];
  }
  function montar({data:P,parentElement}){const old=window.__comprasAno;old?.abort.abort();old?.ro?.disconnect();let root=parentElement.querySelector('.vap');if(!root){root=document.createElement('div');root.className='vap';parentElement.appendChild(root);}const s=old?.s||inicial(P.inicial);if(!MODOS.includes(s.modo))s.modo='Valor';if(!P.opciones.includes(s.ventana))s.ventana='3m';if(!['Cascada','Tabla'].includes(s.vista))s.vista='Cascada';
    if(!P.planes[s.fam])s.fam=ALL;
    const plan=P.planes[s.fam];if(plan&&!plan.mapas[s.agrupar])s.agrupar='Producto';
    const G={P,s,root,cache:{},abort:new AbortController(),tablas:{}};window.__comprasAno=G;const signal=G.abort.signal;
    root.addEventListener('click',e=>{const b=e.target.closest('[data-a]');if(!b)return;const{a,v,id}=b.dataset;
      if(a==='modo')s.modo=v;else if(a==='vista')s.vista=v;
      else if(a==='todo'){s.foco=null;s.auto=false;s.prodSerie=null;}
      else if(a==='foco'){s.foco=G.D.foco===v?null:v;s.auto=false;s.prodSerie=null;}
      else if(a==='meses'){s.meses=[];s.ancla=null;}
      else if(a==='mes'){
        if(e.shiftKey&&s.ancla){const ks=G.D.serie.map(r=>r.mes),a=ks.indexOf(s.ancla),b=ks.indexOf(v);s.meses=a>=0&&b>=0?ks.slice(Math.min(a,b),Math.max(a,b)+1):[v];}
        else{s.meses=s.meses.length===1&&s.meses[0]===v?[]:[v];s.ancla=v;}
      }else if(a==='orden'){const o=s.orden;s.orden={id,k:v,d:o?.id===id&&o.k===v?-o.d:1};}
      else if(a==='excel'){bajar('Compras_vs_ano_pasado.xlsx',libro(exportar(G)));return;}
      dibujar(G);
    },{signal});
    root.addEventListener('change',e=>{const k=e.target.dataset.select;if(k){s[k]=e.target.value;if(k==='agrupar'){s.foco=null;s.prodSerie=null;}}else if(e.target.hasAttribute('data-detallemeses'))s.detalleMeses=e.target.checked;else return;dibujar(G);},{signal});
    root.addEventListener('input',e=>{if(e.target.dataset.input==='q'){s.q=e.target.value;dibujar(G);}},{signal});
    root.addEventListener('keydown',e=>{const el=e.target.closest('[data-a=foco],[data-a=mes]');if(el&&(e.key==='Enter'||e.key===' ')){e.preventDefault();el.dispatchEvent(new MouseEvent('click',{bubbles:true,shiftKey:e.shiftKey}));}},{signal});
    root.addEventListener('scroll',e=>{const el=e.target,t=G.tablas[el.dataset?.tabla];if(t&&el.scrollTop+el.clientHeight>=el.scrollHeight-180&&t.n<t.filas.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',rows(G,el.dataset.tabla,t.n,t.n+150));t.n+=150;}},{signal,capture:true});
    dibujar(G);return()=>{G.abort.abort();G.ro?.disconnect();};
  }
  return{montar,inicial,leer,calcular,porProducto,agrupar,magnitud,exportar,dibujar};
})();
window.__vapDatos=VAP;
export default function(component){return VAP.montar(component);}
