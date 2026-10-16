// La fila de KPI de las tarjetas «por período» de Movimientos (regla #649).
//
// La monta graficos/movimientos_periodo.py::_tarjeta con st.components.v2,
// SIN shadow root (isolate_styles=False): el HTML es el mismo que arma
// `_html_kpi` y lo siguen estilando las reglas de `_CSS_MOLDE`, que cuelgan
// de `.st-key-<c>_kpi`. Esta pieza sólo agrega el clic.
//
// Python manda en `data.html` la fila entera. Los tramos que se pueden
// resaltar son `<button data-res="<tramo>" aria-pressed>`. A Python le llega
// una sola cosa, el trigger «resaltar»: {nombre: <tramo> | null, t}. Un clic
// en el resaltado lo suelta (null). El botón cambia de estado acá mismo, sin
// esperar la corrida: el cuadrito y el fondo los pinta el CSS según
// `aria-pressed`.

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  let raiz = parentElement.querySelector('.mp-kpi-raiz');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'mp-kpi-raiz';
    parentElement.appendChild(raiz);
    raiz.addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-res]');
      if (!b || !raiz.contains(b)) return;
      const soltar = b.getAttribute('aria-pressed') === 'true';
      for (const x of raiz.querySelectorAll('[data-res]')) x.setAttribute('aria-pressed', 'false');
      if (!soltar) b.setAttribute('aria-pressed', 'true');
      // Un sello por aviso: dos clics iguales seguidos son dos avisos.
      raiz.__enviar({ nombre: soltar ? null : b.dataset.res, t: Date.now() });
    });
  }
  raiz.__enviar = (v) => setTriggerValue('resaltar', v);
  // Sólo se reescribe si cambió: cada corrida vuelve a llamar esta función,
  // y rehacer el DOM igual le borraría el foco del teclado al botón.
  const html = (data && data.html) || '';
  if (raiz.__html !== html) {
    raiz.innerHTML = html;
    raiz.__html = html;
  }
}
