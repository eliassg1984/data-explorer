// Ventas: la fecha de la franja no manda en las vistas que eligen sus propios
// períodos —Análisis de platos y la comparación con el año pasado— (regla #768).
// La franja se dibuja fuera de la pila y no sabe qué vista está en pantalla, así
// que la pieza lo sube a un data-* de <html>, barato de cambiar (regla #469), y
// `estilos/_50_fecha.py` la esconde sin correr lo que tiene al lado. Sale sola:
// una raíz que deja la pantalla, o que se quita de la página, avisa al observador.
function sinFechaFranja(raiz) {
  if (raiz.__ioFecha) return;
  const vistas = window.__vtSinFecha || (window.__vtSinFecha = new Set());
  raiz.__ioFecha = new IntersectionObserver((avisos) => {
    avisos.forEach((a) => { if (a.isIntersecting && a.intersectionRatio >= 0.5) vistas.add(a.target); else vistas.delete(a.target); });
    [...vistas].forEach((v) => { if (!v.isConnected) vistas.delete(v); });
    const h = document.documentElement, oculta = vistas.size > 0;
    if ((h.dataset.vtSinFecha === '1') !== oculta) { if (oculta) h.dataset.vtSinFecha = '1'; else delete h.dataset.vtSinFecha; }
  }, { threshold: [0, 0.5, 1] });
  raiz.__ioFecha.observe(raiz);
}
