// Recetas › «Cambios en recetas» (regla #707).
//
// La monta graficos/recetas_cambios.py::render_cambios_recetas_base con
// st.components.v2 (sin iframe, estilos en un shadow root). Es la forma del
// boceto aprobado (https://claude.ai/artifact/GUZqHk1LzTiEbX58EBogAZ): las
// pestañas Todo / Recetas base / Recetas de plato / Precios, seis
// indicadores que filtran, buscar, usuario, «Incluir productos sin costo»,
// la lista por día y la ficha del elegido con su historial. Python manda
// los cambios del rango de la tarjeta ya armados (`armar`): acá no se
// recalcula nada, sólo se filtra y se dibuja. No vuelve nada a Python.
//
// Python manda en `data`: `items` (uno por cambio: id, tipo base|plato|
// precio, k —su identidad: rb:<receta base>, rv:<receta de plato>,
// pl:<plato>—, t, usr, nombre, grupo, cods —los platos a los que toca— y lo
// de su tipo: lineas [insumo, antes, después, unidad, soles], antes,
// despues, delta, grande; usos y guardados en una base; platos [cod,
// nombre, precio, costo, neto], nueva, quitada, aprox y desde en una de
// plato; canales [canal, antes, después, costo] y sinCosto en un precio),
// `platos` ({cod: [nombre, receta, [recetas base]]}, la receta de HOY),
// `foco` ({cod, nombre, n}: el plato que pidió «Ver cambios» en Costo de Carta),
// `fotos` ({n, primera}), `preciosDeFotos`, `rango`, `grande` y `divisor`.
//
// EL HISTORIAL de la ficha junta lo que le toca a los platos del cambio
// elegido: sus precios, su receta y las recetas base que llevan directo. El
// de una receta base es sólo el suyo: la llevan decenas de platos, y sus
// precios no son un cambio de ella.

const CLAVE = 'rec_cambios_est';
const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const DIA = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
const CORTO = { 'En el Local': 'Local', Delivery: 'Deliv.', 'Para Llevar': 'Llevar', Rappi: 'Rappi', 'Pedidos Ya': 'P. Ya' };
const TIPOS = [['todo', 'Todo'], ['base', 'Recetas base'], ['plato', 'Recetas de plato'], ['precio', 'Precios']];
const ROT_TIPO = { base: 'BASE', plato: 'PLATO', precio: 'PRECIO' };

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento */ } }
const sinTilde = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
function soles(v, signo) {
  if (v == null || !isFinite(v)) return '—';
  const s = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const pre = signo ? (v > 0.0049 ? '+' : v < -0.0049 ? '−' : '') : (v < 0 ? '−' : '');
  return `${pre}S/ ${s}`;
}
const cant = (v) => (v == null ? '—' : (+v.toFixed(3)).toLocaleString('en-US', { maximumFractionDigits: 3 }));
const pct = (v) => (v == null || !isFinite(v) ? '—' : `${(v * 100).toFixed(1)} %`);
const pctSigno = (v) => `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v * 100).toFixed(0)} %`;
const fecha = (t) => new Date(t);
const hora = (f) => `${String(f.getHours()).padStart(2, '0')}:${String(f.getMinutes()).padStart(2, '0')}`;
const diaLargo = (f) => `${DIA[f.getDay()]} ${f.getDate()} ${MES[f.getMonth()]}`;
const corta = (f) => `${String(f.getDate()).padStart(2, '0')}/${String(f.getMonth() + 1).padStart(2, '0')}/${String(f.getFullYear()).slice(2)}`;
const chipTipo = (t) => `<span class="tipo ${t}">${ROT_TIPO[t]}</span>`;
const tipoLinea = (l) => (!l[1] ? 'Agregado' : !l[2] ? 'Quitado' : 'Cantidad');
const clase = (v) => (v > 0.0049 ? 'sube' : v < -0.0049 ? 'baja' : 'gris');

// El canal que se muestra en la lista: el primero que tenía y tiene precio.
const canalPrincipal = (x) => x.canales.find((c) => c[1] > 0 && c[2] > 0) || x.canales[0];
const dPrecio = (x) => { const c = canalPrincipal(x); return c[1] != null && c[2] != null ? c[2] - c[1] : null; };

const KPIS = [
  ['todos', 'Cambios', () => true],
  ['sube', 'Suben el costo', (x) => x.tipo !== 'precio' && x.delta > 0.0049],
  ['baja', 'Bajan el costo', (x) => x.tipo !== 'precio' && x.delta < -0.0049],
  ['grande', 'Cambio grande de costo', (x) => !!x.grande],
  ['psube', 'Suben de precio', (x) => x.tipo === 'precio' && dPrecio(x) > 0],
  ['pbaja', 'Bajan de precio', (x) => x.tipo === 'precio' && dPrecio(x) < 0],
];

function clavesDePlato(d, cod) {
  const p = d.platos[cod];
  return new Set([`pl:${cod}`, ...(p ? [`rv:${p[1]}`, ...p[2].map((r) => `rb:${r}`)] : [])]);
}
function base(raiz) {
  const { data: d, st } = raiz.__d;
  const del = st.plato ? clavesDePlato(d, st.plato) : null;
  const q = sinTilde(st.q);
  return d.items.filter((x) => (st.sinCosto || !x.sinCosto)
    && (!st.usr || x.usr === st.usr)
    && (!del || del.has(x.k))
    && (!q || [x.nombre, x.grupo, ...(x.lineas || []).map((l) => l[0]), ...(x.platos || []).map((p) => p[1]), ...(x.usos || [])]
      .some((s) => sinTilde(s).includes(q))));
}
function visibles(raiz) {
  const { st } = raiz.__d, k = KPIS.find((y) => y[0] === st.kpi);
  return base(raiz).filter((x) => (st.tab === 'todo' || x.tipo === st.tab) && (!k || k[2](x)));
}

// ── Las partes ───────────────────────────────────────────────────────────
function htmlTabs(raiz) {
  const { st } = raiz.__d, b = base(raiz);
  return TIPOS.map(([id, r]) => `<button type="button" data-acc="tab" data-id="${id}" class="${st.tab === id ? 'on' : ''}">${r}<i>${b.filter((x) => id === 'todo' || x.tipo === id).length}</i></button>`).join('');
}
function htmlKpis(raiz) {
  const { st } = raiz.__d, b = base(raiz).filter((x) => st.tab === 'todo' || x.tipo === st.tab);
  return KPIS.map(([id, r, f]) => {
    const L = b.filter(f);
    let s;
    if (id === 'todos') s = `${new Set(L.map((x) => x.k)).size} recetas o productos`;
    else if (id === 'sube' || id === 'baja') s = `${soles(L.reduce((a, x) => a + (x.delta || 0), 0), true)} en total`;
    else if (id === 'grande') s = `±${raiz.__d.data.grande[0] * 100} % y ±S/ ${raiz.__d.data.grande[1]}`;
    else s = `${new Set(L.map((x) => x.k)).size} productos`;
    return `<button type="button" class="kpi${st.kpi === id ? ' on' : ''}" data-acc="kpi" data-id="${id}"><span class="r">${r}</span><span class="v">${L.length}</span><span class="s">${esc(s)}</span></button>`;
  }).join('');
}
function htmlFiltros(raiz) {
  const { data: d, st } = raiz.__d;
  const us = [...new Set(d.items.map((x) => x.usr).filter(Boolean))].sort();
  const nSin = d.items.filter((x) => x.sinCosto).length;
  const foco = st.plato ? `<span class="foco" title="Lo que le toca a este plato: sus precios, su receta y las recetas base que lleva">Plato: ${esc(st.platoNombre || (d.platos[st.plato] || [st.plato])[0])}<button type="button" data-acc="soltar" aria-label="Quitar el filtro del plato">✕</button></span>` : '';
  return `<input data-acc="buscar" placeholder="Buscar receta, plato o insumo…" aria-label="Buscar receta, plato o insumo" value="${esc(st.q)}">${foco}
    ${us.length ? `<span class="rot">Usuario</span><button type="button" class="chip-f${!st.usr ? ' on' : ''}" data-acc="usr" data-id="">Todos</button>${us.map((u) => `<button type="button" class="chip-f${st.usr === u ? ' on' : ''}" data-acc="usr" data-id="${esc(u)}">${esc(u)}</button>`).join('')}` : ''}
    ${nSin ? `<label class="interruptor" title="Propina, vales, anticipos: productos de venta que no tienen costo"><input type="checkbox" data-acc="sincosto"${st.sinCosto ? ' checked' : ''}> Incluir productos sin costo (${nSin})</label>` : ''}`;
}

function resumen(x) {
  if (x.tipo === 'precio') return x.canales.map((c) => `${CORTO[c[0]] || c[0]} ${c[1] ?? '—'} → ${c[2] ?? '—'}`).join(' · ');
  if (x.nueva) return `receta nueva · ${x.lineas.length} insumo${x.lineas.length !== 1 ? 's' : ''}`;
  if (x.quitada) return 'receta quitada';
  const t = { Agregado: 0, Quitado: 0, Cantidad: 0 };
  x.lineas.forEach((l) => { t[tipoLinea(l)] += 1; });
  const partes = [t.Agregado && `${t.Agregado} agreg.`, t.Quitado && `${t.Quitado} quit.`, t.Cantidad && `${t.Cantidad} cant.`].filter(Boolean);
  return `${x.lineas.length} línea${x.lineas.length !== 1 ? 's' : ''} · ${partes.join(' · ')}${x.usr ? ` · ${x.usr}` : ''}`;
}
function valor(x) {
  if (x.tipo === 'precio') {
    const c = canalPrincipal(x), dp = dPrecio(x);
    if (dp == null) return `<span class="gris">${CORTO[c[0]] || c[0]}</span>`;
    // Un precio que sube BAJA el % de costo: verde.
    return `<span class="${dp > 0 ? 'baja' : 'sube'}">${dp > 0 ? '▲' : '▼'} ${soles(Math.abs(dp))}</span><small>${c[1] ? pctSigno(dp / c[1]) : ''} · ${CORTO[c[0]] || c[0]}</small>`;
  }
  const a = x.antes || 0;
  return `<span class="${clase(x.delta)}">${soles(x.delta, true)}</span><small>${x.nueva ? 'receta nueva' : x.quitada ? 'quitada' : a > 0 ? `${pctSigno(x.delta / a)} del costo` : ''}</small>`;
}
function htmlLista(raiz) {
  const { data: d, st } = raiz.__d, L = visibles(raiz);
  const n = `${L.length} cambio${L.length !== 1 ? 's' : ''}`;
  if (!L.length) {
    let txt = 'Ningún cambio con esta fecha y estos filtros.';
    if (st.plato) {
      const [a, b] = d.rango.map((s) => { const [y, m, dd] = s.split('-').map(Number); return `${dd} ${MES[m - 1]} ${y}`; });
      txt = `«${st.platoNombre || (d.platos[st.plato] || [st.plato])[0]}» no tuvo cambios del ${a} al ${b}: ni de precio, ni de su receta, ni de las recetas base que lleva. Para mirar más atrás, el botón de la fecha.`;
    } else if (st.tab === 'plato' && d.fotos.n < 2) {
      txt = `Las recetas de plato se comparan foto contra foto: el POS no guarda su historial. La primera foto es del ${d.fotos.primera ? corta(fecha(d.fotos.primera)) : '—'}; la primera comparación sale con la foto siguiente, a la madrugada.`;
    }
    return [n, `<div class="vacio">${esc(txt)}</div>`];
  }
  let html = '', dia = '';
  for (const x of L) {
    const f = fecha(x.t), dl = diaLargo(f) + (f.getFullYear() !== new Date().getFullYear() ? ` ${f.getFullYear()}` : '');
    if (dl !== dia) { html += `<div class="dia">${dl}</div>`; dia = dl; }
    html += `<div class="f${x.id === st.sel ? ' sel' : ''}" data-acc="sel" data-id="${x.id}" role="button" tabindex="0">
      <span class="h" title="${x.aprox ? 'Hora de la foto: la receta no dice cuándo se guardó' : ''}">${x.aprox ? '≈' : ''}${hora(f)}</span>
      <span class="n" title="${esc(x.nombre)}">${chipTipo(x.tipo)}${x.grande ? '<span class="punto" title="Cambio grande de costo">●</span>' : ''}${esc(x.nombre)}</span>
      <span class="val">${valor(x)}</span>
      <span class="res" title="${esc(resumen(x))}">${esc(resumen(x))}</span></div>`;
  }
  return [n, html];
}

function tablaLineas(x) {
  const filas = x.lineas.map((l) => {
    const t = tipoLinea(l);
    return `<tr><td>${esc(l[0])}</td><td><span class="cambio ${t}">${t}</span></td><td class="d">${cant(l[1])}</td><td class="d">${cant(l[2])}</td><td>${esc(l[3] || '')}</td><td class="d ${clase(l[4])}">${soles(l[4], true)}</td></tr>`;
  }).join('');
  return `<div class="bl"><div class="bl-t">Qué cambió en la receta</div><div class="tabla"><table><thead><tr><th>Insumo</th><th>Cambio</th><th class="d">Antes</th><th class="d">Después</th><th>Unidad</th><th class="d">Δ costo</th></tr></thead><tbody>${filas}</tbody></table></div></div>`;
}
function costos(x, nota) {
  const a = x.antes || 0;
  return `<div class="costos"><div><small>Costo antes</small><b>${soles(x.antes)}</b></div><div><small>Costo después</small><b>${soles(x.despues)}</b></div>
    <span class="pill ${clase(x.delta)}">${soles(x.delta, true)}${a > 0 ? ` · ${(x.delta / a > 0 ? '+' : '−') + Math.abs(x.delta / a * 100).toFixed(1)} %` : ''}</span><span class="nota">${nota}</span></div>`;
}
function historial(raiz, x) {
  const { data: d } = raiz.__d;
  let claves;
  if (x.tipo === 'base') claves = new Set([x.k]);
  else { claves = new Set([x.k]); (x.cods || []).forEach((c) => clavesDePlato(d, c).forEach((k) => claves.add(k))); }
  const H = d.items.filter((y) => claves.has(y.k));
  if (H.length < 2) return '';
  const filas = H.map((y) => `<div class="${y.id === x.id ? 'on' : ''}" data-acc="sel" data-id="${y.id}" role="button" tabindex="0"><span class="num">${corta(fecha(y.t))}</span><span>${chipTipo(y.tipo)}</span><span class="q" title="${esc(y.nombre)} · ${esc(resumen(y))}">${y.k === x.k ? esc(resumen(y)) : esc(y.nombre)}</span><span class="d">${y.tipo === 'precio' ? '' : `<span class="${clase(y.delta)}">${soles(y.delta, true)}</span>`}</span></div>`).join('');
  const que = x.tipo === 'base' ? 'de esta receta base' : 'de sus precios, su receta y las recetas base que lleva';
  return `<div class="bl"><div class="bl-t">Historial en el rango · ${H.length} cambios ${que}</div><div class="hist">${filas}</div></div>`;
}
function htmlFicha(raiz) {
  const { data: d, st } = raiz.__d, x = d.items.find((y) => y.id === st.sel);
  if (!x) return '<div class="vacio">Elegí un cambio de la lista.</div>';
  const f = fecha(x.t);
  const quien = x.usr ? ` por <b>${esc(x.usr)}</b>` : '';
  let meta;
  if (x.tipo === 'base') meta = `Editada el ${corta(f)} a las ${hora(f)}${quien}${x.guardados > 1 ? ` · ${x.guardados} guardados` : ''}`;
  else if (x.tipo === 'plato') meta = x.aprox ? `Cambió entre la foto del ${corta(fecha(x.desde))} y la del ${corta(f)}` : `Guardada el ${corta(f)} a las ${hora(f)}${quien}`;
  else meta = x.usr ? `Cambiado el ${corta(f)} a las ${hora(f)}${quien}` : `Cambió entre dos fotos: llegó en la del ${corta(f)}`;
  let h = `<div><div>${chipTipo(x.tipo)}<span class="fi-de">${esc(x.grupo || '')}</span></div><div class="fi-nom">${esc(x.nombre)}</div><div class="fi-de">${meta}</div></div>`;
  if (x.tipo !== 'precio') {
    if (x.grande) h += `<div class="aviso">Cambio grande de costo: de ${soles(x.antes)} a ${soles(x.despues)}. Conviene revisar que no sea un error de digitación.</div>`;
    h += costos(x, x.tipo === 'base' ? 'por unidad de la receta, con los precios de antes' : 'por plato, con los precios de hoy');
    if (x.lineas.length) h += tablaLineas(x);
    if (x.tipo === 'base') {
      h += `<div class="bl"><div class="bl-t">Dónde se usa hoy · ${x.usos.length} plato${x.usos.length !== 1 ? 's' : ''}</div><div class="chips">${x.usos.map((u) => `<span>${esc(u)}</span>`).join('') || '<span>Ningún plato la lleva directo</span>'}</div></div>`;
    } else if (x.platos.length) {
      const filas = x.platos.map((p) => {
        const neto = p[2] ? p[2] / d.divisor : null, ca = p[3] != null ? p[3] - (x.delta || 0) : null;
        return `<tr><td>${esc(p[1])}</td><td class="d">${soles(p[2])}</td><td class="d">${neto ? pct(ca / neto) : '—'}</td><td class="d ${clase(x.delta)}">${neto && p[3] != null ? pct(p[3] / neto) : '—'}</td></tr>`;
      }).join('');
      h += `<div class="bl"><div class="bl-t">Platos con esta receta · % de costo en el local</div><div class="tabla"><table><thead><tr><th>Plato</th><th class="d">Precio</th><th class="d">% costo antes</th><th class="d">% costo hoy</th></tr></thead><tbody>${filas}</tbody></table></div></div>`;
    }
  } else {
    if (x.sinCosto) h += '<div class="aviso gris">Este producto no tiene costo en el POS: no tiene % de costo.</div>';
    const filas = x.canales.map((c) => {
      const dd = c[1] != null && c[2] != null ? c[2] - c[1] : null;
      const pa = c[3] && c[1] ? c[3] / (c[1] / d.divisor) : null, pd = c[3] && c[2] ? c[3] / (c[2] / d.divisor) : null;
      const pr = (v) => (v == null ? '—' : v ? soles(v) : 'no se vende');
      return `<tr><td>${esc(c[0])}</td><td class="d">${pr(c[1])}</td><td class="d">${pr(c[2])}</td><td class="d ${dd > 0 ? 'baja' : dd < 0 ? 'sube' : ''}">${dd == null ? '' : soles(dd, true)}</td><td class="d">${pct(pa)}</td><td class="d ${pa != null && pd != null ? (pd > pa ? 'sube' : 'baja') : ''}">${pct(pd)}</td></tr>`;
    }).join('');
    h += `<div class="bl"><div class="bl-t">Precio por canal · el % de costo con el costo de hoy</div><div class="tabla"><table><thead><tr><th>Canal</th><th class="d">Antes</th><th class="d">Después</th><th class="d">Δ</th><th class="d">% costo antes</th><th class="d">% costo después</th></tr></thead><tbody>${filas}</tbody></table></div></div>`;
    if (d.preciosDeFotos) h += '<div class="aviso gris">Este precio sale de las fotos diarias, sin hora ni usuario: la fila «auditoriacostos» del Sheet todavía no trae los campos «Precio Venta Canal».</div>';
  }
  return h + historial(raiz, x);
}

// ── Dibujar ──────────────────────────────────────────────────────────────
function dibujar(raiz, solo) {
  const { st } = raiz.__d;
  if (!raiz.querySelector('.cuerpo')) {
    raiz.innerHTML = `<div class="seg" role="tablist" data-zona="tabs"></div><div class="kpis" data-zona="kpis"></div>
      <div class="filtros" data-zona="filtros"></div>
      <div class="cuerpo"><div class="caja lista"><div class="lcab"><span data-zona="n"></span><span>Δ costo · Δ precio</span></div><div class="filas" data-zona="filas"></div></div>
      <aside class="caja ficha" data-zona="ficha" aria-label="Ficha del cambio"></aside></div>`;
  }
  const z = (n) => raiz.querySelector(`[data-zona="${n}"]`);
  const L = visibles(raiz);
  if (!L.some((x) => x.id === st.sel)) st.sel = L.length ? L[0].id : null;
  if (solo !== 'sel') {
    z('tabs').innerHTML = htmlTabs(raiz);
    z('kpis').innerHTML = htmlKpis(raiz);
    if (solo !== 'buscar') z('filtros').innerHTML = htmlFiltros(raiz);
  }
  const y = z('filas').scrollTop;
  const [n, html] = htmlLista(raiz);
  z('n').textContent = n;
  z('filas').innerHTML = html;
  if (solo === 'sel') z('filas').scrollTop = y;
  z('ficha').innerHTML = htmlFicha(raiz);
  z('ficha').scrollTop = 0;
}

function enlazar(raiz) {
  const elegir = (b) => {
    const { st } = raiz.__d, acc = b.dataset.acc, id = b.dataset.id;
    if (acc === 'sel') {
      if (st.sel === +id) return;
      st.sel = +id;
      // Del historial a un cambio que el filtro de la pestaña esconde: se ve en «Todo».
      if (!visibles(raiz).some((x) => x.id === st.sel)) { st.tab = 'todo'; st.kpi = null; dibujar(raiz); return; }
      dibujar(raiz, 'sel');
      return;
    }
    if (acc === 'tab') { st.tab = id; st.kpi = null; }
    else if (acc === 'kpi') st.kpi = st.kpi === id || id === 'todos' ? null : id;
    else if (acc === 'usr') st.usr = id || null;
    else if (acc === 'soltar') { st.plato = null; st.platoNombre = null; }
    else return;
    guardar(CLAVE, { tab: st.tab });
    dibujar(raiz);
  };
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b) || b.tagName === 'INPUT') return;
    elegir(b);
  });
  raiz.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter' && ev.key !== ' ') return;
    const b = ev.target.closest('[data-acc="sel"]');
    if (b) { ev.preventDefault(); elegir(b); }
  });
  raiz.addEventListener('input', (ev) => {
    if (ev.target.dataset.acc !== 'buscar') return;
    raiz.__d.st.q = ev.target.value;
    dibujar(raiz, 'buscar');
  });
  raiz.addEventListener('change', (ev) => {
    if (ev.target.dataset.acc !== 'sincosto') return;
    raiz.__d.st.sinCosto = ev.target.checked;
    dibujar(raiz);
  });
}

export default function (component) {
  const { data, parentElement } = component;
  if (!data || !data.items) return;
  let raiz = parentElement.querySelector('.cr');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'cr';
    parentElement.appendChild(raiz);
    raiz.__d = { st: Object.assign({ tab: 'todo' }, leer(CLAVE, {}),
      { kpi: null, usr: null, q: '', sinCosto: false, sel: null, plato: null, platoNombre: null, focoN: null }) };
    enlazar(raiz);
  }
  raiz.__d.data = data;
  const st = raiz.__d.st;
  // «Ver cambios» desde Costo de Carta: un pedido nuevo (otro `n`) filtra
  // por su plato y abre en «Todo».
  if (data.foco && data.foco.n !== st.focoN) {
    st.focoN = data.foco.n; st.plato = data.foco.cod; st.platoNombre = data.foco.nombre || null; st.tab = 'todo'; st.kpi = null; st.q = ''; st.sel = null;
  }
  if (!TIPOS.some((t) => t[0] === st.tab)) st.tab = 'todo';
  dibujar(raiz);
}
