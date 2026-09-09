"""estilos._88_cargando - "esto se esta recalculando": velo + circulo sobre el
grafico o la tabla que el servidor esta rehaciendo (2026-09-09).

POR QUE EXISTE. Esta app esconde el indicador nativo de Streamlit
(`[data-testid="stStatusWidget"]`, el de la esquina superior derecha) en
`_70_chrome.py`, y con razon: trae el boton "Stop" y el cromo de Community
Cloud. Pero al esconderlo se fue TODA la senal de "estoy trabajando", y los
reruns de esta app no son instantaneos. Medido en el navegador el 2026-09-09,
sobre Compras > Proveedores con los datos reales de R2:

    gesto                                    hay elementos stale desde/hasta
    --------------------------------------   -------------------------------
    Top 5 -> Top 20 (chips del ranking)      414 ms  ->  5.229 ms
    Top 20 -> Top 10                       1.090 ms  ->  6.329 ms
    clic en un item del rail (solo scroll)   522 ms  ->  3.388 ms

Durante esos 3-6 segundos el grafico y la tabla siguen mostrando el dato
VIEJO, sin ninguna marca. El usuario lo reporto como "cuando una tabla o
grafico esta cargando quiero un circulo o algo que haga referencia a cargar".

DE DONDE SALE EL "ESTA CARGANDO". No hace falta JS ni un flag de Python:
Streamlit ya marca cada elemento pendiente de rehacer con `data-stale="true"`
sobre su `stElementContainer`. Y lo hace CON PRECISION de fragment - en el
bundle, la funcion que lo decide devuelve true solo para los elementos del
fragment que esta corriendo, asi que tocar un chip de Proveedores no marca
los graficos de Producto. Lo unico que Streamlit hace hoy con ese atributo es
pasarlo a emotion, y el estilo resultante es `opacity: 1` (medido): nadie lo
estaba usando para nada visible.

POR QUE SOLO GRAFICOS Y TABLAS. En un rerun se marcan ~24 contenedores
(titulos, chips, botones, KPIs). Ponerle un circulo a cada uno seria una
feria. El velo va sobre las dos cosas que el usuario mira y que ademas
MIENTEN mientras estan stale, porque siguen dibujando el dato anterior: la
figura Plotly y la grilla AgGrid.

EL RETARDO NO ES DECORACION. `carga_entrar` no arranca hasta los 400 ms: un
rerun que se resuelve antes no llega a mostrar nada, y asi el indicador
significa "esto esta tardando" en vez de parpadear en cada clic. Es el mismo
criterio -y casi el mismo numero- que el `DELAY_SECS = 0.5` que `st.spinner`
trae adentro por lo mismo.

COSTE DEL `:has()`, medido ANTES de escribirlo. Un `iframe` no admite
pseudo-elementos, asi que el velo de la tabla no se puede colgar de la grilla
misma: hay que subir al contenedor, y para eso hace falta `:has()`. Medido en
esta pagina (111 contenedores, 24 cambiando a la vez, media de 10 ciclos):

    marcar 24 contenedores como stale, sin esta regla ....  0,02 ms
    marcar 24 contenedores como stale, con esta regla ....  2,28 ms

2,3 ms dos veces por rerun contra reruns de 3.000-6.000 ms. Se paga.

OJO (regla #198): este modulo NO lleva `<style>` propio. `_00_base` abre la
etiqueta y `_99_movil` la cierra; lo del medio va pelado. Un `<style>`
anidado es sintaxis invalida y el parser descarta este modulo Y todos los
siguientes.
"""

CSS = """
    /* =================================================================== */
    /* CARGANDO — velo + círculo sobre lo que se está recalculando          */
    /* =================================================================== */

    @keyframes carga_giro   { to { transform: rotate(360deg); } }
    @keyframes carga_entrar { to { opacity: 1; } }

    /* Streamlit ya deja el contenedor en `position: relative` (medido), pero
       de eso dependen las dos capas de abajo: se declara para que un cambio
       suyo no las mande a posicionarse contra el viewport. */
    [data-testid="stElementContainer"][data-stale="true"]:has([data-testid="stPlotlyChart"]),
    [data-testid="stElementContainer"][data-stale="true"]:has(iframe[title="st_aggrid.AgGrid.agGrid"]) {
        position: relative;
    }

    /* EL VELO. Cubre el dato viejo lo justo para que se lea como "esto ya no
       vale" sin borrarlo — quien estaba mirando una barra sigue ubicado
       cuando vuelve el dato nuevo. Lleva la palabra adentro (`content`)
       porque un pseudo-elemento no puede ser a la vez el velo y el círculo,
       y son sólo dos por elemento.

       `rgba()` plano ANTES del `color-mix()`: si el navegador no soporta esa
       función la declaración es inválida y SE IGNORA ENTERA, y sin nada
       previo válido el velo desaparece. rgba(255,255,255,...) es el mismo
       --bg-card (#ffffff) escrito a mano — si --bg-card cambia, actualizar
       también este rgba(). Mismo patrón que el panel de `_80_cards.py`.
       El 80% se eligió mirándolo, no a ojo de tabla: al 74% la palabra
       peleaba con las barras del ranking debajo.

       `pointer-events: none` a propósito: esto AVISA, no bloquea. Un velo
       que se come los clics convierte un rerun lento en una app trabada. */
    [data-testid="stElementContainer"][data-stale="true"]:has([data-testid="stPlotlyChart"])::before,
    [data-testid="stElementContainer"][data-stale="true"]:has(iframe[title="st_aggrid.AgGrid.agGrid"])::before {
        content: "Actualizando…";
        position: absolute;
        inset: 0;
        z-index: 3;
        display: grid;
        place-items: center;
        /* Empuja la palabra DEBAJO del círculo: el grupo (círculo 26 + aire
           10 + texto 14 = 50px) queda centrado si el texto cae en
           centro + 18px, y para eso el padding es 2 x 18. */
        padding-top: 36px;
        overflow: hidden;            /* en una figura angosta se recorta la
                                        palabra, nunca el círculo */
        pointer-events: none;
        font-size: 11.5px;
        font-weight: 500;
        letter-spacing: .02em;
        color: var(--text-secondary);
        background: rgba(255, 255, 255, 0.80);
        background: color-mix(in srgb, var(--bg-card) 80%, transparent);
        opacity: 0;
        animation: carga_entrar .18s ease-out .4s forwards;
    }

    /* EL CÍRCULO. Un anillo con un cuarto teñido — el idioma universal de
       "cargando", el mismo registro que el brillo de `_27_pila.py` para los
       esqueletos. Va ARRIBA del centro (margin-top negativo mayor que medio
       alto) para dejarle sitio a la palabra. */
    [data-testid="stElementContainer"][data-stale="true"]:has([data-testid="stPlotlyChart"])::after,
    [data-testid="stElementContainer"][data-stale="true"]:has(iframe[title="st_aggrid.AgGrid.agGrid"])::after {
        content: "";
        position: absolute;
        top: 50%;
        left: 50%;
        z-index: 4;
        width: 26px;
        height: 26px;
        margin: -25px 0 0 -13px;
        /* La pista en --border-lavender, no en --accent-light: probado al
           lado, el lavanda 100 (#e7e3fb) sobre el velo casi blanco no se
           lee como círculo — se ve un fantasma. */
        border: 2.5px solid var(--border-lavender);
        border-top-color: var(--accent);
        border-radius: 50%;
        pointer-events: none;
        opacity: 0;
        animation: carga_giro .8s linear infinite,
                   carga_entrar .18s ease-out .4s forwards;
    }

    /* Movimiento reducido: el anillo se queda quieto pero se ve. Sin giro
       sigue diciendo lo mismo, igual que el hueco quieto de `_27_pila.py`. */
    @media (prefers-reduced-motion: reduce) {
        [data-testid="stElementContainer"][data-stale="true"]:has([data-testid="stPlotlyChart"])::after,
        [data-testid="stElementContainer"][data-stale="true"]:has(iframe[title="st_aggrid.AgGrid.agGrid"])::after {
            animation: carga_entrar .18s ease-out .4s forwards;
        }
    }

    /* =================================================================== */
    /* CARGANDO — la sección que se construye por primera vez               */
    /* =================================================================== */
    /* Lo dibuja `graficos/base.py::seccion_perezosa` con `st.spinner`: ahí
       no hay nada en pantalla que marcar como stale —el esqueleto acaba de
       irse y el contenido todavía no llegó—, así que ese aviso lo pone
       Python y esto sólo lo pone a tono con el resto.

       NO se acota a una key: `st.spinner` es un elemento TRANSITORIO (no
       ocupa índice en el delta path), así que no hay `st-key-*` del que
       colgarse. Es el único `st.spinner` con texto propio de la app fuera
       del asistente, que ya tiene su regla en `_85_asistente.py`. */
    [data-testid="stSpinner"] {
        padding: 6px 0 2px !important;
    }
    [data-testid="stSpinner"] p {
        font-size: 12px !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        margin: 0 !important;
    }
"""
