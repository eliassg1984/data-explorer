"""Esqueletos de carga de la pagina apilada (2026-08-24).

Compras dejo de mostrar una vista por vez: ahora son seis secciones que se
leen bajando. Construirlas cuesta ~45s en una maquina lenta (medido, con la
cache de datos caliente; en frio son ~118s porque se suman los parquets de
R2). Streamlit manda cada elemento apenas lo construye, asi que la pagina se
llena SOLA de arriba abajo y la primera seccion esta lista mucho antes que el
resto — el usuario nunca espera el total.

El problema no era el orden, entonces, sino que no se veia:

  · la pagina CRECIA bajo el cursor. Empezabas a leer Proveedor y lo que
    mirabas se movia cuando aterrizaba la seccion siguiente;
  · nada indicaba que faltaba. A los 15s la pagina parecia terminar en
    Proveedor, y quien no sabia se iba.

La solucion es la estandar para esto: el ESQUELETO se dibuja entero antes de
construir nada. La pagina nace con su estructura y su altura, cada hueco
lleva el nombre de la vista que va a ocupar —asi funciona ademas como indice
de lo que viene— y el contenido real lo reemplaza al llegar.

ALTURA RESERVADA: `var(--alto-util)`, o sea UNA PANTALLA por seccion. No es
un numero elegido a ojo: es la unidad del proyecto (`estilos/_00_base.py`,
la misma de "una tarjeta = una pantalla") y por lo tanto no es un alto suelto
de los que prohibe `test_graficos.py`. No acierta el alto exacto de cada
seccion —imposible, depende de los datos: Volatilidad puede medir 24px si no
hay 4 semanas en el rango— pero lleva el salto de "de 0 a mil y pico" a un
ajuste chico, que es lo que el scroll anchoring del navegador absorbe bien.

El brillo que recorre las cajas es el idioma universal de "esto esta
cargando". Se apaga con `prefers-reduced-motion`: ahi queda el hueco quieto,
que sigue comunicando lo mismo sin movimiento.

OJO (regla #198): este modulo NO lleva `<style>` propio. `_00_base` abre la
etiqueta y `_99_movil` la cierra; lo del medio va pelado. Un `<style>`
anidado es sintaxis invalida y el parser descarta este modulo Y todos los
siguientes.
"""

CSS = """
    /* =================================================================== */
    /* ESQUELETOS DE LA PILA                                                */
    /* =================================================================== */
    .pila-hueco {
        min-height: var(--alto-util);
        display: flex;
        flex-direction: column;
        gap: 14px;
        padding: 18px 20px;
        border: 1px solid var(--border);
        border-radius: 12px;          /* mismas esquinas que la tarjeta */
        background: var(--bg-card);
    }

    /* El nombre de la vista que va a ocupar el hueco. En reposo, no en
       gris fantasma: es informacion util (que viene mas abajo), no
       relleno. */
    .pila-hueco-tit {
        font-size: .95rem;
        font-weight: 600;
        color: var(--text-secondary);
        letter-spacing: .01em;
    }

    /* Las cajas imitan la FORMA del contenido —una franja de controles, un
       bloque grande de grafico— para que el hueco se lea como "aca va algo"
       y no como un error de layout. */
    .pila-hueco-barra {
        height: 14px;
        width: 38%;
        border-radius: 6px;
    }
    .pila-hueco-caja {
        flex: 1 1 auto;
        min-height: 160px;
        border-radius: 10px;
    }

    .pila-hueco-barra,
    .pila-hueco-caja {
        /* El degradado es TRES paradas del mismo gris con una mas clara en
           el medio: es la banda que viaja. Se mueve con background-position
           y no con un pseudo-elemento desplazado, para no crear una capa
           que el navegador tenga que componer aparte en cada frame. */
        background: linear-gradient(
            100deg,
            var(--bg-hover) 30%,
            var(--bg-card)  50%,
            var(--bg-hover) 70%);
        background-size: 300% 100%;
        animation: pila_brillo 1.6s ease-in-out infinite;
    }

    @keyframes pila_brillo {
        from { background-position: 150% 0; }
        to   { background-position: -50% 0; }
    }

    /* Movimiento reducido: se apaga la banda y queda el hueco quieto. El
       mensaje ("falta contenido aca") lo da la forma, no la animacion. */
    @media (prefers-reduced-motion: reduce) {
        .pila-hueco-barra,
        .pila-hueco-caja {
            animation: none;
            background: var(--bg-hover);
        }
    }

    /* El boton que activa la seccion. Invisible pero PRESENTE: lo aprieta
       el observador con `.click()`, y `display:none` es justo lo que hay
       que evitar — un boton no dibujado no existe para Streamlit y el
       fragment nunca se enteraria. Se saca del flujo con position absolute
       y se apaga con opacity, que no cambia si el elemento esta ahi. */
    [class*="st-key-pila_go_"] {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        overflow: hidden !important;
        opacity: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* En movil la pantalla es otra y una reserva de `--alto-util` por
       seccion deja al usuario scrolleando huecos. Se reserva menos: alcanza
       para que se vea que viene algo. */
    @media screen and (max-width: 768px) {
        .pila-hueco {
            min-height: 240px;
            padding: 14px 16px;
        }
    }

    /* =================================================================== */
    /* ENCAJE: UNA VISTA POR PANTALLA (2026-09-25, regla #533)              */
    /* =================================================================== */
    /* A pedido: «a veces cuando el usuario hace scroll, las tarjetas se
       quedan a medio scroll y eso puede quitar el enfoque». Se eligió, con
       un mockup de por medio, la variante «diapositivas» sobre «imán al
       borde» y «sólo si queda cerca»: cada vista ocupa la pantalla entera y
       la siguiente no asoma.

       Tres piezas, y hacen falta las tres:

       · `scroll-snap-type: y mandatory` en `.stMain`, que es el que
         scrollea (no la ventana). Obligatorio y no por cercanía: con
         `proximity`, soltar a mitad de camino deja a mitad de camino, que
         es justo la queja.
       · `scroll-padding-top: var(--cab-offset-contenido)`: la vista encaja
         donde abre la primera tarjeta (20px desde 901, 52 entre 769 y 900).
         Desde 901 es el MISMO punto donde ya aterrizaba el clic del rail
         (`techo + 8` en `base.py::_render_rail`), así que el salto y el
         encaje no se pelean; y `scrollIntoView` (`scroll_a_seccion`) lo
         respeta solo.
       · Cada sección mide AL MENOS una pantalla: lo que mide una sección
         cuya tarjeta llega al techo `--alto-util`, más sus dos márgenes.
         Hace tres trabajos: la siguiente no asoma (una vista corta deja
         aire abajo, que es el costo aceptado), la ÚLTIMA puede subir hasta
         arriba (sin esto la página se acababa antes y quedaba a la vista la
         cola de la anteúltima), y una sección que se construye no se
         desploma mientras llega su contenido (medido en Compras › Vs año
         pasado: el esqueleto de 708px caía a 0 y crecía durante ~35 s, con
         todo lo de abajo subiendo y bajando solo).

       Una vista más ALTA que la pantalla (Compras › Producto no lleva
       techo) se recorre libre por dentro: el navegador da por válida
       cualquier posición en que la sección cubra la pantalla, y encaja
       recién al salir. Medido, igual que otras dos: si la sección de arriba
       crece mientras se mira otra, la de pantalla se queda quieta (el
       navegador re-encaja en el mismo elemento), y una tabla que crece
       adentro de la vista en pantalla no la hace saltar.

       LA TRAMPA: con encaje obligatorio, lo que está EN EL FLUJO y no es un
       punto de encaje no se puede dejar a la vista. Un aviso arriba de la
       pila quedaría del otro lado del borde para siempre: la página salta a
       la primera sección y no deja volver. Por eso el aviso de datos viejos
       (`app.py`, `aviso_dato_viejo`) es él mismo un punto de encaje, y lo
       que se agregue arriba o abajo de una pila tiene que serlo también.
       Y la trampa gemela, que es por qué el tipo de encaje es una VARIABLE:
       en una página SIN pila (un destino aparte como Documentos SUNAT, o
       una herramienta) ese aviso sería el único punto de encaje, y la
       página no se podría bajar. `--pila-encaje` la publica
       `base.py::_render_rail` sólo cuando dibuja la pila; sin ella, `none`.

       Las secciones se reconocen por el infijo `_sec_` de su key, menos los
       botones invisibles `pila_go_<clave>`, que también lo llevan: a esos un
       punto de encaje los volvería un segundo tope, corrido un pixel. Fuera
       de un `:has()`, un atributo no cuesta (regla #469).

       Sólo desde 769px. En el celular las vistas miden varias pantallas y
       el esqueleto reserva 240px (arriba): encajar ahí sería pelear con el
       dedo. */
    @media screen and (min-width: 769px) {
        :root {
            --pila-seccion-min: calc(var(--alto-util)
                                     + var(--margen-tarjeta) * 2);
        }
        .stMain {
            scroll-snap-type: var(--pila-encaje, none);
            scroll-padding-top: var(--cab-offset-contenido);
        }
        [class*="st-key-"][class*="_sec_"]:not([class*="st-key-pila_go_"]) {
            scroll-snap-align: start;
            min-height: var(--pila-seccion-min);
        }
        .st-key-aviso_dato_viejo {
            scroll-snap-align: start;
        }
    }
"""
