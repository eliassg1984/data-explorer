// Ventas › «Análisis de platos»: lo que comparten sus dos piezas (regla #767).
//
// El corte, «Comparar» y las pestañas son UNA fila en el ranking y en la
// Ingeniería de menú, así que cada pieza los dibuja con esto, que
// graficos/ventas_platos.py y ventas_menu.py anteponen a su `.js`. Python
// manda `data.cromo` ({vista, cortes, corte, periodos, elegidos, max}) y lo que
// cambia los datos vuelve por el trigger `cromo`: {corte}, {elegidos} o {vista}.
// Los meses esperan 1,2 s antes de pedir, como el panel de fecha (#616): elegir
// tres meses recalcula una vez, no tres.

const CLAVE_PL = 'vt_pl_est';
const escPl = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function leerPl(def) { try { const v = localStorage.getItem(CLAVE_PL); return v ? JSON.parse(v) : def; } catch (_) { return def; } }
function guardarPl(extra) { try { localStorage.setItem(CLAVE_PL, JSON.stringify(Object.assign(leerPl({}), extra))); } catch (_) { /* sin almacenamiento */ } }

function textoElegidos(lista) {
  const anios = lista.map((e) => (/^\S+ \d{2}$/.test(e) ? e.split(' ')[1] : null));
  if (lista.length > 1 && anios[0] && anios.every((a) => a === anios[0])) return `${lista.map((e) => e.split(' ')[0]).join(' · ')} ${anios[0]}`;
  return lista.join(' · ');
}
function htmlCromo(c, st) {
  if (!c) return '';
  const meses = st.menu === 'comparar' ? `<div class="pl-pop pl-meses">${c.periodos.map((e) => `<button type="button" class="${st.elegidos.includes(e) ? 'on' : ''}" aria-pressed="${st.elegidos.includes(e)}" data-acc="mes" data-id="${escPl(e)}">${escPl(e)}</button>`).join('')}<span>Hasta ${c.max}, y no tienen que ser seguidos.${c.vista === 'Ranking' ? '' : ' La Ingeniería clasifica el último.'}</span></div>` : '';
  return `<div class="pl-seg" role="group" aria-label="Corte">${c.cortes.map((x) => `<button type="button" class="${x === c.corte ? 'on' : ''}" data-acc="corte" data-id="${escPl(x)}">${escPl(x)}</button>`).join('')}</div>
    <div class="pl-m"><button type="button" class="pl-mb on" aria-expanded="${st.menu === 'comparar'}" data-acc="menu" data-id="comparar">Comparar: ${escPl(textoElegidos(st.elegidos))} <i>▾</i></button>${meses}</div>`;
}
function htmlPestanas(actual) {
  return `<div class="pl-tabs" role="tablist" aria-label="Qué se ve">${[['Tabla', 'Tabla'], ['Puestos', 'Puestos'], ['Menu', 'Ingeniería de menú']].map(([id, t]) => `<button type="button" role="tab" aria-selected="${actual === id}" class="${actual === id ? 'on' : ''}" data-acc="tab" data-id="${id}">${t}</button>`).join('')}</div>`;
}
function pedirCromo(raiz, valor) {
  raiz.classList.add('cargando');
  raiz.__d.enviar('cromo', Object.assign(valor, { n: Date.now() }));
}
function soltarMeses(raiz) {
  const D = raiz.__d;
  if (!D.esperaMes) return;
  clearTimeout(D.esperaMes);
  D.esperaMes = null;
  pedirCromo(raiz, { elegidos: D.st.elegidos.slice() });
}
// `true` si la acción era de acá. `pintar` redibuja la fila de controles.
function accionCromo(raiz, acc, id, pintar) {
  const D = raiz.__d, st = D.st, c = D.data.cromo;
  if (acc === 'menu') {
    st.menu = st.menu === id ? null : id;
    pintar();
    if (!st.menu) soltarMeses(raiz);
    return true;
  }
  if (acc === 'corte') {
    if (id !== c.corte) { st.menu = null; pedirCromo(raiz, { corte: id }); }
    return true;
  }
  if (acc === 'mes') {
    const orden = c.periodos, hay = st.elegidos.includes(id);
    const nueva = (hay ? st.elegidos.filter((x) => x !== id) : st.elegidos.concat([id]))
      .sort((a, b) => orden.indexOf(a) - orden.indexOf(b)).slice(-c.max);
    if (!nueva.length) return true;
    st.elegidos = nueva;
    pintar();
    clearTimeout(D.esperaMes);
    D.esperaMes = setTimeout(() => soltarMeses(raiz), 1200);
    return true;
  }
  return false;
}
// Lo que llega de Python manda, salvo unos meses que todavía no se pidieron.
function recibirCromo(raiz, data) {
  const D = raiz.__d;
  raiz.classList.remove('cargando');
  if (!data.cromo) { D.st.elegidos = D.st.elegidos || []; return; }
  if (!D.esperaMes) D.st.elegidos = data.cromo.elegidos.slice();
}
