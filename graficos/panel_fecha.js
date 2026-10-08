// Panel del selector de fecha de las tarjetas (regla #616).
//
// Lo monta graficos/panel_fecha.py con st.components.v2 (sin iframe, estilos
// en un shadow root). Todo lo que pasa acá adentro es del navegador; a Python
// le llega sólo el rango elegido, como el trigger «rango»: {a, b} en ISO.
//
// Python manda en `data`: min y max (los datos), a y b (lo vigente), los
// atajos ya calculados ({k, nombre, grupo, a, b, pista}) y la nota del pie.
// Los atajos NO se calculan acá: el texto del botón los necesita igual, y dos
// cuentas del mismo atajo se desincronizan.

const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const MES_L = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
  'setiembre', 'octubre', 'noviembre', 'diciembre'];
const DSEM = ['lu', 'ma', 'mi', 'ju', 'vi', 'sá', 'do'];
const DSEM_L = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
const DIA = 864e5;

// Cuánto espera un mes (o un día) suelto antes de avisar a Python. Si llega
// el segundo clic, se avisa UNA vez el rango entero: cada aviso recalcula la
// tarjeta, y dos seguidos eran justo lo que se sentía inestable. Mientras el
// cursor recorre otros casilleros la espera se renueva (va a buscar el
// último); al vencer, el mes suelto queda elegido y el próximo clic empieza
// de nuevo — sin eso, elegir marzo y después noviembre armaba marzo-noviembre.
const ESPERA_MS = 1200;
// Cambiar de año o de mes con un mes ya marcado es ir a buscar el último:
// la espera se estira.
const ESPERA_NAVEGANDO_MS = 4000;

const dn = (y, m, d) => Math.round(Date.UTC(y, m - 1, d) / DIA);
const ymd = (n) => { const t = new Date(n * DIA); return [t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate()]; };
const dow = (n) => (new Date(n * DIA).getUTCDay() + 6) % 7;
const dia = (n) => ymd(n)[2];
const finMes = (y, m) => dn(y, m + 1, 1) - 1;
const deIso = (s) => { if (!s) return null; const [y, m, d] = String(s).split('-').map(Number); return dn(y, m, d); };
const aIso = (n) => { const [y, m, d] = ymd(n); return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`; };
const idxMes = ([y, m]) => y * 12 + m - 1;
const deIdx = (i) => [Math.floor(i / 12), (i % 12) + 1];
const mesMas = (ym, k) => deIdx(idxMes(ym) + k);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const IC_IZQ = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M10 3.5L5.5 8 10 12.5"/></svg>';
const IC_DER = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3.5L10.5 8 6 12.5"/></svg>';

function fLargo(a, b) {
  const [ya, ma, da] = ymd(a), [yb, mb, db] = ymd(b);
  if (a === b) return `El ${db} de ${MES_L[mb - 1]} de ${yb}`;
  if (ya === yb && ma === mb) return `Del ${da} al ${db} de ${MES_L[mb - 1]} de ${yb}`;
  if (ya === yb) return `Del ${da} de ${MES_L[ma - 1]} al ${db} de ${MES_L[mb - 1]} de ${yb}`;
  return `Del ${da} de ${MES_L[ma - 1]} de ${ya} al ${db} de ${MES_L[mb - 1]} de ${yb}`;
}
const fDias = (n) => (n === 1 ? '1 día' : `${n.toLocaleString('en-US')} días`);

// ── Estado ───────────────────────────────────────────────────────────────
// Vive en el elemento raíz: la función se vuelve a llamar en cada corrida de
// Python con los datos nuevos, pero el DOM (y esto) sobreviven mientras el
// panel esté abierto.
function sincronizar(st, data, primera) {
  st.min = deIso(data.min);
  st.max = deIso(data.max);
  st.atajos = (data.atajos || []).map((x) => ({ ...x, a: deIso(x.a), b: deIso(x.b) }));
  st.nota = data.nota || '';
  const a = deIso(data.a), b = deIso(data.b);
  // Lo de Python manda, salvo que haya una elección todavía sin avisar: la
  // corrida en curso todavía no la conoce.
  if (!st.timer) {
    if (a != null && b != null) { st.a = Math.max(a, st.min); st.b = Math.min(b, st.max); }
    else if (st.a == null) { st.a = st.min; st.b = st.max; }
  }
  if (primera) {
    st.modo = 'meses';
    st.ancla = null;
    st.timer = null;
    verHasta(st, st.b);
  }
}

// La vista (qué año, qué mes) va a donde TERMINA lo elegido.
function verHasta(st, fin) {
  const [y, m] = ymd(fin);
  st.anio = y;
  st.mes = [y, m];
}

const atajoActivo = (st) => st.atajos.find((x) => x.a === st.a && x.b === st.b) || null;
const topeMes = (st, ym) => deIdx(Math.min(idxMes(ymd(st.max)), Math.max(idxMes(ymd(st.min)), idxMes(ym))));

// ── Dibujo ───────────────────────────────────────────────────────────────
function tramo(st, s, e) {
  const ds = Math.max(s, st.min), de = Math.min(e, st.max);
  if (de < ds) return { dis: true };
  const r = {};
  const ia = Math.max(ds, st.a), ib = Math.min(de, st.b);
  if (ib >= ia) {
    Object.assign(r, { en: true, ia, ib, parcial: ia > ds || ib < de,
      ini: st.a >= s && st.a <= e, fin: st.b >= s && st.b <= e });
  }
  if (st.ancla && st.ancla[0] === s && st.ancla[1] === e) r.ancla = true;
  return r;
}
const clases = (r, extra) => ['cel', r.en && 'en', r.ini && 'ini', r.fin && 'fin', r.parcial && 'parcial',
  r.ancla && 'ancla', extra].filter(Boolean).join(' ');

function celdaMes(st, y, m) {
  const s = dn(y, m, 1), e = finMes(y, m), r = tramo(st, s, e);
  let sub = '';
  if (r.en && r.parcial) sub = r.ia === r.ib ? String(dia(r.ia)) : `${dia(r.ia)}–${dia(r.ib)}`;
  else if (!r.dis && e > st.max) sub = `al ${dia(st.max)}`;
  let tit = `${MES_L[m - 1]} ${y}`;
  if (r.dis) tit += ' · sin datos';
  else if (r.en && r.parcial) tit += ` · del ${dia(r.ia)} al ${dia(r.ib)}`;
  return `<button type="button" class="${clases(r)}" data-s="${s}" data-e="${e}"${r.dis ? ' disabled' : ''}`
    + ` aria-pressed="${!!r.en}" title="${tit}"><span>${MES[m - 1]}</span>${sub ? `<small>${sub}</small>` : ''}</button>`;
}

function calendario(st, y, m) {
  const s = dn(y, m, 1), e = finMes(y, m);
  let h = '<div class="cal-sem">' + DSEM.map((d) => `<span>${d}</span>`).join('') + '</div><div class="cal-dias">';
  for (let i = 0; i < dow(s); i++) h += '<span></span>';
  for (let d = s; d <= e; d++) {
    const r = tramo(st, d, d);
    const tit = `${DSEM_L[dow(d)]} ${dia(d)} de ${MES_L[m - 1]}`
      + (d === st.max ? ' · último día con datos' : r.dis ? ' · sin datos' : '');
    h += `<button type="button" class="${clases(r, d === st.max ? 'ultimo' : '')}" data-s="${d}" data-e="${d}"`
      + `${r.dis ? ' disabled' : ''} aria-pressed="${!!r.en}" title="${tit}">${dia(d)}</button>`;
  }
  return h + '</div>';
}

const flecha = (d, ok) => `<button type="button" class="flecha" data-nav="${d}"${ok ? '' : ' disabled'}`
  + ` aria-label="${d < 0 ? 'Mes anterior' : 'Mes siguiente'}">${d < 0 ? IC_IZQ : IC_DER}</button>`;

function textoPista(st) {
  if (st.ancla) {
    const [y, m, d] = ymd(st.ancla[0]);
    return st.modo === 'meses'
      ? `Elegido: ${MES_L[m - 1]} ${y}. Un clic en otro mes suma los del medio.`
      : `Elegido: ${d} de ${MES_L[m - 1]}. Un clic en otro día suma los del medio.`;
  }
  return st.modo === 'meses'
    ? 'Un clic elige un mes. Para varios: clic en el primero y en el último.'
    : 'Un clic elige un día. Para un rango: clic en el primero y en el último.';
}

function dibujar(raiz) {
  const st = raiz.__st;
  const activo = atajoActivo(st);
  let h = '<div class="pa"><div class="pa-atajos">';
  const grupos = [];
  for (const x of st.atajos) {
    let g = grupos.find((g2) => g2.tit === x.grupo);
    if (!g) { g = { tit: x.grupo, xs: [] }; grupos.push(g); }
    g.xs.push(x);
  }
  for (const g of grupos) {
    h += `<div class="grupo"><div class="grupo-tit">${esc(g.tit)}</div>`;
    for (const x of g.xs) {
      h += `<button type="button" class="atajo" data-k="${esc(x.k)}" aria-pressed="${!!activo && activo.k === x.k}">`
        + `<span class="at-nom">${esc(x.nombre)}</span><span class="at-f">${esc(x.pista)}</span></button>`;
    }
    h += '</div>';
  }
  h += '</div><div class="pa-der">';
  h += '<div class="seg" role="group" aria-label="Elegir por">'
    + `<button type="button" data-modo="meses" aria-pressed="${st.modo === 'meses'}">Meses</button>`
    + `<button type="button" data-modo="dias" aria-pressed="${st.modo === 'dias'}">Días</button></div>`;
  // Los años son pestañas de lo que se VE; el punto marca dónde cae lo elegido.
  const verAnio = st.modo === 'meses' ? st.anio : st.mes[0];
  h += '<div class="anios" role="group" aria-label="Año">';
  for (let y = ymd(st.min)[0]; y <= ymd(st.max)[0]; y++) {
    const conSel = st.a <= dn(y, 12, 31) && st.b >= dn(y, 1, 1);
    h += `<button type="button" data-anio="${y}" aria-pressed="${y === verAnio}"${conSel ? ' class="con-sel"' : ''}`
      + ` title="${conSel ? `Lo elegido incluye ${y}` : `Ver ${y}`}">${y}</button>`;
  }
  h += '</div>';
  if (st.modo === 'meses') {
    h += '<div class="g-meses">';
    for (let m = 1; m <= 12; m++) h += celdaMes(st, st.anio, m);
    h += '</div>';
  } else {
    const [y, m] = st.mes;
    h += `<div class="nav">${flecha(-1, dn(y, m, 1) > st.min)}<span class="nav-tit">${MES_L[m - 1]} ${y}</span>`
      + `${flecha(1, finMes(y, m) < st.max)}</div>`;
    h += calendario(st, y, m);
  }
  h += `<p class="pista" aria-live="polite">${textoPista(st)}</p></div></div>`;
  h += `<div class="pie"><p class="pie-rango"><strong>${fLargo(st.a, st.b)}</strong> · ${fDias(st.b - st.a + 1)}</p>`
    + `<p class="pie-nota">${esc(st.nota)}</p></div>`;
  raiz.innerHTML = h;
  // Con muchos años las pestañas se deslizan: la que se ve, a la vista.
  const anios = raiz.querySelector('.anios');
  const vista = anios && anios.querySelector('[aria-pressed="true"]');
  if (vista && anios.scrollWidth > anios.clientWidth) {
    anios.scrollLeft = vista.offsetLeft - anios.clientWidth + vista.offsetWidth + 8;
  }
}

// ── Avisar a Python ──────────────────────────────────────────────────────
function enviarYa(st) {
  if (st.timer) { clearTimeout(st.timer); st.timer = null; }
  st.enviar('rango', { a: aIso(st.a), b: aIso(st.b) });
}

// La espera de un mes suelto: al vencer avisa y suelta el primer clic.
function programar(raiz, ms) {
  const st = raiz.__st;
  if (st.timer) clearTimeout(st.timer);
  st.timer = setTimeout(() => {
    st.timer = null;
    st.ancla = null;
    dibujar(raiz);
    enviarYa(st);
  }, ms);
}

function avisar(raiz, ahora) {
  const st = raiz.__st;
  if (st.timer) { clearTimeout(st.timer); st.timer = null; }
  dibujar(raiz);
  if (ahora) enviarYa(st);
  else programar(raiz, ESPERA_MS);
}

function estirarEspera(raiz, ms) {
  if (raiz.__st.timer) programar(raiz, ms);
}

function clicCelda(raiz, s, e) {
  const st = raiz.__st;
  if (!st.ancla) {
    st.ancla = [s, e];
    st.a = s;
    st.b = e;
    avisar(raiz, false);
    return;
  }
  const [as, ae] = st.ancla;
  st.ancla = null;
  st.a = Math.min(as, s);
  st.b = Math.max(ae, e);
  avisar(raiz, true);
}

function previa(raiz, s, e) {
  const st = raiz.__st;
  const cs = raiz.querySelectorAll('.cel');
  if (s == null || !st.ancla) { cs.forEach((c) => c.classList.remove('previa')); return; }
  const lo = Math.min(st.ancla[0], s), hi = Math.max(st.ancla[1], e);
  cs.forEach((c) => c.classList.toggle('previa', Number(c.dataset.s) >= lo && Number(c.dataset.e) <= hi));
}

function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (!b || b.disabled || !raiz.contains(b)) return;
    const st = raiz.__st;
    if (b.dataset.k) {
      const x = st.atajos.find((y) => y.k === b.dataset.k);
      if (!x) return;
      st.ancla = null;
      st.a = x.a;
      st.b = x.b;
      verHasta(st, x.b);
      avisar(raiz, true);
      return;
    }
    if (b.dataset.modo) {
      if (b.dataset.modo === st.modo) return;
      if (st.timer) enviarYa(st);
      st.ancla = null;
      if (b.dataset.modo === 'dias') {
        const [yb, mb] = ymd(st.b);
        st.mes = topeMes(st, [st.anio, yb === st.anio ? mb : st.mes[1]]);
      } else {
        st.anio = st.mes[0];
      }
      st.modo = b.dataset.modo;
      dibujar(raiz);
      return;
    }
    if (b.dataset.anio) {
      const y = Number(b.dataset.anio);
      if (st.modo === 'meses') st.anio = y;
      else st.mes = topeMes(st, [y, st.mes[1]]);
      estirarEspera(raiz, ESPERA_NAVEGANDO_MS);
      dibujar(raiz);
      return;
    }
    if (b.dataset.nav) {
      st.mes = topeMes(st, mesMas(st.mes, Number(b.dataset.nav)));
      estirarEspera(raiz, ESPERA_NAVEGANDO_MS);
      dibujar(raiz);
      return;
    }
    if (b.classList.contains('cel')) clicCelda(raiz, Number(b.dataset.s), Number(b.dataset.e));
  });
  raiz.addEventListener('pointerover', (ev) => {
    const c = ev.target.closest('.cel');
    const st = raiz.__st;
    if (!c || c.disabled || !st.ancla) return;
    previa(raiz, Number(c.dataset.s), Number(c.dataset.e));
    // Recorrer otros casilleros es ir a buscar el último: la espera se renueva.
    if (c !== st.ultimaCelda) { st.ultimaCelda = c; estirarEspera(raiz, ESPERA_MS); }
  });
  raiz.addEventListener('pointerleave', () => previa(raiz, null));
}

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  let raiz = parentElement.querySelector('.pf');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'pf';
    parentElement.appendChild(raiz);
    raiz.__st = { a: null, b: null, timer: null };
    sincronizar(raiz.__st, data || {}, true);
    enlazar(raiz);
  } else {
    sincronizar(raiz.__st, data || {}, false);
  }
  raiz.__st.enviar = setTriggerValue;
  dibujar(raiz);
  // Al cerrarse el panel con un mes marcado y la espera corriendo, se avisa
  // igual: lo marcado en pantalla es lo que el usuario cree haber elegido.
  return () => {
    const st = raiz.__st;
    if (st && st.timer) {
      try { enviarYa(st); } catch (_) { /* el panel ya no existe */ }
    }
  };
}
