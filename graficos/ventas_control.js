/* Control de pedidos: las reglas del POS se reciben de Python (#723). */
const CONTROL=(()=>{
  const SUBS=['Anulaciones','Transferencias','Tiempos','Ocupación'],GRANOS=['Día','Semana','Mes'],DAY=86400000;
  const nfmt=new Intl.NumberFormat('es-PE',{maximumFractionDigits:0});
  const vfmt=new Intl.NumberFormat('es-PE',{minimumFractionDigits:2,maximumFractionDigits:2});
  const dfmt=new Intl.NumberFormat('es-PE',{maximumFractionDigits:1});
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm=v=>String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const suma=(rs,k)=>rs.reduce((a,r)=>a+(r[k]||0),0),dia=f=>Math.floor(f/DAY);
  const dinero=v=>v==null?'—':`S/ ${vfmt.format(v)}`;
  const mins=v=>v==null?'—':`${dfmt.format(v)} min`;
  const fecha=v=>v==null?'—':new Date(v).toISOString().slice(0,16).replace('T',' ');
  const cmp=(a,b)=>a<b?-1:a>b?1:0;
  const agrupar=(rs,key)=>{const m=new Map();for(const r of rs){const k=typeof key==='function'?key(r):r[key];if(!m.has(k))m.set(k,[]);m.get(k).push(r);}return m;};
  function quantil(xs,q=.5){const a=xs.filter(v=>typeof v==='number'&&Number.isFinite(v)).sort((a,b)=>a-b);if(!a.length)return null;const i=(a.length-1)*q,l=Math.floor(i);return a[l]+(a[Math.ceil(i)]-a[l])*(i-l);}
  const med=(rs,k,q=.5)=>quantil(rs.map(r=>r[k]),q);
  function leer(P){const out={P};for(const k of ['p','t','b'])out[k]=P[k].map((a,i)=>Object.fromEntries([['id',`${k}${i}`],...P[`c${k}`].map((c,j)=>[c,a[j]])]));out.porPedido=new Map(out.p.map(r=>[r.ped,r]));return out;}
  function inicial(v={}){return{gran:'Día',sub:'Anulaciones',mesa:'',mesero:'',q:'',tipos:{},foco:null,foto:null,ped:null,origen:null,destino:null,lista:'Grupos',mesaLista:null,grupoLista:null,lentos:false,orden:{},...v};}
  function resumen(p,t,b){
    const an=p.filter(r=>r.anulado),pa=t.filter(r=>r.tipo==='PLATO ANULADO'),tr=t.filter(r=>r.tipo==='TRANSFERENCIA'),coc=pa.filter(r=>r.cocina),cort=tr.filter(r=>r.clase==='A cortesía');
    const anulado=suma(an,'monto_anulado')+suma(pa,'venta'),consumo=suma(p,'monto');
    const r={pedidos:p.length,ped_anul:an.length,m_anul:suma(an,'monto_anulado'),pl_anul:pa.length,m_pl:suma(pa,'venta'),
      pl_cocina:coc.length,m_cocina:suma(coc,'venta'),pct:consumo+anulado?anulado/(consumo+anulado):0,
      n_tr:tr.length,s_tr:suma(tr,'venta'),n_div:tr.filter(r=>r.clase==='Cuenta dividida').length,
      cort:cort.length,m_cort:suma(cort,'venta'),n_mesa:tr.filter(r=>r.clase==='Entre mesas').length,mesas:b.length};
    for(const k of ['espera','comida','sobremesa','cobro','total'])r[`t_${k}`]=med(b,k);
    r.p90=med(b,'total',.9);r.precuentas=b.filter(r=>r.n_precuenta>1).length;return r;
  }
  function porMesa(b){return[...agrupar(b,'mesa')].map(([mesa,rs])=>({id:`mesa:${mesa}`,mesa,usos:rs.length,personas:suma(rs,'adultos'),consumo:suma(rs,'monto'),minutos:suma(rs,'total'),x_hora:suma(rs,'total')?suma(rs,'monto')/(suma(rs,'total')/60):null,mediana:med(rs,'total')})).sort((a,b)=>b.consumo-a.consumo||cmp(a.mesa,b.mesa));}
  function porGrupo(b,P){return P.grupos.flatMap(grupo=>{const x=b.filter(r=>r.grupo===grupo);return x.length?[{id:`grupo:${grupo}`,grupo,mesas:x.length,total:med(x,'total'),sobremesa:med(x,'sobremesa'),x_mesa:suma(x,'monto')/x.length,x_persona:suma(x,'adultos')?suma(x,'monto')/suma(x,'adultos'):null}]:[];});}
  function ocupacion(b,dias){const z=dias.map(()=>Array(28).fill(0)),indices=new Map(dias.map((d,i)=>[d,i]));for(const r of b){const i=indices.get(dia(r.dia));if(i===undefined)continue;for(let j=r.desde;j<=r.hasta;j++)if(j>=0&&j<28)z[i][j]++;}return z;}
  function calcular(B,s,cache={}){
    const P=B.P,key=JSON.stringify([s.mesa,s.mesero]);
    if(cache.key!==key){
      const p=B.p.filter(r=>(!s.mesa||r.mesa===s.mesa)&&(!s.mesero||r.mesero===s.mesero)),ids=new Set(p.map(r=>r.ped));
      const t=s.mesa||s.mesero?B.t.filter(r=>ids.has(r.ped)):B.t;
      const b=B.b.filter(r=>ids.has(r.ped)),z=ocupacion(b,P.dias),nmesas=new Set(b.map(r=>r.mesa)).size;
      let pico=null;for(let i=0;i<z.length;i++)for(let j=0;j<28;j++)if(z[i][j]>(pico?.n||0))pico={n:z[i][j],dia:P.dias[i],slot:j};
      cache.key=key;cache.core={p,t,b,z,nmesas,pico,total:resumen(p,t,b),periodos:{}};
    }
    const C=cache.core,plan=P.planes[s.gran];
    if(!C.periodos[s.gran]){
      const kp=r=>plan.mapa[dia(r.dia)],pg=agrupar(C.p,kp),tg=agrupar(C.t,kp),bg=agrupar(C.b,kp);
      const keys=[...new Set([...pg.keys(),...tg.keys()])].sort();
      C.periodos[s.gran]=keys.map(k=>({clave:k,periodo:plan.rotulos[k],...resumen(pg.get(k)||[],tg.get(k)||[],bg.get(k)||[])}));
    }
    const series=C.periodos[s.gran],foco=series.some(r=>r.clave===s.foco)?s.foco:null;
    const filt=rs=>foco?rs.filter(r=>plan.mapa[dia(r.dia)]===foco):rs;
    const p=filt(C.p),t=filt(C.t),b=filt(C.b),scope=resumen(p,t,b),pp=B.porPedido;
    let eventos=[];
    if(s.sub==='Anulaciones'){
      eventos=t.filter(r=>r.tipo==='PLATO ANULADO').map(r=>({...r,fecha:r.f_trx,que:r.producto,valor:r.venta,mesa:pp.get(r.ped)?.mesa||'',mesero:pp.get(r.ped)?.mesero||''}));
      eventos.push(...p.filter(r=>r.anulado).map(r=>({id:r.id,ped:r.ped,destino:'',fecha:r.f_anul??r.apertura,que:'Pedido entero',valor:r.monto_anulado,usuario:r.usu_anul,clase:r.motivo,obs:r.obs_anul,mesa:r.mesa,mesero:r.mesero})));
    }else if(s.sub==='Transferencias')eventos=t.filter(r=>r.tipo==='TRANSFERENCIA').map(r=>({...r,fecha:r.f_trx,que:r.producto,valor:r.venta,mesa:pp.get(r.ped)?.mesa||'',mesero:pp.get(r.ped)?.mesero||''}));
    eventos.sort((a,b)=>b.valor-a.valor||(b.fecha||0)-(a.fecha||0)||cmp(a.id,b.id));
    const tipos=[...new Set(eventos.map(r=>r.clase))].sort(),tipo=s.tipos[s.sub]||'',q=norm(s.q);
    const filtrarEventos=eventos.filter(r=>(!tipo||r.clase===tipo)&&(!q||norm([r.ped,r.destino,r.que,r.usuario,r.obs,r.clase,r.mesa,r.mesero].join(' ')).includes(q)));
    const foto=s.sub==='Ocupación'&&s.foto?s.foto:null;
    let pedidos=b;
    if(foto)pedidos=pedidos.filter(r=>dia(r.dia)===foto.dia&&r.desde<=foto.slot&&r.hasta>=foto.slot);
    if(s.mesaLista)pedidos=pedidos.filter(r=>r.mesa===s.mesaLista);
    if(s.grupoLista)pedidos=pedidos.filter(r=>r.grupo===s.grupoLista);
    if(s.sub==='Tiempos'&&s.lentos&&scope.p90!=null)pedidos=pedidos.filter(r=>r.total>=scope.p90);
    pedidos=pedidos.filter(r=>!q||norm([r.ped,r.mesa,r.mesero,r.grupo,r.servicio].join(' ')).includes(q)).sort((a,b)=>b.total-a.total||cmp(a.ped,b.ped));
    const grupos=porGrupo(b,P).filter(r=>!q||norm(r.grupo).includes(q));
    const mesas=porMesa(b).filter(r=>!q||norm(r.mesa).includes(q));
    let modo='eventos',filas=filtrarEventos;
    if(s.sub==='Tiempos'){modo=s.lista==='Pedidos'?'pedidos':'grupos';filas=modo==='pedidos'?pedidos:grupos;}
    if(s.sub==='Ocupación'){modo=foto||s.mesaLista||s.lista==='Pedidos'?'pedidos':'mesas';filas=modo==='pedidos'?pedidos:mesas;}
    const sugerido=filas.find(r=>r.ped)?.ped||pedidos[0]?.ped||p[0]?.ped||null;
    const elegido=s.ped||sugerido,pedido=pp.get(elegido)||null,tiempo=B.b.find(r=>r.ped===elegido)||null;
    const relacionados=B.t.filter(r=>elegido&&(r.ped===elegido||r.destino===elegido)).sort((a,b)=>(a.f_trx??Infinity)-(b.f_trx??Infinity));
    const scopeDias=P.dias.filter(d=>!foco||plan.mapa[d]===foco);
    return{...C,series,foco,pScope:p,tScope:t,bScope:b,scope,scopeDias,eventos,filas,modo,tipos,tipo,
      pedido,tiempo,elegido,relacionados,foto,fueraFiltro:!!pedido&&!C.p.some(r=>r.ped===pedido.ped),
      mesasOps:[...new Set(B.p.map(r=>r.mesa))].sort(),meserosOps:[...new Set(B.p.map(r=>r.mesero))].sort()};
  }
  const c=(k,n,t='')=>({k,n,t});
  const COLPER={
    Anulaciones:[c('pedidos','Pedidos','n'),c('ped_anul','Pedidos anulados','n'),c('m_anul','Valor pedidos','v'),c('pl_anul','Lín. anuladas','n'),c('m_pl','Valor líneas','v'),c('pl_cocina','Ya en cocina','n'),c('m_cocina','Valor cocina','v'),c('pct','% anulado','pct')],
    Transferencias:[c('n_tr','Líneas','n'),c('s_tr','Valor','v'),c('n_div','Cuenta dividida','n'),c('cort','A cortesía','n'),c('m_cort','Valor a cortesía','v'),c('n_mesa','Entre mesas','n')],
    Tiempos:[c('mesas','Mesas cobradas','n'),c('t_espera','1er plato','m'),c('t_comida','Comida','m'),c('t_sobremesa','Sobremesa','m'),c('t_cobro','Cobro','m'),c('t_total','Total','m'),c('p90','P90 total','m')],
  };
  const COLEVENT=[c('fecha','Fecha','f'),c('que','Qué'),c('valor','Valor','v'),c('usuario','Quién'),c('clase','Tipo / motivo'),c('ped','Pedido'),c('destino','Destino'),c('mesa','Mesa'),c('obs','Observación')];
  const COLPED=[c('ped','Pedido'),c('mesa','Mesa'),c('mesero','Mesero'),c('adultos','Adultos','n'),c('total','Total','m'),c('espera','1er plato','m'),c('comida','Comida','m'),c('sobremesa','Sobremesa','m'),c('cobro','Cobro','m'),c('monto','Consumo','v'),c('n_precuenta','Precuentas','n'),c('servicio','Servicio')];
  const COLGRUPO=[c('grupo','Adultos por mesa'),c('mesas','Mesas','n'),c('total','Total','m'),c('sobremesa','Sobremesa','m'),c('x_mesa','Consumo / mesa','v'),c('x_persona','Consumo / adulto','v')];
  const COLMESA=[c('mesa','Mesa'),c('usos','Usos','n'),c('personas','Adultos','n'),c('consumo','Consumo','v'),c('x_hora','Consumo / hora','v'),c('mediana','Duración típica','m')];
  const COLTRX=[c('f_trx','Fecha','f'),c('ped','Origen'),c('destino','Destino'),c('producto','Producto'),c('cant','Cantidad','n'),c('venta','Valor','v'),c('clase','Tipo'),c('usuario','Quién'),c('obs','Observación')];
  const VISIBLE={
    Anulaciones:[c('pedidos','Pedidos','n'),{...c('ped_anul','Anulados','n'),extra:'m_anul'},
      {...c('pl_anul','Platos','n'),extra:'m_pl'},{...c('pl_cocina','En cocina','n'),extra:'m_cocina'},c('pct','% anulado','pct')],
    Transferencias:[c('n_tr','Líneas','n'),c('s_tr','Valor','v'),c('n_div','Dividida','n'),
      {...c('cort','A cortesía','n'),extra:'m_cort'},c('n_mesa','Entre mesas','n')],
    Tiempos:COLPER.Tiempos.map(c=>({...c,n:c.k==='mesas'?'Mesas':c.k==='p90'?'P90':c.n})),
  };
  function form(v,col){if(col.t==='v')return dinero(v);if(col.t==='m')return mins(v);if(col.t==='f')return fecha(v);if(col.t==='pct')return v==null?'—':`${dfmt.format(v*100)} %`;if(col.t==='n')return v==null?'—':dfmt.format(v);return v??'';}
  function tabla(G,id,cols,filas,accion=''){
    const ord=G.s.orden[id],fs=filas.slice();
    if(ord)fs.sort((a,b)=>{const x=a[ord.k],y=b[ord.k];if(x==null)return y==null?0:1;if(y==null)return-1;return(typeof x==='number'&&typeof y==='number'?x-y:cmp(String(x),String(y)))*ord.d;});
    G.tablas[id]={cols,filas:fs,accion,limite:150};
    return`<div class="ctl-scroll" data-tabla="${id}" tabindex="0"><table><thead><tr>${cols.map(col=>`<th><button data-a="orden" data-id="${id}" data-v="${col.k}">${esc(col.n)}${ord?.k===col.k?ord.d===1?' ↑':' ↓':''}</button></th>`).join('')}</tr></thead><tbody>${rows(G,id,0,150)}</tbody></table>${fs.length?'':'<p class="ctl-vacio">Nada que mostrar con esta selección.</p>'}</div>`;
  }
  function rows(G,id,a,b){const t=G.tablas[id];return t.filas.slice(a,b).map(r=>`<tr ${t.accion?`data-a="${t.accion}" data-v="${esc(r.id??r.clave??r.ped??'')}" tabindex="0"`:''} class="${r.ped&&r.ped===G.D.elegido||r.clave&&r.clave===G.D.foco?'elegido':''}">${t.cols.map(col=>`<td class="${col.t?'num':''}" title="${esc(form(r[col.k],col))}">${esc(form(r[col.k],col))}${col.extra?`<small class="ctl-subcelda">${dinero(r[col.extra])}</small>`:''}</td>`).join('')}</tr>`).join('');}
  function seg(ops,v,accion){return`<div class="ctl-seg">${ops.map(op=>`<button data-a="${accion}" data-v="${esc(op)}" class="${v===op?'on':''}" aria-pressed="${v===op}">${esc(op)}</button>`).join('')}</div>`;}
  function selector(label,k,ops,sel){const oferta=[...ops];if(sel&&!oferta.includes(sel))oferta.push(sel);return`<label class="ctl-select"><span>${label}</span><select data-select="${k}" aria-label="${label}"><option value="">Todos</option>${oferta.filter(Boolean).map(v=>`<option value="${esc(v)}" ${v===sel?'selected':''}>${esc(v)}</option>`).join('')}</select></label>`;}
  function ambito(G){return G.D.foco?G.P.planes[G.s.gran].rotulos[G.D.foco]:'Todo el rango';}
  function clavesAmbito(G){
    const D=G.D,top=(rs,k,valor=null)=>[...agrupar(rs,r=>r[k]||'Sin dato')].map(([n,g])=>({n,v:valor?suma(g,valor):g.length})).filter(r=>r.v>0).sort((a,b)=>b.v-a.v||cmp(a.n,b.n)).slice(0,3).map(r=>`${r.n}: ${valor?dinero(r.v):nfmt.format(r.v)}`).join(' · ')||'Sin casos';
    let lineas=[];
    if(G.s.sub==='Anulaciones'){
      const an=D.pScope.filter(r=>r.anulado),pa=D.tScope.filter(r=>r.tipo==='PLATO ANULADO');
      lineas=[['Motivos',top(an,'motivo')],['Clases de platos',top(pa,'clase')],['Quién anula',top([...an.map(r=>({usuario:r.usu_anul})),...pa],'usuario')],['Platos por valor anulado',top(pa,'producto','venta')]];
    }else if(G.s.sub==='Transferencias'){
      const tr=D.tScope.filter(r=>r.tipo==='TRANSFERENCIA');lineas=[['Tipos',top(tr,'clase')],['Quién transfiere',top(tr,'usuario')],['Platos más movidos',top(tr,'producto')]];
    }else if(G.s.sub==='Tiempos'){
      const mas=D.bScope.reduce((a,r)=>!a||r.total>a.total?r:a,null);
      lineas=[['Por servicio',[...agrupar(D.bScope,'servicio')].map(([n,g])=>`${n}: ${mins(med(g,'total'))}`).join(' · ')||'Sin datos'],['Precuentas',`${D.scope.precuentas} pedidos con más de una precuenta`],['Duración máxima',mas?`${mins(mas.total)} · mesa ${mas.mesa}`:'Sin datos']];
    }
    return lineas.length?`<details class="ctl-claves" ${G.s.claves?'open':''}><summary>Claves del ámbito</summary>${lineas.map(([n,v])=>`<p><b>${esc(n)}:</b> ${esc(v)}</p>`).join('')}</details>`:'';
  }
  function heat(G){
    const D=G.D,P=G.P,max=Math.max(1,D.pico?.n||0),ds=D.scopeDias;
    G.heat={dias:ds,limite:45,max};
    if(!P.fuentes.pedidos)return '<p class="ctl-vacio">No hay pedidos disponibles para reconstruir la ocupación.</p>';
    return`<div class="ctl-scroll ctl-heat" data-heat tabindex="0"><table><thead><tr><th>Día</th>${P.slots.map((s,j)=>`<th>${j%2?'':s}</th>`).join('')}</tr></thead><tbody>${heatRows(G,0,45)}</tbody></table>${!D.b.length?'<p class="ctl-vacio">Sin mesas cobradas válidas para reconstruir la ocupación.</p>':''}</div>`;
  }
  function heatRows(G,a,b){return G.heat.dias.slice(a,b).map(d=>{const i=G.P.dias.indexOf(d);return`<tr><td>${esc(new Date(d*DAY).toISOString().slice(0,10))}</td>${G.D.z[i].map((n,j)=>`<td><button data-a="foto" data-dia="${d}" data-slot="${j}" style="--nivel:${n/G.heat.max}" class="ctl-celda ${G.s.foto?.dia===d&&G.s.foto.slot===j?'elegido':''}" title="${new Date(d*DAY).toISOString().slice(0,10)} ${G.P.slots[j]} · ${n} pedidos abiertos, ${G.D.nmesas} mesas observadas" aria-label="${new Date(d*DAY).toISOString().slice(0,10)} ${G.P.slots[j]}: ${n}">${n||''}</button></td>`).join('')}</tr>`;}).join('');}
  function dibujar(G){
    const {s,P,root}=G;G.D=calcular(G.B,s,G.cache);const D=G.D,T=D.total;G.tablas={};
    const active=root.querySelector('input:focus'),foco=active?[active.dataset.input,active.selectionStart,active.selectionEnd]:null;
    const scroll=[...root.querySelectorAll('[data-tabla]')].map(e=>[e.dataset.tabla,e.scrollTop,e.scrollLeft]);
    const kpi=(rot,v,nota,tip='')=>`<div class="ctl-kpi" title="${esc(tip||nota)}"><span>${esc(rot)}</span><b>${esc(v)}</b><small>${esc(nota)}</small></div>`;
    let html=`<section class="ctl-card ctl-main"><header><h3>Control de pedidos</h3><p>${esc(P.rango.join(' al '))} · ${P.turno?'Día del turno':'Fecha de apertura / transacción'}${P.canales.length?` · Canal: ${esc(P.canales.join(', '))}`:''}</p></header>`
      +`<div class="ctl-controles">${seg(SUBS,s.sub,'sub')}${seg(GRANOS,s.gran,'gran')}</div>`
      +`<div class="ctl-filtros">${selector('Mesa','mesa',D.mesasOps,s.mesa)}${selector('Mesero','mesero',D.meserosOps,s.mesero)}${s.mesa||s.mesero?'<button data-a="filtros">Quitar filtros</button>':''}<span>Pedidos y transacciones · el canal de Ventas se aplica al origen</span></div>`
      +`<div class="ctl-kpis">${kpi('Pedidos',P.fuentes.pedidos?nfmt.format(T.pedidos):'Sin datos',`${T.ped_anul} anulados · ${dinero(T.m_anul)}`)}${kpi('Platos anulados',P.fuentes.transacciones?nfmt.format(T.pl_anul):'Sin datos',dinero(T.m_pl),`${T.pl_anul} líneas. ${T.pl_cocina} ya en cocina por ${dinero(T.m_cocina)}. No implica pérdida confirmada.`)}${kpi('Transferencias',P.fuentes.transacciones?nfmt.format(T.n_tr):'Sin datos',dinero(T.s_tr),`${T.cort} a cortesía por ${dinero(T.m_cort)}`)}${kpi('Duración típica',mins(T.t_total),`Sobremesa: ${mins(T.t_sobremesa)}`,'Mediana de pedidos cobrados con mesa y duración total válida. Excluye pedidos sin mesa y anulados. Consumo del pedido, no venta neta.')} ${kpi('Pico observado',D.pico?`${D.pico.n} pedidos`:'—',D.pico?`${new Date(D.pico.dia*DAY).toISOString().slice(0,10)} ${P.slots[D.pico.slot]}`:'Sin ocupación reconstruible',`${D.nmesas} mesas distintas usadas. Es una reconstrucción de pedidos cobrados; no aforo ni asientos.`)}</div>`;
    if(!P.fuentes.pedidos||!P.fuentes.transacciones)html+=`<p class="ctl-aviso">Sin registros recibidos de: ${[!P.fuentes.pedidos?'pedidos':'',!P.fuentes.transacciones?'transacciones':''].filter(Boolean).join(' y ')}. Puede ser un rango vacío o una fuente no disponible. Los indicadores que dependen de esos registros no se pueden completar.</p>`;
    html+=`<div class="ctl-titulo-zona"><b>${s.sub==='Ocupación'?'Ocupación por día y media hora':'Resumen por período'}</b><span>Totales del rango filtrado</span><button data-a="excel">Excel de esta vista ↓</button></div><div class="ctl-cuerpo"><div class="ctl-izq">`;
    if(s.sub==='Ocupación')html+=heat(G);
    else html+=tabla(G,'periodos',[c('periodo',s.gran),...VISIBLE[s.sub]],D.series,'periodo');
    html+=`<p class="ctl-nota">${s.sub==='Ocupación'?`${D.nmesas} mesas observadas. Incluye apertura y comprobante en la foto; de 12:00 a 01:30. Tocá una celda para investigar.`:'Tocá un período para acotar el detalle. Los importes no se redondean al sumar.'}</p></div><div class="ctl-der"><div class="ctl-ambito"><b>${esc(ambito(G))}${s.mesaLista?` · Mesa ${esc(s.mesaLista)}`:''}${s.grupoLista?` · Grupo ${esc(s.grupoLista)} adultos`:''}${D.foto?` · ${new Date(D.foto.dia*DAY).toISOString().slice(0,10)} ${P.slots[D.foto.slot]}`:''}</b>${D.foco||D.foto||s.mesaLista||s.grupoLista?'<button data-a="rango">Ver todo</button>':''}</div>`
      +`<div class="ctl-buscar"><input type="search" data-input="q" aria-label="Buscar en el detalle" placeholder="Buscar pedido, producto, persona, mesa…" value="${esc(s.q)}">${D.modo==='eventos'?selector('Tipo / motivo','tipo',D.tipos,D.tipo):''}</div>`;
    if(s.sub==='Tiempos'||s.sub==='Ocupación')html+=`<div class="ctl-analisis">${seg(s.sub==='Tiempos'?['Grupos','Pedidos']:['Mesas','Pedidos'],D.modo==='pedidos'?'Pedidos':s.sub==='Tiempos'?'Grupos':'Mesas','lista')}${s.sub==='Tiempos'?`<span>P90: ${mins(D.scope.p90)} · ${D.bScope.length} pedidos</span><label title="Duraciones desde el percentil 90 del ámbito, incluyendo empates. Es una descripción, no un objetivo de servicio."><input type="checkbox" data-lentos ${s.lentos?'checked':''}> Desde P90</label>`:''}</div>`;
    const cols={eventos:COLEVENT,pedidos:COLPED,grupos:COLGRUPO,mesas:COLMESA}[D.modo];
    html+=clavesAmbito(G)+tabla(G,'detalle',cols,D.filas,'detalle')+`<p class="ctl-nota">${D.filas.length} filas · Buscar y Tipo acotan esta lista. ${D.modo==='grupos'?'Adultos por mesa; medianas de registros originales, no promedios de medianas.':D.modo==='mesas'?'Usos de cada mesa; consumo del pedido por hora ocupada.':'Tocá una fila para investigar el pedido.'}</p></div></div></section>`+ficha(G);
    root.innerHTML=html;
    const fb=document.querySelector('.st-key-vt_ctl_nativa_fecha');root.style.setProperty('--ctl-fecha',`${fb?.offsetWidth?fb.offsetWidth+24:0}px`);
    scroll.forEach(([id,top,left])=>{const el=root.querySelector(`[data-tabla="${id}"]`);if(el){el.scrollTop=top;el.scrollLeft=left;}});
    if(foco){const e=root.querySelector(`[data-input="${foco[0]}"]`);if(e){e.focus({preventScroll:true});e.setSelectionRange(foco[1],foco[2]);}}
  }
  function ficha(G){const D=G.D,p=D.pedido,b=D.tiempo,s=G.s;
    let h=`<section class="ctl-card ctl-ficha"><div class="ctl-ficha-cab"><h3>Pedido ${esc(D.elegido||'—')}</h3><span>${p?`Mesa ${esc(p.mesa||'sin dato')} · ${esc(p.mesero||'Sin mesero')} · ${esc(p.estado)}`:'Elegí una fila del detalle'}</span><button data-a="excelFicha">Excel del pedido ↓</button></div>`;
    if(s.origen||s.destino)h+=`<div class="ctl-enlaces"><span>Transferencia elegida</span>${s.origen?`<button data-a="ped" data-v="${esc(s.origen)}">Origen ${esc(s.origen)}</button>`:''}${s.destino?`<button data-a="ped" data-v="${esc(s.destino)}">Destino ${esc(s.destino)}</button>`:''}</div>`;
    if(!p)h+=`<p class="ctl-aviso">${D.elegido?'El pedido no está entre los datos cargados de estas fechas y canales. Sus transacciones disponibles se conservan debajo.':'No hay un pedido seleccionado.'}</p>`;
    else{
      if(D.fueraFiltro)h+='<p class="ctl-aviso">Este pedido está fuera de los filtros actuales de mesa o mesero.</p>';
      h+=`<div class="ctl-datos"><span>Día: <b>${fecha(p.dia).slice(0,10)}</b></span><span>Canal: <b>${esc(p.canal||'Sin dato')}</b></span><span>Adultos: <b>${nfmt.format(p.adultos)}</b></span><span>Consumo: <b>${dinero(p.monto)}</b></span><span>Precuentas: <b>${nfmt.format(p.n_precuenta)}</b></span>${p.anulado?`<span>Anulado: <b>${dinero(p.monto_anulado)}</b> · ${esc(p.motivo)} · ${esc(p.obs_anul)}</span>`:''}</div>`
        +`<div class="ctl-timeline">${[['apertura','Apertura'],['primer','Primer plato'],['ultimo','Último plato'],['precuenta','Precuenta'],['comp','Comprobante'],...(p.anulado?[['f_anul','Anulación']]:[])].map(([k,n])=>`<div><span>${n}</span><b>${fecha(p[k])}</b></div>`).join('')}</div>`
        +`<div class="ctl-tramos">${[['espera','Primer plato'],['comida','Comida'],['sobremesa','Sobremesa'],['cobro','Cobro'],['total','Total']].map(([k,n])=>`<span>${n}<b>${mins(b?.[k])}</b></span>`).join('')}</div><p class="ctl-nota">${b&&b.inicio!==p.apertura?'Pedido reabierto: el tiempo comienza en el primer plato (más de 120 minutos después de abrir). ':''}${!b?'Sin duración total válida de mesa cobrada. ':''}Un tramo sin fecha o con duración negativa queda sin dato. Consumo del pedido; no es venta neta ni importe cobrado.</p>`;
    }
    h+=`<div class="ctl-titulo-zona"><b>Transacciones relacionadas</b><span>Como origen o destino, dentro de las fechas y canales cargados</span></div>`+tabla(G,'relacionadas',COLTRX,D.relacionados,'relacionada')+'</section>';return h;
  }
  function exportar(G,fichaSolo=false){const {D,P,s}=G;
    const hoja=(nombre,cols,filas)=>({nombre,cabeza:cols.map(c=>c.n),decimales:6,filas:filas.map(r=>cols.map(c=>c.t==='f'?r[c.k]==null?'':fecha(r[c.k]):r[c.k]??''))});
    const contexto=[['Vista','Control de pedidos'],['Desde (incluido)',P.rango[0]],['Hasta (incluido)',P.rango[1]],['Fecha',P.turno?'Día del turno':'Fecha de apertura / transacción'],['Canales',P.canales.join(', ')||'Todos'],['Mesa',s.mesa||'Todas'],['Mesero',s.mesero||'Todos'],['Apartado',s.sub],['Agrupación',s.gran],['Detalle',ambito(G)],['Lista',D.modo],['Grupo elegido',s.grupoLista||'Todos'],['Mesa del detalle',s.mesaLista||'Todas'],['Búsqueda',s.q],['Tipo / motivo',D.tipo||'Todos'],['Foto de ocupación',D.foto?`${new Date(D.foto.dia*DAY).toISOString().slice(0,10)} ${P.slots[D.foto.slot]}`:'Sin selección'],['Desde P90',s.sub==='Tiempos'&&s.lentos?'Sí, incluye empates':'No'],['Pedido de la ficha',D.elegido||''],['Fuentes',`Pedidos: ${P.fuentes.pedidos?'disponible':'sin registros disponibles'}; transacciones: ${P.fuentes.transacciones?'disponible':'sin registros disponibles'}`],['Importes','Consumo y valor de líneas del pedido. No es venta neta ni pérdida confirmada.'],['Ocupación','Reconstruida con pedidos cobrados, fechas completas y extremos incluidos; no aforo ni asientos.'],['Tiempos','Minutos numéricos; medianas sobre registros originales. P90 lineal sobre duraciones válidas.'],['Filas','Todas las filas, incluidas las aún no dibujadas. Valores sin redondear; formato de seis decimales.']];
    const hojas=[];
    if(!fichaSolo){
      if(s.sub==='Ocupación')hojas.push(hoja('Ocupación',[c('dia','Día'),...P.slots.map((n,j)=>c(`s${j}`,n))],(P.fuentes.pedidos?D.scopeDias:[]).map(d=>Object.fromEntries([['dia',new Date(d*DAY).toISOString().slice(0,10)],...D.z[P.dias.indexOf(d)].map((v,j)=>[`s${j}`,v])]))));
      else hojas.push(hoja('Resumen',[c('periodo','Período'),...COLPER[s.sub]],D.series));
      const t=G.tablas.detalle;hojas.push(hoja('Detalle',t.cols,t.filas));
    }
    if(D.pedido)hojas.push({nombre:'Pedido',cabeza:['Dato','Valor'],decimales:6,filas:P.cp.map(k=>[k,['dia','apertura','primer','ultimo','precuenta','comp','f_anul'].includes(k)?D.pedido[k]==null?'':fecha(D.pedido[k]):D.pedido[k]??''])});
    if(D.tiempo)hojas.push(hoja('Tiempos del pedido',COLPED,[D.tiempo]));
    hojas.push(hoja('Transacciones relacionadas',COLTRX,D.relacionados));
    hojas.push({nombre:'Contexto',cabeza:['Dato','Selección'],decimales:6,filas:contexto});return hojas;
  }
  function enlazar(G){const {root,s}=G,signal=G.abort.signal;
    const on=(e,fn)=>root.addEventListener(e,fn,{signal});
    on('click',e=>{const el=e.target.closest('[data-a]');if(!el)return;const{a,v,id}=el.dataset;
      if(a==='sub'){s.sub=v;s.foto=null;s.mesaLista=null;s.grupoLista=null;s.lista=v==='Tiempos'?'Grupos':'Mesas';}
      else if(a==='gran'){s.gran=v;s.foco=null;s.foto=null;s.mesaLista=null;s.grupoLista=null;}
      else if(a==='filtros'){s.mesa='';s.mesero='';s.foco=null;s.foto=null;s.mesaLista=null;s.grupoLista=null;}
      else if(a==='rango'){s.foco=null;s.foto=null;s.mesaLista=null;s.grupoLista=null;}
      else if(a==='periodo'){const r=G.tablas.periodos.filas.find(r=>r.clave===v);s.foco=s.foco===r.clave?null:r.clave;s.foto=null;s.ped=null;s.origen=null;s.destino=null;}
      else if(a==='foto'){s.foto={dia:Number(el.dataset.dia),slot:Number(el.dataset.slot)};s.lista='Pedidos';s.mesaLista=null;s.grupoLista=null;s.ped=null;s.origen=null;s.destino=null;}
      else if(a==='lista'){s.lista=v;s.mesaLista=null;s.grupoLista=null;s.foto=null;if(v!=='Pedidos')s.lentos=false;}
      else if(a==='detalle'){
        const r=G.tablas.detalle.filas.find(r=>r.id===v);if(!r)return;
        if(G.D.modo==='grupos'){s.lista='Pedidos';s.grupoLista=r.grupo;s.ped=null;s.origen=null;s.destino=null;}
        else if(G.D.modo==='mesas'){s.lista='Pedidos';s.mesaLista=r.mesa;s.ped=null;s.origen=null;s.destino=null;}
        else{s.ped=r.ped;s.origen=G.D.modo==='eventos'&&s.sub==='Transferencias'?r.ped:null;s.destino=s.origen?r.destino||null:null;}
      }
      else if(a==='relacionada'){const r=G.D.relacionados.find(r=>r.id===v);if(r){s.origen=r.tipo==='TRANSFERENCIA'?r.ped:null;s.destino=s.origen?r.destino||null:null;s.ped=r.ped;}}
      else if(a==='ped')s.ped=v;
      else if(a==='orden'){const o=s.orden[id];s.orden[id]={k:v,d:o?.k===v?-o.d:1};}
      else if(a==='excel'||a==='excelFicha'){bajar(`Control_${a==='excelFicha'?'pedido':'vista'}.xlsx`,libro(exportar(G,a==='excelFicha')));return;}
      dibujar(G);
    });
    on('input',e=>{if(e.target.dataset.input==='q'){s.q=e.target.value;dibujar(G);}});
    on('change',e=>{const k=e.target.dataset.select;if(k==='tipo')s.tipos[s.sub]=e.target.value;else if(k){s[k]=e.target.value;s.foco=null;s.foto=null;s.mesaLista=null;s.grupoLista=null;s.ped=null;s.origen=null;s.destino=null;}else if(e.target.hasAttribute('data-lentos')){s.lentos=e.target.checked;s.lista='Pedidos';s.ped=null;s.origen=null;s.destino=null;}else return;dibujar(G);});
    on('keydown',e=>{const tr=e.target.closest('tr[data-a]');if(tr&&(e.key==='Enter'||e.key===' ')){e.preventDefault();tr.click();}});
    root.addEventListener('toggle',e=>{if(e.target.classList?.contains('ctl-claves'))s.claves=e.target.open;},{signal,capture:true});
    root.addEventListener('scroll',e=>{const el=e.target;
      if(el.hasAttribute?.('data-heat')&&el.scrollTop+el.clientHeight>el.scrollHeight-180&&G.heat.limite<G.heat.dias.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',heatRows(G,G.heat.limite,G.heat.limite+45));G.heat.limite+=45;}
      const t=G.tablas[el.dataset?.tabla];if(t&&el.scrollTop+el.clientHeight>el.scrollHeight-180&&t.limite<t.filas.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',rows(G,el.dataset.tabla,t.limite,t.limite+150));t.limite+=150;}
    },{signal,capture:true});
  }
  function montar({data:P,parentElement}){const prev=window.__ventasControl;prev?.abort.abort();let root=parentElement.querySelector('.ctl');if(!root){root=document.createElement('div');root.className='ctl';parentElement.appendChild(root);}const s=prev?.s||inicial(P.inicial);if(prev?.P.sello!==P.sello){s.foco=null;s.foto=null;s.ped=null;s.origen=null;s.destino=null;s.mesaLista=null;s.grupoLista=null;}if(!GRANOS.includes(s.gran))s.gran='Día';if(!SUBS.includes(s.sub))s.sub='Anulaciones';const G={P,s,root,B:leer(P),cache:{},abort:new AbortController(),tablas:{}};window.__ventasControl=G;enlazar(G);dibujar(G);return()=>G.abort.abort();}
  return{montar,leer,inicial,calcular,resumen,ocupacion,porMesa,porGrupo,quantil,dibujar,exportar};
})();
window.__controlDatos=CONTROL;
export default function(component){return CONTROL.montar(component);}
