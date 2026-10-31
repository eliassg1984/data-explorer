// Cálculos compartidos de Stock por Producto y Área/Familia (#724).
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
  const clase=st.clase||'todos',counts=sestados(stock),visibles=stock.filter(r=>(st.chip==='todos'||(st.chip==='A'?r.abc==='A':st.chip==='areaNeg'?r.negArea:r.estado===st.chip))&&(clase==='todos'||(clase==='areaNeg'?r.negArea:r.abc===clase)));
  const serie=st.chip==='todos'&&clase==='todos'&&!st.q.trim()?base.serie:B.P.meses.map((_,i)=>visibles.reduce((s,r)=>s+(r.h[i]||0),0));
  return {...base,counts,sin,stock,visibles,serie,total:ssum(visibles,'v'),dias:sdiasConjunto(visibles,B.P.ventana),
    sinCons:ssum(visibles.filter(r=>r.estado==='sin'),'v'),analisis:B.P.analisis&&!st.af};
}
function sescenario(r,dias,ventana=90){
  if(!r||r.mixed||r.q<0||!(r.consumo>0)||!(dias>0))return null;
  const equivalente=r.consumo/ventana*dias,diferencia=r.q-equivalente;
  return {dias,equivalente,diferencia,valor:r.precio>0?diferencia*r.precio:null};
}

// ── Lo común a las dos perspectivas desde la #765: indicadores, líneas y ficha.
const sv0=n=>`${n<-.5?'−':''}${sn(Math.abs(n))}`;
const sd0=n=>`${n>.5?'+':n<-.5?'−':''}S/ ${sn(Math.abs(n))}`;
const sdiasTxt=d=>d==null?'—':d>365?'más de 365':sn(d);
function sserie(rs,n){const h=new Array(n).fill(0);for(const r of rs)for(let i=0;i<n;i++)h[i]+=r.h[i]||0;return h;}
function smini(h,hist=''){if(!h?.length)return '';const mn=Math.min(...h),mx=Math.max(...h),rg=mx-mn,y=v=>rg?18-(v-mn)/rg*16:10,n=Math.max(1,h.length-1);
  return `<svg class="ist-mini" viewBox="0 0 68 20" role="img" aria-label="${se(hist||'Valor después de cada cierre')}"><polyline points="${h.map((v,i)=>`${(2+i*64/n).toFixed(1)},${y(v).toFixed(1)}`).join(' ')}"/><circle cx="66" cy="${y(h.at(-1)).toFixed(1)}" r="2" class="${h.at(-1)<0?'neg':''}"/></svg>`;}
function skpiCurva(h){if(!h?.length)return '';const mn=Math.min(...h),mx=Math.max(...h),rg=mx-mn||1,n=Math.max(1,h.length-1);
  return `<svg viewBox="0 0 100 34" preserveAspectRatio="none" aria-hidden="true"><polyline points="${h.map((v,i)=>`${(i*100/n).toFixed(1)},${(31-(v-mn)/rg*28).toFixed(1)}`).join(' ')}"/></svg>`;}
// `attrs` es lo que lo hace reaccionar: `data-act` en una pieza, `data-a` en la otra.
const skpiBtn=({attrs,on=false,rot,val,sub='',h=null,neg=false,tip='',dis=false})=>`<button type="button" class="ist-kpi ${on?'on':''} ${neg?'neg':''}" ${attrs} title="${se(tip)}" aria-pressed="${on}" ${dis?'disabled':''}>${skpiCurva(h)}<span class="r">${se(rot)}</span><span class="v">${se(val)}</span><span class="d">${se(sub)}</span></button>`;
function scurvaFicha(h,meses,ref){if(!h?.length)return '';const mn=Math.min(0,...h),mx=Math.max(0,...h),rg=mx-mn||1,n=Math.max(1,h.length-1),X=i=>i*100/n,Y=v=>94-(v-mn)/rg*86;
  const L=h.map((v,i)=>`${X(i).toFixed(2)},${Y(v).toFixed(2)}`).join(' ');
  const rot=meses.map((t,i)=>[t,i]).filter(([,i])=>i===0||i===n||i===ref||(i%3===0&&i<n-1&&Math.abs(i-ref)>1));
  return `<div class="ist-curva"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polygon points="0,${Y(0).toFixed(2)} ${L} 100,${Y(0).toFixed(2)}"/><polyline points="${L}"/></svg>${h.map((v,i)=>`<span class="ist-pto ${i===ref?'ref':v<0?'neg':''}" style="left:${X(i).toFixed(2)}%;top:${Y(v).toFixed(2)}%" title="${se(`${meses[i]}: ${ss(v,0)}`)}"></span>`).join('')}</div><div class="ist-cm">${rot.map(([t,i])=>`<span style="left:${X(i).toFixed(2)}%;transform:${i===0?'none':i===n?'translateX(-100%)':'translateX(-50%)'}">${se(t)}</span>`).join('')}</div>`;}
// Insumos de operación: ninguna receta los descarga, así que «sin consumo» no quiere decir lo mismo que en la comida (regla #645).
const soperacion=(r,P)=>!!P.fam_operacion&&r.fam===P.fam_operacion;
function sparado(rs,P){const pos=rs.reduce((s,r)=>s+Math.max(0,r.v),0),neg=rs.reduce((s,r)=>s+Math.min(0,r.v),0),pa=rs.filter(r=>r.estado==='sin'||r.estado==='alto'),parado=pa.reduce((s,r)=>s+Math.max(0,r.v),0),oper=pa.filter(r=>soperacion(r,P)).reduce((s,r)=>s+Math.max(0,r.v),0);return {pos,neg,parado,oper};}
function sfrase(rs,P,chip){const a=sparado(rs,P);if(chip==='neg')return `Se descargaron antes de que entrara lo que los cubre: restan ${ss(-a.neg,0)} al total sin ser mercadería que falta.`;
  if(!(a.parado>.5))return '';const todo=a.parado/(a.pos||1)>.995,soloOper=!rs.some(r=>r.v>.5&&!soperacion(r,P));
  if(soloOper)return 'Son insumos de operación: ninguna receta los descarga, así que sólo salen al contar.';
  const oper=a.oper>.5?`${ss(a.oper,0)} ${todo?'de esto':'de eso'} son insumos de operación (menaje, limpieza, leña), que ninguna receta descarga.`:'';
  return (todo?(a.oper>.5?`${oper} Lo demás, ${ss(a.parado-a.oper,0)}, es comida, bebida y envases.`:''):`De ${ss(a.pos,0)} en positivo, ${ss(a.parado,0)} (${sn(a.parado/(a.pos||1)*100)} %) no tuvo consumo en 90 días o tiene más de ${P.umbral} días de stock. ${oper}`).trim();}
// Lo que sobra por encima de `dias` de cobertura; cálculo propio, al ritmo de los últimos 90 días.
const ssobra=(r,dias)=>r.q>0&&r.dias!=null&&r.dias>dias&&r.v>0?r.v*(1-dias/r.dias):0;
