// Stock por Producto (#721). Las fotos las consulta Python; el análisis es local.
const SP={cod:0,prod:1,fam:2,sub:3,area:4,um:5,usal:6,acod:7,factor:8,precio:9,q:10,v:11,h:12};
const SEPS=1e-9;
const se=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sfmt=Array.from({length:7},(_,d)=>new Intl.NumberFormat('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}));
const svar=Array.from({length:7},(_,d)=>new Intl.NumberFormat('en-US',{maximumFractionDigits:d}));
const sn=(n,d=0)=>n==null||!Number.isFinite(n)?'—':sfmt[d].format(n);
const sv=(n,d=3)=>n==null||!Number.isFinite(n)?'—':svar[d].format(n);
const ss=(n,d=2)=>n==null||!Number.isFinite(n)?'—':`${n<0?'−':''}S/ ${sn(Math.abs(n),d)}`;
const scolor=n=>n<0?'var(--danger)':n>0?'var(--success)':'var(--text-secondary)';
const splano=s=>String(s??'').normalize('NFKD').replace(/[^\x00-\x7f]/g,'').toLowerCase();
const sorden=s=>splano(String(s).replace(/^\s*(\([^)]*\)\s*)+/,''));
const scmp=(a,b)=>a<b?-1:a>b?1:0;
const slabel=(G,k,v)=>G.B.P.rotulos?.[k==='sub'?'subfam':k]?.[v]??v;
const ssum=(rs,k)=>{let sum=0,c=0;for(const r of rs){const x=(r[k]||0)-c,t=sum+x;c=t-sum-x;sum=t;}return sum;};
const sgroup=(rs,k)=>{const m=new Map();for(const r of rs){const v=k(r);if(!m.has(v))m.set(v,[]);m.get(v).push(r);}return m;};
const sbits=new DataView(new ArrayBuffer(8));
function sround(x,d=0){
  // round de Python: la fracción IEEE exacta, con empate al par. Importa
  // al partir litros/onzas y al llevar 1000 g a la unidad siguiente.
  if(!Number.isFinite(x)||x===0)return x;const neg=x<0;
  sbits.setFloat64(0,Math.abs(x));const bits=sbits.getBigUint64(0),exp=Number((bits>>52n)&2047n),frac=bits&((1n<<52n)-1n);
  let m=(exp?frac+(1n<<52n):frac)*10n**BigInt(d),e=(exp?exp-1023:1-1023)-52;
  if(e>=0)m<<=BigInt(e);else{const den=1n<<BigInt(-e),q=m/den,r=m%den;m=q+(2n*r>den||(2n*r===den&&(q&1n))?1n:0n);}
  return (neg?-1:1)*Number(m)/10**d;
}
function scantidad(q,factor,ue,us,salida=false){
  if(q==null)return '—';const signo=q<0?'−':'',a=Math.abs(q),f=factor||0;
  if(!salida||!ue||!us||ue===us||f<=1)return `${signo}${sv(sround(a,3),3)}${ue?' '+ue:''}`;
  const dec=f>=100?0:1;let entero=Math.trunc(a),resto=sround((a-entero)*f,dec);
  if(resto>=f){entero++;resto=0;}const partes=[];
  if(entero)partes.push(`${sn(entero)} ${ue}`);if(resto)partes.push(`${sn(resto,dec)} ${us}`);
  return signo+(partes.length?partes.join(' '):`0 ${ue}`);
}
function sleer(P){
  const names=['cod','prod','fam','sub','area','um','usal','acod'],dict=['cod','prod','fam','subfam','area','unidad','usal','cod_area'];
  const rows=P.filas.map((z,i)=>{const r={i};for(let k=0;k<names.length;k++)r[names[k]]=P.dic[dict[k]][z[k]];
    for(const k of ['factor','precio','q','v'])r[k]=z[SP[k]];r.q=r.q||0;r.v=r.v||0;r.h=z[SP.h];return r;});
  return {P,rows,fotos:new Map(),cache:new Map()};
}
function sagrupar(rows,B,analisis){
  const prods=[],areaMap=new Map();
  for(const [cod,g] of sgroup(rows,r=>r.cod)){
    const first=k=>g.find(r=>r[k]!=null)?.[k]??null,precios=g.map(r=>r.precio).filter(v=>v!=null),q=ssum(g,'q'),v=ssum(g,'v');
    let precio=first('precio');if(precios.length&&Math.max(...precios)-Math.min(...precios)>SEPS&&Math.abs(q)>SEPS)precio=v/q;
    const areas=[...sgroup(g.filter(r=>['q','v','qh','vh'].some(k=>Math.abs(r[k]||0)>SEPS)),r=>r.area)].map(([area,rs])=>({
      cod,area,q:ssum(rs,'q'),v:ssum(rs,'v'),qh:ssum(rs,'qh'),vh:ssum(rs,'vh'),h:B.P.meses.map((_,i)=>rs.reduce((s,r)=>s+(r.h[i]||0),0))})).sort((a,b)=>b.v-a.v);
    const mixed=new Set(g.map(r=>r.um)).size>1,cons=analisis?(B.P.consumo[cod]||0):null;
    const dias=analisis&&!mixed&&q>0&&cons>0?q/(cons/B.P.ventana):null;
    const estado=!analisis||mixed?'':q<0?'neg':q>0&&cons<=0?'sin':dias>B.P.umbral?'alto':'';
    const r={...g[0],factor:first('factor'),precio,q,v,qh:ssum(g,'qh'),vh:ssum(g,'vh'),h:B.P.meses.map((_,i)=>g.reduce((s,r)=>s+(r.h[i]||0),0)),
      areas,consumo:cons,dias,estado,abc:null,mixed,negArea:areas.some(a=>a.q<0),posicion:prods.length};
    prods.push(r);areaMap.set(cod,areas);
  }
  if(analisis){const pos=prods.filter(r=>r.v>0).sort((a,b)=>b.v-a.v),total=ssum(pos,'v');let acum=0;
    for(const r of pos){acum+=r.v;const antes=(acum-r.v)/total;r.abc=antes<.8?'A':antes<.95?'B':'C';}}
  // Orden inicial de la #636. El valor deshace los empates de nombre.
  const cmp=(a,b)=>scmp(sorden(a.fam),sorden(b.fam))||scmp(sorden(a.sub),sorden(b.sub))||scmp(sorden(a.prod),sorden(b.prod))||b.v-a.v;
  return {productos:prods.sort(cmp),areaMap};
}
function sestados(rs){return {todos:rs.length,A:rs.filter(r=>r.abc==='A').length,neg:rs.filter(r=>r.estado==='neg').length,
  sin:rs.filter(r=>r.estado==='sin').length,alto:rs.filter(r=>r.estado==='alto').length,areaNeg:rs.filter(r=>r.negArea).length};}
function sdiasConjunto(rs,ventana=90){const g=rs.filter(r=>r.q>0&&!r.mixed),diario=g.reduce((s,r)=>s+(r.consumo||0)*(r.precio||0),0)/ventana;
  return diario>0?g.reduce((s,r)=>s+Math.max(0,r.v),0)/diario:null;}
function sfiltrar(B,st){
  let source=B.rows,photo=null;
  if(st.af){photo=B.fotos.get(`${st.fecha}|${st.hora}`);if(!photo?.ok)return {pending:!photo,error:photo?.error||'',photo};
    source=B.rows.map((r,i)=>{const z=photo.filas[i];return {...r,precio:z[0],q:z[1]||0,v:z[2]||0,qh:st.comparar&&photo.comparar?z[3]||0:0,vh:st.comparar&&photo.comparar?z[4]||0:0};});}
  const key=JSON.stringify([st.af,st.fecha,st.hora,st.comparar,st.areas,st.fams,st.subs,photo?.ok]);
  let base=B.cache.get(key);
  if(!base){
    const rs=source.filter(r=>(!st.areas.length||st.areas.includes(r.area))&&(!st.fams.length||st.fams.includes(r.fam))&&(!st.subs.length||st.subs.includes(r.sub)));
    const a=sagrupar(rs,B,B.P.analisis&&!st.af),serie=B.P.meses.map((_,i)=>rs.reduce((s,r)=>s+(r.h[i]||0),0));
    base={...a,serie,photo};if(B.cache.size>24)B.cache.clear();B.cache.set(key,base);
  }
  const palabras=splano(st.q).split(/\s+/).filter(Boolean);
  const buscados=base.productos.filter(r=>palabras.every(p=>splano(r.prod+' '+r.cod).includes(p)));
  const sin=buscados.filter(r=>!r.areas.length).length,stock=buscados.filter(r=>st.sin||r.areas.length);
  const counts=sestados(stock),visibles=stock.filter(r=>st.chip==='todos'||(st.chip==='A'?r.abc==='A':st.chip==='areaNeg'?r.negArea:r.estado===st.chip));
  const serie=st.chip==='todos'&&!st.q.trim()?base.serie:B.P.meses.map((_,i)=>visibles.reduce((s,r)=>s+(r.h[i]||0),0));
  return {...base,counts,sin,stock,visibles,serie,total:ssum(visibles,'v'),dias:sdiasConjunto(visibles,B.P.ventana),
    sinCons:ssum(visibles.filter(r=>r.estado==='sin'),'v'),analisis:B.P.analisis&&!st.af};
}
function sescenario(r,dias,ventana=90){
  if(!r||r.mixed||r.q<0||!(r.consumo>0)||!(dias>0))return null;
  const equivalente=r.consumo/ventana*dias,diferencia=r.q-equivalente;
  return {dias,equivalente,diferencia,valor:r.precio>0?diferencia*r.precio:null};
}
const schips=[['todos','Todos'],['A','Clase A'],['neg','Negativos'],['sin','Sin consumo 90 d'],['alto','Más de 60 d'],['areaNeg','Áreas negativas']];
function sinicial(P){const tope=P.rango?.[1]||'',fecha=tope?new Date(Date.parse(tope+'T00:00:00Z')-864e5*(+tope.slice(8))).toISOString().slice(0,10):'';
  return {areas:[...P.areas_iniciales],fams:[],subs:[],q:'',sin:false,salida:false,chip:'todos',af:false,fecha:fecha<P.rango?.[0]?P.rango[0]:fecha,hora:23,comparar:false,
    abiertos:[],foco:null,focoArea:null,tab:'areas',objetivo:60,limite:150,orden:[{k:'fam',d:1},{k:'sub',d:1},{k:'prod',d:1}],...P.inicial};}
const sb=(act,v,txt,on=false,tip='')=>`<button type="button" data-act="${act}" data-v="${se(v)}" class="${on?'on':''}" title="${se(tip)}" aria-pressed="${on}">${se(txt)}</button>`;
const stoggle=(key,txt,val)=>`<label class="isp-toggle"><input type="checkbox" data-toggle="${key}" ${val?'checked':''}>${se(txt)}</label>`;
const skpi=(txt,val,sub='',tip='')=>`<div class="isp-kpi" title="${se(tip)}"><small>${se(txt)}</small><b>${se(val)}</b><span>${se(sub)}</span></div>`;
function sfiltro(G,key,txt,ops){const vs=G.st[key];return `<details class="isp-filter"><summary>${se(vs.length===1?slabel(G,key==='fams'?'fam':key==='subs'?'sub':'area',vs[0]):vs.length?`${vs.length} ${txt.toLowerCase()}`:`Todas las ${txt.toLowerCase()}`)}</summary><div class="isp-options">${sb('todos',key,'Todas')}${key==='areas'?sb('principales',key,'Las principales'):''}<input type="search" placeholder="Buscar en la lista…" data-lista="${key}" aria-label="Buscar ${txt.toLowerCase()}">${ops.map(v=>`<label><input type="checkbox" data-filter="${key}" value="${se(v)}" ${vs.includes(v)?'checked':''}>${se(slabel(G,key==='fams'?'fam':key==='subs'?'sub':'area',v))}</label>`).join('')}<small>Sin ninguna marcada entran todas.</small></div></details>`;}
function scurve(v,labels=[],mini=false,alto=140){
  if(!v.length)return '<span>Sin historia disponible</span>';
  const w=mini?92:720,h=mini?22:alto,L=mini?2:14,R=mini?3:18,T=mini?2:17,D=mini?2:alto<100?16:22;
  const min=Math.min(0,...v),max=Math.max(0,...v),dif=max-min||1,X=i=>L+i*(w-L-R)/Math.max(1,v.length-1),Y=x=>T+(h-T-D)*(1-(x-min)/dif);
  const pts=v.map((x,i)=>`${X(i)},${Y(x)}`).join(' '),zero=Y(0);
  return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Valorizado después de cada cierre" class="${mini?'isp-mini':'isp-curve'}"><path d="M${X(0)},${zero} L${pts.replaceAll(' ',' L')} L${X(v.length-1)},${zero} Z" fill="var(--accent-tint)"/><line x1="${L}" x2="${w-R}" y1="${zero}" y2="${zero}" stroke="var(--border)"/><polyline points="${pts}" fill="none" stroke="var(--accent)" stroke-width="${mini?1.4:2}"/>
    ${v.map((x,i)=>mini&&x>=0&&i!==v.length-1?'':`<circle cx="${X(i)}" cy="${Y(x)}" r="${mini?2:3}" fill="${x<0?'var(--danger)':'var(--accent)'}"><title>${se(labels[i]||'')}: ${ss(x)}</title></circle>`).join('')}
    ${mini?'':labels.map((s,i)=>i%2&&i!==labels.length-1?'':`<text x="${X(i)}" y="${h-4}" text-anchor="${i===0?'start':i===labels.length-1?'end':'middle'}">${se(s)}</text>`).join('')+`<text x="${L}" y="12">${se(ss(v[0],0))}</text><text x="${w-R}" y="12" text-anchor="end">${se(ss(v.at(-1),0))}</text>`}</svg>`;
}
function ssort(rs,order){if(!order.length)return rs;
  return [...rs].sort((a,b)=>{for(const o of order){let x=a[o.k],y=b[o.k];if(x==null&&y==null)continue;if(x==null)return 1;if(y==null)return -1;
    if(['prod','fam','sub'].includes(o.k)){x=sorden(x);y=sorden(y);}const d=typeof x==='number'?x-y:String(x).localeCompare(String(y));if(d)return o.d*d;}return 0;});
}
function scols(G,D){const h=[['cod','Código'],['fam','Familia'],['sub','Subfamilia'],['prod','Producto']];
  if(!D.analisis&&!G.st.salida&&!G.st.comparar)h.push(['um','Unidad kardex']);
  if(!(G.st.af&&G.st.comparar&&D.photo?.comparar))h.push(['precio','P. unitario']);
  h.push(['q',G.st.af?'Cantidad a la fecha':'Cantidad'],['v',G.st.af?'Valor a la fecha':'Valorizado']);
  if(G.st.af&&G.st.comparar&&D.photo?.comparar)h.push(['qh','Cantidad hoy'],['vh','Valor hoy'],['delta','Δ valor']);
  if(D.analisis)h.push(['abc','ABC'],['h','12 meses'],['consumo','Consumo 90 d'],['dias','Días inv.'],['estado','Estado']);
  return h;
}
const setiqueta={neg:'Negativo',sin:'Sin consumo',alto:'Más de 60 días','':''};
function scelda(G,r,k,area=false){const {P}=G.B,st=G.st,unidad=P.unidades[r.um]||r.um;
  if(k==='prod')return area?`<span class="isp-area-name">↳ ${se(r.area)}</span>`:sb('foco',r.cod,r.prod,st.foco===r.cod);
  if(['cod','fam','sub','um'].includes(k))return area?'':`<span title="${se(slabel(G,k,r[k]))}">${se(slabel(G,k,r[k]))}</span>`;
  if(k==='h')return `<button data-act="historia" data-v="${se(JSON.stringify([r.cod,area?r.area:null]))}" title="Abrir historia del producto o área" aria-label="Abrir historia">${scurve(r.h,P.meses,true)}</button>`;
  if(k==='q'||k==='qh')return r.mixed?'Unidades distintas':`<span title="${se(`${sv(r[k],6)} ${unidad}`)}">${se(scantidad(r[k],r.factor,unidad,P.unidades[r.usal]||r.usal,st.salida))}</span>`;
  if(k==='v'||k==='vh'||k==='precio'||k==='delta')return area&&k==='precio'?'':`<span style="color:${k==='precio'?'inherit':scolor(k==='delta'?r.vh-r.v:r[k])}">${se(ss(k==='delta'?r.vh-r.v:r[k]))}</span>`;
  if(k==='abc')return area?'':`<span class="isp-abc">${r.abc||'—'}</span>`;
  if(k==='consumo')return area?'':se(r.mixed?'Unidades distintas':scantidad(r.consumo,r.factor,unidad,P.unidades[r.usal]||r.usal,st.salida));
  if(k==='dias')return area?'':r.mixed?'—':r.dias>365?'más de 365':sn(r.dias);
  if(k==='estado')return area?'':se(r.mixed?'Unidades distintas':setiqueta[r.estado]||'');
  return '';
}
function stabla(G,D){
  const cols=scols(G,D),rows=ssort(D.visibles,G.st.orden);G.ordenados=rows;
  const header=cols.map(([k,t])=>{const i=G.st.orden.findIndex(o=>o.k===k),o=G.st.orden[i];return `<th class="isp-col-${k}">${k==='h'?se(t):sb('orden',k,`${t}${o?` ${i+1} ${o.d>0?'↑':'↓'}`:' ↕'}`)}</th>`;}).join('');
  const fila=(r,area=false)=>`<tr class="${area?'isp-child':r.cod===G.st.foco?'chosen':''}"><td class="isp-expand">${area?'':r.areas.length?sb('abrir',r.cod,(G.st.abiertos.includes(r.cod)?'▾':'▸')+` ${r.areas.length}`,G.st.abiertos.includes(r.cod),'Abrir sus áreas'):''}</td>${cols.map(([k])=>`<td class="isp-col-${k}">${scelda(G,r,k,area)}</td>`).join('')}</tr>`;
  const body=[];for(const r of rows.slice(0,G.st.limite)){body.push(fila(r));if(G.st.abiertos.includes(r.cod))for(const a of r.areas)body.push(fila({...r,...a},true));}
  return `<table><thead><tr><th></th>${header}</tr></thead><tbody>${body.join('')}</tbody><tfoot><tr><th></th>${cols.map(([k])=>`<td>${k==='prod'?`TOTAL · ${rows.length} productos`:k==='v'?ss(D.total):k==='vh'?ss(ssum(rows,'vh')):k==='delta'?ss(ssum(rows,'vh')-D.total):''}</td>`).join('')}</tr></tfoot></table>`;
}
function stituloFecha(st){return st.af?`${st.fecha.split('-').reverse().join('/')} · ${String(st.hora).padStart(2,'0')}:59`:'Stock actual';}
function sprincipal(G,D){const st=G.st,P=G.B.P,subs=[...new Set(G.B.rows.filter(r=>!st.fams.length||st.fams.includes(r.fam)).map(r=>r.sub))].filter(Boolean).sort();
  const fecha=P.hay_fecha?stoggle('af','Ver a una fecha',st.af):'';
  const fechaCtrl=st.af?`<label>Fecha <input type="date" data-change="fecha" value="${se(st.fecha)}" min="${P.rango?.[0]||''}" max="${P.rango?.[1]||''}" aria-label="Fecha de stock"></label><label>Hora <select data-change="hora" aria-label="Hora de stock">${Array.from({length:24},(_,i)=>`<option value="${i}" ${i===st.hora?'selected':''}>${String(i).padStart(2,'0')}:59</option>`).join('')}</select></label>${stoggle('comparar','Comparar con hoy',st.comparar)}`:'';
  let contenido='',banda='';
  if(D.pending||D.error){contenido=`<div class="isp-notice" role="status">${se(D.pending?'Consultando el stock de esa fecha y hora…':D.error)}${D.error?sb('reintentar','','Reintentar'):''}</div>`;}
  else{
    if(D.analisis){const ini=D.serie[0],fin=D.serie.at(-1),pct=ini>0&&fin>0?100*(fin/ini-1):null;
      banda=`<div class="isp-band"><div class="isp-kpis">${skpi('Valorizado',ss(D.total,0))}${skpi(`vs ${P.meses[0]}`,pct==null?'—':`${pct>0?'+':''}${sn(pct)}%`,'Evolución de los productos del gráfico')}${skpi('Días de inventario',D.dias>365?'más de 365':sn(D.dias),'Stock seleccionado / consumo del restaurante','Valor del stock positivo elegido / consumo diario del restaurante entero, en soles. Se excluyen productos con unidades incompatibles.')}${skpi('Sin consumo 90 días',ss(D.sinCons,0))}</div><div class="isp-band-chart">${scurve(D.serie,P.meses,false,76)}<small>${st.q.trim()||st.chip!=='todos'?'Historia de los productos a la vista':'Historia del recorte completo, incluidos productos hoy sin stock'} · precios por área del kardex</small></div></div>`;}
    contenido=D.visibles.length?stabla(G,D):'<p>No hay productos para estos filtros.</p>';
  }
  return `<header><h3>Stock por Producto <small>${D.visibles?`${D.visibles.length} productos${D.sin&&!st.sin?` · ${D.sin} sin stock ocultos`:''}`:''}</small></h3>${fecha}${sb('excel','lista','Excel de productos')}</header>
    <div class="isp-toolbar">${sfiltro(G,'areas','Áreas',P.dic.area.filter(Boolean))}${sfiltro(G,'fams','Familias',P.dic.fam.filter(Boolean))}${sfiltro(G,'subs','Subfamilias',subs)}<input type="search" class="isp-search" data-input="q" value="${se(st.q)}" placeholder="Buscar producto o código…" aria-label="Buscar producto o código">${stoggle('sin','Ver sin stock',st.sin)}${P.hay_salida?stoggle('salida','Ver en unidad de salida',st.salida):''}</div>
    ${st.af?`<div class="isp-toolbar isp-date">${fechaCtrl}<small>${se(stituloFecha(st))}${D.photo&&!D.photo.comparar&&st.comparar?' · Hoy no disponible: comparación desactivada':''}</small></div>`:''}
    ${D.analisis?`<nav class="isp-chips">${schips.map(([k,t])=>sb('chip',k,`${t} ${D.counts[k]}`,st.chip===k)).join('')}</nav>`:!st.af?'<p class="isp-note">Análisis reciente del kardex no disponible: se muestra el stock actual.</p>':''}${banda}
    <div class="isp-scroll isp-table">${contenido}</div><footer><span>El área cambia las cantidades y el valor. El ABC se calcula antes de buscar. Clic en ▸ para abrir las áreas; en el nombre para la ficha.</span>${D.visibles?.length>st.limite?sb('mas','',`Ver más (${Math.min(st.limite,D.visibles.length)}/${D.visibles.length})`):''}</footer>`;
}
function sficha(G,D){const st=G.st,P=G.B.P;
  if(!D.visibles?.length)return '<h3>Ficha de producto</h3><p>Seleccione un producto del listado.</p>';
  let r=D.visibles.find(r=>r.cod===st.foco);if(!r){r=D.visibles[0];st.foco=r.cod;st.focoArea=null;}
  const a=r.areas.find(a=>a.area===st.focoArea),v=a?{...r,...a}:r;
  const um=P.unidades[r.um]||r.um,pctTotal=r.areas.reduce((s,a)=>s+Math.max(0,a.v),0),tabs=[['areas','Por área']];
  if(D.analisis){tabs.push(['historia','Evolución'],['escenario','Escenario de cobertura']);}
  if(!tabs.some(([k])=>k===st.tab))st.tab='areas';
  let body='';
  if(st.tab==='areas'){
    body=`<div class="isp-scroll"><table class="isp-areas"><thead><tr><th>Área · clic para su historia</th><th>Stock</th><th>Valorizado</th><th>% del positivo</th>${st.af&&st.comparar&&D.photo?.comparar?'<th>Stock hoy</th><th>Valor hoy</th><th>Δ cantidad</th><th>Δ valor</th>':''}</tr></thead><tbody>${r.areas.map(a=>`<tr><td>${sb('area',a.area,a.area,st.focoArea===a.area)}</td><td>${r.mixed?'Unidades distintas':se(scantidad(a.q,r.factor,um,P.unidades[r.usal]||r.usal,st.salida))}</td><td style="color:${scolor(a.v)}">${ss(a.v)}</td><td class="isp-bar" style="--barra:${pctTotal?100*Math.max(0,a.v)/pctTotal:0}%">${a.v<0?'Negativo':pctTotal?sn(100*a.v/pctTotal,1)+'%':'—'}</td>${st.af&&st.comparar&&D.photo?.comparar?`<td>${sv(a.qh)} ${se(um)}</td><td>${ss(a.vh)}</td><td>${r.mixed?'—':sv(a.qh-a.q)} ${se(um)}</td><td>${ss(a.vh-a.v)}</td>`:''}</tr>`).join('')}</tbody></table></div><p class="isp-note">${r.negArea?'Hay stock negativo en alguna área. El total del producto puede compensarlo con stock de otra. ':''}${r.mixed?'Las unidades de este código no coinciden: no se suman sus cantidades ni se calcula cobertura.':'La distribución usa sólo el valor positivo; las áreas negativas se muestran aparte.'}</p>`;
  }else if(st.tab==='historia'){
    body=`<div class="isp-history"><div class="isp-toolbar"><label>Área de la curva <select data-change="curvaArea" aria-label="Área de la curva"><option value="">Producto completo</option>${r.areas.map(a=>`<option value="${se(a.area)}" ${st.focoArea===a.area?'selected':''}>${se(a.area)}</option>`).join('')}</select></label></div><h4>${se(a?a.area:'Todas las áreas del producto')}</h4>${scurve(v.h,P.meses)}<div class="isp-scroll"><table><thead><tr><th>Cierre</th>${P.meses.map(m=>`<th>${se(m)}</th>`).join('')}</tr></thead><tbody><tr><th>Valor S/</th>${v.h.map(x=>`<td>${ss(x)}</td>`).join('')}</tr></tbody></table></div><p class="isp-note">Fotos después de cada cierre y último momento del kardex. Cada punto es stock × precio del área; no son movimientos que se puedan sumar.</p></div>`;
  }else{
    const esc=sescenario(r,st.objetivo,P.ventana);
    body=`<div class="isp-scenario"><label>Escenario: días de cobertura <input type="number" min="1" max="365" step="1" data-input="objetivo" value="${st.objetivo}" aria-label="Días del escenario"></label>${esc?`<div class="isp-kpis">${skpi('Consumo por día',`${sv(r.consumo/P.ventana)} ${um}`)}${skpi(`Equivalente a ${esc.dias} días`,`${sv(esc.equivalente)} ${um}`)}${skpi('Stock menos equivalente',`${esc.diferencia>0?'+':''}${sv(esc.diferencia)} ${um}`)}${skpi('Valor de esa diferencia',ss(esc.valor))}</div>`:'<p>Se necesita stock no negativo, una sola unidad y consumo positivo para calcular este escenario.</p>'}<p class="isp-note">Cálculo propio con el ritmo promedio de los últimos 90 días del restaurante entero. El stock es el de las áreas seleccionadas. Es un escenario de cobertura; no incorpora plazos de compra, estacionalidad ni cambios de demanda.</p></div>`;
  }
  return `<header><div><h3>${se(r.prod)}</h3><small>${se(r.cod)} · ${se(slabel(G,'fam',r.fam))} · ${se(slabel(G,'sub',r.sub))}</small></div>${sb('excel','ficha','Excel de la ficha')}</header><div class="isp-kpis">${skpi('Stock seleccionado',r.mixed?'Unidades distintas':scantidad(r.q,r.factor,um,P.unidades[r.usal]||r.usal,st.salida))}${skpi('Valorizado',ss(r.v))}${skpi('Áreas con stock',sn(r.areas.length),r.negArea?'Incluye áreas negativas':'')}${D.analisis?skpi('Consumo 90 d',r.mixed?'—':`${sv(r.consumo)} ${um}`,'Restaurante entero')+skpi('Días / clase',`${r.dias>365?'más de 365':sn(r.dias)} · ${r.abc||'—'}`,setiqueta[r.estado]||''):skpi('Precio unitario',ss(r.precio))}</div><nav>${tabs.map(([k,t])=>sb('tab',k,t,st.tab===k)).join('')}</nav>${body}`;
}
const sheads=['Código','Familia','Subfamilia','Producto','Unidad kardex','Precio unitario','Cantidad','Valorizado S/','ABC','Consumo 90 d','Días de inventario','Estado','Áreas negativas'];
const svals=r=>[r.cod,r.fam,r.sub,r.prod,r.mixed?'Varias unidades':r.um,r.precio,r.mixed?null:r.q,r.v,r.abc,r.mixed?null:r.consumo,r.dias,setiqueta[r.estado]||'',r.negArea?'Sí':'No'];
function scontexto(G){const st=G.st,P=G.B.P;return {nombre:'Contexto',cabeza:['Criterio','Valor'],filas:[
  ['Modo',st.af?'Histórico del kardex':'Stock actual del maestro'],['Fecha y hora',stituloFecha(st)],['Hoy del kardex',P.rango?.[1]||'No disponible'],['Comparar con hoy',st.af&&st.comparar&&G.D.photo?.comparar?'Sí':'No'],
  ['Áreas',st.areas.join(' / ')||'Todas'],['Familias',st.fams.join(' / ')||'Todas'],['Subfamilias',st.subs.join(' / ')||'Todas'],['Búsqueda',st.q],['Estado',schips.find(([k])=>k===st.chip)?.[1]||'Todos'],['Ver sin stock',st.sin?'Sí':'No'],['Unidad de pantalla',st.salida?'Entrada y resto en salida':'Kardex'],['Producto en ficha',st.foco||''],['Área de la curva',st.focoArea||'Todas'],['Escenario días',st.objetivo],
  ['ABC','Valor positivo del recorte antes de buscar; acumulado anterior a cada producto: A <80%, B <95%, C resto.'],['Consumo','Restaurante entero, últimos 90 días; sin transferencias ni requerimientos ni ajustes.'],['Cantidades','Numéricas en la unidad kardex, seis decimales. Sin total entre productos o unidades diferentes.'],['Histórico','Foto de mayor correlativo hasta la hora; datos maestros y activos de hoy. Consulta fallida no se toma por stock cero.'],['Alcance','Todas las filas del listado filtrado o la ficha elegida, sin el límite de pantalla.']]};}
function sexportar(G,tipo){const D=G.D,st=G.st;if(!D.visibles)return null;const rows=ssort(D.visibles,st.orden),r=rows.find(x=>x.cod===st.foco),ps=tipo==='ficha'?(r?[r]:[]):rows;
  const cmp=st.af&&st.comparar&&D.photo?.comparar,hojas=[{nombre:'Productos',cabeza:[...sheads,...(cmp?['Stock hoy','Valor hoy S/','Δ cantidad','Δ valor S/']:[])],filas:ps.map(r=>[...svals({...r,fam:slabel(G,'fam',r.fam),sub:slabel(G,'sub',r.sub)}),...(cmp?[r.mixed?null:r.qh,r.vh,r.mixed?null:r.qh-r.q,r.vh-r.v]:[])]),decimales:6},
    {nombre:'Áreas',cabeza:['Código','Producto','Área','Unidad','Cantidad','Valorizado S/',...(cmp?['Stock hoy','Valor hoy S/','Δ cantidad','Δ valor S/']:[])],filas:ps.flatMap(r=>r.areas.map(a=>[r.cod,r.prod,a.area,r.um,r.mixed?null:a.q,a.v,...(cmp?[r.mixed?null:a.qh,a.vh,r.mixed?null:a.qh-a.q,a.vh-a.v]:[])])),decimales:6}];
  if(D.analisis)hojas.push({nombre:'Historia',cabeza:['Código','Producto','Área',...G.B.P.meses],filas:ps.flatMap(r=>[[r.cod,r.prod,'Todas',...r.h],...r.areas.map(a=>[r.cod,r.prod,a.area,...a.h])]),decimales:6});
  if(tipo==='ficha'&&D.analisis&&r){const e=sescenario(r,st.objetivo,G.B.P.ventana);hojas.push({nombre:'Escenario',cabeza:['Código','Unidad','Días','Stock','Consumo 90 d','Equivalente','Stock menos equivalente','Valor diferencia S/'],filas:e?[[r.cod,r.um,e.dias,r.q,r.consumo,e.equivalente,e.diferencia,e.valor]]:[],decimales:6});}
  hojas.push(scontexto(G));return libro(hojas);
}
function spintar(G,soloFicha=false){G.D=sfiltrar(G.B,G.st);
  if(!soloFicha)G.root.querySelector('.isp-main').innerHTML=sprincipal(G,G.D);
  G.root.querySelector('.isp-ficha').innerHTML=sficha(G,G.D);
  for(const b of G.root.querySelectorAll('.isp-main [data-act=foco]')){const on=b.dataset.v===G.st.foco;b.closest('tr').classList.toggle('chosen',on);b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));}
}
function spedir(G,reintentar=false){const st=G.st;if(!st.af)return;const key=`${st.fecha}|${st.hora}`,foto=G.B.fotos.get(key);
  if(foto&&!reintentar)return;if(!G.B.P.rango)return;
  if(st.fecha<G.B.P.rango[0]||st.fecha>G.B.P.rango[1])return;
  if(G.pedido===key&&!reintentar)return;G.pedido=key;
  G.enviar?.('foto',{sello:G.B.P.sello,fecha:st.fecha,hora:st.hora,reintentar});
}
function senlazar(G){const root=G.root;
  root.addEventListener('click',ev=>{const b=ev.target.closest('[data-act]');if(!b)return;const {act,v}=b.dataset,st=G.st;let ficha=false;
    if(act==='todos'){st[v]=[];st.limite=150;}else if(act==='principales'){st.areas=[...G.B.P.areas_iniciales];st.limite=150;}
    else if(act==='abrir')st.abiertos=st.abiertos.includes(v)?st.abiertos.filter(x=>x!==v):[...st.abiertos,v];
    else if(act==='foco'){st.foco=v;st.focoArea=null;ficha=true;}
    else if(act==='historia'){[st.foco,st.focoArea]=JSON.parse(v);st.tab='historia';ficha=true;}
    else if(act==='area'){st.focoArea=v||null;st.tab=G.D.analisis?'historia':'areas';ficha=true;}
    else if(act==='tab'){st.tab=v;ficha=true;}
    else if(act==='chip'){st.chip=v;st.limite=150;}
    else if(act==='mas')st.limite+=150;
    else if(act==='orden'){const old=st.orden.find(o=>o.k===v),next=!old?{k:v,d:1}:old.d===1?{k:v,d:-1}:null;
      if(!ev.shiftKey)st.orden=next?[next]:[];else if(old)st.orden=next?st.orden.map(o=>o.k===v?next:o):st.orden.filter(o=>o.k!==v);else st.orden.push(next);}
    else if(act==='reintentar'){G.B.fotos.delete(`${st.fecha}|${st.hora}`);spedir(G,true);}
    else if(act==='excel'){const blob=sexportar(G,v);if(blob)bajar(`stock_${v}_${st.af?st.fecha:'actual'}.xlsx`,blob);return;}
    spintar(G,ficha);
  });
  root.addEventListener('change',ev=>{const el=ev.target,st=G.st,key=el.dataset.filter;
    if(key){st[key]=el.checked?[...st[key],el.value]:st[key].filter(v=>v!==el.value);
      if(key==='fams'){const subs=new Set(G.B.rows.filter(r=>!st.fams.length||st.fams.includes(r.fam)).map(r=>r.sub));st.subs=st.subs.filter(x=>subs.has(x));}
      st.limite=150;spintar(G);root.querySelector(`input[data-filter="${key}"]`)?.closest('details').setAttribute('open','');return;}
    const toggle=el.dataset.toggle;if(toggle){st[toggle]=el.checked;st.limite=150;if(toggle==='af'){st.chip='todos';st.focoArea=null;}spintar(G);if(toggle==='af')spedir(G);return;}
    if(el.dataset.change==='fecha'||el.dataset.change==='hora'){const key=el.dataset.change;
      if(key==='fecha'&&(!el.value||el.value<G.B.P.rango[0]||el.value>G.B.P.rango[1])){el.value=st.fecha;return;}
      st[key]=key==='hora'?+el.value:el.value;st.limite=150;spintar(G);spedir(G);}
    if(el.dataset.input==='objetivo'){const n=+el.value;if(Number.isInteger(n)&&n>=1&&n<=365){st.objetivo=n;spintar(G,true);}else el.value=st.objetivo;}
    if(el.dataset.change==='curvaArea'){st.focoArea=el.value||null;spintar(G,true);}
  });
  root.addEventListener('input',ev=>{const el=ev.target,st=G.st;
    if(el.dataset.lista){const q=splano(el.value);el.closest('.isp-options').querySelectorAll('label').forEach(l=>l.hidden=!splano(l.textContent).includes(q));return;}
    if(el.dataset.input==='q'){const pos=el.selectionStart;st.q=el.value;st.limite=150;spintar(G);const e=root.querySelector('.isp-search');e.focus();if(pos!=null)e.setSelectionRange(pos,pos);}
  });
  root.addEventListener('scroll',ev=>{const el=ev.target;if(el.matches('.isp-table')&&G.D.visibles?.length>G.st.limite&&el.scrollTop+el.clientHeight>el.scrollHeight-70){const x=el.scrollLeft,y=el.scrollTop;G.st.limite+=150;spintar(G);const n=root.querySelector('.isp-table');n.scrollTop=y;n.scrollLeft=x;}},true);
}
window.__stockDatos={leer:sleer,agrupar:sagrupar,filtrar:sfiltrar,estados:sestados,diasConjunto:sdiasConjunto,escenario:sescenario,cantidad:scantidad,round:sround,ordenar:ssort};
window.__stockUI={inicial:sinicial,pintar:spintar,exportar:sexportar};
export default function(component){const {data:P,parentElement,setTriggerValue}=component;if(!P)return;const old=window.__stockProd;
  if(P.parte==='foto'){
    if(!old){window.__stockFotoPendiente=P;return;}if(P.sello!==old.B.P.sello)return;
    const key=`${P.fecha}|${P.hora}`;old.B.fotos.set(key,P);old.B.cache.clear();if(old.pedido===key)old.pedido=null;
    if(old.B.fotos.size>12)old.B.fotos.delete(old.B.fotos.keys().next().value);if(old.root.isConnected)spintar(old);return;
  }
  old?.abort?.abort();let st=old?.st||sinicial(P),B=old?.B.P.sello===P.sello?old.B:sleer(P);
  if(old&&old.B.P.sello!==P.sello){for(const [k,dk] of [['areas','area'],['fams','fam'],['subs','subfam']])st[k]=st[k].filter(v=>P.dic[dk].includes(v));st.focoArea=null;st.abiertos=[];st.limite=150;}
  if(old&&old.semilla!==P.semilla)st={...st,...P.inicial,af:false,foco:null,focoArea:null,limite:150};
  if(!P.hay_fecha)st.af=false;else if(P.rango){st.fecha=st.fecha<P.rango[0]?P.rango[0]:st.fecha>P.rango[1]?P.rango[1]:st.fecha;}
  if(!P.analisis)st.chip='todos';
  let root=parentElement.querySelector('.isp');if(root)root.remove();root=document.createElement('div');root.className='isp';root.innerHTML='<section class="isp-card isp-main"></section><section class="isp-card isp-ficha"></section>';parentElement.appendChild(root);
  const G={root,st,B,enviar:setTriggerValue,semilla:P.semilla,abort:new AbortController(),pedido:old?.B.P.sello===P.sello?old.pedido:null};window.__stockProd=G;
  const pend=window.__stockFotoPendiente;if(pend?.sello===P.sello){B.fotos.set(`${pend.fecha}|${pend.hora}`,pend);window.__stockFotoPendiente=null;}
  senlazar(G);spintar(G);spedir(G);
  document.addEventListener('pointerdown',ev=>{if(!ev.composedPath().includes(root))root.querySelectorAll('details[open]').forEach(d=>d.open=false);},{signal:G.abort.signal});
  document.addEventListener('keydown',ev=>{if(ev.key==='Escape')root.querySelectorAll('details[open]').forEach(d=>d.open=false);},{signal:G.abort.signal});
}
