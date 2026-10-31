const DESTINO=(()=>{
  function preparar(P){const L=P.filas.map(f=>Object.fromEntries([['i',f[0]],...P.identidad.map((c,j)=>[c,P.productos[f[0]][j]]),...P.columnas.map((c,j)=>[c,f[j+1]])])),porK=new Map(),tot=new Map(P.totales.map(t=>[t.k,t]));for(const r of L){if(!porK.has(r.k))porK.set(r.k,[]);porK.get(r.k).push(r);}return{P,L,porK,tot};}
  const ks=(P,k)=>{const fin=k<Math.max(0,P.periodos.length-P.cierres_grafico)?k+1:P.periodos.length;return Array.from({length:Math.min(fin,P.cierres_grafico)},(_,j)=>Math.max(0,fin-P.cierres_grafico)+j);};
  const identidad=r=>JSON.stringify([r.cod,r.unidad]);
  function dominante(r){if(!(r.sinplato_v>0))return{nombre:'',pct:null};const a=[[r.falt_v,'faltante'],[r.baja_v,'bajas'],[r.otras_v,'otras salidas']].sort((a,b)=>b[0]-a[0]||(a[1]<b[1]?1:a[1]>b[1]?-1:0));return{nombre:a[0][1],pct:100*a[0][0]/r.sinplato_v};}
  function ranking(B,s){const col=s.modo==='sobr'?'sobr_v':'sinplato_v',prev=new Map((B.porK.get(s.k-1)||[]).map(r=>[identidad(r),r])),base=(B.porK.get(s.k)||[]).filter(r=>r.clase===B.P.alimentos&&r[col]>.5),q=(s.q||'').trim().toLowerCase();
    const todos=base.map(r=>{const ant=prev.get(identidad(r)),antes=ant?.[col]??null;return{...r,valor:r[col],antes,delta:antes==null?null:r[col]-antes,dominante:dominante(r)};}),visibles=todos.filter(r=>(!q||(r.cod+' '+r.producto+' '+r.familia).toLowerCase().includes(q))&&r.valor>=Number(s.min||0));
    visibles.sort((a,b)=>{const x=s.orden==='producto'?a.producto:s.orden==='delta'?a.delta:a.valor,y=s.orden==='producto'?b.producto:s.orden==='delta'?b.delta:b.valor;if(x==null)return y==null?0:1;if(y==null)return-1;return(typeof x==='string'?x.localeCompare(y,'es'):y-x);});return{todos,visibles,col};}
  function comparar(B,k){const t=B.tot.get(k),a=B.tot.get(k-1),p=B.P.periodos[k],ant=B.P.periodos[k-1],c=[['Sin plato',t=>t.baja+t.otras+t.falt],['Bajas',t=>t.baja],['Otras salidas',t=>t.otras],['Faltante',t=>t.falt],['Sobrante',t=>t.sobr],['A un plato',t=>t.venta+t.cort+t.evvi],['Operación',t=>t.operacion]];return c.map(([concepto,f])=>{const actual=f(t),antes=a?f(a):null;return{concepto,actual,antes,delta:antes==null?null:actual-antes,por_dia:actual/p.dias,antes_por_dia:a?antes/ant.dias:null};});}
  function grafico(B,k){return ks(B.P,k).map(j=>({k:j,partes:['baja','otras','falt','sobr'].map(c=>({c,v:(c==='sobr'?-1:1)*B.tot.get(j)[c]}))}));}
  // Los cuatro indicadores de un cierre y la parte con documento (regla #772).
  const conDoc=t=>{const s=t.baja+t.otras+t.falt;return s>0?(t.baja+t.otras)/s*100:null;};
  function docAntes(P){const ts=P.totales.slice(0,-3);let a=0,b=0;for(const t of ts){a+=t.baja+t.otras;b+=t.baja+t.otras+t.falt;}return b>0&&ts.length>=3?a/b*100:null;}
  function kpis(B,k){const t=B.tot.get(k),a=B.tot.get(k-1),P=B.P,sol=x=>`${Math.round(x)<0?'−':''}S/ ${Math.round(Math.abs(x)).toLocaleString('en-US')}`,sin=t.baja+t.otras+t.falt,plato=t.venta+t.cort+t.evvi,d=conDoc(t),d0=docAntes(P),esc=x=>String(x??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
    const kpi=(rot,val,sub,tip,cl='')=>`<div class="dst-kpi ${cl}" title="${esc(tip)}"><span>${esc(rot)}</span><b>${esc(val)}</b><small>${esc(sub)}</small></div>`;
    const dSin=a?sin-(a.baja+a.otras+a.falt):null;
    return kpi('Salió sin plato',sol(sin),`${Math.round(sin/((sin+plato)||1)*100)} % de lo que salió${dSin!=null?` · ${dSin<0?'−':'+'}S/ ${Math.round(Math.abs(dSin)).toLocaleString('en-US')} vs ${P.periodos[k-1].corto}`:''}`,'Bajas + otras notas + faltante del conteo. Sin los insumos de operación.','malo')
      +kpi('Con documento',d==null?'—':`${Math.round(d)} %`,`${sol(t.baja+t.otras)} con nota${d0!=null?` · antes: ${Math.round(d0)} %`:''}`,'De lo que salió sin plato, cuánto dejó una nota; lo demás sólo apareció al contar. Cálculo propio: mide el rastro, no cuánto se perdió.',d!=null&&d<20?'alerta':'')
      +kpi('Faltante del conteo',sol(t.falt),`sobrante ${sol(t.sobr)} · neto ${sol(t.sobr-t.falt)}`,'Lo que el conteo encontró de menos. El sobrante va aparte: no descuenta lo que salió sin plato.')
      +kpi('A un plato',sol(plato),`cortesías ${sol(t.cort)} · eventos ${sol(t.evvi)}`,'El descargo de ventas del kardex, con las cortesías. Los insumos de operación van aparte.');}
  return{preparar,ks,ranking,comparar,grafico,dominante,kpis,conDoc,docAntes};
})();
window.__destinoDatos=DESTINO;
