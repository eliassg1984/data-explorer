// Recetas › «Simular Alza de Insumos» (regla #695).
//
// La monta graficos/recetas_alza.py con st.components.v2 (sin iframe,
// estilos en un shadow root). Es la forma del boceto aprobado
// (https://claude.ai/artifact/9Cyr741W82XtckkUzZheCJ), pasado desde la #779 al
// lenguaje de Costo de Carta (#775): nivel 2 con «Platos | Por subgrupo» y
// «Detalle», el escenario en pastillas (nivel 3), la franja de indicadores,
// la lista y la ficha con plegables; lo que explica, en pops. Toda la cuenta pasa acá mientras se escribe; nada vuelve a
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

// ── El escenario: una pastilla por insumo y el editor del elegido ──────
// Regla #779: el escenario ocupaba una tarjeta de 110 px por insumo. Ahora
// cada insumo es una pastilla de la fila de filtros (nivel 3) con su %, y
// el elegido se edita en UN renglón debajo. Los campos conservan sus
// `data-acc`: la lógica de `enlazar` no cambió.
function htmlChips(d, st) {
  const chips = st.orden.map((cod) => {
    const i = d.insumos.findIndex((x) => x[0] === cod);
    const nombre = d.insumos[i][1];
    const p = st.pcts[cod] || 0;
    const on = cod === st.activo;
    return `<span class="sa-chip${on ? ' on' : ''}">
      <button type="button" class="sa-chip-b" data-acc="activo" data-cod="${esc(cod)}" aria-pressed="${on}" title="${esc(nombre)}">
        <i style="background:${color(i)}"></i><span class="sa-chip-n">${esc(nombre)}</span><b class="${tinta(p)}">${p > 0 ? '+' : p < 0 ? '−' : ''}${num(Math.abs(p))} %</b></button>
      <button type="button" class="sa-x" data-acc="quitar" data-cod="${esc(cod)}" aria-label="Quitar ${esc(nombre)}">×</button></span>`;
  }).join('');
  const pop = st.agregar ? `<div class="sa-pop">
      <input type="search" data-acc="buscar" placeholder="Buscar un insumo…" value="${esc(st.q)}" aria-label="Buscar un insumo">
      <div class="sa-pop-nota">Ordenados por lo que cargan a la carta (costo × lo vendido en 90 días)</div>
      <div class="sa-pop-lista" data-zona="sug">${sugerencias(d, st)}</div>
    </div>` : '';
  return `${chips}<div class="sa-agr"><button type="button" class="sa-agr-b" data-acc="abrir-agregar" aria-expanded="${st.agregar}">+ Agregar insumo</button>${pop}</div>`;
}

function htmlEditor(d, st) {
  const i = d.insumos.findIndex((x) => x[0] === st.activo);
  if (i < 0) return '';
  const cod = st.activo;
  const [, nombre, base, unid, fuente, , npl] = d.insumos[i];
  const p = st.pcts[cod] || 0;
  const precio = base
    ? `<label class="sa-precio"><span>S/</span><input type="number" step="0.01" min="0" data-acc="precio" data-cod="${esc(cod)}" value="${(base * (1 + p / 100)).toFixed(2)}" aria-label="Nuevo precio por ${esc(unid)}"><span>/ ${esc(unid)}</span></label>
       <span class="sa-base">hoy ${dinero(base, 2)} / ${esc(unid)} · ${esc(fuente === 'promedio de almacén' ? 'prom. almacén' : fuente)}</span>`
    : `<span class="sa-base">${esc(fuente)}: sólo el %</span>`;
  return `<div class="sa-ins" aria-label="${esc(nombre)}">
    <div class="sa-step">
      <button type="button" data-acc="menos" data-cod="${esc(cod)}" aria-label="Bajar 1 %">−</button>
      <input type="number" step="0.1" min="-100" data-acc="pct" data-cod="${esc(cod)}" value="${+p.toFixed(2)}" class="${tinta(p)}" aria-label="Cambio en %">
      <span>%</span>
      <button type="button" data-acc="mas" data-cod="${esc(cod)}" aria-label="Subir 1 %">+</button>
    </div>
    ${precio}
    <div class="sa-pres">${PRESETS.map((v) => `<button type="button" class="sa-pre${p === v ? ' on' : ''}" data-acc="preset" data-cod="${esc(cod)}" data-v="${v}">${v > 0 ? '+' : '−'}${Math.abs(v)} %</button>`).join('')}</div>
    <span class="sa-npl">lo llevan ${npl} ${npl === 1 ? 'plato' : 'platos'}</span>
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

// ── Las explicaciones: un pop con título y texto ─────────────────────────
// Lo que explica va acá y no a la vista (boceto de la #775). Se abre con un
// clic, para que sirva en el celular.
function info(d, id) {
  const T = {
    k0: ['Costo de recetas del período', 'Lo que cambia el costo de las recetas de lo vendido en las fechas elegidas: el cambio de cada plato × sus unidades vendidas. Con la receta de hoy.'],
    k1: ['Food cost de la carta', 'Costo de recetas ÷ venta neta de toda la carta activa costeada en el período, hoy y con el alza. Incluye los platos que no llevan los insumos elegidos.'],
    k2: ['Margen sobre recetas', 'Venta neta − costo de recetas, con el alza. Es margen sobre recetas, no la utilidad final.'],
    k3: ['Cruzan un umbral', 'Platos que hoy están en 30 % o menos y con el alza pasan el 30 %, más los que pasan el 35 %.'],
    calculo: ['Cómo se calcula', `${d.ayuda || ''} Costo con la receta de hoy, sobre el neto. El precio lleva IGV, en la misma proporción que el neto de hoy. Los cortes porcionados cuentan para su insumo de origen.`],
    lista: ['Cómo leer la lista', `% de costo sobre el neto: ámbar más de 30 %, rojo más de 35 %. «revisar costo»: el costo de hoy ya pasa el 60 % del neto, casi seguro un error de receta o de factor. Ordenada por el cambio en el período. ${d.periodo ? `Ventas del ${d.periodo}.` : 'Sin ventas disponibles: el efecto del período es cero.'}`],
  };
  const [tit, txt] = T[id] || ['', ''];
  return { tit, txt };
}

function abrirInfo(raiz, b) {
  const { data: d, st } = raiz.__d;
  const pop = raiz.querySelector('[data-zona="pop"]');
  const id = b ? b.dataset.id : null;
  st.pop = id && st.pop !== id ? id : null;
  if (!st.pop) { pop.hidden = true; return; }
  const t = info(d, id);
  pop.innerHTML = `<div class="sa-pi-cab"><b>${esc(t.tit)}</b><button type="button" class="sa-x" data-acc="cerrar-info" aria-label="Cerrar">×</button></div><p>${esc(t.txt)}</p>`;
  pop.hidden = false;
  const r = b.getBoundingClientRect(), base = raiz.getBoundingClientRect();
  const ancho = Math.min(340, base.width - 16);
  pop.style.width = `${ancho}px`;
  pop.style.left = `${Math.max(8, Math.min(r.right - base.left - ancho, base.width - ancho - 8))}px`;
  const abajo = r.bottom - base.top + 6;
  pop.style.top = `${abajo + pop.offsetHeight > base.height ? Math.max(0, r.top - base.top - pop.offsetHeight - 6) : abajo}px`;
}

// ── Indicadores ──────────────────────────────────────────────────────────
// Cuatro, como Costo de Carta. «Platos que los llevan» pasó al pie de la
// lista; el renglón de abajo de cada uno aparece con «Detalle».
function htmlKpis(d, filas) {
  const dTot = filas.reduce((s, f) => s + f.dPer, 0);
  const hay = !!d.periodo;
  const fcH = d.neto ? d.costo / d.neto * 100 : NaN, fcN = d.neto ? (d.costo + dTot) / d.neto * 100 : NaN;
  const pp = fcN - fcH;
  const c30 = filas.filter((f) => f.pH <= 30 && f.pN > 30).length;
  const c35 = filas.filter((f) => f.pH <= 35 && f.pN > 35).length;
  const kpi = (id, rot, val, sub, cls = '') => `<div class="sa-kpi"><span class="sa-kpi-rot">${rot}</span>
    <span class="sa-kpi-val ${cls}">${val}</span><span class="sa-kpi-sub">${sub}</span>
    <button type="button" class="sa-i" data-acc="info" data-id="${id}" aria-label="Qué es ${rot}">i</button></div>`;
  return [
    kpi('k0', 'Costo de recetas del período', hay ? dinero(dTot, 0, true) : '—',
      hay ? `${dinero(d.costo, 0)} → ${dinero(d.costo + dTot, 0).replace('S/ ', '')}` : 'sin ventas disponibles', tinta(dTot)),
    kpi('k1', 'Food cost de la carta', pct(fcN), isFinite(pp) ? `hoy ${pct(fcH)} · ${pp >= 0 ? '+' : '−'}${Math.abs(pp).toFixed(2)} pp` : 'sin ventas en el período'),
    kpi('k2', 'Margen sobre recetas', hay ? dinero(d.neto - d.costo - dTot, 0) : '—',
      hay ? `${dinero(-dTot, 0, true)} · venta ${dinero(d.neto, 0)}` : ''),
    kpi('k3', 'Cruzan un umbral', String(c30 + c35), `${c30} pasan 30 % · ${c35} pasan 35 %`, c30 + c35 ? 'ambar' : ''),
  ].join('');
}

// ── Lista y ficha ────────────────────────────────────────────────────────
function htmlTabs(st) {
  return [['platos', 'Platos'], ['sub', 'Por subgrupo']].map(([id, r]) =>
    `<button type="button" role="tab" aria-selected="${st.vista === id}" class="${st.vista === id ? 'on' : ''}" data-acc="vista" data-id="${id}">${r}</button>`).join('');
}

const amp = (st, id, que) => `<button type="button" class="sa-amp" data-acc="ampliar" data-id="${id}" title="${st.amp === id ? 'Volver' : `Ampliar ${que}`}" aria-label="${st.amp === id ? 'Volver' : `Ampliar ${que}`}">${st.amp === id ? '↙' : '⤢'}</button>`;

function htmlLista(d, st, filas, elegido) {
  const vendidos = filas.filter((f) => f.vend > 0).length;
  const pie = `<div class="sa-lpie"><span>${filas.length} ${filas.length === 1 ? 'plato lo lleva' : 'platos los llevan'} · ${vendidos} con ventas en el período</span>
    <button type="button" class="sa-i" data-acc="info" data-id="lista" aria-label="Cómo leer la lista">i</button>${amp(st, 'lista', 'la lista')}</div>`;
  if (!filas.length) {
    const msg = st.orden.length ? 'Ningún plato de la carta lleva los insumos elegidos.'
      : 'Agrega un insumo arriba para ver qué platos lo llevan y cómo quedan.';
    return `<div class="sa-vacio">${msg}</div>${pie}`;
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
    return `<div class="sa-tabla"><table><thead><tr><th>Subgrupo</th><th class="num">Platos</th>
      <th class="num" title="Costo de recetas ÷ neto vendido de esos platos">% de costo</th><th>Δ en el período</th></tr></thead><tbody>
      ${subs.map(([s, x]) => `<tr><td><b>${esc(s || '—')}</b></td><td class="num">${x.n}</td>
        <td class="num">${x.v ? `${pct(x.c / x.v * 100)} → <b>${pct((x.c + x.d) / x.v * 100)}</b>` : '—'}</td>
        <td><div class="sa-bar"><i class="${x.d >= 0 ? 'sube' : 'baja'}" style="width:${Math.max(2, Math.abs(x.d) / maxS * 160)}px"></i><b class="${tinta(x.d)}">${dinero(x.d, 0, true)}</b></div></td></tr>`).join('')}
      </tbody></table></div>${pie}`;
  }
  // Sin «Detalle», tres columnas: el plato, cómo queda y cuánto pesa en el
  // período. Con «Detalle» vuelven las otras cuatro.
  const det = st.detalle;
  const filasHtml = filas.map((f) => {
    const cruza = f.pH <= 35 && f.pN > 35 ? 'pasa 35 %' : f.pH <= 30 && f.pN > 30 ? 'pasa 30 %' : '';
    const dif = f.mant - f.precio;
    return `<tr class="sa-fila${elegido && f.cod === elegido.cod ? ' sel' : ''}" data-acc="plato" data-cod="${esc(f.cod)}">
      <td class="sa-plato"><div><b title="${esc(f.plato)}">${esc(f.plato)}</b>${f.pH > 60 ? '<span class="sa-revisar" title="El costo de hoy ya pasa el 60 % del neto: casi seguro un error de receta o de factor. Revisarlo en Costo de Carta.">revisar costo</span>' : ''}</div>
        <span>${esc(f.sub)} · S/ ${num(f.precio)}</span></td>
      ${det ? `<td><div class="sa-seg">${f.partes.map(([i, s]) => `<i style="width:${Math.min(100, s / f.costo * 100)}%;background:${color(i)}"></i>`).join('')}</div>
        <span class="sa-sub" title="${dinero(f.peso, 2)} de un costo de ${dinero(f.costo, 2)}">${dinero(f.peso, 2)} · ${Math.round(f.peso / f.costo * 100)} % del costo</span></td>` : ''}
      <td class="sa-pct"><span class="hoy">${f.pH.toFixed(1)}</span> → <span class="pill ${nivel(f.pN)}">${pct(f.pN)}</span>${cruza ? `<em>${cruza}</em>` : ''}</td>
      ${det ? `<td class="num ${tinta(f.delta)}">${dinero(f.delta, 2, true)}</td><td class="num">${num(f.vend)}</td>` : ''}
      <td><div class="sa-bar"><i class="${f.dPer >= 0 ? 'sube' : 'baja'}" style="width:${Math.max(2, Math.abs(f.dPer) / maxPer * 56)}px"></i><b class="${tinta(f.dPer)}">${dinero(f.dPer, 0, true)}</b></div></td>
      ${det ? `<td class="num"><b>${dinero(f.mant, 2)}</b> <span class="sa-sub">${Math.abs(dif) < 0.005 ? '=' : dinero(dif, 2, true).replace('S/ ', '')}</span></td>` : ''}
    </tr>`;
  }).join('');
  return `<div class="sa-tabla"><table><thead><tr>
      <th>Plato</th>${det ? '<th title="Soles de los insumos elegidos en el plato: dentro de sus recetas base y de los cortes que salen de ellos">Pesan en el plato</th>' : ''}
      <th class="der">% de costo</th>${det ? '<th class="num" title="Cuánto cambia el costo de UN plato">Δ por plato</th><th class="num">Vend.</th>' : ''}
      <th class="orden der" title="Cambio por plato × unidades vendidas en las fechas elegidas">Δ en el período ↓</th>
      ${det ? '<th class="num" title="El precio de venta con que el plato queda en su % de costo de hoy">Precio para mantener</th>' : ''}
    </tr></thead><tbody>${filasHtml}</tbody></table></div>${pie}`;
}

function plegable(st, id, tit, cuerpo) {
  const ab = !!st.pleg[id];
  return `<div class="sa-pleg${ab ? ' abierto' : ''}"><button type="button" class="sa-pleg-b" data-acc="pleg" data-id="${id}" aria-expanded="${ab}"><span>${tit}</span><i>▾</i></button>
    <div class="sa-pleg-c">${cuerpo}</div></div>`;
}

// La ficha: quién es, dos cifras, la barra, una lectura y lo demás plegado.
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
  const absorber = f.vend ? `${dinero(-f.delta * f.vend, 0, true)} de margen en el período` : `${dinero(-f.delta, 2, true)} por plato`;
  const sube = Math.abs(f.mant - f.precio) < 0.005 ? 'el precio queda igual' : `el precio pasa a ${dinero(f.mant, 2)}`;
  return `<div class="sa-fcab"><span>${esc(f.sub)} · ${f.vend ? `se vendieron ${num(f.vend)} en el período` : 'sin ventas en el período'}</span><div class="sa-ftit"><h3>${esc(f.plato)}</h3>${amp(st, 'ficha', 'la ficha')}</div></div>
    <div class="sa-cifras">
      <div><span class="sa-c-rot">Costo del plato · antes ${dinero(f.costo, 2)}</span><b class="sa-c-val ${tinta(f.delta)}">${dinero(f.nuevo, 2)}</b></div>
      <div><span class="sa-c-rot">% de costo · hoy ${pct(f.pH)}</span><b class="sa-c-val ${nivel(f.pN)}">${pct(f.pN)}</b></div>
    </div>
    <div class="sa-fseg">${segs}</div>
    <div class="sa-lectura"><b>Para quedar en ${pct(f.pH)}, ${sube}</b><span>${dif(f.mant)} sobre los ${dinero(f.precio, 2)} de hoy. Absorberlo: ${absorber}.</span></div>
    ${plegable(st, 'precio', `Qué hacer con el precio de ${dinero(f.precio, 2)}`,
      opc('Mantener su % de costo', dinero(f.mant, 2), `queda en ${pct(f.pH)}`, dif(f.mant), 'prop')
      + opc('Absorberlo', dinero(f.precio, 2), `queda en ${pct(f.pN)}`, absorber)
      + opc('Llevarlo a 30 %', dinero(en30, 2), f.pN > 30 ? `hoy está en ${pct(f.pH)}` : 'ya queda por debajo', dif(en30)))}
    ${plegable(st, 'ley', 'Cuánto pone cada insumo', ley)}`;
}

// ── Dibujar ──────────────────────────────────────────────────────────────
// Los niveles del boceto de la #775: nivel 2 (qué se mira, con subrayado y
// línea de borde a borde), nivel 3 (la fecha nativa y el escenario, en
// pastillas grises), el resumen y, abajo, la lista y la ficha.
function dibujar(raiz, zonas) {
  const { data: d, st } = raiz.__d;
  if (!raiz.querySelector('.sa-arriba')) {
    raiz.innerHTML = `<div class="sa-arriba">
        <div class="sa-n2"><div class="sa-tabs" role="tablist" aria-label="Ver por" data-zona="tabs"></div>
          <div class="sa-n2-der"><label class="sa-switch"><input type="checkbox" data-acc="detalle" role="switch">Detalle</label>
            <button type="button" class="sa-link" data-acc="reset">Restablecer</button>
            <button type="button" class="sa-link" data-acc="info" data-id="calculo">Cómo se calcula</button></div></div>
        <div class="sa-n3"><span class="sa-fecha-lugar" aria-hidden="true"></span><div class="sa-chips" data-zona="chips"></div></div>
        <div data-zona="editor"></div>
        <div class="sa-kpis" data-zona="kpis"></div>
      </div>
      <div class="sa-cuerpo"><div class="sa-lista" data-zona="lista"></div><div class="sa-ficha" data-zona="ficha"></div></div>
      <div class="sa-pi" data-zona="pop" role="dialog" hidden></div>`;
  }
  if (!st.orden.includes(st.activo)) st.activo = st.orden[st.orden.length - 1] || null;
  raiz.classList.toggle('detalle', !!st.detalle);
  // Ampliar: la zona elegida toma la hoja debajo del nivel 2 (#780).
  raiz.classList.toggle('amp-lista', st.amp === 'lista');
  raiz.classList.toggle('amp-ficha', st.amp === 'ficha');
  raiz.querySelector('[data-acc="detalle"]').checked = !!st.detalle;
  const filas = calcular(d, st);
  const elegido = filas.find((f) => f.cod === st.sel) || filas[0];
  const z = (n) => raiz.querySelector(`[data-zona="${n}"]`);
  const todas = !zonas;
  if (todas || zonas.includes('esc') || zonas.includes('chips')) z('chips').innerHTML = htmlChips(d, st);
  if (todas || zonas.includes('esc')) z('editor').innerHTML = htmlEditor(d, st);
  z('tabs').innerHTML = htmlTabs(st);
  z('kpis').innerHTML = htmlKpis(d, filas);
  const lista = z('lista'), scroll = lista.querySelector('.sa-tabla')?.scrollTop || 0;
  lista.innerHTML = htmlLista(d, st, filas, elegido);
  const t = lista.querySelector('.sa-tabla');
  if (t) t.scrollTop = scroll;
  const ficha = z('ficha'), fscroll = ficha.scrollTop;
  ficha.innerHTML = htmlFicha(d, st, elegido);
  ficha.scrollTop = fscroll;
  medir(raiz);
}

// El calendario es el nativo de siempre (`rec_alza_cab`, de Streamlit): se
// ubica sobre el hueco que deja la pieza en su fila de filtros, como en
// Costo de Carta.
function medir(raiz) {
  const cab = document.querySelector('.st-key-rec_alza_cab'), slot = raiz.querySelector('.sa-fecha-lugar');
  if (!cab || !slot || !cab.offsetWidth) return;
  const ancho = `${cab.offsetWidth + 4}px`;
  if (raiz.style.getPropertyValue('--sa-fecha') !== ancho) raiz.style.setProperty('--sa-fecha', ancho);
  const padre = cab.offsetParent;
  if (!padre) return;
  const a = slot.getBoundingClientRect(), p = padre.getBoundingClientRect();
  const x = `${Math.round(a.left - p.left)}px`, y = `${Math.round(a.top - p.top + (a.height - cab.offsetHeight) / 2)}px`;
  if (cab.style.left !== x) cab.style.left = x;
  if (cab.style.top !== y) cab.style.top = y;
  const vis = raiz.__d.st.amp ? 'hidden' : 'visible';
  if (cab.style.visibility !== vis) cab.style.visibility = vis;
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
    if (st.pop && !ev.target.closest('.sa-pi') && !(b && b.dataset.acc === 'info')) abrirInfo(raiz, null);
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
      st.activo = cod;
      if (st.pcts[cod] == null) st.pcts[cod] = 10;
      st.agregar = false; st.q = '';
      guardar(CLAVE, { orden: st.orden, pcts: st.pcts });
    } else if (acc === 'vista') { st.vista = b.dataset.id; guardar('sa_vista', st.vista); dibujar(raiz, []); return; }
    else if (acc === 'plato') { st.sel = cod; dibujar(raiz, []); return; }
    else if (acc === 'activo') { st.activo = cod; dibujar(raiz, ['esc']); return; }
    else if (acc === 'info') { abrirInfo(raiz, b); return; }
    else if (acc === 'ampliar') { st.amp = st.amp === b.dataset.id ? null : b.dataset.id; dibujar(raiz, []); return; }
    else if (acc === 'cerrar-info') { abrirInfo(raiz, null); return; }
    else if (acc === 'detalle') { st.detalle = b.checked; guardar('sa_detalle', st.detalle); dibujar(raiz, []); return; }
    else if (acc === 'pleg') { st.pleg[b.dataset.id] = !st.pleg[b.dataset.id]; guardar('sa_pleg', st.pleg); dibujar(raiz, []); return; }
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
    dibujar(raiz, ['chips']);
  });
  // Al salir del campo, el escenario se dibuja con lo que quedó (−100 como piso).
  raiz.addEventListener('change', (ev) => {
    const acc = ev.target.dataset.acc;
    if (acc === 'pct' || acc === 'precio') dibujar(raiz, ['esc']);
  });
  window.addEventListener('resize', () => medir(raiz));
  // En el documento y no en la raíz: el redibujo reemplaza el botón ⤢ que
  // tenía el foco, y la tecla ya no llegaría a la pieza.
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && raiz.__d.st.amp) { raiz.__d.st.amp = null; dibujar(raiz, []); }
  });
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => medir(raiz)).observe(raiz);
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
    raiz.__d = { st: Object.assign({ sel: null, vista: leer('sa_vista', 'platos'), agregar: false, q: '',
      activo: null, pop: null, amp: null, detalle: leer('sa_detalle', false), pleg: leer('sa_pleg', { precio: true }) },
    inicial(data, false)) };
    enlazar(raiz);
  }
  raiz.__d.data = data;
  dibujar(raiz);
}
