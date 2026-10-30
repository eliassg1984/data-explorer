"""sunat_control.py — ¿lo que muestra la app es todo lo que tiene SUNAT? (regla #759)

La app lee `sunat_compras.parquet`, que sale de la PROPUESTA de SUNAT (la
lista de comprobantes que SUNAT reúne por su cuenta). Eso deja dos preguntas
sin contestar, y un total creíble las esconde:

  · ¿Llegó todo lo de la lista? Un mes que falla al actualizar, o un cambio
    en la consulta `busqueda` —que no está en el manual—, no da ningún error.
  · ¿Y lo PRESENTADO? Es la lista con lo que se agregó o corrigió. Medido el
    2026-10-30, en 20 meses: 6.601 documentos presentados, 90 de ellos
    (S/ 323.949) no están en la app — recibos de luz, gas e internet, boletos
    aéreos, formularios — y 9 facturas en dólares la app las tiene sin
    convertir, porque la propuesta las trae con tipo de cambio 1.

Dos fuentes oficiales lo contestan, las dos por la API y sin navegador:

  · **El resumen** (`URL_RESUMEN`, §5.35 del manual, ~2 s): totales por tipo
    de un mes, de la propuesta (tipo 1) o de lo presentado (tipo 4). Una
    segunda opinión, por otra puerta, sobre el mismo mes.
  · **El detalle de lo presentado** (`URL_EXPORTAR`, §5.40): un ticket, y con
    él un ZIP con un TXT. Las 20 exportaciones dieron exactamente lo que dice
    su resumen. Es sólo una exportación: los servicios que registran,
    reemplazan o eliminan son otros (POST y PUT) y acá NO se llaman.

Corre de madrugada con `herramientas/sunat_registro_sync.py`, que deja
`sunat_control.json` y `sunat_presentado.parquet` en R2; la vista
(`graficos/compras/sunat_control_pieza.py`) sólo lee. Las cuentas de abajo son
puras: las prueba `test_sunat_control.py` sin red.
"""

import datetime
import io
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
import streamlit as st

import sunat

ARCHIVO_CONTROL = "sunat_control.json"
ARCHIVO_PRESENTADO = "sunat_presentado.parquet"

URL_EXPORTAR = (sunat._BASE_SIRE + "/rce/preliminar/web/registroslibros"
                "/{periodo}/exportareportepreliminar")
URL_TICKETS = (sunat._BASE_SIRE
               + "/rvierce/gestionprocesosmasivos/web/masivo/consultaestadotickets")
URL_ARCHIVO = (sunat._BASE_SIRE
               + "/rvierce/gestionprocesosmasivos/web/masivo/archivoreporte")

TIPOS = {"00": "Otros", "01": "Factura", "03": "Boleta", "05": "Boleto aéreo",
         "07": "Nota de crédito", "08": "Nota de débito",
         "14": "Recibo de servicios públicos", "30": "Emitido por adquiriente",
         "42": "Tarjeta de crédito propia", "46": "Form. 617 o 1662"}
"""Los tipos de comprobante que se han visto en este registro (tabla 3 de la
RS 112-2021/SUNAT), con un nombre que se entiende. Uno que no esté acá se
muestra con su código."""

TIPO_TARJETA_PROPIA = "42"
"""Los documentos de quien emite su propia tarjeta y cobra con ella: en este
RUC, sólo Diners. Base + IGV es la comisión (2,85 % + IGV: 3,36-3,38 % del
total en los 30 documentos) y su `mtoTotalCp` se parece mes a mes a lo vendido
con esa tarjeta, así que NO es un monto distinto que revisar ni un costo."""

TOLERANCIA = 1.0
"""Soles de diferencia desde los que un documento cuenta como distinto: por
debajo son redondeos de la conversión."""

_ESPERA_TICKET = 4
_INTENTOS_TICKET = 30
_HILOS_ZIP = 8


# ===========================================================================
# LAS CUENTAS (puras)
# ===========================================================================

def _numero(texto):
    try:
        return float(str(texto).strip() or 0)
    except ValueError:
        return 0.0


def parsear_resumen(texto):
    """El TXT del resumen → `{"por": {tipo: [n, total]}, "tot": [n, total, otros]}`.

    Lee las columnas por NOMBRE: el manual ya les cambió el orden una vez entre
    versiones. `otros` son los otros tributos y cargos, que van en «Total CP» y
    no en la base."""
    lineas = [x for x in str(texto or "").splitlines() if "|" in x]
    if len(lineas) < 2:
        return None
    cab = [c.strip() for c in lineas[0].split("|")]
    try:
        i_n, i_t = cab.index("Total Documentos"), cab.index("Total CP")
    except ValueError:
        return None
    i_o = cab.index("Otros Trib/ Cargos") if "Otros Trib/ Cargos" in cab else None
    salida = {"por": {}, "tot": None}
    for linea in lineas[1:]:
        c = linea.split("|")
        if len(c) <= max(i_n, i_t):
            continue
        nombre = c[0].strip()
        n, total = int(_numero(c[i_n])), round(_numero(c[i_t]), 2)
        if nombre.upper().startswith("TOTAL"):
            otros = round(_numero(c[i_o]), 2) if i_o is not None else 0.0
            salida["tot"] = [n, total, otros]
        else:
            salida["por"][nombre[:2]] = [n, total]
    return salida if salida["tot"] else None


def parsear_presentado(crudo, periodo):
    """El TXT de lo presentado → un DataFrame con una fila por documento.

    `crudo` son bytes: SUNAT no siempre escribe UTF-8 («LATAM AIRLINES PERÚ»
    llega en latin-1)."""
    try:
        texto = crudo.decode("utf-8")
    except UnicodeDecodeError:
        texto = crudo.decode("latin-1")
    lineas = [x for x in texto.splitlines() if x.strip()]
    if not lineas:
        return pd.DataFrame()
    cab = [c.strip() for c in lineas[0].split("|")]
    filas = []
    for linea in lineas[1:]:
        r = dict(zip(cab, linea.split("|")))
        n = lambda *cols: sum(_numero(r.get(c)) for c in cols)  # noqa: E731
        serie = str(r.get("Serie del CDP") or "").strip()
        numero = str(r.get("Nro CP o Doc. Nro Inicial (Rango)") or "").strip()
        filas.append({
            "periodo": str(periodo),
            "car": str(r.get("CAR SUNAT") or "").strip(),
            "fecha": str(r.get("Fecha de emisión") or "").strip(),
            "tipo": str(r.get("Tipo CP/Doc.") or "").strip().zfill(2),
            "serie": serie, "numero": numero,
            "documento": f"{serie}-{numero}",
            "ruc": str(r.get("Nro Doc Identidad") or "").strip(),
            "proveedor": " ".join(str(r.get("Apellidos Nombres/ Razón  Social") or "").split()),
            "base": round(n("BI Gravado DG", "BI Gravado DGNG", "BI Gravado DNG"), 2),
            "igv": round(n("IGV / IPM DG", "IGV / IPM DGNG", "IGV / IPM DNG"), 2),
            "no_gravado": round(n("Valor Adq. NG"), 2),
            "total": round(n("Total CP"), 2),
            "moneda": str(r.get("Moneda") or "").strip(),
            "tipo_cambio": n("Tipo de Cambio"),
        })
    return pd.DataFrame(filas)


def rellenar_fallidos(df, previo, fallidos):
    """Los meses que SUNAT no dio, con sus filas de la corrida anterior.

    Hasta la regla #759 el parquet se subía SIN el mes que fallaba: desaparecía
    de la app con un total creíble, y el único aviso era un correo de GitHub.
    Mejor el dato de ayer, con el aviso en pantalla (`fallidos` del control),
    que un mes en cero. Un CAR que ya llegó por otro período no se repite."""
    if previo is None or previo.empty or not fallidos or "periodo" not in previo.columns:
        return df
    viejas = previo[previo["periodo"].astype(str).isin([str(p) for p in fallidos])]
    if "car" in viejas.columns and df is not None and not df.empty and "car" in df.columns:
        viejas = viejas[~viejas["car"].astype(str).isin(set(df["car"].astype(str)))]
    if viejas.empty:
        return df
    if df is None or df.empty:
        return viejas.reset_index(drop=True)
    return pd.concat([df, viejas], ignore_index=True)


def _partes(df):
    """Base + IGV + no gravado: lo que la app llama `total` (ver
    `sunat._normalizar_registro`)."""
    return df["base_imponible"] + df["igv"] + df["no_gravado"]


def _sin_ceros(s):
    return str(s or "").strip().lstrip("0")


def clasificar_presentado(pres, registro):
    """Cada documento presentado, contra la app. Agrega `est`, `p_app` y `app`.

    · `igual` — el mismo CAR, en el mismo mes y con el mismo monto.
    · `falta` — ni su CAR ni su serie, número y RUC están en la app.
    · `otra_anot` — está con otro CAR: el documento se anotó dos veces.
    · `otro_mes` — mismo CAR, pero en la app está en otro mes.
    · `usd` — en dólares, y en la app sin convertir: la propuesta lo trae con
      tipo de cambio 1 y la app lo suma como si fueran soles.
    · `monto` — mismo CAR y mes, con otro monto.

    Por CAR y no por serie-número: 1.422 documentos comparten serie-número con
    otro de un proveedor distinto (`documentos_sunat._fila_de`)."""
    if pres is None or pres.empty:
        return pres
    reg = registro.copy()
    reg["_partes"] = _partes(reg)
    por_car = {str(c): (str(p), float(v), float(t)) for c, p, v, t in zip(
        reg["car"], reg["periodo"], reg["_partes"], reg["tipo_cambio"])}
    por_doc = {(str(s).strip(), _sin_ceros(n), str(r).strip()): str(p) for s, n, r, p in zip(
        reg["serie"], reg["numero"], reg["ruc_proveedor"], reg["periodo"])}
    est, p_app, app = [], [], []
    for r in pres.to_dict("records"):
        partes = r["base"] + r["igv"] + r["no_gravado"]
        en_app = por_car.get(r["car"])
        if en_app is None:
            otra = por_doc.get((r["serie"], _sin_ceros(r["numero"]), r["ruc"]))
            est.append("otra_anot" if otra else "falta")
            p_app.append(otra or "")
            app.append(None)
            continue
        periodo, valor, tc = en_app
        p_app.append(periodo)
        app.append(round(valor, 2))
        if periodo != r["periodo"]:
            est.append("otro_mes")
        elif abs(partes - valor) <= TOLERANCIA:
            est.append("igual")
        elif (r["moneda"] == "USD" and tc <= 1.01
              and abs(partes - valor * (r["tipo_cambio"] or 1)) <= 2):
            est.append("usd")
        else:
            est.append("monto")
    return pres.assign(est=est, p_app=p_app, app=app)


def docs_con_otro_total(registro):
    """`{periodo: [[fecha, doc, proveedor, total SUNAT, partes], ...]}`: los
    documentos cuyo total de SUNAT no es la suma de sus partes.

    Sin los de tarjeta propia, que son todos así (`TIPO_TARJETA_PROPIA`). Un
    parquet anterior a la regla #759 no trae `total_cp`: no hay nada que decir."""
    if registro is None or "total_cp" not in registro.columns:
        return {}
    r = registro[registro["total_cp"].notna()].copy()
    if r.empty:
        return {}
    r["_partes"] = _partes(r)
    otros = (pd.to_numeric(r["otros_sunat"], errors="coerce").fillna(0)
             if "otros_sunat" in r.columns else 0.0)
    malos = r[((r["total_cp"] - r["_partes"] - otros).abs() > TOLERANCIA)
              & (r["tipo_cdp"].astype(str).str.zfill(2) != TIPO_TARJETA_PROPIA)]
    salida = {}
    for x in malos.sort_values("fecha_emision").to_dict("records"):
        salida.setdefault(str(x["periodo"]), []).append(
            [f"{pd.Timestamp(x['fecha_emision']):%d/%m/%Y}", x["documento"], x["proveedor"],
             round(float(x["total_cp"]), 2), round(float(x["_partes"]), 2)])
    return salida


def armar_meses(control, registro, presentado):
    """Lo que dibuja la vista: un renglón por mes, del más viejo al más nuevo.

    `e` es lo que dice la columna «La app contra la lista»:
    · `fallo` — SUNAT no respondió al actualizarlo; son datos de antes.
    · `dos` — el detalle de SUNAT y su resumen no coinciden entre sí (mayo y
      junio de 2024). No en el mes abierto: entre una consulta y otra pueden
      llegar comprobantes.
    · `sol` — los mismos documentos, y en alguno SUNAT da otro total.
    · `tar` — igual, y SUNAT muestra de Diners un total que no es su comisión.
    · `ok` — igual."""
    fallidos = {str(p) for p in control.get("fallidos") or ()}
    reg = registro.copy()
    reg["periodo"] = reg["periodo"].astype(str)
    reg["_tipo"] = reg["tipo_cdp"].astype(str).str.zfill(2)
    n_app = reg.groupby("periodo").size().to_dict()
    s_app = reg.groupby("periodo")["total"].sum().to_dict()
    por_tipo = {}
    for (p, t), g in reg.groupby(["periodo", "_tipo"]):
        por_tipo.setdefault(p, {})[t] = [len(g), round(float(g["total"].sum()), 2)]
    distintos = docs_con_otro_total(reg)
    clasif = clasificar_presentado(presentado, reg) if presentado is not None else None
    filas = {}
    if clasif is not None and not clasif.empty:
        for r in clasif.to_dict("records"):
            filas.setdefault(r["periodo"], []).append(
                [r["fecha"], r["tipo"], r["documento"], r["proveedor"], r["base"], r["igv"],
                 r["no_gravado"], r["total"], r["moneda"], r["est"], r["p_app"],
                 # Un NaN no es JSON: la pieza revienta al leerlo.
                 None if pd.isna(r["app"]) else r["app"]])
    abierto = max((m["p"] for m in control["meses"]), default=None)
    meses = []
    for m in control["meses"]:
        p = m["p"]
        t1 = (m.get("r1") or {}).get("tot")
        a = por_tipo.get(p, {})
        n = int(n_app.get(p, 0))
        por1 = (m.get("r1") or {}).get("por") or {}
        t42 = por1.get(TIPO_TARJETA_PROPIA, [0, 0])[1]
        a42 = a.get(TIPO_TARJETA_PROPIA, [0, 0])[1]
        docs = distintos.get(p, [])
        if p in fallidos:
            e = "fallo"
        elif t1 and t1[0] != n and p != abierto:
            e = "dos"
        elif docs:
            e = "sol"
        elif abs(t42 - a42) > TOLERANCIA:
            e = "tar"
        else:
            e = "ok"
        fp = filas.get(p, [])
        meses.append({
            "p": p, "est": m.get("est"), "e": e,
            "app": [n, round(float(s_app.get(p, 0.0)), 2)], "a": a,
            "r1": m.get("r1"), "r4": m.get("r4"), "det": m.get("det"),
            "ticket": m.get("ticket"), "t42": t42, "a42": a42,
            "docs": docs, "filas": fp,
            "falta": sum(1 for x in fp if x[9] == "falta"),
            "falta_s": round(sum(x[7] for x in fp if x[9] == "falta"), 2),
        })
    return {"generado": control.get("generado"), "abierto": abierto,
            "fallidos": sorted(fallidos), "nom": TIPOS, "meses": meses}


def resumen_de(meses):
    """Las cifras del aviso de arriba, para no releer todo en cada corrida."""
    cuenta = {}
    for m in meses:
        for x in m["filas"]:
            cuenta[x[9]] = cuenta.get(x[9], 0) + 1
    return {"falta": sum(m["falta"] for m in meses),
            "falta_s": round(sum(m["falta_s"] for m in meses), 2),
            "rev": sum(1 for m in meses if m["e"] in ("dos", "sol")),
            "presentados": sum(len(m["filas"]) for m in meses),
            "por_estado": cuenta}


def comparar_mes(vivo, registro, periodo):
    """«Verificar con SUNAT»: el mes en vivo contra lo que tiene la app."""
    reg = registro[registro["periodo"].astype(str) == str(periodo)]
    cars = set(registro["car"].astype(str))
    en_vivo = set(vivo["car"].astype(str)) if vivo is not None and not vivo.empty else set()

    def lista(df):
        return [[f"{pd.Timestamp(x['fecha_emision']):%d/%m/%Y}", x["documento"], x["proveedor"],
                 round(float(x["total"]), 2)]
                for x in df.sort_values("fecha_emision", ascending=False).to_dict("records")]
    faltan = vivo[~vivo["car"].astype(str).isin(cars)] if en_vivo else reg.iloc[0:0]
    sobran = reg[~reg["car"].astype(str).isin(en_vivo)]
    return {"vivo": len(en_vivo), "app": len(reg), "fa": lista(faltan), "so": lista(sobran)}


# ===========================================================================
# CONTRA SUNAT (sólo lectura)
# ===========================================================================

def _pedir(url, token, params=None, intentos=3):
    """Un GET con reintentos: SUNAT corta seguido y a veces no contesta en 60 s
    (el 2026-10-30, en dos de cada 100 llamadas). Devuelve la respuesta tal
    cual: un 422 es una respuesta, no una falla de red."""
    assert url.startswith(sunat._BASE_SIRE), "sólo se habla con el SIRE"
    ultimo = None
    for i in range(intentos):
        try:
            r = requests.get(url, params=params, timeout=sunat._TIMEOUT,
                             headers={"Authorization": f"Bearer {token}", "Accept": "*/*"})
        except requests.RequestException as e:
            ultimo = e
            time.sleep(5 * (i + 1))
            continue
        if r.status_code >= 500 and i < intentos - 1:
            time.sleep(5 * (i + 1))
            continue
        return r
    raise ultimo or RuntimeError("SUNAT no respondió")


def resumen_periodo(periodo, tipo, token):
    """El resumen de un mes, o None si SUNAT no lo tiene (un mes sin presentar
    responde 422 al pedir lo presentado)."""
    r = _pedir(sunat.URL_RESUMEN.format(periodo=periodo, tipo=tipo), token,
               {"codLibro": sunat.COD_LIBRO_RCE})
    return parsear_resumen(r.text) if r.status_code == 200 else None


def exportar_presentado(periodo, token):
    """`(DataFrame, ticket)` de lo presentado en un mes: pide la exportación,
    espera el ticket y baja el ZIP. Lanza si SUNAT no lo entrega."""
    r = _pedir(URL_EXPORTAR.format(periodo=periodo), token,
               {"codTipoArchivo": 0, "codOrigenEnvio": 2})
    if r.status_code != 200:
        raise RuntimeError(f"la exportación respondió {r.status_code}")
    ticket = r.json().get("numTicket")
    for _ in range(_INTENTOS_TICKET):
        time.sleep(_ESPERA_TICKET)
        e = _pedir(URL_TICKETS, token, {"perIni": periodo, "perFin": periodo, "page": 1,
                                        "perPage": 20, "numTicket": ticket})
        if e.status_code != 200:
            continue
        regs = e.json().get("registros") or []
        if not regs or not regs[0].get("archivoReporte"):
            continue
        x, a = regs[0], regs[0]["archivoReporte"][0]
        f = _pedir(URL_ARCHIVO, token, {
            "nomArchivoReporte": a["nomArchivoReporte"],
            # `codTipoAchivoReporte`, sin la «r»: así lo escribe SUNAT. Ver el
            # docstring de `sunat.py`.
            "codTipoArchivoReporte": a.get("codTipoAchivoReporte", "00"),
            "perTributario": periodo, "codProceso": x.get("codProceso"),
            "numTicket": ticket, "codLibro": sunat.COD_LIBRO_RCE})
        if f.status_code != 200:
            raise RuntimeError(f"la descarga respondió {f.status_code}")
        z = zipfile.ZipFile(io.BytesIO(f.content))
        return parsear_presentado(z.read(z.namelist()[0]), periodo), ticket
    raise RuntimeError("SUNAT no terminó de generar el archivo")


def construir_control(registro, estados, detalle, fallidos, presentado_previo, control_previo, log=print):
    """`(control, presentado)`, listos para subir. Lo llama el sync de madrugada.

    Lo presentado sólo se vuelve a pedir si su resumen cambió: cada exportación
    es un ticket en SUNAT y los meses cerrados casi nunca se mueven. Si una
    falla, queda lo de la corrida anterior."""
    token = sunat.obtener_token()
    previos = {m["p"]: m for m in (control_previo or {}).get("meses", [])}
    partes = []
    meses = []
    fallos_pres = []
    for p in sorted(estados):
        r1 = resumen_periodo(p, 1, token)
        # Sólo los meses presentados tienen esto («03» es No Presentado).
        r4 = resumen_periodo(p, 4, token) if estados[p] in ("01", "02") else None
        ticket = None
        if r4:
            ant = previos.get(p) or {}
            igual = (((ant.get("r4") or {}).get("tot") == r4["tot"])
                     and presentado_previo is not None
                     and (presentado_previo["periodo"] == p).any())
            if igual:
                partes.append(presentado_previo[presentado_previo["periodo"] == p])
                ticket = ant.get("ticket")
            else:
                try:
                    d, ticket = exportar_presentado(p, token)
                    partes.append(d)
                    if len(d) != r4["tot"][0]:
                        log(f"  {p}: el archivo trae {len(d)} y el resumen dice {r4['tot'][0]}")
                except Exception as e:
                    fallos_pres.append(p)
                    log(f"  {p}: no se pudo bajar lo presentado — {str(e)[:100]}")
                    if presentado_previo is not None:
                        partes.append(presentado_previo[presentado_previo["periodo"] == p])
                    ticket = ant.get("ticket")
        meses.append({"p": p, "est": estados[p], "r1": r1, "r4": r4,
                      "det": detalle.get(p), "ticket": ticket})
    presentado = (pd.concat(partes, ignore_index=True) if partes else pd.DataFrame())
    control = {"generado": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               "fallidos": sorted(str(p) for p in fallidos), "fallos_presentado": fallos_pres,
               "meses": meses}
    control["resumen"] = resumen_de(armar_meses(control, registro, presentado)["meses"])
    return control, presentado


# ===========================================================================
# LO QUE LEE LA APP
# ===========================================================================

@st.cache_data(ttl=600, show_spinner=False)
def leer_control():
    """El control de la última corrida, o None si todavía no hay ninguno."""
    import data

    if not data.secrets_disponibles():
        return None
    try:
        crudo = data.get_s3_cliente().get_object(
            Bucket=st.secrets["R2_BUCKET"], Key=ARCHIVO_CONTROL)["Body"].read()
        return json.loads(crudo.decode("utf-8"))
    except Exception:
        return None


def leer_presentado():
    """`sunat_presentado.parquet`, o None. Sin caché: la vista cachea lo armado."""
    import data

    try:
        crudo = data.get_s3_cliente().get_object(
            Bucket=st.secrets["R2_BUCKET"], Key=ARCHIVO_PRESENTADO)["Body"].read()
        return pd.read_parquet(io.BytesIO(crudo))
    except Exception:
        return None


def armar_zip(docs, faltantes_xlsx):
    """`(bytes del ZIP, n de XML, los que no se pudieron leer)`.

    `docs` son `[(nombre en el ZIP, clave en R2)]`. El ZIP lleva SIEMPRE la
    lista de los que no trae: si no, parece completo sin estarlo. Por mes y no
    por año: 300 XML son 8 MB y 30 s con ocho hilos; 12 meses no caben en la
    memoria de Community Cloud."""
    import data

    s3 = data.get_s3_cliente()
    bucket = st.secrets["R2_BUCKET"]

    def uno(par):
        try:
            return par[0], s3.get_object(Bucket=bucket, Key=par[1])["Body"].read()
        except Exception:
            return par[0], None

    with ThreadPoolExecutor(_HILOS_ZIP) as ex:
        leidos = list(ex.map(uno, docs))
    buf = io.BytesIO()
    fallaron = [n for n, b in leidos if b is None]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in leidos:
            if contenido is not None:
                z.writestr(nombre, contenido)
        z.writestr("faltantes.xlsx", faltantes_xlsx)
    return buf.getvalue(), len(leidos) - len(fallaron), fallaron
