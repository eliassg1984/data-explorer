/**
 * auditar_graficos.js  —  ¿algún texto de un gráfico se pisa o se corta?
 *
 * Cómo usar:
 *   1. Levantar el preview y abrir la vista que querés revisar.
 *      (Con el deep-link es directo: ?reporte=Ventas&vista=comparativo_vs_ano_pasado)
 *   2. DevTools (F12) → Console → pegar este archivo → Enter.
 *   3. Llamar:
 *        auditarGraficos()                  // todos los Plotly de la página
 *        auditarGraficos({minSolape: 1})    // más estricto (default: 3 px)
 *        auditarGraficos({verTodo: true})   // lista también los textos sanos
 *
 * POR QUÉ EXISTE (2026-08-12): este chequeo se escribió a mano cinco veces
 * en una sola sesión, y encontró cosas que el razonamiento daba por buenas.
 * El caso testigo: pasar las fechas del eje X de diagonales a horizontales
 * (`tickangle=0`) parece obviamente correcto y pisaba 5 pares de etiquetas
 * a 14 barras. Ver `arquitectura.md` regla #92.
 *
 * COMPLEMENTA a herramientas/ver_figura.py, no lo reemplaza:
 *   · ver_figura.py exporta un PNG → sirve para juzgar si algo SE LEE.
 *   · esto mide el DOM real del navegador → sirve para pisadas y recortes,
 *     que en el PNG no son fieles (kaleido no expande márgenes igual).
 *
 * ⚠ SI CAMBIASTE EL TAMAÑO DE LA VENTANA, RECARGÁ ANTES DE AUDITAR.
 * Plotly no re-maquetea solo: el <svg> conserva el ancho viejo y el chequeo
 * reporta media docena de textos "cortados" que en realidad están bien.
 * Pasó de verdad — 25 falsos positivos que desaparecieron con un F5.
 *
 * NO modifica nada. Solo lee.
 */
(function () {
  window.auditarGraficos = function (opts = {}) {
    const cfg = { minSolape: 3, verTodo: false, ...opts };

    const plots = Array.from(document.querySelectorAll(".js-plotly-plot"));
    if (!plots.length) {
      console.warn("No hay ningún gráfico de Plotly en esta página.");
      return { graficos: 0 };
    }

    const nombreDe = (plot) => {
      // La key de Streamlit es el nombre útil: st.plotly_chart(key=...)
      // emite una clase st-key-<key> en su element container.
      const cont = plot.closest('[class*="st-key-"]');
      const m = cont && cont.className.match(/st-key-([\w-]+)/);
      return m ? m[1] : "(sin key)";
    };

    const informe = plots.map((plot) => {
      // TODOS los svg, no el primero. Plotly parte el gráfico en VARIOS
      // `svg.main-svg`: el de los datos/ejes y el "infolayer" con las
      // anotaciones, el legend y los títulos. Mirar sólo el primero deja
      // ciego justo a las anotaciones ("feriado", "en curso", el %Var) —
      // se comprobó plantando dos textos en el mismo punto y este chequeo
      // no los veía. Peor: los solapamientos ENTRE capas (una anotación
      // encima de una etiqueta de barra) son de los más fáciles de generar.
      const svgs = Array.from(plot.querySelectorAll("svg.main-svg"));
      if (!svgs.length) return { grafico: nombreDe(plot), error: "sin svg" };
      const marco = plot.getBoundingClientRect();

      const textos = svgs
        .flatMap((s) => Array.from(s.querySelectorAll("text")))
        .filter((t) => t.textContent.trim())
        .map((t) => {
          const r = t.getBoundingClientRect();
          return { s: t.textContent.trim(), top: r.top, bottom: r.bottom,
                   left: r.left, right: r.right };
        })
        // Los de tamaño 0 no se dibujan (Plotly deja nodos ocultos sueltos).
        .filter((b) => b.right > b.left && b.bottom > b.top);

      // ── pisadas: cualquier par que se superponga en AMBOS ejes ──
      const pisadas = [];
      for (let i = 0; i < textos.length; i++) {
        for (let j = i + 1; j < textos.length; j++) {
          const a = textos[i], b = textos[j];
          const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (ox > cfg.minSolape && oy > cfg.minSolape) {
            pisadas.push({ a: a.s, b: b.s, px: Math.round(Math.min(ox, oy)) });
          }
        }
      }

      // ── recortes: LOS CUATRO lados. El bug que se escapó una vez fue
      //    mirar sólo arriba/abajo y no ver el eje Y cortado por izquierda.
      const recortados = textos
        .filter((b) => b.left < marco.left - 1 || b.right > marco.right + 1 ||
                       b.top < marco.top - 1 || b.bottom > marco.bottom + 1)
        .map((b) => b.s);

      return {
        grafico: nombreDe(plot),
        textos: textos.length,
        pisadas,
        recortados,
        ok: !pisadas.length && !recortados.length,
        ...(cfg.verTodo ? { todos: textos.map((t) => t.s) } : {}),
      };
    });

    const malos = informe.filter((g) => !g.ok);
    console.log(
      `%c${plots.length} gráfico(s) · ${malos.length} con problemas`,
      `font-weight:bold;color:${malos.length ? "#ef4444" : "#16a34a"}`
    );
    informe.forEach((g) => {
      if (g.ok) {
        console.log(`  ✅ ${g.grafico} (${g.textos} textos)`);
        return;
      }
      console.group(`  ❌ ${g.grafico}`);
      if (g.pisadas && g.pisadas.length) {
        console.log("se pisan:", g.pisadas);
      }
      if (g.recortados && g.recortados.length) {
        console.log("cortados por el borde:", g.recortados);
      }
      console.groupEnd();
    });
    return informe;
  };

  console.log(
    "%cauditarGraficos()%c listo — busca textos pisados o cortados en los gráficos.",
    "font-weight:bold", ""
  );
})();
