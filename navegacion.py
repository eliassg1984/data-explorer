"""
Navegación de la app: rail vertical de iconos + título superior.

Implementación con BOTONES NATIVOS de Streamlit (sin iframes ni manipulación
del DOM): el click lo maneja Streamlit directamente vía on_click, por lo que
cambiar de reporte es fiable en cada pulsación (no se cuelga ni "deja de hacer
caso"). app.py lee la selección desde st.session_state["_nav_reporte"].
"""

import re
import streamlit as st


# Icono Material por defecto si un reporte no trae 'icono' válido en data.py.
ICONO_DEFECTO = "description"

# Mapa de los nombres de icono que usas en data.py (estilo Bootstrap) a
# Material Symbols, que es lo que acepta st.button como icono.
_MATERIAL = {
    "sliders": "tune",
    "cart": "shopping_cart",
    "boxes": "inventory_2",
    "clipboard-data": "assignment",
    "receipt": "receipt_long",
    "cash-coin": "payments",
    "box-arrow-up": "output",
    "card-checklist": "checklist",
    "search": "search",
    "question-circle": "help",
}


def _slug(s):
    return re.sub(r'[^a-zA-Z0-9]+', '_', s)


def _on_nav_click(nombre):
    """Guarda el reporte elegido. Corre ANTES del script => app.py lo ve desde
    arriba en un solo rerun."""
    st.session_state["_nav_reporte"] = nombre


def _on_refresh_click():
    st.session_state["_nav_refresh"] = True


# ── CSS: convierte el contenedor de botones en una barra fija vertical ──────
_CSS = """
<style>
section[data-testid="stSidebar"] { display:none !important; }
.stApp { margin-left:64px !important; padding-top:48px !important; }

/* Título superior fijo */
#nav-topbar {
    position:fixed; top:0; left:64px; right:0; height:48px;
    display:flex; align-items:center; padding:0 18px;
    font-family:-apple-system,BlinkMacSystemFont,sans-serif;
    font-weight:600; font-size:14px; color:#1e3a5f;
    z-index:999998; pointer-events:none;
}

/* Contenedor del rail -> barra vertical fija a la izquierda */
.st-key-nav_rail {
    position:fixed !important; top:0 !important; left:0 !important;
    width:64px !important; height:100vh !important;
    background:#1e3a5f !important; z-index:999999 !important;
    padding:14px 0 14px 0 !important;
    box-shadow:2px 0 8px rgba(0,0,0,.15) !important;
}
.st-key-nav_rail [data-testid="stVerticalBlock"] {
    display:flex !important; flex-direction:column !important;
    align-items:center !important; gap:6px !important;
    height:100% !important; width:100% !important;
}
.st-key-nav_rail [data-testid="stElementContainer"],
.st-key-nav_rail [class*="st-key-navbtn_"] {
    width:auto !important; min-width:0 !important;
}

/* Cada botón -> tile de icono */
.st-key-nav_rail [class*="st-key-navbtn_"] button {
    width:48px !important; height:48px !important; min-height:48px !important;
    padding:0 !important; margin:0 !important;
    border:none !important; border-radius:12px !important;
    background:transparent !important; color:#cbd5e1 !important;
    display:flex !important; align-items:center !important; justify-content:center !important;
    transition:background .2s, color .2s !important;
}
.st-key-nav_rail [class*="st-key-navbtn_"] button:hover {
    background:#2563eb !important; color:#fff !important;
}
.st-key-nav_rail [class*="st-key-navbtn_"] button[kind="primary"] {
    background:#3b82f6 !important; color:#fff !important;
    box-shadow:0 0 0 2px #93c5fd !important;
}
.st-key-nav_rail [class*="st-key-navbtn_"] button p,
.st-key-nav_rail [class*="st-key-navbtn_"] button span,
.st-key-nav_rail [class*="st-key-navbtn_"] button [data-testid="stIconMaterial"] {
    font-size:24px !important; line-height:1 !important;
}

/* Botón de refresco, al fondo del rail */
.st-key-navbtn_refresh { margin-top:auto !important; }

@media (max-width:768px) {
    .st-key-nav_rail { display:none !important; }
    .stApp { margin-left:0 !important; }
    #nav-topbar { left:0 !important; }
}
</style>
"""


def inject_navegacion(reportes, reporte_activo, mostrar_inspector=False):
    """Dibuja el rail (botones nativos) + el título superior."""
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div id="nav-topbar">{reporte_activo}</div>',
        unsafe_allow_html=True,
    )

    visibles = {
        nombre: info.get("icono") or "question-circle"
        for nombre, info in reportes.items()
        if not (nombre == "Inspector" and not mostrar_inspector)
    }

    with st.container(key="nav_rail"):
        for nombre, icono in visibles.items():
            mat = _MATERIAL.get(icono, ICONO_DEFECTO)
            st.button(
                f":material/{mat}:",
                key=f"navbtn_{_slug(nombre)}",
                help=nombre,
                type="primary" if nombre == reporte_activo else "secondary",
                on_click=_on_nav_click,
                args=(nombre,),
            )
        st.button(
            ":material/refresh:",
            key="navbtn_refresh",
            help="Actualizar datos",
            on_click=_on_refresh_click,
        )
