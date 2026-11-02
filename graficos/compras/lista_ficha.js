// Compras › Proveedor y Producto (regla #774): lo que las dos piezas dibujan
// igual, antepuesto a cada una en Python. La curva va en HTML y en porcentajes:
// mide lo que mida su caja, también con «Ampliar», sin volver a calcular nada.
//
// `ys` son las barras (null: sin barra). `linea`, si viene, se dibuja encima en
// su propia escala, entre `banda[0]` y `banda[1]` % del alto: el precio no se
// lee en la escala de la cantidad, y desde cero no se lo ve moverse.

function lfSpark(vals) {
  const vs = vals.filter((v) => v != null && isFinite(v));
  if (vs.length < 2) return '';
  const lo = Math.min(...vs), hi = Math.max(...vs), r = hi - lo || hi * 0.1 || 1, n = vals.length;
  return vals.map((p, j) => (p == null || !isFinite(p) ? null
    : `${(1 + j * 66 / (n - 1)).toFixed(1)},${(18 - (p - lo) / r * 16).toFixed(1)}`)).filter(Boolean).join(' ');
}

function lfCurva({ etqs, ys, acc, claves, parcial, refY, foco, rotY, linea, hab, marcadas, banda }) {
  const n = etqs.length, w = 100 / Math.max(1, n);
  const nums = ys.filter((y) => y != null && isFinite(y));
  const max = Math.max(1e-9, ...nums, refY != null && isFinite(refY) ? refY : 0) * 1.14;
  const iMax = nums.length ? ys.indexOf(Math.max(...nums)) : -1;
  let h = '<div class="lf-grf">' + [25, 50, 75].map((g) => `<span class="lf-gl" style="bottom:${g}%"></span>`).join('');
  ys.forEach((y, i) => {
    if (y == null || !isFinite(y)) return;
    const alto = (y / max * 100).toFixed(2), par = parcial && i === n - 1;
    h += `<span class="lf-ba${par ? ' par' : ''}${claves[i] === foco ? ' foco' : ''}" style="left:${(i * w + w * 0.18).toFixed(3)}%;width:${(w * 0.64).toFixed(3)}%;height:${alto}%"></span>`;
    if (rotY && y && (n <= 8 || i === n - 1 || i === iMax)) h += `<span class="lf-rot${i === n - 1 ? ' fin' : ''}" style="left:${((i + (i === n - 1 ? 1 : 0.5)) * w).toFixed(2)}%;bottom:${alto}%">${rotY(y)}</span>`;
  });
  if (parcial && n && refY != null && isFinite(refY)) {
    h += `<span class="lf-ref" style="left:${((n - 1) * w + w * 0.1).toFixed(3)}%;width:${(w * 0.8).toFixed(3)}%;bottom:${(refY / max * 100).toFixed(2)}%" title="Los mismos días del período anterior"></span>`;
  }
  if (linea) {
    const vs = [...linea, ...(hab || [])].filter((v) => v != null && isFinite(v));
    if (vs.length) {
      const lo0 = Math.min(...vs), hi0 = Math.max(...vs), rg = Math.max(hi0 - lo0, hi0 * 0.1, 0.01), lo = lo0 - rg * 0.1, up = hi0 + rg * 0.1;
      const [b0, b1] = banda || [10, 85];
      const Y = (v) => (b0 + (up - v) / (up - lo) * (b1 - b0)).toFixed(2), X = (i) => ((i + 0.5) * w).toFixed(2);
      const pts = (a) => a.map((v, i) => (v == null || !isFinite(v) ? null : `${X(i)},${Y(v)}`)).filter(Boolean).join(' ');
      h += `<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${hab ? `<polyline class="hab" points="${pts(hab)}"/>` : ''}<polyline class="lin" points="${pts(linea)}"/></svg>`;
      linea.forEach((v, i) => { if (v != null && isFinite(v)) h += `<span class="lf-pto${marcadas && marcadas[i] ? ' fl' : ''}" style="left:${X(i)}%;top:${Y(v)}%"></span>`; });
      let u = -1;
      linea.forEach((v, i) => { if (v != null && isFinite(v)) u = i; });
      if (u >= 0 && rotY) h += `<span class="lf-prec" style="left:${X(u)}%;top:${Y(linea[u])}%">${rotY(linea[u], true)}</span>`;
    }
  }
  claves.forEach((k, i) => { h += `<button class="lf-hit" data-acc="${acc}" data-v="${String(k).replace(/"/g, '&quot;')}" style="left:${(i * w).toFixed(3)}%;width:${w.toFixed(3)}%" aria-label="${etqs[i]}"></button>`; });
  h += '<div class="lf-tip" hidden></div></div>';
  const paso = Math.max(1, Math.ceil(n / 8));
  h += '<div class="lf-cm">' + etqs.map((t, i) => ((n - 1 - i) % paso === 0 ? `<span style="left:${((i + 0.5) * w).toFixed(2)}%">${t}</span>` : '')).join('') + '</div>';
  return h;
}

// El globo al pasar el cursor por un período: a la derecha o, pasada la mitad, a la izquierda.
function lfTip(raiz, i, n, html) {
  const tip = raiz && raiz.querySelector('.lf-tip');
  if (!tip) return;
  if (i == null || i < 0) { tip.hidden = true; return; }
  tip.innerHTML = html;
  tip.hidden = false;
  const x = (i + 0.5) / Math.max(1, n) * 100;
  tip.style.left = x > 52 ? `calc(${x.toFixed(2)}% - ${(tip.offsetWidth || 230) + 12}px)` : `calc(${x.toFixed(2)}% + 12px)`;
}

// La fecha y el filtro son de Python: se paran en el hueco que la pieza les deja.
function lfPasarFecha(raiz, selector) {
  const fb = document.querySelector(selector), lg = raiz.querySelector('.lf-lugar');
  if (!fb) return;
  // Con la lista o la ficha ampliadas el nivel 3 no está: la fecha tampoco (#789).
  const ver = !!(lg && lg.offsetWidth);
  if (fb.style.visibility !== (ver ? '' : 'hidden')) fb.style.visibility = ver ? '' : 'hidden';
  if (!ver || !fb.offsetWidth) return;
  const w = `${fb.offsetWidth + 8}px`;
  if (raiz.style.getPropertyValue('--lf-fecha') !== w) raiz.style.setProperty('--lf-fecha', w);
  const padre = fb.offsetParent;
  if (!padre) return;
  const a = lg.getBoundingClientRect(), b = padre.getBoundingClientRect();
  const x = `${Math.round(a.left - b.left)}px`, y = `${Math.round(a.top - b.top + (a.height - fb.offsetHeight) / 2)}px`;
  if (fb.style.left !== x) fb.style.left = x;
  if (fb.style.top !== y) fb.style.top = y;
}

function lfMenuFamilias(pa, abierto, fmt, escapar) {
  if (!pa || !pa.todas || !pa.todas.length) return '';
  const el = new Set(pa.elegidas), n = pa.elegidas.length || pa.todas.length;
  return `<div class="lf-ms"><button class="lf-pil" data-acc="menu" data-v="fam" aria-expanded="${abierto}">${n === pa.todas.length ? 'Todas las familias' : `Familias: ${n} de ${pa.todas.length}`} ▾</button>`
    + (abierto ? `<div class="lf-pop">${pa.todas.map(([r, nom, v]) => `<label><input type="checkbox" data-pfam value="${escapar(r)}"${el.has(r) || !el.size ? ' checked' : ''}><span>${escapar(nom)}</span><small>${fmt(v)}</small></label>`).join('')}<p>Vale para todas las vistas de Compras.</p></div>` : '')
    + '</div>';
}

function lfFuera(pa, fmt, escapar) {
  if (!pa || !pa.todas || !pa.elegidas.length) return '';
  const el = new Set(pa.elegidas), fuera = pa.todas.filter((x) => !el.has(x[0])), s = fuera.reduce((a, x) => a + x[2], 0);
  if (s <= 0.5) return '';
  return `<div class="lf-fuera"><span>Fuera de esta cuenta: ${fmt(s)} de ${escapar(fuera.slice(0, 2).map((x) => x[1]).join(', '))}${fuera.length > 2 ? '…' : ''}</span><button class="lf-quita" data-acc="sumar">Sumarlas</button></div>`;
}

// ── El lenguaje de Costo de Carta (#775, regla #789 en Compras) ────────────
// Nivel 2 (subrayado, de borde a borde): cómo ver la lista, y a la derecha
// «Detalle» y «Cómo se calcula». Nivel 3, la cabecera de siempre sin título:
// la fecha, las familias, el buscador y el Excel. «Detalle» y lo plegado se
// recuerdan en el navegador, por pieza.
const LF_ICONO_AMP = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4"/></svg>';
const LF_ICONO_VOLVER = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 2v4H2M14 6h-4V2M10 14v-4h4M2 10h4v4"/></svg>';

function lfLeer(clave, defecto) {
  try { const v = localStorage.getItem(clave); return v == null ? defecto : JSON.parse(v); } catch (e) { return defecto; }
}
function lfGuardar(clave, valor) {
  try { localStorage.setItem(clave, JSON.stringify(valor)); } catch (e) { /* sin almacenamiento: sólo esta vez */ }
}

// `tabs`: [[clave, texto, ayuda]]; `extra`: lo que va pegado a las pestañas.
function lfNivel2(tabs, on, det, comoAbierto, comoHtml, extra) {
  const e = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  return `<div class="lf-n2"><div class="lf-tabs" role="tablist">${tabs.map(([k, t, tip]) => `<button role="tab" class="${on === k ? 'on' : ''}" data-acc="ver" data-v="${k}" aria-selected="${on === k}"${tip ? ` title="${e(tip)}"` : ''}>${e(t)}</button>`).join('')}</div>${extra || ''}`
    + `<div class="lf-n2-der"><label class="lf-switch"><input type="checkbox" data-acc="detalle" role="switch"${det ? ' checked' : ''}>Detalle</label>`
    + `<span class="lf-como"><button class="lf-link" data-acc="como" aria-expanded="${!!comoAbierto}">Cómo se calcula</button>${comoAbierto ? `<div class="lf-pop lf-pop-como" role="dialog">${comoHtml}</div>` : ''}</span></div></div>`;
}

function lfAmp(cual, on, rotulo) {
  return `<button class="lf-amp" data-acc="amp" data-v="${cual}" aria-pressed="${!!on}" title="${on ? 'Volver (Esc)' : `Ampliar ${rotulo}`}" aria-label="${on ? 'Volver' : `Ampliar ${rotulo}`}">${on ? LF_ICONO_VOLVER : LF_ICONO_AMP}</button>`;
}

// Un plegable: el título siempre, el cuerpo si está abierto.
function lfPleg(id, titulo, cuerpo, abierto, cifra) {
  return `<div class="lf-pleg${abierto ? ' abierto' : ''}"><button class="lf-pleg-b" data-acc="pleg" data-v="${id}" aria-expanded="${!!abierto}"><span>${titulo}</span>${cifra ? `<b>${cifra}</b>` : ''}<i><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5l3 3 3-3"/></svg></i></button>${abierto ? `<div class="lf-pleg-c">${cuerpo}</div>` : ''}</div>`;
}

// `Esc` vuelve de una zona ampliada o cierra el pop. Se escucha en el documento:
// el redibujo reemplaza el botón que tenía el foco (#780).
function lfEscape(G, pintar) {
  if (G.escOk) return;
  G.escOk = true;
  document.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Escape' || !G.raiz || !G.raiz.isConnected) return;
    if (G.st.como) { G.st.como = false; pintar(); } else if (G.st.amp) { G.st.amp = null; pintar(); }
  });
}
