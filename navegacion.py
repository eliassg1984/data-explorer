"""
Navegación de la app: rail vertical de iconos y franja superior.
Una sola inyección, un solo MutationObserver, un solo bloque de estilos.

Cambio clave: al pulsar un icono NO se recarga la página. El rail "clickea"
botones nativos ocultos (puente) y eso provoca un rerun de Streamlit por
websocket, conservando el shell, el rail y el scroll (sensación de SPA).
"""

import re
import json
import streamlit as st
import streamlit.components.v1 as components


# Nombre del icono "por defecto" si algún reporte no trae 'icono' en data.py
# (debe ser un nombre válido de Bootstrap Icons, sin el prefijo "bi-").
ICONO_DEFECTO = "question-circle"


def _slug(s):
    """Convierte un nombre de reporte en un sufijo de key seguro."""
    return re.sub(r'[^a-zA-Z0-9]+', '_', s)


def _render_bridge(nombres):
    """Botones nativos OCULTOS. El rail los 'clickea' para forzar un rerun por
    websocket (sin recargar la página). Se posicionan fuera de pantalla pero
    siguen siendo clicables."""
    st.markdown(
        "<style>"
        "[class*='st-key-navbtn_'],.st-key-navrefresh{"
        "position:absolute!important;left:-9999px!important;top:0!important;"
        "width:1px!important;height:1px!important;overflow:hidden!important;}"
        "</style>",
        unsafe_allow_html=True,
    )
    for nombre in nombres:
        if st.button(nombre, key=f"navbtn_{_slug(nombre)}"):
            st.query_params["reporte"] = nombre
            if "refresh" in st.query_params:
                del st.query_params["refresh"]
            st.rerun()
    if st.button("__nav_refresh__", key="navrefresh"):
        st.cache_data.clear()
        if "refresh" in st.query_params:
            del st.query_params["refresh"]
        st.rerun()


def inject_navegacion(reportes, reporte_activo, mostrar_inspector=False):
    """Inyecta rail + top bar en una sola llamada."""

    visibles = {
        nombre: info.get("icono") or ICONO_DEFECTO
        for nombre, info in reportes.items()
        if not (nombre == "Inspector" and not mostrar_inspector)
    }

    # Botones puente (ocultos) que el rail clickea para navegar sin recargar.
    _render_bridge(list(visibles.keys()))

    components.html(f"""
    <script>
    (function() {{
        var doc = window.parent.document;
        var win = window.parent;

        // ── Funciones de navegacion (asignadas en window.parent en CADA
        //    inyeccion -> nunca queda una version vieja pegada). Clickean los
        //    botones puente => rerun por websocket, sin recargar la pagina.
        //    Usamos textContent (no innerText): funciona aunque el boton este
        //    oculto/colapsado.
        win.__navReporte = function(n) {{
            try {{
                var b = null;
                var slug = n.replace(/[^a-zA-Z0-9]+/g, '_');
                var w = doc.querySelector('.st-key-navbtn_' + slug);
                if (w) b = w.querySelector('button');
                if (!b) {{
                    var a = doc.querySelectorAll('button');
                    for (var i = 0; i < a.length; i++) {{
                        if ((a[i].textContent || '').trim() === n) {{ b = a[i]; break; }}
                    }}
                }}
                if (b) {{ b.click(); }}
                else if (win.__logErr) {{ win.__logErr('Nav: boton no hallado para ' + n); }}
            }} catch (e) {{ if (win.__logErr) win.__logErr('Nav: ' + e.message); }}
        }};
        win.__refreshReporte = function() {{
            try {{
                var b = null;
                var w = doc.querySelector('.st-key-navrefresh');
                if (w) b = w.querySelector('button');
                if (!b) {{
                    var a = doc.querySelectorAll('button');
                    for (var i = 0; i < a.length; i++) {{
                        if ((a[i].textContent || '').trim() === '__nav_refresh__') {{ b = a[i]; break; }}
                    }}
                }}
                if (b) {{ b.click(); }}
            }} catch (e) {{ if (win.__logErr) win.__logErr('Refresh: ' + e.message); }}
        }};

        // ── Fuente de iconos (Bootstrap Icons), una sola vez ───────────
        if (!doc.getElementById('bi-icons-css')) {{
            var biLink = doc.createElement('link');
            biLink.id = 'bi-icons-css';
            biLink.rel = 'stylesheet';
            biLink.href = 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css';
            doc.head.appendChild(biLink);
        }}

        var REPORTES = {json.dumps(visibles)};
        var ACTIVO = {json.dumps(reporte_activo)};

        // ── Actualizar resaltado + titulo EN CADA rerun (sin reconstruir) ──
        var icons = doc.querySelectorAll('#icon-rail .rail-icon');
        for (var k = 0; k < icons.length; k++) {{
            if (icons[k].getAttribute('data-tooltip') === ACTIVO) icons[k].classList.add('active');
            else icons[k].classList.remove('active');
        }}
        var _tit = doc.querySelector('#top-bar .tb-titulo');
        if (_tit) _tit.textContent = ACTIVO;

        // ── Una sola construccion del DOM ──────────────────────────────
        if (win.__navInit) return;
        win.__navInit = true;

        // ── Estilos: un solo <style> ───────────────────────────────────
        var style = doc.createElement('style');
        style.id = 'nav-styles';
        style.textContent = [
            'section[data-testid="stSidebar"] {{ display: none !important; }}',
            '.stApp {{ margin-left: 64px !important; padding-top: 48px !important; }}',
            '#icon-rail {{',
            '  position:fixed; top:0; left:0; width:64px; height:100vh;',
            '  background:#1e3a5f; display:flex; flex-direction:column;',
            '  align-items:center; padding-top:1rem; z-index:999999;',
            '  box-shadow:2px 0 8px rgba(0,0,0,0.15);',
            '  font-family:-apple-system,BlinkMacSystemFont,sans-serif;',
            '}}',
            '.rail-icon {{',
            '  width:48px; height:48px; margin:6px 0; border-radius:12px;',
            '  background:transparent; display:flex; align-items:center;',
            '  justify-content:center; font-size:24px; color:#cbd5e1;',
            '  cursor:pointer; transition:background .2s,color .2s; position:relative;',
            '}}',
            '.rail-icon:hover {{ background:#2563eb; color:#fff; }}',
            '.rail-icon.active {{ background:#3b82f6; color:#fff; box-shadow:0 0 0 2px #93c5fd; }}',
            '.rail-icon::after {{',
            '  content:attr(data-tooltip); position:fixed; left:72px;',
            '  background:#1e293b; color:#fff; padding:4px 10px;',
            '  border-radius:6px; white-space:nowrap; font-size:13px;',
            '  opacity:0; pointer-events:none; transition:opacity .15s;',
            '  z-index:9999999; transform:translateY(-50%);',
            '}}',
            '.rail-icon:hover::after {{ opacity:1; }}',
            '.rail-spacer {{ flex:1; }}',
            '.rail-btn {{',
            '  width:48px; height:48px; margin:6px 0; border-radius:12px;',
            '  background:transparent; display:flex; align-items:center;',
            '  justify-content:center; font-size:22px; color:#cbd5e1;',
            '  cursor:pointer; transition:background .2s,color .2s;',
            '}}',
            '.rail-btn:hover {{ background:#2563eb; color:#fff; }}',
            '#top-bar {{',
            '  position:fixed; top:0; left:64px; right:0; height:48px;',
            '  display:flex; align-items:center; gap:14px; padding:0 18px;',
            '  z-index:999998; font-family:-apple-system,BlinkMacSystemFont,sans-serif;',
            '  pointer-events:none;',
            '}}',
            '#top-bar .tb-titulo {{',
            '  font-weight:600; font-size:14px; color:#1e3a5f;',
            '  white-space:nowrap;',
            '}}',
            '#top-bar .tb-spacer {{ flex:1; }}',
            '@media(max-width:768px) {{',
            '  #icon-rail {{ display:none !important; }}',
            '  .stApp {{ margin-left:0 !important; }}',
            '  #top-bar {{ left:0 !important; }}',
            '}}',
        ].join('\\n');
        doc.head.appendChild(style);

        // ── Construir rail ─────────────────────────────────────────────
        var rail = doc.createElement('div');
        rail.id = 'icon-rail';

        var iconsContainer = doc.createElement('div');
        rail.appendChild(iconsContainer);

        for (var nombre in REPORTES) {{
            var div = doc.createElement('div');
            div.className = 'rail-icon';
            if (nombre === ACTIVO) div.classList.add('active');
            div.setAttribute('data-tooltip', nombre);
            div.innerHTML = '<i class="bi bi-' + REPORTES[nombre] + '"></i>';
            div.onclick = (function(n) {{
                return function(e) {{ e.stopPropagation(); win.__navReporte(n); }};
            }})(nombre);
            iconsContainer.appendChild(div);
        }}

        var spacer = doc.createElement('div');
        spacer.className = 'rail-spacer';
        rail.appendChild(spacer);

        var refreshBtn = doc.createElement('div');
        refreshBtn.className = 'rail-btn';
        refreshBtn.title = 'Actualizar datos';
        refreshBtn.innerHTML = '🔄';
        refreshBtn.onclick = function() {{ win.__refreshReporte(); }};
        rail.appendChild(refreshBtn);

        // ── Construir top bar (con titulo) ────────────────────────────
        var bar = doc.createElement('div');
        bar.id = 'top-bar';

        var titulo = doc.createElement('div');
        titulo.className = 'tb-titulo';
        titulo.textContent = ACTIVO;
        bar.appendChild(titulo);

        var barSpacer = doc.createElement('div');
        barSpacer.className = 'tb-spacer';
        bar.appendChild(barSpacer);

        // ── Anclar al body con MutationObserver ────────────────────────
        function anclar() {{
            var r = doc.getElementById('icon-rail');
            if (!r || r.parentNode !== doc.body) {{
                if (r) r.parentNode.removeChild(r);
                doc.body.appendChild(rail);
            }}
            var b = doc.getElementById('top-bar');
            if (!b || b.parentNode !== doc.body) {{
                if (b) b.parentNode.removeChild(b);
                doc.body.appendChild(bar);
            }}
        }}

        anclar();

        var obs = new MutationObserver(function() {{
            var r = doc.getElementById('icon-rail');
            var b = doc.getElementById('top-bar');
            if (!r || r.parentNode !== doc.body || !b || b.parentNode !== doc.body) {{
                anclar();
            }}
        }});
        obs.observe(doc.body, {{ childList: false, subtree: false }});

        setTimeout(anclar, 2000);

    }})();
    </script>
    """, height=0, scrolling=False)
