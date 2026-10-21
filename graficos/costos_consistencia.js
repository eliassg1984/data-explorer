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

// ── El Excel (.xlsx), armado acá sin librerías (regla #691) ──────────────
// Un .xlsx es un ZIP de XML. Se guarda SIN comprimir (método 0), que Excel
// lee igual: sólo hace falta el CRC32 de cada archivo. Los montos van como
// número (se pueden sumar); el resto, como texto en la celda.
const CRC = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(b) {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}
const u16 = (v) => [v & 255, (v >>> 8) & 255];
const u32 = (v) => [v & 255, (v >>> 8) & 255, (v >>> 16) & 255, (v >>> 24) & 255];
function zip(archivos) {
  const enc = new TextEncoder();
  const partes = [], central = [];
  let off = 0;
  archivos.forEach(([nombre, texto]) => {
    const n = enc.encode(nombre), d = enc.encode(texto), c = crc32(d);
    // Fecha 1-ene-1980 (0x21), nombres en UTF-8 (bit 11).
    const comun = [...u16(20), ...u16(0x0800), ...u16(0), ...u16(0), ...u16(0x21),
      ...u32(c), ...u32(d.length), ...u32(d.length), ...u16(n.length), ...u16(0)];
    const loc = new Uint8Array([...u32(0x04034b50), ...comun]);
    partes.push(loc, n, d);
    central.push(new Uint8Array([...u32(0x02014b50), ...u16(20), ...comun,
      ...u16(0), ...u16(0), ...u16(0), ...u32(0), ...u32(off)]), n);
    off += loc.length + n.length + d.length;
  });
  const tam = central.reduce((s, x) => s + x.length, 0);
  const fin = new Uint8Array([...u32(0x06054b50), ...u16(0), ...u16(0), ...u16(archivos.length),
    ...u16(archivos.length), ...u32(tam), ...u32(off), ...u16(0)]);
  return new Blob([...partes, ...central, fin],
    { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}
const xml = (s) => String(s).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '')
  .replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function letra(i) {
  let s = '';
  for (i += 1; i > 0; i = Math.floor((i - 1) / 26)) s = String.fromCharCode(65 + ((i - 1) % 26)) + s;
  return s;
}
const NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main';
const NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
// Una hoja: la cabecera congelada y el ancho de cada columna según su texto.
function hoja(cabeza, filas) {
  const ancho = cabeza.map((h, i) => Math.min(60, Math.max(8, String(h).length + 2,
    ...filas.slice(0, 400).map((f) => (f[i] == null ? 0 : String(f[i]).length + 2)))));
  const celda = (v, ref) => {
    if (typeof v === 'number' && isFinite(v)) return `<c r="${ref}"><v>${Math.round(v * 100) / 100}</v></c>`;
    if (v == null || v === '') return '';
    return `<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${xml(v)}</t></is></c>`;
  };
  const fila = (r, vals) => `<row r="${r}">${vals.map((v, i) => celda(v, letra(i) + r)).join('')}</row>`;
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    + `<worksheet xmlns="${NS}"><sheetViews><sheetView workbookViewId="0">`
    + '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
    + `<cols>${ancho.map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`).join('')}</cols>`
    + `<sheetData>${[fila(1, cabeza), ...filas.map((f, i) => fila(i + 2, f))].join('')}</sheetData></worksheet>`;
}
// `hojas`: [{nombre, cabeza, filas}]. El nombre de una hoja: hasta 31
// caracteres y sin []:*?/\ (si no, Excel no abre el archivo).
function libro(hojas) {
  const nom = (s) => String(s).replace(/[[\]:*?/\\]/g, ' ').slice(0, 31);
  const archivos = [
    ['[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      + '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      + '<Default Extension="xml" ContentType="application/xml"/>'
      + '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
      + hojas.map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('')
      + '</Types>'],
    ['_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
      + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
      + '</Relationships>'],
    ['xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + `<workbook xmlns="${NS}" xmlns:r="${NS_R}"><sheets>`
      + hojas.map((h, i) => `<sheet name="${xml(nom(h.nombre))}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join('')
      + '</sheets></workbook>'],
    ['xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
      + hojas.map((_, i) => `<Relationship Id="rId${i + 1}" Type="${NS_R}/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join('')
      + '</Relationships>'],
    ...hojas.map((h, i) => [`xl/worksheets/sheet${i + 1}.xml`, hoja(h.cabeza, h.filas)]),
  ];
  return zip(archivos);
}
function bajar(nombre, blob) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
}
const archivo = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^A-Za-z0-9]+/g, '_');

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
