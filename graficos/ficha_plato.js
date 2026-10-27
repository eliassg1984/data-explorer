// Recetas › «Costo de Carta» › lo de la ficha del plato que llega de Python
// (reglas #744 y #746).
//
// Desde la regla #746 no es una pieza aparte: `carta_costeada.py` antepone
// este archivo al de la lista (`carta_costeada.js`), y la ficha del costado
// dibuja con estas funciones sus pestañas Receta y Evolución, el «Qué mueve
// el costo de hoy» y «Costo y utilidad» del Resumen. Todo va dentro de
// `FichaPlato` para no chocar con los nombres de la lista, que vive en el
// mismo módulo.
//
// Python manda en `data.ficha` lo de carta_costeada.armar_ficha: `plato`,
// `filas` (la receta aplanada, ver `filas_receta`), `meses`, `rango`,
// `marcas`, `cambios`, `picos`, `cortes`, `q`, `divisor`, `umbrales`,
// `combo_antes` y `faltan`. Lo que se elige acá vuelve a Python por la lista:
// `simular` ({cod, estado, n}: abre la modal, sembrada con el precio
// habitual de un corte si viene `estado`), `nuevo_costeo` ({cod, n}) y
// `produccion` ({destino: 'rend'|'rev', cod, n}).

const FichaPlato = (() => {
  const R = { id: 0, par: 1, niv: 2, nom: 3, ficha: 4, cant: 5, unid: 6, costo: 7, nh: 8, cod: 9, fbase: 10, ruta: 11 };
  const M = { mes: 0, u: 1, cu: 2, neto: 3, pct: 4, sin: 5 };
  const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
  const NOMBRE_MES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'setiembre', 'octubre',
    'noviembre', 'diciembre'];
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const f2 = (v) => Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  function dinero(v, dec = 2) {
    if (v == null || !isFinite(v)) return '—';
    const s = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    return `${v < 0 ? '−' : ''}S/ ${s}`;
  }
  const pct = (v) => (v == null || !isFinite(v) ? '—' : `${v.toFixed(1)} %`);
  const signo = (v) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(1)} %`;
  const cant = (v) => (Math.round(v * 1000) / 1000).toLocaleString('en-US', { maximumFractionDigits: 3 });
  const etqMes = (m) => `${MESES[+m.slice(5) - 1]} ${m.slice(2, 4)}`;
  // El nombre sin el área ni la unidad del Almacén: «Salsa de lomo x kg
  // (Calientes)» → «Salsa de lomo». En la receta va entero.
  const UNIDAD_FINAL = /\s+x\s+(und|unid|kg|porc|por|lt|l|gr|g)(\s.*)?$/i;
  const corto = (s) => String(s || '').replace(/\s*\([^)]*\)\s*$/, '').replace(UNIDAD_FINAL, '').trim() || String(s || '');
  const fecha = (s) => (s ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(2, 4)}` : '—');

  // ── Las cuentas (puras: las lee test_ficha_plato.py) ─────────────────────
  function nivel(d, p) {
    if (p == null) return '';
    return p > d.umbrales[1] ? 'rojo' : p > d.umbrales[0] ? 'ambar' : 'verde';
  }
  // Las cifras del Resumen y las de «Costo y utilidad».
  function cifras(d) {
    const p = d.plato, conCosto = !p.sin_costo && p.costo > 0;
    const pctHoy = conCosto && p.neto ? p.costo / p.neto * 100 : null;
    const vnetoU = p.vend > 0 ? p.vneto / p.vend : null;
    const vcostoU = p.vend > 0 ? p.vcosto / p.vend : null;
    const pctV = p.vneto > 0.5 && p.vcosto > 0 ? p.vcosto / p.vneto * 100 : null;
    const con = d.meses.filter((m) => m[M.cu] != null);
    let mm = null;
    if (con.length >= 2) {
      const a = con[con.length - 2], b = con[con.length - 1];
      mm = { a: a[M.cu], b: b[M.cu], ma: a[M.mes], mb: b[M.mes], var: (b[M.cu] / a[M.cu] - 1) * 100 };
    }
    let tramo = null;
    if (con.length >= 2) {
      const a = con[0], b = con[con.length - 1];
      tramo = { a: a[M.cu], b: b[M.cu], ma: a[M.mes], mb: b[M.mes], var: (b[M.cu] / a[M.cu] - 1) * 100 };
    }
    const objetivos = d.umbrales.map((u) => ({
      u, precio: conCosto ? p.costo / (u / 100) * d.divisor : null, costo: p.neto * u / 100,
    }));
    return { pctHoy, margen: conCosto ? p.neto - p.costo : null, vnetoU, vcostoU, pctV, mm, tramo, objetivos };
  }
  // Qué filas se ven con las recetas base `abiertos` abiertas.
  function visibles(filas, abiertos) {
    const porId = new Map(filas.map((f) => [f[R.id], f]));
    return filas.filter((f) => {
      let p = f[R.par];
      while (p >= 0) { if (!abiertos.has(p)) return false; p = porId.get(p)[R.par]; }
      return true;
    });
  }
  // El reparto: las cinco líneas de arriba que más pesan y el resto junto.
  function reparto(filas) {
    const arriba = filas.filter((f) => f[R.par] === -1).sort((a, b) => b[R.costo] - a[R.costo]);
    const out = arriba.slice(0, 5).map((f) => ({ n: corto(f[R.nom]), v: f[R.costo], id: f[R.id] }));
    if (arriba.length > 5) {
      const resto = arriba.slice(5);
      out.push({ n: `${resto.length} ${resto.length === 1 ? 'línea más' : 'líneas más'}`,
        v: resto.reduce((s, f) => s + f[R.costo], 0), id: -1, ids: resto.map((f) => f[R.id]) });
    }
    return out;
  }
  // El tope del eje del costo: un número redondo por encima de todo lo dibujado.
  function tope(valores) {
    const m = Math.max(1, ...valores.filter((v) => v != null && isFinite(v)));
    const paso = m > 60 ? 20 : m > 25 ? 10 : m > 10 ? 5 : m > 4 ? 2 : 1;
    return Math.ceil(m * 1.12 / paso) * paso;
  }
  // Qué pasó en un mes: ediciones, cambios de la auditoría, picos y
  // porcionamientos que fijaron el precio de un corte.
  function delMes(d, mes) {
    const cosas = [];
    d.marcas.filter((k) => k.t.slice(0, 7) === mes).forEach((k) => cosas.push({ s: '▼', c: 'marca', t: k.x }));
    d.cambios.filter((k) => k.t.slice(0, 7) === mes).forEach((k) => cosas.push({ s: '◆', c: 'cambio', t: k.x }));
    d.picos.filter((k) => k.ini.slice(0, 7) === mes).forEach((k) => cosas.push({ s: '◯', c: 'pico', t: k.x }));
    Object.values(d.cortes).forEach((c) => {
      const u = c.filas[0];
      if (u && u[0].slice(0, 7) === mes) {
        const doc = c.ult.doc ? `PO-${c.ult.doc}, ` : '';
        cosas.push({ s: '●', c: 'porc', t: `${fecha(u[0])} · ${corto(c.n)} entró a ${dinero(u[7])} por ${c.u.toLowerCase()} `
          + `(${doc}desde ${u[1]}, ${u[6].toFixed(1)} % de merma): es el precio que tiene hoy en la receta.` });
      }
    });
    return cosas;
  }
  // El pico del rango de la tarjeta, si lo hubo: explica un «se vendió al»
  // muy por encima del costo de hoy.
  function picoDelRango(d) {
    if (!d.rango) return null;
    return d.picos.filter((p) => p.fin >= d.rango[0] && p.ini <= d.rango[1]).slice(-1)[0] || null;
  }
  // Cuántas líneas tiene la receta: las de arriba y, con las de adentro.
  function lineas(d) {
    const nl = d.filas.filter((f) => f[R.par] === -1).length;
    return d.filas.length ? `${nl} ${nl === 1 ? 'línea' : 'líneas'}${d.filas.length > nl ? `, ${d.filas.length} con las de adentro` : ''}` : '';
  }

  // ── El HTML ─────────────────────────────────────────────────────────────
  // Lo que vendió a costo 0 y «Qué mueve el costo de hoy».
  function htmlAvisos(d, { sinNota = false } = {}) {
    const p = d.plato, q = d.q, out = [];
    if (p.sin_neto > 0 && !sinNota) {
      out.push(`<div class="fp-nota ambar">${dinero(p.sin_neto, 0)} de lo vendido en el rango entró al FoodCost con costo 0: ${esc(p.sin_causa)}, y así queda guardado.</div>`);
    }
    if (q) {
      const origen = q.de_porc ? ` —que también sale de un porcionamiento—` : '';
      const sube = q.ult > q.hab;
      out.push(`<div class="fp-mueve"><div class="fp-mueve-txt"><b class="fp-mueve-tit">Qué mueve el costo de hoy</b>
        <div>El <b>${pct(q.pct)}</b> del costo es <b>${esc(corto(q.nombre))}</b> (${dinero(q.ult)} por ${esc(q.unid.toLowerCase())}). Ese precio salió del porcionamiento <b>${q.doc ? `PO-${esc(q.doc)} ` : ''}del ${fecha(q.fecha)}</b>, hecho desde <b>${esc(corto(q.de))}</b>${origen} con ${q.merma.toFixed(1)} % de merma. Los ${q.n} porcionamientos de los 30 días anteriores dieron <b class="num">${dinero(q.hab)}</b> por ${esc(q.unid.toLowerCase())} (ponderado por lo que salió).</div>
        <div>Con ese precio el plato costaría <b class="num">${dinero(q.plato)}</b> y quedaría en <b class="num ${nivel(d, q.pct_hab)}">${pct(q.pct_hab)}</b> en vez de ${pct(p.costo / p.neto * 100)}${sube ? '' : ': el último porcionamiento salió más barato que lo habitual'}.</div></div>
        <div class="fp-mueve-acc"><button type="button" class="fp-btn" data-acc="ver-porc" data-cod="${esc(q.cod)}">Ver los porcionamientos</button>
        ${q.P ? `<button type="button" class="fp-btn" data-acc="simular-hab">Simular con ${dinero(q.hab)}</button>` : ''}</div></div>`);
    }
    return out.join('');
  }

  function htmlReceta(d, st) {
    const p = d.plato;
    if (!d.filas.length) return htmlDescarga(d);
    const vis = visibles(d.filas, st.abiertos);
    const total = d.filas.filter((f) => f[R.par] === -1).reduce((s, f) => s + f[R.costo], 0) || 1;
    const marcadas = new Set(st.marcadas || []);
    const filas = vis.map((f) => {
      const abre = f[R.nh] > 0, abierta = st.abiertos.has(f[R.id]);
      const tit = f[R.fbase] ? `Receta base guardada el ${fecha(f[R.fbase])}` : f[R.ficha] === 'P' ? 'Corte porcionado: ver sus porcionamientos' : f[R.nom];
      const sel = st.sel === f[R.id] || marcadas.has(f[R.id]);
      return `<button type="button" class="fp-fila${sel ? ' sel' : ''}${f[R.niv] ? '' : ' arriba'}" data-acc="linea" data-id="${f[R.id]}" title="${esc(tit)}"${abre ? ` aria-expanded="${abierta}"` : ''}>
        <span class="fp-nom" style="padding-left:${f[R.niv] * 14}px"><span class="fp-car">${abre ? (abierta ? '▾' : '▸') : ''}</span>${f[R.ficha] ? `<span class="fp-chip ${f[R.ficha]}">${f[R.ficha]}</span>` : ''}<em>${esc(f[R.nom])}</em></span>
        <span class="num gris der">${cant(f[R.cant])} ${esc(f[R.unid])}</span>
        <span class="num der">${f[R.costo] >= 0.01 ? f2(f[R.costo]) : '< 0.01'}</span>
        <span class="fp-barra"><i style="width:${Math.max(0.6, f[R.costo] / total * 100).toFixed(1)}%"></i></span></button>`;
    }).join('');
    const c = cifras(d);
    return `<div class="fp-rec"><div class="fp-rec-cab"><span class="fp-rot">Receta · por 1 plato</span>
        <span class="fp-tabs chico"><button type="button" data-acc="abrir-todo">Abrir todo</button><button type="button" data-acc="plegar">Plegar</button></span></div>
      <div class="fp-fila enc"><span>Línea</span><span class="der">Cantidad</span><span class="der">Costo</span><span>del plato</span></div>
      <div class="fp-lineas">${filas}</div>
      <div class="fp-fila tot"><span>Total por plato</span><span></span><span class="num der">${dinero(p.costo)}</span><span class="num gris">${pct(c.pctHoy)}</span></div>
      <p class="fp-pie">Un clic en una receta base (Rs) la abre en su lugar; en un corte porcionado (P), lleva a sus porcionamientos.</p></div>`;
  }

  function htmlDescarga(d) {
    const p = d.plato;
    let cuerpo;
    if (p.tipo === 'Directo') {
      cuerpo = `<p>Se descarga <b>directo</b> del almacén: <b>${esc(p.descarga || '(sin nombre)')}</b>. Su costo es el del artículo.</p>`
        + (p.sin_costo ? '<p class="fp-nota ambar">El artículo no tiene costo en el POS: la venta de este producto entra al FoodCost en cero.</p>' : '');
    } else if (p.tipo === 'Combo' && p.combo) {
      const b = p.combo.banda.map(([n, v]) => `<tr><td>${n}</td><td class="num der">${dinero(v)}</td></tr>`).join('');
      cuerpo = `<p><b>Combo ${esc(p.combo.tipo.toLowerCase())}</b> · ${esc(p.combo.metodo || 'sin método')}</p>
        <table class="fp-tabla"><tbody>${b}</tbody></table>
        <p class="fp-pie">El POS no costea los combos: la banda la calcula la consulta del Sheet (regla #548).</p>`;
    } else if (p.tipo === 'No aplica') {
      cuerpo = '<p>Su descargo está en <b>«No aplica»</b>: el POS no descarga nada del almacén al venderlo, así que no tiene costo.</p>';
    } else {
      cuerpo = '<p><b>Sin enlace</b>: no está enlazado a una receta ni a un artículo, así que el POS no descarga nada al venderlo y no tiene costo.</p>';
    }
    return `<div class="fp-rec"><div class="fp-rec-cab"><span class="fp-rot">Qué descarga del almacén</span></div>${cuerpo}</div>`;
  }

  // Evolución: barras = platos vendidos; línea = costo por plato al vender.
  function htmlEvo(d, st, W) {
    if (!d.meses.length) {
      return '<p class="fp-nota">No se vendió desde que hay ventas en la app: no hay costo al vender que mostrar.</p>';
    }
    const H = 230, X0 = 44, BASE = H - 22, ALTO = BASE - 30;
    const ms = d.meses, n = ms.length, paso = (W - X0 - 4) / n;
    const T = tope([...ms.map((m) => m[M.cu]), d.plato.sin_costo ? null : d.plato.costo]);
    const yC = (v) => BASE - v / T * ALTO;
    const maxU = Math.max(1, ...ms.map((m) => m[M.u]));
    const xm = (i) => X0 + i * paso + paso / 2;
    const ix = new Map(ms.map((m, i) => [m[M.mes], i]));
    const enRango = (m) => d.rango && m >= d.rango[0].slice(0, 7) && m <= d.rango[1].slice(0, 7);
    const r0 = ms.findIndex((m) => enRango(m[M.mes])), r1 = ms.length - 1 - [...ms].reverse().findIndex((m) => enRango(m[M.mes]));
    const svg = [];
    const pasoT = T / 4;
    for (let v = pasoT; v <= T + 1e-9; v += pasoT) {
      svg.push(`<line x1="${X0}" x2="${W}" y1="${yC(v).toFixed(1)}" y2="${yC(v).toFixed(1)}" class="g"/>`
        + `<text x="0" y="${(yC(v) + 4).toFixed(1)}" class="t">S/ ${Math.round(v)}</text>`);
    }
    if (r0 >= 0) svg.push(`<rect x="${(X0 + r0 * paso).toFixed(1)}" y="0" width="${(paso * (r1 - r0 + 1)).toFixed(1)}" height="${BASE}" class="rango" rx="4"/>`);
    const cada = Math.max(1, Math.ceil(n / Math.max(4, Math.floor(W / 64))));
    ms.forEach((m, i) => {
      const h = m[M.u] / maxU * 64, cls = m[M.mes] === st.mes ? 'b sel' : enRango(m[M.mes]) ? 'b ran' : 'b';
      svg.push(`<rect x="${(X0 + i * paso + paso * 0.18).toFixed(1)}" y="${(BASE - h).toFixed(1)}" width="${(paso * 0.64).toFixed(1)}" height="${h.toFixed(1)}" class="${cls}" rx="2"/>`);
      if (i % cada === 0) svg.push(`<text x="${xm(i).toFixed(1)}" y="${H - 6}" class="t c">${etqMes(m[M.mes])}</text>`);
    });
    if (!d.plato.sin_costo && d.plato.costo > 0) {
      svg.push(`<line x1="${X0}" x2="${W}" y1="${yC(d.plato.costo).toFixed(1)}" y2="${yC(d.plato.costo).toFixed(1)}" class="hoy"/>`
        + `<text x="${X0 + 4}" y="${(yC(d.plato.costo) - 5).toFixed(1)}" class="t">hoy ${dinero(d.plato.costo)}</text>`);
    }
    // La línea, cortada donde un mes no tiene costo.
    let tramo = [];
    const tramos = [];
    ms.forEach((m, i) => {
      if (m[M.cu] == null) { if (tramo.length) tramos.push(tramo); tramo = []; return; }
      tramo.push(`${xm(i).toFixed(1)},${yC(m[M.cu]).toFixed(1)}`);
    });
    if (tramo.length) tramos.push(tramo);
    tramos.forEach((t) => svg.push(`<polyline points="${t.join(' ')}" class="linea"/>`));
    ms.forEach((m, i) => {
      if (m[M.cu] != null) svg.push(`<circle cx="${xm(i).toFixed(1)}" cy="${yC(m[M.cu]).toFixed(1)}" r="${m[M.mes] === st.mes ? 4.5 : 2.5}" class="${m[M.sin] > 0 ? 'pt sin' : 'pt'}${m[M.mes] === st.mes ? ' sel' : ''}"/>`);
    });
    d.picos.forEach((p) => {
      const i = ix.get(p.ini.slice(0, 7));
      if (i != null && ms[i][M.cu] != null) svg.push(`<circle cx="${xm(i).toFixed(1)}" cy="${yC(ms[i][M.cu]).toFixed(1)}" r="8" class="pico"/>`);
    });
    const arriba = (lista, y, cls, s) => {
      const meses = new Set(lista.map((k) => (k.t || k.ini).slice(0, 7)));
      meses.forEach((m) => { if (ix.has(m)) svg.push(`<text x="${xm(ix.get(m)).toFixed(1)}" y="${y}" class="${cls}">${s}</text>`); });
    };
    arriba(d.marcas, 11, 'mk', '▼');
    arriba(d.cambios, 23, 'ca', '◆');
    const golpes = ms.map((m, i) => `<button type="button" class="fp-mes" data-acc="mes" data-id="${m[M.mes]}" style="left:${(X0 + i * paso).toFixed(1)}px;width:${paso.toFixed(1)}px" aria-label="${etqMes(m[M.mes])}: ${cant(m[M.u])} vendidos${m[M.cu] != null ? `, ${dinero(m[M.cu])} por plato` : ''}" title="${etqMes(m[M.mes])}: ${cant(m[M.u])} vendidos${m[M.cu] != null ? ` · ${dinero(m[M.cu])}` : ''}"></button>`).join('');

    const i = ix.has(st.mes) ? ix.get(st.mes) : n - 1, mm = ms[i];
    let ant = null;
    for (let j = i - 1; j >= 0; j--) if (ms[j][M.cu] != null) { ant = ms[j]; break; }
    const dv = ant && mm[M.cu] != null ? (mm[M.cu] / ant[M.cu] - 1) * 100 : null;
    const cosas = delMes(d, mm[M.mes]);
    if (!cosas.length) cosas.push({ s: '·', c: 'gris', t: 'Ninguna edición de sus recetas base, cambio de la auditoría ni pico este mes: lo que se mueve es el precio de compra y el de los porcionamientos.' });
    const c = cifras(d), pie = [];
    if (c.tramo) pie.push(`De ${dinero(c.tramo.a)} (${etqMes(c.tramo.ma)}) a ${dinero(c.tramo.b)} (${etqMes(c.tramo.mb)}): ${signo(c.tramo.var)}, el costo que guardó el POS al vender.`);
    if (r0 >= 0) pie.push('Sombreado: el rango de la tarjeta.');
    if (d.plato.tipo === 'Combo' && ms.some((m) => m[M.mes] < d.combo_antes)) pie.push('Hasta setiembre de 2025 el POS registró los platos de los combos entre 8 y 32 % más baratos que sueltos.');
    if (d.faltan.length) pie.push(`Sin ${d.faltan.join(' ni ')}: todavía no están en R2. Se agregan en el Sheet.`);
    return `<div class="fp-ley"><span><i class="l-linea"></i> costo por plato al vender (la foto del POS)</span><span><i class="l-hoy"></i> costo de hoy</span>
        <span><i class="l-barra"></i> platos vendidos</span><span class="mk">▼ edición de una receta base</span><span class="ca">◆ cambio en la auditoría</span><span class="pk">◯ pico</span></div>
      <div class="fp-graf" style="height:${H}px"><svg width="${W}" height="${H}" aria-hidden="true">${svg.join('')}</svg>${golpes}</div>
      <div class="fp-det"><div><b>${NOMBRE_MES[+mm[M.mes].slice(5) - 1]} ${mm[M.mes].slice(0, 4)}</b>
        <div class="num">${cant(mm[M.u])} platos vendidos</div>
        <div class="num">${mm[M.cu] != null ? `${dinero(mm[M.cu])} por plato al vender` : 'vendido sin costo'}</div>
        ${mm[M.pct] != null ? `<div class="num">al ${pct(mm[M.pct])} de costo</div>` : ''}
        ${dv != null ? `<div class="num ${dv > 5 ? 'rojo' : dv < -5 ? 'verde' : 'gris'}">${signo(dv)} contra ${etqMes(ant[M.mes])}</div>` : ''}</div>
        <ul class="fp-lista">${cosas.map((k) => `<li><span class="${k.c}">${k.s}</span><span>${esc(k.t)}</span></li>`).join('')}</ul></div>
      <p class="fp-pie">Un clic en un mes lo explica debajo del gráfico. ${esc(pie.join(' '))}</p>`;
  }

  // Costo y utilidad: el plato a precio de carta contra lo cobrado por plato.
  // `conObjetivos` agrega el «Para quedar en»; el Resumen lo tiene aparte.
  function htmlUtil(d, { conObjetivos = true } = {}) {
    const p = d.plato, c = cifras(d);
    if (p.sin_costo || !(p.costo > 0)) {
      return '<p class="fp-nota">Sin costo cargado: no hay cómo repartir el precio entre costo y utilidad.</p>';
    }
    const barras = [{ t: 'La carta, con el costo de hoy', sub: `precio ${dinero(p.precio)} · neto ${dinero(p.neto)}`, bruto: p.precio, costo: p.costo, neto: p.neto }];
    if (c.vnetoU && c.vcostoU) {
      barras.push({ t: `Lo vendido, por plato (${fecha(d.rango[0])} – ${fecha(d.rango[1])})`,
        sub: `${cant(p.vend)} platos · neto ${dinero(c.vnetoU)} por plato`, bruto: c.vnetoU * d.divisor, costo: c.vcostoU, neto: c.vnetoU });
    }
    const escala = Math.max(...barras.map((b) => b.bruto)) || 1;
    const html = barras.map((b) => {
      const m = Math.max(0, b.neto - b.costo), cc = Math.min(b.costo, b.neto);
      return `<div class="fp-util"><div class="fp-util-cab"><b>${esc(b.t)}</b><span class="num gris">${esc(b.sub)}</span></div>
        <div class="fp-util-barra" style="width:${(b.bruto / escala * 100).toFixed(1)}%">
          <div class="i" style="width:${((b.bruto - b.neto) / b.bruto * 100).toFixed(1)}%"><span class="num">${dinero(b.bruto - b.neto)}</span></div>
          <div class="c" style="width:${(cc / b.bruto * 100).toFixed(1)}%"><span class="num">${dinero(b.costo)} · ${pct(b.costo / b.neto * 100)}</span></div>
          <div class="m" style="width:${(m / b.bruto * 100).toFixed(1)}%"><span class="num">${dinero(b.neto - b.costo)}</span></div></div></div>`;
    }).join('');
    let nota = '';
    if (c.vnetoU && c.vcostoU) {
      const dif = p.neto - c.vnetoU;
      nota = `<div class="fp-nota">Lo vendido salió en promedio a <b class="num">${dinero(c.vnetoU)}</b> neto por plato, ${dinero(Math.abs(dif))} ${dif >= 0 ? 'por debajo' : 'por encima'} del neto de carta (descuentos y precios de otros canales, por ejemplo). Y el costo al vender, <b class="num">${dinero(c.vcostoU)}</b>, es la foto que guardó el POS en cada pedido, no el de hoy.</div>`;
    }
    let obj = '';
    if (conObjetivos) {
      const o = c.objetivos.map((x) => `<div class="fp-kpi"><span>${x.u} % de costo</span><b class="num">${dinero(x.precio)}</b><span class="num">o bajar el costo a ${dinero(x.costo)}</span></div>`);
      if (d.q && d.q.pct_hab != null) {
        o.push(`<div class="fp-kpi"><span>Con ${esc(corto(d.q.nombre))} a lo habitual</span><b class="num ${nivel(d, d.q.pct_hab)}">${pct(d.q.pct_hab)}</b><span class="num">a ${dinero(p.precio)}, sin tocar el precio</span></div>`);
      }
      obj = `<span class="fp-rot">Para quedar en</span><div class="fp-obj">${o.join('')}</div>`;
    }
    return `${html}<div class="fp-ley"><span><i class="l-imp"></i> impuestos y recargo</span><span><i class="l-costo"></i> costo</span><span><i class="l-margen"></i> margen</span></div>
      ${nota}${obj}`;
  }

  // Reparto del precio: cada línea → costo; costo y margen → neto.
  function htmlRep(d, st, W) {
    const p = d.plato;
    if (!d.filas.length) return '<p class="fp-nota">Sin receta no hay reparto: se reparte el costo entre las líneas de la receta.</p>';
    if (p.sin_costo || !(p.costo > 0)) return '<p class="fp-nota">Sin costo cargado: no hay cómo repartir el precio.</p>';
    const nodos = reparto(d.filas), margen = Math.max(0, p.neto - p.costo);
    const H = 300, GAP = 8, AN = Math.min(220, Math.max(130, W * 0.36)), XL = AN + 4;
    const XN = W - 96, XM = XL + (XN - XL) * 0.55;
    const util = H - 20 - GAP * (nodos.length - 1);
    const K = util / Math.max(p.neto, p.costo);
    const banda = (x0, a0, b0, x1, a1, b1) => {
      const c = (x0 + x1) / 2;
      return `M${x0},${a0} C${c},${a0} ${c},${a1} ${x1},${a1} L${x1},${b1} C${c},${b1} ${c},${b0} ${x0},${b0} Z`;
    };
    const marcadas = new Set(st.marcadas || []);
    const svg = [], botones = [];
    let y = 10;
    const hc = p.costo * K, hm = margen * K;
    const yc = 10 + (H - 20 - hc - hm - 14) / 2;
    let yd = yc;
    nodos.forEach((nd) => {
      const alto = Math.max(2, nd.v * K), caja = Math.max(alto, 18), on = nd.id >= 0 ? st.sel === nd.id : (nd.ids || []).some((i) => marcadas.has(i));
      svg.push(`<path d="${banda(XL, y, y + alto, XM, yd, yd + nd.v * K)}" class="bd${on ? ' on' : ''}"/>`);
      botones.push(`<button type="button" class="fp-nodo${on ? ' on' : ''}" data-acc="nodo" data-id="${nd.id}" style="top:${y}px;height:${caja}px;width:${AN}px" title="${esc(nd.n)}: ${dinero(nd.v)}"><span>${esc(nd.n)}</span><span class="num gris fp-nodo-v">${dinero(nd.v)}</span></button>`);
      y += caja + GAP; yd += nd.v * K;
    });
    const ym = yc + hc + 14, yn = yc + 7;
    svg.push(`<path d="${banda(XM + 10, yc, yc + hc, XN, yn, yn + hc)}" class="bc"/>`);
    if (hm > 0) svg.push(`<path d="${banda(XM + 10, ym, ym + hm, XN, yn + hc, yn + hc + hm)}" class="bm"/>`);
    svg.push(`<rect x="${XM}" y="${yc}" width="10" height="${hc}" class="nc"/>`);
    if (hm > 0) svg.push(`<rect x="${XM}" y="${ym}" width="10" height="${hm}" class="nm"/>`);
    svg.push(`<rect x="${XN}" y="${yn}" width="10" height="${hc + hm}" class="nn"/>`);
    const rot = (x, yy, t, s, cls = '') => `<div class="fp-sk-rot num ${cls}" style="left:${x}px;top:${yy}px"><b>${t}</b><br>${s}</div>`;
    return `<div class="fp-graf" style="height:${H}px"><svg width="${W}" height="${H}" role="img" aria-label="Reparto del precio neto entre las líneas de la receta, el costo y el margen">${svg.join('')}</svg>
        ${botones.join('')}${rot(XM + 16, yc + hc / 2 - 16, 'Costo', `${dinero(p.costo)} · ${pct(p.costo / p.neto * 100)}`)}
        ${hm > 0 ? rot(XM + 16, ym + hm / 2 - 16, 'Margen', `${dinero(margen)} · ${pct(margen / p.neto * 100)}`) : ''}
        ${rot(XN + 14, yn + (hc + hm) / 2 - 16, 'Neto', dinero(p.neto))}</div>
      <p class="fp-pie">Cada banda es lo que esa línea le cuesta al plato. Un clic en una la marca en la receta.${nodos.some((n) => n.id < 0) ? ' Las más chicas van juntas.' : ''}${margen <= 0 ? ' El costo de hoy pasa el precio neto: no queda margen.' : ''}</p>`;
  }

  function htmlPorc(d, st) {
    const cods = Object.keys(d.cortes);
    if (!cods.length) return '<p class="fp-nota">Ninguna línea del plato sale de un porcionamiento.</p>';
    const cod = cods.includes(st.corte) ? st.corte : cods[0], c = d.cortes[cod];
    const chips = cods.map((k) => `<button type="button" class="fp-chipc${k === cod ? ' on' : ''}" data-acc="corte" data-id="${esc(k)}" title="${esc(d.cortes[k].n)}">${esc(corto(d.cortes[k].n))}</button>`).join('');
    const maxC = Math.max(...c.filas.map((r) => r[7]), 0.01);
    const ultCls = c.ult.raro || (c.hab && Math.abs(c.filas[0][7] / c.hab.costo - 1) >= 0.1) ? 'ult' : '';
    const filas = c.filas.map((r, i) => `<tr class="${i === 0 ? ultCls : ''}"><td class="num">${fecha(r[0])}</td><td>${esc(r[1])}</td>
        <td class="num der">${cant(r[2])} ${esc(String(r[3]).toLowerCase())}</td><td class="num der">${cant(r[4])} ${esc(String(r[5]).toLowerCase())}</td>
        <td class="num der ${r[6] > 30 ? 'ambar' : ''}">${r[6].toFixed(1)} %</td><td class="num der fuerte">${dinero(r[7])}</td>
        <td><span class="fp-barra ancha"><i class="${i === 0 && ultCls ? 'ult' : ''}" style="width:${(r[7] / maxC * 100).toFixed(1)}%"></i></span></td></tr>`).join('');
    const u = c.filas[0], unidad = esc(c.u.toLowerCase());
    const igual = Math.abs(c.unit - u[7]) <= Math.max(0.01, 0.01 * u[7]);
    let nota = igual
      ? `La receta le pone ${dinero(c.unit)} por ${unidad}: el precio del último porcionamiento (${fecha(u[0])}), hecho desde ${esc(u[1])}.`
      : `La receta le pone ${dinero(c.unit)} por ${unidad}, el promedio del almacén; el último porcionamiento (${fecha(u[0])}) dio ${dinero(u[7])}.`;
    if (c.hab) nota += ` Los ${c.hab.n} porcionamientos de los 30 días anteriores dieron ${dinero(c.hab.costo)} por ${unidad}, ponderados por lo que salió.`;
    if (c.ult.raro) nota += ` Ese porcionamiento le asignó ${cant(c.ult.kgu)} por unidad y lo habitual es ${cant(c.ult.hab)}: su costo, y el de esta receta, pueden estar mal.`;
    const bot = [];
    if (c.ult.cod_de) bot.push(`<button type="button" class="fp-btn" data-acc="rend" data-id="${esc(cod)}">Ver la curva en Producción › Rendimiento</button>`);
    if (c.ult.raro && c.ult.reciente) bot.push(`<button type="button" class="fp-btn" data-acc="rev" data-id="${esc(cod)}">Abrir PO-${esc(c.ult.doc)} en Para revisar</button>`);
    return `<div class="fp-cortes"><span class="fp-rot">Cortes del plato</span>${chips}</div>
      <div class="fp-scroll"><table class="fp-tabla po"><thead><tr><th>Fecha</th><th>Desde</th><th class="der">Porcionado</th><th class="der">Salieron</th><th class="der">Merma</th><th class="der">Costo por ${unidad}</th><th></th></tr></thead><tbody>${filas}</tbody></table></div>
      <div class="fp-nota">${nota}</div>${bot.length ? `<div class="fp-acc">${bot.join('')}</div>` : ''}`;
  }

  // ── El estado de la ficha y lo que hace un clic ─────────────────────────
  // `rec` es la forma de la pestaña Receta: lista, reparto o porcionados.
  function estadoInicial(d) {
    const conCosto = d.meses.filter((m) => m[M.cu] != null);
    const ult = (conCosto.length ? conCosto : d.meses).slice(-1)[0];
    return { cod: d.plato.cod, rec: 'lista', abiertos: new Set(), sel: null, marcadas: [], mes: ult ? ult[M.mes] : null,
      corte: d.q ? d.q.cod : Object.keys(d.cortes)[0] || null };
  }

  // Un clic dentro de lo que dibuja este módulo. Devuelve {enviar: [trigger,
  // valor]} para Python, 'receta' para pasar a esa pestaña, true para
  // redibujar o null si el clic no era suyo.
  function accion(st, d, acc, id, b) {
    const n = Date.now(), cod = d.plato.cod;
    if (acc === 'simular-hab' && d.q) return { enviar: ['simular', { cod, estado: { [d.q.ruta]: { P: d.q.P } }, n }] };
    if (acc === 'nuevo') return { enviar: ['nuevo_costeo', { cod, n }] };
    if (acc === 'rend' || acc === 'rev') return { enviar: ['produccion', { destino: acc, cod: id, n }] };
    if (acc === 'rec') st.rec = id;
    else if (acc === 'mes') st.mes = id;
    else if (acc === 'corte') st.corte = id;
    else if (acc === 'ver-porc') { st.rec = 'porc'; st.corte = b.dataset.cod; if (d.q) st.sel = d.q.id; return 'receta'; }
    else if (acc === 'abrir-todo') st.abiertos = new Set(d.filas.filter((f) => f[R.nh] > 0).map((f) => f[R.id]));
    else if (acc === 'plegar') st.abiertos = new Set();
    else if (acc === 'nodo') {
      const nd = reparto(d.filas).find((x) => String(x.id) === id);
      st.sel = nd && nd.id >= 0 ? (st.sel === nd.id ? null : nd.id) : null;
      st.marcadas = nd && nd.id < 0 ? ((st.marcadas || []).length ? [] : nd.ids) : [];
    } else if (acc === 'linea') {
      const f = d.filas[+id];
      st.marcadas = [];
      if (f[R.nh] > 0) {
        const a = new Set(st.abiertos);
        if (a.has(f[R.id])) a.delete(f[R.id]); else a.add(f[R.id]);
        st.abiertos = a; st.sel = f[R.id];
      } else if (f[R.ficha] === 'P' && d.cortes[f[R.cod]]) { st.sel = f[R.id]; st.rec = 'porc'; st.corte = f[R.cod]; }
      else st.sel = st.sel === f[R.id] ? null : f[R.id];
    } else return null;
    return true;
  }

  return { R, M, corto, cifras, visibles, reparto, tope, delMes, picoDelRango, lineas, nivel,
    htmlAvisos, htmlReceta, htmlDescarga, htmlEvo, htmlUtil, htmlRep, htmlPorc, estadoInicial, accion };
})();

if (typeof window !== 'undefined') window.FichaPlato = FichaPlato;
