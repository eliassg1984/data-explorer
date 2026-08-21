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

| `.bat` | Cuándo | Qué hace |
|---|---|---|
| `sunat_pedidos.bat` | cada minuto | Atiende lo que alguien pidió con el botón "Traer el original". Sin pedidos sale en ~1 seg **sin abrir el navegador**. |
| `sunat_nocturno.bat` | 1 vez de noche | Atiende pedidos y con el tiempo restante baja lo que falta, de lo más nuevo hacia atrás. Corta a los 120 min. |

**Medido en el servidor: ~23 seg por documento**, o sea ~313 por noche a 2
horas. Con 9.813 pendientes son **~31 noches** para cubrir la ventana de 24
meses. Para ir más rápido las primeras semanas, subir a `--minutos 240`
(~16 noches).

> **El usuario de la tarea importa.** Python, sus paquetes y el Chromium
> quedan bajo el perfil de quien haya corrido el `pip install`
> (`Administrador`). Si la tarea programada corre con otro usuario, falla
> con "No module named pandas" aunque a mano funcione perfecto.

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
