"""Documentos SUNAT › «Control» (regla #759): la app contra SUNAT, sin red.

Las cuentas sobre documentos de mentira con cada caso medido —el recibo que la
propuesta no trae, el documento presentado un año después, las facturas en
dólares sin convertir, Diners, un mes que falla— y, en Chromium, la pieza.
"""
import io
import json
import re
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import sunat
import sunat_control as sc

ROOT = Path(__file__).parent
_CAB_RES = ("Tipo de Documento|Total Documentos|BI Gravado DG|IGV / IPM DG|BI Gravado DGNG|IGV / IPM DGNG|"
            "BI Gravado DNG|IGV / IPM DNG|Valor Adq. NG|ISC|ICBPER|Otros Trib/ Cargos|Total CP")
_CAB_TXT = ("RUC|Apellidos y Nombres o Razón social|Periodo|CAR SUNAT|Fecha de emisión|Fecha Vcto/Pago|Tipo CP/Doc.|"
            "Serie del CDP|Año|Nro CP o Doc. Nro Inicial (Rango)|Nro Final (Rango)|Tipo Doc Identidad|Nro Doc Identidad|"
            "Apellidos Nombres/ Razón  Social|BI Gravado DG|IGV / IPM DG|BI Gravado DGNG|IGV / IPM DGNG|BI Gravado DNG|"
            "IGV / IPM DNG|Valor Adq. NG|ISC|ICBPER|Otros Trib/ Cargos|Total CP|Moneda|Tipo de Cambio")


def registro():
    def f(car, per, serie, num, ruc, base, igv=0.0, ng=0.0, cdp="01", tc=1.0, cp=None, otros=0.0, mon="PEN"):
        return dict(periodo=per, car=car, fecha_emision=pd.Timestamp(per[:4] + "-" + per[4:] + "-10"), tipo_cdp=cdp,
                    serie=serie, numero=num, documento=f"{serie}-{num}", ruc_proveedor=ruc, proveedor="Prov " + ruc,
                    base_imponible=base, igv=igv, no_gravado=ng, total=base + igv + ng, moneda=mon, tipo_cambio=tc,
                    total_cp=base + igv + ng + otros if cp is None else cp, otros_sunat=otros)
    return pd.DataFrame([
        f("a1", "202609", "F001", "1", "111", 100, 18),
        f("a2", "202609", "F001", "2", "111", 50, 9, otros=3.0),
        f("usd", "202609", "E001", "3", "222", 1000, 180, tc=1.0, mon="USD"),
        f("mes", "202509", "E001", "4", "333", 200, 36),
        f("mon", "202609", "F002", "5", "444", 300, 54),
        f("din", "202609", "F004", "6", "555", 41.92, 7.56, cdp="42", cp=1462.92),
        f("raro", "202501", "E001", "21", "666", -6142.5, -368.55, cdp="07", cp=-2416.05),
    ])


def presentado():
    filas = [
        ("a1", "01", "F001", "1", "111", 100, 18, 0, "PEN", 1),       # igual
        ("a2", "01", "F001", "00000002", "111", 50, 9, 0, "PEN", 1),  # igual, con ceros en el número
        ("usd", "01", "E001", "3", "222", 3560, 640.8, 0, "USD", 3.56),  # sin convertir
        ("mes", "01", "E001", "4", "333", 200, 36, 0, "PEN", 1),      # en otro mes
        ("mon", "01", "F002", "5", "444", 0, 0, 0, "PEN", 1),         # otro monto
        ("luz", "14", "S130", "9", "777", 9000, 1620, 0, "PEN", 1),   # no está
        ("din2", "30", "F004", "00000006", "555", 41.92, 7.56, 0, "PEN", 1),  # otra anotación
    ]
    return pd.DataFrame([dict(periodo="202609", car=c, fecha="10/09/2026", tipo=t, serie=s, numero=n,
                              documento=f"{s}-{n}", ruc=r, proveedor="Prov " + r, base=b, igv=i, no_gravado=ng,
                              total=b + i + ng, moneda=m, tipo_cambio=tc)
                         for c, t, s, n, r, b, i, ng, m, tc in filas])


def control(fallidos=()):
    def res(n, total, otros=0.0, por=None):
        return dict(por=por or {"01": [n, total]}, tot=[n, total, otros])
    return dict(generado="2026-10-30T08:50:00+00:00", fallidos=list(fallidos), meses=[
        dict(p="202406", est="03", r1=res(9, 10.0), r4=None, det=0),       # el resumen no coincide
        dict(p="202501", est="03", r1=res(1, -2416.05), r4=None, det=1),
        dict(p="202509", est="01", r1=res(1, 236.0), r4=res(1, 236.0), det=1),
        dict(p="202609", est="01", r1=res(5, 1500.0, por={"01": [4, 37.0], "42": [1, 1462.92]}), r4=res(7, 15000.0), det=5, ticket="T1"),
        dict(p="202610", est="03", r1=res(3, 3.0), r4=None, det=0),        # el mes abierto
    ])


class Parseo(unittest.TestCase):
    def test_resumen_por_nombre_de_columna(self):
        r = sc.parsear_resumen(_CAB_RES + "\n01-Factura|294|1|2|0|0|0|0|3|0|0|148.53|205372.93\n"
                               "14-Recibo de Servicios Públicos Electrónico|2|1|1|0|0|0|0|0|0|0|0|1847.99\n"
                               "TOTAL |296|1|2|0|0|0|0|3|0|0|148.53|207220.92")
        self.assertEqual(r["por"]["01"], [294, 205372.93])
        self.assertEqual(r["por"]["14"], [2, 1847.99])
        self.assertEqual(r["tot"], [296, 207220.92, 148.53])

    def test_resumen_sin_datos(self):
        self.assertIsNone(sc.parsear_resumen(""))
        self.assertIsNone(sc.parsear_resumen('{"cod":422}'))

    def test_presentado_latin1_y_columnas(self):
        fila = ("0|Yo|202609|CAR9|07/09/2026||14|S001|2026|576913||6|777|LATAM AIRLINES PERÚ  S.A.|"
                "373.42|67.22|0|0|0|0|0.88|0|0|0|441.52|PEN|")
        d = sc.parsear_presentado((_CAB_TXT + "\n" + fila).encode("latin-1"), "202609")
        r = d.iloc[0].to_dict()
        self.assertEqual(r["car"], "CAR9")
        self.assertEqual(r["proveedor"], "LATAM AIRLINES PERÚ S.A.")
        self.assertEqual((r["tipo"], r["documento"], r["ruc"]), ("14", "S001-576913", "777"))
        self.assertEqual((r["base"], r["igv"], r["no_gravado"], r["total"]), (373.42, 67.22, 0.88, 441.52))


class Registro(unittest.TestCase):
    def test_total_sigue_siendo_la_suma_y_el_de_sunat_va_aparte(self):
        n = sunat._normalizar_registro(dict(montos=dict(
            mtoBIGravadaDG=41.92, mtoIgvIpmDG=7.56, mtoTotalCp=1462.92, mtoOtrosTrib=1.0, mtoIcbp=0.5)))
        self.assertAlmostEqual(n["total"], 49.48)
        self.assertEqual(n["total_cp"], 1462.92)
        self.assertEqual(n["otros_sunat"], 1.5)

    def test_mes_que_falla_conserva_las_filas_de_ayer(self):
        hoy = pd.DataFrame([dict(periodo="202609", car="a"), dict(periodo="202609", car="b")])
        ayer = pd.DataFrame([dict(periodo="202608", car="c"), dict(periodo="202608", car="a"),
                             dict(periodo="202607", car="d")])
        d = sc.rellenar_fallidos(hoy, ayer, ["202608"])
        self.assertEqual(sorted(d["car"]), ["a", "b", "c"])         # «a» no se repite; 202607 no falló
        self.assertEqual(sc.rellenar_fallidos(hoy, None, ["202608"]).shape[0], 2)
        self.assertEqual(sc.rellenar_fallidos(hoy, ayer, []).shape[0], 2)
        self.assertEqual(sc.rellenar_fallidos(pd.DataFrame(), ayer, ["202607"])["car"].tolist(), ["d"])


class Dolares(unittest.TestCase):
    def _df(self):
        fila = lambda car, dia, tc, base, mon="USD": dict(car=car, fecha_emision=pd.Timestamp(dia), moneda=mon, tipo_cambio=tc, base_imponible=base,  # noqa: E731
                                                          igv=base * .18, no_gravado=0.0, total=base * 1.18, total_cp=base * 1.18, otros_sunat=0.0)
        return pd.DataFrame([fila("a", "2025-07-03", 1.0, 100.0), fila("b", "2025-07-03", 3.5, 350.0), fila("c", "2025-07-05", 1.0, 100.0),
                             fila("d", "2025-07-09", 3.6, 360.0), fila("p", "2025-07-05", 1.0, 100.0, "PEN")])

    def test_el_cambio_sale_de_lo_presentado_del_dia_o_del_mas_cercano(self):
        d = sunat.convertir_sin_cambio(self._df(), {"c": 3.56}).set_index("car")
        self.assertEqual(d.loc["c", "tipo_cambio"], 3.56)              # lo presentado manda
        self.assertEqual(d.loc["c", "base_imponible"], 356.0)
        self.assertEqual(d.loc["a", "tipo_cambio"], 3.5)               # otro documento del mismo día
        self.assertEqual(d.loc["a", "total"], 413.0)
        self.assertTrue(d.loc["a", "cambio_estimado"])
        self.assertEqual(d.loc["b", "base_imponible"], 350.0)          # el que ya estaba bien
        self.assertFalse(d.loc["b", "cambio_estimado"])
        self.assertEqual(d.loc["p", "base_imponible"], 100.0)          # soles: no se toca

    def test_dia_sin_cambio_usa_el_mas_cercano_y_es_idempotente(self):
        d = sunat.convertir_sin_cambio(self._df())
        self.assertEqual(d.set_index("car").loc["c", "tipo_cambio"], 3.5)
        otra = sunat.convertir_sin_cambio(d)
        pd.testing.assert_frame_equal(d, otra)

    def test_sin_ninguna_referencia_queda_como_vino(self):
        d = sunat.convertir_sin_cambio(self._df().iloc[[0]])
        self.assertEqual(d.iloc[0]["base_imponible"], 100.0)
        self.assertEqual(sunat.convertir_sin_cambio(pd.DataFrame()).shape[0], 0)
        self.assertEqual(sc.cambios_presentados(presentado())["usd"], 3.56)


class Causa(unittest.TestCase):
    def test_sin_el_xml(self):
        c = sc.causa_documento
        self.assertEqual(c("Solo SUNAT", [1, 0, 1], [None] * 3)[0], "falta")
        self.assertEqual(c("Coincide", [1, 0, 1], [1, 0, 1])[0], "ok")
        self.assertEqual(c("Diferencia", [100, 18, 118], [100.4, 18, 118.4])[0], "centimos")
        self.assertEqual(c("Diferencia", [1216.01, 218.89, 1434.9], [1434.9, 258.28, 1693.18])[0], "igv_adentro")
        self.assertEqual(c("Diferencia", [36.19, 6.51, 42.7], [2937.63, 528.77, 3466.4])[0], "otro_doc")
        self.assertEqual(c("Diferencia", [1329.42, 230.56, 1559.98], [1322.02, 237.96, 1559.98])[0], "igv_parejo")
        self.assertEqual(c("Diferencia", [1674.2, 293.8, 1968], [1669.63, 298.37, 1968])[0], "reparto")
        self.assertEqual(c("Diferencia", [393.52, 41.32, 434.84], [411.86, 74.14, 486])[0], "tasa")
        self.assertEqual(c("Diferencia", [237.29, 42.71, 280], [220.34, 39.66, 260])[0], "monto")

    def test_con_el_xml_la_frase_dice_cuanto(self):
        c = sc.causa_documento
        lineas = [dict(importe=417.62, igv=79.99, isc=26.79, igv_porcentaje=18)]
        self.assertEqual(c("Diferencia", [444.41, 79.99, 524.4], [417.62, 75.17, 492.79], lineas)[0], "isc")
        exon = [dict(importe=230, igv=0, isc=0, igv_porcentaje=0), dict(importe=1000, igv=180, isc=0, igv_porcentaje=18)]
        ck, frase = c("Diferencia", [1230, 180, 1410], [1194.92, 215.08, 1410], exon)
        self.assertEqual(ck, "igv_parejo")
        self.assertIn("S/ 230.00 sin IGV", frase)
        self.assertIn("Sin la factura", c("Diferencia", [1329.42, 230.56, 1559.98], [1322.02, 237.96, 1559.98], [])[1])

    def test_mezcla_con_exonerados_no_es_otra_tasa(self):
        self.assertEqual(sc.causa_documento("Diferencia", [100, 14, 114], [120, 21.6, 141.6])[0], "monto")


class Cruce(unittest.TestCase):
    def test_cada_documento_en_su_estado(self):
        d = sc.clasificar_presentado(presentado(), registro()).set_index("car")
        self.assertEqual(d["est"].to_dict(), {"a1": "igual", "a2": "igual", "usd": "usd", "mes": "otro_mes",
                                              "mon": "monto", "luz": "falta", "din2": "otra_anot"})
        self.assertEqual(d.loc["mes", "p_app"], "202509")
        self.assertEqual(d.loc["usd", "app"], 1180.0)

    def test_un_mes_sin_convertir_necesita_el_cambio_1_en_la_app(self):
        r = registro()
        r.loc[r["car"] == "usd", "tipo_cambio"] = 3.56
        d = sc.clasificar_presentado(presentado(), r).set_index("car")
        self.assertEqual(d.loc["usd", "est"], "monto")

    def test_docs_con_otro_total_sin_tarjeta_propia(self):
        d = sc.docs_con_otro_total(registro())
        self.assertEqual(list(d), ["202501"])
        self.assertEqual(d["202501"][0][1:], ["E001-21", "Prov 666", -2416.05, -6511.05])
        # Tres soles de otros tributos no son un monto distinto.
        self.assertNotIn("F001-2", json.dumps(d))
        self.assertEqual(sc.docs_con_otro_total(registro().drop(columns="total_cp")), {})

    def test_el_estado_de_cada_mes(self):
        A = sc.armar_meses(control(), registro(), presentado())
        M = {m["p"]: m for m in A["meses"]}
        self.assertEqual(A["abierto"], "202610")
        self.assertEqual({p: m["e"] for p, m in M.items()},
                         {"202406": "dos", "202501": "sol", "202509": "ok", "202609": "tar", "202610": "ok"})
        self.assertEqual(M["202609"]["falta"], 1)
        self.assertEqual(M["202609"]["falta_s"], 10620.0)
        self.assertEqual(M["202609"]["a"]["42"], [1, 49.48])
        self.assertEqual((M["202609"]["t42"], M["202609"]["a42"]), (1462.92, 49.48))

    def test_lo_que_va_a_la_pieza_es_json_de_verdad(self):
        A = sc.armar_meses(control(), registro(), presentado())
        json.dumps(A, allow_nan=False)      # un NaN revienta `JSON.parse` en el navegador

    def test_un_mes_que_fallo_manda_sobre_lo_demas(self):
        A = sc.armar_meses(control(fallidos=["202609"]), registro(), presentado())
        self.assertEqual(next(m["e"] for m in A["meses"] if m["p"] == "202609"), "fallo")
        self.assertEqual(A["fallidos"], ["202609"])

    def test_resumen_del_aviso(self):
        A = sc.armar_meses(control(), registro(), presentado())
        r = sc.resumen_de(A["meses"])
        self.assertEqual((r["falta"], r["rev"], r["presentados"]), (1, 2, 7))
        self.assertEqual(r["por_estado"]["usd"], 1)

    def test_sin_presentado_no_revienta(self):
        A = sc.armar_meses(control(), registro(), None)
        self.assertEqual(sum(m["falta"] for m in A["meses"]), 0)

    def test_verificar_compara_por_car(self):
        reg = registro()
        vivo = reg[reg["periodo"] == "202609"].copy()
        vivo = vivo[vivo["car"] != "a1"]
        nuevo = vivo.iloc[[0]].assign(car="nuevo", documento="F009-9")
        r = sc.comparar_mes(pd.concat([vivo, nuevo]), reg, "202609")
        self.assertEqual((r["vivo"], r["app"]), (5, 5))
        self.assertEqual([x[1] for x in r["fa"]], ["F009-9"])
        self.assertEqual([x[1] for x in r["so"]], ["F001-1"])


class SoloLectura(unittest.TestCase):
    def test_el_control_solo_hace_get_contra_sunat(self):
        fuente = (ROOT / "sunat_control.py").read_text(encoding="utf-8")
        self.assertNotRegex(fuente, r"requests\.(post|put|delete|patch)")
        for prohibido in ("registroslibros/{periodo}/registra", "eliminapreliminar", "aceptapropuesta"):
            self.assertNotIn(prohibido, fuente)

    def test_el_sync_conserva_el_mes_y_sale_con_codigo(self):
        fuente = (ROOT / "herramientas/sunat_registro_sync.py").read_text(encoding="utf-8")
        self.assertIn("sunat_control.rellenar_fallidos", fuente)
        self.assertIn("_mes_con_reintentos(per)", fuente)
        self.assertIn("sys.exit(2)", fuente)

    def test_zip_lleva_siempre_la_lista_de_faltantes(self):
        class S3:
            def get_object(self, Bucket, Key):
                if Key == "malo":
                    raise OSError("no")
                return {"Body": io.BytesIO(b"<xml/>")}
        fake = type("D", (), {"get_s3_cliente": staticmethod(lambda: S3())})
        with patch.dict(sys.modules, {"data": fake}), patch.object(sc.st, "secrets", {"R2_BUCKET": "b"}):
            contenido, n, fallaron = sc.armar_zip([("a.xml", "k"), ("b.xml", "malo")], b"lista")
        z = zipfile.ZipFile(io.BytesIO(contenido))
        self.assertEqual(sorted(z.namelist()), ["a.xml", "faltantes.xlsx"])
        self.assertEqual((n, fallaron), (1, ["b.xml"]))


class Aviso(unittest.TestCase):
    def test_texto_del_renglon(self):
        from graficos.compras import sunat_control_pieza as p
        ahora = pd.Timestamp("2026-10-30T12:00:00+00:00")
        c = dict(generado="2026-10-30T08:50:00+00:00", fallidos=[], resumen=dict(falta=90, rev=7))
        t, grave = p.texto_aviso(c, ahora)
        self.assertEqual(t, "90 presentados no están en la app · 7 meses con cifras distintas")
        self.assertFalse(grave)
        self.assertIn("no se actualizó", p.texto_aviso(c | dict(fallidos=["202609"]), ahora)[0])
        self.assertTrue(p.texto_aviso(c | dict(fallidos=["202609"]), ahora)[1])
        viejo = p.texto_aviso(c | dict(generado="2026-10-20T08:50:00+00:00"), ahora)
        self.assertTrue(viejo[1])
        self.assertIn("no corre hace", viejo[0])
        self.assertIsNone(p.texto_aviso(None))
        self.assertTrue(p.texto_aviso(c | dict(resumen={}), ahora)[0].startswith("✓"))

    def test_motivos_del_lote_por_car(self):
        from graficos.compras import documentos_sunat as ds
        doc = pd.DataFrame([dict(car="b1", ruc_proveedor="1", serie="F1", numero="1", documento="F1-1",
                                 proveedor="BANCO DE CREDITO DEL PERU", tipo_cdp="01", fecha_emision="2026-01-01")])
        m = {}
        with patch.object(ds.sunat, "claves_xml_en_r2", return_value=frozenset()), \
                patch.object(ds.sunat, "solicitudes_en_r2", return_value=frozenset()), \
                patch.object(ds.sunat, "_registro_de_parquet", return_value=doc):
            pedibles, descartes = ds._candidatos_lote(doc, doc, motivos=m)
        self.assertEqual(pedibles, [])
        self.assertEqual(m["b1"], "de bancos y financieras")
        self.assertEqual(descartes, {"de bancos y financieras": 1})

    def test_vista_declarada_en_rail_y_pestana(self):
        import navegacion
        from graficos import sunat_reporte
        from graficos.compras import _sunat_vistas as sv
        self.assertIn("Control", sv.VISTAS)
        self.assertEqual(navegacion.ROTULO_PESTANA[("Documentos SUNAT", "Control")], "Control")
        self.assertIn("Control", json.dumps(sunat_reporte._SUNAT_RAIL_CATEGORIAS, default=str))


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def payload(**extra):
    A = sc.armar_meses(control(), registro(), presentado())
    return A | dict(resumen=sc.resumen_de(A["meses"]), aviso="", zip=None, verif={"202610": dict(vivo=0, app=0, fa=[], so=[], h="10:00")},
                    xml=dict(total=4, con=2, tope=25, pedibles=1, por_mes=[["202609", 3, 2], ["202610", 1, 0]],
                             falt=[["01/10/2026", "F9-1", "Prov A", 10.0, "pedir", "202610"],
                                   ["02/09/2026", "F9-2", "BANCO", 5.5, "banco", "202609"]])) | extra


@unittest.skipIf(sync_playwright is None, "sin Playwright")
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.br = cls.pw.chromium.launch()
        except Exception as e:
            cls.pw.stop()
            raise unittest.SkipTest(str(e))
        cls.pg = cls.br.new_page(viewport={"width": 1323, "height": 696}, accept_downloads=True)
        cls.pg.set_default_timeout(5000)
        cls.pg.route("https://scx.test.example/**", lambda r: r.fulfill(body='<div id="host"></div>', content_type="text/html"))
        cls.pg.goto("https://scx.test.example/")
        css = (ROOT / "graficos/compras/sunat_control.css").read_text(encoding="utf-8")
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"});window.mount=document.createElement("div");'
                        'const st=document.createElement("style");st.textContent=css;sr.append(st,window.mount);window.trig=[];}', css)
        js = (ROOT / "graficos/_xlsx.js").read_text(encoding="utf-8") + (ROOT / "graficos/compras/sunat_control.js").read_text(encoding="utf-8")
        cls.pg.add_script_tag(content=re.sub(r"export\s+default\s+function\s*\(component\)", "window.pieza=function(component)", js))

    @classmethod
    def tearDownClass(cls):
        cls.br.close()
        cls.pw.stop()

    def mount(self, P=None):
        self.pg.evaluate('P=>{window.trig=[];window.__sunatControl=null;window.mount.innerHTML="";window.pieza({data:P,parentElement:window.mount,setTriggerValue:(k,v)=>window.trig.push([k,v])})}', P or payload())

    def txt(self, sel):
        return self.pg.evaluate('s=>{const e=window.mount.querySelector(s);return e?e.innerText.replace(/\\n/g," | "):null}', sel)

    def clic(self, sel):
        self.pg.evaluate('s=>window.mount.querySelector(s).click()', sel)

    def test_meses_y_ficha(self):
        self.mount()
        self.assertIn("1", self.txt(".kpi:nth-child(4)"))
        filas = self.pg.evaluate('()=>[...window.mount.querySelectorAll(".caja tbody tr")].map(t=>t.innerText.replace(/\\t/g,";"))')
        self.assertEqual(len(filas), 5)
        self.assertTrue(filas[0].startswith("Octubre 2026"))
        self.clic('td button[data-v="202609"]')
        panel = self.txt(".panel")
        self.assertIn("Diners: la app muestra la comisión (S/ 49.48)", panel)
        self.assertIn("Prov 777", panel)
        self.assertIn("No están en la app 1", panel)
        self.clic('[data-a="grupo"][data-v="usd"]')
        self.assertIn("sin convertir a soles", self.txt(".panel"))
        self.clic('[data-a="grupo"][data-v="otro_mes"]')
        self.assertIn("en la app, en setiembre 2025", self.txt(".panel"))

    def test_estados_con_sus_frases(self):
        self.mount()
        self.clic('td button[data-v="202406"]')
        self.assertIn("Las dos cuentas de SUNAT no coinciden", self.txt(".causa"))
        self.clic('td button[data-v="202501"]')
        self.assertIn("E001-21", self.txt(".panel"))

    def test_filtros_de_indicadores(self):
        self.mount()
        self.clic('.kpi[data-v="reg"]')
        self.assertEqual(self.pg.evaluate('()=>window.mount.querySelectorAll(".caja tbody tr").length'), 1)
        self.clic('.kpi[data-v="reg"]')
        self.assertEqual(self.pg.evaluate('()=>window.mount.querySelectorAll(".caja tbody tr").length'), 5)

    def test_archivo_y_excel(self):
        self.mount()
        self.clic('td button[data-v="202609"]')
        self.clic('[data-a="archivo"]')
        self.assertEqual(self.pg.evaluate('()=>window.mount.querySelectorAll(".lado tbody tr").length'), 7)
        self.assertIn("su resumen dice 7", self.txt(".lado .causa").replace("igual que su resumen (7)", "su resumen dice 7"))
        self.clic('[data-a="archf"][data-v="falta"]')
        self.assertEqual(self.pg.evaluate('()=>window.mount.querySelectorAll(".lado tbody tr").length'), 1)
        with self.pg.expect_download() as d:
            self.clic('[data-a="excel"]')
        self.assertEqual(d.value.suggested_filename, "sunat_presentado_202609.xlsx")

    def test_verificar_pide_y_muestra(self):
        P = payload(verif={})
        self.mount(P)
        self.pg.wait_for_timeout(400)
        self.assertEqual(self.pg.evaluate('()=>window.trig.map(x=>x[0]+":"+x[1].p)'), ["verificar:202610"])  # el abierto, solo
        self.assertIn("Consultando", self.txt(".panel"))
        Q = payload(verif={"202610": dict(vivo=4, app=3, fa=[["30/10/2026", "F7-7", "Prov Z", 12.5]], so=[], h="11:00")})
        self.pg.evaluate('P=>window.pieza({data:P,parentElement:window.mount,setTriggerValue:(k,v)=>window.trig.push([k,v])})', Q)
        self.assertIn("Faltan 1 documentos", self.txt(".causa"))
        self.assertIn("F7-7", self.txt(".panel"))
        self.assertIn("1", self.txt('.kpi[data-v="act"] .v'))
        self.pg.evaluate('P=>{window.pieza({data:P,parentElement:window.mount,setTriggerValue:(k,v)=>window.trig.push([k,v])})}',
                         payload(verif={"202610": dict(error="SUNAT no respondió.")}))
        self.assertIn("SUNAT no respondió", self.txt(".panel"))

    def test_mes_que_fallo_se_avisa(self):
        A = sc.armar_meses(control(fallidos=["202609"]), registro(), presentado())
        self.mount(payload() | A | dict(verif={"202610": dict(vivo=0, app=0, fa=[], so=[], h="10:00")}))
        self.assertIn("SUNAT no respondió al actualizar setiembre 2026", self.txt(".sc > .causa"))

    def test_xml_buscar_sin_perder_el_foco_y_triggers(self):
        self.mount()
        self.clic('[data-a="tab"][data-v="xml"]')
        self.assertIn("2", self.txt(".kpi .v"))
        self.assertEqual(self.pg.evaluate('()=>window.mount.querySelectorAll(".xfilas tr").length'), 2)
        self.clic('.kpi[data-v="banco"]')
        self.assertEqual(self.pg.evaluate('()=>window.mount.querySelectorAll(".xfilas tr").length'), 1)
        self.clic('.kpi[data-v=""]')
        self.pg.evaluate('()=>window.mount.querySelector(".bus").focus()')
        self.pg.keyboard.type("prov", delay=20)
        estado = self.pg.evaluate('()=>[window.mount.getRootNode().activeElement.className,window.mount.querySelector(".bus").value,window.mount.querySelectorAll(".xfilas tr").length]')
        self.assertEqual(estado, ["bus", "prov", 1])
        self.clic('[data-a="pedir"]')
        self.clic('[data-a="zip"]')
        self.assertEqual(self.pg.evaluate('()=>window.trig.map(x=>x[0])').count("zip"), 1)
        self.assertEqual(self.pg.evaluate('()=>window.trig.map(x=>x[0])').count("pedir"), 1)
        self.assertEqual(self.pg.evaluate('()=>window.trig.find(x=>x[0]==="zip")[1].mes'), "202610")
        self.assertIn("Preparando", self.txt('[data-a="zip"]'))

    def test_no_desborda_y_cabe_en_celular(self):
        self.mount()
        self.assertEqual(self.pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)
        self.pg.set_viewport_size({"width": 390, "height": 844})
        try:
            self.mount()
            self.assertEqual(self.pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)
            ancho = self.pg.evaluate('()=>window.mount.querySelector(".panel").getBoundingClientRect().width')
            self.assertGreater(ancho, 300)
        finally:
            self.pg.set_viewport_size({"width": 1323, "height": 696})


if __name__ == "__main__":
    unittest.main()
