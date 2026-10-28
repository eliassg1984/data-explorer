// La presentación se aplica a los nodos reales, conservando sus eventos y
// el estado del reporte. Cada componente tiene su propio shadow root.
const __movilMedia = '(max-width: 900px)';
const __movilPerfiles = [
  ['.re', ''], ['.cv', '.cv-controles'], ['.cd', '.cd-der'],
  ['.cpvr', ''], ['.cpvf', '.cc'], ['.cpr', '.ctl'], ['.cpf', '.cc'],
  ['.sv', '.cab .campo, .filtros'], ['.cvol', '.cv-toolbar'], ['.vap', '.vap-controles'], ['.dc', '.dc-filtros'], ['.sud', '.sud-controles'],
  ['.vp', '.fils, .vp-ctrl'], ['.vm', '.vm-ctrl'], ['.ig', '.ig-filtro'], ['.vh', '.ctrl'],
  ['.vcc', '.vcc-controls'], ['.msp', '.ms-toolbar'], ['.ctl', '.ctl-filtros'],
  ['.isp', '.isp-toolbar'], ['.iar', '.iar-controles'], ['.imv', '.imv-controls'],
  ['.ajc', '.ajc-filters'], ['.adf', '.adf-controls'], ['.apv', '.apv-controles'], ['.ev', '.chips'],
  ['.mv', '.mv-filtros'], ['.rqa', '.rqa-controles'], ['.saa', '.rqa-controles'], ['.destino', '.dst-control'],
  ['.pvu', '.pvu-filtros'], ['.mre', '.mre-controles'], ['.mrv', '.mrv-filtros'],
  ['.cc', '.cc-filtros'], ['.rb', '.cab .sel'], ['.cr', '.filtros'], ['.rr', '.rr-per'],
  ['.sa', '.sa-esc'], ['.nc', ''], ['.sim', ''], ['.pd', '.pd-der'], ['.consumo-pieza', '.ctrls'],
  ['.pf', ''], ['.pa', ''], ['.ps', ''], ['.ld', '']
];
const __movilRaices = __movilPerfiles.map(([raiz]) => raiz).join(', ');

function __movilAdaptar(parent) {
  if (!parent) return;
  if (parent.__movilAdaptacion) return parent.__movilAdaptacion.desmontar;
  const media = window.matchMedia(__movilMedia), abiertos = new Map();
  let pendiente = false;
  const contexto = (nodo) => {
    const textos = [...nodo.querySelectorAll('select')].flatMap((e) => [...e.selectedOptions].map((o) => o.textContent.trim()));
    nodo.querySelectorAll('input[type="search"], input[type="text"]').forEach((e) => { if (e.value.trim()) textos.push(e.value.trim()); });
    return [...new Set(textos)].filter((s) => s && !/^(todos?|todas?)(\b|$)/i.test(s)).slice(0, 3).join(' · ');
  };
  const restaurar = () => {
    parent.querySelectorAll('.rpt-movil-kpis').forEach((d) => d.replaceWith(...d.querySelector('.rpt-kpis-mas').childNodes));
    parent.querySelectorAll('.rpt-movil-panel').forEach((d) => {
      const grupo = d.querySelector('.rpt-movil-filtros');
      if (grupo) { grupo.classList.remove('rpt-movil-filtros'); d.replaceWith(grupo); }
    });
    parent.querySelectorAll('.rpt-tabla-scroll[data-movil-wrap], .rpt-graf-scroll[data-movil-wrap]').forEach((n) => n.replaceWith(...n.childNodes));
    parent.querySelectorAll('.rpt-tabla-scroll').forEach((n) => n.classList.remove('rpt-tabla-scroll'));
    parent.querySelectorAll('.rpt-tabla-ancha').forEach((n) => n.classList.remove('rpt-tabla-ancha'));
    parent.querySelectorAll('.rpt-movil').forEach((n) => n.classList.remove('rpt-movil'));
    parent.querySelectorAll('.rpt-movil-lectura').forEach((n) => n.remove());
  };
  const aplicar = () => {
    pendiente = false;
    observador.disconnect();
    if (!media.matches) restaurar();
    else __movilPerfiles.forEach(([raiz, filtros]) => {
      parent.querySelectorAll(raiz).forEach((root, ri) => {
        // Clases cortas como .cv o .ctl también nombran celdas y controles
        // de otras piezas. Sólo adaptar la raíz exterior del reporte.
        const anterior = root.parentElement?.closest(__movilRaices);
        if (anterior && parent.contains(anterior)) return;
        root.classList.add('rpt-movil');
        if (filtros) root.querySelectorAll(filtros).forEach((grupo, gi) => {
          const existente = grupo.closest('.rpt-movil-panel');
          if (existente) {
            const sum = existente.querySelector('summary'), ctx = contexto(grupo);
            let small = sum.querySelector('small');
            if (ctx && !small) { small = document.createElement('small'); sum.appendChild(small); }
            if (small) { small.textContent = ctx; small.hidden = !ctx; }
            return;
          }
          if (grupo.closest('.rpt-movil-lectura')) return;
          const clave = `${raiz}:${ri}:${gi}`, panel = document.createElement('details'), sum = document.createElement('summary');
          panel.className = 'rpt-movil-panel';
          sum.textContent = 'Filtros y opciones';
          const ctx = contexto(grupo);
          if (ctx) { const s = document.createElement('small'); s.textContent = ctx; sum.appendChild(s); }
          const foco = root.getRootNode().activeElement, conservar = foco && grupo.contains(foco);
          panel.open = abiertos.get(clave) || conservar || false;
          panel.addEventListener('toggle', () => abiertos.set(clave, panel.open));
          grupo.before(panel); panel.append(sum, grupo); grupo.classList.add('rpt-movil-filtros');
          if (conservar) foco.focus({ preventScroll: true });
        });
        if (raiz === '.vp') root.querySelectorAll('.kpis').forEach((grupo, gi) => {
          if (grupo.querySelector('.rpt-movil-kpis')) return;
          const cifras = [...grupo.children];
          if (cifras.length <= 4) return;
          const panel = document.createElement('details'), sum = document.createElement('summary'), mas = document.createElement('div');
          const clave = `kpis:${ri}:${gi}`;
          panel.className = 'rpt-movil-kpis'; mas.className = 'rpt-kpis-mas';
          sum.textContent = `Más indicadores · ${cifras.length - 4}`;
          panel.open = abiertos.get(clave) || false;
          panel.addEventListener('toggle', () => abiertos.set(clave, panel.open));
          mas.append(...cifras.slice(4)); panel.append(sum, mas); grupo.appendChild(panel);
        });
        root.querySelectorAll('table').forEach((tabla) => {
          if (tabla.closest('.rpt-tabla-scroll')) return;
          const cols = [...(tabla.rows[0]?.cells || [])].reduce((n, c) => n + c.colSpan, 0);
          const padre = tabla.parentElement, estilo = getComputedStyle(padre);
          if (['auto', 'scroll'].includes(estilo.overflowX)) {
            padre.classList.add('rpt-tabla-scroll');
          } else {
            const wrap = document.createElement('div'); wrap.className = 'rpt-tabla-scroll'; wrap.dataset.movilWrap = '';
            tabla.before(wrap); wrap.appendChild(tabla);
          }
          if (cols > 4) tabla.classList.add('rpt-tabla-ancha');
        });
        root.querySelectorAll('svg').forEach((svg) => {
          if (svg.closest('.rpt-graf-scroll') || svg.closest('button') || svg.closest('.rpt-movil-lectura')) return;
          const ancho = Number(svg.getAttribute('width'));
          if (ancho > root.clientWidth + 2) {
            const wrap = document.createElement('div'); wrap.className = 'rpt-graf-scroll'; wrap.dataset.movilWrap = '';
            svg.before(wrap); wrap.appendChild(svg);
          }
        });
      });
    });
    observador.observe(parent, { childList: true, subtree: true });
  };
  const programar = (cambios) => {
    if (Array.isArray(cambios) && cambios.every((r) => r.target.nodeType === 1 && r.target.closest('svg, .tip, .tooltip, .mv-tip, .cv-tip, [role="tooltip"]'))) return;
    if (pendiente) return;
    pendiente = true; queueMicrotask(aplicar);
  };
  const observador = new MutationObserver(programar);
  media.addEventListener('change', programar);
  const desmontar = () => {
    observador.disconnect(); media.removeEventListener('change', programar);
    delete parent.__movilAdaptacion;
  };
  parent.__movilAdaptacion = { aplicar, observador, desmontar };
  aplicar();
  return desmontar;
}
