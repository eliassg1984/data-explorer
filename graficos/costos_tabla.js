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
const VENTANA = 12;
const BAJAS = 'Bajas';

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
  const ini = Math.max(0, Math.min(st.ini[st.grano], n - VENTANA));
  const fin = Math.min(n, ini + VENTANA);
  return { ini, fin, per: data.periodos.slice(ini, fin) };
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
  };
  if (st.extra && b === 'Alimentos') {
    for (const g of Object.keys(data.venta_extra || {})) {
      r.v = suma(r.v, cortar(data.venta_extra[g], w));
      r.pos = suma(r.pos, cortar((data.costo_extra || {})[g], w));
    }
  }
  r.operativo = resta(suma(r.ii, r.c), r.fi);
  // Consumos no vendidos: las bajas, el costo de las cortesías y las demás
  // salidas que no se quitaron. Es lo que va del consumo operativo al carta.
  let nv = suma(r.bajas, r.cort);
  for (const t of st.agregadas) {
    r[`s_${t}`] = de((data.salidas || {})[t]);
    nv = suma(nv, r[`s_${t}`]);
  }
  r.nv = nv;
  r.carta = resta(r.operativo, nv);
  r.margen = resta(r.v, r.carta);
  r.dif = resta(r.carta, r.pos);
  return r;
}

function filas(st) {
  const f = [
    // La venta arriba, como en un estado de resultados: es la base de cada %.
    { k: 'v', nom: 'Venta neta', tipo: 'suma', sentido: 'bien', calc: true },
    { k: 'ii', nom: 'Inventario inicial', tipo: 'ini', sentido: 'neutro', fuerte: true },
    { k: 'c', nom: 'Compras', signo: '+', tipo: 'suma', sentido: 'mal' },
    { k: 'fi', nom: 'Inventario final', signo: '−', tipo: 'fin', sentido: 'neutro' },
    { k: 'operativo', nom: 'Consumo operativo', nota: 'inventario inicial + compras − inventario final', signo: '=', tipo: 'suma', sentido: 'mal', calc: true, fuerte: true },
    { k: 'p_operativo', nom: '% costo operativo', tipo: 'pct', sentido: 'mal', num: 'operativo', den: 'v' },
    // El grupo (a pedido, 2026-10-09): lo consumido que no se vendió, en su
    // nombre de control de costos. Cerrado es UNA fila con el total; abierto
    // crece hacia abajo con sus dos tramos —lo que viene del Almacén y lo
    // que viene del Sistema Restaurante—, que contablemente son cosas
    // distintas (merma o desmedro, gasto de personal, promoción).
    { k: 'nv', nom: 'Consumos no vendidos', nota: 'bajas, consumo interno y cortesías', signo: '−', tipo: 'suma', sentido: 'mal', grupo: true, fuerte: true },
  ];
  if (st.grupoAbierto) {
    f.push({ tramo: 'Notas de salida del Almacén' });
    f.push({ k: 'bajas', nom: 'Bajas', tipo: 'suma', sentido: 'mal', hijo: true });
    for (const t of st.agregadas) f.push({ k: `s_${t}`, nom: t, tipo: 'suma', sentido: 'mal', quitar: t, hijo: true });
    f.push({ agregar: true });
    f.push({ tramo: 'Sistema Restaurante' });
    f.push({ k: 'cort', nom: 'Costo de cortesías', tipo: 'suma', sentido: 'mal', hijo: true });
  }
  f.push({ k: 'carta', nom: 'Consumo carta', nota: 'consumo operativo − consumos no vendidos', signo: '=', tipo: 'suma', sentido: 'mal', calc: true, fuerte: true });
  f.push({ k: 'p_carta', nom: '% costo carta real', tipo: 'pct', sentido: 'mal', num: 'carta', den: 'v', calc: true });
  f.push({ k: 'margen', nom: 'Margen bruto', nota: 'venta − consumo carta', signo: '=', tipo: 'suma', sentido: 'bien', calc: true, fuerte: true });
  f.push({ sec: 'Contra el Sistema Restaurante (Paloteo comparativo)' });
  f.push({ k: 'pos', nom: 'Costo según Sistema Restaurante', tipo: 'suma', sentido: 'mal' });
  f.push({ k: 'p_pos', nom: '% costo según Sistema Restaurante', tipo: 'pct', sentido: 'mal', num: 'pos', den: 'v' });
  f.push({ k: 'dif', nom: 'Diferencia', nota: 'consumo carta − Sistema Restaurante', signo: '=', tipo: 'suma', sentido: 'mal', calc: true, fuerte: true });
  f.push({ k: 'p_dif', nom: 'Diferencia en puntos', tipo: 'pp', sentido: 'mal', calc: true });
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
  const hayMas = data.periodos.length > VENTANA;
  const aviso = esMes ? '' : `Por ${st.grano}, el inventario es el del kardex al final de cada período, no lo contado: el ajuste de cada cierre cae entero en el período del cierre, y por eso las ${plural(st.grano)} no suman el mes.`;
  let html = `<div class="cv-cab"><div class="cv-tit"><h2>Estado de costo de ventas</h2>
    <span class="cv-rango">${esc(w.per[0].rot)}${sep}${esc(w.per[n - 1].rot)} · ${n} ${plural(st.grano)}${esMes ? ' operativos' : ''}</span>
    ${hayMas ? `<span class="cv-ventana"><button type="button" data-ventana="-1" aria-label="Períodos anteriores" ${w.ini === 0 ? 'disabled' : ''}>‹</button><button type="button" data-ventana="1" aria-label="Períodos siguientes" ${w.fin >= data.periodos.length ? 'disabled' : ''}>›</button></span>` : ''}
    ${aviso ? `<span class="cv-kardex" title="${esc(aviso)}">inventario del kardex ⓘ</span>` : ''}</div>
    <div class="cv-controles">`;
  if (hay.length > 1) {
    html += `<label class="cv-campo"><span class="cv-rot">Período</span><select data-grano-sel aria-label="Período">${hay.map(([g, nom]) =>
      `<option value="${g}"${st.grano === g ? ' selected' : ''}>${nom}</option>`).join('')}</select></label>`;
  }
  const famTxt = F.length === BUCK.length ? 'Todas' : F.length === 1 ? F[0] : `${F.length} de ${BUCK.length}`;
  html += `<details class="dd"${st.ddAbierto ? ' open' : ''}><summary><span class="cv-rot">Familias</span><span class="dd-val">${famTxt}</span><span class="dd-fl">▾</span></summary>
      <div class="dd-panel">${BUCK.map((b) => `<label class="dd-op"><input type="checkbox" data-fam-chk="${b}" ${st.fams.has(b) ? 'checked' : ''}><span class="pt" style="background:var(${COLOR[b]})"></span>${b}</label>`).join('')}
      <span class="dd-nota">Para comparar contra el Sistema Restaurante, sin Envases: no los costea.</span></div></details>
    <label class="interruptor"><input type="checkbox" data-extra ${st.extra ? 'checked' : ''}> Sumar Eventos y Venta interna</label>
    </div></div>`;

  // La tabla
  const cols = `<col class="c-lab">${w.per.map(() => '<col class="c-mes">').join('')}<col class="c-tot">`;
  const ths = w.per.map((p) => `<th scope="col">${esc(p.rot)}<span class="sub">${esc(p.sub || '')}</span></th>`).join('');
  let cuerpo = '';
  for (const fila of filas(st)) {
    if (fila.sec) { cuerpo += `<tr class="sec"><td colspan="${n + 2}">${fila.sec}</td></tr>`; continue; }
    if (fila.agregar) { cuerpo += filaAgregar(st, data, w, F, n); continue; }
    if (fila.tramo) { cuerpo += `<tr class="tramo"><td colspan="${n + 2}">${fila.tramo}</td></tr>`; continue; }
    const val = valores(st, data, w, fila, F);
    const abierta = st.abierta === fila.k;
    const cls = ['fila', fila.calc ? 'calc' : '', fila.fuerte ? 'fuerte' : '', abierta ? 'abierta' : '',
      fila.hijo ? 'hijo' : '', fila.grupo ? 'grupo' : '', fila.grupo && st.grupoAbierto ? 'grupo-abierto' : ''].join(' ');
    const tip = fila.nota ? ` title="${esc(`${fila.nom}: ${fila.nota}`)}"` : '';
    cuerpo += `<tr class="${cls}"><td class="lab"><div class="fila-lab">`
      + (fila.grupo ? `<button type="button" class="chev" data-grupo aria-expanded="${!!st.grupoAbierto}" aria-label="${st.grupoAbierto ? 'Cerrar' : 'Abrir'} el detalle de ${esc(fila.nom)}">${st.grupoAbierto ? '▾' : '▸'}</button>` : '')
      + `<button type="button" class="fila-btn" data-fila="${esc(fila.k)}" aria-expanded="${abierta}"${tip}><span class="signo">${fila.signo || ''}</span>`
      + `<span class="nom">${esc(fila.nom)}</span><span class="flecha">▼</span></button>`
      + (fila.quitar ? `<button type="button" class="quitar" data-quitar="${esc(fila.quitar)}" aria-label="Quitar ${esc(fila.quitar)}">×</button>` : '')
      + `</div></td>${val.mes.map((x) => `<td class="${claseCelda(fila, x)}">${fmtCelda(fila, x)}</td>`).join('')}`
      + `<td class="tot ${claseCelda(fila, val.tot)}">${fmtCelda(fila, val.tot)}</td></tr>`;
    if (abierta) cuerpo += detalle(st, data, w, fila, F, val);
  }
  html += `<div class="desliza"><table><colgroup>${cols}</colgroup><thead><tr><th class="lab" scope="col">Concepto<span class="sub">${esMes ? 'mes operativo · cierre' : 'kardex'}</span></th>${ths}<th class="tot" scope="col">${n} ${plural(st.grano)}<span class="sub">${esc(w.per[0].rot)}${sep}${esc(w.per[n - 1].rot)}</span></th></tr></thead><tbody>${cuerpo}</tbody></table></div>`;
  html += notas(data, w);

  const sx = raiz.querySelector('.desliza') ? raiz.querySelector('.desliza').scrollLeft : 0;
  raiz.innerHTML = html;
  const d = raiz.querySelector('.desliza');
  if (d) d.scrollLeft = sx;
  ajustar(raiz);
}

// Que la tabla entre ENTERA en la pantalla: si no entra con la densidad de
// siempre, se aprieta un grado (letra y renglones más chicos). Se mide sin
// la fila abierta —abrir una no tiene que cambiar la densidad— y contra el
// alto de la ventana menos el cromo de arriba y la fila del título.
const CROMO_PX = 96;
function ajustar(raiz) {
  const t = raiz.querySelector('table');
  if (!t) return;
  raiz.classList.remove('apretada');
  const det = t.querySelector('tr.detalle');
  const hijos = [...t.querySelectorAll('tr.hijo, tr.tramo, tr.agregar')].reduce((a, r) => a + r.offsetHeight, 0);
  const alto = t.offsetHeight - (det ? det.offsetHeight : 0) - hijos;
  if (alto > window.innerHeight - CROMO_PX) raiz.classList.add('apretada');
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
  return `<tr class="agregar"><td colspan="${n + 2}">${btn}${menu}</td></tr>`;
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
  return `<tr class="detalle"><td class="lab">${stats}</td><td colspan="${n}" class="graf-celda"><div class="graf">${svg}${puntos}</div>${vari}</td><td class="tot">${comp}</td></tr>`;
}

function notas(data, w) {
  const tot = (arr) => cortar(arr, w).reduce((a, x) => a + x, 0);
  const vEx = data.venta_extra || {}, cEx = data.costo_extra || {};
  const ev = 'Eventos', vi = 'Venta interna';
  return `<div class="notas">
  <details class="nota"><summary>De dónde sale cada fila</summary><dl>
    <dt>Venta neta</dt><dd>Sin IGV ni recargo, sin cortesías ni anulados, con las notas de crédito restando, por día del turno de caja. Grupos Alimentos, Bebidas con alcohol, sin alcohol y calientes, y Vinos y Espumantes.</dd>
    <dt>Inventario inicial y final</dt><dd>Por mes, el cierre de inventario de cada área en su mes operativo: el que se registra del 1 al 6 cuenta para el mes anterior. Se toma el último cierre de cada área en el mes, valorizado como se contó (stock declarado × precio promedio). Por quincena o semana no hay conteo: es el stock del kardex al final del último día, sólo de lo activo, con la regla del Histórico del Almacén. El inicial de un período es el final del anterior. Alimentos, Bebidas, Vinos y Envases.</dd>
    <dt>Compras</dt><dd>Valor neto, sin IGV, con las notas de crédito de los proveedores restadas, por fecha del documento.</dd>
    <dt>Bajas y las otras salidas</dt><dd>Notas de salida procesadas, a su valor neto, por fecha de registro, como la «Relación de Notas de Salidas» del Almacén.</dd>
    <dt>Costo de cortesías</dt><dd>Lo que el Sistema Restaurante facturó como cortesía en Alimentos, Bebidas y Vinos, a precio costo. Se resta porque su costo, «(a) Ventas en el rango», no las incluye: en el Paloteo son otro origen, «(b) Cortesías».</dd>
    <dt>Consumo operativo, consumos no vendidos y consumo carta</dt><dd>Consumo operativo = inventario inicial + compras − inventario final: todo lo que salió del almacén; no se compara con el Sistema Restaurante. Consumos no vendidos: lo consumido que no se vendió —las bajas, las demás notas de salida (entran todas; abierto el grupo, la × quita una) y el costo de las cortesías—; en control de costos, las deducciones que llevan del costo de lo consumido al costo de lo vendido. Consumo carta = consumo operativo − consumos no vendidos: lo que costó lo vendido, y es el que se compara con el Sistema Restaurante.</dd>
    <dt>Costo según Sistema Restaurante</dt><dd>El costo a precio costo de lo vendido en esos grupos: lo del Paloteo de Producción, tipo Comparativo, con origen «(a) Ventas en el rango». El Paloteo fecha por la apertura de la mesa y esta tabla por el turno: un pedido de medianoche del último día puede caer en otro mes.</dd>
  </dl></details>
  <details class="nota alerta"><summary>Antes de leer la diferencia</summary><ul>
    <li><b>Envases entra en inventario, compras y salidas, pero el Sistema Restaurante no lo costea.</b> Para comparar en igualdad, desmarcá Envases.</li>
    <li><b>Eventos y Venta interna gastan inventario y no están en la venta.</b> En estos períodos vendieron S/ ${mil(tot(vEx[ev]))} y S/ ${mil(tot(vEx[vi]))}, con un costo de S/ ${mil(tot(cEx[ev]))} y S/ ${mil(tot(cEx[vi]))}. Fuera de la venta, su consumo agranda la diferencia; el interruptor los suma a Alimentos.</li>
    <li><b>Costos de producción queda fuera</b> de inventarios, compras y salidas.</li>
    <li><b>Desde octubre 2025.</b> Antes, los cierres y el kardex no cuadran (setiembre 2025 tuvo un ajuste de S/ 627 mil al limpiar el inventario).</li>
  </ul></details></div>`;
}

// ── Eventos: uno solo en la raíz, que sobrevive a cada dibujo ──────────
function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const st = raiz.__st;
    const b = ev.target.closest('button');
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
    } else if (b.hasAttribute('data-grupo')) {
      st.grupoAbierto = !st.grupoAbierto;
      if (!st.grupoAbierto && /^(bajas|cort|s_)/.test(st.abierta || '')) st.abierta = null;
      guardar('costos_grupo_abierto', st.grupoAbierto);
    } else if (b.hasAttribute('data-menu')) {
      st.menu = !st.menu;
    } else if (b.dataset.modo) {
      st.modo = b.dataset.modo;
    } else if (b.dataset.ventana) {
      st.ini[st.grano] += Number(b.dataset.ventana) * VENTANA;
    } else {
      return;
    }
    dibujar(raiz);
  });
  raiz.addEventListener('change', (ev) => {
    const st = raiz.__st, el = ev.target;
    if (el.matches('[data-extra]')) {
      st.extra = el.checked;
      guardar('costos_extra', st.extra);
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
  }, true);
  document.addEventListener('click', (ev) => {
    const dd = raiz.querySelector('details.dd');
    if (dd && dd.open && !ev.composedPath().includes(dd)) { dd.open = false; raiz.__st.ddAbierto = false; }
  });
  window.addEventListener('resize', () => ajustar(raiz));
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
      extra: leer('costos_extra', false) === true,
      // Lo que se guarda es lo QUITADO: todo lo demás entra. (Hasta el
      // 2026-10-09 se guardaba lo añadido, en `costos_salidas`, que se ignora.)
      quitadas: leer('costos_salidas_quitadas', []).filter((t) => typeof t === 'string'),
      agregadas: [],
      abierta: null, modo: 'total', menu: false, grano: leer('costos_grano', 'mes'),
      grupoAbierto: leer('costos_grupo_abierto', false) === true,
      ini: { mes: Number.MAX_SAFE_INTEGER, quincena: Number.MAX_SAFE_INTEGER, semana: Number.MAX_SAFE_INTEGER },
    };
    enlazar(raiz);
  }
  const st = raiz.__st;
  st.todo = data || {};
  dibujar(raiz);
}
