// Costos › «Consistencia de datos» (reglas #686 y #689).
//
// La monta graficos/costos_consistencia.py con st.components.v2 (sin iframe,
// estilos en un shadow root). Es la forma del boceto aprobado
// (https://claude.ai/artifact/JDqYExY3U12yEfTrnewdhJ): indicadores, pestañas
// por grupo, la lista de controles y la ficha del elegido con TODOS sus
// casos. Todo pasa en el navegador: elegir un grupo, abrir un control,
// buscar entre sus casos y bajar el CSV. Nada vuelve a Python.
//
// Python manda en `data`: `hoy` (el corte), `dominios` ([id, rótulo]) y
// `controles`, uno por control de `consistencia_maestro.CONTROLES`, con sus
// textos, su estado y sus casos como filas [código, nombre, área, dato,
// soles, fecha, quién].

const ESTADO = { rojo: 'Revisar ya', ambar: 'Mirar', verde: 'En orden', fallo: 'No se pudo calcular' };
const MAX_FILAS = 300;
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leer(k, def) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardar(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) { /* sin almacenamiento */ } }
function soles(v) {
  if (v == null || !isFinite(v)) return '—';
  return `${v < -0.5 ? '−' : ''}S/ ${Math.abs(Math.round(v)).toLocaleString('en-US')}`;
}
const num = (n) => Number(n || 0).toLocaleString('en-US');
const chip = (e) => `<span class="chip ${e}">${ESTADO[e] || e}</span>`;

// El CSV de unos casos, con los rótulos de su ficha. BOM para que Excel lea
// las tildes.
function csv(cabeza, filas) {
  const celda = (v) => {
    const s = v == null ? '' : String(v);
    return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return '﻿' + [cabeza, ...filas].map((f) => f.map(celda).join(',')).join('\n');
}
function bajar(nombre, texto) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([texto], { type: 'text/csv;charset=utf-8' }));
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
}
const archivo = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9]+/g, '_');

// ── Partes de la página ──────────────────────────────────────────────────
function cabecera(data) {
  return `<div class="cd-cab">
    <div class="cd-tit">
      <h2>¿Los datos del sistema tienen lógica?</h2>
      <p>Cada fila es un control: una pregunta que el maestro y los movimientos deberían poder
      responder sin contradecirse. Rojo pide acción en el POS, ámbar pide mirar, verde está en
      orden. «Movimientos raros» son señales, no pruebas.</p>
    </div>
    <div class="cd-der">
      <span class="cd-corte" title="90 días hacia atrás; 180 para «no se usa»; un año para los movimientos raros">Corte: ${esc(data.hoy)}, el último día del kardex</span>
      <button class="cd-btn prim" data-acc="csv-todo">Todos los casos (CSV)</button>
    </div>
  </div>`;
}

function indicadores(ctrl) {
  const c = { rojo: 0, ambar: 0, verde: 0 };
  ctrl.forEach((x) => { if (c[x.estado] != null) c[x.estado] += 1; });
  // Los tres que más plata ponen en juego entre los que piden algo: es lo
  // primero que hay que mirar, y cambia con el dato.
  const top = ctrl.filter((x) => (x.estado === 'rojo' || x.estado === 'ambar') && x.soles != null)
    .sort((a, b) => Math.abs(b.soles) - Math.abs(a.soles)).slice(0, 3);
  return `<div class="cd-kpis">
    <div class="cd-kpi"><span class="cd-kpi-rot">Controles</span>
      <div class="cd-cuenta"><span><b>${c.rojo}</b> <span class="r">para revisar ya</span></span>
        <span><b>${c.ambar}</b> <span class="a">para mirar</span></span>
        <span><b>${c.verde}</b> <span class="v">en orden</span></span></div>
      <div class="cd-barra"><div class="r" style="flex:${c.rojo}"></div><div class="a" style="flex:${c.ambar}"></div><div class="v" style="flex:${c.verde}"></div></div>
    </div>
    ${top.map((x) => `<button class="cd-kpi" data-acc="abrir" data-id="${x.id}">
      <span class="cd-kpi-rot">${esc(x.nombre)}</span>
      <span class="cd-kpi-val">${soles(x.soles)}</span>
      <span class="cd-kpi-sub">${num(x.n)} casos${x.concentra ? ' · ' + esc(x.concentra) : ''}</span>
    </button>`).join('')}
  </div>`;
}

function pestanas(data, st) {
  const cuenta = (l, e) => l.filter((x) => x.estado === e).length;
  const tabs = [['todo', 'Todo'], ...data.dominios];
  return `<div class="cd-tabs" role="tablist">${tabs.map(([id, rot]) => {
    const l = id === 'todo' ? data.controles : data.controles.filter((x) => x.dom === id);
    return `<button class="cd-tab${st.dom === id ? ' sel' : ''}" role="tab" aria-selected="${st.dom === id}"
      data-acc="dom" data-id="${id}">${esc(rot)}<span class="cd-pts"><span class="pt r"></span>${cuenta(l, 'rojo')}<span class="pt a"></span>${cuenta(l, 'ambar')}</span></button>`;
  }).join('')}</div>`;
}

function lista(data, st) {
  const nombres = Object.fromEntries(data.dominios);
  const vis = st.dom === 'todo' ? data.controles : data.controles.filter((x) => x.dom === st.dom);
  let previo = null;
  const filas = vis.map((x) => {
    const grupo = st.dom === 'todo' && x.dom !== previo
      ? `<div class="cd-grupo">${esc(nombres[x.dom] || x.dom).toUpperCase()}</div>` : '';
    previo = x.dom;
    return `${grupo}<button class="cd-fila${x.id === st.sel ? ' sel' : ''}" data-acc="abrir" data-id="${x.id}" aria-pressed="${x.id === st.sel}">
      ${chip(x.estado)}
      <span class="cd-nom"><b>${esc(x.nombre)}</b><span>${esc(x.mide)}</span></span>
      <span class="cd-n">${num(x.n)}</span>
      <span class="cd-s">${soles(x.soles)}</span>
      <span class="cd-donde">${esc(x.concentra || '—')}</span>
    </button>`;
  }).join('');
  return `<div class="cd-lista">
    <div class="cd-lcab"><span>Estado</span><span>Control</span><span style="text-align:right">Casos</span><span style="text-align:right">S/ en juego</span><span>Se concentra en</span></div>
    ${filas}
  </div>`;
}

// Las columnas de los casos de un control: las que el control llena.
function columnas(x) {
  const [ca, cb, cd] = x.cols;
  const todas = [
    ['Código', 0, 'cod'], [ca, 1, ''], [cb || 'Área', 2, ''], [cd, 3, ''],
    ['S/', 4, 'num'], ['Fecha', 5, 'num'], ['Usuario', 6, ''],
  ];
  return todas.filter(([, i]) => i === 1 || x.casos.some((f) => f[i] != null && f[i] !== '' && f[i] !== '—'));
}

function filtrar(x, q) {
  if (!q) return x.casos;
  const t = q.toLowerCase();
  return x.casos.filter((f) => f.some((v) => v != null && String(v).toLowerCase().includes(t)));
}

function tablaCasos(x, q) {
  const cols = columnas(x);
  const filas = filtrar(x, q);
  const celda = (f, [, i, cls]) => `<td class="${cls}">${i === 4 ? soles(f[i]) : esc(f[i] ?? '')}</td>`;
  const pie = filas.length > MAX_FILAS
    ? `Se ven ${num(MAX_FILAS)} de ${num(filas.length)}: el resto, buscando o en el CSV.`
    : `${num(filas.length)} ${filas.length === 1 ? 'caso' : 'casos'}${q ? ' con «' + esc(q) + '»' : ''}, de mayor a menor monto.`;
  return `<div class="cd-tabla"><table>
      <thead><tr>${cols.map(([n, , cls]) => `<th class="${cls}">${esc(n)}</th>`).join('')}</tr></thead>
      <tbody>${filas.slice(0, MAX_FILAS).map((f) => `<tr>${cols.map((c) => celda(f, c)).join('')}</tr>`).join('')}</tbody>
    </table></div><span class="cd-pie">${pie}</span>`;
}

function ficha(data, st) {
  const x = data.controles.find((c) => c.id === st.sel) || data.controles[0];
  if (!x) return '';
  const nombres = Object.fromEntries(data.dominios);
  let casos;
  if (x.estado === 'fallo') {
    casos = `<div class="cd-pie">Este control no se pudo calcular: ${esc(x.error)}</div>`;
  } else if (!x.n) {
    casos = '<div class="cd-vacio">Sin casos: el maestro contesta bien esta pregunta.</div>';
  } else {
    casos = `<div class="cd-casos">
      <div class="cd-buscar"><input type="search" placeholder="Buscar entre los ${num(x.n)} casos…" value="${esc(st.q)}" data-acc="buscar" aria-label="Buscar entre los casos">
        <button class="cd-btn" data-acc="csv">Descargar CSV</button></div>
      <div data-zona="tabla">${tablaCasos(x, st.q)}</div>
    </div>`;
  }
  return `<div class="cd-ficha">
    <div class="cd-fcab">${chip(x.estado)}<span class="cd-fdom">${esc((nombres[x.dom] || '').toUpperCase())}</span></div>
    <h3>${esc(x.nombre)}</h3>
    <p>${esc(x.porque)}</p>
    <div class="cd-mini">
      <div><small>Casos</small><b>${num(x.n)}</b></div>
      <div><small>S/ en juego</small><b>${soles(x.soles)}</b></div>
      <div><small>Se concentra en</small><span class="txt">${esc(x.concentra || '—')}</span></div>
    </div>
    <div class="cd-regla"><span class="rot">La regla</span><span>${esc(x.regla)}</span>
      ${x.ya ? `<span class="ya">Ya lo marca: ${esc(x.ya)}</span>` : ''}</div>
    ${casos}
    <div class="cd-hacer"><span class="rot">Qué hacer</span><span>${esc(x.accion)}</span></div>
  </div>`;
}

function dibujar(raiz) {
  const { data, st } = raiz.__d;
  raiz.innerHTML = `${cabecera(data)}${indicadores(data.controles)}${pestanas(data, st)}
    <div class="cd-cuerpo">${lista(data, st)}${ficha(data, st)}</div>
    <p class="cd-nota">Falta comparar contra el cierre anterior: el maestro de stock es una foto de hoy.
    Los montos de «S/ en juego» no se suman entre controles: cada uno mide otra cosa (stock, venta, compra).</p>`;
}

// El control que abre: el primero que pide acción del grupo, si el guardado
// no está en él.
function elegirEn(data, st) {
  const vis = st.dom === 'todo' ? data.controles : data.controles.filter((x) => x.dom === st.dom);
  if (vis.some((x) => x.id === st.sel)) return;
  const primero = vis.find((x) => x.estado === 'rojo') || vis.find((x) => x.estado === 'ambar') || vis[0];
  st.sel = primero ? primero.id : null;
}

function enlazar(raiz) {
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    if (!b || !raiz.contains(b)) return;
    const { data, st } = raiz.__d;
    const acc = b.dataset.acc;
    if (acc === 'dom') {
      st.dom = b.dataset.id; guardar('cd_dom', st.dom); elegirEn(data, st); st.q = '';
    } else if (acc === 'abrir') {
      const x = data.controles.find((c) => c.id === b.dataset.id);
      if (!x) return;
      // Un indicador de arriba puede abrir un control de otro grupo.
      if (st.dom !== 'todo' && x.dom !== st.dom) { st.dom = 'todo'; guardar('cd_dom', st.dom); }
      st.sel = x.id; st.q = ''; guardar('cd_sel', st.sel);
    } else if (acc === 'csv' || acc === 'csv-todo') {
      const elegidos = acc === 'csv' ? data.controles.filter((c) => c.id === st.sel) : data.controles;
      const filas = [];
      elegidos.forEach((x) => filtrar(x, acc === 'csv' ? st.q : '').forEach((f) => filas.push([x.nombre, ...f])));
      const x = elegidos[0];
      const cabeza = acc === 'csv'
        ? ['Control', 'Código', x.cols[0], x.cols[1] || 'Área', x.cols[2], 'S/', 'Fecha', 'Usuario']
        : ['Control', 'Código', 'Nombre', 'Área', 'Dato', 'S/', 'Fecha', 'Usuario'];
      bajar(acc === 'csv' ? `consistencia_${archivo(x.nombre)}.csv` : 'consistencia_de_datos.csv', csv(cabeza, filas));
      return;
    } else {
      return;
    }
    dibujar(raiz);
  });
  // Buscar sólo redibuja la tabla: el campo no pierde el foco.
  raiz.addEventListener('input', (ev) => {
    if (ev.target.dataset.acc !== 'buscar') return;
    const { data, st } = raiz.__d;
    st.q = ev.target.value;
    const x = data.controles.find((c) => c.id === st.sel);
    const zona = raiz.querySelector('[data-zona="tabla"]');
    if (x && zona) zona.innerHTML = tablaCasos(x, st.q);
  });
}

export default function (component) {
  const { data, parentElement } = component;
  let raiz = parentElement.querySelector('.cd');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'cd';
    parentElement.appendChild(raiz);
    raiz.__d = { st: { dom: leer('cd_dom', 'todo'), sel: leer('cd_sel', null), q: '' } };
    enlazar(raiz);
  }
  if (!data || !data.controles) return;
  const st = raiz.__d.st;
  if (st.dom !== 'todo' && !data.dominios.some(([id]) => id === st.dom)) st.dom = 'todo';
  raiz.__d.data = data;
  elegirEn(data, st);
  dibujar(raiz);
}
