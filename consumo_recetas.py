"""consumo_recetas — cuánto INSUMO DE COMPRA usaron las ventas, bajando por las recetas.

La pregunta (2026-09-28, a pedido): «cuánto de crema de leche usé en una
semana», cuando la crema entra directo en unos platos y ESCONDIDA en recetas
base de otros; o «cuánto pulpo», cuando la receta del plato pide un corte que
sale de un porcionamiento. El SP del POS (`spRep_PaloteoInsumo`) contesta sólo
el PRIMER nivel: lo que nombra la receta de venta del plato.

EL ÁRBOL. Cada venta del primer nivel (`paloteoinsumosnivel1.parquet`, que es
el SP entero con la fecha del pedido y la hora de CADA plato) se abre hasta
llegar a lo que se compra:

    plato ─ receta de venta ─► insumo del nivel 1
      · si es un CORTE que se porciona  → el insumo entero del que sale,
        con el RENDIMIENTO de los porcionamientos reales;
      · si no, si tiene RECETA BASE activa → sus insumos, por lote;
      · si no, es una HOJA: un insumo de compra.
    …y así hasta NIVELES_MAX niveles, sin pasar dos veces por el mismo código.

Lo que decidió el usuario (2026-09-28), y cómo quedó al verificarlo:
  · EL RENDIMIENTO REAL MANDA. Mes a mes: si el producto se porcionó en los
    90 días que terminan el último día del mes, baja por esos porcionamientos
    aunque tenga receta; si no, por su RECETA base activa; y sólo si no tiene
    receta, por los 10 porcionamientos más cercanos (el respaldo). Así lo
    pidió («la receta sólo como respaldo cuando no hay porcionamientos») y así
    se afinó al correrlo sobre los datos: un porcionamiento VIEJO de un
    producto con receta era casi siempre otra cosa — el código viejo del pulpo
    cocido (hoy una receta sobre el corte nuevo), o una crema de yogurt y un
    jus de res «porcionados» desde pan campesino.
  · Un corte que sale de varios insumos pesa lo que aportó cada uno en la
    ventana. El reparto entre los cortes de un mismo porcionamiento es por
    PESO RESULT, que es la regla del propio Almacén (medido: 2.612 de 2.613
    porcionamientos con el mismo costo por kilo; `CANT TOT RESUL` es la suma
    de los pesos en 7.657 de 7.660). A un subproducto (grasa, retazos,
    carcasa) la cocina le anota poco peso y le toca poco insumo: es costeo,
    no física, y está bien que lo sea.
  · HAY PORCIONAMIENTOS AL REVÉS (del corte al insumo: correcciones). Arman
    un círculo; lo que ya no tiene por dónde seguir sin volver sobre sus
    pasos es una hoja. Sin eso, el asado de tira y las conchas se perdían.
  · El DÍA es el de la fecha del pedido (la de la mesa); la HORA, la de cada
    plato (`FECHA ITEM` = `DPEDIDO.fregistro`): un postre llega unos 70 minutos
    después de abierta la mesa.

LAS UNIDADES. El POS y las recetas hablan en unidad de SALIDA (mililitros,
gramos); el kardex y los porcionamientos, en la de ENTRADA (litros, kilos). Se
pasa a la de entrada con el `FACTOR` del maestro (`inventariovalorizado.parquet`)
y todo el árbol viaja en entrada: una receta base rinde UN lote = una unidad de
entrada de su producto (medido: 407 de 426 recetas). El costo es cantidad ×
`PRECIO PROMEDIO` de HOY, y las recetas son las de HOY: editar una receta
cambia el consumo histórico, como en el SP.

LO QUE NO CIERRA, Y ES A PROPÓSITO. El costo del primer nivel (el del SP) y el
de las hojas no coinciden: por las recetas base sí —el Almacén recosta sus
productos con sus insumos, y el cuadre de un documento dio S/ 16,80665 contra
S/ 16,80665—, pero por un porcionamiento el costo de las hojas es el del
rendimiento REAL y el del corte, el que le puso el Almacén. Medido en el mes
del mockup: −5,8 %, y la mitad sale de los tres productos de Venta Interna
(el chorizo y la chistorra de pato). `herramientas/verificar_consumo.py` lo
parte rama por rama.

Puro DuckDB + pandas, sin streamlit —como `definicion_venta.py`—: lo usan
`data.py` (que lee los parquets de R2 y cachea), la vista de Movimientos, la
herramienta de verificación y `test_consumo_recetas.py`. Ver `arquitectura.md`
regla #558.
"""

import datetime as dt

import duckdb

VERSION = 1
"""Va en la clave de la caché de disco (que no caduca): subirla cuando cambie
QUÉ se calcula, no cómo se ve."""

ARCHIVOS = {
    "paloteo": "paloteoinsumosnivel1.parquet",
    "recetabase": "recetabase.parquet",
    "porcionamientos": "porcionamientos.parquet",
    "maestro": "inventariovalorizado.parquet",
}
"""Los cuatro parquets del cálculo. El primero es el que manda el rango."""

GRUPOS_NO_SERVICIO = ("Venta Interna", "Eventos")
"""Los grupos del POS que no son servicio de salón: se venden por tanda (el
chorizo y la chistorra de pato para Mayta, 8 pedidos en 6 días de un mes) y
corren el patrón por día y por hora. Es la lista de
`graficos/ventas_ficha_hora.py::GRUPOS_RAROS`; el test vigila que no se
separen."""

HORA_CENA = 17
"""Desde qué hora un plato es de la cena: a las 17 h la venta cae casi a cero
(S/ 2 por día contra S/ 530 a las 13 h, medido en septiembre de 2026)."""

HORA_MADRUGADA = 6
"""Lo pedido antes de las 6 h es de la cena de la noche anterior."""

VENTANA_DIAS = 90
RESPALDO_N = 10
NIVELES_MAX = 12
RECETA_ACTIVA = "RB.ACTIV"

DIRECTO = "directo en el plato"
"""El camino de lo que la receta de venta nombra y ya es de compra."""

GRANO_DIA_MAX = 62
"""Hasta cuántos días el detalle va día por día; más largo, por semana (con
los meses aparte). Doce meses por día serían 365 columnas y varios MB."""


# ===========================================================================
# LECTURA: los parquets tal como vienen → tablas con nombres propios
# ===========================================================================
# Cada `sql_*` recibe la RELACIÓN de donde leer (`read_parquet('s3://…')` en la
# app, el nombre de un DataFrame registrado en el test) y devuelve la consulta.
# Los nombres de las columnas del Sheet viven sólo acá.

def sql_nivel1(relacion, ini, fin, con_hora_item=True):
    """El primer nivel del rango, agregado por día, hora, plato e insumo.

    `ini`/`fin` son fechas (inclusive) sobre la fecha del PEDIDO. Sin
    `FECHA ITEM` (un parquet anterior al 2026-09-28) la hora es la de la mesa."""
    hora = ('hour(COALESCE("FECHA ITEM", "FECHA PEDIDO"))' if con_hora_item
            else 'hour("FECHA PEDIDO")')
    return f"""
        SELECT CAST("FECHA PEDIDO" AS DATE)            AS fecha,
               {hora}                                  AS hora,
               "PRODUCTO"                              AS plato,
               ANY_VALUE("GRUPO")                      AS grupo,
               "COD INSUMO"                            AS cod,
               SUM("CONSUMO TOTAL")                    AS consumo,
               SUM("COSTO TOTAL")                      AS costo,
               SUM("CANT VENDIDA")                     AS vendido,
               ANY_VALUE("UNIDAD")                     AS unid_salida
        FROM {relacion}
        WHERE CAST("FECHA PEDIDO" AS DATE) BETWEEN DATE '{ini}' AND DATE '{fin}'
        GROUP BY 1, 2, 3, 5"""


def sql_recetas(relacion):
    return f"""
        SELECT "COD PROD RB" AS prod, "COD INS RB" AS ins, "CANT" AS cant,
               "FACTOR INS" AS factor_ins, "UNID" AS unid_ins,
               "RB ACT" = '{RECETA_ACTIVA}' AS activa
        FROM {relacion}
        WHERE "COD INS RB" IS NOT NULL"""


def sql_porcionamientos(relacion):
    return f"""
        SELECT "COD PORC" AS porc, "FEC REGIST" AS fecha,
               "COD PROD INIC" AS cod_e, "COD PROD FINAL" AS cod_x,
               "CANT A PORCIONAR" AS cant_porc, "CANT TOT RESUL" AS cant_tot,
               "CANT RESULT" AS cant_x, "PESO RESULT" AS peso
        FROM {relacion}"""


def sql_maestro(relacion):
    return f"""
        SELECT "CODIGO PRODUCTO" AS cod, "NOMBRE PRODUCTO" AS nombre,
               "UNIDAD KARDEX" AS unid, "FACTOR" AS factor,
               "PRECIO PROMEDIO" AS precio, "NOMBRE FAMILIA" AS familia,
               "NOMBRE SUBFAMILIA" AS subfamilia
        FROM {relacion}"""


# ===========================================================================
# EL CÁLCULO
# ===========================================================================

def grano(ini, fin):
    """'dia' si el rango entra día por día; si no, 'semana'."""
    return "dia" if (fin - ini).days + 1 <= GRANO_DIA_MAX else "semana"


def cubetas(ini, fin, g=None):
    """Las fechas de inicio de cada cubeta fina y de cada mes del rango."""
    g = g or grano(ini, fin)
    if g == "dia":
        finas = [ini + dt.timedelta(days=i) for i in range((fin - ini).days + 1)]
    else:
        lunes = ini - dt.timedelta(days=ini.weekday())
        finas = []
        while lunes <= fin:
            finas.append(lunes)
            lunes += dt.timedelta(days=7)
    meses, m = [], ini.replace(day=1)
    while m <= fin:
        meses.append(m)
        m = (m + dt.timedelta(days=32)).replace(day=1)
    return finas, meses


def dias_por_dia_semana(ini, fin):
    """Cuántos lunes, martes… hay en el rango: el divisor del promedio."""
    n = [0] * 7
    d = ini
    while d <= fin:
        n[d.weekday()] += 1
        d += dt.timedelta(days=1)
    return n


def calcular(nivel1, recetas, porcionamientos, maestro, ini, fin):
    """El consumo de insumos de compra del rango.

    Recibe lo que devuelven las `sql_*` (DataFrames) y el rango (fechas,
    inclusive). Devuelve un dict chico, listo para cachear:

      filas     una por (insumo, preparación, plato, lo que nombra la receta,
                camino, última arista), con la cantidad por cubeta fina
                (`fino`, disperso), por mes (`mes`, disperso), por día de la
                semana (`dsem`, lun..dom) y por turno (`turno`, almuerzo y
                cena), en unidad de ENTRADA del insumo.
      horas     por (insumo, venta interna, día de la semana, hora).
      rend      los rendimientos de los meses del rango.
      porcionado  lo porcionado de verdad en el rango, por insumo de origen.
      maestro   nombre, unidad, factor, precio y familia de los códigos usados.
      platos    las unidades vendidas y si es venta interna.
      cuadre    cada insumo del primer nivel: su costo ahí contra el de sus
                hojas, y si bajó por algún porcionamiento.
      resumen   totales y avisos (costo del primer nivel, filas sin maestro…).
    """
    g = grano(ini, fin)
    finas, meses = cubetas(ini, fin, g)
    con = duckdb.connect()
    try:
        con.register("n1_in", nivel1)
        con.register("rb_in", recetas)
        con.register("porc_in", porcionamientos)
        con.register("maestro_in", maestro)
        lista_ns = ", ".join("'" + x.replace("'", "''") + "'" for x in GRUPOS_NO_SERVICIO)
        lunes0 = finas[0] if g == "semana" else ini - dt.timedelta(days=ini.weekday())
        con.execute(f"""
        CREATE TABLE maestro AS
        SELECT cod, ANY_VALUE(nombre) nombre, ANY_VALUE(unid) unid, ANY_VALUE(factor) factor,
               ANY_VALUE(precio) precio, ANY_VALUE(familia) familia, ANY_VALUE(subfamilia) subfamilia
        FROM maestro_in WHERE cod IS NOT NULL GROUP BY cod;

        CREATE TABLE n1_todo AS
        SELECT CAST(n.fecha AS DATE) fecha, date_trunc('month', CAST(n.fecha AS DATE))::DATE mes,
               CAST(n.hora AS INTEGER) hora, n.plato,
               COALESCE(n.grupo IN ({lista_ns}), false) interna, n.cod,
               n.consumo, n.costo, n.vendido, n.unid_salida,
               n.consumo / NULLIF(m.factor, 0) q, m.cod IS NOT NULL en_maestro
        FROM n1_in n LEFT JOIN maestro m USING (cod)
        WHERE CAST(n.fecha AS DATE) BETWEEN DATE '{ini}' AND DATE '{fin}';

        CREATE TABLE n1 AS SELECT * FROM n1_todo WHERE q IS NOT NULL;

        -- LOS PORCIONAMIENTOS: una fila por corte; lo que entró del insumo de
        -- origen se reparte entre los cortes por su PESO. Fuera los que no
        -- pesan (11 de 12.331): no se pueden repartir.
        CREATE TABLE cortes AS
        SELECT porc, CAST(fecha AS DATE) fecha, cod_e, cod_x, cant_x sale_x,
               cant_porc * peso / cant_tot entra_e
        FROM porc_in
        WHERE cant_x > 0 AND cant_tot > 0 AND peso > 0 AND cod_e IS NOT NULL AND cod_x IS NOT NULL;

        CREATE TABLE meses AS SELECT DISTINCT mes, last_day(mes) fin FROM n1;

        CREATE TABLE grilla AS
        SELECT x.cod_x, m.mes, m.fin FROM (SELECT DISTINCT cod_x FROM cortes) x CROSS JOIN meses m;

        CREATE TABLE ventana AS
        SELECT g.cod_x, g.mes, c.cod_e, c.entra_e, c.sale_x, c.fecha
        FROM grilla g JOIN cortes c
          ON c.cod_x = g.cod_x AND c.fecha > g.fin - {VENTANA_DIAS} AND c.fecha <= g.fin;

        CREATE TABLE respaldo AS
        SELECT * EXCLUDE (rn) FROM (
          SELECT g.cod_x, g.mes, c.cod_e, c.entra_e, c.sale_x, c.fecha,
                 ROW_NUMBER() OVER (PARTITION BY g.cod_x, g.mes
                                    ORDER BY abs(date_diff('day', c.fecha, g.fin)), c.fecha DESC, c.porc) rn
          FROM grilla g JOIN cortes c ON c.cod_x = g.cod_x
          WHERE NOT EXISTS (SELECT 1 FROM ventana v WHERE v.cod_x = g.cod_x AND v.mes = g.mes)
        ) WHERE rn <= {RESPALDO_N};

        CREATE TABLE rend AS
        WITH base AS (
          SELECT *, 'ventana' fuente FROM ventana
          UNION ALL
          SELECT *, 'respaldo' FROM respaldo
        )
        SELECT cod_x, mes, cod_e, ANY_VALUE(fuente) fuente,
               SUM(entra_e) / ANY_VALUE(tot_x) rend,
               ANY_VALUE(n_x) n_porc, ANY_VALUE(desde) desde, ANY_VALUE(hasta) hasta
        FROM (SELECT *, SUM(sale_x) OVER (PARTITION BY cod_x, mes) tot_x,
                        COUNT(*) OVER (PARTITION BY cod_x, mes) n_x,
                        MIN(fecha) OVER (PARTITION BY cod_x, mes) desde,
                        MAX(fecha) OVER (PARTITION BY cod_x, mes) hasta
              FROM base)
        GROUP BY cod_x, mes, cod_e;

        -- EL ÁRBOL, MES A MES: (1) si el producto se porcionó en la ventana
        -- de 90 días, baja por esos porcionamientos (el real manda); (2) si
        -- no, por su receta base activa, un lote por unidad de entrada;
        -- (3) sólo sin receta, por los porcionamientos más cercanos. Un
        -- porcionamiento VIEJO no es «el real»: verificado sobre los datos
        -- (2026-09-28), el respaldo de un producto con receta era casi
        -- siempre otra cosa — el código viejo del pulpo cocido, que hoy es
        -- una receta sobre el corte nuevo; una crema de yogurt o un jus de
        -- res «porcionados» desde pan campesino.
        CREATE TABLE rb_aristas AS
        SELECT r.prod, r.ins, SUM(r.cant) / NULLIF(ANY_VALUE(COALESCE(r.factor_ins, m.factor)), 0) coef
        FROM rb_in r LEFT JOIN maestro m ON m.cod = r.ins
        WHERE r.activa
        GROUP BY r.prod, r.ins;

        CREATE TABLE aristas AS
        SELECT cod_x padre, cod_e hijo, mes, rend coef, 'porcionamiento' via
        FROM rend WHERE fuente = 'ventana'
        UNION ALL
        SELECT e.prod, e.ins, m.mes, e.coef, 'receta base'
        FROM rb_aristas e CROSS JOIN meses m
        WHERE NOT EXISTS (SELECT 1 FROM rend v
                          WHERE v.cod_x = e.prod AND v.mes = m.mes AND v.fuente = 'ventana')
        UNION ALL
        SELECT cod_x, cod_e, mes, rend, 'porcionamiento'
        FROM rend WHERE fuente = 'respaldo' AND cod_x NOT IN (SELECT prod FROM rb_aristas);

        CREATE TABLE hojas AS
        WITH RECURSIVE e AS (
          SELECT fecha, mes, hora, plato, interna, cod, q, 0 nivel, '' via,
                 NULL::VARCHAR padre, NULL::VARCHAR ultima, cod n1, '/' || cod || '/' ruta
          FROM n1
          UNION ALL
          SELECT e.fecha, e.mes, e.hora, e.plato, e.interna, a.hijo, e.q * a.coef, e.nivel + 1,
                 CASE WHEN e.via = '' THEN a.via
                      WHEN position(a.via IN e.via) > 0 THEN e.via
                      ELSE e.via || ' + ' || a.via END,
                 e.cod, a.via, e.n1, e.ruta || a.hijo || '/'
          FROM e JOIN aristas a ON a.padre = e.cod AND a.mes = e.mes
          WHERE e.nivel < {NIVELES_MAX} AND position('/' || a.hijo || '/' IN e.ruta) = 0
            AND a.coef IS NOT NULL
        )
        SELECT fecha, hora, plato, interna, cod, nivel, n1 raiz,
               COALESCE(padre, '') padre,
               CASE WHEN nivel >= 2 AND n1 <> padre THEN n1 ELSE '' END n1,
               CASE WHEN via = '' THEN '{DIRECTO}' ELSE via END camino,
               COALESCE(ultima, 'directo') ultima, q
        FROM e
        -- Una HOJA es lo que ya no tiene por dónde seguir. Una arista que
        -- vuelve a un código del camino no cuenta: hay porcionamientos AL
        -- REVÉS (del corte al insumo, correcciones), y sin esto el asado de
        -- tira y las conchas se perdían enteros en el círculo.
        WHERE NOT EXISTS (SELECT 1 FROM aristas a
                          WHERE a.padre = e.cod AND a.mes = e.mes AND a.coef IS NOT NULL
                            AND position('/' || a.hijo || '/' IN e.ruta) = 0);
        """)

        # ── Las filas de la tabla: una por insumo × preparación × plato ────
        if g == "dia":
            idx_fino = f"date_diff('day', DATE '{ini}', fecha)"
        else:
            idx_fino = f"date_diff('day', DATE '{lunes0}', date_trunc('week', fecha)::DATE) // 7"
        idx_mes = (f"(year(fecha) * 12 + month(fecha)) - ({ini.year * 12 + ini.month})")
        turno = f"CASE WHEN hora >= {HORA_MADRUGADA} AND hora < {HORA_CENA} THEN 0 ELSE 1 END"
        filas = con.execute(f"""
        WITH h AS (
          SELECT cod, padre, plato, interna, n1, camino, ultima, q,
                 {idx_fino} i_fino, {idx_mes} i_mes, isodow(fecha) - 1 i_dsem, {turno} i_turno
          FROM hojas
        ),
        clave AS (
          SELECT cod, padre, plato, n1, camino, ultima, ANY_VALUE(interna) interna, SUM(q) q,
                 {", ".join(f"SUM(q) FILTER (WHERE i_dsem = {i}) d{i}" for i in range(7))},
                 SUM(q) FILTER (WHERE i_turno = 0) t0, SUM(q) FILTER (WHERE i_turno = 1) t1
          FROM h GROUP BY cod, padre, plato, n1, camino, ultima
        ),
        fino AS (
          SELECT cod, padre, plato, n1, camino, ultima, list([i_fino::DOUBLE, q] ORDER BY i_fino) fino
          FROM (SELECT cod, padre, plato, n1, camino, ultima, i_fino, SUM(q) q FROM h GROUP BY ALL)
          GROUP BY ALL
        ),
        mes AS (
          SELECT cod, padre, plato, n1, camino, ultima, list([i_mes::DOUBLE, q] ORDER BY i_mes) mes
          FROM (SELECT cod, padre, plato, n1, camino, ultima, i_mes, SUM(q) q FROM h GROUP BY ALL)
          GROUP BY ALL
        )
        SELECT c.*, f.fino, m.mes
        FROM clave c
        JOIN fino f USING (cod, padre, plato, n1, camino, ultima)
        JOIN mes m USING (cod, padre, plato, n1, camino, ultima)
        ORDER BY cod, padre, plato, n1, camino, ultima
        """).df()
        for i in range(7):
            filas[f"d{i}"] = filas[f"d{i}"].fillna(0.0)
        filas["t0"] = filas["t0"].fillna(0.0)
        filas["t1"] = filas["t1"].fillna(0.0)

        horas = con.execute("""
            SELECT cod, interna, isodow(fecha) - 1 dsem, hora, SUM(q) q
            FROM hojas GROUP BY ALL ORDER BY ALL""").df()

        con.execute("""
            CREATE TABLE usados AS
            SELECT DISTINCT cod FROM (
              SELECT cod FROM hojas UNION SELECT padre FROM hojas WHERE padre <> ''
              UNION SELECT n1 FROM hojas WHERE n1 <> '' UNION SELECT cod_x FROM rend)""")
        mae = con.execute("""
            SELECT m.*, s.unid_salida
            FROM maestro m
            LEFT JOIN (SELECT cod, ANY_VALUE(unid_salida) unid_salida FROM (
                         SELECT cod, unid_salida FROM n1_todo WHERE unid_salida IS NOT NULL
                         UNION ALL
                         SELECT ins, unid_ins FROM rb_in WHERE unid_ins IS NOT NULL)
                       GROUP BY cod) s USING (cod)
            WHERE m.cod IN (SELECT cod FROM usados)""").df()

        # `usado`: si el árbol baja por esa fila (la ventana siempre; el
        # respaldo, sólo si el producto no tiene receta).
        rend = con.execute("""
            SELECT r.*, (r.fuente = 'ventana' OR r.cod_x NOT IN (SELECT prod FROM rb_aristas)) usado
            FROM rend r ORDER BY cod_x, mes, cod_e""").df()
        porcionado = con.execute(f"""
            SELECT cod_e cod, SUM(cant_porc) cant
            FROM (SELECT DISTINCT porc, cod_e, cant_porc FROM porc_in
                  WHERE CAST(fecha AS DATE) BETWEEN DATE '{ini}' AND DATE '{fin}' AND cod_e IS NOT NULL)
            GROUP BY 1""").df()
        platos = con.execute("""
            SELECT plato, ANY_VALUE(interna) interna, MAX(u) vendidos
            FROM (SELECT plato, cod, ANY_VALUE(interna) interna, SUM(vendido) u FROM n1_todo GROUP BY plato, cod)
            GROUP BY plato""").df()

        # EL CUADRE: cada insumo del primer nivel contra lo que cuestan sus
        # hojas. Por las recetas base tiene que dar lo mismo (el Almacén
        # recuesta sus productos con sus insumos); por un porcionamiento, no
        # (el rendimiento es el real). Lo lee `herramientas/verificar_consumo.py`.
        cuadre = con.execute("""
            SELECT r.cod, r.interna, r.costo_n1,
                   COALESCE(h.costo_hojas, 0) costo_hojas,
                   COALESCE(h.porc, false) con_porcionamiento
            FROM (SELECT cod, interna, SUM(costo) costo_n1 FROM n1 GROUP BY cod, interna) r
            LEFT JOIN (SELECT hh.raiz, hh.interna, SUM(hh.q * m.precio) costo_hojas,
                              bool_or(position('porcionamiento' IN hh.camino) > 0) porc
                       FROM hojas hh JOIN maestro m ON m.cod = hh.cod
                       GROUP BY hh.raiz, hh.interna) h
              ON h.raiz = r.cod AND h.interna = r.interna
            ORDER BY r.costo_n1 DESC""").df()

        costo_hojas = con.execute("""
            SELECT COALESCE(SUM(h.q * m.precio), 0), COALESCE(SUM(h.q * m.precio) FILTER (WHERE h.interna), 0),
                   COUNT(DISTINCT h.cod), COALESCE(MAX(h.nivel), 0)
            FROM hojas h JOIN maestro m USING (cod)""").fetchone()
        costo_n1 = con.execute("""
            SELECT COALESCE(SUM(costo), 0), COALESCE(SUM(costo) FILTER (WHERE interna), 0)
            FROM n1_todo""").fetchone()
        sin = con.execute("""
            SELECT COUNT(*) FILTER (WHERE NOT en_maestro), COUNT(*) FILTER (WHERE en_maestro AND q IS NULL),
                   COALESCE(SUM(costo) FILTER (WHERE q IS NULL), 0)
            FROM n1_todo""").fetchone()
        resumen = dict(
            ini=ini, fin=fin, grano=g, finas=finas, meses=meses,
            n_dia=dias_por_dia_semana(ini, fin),
            costo=float(costo_hojas[0]), costo_interna=float(costo_hojas[1]),
            insumos=int(costo_hojas[2]), niveles=int(costo_hojas[3]),
            costo_nivel1=float(costo_n1[0]), costo_nivel1_interna=float(costo_n1[1]),
            sin_maestro=int(sin[0]), sin_factor=int(sin[1]), costo_sin_convertir=float(sin[2]),
        )
        return dict(filas=filas, horas=horas, rend=rend, porcionado=porcionado,
                    maestro=mae, platos=platos, cuadre=cuadre, resumen=resumen)
    finally:
        con.close()
