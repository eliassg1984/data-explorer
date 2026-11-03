/* Ajuste › Detalle histórico (#809). La forma de Compras › Detalle docs.: Conteos |
   Líneas | Tabla dinámica, cuatro indicadores que filtran y, al costado, el resumen o
   la ficha del conteo. Usa las clases `dc-*` de documentos.css, que va antes en la
   hoja. Los meses son el botón de Python, puesto en el hueco `.dc-lugar`. */
const AJH=(()=>{
  const CAMPOS=['Familia','Subfamilia','Producto','Área','Unidad','Mes','Sesión','Fecha'];
  const METRICAS=['Ajuste valorizado','Ajuste (cantidad)','Valorizado total','Líneas'];
  const EPS=1e-9,MES=['ene','feb','mar','abr','may','jun','jul','ago','set','oct','nov','dic'];
  const nf=new Intl.NumberFormat('es-PE',{minimumFractionDigits:2,maximumFractionDigits:2}),qf=new Intl.NumberFormat('es-PE',{maximumFractionDigits:3});
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm=v=>String(v??'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
  const cmp=(a,b)=>a<b?-1:a>b?1:0;
  const suma=(rs,k)=>{let s=0,c=0;for(const r of rs){const x=r[k];if(x==null)continue;const v=x-c,t=s+v;c=t-s-v;s=t;}return s;};
  const f2=v=>v==null||!isFinite(v)?'—':nf.format(v),qn=v=>v==null||!isFinite(v)?'—':qf.format(v);
  const fS=v=>v==null||!isFinite(v)?'—':`${v<-.5?'−':''}S/ ${Math.round(Math.abs(v)).toLocaleString('en-US')}`;
  const nN=(n,t,pl)=>`${n.toLocaleString('en-US')} ${n===1?t:(pl||t+'s')}`;
  const fCorta=v=>{if(!v)return'—';const[y,m,d]=v.split('-');return`${+d} ${MES[+m-1]} ${y.slice(2)}`;};
  const mesR=v=>{const[y,m]=String(v).split('-');return m?`${MES[+m-1]} ${y.slice(2)}`:v;};
  const leerLS=(k,d)=>{try{const v=localStorage.getItem(k);return v==null?d:JSON.parse(v);}catch(e){return d;}},guardarLS=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v));}catch(e){/* sólo esta vez */}};
  function inicial(){return{modo:'Conteos',kpi:'todos',amp:null,menu:null,q:'',fams:null,areas:null,conteo:null,orden:null,como:false,config:false,
    filas:['Familia','Producto'],columnas:['Mes'],metrica:'Ajuste valorizado',abiertos:[],nCols:12};}
  // Una línea: posiciones de `_historico_datos.CAMPOS`.
  function leer(P){const D=P.dic;return P.filas.map((r,id)=>{const[f,fam,sub,area,prod,cod,um,sis,fis,dif,val,stock]=r;
    return{id,f,fam,sub,area,prod,cod,um,sis,fis,dif,val:val??0,stock,k:`${f}|${area}`,
      buscar:norm([D.prod[prod],D.cod[cod],D.area[area],D.fam[fam],D.sub[sub]].join(' '))};});}
  const precio=l=>Math.abs(l.dif??0)>EPS?l.val/l.dif:Math.abs(l.fis??0)>EPS&&l.stock!=null?l.stock/l.fis:null;
  function conteos(rs,P){const m=new Map();for(const l of rs){let c=m.get(l.k);if(!c){c={key:l.k,f:l.f,area:l.area,fecha:P.fechas[l.f],sesion:P.sesiones[l.f]||'',areaN:P.dic.area[l.area]||'Sin área',lineas:0,ndif:0,falta:0,sobra:0,neto:0,stock:0};m.set(l.k,c);}
      c.lineas++;if(Math.abs(l.val)>EPS||Math.abs(l.dif??0)>EPS)c.ndif++;if(l.val<-EPS)c.falta+=l.val;else if(l.val>EPS)c.sobra+=l.val;c.neto+=l.val;c.stock+=l.stock??0;}
    return[...m.values()].sort((a,b)=>cmp(b.fecha,a.fecha)||cmp(a.areaN,b.areaN));}
  function calcular(P,s,cache){
    if(cache.sello!==P.sello){cache.sello=P.sello;cache.base=leer(P);cache.fk=null;cache.codDe=new Map();for(const l of cache.base)if(!cache.codDe.has(l.prod))cache.codDe.set(l.prod,l.cod);}
    const fk=JSON.stringify([s.fams,s.areas,s.q,s.kpi]);
    if(cache.fk!==fk){const fs=s.fams&&new Set(s.fams),as=s.areas&&new Set(s.areas),qs=norm(s.q).split(/\s+/).filter(Boolean);
      cache.alcance=cache.base.filter(l=>(!fs||fs.has(l.fam))&&(!as||as.has(l.area)));
      const rs0=cache.alcance.filter(l=>qs.every(q=>l.buscar.includes(q)));
      // Los indicadores se cuentan antes de filtrar por ellos: si no, los otros caerían a cero.
      cache.kpis={todos:rs0,falta:rs0.filter(l=>l.val<-EPS),sobra:rs0.filter(l=>l.val>EPS),grande:rs0.filter(l=>Math.abs(l.val)>=100)};
      cache.rs=cache.kpis[s.kpi]||rs0;cache.conteos=conteos(cache.rs,P);cache.fk=fk;cache.pk=null;}
    const pk=JSON.stringify([fk,s.filas,s.columnas]);if(cache.pk!==pk){cache.piv=pivot(cache.rs,P,s);cache.pk=pk;}
    const ficha=s.conteo?cache.alcance.filter(l=>l.k===s.conteo):null;
    return{rs:cache.rs,conteos:cache.conteos,kpis:cache.kpis,piv:cache.piv,ficha:ficha&&ficha.length?ficha:null,alcance:cache.alcance};
  }
  // ── Tabla dinámica: filas en árbol, columnas por un campo, una métrica.
  function dim(l,f,P){return f==='Familia'?l.fam:f==='Subfamilia'?l.sub:f==='Producto'?l.prod:f==='Área'?l.area:f==='Unidad'?l.um:f==='Mes'?P.meses[l.f]:f==='Sesión'?(P.sesiones[l.f]||'~'):P.fechas[l.f];}
  function rot(v,f,P){const D=P.dic;return f==='Familia'?D.fam[v]||'Sin familia':f==='Subfamilia'?D.sub[v]||'Sin subfamilia':f==='Producto'?D.prod[v]||'Sin nombre':f==='Área'?D.area[v]||'Sin área':f==='Unidad'?D.um[v]||'Sin unidad':f==='Mes'?mesR(v):f==='Sesión'?(v==='~'?'Sin sesión':v):fCorta(v);}
  function acc(){return{n:0,val:0,stock:0,dif:0,ums:new Set()};}
  function mas(a,l){a.n++;a.val+=l.val;a.stock+=l.stock??0;a.dif+=l.dif??0;a.ums.add(l.um);}
  function valor(a,m){if(!a)return null;return m==='Líneas'?a.n:m==='Ajuste valorizado'?a.val:m==='Valorizado total'?a.stock:a.ums.size===1?a.dif:null;}
  const fmtM=(v,m)=>m==='Líneas'?(v==null?'—':v.toLocaleString('en-US')):m==='Ajuste (cantidad)'?qn(v):f2(v);
  function nodo(id,campo,val,prof,camino){return{id,campo,val,prof,camino,hijos:new Map(),celdas:new Map(),total:acc()};}
  function pivot(rs,P,s){const raiz=nodo('',null,null,0,[]),cols=new Map();
    for(const l of rs){const ck=s.columnas.length?String(dim(l,s.columnas[0],P)):'~';cols.set(ck,ck);let n=raiz;
      const poner=()=>{mas(n.total,l);if(!n.celdas.has(ck))n.celdas.set(ck,acc());mas(n.celdas.get(ck),l);};poner();
      s.filas.forEach((f,i)=>{const v=dim(l,f,P),key=f+'|'+v;if(!n.hijos.has(key)){const camino=[...n.camino,v];n.hijos.set(key,nodo(JSON.stringify(camino),f,v,i+1,camino));}n=n.hijos.get(key);poner();});}
    return{raiz,columnas:[...cols.keys()].sort()};}
  function ordenar(n,G){const{s,P}=G,o=s.orden;return[...n.hijos.values()].sort((a,b)=>{
    if(o?.id==='pivot'&&o.col!==undefined){const x=valor(o.col==null?a.total:a.celdas.get(o.col),s.metrica),y=valor(o.col==null?b.total:b.celdas.get(o.col),s.metrica);if(x==null||y==null)return x==null?(y==null?0:1):-1;return(x-y)*o.d;}
    return Math.abs(b.total.val)-Math.abs(a.total.val)||cmp(rot(a.val,a.campo,P),rot(b.val,b.campo,P));});}
  function aplanar(G,todo=false){const rs=[],ab=new Set(G.s.abiertos);const ir=n=>{for(const h of ordenar(n,G)){if(!todo||!h.hijos.size)rs.push(h);if(todo||ab.has(h.id))ir(h);}};if(!G.s.filas.length)return[G.D.piv.raiz];ir(G.D.piv.raiz);return rs;}
  function nombreNodo(n,P){if(!n.campo)return'Total';const t=rot(n.val,n.campo,P);if(n.campo!=='Producto')return t;const ci=G0.cache.codDe.get(n.val),c=ci==null?'':P.dic.cod[ci];return c?`${c} · ${t}`:t;}
  function cuerpoPivot(G,a,b){const{s,P}=G,t=G.tablas.pivot;return t.rs.slice(a,b).map(n=>{const ab=s.abiertos.includes(n.id),nom=nombreNodo(n,P),bot=n.hijos.size?`<button data-a="abrir" data-v="${esc(n.id)}" aria-expanded="${ab}" aria-label="${ab?'Contraer':'Expandir'} ${esc(nom)}">${ab?'▾':'▸'}</button>`:'';
    const td=v=>`<td class="num${s.metrica==='Ajuste valorizado'&&v!=null?v<-EPS?' rojo':v>EPS?' verde':'':''}">${fmtM(v,s.metrica)}</td>`;
    return`<tr><td class="dc-nombre"><div style="padding-left:${Math.max(0,n.prof-1)*12}px">${bot}<span title="${esc(nom)}">${esc(nom)}</span></div></td>${t.cols.map(ck=>td(valor(n.celdas.get(ck),s.metrica))).join('')}${t.total?td(valor(n.total,s.metrica)):''}</tr>`;}).join('');}
  function tablaPivot(G){const{s,P,D}=G,cols=D.piv.columnas.slice(0,s.nCols),total=s.columnas.length>0&&D.piv.columnas.length>1,rs=aplanar(G),o=s.orden;G.tablas.pivot={cols,rs,n:150,total};
    const th=(t,ck)=>`<th><button data-a="sortpivot" data-v="${esc(ck??'~total')}">${esc(t)}${o?.id==='pivot'&&o.col===ck?o.d===1?' ↑':' ↓':''}</button></th>`,cr=ck=>s.columnas.length?rot(ck,s.columnas[0],P):s.metrica;
    return`<div class="dc-pivot-info"><span>${rs.length.toLocaleString('en-US')} filas desplegadas · ${cols.length}/${D.piv.columnas.length} columnas</span>${cols.length<D.piv.columnas.length?'<button class="dc-pil" data-a="mascols">Más columnas</button>':''}<button class="dc-pil" data-a="plegar">Contraer todo</button></div><div class="dc-scroll" data-tabla="pivot" tabindex="0"><table class="dc-p"><thead><tr><th class="dc-nombre">${esc(s.filas.join(' / ')||'Total')}</th>${cols.map(ck=>th(cr(ck),ck)).join('')}${total?th('Total',null):''}</tr></thead><tbody>${cuerpoPivot(G,0,150)}</tbody><tfoot><tr><th class="dc-nombre">Total de lo elegido</th>${cols.map(ck=>`<td class="num">${fmtM(valor(D.piv.raiz.celdas.get(ck),s.metrica),s.metrica)}</td>`).join('')}${total?`<td class="num">${fmtM(valor(D.piv.raiz.total,s.metrica),s.metrica)}</td>`:''}</tr></tfoot></table>${rs.length?'':'<p class="dc-vacio">No hay líneas con estos filtros.</p>'}</div>`;}
  const op=(v,t,act)=>`<option value="${esc(v)}"${v===act?' selected':''}>${esc(t)}</option>`;
  function configuracion(G){const s=G.s;
    const eje=e=>`<div class="dc-eje" data-eje="${e}"><b>${e==='filas'?'Filas':'Columnas'}</b><div class="dc-tags">${s[e].map((f,i)=>`<span>${f}${e==='filas'?`<button data-a="mover" data-i="${i}" data-dir="-1" aria-label="Subir ${f}" ${i===0?'disabled':''}>↑</button><button data-a="mover" data-i="${i}" data-dir="1" aria-label="Bajar ${f}" ${i===s[e].length-1?'disabled':''}>↓</button>`:''}<button data-a="quitar" data-eje="${e}" data-v="${f}" aria-label="Quitar ${f}">×</button></span>`).join('')}</div><select data-add="${e}" aria-label="Añadir a ${e}"><option value="">${e==='columnas'&&s.columnas.length?'Cambiar campo…':'Añadir campo…'}</option>${CAMPOS.filter(f=>!s.filas.includes(f)&&!s.columnas.includes(f)).map(f=>op(f,f,'')).join('')}</select></div>`;
    return`<div class="dc-config"><p>Elegí qué va en filas (en árbol) y qué en columnas. Los meses y los filtros de arriba recortan la tabla.</p>${eje('filas')}${eje('columnas')}<button data-a="restaurar">Restaurar tabla</button></div>`;}
  // ── Listas
  function colsLista(G,modo){const det=!!G.s.det;
    if(modo==='ficha')return[['cod','Código','w-cd','c'],['prod','Producto','','l'],['cant','Ajuste','w-x','r'],['val','Valor','w-im','s']];
    if(modo==='Conteos')return[['fecha','Fecha','w-fe','f'],['areaN','Área','','l'],['sesion','Sesión','w-pv','l'],['ndif','Con dif.','w-pc','n'],['falta','Faltó','w-im','s'],['sobra','Sobró','w-im','s'],['neto','Neto','w-im','s'],...(det?[['lineas','Líneas','w-pc','n'],['stock','Valorizado','w-im','v']]:[])];
    return[['fecha','Fecha','w-fe','f'],['cod','Código','w-cd','c'],['prod','Producto','','l'],['areaN','Área','w-pv','l'],...(det?[['famN','Familia','w-pv','l'],['subN','Subfamilia','w-pv','l'],['sis','Stock al cierre','w-st','q'],['fis','Stock declarado','w-st','q'],['precio','Precio prom.','w-st','v']]:[]),['cant','Ajuste','w-x','r'],['val','Ajuste valorizado','w-im','s'],...(det?[['stock','Valorizado total','w-im','v']]:[])];}
  function lineasTabla(rs,P){const D=P.dic;return rs.map(l=>{const um=D.um[l.um]||'';return{key:l.k,id:l.id,fecha:P.fechas[l.f],cod:D.cod[l.cod]||'—',prod:D.prod[l.prod]||'Sin nombre',areaN:D.area[l.area]||'Sin área',famN:D.fam[l.fam]||'',subN:D.sub[l.sub]||'',
    cant:`${qn(l.dif)}${um?` ${um.toLowerCase()}`:''}`,dif:l.dif,sis:l.sis,fis:l.fis,precio:precio(l),val:l.val,stock:l.stock};});}
  function celda(r,c){const[k,,,t]=c,v=r[k];
    if(t==='f')return`<td class="l">${esc(fCorta(v))}</td>`;
    if(t==='n')return`<td>${v==null?'—':Number(v).toLocaleString('en-US')}</td>`;
    if(t==='s')return`<td class="fuerte${v<-EPS?' rojo':v>EPS?' verde':''}">${f2(v)}</td>`;
    if(t==='v')return`<td>${f2(v)}</td>`;if(t==='q')return`<td>${qn(v)}</td>`;if(t==='r')return`<td>${esc(v)}</td>`;
    if(t==='c')return`<td class="l ajh-cod">${esc(v)}</td>`;
    return`<td class="l" title="${esc(v)}">${esc(v)}</td>`;}
  function tablaLista(G,id,cols,filas,conTotal=true){let rs=filas.slice();const o=G.s.orden;
    if(o?.id===id)rs.sort((a,b)=>{const x=a[o.k],y=b[o.k];return x==null?y==null?0:1:y==null?-1:(typeof x==='number'?x-y:cmp(String(x),String(y)))*o.d;});
    G.tablas[id]={cols,rs,n:150};
    const sumables=['ndif','falta','sobra','neto','lineas','stock','val'],pri=Math.max(1,cols.findIndex(c=>sumables.includes(c[0])||c[0]==='cant'));
    const tot=c=>sumables.includes(c[0])?`<td class="${['falta','neto','val'].includes(c[0])&&suma(rs,c[0])<-EPS?'rojo':''}">${['ndif','lineas'].includes(c[0])?suma(rs,c[0]).toLocaleString('en-US'):f2(suma(rs,c[0]))}</td>`:'<td></td>';
    return`<div class="dc-scroll" data-tabla="${id}" tabindex="0"><table class="dc-t"><thead><tr>${cols.map(([k,t,w,c])=>`<th class="${w} ${['l','f','c'].includes(c)?'l':''}"><button data-a="orden" data-id="${id}" data-v="${k}">${esc(t)}${o?.id===id&&o.k===k?o.d===1?' ↑':' ↓':''}</button></th>`).join('')}</tr></thead><tbody>${conTotal?`<tr class="tot"><td class="l" colspan="${pri}">Total · ${id==='conteos'?nN(rs.length,'conteo'):nN(rs.length,'línea')}</td>${cols.slice(pri).map(tot).join('')}</tr>`:''}${filasLista(G,id,0,150)}</tbody></table>${rs.length?'':'<p class="dc-vacio">No hay líneas con estos filtros. Cambiá la búsqueda o elegí otro indicador.</p>'}</div>`;}
  function filasLista(G,id,a,b){const t=G.tablas[id];return t.rs.slice(a,b).map(r=>`<tr ${id==='ficha'?'':`data-a="conteo" data-v="${esc(r.key)}" tabindex="0"`} class="${id!=='ficha'&&r.key===G.s.conteo?'on':''}">${t.cols.map(c=>celda(r,c)).join('')}</tr>`).join('');}
  // ── Filtros, indicadores, ficha y resumen
  function menu(G,id,rot,dic,sel){const{s}=G,ab=s.menu===id,por=new Map();for(const l of G.cache.base){const k=id==='fam'?l.fam:l.area;por.set(k,(por.get(k)||0)+l.val);}
    const ids=[...por.keys()].sort((a,b)=>cmp(dic[a],dic[b])),el=sel?new Set(sel):null,n=sel?sel.length:ids.length;
    return`<div class="dc-ms"><button class="dc-pil" data-a="menu" data-v="${id}" aria-expanded="${ab}">${n===ids.length?`${rot}: todas`:`${rot}: ${n} de ${ids.length}`} ▾</button>${ab?`<div class="dc-pop"><div class="ajh-bar"><button data-a="todas" data-v="${id}">Todas</button><button data-a="ninguna" data-v="${id}">Ninguna</button></div>${ids.map(i=>`<label><input type="checkbox" data-a="chk" data-m="${id}" value="${i}"${!el||el.has(i)?' checked':''}><span>${esc(dic[i]||'—')}</span><small>${esc(fS(por.get(i)))}</small></label>`).join('')}</div>`:''}</div>`;}
  function kpisHtml(G){const{D,s}=G,K=D.kpis,k=(id,r,v,sub,tip,cls='')=>`<button class="dc-kpi${s.kpi===id?' on':''}" data-a="kpi" data-v="${id}" aria-pressed="${s.kpi===id}" title="${esc(tip)}"><span class="r">${esc(r)}</span><span class="v ${cls}">${esc(v)}</span><span class="d">${esc(sub)}</span></button>`,nc=rs=>new Set(rs.map(l=>l.k)).size;
    return k('todos','Conteos',nc(K.todos).toLocaleString('en-US'),`${nN(K.todos.length,'línea')} · neto ${fS(suma(K.todos,'val'))}`,'Cada fecha × área con ajuste registrado en los meses elegidos.')
      +k('falta','Faltantes',K.falta.length.toLocaleString('en-US'),`${fS(suma(K.falta,'val'))} en ${nN(nc(K.falta),'conteo')}`,'Líneas donde se contó menos de lo que decía el sistema.',K.falta.length?'rojo':'')
      +k('sobra','Sobrantes',K.sobra.length.toLocaleString('en-US'),`${fS(suma(K.sobra,'val'))} en ${nN(nc(K.sobra),'conteo')}`,'Líneas donde se contó más de lo que decía el sistema.',K.sobra.length?'verde':'')
      +k('grande','De S/ 100 o más',K.grande.length.toLocaleString('en-US'),`neto ${fS(suma(K.grande,'val'))}`,'Líneas cuyo ajuste vale S/ 100 o más, de un lado o del otro.');}
  const ICO_AMP='<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4"/></svg>',ICO_VOL='<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 2v4H2M14 6h-4V2M10 14v-4h4M2 10h4v4"/></svg>';
  const ampB=(s,c,r)=>`<button class="dc-amp" data-a="amp" data-v="${c}" aria-pressed="${s.amp===c}" title="${s.amp===c?'Volver (Esc)':`Ampliar ${r}`}" aria-label="${s.amp===c?'Volver':`Ampliar ${r}`}">${s.amp===c?ICO_VOL:ICO_AMP}</button>`;
  function fichaHtml(G){const{P,D,s}=G,ls=D.ficha,c=conteos(ls,P)[0],cif=(r,x,y,cl='')=>`<div class="dc-cf"><span>${esc(r)}</span><b class="${cl}">${esc(x)}</b><small>${esc(y)}</small></div>`;
    const peor=[...ls].sort((a,b)=>a.val-b.val)[0],mejor=[...ls].sort((a,b)=>b.val-a.val)[0],fr=[];
    fr.push(`${nN(c.lineas,'línea')} contadas, ${c.ndif} con diferencia.`);
    if(peor&&peor.val<-EPS)fr.push(`El mayor faltante: ${P.dic.prod[peor.prod]} (${fS(peor.val)}).`);
    if(mejor&&mejor.val>EPS)fr.push(`El mayor sobrante: ${P.dic.prod[mejor.prod]} (${fS(mejor.val)}).`);
    const filas=lineasTabla([...ls].sort((a,b)=>a.val-b.val),P);
    return`<div class="dc-fcab"><div class="dc-ftit"><span class="dc-miga">${esc(c.sesion||'Conteo')}</span><h3>${esc(c.areaN)}</h3><span class="dc-miga">${esc(`registrado el ${fCorta(c.fecha)}`)}</span></div>${ampB(s,'panel','la ficha')}<button class="dc-quita" data-a="cerrar">Soltar</button></div>
      <div class="dc-cifras">${cif('Faltó',fS(c.falta),'',c.falta<-EPS?'rojo':'')}${cif('Sobró',fS(c.sobra),'',c.sobra>EPS?'verde':'')}${cif('Neto',fS(c.neto),'',c.neto<-EPS?'rojo':'')}${cif('Valorizado',fS(c.stock),'lo contado')}</div>
      <p class="dc-frase">${esc(fr.join(' '))}</p>${tablaLista(G,'ficha',colsLista(G,'ficha'),filas,false)}`;}
  function resumenHtml(G){const{P,D,s}=G,rs=D.rs,cs=D.conteos,por=new Map();for(const c of cs){const a=por.get(c.area)||{n:0,neto:0};a.n++;a.neto+=c.neto;por.set(c.area,a);}
    const tit={todos:'Qué hay en estos conteos',falta:'Los faltantes',sobra:'Los sobrantes',grande:'Lo de S/ 100 o más'}[s.kpi],f=suma(rs.filter(l=>l.val<0),'val'),so=suma(rs.filter(l=>l.val>0),'val');
    const ms=[...new Set(rs.map(l=>P.meses[l.f]))].sort(),uno=s.areas?.length===1?s.areas[0]:null;
    const fr=`${nN(cs.length,'conteo')} en ${nN(ms.length,'mes','meses')}${ms.length?` (${mesR(ms[0])}${ms.length>1?` a ${mesR(ms[ms.length-1])}`:''})`:''}: faltó ${fS(f)} y sobró ${fS(so)}, neto ${fS(f+so)}. Un clic en un conteo abre sus líneas al costado.`;
    const filas=[...por].sort((a,b)=>a[1].neto-b[1].neto).map(([i,a])=>`<button class="dc-fi${uno===i?' on':''}" data-a="areauna" data-v="${i}"><span class="n" title="${esc(P.dic.area[i])}">${esc(P.dic.area[i]||'Sin área')}</span><small>${esc(nN(a.n,'conteo'))}</small><b class="${a.neto<-EPS?'rojo':''}">${esc(fS(a.neto))}</b></button>`).join('');
    return`<div class="dc-fcab"><div class="dc-ftit"><span class="dc-miga">${esc(s.areas?nN(s.areas.length,'área'):'Todas las áreas')}</span><h3>${esc(tit)}</h3><span class="dc-miga">${esc(`${nN(rs.length,'línea')} · neto ${fS(f+so)}`)}</span></div>${ampB(s,'panel','el resumen')}</div><p class="dc-frase">${esc(fr)}</p><div class="dc-bloque">Por área</div><div class="dc-lista" data-lista="panel">${filas}</div>`;}
  function nivel2(G,n,nL){const{s}=G,como=s.como?`<div class="dc-pop-como" role="dialog"><p>Las líneas de ajuste de los meses elegidos, con cantidades y soles del Almacén, sin redondear.</p><dl>`
      +'<dt>Conteo</dt><dd>Una fecha × un área: lo que esa área registró ese día. La sesión dice a qué cierre o parcial pertenece.</dd>'
      +'<dt>Ajuste</dt><dd>Stock declarado (lo contado) menos stock al cierre (lo que decía el sistema). Negativo es faltante.</dd>'
      +'<dt>Precio prom.</dt><dd>Ajuste valorizado ÷ ajuste; sin ajuste, valorizado total ÷ stock declarado.</dd>'
      +'<dt>Mes</dt><dd>El del cierre: lo registrado del 1 al 7 cuenta en el mes anterior, salvo que «Mes del cierre» diga registro.</dd>'
      +'<dt>Indicadores</dt><dd>Filtran las líneas. Con una búsqueda, cuentan sólo lo que coincide; la ficha muestra el conteo entero.</dd></dl><p>Es un cálculo propio, no un estándar.</p></div>':'';
    return`<div class="dc-n2"><div class="dc-tabs" role="tablist">${[['Conteos',`Conteos · ${n.toLocaleString('en-US')}`],['Líneas',`Líneas · ${nL.toLocaleString('en-US')}`],['Tabla dinámica','Tabla dinámica']].map(([k,t])=>`<button role="tab" data-a="modo" data-v="${k}" class="${s.modo===k?'on':''}" aria-selected="${s.modo===k}">${esc(t)}</button>`).join('')}</div>`
      +`<div class="dc-n2-der"><label class="dc-switch"><input type="checkbox" data-a="det" role="switch"${s.det?' checked':''}>Detalle</label><span class="dc-como"><button class="dc-link" data-a="como" aria-expanded="${!!s.como}">Cómo se calcula</button>${como}</span></div></div>`;}
  function pasarFecha(G){const fb=document.querySelector('.st-key-ajh_nativa_fecha'),lg=G.root.querySelector('.dc-lugar');if(!fb)return;
    const ver=!!(lg&&lg.offsetWidth);if(fb.style.visibility!==(ver?'':'hidden'))fb.style.visibility=ver?'':'hidden';if(!ver||!fb.offsetWidth)return;
    const w=`${fb.offsetWidth+8}px`;if(G.root.style.getPropertyValue('--dc-fecha')!==w)G.root.style.setProperty('--dc-fecha',w);
    const padre=fb.offsetParent;if(!padre)return;const a=lg.getBoundingClientRect(),b=padre.getBoundingClientRect();
    const x=`${Math.round(a.left-b.left)}px`,y=`${Math.round(a.top-b.top+(a.height-fb.offsetHeight)/2)}px`;if(fb.style.left!==x)fb.style.left=x;if(fb.style.top!==y)fb.style.top=y;}
  let G0=null;
  function pintar(G){const{P,s,root}=G;G0=G;G.D=calcular(P,s,G.cache);const D=G.D;if(!D.ficha)s.conteo=null;
    root.classList.toggle('amp',!!s.amp);root.classList.toggle('det',!!s.det);
    const inp=root.querySelector('[data-input=q]:focus'),fc=inp?[inp.selectionStart,inp.selectionEnd]:null;
    const pos=G.resetScroll?[]:[...root.querySelectorAll('[data-tabla]')].map(e=>[e.dataset.tabla,e.scrollTop,e.scrollLeft]);G.resetScroll=false;G.tablas={};
    const piv=s.modo==='Tabla dinámica',verIzq=s.amp!=='panel',verPanel=s.amp!=='izq'&&(!piv||!!D.ficha||s.amp==='panel');
    const chips=[...(s.areas?.length===1?[`<button class="dc-quita" data-a="areauna" data-v="${s.areas[0]}">${esc(P.dic.area[s.areas[0]])} ✕</button>`]:[]),...(s.kpi!=='todos'?[`<button class="dc-quita" data-a="kpi" data-v="${s.kpi}">${esc({falta:'Faltantes',sobra:'Sobrantes',grande:'De S/ 100 o más'}[s.kpi])} ✕</button>`]:[])].join('');
    let h=`<section class="dc-card dc-main">${nivel2(G,D.conteos.length,D.rs.length)}<div class="dc-cab"><span class="dc-lugar" aria-hidden="true"></span>${menu(G,'fam','Familias',P.dic.fam,s.fams)}${menu(G,'area','Áreas',P.dic.area,s.areas)}${chips}<span class="dc-esp"></span><input class="dc-busca" data-input="q" type="search" value="${esc(s.q)}" placeholder="Código, producto o área…" aria-label="Buscar líneas"><button class="dc-pil" data-a="excel" ${D.rs.length?'':'disabled'} title="Baja lo que se ve">Excel ↓</button></div><div class="dc-kpis">${kpisHtml(G)}</div><div class="dc-cuerpo" data-amp="${s.amp||''}">`;
    if(verIzq){h+=`<div class="dc-izq${!verPanel?' full':''}"><div class="dc-fl"><span class="dc-esp"></span>`
        +(piv?`<select class="dc-men" data-select="metrica" aria-label="Qué se suma">${METRICAS.map(m=>op(m,m,s.metrica)).join('')}</select><button class="dc-pil" data-a="config" aria-expanded="${s.config}">Configurar tabla ${s.config?'▴':'▾'}</button>`:'')
        +ampB(s,'izq',piv?'la tabla':'la lista')+'</div>';
      if(piv)h+=`${s.config?configuracion(G):''}${tablaPivot(G)}<p class="dc-nota">La cantidad sólo suma una misma unidad; si se mezclan, va «—».</p>`;
      else h+=`${tablaLista(G,s.modo==='Conteos'?'conteos':'lineas',colsLista(G,s.modo),s.modo==='Conteos'?D.conteos:lineasTabla([...D.rs].sort((a,b)=>b.f-a.f||a.val-b.val),P))}<p class="dc-nota">${s.modo==='Líneas'?'En rojo, lo que faltó; en verde, lo que sobró. «Detalle» suma familia, stocks y precio. ':''}Un clic abre el conteo al costado.</p>`;
      h+='</div>';}
    if(verPanel)h+=`<aside class="dc-panel" aria-label="Ficha">${D.ficha?fichaHtml(G):resumenHtml(G)}</aside>`;
    h+='</div></section>';
    root.innerHTML=h;pos.forEach(([id,t,l])=>{const e=root.querySelector(`[data-tabla="${id}"]`);if(e){e.scrollTop=t;e.scrollLeft=l;}});
    G.ro?.disconnect();const cfg=root.querySelector('.dc-config'),main=root.querySelector('.dc-main');
    if(cfg){const ub=()=>{if(window.innerWidth<=900){cfg.style.top='';cfg.style.maxHeight='';return;}const b=root.querySelector('[data-a=config]').getBoundingClientRect(),m=main.getBoundingClientRect(),top=b.bottom-m.top+6;cfg.style.top=top+'px';cfg.style.maxHeight=Math.max(100,m.height-top-18)+'px';};G.ro=new ResizeObserver(ub);G.ro.observe(main);ub();}
    if(fc){const e=root.querySelector('[data-input=q]');e.focus({preventScroll:true});e.setSelectionRange(...fc);}
    pasarFecha(G);}
  function exportar(G){const{P,s,D}=G,hoja=(nombre,cols,rs)=>({nombre,cabeza:cols.map(c=>c[1]),decimales:6,filas:rs.map(r=>cols.map(([k])=>r[k]??''))});
    const todas=[['fecha','Fecha'],['sesion','Sesión'],['cod','Código'],['famN','Familia'],['subN','Subfamilia'],['prod','Producto'],['umN','Unidad'],['areaN','Área'],['precio','Precio prom.'],['sis','Stock al cierre'],['dif','Ajuste'],['fis','Stock declarado'],['val','Ajuste valorizado'],['stock','Valorizado total']];
    const ls=lineasTabla(D.rs,P).map((r,i)=>({...r,sesion:P.sesiones[D.rs[i].f],umN:P.dic.um[D.rs[i].um]}));
    const cab=[...s.filas,...D.piv.columnas.map(ck=>s.columnas.length?rot(ck,s.columnas[0],P):s.metrica),...(s.columnas.length?['Total']:[])];
    const fp=aplanar(G,true).map(n=>[...n.camino.map((v,i)=>i===n.camino.length-1?nombreNodo(n,P):rot(v,s.filas[i],P)),...D.piv.columnas.map(ck=>valor(n.celdas.get(ck),s.metrica)),...(s.columnas.length?[valor(n.total,s.metrica)]:[])]);
    const ctx=[['Vista','Ajuste · Detalle histórico'],...Object.entries(P.contexto),['Indicador',s.kpi],['Buscar',s.q],['Familias',s.fams?s.fams.map(i=>P.dic.fam[i]).join(', ')||'Ninguna':'Todas'],['Áreas',s.areas?s.areas.map(i=>P.dic.area[i]).join(', ')||'Ninguna':'Todas'],['Tabla dinámica',`${s.filas.join(' → ')||'Total'} × ${s.columnas.join('')||'—'} · ${s.metrica}`]];
    const hojas=[hoja('Conteos',colsLista({s:{det:true}},'Conteos'),D.conteos),hoja('Líneas',todas,ls),{nombre:'Tabla dinámica',cabeza:cab,decimales:6,filas:fp},{nombre:'Contexto',cabeza:['Dato','Selección'],decimales:6,filas:ctx}];
    if(D.ficha)hojas.push(hoja('Conteo elegido',todas,lineasTabla(D.ficha,P).map((r,i)=>({...r,sesion:P.sesiones[D.ficha[i].f],umN:P.dic.um[D.ficha[i].um]}))));return hojas;}
  function montar({data:P,parentElement}){const old=window.__ajHist;old?.abort.abort();old?.ro?.disconnect();let root=parentElement.querySelector('.dc');if(!root){root=document.createElement('div');root.className='dc ajh';parentElement.appendChild(root);}
    const s=old?.s||inicial();if(s.det==null)s.det=!!leerLS('aj_hist_det',false);if(old&&old.P.sello!==P.sello){s.abiertos=[];s.conteo=null;s.fams=null;s.areas=null;}
    const G={P,s,root,cache:{},abort:new AbortController(),tablas:{}};window.__ajHist=G;const signal=G.abort.signal;
    const lista=m=>m==='fam'?'fams':'areas',ids=m=>[...new Set(G.cache.base.map(l=>m==='fam'?l.fam:l.area))];
    root.addEventListener('click',e=>{const b=e.target.closest('[data-a]');
      if(!b&&s.como&&!e.target.closest?.('.dc-como')){s.como=false;pintar(G);return;}
      if(b&&b.dataset.a==='det'){s.det=!!b.checked;guardarLS('aj_hist_det',s.det);pintar(G);return;}
      if(!b||b.disabled||b.matches('input'))return;const{a,v,id,eje,i,dir}=b.dataset;
      if(a!=='como')s.como=false;
      if(a==='como')s.como=!s.como;
      else if(a==='modo'){s.modo=v;s.orden=null;G.resetScroll=true;}else if(a==='config')s.config=!s.config;
      else if(a==='kpi'){s.kpi=s.kpi===v?'todos':v;s.conteo=null;G.resetScroll=true;}
      else if(a==='amp')s.amp=s.amp===v?null:v;
      else if(a==='menu')s.menu=s.menu===v?null:v;
      else if(a==='todas'){s[lista(v)]=null;G.resetScroll=true;}else if(a==='ninguna'){s[lista(v)]=[];G.resetScroll=true;}
      else if(a==='areauna'){const n=+v;s.areas=s.areas?.length===1&&s.areas[0]===n?null:[n];s.conteo=null;G.resetScroll=true;}
      else if(a==='conteo'){s.conteo=s.conteo===v?null:v;if(s.amp==='izq')s.amp=null;}
      else if(a==='cerrar'){s.conteo=null;if(s.amp==='panel')s.amp=null;}
      else if(a==='abrir')s.abiertos=s.abiertos.includes(v)?s.abiertos.filter(x=>x!==v):[...s.abiertos,v];
      else if(a==='plegar')s.abiertos=[];else if(a==='mascols')s.nCols+=12;
      else if(a==='restaurar'){Object.assign(s,{filas:['Familia','Producto'],columnas:['Mes'],metrica:'Ajuste valorizado',abiertos:[],nCols:12,orden:null});}
      else if(a==='quitar'){s[eje]=s[eje].filter(f=>f!==v);s.abiertos=[];s.orden=null;}
      else if(a==='mover'){const x=+i,y=x+(+dir);[s.filas[x],s.filas[y]]=[s.filas[y],s.filas[x]];s.abiertos=[];}
      else if(a==='orden'){const o=s.orden;s.orden={id,k:v,d:o?.id===id&&o.k===v?-o.d:(['falta','neto','val'].includes(v)?1:-1)};G.resetScroll=true;}
      else if(a==='sortpivot'){const o=s.orden,col=v==='~total'?null:v;s.orden={id:'pivot',col,d:o?.id==='pivot'&&o.col===col?-o.d:1};}
      else if(a==='excel'){bajar('Ajuste_detalle_historico.xlsx',libro(exportar(G)));return;}
      else return;
      pintar(G);},{signal});
    root.addEventListener('input',e=>{if(e.target.dataset.input==='q'){s.q=e.target.value;G.resetScroll=true;pintar(G);}},{signal});
    root.addEventListener('change',e=>{const t=e.target;
      if(t.dataset.a==='chk'){const k=lista(t.dataset.m),todo=ids(t.dataset.m),act=new Set(s[k]??todo),n=+t.value;if(t.checked)act.add(n);else act.delete(n);s[k]=act.size===todo.length?null:[...act];s.conteo=null;G.resetScroll=true;}
      else if(t.dataset.select){s[t.dataset.select]=t.value;s.orden=null;}
      else if(t.dataset.add){if(!t.value)return;const f=t.value,e2=t.dataset.add;if(e2==='columnas')s.columnas=[f];else s.filas=[...s.filas,f];s.abiertos=[];s.orden=null;s.nCols=12;}
      else return;pintar(G);},{signal});
    root.addEventListener('keydown',e=>{const el=e.target.closest('tr[data-a]');if(el&&(e.key==='Enter'||e.key===' ')){e.preventDefault();el.click();}},{signal});
    root.addEventListener('scroll',e=>{const el=e.target,id=el.dataset?.tabla,t=G.tablas[id];if(t&&el.scrollTop+el.clientHeight>=el.scrollHeight-160&&t.n<t.rs.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',id==='pivot'?cuerpoPivot(G,t.n,t.n+150):filasLista(G,id,t.n,t.n+150));t.n+=150;}},{signal,capture:true});
    // Con `click` y no `pointerdown`: redibujar al apretar dejaba el clic (Excel, un
    // indicador) sobre un botón que ya no existe.
    document.addEventListener('click',e=>{if(!s.menu||e.composedPath().some(n=>n.classList?.contains('dc-ms')))return;s.menu=null;pintar(G);},{signal});
    // Esc se escucha en el document: el redibujo se lleva el foco (#778).
    document.addEventListener('keydown',e=>{if(e.key!=='Escape'||!root.isConnected)return;if(s.menu)s.menu=null;else if(s.como)s.como=false;else if(s.amp)s.amp=null;else return;pintar(G);},{signal});
    const tick=setInterval(()=>{if(root.isConnected)pasarFecha(G);},400);signal.addEventListener('abort',()=>clearInterval(tick));
    pintar(G);return()=>{G.abort.abort();G.ro?.disconnect();};}
  return{inicial,leer,calcular,pivot,valor,conteos,exportar,montar};
})();
window.__ajHistDatos=AJH;
export default function(component){return AJH.montar(component);}
