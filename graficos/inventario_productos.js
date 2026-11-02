// Interfaz de Stock por Producto (#721): una pantalla, lista con niveles y ficha al costado (#765).
// inventario_base.js se antepone en Python (#724).
const setiqueta={neg:'Negativo',sin:'Sin consumo',alto:'Más de 60 días','':''};
const sestadoNom={todos:'Todos',neg:'En negativo',sin:'Sin consumo',alto:'Más de 60 días',A:'Clase A',areaNeg:'Con un área negativa'};
function sinicial(P){const tope=P.rango?.[1]||'',fecha=tope?new Date(Date.parse(tope+'T00:00:00Z')-864e5*(+tope.slice(8))).toISOString().slice(0,10):'';
  return {areas:[...P.areas_iniciales],fams:[],subs:[],q:'',sin:false,salida:false,chip:'todos',clase:'todos',af:false,fecha:fecha<P.rango?.[0]?P.rango[0]:fecha,hora:23,comparar:false,
    abiertos:[],foco:null,grupo:null,focoArea:null,tab:'areas',objetivo:30,limite:150,orden:[],prof:'Subfamilia',ab:{},amp:false,ref:Math.max(0,(P.meses?.length||0)-3),...P.inicial};}
const sb=(act,v,txt,on=false,tip='',cls='')=>`<button type="button" data-act="${act}" data-v="${se(v)}" class="${on?'on':''} ${cls}" title="${se(tip)}" aria-pressed="${on}">${se(txt)}</button>`;
const stoggle=(key,txt,val)=>`<label><input type="checkbox" data-toggle="${key}" ${val?'checked':''}><span>${se(txt)}</span></label>`;
const SICO_AMP='<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4"/></svg>',SICO_VOL='<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 2v4H2M14 6h-4V2M10 14v-4h4M2 10h4v4"/></svg>';
const samp=(st,cual,rot)=>`<button type="button" class="ist-amp" data-act="amp" data-v="${cual}" aria-pressed="${st.amp===cual}" title="${st.amp===cual?'Volver (Esc)':`Ampliar ${rot}`}" aria-label="${st.amp===cual?'Volver':`Ampliar ${rot}`}">${st.amp===cual?SICO_VOL:SICO_AMP}</button>`;
const sleerLS=(k,d)=>{try{const v=localStorage.getItem(k);return v==null?d:JSON.parse(v);}catch(e){return d;}},sguardarLS=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v));}catch(e){/* sólo esta vez */}};
// A la derecha del nivel 2 (el renglón de «Ver», de Python): «Detalle» y «Cómo se calcula» (#796).
function sn2der(G){const st=G.st;return `<label class="ist-switch"><input type="checkbox" data-toggle="det" role="switch"${st.det?' checked':''}>Detalle</label><span class="ist-como"><button type="button" class="ist-link" data-act="como" aria-expanded="${!!st.como}">Cómo se calcula</button>${st.como?`<div class="ist-pop-como" role="dialog"><p>El stock que el POS da por activo: área activa, producto activo, habilitado en el área y de mercadería.</p><dl>`
  +'<dt>Valorizado</dt><dd>Cantidad × el precio de cada área. «Por producto» cuenta las áreas elegidas; «Por área» las cuenta todas.</dd>'
  +'<dt>Sin consumo en 90 días</dt><dd>Lo que no salió en 90 días. Los insumos de operación (menaje, limpieza, leña) van aparte: ninguna receta los descarga.</dd>'
  +'<dt>Días de stock</dt><dd>La cantidad ÷ el consumo diario de los últimos 90 días, del restaurante entero.</dd>'
  +'<dt>ABC</dt><dd>A: los que suman el 80 % del valorizado; B, el 15 % siguiente; C, el resto.</dd>'
  +'<dt>A una fecha</dt><dd>La foto sale del kardex: el último movimiento por correlativo, con el precio del área.</dd></dl><p>Es un cálculo propio, no un estándar.</p></div>':''}</span>`;}
const ssegm=(act,ops,val)=>`<span class="ist-seg" role="group">${ops.map(([v,t])=>sb(act,v,t,val===v)).join('')}</span>`;
const sopcion=(key,G,v,suma)=>`<label><input type="checkbox" data-filter="${key}" value="${se(v)}" ${G.st[key].includes(v)?'checked':''}><span>${se(key==='areas'?v:slabel(G,key==='fams'?'fam':'sub',v))}</span><small>${se(ss(suma,0))}</small></label>`;
function ssumas(rows,k){const m=new Map();for(const r of rows)if(r[k])m.set(r[k],(m.get(r[k])||0)+r.v);return [...m.entries()].sort((a,b)=>b[1]-a[1]);}
function scab(G,D){const st=G.st,P=G.B.P,rows=G.B.rows,ini=P.areas_iniciales;
  const iguales=st.areas.length===ini.length&&st.areas.every(a=>ini.includes(a));
  const aTxt=!st.areas.length?'todas':iguales?`${ini.length} principales`:st.areas.length===1?st.areas[0]:String(st.areas.length);
  const areas=ssumas(rows,'area');
  const fams=ssumas(rows.filter(r=>!st.areas.length||st.areas.includes(r.area)),'fam');
  const subs=st.fams.length?ssumas(rows.filter(r=>(!st.areas.length||st.areas.includes(r.area))&&st.fams.includes(r.fam)),'sub'):[];
  const fTxt=st.subs.length?`${st.subs.length} ${st.subs.length===1?'subfamilia':'subfamilias'}`:st.fams.length===1?slabel(G,'fam',st.fams[0]):st.fams.length?`${st.fams.length} familias`:'Todas las familias';
  const horas=Array.from({length:24},(_,i)=>`<option value="${i}" ${i===st.hora?'selected':''}>${String(i).padStart(2,'0')}:59</option>`).join('');
  const fecha=P.hay_fecha?`<details class="ist-filtro ${st.af?'act':''}" data-menu="fecha"><summary>${se(st.af?`Stock al ${stituloFecha(st)}`:'Stock de hoy')}</summary><div class="ist-menu">${stoggle('af','Ver a una fecha',st.af)}${st.af?`<div class="cmp"><input type="date" data-change="fecha" value="${se(st.fecha)}" min="${P.rango?.[0]||''}" max="${P.rango?.[1]||''}" aria-label="Fecha de stock"><select data-change="hora" aria-label="Hora de stock">${horas}</select></div>${stoggle('comparar','Comparar con hoy',st.comparar)}${D.photo&&!D.photo.comparar&&st.comparar?'<p>Hoy no disponible: comparación desactivada.</p>':''}`:''}<p>La foto es la del kardex a esa hora; los datos maestros y los activos, los de hoy.</p></div></details>`:'';
  return `<details class="ist-filtro ${iguales?'':'act'}" data-menu="areas"><summary>Áreas: ${se(aTxt)}</summary><div class="ist-menu"><div class="fbt">${sb('todos','areas','Todas',false,'','ist-mini-btn')}${sb('principales','areas','Las principales',false,'','ist-mini-btn')}</div><input type="search" placeholder="Buscar en la lista…" data-lista="areas" aria-label="Buscar áreas">${areas.map(([v,s])=>sopcion('areas',G,v,s)).join('')}<p>Sin ninguna marcada entran todas.</p></div></details>
    <details class="ist-filtro ${st.fams.length||st.subs.length?'act':''}" data-menu="fams"><summary>${se(fTxt)}</summary><div class="ist-menu"><div class="fbt">${sb('todos','fams','Todas',false,'','ist-mini-btn')}</div><h4>Familias</h4>${fams.map(([v,s])=>sopcion('fams',G,v,s)).join('')}${subs.length?`<h4>Subfamilias</h4>${subs.map(([v,s])=>sopcion('subs',G,v,s)).join('')}`:''}<p>Sin ninguna marcada entran todas.</p></div></details>
    ${fecha}<input type="search" class="ist-busca isp-search" data-input="q" value="${se(st.q)}" placeholder="Buscar producto o código…" aria-label="Buscar producto o código">
    <details class="ist-filtro" data-menu="mas"><summary>Más</summary><div class="ist-menu der">${stoggle('sin',`Ver sin stock${D.sin?` (${sn(D.sin)})`:''}`,st.sin)}${P.hay_salida?stoggle('salida','Ver en unidad de salida',st.salida):''}<p>El área cambia las cantidades y el valor. El ABC se calcula antes de buscar.</p></div></details>
    ${sb('excel','lista','Excel ↓',false,'Baja todas las filas de lo filtrado','ist-pil')}`;
}
function skpis(G,D){const st=G.st,P=G.B.P,n=P.meses.length;if(D.pending||D.error||!D.stock)return skpiBtn({attrs:'disabled',rot:'Valorizado',val:'—',dis:true});
  const nA=st.areas.length?`${st.areas.length} ${st.areas.length===1?'área':'áreas'}`:'todas las áreas',suma=rs=>ssum(rs,'v');
  if(!D.analisis){const cmp=st.af&&st.comparar&&D.photo?.comparar,rs=D.visibles;
    return skpiBtn({attrs:'disabled',rot:`Valorizado · ${nA}`,val:ss(suma(rs),0),sub:`${sn(rs.length)} productos${st.af?` · ${stituloFecha(st)}`:''}`,dis:true})+(cmp?skpiBtn({attrs:'disabled',rot:'Valor hoy',val:ss(ssum(rs,'vh'),0),dis:true})+skpiBtn({attrs:'disabled',rot:'Δ valor',val:sd0(ssum(rs,'vh')-suma(rs)),dis:true}):'');}
  const de=k=>D.stock.filter(r=>r.estado===k),oper=rs=>suma(rs.filter(r=>soperacion(r,P)));
  const conOper=rs=>`${sn(rs.length)} productos${oper(rs)>.5?` · ${ss(oper(rs),0)} son de operación`:''}`;
  const pick=k=>`data-act="chip" data-v="${k}"`,kp=(k,o)=>skpiBtn({attrs:pick(k),on:st.chip===k,...o});
  return kp('todos',{rot:`Valorizado · ${nA}`,val:ss(suma(D.stock),0),sub:`${sn(D.stock.length)} productos · ${sdiasTxt(sdiasConjunto(D.stock,P.ventana))} días de inventario`,h:sserie(D.stock,n),tip:'Stock con el precio de cada área. Días: stock positivo ÷ consumo diario en soles del restaurante entero.'})
    +kp('sin',{rot:'Sin consumo en 90 días',val:ss(suma(de('sin')),0),sub:conOper(de('sin')),h:sserie(de('sin'),n),tip:'Hay stock y no salió nada en 90 días. Un clic filtra la lista.'})
    +kp('alto',{rot:`Más de ${P.umbral} días de stock`,val:ss(suma(de('alto')),0),sub:conOper(de('alto')),h:sserie(de('alto'),n),tip:`Al ritmo de los últimos 90 días dura más de ${P.umbral} días. Un clic filtra la lista.`})
    +kp('neg',{rot:'En negativo',val:ss(suma(de('neg')),0),sub:`${sn(D.counts.neg)} productos · ${sn(D.counts.areaNeg)} con algún área negativa`,h:sserie(de('neg'),n),neg:true,tip:'Cantidad total bajo cero. Un clic filtra la lista.'});
}
function ssort(rs,order){if(!order.length)return rs;
  return [...rs].sort((a,b)=>{for(const o of order){let x=a[o.k],y=b[o.k];if(x==null&&y==null)continue;if(x==null)return 1;if(y==null)return -1;
    if(['prod','fam','sub'].includes(o.k)){x=sorden(x);y=sorden(y);}const d=typeof x==='number'?x-y:String(x).localeCompare(String(y));if(d)return o.d*d;}return 0;});
}
// Por valor; en «En negativo», lo más negativo arriba.
const sord=st=>st.orden[0]||{k:'v',d:st.chip==='neg'?1:-1};
function sgrupos(G,rs,k,o){const lab=n=>slabel(G,k==='sub'?'sub':'fam',n);
  return [...sgroup(rs,r=>r[k])].map(([n,g])=>({n,g,v:ssum(g,'v'),dias:sdiasConjunto(g,G.B.P.ventana)})).sort((a,b)=>{
    if(o.k==='prod')return sorden(lab(a.n)).localeCompare(sorden(lab(b.n)))*o.d;
    if(o.k==='dias'){const x=a.dias,y=b.dias;if(x==null||y==null)return x==null?(y==null?0:1):-1;return (x-y)*o.d;}
    return (a.v-b.v)*(o.k==='v'?o.d:-1);});}
function scols(G,D){const st=G.st,cmp=st.af&&st.comparar&&D.photo?.comparar,h=[];
  if(st.det)h.push(['cod','Código','w-c'],['precio','Precio','w-n']);
  h.push(['q',st.af?'A la fecha':'Cantidad','w-q'],['v','Valor S/','w-v']);
  if(cmp)h.push(['qh','Cantidad hoy','w-q'],['vh','Valor hoy','w-v'],['delta','Δ valor','w-v']);
  if(D.analisis){h.push(['pct','%','w-p'],['dias','Días','w-d']);if(st.det)h.push(['consumo','Consumo 90 d','w-u']);h.push(['h',`${G.B.P.meses.length} meses`,'w-t'],['abc','ABC','w-a']);}
  return h;
}
function scelda(G,r,k,tot,area=false){const {P}=G.B,st=G.st,unidad=P.unidades[r.um]||r.um,usal=P.unidades[r.usal]||r.usal;
  if(k==='cod')return area?'':se(r.cod);
  if(k==='precio')return area||r.precio==null?'':se(sn(r.precio,2));
  if(k==='q'||k==='qh')return r.mixed?'—':se(scantidad(r[k],r.factor,unidad,usal,st.salida));
  if(k==='v'||k==='vh')return se(sv0n(r[k]));
  if(k==='delta')return se(sv0n(r.vh-r.v));
  if(k==='pct')return r.v>0&&tot>0?`${sn(r.v/tot*100,r.v/tot<.1?1:0)} %`:'—';
  if(k==='dias')return area?'':r.mixed||r.estado==='neg'?'—':r.estado==='sin'?'sin consumo':sdiasTxt(r.dias);
  if(k==='consumo')return area||r.mixed?'':se(scantidad(r.consumo,r.factor,unidad,usal,st.salida));
  if(k==='h')return `<button data-act="historia" data-v="${se(JSON.stringify([r.cod,area?r.area:null]))}" title="Ver su evolución" aria-label="Ver su evolución">${smini(r.h)}</button>`;
  if(k==='abc')return area?'':r.abc||'—';
  return '';
}
const sv0n=n=>`${n<0&&Math.abs(n)>=.005?'−':''}${sn(Math.abs(n),2)}`;
const sclaseCol=(r,k)=>k==='abc'?`abc ${r.abc||''}`:k==='v'||k==='q'||k==='vh'||k==='qh'||k==='delta'?(((k==='delta'?r.vh-r.v:r[k])<0?'rojo':'')+(k==='v'?' val':'')):k==='dias'&&(r.estado==='sin'||r.estado==='alto')?'nar':k==='h'?'t':'';
function sfilas(G,D,cols){const st=G.st,o=sord(st),tot=D.visibles.reduce((s,r)=>s+Math.max(0,r.v),0),niv={Familia:0,Subfamilia:1,Producto:2}[st.prof],out=[],plana=st.q.trim()||st.prof==='Lista';
  const fProd=(r,ind)=>{const on=st.foco===r.cod,abr=st.abiertos.includes(r.cod),mk=st.det&&r.areas.length?`<button class="ist-mk" data-act="abrir" data-v="${se(r.cod)}" aria-expanded="${abr}" title="Abrir sus áreas">${abr?'▾':'▸'}</button>`:'<span class="ist-mk0"></span>';
    out.push(`<tr class="ist-n2 ${on?'chosen':''}"><td class="i isp-col-prod" title="${se(r.prod)}"><span class="ist-fila" style="padding-left:${ind}px">${mk}<button class="ist-tn ${on?'on':''}" data-act="foco" data-v="${se(r.cod)}" data-sel="p:${se(r.cod)}" aria-pressed="${on}"><span class="nm">${se(r.prod)}</span>${st.det?'':`<small class="ist-cod">${se(r.cod)}</small>`}</button></span></td>${cols.map(([k])=>`<td class="${sclaseCol(r,k)}">${scelda(G,r,k,tot)}</td>`).join('')}</tr>`);
    if(st.det&&abr)for(const a of r.areas)out.push(`<tr class="ist-area"><td class="i"><span class="ist-fila" style="padding-left:${ind+18}px"><span class="ist-mk0"></span>↳ ${se(a.area)}</span></td>${cols.map(([k])=>`<td class="${sclaseCol({...r,...a},k)}">${scelda(G,{...r,...a},k,tot,true)}</td>`).join('')}</tr>`);};
  const fGrupo=(g,n,fam,sub,key,ind)=>{const abierto=st.ab[key]??niv>n,on=st.grupo&&st.grupo.fam===fam&&(st.grupo.sub??null)===(sub??null),h=sserie(g.g,G.B.P.meses.length);
    out.push(`<tr class="ist-n${n} ${on?'chosen':''}"><td class="i" title="${se(slabel(G,n?'sub':'fam',g.n))}"><span class="ist-fila" style="padding-left:${ind}px"><button class="ist-mk" data-act="abrirG" data-v="${se(key)}" data-ab="${abierto?1:0}" aria-expanded="${abierto}" aria-label="Abrir o cerrar">${abierto?'▾':'▸'}</button><button class="ist-tn" data-act="grupo" data-fam="${se(fam)}" data-sub="${se(sub??'')}" data-n="${n}" data-sel="g:${se(fam)}|${se(sub??'')}" aria-pressed="${!!on}"><span class="nm">${se(slabel(G,n?'sub':'fam',g.n))}</span><small>${sn(g.g.length)}</small></button></span></td>${cols.map(([k])=>`<td class="${k==='h'?'t':k==='v'?`val ${g.v<0?'rojo':''}`:k==='abc'?'abc':''}">${k==='v'?se(sv0(g.v)):k==='pct'?(g.v>0&&tot>0?`${sn(g.v/tot*100,g.v/tot<.1?1:0)} %`:'—'):k==='dias'?se(sdiasTxt(g.dias)):k==='h'?smini(h):''}</td>`).join('')}</tr>`);
    return abierto;};
  if(plana)for(const r of ssort(D.visibles,[o]))fProd(r,8);
  else for(const f of sgrupos(G,D.visibles,'fam',o))if(fGrupo(f,0,f.n,null,f.n,2))for(const s of sgrupos(G,f.g,'sub',o))if(fGrupo(s,1,f.n,s.n,`${f.n}|${s.n}`,16))for(const r of ssort(s.g,[o]))fProd(r,40);
  return out;
}
function stabla(G,D){const st=G.st,cols=scols(G,D),o=sord(st),filas=sfilas(G,D,cols),plana=st.q.trim()||st.prof==='Lista';G.nFilas=filas.length;
  const orden=(k,t)=>`<button data-act="orden" data-v="${k}">${se(t)}${o.k===k?(o.d>0?' ↑':' ↓'):''}</button>`;
  const header=cols.map(([k,t,w])=>`<th class="${w}" ${k==='abc'?'title="Clase por valor positivo, calculada antes de buscar: A hasta el 80 %, B hasta el 95 %"':k==='pct'?'title="Sobre lo que está en positivo"':''}>${['h','pct','delta'].includes(k)?se(t):orden(k,t)}</th>`).join('');
  const total=cols.map(([k])=>`<td>${k==='v'?se(sv0(D.total)):k==='vh'?se(sv0(ssum(D.visibles,'vh'))):k==='delta'?se(sv0(ssum(D.visibles,'vh')-D.total)):k==='dias'?se(sdiasTxt(D.dias)):''}</td>`).join('');
  return `<table><thead><tr><th class="i">${orden('prod',plana?'Producto':'Familia › Subfamilia › Producto')}</th>${header}</tr></thead><tbody><tr class="tot"><td class="i">Total · ${sn(D.visibles.length)} productos</td>${total}</tr>${filas.slice(0,st.limite).join('')}</tbody></table>${filas.length>st.limite?sb('mas','',`Ver ${Math.min(150,filas.length-st.limite)} más de ${sn(filas.length-st.limite)}`,false,'','ist-mas'):''}`;
}
function stituloFecha(st){return st.af?`${st.fecha.split('-').reverse().join('/')} · ${String(st.hora).padStart(2,'0')}:59`:'Stock actual';}
function sprincipal(G,D){const st=G.st;
  if(D.pending||D.error)return `<div class="ist-aviso" role="status">${se(D.pending?'Consultando el stock de esa fecha y hora…':D.error)}${D.error?sb('reintentar','','Reintentar',false,'','ist-mini-btn'):''}</div>`;
  const nota=!D.analisis&&!st.af?'<p class="ist-nota">Análisis reciente del kardex no disponible: se muestra el stock actual.</p>':'';
  const clase=D.analisis?`<select class="ist-men" data-change="clase" aria-label="Filtrar por clase">${[['todos','Clase: todas'],['A','Clase A'],['B','Clase B'],['C','Clase C'],['areaNeg','Con un área negativa']].map(([v,t])=>`<option value="${v}" ${st.clase===v?'selected':''}>${t}</option>`).join('')}</select>`:'';
  return `<div class="ist-fl"><span class="ist-lb">Abrir hasta ${ssegm('prof',[['Familia','Familia'],['Subfamilia','Subfamilia'],['Producto','Producto'],['Lista','Lista']],st.prof)}</span>${st.chip!=='todos'?`<button class="ist-quita" data-act="chip" data-v="${se(st.chip)}" title="Ver todo">${se(sestadoNom[st.chip]||st.chip)} ✕</button>`:''}<span class="ist-esp"></span>${clase}${samp(st,'lista','la lista')}</div>
    <div class="ist-wrap ist-arbol isp-table">${D.visibles.length?stabla(G,D):'<p class="ist-aviso">No hay productos con estos filtros.</p>'}</div>${nota}`;
}
function salcance(G,D){const st=G.st;if(!D.visibles)return {rs:[],P:null,sel:false};
  const p=st.foco?D.visibles.find(r=>r.cod===st.foco):null;if(p)return {rs:[p],P:p,sel:true};
  if(st.grupo){const rs=D.visibles.filter(r=>r.fam===st.grupo.fam&&(st.grupo.sub==null||r.sub===st.grupo.sub));if(rs.length)return {rs,P:null,sel:true};}
  return {rs:D.visibles,P:null,sel:false};}
function sficha(G,D){const st=G.st,P=G.B.P;
  if(D.pending||D.error)return '<p class="ist-aviso">—</p>';
  if(!D.visibles?.length)return '<p class="ist-aviso">Elegí un producto o una familia de la lista.</p>';
  const {rs,P:r,sel}=salcance(G,D),um=r?(P.unidades[r.um]||r.um):'',usal=r?(P.unidades[r.usal]||r.usal):'',cmp=st.af&&st.comparar&&D.photo?.comparar,qq=q=>r&&!r.mixed?scantidad(q,r.factor,um,usal,st.salida):'—',nA=st.areas.length?`${st.areas.length} ${st.areas.length===1?'área':'áreas'}`:'todas las áreas';
  const miga=r?`${slabel(G,'fam',r.fam)} › ${slabel(G,'sub',r.sub)}`:sel&&st.grupo.sub!=null?slabel(G,'fam',st.grupo.fam):sel?'Familia':'Stock';
  const tit=r?r.prod:sel?(st.grupo.sub!=null?slabel(G,'sub',st.grupo.sub):slabel(G,'fam',st.grupo.fam)):st.chip!=='todos'?sestadoNom[st.chip]:'Todo el stock';
  const sub=r?`cód. ${r.cod} · ${um}${r.abc?` · Clase ${r.abc}`:''}`:`${sn(rs.length)} productos · ${nA}`;
  const cf=(rot,v,s='',c='')=>`<div class="ist-cf"><span>${se(rot)}</span><b class="${c}">${se(v)}</b><small>${se(s)}</small></div>`;
  const pa=sparado(rs,P);
  const cifras=!sel?'':r?cf('Cantidad',qq(r.q),`en ${r.areas.length} ${r.areas.length===1?'área':'áreas'}`,r.q<0?'rojo':'')+cf('Valor',ss(r.v),r.precio==null?'':`a ${ss(r.precio)} / ${um}`,r.v<0?'rojo':'')+(D.analisis?cf('Consumo 90 días',r.mixed?'—':r.consumo>0?scantidad(r.consumo,r.factor,um,usal,false):'Nada',r.consumo>0&&!r.mixed?`${sv(r.consumo/P.ventana)} ${um} por día`:'Restaurante entero')+cf('Días de stock',r.estado==='neg'||r.mixed?'—':r.estado==='sin'?'Sin consumo':sdiasTxt(r.dias),r.estado==='alto'?`más de ${P.umbral}`:'',r.estado==='sin'||r.estado==='alto'?'nar':''):cf('Precio',ss(r.precio))):cf('Valor',ss(ssum(rs,'v'),0))+cf('En positivo',ss(pa.pos,0))+cf('En negativo',ss(pa.neg,0),`${sn(rs.filter(x=>x.estado==='neg').length)} productos`,pa.neg<-.5?'rojo':'')+(D.analisis?cf('Días de inventario',sdiasTxt(sdiasConjunto(rs,P.ventana))):'');
  let frase='';
  if(D.analisis){if(r){const q=scantidad(r.q,r.factor,um,usal,false),c=r.consumo>0?scantidad(r.consumo,r.factor,um,usal,false):'';
      frase=r.mixed?'Las unidades de este código no coinciden: no se suman sus cantidades ni se calcula cobertura.':r.estado==='neg'?`El sistema dice ${q}: se descargó más de lo que entró. Resta al total sin ser mercadería que falta.`:r.estado==='sin'?`Hay ${q} y no salió nada en 90 días.${soperacion(r,P)?' Es un insumo de operación: ninguna receta lo descarga, así que sale sólo al contar.':''}`:r.dias!=null?`Hay ${q} y salen ${c} cada 90 días: alcanza para ${sdiasTxt(r.dias)} días.${soperacion(r,P)?' Es un insumo de operación.':''}`:'';}
    else frase=sfrase(rs,P,sel?'':st.chip);}
  const tabs=[['areas','Por área']];if(D.analisis)tabs.push(['historia','Evolución'],['escenario','Cobertura']);
  if(!tabs.some(([k])=>k===st.tab))st.tab='areas';
  const verFrase=frase&&st.tab!=='escenario'&&(r||st.tab==='areas');
  let body='';
  if(st.tab==='areas'){
    const m=new Map();for(const x of rs)for(const a of x.areas){const c=m.get(a.area)||{q:0,v:0,vh:0};c.q+=a.q;c.v+=a.v;c.vh+=a.vh||0;m.set(a.area,c);}
    const fil=[...m.entries()].sort((a,b)=>b[1].v-a[1].v),pos=fil.reduce((s,[,x])=>s+Math.max(0,x.v),0)||1,mx=Math.max(1,...fil.map(([,x])=>Math.abs(x.v)));
    const filas=fil.map(([n,x])=>cmp?`<button class="ist-ar cmp" data-act="area" data-v="${se(n)}"><span class="n">${se(n)}</span><span class="val ${x.v<0?'rojo':''}">${se(ss(x.v,0))}</span><span class="q">${se(ss(x.vh,0))}</span><span class="q">${se(sd0(x.vh-x.v))}</span></button>`:`<button class="ist-ar ${r?'cq':''} ${st.focoArea===n?'on':''}" data-act="area" data-v="${se(n)}" title="Ver su evolución"><span class="n">${se(n)}</span>${r?`<span class="q ${x.q<0?'rojo':''}">${se(qq(x.q))}</span>`:''}<span class="x"><i style="width:${(Math.abs(x.v)/mx*100).toFixed(1)}%"></i></span><span class="val ${x.v<0?'rojo':''}">${se(ss(x.v,r?2:0))}</span>${r?'':`<span class="p">${x.v>0?`${sn(x.v/pos*100)} %`:'—'}</span>`}</button>`).join('');
    const fuera=sfuera(G,D,sel);
    body=`<div class="ist-lista">${filas||'<p class="ist-nota">Sin stock en estas áreas.</p>'}</div>${r?.negArea?'<p class="ist-nota">Hay stock negativo en alguna área: el total del producto puede compensarlo con el de otra.</p>':''}${fuera}`;
  }else if(st.tab==='historia'){
    const areas=[...new Set(rs.flatMap(x=>x.areas.map(a=>a.area)))],foco=areas.includes(st.focoArea)?st.focoArea:null,n=P.meses.length;
    const h=foco?(()=>{const z=new Array(n).fill(0);for(const x of rs)for(const a of x.areas)if(a.area===foco)for(let i=0;i<n;i++)z[i]+=a.h[i]||0;return z;})():!sel?D.serie:sserie(rs,n);
    const ref=Math.min(st.ref,Math.max(0,n-1)),dif=h[n-1]-h[ref],pct=h[ref]>0&&h[n-1]>0?(h[n-1]/h[ref]-1)*100:null;
    const base=r?r.areas.map(a=>({n:a.area,an:a.h[ref]||0,ah:a.h[n-1]||0})):rs.map(x=>{const a=foco?x.areas.find(z=>z.area===foco):null,hh=foco?(a?a.h:[]):x.h;return {n:x.prod,an:hh[ref]||0,ah:hh[n-1]||0};});
    const camb=base.map(x=>({...x,d:x.ah-x.an})).filter(x=>Math.abs(x.d)>=1).sort((a,b)=>Math.abs(b.d)-Math.abs(a.d));
    body=`<div class="ist-evcab"><select class="ist-men" data-change="ref" aria-label="Contra qué mes">${P.meses.slice(0,-1).map((m,i)=>`<option value="${i}" ${i===ref?'selected':''}>Contra ${se(m)}</option>`).join('')}</select><span class="ist-dif">${se(sd0(dif))}${pct==null?'':` (${pct>0?'+':'−'}${sn(Math.abs(pct))} %)`}</span><span class="ist-esp"></span><select class="ist-men" data-change="curvaArea" aria-label="Área de la curva"><option value="">Todas las áreas</option>${areas.map(a=>`<option value="${se(a)}" ${foco===a?'selected':''}>${se(a)}</option>`).join('')}</select></div>${scurvaFicha(h,P.meses,ref)}<div class="ist-lista">${camb.slice(0,7).map(x=>`<div class="ist-tp"><span class="n" title="${se(x.n)}">${se(x.n)}</span><small>${sn(x.an)} → ${sn(x.ah)}</small><b>${se(sd0(x.d))}</b></div>`).join('')}</div><p class="ist-nota">${camb.length?`Fotos después de cada cierre y último momento del kardex, a precio de cada área; por eso el último punto (${se(ss(h[n-1],0))}) puede diferir un poco del Valorizado.`:'Sin cambios de al menos S/ 1 contra ese mes.'}</p>`;
  }else{
    const dias=st.objetivo,atajos=ssegm('obj',[30,45,60,90].map(n=>[String(n),String(n)]),String(dias));
    const cab=`<div class="ist-evcab"><span class="ist-lb">Días de cobertura ${atajos}</span><label class="ist-lb">Otro <input class="ist-dias" type="number" min="1" max="365" step="1" data-input="objetivo" value="${dias}" aria-label="Días del escenario"></label></div>`;
    const nota='<p class="ist-nota">Cálculo propio, al ritmo de los últimos 90 días del restaurante entero. El stock es el de las áreas elegidas; no incluye plazos de compra, estacionalidad ni cambios de demanda.</p>';
    if(r){const e=sescenario(r,dias,P.ventana),so=ssobra(r,dias);
      body=`${cab}<p class="ist-frase">${e?(so>0?`Con ${dias} días de stock bastan ${se(`${sv(e.equivalente)} ${um}`)}: sobran ${se(ss(so,0))}.`:`Tiene menos de ${dias} días: no sobra nada.`):'Se necesita stock no negativo, una sola unidad y consumo positivo para calcular este escenario.'}</p>${e?`<div class="ist-lista"><div class="ist-pr"><span>Consumo por día</span><b>${se(`${sv(r.consumo/P.ventana)} ${um}`)}</b></div><div class="ist-pr"><span>Equivalente a ${dias} días</span><b>${se(`${sv(e.equivalente)} ${um}`)}</b></div><div class="ist-pr"><span>Stock menos equivalente</span><b>${se(`${e.diferencia>0?'+':''}${sv(e.diferencia)} ${um}`)}</b></div><div class="ist-pr"><span>Valor de esa diferencia</span><b>${se(ss(e.valor))}</b></div></div>`:''}${nota}`;
    }else{const lista=rs.map(x=>({x,s:ssobra(x,dias)})).filter(z=>z.s>=1).sort((a,b)=>b.s-a.s),tot=lista.reduce((s,z)=>s+z.s,0),sinC=ssum(rs.filter(x=>x.estado==='sin'),'v');
      body=`${cab}<p class="ist-frase">Por encima de ${dias} días sobran ${se(ss(tot,0))} en lo que sí se consume${sinC>.5?`, y ${se(ss(sinC,0))} más en lo que no tuvo consumo.`:'.'}</p><div class="ist-lista">${lista.slice(0,8).map(z=>`<div class="ist-tp"><span class="n" title="${se(z.x.prod)}">${se(z.x.prod)}</span><small>${se(sdiasTxt(z.x.dias))} días</small><b>${se(ss(z.s,0))}</b></div>`).join('')}</div>${nota}`;}
  }
  return `<div class="ist-fcab"><div class="ist-ftit"><span class="ist-miga">${se(miga)}</span><h3 title="${se(tit)}">${se(tit)}</h3><span class="ist-fsub">${se(sub)}</span></div>${r?sb('excel','ficha','Excel',false,'Baja la ficha de este producto','ist-mini-btn'):''}${samp(st,'ficha','la ficha')}${sel?sb('soltar','','Soltar',false,'','ist-mini-btn'):''}</div>${cifras?`<div class="ist-cifras">${cifras}</div>`:''}${verFrase?`<p class="ist-frase">${se(frase)}</p>`:''}<div class="ist-fl ist-ftabs">${ssegm('tab',tabs,st.tab)}</div><div class="ist-fzona">${body}</div>`;
}
// Lo que el total de arriba deja afuera: por eso «Por área» dice otro número.
function sfuera(G,D,sel){const st=G.st,P=G.B.P;if(sel||st.af||st.chip!=='todos'||st.clase!=='todos'||st.fams.length||st.subs.length||st.q.trim())return '';
  if(!st.areas.length)return P.areas_iniciales.length?`<div class="ist-fuera"><span>Con todas las áreas.</span>${sb('principales','areas','Las principales',false,'','ist-mini-btn')}</div>`:'';
  const otras=ssumas(G.B.rows.filter(r=>!st.areas.includes(r.area)),'area').filter(([,v])=>Math.abs(v)>=.5);if(!otras.length)return '';
  const tot=otras.reduce((s,[,v])=>s+v,0),nom=otras.slice(0,3).map(([a])=>slabel(G,'area',a)).join(', ');
  return `<div class="ist-fuera"><span>Fuera de esta cuenta: ${se(ss(tot,0))} en otras ${otras.length} ${otras.length===1?'área':'áreas'} (${se(nom)}${otras.length>3?'…':''}).</span>${sb('todos','areas','Sumarlas',false,'','ist-mini-btn')}</div>`;}
const sheads=['Código','Familia','Subfamilia','Producto','Unidad kardex','Precio unitario','Cantidad','Valorizado S/','ABC','Consumo 90 d','Días de inventario','Estado','Áreas negativas'];
const svals=r=>[r.cod,r.fam,r.sub,r.prod,r.mixed?'Varias unidades':r.um,r.precio,r.mixed?null:r.q,r.v,r.abc,r.mixed?null:r.consumo,r.dias,setiqueta[r.estado]||'',r.negArea?'Sí':'No'];
function scontexto(G){const st=G.st,P=G.B.P;return {nombre:'Contexto',cabeza:['Criterio','Valor'],filas:[
  ['Modo',st.af?'Histórico del kardex':'Stock actual del maestro'],['Fecha y hora',stituloFecha(st)],['Hoy del kardex',P.rango?.[1]||'No disponible'],['Comparar con hoy',st.af&&st.comparar&&G.D.photo?.comparar?'Sí':'No'],
  ['Áreas',st.areas.join(' / ')||'Todas'],['Familias',st.fams.join(' / ')||'Todas'],['Subfamilias',st.subs.join(' / ')||'Todas'],['Búsqueda',st.q],['Estado',sestadoNom[st.chip]||'Todos'],['Clase',st.clase==='todos'?'Todas':sestadoNom[st.clase]||st.clase],['Ver sin stock',st.sin?'Sí':'No'],['Unidad de pantalla',st.salida?'Entrada y resto en salida':'Kardex'],['Producto en ficha',st.foco||''],['Área de la curva',st.focoArea||'Todas'],['Escenario días',st.objetivo],
  ['ABC','Valor positivo del recorte antes de buscar; acumulado anterior a cada producto: A <80%, B <95%, C resto.'],['Consumo','Restaurante entero, últimos 90 días; sin transferencias ni requerimientos ni ajustes.'],['Cantidades','Numéricas en la unidad kardex, seis decimales. Sin total entre productos o unidades diferentes.'],['Histórico','Foto de mayor correlativo hasta la hora; datos maestros y activos de hoy. Consulta fallida no se toma por stock cero.'],['Alcance','Todas las filas del listado filtrado o la ficha elegida, sin el límite de pantalla.']]};}
function sexportar(G,tipo){const D=G.D,st=G.st;if(!D.visibles)return null;const rows=ssort(D.visibles,[sord(st)]),r=rows.find(x=>x.cod===st.foco),ps=tipo==='ficha'?(r?[r]:[]):rows;
  const cmp=st.af&&st.comparar&&D.photo?.comparar,hojas=[{nombre:'Productos',cabeza:[...sheads,...(cmp?['Stock hoy','Valor hoy S/','Δ cantidad','Δ valor S/']:[])],filas:ps.map(r=>[...svals({...r,fam:slabel(G,'fam',r.fam),sub:slabel(G,'sub',r.sub)}),...(cmp?[r.mixed?null:r.qh,r.vh,r.mixed?null:r.qh-r.q,r.vh-r.v]:[])]),decimales:6},
    {nombre:'Áreas',cabeza:['Código','Producto','Área','Unidad','Cantidad','Valorizado S/',...(cmp?['Stock hoy','Valor hoy S/','Δ cantidad','Δ valor S/']:[])],filas:ps.flatMap(r=>r.areas.map(a=>[r.cod,r.prod,a.area,r.um,r.mixed?null:a.q,a.v,...(cmp?[r.mixed?null:a.qh,a.vh,r.mixed?null:a.qh-a.q,a.vh-a.v]:[])])),decimales:6}];
  if(D.analisis)hojas.push({nombre:'Historia',cabeza:['Código','Producto','Área',...G.B.P.meses],filas:ps.flatMap(r=>[[r.cod,r.prod,'Todas',...r.h],...r.areas.map(a=>[r.cod,r.prod,a.area,...a.h])]),decimales:6});
  if(tipo==='ficha'&&D.analisis&&r){const e=sescenario(r,st.objetivo,G.B.P.ventana);hojas.push({nombre:'Escenario',cabeza:['Código','Unidad','Días','Stock','Consumo 90 d','Equivalente','Stock menos equivalente','Valor diferencia S/'],filas:e?[[r.cod,r.um,e.dias,r.q,r.consumo,e.equivalente,e.diferencia,e.valor]]:[],decimales:6});}
  hojas.push(scontexto(G));return libro(hojas);
}
// `modo`: 'ficha' sólo la ficha; 'busca' todo menos la cabecera, donde está el cursor.
function spintar(G,modo){G.D=sfiltrar(G.B,G.st);const root=G.root,st=G.st;
  if(modo!=='ficha'){
    if(modo!=='busca'){const cab=root.querySelector('.isp-cab'),ab=[...cab.querySelectorAll('details[open]')].map(d=>[d.dataset.menu,d.querySelector('.ist-menu')?.scrollTop||0]);
      cab.innerHTML=scab(G,G.D);for(const [m,y] of ab){const d=cab.querySelector(`[data-menu="${m}"]`);if(d){d.setAttribute('open','');const x=d.querySelector('.ist-menu');if(x)x.scrollTop=y;}}}
    root.querySelector('.isp-kpis').innerHTML=skpis(G,G.D);
    const viejo=root.querySelector('.isp-table'),x=viejo?.scrollLeft||0,y=viejo?.scrollTop||0;
    root.querySelector('.isp-main').innerHTML=sprincipal(G,G.D);
    const nuevo=root.querySelector('.isp-table');if(nuevo){nuevo.scrollTop=y;nuevo.scrollLeft=x;}
  }
  root.classList.toggle('amp',!!st.amp);root.classList.toggle('det',!!st.det);root.querySelector('.isp-main').hidden=st.amp==='ficha';
  const der=root.querySelector('.isp-n2der');if(der)der.innerHTML=sn2der(G);
  const ficha=root.querySelector('.isp-ficha');ficha.hidden=st.amp==='lista';if(st.amp!=='lista')ficha.innerHTML=sficha(G,G.D);
  const clave=st.foco?`p:${st.foco}`:st.grupo?`g:${st.grupo.fam}|${st.grupo.sub??''}`:'';
  for(const b of root.querySelectorAll('.isp-main [data-sel]')){const on=b.dataset.sel===clave;b.closest('tr').classList.toggle('chosen',on);b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));}
}
function spedir(G,reintentar=false){const st=G.st;if(!st.af)return;const key=`${st.fecha}|${st.hora}`,foto=G.B.fotos.get(key);
  if(foto&&!reintentar)return;if(!G.B.P.rango)return;
  if(st.fecha<G.B.P.rango[0]||st.fecha>G.B.P.rango[1])return;
  if(G.pedido===key&&!reintentar)return;G.pedido=key;
  G.enviar?.('foto',{sello:G.B.P.sello,fecha:st.fecha,hora:st.hora,reintentar});
}
function senlazar(G){const root=G.root;
  root.addEventListener('click',ev=>{const b=ev.target.closest('[data-act]');if(!b){if(G.st.como&&!ev.target.closest('.ist-como')){G.st.como=false;spintar(G,'ficha');}return;}const {act,v}=b.dataset,st=G.st;let modo;
    if(act!=='como')st.como=false;
    if(act==='todos'){st[v]=[];if(v==='fams')st.subs=[];st.limite=150;st.foco=null;st.grupo=null;}else if(act==='principales'){st.areas=[...G.B.P.areas_iniciales];st.limite=150;}
    else if(act==='abrir')st.abiertos=st.abiertos.includes(v)?st.abiertos.filter(x=>x!==v):[...st.abiertos,v];
    else if(act==='abrirG')st.ab={...st.ab,[v]:b.dataset.ab!=='1'};
    else if(act==='prof'){st.prof=v;st.ab={};st.limite=150;}
    else if(act==='foco'){st.foco=st.foco===v?null:v;st.grupo=null;st.focoArea=null;if(st.amp)st.amp=false;else modo='ficha';}
    else if(act==='grupo'){const g={fam:b.dataset.fam,sub:b.dataset.n==='1'?b.dataset.sub:null},igual=st.grupo&&st.grupo.fam===g.fam&&st.grupo.sub===g.sub;st.grupo=igual?null:g;st.foco=null;st.focoArea=null;modo='ficha';}
    else if(act==='soltar'){st.foco=null;st.grupo=null;st.focoArea=null;modo='ficha';}
    else if(act==='historia'){[st.foco,st.focoArea]=JSON.parse(v);st.grupo=null;st.tab='historia';if(st.amp)st.amp=false;else modo='ficha';}
    else if(act==='area'){st.focoArea=v||null;st.tab=G.D.analisis?'historia':'areas';modo='ficha';}
    else if(act==='tab'){st.tab=v;modo='ficha';}
    else if(act==='obj'){st.objetivo=+v;modo='ficha';}
    else if(act==='chip'){st.chip=st.chip===v?'todos':v;st.foco=null;st.grupo=null;st.focoArea=null;st.limite=150;}
    else if(act==='amp')st.amp=st.amp===v?false:v;
    else if(act==='como'){st.como=!st.como;}
    else if(act==='mas')st.limite+=150;
    else if(act==='orden'){const o=sord(st),num=!['prod','cod'].includes(v);st.orden=[{k:v,d:o.k===v?-o.d:num?-1:1}];}
    else if(act==='reintentar'){G.B.fotos.delete(`${st.fecha}|${st.hora}`);spedir(G,true);}
    else if(act==='excel'){const blob=sexportar(G,v);if(blob)bajar(`stock_${v}_${st.af?st.fecha:'actual'}.xlsx`,blob);return;}
    spintar(G,modo);
  });
  root.addEventListener('change',ev=>{const el=ev.target,st=G.st,key=el.dataset.filter;
    if(key){st[key]=el.checked?[...st[key],el.value]:st[key].filter(v=>v!==el.value);
      if(key==='fams'){const subs=new Set(G.B.rows.filter(r=>!st.fams.length||st.fams.includes(r.fam)).map(r=>r.sub));st.subs=st.subs.filter(x=>subs.has(x));}
      st.limite=150;st.foco=null;st.grupo=null;spintar(G);return;}
    if(el.dataset.toggle==='det'){st.det=el.checked;sguardarLS('stock_det',st.det);spintar(G);return;}
    const toggle=el.dataset.toggle;if(toggle){st[toggle]=el.checked;st.limite=150;if(toggle==='af'){st.chip='todos';st.clase='todos';st.focoArea=null;}spintar(G);if(toggle==='af')spedir(G);return;}
    if(el.dataset.change==='fecha'||el.dataset.change==='hora'){const key=el.dataset.change;
      if(key==='fecha'&&(!el.value||el.value<G.B.P.rango[0]||el.value>G.B.P.rango[1])){el.value=st.fecha;return;}
      st[key]=key==='hora'?+el.value:el.value;st.limite=150;spintar(G);spedir(G);}
    if(el.dataset.change==='clase'){st.clase=el.value;st.foco=null;st.grupo=null;st.limite=150;spintar(G);}
    if(el.dataset.change==='ref'){st.ref=+el.value;spintar(G,'ficha');}
    if(el.dataset.input==='objetivo'){const n=+el.value;if(Number.isInteger(n)&&n>=1&&n<=365){st.objetivo=n;spintar(G,'ficha');}else el.value=st.objetivo;}
    if(el.dataset.change==='curvaArea'){st.focoArea=el.value||null;spintar(G,'ficha');}
  });
  root.addEventListener('input',ev=>{const el=ev.target,st=G.st;
    if(el.dataset.lista){const q=splano(el.value);el.closest('.ist-menu').querySelectorAll('label').forEach(l=>l.hidden=!splano(l.textContent).includes(q));return;}
    if(el.dataset.input==='q'){st.q=el.value;st.limite=150;spintar(G,'busca');}
  });
  root.addEventListener('scroll',ev=>{const el=ev.target;if(el.matches?.('.isp-table')&&G.nFilas>G.st.limite&&el.scrollTop+el.clientHeight>el.scrollHeight-70){G.st.limite+=150;spintar(G,'busca');}},true);
}
window.__stockDatos={leer:sleer,agrupar:sagrupar,filtrar:sfiltrar,estados:sestados,diasConjunto:sdiasConjunto,escenario:sescenario,cantidad:scantidad,round:sround,ordenar:ssort,parado:sparado,frase:sfrase,sobra:ssobra};
window.__stockUI={inicial:sinicial,pintar:spintar,exportar:sexportar};
export default function(component){const {data:P,parentElement,setTriggerValue}=component;if(!P)return;const old=window.__stockProd;
  if(P.parte==='foto'){
    if(!old){window.__stockFotoPendiente=P;return;}if(P.sello!==old.B.P.sello)return;
    const key=`${P.fecha}|${P.hora}`;old.B.fotos.set(key,P);old.B.cache.clear();if(old.pedido===key)old.pedido=null;
    if(old.B.fotos.size>12)old.B.fotos.delete(old.B.fotos.keys().next().value);if(old.root.isConnected)spintar(old);return;
  }
  old?.abort?.abort();let st=old?.st||sinicial(P),B=old?.B.P.sello===P.sello?old.B:sleer(P);
  if(old&&old.B.P.sello!==P.sello){for(const [k,dk] of [['areas','area'],['fams','fam'],['subs','subfam']])st[k]=st[k].filter(v=>P.dic[dk].includes(v));st.focoArea=null;st.abiertos=[];st.limite=150;}
  if(old&&old.semilla!==P.semilla)st={...st,...P.inicial,af:false,clase:'todos',foco:null,grupo:null,focoArea:null,limite:150};
  if(!P.hay_fecha)st.af=false;else if(P.rango){st.fecha=st.fecha<P.rango[0]?P.rango[0]:st.fecha>P.rango[1]?P.rango[1]:st.fecha;}
  if(!P.analisis)st.chip='todos';
  let root=parentElement.querySelector('.isp');if(root)root.remove();root=document.createElement('div');root.className='isp ist';
  if(st.det==null)st.det=!!sleerLS('stock_det',false);if(typeof st.amp==='boolean'&&st.amp)st.amp='lista';
  root.innerHTML='<div class="isp-n2der ist-n2der"></div><div class="isp-cab ist-cab"></div><div class="isp-kpis ist-kpis"></div><div class="ist-cuerpo"><section class="isp-main ist-izq"></section><aside class="isp-ficha ist-ficha" aria-label="Ficha"></aside></div>';parentElement.appendChild(root);
  const G={root,st,B,enviar:setTriggerValue,semilla:P.semilla,abort:new AbortController(),pedido:old?.B.P.sello===P.sello?old.pedido:null};window.__stockProd=G;
  const pend=window.__stockFotoPendiente;if(pend?.sello===P.sello){B.fotos.set(`${pend.fecha}|${pend.hora}`,pend);window.__stockFotoPendiente=null;}
  senlazar(G);spintar(G);spedir(G);
  document.addEventListener('pointerdown',ev=>{if(!ev.composedPath().some(n=>n.dataset?.menu))root.querySelectorAll('details[open]').forEach(d=>d.open=false);},{signal:G.abort.signal});
  document.addEventListener('keydown',ev=>{if(ev.key!=='Escape'||!root.isConnected)return;const ab=root.querySelectorAll('details[open]');
    if(ab.length)ab.forEach(d=>d.open=false);else if(G.st.como){G.st.como=false;spintar(G);}else if(G.st.amp){G.st.amp=false;spintar(G);}},{signal:G.abort.signal});
}
