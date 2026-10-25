// Cuentas de productos: mismas ventanas, mediana por línea y cobertura por área (#734).
const REQ=(()=>{
  const sum=(rs,k)=>rs.reduce((a,r)=>a+(Number(r[k])||0),0);
  const grupo=n=>n>=150?'Casi diario':n>=53?'Semanal':n>=13?'Ocasional':'Esporádico';
  const agrupar=(rs,k)=>{const m=new Map();for(const r of rs){const key=typeof k==='function'?k(r):r[k];if(!m.has(key))m.set(key,[]);m.get(key).push(r);}return m;};
  const mediana=ns=>{if(!ns.length)return null;const s=[...ns].sort((a,b)=>a-b),m=Math.floor(s.length/2);return s.length%2?s[m]:(s[m-1]+s[m])/2;};
  function preparar(P){
    const fila=f=>({i:f[0],area:f[1],fam:f[2],subfam:f[3],doc:f[4],fecha:f[5],cant:f[6],valor:f[7],habitual:f[8],veces:f[9],exceso:f[10],nuevo:f[11],repite_min:f[12]});
    return{P,L:P.rango.map(fila),V:P.ventana.map(fila),sal:new Map(P.salida.map(r=>[r[0]+'|'+r[1],{cubre:r[2],descarga:r[3]}]))};
  }
  function recorte(rs,s){return rs.filter(r=>(s.area==null||s.area===r.area)&&(s.fam==null||s.fam===r.fam)&&(s.subfam==null||s.subfam===r.subfam));}
  function productos(B,L,V){
    const gs=agrupar(L,'i'),total=sum(L,'valor'),vs=agrupar(V,'i'),salDisponible=B.P.salida.length>0;
    return[...gs].map(([i,rs])=>{
      const v=vs.get(i)||[],pa=agrupar(v,'area');let conocido=false,sin=0,pv=0,descarga=false;
      for(const [a,ls]of pa){const sal=B.sal.get(i+'|'+a),desc=salDisponible?(sal?.descarga??true):true;descarga||=desc;
        if(desc&&sal?.cubre!=null){const val=sum(ls,'valor');conocido=true;sin+=val*(1-sal.cubre);pv+=val;}}
      const valor=sum(rs,'valor'),cant=sum(rs,'cant'),dias=new Set(v.map(r=>r.fecha.slice(0,10))).size;
      return{i,cod:B.P.productos[i][0],prod:B.P.productos[i][1],unid:B.P.productos[i][2],valor,pct:total?valor/total*100:0,cant,punit:cant>0?valor/cant:null,
        ped_vent:sum(v,'valor'),dias,grupo:grupo(dias),tipico:mediana(v.map(r=>r.cant)),
        fuera:v.filter(r=>r.veces>0).length,exceso:sum(v,'exceso'),nuevos:v.filter(r=>r.nuevo).length,repetidos:v.filter(r=>r.repite_min!=null).length,
        salio:conocido&&pv>0?1-sin/pv:null,sin_salida:conocido?sin:null,no_descarga:salDisponible&&pa.size>0?!descarga:false};
    }).sort((a,b)=>b.valor-a.valor);
  }
  function resumen(tabla){const rs=tabla.filter(r=>!r.no_descarga&&r.salio!=null),poco=rs.filter(r=>r.salio<.5);return[sum(rs,'sin_salida'),sum(rs,'ped_vent'),poco.length,sum(poco,'sin_salida')];}
  function rank(rs,k){return[...agrupar(rs,k)].map(([i,ls])=>({i,valor:sum(ls,'valor'),productos:new Set(ls.map(r=>r.i)).size})).sort((a,b)=>b.valor-a.valor);}
  function calcular(B,s){
    const clave=JSON.stringify([s.area??null,s.fam??null,s.subfam??null]);
    if(B._core?.clave!==clave){
      const L=recorte(B.L,s),V=recorte(B.V,s),tabla=productos(B,L,V);
      B._core={clave,L,V,tabla,resumen:resumen(tabla),areas:rank(B.L,'area'),familias:rank(recorte(B.L,{area:s.area}),'fam'),
        subfamilias:rank(recorte(B.L,{area:s.area,fam:s.fam}),'subfam'),total:sum(L,'valor')};
    }
    const {tabla}=B._core;
    const visibles=tabla.filter(r=>(!s.grupo||s.grupo===r.grupo)&&(!s.poco||!r.no_descarga&&r.salio!=null&&r.salio<.5)
      &&(!s.q||(r.cod+' '+r.prod).toLowerCase().includes(s.q.toLowerCase()))
      &&(!s.marca||s.marca==='fuera'&&r.fuera||s.marca==='nuevo'&&r.nuevos||s.marca==='repite'&&r.repetidos));
    return{...B._core,visibles};
  }
  function ficha(B,D,i){
    const ls=D.V.filter(r=>r.i===i),areas=new Set(ls.map(r=>r.area)),k=B.P.kardex.filter(r=>r[0]===i&&areas.has(r[1]));
    const ms=B.P.meses.map((mes,m)=>{
      const rr=ls.filter(r=>r.fecha.slice(0,7)===mes),kk=k.filter(r=>r[2]===m),val=j=>kk.reduce((a,r)=>a+(r[j]||0),0);
      const ped=sum(rr,'cant'),ven=val(4),pro=val(5),nts=val(6),tra=val(7),aj=val(8),sal=ven+pro+nts+Math.max(0,tra);
      return{mes,ped,valor:sum(rr,'valor'),ven,pro,nts,tra,aj,sal,parte:Math.min(ped,sal),resto:Math.max(ped-Math.min(ped,sal),0)};
    });
    const ini=Date.parse(B.P.desde+'T00:00:00Z'),semanas=Array(53).fill(0);
    for(const l of ls){const f=Date.parse(l.fecha.slice(0,10)+'T00:00:00Z'),j=Math.max(0,Math.min(52,Math.floor((f-ini)/6048e5)));semanas[j]+=l.cant;}
    return{producto:D.tabla.find(r=>r.i===i),ls,ms,semanas,documentos:new Set(ls.map(r=>r.doc)).size,areas:[...areas]};
  }
  return{preparar,recorte,productos,resumen,rank,calcular,ficha,grupo,sum,agrupar,mediana};
})();
window.__reqAreaDatos=REQ;
export default function(component){
  const old=window.__reqArea;old?.cleanup();
  const P=component.data,B=REQ.preparar(P),owner=component.parentElement.ownerDocument;
  let root=component.parentElement.querySelector('.rqa');if(!root){root=owner.createElement('div');root.className='rqa';component.parentElement.append(root);}
  const abort=new AbortController(),esc=x=>String(x??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const n=(x,d=2)=>x==null?'—':Number(x).toLocaleString('es-PE',{maximumFractionDigits:d}),sol=x=>x==null?'—':'S/ '+n(x),por=x=>x==null?'—':n(x*100,1)+' %';
  const btn=(a,v,t,on=false)=>`<button type="button" data-a="${a}" data-v="${esc(v)}" aria-pressed="${on}" class="${on?'on':''}">${t}</button>`;
  const K='mov_req_area_734';let ui={};try{ui=JSON.parse(sessionStorage.getItem(K)||'{}')||{};}catch(e){}
  const id=(xs,v)=>v==null?null:xs.includes(v)?xs.indexOf(v):null;
  let s={area:id(P.areas,ui.area),fam:id(P.familias,ui.fam),subfam:id(P.subfamilias,ui.subfam),cod:ui.cod||null,grupo:ui.grupo||null,
    poco:!!ui.poco&&P.kardex_disponible,q:typeof ui.q==='string'?ui.q:'',marca:['fuera','nuevo','repite'].includes(ui.marca)?ui.marca:'',
    orden:ui.orden||'valor',asc:!!ui.asc,mes:null,semana:null,dq:'',doc:null};
  if(!ui.iniciado)s.area=REQ.rank(B.L,'area')[0]?.i??null;
  if(!['Casi diario','Semanal','Ocasional','Esporádico'].includes(s.grupo))s.grupo=null;
  if(!['valor','prod','cant','punit','salio','dias','fuera','repetidos','exceso'].includes(s.orden))s.orden='valor';
  let D,F;const lotes=new Map();
  const guardar=()=>{try{sessionStorage.setItem(K,JSON.stringify({...s,iniciado:true,area:P.areas[s.area]??null,fam:P.familias[s.fam]??null,subfam:P.subfamilias[s.subfam]??null}));}catch(e){}};
  root.innerHTML=`<div class="rqa-nota" data-k="nota"></div><div class="rqa-cadena">${['area','fam','subfam'].map(k=>`<section class="rqa-card"><h3>${{area:'Sub almacén',fam:'Familia',subfam:'Subfamilia'}[k]}</h3><div class="rqa-wrap rqa-rank" data-rank="${k}"></div></section>`).join('')}</div>
    <section class="rqa-card"><div class="rqa-h"><h3>Productos</h3><button type="button" data-a="excel">Excel con fuentes ↓</button></div>
      <p data-k="salida" class="rqa-ayuda"></p><div data-k="grupos" class="rqa-grupos"></div>
      <div class="rqa-controles"><input type="search" data-k="q" aria-label="Buscar producto o código" placeholder="Buscar producto o código…"><label><input type="checkbox" data-k="poco"> Salió menos de la mitad</label>
      <select data-k="marca" aria-label="Marca de los pedidos"><option value="">Todas las marcas</option value="fuera">Fuera de lo habitual</option><option value="nuevo">Primera vez en 90 días</option><option value="repite">Repetido en el día</option></select></div>
      <div class="rqa-wrap" data-wrap="productos"><table><thead><tr>${[['prod','Producto'],['valor','Pedido S/'],['cant','Cantidad'],['punit','S/ por unidad'],['salio','Salió registrado'],['dias','Días con pedido'],['fuera','Fuera de habitual'],['exceso','Exceso S/'],['repetidos','Repetidos']].map(([k,t])=>`<th>${btn('orden',k,esc(t))}</th>`).join('')}</tr></thead><tbody data-tabla="productos"></tbody></table></div>
      <div data-k="productos-pie" class="rqa-ayuda"></div></section>
    <section class="rqa-card" data-panel="ficha"></section>
    <section class="rqa-card"><div class="rqa-h"><h3>Sus pedidos · 12 meses</h3><span data-k="tramo"></span>${btn('limpiar-tramo','','Todo el período')}</div>
      <input type="search" data-k="dq" aria-label="Buscar documento o área" placeholder="Buscar documento o área…"><div class="rqa-wrap"><table><thead><tr><th>Fecha</th><th>Requerimiento</th><th>Área</th><th>Cantidad</th><th>S/</th><th>Marca</th></tr></thead><tbody data-tabla="pedidos"></tbody></table></div><p data-k="pedidos-pie" class="rqa-ayuda"></p></section>
    <dialog class="rqa-modal" aria-label="Requerimiento completo"><div class="rqa-h"><h3 data-k="doc-titulo"></h3><button type="button" data-a="cerrar">Cerrar</button></div><p class="rqa-ayuda">Todas sus líneas disponibles en las fuentes de la página, sin recorte por área, familia o producto del navegador.</p><div class="rqa-wrap"><table><thead><tr><th>Producto</th><th>Área</th><th>Fecha</th><th>Cantidad</th><th>Unidad</th><th>S/</th><th>Marca</th></tr></thead><tbody data-tabla="documento"></tbody></table></div></dialog>`;
  const $=sel=>root.querySelector(sel),$$=sel=>root.querySelectorAll(sel),out=(k,html)=>$(`[data-k="${k}"]`).innerHTML=html;
  $('[data-k=q]').value=s.q;$('[data-k=poco]').checked=s.poco;$('[data-k=poco]').disabled=!P.kardex_disponible;$('[data-k=marca]').value=s.marca;
  function tabla(nombre,rs,html){
    const tb=$(`[data-tabla="${nombre}"]`),wrap=tb.closest('.rqa-wrap');lotes.get(nombre)?.boton.remove();tb.innerHTML='';
    const boton=owner.createElement('button');boton.type='button';boton.className='rqa-mas';const lote={rs,n:0,boton};lotes.set(nombre,lote);
    const mas=()=>{const to=Math.min(lote.n+150,rs.length);tb.insertAdjacentHTML('beforeend',rs.slice(lote.n,to).map(html).join(''));lote.n=to;boton.hidden=to>=rs.length;boton.textContent=`Mostrar más · ${to} de ${rs.length}`;};
    if(!rs.length)tb.innerHTML='<tr><td colspan="10">Sin registros con estos filtros.</td></tr>';mas();wrap.after(boton);boton.onclick=mas;wrap.scrollTop=0;
    wrap.onscroll=()=>{if(wrap.scrollTop+wrap.clientHeight>=wrap.scrollHeight-100&&!boton.hidden)mas();};
  }
  const marca=r=>[r.veces>0?`Fuera de lo habitual ×${n(r.veces,1)} (habitual ${n(r.habitual)}, exceso ${sol(r.exceso)})`:'',r.nuevo?'Primera vez en 90 días':'',r.repite_min!=null?`Repetido en el día · ${n(r.repite_min,0)} min`:'' ].filter(Boolean).join(' · ')||'—';
  function rangos(){for(const [k,rs,labels]of [['area',D.areas,P.areas],['fam',D.familias,P.familias],['subfam',D.subfamilias,P.subfamilias]]){
    const total=REQ.sum(rs,'valor');$(`[data-rank=${k}]`).innerHTML=`<table><thead><tr><th>Nombre</th><th>S/</th><th>%</th></tr></thead><tbody>${rs.map(r=>`<tr data-a="${k}" data-v="${r.i}" tabindex="0" aria-selected="${s[k]===r.i}"><td style="background:linear-gradient(to right,var(--accent-tint) ${Math.max(0,Math.min(100,total?r.valor/total*100:0))}%,transparent 0)">${esc(labels[r.i]||'Sin categoría')}</td><td>${n(r.valor)}</td><td>${total?n(r.valor/total*100,1):'—'}</td></tr>`).join('')}</tbody><tfoot><tr data-a="${k}" data-v="" tabindex="0"><td>Total · todas</td><td>${n(total)}</td><td>${total?100:0}</td></tr></tfoot></table>`;
  }}
  function render(){D=REQ.calcular(B,s);rangos();out('nota',`Rango: ${esc(P.rango_desde)} a ${esc(P.rango_hasta)} (fin excluido). ${esc(P.nota[0]||'')} <span title="${esc(P.nota[1]||'')}">ⓘ</span>`);
    const [sin,ped,np]=D.resumen;
    out('salida',!P.kardex_disponible?'Salió registrado: no se pudo leer el kardex; los datos ausentes se muestran como —.':D.tabla.length&&D.tabla.every(r=>r.no_descarga)?'Estas áreas no registran salidas: su consumo se reconoce en el ajuste del cierre.':`En 12 meses, ${sol(sin)} (${por(ped?sin/ped:null)}) pedidos sin salida registrada. ${np} productos salieron menos de la mitad. La diferencia puede seguir en el área o aparecer en el cierre.`);
    out('grupos',['Casi diario','Semanal','Ocasional','Esporádico'].map(g=>{const rs=D.tabla.filter(r=>r.grupo===g);return btn('grupo',g,`${esc(g)} <small>${rs.length} productos · ${sol(REQ.sum(rs,'valor'))}</small>`,s.grupo===g);}).join(''));
    const rs=[...D.visibles].sort((a,b)=>{const x=a[s.orden],y=b[s.orden];if(x==null)return y==null?0:1;if(y==null)return -1;return(typeof x==='string'?x.localeCompare(y):x-y)*(s.asc?1:-1);});
    D.ordenados=rs;
    if(!rs.some(r=>r.cod===s.cod))s.cod=rs[0]?.cod??null;
    tabla('productos',rs,r=>`<tr data-a="producto" data-v="${r.i}" tabindex="0" aria-selected="${r.cod===s.cod}"><td>${esc(r.prod)}<small>${esc(r.cod)} · ${esc(r.unid)} · ${esc(r.grupo)}</small></td><td>${n(r.valor)}<small>${n(r.pct,1)} % del recorte</small></td><td>${n(r.cant)} ${esc(r.unid)}</td><td>${n(r.punit)}</td><td>${r.no_descarga?'No descarga':por(r.salio)}<small>${r.sin_salida==null?'':sol(r.sin_salida)+' sin registrar'}</small></td><td>${r.dias}<small>Típico ${n(r.tipico)} ${esc(r.unid)}</small></td><td>${r.fuera}<small>${r.nuevos} primeras veces</small></td><td>${n(r.exceso)}</td><td>${r.repetidos}</td></tr>`);
    out('productos-pie',`${rs.length} de ${D.tabla.length} productos · ${sol(REQ.sum(rs,'valor'))} en el rango. Frecuencia, habitual y marcas: 12 meses calendario (${esc(P.desde)} a ${esc(P.hasta)}, fin excluido). Cantidades por producto y unidad.`);
    ficha();guardar();
  }
  function grafico(ms){
    const w=780,h=210,x0=50,y0=22,bottom=170,min=Math.min(0,...ms.flatMap(r=>[r.ped,r.sal,r.parte])),max=Math.max(1,...ms.flatMap(r=>[r.ped,r.sal]));
    const y=v=>bottom-(v-min)/(max-min)*(bottom-y0),base=y(0),ancho=(w-x0-15)/ms.length;
    const rect=(m,start,val,col)=>`<rect x="${x0+m*ancho+8}" y="${Math.min(y(start),y(start+val))}" width="${ancho-16}" height="${Math.max(0,Math.abs(y(start)-y(start+val)))}" fill="${col}"/>`;
    return`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Pedido y salida registrados por mes"><path d="M${x0} ${base}H${w}" stroke="var(--border)"/>${[min,0,max].map(v=>`<text x="45" y="${y(v)+4}" text-anchor="end">${n(v,0)}</text>`).join('')}${ms.map((r,m)=>`<g data-a="mes" data-v="${m}" tabindex="0" role="button" aria-label="Filtrar pedidos de ${r.mes}"><title>${r.mes}: pedido ${n(r.ped)}${P.kardex_disponible?', salió '+n(r.sal)+', ajuste '+n(r.aj):'; salida no disponible'}</title><rect x="${x0+m*ancho}" y="0" width="${ancho}" height="${h}" fill="${s.mes===m?'var(--accent-tint)':'transparent'}"/>${rect(m,0,r.parte,'var(--accent)')}${rect(m,r.parte,r.resto,'var(--rqa-claro)')}${P.kardex_disponible&&r.sal>r.ped?`<circle cx="${x0+(m+.5)*ancho}" cy="${y(r.sal)}" r="4" fill="white" stroke="var(--accent)"/>`:''}<text x="${x0+(m+.5)*ancho}" y="190" text-anchor="middle">${r.mes.slice(2)}</text></g>`).join('')}</svg>`;
  }
  function ficha(){
    const i=P.productos.findIndex(p=>p[0]===s.cod);F=i<0?null:REQ.ficha(B,D,i);const panel=$('[data-panel=ficha]');
    if(!F){panel.innerHTML='<p>Elegí un producto de la tabla.</p>';pedidos();return;}
    const p=F.producto,mx=Math.max(1,...F.semanas.map(Math.abs));
    panel.innerHTML=`<h3>${esc(p.prod)} <small>${esc(p.cod)} · ${esc(p.unid)}</small></h3><div class="rqa-cifras"><div><small>Pedido · 12 meses</small><b>${sol(p.ped_vent)}</b><span>${n(REQ.sum(F.ls,'cant'))} ${esc(p.unid)} · ${F.documentos} requerimientos</span></div><div><small>Salió registrado</small><b>${p.no_descarga?'No descarga':por(p.salio)}</b><span>${!P.kardex_disponible?'Kardex no disponible':p.salio==null?'Sin cobertura del área':'Ponderado por valor pedido en cada área'}</span></div><div><small>Frecuencia</small><b>${esc(p.grupo)}</b><span>${p.dias} días · típico ${n(p.tipico)} ${esc(p.unid)}</span></div><div><small>Fuera de lo habitual</small><b>${p.fuera} veces</b><span>${sol(p.exceso)} de exceso · ${p.nuevos} primeras veces</span></div><div><small>Repetido en el día</small><b>${p.repetidos}</b><span>Siempre por fecha de registro</span></div></div>
      <div class="rqa-ficha-grid"><div><p class="rqa-ayuda">Pedido por mes, en ${esc(p.unid)} · ${P.kardex_disponible?"oscuro: salió registrado · punto: salió más de lo pedido.":"Kardex no disponible: sólo lo pedido."} Clic para filtrar sus pedidos.</p><div class="rqa-curva">${grafico(F.ms)}</div><div class="rqa-wrap rqa-meses"><table><thead><tr><th>Mes</th><th>Pedido</th><th>Salió registrado</th><th>Ajuste</th></tr></thead><tbody>${F.ms.map(r=>`<tr><td>${r.mes}</td><td>${n(r.ped)}</td><td>${P.kardex_disponible?n(r.sal):'—'}</td><td>${P.kardex_disponible?(r.aj>0?'−':r.aj<0?'+':'')+n(Math.abs(r.aj)):'—'}</td></tr>`).join('')}</tbody></table></div></div>
      <div><h4>Por dónde salió · 12 meses</h4>${[['Ventas (recetas)','ven'],['Producción y porcionamiento','pro'],['Notas de salida','nts'],['Transferido a otra área','tra'],['Ajuste del cierre','aj']].map(([lab,k])=>`<p class="rqa-via"><span>${lab}</span><b>${P.kardex_disponible?n(k==='tra'?Math.max(0,REQ.sum(F.ms,k)):REQ.sum(F.ms,k)):'—'} ${esc(p.unid)}</b></p>`).join('')}<p class="rqa-ayuda">Un ajuste positivo es faltante del cierre; uno negativo es sobrante. No se suma como salida registrada.</p><h4>Semanas con pedido</h4><div class="rqa-semanas">${F.semanas.map((q,j)=>{const d=new Date(Date.parse(P.desde+'T00:00:00Z')+j*6048e5).toISOString().slice(0,10);return`<button type="button" data-a="semana" data-v="${j}" aria-pressed="${s.semana===j}" title="Desde ${d}: ${n(q)} ${esc(p.unid)}" style="opacity:${q?.3+.7*Math.abs(q)/mx:.15}"></button>`;}).join('')}</div><p class="rqa-ayuda">Mediana por línea de pedido; cada casillero son 7 días desde el inicio de la ventana. El habitual mira los 90 días anteriores al registro.</p></div></div>`;
    pedidos();
  }
  function pedidosVisibles(){if(!F)return[];return F.ls.filter(r=>(s.mes==null||r.fecha.slice(0,7)===P.meses[s.mes])&&(s.semana==null||Math.max(0,Math.min(52,Math.floor((Date.parse(r.fecha.slice(0,10)+'T00:00:00Z')-Date.parse(P.desde+'T00:00:00Z'))/6048e5)))===s.semana)&&(!s.dq||(P.docs[r.doc]+' '+P.areas[r.area]).toLowerCase().includes(s.dq.toLowerCase()))).sort((a,b)=>b.fecha.localeCompare(a.fecha));}
  function pedidos(){const rs=pedidosVisibles();out('tramo',s.mes!=null?esc(P.meses[s.mes]):s.semana!=null?'Semana '+(s.semana+1):'Ventana completa');
    tabla('pedidos',rs,r=>`<tr data-a="documento" data-v="${r.doc}" tabindex="0"><td>${esc(r.fecha.replace('T',' '))}</td><td>${esc(P.docs[r.doc])}</td><td>${esc(P.areas[r.area])}</td><td>${n(r.cant)} ${esc(F?.producto.unid)}</td><td>${n(r.valor)}</td><td>${esc(marca(r))}</td></tr>`);out('pedidos-pie',`${rs.length} líneas · ${new Set(rs.map(r=>r.doc)).size} documentos · ${sol(REQ.sum(rs,'valor'))}. Clic en un documento para consultar sus otras líneas.`);}
  function documento(i){s.doc=i;const ls=B.V.filter(r=>r.doc===i),dlg=$('dialog');out('doc-titulo','Requerimiento '+esc(P.docs[i]));
    tabla('documento',ls,r=>`<tr><td>${esc(P.productos[r.i][1])}<small>${esc(P.productos[r.i][0])}</small></td><td>${esc(P.areas[r.area])}</td><td>${esc(r.fecha.replace('T',' '))}</td><td>${n(r.cant)}</td><td>${esc(P.productos[r.i][2])}</td><td>${n(r.valor)}</td><td>${esc(marca(r))}</td></tr>`);dlg.showModal();dlg.querySelector('[data-a=cerrar]').focus();}
  function exportar(){
    const hs=[],hoja=(nombre,cabeza,filas)=>hs.push({nombre,cabeza,filas,decimales:6}),base=r=>[r.cod,r.prod,r.unid,r.valor,r.pct,r.cant,r.punit,r.ped_vent,r.dias,r.grupo,r.tipico,r.salio,r.sin_salida,r.no_descarga?'Sí':'No',r.fuera,r.exceso,r.nuevos,r.repetidos];
    const cab=['Código','Producto','Unidad','Pedido rango S/','% recorte','Cantidad rango','Precio unidad rango','Pedido ventana S/','Días con pedido','Frecuencia','Pedido típico','Salió fracción','Sin salida S/','Área sin descarga','Fuera de habitual','Exceso S/','Primera vez','Repetidos'];
    hoja('Productos visibles',cab,(D.ordenados||D.visibles).map(base));hoja('Productos recorte',cab,D.tabla.map(base));
    hoja('Meses del producto',['Código','Producto','Unidad','Mes','Pedido','Valor pedido','Ventas','Producción','Notas','Transferencia','Ajuste','Salió registrado'],F?F.ms.map(r=>[s.cod,F.producto.prod,F.producto.unid,r.mes,r.ped,r.valor,...['ven','pro','nts','tra','aj','sal'].map(k=>P.kardex_disponible?r[k]:null)]):[]);
    const cabLin=['Código','Producto','Unidad','Área','Familia','Subfamilia','Documento','Fecha','Cantidad','S/','Habitual','Veces habitual','Exceso S/','Primera vez','Minutos repetido'];
    const linea=r=>[...P.productos[r.i],P.areas[r.area],P.familias[r.fam],P.subfamilias[r.subfam],P.docs[r.doc],r.fecha,r.cant,r.valor,r.habitual,r.veces,r.exceso,r.nuevo?'Sí':'No',r.repite_min];
    hoja('Pedidos producto',cabLin,pedidosVisibles().map(linea));hoja('Fuente rango',cabLin,B.L.map(linea));hoja('Fuente ventana',cabLin,B.V.map(linea));
    hoja('Kardex de referencia',['Código','Producto','Unidad','Área','Mes','Pedido kardex','Ventas','Producción','Notas','Transferencia','Ajuste'],P.kardex.map(r=>[...P.productos[r[0]],P.areas[r[1]],P.meses[r[2]],...r.slice(3)]));
    hoja('Contexto',['Concepto','Valor'],[['Desde rango incluido',P.rango_desde],['Hasta rango excluido',P.rango_hasta],['Desde ventana incluido',P.desde],['Hasta ventana excluido',P.hasta],['Área',P.areas[s.area]??'Todas'],['Familia',P.familias[s.fam]??'Todas'],['Subfamilia',P.subfamilias[s.subfam]??'Todas'],['Grupo',s.grupo||'Todos'],['Salió menos de mitad',s.poco?'Sí':'No'],['Marca',s.marca||'Todas'],['Búsqueda',s.q],['Producto',s.cod||''],['Mes pedidos',s.mes==null?'Todos':P.meses[s.mes]],['Semana pedidos',s.semana==null?'Todas':s.semana+1],['Búsqueda de pedidos',s.dq],['Kardex disponible',P.kardex_disponible?'Sí':'No'],['Página',JSON.stringify(P.contexto)],['Excluidos',P.nota[1]||''],['Ventana','Doce meses calendario completos hasta el mes del último día del rango; puede incluir días posteriores al fin del rango.'],['Marcas','Según fecha de registro y 90 días anteriores, aunque la vista use fecha de proceso. No se recalculan contra el rango.'],['Mediana','Cantidad por línea de pedido, no por documento agregado. Frecuencia: días distintos con pedido.'],['Cobertura','Por área: (ventas + producción + notas + transferencia positiva) / pedido; tope superior 1, sin tope inferior. Ponderación por valor pedido; no descarga se distingue de falta de cobertura.'],['Unidades','Unidad actual del kardex, por código. No sumar cantidades de productos o unidades diferentes.'],['Fuentes','Rango y ventana completos de los filtros de página. Fuente ventana y kardex sin recorte por filtros del navegador.'],['Precisión','Valores fuente sin redondeo previo; Excel numérico con seis decimales.']]);return hs;
  }
  root.addEventListener('click',e=>{const a=e.target.closest('[data-a]');if(!a)return;const k=a.dataset.a,v=a.dataset.v;
    if(['area','fam','subfam'].includes(k)){const i=v===''?null:Number(v);s[k]=s[k]===i?null:i;if(k==='area'){s.fam=null;s.subfam=null;}if(k==='fam')s.subfam=null;s.mes=null;s.semana=null;render();}
    else if(k==='grupo'){s.grupo=s.grupo===v?null:v;render();}
    else if(k==='orden'){s.asc=s.orden===v?!s.asc:v==='prod';s.orden=v;render();}
    else if(k==='producto'){s.cod=P.productos[Number(v)][0];s.mes=null;s.semana=null;$$('[data-tabla=productos] tr[data-a]').forEach(tr=>tr.setAttribute('aria-selected',P.productos[Number(tr.dataset.v)][0]===s.cod));ficha();guardar();}
    else if(k==='mes'||k==='semana'){s[k]=s[k]===Number(v)?null:Number(v);s[k==='mes'?'semana':'mes']=null;ficha();}
    else if(k==='limpiar-tramo'){s.mes=null;s.semana=null;ficha();}
    else if(k==='documento')documento(Number(v));else if(k==='cerrar')$('dialog').close();else if(k==='excel')bajar(`requerimientos_area_${P.rango_desde}.xlsx`,libro(exportar()));
    if(['area','fam','subfam','grupo','mes','semana'].includes(k))root.querySelector(`[data-a="${k}"][data-v="${CSS.escape(v)}"]`)?.focus({preventScroll:true});
  },{signal:abort.signal});
  root.addEventListener('keydown',e=>{const el=e.target.closest('[data-a]');if(el&&el.tagName!=='BUTTON'&&['Enter',' '].includes(e.key)){e.preventDefault();el.dispatchEvent(new MouseEvent('click',{bubbles:true}));}},{signal:abort.signal});
  root.addEventListener('input',e=>{const k=e.target.dataset.k;if(k==='q'){s.q=e.target.value;render();}if(k==='dq'){s.dq=e.target.value;pedidos();}},{signal:abort.signal});
  root.addEventListener('change',e=>{const k=e.target.dataset.k;if(k==='poco')s.poco=e.target.checked;if(k==='marca')s.marca=e.target.value;if(k==='poco'||k==='marca')render();},{signal:abort.signal});
  render();const cleanup=()=>{abort.abort();$('dialog')?.close();};window.__reqArea={P,B,s,get D(){return D;},get F(){return F;},render,exportar,cleanup,lotes};return cleanup;
}
