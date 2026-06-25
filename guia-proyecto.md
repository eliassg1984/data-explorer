# Guía del proyecto — cómo trabajar con IA

Este archivo es el "mapa" de la app. Sirve para que, aunque no leas código,
puedas decirle a la IA **exactamente dónde** hacer cada cambio. Déjalo en el
repositorio y dentro del proyecto de Claude para que siempre esté a la vista.

---

## Qué es esta app

Un panel de reportes (inventario, compras, ventas, recetas, etc.) hecho en
Streamlit. Los datos viven en archivos Parquet en Cloudflare R2 y se consultan
con DuckDB. Si no hay credenciales configuradas, la app entra en **modo demo**
con datos de ejemplo para que todo se pueda abrir igual.

---

## El mapa: "quiero cambiar X → el archivo es Y"

| Quiero cambiar...                                                        | Archivo                     |
| ------------------------------------------------------------------------ | --------------------------- |
| Colores, fuentes, apariencia general                                     | `estilos.py`                |
| Agregar o quitar un reporte, o cambiar sus columnas, filtros o ícono     | `data.py` (sección `REPORTES`) |
| Cómo se ve o se comporta una **tabla** (formato de números, totales)     | `tablas.py`                 |
| Los **gráficos** y las tarjetas de indicadores (KPIs)                    | `graficos.py`               |
| La barra de iconos del costado o la franja de arriba                      | `navegacion.py`             |
| De dónde vienen los **datos** (conexión a R2, modo demo)                 | `data.py`                   |
| El **inspector** de datos crudos                                         | `inspector.py`              |
| Herramientas de diagnóstico (errores en pantalla, `?debug`, `?inspector`)| `inyecciones.py`            |
| Cómo arranca todo y qué reporte se muestra primero                       | `app.py`                    |
| (interno) Buscar columnas por nombre aunque tengan acentos o espacios    | `utils.py`                  |

> Truco: cuando le pidas un cambio a la IA, puedes decir directamente
> "esto va en `tablas.py`" usando esta tabla. Le ahorras tiempo y reduces
> el riesgo de que toque el archivo equivocado.

---

## Qué hace cada archivo

- **app.py** — El director de orquesta: arranca la app, decide qué reporte
  mostrar y arma la pantalla. No debería tener lógica complicada adentro.
- **data.py** — Los datos y la **configuración de cada reporte**. Aquí vive
  `REPORTES`, que es tu "panel de control": qué archivo usa cada reporte, qué
  columnas muestra, qué filtros tiene y qué ícono lleva.
- **estilos.py** — Los colores y la apariencia general (CSS).
- **tablas.py** — Las tablas: formato de números en soles, totales al pie,
  columnas fijas, etc.
- **graficos.py** — Los gráficos y las tarjetas de indicadores (KPIs).
- **navegacion.py** — La barra de iconos del costado y la franja superior.
- **inyecciones.py** — Trucos de diagnóstico que muestran los errores en
  pantalla sin tener que abrir la consola del navegador.
- **inspector.py** — Herramienta para mirar los datos crudos y confirmar que
  un registro de verdad existe en el archivo.
- **utils.py** — Ayudas internas para encontrar columnas aunque el nombre
  venga con acentos, espacios o mayúsculas distintas.
- **README.md** — Descripción corta del proyecto.

---

## Reglas para mantener el orden

1. **Un archivo, un trabajo.** Si algo no encaja claramente en un archivo,
   probablemente necesita el suyo propio.
2. **Nada duplicado, nada muerto.** Dos copias de lo mismo = un día le pides
   un cambio a la IA y "no pasa nada", porque editó la copia equivocada.
   (Por esta razón se borró `ui.py`, que era una versión vieja.)
3. **Ajustes separados del motor.** Lo que vas a querer tocar seguido
   —reportes, columnas, colores— vive en lugares claros (sobre todo `REPORTES`
   en `data.py`). El resto es maquinaria: déjala quieta salvo que haga falta.
4. **Archivos cortos.** Si un archivo crece demasiado, pídele a la IA que lo
   divida. Archivos cortos = la IA los lee completos y se equivoca menos.
5. **Todo igual.** Que cada reporte funcione del mismo modo; así uno nuevo se
   hace "copiando" la lógica de uno que ya existe.

---

## Cómo pedirle cambios a la IA

- **Describe qué quieres en palabras simples** y, si puedes, indícale el
  archivo usando el mapa de arriba.
- **Un cambio a la vez.** Pide una sola cosa, verifica que funcione, y recién
  pasa a la siguiente. Así, si algo se rompe, sabes exactamente qué lo causó.
- **Pide que te expliquen en simple** qué se cambió y qué se podría romper.
- **Pide cómo comprobarlo:** qué pantalla abrir, qué botón tocar y qué
  deberías ver si salió bien.
- **Cuando un cambio funcione, súbelo** al repositorio y al proyecto, para que
  la IA siempre esté viendo la versión más reciente.
