// Paneles del mismo componente Costos; comparten selección y cálculos.
// Se concatenan con costos_tabla.js: no hay peticiones ni cifras de ejemplo.
function tasaCelda(st, data, w, F, fila, indice) {
  if (!fila.tasa) return '';
  const v = valores(st, data, w, { tipo: 'pct', num: fila.tasa, den: 'v' }, F);
  return `<span class="tasa">${pct(indice == null ? v.tot : v.mes[indice])} de venta</span>`;
}

function observaciones(st, data, w, F) {
  if (st.grano !== 'mes') return '';
  const seleccion = data.calidad?.[st.seleccionado] || {};
  const detalle = (seleccion.detalle || []).filter(r => F.includes(r.familia));
  st.detalleObservaciones = detalle;
  const seleccionVenta = (data.calidad_venta?.[st.seleccionado] || []);
  const grupos = seleccionVenta.filter(g => F.includes(g.familia)
    || (g.extra && F.includes('Alimentos') && st.extra.has(g.extra)));
  const sinCosto = grupos.reduce((a, g) => a + g.sin_costo, 0);
  const ventaSinCosto = grupos.reduce((a, g) => a + g.venta_sin_costo, 0);
  const fuera = seleccionVenta.filter(g => !g.familia && !g.extra && Math.abs(g.neto) > .005);
  const areas = (seleccion.areas_sin_cierre_final || []).length + (seleccion.areas_sin_cierre_inicial || []).length;
  const operativo = valores(st, data, w, { k: 'operativo', tipo: 'suma' }, F);
  const indice = w.per.findIndex(p => p.k === st.seleccionado);
  const negativo = operativo.mes[indice] < -.005;
  const observada = detalle.length || sinCosto || areas || negativo || fuera.length;
  const meses = w.per.filter(p => (data.calidad?.[p.k]?.detalle || []).some(r => F.includes(r.familia))).length;
  const nombre = w.per[indice]?.rot || st.seleccionado;
  const abierto = st.notasAbiertas.has('calidad');
  let cuerpo = `<p>Se revisan el inventario inicial y final de <b>${esc(nombre)}</b>, para las familias elegidas. ${meses} de ${w.per.length} meses visibles tienen observaciones en sus inventarios. Los valores se conservan como fueron registrados.</p>`;
  if (!observada) cuerpo += '<p>Sin alertas automáticas detectadas en la selección. Esto no certifica el conteo físico ni todos los costos de receta.</p>';
  if (negativo) cuerpo += '<p><b>Consumo operativo negativo:</b> revisar cierres, compras y valorización antes de interpretar este resultado.</p>';
  if (areas) cuerpo += `<p><b>Cobertura de áreas diferente:</b> ${seleccion.areas_sin_cierre_final.length} áreas con valor inicial sin cierre final y ${seleccion.areas_sin_cierre_inicial.length} con valor final sin cierre inicial. Revisar el alcance del período.</p>`;
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
  return `<details class="cv-panel cv-calidad ${observada ? 'con-observaciones' : ''}" data-nota="calidad"${abierto ? ' open' : ''}><summary><span>${observada ? 'Con observaciones de valorización' : 'Calidad de los datos'} · ${esc(nombre)}</span><span class="cv-panel-ayuda">Ver detalle por mes y familia</span></summary><div class="cv-panel-cuerpo">${cuerpo}</div></details>`;
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

function coberturaSUNAT(st) {
  if (st.grano !== 'mes') return '';
  const c = st.todo.documental?.[st.seleccionado];
  const enlace = st.todo.enlaces?.mes?.[st.seleccionado]?.documental?.url || '?reporte=Documentos%20SUNAT';
  const abierto = st.notasAbiertas.has('documental');
  let texto = '<p>No hay cobertura disponible del registro SUNAT cargado para este mes. La ausencia de datos no equivale a cero comprobantes pendientes.</p>';
  let resumen = 'Sin cobertura disponible';
  if (c?.disponible) {
    resumen = `${c.ubicados} de ${c.documentos} ubicados (${pct(c.cobertura)}) · ${c.sin_coincidencia} sin coincidencia`;
    texto = `<div class="cv-documental-metricas"><div><strong>${pct(c.cobertura)}</strong><span>Cobertura de coincidencia</span></div><div><strong>${c.coinciden}</strong><span>Importes coincidentes</span></div><div><strong>${c.con_diferencia}</strong><span>Ubicados con diferencias</span></div><div><strong>${c.sin_coincidencia}</strong><span>Sin coincidencia en el Sistema</span></div></div>
      <p>Sin coincidencia: importes positivos ${soles(c.importe_positivo_sin_coincidencia)}${c.notas_sin_coincidencia ? `; ${c.notas_sin_coincidencia} notas de crédito por ${soles(c.importe_notas_sin_coincidencia)}` : ''}. Son montos documentales con impuestos; las notas se muestran separadas.</p>`;
  }
  return `<details class="cv-panel" data-nota="documental"${abierto ? ' open' : ''}><summary><span>Cobertura de registro · SUNAT y Sistema</span><span class="cv-panel-ayuda">${esc(resumen)}</span></summary><div class="cv-panel-cuerpo">${texto}<p>Entre los comprobantes SUNAT disponibles del mes seleccionado, antes de filtrar estados. Los documentos solo del Sistema quedan fuera del denominador. Este control no sigue los filtros de familias: SUNAT registra documentos, no insumos.</p><p>Sin coincidencia documental no confirma falta de recepción física ni demuestra que toda la mercadería no se registró por otro documento. No se añade ni se resta ningún importe a las compras o al consumo.</p><a class="cv-accion" href="${esc(enlace)}" target="_blank" rel="noopener noreferrer">Abrir Documentos SUNAT del mes ↗</a></div></details>`;
}

function graficoComparacion(st, data, w, F) {
  const esPct = st.metrica !== 'importe';
  const serie = k => valores(st, data, w, esPct ? { tipo: 'pct', num: k, den: 'v' } : { tipo: 'suma', k }, F).mes;
  const carta = serie('carta'), pos = serie('pos');
  const todos = [...carta, ...pos].filter(x => x != null && isFinite(x));
  let lo = Math.min(0, ...todos), hi = Math.max(0, ...todos);
  if (hi - lo < 1e-9) hi = lo + 1;
  const n = w.per.length, xp = i => 65 + (n < 2 ? 390 : i * 780 / (n - 1));
  const yp = x => 185 - (x - lo) * 150 / (hi - lo);
  const fmt = x => esPct ? pct(x) : soles(x);
  let svg = '<svg viewBox="0 0 910 230" role="img" aria-label="Comparación de consumo carta y costo del Sistema">';
  for (let i = 0; i < 4; i++) { const x = lo + (hi - lo) * i / 3; svg += `<line x1="65" x2="845" y1="${yp(x)}" y2="${yp(x)}" class="cv-grilla"/><text x="56" y="${yp(x) + 4}" text-anchor="end">${esc(esPct ? pct(x) : mil(x))}</text>`; }
  for (const [nombre, vals, clase] of [['Consumo carta', carta, 'carta'], ['Sistema', pos, 'sistema']]) {
    // Cada tramo termina en un dato ausente: nunca une el hueco con una línea.
    let tramo = [];
    const terminar = () => { if (tramo.length) svg += `<polyline class="cv-linea ${clase}" points="${tramo.join(' ')}"/>`; tramo = []; };
    vals.forEach((x, i) => { if (x == null || !isFinite(x)) { terminar(); return; } tramo.push(`${xp(i)},${yp(x)}`); }); terminar();
    vals.forEach((x, i) => { if (x == null || !isFinite(x)) return; svg += `<circle class="cv-punto ${clase}" data-seleccionar="${esc(w.per[i].k)}" tabindex="0" role="button" aria-label="${esc(w.per[i].rot)} · ${nombre}: ${esc(fmt(x))}" cx="${xp(i)}" cy="${yp(x)}" r="${w.per[i].k === st.seleccionado ? 6 : 4}"><title>${esc(w.per[i].rot)} · ${nombre}: ${esc(fmt(x))}</title></circle>`; });
  }
  w.per.forEach((p, i) => { svg += `<text x="${xp(i)}" y="214" text-anchor="middle">${esc(p.rot)}</text>`; });
  svg += '</svg>';
  const i = w.per.findIndex(p => p.k === st.seleccionado);
  const dif = valores(st, data, w, { tipo: 'suma', k: 'dif' }, F).mes[i];
  return `<details class="cv-panel" data-nota="grafico"${st.notasAbiertas.has('grafico') ? ' open' : ''}><summary><span>Evolución · Consumo carta y Sistema</span><span class="cv-panel-ayuda">Seleccionar un mes y revisar su cálculo</span></summary><div class="cv-panel-cuerpo"><div class="cv-grafico-controles"><div class="modo" role="group" aria-label="Medida del gráfico"><button type="button" data-metrica="porcentaje" aria-pressed="${esPct}">% de venta</button><button type="button" data-metrica="importe" aria-pressed="${!esPct}">Importe S/</button></div><div class="leyenda"><span><i class="carta"></i>Consumo carta</span><span><i class="sistema"></i>Sistema</span></div></div><div class="cv-comparacion">${svg}</div><div class="cv-elegir-mes" role="group" aria-label="Mes seleccionado">${w.per.map(p => `<button type="button" class="cv-accion" data-seleccionar="${esc(p.k)}" aria-pressed="${p.k === st.seleccionado}">${esc(p.rot)}</button>`).join('')}</div><div class="cv-seleccion-resumen"><b>${esc(w.per[i].rot)}</b><span>Consumo carta ${esc(fmt(carta[i]))}</span><span>Sistema ${esc(fmt(pos[i]))}</span><span>Diferencia ${soles(dif)}</span><button type="button" class="cv-accion" data-revisar-mes>Revisar cálculo y observaciones</button></div><p>La selección resalta la columna y actualiza las observaciones y el control documental. Cada porcentaje usa la venta neta del mismo período y alcance.</p></div></details>`;
}

function comercial(st, data, w, F) {
  const defs = [{ k: 'margen', nom: 'Margen según consumo', nota: 'venta neta − consumo carta', tipo: 'suma' },
    { k: 'desc', nom: 'Costo atribuido a descuentos', nota: 'referencia proporcional neta de convenios', tipo: 'suma' }];
  const rows = defs.map(f => { const v = valores(st, data, w, f, F); return `<tr><th scope="row">${f.nom}<span class="tasa">${f.nota}</span></th>${v.mes.map((x, i) => `<td>${num(x)}${enlaceOrigen(st, f, w.per[i])}</td>`).join('')}<td class="tot">${num(v.tot)}</td></tr>`; }).join('');
  return `<details class="cv-panel" data-nota="comercial"${st.notasAbiertas.has('comercial') ? ' open' : ''}><summary><span>Margen y descuentos</span><span class="cv-panel-ayuda">Análisis comercial separado de la conciliación</span></summary><div class="cv-panel-cuerpo"><div class="cv-comercial-scroll"><table class="cv-comercial-tabla"><thead><tr><th>Concepto</th>${w.per.map(p => `<th>${esc(p.rot)}</th>`).join('')}<th>Total</th></tr></thead><tbody>${rows}</tbody></table></div><p>El costo atribuido a descuentos no es el descuento cobrado al cliente. Es una referencia proporcional del costo de los platos, ajustada por las devoluciones de convenios configuradas. No se resta del consumo carta ni del costo del Sistema.</p><p>El margen incluye las diferencias de consumo pendientes de conciliar. Los porcentajes y totales de la tabla principal usan la venta acumulada; los inventarios muestran la primera y la última punta, sin sumar cierres mensuales.</p></div></details>`;
}
