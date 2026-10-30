// El cruce y la moneda ya están resueltos por el modelo canónico de Python.
const SUNATDOCS=(()=>{
  const n=v=>v==null||!Number.isFinite(Number(v))?null:Number(v),sum=(rs,k)=>rs.reduce((a,r)=>a+(n(r[k])??0),0);
  function preparar(P){return{P,filas:P.filas.map(r=>{const x={...r,buscar:[r.Documento,r.Proveedor,r.ruc,r.raw.documento_sistema,r.raw.ruc_sistema,r.Tipo].join(' ').toLocaleLowerCase()},b=importes(x).map(v=>v.brecha).filter(v=>v!=null);x._mayor=b.length?Math.max(...b.map(Math.abs)):null;return x;})};}
  function calcular(B,s){
    const P=B.P,q=(s.q||'').trim().toLocaleLowerCase();
    const censo=B.filas.filter(r=>(!q||r.buscar.includes(q))&&(!s.tipo||r.Tipo===s.tipo)&&(!s.xml||(s.xml==='si'?!!r.XML:!r.XML))&&(!s.brecha||importes(r).some(v=>v.brecha!=null&&Math.abs(v.brecha)>P.tolerancia)));
    const conteos=Object.fromEntries(P.estados.map(e=>[e,censo.filter(r=>r[P.estado_col]===e).length]));
    const soles=Object.fromEntries(P.estados.map(e=>[e,censo.filter(r=>r[P.estado_col]===e).reduce((a,r)=>a+Math.abs(n(r.raw.total_sunat)??n(r.raw.total_sistema)??0),0)]));const visibles=censo.filter(r=>(!s.estado||r[P.estado_col]===s.estado)&&(!s.causa||s.estado!=='Diferencia'||r._ck===s.causa));
    const k=s.orden||'fecha',dir=s.dir==='asc'?1:-1;
    visibles.sort((a,b)=>{const av=a[k],bv=b[k];if(av==null||av==='')return bv==null||bv===''?0:1;if(bv==null||bv==='')return-1;const c=typeof av==='number'&&typeof bv==='number'?av-bv:String(av).localeCompare(String(bv),'es',{numeric:true});return dir*c||a.id.localeCompare(b.id);});
    const sunat=visibles.filter(r=>r.raw.total_sunat!=null),sistema=visibles.filter(r=>r.raw.total_sistema!=null),comparables=visibles.filter(r=>r.brecha!=null);
    return{B,s,censo,conteos,soles,visibles,sunat,sistema,comparables,totales:{sunat:sunat.length?sunat.reduce((a,r)=>a+(n(r.raw.total_sunat)??0),0):null,sistema:sistema.length?sistema.reduce((a,r)=>a+(n(r.raw.total_sistema)??0),0):null,brecha:comparables.length?sum(comparables,'brecha'):null}};
  }
  function importes(r){return['base','igv','total'].map(k=>{const a=n(r.raw[k+'_sunat']),b=n(r.raw[k+'_sistema']);return{campo:k,sunat:a,sistema:b,brecha:a==null||b==null?null:b-a};});}
  return{n,sum,preparar,calcular,importes};
})();
window.__sunatDocumentosDatos=SUNATDOCS;

const ESTADO_TXT={'Solo SUNAT':'Falta cargar',Diferencia:'Con diferencia',Coincide:'Cuadra','Solo sistema':'Sólo en el sistema'};
const ESTADO_ORDEN=['Solo SUNAT','Diferencia','Coincide','Solo sistema'];
const CAUSA_TXT={igv_parejo:'IGV al 18 % parejo',centimos:'Céntimos',igv_adentro:'IGV adentro del neto',reparto:'Otro reparto de base e IGV',tasa:'Otra tasa de IGV',monto:'Monto distinto',otro_doc:'¿Otro documento?',isc:'ISC sin cargar'};
const CAUSA_TONO={ok:'ok',centimos:'gris',fuera:'gris',falta:'ojo',igv_adentro:'ojo',otro_doc:'ojo',isc:'ojo',monto:'ojo',tasa:'ojo',igv_parejo:'lav',reparto:'lav'};

export default function(component){
  const P=component.data;if(!P)return;
  // El montaje chico: trae las líneas de un documento, sin volver a mandar la tabla.
  if(P.parte==='lineas'){if(P.id){(window.__sudLineas=window.__sudLineas||{})[P.id]=P.d;window.__sudRefrescar?.(P.id);}return;}
  const host=component.parentElement,owner=host.ownerDocument;host.__sudComp=component;
  // La misma tabla (una corrida del fragment que trae líneas): no se rehace nada.
  const clave=[P.sello,P.salto,JSON.stringify(P.inicial||{}),P.menos||0].join('|');if(host.__sudClave===clave&&host.querySelector('.sud'))return;host.__sudClave=clave;
  host.__sudCleanup?.();
  let root=host.querySelector('.sud');if(!root){root=owner.createElement('div');root.className='sud';host.append(root);}
  root.style.setProperty('--sud-menos',(P.menos||0)+'px');
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const f=(v,d=2)=>v==null?'—':Number(v).toLocaleString('es-PE',{minimumFractionDigits:d,maximumFractionDigits:d}),f3=v=>v==null?'—':Number(v).toLocaleString('es-PE',{maximumFractionDigits:3}),sol=v=>v==null?'—':'S/ '+f(v),sg=v=>v==null?'—':(v>0?'+':v<0?'−':'')+'S/ '+f(Math.abs(v)),dif=v=>v==null?'—':Math.abs(v)<=.005?'0.00':(v>0?'+':'−')+f(Math.abs(v)),cl=v=>v==null?'':v>P.tolerancia?'sud-pos':v<-P.tolerancia?'sud-neg':'',mil=v=>{const a=Math.abs(v||0);return'S/ '+(a>=1e6?(a/1e6).toFixed(2)+'M':a>=1e3?(a/1e3).toFixed(1)+'k':Math.round(a));};
  let saved={};try{saved=JSON.parse(sessionStorage.getItem('sunat_docs_741')||'{}');}catch{}
  const initial=P.inicial||{},s={estado:'',q:'',tipo:'',xml:'',brecha:false,causa:'',orden:'fecha',dir:'desc',elegido:null,amp:false,lado:false,dtab:'al',...initial,...saved};
  if(saved.eco&&JSON.stringify(saved.eco.estado)!==JSON.stringify(initial.estado))s.estado=initial.estado||'';
  if(saved.salto!=null&&saved.salto!==P.salto){s.estado=initial.estado||'';s.q='';s.tipo='';s.xml='';s.brecha=false;s.causa='';s.elegido=null;s.lado=false;}
  s.eco=initial;s.salto=P.salto;if(!P.estados.includes(s.estado))s.estado='';
  const B=SUNATDOCS.preparar(P);if(!B.filas.some(r=>r.Tipo===s.tipo))s.tipo='';if(!['','si','no'].includes(s.xml))s.xml='';if(!B.filas.some(r=>r.id===s.elegido))s.elegido=null;
  let D,limite=150,timer,seq=0,timerL;
  const save=()=>{try{sessionStorage.setItem('sunat_docs_741',JSON.stringify(s));}catch{}};
  const out=(k,h)=>{const e=root.querySelector(`[data-k="${k}"]`);if(e)e.innerHTML=h;};
  const btn=(a,v,t,extra='')=>`<button type="button" data-a="${a}" data-v="${esc(v)}" ${extra}>${t}</button>`;
  const lineasDe=id=>(window.__sudLineas||{})[id];
  const trigger=(k,v)=>host.__sudComp.setTriggerValue(k,v);
  function pedir(que,id=null){save();const a={que,sello:P.sello,nonce:Date.now()+'-'+(++seq)};if(que==='lote')a.ids=D.visibles.map(r=>r.id);else a.id=id;trigger('accion',a);}
  // Las líneas se piden al elegir, con una pausa: pasar por diez filas con el teclado no son diez consultas.
  function pedirLineas(id){clearTimeout(timerL);if(!id||lineasDe(id))return;timerL=setTimeout(()=>trigger('lineas',{id,sello:P.sello,t:Date.now()+'-'+(++seq)}),150);}
  function recalcular(){D=SUNATDOCS.calcular(B,s);if(!D.visibles.some(r=>r.id===s.elegido)){s.elegido=s.estado==='Diferencia'&&D.visibles.length?D.visibles[0].id:null;s.lado=false;}limite=150;dibujar();save();window.__sunatDocumentos={P,B,s,D};pedirLineas(s.elegido);}
  function importe(r,k,sis){const a=r[k],b=r[sis],doble=s.elegido===r.id&&a!=null&&b!=null&&Math.abs(a-b)>P.tolerancia;return`<span>${f(a)}</span>${doble?`<small title="Importe del sistema">sis. ${f(b)}</small>`:''}${k==='Total'&&s.elegido===r.id&&r._conv?`<small title="Importe en la moneda del papel">${esc(r._conv)}</small>`:''}`;}
  function tabla(){
    const columnas=s.amp?[['fecha','Fecha'],['Documento','Documento'],['Proveedor','Proveedor'],['Tipo','Tipo'],['Base','Base S/'],['IGV','IGV S/'],['Total','Total S/'],['brecha','Brecha total S/'],['D','D'],['XML','XML'],[P.estado_col,'Estado']]:[['fecha','Fecha'],['Documento','Documento'],['Proveedor','Proveedor'],['Total','Total S/'],['_mayor','Mayor dif.'],[P.estado_col,'Estado']];
    const estado=r=>`<span class="sud-est ${r[P.estado_col]==='Solo SUNAT'?'c':r[P.estado_col]==='Diferencia'?'b':r[P.estado_col]==='Coincide'?'a':'e'}">${esc(ESTADO_TXT[r[P.estado_col]]||r[P.estado_col])}</span>`;
    const rows=D.visibles.slice(0,limite).map(r=>`<tr data-id="${esc(r.id)}" tabindex="0" aria-selected="${s.elegido===r.id}" class="${s.elegido===r.id?'sud-elegida':''}"><td class="sud-fecha">${esc(r.Fecha)}</td><td class="sud-documento"><b>${esc(r.Documento)}</b>${r._chips?`<span class="sud-chips">${r._chips.split('|').map(c=>`<i>${esc(c)}</i>`).join('')}</span>`:''}<small class="sud-fecha-movil">${esc(r.Fecha)}</small></td><td class="sud-proveedor" title="${esc(r.Proveedor+' · '+r.ruc)}">${esc(r.Proveedor)}</td>${s.amp?`<td title="${esc(r._tipo_por)}">${esc(r.Tipo)}</td><td>${importe(r,'Base','_base_sis')}</td><td>${importe(r,'IGV','_igv_sis')}</td><td>${importe(r,'Total','_total_sis')}</td><td class="${cl(r.brecha)}" title="Sistema menos SUNAT, sólo con ambas fuentes">${r.brecha==null?'—':sg(r.brecha)}</td><td title="Marca de detracción del registro SUNAT">${esc(r.D)}</td><td title="${r.XML?'XML original disponible':'Sin XML disponible'}">${esc(r.XML)}</td>`:`<td>${f(r.Total)}</td><td title="La mayor diferencia entre base, IGV y total">${r._mayor==null?'—':f(r._mayor)}</td>`}<td class="sud-col-est">${estado(r)}${s.amp&&r.Ingresar?btn('ingreso',r.id,'↓ Ingresar'):''}</td></tr>`).join('');
    const ft=k=>D.sunat.reduce((a,r)=>a+(SUNATDOCS.n(r.raw[k+'_sunat'])??0),0);
    const n=columnas.length;
    return`<div class="sud-wrap" tabindex="0" aria-label="Documentos del cruce"><table><thead><tr>${columnas.map(([k,t])=>`<th class="${k==='fecha'?'sud-fecha':k==='Documento'?'sud-documento':k==='Proveedor'?'sud-proveedor':k===P.estado_col?'sud-col-est':''}">${btn('orden',k,esc(t)+(s.orden===k?(s.dir==='asc'?' ↑':' ↓'):''))}</th>`).join('')}</tr></thead><tbody>${rows||`<tr><td colspan="${n}">No hay documentos con estos filtros.</td></tr>`}</tbody><tfoot><tr>${s.amp?`<th colspan="4">${D.sunat.length} documentos SUNAT · ${D.sistema.length} del sistema</th>${['base','igv','total'].map(k=>`<td title="Suma de SUNAT; los documentos del sistema se muestran por separado">${D.sunat.length?f(ft(k)):'—'}</td>`).join('')}<td class="${cl(D.totales.brecha)}">${sg(D.totales.brecha)}</td><td colspan="3">${D.comparables.length} comparables</td>`:`<th colspan="3">${D.sunat.length} SUNAT · ${D.sistema.length} del sistema</th><td title="Suma de SUNAT">${D.sunat.length?f(ft('total')):'—'}</td><td colspan="2" class="${cl(D.totales.brecha)}" title="Sistema menos SUNAT, sólo con ambas fuentes">${sg(D.totales.brecha)}</td>`}</tr></tfoot></table></div>${D.visibles.length>limite?btn('mas','',`Mostrar 150 más · ${Math.min(limite,D.visibles.length)} de ${D.visibles.length}`,'class="sud-mas-filas"'):''}`;
  }
  function ficha(){
    const r=B.filas.find(x=>x.id===s.elegido);
    if(!r)return`<h3>Elige un documento</h3><div class="sub">Cómo está en SUNAT, cómo está ingresado en el Almacén y qué dice la factura.</div>`;
    const L=lineasDe(r.id),ck=L?L.ck:r._ck,ca=L?L.ca:r._ca,vs=SUNATDOCS.importes(r),hayAl=r.raw.total_sistema!=null,haySu=r.raw.total_sunat!=null;
    const filaCmp=vs.map(v=>`<tr class="${v.brecha!=null&&Math.abs(v.brecha)>P.tolerancia?'si':''}"><td class="i">${{base:'Base',igv:'IGV',total:'Total'}[v.campo]}</td><td>${f(v.sunat)}</td><td>${f(v.sistema)}</td><td class="${v.brecha!=null&&Math.abs(v.brecha)>P.tolerancia?'mal':''}">${dif(v.brecha)}</td></tr>`).join('');
    const pr=[['Tipo de compra',r.Tipo,r._tipo_por],...(hayAl?[['Procesado en el Almacén',L?(L.fp||'—'):'…','']]:[]),['Detracción',r.D?'Sí':'No',''],['Factura electrónica',r.XML?'Bajada':'Sin bajar','']];
    if(r.raw.documento_sistema&&!haySu)pr.push(['En el sistema',r.raw.documento_sistema,'']);
    if(r.raw.proveedor_sistema&&String(r.raw.proveedor_sistema).trim().toLowerCase()!==String(r.Proveedor).trim().toLowerCase())pr.push(['Proveedor en el Almacén',r.raw.proveedor_sistema,'']);
    const tab=!hayAl?'fa':!haySu?'al':s.dtab;
    const tabs=L?`<span class="sud-seg" role="group" aria-label="Líneas">${hayAl?btn('dtab','al',`En el Almacén ${L.la.length}`,`class="${tab==='al'?'on':''}"`):''}${haySu?btn('dtab','fa',`En la factura ${L.lx.length}`,`class="${tab==='fa'?'on':''}"`):''}</span>${L.la.length&&L.lx.length?btn('lado','','Lado a lado ↗','class="sud-quita"'):''}`:'';
    let lineas=`<p class="sud-nota">Trayendo las líneas…</p>`;
    if(L){
      const simb=L.mon==='USD'?'US$':L.mon==='PEN'?'S/':L.mon,ln=(a,b,v)=>`<div class="sud-ln"><span title="${esc(a)}">${esc(a)}<small>${esc(b)}</small></span><b>${esc(v)}</b></div>`;
      const sumaA=L.la.reduce((x,l)=>x+(l[4]||0),0),sumaX=L.lx.reduce((x,l)=>x+(l[4]||0),0);
      if(tab==='al')lineas=L.la.length?L.la.map(l=>ln(l[0],f3(l[1])+' '+String(l[2]).toLowerCase()+' · S/ '+f(l[3]),f(l[4]))).join('')+`<div class="sud-ln tot"><span>Suma de sus líneas<small>${Math.abs(sumaA-(r.raw.base_sistema||0))<=.05?'Es el neto del Almacén':'El neto del Almacén es S/ '+f(r.raw.base_sistema)}</small></span><b>S/ ${f(sumaA)}</b></div>`:`<p class="sud-nota">Este documento no tiene líneas en el Almacén.</p>`;
      else lineas=L.lx.length?L.lx.map(l=>ln(l[0],f3(l[1])+' '+l[2]+' · '+simb+' '+f(l[3])+' · IGV '+f(l[5])+(l[6]?' · ISC '+f(l[6]):''),f(l[4]))).join('')+`<div class="sud-ln tot"><span>Suma de sus líneas<small>${Math.abs(sumaX*(L.tc||1)-(r.raw.base_sunat||0))<=.05?'Es la base de SUNAT':'La base de SUNAT es S/ '+f(r.raw.base_sunat)}</small></span><b>${simb} ${f(sumaX)}</b></div>`:`<p class="sud-nota">Todavía no se bajó su factura electrónica: se pide con «Traer XML…».</p>`;
    }
    return`<h3>${esc(r.Documento)}</h3><div class="sub">${esc(r.Proveedor)} · ${esc(r.ruc)} · ${esc(r.Fecha)}</div>
      <div class="sud-causa ${CAUSA_TONO[ck]||'gris'}">${esc(ca)}</div>
      <table class="sud-cmp"><thead><tr><th></th><th>SUNAT</th><th>Almacén</th><th>Dif.</th></tr></thead><tbody>${filaCmp}</tbody></table>
      ${r._conv?`<p class="sud-nota">Moneda del papel: ${esc(r._conv)}. La comparación ya está en soles.</p>`:''}
      ${pr.map(([a,b,t])=>`<div class="sud-pr" title="${esc(t)}"><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join('')}
      <div class="sud-fl">${tabs}</div>${lineas}
      ${r.Ingresar?btn('ingreso',r.id,'↓ Ingresar al Almacén','class="sud-ir prim"'):''}${r._car?btn('ficha',r.id,'Ver el comprobante','class="sud-ir"'):''}`;
  }
  function ladoALado(){
    const r=B.filas.find(x=>x.id===s.elegido),L=r&&lineasDe(r.id);if(!L)return'';
    const tc=L.tc||1,usados=new Set(L.pa.filter(j=>j!=null)),celdaX=x=>`<td class="i tr" title="${esc(x[0])}">${esc(x[0])}</td><td>${f3(x[1])}</td><td class="i">${esc(x[2])}</td><td>${f(x[4])}</td><td>${f(x[5])}</td>`,vacioX='<td class="i tr"></td><td></td><td class="i"></td><td></td><td></td>',celdaA=a=>`<td class="i tr sep" title="${esc(a[0])}">${esc(a[0])}</td><td>${f3(a[1])}</td><td class="i">${esc(String(a[2]).toLowerCase())}</td><td>${f(a[4])}</td>`,vacioA='<td class="i tr sep"></td><td></td><td class="i"></td><td></td>';
    const filas=L.lx.map((x,i)=>{const j=L.pa[i],a=j==null?null:L.la[j];let d='sin par',c='gris';if(a){const imp=(x[4]||0)*tc,conI=imp+(x[5]||0)*tc,di=(a[4]||0)-imp;if(Math.abs(di)<=.05)d='—';else if(Math.abs((a[4]||0)-conI)<=.05){d='con IGV';c='mal';}else{d=dif(di);c='mal';}}return`<tr>${celdaX(x)}${a?celdaA(a):vacioA}<td class="sep ${c}">${d}</td></tr>`;});
    L.la.forEach((a,j)=>{if(!usados.has(j))filas.push(`<tr>${vacioX}${celdaA(a)}<td class="sep gris">sin par</td></tr>`);});
    const sumaA=L.la.reduce((x,l)=>x+(l[4]||0),0),sumaX=L.lx.reduce((x,l)=>x+(l[4]||0),0),sumaI=L.lx.reduce((x,l)=>x+(l[5]||0),0);
    return`<div class="sud-lado"><div class="sud-fl">${btn('nolado','','← Volver a la lista','class="sud-amp"')}<b>${esc(r.Documento)}</b><span class="sud-nota">${esc(r.Proveedor)} · ${esc(r.Fecha)}</span></div>
      <div class="sud-causa ${CAUSA_TONO[L.ck]||'gris'}">${esc(L.ca)}</div>
      <div class="sud-wrap"><table><thead><tr><th class="i">En la factura</th><th>Cant.</th><th class="i">Und.</th><th>Importe ${L.mon==='USD'?'US$':'S/'}</th><th>IGV</th><th class="i sep">En el Almacén</th><th>Cant.</th><th class="i">Und.</th><th>Neto S/</th><th class="sep">Diferencia</th></tr></thead><tbody>${filas.join('')}<tr class="tot"><td class="i">Suma</td><td></td><td></td><td>${f(sumaX)}</td><td>${f(sumaI)}</td><td class="i sep">Suma</td><td></td><td></td><td>${f(sumaA)}</td><td class="sep ${Math.abs(sumaA-sumaX*tc)>.05?'mal':''}">${dif(sumaA-sumaX*tc)}</td></tr></tbody></table></div>
      <p class="sud-nota">Los pares los busca la app por nombre, cantidad e importe. Una línea del Almacén puede juntar varias de la factura: «sin par» no significa que falte. La cantidad puede cambiar de unidad (botellas a litros).</p></div>`;
  }
  function dibujar(){
    const tipos=[...new Set(B.filas.map(r=>r.Tipo))].sort(),chips=[['','Todos',D.censo.length,''],...ESTADO_ORDEN.filter(e=>P.estados.includes(e)).map(e=>[e,ESTADO_TXT[e],D.conteos[e],mil(D.soles[e])])];
    const causas={};if(s.estado==='Diferencia')D.censo.filter(r=>r[P.estado_col]==='Diferencia').forEach(r=>{causas[r._ck]=(causas[r._ck]||0)+1;});
    const selCausa=s.estado==='Diferencia'?`<label class="sud-lb">Causa probable<select data-k="causa"><option value="">Todas (${D.conteos.Diferencia})</option>${Object.keys(causas).sort((a,b)=>causas[b]-causas[a]).map(k=>`<option value="${esc(k)}" ${s.causa===k?'selected':''}>${esc(CAUSA_TXT[k]||k)} (${causas[k]})</option>`).join('')}</select></label>`:'';
    const activos=(s.tipo?1:0)+(s.xml?1:0)+(s.brecha?1:0);
    const cuerpo=s.lado&&lineasDe(s.elegido)?ladoALado():`<div class="sud-cuerpo"><div class="sud-izq"><div data-k="tabla">${tabla()}</div><div class="sud-fl sud-pie"><span class="sud-nota"><b>${D.visibles.length} de ${D.censo.length}</b> · SUNAT ${sol(D.totales.sunat)} · Sistema ${sol(D.totales.sistema)}</span><span class="sud-esp"></span>${btn('excel','','↓ Excel del recorte','class="sud-pil"')}${btn('lote','','Traer XML…',`class="sud-pil" ${D.visibles.length?'':'disabled'}`)}${btn('amp','',s.amp?'Volver':'Ampliar','class="sud-amp"')}</div></div>${s.amp?'':`<div class="sud-panel" data-k="ficha">${ficha()}</div>`}</div>`;
    root.innerHTML=`<div class="sud-estados" role="group" aria-label="Estado">${chips.map(([k,n,c,x])=>`<button type="button" class="sud-chip${s.estado===k?' on':''}" data-a="estado" data-v="${esc(k)}" aria-pressed="${s.estado===k}">${esc(n)} <b>${c}</b><small>${esc(x)}</small></button>`).join('')}</div>
      <div class="sud-controles"><input type="search" data-k="q" aria-label="Buscar documento, proveedor o RUC" placeholder="Documento, proveedor, RUC…" value="${esc(s.q)}">${selCausa}<label class="sud-lb">Tipo de compra<select data-k="tipo"><option value="">Todos</option>${tipos.map(t=>`<option value="${esc(t)}" ${s.tipo===t?'selected':''}>${esc(t)}</option>`).join('')}</select></label><label class="sud-lb">XML<select data-k="xml"><option value="">Todos</option><option value="si" ${s.xml==='si'?'selected':''}>Disponible</option><option value="no" ${s.xml==='no'?'selected':''}>Sin XML</option></select></label><label class="sud-check"><input type="checkbox" data-k="brecha" ${s.brecha?'checked':''}>Con brecha</label></div>${cuerpo}`;
  }
  function excel(){const headers=['Fecha','Documento','Proveedor','RUC','Tipo','Base S/','IGV S/','Total S/','Base sistema S/','IGV sistema S/','Total sistema S/','Brecha total S/','Mayor diferencia S/','Moneda del papel','Detracción','XML','Estado','Causa probable'];const fila=r=>[r.Fecha,r.Documento,r.Proveedor,r.ruc,r.Tipo,r.Base,r.IGV,r.Total,r._base_sis,r._igv_sis,r._total_sis,r.brecha,r._mayor,r._conv,r.D,r.XML,r[P.estado_col],r._ca];const keys=[...new Set(P.filas.flatMap(r=>Object.keys(r.raw)))],sk=[...new Set(P.sire.flatMap(r=>Object.keys(r)))];const contexto=Object.entries({...P.contexto,'Búsqueda':s.q,'Estado local':s.estado||'Todos','Causa local':s.causa||'Todas','Tipo local':s.tipo||'Todos','XML local':s.xml||'Todos','Sólo con brecha':s.brecha?'Sí':'No','Alcance del censo':'Búsqueda, tipo y XML se aplican antes del conteo de estados.','Brecha':'Sistema menos SUNAT, sólo si ambas fuentes tienen importe.','Totales':'SUNAT y sistema se suman por separado; no se suman entre sí.','Precisión':'Los números se exportan con seis decimales.'});const r=B.filas.find(r=>r.id===s.elegido);bajar('sunat_documentos.xlsx',libro([{nombre:'Documentos del recorte',cabeza:headers,filas:D.visibles.map(fila),decimales:6},{nombre:'Comparación de importes',cabeza:['Documento','Proveedor','RUC','Campo','SUNAT soles','Sistema soles','Brecha soles'],filas:D.visibles.flatMap(r=>SUNATDOCS.importes(r).map(v=>[r.Documento,r.Proveedor,r.ruc,v.campo,v.sunat,v.sistema,v.brecha])),decimales:6},{nombre:'Cruce de la página',cabeza:keys,filas:P.filas.map(r=>keys.map(k=>r.raw[k])),decimales:6},{nombre:'Registro SUNAT de página',cabeza:sk,filas:P.sire.map(r=>sk.map(k=>r[k])),decimales:6},{nombre:'Documento elegido',cabeza:headers,filas:r?[fila(r)]:[],decimales:6},{nombre:'Contexto',cabeza:['Concepto','Valor'],filas:contexto}]));}
  function elegir(id){const w=root.querySelector('.sud-wrap'),top=w.scrollTop,left=w.scrollLeft;s.elegido=id;out('tabla',tabla());out('ficha',ficha());const nw=root.querySelector('.sud-wrap');nw.scrollTop=top;nw.scrollLeft=left;save();pedirLineas(id);}
  window.__sudRefrescar=id=>{if(s.elegido===id&&root.isConnected){if(s.lado)dibujar();else out('ficha',ficha());}};
  const click=e=>{const b=e.target.closest('[data-a]');if(b){const a=b.dataset.a,v=b.dataset.v;if(a==='orden'){s.dir=s.orden===v&&s.dir==='desc'?'asc':'desc';s.orden=v;recalcular();}else if(a==='estado'){s.estado=v;s.causa='';s.elegido=null;recalcular();}else if(a==='mas'){const w=root.querySelector('.sud-wrap'),top=w.scrollTop,left=w.scrollLeft;limite+=150;out('tabla',tabla());const nw=root.querySelector('.sud-wrap');nw.scrollTop=top;nw.scrollLeft=left;}else if(a==='ficha'||a==='ingreso'){s.elegido=v;save();pedir(a,v);}else if(a==='lote')pedir('lote');else if(a==='excel')excel();else if(a==='amp'){s.amp=!s.amp;dibujar();save();}else if(a==='dtab'){s.dtab=v;out('ficha',ficha());save();}else if(a==='lado'){s.lado=true;dibujar();save();}else if(a==='nolado'){s.lado=false;dibujar();save();}return;}const tr=e.target.closest('tbody tr[data-id]');if(tr)elegir(tr.dataset.id);};
  const change=e=>{const k=e.target.dataset.k;if(!k||k==='q')return;s[k]=e.target.type==='checkbox'?e.target.checked:e.target.value;recalcular();};
  const input=e=>{if(e.target.dataset.k!=='q')return;s.q=e.target.value;const pos=e.target.selectionStart;clearTimeout(timer);timer=setTimeout(()=>{recalcular();const q=root.querySelector('[data-k=q]');q.focus();try{q.setSelectionRange(pos,pos);}catch{}},100);};
  const keydown=e=>{if(e.key==='Enter'&&e.target.matches('tr[data-id]'))elegir(e.target.dataset.id);};
  root.addEventListener('click',click);root.addEventListener('change',change);root.addEventListener('input',input);root.addEventListener('keydown',keydown);
  host.__sudCleanup=()=>{clearTimeout(timer);clearTimeout(timerL);root.removeEventListener('click',click);root.removeEventListener('change',change);root.removeEventListener('input',input);root.removeEventListener('keydown',keydown);};recalcular();
}
