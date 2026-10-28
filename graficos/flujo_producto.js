// El recorrido describe relaciones; nunca atribuye una venta a un lote.
export default function(component){
  const host=component.parentElement, doc=host.ownerDocument, D=component.data;
  host.querySelector('.flujo-producto')?.remove();
  const root=doc.createElement('section');root.className='flujo-producto';host.appendChild(root);
  const N=new Map(D.nodos.map(n=>[n.id,n])), out=new Map(), incoming=new Map();
  D.enlaces.forEach(e=>{if(!out.has(e.origen))out.set(e.origen,[]);out.get(e.origen).push(e);if(!incoming.has(e.destino))incoming.set(e.destino,[]);incoming.get(e.destino).push(e);});
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean=s=>String(s).replace(/^\((P|Rs)\)\s*/i,'').replace(/\s*\((produccion|frios|calientes)\)\s*$/i,'');
  const fold=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const date=s=>s?s.split('-').reverse().join('/'):'Sin fecha';
  const action=t=>({'porcionamiento':'Porcionar','receta base':'Preparar','receta de venta':'Armar el plato'}[t]||t);
  const stateKey='flujo_producto_ui_v1';
  let saved={};try{saved=JSON.parse(window.sessionStorage.getItem(stateKey)||'{}');}catch{}
  let S={mode:saved.mode==='plato'?'plato':'producto',start:N.has(saved.start)?saved.start:null,origin:saved.origin,target:saved.target,step:0};
  let route=[],edges=[],limit=false;
  const opts=(xs,sel)=>xs.map(id=>`<option value="${esc(id)}" ${id===sel?'selected':''}>${esc(clean(N.get(id).nombre))} · ${esc(N.get(id).cod)}</option>`).join('');
  const sorted=xs=>[...new Set(xs)].sort((a,b)=>N.get(a).nombre.localeCompare(N.get(b).nombre,'es'));
  const candidates=()=>sorted(D.nodos.filter(n=>S.mode==='plato'?n.tipo==='plato':n.tipo!=='plato'&&out.has(n.id)).map(n=>n.id));
  function reachable(start,back=false){
    const seen=new Map([[start,0]]),q=[start];let clipped=false;
    for(let i=0;i<q.length;i++){
      const id=q[i],depth=seen.get(id),es=(back?incoming:out).get(id)||[];
      for(const e of es){const next=back?e.origen:e.destino;if(seen.has(next))continue;if(depth>=12){clipped=true;continue;}seen.set(next,depth+1);q.push(next);}
    }
    return {ids:[...seen.keys()],clipped};
  }
  function path(a,b){
    if(a===b)return {nodes:[a],edges:[]};
    const q=[a],prev=new Map([[a,null]]),depth=new Map([[a,0]]);
    for(let i=0;i<q.length;i++){
      const id=q[i];if(depth.get(id)>=12)continue;
      for(const e of out.get(id)||[]){if(prev.has(e.destino))continue;prev.set(e.destino,e);depth.set(e.destino,depth.get(id)+1);q.push(e.destino);
        if(e.destino===b){let cur=b,ns=[b],es=[];while(cur!==a){const edge=prev.get(cur);es.unshift(edge);cur=edge.origen;ns.unshift(cur);}return {nodes:ns,edges:es};}}
    }
    return null;
  }
  function persist(){try{window.sessionStorage.setItem(stateKey,JSON.stringify({mode:S.mode,start:S.start,origin:S.origin,target:S.target}));}catch{}}
  function controls(){
    const cs=candidates();
    if(!cs.includes(S.start))S.start=cs.find(x=>x==='p:0000287')||cs[0];
    root.innerHTML=`<div class="fp-intro"><div><span class="fp-eyebrow">DEL INSUMO AL PLATO</span><h2>Así recorre la cocina</h2><p>Elige un producto para seguir sus transformaciones y explicar de dónde viene y en qué se usa.</p></div><div class="fp-tools"><button type="button" data-present>Presentar</button><button type="button" data-save>Guardar recorrido</button></div></div>
      <div class="fp-controls"><div class="fp-mode" role="group" aria-label="Partir de"><button type="button" data-mode="producto" aria-pressed="${S.mode==='producto'}">Desde un insumo</button><button type="button" data-mode="plato" aria-pressed="${S.mode==='plato'}">Desde un plato</button></div><label class="fp-search">Buscar producto<input type="search" placeholder="Lomo, pulpo, salsa…" aria-label="Buscar producto"></label><label class="fp-pick">${S.mode==='plato'?'Plato':'Insumo o preparación'}<select data-start aria-label="Producto del recorrido">${opts(cs,S.start)}</select></label></div>
      <div class="fp-selectors"></div><div class="fp-stage"></div><div class="fp-branches"></div><div class="fp-note">Relaciones observadas del ${date(D.rango[0])} al ${date(D.rango[1])}; recetas activas de hoy. El mapa incluye todas las áreas y familias. Las flechas muestran relaciones entre productos; no identifican el lote de una venta.</div>${D.avisos.length?`<details class="fp-source-warnings"><summary>Fuentes incompletas</summary>${D.avisos.map(x=>`<p>${esc(x)}</p>`).join('')}</details>`:''}`;
    root.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{S.mode=b.dataset.mode;S.start=null;S.origin=null;S.target=null;S.step=0;controls();});
    root.querySelector('input').oninput=e=>{const filtered=cs.filter(id=>fold(N.get(id).nombre+' '+N.get(id).cod).includes(fold(e.target.value)));const select=root.querySelector('[data-start]');select.innerHTML=opts(filtered,S.start);if(filtered.length&&!filtered.includes(S.start)){S.start=filtered[0];S.origin=null;S.target=null;S.step=0;diagram();}if(!filtered.length)select.innerHTML='<option>Sin coincidencias</option>';};
    root.querySelector('[data-start]').onchange=e=>{if(!N.has(e.target.value))return;S.start=e.target.value;S.origin=null;S.target=null;S.step=0;diagram();};
    root.querySelector('[data-present]').onclick=async()=>{if(doc.fullscreenElement){await doc.exitFullscreen?.();return;}if(root.classList.contains('fp-present')){root.classList.remove('fp-present');root.querySelector('[data-present]').textContent='Presentar';return;}try{await root.requestFullscreen();}catch{root.classList.add('fp-present');}root.querySelector('[data-present]').textContent='Salir de presentación';};
    root.onfullscreenchange=()=>{root.querySelector('[data-present]').textContent=doc.fullscreenElement?'Salir de presentación':'Presentar';};
    root.querySelector('[data-save]').onclick=save;
    if(!S.start){root.querySelector('.fp-stage').textContent='No hay productos disponibles para esta perspectiva.';return;}
    diagram();
  }
  function diagram(){
    const up=reachable(S.start,true),down=reachable(S.start);limit=up.clipped||down.clipped;
    let origins=sorted(up.ids.filter(id=>N.get(id).compras.length));
    if(!origins.length)origins=sorted(up.ids.filter(id=>!incoming.has(id)));
    if(!origins.length)origins=[S.start];
    let targets=S.mode==='plato'?[S.start]:sorted(down.ids.filter(id=>N.get(id).tipo==='plato'));
    if(!targets.length)targets=sorted(down.ids.filter(id=>!out.has(id)));
    if(!targets.length)targets=[S.start];
    if(!origins.includes(S.origin)){
      const words=fold(N.get(S.start).nombre).split(/\W+/).filter(w=>w.length>3);
      const score=id=>{const p=path(id,S.start),name=fold(N.get(id).nombre);return words.filter(w=>name.includes(w)).length*10+(p?.edges.some(e=>e.tipo==='porcionamiento')?2:0);};
      S.origin=[...origins].sort((a,b)=>score(b)-score(a))[0];
    }
    if(!targets.includes(S.target))S.target=targets.find(id=>fold(N.get(id).nombre)==='lomo al trapo 1kg')||targets[0];
    const left=path(S.origin,S.start),right=path(S.start,S.target);
    route=left&&right?[...left.nodes,...right.nodes.slice(1)]:[S.start];edges=left&&right?[...left.edges,...right.edges]:[];
    // Correcciones de porcionamiento pueden cerrar un círculo. Mostrarlo
    // como dos pasos de la misma ruta induciría a enseñar un proceso falso.
    const repeated=route.length!==new Set(route).size;
    if(repeated){route=right?.nodes||[S.start];edges=right?.edges||[];}
    S.step=Math.min(S.step,route.length-1);
    root.querySelector('.fp-selectors').innerHTML=`<label>Origen del recorrido<select data-origin aria-label="Origen del recorrido">${opts(origins,S.origin)}</select></label><span class="fp-toward">→</span><label>Destino${S.mode==='plato'?'':' · '+targets.length+' relacionados'}<select data-target aria-label="Destino del recorrido">${opts(targets,S.target)}</select></label>`;
    root.querySelector('[data-origin]').onchange=e=>{S.origin=e.target.value;S.step=0;diagram();};
    root.querySelector('[data-target]').onchange=e=>{S.target=e.target.value;S.step=0;diagram();};
    root.querySelector('.fp-stage').innerHTML=`<div class="fp-route-head"><span>Recorrido hacia <strong>${esc(clean(N.get(S.target).nombre))}</strong></span><div class="fp-step-controls"><button type="button" data-prev aria-label="Paso anterior">←</button><span data-step-label></span><button type="button" data-next aria-label="Paso siguiente">→</button></div></div><div class="fp-route" role="list" aria-label="Flujo del producto">${route.map((id,i)=>{
      const n=N.get(id),edge=edges[i-1];
      const kind=i===0?(n.compras.length?'Compra registrada':'Origen sin compra observada'):n.tipo==='plato'?'Plato de venta':edge.tipo==='porcionamiento'?'Producto porcionado':'Preparación';
      return `${i?`<div class="fp-arrow"><span>${esc(action(edge.tipo))}</span><svg viewBox="0 0 60 24" aria-hidden="true"><path d="M1 12h54m-8-7 8 7-8 7"/></svg></div>`:''}<button type="button" class="fp-node" role="listitem" data-step="${i}"><span class="fp-number">${i+1}</span><span class="fp-kind">${esc(kind)}</span><strong>${esc(clean(n.nombre))}</strong><span class="fp-unit">${esc(n.unidad||'Plato')} · ${esc(n.cod)}</span></button>`;
    }).join('')}</div><div class="fp-explain" aria-live="polite"></div>${repeated?'<p class="fp-warning">Hay relaciones de ida y vuelta en los registros. Se muestra el tramo hacia el destino para evitar repetir un producto.</p>':''}${limit?'<p class="fp-warning">El mapa se limita a 12 transformaciones por sentido. Puede haber más relaciones.</p>':''}`;
    root.querySelectorAll('[data-step]').forEach(b=>b.onclick=()=>{S.step=Number(b.dataset.step);explain();});
    root.querySelector('[data-prev]').onclick=()=>{S.step=Math.max(0,S.step-1);explain();};
    root.querySelector('[data-next]').onclick=()=>{S.step=Math.min(route.length-1,S.step+1);explain();};
    const others=targets.filter(id=>id!==S.target);
    root.querySelector('.fp-branches').innerHTML=others.length?`<details><summary>También llega a ${others.length} ${others.length===1?'destino':'destinos'}</summary><div class="fp-chips">${others.map(id=>`<button type="button" data-dest="${esc(id)}">${esc(clean(N.get(id).nombre))} →</button>`).join('')}</div></details>`:'';
    root.querySelectorAll('[data-dest]').forEach(b=>b.onclick=()=>{S.target=b.dataset.dest;S.step=0;diagram();});
    persist();explain();
  }
  function explain(){
    const n=N.get(route[S.step]),e=edges[S.step-1],prev=S.step?N.get(route[S.step-1]):null;
    let text=S.step===0?(n.compras.length?`Se compra ${clean(n.nombre)}. Este es el punto de entrada de este recorrido.`:`El recorrido empieza en ${clean(n.nombre)}. No se encontró una compra de este producto en las fechas elegidas; su origen requiere revisión.`):e.tipo==='porcionamiento'?`Al porcionar ${clean(prev.nombre)}, se obtiene ${clean(n.nombre)}. Un mismo porcionamiento puede generar otros cortes.`:e.tipo==='receta base'?`Se utiliza ${clean(prev.nombre)} para preparar ${clean(n.nombre)}, según su receta base activa.`:`La receta de ${clean(n.nombre)} lleva ${clean(prev.nombre)}. Este es el vínculo con el plato que se ofrece al cliente; no confirma una venta individual.`;
    const inputs=new Set((incoming.get(n.id)||[]).map(x=>x.origen));
    if(S.step&&e.tipo!=='porcionamiento'&&inputs.size>1)text+=` Esta ${n.tipo==='plato'?'receta de venta':'preparación'} tiene además ${inputs.size-1} ingredientes relacionados.`;
    let evidence='';
    if(!S.step&&n.compras.length)evidence=`<h4>Compras observadas · hasta 20 documentos recientes</h4><ul>${n.compras.map(c=>`<li>${date(c[1])} · ${esc(c[0]||'Documento sin número')}${c[2]?' · '+esc(c[2]):''}</li>`).join('')}</ul>`;
    if(e)evidence=e.tipo==='porcionamiento'?`<h4>${e.cantidad} porcionamientos que vinculan estos productos</h4><ul>${e.registros.map(r=>`<li>${date(r.fecha)} · ${esc(r.doc||'Sin número')}${r.area?' · '+esc(r.area):''}</li>`).join('')}</ul>${e.cantidad>20?'<p>Se muestran los 20 más recientes.</p>':''}`:`<p>Fuente: ${e.tipo==='receta base'?'recetabase.parquet · receta base activa':'recetaventa.parquet · receta de venta activa'}. Composición actual.</p>`;
    if(n.ordenes.length)evidence+=`<h4>Producción procesada observada</h4><ul>${n.ordenes.map(r=>`<li>${date(r.fecha)} · ${esc(r.doc)}</li>`).join('')}</ul>`;
    root.querySelector('.fp-explain').innerHTML=`<div class="fp-explain-title">Paso ${S.step+1} · ${esc(S.step?action(e.tipo):n.compras.length?'Comprar':'Revisar origen')}</div><p>${esc(text)}</p><details><summary>Ver registros de respaldo</summary>${evidence||'<p>No hay documento de origen disponible para este paso.</p>'}</details>`;
    root.querySelectorAll('[data-step]').forEach(b=>{const on=Number(b.dataset.step)===S.step;b.classList.toggle('fp-active',on);b.setAttribute('aria-current',on?'step':'false');});
    root.querySelector('[data-step-label]').textContent=`${S.step+1} / ${route.length}`;
    root.querySelector('[data-prev]').disabled=S.step===0;root.querySelector('[data-next]').disabled=S.step===route.length-1;
  }
  function save(){
    const css=component.data.exportCss||'',name=clean(N.get(S.target).nombre);
    const steps=route.map((id,i)=>{const n=N.get(id),e=edges[i-1];const records=e?.tipo==='porcionamiento'?e.registros.map(r=>`${date(r.fecha)} · ${esc(r.doc)}${r.area?' · '+esc(r.area):''}`):!i?n.compras.map(c=>`${date(c[1])} · ${esc(c[0])}${c[2]?' · '+esc(c[2]):''}`):[];return `<article><small>${i+1} · ${esc(i?action(e.tipo):n.compras.length?'Comprar':'Origen sin compra observada')}</small><h2>${esc(clean(n.nombre))}</h2><p>${esc(n.cod)} · ${esc(n.unidad)}</p>${e?`<p>Fuente: ${esc(e.tipo)}${e.tipo==='porcionamiento'?' · '+e.cantidad+' documentos':''}</p>`:''}${records.length?'<details><summary>Registros de respaldo</summary><ul>'+records.map(r=>'<li>'+r+'</li>').join('')+'</ul></details>':''}</article>`;}).join('<div class="arrow">↓</div>');
    const html=`<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Flujo · ${esc(name)}</title><style>${css}body{font:16px system-ui;margin:40px auto;max-width:760px;padding:0 20px}article{border:1px solid var(--fp-border);padding:20px;border-radius:12px}.arrow{text-align:center;font-size:28px}small{font-weight:600}button{padding:10px}@media print{button{display:none}article{break-inside:avoid}}</style><h1>Flujo del producto</h1><p>${esc(name)}</p><p>Relaciones observadas: ${date(D.rango[0])}–${date(D.rango[1])}. Recetas activas al generar este recorrido.</p>${steps}<p>Mapa de relaciones entre productos. No atribuye una venta a un lote ni a una factura. Los porcionamientos pueden tener otros resultados y las recetas otros ingredientes.</p><button onclick="window.print()">Imprimir / guardar PDF</button></html>`;
    const url=URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'})),a=doc.createElement('a');a.href=url;a.download='flujo-'+fold(name).replace(/[^a-z0-9]+/g,'-')+'.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  controls();
}
