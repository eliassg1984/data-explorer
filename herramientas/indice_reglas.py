"""indice_reglas.py — regenera el índice temático de `arquitectura.md`.

    python herramientas/indice_reglas.py            # reescribe el índice
    python herramientas/indice_reglas.py --check    # sólo dice si está al día

POR QUÉ EXISTE (2026-08-22). La bitácora tiene 162 reglas en orden
CRONOLÓGICO, así que las que hablan del mismo tema quedan a miles de líneas
unas de otras. Sin índice, "¿qué sé ya sobre Plotly?" no se puede contestar
sin adivinar palabras para grepear.

POR QUÉ UN ÍNDICE Y NO FICHEROS POR TEMA: medido sobre el corpus, el 19% de
las reglas cae en más de un tema (y muchas en ninguno limpio). Un fichero
obliga a elegir un hogar único; el índice deja que una regla aparezca bajo
todos los temas que le corresponden. Además hay 143 referencias cruzadas
entre reglas y 166 citas `arquitectura.md #NNN` en el código: repartirlas
rompía las dos redes de una vez.

El índice se escribe ENTRE MARCADORES, así que este script nunca toca el
cuerpo de las reglas. `test_docs.py` verifica que no se desincronice.
"""

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQ = RAIZ / "arquitectura.md"

INI = "<!-- INDICE:INICIO — generado por herramientas/indice_reglas.py, no editar a mano -->"
FIN = "<!-- INDICE:FIN -->"

# Orden = el del índice. Una regla puede caer en VARIOS temas a propósito.
#
# Cada tema trae DOS patrones porque un umbral único no servía: con 3
# apariciones exigidas quedaban 39 reglas (24%) sin clasificar pese a tener
# tema obvio —#2 y #26 son puro AgGrid, #12 y #92 puro Plotly— y bajarlo a 1
# metía cualquier mención de pasada. Así que:
#   · DECISIVO: nombra la tecnología sin ambigüedad. Con UNA alcanza.
#   · CONTEXTO: pistas más débiles. Hacen falta UMBRAL apariciones.
TEMAS = (
    ("CSS y estilos",
     r"\bCSS\b|estilos/|`--[a-z-]+`|st-key-",
     r"!important|selector|margin|padding|z-index|flex|:has\(|::(before|after)"),
    ("Layout y alturas",
     r"alturas\.py|alto-util|COLUMNAS_DRILL|max-height",
     r"st\.columns|viewport|px de alto|scroll interno|tarjeta"),
    ("Plotly y figuras",
     r"Plotly|go\.(Bar|Scatter|Waterfall|Figure|Heatmap)|px\.(bar|histogram|line)|tickangle",
     r"update_layout|heatmap|eje X|eje Y|figura|barra|leyenda|hover"),
    ("AgGrid y tablas",
     r"AgGrid|AG Grid|st_aggrid|cellRenderer|gridOptions|pivotMode|configure_column|GridOptionsBuilder",
     r"\bgrid\b|fila de totales|panel de columnas|celda|headerName"),
    ("Streamlit",
     r"Streamlit|session_state|st\.(markdown|button|pills|popover|container|date_input|plotly_chart|fragment)",
     r"rerun|query_params|widget|key=|components\.html"),
    ("Datos, R2 y DuckDB",
     r"DuckDB|parquet|\bR2\b|cache_data|cargar_rango",
     r"cache|filtrar|df_f|dataframe"),
    ("SUNAT y SIRE",
     r"SUNAT|SIRE|\bRUC\b|Playwright",
     r"comprobante|serie-número|emisión|token"),
    ("Fechas, rangos y cortes",
     r"estado_rango|clave_rango|corte_vigente|date_input|cortes\.py",
     r"\bcorte\b|calendario|rango de fecha|granularidad"),
    ("Asistente IA",
     r"asistente|Groq|tool calling|asistente_datos",
     r"prompt|modelo|SQL"),
    ("Herramientas de desarrollo",
     r"inspector|modo diseño|auditar_|rayos ?X|\?debug=1|diagnostico=1",
     r"tooltip|medir en el navegador|DevTools"),
    ("Decisiones de diseño y UX",
     r"a pedido|reportado con captura|mockup",
     r"rail|drill|vista|se ve|legible|pantalla"),
    ("Mantenimiento y trampas del lenguaje",
     r"ruff|F401|re-export|código muerto|codigo muerto|test_graficos|test_docs",
     r"refactor|se borró|se eliminó|paquete|dispatcher|una sola fuente|duplicad"),
)
UMBRAL = 2       # apariciones de CONTEXTO para que un tema entre en juego
MAX_TEMAS = 2    # en cuántos temas puede aparecer una misma regla
PISO = 0.40      # y con qué fracción del tema más fuerte, como mínimo
#                  (.45 dejaba la #156 sin CSS por un punto: 10 contra 10.8)


FIN_REGLAS = "<!-- REGLAS:FIN"


def _reglas(texto):
    """[(numero, titulo_corto, cuerpo)] en el orden en que aparecen.

    Corta en FIN_REGLAS: sin eso el cuerpo de la ÚLTIMA regla se comía todo
    lo que viniera después —hoy la nota sobre qué número toca— y la
    clasificaba con esas palabras. Costó un diagnóstico: la #161, que es de
    Plotly, salía indexada bajo SUNAT porque esa nota nombra la serie de
    SUNAT."""
    corte = texto.find(FIN_REGLAS)
    if corte != -1:
        texto = texto[:corte]
    marcas = [(int(m.group(1)), m.start()) for m in
              re.finditer(r"^(\d{1,3})\. \*\*", texto, re.M)]
    fuera = []
    for i, (num, ini) in enumerate(marcas):
        fin = marcas[i + 1][1] if i + 1 < len(marcas) else len(texto)
        cuerpo = texto[ini:fin]
        # El título es lo que va entre el primer ** y el ** de cierre. Puede
        # ocupar varias líneas: se aplana y se recorta.
        m = re.search(r"\*\*(.+?)\*\*", cuerpo, re.S)
        titulo = " ".join(m.group(1).split()) if m else "(sin título)"
        titulo = re.sub(r"`([^`]+)`", r"\1", titulo).rstrip(" .:")
        if len(titulo) > 95:
            titulo = titulo[:94].rsplit(" ", 1)[0] + "…"
        fuera.append((num, titulo, cuerpo))
    return fuera


def _clasificar(cuerpo):
    """Los temas MÁS FUERTES de una regla, como mucho `MAX_TEMAS`.

    No alcanza con "¿supera el umbral?": casi toda regla roza varios temas
    (una de CSS habla de una tarjeta de Streamlit que muestra un Plotly), y
    clasificarla en todos daba 601 entradas para 162 reglas — un índice donde
    todo está en todos lados no ayuda a nadie. Se PUNTÚA y se conservan los
    punteros de arriba, con un piso relativo al mejor para que un tema que
    apenas roza no entre a upa del que sí manda.
    """
    puntos = {}
    for nombre, decisivo, contexto in TEMAS:
        p = 3 * len(re.findall(decisivo, cuerpo, re.I)) \
            + len(re.findall(contexto, cuerpo, re.I))
        if re.search(decisivo, cuerpo, re.I) or p >= UMBRAL:
            puntos[nombre] = p
    if not puntos:
        return []
    mejor = max(puntos.values())
    fuertes = [n for n, p in puntos.items() if p >= max(UMBRAL, mejor * PISO)]
    fuertes.sort(key=lambda n: -puntos[n])
    return fuertes[:MAX_TEMAS]


def construir_indice(texto):
    reglas = _reglas(texto)
    por_tema = {t[0]: [] for t in TEMAS}
    sin_tema = []
    for num, titulo, cuerpo in reglas:
        temas = _clasificar(cuerpo)
        if temas:
            for t in temas:
                por_tema[t].append((num, titulo))
        else:
            sin_tema.append((num, titulo))

    out = [INI, "", "## Índice por tema", "",
           f"{len(reglas)} reglas. Una misma regla aparece bajo todos los temas "
           "que le corresponden — por eso los totales suman más que el total.", ""]
    for nombre, _dec, _ctx in TEMAS:
        filas = por_tema[nombre]
        if not filas:
            continue
        out.append(f"**{nombre}** ({len(filas)})")
        out.append("")
        for num, titulo in filas:
            out.append(f"- **#{num}** — {titulo}")
        out.append("")
    if sin_tema:
        out.append(f"**Sin tema asignado** ({len(sin_tema)})")
        out.append("")
        for num, titulo in sin_tema:
            out.append(f"- **#{num}** — {titulo}")
        out.append("")
    out.append(FIN)
    return "\n".join(out)


def aplicar(texto, indice):
    """Reemplaza el bloque entre marcadores, o lo inserta tras la cabecera."""
    if INI in texto and FIN in texto:
        ini = texto.index(INI)
        fin = texto.index(FIN) + len(FIN)
        return texto[:ini] + indice + texto[fin:]
    # Primera vez: va justo antes de la regla 1.
    m = re.search(r"^1\. \*\*", texto, re.M)
    if not m:
        raise SystemExit("no se encontró la regla 1: ¿cambió el formato?")
    return texto[:m.start()] + indice + "\n\n" + texto[m.start():]


def main():
    texto = ARQ.read_text(encoding="utf-8")
    indice = construir_indice(texto)
    nuevo = aplicar(texto, indice)
    if "--check" in sys.argv:
        if nuevo != texto:
            print("DESACTUALIZADO: corré  python herramientas/indice_reglas.py")
            return 1
        print("índice al día")
        return 0
    ARQ.write_text(nuevo, encoding="utf-8")
    n = indice.count("\n- **#")
    print(f"índice regenerado: {n} entradas sobre {len(_reglas(texto))} reglas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
