// Ventas › el filtro «Venta» de cada tarjeta (regla #755).
//
// Un módulo, no una pieza: graficos/ventas_alcance.py::js lo antepone al .js
// de cada pieza de Ventas que lo usa (Venta por Periodo, Mix de carta), y
// cada una lo dibuja en SU tarjeta. Lo que se elige en una no toca a las
// otras. Python manda en `A` (`ventas_alcance.datos`): los `bloques`
// ([[Carta|Eventos|Otros, [grupos]]]), los `subs` de cada grupo (si la
// pieza los tiene), los `atajos` ([[nombre, lista | null]]) y con cuál
// `abre` la tarjeta.
//
// Una ELECCIÓN es `null` —toda la venta— o un objeto {grupo: true |
// [subgrupos]}: el grupo entero o sólo esos subgrupos. Marcado = se cuenta.
// `normalizar` la deja en su forma única: un grupo con todos sus subgrupos
// es `true`, y con todos los grupos enteros es `null`.
window.VentasAlcance = (function () {
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const sinTilde = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

  function grupos(A) { return A.bloques.flatMap((b) => b[1]); }
  function subsDe(A, g) { return (A.subs && A.subs[g]) || []; }

  function desdeLista(lista) {
    if (lista == null) return null;
    const s = {};
    for (const [g, sub] of lista) {
      if (sub == null) s[g] = true;
      else if (s[g] !== true) (s[g] = s[g] || []).push(sub);
    }
    return s;
  }
  function normalizar(A, sel) {
    if (!sel) return null;
    const out = {};
    for (const g of grupos(A)) {
      const v = sel[g];
      if (!v) continue;
      const subs = subsDe(A, g);
      if (v === true || (subs.length && subs.every((x) => v.includes(x)))) out[g] = true;
      else {
        const w = subs.filter((x) => v.includes(x));
        if (w.length) out[g] = w;
      }
    }
    return grupos(A).every((g) => out[g] === true) ? null : out;
  }
  const firma = (sel) => (sel ? JSON.stringify(Object.keys(sel).sort().map((g) => [g, sel[g]])) : 'toda');
  const igual = (a, b) => firma(a) === firma(b);
  function atajo(A, nombre) { const a = A.atajos.find((x) => x[0] === nombre); return a ? normalizar(A, desdeLista(a[1])) : null; }
  function inicio(A) { return atajo(A, A.abre); }

  // ¿Esta línea se cuenta? Sin subgrupo (una pieza que no los tiene), sólo
  // pasa con el grupo entero.
  function pasa(sel, grupo, sub) {
    if (!sel) return true;
    const v = sel[grupo];
    return v === true || (Array.isArray(v) && v.includes(sub));
  }
  // Los grupos que se cuentan, para una pieza que filtra sólo por grupo.
  // `[]` es todo; nada elegido devuelve un grupo que no existe.
  function listaGrupos(A, sel) {
    if (!sel) return [];
    const gs = Object.keys(sel).filter((g) => sel[g] === true);
    return gs.length ? gs : ['\u0000ninguno'];
  }

  function nombreAtajo(A, sel) {
    const at = A.atajos.find((x) => x[0] === A.abre && igual(atajo(A, x[0]), sel))
      || A.atajos.find((x) => igual(atajo(A, x[0]), sel));
    return at ? at[0] : null;
  }
  // Otro rango trae otros grupos: una elección que era un atajo sigue siendo
  // ese atajo (un grupo nuevo de la carta entra en «Carta + Eventos»); una
  // hecha a mano conserva lo que todavía existe.
  function reubicar(viejo, nuevo, sel) {
    const n = viejo ? nombreAtajo(viejo, sel) : null;
    return n ? atajo(nuevo, n) : normalizar(nuevo, sel);
  }
  function etiqueta(A, sel) {
    if (!sel) return 'toda';
    const n = nombreAtajo(A, sel);
    if (n) return n;
    const gs = Object.keys(sel);
    if (!gs.length) return 'nada';
    if (gs.length === 1) {
      const v = sel[gs[0]];
      return v === true ? gs[0] : (v.length === 1 ? `${gs[0]} › ${v[0]}` : `${gs[0]} › ${v.length} subgrupos`);
    }
    return `${gs.length} grupos`;
  }

  // 'on' | 'mid' | 'off' de un grupo, un subgrupo o un bloque.
  function estadoGrupo(sel, g) { if (!sel) return 'on'; const v = sel[g]; return v === true ? 'on' : v ? 'mid' : 'off'; }
  function estadoSub(sel, g, s) { return pasa(sel, g, s) ? 'on' : 'off'; }
  function estadoBloque(sel, gs) {
    const e = gs.map((g) => estadoGrupo(sel, g));
    return e.every((x) => x === 'on') ? 'on' : e.every((x) => x === 'off') ? 'off' : 'mid';
  }
  const todoEntero = (A) => Object.fromEntries(grupos(A).map((g) => [g, true]));

  // ── El dibujo ───────────────────────────────────────────────────────────
  const caja = (e) => `<span class="va-k ${e}" aria-hidden="true">${e === 'on' ? '✓' : e === 'mid' ? '–' : ''}</span>`;
  const aria = (e) => (e === 'on' ? 'true' : e === 'mid' ? 'mixed' : 'false');
  function filaGrupo(A, sel, ui, g, nivel, rotulo) {
    const subs = subsDe(A, g), abierto = ui.exp.has(g), e = estadoGrupo(sel, g);
    let h = `<div class="va-f n${nivel}"><button type="button" role="checkbox" aria-checked="${aria(e)}" class="va-c" data-va="grupo" data-g="${esc(g)}">${caja(e)}<span>${esc(rotulo || g)}</span></button>`
      + (subs.length ? `<button type="button" class="va-ab" data-va="abrir" data-g="${esc(g)}" aria-expanded="${abierto}" aria-label="${abierto ? 'Cerrar' : 'Ver'} los subgrupos de ${esc(g)}">${subs.length} ${abierto ? '▾' : '▸'}</button>` : '') + '</div>';
    if (abierto) for (const s of subs) h += filaSub(sel, g, s, nivel + 1);
    return h;
  }
  function filaSub(sel, g, s, nivel, conGrupo) {
    const e = estadoSub(sel, g, s);
    return `<div class="va-f n${nivel}"><button type="button" role="checkbox" aria-checked="${aria(e)}" class="va-c" data-va="sub" data-g="${esc(g)}" data-s="${esc(s)}">${caja(e)}<span>${esc(s)}${conGrupo ? ` <small>${esc(g)}</small>` : ''}</span></button></div>`;
  }
  function lista(A, sel, ui) {
    const q = sinTilde(ui.q).trim();
    let h = '';
    if (q) {
      for (const g of grupos(A)) {
        if (sinTilde(g).includes(q)) h += filaGrupo(A, sel, ui, g, 0);
        for (const s of subsDe(A, g)) if (sinTilde(s).includes(q)) h += filaSub(sel, g, s, 0, true);
      }
      return h || '<div class="va-vacio">Nada con ese nombre.</div>';
    }
    for (const [b, gs] of A.bloques) {
      // Un bloque de un solo grupo con su mismo nombre (Eventos) es una fila.
      if (gs.length === 1 && sinTilde(gs[0]) === sinTilde(b)) { h += `<div class="va-bl">${filaGrupo(A, sel, ui, gs[0], 0)}</div>`; continue; }
      const e = estadoBloque(sel, gs);
      h += `<div class="va-bl"><div class="va-f n0"><button type="button" role="checkbox" aria-checked="${aria(e)}" class="va-c" data-va="bloque" data-b="${esc(b)}">${caja(e)}<span>${esc(b)}</span></button><span class="va-n">${gs.length} grupos</span></div>`
        + gs.map((g) => filaGrupo(A, sel, ui, g, 1)).join('') + '</div>';
    }
    return h;
  }
  function html(A, sel, ui, rot = 'Venta') {
    const ini = inicio(A), distinto = !igual(sel, ini);
    let h = `<div class="va${ui.abierto ? ' abierto' : ''}"><button type="button" class="va-b${distinto ? ' on' : ''}" data-va="toggle" aria-expanded="${ui.abierto}">${esc(rot)}: ${esc(etiqueta(A, sel))} <i aria-hidden="true">▾</i></button>`;
    if (distinto) h += `<button type="button" class="va-x" data-va="inicio" title="Volver a ${esc(A.abre)}" aria-label="Volver a ${esc(A.abre)}">✕</button>`;
    if (ui.abierto) {
      h += '<div class="va-p" role="dialog" aria-label="Qué venta contar"><div class="va-at">'
        + A.atajos.map(([n]) => `<button type="button" class="${igual(atajo(A, n), sel) ? 'on' : ''}" data-va="atajo" data-n="${esc(n)}">${esc(n)}${n === A.abre ? ' · al abrir' : ''}</button>`).join('')
        + `</div><input class="va-q" data-va="q" value="${esc(ui.q)}" placeholder="${Object.keys(A.subs || {}).length ? 'Buscar grupo o subgrupo' : 'Buscar grupo'}" aria-label="Buscar" autocomplete="off">`
        + `<div class="va-l">${lista(A, sel, ui)}</div>`
        + '<div class="va-pie"><span>Sólo cambia esta tarjeta · marcado = se cuenta</span><button type="button" class="va-ok" data-va="cerrar">Listo</button></div></div>';
    }
    return h + '</div>';
  }

  // ── Un clic: devuelve la elección nueva (o la misma) ────────────────────
  function accion(A, sel, ui, el) {
    const op = el.dataset.va, g = el.dataset.g;
    const base = () => (sel ? JSON.parse(JSON.stringify(sel)) : todoEntero(A));
    if (op === 'toggle') { ui.abierto = !ui.abierto; return sel; }
    if (op === 'cerrar') { ui.abierto = false; ui.q = ''; return sel; }
    if (op === 'inicio') { ui.abierto = false; ui.q = ''; return inicio(A); }
    if (op === 'abrir') { if (ui.exp.has(g)) ui.exp.delete(g); else ui.exp.add(g); return sel; }
    if (op === 'atajo') return atajo(A, el.dataset.n);
    const s = base();
    if (op === 'bloque') {
      const gs = (A.bloques.find((b) => b[0] === el.dataset.b) || [null, []])[1];
      const prender = estadoBloque(sel, gs) !== 'on';
      for (const x of gs) { if (prender) s[x] = true; else delete s[x]; }
    } else if (op === 'grupo') {
      if (estadoGrupo(sel, g) === 'on') delete s[g]; else s[g] = true;
    } else if (op === 'sub') {
      const sub = el.dataset.s, todos = subsDe(A, g), v = s[g];
      if (v === true) s[g] = todos.filter((x) => x !== sub);
      else if (Array.isArray(v) && v.includes(sub)) s[g] = v.filter((x) => x !== sub);
      else s[g] = (Array.isArray(v) ? v : []).concat(sub);
      if (Array.isArray(s[g]) && !s[g].length) delete s[g];
    } else return sel;
    return normalizar(A, s);
  }
  function nuevaUi() { return { abierto: false, exp: new Set(), q: '' }; }

  return { desdeLista, normalizar, igual, atajo, inicio, reubicar, pasa, listaGrupos, etiqueta, html, lista, accion, nuevaUi };
})();
