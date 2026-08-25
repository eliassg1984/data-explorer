"""inyecciones.inspector - inspector de elementos (herramienta de desarrollo).

Permite senalar un elemento en la pagina y ver sus selectores y estilos. Es
la inyeccion mas grande del paquete y no participa del render normal.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from inyecciones._iframe import inyectar_html
from inyecciones._inspector_js import JS

_RAIZ = Path(__file__).resolve().parent.parent
_KEY_PY = re.compile(r"""key\s*=\s*['"]([A-Za-z0-9_]+)['"]""")
_KEY_CSS = re.compile(r"st-key-([A-Za-z0-9_]+)")
# def / async def top-level (indent 0). Captura el nombre.
_DEF_TOP = re.compile(r"^(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
# key=f"PREFIX_{...}" — detecta helpers que construyen keys con f-string.
_KEY_FSTRING = re.compile(r"""key\s*=\s*f['"]([A-Za-z0-9]+)_\{""")
# <var>key<var> = f"PREFIX_{...}"  o  key=f"PREFIX_{...}" — keys dinamicas
# armadas con f-string. Captura el PREFIJO ESTATICO COMPLETO (incluye los '_'
# internos y el '_' final) hasta la primera interpolacion {. Sirve de fallback
# por prefijo cuando la key exacta no existe en el codigo (se arma en runtime,
# ej: _tkey = f"compras_g_fam_time_{focus}_{gran}_{rst}").
_KEY_FSTRING_PREFIJO = re.compile(
    r"""\b(\w*key\w*)\s*=\s*f['"]([A-Za-z0-9_]+)\{""", re.IGNORECASE)


def _slug_py(s: str) -> str:
    """Slug equivalente a graficos.base._slug: minúsculas, no-alfanum → '_'."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
# st.caption("..."), st.button("..."), st.markdown("..."), etc.
# Solo capturamos el PRIMER argumento string literal (label/texto principal).
_ST_TEXTO = re.compile(
    r"""st\.(caption|button|markdown|write|info|warning|error|success|
            title|header|subheader|toast|link_button|download_button|pills|
            segmented_control|radio|selectbox|multiselect|toggle|checkbox|
            text_input|text_area|number_input|date_input|time_input|
            slider|select_slider|color_picker|chat_input|badge|metric)
        \s*\(\s*(?:f\s*)?['"]([^'"\n]{2,80})['"]""",
    re.VERBOSE,
)


def _funcion_contenedora(lineas: list[str], linea_1based: int) -> tuple[str, int, int, bool]:
    """Para una linea dada (1-based), devuelve (nombre_func, ini, fin, es_fragment).
    `es_fragment`: True si la función tiene @st.fragment (o @fragment) arriba.
    Si la linea no cae dentro de ningun `def` de nivel 0, devuelve ('', 0, 0, False).
    """
    idx = linea_1based - 1
    ini_def = -1
    nombre = ""
    for j in range(idx, -1, -1):
        m = _DEF_TOP.match(lineas[j])
        if m:
            ini_def = j
            nombre = m.group(1)
            break
    if ini_def < 0:
        return ("", 0, 0, False)
    # decoradores inmediatamente arriba del def
    es_fragment = False
    j = ini_def - 1
    while j >= 0:
        ln = lineas[j].strip()
        if not ln or ln.startswith("#"):
            j -= 1
            continue
        if ln.startswith("@"):
            if "fragment" in ln:
                es_fragment = True
            j -= 1
            continue
        break
    fin = len(lineas)
    for j in range(ini_def + 1, len(lineas)):
        ln = lineas[j]
        if not ln.strip():
            continue
        if ln[0] not in (" ", "\t", ")", "]", "#"):
            fin = j
            break
    while fin > ini_def + 1 and not lineas[fin - 1].strip():
        fin -= 1
    return (nombre, ini_def + 1, fin, es_fragment)


def _norm_texto(s: str) -> str:
    """Normaliza texto para comparar: minúsculas y whitespace colapsado.
    Se usa para matchear el innerText de un elemento (que puede tener saltos
    de linea y iconos Material) contra el string literal del codigo."""
    return " ".join(s.lower().split())


@lru_cache(maxsize=1)
def _mapas_desarrollador() -> tuple[str, str, str, str, str, str, str, str]:
    """Devuelve mapas serializados a JSON:
      codigo, estilos, snippets, funcion, refs, texto, construido, prefijos.

    mapa_construido: {key -> "helper(args) — archivo:linea"}  keys f-string
    mapa_prefijos:   {prefijo_ -> {codigo, snippet, funcion, refs}} fallback
                     por prefijo para keys dinamicas (f-string con vars runtime).
    """
    mapa_codigo: dict[str, str] = {}
    mapa_snippets: dict[str, str] = {}
    mapa_funcion: dict[str, str] = {}
    mapa_texto: dict[str, str] = {}
    # (nombre_func, archivo_def) por key -> se usa para calcular refs despues
    key_a_func: dict[str, tuple[str, str]] = {}
    # Fallback por prefijo para keys dinamicas (f-string). prefijo -> registro
    # {codigo, snippet, funcion}. Los refs se calculan luego junto con los de key.
    mapa_prefijos: dict[str, dict] = {}
    prefijo_a_func: dict[str, tuple[str, str]] = {}

    # graficos/ se recorre RECURSIVO (`**`), no plano: cada vez que un
    # dashboard se parte en paquete (compras 2026-07, ajuste despues) sus
    # keys quedaban fuera del indice y el tooltip salia sin "Declarado en",
    # sin snippet y sin funcion — y las Referencias perdian esos call sites,
    # que es peor: una referencia que falta parece "nadie depende de esto".
    # Antes habia una linea por subpaquete y compras era la unica agregada.
    # Los `_`-prefijados SI entran aca (a diferencia de la raiz): es
    # justamente donde viven las keys de los paquetes (_heatmap.py, etc).
    fuentes_py = sorted(p for p in _RAIZ.glob("*.py") if not p.name.startswith("_"))
    fuentes_py += sorted((_RAIZ / "graficos").glob("**/*.py"))
    fuentes_py += sorted((_RAIZ / "tablas").glob("**/*.py")) if (_RAIZ / "tablas").exists() else []

    # cache: {archivo -> [lineas]} para no releer al buscar refs
    contenido_por_archivo: dict[str, list[str]] = {}

    for archivo in fuentes_py:
        try:
            lineas = archivo.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        rel = archivo.relative_to(_RAIZ).as_posix()
        contenido_por_archivo[rel] = lineas
        for i, linea in enumerate(lineas, 1):
            # textos literales de st.XXX("...") — indice inverso texto->ubicacion
            for m_txt in _ST_TEXTO.finditer(linea):
                txt_norm = _norm_texto(m_txt.group(2))
                if txt_norm and txt_norm not in mapa_texto:
                    mapa_texto[txt_norm] = f"{rel}:{i}"
            for k in _KEY_PY.findall(linea):
                if k not in mapa_codigo:
                    mapa_codigo[k] = f"{rel}:{i}"
                    start = max(0, i - 3)
                    end = min(len(lineas), i + 2)
                    snippet_lines = []
                    for j in range(start, end):
                        prefix = ">>>" if j == i - 1 else "   "
                        snippet_lines.append(f"{prefix} {j+1:>4}| {lineas[j]}")
                    mapa_snippets[k] = "\n".join(snippet_lines)
                    # funcion contenedora
                    nombre, ini, fin, es_frag = _funcion_contenedora(lineas, i)
                    if nombre:
                        tag = " [@st.fragment]" if es_frag else ""
                        mapa_funcion[k] = f"{nombre} ({rel}:{ini}-{fin}){tag}"
                        key_a_func[k] = (nombre, rel)
            # keys dinamicas por f-string: registrar el prefijo estatico como
            # fallback (ej: _tkey = f"compras_g_fam_time_{...}" -> prefijo
            # "compras_g_fam_time_"). Gana el prefijo mas largo en el lookup JS.
            for m_fs in _KEY_FSTRING_PREFIJO.finditer(linea):
                pref = m_fs.group(2)
                if not pref or pref in mapa_prefijos:
                    continue
                start = max(0, i - 3)
                end = min(len(lineas), i + 2)
                snippet_lines = []
                for j in range(start, end):
                    prefix = ">>>" if j == i - 1 else "   "
                    snippet_lines.append(f"{prefix} {j+1:>4}| {lineas[j]}")
                reg = {"codigo": f"{rel}:{i}", "snippet": "\n".join(snippet_lines),
                       "funcion": ""}
                nombre, ini, fin, es_frag = _funcion_contenedora(lineas, i)
                if nombre:
                    tag = " [@st.fragment]" if es_frag else ""
                    reg["funcion"] = f"{nombre} ({rel}:{ini}-{fin}){tag}"
                    prefijo_a_func[pref] = (nombre, rel)
                mapa_prefijos[pref] = reg

    # Referencias: por cada key con func, buscar el nombre en todos los .py
    # excepto en la propia linea de definicion. Evita ruido acotando a `\bNAME\b`.
    mapa_refs: dict[str, list[str]] = {}
    # cachear regex por nombre reutilizable entre keys que comparten funcion
    refs_por_nombre: dict[tuple[str, str], list[str]] = {}

    def _refs_de(nombre: str, archivo_def: str) -> list[str]:
        clave = (nombre, archivo_def)
        if clave in refs_por_nombre:
            return refs_por_nombre[clave]
        patron = re.compile(rf"\b{re.escape(nombre)}\b")
        refs: list[str] = []
        for rel, lineas_a in contenido_por_archivo.items():
            for i, linea in enumerate(lineas_a, 1):
                if not patron.search(linea):
                    continue
                # saltar la propia def
                m = _DEF_TOP.match(linea)
                if m and m.group(1) == nombre and rel == archivo_def:
                    continue
                refs.append(f"{rel}:{i}")
                if len(refs) >= 8:
                    break
            if len(refs) >= 8:
                break
        refs_por_nombre[clave] = refs
        return refs

    for k, (nombre, archivo_def) in key_a_func.items():
        mapa_refs[k] = _refs_de(nombre, archivo_def)
    # refs para los prefijos dinamicos (mismo cache por nombre de funcion)
    for pref, (nombre, archivo_def) in prefijo_a_func.items():
        mapa_prefijos[pref]["refs"] = _refs_de(nombre, archivo_def)

    # Helpers que construyen keys con f-string (ej: _card usa key=f"chartcard_{...}").
    # Los registramos por PREFIX → nombre_helper, y luego buscamos sus callers
    # para reconstruir la key que va a producir cada llamada literal.
    helpers_por_prefix: dict[str, list[str]] = {}
    for rel, lineas_a in contenido_por_archivo.items():
        for i, linea in enumerate(lineas_a, 1):
            m = _KEY_FSTRING.search(linea)
            if not m:
                continue
            prefix = m.group(1) + "_"
            nombre, _ini, _fin, _ = _funcion_contenedora(lineas_a, i)
            if not nombre:
                continue
            arr = helpers_por_prefix.setdefault(prefix, [])
            if nombre not in arr:
                arr.append(nombre)

    # Para cada helper, busca callers helper("arg1", "arg2") y computa la key
    # esperada = PREFIX + _slug(arg1). Solo captura callers con literales
    # (skip variables). El result mapea key_esperada -> 'helper("arg1","arg2") - archivo:linea'.
    mapa_construido: dict[str, str] = {}
    for prefix, helpers in helpers_por_prefix.items():
        for helper in helpers:
            patron = re.compile(
                rf'\b{re.escape(helper)}\s*\(\s*[\'"]([^\'"]+)[\'"]'
                rf'(?:\s*,\s*[\'"]([^\'"]+)[\'"])?'
            )
            for rel, lineas_a in contenido_por_archivo.items():
                for i, linea in enumerate(lineas_a, 1):
                    m = patron.search(linea)
                    if not m:
                        continue
                    arg1 = m.group(1)
                    arg2 = m.group(2) or ""
                    key_esperada = prefix + _slug_py(arg1)
                    if key_esperada in mapa_construido:
                        continue
                    call = (f'{helper}("{arg1}", "{arg2}")' if arg2
                            else f'{helper}("{arg1}")')
                    mapa_construido[key_esperada] = f"{call} — {rel}:{i}"

    mapa_estilos: dict[str, list[str]] = {}
    for archivo in sorted((_RAIZ / "estilos").glob("*.py")):
        try:
            texto = archivo.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = archivo.relative_to(_RAIZ).as_posix()
        for k in set(_KEY_CSS.findall(texto)):
            k_norm = k.rstrip("_")
            if not k_norm:
                continue
            mapa_estilos.setdefault(k_norm, [])
            if rel not in mapa_estilos[k_norm]:
                mapa_estilos[k_norm].append(rel)

    return (
        json.dumps(mapa_codigo),
        json.dumps(mapa_estilos),
        json.dumps(mapa_snippets),
        json.dumps(mapa_funcion),
        json.dumps(mapa_refs),
        json.dumps(mapa_texto),
        json.dumps(mapa_construido),
        json.dumps(mapa_prefijos),
    )


def inject_element_inspector():
    """
    Inspector de elementos v2 - tooltip enriquecido al pasar el cursor.
    Activacion : ?debug=1 en la URL  o  Alt+I

    Unificado con el resto de herramientas de desarrollo: el mismo ?debug=1
    que muestra el panel de diagnostico activa tambien este inspector.

    NOTA — colores: el tooltip (#el-inspector-tip) y el badge
    (#el-inspector-badge) se añaden a doc.body (documento PADRE), no al
    iframe de AgGrid, así que sus var(--x) SÍ resuelven contra el :root de
    estilos.py. Se mantienen tal cual.
    """
    mapa_codigo, mapa_estilos, mapa_snippets, mapa_funcion, mapa_refs, mapa_texto, mapa_construido, mapa_prefijos = _mapas_desarrollador()
    # session_state: snapshot no cacheado (cambia cada rerun). Se serializa a
    # str truncado — solo para inspección; nunca para persistir.
    import streamlit as st
    _ss_snapshot: dict[str, str] = {}
    try:
        for _k, _v in st.session_state.items():
            if not isinstance(_k, str) or _k.startswith("_"):
                continue
            try:
                _s = repr(_v)
            except Exception:
                _s = f"<{type(_v).__name__}>"
            if len(_s) > 80:
                _s = _s[:77] + "..."
            _ss_snapshot[_k] = _s
    except Exception:
        pass
    mapa_ss = json.dumps(_ss_snapshot)
    # Sustitucion de los placeholders del blob (ver _inspector_js.py). Antes
    # era una cadena de nueve .replace() encadenados en UNA linea de 400
    # caracteres; asi se ve de un vistazo que mapa alimenta a cual.
    #
    # INVARIANTE: cada clave de aqui existe en el blob, y el blob no tiene
    # placeholders de mas. Se comprueba abajo, porque un placeholder que
    # nadie sustituye rompe el JSON.parse del JS entero, y uno que sobra es
    # trabajo que se calcula para tirar — que es lo que le pasaba a
    # __MAPA_PREFIJOS__ hasta el 2026-08-08 (ver arquitectura.md #56).
    _sustituciones = {
        "__MAPA_CODIGO__": mapa_codigo,
        "__MAPA_ESTILOS__": mapa_estilos,
        "__MAPA_SNIPPETS__": mapa_snippets,
        "__MAPA_FUNCION__": mapa_funcion,
        "__MAPA_REFS__": mapa_refs,
        "__MAPA_TEXTO__": mapa_texto,
        "__MAPA_CONSTRUIDO__": mapa_construido,
        "__MAPA_PREFIJOS__": mapa_prefijos,
        "__MAPA_SS__": mapa_ss,
    }
    _html = JS
    for _ph, _valor in _sustituciones.items():
        _html = _html.replace(_ph, _valor)
    inyectar_html(_html, height=0)


def _placeholders_descuadrados() -> tuple[set, set]:
    """(sobran_en_el_blob, sobran_en_el_dict). Ambos deben venir vacios.

    Lo usa test_graficos.py: es el chequeo que habria cazado en su momento
    el __MAPA_PREFIJOS__ muerto, que estuvo sustituyendose contra un
    placeholder inexistente sin que nada se quejara."""
    del_blob = set(re.findall(r"__MAPA_[A-Z]+__", JS))
    del_codigo = {
        "__MAPA_CODIGO__", "__MAPA_ESTILOS__", "__MAPA_SNIPPETS__",
        "__MAPA_FUNCION__", "__MAPA_REFS__", "__MAPA_TEXTO__",
        "__MAPA_CONSTRUIDO__", "__MAPA_PREFIJOS__", "__MAPA_SS__",
    }
    return del_blob - del_codigo, del_codigo - del_blob
