"""test_datos.py — el contrato de la caché de datos, que falla EN SILENCIO.

Hoy vigila uno solo, el de `arquitectura.md` regla #367: **toda función
cacheada CON `persist="disk"` tiene que llevar el `sello` en su clave.**

Olvidarlo no da error. Da una app que sirve el parquet de hace días con
cara de dato de hoy — el `ttl` de `@st.cache_data` sólo gobierna la copia
en MEMORIA; la de disco no caduca nunca (streamlit 1.59.2,
`in_memory_cache_storage_wrapper.py:91` cae a `_persist_storage.get()` sin
mirar ninguna fecha). Es la misma forma que el `categoria=` de las tarjetas
de Compras, que vigila `test_graficos.py`: un argumento que si falta no
rompe nada, sólo miente.

Es análisis estático con `ast`: corre sin secrets, sin red y sin navegador.

Se ejecuta solo:  python test_datos.py
"""

import ast
import sys
from pathlib import Path

# Igual que los otros tres tests: la consola de Windows (cp1252) revienta con
# UnicodeEncodeError en el PRIMER print y el gate falla sin decir por qué.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent
DATA = RAIZ / "data.py"

_fallos = []


def ok(cond, nombre, detalle=""):
    print(f"{'OK  ' if cond else 'FALLA'}  {nombre}")
    if not cond:
        _fallos.append(f"{nombre}{(' — ' + detalle) if detalle else ''}")
        if detalle:
            print(f"         {detalle}")


fuente = DATA.read_text(encoding="utf-8")
arbol = ast.parse(fuente)


def _es_cache_data(dec):
    """`True` si el decorador es `@st.cache_data(...)` (con o sin args)."""
    llamada = dec.func if isinstance(dec, ast.Call) else dec
    return isinstance(llamada, ast.Attribute) and llamada.attr == "cache_data"


def _persiste_en_disco(dec):
    if not isinstance(dec, ast.Call):
        return False
    return any(kw.arg == "persist" and getattr(kw.value, "value", None) == "disk"
               for kw in dec.keywords)


CACHEADAS = [n for n in ast.walk(arbol)
             if isinstance(n, ast.FunctionDef)
             and any(_es_cache_data(d) for d in n.decorator_list)]

print("\n── la clave de la caché lleva la versión del dato (regla #367) ──")

ok(len(CACHEADAS) >= 4, "data.py tiene funciones cacheadas que inspeccionar",
   f"encontradas {len(CACHEADAS)} — ¿cambió la forma del decorador?")

EN_DISCO = [f for f in CACHEADAS
            if any(_persiste_en_disco(d) for d in f.decorator_list)]

ok(len(EN_DISCO) >= 4, "data.py tiene cacheables con persist=\"disk\"",
   f"encontradas {len(EN_DISCO)}")

for f in EN_DISCO:
    args = [a.arg for a in f.args.args]
    ok(args[:2] == ["archivo", "sello"],
       f"{f.name}() lleva (archivo, sello) al frente de su clave",
       f"firma actual: ({', '.join(args)}) — sin el sello, un parquet nuevo "
       f"en R2 no se ve hasta un .clear()")

# El sello mismo NO puede persistir: sería la foto vieja decidiendo si la
# foto vieja está vieja.
_sello = [f for f in CACHEADAS if f.name == "_sello_r2"]
ok(len(_sello) == 1, "existe la cacheable del sello (_sello_r2)")
if _sello:
    ok(not any(_persiste_en_disco(d) for d in _sello[0].decorator_list),
       "_sello_r2 NO persiste en disco",
       "con persist el sello sobreviviría al reinicio y decidiría, con el "
       "valor viejo, que el dato viejo está al día")

print("\n── los wrappers pasan el sello ──")

NOMBRES = {f.name for f in EN_DISCO}
_llamadas = [n for n in ast.walk(arbol)
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id in NOMBRES]

ok(len(_llamadas) >= len(NOMBRES),
   "cada cacheable tiene al menos un llamador en data.py",
   f"{len(_llamadas)} llamadas para {len(NOMBRES)} funciones")

for c in _llamadas:
    segundo = c.args[1] if len(c.args) > 1 else None
    pasa_sello = (isinstance(segundo, ast.Call)
                  and isinstance(segundo.func, ast.Name)
                  and segundo.func.id == "sello_datos")
    ok(pasa_sello,
       f"la llamada a {c.func.id}() de la línea {c.lineno} pasa sello_datos()",
       "el segundo argumento tiene que ser sello_datos(archivo): es lo que "
       "hace que un archivo nuevo sea una entrada nueva")

print("\n── el refresco manual limpia TODO lo de ese parquet ──")

_limpiar = next((n for n in ast.walk(arbol)
                 if isinstance(n, ast.FunctionDef) and n.name == "limpiar_cache"),
                None)
ok(_limpiar is not None, "existe limpiar_cache()")
if _limpiar is not None:
    _cuerpo = ast.dump(_limpiar)
    for nombre in sorted(NOMBRES | {"_sello_r2"}):
        ok(f"'{nombre}'" in _cuerpo,
           f"limpiar_cache() limpia {nombre}",
           "el botón Refrescar decía «actualizado» y esta caché seguía "
           "sirviendo lo viejo — es el bug de 2026-09-03, que ya pasó una vez")

# ── Cierre ─────────────────────────────────────────────────────────────────
print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for f in _fallos:
        print(f"   · {f}")
    sys.exit(1)
print(f"✅ Todo OK (caché de datos: {len(EN_DISCO)} cacheables selladas, "
      f"{len(_llamadas)} llamadas revisadas)")
