// Simulador de un plato de Recetas › Costo Carta (regla #656).
//
// Lo monta graficos/simulador_plato.py con st.components.v2 (sin iframe,
// estilos en un shadow root). Las cuentas corren ACÁ, en vivo, mientras se
// escribe: es la razón de ser un componente y no un st.data_editor, que no
// recalcula una columna bloqueada hasta la corrida siguiente (regla #656).
// A Python le llega sólo «guardar», con el borrador entero, y Python vuelve
// a hacer la cuenta con simulador_receta.costo_arbol antes de guardar.
//
// Python manda en `data`: el plato ({cod, nombre, precio}), el árbol de su
// receta (`nodos`, de simulador_receta.arbol_plato), el divisor del neto, el
// % objetivo de arranque, quién está mirando y, después de guardar, el aviso.
//
// LA CUENTA ES LA DE simulador_receta.costo_nodo, línea por línea. Si se
// toca una, se toca la otra (lo vigila test_graficos.py).

const DIV_DEF = 1.235;
const UCOMPRA = { g: 'kg', ml: 'l', oz: 'l', kg: 'kg', l: 'l', und: 'und', porc: 'porc' };
const f2 = (v) => 'S/ ' + (+v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const pc1 = (v) => (isFinite(v) ? v.toFixed(1).replace('.', ',') : '—') + ' %';
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const semaf = (v) => (v > 35 ? 'roj' : v > 30 ? 'amb' : 'ok');
const fecha = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(2, 4)}` : '');

// ── La cuenta (gemela de simulador_receta.py) ────────────────────────────
const precioHoy = (n) => (n.cant ? n.costo / n.cant * n.factor : 0);
function origenHoy(n) {
  const p = n.porc, corte = n.costo / (n.cant || 1);
  return p.peso ? corte * (1 - p.merma / 100) / p.peso : 0;
}
function precioModo(hoy, compra, modo) {
  if (modo === 'hoy' || !compra) return hoy;
  const v = modo === 'ult' ? compra.ult : compra.p90;
  return v && hoy && v / hoy > 1 / 3 && v / hoy < 3 ? v : hoy;
}
const esPorcionado = (n) => !(n.hijos && n.hijos.length) && n.porc && n.porc.peso > 0 && n.porc.merma >= 0 && n.porc.merma < 100;
function costo(n, ruta, k, estado, modo) {
  const s = estado[ruta] || {};
  const cant = (s.cant ?? n.cant) * k;
  if (n.hijos && n.hijos.length) {
    const k2 = n.cant ? cant / n.cant : 0;
    return n.hijos.reduce((a, h, i) => a + costo(h, `${ruta}.${i}`, k2, estado, modo), 0);
  }
  if (esPorcionado(n)) {
    const p = n.porc;
    const P = s.P ?? precioModo(origenHoy(n), p.compra_origen, modo);
    const m = s.merma ?? p.merma, peso = s.peso ?? p.peso;
    return cant * P / (1 - m / 100) * peso;
  }
  const P = s.P ?? precioModo(precioHoy(n), n.compra, modo);
  return n.factor ? cant * P / n.factor : 0;
}
const total = (st, estado, modo) => st.nodos.reduce((a, n, i) => a + costo(n, String(i), 1, estado, modo), 0);
function nodo(st, ruta) {
  const ps = ruta.split('.').map(Number);
  let n = st.nodos[ps[0]];
  for (const i of ps.slice(1)) n = n.hijos[i];
  return n;
}
const precioMostrado = (st, n, s) => s.P ?? (esPorcionado(n)
  ? precioModo(origenHoy(n), n.porc.compra_origen, st.modo)
  : precioModo(precioHoy(n), n.compra, st.modo));

// ── El dibujo ────────────────────────────────────────────────────────────
function filas(st, ls, pre, nivel) {
  let h = '';
  ls.forEach((n, i) => {
    const ruta = pre === '' ? String(i) : `${pre}.${i}`;
    const tieneH = !!(n.hijos && n.hijos.length), abierta = st.abiertos.has(ruta);
    const porc = esPorcionado(n), s = st.estado[ruta] || {};
    let tag = '';
    if (tieneH) tag = `<span class="tag">receta base${n.base && n.base.fecha ? ' · ' + fecha(n.base.fecha) : ''}</span>`;
    else if (porc) tag = `<span class="tag">porcionado de ${esc(n.porc.origen)}</span>`;
    const uc = porc ? (UCOMPRA[n.porc.unid_origen] || n.porc.unid_origen || 'kg') : (UCOMPRA[n.unid] || n.unid);
    const precio = tieneH
      ? '<span class="gris">sale de su receta</span>'
      : `S/ <input class="ni" type="number" step="any" min="0" data-r="${ruta}" data-f="P" value="${(+precioMostrado(st, n, s)).toFixed(2)}"> <span class="u">/ ${esc(uc)}</span>`;
    h += `<tr class="n${Math.min(nivel, 3)}"><td class="nom" style="padding-left:${8 + nivel * 18}px">`
      + `<button type="button" class="tog${tieneH ? '' : ' no'}" data-tog="${ruta}" ${tieneH ? '' : 'tabindex="-1"'} aria-label="${tieneH ? (abierta ? 'Cerrar' : 'Abrir') + ' la receta base' : ''}">${tieneH ? (abierta ? '▾' : '▸') : '·'}</button>`
      + `${esc(n.ins)}${tag}</td>`
      + `<td class="r"><input class="ni" type="number" step="any" min="0" data-r="${ruta}" data-f="cant" value="${+(s.cant ?? n.cant).toFixed(3)}"> <span class="u">${esc(n.unid)}</span></td>`
      + `<td class="r">${precio}</td><td class="r" data-c="${ruta}"></td><td class="r" data-d="${ruta}"></td></tr>`;
    if (porc) {
      h += `<tr class="n${Math.min(nivel + 1, 3)} porc"><td colspan="5" style="padding-left:${30 + nivel * 18}px">`
        + `Merma <input class="ni c" type="number" step="0.5" min="0" max="95" data-r="${ruta}" data-f="merma" value="${(+(s.merma ?? n.porc.merma)).toFixed(1)}"> %`
        + ` · peso por corte <input class="ni c" type="number" step="5" min="1" data-r="${ruta}" data-f="pesog" value="${Math.round((s.peso ?? n.porc.peso) * 1000)}"> g`
        + ` <span class="gris">· porcionamiento ${esc(n.porc.po)} del ${fecha(n.porc.fecha)}: precio ÷ (1 − merma) × peso</span></td></tr>`;
    }
    if (tieneH && abierta) h += filas(st, n.hijos, ruta, nivel + 1);
  });
  return h;
}

function dibujar(raiz) {
  const st = raiz.__st;
  if (!st.nodos.length) {
    raiz.innerHTML = '<p class="vacio">Este plato no tiene receta que simular.</p>';
    return;
  }
  raiz.innerHTML = `
    <div class="cab">
      <span class="pestanas" role="group" aria-label="Precios">${[['hoy', 'Precio de hoy'], ['ult', 'Última compra'], ['p90', 'Promedio 90 días']]
        .map(([k, t]) => `<button type="button" data-modo="${k}" aria-pressed="${st.modo === k}">${t}</button>`).join('')}</span>
      <span class="borr">Borrador: no toca el POS</span>
    </div>
    <div class="kpis">
      <div><small>Costo</small><b data-k="costo"></b><span data-k="costo-d"></span></div>
      <div><small>Precio de venta</small><span class="pv">S/ <input class="ni pv-in" type="number" step="0.5" min="0" data-g="precio" value="${st.precio}"></span><span class="gris">neto <span data-k="neto"></span></span></div>
      <div><small>% de costo</small><b data-k="pct"></b><span data-k="pct-d"></span></div>
      <div><small>Margen por plato</small><b data-k="mg"></b><span data-k="mg-d"></span></div>
      <div class="obj"><small>Para quedar en <input class="ni c" type="number" step="1" min="5" max="90" data-g="obj" value="${st.obj}"> %</small><b data-k="sug"></b><span class="gris">precio de venta, con IGV y recargo</span></div>
    </div>
    <div class="tabla"><table><thead><tr><th>Insumo · ▸ abre la receta base, que también se edita</th><th class="r">Cantidad</th><th class="r">Precio de compra</th><th class="r">Costo</th><th class="r">Δ</th></tr></thead>
      <tbody>${filas(st, st.nodos, '', 0)}</tbody></table></div>
    <div class="pie">
      <div data-k="cambios"></div>
      <div class="acciones">
        <button type="button" class="sec" data-a="reset">↺ Volver al original</button>
        <input class="por" type="text" data-g="por" placeholder="Tu nombre" value="${esc(st.por)}" aria-label="Guardado por">
        <button type="button" class="prim" data-a="guardar">Guardar como propuesta</button>
      </div>
    </div>
    <p class="aviso" data-k="aviso">${esc(st.aviso)}</p>`;
  actualizar(raiz);
}

function actualizar(raiz) {
  const st = raiz.__st, q = (k) => raiz.querySelector(`[data-k="${k}"]`);
  const hoy = total(st, {}, 'hoy'), sim = total(st, st.estado, st.modo);
  const neto = st.precio / st.div, neto0 = st.precio0 / st.div;
  const pct = neto ? sim / neto * 100 : NaN, pct0 = neto0 ? hoy / neto0 * 100 : NaN;
  const d = (v, alReves) => {
    if (Math.abs(v) < 0.005) return '<span class="gris">sin cambio</span>';
    const malo = alReves ? v < 0 : v > 0;
    return `<span class="${malo ? 'roj' : 'ok'}">${v > 0 ? '+' : '−'}${f2(Math.abs(v))}</span>`;
  };
  q('costo').textContent = f2(sim);
  q('costo-d').innerHTML = `hoy ${f2(hoy)} · ${d(sim - hoy)}`;
  q('neto').textContent = f2(neto);
  q('pct').textContent = pc1(pct);
  q('pct').className = semaf(pct);
  q('pct-d').textContent = `hoy ${pc1(pct0)}`;
  q('mg').textContent = f2(neto - sim);
  q('mg-d').innerHTML = `hoy ${f2(neto0 - hoy)} · ${d((neto - sim) - (neto0 - hoy), true)}`;
  q('sug').textContent = st.obj > 0 ? f2(sim / (st.obj / 100) * st.div) : '—';
  const recorrer = (ls, pre, k) => ls.forEach((n, i) => {
    const ruta = pre === '' ? String(i) : `${pre}.${i}`;
    const c0 = costo(n, ruta, 1, {}, 'hoy') * (k.orig ?? 1);
    const c1 = costo(n, ruta, k.sim, st.estado, st.modo);
    const ec = raiz.querySelector(`[data-c="${ruta}"]`), ed = raiz.querySelector(`[data-d="${ruta}"]`);
    if (ec) ec.textContent = f2(c1);
    if (ed) {
      ed.innerHTML = Math.abs(c1 - c0) < 0.005 ? '<span class="gris">—</span>'
        : `<span class="${c1 > c0 ? 'roj' : 'ok'}">${c1 > c0 ? '+' : '−'}${Math.abs(c1 - c0).toFixed(2)}</span>`;
    }
    if (n.hijos && n.hijos.length && st.abiertos.has(ruta)) {
      const s = st.estado[ruta] || {};
      const cant1 = (s.cant ?? n.cant) * k.sim;
      recorrer(n.hijos, ruta, { orig: 1, sim: n.cant ? cant1 / n.cant : 0 });
    }
  });
  recorrer(st.nodos, '', { orig: 1, sim: 1 });
  // Lo que cambió, cada cosa con lo que mueve ella sola.
  const items = Object.entries(st.estado).map(([ruta, s]) => {
    const n = nodo(st, ruta);
    const solo = total(st, { [ruta]: s }, st.modo) - total(st, {}, st.modo);
    const partes = [];
    if (s.cant != null) partes.push(`cantidad ${+n.cant.toFixed(3)} → ${+s.cant.toFixed(3)} ${esc(n.unid)}`);
    if (s.P != null) partes.push(`precio → ${f2(s.P)}`);
    if (s.merma != null) partes.push(`merma ${n.porc.merma} → ${s.merma} %`);
    if (s.peso != null) partes.push(`peso ${Math.round(n.porc.peso * 1000)} → ${Math.round(s.peso * 1000)} g`);
    return `<li><b>${esc(n.ins)}</b>: ${partes.join(', ')} <span class="${solo > 0 ? 'roj' : 'ok'}">${solo >= 0 ? '+' : '−'}${f2(Math.abs(solo))} por plato</span></li>`;
  });
  const modo = st.modo === 'hoy' ? '' : `<li>Precios de <b>${st.modo === 'ult' ? 'la última compra' : 'compra de los últimos 90 días'}</b> donde los hay; el resto, los de hoy.</li>`;
  q('cambios').innerHTML = items.length || modo
    ? `<b>Cambios</b><ul>${modo}${items.join('')}</ul>`
    : '<span class="gris">Sin cambios: cambiá una cantidad, un precio o la merma.</span>';
}

function enlazar(raiz) {
  raiz.addEventListener('input', (e) => {
    const t = e.target, st = raiz.__st;
    if (t.dataset.r) {
      const ruta = t.dataset.r, f = t.dataset.f, n = nodo(st, ruta);
      const v = t.value === '' ? null : +t.value;
      const s = (st.estado[ruta] = st.estado[ruta] || {});
      if (f === 'cant') { if (v == null || Math.abs(v - n.cant) < 1e-9) delete s.cant; else s.cant = Math.max(v, 0); }
      else if (f === 'merma') { if (v == null || Math.abs(v - n.porc.merma) < 1e-9) delete s.merma; else s.merma = Math.min(Math.max(v, 0), 95); }
      else if (f === 'pesog') { if (v == null || Math.abs(v / 1000 - n.porc.peso) < 1e-6) delete s.peso; else s.peso = Math.max(v, 1) / 1000; }
      else if (f === 'P') {
        const base = esPorcionado(n) ? precioModo(origenHoy(n), n.porc.compra_origen, st.modo) : precioModo(precioHoy(n), n.compra, st.modo);
        if (v == null || Math.abs(v - base) < 0.005) delete s.P; else s.P = Math.max(v, 0);
      }
      if (!Object.keys(s).length) delete st.estado[ruta];
      actualizar(raiz);
    } else if (t.dataset.g === 'precio') { st.precio = +t.value || 0; actualizar(raiz); }
    else if (t.dataset.g === 'obj') { st.obj = +t.value || 0; actualizar(raiz); }
    else if (t.dataset.g === 'por') { st.por = t.value; }
  });
  raiz.addEventListener('click', (e) => {
    const st = raiz.__st, t = e.target;
    const tog = t.closest('[data-tog]');
    if (tog && !tog.classList.contains('no')) {
      const r = tog.dataset.tog;
      if (st.abiertos.has(r)) st.abiertos.delete(r); else st.abiertos.add(r);
      dibujar(raiz);
      return;
    }
    const m = t.closest('[data-modo]');
    if (m) { st.modo = m.dataset.modo; dibujar(raiz); return; }
    const a = t.closest('[data-a]');
    if (!a) return;
    if (a.dataset.a === 'reset') {
      st.estado = {}; st.modo = 'hoy'; st.precio = st.precio0; st.aviso = '';
      dibujar(raiz);
    } else if (a.dataset.a === 'guardar') {
      if (!String(st.por || '').trim()) {
        st.aviso = 'Escribí tu nombre para guardar la propuesta.';
        raiz.querySelector('[data-k="aviso"]').textContent = st.aviso;
        raiz.querySelector('[data-g="por"]').focus();
        return;
      }
      st.aviso = 'Guardando…';
      raiz.querySelector('[data-k="aviso"]').textContent = st.aviso;
      st.enviar('guardar', {
        plato: st.cod, estado: st.estado, modo: st.modo, precio: st.precio,
        obj: st.obj, por: String(st.por).trim(), nonce: Date.now(),
      });
    }
  });
}

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  const d = data || {};
  let raiz = parentElement.querySelector('.sim');
  const nuevo = !raiz || raiz.__st.cod !== (d.plato || {}).cod;
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'sim';
    parentElement.appendChild(raiz);
    enlazar(raiz);
  }
  if (nuevo) {
    const p = d.plato || {};
    raiz.__st = {
      cod: p.cod, nodos: d.nodos || [], div: d.divisor || DIV_DEF,
      precio0: +p.precio || 0, precio: +p.precio || 0, obj: +d.obj || 30,
      modo: 'hoy', estado: {}, abiertos: new Set(['0']), por: d.usuario || '', aviso: '',
    };
  }
  const st = raiz.__st;
  st.enviar = setTriggerValue;
  // El aviso de Python (guardado o error) llega en la corrida siguiente.
  if (d.aviso && d.aviso !== st.avisoPy) { st.avisoPy = d.aviso; st.aviso = d.aviso; }
  if (nuevo) dibujar(raiz);
  else {
    const a = raiz.querySelector('[data-k="aviso"]');
    if (a) a.textContent = st.aviso;
  }
}
