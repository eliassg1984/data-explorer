/* El flujo del inventario de «En qué se fue cada producto» (regla #743):
   la franja compacta, el flujo neteado del restaurante con su panel,
   «Cómo se calcula» y, con DESTINO_AREAS, el mapa por área. Trabaja sobre
   las filas que ya trae la pieza; nada vuelve a Python. Desde la regla
   #750, un solo reloj: de conteo a conteo de cada área. */
const DESTINO_FLUJO = (() => {
  const fmt = (x, d = 0) => Number(x || 0).toLocaleString('es-PE', {maximumFractionDigits: d});
  const sol = x => (x < -0.005 ? '−' : '') + 'S/ ' + fmt(Math.abs(x));
  const esc = x => String(x ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const r1 = x => Math.round(x * 10) / 10;
  const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
  const dia = iso => { const t = new Date(iso); return `${t.getDate()} ${MESES[t.getMonth()]}`; };
  const hora = iso => { const t = new Date(iso); return `${dia(iso)} ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`; };
  const flecha = c => c == null || !Number.isFinite(c) ? '' : (c < 0 ? '▼ ' : '▲ ') + fmt(Math.abs(c), 1) + ' %';
  const cambio = (a, b) => b != null && Math.abs(b) > 0.5 ? (a - b) / Math.abs(b) * 100 : null;

  const BASE = {abierto: false, vista: 'restaurante', que: 'flujo', modo: 'resumen', simular: false, sim: 'p20',
    sel: '', forma: 'mapa', capas: {}, presentar: false, paso: 1, asel: ''};
  function estado(g) {
    const s = {...BASE, ...(g && typeof g === 'object' ? g : {})};
    if (!['restaurante', 'area'].includes(s.vista)) s.vista = 'restaurante';
    if (!['flujo', 'calculo'].includes(s.que)) s.que = 'flujo';
    if (!['resumen', 'desglose'].includes(s.modo)) s.modo = 'resumen';
    if (!['p10', 'p20', 'p30', 'mejor'].includes(s.sim)) s.sim = 'p20';
    if (!['mapa', 'matriz'].includes(s.forma)) s.forma = 'mapa';
    if (typeof s.sel !== 'string') s.sel = '';
    if (typeof s.asel !== 'string') s.asel = '';
    if (!s.capas || typeof s.capas !== 'object') s.capas = {};
    s.abierto = !!s.abierto; s.simular = !!s.simular; s.presentar = !!s.presentar;
    s.paso = Math.max(1, Math.min(6, Number(s.paso) || 1));
    return s;
  }

  // ── Los conceptos del flujo ────────────────────────────────────────────
  function definiciones(P, grupo) {
    const c = P.colores, f = P.colores_flujo, alim = grupo !== P.operacion;
    const D = {
      ini: {lado: 'in', label: 'Stock inicial', color: f.ini, col: 'ini_v', stock: true},
      compra: {lado: 'in', label: 'Compras netas', color: f.compra, col: 'compra_v'},
      sobr: {lado: 'in', label: 'Sobrante al contar', color: f.sobr, col: 'sobr_v'},
      val: {lado: 'in', label: 'Valorización (neto)', color: f.val, col: ''},
      fin: {lado: 'out', label: 'Quedó en stock', color: f.fin, col: 'fin_v', stock: true}
    };
    if (alim) Object.assign(D, {
      plato: {lado: 'out', label: 'A un plato', color: c.venta, partes: ['venta', 'cort', 'evvi'], col: 'plato_v'},
      sinplato: {lado: 'out', label: 'Sin plato', color: c.falt, partes: ['falt', 'otras', 'baja'], col: 'sinplato_v', tono: 'baja'},
      venta: {lado: 'out', g: 'plato', label: 'Venta', color: c.venta, col: 'venta_v'},
      cort: {lado: 'out', g: 'plato', label: 'Cortesías', color: c.cort, col: 'cort_v'},
      evvi: {lado: 'out', g: 'plato', label: 'Eventos y venta interna', color: c.evvi, col: 'evvi_v'},
      falt: {lado: 'out', g: 'sinplato', label: 'Faltante', color: c.falt, col: 'falt_v', tono: 'baja'},
      otras: {lado: 'out', g: 'sinplato', label: 'Otras notas', color: c.otras, col: 'otras_v', tono: 'sube'},
      baja: {lado: 'out', g: 'sinplato', label: 'Bajas', color: c.baja, col: 'baja_v', tono: 'sube'}
    });
    else Object.assign(D, {
      falt: {lado: 'out', label: 'Consumido al contar', color: f.consumo, col: 'falt_v'},
      notas: {lado: 'out', label: 'Notas de salida', color: c.otras, col: 'notas'}
    });
    return D;
  }
  const valorProducto = r => (r.fin_v || 0) - ((r.ini_v || 0) + (r.entro_v || 0) - (r.plato_v || 0) - (r.prep_v || 0) - (r.sinplato_v || 0) + (r.sobr_v || 0));
  const valorDe = (r, id, D) => id === 'notas' ? (r.baja_v || 0) + (r.otras_v || 0) : id === 'val' ? valorProducto(r) : (r[D[id]?.col] || 0);
  const PRED = {
    neg: r => r.fin_q < -0.05,
    val: r => Math.abs(valorProducto(r)) > 0.5,
    notas: r => (r.baja_v || 0) + (r.otras_v || 0) > 0.5
  };
  function predicado(id, D) {
    if (PRED[id]) return PRED[id];
    const col = D[id]?.col;
    return col ? r => (r[col] || 0) > 0.5 : null;
  }

  /* La cuenta del restaurante sobre las filas del alcance: con el reloj
     operativo y el grupo entero, lo vendido de un lado del conteo y
     descontado del otro pasa de faltante a plato (no es por producto). */
  function cuenta(P, rows, k, grupo, completo) {
    const n = {}, s = c => rows.reduce((a, r) => a + (r[c] || 0), 0);
    for (const c of ['ini', 'compra', 'sobr', 'venta', 'cort', 'evvi', 'falt', 'otras', 'baja', 'fin', 'prep', 'combos', 'entro'])
      n[c] = s(c + '_v');
    n.borde = 0;
    if (completo && grupo !== P.operacion && P.reloj === 'operativo') {
      const b = P.borde[k] || [0, 0, 0];
      n.borde = b[0] - b[1]; n.venta += n.borde; n.falt -= n.borde;
    }
    n.plato = n.venta + n.cort + n.evvi; n.notas = n.otras + n.baja; n.sinplato = n.falt + n.notas;
    const outs = (grupo === P.operacion ? n.falt + n.notas : n.plato + n.sinplato) + n.fin;
    n.val = outs - (n.ini + n.compra + n.sobr);
    const neg = rows.filter(r => r.fin_q < -0.05);
    n.neg = {n: neg.length, v: -neg.reduce((a, r) => a + Math.min(0, r.fin_v || 0), 0),
      tops: [...neg].sort((a, b) => a.fin_v - b.fin_v).slice(0, 3)};
    n.dias = P.periodos[k]?.dias || 1;
    return n;
  }

  /* Los nodos de cada lado, con signo: un stock que cerró en negativo o
     una valorización en contra cambian de lado. Los dos lados suman igual. */
  function nodos(P, n, grupo, modo) {
    const D = definiciones(P, grupo), alim = grupo !== P.operacion;
    const outs = alim ? (modo === 'desglose' ? ['venta', 'cort', 'evvi', 'falt', 'otras', 'baja'] : ['plato', 'sinplato']) : ['falt', 'notas'];
    const L = [...['ini', 'compra', 'sobr'].map(id => ({id, lado: 'in', v: n[id]})),
      ...[...outs, 'fin'].map(id => ({id, lado: 'out', v: n[id]})), {id: 'val', lado: 'in', v: n.val}];
    return L.filter(x => Math.abs(x.v) > 0.5).map(x => {
      const neg = x.v < 0, lado = neg ? (x.lado === 'in' ? 'out' : 'in') : x.lado;
      const label = !neg || x.id === 'val' ? D[x.id].label : D[x.id].label + ' en negativo';
      return {...D[x.id], id: x.id, lado, v: Math.abs(x.v), neg, label};
    });
  }

  // ── Textos que salen de los datos ──────────────────────────────────────
  function codigo(P, id, k, grupo) {
    const op = P.reloj === 'operativo', p = P.periodos[k];
    if (grupo === P.operacion && id === 'falt') return 'Kardex 93 · lo que se usó aparece al contar';
    return {
      ini: op ? 'Foto del kardex justo después del conteo anterior de cada área' : `Foto del kardex al fin del día anterior al ${dia(p.desde + 'T00:00')}`,
      compra: op ? 'Kardex < 90, cortado en el conteo de cada área' : 'Kardex < 90 · documentos de compra',
      sobr: 'Kardex 93 · ajuste positivo del conteo', val: 'Diferencia del balance en soles',
      plato: op ? 'Kardex 95 + ventas de antes del conteo descontadas después (paloteo)' : 'Kardex 95 · descargo de ventas (se corre a mano, por las mañanas)',
      sinplato: 'Faltante (93) + bajas y otras notas (91 · 92 · 98)',
      fin: op ? 'Foto del kardex justo después del conteo de cada área' : `Foto del kardex al fin del día (${dia(p.hasta + 'T00:00')} 23:59)`,
      venta: 'Kardex 95, repartido con lo vendido en el POS', cort: 'Kardex 95, repartido con lo vendido en el POS',
      evvi: 'Kardex 95, repartido con lo vendido en el POS',
      falt: op ? 'Kardex 93, sin las ventas que el descargo no tomó a tiempo' : 'Kardex 93 · ajuste negativo del conteo',
      otras: 'Kardex 91 · 92 · 98, sin las bajas', baja: 'Notas de salida «Bajas» (98), por fecha de proceso',
      notas: 'Kardex 91 · 92 · 98', neg: ''
    }[id] || '';
  }

  /* El resumen del restaurante de cada cierre, de conteo a conteo (desde la
     regla #750 el único reloj: el del kardex se fue). */
  function puente(P, k) {
    const o = (P.puente.operativo || [])[k];
    return o ? {o, oa: (P.puente.operativo || [])[k - 1]} : null;
  }

  function nota(ctx, id) {
    const {P, n, k, grupo, completo, rows, ant} = ctx, op = P.reloj === 'operativo', b = P.borde[k] || [0, 0, 0];
    if (id === 'ini' || id === 'fin') {
      const pos = rows.reduce((a, r) => a + Math.max(0, r[id + '_v'] || 0), 0), neg = rows.filter(r => (r[id + '_v'] || 0) < -0.5);
      return `Neto: ${sol(pos)} en positivo menos ${sol(-neg.reduce((a, r) => a + r[id + '_v'], 0))} de ${neg.length} productos que ${id === 'ini' ? 'arrancaron' : 'cerraron'} en negativo.`;
    }
    if (grupo === P.operacion) return id === 'falt' ? 'Carbón, leña, limpieza y descartables: ninguna receta los descarga, su uso aparece al contar.' : '';
    if (id === 'plato' && b[0] > 0.5) return op
      ? `Suma ${sol(b[0])} vendidos antes del conteo y descontados después o nunca (${sol(b[2])} nunca) y resta ${sol(b[1])} que eran del cierre anterior.`
      : `Le faltan ${sol(b[0])} vendidos antes del conteo que el descargo no tomó a tiempo (${sol(b[2])} nunca se descontaron).`;
    if (id === 'falt' && b[0] > 0.5) return op
      ? `Sin las ventas sin descontar al contar: −${sol(b[0])} de este cierre y +${sol(b[1])} que el anterior le había pasado.`
      : `Incluye ${sol(b[0])} de ventas sin descontar al contar: no son pérdida.`;
    if (id === 'sinplato') {
      const salio = n.plato + n.sinplato, prev = ctx.historia.slice(-7, -1), sp = prev.reduce((a, h) => a + h.n.sinplato, 0), sa = prev.reduce((a, h) => a + h.n.plato + h.n.sinplato, 0);
      return `${fmt(n.sinplato / Math.max(1, salio) * 100, 1)} % de lo que salió hacia afuera` + (ant ? ` · ${P.periodos[k - 1].corto} ${fmt(ant.sinplato / Math.max(1, ant.plato + ant.sinplato) * 100, 1)} %` : '') + (sa > 0 ? ` · seis cierres ${fmt(sp / sa * 100, 1)} %` : '') + '.';
    }
    if (id === 'venta' && n.combos > 0.5) return `Incluye ${sol(n.combos)} servidos dentro de combos.`;
    if (id === 'otras') return 'Notas 98 que no son baja: personal, uso del área y otras.';
    if (id === 'val') {
      const v = rows.map(valorProducto), mas = v.reduce((a, x) => a + Math.max(0, x), 0), menos = -v.reduce((a, x) => a + Math.min(0, x), 0);
      return `Por producto: ${sol(menos)} a favor y ${sol(mas)} en contra; neto ${sol(n.val)}${ant ? ` (${P.periodos[k - 1].corto}: ${sol(ant.val)})` : ''}. Cambios de precio o diferencias entre fuentes del kardex, no pérdida.`;
    }
    if (id === 'sobr') {
      const top = [...rows].sort((a, b) => b.sobr_v - a.sobr_v)[0], par = top && window.__destinoProductoDatos?.parejas(rows, top.cod)?.[0];
      return 'No compensa el faltante.' + (par ? ` Pareja del conteo: ${top.producto} sobró ${sol(top.sobr_v)} y ${par.producto} faltó ${sol(par.falt_v)}.` : '');
    }
    return '';
  }

  // ── El dibujo del flujo neteado ────────────────────────────────────────
  function sankey(W, nodosL, sel, D, simular) {
    const H = 284, TOP = 22, AVAIL = H - TOP - 4, BAR = 10, XO = 146, XD = W - 156, XP = (XO + XD) / 2;
    const ins = nodosL.filter(x => x.lado === 'in'), outs = nodosL.filter(x => x.lado === 'out');
    const gaps = col => col.map((c, i) => i === col.length - 1 ? 0 : (c.g && col[i + 1].g === c.g ? 3 : 12));
    const gi = gaps(ins), go = gaps(outs), suma = a => a.reduce((x, y) => x + y, 0);
    const total = suma(ins.map(x => x.v)) || 1, kk = (AVAIL - Math.max(suma(gi), suma(go))) / total;
    const columna = (ids, gp) => { const alto = suma(ids.map(x => x.v * kk)) + suma(gp); let y = TOP + (AVAIL - alto) / 2; return ids.map((x, i) => { const o = {...x, y, h: x.v * kk}; y += o.h + gp[i]; return o; }); };
    const cin = columna(ins, gi), cout = columna(outs, go), poolH = total * kk, poolY = TOP + (AVAIL - poolH) / 2;
    const elegido = sel && D[sel] ? sel : '', esSel = id => !!elegido && (elegido === id || D[id]?.g === elegido || D[elegido]?.g === id);
    const ladoSel = elegido ? (nodosL.find(x => x.id === elegido)?.lado || D[elegido].lado) : '';
    const banda = (x1, y1, x2, y2, h) => { const xm = (x1 + x2) / 2; return `M${r1(x1)},${r1(y1)} C${r1(xm)},${r1(y1)} ${r1(xm)},${r1(y2)} ${r1(x2)},${r1(y2)} L${r1(x2)},${r1(y2 + h)} C${r1(xm)},${r1(y2 + h)} ${r1(xm)},${r1(y1 + h)} ${r1(x1)},${r1(y1 + h)} Z`; };
    let off = 0, svg = '';
    for (const c of cin) { svg += `<path d="${banda(XO + BAR, c.y, XP, poolY + off, c.h)}" fill="${c.color}" opacity="${esSel(c.id) ? .55 : .22}"/>`; off += c.h; }
    off = 0;
    for (const c of cout) { svg += `<path d="${banda(XP + BAR, poolY + off, XD, c.y, c.h)}" fill="${c.color}" opacity="${esSel(c.id) ? .55 : (ladoSel === 'out' ? .14 : .3)}"/>`; off += c.h; }
    for (const c of [...cin, ...cout]) svg += `<rect x="${c.lado === 'in' ? XO : XD}" y="${r1(c.y)}" width="${BAR}" height="${Math.max(2, r1(c.h))}" rx="2" fill="${c.color}"/>`;
    svg += `<rect x="${XP}" y="${r1(poolY)}" width="${BAR}" height="${r1(poolH)}" rx="2" fill="${D.val.color}" opacity=".7"/>`;
    const ALTO = 30, ubicar = col => { const L = col.map(c => ({c, top: c.y + c.h / 2 - ALTO / 2})); for (let i = 1; i < L.length; i++) L[i].top = Math.max(L[i].top, L[i - 1].top + ALTO + 1); if (L.length && L[L.length - 1].top + ALTO > H - 1) { L[L.length - 1].top = H - 1 - ALTO; for (let i = L.length - 2; i >= 0; i--) L[i].top = Math.min(L[i].top, L[i + 1].top - ALTO - 1); } return L; };
    const rot = [...ubicar(cin), ...ubicar(cout)].map(({c, top}) => {
      const izq = c.lado === 'in', on = esSel(c.id);
      return `<button type="button" class="dstf-rot${elegido === c.id ? ' on' : on ? ' cerca' : ''}" data-f="sel:${c.id}" aria-pressed="${elegido === c.id}" aria-label="${esc(c.label)}, ${esc(sol(c.v))}. Ver detalle" style="top:${r1(Math.max(TOP - 4, top))}px;${izq ? 'left:0;align-items:flex-end;text-align:right' : `left:${XD + 16}px;align-items:flex-start;text-align:left`}"><b>${esc(c.label)}</b><span>${esc(sol(c.v))} · ${fmt(c.v / total * 100, 1)} %</span></button>`;
    }).join('');
    return `<div class="dstf-lienzo" style="height:${H}px"><div class="dstf-col" style="left:0;width:${XO + 10}px;text-align:right">HABÍA Y ENTRÓ</div><div class="dstf-col${simular ? ' on' : ''}" style="left:${XP - 130}px;width:260px;text-align:center">${simular ? 'ESCENARIO · ' : ''}DISPONIBLE · ${esc(sol(total))}</div><div class="dstf-col" style="left:${XD}px;width:156px">A DÓNDE FUE</div><svg width="${W}" height="${H}" aria-hidden="true">${svg}</svg>${rot}</div>`;
  }

  // ── El panel del nodo elegido ──────────────────────────────────────────
  function panel(ctx, id, V, ahorro) {
    const {P, n, k, grupo, D, historia, rows, ant, s} = ctx;
    if (id === 'neg') {
      const t = n.neg, tres = t.tops.reduce((a, r) => a - r.fin_v, 0);
      return `<div class="dstf-tag">AVISO · STOCK EN NEGATIVO</div><div class="dstf-monto"><strong>${esc(sol(t.v))}</strong><span>${t.n} productos cerraron en negativo</span></div><p class="dstf-cod">Se descargó antes de registrar el ingreso: hay que corregirlo en el kardex. En el flujo va neteado contra el stock final.</p>${t.v > 0.5 ? `<p class="dstf-nota">${t.tops.length > 1 ? `${t.tops.length === 3 ? 'Tres' : 'Dos'} productos explican el ${fmt(tres / t.v * 100)} %. ` : ''}Tocar un producto lo abre en la tabla.</p>` : ''}${tops('Los que más pesan', t.tops.map(r => [r.cod, r.producto, -r.fin_v]), t.v, '−')}`;
    }
    const f = s.flujo, d = D[id], v = n[id], comp = (() => {
      if (!ant) return '';
      if (d.stock) return `${P.periodos[k - 1].corto}: ${sol(ant[id])} · ${flecha(cambio(n[id], ant[id]))}`;
      if (id === 'val') return '';
      const hoy = n[id] / n.dias, antes = ant[id] / ant.dias, c = cambio(hoy, antes);
      return `Por día ${sol(hoy)} · ${P.periodos[k - 1].corto} ${sol(antes)} · ${flecha(c)}`;
    })();
    let color = '';
    if (comp && !d.stock && ant) {
      const c = cambio(n[id] / n.dias, ant[id] / ant.dias);
      if (d.tono === 'baja') color = c < 0 ? 'bien' : 'mal';
      if (d.tono === 'sube') color = c > 0 ? 'mal' : 'bien';
    }
    const sim = f.simular && (id === 'falt' || id === 'sinplato') && grupo !== P.operacion;
    const hist = d.stock || id === 'val' ? [] : historia.map(h => ({k: h.k, v: h.n[id] / h.n.dias}));
    const maxH = Math.max(1, ...hist.map(h => h.v));
    const salioHoy = n.plato + n.sinplato, salioSim = V.plato + V.sinplato;
    const lista = id === 'val' ? [] : [...rows].map(r => [r.cod, r.producto, valorDe(r, id, D)]).filter(x => x[2] > 0.5).sort((a, b) => b[2] - a[2]).slice(0, sim || hist.length ? 3 : 5);
    const total = ctx.nodosL.filter(x => x.lado === 'in').reduce((a, x) => a + x.v, 0), mejor = ctx.mejor;
    return `<div class="dstf-tag">${d.lado === 'in' ? 'HABÍA Y ENTRÓ' : 'A DÓNDE FUE'} · ${d.g ? esc(D[d.g].label.toUpperCase()) + ' › ' : ''}${esc(d.label.toUpperCase())}</div>
      <div class="dstf-monto"><strong>${esc(sol(v))}</strong><span>${fmt(Math.abs(v) / Math.max(1, total) * 100, 1)} % de lo disponible</span></div>
      <p class="dstf-cod">${esc(codigo(P, id, k, grupo))}</p>
      ${comp ? `<p class="dstf-comp ${color}">${esc(comp)}</p>` : ''}
      ${sim ? `<div class="dstf-sim"><b>¿Y si el faltante bajara?</b><div>${[['p10', '−10 %'], ['p20', '−20 %'], ['p30', '−30 %'], ...(mejor ? [['mejor', `Al mejor cierre (${P.periodos[mejor.k].corto})`]] : [])].map(([o, t]) => `<button type="button" data-f="sim:${o}" class="${f.sim === o ? 'on' : ''}" aria-pressed="${f.sim === o}">${t}</button>`).join('')}</div>
        <p><span>Ahorro en el cierre</span><b>${esc(sol(ahorro))} · ${esc(sol(ahorro / n.dias))} por día</b></p>
        <p><span>Sin plato, de lo que salió</span><b>${fmt(V.sinplato / Math.max(1, salioSim) * 100, 1)} % (hoy ${fmt(n.sinplato / Math.max(1, salioHoy) * 100, 1)} %)</b></p>
        <p><span>Quedaría en stock</span><b>${esc(sol(V.fin))}</b></p></div>` : ''}
      ${!sim && nota(ctx, id) ? `<p class="dstf-nota">${esc(nota(ctx, id))}</p>` : ''}
      ${hist.length > 1 && !sim ? `<div class="dstf-hist" role="img" aria-label="${esc(d.label)} por día, últimos ${hist.length} cierres">${hist.map((h, i) => `<i title="${esc(P.periodos[h.k].corto)}: ${esc(sol(h.v))} por día" style="height:${r1(h.v / maxH * 26 + 2)}px;background:${i === hist.length - 1 ? d.color : 'var(--dstf-gris)'}"></i>`).join('')}</div><div class="dstf-hist-pie"><span>${esc(P.periodos[hist[0].k].corto)}</span><span>por día, ${hist.length} cierres</span><span>${esc(P.periodos[k].corto)}</span></div>` : ''}
      ${d.partes ? `<div class="dstf-partes">${d.partes.map(p => `<button type="button" data-f="parte:${p}"><i style="background:${D[p].color}"></i>${esc(D[p].label)} ${esc(fmt(n[p]))}</button>`).join('')}</div>` : ''}
      ${tops('Productos que más pesan', lista, Math.abs(v))}`;
  }
  const tops = (titulo, lista, total, signo = '') => lista.length ? `<div class="dstf-tops"><b>${esc(titulo)}</b>${lista.map(([cod, nombre, v]) => `<button type="button" data-f="prod:${esc(cod)}" title="Abrir en la tabla"><span>${esc(nombre)}</span><span>${signo}${esc(sol(v))}</span><span>${fmt(v / Math.max(1, total) * 100)} %</span></button>`).join('')}</div>` : '';

  // ── «Cómo se calcula» ──────────────────────────────────────────────────
  function aportes(r) {
    // El balance bruto de un producto, como lo dibujaba el Sankey anterior:
    // cada movimiento de su lado y lo negativo del otro.
    const ins = {}, outs = {}, poner = (o, c, v) => { o[c] = (o[c] || 0) + v; };
    const par = (c, lado, v) => { v = Number(v) || 0; if (Math.abs(v) < 1e-9) return; if (v > 0) poner(lado === 'in' ? ins : outs, c, v); else poner(lado === 'in' ? outs : ins, 'rev', -v); };
    if ((r.ini_v || 0) < 0) poner(outs, 'ini_neg', -r.ini_v); else poner(ins, 'ini', r.ini_v || 0);
    par('compra', 'in', r.compra_v);
    for (const t of ['90', '94', '96']) { par('prod' + t, 'in', r['ing_' + t + '_v']); par('prep', 'out', r['prep_' + t + '_v']); }
    for (const c of ['venta', 'cort', 'evvi', 'baja', 'otras']) par(c, 'out', r[c + '_v']);
    par('sobr', 'in', r.sobr_v); par('falt', 'out', r.falt_v);
    par('otros', 'in', r.otros_ing_v); par('otros', 'out', r.otros_sal_v);
    if ((r.fin_v || 0) < 0) poner(ins, 'fin_neg', -r.fin_v); else poner(outs, 'fin', r.fin_v || 0);
    const dif = Object.values(ins).reduce((a, x) => a + x, 0) - Object.values(outs).reduce((a, x) => a + x, 0);
    if (dif < 0) poner(ins, 'val', -dif); else if (dif > 0) poner(outs, 'val', dif);
    return {ins, outs};
  }
  function bruto(rows) {
    const t = {ins: {}, outs: {}, nIni: 0, nFin: 0};
    for (const r of rows) {
      const a = aportes(r);
      for (const [c, v] of Object.entries(a.ins)) t.ins[c] = (t.ins[c] || 0) + v;
      for (const [c, v] of Object.entries(a.outs)) t.outs[c] = (t.outs[c] || 0) + v;
      if ((r.ini_v || 0) < -0.5) t.nIni++; if ((r.fin_v || 0) < -0.5) t.nFin++;
    }
    t.entrada = Object.values(t.ins).reduce((a, x) => a + x, 0);
    return t;
  }
  function calculo(ctx) {
    const {P, n, k, rows, nodosL} = ctx, b = bruto(rows), I = b.ins, neto = nodosL.filter(x => x.lado === 'in').reduce((a, x) => a + x.v, 0);
    const prod = (I.prod90 || 0) + (I.prod94 || 0) + (I.prod96 || 0), neg = (b.outs.ini_neg || 0) + (I.fin_neg || 0);
    const val = (I.val || 0) - Math.max(0, n.val), resto = b.entrada - prod - neg - val - neto;
    const fila = (t, v, fuerte) => `<span${fuerte ? ' class="f"' : ''}>${t}</span><b class="${fuerte ? 'f' : ''}">${fuerte ? '' : '−'}${fmt(Math.abs(v))}</b>`;
    const op = P.reloj === 'operativo', pu = puente(P, k), b0 = P.borde[k] || [0, 0, 0], p = P.periodos[k];
    const porDia = (x, xa) => x && xa ? flecha(cambio(x.sinplato / x.dias, xa.sinplato / xa.dias)) : '—';
    const platoDia = (x, xa) => x && xa ? flecha(cambio(x.plato / x.dias, xa.plato / xa.dias)) : '—';
    const tarde = (p.cortes_op || []).filter(c => p.t1_op && c[1].slice(0, 10) !== p.t1_op.slice(0, 10));
    const filasP = pu ? [
      ['Período', fmt(pu.o.dias, 1) + ' días', p.t1_op ? `Cada área de su conteo al siguiente; termina en el conteo de las áreas con stock (la mayoría, ${hora(p.t1_op)}${tarde.length ? '; ' + tarde.slice(0, 2).map(c => `${c[0]}, ${hora(c[1])}`).join('; ') : ''}). Las que contaron sin stock toman ese corte.` : ''],
      ['Compras', fmt(pu.o.compra), 'Registradas en el kardex antes del conteo de su área; lo registrado después es del cierre siguiente.'],
      ['A un plato', fmt(pu.o.plato), b0[0] > 0.5 || b0[1] > 0.5 ? `+${fmt(b0[0])} vendidos antes del conteo y descontados después o nunca (${fmt(b0[2])} nunca); −${fmt(b0[1])} que eran del cierre anterior.` : 'Ninguna venta cruzó el conteo.'],
      ['Faltante', fmt(pu.o.falt), b0[0] > 0.5 || b0[1] > 0.5 ? 'Sin esas ventas: no eran pérdida.' : 'Lo que el conteo encontró de menos.'],
      ['Quedó en stock', fmt(pu.o.fin), 'Foto justo después del conteo de cada área, sin lo registrado después.'],
      ['Sin plato por día vs anterior', porDia(pu.o, pu.oa), pu.oa ? `Cierre anterior: ${fmt(pu.oa.dias, 1)} días. Los períodos no miden lo mismo: por eso, por día.` : ''],
      ['A un plato por día vs anterior', platoDia(pu.o, pu.oa), '']
    ] : [];
    const FECHAS = [
      ['Compras', 'Registro en el kardex, cortado en el conteo de su área'],
      ['Venta, cortesías, eventos', 'Corrida del descargo; la hora del pedido si cruza un conteo'],
      ['Producción', 'Proceso en el kardex, cortado en el conteo'],
      ['Bajas y notas', 'Fecha de proceso, cortada en el conteo'],
      ['Stock', 'Kardex justo después del conteo de cada área'],
      ['Traslados 97 / 99', 'Fuera, salvo áreas contadas en momentos distintos']
    ];
    return `<div class="dstf-calc">
      <section class="dstf-caja"><div class="dstf-tag">DEL BRUTO AL NETO</div>
        <p>Por qué el balance producto por producto suma ${esc(sol(b.entrada))} y el flujo, ${esc(sol(neto))}.</p>
        <div class="dstf-con"><span>Entradas producto por producto</span><b>${fmt(b.entrada)}</b>
        ${fila(`Producción interna: sale como insumo y vuelve como corte (porcionamientos ${fmt(I.prod96 || 0)} · órdenes ${fmt((I.prod94 || 0) + (I.prod90 || 0))})`, prod)}
        ${fila(`Stock negativo, neteado en su punta (${b.nIni} productos al inicio, ${b.nFin} al final)`, neg)}
        ${fila('Valorización a favor y en contra que se compensan', val)}
        ${Math.abs(resto) > 0.5 ? fila('Reversos y otros movimientos (notas o compras al revés, tipos no clasificados)', resto) : ''}
        ${fila('Disponible neto', neto, true)}</div>
        <p class="dstf-nota">Los traslados entre áreas (97 transferencias, 99 requerimientos) se anulan en el restaurante entero y no entran.</p></section>
      <section class="dstf-caja borde"><div class="dstf-tag">DE CONTEO A CONTEO · ${esc(p.nombre.toUpperCase())}</div>
        ${pu ? `<div class="dstf-puente uno"><b>Concepto</b><b class="n">S/</b><b>Por qué</b>${filasP.map(x => `<span>${esc(x[0])}</span><span class="n f">${esc(x[1])}</span><span class="pq">${esc(x[2])}</span>`).join('')}</div><p class="dstf-nota">Alimentos y bebidas del restaurante entero${P.areas_familias ? ', sin el filtro de familias' : ''}.</p>` : '<p class="dstf-nota">Sin el resumen de este cierre.</p>'}</section>
      <section class="dstf-caja"><div class="dstf-tag">QUÉ FECHA USA CADA MOVIMIENTO</div>
        <div class="dstf-fechas uno"><b>Movimiento</b><b>Fecha que usa</b>${FECHAS.map(x => `<span class="f">${esc(x[0])}</span><span>${esc(x[1])}</span>`).join('')}</div>
        <p class="dstf-nota">El Excel lleva la hoja «Flujo»: cada concepto con su código del kardex, bruto y neto.</p>
        <p class="dstf-nota">«Por área»: origen y destino de cada requerimiento y transferencia, de la fila «transferencias» del Sheet.</p></section></div>`;
  }

  // ── Montaje ────────────────────────────────────────────────────────────
  function montar(el, opts) {
    const abort = new AbortController();
    let ctx = null, ancho = 0, movil = false;
    const api = {cleanup: () => { abort.abort(); obs?.disconnect(); }, ctx: () => ctx, hojaFlujo, hojasArea: () => ctx ? DESTINO_AREAS.hojas(ctx) : []};
    function preparar(c) {
      const {P, B, s, k, grupo} = c, D = definiciones(P, grupo);
      const n = cuenta(P, c.rows, k, grupo, c.completo);
      const ant = k > 0 ? cuenta(P, c.alcance(k - 1), k - 1, grupo, c.completo) : null;
      const desde = Math.max(0, k - 11), historia = [];
      for (let j = desde; j <= k; j++) historia.push({k: j, n: j === k ? n : j === k - 1 ? ant : cuenta(P, c.alcance(j), j, grupo, c.completo)});
      const previos = historia.filter(h => h.k < k && h.n.sinplato > 0.5);
      const mejor = previos.length ? previos.map(h => ({k: h.k, v: h.n.sinplato / h.n.dias})).sort((a, b) => a.v - b.v)[0] : null;
      return {...c, D, n, ant, historia, mejor, B, s};
    }
    function render(otra = false) {
      if (!ctx) return;
      const {P, n, grupo, D} = ctx, f = ctx.s.flujo, alim = grupo !== P.operacion;
      // El escenario: el faltante que no se pierde queda en stock.
      const V = {...n};
      let ahorro = 0;
      const simAplica = alim && f.simular && (f.sel === 'falt' || f.sel === 'sinplato' || !f.sel);
      if (simAplica) {
        ahorro = f.sim === 'mejor' && ctx.mejor ? Math.max(0, Math.min(n.falt, (n.sinplato / n.dias - ctx.mejor.v) * n.dias)) : n.falt * Number(String(f.sim).slice(1) || 0) / 100;
        V.falt -= ahorro; V.sinplato -= ahorro; V.fin += ahorro;
      }
      ctx.nodosL = nodos(P, n, grupo, f.modo);
      const nodosV = nodos(P, V, grupo, f.modo);
      const sel = f.sel && (D[f.sel] || f.sel === 'neg') ? f.sel : (alim ? 'sinplato' : 'falt');
      // En el celular el flujo no se abre: la franja y su lista plegable bastan.
      movil = !!el.ownerDocument.defaultView?.matchMedia('(max-width: 900px)').matches;
      el.dataset.abierto = f.abierto && !movil ? '1' : '0';
      if (!f.abierto || movil) { el.innerHTML = franja(ctx); return; }
      ancho = medir();
      const cab = `<div class="dstf-cab"><div class="dstf-grupo"><b>Destino del inventario</b>
        <div class="dstf-seg" role="group" aria-label="Ver">${['restaurante', 'area'].map(v => `<button type="button" data-f="vista:${v}" class="${f.vista === v ? 'on' : ''}" aria-pressed="${f.vista === v}">${v === 'area' ? 'Por área' : 'Restaurante'}</button>`).join('')}</div>
        ${f.vista === 'restaurante' ? `<div class="dstf-botones" role="group" aria-label="Qué ver">${[['flujo', 'Flujo'], ['calculo', 'Cómo se calcula']].map(([v, t]) => `<button type="button" data-f="que:${v}" class="${f.que === v ? 'on' : ''}" aria-pressed="${f.que === v}">${t}</button>`).join('')}</div>` : DESTINO_AREAS.botones(ctx)}</div>
        <div class="dstf-grupo">${f.vista === 'restaurante' && f.que === 'flujo' ? `${alim ? `<div class="dstf-botones" role="group" aria-label="Detalle del flujo">${[['resumen', 'Resumen'], ['desglose', 'Desglose']].map(([v, t]) => `<button type="button" data-f="modo:${v}" class="${f.modo === v ? 'on' : ''}" aria-pressed="${f.modo === v}">${t}</button>`).join('')}</div><button type="button" data-f="simular" class="${f.simular ? 'on' : ''}" aria-pressed="${f.simular}">Simular</button>` : ''}` : ''}
        ${f.vista === 'area' ? DESTINO_AREAS.aviso(ctx) : negBoton(ctx, sel === 'neg')}<button type="button" class="dstf-ocultar" data-f="cerrar">Ocultar flujo ▴</button></div></div>`;
      let cuerpo;
      if (f.vista === 'area') cuerpo = DESTINO_AREAS.html(ctx, ancho);
      else if (f.que === 'calculo') cuerpo = calculo(ctx);
      else cuerpo = `<div class="dstf-abierto"><div class="dstf-izq">${sankey(ancho, nodosV, f.sel, D, simAplica)}
        ${alim && tira(ctx) ? `<div class="dstf-tira"><span>${esc(tira(ctx))}</span><button type="button" data-f="tira">Cómo se calcula</button></div>` : ''}
        ${n.prep > 0.5 ? `<p class="dstf-prod">No se dibuja la producción interna: ${esc(sol(n.prep))} salieron a porcionamientos y órdenes y volvieron como cortes. No es consumo.</p>` : ''}</div>
        <aside class="dstf-panel" aria-label="Detalle del concepto elegido">${panel(ctx, sel, V, ahorro)}</aside></div>`;
      el.innerHTML = cab + cuerpo;
      // El dibujo va al ancho real de su columna, no a un viewBox fijo: una
      // segunda pasada si la columna salió de otro ancho, nunca más.
      if (!otra && Math.abs(medir() - ancho) > 8) render(true);
    }
    // Menos de 560 px no se dibuja: la columna recorta (en el celular el flujo no se abre).
    const medir = () => Math.max(560, Math.floor(el.querySelector('.dstf-izq')?.clientWidth || el.clientWidth * 0.66 || 790));
    function negBoton(c, on) {
      const t = c.n.neg;
      return c.grupo !== c.P.operacion && t.n ? `<button type="button" class="dstf-neg${on ? ' on' : ''}" data-f="sel:neg" aria-pressed="${on}"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M12 3 2 21h20z"/><path d="M12 10v5M12 18h.01"/></svg>${t.n} en negativo · ${esc(sol(t.v))}</button>` : '';
    }
    function tira(c) {
      const {P, k} = c, b = P.borde[k] || [0, 0, 0];
      if (b[0] <= 0.5 && b[1] <= 0.5) return '';
      return `De conteo a conteo: ${sol(b[0])} vendidos antes del conteo y descontados después pasan de faltante a plato${b[1] > 0.5 ? `; ${sol(b[1])} eran del cierre anterior` : ''}.`;
    }
    function franja(c) {
      const {P, n, grupo, D, ant, s} = c, f = s.flujo, alim = grupo !== P.operacion;
      const partes = nodos(P, n, grupo, 'desglose').filter(x => x.lado === 'out'), grupos = nodos(P, n, grupo, 'resumen').filter(x => x.lado === 'out');
      const T = partes.reduce((a, x) => a + x.v, 0) || 1, sel = f.sel, ancho = v => (v / T * 100).toFixed(3) + '%';
      const grupoDe = id => D[id]?.g || id, prin = alim ? 'sinplato' : 'falt';
      const hoy = n[prin] / n.dias, antes = ant ? ant[prin] / ant.dias : null, c0 = cambio(hoy, antes);
      const compTxt = ant ? `${alim ? 'Sin plato' : 'Consumido'} por día ${flecha(c0)} vs ${P.periodos[c.k - 1].corto} · ${fmt(n.dias, 1)} y ${fmt(ant.dias, 1)} días` : '';
      const tono = c0 == null ? '' : c0 < 0 ? 'bien' : 'mal';
      const movil = grupos.map(g => {
        const sub = g.partes ? g.partes.map(p => partes.find(x => x.id === p)).filter(Boolean) : [];
        const lista = [...c.rows].map(r => [r.cod, r.producto, valorDe(r, g.id, D)]).filter(x => x[2] > 0.5).sort((a, b) => b[2] - a[2]).slice(0, 3);
        const ab = f.movil === g.id;
        return `<div class="dstf-acc"><button type="button" data-f="acc:${g.id}" aria-expanded="${ab}"><i style="background:${g.color}"></i><span><b>${esc(g.label)}</b><small>${esc(sol(g.v))} · ${fmt(g.v / T * 100, 1)} %</small></span><span class="dstf-chev">${ab ? '▴' : '▾'}</span></button>${ab ? `<div class="dstf-acc-cuerpo">${sub.map(p => `<p><span><i style="background:${p.color}"></i>${esc(p.label)}</span><span>${esc(sol(p.v))}</span></p>`).join('')}${nota(c, g.id) ? `<p class="dstf-nota">${esc(nota(c, g.id))}</p>` : ''}${tops('Más pesan', lista, g.v)}</div>` : ''}</div>`;
      }).join('');
      return `<div class="dstf-franja"><div class="dstf-resumen"><h3>Destino del inventario</h3><p>${esc(sol(T))} que había o entró</p>${compTxt ? `<p class="dstf-comp ${tono}">${esc(compTxt)}</p>` : ''}${negBoton(c, sel === 'neg')}</div>
        <div class="dstf-barra"><div class="dstf-grupos">${grupos.map(g => `<button type="button" data-f="sel:${g.id}" title="${esc(g.label)}: ${esc(sol(g.v))} (${fmt(g.v / T * 100, 1)} %). Filtrar la tabla" style="width:${ancho(g.v)};opacity:${!sel || sel === g.id || grupoDe(sel) === g.id ? 1 : .45}" class="${sel === g.id ? 'on' : ''}" aria-pressed="${sel === g.id}"><span>${esc(g.label)} · ${fmt(g.v / T * 100, 1)} %</span><i style="background:${g.color}"></i></button>`).join('')}</div>
        <div class="dstf-segs">${partes.map(p => `<button type="button" data-f="sel:${p.id}" title="${esc(p.label)}: ${esc(sol(p.v))} (${fmt(p.v / T * 100, 1)} %). Filtrar la tabla" aria-label="${esc(p.label)}: ${esc(sol(p.v))}" aria-pressed="${sel === p.id}" class="${sel === p.id ? 'on' : ''}" style="width:${ancho(p.v)};background:${p.color};opacity:${!sel || sel === p.id || sel === grupoDe(p.id) ? 1 : .35}">${p.v / T > 0.09 ? esc(p.label) : ''}</button>`).join('')}</div>
        <div class="dstf-ley">${partes.map(p => `<button type="button" data-f="sel:${p.id}" class="${sel === p.id ? 'on' : ''}"><i style="background:${p.color}"></i>${esc(p.label)} ${esc(fmt(p.v))}</button>`).join('')}</div></div>
        <button type="button" class="dstf-ver" data-f="abrir">Ver flujo ▾</button></div>
        <div class="dstf-movil">${movil}<p class="dstf-nota">${esc(P.reloj === 'operativo' ? 'Cada área cortada en la hora de su conteo.' : 'Cada movimiento en el día en que movió el kardex.')} La producción interna (${esc(sol(n.prep))}) no se cuenta.</p></div>`;
    }
    function hojaFlujo() {
      if (!ctx) return [];
      const {P, k, rows, n} = ctx, b = bruto(rows), fila = [];
      const con = (t, c, lado, br, ne) => fila.push([t, c, lado, br, ne]);
      const neto = (ctx.nodosL || nodos(P, n, ctx.grupo, 'resumen')).filter(x => x.lado === 'in').reduce((a, x) => a + x.v, 0);
      con('Total que había o entró', '', 'Origen', b.entrada, neto);
      con('Stock inicial', 'Foto del kardex', 'Origen', b.ins.ini || 0, n.ini);
      con('Compras netas', '< 90', 'Origen', b.ins.compra || 0, n.compra);
      con('Producción interna (ingreso)', '90 · 94 · 96', 'Origen', (b.ins.prod90 || 0) + (b.ins.prod94 || 0) + (b.ins.prod96 || 0), 0);
      con('Sobrante al contar', '93', 'Origen', b.ins.sobr || 0, n.sobr);
      con('Valorización', 'Diferencia del balance', n.val >= 0 ? 'Origen' : 'Destino', (b.ins.val || 0) - (b.outs.val || 0), n.val);
      con('Venta (incluye combos)', '95', 'Destino', b.outs.venta || 0, n.venta);
      con('Cortesías', '95', 'Destino', b.outs.cort || 0, n.cort);
      con('Eventos y venta interna', '95', 'Destino', b.outs.evvi || 0, n.evvi);
      con('A un plato', '95', 'Destino', (b.outs.venta || 0) + (b.outs.cort || 0) + (b.outs.evvi || 0), n.plato);
      con('Producción interna (insumo)', '90 · 94 · 96', 'Destino', b.outs.prep || 0, 0);
      con('Faltante', '93', 'Destino', b.outs.falt || 0, n.falt);
      con('Bajas', '98 · Bajas', 'Destino', b.outs.baja || 0, n.baja);
      con('Otras notas', '91 · 92 · 98', 'Destino', b.outs.otras || 0, n.otras);
      con('Quedó en stock', 'Foto del kardex', 'Destino', b.outs.fin || 0, n.fin);
      con('Stock negativo (neteado)', 'Foto del kardex', 'Ambos', (b.outs.ini_neg || 0) + (b.ins.fin_neg || 0), 0);
      con('Ventas que cruzan el conteo', 'Paloteo × descargos', 'Faltante → plato', (P.borde[k] || [0])[0], n.borde);
      return [{nombre: 'Flujo', cabeza: ['Concepto', 'Código del kardex', 'Lado', 'Bruto S/', 'Neto S/'], filas: fila, decimales: 6}];
    }
    el.addEventListener('click', e => {
      const b = e.composedPath().find(x => x?.dataset?.f);
      if (!b || !el.contains(b) || !ctx) return;
      const [a, v] = [b.dataset.f.split(':')[0], b.dataset.f.slice(b.dataset.f.indexOf(':') + 1)], f = ctx.s.flujo;
      let tabla = false;
      if (a === 'abrir' || a === 'cerrar') f.abierto = a === 'abrir';
      else if (a === 'sel' || a === 'parte') { f.sel = f.sel === v && a === 'sel' ? '' : v; if (a === 'parte') f.modo = 'desglose'; tabla = true; }
      else if (a === 'vista') { f.vista = v; f.presentar = false; }
      else if (a === 'que') f.que = v;
      else if (a === 'modo') f.modo = v;
      else if (a === 'simular') { f.simular = !f.simular; if (f.simular && !['falt', 'sinplato'].includes(f.sel)) { f.sel = 'falt'; tabla = true; } }
      else if (a === 'sim') f.sim = v;
      else if (a === 'acc') f.movil = f.movil === v ? '' : v;
      else if (a === 'tira') f.que = 'calculo';
      else if (a === 'prod') { opts.producto(v); return; }
      else if (DESTINO_AREAS.accion(ctx, a, v)) { /* el mapa por área */ }
      else return;
      if (tabla) opts.cambiar(true); else { render(); opts.cambiar(false); }
    }, {signal: abort.signal});
    el.addEventListener('keydown', e => {
      const b = e.composedPath().find(x => x?.dataset?.f);
      if (b && b.tagName !== 'BUTTON' && ['Enter', ' '].includes(e.key)) { e.preventDefault(); b.dispatchEvent(new MouseEvent('click', {bubbles: true, composed: true})); }
    }, {signal: abort.signal});
    DESTINO_AREAS.tooltip(el, abort.signal);
    const obs = typeof ResizeObserver === 'function' ? new ResizeObserver(() => {
      const ahora = !!el.ownerDocument.defaultView?.matchMedia('(max-width: 900px)').matches;
      if (ahora !== movil || el.querySelector('.dstf-izq') && Math.abs(medir() - ancho) > 8) render();
    }) : null;
    obs?.observe(el);
    api.actualizar = c => { ctx = preparar(c); render(); };
    api.render = render;
    return api;
  }
  return {estado, montar, cuenta, nodos, definiciones, predicado, valorProducto, bruto, puente, codigo};
})();
window.__destinoFlujo = DESTINO_FLUJO;
