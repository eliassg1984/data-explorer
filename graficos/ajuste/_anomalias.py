"""graficos.ajuste._anomalias - que ajuste es RARO para SU producto.

Los chips actuales de Ajuste (Faltantes, Sobrantes, Criticos >=40%,
Top N) son umbrales ABSOLUTOS: siempre senalan a los mismos productos
caros o de mucho volumen. Eso no es un hallazgo, es una ordenacion.

Aca la pregunta es otra: **para ESTE producto, comparado consigo mismo,
lo de este corte es normal?** Un producto que siempre ajusta ±2% y hoy
ajusta 18% es una senal, aunque en soles sea calderilla. Uno que ajusta
±30% todos los meses no lo es, aunque sea el que mas plata mueve.

DECISIONES QUE IMPORTAN (y por que)
-----------------------------------
1. **Mediana y MAD, no media y desviacion tipica.** Con pocos cortes por
   producto, UN corte malo se mete en la media y en la desviacion, y el
   propio outlier sube el listron hasta declararse normal. La mediana y
   la MAD (desviacion absoluta mediana) no se mueven por un valor
   extremo, que es justo lo que buscamos.

2. **Se mide el ajuste como % del stock**, no en unidades ni en soles.
   Si no, la escala del producto domina: 10 unidades sobre un stock de
   20 es gravisimo y sobre 100.000 es ruido.

3. **Sin histórico suficiente NO se inventa un score.** Con 2 o 3 cortes
   cualquier numero es una casualidad con decimales. Esos productos
   salen marcados `sin_historico` y el llamador decide si los muestra.
   Es la diferencia entre "no lo se" y "es normal", que no son lo mismo.

4. **MAD ~ 0 se trata aparte.** Un producto que SIEMPRE ajusta
   exactamente igual (tipico: siempre 0) tiene dispersion nula, y ahi
   cualquier desvio daria z infinito. Si el valor actual coincide con su
   mediana es `normal`; si no, es `nuevo_patron` — informativo, pero no
   un z que no significa nada. La comparacion es con TOLERANCIA, no con
   `== 0`: contra datos reales aparecieron MAD del orden de 1e-16 que
   pasaban el `== 0` y daban z de 3e16.

5. **Agotarse (`STOCK DECLARADO = 0`) es un ATRIBUTO, no un veredicto.**
   `DECLARADO = 0` significa que el producto se quedo sin stock — el
   conteo no encontro nada. Pasa mucho: el 24,6% de las filas del
   parquet real tiene un ajuste de exactamente -100% del stock.

   La tentacion es sacarlo como categoria propia. Se probo y era PEOR:
   un veredicto `conteo_cero` no distingue los dos casos opuestos que
   importan —

     · el producto que se agota en CADA corte: su historia esta llena de
       -100%, asi que un -100% nuevo es normal PARA EL. No es noticia.
     · el producto que NUNCA se habia agotado y hoy si: eso es
       exactamente lo que se busca.

   El z robusto ya los separa solo (en el primero la mediana ronda -100
   y la MAD es chica; en el segundo el salto es enorme). Sacar esos
   productos del calculo tiraba justo la señal. Asi que `agotado` va
   como columna booleana y el veredicto lo sigue decidiendo la historia.
"""

import numpy as np
import pandas as pd

# Escala que hace comparable la MAD con una desviacion tipica cuando los
# datos son normales (constante estandar del z robusto).
_ESCALA_MAD = 0.6745

# Umbrales del veredicto, sobre el z robusto. 3.5 es el valor que usa la
# literatura de Iglewicz-Hoaglin para "outlier" con z robusto; 2.5 se
# reserva para "vigilar". No son sagrados: se exponen como parametros.
_Z_ANOMALO = 3.5
_Z_VIGILAR = 2.5

# Minimo de cortes para que la historia signifique algo. Con 4 ya hay una
# mediana y una dispersion con algun sentido; por debajo, no.
_MIN_CORTES = 4


def perfil_por_producto(df, col_producto, col_fecha, col_ajuste,
                        col_stock, col_declarado=None,
                        min_cortes=_MIN_CORTES,
                        z_anomalo=_Z_ANOMALO, z_vigilar=_Z_VIGILAR):
    """Un registro por producto, comparando su ULTIMO corte con su historia.

    Devuelve un DataFrame con una fila por producto y las columnas:

        producto        nombre del producto
        n_cortes        cuantos cortes tiene en el df
        pct_actual      ajuste del ultimo corte, en % de su stock
        pct_mediana     mediana historica de ese % (sin el corte actual)
        dispersion      MAD del historico, en puntos porcentuales
        z               z robusto del corte actual (NaN si no aplica)
        veredicto       anomalo | nuevo_patron | vigilar | normal |
                        sin_historico
        agotado         True si el ultimo corte del producto se conto en
                        cero (se quedo sin stock). Es un ATRIBUTO, no un
                        veredicto: ver el punto 5 del docstring del
                        modulo. Sin `col_declarado` sale siempre False.

    El df de entrada NO se modifica. Las filas sin fecha, sin producto o
    con stock nulo/cero se descartan: sin stock no hay porcentaje que
    calcular, y meterlas como 0 inventaria normalidad.
    """
    faltan = [c for c in (col_producto, col_fecha, col_ajuste, col_stock)
              if not c or c not in df.columns]
    if faltan:
        return pd.DataFrame(columns=["producto", "n_cortes", "pct_actual",
                                     "pct_mediana", "dispersion", "z",
                                     "veredicto", "agotado"])

    usa_decl = bool(col_declarado) and col_declarado in df.columns
    cols = [col_producto, col_fecha, col_ajuste, col_stock]
    nombres = ["producto", "fecha", "ajuste", "stock"]
    if usa_decl:
        cols.append(col_declarado)
        nombres.append("declarado")

    d = df[cols].copy()
    d.columns = nombres
    d["fecha"] = pd.to_datetime(d["fecha"], errors="coerce")
    for c in nombres[2:]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["producto", "fecha", "ajuste", "stock"])
    d = d[d["stock"] != 0]
    if d.empty:
        return pd.DataFrame(columns=["producto", "n_cortes", "pct_actual",
                                     "pct_mediana", "dispersion", "z",
                                     "veredicto", "agotado"])

    # Ajuste relativo al stock, en %. abs() NO: el signo distingue faltante
    # de sobrante, y un producto que siempre falta y de pronto sobra es
    # justo el caso interesante.
    d["pct"] = d["ajuste"] / d["stock"] * 100

    # Varias filas del mismo producto en el mismo corte (varias areas):
    # se agregan sumando ajuste y stock ANTES de sacar el %, que no es lo
    # mismo que promediar porcentajes.
    agg = {"ajuste": ("ajuste", "sum"), "stock": ("stock", "sum")}
    if usa_decl:
        agg["declarado"] = ("declarado", "sum")
    g = d.groupby(["producto", "fecha"], as_index=False).agg(**agg)
    g = g[g["stock"] != 0]
    g["pct"] = g["ajuste"] / g["stock"] * 100
    g = g.sort_values(["producto", "fecha"])

    filas = []
    for producto, sub in g.groupby("producto", sort=False):
        pcts = sub["pct"].to_numpy()
        n = len(pcts)
        actual = float(pcts[-1])
        # La historia EXCLUYE el corte actual: si no, el propio valor que
        # se juzga entra en la mediana y se auto-normaliza.
        historia = pcts[:-1]

        # Agotado: se anota y se sigue. NO corta el analisis — que un
        # producto se quede sin stock solo es noticia si para EL es raro,
        # y eso lo decide su historia (punto 5 del docstring del modulo).
        agotado = bool(usa_decl and float(sub["declarado"].to_numpy()[-1]) == 0)

        if n < min_cortes:
            filas.append((producto, n, actual, np.nan, np.nan, np.nan,
                          "sin_historico", agotado))
            continue

        mediana = float(np.median(historia))
        mad = float(np.median(np.abs(historia - mediana)))

        # Tolerancia, NO `== 0`: con datos reales aparecen MAD de ~1e-16
        # que pasan el `== 0` y producen z del orden de 1e16. La escala la
        # marca la propia mediana (un producto que se mueve en cientos
        # tiene otro "practicamente cero" que uno que se mueve en unidades).
        if mad <= max(1e-9, abs(mediana) * 1e-9):
            veredicto = "normal" if np.isclose(actual, mediana) else "nuevo_patron"
            filas.append((producto, n, actual, mediana, 0.0, np.nan,
                          veredicto, agotado))
            continue

        z = _ESCALA_MAD * (actual - mediana) / mad
        az = abs(z)
        if az >= z_anomalo:
            veredicto = "anomalo"
        elif az >= z_vigilar:
            veredicto = "vigilar"
        else:
            veredicto = "normal"
        filas.append((producto, n, actual, mediana, mad, z, veredicto,
                      agotado))

    out = pd.DataFrame(filas, columns=["producto", "n_cortes", "pct_actual",
                                       "pct_mediana", "dispersion", "z",
                                       "veredicto", "agotado"])
    # Primero lo mas raro; dentro de cada grupo, el desvio mayor.
    orden = {"anomalo": 0, "nuevo_patron": 1, "vigilar": 2,
             "normal": 3, "sin_historico": 4}
    out["_o"] = out["veredicto"].map(orden)
    out = (out.sort_values(["_o", "z"], key=lambda s: s.abs() if s.name == "z" else s,
                           ascending=[True, False])
              .drop(columns="_o")
              .reset_index(drop=True))
    return out
