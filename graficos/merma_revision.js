/* Porcionamientos para revisar: marcas superpuestas e impacto sin duplicar (#732). */
const REV=(()=>{
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const plano=v=>String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const cmp=(a,b)=>String(a).localeCompare(String(b),'es');
  const fmt=new Intl.NumberFormat('es-PE',{maximumFractionDigits:2});
  const num=v=>v==null||!Number.isFinite(v)?'Sin dato':fmt.format(v);
  const sol=v=>v==null||!Number.isFinite(v)?'Sin base':`S/ ${num(v)}`;
  const pct=v=>v==null||!Number.isFinite(v)?'Sin base':`${num(v*100)} %`;
  const sum=(rs,k)=>rs.reduce((a,r)=>a+(r[k]??0),0);
  const fecha=v=>v?`${v.slice(8,10)}/${v.slice(5,7)}/${v.slice(0,4)}`:'—';
  const IMPACTOS=['alta','baja','cero','sinpeso','peso'];
  function estado(v={}){return{marcas:null,todos:false,area:null,usuario:null,prod:null,q:'',sentido:'Todos',doc:null,orden:null,...v};}
  function impacto(r,marcas,modo){
    const precio=(modo==='hoy'?r.precioHoy:r.precioDia)??0,valor=(modo==='hoy'?r.valorHoy:r.valorDia)??0;
    const dif=r.pct!=null&&r.normal.med!=null?(r.pct-r.normal.med)*r.cant*precio:0;
    const m={alta:dif,baja:dif,cero:r.normal.med!=null?r.normal.med*r.cant*precio:0,sinpeso:valor,peso:-(r.dpeso??0)*precio};
    let mejor=0;for(const k of IMPACTOS)if(marcas.includes(k)&&r.marcas.includes(k)&&Number.isFinite(m[k])&&Math.abs(m[k])>Math.abs(mejor))mejor=m[k];
    return mejor;
  }
  function calcular(P,s){
    const modo=P.modo==='hoy'&&P.precios_disponibles?'hoy':'dia',elegidas=s.marcas??P.inicial_marcas;
    const scoped=P.filas.filter(r=>(s.area==null||r.area===s.area)&&(s.usuario==null||r.usuario===s.usuario)&&(s.prod==null||r.prod===s.prod));
    const cuenta=Object.fromEntries(Object.keys(P.marcas).map(k=>[k,scoped.filter(r=>r.marcas.includes(k)).length]));
    const seleccion=scoped.filter(r=>s.todos||r.marcas.some(k=>elegidas.includes(k))).map(r=>({...r,impacto:impacto(r,elegidas,modo),valor:(modo==='hoy'?r.valorHoy:r.valorDia)??0}));
    seleccion.sort((a,b)=>Math.abs(b.impacto)-Math.abs(a.impacto));
    const q=plano(s.q),porDoc=new Map();for(const c of P.cortes){if(!porDoc.has(c.doc))porDoc.set(c.doc,[]);porDoc.get(c.doc).push(c);}
    const visibles=seleccion.filter(r=>(s.sentido==='Todos'||s.sentido==='Positivo'&&r.impacto>0||s.sentido==='Negativo'&&r.impacto<0||s.sentido==='Sin importe'&&r.impacto===0)
      &&(!q||plano([r.doc,P.productos[r.prod].nombre,P.productos[r.prod].cod,r.area,r.usuario,r.proveedor,...(porDoc.get(r.doc)??[]).map(c=>c.nombre+' '+c.cod)].join(' ')).includes(q)));
    const elegido=visibles.find(r=>r.doc===s.doc)||visibles[0]||null,cs=elegido?porDoc.get(elegido.doc)??[]:[];
    return{modo,elegidas,scoped,cuenta,seleccion,visibles,elegido,cs,positivos:sum(seleccion.filter(r=>r.impacto>0),'impacto'),negativos:sum(seleccion.filter(r=>r.impacto<0),'impacto'),sinImporte:seleccion.filter(r=>r.impacto===0).length,
      solicitado:P.solicitado??null,fuera:s.solicitud&&P.solicitado&&!visibles.some(r=>r.doc===P.solicitado)?P.filas.find(r=>r.doc===P.solicitado)??'fuera':null};
  }
  const col=(k,n,t='texto')=>({k,n,t});
  function columnas(){return[col('doc','Porcionamiento'),col('fecha','Fecha','fecha'),col('producto','Producto'),col('unid','UM'),col('pct','Merma','pct'),col('normalTxt','Lo normal'),col('impacto','Impacto','impacto'),col('motivos','Marcas elegidas'),col('usuario','Usuario'),col('area','Área')];}
  function lista(G){const{D,P}=G;return D.visibles.map(r=>({...r,producto:P.productos[r.prod].nombre,unid:P.productos[r.prod].unid,normalTxt:r.normal.q1==null?'Sin base':`${pct(r.normal.q1)}–${pct(r.normal.q3)}`,motivos:r.marcas.filter(k=>D.elegidas.includes(k)).map(k=>P.marcas[k].nombre).join(' · ')||'Sin marcas elegidas'}));}
  function textoCelda(v,c){return c.t==='sol'?sol(v):c.t==='num'?num(v):c.t==='pct'?pct(v):c.t==='fecha'?fecha(v):c.t==='impacto'?v?sol(v):'Sin importe':String(v??'—');}
  function ordenar(rs,o){if(!o)return rs;const[k,d]=o;return rs.slice().sort((a,b)=>(a[k]==null)-(b[k]==null)||(typeof a[k]==='number'&&typeof b[k]==='number'?(a[k]-b[k])*d:cmp(a[k]??'',b[k]??'')*d));}
  function renglones(G,ini,fin){return G.tabla.rows.slice(ini,fin).map(r=>`<tr tabindex="0" data-a="doc" data-v="${esc(r.doc)}" aria-selected="${r.doc===G.D.elegido?.doc}" class="${r.doc===G.D.elegido?.doc?'on':''}">${G.tabla.cols.map(c=>`<td title="${esc(c.n+': '+(r[c.k]??'Sin base'))}" class="${['sol','num','pct','impacto'].includes(c.t)?'mrv-num':''}">${esc(textoCelda(r[c.k],c))}</td>`).join('')}</tr>`).join('');}
  function tabla(G){G.tabla={rows:ordenar(lista(G),G.s.orden),cols:columnas(),n:150};return`<div class="mrv-scroll mrv-lista" data-tabla="casos"><table><thead><tr>${G.tabla.cols.map(c=>`<th><button data-a="orden" data-v="${c.k}">${esc(c.n)}</button></th>`).join('')}</tr></thead><tbody>${renglones(G,0,150)}</tbody></table>${G.tabla.rows.length?'':'<p class="mrv-vacio">No hay casos con estas marcas y filtros.</p>'}</div>`;}
  function motivo(G,r,k){const n=r.normal,u=G.P.productos[r.prod].unid;
    if(k==='alta'||k==='baja')return`Perdió ${pct(r.pct)}. La mitad central del historial de este producto va de ${pct(n.q1)} a ${pct(n.q3)}, con mediana ${pct(n.med)} (${num(n.n)} registros).`;
    if(k==='cero')return`No registró merma; este producto suele perder ${pct(n.med)}, unos ${num(n.med*r.cant)} ${u} sobre esta entrada.`;
    if(k==='sinpeso')return'Hay un corte con cantidad positiva y peso cero o ausente. Puede inflar la merma y dejar cortes sin costo; se conserva el registro original.';
    if(k==='peso')return`La merma es la entrada menos los pesos asignados. Con el peso habitual sería ${pct(r.pctCorr)}, frente al ${pct(r.pct)} registrado. Diferencia de peso: ${num(r.dpeso)} ${u}. Es una referencia para revisar el registro.`;
    if(k==='costo')return`Costo del día por entrada: ${sol(r.precioDia)} / ${u}; última compra atribuida: ${sol(r.pcompra)} / ${u}. El promedio del Almacén puede diferir de lo pagado.`;
    if(k==='fecha')return`Su número comienza por ${r.doc.slice(0,4)} y la fecha de registro es ${fecha(r.fecha)}. El reporte usa el registro y el kardex puede llevarlo al mes de proceso.`;
    return'';
  }
  function filasInternas(t,ini,fin){return t.rows.slice(ini,fin).map(r=>`<tr class="${r.clase??''}">${r.celdas.map(v=>`<td title="${esc(v)}">${esc(v)}</td>`).join('')}</tr>`).join('');}
  function tablaDetalle(G,id,cabeza,rows){const t={rows,n:150};G.internas[id]=t;return`<div class="mrv-scroll mrv-cortes" data-detalle-tabla="${id}"><table><thead><tr>${cabeza.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${filasInternas(t,0,150)}</tbody></table></div>`;}
  function abierto(G,clave){return G.s.detalles?.[JSON.stringify([G.D.elegido?.doc,clave])]===false?'':'open';}
  function cortesFicha(G){const{D,P}=G,u=P.productos[D.elegido.prod].unid;
    const rows=D.cs.map(c=>({clase:c.raro||c.cant>0&&(c.peso==null||c.peso===0)?'mrv-alerta':'',celdas:[c.corto||c.nombre,num(c.cant),c.unid,num(c.peso),num(c.kgu),num(c.hab),sol(c.pprom),sol(c.valor)]}));
    return tablaDetalle(G,'cortes',['Corte','Cantidad','UM final',`Peso (${u})`,'Por unidad','Habitual','Precio día','Valor día'],rows)+`<small>Peso y peso por unidad en ${esc(u)} de origen; cantidad en la unidad final. Habitual: mediana de hasta diez registros anteriores del mismo corte, con al menos cinco.</small>`;
  }
  function carta(G){const{P,D}=G,candidatos=D.cs.filter(c=>c.carta!=null);if(!candidatos.length)return'';
    return`<details class="mrv-carta" data-detalle="carta" ${abierto(G,'carta')}><summary>Rastro en el Almacén y la carta</summary>${candidatos.map(c=>{const a=P.carta[c.carta];return`<div><h4>${esc(c.nombre)}</h4><p>Entró a ${sol(c.pprom)} por ${esc(c.unid)} y hoy figura a ${sol(c.precioHoy)}. Con el peso habitual, su referencia sería ${sol(c.precioCorregido)}. El escenario conserva las cantidades y compara costos.</p>${P.recetas_disponibles===false?'<p>No se pudo leer la receta de venta; el efecto en platos no está disponible.</p>':a.platos.length?tablaDetalle(G,'carta'+c.carta,['Plato directo','Costo actual','% costo','Costo con referencia','% con referencia'],a.platos.map(r=>({celdas:[r.nombre,sol(r.costo),pct(r.pct),sol(r.costoCorr),pct(r.pctCorr)]})))+`<small>${a.platos.length} platos activos con el corte directo, en orden de costo actual.</small>`:'<p>Ningún plato activo lo lleva directo.</p>'}</div>`;}).join('')}</details>`;
  }

  function ficha(G){const{P,D}=G,r=D.elegido;if(!r)return'<div class="mrv-vacio">Selecciona un caso para ver sus motivos y cortes.</div>';
    const p=P.productos[r.prod],otro=D.modo==='hoy'?r.valorDia:r.valorHoy;
    return`<div class="mrv-ficha"><h4>PO-${esc(r.doc)} · ${esc(p.nombre)}</h4><p class="mrv-nota">${fecha(r.fecha)} · ${esc(r.area||'Sin área')} · ${esc(r.usuario||'Sin usuario')}${r.proveedor?` · última compra atribuida a ${esc(r.proveedor)}, ${num(r.dias)} días antes`:''}</p><div class="mrv-tiles"><div><span>Entrada</span><b>${num(r.cant)} ${esc(p.unid)}</b></div><div><span>Merma</span><b>${num(r.merma)} ${esc(p.unid)}</b><small>${pct(r.pct)}</small></div><div><span>Valor de merma</span><b>${sol(r.valor)}</b><small>${D.modo==='hoy'?'Día':'Hoy'}: ${otro==null?'Sin precio o dato':sol(otro)}</small></div></div>${D.modo==='hoy'&&!r.precioDisponible?'<p class="mrv-nota">Código sin precio actual conocido: la valorización de hoy conserva el cero de la fuente.</p>':''}<p><b>Impacto con las marcas elegidas: ${r.impacto?sol(r.impacto):'Sin importe estimado'}</b>. Cada caso toma la marca de mayor valor absoluto; no suma alertas superpuestas.</p>${r.marcas.map(k=>`<details class="mrv-motivo" data-nivel="${esc(P.marcas[k].nivel)}" data-detalle="${k}" ${abierto(G,k)}><summary>${esc(P.marcas[k].nombre)}</summary><p>${esc(motivo(G,r,k))}</p></details>`).join('')||'<p>Sin observaciones de las reglas actuales.</p>'}${cortesFicha(G)}${carta(G)}</div>`;
  }
  function select(k,nombre,values,selected,label=v=>v){return`<label>${nombre}<select data-k="${k}" aria-label="${nombre}"><option value="__all__">Todos</option>${values.map(v=>`<option value="${esc(v)}" ${selected===v?'selected':''}>${esc(label(v)||'Sin dato')}</option>`).join('')}</select></label>`;}
  function dibujar(G){const{P,s,raiz}=G,anterior=G.D?.elegido?.doc,scroll=raiz.querySelector('.mrv-detalle')?.scrollTop??0; s.detalles??={};if(anterior)for(const el of raiz.querySelectorAll('details[data-detalle]'))s.detalles[JSON.stringify([anterior,el.dataset.detalle])]=el.open;G.internas={};const activo=raiz.getRootNode().activeElement||document.activeElement,k=raiz.contains(activo)?activo.dataset.k:null,pos=k?activo.selectionStart:null;G.D=calcular(P,s);const D=G.D;if(D.elegido)s.doc=D.elegido.doc;
    const areas=[...new Set(P.filas.map(r=>r.area))].sort(cmp),usuarios=[...new Set(P.filas.map(r=>r.usuario))].sort(cmp),prods=[...new Set(P.filas.map(r=>r.prod))].sort((a,b)=>cmp(P.productos[a].nombre,P.productos[b].nombre));
    raiz.innerHTML=`<section class="mrv-main"><header><div><h3>Porcionamientos para revisar</h3><p>${P.filas.length} cabeceras con cantidad positiva · normal desde ${fecha(P.normal_desde)} · ${D.modo==='hoy'?'Precio de hoy':'Costo del día'}${P.modo==='hoy'&&!P.precios_disponibles?' · precio actual no disponible':''}</p></div><button data-a="excel">Excel de esta vista ↓</button></header><div class="mrv-marcas">${Object.entries(P.marcas).map(([key,m])=>`<button data-a="marca" data-v="${key}" data-nivel="${esc(m.nivel)}" aria-pressed="${D.elegidas.includes(key)}" class="${D.elegidas.includes(key)?'on':''}">${esc(m.nombre)} · ${D.cuenta[key]}</button>`).join('')}</div><div class="mrv-filtros">${select('area','Área',areas,s.area)}${select('usuario','Usuario',usuarios,s.usuario)}${select('prod','Producto',prods,s.prod,v=>P.productos[v].nombre+' · '+P.productos[v].unid)}<label><input type="checkbox" data-k="todos" ${s.todos?'checked':''}> Todos los registros</label><button data-a="limpiar">Quitar filtros</button></div><div class="mrv-resumen"><span><b>${D.seleccion.length}</b> casos con marcas/filtros</span><span>Positivo <b>${sol(D.positivos)}</b></span><span>Negativo <b>${sol(D.negativos)}</b></span><span>Sin importe <b>${D.sinImporte}</b></span></div>${D.fuera?`<div class="mrv-aviso">${D.fuera==='fuera'?'El porcionamiento solicitado no está en el rango actual o no tiene cantidad positiva.':'El porcionamiento solicitado queda fuera de los filtros.'}${D.fuera!=='fuera'?'<button data-a="solicitud">Mostrar el solicitado</button>':''}</div>`:''}<div class="mrv-cuerpo"><div class="mrv-panel"><div class="mrv-buscar"><input type="search" data-k="q" value="${esc(s.q)}" placeholder="Buscar documento, producto, corte o usuario…" aria-label="Buscar caso"><label>Impacto<select data-k="sentido">${['Todos','Positivo','Negativo','Sin importe'].map(v=>`<option ${s.sentido===v?'selected':''}>${v}</option>`).join('')}</select></label></div>${tabla(G)}<small>${D.visibles.length} visibles de ${D.seleccion.length}. La búsqueda y el signo de impacto filtran la lista; los resúmenes conservan el conjunto de marcas, área, usuario y producto.</small></div><div class="mrv-panel mrv-detalle">${ficha(G)}</div></div></section>`;
    if(anterior===D.elegido?.doc){const panel=raiz.querySelector('.mrv-detalle');if(panel)panel.scrollTop=scroll;}
    if(k){const el=raiz.querySelector(`[data-k="${k}"]`);el?.focus({preventScroll:true});if(pos!=null&&el?.type==='search')el.setSelectionRange(pos,pos);}
  }
  function exportar(G){const{P,D,s}=G,cs=columnas(),row=(r)=>{const p=P.productos[r.prod];return[r.doc,r.fecha,p.cod,p.nombre,p.unid,r.area,r.usuario,r.cant,r.merma,r.pct,r.costoDia,r.valorDia,r.valorHoy,r.normal.n,r.normal.q1,r.normal.med,r.normal.q3,r.dpeso,r.pctCorr,r.proveedor??'',r.pcompra,r.dias,r.marcas.map(k=>P.marcas[k].nombre).join(' · ')];};
    const cabezas=['Documento','Fecha','Código','Producto','Unidad','Área','Usuario','Cantidad','Merma','Merma fracción','Costo día','Merma día','Merma hoy','Referencias','Normal Q1','Mediana','Normal Q3','Diferencia peso','Merma con peso habitual','Proveedor atribuido','Precio compra','Días compra','Todas las marcas'];
    const pp=new Map(P.filas.map(r=>[r.doc,P.productos[r.prod]]));
    return[{nombre:'Casos visibles',cabeza:cs.map(c=>c.n),filas:ordenar(lista(G),s.orden).map(r=>cs.map(c=>r[c.k]??''))},
      {nombre:'Casos del conjunto',cabeza:[...cabezas,'Impacto elegido'],filas:D.seleccion.map(r=>[...row(r),r.impacto])},
      {nombre:'Cabeceras del rango',cabeza:cabezas,filas:P.filas.map(row)},
      {nombre:'Marcas por cabecera',cabeza:['Documento',...Object.values(P.marcas).map(r=>r.nombre)],filas:P.filas.map(r=>[r.doc,...Object.keys(P.marcas).map(k=>r.marcas.includes(k)?1:0)])},
      {nombre:'Cortes del rango',cabeza:['Documento','Código origen','Producto origen','Unidad origen','Código corte','Corte','Cantidad','Unidad final','Peso asignado','Peso por unidad','Peso habitual','Peso raro válido','Precio día','Valor día','Precio con peso habitual','Precio hoy'],filas:P.cortes.filter(r=>pp.has(r.doc)).map(r=>[r.doc,pp.get(r.doc).cod,pp.get(r.doc).nombre,pp.get(r.doc).unid,r.cod,r.nombre,r.cant,r.unid,r.peso,r.kgu,r.hab,r.raro?1:0,r.pprom,r.valor,r.precioCorregido??'',r.precioHoy??''])},
      {nombre:'Rastro en carta',cabeza:['Código corte','Factor de referencia','Plato activo','Costo actual','Fracción costo actual','Costo con referencia','Fracción con referencia'],filas:P.carta.flatMap(c=>c.platos.map(p=>[c.cod,c.factor,p.nombre,p.costo,p.pct,p.costoCorr,p.pctCorr]))},
      {nombre:'Comparación de bases',cabeza:['Documento','Merma física','Unidad','Precio día','Precio hoy','Merma día','Merma hoy','Impacto día','Impacto hoy','Precio actual conocido'],filas:P.filas.map(r=>[r.doc,r.merma,P.productos[r.prod].unid,r.precioDia,r.precioHoy,r.valorDia,r.valorHoy,impacto(r,D.elegidas,'dia'),P.precios_disponibles?impacto(r,D.elegidas,'hoy'):'',r.precioDisponible?'Sí':'No'])},
      {nombre:'Contexto',cabeza:['Concepto','Valor'],filas:[['Desde incluido',P.rango?.[0]??''],['Hasta excluido',P.rango?.[1]??''],['Normal desde',P.normal_desde??''],['Valorización solicitada',P.modo],['Valorización efectiva',D.modo],['Marcas',D.elegidas.map(k=>P.marcas[k].nombre).join(', ')],['Todos los registros',s.todos?'Sí':'No'],['Área',s.area??'Todas'],['Usuario',s.usuario??'Todos'],['Producto',s.prod==null?'Todos':P.productos[s.prod].nombre+' · '+P.productos[s.prod].unid],['Búsqueda',s.q],['Signo de impacto',s.sentido],['Regla de impacto','Por cabecera, mayor valor absoluto entre las marcas elegidas; nunca sumar marcas superpuestas'],['Peso habitual','Mediana de hasta diez observaciones anteriores; mínimo cinco. El escenario no modifica el registro'],['Proveedor','Última compra atribuida hasta 45 días antes; no es lote identificado'],['Recetas de venta',P.recetas_disponibles===null?'No se necesitaron':P.recetas_disponibles?'Disponibles':'No disponibles'],['Decimales','Seis en Excel; sin redondear antes del cálculo'],...Object.entries(P.contexto).map(([k,v])=>[k,Array.isArray(v)?v.join(', '):v])]}].map(h=>({...h,decimales:6}));
  }
  function montar(component){const{data:P,parentElement}=component,prev=window.__mermaRev;prev?.abort.abort();const s=prev?.s??estado(P.inicial);
    if(prev&&prev.P.sello_origen!==P.sello_origen){const old=prev.P.productos[s.prod];if(old){const id=P.productos.findIndex(p=>p.cod===old.cod&&p.unid===old.unid);s.prod=id>=0?id:null;}if(!P.filas.some(r=>r.doc===s.doc))s.doc=null;if(!P.filas.some(r=>r.area===s.area))s.area=null;if(!P.filas.some(r=>r.usuario===s.usuario))s.usuario=null;}
    if(!prev||prev.P.salto!==P.salto){s.solicitud=!!P.solicitado;if(P.solicitado)s.doc=P.solicitado;}
    let raiz=parentElement.querySelector('.mrv');if(!raiz){raiz=document.createElement('div');raiz.className='mrv';parentElement.appendChild(raiz);}
    const G={P,s,raiz,component,abort:new AbortController(),D:prev?.D};window.__mermaRev=G;const{signal}=G.abort;
    raiz.addEventListener('click',e=>{const el=e.target.closest('[data-a]');if(!el)return;const a=el.dataset.a,v=el.dataset.v;
      if(a==='excel'){bajar('Porcionamientos_para_revisar.xlsx',libro(exportar(G)));return;}
      if(a==='doc'){
        s.detalles??={};const anterior=G.D?.elegido?.doc;
        if(anterior)for(const d of raiz.querySelectorAll('details[data-detalle]'))s.detalles[JSON.stringify([anterior,d.dataset.detalle])]=d.open;
        s.doc=v;s.solicitud=false;G.D=calcular(P,s);G.internas={};const panel=raiz.querySelector('.mrv-detalle');panel.innerHTML=ficha(G);panel.scrollTop=0;
        for(const row of raiz.querySelectorAll('[data-tabla=casos] tr[data-a=doc]')){const on=row.dataset.v===G.D.elegido?.doc;if(row.classList.contains('on')!==on)row.classList.toggle('on',on);if(row.getAttribute('aria-selected')!==String(on))row.setAttribute('aria-selected',String(on));}
        el.focus({preventScroll:true});return;
      }
      if(a==='marca'){const m=(s.marcas??P.inicial_marcas).slice();s.marcas=m.includes(v)?m.filter(k=>k!==v):[...m,v];}
      else if(a==='limpiar')Object.assign(s,estado());
      else if(a==='solicitud'){const r=P.filas.find(r=>r.doc===P.solicitado);if(r){s.area=null;s.usuario=null;s.prod=null;s.q=r.doc;s.sentido='Todos';s.doc=r.doc;s.marcas=[...new Set([...(s.marcas??P.inicial_marcas),...r.marcas])];if(!r.marcas.length)s.todos=true;}}
      else if(a==='orden')s.orden=[v,s.orden?.[0]===v?-s.orden[1]:1];
      s.solicitud=false;dibujar(G);
    },{signal});
    raiz.addEventListener('input',e=>{if(e.target.dataset.k==='q'){s.q=e.target.value;s.solicitud=false;dibujar(G);}},{signal});
    raiz.addEventListener('change',e=>{const k=e.target.dataset.k;if(k==='todos')s.todos=e.target.checked;else if(k==='area'||k==='usuario')s[k]=e.target.value==='__all__'?null:e.target.value;else if(k==='prod')s.prod=e.target.value==='__all__'?null:Number(e.target.value);else if(k==='sentido')s.sentido=e.target.value;else return;s.solicitud=false;dibujar(G);},{signal});
    raiz.addEventListener('toggle',e=>{const el=e.target;if(el.matches?.('details[data-detalle]')&&el.isConnected&&G.D.elegido){s.detalles??={};s.detalles[JSON.stringify([G.D.elegido.doc,el.dataset.detalle])]=el.open;}},{signal,capture:true});
    raiz.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('tr[data-a=doc]')){e.preventDefault();e.target.click();}},{signal});
    raiz.addEventListener('scroll',e=>{const el=e.target,t=G.tabla,interno=G.internas[el.dataset?.detalleTabla];if(interno){if(el.scrollTop+el.clientHeight>=el.scrollHeight-220&&interno.n<interno.rows.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',filasInternas(interno,interno.n,interno.n+150));interno.n+=150;}return;}if(el.dataset?.tabla!=='casos'||el.scrollTop+el.clientHeight<el.scrollHeight-220||t.n>=t.rows.length)return;el.querySelector('tbody').insertAdjacentHTML('beforeend',renglones(G,t.n,t.n+150));t.n+=150;},{signal,capture:true});
    dibujar(G);return()=>G.abort.abort();
  }

  return{estado,impacto,calcular,dibujar,exportar,montar};
})();
window.__mermaRevDatos=REV;

export default function(component){return REV.montar(component);}
