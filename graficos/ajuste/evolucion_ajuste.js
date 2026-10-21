// Ajuste › Evolución (regla #692): la serie, el panel del período y, abajo,
// la matriz familia × mes, «¿Es mucho?» y la tabla de resumen.
//
// La monta graficos/ajuste/_evolucion.py::vista_evolucion_ajuste con
// st.components.v2 (sin iframe, estilos en un shadow root). Es el boceto
// aprobado (https://claude.ai/artifact/TNvQPfrb4Ty7RQVHvUtPjF): abre en rojo
// y verde, y «Explicar con» suma de a uno los posibles orígenes —a pedido,
// «que los colores no se muestren todos a la vez»—.
//
// Python manda en `data` los números en soles (`datos_pieza`). Todo lo que
// se elige acá —el mes, los orígenes, la familia abierta, el modo de la
// matriz, el hueco de abajo— es del navegador y no cuesta una corrida. A
// Python le llega una sola cosa, el trigger «pedir» ({que, t}), cuando hace
// falta un dato caro que todavía no está: los posibles orígenes (la cuenta
// de «Análisis de diferencias», ~30 s por sesión la primera vez) o el
// consumo de cada mes (la cuenta de Costos).

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const sum = (a) => a.reduce((x, y) => x + (y || 0), 0);
const hay = (v) => v !== null && v !== undefined && !Number.isNaN(v);

// «+45.1k», «−830»: el monto corto, con el signo siempre escrito.
function fk(v) {
  if (!hay(v)) return '—';
  const a = Math.abs(v);
  const sg = v < -0.5 ? '−' : v > 0.5 ? '+' : '';
  return sg + (a >= 1000 ? (a / 1000).toFixed(1) + 'k' : String(Math.round(a)));
}
const soles = (v) => (hay(v) ? 'S/ ' + fk(v) : '—');
function pc(v) {
  if (!hay(v)) return '—';
  const a = Math.abs(v);
  return (v > 0.05 ? '+' : v < -0.05 ? '−' : '') + a.toFixed(a < 10 ? 1 : 0).replace('.', ',') + ' %';
}

const NOM = {
  sin: 'Sin pista', neg: 'Sistema en negativo', ven: 'Descargo de ventas',
  pro: 'Producción y porcionamiento', reg: 'Registro, traslado o código',
};
// El botón lleva el nombre corto (los cuatro en un renglón a 1323 de
// ancho); la leyenda y el panel, el largo, y el botón lo dice al pasar.
const CORTO = { neg: 'Sistema en negativo', ven: 'Ventas', pro: 'Producción', reg: 'Registro o traslado' };
const CHIPS = ['neg', 'ven', 'pro', 'reg'];
const CARO = ['ven', 'pro', 'reg'];

// Las partes de un período: el sobrante y el faltante partidos por posible
// origen. «Sin pista» es lo que queda por diferencia, así las partes suman
// siempre lo mismo que la barra.
function partes(d, i) {
  const p = d.periodos[i];
  const S = p.s || 0, F = p.f || 0;
  const o = d.origen && d.origen[i];
  const par = (k) => (o && o[k] ? o[k] : [0, 0]);
  const neg = Math.min(d.neg[i] || 0, S);
  const s = { neg, ven: par('ven')[0], pro: par('pro')[0], reg: par('reg')[0] };
  const f = { ven: par('ven')[1], pro: par('pro')[1], reg: par('reg')[1] };
  s.sin = Math.max(0, S - s.neg - s.ven - s.pro - s.reg);
  f.sin = Math.min(0, F - f.ven - f.pro - f.reg);
  return { s, f };
}

function colorDe(d, o, lado) {
  if (o === 'sin') return lado === 's' ? d.col.pos : d.col.neg;
  return o === 'neg' ? d.col.gneg : d.col[o];
}

// Cuál origen está a la vista: prendido, y con su dato ya calculado.
function visible(ui, d, o) {
  return !!ui.on[o] && (o === 'neg' || d.origen_estado === 'listo');
}

function mediana(xs) {
  const a = xs.filter(hay).sort((x, y) => x - y);
  if (!a.length) return null;
  const m = Math.floor(a.length / 2);
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
}

// ── la serie ────────────────────────────────────────────────────────────
function htmlSerie(d, ui) {
  const H = d.alto.graf, padT = 18, padB = 18;
  const P = d.periodos;
  const maxS = Math.max(1, ...P.map((p) => p.s || 0));
  const maxF = Math.max(1, ...P.map((p) => -(p.f || 0)));
  const K = (H - padT - padB) / (maxS + maxF);
  const TOP = padT + maxS * K;
  const ifoco = P.findIndex((p) => p.k === ui.foco);
  const netos = P.map((p) => p.n);
  const conN = netos.map((n, i) => [n, i]).filter(([n]) => hay(n));
  const iMin = conN.length ? conN.reduce((a, b) => (b[0] < a[0] ? b : a))[1] : -1;
  const iMax = conN.length ? conN.reduce((a, b) => (b[0] > a[0] ? b : a))[1] : -1;
  const cons = d.consumo_estado === 'listo' ? d.consumo : null;
  const fuera = (i) => cons && hay(cons.pct[i]) && hay(cons.ci) && (cons.pct[i] < cons.ci || cons.pct[i] > cons.cs);
  const n = P.length;
  let cols = '', pts = [], kpts = [];
  P.forEach((p, i) => {
    const x = ((i + 0.5) / n) * 100;
    const pa = partes(d, i);
    const restoS = pa.s.sin + CHIPS.filter((o) => !visible(ui, d, o)).reduce((a, o) => a + (pa.s[o] || 0), 0);
    const restoF = pa.f.sin + CARO.filter((o) => !visible(ui, d, o)).reduce((a, o) => a + (pa.f[o] || 0), 0);
    const sup = ['neg', 'ven', 'pro', 'reg'].filter((o) => visible(ui, d, o))
      .map((o) => [pa.s[o], colorDe(d, o, 's')]).concat([[restoS, d.col.pos]]).filter(([v]) => v * K >= 0.6);
    const inf = [[-restoF, d.col.neg]].concat(['reg', 'pro', 'ven'].filter((o) => visible(ui, d, o)).reverse()
      .map((o) => [-pa.f[o], colorDe(d, o, 'f')])).filter(([v]) => v * K >= 0.6);
    const apag = ifoco >= 0 && ifoco !== i;
    let barras = `<div class="sup" style="bottom:${H - TOP}px">` +
      sup.map(([v, c]) => `<i style="height:${(v * K).toFixed(1)}px;background:${c}"></i>`).join('') + '</div>' +
      `<div class="inf" style="top:${TOP}px">` +
      inf.map(([v, c]) => `<i style="height:${(v * K).toFixed(1)}px;background:${c}"></i>`).join('') + '</div>';
    if (hay(p.n)) {
      const y = TOP - p.n * K;
      pts.push(`${x.toFixed(2)},${y.toFixed(1)}`);
      barras += `<b class="pto" style="top:${(y - 4).toFixed(1)}px"></b>`;
      if (i === ifoco || i === iMin || i === iMax || fuera(i)) {
        barras += `<span class="rot ${p.n < 0 ? 'neg' : 'pos'}" style="top:${(p.n < 0 ? y + 7 : y - 22).toFixed(1)}px">${soles(p.n)}</span>`;
      }
    }
    if (d.kardex && hay(p.kx)) {
      const yk = TOP - p.kx * K;
      kpts.push(`${x.toFixed(2)},${yk.toFixed(1)}`);
      if (p.dkx) barras += `<b class="kx" style="top:${(yk - 3).toFixed(1)}px"></b>`;
    }
    const tip = [p.eje, hay(p.n) ? `Sobrante ${soles(p.s)} · Faltante ${soles(p.f)} · Neto ${soles(p.n)}` : 'Sin conteo']
      .concat(d.kardex && hay(p.n) ? [`Kardex: ${!hay(p.kx) ? 'sin dato' : p.dkx ? soles(p.kx) + ' · difiere' : 'igual'}`] : [])
      .concat(hay(p.contado) ? [`Valor contado: ${soles(p.contado)}`] : []).join('\n');
    cols += `<button type="button" class="col${i === ifoco ? ' foco' : ''}${apag ? ' apag' : ''}" data-act="mes" data-arg="${i}"` +
      ` aria-pressed="${i === ifoco}" title="${esc(tip)}">${barras}</button>`;
  });
  // Con muchos cortes («16-18 ago 26» mide ~75 px) los rótulos se pisan: uno
  // de cada `paso`, más el último y el elegido, como `_marcas_eje` del
  // gráfico de Plotly que esto reemplazó. El de cada columna, al pasar.
  const paso = Math.max(1, Math.ceil(n / 12));
  const ejes = P.map((p, i) => `<span class="${i === ifoco ? 'foco' : ''}">${
    i % paso === 0 || i === n - 1 || i === ifoco ? esc(p.eje) : ''}</span>`).join('');
  return `<div class="serie" style="height:${H + 18}px">` +
    `<div class="cero" style="top:${TOP}px"></div>` +
    `<div class="cols" style="height:${H}px">${cols}</div>` +
    `<svg class="linea" viewBox="0 0 100 ${H}" preserveAspectRatio="none" style="height:${H}px" aria-hidden="true">` +
    (kpts.length > 1 ? `<polyline class="kx" points="${kpts.join(' ')}"/>` : '') +
    (pts.length > 1 ? `<polyline points="${pts.join(' ')}"/>` : '') + '</svg>' +
    `<div class="ejes${n > 14 ? ' apretado' : ''}">${ejes}</div></div>`;
}

// ── «Explicar con» y la leyenda ─────────────────────────────────────────
function htmlExplicar(d, ui) {
  const P = d.periodos;
  const sobTot = sum(P.map((p) => p.s)), negTot = sum(d.neg);
  const cargando = d.origen_estado !== 'listo' && CARO.some((o) => ui.on[o]);
  const monto = (o) => {
    if (o === 'neg') return soles(negTot);
    if (d.origen_estado !== 'listo') return '';
    return soles(sum(P.map((p, i) => partes(d, i).f[o])));
  };
  const chips = CHIPS.map((o) => {
    const on = !!ui.on[o];
    const sw = on ? colorDe(d, o, 's') : 'transparent';
    return `<button type="button" class="chip${on ? ' on' : ''}" data-act="chip" data-arg="${o}" aria-pressed="${on}" title="${esc(NOM[o])}">` +
      `<i style="background:${sw}"></i>${CORTO[o]}<span class="m">${monto(o)}</span></button>`;
  }).join('');
  const algo = CHIPS.some((o) => ui.on[o]);
  const pct = sobTot > 0 ? Math.round((100 * negTot) / sobTot) : 0;
  const inv = !ui.on.neg && negTot > 0
    ? `<button type="button" class="inv" data-act="chip" data-arg="neg">${pct} % del sobrante es sistema en negativo · ver</button>` : '';
  const leyenda = [[algo ? 'Sobrante sin explicar' : 'Sobrante', d.col.pos], [algo ? 'Faltante sin explicar' : 'Faltante', d.col.neg]]
    .concat(CHIPS.filter((o) => visible(ui, d, o)).map((o) => [NOM[o], colorDe(d, o, 's')]))
    .map(([t, c]) => `<span><i style="background:${c}"></i>${esc(t)}</span>`).join('') +
    '<span><i class="raya"></i>Neto</span>' +
    (d.kardex ? `<span title="${esc(d.ayuda_kx)}"><i class="puntos"></i>Kardex</span>` : '');
  return '<div class="explicar"><div class="chips" role="group" aria-label="Explicar con">' +
    '<span class="tit">Explicar con</span>' +
    '<span class="prueba" title="Las pistas son posibles orígenes: la cuenta todavía está aprendiendo.">en prueba</span>' +
    chips + (algo ? '<button type="button" class="quitar" data-act="quitar">Quitar</button>' : '') +
    (cargando ? '<span class="carga">calculando los orígenes…</span>' : '') + inv + '</div>' +
    `<div class="leyenda">${leyenda}</div></div>`;
}

// ── el panel del período ────────────────────────────────────────────────
function htmlPanel(d, ui) {
  const P = d.periodos;
  const i = P.findIndex((p) => p.k === ui.foco);
  const idx = i >= 0 ? [i] : P.map((_, j) => j);
  const tot = (fn) => sum(idx.map(fn));
  const S = tot((j) => P[j].s), F = tot((j) => P[j].f), N = S + F;
  const ps = idx.map((j) => partes(d, j));
  const ss = (o) => sum(ps.map((x) => x.s[o])), ff = (o) => sum(ps.map((x) => x.f[o]));
  const conOrigen = d.origen_estado === 'listo';
  // Sin los orígenes calculados, «sin pista» no es eso: es lo demás.
  const nombre = (o) => (o === 'sin' && !conOrigen ? 'Lo demás' : NOM[o]);
  const fila = (o, v, lado) => `<span class="o"><i style="background:${colorDe(d, o, lado)}"></i>${nombre(o)}</span><span class="v">${soles(v)}</span>`;
  const falt = conOrigen ? ['sin', 'reg', 'pro', 'ven'].map((o) => fila(o, ff(o), 'f')).join('') : '';
  const sobr = ['sin', 'neg'].concat(conOrigen ? ['reg', 'pro', 'ven'] : []).map((o) => fila(o, ss(o), 's')).join('');
  // La familia que más pesa y cuánto se movió.
  let frase = '';
  if (d.familias.length) {
    const fam = d.familias.map((f) => {
      const n = sum(idx.map((j) => (f.s[j] || 0) + (f.f[j] || 0)));
      const m = sum(idx.map((j) => (f.s[j] || 0) - (f.f[j] || 0)));
      return [f.nombre, n, m];
    }).reduce((a, b) => (Math.abs(b[1]) > Math.abs(a[1]) ? b : a));
    frase = `${esc(fam[0])} pesa más: neto ${soles(fam[1])} sobre ${soles(fam[2]).replace('+', '')} movidos.`;
  }
  // Del valor del sistema: el cierre del mes (o la sesión), o todos juntos.
  let sis = '';
  const T = d.sistema && d.sistema.TOTAL;
  if (T) {
    const cs = idx.map((j) => T[j]).filter(Boolean);
    if (cs.length) {
      const c = [0, 1, 2, 3, 4].map((m) => sum(cs.map((x) => x[m])));
      const base = (i < 0 ? `${cs.length} ${d.gran === 'Mes' ? 'cierres' : 'sesiones'} · ` : d.gran === 'Mes' ? 'cierre · ' : '') +
        `el sistema decía ${soles(c[0]).replace('+', '')}`;
      sis = '<div class="sis"><div class="cab"><span>DEL VALOR DEL SISTEMA</span>' +
        `<b class="${c[1] + c[2] < 0 ? 'neg' : 'pos'}">${c[0] > 0 ? pc((100 * (c[1] + c[2])) / c[0]) : '—'}</b></div>` +
        `<div class="base">${esc(base)}</div>` + (c[0] > 0
        ? '<div class="g">' +
          `<span>Faltante</span><span class="v neg">${pc((100 * c[1]) / c[0])}</span>` +
          `<span class="sub">de eso, contado en cero</span><span class="v">${pc((100 * c[3]) / c[0])}</span>` +
          `<span>Sobrante</span><span class="v pos">${pc((100 * c[2]) / c[0])}</span>` +
          '<span class="sub" title="Productos que el sistema tenía en cero o en negativo: no entran en la base, porque no hay un porcentaje de algo negativo.">Aparte: en negativo</span>' +
          `<span class="v">${soles(c[4])}</span></div>` : '') + '</div>';
    } else if (i >= 0) {
      sis = `<div class="sis"><div class="cab"><span>DEL VALOR DEL SISTEMA</span><b>—</b></div><div class="base">${d.gran === 'Mes' ? 'sin cierre en este mes' : 'sin dato'}</div></div>`;
    }
  }
  const cons = d.consumo_estado === 'listo' ? d.consumo : null;
  const pctC = cons && i >= 0 && hay(cons.pct[i]) ? `<div class="consumo">del consumo del mes <b>${pc(cons.pct[i])}</b></div>` : '';
  const titulo = i >= 0 ? P[i].eje : `Los ${P.length} ${d.gran === 'Mes' ? 'meses' : 'cortes'}`;
  return '<aside class="panel" aria-label="Detalle del período">' +
    `<div class="cab"><h3>${esc(titulo)}</h3>` +
    (i >= 0 ? '<button type="button" class="soltar" data-act="soltar">Ver todos</button>' : '') + '</div>' +
    `<div class="neto ${N < 0 ? 'neg' : 'pos'}">${soles(N)}</div>${pctC}` +
    (frase ? `<div class="frase">${frase}</div>` : '') +
    `<div class="g"><span class="t">FALTANTE</span><span class="v t">${soles(F)}</span>${falt}` +
    `<span class="t sep">SOBRANTE</span><span class="v t sep">${soles(S)}</span>${sobr}</div>` +
    (conOrigen ? '' : '<div class="nota">Los demás orígenes salen al prenderlos en «Explicar con».</div>') +
    sis + '</aside>';
}

// ── la matriz familia × período ─────────────────────────────────────────
function heat(v, max) {
  if (!hay(v) || Math.abs(v) < 0.5) return 'var(--bg-primary)';
  const a = (0.1 + (0.55 * Math.abs(v)) / max).toFixed(2);
  return v < 0 ? `rgb(var(--ev-neg-rgb) / ${a})` : `rgb(var(--ev-pos-rgb) / ${a})`;
}

function htmlMatriz(d, ui) {
  const P = d.periodos, n = P.length;
  const ifoco = P.findIndex((p) => p.k === ui.foco);
  const modo = ui.modo === 'pct' && d.sistema && d.sistema.TOTAL ? 'pct' : 'soles';
  const filas = d.familias.map((f) => ({ id: f.id, nombre: f.nombre, s: f.s, f: f.f }));
  filas.push({
    id: 'TOTAL', nombre: 'Total', total: true,
    s: P.map((_, j) => (d.familias.some((f) => hay(f.s[j])) ? sum(d.familias.map((f) => f.s[j])) : null)),
    f: P.map((_, j) => (d.familias.some((f) => hay(f.f[j])) ? sum(d.familias.map((f) => f.f[j])) : null)),
  });
  const marco = (j) => (j === ifoco ? ' foco' : '');
  let h = '<div class="mz" style="--mz-n:' + n + ';min-width:' + (226 + n * 54) + 'px">';
  h += '<span></span>' + P.map((p, j) => `<span class="h${marco(j)}">${esc(p.eje)}</span>`).join('') + `<span class="h r">${n} ${d.gran === 'Mes' ? 'meses' : 'cortes'}</span>`;
  filas.forEach((r, fi) => {
    const abre = ui.abierta === r.id;
    let vals, tot, tip, fmt;
    if (modo === 'pct') {
      const sis = (d.sistema[r.id] || P.map(() => null));
      vals = sis.map((c) => (c && c[0] > 0 ? (100 * (c[1] + c[2])) / c[0] : null));
      const cs = sis.filter(Boolean);
      const T = [0, 1, 2, 3, 4].map((m) => sum(cs.map((x) => x[m])));
      tot = T[0] > 0 ? (100 * (T[1] + T[2])) / T[0] : null;
      fmt = pc;
      tip = (j) => (sis[j] ? `${r.nombre} · ${P[j].eje}: el sistema decía ${soles(sis[j][0]).replace('+', '')} y se ajustó ${pc(vals[j])}` : `${r.nombre} · ${P[j].eje}: ${d.gran === 'Mes' ? 'sin cierre' : 'sin dato'}`);
    } else {
      vals = P.map((_, j) => (hay(r.s[j]) || hay(r.f[j]) ? (r.s[j] || 0) + (r.f[j] || 0) : null));
      tot = sum(vals);
      fmt = fk;
      tip = (j) => `${r.nombre} · ${P[j].eje}: sobró ${soles(r.s[j])}, faltó ${soles(r.f[j])}, neto ${soles(vals[j])}`;
    }
    const max = Math.max(1, ...vals.filter(hay).map(Math.abs));
    h += `<button type="button" class="fam${r.total ? ' total' : ''}${abre ? ' abierta' : ''}" data-act="fam" data-arg="${esc(r.id)}" aria-expanded="${abre}">` +
      `<span class="fl" aria-hidden="true">${abre ? '▾' : '▸'}</span><span class="nm">${esc(r.nombre)}</span></button>`;
    h += vals.map((v, j) => {
      const ver = hay(v) && (abre || Math.abs(v) >= 0.6 * max);
      return `<span class="c${marco(j)}${r.total ? ' total' : ''}" style="background:${heat(v, max)}" title="${esc(tip(j))}">` +
        (ver ? `<b class="${v < 0 ? 'neg' : 'pos'}">${fmt(v)}</b>` : '') + '</span>';
    }).join('');
    h += `<span class="c tot${r.total ? ' total' : ''}"><b class="${hay(tot) && tot < 0 ? 'neg' : 'pos'}">${fmt(tot)}</b></span>`;
    if (abre) h += subfilas(d, r, modo, marco, fi);
  });
  return h + '</div>';
}

function subfilas(d, r, modo, marco) {
  const P = d.periodos;
  const fila = (nom, cls, barra, vals, tot, fmt, max) => `<span class="sn ${cls}">${nom}</span>` +
    vals.map((v, j) => `<span class="sc${marco(j)}"><span class="${cls}">${hay(v) ? fmt(v) : ''}</span>` +
      `<i style="width:${hay(v) ? Math.max(3, (100 * Math.abs(v)) / max) : 0}%;background:${barra}"></i></span>`).join('') +
    `<span class="sc tot"><span class="${cls}">${hay(tot) ? fmt(tot) : ''}</span>` +
    `<i style="width:${hay(tot) ? Math.min(100, (100 * Math.abs(tot)) / Math.max(max * P.length, 1)) : 0}%;background:${barra}"></i></span>`;
  if (modo === 'pct') {
    const sis = d.sistema[r.id] || P.map(() => null);
    const parte = (m) => sis.map((c) => (c && c[0] > 0 ? (100 * c[m]) / c[0] : null));
    const cs = sis.filter(Boolean);
    const T = [0, 1, 2, 3, 4].map((m) => sum(cs.map((x) => x[m])));
    const tp = (m) => (T[0] > 0 ? (100 * T[m]) / T[0] : null);
    const F = parte(1);
    const max = Math.max(1, ...F.filter(hay).map(Math.abs));
    const NG = sis.map((c) => (c ? c[4] : null));
    const maxNG = Math.max(1, ...NG.filter(hay).map(Math.abs));
    return fila('Faltante', 'neg', d.col.neg, F, tp(1), pc, max) +
      fila('de eso, en cero', 'cero', d.col.neg + '88', parte(3), tp(3), pc, max) +
      fila('Sobrante', 'pos', d.col.pos, parte(2), tp(2), pc, max) +
      fila('En negativo (S/)', 'gris', d.col.gneg, NG, T[4], fk, maxNG);
  }
  const mov = P.map((_, j) => (hay(r.s[j]) || hay(r.f[j]) ? (r.s[j] || 0) - (r.f[j] || 0) : null));
  const max = Math.max(1, ...mov.filter(hay));
  const abs = (v) => (hay(v) ? (Math.abs(v) >= 1000 ? (Math.abs(v) / 1000).toFixed(1) + 'k' : String(Math.round(Math.abs(v)))) : '');
  return fila('Sobrante', 'pos', d.col.pos, r.s, sum(r.s), fk, max) +
    fila('Faltante', 'neg', d.col.neg, r.f, sum(r.f), fk, max) +
    fila('Se movió', 'gris', d.col.gneg, mov, sum(mov), abs, max);
}

// ── «¿Es mucho?» ────────────────────────────────────────────────────────
function htmlEsMucho(d, ui) {
  if (d.consumo_estado === 'no') return '<div class="aviso">Calculando el consumo de cada mes…</div>';
  if (d.consumo_estado !== 'listo') return `<div class="aviso">${esc(d.consumo_nota || 'Sin dato del consumo.')}</div>`;
  const c = d.consumo, P = d.periodos, n = P.length;
  const H = d.alto.abajo - 30, pad = 14;
  const vals = c.pct.filter(hay);
  if (!vals.length) return '<div class="aviso">Ningún mes del rango tiene consumo calculado (hace falta el cierre del mes y el del anterior).</div>';
  const banda = hay(c.ci);
  const hi = Math.max(...vals, banda ? c.cs : 0, 0) + 4, lo = Math.min(...vals, banda ? c.ci : 0, 0) - 4;
  const py = (v) => pad + ((hi - v) / (hi - lo)) * (H - 2 * pad);
  const ifoco = P.findIndex((p) => p.k === ui.foco);
  let h = `<div class="mucho" style="height:${H + 16}px">`;
  if (banda) {
    h += `<div class="bf" style="top:${py(c.cs)}px;height:${py(c.ci) - py(c.cs)}px"></div>` +
      `<div class="bh" style="top:${py(c.q3)}px;height:${py(c.q1) - py(c.q3)}px"></div>` +
      `<div class="med" style="top:${py(c.med)}px"></div>`;
  }
  h += `<div class="cero" style="top:${py(0)}px"></div><span class="c0" style="top:${py(0) - 7}px">0 %</span>`;
  const pts = [];
  let cols = '';
  P.forEach((p, i) => {
    const v = c.pct[i];
    const x = ((i + 0.5) / n) * 100;
    let dentro = '';
    if (hay(v)) {
      const y = py(v);
      pts.push(`${x.toFixed(2)},${y.toFixed(1)}`);
      const antes = p.k < c.banda_desde;
      const fuera = banda && !antes && (v < c.ci || v > c.cs);
      const tip = antes ? `${p.eje}: ${pc(v)} · antes de setiembre 2025 el ajuste del cierre no es el del kardex (regla #612): no entra en la banda` : `${p.eje}: ${pc(v)} del consumo`;
      dentro = `<b class="pto${fuera ? ' fuera' : ''}${antes ? ' antes' : ''}" style="top:${y - 4}px" title="${esc(tip)}"></b>` +
        `<span class="rot${fuera ? ' fuera' : ''}" style="top:${hay(c.med) && v < c.med ? y + 7 : y - 20}px">${fuera ? '⚠ ' : ''}${pc(v)}</span>`;
    } else {
      dentro = `<span class="vacio" style="top:${H / 2 - 6}px">${i === n - 1 ? 'en curso' : 'sin cierre'}</span>`;
    }
    cols += `<div class="mc${i === ifoco ? ' foco' : ''}${ifoco >= 0 && i !== ifoco ? ' apag' : ''}">${dentro}<span class="eje">${esc(p.eje)}</span></div>`;
  });
  h += `<svg viewBox="0 0 100 ${H + 16}" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts.join(' ')}"/></svg>`;
  return h + `<div class="mcols">${cols}</div></div>`;
}

// ── la tabla de resumen ─────────────────────────────────────────────────
function htmlTabla(d, ui) {
  const P = d.periodos;
  const td = (v, cls = '') => `<td class="n ${cls}">${hay(v) ? 'S/ ' + Math.round(v).toLocaleString('en-US') : '—'}</td>`;
  const kx = (p) => (!d.kardex ? '' : !hay(p.kx) ? '<td class="n suave" title="Sin dato del kardex">—</td>'
    : p.dkx ? `<td class="n alerta" title="Difiere del neto en S/ ${Math.round(p.kx - (p.n || 0)).toLocaleString('en-US')}">S/ ${Math.round(p.kx).toLocaleString('en-US')}</td>`
      : `<td class="n suave" title="Igual al neto">S/ ${Math.round(p.kx).toLocaleString('en-US')}</td>`);
  const filas = P.slice().reverse().map((p) => `<tr class="${p.k === ui.foco ? 'foco' : ''}">` +
    `<td>${esc(p.eje)}${hay(p.n) ? '' : ' <span class="suave">sin conteo</span>'}</td>` +
    td(p.s, 'pos') + td(p.f, 'neg') + td(p.n, 'neto') + kx(p) + td(p.contado, 'suave') + '</tr>').join('');
  const T = (k) => sum(P.map((p) => p[k]));
  return '<div class="tabla"><table><thead><tr><th>Período</th><th class="n">Sobrante</th><th class="n">Faltante</th><th class="n">Neto</th>' +
    (d.kardex ? `<th class="n" title="${esc(d.ayuda_kx)}">Kardex</th>` : '') +
    '<th class="n" title="Stock declarado × precio de lo que se contó. Contexto: en un mes con varias sesiones cuenta el stock más de una vez">Valor contado</th></tr></thead>' +
    `<tbody>${filas}</tbody><tfoot><tr><td>Total del rango</td>${td(T('s'), 'pos')}${td(T('f'), 'neg')}${td(T('n'), 'neto')}` +
    (d.kardex ? '<td></td>' : '') + `${td(T('contado'), 'suave')}</tr></tfoot></table></div>`;
}

// ── el hueco de abajo ───────────────────────────────────────────────────
function htmlAbajo(d, ui) {
  const tabs = [];
  if (d.familias.length) tabs.push(['fam', d.gran === 'Mes' ? 'Familia × mes' : 'Familia × corte']);
  tabs.push(['pct', '¿Es mucho?'], ['tabla', 'Tabla']);
  if (!tabs.some(([k]) => k === ui.abajo)) ui.abajo = tabs[0][0];
  const sel = tabs.map(([k, t]) => `<button type="button" data-act="abajo" data-arg="${k}" aria-pressed="${ui.abajo === k}" class="${ui.abajo === k ? 'on' : ''}">${t}</button>`).join('');
  let extra = '', cuerpo = '';
  if (ui.abajo === 'fam') {
    const modos = d.sistema && d.sistema.TOTAL
      ? '<span class="seg mini" role="group" aria-label="Medir la matriz">' + [['soles', 'En soles'], ['pct', '% del sistema']].map(([k, t]) =>
        `<button type="button" data-act="modo" data-arg="${k}" aria-pressed="${ui.modo === k}" class="${ui.modo === k ? 'on' : ''}">${t}</button>`).join('') + '</span>' : '';
    const txt = ui.modo === 'pct' ? 'ajuste ÷ lo que el sistema decía · sin productos en negativo' : 'color = neto · la cifra, sólo donde se sale de lo normal';
    extra = `${modos}<span class="ayuda">${txt} · clic en una familia</span>`;
    cuerpo = `<div class="mz-marco">${htmlMatriz(d, ui)}</div>`;
  } else if (ui.abajo === 'pct') {
    const c = d.consumo_estado === 'listo' ? d.consumo : null;
    extra = c && hay(c.ci)
      ? '<span class="ayuda"><i class="bh"></i>lo habitual <i class="bf"></i>todavía normal <i class="med"></i>mediana ' + pc(c.med) +
        ' · el neto como % del consumo operativo del mes</span>'
      : '<span class="ayuda">el neto como % del consumo operativo del mes</span>';
    cuerpo = htmlEsMucho(d, ui);
  } else {
    extra = `<span class="ayuda">del más nuevo al más viejo${d.nota_kx ? ' · ' + d.nota_kx : ''}</span>`;
    cuerpo = htmlTabla(d, ui);
  }
  return `<div class="abajo"><div class="cab"><span class="seg" role="group" aria-label="Debajo de la serie">${sel}</span>${extra}</div>` +
    `<div class="hueco" style="height:${d.alto.abajo}px">${cuerpo}</div></div>`;
}

// ── dibujar y escuchar ──────────────────────────────────────────────────
function dibujar(raiz) {
  const { data: d, ui } = raiz.__st;
  if (ui.foco && !d.periodos.some((p) => p.k === ui.foco)) ui.foco = null;
  if (ui.abierta && !(ui.abierta === 'TOTAL' || d.familias.some((f) => f.id === ui.abierta))) ui.abierta = null;
  const hex = (c) => { const m = /^#?([0-9a-f]{6})$/i.exec(c || ''); if (!m) return '0 0 0'; const n = parseInt(m[1], 16); return `${n >> 16} ${(n >> 8) & 255} ${n & 255}`; };
  raiz.style.setProperty('--ev-pos', d.col.pos);
  raiz.style.setProperty('--ev-neg', d.col.neg);
  raiz.style.setProperty('--ev-pos-rgb', hex(d.col.pos));
  raiz.style.setProperty('--ev-neg-rgb', hex(d.col.neg));
  raiz.style.setProperty('--ev-post', d.col.post);
  raiz.style.setProperty('--ev-negt', d.col.negt);
  raiz.style.setProperty('--ev-alerta', d.col.alerta);
  const mz = raiz.querySelector('.mz-marco');
  const scroll = mz ? [mz.scrollTop, mz.scrollLeft] : null;
  raiz.innerHTML = '<div class="cuerpo"><div class="izq">' + htmlExplicar(d, ui) + htmlSerie(d, ui) + '</div>' +
    htmlPanel(d, ui) + htmlAbajo(d, ui) + '</div>';
  const mz2 = raiz.querySelector('.mz-marco');
  if (mz2 && scroll) { mz2.scrollTop = scroll[0]; mz2.scrollLeft = scroll[1]; }
  // Lo caro se pide UNA vez por montaje: al llegar, Python lo deja en `data`.
  if (ui.abajo === 'pct' && d.consumo_estado === 'no' && !ui.pidioConsumo) {
    ui.pidioConsumo = true;
    raiz.__st.enviar('consumo');
  }
  if (d.origen_estado !== 'listo' && CARO.some((o) => ui.on[o]) && !ui.pidioOrigen) {
    ui.pidioOrigen = true;
    raiz.__st.enviar('origen');
  }
}

function enlazar(raiz) {
  raiz.addEventListener('click', (e) => {
    const b = e.target.closest('[data-act]');
    if (!b) return;
    const { ui } = raiz.__st;
    const arg = b.dataset.arg;
    switch (b.dataset.act) {
      case 'mes': {
        const k = raiz.__st.data.periodos[Number(arg)].k;
        ui.foco = ui.foco === k ? null : k;
        break;
      }
      case 'soltar': ui.foco = null; break;
      case 'chip': ui.on = { ...ui.on, [arg]: !ui.on[arg] }; break;
      case 'quitar': ui.on = {}; break;
      case 'abajo': ui.abajo = arg; break;
      case 'modo': ui.modo = arg; break;
      case 'fam': ui.abierta = ui.abierta === arg ? null : arg; break;
      default: return;
    }
    dibujar(raiz);
  });
}

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  let raiz = parentElement.querySelector('.ev');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'ev';
    parentElement.appendChild(raiz);
    raiz.__st = { ui: { foco: null, on: {}, abajo: 'fam', abierta: null, modo: 'soles' } };
    enlazar(raiz);
  }
  raiz.__st.data = { periodos: [], familias: [], neg: [], sistema: {}, col: {}, alto: { graf: 186, abajo: 172 }, ...(data || {}) };
  // Un sello por pedido: el mismo pedido dos veces son dos avisos.
  raiz.__st.enviar = (que) => setTriggerValue('pedir', { que, t: Date.now() });
  dibujar(raiz);
}
