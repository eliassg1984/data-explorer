// La ficha del filtro de familias de una vista de Compras (regla #843).
//
// El filtro de Familia y Subfamilia es de la VISTA y lo aplica Python
// (`graficos/compras/_filtros_vista.py`): recorta el rango, el histórico, las
// notas de crédito, el punto del rail y lo que ve el asistente. Este módulo
// sólo lo MUESTRA y lo EDITA dentro de la pieza: una ficha lavanda con su ✕ al
// lado de «Más filtros» cuando hay filtro, y el panel de casillas.
//
// Se antepone a la pieza, como `_xlsx.js`, y deja un solo nombre: `FichaFam`.
// No toca el DOM ni manda nada: arma HTML y hace cuentas; los clics los pone la
// pieza. Las acciones que dibuja (`data-acc`): ffam-menu, ffam-fam, ffam-sub,
// ffam-sublimpiar, ffam-aplicar, ffam-quitar, ffam-entrada y ffam-todas.
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
  // «5 de 8 familias», «Familia: Alimentos», «… · 2 subfamilias».
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

  function listaSub(P, pend, q) {
    const sel = new Set(pend.sub), k = plano(q || '');
    const ops = subsDe(P, pend.fam).filter((x) => !k || plano(nom(x)).includes(k));
    return ops.map((x) => `<label><input type="checkbox" data-acc="ffam-sub" data-v="${esc(x)}"${sel.has(x) ? ' checked' : ''}><span>${esc(nom(x))}</span></label>`).join('')
      || '<p class="ff-nada">Sin coincidencias.</p>';
  }
  // El panel: Familia con lo que suma cada una, Subfamilia y el pie. `o`:
  // pend (lo que se está marcando), q (lo buscado), fmt (cómo escribir un
  // monto) y volver (el panel abrió desde «Más filtros»).
  function panel(P, o) {
    const pend = o.pend || aplicado(P), sel = new Set(pend.fam), v = valor(P, pend), fmt = o.fmt || String;
    const subs = subsDe(P, pend.fam), nSub = pend.sub.length, pendiente = !igual(v, vigente(P)), ent = deEntrada(P);
    const atajos = (activo(P, ent) && !igual(v, ent) ? `<button class="ff-at" data-acc="ffam-entrada" title="${esc(P.entrada.map(nom).join(', '))}">Las de siempre</button>` : '')
      + (activo(P, v) ? '<button class="ff-at" data-acc="ffam-todas">Todas</button>' : '');
    return '<div class="ff-l" role="dialog" aria-label="Familia y subfamilia de esta vista">'
      + (o.volver ? '<button class="ff-at ff-volver" data-acc="menu" data-v="fil">‹ Más filtros</button>' : '')
      + `<h4><span>Familia</span><span class="ff-ats">${atajos}</span></h4>`
      + `<div class="ff-o ff-fams">${P.todas.map(([f, x]) => `<label><input type="checkbox" data-acc="ffam-fam" data-v="${esc(f)}"${sel.has(f) ? ' checked' : ''}><span>${esc(nom(f))}</span><small>${esc(fmt(x))}</small></label>`).join('')}</div>`
      + (subs.length ? `<h4><span>Subfamilia<small> · ${nSub || 'todas'}</small></span><span class="ff-ats">${nSub ? '<button class="ff-at" data-acc="ffam-sublimpiar">Quitar</button>' : ''}</span></h4>`
        + (subs.length > 8 ? `<input class="ff-q" data-k="ffsub" placeholder="Buscar subfamilia…" aria-label="Buscar subfamilia" value="${esc(o.q || '')}" autocomplete="off">` : '')
        + `<div class="ff-o ff-subs" data-k="ffsub">${listaSub(P, pend, o.q)}</div>` : '')
      + `<div class="ff-pie"><span>${pendiente ? 'Se aplica al cerrar' : 'Sólo esta vista'}</span>${pendiente ? '<button class="ff-ap" data-acc="ffam-aplicar">Aplicar</button>' : ''}</div></div>`;
  }
  // La ficha, y debajo su panel. Sin filtro no dibuja nada: ahí el panel abre
  // desde «Más filtros» (`entrada`). `o.envio` es lo pedido a Python que
  // todavía no volvió: la ficha lo dice apagada, sin botones.
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
  // El renglón de «Más filtros» que abre el panel cuando no hay ficha.
  const entrada = () => '<div class="ff-en"><button class="ff-ir" data-acc="ffam-menu" aria-haspopup="dialog"><span>Familia y subfamilia</span><small>Todas ›</small></button></div>';

  return { nom, subsDe, aplicado, valor, vigente, sinFiltro, deEntrada, activo, cambio, distinto, rotulo,
    iniciar, alternarFam, alternarSub, listaSub, panel, ficha, entrada };
})();
window.__cpFichaFam = FichaFam;
