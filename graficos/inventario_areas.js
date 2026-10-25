/* Área y familia: exploración, matriz y comparación sobre el mismo stock (#724). */
const AREAS=(()=>{
  const TODO='__todas__';
  const lab=(B,k,v)=>v==null?'':(k==='area'?v:B.P.rotulos[k==='sub'?'subfam':k]?.[v])||v||`Sin ${k==='fam'?'familia':k==='sub'?'subfamilia':'área'}`;
  function rank(rows,k,B){
    const rs=[...sgroup(rows,r=>r[k])].map(([nombre,g])=>({nombre,rotulo:lab(B,k,nombre),v:ssum(g,'v'),
      h:B.P.meses.map((_,i)=>g.reduce((a,r)=>a+(r.h[i]||0),0)),productos:new Set(g.map(r=>r.cod)).size,
      neg:new Set(g.filter(r=>r.q<0).map(r=>r.cod)).size})).sort((a,b)=>b.v-a.v||scmp(a.nombre,b.nombre));
    const pos=ssum(rs.filter(r=>r.v>0),'v');return rs.map(r=>({...r,pct:r.v>=0&&pos>0?r.v/pos*100:null}));
  }
  function inicial(P,B){const areas=rank(B.rows,'area',B);return {modo:'Explorar',area:P.default_area??areas[0]?.nombre??TODO,fam:null,sub:null,
    ref:P.ref_default,metrica:'Valor',a:P.default_area??areas[0]?.nombre??null,b:areas.find(r=>r.nombre!==(P.default_area??areas[0]?.nombre))?.nombre??null,
    comparar:'Familias',q:'',exArea:null,motivo:null,exq:'',orden:{}};}
  function scope(B,s,areas=null){return B.rows.filter(r=>(areas?areas.includes(r.area):s.area===TODO||r.area===s.area)
    &&(s.fam==null||r.fam===s.fam)&&(s.sub==null||r.sub===s.sub));}
  function cambios(rs,P,ref){
    const g=[...sgroup(rs,r=>r.cod)].sort((a,b)=>scmp(a[0],b[0])).map(([cod,rr])=>{
      const h=P.meses.map((_,i)=>rr.reduce((a,r)=>a+(r.h[i]||0),0));
      return{cod,prod:rr[0].prod,antes:h[ref]||0,ahora:h.at(-1)||0,delta:(h.at(-1)||0)-(h[ref]||0),vacio:rr.reduce((a,r)=>a+Math.abs(r.v),0)<.5};});
    const todos=g.filter(r=>Math.abs(r.delta)>=1).sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta));
    return {top:todos.slice(0,7),total:ssum(g,'delta'),n:todos.length,resto:ssum(g,'delta')-ssum(todos.slice(0,7),'delta')};
  }
  function comparar(B,s){
    const rows=scope(B,{...s,area:TODO},[s.a,s.b].filter(v=>v!=null)),porProducto=s.comparar==='Productos';
    const key=r=>porProducto?JSON.stringify([r.cod,r.um]):r.fam;
    const rs=[...sgroup(rows,key)].map(([clave,g])=>{
      const a=g.filter(r=>r.area===s.a),b=g.filter(r=>r.area===s.b);
      return{clave,nombre:porProducto?g[0].prod:lab(B,'fam',g[0].fam),cod:porProducto?g[0].cod:'',fam:g[0].fam,
        um:porProducto?g[0].um:'',qa:porProducto?ssum(a,'q'):null,qb:porProducto?ssum(b,'q'):null,
        a:ssum(a,'v'),b:ssum(b,'v'),delta:ssum(b,'v')-ssum(a,'v'),
        na:new Set(a.filter(r=>Math.abs(r.q)>SEPS||Math.abs(r.v)>SEPS).map(r=>r.cod)).size,nb:new Set(b.filter(r=>Math.abs(r.q)>SEPS||Math.abs(r.v)>SEPS).map(r=>r.cod)).size};
    }).filter(r=>!porProducto||r.na||r.nb).sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta)||scmp(a.clave,b.clave));
    const q=splano(s.q);return rs.filter(r=>!q||splano(r.nombre+' '+r.cod).includes(q));
  }
  function matriz(B,s){
    const areas=rank(B.rows,'area',B).map(r=>r.nombre),fams=rank(B.rows,'fam',B),q=splano(s.q);
    const cells=new Map([...sgroup(B.rows,r=>JSON.stringify([r.fam,r.area]))].map(([k,g])=>[k,{v:ssum(g,'v'),
      neg:new Set(g.filter(r=>r.q<0).map(r=>r.cod)).size,negV:ssum(g.filter(r=>r.q<0),'v')}]));
    const filas=fams.filter(r=>!q||splano(r.rotulo).includes(q)).map(r=>({...r,cells:areas.map(a=>cells.get(JSON.stringify([r.nombre,a]))||{v:0,neg:0,negV:0})}));
    return{areas,filas};
  }
  function calcular(B,s,E=null,cache=null){
    if(cache){
      const key=JSON.stringify([s.modo,s.area,s.fam,s.sub,s.ref,s.a,s.b,s.comparar,s.exArea,s.motivo]);
      if(cache.key!==key){cache.key=key;cache.datos=calcular(B,{...s,q:'',exq:''},E);}
      const d=cache.datos,q=splano(s.q),eq=splano(s.exq);
      return{...d,matriz:{...d.matriz,filas:d.matriz.filas.filter(r=>!q||splano(r.rotulo).includes(q))},
        comparacion:d.comparacion.filter(r=>!q||splano(r.nombre+' '+r.cod).includes(q)),
        exfilas:d.exfilas.filter(r=>!eq||splano(r.cod+' '+r.prod+' '+r.motivo).includes(eq))};
    }
    const ar=rank(B.rows,'area',B),porArea=B.rows.filter(r=>s.area===TODO||r.area===s.area),familias=rank(porArea,'fam',B),
      subfamilias=rank(porArea.filter(r=>s.fam==null||r.fam===s.fam),'sub',B);
    const elegidas=s.modo==='Comparar'?[s.a,s.b].filter(v=>v!=null):s.area===TODO?[]:[s.area];
    const rs=scope(B,s,s.modo==='Comparar'?elegidas:null),prods=sagrupar(rs,B,B.P.analisis).productos;
    const h=B.P.meses.map((_,i)=>rs.reduce((a,r)=>a+(r.h[i]||0),0));
    const ex=(E?.rows||[]).filter(r=>(B.P.hay_cantidad?Math.abs(r.q)>0:true)||Math.abs(r.v)>0)
      .map(r=>({...r,motivo:E.P.motivos[r.i]||'Sin motivo'}));
    const q=splano(s.exq),exfilas=ex.filter(r=>(s.exArea==null||r.area===s.exArea)&&(s.motivo==null||r.motivo===s.motivo)
      &&(!q||splano(r.cod+' '+r.prod+' '+r.motivo).includes(q)));
    return{areas:ar,familias,subfamilias,rs,prods,h,elegidas,total:ssum(rs,'v'),
      stock:prods.filter(r=>r.areas.length).length,dias:B.P.analisis?sdiasConjunto(prods,B.P.ventana):null,
      estados:sestados(prods),cambios:cambios(rs,B.P,s.ref),matriz:matriz(B,s),comparacion:comparar(B,s),
      excluidos:ex,exfilas,exTotal:ssum(ex,'v')};
  }
  const btn=(a,v,t,on=false)=>`<button data-a="${a}" data-v="${se(v)}" class="${on?'on':''}" aria-pressed="${on}">${se(t)}</button>`;
  const seg=(ops,v,a)=>`<div class="iar-seg">${ops.map(op=>btn(a,op,op,v===op)).join('')}</div>`;
  function curva(h,mini=false,labels=[]){if(!h.length)return 'Sin historia';const w=mini?72:650,H=mini?20:110,mn=Math.min(0,...h),mx=Math.max(0,...h),dif=mx-mn||1;
    return `<svg viewBox="0 0 ${w} ${H}" class="${mini?'iar-mini':'iar-curva'}" role="img" aria-label="Valorizado según kardex"><polyline points="${h.map((v,i)=>`${2+i*(w-4)/Math.max(1,h.length-1)},${H-(mini?3:20)-(v-mn)/dif*(H-(mini?6:26))}`).join(' ')}" fill="none" stroke="var(--accent)" stroke-width="${mini?1.3:2}" vector-effect="non-scaling-stroke"/>${mini?'':labels.map((m,i)=>i===0||i===Math.floor(labels.length/2)||i===labels.length-1?`<text x="${2+i*(w-4)/Math.max(1,h.length-1)}" y="${H-2}" text-anchor="${i===0?'start':i===labels.length-1?'end':'middle'}">${se(m)}</text>`:'').join('')}<title>${se(h.map((v,i)=>(labels[i]||'')+': '+ss(v)).join(' → '))}</title></svg>`;}
  function ranking(G,k,rs,titulo,elegido,todas=false){const total=ssum(rs,'v'),max=Math.max(1,...rs.map(r=>Math.abs(r.v)));return`<div class="iar-panel"><h4>${titulo}</h4><div class="iar-scroll"><table class="iar-rank"><thead><tr><th>Nombre</th><th>Valorizado</th><th>% positivo</th>${G.P.meses.length?'<th>Historia</th>':''}</tr></thead><tbody>${todas?`<tr data-a="area" data-v="${TODO}" class="${elegido===TODO?'on':''}" tabindex="0"><td>Todas las áreas</td><td class="num">${ss(total,0)}</td><td>—</td>${G.P.meses.length?'<td></td>':''}</tr>`:''}${rs.map(r=>`<tr data-a="${k}" data-v="${se(r.nombre)}" class="${r.nombre===elegido?'on':''}" tabindex="0"><td title="${se(r.rotulo)}">${se(r.rotulo)}</td><td class="num ${r.v<0?'neg':''}" style="background-image:linear-gradient(to right,var(--accent-tint) ${Math.abs(r.v)/max*45}%,transparent ${Math.abs(r.v)/max*45}%)" title="${ss(r.v)}">${ss(r.v,0)}</td><td class="num">${r.pct==null?'—':sn(r.pct,1)+'%'}</td>${G.P.meses.length?`<td>${curva(r.h,true,G.P.meses)}</td>`:''}</tr>`).join('')}</tbody><tfoot><tr><td>Total</td><td class="num">${ss(total,0)}</td><td></td>${G.P.meses.length?'<td></td>':''}</tr></tfoot></table>${rs.length?'':'<p class="iar-vacio">Sin filas para el recorte.</p>'}</div></div>`;}
  function ruta(G){const s=G.s,B=G.B;return[s.modo==='Comparar'?`${s.a??'—'} / ${s.b??'—'}`:s.area===TODO?'Todas las áreas':lab(B,'area',s.area),
    s.fam!=null?lab(B,'fam',s.fam):null,s.sub!=null?lab(B,'sub',s.sub):null].filter(v=>v!=null).join(' › ');}
  function matrizHTML(G){const M=G.D.matriz,s=G.s,max=Math.max(1,...M.filas.flatMap(r=>r.cells.map(c=>s.metrica==='Negativos'?c.neg:Math.abs(c.v))));
    return`<div class="iar-scroll"><table class="iar-matriz"><thead><tr><th>Familia / Área</th>${M.areas.map(a=>`<th>${se(lab(G.B,'area',a))}</th>`).join('')}</tr></thead><tbody>${M.filas.map(r=>`<tr><td>${se(r.rotulo)}</td>${r.cells.map((c,i)=>`<td><button data-a="celda" data-area="${se(M.areas[i])}" data-fam="${se(r.nombre)}" style="--nivel:${(s.metrica==='Negativos'?c.neg:Math.abs(c.v))/max}" class="${c.v<0?'neg':''} ${s.area===M.areas[i]&&s.fam===r.nombre?'on':''}" title="${se(r.rotulo+' · '+M.areas[i])}: ${ss(c.v)} · ${c.neg} productos con cantidad negativa, por ${ss(c.negV)}">${s.metrica==='Negativos'?sn(c.neg):ss(c.v,0)}</button></td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  function lista(G,id,cols,filas){const o=G.s.orden[id];let fs=filas.slice();if(o)fs.sort((a,b)=>{const x=a[o.k],y=b[o.k];if(x==null)return y==null?0:1;if(y==null)return-1;return(typeof x==='number'&&typeof y==='number'?x-y:scmp(String(x),String(y)))*o.d;});G.tablas[id]={cols,filas:fs,n:150};
    return`<div class="iar-scroll" data-tabla="${id}" tabindex="0"><table><thead><tr>${cols.map(c=>`<th><button data-a="orden" data-id="${id}" data-v="${c[0]}">${se(c[1])}${o?.k===c[0]?o.d===1?' ↑':' ↓':''}</button></th>`).join('')}</tr></thead><tbody>${listRows(G,id,0,150)}</tbody></table>${fs.length?'':'<p class="iar-vacio">Sin filas con esta selección.</p>'}</div>`;
  }
  function form(v,t){return t==='v'?ss(v):t==='q'?sv(v):v??'';}
  function listRows(G,id,a,b){const t=G.tablas[id];return t.filas.slice(a,b).map(r=>`<tr>${t.cols.map(c=>`<td class="${c[2]?'num':''}" title="${se(form(r[c[0]],c[2]))}">${se(form(r[c[0]],c[2]))}</td>`).join('')}</tr>`).join('');}
  function select(G,k,ops,v,label){const offered=[...ops];if(v!=null&&!offered.includes(v))offered.push(v);return`<label>${label}<select data-select="${k}"><option value="__sin__">${k==='a'||k==='b'?'Elegir área':'Todos'}</option>${offered.map(x=>`<option value="${se(x)}" ${x===v?'selected':''}>${se(x||'Sin dato')}</option>`).join('')}</select></label>`;}
  function dibujar(G){const {root,s,P,B}=G;G.D=calcular(B,s,G.E,G.cache);const D=G.D;G.tablas={};
    const active=root.querySelector('input:focus'),f=active?[active.dataset.input,active.selectionStart,active.selectionEnd]:null;
    const scroll=[...root.querySelectorAll('[data-tabla]')].map(e=>[e.dataset.tabla,e.scrollTop,e.scrollLeft]);
    let html=`<section class="iar-card iar-main"><header><h3>Stock por área y familia</h3><span>${se(Object.entries(P.contexto).filter(([,v])=>v.length).map(([k,v])=>k+': '+v.join(', ')).join(' · '))}</span><button data-a="excel">Excel de esta vista ↓</button></header>`
      +`<div class="iar-barra">${seg(['Explorar','Matriz','Comparar',...(D.excluidos.length?['Excluidos']:[])],s.modo,'modo')}<span>${s.modo==='Excluidos'?'No suman al stock':se(s.modo==='Matriz'?'Matriz de los filtros de la página':ruta(G))}</span>${s.fam!=null||s.sub!=null?'<button data-a="soltar">Todas las familias</button>':''}</div>`;
    if(s.modo==='Explorar')html+=`<div class="iar-rankings">${ranking(G,'area',D.areas,'Área',s.area,true)}${ranking(G,'fam',D.familias,'Familia',s.fam)}${ranking(G,'sub',D.subfamilias,'Subfamilia',s.sub)}</div><p class="iar-nota">Porcentajes sobre las categorías con valor positivo; un negativo no es participación. Elegí una fila para profundizar.</p>`;
    else if(s.modo==='Matriz')html+=`<div class="iar-controles">${seg(['Valor','Negativos'],s.metrica,'metrica')}<input type="search" data-input="q" aria-label="Buscar familia" placeholder="Buscar familia…" value="${se(s.q)}"></div>${matrizHTML(G)}<p class="iar-nota">${s.metrica==='Negativos'?'Productos distintos con cantidad negativa en cada celda; el tooltip conserva su valorizado.':'Valorizado neto por familia y área. Los negativos se muestran con su signo.'} La matriz conserva los filtros de la página; tocá una celda para acotar sólo el análisis de abajo.</p>`;
    else if(s.modo==='Comparar'){
      html+=`<div class="iar-controles">${select(G,'a',D.areas.map(r=>r.nombre),s.a,'Área A')}${select(G,'b',D.areas.map(r=>r.nombre),s.b,'Área B')}${seg(['Familias','Productos'],s.comparar,'comparar')}<input type="search" data-input="q" aria-label="Buscar comparación" placeholder="Buscar…" value="${se(s.q)}"></div>`;
      const cols=s.comparar==='Productos'?[['cod','Código'],['nombre','Producto'],['um','Unidad'],['qa','Cantidad A','q'],['qb','Cantidad B','q']]:[['nombre','Familia'],['na','Con stock A','q'],['nb','Con stock B','q']];
      G.compCols=[...cols,['a','Valor A','v'],['b','Valor B','v'],['delta','B − A','v']];
      html+=s.a==null||s.b==null||s.a===s.b?'<p class="iar-vacio">Elegí dos áreas distintas disponibles en los filtros de la página.</p>':lista(G,'comparar',G.compCols,D.comparacion);
      html+='<p class="iar-nota">B − A compara existencias; no es una recomendación de transferencia. Cantidades separadas por código y unidad; no se suman unidades distintas.</p>';
    }else{
      html+=`<div class="iar-controles">${select(G,'exArea',[...new Set(D.excluidos.map(r=>r.area))].sort(),s.exArea,'Área')}${select(G,'motivo',[...new Set(D.excluidos.map(r=>r.motivo))].sort(),s.motivo,'Motivo')}<input type="search" data-input="exq" aria-label="Buscar excluidos" placeholder="Buscar código, nombre o motivo…" value="${se(s.exq)}"></div><p class="iar-nota">Inactivos, servicios y artículos o áreas no habilitados; sólo filas con stock o valorizado. Total excluido: ${ss(D.exTotal)}.</p>`;
      G.exCols=[['cod','Código'],['prod','Producto'],['area','Área'],['motivo','Por qué'],['um','Unidad'],['q','Cantidad','q'],['precio','Precio','v'],['v','Valorizado','v']];html+=lista(G,'excluidos',G.exCols,D.exfilas);
    }
    html+='</section>';
    if(s.modo!=='Excluidos'){
      const states=[['neg','Negativos'],['sin','Sin consumo 90 d'],['alto','Más de 60 días']];
      html+=`<section class="iar-card iar-analisis"><header><div><h3>${se(ruta(G))}</h3><p>${D.stock} productos con stock · ${ss(D.total)} en el maestro actual</p></div><button data-a="ir" data-v="todos" ${!D.rs.length?'disabled':''}>Ver sus productos ↑</button></header><div class="iar-controles"><label>Comparar historia desde<select data-select="ref">${P.meses.map((m,i)=>`<option value="${i}" ${s.ref===i?'selected':''}>${se(m)}</option>`).join('')}</select></label><span>Histórico del kardex después de cada cierre; el último punto es su foto más reciente.</span></div>`
        +`<div class="iar-analisis-cuerpo"><div class="iar-cambios"><h4>Qué más cambió · ${P.meses.length?ss(D.cambios.total):'Sin historia'}</h4>${P.meses.length?curva(D.h,false,P.meses):'<p class="iar-vacio">Sin historia disponible.</p>'}`
        +lista(G,'cambios',[['prod','Producto'],['antes','Antes','v'],['ahora','Última foto','v'],['delta','Cambio','v']],P.meses.length?D.cambios.top:[])
        +`<p class="iar-nota">${P.meses.length?`${D.cambios.n} productos cambiaron al menos S/ 1. El resto explica ${ss(D.cambios.resto)}. Se incluyen los que se vaciaron.`:'No hay fotos históricas disponibles para comparar.'}</p></div><div class="iar-alertas"><h4>Dónde mirar</h4><div class="iar-alerta"><small>Días de inventario del recorte</small><b>${D.dias==null?'Sin base':D.dias>365?'Más de 365':sn(D.dias)}</b><p>Al ritmo de consumo del restaurante entero en 90 días.</p></div>`
        +states.map(([k,n])=>`<button class="iar-alerta" data-a="ir" data-v="${k}" ${!P.analisis||!D.rs.length?'disabled':''}><small>${n}</small><b>${P.analisis?sn(D.estados[k]):'Sin datos'}</b><p>${P.analisis?ss(ssum(D.prods.filter(r=>r.estado===k),'v')):'Falta historia o consumo para este análisis.'} · Ver productos ↑</p></button>`).join('')+'</div></div></section>';
    }
    root.innerHTML=html;
    scroll.forEach(([id,top,left])=>{const e=root.querySelector(`[data-tabla="${id}"]`);if(e){e.scrollTop=top;e.scrollLeft=left;}});
    if(f){const e=root.querySelector(`[data-input="${f[0]}"]`);if(e){e.focus({preventScroll:true});e.setSelectionRange(f[1],f[2]);}}
  }
  function exportar(G){const {P,s,D}=G,hoja=(nombre,cols,filas)=>({nombre,cabeza:cols.map(c=>c[1]),decimales:6,filas:filas.map(r=>cols.map(c=>r[c[0]]??''))});
    const contexto=[['Vista','Stock por área y familia'],['Modo',s.modo],['Recorte',ruta(G)],...Object.entries(P.contexto).map(([k,v])=>[k,v.join(', ')||'Todos']),['Área A',s.a??''],['Área B',s.b??''],['Búsqueda',s.modo==='Excluidos'?s.exq:s.q],['Referencia histórica',P.meses[s.ref]||'Sin historia'],['Última foto kardex',P.momentos.at(-1)||'Sin historia'],['Stock actual','Maestro de inventario activo; los excluidos van separados.'],['Consumo','Restaurante entero, 90 días; no es el consumo de cada área.'],['Cantidades','Sólo por código y unidad. No hay total entre unidades distintas.']];
    if(s.modo==='Excluidos')return[hoja('Excluidos',G.exCols,G.tablas.excluidos.filas),{nombre:'Contexto',cabeza:['Dato','Selección'],filas:[...contexto,['Área excluida',s.exArea??'Todas'],['Motivo excluido',s.motivo??'Todos']]}];
    const out=[hoja('Áreas',[['rotulo','Área'],['v','Valorizado'],['pct','% positivo']],D.areas),hoja('Familias',[['rotulo','Familia'],['v','Valorizado'],['pct','% positivo']],D.familias),hoja('Subfamilias',[['rotulo','Subfamilia'],['v','Valorizado'],['pct','% positivo']],D.subfamilias)];
    if(s.modo==='Comparar'&&s.a!=null&&s.b!=null&&s.a!==s.b)out.push(hoja('Comparación',G.compCols,G.tablas.comparar.filas));
    if(s.modo==='Matriz')out.push({nombre:'Matriz',cabeza:['Familia',...D.matriz.areas],decimales:6,filas:D.matriz.filas.map(r=>[r.rotulo,...r.cells.map(c=>s.metrica==='Negativos'?c.neg:c.v)])});
    out.push(hoja('Productos del recorte',[['cod','Código'],['prod','Producto'],['um','Unidad'],['q','Cantidad'],['v','Valorizado']],D.prods.map(r=>({...r,q:r.mixed?null:r.q,um:r.mixed?'Unidades incompatibles':r.um}))),
      {nombre:'Historia del recorte',cabeza:['Momento','Fecha de foto','Valorizado'],decimales:6,filas:P.meses.map((m,i)=>[m,P.momentos[i],D.h[i]])},
      hoja('Mayores cambios',[['cod','Código'],['prod','Producto'],['antes','Antes'],['ahora','Última foto'],['delta','Cambio'],['vacio','Se vació en maestro']],D.cambios.top),
      {nombre:'Contexto',cabeza:['Dato','Selección'],filas:[...contexto,['Métrica matriz',s.metrica],['Días del conjunto',D.dias??'Sin base']]});return out;
  }
  function montar({data:P,parentElement,setTriggerValue}){
    const old=window.__inventarioAreas;old?.abort.abort();let root=parentElement.querySelector('.iar');if(!root){root=document.createElement('div');root.className='iar';parentElement.appendChild(root);}
    const B=sleer(P),E=P.excluidos?sleer(P.excluidos):null,s=old?.s||inicial(P,B);
    if(old&&old.P.sello!==P.sello){const etiqueta=old.P.meses[old.s.ref],i=P.meses.indexOf(etiqueta);s.ref=i>=0?i:P.ref_default;}
    if(!(s.ref>=0&&s.ref<P.meses.length))s.ref=P.ref_default;
    const G={P,B,E,s,root,enviar:setTriggerValue,tablas:{},cache:{},abort:new AbortController()};window.__inventarioAreas=G;
    const signal=G.abort.signal;
    root.addEventListener('click',e=>{const b=e.target.closest('[data-a]');if(!b)return;const{a,v,id}=b.dataset;
      if(a==='modo')s.modo=v;else if(a==='area'){s.area=s.area===v&&v!==TODO?(P.default_area??TODO):v;s.fam=null;s.sub=null;}
      else if(a==='fam'){s.fam=s.fam===v?null:v;s.sub=null;}else if(a==='sub')s.sub=s.sub===v?null:v;
      else if(a==='soltar'){s.fam=null;s.sub=null;}else if(a==='celda'){s.area=b.dataset.area;s.fam=b.dataset.fam;s.sub=null;}
      else if(a==='comparar')s.comparar=v;else if(a==='metrica')s.metrica=v;
      else if(a==='orden'){const o=s.orden[id];s.orden[id]={k:v,d:o?.k===v?-o.d:1};}
      else if(a==='excel'){bajar('Stock_por_area.xlsx',libro(exportar(G)));return;}
      else if(a==='ir'){G.enviar('ir',{sello:P.sello,areas:G.D.elegidas,fams:s.fam==null?[]:[s.fam],subs:s.sub==null?[]:[s.sub],chip:v});return;}
      dibujar(G);
    },{signal});
    root.addEventListener('change',e=>{const k=e.target.dataset.select;if(!k)return;s[k]=k==='ref'?Number(e.target.value):e.target.value==='__sin__'?null:e.target.value;dibujar(G);},{signal});
    root.addEventListener('input',e=>{const k=e.target.dataset.input;if(k){s[k]=e.target.value;dibujar(G);}},{signal});
    root.addEventListener('keydown',e=>{const tr=e.target.closest('tr[data-a]');if(tr&&(e.key==='Enter'||e.key===' ')){e.preventDefault();tr.click();}},{signal});
    root.addEventListener('scroll',e=>{const el=e.target,t=G.tablas[el.dataset?.tabla];if(t&&el.scrollTop+el.clientHeight>=el.scrollHeight-180&&t.n<t.filas.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',listRows(G,el.dataset.tabla,t.n,t.n+150));t.n+=150;}},{signal,capture:true});
    dibujar(G);return()=>G.abort.abort();
  }
  return{montar,inicial,calcular,rank,matriz,comparar,cambios,exportar};
})();
window.__areasDatos=AREAS;
export default function(component){return AREAS.montar(component);}
