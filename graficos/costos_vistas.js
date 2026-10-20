// Las dos formas de la parte de arriba de «Costo de ventas» y la evolución
// que va debajo de las dos (regla #679, sobre un boceto aprobado:
// https://claude.ai/artifact/RPV9HCSNWa9rrZtABRnRkj).
//
// - Tablero: cuatro indicadores del período elegido, la tabla y, al
//   costado, el estado del período (cascada compacta, observaciones,
//   cobertura SUNAT). Si la tabla no entra al lado, el estado baja.
// - Cascada: una tira con los períodos de la ventana y el elegido explicado
//   en una cascada; la tabla pasa a ser la primera pestaña de abajo.
//
// Se concatena con costos_paneles.js y costos_tabla.js (mismo módulo): usa
// `valores`, `esc`, `num`, `soles`, `pct` de allá. Nada vuelve a Python.

const VISTAS = [['tablero', 'Tablero'], ['cascada', 'Cascada']];

// Las cifras de la ventana para las familias elegidas, y qué período se sale
// de lo habitual: el que pasa el doble de la mediana de «sin explicar» (y por
// lo menos 2 puntos encima de ella), con tres períodos o más para comparar.
function cifras(st, data, w, F) {
  const s = (k) => valores(st, data, w, { k, tipo: 'suma' }, F).mes;
  const v = s('v'), carta = s('carta'), pos = s('pos'), dif = s('dif'), bajas = s('bajas'), falt = s('falt');
  const tasa = (a) => a.map((x, i) => (v[i] ? x / v[i] : null));
  const tf = tasa(falt);
  const ord = tf.filter((x) => x != null && isFinite(x)).sort((a, b) => a - b);
  const m = ord.length;
  const med = m ? (m % 2 ? ord[(m - 1) / 2] : (ord[m / 2 - 1] + ord[m / 2]) / 2) : null;
  const umbral = med == null || m < 3 ? null : Math.max(2 * med, med + 0.02);
  return {
    v, carta, pos, dif, bajas, falt, tc: tasa(carta), tp: tasa(pos), tf, med,
    raro: tf.map((x) => umbral != null && x != null && x > umbral),
  };
}

function cabeceraVista(st, w, i) {
  const seg = `<div class="modo cv-vista" role="group" aria-label="Vista">${VISTAS.map(([k, nom]) =>
    `<button type="button" data-vista="${k}" aria-pressed="${st.vista === k}">${nom}</button>`).join('')}</div>`;
  const nav = `<span class="cv-nav"><button type="button" data-paso="-1" aria-label="Período anterior">‹</button>`
    + `<span class="cv-sel">${esc(w.per[i].rot)}</span>`
    + `<button type="button" data-paso="1" aria-label="Período siguiente">›</button></span>`;
  return nav + seg;
}

function sparkline(arr, i, clase) {
  const W = 200, H = 30;
  const pts = arr.map((x, j) => [x, j]).filter(([x]) => x != null && isFinite(x));
  if (pts.length < 2) return '';
  const vs = pts.map(([x]) => x), lo = Math.min(...vs), hi = Math.max(...vs), r = hi - lo || 1;
  const xp = (j) => (j * W) / (arr.length - 1), yp = (x) => H - 3 - ((x - lo) / r) * (H - 6);
  const d = pts.map(([x, j], k) => `${k ? 'L' : 'M'}${xp(j).toFixed(1)} ${yp(x).toFixed(1)}`).join(' ');
  const sel = arr[i] != null && isFinite(arr[i]) ? `<circle cx="${xp(i)}" cy="${yp(arr[i])}" r="3"/>` : '';
  return `<svg class="cv-spark ${clase}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">`
    + `<path class="area" d="${d} L${xp(pts[pts.length - 1][1])} ${H} L${xp(pts[0][1])} ${H}Z"/><path class="linea" d="${d}"/>${sel}</svg>`;
}

function variacion(actual, previo, puntos, malSiSube, rot) {
  if (actual == null || previo == null || !isFinite(actual) || !isFinite(previo)) return '';
  const d = puntos ? (actual - previo) * 100 : (Math.abs(previo) < 1 ? null : ((actual - previo) / Math.abs(previo)) * 100);
  if (d == null || Math.abs(d) < 0.05) return `<span class="cv-var">= vs ${esc(rot)}</span>`;
  const sube = d > 0;
  return `<span class="cv-var ${sube === malSiSube ? 'mal' : 'bien'}">${sube ? '▲' : '▼'} ${Math.abs(d).toFixed(1)}${puntos ? ' pts' : ' %'} vs ${esc(rot)}</span>`;
}

// Tablero: los cuatro indicadores del período elegido.
function indicadores(w, c, i) {
  const ant = i > 0 ? w.per[i - 1].rot : null;
  const vr = (a, puntos, mal) => (ant ? variacion(a[i], a[i - 1], puntos, mal, ant) : '');
  const raro = c.raro[i];
  return `<div class="cv-kpis">
    <div class="cv-kpi"><span class="cv-rot">Venta neta documentada</span><b class="cv-cifra">${soles(c.v[i])}</b>${vr(c.v, false, false)}${sparkline(c.v, i, 'carta')}</div>
    <div class="cv-kpi"><span class="cv-rot">Consumo carta</span><b class="cv-cifra">${pct(c.tc[i])}</b><span class="cv-sub">${soles(c.carta[i])} · según inventario</span>${sparkline(c.tc, i, 'carta')}</div>
    <div class="cv-kpi"><span class="cv-rot">Costo del Sistema</span><b class="cv-cifra">${pct(c.tp[i])}</b><span class="cv-sub">${soles(c.pos[i])} · según lo vendido</span>${sparkline(c.tp, i, 'sistema')}</div>
    <div class="cv-kpi${raro ? ' raro' : ''}"><span class="cv-rot">Sin explicar</span><b class="cv-cifra">${soles(c.falt[i])}</b><span class="cv-sub">${pct(c.tf[i])} de la venta</span>${vr(c.tf, true, true)}${sparkline(c.tf, i, raro ? 'raro' : 'falt')}</div>
  </div>`;
}

// Tablero: la cascada en el costado. Dos barras a la misma escala y la
// diferencia partida en bajas y sin explicar (sólo si las dos son positivas:
// si no, lo dice en palabras).
function cascadaCompacta(w, c, i) {
  const carta = c.carta[i], pos = c.pos[i], dif = c.dif[i], bajas = c.bajas[i], falt = c.falt[i];
  const mx = Math.max(Math.abs(carta), Math.abs(pos)) || 1;
  const fila = (nom, val, clase) => `<div class="cv-hfila"><span>${nom}</span><span class="cv-hbarra"><i class="${clase}" style="width:${(Math.max(0, val) / mx) * 100}%"></i></span><b>${num(val)}</b></div>`;
  let parte;
  if (dif > 0.5 && bajas >= 0 && falt >= 0) {
    parte = `<div class="cv-parte"><span>La diferencia, <b>${soles(dif)}</b>, se reparte así:</span>
      <div class="cv-reparto"><i class="bajas" style="width:${(bajas / dif) * 100}%"></i><i class="${c.raro[i] ? 'raro' : 'falt'}" style="width:${(falt / dif) * 100}%"></i></div>
      <div class="cv-reparto-rot"><span>Bajas <b>${num(bajas)}</b> · ${Math.round((bajas / dif) * 100)} %</span><span>Sin explicar <b>${num(falt)}</b> · ${Math.round((falt / dif) * 100)} %</span></div></div>`;
  } else if (dif <= 0.5) {
    parte = `<p class="cv-nota-corta">El consumo carta quedó <b>${soles(-dif)}</b> por debajo del Sistema: no hay diferencia que repartir.</p>`;
  } else {
    parte = `<p class="cv-nota-corta">Las bajas registradas (${soles(bajas)}) superan la diferencia (${soles(dif)}).</p>`;
  }
  return `<div class="cv-tarjeta"><h3>De consumo carta a sin explicar · ${esc(w.per[i].rot)}</h3>
    ${fila('Consumo carta', carta, 'carta')}${fila('Costo del Sistema', pos, 'sistema')}${parte}</div>`;
}

// Las observaciones de valorización, en corto, y el botón que abre el detalle
// entero a todo el ancho (`observaciones`, de costos_paneles.js).
function calidadCorta(st, data, w, F) {
  if (st.grano !== 'mes') return '';
  const q = calidad(st, data, w, F);
  const abierto = st.notasAbiertas.has('calidad');
  const lista = q.puntos.length
    ? `<ul>${q.puntos.map((p) => `<li>${p}</li>`).join('')}</ul>`
    : '<p class="cv-nota-corta">Sin alertas automáticas en la selección. No certifica el conteo físico.</p>';
  return `<div class="cv-tarjeta${q.observada ? ' alerta' : ''}"><h3>${q.observada ? 'Observaciones de valorización' : 'Calidad de los datos'} · ${esc(q.nombre)}</h3>${lista}
    <button type="button" class="cv-enlace" data-ver-calidad aria-expanded="${abierto}">${abierto ? 'Cerrar el detalle' : 'Ver detalle por familia'} ${abierto ? '↑' : '↓'}</button></div>`;
}

function coberturaCorta(st) {
  if (st.grano !== 'mes') return '';
  const c = st.todo.documental?.[st.seleccionado];
  const enlace = st.todo.enlaces?.mes?.[st.seleccionado]?.documental?.url || '?reporte=Documentos%20SUNAT';
  const abrir = `<a class="cv-enlace" href="${esc(enlace)}" target="_blank" rel="noopener noreferrer">Abrir Documentos SUNAT del mes ↗</a>`;
  if (!c?.disponible) {
    return `<div class="cv-tarjeta cv-cob"><h3>Cobertura SUNAT y Sistema</h3><p class="cv-nota-corta">No hay registro SUNAT cargado para este mes. No equivale a cero comprobantes pendientes.</p>${abrir}</div>`;
  }
  const r = 26, largo = 2 * Math.PI * r, lleno = Math.max(0, Math.min(1, c.cobertura || 0)) * largo;
  const notas = c.notas_sin_coincidencia ? ` · ${c.notas_sin_coincidencia} notas por ${soles(c.importe_notas_sin_coincidencia)}` : '';
  return `<div class="cv-tarjeta cv-cob"><h3>Cobertura SUNAT y Sistema</h3>
    <div class="cv-anillo"><svg width="56" height="56" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="${r}" class="fondo"/><circle cx="32" cy="32" r="${r}" class="lleno" stroke-dasharray="${lleno.toFixed(1)} ${largo.toFixed(1)}" transform="rotate(-90 32 32)"/></svg>
    <div><b class="cv-cifra">${pct(c.cobertura)}</b><span class="cv-sub">${c.ubicados} de ${c.documentos} ubicados · ${c.coinciden} coinciden, ${c.con_diferencia} con diferencias</span></div></div>
    <p class="cv-nota-corta">${c.sin_coincidencia} sin coincidencia en el Sistema · importes positivos ${soles(c.importe_positivo_sin_coincidencia)}${notas}.</p>${abrir}</div>`;
}

// La misma cobertura en un renglón: va debajo de la tabla cuando el estado
// del período está al costado (`cv-lado`), para que la columna no quede más
// alta que la tabla. El CSS muestra una u otra.
function coberturaLinea(st) {
  if (st.grano !== 'mes') return '';
  const c = st.todo.documental?.[st.seleccionado];
  const enlace = st.todo.enlaces?.mes?.[st.seleccionado]?.documental?.url || '?reporte=Documentos%20SUNAT';
  const texto = c?.disponible
    ? `<b>${pct(c.cobertura)}</b> · ${c.ubicados} de ${c.documentos} ubicados · ${c.sin_coincidencia} sin coincidencia (${soles(c.importe_positivo_sin_coincidencia)})`
    : 'sin registro SUNAT cargado para este mes';
  return `<div class="cv-tarjeta cv-cob-linea"><span><span class="cv-rot">Cobertura SUNAT y Sistema</span> ${texto}</span><a class="cv-enlace" href="${esc(enlace)}" target="_blank" rel="noopener noreferrer">Abrir Documentos SUNAT ↗</a></div>`;
}

// Cascada: la tira con los períodos de la ventana.
function tira(st, w, c) {
  const top = Math.max(...c.tc, ...c.tp, 0.01);
  return `<div class="cv-tira" style="--cv-n:${w.per.length}" role="group" aria-label="Elegir período">${w.per.map((p, i) => `<button type="button" class="cv-mes${p.k === st.seleccionado ? ' on' : ''}" data-seleccionar="${esc(p.k)}" aria-pressed="${p.k === st.seleccionado}">
      <span class="m">${esc(p.rot)}</span><b class="${c.raro[i] ? 'raro' : ''}">${pct(c.tf[i])}</b>
      <span class="mini"><i class="carta" style="height:${Math.max(0, (c.tc[i] || 0) / top) * 100}%"></i><i class="sistema" style="height:${Math.max(0, (c.tp[i] || 0) / top) * 100}%"></i></span>
      <span class="cv-rot">sin explicar</span></button>`).join('')}</div>`;
}

function acciones(st) {
  return `<div class="cv-acciones"><button type="button" class="cv-accion" data-pestana="tabla">Ver la tabla</button>${st.grano === 'mes' ? '<button type="button" class="cv-accion" data-revisar-mes>Revisar cálculo y observaciones</button>' : ''}</div>`;
}

function lectura(st, w, c, i) {
  const rot = w.per[i].rot, t = (x) => pct(x);
  const partes = [`<p>Según el inventario se consumió <b>${soles(c.carta[i])}</b> (${t(c.tc[i])} de la venta). Por el costo guardado en lo vendido, el Sistema esperaba <b>${soles(c.pos[i])}</b> (${t(c.tp[i])}).</p>`];
  if (c.dif[i] > 0.5) {
    partes.push(`<p>La diferencia es <b>${soles(c.dif[i])}</b>. Las bajas registradas explican <b>${soles(c.bajas[i])}</b>${c.bajas[i] > 0 ? ` (${Math.round((c.bajas[i] / c.dif[i]) * 100)} %)` : ''}.</p>`);
  } else {
    partes.push(`<p>El consumo quedó <b>${soles(-c.dif[i])}</b> por debajo de lo que esperaba el Sistema.</p>`);
  }
  const med = c.med == null ? '' : ` (mediana de la ventana: ${t(c.med)})`;
  if (c.falt[i] < -0.5) {
    partes.push(`<p>Lo sin explicar es negativo, <b>${soles(c.falt[i])}</b> (${t(c.tf[i])} de la venta): con las bajas sumadas, se consumió menos de lo que esperaba el Sistema.${st.grano === 'mes' ? ' Revisar el conteo del cierre y las compras sin ingresar.' : ' Con el inventario del kardex suele ser un ajuste de cierre que cae en otro período.'}</p>`);
    return `<div class="cv-tarjeta cv-lectura"><h3>Qué pasó en ${esc(rot)}</h3>${partes.join('')}${acciones(st)}</div>`;
  }
  partes.push(`<p>Quedan <b class="${c.raro[i] ? 'raro' : ''}">${soles(c.falt[i])}</b> sin explicar, ${t(c.tf[i])} de la venta. ${c.raro[i]
    ? `Es más del doble de lo habitual${med}: revisar el conteo y las observaciones de este cierre.`
    : `Está dentro de lo habitual${med}.`}</p>`);
  return `<div class="cv-tarjeta cv-lectura"><h3>Qué pasó en ${esc(rot)}</h3>${partes.join('')}${acciones(st)}</div>`;
}

// Cascada: consumo carta − Sistema = diferencia − bajas = sin explicar.
// Cada barra va entre dos niveles; aguanta diferencias negativas.
function cascadaGrande(st, w, c, i) {
  const total = st.anchoGraf || 1000;
  const W = Math.max(420, Math.round(st.angosta ? total - 30 : (total - 10) * 7 / 12 - 30)), H = 250, T = 26, B = 50, L = 8;
  const carta = c.carta[i], pos = c.pos[i], dif = c.dif[i], bajas = c.bajas[i], falt = c.falt[i];
  const pasos = [['Consumo carta', 0, carta, 'carta', carta], ['− Costo del Sistema', dif, carta, 'sistema', pos],
    ['Diferencia', 0, dif, 'dif', dif], ['− Bajas', falt, dif, 'sistema', bajas], ['Sin explicar', 0, falt, c.raro[i] ? 'raro' : 'falt', falt]];
  const niveles = pasos.flatMap((p) => [p[1], p[2]]);
  const hi = Math.max(...niveles, 1) * 1.08, lo = Math.min(0, ...niveles);
  const y = (v) => T + ((hi - v) / (hi - lo)) * (H - T - B);
  const bw = Math.min(120, Math.max(64, W / 7)), gap = (W - 2 * L - bw * 5) / 4;
  let s = `<svg class="cv-cascada" viewBox="0 0 ${W} ${H}" role="img" aria-label="Cascada de ${esc(w.per[i].rot)}"><line x1="0" x2="${W}" y1="${y(0)}" y2="${y(0)}" class="cv-eje"/>`;
  pasos.forEach(([nom, a, b, clase, val], k) => {
    const x = L + k * (bw + gap), arriba = Math.min(y(a), y(b)), alto = Math.max(2, Math.abs(y(a) - y(b)));
    if (k < 4) {
      const nivel = k === 0 ? carta : k === 1 || k === 2 ? dif : falt;
      s += `<line x1="${x + bw}" x2="${x + bw + gap}" y1="${y(nivel)}" y2="${y(nivel)}" class="cv-guia"/>`;
    }
    s += `<rect x="${x}" y="${arriba}" width="${bw}" height="${alto}" rx="4" class="${clase}"><title>${esc(nom)}: ${esc(soles(val))}</title></rect>`
      + `<text class="v" x="${x + bw / 2}" y="${arriba - 6}" text-anchor="middle">${esc(num(val))}</text>`
      + `<text x="${x + bw / 2}" y="${H - 28}" text-anchor="middle">${esc(nom)}</text>`
      + `<text x="${x + bw / 2}" y="${H - 12}" text-anchor="middle">${c.v[i] ? esc(pct(val / c.v[i])) + ' venta' : ''}</text>`;
  });
  return `<div class="cv-tarjeta"><h3>De consumo carta a sin explicar · S/</h3>${s}</svg></div>`;
}

// La evolución, debajo de las dos vistas. Dos pisos con los mismos períodos:
// arriba consumo carta y Sistema (la franja entre ellos es la diferencia);
// abajo esa diferencia partida en bajas y sin explicar, con la mediana.
function evolucion(st, w, c) {
  const esPct = st.metrica !== 'importe';
  const S = st.series;
  const n = w.per.length;
  const W = Math.max(640, Math.round((st.anchoGraf || 1000) - 30)), H = 340, L = 84, R = 20, T1 = 30, B1 = 186, T2 = 222, B2 = 300;
  const x = (i) => L + 36 + (n < 2 ? (W - L - R - 72) / 2 : (i * (W - L - R - 72)) / (n - 1));
  const u = (a) => (esPct ? a.map((v, i) => (c.v[i] ? v / c.v[i] : null)) : a);
  const carta = u(c.carta), pos = u(c.pos), bajas = u(c.bajas), falt = u(c.falt), dif = u(c.dif);
  const fmt = (v) => (v == null || !isFinite(v) ? '—' : esPct ? `${(v * 100).toFixed(1)}` : `${Math.round(v / 1000).toLocaleString('en-US')}k`);
  const ok = (v) => v != null && isFinite(v);
  const arriba = [...(S.carta ? carta : []), ...(S.pos ? pos : [])].filter(ok);
  let hi = arriba.length ? Math.max(...arriba) : 1, lo = arriba.length ? Math.min(...arriba) : 0;
  if (hi - lo < 1e-9) { hi += esPct ? 0.01 : 1000; lo -= esPct ? 0.01 : 1000; }
  const pad = (hi - lo) * 0.18; hi += pad; lo = Math.max(0, lo - pad);
  const y = (v) => T1 + ((hi - v) / (hi - lo)) * (B1 - T1);
  const abajo = [...bajas, ...dif, 0].filter(ok);
  const bhi = Math.max(...abajo) * 1.18 || 1, blo = Math.min(...abajo);
  const yb = (v) => T2 + ((bhi - v) / (bhi - blo || 1)) * (B2 - T2);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Evolución de consumo carta, costo del Sistema, bajas y sin explicar">`;
  for (let k = 0; k <= 3; k++) {
    const g = lo + ((hi - lo) * k) / 3;
    s += `<line x1="${L}" x2="${W - R}" y1="${y(g)}" y2="${y(g)}" class="cv-grilla"/><text x="${L - 8}" y="${y(g) + 4}" text-anchor="end">${esPct ? `${(g * 100).toFixed(0)}%` : `${Math.round(g / 1000)}k`}</text>`;
  }
  s += `<line x1="${L}" x2="${W - R}" y1="${yb(0)}" y2="${yb(0)}" class="cv-eje"/>`;
  s += `<text x="${L}" y="${T1 - 12}" class="t">Consumo carta y Sistema</text><text x="${L}" y="${T2 - 12}" class="t">La diferencia: bajas registradas + sin explicar</text>`;
  const isel = w.per.findIndex((p) => p.k === st.seleccionado);
  if (isel >= 0) s += `<rect x="${x(isel) - 36}" y="${T1 - 6}" width="72" height="${B2 - T1 + 12}" rx="8" class="cv-col-sel"/>`;
  if (S.brecha && S.carta && S.pos && carta.every(ok) && pos.every(ok)) {
    s += `<path class="cv-brecha" d="${carta.map((v, i) => `${i ? 'L' : 'M'}${x(i)} ${y(v)}`).join(' ')} ${pos.map((_, k) => `L${x(n - 1 - k)} ${y(pos[n - 1 - k])}`).join(' ')}Z"/>`;
  }
  const linea = (a, clase, etiqueta, debajo) => {
    let tramo = [], out = '';
    const cerrar = () => { if (tramo.length > 1) out += `<polyline class="cv-linea ${clase}" points="${tramo.join(' ')}"/>`; tramo = []; };
    a.forEach((v, i) => { if (!ok(v)) { cerrar(); return; } tramo.push(`${x(i)},${y(v)}`); }); cerrar();
    a.forEach((v, i) => {
      if (!ok(v)) return;
      out += `<circle class="cv-punto ${clase}" cx="${x(i)}" cy="${y(v)}" r="${i === isel ? 5.5 : 3.5}"/>`;
      if (etiqueta) out += `<text class="${debajo ? '' : 'v'}" x="${x(i)}" y="${y(v) + (debajo ? 18 : -10)}" text-anchor="middle">${fmt(v)}</text>`;
    });
    return out;
  };
  if (S.pos) s += linea(pos, 'sistema', true, true);
  if (S.carta) s += linea(carta, 'carta', true, false);
  if (S.barras) {
    const bw = Math.min(34, ((W - L - R) / n) * 0.45);
    w.per.forEach((p, i) => {
      if (!ok(bajas[i]) || !ok(dif[i])) return;
      const xx = x(i) - bw / 2, b0 = yb(0), b1 = yb(bajas[i]), d1 = yb(dif[i]);
      s += `<rect x="${xx}" y="${Math.min(b0, b1)}" width="${bw}" height="${Math.abs(b0 - b1)}" class="bajas"/>`
        + `<rect x="${xx}" y="${Math.min(b1, d1)}" width="${bw}" height="${Math.abs(b1 - d1)}" class="${c.raro[i] ? 'raro' : 'falt'}${falt[i] < 0 ? ' sobra' : ''}"/>`
        + `<text class="v${c.raro[i] ? ' raro' : ''}" x="${x(i)}" y="${Math.min(b1, d1, b0) - 5}" text-anchor="middle">${fmt(falt[i])}</text>`;
    });
    if (c.med != null) {
      const m = esPct ? c.med : (() => { const o = c.falt.filter(ok).sort((a, b) => a - b); const k = o.length; return k % 2 ? o[(k - 1) / 2] : (o[k / 2 - 1] + o[k / 2]) / 2; })();
      s += `<line x1="${L}" x2="${W - R}" y1="${yb(m)}" y2="${yb(m)}" class="cv-mediana"/><text x="${L - 8}" y="${yb(m) + 4}" text-anchor="end">mediana ${fmt(m)}</text>`;
    }
  }
  w.per.forEach((p, i) => {
    s += `<text x="${x(i)}" y="${H - 14}" text-anchor="middle" class="${i === isel ? 'sel' : ''}">${esc(p.rot)}${c.raro[i] ? ' ⚠' : ''}</text>`
      + `<rect class="cv-hit" data-seleccionar="${esc(p.k)}" data-i="${i}" x="${x(i) - Math.min(46, (W - L - R) / n / 2)}" y="${T1 - 14}" width="${Math.min(92, (W - L - R) / n)}" height="${H - T1}"/>`;
  });
  s += '</svg>';
  const chip = (k, nom, clase) => `<button type="button" class="cv-serie" data-serie="${k}" aria-pressed="${!!S[k]}"><i class="${clase}"></i>${nom}</button>`;
  return `<div class="cv-tarjeta cv-evo"><div class="cv-evo-cab"><h3>Evolución</h3><div class="cv-evo-ctrl">
      <div class="modo" role="group" aria-label="Medida del gráfico"><button type="button" data-metrica="porcentaje" aria-pressed="${esPct}">% de venta</button><button type="button" data-metrica="importe" aria-pressed="${!esPct}">S/</button></div>
      ${chip('carta', 'Consumo carta', 'carta')}${chip('pos', 'Costo del Sistema', 'sistema')}${chip('brecha', 'Diferencia', 'brecha')}${chip('barras', 'Bajas y sin explicar', 'falt')}
    </div></div><div class="cv-evo-graf">${s}</div>
    <p class="cv-nota-corta">Pasa el cursor por un período para ver sus cifras; un clic lo elige. ⚠ marca el que duplica la mediana de lo sin explicar.</p>
    <div class="cv-tip" hidden></div></div>`;
}

function ficha(st, i) {
  const c = st.evo.c, p = st.evo.per[i];
  const f = (nom, v, t, clase) => `<div class="r"><span>${clase ? `<i class="${clase}"></i>` : ''}${nom}</span><b>${num(v)}${t == null ? '' : ` · ${pct(t)}`}</b></div>`;
  return `<div class="h">${esc(p.rot)}${p.sub ? ` · ${esc(p.sub)}` : ''}</div>${f('Venta', c.v[i])}${f('Consumo carta', c.carta[i], c.tc[i], 'carta')}`
    + `${f('Costo del Sistema', c.pos[i], c.tp[i], 'sistema')}${f('Diferencia', c.dif[i])}${f('Bajas registradas', c.bajas[i], null, 'bajas')}`
    + `${f('Sin explicar', c.falt[i], c.tf[i], c.raro[i] ? 'raro' : 'falt')}<div class="pie">Clic para elegir este período</div>`;
}

// Las pestañas de abajo. En Cascada, la primera es la tabla.
function pestanas(st, tablaHtml, cuerpos) {
  const lista = [...(st.vista === 'cascada' ? [['tabla', 'Tabla por período']] : []),
    ['comercial', 'Margen y descuentos'], ['calculo', 'Cómo se calcula'], ['referencias', 'Referencias Inforest y alcance']];
  if (!lista.some(([k]) => k === st.pestana)) st.pestana = lista[0][0];
  const cuerpo = st.pestana === 'tabla' ? tablaHtml : `<div class="cv-pestana-cuerpo">${cuerpos[st.pestana]}</div>`;
  return `<div class="cv-tarjeta cv-pestanas"><div class="cv-tabs" role="tablist">${lista.map(([k, nom]) =>
    `<button type="button" role="tab" data-pestana="${k}" aria-selected="${st.pestana === k}">${nom}</button>`).join('')}</div>${cuerpo}</div>`;
}
