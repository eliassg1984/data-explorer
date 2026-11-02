/* Detalle docs. Controles locales; fecha, familias y aviso del ranking releen Python (#726, #773). */
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
  function inicial(v={}){return{modo:'Documentos',kpi:'todos',amp:null,menu:null,gran:'Mes',proveedores:null,q:'',importe:'Todos',doc:null,config:false,
    filas:['Proveedor','Fecha','Documento','Producto'],columnas:['Periodo'],metricas:[{campo:'Valor',aggr:'Suma'}],abiertos:[],orden:null,nCols:12,...v};}
  function leer(P){return P.lineas.map((r,id)=>{const d=P.documentos[r[3]],prov=P.proveedores[r[0]],prod=P.productos[r[1]];
    return{prov:r[0],prod:r[1],fecha:r[2],doc:r[3],q:r[4],v:r[5],pu:r[6],um:r[7],id,igv:r[8]??0,ref:r[9]??null,fl:r[10]??0,fam:r[11]??null,nc:r[12]??0,dentro:true,
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
  function rotulo(v,f,P,s){return f==='Proveedor'?P.proveedores[v][1]:f==='Producto'?P.productos[v]:f==='Fecha'?fecha(v==='~sinfecha'?null:v):f==='Documento'?(P.documentos[v][4]+(P.documentos[v][5]?'':` · línea ${+v+1}`)):f==='Unidad'?(P.unidades[v]||'Sin unidad'):f==='Cantidad'?numero(v):f==='Valor'||f==='Precio informado'?(v==='~sindato'?'Sin dato':'S/ '+numero(v)):mesCorto(P.calendario[s.gran].rotulos[v]||v);}
  const mesCorto=t=>{const m=/^(\d{4})-(\d{2})$/.exec(t);return m?`${['ene','feb','mar','abr','may','jun','jul','ago','set','oct','nov','dic'][+m[2]-1]} ${m[1].slice(2)}`:t;};
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
    return[...m].map(([doc,ls])=>{const d=P.documentos[doc],t=completos.get(doc),af=t.ls.filter(l=>!l.dentro),igv=suma(ls,'igv'),valor=suma(ls,'v');return{doc,key:d[0],provI:d[1],proveedor:P.proveedores[d[1]][1],fecha:P.fechas[d[2]],numero:d[4],raw:d[3],identificado:d[5],tipo:d[6]||'',valor,igv,total:valor+igv,completo:t.valor,lineas:ls.length,todas:t.lineas,productos:new Set(ls.map(l=>l.prod)).size,nfl:ls.filter(l=>l.fl).length,nc:ls.reduce((a,l)=>a+Math.abs(l.nc),0),nAfuera:af.length,vAfuera:suma(af,'v')};})
      .sort((a,b)=>cmp(b.fecha||'',a.fecha||'')||cmp(a.proveedor,b.proveedor)||cmp(a.numero,b.numero));}
  // Las familias del filtro de la página: las líneas de las demás viajan para decir el documento entero.
  function pagSet(P){const pa=P.pagina;if(!pa?.elegidas?.length)return null;const m=new Map(pa.todas.map(x=>[x[0],x[1]]));return new Set(pa.elegidas.map(f=>m.get(f)??f));}
  function calcular(P,s,cache={}){
    if(cache.sello!==P.sello){cache.sello=P.sello;cache.base=leer(P);cache.completos=new Map();const porProv=new Map(),pag=pagSet(P);for(const l of cache.base){l.dentro=!pag||pag.has(P.familias?.[l.fam]);if(!cache.completos.has(l.doc))cache.completos.set(l.doc,[]);cache.completos.get(l.doc).push(l);if(l.dentro)porProv.set(l.prov,(porProv.get(l.prov)||0)+l.v);}cache.rank=[...porProv].sort((a,b)=>b[1]-a[1]).map(([i])=>i);cache.completos=new Map([...cache.completos].map(([doc,ls])=>[doc,{ls,valor:suma(ls,'v'),lineas:ls.length}]));cache.filtro=null;}
    const fk=JSON.stringify([s.proveedores,s.q,s.importe,s.kpi]);
    if(cache.filtro!==fk){const ps=s.proveedores==null?null:new Set(s.proveedores),qs=norm(s.q).split(/\s+/).filter(Boolean);
      cache.alcance=cache.base.filter(l=>l.dentro&&(ps==null||ps.has(P.proveedores[l.prov][0])));
      const rs0=cache.alcance.filter(l=>qs.every(q=>l.buscar.includes(q))&&(s.importe==='Todos'||s.importe==='Positivos'&&l.v>0||s.importe==='Negativos'&&l.v<0||s.importe==='Cero'&&l.v===0)),docs0=listaDocs(rs0,P,cache.completos);
      // Los indicadores se cuentan antes de filtrar por ellos: si no, los otros tres caerían a cero.
      cache.kpis={todos:docs0,guia:docs0.filter(d=>d.tipo.toLowerCase().startsWith('gu')),raro:docs0.filter(d=>d.nfl>0),parcial:docs0.filter(d=>d.nAfuera>0)};
      const ks=s.kpi==='todos'?null:new Set((cache.kpis[s.kpi]||[]).map(d=>d.doc));cache.rs=ks?rs0.filter(l=>ks.has(l.doc)):rs0;cache.docs=ks?docs0.filter(d=>ks.has(d.doc)):docs0;cache.filtro=fk;cache.pk=null;
    }
    const pk=JSON.stringify([fk,s.gran,s.filas,s.columnas]);if(cache.pk!==pk){cache.piv=pivot(cache.rs,P,s);cache.pk=pk;}
    const rs=cache.rs,conNumero=cache.docs.filter(d=>d.identificado),resumen={valor:suma(rs,'v'),documentos:conNumero.length,proveedores:new Set(rs.map(l=>l.prov)).size,
      productos:new Set(rs.map(l=>l.prod)).size,lineas:rs.length,sinNumero:rs.filter(l=>!P.documentos[l.doc][5]).length,sinFecha:rs.filter(l=>P.fechas[l.fecha]==null).length};
    const doc=P.documentos.findIndex(d=>d[0]===s.doc),ficha=doc>=0&&cache.alcance.some(l=>l.doc===doc)?{doc,...cache.completos.get(doc)}:null;
    return{rs,docs:cache.docs,kpis:cache.kpis,resumen,piv:cache.piv,ficha,base:cache.base,alcance:cache.alcance,rank:cache.rank};
  }
  function mover(s,campo,eje,pos){if(!CAMPOS.includes(campo)||!['filas','columnas'].includes(eje))return;
    const viejo=s[eje].indexOf(campo);s.filas=s.filas.filter(f=>f!==campo);s.columnas=s.columnas.filter(f=>f!==campo);
    let i=pos==null?s[eje].length:pos;if(pos!=null&&viejo>=0&&viejo<i)i--;s[eje].splice(Math.max(0,i),0,campo);s.abiertos=[];s.nCols=12;s.orden=null;}
  const op=(v,t,actual)=>`<option value="${esc(v)}" ${v===actual?'selected':''}>${esc(t)}</option>`;
  function filtros(G){const {P,s,D}=G,rank=D.rank.map(i=>({p:P.proveedores[i]}));
    return`<details class="dc-provs"><summary>Proveedores: ${s.proveedores==null?'todos':s.proveedores.length} ▾</summary><div class="dc-popup"><div class="dc-bar">${['Todos','3','5','10','Ninguno'].map(x=>`<button data-a="provtop" data-v="${x}">${x==='3'?'Top 3':x}</button>`).join('')}</div><input data-provq placeholder="Buscar proveedor…" aria-label="Buscar proveedor"><div class="dc-provlista">${rank.map(({p})=>`<label data-provnombre="${esc(norm(p.join(' ')))}"><input type="checkbox" data-prov="${esc(p[0])}" ${s.proveedores==null||s.proveedores.includes(p[0])?'checked':''}>${esc(p[1])}</label>`).join('')}</div></div></details>`;
  }
  function configuracion(G){const s=G.s;
    const eje=e=>`<div class="dc-eje" data-eje="${e}"><b>${e==='filas'?'Filas':'Columnas'}</b><div class="dc-tags">${s[e].map((f,i)=>`<span draggable="true" data-campo="${f}" data-desde="${e}" data-pos="${i}">${f}<button data-a="mover" data-eje="${e}" data-i="${i}" data-dir="-1" aria-label="Subir ${f}" ${i===0?'disabled':''}>↑</button><button data-a="mover" data-eje="${e}" data-i="${i}" data-dir="1" aria-label="Bajar ${f}" ${i===s[e].length-1?'disabled':''}>↓</button><button data-a="quitar" data-eje="${e}" data-v="${f}" aria-label="Quitar ${f}">×</button></span>`).join('')}</div><select data-add="${e}" aria-label="Añadir a ${e}"><option value="">Añadir campo…</option>${CAMPOS.filter(f=>!s[e].includes(f)).map(f=>op(f,f,'')).join('')}</select></div>`;
    return`<div class="dc-config"><p>Arrastrá los campos entre Filas y Columnas o usá las flechas. La fecha de la página permanece compartida con Proveedores.</p>${eje('filas')}${eje('columnas')}<div class="dc-valores"><b>Valores</b>${METRICAS.map(f=>{const m=s.metricas.find(m=>m.campo===f),ags=f==='Precio medio'?['Ponderado']:f==='Precio informado'?['Media','Mínimo','Máximo','Conteo']:['Suma','Media','Mínimo','Máximo','Conteo'];return`<label><input type="checkbox" data-metrica="${f}" ${m?'checked':''}>${f}<select data-aggr="${f}" aria-label="Cálculo de ${f}" ${m?'':'disabled'}>${ags.map(a=>op(a,a,m?.aggr||ags[0])).join('')}</select></label>`;}).join('')}</div><button data-a="restaurar">Restaurar tabla</button></div>`;
  }
  function columnasLista(modo){return modo==='Documentos'?[['fecha','Fecha'],['proveedor','Proveedor'],['numero','Documento'],['tipo','Tipo'],['valor','Neto visible','v'],['igv','IGV','v'],['total','Total','v'],['completo','Documento completo','v'],['lineas','Líneas visibles','n'],['todas','Líneas completas','n']]:[['fecha','Fecha'],['proveedor','Proveedor'],['numero','Documento'],['producto','Producto'],['unidad','Unidad'],['q','Cantidad','n'],['pu','Precio informado','v'],['medio','Valor / cantidad','v'],['v','Valor','v']];}
  function lineasTabla(rs,P){return rs.map(l=>{const medio=l.q>0?l.v/l.q:null,u=P.unidades[l.um]||'';return{key:P.documentos[l.doc][0],fecha:P.fechas[l.fecha],proveedor:P.proveedores[l.prov][1],numero:P.documentos[l.doc][4],producto:P.productos[l.prod],unidad:u||'Sin unidad',cantTxt:`${numero(l.q)}${u?` ${u.toLowerCase()}`:''}`,q:l.q,pu:l.pu,medio,vsHab:medio!=null&&l.ref>0?medio/l.ref-1:null,fl:l.fl,fuera:!l.dentro,famN:P.familias?.[l.fam]||'',v:l.v};});}
  // ── La pantalla (regla #773): la lista primero, cuatro indicadores que filtran y la
  // ficha al costado. La tabla dinámica es una pestaña, con todo lo que tenía.
  const f2=v=>v==null||!isFinite(v)?'—':nf.format(v);
  const fS=v=>v==null||!isFinite(v)?'—':`${v<-.5?'−':''}S/ ${Math.round(Math.abs(v)).toLocaleString('en-US')}`;
  const fS2=v=>v==null||!isFinite(v)?'—':`${v<0?'−':''}S/ ${nf.format(Math.abs(v))}`;
  const fP=x=>x==null||!isFinite(x)?'—':Math.abs(x)<.0005?'0 %':`${x>0?'+':'−'}${Math.abs(x*100).toFixed(Math.abs(x)<.1?1:0)} %`;
  const nN=(n,t)=>`${n.toLocaleString('en-US')} ${t}${n===1?'':t.endsWith('r')?'es':'s'}`;
  const MES=['ene','feb','mar','abr','may','jun','jul','ago','set','oct','nov','dic'];
  function fCorta(v,P){if(!v)return'Sin fecha';const[y,m,d]=v.split('-'),varios=P&&new Set(P.fechas.filter(Boolean).map(f=>f.slice(0,4))).size>1;return`${+d} ${MES[+m-1]}${varios?` ${y.slice(2)}`:''}`;}
  const tipoGuia=t=>String(t||'').toLowerCase().startsWith('gu');
  function colsPantalla(s){if(s==='ficha')return[['producto','Producto','','l'],['cantTxt','Cant.','w-x','r'],['medio','Precio','w-pr','v'],['vsHab','Vs. hab.','w-pc','p'],['v','Valor','w-im','v']];
    const amp=!!G0?.s.det;if(s==='Documentos')return[['fecha','Fecha','w-fe','f'],['numero','Documento','w-do','l'],['proveedor','Proveedor','','m'],['lineas','Líneas','w-pc','n'],['valor','Neto','w-im','v'],...(amp?[['igv','IGV','w-im','v'],['total','Total','w-im','v']]:[])];
    return[['fecha','Fecha','w-fe','f'],...(amp?[['numero','Documento','w-do','l']]:[]),['producto','Producto','','l'],['proveedor','Proveedor','w-pv','l'],['cantTxt','Cantidad','w-x','r'],['medio','Precio','w-pr','v'],['vsHab','Vs. hab.','w-pc','p'],['v','Valor','w-im','v']];}
  let G0=null;
  function celda(r,c,P){const[k,,,t]=c,v=r[k];
    if(t==='f')return`<td class="l">${esc(fCorta(v,P))}</td>`;
    if(t==='n')return`<td>${v==null?'—':Number(v).toLocaleString('en-US')}</td>`;
    if(t==='v')return`<td class="${k==='valor'||k==='v'?'fuerte':''}${k==='medio'&&r.fl?' nar':''}">${f2(v)}</td>`;
    if(t==='p')return r.fuera?'<td></td>':`<td class="${r.fl?'nar':v==null?'':v>.005?'rojo':v<-.005?'verde':''}" title="Contra su precio habitual">${r.fl?'revisar':fP(v)}</td>`;
    if(t==='r')return`<td>${esc(v)}</td>`;
    if(t==='m'){const mar=[];if(r.tipo&&r.tipo!=='Factura')mar.push(`<span class="dc-chip" title="${esc(tipoGuia(r.tipo)?'Guía sin factura: todavía no lleva IGV':r.tipo)}">${esc(tipoGuia(r.tipo)?'Guía':String(r.tipo).split(' ')[0])}</span>`);if(r.nc>.005)mar.push(`<span class="dc-chip" title="Tiene una nota de crédito restada: ${esc(fS(r.nc))}">NC</span>`);if(r.nfl)mar.push(`<span class="dc-chip nar" title="${r.nfl} ${r.nfl===1?'línea':'líneas'} con precio raro">Precio</span>`);if(r.nAfuera)mar.push(`<span class="dc-chip lav" title="${r.nAfuera} ${r.nAfuera===1?'línea más':'líneas más'} en otras familias: ${esc(fS(r.vAfuera))}">+${r.nAfuera}</span>`);
      return`<td class="l" title="${esc(v)}"><span class="dc-prov">${esc(v)}</span>${mar.join('')}</td>`;}
    return`<td class="l" title="${esc(v)}">${esc(v)}</td>`;}
  function tablaLista(G,id,cols,filas,conTotal=true){let rs=filas.slice();const o=G.s.orden;if(o?.id===id)rs.sort((a,b)=>{const x=a[o.k],y=b[o.k];return x==null?y==null?0:1:y==null?-1:(typeof x==='number'?x-y:cmp(x,y))*o.d;});
    G.tablas[id]={cols,rs,n:150};
    const tot=c=>['lineas','valor','igv','total','v'].includes(c[0])?`<td>${c[0]==='lineas'?suma(rs,c[0]).toLocaleString('en-US'):f2(suma(rs,c[0]))}</td>`:'<td></td>',primero=cols[0][1]==='Fecha'?`Total · ${id==='docs'?nN(rs.length,'documento'):nN(rs.length,'línea')}`:'Total';
    return`<div class="dc-scroll" data-tabla="${id}" tabindex="0"><table class="dc-t"><thead><tr>${cols.map(([k,t,w,c])=>`<th class="${w} ${['l','m','f'].includes(c)?'l':''}"><button data-a="orden" data-id="${id}" data-v="${k}">${esc(t)}${o?.id===id&&o.k===k?o.d===1?' ↑':' ↓':''}</button></th>`).join('')}</tr></thead><tbody>${conTotal?`<tr class="tot"><td class="l" colspan="${Math.max(1,cols.findIndex(c=>['lineas','cantTxt'].includes(c[0])))}">${primero}</td>${cols.slice(Math.max(1,cols.findIndex(c=>['lineas','cantTxt'].includes(c[0])))).map(tot).join('')}</tr>`:''}${filasLista(G,id,0,150)}</tbody></table>${rs.length?'':'<p class="dc-vacio">No hay registros con estos filtros. Cambiá la búsqueda o elegí Todos.</p>'}</div>`;
  }
  function filasLista(G,id,a,b){const t=G.tablas[id],P=G.P;return t.rs.slice(a,b).map(r=>`<tr ${id==='ficha'?'':`data-a="doc" data-v="${r.key}" tabindex="0"`} class="${r.key===G.s.doc&&id!=='ficha'?'on':''}${r.fuera?' tenue':''}"${r.fuera?` title="${esc(`Familia fuera del filtro: ${r.famN}`)}"`:''}>${t.cols.map(c=>celda(r,c,P)).join('')}</tr>`).join('');}
  function ordenarNodos(n,G){const {s,P}=G,os=s.orden,rs=[...n.hijos.values()];return rs.sort((a,b)=>{if(os?.id==='pivot'&&os.metric!=null){const x=valor(os.col==null?a.total:a.celdas.get(os.col),s.metricas[os.metric],P),y=valor(os.col==null?b.total:b.celdas.get(os.col),s.metricas[os.metric],P);if(x==null||y==null)return x==null?(y==null?0:1):-1;return(x-y)*os.d||comparar(a.val,b.val,a.campo,P,s);}return comparar(a.val,b.val,a.campo,P,s)*(os?.id==='pivot'&&os.metric==null?os.d:1);});}
  function aplanar(G,todo=false){const rs=[],ab=new Set(G.s.abiertos);const visitar=n=>{for(const h of ordenarNodos(n,G)){if(!todo||!h.hijos.size)rs.push(h);if(todo||ab.has(h.id))visitar(h);}};if(!G.s.filas.length)return[G.D.piv.raiz];visitar(G.D.piv.raiz);return rs;}
  const nombreM=m=>`${m.campo} · ${m.aggr}`;
  function fmtM(v,m){return m.aggr==='Conteo'||m.campo==='Cantidad'?numero(v):money(v);}
  function cuerpoPivot(G,a,b){const t=G.tablas.pivot;return t.rs.slice(a,b).map(n=>{const {s,P}=G,hojas=n.hijos.size,ab=s.abiertos.includes(n.id),nombre=n.campo?rotulo(n.val,n.campo,P,s):'Total',boton=hojas?`<button data-a="abrir" data-v="${esc(n.id)}" aria-label="${ab?'Contraer':'Expandir'} ${esc(nombre)}" aria-expanded="${ab}">${ab?'▾':'▸'}</button>`:'';
    return`<tr><td class="dc-nombre"><div style="padding-left:${Math.max(0,n.prof-1)*12}px">${boton}<span title="${esc(nombre)}">${esc(nombre)}</span>${n.campo==='Documento'?`<button data-a="doc" data-v="${P.documentos[n.val][0]}" aria-label="Ver documento ${esc(nombre)}">↗</button>`:''}</div></td>${t.cols.map(([ck])=>s.metricas.map(m=>{const v=valor(n.celdas.get(ck),m,P);return`<td class="num" title="${v==null?'Sin dato o unidades/productos no comparables':numero(v)}">${fmtM(v,m)}</td>`;}).join('')).join('')}${t.total?s.metricas.map(m=>`<td class="num dc-total">${fmtM(valor(n.total,m,P),m)}</td>`).join(''):''}</tr>`;}).join('');}
  // Con un solo período, la columna Total repite la de al lado: no se dibuja. El Excel la conserva.
  function tablaPivot(G){const {s,P,D}=G,cols=D.piv.columnas.slice(0,s.nCols),total=s.columnas.length>0&&D.piv.columnas.length>1,rs=aplanar(G),o=s.orden;G.tablas.pivot={cols,rs,n:150,total};
    const header=(rot,ck)=>s.metricas.map((m,i)=>`<th><button data-a="sortpivot" data-v="${esc(ck??'~total')}" data-i="${i}" title="${esc(nombreM(m))}">${esc(rot)}<small>${esc(nombreM(m))}${o?.id==='pivot'&&o.col===ck&&o.metric===i?o.d===1?' ↑':' ↓':''}</small></button></th>`).join('');
    return`<div class="dc-pivot-info"><span>${rs.length} filas desplegadas · ${cols.length}/${D.piv.columnas.length} grupos de columnas</span>${cols.length<D.piv.columnas.length?'<button class="dc-pil" data-a="mascols">Más columnas</button>':''}<button class="dc-pil" data-a="plegar">Contraer todo</button></div><div class="dc-scroll" data-tabla="pivot" tabindex="0"><table class="dc-p"><thead><tr><th class="dc-nombre"><button data-a="sortnombre">${esc(s.filas.join(' / ')||'Total')}</button></th>${cols.map(([ck,vs])=>header(vs.map((v,i)=>rotulo(v,s.columnas[i],P,s)).join(' / ')||'Selección',ck)).join('')}${total?header('Total',null):''}</tr></thead><tbody>${cuerpoPivot(G,0,150)}</tbody><tfoot><tr><th class="dc-nombre">Total de lo elegido</th>${cols.map(([ck])=>s.metricas.map(m=>`<td class="num">${fmtM(valor(D.piv.raiz.celdas.get(ck),m,P),m)}</td>`).join('')).join('')}${total?s.metricas.map(m=>`<td class="num">${fmtM(valor(D.piv.raiz.total,m,P),m)}</td>`).join(''):''}</tr></tfoot></table>${rs.length?'':'<p class="dc-vacio">No hay registros. Los filtros y la fecha siguen disponibles.</p>'}</div>`;
  }
  function menuFamilias(G){const{P,s}=G,pa=P.pagina;if(!pa?.todas?.length)return'';const el=new Set(pa.elegidas),n=pa.elegidas.length||pa.todas.length,ab=s.menu==='fam';
    return`<div class="dc-ms"><button class="dc-pil" data-a="menu" data-v="fam" aria-expanded="${ab}">${n===pa.todas.length?'Todas las familias':`Familias: ${n} de ${pa.todas.length}`} ▾</button>${ab?`<div class="dc-pop">${pa.todas.map(([r,nom,v])=>`<label><input type="checkbox" data-a="pfam" value="${esc(r)}"${el.has(r)||!el.size?' checked':''}><span>${esc(nom)}</span><small>${esc(fS(v))}</small></label>`).join('')}<p>Vale para todas las vistas de Compras.</p></div>`:''}</div>`;}
  function kpisHtml(G){const{D,s}=G,K=D.kpis,k=(id,rot,val,sub,tip,cls='')=>`<button class="dc-kpi${s.kpi===id?' on':''}" data-a="kpi" data-v="${id}" aria-pressed="${s.kpi===id}" title="${esc(tip)}"><span class="r">${esc(rot)}</span><span class="v ${cls}">${esc(val)}</span><span class="d">${esc(sub)}</span></button>`,sV=a=>suma(a,'valor');
    return k('todos','Documentos',K.todos.length.toLocaleString('en-US'),`${fS(sV(K.todos))} sin IGV · ${nN(new Set(K.todos.map(d=>d.provI)).size,'proveedor')}`,'Todos los documentos del rango y de los filtros.')
      +k('guia','Guías sin factura',K.guia.length.toLocaleString('en-US'),`${fS(sV(K.guia))} que todavía no llevan IGV`,'Mercadería que entró con guía y aún no tiene su factura.')
      +k('raro','Con precio raro',K.raro.length.toLocaleString('en-US'),`${fS(sV(K.raro))} · ${nN(suma(K.raro,'nfl'),'línea')} para revisar`,'Una línea de S/ 50 o más a 2,5 veces su habitual o a menos de 0,4, o con decimales en una unidad entera.',K.raro.length?'nar':'')
      +k('parcial','Con líneas afuera',K.parcial.length.toLocaleString('en-US'),`${fS(suma(K.parcial,'vAfuera'))} en familias fuera del filtro`,'Documentos que además tienen líneas en otras familias: el total de la tabla no las cuenta.');}
  function fichaHtml(G){const{P,D,s}=G,F=D.ficha,d=P.documentos[F.doc],dentro=F.ls.filter(l=>l.dentro),afuera=F.ls.filter(l=>!l.dentro),v=suma(dentro,'v'),igv=suma(dentro,'igv'),va=suma(afuera,'v'),tipo=d[6]||'Documento',guia=tipoGuia(tipo),nfl=dentro.filter(l=>l.fl).length,nc=dentro.reduce((a,l)=>a+Math.abs(l.nc),0),proc=d[7]||'';
    const cif=(r,x,y,c='')=>`<div class="dc-cf"><span>${esc(r)}</span><b class="${c}">${esc(x)}</b><small>${esc(y)}</small></div>`,fr=[];
    if(afuera.length)fr.push(`Tiene ${afuera.length} ${afuera.length===1?'línea más':'líneas más'} en familias fuera del filtro, por ${fS(va)}: el documento entero suma ${fS2(v+va)} sin IGV.`);if(guia)fr.push('Guía: todavía no lleva IGV; lo trae la factura.');if(nc>.005)fr.push(`Ya tiene restada una nota de crédito de ${fS(nc)}.`);
    const emit=fCorta(P.fechas[d[2]],P),ingreso=proc?`· ingresada el ${fCorta(proc.slice(0,10),P)} a las ${proc.slice(11,16)}`:'';
    return`<div class="dc-fcab"><div class="dc-ftit"><span class="dc-miga">${esc(P.proveedores[d[1]][1])}</span><h3 title="${esc(d[4])}">${esc(d[5]?d[4]:'Línea sin número')}</h3><span class="dc-miga">${esc(`${tipo} · emitida el ${emit} ${ingreso}`)}</span></div>${ampB(s,'panel','la ficha')}<button class="dc-quita" data-a="cerrar">Soltar</button></div>
      <div class="dc-cifras">${cif('Neto',fS2(v),nN(dentro.length,'línea'))}${cif('IGV',guia?'—':fS2(igv),guia?'la guía no lo lleva':'')}${cif('Total',fS2(v+igv),afuera.length?'sólo lo que entra en el filtro':'lo que dice el papel')}${cif('Precios raros',String(nfl),nfl?'no entran en los precios':'',nfl?'nar':'')}</div>
      ${fr.length?`<p class="dc-frase">${esc(fr.join(' '))}</p>`:''}${tablaLista(G,'ficha',colsPantalla('ficha'),lineasTabla([...dentro,...afuera],P),false)}`;}
  function resumenHtml(G){const{P,D,s}=G,docs=D.docs,v=suma(docs,'valor'),igv=suma(docs,'igv'),nF=docs.filter(d=>d.tipo==='Factura').length,nG=docs.filter(d=>tipoGuia(d.tipo)).length,may=[...docs].sort((a,b)=>b.valor-a.valor)[0];
    const fr=s.kpi==='guia'?'Mercadería que entró con guía: todavía no lleva IGV y aparece en las compras sin factura. Cuando llega la factura, el documento cambia.':s.kpi==='raro'?'Cada uno tiene alguna línea a un precio muy lejos de su habitual, o con decimales en una unidad que se cuenta entera. Suelen ser errores de tipeo o de unidad: esas líneas no entran en ningún precio.':s.kpi==='parcial'?'Estos documentos también tienen líneas en familias fuera del filtro. La lista muestra sólo la parte que entra; la ficha, el documento entero.':
      `${nN(nF,'factura')}${nG?` y ${nN(nG,'guía')}`:''} por ${fS(v)} sin IGV y ${fS(v+igv)} con IGV.${may?` El más grande: ${may.proveedor}, ${may.numero}, ${fS(may.valor)}.`:''}`;
    const tit={todos:'Qué hay en estos documentos',guia:'Guías sin factura',raro:'Documentos con precio raro',parcial:'Documentos con líneas afuera'}[s.kpi],por=new Map();for(const d of docs){const a=por.get(d.provI)||{n:0,v:0};a.n++;a.v+=d.valor;por.set(d.provI,a);}
    const uno=s.proveedores?.length===1?s.proveedores[0]:null,filas=[...por].sort((a,b)=>b[1].v-a[1].v).map(([i,a])=>`<button class="dc-fi${uno===P.proveedores[i][0]?' on':''}" data-a="provuno" data-v="${esc(P.proveedores[i][0])}"><span class="n" title="${esc(P.proveedores[i][1])}">${esc(P.proveedores[i][1])}</span><small>${esc(nN(a.n,'documento'))}</small><b>${esc(fS(a.v))}</b></button>`).join('');
    const pa=P.pagina,el=new Set(pa?.elegidas||[]),fuera=pa&&el.size?pa.todas.filter(x=>!el.has(x[0])).sort((a,b)=>b[2]-a[2]):[],sF=fuera.reduce((a,x)=>a+x[2],0);
    return`<div class="dc-fcab"><div class="dc-ftit"><span class="dc-miga">${esc(s.proveedores?nN(s.proveedores.length,'proveedor'):'Todos los proveedores')}${P.rango?` · ${esc(fCorta(P.rango[0],P))} – ${esc(fCorta(P.rango[1],P))}`:''}</span><h3>${esc(tit)}</h3><span class="dc-miga">${esc(`${nN(docs.length,'documento')} · ${fS(v)} sin IGV`)}</span></div>${ampB(s,'panel','el resumen')}</div><p class="dc-frase">${esc(fr)}</p><div class="dc-bloque">Por proveedor</div><div class="dc-lista" data-lista="panel">${filas}</div>${s.kpi==='todos'&&sF>.5?`<div class="dc-fuera"><span>Fuera de esta cuenta: ${esc(fS(sF))} de ${esc(fuera.slice(0,2).map(x=>x[1]).join(', '))}${fuera.length>2?'…':''}</span><button class="dc-quita" data-a="sumar">Sumarlas</button></div>`:''}`;}
  const ICO_AMP='<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4"/></svg>',ICO_VOLVER='<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 2v4H2M14 6h-4V2M10 14v-4h4M2 10h4v4"/></svg>';
  const ampB=(s,cual,rot)=>`<button class="dc-amp" data-a="amp" data-v="${cual}" aria-pressed="${s.amp===cual}" title="${s.amp===cual?'Volver (Esc)':`Ampliar ${rot}`}" aria-label="${s.amp===cual?'Volver':`Ampliar ${rot}`}">${s.amp===cual?ICO_VOLVER:ICO_AMP}</button>`;
  const leerLS=(k,d)=>{try{const v=localStorage.getItem(k);return v==null?d:JSON.parse(v);}catch(e){return d;}},guardarLS=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v));}catch(e){/* sólo esta vez */}};
  function pasarFecha(G){const fb=document.querySelector('.st-key-cp_docs_nativa_fecha'),lg=G.root.querySelector('.dc-lugar');if(!fb)return;
    const ver=!!(lg&&lg.offsetWidth);if(fb.style.visibility!==(ver?'':'hidden'))fb.style.visibility=ver?'':'hidden';if(!ver||!fb.offsetWidth)return;
    const w=`${fb.offsetWidth+8}px`;if(G.root.style.getPropertyValue('--dc-fecha')!==w)G.root.style.setProperty('--dc-fecha',w);
    const padre=fb.offsetParent;if(!padre)return;const a=lg.getBoundingClientRect(),b=padre.getBoundingClientRect();
    const x=`${Math.round(a.left-b.left)}px`,y=`${Math.round(a.top-b.top+(a.height-fb.offsetHeight)/2)}px`;if(fb.style.left!==x)fb.style.left=x;if(fb.style.top!==y)fb.style.top=y;}
  // Nivel 2: cómo ver, y a la derecha «Detalle» y «Cómo se calcula» (#793).
  function nivel2(G,n,nL){const{s}=G,como=s.como?`<div class="dc-pop-como" role="dialog"><p>Los documentos del rango, sin IGV salvo en «Detalle», con las notas de crédito ya restadas.</p><dl>`
      +'<dt>Documentos</dt><dd>Comprobantes distintos; con una búsqueda, las cifras suman sólo las líneas que coinciden y la ficha muestra el documento entero.</dd>'
      +'<dt>Guías sin factura</dt><dd>Guías de remisión que todavía no se canjearon por su factura.</dd>'
      +'<dt>Precio raro</dt><dd>Una compra de S/ 50 o más a 2,5 veces su habitual o a menos de 0,4, o con decimales en una unidad entera.</dd>'
      +'<dt>Líneas afuera</dt><dd>Documentos con líneas de familias que no están en el filtro de la página: la ficha las muestra.</dd>'
      +'<dt>Vs. hab.</dt><dd>El precio de la línea contra el habitual del producto: la mediana de los 90 días anteriores.</dd></dl><p>Es un cálculo propio, no un estándar.</p></div>':'';
    return`<div class="dc-n2"><div class="dc-tabs" role="tablist">${[['Documentos',`Documentos · ${n.toLocaleString('en-US')}`],['Líneas',`Líneas · ${nL.toLocaleString('en-US')}`],['Tabla dinámica','Tabla dinámica']].map(([k,t])=>`<button role="tab" data-a="modo" data-v="${k}" class="${s.modo===k?'on':''}" aria-selected="${s.modo===k}">${esc(t)}</button>`).join('')}</div>`
      +`<div class="dc-n2-der"><label class="dc-switch"><input type="checkbox" data-a="det" role="switch"${s.det?' checked':''}>Detalle</label><span class="dc-como"><button class="dc-link" data-a="como" aria-expanded="${!!s.como}">Cómo se calcula</button>${como}</span></div></div>`;}
  function pintar(G){const {P,s,root}=G;G0=G;G.D=calcular(P,s,G.cache);const D=G.D;
    if(!D.ficha)s.doc=null;root.classList.toggle('amp',!!s.amp);root.classList.toggle('det',!!s.det);
    const input=root.querySelector('[data-input=q]:focus'),f=input?[input.selectionStart,input.selectionEnd]:null;
    const provAbierto=root.querySelector('.dc-provs')?.open,provQ=root.querySelector('[data-provq]')?.value||'';
    const pos=G.resetScroll?[]:[...root.querySelectorAll('[data-tabla]')].map(e=>[e.dataset.tabla,e.scrollTop,e.scrollLeft]),yL=root.querySelector('[data-lista]')?.scrollTop||0;G.resetScroll=false;G.tablas={};
    const piv=s.modo==='Tabla dinámica',verIzq=s.amp!=='panel',verPanel=s.amp!=='izq'&&(!piv||!!D.ficha||s.amp==='panel'),n=D.docs.length,nL=D.rs.length,uno=s.proveedores?.length===1?P.proveedores.find(x=>x[0]===s.proveedores[0])?.[1]:null;
    const chips=[...(uno?[`<button class="dc-quita" data-a="provtop" data-v="Todos">${esc(uno)} ✕</button>`]:[]),...(s.kpi!=='todos'?[`<button class="dc-quita" data-a="kpi" data-v="${s.kpi}">${esc({guia:'Guías sin factura',raro:'Con precio raro',parcial:'Con líneas afuera'}[s.kpi])} ✕</button>`]:[])].join('');
    let h=`<section class="dc-card dc-main">${nivel2(G,n,nL)}<div class="dc-cab"><span class="dc-lugar" aria-hidden="true"></span>${menuFamilias(G)}${filtros(G)}${chips}<span class="dc-esp"></span><input class="dc-busca" data-input="q" type="search" value="${esc(s.q)}" placeholder="Documento, proveedor o producto…" aria-label="Buscar documentos"><button class="dc-pil" data-a="excel" ${!D.rs.length?'disabled':''} title="Baja lo que se ve">Excel ↓</button></div><div class="dc-kpis">${kpisHtml(G)}</div><div class="dc-cuerpo" data-amp="${s.amp||''}">`;
    if(verIzq){h+=`<div class="dc-izq${!verPanel?' full':''}"><div class="dc-fl"><span class="dc-esp"></span>`
        +(piv?`<select class="dc-men" data-select="gran" aria-label="Columnas por período">${P.granos.map(g=>`<option value="${g}"${g===s.gran?' selected':''}>Columnas: ${g}</option>`).join('')}</select><button class="dc-pil" data-a="config" aria-expanded="${s.config}">Configurar tabla ${s.config?'▴':'▾'}</button>`:`<select class="dc-men" data-select="importe" aria-label="Importes">${['Todos','Positivos','Negativos','Cero'].map(x=>`<option value="${x}"${x===s.importe?' selected':''}>Importes: ${x.toLowerCase()}</option>`).join('')}</select>`)
        +ampB(s,'izq',piv?'la tabla':'la lista')+'</div>';
      if(piv)h+=`${s.config?configuracion(G):''}${tablaPivot(G)}<p class="dc-nota">${D.resumen.sinNumero?`${D.resumen.sinNumero} líneas sin número de documento. `:''}Cantidad sólo suma unidades compatibles; los precios requieren un producto y una unidad.</p>`;
      else h+=`${tablaLista(G,s.modo==='Documentos'?'docs':'lineas',colsPantalla(s.modo),s.modo==='Documentos'?D.docs:lineasTabla([...D.rs].sort((a,b)=>b.fecha-a.fecha||b.doc-a.doc),P))}<p class="dc-nota">${s.q?'Con una búsqueda, las cifras suman sólo las líneas que coinciden; la ficha muestra el documento entero. ':'Sin IGV. Las notas de crédito ya están restadas. '}${s.modo==='Líneas'?'En naranja, los precios raros. ':''}Un clic abre el documento al costado.</p>`;
      h+='</div>';}
    if(verPanel)h+=`<aside class="dc-panel" aria-label="Ficha">${D.ficha?fichaHtml(G):resumenHtml(G)}</aside>`;
    h+='</div></section>';
    root.innerHTML=h;pos.forEach(([id,top,left])=>{const e=root.querySelector(`[data-tabla="${id}"]`);if(e){e.scrollTop=top;e.scrollLeft=left;}});const li=root.querySelector('[data-lista]');if(li)li.scrollTop=yL;
    if(provAbierto)root.querySelector('.dc-provs').open=true;if(provQ){root.querySelector('[data-provq]').value=provQ;root.querySelectorAll('[data-provnombre]').forEach(l=>l.hidden=!l.dataset.provnombre.includes(norm(provQ)));}
    G.ro?.disconnect();const cfg=root.querySelector('.dc-config'),main=root.querySelector('.dc-main');
    if(cfg){const ubicar=()=>{if(window.innerWidth<=900){cfg.style.top='';cfg.style.maxHeight='';return;}const b=root.querySelector('[data-a=config]').getBoundingClientRect(),m=main.getBoundingClientRect(),top=b.bottom-m.top+6;cfg.style.top=top+'px';cfg.style.maxHeight=Math.max(100,m.height-top-18)+'px';};G.ro=new ResizeObserver(ubicar);G.ro.observe(main);ubicar();}
    if(f){const e=root.querySelector('[data-input=q]');e.focus({preventScroll:true});e.setSelectionRange(...f);}
    pasarFecha(G);
  }
  function exportar(G){const {P,s,D}=G,hoja=(nombre,cols,rs)=>({nombre,cabeza:cols.map(c=>c[1]),decimales:6,filas:rs.map(r=>cols.map(([k])=>r[k]??''))});
    const docs=hoja('Documentos',columnasLista('Documentos'),G.tablas.docs?.rs||D.docs),ls=hoja('Líneas filtradas',columnasLista('Líneas'),G.tablas.lineas?.rs||lineasTabla(D.rs,P));
    const headers=[...s.filas,...D.piv.columnas.flatMap(([,vs])=>s.metricas.map(m=>(vs.map((v,i)=>rotulo(v,s.columnas[i],P,s)).join(' / ')||'Selección')+' · '+nombreM(m))),...(s.columnas.length?s.metricas.map(m=>'Total · '+nombreM(m)):[])];
    const filas=aplanar(G,true).map(n=>[...n.camino.map((v,i)=>rotulo(v,s.filas[i],P,s)),...D.piv.columnas.flatMap(([ck])=>s.metricas.map(m=>valor(n.celdas.get(ck),m,P))),...(s.columnas.length?s.metricas.map(m=>valor(n.total,m,P)):[])]);
    if(s.filas.length)filas.push(['TOTAL',...s.filas.slice(1).map(()=>''),...D.piv.columnas.flatMap(([ck])=>s.metricas.map(m=>valor(D.piv.raiz.celdas.get(ck),m,P))),...(s.columnas.length?s.metricas.map(m=>valor(D.piv.raiz.total,m,P)):[])]);
    const contexto=[['Vista','Compras · Detalle de documentos'],['Rango compartido con Proveedores',P.rango?.join(' → ')||'Sin rango con fechas'],...Object.entries(P.contexto).map(([k,v])=>[k,v.join(', ')||'Todas']),['Proveedores locales',s.proveedores==null?'Todos los del ranking':s.proveedores.join(', ')||'Ninguno'],['Buscar',s.q],['Importes',s.importe],['Indicador',s.kpi],['Vista activa',s.modo],['Período del pivote',s.gran],['Filas del pivote',s.filas.join(' → ')||'Total'],['Columnas del pivote',s.columnas.join(' → ')||'Sin eje'],['Valores',s.metricas.map(nombreM).join(', ')],['Importe visible',D.resumen.valor],['Documentos con número',D.resumen.documentos],['Líneas sin número',D.resumen.sinNumero],['Líneas sin fecha',D.resumen.sinFecha],['Documentos','Identidad = proveedor + fecha + número original; sin número se conserva cada línea, sin inventar documentos.'],['Ficha','Completa dentro del rango, familias y proveedores cargados. Buscar e Importes no la recortan.'],['Cantidades','Sin suma entre unidades distintas o desconocidas. Los precios agregados requieren un producto y una unidad.'],['Precio informado','Media simple de los precios unitarios de las líneas, como el pivote anterior. No equivale al precio medio ponderado.'],['Precio medio','Valor total / cantidad total positiva de un producto y una unidad.'],['Tabla dinámica','Exporta todos los grupos de columnas y las hojas de la jerarquía, más el total; no duplica subtotales intermedios.'],['Precisión','Valores numéricos con seis decimales. Cantidades y valores se suman sin redondear las líneas.']];
    const hojas=[docs,ls,{nombre:'Tabla dinámica',cabeza:headers,decimales:6,filas},{nombre:'Contexto',cabeza:['Dato','Selección'],decimales:6,filas:contexto}];
    if(D.ficha)hojas.push(hoja('Ficha completa',columnasLista('Líneas'),lineasTabla(D.ficha.ls,P)));return hojas;
  }
  function montar({data:P,parentElement,setTriggerValue}){const old=window.__comprasDocs;old?.abort.abort();old?.ro?.disconnect();let root=parentElement.querySelector('.dc');if(!root){root=document.createElement('div');root.className='dc';parentElement.appendChild(root);}const s=old?.s||inicial(P.inicial);if(s.det==null)s.det=!!leerLS('cp_docs_det',false);G0=null;
    if(old&&old.P.sello!==P.sello){s.abiertos=[];if(old.P.documentos.find(d=>d[0]===s.doc)?.[5]===false)s.doc=null;}
    if(!['Documentos','Líneas','Tabla dinámica'].includes(s.modo))s.modo='Documentos';if(!P.granos.includes(s.gran))s.gran='Mes';
    if(s.proveedores!=null)s.proveedores=s.proveedores.filter(p=>P.proveedores.some(x=>x[0]===p));
    const G={P,s,root,cache:{},abort:new AbortController(),tablas:{},enviar:setTriggerValue};window.__comprasDocs=G;const signal=G.abort.signal;
    G.selloRank=window.__cpProv?.rankData?.sello;
    window.addEventListener('compras-proveedores-cambio',e=>{const d=e.detail;if(!root.isConnected||!G.selloRank||!d||d.sello!==G.selloRank||JSON.stringify(d.rango)!==JSON.stringify(P.rango))return;
      const siguiente=JSON.stringify([...d.sel].sort()),actual=JSON.stringify([...(P.contexto['Proveedores del ranking']||[])].sort());
      if(siguiente===actual||siguiente===G.pedido)return;G.pedido=siguiente;setTriggerValue?.('ranking',{sello:P.sello});
    },{signal});
    const avisarFamilias=()=>{if(G.pagina){const x=G.pagina;G.pagina=null;setTriggerValue?.('familias',x);}};
    root.addEventListener('click',e=>{const b=e.target.closest('[data-a]');
      if(!b&&s.como&&!e.target.closest?.('.dc-como')){s.como=false;pintar(G);return;}
      if(b&&b.dataset.a==='det'){s.det=!!b.checked;guardarLS('cp_docs_det',s.det);pintar(G);return;}
      if(!b||b.disabled||b.matches('input'))return;const {a,v,id,eje,i,dir}=b.dataset;
      if(a!=='como')s.como=false;
      if(a==='como')s.como=!s.como;
      else if(a==='modo'){s.modo=v;s.orden=null;G.resetScroll=true;}else if(a==='config')s.config=!s.config;
      else if(a==='kpi'){s.kpi=s.kpi===v?'todos':v;s.doc=null;G.resetScroll=true;}
      else if(a==='amp'){s.amp=s.amp===v?null:v;}
      else if(a==='provuno'){s.proveedores=s.proveedores?.length===1&&s.proveedores[0]===v?null:[v];s.doc=null;G.resetScroll=true;}
      else if(a==='menu'){s.menu=s.menu===v?null:v;if(!s.menu)avisarFamilias();}
      else if(a==='sumar'){const pa=P.pagina;pa.elegidas=pa.todas.map(x=>x[0]);G.pagina=pa.elegidas.slice();avisarFamilias();}
      else if(a==='provtop'){s.proveedores=v==='Todos'?null:v==='Ninguno'?[]:G.D.rank.slice(0,+v).map(i=>P.proveedores[i][0]);G.resetScroll=true;}
      else if(a==='doc'){s.doc=s.doc===v?null:v;if(s.amp==='izq')s.amp=null;}
      else if(a==='cerrar'){s.doc=null;if(s.amp==='panel')s.amp=null;}
      else if(a==='abrir')s.abiertos=s.abiertos.includes(v)?s.abiertos.filter(x=>x!==v):[...s.abiertos,v];
      else if(a==='plegar')s.abiertos=[];else if(a==='mascols')s.nCols+=12;
      else if(a==='restaurar'){s.filas=['Proveedor','Fecha','Documento','Producto'];s.columnas=['Periodo'];s.metricas=[{campo:'Valor',aggr:'Suma'}];s.abiertos=[];s.nCols=12;s.orden=null;}
      else if(a==='quitar'){s[eje]=s[eje].filter(f=>f!==v);s.abiertos=[];s.orden=null;}
      else if(a==='mover'){const x=+i,y=x+(+dir);[s[eje][x],s[eje][y]]=[s[eje][y],s[eje][x]];s.abiertos=[];s.orden=null;}
      else if(a==='orden'){const o=s.orden;s.orden={id,k:v,d:o?.id===id&&o.k===v?-o.d:1};G.resetScroll=true;}
      else if(a==='sortnombre'){const o=s.orden;s.orden={id:'pivot',metric:null,d:o?.id==='pivot'&&o.metric==null?-o.d:1};}
      else if(a==='sortpivot'){const o=s.orden,col=v==='~total'?null:v;s.orden={id:'pivot',col,metric:+i,d:o?.id==='pivot'&&o.col===col&&o.metric===+i?-o.d:1};}
      else if(a==='excel'){bajar('Compras_detalle_documentos.xlsx',libro(exportar(G)));return;}
      else if(!['provtop','abrir','plegar','mascols','restaurar','quitar','mover','orden','sortnombre','sortpivot'].includes(a))return;
      pintar(G);
    },{signal});
    root.addEventListener('input',e=>{if(e.target.dataset.input==='q'){s.q=e.target.value;G.resetScroll=true;pintar(G);}else if(e.target.hasAttribute('data-provq')){const q=norm(e.target.value);root.querySelectorAll('[data-provnombre]').forEach(l=>l.hidden=!l.dataset.provnombre.includes(q));}},{signal});
    root.addEventListener('change',e=>{const t=e.target,k=t.dataset.select;
      if(k){s[k]=t.value;if(k==='gran'){s.abiertos=[];s.orden=null;}G.resetScroll=true;}
      else if(t.hasAttribute('data-prov')){const p=t.dataset.prov,actual=new Set(s.proveedores??P.proveedores.map(x=>x[0]));if(t.checked)actual.add(p);else actual.delete(p);s.proveedores=actual.size===P.proveedores.length?null:[...actual];G.resetScroll=true;}
      else if(t.dataset.a==='pfam'){const pa=P.pagina,el=pa.elegidas.length?pa.elegidas:pa.todas.map(x=>x[0]);pa.elegidas=t.checked?[...el,t.value]:el.filter(x=>x!==t.value);G.pagina=pa.elegidas.slice();G.cache={};s.doc=null;}
      else if(t.dataset.add){if(!t.value)return;mover(s,t.value,t.dataset.add);}
      else if(t.dataset.metrica){const f=t.dataset.metrica;if(t.checked)s.metricas.push({campo:f,aggr:f==='Precio medio'?'Ponderado':f==='Precio informado'?'Media':'Suma'});else if(s.metricas.length>1)s.metricas=s.metricas.filter(m=>m.campo!==f);}
      else if(t.dataset.aggr){const m=s.metricas.find(m=>m.campo===t.dataset.aggr);if(m)m.aggr=t.value;}
      else return;pintar(G);
    },{signal});
    root.addEventListener('keydown',e=>{const el=e.target.closest('tr[data-a]');if(el&&(e.key==='Enter'||e.key===' ')){e.preventDefault();el.click();}},{signal});
    root.addEventListener('scroll',e=>{const el=e.target,id=el.dataset?.tabla,t=G.tablas[id];if(t&&el.scrollTop+el.clientHeight>=el.scrollHeight-160&&t.n<t.rs.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',id==='pivot'?cuerpoPivot(G,t.n,t.n+150):filasLista(G,id,t.n,t.n+150));t.n+=150;}},{signal,capture:true});
    document.addEventListener('pointerdown',e=>{if(!s.menu||e.composedPath().some(n=>n.classList?.contains('dc-ms')))return;s.menu=null;pintar(G);avisarFamilias();},{signal});
    document.addEventListener('keydown',e=>{if(e.key!=='Escape'||!root.isConnected)return;
      if(s.menu){s.menu=null;pintar(G);avisarFamilias();}else if(s.como){s.como=false;pintar(G);}else if(s.amp){s.amp=null;pintar(G);}},{signal});
    root.addEventListener('dragstart',e=>{const el=e.target.closest('[data-campo]');if(el)e.dataTransfer.setData('text/plain',el.dataset.campo);},{signal});
    root.addEventListener('dragover',e=>{if(e.target.closest('[data-eje]'))e.preventDefault();},{signal});
    root.addEventListener('drop',e=>{const eje=e.target.closest('[data-eje]'),tag=e.target.closest('[data-pos]');if(!eje)return;e.preventDefault();mover(s,e.dataTransfer.getData('text/plain'),eje.dataset.eje,tag?+tag.dataset.pos:null);pintar(G);},{signal});
    pintar(G);return()=>{G.abort.abort();G.ro?.disconnect();};
  }
  return{inicial,leer,calcular,pivot,valor,dimension,rotulo,mover,aplanar,exportar,pintar,montar};
})();
window.__docsDatos=DOCS;
export default function(component){return DOCS.montar(component);}
