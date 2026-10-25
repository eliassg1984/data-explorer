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
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normal = v => String(v ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const sumar = (rs, k = 'valor') => rs.reduce((a, r) => a + (r[k] || 0), 0);
  const unico = (rs, k) => new Set(rs.map(r => r[k])).size;
  const valido = r => !!r.prod && r.estado !== 'ANULADO';
  const ordenTexto = (a, b) => a < b ? -1 : a > b ? 1 : 0;
  const fecha = ms => new Date(ms).toISOString().slice(0, 16).replace('T', ' ');
  const dia = ms => Math.floor(ms / DIA);
  const por = (rs, k) => {
    const m = new Map();
    for (const r of rs) { const v = typeof k === 'function' ? k(r) : r[k]; if (!m.has(v)) m.set(v, []); m.get(v).push(r); }
    return m;
  };
  function decodificar(P, historial = false) {
    return (historial ? P.hist : P.filas).map(a => {
      const r = {fecha:a[0], cant:a[9], punit:a[10], valor:a[11], habitual:a[12] ?? null,
        veces:a[13] || 0, exceso:a[14] || 0, nuevo:!!a[15], repite:a[16] ?? null, marca:a[17] || ''};
      CAMPOS.forEach((k, i) => { r[k] = P.dic[k][a[i + 1]]; });
      return r;
    });
  }
  function estado(inicial = {}) {
    return {gran:'Semana', area:[], tipo:[], fam:[], prod:[], partir:null, resaltados:{},
      modo:'Resumen', q:'', marca:'Todas', foco:null, tramo:null, doc:null, completo:false,
      orden:null, menu:null, mq:'', ...inicial};
  }
  function filtros(rs, s, productos) {
    return rs.filter(r => ['area', 'tipo', 'fam'].every(k => !s[k]?.length || s[k].includes(r[k]))
      && (!s.prod?.length || productos.includes(r.prod)));
  }
  function opciones(rs, s, conTipo) {
    let restantes = rs.filter(valido);
    const ops = {}, rank = (xs, k) => [...por(xs, k)].map(([n, g]) => [n, sumar(g)])
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
  function documentos(rs, fem = false) {
    return [...por(rs, 'doc')].map(([doc, g]) => {
      const primero = g[0], lineas = g.filter(r => r.prod).length;
      const anulado = primero.estado === 'ANULADO', generado = primero.estado === 'GENERADO';
      return {doc, fecha:Math.min(...g.map(r => r.fecha)), area:primero.area, tipo:primero.tipo,
        causa:primero.causa, estado:anulado ? fem ? 'Anulada' : 'Anulado' : generado ? 'Sin procesar' : !lineas ? 'Sin ítems' : '',
        lineas, valor:sumar(g), suma:!anulado && !!lineas,
        rotulo:anulado ? fem ? 'Anulada' : 'Anulado' : !lineas ? generado ? 'Sin procesar' : 'Sin ítems' : '',
        rep:g.filter(r => r.repite != null).length,
        fuera:g.filter(r => r.veces > 0 || r.nuevo).length,
        busqueda:normal([doc, primero.area, primero.tipo, primero.causa, ...g.map(r => r.prod)].join(' '))};
    }).sort((a,b) => b.valor-a.valor || ordenTexto(a.doc,b.doc));
  }
  function productos(rs) {
    return [...por(rs.filter(valido), r => JSON.stringify([r.prod, r.unid]))].map(([,g]) => ({
      prod:g[0].prod, unid:g[0].unid, cant:sumar(g, 'cant'), valor:sumar(g), docs:unico(g, 'doc'),
      lineas:g.length, areas:unico(g, 'area'), rep:g.filter(r => r.repite != null).length,
      fuera:g.filter(r => r.veces > 0 || r.nuevo).length,
    })).sort((a,b) => b.valor-a.valor || ordenTexto(a.prod,b.prod));
  }
  function firma(s) {
    return JSON.stringify([s.gran,s.area,s.tipo,s.fam,s.prod,s.partir,s.resaltados]);
  }
  function calcular(P, st, base = decodificar(P), hist = decodificar(P, true), cache = null) {
    const s = estado(st), plan = P.planes[s.gran] || P.planes.Semana;
    if(cache?.firma===firma(s))return detalle(P,s,cache.core,cache);
    const ops = opciones(base, s, P.tipo);s.prod = ops.prodSel;
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
    const resaltado = guardado === null ? null : resaltables.includes(guardado) ? guardado : resaltables[0] || null;
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
    const acotado = !!(s.tramo || s.foco);
    const ambito=JSON.stringify([s.foco,s.tramo]);
    let scope=cache?.ambito===ambito?cache.scope:null;
    if(!scope){
      const amb=acotado ? bl.filter(r => seleccion.includes(plan.mapa[dia(r.fecha)])) : bl;
      const vs=amb.filter(valido);
      scope={amb,ds:documentos(amb,P.fem),productos:productos(amb),total:sumar(vs),nDocs:unico(vs,'doc'),
        rep:sumar(vs.filter(r=>r.repite!=null)),fuera:sumar(vs.filter(r=>r.veces>0||r.nuevo)),exceso:sumar(vs,'exceso')};
      if(cache){cache.ambito=ambito;cache.scope=scope;}
    }
    const {amb,ds}=scope, q = normal(s.q);
    const docs = ds.filter(r => (!q || r.busqueda.includes(q)) && (s.marca === 'Todas'
      || (s.marca === REP ? r.rep > 0 : r.fuera > 0)));
    const elegido = docs.some(r => r.doc === s.doc) ? s.doc : docs.find(r => r.suma)?.doc ?? docs[0]?.doc ?? null;
    const lineas = (s.completo ? base : amb).filter(r => r.doc === elegido && r.prod).sort((a,b) => b.valor-a.valor);
    const indices = claves.map((k,i) => seleccion.includes(k) ? i : -1).filter(i => i >= 0);
    const compSel = comps.map(c => ({...c, valor:acotado ? indices.reduce((a,i) => a+c.valores[i],0) : c.total}));
    const registroVisible = s.gran === 'Mes' && !s.area.length && !s.fam.length && !s.prod.length
      && (!s.tipo.length || (s.tipo.length === 1 && s.tipo[0] === 'Bajas'))
      && !Object.values(P.contexto).some(v => v.length);
    const units = [...new Set(validas.map(r => r.unid))];
    return {ops, partir, partirOps, resaltables, resaltado, bl, validas, series, claves, trazas, comps,
      seleccion, amb, docs, todosDocs:ds, elegido, lineas, productos:scope.productos, compSel,
      total:scope.total, nDocs:scope.nDocs, rep:scope.rep,fuera:scope.fuera,
      exceso:scope.exceso, unidades:units,
      registro:registroVisible ? Object.fromEntries(series.filter(r => !r.parcial && P.registro[r.clave]).map(r => [r.clave,P.registro[r.clave]])) : {},
      noSuman:ds.filter(r => !r.suma).length, acotado};
  }

  function columna(k, nombre, tipo = '') { return {k, nombre, tipo}; }
  function tablas(G) {
    const {P, D, s} = G;
    let resumen = [columna('fila','Período'), columna('valor','Valorizado','dinero'), columna('docs',P.lado,'n'),
      columna('areas','Áreas','n'), columna('lineas','Líneas','n'), columna('variacion','Variación','pct'),
      columna('estado','Estado')];
    if (D.unidades.length === 1 && D.unidades[0]) resumen.splice(5,0,columna('cant',`Cantidad (${D.unidades[0]})`,'cant'));
    if (P.marcas) resumen = resumen.concat([columna('por_dia','Req./día','cant'), columna('rep_n','Lín. repetidas','n'),
      columna('rep_v','Valor repetido','dinero'), columna('fuera_n','Lín. sobre habitual','n'),
      columna('fuera_v','Exceso','dinero'), columna('nuevos_n','Lín. nuevas','n')]);
    if (Object.keys(D.registro).length) resumen.push(columna('registro','Bajas / faltante'));
    const filas = D.series.filter(r => D.seleccion.includes(r.clave)).map(r => ({...r,
      estado:[r.parcial ? 'Período parcial' : '',r.anulados ? `${r.anulados} anulado(s)` : '',
        r.sin_procesar ? `${r.sin_procesar} sin procesar` : '',r.poco ? 'Poco registro' : ''].filter(Boolean).join(' · '),
      registro:D.registro[r.clave] ? `${fmt.format(D.registro[r.clave][1])} %` : '—'}));
    const docs = [columna('fecha','Fecha','fecha'), columna('doc','Código'), columna('area','Área'),
      ...(P.tipo ? [columna('tipo','Tipo'),columna('causa','Causa')] : []), columna('lineas','Líneas','n'),
      columna('valor','Valorizado','docValor'), columna('estado','Estado'),
      ...(P.marcas ? [columna('rep','Repetidas','n'),columna('fuera','Fuera de habitual','n')] : [])];
    const lineas = [columna('prod','Producto'), columna('unid','Unidad'), columna('cant','Cantidad','cant'),
      columna('punit','Precio unit.','precio'), columna('valor','Valorizado','dinero'),columna('area','Área'),
      columna('fam','Familia'), ...(P.marcas ? [columna('marca','Marca')] : [])];
    const prods = [columna('prod','Producto'),columna('unid','Unidad'),columna('cant','Cantidad','cant'),
      columna('valor','Valorizado','dinero'),columna('docs','Documentos','n'),columna('areas','Áreas','n'),columna('lineas','Líneas','n')];
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
    if (c.tipo === 'fecha') return fecha(v);
    if (c.tipo === 'pct') return pct(v);
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
  function segmento(valores, actual, accion) {
    return `<div class="mv-seg">${valores.map(v => `<button data-a="${accion}" data-v="${esc(v)}" aria-pressed="${v === actual}" class="${v === actual ? 'on' : ''}">${esc(v)}</button>`).join('')}</div>`;
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
  function dibujar(G) {
    const {s,P,raiz} = G;
    G.D = calcular(P,s,G.base,G.hist,G.cache);const D=G.D;
    s.prod = D.ops.prodSel;s.partir = D.partir;s.doc=D.elegido;
    if(s.modo==='Comparación'&&!D.comps.length)s.modo='Resumen';
    G.T = tablas(G);G.tablas={};
    const enfocado = raiz.querySelector('input:focus');
    const foco = enfocado ? [enfocado.dataset.input,enfocado.selectionStart,enfocado.selectionEnd] : null;
    const scrolls = [...raiz.querySelectorAll('[data-tabla]')].map(e => [e.dataset.tabla,e.scrollTop,e.scrollLeft]);
    const filtrosHTML = [['area','Área'],...(P.tipo ? [['tipo','Tipo de descargo']] : []),['fam','Familia'],['prod','Producto']].map(([k,n]) =>
      `<button class="mv-filtro ${s[k].length ? 'activo' : ''}" data-a="menu" data-v="${k}" aria-expanded="${s.menu === k}" title="${esc(s[k].join(', ') || `Todas las opciones de ${n}`)}">${n}<strong>${s[k].length ? esc(s[k].length === 1 ? s[k][0] : `${s[k].length} elegidos`) : 'Todos'}</strong><span>⌄</span></button>`).join('');
    const kpi = (titulo, valor, nota, accion='', v='', title='') => `<${accion ? 'button' : 'div'} class="mv-kpi ${accion && D.resaltado === v ? 'on' : ''}" ${accion ? `data-a="${accion}" data-v="${esc(v)}"` : ''} title="${esc(title || nota)}"><span>${esc(titulo)}</span><b>${esc(valor)}</b><small>${esc(nota)}</small></${accion ? 'button' : 'div'}>`;
    const highlights = D.resaltables.filter(x => x !== REP && x !== FUERA).slice(0,3);
    let kpis = kpi(D.acotado ? 'Valorizado del tramo' : P.titulo,dinero(D.total),`${entero.format(D.nDocs)} ${P.lado}${D.noSuman ? ` · ${D.noSuman} no suman` : ''}`);
    if (P.marcas) {
      kpis += kpi(REP,dinero(D.rep),'Líneas ya pedidas en el día','resaltar',REP,'Puede coincidir con «Fuera de lo habitual». No se suman ambas marcas.');
      kpis += kpi(FUERA,dinero(D.fuera),`Exceso: ${dinero(D.exceso)}`,'resaltar',FUERA,'Valor de las líneas sobre lo habitual o nuevas. El exceso es sólo la diferencia sobre la referencia.');
    } else {
      for (const nombre of highlights) {
        const t=D.trazas.find(t => t.nombre === nombre);const value=t.valores.reduce((a,v,i) => a+(D.seleccion.includes(D.claves[i]) ? v : 0),0);
        kpis += kpi(nombre,dinero(value),D.total > 0 ? `${fmt.format(value / D.total * 100)} % del ámbito` : '', 'resaltar',nombre);
      }
    }
    const context = Object.entries(P.contexto).filter(([,v]) => v.length).map(([k,v]) => `${k}: ${v.join(', ')}`).join(' · ');
    const fechaRango = `${P.rango[0].slice(0,10)} al ${new Date(new Date(P.rango[1].replace(' ','T')).getTime()-DIA).toISOString().slice(0,10)}`;
    let html = `<section class="mv-card mv-main"><header><div><h3>${esc(P.titulo)}</h3><p>${esc(fechaRango)} · ${esc(P.rot_fecha || 'fecha del documento')}</p></div></header>`
      + `<div class="mv-controles">${segmento(GRANOS,s.gran,'gran')}${P.tipo ? segmento(D.partirOps,D.partir,'partir') : ''}</div>`
      + `<div class="mv-filtros">${filtrosHTML}${Object.values(s).some(v => Array.isArray(v) && v.length) && ['area','tipo','fam','prod'].some(k => s[k].length) ? '<button data-a="todos" class="mv-quitar">Quitar filtros</button>' : ''}</div>`
      + `<div class="mv-kpis">${kpis}</div><div class="mv-leyenda"><span>${D.resaltado ? `Resaltado: ${esc(D.resaltado)}` : 'Valorizado total'}${D.resaltado ? ' · ' : ''}</span>${D.resaltado ? '<button data-a="sinresaltar">Ver total</button>' : ''}`
      + `<select data-select="resaltar" aria-label="Resaltar parte"><option value="">Elegir parte…</option>${D.resaltables.map(v => `<option ${v === D.resaltado ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>`
      + D.compSel.map(c => `<span title="${esc(c.docs)} documentos en el rango comparable completo">┄ ${esc(c.rot)}: ${dinero(c.valor)} · ${pct(c.valor > 0 ? (D.total-c.valor)/c.valor*100 : null)}</span>`).join('')
      + `</div><div class="mv-grafico" aria-label="Valorizado por período"><svg role="img" aria-label="Barras por período"></svg><div class="mv-tip" hidden></div></div>`
      + `<div class="mv-notas"><span>${D.series.length ? 'Clic: detalle del período · Arrastrá: elegir tramo' : 'Sin movimientos que sumen. Ampliá la fecha o quitá un filtro.'}</span>${D.acotado ? '<button data-a="rango">Todo el rango</button>' : ''}<span>${esc(context)}</span></div>`
      + (P.poco.length ? `<p class="mv-aviso" title="Meses completos con menos de la mitad de los documentos habituales; referencia: mediana de los doce meses anteriores con al menos seis meses de datos.">Poco registro en ${P.poco.map(m => `${esc(m.mes)} (${m.docs} documentos; referencia ${cantidad.format(m.referencia)})`).join(' · ')}. Una barra menor puede reflejar menos registros.</p>` : '')
      + `${menu(G)}</section><section class="mv-card mv-detalle"><div class="mv-cab-det"><h3>${esc(ambito(G))}</h3><button data-a="excel" title="Descargar los datos y el contexto de esta vista">Excel de esta vista ↓</button></div>`
      + `<div class="mv-barra">${segmento(['Resumen','Detalle','Productos',...(D.comps.length ? ['Comparación'] : [])],s.modo,'modo')}<span class="mv-total">${dinero(D.total)} · ${D.nDocs} ${esc(P.corto)}</span></div>`;
    if (s.modo === 'Detalle') {
      html += `<div class="mv-buscar"><input data-input="q" type="search" aria-label="Buscar documentos o productos" placeholder="Buscar código, producto, área…" value="${esc(s.q)}">${P.marcas ? `<select data-select="marca" aria-label="Filtrar documentos por marca">${['Todas',REP,FUERA].map(v => `<option ${s.marca === v ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>` : ''}<span>${D.docs.length} documentos${s.marca !== 'Todas' ? ' · con líneas marcadas' : ''}</span></div>`
        + `<div class="mv-documentos">${tabla(G,G.T.docs,'docs')}</div><div class="mv-doc-cab"><b>${esc(P.sing)} ${esc(D.elegido || '—')}</b><label><input type="checkbox" data-completo ${s.completo ? 'checked' : ''}> Documento completo</label><span>${s.completo ? 'Líneas disponibles con las fechas y filtros de la página' : 'Líneas dentro de los filtros y el tramo'}</span></div>`
        + `<div class="mv-lineas">${tabla(G,G.T.lineas,'lineas')}</div>`;
    } else if (s.modo === 'Productos') html += tabla(G,G.T.productos,'productos') + '<p class="mv-pie">Cantidades separadas por producto y unidad; no se suman unidades distintas.</p>';
    else if (s.modo === 'Comparación') {
      html += tabla(G,G.T.comp,'comp') + `<p class="mv-pie">Día y semana: 364 días por año, comparando el mismo día de la semana. Mes y año: calendario. «Sin base» indica una referencia sin valor positivo. Las fechas pueden cortar períodos.${D.acotado ? ' Totales de las barras del tramo elegido.' : ' El total histórico de la leyenda incluye todo el rango desplazado, incluso períodos sin barra actual.'}</p>`;
    } else html += tabla(G,G.T.resumen,'resumen') + `<p class="mv-pie">Variación frente a la barra anterior. Los períodos parciales no muestran porcentaje.${Object.keys(D.registro).length ? ' Bajas / faltante: bajas registradas del mes completo divididas por el faltante de su cierre.' : ''}${P.marcas ? ' Las marcas pueden coincidir: sus importes no se suman entre sí.' : ''}</p>`;
    html += '</section>';
    raiz.innerHTML=html;
    const fb=document.querySelector(`.st-key-${P.k}_nativa_fecha`);
    raiz.style.setProperty('--mv-fecha',`${fb?.offsetWidth ? fb.offsetWidth+24 : 0}px`);
    if (foco) {
      const e=raiz.querySelector(`input[data-input="${foco[0]}"]`);
      if (e) { e.focus({preventScroll:true});if (e.type !== 'checkbox') e.setSelectionRange(foco[1],foco[2]); }
    }
    scrolls.forEach(([id,top,left]) => { const e=raiz.querySelector(`[data-tabla="${id}"]`);if(e){e.scrollTop=top;e.scrollLeft=left;} });
    G.ro?.disconnect();G.ro=new ResizeObserver(() => grafico(G));G.ro.observe(raiz.querySelector('.mv-grafico'));
    grafico(G);
  }
  function grafico(G) {
    const box=G.raiz.querySelector('.mv-grafico'), svg=box?.querySelector('svg');if(!svg)return;
    const W=box.clientWidth,H=box.clientHeight;if(W<80 || H<60)return;
    const rs=G.D.series, N=rs.length, L=68,R=14,T=27,B=G.s.gran==='Semana'?49:36, pw=W-L-R, ph=H-T-B;
    svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('width',W);svg.setAttribute('height',H);
    if(!N){svg.innerHTML='';return;}
    const highlight=G.D.trazas.find(t=>t.nombre===G.D.resaltado);
    const vals=[0,...rs.map(r=>r.valor),...G.D.comps.flatMap(c=>c.valores),...(highlight?.valores||[])];
    const max=Math.max(...vals,1)*1.15,min=Math.min(...vals,0)*1.15,span=max-min;
    const y=v=>T+(max-v)/span*ph,x=i=>L+(i+.5)*pw/N, bw=Math.max(1,pw/N*.68),zero=y(0);
    G.chart={x,y,W,H,L,pw,N,rs};
    let html='';
    for(let i=0;i<4;i++){const v=min+span*i/3,yy=y(v);html+=`<line x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}" class="mv-grid"/><text x="${L-8}" y="${yy+4}" text-anchor="end" class="mv-axis">${esc(cantidad.format(Math.round(v)))}</text>`;}
    const cada=Math.max(1,Math.ceil(N/(pw/(G.s.gran==='Semana'?140:85))));
    rs.forEach((r,i)=>{
      const xx=x(i), yy=y(r.valor), alto=Math.max(1,Math.abs(zero-yy)),select=G.D.seleccion.includes(r.clave);
      if(r.especial)html+=`<rect x="${xx-pw/N/2}" y="${T}" width="${pw/N}" height="${ph}" class="mv-feriado"><title>${esc(r.especial)}</title></rect>`;
      html+=`<g opacity="${select?1:.25}"><rect x="${xx-bw/2}" y="${Math.min(yy,zero)}" width="${bw}" height="${alto}" class="mv-bar ${highlight?'suave':''}"/>`;
      if(highlight){const v=highlight.valores[i],hy=y(v);html+=`<rect x="${xx-bw/2}" y="${Math.min(hy,zero)}" width="${bw}" height="${Math.max(1,Math.abs(zero-hy))}" class="mv-bar"/>`;}
      G.D.comps.forEach((c,j)=>{const cy=y(c.valores[i]);html+=`<line x1="${xx-bw*.8}" x2="${xx+bw*.8}" y1="${cy}" y2="${cy}" class="mv-comp c${j}"/>`;});
      if(pw/N>65)html+=`<text x="${xx}" y="${Math.max(T-6,yy-8)}" text-anchor="middle" class="mv-label">${esc(entero.format(r.valor))}</text>`;
      if(i%cada===0)html+=`<text x="${xx}" y="${H-B+19}" text-anchor="middle" class="mv-axis">${esc(r.eje)}</text>${G.s.gran==='Semana'?`<text x="${xx}" y="${H-9}" text-anchor="middle" class="mv-axis">${esc(r.clave.slice(0,4))}</text>`:''}`;
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
      ['Fecha usada',P.rot_fecha],['Agrupación',s.gran],['Detalle elegido',ambito(G)],['Modo',s.modo],
      ...Object.entries(P.contexto).map(([k,v])=>[k,v.join(', ')||'Todas']),
      ...['area','tipo','fam','prod'].map(k=>[`Filtro ${k}`,s[k].join(', ')||'Todos']),
      ['Búsqueda en documentos',s.q],['Marca en documentos',s.marca],['Documento elegido',D.elegido||''],
      ['Líneas del documento',s.completo?'Completo con fechas y filtros de la página':'Dentro de los filtros y tramo'],
      ['Marcas','Pueden coincidir. No sumar sus importes entre sí.'],
      ['Comparación','Día y semana: 364 días por año; mes y año: calendario. Sin base si referencia <= 0.'],
      ['Decimales','Valores numéricos con seis decimales; totales calculados sin redondear.'],
      ['Valorizado del ámbito',D.total],['Documentos válidos del ámbito',D.nDocs]];
    D.compSel.forEach(c=>contexto.push([`Total comparable ${c.rot}`,c.valor]));
    const docsVisibles=new Set(D.docs.map(r=>r.doc));
    const hojas=[hoja('Resumen',T.resumen),hoja('Documentos',T.docs),hoja('Productos',T.productos),
      hoja('Líneas del documento',T.lineas)];
    if(s.modo==='Detalle')hojas.push(hoja('Líneas de documentos visibles',{...T.lineas,filas:D.amb.filter(r=>r.prod&&docsVisibles.has(r.doc))}));
    if(D.comps.length)hojas.push(hoja('Comparación',T.comp));
    hojas.push({nombre:'Contexto',cabeza:['Dato','Selección'],decimales:6,filas:contexto});
    return {hojas,indices};
  }
  function eventos(G) {
    const {raiz,s}=G, signal=G.abort.signal;
    const on=(evento,fn)=>raiz.addEventListener(evento,fn,{signal});
    on('click',e=>{
      const b=e.target.closest('[data-a]');if(!b)return;
      const {a,v,id}=b.dataset;
      if(a==='gran'){s.gran=v;s.foco=null;s.tramo=null;s.doc=null;}
      else if(a==='modo'){s.modo=v;s.orden=null;}
      else if(a==='partir')s.partir=v;
      else if(a==='menu'){s.menu=s.menu===v?null:v;s.mq='';}
      else if(a==='cerrar')s.menu=null;
      else if(a==='limpiar')s[v]=[];
      else if(a==='todos'){['area','tipo','fam','prod'].forEach(k=>s[k]=[]);s.menu=null;}
      else if(a==='resaltar')s.resaltados[s.partir]=G.D.resaltado===v?null:v;
      else if(a==='sinresaltar')s.resaltados[s.partir]=null;
      else if(a==='rango'){s.foco=null;s.tramo=null;}
      else if(a==='periodo'){s.foco=v;s.tramo=null;s.modo='Detalle';s.doc=null;}
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
      else if(e.target.hasAttribute('data-completo'))s.completo=e.target.checked;
      else return;
      dibujar(G);
    });
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
      if(d.i!==d.j && Math.abs(e.clientX-d.x)>8){const a=Math.min(d.i,d.j),b=Math.max(d.i,d.j);s.tramo=[G.D.claves[a],G.D.claves[b]];s.foco=null;s.doc=null;dibujar(G);}
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
    G.s.foco=G.s.modo==='Detalle'&&G.s.foco===clave?null:clave;G.s.tramo=null;G.s.modo='Detalle';G.s.doc=null;dibujar(G);
  }
  function montar(component) {
    const {data:P,parentElement}=component;
    window.__movPeriodoEstados ||= {};
    const prev=window.__movPeriodoEstados[P.k];
    prev?.abort.abort();prev?.ro?.disconnect();
    const s=prev?.s||estado(P.inicial);
    if(prev&&prev.P.sello!==P.sello){s.foco=null;s.tramo=null;s.doc=null;s.menu=null;}
    if(!GRANOS.includes(s.gran))s.gran='Semana';
    let raiz=parentElement.querySelector('.mv');if(!raiz){raiz=document.createElement('div');raiz.className='mv';parentElement.appendChild(raiz);}
    const G={P,s,raiz,base:decodificar(P),hist:decodificar(P,true),abort:new AbortController(),tablas:{},cache:{}};
    window.__movPeriodoEstados[P.k]=G;window.__movPeriodo=G;
    eventos(G);dibujar(G);
    return ()=>{G.abort.abort();G.ro?.disconnect();};
  }
  return {montar,calcular,estado,decodificar,documentos,productos,exportar,dibujar,tablas};
})();
window.__movPeriodoDatos = MOV;
export default function(component) { return MOV.montar(component); }
