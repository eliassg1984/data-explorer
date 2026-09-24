"""
envio_receta.py — la receta o el combo de «Nueva receta», listos para
mandar por correo DESDE EL GMAIL DE QUIEN ESTÁ LOGUEADO.

Piezas puras (sin Streamlit), que reciben un `resumen` ya armado por
`formulario_receta._resumen_envio`:

  - `pdf_receta(resumen)`   → bytes del PDF (A4, una tabla + el desglose).
  - `excel_receta(resumen)` → bytes del .xlsx (misma información, editable).
  - `armar_correo` + `enviar_correo` → el envío AUTOMÁTICO con los dos
    adjuntos, por el SMTP de Gmail. Es el camino principal desde que se
    pidió «debe adjuntarlo automáticamente» (regla #503); necesita
    `GMAIL_REMITENTE` y `GMAIL_APP_PASSWORD` en secrets.
  - `url_gmail(resumen, correo)` → el camino de reserva, SIN esos secrets:
    abre «Redactar» del Gmail del usuario con asunto y cuerpo escritos, y
    los adjuntos van a mano. Lo que sigue explica por qué nació así.

POR QUÉ «ABRIR SU GMAIL» Y NO ENVIAR DESDE EL SERVIDOR (2026-09-23). Se
pidió que el correo salga con la dirección de quien está logueado. El login
de esta app es el de Streamlit Community Cloud («Only specific people can
view this app»): le dice a la app QUIÉN es (`st.user.email`), pero no le da
permiso para mandar correo en su nombre. Para eso hay dos caminos, y los
dos cuestan más de lo que resuelven hoy:

  - SMTP con contraseña de aplicación: manda desde UNA cuenta fija (la de
    la contraseña), no desde la de cada usuario.
  - Gmail API con permiso `gmail.send` por usuario: exige un `[auth]` propio
    en secrets, y con eso Cloud deja de llenar `st.user.email` a su manera
    (ver el docstring de `aviso_ingreso.py`) — se rompe el aviso de ingreso
    por Telegram — además de configurar Google Cloud y re-autorizar cada
    hora.

Abrir la ventana de redactar de SU Gmail no necesita nada de eso: el
correo sale de su cuenta porque lo manda él, con sus contactos para
autocompletar los destinatarios. Lo único que no se puede hacer desde una
página web es ADJUNTAR en su Gmail, así que los dos archivos se descargan
con un clic y se arrastran. Si algún día hace falta que salga sin ese paso,
el camino es la Gmail API, y `pdf_receta`/`excel_receta` se reusan tal cual.

El PDF se dibuja con matplotlib (ya es dependencia; mismo criterio que
`sunat.ficha_pdf`) usando `Figure` y no `pyplot`: `st.download_button` con
`data=callable` lo corre en OTRO hilo, y `pyplot` es estado global.
"""

import io
import re
import smtplib
import unicodedata
from email.message import EmailMessage
from urllib.parse import quote, urlencode

# Cuántas líneas entran en el CUERPO del correo antes de cortar con «y N
# más». El enlace viaja como URL: con recetas largas se pasaba de lo que
# Gmail acepta en `body`, y el detalle completo va en los adjuntos igual.
_MAX_LINEAS_CUERPO = 25
# Filas de la tabla por página del PDF (A4 vertical, cuerpo de 8,5 pt).
_FILAS_POR_PAGINA = 30


def _soles(v):
    return f"S/ {v:,.2f}"


def _num(v):
    """Cantidad o precio unitario, sin ceros de relleno y hasta 4
    decimales: las recetas del sistema vienen en gramos (0,0381 soles el
    gramo) y con `:,.2f` salían «0.04». Mismo criterio que la tabla de
    `formulario_receta._num`."""
    return f"{round(float(v), 4):,.4f}".rstrip("0").rstrip(".")


def nombre_archivo(resumen, extension):
    """«receta_lomo-saltado.pdf»: sin tildes ni espacios, para que el
    adjunto no llegue con el nombre roto en otro cliente de correo."""
    base = unicodedata.normalize("NFKD", resumen["nombre"] or "sin-nombre")
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "sin-nombre"
    prefijo = "combo" if resumen["tipo"] == "Combo" else "receta"
    return f"{prefijo}_{base[:60]}.{extension}"


def _filas_desglose(resumen):
    """Las filas del panel de precios, en el MISMO orden que en pantalla."""
    filas = [("Costo total", resumen["costo_total"])]
    if resumen["precio_venta"] > 0:
        filas += [
            ("Precio de venta", resumen["precio_venta"]),
            ("Precio neto (base)", resumen["base"]),
            (f"Recargo al consumo ({resumen['pct_recargo']:.0f}%)", resumen["recargo"]),
            (f"IGV ({resumen['pct_igv']:.0f}%)", resumen["igv"]),
        ]
    return filas


def _pct_costo(resumen):
    """% de costo sobre el precio neto, o None si no hay precio de venta."""
    if resumen["precio_venta"] > 0 and resumen["base"] > 0:
        return resumen["costo_total"] / resumen["base"] * 100
    return None


def _encabezado(resumen):
    tipo = {"Combo": "Combo", "Modificación de receta": "Modificación de receta"}.get(
        resumen["tipo"], "Receta de venta")
    quien = f"Propuesta de {resumen['autor']}" if resumen["autor"] else "Propuesta"
    return (f"{tipo}: {resumen['nombre'] or '(sin nombre)'}",
            f"{quien} · {resumen['fecha']}")


# ─── PDF ────────────────────────────────────────────────────────────────
def pdf_receta(resumen):
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.figure import Figure

    from tema import ACENTO, GRIS_BORDE, GRIS_FONDO, GRIS_TEXTO, TEXTO_PRINCIPAL

    titulo, subtitulo = _encabezado(resumen)
    lineas = resumen["lineas"]
    total = resumen["costo_total"]
    # Rótulos CORTOS: alineados a la derecha, «P. unit. (S/)» y
    # «Subtotal (S/)» se pisaban en la cabecera. La moneda va arriba.
    cab = ["Código", "Producto", "Unidad", "Cant.", "P. unit.", "Subtotal", "%"]
    filas = []
    for l in lineas:
        sub = l["cantidad"] * l["precio"]
        filas.append([
            str(l["cod"]), str(l["nombre"])[:48], str(l["unidad"]),
            _num(l["cantidad"]), _num(l["precio"]), f"{sub:,.2f}",
            f"{(sub / total * 100) if total > 0 else 0:.1f}",
        ])
    paginas = [filas[i:i + _FILAS_POR_PAGINA]
               for i in range(0, len(filas), _FILAS_POR_PAGINA)] or [[]]

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        for n, trozo in enumerate(paginas, start=1):
            fig = Figure(figsize=(8.27, 11.69))          # A4 en pulgadas
            fig.text(0.07, 0.95, titulo, fontsize=16, weight="bold",
                     color=TEXTO_PRINCIPAL)
            fig.text(0.07, 0.925, subtitulo + " · importes en S/", fontsize=9,
                     color=GRIS_TEXTO)
            alto = 0.022 * (len(trozo) + 1)
            ax = fig.add_axes([0.07, 0.90 - alto, 0.86, alto])
            ax.axis("off")
            if trozo:
                t = ax.table(cellText=trozo, colLabels=cab, loc="upper center",
                             cellLoc="left", colLoc="left",
                             colWidths=[0.10, 0.39, 0.10, 0.09, 0.11, 0.12, 0.09])
                t.auto_set_font_size(False)
                t.set_fontsize(8.5)
                for (r, c), celda in t.get_celld().items():
                    # El margen interno es una FRACCIÓN del ancho: en la
                    # columna Producto el 10 % por defecto dejaba un hueco.
                    celda.PAD = 0.04
                    celda.set_edgecolor(GRIS_BORDE)
                    celda.set_height(1 / (len(trozo) + 1))
                    if c >= 3:
                        celda.get_text().set_horizontalalignment("right")
                    if r == 0:
                        celda.set_facecolor(GRIS_FONDO)
                        celda.get_text().set_weight("bold")
            # El desglose va sólo en la última página, debajo de la tabla.
            if n == len(paginas):
                y = 0.90 - alto - 0.05
                for concepto, valor in _filas_desglose(resumen):
                    fig.text(0.55, y, concepto, fontsize=10, color=TEXTO_PRINCIPAL)
                    fig.text(0.93, y, _soles(valor), fontsize=10, ha="right",
                             color=TEXTO_PRINCIPAL,
                             weight="bold" if concepto == "Costo total" else "normal")
                    y -= 0.022
                pct = _pct_costo(resumen)
                if pct is not None:
                    fig.text(0.55, y - 0.005, f"% de costo sobre neto: {pct:.1f}%",
                             fontsize=10, color=ACENTO, weight="bold")
            fig.text(0.07, 0.03, "Generado desde Reportes › Recetas › Nueva receta. "
                     "Es una PROPUESTA: no modifica la receta del sistema.",
                     fontsize=7.5, color=GRIS_TEXTO)
            if len(paginas) > 1:
                fig.text(0.93, 0.03, f"{n}/{len(paginas)}", fontsize=7.5,
                         ha="right", color=GRIS_TEXTO)
            pdf.savefig(fig)
    return buf.getvalue()


# ─── Excel ──────────────────────────────────────────────────────────────
def excel_receta(resumen):
    import xlsxwriter

    from tema import GRIS_FONDO, GRIS_TEXTO

    titulo, subtitulo = _encabezado(resumen)
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet("Receta")
    f_tit = wb.add_format({"bold": True, "font_size": 14})
    f_sub = wb.add_format({"font_color": GRIS_TEXTO})
    f_cab = wb.add_format({"bold": True, "bg_color": GRIS_FONDO, "bottom": 1})
    f_num = wb.add_format({"num_format": "#,##0.00"})
    # Cantidad y precio unitario con hasta 4 decimales (gramos del sistema).
    f_fino = wb.add_format({"num_format": "#,##0.####"})
    f_pct = wb.add_format({"num_format": "0.0"})
    f_tot = wb.add_format({"bold": True, "num_format": "#,##0.00", "top": 1})
    f_tot_txt = wb.add_format({"bold": True, "top": 1})

    ws.write(0, 0, titulo, f_tit)
    ws.write(1, 0, subtitulo, f_sub)
    cab = ["Código", "Producto", "Unidad", "Cantidad", "Precio unit. (S/)",
           "Subtotal (S/)", "% del total"]
    fila0 = 3
    for c, texto in enumerate(cab):
        ws.write(fila0, c, texto, f_cab)
    total = resumen["costo_total"]
    r = fila0
    for r, l in enumerate(resumen["lineas"], start=fila0 + 1):
        sub = l["cantidad"] * l["precio"]
        ws.write(r, 0, str(l["cod"]))
        ws.write(r, 1, str(l["nombre"]))
        ws.write(r, 2, str(l["unidad"]))
        ws.write_number(r, 3, l["cantidad"], f_fino)
        ws.write_number(r, 4, l["precio"], f_fino)
        # Fórmulas, no valores: si alguien corrige una cantidad en el
        # Excel, el subtotal y el total lo siguen.
        ws.write_formula(r, 5, f"=D{r + 1}*E{r + 1}", f_num, sub)
    ult = r
    fila_tot = ult + 1
    ws.write(fila_tot, 4, "Costo total", f_tot_txt)
    ws.write_formula(fila_tot, 5, f"=SUM(F{fila0 + 2}:F{ult + 1})", f_tot, total)
    for rr in range(fila0 + 1, ult + 1):
        sub = resumen["lineas"][rr - fila0 - 1]
        v = sub["cantidad"] * sub["precio"]
        ws.write_formula(rr, 6, f"=IF($F${fila_tot + 1}>0,F{rr + 1}/$F${fila_tot + 1}*100,0)",
                         f_pct, (v / total * 100) if total > 0 else 0)

    r = fila_tot + 2
    for concepto, valor in _filas_desglose(resumen)[1:]:
        ws.write(r, 4, concepto)
        ws.write_number(r, 5, valor, f_num)
        r += 1
    pct = _pct_costo(resumen)
    if pct is not None:
        ws.write(r, 4, "% de costo sobre neto")
        ws.write_number(r, 5, pct, f_pct)

    ws.set_column(0, 0, 11)
    ws.set_column(1, 1, 42)
    ws.set_column(2, 2, 10)
    ws.set_column(3, 6, 15)
    wb.close()
    return buf.getvalue()


# ─── Correo ─────────────────────────────────────────────────────────────
def cuerpo_correo(resumen):
    titulo, subtitulo = _encabezado(resumen)
    txt = [titulo, subtitulo, "", "Ítems:"]
    lineas = resumen["lineas"]
    for l in lineas[:_MAX_LINEAS_CUERPO]:
        sub = l["cantidad"] * l["precio"]
        txt.append(f"- {l['nombre']} · {_num(l['cantidad'])} {l['unidad']} · {_soles(sub)}")
    if len(lineas) > _MAX_LINEAS_CUERPO:
        txt.append(f"… y {len(lineas) - _MAX_LINEAS_CUERPO} más (ver adjuntos).")
    txt.append("")
    for concepto, valor in _filas_desglose(resumen):
        txt.append(f"{concepto}: {_soles(valor)}")
    pct = _pct_costo(resumen)
    if pct is not None:
        txt.append(f"% de costo sobre neto: {pct:.1f}%")
    txt += ["", "Adjunto el detalle en PDF y en Excel."]
    return "\n".join(txt)


def url_gmail(resumen, correo=None):
    """Enlace a «Redactar» de Gmail con asunto y cuerpo escritos.

    `authuser=<correo>` abre la cuenta de ESE usuario aunque el navegador
    tenga varias sesiones de Google abiertas — sin él, Gmail usa la
    primera, y el correo saldría de otra dirección. Los destinatarios no
    se piden en la app: en Gmail se escriben con su autocompletado."""
    titulo, _ = _encabezado(resumen)
    params = {"view": "cm", "fs": "1", "su": titulo, "body": cuerpo_correo(resumen)}
    if correo:
        params["authuser"] = correo
    return "https://mail.google.com/mail/?" + urlencode(params, quote_via=quote)


# ─── Envío automático con adjuntos (SMTP de Gmail) ──────────────────────
# Pedido 2026-09-23, al ver el primer camino: «debe adjuntarlo
# automáticamente». Abrir el Gmail del usuario NO puede adjuntar, así que
# con los secrets configurados la app manda el correo ella misma, desde la
# cuenta de `GMAIL_REMITENTE` con su contraseña de aplicación. Sale SIEMPRE
# de esa cuenta — quien apretó el botón va en «Responder a» y en el cuerpo.
# Regla #503.
_RE_CORREO = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")
MAX_DESTINATARIOS = 10


def separar_destinatarios(texto):
    """«a@x.com, b@y.pe; c@z.com» → (válidos, inválidos). Acepta coma,
    punto y coma o espacios como separador, y descarta repetidos."""
    partes = [p.strip() for p in re.split(r"[,;\s]+", texto or "") if p.strip()]
    validos, invalidos, vistos = [], [], set()
    for p in partes:
        if not _RE_CORREO.match(p):
            invalidos.append(p)
        elif p.lower() not in vistos:
            vistos.add(p.lower())
            validos.append(p)
    return validos, invalidos


def armar_correo(resumen, remitente, destinatarios, responder_a=None,
                 pdf=None, xlsx=None):
    """El `EmailMessage` listo: texto + el PDF y el Excel adjuntos. Se
    separa de `enviar_correo` para poder probarlo sin red."""
    titulo, _ = _encabezado(resumen)
    msg = EmailMessage()
    msg["Subject"] = titulo
    msg["From"] = remitente
    msg["To"] = ", ".join(destinatarios)
    if responder_a and responder_a.lower() != remitente.lower():
        msg["Reply-To"] = responder_a
    msg.set_content(cuerpo_correo(resumen))
    msg.add_attachment(pdf if pdf is not None else pdf_receta(resumen),
                       maintype="application", subtype="pdf",
                       filename=nombre_archivo(resumen, "pdf"))
    msg.add_attachment(
        xlsx if xlsx is not None else excel_receta(resumen),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=nombre_archivo(resumen, "xlsx"))
    return msg


def enviar_correo(msg, remitente, clave_app):
    """Manda `msg` por el SMTP de Gmail (SSL, puerto 465). `clave_app` es
    la CONTRASEÑA DE APLICACIÓN de 16 letras, no la de la cuenta: Gmail
    rechaza la normal por SMTP. Gmail guarda una copia en «Enviados» de
    esa cuenta. Levanta la excepción de `smtplib` tal cual: el llamador
    decide qué decirle al usuario."""
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(remitente, clave_app.replace(" ", ""))
        smtp.send_message(msg)
