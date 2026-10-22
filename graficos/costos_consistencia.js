// Costos › «Consistencia de datos» (reglas #686, #689 y #690).
//
// La monta graficos/costos_consistencia.py con st.components.v2 (sin iframe,
// estilos en un shadow root). Es la forma del boceto aprobado
// (https://claude.ai/artifact/JDqYExY3U12yEfTrnewdhJ): indicadores, pestañas
// por grupo, la lista de controles y la ficha del elegido con TODOS sus
// casos. Todo pasa en el navegador: elegir un grupo, abrir un control,
// buscar entre sus casos y bajarlos en Excel. Nada vuelve a Python.
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

// El Excel: `libro`, `bajar` y `archivo` vienen de graficos/_xlsx.js, que
// costos_consistencia.py antepone a este módulo.


// ── Partes de la página ──────────────────────────────────────────────────
// La explicación va en el «?» y no en un párrafo: a 619px de alto, cada
// renglón de arriba es uno menos de la lista (regla #690).
const AYUDA = 'Cada fila es un control: una pregunta que el maestro y los movimientos deberían '
  + 'poder responder sin contradecirse. Rojo pide acción en el POS, ámbar pide mirar, verde '
  + 'está en orden. «Movimientos raros» son señales, no pruebas. Los montos de «S/ en juego» '
  + 'no se suman entre controles: cada uno mide otra cosa (stock, venta, compra). Falta '
  + 'comparar contra el cierre anterior: el maestro de stock es una foto de hoy.';

function cabecera(data) {
  return `<div class="cd-cab">
    <div class="cd-tit">
      <h2>¿Los datos del sistema tienen lógica?</h2>
      <span class="cd-ayuda" tabindex="0" role="note" aria-label="${esc(AYUDA)}" title="${esc(AYUDA)}">?</span>
    </div>
    <div class="cd-der">
      <span class="cd-corte" title="90 días hacia atrás; 180 para «no se usa»; un año para los movimientos raros">Corte ${esc(data.hoy)} · último día del kardex</span>
      <button class="cd-btn" data-acc="xls-todo">Todos los casos (Excel)</button>
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
      <div class="cd-cuenta"><span><b>${c.rojo}</b> <span class="r">revisar ya</span></span>
        <span><b>${c.ambar}</b> <span class="a">mirar</span></span>
        <span><b>${c.verde}</b> <span class="v">en orden</span></span></div>
      <div class="cd-barra"><div class="r" style="flex:${c.rojo}"></div><div class="a" style="flex:${c.ambar}"></div><div class="v" style="flex:${c.verde}"></div></div>
    </div>
    ${top.map((x) => `<button class="cd-kpi" data-acc="abrir" data-id="${x.id}" title="${esc(x.concentra ? 'Se concentra en ' + x.concentra : x.nombre)}">
      <span class="cd-kpi-rot">${esc(x.nombre)}</span>
      <span class="cd-kpi-lin"><span class="cd-kpi-val">${soles(x.soles)}</span>
        <span class="cd-kpi-sub">${num(x.n)} casos</span></span>
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
      <span class="cd-nom"><b>${esc(x.nombre)}</b><span title="${esc(x.mide)}">${esc(x.mide)}</span></span>
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
    ? `Se ven ${num(MAX_FILAS)} de ${num(filas.length)}: el resto, buscando o en el Excel.`
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
        <button class="cd-btn" data-acc="xls">Descargar Excel</button></div>
      <div class="cd-zona" data-zona="tabla">${tablaCasos(x, st.q)}</div>
    </div>`;
  }
  // Compacta (regla #690): las cifras en un renglón, «qué hacer» en una
  // caja baja y la regla plegada, para que los casos tengan alto.
  const cifras = [`<b>${num(x.n)}</b> casos`];
  if (x.soles != null) cifras.push(`<b>${soles(x.soles)}</b> en juego`);
  if (x.concentra) cifras.push(`se concentra en ${esc(x.concentra)}`);
  return `<div class="cd-ficha">
    <div class="cd-fcab">${chip(x.estado)}<h3>${esc(x.nombre)}</h3><span class="cd-fdom">${esc((nombres[x.dom] || '').toUpperCase())}</span></div>
    <p>${esc(x.porque)}</p>
    <div class="cd-cifras">${cifras.join(' · ')}</div>
    <div class="cd-hacer"><b>Qué hacer:</b> ${esc(x.accion)}</div>
    <details class="cd-regla"${st.regla ? ' open' : ''}><summary>La regla${x.ya ? ' y dónde ya se ve' : ''}</summary>
      <div><span>${esc(x.regla)}</span>${x.ya ? `<span class="ya">Ya lo marca: ${esc(x.ya)}</span>` : ''}</div></details>
    ${casos}
  </div>`;
}

function dibujar(raiz) {
  const { data, st } = raiz.__d;
  // Rehacer el HTML devuelve la lista arriba de todo: con scroll propio, un
  // clic en la fila 20 la perdía de vista.
  const previa = raiz.querySelector('.cd-lista');
  const scroll = previa ? previa.scrollTop : 0;
  raiz.innerHTML = `<div class="cd-arriba">${cabecera(data)}${indicadores(data.controles)}${pestanas(data, st)}</div>
    <div class="cd-cuerpo">${lista(data, st)}${ficha(data, st)}</div>`;
  const nueva = raiz.querySelector('.cd-lista');
  if (nueva && st.mismaLista) nueva.scrollTop = scroll;
  st.mismaLista = true;
  medir(raiz);
}

// Lo de arriba (título, indicadores, pestañas) puede ocupar uno o dos
// renglones según el ancho: se mide y la lista y la ficha toman el resto.
function medir(raiz) {
  const arriba = raiz.querySelector('.cd-arriba');
  if (!arriba) return;
  const alto = Math.ceil(arriba.getBoundingClientRect().height) + 10;  // + el gap de .cd
  if (raiz.__d.arriba !== alto) {
    raiz.__d.arriba = alto;
    raiz.style.setProperty('--cd-arriba', `${alto}px`);
  }
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
      st.mismaLista = false;
    } else if (acc === 'abrir') {
      const x = data.controles.find((c) => c.id === b.dataset.id);
      if (!x) return;
      // Un indicador de arriba puede abrir un control de otro grupo.
      if (st.dom !== 'todo' && x.dom !== st.dom) { st.dom = 'todo'; guardar('cd_dom', st.dom); st.mismaLista = false; }
      st.sel = x.id; st.q = ''; guardar('cd_sel', st.sel);
    } else if (acc === 'xls' || acc === 'xls-todo') {
      const grupos = Object.fromEntries(data.dominios);
      if (acc === 'xls') {
        // El control elegido, con lo que se esté buscando.
        const x = data.controles.find((c) => c.id === st.sel);
        if (!x) return;
        // Las mismas columnas que la tabla: sin las que el control no llena.
        const cols = columnas(x);
        bajar(`consistencia_${archivo(x.nombre)}.xlsx`, libro([{
          nombre: x.nombre, cabeza: cols.map(([n]) => n),
          filas: filtrar(x, st.q).map((f) => cols.map(([, i]) => f[i])),
        }]));
      } else {
        // Todo: una hoja con la lista de controles y otra con todos los casos.
        const resumen = data.controles.map((x) => [grupos[x.dom] || x.dom, x.nombre,
          ESTADO[x.estado] || x.estado, x.n, x.soles, x.concentra || '', x.regla]);
        const casos = [];
        data.controles.forEach((x) => x.casos.forEach((f) => casos.push([x.nombre, ...f])));
        bajar('consistencia_de_datos.xlsx', libro([
          { nombre: 'Controles', cabeza: ['Grupo', 'Control', 'Estado', 'Casos', 'S/ en juego', 'Se concentra en', 'La regla'], filas: resumen },
          { nombre: 'Casos', cabeza: ['Control', 'Código', 'Nombre', 'Área', 'Dato', 'S/', 'Fecha', 'Usuario'], filas: casos },
        ]));
      }
      return;
    } else {
      return;
    }
    dibujar(raiz);
  });
  // La regla plegada o abierta se recuerda al cambiar de control.
  raiz.addEventListener('toggle', (ev) => {
    if (ev.target.classList && ev.target.classList.contains('cd-regla')) raiz.__d.st.regla = ev.target.open;
  }, true);
  // Con otro ancho, lo de arriba puede pasar a dos renglones.
  window.addEventListener('resize', () => medir(raiz));
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
