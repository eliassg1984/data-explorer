// Paneles del mismo componente Costos; comparten selección y cálculos.
// Se concatenan con costos_tabla.js: no hay peticiones ni cifras de ejemplo.
function tasaCelda(st, data, w, F, fila, indice) {
  if (!fila.tasa) return '';
  const v = valores(st, data, w, { tipo: 'pct', num: fila.tasa, den: 'v' }, F);
  return `<span class="tasa">${pct(indice == null ? v.tot : v.mes[indice])} de venta</span>`;
}

// Lo que se revisa del período elegido: los puntos en corto (la tarjeta del
// costado, `calidadCorta` en costos_vistas.js) y el cuerpo entero (el
// detalle a todo el ancho, que se dibuja sólo mientras está abierto).
function calidad(st, data, w, F) {
  const seleccion = data.calidad?.[st.seleccionado] || {};
  const detalle = (seleccion.detalle || []).filter(r => F.includes(r.familia));
  st.detalleObservaciones = detalle;
  const seleccionVenta = (data.calidad_venta?.[st.seleccionado] || []);
  const grupos = seleccionVenta.filter(g => F.includes(g.familia)
    || (g.extra && F.includes('Alimentos') && st.extra.has(g.extra)));
  const sinCosto = grupos.reduce((a, g) => a + g.sin_costo, 0);
  const ventaSinCosto = grupos.reduce((a, g) => a + g.venta_sin_costo, 0);
  const fuera = seleccionVenta.filter(g => !g.familia && !g.extra && Math.abs(g.neto) > .005);
  const sinFinal = (seleccion.areas_sin_cierre_final || []).length, sinInicial = (seleccion.areas_sin_cierre_inicial || []).length;
  const areas = sinFinal + sinInicial;
  const operativo = valores(st, data, w, { k: 'operativo', tipo: 'suma' }, F);
  const indice = w.per.findIndex(p => p.k === st.seleccionado);
  const negativo = operativo.mes[indice] < -.005;
  const observada = !!(detalle.length || sinCosto || areas || negativo || fuera.length);
  const meses = w.per.filter(p => (data.calidad?.[p.k]?.detalle || []).some(r => F.includes(r.familia))).length;
  const nombre = w.per[indice]?.rot || st.seleccionado;
  const puntos = [];
  if (negativo) puntos.push('<b>Consumo operativo negativo</b>');
  if (detalle.length) puntos.push(`<b>${detalle.length}</b> ${detalle.length === 1 ? 'línea' : 'líneas'} de inventario por revisar`);
  if (areas) puntos.push(`<b>${areas}</b> áreas con cobertura distinta entre cierres`);
  if (sinCosto) puntos.push(`<b>${sinCosto}</b> ${sinCosto === 1 ? 'línea vendida' : 'líneas vendidas'} sin costo · ${soles(ventaSinCosto)}`);
  if (fuera.length) puntos.push(`<b>${fuera.length}</b> ${fuera.length === 1 ? 'grupo' : 'grupos'} de venta fuera de la agrupación`);
  if (seleccion.fechas_finales?.length > 1) puntos.push(`Cierre final abierto en ${seleccion.fechas_finales.length} fechas`);
  if (!seleccion.columnas_valorizacion) puntos.push('Faltan columnas para comprobar cantidades y precios');
  if (meses) puntos.push(`${meses} de ${w.per.length} meses visibles con observaciones`);
  let cuerpo = `<p>Se revisan el inventario inicial y final de <b>${esc(nombre)}</b>, para las familias elegidas. ${meses} de ${w.per.length} meses visibles tienen observaciones en sus inventarios. Los valores se conservan como fueron registrados.</p>`;
  if (!observada) cuerpo += '<p>Sin alertas automáticas detectadas en la selección. Esto no certifica el conteo físico ni todos los costos de receta.</p>';
  if (negativo) cuerpo += '<p><b>Consumo operativo negativo:</b> revisar cierres, compras y valorización antes de interpretar este resultado.</p>';
  if (areas) cuerpo += `<p><b>Cobertura de áreas diferente:</b> ${sinFinal} áreas con valor inicial sin cierre final y ${sinInicial} con valor final sin cierre inicial. Revisar el alcance del período.</p>`;
  if (seleccion.fechas_finales?.length > 1) cuerpo += `<p>Aperturas del cierre final: ${esc(seleccion.fechas_finales.join(', '))}. Confirmar las fechas de conteo y los movimientos incluidos.</p>`;
  if (!seleccion.columnas_valorizacion) cuerpo += '<p>No están disponibles todas las columnas para comprobar cantidades y precios de los cierres.</p>';
  if (detalle.length) {
    cuerpo += `<p><b>${detalle.length} líneas de inventario por revisar.</b> El precio cero no permite estimar su costo faltante. Una observación del cierre anterior también afecta el inventario inicial de este mes.</p><button type="button" class="cv-accion" data-exportar-observaciones>Descargar detalle completo (CSV)</button>`;
    cuerpo += `<div class="cv-calidad-scroll"><table class="cv-calidad-tabla"><thead><tr>${['Punta', 'Fecha', 'Área', 'Producto', 'Stock', 'Precio', 'Valor S/', 'Observación'].map(n => `<th>${n}</th>`).join('')}</tr></thead><tbody>${detalle.slice(0, 100).map(r => `<tr><td>${esc(r.punta)}</td><td>${esc(r.fecha)}</td><td>${esc(r.area)}</td><td>${esc(r.codigo)} · ${esc(r.producto)}</td><td>${r.cantidad == null ? '—' : esc(r.cantidad)}</td><td>${r.precio == null ? '—' : esc(r.precio)}</td><td>${r.valor == null ? '—' : esc(r.valor)}</td><td>${esc(r.observacion)}</td></tr>`).join('')}</tbody></table></div>`;
    if (detalle.length > 100) cuerpo += `<p>Mostrando 100 de ${detalle.length} líneas; el CSV contiene todas.</p>`;
    cuerpo += '<p>Las cantidades de productos con unidades distintas no se suman.</p>';
  }
  if (sinCosto) cuerpo += `<p><b>${sinCosto} líneas con venta positiva y costo cero o ausente</b> · venta neta ${soles(ventaSinCosto)}. Ese importe es venta, no costo faltante. Revisar servicios sin receta y costos no registrados. ${enlaceOrigen(st, { k: 'pos' }, w.per[indice])}</p>`;
  if (fuera.length) cuerpo += `<p><b>Grupos fuera de la agrupación:</b> ${fuera.map(g => `${esc(g.grupo)} (venta ${soles(g.neto)}, costo ${soles(g.costo)})`).join('; ')}. Revisar si consumen inventario de las familias elegidas.</p>`;
  return { observada, puntos, cuerpo, nombre };
}

// El detalle entero, a todo el ancho: sólo mientras está abierto. Lo abre
// la tarjeta corta del costado o «Revisar cálculo y observaciones».
function observaciones(st, data, w, F) {
  if (st.grano !== 'mes' || !st.notasAbiertas.has('calidad')) return '';
  const q = calidad(st, data, w, F);
  return `<details class="cv-panel cv-calidad ${q.observada ? 'con-observaciones' : ''}" data-nota="calidad" open><summary><span>${q.observada ? 'Observaciones de valorización' : 'Calidad de los datos'} · ${esc(q.nombre)}</span><span class="cv-panel-ayuda">Cerrar ↑</span></summary><div class="cv-panel-cuerpo">${q.cuerpo}</div></details>`;
}

function exportarObservaciones(st) {
  const campos = ['punta', 'fecha', 'familia', 'area', 'codigo', 'producto', 'cantidad', 'precio', 'valor', 'observacion'];
  // Evita interpretar nombres/códigos como fórmulas al abrir el CSV.
  const celda = v => { let t = String(v ?? ''); if (/^[=+@\-]/.test(t) && typeof v !== 'number') t = "'" + t; return '"' + t.replaceAll('"', '""') + '"'; };
  const texto = '\ufeff' + [campos, ...(st.detalleObservaciones || []).map(r => campos.map(c => r[c]))].map(r => r.map(celda).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([texto], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a'); a.href = url; a.download = `costos-observaciones-${st.seleccionado}.csv`; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function comercial(st, data, w, F) {
  // Cuerpo de la pestaña «Margen y descuentos».
  const defs = [{ k: 'margen', nom: 'Margen según consumo', nota: 'venta neta − consumo carta', tipo: 'suma' },
    { k: 'desc', nom: 'Costo atribuido a descuentos', nota: 'referencia proporcional neta de convenios', tipo: 'suma' }];
  const rows = defs.map(f => { const v = valores(st, data, w, f, F); return `<tr><th scope="row">${f.nom}<span class="tasa">${f.nota}</span></th>${v.mes.map((x, i) => `<td>${num(x)}${enlaceOrigen(st, f, w.per[i])}</td>`).join('')}<td class="tot">${num(v.tot)}</td></tr>`; }).join('');
  return `<div class="cv-comercial-scroll"><table class="cv-comercial-tabla"><thead><tr><th>Concepto</th>${w.per.map(p => `<th>${esc(p.rot)}</th>`).join('')}<th>Total</th></tr></thead><tbody>${rows}</tbody></table></div><p>El costo atribuido a descuentos no es el descuento cobrado al cliente. Es una referencia proporcional del costo de los platos, ajustada por las devoluciones de convenios configuradas. No se resta del consumo carta ni del costo del Sistema.</p><p>El margen incluye las diferencias de consumo que siguen sin explicar. Los porcentajes y totales de la tabla principal usan la venta acumulada; los inventarios muestran la primera y la última punta, sin sumar cierres mensuales.</p>`;
}
