// Gráficos chicos de las piezas propias (regla #847), traducidos de los
// componentes de Tremor (https://github.com/tremorlabs/tremor, Apache 2.0:
// Copyright © 2024 Tremor Labs, Inc.). No se copió su código —React, Tailwind y
// Recharts no corren acá—: se rehízo la FORMA en JS plano, con la paleta y la
// escala 12/17 de la app. Cinco piezas, cada una devuelve HTML (un string), como
// `icono()`; la pieza que las usa pone el resultado donde quiera y escucha sus
// clics por delegación (`data-id`). Va antepuesto al .js de cada pieza, junto con
// `mini.css` (y con `iconos.css`, que da el nombre al cursor de `data-tip`).
//
//   miniBarras(filas, op)   lista con una barra de fondo por monto (BarList)
//   miniRastro(celdas, op)  fila de cuadritos, uno por período (Tracker)
//   miniTramos(tramos, op)  una barra partida en tramos, con marcador (CategoryBar)
//   miniChispa(serie, op)   curva o barras sin ejes, en una línea de texto (SparkChart)
//   miniDelta(act, base, op) la cápsula «▲ 6 %» (BadgeDelta)
//
// Nada mide el DOM: los anchos van en porcentajes y la chispa en un viewBox
// estirado, así que «Ampliar» o el celular no piden redibujar.
const miniEsc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const miniNum=new Intl.NumberFormat('es-PE',{maximumFractionDigits:0});
const miniSoles=v=>`${v<0?'−':''}S/ ${miniNum.format(Math.abs(v))}`;
const miniNumero=v=>v!=null&&isFinite(v);

// BarList. `filas`: [{id, rotulo, valor, sub?, tip?}]. El ancho de cada barra es
// |valor| ÷ el mayor |valor| (o `op.max`): un faltante se dibuja igual que un
// sobrante y el signo lo dice la cifra, o `op.tono` ('neg' rojo, 'pos' verde)
// cuando el color significa algo — rojo y verde no son decoración (#771).
// `op.elegido` marca una fila; `op.formato` escribe la cifra (soles por defecto).
function miniBarras(filas,op={}){
  const fmt=op.formato||miniSoles,max=op.max||Math.max(0,...filas.map(f=>Math.abs(+f.valor||0)))||1;
  const tono=op.tono?` ${op.tono}`:'';
  const li=filas.map(f=>{
    const v=+f.valor||0,pct=Math.min(100,Math.abs(v)/max*100);
    const sel=op.elegido!=null&&String(op.elegido)===String(f.id)?' on':'';
    const sub=f.sub?`<span class="mbl-sub">${miniEsc(f.sub)}</span>`:'';
    return `<li class="mbl-f${sel}" data-id="${miniEsc(f.id)}"${f.tip?` title="${miniEsc(f.tip)}"`:''}>`
      +`<span class="mbl-b${tono}" style="width:${pct.toFixed(2)}%"></span>`
      +`<span class="mbl-r">${miniEsc(f.rotulo)}${sub}</span>`
      +`<span class="mbl-v">${miniEsc(fmt(v))}</span></li>`;
  }).join('');
  const cab=op.titulo?`<div class="mbl-cab"><span>${miniEsc(op.titulo)}</span><span>${miniEsc(op.columna||'')}</span></div>`:'';
  return `<div class="mbl${op.clic?' clic':''}">${cab}<ol class="mbl-l">${li}</ol></div>`;
}

// Tracker. `celdas`: [{id?, rotulo, estado, tip?}], estado ∈ ok | ojo | mal | nada.
// Un cuadrito por período (mes, cierre, día) y su texto al cursor. `op.pie` pone
// los rótulos de la primera y la última celda debajo.
function miniRastro(celdas,op={}){
  const c=celdas.map(x=>{
    const e=['ok','ojo','mal'].includes(x.estado)?x.estado:'nada';
    const tip=x.tip||x.rotulo||'';
    return `<span class="mrs-c ${e}"${x.id!=null?` data-id="${miniEsc(x.id)}"`:''} data-tip="${miniEsc(tip)}" role="img" aria-label="${miniEsc(tip)}"></span>`;
  }).join('');
  const pie=op.pie&&celdas.length?`<div class="mrs-pie"><span>${miniEsc(celdas[0].rotulo)}</span><span>${miniEsc(celdas[celdas.length-1].rotulo)}</span></div>`:'';
  return `<div class="mrs"><div class="mrs-f">${c}</div>${pie}</div>`;
}

// CategoryBar. `tramos`: [{hasta, estado, rotulo?}] en orden, desde `op.desde`
// (0). `op.valor` pone el marcador; `op.meta`, una raya fina. `op.formato`
// escribe los bordes debajo (por defecto «n %»). Para «% de costo contra el 30 %».
function miniTramos(tramos,op={}){
  const desde=op.desde??0,fin=tramos.length?tramos[tramos.length-1].hasta:1,span=(fin-desde)||1;
  const fmt=op.formato||(v=>`${miniNum.format(v)} %`);
  const pos=v=>Math.max(0,Math.min(100,(v-desde)/span*100)).toFixed(2);
  let ant=desde;
  const t=tramos.map(x=>{const w=(x.hasta-ant)/span*100;ant=x.hasta;
    return `<span class="mtr-t ${miniEsc(x.estado||'nada')}" style="width:${w.toFixed(2)}%"${x.rotulo?` title="${miniEsc(x.rotulo)}"`:''}></span>`;}).join('');
  const meta=miniNumero(op.meta)?`<span class="mtr-meta" style="left:${pos(op.meta)}%" data-tip="Meta: ${miniEsc(fmt(op.meta))}"></span>`:'';
  const val=miniNumero(op.valor)?`<span class="mtr-m" style="left:${pos(op.valor)}%" data-tip="${miniEsc(op.tipValor||fmt(op.valor))}"></span>`:'';
  const bordes=[desde,...tramos.map(x=>x.hasta)].map(v=>`<span style="left:${pos(v)}%">${miniEsc(fmt(v))}</span>`).join('');
  return `<div class="mtr"><div class="mtr-b">${t}${meta}${val}</div><div class="mtr-e">${bordes}</div></div>`;
}

// SparkChart. `serie`: números (null = sin dato, corta la curva). `op.tipo`:
// 'linea' (por defecto, con un área tenue) o 'barras'. `op.ultimo` resalta el
// último punto. Sin ejes ni rótulos: es una forma, la cifra va al lado.
function miniChispa(serie,op={}){
  const n=serie.length,W=100,H=32,pad=3;
  if(!n)return '<span class="msp"></span>';
  // Las barras arrancan en cero (la altura es el monto); la línea, en su mínimo, o
  // una venta de 118 a 170 se vería plana.
  const vals=serie.filter(miniNumero),lo=op.tipo==='barras'?Math.min(0,...vals):Math.min(...vals),hi=Math.max(...vals,lo+1e-9);
  const y=v=>H-pad-(v-lo)/(hi-lo)*(H-2*pad);
  const tip=op.tip?` data-tip="${miniEsc(op.tip)}"`:'';
  if(op.tipo==='barras'){
    const bw=W/n,b=serie.map((v,i)=>miniNumero(v)?`<rect class="msp-b${i===n-1&&op.ultimo?' u':''}" x="${(i*bw+bw*.15).toFixed(2)}" y="${Math.min(y(v),y(0)).toFixed(2)}" width="${(bw*.7).toFixed(2)}" height="${Math.max(.6,Math.abs(y(0)-y(v))).toFixed(2)}"/>`:'').join('');
    return `<span class="msp"${tip}><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">${b}</svg></span>`;
  }
  const x=i=>n===1?W/2:i/(n-1)*W;
  let d='',area='',abierto=false,ini=0;
  serie.forEach((v,i)=>{
    if(!miniNumero(v)){if(abierto){area+=`L${x(i-1).toFixed(2)},${H}L${x(ini).toFixed(2)},${H}Z`;abierto=false;}return;}
    const p=`${x(i).toFixed(2)},${y(v).toFixed(2)}`;
    if(!abierto){d+=`M${p}`;area+=`M${p}`;abierto=true;ini=i;}else{d+=`L${p}`;area+=`L${p}`;}
  });
  if(abierto)area+=`L${x(n-1).toFixed(2)},${H}L${x(ini).toFixed(2)},${H}Z`;
  const u=op.ultimo&&miniNumero(serie[n-1])?`<span class="msp-u" style="left:${x(n-1)}%;top:${(y(serie[n-1])/H*100).toFixed(2)}%"></span>`:'';
  return `<span class="msp"${tip}><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true"><path class="msp-a" d="${area}"/><path class="msp-l" d="${d}"/></svg>${u}</span>`;
}

// BadgeDelta. La variación de `actual` contra `base` en una cápsula: «▲ 6 %»,
// «▼ 12 %», «= 0 %», o «nuevo» sin base. El color sólo si `op.sentido` dice qué
// es bueno: 'sube-malo' (precio, costo: subir es rojo), 'sube-bueno' (venta);
// sin sentido, gris: comprar menos no es bueno ni malo (#771). `op.texto`
// cambia lo escrito; `op.tip`, el nombre al cursor.
function miniDelta(actual,base,op={}){
  let txt,cls='neu';
  if(!miniNumero(base)||base===0){txt=miniNumero(actual)&&actual!==0?'nuevo':'—';}
  else{
    const p=(actual-base)/Math.abs(base)*100,r=Math.round(p);
    txt=r===0?'= 0 %':`${r>0?'▲':'▼'} ${miniNum.format(Math.abs(r))} %`;
    if(r!==0&&op.sentido){const malo=op.sentido==='sube-malo'?r>0:r<0;cls=malo?'mal':'bien';}
  }
  const tip=op.tip?` data-tip="${miniEsc(op.tip)}"`:'';
  return `<span class="mdl ${cls}"${tip}>${miniEsc(op.texto||txt)}</span>`;
}
