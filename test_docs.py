"""test_docs.py — que la documentación no se contradiga con el código.

POR QUÉ EXISTE (2026-08-22). `arquitectura.md` pasó los 7.200 renglones y 161
reglas. A ese tamaño ya no se verifica a ojo: en UNA sola sesión aparecieron
cuatro defectos, y tres eran mecánicos —

  · dos reglas con el número #157 (dos sesiones agregando al final a la vez)
  · el #143 duplicado, que llevaba días sin que nadie lo notara
  · un parche que citaba "regla #150" cuando la #150 es de otro tema
  · la lista de módulos de `estilos/` en CLAUDE.md, incompleta (10 de 12)

— y ninguno lo habría encontrado un lector, porque comprobarlos exige
recorrer el fichero entero. Es el mismo razonamiento que ya aplica
`test_graficos.py` con los altos sueltos: si algo se rompe en silencio y
revisarlo es caro, se convierte en test.

NO juzga el CONTENIDO de las reglas (eso es criterio humano). Sólo verifica
lo que tiene una respuesta objetiva: numeración, referencias cruzadas y que
lo que CLAUDE.md afirma del código siga siendo cierto.

Se ejecuta solo:  python test_docs.py
"""

import re
import sys
from pathlib import Path

# Igual que test_graficos.py y test_asistente_datos.py: la consola de Windows
# (cp1252) revienta con UnicodeEncodeError en el PRIMER print y el gate falla
# sin decir por qué.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent
ARQ = RAIZ / "arquitectura.md"
CLAUDE = RAIZ / "CLAUDE.md"

_fallos = []


def ok(cond, nombre, detalle=""):
    print(f"{'OK  ' if cond else 'FALLA'}  {nombre}")
    if not cond:
        _fallos.append(f"{nombre}{(' — ' + detalle) if detalle else ''}")
        if detalle:
            print(f"         {detalle}")


arq = ARQ.read_text(encoding="utf-8")
claude = CLAUDE.read_text(encoding="utf-8")

# ── Numeración de las reglas ───────────────────────────────────────────────
print("\n── numeración de las reglas ──")

# Una regla se declara como "NNN. **Título" al principio de línea. Es el
# mismo patrón con el que están escritas las 161; si alguna vez cambia el
# formato, este test deja de ver reglas y el chequeo de "hay reglas" avisa.
_declaradas = [int(m.group(1)) for m in re.finditer(r"^(\d{1,3})\. \*\*", arq, re.M)]
ok(len(_declaradas) > 100, "arquitectura.md declara sus reglas con el formato esperado",
   f"encontradas {len(_declaradas)}, se esperaban >100 — ¿cambió el formato?")

_dups = sorted({n for n in _declaradas if _declaradas.count(n) > 1})
ok(not _dups, "ningún número de regla está repetido",
   f"repetidos: {_dups}")

_conjunto = set(_declaradas)
_huecos = sorted(set(range(1, max(_conjunto) + 1)) - _conjunto) if _conjunto else []
ok(not _huecos, "la numeración no tiene huecos",
   f"sin regla: {_huecos}")

# ── Referencias cruzadas ───────────────────────────────────────────────────
print("\n── referencias cruzadas (#NNN) ──")

# Se miran .py/.md/.js del repo salvo lo generado. Una referencia a un número
# que NO existe casi siempre es un dedazo o una regla renumerada a medias.
# `.claude` incluye los worktrees de las tareas en curso, que son COPIAS del
# repo: sin excluirlos, cada hallazgo se reporta dos veces y con una ruta que
# no es la que hay que editar.
#
# Los componentes se miran RELATIVOS a RAIZ, nunca los de la ruta absoluta:
# este mismo repo se clona a `…/.claude/worktrees/<nombre>/` para trabajar, y
# ahí la ruta absoluta de TODO fichero lleva un `.claude` adentro. Con
# `set(f.parts)` el filtro descartaba los 99 candidatos y el barrido pasaba en
# verde sin abrir ninguno (medido el 2026-08-28; ver arquitectura.md #233).
_omitir = {".git", ".claude", "__pycache__", ".venv", "venv", "node_modules"}
_rotas, _mirados = {}, 0
for f in RAIZ.rglob("*"):
    if f.suffix not in (".py", ".md", ".js"):
        continue
    if _omitir & set(f.relative_to(RAIZ).parts):
        continue
    try:
        texto = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        continue
    _mirados += 1
    for m in re.finditer(r"(?:reglas?\s*#|arquitectura\.md\s*#|#)(\d{1,3})\b", texto):
        n = int(m.group(1))
        if 1 <= n <= max(_conjunto) and n not in _conjunto:
            _rotas.setdefault(n, set()).add(f.relative_to(RAIZ).as_posix())

# En positivo, y antes del veredicto: un barrido de CERO ficheros no puede
# encontrar referencias rotas, así que sin esta línea el fallo se disfraza
# de éxito. Es la mitad del bug de arriba que no avisa.
ok(_mirados > 20, f"el barrido leyó {_mirados} ficheros del repo",
   "0 o casi 0: el filtro de directorios se está comiendo el repo entero")

ok(not _rotas, "ninguna referencia apunta a una regla inexistente",
   "; ".join(f"#{n} en {', '.join(sorted(v)[:3])}" for n, v in sorted(_rotas.items())))

# ── Índice temático ────────────────────────────────────────────────────────
print("\n── índice de arquitectura.md ──")

# El índice se genera; si alguien agrega una regla y no lo regenera, queda
# invisible en la única estructura que hace navegable un fichero de 7.100
# renglones. Por eso se verifica acá y no se confía en que alguien se acuerde.
sys.path.insert(0, str(RAIZ / "herramientas"))
try:
    import indice_reglas
except ImportError:
    indice_reglas = None

ok(indice_reglas is not None, "herramientas/indice_reglas.py se puede importar")
if indice_reglas is not None:
    ok(indice_reglas.INI in arq and indice_reglas.FIN in arq,
       "arquitectura.md tiene el bloque del índice")
    _esperado = indice_reglas.aplicar(arq, indice_reglas.construir_indice(arq))
    ok(_esperado == arq, "el índice está al día",
       "corré: python herramientas/indice_reglas.py")

    _indexadas = {int(n) for n in re.findall(
        r"^- \*\*#(\d+)\*\*", arq[arq.index(indice_reglas.INI):
                                  arq.index(indice_reglas.FIN)], re.M)}
    _sin = sorted(_conjunto - _indexadas)
    ok(not _sin, "todas las reglas aparecen en el índice", f"faltan: {_sin}")

# ── CLAUDE.md contra el código ─────────────────────────────────────────────
print("\n── CLAUDE.md dice la verdad sobre el código ──")

# El orden de _SECCIONES ES comportamiento (gana la regla que va después), así
# que una lista incompleta en CLAUDE.md no es cosmética: hace creer que la
# cadena tiene menos eslabones de los que tiene. Pasó — faltaban
# _25_rails_pestillo y _85_asistente.
_init = (RAIZ / "estilos" / "__init__.py").read_text(encoding="utf-8")
_orden_real = re.findall(r"^from \.(_\d\d_\w+) import", _init, re.M)
_orden_doc = re.findall(r"`(_\d\d_\w+)`", claude)
# En CLAUDE.md los módulos aparecen también sueltos en prosa; la LISTA es la
# subsecuencia que respeta el orden de disco. Se compara como conjunto y
# además se exige que los que aparezcan no contradigan el orden.
_faltan = [m for m in _orden_real if m not in _orden_doc]
ok(not _faltan, "CLAUDE.md enumera TODOS los módulos de estilos/",
   f"sin listar: {_faltan}")

_sobran = [m for m in dict.fromkeys(_orden_doc) if m not in _orden_real]
ok(not _sobran, "CLAUDE.md no nombra módulos de estilos/ que no existan",
   f"inexistentes: {_sobran}")

_pos = [_orden_real.index(m) for m in dict.fromkeys(_orden_doc) if m in _orden_real]
ok(_pos == sorted(_pos), "el orden que lista CLAUDE.md coincide con el de _SECCIONES",
   f"orden documentado: {[m for m in dict.fromkeys(_orden_doc) if m in _orden_real]}")

# Símbolos que CLAUDE.md manda usar por nombre. Si uno se renombra, el
# documento queda mandando a una función que ya no está — y es el fichero que
# se carga solo en cada sesión, así que el error se propaga.
_SIMBOLOS = [
    ("publicar_contexto_ia", "graficos/base.py"),
    ("paso_etiquetas", "graficos/base.py"),
    ("COLUMNAS_DRILL", "graficos/compras/_comun.py"),
    ("por_filas", "graficos/alturas.py"),
    ("_datos_demo", "data.py"),
    ("inject_element_inspector", "inyecciones/inspector.py"),
    ("inject_herramientas", "inyecciones/herramientas.py"),
    ("en_moneda_del_papel", "sunat.py"),
]
for simbolo, modulo in _SIMBOLOS:
    ruta = RAIZ / modulo
    existe = ruta.exists() and simbolo in ruta.read_text(encoding="utf-8")
    ok(existe, f"{simbolo} sigue en {modulo}")

# Las herramientas que CLAUDE.md manda pegar/usar tienen que existir: son la
# primera cosa que alguien intenta al leer el documento.
for nombre in ("auditar_layout.js", "auditar_graficos.js", "rayos_x.js",
               "ver_figura.py"):
    ok((RAIZ / "herramientas" / nombre).exists(),
       f"herramientas/{nombre} existe (CLAUDE.md lo nombra)")

# ── Cierre ─────────────────────────────────────────────────────────────────
print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for f in _fallos:
        print(f"   · {f}")
    sys.exit(1)
print(f"✅ Todo OK (documentación: {len(_declaradas)} reglas, "
      f"{len(_conjunto)} números, sin duplicados ni referencias rotas)")
