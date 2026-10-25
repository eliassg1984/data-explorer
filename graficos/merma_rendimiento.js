/* Rendimiento: series ponderadas y precio de cortes con sus factores (#730). */
const REND=(()=>{
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const plano=v=>String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const cmp=(a,b)=>String(a).localeCompare(String(b),'es');
  const fmt=new Intl.NumberFormat('es-PE',{maximumFractionDigits:2});
  const n=v=>v==null||!Number.isFinite(v)?'Sin base':fmt.format(v);
  const sol=v=>v==null||!Number.isFinite(v)?'Sin base':`S/ ${n(v)}`;
  const pct=v=>v==null||!Number.isFinite(v)?'Sin base':`${n(v*100)} %`;
  const pp=v=>v==null?'Sin comparación':`${v>0?'+':''}${n(v*100)} pp`;
  const fecha=v=>v?`${v.slice(8,10)}/${v.slice(5,7)}/${v.slice(0,4)}`:'—';
  const sum=(rs,k)=>rs.reduce((a,r)=>a+(r[k]??0),0);
  const group=(rs,key)=>{const m=new Map();for(const r of rs){const k=key(r);if(!m.has(k))m.set(k,[]);m.get(k).push(r);}return m;};
  const ratio=(a,b)=>b?a/b:null;
  const mes=f=>f.slice(0,7)+'-15T00:00:00';
  const FACTORES=['insumo','merma','gramaje','otros'];
  const observaciones=(r,P)=>[...r.marcas.map(k=>P.marcas[k]),...(r.merma==null?['Merma sin dato']:[])];
  function estado(v={}){return{ventana:'12 meses',prod:null,corte:null,precio:'Precio del corte',lista:'Cortes de este producto',q:'',solo:false,mes:null,doc:null,ficha:false,orden:{},...v};}
  function agregado(rs){const cant=sum(rs,'cant'),merma=sum(rs,'merma'),costo=sum(rs,'costo');return{n:rs.length,cant,merma,costo,pct:ratio(merma,cant),pkg:ratio(costo,cant)};}
  function mensual(xs){return [...group(xs,r=>mes(r.fecha))].sort((a,b)=>cmp(a[0],b[0])).map(([mes,rs])=>{const a=agregado(rs);return{mes,pct:a.pct,pkg:a.costo>0?a.pkg:null};});}
  function lado(filas,cab){const docs=[...new Set(filas.map(r=>r.doc))],rs=docs.map(d=>cab.get(d)),q=sum(filas,'cant'),a=agregado(rs);return{n:docs.length,P:q>0?sum(filas,'valor')/q:null,K:a.cant>0?a.pkg:null,m:a.cant>0?a.pct:null,g:q>0?sum(filas,'peso')/q:null};}
  function desglose(a,b){
    if(!a.n||!b.n||![a.P,a.K,a.g,b.P,b.K,b.g,1-a.m,1-b.m].every(v=>v!=null&&Number.isFinite(v)&&v>0))return null;
    const ra=a.P/(a.K/(1-a.m)*a.g),rb=b.P/(b.K/(1-b.m)*b.g),dl=Math.log(b.P/a.P),L=Math.abs(dl)<1e-12?a.P:(b.P-a.P)/dl;
    return{insumo:L*Math.log(b.K/a.K),merma:L*Math.log((1-a.m)/(1-b.m)),gramaje:L*Math.log(b.g/a.g),otros:L*Math.log(rb/ra)};
  }
  function cortes(xs,cs,finRec){const cab=new Map(xs.map(r=>[r.doc,r]));return [...group(cs.filter(r=>cab.has(r.doc)&&r.cant>0),r=>r.key)].map(([key,rs])=>{
    const a=lado(rs.filter(r=>cab.get(r.doc).fecha<finRec),cab),b=lado(rs.filter(r=>cab.get(r.doc).fecha>=finRec),cab),des=desglose(a,b),ult=rs.at(-1);
    return{key,clave:ult.clave,nombre:ult.nombre,corto:ult.nombreCorto,unid:ult.unid,valor:sum(rs,'valor'),a,b,var:a.n&&b.n&&a.P>0?b.P/a.P-1:null,desglose:des,causa:des?FACTORES.reduce((a,k)=>Math.abs(des[k])>Math.abs(des[a])?k:a):null};
  }).sort((a,b)=>b.valor-a.valor);}
  function mensualCorte(xs,cs,med){const cab=new Map(xs.map(r=>[r.doc,r]));return [...group(cs.filter(r=>cab.has(r.doc)),r=>mes(cab.get(r.doc).fecha))].sort((a,b)=>cmp(a[0],b[0])).map(([mes,rs])=>{
    const q=sum(rs,'cant'),precio=q>0?sum(rs,'valor')/q:null,ds=[...new Set(rs.map(r=>r.doc))].map(d=>cab.get(d)),a=agregado(ds),m=a.pct;
    return{mes,precio,merma:m,normal:precio!=null&&m!=null&&med!=null&&Number.isFinite(med)&&med<1?precio*(1-m)/(1-med):null};
  });}
  function cambios(rs,P){return [...group(rs,r=>r.prod)].map(([prod,x])=>{
    const rr=x.filter(r=>r.fecha>=P.reciente),aa=x.filter(r=>r.fecha<P.reciente),a=agregado(aa),b=agregado(rr);
    if(a.n<P.min_cambios||b.n<P.min_cambios||!(a.cant>0&&b.cant>0))return null;
    const dpp=b.pct-a.pct;return{prod,...P.productos[prod],pct_ant:a.pct,pct_rec:b.pct,dpp,dprecio:a.pkg>0?b.pkg/a.pkg-1:null,impacto:dpp*sum(rr,'valorCosto')};
  }).filter(Boolean).sort((a,b)=>Math.abs(b.impacto)-Math.abs(a.impacto));}
  function calcular(P,s){
    const v=P.ventanas[s.ventana],modo=P.modo==='hoy'&&P.precios_disponibles?'hoy':'dia';
    const rows=(v?P.filas.filter(r=>r.fecha>=v.ini&&r.fecha<v.fin):[]).map(r=>({...r,valor:(modo==='hoy'?r.valorHoy:r.valorDia)??0,valorCosto:modo==='hoy'?r.cant*(P.productos[r.prod].precio??0):r.costo}));
    const productos=[...group(rows,r=>r.prod)].map(([id,rs])=>({id,...P.productos[id],valor:sum(rs,'valor')})).sort((a,b)=>b.valor-a.valor||cmp(a.cod,b.cod)||cmp(a.unid,b.unid));
    const ch=cambios(rows,P),prod=productos.find(r=>r.id===s.prod)||productos.find(r=>r.id===ch[0]?.prod)||productos[0]||null;
    const xs=rows.filter(r=>r.prod===prod?.id),cab=new Map(xs.map(r=>[r.doc,r])),cs=P.cortes.filter(r=>cab.has(r.doc)),pc=cortes(xs,cs,P.reciente);
    const corte=pc.find(r=>r.key===s.corte)||pc.find(r=>r.clave===s.corte)||pc[0]||null;
    const norm=P.normales[String(prod?.id)]??null,med=norm&&norm.n>=P.min_normal?norm.med:null,filasCorte=cs.filter(r=>r.key===corte?.key);
    const rec=agregado(xs.filter(r=>r.fecha>=P.reciente)),ant=agregado(xs.filter(r=>r.fecha<P.reciente)),a=agregado(xs);
    const q=plano(s.q),docs=xs.filter(r=>(!s.solo||r.marcas.length||r.merma==null)&&(!s.mes||mes(r.fecha)===s.mes)&&(!q||plano([r.doc,r.area,r.usuario,r.proveedor,...cs.filter(c=>c.doc===r.doc).map(c=>c.nombre+' '+c.cod)].join(' ')).includes(q))).sort((a,b)=>cmp(b.fecha,a.fecha)||cmp(a.doc,b.doc));
    const elegido=xs.find(r=>r.doc===s.doc)||null,conMerma=xs.filter(r=>r.cant!=null&&r.merma!=null),queda=conMerma.reduce((a,r)=>a+r.cant-r.merma,0);
    return{modo,rows,productos,ch,prod,xs,cs,pc,corte,norm,med,mes:mensual(xs),mesCorte:mensualCorte(xs,filasCorte,med),filasCorte,rec,ant,
      kpi:{...a,queda,conMerma:conMerma.length,util:queda>0?a.costo/queda:null,valor:sum(xs,'valor'),dpp:rec.pct!=null&&ant.pct!=null?rec.pct-ant.pct:null,n:xs.length,observaciones:xs.filter(r=>r.marcas.length||r.merma==null).length},
      docs,elegido,cortesElegido:cs.filter(r=>r.doc===elegido?.doc)};
  }
  const col=(k,n,t='texto')=>({k,n,t});
  function cols(G,id){const u=G.D.prod?.unid||'unidad';if(id==='cortes')return[col('nombre','Corte'),col('unid','UM'),col('antes','Antes','sol'),col('ahora','90 días','sol'),col('var','Δ precio','pct'),col('causa','Factor principal')];
    if(id==='cambios')return[col('nombre','Producto'),col('unid','UM'),col('pct_ant','Antes','pct'),col('pct_rec','90 días','pct'),col('dpp','Δ merma','pp'),col('dprecio','Δ costo','pct'),col('impacto','Impacto','sol')];
    return[col('doc','N.º porcionamiento'),col('fecha','Fecha','fecha'),col('cant',`Entrada (${u})`,'num'),col('merma',`Merma (${u})`,'num'),col('pct','Merma %','pct'),col('costo','Costo día','sol'),col('valor','Merma S/','sol'),col('proveedor','Proveedor atribuido'),col('usuario','Usuario'),col('marcasTxt','Observaciones')];
  }
  function listas(G){const{D,P}=G;return{cortes:D.pc.map(r=>({...r,antes:r.a.n?r.a.P:null,ahora:r.b.n?r.b.P:null,causa:r.causa??'Sin comparación'})),cambios:D.ch,docs:D.docs.map(r=>({...r,marcasTxt:observaciones(r,P).join(' · ')}))};}
  function valor(v,c){return c.t==='sol'?sol(v):c.t==='num'?n(v):c.t==='pct'?pct(v):c.t==='pp'?pp(v):c.t==='fecha'?fecha(v):String(v??'—');}
  function ordenar(rs,cfg){if(!cfg)return rs;const[k,d]=cfg;return rs.slice().sort((a,b)=>(a[k]==null)-(b[k]==null)||(typeof a[k]==='number'&&typeof b[k]==='number'?(a[k]-b[k])*d:cmp(a[k]??'',b[k]??'')*d));}
  function renglones(G,t,ini,fin){return t.rows.slice(ini,fin).map(r=>{
    const a=t.id==='cortes'?'corte':t.id==='cambios'?'producto':'doc',v=t.id==='cortes'?r.key:t.id==='cambios'?r.prod:r.doc,on=t.id==='cortes'?r.key===G.D.corte?.key:t.id==='cambios'?r.prod===G.D.prod?.id:r.doc===G.s.doc;
    return`<tr tabindex="0" data-a="${a}" data-v="${esc(v)}" aria-selected="${on}" class="${on?'on':''}">${t.cols.map(c=>`<td title="${esc(c.n+': '+(r[c.k]??'Sin base'))}" class="${['num','sol','pct','pp'].includes(c.t)?'mre-num':''}">${esc(valor(r[c.k],c))}</td>`).join('')}</tr>`;
  }).join('');}
  function tabla(G,id,rs){const t={id,rows:ordenar(rs,G.s.orden[id]),cols:cols(G,id),n:150};G.tablas[id]=t;return`<div class="mre-scroll" data-tabla="${id}"><table><thead><tr>${t.cols.map(c=>`<th><button data-a="orden" data-t="${id}" data-v="${c.k}">${esc(c.n)}</button></th>`).join('')}</tr></thead><tbody>${renglones(G,t,0,150)}</tbody></table>${rs.length?'':'<p class="mre-vacio">Sin datos para esta selección.</p>'}</div>`;}
  function grafico(G,tipo){
    const{D,P,s}=G,v=P.ventanas[s.ventana];if(!v||!D.xs.length)return'<p class="mre-vacio">Sin porcionamientos en la ventana.</p>';
    const esMerma=tipo==='merma',esCorte=!esMerma&&s.precio==='Precio del corte'&&D.corte;
    const cab=new Map(D.xs.map(r=>[r.doc,r])),dots=esMerma?D.xs.map(r=>({doc:r.doc,f:r.fecha,y:r.pct,rare:r.marcas.some(k=>['alta','baja','cero','sinpeso'].includes(k)),label:`${r.doc} · ${fecha(r.fecha)} · ${pct(r.pct)} · ${r.usuario}`})):esCorte?D.filasCorte.filter(r=>r.cant>0).map(r=>({doc:r.doc,f:cab.get(r.doc).fecha,y:r.valor/r.cant,label:`${r.doc} · ${fecha(cab.get(r.doc).fecha)} · ${sol(r.valor/r.cant)} / ${r.unid}`})):D.xs.filter(r=>r.costo>0).map(r=>({doc:r.doc,f:r.fecha,y:r.costo/r.cant,label:`${r.doc} · ${fecha(r.fecha)} · ${sol(r.costo/r.cant)} / ${D.prod.unid}`}));
    const serie=esMerma?D.mes.map(r=>({f:r.mes,y:r.pct})):esCorte?D.mesCorte.map(r=>({f:r.mes,y:r.precio})):D.mes.map(r=>({f:r.mes,y:r.pkg}));
    const ref=esMerma?[]:esCorte?D.mesCorte.map(r=>({f:r.mes,y:r.normal})):D.prod.precio?[{f:v.ini,y:D.prod.precio},{f:v.fin,y:D.prod.precio}]:[];
    const ys=[0,...dots.map(r=>r.y),...serie.map(r=>r.y),...ref.map(r=>r.y),...(esMerma&&D.norm?[D.norm.q1,D.norm.q3]:[])].filter(y=>y!=null&&Number.isFinite(y));
    const lo=Math.min(...ys),hi=Math.max(...ys),pad=(hi-lo||1)*.08,y0=lo<0?lo-pad:lo,y1=hi+pad;
    const w=Math.max(260,Math.floor(G.raiz.clientWidth<800?G.raiz.clientWidth-28:G.raiz.clientWidth*.62-40)),h=143,l=60,r=10,t=8,b=24,dt=f=>Date.parse(f),start=dt(v.ini),end=dt(v.fin),x=f=>l+(dt(f)-start)/(end-start||1)*(w-l-r),y=z=>h-b-(z-y0)/(y1-y0)*(h-t-b);
    const path=rs=>rs.filter(r=>r.y!=null&&Number.isFinite(r.y)).map((r,i)=>`${i?'L':'M'}${x(r.f).toFixed(2)},${y(r.y).toFixed(2)}`).join(' ');
    const ticks=[0,.5,1].map(k=>{const z=y0+(y1-y0)*k;return`<line x1="${l}" x2="${w-r}" y1="${y(z)}" y2="${y(z)}" class="mre-grid"/><text x="${l-6}" y="${y(z)+3}" text-anchor="end">${esc(esMerma?pct(z):n(z))}</text>`;}).join('');
    const band=esMerma&&D.norm?.q1!=null&&D.norm?.q3!=null?`<rect x="${l}" y="${y(D.norm.q3)}" width="${w-l-r}" height="${Math.max(0,y(D.norm.q1)-y(D.norm.q3))}" class="mre-band"/>`:'';
    const dotsSVG=dots.filter(r=>r.y!=null&&Number.isFinite(r.y)).map(d=>`<circle tabindex="0" role="button" aria-label="${esc(d.label)}" data-a="doc" data-v="${esc(d.doc)}" cx="${x(d.f)}" cy="${y(d.y)}" r="${d.rare?4:3}" class="${d.rare?'mre-raro':'mre-dot'} ${s.doc===d.doc?'mre-elegido':''}"><title>${esc(d.label)}</title></circle>`).join('');
    const months=serie.filter((_,i)=>i%(serie.length>8?2:1)===0).map(d=>`<text x="${x(d.f)}" y="${h-5}" text-anchor="middle">${esc(d.f.slice(0,7))}</text>`).join('');
    const points=serie.filter(d=>d.y!=null).map(d=>`<circle tabindex="0" role="button" aria-label="Ver ${d.f.slice(0,7)}" data-a="mes" data-v="${d.f}" cx="${x(d.f)}" cy="${y(d.y)}" r="3" class="mre-mes"><title>${esc(d.f.slice(0,7)+' · '+(esMerma?pct(d.y):sol(d.y)))}</title></circle>`).join('');
    return`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esMerma?'Merma por porcionamiento':'Precio histórico y referencia'}">${band}${ticks}<path d="${path(ref)}" class="mre-ref"/>${dotsSVG}<path d="${path(serie)}" class="mre-linea"/>${points}${months}</svg>`;
  }
  function notaCorte(D){const r=D.corte;if(!r?.desglose)return'Para repartir el cambio se necesitan cortes antes y en los últimos 90 días, con precio y factores positivos.';
    return`Antes ${sol(r.a.P)} → últimos 90 días ${sol(r.b.P)} (${pct(r.var)}). ${FACTORES.map(k=>`${k}: ${sol(r.desglose[k])}`).join(' · ')}. Suma: ${sol(sum(FACTORES.map(k=>({v:r.desglose[k]})),'v'))} por ${r.unid}.`;
  }
  function ficha(G){const{D,P}=G,r=D.elegido;if(!G.s.ficha||!r)return'';const u=D.prod.unid,q=r.merma==null?null:r.cant-r.merma,precio=D.prod.precio;
    return`<div class="mre-velo" data-a="cerrar"><section class="mre-ficha" role="dialog" aria-modal="true" aria-label="Ficha del porcionamiento"><header><h4>Porcionamiento ${esc(r.doc)} · ${fecha(r.fecha)}</h4><button data-a="cerrar" aria-label="Cerrar ficha">Cerrar ×</button></header><p>${esc(D.prod.nombre)} · ${esc(r.area)} · ${esc(r.usuario)}</p><p><b>${q==null?'Falta merma: cantidad útil sin base':`${n(r.cant)} ${esc(u)} → ${n(q)} ${esc(u)} útiles`}</b> · rendimiento ${pct(q==null?null:ratio(q,r.cant))} · merma ${pct(r.pct)}</p><p>Merma al costo del día: <b>${sol(r.valorDia)}</b> · a precio de hoy: <b>${P.precios_disponibles?sol(r.valorHoy):'Precio actual no disponible'}</b>${precio==null?' · código sin precio actual conocido':''}.</p><p>Proveedor atribuido: ${esc(r.proveedor??'Sin proveedor asignable')}. Cambiar valorización conserva la merma física.</p><p>${observaciones(r,P).map(esc).join(' · ')||'Sin observaciones de las reglas actuales.'}</p><div class="mre-scroll"><table><thead><tr><th>Corte</th><th>Cantidad</th><th>UM final</th><th>Peso (${esc(u)})</th><th>Precio día</th><th>Valor día</th></tr></thead><tbody>${D.cortesElegido.map(c=>`<tr><td>${esc(c.nombre)}</td><td>${n(c.cant)}</td><td>${esc(c.unid)}</td><td>${n(c.peso)}</td><td>${sol(c.pprom)}</td><td>${sol(c.valor)}</td></tr>`).join('')}</tbody></table></div><small>Los cortes conservan su costo del día. El peso está en la unidad de origen y su cantidad en la unidad final.</small></section></div>`;
  }
  function dibujar(G){const{P,s,raiz}=G,active=raiz.contains(raiz.getRootNode().activeElement||document.activeElement)?(raiz.getRootNode().activeElement||document.activeElement):null,k=active?.dataset.k,pos=active?.selectionStart;
    G.D=calcular(P,s);const D=G.D,L=listas(G);if(D.prod)s.prod=D.prod.id;if(D.corte)s.corte=D.corte.key;G.tablas={};
    const a=D.kpi,u=D.prod?.unid||'unidad',precioCorte=s.precio==='Precio del corte'&&D.corte,titulo=precioCorte?`${D.corte.nombre} · S/ por ${D.corte.unid}`:`Costo del día por ${u} que entró`;
    raiz.innerHTML=`<section class="mre-card mre-main"><header><div><h3>Rendimiento por producto</h3><p>${esc(P.ventanas[s.ventana]?.rotulo??'Sin fechas disponibles')} · ${D.modo==='hoy'?'Precio de hoy':'Costo del día'}${P.modo==='hoy'&&!P.precios_disponibles?' · precio actual no disponible':''}</p></div><button data-a="excel">Excel de esta vista ↓</button></header><div class="mre-controles"><div class="mre-seg">${Object.keys(P.ventanas).map(v=>`<button data-a="ventana" data-v="${esc(v)}" class="${s.ventana===v?'on':''}">${esc(v)}</button>`).join('')}</div><label>Producto <select data-k="prod" aria-label="Producto">${D.productos.map(r=>`<option value="${r.id}" ${D.prod?.id===r.id?'selected':''}>${esc(r.nombre||r.cod)} · ${esc(r.unid)} · ${sol(r.valor)}</option>`).join('')}</select></label></div><div class="mre-kpis"><div><span>Merma de la ventana</span><b>${pct(a.pct)}</b><small>${a.n} registros · ${n(a.cant)} ${esc(u)}</small></div><div><span>Últimos 90 días</span><b>${pct(D.rec.pct)}</b><small>${pp(a.dpp)} contra antes ${pct(D.ant.pct)}</small></div><div><span>Costo del día / ${esc(u)}, 90 d.</span><b>${sol(D.rec.pkg)}</b><small>Antes ${sol(D.ant.pkg)} · hoy ${sol(D.prod?.precio)}</small></div><div><span>Costo / ${esc(u)} útil</span><b>${sol(a.util)}</b><small>Pagado ÷ cantidad útil · ${a.conMerma}/${a.n} con merma conocida</small></div><div><span>Merma en soles</span><b>${sol(a.valor)}</b><small>${D.modo==='hoy'?'Precio de hoy':'Costo del día'}</small></div></div><div class="mre-cuerpo"><div class="mre-graficas"><div class="mre-grafica"><h4>Merma por porcionamiento <small>· banda: mitad central del historial</small></h4>${grafico(G,'merma')}</div><div class="mre-grafica"><div class="mre-g2"><h4 title="${esc(titulo)}">${esc(titulo)}</h4><div class="mre-seg">${['Precio del corte','Costo del insumo'].map(v=>`<button data-a="precio" data-v="${v}" class="${s.precio===v?'on':''}">${v}</button>`).join('')}</div></div>${grafico(G,'precio')}</div><p class="mre-nota">${esc(precioCorte?notaCorte(D):'Puntos: costo del día por entrada. Línea: promedio mensual ponderado. Cortada: precio de hoy, si está disponible.')}</p></div><div class="mre-panel"><div class="mre-seg">${['Cortes de este producto','Productos que cambiaron'].map(v=>`<button data-a="lista" data-v="${v}" class="${s.lista===v?'on':''}">${v}</button>`).join('')}</div><small>${s.lista==='Cortes de este producto'?'Precio por unidad: últimos 90 días frente al resto de la ventana. Selecciona un corte.':`Al menos ${P.min_cambios} registros en cada lado. Impacto de los puntos de merma en la valorización elegida.`}</small>${s.lista==='Cortes de este producto'?tabla(G,'cortes',L.cortes):tabla(G,'cambios',L.cambios)}<small>Normal: historial desde ${fecha(P.historia_desde)}; ${D.norm?.n??0} registros${D.norm&&D.norm.n<P.min_normal?' · muestra insuficiente para precio con merma normal':''}. Clic en un punto para abrir su ficha.</small></div></div></section><section class="mre-card mre-documentos"><header><div><h3>Historial del producto</h3><p>${esc(D.prod?.nombre??'Sin producto')} · ${D.docs.length} visibles de ${D.xs.length} registros de la ventana${s.mes?' · mes '+s.mes.slice(0,7):''}</p></div>${s.mes?'<button data-a="limpiarMes">Quitar mes</button>':''}</header><div class="mre-controles"><input type="search" data-k="q" value="${esc(s.q)}" placeholder="Buscar documento, corte, usuario o proveedor…" aria-label="Buscar en el historial"><label><input type="checkbox" data-k="solo" ${s.solo?'checked':''}> Sólo observaciones (${a.observaciones})</label><small>La búsqueda y las observaciones filtran esta lista; los indicadores conservan toda la ventana.</small></div>${tabla(G,'docs',L.docs)}<small>Cabeceras contadas una vez, cortes completos en la ficha. Cantidades separadas por producto y unidad; sin corregir valores de origen.</small></section>${ficha(G)}`;
    if(k){const el=raiz.querySelector(`[data-k="${k}"]`);el?.focus({preventScroll:true});if(pos!=null&&el?.type==='search')el.setSelectionRange(pos,pos);}
    if(s.ficha){raiz.querySelector('.mre-ficha [data-a=cerrar]')?.focus({preventScroll:true});}
  }
  function exportar(G){const{P,D,s}=G,L=listas(G),hoja=(nombre,id,rows)=>{const cs=cols(G,id);return{nombre,cabeza:cs.map(c=>c.n),filas:ordenar(rows,s.orden[id]).map(r=>cs.map(c=>r[c.k]??''))};};
    return[hoja('Cortes del producto','cortes',L.cortes),hoja('Cambios de productos','cambios',L.cambios),hoja('Historial visible','docs',L.docs),
      {nombre:'Historial completo',cabeza:['Documento','Fecha','Código','Producto','Unidad','Cantidad','Merma','Costo día','Merma día','Merma hoy','Proveedor atribuido','Usuario','Observaciones'],filas:D.xs.map(r=>[r.doc,r.fecha,D.prod.cod,D.prod.nombre,D.prod.unid,r.cant,r.merma,r.costo,r.valorDia,r.valorHoy,r.proveedor??'',r.usuario,observaciones(r,P).join(' · ')])},
      {nombre:'Cortes completos',cabeza:['Documento','Clave','Código','Corte','Cantidad final','Unidad final','Peso asignado','Unidad de origen','Precio día','Valor día'],filas:D.cs.map(r=>[r.doc,r.clave,r.cod,r.nombre,r.cant,r.unid,r.peso,D.prod?.unid??'',r.pprom,r.valor])},
      {nombre:'Series mensuales',cabeza:['Mes','Merma fracción','Costo día por entrada','Precio corte','Merma del corte','Precio con merma normal'],filas:D.mes.map(r=>{const c=D.mesCorte.find(c=>c.mes===r.mes);return[r.mes,r.pct,r.pkg,c?.precio??'',c?.merma??'',c?.normal??''];})},
      {nombre:'Factores del corte',cabeza:['Clave','Corte','Unidad','Antes','90 días','Insumo','Merma','Gramaje','Otros','Cambio total','Registros antes','Registros recientes'],filas:D.pc.map(r=>[r.clave,r.nombre,r.unid,r.a.P,r.b.P,r.desglose?.insumo??'',r.desglose?.merma??'',r.desglose?.gramaje??'',r.desglose?.otros??'',r.desglose?r.b.P-r.a.P:'',r.a.n,r.b.n])},
      {nombre:'Contexto',cabeza:['Concepto','Valor'],filas:[['Ventana',s.ventana],['Desde incluido',P.ventanas[s.ventana]?.ini??''],['Hasta excluido',P.ventanas[s.ventana]?.fin??''],['Historia normal desde',P.historia_desde??''],['Valorización efectiva',D.modo],['Precio actual disponible',P.precios_disponibles?'Sí':'No'],['Producto',D.prod?`${D.prod.cod} · ${D.prod.nombre} · ${D.prod.unid}`:''],['Corte elegido',D.corte?.nombre??''],['Búsqueda',s.q],['Sólo observaciones',s.solo?'Sí':'No'],['Mes de la lista',s.mes??'Todos'],['Rango normal',D.norm?JSON.stringify(D.norm):'Sin base'],['Registros con merma conocida',`${D.kpi.conMerma} de ${D.kpi.n}`],['Merma','Σ merma física ÷ Σ cantidad; costo útil = Σ costo del día ÷ Σ (cantidad − merma) con ambos datos conocidos'],['Factores','LMDI: insumo + merma + gramaje + otros = cambio del precio ponderado del corte'],['Proveedor','Atribuido a última compra hasta 45 días antes; no es lote identificado'],['Decimales','Seis en Excel; cálculos sin redondeo previo'],...Object.entries(P.contexto).map(([k,v])=>[k,Array.isArray(v)?v.join(', '):v])]}].map(h=>({...h,decimales:6}));
  }
  function montar(component){const{data:P,parentElement}=component,prev=window.__mermaRend;prev?.abort.abort();prev?.ro?.disconnect();const s=prev?.s??estado(P.inicial);
    if(prev&&prev.P.sello_origen!==P.sello_origen){s.prod=null;s.doc=null;s.ficha=false;s.mes=null;}
    if(!prev||prev.P.comun!==P.comun){const init=P.inicial??{},id=P.productos.findIndex(r=>r.cod===init.cod&&(!init.unid||r.unid===init.unid));const salto=prev&&P.salto!==prev.P.salto,externo=id>=0&&id!==s.prod;if(externo){s.prod=id;s.doc=null;s.ficha=false;}if(!prev||externo||salto||init.corte!==prev.P.inicial?.corte)s.corte=init.corte??s.corte;if(!prev||externo||salto||init.precio!==prev.P.inicial?.precio)s.precio=init.precio??s.precio;}
    if(!P.ventanas[s.ventana])s.ventana=Object.keys(P.ventanas)[0]??'12 meses';
    let raiz=parentElement.querySelector('.mre');if(!raiz){raiz=document.createElement('div');raiz.className='mre';parentElement.appendChild(raiz);}
    const G={P,s,raiz,component,abort:new AbortController(),tablas:{},enviado:JSON.stringify([P.inicial?.cod,P.inicial?.unid])};window.__mermaRend=G;const{signal}=G.abort;
    function avisar(){const p=G.D.prod;if(!p)return;const key=JSON.stringify([p.cod,p.unid]);if(key!==G.enviado){G.enviado=key;component.setTriggerValue?.('producto',{sello:P.sello,cod:p.cod,unid:p.unid});}}
    raiz.addEventListener('click',e=>{const el=e.target.closest('[data-a]');if(!el)return;const a=el.dataset.a,v=el.dataset.v;
      if(a==='excel'){bajar('Rendimiento_por_producto.xlsx',libro(exportar(G)));return;}
      if(a==='cerrar'&&e.target.closest('.mre-ficha')&&!e.target.closest('button[data-a=cerrar]'))return;
      if(a==='ventana'){s.ventana=v;s.doc=null;s.ficha=false;s.mes=null;}
      else if(a==='producto'){s.prod=Number(v);s.corte=null;s.doc=null;s.ficha=false;s.mes=null;}
      else if(a==='corte'){s.corte=v;s.precio='Precio del corte';}
      else if(a==='precio')s.precio=v;
      else if(a==='lista')s.lista=v;
      else if(a==='mes'){s.mes=s.mes===v?null:v;}
      else if(a==='limpiarMes')s.mes=null;
      else if(a==='doc'){G.origenFicha=el;s.doc=v;s.ficha=true;}
      else if(a==='cerrar')s.ficha=false;
      else if(a==='orden'){const t=el.dataset.t,old=s.orden[t];s.orden[t]=[v,old?.[0]===v?-old[1]:1];}
      dibujar(G);if(a==='producto')avisar();if(a==='cerrar')(raiz.querySelector(`[data-tabla=docs] tr[data-v="${CSS.escape(s.doc??'')}"]`)||raiz.querySelector('[data-k=q]'))?.focus({preventScroll:true});
    },{signal});
    raiz.addEventListener('change',e=>{const k=e.target.dataset.k;if(k==='prod'){s.prod=Number(e.target.value);s.corte=null;s.doc=null;s.ficha=false;s.mes=null;dibujar(G);avisar();}else if(k==='solo'){s.solo=e.target.checked;dibujar(G);}},{signal});
    raiz.addEventListener('input',e=>{if(e.target.dataset.k==='q'){s.q=e.target.value;dibujar(G);}},{signal});
    raiz.addEventListener('keydown',e=>{if(e.key==='Escape'&&s.ficha){s.ficha=false;dibujar(G);(raiz.querySelector(`[data-tabla=docs] tr[data-v="${CSS.escape(s.doc??'')}"]`)||raiz.querySelector('[data-k=q]'))?.focus({preventScroll:true});return;}if((e.key==='Enter'||e.key===' ')&&e.target.matches('tr[data-a],circle[data-a]')){e.preventDefault();e.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));}if(e.key==='Tab'&&s.ficha){const f=[...raiz.querySelectorAll('.mre-ficha button,.mre-ficha [tabindex="0"]')],a=f[0],b=f.at(-1);if(e.shiftKey&&(raiz.getRootNode().activeElement||document.activeElement)===a){e.preventDefault();b?.focus();}else if(!e.shiftKey&&(raiz.getRootNode().activeElement||document.activeElement)===b){e.preventDefault();a?.focus();}}},{signal});
    raiz.addEventListener('scroll',e=>{const el=e.target,t=G.tablas[el.dataset?.tabla];if(!t||el.scrollTop+el.clientHeight<el.scrollHeight-220||t.n>=t.rows.length)return;el.querySelector('tbody').insertAdjacentHTML('beforeend',renglones(G,t,t.n,t.n+150));t.n+=150;},{signal,capture:true});
    dibujar(G);let ancho=raiz.clientWidth;G.ro=new ResizeObserver(()=>{if(Math.abs(raiz.clientWidth-ancho)>2){ancho=raiz.clientWidth;dibujar(G);}});G.ro.observe(raiz);return()=>{G.abort.abort();G.ro.disconnect();};
  }
  return{estado,agregado,mensual,lado,desglose,cortes,mensualCorte,cambios,calcular,exportar,montar};
})();
window.__mermaRendDatos=REND;
export default function(component){return REND.montar(component);}
