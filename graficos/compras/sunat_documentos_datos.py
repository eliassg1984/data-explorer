"""Documentos SUNAT: mismo transporte de celdas que la tabla de referencia (#741)."""
import datetime as dt
import hashlib
import json
import math
from numbers import Integral, Real
import pandas as pd
import sunat_control
from . import documentos_sunat as ds

sunat=ds.sunat


def filas_tabla(df_cruce,df_sire,xmls=frozenset()):
    """Reproduce las celdas canónicas sin I/O; los originales ya listados entran como dato."""
    if df_cruce is None or df_cruce.empty:
        return pd.DataFrame()
    # Los campos que el cruce no lleva, por `car`. `.get` con relleno: los
    # tests arman df sin estas columnas y `cruzar_con_parquet` es publica.
    _cols = ("tipo_nombre", "moneda", "tipo_cambio", "detraccion", "estado",
             "ruc_proveedor", "serie", "numero")
    extra = {}
    if df_sire is not None and "car" in df_sire.columns:
        for r in df_sire.to_dict("records"):
            extra[str(r.get("car") or "")] = {c: r.get(c) for c in _cols}

    # Los XML que ya están en R2, en UN listado (ver
    # `sunat.claves_xml_en_r2`). La key se arma con la MISMA función que usa
    # el sync que los sube, así que no hay forma de que difieran en el nombre.
    _xml_en_r2 = xmls

    filas = []
    # Diccionarios y no `iterrows()`, como en `cruzar_con_parquet` (#589).
    for r in df_cruce.to_dict("records"):
        car = str(r.get("car") or "")
        ex = extra.get(car, {})
        mon = str(ex.get("moneda") or "PEN").strip().upper() or "PEN"
        tc = ex.get("tipo_cambio") or 1.0
        total_sunat = ds._num(r.get("total_sunat"))
        # LA TABLA ESTA EN SOLES, las dos columnas: el registro del SIRE
        # viene en soles y el lado del sistema se convierte al agrupar
        # (ver `_parquet_agrupado_por_documento`). La segunda linea es el
        # importe como lo dice el PAPEL, y solo aparece en las 647 filas
        # en moneda extranjera del registro; en las otras 16.042 no hay
        # nada que aclarar.
        conv = ""
        if mon != "PEN" and total_sunat is not None:
            try:
                conv = (f"{sunat.simbolo_moneda(mon)} "
                        f"{total_sunat / float(tc):,.2f}")
            except (TypeError, ValueError, ZeroDivisionError):
                conv = ""
        _chips = ds._chips_de({"tipo_nombre": ex.get("tipo_nombre"),
                            "moneda": mon, "estado_cpe": ex.get("estado")})
        base_s, igv_s, tot_s = (ds._num(r.get("base_sistema")),
                                ds._num(r.get("igv_sistema")),
                                ds._num(r.get("total_sistema")))
        base_u, igv_u = ds._num(r.get("base_sunat")), ds._num(r.get("igv_sunat"))
        # Si la fila va a necesitar DOS lineas en alguna celda, la fila
        # entera mide `_ALTO_FILA_DOS` en vez de `ALTO_FILA_RANK`
        # (`getRowHeight`). Se decide aca y no en JS para no repetir la
        # comparacion en tres renderers.
        dos = bool(conv) or any(
            a is not None and b is not None
            and abs(a - b) > ds._TOLERANCIA_CENTAVOS
            for a, b in ((base_u, base_s), (igv_u, igv_s), (total_sunat, tot_s)))

        filas.append({
            "_car": car,
            "_chips": _chips,
            # Soles SIEMPRE: los importes de las dos fuentes ya estan en
            # soles cuando llegan aca. El simbolo de la moneda del papel
            # vive en `_conv`, que es el importe que si esta en esa moneda.
            "_sim": "S/",
            "_tipo": str(ex.get("tipo_nombre") or ""),
            "_base_sis": base_s, "_igv_sis": igv_s, "_total_sis": tot_s,
            "_conv": conv,
            "_dos": dos,
            # El sello del clic en el ojo/número (lo escribe `onCellClicked`):
            # es lo que distingue «abrí la ficha» de «elegí la fila».
            "_ver": 0,
            # El sello del clic en «Ingresar» (regla #683): mismo mecanismo
            # que `_ver`, pero abre la ventana de «Ingresar al Almacén».
            "_ing": 0,
            "Fecha": r.get("fecha_emision"),
            "Documento": str(r.get("documento") or ""),
            "Proveedor": str(r.get("proveedor") or "")
                         or str(r.get("proveedor_sistema") or ""),
            # Qué se compró (`tipo_compra.clasificar`, regla #640). Sin
            # tipo, una raya: el tooltip dice por qué no hubo pista.
            "Tipo": str(r.get("tipo") or "") or "—",
            "_tipo_por": str(r.get("tipo_por") or ""),
            "Base": base_u if base_u is not None else base_s,
            "IGV": igv_u if igv_u is not None else igv_s,
            "Total": total_sunat if total_sunat is not None else tot_s,
            "D": "D" if str(ex.get("detraccion") or "").strip().upper() == "D"
                 else "",
            # Sin fila del SIRE («Solo sistema») no hay comprobante que
            # bajar: la celda queda vacía, igual que la de un XML que falta.
            "XML": "✓" if ex and sunat.claves_original(ex)[1] in _xml_en_r2
                   else "",
            ds._COL_ESTADO: str(r.get("estado") or ""),
            # Sólo lo que SUNAT tiene y el sistema no: es lo único que hay
            # que ingresar. Sin fila del SIRE no hay XML que convertir.
            "Ingresar": ("Ingresar" if ex and str(r.get("estado") or "")
                         == "Solo SUNAT" else ""),
        })

    tv = pd.DataFrame(filas)
    tv["Fecha"] = pd.to_datetime(tv["Fecha"], errors="coerce").dt.strftime(
        "%d/%m/%Y").fillna("")

    return tv


def completar_pares(lx,la,pa,tc=1.0):
    """Los pares del conversor, más los que calzan al céntimo por importe: «Gin de
    la casa» no se parece a «GIN MG X 700 ML», pero vale lo mismo con su IGV."""
    pa=list(pa);usados={j for j in pa if j is not None}
    for i,x in enumerate(lx):
        if pa[i] is not None:continue
        imp=(x.get('importe') or 0)*tc;con=imp+(x.get('igv') or 0)*tc
        for j,a in enumerate(la):
            v=a[4] or 0
            if j not in usados and (abs(v-imp)<=.05 or abs(v-con)<=.05):
                pa[i]=j;usados.add(j);break
    return pa


def lineas_documento(fila,doc,d,xml=None):
    """Lo que trae la ficha al elegir un documento: las líneas del Almacén, las de
    la factura y la causa con ellas a la vista. `fila` es la de la pieza, `doc` la
    del SIRE (o lo que se sabe de un «Solo sistema») y `xml` los bytes, si hay."""
    raw=fila['raw'];L=ds._lineas_parquet_del_documento(d,doc)
    if 'FECHA_PROCESO_DOC' in L.columns:
        v=pd.to_datetime(L['FECHA_PROCESO_DOC'],errors='coerce').dropna();fp=f'{v.iloc[0]:%d/%m/%Y}' if len(v) else ''
    else:fp=''
    n=lambda x:valor(x)
    la=[[str(r.NOMBRE_PRODUCTO),n(r.CANTIDAD_COMPRA),str(r.UNIDAD_DE_INGRESO),n(r.PRECIO_UNIT),n(r.VALOR_COMPRA)] for r in L.itertuples()]
    bruto=sunat.lineas_xml(xml) if xml else []
    mon=str(doc.get('moneda') or 'PEN').strip().upper() or 'PEN'
    tc=float(doc.get('tipo_cambio') or 1.0) if mon!='PEN' else 1.0
    pa=[None]*len(bruto)
    if bruto and not L.empty:pa=[None if j is None else int(j) for j in ds._parear_lineas_sistema(bruto,L)]
    pa=completar_pares(bruto,la,pa,tc)
    en_soles=[{k:(x.get(k) or 0)*tc for k in ('importe','igv','isc')}|{'igv_porcentaje':x.get('igv_porcentaje')} for x in bruto]
    ck,ca=sunat_control.causa_documento(str(raw.get('estado') or ''),
        [ds._num(raw.get(k+'_sunat')) for k in ('base','igv','total')],
        [ds._num(raw.get(k+'_sistema')) for k in ('base','igv','total')],en_soles if xml else [])
    if ck=='otro_doc' and bruto and la:
        ca+=f" La factura tiene {len(bruto)} {'línea' if len(bruto)==1 else 'líneas'} y el Almacén {len(la)}."
    lx=[[str(x.get('descripcion') or ''),n(x.get('cantidad')),str(x.get('unidad') or ''),n(x.get('precio_unitario')),n(x.get('importe')),n(x.get('igv')),n(x.get('isc'))] for x in bruto]
    return dict(la=la,lx=lx,pa=pa,mon=mon,tc=tc,fp=fp,ck=ck,ca=ca)


def valor(v):
    if v is None:return None
    if isinstance(v,dict):return {str(k):valor(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [valor(x) for x in v]
    if isinstance(v,pd.DataFrame):return valor(v.to_dict('records'))
    if isinstance(v,(str,bool)):return v
    if pd.isna(v):return None
    if isinstance(v,(dt.datetime,dt.date,pd.Timestamp)):return v.isoformat()
    if isinstance(v,Integral):return int(v)
    if isinstance(v,Real):return float(v) if math.isfinite(float(v)) else None
    if hasattr(v,'item'):return valor(v.item())
    return str(v)


def armar(cruce,sire,xmls=frozenset(),contexto=None):
    tv=filas_tabla(cruce,sire,xmls);rows=[];vistos={}
    originales=valor(cruce) if cruce is not None else []
    claves=ds._claves_proveedor_cruce(cruce).tolist() if cruce is not None and not cruce.empty else []
    for i,r in enumerate(tv.to_dict('records')):
        raw=originales[i];fecha=pd.to_datetime(raw.get('fecha_emision'),errors='coerce')
        identidad=[raw.get(k) for k in ['car','ruc_proveedor','ruc_sistema','documento','documento_sistema','fecha_emision']]
        base=hashlib.sha256(json.dumps(identidad,ensure_ascii=False).encode()).hexdigest()[:24];n=vistos.get(base,0);vistos[base]=n+1
        r.update(id=base+':'+str(n),raw=raw,prov=claves[i],ruc=str(raw.get('ruc_proveedor') or raw.get('ruc_sistema') or ''),
            fecha=None if pd.isna(fecha) else fecha.date().isoformat())
        a,b=ds._num(raw.get('total_sunat')),ds._num(raw.get('total_sistema'))
        r['brecha']=None if a is None or b is None else b-a
        # Lo que da la lista sin abrir el XML; la ficha la afina al elegir (#760).
        r['_ck'],r['_ca']=sunat_control.causa_documento(str(raw.get('estado') or ''),
            [ds._num(raw.get(k+'_sunat')) for k in ('base','igv','total')],
            [ds._num(raw.get(k+'_sistema')) for k in ('base','igv','total')])
        rows.append(valor(r))
    P=dict(version=741,filas=rows,sire=valor(sire) if sire is not None else [],
        estados=list(ds._ESTADOS_CRUCE),estado_col=ds._COL_ESTADO,
        tolerancia=ds._TOLERANCIA_CENTAVOS,contexto=contexto or {})
    P['sello']=hashlib.sha256(json.dumps(P,ensure_ascii=False,allow_nan=False,sort_keys=True).encode()).hexdigest()
    return P
