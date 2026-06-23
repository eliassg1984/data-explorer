"""
Interfaz de usuario: CSS, botón flotante, tablas AgGrid y gráficos (OPTIMIZADO).
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from utils import _norm, buscar_columna, LOCALE_ES

# ===========================================================================
# MAPEO DE TAMAÑOS DE FUENTE
# ===========================================================================

TAM_FUENTE = {
    "Pequeño": 12,
    "Mediano": 14,
    "Grande": 17,
    "Muy grande": 20
}


# ===========================================================================
# CSS GLOBAL (CACHEADO)
# ===========================================================================

@st.cache_data
def get_css():
    """Retorna el CSS como string (cacheado para no reinyectar)."""
    return """
    <style>
    /* ============ PALETA DE COLORES ============ */
    :root {
        --bg-primary: #f8fafc;
        --bg-secondary: #ffffff;
        --bg-sidebar: #f1f5f9;
        --bg-card: #ffffff;
        --bg-hover: #e2e8f0;
        --text-primary: #1e293b;
        --text-secondary: #475569;
        --text-muted: #94a3b8;
        --accent: #3b82f6;
        --accent-hover: #2563eb;
        --accent-light: #dbeafe;
        --border: #e2e8f0;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
        --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.05), 0 2px 4px rgba(0, 0, 0, 0.03);
    }

    /* ============ HEADER NATIVO + ESPACIO SUPERIOR ============ */
    header[data-testid="stHeader"],
    .stAppHeader {
        background: transparent !important;
        border-bottom: none !important;
        box-shadow: none !important;
        height: 0 !important;
        min-height: 0 !important;
    }

    .stMainBlockContainer,
    [data-testid="stMainBlockContainer"],
    .block-container {
        padding-top: 1.5rem !important;
    }

    [data-testid="stSidebarHeader"] {
        height: 2rem !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }

    [data-testid="stIFrame"] {
        height: 0 !important;
        min-height: 0 !important;
        display: block !important;
    }
    [data-testid="stElementContainer"]:has([data-testid="stIFrame"]) {
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    [data-testid="stDecoration"] {
        display: none !important;
    }

    [data-testid="stToolbar"] {
        display: none !important;
    }

    /* ============ BOTÓN PARA EXPANDIR EL SIDEBAR ============ */
    [data-testid*="SidebarCollaps"],
    [data-testid="collapsedControl"],
    [data-testid*="xpandSidebar"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }

    /* ============ ESTILOS BASE ============ */
    [data-testid="stAppViewContainer"] { 
        background: var(--bg-primary); 
    }

    h1 { 
        margin-bottom: 0.2rem !important; 
        padding-top: 0 !important; 
    }

    [data-testid="stSidebar"] { 
        background: var(--bg-sidebar); 
        border-right: 1px solid var(--border); 
    }

    html, body, [class*="css"] { 
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
        color: var(--text-primary); 
    }

    h1 { 
        color: var(--text-primary) !important; 
        font-size: 1.6rem !important; 
        font-weight: 700 !important; 
    }

    h2, h3 { 
        color: var(--text-primary) !important; 
        font-weight: 600 !important; 
    }

    h4 { 
        color: var(--accent) !important; 
        font-weight: 600 !important; 
    }

    label { 
        color: var(--text-secondary) !important; 
        font-size: 0.78rem !important; 
        text-transform: uppercase; 
        font-weight: 600 !important;
    }

    /* ============ INPUTS Y BOTONES ============ */
    .stSelectbox > div > div, 
    .stMultiSelect > div > div,
    .stDateInput > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }

    .stSelectbox > div > div:hover,
    .stMultiSelect > div > div:hover {
        border-color: var(--accent) !important;
    }

    button[kind="secondary"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
    }

    button[kind="secondary"]:hover {
        background: var(--bg-hover) !important;
        border-color: var(--accent) !important;
    }

    button[kind="primary"] {
        background: var(--accent) !important;
        border: none !important;
        color: white !important;
        border-radius: 8px !important;
    }

    button[kind="primary"]:hover {
        background: var(--accent-hover) !important;
    }

    /* ============ EXPANDER ============ */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
    }

    .streamlit-expanderContent {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }

    /* ============ CAPTION Y ALERTAS ============ */
    .stCaption {
        color: var(--text-muted) !important;
    }

    .stWarning {
        background: #fef3c7 !important;
        border: 1px solid #fcd34d !important;
        color: #92400e !important;
        border-radius: 8px !important;
    }

    .stInfo {
        background: var(--accent-light) !important;
        border: 1px solid #93c5fd !important;
        color: #1e40af !important;
        border-radius: 8px !important;
    }

    .stError {
        background: #fee2e2 !important;
        border: 1px solid #fca5a5 !important;
        color: #991b1b !important;
        border-radius: 8px !important;
    }

    /* ============ SIDEBAR ============ */
    [data-testid="stSidebar"] .nav-link {
        background: #ffffff !important;
        color: #475569 !important;
        border: 1px solid #e2e8f0 !important;
    }

    [data-testid="stSidebar"] .nav-link:hover {
        background: #eff6ff !important;
        color: #2563eb !important;
        border-color: #93c5fd !important;
    }

    [data-testid="stSidebar"] .nav-link-selected {
        background: #3b82f6 !important;
        color: #ffffff !important;
        border-color: #3b82f6 !important;
    }

    /* ============ AGGRID - ANCHO COMPLETO ============ */
    .ag-root-wrapper {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    .ag-body-viewport {
        overflow-x: auto !important;
    }

    /* ============ CONTROL DE TAMAÑO EN SIDEBAR ============ */
    [data-testid="stSidebar"] .stSlider {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* ============ MÓVIL ============ */
    @media screen and (max-width: 768px) {
        header[data-testid="stHeader"] {
            background: transparent !important;
            box-shadow: none !important;
            border-bottom: none !important;
        }
        
        [data-testid="stAppViewContainer"] {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        
        [data-testid="stMain"] {
            padding: 0.5rem 0.5rem !important;
            margin-top: 0 !important;
        }
        
        .block-container,
        .stMainBlockContainer {
            padding: 0.5rem !important;
            margin-top: 0 !important;
            gap: 0 !important;
        }
        
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        
        [data-testid="stSidebar"] {
            max-height: 100vh;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            -webkit-overflow-scrolling: touch;
            background: var(--bg-sidebar) !important;
        }
        
        [data-testid="stSidebarUserContent"] {
            padding: 12px 8px !important;
        }
        
        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="stExpandSidebarButton"] button,
        [data-testid="collapsedControl"] button {
            width: 44px !important;
            height: 44px !important;
            min-height: 44px !important;
            padding: 8px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        
        h1 { 
            font-size: 1.3rem !important;
            margin-top: 0 !important;
            padding-top: 0.5rem !important;
        }
        h2 { font-size: 1.1rem !important; }
        h3 { font-size: 1rem !important; }
        label { font-size: 0.7rem !important; }
        
        .stApp { padding: 0 !important; }
        
        button { 
            min-height: 44px !important; 
            padding: 10px 16px !important;
            font-size: 0.9rem !important;
        }
        
        [data-testid="stSidebar"] { 
            width: 100% !important;
            max-width: 100% !important;
        }
    }

    /* =================================================================== */
    /* BOTONES TABLA / GRÁFICOS (segmented_control) — Opción 2 GRANDE azul  */
    /* =================================================================== */
    /* Separación entre los dos botones (cubrimos las variantes de Streamlit) */
    [data-testid="stSegmentedControl"] [data-baseweb="button-group"],
    [data-testid="stSegmentedControl"] [role="radiogroup"],
    [data-testid="stSegmentedControl"] [role="group"],
    [data-testid="stSegmentedControl"] > div,
    [data-testid="stButtonGroup"] > div {
        gap: 16px !important;
    }
    /* Base de cada botón — apuntamos por contenedor Y por kind del botón,    */
    /* así cae en alguna combinación según tu versión de Streamlit.          */
    [data-testid="stSegmentedControl"] button,
    [data-testid="stButtonGroup"] button,
    button[data-testid^="stBaseButton-segmented_control"],
    button[kind^="segmented_control"] {
        min-width: 190px !important;          /* MÁS GRANDE: ancho */
        padding: 14px 30px !important;        /* MÁS GRANDE: alto */
        margin: 0 !important;                 /* quita el -1px que los pega */
        font-size: 15px !important;
        font-weight: 600 !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 999px !important;      /* pill completo en ambos */
        transition: all .15s ease !important;
    }
    /* Icono Material un poco más grande dentro del botón */
    [data-testid="stSegmentedControl"] button [data-testid="stIconMaterial"],
    [data-testid="stSegmentedControl"] button p,
    button[kind^="segmented_control"] [data-testid="stIconMaterial"] {
        font-size: 20px !important;
    }
    /* ESTADO ACTIVO — Streamlit lo marca con kind="...Active"               */
    [data-testid="stSegmentedControl"] button[kind*="Active"],
    button[data-testid$="segmented_controlActive"],
    button[kind="segmented_controlActive"],
    [data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background: #eff6ff !important;
        color: #1e40af !important;
        border-color: #2563eb !important;
    }
    [data-testid="stSegmentedControl"] button[kind*="Active"] p,
    button[kind="segmented_controlActive"] p {
        color: #1e40af !important;
    }
    [data-testid="stSegmentedControl"] button:hover,
    button[kind^="segmented_control"]:hover {
        border-color: #93c5fd !important;
    }

    /* =================================================================== */
    /* BOTÓN FILTROS (popover) — a juego, grande y con contorno azul        */
    /* =================================================================== */
    [data-testid="stPopover"] button {
        min-width: 180px !important;
        padding: 14px 26px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 999px !important;
        transition: all .15s ease !important;
    }
    [data-testid="stPopover"] button:hover {
        border-color: #2563eb !important;
        background: #eff6ff !important;
        color: #1e40af !important;
    }
    </style>
    """


def inject_css():
    """Inyecta el CSS cacheado en la app."""
    st.markdown(get_css(), unsafe_allow_html=True)


# ===========================================================================
# OVERLAY DE ERRORES EN PANTALLA (para diagnóstico sin F12)
# ===========================================================================

def inject_error_overlay():
    """Captura los errores de JavaScript de la ventana principal y los muestra
    en un panel rojo fijo en pantalla. Así los errores quedan VISIBLES (también
    en capturas de pantalla), sin necesidad de abrir la consola del navegador.

    Otros scripts inyectados pueden reportar manualmente con:
        window.__logErr('mi mensaje')
    """
    components.html("""
    <script>
    (function(){
      var win = window.parent, doc = win.document;
      if (win.__errOverlayInit) return;
      win.__errOverlayInit = true;
      win.__errLog = [];
      function render(){
        var box = doc.getElementById('err-overlay');
        if (!win.__errLog.length){ if (box) box.remove(); return; }
        if (!box){
          box = doc.createElement('div');
          box.id = 'err-overlay';
          box.style.cssText = 'position:fixed;bottom:8px;right:8px;max-width:540px;'
            + 'max-height:42vh;overflow:auto;z-index:2147483647;background:#7f1d1d;'
            + 'color:#fff;font:12px/1.45 monospace;padding:10px 12px;border-radius:8px;'
            + 'box-shadow:0 4px 16px rgba(0,0,0,.4)';
          doc.body.appendChild(box);
        }
        var items = win.__errLog.slice(-12).map(function(e){
          return String(e).replace(/&/g,'&amp;').replace(/</g,'&lt;');
        }).join('<br>──<br>');
        box.innerHTML = '<b>⚠️ Errores JS (' + win.__errLog.length + ')</b>'
          + '<span style="float:right;cursor:pointer;opacity:.7" '
          + 'onclick="this.parentNode.remove()">✕</span><br>' + items;
      }
      function log(m){ win.__errLog.push(String(m).slice(0,400)); render(); }
      win.addEventListener('error', function(ev){
        log('[error] ' + (ev.message || ev.error) + (ev.filename ? ' @ ' + ev.filename : ''));
      });
      win.addEventListener('unhandledrejection', function(ev){
        log('[promise] ' + ((ev.reason && ev.reason.message) || ev.reason));
      });
      win.__logErr = log;
    })();
    </script>
    """, height=0)


def inject_grid_health_check():
    """Comprueba que el grid de AgGrid se haya montado de verdad e inyecta
    CSS de paginación directamente dentro del iframe para garantizar que los
    estilos pisen los del tema nativo (balham/material).

    Los errores de render DENTRO del iframe de AgGrid (p.ej. un cellRenderer/
    JsCode que devuelve un nodo DOM → React #31) no llegan a la ventana
    principal, así que aquí inspeccionamos el iframe: si existe pero no aparece
    '.ag-root-wrapper' tras unos segundos, lo reportamos al overlay de errores.
    (No revisa el nº de filas: un grid vacío legítimo SÍ monta el wrapper.)"""
    components.html("""
    <script>
    (function(){
      var win = window.parent, doc = win.document;
      var tries = 0, MAX = 20;

      // ── CSS de paginación Opción A (Minimalista) ─────────────────────
      // Se inyecta dentro del iframe de AgGrid para garantizar que pisa
      // los estilos del tema. El custom_css del componente no siempre tiene
      // suficiente especificidad frente a los estilos del tema balham/material.
      var PAG_CSS = [
        /* Quitar fondo morado/rayado de la status bar */
        '.ag-status-bar {',
        '  background: #f8fafc !important;',
        '  border-top: 1px solid #e2e8f0 !important;',
        '  color: #475569 !important;',
        '  padding: 4px 16px !important;',
        '  font-size: 12px !important;',
        '  background-image: none !important;',
        '  background-color: #f8fafc !important;',
        '}',
        '.ag-status-bar * {',
        '  background-image: none !important;',
        '}',
        '.ag-status-name-value { color: #475569 !important; font-size: 12px !important; }',
        '.ag-status-name-value-value { color: #1e293b !important; font-weight: 600 !important; }',

        /* Franja de paginación limpia */
        '.ag-paging-panel {',
        '  display: flex !important;',
        '  align-items: center !important;',
        '  justify-content: space-between !important;',
        '  background: #f8fafc !important;',
        '  background-image: none !important;',
        '  border-top: 1px solid #e2e8f0 !important;',
        '  padding: 8px 16px !important;',
        '  min-height: 44px !important;',
        '  font-size: 12px !important;',
        '  color: #64748b !important;',
        '}',

        /* Selector de tamaño a la izquierda */
        '.ag-paging-page-size { order: -1 !important; margin-right: auto !important; }',
        '.ag-paging-page-size .ag-label { color: #64748b !important; font-size: 12px !important; margin-right: 6px !important; }',
        '.ag-paging-page-size .ag-select, .ag-paging-page-size select {',
        '  border: 1px solid #e2e8f0 !important;',
        '  border-radius: 6px !important;',
        '  background: #fff !important;',
        '  color: #1e293b !important;',
        '  font-size: 12px !important;',
        '  padding: 2px 6px !important;',
        '}',

        /* Resumen "1 a 50 de 5,000" */
        '.ag-paging-row-summary-panel { color: #64748b !important; font-size: 12px !important; }',
        '.ag-paging-row-summary-panel-number { color: #1e293b !important; font-weight: 600 !important; }',

        /* Descripción de página "Página X de Y" */
        '.ag-paging-description { color: #64748b !important; font-size: 12px !important; }',

        /* Botones de navegación — base */
        '.ag-paging-button {',
        '  width: 28px !important; height: 28px !important;',
        '  border: 1px solid #e2e8f0 !important;',
        '  border-radius: 6px !important;',
        '  background: #fff !important;',
        '  color: #475569 !important;',
        '  font-size: 14px !important;',
        '  margin: 0 2px !important;',
        '  cursor: pointer !important;',
        '  display: inline-flex !important;',
        '  align-items: center !important;',
        '  justify-content: center !important;',
        '  transition: all 0.15s ease !important;',
        '  position: relative !important;',
        '}',
        /* Ocultar el icono SVG interno que no carga en el iframe */
        '.ag-paging-button span, .ag-paging-button .ag-icon {',
        '  display: none !important;',
        '}',
        /* Reemplazar con caracteres Unicode visibles via ::after */
        '.ag-paging-button[ref="btFirst"]::after  { content: "«" !important; }',
        '.ag-paging-button[ref="btPrevious"]::after { content: "‹" !important; }',
        '.ag-paging-button[ref="btNext"]::after   { content: "›" !important; }',
        '.ag-paging-button[ref="btLast"]::after   { content: "»" !important; }',
        '.ag-paging-button::after {',
        '  font-size: 16px !important;',
        '  line-height: 1 !important;',
        '  color: #475569 !important;',
        '}',
        '.ag-paging-button:hover:not(.ag-disabled) {',
        '  background: #eff6ff !important;',
        '  border-color: #93c5fd !important;',
        '}',
        '.ag-paging-button:hover:not(.ag-disabled)::after {',
        '  color: #2563eb !important;',
        '}',
        '.ag-paging-button.ag-disabled {',
        '  border-color: #f1f5f9 !important;',
        '  background: #f8fafc !important;',
        '  cursor: default !important;',
        '  opacity: 0.4 !important;',
        '}',

        /* ── Pestañas del panel lateral (Columnas/Filtros) ARRIBA y en  ── */
        /*    horizontal, en vez de verticales al costado.                  */
        /*    Se usa `order` para que los botones queden arriba sin         */
        /*    depender del orden del DOM (varía entre versiones de AgGrid). */
        '.ag-side-bar {',
        '  flex-direction: column !important;',
        '}',
        '.ag-side-bar .ag-side-buttons {',
        '  order: -1 !important;',
        '  flex: 0 0 auto !important;',
        '  display: flex !important;',
        '  flex-direction: row !important;',
        '  width: 100% !important;',
        '  border-right: none !important;',
        '  border-bottom: 1px solid #e2e8f0 !important;',
        '  padding: 0 !important;',
        '}',
        '.ag-side-bar .ag-tool-panel-wrapper {',
        '  order: 1 !important;',
        '  width: 100% !important;',
        '  flex: 1 1 auto !important;',
        '  height: auto !important;',
        '  min-height: 220px !important;',
        '}',
        '.ag-side-bar .ag-column-panel, .ag-side-bar .ag-column-select, .ag-side-bar .ag-filter-toolpanel {',
        '  flex: 1 1 auto !important;',
        '  height: auto !important;',
        '}',
        '.ag-side-bar .ag-side-button {',
        '  flex: 1 1 0 !important;',
        '  border-bottom: none !important;',
        '  border-right: 1px solid #e2e8f0 !important;',
        '}',
        '.ag-side-bar .ag-side-button:last-child {',
        '  border-right: none !important;',
        '}',
        '.ag-side-bar .ag-side-button-button {',
        '  writing-mode: horizontal-tb !important;',
        '  -webkit-writing-mode: horizontal-tb !important;',
        '  transform: none !important;',
        '  rotate: none !important;',
        '  display: flex !important;',
        '  flex-direction: row !important;',
        '  align-items: center !important;',
        '  justify-content: center !important;',
        '  width: 100% !important;',
        '  height: auto !important;',
        '  padding: 9px 6px !important;',
        '  gap: 6px !important;',
        '}',
        '.ag-side-bar .ag-side-button-label {',
        '  writing-mode: horizontal-tb !important;',
        '  -webkit-writing-mode: horizontal-tb !important;',
        '  transform: none !important;',
        '  rotate: none !important;',
        '  margin: 0 !important;',
        '  padding: 0 !important;',
        '  white-space: nowrap !important;',
        '  font-size: 12px !important;',
        '}',
        '.ag-side-bar .ag-side-button-icon-wrapper {',
        '  margin: 0 !important;',
        '  padding: 0 !important;',
        '}',
      ].join('\\n');

      function inyectarCSS(fdoc) {
        if (fdoc.getElementById('pag-custom-css')) return;
        var s = fdoc.createElement('style');
        s.id = 'pag-custom-css';
        s.textContent = PAG_CSS;
        fdoc.head.appendChild(s);
      }

      function check(){
        tries++;
        var frames = doc.querySelectorAll('iframe[src*="st_aggrid"]');
        if (frames.length === 0){
          if (tries < MAX) setTimeout(check, 500);
          return;
        }
        var montado = false;
        for (var i = 0; i < frames.length; i++){
          var d = null;
          try { d = frames[i].contentDocument; } catch(e){}
          if (!d) continue;
          if (d.querySelector('.ag-root-wrapper')) {
            montado = true;
            inyectarCSS(d);   // <── inyección directa dentro del iframe
          }
        }
        if (montado) return;
        if (tries < MAX){ setTimeout(check, 500); return; }
        if (win.__logErr) win.__logErr('Tabla no renderizada: el grid de AgGrid '
          + 'no se montó (posible cellRenderer/JsCode que devuelve un nodo DOM → React #31).');
      }
      setTimeout(check, 800);
    })();
    </script>
    """, height=0)


# ===========================================================================
# BOTÓN FLOTANTE PARA ABRIR/CERRAR EL SIDEBAR (CACHEADO)
# ===========================================================================

@st.cache_data
def get_sidebar_toggle_html():
    """Retorna el HTML del botón flotante (cacheado)."""
    return """
    <script>
    (function () {
        const doc = window.parent.document;
        const BTN_ID = 'mi-toggle-sidebar';

        function buscarControlNativo() {
            const sels = [
                '[data-testid="stSidebarCollapseButton"] button',
                '[data-testid="stSidebarCollapseButton"]',
                '[data-testid="stExpandSidebarButton"]',
                '[data-testid="collapsedControl"]',
                '[data-testid="stSidebarCollapsedControl"]',
                'button[kind="header"]',
                'section[data-testid="stSidebar"] button'
            ];
            for (const s of sels) {
                const el = doc.querySelector(s);
                if (el) return el;
            }
            return null;
        }

        function sidebarEstaAbierto() {
            const sb = doc.querySelector('section[data-testid="stSidebar"]');
            if (!sb) return false;
            const rect = sb.getBoundingClientRect();
            return rect.left > -100;
        }

        function toggleSidebar() {
            const nativo = buscarControlNativo();
            if (nativo) { nativo.click(); return; }

            const sb = doc.querySelector('section[data-testid="stSidebar"]');
            if (!sb) return;

            if (sidebarEstaAbierto()) {
                sb.style.transform = 'translateX(-110%)';
                sb.style.width = '0';
                sb.style.minWidth = '0';
                sb.style.overflow = 'hidden';
                sb.dataset.abierto = '';
            } else {
                sb.style.transform = 'none';
                sb.style.width = '21rem';
                sb.style.minWidth = '21rem';
                sb.style.visibility = 'visible';
                sb.style.overflow = 'visible';
                sb.style.zIndex = '1000';
                sb.dataset.abierto = '1';
            }
        }

        function asegurarBoton() {
            if (doc.getElementById(BTN_ID)) return;
            const b = doc.createElement('button');
            b.id = BTN_ID;
            b.innerHTML = '☰';
            b.title = 'Abrir / cerrar menú';
            b.style.cssText = [
                'position:fixed', 'top:12px', 'left:12px', 'z-index:1000000',
                'width:44px', 'height:44px', 'border-radius:10px',
                'border:1px solid #2563eb', 'background:#3b82f6', 'color:#ffffff',
                'font-size:20px', 'line-height:1', 'cursor:pointer',
                'box-shadow:0 2px 8px rgba(0,0,0,0.2)', 'display:flex',
                'align-items:center', 'justify-content:center', 'padding:0'
            ].join(';');
            b.onclick = toggleSidebar;
            doc.body.appendChild(b);
        }

        asegurarBoton();
        setInterval(asegurarBoton, 1000);
    })();
    </script>
    """


def inject_sidebar_toggle():
    """Inyecta el botón flotante cacheado."""
    components.html(get_sidebar_toggle_html(), height=0)


# ===========================================================================
# INSPECTOR DE ELEMENTOS — tooltips de identificación para capturas de pantalla
# ===========================================================================

def inject_element_inspector():
    """
    Inspector de elementos v2 — tooltip enriquecido al pasar el cursor.

    Muestra: tipo de widget, label, key Python, valor actual, y para AgGrid:
    nombre de columna, valor de celda, fila, tipo de zona (header/cell/panel).

    Activación : ?inspector=1 en la URL  o  Alt+I
    Desactivación: quitar parámetro     o  Alt+I de nuevo

    Elementos reconocidos:
        • Widgets Streamlit  → tipo | label | key | valor actual
        • Botones / Popover  → tipo | texto visible
        • Tabs / Expander    → tipo | título
        • Métricas           → label | valor | delta
        • Plotly             → título | ejes X e Y
        • AgGrid celda       → columna | valor | fila nº
        • AgGrid header      → columna | tipo de ordenación activa
        • AgGrid panel cols  → columna listada | si está visible o no
        • AgGrid panel filtros → nombre del filtro
        • AgGrid paginación  → página actual / total
        • AgGrid status bar  → texto del panel de estado
        • Rail de navegación → nombre del reporte
    """
    components.html("""
    <script>
    (function() {
        var win = window.parent;
        var doc = win.document;

        if (win.__inspectorInit) return;
        win.__inspectorInit = true;

        // ── Activación ───────────────────────────────────────────────────
        function inspectorActivo() {
            return new URL(win.location.href).searchParams.get('inspector') === '1';
        }

        // ── Tooltip multilínea ───────────────────────────────────────────
        var tip = doc.createElement('div');
        tip.id = 'el-inspector-tip';
        tip.style.cssText = [
            'position:fixed',
            'pointer-events:none',
            'z-index:2147483647',
            'background:#0f172a',
            'color:#e2e8f0',
            'font:12px/1.55 "Courier New",monospace',
            'padding:7px 11px',
            'border-radius:6px',
            'border:1px solid #3b82f6',
            'white-space:pre',
            'opacity:0',
            'transition:opacity 0.1s',
            'max-width:420px',
            'overflow:hidden',
            'box-shadow:0 3px 12px rgba(0,0,0,0.5)'
        ].join(';');
        doc.body.appendChild(tip);

        // ── Badge ON/OFF ─────────────────────────────────────────────────
        var badge = doc.createElement('div');
        badge.id = 'el-inspector-badge';
        badge.style.cssText = [
            'position:fixed','bottom:10px','left:72px','z-index:2147483646',
            'background:#1e40af','color:#fff',
            'font:600 11px/1 -apple-system,sans-serif',
            'padding:5px 10px','border-radius:20px','display:none',
            'align-items:center','gap:6px','box-shadow:0 2px 8px rgba(0,0,0,0.3)'
        ].join(';');
        badge.innerHTML = '🔍 Inspector ON &nbsp;<span style="opacity:.6;font-weight:400">Alt+I para desactivar</span>';
        doc.body.appendChild(badge);

        function actualizarBadge() {
            badge.style.display = inspectorActivo() ? 'flex' : 'none';
        }
        actualizarBadge();

        // ── Helpers ──────────────────────────────────────────────────────
        function txt(el) { return el ? el.textContent.trim() : ''; }

        function labelWidget(container) {
            var l = container.querySelector('label p');
            if (!l) l = container.querySelector('label');
            return l ? l.textContent.trim() : '';
        }

        function valorWidget(container, tipo) {
            if (tipo === 'stTextInput' || tipo === 'stNumberInput' || tipo === 'stTextArea') {
                var inp = container.querySelector('input, textarea');
                return inp ? inp.value : '';
            }
            if (tipo === 'stSelectbox') {
                var sel = container.querySelector('[data-baseweb="select"] [aria-selected="true"], ' +
                                                  '[data-baseweb="select"] span:first-child');
                return sel ? sel.textContent.trim() : '';
            }
            if (tipo === 'stMultiSelect') {
                var tags = container.querySelectorAll('[data-baseweb="tag"] span');
                if (!tags.length) return '(ninguno)';
                return Array.from(tags).map(function(t){ return t.textContent.trim(); })
                            .filter(Boolean).join(', ');
            }
            if (tipo === 'stSlider' || tipo === 'stSelectSlider') {
                var thumb = container.querySelector('[data-testid="stThumbValue"], ' +
                                                   '[aria-valuenow]');
                if (thumb) return thumb.getAttribute('aria-valuenow') || thumb.textContent.trim();
            }
            if (tipo === 'stDateInput') {
                var di = container.querySelector('input');
                return di ? di.value : '';
            }
            if (tipo === 'stCheckbox') {
                var cb = container.querySelector('input[type="checkbox"]');
                return cb ? (cb.checked ? 'marcado ✓' : 'desmarcado') : '';
            }
            return '';
        }

        // ── Intentar leer DOM interno del iframe de AgGrid ───────────────
        // (funciona mientras el iframe y el padre compartan origen o no haya
        //  bloqueo CORS estricto — en Streamlit local/cloud suele funcionar)
        function agGridInfo(mouseX, mouseY) {
            var frames = doc.querySelectorAll('iframe[src*="st_aggrid"], iframe[title*="aggrid"], iframe[title*="AgGrid"]');
            if (!frames.length) {
                // Buscar por posición si no hay atributo reconocible
                frames = doc.querySelectorAll('iframe');
            }
            for (var fi = 0; fi < frames.length; fi++) {
                var fr = frames[fi];
                var rect = fr.getBoundingClientRect();
                // ¿El cursor está dentro de este iframe?
                if (mouseX < rect.left || mouseX > rect.right ||
                    mouseY < rect.top  || mouseY > rect.bottom) continue;

                var fdoc = null;
                try { fdoc = fr.contentDocument; } catch(e) { continue; }
                if (!fdoc) continue;

                // Coordenadas relativas al iframe
                var rx = mouseX - rect.left;
                var ry = mouseY - rect.top;
                var inner = fdoc.elementFromPoint(rx, ry);
                if (!inner) continue;

                // ── Zona: celda de datos ──────────────────────────────────
                var cell = inner.closest('.ag-cell');
                if (cell) {
                    var colId   = cell.getAttribute('col-id') || '?';
                    var cellVal = cell.textContent.trim();
                    // Número de fila
                    var row = cell.closest('.ag-row');
                    var rowIdx = row ? (row.getAttribute('row-index') || '?') : '?';
                    // Tipo de fila (group, pinned-bottom = totales, normal)
                    var rowTipo = '';
                    if (row) {
                        if (row.classList.contains('ag-row-pinned')) rowTipo = ' [TOTAL]';
                        else if (row.classList.contains('ag-row-group')) rowTipo = ' [grupo]';
                    }
                    var lines = [
                        '📋 AgGrid › celda',
                        '  columna : ' + colId,
                        '  valor   : ' + (cellVal.length > 60 ? cellVal.slice(0,57)+'…' : cellVal),
                        '  fila nº : ' + rowIdx + rowTipo
                    ];
                    return lines.join('\n');
                }

                // ── Zona: header de columna ───────────────────────────────
                var hcell = inner.closest('.ag-header-cell');
                if (hcell) {
                    var hColId = hcell.getAttribute('col-id') || '?';
                    var hLabel = txt(hcell.querySelector('.ag-header-cell-text')) || hColId;
                    // Ordenación activa
                    var sortIcon = hcell.querySelector('.ag-sort-ascending-icon:not(.ag-hidden)');
                    var sortDesc = hcell.querySelector('.ag-sort-descending-icon:not(.ag-hidden)');
                    var sortInfo = sortIcon ? ' ↑ ascendente' : sortDesc ? ' ↓ descendente' : ' sin orden';
                    // ¿Tiene filtro activo?
                    var filtroActivo = hcell.querySelector('.ag-filter-active') ? ' 🔎 filtro activo' : '';
                    return [
                        '📋 AgGrid › encabezado',
                        '  col-id  : ' + hColId,
                        '  nombre  : ' + hLabel,
                        '  orden   :' + sortInfo + filtroActivo
                    ].join('\n');
                }

                // ── Zona: panel lateral — lista de columnas ───────────────
                var colItem = inner.closest('.ag-column-select-column');
                if (colItem) {
                    var colName = txt(colItem.querySelector('.ag-column-select-column-label')) || '?';
                    var visible = colItem.querySelector('input[type="checkbox"]');
                    var visStr  = visible ? (visible.checked ? 'visible ✓' : 'oculta') : '?';
                    return [
                        '📋 AgGrid › panel columnas',
                        '  columna : ' + colName,
                        '  estado  : ' + visStr
                    ].join('\n');
                }

                // ── Zona: panel lateral — filtros ─────────────────────────
                var filtItem = inner.closest('.ag-filter-toolpanel-instance');
                if (filtItem) {
                    var filtName = txt(filtItem.querySelector('.ag-filter-toolpanel-instance-header-text')) || '?';
                    return [
                        '📋 AgGrid › panel filtros',
                        '  filtro  : ' + filtName
                    ].join('\n');
                }

                // ── Zona: barra de paginación ─────────────────────────────
                var pag = inner.closest('.ag-paging-panel');
                if (pag) {
                    var pagTxt = pag.textContent.replace(/\s+/g, ' ').trim();
                    return [
                        '📋 AgGrid › paginación',
                        '  ' + pagTxt.slice(0, 80)
                    ].join('\n');
                }

                // ── Zona: status bar ──────────────────────────────────────
                var status = inner.closest('.ag-status-bar');
                if (status) {
                    return [
                        '📋 AgGrid › barra de estado',
                        '  ' + status.textContent.replace(/\s+/g, ' ').trim().slice(0, 80)
                    ].join('\n');
                }

                // ── Zona: botones del menú de columna (pin, sort, etc.) ───
                var menuItem = inner.closest('.ag-menu-option');
                if (menuItem) {
                    return '📋 AgGrid › menú: ' + txt(menuItem.querySelector('.ag-menu-option-text'));
                }

                // ── Fallback: dentro del iframe pero zona desconocida ─────
                if (fdoc.querySelector('.ag-root-wrapper')) {
                    return '📋 AgGrid › zona: ' + (inner.className || inner.tagName).toString().slice(0, 60);
                }
            }
            return null;
        }

        // ── Detección de elementos Streamlit ─────────────────────────────
        var WIDGET_MAP = {
            'stTextInput':    { ico: '✏️',  tipo: 'text_input'    },
            'stNumberInput':  { ico: '🔢',  tipo: 'number_input'  },
            'stTextArea':     { ico: '📝',  tipo: 'text_area'     },
            'stSelectbox':    { ico: '📌',  tipo: 'selectbox'     },
            'stMultiSelect':  { ico: '☑️',  tipo: 'multiselect'   },
            'stSlider':       { ico: '🎚️',  tipo: 'slider'        },
            'stSelectSlider': { ico: '🎚️',  tipo: 'select_slider' },
            'stDateInput':    { ico: '📅',  tipo: 'date_input'    },
            'stTimeInput':    { ico: '🕐',  tipo: 'time_input'    },
            'stCheckbox':     { ico: '✅',  tipo: 'checkbox'      },
        };

        function labelDe(el, mouseX, mouseY) {

            // 1. Widgets con label, key y valor
            for (var testid in WIDGET_MAP) {
                var container = el.closest('[data-testid="' + testid + '"]');
                if (!container) continue;
                var meta  = WIDGET_MAP[testid];
                var lbl   = labelWidget(container);
                var val   = valorWidget(container, testid);
                // Intentar extraer el key de Streamlit del atributo aria o del id del input
                var inp   = container.querySelector('input, select, textarea');
                var keyAt = inp ? (inp.getAttribute('aria-label') || inp.id || '') : '';
                // Filtrar keys internos de Streamlit (tienen formato "st-xx…")
                if (/^st-[a-z0-9]+$/i.test(keyAt)) keyAt = '';
                var lines = [meta.ico + ' ' + meta.tipo];
                if (lbl)   lines.push('  label : ' + lbl);
                if (keyAt) lines.push('  key   : ' + keyAt);
                if (val)   lines.push('  valor : ' + (val.length > 55 ? val.slice(0,52)+'…' : val));
                return lines.join('\n');
            }

            // 2. Botón de Streamlit (con data-testid en el key si existe)
            var btn = el.closest('[data-testid="baseButton-secondary"], [data-testid="baseButton-primary"], button[kind]');
            if (btn) {
                var btxt = btn.innerText.trim().replace(/\n/g, ' ');
                var bkey = btn.getAttribute('data-testid') || '';
                var blines = ['🔘 button'];
                if (btxt) blines.push('  texto : ' + btxt);
                if (bkey && bkey !== 'baseButton-secondary' && bkey !== 'baseButton-primary')
                    blines.push('  testid: ' + bkey);
                return blines.join('\n');
            }

            // 3. Popover
            var popover = el.closest('[data-testid="stPopover"]');
            if (popover) {
                var pbtn = popover.querySelector('button');
                var ptxt = pbtn ? pbtn.innerText.trim() : '?';
                var popen = popover.querySelector('[data-testid="stPopoverBody"]') ? ' (abierto)' : ' (cerrado)';
                return '🔽 popover\n  texto : ' + ptxt + '\n  estado: ' + popen.trim();
            }

            // 4. Tab activa / inactiva
            var tabBtn = el.closest('[data-baseweb="tab"]');
            if (tabBtn) {
                var isActive = tabBtn.getAttribute('aria-selected') === 'true';
                return '📑 tab\n  nombre: ' + tabBtn.innerText.trim() +
                       '\n  estado: ' + (isActive ? 'activa ✓' : 'inactiva');
            }

            // 5. Expander
            var expander = el.closest('[data-testid="stExpander"]');
            if (expander) {
                var etxt2 = expander.querySelector('summary p, summary span, .streamlit-expanderHeader p');
                var eopen = expander.querySelector('[data-testid="stExpanderDetails"]');
                var eIsOpen = eopen ? (eopen.style.display !== 'none' && eopen.style.visibility !== 'hidden') : false;
                return '📂 expander\n  título: ' + (etxt2 ? etxt2.textContent.trim() : '?') +
                       '\n  estado: ' + (eIsOpen ? 'abierto' : 'cerrado');
            }

            // 6. Métrica — label, valor y delta
            var metric = el.closest('[data-testid="stMetric"]');
            if (metric) {
                var mlbl2  = metric.querySelector('[data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"]');
                var mval   = metric.querySelector('[data-testid="stMetricValue"]');
                var mdelta = metric.querySelector('[data-testid="stMetricDelta"]');
                var mlines = ['📊 metric'];
                if (mlbl2)  mlines.push('  label : ' + mlbl2.textContent.trim());
                if (mval)   mlines.push('  valor : ' + mval.textContent.trim());
                if (mdelta) mlines.push('  delta : ' + mdelta.textContent.trim());
                return mlines.join('\n');
            }

            // 7. Plotly — título + ejes
            var plotly = el.closest('.js-plotly-plot, [data-testid="stPlotlyChart"]');
            if (plotly) {
                var ptitle2 = plotly.querySelector('.gtitle, .g-gtitle');
                var xTitle  = plotly.querySelector('.g-xtitle');
                var yTitle  = plotly.querySelector('.g-ytitle');
                var plines  = ['📈 plotly'];
                plines.push('  título: ' + (ptitle2 ? ptitle2.textContent.trim() : '(sin título)'));
                if (xTitle) plines.push('  eje X : ' + xTitle.textContent.trim());
                if (yTitle) plines.push('  eje Y : ' + yTitle.textContent.trim());
                return plines.join('\n');
            }

            // 8. AgGrid — delegamos al lector de iframe
            var agEl = el.closest('[data-testid="stAgGrid"], .ag-root-wrapper');
            if (agEl || el.tagName === 'IFRAME') {
                var agInfo = agGridInfo(mouseX, mouseY);
                if (agInfo) return agInfo;
                return '📋 AgGrid tabla';
            }

            // 9. Rail de navegación
            var railIcon = el.closest('.rail-icon');
            if (railIcon) {
                var rname   = railIcon.getAttribute('data-tooltip') || railIcon.innerText.trim();
                var rActive = railIcon.classList.contains('active');
                return '🧭 nav\n  reporte: ' + rname + '\n  estado : ' + (rActive ? 'activo ✓' : 'inactivo');
            }

            // 10. Caption / aviso
            var caption = el.closest('[data-testid="stCaptionContainer"]');
            if (caption) {
                return 'ℹ️ caption\n  ' + caption.textContent.trim().slice(0, 80);
            }

            return null;
        }

        // ── Resaltado ────────────────────────────────────────────────────
        var elActual = null;
        function resaltarEl(el, etiqueta) {
            if (elActual) { elActual.style.outline = ''; elActual.style.outlineOffset = ''; }
            if (el && etiqueta) {
                el.style.outline = '2px solid #3b82f6';
                el.style.outlineOffset = '2px';
                elActual = el;
            } else { elActual = null; }
        }

        // ── Mousemove sobre el documento padre ───────────────────────────
        doc.addEventListener('mousemove', function(e) {
            if (!inspectorActivo()) {
                tip.style.opacity = '0';
                resaltarEl(null, null);
                return;
            }

            var el = e.target;
            var etiqueta = null;
            var cursor = el;

            // Intentar primero AgGrid (iframe) con las coordenadas del mouse
            var agInfo = agGridInfo(e.clientX, e.clientY);
            if (agInfo) {
                etiqueta = agInfo;
                // Resaltar el iframe como bloque
                var agFrame = doc.querySelector('iframe[src*="st_aggrid"], [data-testid="stAgGrid"] iframe');
                if (!agFrame) {
                    var iframes = doc.querySelectorAll('iframe');
                    for (var fi=0; fi<iframes.length; fi++) {
                        var r = iframes[fi].getBoundingClientRect();
                        if (e.clientX >= r.left && e.clientX <= r.right &&
                            e.clientY >= r.top  && e.clientY <= r.bottom) {
                            agFrame = iframes[fi]; break;
                        }
                    }
                }
                if (agFrame) resaltarEl(agFrame, etiqueta);
            } else {
                // Recorrer DOM hasta encontrar widget (máx 12 niveles)
                for (var i = 0; i < 12 && cursor && cursor !== doc.body; i++) {
                    etiqueta = labelDe(cursor, e.clientX, e.clientY);
                    if (etiqueta) { el = cursor; break; }
                    cursor = cursor.parentElement;
                }
                if (etiqueta) resaltarEl(el, etiqueta);
                else resaltarEl(null, null);
            }

            if (etiqueta) {
                tip.textContent = etiqueta;
                tip.style.opacity = '1';
                var x = e.clientX + 16;
                var y = e.clientY - 10;
                // Calcular alto real del tooltip (multilínea)
                var tw = tip.offsetWidth  || 260;
                var th = tip.offsetHeight || 80;
                if (x + tw > win.innerWidth  - 8) x = e.clientX - tw - 16;
                if (y + th > win.innerHeight - 8) y = e.clientY - th - 10;
                if (y < 6) y = 6;
                tip.style.left = x + 'px';
                tip.style.top  = y + 'px';
            } else {
                tip.style.opacity = '0';
            }
        }, true);

        doc.addEventListener('mouseleave', function() {
            tip.style.opacity = '0';
            resaltarEl(null, null);
        });

        // ── Alt+I para activar/desactivar ────────────────────────────────
        doc.addEventListener('keydown', function(e) {
            if (e.altKey && (e.key === 'i' || e.key === 'I')) {
                var url = new URL(win.location.href);
                if (url.searchParams.get('inspector') === '1') {
                    url.searchParams.delete('inspector');
                } else {
                    url.searchParams.set('inspector', '1');
                }
                win.history.replaceState({}, '', url.toString());
                actualizarBadge();
                if (!inspectorActivo()) {
                    tip.style.opacity = '0';
                    resaltarEl(null, null);
                }
            }
        });

        var _push = win.history.pushState.bind(win.history);
        win.history.pushState = function() { _push.apply(win.history, arguments); actualizarBadge(); };
        win.addEventListener('popstate', actualizarBadge);

    })();
    </script>
    """, height=0, scrolling=False)


# ===========================================================================
# FUNCIÓN: AGGRID DESKTOP — con formato financiero y diseño mejorado
# ===========================================================================

def renderizar_aggrid_desktop(df_grid, grupos_sel, cols_mostrar, reporte, font_px=14, cols_visibles=None):
    """Renderiza la tabla AgGrid en vista desktop con formato financiero y diseño premium.

    cols_visibles: lista de columnas que arrancan VISIBLES. El resto se oculta
    por defecto y el usuario las activa desde la barra lateral (panel "Columnas").
    Si es None, se muestran todas.
    """

    # Envolver cabeceras en varias líneas (white-space: normal) SOLO para este
    # reporte. El resto de tablas mantiene la cabecera en una sola línea.
    envolver_cabeceras = (reporte == "Inventario Valorizado")

    # Quitar fondos de color (píldoras de stock, filas teñidas y barra del
    # valorizado) SOLO en este reporte. Se conserva todo el formato y la función.
    quitar_fondos = (reporte == "Inventario Valorizado")

    # Variaciones E y F SOLO para este reporte:
    #   E → agrupación en fila completa (groupDisplayType="groupRows")
    #   F → tema Material (Google design) con cabecera clara y acento rojo
    # Ambas son puramente visuales/de disposición: NO tocan totales, formato S/,
    # panel lateral, barra de estado, ni ninguna otra funcionalidad del grid.
    es_inventario = (reporte == "Inventario Valorizado")

    # ─────────────────────────────────────────────────────────────────
    # REORDENAR COLUMNAS (Producto, Stock, Precio, Valorizado)
    # ─────────────────────────────────────────────────────────────────
    col_producto   = buscar_columna(df_grid, "Nombre Producto", "producto", "descripcion")
    col_stock      = buscar_columna(df_grid, "Stock al dia", "Stock al Dia", "stock")
    col_precio_ord = buscar_columna(df_grid, "Precio Promedio", "precio promedio", "precio")
    col_valorizado = buscar_columna(df_grid, "Valorizado total", "valorizado")

    prioridad = []
    for c in (col_producto, col_stock, col_precio_ord, col_valorizado):
        if c and c in df_grid.columns and c not in prioridad:
            prioridad.append(c)
    if prioridad:
        resto = [c for c in df_grid.columns if c not in prioridad]
        df_grid = df_grid[prioridad + resto]

    # Máximo del valorizado para escalar las barras de datos
    max_valorizado = 1.0
    if col_valorizado and col_valorizado in df_grid.columns:
        try:
            m = float(df_grid[col_valorizado].max())
            if m > 0:
                max_valorizado = m
        except Exception:
            pass

    gb = GridOptionsBuilder.from_dataframe(df_grid)
    _opciones_col_def = dict(
        resizable=True, filter=True, sortable=True,
        editable=False, enableRowGroup=True,
        enablePivot=True, enableValue=True,
        minWidth=100,
        tooltipValueGetter=JsCode("function(params){ return params.value; }"),
    )
    if envolver_cabeceras:
        # wrapHeaderText  → el texto de la cabecera salta de línea.
        # autoHeaderHeight → el alto de la cabecera se ajusta automáticamente.
        _opciones_col_def["wrapHeaderText"] = True
        _opciones_col_def["autoHeaderHeight"] = True
    gb.configure_default_column(**_opciones_col_def)

    # ── Fuente mono para columnas numéricas genéricas ──
    mono_style = JsCode("""
        function(params) {
            return { fontFamily: "'Courier New', Courier, monospace" };
        }
    """)

    # ── PÍLDORAS DE COLOR PARA EL STOCK (no mancha la fila entera) ──
    stock_cell_style = JsCode("""
        function(params) {
            if (params.value === null || params.value === undefined) return {};
            if (params.node && params.node.rowPinned) {
                return { fontWeight: '700', color: '#1e3a5f' };
            }
            var v = Number(params.value);
            var base = { 
                fontFamily: "'Courier New', Courier, monospace", 
                fontWeight: '700', 
                textAlign: 'right',
                padding: '2px 10px' 
            };
            // Stock negativo (rojo)
            if (v < 0) {
                return Object.assign({}, base, { 
                    backgroundColor: '#fee2e2', 
                    color: '#991b1b', 
                    borderRadius: '20px' 
                });
            }
            // Stock en 0 (amarillo)
            if (v === 0) {
                return Object.assign({}, base, { 
                    backgroundColor: '#fef3c7', 
                    color: '#92400e', 
                    borderRadius: '20px' 
                });
            }
            // Stock bajo < 10 (naranja)
            if (v < 10) {
                return Object.assign({}, base, { 
                    backgroundColor: '#ffedd5', 
                    color: '#9a3412', 
                    borderRadius: '20px' 
                });
            }
            // Stock normal (verde oscuro)
            return Object.assign({}, base, { color: '#065f46' });
        }
    """)

    # ── Versión PLANA del stock: sin fondos de color, conserva mono/negrita/
    #    alineación a la derecha (solo cambia el color → texto oscuro neutro). ──
    stock_cell_style_plano = JsCode("""
        function(params) {
            if (params.value === null || params.value === undefined) return {};
            if (params.node && params.node.rowPinned) {
                return { fontWeight: '700', color: '#1e3a5f' };
            }
            return {
                fontFamily: "'Courier New', Courier, monospace",
                fontWeight: '700',
                textAlign: 'right',
                padding: '2px 10px',
                color: '#1e293b'
            };
        }
    """)

    # ── BARRA DE DATOS GRUESA PARA EL VALORIZADO ──
    valorizado_bar_style = JsCode(f"""
        function(params) {{
            var base = {{
                fontFamily: "'Courier New', Courier, monospace",
                color: '#1e3a5f',
                fontWeight: '600',
                textAlign: 'right',
                paddingRight: '12px'
            }};
            if (params.value === null || params.value === undefined) {{
                return base;
            }}
            if (params.node && (params.node.group || params.node.rowPinned)) {{
                return Object.assign({{}}, base, {{ fontWeight: '800' }});
            }}
            var maxv = {max_valorizado};
            var num = Number(params.value);
            if (isNaN(num)) return base;
            var pct = maxv > 0 ? Math.max(0, Math.min(100, (num / maxv) * 100)) : 0;
            return Object.assign({{}}, base, {{
                backgroundImage: 'linear-gradient(to right, #bfdbfe 0%, #bfdbfe ' + pct + '%, transparent ' + pct + '%, transparent 100%)',
                backgroundRepeat: 'no-repeat',
                backgroundSize: '100% 80%',
                backgroundPosition: 'left center'
            }});
        }}
    """)

    # ── Versión PLANA del valorizado: sin barra de datos, conserva mono/negrita/
    #    alineación a la derecha y el formato S/ (solo se quita el fondo). ──
    valorizado_plano = JsCode("""
        function(params) {
            var base = {
                fontFamily: "'Courier New', Courier, monospace",
                color: '#1e3a5f',
                fontWeight: '600',
                textAlign: 'right',
                paddingRight: '12px'
            };
            if (params.node && (params.node.group || params.node.rowPinned)) {
                return Object.assign({}, base, { fontWeight: '800' });
            }
            return base;
        }
    """)

    # Elegimos el estilo con o sin fondos de color según el reporte.
    _stock_style = stock_cell_style_plano if quitar_fondos else stock_cell_style
    _valor_style = valorizado_plano       if quitar_fondos else valorizado_bar_style

    # ── Formateo por tipo de columna ──
    for c in df_grid.columns:
        if not pd.api.types.is_numeric_dtype(df_grid[c]):
            continue

        gb.configure_column(c, filter="agNumberColumnFilter")

        norm_c        = _norm(c)
        es_stock      = "stock" in norm_c
        es_valorizado = "valorizado" in norm_c
        es_precio     = any(k in norm_c for k in ("precio", "promedio", "unitario", "costo"))
        es_valor      = any(k in norm_c for k in ("valorizado", "total", "importe", "monto"))

        if es_stock:
            gb.configure_column(
                c, aggFunc="sum", type=["numericColumn"],
                cellStyle=_stock_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 0, maximumFractionDigits: 0 });
                    }
                """),
            )
        elif es_valorizado:
            gb.configure_column(
                c, aggFunc="sum", type=["numericColumn"],
                minWidth=170,
                cellStyle=_valor_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return 'S/ ' + Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                """),
            )
        elif es_precio:
            gb.configure_column(
                c, aggFunc="avg", type=["numericColumn"],
                cellStyle=mono_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return 'S/ ' + Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                """),
            )
        elif es_valor:
            gb.configure_column(
                c, aggFunc="sum", type=["numericColumn"],
                cellStyle=mono_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return 'S/ ' + Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                """),
            )
        else:
            gb.configure_column(
                c, aggFunc="sum", type=["numericColumn"],
                cellStyle=mono_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 0, maximumFractionDigits: 2 });
                    }
                """),
            )

    # ── Fijar columna Producto a la izquierda (más ancha para evitar cortes) ──
    if col_producto and col_producto in df_grid.columns and col_producto not in grupos_sel:
        gb.configure_column(col_producto, pinned="left", minWidth=300)

    # ── Columnas ocultas por defecto ──
    if cols_visibles is not None:
        visibles_norm = {_norm(c) for c in cols_visibles}
        # Salvaguarda: si NINGUNA columna del grid coincide con la lista de
        # "visibles", no ocultamos nada. Ocultarlas todas dejaría la tabla
        # completamente en blanco (cabecera vacía incluida). En ese caso es
        # preferible mostrar todas las columnas.
        hay_match = any(_norm(c) in visibles_norm for c in df_grid.columns)
        if hay_match:
            for c in df_grid.columns:
                if c in grupos_sel:
                    continue
                if _norm(c) not in visibles_norm:
                    gb.configure_column(c, hide=True)

    row_h    = max(28, min(60, font_px + 12))
    header_h = max(30, min(62, font_px + 14))

    # ── Fila de totales al pie ──
    cols_valor  = [c for c in df_grid.columns
                   if pd.api.types.is_numeric_dtype(df_grid[c]) and
                   any(k in _norm(c) for k in ("valorizado", "total", "importe", "monto"))]
    cols_precio = [c for c in df_grid.columns
                   if pd.api.types.is_numeric_dtype(df_grid[c]) and
                   any(k in _norm(c) for k in ("precio", "promedio", "unitario", "costo"))]
    cols_stock  = [c for c in df_grid.columns
                   if pd.api.types.is_numeric_dtype(df_grid[c]) and "stock" in _norm(c)]

    primera_col = list(df_grid.columns)[0] if len(df_grid.columns) > 0 else None
    fila_totales = {}
    for c in df_grid.columns:
        if c in cols_valor:
            fila_totales[c] = round(float(df_grid[c].sum()), 2)
        elif c in cols_precio:
            fila_totales[c] = round(float(df_grid[c].mean()), 2)
        elif c in cols_stock:
            fila_totales[c] = round(float(df_grid[c].sum()), 0)
        elif c == primera_col:
            fila_totales[c] = "▶ TOTAL"
        else:
            fila_totales[c] = None

    # ── Estilo de fila para el semáforo (totales y alertas) ──
    # Si quitar_fondos está activo, NO se aplican los tintes por fila (rosa/
    # crema); se usa la rama de abajo, que solo estiliza la fila de totales.
    if col_stock and col_stock in df_grid.columns and not quitar_fondos:
        _sf = str(col_stock).replace("\\", "\\\\").replace('"', '\\"')
        get_row_style = JsCode(f"""
            function(params) {{
                if (params.node.rowPinned === 'bottom') {{
                    return {{ fontWeight:'700', backgroundColor:'#dbeafe', color:'#1e3a5f',
                              borderTop:'2px solid #3b82f6', fontSize:'13px' }};
                }}
                if (params.node.group || !params.data) return null;
                var s = params.data["{_sf}"];
                if (s === null || s === undefined || s === '') return null;
                var v = Number(s);
                if (isNaN(v)) return null;
                if (v === 0) return {{ backgroundColor:'#fef2f2' }};
                if (v < 10)  return {{ backgroundColor:'#fffbeb' }};
                return null;
            }}
        """)
    elif es_inventario:
        # Fila de totales en paleta azul (igual que el resto de reportes).
        get_row_style = JsCode("""
            function(params) {
                if (params.node.rowPinned === 'bottom') {
                    return { fontWeight:'700', backgroundColor:'#dbeafe', color:'#1e3a5f',
                             borderTop:'2px solid #3b82f6', fontSize:'13px' };
                }
            }
        """)
    else:
        get_row_style = JsCode("""
            function(params) {
                if (params.node.rowPinned === 'bottom') {
                    return { fontWeight:'700', backgroundColor:'#dbeafe', color:'#1e3a5f',
                             borderTop:'2px solid #3b82f6', fontSize:'13px' };
                }
            }
        """)

    # ── Configuración general del Grid ──
    opciones_grid = {
        "autoGroupColumnDef": {"minWidth": 200},
        "localeText": LOCALE_ES,
        "suppressSizeToFit": True,            # <--- CLAVE: evita que el grid se encoja y rompa el borde
        "sideBar": {
            "toolPanels": [
                {
                    "id": "columns",
                    "labelDefault": "Columnas",
                    "labelKey": "columns",
                    "iconKey": "columns",
                    "toolPanel": "agColumnsToolPanel",
                    "toolPanelParams": {
                        "suppressRowGroups": True,
                        "suppressValues": True,
                        "suppressPivots": True,
                        "suppressPivotMode": True,
                        "suppressColumnFilter": False,
                        "suppressColumnSelectAll": False,
                        "suppressColumnExpandAll": True,
                    },
                },
                {
                    "id": "filters",
                    "labelDefault": "Filtros",
                    "labelKey": "filters",
                    "iconKey": "filter",
                    "toolPanel": "agFiltersToolPanel",
                },
            ],
            "defaultToolPanel": "columns",
            "position": "right",
        },
        "rowHeight": row_h,
        "headerHeight": header_h,
        "pinnedBottomRowData": [fila_totales],
        "cellSelection": True,
        "tooltipShowDelay": 300,
        # Barra de estado eliminada a pedido (la franja inferior "Filas: N").
        "getRowStyle": get_row_style,
        # Eliminamos los 'sizeColumnsToFit' para que las columnas no se encojan
        "onGridSizeChanged": JsCode("function(params) { /* No auto-fit */ }"),
        "onFirstDataRendered": JsCode("function(params) { /* No auto-fit */ }"),
    }

    agrupar_on = bool(grupos_sel)
    if agrupar_on:
        for c in grupos_sel:
            if c in df_grid.columns:
                gb.configure_column(c, rowGroup=True, hide=True)

        if es_inventario:
            # ── Variación E: grupos en FILA COMPLETA (groupRows) ──
            # En vez de columnas de grupo, cada grupo es una fila ancha con su
            # nombre, el conteo de hijos y el subtotal del valorizado.
            # La fila de totales (pinnedBottom) y las agregaciones del resto de
            # columnas siguen funcionando igual.
            opciones_grid["groupDisplayType"] = "groupRows"

            _col_val_js = ""
            if col_valorizado and col_valorizado in df_grid.columns:
                _col_val_js = str(col_valorizado).replace("\\", "\\\\").replace('"', '\\"')

            opciones_grid["groupRowRendererParams"] = {
                "innerRenderer": JsCode(f"""
                    function(params) {{
                        if (!params.node || !params.node.group) return params.value;
                        var nombre = (params.value == null ? '' : params.value);
                        var n = params.node.allChildrenCount;
                        var extra = '';
                        var colVal = "{_col_val_js}";
                        if (colVal && params.node.aggData &&
                            params.node.aggData[colVal] !== null &&
                            params.node.aggData[colVal] !== undefined) {{
                            var v = Number(params.node.aggData[colVal]);
                            if (!isNaN(v)) {{
                                extra = ' · S/ ' + v.toLocaleString('es-PE', {{
                                    minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                            }}
                        }}
                        return '<span style="font-weight:600;color:#1e293b">' + nombre +
                               '</span> <span style="color:#64748b;font-weight:400">(' +
                               n + ')' + extra + '</span>';
                    }}
                """)
            }
        else:
            opciones_grid["groupDisplayType"] = "multipleColumns"

        opciones_grid["groupDefaultExpanded"] = 0
        opciones_grid["pivotMode"] = False
    else:
        opciones_grid["pivotMode"] = False

    if envolver_cabeceras:
        # Reservamos altura para 2 líneas de cabecera. (autoHeaderHeight la
        # ajusta sola si el navegador lo soporta; si no, este alto fijo basta.)
        opciones_grid["headerHeight"] = int(font_px * 2.5 + 20)

    gb.configure_grid_options(**opciones_grid)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
    grid_options = gb.build()

    # ── CSS personalizado (CON EL PANEL LATERAL ESTILIZADO) ──
    custom_css = {
        ".ag-root-wrapper": {
            "background-color": "#ffffff",
            "border": "1px solid #0f172a",          # Borde azul petróleo oscuro
            "border-radius": "10px !important",     # Redondeo elegante
            "overflow": "hidden !important",        # CLAVE: Cierra el marco perfectamente
            "box-shadow": "0 4px 12px rgba(0,0,0,0.06)",
            "width": "100% !important",
        },
        ".ag-header": {
            "background-color": "#0f172a !important",
            "border-bottom": "none !important",
        },
        ".ag-header-cell": {
            "background-color": "#0f172a !important",
        },
        ".ag-header-cell-text": {
            "color": "#f8fafc !important",
            "font-weight": "700",
            "font-size": f"{font_px}px",
            "letter-spacing": "0.03em",
            "text-transform": "uppercase",
        },
        ".ag-header-icon": {
            "color": "#93c5fd !important",
        },
        ".ag-row": {
            "border-bottom": "1px solid #f1f5f9",
            "color": "#1e293b",
        },
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd": {"background-color": "#f8fafc"},
        ".ag-row-hover": {"background-color": "#eff6ff !important"},
        ".ag-cell": {"color": "#334155", "font-size": f"{font_px}px"},
        ".ag-row-pinned": {
            "background-color": "#dbeafe !important",
            "font-weight": "700 !important",
            "border-top": "2px solid #3b82f6 !important",
            "color": "#1e3a5f !important",
            "font-size": f"{font_px + 1}px !important",
        },
        # ── Opción A Minimalista: paginación limpia en una sola franja ──
        ".ag-paging-panel": {
            "display": "flex !important",
            "align-items": "center !important",
            "justify-content": "space-between !important",
            "color": "#64748b",
            "background-color": "#f8fafc",
            "border-top": "1px solid #e2e8f0",
            "padding": "8px 16px !important",
            "border-bottom-left-radius": "10px !important",
            "border-bottom-right-radius": "10px !important",
            "font-size": "12px !important",
            "min-height": "44px !important",
        },
        # Selector de tamaño de página
        ".ag-paging-panel .ag-paging-page-size": {
            "order": "-1 !important",
            "margin-right": "auto !important",
        },
        ".ag-paging-panel .ag-paging-page-size .ag-label": {
            "color": "#64748b !important",
            "font-size": "12px !important",
            "margin-right": "6px !important",
        },
        ".ag-paging-panel .ag-paging-page-size select, "
        ".ag-paging-panel .ag-paging-page-size .ag-select": {
            "border": "1px solid #e2e8f0 !important",
            "border-radius": "6px !important",
            "background": "#ffffff !important",
            "color": "#1e293b !important",
            "font-size": "12px !important",
            "padding": "2px 6px !important",
        },
        # Botones de navegación: estilo pill
        ".ag-paging-button": {
            "width": "28px !important",
            "height": "28px !important",
            "border": "1px solid #e2e8f0 !important",
            "background": "#ffffff !important",
            "border-radius": "6px !important",
            "color": "#475569 !important",
            "font-size": "13px !important",
            "cursor": "pointer !important",
            "display": "flex !important",
            "align-items": "center !important",
            "justify-content": "center !important",
            "margin": "0 2px !important",
            "transition": "all 0.15s ease !important",
        },
        ".ag-paging-button:hover:not(.ag-disabled)": {
            "background": "#eff6ff !important",
            "border-color": "#93c5fd !important",
            "color": "#2563eb !important",
        },
        ".ag-paging-button.ag-disabled": {
            "color": "#cbd5e1 !important",
            "border-color": "#f1f5f9 !important",
            "background": "#f8fafc !important",
            "cursor": "default !important",
        },
        # Texto "X a Y de Z"
        ".ag-paging-row-summary-panel": {
            "color": "#64748b !important",
            "font-size": "12px !important",
            "margin-left": "auto !important",
        },
        ".ag-paging-row-summary-panel-number": {
            "color": "#1e293b !important",
            "font-weight": "600 !important",
        },
        # Status bar limpia, sin el fondo morado/rayado de AgGrid
        ".ag-status-bar": {
            "background-color": "#f8fafc !important",
            "border-top": "1px solid #e2e8f0 !important",
            "color": "#475569 !important",
            "padding": "4px 16px !important",
            "font-size": "12px !important",
            "min-height": "0 !important",
        },
        ".ag-status-name-value": {
            "color": "#475569 !important",
            "font-size": "12px !important",
        },
        ".ag-status-name-value-value": {
            "color": "#1e293b !important",
            "font-weight": "600 !important",
        },
        # ========== ESTILOS PARA EL PANEL LATERAL DE COLUMNAS (CORREGIDO) ==========
        ".ag-side-bar": {
            "background-color": "#ffffff",
            "border-left": "1px solid #e2e8f0 !important",
            "border-top-right-radius": "10px !important",
            "border-bottom-right-radius": "10px !important",
            "border-bottom": "1px solid #0f172a !important",
        },
        ".ag-side-bar .ag-side-buttons": {
            "border-right": "1px solid #e2e8f0 !important",
        },
        ".ag-side-button": {
            "background-color": "#f8fafc !important",
            "border": "none !important",
            "border-bottom": "1px solid #e2e8f0 !important",
            "color": "#475569 !important",
        },
        ".ag-side-button:hover": {
            "background-color": "#dbeafe !important",
            "color": "#2563eb !important",
        },
        ".ag-side-button.ag-selected": {
            "background-color": "#2563eb !important",
            "color": "#ffffff !important",
            "box-shadow": "inset 0 0 0 1px #3b82f6",
        },
        ".ag-tool-panel-wrapper": {
            "background-color": "#ffffff !important",
            "border": "none !important",
        },
        ".ag-column-select-panel": {
            "padding": "10px !important",
            "background-color": "#ffffff !important",
        },
        ".ag-column-tool-panel .ag-column-panel": {
            "border": "none !important",
        },
        ".ag-column-tool-panel .ag-column-select-all": {
            "padding": "10px 0 !important",
            "border-bottom": "1px solid #e2e8f0 !important",
        },
        ".ag-column-panel .ag-header-cell-text": {
            "color": "#1e293b !important", 
            "font-weight": "600 !important",
        },
        ".ag-filter-toolpanel-body": {
            "padding": "10px !important",
            "background-color": "#ffffff !important",
        },

        # ================================================================
        # PANEL DE COLUMNAS COMO INTERRUPTORES (Opción B)
        # Cada columna es una fila con: etiqueta a la izquierda + toggle a
        # la derecha. El checkbox nativo de AgGrid se "disfraza" de switch.
        # ================================================================
        # Fila de cada columna: aire, divisor fino y etiqueta a la izquierda.
        ".ag-column-select-column": {
            "display": "flex !important",
            "align-items": "center !important",
            "padding": "10px 12px !important",
            "border-bottom": "0.5px solid #f1f5f9 !important",
        },
        # La etiqueta va primero (order -1) y empuja el toggle a la derecha.
        ".ag-column-select-column-label": {
            "order": "-1 !important",
            "margin-right": "auto !important",
            "color": "#475569 !important",
            "font-size": "12.5px !important",
        },
        # Resaltar la columna activa (navegadores con :has()).
        ".ag-column-select-column:has(.ag-checked) .ag-column-select-column-label": {
            "color": "#1e293b !important",
            "font-weight": "500 !important",
        },
        # Ocultamos la manijita de arrastre para un look limpio
        # (igual puedes reordenar arrastrando las cabeceras de la tabla).
        ".ag-column-select-column .ag-drag-handle": {
            "display": "none !important",
        },
        # ── El checkbox convertido en riel del interruptor ──
        ".ag-column-select-column .ag-checkbox-input-wrapper": {
            "width": "36px !important",
            "height": "20px !important",
            "border-radius": "999px !important",
            "background": "#e2e8f0 !important",
            "border": "none !important",
            "box-shadow": "none !important",
            "position": "relative !important",
            "transition": "background .15s ease !important",
        },
        # ── La perilla blanca (reemplaza el check del icono) ──
        ".ag-column-select-column .ag-checkbox-input-wrapper::after": {
            "content": "'' !important",
            "position": "absolute !important",
            "top": "2px !important",
            "left": "2px !important",
            "width": "16px !important",
            "height": "16px !important",
            "border-radius": "50% !important",
            "background": "#ffffff !important",
            "color": "transparent !important",
            "box-shadow": "0 1px 2px rgba(0,0,0,0.25) !important",
            "transition": "left .15s ease !important",
        },
        # ── Estado encendido: riel azul + perilla a la derecha ──
        ".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked": {
            "background": "#2563eb !important",
        },
        ".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked::after": {
            "content": "'' !important",
            "left": "18px !important",
        },
        # El input transparente sigue cubriendo el switch para poder clicar.
        ".ag-column-select-column .ag-checkbox-input": {
            "cursor": "pointer !important",
        },
    }

    # ── Cabeceras envueltas en varias líneas (solo Inventario Valorizado) ──
    if envolver_cabeceras:
        # OJO: el tema Balham trae 'white-space: nowrap' con más especificidad,
        # por eso aquí va con !important; si no, gana el tema y sale «…».
        custom_css[".ag-header-cell-text"].update({
            "white-space": "normal !important",   # fuerza el salto de línea
            "overflow": "visible !important",     # quita el recorte
            "text-overflow": "clip !important",   # elimina los puntos «…»
            "line-height": "1.2 !important",
            "word-break": "break-word",
        })
        # El contenedor del texto también debe permitir varias líneas.
        custom_css[".ag-header-cell-label"] = {
            "white-space": "normal !important",
            "overflow": "visible !important",
            "align-items": "center",
        }

    # ── Inventario Valorizado: tema Material con cabecera clara y acento AZUL ──
    # Reemplaza el subrayado rojo de marca por el azul de la paleta principal,
    # manteniendo todo el formato S/, totales, panel lateral y barra de estado.
    tema_grid = "balham"
    if es_inventario:
        tema_grid = "material"
        custom_css[".ag-root-wrapper"].update({
            "background-color": "#f8fafc !important",   # mismo fondo que la página
            "border": "none !important",                # sin borde
            "box-shadow": "none !important",            # sin sombra
            "border-radius": "4px !important",          # conserva el redondeo suave (opcional, si lo quieres quitar pon 0px)
        })
        custom_css[".ag-header"].update({
            "background-color": "#ffffff !important",
            "border-bottom": "2px solid #3b82f6 !important",   # azul en lugar de rojo
        })   
        custom_css[".ag-tool-panel-horizontal-resize"] = {
            "width": "8px !important",
            "background-color": "#e2e8f0",
            "cursor": "col-resize",
        }
        custom_css[".ag-header-cell"].update({
            "background-color": "#ffffff !important",
        })
        custom_css[".ag-header-cell-text"].update({
            "color": "#5f6368 !important",
            "font-weight": "600",
            "letter-spacing": "0.05em",
            "text-transform": "uppercase",
        })
        custom_css[".ag-header-icon"].update({
            "color": "#9aa0a6 !important",
        })
        custom_css[".ag-row-pinned"].update({
            "background-color": "#dbeafe !important",          # azul claro en lugar de rosado
            "border-top": "2px solid #3b82f6 !important",      # azul en lugar de rojo
            "color": "#1e3a5f !important",                     # azul oscuro en lugar de rojo oscuro
        })

        # ── Scrollbar azul personalizada (solo Inventario Valorizado) ──
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar"] = {
            "width": "8px",
        }
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-track"] = {
            "background": "#e2e8f0",
            "border-radius": "4px",
        }
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-thumb"] = {
            "background": "#3b82f6",
            "border-radius": "4px",
        }
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-thumb:hover"] = {
            "background": "#2563eb",
        }

        # ── Opción 3: panel lateral como TARJETA DESPEGADA (solo Inventario) ──
        # En vez de una franja pegada al borde de la tabla, el panel se separa
        # con un espacio a la izquierda y tiene su propio borde redondeado,
        # un tono claro y una sombra suave. `overflow: hidden` en el panel hace
        # que el contenido (pestañas y lista) se recorte a las esquinas
        # redondeadas. Los márgenes lo despegan de la tabla y de la paginación.
        custom_css[".ag-side-bar"].update({
            "background-color": "#f6f8fb !important",
            "border": "1px solid #dbe2ec !important",
            "border-left": "1px solid #dbe2ec !important",
            "border-bottom": "1px solid #dbe2ec !important",
            "border-radius": "10px !important",
            "border-top-right-radius": "10px !important",
            "border-bottom-right-radius": "10px !important",
            "box-shadow": "0 4px 14px rgba(15,23,42,0.08) !important",
            "margin": "4px 6px 6px 12px !important",
            "overflow": "hidden !important",
        })
        # Franja de pestañas con un tono un poco más marcado que el cuerpo.
        custom_css[".ag-side-bar .ag-side-buttons"].update({
            "background-color": "#eef2f7 !important",
            "border-bottom": "1px solid #dbe2ec !important",
        })

        # ── Borde azul para el área de datos (solo Inventario Valorizado) ──
        custom_css[".ag-root"] = {
            "border": "2px solid #3b82f6",
            "border-radius": "6px",
        }

    AgGrid(
        df_grid.head(5000), gridOptions=grid_options, height=600,
        theme=tema_grid, custom_css=custom_css,
        fit_columns_on_grid_load=False, allow_unsafe_jscode=True,
        enable_enterprise_modules=True, key=f"grid_{reporte}",
    )

    inject_grid_health_check()


# ===========================================================================
# FUNCIÓN: AGGRID MÓVIL (ANCHO COMPLETO)
# ===========================================================================

def renderizar_aggrid_movil(df_grid, columnas_fijas, reporte, font_px=14):
    """Renderiza la tabla AgGrid optimizada para vista móvil."""
    envolver_cabeceras = (reporte == "Inventario Valorizado")

    gb = GridOptionsBuilder.from_dataframe(df_grid)
    _opciones_col_def = dict(
        resizable=True, sortable=True, filter=True,
        editable=False, groupable=False, enableRowGroup=False,
        enablePivot=False, menuTabs=["filterMenuTab", "generalMenuTab", "columnsMenuTab"],
    )
    if envolver_cabeceras:
        _opciones_col_def["wrapHeaderText"] = True
        _opciones_col_def["autoHeaderHeight"] = True
    gb.configure_default_column(**_opciones_col_def)
    
    for i, col in enumerate(df_grid.columns):
        if i < columnas_fijas:
            gb.configure_column(col, pinned="left")
        if pd.api.types.is_numeric_dtype(df_grid[col]):
            af = "avg" if ("precio" in _norm(col) or "promedio" in _norm(col)) else "sum"
            gb.configure_column(col, aggFunc=af, type=["numericColumn"],
                                valueFormatter="x == null ? '' : x.toLocaleString()")
    
    row_h = max(28, min(60, font_px + 12))
    header_h = max(30, min(62, font_px + 14))
    
    opciones_grid = {
        "localeText": LOCALE_ES,
        "suppressColumnVirtualisation": True,
        "rowHeight": row_h,
        "headerHeight": header_h,
        "animateRows": False,
        "sideBar": False,
        "suppressContextMenu": False,
        "pagination": True,
        "paginationAutoPageSize": False,
        "paginationPageSize": 25,
    }
    
    if envolver_cabeceras:
        opciones_grid["headerHeight"] = int(font_px * 2.5 + 20)

    gb.configure_grid_options(**opciones_grid)
    grid_options = gb.build()
    
    custom_css = {
        ".ag-root-wrapper": {"background-color": "#ffffff", "border": "1px solid #e2e8f0", "border-radius": "8px", "width": "100% !important"},
        ".ag-header": {"background-color": "#f1f5f9", "border-bottom": "2px solid #3b82f6"},
        ".ag-header-cell-text": {"color": "#1e293b", "font-weight": "700", "font-size": f"{font_px}px"},
        ".ag-row": {"color": "#334155", "border-color": "#e2e8f0"},
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd": {"background-color": "#f8fafc"},
        ".ag-row-hover": {"background-color": "#eff6ff !important"},
        ".ag-cell": {"color": "#334155", "font-size": f"{font_px}px"},
        ".ag-paging-panel": {"color": "#64748b", "background-color": "#f8fafc", "border-top": "1px solid #e2e8f0", "font-size": "0.75rem"},
        ".ag-menu": {"background-color": "#ffffff", "color": "#1e293b", "border": "1px solid #e2e8f0"},
        ".ag-pinned-left-header": {"box-shadow": "3px 0 8px rgba(0,0,0,0.08)"},
        ".ag-pinned-left-cols-container": {"box-shadow": "3px 0 8px rgba(0,0,0,0.08)"},
    }

    if envolver_cabeceras:
        custom_css[".ag-header-cell-text"].update({
            "white-space": "normal !important",
            "overflow": "visible !important",
            "text-overflow": "clip !important",
            "line-height": "1.2 !important",
            "word-break": "break-word",
        })
        custom_css[".ag-header-cell-label"] = {
            "white-space": "normal !important",
            "overflow": "visible !important",
            "align-items": "center",
        }

    AgGrid(
        df_grid.head(3000), gridOptions=grid_options, height=380,
        theme="balham", custom_css=custom_css,
        fit_columns_on_grid_load=False, allow_unsafe_jscode=True,
        enable_enterprise_modules=True, key=f"grid_movil_{reporte}",
    )

    inject_grid_health_check()


# ===========================================================================
# FUNCIÓN: DASHBOARD DE GRÁFICOS
# ===========================================================================

def renderizar_graficos(df_f, es_movil=False):
    """Renderiza todos los gráficos del dashboard."""
    
    col_area = buscar_columna(df_f, "Nombre Area", "area")
    col_familia = buscar_columna(df_f, "Nombre Familia", "familia")
    col_producto = buscar_columna(df_f, "Nombre Producto", "producto")
    col_stock = buscar_columna(df_f, "Stock al dia", "stock")
    col_precio = buscar_columna(df_f, "Precio Promedio", "precio promedio")
    col_valorizado = buscar_columna(df_f, "Valorizado total", "valorizado")
    
    if not col_producto or not col_stock or not col_precio or not col_valorizado:
        st.warning("Faltan columnas esenciales (Producto, Stock, Precio, Valorizado). No se pueden generar gráficos.")
        return
    
    total_val = df_f[col_valorizado].sum()
    total_prod = len(df_f[col_producto].unique())
    stock_bajo = len(df_f[df_f[col_stock] < 10])
    stock_cero = len(df_f[df_f[col_stock] == 0])
    areas = len(df_f[col_area].unique()) if col_area else 0
    precio_prom = df_f[col_precio].mean()
    
    if es_movil:
        cols_kpi = st.columns(2)
        with cols_kpi[0]:
            st.metric("💰 Total Valorizado", f"S/ {total_val:,.0f}")
        with cols_kpi[1]:
            st.metric("📦 Productos", total_prod)
        
        cols_kpi2 = st.columns(2)
        with cols_kpi2[0]:
            st.metric("⚠️ Stock Bajo", stock_bajo, delta=f"{stock_cero} sin stock", delta_color="inverse")
        with cols_kpi2[1]:
            st.metric("💵 Precio Prom.", f"S/ {precio_prom:,.2f}")
    else:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("💰 Total Valorizado", f"S/ {total_val:,.0f}")
        with col2:
            st.metric("📦 Productos", total_prod, delta=f"{areas} áreas" if areas else None)
        with col3:
            st.metric("⚠️ Stock Bajo (<10)", stock_bajo, delta=f"{stock_cero} sin stock", delta_color="inverse")
        with col4:
            st.metric("💵 Precio Prom.", f"S/ {precio_prom:,.2f}")
        with col5:
            rotacion = total_val / total_prod if total_prod > 0 else 0
            st.metric("📊 Valor/Prod", f"S/ {rotacion:,.0f}")
    
    def crear_scatter(df, col_precio, col_stock, col_valorizado, col_producto, col_area=None, height=450):
        fig = go.Figure()
        
        valores = df[col_valorizado].fillna(0).values
        max_val = max(valores.max(), 1)
        
        if col_area:
            for area in df[col_area].unique():
                df_area = df[df[col_area] == area].copy()
                if df_area.empty:
                    continue
                
                sizes = df_area[col_valorizado].fillna(0).values
                sizes_norm = np.clip((sizes / max_val) * 35 + 5, 5, 40)
                
                fig.add_trace(go.Scatter(
                    x=df_area[col_precio],
                    y=df_area[col_stock],
                    mode='markers',
                    name=str(area),
                    marker=dict(
                        size=sizes_norm,
                        opacity=0.7,
                        sizemode='diameter'
                    ),
                    text=df_area[col_producto],
                    hovertemplate='<b>%{text}</b><br>Precio: S/ %{x:,.2f}<br>Stock: %{y:,.0f}<extra></extra>'
                ))
        else:
            sizes = df[col_valorizado].fillna(0).values
            sizes_norm = np.clip((sizes / max_val) * 35 + 5, 5, 40)
            
            fig.add_trace(go.Scatter(
                x=df[col_precio],
                y=df[col_stock],
                mode='markers',
                name='Productos',
                marker=dict(
                    size=sizes_norm,
                    opacity=0.7,
                    color='#3b82f6',
                    sizemode='diameter'
                ),
                text=df[col_producto],
                hovertemplate='<b>%{text}</b><br>Precio: S/ %{x:,.2f}<br>Stock: %{y:,.0f}<extra></extra>'
            ))
        
        fig.add_hline(y=10, line_dash="dash", line_color="red", 
                     annotation_text="Stock mínimo")
        
        if not col_area and height >= 400:
            fig.add_vline(x=df[col_precio].mean(), line_dash="dash", 
                         line_color="blue",
                         annotation_text=f"Precio prom. (S/ {df[col_precio].mean():.2f})")
        
        fig.update_layout(
            title='Relación Precio vs Stock (tamaño = valorizado)',
            xaxis_title='Precio Promedio (S/)',
            yaxis_title='Stock',
            height=height,
            paper_bgcolor='#f8fafc',
            plot_bgcolor='#ffffff',
            showlegend=True if col_area else False
        )
        
        return fig
    
    if es_movil:
        tab1, tab2 = st.tabs(["🗺️ Mapa", "📊 Análisis"])
        
        with tab1:
            if col_area:
                try:
                    path = [col_area]
                    if col_familia:
                        path.append(col_familia)
                    
                    fig_tree = px.treemap(
                        df_f, path=path, values=col_valorizado,
                        color=col_valorizado, color_continuous_scale='blues',
                        title='Valorización por Área y Familia'
                    )
                    fig_tree.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=350)
                    st.plotly_chart(fig_tree, use_container_width=True)
                except Exception as e:
                    st.warning(f"No se pudo generar el treemap: {str(e)}")
            else:
                st.info("Se necesita columna de Área para el treemap")
            
            with st.expander("🏆 Top 10 Productos"):
                try:
                    top_10 = df_f.nlargest(10, col_valorizado)
                    fig_top = px.bar(
                        top_10, x=col_valorizado, y=col_producto,
                        orientation='h',
                        title='Top 10 por Valorización',
                        text=col_valorizado,
                        color_discrete_sequence=['#3b82f6']
                    )
                    fig_top.update_traces(texttemplate='S/ %{text:,.0f}', textposition='outside')
                    fig_top.update_layout(height=350)
                    st.plotly_chart(fig_top, use_container_width=True)
                except Exception as e:
                    st.warning(f"No se pudo generar el top 10: {str(e)}")
        
        with tab2:
            try:
                fig_scatter = crear_scatter(
                    df_f, col_precio, col_stock, col_valorizado, 
                    col_producto, col_area, height=350
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            except Exception as e:
                st.warning(f"No se pudo generar el scatter plot: {str(e)}")
            
            if col_area:
                with st.expander("☀️ Distribución Jerárquica"):
                    try:
                        path = [col_area]
                        if col_familia:
                            path.append(col_familia)
                        
                        fig_sun = px.sunburst(
                            df_f, path=path, values=col_valorizado,
                            color=col_valorizado, color_continuous_scale='blues',
                            title='Distribución Jerárquica del Valor'
                        )
                        fig_sun.update_layout(height=350)
                        st.plotly_chart(fig_sun, use_container_width=True)
                    except Exception as e:
                        st.warning(f"No se pudo generar el sunburst: {str(e)}")
            
            with st.expander("📈 Distribución de Precios"):
                try:
                    fig_hist = px.histogram(
                        df_f, x=col_precio, nbins=20,
                        title='Distribución de Precios Promedio',
                        color_discrete_sequence=['#3b82f6']
                    )
                    fig_hist.update_layout(height=300)
                    st.plotly_chart(fig_hist, use_container_width=True)
                except Exception as e:
                    st.warning(f"No se pudo generar el histograma: {str(e)}")
    
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "🗺️ Mapa de Valor", "📊 Análisis Precio/Stock",
            "🏆 Top Productos", "📈 Distribución"
        ])
        
        with tab1:
            col_a, col_b = st.columns(2)
            
            with col_a:
                if col_area:
                    try:
                        path = [col_area]
                        if col_familia:
                            path.append(col_familia)
                        
                        fig_tree = px.treemap(
                            df_f, path=path, values=col_valorizado,
                            color=col_valorizado, color_continuous_scale='blues',
                            title='Valorización por Área y Familia'
                        )
                        fig_tree.update_layout(margin=dict(l=10, r=10, t=30, b=10))
                        st.plotly_chart(fig_tree, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Error en treemap: {str(e)}")
                else:
                    st.info("Se necesita columna de Área")
            
            with col_b:
                if col_area:
                    try:
                        path = [col_area]
                        if col_familia:
                            path.append(col_familia)
                        
                        fig_sun = px.sunburst(
                            df_f, path=path, values=col_valorizado,
                            color=col_valorizado, color_continuous_scale='blues',
                            title='Distribución Jerárquica'
                        )
                        fig_sun.update_layout(margin=dict(l=10, r=10, t=30, b=10))
                        st.plotly_chart(fig_sun, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Error en sunburst: {str(e)}")
        
        with tab2:
            try:
                fig_scatter = crear_scatter(
                    df_f, col_precio, col_stock, col_valorizado, 
                    col_producto, col_area, height=450
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            except Exception as e:
                st.warning(f"Error en scatter: {str(e)}")
            
            with st.expander("🔍 Productos con stock bajo y alto valor"):
                try:
                    outliers = df_f[(df_f[col_stock] < 10) & 
                                   (df_f[col_valorizado] > df_f[col_valorizado].median())]
                    if not outliers.empty:
                        st.warning(f"⚠️ {len(outliers)} productos con stock bajo y alto valor")
                        cols_out = [col_producto, col_stock, col_valorizado]
                        if col_area:
                            cols_out.insert(1, col_area)
                        st.dataframe(
                            outliers[cols_out].sort_values(col_valorizado, ascending=False).head(10),
                            use_container_width=True
                        )
                    else:
                        st.success("✅ No hay productos críticos")
                except Exception as e:
                    st.warning(f"Error en outliers: {str(e)}")
        
        with tab3:
            col_a, col_b = st.columns(2)
            
            with col_a:
                try:
                    top_15 = df_f.nlargest(15, col_valorizado)
                    fig_top = px.bar(
                        top_15, x=col_valorizado, y=col_producto,
                        orientation='h', color=col_stock,
                        color_continuous_scale=['#ef4444', '#f59e0b', '#10b981'],
                        title='Top 15 Productos (color = stock)',
                        text=col_valorizado
                    )
                    fig_top.update_traces(texttemplate='S/ %{text:,.0f}', textposition='outside')
                    fig_top.update_layout(height=400)
                    st.plotly_chart(fig_top, use_container_width=True)
                except Exception as e:
                    st.warning(f"Error en top 15: {str(e)}")
            
            with col_b:
                if col_area:
                    try:
                        area_val = df_f.groupby(col_area)[col_valorizado].sum().reset_index()
                        area_val = area_val.sort_values(col_valorizado, ascending=True)
                        
                        fig_area = px.bar(
                            area_val, x=col_valorizado, y=col_area,
                            orientation='h', color=col_valorizado,
                            color_continuous_scale='blues',
                            title='Ranking por Área',
                            text=col_valorizado
                        )
                        fig_area.update_traces(texttemplate='S/ %{text:,.0f}', textposition='outside')
                        fig_area.update_layout(height=400)
                        st.plotly_chart(fig_area, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Error en ranking: {str(e)}")
        
        with tab4:
            col_a, col_b = st.columns(2)
            
            with col_a:
                try:
                    if col_area:
                        fig_box = px.box(
                            df_f, x=col_area, y=col_precio,
                            color=col_area,
                            title='Distribución de Precios por Área',
                            color_discrete_sequence=px.colors.qualitative.Set2
                        )
                    else:
                        fig_box = px.box(
                            df_f, y=col_precio,
                            title='Distribución de Precios',
                            color_discrete_sequence=['#3b82f6']
                        )
                    fig_box.update_layout(height=400)
                    st.plotly_chart(fig_box, use_container_width=True)
                except Exception as e:
                    st.warning(f"Error en box plot: {str(e)}")
            
            with col_b:
                try:
                    fig_hist = px.histogram(
                        df_f, x=col_precio, nbins=30,
                        title='Distribución de Precios',
                        color_discrete_sequence=['#3b82f6']
                    )
                    fig_hist.update_layout(height=400)
                    st.plotly_chart(fig_hist, use_container_width=True)
                except Exception as e:
                    st.warning(f"Error en histograma: {str(e)}")
            
            with st.expander("📋 Resumen por Área"):
                if col_area:
                    try:
                        resumen = df_f.groupby(col_area).agg(
                            Productos=(col_producto, 'nunique'),
                            Stock_Promedio=(col_stock, 'mean'),
                            Precio_Promedio=(col_precio, 'mean'),
                            Valorizado_Total=(col_valorizado, 'sum')
                        ).reset_index()
                        resumen['% del Total'] = (resumen['Valorizado_Total'] / total_val * 100).round(1)
                        
                        st.dataframe(
                            resumen.style.format({
                                'Stock_Promedio': '{:,.0f}',
                                'Precio_Promedio': 'S/ {:.2f}',
                                'Valorizado_Total': 'S/ {:,.0f}',
                                '% del Total': '{:.1f}%'
                            }).background_gradient(subset=['Valorizado_Total'], cmap='Blues'),
                            use_container_width=True
                        )
                    except Exception as e:
                        st.warning(f"Error en resumen: {str(e)}")
