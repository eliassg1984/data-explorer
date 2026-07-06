"""
Navegación de la app: rail vertical de iconos + título superior.

Implementación con BOTONES NATIVOS de Streamlit (sin iframes ni manipulación
del DOM): el click lo maneja Streamlit directamente vía on_click, por lo que
cambiar de reporte es fiable en cada pulsación (no se cuelga ni "deja de hacer
caso"). app.py lee la selección desde st.session_state["_nav_reporte"].
"""

import re
import streamlit as st
import base64
import os


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


# ── Logo del rail (embebido en base64, leído desde assets/logo.png) ──
_LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")

def _logo_data_uri():
    """Lee assets/logo.png y lo devuelve como data URI. Si no existe, vacío."""
    try:
        with open(_LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""

_LOGO_URI = _logo_data_uri()


# ── CSS: convierte el contenedor de botones en una barra fija vertical ──────
# RAIL_ANCHO: ancho de la barra lateral, 40% más grande que el original (64px).
RAIL_ANCHO = 90  # 64 * 1.4 ≈ 90
LOGO_ALTO = 64   # bloque reservado arriba, para el logo

_CSS = f"""
<style>
section[data-testid="stSidebar"] {{ display:none !important; }}
.stApp {{ margin-left:{RAIL_ANCHO}px !important; padding-top:48px !important; }}

/* Título superior fijo */
#nav-topbar {{
    position:fixed; top:0; left:{RAIL_ANCHO}px; right:0; height:48px;
    display:flex; align-items:center; padding:0 18px;
    font-family:'DM Sans',-apple-system,BlinkMacSystemFont,sans-serif;
    font-weight:600; font-size:14px; color:#18181d;
    z-index:999998; pointer-events:none;
}}

/* Contenedor del rail -> barra vertical fija a la izquierda.
   TEMA CALLAI: sidebar blanco con borde sutil (antes rail oscuro). */
.st-key-nav_rail {{
    position:fixed !important; top:0 !important; left:0 !important;
    width:{RAIL_ANCHO}px !important; height:100vh !important;
    background:#ffffff !important; z-index:999999 !important;
    border-right:1px solid #e6e6eb !important;
    padding:0 !important;
    display:flex !important;
    flex-direction:column !important;
}}

/* Bloque arriba del rail, reservado para el logo.
   AHORA usa el logo embebido en base64 desde assets/logo.png */
.st-key-nav_rail::before {{
    content: "";
    display: block;
    width: 100%;
    height: {LOGO_ALTO}px;
    background: #18181d url('{_LOGO_URI}') center / 72% auto no-repeat;
    flex-shrink: 0;
}}

.st-key-nav_rail [data-testid="stVerticalBlock"] {{
    display:flex !important; flex-direction:column !important;
    align-items:center !important; gap:6px !important;
    width:100% !important;
    flex:1 1 auto !important;
    padding:14px 0 14px 0 !important;
}}

/* CONTENEDORES DE BOTONES: los 3 niveles centran su contenido */
.st-key-nav_rail [data-testid="stElementContainer"],
.st-key-nav_rail [class*="st-key-navbtn_"],
.st-key-nav_rail [data-testid="stButton"] {{
    width:100% !important; min-width:0 !important;
    display:flex !important;
    justify-content:center !important;
}}

/* Cada botón -> tile de icono.
   Reposo: icono gris. Hover: tinte lavanda. Activo: píldora lavanda con
   icono índigo, como el ítem activo del sidebar de CallAI. */
.st-key-nav_rail [class*="st-key-navbtn_"] button {{
    width:{RAIL_ANCHO - 16}px !important; height:62px !important; min-height:62px !important;
    margin:0 auto !important;
    padding:0 !important;
    border:none !important; border-radius:12px !important;
    background:transparent !important; color:#85858f !important;
    display:flex !important; align-items:center !important; justify-content:center !important;
    transition:background .2s, color .2s !important;
}}
.st-key-nav_rail [class*="st-key-navbtn_"] button:hover {{
    background:#f0edfe !important; color:#6c5ce7 !important;
}}
.st-key-nav_rail [class*="st-key-navbtn_"] button[kind="primary"] {{
    background:#e7e3fb !important; color:#6c5ce7 !important;
    box-shadow:inset 0 0 0 1px #d4cdf7 !important;
}}
.st-key-nav_rail [class*="st-key-navbtn_"] button p,
.st-key-nav_rail [class*="st-key-navbtn_"] button span,
.st-key-nav_rail [class*="st-key-navbtn_"] button [data-testid="stIconMaterial"] {{
    font-size:26px !important; line-height:1 !important;
}}

/* Botón de refresco, al fondo del rail */
.st-key-navbtn_refresh {{ margin-top:auto !important; }}

@media (max-width:768px) {{
    .st-key-nav_rail {{ display:none !important; }}
    .stApp {{ margin-left:0 !important; }}
    #nav-topbar {{ left:0 !important; }}
}}
</style>
"""


# ── CSS extra SOLO para "Ajuste de Inventario" ──────────────────────────────
# En este reporte el topbar va vacío, así que el padding-top:48px que reserva
# _CSS queda como una franja en blanco arriba. Aquí lo anulamos:
#   - Ocultamos el #nav-topbar (no muestra nada en este reporte).
#   - Usamos "html body ..." para tener MAYOR especificidad que el ".stApp"
#     de _CSS y ganar siempre, sin depender del orden de inyección.
# Esto solo se inyecta cuando el reporte activo es Ajuste de Inventario, por
# lo que el resto de reportes conservan su título y su espacio superior.
_CSS_AJUSTE = """
<style>
/* ── AJUSTE DE INVENTARIO: subir todo el contenido al tope ───────────── */

/* 1) Topbar vacío en este reporte: oculto por completo. */
#nav-topbar { display: none !important; }

/* 2) Quitar el padding-top de 48px que el rail reserva para el topbar. */
html body .stApp { padding-top: 0 !important; }

/* 3) Padding superior mínimo del contenedor principal — OVERRIDE POR SECCIÓN
   (nivel 2 de 3; jerarquía en ARQUITECTURA.md). El prefijo `html body` NO es
   decorativo: le da más especificidad que el default global de estilos.py
   (1.5rem) para ganar SIEMPRE, sin depender del orden de inyección. Es el
   mecanismo estándar para overrides por sección en este proyecto.
   CAMBIADO: de 0.4rem a 0.15rem para subir el chip "Ajuste de Inventario". */
html body [data-testid="stMainBlockContainer"],
html body .stMainBlockContainer,
html body .block-container { padding-top: 0.85rem !important; }

/* 4) CLAVE: colapsar los contenedores "invisibles" que se apilan arriba
   (st.markdown que solo inyectan <style>, los iframes de overlay/inspector
   y el wrapper del topbar). Cada uno aporta un "gap" del bloque vertical y,
   sumados, forman la franja blanca. Ocultar su wrapper elimina ese gap SIN
   desactivar el CSS (un <style> aplica igual aunque esté en display:none). */
html body [data-testid="stElementContainer"]:has([data-testid="stMarkdown"] style),
html body [data-testid="stElementContainer"]:has([data-testid="stIFrame"]),
html body [data-testid="stElementContainer"]:has(#nav-topbar) {
    display: none !important;
}
</style>
"""


def inject_navegacion(reportes, reporte_activo, mostrar_inspector=False):
    """Dibuja el rail (botones nativos) + el título superior."""
    st.markdown(_CSS, unsafe_allow_html=True)

    # Ajuste de Inventario: sube el encabezado al tope (elimina la franja).
    if reporte_activo == "Ajuste de Inventario":
        st.markdown(_CSS_AJUSTE, unsafe_allow_html=True)

    # El título superior queda vacío en "Ajuste de Inventario"
    _titulo_topbar = "" if reporte_activo == "Ajuste de Inventario" else reporte_activo
    st.markdown(
        f'<div id="nav-topbar">{_titulo_topbar}</div>',
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
