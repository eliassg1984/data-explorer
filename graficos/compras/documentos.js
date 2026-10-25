/* Detalle docs. Controles locales; fecha y aviso del ranking releen Python (#726). */
const DOCS=(()=>{
  const CAMPOS=['Proveedor','Fecha','Documento','Producto','Periodo','Unidad','Cantidad','Precio informado','Valor'];
  const METRICAS=['Valor','Cantidad','Precio informado','Precio medio'];
  const nf=new Intl.NumberFormat('es-PE',{minimumFractionDigits:2,maximumFractionDigits:2}),qf=new Intl.NumberFormat('es-PE',{maximumFractionDigits:6});
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm=v=>String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const cmp=(a,b)=>a<b?-1:a>b?1:0,fecha=v=>v?v.split('-').reverse().join('/'):'Sin fecha';
  const money=v=>v==null?'—':'S/ '+nf.format(v),numero=v=>v==null?'—':qf.format(v);
  const suma=(rs,k)=>{let s=0,c=0;for(const r of rs){const v=r[k]-c,t=s+v;c=t-s-v;s=t;}return s;};
  const limpiaUM=v=>!['','nan','none','<na>'].includes(String(v).trim().toLowerCase());
  function inicial(v={}){return{modo:'Tabla dinámica',gran:'Mes',proveedores:null,q:'',importe:'Todos',doc:null,config:false,
    filas:['Proveedor','Fecha','Documento','Producto'],columnas:['Periodo'],metricas:[{campo:'Valor',aggr:'Suma'}],abiertos:[],orden:null,nCols:12,...v};}
  function leer(P){return P.lineas.map((r,id)=>{const d=P.documentos[r[3]],prov=P.proveedores[r[0]],prod=P.productos[r[1]];
    return{prov:r[0],prod:r[1],fecha:r[2],doc:r[3],q:r[4],v:r[5],pu:r[6],um:r[7],id,
      buscar:norm([prov[0],prov[1],prod,d[3],d[4]].join(' '))};});}
  function acc(){return{n:0,v:0,vc:0,q:0,qc:0,pu:0,puc:0,pn:0,vmin:null,vmax:null,qmin:null,qmax:null,pmin:null,pmax:null,prods:new Set(),ums:new Set()};}
  function mas(a,l){a.n++;for(const [k,c,x] of [['v','vc',l.v],['q','qc',l.q]]){const y=x-a[c],t=a[k]+y;a[c]=t-a[k]-y;a[k]=t;}
    for(const [k,x] of [['v',l.v],['q',l.q],['p',l.pu]])if(x!=null){a[k+'min']=a[k+'min']==null?x:Math.min(a[k+'min'],x);a[k+'max']=a[k+'max']==null?x:Math.max(a[k+'max'],x);}
    if(l.pu!=null){const y=l.pu-a.puc,t=a.pu+y;a.puc=t-a.pu-y;a.pu=t;a.pn++;}a.prods.add(l.prod);a.ums.add(l.um);return a;}
  function valor(a,m,P){if(!a)return null;
    if(m.aggr==='Conteo')return m.campo==='Precio informado'?a.pn:a.n;
    const compatible=a.ums.size===1&&limpiaUM(P.unidades[[...a.ums][0]]);
    if(m.campo==='Cantidad'&&!compatible)return null;
    if(m.campo.startsWith('Precio')&&(!compatible||a.prods.size!==1))return null;
    if(m.campo==='Precio medio')return a.q>0?a.v/a.q:null;
    const k=m.campo==='Valor'?'v':m.campo==='Cantidad'?'q':'p';
    if(m.aggr==='Mínimo')return a[k+'min'];if(m.aggr==='Máximo')return a[k+'max'];
    if(m.aggr==='Media')return k==='p'?(a.pn?a.pu/a.pn:null):a.n?a[k]/a.n:null;
    return k==='p'?null:a[k];
  }
  function dimension(l,f,P,s){return f==='Proveedor'?l.prov:f==='Producto'?l.prod:f==='Fecha'?(P.fechas[l.fecha]||'~sinfecha'):f==='Documento'?l.doc:f==='Unidad'?l.um:f==='Cantidad'?l.q:f==='Valor'?l.v:f==='Precio informado'?(l.pu??'~sindato'):P.calendario[s.gran].por_fecha[l.fecha];}
  function rotulo(v,f,P,s){return f==='Proveedor'?P.proveedores[v][1]:f==='Producto'?P.productos[v]:f==='Fecha'?fecha(v==='~sinfecha'?null:v):f==='Documento'?(P.documentos[v][4]+(P.documentos[v][5]?'':` · línea ${+v+1}`)):f==='Unidad'?(P.unidades[v]||'Sin unidad'):f==='Cantidad'?numero(v):f==='Valor'||f==='Precio informado'?(v==='~sindato'?'Sin dato':'S/ '+numero(v)):P.calendario[s.gran].rotulos[v]||v;}
  function comparar(a,b,f,P,s){if(f==='Proveedor'||f==='Producto'||f==='Unidad')return cmp(rotulo(a,f,P,s),rotulo(b,f,P,s));if(f==='Documento'){const x=P.documentos[a],y=P.documentos[b];return cmp(P.fechas[x[2]]||'~',P.fechas[y[2]]||'~')||cmp(x[3],y[3]);}if(f==='Cantidad'||f==='Valor'||f==='Precio informado')return a==='~sindato'?b==='~sindato'?0:1:b==='~sindato'?-1:a-b;return cmp(a,b);}
  function nodo(id='',campo=null,val=null,prof=0,camino=[]){return{id,campo,val,prof,camino,hijos:new Map(),celdas:new Map(),total:acc()};}
  function pivot(rs,P,s){const raiz=nodo(),columnas=new Map();
    for(const l of rs){const co=s.columnas.map(f=>dimension(l,f,P,s)),ck=JSON.stringify(co);columnas.set(ck,co);let n=raiz;
      const poner=()=>{mas(n.total,l);if(!n.celdas.has(ck))n.celdas.set(ck,acc());mas(n.celdas.get(ck),l);};poner();
      s.filas.forEach((f,i)=>{const v=dimension(l,f,P,s),key=JSON.stringify([f,v]);if(!n.hijos.has(key)){const camino=[...n.camino,v];n.hijos.set(key,nodo(JSON.stringify(camino),f,v,i+1,camino));}n=n.hijos.get(key);poner();});
    }
    const cols=[...columnas].sort((a,b)=>{for(let i=0;i<s.columnas.length;i++){const c=comparar(a[1][i],b[1][i],s.columnas[i],P,s);if(c)return c;}return 0;});
    return{raiz,columnas:cols};
  }
  function listaDocs(rs,P,completos){const m=new Map();for(const l of rs){if(!m.has(l.doc))m.set(l.doc,[]);m.get(l.doc).push(l);}
    return[...m].map(([doc,ls])=>{const d=P.documentos[doc],t=completos.get(doc);return{doc,key:d[0],proveedor:P.proveedores[d[1]][1],fecha:P.fechas[d[2]],numero:d[4],raw:d[3],identificado:d[5],valor:suma(ls,'v'),completo:t.valor,lineas:ls.length,todas:t.lineas,productos:new Set(ls.map(l=>l.prod)).size};})
      .sort((a,b)=>cmp(b.fecha||'',a.fecha||'')||cmp(a.proveedor,b.proveedor)||cmp(a.numero,b.numero));}
  function calcular(P,s,cache={}){
    if(cache.sello!==P.sello){cache.sello=P.sello;cache.base=leer(P);cache.completos=new Map();const porProv=new Map();for(const l of cache.base){if(!cache.completos.has(l.doc))cache.completos.set(l.doc,[]);cache.completos.get(l.doc).push(l);porProv.set(l.prov,(porProv.get(l.prov)||0)+l.v);}cache.rank=[...porProv].sort((a,b)=>b[1]-a[1]).map(([i])=>i);cache.completos=new Map([...cache.completos].map(([doc,ls])=>[doc,{ls,valor:suma(ls,'v'),lineas:ls.length}]));cache.filtro=null;}
    const fk=JSON.stringify([s.proveedores,s.q,s.importe]);
    if(cache.filtro!==fk){const ps=s.proveedores==null?null:new Set(s.proveedores),qs=norm(s.q).split(/\s+/).filter(Boolean);
      cache.alcance=cache.base.filter(l=>ps==null||ps.has(P.proveedores[l.prov][0]));
      cache.rs=cache.alcance.filter(l=>qs.every(q=>l.buscar.includes(q))&&(s.importe==='Todos'||s.importe==='Positivos'&&l.v>0||s.importe==='Negativos'&&l.v<0||s.importe==='Cero'&&l.v===0));
      cache.docs=listaDocs(cache.rs,P,cache.completos);cache.filtro=fk;cache.pk=null;
    }
    const pk=JSON.stringify([fk,s.gran,s.filas,s.columnas]);if(cache.pk!==pk){cache.piv=pivot(cache.rs,P,s);cache.pk=pk;}
    const rs=cache.rs,conNumero=cache.docs.filter(d=>d.identificado),resumen={valor:suma(rs,'v'),documentos:conNumero.length,proveedores:new Set(rs.map(l=>l.prov)).size,
      productos:new Set(rs.map(l=>l.prod)).size,lineas:rs.length,sinNumero:rs.filter(l=>!P.documentos[l.doc][5]).length,sinFecha:rs.filter(l=>P.fechas[l.fecha]==null).length};
    const doc=P.documentos.findIndex(d=>d[0]===s.doc),ficha=doc>=0&&cache.alcance.some(l=>l.doc===doc)?{doc,...cache.completos.get(doc)}:null;
    return{rs,docs:cache.docs,resumen,piv:cache.piv,ficha,base:cache.base,alcance:cache.alcance,rank:cache.rank};
  }
  function mover(s,campo,eje,pos){if(!CAMPOS.includes(campo)||!['filas','columnas'].includes(eje))return;
    const viejo=s[eje].indexOf(campo);s.filas=s.filas.filter(f=>f!==campo);s.columnas=s.columnas.filter(f=>f!==campo);
    let i=pos==null?s[eje].length:pos;if(pos!=null&&viejo>=0&&viejo<i)i--;s[eje].splice(Math.max(0,i),0,campo);s.abiertos=[];s.nCols=12;s.orden=null;}
  const op=(v,t,actual)=>`<option value="${esc(v)}" ${v===actual?'selected':''}>${esc(t)}</option>`;
  function select(k,t,ops,v){return`<label>${esc(t)} <select data-select="${k}" aria-label="${esc(t)}">${ops.map(x=>op(x,x,v)).join('')}</select></label>`;}
  function botones(ops,v,a){return`<div class="dc-seg">${ops.map(x=>`<button data-a="${a}" data-v="${esc(x)}" class="${x===v?'on':''}" aria-pressed="${x===v}">${esc(x)}</button>`).join('')}</div>`;}
  function filtros(G){const {P,s,D}=G,rank=D.rank.map(i=>({p:P.proveedores[i]}));
    return`<details class="dc-provs"><summary>Proveedores: ${s.proveedores==null?'todos':s.proveedores.length}</summary><div class="dc-popup"><div class="dc-bar">${['Todos','3','5','10','Ninguno'].map(x=>`<button data-a="provtop" data-v="${x}">${x==='3'?'Top 3':x}</button>`).join('')}</div><input data-provq placeholder="Buscar proveedor…" aria-label="Buscar proveedor"><div class="dc-provlista">${rank.map(({p})=>`<label data-provnombre="${esc(norm(p.join(' ')))}"><input type="checkbox" data-prov="${esc(p[0])}" ${s.proveedores==null||s.proveedores.includes(p[0])?'checked':''}>${esc(p[1])}</label>`).join('')}</div></div></details>`;
  }
  function configuracion(G){const s=G.s;
    const eje=e=>`<div class="dc-eje" data-eje="${e}"><b>${e==='filas'?'Filas':'Columnas'}</b><div class="dc-tags">${s[e].map((f,i)=>`<span draggable="true" data-campo="${f}" data-desde="${e}" data-pos="${i}">${f}<button data-a="mover" data-eje="${e}" data-i="${i}" data-dir="-1" aria-label="Subir ${f}" ${i===0?'disabled':''}>↑</button><button data-a="mover" data-eje="${e}" data-i="${i}" data-dir="1" aria-label="Bajar ${f}" ${i===s[e].length-1?'disabled':''}>↓</button><button data-a="quitar" data-eje="${e}" data-v="${f}" aria-label="Quitar ${f}">×</button></span>`).join('')}</div><select data-add="${e}" aria-label="Añadir a ${e}"><option value="">Añadir campo…</option>${CAMPOS.filter(f=>!s[e].includes(f)).map(f=>op(f,f,'')).join('')}</select></div>`;
    return`<div class="dc-config"><p>Arrastrá los campos entre Filas y Columnas o usá las flechas. La fecha de la página permanece compartida con Proveedores.</p>${eje('filas')}${eje('columnas')}<div class="dc-valores"><b>Valores</b>${METRICAS.map(f=>{const m=s.metricas.find(m=>m.campo===f),ags=f==='Precio medio'?['Ponderado']:f==='Precio informado'?['Media','Mínimo','Máximo','Conteo']:['Suma','Media','Mínimo','Máximo','Conteo'];return`<label><input type="checkbox" data-metrica="${f}" ${m?'checked':''}>${f}<select data-aggr="${f}" aria-label="Cálculo de ${f}" ${m?'':'disabled'}>${ags.map(a=>op(a,a,m?.aggr||ags[0])).join('')}</select></label>`;}).join('')}</div><button data-a="restaurar">Restaurar tabla</button></div>`;
  }
  function columnasLista(modo){return modo==='Documentos'?[['fecha','Fecha'],['proveedor','Proveedor'],['numero','Documento'],['valor','Valor visible','v'],['completo','Documento completo','v'],['lineas','Líneas visibles','n'],['todas','Líneas completas','n']]:[['fecha','Fecha'],['proveedor','Proveedor'],['numero','Documento'],['producto','Producto'],['unidad','Unidad'],['q','Cantidad','n'],['pu','Precio informado','v'],['medio','Valor / cantidad','v'],['v','Valor','v']];}
  function lineasTabla(rs,P){return rs.map(l=>({key:P.documentos[l.doc][0],fecha:P.fechas[l.fecha],proveedor:P.proveedores[l.prov][1],numero:P.documentos[l.doc][4],producto:P.productos[l.prod],unidad:P.unidades[l.um]||'Sin unidad',q:l.q,pu:l.pu,medio:l.q>0?l.v/l.q:null,v:l.v}));}
  function form(v,t){return t==='v'?money(v):t==='n'?numero(v):t==='fecha'?fecha(v):String(v??'');}
  function tablaLista(G,id,cols,filas){let rs=filas.slice();const o=G.s.orden;if(o?.id===id)rs.sort((a,b)=>{const x=a[o.k],y=b[o.k];return x==null?y==null?0:1:y==null?-1:(typeof x==='number'?x-y:cmp(x,y))*o.d;});
    G.tablas[id]={cols,rs,n:150};return`<div class="dc-scroll" data-tabla="${id}" tabindex="0"><table><thead><tr>${cols.map(([k,t])=>`<th><button data-a="orden" data-id="${id}" data-v="${k}">${esc(t)}${o?.id===id&&o.k===k?o.d===1?' ↑':' ↓':''}</button></th>`).join('')}</tr></thead><tbody>${filasLista(G,id,0,150)}</tbody></table>${rs.length?'':'<p class="dc-vacio">No hay registros con estos filtros. Cambiá la búsqueda o elegí Todos.</p>'}</div>`;
  }
  function filasLista(G,id,a,b){const t=G.tablas[id];return t.rs.slice(a,b).map(r=>`<tr ${id==='ficha'?'':`data-a="doc" data-v="${r.key}" tabindex="0"`} class="${r.key===G.s.doc&&id!=='ficha'?'on':''}">${t.cols.map(([k,,f])=>`<td class="${f?'num':''}" title="${esc(typeof r[k]==='number'?numero(r[k]):form(r[k],k==='fecha'?'fecha':f))}">${esc(form(r[k],k==='fecha'?'fecha':f))}</td>`).join('')}</tr>`).join('');}
  function ordenarNodos(n,G){const {s,P}=G,os=s.orden,rs=[...n.hijos.values()];return rs.sort((a,b)=>{if(os?.id==='pivot'&&os.metric!=null){const x=valor(os.col==null?a.total:a.celdas.get(os.col),s.metricas[os.metric],P),y=valor(os.col==null?b.total:b.celdas.get(os.col),s.metricas[os.metric],P);if(x==null||y==null)return x==null?(y==null?0:1):-1;return(x-y)*os.d||comparar(a.val,b.val,a.campo,P,s);}return comparar(a.val,b.val,a.campo,P,s)*(os?.id==='pivot'&&os.metric==null?os.d:1);});}
  function aplanar(G,todo=false){const rs=[],ab=new Set(G.s.abiertos);const visitar=n=>{for(const h of ordenarNodos(n,G)){if(!todo||!h.hijos.size)rs.push(h);if(todo||ab.has(h.id))visitar(h);}};if(!G.s.filas.length)return[G.D.piv.raiz];visitar(G.D.piv.raiz);return rs;}
  const nombreM=m=>`${m.campo} · ${m.aggr}`;
  function fmtM(v,m){return m.aggr==='Conteo'||m.campo==='Cantidad'?numero(v):money(v);}
  function cuerpoPivot(G,a,b){const t=G.tablas.pivot;return t.rs.slice(a,b).map(n=>{const {s,P}=G,hojas=n.hijos.size,ab=s.abiertos.includes(n.id),nombre=n.campo?rotulo(n.val,n.campo,P,s):'Total',boton=hojas?`<button data-a="abrir" data-v="${esc(n.id)}" aria-label="${ab?'Contraer':'Expandir'} ${esc(nombre)}" aria-expanded="${ab}">${ab?'▾':'▸'}</button>`:'';
    return`<tr><td class="dc-nombre"><div style="padding-left:${Math.max(0,n.prof-1)*12}px">${boton}<span title="${esc(nombre)}">${esc(nombre)}</span>${n.campo==='Documento'?`<button data-a="doc" data-v="${P.documentos[n.val][0]}" aria-label="Ver documento ${esc(nombre)}">↗</button>`:''}</div></td>${t.cols.map(([ck])=>s.metricas.map(m=>{const v=valor(n.celdas.get(ck),m,P);return`<td class="num" title="${v==null?'Sin dato o unidades/productos no comparables':numero(v)}">${fmtM(v,m)}</td>`;}).join('')).join('')}${t.total?s.metricas.map(m=>`<td class="num dc-total">${fmtM(valor(n.total,m,P),m)}</td>`).join(''):''}</tr>`;}).join('');}
  function tablaPivot(G){const {s,P,D}=G,cols=D.piv.columnas.slice(0,s.nCols),total=s.columnas.length>0,rs=aplanar(G),o=s.orden;G.tablas.pivot={cols,rs,n:150,total};
    const header=(rot,ck)=>s.metricas.map((m,i)=>`<th><button data-a="sortpivot" data-v="${esc(ck??'~total')}" data-i="${i}" title="${esc(nombreM(m))}">${esc(rot)}<small>${esc(nombreM(m))}${o?.id==='pivot'&&o.col===ck&&o.metric===i?o.d===1?' ↑':' ↓':''}</small></button></th>`).join('');
    return`<div class="dc-pivot-info"><span>${rs.length} filas desplegadas · ${cols.length}/${D.piv.columnas.length} grupos de columnas</span>${cols.length<D.piv.columnas.length?'<button data-a="mascols">Más columnas</button>':''}<button data-a="plegar">Contraer todo</button></div><div class="dc-scroll" data-tabla="pivot" tabindex="0"><table><thead><tr><th class="dc-nombre"><button data-a="sortnombre">${esc(s.filas.join(' / ')||'Total')}</button></th>${cols.map(([ck,vs])=>header(vs.map((v,i)=>rotulo(v,s.columnas[i],P,s)).join(' / ')||'Selección',ck)).join('')}${total?header('Total',null):''}</tr></thead><tbody>${cuerpoPivot(G,0,150)}</tbody><tfoot><tr><th class="dc-nombre">TOTAL DE LA SELECCIÓN</th>${cols.map(([ck])=>s.metricas.map(m=>`<td class="num">${fmtM(valor(D.piv.raiz.celdas.get(ck),m,P),m)}</td>`).join('')).join('')}${total?s.metricas.map(m=>`<td class="num">${fmtM(valor(D.piv.raiz.total,m,P),m)}</td>`).join(''):''}</tr></tfoot></table>${rs.length?'':'<p class="dc-vacio">No hay registros. Los filtros y la fecha siguen disponibles.</p>'}</div>`;
  }
  function pintar(G){const {P,s,root}=G;G.D=calcular(P,s,G.cache);const D=G.D,R=D.resumen;
    if(!D.ficha)s.doc=null;
    const input=root.querySelector('[data-input=q]:focus'),f=input?[input.selectionStart,input.selectionEnd]:null;
    const provAbierto=root.querySelector('.dc-provs')?.open,provQ=root.querySelector('[data-provq]')?.value||'';
    const pos=G.resetScroll?[]:[...root.querySelectorAll('[data-tabla]')].map(e=>[e.dataset.tabla,e.scrollTop,e.scrollLeft]);G.resetScroll=false;G.tablas={};
    let h=`<section class="dc-card dc-main"><header><h3>Detalle de documentos</h3><p>Mismo rango y selección del ranking de Proveedores.</p></header><div class="dc-bar">${botones(['Documentos','Líneas','Tabla dinámica'],s.modo,'modo')}<span class="dc-acciones"><button data-a="excel" ${!D.rs.length?'disabled':''}>Excel ↓</button><button data-a="fullscreen" aria-label="Pantalla completa">⛶</button></span></div><div class="dc-bar dc-filtros">${filtros(G)}<input data-input="q" type="search" value="${esc(s.q)}" placeholder="Documento, proveedor o producto…" aria-label="Buscar documentos">${select('importe','Importes',['Todos','Positivos','Negativos','Cero'],s.importe)}</div><div class="dc-kpis"><span><b>${money(R.valor)}</b>Importe visible</span><span><b>${R.documentos}</b>Documentos con número</span><span><b>${R.proveedores}</b>Proveedores</span><span><b>${R.productos}</b>Productos</span></div>`;
    if(s.modo==='Tabla dinámica')h+=`<div class="dc-bar">${select('gran','Período',P.granos,s.gran)}<button data-a="config" aria-expanded="${s.config}">Configurar tabla ${s.config?'▴':'▾'}</button>${s.config?'<span>Filas, columnas y cálculos</span>':''}</div>${s.config?configuracion(G):''}`+tablaPivot(G);
    else h+=tablaLista(G,s.modo==='Documentos'?'docs':'lineas',columnasLista(s.modo),s.modo==='Documentos'?D.docs:lineasTabla(D.rs,P));
    h+=`<p class="dc-nota">${R.lineas} líneas · ${R.sinNumero} sin número de documento · ${R.sinFecha} sin fecha. ${s.modo==='Tabla dinámica'?'Cantidad sólo suma unidades compatibles; los precios requieren un producto y una unidad. Precio informado conserva la media simple; Precio medio usa valor/cantidad.':'Valor visible aplica la búsqueda; la ficha muestra el documento completo dentro de los filtros de la página.'}</p></section>`;
    if(D.ficha){const F=D.ficha,d=P.documentos[F.doc],unidades=new Set(F.ls.map(l=>l.um));h+=`<section class="dc-card dc-ficha"><div class="dc-bar"><h3>${d[5]?'Documento':'Línea sin número'} · ${esc(d[4])}</h3><button data-a="cerrar">Cerrar ficha ×</button></div><p>${esc(P.proveedores[d[1]][1])} · ${fecha(P.fechas[d[2]])}</p><div class="dc-kpis"><span><b>${money(F.valor)}</b>Documento completo</span><span><b>${F.lineas}</b>Líneas</span><span><b>${new Set(F.ls.map(l=>l.prod)).size}</b>Productos</span><span><b>${unidades.size}</b>Unidades de medida</span></div><p class="dc-nota">Incluye todas sus líneas disponibles en el rango y las familias de la página. La búsqueda y el filtro de importes no recortan esta ficha. Los importes incluyen las notas de crédito ya aplicadas por Compras.</p>`+tablaLista(G,'ficha',columnasLista('Líneas').filter(([k])=>!['proveedor','numero','fecha'].includes(k)),lineasTabla(F.ls,P))+'</section>';}
    root.innerHTML=h;pos.forEach(([id,top,left])=>{const e=root.querySelector(`[data-tabla="${id}"]`);if(e){e.scrollTop=top;e.scrollLeft=left;}});
    if(provAbierto)root.querySelector('.dc-provs').open=true;if(provQ){root.querySelector('[data-provq]').value=provQ;root.querySelectorAll('[data-provnombre]').forEach(l=>l.hidden=!l.dataset.provnombre.includes(norm(provQ)));}
    G.ro?.disconnect();const cfg=root.querySelector('.dc-config'),main=root.querySelector('.dc-main');
    if(cfg){const ubicar=()=>{if(window.innerWidth<=800){cfg.style.top='';cfg.style.maxHeight='';return;}const b=root.querySelector('[data-a=config]').getBoundingClientRect(),m=main.getBoundingClientRect(),top=b.bottom-m.top+6;cfg.style.top=top+'px';cfg.style.maxHeight=Math.max(100,m.height-top-18)+'px';};G.ro=new ResizeObserver(ubicar);G.ro.observe(main);ubicar();}
    if(f){const e=root.querySelector('[data-input=q]');e.focus({preventScroll:true});e.setSelectionRange(...f);}
  }
  function exportar(G){const {P,s,D}=G,hoja=(nombre,cols,rs)=>({nombre,cabeza:cols.map(c=>c[1]),decimales:6,filas:rs.map(r=>cols.map(([k])=>r[k]??''))});
    const docs=hoja('Documentos',columnasLista('Documentos'),G.tablas.docs?.rs||D.docs),ls=hoja('Líneas filtradas',columnasLista('Líneas'),G.tablas.lineas?.rs||lineasTabla(D.rs,P));
    const headers=[...s.filas,...D.piv.columnas.flatMap(([,vs])=>s.metricas.map(m=>(vs.map((v,i)=>rotulo(v,s.columnas[i],P,s)).join(' / ')||'Selección')+' · '+nombreM(m))),...(s.columnas.length?s.metricas.map(m=>'Total · '+nombreM(m)):[])];
    const filas=aplanar(G,true).map(n=>[...n.camino.map((v,i)=>rotulo(v,s.filas[i],P,s)),...D.piv.columnas.flatMap(([ck])=>s.metricas.map(m=>valor(n.celdas.get(ck),m,P))),...(s.columnas.length?s.metricas.map(m=>valor(n.total,m,P)):[])]);
    if(s.filas.length)filas.push(['TOTAL',...s.filas.slice(1).map(()=>''),...D.piv.columnas.flatMap(([ck])=>s.metricas.map(m=>valor(D.piv.raiz.celdas.get(ck),m,P))),...(s.columnas.length?s.metricas.map(m=>valor(D.piv.raiz.total,m,P)):[])]);
    const contexto=[['Vista','Compras · Detalle de documentos'],['Rango compartido con Proveedores',P.rango?.join(' → ')||'Sin rango con fechas'],...Object.entries(P.contexto).map(([k,v])=>[k,v.join(', ')||'Todas']),['Proveedores locales',s.proveedores==null?'Todos los del ranking':s.proveedores.join(', ')||'Ninguno'],['Buscar',s.q],['Importes',s.importe],['Vista activa',s.modo],['Período del pivote',s.gran],['Filas del pivote',s.filas.join(' → ')||'Total'],['Columnas del pivote',s.columnas.join(' → ')||'Sin eje'],['Valores',s.metricas.map(nombreM).join(', ')],['Importe visible',D.resumen.valor],['Documentos con número',D.resumen.documentos],['Líneas sin número',D.resumen.sinNumero],['Líneas sin fecha',D.resumen.sinFecha],['Documentos','Identidad = proveedor + fecha + número original; sin número se conserva cada línea, sin inventar documentos.'],['Ficha','Completa dentro del rango, familias y proveedores cargados. Buscar e Importes no la recortan.'],['Cantidades','Sin suma entre unidades distintas o desconocidas. Los precios agregados requieren un producto y una unidad.'],['Precio informado','Media simple de los precios unitarios de las líneas, como el pivote anterior. No equivale al precio medio ponderado.'],['Precio medio','Valor total / cantidad total positiva de un producto y una unidad.'],['Tabla dinámica','Exporta todos los grupos de columnas y las hojas de la jerarquía, más el total; no duplica subtotales intermedios.'],['Precisión','Valores numéricos con seis decimales. Cantidades y valores se suman sin redondear las líneas.']];
    const hojas=[docs,ls,{nombre:'Tabla dinámica',cabeza:headers,decimales:6,filas},{nombre:'Contexto',cabeza:['Dato','Selección'],decimales:6,filas:contexto}];
    if(D.ficha)hojas.push(hoja('Ficha completa',columnasLista('Líneas'),lineasTabla(D.ficha.ls,P)));return hojas;
  }
  function montar({data:P,parentElement,setTriggerValue}){const old=window.__comprasDocs;old?.abort.abort();old?.ro?.disconnect();let root=parentElement.querySelector('.dc');if(!root){root=document.createElement('div');root.className='dc';parentElement.appendChild(root);}const s=old?.s||inicial(P.inicial);
    if(old&&old.P.sello!==P.sello){s.abiertos=[];if(old.P.documentos.find(d=>d[0]===s.doc)?.[5]===false)s.doc=null;}
    if(!['Documentos','Líneas','Tabla dinámica'].includes(s.modo))s.modo='Tabla dinámica';if(!P.granos.includes(s.gran))s.gran='Mes';
    if(s.proveedores!=null)s.proveedores=s.proveedores.filter(p=>P.proveedores.some(x=>x[0]===p));
    const G={P,s,root,cache:{},abort:new AbortController(),tablas:{}};window.__comprasDocs=G;const signal=G.abort.signal;
    G.selloRank=window.__cpProv?.rankData?.sello;
    window.addEventListener('compras-proveedores-cambio',e=>{const d=e.detail;if(!root.isConnected||!G.selloRank||!d||d.sello!==G.selloRank||JSON.stringify(d.rango)!==JSON.stringify(P.rango))return;
      const siguiente=JSON.stringify([...d.sel].sort()),actual=JSON.stringify([...(P.contexto['Proveedores del ranking']||[])].sort());
      if(siguiente===actual||siguiente===G.pedido)return;G.pedido=siguiente;setTriggerValue?.('ranking',{sello:P.sello});
    },{signal});
    root.addEventListener('click',e=>{const b=e.target.closest('[data-a]');if(!b)return;const {a,v,id,eje,i,dir}=b.dataset;let scroll=null;
      if(a==='modo'){s.modo=v;s.orden=null;G.resetScroll=true;}else if(a==='config')s.config=!s.config;
      else if(a==='provtop'){s.proveedores=v==='Todos'?null:v==='Ninguno'?[]:G.D.rank.slice(0,+v).map(i=>P.proveedores[i][0]);G.resetScroll=true;}
      else if(a==='doc'){s.doc=v;scroll='.dc-ficha';}
      else if(a==='cerrar'){s.doc=null;scroll='.dc-main';}
      else if(a==='abrir')s.abiertos=s.abiertos.includes(v)?s.abiertos.filter(x=>x!==v):[...s.abiertos,v];
      else if(a==='plegar')s.abiertos=[];else if(a==='mascols')s.nCols+=12;
      else if(a==='restaurar'){s.filas=['Proveedor','Fecha','Documento','Producto'];s.columnas=['Periodo'];s.metricas=[{campo:'Valor',aggr:'Suma'}];s.abiertos=[];s.nCols=12;s.orden=null;}
      else if(a==='quitar'){s[eje]=s[eje].filter(f=>f!==v);s.abiertos=[];s.orden=null;}
      else if(a==='mover'){const x=+i,y=x+(+dir);[s[eje][x],s[eje][y]]=[s[eje][y],s[eje][x]];s.abiertos=[];s.orden=null;}
      else if(a==='orden'){const o=s.orden;s.orden={id,k:v,d:o?.id===id&&o.k===v?-o.d:1};G.resetScroll=true;}
      else if(a==='sortnombre'){const o=s.orden;s.orden={id:'pivot',metric:null,d:o?.id==='pivot'&&o.metric==null?-o.d:1};}
      else if(a==='sortpivot'){const o=s.orden,col=v==='~total'?null:v;s.orden={id:'pivot',col,metric:+i,d:o?.id==='pivot'&&o.col===col&&o.metric===+i?-o.d:1};}
      else if(a==='excel'){bajar('Compras_detalle_documentos.xlsx',libro(exportar(G)));return;}
      else if(a==='fullscreen'){if(document.fullscreenElement)document.exitFullscreen();else root.requestFullscreen?.().catch(()=>{});return;}
      pintar(G);if(scroll)root.querySelector(scroll)?.scrollIntoView({block:'start'});
    },{signal});
    root.addEventListener('input',e=>{if(e.target.dataset.input==='q'){s.q=e.target.value;G.resetScroll=true;pintar(G);}else if(e.target.hasAttribute('data-provq')){const q=norm(e.target.value);root.querySelectorAll('[data-provnombre]').forEach(l=>l.hidden=!l.dataset.provnombre.includes(q));}},{signal});
    root.addEventListener('change',e=>{const t=e.target,k=t.dataset.select;
      if(k){s[k]=t.value;if(k==='gran'){s.abiertos=[];s.orden=null;}G.resetScroll=true;}
      else if(t.hasAttribute('data-prov')){const p=t.dataset.prov,actual=new Set(s.proveedores??P.proveedores.map(x=>x[0]));if(t.checked)actual.add(p);else actual.delete(p);s.proveedores=actual.size===P.proveedores.length?null:[...actual];G.resetScroll=true;}
      else if(t.dataset.add){if(!t.value)return;mover(s,t.value,t.dataset.add);}
      else if(t.dataset.metrica){const f=t.dataset.metrica;if(t.checked)s.metricas.push({campo:f,aggr:f==='Precio medio'?'Ponderado':f==='Precio informado'?'Media':'Suma'});else if(s.metricas.length>1)s.metricas=s.metricas.filter(m=>m.campo!==f);}
      else if(t.dataset.aggr){const m=s.metricas.find(m=>m.campo===t.dataset.aggr);if(m)m.aggr=t.value;}
      else return;pintar(G);
    },{signal});
    root.addEventListener('keydown',e=>{const el=e.target.closest('tr[data-a]');if(el&&(e.key==='Enter'||e.key===' ')){e.preventDefault();el.click();}},{signal});
    root.addEventListener('scroll',e=>{const el=e.target,id=el.dataset?.tabla,t=G.tablas[id];if(t&&el.scrollTop+el.clientHeight>=el.scrollHeight-160&&t.n<t.rs.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',id==='pivot'?cuerpoPivot(G,t.n,t.n+150):filasLista(G,id,t.n,t.n+150));t.n+=150;}},{signal,capture:true});
    root.addEventListener('dragstart',e=>{const el=e.target.closest('[data-campo]');if(el)e.dataTransfer.setData('text/plain',el.dataset.campo);},{signal});
    root.addEventListener('dragover',e=>{if(e.target.closest('[data-eje]'))e.preventDefault();},{signal});
    root.addEventListener('drop',e=>{const eje=e.target.closest('[data-eje]'),tag=e.target.closest('[data-pos]');if(!eje)return;e.preventDefault();mover(s,e.dataTransfer.getData('text/plain'),eje.dataset.eje,tag?+tag.dataset.pos:null);pintar(G);},{signal});
    pintar(G);return()=>{G.abort.abort();G.ro?.disconnect();};
  }
  return{inicial,leer,calcular,pivot,valor,dimension,rotulo,mover,aplanar,exportar,pintar,montar};
})();
window.__docsDatos=DOCS;
export default function(component){return DOCS.montar(component);}
