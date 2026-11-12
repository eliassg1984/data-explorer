// El vocabulario de íconos de las piezas propias (regla #821). Un dibujo, un
// significado, en toda la app: una pieza que necesite «descargar» usa éste y no
// dibuja el suyo. La app se usa a diario, así que una acción puede ser un ícono
// solo, con dos condiciones: el nombre al pasar el cursor (`data-tip`) y el mismo
// nombre para los lectores de pantalla (`aria-label`). El ESTADO —qué pestaña, qué
// fecha, cuánto dio— sigue en texto. Va antepuesto al .js de cada pieza, junto con
// `iconos.css`; ver `graficos/ajuste/_cierre.py`.
const ICONOS={
  filtro:'<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
  lupa:'<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>',
  ambos:'<rect x="3.5" y="5" width="7" height="14" rx="1.5"/><rect x="13.5" y="5" width="7" height="14" rx="1.5"/>',
  una:'<rect x="5" y="5" width="14" height="14" rx="1.5"/><path d="M5 10h14M5 14.5h14"/>',
  tabla:'<rect x="3.5" y="5" width="17" height="14" rx="1.5"/><path d="M3.5 10h17M3.5 14.5h17M9.5 5v14"/>',
  bajar:'<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14"/>',
  mas:'<circle cx="12" cy="6" r="1.4" fill="currentColor"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/><circle cx="12" cy="18" r="1.4" fill="currentColor"/>',
  ampliar:'<path d="M14 4h6v6M20 4l-7 7M10 20H4v-6M4 20l7-7"/>',
  izq:'<path d="M14.5 6l-6 6 6 6"/>',
  der:'<path d="M9.5 6l6 6-6 6"/>',
  caret:'<path d="M7.5 10l4.5 4.5 4.5-4.5"/>',
  chev:'<path d="M9.5 6.5l5.5 5.5-5.5 5.5"/>',
  cerrar:'<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
  info:'<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5"/><circle cx="12" cy="8" r=".6" fill="currentColor"/>',
  refrescar:'<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5v4h-4"/>',
  numeros:'<path d="M6 19v-7M12 19V5M18 19v-10"/>',
  fijar:'<path d="M9 4h6l-1 6 3 3H7l3-3z"/><path d="M12 13v7"/>',
  documento:'<path d="M7 3.5h7l4 4v13H7z"/><path d="M14 3.5v4h4M9.5 12h6M9.5 15.5h6"/>',
};
const icono=(n,cls='')=>`<svg class="ico${cls?` ${cls}`:''}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONOS[n]||''}</svg>`;
