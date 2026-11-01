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
    if (rotY && y && (n <= 8 || i === n - 1 || i === iMax)) h += `<span class="lf-rot" style="left:${((i + 0.5) * w).toFixed(2)}%;bottom:${alto}%">${rotY(y)}</span>`;
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
  if (!fb || !fb.offsetWidth || !lg) return;
  const w = `${fb.offsetWidth + 8}px`;
  if (raiz.style.getPropertyValue('--lf-fecha') !== w) raiz.style.setProperty('--lf-fecha', w);
  const padre = fb.offsetParent;
  if (!padre || !lg.offsetWidth) return;
  const x = `${Math.round(lg.getBoundingClientRect().left - padre.getBoundingClientRect().left)}px`;
  if (fb.style.left !== x) fb.style.left = x;
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
