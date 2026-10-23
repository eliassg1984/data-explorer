// Inicio › «Pendientes del período» (regla #711).
//
// La monta graficos/pendientes.py con st.components.v2 (sin iframe, estilos
// en un shadow root). Es la forma del boceto aprobado: título y filtro por
// gravedad, cuatro contadores y las áreas en tres columnas, una fila por
// señal con su punto, lo que dice, de dónde sale y su cifra.
//
// Python manda en `data`: `columnas` ([[{n, i, filas}]]), `cuenta`
// ({rojo, ambar, verde, sin}), `cierre` y `calculable` (si falta algo que
// el botón «Calcular ahora» sabe calcular). Cada fila trae `t`, `estado`,
// `v`, `por`, `ir_rot`, `ayuda` e `ir` ({r, sk, v, abrir} o null). A Python
// vuelven dos triggers: «ir» (la fila elegida) y «calcular» (el botón de lo
// que falta). El filtro se resuelve acá y se recuerda en el navegador.

const ESTADO = { rojo: 'Revisar ya', ambar: 'Para mirar', verde: 'Al día', sin: 'Sin calcular' };
const FILTROS = [['todo', 'Todo'], ['rojo', 'Revisar ya'], ['ambar', 'Para mirar']];
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento */ } }

function cabecera(data, filtro) {
  const botones = FILTROS.map(([k, t]) => `<button type="button" class="pd-filtro${k === filtro ? ' sel' : ''}"
    data-acc="filtro" data-k="${k}" aria-pressed="${k === filtro}">${t}</button>`).join('');
  const calc = data.calculable
    ? `<button type="button" class="pd-calc" data-acc="calcular" title="Lo calculan las mismas funciones que sus vistas, y les queda hecho. La primera vez de los datos de hoy tarda alrededor de un minuto.">Calcular ahora</button>`
    : '';
  return `<div class="pd-cab">
    <div class="pd-tit"><h2>Pendientes del período</h2>
      <p>Lo que conviene mirar antes de cerrar el mes. Cada fila lleva a la vista donde se resuelve.</p></div>
    <div class="pd-der">
      <div class="pd-grupo" role="group" aria-label="Filtrar por gravedad">${botones}</div>
      ${calc}
      ${data.cierre ? `<span class="pd-cierre">Último cierre: ${esc(data.cierre)}</span>` : ''}
    </div>
  </div>`;
}

function contadores(data) {
  return `<div class="pd-kpis">${['rojo', 'ambar', 'verde', 'sin'].map((e) => `
    <div class="pd-kpi"><span class="pd-punto ${e}" aria-hidden="true"></span>
      <span class="pd-kpi-n">${data.cuenta[e] || 0}</span><span class="pd-kpi-t">${ESTADO[e]}</span></div>`).join('')}
  </div>`;
}

function fila(f, i) {
  const ir = f.ir ? `<span class="pd-ir">${esc(f.ir_rot)} →</span>` : '';
  const tag = f.ir ? 'button type="button"' : 'div';
  const cierre = f.ir ? 'button' : 'div';
  return `<${tag} class="pd-fila${f.ir ? '' : ' fija'}" data-acc="ir" data-i="${i}"
      title="${esc(f.ayuda || '')}">
    <span class="pd-punto ${f.estado}" aria-label="${ESTADO[f.estado]}"></span>
    <span class="pd-txt"><span class="pd-t">${esc(f.t)}</span>
      <span class="pd-por">${esc(f.por)}${f.por && ir ? ' · ' : ''}${ir}</span></span>
    <span class="pd-v${f.estado === 'sin' ? ' sin' : ''}">${esc(f.v)}</span>
    ${f.ir ? '<span class="pd-flecha" aria-hidden="true">›</span>' : ''}
  </${cierre}>`;
}

function columnas(data, filtro, todas) {
  return `<div class="pd-cols">${data.columnas.map((col) => `<div class="pd-col">${col.map((a) => {
    const filas = a.filas.filter((f) => filtro === 'todo' || f.estado === filtro);
    const cuerpo = filas.length
      ? filas.map((f) => fila(f, todas.indexOf(f))).join('')
      : '<div class="pd-nada">Nada en este filtro.</div>';
    return `<section class="pd-area" aria-label="${esc(a.n)}">
      <div class="pd-area-cab"><span class="pd-ico" aria-hidden="true">${esc(a.i)}</span>${esc(a.n)}</div>
      ${cuerpo}</section>`;
  }).join('')}</div>`).join('')}</div>`;
}

function dibujar(raiz) {
  const { data, filtro } = raiz.__d;
  const todas = data.columnas.flat().flatMap((a) => a.filas);
  raiz.__d.todas = todas;
  raiz.innerHTML = cabecera(data, filtro) + contadores(data) + columnas(data, filtro, todas)
    + '<p class="pd-pie">Cada señal sale de la vista que la calcula. Si todavía no se calculó con los datos de hoy, dice «sin calcular» y no 0.</p>';
}

function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b)) return;
    const d = raiz.__d;
    if (b.dataset.acc === 'filtro') {
      d.filtro = b.dataset.k;
      guardar('pd_filtro', d.filtro);
      dibujar(raiz);
    } else if (b.dataset.acc === 'calcular') {
      b.disabled = true;
      b.textContent = 'Calculando…';
      d.enviar('calcular', Date.now());
    } else if (b.dataset.acc === 'ir') {
      const f = d.todas[Number(b.dataset.i)];
      if (f && f.ir) d.enviar('ir', { ...f.ir, t: Date.now() });
    }
  });
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  let raiz = parentElement.querySelector('.pd');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'pd';
    parentElement.appendChild(raiz);
    const f = leer('pd_filtro', 'todo');
    raiz.__d = { filtro: FILTROS.some(([k]) => k === f) ? f : 'todo' };
    enlazar(raiz);
  }
  raiz.__d.enviar = setTriggerValue;
  if (!data || !data.columnas) return;
  raiz.__d.data = data;
  dibujar(raiz);
}
