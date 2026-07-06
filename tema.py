"""
tema.py — PALETA DE COLORES del proyecto, definida UNA sola vez.

Regla de oro: ningún fichero debe escribir un color a mano (#xxxxxx).
Todos importan de aquí:

    from tema import ACENTO, LAVANDA_FONDO, GRIS_BORDE

Así, cambiar un tono de la marca = editar UNA línea de este fichero.
Los valores de abajo fueron extraídos del código existente (no cambian
nada visualmente): son los mismos colores que ya usa la app.
"""

# ═══════════════════════════════════════════════════════════════════════════
# MORADOS / LAVANDAS (identidad de la marca)
# ═══════════════════════════════════════════════════════════════════════════

ACENTO = "#6c5ce7"
"""Morado principal de la marca ("Lavender Indigo"). En estilos.py es
--accent. Acentos, textos activos, bordes de foco."""

ACENTO_FUERTE = "#5a4ad9"
"""Morado más intenso: estado hover/activo fuerte (toggles encendidos,
botón de página activa). En estilos.py es --accent-hover."""

ACENTO_TEXTO = "#4938b8"
"""Índigo para texto sobre fondos lavanda (etiquetas de chips activos)."""

ACENTO_TEXTO_OSCURO = "#3b2e93"
"""Índigo oscuro: cabeceras de grupo, títulos sobre lavanda."""

LAVANDA_FONDO = "#f0edfe"
"""Fondo lavanda suave: hover de chips, filas/botones activos."""

LAVANDA_BORDE = "#d4cdf7"
"""Borde lavanda: chips activos, hover de pastillas."""

LAVANDA_CHIP = "#eeedfe"
"""Fondo de chips/píldoras (título de reporte, fecha)."""

LAVANDA_CABECERA_GRUPO = "#e7e3fb"
"""Fondo de cabeceras de grupo de columnas en el grid."""

# ═══════════════════════════════════════════════════════════════════════════
# GRISES (estructura y texto)
# ═══════════════════════════════════════════════════════════════════════════

GRIS_FONDO = "#f6f6f8"
"""Fondo de pastillas/chips en reposo (paneles Columnas, Filtros, Pivote)."""

GRIS_BORDE = "#e6e6eb"
"""Borde estándar de pastillas, botones y separadores."""

GRIS_LINEA = "#f1f1f4"
"""Líneas divisorias finas (0.5px) entre filas."""

GRIS_TEXTO = "#71717a"
"""Texto secundario: etiquetas, títulos de campos."""

GRIS_TEXTO_SUAVE = "#a2a2ad"
"""Texto terciario: iconos, placeholders, títulos de sección."""

GRIS_TOGGLE_APAGADO = "#e6e6eb"
"""Fondo del interruptor apagado (mismo tono que GRIS_BORDE, a propósito)."""

TEXTO_PRINCIPAL = "#18181d"
"""Texto principal casi negro."""

BLANCO = "#ffffff"


# ═══════════════════════════════════════════════════════════════════════════
# ESTADOS SEMÁNTICOS (éxito / advertencia / error)
# Cada estado tiene 3 tonos: base (fuerte), fondo (claro) y — cuando aplica —
# borde/texto intermedio. Nombres alineados con las variables --success/
# --warning/--danger que ya existen en estilos.py.
# ═══════════════════════════════════════════════════════════════════════════

EXITO = "#16a34a"
"""Verde base: badges de éxito, ajustes positivos."""

EXITO_FONDO = "#f0fdf4"
"""Verde muy claro: fondo de badge/alerta de éxito."""

ADVERTENCIA = "#f97316"
"""Naranja base: badges de advertencia."""

ADVERTENCIA_FONDO = "#fff7ed"
"""Naranja muy claro: fondo de alerta de advertencia."""

ADVERTENCIA_BORDE = "#fdba74"
"""Naranja medio: borde de alerta de advertencia."""

ADVERTENCIA_TEXTO = "#c2410c"
"""Naranja oscuro: texto sobre fondo de advertencia."""

ERROR = "#ef4444"
"""Rojo base: badges/estados de error."""

ERROR_FONDO = "#fee2e2"
"""Rojo muy claro: fondo de alerta de error."""

ERROR_BORDE = "#fca5a5"
"""Rojo medio: borde de alerta de error."""

# ═══════════════════════════════════════════════════════════════════════════
# LAVANDA DE FOCO
# ═══════════════════════════════════════════════════════════════════════════

LAVANDA_FOCO = "#b9aff2"
"""Lavanda claro para bordes de foco/selección (inputs, tabs activos)."""


# ═══════════════════════════════════════════════════════════════════════════
# NOTAS DE USO
# ═══════════════════════════════════════════════════════════════════════════
# - En diccionarios de CSS (custom_css de AgGrid) se usan con f-string:
#       {"background": f"{GRIS_FONDO} !important"}
# - En bloques CSS de estilos.py igual:
#       f".mi-clase {{ color: {GRIS_TEXTO}; }}"
# - Si necesitas un color NUEVO, créalo aquí con nombre y comentario;
#   nunca lo pegues directo en otro fichero.
