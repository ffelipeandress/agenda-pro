from pathlib import Path


# ============================================================
# AGENDA PRO — CONFIGURACIÓN GENERAL
# ============================================================
# Este archivo centraliza los datos principales del sistema.
# Más adelante podremos cambiar el nombre del salón, colores,
# horarios o rutas sin modificar todos los módulos.
# ============================================================


# ------------------------------------------------------------
# INFORMACIÓN GENERAL
# ------------------------------------------------------------

APP_NAME = "Agenda PRO"
SALON_NAME = "Acrylic Purple"
APP_VERSION = "0.1.0"

PAGE_TITLE = f"{APP_NAME} | {SALON_NAME}"
PAGE_ICON = "💅"


# ------------------------------------------------------------
# RUTAS DEL PROYECTO
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "agenda_pro.db"

BACKUPS_DIR = BASE_DIR / "backups"

ASSETS_DIR = BASE_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"

LOGO_PATH = ASSETS_DIR / "logo.png"


# ------------------------------------------------------------
# CONFIGURACIÓN DE RESPALDOS
# ------------------------------------------------------------

PREFIJO_RESPALDO = "agenda_pro"
MAXIMO_RESPALDOS = 30


# ------------------------------------------------------------
# HORARIOS DE ATENCIÓN
# ------------------------------------------------------------

DIAS_ATENCION = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
}

HORARIOS_DIARIOS = [
    "09:00",
    "15:00",
    "18:30",
]

HORA_PRIMERA_RESERVA = "09:00"
HORA_SEGUNDA_RESERVA = "15:00"
HORA_TERCERA_RESERVA = "18:30"


# ------------------------------------------------------------
# ESTADOS DE LAS RESERVAS
# ------------------------------------------------------------

ESTADO_RESERVADA = "Reservada"
ESTADO_ATENDIDA = "Atendida"
ESTADO_CANCELADA = "Cancelada"

ESTADOS_RESERVA = [
    ESTADO_RESERVADA,
    ESTADO_ATENDIDA,
    ESTADO_CANCELADA,
]


# ------------------------------------------------------------
# COLORES PRINCIPALES
# ------------------------------------------------------------

COLOR_PRINCIPAL = "#6A189A"
COLOR_PRINCIPAL_OSCURO = "#4B0F73"
COLOR_PRINCIPAL_CLARO = "#8D3FC2"

COLOR_LILA = "#E9D5FF"
COLOR_LILA_CLARO = "#F6EEFF"

COLOR_ROSADO = "#FF6EC7"
COLOR_ROSADO_CLARO = "#FFE5F5"

COLOR_FONDO = "#FFFFFF"
COLOR_FONDO_SUAVE = "#FAF8FC"

COLOR_TEXTO = "#242437"
COLOR_TEXTO_SUAVE = "#6F6F82"

COLOR_BORDE = "#E7E2EC"

COLOR_EXITO = "#2E9B58"
COLOR_EXITO_CLARO = "#E7F7EC"

COLOR_ADVERTENCIA = "#E6A700"
COLOR_ADVERTENCIA_CLARO = "#FFF6D8"

COLOR_ERROR = "#DC3545"
COLOR_ERROR_CLARO = "#FFE9EC"

COLOR_GRIS = "#B2B3BE"
COLOR_GRIS_CLARO = "#F1F1F5"


# ------------------------------------------------------------
# DISEÑO GENERAL
# ------------------------------------------------------------

RADIO_BORDE = "14px"
RADIO_BORDE_GRANDE = "20px"

SOMBRA_SUAVE = "0 4px 18px rgba(74, 31, 97, 0.08)"
SOMBRA_MEDIA = "0 8px 24px rgba(74, 31, 97, 0.12)"

FUENTE_PRINCIPAL = "Arial, Helvetica, sans-serif"


# ------------------------------------------------------------
# TEXTOS DEL SISTEMA
# ------------------------------------------------------------

TEXTO_PRECIO_BASE = "Precio base, no incluye diseños adicionales."

MENSAJE_SIN_RESERVAS = "No existen reservas para este día."
MENSAJE_HORA_LIBRE = "Hora disponible."
MENSAJE_RESERVA_GUARDADA = "La reserva fue guardada correctamente."
MENSAJE_RESERVA_CANCELADA = "La reserva fue cancelada y la hora quedó disponible."


# ------------------------------------------------------------
# FUNCIONES DE PREPARACIÓN
# ------------------------------------------------------------

def preparar_directorios() -> None:
    """
    Crea automáticamente las carpetas fundamentales del sistema.

    Esta función permite que Agenda PRO pueda iniciarse aunque alguna
    carpeta haya sido eliminada accidentalmente.
    """

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)


def obtener_nombre_completo() -> str:
    """
    Devuelve el nombre completo mostrado en la interfaz.
    """

    return f"{APP_NAME} — {SALON_NAME}"


def obtener_version_visible() -> str:
    """
    Devuelve la versión de la aplicación en formato visible.
    """

    return f"Versión {APP_VERSION}"
