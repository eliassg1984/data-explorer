"""
ver_figura.py — vuelca a PNG los gráficos de un dashboard, SIN navegador.

    python herramientas/ver_figura.py Ventas
    python herramientas/ver_figura.py Ventas -s ventas_comp_vista=Descomposición
    python herramientas/ver_figura.py --lista

Por qué existe (2026-08-12): hasta ahora la única forma de VER un gráfico
era levantar la app y hacer 4-5 clics encadenados, cada uno con su rerun.
Cuando eso no estaba disponible se terminaba "verificando" por medición del
DOM — que prueba que el gráfico FUNCIONA, nunca que SE VE. Así se escapó un
legend que existía, respondía al clic y era ilegible: estaba en la misma
franja que las anotaciones de feriado. Un PNG lo habría mostrado en 10
segundos. Ver `arquitectura.md` regla #91.

Cómo funciona: no levanta Streamlit. Parchea EN CALIENTE las funciones de
UI del módulo `streamlit` ya importado (`st.pills`, `st.columns`, …) por
stubs que devuelven el default, y `st.plotly_chart` por uno que guarda la
figura. Se parchea el módulo real —no se reemplaza en `sys.modules`— a
propósito: así `st.secrets` y `@st.cache_data` siguen siendo los de verdad
y los datos salen de R2 igual que en producción, con la misma caché en
disco.

Limitaciones honestas:
  · Renderiza el estado que producen los DEFAULTS de cada widget. Para
    llegar a otra vista hay que forzarla con `-s <key>=<valor>` (la key es
    la del widget en el .py; el inspector de la app las muestra).
  · No valida CSS ni layout de Streamlit — sólo lo que dibuja Plotly.
    Para el layout de la página sigue estando `auditar_layout.js`.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import logging
import pathlib
import sys

# Importar el proyecto desde la raíz aunque el script se invoque por ruta.
_RAIZ = pathlib.Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

if hasattr(sys.stdout, "reconfigure"):      # consola cp1252 de Windows
    sys.stdout.reconfigure(encoding="utf-8")
logging.getLogger("streamlit").setLevel(logging.ERROR)

import streamlit as st                                       # noqa: E402

SALIDA = _RAIZ / "herramientas" / "_figuras"
# Ancho de referencia: el del card en un monitor de 1912px, que es donde se
# mira la app. Las figuras no fijan `width` (se estiran al contenedor), así
# que acá hay que elegir uno o Plotly usa su default de 700 y el gráfico se
# ve más apretado de lo que se ve en pantalla.
ANCHO = 1550


class _Caja:
    """Reemplazo universal de los contenedores de Streamlit.

    Sirve de context manager (`with st.container(): ...`), se deja llamar y
    devuelve algo inofensivo ante cualquier atributo. Con esto alcanza para
    `container`, `expander`, `popover`, `form`, `sidebar`, `empty`, …
    """

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def __call__(self, *_a, **_k):
        return _Caja()

    def __getattr__(self, _n):
        return _Caja()


class _Estado(dict):
    """`st.session_state` de mentira. El de verdad no funciona fuera de
    `streamlit run` ("Session state does not function…"), y sin él el rail no
    puede resolver qué item está activo: `_render_rail` lo lee de ahí."""

    def __getattr__(self, n):
        try:
            return self[n]
        except KeyError as e:
            raise AttributeError(n) from e

    def __setattr__(self, n, v):
        self[n] = v


def _valor(txt):
    """Los -s llegan como texto; convertir lo obvio. Sin esto un
    `-s algo=false` entraría como la cadena "false", que es TRUTHY."""
    b = txt.strip().lower()
    if b in ("true", "sí", "si", "1"):
        return True
    if b in ("false", "no", "0"):
        return False
    try:
        return int(txt)
    except ValueError:
        return txt


def _instalar_stubs(overrides: dict, figuras: list):
    """Parchea las funciones de UI de `st`. Devuelve el dict original para
    poder restaurarlo (importa si algún día esto corre dentro de un test)."""
    previo = {n: getattr(st, n, None) for n in dir(st)}

    def _elegido(key, por_defecto):
        """El valor forzado con -s si lo hay; si no, el default del widget."""
        return overrides.get(key, por_defecto) if key else por_defecto

    # ── Widgets que DEVUELVEN una selección ────────────────────────────────
    def _pills(label, options, *a, key=None, default=None, **k):
        opts = list(options)
        if k.get("selection_mode") == "multi":
            return _elegido(key, default if default is not None else [])
        return _elegido(key, default if default is not None
                        else (opts[0] if opts else None))

    def _checkbox(label, value=False, *a, key=None, **k):
        return bool(_elegido(key, value))

    def _toggle(label, value=False, *a, key=None, **k):
        return bool(_elegido(key, value))

    def _selectbox(label, options, index=0, *a, key=None, **k):
        opts = list(options)
        return _elegido(key, opts[index] if opts else None)

    def _radio(label, options, index=0, *a, key=None, **k):
        opts = list(options)
        return _elegido(key, opts[index] if opts else None)

    def _multiselect(label, options, default=None, *a, key=None, **k):
        return _elegido(key, list(default) if default else [])

    def _slider(label, min_value=0, max_value=100, value=None, *a, key=None, **k):
        return _elegido(key, value if value is not None else min_value)

    def _number_input(label, min_value=None, *a, value=None, key=None, **k):
        return _elegido(key, value if value is not None else (min_value or 0))

    def _text_input(label, value="", *a, key=None, **k):
        return _elegido(key, value)

    def _date_input(label, value=None, *a, key=None, **k):
        return _elegido(key, value)

    def _button(*_a, **_k):
        return False        # nadie "hace clic" en un render headless

    def _columns(spec, *_a, **_k):
        n = spec if isinstance(spec, int) else len(spec)
        return [_Caja() for _ in range(n)]

    def _tabs(labels, *_a, **_k):
        return [_Caja() for _ in labels]

    # ── La razón de ser del script ─────────────────────────────────────────
    def _plotly_chart(fig, *_a, key=None, **_k):
        figuras.append((key, fig))
        return None

    def _fragment(fn=None, **_k):
        """`@st.fragment` como passthrough. Se aplica al IMPORTAR el módulo,
        así que esto sólo sirve si los stubs se instalan ANTES de importar
        `graficos` — main() lo hace en ese orden a propósito."""
        if fn is None:
            return lambda f: f
        return fn

    def _aviso(pref):
        def _f(msg="", *_a, **_k):
            print(f"  [{pref}] {str(msg)[:160]}")
            return _Caja()
        return _f

    stubs = {
        "fragment": _fragment, "experimental_fragment": _fragment,
        # Que los errores se VEAN: si R2 falla, data.py llama a st.error y
        # tragarlo dejaría un "sin datos" sin explicación.
        "error": _aviso("error"), "warning": _aviso("aviso"),
        "pills": _pills, "segmented_control": _pills,
        "checkbox": _checkbox, "toggle": _toggle,
        "selectbox": _selectbox, "radio": _radio, "multiselect": _multiselect,
        "slider": _slider, "select_slider": _slider,
        "number_input": _number_input, "text_input": _text_input,
        "date_input": _date_input,
        "button": _button, "download_button": _button, "form_submit_button": _button,
        "columns": _columns, "tabs": _tabs,
        "plotly_chart": _plotly_chart,
    }
    # Contenedores y salidas de texto: todo lo mismo, no dibujan nada acá.
    for nombre in ("container", "expander", "popover", "form", "empty",
                   "sidebar", "status", "spinner", "markdown", "caption",
                   "write", "info", "success", "metric",
                   "dataframe", "table", "divider", "subheader", "header",
                   "title", "text", "json", "code", "image", "altair_chart",
                   "pyplot", "progress", "toast", "badge", "html", "rerun",
                   "stop", "audio", "video", "link_button", "page_link"):
        stubs[nombre] = _Caja()

    for nombre, fn in stubs.items():
        setattr(st, nombre, fn)
    # Sembrado con los overrides: así un -s sirve tanto para un widget
    # (que lee su key) como para el rail (que lee su state_key).
    st.session_state = _Estado(overrides)
    return previo


def _cargar_df(reporte, cfg):
    """El MISMO camino que app.py: por rango si el reporte lo usa, si no
    completo. Con `persist="disk"` esto es instantáneo a partir del 2º uso."""
    from data import cargar, cargar_rango

    col_rango = cfg.get("carga_por_rango")
    if not col_rango:
        return cargar(cfg["archivo"])
    hoy = _dt.date.today()
    return cargar_rango(cfg["archivo"], col_rango, hoy.replace(day=1), hoy)


def main():
    ap = argparse.ArgumentParser(
        description="Vuelca a PNG los gráficos de un dashboard, sin navegador.")
    ap.add_argument("reporte", nargs="?", help='p.ej. "Ventas"')
    ap.add_argument("-s", "--set", action="append", default=[], metavar="KEY=VALOR",
                    help="fuerza el valor de un widget por su key "
                         "(repetible). Ej: -s ventas_comp_vista=Descomposición")
    ap.add_argument("--lista", action="store_true",
                    help="lista los reportes con dashboard y sale")
    args = ap.parse_args()

    overrides = {}
    for par in args.set:
        if "=" not in par:
            print(f"--set espera KEY=VALOR, recibí: {par!r}")
            return 1
        k, v = par.split("=", 1)
        overrides[k.strip()] = _valor(v)

    # ORDEN IMPORTANTE: los stubs van ANTES de importar `graficos`, porque
    # `@st.fragment` se aplica al importar y hay que neutralizarlo. El resto
    # de las llamadas (st.pills, …) se resuelven contra el módulo en cada
    # invocación, así que para esas daría igual.
    figuras = []
    _instalar_stubs(overrides, figuras)

    from data import REPORTES
    from graficos import _DASHBOARDS

    if args.lista or not args.reporte:
        print("Reportes con dashboard:")
        for r in sorted(_DASHBOARDS):
            print("  ", r)
        return 0

    if args.reporte not in _DASHBOARDS:
        print(f"'{args.reporte}' no tiene dashboard. Usá --lista.")
        return 1

    cfg = REPORTES.get(args.reporte, {})
    print(f"Cargando datos de {args.reporte} ({cfg.get('archivo','?')})…")
    df = _cargar_df(args.reporte, cfg)
    if df is None or df.empty:
        print("Sin datos: R2 no respondió o el parquet vino vacío.")
        return 1
    print(f"  {len(df):,} filas")

    try:
        _DASHBOARDS[args.reporte](df, args.reporte, df_full=df, tabla_cb=lambda _d: None)
    except Exception as e:
        # No se aborta: puede haber figuras válidas ya capturadas antes del
        # fallo, y verlas suele explicar el fallo.
        print(f"  ⚠ el dashboard cortó con {type(e).__name__}: {str(e)[:200]}")

    if not figuras:
        print("No se capturó ninguna figura. ¿La vista por defecto dibuja "
              "alguna? Probá forzarla con -s.")
        return 1

    SALIDA.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() else "_" for c in args.reporte).lower()
    escritos = []
    for i, (key, fig) in enumerate(figuras, 1):
        nombre = f"{slug}_{i:02d}_{(key or 'sin_key')[:50]}.png"
        destino = SALIDA / nombre
        ancho = fig.layout.width or ANCHO
        alto = fig.layout.height or 500
        # El tamaño va en el LAYOUT, no como kwargs de write_image (por
        # kwarg, kaleido ni siquiera intenta ajustar los márgenes).
        #
        # `automargin` va SOLO para exportar: los dashboards usan márgenes
        # apretados (l=10, b=10) y en el navegador entran igual porque
        # Plotly los expande solo — verificado contra el DOM, donde ni el
        # eje Y ni las fechas se cortan. kaleido no hace esa expansión y
        # recortaba las etiquetas, o sea que el PNG mostraba un problema
        # que en la app NO existe. Con automargin el PNG se parece a la
        # pantalla; a cambio, los MÁRGENES del PNG no son fieles al píxel:
        # para juzgar recortes, el navegador manda.
        fig.update_layout(width=ancho, height=alto)
        fig.update_xaxes(automargin=True)
        fig.update_yaxes(automargin=True)
        fig.write_image(str(destino), scale=2)
        escritos.append(destino)
        print(f"  → {destino.relative_to(_RAIZ)}  ({ancho}x{alto})")

    print(f"\n{len(escritos)} figura(s) en {SALIDA.relative_to(_RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
