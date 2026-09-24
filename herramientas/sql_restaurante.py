"""
herramientas/sql_restaurante.py — consultas directas al SQL Server del
restaurante (SRCA65DADDFC = 26.94.118.165), sin que nadie escriba la clave.

QUÉ HACE Y POR QUÉ EXISTE
--------------------------
Hasta el 2026-09-24, ver en producción algo que todavía no estaba en un
parquet exigía sumar una fila al Sheet y pedir el refresco por R2: minutos
por pregunta, y una consulta de más en el extractor. Esto responde en
segundos y no deja nada detrás.

EL LOGIN SÓLO PUEDE LEER
------------------------
Es `lectura`, no `sa`: db_datareader + VIEW DEFINITION en ALMACEN,
INFOREST y ALMACENPRUEBA1, nada más. Lo crea el usuario en SSMS, conectado
como sa (`sp_addrolemember` y no `ALTER ROLE … ADD MEMBER`: las bases están
en compatibilidad 100):

    CREATE LOGIN lectura WITH PASSWORD = N'…', DEFAULT_DATABASE = ALMACEN;
    -- y en cada base:
    CREATE USER lectura FOR LOGIN lectura;
    EXEC sp_addrolemember 'db_datareader', 'lectura';
    GRANT VIEW DEFINITION TO lectura;

`--probar` dice con qué login entró y, base por base, si puede escribir.

LA CLAVE NO PASA POR ACÁ
------------------------
El login y su clave viven en el Administrador de credenciales de Windows de
la laptop, como credencial genérica «sql-restaurante». Los carga el usuario:

    cmdkey /generic:sql-restaurante /user:lectura /pass

— sin valor después de /pass, cmdkey la pide sin mostrarla. El script la lee
de ahí al conectar: no está en el repo, ni en un archivo, ni en la línea de
comandos, y nunca se imprime. Claude no escribe contraseñas.

Por qué no autenticación de Windows: el servidor ve a esta laptop como
`SRCA65DADDFC\\Invitado` (el usuario `pc` no existe allá). Arreglarlo pedía
una cuenta de Windows espejo en el servidor, con la misma clave que la de la
laptop y sincronizada para siempre.

Y ADEMÁS, TODO SE DESHACE
-------------------------
El script no sabe qué login hay en la credencial, así que no confía sólo en
los permisos: cada corrida va dentro de una transacción que se revierte al
terminar. Un SELECT devuelve lo mismo; un INSERT, UPDATE, DELETE o CREATE que
se colara se deshace solo, y lo que no admite transacción (CREATE/ALTER
DATABASE, BACKUP) directamente falla. Para que un cambio QUEDE hacen falta
`--escribir` y un login que pueda escribir, y sólo cuando el usuario pidió
ESE cambio.

NO TRABA LA CAJA
----------------
Es la base del POS en pleno servicio. La sesión arranca en READ UNCOMMITTED:
el SELECT no toma bloqueos compartidos, así que no deja esperando a nadie que
esté grabando un pedido. El precio es poder leer una fila a medio grabar —
para explorar da igual; la cifra que tiene que cerrar sale del parquet de la
madrugada. Cada consulta se corta a los `--timeout` segundos, y la sesión
figura como `claude` en el Monitor de actividad de SSMS.

Las bases están en nivel de compatibilidad 100 (SQL Server 2008): no hay
STRING_AGG, IIF, CONCAT, TRY_CAST, LAG/LEAD ni OFFSET/FETCH.

USO
---
    python herramientas/sql_restaurante.py --probar
    python herramientas/sql_restaurante.py -q "SELECT TOP 5 * FROM dbo.vProducto"
    python herramientas/sql_restaurante.py -f consulta.sql --base INFOREST
    python herramientas/sql_restaurante.py -f consulta.sql --csv salida.csv

Para SQL de más de una línea, `-f` con un archivo: las comillas de la consola
rompen el SQL. El archivo puede traer lotes separados por `GO`, como en SSMS.
"""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import pathlib
import re
import sys
from ctypes import wintypes

import pyodbc

if hasattr(sys.stdout, "reconfigure"):      # consola cp1252 de Windows
    sys.stdout.reconfigure(encoding="utf-8")

SERVIDOR = "26.94.118.165"
CREDENCIAL = "sql-restaurante"
_DRIVERS = ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server")


class _CREDENTIAL(ctypes.Structure):
    # CREDENTIALW de wincred.h, campo por campo: el relleno lo pone ctypes.
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.c_void_p),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def _leer_credencial(destino: str) -> tuple[str, str] | None:
    """(usuario, clave) de una credencial genérica de Windows; None si no está.

    Con ctypes y no con `keyring`: es una llamada a la API y no suma una
    dependencia. cmdkey y el panel de control guardan la clave en UTF-16."""
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                 ctypes.POINTER(ctypes.POINTER(_CREDENTIAL))]
    advapi.CredReadW.restype = wintypes.BOOL
    advapi.CredFree.argtypes = [ctypes.c_void_p]
    advapi.CredFree.restype = None

    p = ctypes.POINTER(_CREDENTIAL)()
    if not advapi.CredReadW(destino, 1, 0, ctypes.byref(p)):    # 1 = CRED_TYPE_GENERIC
        err = ctypes.get_last_error()
        if err == 1168:                                         # ERROR_NOT_FOUND
            return None
        raise ctypes.WinError(err)
    try:
        c = p.contents
        n = c.CredentialBlobSize
        clave = ctypes.string_at(c.CredentialBlob, n).decode("utf-16-le") if n else ""
        return c.UserName or "", clave
    finally:
        advapi.CredFree(p)


def _abrir(cadena: str, timeout: int, escribir: bool) -> pyodbc.Connection:
    """Conexión en READ UNCOMMITTED y, salvo `escribir`, con la transacción
    que main() revierte al final YA abierta."""
    # autocommit apagado = el driver pone IMPLICIT_TRANSACTIONS ON. Pero un SET
    # no abre la transacción: la abre la primera sentencia que lee una tabla.
    # Se la fuerza acá porque, sin transacción abierta, un ALTER DATABASE o un
    # BACKUP que llegaran PRIMEROS correrían y quedarían grabados.
    cn = pyodbc.connect(cadena, timeout=10, autocommit=escribir)
    cn.timeout = timeout
    cn.execute("SET NOCOUNT ON; SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
    if not escribir:
        cn.execute("SELECT TOP (0) 1 FROM sys.objects;")
    return cn


def conectar(base: str, timeout: int, servidor: str = SERVIDOR,
             credencial: str = CREDENCIAL, escribir: bool = False) -> pyodbc.Connection:
    cred = _leer_credencial(credencial)
    if cred is None:
        sys.exit(
            f"No está la credencial «{credencial}» en el Administrador de "
            "credenciales de Windows. Se carga UNA vez, en una terminal (pide "
            "la clave sin mostrarla):\n\n"
            f"    cmdkey /generic:{credencial} /user:lectura /pass\n")
    usuario, clave = cred
    driver = next((d for d in _DRIVERS if d in pyodbc.drivers()), None)
    if driver is None:
        sys.exit("Falta el «ODBC Driver 17 for SQL Server» (o el 18).")

    def llaves(v: str) -> str:          # ODBC: un valor con ; o } va entre llaves
        return "{" + v.replace("}", "}}") + "}"

    cadena = (f"DRIVER={{{driver}}};SERVER={servidor};DATABASE={base};"
              f"UID={llaves(usuario)};PWD={llaves(clave)};"
              "APP=claude;TrustServerCertificate=yes")
    try:
        return _abrir(cadena, timeout, escribir)
    except pyodbc.Error as e:
        # El mensaje del driver nombra al usuario; la cadena y la clave, nunca.
        sys.exit(f"No conecta a {servidor} como {usuario}: {e.args[-1]}")


def _lotes(sql: str) -> list[str]:
    """Parte en los `GO` de SSMS: es de la consola, el servidor no lo entiende."""
    return [lote for lote in re.split(r"(?im)^[ \t]*GO[ \t]*;?[ \t]*$", sql)
            if lote.strip()]


def ejecutar(cn: pyodbc.Connection, sql: str, maximo: int,
             csv: pathlib.Path | None) -> None:
    import pandas as pd

    cur = cn.cursor()
    n = 0
    for lote in _lotes(sql):
        cur.execute(lote)
        while True:
            if cur.description:
                n += 1
                cols = [d[0] or f"col{i + 1}" for i, d in enumerate(cur.description)]
                # Sin CSV se trae una fila de más: alcanza para saber si hay más.
                filas = cur.fetchall() if csv else cur.fetchmany(maximo + 1)
                df = pd.DataFrame.from_records([tuple(f) for f in filas], columns=cols)
                if n > 1:
                    print()
                if df.empty:
                    print(" | ".join(cols))
                else:
                    print(df.head(maximo).to_string(index=False, max_colwidth=60))
                cuantas = f"{len(df)} fila{'' if len(df) == 1 else 's'}"
                if csv:
                    destino = csv if n == 1 else csv.with_stem(f"{csv.stem}_{n}")
                    df.to_csv(destino, index=False, encoding="utf-8-sig")
                    print(f"({cuantas} → {destino})")
                elif len(df) > maximo:
                    print(f"(primeras {maximo}; hay más — subí --max o usá --csv)")
                else:
                    print(f"({cuantas})")
            if not cur.nextset():
                break
    if n == 0:
        print("(la consulta no devolvió ninguna tabla)")


_PROBAR_SERVIDOR = """
SELECT SUSER_SNAME(), @@SERVERNAME,
       CAST(SERVERPROPERTY('ProductVersion') AS varchar(20)),
       IS_SRVROLEMEMBER('sysadmin')
"""

# Permisos EFECTIVOS, no los declarados: HAS_PERMS_BY_NAME suma roles, grants
# al rol public y todo lo demás. Los procedimientos cuentan como escritura:
# uno que haga INSERT escribe con los permisos de su dueño (encadenamiento de
# propietarios), así que un datareader que puede ejecutarlo no es de sólo
# lectura. IS_MEMBER y no IS_ROLEMEMBER, que es de 2012 (compatibilidad 100).
#
# No cuentan los seis de «Diagramas de base de datos» que SSMS crea en dbo y
# abre al rol public (medido 2026-09-24: los mismos seis en ALMACEN, INFOREST
# y ALMACENPRUEBA1): sólo guardan dibujos de tablas en `sysdiagrams`, y de
# contarlos el veredicto diría «puede escribir» en toda base que alguna vez
# abrió un diagrama.
_PROCS_DIAGRAMAS = ("'sp_alterdiagram', 'sp_creatediagram', 'sp_dropdiagram', "
                    "'sp_helpdiagramdefinition', 'sp_helpdiagrams', 'sp_renamediagram'")
_PROBAR_BASE = """
SELECT IS_MEMBER('db_datareader'),
       IS_MEMBER('db_datawriter') | IS_MEMBER('db_owner'),
       HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DEFINITION'),
       (SELECT COUNT(*) FROM sys.tables
         WHERE HAS_PERMS_BY_NAME(QUOTENAME(SCHEMA_NAME(schema_id)) + '.' + QUOTENAME(name), 'OBJECT', 'INSERT') = 1
            OR HAS_PERMS_BY_NAME(QUOTENAME(SCHEMA_NAME(schema_id)) + '.' + QUOTENAME(name), 'OBJECT', 'UPDATE') = 1
            OR HAS_PERMS_BY_NAME(QUOTENAME(SCHEMA_NAME(schema_id)) + '.' + QUOTENAME(name), 'OBJECT', 'DELETE') = 1),
       (SELECT COUNT(*) FROM sys.procedures
         WHERE HAS_PERMS_BY_NAME(QUOTENAME(SCHEMA_NAME(schema_id)) + '.' + QUOTENAME(name), 'OBJECT', 'EXECUTE') = 1
           AND NOT (SCHEMA_NAME(schema_id) = 'dbo' AND name IN (""" + _PROCS_DIAGRAMAS + """)))
"""


def probar(cn: pyodbc.Connection) -> None:
    cur = cn.cursor()
    login, servidor, version, sysadmin = cur.execute(_PROBAR_SERVIDOR).fetchone()
    print(f"Entré como {login} a {servidor} (SQL Server {version}).")
    bases = [f[0] for f in cur.execute(
        "SELECT name FROM sys.databases WHERE database_id > 4 "
        "AND HAS_DBACCESS(name) = 1 ORDER BY name").fetchall()]
    if sysadmin:
        # sysadmin entra a todas y puede todo: contar permisos base por base
        # sería medir lo que ya se sabe.
        print("sysadmin: SÍ — puede leer y escribir en todas las bases.")
        print("Bases: " + ", ".join(bases))
        print("Sin --escribir, el script deshace todo cambio al terminar.")
        return
    print("sysadmin: no\n")
    si = {1: "sí", 0: "no", None: "?"}
    print(f"{'base':<18}{'lee':<6}{'rol que escribe':<17}{'ve código':<11}"
          f"{'tablas escribibles':<20}procs ejecutables (sin los de diagramas)")
    escribe = False
    for b in bases:
        cur.execute(f"USE [{b.replace(']', ']]')}];")
        lee, rol, codigo, tablas, procs = cur.execute(_PROBAR_BASE).fetchone()
        escribe = escribe or bool(rol) or tablas > 0 or procs > 0
        print(f"{b:<18}{si[lee]:<6}{si[rol]:<17}{si[codigo]:<11}{tablas:<20}{procs}")
    print("\n" + ("OJO: este login PUEDE escribir en algún lado (ver arriba). Sin "
                  "--escribir, el script igual lo deshace al terminar." if escribe
                  else "Solo lectura: no puede cambiar datos en ninguna base."))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Consultas al SQL Server del restaurante; todo cambio se "
                    "deshace al terminar, salvo con --escribir.")
    que = ap.add_mutually_exclusive_group(required=True)
    que.add_argument("-q", "--consulta", help="SQL en una sola línea")
    que.add_argument("-f", "--archivo", type=pathlib.Path,
                     help="archivo .sql (admite lotes separados por GO)")
    que.add_argument("--probar", action="store_true",
                     help="con qué login entra y qué puede hacer en cada base")
    ap.add_argument("--base", default="ALMACEN")
    ap.add_argument("--max", type=int, default=50, help="filas a mostrar por resultado")
    ap.add_argument("--csv", type=pathlib.Path, help="guardar el resultado entero en CSV")
    ap.add_argument("--timeout", type=int, default=120, help="segundos por consulta")
    ap.add_argument("--escribir", action="store_true",
                    help="que los cambios QUEDEN grabados; sólo si el usuario pidió ese cambio")
    ap.add_argument("--servidor", default=SERVIDOR)
    ap.add_argument("--credencial", default=CREDENCIAL,
                    help="nombre de la credencial genérica de Windows")
    a = ap.parse_args()

    cn = conectar(a.base, a.timeout, a.servidor, a.credencial, a.escribir)
    try:
        if a.probar:
            probar(cn)
        else:
            sql = a.consulta or a.archivo.read_text(encoding="utf-8-sig")
            ejecutar(cn, sql, a.max, a.csv)
    except pyodbc.Error as e:
        sys.exit(f"Error de SQL Server: {e.args[-1]}")
    finally:
        if not a.escribir:
            with contextlib.suppress(pyodbc.Error):
                cn.rollback()       # lo que la consulta haya cambiado se deshace acá
        cn.close()


if __name__ == "__main__":
    main()
