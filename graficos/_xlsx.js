// Un .xlsx armado en el navegador, sin librerías (regla #691). Lo usan las
// piezas que bajan su tabla en Excel —«Consistencia de datos» y «Costo de
// Carta» (#696)—: su .py lo antepone a su propio .js, así que lo de acá
// queda en el mismo módulo. Usar: bajar('nombre.xlsx', libro([{nombre,
// cabeza, filas}])); `archivo(texto)` da un nombre de fichero sin tildes.
//
// ── El Excel (.xlsx), armado acá sin librerías (regla #691) ──────────────
// Un .xlsx es un ZIP de XML. Se guarda SIN comprimir (método 0), que Excel
// lee igual: sólo hace falta el CRC32 de cada archivo. Los montos van como
// número (se pueden sumar); el resto, como texto en la celda.
const CRC = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(b) {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}
const u16 = (v) => [v & 255, (v >>> 8) & 255];
const u32 = (v) => [v & 255, (v >>> 8) & 255, (v >>> 16) & 255, (v >>> 24) & 255];
function zip(archivos) {
  const enc = new TextEncoder();
  const partes = [], central = [];
  let off = 0;
  archivos.forEach(([nombre, texto]) => {
    const n = enc.encode(nombre), d = enc.encode(texto), c = crc32(d);
    // Fecha 1-ene-1980 (0x21), nombres en UTF-8 (bit 11).
    const comun = [...u16(20), ...u16(0x0800), ...u16(0), ...u16(0), ...u16(0x21),
      ...u32(c), ...u32(d.length), ...u32(d.length), ...u16(n.length), ...u16(0)];
    const loc = new Uint8Array([...u32(0x04034b50), ...comun]);
    partes.push(loc, n, d);
    central.push(new Uint8Array([...u32(0x02014b50), ...u16(20), ...comun,
      ...u16(0), ...u16(0), ...u16(0), ...u32(0), ...u32(off)]), n);
    off += loc.length + n.length + d.length;
  });
  const tam = central.reduce((s, x) => s + x.length, 0);
  const fin = new Uint8Array([...u32(0x06054b50), ...u16(0), ...u16(0), ...u16(archivos.length),
    ...u16(archivos.length), ...u32(tam), ...u32(off), ...u16(0)]);
  return new Blob([...partes, ...central, fin],
    { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}
const xml = (s) => String(s).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '')
  .replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function letra(i) {
  let s = '';
  for (i += 1; i > 0; i = Math.floor((i - 1) / 26)) s = String.fromCharCode(65 + ((i - 1) % 26)) + s;
  return s;
}
const NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main';
const NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
// Una hoja: la cabecera congelada y el ancho de cada columna según su texto.
function hoja(cabeza, filas, decimales = 2) {
  const factor = 10 ** decimales;
  const ancho = cabeza.map((h, i) => Math.min(60, Math.max(8, String(h).length + 2,
    ...filas.slice(0, 400).map((f) => (f[i] == null ? 0 : String(f[i]).length + 2)))));
  const celda = (v, ref) => {
    if (typeof v === 'number' && isFinite(v)) return `<c r="${ref}"><v>${Math.round(v * factor) / factor}</v></c>`;
    if (v == null || v === '') return '';
    return `<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${xml(v)}</t></is></c>`;
  };
  const fila = (r, vals) => `<row r="${r}">${vals.map((v, i) => celda(v, letra(i) + r)).join('')}</row>`;
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    + `<worksheet xmlns="${NS}"><sheetViews><sheetView workbookViewId="0">`
    + '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
    + `<cols>${ancho.map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`).join('')}</cols>`
    + `<sheetData>${[fila(1, cabeza), ...filas.map((f, i) => fila(i + 2, f))].join('')}</sheetData></worksheet>`;
}
// `hojas`: [{nombre, cabeza, filas}]. El nombre de una hoja: hasta 31
// caracteres y sin []:*?/\ (si no, Excel no abre el archivo).
function libro(hojas) {
  const nom = (s) => String(s).replace(/[[\]:*?/\\]/g, ' ').slice(0, 31);
  const archivos = [
    ['[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      + '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      + '<Default Extension="xml" ContentType="application/xml"/>'
      + '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
      + hojas.map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('')
      + '</Types>'],
    ['_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
      + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
      + '</Relationships>'],
    ['xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + `<workbook xmlns="${NS}" xmlns:r="${NS_R}"><sheets>`
      + hojas.map((h, i) => `<sheet name="${xml(nom(h.nombre))}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join('')
      + '</sheets></workbook>'],
    ['xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
      + hojas.map((_, i) => `<Relationship Id="rId${i + 1}" Type="${NS_R}/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join('')
      + '</Relationships>'],
    ...hojas.map((h, i) => [`xl/worksheets/sheet${i + 1}.xml`, hoja(h.cabeza, h.filas, h.decimales ?? 2)]),
  ];
  return zip(archivos);
}
function bajar(nombre, blob) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
}
const archivo = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^A-Za-z0-9]+/g, '_');
