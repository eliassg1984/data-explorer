// La ficha del filtro de familias de una vista de Compras (reglas #843 y #844).
//
// El filtro de Familia y Subfamilia es de la VISTA y lo aplica Python
// (`graficos/compras/_filtros_vista.py`): recorta el rango, el histórico, las
// notas de crédito, el punto del rail y lo que ve el asistente. Este módulo
// sólo lo MUESTRA y lo EDITA dentro de la pieza, como el boceto
// https://claude.ai/artifact/2EZyYV79UzT13MBJ1Kxnca: una ficha lavanda con su
// ✕ al lado de «Más filtros» cuando hay filtro; su panel, con las familias y
// lo que suma cada una y el campo de Subfamilia; y los dos campos, Familia y
// Subfamilia, que la pieza pone dentro de «Más filtros».
//
// Se antepone a la pieza, como `_xlsx.js`, y deja un solo nombre: `FichaFam`.
// No toca el DOM ni manda nada: arma HTML y hace cuentas; los clics los pone la
// pieza. Las acciones que dibuja (`data-acc`): ffam-menu, ffam-fam, ffam-sub,
// ffam-sublimpiar, ffam-aplicar, ffam-quitar, ffam-entrada, ffam-todas y
// `campo` con `data-v="ffsub"` (abrir o plegar el campo de Subfamilia).
//
// `P` es `familias` del mensaje de Python (`_filtros_vista.datos_ficha`):
//   todas     [[familia, lo que suma en el rango], …]: todas las de la página
//   elegidas  lo aplicado; vacío quiere decir todas
//   subs      { mapa: { familia: [subfamilia, …] }, elegidas: […] }
//   entrada   las familias con que abre la vista («Las de siempre»)
// Una selección es `{ fam: […], sub: […] }`. Mientras se edita, `fam` lleva
// las familias marcadas una por una; lo que viaja a Python (`valor`) lleva
// `fam: []` cuando están todas y no hay subfamilias: sin filtro no hay ficha.
const FichaFam = (() => {
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const plano = (s) => String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const nom = (f) => { const x = String(f).toLowerCase(); return x.charAt(0).toUpperCase() + x.slice(1); };
  const todas = (P) => P.todas.map((x) => x[0]);
  const enOrden = (P, xs) => { const s = new Set(xs); return todas(P).filter((f) => s.has(f)); };
  const igual = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  // Las subfamilias que se pueden elegir: las de las familias marcadas.
  function subsDe(P, fams) {
    const s = new Set(), m = (P.subs && P.subs.mapa) || {};
    fams.forEach((f) => (m[f] || []).forEach((x) => s.add(x)));
    return [...s].sort();
  }
  // Lo aplicado, con las familias una por una.
  function aplicado(P) {
    return { fam: P.elegidas && P.elegidas.length ? enOrden(P, P.elegidas) : todas(P),
      sub: ((P.subs && P.subs.elegidas) || []).slice().sort() };
  }
  // Lo que viaja a Python, siempre escrito igual: las familias en el orden de
  // la lista y las subfamilias que siguen disponibles, ordenadas.
  function valor(P, s) {
    const fam = enOrden(P, s.fam), disp = new Set(subsDe(P, fam)), sub = s.sub.filter((x) => disp.has(x)).sort();
    return { fam: fam.length === P.todas.length && !sub.length ? [] : fam, sub };
  }
  const sinFiltro = () => ({ fam: [], sub: [] });
  const deEntrada = (P) => valor(P, { fam: P.entrada && P.entrada.length ? P.entrada : todas(P), sub: [] });
  const vigente = (P) => valor(P, aplicado(P));
  const activo = (P, v) => { const x = v || vigente(P); return (x.fam.length > 0 && x.fam.length < P.todas.length) || x.sub.length > 0; };
  // Lo que cambia si se aplica `pend`; null si queda igual.
  function cambio(P, pend) { const v = valor(P, pend); return igual(v, vigente(P)) ? null : v; }
  const distinto = (P, v) => !igual(valor(P, { fam: v.fam.length ? v.fam : todas(P), sub: v.sub }), vigente(P));
  // Lo que dice cada campo: «5 de 8 familias», «Todas las subfamilias»…
  function rotuloFam(P, s) {
    const n = valor(P, s || aplicado(P)).fam.length;
    return !n || n === P.todas.length ? 'Todas las familias' : n === 1 ? nom(valor(P, s || aplicado(P)).fam[0]) : `${n} de ${P.todas.length} familias`;
  }
  function rotuloSub(P, s) {
    const x = valor(P, s || aplicado(P)).sub;
    return !x.length ? 'Todas las subfamilias' : x.length === 1 ? nom(x[0]) : `${x.length} subfamilias`;
  }
  // Lo que dice la ficha: «5 de 8 familias», «Familia: Alimentos», «… · 2 subfamilias».
  function rotulo(P, v) {
    const x = v || vigente(P), n = x.fam.length, p = [];
    if (n > 0 && n < P.todas.length) p.push(n === 1 ? `Familia: ${nom(x.fam[0])}` : `${n} de ${P.todas.length} familias`);
    if (x.sub.length) p.push(x.sub.length === 1 ? `Subfamilia: ${nom(x.sub[0])}` : `${x.sub.length} subfamilias`);
    return p.join(' · ');
  }

  const iniciar = (P) => aplicado(P);
  // Marcar o desmarcar una familia. La última no se desmarca: sin ninguna no
  // hay nada que mirar. Las subfamilias de una familia que sale, salen con ella.
  function alternarFam(P, pend, f) {
    const s = new Set(pend.fam);
    if (s.has(f)) { if (s.size === 1) return pend; s.delete(f); } else s.add(f);
    const fam = enOrden(P, [...s]), disp = new Set(subsDe(P, fam));
    return { fam, sub: pend.sub.filter((x) => disp.has(x)) };
  }
  function alternarSub(P, pend, x) {
    const s = new Set(pend.sub);
    if (s.has(x)) s.delete(x); else s.add(x);
    return { fam: pend.fam, sub: [...s].sort() };
  }

  // ── Lo que se dibuja. `o`: pend (lo que se está marcando), q (lo buscado en
  // Subfamilia), fmt (cómo escribir un monto), campo (el campo abierto),
  // abierto (el panel de la ficha) y envio (lo pedido a Python que no volvió).
  function listaFam(P, pend, fmt) {
    const sel = new Set(pend.fam), f = fmt || String;
    return P.todas.map(([k, x]) => `<label><input type="checkbox" data-acc="ffam-fam" data-v="${esc(k)}"${sel.has(k) ? ' checked' : ''}><span>${esc(nom(k))}</span><small>${esc(f(x))}</small></label>`).join('');
  }
  function listaSub(P, pend, q) {
    const sel = new Set(pend.sub), k = plano(q || '');
    const ops = subsDe(P, pend.fam).filter((x) => !k || plano(nom(x)).includes(k));
    return ops.map((x) => `<label><input type="checkbox" data-acc="ffam-sub" data-v="${esc(x)}"${sel.has(x) ? ' checked' : ''}><span>${esc(nom(x))}</span></label>`).join('')
      || '<p class="ff-nada">Sin coincidencias.</p>';
  }
  // «Las de siempre» y «Todas las familias»: sólo las que cambian algo.
  function atajos(P, pend) {
    const v = valor(P, pend), ent = deEntrada(P);
    return (activo(P, ent) && !igual(v, ent) ? `<button class="ff-at" data-acc="ffam-entrada" title="${esc(P.entrada.map(nom).join(', '))}">Las de siempre</button>` : '')
      + (activo(P, v) ? '<button class="ff-at" data-acc="ffam-todas">Todas las familias</button>' : '');
  }
  // Lo que abre el campo Familia de «Más filtros»: la lista y sus atajos.
  function cuerpoFam(P, o) {
    const pend = o.pend || aplicado(P), at = atajos(P, pend);
    return `<div class="ff-o ff-fams">${listaFam(P, pend, o.fmt)}</div>${at ? `<div class="ff-ats">${at}</div>` : ''}`;
  }
  // Lo que abre el campo Subfamilia, en «Más filtros» o en el panel de la ficha.
  function cuerpoSub(P, o) {
    const pend = o.pend || aplicado(P), subs = subsDe(P, pend.fam);
    if (!subs.length) return '<p class="ff-nada">Estas familias no tienen subfamilias.</p>';
    return (subs.length > 8 ? `<input class="ff-q" data-k="ffsub" placeholder="Buscar subfamilia…" aria-label="Buscar subfamilia" value="${esc(o.q || '')}" autocomplete="off">` : '')
      + `<div class="ff-o ff-subs" data-k="ffsub">${listaSub(P, pend, o.q)}</div>`
      + (pend.sub.length ? '<div class="ff-ats"><button class="ff-at" data-acc="ffam-sublimpiar">Todas las subfamilias</button></div>' : '');
  }
  // Un campo: plegado dice lo elegido; un clic lo abre ahí mismo. Lo usa la
  // pieza para los suyos (Proveedor, Producto), para que todos sean iguales.
  function campo(k, rot, txt, abierto, cuerpo) {
    return `<div class="ff-c"><h4>${esc(rot)}</h4><button class="ff-campo" data-acc="campo" data-v="${esc(k)}" aria-expanded="${!!abierto}"><span>${esc(txt)}</span><i aria-hidden="true">▾</i></button>`
      + (abierto ? `<div class="ff-cl">${cuerpo()}</div>` : '') + '</div>';
  }
  // El panel de la ficha: las familias con lo que suma cada una, el campo de
  // Subfamilia y el pie.
  function panel(P, o) {
    const pend = o.pend || aplicado(P), pendiente = !!cambio(P, pend), at = atajos(P, pend);
    return '<div class="ff-l" role="dialog" aria-label="Familia y subfamilia de esta vista">'
      + `<div class="ff-c"><h4>Familia</h4><div class="ff-o ff-fams">${listaFam(P, pend, o.fmt)}</div></div>`
      + campo('ffsub', 'Subfamilia', rotuloSub(P, pend), o.campo === 'ffsub', () => cuerpoSub(P, o))
      + `<div class="ff-pie"><span>${pendiente ? 'Se aplica al cerrar' : 'Sólo esta vista'}</span>${pendiente ? '<button class="ff-ap" data-acc="ffam-aplicar">Aplicar</button>' : `<span class="ff-ats">${at}</span>`}</div></div>`;
  }
  // La ficha, y debajo su panel. Sin filtro no dibuja nada. Mientras Python
  // contesta dice lo pedido, apagada y sin botones.
  function ficha(P, o) {
    const hay = activo(P), v = o.envio || vigente(P);
    let chip = '';
    if (o.envio) chip = `<span class="ff-chip espera" aria-busy="true"><span class="ff-b">${esc(activo(P, v) ? rotulo(P, v) : 'Quitando el filtro')}…</span></span>`;
    else if (hay) {
      chip = `<span class="ff-chip${o.abierto ? ' abierta' : ''}"><button class="ff-b" data-acc="ffam-menu" aria-haspopup="dialog" aria-expanded="${!!o.abierto}" title="${esc([v.fam.length ? v.fam.map(nom).join(', ') : 'Todas las familias', ...(v.sub.length ? [v.sub.map(nom).join(', ')] : [])].join(' · '))}. Un clic abre Familia y Subfamilia.">${esc(rotulo(P, v))}</button>`
        + '<button class="ff-x" data-acc="ffam-quitar" title="Quitar el filtro" aria-label="Quitar el filtro de familias">✕</button></span>';
    }
    return `<div class="ff">${chip}${o.abierto && hay && !o.envio ? panel(P, o) : ''}</div>`;
  }

  return { nom, subsDe, aplicado, valor, vigente, sinFiltro, deEntrada, activo, cambio, distinto, rotulo, rotuloFam, rotuloSub,
    iniciar, alternarFam, alternarSub, listaFam, listaSub, cuerpoFam, cuerpoSub, campo, panel, ficha };
})();
window.__cpFichaFam = FichaFam;
