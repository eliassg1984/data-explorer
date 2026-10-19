// La tabla del costo de ventas del reporte «Costos» (regla #622).
//
// La monta graficos/costos.py con st.components.v2 (sin iframe, estilos en
// un shadow root). Todo lo que pasa acá adentro es del navegador: elegir
// familias, sumar Eventos y Venta interna, añadir salidas, abrir una fila.
// Nada vuelve a Python: la tabla no recalcula la página.
//
// Python manda en `data.granos` un grano por clave (mes, quincena, semana),
// cada uno como lo arma `costo_ventas.armar`/`armar_kardex`: los períodos y,
// por fila, una serie por familia («cubeta»). Las cuentas de abajo (consumo
// operativo, consumo carta, margen, %) se hacen acá porque dependen de lo
// que se elige en pantalla; sus definiciones son las de costo_ventas.py.

const BUCK = ['Alimentos', 'Bebidas', 'Vinos', 'Envases'];
const COLOR = { Alimentos: '--serie-0', Bebidas: '--serie-3', Vinos: '--serie-2', Envases: '--serie-1' };
const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const VENTANA = 6;
const BAJAS = 'Bajas';
// Lo que gasta inventario sin ser la venta del reporte y se puede sumar a la
// venta de Alimentos (las claves de `venta_extra` en costo_ventas.py).
const EXTRAS = ['Eventos', 'Venta interna'];

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento */ } }

// El grano: Mes (inventario de los cierres) o Quincena / Semana (del kardex).
const GRANOS = [['mes', 'Mes', 'meses'], ['quincena', 'Quincena', 'quincenas'], ['semana', 'Semana', 'semanas']];
const plural = (g) => (GRANOS.find((x) => x[0] === g) || GRANOS[0])[2];
function soles(v) {
  if (v == null || !isFinite(v)) return '—';
  return `${v < -0.5 ? '−' : ''}S/ ${Math.abs(Math.round(v)).toLocaleString('en-US')}`;
}
function num(v) {
  if (v == null || !isFinite(v)) return '—';
  return `${v < -0.5 ? '−' : ''}${Math.abs(Math.round(v)).toLocaleString('en-US')}`;
}
const pct = (v) => (v == null || !isFinite(v) ? '—' : `${(v * 100).toFixed(1)}%`);
const pp = (v) => (v == null || !isFinite(v) ? '—' : `${v >= 0 ? '+' : '−'}${Math.abs(v * 100).toFixed(1)} pp`);
const mil = (v) => `${(v / 1000).toLocaleString('en-US', { maximumFractionDigits: 1 })} mil`;

// ── Las series de la ventana ─────────────────────────────────────────────
// `st.ini[grano]` es el primer período visible: la tabla muestra VENTANA.
function ventana(st, data) {
  const n = data.periodos.length;
  const cantidad = st.cantidad || VENTANA;
  const indices = st.grano === 'mes' && st.anio ? data.periodos.map((p, i) => p.k.startsWith(st.anio + '-') ? i : -1).filter(i => i >= 0) : [];
  const minimo = indices.length ? indices[0] : 0, maximo = indices.length ? indices[indices.length - 1] + 1 : n;
  const ini = Math.max(minimo, Math.min(st.ini[st.grano], Math.max(minimo, maximo - cantidad)));
  const fin = Math.min(maximo, ini + cantidad);
  return { ini, fin, minimo, maximo, per: data.periodos.slice(ini, fin) };
}

function cortar(arr, w) { return (arr || []).slice(w.ini, w.fin); }
function ceros(w) { return new Array(w.fin - w.ini).fill(0); }
const suma = (a, b) => a.map((x, i) => x + b[i]);
const resta = (a, b) => a.map((x, i) => x - b[i]);

function porFamilia(st, data, w, b) {
  const de = (obj) => (obj && obj[b] ? cortar(obj[b], w) : ceros(w));
  const f = data.filas;
  const r = {
    v: de(f.venta), ii: de(f.inv_inicial), c: de(f.compras), fi: de(f.inv_final),
    bajas: de((data.salidas || {})[BAJAS]), cort: de(f.cortesias), pos: de(f.costo_pos),
    desc: de(f.descuentos),
  };
  if (b === 'Alimentos') {
    for (const g of Object.keys(data.venta_extra || {}).filter((x) => st.extra.has(x))) {
      r.v = suma(r.v, cortar(data.venta_extra[g], w));
      r.pos = suma(r.pos, cortar((data.costo_extra || {})[g], w));
      const d = cortar((data.descuento_extra || {})[g], w);
      if (d.length) r.desc = suma(r.desc, d);
    }
  }
  r.operativo = resta(suma(r.ii, r.c), r.fi);
  // Consumos no vendidos: cortesías y salidas seleccionadas. Es lo que va del consumo
  // operativo al carta. Las BAJAS no: son pérdida, se quedan en el consumo
  // carta y explican la diferencia (regla #662, como el cuadro de costos
  // que el usuario llevaba antes).
  let nv = [...r.cort];
  for (const t of st.agregadas) {
    r[`s_${t}`] = de((data.salidas || {})[t]);
    nv = suma(nv, r[`s_${t}`]);
  }
  r.nv = nv;
  r.carta = resta(r.operativo, nv);
  r.margen = resta(r.v, r.carta);
  // El plato vendido mantiene su costo histórico completo. Los descuentos
  // son referencia comercial y no modifican ninguno de los dos lados.
  r.dif = resta(r.carta, r.pos);
  // Separar las bajas registradas deja un saldo pendiente de conciliar;
  // por sí solo, ese saldo no identifica su causa.
  r.falt = resta(r.dif, r.bajas);
  return r;
}

function filas(st) {
  const f = [
    { k: 'v', nom: 'Venta neta documentada', nota: 'pagados y por cobrar − notas de crédito; sin IGV ni recargo', tipo: 'suma', sentido: 'bien', calc: true },
    { k: 'carta', nom: 'Consumo carta', nota: 'consumo operativo − salidas seleccionadas − cortesías; abrir cálculo', tipo: 'suma', sentido: 'mal', calc: true, fuerte: true, calculo: true, tasa: 'carta' },
  ];
  if (st.calculoAbierto) {
    f.push({ k: 'ii', nom: 'Inventario inicial', tipo: 'ini', sentido: 'neutro', hijo: true },
      { k: 'c', nom: 'Compras netas', signo: '+', tipo: 'suma', sentido: 'mal', hijo: true },
      { k: 'fi', nom: 'Inventario final', signo: '−', tipo: 'fin', sentido: 'neutro', hijo: true },
      { k: 'operativo', nom: 'Consumo operativo valorizado', signo: '=', tipo: 'suma', sentido: 'mal', hijo: true, tasa: 'operativo' },
      { k: 'nv', nom: 'Consumos no vendidos', nota: 'salidas seleccionadas y cortesías; descuentos separados', signo: '−', tipo: 'suma', sentido: 'mal', grupo: true });
    if (st.grupoAbierto) {
      for (const t of st.agregadas) f.push({ k: `s_${t}`, nom: t, tipo: 'suma', sentido: 'mal', quitar: t, hijo: true });
      f.push({ agregar: true }, { k: 'cort', nom: 'Costo de cortesías', tipo: 'suma', sentido: 'mal', hijo: true });
    }
  }
  f.push({ k: 'pos', nom: 'Costo del Sistema', nota: 'costo histórico completo de platos, combos y propiedades; notas de crédito restadas', tipo: 'suma', sentido: 'mal', tasa: 'pos' },
    { k: 'dif', nom: 'Diferencia', nota: 'consumo carta − costo histórico completo del Sistema', tipo: 'suma', sentido: 'mal', calc: true, fuerte: true, tasa: 'dif' },
    { k: 'bajas', nom: 'Bajas registradas', nota: 'salidas procesadas de tipo baja; permanecen en el consumo carta', tipo: 'suma', sentido: 'mal', hijo: true },
    { k: 'falt', nom: 'Pendiente de conciliación', nota: 'diferencia − bajas registradas; el saldo no demuestra por sí solo pérdida física', tipo: 'suma', sentido: 'mal', calc: true, fuerte: true, tasa: 'falt' });
  return f;
}

// Valores de una fila para un conjunto de familias: por mes y el total.
function valores(st, data, w, fila, fams) {
  const R = fams.map((b) => porFamilia(st, data, w, b));
  const sumK = (k) => R.reduce((a, r) => suma(a, r[k]), ceros(w));
  const tot = (a) => a.reduce((x, y) => x + y, 0);
  if (fila.tipo === 'pct') {
    const n = sumK(fila.num), d = sumK(fila.den);
    return { mes: n.map((x, i) => (d[i] ? x / d[i] : null)), tot: tot(d) ? tot(n) / tot(d) : null };
  }
  if (fila.tipo === 'pp') {
    const c = valores(st, data, w, { tipo: 'pct', num: 'carta', den: 'v' }, fams);
    const p = valores(st, data, w, { tipo: 'pct', num: 'pos', den: 'v' }, fams);
    return {
      mes: c.mes.map((x, i) => (x == null || p.mes[i] == null ? null : x - p.mes[i])),
      tot: c.tot == null || p.tot == null ? null : c.tot - p.tot,
    };
  }
  const m = sumK(fila.k);
  const n = m.length;
  // Inventarios: el total de la ventana es su punta, no una suma.
  return { mes: m, tot: fila.tipo === 'ini' ? m[0] : fila.tipo === 'fin' ? m[n - 1] : tot(m) };
}

function fmtCelda(fila, v) {
  if (fila.tipo === 'pct') return pct(v);
  if (fila.tipo === 'pp') return pp(v);
  return num(v);
}
function claseCelda(fila, v) {
  if (v == null) return 'cero';
  if (fila.tipo === 'suma' && Math.abs(v) < 0.5) return 'cero';
  if ((fila.k === 'margen' || fila.k === 'v') && v < 0) return 'neg';
  return '';
}
function sentidoVar(fila, delta) {
  if (fila.sentido === 'neutro' || Math.abs(delta) < 1e-9) return 'neutro';
  const sube = delta > 0;
  return (fila.sentido === 'mal') === sube ? 'mal' : 'bien';
}

function enlaceOrigen(st, fila, periodo) {
  if (['v', 'pos', 'pos_aj', 'cort', 'desc'].includes(fila.k)
      && [...st.fams].every(f => f === 'Envases')) return '';
  const enlace = st.todo.enlaces?.[st.grano]?.[periodo.k]?.[fila.k];
  if (!enlace) return '';
  const href = enlace.url + '&familias=' + encodeURIComponent(JSON.stringify([...st.fams]))
    + '&extras=' + encodeURIComponent(JSON.stringify([...st.extra]));
  const titulo = `${enlace.nombre} · ${periodo.rot} · abrir en otra pestaña`;
  return `<a class="enlace-origen" href="${esc(href)}" target="_blank" rel="noopener noreferrer" aria-label="${esc(titulo)}" title="${esc(titulo)}">↗</a>`;
}

// ── Dibujo ───────────────────────────────────────────────────────────────
function dibujar(raiz) {
  const st = raiz.__st;
  const granos = (st.todo && st.todo.granos) || {};
  const hay = GRANOS.filter(([g]) => granos[g] && granos[g].periodos && granos[g].periodos.length);
  if (!hay.length) { raiz.innerHTML = ''; return; }
  if (!hay.some(([g]) => g === st.grano)) st.grano = hay[0][0];
  const data = granos[st.grano];
  st.data = data;
  const w = ventana(st, data);
  st.ini[st.grano] = w.ini;
  const F = BUCK.filter((b) => st.fams.has(b));
  const n = w.per.length;
  const esMes = st.grano === 'mes';
  // Todas las salidas entran por defecto (a pedido, 2026-10-09); la × quita
  // una y se recuerda cuál. Una sin movimientos en la ventana no se dibuja.
  st.agregadas = Object.keys(data.salidas || {}).filter((t) => t !== BAJAS
    && !st.quitadas.includes(t) && Math.abs(totalSalida(data, w, F, t)) > 0.5);
  // «1–15 abr – 16–30 set» junta dos guiones: entre rótulos que ya llevan uno, «a».
  const sep = esMes ? ' – ' : ' a ';

  // UNA fila arriba (a pedido, 2026-10-09): el título y el rango a la
  // izquierda; Período, Familias y Eventos a la derecha. Sin KPIs: la tabla
  // sube y entra entera en la pantalla.
  const hayMas = w.maximo - w.minimo > (st.cantidad || VENTANA);
  const aviso = esMes ? '' : `Por ${st.grano}, el inventario es el del kardex al final de cada período, no lo contado: el ajuste de cada cierre cae entero en el período del cierre, y por eso las ${plural(st.grano)} no suman el mes.`;
  if (!w.per.some(p => p.k === st.seleccionado)) st.seleccionado = w.per[n - 1].k;
  let html = `<div class="cv-cab"><div class="cv-tit"><h2>Estado de costo de venta</h2>
    <span class="cv-rango">${esc(w.per[0].rot)}${sep}${esc(w.per[n - 1].rot)} · ${n} ${plural(st.grano)}${esMes ? ' operativos' : ''}</span>
    ${hayMas ? `<span class="cv-ventana"><button type="button" data-ventana="-1" aria-label="Períodos anteriores" ${w.ini === w.minimo ? 'disabled' : ''}>‹</button><button type="button" data-ventana="1" aria-label="Períodos siguientes" ${w.fin >= w.maximo ? 'disabled' : ''}>›</button></span>` : ''}
    ${aviso ? `<span class="cv-kardex" title="${esc(aviso)}">inventario del kardex ⓘ</span>` : ''}</div>
    <div class="cv-controles">`;
  if (hay.length > 1) {
    html += `<label class="cv-campo"><span class="cv-rot">Período</span><select data-grano-sel aria-label="Período">${hay.map(([g, nom]) =>
      `<option value="${g}"${st.grano === g ? ' selected' : ''}>${nom}</option>`).join('')}</select></label>`;
  }
  if (esMes) {
    const anios = [...new Set(data.periodos.map(p => p.k.slice(0, 4)))];
    html += `<label class="cv-campo"><span class="cv-rot">Año</span><select data-anio aria-label="Año"><option value=""${!st.anio ? ' selected' : ''}>Recientes</option>${anios.map(a => `<option value="${a}"${a === st.anio ? ' selected' : ''}>${a}</option>`).join('')}</select></label>`;
  }
  html += `<label class="cv-campo"><span class="cv-rot">Columnas</span><select data-cantidad aria-label="Cantidad de períodos"><option value="6"${st.cantidad === 6 ? ' selected' : ''}>6 períodos</option><option value="12"${st.cantidad === 12 ? ' selected' : ''}>12 períodos</option></select></label>`;
  const famTxt = F.length === BUCK.length ? 'Todas' : F.length === 1 ? F[0] : `${F.length} de ${BUCK.length}`;
  html += `<details class="dd"${st.ddAbierto ? ' open' : ''}><summary><span class="cv-rot">Familias</span><span class="dd-val">${famTxt}</span><span class="dd-fl">▾</span></summary>
      <div class="dd-panel">${BUCK.map((b) => `<label class="dd-op"><input type="checkbox" data-fam-chk="${b}" ${st.fams.has(b) ? 'checked' : ''}><span class="pt" style="background:var(${COLOR[b]})"></span>${b}</label>`).join('')}
      <span class="dd-nota">Familias de insumos del Almacén. La venta se agrupa por grupos de carta; Envases no tiene venta ni costo del Sistema propio en esta selección.</span></div></details>
    <span class="cv-campo"><span class="cv-rot">Sumar a la venta</span>${EXTRAS.map((g) =>
      `<label class="interruptor"><input type="checkbox" data-extra="${g}" ${st.extra.has(g) ? 'checked' : ''}> ${g}</label>`).join('')}</span>
    </div></div>`;
  const estadoExtra = EXTRAS.map((g) => {
    const incluido = F.includes('Alimentos') && st.extra.has(g);
    return `${g} ${g === 'Eventos' ? (incluido ? 'incluidos' : 'excluidos') : (incluido ? 'incluida' : 'excluida')}`;
  });
  html += `<div class="cv-contexto" role="status" aria-live="polite" aria-atomic="true">
    <span>${esMes ? 'Mes operativo · inventario contado' : `${st.grano === 'semana' ? 'Semana' : 'Quincena'} · inventario del kardex`}</span>
    <span>Venta y costo del Sistema: día contable del turno</span>
    <span>Familias: ${esc(F.join(', '))}</span>
    <span>${esc(estadoExtra.join(' · '))}</span></div>`;
  html += observaciones(st, data, w, F);
  html += coberturaSUNAT(st);

  // La tabla
  const cols = `<col class="c-lab">${w.per.map(() => '<col class="c-mes">').join('')}<col class="c-tot">`;
  const ths = w.per.map((p) => `<th scope="col" class="${p.k === st.seleccionado ? 'seleccionado' : ''}"><button type="button" data-seleccionar="${esc(p.k)}" aria-pressed="${p.k === st.seleccionado}">${esc(p.rot)}</button><span class="sub">${esc(p.sub || '')}</span></th>`).join('');
  let cuerpo = '';
  for (const fila of filas(st)) {
    if (fila.sec) { cuerpo += `<tr class="sec"><td colspan="${n + 2}"><div class="fila-fija">${fila.sec}</div></td></tr>`; continue; }
    if (fila.agregar) { cuerpo += filaAgregar(st, data, w, F, n); continue; }
    if (fila.tramo) { cuerpo += `<tr class="tramo"><td colspan="${n + 2}"><div class="fila-fija">${fila.tramo}</div></td></tr>`; continue; }
    const val = valores(st, data, w, fila, F);
    const abierta = fila.calculo ? st.calculoAbierto : fila.grupo ? st.grupoAbierto : st.abierta === fila.k;
    const accion = fila.calculo ? 'data-calculo' : fila.grupo ? 'data-grupo' : `data-fila="${esc(fila.k)}"`;
    const cls = ['fila', fila.calc ? 'calc' : '', fila.fuerte ? 'fuerte' : '', abierta ? 'abierta' : '',
      fila.hijo ? 'hijo' : '', fila.grupo ? 'grupo' : '', fila.grupo && st.grupoAbierto ? 'grupo-abierto' : ''].join(' ');
    const tip = ` title="${esc(fila.nota ? `${fila.nom}: ${fila.nota}` : fila.nom)}"`;
    cuerpo += `<tr class="${cls}"><td class="lab"><div class="fila-lab">`
      + (fila.calculo ? `<button type="button" class="chev" data-calculo aria-expanded="${!!st.calculoAbierto}" aria-label="Abrir cálculo del consumo carta">${st.calculoAbierto ? '▾' : '▸'}</button>` : '')
      + (fila.grupo ? `<button type="button" class="chev" data-grupo aria-expanded="${!!st.grupoAbierto}" aria-label="${st.grupoAbierto ? 'Cerrar' : 'Abrir'} el detalle de ${esc(fila.nom)}">${st.grupoAbierto ? '▾' : '▸'}</button>` : '')
      + `<button type="button" class="fila-btn" ${accion} aria-expanded="${abierta}"${tip}><span class="signo">${fila.signo || ''}</span>`
      + `<span class="nom">${esc(fila.nom)}</span><span class="flecha">▼</span></button>`
      + (fila.quitar ? `<button type="button" class="quitar" data-quitar="${esc(fila.quitar)}" aria-label="Quitar ${esc(fila.quitar)}">×</button>` : '')
      + `</div></td>${val.mes.map((x, i) => `<td class="${claseCelda(fila, x)} ${w.per[i].k === st.seleccionado ? 'seleccionado' : ''}">${fmtCelda(fila, x)}${enlaceOrigen(st, fila, w.per[i])}${tasaCelda(st, data, w, F, fila, i)}</td>`).join('')}`
      + `<td class="tot ${claseCelda(fila, val.tot)}">${fmtCelda(fila, val.tot)}${tasaCelda(st, data, w, F, fila, null)}</td></tr>`;
    if (abierta && !fila.calculo && !fila.grupo) cuerpo += detalle(st, data, w, fila, F, val);
  }
  html += `<div class="desliza" role="region" aria-label="Tabla de costos con desplazamiento horizontal por períodos"><table><colgroup>${cols}</colgroup><thead><tr><th class="lab" scope="col">Concepto<span class="sub">${esMes ? 'mes operativo · cierre' : 'kardex'}</span></th>${ths}<th class="tot" scope="col">${n} ${plural(st.grano)}<span class="sub">${esc(w.per[0].rot)}${sep}${esc(w.per[n - 1].rot)}</span></th></tr></thead><tbody>${cuerpo}</tbody></table></div>`;
  html += `<div class="estado-desliza"><span>← Períodos anteriores · recientes →</span><span class="periodos-visibles"></span></div>`;

  html += graficoComparacion(st, data, w, F);
  html += comercial(st, data, w, F);
  html += notas(st, data, w);
  raiz.innerHTML = html;
  prepararDesplazamiento(raiz, w);
  if (st.irCalculo) {
    raiz.querySelector('.cv-calidad')?.scrollIntoView({ block: 'start' });
    st.irCalculo = false;
  }
}

function prepararDesplazamiento(raiz, w) {
  const st = raiz.__st, d = raiz.querySelector('.desliza');
  const clave = `${st.grano}:${w.per[0].k}:${w.per[w.per.length - 1].k}`;
  st.scroll ||= {};
  const aplicarAncho = () => {
    for (const [clase, activa] of [['cv-angosta', raiz.clientWidth < 760], ['cv-movil', raiz.clientWidth < 640]]) {
      if (raiz.classList.contains(clase) !== activa) raiz.classList.toggle(clase, activa);
    }
    const ancho = `${d.clientWidth}px`;
    if (raiz.style.getPropertyValue('--cv-ancho') !== ancho) raiz.style.setProperty('--cv-ancho', ancho);
  };
  raiz.style.setProperty('--cv-columnas', w.per.length);
  aplicarAncho();
  const max = Math.max(0, d.scrollWidth - d.clientWidth);
  let posicion = d.clientWidth < 640 ? Math.max(0, max - 108) : max;
  if (st.scroll[clave] != null) posicion = st.scroll[clave] * max;
  else if (st.todo.mes_inicial && st.grano === 'mes') {
    const i = w.per.findIndex(p => p.k === st.todo.mes_inicial);
    if (i >= 0) posicion = i * 104;
  }
  d.scrollLeft = Math.max(0, Math.min(max, posicion));
  if (st.enfocarSeleccion) {
    const i = w.per.findIndex(p => p.k === st.seleccionado);
    const columna = d.querySelectorAll('thead th')[i + 1];
    const lab = d.querySelector('th.lab');
    if (columna && lab && i >= 0) d.scrollLeft = Math.max(0, columna.offsetLeft - lab.offsetWidth);
    st.enfocarSeleccion = false;
  }
  st.scroll[clave] = max ? d.scrollLeft / max : 0;
  const actualizar = () => {
    const borde = d.getBoundingClientRect();
    const lab = d.querySelector('th.lab').getBoundingClientRect();
    const total = d.querySelector('th.tot').getBoundingClientRect();
    const derecha = total.left > lab.right ? Math.min(borde.right, total.left) : borde.right;
    const visibles = [...d.querySelectorAll('thead th')].slice(1, -1)
      .map((el, i) => ({ rect: el.getBoundingClientRect(), p: w.per[i] }))
      .filter(x => x.rect.right > lab.right + 30 && x.rect.left < derecha - 30);
    const rango = visibles.length ? `${visibles[0].p.rot} – ${visibles[visibles.length - 1].p.rot} · ` : '';
    const texto = `${rango}histórico de ${w.per.length} ${plural(st.grano)}`;
    const etiqueta = raiz.querySelector('.periodos-visibles');
    if (etiqueta.textContent !== texto) etiqueta.textContent = texto;
  };
  d.addEventListener('scroll', () => {
    const limite = d.scrollWidth - d.clientWidth;
    st.scroll[clave] = limite ? d.scrollLeft / limite : 0;
    actualizar();
  }, { passive: true });
  st.actualizarAncho = () => {
    aplicarAncho();
    const posicionNueva = (d.scrollWidth - d.clientWidth) * st.scroll[clave];
    if (Math.abs(d.scrollLeft - posicionNueva) > 0.5) d.scrollLeft = posicionNueva;
    actualizar();
  };
  actualizar();
}

function totalSalida(data, w, F, t) {
  return F.reduce((a, b) => a + cortar(((data.salidas || {})[t] || {})[b], w).reduce((x, y) => x + y, 0), 0);
}

// La fila para volver a sumar una salida que se quitó. Sin ninguna quitada,
// no se dibuja.
function filaAgregar(st, data, w, F, n) {
  const totalDe = (t) => totalSalida(data, w, F, t);
  const disp = Object.keys(data.salidas || {})
    .filter((t) => t !== BAJAS && st.quitadas.includes(t) && Math.abs(totalDe(t)) > 0.5);
  if (!disp.length) return '';
  let menu = '';
  if (st.menu && disp.length) {
    menu = `<div class="menu">${disp.map((t) =>
      `<button type="button" class="chip" data-agregar="${esc(t)}">${esc(t)} <span class="n">S/ ${mil(totalDe(t))}</span></button>`).join('')}</div>`;
  }
  const btn = `<button type="button" class="btn-agregar" data-menu>${st.menu ? 'Cerrar' : '+ Volver a sumar una salida'}</button>`;
  return `<tr class="agregar"><td colspan="${n + 2}"><div class="fila-fija">${btn}${menu}</div></td></tr>`;
}

function detalle(st, data, w, fila, F, val) {
  const n = val.mes.length;
  const esPct = fila.tipo === 'pct' || fila.tipo === 'pp';
  const fmt = (x) => (esPct ? fmtCelda(fila, x) : soles(x));
  const series = st.modo === 'total'
    ? [{ nom: 'Total', vals: val.mes, color: 'var(--accent)' }]
    : F.map((b) => ({ nom: b, vals: valores(st, data, w, fila, [b]).mes, color: `var(${COLOR[b]})` }))
      .filter((s) => s.vals.some((x) => x != null && Math.abs(x) > 5e-4));
  const todos = series.flatMap((s) => s.vals).filter((x) => x != null && isFinite(x));
  let lo = todos.length ? Math.min(...todos) : 0, hi = todos.length ? Math.max(...todos) : 1;
  if (hi - lo < 1e-9) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.14; lo -= pad; hi += pad;
  const y = (x) => 100 - ((x - lo) / (hi - lo)) * 100;
  const xp = (i) => (i + 0.5) * 100;

  let svg = `<svg viewBox="0 0 ${n * 100} 100" preserveAspectRatio="none" aria-hidden="true">`;
  for (const g of [25, 50, 75]) svg += `<line x1="0" x2="${n * 100}" y1="${g}" y2="${g}" stroke="var(--border-lavender)" stroke-width="1" vector-effect="non-scaling-stroke" opacity=".6"/>`;
  if (lo < 0 && hi > 0) svg += `<line x1="0" x2="${n * 100}" y1="${y(0)}" y2="${y(0)}" stroke="var(--text-secondary)" stroke-width="1" vector-effect="non-scaling-stroke"/>`;
  let puntos = '';
  for (const s of series) {
    const pts = s.vals.map((x, i) => (x == null ? null : `${xp(i)},${y(x)}`)).filter(Boolean);
    if (st.modo === 'total' && pts.length > 1) {
      const base = lo < 0 && hi > 0 ? y(0) : 100;
      svg += `<polygon points="${xp(0)},${base} ${pts.join(' ')} ${xp(n - 1)},${base}" fill="var(--accent)" opacity=".10"/>`;
      const vs = s.vals.filter((x) => x != null);
      const prom = vs.reduce((a, x) => a + x, 0) / vs.length;
      svg += `<line x1="0" x2="${n * 100}" y1="${y(prom)}" y2="${y(prom)}" stroke="var(--accent)" stroke-dasharray="4 4" stroke-width="1" vector-effect="non-scaling-stroke" opacity=".7"/>`;
    }
    svg += `<polyline points="${pts.join(' ')}" fill="none" stroke="${s.color}" stroke-width="2.2" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`;
    if (st.modo === 'total') {
      s.vals.forEach((x, i) => {
        if (x == null) return;
        const prev = i > 0 ? s.vals[i - 1] : null;
        const sv = prev == null ? 'neutro' : sentidoVar(fila, x - prev);
        const col = sv === 'mal' ? 'var(--danger-text)' : sv === 'bien' ? 'var(--success-text)' : 'var(--accent)';
        puntos += `<div class="hitbox" style="left:calc(${i} * 100% / ${n});width:calc(100% / ${n})"></div>`
          + `<div class="punto${i === n - 1 ? ' ult' : ''}" style="left:calc(${i + 0.5} * 100% / ${n});top:${y(x)}%;background:${col}"><span class="tip">${fmt(x)}</span></div>`;
      });
    }
  }
  svg += '</svg>';

  // Una sola marca de variación: la del mes contra el anterior.
  let vari;
  if (st.modo === 'total') {
    vari = `<div class="variaciones" style="grid-template-columns:repeat(${n},1fr)">${val.mes.map((x, i) => {
      const prev = i > 0 ? val.mes[i - 1] : null;
      if (prev == null || x == null) return `<span class="neutro">${i === 0 ? '' : '—'}</span>`;
      const dlt = x - prev;
      let t;
      if (esPct) t = `${dlt >= 0 ? '▲' : '▼'} ${Math.abs(dlt * 100).toFixed(1)} pp`;
      else if (Math.abs(prev) < 1) t = '—';
      else t = `${dlt >= 0 ? '▲' : '▼'} ${Math.abs((dlt / Math.abs(prev)) * 100).toFixed(0)}%`;
      return `<span class="${sentidoVar(fila, dlt)}">${t}</span>`;
    }).join('')}</div>`;
  } else {
    vari = `<div class="leyenda">${series.map((s) => `<span><i style="background:${s.color}"></i>${s.nom}</span>`).join('')}</div>`;
  }

  const vs = val.mes.map((x, i) => [x, i]).filter(([x]) => x != null);
  const prom = vs.reduce((a, [x]) => a + x, 0) / (vs.length || 1);
  const mn = vs.reduce((a, b) => (b[0] < a[0] ? b : a), vs[0] || [null, 0]);
  const mx = vs.reduce((a, b) => (b[0] > a[0] ? b : a), vs[0] || [null, 0]);
  const ult = val.mes[n - 1];
  let vsProm = '—';
  if (ult != null && prom) {
    vsProm = esPct ? pp(ult - prom)
      : `${ult - prom >= 0 ? '+' : '−'}${Math.abs(((ult - prom) / Math.abs(prom)) * 100).toFixed(0)}%`;
  }
  const stats = `<div class="stats">
      <span>Promedio <b>${fmt(prom)}</b></span>
      <span>Mínimo <b>${fmt(mn[0])}</b> · ${esc(w.per[mn[1]].rot)}</span>
      <span>Máximo <b>${fmt(mx[0])}</b> · ${esc(w.per[mx[1]].rot)}</span>
      <span>${esc(w.per[n - 1].rot)} contra el promedio <b>${vsProm}</b></span>
      <div class="modo" role="group" aria-label="Qué dibujar">
        <button type="button" data-modo="total" aria-pressed="${st.modo === 'total'}">Total</button>
        <button type="button" data-modo="familia" aria-pressed="${st.modo === 'familia'}">Por familia</button>
      </div></div>`;

  // La columna del total: de qué familias se compone la fila.
  let comp = '';
  if (F.length > 1) {
    const partes = F.map((b) => ({ b, t: valores(st, data, w, fila, [b]).tot }))
      .filter((p) => p.t != null && isFinite(p.t) && (esPct || Math.abs(p.t) > 0.5));
    if (esPct) {
      comp = `<div class="comp">${partes.map((p) => `<div class="fila-c"><span>${p.b}</span><b>${fmtCelda(fila, p.t)}</b></div>`).join('')}</div>`;
    } else if (partes.length && partes.every((p) => p.t >= 0)) {
      const total = partes.reduce((a, p) => a + p.t, 0);
      comp = `<div class="comp"><div class="barra">${partes.map((p) => `<span style="width:${(p.t / total) * 100}%;background:var(${COLOR[p.b]})"></span>`).join('')}</div>`
        + `${partes.map((p) => `<div class="fila-c"><span>${p.b}</span><b>${Math.round((p.t / total) * 100)}%</b></div>`).join('')}</div>`;
    }
  }
  return `<tr class="detalle"><td colspan="${n + 2}"><div class="evolucion-panel">
    <div class="evolucion-titulo"><b>${esc(fila.nom)}</b><span>Evolución completa · ${n} ${plural(st.grano)}</span></div>
    <div>${stats}</div><div class="evolucion-grafico"><div class="graf" role="img" aria-label="Evolución de ${esc(fila.nom)} · ${st.modo === 'familia' ? 'por familia' : 'total'}">${svg}${puntos}</div>${vari}
      <div class="evolucion-periodos">${w.per.map(p => `<span>${esc(p.rot)}</span>`).join('')}</div></div><div>${comp}</div>
  </div></td></tr>`;
}

function notas(st, data, w) {
  const tot = (arr) => cortar(arr, w).reduce((a, x) => a + x, 0);
  const vEx = data.venta_extra || {}, cEx = data.costo_extra || {};
  const abiertos = st.notasAbiertas ||= new Set();
  const inventario = st.grano === 'mes'
    ? 'Inventario contado: último cierre de cada área en su mes operativo, valorizado como stock declarado × precio promedio. Los cierres registrados del 1 al 7 inclusive se asignan al mes anterior.'
    : 'Inventario del kardex al final del último día de cada período, sólo de productos activos, según la regla del Histórico del Almacén. El ajuste de un cierre cae en el período en que se registró: las semanas o quincenas pueden no sumar el resultado mensual basado en conteos.';
  const extras = EXTRAS.map((g) => {
    const incluido = st.fams.has('Alimentos') && st.extra.has(g);
    const estado = g === 'Eventos' ? (incluido ? 'incluidos' : 'excluidos') : (incluido ? 'incluida' : 'excluida');
    return `<li><b>${g}: ${estado} en la selección actual.</b> En la ventana completa: venta neta S/ ${mil(tot(vEx[g]))} y costo histórico S/ ${mil(tot(cEx[g]))}. Sus casillas suman ambos importes a Alimentos; sólo tienen efecto cuando esa familia está seleccionada. Si se excluyen, su consumo puede seguir presente en inventarios y compras.</li>`;
  }).join('');
  return `<div class="notas">
  <details class="nota" data-nota="calculo"${abiertos.has('calculo') ? ' open' : ''}><summary>Cómo se calcula</summary><dl>
    <dt>Venta neta documentada</dt><dd>Comprobantes pagados y por cobrar − notas de crédito, sin IGV ni recargo; excluye cortesías y anulados. Se agrupa por día contable del turno de caja, no por fecha del cobro. La selección de familias y las casillas de Eventos y Venta interna determinan el alcance.</dd>
    <dt>Inventario inicial y final</dt><dd>${inventario} El inicial de un período es el final del anterior. El total de la ventana muestra el primer inventario inicial y el último final, sin sumarlos.</dd>
    <dt>Compras y salidas</dt><dd>Compras a valor neto, sin IGV, con las notas de crédito de proveedores restadas, por fecha del documento. Notas de salida procesadas a valor neto, por fecha de registro. Todas las salidas que no son bajas entran como deducción inicialmente; la × permite quitar una.</dd>
    <dt>Consumo operativo valorizado</dt><dd>Inventario inicial + compras − inventario final. Es la variación valorizada disponible para analizar el consumo del período; incluye los efectos de registros, ajustes de inventario y valorización.</dd>
    <dt>Consumos no vendidos</dt><dd>Notas de salida seleccionadas que no son bajas + costo de cortesías. Las bajas permanecen dentro del consumo carta y se presentan aparte para conciliar la diferencia.</dd>
    <dt>Cortesías y descuentos</dt><dd>Las cortesías se valorizan al costo histórico registrado y se excluyen de la venta documentada. Costo de descuentos = costo del plato × proporción descontada de la línea; se ajusta por la devolución de convenios bancarios configurada. Esta referencia comercial no se resta del consumo carta ni del costo del Sistema.</dd>
    <dt>Consumo carta</dt><dd>Consumo operativo valorizado − consumos no vendidos seleccionados. Es la base de consumo que se compara con el costo completo del Sistema; puede contener diferencias pendientes de explicar.</dd>
    <dt>Costo histórico de lo vendido</dt><dd>Costo guardado en el pedido, incluidos componentes de combos y propiedades, respetando cantidades y ajustes positivos o negativos. Las notas de crédito revierten la parte correspondiente del costo de la venta. No se recalcula con la receta ni los precios actuales.</dd>
    <dt>Descuentos separados</dt><dd>El costo histórico completo de lo vendido se compara con el consumo carta. Los descuentos y el margen se presentan en el análisis comercial.</dd>
    <dt>Diferencia y saldo pendiente</dt><dd>Diferencia = consumo carta − costo completo del Sistema. Diferencia pendiente de conciliación = diferencia − bajas registradas. El saldo por sí solo no demuestra una pérdida física: requiere revisar fechas, alcance, clasificación, recetas, valorización y registros.</dd>
    <dt>Porcentajes y margen</dt><dd>Cada % de costo divide su costo o consumo entre la venta neta documentada de la misma selección. Margen bruto = venta neta documentada − consumo carta. Diferencia en puntos = % consumo carta − % costo completo del Sistema.</dd>
  </dl></details>
  <details class="nota alerta" data-nota="referencias"${abiertos.has('referencias') ? ' open' : ''}><summary>Referencias Inforest y alcance</summary><ul>
    <li><b>Referencia del costo: Paloteo de Producción → Comparativo → «(a) Ventas en el rango» → Precio costo.</b> Sin «Evaluar por Día Contable», el comparativo revisado exige que tanto el pedido como el comprobante estén dentro del rango. Esta vista agrupa venta y costo por día contable del turno: para comparar deben conciliarse ambas fechas, las notas de crédito y los filtros.</li>
    <li><b>Referencia de venta: Registro de Ventas.</b> En modo por fecha de emisión, selecciona comprobantes por emisión y puede incluir cuentas por cobrar; aquí se agrupan por turno. La venta documentada no representa necesariamente cobros del período.</li>
    <li><b>Referencias del Almacén:</b> cierres de inventario o Histórico del Almacén para existencias, compras netas y «Relación de Notas de Salidas» para salidas. El consumo y su conciliación combinan esas fuentes en la webapp; no equivalen por sí solos a un reporte único de Inforest.</li>
    <li><b>Familias de insumos y grupos de carta son clasificaciones distintas.</b> Inventario, compras y salidas usan familias del Almacén; venta y costo del Sistema usan grupos de carta. Una receta puede consumir insumos de otra familia, por lo que cada fila familiar requiere conciliar su composición.</li>
    <li><b>Envases:</b> entra en inventario, compras y salidas, pero no tiene venta ni costo del Sistema propio en esta agrupación. Su inclusión puede ampliar la diferencia; quitarlo no corrige por sí solo las diferencias de clasificación de ingredientes.</li>
    ${extras}
    <li><b>Costos de producción queda fuera</b> de inventarios, compras y salidas.</li>
    <li><b>Mes desde 2024.</b> Requiere inventario inicial y final y datos de venta del mes; las observaciones de valorización se muestran por período y familia. Semana y Quincena conservan su histórico desde octubre 2025, basado en Kardex.</li>
  </ul></details></div>`;
}

// ── Eventos: uno solo en la raíz, que sobrevive a cada dibujo ──────────
function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const st = raiz.__st;
    const b = ev.target.closest('button, [data-seleccionar]');
    if (!b || !raiz.contains(b)) return;
    if (b.dataset.fila) {
      st.abierta = st.abierta === b.dataset.fila ? null : b.dataset.fila;
      st.modo = 'total';
    } else if (b.dataset.quitar) {
      if (!st.quitadas.includes(b.dataset.quitar)) st.quitadas.push(b.dataset.quitar);
      if (st.abierta === `s_${b.dataset.quitar}`) st.abierta = null;
      guardar('costos_salidas_quitadas', st.quitadas);
    } else if (b.dataset.agregar) {
      st.quitadas = st.quitadas.filter((t) => t !== b.dataset.agregar);
      st.menu = false;
      guardar('costos_salidas_quitadas', st.quitadas);
    } else if (b.dataset.seleccionar) {
      st.seleccionado = b.dataset.seleccionar;
      st.enfocarSeleccion = true;
    } else if (b.hasAttribute('data-calculo')) {
      st.calculoAbierto = !st.calculoAbierto;
    } else if (b.dataset.metrica) {
      st.metrica = b.dataset.metrica;
    } else if (b.hasAttribute('data-revisar-mes')) {
      st.calculoAbierto = true;
      st.notasAbiertas.add('calidad');
      st.irCalculo = true;
    } else if (b.hasAttribute('data-exportar-observaciones')) {
      exportarObservaciones(st);
      return;
    } else if (b.hasAttribute('data-grupo')) {
      st.grupoAbierto = !st.grupoAbierto;
      if (!st.grupoAbierto && /^(bajas|cort|s_)/.test(st.abierta || '')) st.abierta = null;
      guardar('costos_grupo_abierto', st.grupoAbierto);
    } else if (b.hasAttribute('data-menu')) {
      st.menu = !st.menu;
    } else if (b.dataset.modo) {
      st.modo = b.dataset.modo;
    } else if (b.dataset.ventana) {
      st.ini[st.grano] += Number(b.dataset.ventana) * (st.cantidad || VENTANA);
    } else {
      return;
    }
    dibujar(raiz);
  });
  raiz.addEventListener('change', (ev) => {
    const st = raiz.__st, el = ev.target;
    if (el.matches('[data-extra]')) {
      if (el.checked) st.extra.add(el.dataset.extra); else st.extra.delete(el.dataset.extra);
      guardar('costos_sumar', [...st.extra]);
    } else if (el.matches('[data-anio]')) {
      st.anio = el.value || null;
      st.ini.mes = el.value ? Math.max(0, st.data.periodos.findIndex(p => p.k.startsWith(el.value + '-'))) : Number.MAX_SAFE_INTEGER;
      st.seleccionado = null;
    } else if (el.matches('[data-cantidad]')) {
      st.cantidad = Number(el.value);
    } else if (el.matches('[data-grano-sel]')) {
      st.grano = el.value;
      st.abierta = null;
      guardar('costos_grano', st.grano);
    } else if (el.matches('[data-fam-chk]')) {
      const f = el.dataset.famChk;
      if (el.checked) st.fams.add(f); else if (st.fams.size > 1) st.fams.delete(f);
      st.ddAbierto = true;
      guardar('costos_fams', [...st.fams]);
    } else {
      return;
    }
    dibujar(raiz);
  });
  // El desplegable de familias se queda abierto mientras se marcan casillas
  // (cada cambio redibuja) y se cierra con un clic fuera de él.
  raiz.addEventListener('toggle', (ev) => {
    if (ev.target.matches && ev.target.matches('details.dd')) raiz.__st.ddAbierto = ev.target.open;
    if (ev.target.matches && ev.target.matches('details[data-nota]')) {
      const abiertas = raiz.__st.notasAbiertas, clave = ev.target.dataset.nota;
      if (ev.target.open) abiertas.add(clave); else abiertas.delete(clave);
    }
  }, true);
  raiz.addEventListener('keydown', ev => {
    const punto = ev.target.closest('circle[data-seleccionar]');
    if (punto && (ev.key === 'Enter' || ev.key === ' ')) {
      ev.preventDefault();
      raiz.__st.seleccionado = punto.dataset.seleccionar;
      raiz.__st.enfocarSeleccion = true;
      dibujar(raiz);
    }
  });
  document.addEventListener('click', (ev) => {
    const dd = raiz.querySelector('details.dd');
    if (dd && dd.open && !ev.composedPath().includes(dd)) { dd.open = false; raiz.__st.ddAbierto = false; }
  });
  const observador = new ResizeObserver(() => raiz.__st.actualizarAncho?.());
  observador.observe(raiz);
}

export default function (component) {
  const { data, parentElement } = component;
  let raiz = parentElement.querySelector('.cv');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'cv';
    parentElement.appendChild(raiz);
    const fams = leer('costos_fams', BUCK).filter((b) => BUCK.includes(b));
    raiz.__st = {
      fams: new Set(fams.length ? fams : BUCK),
      // Eventos entra por defecto a la venta (a pedido, 2026-10-09); Venta
      // interna, sólo si se marca. Se guarda lo marcado, en otra clave que
      // el interruptor único de antes (`costos_extra`, que se ignora).
      extra: new Set(leer('costos_sumar', ['Eventos']).filter((g) => EXTRAS.includes(g))),
      // Lo que se guarda es lo QUITADO: todo lo demás entra. (Hasta el
      // 2026-10-09 se guardaba lo añadido, en `costos_salidas`, que se ignora.)
      quitadas: leer('costos_salidas_quitadas', []).filter((t) => typeof t === 'string'),
      agregadas: [],
      calculoAbierto: false, cantidad: VENTANA, seleccionado: null, anio: null, metrica: 'porcentaje',
      abierta: null, modo: 'total', menu: false, grano: leer('costos_grano', 'mes'),
      grupoAbierto: leer('costos_grupo_abierto', false) === true,
      notasAbiertas: new Set(),
      ini: { mes: Number.MAX_SAFE_INTEGER, quincena: Number.MAX_SAFE_INTEGER, semana: Number.MAX_SAFE_INTEGER },
    };
    if (data?.desde_resumen) {
      const i = (data.granos?.mes?.periodos || []).findIndex(p => p.k === data.mes_inicial);
      raiz.__st.grano = 'mes';
      raiz.__st.seleccionado = data.mes_inicial;
      raiz.__st.fams = new Set(BUCK);
      raiz.__st.extra = new Set(['Eventos']);
      raiz.__st.quitadas = [];
      if (i >= 0) raiz.__st.ini.mes = Math.max(0, i - VENTANA + 1);
    }
    enlazar(raiz);
  }
  const st = raiz.__st;
  st.todo = data || {};
  dibujar(raiz);
}
