// Recetas › «Nuevo Costeo»: la receta y su precio (regla #697).
//
// La monta formulario_receta.py::_pieza con st.components.v2 (sin iframe,
// estilos en un shadow root). Es la forma del boceto aprobado
// (https://claude.ai/artifact/Rb2hkVYJQVLWy7NstKqufo): las líneas de la
// receta con su cantidad y su precio editables, y al costado el precio de
// venta, los cinco canales del POS y a cuánto llevarlo para quedar en 30 o
// 35 %. El buscador, el importador, guardar y enviar, y el panel de «Dónde
// se usa» / lo nuevo siguen en Python.
//
// LA CUENTA CORRE ACÁ mientras se escribe, y lo editado vuelve a Python en
// `cambios` (una foto entera de lo editable, con `rev`), medio segundo
// después de la última tecla. Hasta que Python devuelve ese `rev`, lo que
// llega no pisa lo escrito: se toman sus líneas (pudo sumarse una desde el
// buscador) con las cantidades, precios y quitadas de acá encima. Los
// botones que cambian más que números van en `accion`.
//
// El precio de una línea se guarda por la unidad de la RECETA (S/ por
// gramo); en gramos y mililitros se muestra y se escribe por kilo y litro,
// como se compra.

const ESPERA = 500;
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function dinero(v, dec = 2) {
  if (v == null || !isFinite(v)) return '—';
  const s = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  return `${v < -0.004 ? '−' : ''}S/ ${s}`;
}
const pct = (v) => (v == null || !isFinite(v) ? '—' : `${v.toFixed(1)} %`);
const num = (v) => (Math.round(v * 10000) / 10000).toString();
function nivel(d, p) {
  if (p == null) return '';
  return p > d.umbrales[1] ? 'rojo' : p > d.umbrales[0] ? 'ambar' : 'verde';
}
// GRAMOS → kg, MILILITROS → l: el precio se lee como se compra.
function escala(unidad) {
  const u = String(unidad || '').toUpperCase().trim();
  if (['GRAMOS', 'GRAMO', 'GR', 'G', 'GRS'].includes(u)) return [1000, 'kg', 'g'];
  if (['MILILITROS', 'MILILITRO', 'ML'].includes(u)) return [1000, 'l', 'ml'];
  return [1, u.toLowerCase() || 'unidad', u.toLowerCase() || 'unidad'];
}

// ── Las cuentas ──────────────────────────────────────────────────────────
const costoDe = (ls) => ls.reduce((s, l) => s + l.cantidad * l.precio, 0);
function cuentas(d, costo, pv) {
  const neto = pv > 0 ? pv / d.divisor : 0;
  return { pv, neto, recargo: neto * d.recargo, igv: neto * d.igv, util: neto - costo,
    pct: neto > 0 ? costo / neto * 100 : null };
}

// ── La tabla ─────────────────────────────────────────────────────────────
function chip(l) {
  const c = l.chip;
  const cls = c.includes('nuevo') ? (l.estado === 'ok' ? 'lav' : 'ambar') : c === '(Rs)' || c === 'Rs' ? 'azul' : c === 'P' ? 'lav' : '';
  const t = { P: '(P)', Rs: '(Rs)', L: '(L)' }[c] || c;
  const ayuda = c.includes('nuevo') ? (l.estado === 'ok' ? 'Nuevo, con su costo completo' : 'Nuevo: precio estimado o falta detalle')
    : { P: 'Porcionado', Rs: 'Receta base', L: 'Insumo limpio', insumo: 'Insumo de compra', plato: 'Producto de venta' }[c] || '';
  return `<span class="nc-chip ${cls}" title="${esc(ayuda)}">${esc(t)}</span>`;
}
function htmlTabla(d, st) {
  const ls = st.lineas;
  if (!ls.length) {
    const msg = d.modo === 'modificar' ? 'Elegí arriba un plato, combo o receta base del sistema y dale «Importar»: su receta aparece acá para editarla.'
      : 'Buscá un artículo arriba y agregalo con «+»: la receta se arma acá.';
    return `<div class="nc-vacio">${msg}</div>`;
  }
  const costo = costoDe(ls), max = Math.max(1e-9, ...ls.map((l) => l.cantidad * l.precio));
  const conAntes = !!(d.origen || d.es_base) && d.modo === 'modificar';
  const filas = ls.map((l) => {
    const [f, uc, ur] = escala(l.unidad);
    const c = l.cantidad * l.precio;
    let vs = '';
    if (conAntes) {
      if (!l.antes) vs = `<span class="nc-vs sube" title="No está en la receta del sistema">nueva ${dinero(c)}</span>`;
      else {
        const dc = c - l.antes[0] * l.antes[1];
        const cambio = Math.abs(l.cantidad - l.antes[0]) > 1e-9 || Math.abs(l.precio - l.antes[1]) > 1e-9;
        vs = cambio ? `<span class="nc-vs ${dc > 0.004 ? 'sube' : dc < -0.004 ? 'baja' : ''}" title="En el sistema: ${num(l.antes[0])} ${esc(ur)}">${dc >= 0 ? '+' : '−'}${dinero(Math.abs(dc)).replace('S/ ', 'S/ ')}</span>` : '<span class="nc-vs">—</span>';
      }
    }
    const cambiada = l.antes && (Math.abs(l.cantidad - l.antes[0]) > 1e-9);
    const sub = d.combo ? (l.grupo || (l.chip.includes('nuevo') ? 'nuevo' : '')) : l.usos;
    return `<tr class="nc-f${st.sel === l.uid ? ' sel' : ''}${l.cantidad === 0 ? ' cero' : ''}" data-uid="${esc(l.uid)}">
      <td class="nc-ins"><div>${chip(l)}<b title="${esc(l.nombre)}${l.cod ? ' · ' + esc(l.cod) : ''}">${esc(l.nombre.replace(/^\((L|P|Rs)\)\s*/, ''))}</b>${l.inactivo ? '<span class="nc-tag" title="Inactivo en el almacén">inactivo</span>' : ''}</div>
        ${sub ? `<span title="${esc(sub)}">${esc(sub)}</span>` : ''}</td>
      <td class="num nc-cant"><input type="number" min="0" step="any" data-campo="cantidad" data-uid="${esc(l.uid)}" value="${num(l.cantidad)}" class="${cambiada ? 'cambio' : ''}" aria-label="Cantidad"><span>${esc(ur)}</span></td>
      <td class="num nc-pre">${l.fijo ? `<span title="Sale de su detalle, en el panel de lo nuevo">${dinero(l.precio * f, f > 1 ? 2 : 4)}</span>`
        : `<span>S/</span><input type="number" min="0" step="any" data-campo="precio" data-uid="${esc(l.uid)}" value="${num(l.precio * f)}" aria-label="Precio por ${esc(uc)}">`}<span>/ ${esc(uc)}</span></td>
      <td class="nc-costo"><div><i style="width:${Math.max(2, c / max * 80)}px"></i><b class="num">${dinero(c)}</b><span class="num">${costo ? Math.round(c / costo * 100) : 0} %</span></div></td>
      ${conAntes ? `<td class="num">${vs}</td>` : ''}
      <td class="nc-x"><button type="button" data-acc="quitar" data-uid="${esc(l.uid)}" aria-label="Quitar ${esc(l.nombre)}">×</button></td></tr>`;
  }).join('');
  return `<div class="nc-tabla"><table><thead><tr><th>${d.combo ? 'Producto' : 'Insumo'}</th><th class="num">Cantidad</th>
      <th class="num" title="${d.combo ? 'Costo de una porción' : 'Precio promedio del almacén, por la unidad en que se compra'}">${d.combo ? 'Costo' : 'Precio de compra'}</th>
      <th>Costo en ${d.combo ? 'el combo' : 'el plato'}</th>${conAntes ? '<th class="num">vs. sistema</th>' : ''}<th></th></tr></thead><tbody>${filas}</tbody></table></div>`;
}
function htmlPieTabla(d, st) {
  const ls = st.lineas, costo = costoDe(ls);
  let cambios = '';
  if (d.modo === 'modificar' && (d.origen || d.es_base)) {
    const n = ls.filter((l) => !l.antes || Math.abs(l.cantidad - l.antes[0]) > 1e-9 || Math.abs(l.precio - l.antes[1]) > 1e-9).length
      + (d.origen ? d.origen.quitadas : 0) + st.quitar.size;
    cambios = n ? ` · ${n} ${n === 1 ? 'cambio' : 'cambios'} respecto del sistema` : ' · sin cambios respecto del sistema';
  }
  const original = d.modo === 'modificar' && (d.origen || d.es_base)
    ? '<button type="button" class="nc-btn" data-acc="original">Volver al original</button>' : '';
  return `<span class="nc-pie-txt">${ls.length} ${ls.length === 1 ? 'línea' : 'líneas'}${cambios}</span>
    <span class="nc-pie-bot">${original}<button type="button" class="nc-btn" data-acc="vaciar" ${ls.length ? '' : 'disabled'}>Vaciar</button></span>
    <span class="nc-total"><span>Costo ${d.combo ? 'del combo' : 'de la receta'}</span><b class="num">${dinero(costo)}</b></span>`;
}

// ── El precio, los canales y lo que se abre al costado ───────────────────
function htmlPrecio(d, st) {
  const costo = costoDe(st.lineas);
  const botones = [];
  if (d.paneles.includes('usos')) botones.push('<button type="button" class="nc-btn" data-acc="panel" data-panel="usos">Dónde se usa ›</button>');
  const nuevo = d.paneles.find((p) => p !== 'usos');
  if (nuevo) botones.push(`<button type="button" class="nc-btn ambar" data-acc="panel" data-panel="${esc(nuevo)}">Lo nuevo · ${d.n_nuevos} ›</button>`);
  const aviso = d.aviso ? `<div class="nc-aviso" title="${esc(d.aviso)}">${esc(d.aviso)}</div>` : '';
  if (d.es_base) {
    const b = d.base;
    if (!b) return `<div class="nc-vacio">Importá una receta base para ver su costo contra el del sistema y a qué platos afecta.</div>`;
    const por = b.rinde > 0 ? costo / b.rinde : 0, delta = por - b.actual, p = b.actual > 0 ? delta / b.actual * 100 : null;
    return `<div class="nc-ptit">Costo de la receta base</div>
      <div class="nc-cifras"><div><span>Por ${esc(b.una)}, ahora</span><b class="num">${dinero(por)}</b></div>
        <div><span>En el sistema</span><b class="num">${dinero(b.actual)}</b></div>
        <div><span>Cambio</span><b class="num ${delta > 0.004 ? 'sube' : delta < -0.004 ? 'baja' : ''}">${delta >= 0 ? '+' : '−'}${dinero(Math.abs(delta))}${p != null ? ` · ${p >= 0 ? '+' : '−'}${Math.abs(p).toFixed(1)} %` : ''}</b></div></div>
      <div class="nc-nota">Rinde ${num(b.rinde)} ${esc(b.una)} por tanda (${dinero(costo)}). La llevan ${b.n_platos} ${b.n_platos === 1 ? 'plato' : 'platos'} y ${b.n_bases} ${b.n_bases === 1 ? 'receta base' : 'recetas base'}.</div>
      ${aviso}
      <div class="nc-pbot"><button type="button" class="nc-btn prim" data-acc="panel" data-panel="precio">Rinde y a qué recetas afecta ›</button>${botones.join('')}</div>`;
  }
  const N = cuentas(d, costo, st.pv);
  const A = d.origen && d.origen.pv > 0 ? cuentas(d, d.origen.costo, d.origen.pv) : null;
  const tot = Math.max(st.pv, costo + N.recargo + N.igv, 0.01);
  const barra = st.pv > 0 ? `<div class="nc-barra">
      <i class="c ${nivel(d, N.pct)}" style="width:${Math.min(100, costo / tot * 100)}%" title="Costo ${dinero(costo)}"></i>
      <i class="u" style="width:${Math.max(0, N.util) / tot * 100}%" title="Utilidad ${dinero(N.util)}"></i>
      <i class="r" style="width:${N.recargo / tot * 100}%" title="Recargo ${dinero(N.recargo)}"></i>
      <i class="g" style="width:${N.igv / tot * 100}%" title="IGV ${dinero(N.igv)}"></i></div>
    <div class="nc-ley num"><span><i class="c ${nivel(d, N.pct)}"></i>costo ${dinero(costo)}</span><span><i class="u"></i>utilidad ${dinero(N.util)}</span>
      <span><i class="r"></i>recargo ${dinero(N.recargo)}</span><span><i class="g"></i>IGV ${dinero(N.igv)}</span></div>` : '';
  const mismo = !st.precios;
  const canales = d.canales.map((n, i) => {
    const p = mismo ? st.pv : (i === 0 ? st.pv : st.precios[i]);
    const c = cuentas(d, costo, p);
    const celda = !mismo && i > 0
      ? `<input type="number" min="0" step="0.5" data-campo="canal" data-i="${i}" value="${p || ''}" aria-label="Precio en ${esc(n)}">`
      : `<span class="num">${p > 0 ? dinero(p, p % 1 ? 2 : 0) : '—'}</span>`;
    return `<tr><td>${esc(n)}</td><td class="num">${celda}</td><td class="num"><span class="pill ${nivel(d, c.pct)}">${pct(c.pct)}</span></td>
      <td class="num${c.util < 0 && p > 0 ? ' sube' : ''}">${p > 0 ? dinero(c.util) : '—'}</td></tr>`;
  }).join('');
  const objetivos = costo > 0 ? d.umbrales.map((u) => {
    const p = Math.ceil(costo / (u / 100) * d.divisor);
    return `<button type="button" class="nc-obj" data-acc="objetivo" data-pv="${p}"><span>Para quedar en ${u} %</span><b class="num">${dinero(p, 0)}</b></button>`;
  }).join('') : '';
  const sistema = A ? `<div class="nc-nota">En el sistema: ${dinero(A.pv, A.pv % 1 ? 2 : 0)} · costo ${dinero(d.origen.costo)} · <b>${pct(A.pct)}</b>
      → ahora <b class="${nivel(d, N.pct)}">${pct(N.pct)}</b></div>` : '';
  return `<div class="nc-pv">
      <label><span>Precio de venta · ${esc(d.canales[0])}</span>
        <span class="nc-pv-in"><span>S/</span><input type="number" min="0" step="0.5" data-campo="pv" value="${st.pv || ''}" placeholder="0.00" aria-label="Precio de venta"></span></label>
      <div><span>% de costo</span><b class="pill grande ${nivel(d, N.pct)}">${pct(N.pct)}</b></div>
      <div><span>Utilidad</span><b class="num${N.util < 0 && st.pv > 0 ? ' sube' : ''}">${st.pv > 0 ? dinero(N.util) : '—'}</b></div></div>
    ${sistema}${barra}
    <div class="nc-canales"><div class="nc-crot"><span>Los cinco canales del POS</span>
        <label><input type="checkbox" data-acc="mismo" ${mismo ? 'checked' : ''}> mismo precio en todos</label></div>
      <table><thead><tr><th>Canal</th><th class="num">Precio</th><th class="num">% costo</th><th class="num">Utilidad</th></tr></thead><tbody>${canales}</tbody></table></div>
    ${objetivos ? `<div class="nc-objs">${objetivos}</div>` : ''}
    ${aviso}
    ${botones.length ? `<div class="nc-pbot">${botones.join('')}</div>` : ''}`;
}

// ── Dibujar ──────────────────────────────────────────────────────────────
function dibujar(raiz, solo) {
  const { data: d, st } = raiz.__d;
  if (!raiz.querySelector('.nc-cuerpo')) {
    raiz.innerHTML = `<div class="nc-cuerpo"><div class="nc-receta"><div data-zona="tabla" class="nc-zt"></div><div class="nc-pie" data-zona="pie"></div></div>
      <div class="nc-precio" data-zona="precio"></div></div>`;
  }
  const z = (n) => raiz.querySelector(`[data-zona="${n}"]`);
  if (solo !== 'numeros') {
    const t = z('tabla'), y = t.querySelector('.nc-tabla')?.scrollTop || 0;
    t.innerHTML = htmlTabla(d, st);
    const nt = t.querySelector('.nc-tabla');
    if (nt) nt.scrollTop = y;
  } else {
    // Escribir no redibuja la tabla (el campo no pierde el foco): sólo las
    // cifras de cada fila.
    const costo = costoDe(st.lineas), max = Math.max(1e-9, ...st.lineas.map((l) => l.cantidad * l.precio));
    st.lineas.forEach((l) => {
      const tr = raiz.querySelector(`tr[data-uid="${CSS.escape(l.uid)}"]`);
      if (!tr) return;
      const c = l.cantidad * l.precio;
      tr.querySelector('.nc-costo b').textContent = dinero(c);
      tr.querySelector('.nc-costo span').textContent = `${costo ? Math.round(c / costo * 100) : 0} %`;
      tr.querySelector('.nc-costo i').style.width = `${Math.max(2, c / max * 80)}px`;
    });
  }
  z('pie').innerHTML = htmlPieTabla(d, st);
  const pr = z('precio');
  const foco = pr.contains(raiz.getRootNode().activeElement) ? raiz.getRootNode().activeElement : null;
  if (!foco) pr.innerHTML = htmlPrecio(d, st);
  else {
    // Con el foco en un precio, se redibuja todo menos ese campo.
    const campo = foco.dataset.campo, i = foco.dataset.i;
    pr.innerHTML = htmlPrecio(d, st);
    const nuevo = pr.querySelector(`[data-campo="${campo}"]${i ? `[data-i="${i}"]` : ''}`);
    if (nuevo) { nuevo.replaceWith(foco); }
  }
}

// ── Ida y vuelta con Python ──────────────────────────────────────────────
function enviar(raiz) {
  const st = raiz.__d.st;
  clearTimeout(st.timer);
  st.timer = setTimeout(() => {
    st.timer = null;
    st.rev += 1;
    st.enviado = st.rev;
    raiz.__d.trigger('cambios', {
      rev: st.rev, lineas: st.lineas.map((l) => [l.uid, l.cantidad, l.precio]),
      quitar: [...st.quitar], pv: st.pv || null, precios: st.precios,
    });
  }, ESPERA);
}
function accion(raiz, que, extra = {}) {
  clearTimeout(raiz.__d.st.timer);
  raiz.__d.trigger('accion', Object.assign({ que, n: Date.now() }, extra));
}
// Lo que llega de Python. Si ya aplicó lo último que se mandó, manda él;
// si no, sus líneas con lo editado acá encima.
function recibir(raiz, d) {
  const st = raiz.__d.st;
  const enVuelo = st.timer !== null || st.enviado > d.rev;
  if (!st.listo || !enVuelo) {
    st.lineas = d.lineas.map((l) => Object.assign({}, l));
    st.pv = d.pv; st.precios = d.precios; st.quitar = new Set();
    st.rev = Math.max(st.rev, d.rev); st.enviado = 0; st.listo = true;
    return;
  }
  const locales = new Map(st.lineas.map((l) => [l.uid, l]));
  st.lineas = d.lineas.filter((l) => !st.quitar.has(l.uid)).map((l) => {
    const x = locales.get(l.uid);
    return Object.assign({}, l, x ? { cantidad: x.cantidad, precio: l.fijo ? l.precio : x.precio } : {});
  });
}

function enlazar(raiz) {
  raiz.addEventListener('input', (ev) => {
    const el = ev.target, campo = el.dataset.campo;
    if (!campo) return;
    const st = raiz.__d.st, v = parseFloat(el.value);
    if (campo === 'cantidad' || campo === 'precio') {
      const l = st.lineas.find((x) => x.uid === el.dataset.uid);
      if (!l || !isFinite(v) || v < 0) return;
      if (campo === 'cantidad') l.cantidad = v;
      else l.precio = v / escala(l.unidad)[0];
      dibujar(raiz, 'numeros');
    } else if (campo === 'pv') {
      st.pv = isFinite(v) && v > 0 ? v : 0;
      dibujar(raiz, 'numeros');
    } else if (campo === 'canal') {
      st.precios[+el.dataset.i] = isFinite(v) && v > 0 ? v : 0;
      dibujar(raiz, 'numeros');
    }
    enviar(raiz);
  });
  raiz.addEventListener('change', (ev) => {
    if (ev.target.dataset.acc !== 'mismo') return;
    const st = raiz.__d.st;
    st.precios = ev.target.checked ? null : raiz.__d.data.canales.map(() => st.pv || 0);
    dibujar(raiz, 'numeros');
    enviar(raiz);
  });
  raiz.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-acc]');
    const st = raiz.__d.st;
    const fila = ev.target.closest('tr[data-uid]');
    if (fila && !b && st.sel !== fila.dataset.uid) {
      st.sel = fila.dataset.uid;
      raiz.querySelectorAll('tr.nc-f').forEach((t) => t.classList.toggle('sel', t.dataset.uid === st.sel));
    }
    if (!b || b.dataset.acc === 'mismo') return;
    const acc = b.dataset.acc;
    if (acc === 'quitar') {
      st.quitar.add(b.dataset.uid);
      st.lineas = st.lineas.filter((l) => l.uid !== b.dataset.uid);
      dibujar(raiz);
      enviar(raiz);
    } else if (acc === 'objetivo') {
      st.pv = +b.dataset.pv;
      dibujar(raiz, 'numeros');
      enviar(raiz);
    } else if (acc === 'vaciar' || acc === 'original') {
      accion(raiz, acc);
    } else if (acc === 'panel') {
      accion(raiz, 'panel', { panel: b.dataset.panel });
    }
  });
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  if (!data || !data.lineas) return;
  let raiz = parentElement.querySelector('.nc');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'nc';
    parentElement.appendChild(raiz);
    raiz.__d = { st: { lineas: [], pv: 0, precios: null, quitar: new Set(), rev: 0, enviado: 0, timer: null, sel: null, listo: false } };
    enlazar(raiz);
  }
  // Otro modo es otra receta: se empieza de cero.
  if (raiz.__d.data && raiz.__d.data.modo !== data.modo) raiz.__d.st.listo = false;
  raiz.__d.trigger = setTriggerValue;
  raiz.__d.data = data;
  recibir(raiz, data);
  // Si las filas son las mismas (lo que volvió es lo que se escribió), no se
  // rehace la tabla: el campo donde se está escribiendo no pierde el foco.
  const forma = raiz.__d.st.lineas.map((l) => [l.uid, l.nombre, l.unidad, l.fijo, l.chip, l.estado, l.usos].join('|')).join('¦')
    + data.modo + (data.origen ? 'o' : '') + (data.es_base ? 'b' : '');
  dibujar(raiz, forma === raiz.__d.forma ? 'numeros' : undefined);
  raiz.__d.forma = forma;
}
