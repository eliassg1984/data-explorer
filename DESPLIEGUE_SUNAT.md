# Despliegue de los procesos de SUNAT

Son **dos procesos distintos**, con necesidades distintas. Conviene no
pensarlos juntos: uno es barato y no necesita navegador, el otro es lento
y necesita Chromium prendido.

| | Qué hace | Navegador | Dura | Dónde puede correr |
|---|---|---|---|---|
| **A · Registro** | Los ~16.500 comprobantes → `sunat_compras.parquet` en R2 | No | ~4 min | GitHub Actions, o cualquier máquina |
| **B · Originales** | El PDF/XML que emitió el proveedor, a R2 | Sí | tope configurable | Una máquina prendida |

La webapp (Streamlit Cloud) **sólo lee de R2**. Nunca habla con SUNAT ni
abre un navegador.

---

## B · Originales — UN SOLO ARCHIVO

`herramientas/servidor/sunat_originales.py` está hecho para copiarse
suelto a `C:\proyecto\` del servidor, junto a `Extraer a parquet.py` y
`atender_solicitudes.py`. **No hace falta el repo ahí.**

### Instalación

1. Copiar **un archivo**: `sunat_originales.py` → `C:\proyecto\`
2. Dependencias:
   ```
   pip install pandas pyarrow boto3 playwright
   playwright install chromium
   ```
3. Crear `C:\proyecto\credenciales\sunat.json`:
   ```json
   {
     "SUNAT_RUC": "20...",
     "SUNAT_USUARIO_SOL": "...",
     "SUNAT_CLAVE_SOL": "..."
   }
   ```

Las credenciales de **R2 no se configuran**: las lee de
`Extraer a parquet.py`, igual que hace `atender_solicitudes.py`. Si ese
archivo cambia de nombre, actualizar `NOMBRE_ARCHIVO_EXTRACTOR` arriba del
script.

### Las dos tareas

Copiar también `sunat_pedidos.bat` y `sunat_nocturno.bat` a `C:\proyecto\`
y programarlos — traen la ruta completa al `python.exe` y mandan la salida
a `logs\`.

| Qué | Cómo | Cuándo |
|---|---|---|
| **Pedidos** | Servicio con NSSM: `sunat_originales.py --vigilar` | permanente |
| **Backfill** | Tarea programada: `sunat_nocturno.bat` | 1 vez de noche |

Los pedidos van como **servicio**, no como tarea cada minuto — mismo
patrón que `atender_solicitudes.py`, y por lo mismo: el arranque pesado
(importar pandas, cargar el extractor, crear el cliente de R2) ocurre una
vez en lugar de en cada revisión.

> **El intervalo es 15 seg, no 5.** No es gusto, es presupuesto: cada
> revisión es una operación Class A de R2, y el tier gratuito da 1.000.000
> al mes. `atender_solicitudes.py` a 5 seg ya consume ~518.000; otro
> proceso igual sumaría ~1.036.000 y se pasaría. A 15 seg esto usa
> ~173.000 y el total queda en ~700.000. Como la descarga tarda ~23 seg,
> esperar hasta 15 no cambia nada para quien apretó el botón.

**Medido en el servidor: ~23 seg por documento**, o sea ~313 por noche a 2
horas. Con 9.813 pendientes son **~31 noches** para cubrir la ventana de 24
meses. Para ir más rápido las primeras semanas, subir a `--minutos 240`
(~16 noches).

> **⚠️ EL USUARIO DEL SERVICIO/TAREA ES EL ERROR MÁS PROBABLE.** Costó 40
> minutos de diagnóstico en el despliegue real (2026-08-20).
>
> NSSM instala el servicio como **LocalSystem** por defecto. Con esa
> cuenta, Python y sus paquetes SÍ se encuentran (viven en la carpeta de
> instalación), así que el servicio arranca y parece sano — pero
> **Chromium no**, porque `playwright install` lo deja en el perfil del
> usuario que lo corrió. El síntoma es este, en bucle cada 15 seg:
>
> ```
> ERROR en el ciclo: BrowserType.launch: Executable doesn't exist at
> C:\Windows\system32\config\systemprofile\AppData\Local\ms-playwright\...
> ```
>
> `C:\Windows\system32\config\systemprofile` es el perfil de SYSTEM: si
> aparece esa ruta, el servicio está corriendo con la cuenta equivocada.
> Se arregla en `nssm edit <servicio>` → pestaña **Log on** → *This
> account* → `.\Administrador`. Verificable con `sc qc <servicio>`: la
> línea NOMBRE_INICIO_SERVICIO tiene que decir `.\Administrador`, no
> `LocalSystem`.
>
> Lo mismo aplica a la tarea programada del nocturno.

### Cortar el nocturno a mano: hay que matar el proceso, no la tarea

"Finalizar" en el Programador mata el `.bat`, **no el `python.exe` que
lanzó** — el backfill sigue corriendo y sigue teniendo el candado tomado.
Para cortarlo de verdad:

```
wmic process where "name='python.exe'" get processid,commandline
taskkill /F /PID <el que diga sunat_originales.py --minutos>
```

Nunca `taskkill /F /IM python.exe`: eso mataría también los servicios.

Y como un proceso matado a la fuerza no ejecuta su `finally`, **el candado
queda huérfano**. Se borra a mano (o se espera a que venza a las 4 h):

```
del C:\proyecto\logs\sunat.lock
```

### Antes de programar, probar

```
python sunat_originales.py --limite 3 --ver
```
Abre la ventana del navegador y baja 3 documentos. Si los 3 dicen
"subido", está listo.

---

## A · Registro — en GitHub Actions

`.github/workflows/sunat-registro.yml` corre todos los días a las **08:30
UTC = 03:30 de Perú**, en ~4 minutos.

Se eligió Actions sobre el servidor porque este proceso **no necesita
navegador**: así el código no queda en una máquina compartida de uso
administrativo, no depende de que ningún equipo esté prendido, y sigue
funcionando igual el día que el repo pase a privado.

Lo único a configurar, una vez, en **Settings → Secrets and variables →
Actions** del repo: los 9 secrets con sus valores.

```
SUNAT_RUC            SUNAT_CLIENT_ID       R2_ACCOUNT_ID    R2_SECRET_KEY
SUNAT_USUARIO_SOL    SUNAT_CLIENT_SECRET   R2_ACCESS_KEY    R2_BUCKET
SUNAT_CLAVE_SOL
```

Para probarlo sin esperar al horario: **Actions → "Registro SUNAT a R2" →
Run workflow**. Si falta algún secret, el primer paso lo dice por nombre
en vez de fallar con un error críptico de SUNAT.

> GitHub apaga los workflows programados si el repo pasa 60 días sin
> actividad (avisa por mail antes).

---

## Verificar que funciona

- **El parquet:** `sunat_compras.parquet` en R2, con fecha de hoy.
- **En la webapp:** Compras → Documentos SUNAT. La tira de KPIs termina en
  "hoy". Si dice "hace N días" en ámbar, el proceso A dejó de correr.
- **Los originales:** abrir un documento reciente — deben aparecer los
  botones "📄 PDF original" y "🧾 XML".
- **Los pedidos:** abrir un documento viejo, apretar "⬇ Traer el original
  de SUNAT", esperar un minuto y volver a entrar.

## Qué mirar cada tanto

El proceso B navega el portal de SUNAT como lo haría una persona. **No es
un contrato público**: el día que SUNAT cambie un selector va a fallar, y
va a fallar **en silencio** salvo que alguien lea el log.

```
python sunat_originales.py --minutos 120 >> logs\sunat.txt 2>&1
```

Para diagnosticar: `--ver` abre la ventana y se ve dónde se traba. Los
tres arreglos que ya costó este flujo están en `arquitectura.md` regla
#142.

El proceso A no tiene ese riesgo: usa la API REST del SIRE, no el portal.

## Cuidado al tocar el archivo del servidor

`sunat_originales.py` **duplica a propósito** las funciones que arman las
claves de R2, que también viven en `sunat.py` del repo. Si divergen, el
script sube archivos con un nombre y la webapp los busca con otro — sin
error, sólo originales que nunca aparecen.

`test_sunat.py` compara ambas versiones y falla si difieren. Como se corre
antes de cada push, la desincronización se caza sola. **No sacar esa
prueba.**
