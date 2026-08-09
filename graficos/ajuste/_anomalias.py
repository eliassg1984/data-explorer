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

4. **MAD = 0 se trata aparte.** Un producto que SIEMPRE ajusta
   exactamente igual (tipico: siempre 0) tiene dispersion nula, y ahi
   cualquier desvio daria z infinito. Si el valor actual coincide con su
   mediana es `normal`; si no, es `nuevo_patron` — informativo, pero no
   un z que no significa nada.
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
                        col_stock, min_cortes=_MIN_CORTES,
                        z_anomalo=_Z_ANOMALO, z_vigilar=_Z_VIGILAR):
    """Un registro por producto, comparando su ULTIMO corte con su historia.

    Devuelve un DataFrame con una fila por producto y las columnas:

        producto        nombre del producto
        n_cortes        cuantos cortes tiene en el df
        pct_actual      ajuste del ultimo corte, en % de su stock
        pct_mediana     mediana historica de ese % (sin el corte actual)
        dispersion      MAD del historico, en puntos porcentuales
        z               z robusto del corte actual (NaN si no aplica)
        veredicto       anomalo | vigilar | normal | nuevo_patron |
                        sin_historico

    El df de entrada NO se modifica. Las filas sin fecha, sin producto o
    con stock nulo/cero se descartan: sin stock no hay porcentaje que
    calcular, y meterlas como 0 inventaria normalidad.
    """
    faltan = [c for c in (col_producto, col_fecha, col_ajuste, col_stock)
              if not c or c not in df.columns]
    if faltan:
        return pd.DataFrame(columns=["producto", "n_cortes", "pct_actual",
                                     "pct_mediana", "dispersion", "z",
                                     "veredicto"])

    d = df[[col_producto, col_fecha, col_ajuste, col_stock]].copy()
    d.columns = ["producto", "fecha", "ajuste", "stock"]
    d["fecha"] = pd.to_datetime(d["fecha"], errors="coerce")
    d["ajuste"] = pd.to_numeric(d["ajuste"], errors="coerce")
    d["stock"] = pd.to_numeric(d["stock"], errors="coerce")
    d = d.dropna(subset=["producto", "fecha", "ajuste", "stock"])
    d = d[d["stock"] != 0]
    if d.empty:
        return pd.DataFrame(columns=["producto", "n_cortes", "pct_actual",
                                     "pct_mediana", "dispersion", "z",
                                     "veredicto"])

    # Ajuste relativo al stock, en %. abs() NO: el signo distingue faltante
    # de sobrante, y un producto que siempre falta y de pronto sobra es
    # justo el caso interesante.
    d["pct"] = d["ajuste"] / d["stock"] * 100

    # Varias filas del mismo producto en el mismo corte (varias areas):
    # se agregan sumando ajuste y stock ANTES de sacar el %, que no es lo
    # mismo que promediar porcentajes.
    g = (d.groupby(["producto", "fecha"], as_index=False)
           .agg(ajuste=("ajuste", "sum"), stock=("stock", "sum")))
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

        if n < min_cortes:
            filas.append((producto, n, actual, np.nan, np.nan, np.nan,
                          "sin_historico"))
            continue

        mediana = float(np.median(historia))
        mad = float(np.median(np.abs(historia - mediana)))

        if mad == 0:
            veredicto = "normal" if np.isclose(actual, mediana) else "nuevo_patron"
            filas.append((producto, n, actual, mediana, 0.0, np.nan, veredicto))
            continue

        z = _ESCALA_MAD * (actual - mediana) / mad
        az = abs(z)
        if az >= z_anomalo:
            veredicto = "anomalo"
        elif az >= z_vigilar:
            veredicto = "vigilar"
        else:
            veredicto = "normal"
        filas.append((producto, n, actual, mediana, mad, z, veredicto))

    out = pd.DataFrame(filas, columns=["producto", "n_cortes", "pct_actual",
                                       "pct_mediana", "dispersion", "z",
                                       "veredicto"])
    # Primero lo mas raro; dentro de cada grupo, el desvio mayor.
    orden = {"anomalo": 0, "nuevo_patron": 1, "vigilar": 2,
             "normal": 3, "sin_historico": 4}
    out["_o"] = out["veredicto"].map(orden)
    out = (out.sort_values(["_o", "z"], key=lambda s: s.abs() if s.name == "z" else s,
                           ascending=[True, False])
              .drop(columns="_o")
              .reset_index(drop=True))
    return out
