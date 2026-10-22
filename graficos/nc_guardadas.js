// Recetas › «Nuevo Costeo» › «Guardadas» (regla #698).
//
// La monta formulario_receta.py::_render_guardadas con st.components.v2:
// la lista de las propuestas guardadas en R2 —buscar, filtrar por tipo— y,
// al costado, la ficha de la elegida: sus cifras, cómo estaba en el
// sistema si es una modificación, sus canales, sus líneas y lo nuevo que
// lleva. Es la forma del boceto aprobado
// (https://claude.ai/artifact/Rb2hkVYJQVLWy7NstKqufo). Elegir una vuelve a
// Python (`elegir`), que dibuja arriba «Abrir en el editor», el PDF y el
// Excel de ESA propuesta. Comparte la hoja de estilos de la receta
// (`nuevo_costeo.css`).
//
// Python manda en `data`: `propuestas` (ver formulario_receta.armar_guardadas),
// `sel`, `divisor` y `umbrales`.

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function dinero(v, dec = 2) {
  if (v == null || !isFinite(v)) return '—';
  const s = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  return `${v < -0.004 ? '−' : ''}S/ ${s}`;
}
const pct = (v) => (v == null || !isFinite(v) ? '—' : `${v.toFixed(1)} %`);
const num = (v) => (Math.round(v * 10000) / 10000).toLocaleString('en-US', { maximumFractionDigits: 4 });
const sinTilde = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
function nivel(d, p) {
  if (p == null) return '';
  return p > d.umbrales[1] ? 'rojo' : p > d.umbrales[0] ? 'ambar' : 'verde';
}
function estado(d, p) {
  if (!(p.pv > 0)) return ['ambar', 'sin precio de venta'];
  if (p.nuevos.length) return ['ambar', `${p.nuevos.length} ${p.nuevos.length === 1 ? 'artículo nuevo' : 'artículos nuevos'}`];
  const n = nivel(d, p.pct);
  return [n, `${pct(p.pct)} de costo`];
}

function htmlLista(d, st) {
  const tipos = [...new Set(d.propuestas.map((p) => p.tipo))];
  const q = sinTilde(st.q.trim());
  const vis = d.propuestas.filter((p) => (!st.tipo || p.tipo === st.tipo)
    && (!q || sinTilde(p.nombre).includes(q) || sinTilde(p.por).includes(q)));
  const chips = tipos.length > 1 ? tipos.map((t) => `<button type="button" class="ng-chip${st.tipo === t ? ' on' : ''}" data-acc="tipo" data-id="${esc(t)}">${esc(t)} · ${d.propuestas.filter((p) => p.tipo === t).length}</button>`).join('') : '';
  const filas = vis.map((p) => {
    const [cls, txt] = estado(d, p);
    return `<tr class="nc-f${p.id === st.sel ? ' sel' : ''}" data-acc="elegir" data-id="${esc(p.id)}">
      <td class="nc-ins"><div><b>${esc(p.nombre || '(sin nombre)')}</b></div><span>${esc(p.tipo)}</span></td>
      <td>${esc(p.por || '—')}</td><td class="num">${esc(p.cuando)}</td><td class="num">${p.n}</td>
      <td class="num">${dinero(p.costo)}</td><td><span class="pill ${cls}">${esc(txt)}</span></td></tr>`;
  }).join('');
  return `<div class="ng-cab"><label class="ng-buscar"><input type="search" data-acc="buscar" value="${esc(st.q)}" placeholder="Buscar por nombre o por quién" aria-label="Buscar propuesta"></label>${chips}</div>
    <div class="nc-tabla">${vis.length ? `<table><thead><tr><th>Propuesta</th><th>Guardada por</th><th class="num">Cuándo</th><th class="num">Líneas</th><th class="num">Costo</th><th>Estado</th></tr></thead><tbody>${filas}</tbody></table>`
      : '<div class="nc-vacio">Ninguna propuesta con ese filtro.</div>'}</div>
    <div class="nc-pie"><span class="nc-pie-txt">${d.propuestas.length} ${d.propuestas.length === 1 ? 'propuesta guardada' : 'propuestas guardadas'} en R2 · la más nueva primero</span></div>`;
}

function htmlFicha(d, st) {
  const p = d.propuestas.find((x) => x.id === st.sel);
  if (!p) return '<div class="nc-vacio">Elegí una propuesta de la lista.</div>';
  const neto = p.pv > 0 ? p.pv / d.divisor : 0;
  const cifra = (r, v, cls = '') => `<div><span>${r}</span><b class="num ${cls}">${v}</b></div>`;
  const sis = p.sistema ? `<div class="nc-nota">En el sistema: ${p.sistema.pv ? dinero(p.sistema.pv, p.sistema.pv % 1 ? 2 : 0) + ' · ' : ''}costo ${dinero(p.sistema.costo)}${p.sistema.pct != null ? ` · <b>${pct(p.sistema.pct)}</b> → propuesta <b class="${nivel(d, p.pct)}">${pct(p.pct)}</b>` : ''}</div>` : '';
  const canales = p.canales ? `<div class="nc-canales"><div class="nc-crot"><span>Precio por canal</span></div><table><tbody>${p.canales.map(([n, v]) => {
    const pc = v > 0 && p.costo > 0 ? p.costo / (v / d.divisor) * 100 : null;
    return `<tr><td>${esc(n)}</td><td class="num">${v > 0 ? dinero(v, v % 1 ? 2 : 0) : '—'}</td><td class="num"><span class="pill ${nivel(d, pc)}">${pct(pc)}</span></td></tr>`;
  }).join('')}</tbody></table></div>` : '';
  const lineas = p.lineas.map((l) => `<tr><td class="nc-ins"><div><b title="${esc(l.nombre)}">${esc(l.nombre)}</b>${l.tipo === 'nuevo' ? '<span class="nc-tag">nuevo</span>' : ''}</div></td>
      <td class="num">${num(l.cantidad)} <span class="ng-und">${esc(String(l.unidad).toLowerCase())}</span></td><td class="num">${dinero(l.cantidad * l.precio)}</td></tr>`).join('');
  const nuevos = p.nuevos.length ? `<div class="nc-fbloque"><div class="nc-crot"><span>Lo que el almacén todavía no tiene</span></div>${p.nuevos.map((t) => `<div class="nc-aviso">${esc(t)}</div>`).join('')}</div>` : '';
  const aviso = p.pv > 0 ? '' : '<div class="nc-aviso">Se guardó sin precio de venta: no hay % de costo que revisar.</div>';
  const cls = nivel(d, p.pct);
  return `<div class="ng-fcab"><span>${esc(p.tipo)} · guardada por ${esc(p.por || '—')} el ${esc(p.cuando_largo)}${p.area ? ' · área ' + esc(p.area) : ''}</span><h3>${esc(p.nombre || '(sin nombre)')}</h3></div>
    <div class="nc-cifras">${cifra('Costo', dinero(p.costo))}${cifra('Precio de venta', p.pv > 0 ? dinero(p.pv) : '—')}
      ${cifra('% de costo', pct(p.pct), cls)}${cifra('Utilidad', p.pv > 0 ? dinero(neto - p.costo) : '—')}</div>
    ${sis}${aviso}${canales}
    <div class="nc-fbloque"><div class="nc-crot"><span>${p.n} ${p.n === 1 ? 'línea' : 'líneas'}</span></div>
      <table class="ng-lineas"><tbody>${lineas}</tbody></table></div>
    ${nuevos}`;
}

function dibujar(raiz, solo) {
  const { data: d, st } = raiz.__d;
  if (!raiz.querySelector('.ng-cuerpo')) {
    raiz.innerHTML = '<div class="nc-cuerpo ng-cuerpo"><div class="nc-receta" data-zona="lista"></div><div class="nc-precio" data-zona="ficha"></div></div>';
  }
  const lista = raiz.querySelector('[data-zona="lista"]');
  if (solo === 'filas') {
    const tmp = document.createElement('div');
    tmp.innerHTML = htmlLista(d, st);
    lista.querySelector('.nc-tabla').replaceWith(tmp.querySelector('.nc-tabla'));
  } else lista.innerHTML = htmlLista(d, st);
  raiz.querySelector('[data-zona="ficha"]').innerHTML = htmlFicha(d, st);
}

function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b)) return;
    const st = raiz.__d.st;
    if (b.dataset.acc === 'elegir') {
      if (st.sel === b.dataset.id) return;
      st.sel = b.dataset.id;
      dibujar(raiz, 'filas');
      raiz.__d.enviar('elegir', st.sel);
    } else if (b.dataset.acc === 'tipo') {
      st.tipo = st.tipo === b.dataset.id ? null : b.dataset.id;
      dibujar(raiz);
    }
  });
  raiz.addEventListener('input', (ev) => {
    if (ev.target.dataset.acc !== 'buscar') return;
    raiz.__d.st.q = ev.target.value;
    dibujar(raiz, 'filas');
  });
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  if (!data || !data.propuestas) return;
  let raiz = parentElement.querySelector('.nc');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'nc';
    parentElement.appendChild(raiz);
    raiz.__d = { st: { sel: null, q: '', tipo: null } };
    enlazar(raiz);
  }
  raiz.__d.enviar = setTriggerValue;
  raiz.__d.data = data;
  if (!data.propuestas.some((p) => p.id === raiz.__d.st.sel)) raiz.__d.st.sel = data.sel;
  dibujar(raiz);
}
