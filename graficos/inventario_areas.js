/* Área y familia: exploración, matriz y comparación sobre el mismo stock (#724). */
const AREAS=(()=>{
  const TODO='__todas__';
  const lab=(B,k,v)=>v==null?'':(k==='area'?v:B.P.rotulos[k==='sub'?'subfam':k]?.[v])||v||`Sin ${k==='fam'?'familia':k==='sub'?'subfamilia':'área'}`;
  function rank(rows,k,B){
    const rs=[...sgroup(rows,r=>r[k])].map(([nombre,g])=>({nombre,rotulo:lab(B,k,nombre),v:ssum(g,'v'),
      h:B.P.meses.map((_,i)=>g.reduce((a,r)=>a+(r.h[i]||0),0)),productos:new Set(g.map(r=>r.cod)).size,conStock:new Set(g.filter(r=>Math.abs(r.q)>SEPS||Math.abs(r.v)>SEPS).map(r=>r.cod)).size,
      neg:new Set(g.filter(r=>r.q<0).map(r=>r.cod)).size})).sort((a,b)=>b.v-a.v||scmp(a.nombre,b.nombre));
    const pos=ssum(rs.filter(r=>r.v>0),'v');return rs.map(r=>({...r,pct:r.v>=0&&pos>0?r.v/pos*100:null}));
  }
  function inicial(P,B){const areas=rank(B.rows,'area',B);return {modo:'Lista',area:TODO,fam:null,sub:null,prof:'Área',abiertos:{},
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
  const seg=(ops,v,a)=>`<div class="ist-seg" role="group">${ops.map(op=>btn(a,op,op,v===op)).join('')}</div>`;
  function ruta(G){const s=G.s,B=G.B;return[s.modo==='Comparar'?`${s.a??'—'} / ${s.b??'—'}`:s.area===TODO?'Todas las áreas':lab(B,'area',s.area),
    s.fam!=null?lab(B,'fam',s.fam):null,s.sub!=null?lab(B,'sub',s.sub):null].filter(v=>v!=null).join(' › ');}
  function matrizHTML(G){const M=G.D.matriz,s=G.s,mide=c=>s.metrica==='Negativos'?c.neg:Math.abs(c.v),cols=M.areas.map((a,i)=>[a,i]).filter(([,i])=>M.filas.some(r=>Math.abs(r.cells[i].v)>=.5||r.cells[i].neg)),max=Math.max(1,...M.filas.flatMap(r=>r.cells.map(mide)));
    return`<div class="ist-wrap iar-matriz ${s.metrica==='Negativos'?'neg':''}"><table><thead><tr><th>Familia / Área</th>${cols.map(([a])=>`<th title="${se(a)}">${se(G.B.P.rotulos.area?.[a]||a)}</th>`).join('')}</tr></thead><tbody>${M.filas.map(r=>`<tr><td title="${se(r.rotulo)}">${se(r.rotulo)}</td>${cols.map(([a,i])=>{const c=r.cells[i],vacio=Math.abs(c.v)<.5&&!c.neg;return`<td><button data-a="celda" data-area="${se(a)}" data-fam="${se(r.nombre)}" style="--nivel:${vacio?0:(.1+Math.sqrt(mide(c)/max)*.9).toFixed(3)}" class="${c.v<0?'neg':''} ${s.area===a&&s.fam===r.nombre?'on':''}" title="${se(r.rotulo+' · '+a)}: ${ss(c.v)} · ${c.neg} productos con cantidad negativa, por ${ss(c.negV)}">${vacio?'—':s.metrica==='Negativos'?sn(c.neg):se(sv0(c.v))}</button></td>`;}).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  function arbol(G){const {s,B}=G,hayH=B.P.meses.length>0,niv={'Área':0,Familia:1,Subfamilia:2}[s.prof],out=[];
    const pct=r=>r.pct==null?'—':`${Math.round(r.pct)} %`,con=rs=>rs.filter(r=>r.conStock>0||Math.abs(r.v)>=.5);
    const fila=(r,n,key,ind,attrs,on,hoja=false)=>{const ab=!hoja&&(s.abiertos[key]??niv>n);
      out.push(`<tr class="ist-n${n} ${on?'chosen':''}"><td class="i" title="${se(r.rotulo)}"><span class="ist-fila" style="padding-left:${ind}px">${hoja?'<span class="ist-mk0"></span>':`<button class="ist-mk" data-a="abrir" data-v="${se(key)}" data-ab="${ab?1:0}" aria-expanded="${ab}" aria-label="Abrir o cerrar">${ab?'▾':'▸'}</button>`}<button class="ist-tn" ${attrs} aria-pressed="${on}"><span class="nm">${se(r.rotulo)}</span></button></span></td><td class="val ${r.v<0?'rojo':''}">${se(sv0(r.v))}</td><td>${pct(r)}</td><td>${sn(r.conStock)}</td><td class="${r.neg?'rojo':''}">${r.neg?sn(r.neg):'—'}</td>${hayH?`<td class="t">${smini(r.h)}</td>`:''}</tr>`);return ab;};
    const nodo=(a,f,u)=>`data-a="nodo" data-area="${se(a)}" data-fam="${se(f)}" data-sub="${se(u??'')}" data-tiene-sub="${u==null?0:1}"`;
    for(const a of con(rank(B.rows,'area',B))){const rowsA=B.rows.filter(r=>r.area===a.nombre);
      if(fila(a,0,a.nombre,2,`data-a="area" data-v="${se(a.nombre)}"`,s.area===a.nombre&&s.fam==null))
        for(const f of con(rank(rowsA,'fam',B))){const rowsF=rowsA.filter(r=>r.fam===f.nombre),k=a.nombre+'|'+f.nombre;
          if(fila(f,1,k,16,nodo(a.nombre,f.nombre),s.area===a.nombre&&s.fam===f.nombre&&s.sub==null))
            for(const u of con(rank(rowsF,'sub',B)))fila(u,2,k+'|'+u.nombre,32,nodo(a.nombre,f.nombre,u.nombre),s.area===a.nombre&&s.fam===f.nombre&&s.sub===u.nombre,true);}}
    const t=rank(B.rows.map(r=>({...r,__t:1})),'__t',B)[0]||{v:0,conStock:0,neg:0,h:[]};
    return`<div class="ist-wrap ist-arbol"><table><thead><tr><th class="i">Área › Familia › Subfamilia</th><th class="w-v">Valor S/</th><th class="w-p" title="Entre sus vecinos con valor positivo; un negativo no es participación">%</th><th class="w-n">Productos</th><th class="w-n">Negativos</th>${hayH?`<th class="w-t">${B.P.meses.length} meses</th>`:''}</tr></thead><tbody><tr class="tot ist-n0 ${s.area===TODO&&s.fam==null?'chosen':''}"><td class="i" style="padding:0"><span class="ist-fila" style="padding-left:2px"><span class="ist-mk0"></span><button class="ist-tn" data-a="area" data-v="${TODO}" aria-pressed="${s.area===TODO}"><span class="nm">Todas las áreas</span></button></span></td><td class="val">${se(sv0(t.v))}</td><td>—</td><td>${sn(t.conStock)}</td><td class="${t.neg?'rojo':''}">${t.neg?sn(t.neg):'—'}</td>${hayH?`<td class="t">${smini(t.h)}</td>`:''}</tr>${out.join('')}</tbody></table></div>`;
  }
  function kpis(G){const {D,P,s}=G,n=P.meses.length,de=k=>D.prods.filter(r=>r.estado===k),oper=rs=>ssum(rs.filter(r=>soperacion(r,P)),'v'),dis=!P.analisis||!D.rs.length;
    const quien=s.modo==='Comparar'?'las dos áreas':s.area!==TODO||s.fam!=null?'lo elegido':'todas las áreas',txt=rs=>`${sn(rs.length)} productos${oper(rs)>.5?` · ${ss(oper(rs),0)} son de operación`:''}`;
    const kp=(k,o)=>skpiBtn({attrs:`data-a="ir" data-v="${k}"`,dis,tip:'Ver esos productos en «Por producto»',...o});
    return skpiBtn({attrs:'data-a="ir" data-v="todos"',dis:!D.rs.length,tip:'Ver sus productos en «Por producto»',rot:`Valorizado · ${quien}`,val:ss(D.total,0),sub:`${sn(D.stock)} productos${P.analisis?` · ${sdiasTxt(D.dias)} días de inventario`:''}`,h:n?D.h:null})
      +(P.analisis?kp('sin',{rot:'Sin consumo en 90 días',val:ss(ssum(de('sin'),'v'),0),sub:txt(de('sin')),h:sserie(de('sin'),n)})+kp('alto',{rot:`Más de ${P.umbral} días de stock`,val:ss(ssum(de('alto'),'v'),0),sub:txt(de('alto')),h:sserie(de('alto'),n)})+kp('neg',{rot:'En negativo',val:ss(ssum(de('neg'),'v'),0),sub:`${sn(de('neg').length)} productos · ver cuáles →`,h:sserie(de('neg'),n),neg:true})
        :['Sin consumo en 90 días',`Más de ${P.umbral} días de stock`,'En negativo'].map((rot,i)=>kp(['sin','alto','neg'][i],{rot,val:'Sin datos',sub:'Falta historia o consumo'})).join(''));
  }
  function ficha(G){const {D,P,s,B}=G,ru=ruta(G),partes=ru.split(' › '),sel=s.area!==TODO||s.fam!=null,n=P.meses.length,ref=Math.min(s.ref,Math.max(0,n-1));
    const cab=`<div class="ist-fcab"><div class="ist-ftit"><span class="ist-miga">${se(partes.length>1?partes.slice(0,-1).join(' › '):sel?'Área':'Stock')}</span><h3 title="${se(ru)}">${se(partes.at(-1))}</h3><span class="ist-fsub">${sn(D.stock)} productos con stock · ${se(ss(D.total,0))}</span></div>${sel?'<button class="ist-mini-btn" data-a="soltar">Soltar</button>':''}</div>`;
    if(!n)return`${cab}<p class="ist-aviso">Sin historia disponible.</p>`;
    return`${cab}<div class="ist-evcab"><select class="ist-men" data-select="ref" aria-label="Contra qué mes">${P.meses.slice(0,-1).map((m,i)=>`<option value="${i}" ${i===ref?'selected':''}>Contra ${se(m)}</option>`).join('')}</select><span class="ist-dif">${se(sd0(D.cambios.total))} de cambio</span><span class="ist-esp"></span><button class="ist-mini-btn" data-a="ir" data-v="todos" ${!D.rs.length?'disabled':''}>Ver sus productos →</button></div>${scurvaFicha(D.h,P.meses,ref)}<div class="ist-lista">${D.cambios.top.map(r=>`<div class="ist-tp"><span class="n" title="${se(r.prod)}">${se(r.prod)}</span><small>${sn(r.antes)} → ${sn(r.ahora)}</small><b>${se(sd0(r.delta))}</b></div>`).join('')}</div><p class="ist-nota">${sn(D.cambios.n)} productos cambiaron al menos S/ 1; el resto explica ${se(sd0(D.cambios.resto))}. Incluye los que se vaciaron. Precios del kardex, después de cada cierre.</p>`;
  }
  function lista(G,id,cols,filas){const o=G.s.orden[id];let fs=filas.slice();if(o)fs.sort((a,b)=>{const x=a[o.k],y=b[o.k];if(x==null)return y==null?0:1;if(y==null)return-1;return(typeof x==='number'&&typeof y==='number'?x-y:scmp(String(x),String(y)))*o.d;});G.tablas[id]={cols,filas:fs,n:150};
    return`<div class="ist-wrap iar-tabla" data-tabla="${id}" tabindex="0"><table><thead><tr>${cols.map(c=>`<th class="${c[2]?'num':''}"><button data-a="orden" data-id="${id}" data-v="${c[0]}">${se(c[1])}${o?.k===c[0]?o.d===1?' ↑':' ↓':''}</button></th>`).join('')}</tr></thead><tbody>${listRows(G,id,0,150)}</tbody></table>${fs.length?'':'<p class="ist-aviso">Sin filas con esta selección.</p>'}</div>`;
  }
  function form(v,t){return t==='v'?ss(v):t==='q'?sv(v):v??'';}
  function listRows(G,id,a,b){const t=G.tablas[id];return t.filas.slice(a,b).map(r=>`<tr>${t.cols.map(c=>`<td class="${c[2]?'num':''}" title="${se(form(r[c[0]],c[2]))}">${se(form(r[c[0]],c[2]))}</td>`).join('')}</tr>`).join('');}
  function select(G,k,ops,v,label){const offered=[...ops];if(v!=null&&!offered.includes(v))offered.push(v);return`<label>${label}<select data-select="${k}"><option value="__sin__">${k==='a'||k==='b'?'Elegir área':'Todos'}</option>${offered.map(x=>`<option value="${se(x)}" ${x===v?'selected':''}>${se(x||'Sin dato')}</option>`).join('')}</select></label>`;}
  function dibujar(G){const {root,s,P,B}=G;G.D=calcular(B,s,G.E,G.cache);const D=G.D;G.tablas={};
    const active=root.querySelector('input:focus'),f=active?[active.dataset.input,active.selectionStart,active.selectionEnd]:null;
    const scroll=[...root.querySelectorAll('.ist-wrap')].map((e,i)=>[e.dataset.tabla||i,e.scrollTop,e.scrollLeft]);
    const zonas=seg(['Lista','Matriz','Comparar',...(D.excluidos.length?['Excluidos']:[])],s.modo,'modo');
    const busca=s.modo==='Matriz'?['q','Buscar familia…',s.q]:s.modo==='Comparar'?['q','Buscar…',s.q]:s.modo==='Excluidos'?['exq','Buscar código o motivo…',s.exq]:null;
    let html=`<div class="ist-cab iar-cab">${s.modo==='Excluidos'?select(G,'exArea',[...new Set(D.excluidos.map(r=>r.area))].sort(),s.exArea,'Área'):''}${busca?`<input type="search" class="ist-busca" data-input="${busca[0]}" aria-label="${se(busca[1])}" placeholder="${se(busca[1])}" value="${se(busca[2])}">`:''}<button class="ist-pil" data-a="excel" title="Baja lo que se ve">Excel ↓</button></div><div class="ist-kpis">${kpis(G)}</div>`;
    if(s.modo==='Lista')html+=`<div class="ist-cuerpo"><section class="ist-izq iar-main"><div class="ist-fl">${zonas}<span class="ist-esp"></span><span class="ist-lb">Abrir hasta ${seg(['Área','Familia','Subfamilia'],s.prof,'prof')}</span></div>${arbol(G)}</section><aside class="ist-ficha iar-analisis" aria-label="Ficha">${ficha(G)}</aside></div>`;
    else if(s.modo==='Matriz')html+=`<div class="ist-ancho"><div class="ist-fl">${zonas}${seg(['Valor','Negativos'],s.metrica,'metrica')}</div>${matrizHTML(G)}<p class="ist-nota">${s.metrica==='Negativos'?'Productos distintos con cantidad negativa en cada celda; el tooltip conserva su valorizado.':'Valorizado neto por familia y área; los negativos llevan su signo.'} Un clic en una celda abre esa familia en la lista, con su ficha.</p></div>`;
    else if(s.modo==='Comparar'){
      const cols=s.comparar==='Productos'?[['cod','Código'],['nombre','Producto'],['um','Unidad'],['qa','Cantidad A','q'],['qb','Cantidad B','q']]:[['nombre','Familia'],['na','Con stock A','q'],['nb','Con stock B','q']];
      G.compCols=[...cols,['a','Valor A','v'],['b','Valor B','v'],['delta','B − A','v']];
      html+=`<div class="ist-ancho"><div class="ist-fl">${zonas}${select(G,'a',D.areas.map(r=>r.nombre),s.a,'Área A')}${select(G,'b',D.areas.map(r=>r.nombre),s.b,'Área B')}${seg(['Familias','Productos'],s.comparar,'comparar')}</div>${s.a==null||s.b==null||s.a===s.b?'<p class="ist-aviso">Elegí dos áreas distintas disponibles en los filtros de la página.</p>':lista(G,'comparar',G.compCols,D.comparacion)}<p class="ist-nota">B − A compara existencias; no es una recomendación de transferencia. Cantidades separadas por código y unidad; no se suman unidades distintas.</p></div>`;
    }else{
      G.exCols=[['cod','Código'],['prod','Producto'],['area','Área'],['motivo','Por qué'],['um','Unidad'],['q','Cantidad','q'],['precio','Precio','v'],['v','Valorizado','v']];
      const exf=[...D.exfilas].sort((a,b)=>Math.abs(b.v)-Math.abs(a.v)),por=[...sgroup(D.excluidos,r=>r.motivo)].map(([m,g])=>[m,ssum(g,'v')]).sort((a,b)=>Math.abs(b[1])-Math.abs(a[1]));
      html+=`<div class="ist-ancho"><div class="ist-fl">${zonas}<div class="ist-seg" role="group" aria-label="Motivo">${btn('motivo','',`Todos · ${ss(D.exTotal,0)}`,s.motivo==null)}${por.map(([m,v])=>btn('motivo',m,`${m} · ${ss(v,0)}`,s.motivo===m)).join('')}</div></div>${lista(G,'excluidos',G.exCols,exf)}<p class="ist-nota">No suman al stock: inactivos, servicios y artículos o áreas no habilitados; sólo filas con stock o valorizado. Total excluido: ${ss(D.exTotal)}.</p></div>`;
    }
    root.innerHTML=html;
    const nuevas=[...root.querySelectorAll('.ist-wrap')];scroll.forEach(([id,top,left],i)=>{const e=nuevas.find(x=>x.dataset.tabla===id)||nuevas[i];if(e&&(!e.dataset.tabla||e.dataset.tabla===id)){e.scrollTop=top;e.scrollLeft=left;}});
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
    const old=window.__inventarioAreas;old?.abort.abort();let root=parentElement.querySelector('.iar');if(!root){root=document.createElement('div');root.className='iar ist';parentElement.appendChild(root);}
    const B=sleer(P),E=P.excluidos?sleer(P.excluidos):null,s=old?.s||inicial(P,B);
    if(old&&old.P.sello!==P.sello){const etiqueta=old.P.meses[old.s.ref],i=P.meses.indexOf(etiqueta);s.ref=i>=0?i:P.ref_default;}
    if(!(s.ref>=0&&s.ref<P.meses.length))s.ref=P.ref_default;
    const G={P,B,E,s,root,enviar:setTriggerValue,tablas:{},cache:{},abort:new AbortController()};window.__inventarioAreas=G;
    const signal=G.abort.signal;
    root.addEventListener('click',e=>{const b=e.target.closest('[data-a]');if(!b)return;const{a,v,id}=b.dataset;
      if(a==='modo')s.modo=v;else if(a==='area'){s.area=s.area===v&&v!==TODO&&s.fam==null?TODO:v;s.fam=null;s.sub=null;}
      else if(a==='nodo'){const u=b.dataset.tieneSub==='1'?b.dataset.sub:null,igual=s.area===b.dataset.area&&s.fam===b.dataset.fam&&s.sub===u;s.area=igual?TODO:b.dataset.area;s.fam=igual?null:b.dataset.fam;s.sub=igual?null:u;}
      else if(a==='abrir')s.abiertos={...s.abiertos,[v]:b.dataset.ab!=='1'};else if(a==='prof'){s.prof=v;s.abiertos={};}
      else if(a==='motivo')s.motivo=v||null;
      else if(a==='fam'){s.fam=s.fam===v?null:v;s.sub=null;}else if(a==='sub')s.sub=s.sub===v?null:v;
      else if(a==='soltar'){s.area=TODO;s.fam=null;s.sub=null;}else if(a==='celda'){s.area=b.dataset.area;s.fam=b.dataset.fam;s.sub=null;s.abiertos={...s.abiertos,[b.dataset.area]:true};s.modo='Lista';}
      else if(a==='comparar')s.comparar=v;else if(a==='metrica')s.metrica=v;
      else if(a==='orden'){const o=s.orden[id];s.orden[id]={k:v,d:o?.k===v?-o.d:1};}
      else if(a==='excel'){bajar('Stock_por_area.xlsx',libro(exportar(G)));return;}
      else if(a==='ir'){G.enviar('ir',{sello:P.sello,areas:G.D.elegidas,fams:s.fam==null?[]:[s.fam],subs:s.sub==null?[]:[s.sub],chip:v});return;}
      dibujar(G);
    },{signal});
    root.addEventListener('change',e=>{const k=e.target.dataset.select;if(!k)return;s[k]=k==='ref'?Number(e.target.value):e.target.value==='__sin__'?null:e.target.value;dibujar(G);},{signal});
    root.addEventListener('input',e=>{const k=e.target.dataset.input;if(k){s[k]=e.target.value;dibujar(G);}},{signal});
    root.addEventListener('scroll',e=>{const el=e.target,t=G.tablas[el.dataset?.tabla];if(t&&el.scrollTop+el.clientHeight>=el.scrollHeight-180&&t.n<t.filas.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',listRows(G,el.dataset.tabla,t.n,t.n+150));t.n+=150;}},{signal,capture:true});
    dibujar(G);return()=>G.abort.abort();
  }
  return{montar,inicial,calcular,rank,matriz,comparar,cambios,exportar};
})();
window.__areasDatos=AREAS;
export default function(component){return AREAS.montar(component);}
