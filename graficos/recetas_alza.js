// Recetas › «Simular Alza de Insumos» (regla #695).
//
// La monta graficos/recetas_alza.py con st.components.v2 (sin iframe,
// estilos en un shadow root). Es la forma del boceto aprobado
// (https://claude.ai/artifact/9Cyr741W82XtckkUzZheCJ): el escenario (una
// ficha por insumo), una tira de indicadores, la lista de platos y la ficha
// del elegido. Toda la cuenta pasa acá mientras se escribe; nada vuelve a
// Python. El escenario vive en la raíz (sobrevive a las corridas: cambiar
// la fecha manda otro `data` sin rehacer el DOM) y en localStorage.
//
// LAS FÓRMULAS SON LAS DE simulador_receta.alzas / resumen_alzas: si se toca
// una, se toca la otra. test_recetas_alza.py las rehace sobre `armar()`.
//
// Python manda en `data`: `insumos` ([cod, nombre, base, unidad, fuente,
// peso 90 días, nº platos]), `platos` ([cod, plato, subgrupo, precio, neto,
// costo, vendidos, neto vendido, {índice de insumo: soles}]), `neto` y
// `costo` de toda la carta en el período, `periodo` y `ayuda`.

const CLAVE = 'sa_esc';
const PRESETS = [-10, 5, 10, 20];
const MAX_SUG = 40;
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento */ } }
const sinTilde = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

function dinero(v, dec, signo) {
  const s = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const umbral = dec ? 0.005 : 0.5;
  const pre = signo ? (v >= umbral ? '+' : v <= -umbral ? '−' : '') : (v <= -umbral ? '−' : '');
  return `${pre}S/ ${s}`;
}
const pct = (v) => (isFinite(v) ? `${v.toFixed(1)} %` : '—');
const tinta = (v) => (v > 0.004 ? 'sube' : v < -0.004 ? 'baja' : '');
const nivel = (p) => (p > 35 ? 'rojo' : p > 30 ? 'ambar' : '');
const color = (i) => `var(--serie-${i % 7})`;
const num = (n) => Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 2 });

// ── La cuenta: la de simulador_receta.alzas ─────────────────────────────
function calcular(d, st) {
  const idx = new Map(d.insumos.map((x, i) => [x[0], i]));
  const elegidos = st.orden.filter((c) => idx.has(c)).map((c) => [idx.get(c), (st.pcts[c] || 0) / 100]);
  const filas = [];
  for (const [cod, plato, sub, precio, neto, costo, vend, vNeto, lleva] of d.platos) {
    let peso = 0, delta = 0;
    const partes = [];
    for (const [i, p] of elegidos) {
      const s = lleva[i];
      if (!s) continue;
      peso += s; delta += s * p; partes.push([i, s]);
    }
    if (!peso) continue;
    const nuevo = costo + delta;
    filas.push({
      cod, plato, sub, precio, neto, costo, vend, vNeto, peso, delta, nuevo, partes,
      pH: costo / neto * 100, pN: nuevo / neto * 100,
      mant: costo ? precio * nuevo / costo : precio,
      dPer: delta * vend,
    });
  }
  filas.sort((a, b) => Math.abs(b.dPer) - Math.abs(a.dPer) || Math.abs(b.peso) - Math.abs(a.peso));
  return filas;
}

// ── El escenario ─────────────────────────────────────────────────────────
function fichaInsumo(d, st, cod) {
  const i = d.insumos.findIndex((x) => x[0] === cod);
  const [, nombre, base, unid, fuente, , npl] = d.insumos[i];
  const p = st.pcts[cod] || 0;
  const precio = base
    ? `<label class="sa-precio"><span>S/</span><input type="number" step="0.01" min="0" data-acc="precio" data-cod="${esc(cod)}" value="${(base * (1 + p / 100)).toFixed(2)}" aria-label="Nuevo precio por ${esc(unid)}"><span>/ ${esc(unid)}</span></label>
       <span class="sa-base">hoy ${dinero(base, 2)} / ${esc(unid)} · ${esc(fuente === 'promedio de almacén' ? 'prom. almacén' : fuente)}</span>`
    : `<span class="sa-base">${esc(fuente)}: sólo el %</span>`;
  return `<div class="sa-ins">
    <div class="sa-ins-cab"><i style="background:${color(i)}"></i><b title="${esc(nombre)}">${esc(nombre)}</b>
      <button type="button" class="sa-x" data-acc="quitar" data-cod="${esc(cod)}" aria-label="Quitar ${esc(nombre)}">×</button></div>
    <div class="sa-ins-mid">
      <div class="sa-step">
        <button type="button" data-acc="menos" data-cod="${esc(cod)}" aria-label="Bajar 1 %">−</button>
        <input type="number" step="0.1" min="-100" data-acc="pct" data-cod="${esc(cod)}" value="${+p.toFixed(2)}" class="${tinta(p)}" aria-label="Cambio en %">
        <span>%</span>
        <button type="button" data-acc="mas" data-cod="${esc(cod)}" aria-label="Subir 1 %">+</button>
      </div>
      <div class="sa-ins-precio">${precio}</div>
    </div>
    <div class="sa-ins-pie">${PRESETS.map((v) => `<button type="button" class="sa-pre${p === v ? ' on' : ''}" data-acc="preset" data-cod="${esc(cod)}" data-v="${v}">${v > 0 ? '+' : '−'}${Math.abs(v)} %</button>`).join('')}
      <span>${npl} ${npl === 1 ? 'plato' : 'platos'}</span></div>
  </div>`;
}

function sugerencias(d, st) {
  const q = sinTilde(st.q.trim());
  const max = Math.max(1, ...d.insumos.map((x) => x[5]));
  const lista = d.insumos.filter((x) => !st.orden.includes(x[0]) && x[6] > 0
    && (!q || sinTilde(x[1]).includes(q) || x[0].includes(q))).slice(0, MAX_SUG);
  if (!lista.length) return '<div class="sa-sug-vacio">Ningún insumo de la carta con ese nombre.</div>';
  return lista.map((x) => `<button type="button" class="sa-sug" data-acc="agregar" data-cod="${esc(x[0])}">
      <b>${esc(x[1])}</b><span class="sa-sug-s">${dinero(x[5], 0)}</span>
      <span class="sa-sug-d">${x[6]} ${x[6] === 1 ? 'plato' : 'platos'}${x[2] ? ` · hoy ${dinero(x[2], 2)} / ${esc(x[3])}` : ''}</span>
      <span class="sa-sug-b"><i style="width:${Math.round(x[5] / max * 100)}%"></i></span>
    </button>`).join('');
}

function htmlEscenario(d, st) {
  const fichas = st.orden.map((c) => fichaInsumo(d, st, c)).join('');
  const pop = st.agregar ? `<div class="sa-pop">
      <input type="search" data-acc="buscar" placeholder="Buscar un insumo…" value="${esc(st.q)}" aria-label="Buscar un insumo">
      <div class="sa-pop-nota">Ordenados por lo que cargan a la carta (costo × lo vendido en 90 días)</div>
      <div class="sa-pop-lista" data-zona="sug">${sugerencias(d, st)}</div>
    </div>` : '';
  return `${fichas}<div class="sa-agr">
      <button type="button" class="sa-agr-b" data-acc="abrir-agregar" aria-expanded="${st.agregar}">
        <span class="mas">+</span><b>Agregar insumo</b><span>${st.orden.length ? 'los que más pesan en la carta' : 'elige el primero: abre con los que más pesan'}</span>
      </button>${pop}</div>`;
}

// ── Indicadores ──────────────────────────────────────────────────────────
function htmlKpis(d, filas) {
  const dTot = filas.reduce((s, f) => s + f.dPer, 0);
  const hay = !!d.periodo;
  const fcH = d.neto ? d.costo / d.neto * 100 : NaN, fcN = d.neto ? (d.costo + dTot) / d.neto * 100 : NaN;
  const pp = fcN - fcH;
  const c30 = filas.filter((f) => f.pH <= 30 && f.pN > 30).length;
  const c35 = filas.filter((f) => f.pH <= 35 && f.pN > 35).length;
  const vendidos = filas.filter((f) => f.vend > 0).length;
  const kpi = (rot, val, sub, cls = '') => `<div class="sa-kpi"><span class="sa-kpi-rot">${rot}</span>
    <div class="sa-kpi-lin"><span class="sa-kpi-val ${cls}">${val}</span><span class="sa-kpi-sub">${sub}</span></div></div>`;
  return [
    kpi('Costo de recetas del período', hay ? dinero(dTot, 0, true) : '—',
      hay ? `${dinero(d.costo, 0)} → ${dinero(d.costo + dTot, 0).replace('S/ ', '')}` : 'sin ventas disponibles', tinta(dTot)),
    kpi('Food cost de la carta', pct(fcN), isFinite(pp) ? `hoy ${pct(fcH)} · ${pp >= 0 ? '+' : '−'}${Math.abs(pp).toFixed(2)} pp` : 'sin ventas en el período'),
    kpi('Margen sobre recetas', hay ? dinero(d.neto - d.costo - dTot, 0) : '—',
      hay ? `${dinero(-dTot, 0, true)} · venta ${dinero(d.neto, 0)}` : ''),
    kpi('Platos que los llevan', String(filas.length), `${vendidos} con ventas en el período`),
    kpi('Cruzan un umbral', String(c30 + c35), `${c30} pasan 30 % · ${c35} pasan 35 %`, c30 + c35 ? 'ambar' : ''),
  ].join('');
}

// ── Lista y ficha ────────────────────────────────────────────────────────
function htmlLista(d, st, filas, elegido) {
  const tabs = [['platos', 'Platos'], ['sub', 'Por subgrupo']].map(([id, r]) =>
    `<button type="button" role="tab" aria-selected="${st.vista === id}" class="${st.vista === id ? 'on' : ''}" data-acc="vista" data-id="${id}">${r}</button>`).join('');
  const cab = `<div class="sa-lcab"><div class="sa-tabs" role="tablist" aria-label="Ver por">${tabs}</div>
    <span class="sa-leyenda">% de costo sobre el neto: <b class="ambar">ámbar &gt; 30 %</b>, <b class="rojo">rojo &gt; 35 %</b></span>
    <button type="button" class="sa-btn" data-acc="reset">Restablecer</button></div>`;
  if (!filas.length) {
    const msg = st.orden.length ? 'Ningún plato de la carta lleva los insumos elegidos.'
      : 'Agrega un insumo arriba para ver qué platos lo llevan y cómo quedan.';
    return `${cab}<div class="sa-vacio">${msg}</div>`;
  }
  const maxPer = Math.max(1e-9, ...filas.map((f) => Math.abs(f.dPer)));
  if (st.vista === 'sub') {
    const g = new Map();
    for (const f of filas) {
      const x = g.get(f.sub) || { n: 0, d: 0, c: 0, v: 0 };
      x.n++; x.d += f.dPer; x.c += f.costo * f.vend; x.v += f.vNeto;
      g.set(f.sub, x);
    }
    const subs = [...g].sort((a, b) => Math.abs(b[1].d) - Math.abs(a[1].d));
    const maxS = Math.max(1e-9, ...subs.map(([, x]) => Math.abs(x.d)));
    return `${cab}<div class="sa-tabla"><table><thead><tr><th>Subgrupo</th><th class="num">Platos</th>
      <th class="num" title="Costo de recetas ÷ neto vendido de esos platos">% de costo</th><th>Δ en el período</th></tr></thead><tbody>
      ${subs.map(([s, x]) => `<tr><td><b>${esc(s || '—')}</b></td><td class="num">${x.n}</td>
        <td class="num">${x.v ? `${pct(x.c / x.v * 100)} → <b>${pct((x.c + x.d) / x.v * 100)}</b>` : '—'}</td>
        <td><div class="sa-bar"><i class="${x.d >= 0 ? 'sube' : 'baja'}" style="width:${Math.max(2, Math.abs(x.d) / maxS * 220)}px"></i><b class="${tinta(x.d)}">${dinero(x.d, 0, true)}</b></div></td></tr>`).join('')}
      </tbody></table></div>`;
  }
  const filasHtml = filas.map((f) => {
    const cruza = f.pH <= 35 && f.pN > 35 ? 'pasa 35 %' : f.pH <= 30 && f.pN > 30 ? 'pasa 30 %' : '';
    const dif = f.mant - f.precio;
    return `<tr class="sa-fila${elegido && f.cod === elegido.cod ? ' sel' : ''}" data-acc="plato" data-cod="${esc(f.cod)}">
      <td class="sa-plato"><div><b title="${esc(f.plato)}">${esc(f.plato)}</b>${f.pH > 60 ? '<span class="sa-revisar" title="El costo de hoy ya pasa el 60 % del neto: casi seguro un error de receta o de factor. Revisarlo en Costo Carta.">revisar costo</span>' : ''}</div>
        <span>${esc(f.sub)} · S/ ${num(f.precio)}</span></td>
      <td><div class="sa-seg">${f.partes.map(([i, s]) => `<i style="width:${Math.min(100, s / f.costo * 100)}%;background:${color(i)}"></i>`).join('')}</div>
        <span class="sa-sub" title="${dinero(f.peso, 2)} de un costo de ${dinero(f.costo, 2)}">${dinero(f.peso, 2)} · ${Math.round(f.peso / f.costo * 100)} % del costo</span></td>
      <td class="sa-pct"><span class="hoy">${f.pH.toFixed(1)}</span> → <span class="pill ${nivel(f.pN)}">${pct(f.pN)}</span>${cruza ? `<em>${cruza}</em>` : ''}</td>
      <td class="num ${tinta(f.delta)}">${dinero(f.delta, 2, true)}</td>
      <td class="num">${num(f.vend)}</td>
      <td><div class="sa-bar"><i class="${f.dPer >= 0 ? 'sube' : 'baja'}" style="width:${Math.max(2, Math.abs(f.dPer) / maxPer * 56)}px"></i><b class="${tinta(f.dPer)}">${dinero(f.dPer, 0, true)}</b></div></td>
      <td class="num"><b>${dinero(f.mant, 2)}</b> <span class="sa-sub">${Math.abs(dif) < 0.005 ? '=' : dinero(dif, 2, true).replace('S/ ', '')}</span></td>
    </tr>`;
  }).join('');
  return `${cab}<div class="sa-tabla"><table><thead><tr>
      <th>Plato</th><th title="Soles de los insumos elegidos en el plato: dentro de sus recetas base y de los cortes que salen de ellos">Pesan en el plato</th>
      <th>% de costo</th><th class="num" title="Cuánto cambia el costo de UN plato">Δ por plato</th><th class="num">Vend.</th>
      <th title="Cambio por plato × unidades vendidas en las fechas elegidas">Δ en el período</th>
      <th class="num" title="El precio de venta con que el plato queda en su % de costo de hoy">Precio para mantener</th>
    </tr></thead><tbody>${filasHtml}</tbody></table></div>`;
}

function htmlFicha(d, st, f) {
  if (!f) return '<div class="sa-vacio">Elige un plato de la lista.</div>';
  const total = Math.max(f.costo, f.nuevo);
  const resto = Math.max(0, f.costo - f.peso);
  const segs = f.partes.map(([i, s]) => {
    const p = (st.pcts[d.insumos[i][0]] || 0) / 100;
    return `<i title="${esc(d.insumos[i][1])}" style="width:${s * (1 + p) / total * 100}%;background:${color(i)}"></i>`;
  }).join('') + `<i title="Resto de la receta" class="resto" style="width:${resto / total * 100}%"></i>`;
  const ley = f.partes.map(([i, s]) => {
    const dd = s * (st.pcts[d.insumos[i][0]] || 0) / 100;
    return `<div class="sa-ley"><i style="background:${color(i)}"></i><span>${esc(d.insumos[i][1])}</span>
      <span class="num">${dinero(s, 2)}</span><b class="num ${tinta(dd)}">${dinero(dd, 2, true)}</b></div>`;
  }).join('') + `<div class="sa-ley"><i class="resto"></i><span>Resto de la receta</span><span class="num">${dinero(resto, 2)}</span><b class="num">sin cambio</b></div>`;
  const en30 = f.precio * (f.nuevo / 0.30) / f.neto;
  const opc = (t, v, det, extra, cls = '') => `<div class="sa-opc ${cls}"><b>${t}</b><b class="num">${v}</b><span>${det}</span><span class="num">${extra}</span></div>`;
  const dif = (x) => (Math.abs(x - f.precio) < 0.005 ? 'sin cambio' : dinero(x - f.precio, 2, true));
  return `<div class="sa-fcab"><span>${esc(f.sub)} · ${f.vend ? `se vendieron ${num(f.vend)} en el período` : 'sin ventas en el período'}</span><h3>${esc(f.plato)}</h3></div>
    <div class="sa-fbloque"><div class="sa-frot"><span>Costo del plato</span><span class="num">${dinero(f.costo, 2)} → <b>${dinero(f.nuevo, 2)}</b></span></div>
      <div class="sa-fseg">${segs}</div>${ley}</div>
    <div class="sa-fbloque"><div class="sa-frot"><span>Qué hacer con el precio de ${dinero(f.precio, 2)}</span></div>
      ${opc('Mantener su % de costo', dinero(f.mant, 2), `queda en ${pct(f.pH)}`, dif(f.mant), 'prop')}
      ${opc('Absorberlo', dinero(f.precio, 2), `queda en ${pct(f.pN)}`, f.vend ? `${dinero(-f.delta * f.vend, 0, true)} de margen en el período` : `${dinero(-f.delta, 2, true)} por plato`)}
      ${opc('Llevarlo a 30 %', dinero(en30, 2), f.pN > 30 ? `hoy está en ${pct(f.pH)}` : 'ya queda por debajo', dif(en30))}
    </div>
    <div class="sa-fpie">Precio con IGV, en la misma proporción que el neto de hoy. Los cortes porcionados cuentan para su insumo de origen.</div>`;
}

// ── Dibujar ──────────────────────────────────────────────────────────────
function dibujar(raiz, zonas) {
  const { data: d, st } = raiz.__d;
  if (!raiz.querySelector('.sa-arriba')) {
    raiz.innerHTML = `<div class="sa-arriba">
        <div class="sa-esc" data-zona="esc"></div>
        <div class="sa-kpis" data-zona="kpis"></div>
      </div>
      <div class="sa-cuerpo"><div class="sa-lista" data-zona="lista"></div><div class="sa-ficha" data-zona="ficha"></div></div>
      <div class="sa-pie"><span class="sa-ayuda" title="${esc(d.ayuda)}">?</span> ${d.periodo ? `Ventas del ${esc(d.periodo)}.` : 'Sin ventas disponibles: se calcula el efecto por plato, pero el del período es cero.'} Costo con la receta de hoy, sobre el neto.</div>`;
  } else {
    const pie = raiz.querySelector('.sa-pie');
    pie.innerHTML = `<span class="sa-ayuda" title="${esc(d.ayuda)}">?</span> ${d.periodo ? `Ventas del ${esc(d.periodo)}.` : 'Sin ventas disponibles: se calcula el efecto por plato, pero el del período es cero.'} Costo con la receta de hoy, sobre el neto.`;
  }
  const filas = calcular(d, st);
  const elegido = filas.find((f) => f.cod === st.sel) || filas[0];
  const z = (n) => raiz.querySelector(`[data-zona="${n}"]`);
  const todas = !zonas;
  if (todas || zonas.includes('esc')) z('esc').innerHTML = htmlEscenario(d, st);
  z('kpis').innerHTML = htmlKpis(d, filas);
  const lista = z('lista'), scroll = lista.querySelector('.sa-tabla')?.scrollTop || 0;
  lista.innerHTML = htmlLista(d, st, filas, elegido);
  const t = lista.querySelector('.sa-tabla');
  if (t) t.scrollTop = scroll;
  z('ficha').innerHTML = htmlFicha(d, st, elegido);
  medir(raiz);
}

function medir(raiz) {
  const arriba = raiz.querySelector('.sa-arriba');
  if (!arriba) return;
  const alto = Math.ceil(arriba.getBoundingClientRect().height);
  if (raiz.__d.arriba !== alto) {
    raiz.__d.arriba = alto;
    raiz.style.setProperty('--sa-arriba', `${alto}px`);
  }
}

function fijar(raiz, cod, p) {
  const st = raiz.__d.st;
  if (!isFinite(p)) return false;
  st.pcts[cod] = Math.max(-100, Math.round(p * 100) / 100);
  guardar(CLAVE, { orden: st.orden, pcts: st.pcts });
  return true;
}

function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    const { data: d, st } = raiz.__d;
    // Un clic afuera del panel de «Agregar» lo cierra.
    if (st.agregar && !ev.target.closest('.sa-agr')) { st.agregar = false; dibujar(raiz, ['esc']); }
    if (!b || !raiz.contains(b)) return;
    const acc = b.dataset.acc, cod = b.dataset.cod;
    if (acc === 'mas' || acc === 'menos') fijar(raiz, cod, (st.pcts[cod] || 0) + (acc === 'mas' ? 1 : -1));
    else if (acc === 'preset') fijar(raiz, cod, +b.dataset.v);
    else if (acc === 'quitar') {
      st.orden = st.orden.filter((c) => c !== cod);
      guardar(CLAVE, { orden: st.orden, pcts: st.pcts });
    } else if (acc === 'abrir-agregar') { st.agregar = !st.agregar; st.q = ''; }
    else if (acc === 'agregar') {
      st.orden = st.orden.concat([cod]);
      if (st.pcts[cod] == null) st.pcts[cod] = 10;
      st.agregar = false; st.q = '';
      guardar(CLAVE, { orden: st.orden, pcts: st.pcts });
    } else if (acc === 'vista') { st.vista = b.dataset.id; guardar('sa_vista', st.vista); dibujar(raiz, []); return; }
    else if (acc === 'plato') { st.sel = cod; dibujar(raiz, []); return; }
    else if (acc === 'reset') { Object.assign(st, inicial(d, true)); guardar(CLAVE, { orden: st.orden, pcts: st.pcts }); }
    else return;
    dibujar(raiz);
    if (acc === 'abrir-agregar' && st.agregar) raiz.querySelector('[data-acc="buscar"]')?.focus();
  });
  // Escribir no redibuja el escenario: el campo no pierde el foco. El % y el
  // precio del mismo insumo se siguen el uno al otro.
  raiz.addEventListener('input', (ev) => {
    const el = ev.target, acc = el.dataset.acc;
    const { data: d, st } = raiz.__d;
    if (acc === 'buscar') {
      st.q = el.value;
      const zona = raiz.querySelector('[data-zona="sug"]');
      if (zona) zona.innerHTML = sugerencias(d, st);
      return;
    }
    if (acc !== 'pct' && acc !== 'precio') return;
    const cod = el.dataset.cod;
    const base = (d.insumos.find((x) => x[0] === cod) || [])[2];
    if (el.value === '') return;
    const v = parseFloat(el.value);
    const p = acc === 'pct' ? v : (base ? (v / base - 1) * 100 : NaN);
    if (!fijar(raiz, cod, p)) return;
    const ficha = el.closest('.sa-ins');
    const otro = ficha?.querySelector(`[data-acc="${acc === 'pct' ? 'precio' : 'pct'}"]`);
    if (otro) otro.value = acc === 'pct' ? (base * (1 + st.pcts[cod] / 100)).toFixed(2) : +st.pcts[cod].toFixed(2);
    const inPct = ficha?.querySelector('[data-acc="pct"]');
    if (inPct) inPct.className = tinta(st.pcts[cod]);
    ficha?.querySelectorAll('.sa-pre').forEach((x) => x.classList.toggle('on', +x.dataset.v === st.pcts[cod]));
    dibujar(raiz, []);
  });
  // Al salir del campo, el escenario se dibuja con lo que quedó (−100 como piso).
  raiz.addEventListener('change', (ev) => {
    const acc = ev.target.dataset.acc;
    if (acc === 'pct' || acc === 'precio') dibujar(raiz, ['esc']);
  });
  window.addEventListener('resize', () => medir(raiz));
}

// El escenario con que abre: el guardado, si sus insumos siguen en la
// carta; si no, el insumo que más pesa con +10 %.
function inicial(d, limpio) {
  const conocidos = new Set(d.insumos.map((x) => x[0]));
  const g = limpio ? null : leer(CLAVE, null);
  if (g && Array.isArray(g.orden)) {
    const orden = g.orden.filter((c) => conocidos.has(c));
    if (orden.length) return { orden, pcts: g.pcts || {} };
  }
  const primero = d.insumos.find((x) => x[6] > 0);
  return primero ? { orden: [primero[0]], pcts: { [primero[0]]: 10 } } : { orden: [], pcts: {} };
}

export default function (component) {
  const { data, parentElement } = component;
  if (!data || !data.insumos) return;
  let raiz = parentElement.querySelector('.sa');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'sa';
    parentElement.appendChild(raiz);
    raiz.__d = { st: Object.assign({ sel: null, vista: leer('sa_vista', 'platos'), agregar: false, q: '' }, inicial(data, false)) };
    enlazar(raiz);
  }
  raiz.__d.data = data;
  dibujar(raiz);
}
