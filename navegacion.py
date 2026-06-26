"""
Navegación de la app: rail vertical de iconos y franja superior delgada.
Ambos se inyectan como HTML/JS en el documento padre.
"""

import json
import streamlit.components.v1 as components


# ===========================================================================
# MAPEO DE ICONOS A EMOJIS (para la barra lateral)
# ===========================================================================
ICONO_A_EMOJI = {
    "sliders": "🎚️",
    "cart": "🛒",
    "boxes": "📦",
    "clipboard-data": "📋",
    "receipt": "🧾",
    "cash-coin": "💰",
    "box-arrow-up": "📤",
    "card-checklist": "📝",
    "search": "🔍",
}


# ===========================================================================
# BARRA LATERAL DE ICONOS (RAIL) – INYECTADA DIRECTAMENTE EN LA PÁGINA
# ===========================================================================

def inject_icon_rail(reportes, reporte_activo, mostrar_inspector=False):
    """
    Inyecta una barra lateral fija con emojis como iconos.
    Oculta el sidebar nativo y ajusta el margen del contenido.

    mostrar_inspector: si es False (por defecto), el ícono del Inspector
    se oculta para usuarios normales. Solo se muestra cuando se pasa
    mostrar_inspector=True (por ejemplo cuando ?debug=1 está en la URL).
    """
    reportes_emoji = {}
    for nombre, info in reportes.items():
        # Ocultar Inspector a usuarios normales
        if nombre == "Inspector" and not mostrar_inspector:
            continue
        icono_txt = info.get("icono", "❓")
        reportes_emoji[nombre] = ICONO_A_EMOJI.get(icono_txt, "❓")

    reportes_js = json.dumps(reportes_emoji)
    activo_js = json.dumps(reporte_activo)

    html = f"""
    <script>
    (function() {{
        var doc = window.parent.document;
        var win = window.parent;

        // ── Navegación a prueba de sandbox ──────────────────────────────
        if (!doc.getElementById('rail-nav-fns')) {{
            var navScript = doc.createElement('script');
            navScript.id = 'rail-nav-fns';
            navScript.textContent =
                "window.__navReporte=function(n){{try{{var u=new URL(window.location.href);u.searchParams.set('reporte',n);u.searchParams.delete('refresh');window.location.assign(u.toString());}}catch(e){{if(window.__logErr)window.__logErr('Navegacion bloqueada (sandbox?): '+e.message);}}}};" +
                "window.__refreshReporte=function(){{try{{var u=new URL(window.location.href);u.searchParams.set('refresh','1');window.location.assign(u.toString());}}catch(e){{if(window.__logErr)window.__logErr('Refresco bloqueado (sandbox?): '+e.message);}}}};";
            doc.head.appendChild(navScript);
        }}

        // ── Inyectar estilos solo una vez (evitar duplicados) ──
        if (!doc.getElementById('icon-rail-styles')) {{
            var estilos = doc.createElement('style');
            estilos.id = 'icon-rail-styles';
            estilos.textContent = `
                section[data-testid="stSidebar"] {{
                    display: none !important;
                }}
                .stApp {{
                    margin-left: 64px !important;
                }}
                #icon-rail {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 64px;
                    height: 100vh;
                    background: #1e3a5f;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    padding-top: 1rem;
                    z-index: 999999;
                    box-shadow: 2px 0 8px rgba(0,0,0,0.15);
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    overflow: visible;
                }}
                .rail-icon {{
                    width: 48px;
                    height: 48px;
                    margin: 6px 0;
                    border-radius: 12px;
                    background: transparent;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 24px;
                    color: #cbd5e1;
                    cursor: pointer;
                    transition: background 0.2s, color 0.2s;
                    position: relative;
                    overflow: visible;
                }}
                .rail-icon:hover {{
                    background: #2563eb;
                    color: white;
                }}
                .rail-icon.active {{
                    background: #3b82f6;
                    color: white;
                    box-shadow: 0 0 0 2px #93c5fd;
                }}
                .rail-icon::after {{
                    content: attr(data-tooltip);
                    position: fixed;
                    left: 72px;
                    background: #1e293b;
                    color: white;
                    padding: 4px 10px;
                    border-radius: 6px;
                    white-space: nowrap;
                    font-size: 13px;
                    opacity: 0;
                    pointer-events: none;
                    transition: opacity 0.15s;
                    z-index: 9999999;
                    transform: translateY(-50%);
                    margin-top: 0;
                }}
                .rail-icon:hover::after {{
                    opacity: 1;
                }}
                .rail-spacer {{
                    flex: 1;
                }}
                .rail-btn {{
                    width: 48px;
                    height: 48px;
                    margin: 6px 0;
                    border-radius: 12px;
                    background: transparent;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 22px;
                    color: #cbd5e1;
                    cursor: pointer;
                    transition: background 0.2s, color 0.2s;
                }}
                .rail-btn:hover {{
                    background: #2563eb;
                    color: white;
                }}
                @media (max-width: 768px) {{
                    #icon-rail {{ display: none !important; }}
                    .stApp {{ margin-left: 0 !important; }}
                }}
            `;
            doc.head.appendChild(estilos);
        }}

        // ── Construir el rail DOM (una sola vez; guardado en win.__iconRail) ──
        function construirRail() {{
            var rail = doc.createElement('div');
            rail.id = 'icon-rail';

            var iconsContainer = doc.createElement('div');
            iconsContainer.id = 'rail-icons';
            rail.appendChild(iconsContainer);

            var spacer = doc.createElement('div');
            spacer.className = 'rail-spacer';
            rail.appendChild(spacer);

            var refreshBtn = doc.createElement('div');
            refreshBtn.className = 'rail-btn';
            refreshBtn.title = 'Actualizar datos';
            refreshBtn.innerHTML = '🔄';
            refreshBtn.onclick = function() {{
                win.__refreshReporte();
            }};
            rail.appendChild(refreshBtn);

            // Llenar iconos
            var reportes = {reportes_js};
            var activo = {activo_js};
            for (var nombre in reportes) {{
                var emoji = reportes[nombre];
                var div = doc.createElement('div');
                div.className = 'rail-icon' + (nombre === activo ? ' active' : '');
                div.setAttribute('data-tooltip', nombre);
                div.innerHTML = emoji;
                div.onclick = (function(n) {{
                    return function(e) {{
                        e.stopPropagation();
                        win.__navReporte(n);
                    }};
                }})(nombre);
                iconsContainer.appendChild(div);
            }}

            win.__iconRail = rail;
            return rail;
        }}

        // ── Anclar el rail al body; re-anclarlo si Streamlit lo desconecta ──
        function anclarRail() {{
            var existente = doc.getElementById('icon-rail');
            if (existente && existente.parentNode === doc.body) {{
                return;
            }}
            if (existente) {{
                existente.parentNode.removeChild(existente);
            }}
            var rail = win.__iconRail || construirRail();
            doc.body.appendChild(rail);
        }}

        anclarRail();

        if (!win.__iconRailInterval) {{
            win.__iconRailInterval = setInterval(anclarRail, 500);
        }}
    }})();
    </script>
    """
    components.html(html, height=0, scrolling=False)


# ===========================================================================
# FRANJA SUPERIOR DELGADA
# ===========================================================================

def inject_top_bar(reporte_activo):
    """
    Inyecta una franja superior delgada y fija.
    Convive con el rail vertical de iconos (deja 64px libres a la izquierda
    en desktop; en móvil ocupa todo el ancho porque el rail se oculta).
    """
    titulo_js = json.dumps(reporte_activo)

    html = f"""
    <script>
    (function() {{
        var doc = window.parent.document;
        var win = window.parent;

        if (!doc.getElementById('rail-nav-fns')) {{
            var navScript = doc.createElement('script');
            navScript.id = 'rail-nav-fns';
            navScript.textContent =
                "window.__navReporte=function(n){{try{{var u=new URL(window.location.href);u.searchParams.set('reporte',n);u.searchParams.delete('refresh');window.location.assign(u.toString());}}catch(e){{if(window.__logErr)window.__logErr('Navegacion bloqueada (sandbox?): '+e.message);}}}};" +
                "window.__refreshReporte=function(){{try{{var u=new URL(window.location.href);u.searchParams.set('refresh','1');window.location.assign(u.toString());}}catch(e){{if(window.__logErr)window.__logErr('Refresco bloqueado (sandbox?): '+e.message);}}}};";
            doc.head.appendChild(navScript);
        }}

        var estilos = doc.createElement('style');
        estilos.textContent = `
            .stApp {{
                padding-top: 48px !important;
            }}
            #top-bar {{
                position: fixed;
                top: 0;
                left: 64px;
                right: 0;
                height: 48px;
                background: transparent;
                border-bottom: none;
                display: flex;
                align-items: center;
                gap: 14px;
                padding: 0 18px;
                z-index: 999998;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                pointer-events: none;
            }}
            #top-bar .tb-titulo {{
                font-weight: 600;
                font-size: 14px;
                color: #1e3a5f;
                white-space: nowrap;
                transform: translateY(8px);
            }}
            #top-bar .tb-sep {{
                display: none;
            }}
            #top-bar .tb-spacer {{
                flex: 1;
            }}
            #top-bar .tb-btn {{
                width: 30px;
                height: 30px;
                border-radius: 8px;
                border: none;
                background: transparent;
                color: #2563eb;
                font-size: 16px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.15s;
                pointer-events: auto;
            }}
            #top-bar .tb-btn:hover {{
                background: #dbeafe;
            }}
            @media (max-width: 768px) {{
                #top-bar {{
                    left: 0 !important;
                }}
            }}
        `;
        doc.head.appendChild(estilos);

        function crearBarra() {{
            if (doc.getElementById('top-bar')) {{
                return;
            }}
            var bar = doc.createElement('div');
            bar.id = 'top-bar';

            var sep = doc.createElement('div');
            sep.className = 'tb-sep';
            bar.appendChild(sep);

            var spacer = doc.createElement('div');
            spacer.className = 'tb-spacer';
            bar.appendChild(spacer);

            var refreshBtn = doc.createElement('button');
            refreshBtn.className = 'tb-btn';
            refreshBtn.title = 'Actualizar datos';
            refreshBtn.innerHTML = '&#x21bb;';
            refreshBtn.onclick = function() {{
                win.__refreshReporte();
            }};
            bar.appendChild(refreshBtn);

            doc.body.appendChild(bar);
        }}

        crearBarra();
        setInterval(crearBarra, 2000);
    }})();
    </script>
    """
    components.html(html, height=0, scrolling=False)
