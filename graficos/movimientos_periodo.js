/* Movimientos por período. Calendario y marcas del servidor; interacción local (#722). */
const MOV = (() => {
  const DIA = 86400000, GRANOS = ['Día', 'Semana', 'Mes', 'Año'];
  const CAMPOS = ['doc', 'area', 'tipo', 'fam', 'prod', 'unid', 'causa', 'estado'];
  const PARTES = {'Por área': 'area', 'Por tipo': 'tipo', 'Por producto': 'prod', 'Por causa': 'causa'};
  const REP = 'Repetido en el día', FUERA = 'Fuera de lo habitual';
  const fmt = new Intl.NumberFormat('es-PE', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const entero = new Intl.NumberFormat('es-PE', {maximumFractionDigits: 0});
  const cantidad = new Intl.NumberFormat('es-PE', {maximumFractionDigits: 3});
  const precio = new Intl.NumberFormat('es-PE', {maximumFractionDigits: 4});
  const dinero = v => v == null ? '—' : `S/ ${fmt.format(v)}`;
  const pct = v => v == null ? 'Sin base' : `${v > 0 ? '+' : ''}${fmt.format(v)} %`;
  const porcentaje = v => v == null ? 'Sin base' : `${fmt.format(v)} %`;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normal = v => String(v ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const sumar = (rs, k = 'valor') => rs.reduce((a, r) => a + (r[k] || 0), 0);
  const unico = (rs, k) => new Set(rs.map(r => r[k])).size;
  const valido = r => (r.esMerma || !!r.prod) && r.estado !== 'ANULADO' && r.aporta !== false;
  const ordenTexto = (a, b) => a < b ? -1 : a > b ? 1 : 0;
  const fecha = ms => new Date(ms).toISOString().slice(0, 16).replace('T', ' ');
  const dia = ms => Math.floor(ms / DIA);
  const por = (rs, k) => {
    const m = new Map();
    for (const r of rs) { const v = typeof k === 'function' ? k(r) : r[k]; if (!m.has(v)) m.set(v, []); m.get(v).push(r); }
    return m;
  };
  function decodificar(P, historial = false) {
    const buscarCortes={};if(P.merma)for(const c of P.cortes){const doc=P.dic.doc[c[0]];buscarCortes[doc]=(buscarCortes[doc]||'')+' '+P.cortes_dic.fin[c[1]]+' '+P.cortes_dic.cod_fin[c[7]];}
    return (historial ? P.hist : P.filas).map(a => {
      const r = {fecha:a[0], cant:a[9], punit:a[10], valor:a[11], habitual:a[12] ?? null,
        veces:a[13] || 0, exceso:a[14] || 0, nuevo:!!a[15], repite:a[16] ?? null, marca:a[17] || ''};
      CAMPOS.forEach((k, i) => { r[k] = P.dic[k][a[i + 1]]; });
      r.aporta=P.suma_sin_procesar!==false||r.estado!=='GENERADO';
      if(P.relojes&&!historial){r.f={reg:a[18],pro:a[19],cie:a[20]};r.real=a[18]??r.fecha;r.proc=a[19];r.sub=P.relojes.subs[a[21]]||'';}
      if(P.merma){Object.assign(r,P.porciones[r.doc]);r.esMerma=true;r.buscarCortes=buscarCortes[r.doc]||'';}
      return r;
    });
  }
  function estado(inicial = {}) {
    return {gran:'Semana', area:[], tipo:[], fam:[], prod:[], partir:null, resaltados:{}, reloj:'cie', dia:null, ampl:false,
      modo:'Gráfico', q:'', marca:'Todas', foco:null, tramo:null, doc:null, completo:false,
      orden:null, menu:null, mq:'', estadoDoc:'Todas', porcFlag:'Todas', mermaFicha:false, ...inicial};
  }
  function filtros(rs, s, productos) {
    return rs.filter(r => ['area', 'tipo', 'fam'].every(k => !s[k]?.length || s[k].includes(r[k]))
      && (!s.prod?.length || productos.includes(r.prod)));
  }
  function opciones(rs, s, conTipo, produccion=false) {
    let restantes = produccion?rs.filter(r=>r.estado!=='ANULADO'):rs.filter(valido);
    const ops = {}, rank = (xs, k) => [...por(xs, k)].map(([n, g]) => [n, sumar(produccion?g.filter(valido):g)])
      .filter(([n]) => n).sort((a,b) => b[1]-a[1] || ordenTexto(a[0],b[0])).map(x => x[0]);
    for (const k of ['area', ...(conTipo ? ['tipo'] : []), 'fam', 'prod']) {
      let oferta = rank(restantes, k);
      if (k === 'prod') oferta = [5,10,20].filter(n => n < oferta.length).map(n => `Top ${n} por valor`).concat(oferta);
      const sel = (s[k] || []).filter(v => k !== 'prod' || !/^Top (5|10|20) por valor$/.test(v) || oferta.includes(v));
      ops[k] = [...oferta, ...sel.filter(v => !oferta.includes(v))];
      if (k === 'prod') {
        const prods = rank(restantes, k), elegidos = new Set();
        sel.forEach(v => /^Top (5|10|20) por valor$/.test(v) ? prods.slice(0, Number(v.split(' ')[1])).forEach(n => elegidos.add(n)) : elegidos.add(v));
        ops.productos = [...elegidos];ops.prodSel = sel;
      } else if (sel.length) restantes = restantes.filter(r => sel.includes(r[k]));
    }
    return ops;
  }
  function opsPartir(P, s) {
    if (!P.tipo) return ['Por área'];
    return ['Por área', ...(s.tipo.length !== 1 ? ['Por tipo'] : []), 'Por producto',
      ...(P.causa && s.tipo.length === 1 && s.tipo[0] === 'Bajas' ? ['Por causa'] : [])];
  }
  // ── Contar por (regla #772): la misma línea, con la fecha del reloj elegido ──
  const CLOCKS = {cie:'Cierre', reg:'Registro', pro:'Proceso'};
  const ROT_RELOJ = {cie:'al cierre', reg:'fecha de registro', pro:'fecha de proceso'};
  const msDe = t => Date.parse(String(t).replace(' ','T')+'Z');
  // «Cierre» sólo existe mes a mes: por día o por semana sería la fecha de registro.
  function relojDe(P, s) {
    if (!P.relojes) return null;
    const hay = P.relojes.disponibles;
    const r = hay.includes(s.reloj) ? s.reloj : hay[0];
    return r === 'cie' && !['Mes','Año'].includes(s.gran) ? (hay.includes('reg') ? 'reg' : hay[0]) : r;
  }
  const memoReloj = new WeakMap();
  function conReloj(base, P, c) {
    let m = memoReloj.get(base);if (!m) { m = {};memoReloj.set(base,m); }
    if (!m[c]) { const ini=msDe(P.rango[0]),fin=msDe(P.rango[1]);m[c] = base.filter(r => r.f[c] != null && r.f[c] >= ini && r.f[c] < fin).map(r => ({...r,fecha:r.f[c]})); }
    return m[c];
  }
  function documentos(rs, fem = false) {
    return [...por(rs, 'doc')].map(([doc, g]) => {
      const primero = g[0], lineas = g.filter(r => r.esMerma||r.prod).length;
      const anulado = primero.estado === 'ANULADO', generado = primero.estado === 'GENERADO';
      const suma=g.some(valido);
      return {doc, fecha:Math.min(...g.map(r => r.real ?? r.fecha)), proc:primero.proc ?? null, area:primero.area, tipo:primero.tipo, estadoCodigo:primero.estado,
        causa:primero.causa, estado:anulado ? fem ? 'Anulada' : 'Anulado' : generado ? 'Sin procesar' : !lineas ? 'Sin ítems' : '',
        lineas, valor:sumar(g), registrado:sumar(g), suma:!anulado && !!lineas && suma,
        rotulo:anulado ? fem ? 'Anulada' : 'Anulado' : generado&&!suma?'Sin procesar':!lineas ? 'Sin ítems' : '',
        rep:g.filter(r => r.repite != null).length,
        fuera:g.filter(r => r.veces > 0 || r.nuevo).length,
        ...(primero.esMerma?{prod:primero.prod,unid:primero.unid,cant:primero.cant,costo:primero.costo,
          mermaCant:primero.mermaCant,cortes:primero.cortes,pctFisico:primero.pctFisico,pctMonetario:primero.pctMonetario,
          costoDia:primero.costoDia,valorDia:primero.valorDia,costoHoy:primero.costoHoy,valorHoy:primero.valorHoy,
          precioDisponible:primero.precioDisponible,flags:primero.flags,observaciones:primero.flags.join(' · ')}:{}),
        busqueda:normal([doc, primero.area, primero.tipo, primero.causa, primero.buscarCortes||'',...g.map(r => r.prod)].join(' '))};
    }).sort((a,b) => b.valor-a.valor || ordenTexto(a.doc,b.doc));
  }
  function productos(rs) {
    return [...por(rs.filter(valido), r => JSON.stringify([r.prod, r.unid]))].map(([,g]) => ({
      prod:g[0].prod, unid:g[0].unid, cant:sumar(g, 'cant'), valor:sumar(g), medio:sumar(g,'cant')>0?sumar(g)/sumar(g,'cant'):null, docs:unico(g, 'doc'),
      lineas:g.length, areas:unico(g, 'area'), rep:g.filter(r => r.repite != null).length,
      fuera:g.filter(r => r.veces > 0 || r.nuevo).length,
      ...(g[0].esMerma?{costo:sumar(g,'costo'),mermaCant:sumar(g,'mermaCant'),cortes:sumar(g,'cortes'),
        pctFisico:g.every(r=>r.cant!=null&&r.mermaCant!=null)&&sumar(g,'cant')>0?sumar(g,'mermaCant')/sumar(g,'cant')*100:null,
        conFlags:g.filter(r=>r.flags.length).length}:{}),
    })).sort((a,b) => b.valor-a.valor || ordenTexto(a.prod,b.prod));
  }
  function firma(s) {
    return JSON.stringify([s.gran,s.area,s.tipo,s.fam,s.prod,s.partir,s.resaltados,s.reloj]);
  }
  function calcular(P, st, base = decodificar(P), hist = decodificar(P, true), cache = null) {
    const s = estado(st), plan = P.planes[s.gran] || P.planes.Semana;if(P.familia===false)s.fam=[];
    if(cache?.firma===firma(s))return detalle(P,s,cache.core,cache);
    if(P.relojes)base=conReloj(base,P,relojDe(P,s));
    const ops = opciones(base, s, P.tipo, P.produccion);s.prod = ops.prodSel;
    const bl = filtros(base, s, ops.productos), validas = bl.filter(valido);
    const grupos = por(validas, r => plan.mapa[dia(r.fecha)]);
    const claves = [...grupos.keys()].sort();
    const ambs = por(bl, r => plan.mapa[dia(r.fecha)]);
    const series = claves.map((k, i) => {
      const g = grupos.get(k), amb = ambs.get(k) || [], meta = plan.metas[k];
      const ant = i ? grupos.get(claves[i-1]) : null, antes = ant ? sumar(ant) : 0;
      const v = sumar(g), parcialAnt = i > 0 && plan.metas[claves[i-1]].parcial;
      let variacion = null, varEstado = 'primera';
      if (s.gran === 'Año') varEstado = 'anual';
      else if (meta.parcial) varEstado = 'parcial';
      else if (!i) varEstado = 'primera';
      else if (parcialAnt) varEstado = 'ant_parcial';
      else if (antes <= 0) varEstado = 'sin_base';
      else { varEstado = 'ok';variacion = (v-antes)/antes*100; }
      return {clave:k, ...meta, valor:v, docs:unico(g,'doc'), areas:unico(g,'area'), lineas:g.length,
        ...(P.merma?{costo:sumar(g,'costo'),cortes:sumar(g,'cortes')}:{}),
        cant:sumar(g,'cant'), anulados:unico(amb.filter(r => r.estado === 'ANULADO'),'doc'),
        sin_procesar:unico(amb.filter(r => r.estado === 'GENERADO'),'doc'),
        variacion, varEstado, anterior:i ? plan.metas[claves[i-1]].fila : '',
        rep_n:g.filter(r => r.repite != null).length, rep_v:sumar(g.filter(r => r.repite != null)),
        fuera_n:g.filter(r => r.veces > 0).length, fuera_v:sumar(g,'exceso'),
        nuevos_n:g.filter(r => r.nuevo).length, por_dia:unico(g,'doc') / new Set(g.map(r => dia(r.fecha))).size,
        poco:P.poco.some(m => k.startsWith(m.mes) || (meta.desde.slice(0,7) <= m.mes && meta.hasta.slice(0,7) >= m.mes)),
      };
    });
    const partirOps = opsPartir(P, s);
    const partir = partirOps.includes(s.partir) ? s.partir : !s.tipo.length && P.tipo ? 'Por tipo'
      : partirOps.includes('Por causa') ? 'Por causa' : P.tipo ? 'Por producto' : 'Por área';
    const dimension = PARTES[partir], n = partir === 'Por área' ? 3 : 4;
    const totales = [...por(validas, dimension)].map(([nombre, g]) => ({nombre, valor:sumar(g)}))
      .filter(r => r.valor > 0).sort((a,b) => b.valor-a.valor || ordenTexto(a.nombre,b.nombre));
    const nombres = totales.length <= n+1 ? totales.map(r => r.nombre) : totales.slice(0,n).map(r => r.nombre);
    const trazas = nombres.map(nombre => ({nombre, valores:claves.map(k => sumar(grupos.get(k).filter(r => r[dimension] === nombre)))}));
    if (nombres.length < totales.length) trazas.push({nombre:'Resto', valores:claves.map((k,i) => Math.max(0, sumar(grupos.get(k))-sumar(trazas.map(t => ({valor:t.valores[i]})))))});
    const resaltables = trazas.length > 1 ? nombres.slice() : [];
    if (P.marcas) {
      const rep = claves.map(k => sumar(grupos.get(k).filter(r => r.repite != null)));
      const fuera = claves.map(k => sumar(grupos.get(k).filter(r => r.veces > 0 || r.nuevo)));
      if (rep.some(v => v !== 0)) { trazas.push({nombre:REP, valores:rep, marca:true});resaltables.push(REP); }
      if (fuera.some(v => v !== 0)) { trazas.push({nombre:FUERA, valores:fuera, marca:true});resaltables.push(FUERA); }
    }
    const guardado = s.resaltados[partir];
    const resaltado = guardado === null ? null : resaltables.includes(guardado) ? guardado : P.relojes ? null : resaltables[0] || null;
    const comps = plan.comps.map(cp => {
      const h = filtros(hist, s, ops.productos).filter(r => valido(r) && r.fecha >= cp.ini && r.fecha < cp.fin);
      const g = por(h, r => cp.mapa[dia(r.fecha)]);
      return {n:cp.n, rot:cp.rot, valores:claves.map(k => sumar(g.get(k) || [])), total:sumar(h), docs:unico(h,'doc')};
    });
    const core={base,plan,ops,bl,validas,claves,series,partir,partirOps,trazas,resaltables,resaltado,comps};
    if(cache){cache.firma=firma({...s,prod:ops.prodSel,partir});cache.core=core;cache.ambito=null;}
    return detalle(P,s,core,cache);
  }
  function detalle(P,s,core,cache) {
    const {base,plan,ops,bl,validas,claves,series,partir,partirOps,trazas,resaltables,resaltado,comps}=core;
    let seleccion = claves;
    if (s.tramo) seleccion = claves.filter(k => k >= s.tramo[0] && k <= s.tramo[1]);
    else if (s.foco) seleccion = claves.includes(s.foco) ? [s.foco] : [];
    else if (s.dia != null) seleccion = claves.includes(plan.mapa[s.dia]) ? [plan.mapa[s.dia]] : [];
    const acotado = !!(s.tramo || s.foco || s.dia != null);
    const ambito=JSON.stringify([s.foco,s.tramo,s.dia]);
    let scope=cache?.ambito===ambito?cache.scope:null;
    if(!scope){
      const amb=s.dia!=null&&!s.foco&&!s.tramo ? bl.filter(r => dia(r.real ?? r.fecha)===s.dia) : acotado ? bl.filter(r => seleccion.includes(plan.mapa[dia(r.fecha)])) : bl;
      const vs=amb.filter(valido);
      scope={amb,ds:documentos(amb,P.fem),productos:productos(amb),total:sumar(vs),nDocs:unico(vs,'doc'),
        costo:sumar(vs,'costo'),conFlags:vs.filter(r=>r.flags?.length).length,sinCortes:vs.filter(r=>r.esMerma&&!r.cortes).length,
        rep:sumar(vs.filter(r=>r.repite!=null)),fuera:sumar(vs.filter(r=>r.veces>0||r.nuevo)),exceso:sumar(vs,'exceso')};
      if(cache){cache.ambito=ambito;cache.scope=scope;}
    }
    const {amb,ds}=scope, q = normal(s.q);
    const docs = ds.filter(r => (!q || r.busqueda.includes(q))&&(!P.merma||s.porcFlag==='Todas'||s.porcFlag==='Con observaciones'&&r.flags.length||r.flags.includes(s.porcFlag)) && (s.marca === 'Todas'
      || (s.marca === REP ? r.rep > 0 : r.fuera > 0))&&(!P.produccion||s.estadoDoc==='Todas'
      ||s.estadoDoc==='Que suman'&&r.suma||s.estadoDoc==='Sin procesar'&&r.estadoCodigo==='GENERADO'
      ||s.estadoDoc==='Anuladas'&&r.estadoCodigo==='ANULADO'||s.estadoDoc==='Sin ítems'&&!r.lineas&&!['GENERADO','ANULADO'].includes(r.estadoCodigo)));
    const elegido = docs.some(r => r.doc === s.doc) ? s.doc : docs.find(r => r.suma)?.doc ?? docs[0]?.doc ?? null;
    const lineas = P.merma?cortesDe(P,elegido,cache):(s.completo ? base : amb).filter(r => r.doc === elegido && r.prod).sort((a,b) => b.valor-a.valor);
    const indices = claves.map((k,i) => seleccion.includes(k) ? i : -1).filter(i => i >= 0);
    const compSel = comps.map(c => ({...c, valor:acotado ? indices.reduce((a,i) => a+c.valores[i],0) : c.total}));
    const registroVisible = !P.merma&&s.gran === 'Mes' && !s.area.length && !s.fam.length && !s.prod.length
      && (!s.tipo.length || (s.tipo.length === 1 && s.tipo[0] === 'Bajas'))
      && !Object.values(P.contexto).some(v => v.length);
    const units = [...new Set(validas.map(r => r.unid))];
    return {ops, partir, partirOps, resaltables, resaltado, bl, validas, series, claves, trazas, comps,
      seleccion, amb, docs, todosDocs:ds, elegido, lineas, productos:scope.productos, compSel,
      total:scope.total, nDocs:scope.nDocs, rep:scope.rep,fuera:scope.fuera,
      costo:scope.costo,conFlags:scope.conFlags,sinCortes:scope.sinCortes,porcion: P.merma?base.find(r=>r.doc===elegido)||null:null,
      exceso:scope.exceso, unidades:units,
      registro:registroVisible ? Object.fromEntries(series.filter(r => !r.parcial && P.registro[r.clave]).map(r => [r.clave,P.registro[r.clave]])) : {},
      pendientes:ds.filter(r=>r.estadoCodigo==='GENERADO'),anuladas:ds.filter(r=>r.estadoCodigo==='ANULADO'),
      vacias:ds.filter(r=>!r.lineas&&!['GENERADO','ANULADO'].includes(r.estadoCodigo)),
      noSuman:ds.filter(r => !r.suma).length, acotado};
  }
  function cortesDe(P,doc,cache){let mapa=cache?.cortes;
    if(!mapa){mapa=new Map();for(const c of P.cortes){const d=P.dic.doc[c[0]],r={doc:d,fin:P.cortes_dic.fin[c[1]],unid:P.cortes_dic.unid[c[2]],cant:c[3],pprom:c[4],peso:c[5],valor:c[6],cod:P.cortes_dic.cod_fin[c[7]],unidOrigen:P.dic.unid[c[8]]};if(!mapa.has(d))mapa.set(d,[]);mapa.get(d).push(r);}if(cache)cache.cortes=mapa;}
    return(mapa.get(doc)||[]).slice().sort((a,b)=>b.valor-a.valor||ordenTexto(a.fin,b.fin));
  }

  function columna(k, nombre, tipo = '') { return {k, nombre, tipo}; }
  function tablasMerma(G){const {P,D,s}=G,c=columna;
    const resumen=[c('fila','Período'),c('docs','Porcionamientos','n'),c('cortes','Cortes','n'),c('areas','Áreas','n'),c('costo','Lo porcionado','dinero'),c('valor','Merma S/','dinero'),c('pm','Merma / valor porcionado','porcentaje'),c('parte','Parte de merma total','porcentaje'),c('variacion','Variación','pct')];
    const filas=D.series.filter(r=>D.seleccion.includes(r.clave)).map(r=>({...r,pm:r.costo?r.valor/r.costo*100:null,parte:D.total?r.valor/D.total*100:null}));
    const docs=[c('fecha','Fecha','fecha'),c('doc','Código'),c('prod','Producto inicial'),c('area','Área'),c('tipo','Usuario'),c('cant','Cantidad inicial','cant'),c('unid','Unidad'),c('pctFisico','Merma física','porcentaje'),c('valor','Merma S/','dinero'),c('cortes','Cortes','n'),c('observaciones','Observaciones')];
    const lineas=[c('fin','Producto final'),c('cant','Cantidad final','cant'),c('unid','Unidad final'),c('peso','Peso asignado','cant'),c('unidOrigen','Unidad de origen'),c('pprom','Precio unit. del día','precio'),c('valor','Valor al costo del día','dinero'),c('cod','Código final')];
    const prods=[c('prod','Producto inicial'),c('unid','Unidad'),c('cant','Cantidad inicial','cant'),c('mermaCant','Merma física','cant'),c('pctFisico','Merma / cantidad inicial','porcentaje'),c('costo','Lo porcionado','dinero'),c('valor','Merma S/','dinero'),c('docs','Porcionamientos','n'),c('cortes','Cortes','n'),c('conFlags','Con observaciones','n')];
    return{resumen:{cols:resumen,filas,tipo:'periodo'},docs:{cols:docs,filas:D.docs,tipo:'doc'},lineas:{cols:lineas,filas:D.lineas},productos:{cols:prods,filas:D.productos},comp:{cols:[],filas:[]},modo:s.modo};
  }
  function fichaMerma(G){const r=G.D.porcion;if(!r)return'<p class="mv-pie">Elegí un porcionamiento para ver sus cortes.</p>';
    const fis=v=>v==null?'Sin base':`${cantidad.format(v)} ${esc(r.unid||'(sin unidad)')}`,util=r.cant>0&&r.mermaCant!=null?r.cant-r.mermaCant:null,rend=r.cant>0&&util!=null?util/r.cant*100:null;
    return`<details class="mv-ficha-porc" ${G.s.mermaFicha?'open':''}><summary>${esc(r.prod||'Sin producto de origen')}: ${fis(r.cant)} → ${fis(util)} útiles · rendimiento ${porcentaje(rend)} · Ver costos ▾</summary><div class="mv-ficha-cuerpo"><b>Un porcionamiento, dos valorizaciones</b><p>Merma física: ${fis(r.mermaCant)} · ${porcentaje(r.pctFisico)}. La cantidad útil es entrada menos merma.</p><div><span>Costo del día</span><b>${dinero(r.valorDia)} de merma</b><span>${dinero(r.costoDia)} porcionados</span></div><div><span>Precio de hoy</span><b>${r.precioDisponible?dinero(r.valorHoy)+' de merma':'Sin precio actual'}</b><span>${r.precioDisponible?dinero(r.costoHoy)+' porcionados':'No se conoce la comparación'}</span></div><p>${r.precioDisponible?'Diferencia hoy − día: '+dinero(r.valorHoy-r.valorDia)+'. Cambia la base de valorización; no es una merma nueva.':'El Reporte de Mermas asigna cero al código sin precio; no permite concluir que no haya merma física.'}</p><p>Los cortes conservan el costo del día, incluida la asignación de merma. Peso asignado en la unidad del producto inicial; cantidad final en la de cada corte.</p>${r.flags.length?`<p class="mv-aviso">${esc(r.flags.join(' · '))}</p>`:''}</div></details>`;
  }
  function tablas(G) {
    const {P, D, s} = G;
    if(P.merma)return tablasMerma(G);
    let resumen = [columna('fila','Período'), columna('valor','Valorizado','dinero'), columna('docs',P.lado,'n'),
      columna('areas','Áreas','n'), columna('lineas','Líneas','n'), columna('variacion','Variación','pct'),
      columna('estado','Estado')];
    if (D.unidades.length === 1 && D.unidades[0]) resumen.splice(5,0,columna('cant',`Cantidad (${D.unidades[0]})`,'cant'));
    if (P.marcas) resumen = resumen.concat([columna('por_dia','Req./día','cant'), columna('rep_n','Lín. repetidas','n'),
      columna('rep_v','Valor repetido','dinero'), columna('fuera_n','Lín. sobre habitual','n'),
      columna('fuera_v','Exceso','dinero'), columna('nuevos_n','Lín. nuevas','n')]);
    if (Object.keys(D.registro).length) resumen.push(columna('registro','Bajas / faltante'));
    const R = G.R, conRelojes = !!R && s.gran === 'Mes';
    if (conRelojes) {
      const fijas = [columna('fila','Período'), ...P.relojes.disponibles.map(c => columna(`t_${c}`,({cie:'Al cierre',reg:'Registro',pro:'Proceso'})[c],'dinero')),
        ...(R.cie ? [columna('dif','Cierre − registro','dinero')] : []), columna('docs',nombreDetalle(P),'n'), columna('diasNota','Días con registro','n'),
        ...(G.ap ? [columna('ap','Un año antes','dinero')] : [])];
      resumen = fijas.concat(resumen.filter(c => !['fila','valor','docs'].includes(c.k)));
    }
    const filas = D.series.filter(r => D.seleccion.includes(r.clave)).map(r => ({...r,
      ...(conRelojes ? {t_cie:R.cie?.[r.clave] ?? 0, t_reg:R.reg?.[r.clave] ?? 0, t_pro:R.pro?.[r.clave] ?? 0, dif:(R.cie?.[r.clave] ?? 0)-(R.reg?.[r.clave] ?? 0),
        diasNota:R.dias[r.clave] ?? 0, ap:G.ap?.[D.claves.indexOf(r.clave)] ?? null} : {}),
      estado:[r.parcial ? 'Período parcial' : '',r.anulados ? `${r.anulados} anulado(s)` : '',
        r.sin_procesar ? `${r.sin_procesar} sin procesar` : '',r.poco ? 'Poco registro' : ''].filter(Boolean).join(' · '),
      registro:D.registro[r.clave] ? `${fmt.format(D.registro[r.clave][1])} %` : '—'}));
    const docs = [columna('fecha',P.relojes?'Registrada':'Fecha','fecha'), ...(P.relojes?[columna('proc','Procesada','fecha')]:[]), columna('doc','Código'), columna('area','Área'),
      ...(P.tipo ? [columna('tipo',P.rotulo_tipo||'Tipo'),...(P.causa?[columna('causa','Causa')]:[])] : []), columna('lineas','Líneas','n'),
      columna('valor',P.produccion?'Producido':'Valorizado','docValor'),...(P.produccion?[columna('registrado','Valor registrado','dinero')]:[]), columna('estado','Estado'),
      ...(P.marcas ? [columna('rep','Repetidas','n'),columna('fuera','Fuera de habitual','n')] : [])];
    const lineas = [columna('prod','Producto'), columna('unid','Unidad'), columna('cant','Cantidad','cant'),
      columna('punit','Precio unit.','precio'), columna('valor','Valorizado','dinero'),columna('area','Área'),
      columna('fam','Familia'), ...(P.marcas ? [columna('marca','Marca')] : [])];
    const prods = [columna('prod','Producto'),columna('unid','Unidad'),columna('cant','Cantidad','cant'),
      columna('valor','Valorizado','dinero'),...(P.produccion?[columna('medio','Valor / cantidad','precio')]:[]),columna('docs','Documentos','n'),columna('areas','Áreas','n'),columna('lineas','Líneas','n')];
    const comparacion = [columna('fila','Período'),columna('valor','Actual','dinero')];
    D.comps.forEach(c => { comparacion.push(columna(`a${c.n}`,c.rot,'dinero'),columna(`v${c.n}`,`Variación vs ${c.rot}`,'pct')); });
    const compFilas = filas.map(r => {
      const out = {...r}, i = D.claves.indexOf(r.clave);
      D.comps.forEach(c => { out[`a${c.n}`] = c.valores[i];out[`v${c.n}`] = c.valores[i] > 0 ? (r.valor-c.valores[i])/c.valores[i]*100 : null; });
      return out;
    });
    return {resumen:{cols:resumen, filas, tipo:'periodo'}, docs:{cols:docs,filas:D.docs,tipo:'doc'},
      lineas:{cols:lineas,filas:D.lineas}, productos:{cols:prods,filas:D.productos}, comp:{cols:comparacion,filas:compFilas}, modo:s.modo};
  }
  function celda(v, c, r) {
    if (c.k === 'unid' && !v) return 'Sin unidad';
    if (c.tipo === 'docValor') return r.rotulo || dinero(v);
    if (c.tipo === 'dinero') return dinero(v);
    if (c.tipo === 'fecha') return v == null ? '—' : fecha(v);
    if (c.tipo === 'pct') return pct(v);
    if (c.tipo === 'porcentaje') return porcentaje(v);
    if (c.tipo === 'cant') return v == null ? '—' : cantidad.format(v);
    if (c.tipo === 'precio') return v == null ? '—' : precio.format(v);
    if (c.tipo === 'n') return entero.format(v || 0);
    return v ?? '';
  }
  function tabla(G, t, id) {
    const ord = G.s.orden;
    let fs = t.filas.slice();
    if (ord?.id === id) fs.sort((a,b) => {
      const av=a[ord.k], bv=b[ord.k];return (typeof av === 'number' && typeof bv === 'number' ? av-bv : ordenTexto(String(av ?? ''),String(bv ?? ''))) * ord.d;
    });
    G.tablas[id] = {...t, filas:fs, cuantos:150};
    return `<div class="mv-scroll" data-tabla="${id}" tabindex="0"><table><thead><tr>${t.cols.map(c => `<th><button data-a="orden" data-id="${id}" data-v="${c.k}">${esc(c.nombre)}${ord?.id === id && ord.k === c.k ? ord.d === 1 ? ' ↑' : ' ↓' : ''}</button></th>`).join('')}</tr></thead><tbody>${renglones(G.tablas[id],0,150,G)}</tbody></table>${fs.length ? '' : '<p class="mv-vacio">No hay filas con esta selección.</p>'}</div>`;
  }
  function renglones(t, a, b, G) {
    return t.filas.slice(a,b).map(r => `<tr ${t.tipo === 'doc' ? `data-a="doc" data-v="${esc(r.doc)}" tabindex="0" class="${r.doc === G.D.elegido ? 'elegido' : ''}"` : t.tipo === 'periodo' ? `data-a="periodo" data-v="${esc(r.clave)}" tabindex="0"` : ''}>${t.cols.map(c => `<td class="${c.tipo ? 'num' : ''}" title="${esc(c.k === 'variacion' ? notaVar(r) : celda(r[c.k],c,r))}">${esc(celda(r[c.k],c,r))}</td>`).join('')}</tr>`).join('');
  }
  function notaVar(r) {
    if (r.varEstado === 'ok') return `${pct(r.variacion)} frente a ${r.anterior}`;
    return ({parcial:'El rango corta este período: no se calcula variación.', ant_parcial:'El período anterior está cortado por el rango.',
      sin_base:'El período anterior no tiene un valor positivo para comparar.',primera:'Primera barra del rango.',anual:'Sin variación entre barras anuales.'})[r.varEstado] || '';
  }
  function segmento(valores, actual, accion, etiquetas={}) {
    return `<div class="mv-seg">${valores.map(v => `<button data-a="${accion}" data-v="${esc(v)}" aria-pressed="${v === actual}" class="${v === actual ? 'on' : ''}">${esc(etiquetas[v]||v)}</button>`).join('')}</div>`;
  }
  function ambito(G) {
    if (!G.D.acotado) return 'Todo el rango';
    const filas = G.D.series.filter(r => G.D.seleccion.includes(r.clave));
    return filas.length ? filas.length === 1 ? filas[0].fila : `${filas[0].fila} → ${filas.at(-1).fila}` : 'Tramo sin registros';
  }
  function menu(G) {
    const k = G.s.menu;
    if (!k) return '';
    const q = normal(G.s.mq), ops = G.D.ops[k].filter(v => !q || normal(v).includes(q));
    return `<div class="mv-menu" data-menu="${k}" role="dialog" aria-label="Elegir ${k}"><input data-input="mq" aria-label="Buscar opciones" placeholder="Buscar…" value="${esc(G.s.mq)}"><button data-a="limpiar" data-v="${k}">Quitar selección</button><div class="mv-opciones">${ops.map(v => `<label><input type="checkbox" data-filtro="${k}" value="${esc(v)}" ${G.s[k].includes(v) ? 'checked' : ''}><span>${esc(v)}</span></label>`).join('') || '<p>Sin opciones.</p>'}</div><button data-a="cerrar">Listo</button></div>`;
  }
  // ── Lo que cuentan los relojes, por mes, con los filtros de la tarjeta ──
  function relojes(G) {
    const {P,s,D}=G;if(!P.relojes)return null;
    const clave=JSON.stringify([s.area,s.tipo,s.fam,D.ops.productos]);
    if(G.cache.relClave===clave)return G.cache.rel;
    const plan=P.planes.Mes,out={dias:{},docs:{},top:{}},f=rs=>filtros(rs,s,D.ops.productos).filter(valido);
    for(const c of P.relojes.disponibles){const m={};for(const r of f(conReloj(G.base,P,c))){const k=plan.mapa[dia(r.fecha)];m[k]=(m[k]||0)+r.valor;}out[c]=m;}
    if(P.relojes.disponibles.includes('reg')){
      for(const [k,g] of por(f(conReloj(G.base,P,'reg')),r=>plan.mapa[dia(r.fecha)])){
        const q=por(g,r=>dia(r.fecha)),vs=[...q.values()].map(x=>sumar(x)),t=sumar(g);
        out.dias[k]=q.size;out.docs[k]=unico(g,'doc');out.top[k]=t>0?Math.max(...vs)/t*100:0;
      }
    }
    G.cache.relClave=clave;G.cache.rel=out;return out;
  }
  // Lo de un año antes, para la barra gris: la comparación de Salidas o, sin
  // filtros, el total por mes de Requerimientos.
  function anioAntes(G) {
    const {P,D,s}=G;if(D.comps[0])return D.comps[0].valores;
    if(P.relojes&&s.gran==='Mes'&&!['area','tipo','fam','prod'].some(k=>s[k].length)&&Object.keys(P.relojes.ap).length)return D.claves.map(k=>P.relojes.ap[k]??0);
    return null;
  }
  // ¿Se está registrando menos? Los últimos tres meses completos contra los de antes.
  function caida(G) {
    const {P,R}=G;if(!R||!P.tipo)return null;
    const ks=Object.keys(P.planes.Mes.metas).filter(k=>!P.planes.Mes.metas[k].parcial&&R.docs[k]!=null).sort();
    if(ks.length<6)return null;
    const prom=(xs,m)=>xs.reduce((a,k)=>a+(m[k]||0),0)/xs.length,a=ks.slice(0,-3),b=ks.slice(-3);
    const d0=prom(a,R.docs),d1=prom(b,R.docs);if(d1>=d0*.6)return null;
    return {d0,d1,v0:prom(a,R.reg||{}),v1:prom(b,R.reg||{}),n0:prom(a,R.dias),n1:prom(b,R.dias)};
  }
  const k4 = v => Math.abs(v)>=1e6?`${(v/1e6).toFixed(2)}M`:Math.abs(v)>=1e4?`${Math.round(v/1e3)}k`:Math.abs(v)>=1e3?`${(v/1e3).toFixed(1)}k`:entero.format(v);
  const sol0 = v => v==null?'—':`${v<0?'−':''}S/ ${entero.format(Math.abs(v))}`;
  const MENOR = new Set(['de','del','y','en','la','el','a','x']);
  const nomb = t => /[a-záéíóúñ]/.test(t)?t:String(t).toLocaleLowerCase('es').split(/(\s+)/).map((w,i)=>i&&MENOR.has(w)?w:w.charAt(0).toLocaleUpperCase('es')+w.slice(1)).join('');
  const variacionTxt = (a,b) => b>0?`${a>=b?'+':'−'}${Math.abs(Math.round((a/b-1)*100))} %`:'—';
  function nombreDetalle(P){return P.merma?'Porcionamientos':P.produccion?'Órdenes':P.tipo?'Notas':'Requerimientos';}
  function htmlKpis(G) {
    const {P,D,s}=G;
    const kpi = (titulo, valor, nota, accion='', v='', title='', clase='') => `<${accion ? 'button' : 'div'} class="mv-kpi ${clase} ${accion && ((accion==='resaltar'&&D.resaltado === v)||(accion==='sinresaltar'&&!D.resaltado)||(accion==='modo'&&s.modo===v)) ? 'on' : ''}" ${accion ? `data-a="${accion}" data-v="${esc(v)}"` : ''} title="${esc(title || nota)}"><span>${esc(titulo)}</span><b>${esc(valor)}</b><small>${esc(nota)}</small></${accion ? 'button' : 'div'}>`;
    const highlights = D.resaltables.filter(x => x !== REP && x !== FUERA);
    const parte = nombre => { const t=D.trazas.find(t => t.nombre === nombre);return t.valores.reduce((a,v,i) => a+(D.seleccion.includes(D.claves[i]) ? v : 0),0); };
    const ap=G.ap, apSel=ap?D.claves.reduce((a,k,i)=>a+(D.seleccion.includes(k)?ap[i]:0),0):null, vsAp=apSel?`${variacionTxt(D.total,apSel)} contra un año antes`:'';
    if (P.relojes&&P.tipo) {
      const R=G.R,ks=D.seleccion.filter(k=>R.dias[k]!=null),c=caida(G),notasTip='Cuántos documentos se digitaron: una caída puede ser que no se registró, no menos merma.';
      const dias=s.gran==='Mes'&&s.foco&&!s.tramo?R.dias[s.foco]:null,mes=dias!=null?P.planes.Mes.metas[s.foco]:null;
      const subNotas=dias!=null?`${dias} días con nota de ${new Date(msDe(mes.hasta)).getUTCDate()}`:c?`de ~${Math.round(c.d0)} al mes a ${Math.round(c.d1)} los últimos tres`:`${ks.reduce((a,k)=>a+R.dias[k],0)} días con nota`;
      return kpi(D.acotado?'Salidas del tramo':'Salidas',sol0(D.total),[vsAp,D.noSuman?`${D.noSuman} no suman`:''].filter(Boolean).join(' · '),'sinresaltar','','Comida de personal, bajas, despacho a Mayta, uso en el área: no todo es merma.')
        +highlights.slice(0,2).map(n=>kpi(n,sol0(parte(n)),D.total>0?`${Math.round(parte(n)/D.total*100)} % de las salidas`:'','resaltar',n)).join('')
        +kpi('Notas registradas',entero.format(D.nDocs),subNotas,'modo','Calendario',notasTip,c?'alerta':'');
    }
    if (P.relojes) {
      // Sólo los meses con cierre: lo pedido de esos meses contra lo vendido y lo comprado de esos meses.
      const refs=G.refs||null,mapa=P.planes.Mes.mapa,vs=D.amb.filter(valido),conRef=refs?vs.filter(r=>refs[mapa[dia(r.fecha)]]):[];
      const mK=[...new Set(conRef.map(r=>mapa[dia(r.fecha)]))],plato=mK.reduce((a,k)=>a+refs[k].plato,0),compras=mK.reduce((a,k)=>a+refs[k].compras,0);
      const pidio=sumar(conRef.filter(r=>r.area.trim().toUpperCase()==='COCINA')),pedido=sumar(conRef),dias=new Set(D.amb.map(r=>dia(r.fecha))).size,espera=refs?'—':'…';
      return kpi(D.acotado?'Pedido del tramo':'Pedido',sol0(D.total),[vsAp,'no es gasto'].filter(Boolean).join(' · '),'sinresaltar','','Lo que las áreas le piden al Almacén. No es lo que se gastó: lo mismo puede moverse dos veces (Producción pide el insumo, Cocina el producto).')
        +kpi('Cocina, por S/ 100 servidos',plato?`S/ ${Math.round(pidio/plato*100)}`:espera,'lo que pidió Cocina ÷ el costo de lo que salió a plato','','','Normaliza por lo vendido. Cálculo propio. Sólo los meses con cierre.')
        +kpi('Requerimientos',entero.format(D.nDocs),`${dias?Math.round(D.nDocs/dias):0} por día${D.noSuman?` · ${D.noSuman} no suman`:''}`)
        +kpi('Comprado, para comparar',compras?sol0(compras):espera,compras?`lo pedido es ${(pedido/compras).toFixed(1)} veces lo comprado`:'','','','Por qué «Pedido» no es gasto: Cocina y Producción piden la misma comida en distintos pasos.');
    }
    let kpis = kpi(D.acotado ? 'Valorizado del tramo' : P.titulo,dinero(D.total),`${entero.format(D.nDocs)} ${P.lado}${D.noSuman ? ` · ${D.noSuman} no suman` : ''}`);
    if(P.merma){kpis+=kpi('Lo porcionado',dinero(D.costo),D.costo?`${porcentaje(D.total/D.costo*100)} de merma en soles`:'Sin base para porcentaje');kpis+=kpi('Con observaciones',entero.format(D.conFlags),'Datos sin base o para revisar','porcFlag','Con observaciones');kpis+=kpi('Sin cortes',entero.format(D.sinCortes),'Cabeceras sin producto final','porcFlag','Sin cortes');}
    else if(P.produccion){kpis+=kpi('Sin procesar',entero.format(D.pendientes.length),`${dinero(sumar(D.pendientes))} registrados; no producidos`,'estadoDoc','Sin procesar');kpis+=kpi('Anuladas',entero.format(D.anuladas.length),'Fuera del producido','estadoDoc','Anuladas');kpis+=kpi('Sin ítems',entero.format(D.vacias.length),'Órdenes sin producto','estadoDoc','Sin ítems');}
    else if (P.marcas) {
      kpis += kpi(REP,dinero(D.rep),'Líneas ya pedidas en el día','resaltar',REP,'Puede coincidir con «Fuera de lo habitual». No se suman ambas marcas.');
      kpis += kpi(FUERA,dinero(D.fuera),`Exceso: ${dinero(D.exceso)}`,'resaltar',FUERA,'Valor de las líneas sobre lo habitual o nuevas. El exceso es sólo la diferencia sobre la referencia.');
    } else for (const nombre of highlights.slice(0,3)) kpis += kpi(nombre,dinero(parte(nombre)),D.total > 0 ? `${fmt.format(parte(nombre) / D.total * 100)} % del ámbito` : '', 'resaltar',nombre);
    return kpis;
  }
  // ── Al costado: lo que dice el ámbito elegido ───────────────────────────
  function htmlPanel(G) {
    const {P,D,s}=G,R=G.R,fila=(n,v,tip='',fw=false)=>`<div class="mv-pr${fw?' fuerte':''}" title="${esc(tip)}"><span>${esc(n)}</span><span>${esc(v)}</span></div>`;
    const partes=[...por(D.amb.filter(valido),PARTES[D.partir])].map(([n,g])=>[n,sumar(g)]).filter(([n,v])=>n&&v>.005).sort((a,b)=>b[1]-a[1]);
    let html=`<h4>${esc(ambito(G))}</h4>`;
    if(s.dia!=null&&D.amb.length){
      const lista=documentos(D.amb,P.fem).filter(r=>r.suma);
      html+=`<p>${lista.length} ${esc(nombreDetalle(P).toLowerCase())} por ${sol0(D.total)}, de lo que se digitó ese día.</p><div class="mv-ps">Ese día</div>`+lista.slice(0,7).map(r=>fila(`${fecha(r.fecha).slice(11)} · ${r.tipo||r.area}`,sol0(r.valor),r.doc)).join('');
      return html+`<button class="mv-ver" data-a="modo" data-v="Detalle">Ver ${esc(nombreDetalle(P).toLowerCase())} →</button>`;
    }
    if(P.relojes&&P.tipo){const top=partes[0];html+=`<p>Salieron ${sol0(D.total)}${top?`; lo que más pesa es ${esc(top[0].toLocaleLowerCase('es'))} (${Math.round(top[1]/(D.total||1)*100)} %)`:''}. No todo es merma.</p>`;}
    else if(P.relojes){const a=partes.slice(0,2).reduce((x,r)=>x+r[1],0);html+=`<p>Las áreas pidieron ${sol0(D.total)}. ${partes.length>1?`${esc(nomb(partes[0][0]))} y ${esc(nomb(partes[1][0]))} son el ${Math.round(a/(D.total||1)*100)} %, y `:''}piden la misma comida en distintos pasos: no es lo gastado.</p>`;}
    else html+=`<p>${sol0(D.total)} en ${entero.format(D.nDocs)} ${esc(P.lado)}.</p>`;
    const c=caida(G);
    if(c&&!D.acotado)html+=`<p class="mv-alerta">Se registra mucho menos: de ${Math.round(c.d0)} notas al mes a ${Math.round(c.d1)} en los últimos tres, y de ${sol0(c.v0)} a ${sol0(c.v1)}. Un mes con pocas notas no es un mes con poca merma.</p>`;
    else if(R&&s.foco&&s.gran==='Mes'&&P.tipo&&(R.dias[s.foco]||99)<15)html+=`<p class="mv-alerta">Se registró en ${R.dias[s.foco]} días, y el ${Math.round(R.top[s.foco])} % en uno solo. Un mes con pocas notas no es un mes con poca merma.</p>`;
    if(R){
      const suma=m=>{if(!m)return 0;const ks=s.gran==='Mes'&&D.acotado?D.seleccion:Object.keys(m);return ks.reduce((a,k)=>a+(m[k]||0),0);};
      if(s.gran==='Mes'||!D.acotado){
        const usa=relojDe(P,s);
        html+='<div class="mv-ps">Según cómo se cuente</div>'+P.relojes.disponibles.map(k=>fila(({cie:'Al cierre',reg:'Por registro',pro:'Por proceso'})[k],sol0(suma(R[k])),({cie:'Cada mes de apertura a apertura de conteo: lo digitado antes de abrir es del mes que cerró. Es lo que suma Sin plato.',reg:'Cuándo se digitó.',pro:'Cuándo movió el stock.'})[k],k===usa)).join('');
      }
    }
    html+=`<div class="mv-ps">${esc(D.partir==='Por tipo'&&(P.merma||P.produccion)?'Por usuario':D.partir)}</div>`+partes.slice(0,c?3:4).map(([n,v])=>fila(nomb(n),sol0(v))).join('');
    if(P.marcas){
      html+='<div class="mv-ps">Marcas</div>'+[[REP,D.rep,'Líneas ya pedidas en el día. Puede coincidir con la otra marca: no se suman.'],[FUERA,D.fuera,`Exceso: ${dinero(D.exceso)}. Valor de las líneas sobre lo habitual o nuevas.`]].map(([n,v,tip])=>`<button class="mv-pr" data-a="resaltar" data-v="${esc(n)}" title="${esc(tip)}"><span>${esc(n)}</span><span>${sol0(v)}</span></button>`).join('');
    }
    if(R&&P.tipo&&s.foco&&s.gran==='Mes'&&R.dias[s.foco]!=null)html+='<div class="mv-ps">Cómo se registró</div>'+fila('Notas',entero.format(R.docs[s.foco]))+fila('Días con nota',entero.format(R.dias[s.foco]))+fila('El día de más peso',`${Math.round(R.top[s.foco])} %`);
    else if(c&&P.tipo)html+='<div class="mv-ps">Cómo se registró</div>'+fila('Días con nota, antes',`${Math.round(c.n0)} al mes`)+fila('Días con nota, últimos 3',`${Math.round(c.n1)} al mes`);
    if(P.poco.length)html+=`<p class="mv-aviso" title="Meses completos con menos de la mitad de los documentos habituales; referencia: mediana de los doce meses anteriores con al menos seis meses de datos.">Poco registro en ${P.poco.map(m => `${esc(m.mes)} (${m.docs} documentos; referencia ${cantidad.format(m.referencia)})`).join(' · ')}.</p>`;
    if(D.acotado)html+=`<button class="mv-ver" data-a="modo" data-v="Detalle">Ver ${esc(nombreDetalle(P).toLowerCase())} →</button>`;
    return html;
  }
  // ── El calendario: cuándo se digitó, día por día ────────────────────────
  function htmlCalendario(G) {
    const {P,D,s}=G,rows=filtros(conReloj(G.base,P,P.relojes.disponibles.includes('reg')?'reg':P.relojes.disponibles[0]),s,D.ops.productos).filter(valido);
    const q=new Map();for(const [d,g] of por(rows,r=>dia(r.fecha)))q.set(d,{v:sumar(g),docs:unico(g,'doc')});
    const mx=Math.max(1,...[...q.values()].map(x=>x.v)),aper=new Set(P.relojes.aperturas),meses=[],nombre=P.tipo?'notas':'requerimientos';
    const i0=msDe(P.rango[0]),i1=msDe(P.rango[1]);
    let y=new Date(i0).getUTCFullYear(),m=new Date(i0).getUTCMonth();
    while(Date.UTC(y,m,1)<i1){meses.push([y,m]);m++;if(m>11){m=0;y++;}}
    const MES=['ene','feb','mar','abr','may','jun','jul','ago','set','oct','nov','dic'],R=G.R;
    const filas=meses.map(([yy,mm])=>{
      const clave=`${yy}-${String(mm+1).padStart(2,'0')}`,ult=new Date(Date.UTC(yy,mm+1,0)).getUTCDate();let c='';
      for(let n=1;n<=31;n++){
        if(n>ult){c+='<i class="mv-d nada"></i>';continue;}
        const ms=Date.UTC(yy,mm,n),d=dia(ms),x=q.get(d),abre=aper.has(`${yy}-${String(mm+1).padStart(2,'0')}-${String(n).padStart(2,'0')}`),on=s.dia===d;
        const fuera=ms<i0-DIA||ms>=i1,tit=`${n} ${MES[mm]} ${yy}: ${x?`${sol0(x.v)} · ${x.docs} ${nombre}`:`sin ${nombre}`}${abre?' · se abrió el conteo':''}`;
        c+=x?`<button class="mv-d${abre?' abre':''}${on?' on':''}" data-a="dia" data-v="${d}" title="${esc(tit)}" aria-label="${esc(tit)}" style="background:color-mix(in srgb,var(--accent) ${Math.round(14+Math.sqrt(x.v/mx)*86)}%,var(--bg-card))"></button>`
          :`<i class="mv-d vacio${abre?' abre':''}${fuera?' nada':''}" title="${esc(tit)}"></i>`;
      }
      const dias=R.dias[clave]??0,flojo=P.tipo&&dias<15&&!P.planes.Mes.metas[clave]?.parcial,top=R.top[clave]??0;
      return `<button class="mv-m ${s.foco===clave?'on':''}" data-a="calmes" data-v="${clave}">${MES[mm]} ${String(yy).slice(2)}</button>${c}<span class="mv-n">${entero.format(R.docs[clave]??0)}</span><span class="mv-n${flojo?' alerta':''}">${dias}</span><span class="mv-n${P.tipo&&top>=55?' alerta':''}">${Math.round(top)} %</span>`;
    }).join('');
    const nums=Array.from({length:31},(_,i)=>`<span>${i%2?'':i+1}</span>`).join('');
    return `<div class="mv-cal"><span></span>${nums}<span class="mv-n">${P.tipo?'Notas':'Req.'}</span><span class="mv-n">Días</span><span class="mv-n">Mayor</span>${filas}</div><p class="mv-pie"><i class="mv-ley"></i>Más soles digitados ese día <i class="mv-ley abre"></i>Se abrió el conteo · Siempre por fecha de registro: un día sin color, nadie digitó ${esc(nombre)}.</p>`;
  }
  function htmlCuadros(G) {
    const {P,D}=G,vs=D.amb.filter(valido),cuadro=(t,k)=>{
      const fs=[...por(vs,k)].map(([n,g])=>[n,sumar(g)]).filter(([n,v])=>n&&Math.abs(v)>.5).sort((a,b)=>b[1]-a[1]),tot=fs.reduce((a,r)=>a+r[1],0)||1,mx=fs[0]?.[1]||1;
      return `<section><h4><span>${esc(t)}</span><small>${sol0(tot)}</small></h4><div class="mv-lista">${fs.map(([n,v])=>`<div class="mv-lf" title="${esc(n)}"><i style="width:${Math.max(1,v/mx*100)}%"></i><span>${esc(nomb(n))}</span><span>${entero.format(v)}</span><small>${Math.round(v/tot*100)} %</small></div>`).join('')}</div></section>`;
    };
    const lista=P.tipo?[[P.rotulo_tipo||'Tipo','tipo'],['Área','area'],...(P.familia===false?[['Producto','prod']]:[['Familia','fam']])]:P.relojes?[['Área','area'],['Familia','fam'],['Subfamilia','sub']]:[['Área','area'],...(P.familia===false?[]:[['Familia','fam']]),['Producto','prod']];
    return `<div class="mv-cuadros">${lista.map(([t,k])=>cuadro(t,k)).join('')}</div>${P.relojes?'<p class="mv-pie">La cadena completa, con productos y qué se pidió contra qué salió, está en «Análisis por área», arriba.</p>':''}`;
  }
  function dibujar(G) {
    const {s,P,raiz} = G;
    G.D = calcular(P,s,G.base,G.hist,G.cache);const D=G.D;
    D.plan=P.planes[s.gran]||P.planes.Semana;
    s.prod = D.ops.prodSel;s.partir = D.partir;s.doc=D.elegido;
    if(s.modo==='Comparación'&&!D.comps.length)s.modo='Gráfico';
    if(s.modo==='Calendario'&&!P.relojes)s.modo='Gráfico';
    G.R=relojes(G);G.ap=anioAntes(G);
    G.T = tablas(G);G.tablas={};
    const enfocado = raiz.querySelector('input:focus');
    const foco = enfocado ? [enfocado.dataset.input,enfocado.selectionStart,enfocado.selectionEnd] : null;
    const scrolls = [...raiz.querySelectorAll('[data-tabla]')].map(e => [e.dataset.tabla,e.scrollTop,e.scrollLeft]);
    const filtrosHTML = [['area','Área'],...(P.tipo ? [['tipo',P.rotulo_tipo||'Tipo']] : []),...(P.familia===false?[]:[['fam','Familia']]),['prod','Producto']].map(([k,n]) =>
      `<button class="mv-filtro ${s[k].length ? 'activo' : ''}" data-a="menu" data-v="${k}" aria-expanded="${s.menu === k}" title="${esc(s[k].join(', ') || `Todas las opciones de ${n}`)}">${n}: <strong>${s[k].length ? esc(s[k].length === 1 ? s[k][0] : `${s[k].length} elegidos`) : 'todos'}</strong><span>▾</span></button>`).join('');
    const context = Object.entries(P.contexto).filter(([,v]) => v.length).map(([k,v]) => `${k}: ${v.join(', ')}`).join(' · ');
    const fechaRango = `${P.rango[0].slice(0,10)} al ${new Date(new Date(P.rango[1].replace(' ','T')).getTime()-DIA).toISOString().slice(0,10)}`;
    const quitar = ['area','tipo','fam','prod'].some(k => s[k].length) ? '<button data-a="todos" class="mv-quitar">Quitar filtros</button>' : '';
    const efectivo = relojDe(P,s);
    const reloj = P.relojes ? `<span class="mv-rot" title="Cómo se reparten los documentos entre los meses">Contar por</span><div class="mv-seg" role="group" aria-label="Contar por">${P.relojes.disponibles.map(c => { const apagado=c==='cie'&&!['Mes','Año'].includes(s.gran);return `<button data-a="reloj" data-v="${c}" aria-pressed="${c===efectivo}" class="${c===efectivo?'on':''}" ${apagado?'disabled':''} title="${esc(apagado?'El cierre sólo existe mes a mes':({cie:'Cada mes de apertura a apertura de conteo: es lo que suma Sin plato.',reg:'Cuándo se digitó.',pro:'Cuándo movió el stock.'})[c])}">${CLOCKS[c]}</button>`; }).join('')}</div>` : '';
    const tabs = [['Gráfico','Gráfico'],...(P.relojes?[['Calendario','Calendario']]:[]),['Resumen','Tabla'],['Por área','Por área'],['Productos','Productos'],['Detalle',nombreDetalle(P)],...(D.comps.length ? [['Comparación','Comparación']] : [])];
    const tabsHTML = `<div class="mv-tabs" role="tablist">${tabs.map(([v,t]) => `<button role="tab" data-a="modo" data-v="${esc(v)}" aria-selected="${s.modo===v}" class="${s.modo===v?'on':''}">${esc(t)}</button>`).join('')}</div>`;
    const comparaTxt = D.compSel.map(c => `<span title="${esc(c.docs)} documentos en el rango comparable completo">${esc(c.rot)}: ${dinero(c.valor)} · ${pct(c.valor > 0 ? (D.total-c.valor)/c.valor*100 : null)}</span>`).join('');
    let medio = '', zona = '', pie = '';
    if (s.modo === 'Gráfico') {
      medio = (P.tipo ? segmento(D.partirOps,D.partir,'partir',P.produccion||P.merma?{'Por tipo':'Por usuario'}:{}) : '') + `<span class="mv-leyenda"><i class="ley"></i>${esc(D.resaltado||(P.relojes?(P.tipo?'Salidas':'Pedido'):'Valorizado'))}${G.ap?'<i class="ley ap"></i>Un año antes (por registro)':''}</span>`;
      zona = `<div class="mv-grafico" aria-label="Valorizado por período"><svg role="img" aria-label="Barras por período"></svg><div class="mv-tip" hidden></div></div>`;
      pie = `<span>${D.series.length ? `Clic: lo cuenta el panel · Arrastrá: elegir tramo${s.gran==='Mes'&&P.relojes?' · Un mes en curso o cortado por la fecha va más claro':''}` : 'Sin movimientos que sumen. Ampliá la fecha o quitá un filtro.'}</span><span>${esc(context)}</span>`;
    } else if (s.modo === 'Calendario') zona = htmlCalendario(G);
    else if (s.modo === 'Por área') zona = htmlCuadros(G);
    else if (s.modo === 'Detalle') {
      medio = `<input data-input="q" type="search" class="mv-q" aria-label="Buscar documentos o productos" placeholder="${P.merma?'Buscar código, origen o corte…':'Buscar código, producto, área…'}" value="${esc(s.q)}">${P.marcas ? `<select data-select="marca" aria-label="Filtrar documentos por marca">${['Todas',REP,FUERA].map(v => `<option ${s.marca === v ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>` : ''}${P.produccion?`<select data-select="estadoDoc" aria-label="Estado de las órdenes">${['Todas','Que suman','Sin procesar','Anuladas','Sin ítems'].map(v=>`<option ${s.estadoDoc===v?'selected':''}>${esc(v)}</option>`).join('')}</select>`:''}${P.merma?`<label>Observaciones <select data-select="porcFlag" aria-label="Observaciones del porcionamiento">${['Todas','Con observaciones','Cantidad sin base','Merma sin dato','Merma fuera de rango','Sin cortes','Sin precio actual','Sin producto de origen'].map(v=>`<option ${s.porcFlag===v?'selected':''}>${esc(v)}</option>`).join('')}</select></label>`:''}<span class="mv-rot">${D.docs.length} documentos${s.marca !== 'Todas' ? ' · con líneas marcadas' : ''}</span>`;
      zona = `<div class="mv-documentos">${tabla(G,G.T.docs,'docs')}</div><div class="mv-doc-cab"><b>${esc(P.sing)} ${esc(D.elegido || '—')}</b>${P.merma?'':`<label><input type="checkbox" data-completo ${s.completo ? 'checked' : ''}> Documento completo</label>`}<span>${P.merma?'Cortes completos del elegido, al costo del día':s.completo ? 'Líneas disponibles con las fechas y filtros de la página' : 'Líneas dentro de los filtros y el tramo'}</span></div>`
        + (P.merma?fichaMerma(G):'')+`<div class="mv-lineas">${tabla(G,G.T.lineas,'lineas')}</div>`;
    } else if (s.modo === 'Productos') { zona = tabla(G,G.T.productos,'productos');pie = 'Cantidades separadas por producto y unidad; no se suman unidades distintas.'; }
    else if (s.modo === 'Comparación') { medio = `<span class="mv-leyenda">${comparaTxt}</span>`;zona = tabla(G,G.T.comp,'comp');pie = `Día y semana: 364 días por año, comparando el mismo día de la semana. Mes y año: calendario. «Sin base» indica una referencia sin valor positivo. Las fechas pueden cortar períodos.${D.acotado ? ' Totales de las barras del tramo elegido.' : ' El total histórico incluye todo el rango desplazado, incluso períodos sin barra actual.'}`; }
    else { zona = tabla(G,G.T.resumen,'resumen');pie = `${P.merma?'Merma / valor porcionado usa totales en soles, no la media de porcentajes físicos. ':''}${P.relojes&&s.gran==='Mes'?'«Al cierre» es lo que suma Sin plato. ':''}Variación frente a la barra anterior. Los períodos parciales no muestran porcentaje.${Object.keys(D.registro).length ? ' Bajas / faltante: bajas registradas del mes completo divididas por el faltante de su cierre.' : ''}${P.marcas ? ' Las marcas pueden coincidir: sus importes no se suman entre sí.' : ''}`; }
    if(P.merma)pie+=' Cada cabecera se cuenta una vez. La valorización es compartida con Rendimiento y Para revisar. Las familias de la página no recortan esta fuente.';
    if(P.produccion)pie+=' Lo generado, anulado o sin producto no entra en el valorizado producido. Las líneas describen la orden registrada; los pendientes no han producido todavía.';
    const foq = D.acotado ? `<button class="mv-chip" data-a="rango" title="Volver a todo el rango">${esc(ambito(G))} ✕</button>` : '';
    const ampliar = `<button class="mv-amp" data-a="ampl" aria-pressed="${!!s.ampl}" title="${s.ampl?'Volver a poner el panel al costado':'Esconder el panel y usar todo el ancho'}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${s.ampl?'M3 9h6V3M21 9h-6V3M3 15h6v6M21 15h-6v6':'M9 3H3v6M15 3h6v6M9 21H3v-6M15 21h6v-6'}"/></svg>${s.ampl?'Con panel':'Ampliar'}</button>`;
    const html = `<section class="mv-main"><div class="mv-fila mv-uno">${segmento(GRANOS,s.gran,'gran')}${reloj}<div class="mv-filtros">${filtrosHTML}${quitar}</div>${menu(G)}<span class="mv-esp"></span><span class="mv-rot mv-rango" title="${esc(P.rot_fecha||'')}">${P.relojes?'':esc(fechaRango)}${P.merma?' · '+(P.valoracion==='hoy'?'Precio de hoy':'Costo del día')+(P.valoracion_solicitada==='hoy'&&P.valoracion!=='hoy'?' (precio actual no disponible)':''):''}</span><button class="mv-excel" data-a="excel" title="Descargar los datos y el contexto de esta vista">Excel</button></div>`
      + `<div class="mv-kpis">${htmlKpis(G)}</div>`
      + `<div class="mv-fila mv-dos">${tabsHTML}${medio}<span class="mv-esp"></span>${foq}${ampliar}</div>`
      + `<div class="mv-cuerpo"><div class="mv-zona">${zona}${pie?`<div class="mv-notas">${pie.startsWith('<')?pie:`<span>${esc(pie)}</span>`}</div>`:''}</div>${s.ampl?'':`<aside class="mv-pn" aria-label="Lectura">${htmlPanel(G)}</aside>`}</div></section>`;
    raiz.innerHTML=html;
    const fb=document.querySelector(`.st-key-${P.k}_nativa_fecha`);
    raiz.style.setProperty('--mv-fecha',`${fb?.offsetWidth&&!P.relojes ? fb.offsetWidth+12 : 0}px`);
    if (foco) {
      const e=raiz.querySelector(`input[data-input="${foco[0]}"]`);
      if (e) { e.focus({preventScroll:true});if (e.type !== 'checkbox') e.setSelectionRange(foco[1],foco[2]); }
    }
    scrolls.forEach(([id,top,left]) => { const e=raiz.querySelector(`[data-tabla="${id}"]`);if(e){e.scrollTop=top;e.scrollLeft=left;} });
    G.ro?.disconnect();const caja=raiz.querySelector('.mv-grafico');if(caja){G.ro=new ResizeObserver(() => grafico(G));G.ro.observe(caja);grafico(G);}
    if(P.relojes?.pedir_refs&&!G.refs&&!G.refsPedidas&&G.enviar){G.refsPedidas=true;G.enviar('refs',1);}
  }
  function grafico(G) {
    const box=G.raiz.querySelector('.mv-grafico'), svg=box?.querySelector('svg');if(!svg)return;
    const W=box.clientWidth,H=box.clientHeight;if(W<80 || H<60)return;
    const rs=G.D.series, N=rs.length, L=8,R=8,T=22,B=G.s.gran==='Semana'?46:34, pw=W-L-R, ph=H-T-B;
    svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('width',W);svg.setAttribute('height',H);
    if(!N){svg.innerHTML='';return;}
    const highlight=G.D.trazas.find(t=>t.nombre===G.D.resaltado),ap=G.ap,conAp=!!ap&&pw/N>=10;
    const vals=[0,...rs.map(r=>r.valor),...G.D.comps.flatMap(c=>c.valores),...(highlight?.valores||[]),...(ap||[])];
    const max=Math.max(...vals,1)*1.04,min=Math.min(...vals,0)*1.04,span=max-min;
    const y=v=>T+(max-v)/span*ph,x=i=>L+(i+.5)*pw/N, bw=Math.max(1,pw/N*(conAp?.34:.68)),zero=y(0);
    G.chart={x,y,W,H,L,pw,N,rs};
    let html='';
    for(let i=0;i<4;i++){const yy=y(min+span*i/3);html+=`<line x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}" class="mv-grid"/>`;}
    const cada=Math.max(1,Math.ceil(N/(pw/(G.s.gran==='Semana'?140:G.s.gran==='Mes'?52:85))));
    const iMax=rs.reduce((m,r,i)=>r.valor>rs[m].valor?i:m,0),haySel=G.D.acotado;
    rs.forEach((r,i)=>{
      const xx=x(i), yy=y(r.valor), alto=Math.max(1,Math.abs(zero-yy)),select=G.D.seleccion.includes(r.clave),x0=conAp?xx+1:xx-bw/2;
      if(r.especial)html+=`<rect x="${xx-pw/N/2}" y="${T}" width="${pw/N}" height="${ph}" class="mv-feriado"><title>${esc(r.especial)}</title></rect>`;
      if(haySel&&select&&G.D.seleccion.length<N)html+=`<rect x="${xx-pw/N/2+1}" y="2" width="${pw/N-2}" height="${H-4}" rx="7" class="mv-marca"/>`;
      html+=`<g opacity="${select?1:.3}">`;
      if(conAp){const ay=y(ap[i]);html+=`<rect x="${xx-bw-1}" y="${Math.min(ay,zero)}" width="${bw}" height="${Math.max(1,Math.abs(zero-ay))}" rx="2" class="mv-bar-ap"/>`;}
      html+=`<rect x="${x0}" y="${Math.min(yy,zero)}" width="${bw}" height="${alto}" rx="2" class="mv-bar ${highlight?'suave':''} ${r.parcial?'parcial':''}"/>`;
      if(highlight){const v=highlight.valores[i],hy=y(v);html+=`<rect x="${x0}" y="${Math.min(hy,zero)}" width="${bw}" height="${Math.max(1,Math.abs(zero-hy))}" class="mv-bar"/>`;}
      if(!conAp)G.D.comps.forEach((c,j)=>{const cy=y(c.valores[i]);html+=`<line x1="${xx-bw*.8}" x2="${xx+bw*.8}" y1="${cy}" y2="${cy}" class="mv-comp c${j}"/>`;});
      if(i===iMax||i===N-1||(select&&G.D.seleccion.length===1&&haySel))html+=`<text x="${x0+bw/2}" y="${Math.max(13,yy-6)}" text-anchor="middle" class="mv-label">${esc(k4(r.valor))}</text>`;
      if(i%cada===0)html+=`<text x="${xx}" y="${H-B+17}" text-anchor="middle" class="mv-axis">${esc(r.eje)}</text>${G.s.gran==='Semana'?`<text x="${xx}" y="${H-9}" text-anchor="middle" class="mv-axis">${esc(r.clave.slice(0,4))}</text>`:''}`;
      html+=`</g><rect data-bar="${i}" x="${xx-pw/N/2}" y="${T-10}" width="${pw/N}" height="${ph+10}" fill="transparent" tabindex="0" role="button" aria-label="${esc(r.fila)}: ${esc(dinero(r.valor))}"><title>${esc(r.largo)} · ${esc(dinero(r.valor))} · ${r.docs} ${esc(G.P.lado)}</title></rect>`;
    });
    html+='<rect class="mv-brush" hidden/>';svg.innerHTML=html;
  }
  function tip(G,i) {
    const t=G.raiz.querySelector('.mv-tip');if(!t)return;
    if(i==null || !G.D.series[i]){t.hidden=true;return;}
    const r=G.D.series[i];
    t.innerHTML=`<b>${esc(r.largo)}</b><strong>${dinero(r.valor)}</strong><span>${r.docs} ${esc(G.P.lado)} · ${r.lineas} líneas · ${r.areas} áreas</span><span>${esc(notaVar(r))}</span>`
      +G.D.trazas.map(tr=>`<span>${esc(tr.nombre)}: ${dinero(tr.valores[i])}</span>`).join('')
      +G.D.comps.map(c=>`<span>${esc(c.rot)}: ${dinero(c.valores[i])} · ${pct(c.valores[i]>0?(r.valor-c.valores[i])/c.valores[i]*100:null)}</span>`).join('')
      +(G.P.marcas?`<small>Marcas superpuestas. Exceso: ${dinero(r.fuera_v)}.</small>`:'');
    t.hidden=false;t.style.left=`${Math.max(2,Math.min(G.chart.x(i)+12,G.chart.W-t.offsetWidth-4))}px`;
  }
  function exportar(G) {
    const {P,D,s,T}=G, indices=D.claves.map((k,i)=>D.seleccion.includes(k)?i:-1).filter(i=>i>=0);
    const hoja=(nombre,t)=>({nombre,cabeza:t.cols.map(c=>c.nombre),decimales:6,filas:t.filas.map(r=>t.cols.map(c=>{
      const v=r[c.k];return c.tipo==='fecha'?fecha(v):c.tipo==='docValor'&&r.rotulo?r.rotulo:v??'';
    }))});
    const contexto=[['Vista',P.lado],['Desde (incluido)',P.rango[0]],['Hasta (excluido)',P.rango[1]],
      ['Fecha usada',P.relojes?ROT_RELOJ[relojDe(P,s)]:P.rot_fecha],['Agrupación',s.gran],['Detalle elegido',ambito(G)],['Modo',s.modo],
      ...Object.entries(P.contexto).map(([k,v])=>[k,v.join(', ')||'Todas']),
      ...['area','tipo','fam','prod'].map(k=>[`Filtro ${k}`,s[k].join(', ')||'Todos']),
      ['Búsqueda en documentos',s.q],['Marca en documentos',s.marca],['Estado en documentos',s.estadoDoc],['Documento elegido',D.elegido||''],
      ['Líneas del documento',P.merma?'Cortes completos del elegido, siempre al costo del día':s.completo?'Completo con fechas y filtros de la página':'Dentro de los filtros y tramo'],
      ['Marcas','Pueden coincidir. No sumar sus importes entre sí.'],
      ['Comparación','Día y semana: 364 días por año; mes y año: calendario. Sin base si referencia <= 0.'],
      ['Decimales','Valores numéricos con seis decimales; totales calculados sin redondear.'],
      ...(P.produccion?[["Órdenes sin procesar",D.pendientes.length],["Importe registrado sin procesar (no producido)",sumar(D.pendientes)],["Regla de producción","Órdenes generadas, anuladas o sin producto quedan fuera del producido. Las cantidades se separan por producto y unidad."]]:[]),['Valorizado del ámbito',D.total],['Documentos válidos del ámbito',D.nDocs]];
    D.compSel.forEach(c=>contexto.push([`Total comparable ${c.rot}`,c.valor]));
    const docsVisibles=new Set(D.docs.map(r=>r.doc));
    const hojas=[hoja('Resumen',T.resumen),hoja('Documentos',T.docs),hoja('Productos',T.productos),
      hoja(P.merma?'Cortes del elegido':'Líneas del documento',T.lineas)];
    if(s.modo==='Detalle'){if(P.merma)hojas.push(hoja('Cortes de documentos visibles',{...T.lineas,cols:[columna('doc','Porcionamiento'),...T.lineas.cols],filas:[...docsVisibles].flatMap(doc=>cortesDe(P,doc,G.cache))}));else hojas.push(hoja('Líneas de documentos visibles',{...T.lineas,filas:D.amb.filter(r=>r.prod&&docsVisibles.has(r.doc))}));}
    if(D.comps.length)hojas.push(hoja('Comparación',T.comp));
    if(P.merma){
      const c=columna,cols=[c('doc','Porcionamiento'),c('prod','Producto inicial'),c('unid','Unidad de origen'),c('cant','Cantidad inicial'),c('mermaCant','Merma física'),c('costoDia','Costo del día'),c('valorDia','Merma al costo del día'),c('costoHoy','Costo a precio de hoy'),c('valorHoy','Merma a precio de hoy'),c('precioDisponible','Precio actual disponible'),c('delta','Diferencia conocida hoy - día'),c('observaciones','Observaciones')];
      hojas.push(hoja('Dos valorizaciones',{cols,filas:D.docs.map(r=>({...r,delta:r.precioDisponible?r.valorHoy-r.valorDia:null}))}));
      contexto.push(['Valorización efectiva',P.valoracion==='hoy'?'Precio de hoy':'Costo del día'],['Valorización solicitada',P.valoracion_solicitada==='hoy'?'Precio de hoy':'Costo del día'],['Valorización compartida','Con Rendimiento y Para revisar. El selector nativo actualiza todas esas vistas.'],['Familia','No aplica: la fuente de porcionamientos no trae esta dimensión.'],['Observaciones',s.porcFlag],['Lo porcionado en la base elegida',D.costo],['Merma / valor porcionado (%)',D.costo?D.total/D.costo*100:null],['Cabeceras','Cada porcionamiento se cuenta una vez; sus cortes no multiplican la cantidad ni la merma de la cabecera.'],['Costo del día','Suma de cantidad final por precio promedio de los cortes. Incluye la merma asignada a los cortes.'],['Precio de hoy','Cantidad/merma física por precio promedio actual del producto inicial. Un código sin precio vale cero como el Almacén; la diferencia no se calcula si falta ese precio.'],['Porcentajes','Merma monetaria usa totales en soles; merma física usa una cabecera o un producto/unidad. No se promedian porcentajes de porcionamientos.'],['Cortes','Siempre al costo del día. Cantidades en unidad final; pesos asignados en unidad del producto inicial.'],['Observaciones de datos','Cantidad no positiva o sin dato, merma ausente o fuera de 0-100 %, sin cortes, sin precio actual o sin producto de origen. No alteran los valores fuente.']);
    }
    hojas.push({nombre:'Contexto',cabeza:['Dato','Selección'],decimales:6,filas:contexto});
    return {hojas,indices};
  }
  function eventos(G) {
    const {raiz,s}=G, signal=G.abort.signal;
    const on=(evento,fn)=>raiz.addEventListener(evento,fn,{signal});
    on('click',e=>{
      const b=e.target.closest('[data-a]');if(!b)return;
      const {a,v,id}=b.dataset;
      if(a==='gran'){s.gran=v;s.foco=null;s.tramo=null;s.doc=null;s.dia=null;}
      else if(a==='modo'){s.modo=v;s.orden=null;}
      else if(a==='reloj'){s.reloj=v;s.tramo=null;s.doc=null;}
      else if(a==='ampl')s.ampl=!s.ampl;
      else if(a==='dia'){const d=Number(v);s.dia=s.dia===d?null:d;s.foco=null;s.tramo=null;s.doc=null;}
      else if(a==='calmes'){s.gran='Mes';s.dia=null;s.tramo=null;s.doc=null;s.foco=s.foco===v?null:v;}
      else if(a==='estadoDoc'){s.estadoDoc=v;s.modo='Detalle';s.doc=null;}
      else if(a==='porcFlag'){s.porcFlag=v;s.modo='Detalle';s.doc=null;}
      else if(a==='partir')s.partir=v;
      else if(a==='menu'){s.menu=s.menu===v?null:v;s.mq='';}
      else if(a==='cerrar')s.menu=null;
      else if(a==='limpiar')s[v]=[];
      else if(a==='todos'){['area','tipo','fam','prod'].forEach(k=>s[k]=[]);s.menu=null;}
      else if(a==='resaltar')s.resaltados[s.partir]=G.D.resaltado===v?null:v;
      else if(a==='sinresaltar')s.resaltados[s.partir]=null;
      else if(a==='rango'){s.foco=null;s.tramo=null;s.dia=null;}
      else if(a==='periodo'){s.foco=s.foco===v?null:v;s.tramo=null;s.dia=null;s.doc=null;}
      else if(a==='doc'){s.doc=v;}
      else if(a==='orden'){s.orden=s.orden?.id===id&&s.orden.k===v?{id,k:v,d:-s.orden.d}:{id,k:v,d:1};}
      else if(a==='excel'){const out=exportar(G);bajar(`${archivo(G.P.lado)}_periodo.xlsx`,libro(out.hojas));return;}
      dibujar(G);
    });
    on('input',e=>{const k=e.target.dataset.input;if(k){s[k]=e.target.value;dibujar(G);}});
    on('change',e=>{
      const k=e.target.dataset.filtro;
      if(k){s[k]=e.target.checked?[...s[k],e.target.value]:s[k].filter(v=>v!==e.target.value);s.foco=null;s.tramo=null;}
      else if(e.target.dataset.select==='resaltar')s.resaltados[s.partir]=e.target.value||null;
      else if(e.target.dataset.select==='marca')s.marca=e.target.value;
      else if(e.target.dataset.select==='estadoDoc')s.estadoDoc=e.target.value;
      else if(e.target.dataset.select==='porcFlag')s.porcFlag=e.target.value;
      else if(e.target.hasAttribute('data-completo'))s.completo=e.target.checked;
      else return;
      dibujar(G);
    });
    raiz.addEventListener('toggle',e=>{if(e.target.matches('.mv-ficha-porc')&&e.target.isConnected)s.mermaFicha=e.target.open;},{signal,capture:true});
    on('keydown',e=>{
      if(e.key==='Escape'){s.menu=null;tip(G,null);dibujar(G);}
      const b=e.target.closest('[data-bar]');
      if(b&&(e.key==='Enter'||e.key===' ')){e.preventDefault();elegirBarra(G,Number(b.dataset.bar));}
      const fila=e.target.closest('tr[data-a]');if(fila&&(e.key==='Enter'||e.key===' ')){e.preventDefault();fila.click();}
    });
    on('pointermove',e=>{const b=e.target.closest('[data-bar]');if(!G.drag)tip(G,b?Number(b.dataset.bar):null);});
    on('pointerleave',()=>tip(G,null));
    on('pointerdown',e=>{
      const b=e.target.closest('[data-bar]');if(!b || e.button!==0)return;
      G.drag={i:Number(b.dataset.bar),j:Number(b.dataset.bar),x:e.clientX,y:e.clientY,pointer:e.pointerId};
    });
    document.addEventListener('pointermove',e=>{
      const d=G.drag;if(!d||d.pointer!==e.pointerId||!G.chart)return;
      const rect=raiz.querySelector('.mv-grafico').getBoundingClientRect(),c=G.chart;
      d.j=Math.max(0,Math.min(c.N-1,Math.floor((e.clientX-rect.left-c.L)/c.pw*c.N)));
      if(Math.abs(e.clientX-d.x)>8){
        tip(G,null);const b=raiz.querySelector('.mv-brush');b.hidden=false;b.removeAttribute('hidden');
        b.setAttribute('x',c.L+Math.min(d.i,d.j)*c.pw/c.N);b.setAttribute('y',5);
        b.setAttribute('width',(Math.abs(d.i-d.j)+1)*c.pw/c.N);b.setAttribute('height',c.H-20);
      }
    },{signal});
    document.addEventListener('pointerup',e=>{
      const d=G.drag;if(!d||d.pointer!==e.pointerId)return;G.drag=null;
      if(Math.abs(e.clientY-d.y)>25&&Math.abs(e.clientX-d.x)<10)return;
      if(d.i!==d.j && Math.abs(e.clientX-d.x)>8){const a=Math.min(d.i,d.j),b=Math.max(d.i,d.j);s.tramo=[G.D.claves[a],G.D.claves[b]];s.foco=null;s.dia=null;s.doc=null;dibujar(G);}
      else elegirBarra(G,d.i);
    },{signal});
    document.addEventListener('pointercancel',()=>{G.drag=null;},{signal});
    document.addEventListener('click',e=>{
      if(s.menu&&!e.composedPath().includes(raiz)){s.menu=null;dibujar(G);}
    },{signal});
    // scroll no burbujea: una escucha en captura sirve para todas las tablas.
    raiz.addEventListener('scroll',e=>{
      const el=e.target;if(!el.dataset?.tabla||el.scrollTop+el.clientHeight<el.scrollHeight-220)return;
      const t=G.tablas[el.dataset.tabla];if(t&&t.cuantos<t.filas.length){el.querySelector('tbody').insertAdjacentHTML('beforeend',renglones(t,t.cuantos,t.cuantos+150,G));t.cuantos+=150;}
    },{signal,capture:true});
  }
  function elegirBarra(G,i) {
    const clave=G.D.claves[i];
    // Elegir no salta de pestaña: el panel cuenta el período y «Ver…» abre sus documentos.
    G.s.foco=G.s.foco===clave?null:clave;G.s.tramo=null;G.s.dia=null;G.s.doc=null;dibujar(G);
  }
  function montar(component) {
    const {data:P,parentElement}=component;
    window.__movPeriodoEstados ||= {};
    // El segundo montaje, chico: lo vendido y lo comprado de cada mes (regla #772).
    if(P.parte==='refs'){const g=window.__movPeriodoEstados[P.k];if(g&&!g.refs){g.refs=P.refs||{};dibujar(g);}return ()=>{};}
    const prev=window.__movPeriodoEstados[P.k];
    prev?.abort.abort();prev?.ro?.disconnect();
    const s=prev?.s||estado(P.inicial);
    if(prev&&prev.P.sello!==P.sello&&!(P.merma&&prev.P.sello_origen===P.sello_origen)){s.foco=null;s.tramo=null;s.doc=null;s.menu=null;}
    if(!GRANOS.includes(s.gran))s.gran='Semana';if(P.familia===false)s.fam=[];
    let raiz=parentElement.querySelector('.mv');if(!raiz){raiz=document.createElement('div');raiz.className='mv';parentElement.appendChild(raiz);}
    const mismo=prev&&prev.P.sello===P.sello&&prev.raiz===raiz;
    const G={P,s,raiz,base:mismo?prev.base:decodificar(P),hist:mismo?prev.hist:decodificar(P,true),abort:new AbortController(),tablas:{},cache:{},refs:prev?.refs,refsPedidas:prev?.refsPedidas,
      enviar:(k,v)=>component.setTriggerValue?.(k,v)};
    window.__movPeriodoEstados[P.k]=G;window.__movPeriodo=G;
    eventos(G);dibujar(G);
    return ()=>{G.abort.abort();G.ro?.disconnect();};
  }
  return {montar,calcular,estado,decodificar,documentos,productos,exportar,dibujar,tablas};
})();
window.__movPeriodoDatos = MOV;
export default function(component) { return MOV.montar(component); }
