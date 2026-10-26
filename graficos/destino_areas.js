/* «Por área» del flujo de «En qué se fue cada producto» (regla #743): el
   balance de cada área alrededor del Almacén Central, con las flechas de
   requerimientos (99) y transferencias (97) de `transferencias.parquet`,
   las capas que se muestran u ocultan, la matriz de origen y destino y
   «Presentar», que lo cuenta en seis pasos. Los números son los de
   `sin_plato.por_area`; acá sólo se acomodan. */
const DESTINO_AREAS = (() => {
  const fmt = (x, d = 0) => Number(x || 0).toLocaleString('es-PE', {maximumFractionDigits: d});
  const sol = x => (x < -0.005 ? '−' : '') + 'S/ ' + fmt(Math.abs(x));
  const firma = x => (x < -0.005 ? '−' : x > 0.005 ? '+' : '') + fmt(Math.abs(x));
  const esc = x => String(x ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const r1 = x => Math.round(x * 10) / 10;
  const CAPAS = [['c', 'Compras', 'compra'], ['99', 'Requerimientos', 'req'], ['97', 'Transferencias', 'tr'],
    ['prod', 'Producción', 'prod'], ['95', 'Ventas', 'vende'], ['98', 'Notas', 'notas'], ['93', 'Ajustes', 'ajuste']];
  const TIPO = {'99': 'Requerimientos', '97': 'Transferencias', c: 'Compras'};
  const QUE = {'99': 'Requerimiento: el área pide y el Almacén entrega.', '97': 'Transferencia: un área le pasa mercadería a otra.', c: 'Compras: lo que entró de los proveedores.'};
  const CHIP = {'95': ['VENDIÓ (95)', 'Lo que el POS descontó por ventas desde esta área.'],
    prod: ['PORCIONÓ O PRODUJO (94 · 96)', 'Lo que salió de un porcionamiento o una orden de producción en esta área.'],
    '98': ['NOTAS DE SALIDA (91 · 92 · 98)', 'Comida de personal, uso del área, merma y bajas.'],
    '93': ['AJUSTE DEL CONTEO (93)', 'La diferencia entre lo contado y lo que decía el sistema.']};

  const datos = ctx => (ctx.P.areas?.[ctx.grupo] || [])[ctx.k] || null;
  const vector = (P, arr) => Object.fromEntries(P.cols_area.map((c, i) => [c, arr?.[i] || 0]));
  const sumar = (P, arrs) => P.cols_area.map((_, i) => arrs.reduce((a, x) => a + (x[i] || 0), 0));
  const importancia = v => Math.abs(v.compra) + v.req_in + v.req_out + v.tr_in + v.tr_out + v.prod_in + v.prod_out
    + Math.abs(v.venta) + Math.abs(v.notas) + v.aj_pos + v.aj_neg + 0.25 * (Math.abs(v.ini) + Math.abs(v.fin));

  /* Dónde va cada caja: el Almacén al medio, arriba quien más le devuelve
     (Producción), a la derecha quien más le pide (Cocina), en la esquina la
     siguiente y abajo el resto; con más de seis abajo, la última junta a
     las demás. Las coordenadas son de un lienzo de 790 × 300. */
  function disposicion(ctx) {
    const A = datos(ctx), P = ctx.P;
    if (!A || !Object.keys(A.areas || {}).length) return null;
    const nom = c => P.nombres_area[c] || 'Área ' + c;
    const vs = Object.entries(A.areas).map(([c, arr]) => ({c, arr, v: vector(P, arr)}));
    const alm = vs.find(x => x.c === '0') || [...vs].sort((a, b) => b.v.compra - a.v.compra)[0];
    const flujo = (o, d) => (A.flechas || []).filter(f => String(f[1]) === o && String(f[2]) === d).reduce((a, f) => a + f[3], 0);
    let resto = vs.filter(x => x !== alm && importancia(x.v) > 0.5);
    const mayor = (xs, f) => xs.reduce((m, x) => f(x) > (m ? f(m) : 0.5) ? x : m, null);
    const arriba = mayor(resto, x => flujo(x.c, alm.c)); resto = resto.filter(x => x !== arriba);
    const derecha = mayor(resto, x => flujo(alm.c, x.c)); resto = resto.filter(x => x !== derecha);
    resto.sort((a, b) => importancia(b.v) - importancia(a.v));
    const esquina = resto.shift() || null;
    let abajo = resto;
    const N = {prov: {id: 'prov', nombre: 'PROVEEDORES', x: 0, y: 118, w: 104, h: 62, miembros: []}};
    const caja = (x, id, geo) => { N[id] = {id, nombre: nom(x.c).toUpperCase(), miembros: [x.c], v: x.v, arr: x.arr, ...geo}; };
    caja(alm, alm.c, {x: 174, y: 92, w: 168, h: 116});
    if (arriba) caja(arriba, arriba.c, {x: 174, y: 0, w: 168, h: 56});
    if (derecha) caja(derecha, derecha.c, {x: 432, y: 76, w: 186, h: 120});
    if (esquina) caja(esquina, esquina.c, {x: 648, y: 0, w: 142, h: 66});
    let otras = [];
    if (abajo.length > 6) { otras = abajo.slice(5); abajo = abajo.slice(0, 5); }
    const n = abajo.length + (otras.length ? 1 : 0), w = n ? (670 - (n - 1) * 8) / n : 0;
    abajo.forEach((x, i) => caja(x, x.c, {x: 120 + i * (w + 8), y: 244, w, h: 72, fila: 'abajo'}));
    if (otras.length) {
      const arr = sumar(P, otras.map(x => x.arr));
      N.otr = {id: 'otr', nombre: `OTRAS ${otras.length} ÁREAS`, miembros: otras.map(x => x.c), v: vector(P, arr), arr,
        x: 120 + abajo.length * (w + 8), y: 244, w, h: 72, fila: 'abajo', ayuda: otras.map(x => nom(x.c)).join(', ')};
    }
    // Las áreas sin movimiento (sólo stock) no se dibujan. `orden` es el de
    // lectura: un objeto pone primero las claves numéricas (las áreas).
    const de = {}, orden = [alm.c, arriba?.c, derecha?.c, esquina?.c, ...abajo.map(x => x.c), otras.length ? 'otr' : null, 'prov'].filter(Boolean);
    for (const nd of Object.values(N)) for (const c of nd.miembros) de[c] = nd.id;
    return {N, de, orden, alm: alm.c, arriba: arriba?.c, nom};
  }

  function flechas(ctx, L) {
    const A = datos(ctx), m = new Map();
    for (const f of A.flechas || []) {
      const o = L.de[String(f[1])], d = L.de[String(f[2])];
      if (!o || !d || o === d) continue;
      const key = f[0] + '|' + o + '|' + d;
      if (!m.has(key)) m.set(key, {k: key, tipo: f[0], o, d, v: 0, lineas: 0, docs: 0, tops: []});
      const x = m.get(key); x.v += f[3]; x.lineas += f[4]; x.docs += f[5]; x.tops.push(...f[6]);
    }
    for (const x of m.values()) {
      const t = new Map();
      for (const [nombre, v] of x.tops) t.set(nombre, (t.get(nombre) || 0) + v);
      x.tops = [...t].sort((a, b) => b[1] - a[1]).slice(0, 5);
    }
    const lista = [...m.values()];
    const compra = L.N[L.alm]?.v?.compra || 0;
    if (Math.abs(compra) > 0.5) lista.push({k: 'c|prov|' + L.alm, tipo: 'c', o: 'prov', d: L.alm, v: compra, lineas: 0, docs: 0, tops: []});
    return lista;
  }

  function detalleChip(ctx, L, id, clave) {
    const A = datos(ctx), nd = L.N[id], partes = nd.miembros.map(c => (A.detalle?.[c] || {})[clave]).filter(Boolean);
    if (!partes.length) return null;
    const t = new Map();
    for (const p of partes) for (const [nombre, v] of p[2]) t.set(nombre, (t.get(nombre) || 0) + v);
    return [partes.reduce((a, p) => a + p[0], 0), partes.reduce((a, p) => a + p[1], 0), [...t].sort((a, b) => b[1] - a[1]).slice(0, 4)];
  }

  function notas(L, id) {
    const v = L.N[id]?.v;
    if (!v) return '';
    const t = [];
    if (id === L.alm && v.venta < 0.5) t.push('El POS no descuenta ventas aquí: todo lo que sale va con requerimiento, transferencia o nota. Lo que falta al contar salió sin documento.');
    if (v.venta > 0.5 && v.compra + v.req_in + v.tr_in + v.prod_in < 0.5) t.push(`No recibe nada, pero el POS descuenta ventas aquí (${sol(v.venta)}): revisar desde qué área se descarga el plato.`);
    if (v.prod_in > 0.5 && v.tr_out > v.prod_in * 0.5) t.push(`Recibe piezas enteras, las porciona o produce y devuelve ${sol(v.tr_out)} a otras áreas.`);
    if (v.aj_pos > 1000 && v.aj_neg > 1000 && Math.min(v.aj_pos, v.aj_neg) / Math.max(v.aj_pos, v.aj_neg) > 0.5) t.push(`Faltó ${fmt(v.aj_neg)} y sobró ${fmt(v.aj_pos)}: suelen compensarse entre productos parecidos. Ver Ajuste › Análisis de diferencias.`);
    if (v.fin < -0.5) t.push(`Cierra en negativo (${firma(v.fin)}): se descontó antes de registrar lo que llegó.`);
    else if (v.fin_neg < -500) t.push(`Tiene productos en negativo (${firma(v.fin_neg)}): se descontaron antes de registrar lo que llegó.`);
    if (Math.abs(v.val) > 1000) t.push(`La diferencia del balance (${firma(v.val)}) no la explica ningún movimiento.`);
    return t.slice(0, 2).join(' ');
  }

  function pasos(ctx, L, fl) {
    const N = L.N, nom = id => N[id] ? N[id].nombre.charAt(0) + N[id].nombre.slice(1).toLowerCase() : '';
    const req = fl.filter(f => f.tipo === '99' && f.o === L.alm).sort((a, b) => b.v - a.v), tReq = req.reduce((a, f) => a + f.v, 0);
    const areas = Object.values(N).filter(n => n.v), venta = areas.filter(n => n.v.venta > 0.5).sort((a, b) => b.v.venta - a.v.venta);
    const tVenta = venta.reduce((a, n) => a + n.v.venta, 0), conNotas = areas.filter(n => n.v.notas > 0.5).sort((a, b) => b.v.notas - a.v.notas);
    const A = datos(ctx), cmp = A.compensa || {}, top4 = (xs, f) => xs.slice(0, 4).map(x => `${nom(x.d || x.id)} ${fmt(f(x))}`).join(' · ');
    const pr = L.arriba, dePr = fl.filter(f => f.o === pr && f.d === L.alm).reduce((a, f) => a + f.v, 0), aPr = fl.filter(f => f.o === L.alm && f.d === pr).reduce((a, f) => a + f.v, 0);
    const negs = areas.filter(n => n.v.fin < -0.5).sort((a, b) => a.v.fin - b.v.fin);
    const todas = Object.keys(N);
    return [
      {capas: ['c'], foco: ['prov', L.alm], titulo: 'Llegan las compras', monto: sol(N[L.alm]?.v.compra || 0), texto: 'Entran al Almacén Central con facturas, guías y notas de crédito.'},
      {capas: ['c', '99'], foco: [L.alm, ...req.map(f => f.d)], titulo: 'El Almacén reparte por requerimiento', monto: sol(tReq),
        texto: req.length ? top4(req, f => f.v) + (req.length > 4 ? `, y ${sol(req.slice(4).reduce((a, f) => a + f.v, 0))} a las demás áreas.` : '.') : 'Este cierre no hubo requerimientos.'},
      {capas: ['c', '99', '97', 'prod'], foco: [pr, L.alm].filter(Boolean), titulo: pr ? `${nom(pr)} porciona y devuelve` : 'La producción',
        monto: sol(pr ? N[pr].v.prod_in : 0), texto: pr ? `Recibe ${sol(aPr)} en piezas enteras, las porciona o produce y devuelve ${sol(dePr)} al Almacén, que las reparte otra vez.` : 'Ninguna área le devuelve mercadería al Almacén.'},
      {capas: ['c', '99', '97', 'prod', '95'], foco: venta.map(n => n.id), titulo: 'Las áreas venden', monto: sol(tVenta), texto: venta.length ? top4(venta, n => n.v.venta) + '.' : 'Sin descargo de ventas en este cierre.'},
      {capas: ['c', '99', '97', 'prod', '95', '98', '93'], foco: [...new Set([...conNotas.map(n => n.id), ...areas.filter(n => n.v.aj_pos + n.v.aj_neg > 0.5).map(n => n.id)])],
        titulo: 'Notas y conteo', monto: sol(conNotas.reduce((a, n) => a + n.v.notas, 0)) + ' en notas',
        texto: `${conNotas.length ? `Mayor: ${nom(conNotas[0].id)} ${fmt(conNotas[0].v.notas)}. ` : ''}Al contar faltó ${sol(cmp.falta || 0)} y sobró ${sol(cmp.sobra || 0)}; ${sol(cmp.total || 0)} se compensan entre áreas.`},
      {capas: ['c', '99', '97', 'prod', '95', '98', '93'], foco: todas, titulo: 'Lo que quedó', monto: 'Cada caja, su stock',
        texto: 'Cada área cierra con lo que se contó.' + (negs.length ? ' ' + negs.slice(0, 2).map(n => `${nom(n.id)} termina en ${firma(n.v.fin)}`).join(' y ') + ': stock negativo que hay que corregir en el kardex.' : '')}
    ];
  }

  function mapa(ctx, L, fl, W, visible, enFoco) {
    const f = ctx.s.flujo, sel = f.asel || L.alm, sx = W / 790, C = ctx.P.colores_flujo;
    const N = Object.fromEntries(Object.entries(L.N).map(([id, n]) => [id, {...n, x: n.x * sx, w: n.w * sx}]));
    const maxV = Math.max(1, ...fl.map(x => x.v)), ancho = v => Math.max(1.2, v / maxV * 20);
    const centro = n => ({x: n.x + n.w / 2, y: n.y + n.h / 2}), clamp = (x, a) => Math.max(-a, Math.min(a, x));
    const vis = fl.filter(x => visible(x.tipo));
    const pares = new Map();
    for (const x of vis) { const key = [x.o, x.d].sort().join('|'); if (!pares.has(key)) pares.set(key, []); pares.get(key).push(x); }
    for (const xs of pares.values()) { xs.sort((a, b) => a.k < b.k ? -1 : 1); const gap = Math.max(...xs.map(x => ancho(x.v))) + 6; xs.forEach((x, i) => { x.off = (i - (xs.length - 1) / 2) * gap; }); }
    let svg = '', etiquetas = '';
    for (const x of vis) {
      const A = N[x.o], B = N[x.d];
      if (!A || !B) continue;
      const ca = centro(A), cb = centro(B), dx = cb.x - ca.x, dy = cb.y - ca.y, w = ancho(x.v), cab = Math.max(4, w / 2 + 2);
      const abA = A.fila === 'abajo', abB = B.fila === 'abajo', color = x.tipo === '97' ? C.tr : x.tipo === '99' ? C.req : C.compra;
      let d, punta, mx, my, vertical = true;
      if (abA && abB) {
        const x1 = ca.x + x.off, x2 = cb.x + x.off, y1 = A.y, y2 = B.y - 7, alto = Math.min(y1, B.y) - 24;
        d = `M${r1(x1)},${r1(y1)} C${r1(x1)},${r1(alto)} ${r1(x2)},${r1(alto)} ${r1(x2)},${r1(y2)}`;
        punta = `M${r1(x2 - cab)},${r1(y2)} L${r1(x2 + cab)},${r1(y2)} L${r1(x2)},${r1(B.y)} Z`; mx = (x1 + x2) / 2; my = alto + 6;
      } else if (abA || abB || (x.o === L.arriba || x.d === L.arriba) && (x.o === L.alm || x.d === L.alm) || Math.abs(dy) > Math.abs(dx) * 0.9) {
        const s = dy > 0 ? 1 : -1, x1 = ca.x + x.off + clamp(dx * 0.2, A.w / 2 - 12), x2 = cb.x + x.off + clamp(-dx * 0.2, B.w / 2 - 12);
        const y1 = s > 0 ? A.y + A.h : A.y, yb = s > 0 ? B.y : B.y + B.h, y2 = yb - s * 7, ym = (y1 + y2) / 2;
        d = `M${r1(x1)},${r1(y1)} C${r1(x1)},${r1(ym)} ${r1(x2)},${r1(ym)} ${r1(x2)},${r1(y2)}`;
        punta = `M${r1(x2 - cab)},${r1(y2)} L${r1(x2 + cab)},${r1(y2)} L${r1(x2)},${r1(yb)} Z`; mx = (x1 + x2) / 2; my = ym;
      } else {
        vertical = false;
        const s = dx > 0 ? 1 : -1, y1 = ca.y + x.off + clamp(dy * 0.2, A.h / 2 - 8), y2 = cb.y + x.off + clamp(-dy * 0.2, B.h / 2 - 8);
        const x1 = s > 0 ? A.x + A.w : A.x, xb = s > 0 ? B.x : B.x + B.w, x2 = xb - s * 7, xm = (x1 + x2) / 2;
        d = `M${r1(x1)},${r1(y1)} C${r1(xm)},${r1(y1)} ${r1(xm)},${r1(y2)} ${r1(x2)},${r1(y2)}`;
        punta = `M${r1(x2)},${r1(y2 - cab)} L${r1(x2)},${r1(y2 + cab)} L${r1(xb)},${r1(y2)} Z`; mx = xm; my = (y1 + y2) / 2;
      }
      const elegida = sel === 'f:' + x.k, chipDe = sel.startsWith('c:') ? sel.slice(2).split('|')[0] : '';
      const on = elegida || sel === 'comp' || (f.presentar ? enFoco(x.o) && enFoco(x.d) : (!sel.includes(':') && (x.o === sel || x.d === sel)) || (chipDe && (x.o === chipDe || x.d === chipDe)));
      const tip = `${TIPO[x.tipo]} · ${nombre(L, x.o)} → ${nombre(L, x.d)} · ${sol(x.v)}${x.lineas ? ` · ${fmt(x.lineas)} líneas en ${fmt(x.docs)} documentos` : ''} · clic para ver los productos`;
      svg += `<g opacity="${on ? .82 : .16}"><path d="${d}" fill="none" stroke="${color}" stroke-width="${r1(elegida ? w + 2 : w)}"/><path d="${punta}" fill="${color}"/></g><path class="dsta-hit" d="${d}" fill="none" stroke="transparent" stroke-width="${r1(Math.max(12, w + 8))}" data-f="asel:f:${esc(x.k)}" data-tip="${esc(tip)}" tabindex="0" role="button" aria-label="${esc(tip)}"/>`;
      // El rótulo, del lado de afuera de su línea: dos flechas de un mismo par no se tapan.
      if (on && x.tipo !== 'c' && x.v >= maxV * 0.03) etiquetas += `<div class="dsta-etq" style="left:${r1(vertical ? mx + (x.off < 0 ? -6 - w / 2 : 6 + w / 2) : mx)}px;top:${r1(vertical ? my : my + (x.off < 0 ? -4 - w / 2 : 4 + w / 2))}px;transform:translate(${vertical ? (x.off < 0 ? '-100%' : '0') : '-50%'},${vertical ? '-50%' : (x.off < 0 ? '-100%' : '0')});color:${color}">${x.tipo} · ${fmt(x.v)}</div>`;
    }
    const cajas = Object.values(N).map(n => {
      const on = sel === n.id, foco = enFoco(n.id), v = n.v, chips = [];
      const chip = (t, clave, fondo, texto, tip) => chips.push(`<button type="button" class="dsta-chip${sel === 'c:' + n.id + '|' + clave ? ' on' : ''}" data-f="asel:c:${n.id}|${clave}" data-tip="${esc(tip)}" style="background:${fondo};color:${texto}">${esc(t)}</button>`);
      if (n.id === 'prov') {
        if (visible('c')) chips.push(`<button type="button" class="dsta-chip" data-f="asel:f:c|prov|${L.alm}" data-tip="Compras netas del cierre · clic para ver el detalle" style="background:var(--dstf-gris-claro)">Compras ${esc(fmt(N[L.alm].v.compra))}</button>`);
      } else {
        const tinte = c => `color-mix(in srgb, ${c} 13%, white)`;
        if (visible('95') && v.venta > 0.5) chip('95 vende ' + fmt(v.venta), '95', tinte(C.vende), C.vende, `Descargo de ventas: ${sol(v.venta)} · clic para ver qué productos`);
        if (visible('prod') && v.prod_in > 0.5) chip('96·94 ' + fmt(v.prod_in), 'prod', tinte(C.prod), C.prod, `Porcionado o producido: ${sol(v.prod_in)} · clic para ver qué`);
        if (visible('98') && v.notas > 0.5) chip('98 notas ' + fmt(v.notas), '98', tinte(C.notas), C.notas, `Notas de salida: ${sol(v.notas)} · clic para ver qué salió`);
        const aj = v.aj_pos - v.aj_neg;
        if (visible('93') && v.aj_pos + v.aj_neg > 0.5) chip('93 ' + firma(aj), '93', tinte(aj < 0 ? C.ajuste : C.bien), aj < 0 ? C.ajuste : C.bien, `Ajuste del conteo: faltó ${fmt(v.aj_neg)} y sobró ${fmt(v.aj_pos)} · clic para ver qué productos`);
      }
      const linea = n.id === 'prov' ? 'Facturas, guías y notas' : n.w < 150 ? `${fmt(v.ini)} → ${fmt(v.fin)}` : `Había ${fmt(v.ini)} → quedó ${fmt(v.fin)}`;
      return `<div class="dsta-caja${on ? ' on' : ''}${v && v.fin < -0.5 ? ' neg' : ''}" style="left:${r1(n.x)}px;top:${n.y}px;width:${r1(n.w)}px;height:${n.h}px;opacity:${foco ? 1 : .3}"><button type="button" class="dsta-nombre" data-f="${n.id === 'prov' ? `asel:f:c|prov|${L.alm}` : 'asel:' + n.id}" aria-pressed="${on}" data-tip="${esc(n.ayuda ? n.ayuda + ' · clic para ver su balance' : n.id === 'prov' ? 'Proveedores' : 'Clic para ver el balance de ' + nombre(L, n.id))}"><b>${esc(n.nombre)}</b><span>${esc(linea)}</span></button><span class="dsta-chips">${chips.join('')}</span></div>`;
    }).join('');
    return `<div class="dsta-lienzo" style="width:${W}px;height:318px"><svg width="${W}" height="318" aria-hidden="false">${svg}</svg>${etiquetas}${cajas}</div>`;
  }
  const nombre = (L, id) => id === 'prov' ? 'Proveedores' : L.N[id] ? L.N[id].nombre.charAt(0) + L.N[id].nombre.slice(1).toLowerCase() : id;

  function panel(ctx, L, fl, ps) {
    const f = ctx.s.flujo, sel = f.asel || L.alm, filas = (tops, total) => tops.map(([t, v]) => `<p class="dsta-fila"><span>${esc(t)}</span><span>${esc(fmt(v))}</span><span>${fmt(v / Math.max(1, total) * 100)} %</span></p>`).join('');
    if (f.presentar) {
      const p = ps[f.paso - 1];
      return `<div class="dstf-tag">PRESENTAR · PASO ${f.paso} DE ${ps.length}</div><div class="dsta-paso"><div class="dsta-puntos">${ps.map((x, i) => `<button type="button" data-f="paso:${i + 1}" aria-label="Ir al paso ${i + 1}: ${esc(x.titulo)}" class="${i + 1 <= f.paso ? 'on' : ''}"></button>`).join('')}</div><h4>${esc(p.titulo)}</h4><strong>${esc(p.monto)}</strong><p>${esc(p.texto)}</p><div class="dsta-nav"><button type="button" data-f="paso:${f.paso - 1}" ${f.paso === 1 ? 'disabled' : ''}>‹ Anterior</button><button type="button" class="dsta-sig" data-f="${f.paso < ps.length ? 'paso:' + (f.paso + 1) : 'pres'}">${f.paso < ps.length ? 'Siguiente ›' : 'Terminar'}</button></div></div>`;
    }
    if (sel === 'comp') {
      const c = datos(ctx).compensa || {}, ant = (ctx.P.areas?.[ctx.grupo] || [])[ctx.k - 1]?.compensa;
      const lado = l => l.map(([a, v]) => `${ctx.P.nombres_area[a] || a} ${firma(v)}`).join(' / ');
      return `<div class="dstf-tag">AJUSTES QUE SE COMPENSAN ENTRE ÁREAS</div><div class="dstf-monto"><strong>${esc(sol(c.total || 0))}</strong><span>en ${fmt(c.n || 0)} productos</span></div><p class="dstf-cod">Lo que faltó al contar en un área y sobró en otra, producto por producto. No es pérdida: cambió de área sin documento, o se contó donde no estaba.</p><div class="dstf-tops"><b>Los que más pesan</b>${(c.tops || []).map(([p, v, l]) => `<p class="dsta-comp"><span>${esc(p)}</span><b>${esc(fmt(v))}</b><small>${esc(lado(l))}</small></p>`).join('')}</div>${ant ? `<p class="dstf-nota">${esc(ctx.P.periodos[ctx.k - 1].nombre)}: ${esc(sol(ant.total))} en ${fmt(ant.n)} productos.</p>` : ''}<p class="dstf-nota">Al contar faltó ${esc(sol(c.falta || 0))} y sobró ${esc(sol(c.sobra || 0))} sumando área por área.</p>`;
    }
    if (sel.startsWith('f:')) {
      const k = sel.slice(2), x = fl.find(y => y.k === k), [tipo, o, d] = k.split('|');
      if (!x) return `<p class="dstf-nota">Esa flecha no está en este cierre.</p>`;
      if (tipo === 'c') return `<div class="dstf-tag">COMPRAS · PROVEEDORES → ${esc(nombre(L, d).toUpperCase())}</div><div class="dstf-monto"><strong>${esc(sol(x.v))}</strong><span>compras netas</span></div><p class="dstf-cod">${esc(QUE.c)}</p><p class="dstf-nota">Los productos comprados están en Compras › Producto; aquí cuenta el total que entró al Almacén.</p>`;
      return `<div class="dstf-tag">${esc(TIPO[tipo].toUpperCase())} · ${esc(nombre(L, o).toUpperCase())} → ${esc(nombre(L, d).toUpperCase())}</div><div class="dstf-monto"><strong>${esc(sol(x.v))}</strong><span>${fmt(x.lineas)} líneas en ${fmt(x.docs)} documentos</span></div><p class="dstf-cod">${esc(QUE[tipo])}</p><div class="dstf-tops"><b>Lo que más pesó</b>${filas(x.tops, x.v)}</div><p class="dstf-nota">De la fila «transferencias» del Sheet: cada línea con su documento, origen y destino.</p>`;
    }
    if (sel.startsWith('c:')) {
      const [id, clave] = sel.slice(2).split('|'), nd = L.N[id];
      if (!nd) return '';
      const [tit, que] = CHIP[clave] || ['', ''];
      let monto = '', share = '', bloques = '';
      if (clave === '93') {
        const fa = detalleChip(ctx, L, id, 'falta'), so = detalleChip(ctx, L, id, 'sobra');
        monto = sol((so ? so[0] : 0) - (fa ? fa[0] : 0)); share = 'neto';
        if (fa) bloques += `<div class="dstf-tops"><b>Faltó ${fmt(fa[0])} en ${fmt(fa[1])} productos</b>${filas(fa[2], fa[0])}</div>`;
        if (so) bloques += `<div class="dstf-tops"><b>Sobró ${fmt(so[0])} en ${fmt(so[1])} productos</b>${filas(so[2], so[0])}</div>`;
      } else {
        const dc = detalleChip(ctx, L, id, clave);
        if (dc) { monto = sol(dc[0]); share = `en ${fmt(dc[1])} productos`; bloques = `<div class="dstf-tops"><b>Lo que más pesó</b>${filas(dc[2], dc[0])}</div>`; }
      }
      return `<div class="dstf-tag">${esc(nd.nombre)} · ${esc(tit)}</div><div class="dstf-monto"><strong>${esc(monto)}</strong><span>${esc(share)}</span></div><p class="dstf-cod">${esc(que)}</p>${bloques}${notas(L, id) ? `<p class="dstf-nota">${esc(notas(L, id))}</p>` : ''}`;
    }
    const nd = L.N[sel] || L.N[L.alm], v = nd.v, cas = [];
    const linea = (t, x, cls = '') => cas.push(`<span class="${cls}">${esc(t)}</span><span class="${cls || (x < 0 ? 'neg' : 'pos')}">${cls ? fmt(x) : firma(x)}</span>`);
    linea('Había', v.ini, 'f');
    if (Math.abs(v.compra) > 0.5) linea('Compras', v.compra);
    if (v.req_in + v.tr_in > 0.5) linea('Recibió de otras áreas (99 · 97)', v.req_in + v.tr_in);
    if (v.prod_in > 0.5) linea('Produjo o porcionó (94 · 96)', v.prod_in);
    if (v.req_out + v.tr_out > 0.5) linea('Envió a otras áreas (99 · 97)', -(v.req_out + v.tr_out));
    if (v.prod_out > 0.5) linea('Usó en producción (94 · 96)', -v.prod_out);
    if (Math.abs(v.venta) > 0.5) linea('Vendió (95)', -v.venta);
    if (Math.abs(v.notas) > 0.5) linea('Notas (91 · 92 · 98)', -v.notas);
    if (v.aj_pos > 0.5) linea('Sobró al contar (93)', v.aj_pos);
    if (v.aj_neg > 0.5) linea('Faltó al contar (93)', -v.aj_neg);
    if (Math.abs(v.val) > 0.5) linea('Diferencia de valorización', v.val);
    linea('Quedó', v.fin, 'f total');
    const envia = fl.filter(x => x.o === nd.id && x.tipo !== 'c').sort((a, b) => b.v - a.v).slice(0, 3), recibe = fl.filter(x => x.d === nd.id).sort((a, b) => b.v - a.v).slice(0, 3);
    const col = (t, xs, f) => xs.length ? `<div><b>${t}</b>${xs.map(x => `<p class="dsta-fila2"><span>${esc(f(x))}</span><span>${esc(fmt(x.v))}</span></p>`).join('')}</div>` : '<div></div>';
    return `<div class="dstf-tag">BALANCE DEL ÁREA · ${esc(nd.nombre)}</div><div class="dsta-cascada">${cas.join('')}</div><div class="dsta-envios">${col('Envía a', envia, x => `${nombre(L, x.d)} (${x.tipo})`)}${col('Recibe de', recibe, x => x.tipo === 'c' ? 'Proveedores' : `${nombre(L, x.o)} (${x.tipo})`)}</div>${notas(L, nd.id) ? `<p class="dstf-nota">${esc(notas(L, nd.id))}</p>` : ''}${nd.ayuda ? `<p class="dstf-nota">Junta: ${esc(nd.ayuda)}.</p>` : ''}`;
  }

  function matriz(ctx, L, fl) {
    const N = L.N, filas = ['prov', ...L.orden.filter(id => id !== 'prov')], cols = L.orden.filter(id => id !== 'prov'), C = ctx.P.colores_flujo;
    const celda = (x, tono) => {
      const a = Math.abs(x), t = a < 0.5 ? '' : (x < 0 ? '−' : '') + fmt(a), alfa = a < 0.5 ? 0 : Math.min(0.85, 0.08 + Math.log10(a + 1) / 5.2 * 0.8);
      return `<span class="dsta-m${alfa > 0.5 ? ' osc' : ''}" title="${t ? 'S/ ' + esc(t) : ''}" style="background:color-mix(in srgb, ${tono} ${Math.round(alfa * 100)}%, transparent)">${t}</span>`;
    };
    const plantilla = `grid-template-columns:118px repeat(${cols.length},minmax(0,1fr)) repeat(4,74px)`;
    const cab = `<div class="dsta-mfila cab" style="${plantilla}"><span>De ↓ · a →</span>${cols.map(id => `<span title="${esc(nombre(L, id))}">${esc(nombre(L, id))}</span>`).join('')}${['Vendió (95)', 'Notas', 'Ajuste neto', 'Quedó'].map(t => `<span class="ext">${t}</span>`).join('')}</div>`;
    const cuerpo = filas.map(o => `<div class="dsta-mfila" style="${plantilla}"><span class="rot" title="${esc(nombre(L, o))}">${esc(nombre(L, o))}</span>${cols.map(d => celda(fl.filter(x => x.o === o && x.d === d).reduce((a, x) => a + x.v, 0), C.req)).join('')}${o === 'prov' ? '<span></span><span></span><span></span><span></span>' : celda(N[o].v.venta, C.vende) + celda(N[o].v.notas, C.vende) + celda(N[o].v.aj_pos - N[o].v.aj_neg, C.ajuste) + `<span class="dsta-m quedo">${esc(fmt(N[o].v.fin))}</span>`}</div>`).join('');
    return `<div class="dsta-matriz" role="table" aria-label="Matriz de origen y destino">${cab}${cuerpo}</div><p class="dstf-nota">Cada fila es de dónde sale; cada columna, a dónde llega. Las cuatro columnas de la derecha son lo que no pasa a otra área: lo vendido, las notas, el ajuste neto del conteo y lo que quedó. Más oscuro, más soles.</p>`;
  }

  // ── Lo que pide el flujo ───────────────────────────────────────────────
  function botones(ctx) {
    const f = ctx.s.flujo;
    return `<div class="dstf-botones" role="group" aria-label="Forma">${[['mapa', 'Mapa'], ['matriz', 'Matriz']].map(([v, t]) => `<button type="button" data-f="forma:${v}" class="${f.forma === v ? 'on' : ''}" aria-pressed="${f.forma === v}">${t}</button>`).join('')}</div><button type="button" data-f="pres" class="${f.presentar ? 'on' : ''}" aria-pressed="${f.presentar}"><svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 4v16l13-8z"/></svg>${f.presentar ? 'Salir de presentar' : 'Presentar'}</button>`;
  }
  function aviso(ctx) {
    const A = datos(ctx), c = A?.compensa;
    return c && c.total > 0.5 ? `<button type="button" class="dstf-neg${ctx.s.flujo.asel === 'comp' ? ' on' : ''}" data-f="comp" aria-pressed="${ctx.s.flujo.asel === 'comp'}"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M7 7h11l-3-3M17 17H6l3 3"/></svg>Se compensan entre áreas · ${esc(sol(c.total))}</button>` : '';
  }
  function html(ctx, W) {
    const L = disposicion(ctx), f = ctx.s.flujo;
    if (!L) return `<p class="dstf-nota dsta-vacio">El balance por área no se pudo calcular para este cierre: hace falta el kardex por área y la fila «transferencias» del Sheet.</p>`;
    const fl = flechas(ctx, L), ps = pasos(ctx, L, fl), PASO = ps[f.paso - 1];
    const visible = c => f.presentar ? PASO.capas.includes(c) : f.capas[c] !== false, enFoco = id => !f.presentar || PASO.foco.includes(id);
    const capas = `<div class="dsta-capas"><span>Mostrar</span>${CAPAS.map(([c, t, col]) => { const on = visible(c); return `<button type="button" data-f="capa:${c}" aria-pressed="${on}" class="${on ? 'on' : 'off'}" ${f.presentar ? 'disabled title="En «Presentar» las capas las pone cada paso"' : `title="${on ? 'Ocultar' : 'Mostrar'} ${t.toLowerCase()}"`}><i style="background:${on ? ctx.P.colores_flujo[col] : 'var(--dstf-gris)'}"></i>${t}</button>`; }).join('')}</div>`;
    const sinTraslados = !(datos(ctx).flechas || []).length ? '<p class="dstf-nota">Sin la fila «transferencias» del Sheet el mapa no sabe de dónde a dónde va cada traslado: sólo se ven las compras y el balance de cada área.</p>' : '';
    const fam = ctx.P.areas_familias ? '<p class="dstf-nota">El mapa por área cuenta todas las familias: el chip Familia de la página no lo filtra.</p>' : '';
    const izq = f.forma === 'matriz' && !f.presentar ? matriz(ctx, L, fl) : `${mapa(ctx, L, fl, Math.max(560, W), visible, enFoco)}<p class="dstf-nota">Pasa el cursor sobre una flecha o un chip para ver su valor; haz clic para ver qué productos lo forman. Venta por área: la del kardex (las ventas que cruzan el conteo se ven en «Restaurante»).</p>`;
    return `${capas}<div class="dstf-abierto"><div class="dstf-izq">${izq}${sinTraslados}${fam}</div><aside class="dstf-panel" aria-label="Detalle de lo elegido">${panel(ctx, L, fl, ps)}</aside></div>`;
  }
  function accion(ctx, a, v) {
    const f = ctx.s.flujo;
    if (a === 'forma') f.forma = v;
    else if (a === 'pres') { f.presentar = !f.presentar; f.paso = 1; f.forma = 'mapa'; }
    else if (a === 'paso') f.paso = Math.max(1, Math.min(6, Number(v) || 1));
    else if (a === 'capa') { if (!f.presentar) f.capas = {...f.capas, [v]: f.capas[v] === false}; }
    else if (a === 'asel') { f.asel = f.asel === v ? '' : v; f.presentar = false; }
    else if (a === 'comp') { f.asel = f.asel === 'comp' ? '' : 'comp'; f.presentar = false; f.forma = 'mapa'; }
    else return false;
    return true;
  }
  function tooltip(el, signal) {
    let tip = null;
    const quitar = () => { tip?.remove(); tip = null; };
    el.addEventListener('pointermove', e => {
      const t = e.composedPath().find(x => x?.dataset?.tip);
      if (!t || !el.contains(t)) { quitar(); return; }
      if (!tip) { tip = el.ownerDocument.createElement('div'); tip.className = 'dsta-tip'; tip.setAttribute('role', 'tooltip'); el.append(tip); }
      if (tip.textContent !== t.dataset.tip) tip.textContent = t.dataset.tip;
      const r = el.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
      tip.style.left = Math.min(x + 12, el.clientWidth - 260) + 'px'; tip.style.top = (y + 16) + 'px';
    }, {signal});
    el.addEventListener('pointerleave', quitar, {signal});
    el.addEventListener('click', quitar, {signal});
  }
  function hojas(ctx) {
    const L = disposicion(ctx);
    if (!L) return [];
    const A = datos(ctx), P = ctx.P, fl = flechas(ctx, L);
    return [
      {nombre: 'Por área', cabeza: ['Código', 'Área', ...P.cols_area], filas: Object.entries(A.areas).map(([c, arr]) => [c, P.nombres_area[c] || c, ...arr]), decimales: 6},
      {nombre: 'Traslados', cabeza: ['Tipo', 'Origen', 'Destino', 'Importe S/', 'Líneas', 'Documentos'], filas: (A.flechas || []).map(f => [f[0], P.nombres_area[f[1]] || f[1], P.nombres_area[f[2]] || f[2], f[3], f[4], f[5]]), decimales: 6},
      {nombre: 'Compensaciones', cabeza: ['Producto', 'Compensado S/', 'Áreas'], filas: (A.compensa?.tops || []).map(([p, v, l]) => [p, v, l.map(([a, x]) => `${P.nombres_area[a] || a} ${x}`).join(' / ')]), decimales: 6},
      {nombre: 'Mapa', cabeza: ['Flecha', 'Importe S/'], filas: fl.map(x => [`${TIPO[x.tipo]} · ${nombre(L, x.o)} → ${nombre(L, x.d)}`, x.v]), decimales: 6}
    ];
  }
  return {botones, aviso, html, accion, tooltip, hojas, disposicion, flechas, pasos};
})();
window.__destinoAreas = DESTINO_AREAS;
