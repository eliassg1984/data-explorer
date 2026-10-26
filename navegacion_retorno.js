// Protocolo compartido por la página y los shadow roots v2. Sin datos del
// reporte: sólo controles, identificadores de foco y posición. TTL de 2 h.
(function () {
  const w = window.parent, d = w.document;
  const anterior = w.__retorno;
  anterior?.desenlazar?.();
  const prefijo = 'app_retorno_', ttl = 7200000;
  const permitida = /^(cc_est$|costos_|cd_|pd_|rec_|vt_|ventas_|cp_|compras_|mov_|stock_|ajuste_|sin_plato_|destino_|sunat_|consumo_)/;
  const estado = anterior?._estado || { pendiente: null, restaurando: null, montados: new WeakMap() };
  // El iframe de inyección se sustituye al rerunear. Chrome retira sus
  // listeners del documento padre: se enlazan de nuevo y se conserva el viaje.
  const oyentes = [];
  function escuchar(tipo, fn, opciones) {
    d.addEventListener(tipo, fn, opciones); oyentes.push([tipo, fn, opciones]);
  }
  const esc = x => w.CSS.escape(String(x));
  const almacen = nombre => { try { return w[nombre]; } catch { return null; } };
  function todos(root) {
    const es = [...root.querySelectorAll('*')];
    return es.flatMap(e => e.shadowRoot ? [e, ...todos(e.shadowRoot)] : [e]);
  }
  function selector(e) {
    const root = e.getRootNode();
    const unico = s => { try { return root.querySelectorAll(s).length === 1; } catch { return false; } };
    const key = [...e.classList].find(c => c.startsWith('st-key-'));
    if (key && unico('.' + esc(key))) return '.' + esc(key);
    const ats = [...e.attributes].filter(a => /^data-(acc|a|id|cod|k|key|v|periodo|doc|tabla|zona|fila|retorno-clave)$/.test(a.name));
    const attr = e.localName + ats.map(a => '[' + a.name + '="' + esc(a.value) + '"]').join('');
    if (ats.length && unico(attr)) return attr;
    const clases = [...e.classList].filter(c => !/^st-|^css-|^emotion-|^on$|^sel|^active/.test(c));
    for (const c of clases) if (unico('.' + esc(c))) return '.' + esc(c);
    const partes = [];
    for (let n = e; n?.nodeType === 1; n = n.parentElement) {
      const k = [...n.classList].find(c => c.startsWith('st-key-'));
      if (k) { partes.unshift('.' + esc(k)); break; }
      if (n !== e) {
        const ids = [...n.attributes].filter(a => /^data-(acc|a|id|cod|k|key|v|periodo|doc|tabla|zona|fila|retorno-clave)$/.test(a.name));
        const ancla = n.localName + ids.map(a => '[' + a.name + '="' + esc(a.value) + '"]').join('');
        if (ids.length && unico(ancla)) { partes.unshift(ancla); break; }
      }
      const hermanos = n.parentElement ? [...n.parentElement.children].filter(x => x.localName === n.localName) : [];
      partes.unshift(n.localName + (hermanos.length > 1 ? ':nth-of-type(' + (hermanos.indexOf(n) + 1) + ')' : ''));
    }
    return partes.join(' > ');
  }
  function ruta(e) {
    const r = [];
    while (e?.nodeType === 1) {
      r.unshift(selector(e));
      e = e.getRootNode().host;
    }
    return r;
  }
  function buscar(r) {
    let root = d, e;
    try { for (const s of r) { e = root?.querySelector(s); root = e?.shadowRoot; } } catch { return null; }
    return e;
  }
  function copiar(v, nivel = 0) {
    if (nivel > 8 || v === undefined || typeof v === 'function' || v?.nodeType) return undefined;
    if (v === null || ['string', 'number', 'boolean'].includes(typeof v)) return v;
    if (v instanceof w.Set) return { __tipoRetorno: 'set', v: [...v].map(x => copiar(x, nivel + 1)) };
    if (v instanceof w.Map) return { __tipoRetorno: 'map', v: [...v].map(x => copiar(x, nivel + 1)) };
    if (Array.isArray(v)) return v.length < 1000 ? v.map(x => copiar(x, nivel + 1)) : undefined;
    if (Object.getPrototypeOf(v) !== w.Object.prototype && Object.getPrototypeOf(v) !== Object.prototype) return undefined;
    return Object.fromEntries(Object.entries(v).filter(([k]) => !['todo', 'data', 'datos', 'origen', 'boton'].includes(k))
      .map(([k, x]) => [k, copiar(x, nivel + 1)]).filter(([, x]) => x !== undefined));
  }
  function revivir(v) {
    if (!v || typeof v !== 'object') return v;
    if (v.__tipoRetorno === 'set') return new w.Set(v.v.map(revivir));
    if (v.__tipoRetorno === 'map') return new w.Map(v.v.map(revivir));
    return Array.isArray(v) ? v.map(revivir) : Object.fromEntries(Object.entries(v).map(([k, x]) => [k, revivir(x)]));
  }
  function almacenamiento(s) {
    try { return Object.fromEntries(Object.keys(s).filter(k => permitida.test(k)).map(k => [k, s.getItem(k)])); }
    catch { return {}; }
  }
  function capturar(foco) {
    const es = todos(d).filter(e => !e.closest('.st-key-retorno_contextual'));
    return {
      creado: Date.now(),
      local: almacenamiento(almacen('localStorage')), sesion: almacenamiento(almacen('sessionStorage')),
      scroll: es.filter(e => e.scrollHeight > e.clientHeight + 2 || e.scrollWidth > e.clientWidth + 2)
        .filter(e => e === d.scrollingElement || /auto|scroll/.test(w.getComputedStyle(e).overflow + w.getComputedStyle(e).overflowY))
        .map(e => ({ r: ruta(e), x: e.scrollLeft, y: e.scrollTop })),
      abiertos: es.filter(e => e.localName === 'details').map(e => ({ r: ruta(e), abierto: e.open })),
      piezas: es.filter(e => e.__d?.st || e.__st).map(e => ({ r: ruta(e), st: copiar(e.__d?.st || e.__st) })),
      foco: foco ? ruta(foco) : null,
    };
  }
  function guardar(id, snap, compartido = false) {
    if (!snap) return;
    try {
      const s = almacen(compartido ? 'localStorage' : 'sessionStorage');
      for (const k of Object.keys(s).filter(k => k.startsWith(prefijo))) {
        try { if (Date.now() - JSON.parse(s.getItem(k)).creado > ttl) s.removeItem(k); } catch { s.removeItem(k); }
      }
      const keys = Object.keys(s).filter(k => k.startsWith(prefijo));
      while (keys.length >= 24) s.removeItem(keys.shift());
      s.setItem(prefijo + id, JSON.stringify(snap));
    } catch { /* El servidor conserva el contexto aunque el navegador no permita guardarlo. */ }
    estado.memoria ||= new Map(); estado.memoria.set(id, snap);
    if (estado.memoria.size > 24) estado.memoria.delete(estado.memoria.keys().next().value);
  }
  function leer(id) {
    try {
      const s = estado.memoria?.get(id) || JSON.parse(almacen('sessionStorage')?.getItem(prefijo + id) || almacen('localStorage')?.getItem(prefijo + id) || 'null');
      return s && Date.now() - s.creado <= ttl ? s : null;
    } catch { return estado.memoria?.get(id); }
  }
  function restaurar(id) {
    const snap = leer(id);
    if (!snap) return;
    for (const [s, valores] of [[almacen('localStorage'), snap.local], [almacen('sessionStorage'), snap.sesion]]) {
      try {
        for (const k of Object.keys(s).filter(k => permitida.test(k))) if (!(k in valores)) s.removeItem(k);
        for (const [k, v] of Object.entries(valores)) if (permitida.test(k)) s.setItem(k, v);
      } catch { /* modo privado o cuota agotada */ }
    }
    estado.restaurando = { id, snap, hasta: Date.now() + 60000, visto: false };
    // Da tiempo a que Streamlit retire el destino: no restaura sobre su DOM.
    w.__railSalto = Date.now() + 61000;
  }
  function montar(c, render) {
    let resultado = render(c);
    const vuelta = estado.restaurando;
    if (!vuelta || Date.now() > vuelta.hasta || estado.montados.get(c.parentElement) === vuelta.id) return resultado;
    let cambio = false;
    for (const p of vuelta.snap.piezas) {
      const e = buscar(p.r);
      if (!e || !c.parentElement.contains(e)) continue;
      const st = e.__d?.st || e.__st;
      if (st) { Object.assign(st, revivir(p.st)); cambio = true; }
    }
    if (cambio) {
      if (typeof resultado === 'function') resultado();
      resultado = render(c);
      estado.montados.set(c.parentElement, vuelta.id);
    }
    return resultado;
  }
  function posicionar() {
    const v = estado.restaurando;
    if (!v?.visto || Date.now() > v.hasta) return;
    let falta = false;
    for (const p of v.snap.abiertos) {
      const e = buscar(p.r); if (e && e.open !== p.abierto) e.open = p.abierto;
    }
    for (const p of v.snap.scroll) {
      const e = buscar(p.r);
      if (!e) { falta = true; continue; }
      e.scrollLeft = p.x; e.scrollTop = p.y;
      if (Math.abs(e.scrollTop - p.y) > 2 && p.y > 0) {
        falta = true; e.dispatchEvent(new w.Event('scroll'));
      }
    }
    const foco = v.snap.foco && buscar(v.snap.foco);
    const firma = v.snap.scroll.map(p => { const e = buscar(p.r); return e && [e.scrollHeight, e.scrollWidth, e.scrollTop, e.scrollLeft].join(':'); }).join('|');
    const completo = !falta && (foco || !v.snap.foco);
    v.estables = completo && v.ultimoFoco === foco && v.firma === firma ? (v.estables || 0) + 1 : 0;
    v.ultimoFoco = foco; v.firma = firma;
    // Una tanda puede reemplazar las filas en el evento scroll pendiente.
    // Espera al DOM estable antes de marcar y dar por terminada la vuelta.
    if (v.estables >= 3 && foco) {
      foco.style.setProperty('outline', '2px solid #9078ba');
      foco.style.setProperty('outline-offset', '-2px');
      if (!foco.hasAttribute('tabindex')) foco.tabIndex = -1;
      foco.focus({ preventScroll: true });
      w.setTimeout(() => { foco.style.removeProperty('outline'); foco.style.removeProperty('outline-offset'); }, 2500);
    }
    if (v.estables >= 3) { estado.restaurando = null; w.__railSalto = Date.now() + 500; }
  }
  function ceder() {
    if (estado.restaurando) { estado.restaurando = null; w.__railSalto = Date.now(); }
  }
  escuchar('click', ev => {
    const path = ev.composedPath(), el = path.find(x => x?.matches?.('button,a,[role="button"]'));
    if (!el || path.some(x => x?.classList?.contains('st-key-retorno_contextual'))) return;
    ceder();
    const salto = el.matches('a[href],[data-acc="carta"],[data-acc="cambios"],[data-acc="ir"],[data-retorno-salto]')
      || el.closest('.st-key-rec_carta_base_curva,.st-key-rec_carta_base_revisar');
    if (!salto) return;
    const celda = path.find(x => x?.matches?.('td,th,[role="gridcell"]')) || el;
    estado.pendiente = capturar(celda);
    // Las selecciones locales del clic se completan antes de preparar el salto.
    w.queueMicrotask(() => {
      if (estado.pendiente) {
        estado.pendiente.local = almacenamiento(almacen('localStorage'));
        estado.pendiente.sesion = almacenamiento(almacen('sessionStorage'));
      }
    });
    if (el.matches('a') && el.href) {
      const u = new w.URL(el.href, w.location.href);
      if (u.origin === w.location.origin && u.searchParams.has('reporte')) {
        const token = u.searchParams.get('retorno') || estado.enlace;
        if (/^[a-f0-9]{32}$/.test(token || '')) {
          u.searchParams.set('retorno', token); el.href = u.href;
          guardar(token, estado.pendiente, true);
        }
      }
    }
  }, true);
  // Clic central y «Abrir enlace en otra pestaña» también reciben origen.
  for (const evento of ['pointerdown', 'contextmenu']) escuchar(evento, ev => {
    const el = ev.composedPath().find(x => x?.matches?.('a[href]'));
    if (!el) return;
    const u = new w.URL(el.href, w.location.href);
    if (u.origin !== w.location.origin || !u.searchParams.has('reporte')) return;
    const token = u.searchParams.get('retorno') || estado.enlace;
    if (!/^[a-f0-9]{32}$/.test(token || '')) return;
    u.searchParams.set('retorno', token); el.href = u.href;
    guardar(token, capturar(el.closest('td,th') || el), true);
  }, true);
  // Un gesto del usuario termina la reposición para que nunca luche con él.
  for (const evento of ['wheel', 'touchstart', 'keydown']) escuchar(evento, ceder, { capture: true, passive: true });
  const reloj = w.setInterval(posicionar, 150);
  w.__retorno = {
    montar, restaurar, capturar, leer, _estado: estado,
    desenlazar() { for (const [tipo, fn, opciones] of oyentes) d.removeEventListener(tipo, fn, opciones); w.clearInterval(reloj); },
    configurar({ comando, activo, enlace }) {
      if (activo !== undefined) d.documentElement.toggleAttribute('data-retorno', activo);
      if (enlace) estado.enlace = enlace;
      if (comando?.accion === 'guardar') guardar(comando.id, estado.pendiente);
      if (comando?.accion === 'restaurar') {
        if (estado.restaurando?.id !== comando.id) restaurar(comando.id);
        if (estado.restaurando) estado.restaurando.visto = true;
      }
    },
  };
})();
