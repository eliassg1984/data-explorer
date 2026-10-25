/* Costo por unidad útil: cálculo local y trazabilidad de la atribución (#729). */
const PVU=(()=>{
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const texto=v=>String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const cmp=(a,b)=>String(a).localeCompare(String(b),'es');
  const fmt=new Intl.NumberFormat('es-PE',{maximumFractionDigits:2});
  const num=v=>v==null||!Number.isFinite(v)?'Sin base':fmt.format(v);
  const sol=v=>v==null||!Number.isFinite(v)?'Sin base':`S/ ${num(v)}`;
  const pct=v=>v==null?'Sin base':`${num(v*100)} %`;
  const sum=(rs,k)=>rs.reduce((a,r)=>a+(r[k]??0),0);
  const med=vs=>{const a=vs.filter(v=>v!=null).sort((a,b)=>a-b),n=a.length;return n?(a[Math.floor((n-1)/2)]+a[Math.floor(n/2)])/2:null;};
  const fecha=v=>v?`${v.slice(8,10)}/${v.slice(5,7)}/${v.slice(0,4)}`:'—';
  function estado(v={}){return{ventana:'12 meses',unico:false,prod:null,prov:null,contra:null,modo:'Proveedores',q:'',dq:'',todos:false,orden:{},...v};}
  function agrupar(rows,P){
    const gs=new Map();for(const r of rows){if(r.prov==null||!(r.costo>0))continue;if(!gs.has(r.prov))gs.set(r.prov,[]);gs.get(r.prov).push(r);}
    return [...gs].map(([id,rs])=>{const cant=sum(rs,'cant'),merma=sum(rs,'merma'),costo=sum(rs,'costo'),queda=cant-merma;
      return{id,n:rs.length,cant,merma,costo,queda,pct:cant?merma/cant:null,pkg:cant?costo/cant:null,util:queda>0?costo/queda:null,dias:med(rs.map(r=>r.dias)),nombre:P.proveedores[id],rows:rs};
    }).sort((a,b)=>(a.n<P.min_porc)-(b.n<P.min_porc)||(a.util==null)-(b.util==null)||(a.util??0)-(b.util??0)||cmp(a.nombre,b.nombre));
  }
  function partes(t,P){
    const ok=t.filter(r=>r.n>=P.min_porc&&r.queda>0);if(ok.length<2)return null;
    const mejor=ok.reduce((a,r)=>r.util<a.util?r:a),peor=ok.reduce((a,r)=>r.util>a.util?r:a);
    const montos=ok.map(r=>({id:r.id,valor:(r.util-mejor.util)*r.queda,queda:r.queda}));
    return{mejor:mejor.id,peor:peor.id,minimo:mejor.util,extra:sum(montos,'valor'),montos};
  }
  function comparar(a,b){
    if(!a||!b||!(a.cant>0&&b.cant>0&&a.queda>0&&b.queda>0))return null;
    const ya=a.queda/a.cant,yb=b.queda/b.cant;
    return{delta:b.util-a.util,precio:(b.pkg-a.pkg)*(1/ya+1/yb)/2,rendimiento:(a.pkg+b.pkg)/2*(1/yb-1/ya),a:a.id,b:b.id};
  }
  function calcular(P,s){
    const v=P.ventanas[s.ventana],rows=v?P.filas.filter(r=>r.fecha>=v.ini&&r.fecha<v.fin):[];
    const atribuidas=rows.filter(r=>!s.unico||r.unico),gs=new Map();
    for(const r of atribuidas){if(!gs.has(r.prod))gs.set(r.prod,[]);gs.get(r.prod).push(r);}
    const productos=[...gs].map(([id,rs])=>{const t=agrupar(rs,P),pm=partes(t,P);return{id,...P.productos[id],t,pm,extra:pm?.extra??0,n:rs.length};})
      .sort((a,b)=>b.extra-a.extra||cmp(a.cod,b.cod)||cmp(a.unid,b.unid));
    const ranking=productos.filter(r=>r.pm),q=texto(s.q);
    const visibles=(s.todos?productos:ranking).filter(r=>!q||texto([r.cod,r.nombre,r.unid,...r.t.map(t=>t.nombre)].join(' ')).includes(q));
    const foco=productos.find(r=>r.id===s.prod)||visibles[0]||null,t=foco?.t??[],pm=foco?.pm??null;
    const sel=t.find(r=>r.id===s.prov)||t.find(r=>r.id===pm?.mejor)||t[0]||null;
    const contra=t.find(r=>r.id===s.contra&&r.id!==sel?.id)||t.find(r=>r.id===pm?.peor&&r.id!==sel?.id)||t.find(r=>r.id!==sel?.id)||null;
    const detalle=rows.filter(r=>r.prod===foco?.id),trace=sel?.rows??[],dq=texto(s.dq);
    return{rows,atribuidas,productos,ranking,visibles,foco,t,pm,sel,contra,comparacion:comparar(sel,contra),
      trace:trace.slice().sort((a,b)=>cmp(a.fecha,b.fecha)),rastro:trace.filter(r=>!dq||texto([r.doc,r.area,r.otro,fecha(r.compra),fecha(r.fecha)].join(' ')).includes(dq)).sort((a,b)=>cmp(a.fecha,b.fecha)),
      extra:sum(ranking,'extra'),asignadas:rows.filter(r=>r.prov!=null).length,ambiguas:rows.filter(r=>r.prov!=null&&!r.unico).length,
      sin:detalle.filter(r=>r.prov==null||(s.unico&&!r.unico)).length,sinCosto:detalle.filter(r=>r.prov!=null&&(!s.unico||r.unico)&&!(r.costo>0)).length};
  }
  const col=(k,n,t='texto')=>({k,n,t});
  function columnas(G,tipo){const u=G.D.foco?.unid||'unidad';
    if(tipo==='rank')return[col('nombre','Producto'),col('unid','UM'),col('extra','Pagado de más','sol'),col('mejor','Mejor'),col('util_mejor','S/ útil','sol'),col('peor','Más caro')];
    if(tipo==='prov')return[col('nombre','Proveedor'),col('rol','Muestra'),col('n','Porc.','num'),col('pct','Merma','pct'),col('pkg',`S/ por ${u}`,'sol'),col('util',`S/ por ${u} útil`,'sol'),col('dias','Días','num')];
    return[col('doc','N.º porc.'),col('fecha','Fecha','fecha'),col('cant',`Entró (${u})`,'num'),col('merma',`Merma (${u})`,'num'),col('pct','Merma %','pct'),col('pkg','S/ del día','sol'),col('compra','Compra atribuida','fecha'),col('pcompra','S/ compra','sol'),col('otro','Otro proveedor cercano'),col('f_otro','Fecha de otro','fecha'),col('area','Área')];
  }
  function listas(G){const{P,D}=G;return{
    rank:D.visibles.map(r=>({...r,mejor:r.pm?P.proveedores[r.pm.mejor]:'Sin comparación',peor:r.pm?P.proveedores[r.pm.peor]:'—',util_mejor:r.pm?.minimo??null})),
    prov:D.t.map(r=>({...r,rol:r.n<P.min_porc?'Pocos registros':r.util==null?'Sin base útil':r.id===D.pm?.mejor?'Mejor':r.id===D.pm?.peor?'Más caro':'Comparable'})),
    rastro:D.rastro.map(r=>({...r,pkg:r.cant>0?r.costo/r.cant:null}))};}
  function celda(v,c){return c.t==='sol'?sol(v):c.t==='num'?num(v):c.t==='pct'?pct(v):c.t==='fecha'?fecha(v):String(v??'—');}
  function ordenar(rs,cfg){if(!cfg)return rs;const[k,asc]=cfg;return rs.slice().sort((a,b)=>(a[k]==null)-(b[k]==null)||(typeof a[k]==='number'&&typeof b[k]==='number'?(a[k]-b[k])*asc:cmp(a[k]??'',b[k]??'')*asc));}
  function renglones(G,t,ini,fin){return t.rows.slice(ini,fin).map(r=>{
    const action=t.id==='rank'?'producto':t.id==='prov'?'proveedor':null,elegido=t.id==='rank'?r.id===G.D.foco?.id:t.id==='prov'?r.id===G.D.sel?.id:false;
    return`<tr ${action?`data-a="${action}" data-v="${r.id}" tabindex="0" aria-selected="${elegido}"`:''} class="${elegido?'on':''}">${t.cols.map(c=>`<td class="${c.t!=='texto'&&c.t!=='fecha'?'pvu-num':''} ${t.id==='rastro'&&c.k==='pkg'&&r.difiere?'pvu-alerta':''}" title="${esc(c.n+': '+(r[c.k]??'Sin base'))}">${esc(celda(r[c.k],c))}</td>`).join('')}</tr>`;
    }).join('');}
  function tabla(G,id,rows){const t={id,rows:ordenar(rows,G.s.orden[id]),cols:columnas(G,id),n:150};G.tablas[id]=t;
    return`<div class="pvu-scroll" data-tabla="${id}"><table><thead><tr>${t.cols.map(c=>`<th><button data-a="orden" data-t="${id}" data-v="${c.k}">${esc(c.n)}</button></th>`).join('')}</tr></thead><tbody>${renglones(G,t,0,150)}</tbody></table>${rows.length?'':'<p class="pvu-vacio">Sin filas para esta selección.</p>'}</div>`;
  }
  function ficha(G){const{D}=G,r=D.sel,u=D.foco?.unid||'unidad';if(!r)return'<p>Sin proveedor con costo positivo.</p>';
    return`<details class="pvu-ficha" open><summary>Cómo sale · ${esc(r.nombre)}</summary><p>Merma: ${num(r.merma)} ÷ ${num(r.cant)} ${esc(u)} = <b>${pct(r.pct)}</b></p><p>Costo de entrada: ${sol(r.costo)} ÷ ${num(r.cant)} ${esc(u)} = <b>${sol(r.pkg)}</b></p><p>Costo útil: ${sol(r.costo)} ÷ (${num(r.cant)} − ${num(r.merma)}) ${esc(u)} = <b>${sol(r.util)}</b></p>${D.pm?`<p>Pagado de más del producto: Σ (costo útil − ${sol(D.pm.minimo)}) × cantidad útil, entre proveedores con al menos ${G.P.min_porc} registros = <b>${sol(D.pm.extra)}</b>.</p>`:''}<p>${D.sin} porcionamientos sin atribución válida${G.s.unico?' con proveedor único':''}; ${D.sinCosto} con proveedor y sin costo positivo quedan fuera.</p></details>`;
  }
  function comparacion(G){const{D}=G,a=D.sel,b=D.contra,c=D.comparacion;if(!a||!b)return'<p>Se necesitan dos proveedores para comparar.</p>';
    return`<div class="pvu-comparar"><label>Comparar con <select data-k="contra">${D.t.filter(r=>r.id!==a.id).map(r=>`<option value="${r.id}" ${r.id===b.id?'selected':''}>${esc(r.nombre)}</option>`).join('')}</select></label><div class="pvu-dos">${[a,b].map(r=>`<div><span>${esc(r.nombre)}</span><b>${sol(r.util)} / ${esc(D.foco.unid)} útil</b><small>Entrada ${sol(r.pkg)} · rendimiento ${pct(r.cant>0?r.queda/r.cant:null)} · ${r.n} registros${r.n<G.P.min_porc?' · muestra insuficiente para competir':''}</small></div>`).join('')}</div>${c?`<p>B − A: <b>${sol(c.delta)}</b> por unidad útil = precio de entrada ${sol(c.precio)} + rendimiento ${sol(c.rendimiento)}.</p><small>Reparto simétrico de ambos factores. Explica la diferencia observada; las compras son atribuidas.</small>`:'<p>Sin base positiva para separar precio y rendimiento.</p>'}</div>`;
  }
  function dibujar(G){const{P,s,raiz}=G,activo=raiz.contains(document.activeElement)?document.activeElement:null,k=activo?.dataset.k,pos=activo?.selectionStart;
    G.D=calcular(P,s);const D=G.D;if(D.foco)s.prod=D.foco.id;if(D.sel)s.prov=D.sel.id;if(D.contra)s.contra=D.contra.id;G.tablas={};const L=listas(G);
    raiz.innerHTML=`<section class="pvu-main"><header><div><h3>Costo por unidad útil, por proveedor</h3><p>${esc(P.ventanas[s.ventana]?.rotulo??'Sin fechas disponibles')} · costo del día</p></div><button data-a="excel">Excel de esta vista ↓</button></header><div class="pvu-controles"><div class="pvu-seg">${Object.keys(P.ventanas).map(v=>`<button data-a="ventana" data-v="${esc(v)}" class="${s.ventana===v?'on':''}" aria-pressed="${s.ventana===v}">${esc(v)}</button>`).join('')}</div><label><input type="checkbox" data-k="unico" ${s.unico?'checked':''}> Sólo proveedor único en los ${P.dias_unico} días previos</label></div><p class="pvu-nota">Proveedor atribuido a la última compra hasta ${P.dias_proveedor} días antes. El Almacén no registra el lote de origen.</p><div class="pvu-kpis"><div><span>Pagado de más · comparables</span><b>${sol(D.extra)}</b></div><div><span>Productos comparables</span><b>${D.ranking.length}</b></div><div><span>Con proveedor atribuido</span><b>${D.asignadas} / ${D.rows.length}</b></div><div><span>Atribución ambigua</span><b>${D.ambiguas}</b></div></div>${P.compras_disponibles?'':'<p class="pvu-alerta">No se pudo leer Compras: no hay atribución de proveedores.</p>'}<div class="pvu-cuerpo"><div class="pvu-panel"><h4>Dónde pesa más el proveedor</h4><div class="pvu-filtros"><input type="search" data-k="q" value="${esc(s.q)}" placeholder="Buscar producto o proveedor…" aria-label="Buscar producto o proveedor"><label><input type="checkbox" data-k="todos" ${s.todos?'checked':''}> Incluir sin comparación</label></div>${tabla(G,'rank',L.rank)}<small>Mínimo ${P.min_porc} porcionamientos por proveedor y dos proveedores con cantidad útil positiva. Productos separados por unidad.</small></div><div class="pvu-panel pvu-derecha"><h4>${esc(D.foco?D.foco.nombre+' · '+D.foco.unid:'Sin productos comparables')}</h4><div class="pvu-seg">${['Proveedores','Comparar','Porcionamientos'].map(m=>`<button data-a="modo" data-v="${m}" class="${s.modo===m?'on':''}">${m}</button>`).join('')}</div>${s.modo==='Comparar'?comparacion(G):s.modo==='Porcionamientos'?`<p>${esc(D.sel?.nombre??'Sin proveedor')} · ${D.trace.length} registros · entrada ${num(D.sel?.cant)} · merma ${num(D.sel?.merma)} ${esc(D.foco?.unid??'')} · costo ${sol(D.sel?.costo)}</p><input type="search" data-k="dq" value="${esc(s.dq)}" placeholder="Buscar documento, área o compra…" aria-label="Buscar porcionamiento">${tabla(G,'rastro',L.rastro)}<small>${D.rastro.length} visibles de ${D.trace.length}. El resumen conserva todos los registros del proveedor. Costo del día puede diferir del precio de la compra porque el Almacén valora al promedio.</small>`:tabla(G,'prov',L.prov)}${ficha(G)}</div></div></section>`;
    if(k){const el=raiz.querySelector(`[data-k="${k}"]`);el?.focus({preventScroll:true});if(pos!=null&&el?.type==='search')el.setSelectionRange(pos,pos);}
  }
  function exportar(G){const{P,s,D}=G,L=listas(G),prov=G.D.foco,trace=D.rows.map(r=>{const p=P.productos[r.prod];return[r.doc,r.fecha,p.cod,p.nombre,p.unid,r.area,r.prov==null?'':P.proveedores[r.prov],r.unico?'Sí':'No',r.cant,r.merma,r.costo,r.pct,r.compra,r.pcompra,r.dias,r.otro,r.f_otro,r.difiere?'Sí':'No',r.prov==null?'Sin proveedor':s.unico&&!r.unico?'Atribución ambigua':!(r.costo>0)?'Sin costo positivo':'Incluido'];});
    const hoja=(nombre,id,rs)=>{const cs=[...columnas(G,id),...(id==='prov'?[col('cant','Cantidad de entrada'),col('merma','Merma física'),col('costo','Costo del día'),col('queda','Cantidad útil')]:[])];return{nombre,cabeza:cs.map(c=>c.n),filas:ordenar(rs,s.orden[id]).map(r=>cs.map(c=>r[c.k]??''))};};
    const c=D.comparacion;
    return[hoja('Productos visibles','rank',L.rank),hoja('Proveedores del producto','prov',L.prov),hoja('Rastro visible','rastro',L.rastro),
      {nombre:'Porcionamientos ventana',cabeza:['Documento','Fecha','Código','Producto','Unidad','Área','Proveedor atribuido','Único','Cantidad','Merma','Costo día','Merma fracción','Compra atribuida','Precio compra','Días','Otro proveedor','Fecha otro','Costo difiere','Inclusión'],filas:trace},
      {nombre:'Pagado de más',cabeza:['Código','Producto','Unidad','Proveedor','Costo útil','Mínimo comparable','Cantidad útil','Pagado de más','Registros'],filas:D.ranking.flatMap(r=>r.pm.montos.map(m=>[r.cod,r.nombre,r.unid,P.proveedores[m.id],r.t.find(t=>t.id===m.id).util,r.pm.minimo,m.queda,m.valor,r.t.find(t=>t.id===m.id).n]))},
      {nombre:'Comparación',cabeza:['Producto','Unidad','A','B','B menos A','Efecto precio','Efecto rendimiento'],filas:c?[[prov.nombre,prov.unid,P.proveedores[c.a],P.proveedores[c.b],c.delta,c.precio,c.rendimiento]]:[]},
      {nombre:'Contexto',cabeza:['Concepto','Valor'],filas:[['Ventana',s.ventana],['Desde incluido',P.ventanas[s.ventana]?.ini??''],['Hasta excluido',P.ventanas[s.ventana]?.fin??''],['Sólo único',s.unico?'Sí':'No'],['Producto elegido',prov?`${prov.cod} · ${prov.nombre} · ${prov.unid}`:''],['Proveedor elegido',D.sel?.nombre??''],['Orden de tablas',JSON.stringify(s.orden)],['Búsqueda productos',s.q],['Incluir sin comparación',s.todos?'Sí':'No'],['Búsqueda rastro',s.dq],['Proveedor atribuido',`Última compra hasta ${P.dias_proveedor} días antes; único si no hubo otro en ${P.dias_unico} días`],['Costo útil','Costo del día ÷ (cantidad − merma); por producto y unidad'],['Competencia',`Al menos ${P.min_porc} registros por proveedor y cantidad útil positiva`],['Pagado de más','Σ (costo útil − mínimo comparable) × cantidad útil; referencia observada, no ahorro garantizado'],['Factores','Reparto simétrico de precio y rendimiento; B menos A'],['Decimales','Valores numéricos con seis decimales; totales sin redondeo previo'],...Object.entries(P.contexto).map(([k,v])=>[k,Array.isArray(v)?v.join(', '):v])]}].map(h=>({...h,decimales:6}));
  }
  function montar(component){const{data:P,parentElement}=component,prev=window.__provUtil;prev?.abort.abort();const s=prev?.s??estado(P.inicial);
    if(prev&&prev.P.sello!==P.sello){s.prod=null;s.prov=null;s.contra=null;s.dq='';}
    if(!prev||prev.P.comun!==P.comun){const id=P.productos.findIndex(r=>r.cod===P.comun);if(id>=0&&id!==s.prod){s.prod=id;s.prov=null;s.contra=null;s.dq='';}}
    if(!P.ventanas[s.ventana])s.ventana=Object.keys(P.ventanas)[0]??'12 meses';
    let raiz=parentElement.querySelector('.pvu');if(!raiz){raiz=document.createElement('div');raiz.className='pvu';parentElement.appendChild(raiz);}
    const G={P,s,raiz,component,abort:new AbortController(),tablas:{},comunEnviado:P.comun};window.__provUtil=G;const{signal}=G.abort;
    raiz.addEventListener('click',e=>{const el=e.target.closest('[data-a]');if(!el)return;const a=el.dataset.a,v=el.dataset.v;
      if(a==='excel'){bajar('Costo_por_unidad_util.xlsx',libro(exportar(G)));return;}
      if(a==='producto'){s.prod=Number(v);s.prov=null;s.contra=null;s.dq='';}
      else if(a==='proveedor'){s.prov=Number(v);s.contra=null;s.dq='';}
      else if(a==='ventana'){s.ventana=v;s.prov=null;s.contra=null;s.dq='';}
      else if(a==='modo')s.modo=v;
      else if(a==='orden'){const t=el.dataset.t,ant=s.orden[t];s.orden[t]=[v,ant?.[0]===v?-ant[1]:1];}
      dibujar(G);
      if(a==='producto'){const cod=P.productos[s.prod]?.cod;if(cod&&cod!==G.comunEnviado){G.comunEnviado=cod;component.setTriggerValue?.('producto',{sello:P.sello,cod});}}
    },{signal});
    raiz.addEventListener('change',e=>{const k=e.target.dataset.k;if(!k)return;if(k==='unico'||k==='todos')s[k]=e.target.checked;else if(k==='contra')s.contra=Number(e.target.value);else return;dibujar(G);},{signal});
    raiz.addEventListener('input',e=>{const k=e.target.dataset.k;if(k==='q'||k==='dq'){s[k]=e.target.value;dibujar(G);}},{signal});
    raiz.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('tr[data-a]')){e.preventDefault();e.target.click();}},{signal});
    raiz.addEventListener('scroll',e=>{const el=e.target,id=el.dataset?.tabla,t=G.tablas[id];if(!t||el.scrollTop+el.clientHeight<el.scrollHeight-220||t.n>=t.rows.length)return;el.querySelector('tbody').insertAdjacentHTML('beforeend',renglones(G,t,t.n,t.n+150));t.n+=150;},{signal,capture:true});
    dibujar(G);return()=>G.abort.abort();
  }
  return{montar,calcular,estado,agrupar,partes,comparar,exportar};
})();
window.__provUtilDatos=PVU;
export default function(component){return PVU.montar(component);}
