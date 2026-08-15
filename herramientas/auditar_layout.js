/**
 * auditar_layout.js  —  auditoría rápida del layout de la webapp.
 *
 * Cómo usar:
 *   1. Levantar el preview (`streamlit run app.py` o `preview_start` name="app").
 *   2. Abrir DevTools (F12) → pestaña Console.
 *   3. Pegar todo este archivo y presionar Enter. Se define `auditar()`.
 *   4. Llamar:
 *        auditar()                       // vista general
 *        auditar({top: 20})              // mostrar 20 contenedores en vez de 10
 *        auditar({umbralAlto: 0.4})      // señalar los que ocupan >40% del viewport
 *        auditar({soloDesborde: true})   // solo el reporte de desborde horizontal
 *
 * Devuelve un objeto JSON en la consola. Ordena por altura descendente porque
 * los "contenedores muy grandes comparados con los demás" son casi siempre
 * altos. Marca con ⚠️ los que superan el umbral.
 *
 * NO modifica nada de la página. Solo lee.
 */
(function () {
  window.auditar = function (opts = {}) {
    const cfg = {
      top: 10,
      umbralAlto: 0.5,     // % del viewport que se considera "grande"
      umbralAncho: 0.9,    // % del ancho útil que se considera "casi todo"
      soloDesborde: false,
      ...opts,
    };

    const vw = innerWidth, vh = innerHeight;
    const main = document.querySelector('[data-testid="stMainBlockContainer"]')
              || document.querySelector('.stApp')
              || document.body;
    const mw = main.getBoundingClientRect().width;
    const de = document.documentElement;

    // ─── desborde horizontal ─────────────────────────────────────────────
    const desborde = de.scrollWidth - Math.round(vw);
    const culpablesDesborde = [];
    if (desborde > 1) {
      document.querySelectorAll('*').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.right > vw + 2 && r.width > 20) {
          const key = (el.className.toString().match(/st-key-([\w-]+)/) || [])[1];
          culpablesDesborde.push({
            tag: el.tagName.toLowerCase(),
            key: key || null,
            right: Math.round(r.right),
            w: Math.round(r.width),
            selector: key ? `.st-key-${key}` : (el.id ? `#${el.id}` : el.tagName.toLowerCase()),
          });
        }
      });
    }

    if (cfg.soloDesborde) {
      const rpt = {viewport: [vw, vh], scrollWidth: de.scrollWidth,
                   desbordePx: desborde, culpables: culpablesDesborde.slice(0, 8)};
      console.table(rpt.culpables);
      return rpt;
    }

    // ─── contenedores con key propia ─────────────────────────────────────
    const contenedores = [];
    document.querySelectorAll('[class*="st-key-"]').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) return;
      const key = (el.className.match(/st-key-([\w-]+)/) || [])[1] || '?';
      const pctVh = r.height / vh;
      const pctW = r.width / mw;
      contenedores.push({
        key,
        w: Math.round(r.width),
        h: Math.round(r.height),
        '%W': Math.round(pctW * 100),
        '%Vh': Math.round(pctVh * 100),
        alerta: pctVh > cfg.umbralAlto ? '⚠️ alto'
              : pctW > cfg.umbralAncho ? '⚠️ ancho'
              : '',
      });
    });
    contenedores.sort((a, b) => b.h - a.h);

    // ─── elementos flotantes (position fixed/absolute) ───────────────────
    const flotantes = [];
    document.querySelectorAll('*').forEach(el => {
      const pos = getComputedStyle(el).position;
      if (pos !== 'fixed' && pos !== 'absolute') return;
      const r = el.getBoundingClientRect();
      if (r.width < 20 || r.height < 20) return;
      const key = (el.className.toString().match(/st-key-([\w-]+)/) || [])[1];
      const tid = el.getAttribute('data-testid');
      flotantes.push({
        pos, key: key || null, testid: tid || null,
        w: Math.round(r.width), h: Math.round(r.height),
        top: Math.round(r.top), left: Math.round(r.left),
      });
    });

    // ─── outliers dentro de la misma familia de key ──────────────────────
    // Ej. si hay ejex_*, ejey_*, color_*, tipo_* y uno mide el doble.
    const familias = {};
    contenedores.forEach(c => {
      const fam = c.key.replace(/_[^_]*$/, '');
      if (!familias[fam]) familias[fam] = [];
      familias[fam].push(c);
    });
    const outliers = [];
    Object.entries(familias).forEach(([fam, arr]) => {
      if (arr.length < 2) return;
      const alturas = arr.map(x => x.h);
      const med = alturas.slice().sort((a, b) => a - b)[Math.floor(alturas.length / 2)];
      arr.forEach(c => {
        if (med > 0 && c.h > med * 1.5) {
          outliers.push({key: c.key, familia: fam, h: c.h, medianaFam: med});
        }
      });
    });

    // ─── HOLGURA: paneles que podrían crecer y no crecen ─────────────────
    // El auditor avisaba de lo que SE PASA. El caso inverso —un panel con
    // scroll propio de 150px dentro de una tarjeta donde sobran 350— no
    // rompe nada, así que pasaba desapercibido: reportado con captura el
    // 2026-08-14, y la causa era un alto calculado en Python contra una
    // pantalla supuesta (ver alturas.py § LA RESTA NO SE HACE ACÁ).
    //
    // Se mira todo lo que scrollea por dentro y se compara con el hueco que
    // le deja su tarjeta enmarcada (la que tiene max-height). Si sobra
    // espacio Y además el contenido está recortado, el panel está chico por
    // decisión de alguien, no por falta de sitio.
    const holguras = [];
    document.querySelectorAll('[class*="st-key-"]').forEach(el => {
      const cs = getComputedStyle(el);
      if (!/auto|scroll/.test(cs.overflowY)) return;
      const alto = el.clientHeight;
      const recorte = el.scrollHeight - alto;
      if (alto < 40 || recorte < 20) return;      // no scrollea de verdad
      // Tarjeta enmarcada más cercana (la que define "una pantalla").
      let marco = el.parentElement, libre = null;
      while (marco) {
        const m = getComputedStyle(marco);
        if (m.maxHeight && m.maxHeight !== 'none') {
          libre = Math.round(parseFloat(m.maxHeight) - marco.scrollHeight);
          break;
        }
        marco = marco.parentElement;
      }
      if (libre !== null && libre > 60) {
        holguras.push({
          key: (el.className.match(/st-key-[\w-]+/) || [''])[0],
          alto, contenido: el.scrollHeight, recortadoPx: recorte,
          podriaCrecerPx: libre,
          marco: (marco.className.match(/st-key-[\w-]+/) || ['(sin key)'])[0],
        });
      }
    });

    const rpt = {
      viewport: [vw, vh],
      anchoUtil: Math.round(mw),
      totalContenedores: contenedores.length,
      desbordeHorizontalPx: desborde > 1 ? desborde : 0,
      culpablesDesborde: culpablesDesborde.slice(0, 6),
      topAltos: contenedores.slice(0, cfg.top),
      alertas: contenedores.filter(c => c.alerta).slice(0, cfg.top),
      outliersDeFamilia: outliers,
      holguras,
      flotantes,
    };

    console.log('%c[auditar_layout]', 'color:#6c5ce7;font-weight:bold',
                `${vw}×${vh}px  ·  ancho útil ${Math.round(mw)}px  ·  `
              + `${contenedores.length} contenedores con key`);
    if (rpt.desbordeHorizontalPx) {
      console.warn(`Desborde horizontal: ${rpt.desbordeHorizontalPx}px`);
      console.table(rpt.culpablesDesborde);
    }
    if (rpt.alertas.length) {
      console.warn(`${rpt.alertas.length} contenedores por encima del umbral:`);
      console.table(rpt.alertas);
    }
    if (rpt.outliersDeFamilia.length) {
      console.warn('Outliers dentro de la misma familia de key:');
      console.table(rpt.outliersDeFamilia);
    }
    if (rpt.holguras.length) {
      console.warn('Paneles que podrían crecer (alto chico con sitio libre):');
      console.table(rpt.holguras);
    }
    console.log('Top por altura:');
    console.table(rpt.topAltos);
    if (rpt.flotantes.length) {
      console.log(`${rpt.flotantes.length} elementos flotantes (fixed/absolute):`);
      console.table(rpt.flotantes);
    }
    return rpt;
  };

  console.log('%cauditar()%c disponible. Ejemplos:\n' +
              '  auditar()\n  auditar({top:20, umbralAlto:0.4})\n  auditar({soloDesborde:true})',
              'color:#6c5ce7;font-weight:bold', 'color:inherit');
})();
