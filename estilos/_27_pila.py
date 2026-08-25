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

    /* En movil la pantalla es otra y una reserva de `--alto-util` por
       seccion deja al usuario scrolleando huecos. Se reserva menos: alcanza
       para que se vea que viene algo. */
    @media screen and (max-width: 768px) {
        .pila-hueco {
            min-height: 240px;
            padding: 14px 16px;
        }
    }
"""
