"""Los gráficos chicos de las piezas (`graficos/mini.js` + `.css`, regla #847).

En Chromium, con la paleta de verdad (`estilos/_00_base.py`): que cada pieza
dibuje lo que dice —anchos proporcionales, el signo y el color sólo cuando
significan algo, la curva cortada en un hueco, la cápsula de la variación— y
que nada mida el DOM. Sin Playwright, la parte del navegador se salta.

    python test_mini.py            # las pruebas
    python test_mini.py --foto F   # además, la galería en el PNG F
"""
import re
import sys
import unittest
from pathlib import Path

AQUI = Path(__file__).parent
G = AQUI / "graficos"


def _raiz():
    """El `:root` de la paleta, tal cual lo ve la app."""
    s = (AQUI / "estilos" / "_00_base.py").read_text(encoding="utf-8")
    i = s.index(":root {")
    return s[i:s.index("\n    }", i) + 6]


# Ejemplos con forma de restaurante: los usan la prueba y la galería.
_EJEMPLOS = r"""
const proveedores=[{id:'p1',rotulo:'Distribuidora Andina',valor:48210,sub:'32 docs.'},
 {id:'p2',rotulo:'Carnes del Sur',valor:31540,sub:'18 docs.'},{id:'p3',rotulo:'Vinos Tacama',valor:12900},
 {id:'p4',rotulo:'Pesquera Callao',valor:9875},{id:'p5',rotulo:'Otros (14)',valor:6120}];
const faltantes=[{id:'f1',rotulo:'Lomo fino',valor:-3420},{id:'f2',rotulo:'Pulpo',valor:-1985},
 {id:'f3',rotulo:'Aceite de oliva',valor:-640}];
const cierres=['may','jun','jul','ago','set','oct','nov','dic','ene','feb','mar','abr'].map((m,i)=>(
 {id:i,rotulo:m,estado:['ok','ok','ojo','ok','mal','ok','ok','ojo','ok','ok',i===10?'nada':'ok','ok'][i],
  tip:`${m}: sin explicar S/ ${[310,280,910,350,2400,190,260,880,300,240,0,410][i]}`}));
const venta=[118,124,131,122,127,140,null,149,161,155,158,170];
window.__galeria=()=>`
<section><h3>Barras de un ranking · BarList</h3>${miniBarras(proveedores,{titulo:'Proveedor',columna:'Compra',elegido:'p2',clic:true})}</section>
<section><h3>Faltantes, en rojo porque es pérdida</h3>${miniBarras(faltantes,{tono:'neg'})}</section>
<section><h3>Doce cierres · Tracker</h3>${miniRastro(cierres,{pie:true})}</section>
<section><h3>% de costo contra la meta · CategoryBar</h3>${miniTramos([{hasta:28,estado:'ok'},{hasta:32,estado:'ojo'},{hasta:45,estado:'mal'}],{valor:30.8,meta:30,desde:20,tipValor:'Octubre: 30,8 %'})}</section>
<section><h3>Chispas · SparkChart</h3><p>Venta diaria ${miniChispa(venta,{ultimo:true,tip:'12 días'})} &nbsp; Por mes ${miniChispa(venta,{tipo:'barras',ultimo:true})}</p></section>
<section><h3>Variación · BadgeDelta</h3><p>Precio ${miniDelta(10.6,10,{sentido:'sube-malo'})} &nbsp; Venta ${miniDelta(94,100,{sentido:'sube-bueno'})} &nbsp; Cantidad ${miniDelta(88,100)} &nbsp; Igual ${miniDelta(100.2,100)} &nbsp; Sin base ${miniDelta(5,0)}</p></section>`;
"""


def galeria_html():
    css = ((G / "iconos.css").read_text(encoding="utf-8")
           + (G / "mini.css").read_text(encoding="utf-8"))
    js = (G / "iconos.js").read_text(encoding="utf-8") + (G / "mini.js").read_text(encoding="utf-8")
    return f"""<!doctype html><meta charset="utf-8"><style>{_raiz()}
body{{margin:0;padding:24px;background:var(--bg-card);font:13px 'DM Sans',sans-serif;color:var(--text-primary)}}
#g{{display:grid;grid-template-columns:repeat(2,minmax(0,560px));gap:28px 48px}}
h3{{margin:0 0 10px;font-size:12px;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em}}
p{{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:0}}
{css}</style><div id="g"></div><script>{js}{_EJEMPLOS}
document.getElementById('g').innerHTML=window.__galeria();</script>"""


def _chromium():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


class Fuente(unittest.TestCase):
    def test_no_mide_el_dom(self):
        js = (G / "mini.js").read_text(encoding="utf-8")
        for p in ("getBoundingClientRect", "offsetWidth", "clientWidth", "ResizeObserver"):
            self.assertNotIn(p, js, p)

    def test_sin_hex_sueltos(self):
        css = re.sub(r"/\*.*?\*/", "", (G / "mini.css").read_text(encoding="utf-8"), flags=re.S)
        self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,6}\b", css))

    def test_cita_la_licencia(self):
        self.assertIn("Apache 2.0", (G / "mini.js").read_text(encoding="utf-8"))


@unittest.skipIf(_chromium() is None, "sin Playwright")
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._pw = _chromium()().start()
        cls._b = cls._pw.chromium.launch()
        cls.pg = cls._b.new_page(viewport={"width": 1200, "height": 900})
        cls.pg.set_content(galeria_html())

    @classmethod
    def tearDownClass(cls):
        cls._b.close()
        cls._pw.stop()

    def ev(self, js):
        return self.pg.evaluate(js)

    def test_barras_proporcionales(self):
        r = self.ev("""() => [...document.querySelectorAll('section')[0].querySelectorAll('.mbl-f')].map(f => {
            const b = f.querySelector('.mbl-b').getBoundingClientRect().width, w = f.getBoundingClientRect().width;
            return [f.dataset.id, b / w, f.querySelector('.mbl-v').textContent, f.classList.contains('on')]; })""")
        self.assertEqual(r[0][0], "p1")
        self.assertAlmostEqual(r[0][1], 1, places=2)
        self.assertAlmostEqual(r[1][1], 31540 / 48210, places=2)
        self.assertEqual([x[3] for x in r], [False, True, False, False, False])
        self.assertTrue(r[0][2].startswith("S/ 48"))

    def test_faltantes_rojos_con_signo(self):
        r = self.ev("""() => { const s = document.querySelectorAll('section')[1];
            return [getComputedStyle(s.querySelector('.mbl-b')).backgroundColor,
                    getComputedStyle(document.documentElement).getPropertyValue('--danger-bg').trim(),
                    s.querySelector('.mbl-v').textContent]; }""")
        self.assertEqual(r[2][0], "−")
        self.assertNotEqual(r[0], "rgba(0, 0, 0, 0)")

    def test_rastro(self):
        r = self.ev("""() => [...document.querySelectorAll('.mrs-c')].map(c => [c.className, c.dataset.tip])""")
        self.assertEqual(len(r), 12)
        self.assertIn("mal", r[4][0])
        self.assertIn("nada", r[10][0])
        self.assertTrue(r[4][1].startswith("set: sin explicar"))
        pie = self.ev("() => document.querySelector('.mrs-pie').textContent")
        self.assertEqual(pie, "mayabr")

    def test_tramos_marcador_y_meta(self):
        r = self.ev("""() => { const b = document.querySelector('.mtr-b').getBoundingClientRect();
            const x = s => { const e = document.querySelector(s).getBoundingClientRect(); return (e.left + e.width / 2 - b.left) / b.width; };
            return [x('.mtr-m'), x('.mtr-meta'), [...document.querySelectorAll('.mtr-e span')].map(s => s.textContent)]; }""")
        self.assertAlmostEqual(r[0], (30.8 - 20) / 25, delta=0.01)
        self.assertAlmostEqual(r[1], (30 - 20) / 25, delta=0.01)
        self.assertEqual(r[2], ["20 %", "28 %", "32 %", "45 %"])

    def test_chispa_corta_en_el_hueco(self):
        d = self.ev("() => document.querySelector('.msp-l').getAttribute('d')")
        self.assertEqual(d.count("M"), 2)
        self.assertEqual(self.ev("() => document.querySelectorAll('.msp-b').length"), 11)
        self.assertEqual(self.ev("() => document.querySelectorAll('.msp-b.u').length"), 1)

    def test_delta(self):
        r = self.ev("() => [...document.querySelectorAll('.mdl')].map(e => [e.textContent, e.className])")
        self.assertEqual(r, [["▲ 6 %", "mdl mal"], ["▼ 6 %", "mdl mal"], ["▼ 12 %", "mdl neu"],
                             ["= 0 %", "mdl neu"], ["nuevo", "mdl neu"]])

    def test_escapa_el_texto(self):
        h = self.ev("() => miniBarras([{id:'x', rotulo:'<b>A&B</b>', valor:1}])")
        self.assertIn("&lt;b&gt;A&amp;B", h)

    def test_letra_minima(self):
        chicas = self.ev("""() => [...document.querySelectorAll('#g *')].filter(e => e.childNodes.length
            && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())
            && parseFloat(getComputedStyle(e).fontSize) < 12).map(e => e.className)""")
        self.assertEqual(chicas, [])


if __name__ == "__main__":
    if "--foto" in sys.argv:
        i = sys.argv.index("--foto")
        destino = sys.argv[i + 1]
        del sys.argv[i:i + 2]
        with _chromium()() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1180, "height": 600}, device_scale_factor=2)
            pg.set_content(galeria_html())
            pg.locator("#g").screenshot(path=destino)
            b.close()
    unittest.main()
