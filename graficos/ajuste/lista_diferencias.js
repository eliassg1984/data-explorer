// La lista de «Análisis de diferencias» de Ajuste (regla #680).
//
// La monta graficos/ajuste/_diferencias.py::_lista con st.components.v2 (sin
// iframe, estilos en un shadow root). Reemplazó al st.dataframe de la
// regla #650 porque una celda de st.dataframe no puede tener una ficha que
// se clickee: «Posible origen» son fichas cortas con el nombre de la pista, y
// un clic en una abre un pop con su número (`dato`) y lo que la origina, el
// texto de la pista partido en pasos. El número no va en la ficha: se quitó
// a pedido el mismo día («quitemos el dato en la celda»).
//
// Python manda en `data`: las filas (ya ordenadas y con sus textos
// escritos), la elegida, el alto y los dos colores de Ajuste. A Python le
// llega una sola cosa, el trigger «fila»: {k, t} al elegir una línea —con un
// clic en la fila o con «Abrir la ficha» del pop—. Abrir y cerrar un pop es
// del navegador: no cuesta una corrida.

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// Una frase por paso de la traza. Corta en el punto seguido de mayúscula,
// no en «N° 12.» ni en los decimales.
function pasos(tx) {
  const t = String(tx || '').trim();
  if (!t) return [];
  return t.split(/(?<=[.:;])\s+(?=[A-ZÁÉÍÓÚÑ¿«(])/).map((s) => s.trim()).filter(Boolean);
}

function chips(fila) {
  if (!fila.pistas.length) return '<span class="nada">—</span>';
  return '<div class="chips">' + fila.pistas.map((p, j) =>
    `<button type="button" class="chip${p.f ? ' f' : ''}" data-k="${esc(fila.k)}" data-j="${j}"` +
    ` title="${esc(p.ti)}"><span class="t">${esc(p.ti)}</span></button>`).join('') + '</div>';
}

function dibujar(raiz) {
  const st = raiz.__st;
  const d = st.data;
  raiz.style.setProperty('--ld-neg', d.neg || 'currentColor');
  raiz.style.setProperty('--ld-pos', d.pos || 'currentColor');
  if (!d.filas.length) {
    raiz.innerHTML = `<div class="marco"><div class="vacio">${esc(d.vacio || 'Ninguna línea.')}</div></div>`;
    return;
  }
  // Anchos FIJOS por columna (`table-layout: fixed`): con el reparto
  // automático, las fichas —que no se parten— pedían su ancho entero y, con
  // la ficha de la línea abierta al costado, «S/» y «Posible origen» se salían
  // por la derecha (medido a 1323). Así la ficha corta se achica con «…».
  let h = `<div class="marco" style="max-height:${Number(d.alto) || 470}px"><table>` +
    '<colgroup><col style="width:12px"><col style="width:29%"><col style="width:13%">' +
    '<col style="width:10%"><col style="width:10%"><col></colgroup><thead><tr>' +
    '<th></th><th>Producto</th><th>Área</th><th class="n">Dif.</th><th class="n">S/</th>' +
    '<th>Posible origen</th></tr></thead><tbody>';
  for (const f of d.filas) {
    h += `<tr tabindex="0" data-k="${esc(f.k)}" class="${f.k === d.sel ? 'sel' : ''}">` +
      `<td class="sev"><i class="${f.lado}" style="opacity:${(0.25 + 0.7 * (f.peso || 0)).toFixed(2)}"></i></td>` +
      `<td class="prod">${esc(f.p)}<small>${esc(f.sub)}</small></td>` +
      `<td class="area">${esc(f.a)}</td>` +
      `<td class="n ${f.lado}">${esc(f.q)}</td><td class="n ${f.lado}">${esc(f.v)}</td>` +
      `<td>${chips(f)}</td></tr>`;
  }
  h += '</tbody></table></div>';
  const scroll = raiz.querySelector('.marco')?.scrollTop || 0;
  raiz.innerHTML = h;
  const marco = raiz.querySelector('.marco');
  marco.scrollTop = scroll;
  // Después de un cuadro: devolver el scroll de antes dispara un «scroll»
  // que si no cerraría el pop que `reabrir` acaba de poner.
  requestAnimationFrame(() => marco.addEventListener('scroll', () => cerrarPop(raiz), { passive: true }));
}

// `olvidar` = el usuario lo cerró. Una corrida que redibuja la lista lo
// cierra sin olvidarlo, y `reabrir` lo vuelve a poner si su ficha sigue ahí:
// la precarga de las secciones vecinas re-llama al componente sin que nadie
// haya tocado nada, y el pop se iba solo.
function cerrarPop(raiz, olvidar = true) {
  const p = raiz.__pop;
  if (p) { p.remove(); raiz.__pop = null; }
  if (olvidar) raiz.__abierto = null;
}

function reabrir(raiz) {
  const a = raiz.__abierto;
  if (!a) return;
  const chip = [...raiz.querySelectorAll('.chip')].find((c) => c.dataset.k === a.k && c.dataset.j === a.j);
  if (chip) abrirPop(raiz, chip); else raiz.__abierto = null;
}

function abrirPop(raiz, boton) {
  cerrarPop(raiz);
  const st = raiz.__st;
  const fila = st.data.filas.find((f) => f.k === boton.dataset.k);
  const p = fila && fila.pistas[Number(boton.dataset.j)];
  if (!p) return;
  const pop = document.createElement('div');
  pop.className = 'pop';
  pop.setAttribute('role', 'dialog');
  pop.innerHTML = '<button class="x" type="button" aria-label="Cerrar">✕</button>' +
    `<h4>${esc(p.ti)} <span class="fz${p.f ? ' f' : ''}">${p.f ? 'Fuerte' : 'Posible'}</span></h4>` +
    (p.dato ? `<div class="dato">${esc(p.dato)}</div>` : '') +
    `<div class="linea">${esc(fila.p)} · ${esc(fila.a)}</div>` +
    '<div class="traza">' + pasos(p.tx).map((s) => `<div>${esc(s)}</div>`).join('') + '</div>' +
    (fila.k === st.data.sel ? '' : '<button class="ir" type="button">Abrir la ficha de la línea →</button>');
  raiz.appendChild(pop);
  raiz.__pop = pop;
  raiz.__abierto = { k: boton.dataset.k, j: boton.dataset.j };
  // Debajo de la ficha que lo abrió; arriba si no entra; nunca fuera de la
  // pantalla por los costados.
  const b = boton.getBoundingClientRect();
  const w = pop.offsetWidth, hh = pop.offsetHeight;
  let left = Math.min(Math.max(8, b.left), window.innerWidth - w - 8);
  let top = b.bottom + 6;
  if (top + hh > window.innerHeight - 8) top = Math.max(8, b.top - hh - 6);
  pop.style.left = `${left}px`;
  pop.style.top = `${top}px`;
  pop.querySelector('.x').addEventListener('click', () => cerrarPop(raiz));
  const ir = pop.querySelector('.ir');
  if (ir) ir.addEventListener('click', () => { cerrarPop(raiz); st.enviar(fila.k); });
}

function enlazar(raiz) {
  raiz.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (chip) { e.stopPropagation(); abrirPop(raiz, chip); return; }
    if (e.target.closest('.pop')) return;
    const tr = e.target.closest('tbody tr[data-k]');
    if (tr) { cerrarPop(raiz); raiz.__st.enviar(tr.dataset.k); }
  });
  raiz.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { cerrarPop(raiz); return; }
    const tr = e.target.closest && e.target.closest('tbody tr[data-k]');
    if (tr && e.key === 'Enter') raiz.__st.enviar(tr.dataset.k);
  });
  // Un clic afuera cierra el pop. El listener vive en el documento, así que
  // se registra una sola vez por raíz.
  document.addEventListener('click', (e) => {
    if (!raiz.__pop) return;
    const camino = e.composedPath ? e.composedPath() : [];
    if (camino.includes(raiz.__pop) || camino.some((n) => n.classList && n.classList.contains('chip'))) return;
    cerrarPop(raiz);
  });
  window.addEventListener('resize', () => cerrarPop(raiz));
}

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  let raiz = parentElement.querySelector('.ld');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'ld';
    parentElement.appendChild(raiz);
    raiz.__st = {};
    enlazar(raiz);
  }
  raiz.__st.data = { filas: [], ...(data || {}) };
  // Un sello por aviso: dos clics en la misma fila son dos avisos.
  raiz.__st.enviar = (k) => setTriggerValue('fila', { k, t: Date.now() });
  cerrarPop(raiz, false);
  dibujar(raiz);
  reabrir(raiz);
}
