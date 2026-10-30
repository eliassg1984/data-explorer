"""Documentos SUNAT › «Control»: la app contra SUNAT, mes por mes (regla #759).

La cuenta y la lectura viven en `sunat_control.py`; acá se arma lo que recibe
la pieza (`sunat_control.js` + `.css`) y se atienden sus tres triggers:

  · `verificar` — consulta un mes a SUNAT en ese momento y lo compara con la
    app, documento por documento. La pieza lo pide sola para el mes abierto,
    después de dibujar: es el único que puede haber cambiado desde la madrugada.
  · `zip` — arma el ZIP de un mes con sus XML y la lista de los que no trae.
  · `pedir` — deja los pedidos de XML, con el mismo criterio que el lote de la
    tabla (`documentos_sunat._candidatos_lote`).

Todo corre dentro de un fragment: consultar a SUNAT no rehace la página.
"""
import datetime
import zoneinfo
from pathlib import Path

import pandas as pd
import streamlit as st

import sunat
import sunat_control as sc
from graficos.base import una_vez_por_corrida
from graficos.movil import css_movil, js_movil
from . import _sunat_vistas as sv
from . import documentos_sunat as ds

_DIR = Path(__file__).parent
_KEY = "sunat_control_pieza"
K_VERIF = "_sunat_ctl_verif"
K_ZIP = "_sunat_ctl_zip"
K_AVISO = "_sunat_ctl_aviso"
_K_VISTOS = "_sunat_ctl_vistos"
_DIAS_RECIENTE = 7
_MESES_XML = 12
_GRUPO = {"de bancos y financieras": "banco",
          "de proveedores que SUNAT nunca entrega": "nunca",
          "que ya fallaron (se reintentan desde su ficha)": "fallo",
          "ya pedidos": "pedido"}

_PIEZA = st.components.v2.component(
    "sunat_control",
    css=css_movil((_DIR / "sunat_control.css").read_text(encoding="utf-8")),
    js=js_movil((_DIR.parent / "_xlsx.js").read_text(encoding="utf-8")
                + (_DIR / "sunat_control.js").read_text(encoding="utf-8")),
)


@st.cache_data(ttl=3600, show_spinner=False)
def _meses(generado):
    """Los meses ya cruzados. `generado` es la clave: cambia con cada corrida."""
    return sc.armar_meses(sc.leer_control(), sunat._registro_de_parquet(), sc.leer_presentado())


def datos_xml(reg, xmls=None):
    """Los XML de los últimos 12 meses: cuántos hay y por qué faltan los demás."""
    tope = reg["fecha_emision"].max()
    ult = reg[reg["fecha_emision"] >= tope - pd.Timedelta(days=365)].copy()
    xmls = sunat.claves_xml_en_r2() if xmls is None else xmls
    motivos = {}
    pedibles, _ = ds._candidatos_lote(ult, ult, motivos=motivos)
    falt = []
    con = 0
    por_mes = {}
    for r in ult.sort_values("fecha_emision", ascending=False).to_dict("records"):
        mes = f"{r['fecha_emision']:%Y%m}"
        cuenta = por_mes.setdefault(mes, [0, 0])
        cuenta[0] += 1
        if sunat.claves_original(r)[1] in xmls:
            con += 1
            cuenta[1] += 1
            continue
        grupo = _GRUPO.get(motivos.get(str(r.get("car"))))
        if grupo is None:
            grupo = "reciente" if (tope - r["fecha_emision"]).days <= _DIAS_RECIENTE else "pedir"
        falt.append([f"{r['fecha_emision']:%d/%m/%Y}", r["documento"], r["proveedor"],
                     round(float(r["total"]), 2), grupo, mes])
    return {"total": len(ult), "con": con, "falt": falt, "pedibles": len(pedibles),
            "tope": ds._LOTE_MAX, "por_mes": [[m, n, c] for m, (n, c) in sorted(por_mes.items())]}


def _nuevo(que):
    """El valor del trigger, una sola vez: un rerun no lo vuelve a atender."""
    v = (st.session_state.get(_KEY) or {}).get(que)
    vistos = st.session_state.setdefault(_K_VISTOS, {})
    if not isinstance(v, dict) or not v.get("t") or vistos.get(que) == v["t"]:
        return None
    vistos[que] = v["t"]
    return v


def _hora():
    return datetime.datetime.now(zoneinfo.ZoneInfo("America/Lima")).strftime("%H:%M")


def _al_verificar():
    v = _nuevo("verificar")
    if not v or not sunat.periodo_valido(str(v.get("p"))):
        return
    p = str(v["p"])
    try:
        sunat.obtener_comprobantes.clear()
        r = sc.comparar_mes(sunat.obtener_comprobantes(p), sunat._registro_de_parquet(), p)
        r["h"] = _hora()
    except Exception:
        r = {"error": "SUNAT no respondió. Se puede volver a intentar en unos minutos."}
    st.session_state.setdefault(K_VERIF, {})[p] = r


def _armar_zip(mes):
    """`{mes, n, falt, bytes}`: los XML del mes y la lista de los que no trae."""
    reg = sunat._registro_de_parquet()
    ult = reg[reg["fecha_emision"].dt.strftime("%Y%m") == mes]
    xmls = sunat.claves_xml_en_r2()
    docs, sin = [], []
    for r in ult.to_dict("records"):
        k = sunat.claves_original(r)[1]
        if k in xmls:
            docs.append((f"{r['documento']}_{str(r['ruc_proveedor']).strip()}.xml", k))
        else:
            sin.append(r)
    motivos = {}
    ds._candidatos_lote(ult, ult, motivos=motivos)
    falt = pd.DataFrame([{
        "Fecha": f"{r['fecha_emision']:%d/%m/%Y}", "Documento": r["documento"],
        "Proveedor": r["proveedor"], "RUC": r["ruc_proveedor"], "Total S/": r["total"],
        "Por qué no está": motivos.get(str(r.get("car")), "Se puede pedir")} for r in sin],
        columns=["Fecha", "Documento", "Proveedor", "RUC", "Total S/", "Por qué no está"])
    contenido, n, fallaron = sc.armar_zip(docs, ds._excel_bytes(falt, hoja="Faltantes"))
    return {"mes": mes, "n": n, "falt": len(sin) + len(fallaron), "bytes": contenido}


def _al_zip():
    v = _nuevo("zip")
    if not v or not sunat.periodo_valido(str(v.get("mes"))):
        return
    try:
        st.session_state[K_ZIP] = _armar_zip(str(v["mes"]))
    except Exception:
        st.session_state[K_ZIP] = {"mes": str(v["mes"]), "error": True}
        st.session_state[K_AVISO] = "No se pudo armar el ZIP. Vuelve a intentarlo."


def _al_pedir():
    if not _nuevo("pedir"):
        return
    reg = sunat._registro_de_parquet()
    tope = reg["fecha_emision"].max()
    ult = reg[reg["fecha_emision"] >= tope - pd.Timedelta(days=365)]
    pedibles, _ = ds._candidatos_lote(ult, ult)
    pedidos = sum(1 for r in pedibles[:ds._LOTE_MAX] if sunat.solicitar_original(r))
    sunat.solicitudes_en_r2.clear()
    st.session_state[K_AVISO] = (
        f"Pedidos {pedidos}: la máquina del restaurante los trae de a uno, ~1 min cada uno."
        if pedidos else "No se pudo dejar ningún pedido.")


def datos(control, verif=None, zip_listo=None, aviso=""):
    """Lo que recibe la pieza."""
    reg = sunat._registro_de_parquet()
    base = _meses(control["generado"])
    return {**base, "resumen": control.get("resumen") or {}, "verif": verif or {},
            "xml": datos_xml(reg), "aviso": aviso,
            "zip": ({k: v for k, v in zip_listo.items() if k != "bytes"} if zip_listo else None)}


@una_vez_por_corrida
@st.fragment
def _tarjeta():
    with st.container(border=True, key="sunat_card_ctl"):
        control = sc.leer_control()
        reg = sunat._registro_de_parquet()
        if control is None or reg is None or reg.empty:
            st.info("Todavía no hay control: lo arma la actualización de cada madrugada.")
            return
        ss = st.session_state
        z = ss.get(K_ZIP)
        # El contenedor va SIEMPRE, aunque esté vacío: si apareciera recién con
        # el ZIP, la pieza cambiaría de lugar, se volvería a montar y perdería
        # la pestaña y lo elegido.
        fila = st.container(horizontal=True, vertical_alignment="center", gap="small",
                            key="sunat_ctl_zip_fila")
        if z and z.get("bytes"):
            with fila:
                st.download_button(f"⬇ Bajar el ZIP ({z['n']} XML + faltantes.xlsx)",
                                   data=z["bytes"], file_name=f"sunat_xml_{z['mes']}.zip",
                                   mime="application/zip", key="sunat_ctl_zip_btn",
                                   on_click="ignore", type="primary")
        _PIEZA(key=_KEY, data=datos(control, ss.get(K_VERIF), z, ss.get(K_AVISO, "")),
               on_verificar_change=_al_verificar, on_zip_change=_al_zip,
               on_pedir_change=_al_pedir, width="stretch")


def renderizar():
    _tarjeta()


# ── el aviso de las otras tres vistas ─────────────────────────────────────

def _ir_a_control():
    st.session_state[sv.K_VISTA] = sv.VISTA_CONTROL


def texto_aviso(control, ahora=None):
    """`(texto, grave)` del renglón de arriba, o None sin control. `grave` es lo
    que no puede esperar: un mes que falló o una revisión que dejó de correr."""
    if not control:
        return None
    ahora = ahora or pd.Timestamp.now(tz="UTC")
    try:
        horas = (ahora - pd.Timestamp(control["generado"])).total_seconds() / 3600
    except (KeyError, ValueError, TypeError):
        horas = 0
    res = control.get("resumen") or {}
    fallidos = control.get("fallidos") or []
    partes = []
    if fallidos:
        partes.append(f"⚠ {len(fallidos)} {'mes no se actualizó' if len(fallidos) == 1 else 'meses no se actualizaron'}: "
                      "se muestran datos anteriores")
    if horas > 36:
        partes.append(f"⚠ el control no corre hace {int(horas // 24)} días")
    if res.get("falta"):
        partes.append(f"{res['falta']:,} presentados no están en la app")
    if res.get("rev"):
        partes.append(f"{res['rev']} meses con cifras distintas")
    return " · ".join(partes) or "✓ La app tiene lo mismo que SUNAT", bool(fallidos or horas > 36)


def aviso():
    """El renglón de arriba: quien mira un total se entera de lo que le falta."""
    t = texto_aviso(sc.leer_control())
    if not t:
        return
    with st.container(horizontal=True, vertical_alignment="center", gap="small",
                      key="sunat_sello_control"):
        st.markdown(f'<span class="sunat-sello{" grave" if t[1] else ""}">Control con SUNAT: {t[0]}</span>',
                    unsafe_allow_html=True)
        st.button("Ver el control →", key="sunat_sello_ir", type="tertiary", on_click=_ir_a_control)
