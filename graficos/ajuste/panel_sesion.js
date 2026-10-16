// Panel de la SESIÓN de inventario de una vista de Ajuste (reglas #632 y #634).
//
// Lo monta graficos/ajuste/_comun.py::selector_sesion con st.components.v2
// (sin iframe, estilos en un shadow root), adentro del popover del botón de
// la sesión. Es la forma del mockup que aprobó el usuario: cada sesión con su
// neto y su detalle en dos renglones, «Todas / Sólo cierres» (y, en
// Distribución, «Una / Varias») como segmentados y los años como pestañas,
// las mismas del panel de fechas de Compras (graficos/panel_fecha.js).
//
// Python manda en `data`: las sesiones (de la más vieja a la más nueva, con
// su nombre, su detalle y su neto ya escritos), la elegida, las marcadas,
// los dos interruptores y el pie. A Python le llega una sola cosa, el
// trigger «accion»: {tipo: 'elegir'|'varias'|'solo'|'multi', ...}. El año
// que se ve es del navegador: no le importa a nadie más.

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function soles(v) {
  if (v == null) return '';
  const n = Math.round(Math.abs(v)).toLocaleString('en-US');
  if (Math.round(v) === 0) return 'S/ 0';
  return v > 0 ? `+S/ ${n}` : `−S/ ${n}`;
}
const clase = (v) => (v == null || Math.round(v) === 0 ? 'cero' : v > 0 ? 'pos' : 'neg');

function sincronizar(st, data, primera) {
  st.sesiones = data.sesiones || [];
  st.actual = data.actual;
  st.marcadas = new Set(data.marcadas || []);
  st.multi = !!data.multi;
  st.conMulti = !!data.con_multi;
  st.solo = !!data.solo;
  st.pie = data.pie || [];
  st.pieVarias = data.pie_varias || [];
  if (primera || st.anio == null) st.anio = anioDeLoElegido(st);
}

function sesion(st, k) { return st.sesiones.find((s) => s.k === k) || null; }

// El año que se ve al abrir: el de lo elegido (con «Varias», la más nueva).
function anioDeLoElegido(st) {
  let ref = sesion(st, st.actual);
  if (st.multi) {
    const marcadas = st.sesiones.filter((s) => st.marcadas.has(s.k));
    if (marcadas.length) ref = marcadas[marcadas.length - 1];
  }
  if (ref) return ref.anio;
  return st.sesiones.length ? st.sesiones[st.sesiones.length - 1].anio : null;
}

const elegida = (st, k) => (st.multi ? st.marcadas.has(k) : k === st.actual);

function dibujar(raiz) {
  const st = raiz.__st;
  const seg = (dato, opciones) => '<div class="seg" role="group">' + opciones.map(([v, rot, on, tit]) =>
    `<button type="button" data-${dato}="${v}" aria-pressed="${on}"${tit ? ` title="${esc(tit)}"` : ''}>${rot}</button>`).join('') + '</div>';
  let h = '<div class="cab"><span class="tit">Sesión de inventario</span><div class="segs">';
  if (st.conMulti) h += seg('multi', [['0', 'Una', !st.multi], ['1', 'Varias', st.multi]]);
  h += seg('solo', [['0', 'Todas', !st.solo],
    ['1', 'Sólo cierres', st.solo, 'Un cierre de mes es lo registrado del 1 al 7 del mes siguiente; lo demás es parcial.']]);
  h += '</div></div>';

  const anios = [...new Set(st.sesiones.map((s) => s.anio))].sort((a, b) => b - a);
  const conSel = new Set(st.sesiones.filter((s) => elegida(st, s.k)).map((s) => s.anio));
  h += '<div class="anios" role="group" aria-label="Año">';
  for (const y of anios) {
    h += `<button type="button" data-anio="${y}" aria-pressed="${y === st.anio}"${conSel.has(y) ? ' class="con-sel"' : ''}>${y}</button>`;
  }
  h += '</div>';

  const lista = st.sesiones.filter((s) => s.anio === st.anio && (!st.solo || s.tipo === 'cierre')).reverse();
  h += '<div class="lista">';
  if (!lista.length) h += `<p class="vacio">No hay ${st.solo ? 'cierres' : 'sesiones'} en ${st.anio}.</p>`;
  for (const s of lista) {
    h += `<button type="button" class="fila ${s.tipo}${st.multi ? ' casilla' : ''}" data-k="${esc(s.k)}" aria-pressed="${elegida(st, s.k)}">`
      + `<span class="n">${esc(s.nombre)}</span><span class="v ${clase(s.neto)}">${soles(s.neto)}</span>`
      + `<span class="m">${esc(s.meta)}</span></button>`;
  }
  h += '</div>';
  const pie = st.multi ? st.pieVarias : st.pie;
  h += '<div class="pie">' + pie.map((p) => `<p>${esc(p)}</p>`).join('') + '</div>';
  raiz.innerHTML = h;
  const sel = raiz.querySelector('.fila[aria-pressed="true"]');
  if (sel && raiz.__primera) { sel.scrollIntoView({ block: 'nearest' }); }
  raiz.__primera = false;
}

function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (!b || b.disabled || !raiz.contains(b)) return;
    const st = raiz.__st;
    if (b.dataset.k) {
      const k = b.dataset.k;
      if (st.multi) {
        if (st.marcadas.has(k)) { if (st.marcadas.size > 1) st.marcadas.delete(k); } else st.marcadas.add(k);
        const ks = st.sesiones.filter((s) => st.marcadas.has(s.k)).map((s) => s.k);
        st.enviar({ tipo: 'varias', ks });
      } else {
        if (k === st.actual) return;
        st.actual = k;
        st.enviar({ tipo: 'elegir', k });
      }
      dibujar(raiz);
      return;
    }
    if (b.dataset.solo) {
      const v = b.dataset.solo === '1';
      if (v === st.solo) return;
      st.solo = v;
      st.enviar({ tipo: 'solo', v });
      dibujar(raiz);
      return;
    }
    if (b.dataset.multi) {
      const v = b.dataset.multi === '1';
      if (v === st.multi) return;
      st.multi = v;
      if (v) st.marcadas = new Set([st.actual]);
      else {
        const marcadas = st.sesiones.filter((s) => st.marcadas.has(s.k));
        if (marcadas.length) st.actual = marcadas[marcadas.length - 1].k;
      }
      st.enviar({ tipo: 'multi', v });
      dibujar(raiz);
      return;
    }
    if (b.dataset.anio) {
      st.anio = Number(b.dataset.anio);
      dibujar(raiz);
    }
  });
}

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  let raiz = parentElement.querySelector('.ps');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'ps';
    parentElement.appendChild(raiz);
    raiz.__st = {};
    raiz.__primera = true;
    sincronizar(raiz.__st, data || {}, true);
    enlazar(raiz);
  } else {
    sincronizar(raiz.__st, data || {}, false);
  }
  // Un sello por aviso: dos clics iguales seguidos son dos avisos.
  raiz.__st.enviar = (accion) => setTriggerValue('accion', { ...accion, t: Date.now() });
  dibujar(raiz);
}
