import base64
import calendar
from datetime import date, datetime, time, timedelta
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from database.database import (
    conectar,
    obtener_bloqueos_fecha,
    obtener_horarios_del_dia,
    obtener_resumen_bloqueos_mes,
    obtener_servicios_activos,
)


# ============================================================
# AGENDA PRO — CALENDARIO MENSUAL
# ============================================================


MESES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

NOMBRES_DIAS = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


# ============================================================
# FUNCIONES GENERALES
# ============================================================


def formato_pesos(valor: int) -> str:
    return f"${int(valor):,}".replace(",", ".")


def nombre_mes(anio: int, mes: int) -> str:
    return f"{MESES_ES[mes]} {anio}"


def sumar_mes(anio: int, mes: int, cantidad: int) -> tuple[int, int]:
    nuevo_anio = anio
    nuevo_mes = mes + cantidad

    while nuevo_mes > 12:
        nuevo_mes -= 12
        nuevo_anio += 1

    while nuevo_mes < 1:
        nuevo_mes += 12
        nuevo_anio -= 1

    return nuevo_anio, nuevo_mes


def titulo_fecha(fecha_seleccionada: date) -> str:
    nombre_dia = NOMBRES_DIAS[fecha_seleccionada.weekday()]
    nombre_mes_fecha = MESES_ES[fecha_seleccionada.month].lower()

    return (
        f"{nombre_dia} "
        f"{fecha_seleccionada.day} de "
        f"{nombre_mes_fecha}"
    )


def fecha_es_dia_habil(fecha_seleccionada: date) -> bool:
    return fecha_seleccionada.weekday() <= 5


# ============================================================
# ESTADO
# ============================================================


def inicializar_estado_calendario() -> None:
    hoy = date.today()

    if "calendario_anio" not in st.session_state:
        st.session_state.calendario_anio = hoy.year

    if "calendario_mes" not in st.session_state:
        st.session_state.calendario_mes = hoy.month

    if "fecha_seleccionada" not in st.session_state:
        st.session_state.fecha_seleccionada = hoy.isoformat()

    if "pantalla_actual" not in st.session_state:
        st.session_state.pantalla_actual = "calendario"

    if "reserva_seleccionada_id" not in st.session_state:
        st.session_state.reserva_seleccionada_id = None

    if "nueva_reserva_fecha" not in st.session_state:
        st.session_state.nueva_reserva_fecha = None

    if "nueva_reserva_hora" not in st.session_state:
        st.session_state.nueva_reserva_hora = None

    procesar_parametros_calendario_movil()


def procesar_parametros_calendario_movil() -> None:
    """
    Recibe las pulsaciones del calendario HTML mediante parámetros URL.
    Así evitamos st.columns(7) y el selector nativo de fecha.
    """
    try:
        parametros = st.query_params
    except Exception:
        return

    fecha_parametro = parametros.get("fecha")
    anio_parametro = parametros.get("anio")
    mes_parametro = parametros.get("mes")

    if fecha_parametro:
        try:
            fecha_objeto = datetime.strptime(
                str(fecha_parametro),
                "%Y-%m-%d",
            ).date()
        except (TypeError, ValueError):
            fecha_objeto = None

        if fecha_objeto is not None:
            fecha_iso = fecha_objeto.isoformat()
            fecha_anterior = st.session_state.get(
                "fecha_seleccionada"
            )

            st.session_state.fecha_seleccionada = fecha_iso
            st.session_state.calendario_anio = fecha_objeto.year
            st.session_state.calendario_mes = fecha_objeto.month

            # Solo se limpia la navegación cuando la persona
            # realmente selecciona un día distinto.
            if fecha_anterior != fecha_iso:
                st.session_state.reserva_seleccionada_id = None
                st.session_state.nueva_reserva_fecha = None
                st.session_state.nueva_reserva_hora = None

            return

    if anio_parametro and mes_parametro:
        try:
            anio = int(anio_parametro)
            mes = int(mes_parametro)

            if 1 <= mes <= 12:
                st.session_state.calendario_anio = anio
                st.session_state.calendario_mes = mes
        except (TypeError, ValueError):
            pass


def ir_mes_anterior() -> None:
    anio, mes = sumar_mes(
        st.session_state.calendario_anio,
        st.session_state.calendario_mes,
        -1,
    )
    st.session_state.calendario_anio = anio
    st.session_state.calendario_mes = mes


def ir_mes_siguiente() -> None:
    anio, mes = sumar_mes(
        st.session_state.calendario_anio,
        st.session_state.calendario_mes,
        1,
    )
    st.session_state.calendario_anio = anio
    st.session_state.calendario_mes = mes


def ir_mes_actual() -> None:
    hoy = date.today()
    st.session_state.calendario_anio = hoy.year
    st.session_state.calendario_mes = hoy.month
    st.session_state.fecha_seleccionada = hoy.isoformat()


def seleccionar_fecha(fecha_iso: str) -> None:
    st.session_state.fecha_seleccionada = fecha_iso
    st.session_state.reserva_seleccionada_id = None
    st.session_state.nueva_reserva_fecha = None
    st.session_state.nueva_reserva_hora = None


# ============================================================
# CONSULTAS
# ============================================================


def cargar_resumen_reservas_mes(anio: int, mes: int) -> dict[str, int]:
    primer_dia = date(anio, mes, 1)

    if mes == 12:
        siguiente_mes = date(anio + 1, 1, 1)
    else:
        siguiente_mes = date(anio, mes + 1, 1)

    conexion = conectar()

    try:
        filas = conexion.execute(
            """
            SELECT
                fecha,
                COUNT(*) AS cantidad
            FROM reservas
            WHERE fecha >= ?
              AND fecha < ?
              AND estado IN ('Reservada', 'Atendida')
            GROUP BY fecha
            """,
            (primer_dia.isoformat(), siguiente_mes.isoformat()),
        ).fetchall()

        return {
            fila["fecha"]: int(fila["cantidad"])
            for fila in filas
        }

    finally:
        conexion.close()


def cargar_reservas_fecha(fecha_iso: str) -> list[dict]:
    conexion = conectar()

    try:
        filas = conexion.execute(
            """
            SELECT
                r.id,
                r.fecha,
                r.hora,
                r.precio_base,
                r.duracion_minutos,
                r.observacion_interna,
                r.estado,
                r.abono_pagado,
                c.nombre AS cliente,
                c.celular AS celular,
                s.nombre AS servicio
            FROM reservas r
            INNER JOIN clientes c
                ON c.id = r.cliente_id
            INNER JOIN servicios s
                ON s.id = r.servicio_id
            WHERE r.fecha = ?
              AND r.estado IN ('Reservada', 'Atendida')
            ORDER BY r.hora
            """,
            (fecha_iso,),
        ).fetchall()

        return [dict(fila) for fila in filas]

    finally:
        conexion.close()


def obtener_reserva_por_hora(
    reservas: list[dict],
    hora: str,
) -> dict | None:
    for reserva in reservas:
        if reserva["hora"] == hora:
            return reserva

    return None


MARGEN_ENTRE_ATENCIONES_MINUTOS = 30


def convertir_hora_a_datetime(
    fecha_iso: str,
    hora: str,
) -> datetime:
    return datetime.strptime(
        f"{fecha_iso} {hora}",
        "%Y-%m-%d %H:%M",
    )


def horario_cubierto_por_reserva(
    fecha_iso: str,
    hora: str,
    reservas: list[dict],
) -> bool:
    """
    Indica si una hora base cae dentro de una atención existente,
    considerando la duración y 30 minutos de margen.
    """

    instante = convertir_hora_a_datetime(fecha_iso, hora)

    for reserva in reservas:
        inicio = convertir_hora_a_datetime(
            fecha_iso,
            str(reserva["hora"]),
        )
        fin = inicio + timedelta(
            minutes=(
                int(reserva["duracion_minutos"])
                + MARGEN_ENTRE_ATENCIONES_MINUTOS
            )
        )

        if inicio < instante < fin:
            return True

    return False


def obtener_duracion_minima_reservable() -> int | None:
    """
    Devuelve la duración del servicio activo más corto.

    Se usa para decidir si un horario base puede mostrarse realmente
    como disponible antes de una reserva extraordinaria posterior.
    """

    servicios = obtener_servicios_activos()

    duraciones = [
        int(servicio["duracion_minutos"])
        for servicio in servicios
        if int(servicio["duracion_minutos"]) > 0
    ]

    if not duraciones:
        return None

    return min(duraciones)


def horario_base_admite_reserva(
    fecha_iso: str,
    hora: str,
    reservas: list[dict],
    duracion_minima: int | None,
) -> bool:
    """
    Comprueba si al menos el servicio activo más corto puede comenzar
    en un horario base sin cruzarse con una reserva existente.

    Esto evita mostrar, por ejemplo, las 15:00 como disponibles cuando
    existe una reserva a las 16:00 y ningún servicio cabe realmente en
    ese intervalo, considerando también 30 minutos de preparación.
    """

    if duracion_minima is None:
        return False

    inicio_nuevo = convertir_hora_a_datetime(
        fecha_iso,
        hora,
    )
    fin_nuevo = inicio_nuevo + timedelta(
        minutes=(
            int(duracion_minima)
            + MARGEN_ENTRE_ATENCIONES_MINUTOS
        )
    )

    for reserva in reservas:
        inicio_existente = convertir_hora_a_datetime(
            fecha_iso,
            str(reserva["hora"]),
        )
        fin_existente = inicio_existente + timedelta(
            minutes=(
                int(reserva["duracion_minutos"])
                + MARGEN_ENTRE_ATENCIONES_MINUTOS
            )
        )

        if (
            inicio_nuevo < fin_existente
            and inicio_existente < fin_nuevo
        ):
            return False

    return True


def hora_extra_esta_ocupada(
    fecha_iso: str,
    hora: str,
    reservas: list[dict],
) -> bool:
    """
    Evita iniciar un sobrecupo dentro del intervalo ya ocupado.
    La validación completa se vuelve a ejecutar al guardar,
    cuando ya se conoce la duración del nuevo servicio.
    """

    instante = convertir_hora_a_datetime(fecha_iso, hora)

    for reserva in reservas:
        inicio = convertir_hora_a_datetime(
            fecha_iso,
            str(reserva["hora"]),
        )
        fin = inicio + timedelta(
            minutes=(
                int(reserva["duracion_minutos"])
                + MARGEN_ENTRE_ATENCIONES_MINUTOS
            )
        )

        if inicio <= instante < fin:
            return True

    return False



# ============================================================
# NORMALIZACIÓN VISUAL MULTIDISPOSITIVO
# ============================================================


def mostrar_estilos_normalizacion_visual() -> None:
    """
    Unifica el aspecto del calendario y sus controles en Safari,
    Chrome, Edge, iPhone, Android y escritorio.

    No modifica la lógica de reservas ni la base de datos.
    """

    st.html(
        """
        <style>
            :root {
                --ap-purple-900: #4F0D68;
                --ap-purple-800: #651184;
                --ap-purple-700: #7B169F;
                --ap-purple-600: #9225B8;
                --ap-purple-100: #F3E8FA;
                --ap-purple-050: #FAF6FC;

                --ap-text-900: #302336;
                --ap-text-700: #594A60;
                --ap-text-500: #817486;

                --ap-border: #DED7E1;
                --ap-border-strong: #CFC4D3;
                --ap-surface: #FFFFFF;
                --ap-background: #F7F4F8;

                --ap-radius-card: 18px;
                --ap-radius-button: 14px;
                --ap-shadow-card: 0 7px 22px rgba(67, 31, 78, 0.07);
            }

            html,
            body,
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"] {
                background: var(--ap-background) !important;
            }

            [data-testid="stAppViewContainer"] {
                color: var(--ap-text-900);
            }

            [data-testid="stMainBlockContainer"] {
                max-width: 1120px;
                padding-top: 1.1rem;
                padding-bottom: 2.5rem;
            }

            /* Tarjetas creadas con st.container(border=True). */
            [data-testid="stVerticalBlockBorderWrapper"] {
                background: var(--ap-surface) !important;
                border: 1px solid var(--ap-border) !important;
                border-radius: var(--ap-radius-card) !important;
                box-shadow: var(--ap-shadow-card);
                overflow: hidden;
            }

            [data-testid="stVerticalBlockBorderWrapper"]
            > div {
                background: transparent !important;
            }

            /* Botones: mismo alto, radio y tipografía en todos los navegadores. */
            .stButton > button {
                min-height: 46px;
                border-radius: var(--ap-radius-button) !important;
                font-weight: 800 !important;
                line-height: 1.15 !important;
                box-shadow: none !important;
                transition:
                    transform 0.12s ease,
                    border-color 0.12s ease,
                    background 0.12s ease;
                -webkit-appearance: none;
                appearance: none;
            }

            .stButton > button[kind="primary"],
            .stButton > button[data-testid="stBaseButton-primary"] {
                color: #FFFFFF !important;
                background:
                    linear-gradient(
                        135deg,
                        var(--ap-purple-800),
                        var(--ap-purple-600)
                    ) !important;
                border: 1px solid var(--ap-purple-700) !important;
            }

            .stButton > button[kind="secondary"],
            .stButton > button[data-testid="stBaseButton-secondary"] {
                color: var(--ap-purple-800) !important;
                background: #FFFFFF !important;
                border: 1px solid var(--ap-border-strong) !important;
            }

            .stButton > button:active {
                transform: scale(0.99);
            }

            /* Expander de horario extraordinario. */
            [data-testid="stExpander"] {
                margin-top: 10px;
                background: #FFFFFF !important;
                border: 1px solid var(--ap-border-strong) !important;
                border-radius: var(--ap-radius-card) !important;
                box-shadow: var(--ap-shadow-card);
                overflow: hidden;
            }

            [data-testid="stExpander"] details {
                background: #FFFFFF !important;
            }

            [data-testid="stExpander"] summary {
                min-height: 58px;
                padding: 0 17px !important;
                color: var(--ap-text-900) !important;
                background: #FFFFFF !important;
                font-size: 15px !important;
                font-weight: 850 !important;
                -webkit-tap-highlight-color: transparent;
            }

            [data-testid="stExpander"] summary:hover {
                color: var(--ap-purple-800) !important;
                background: var(--ap-purple-050) !important;
            }

            [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
                padding: 4px 17px 17px !important;
                background: #FFFFFF !important;
                border-top: 1px solid #EEE7F0;
            }

            [data-testid="stExpander"] p {
                color: var(--ap-text-700);
            }

            /* Inputs uniformes. */
            [data-testid="stTimeInput"] input,
            [data-testid="stDateInput"] input,
            [data-baseweb="input"] input {
                min-height: 44px;
                color: var(--ap-text-900) !important;
                background: #FFFFFF !important;
                border-radius: 12px !important;
            }

            [data-testid="stTimeInput"] > div,
            [data-testid="stDateInput"] > div {
                border-radius: 12px !important;
            }

            /* Separadores, textos y tarjetas del detalle diario. */
            .ap-period-separator {
                display: flex;
                align-items: center;
                width: 100%;
                margin: 24px 0 12px;
            }

            .ap-period-line {
                flex: 1;
                min-width: 20px;
                height: 1px;
                background: #DCD3DF;
            }

            .ap-period-title {
                padding: 0 14px;
                color: var(--ap-purple-700);
                font-size: 11px;
                font-weight: 900;
                letter-spacing: 1.05px;
                text-align: center;
                text-transform: uppercase;
                white-space: nowrap;
            }

            .appointment-card {
                width: 100%;
                min-width: 0;
            }

            .appointment-status {
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 36px;
                padding: 7px 8px;
                border-radius: 999px;
                font-size: 11px;
                font-weight: 900;
                text-align: center;
            }

            .appointment-status-free {
                color: #25633E;
                background: #E7F7ED;
                border: 1px solid #C8E8D3;
            }

            .selected-day-header,
            .day-summary {
                background: #FFFFFF;
                border: 1px solid var(--ap-border);
                box-shadow: var(--ap-shadow-card);
            }

            /* Safari puede aclarar texto y fondos al aplicar ajustes automáticos. */
            .ap-brand-header,
            .ap-mobile-calendar,
            .selected-day-header,
            .day-summary,
            [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="stExpander"] {
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }

            @media (max-width: 680px) {
                [data-testid="stMainBlockContainer"] {
                    width: 100%;
                    padding: 0.7rem 0.72rem 2rem;
                }

                [data-testid="stVerticalBlockBorderWrapper"] {
                    border-radius: 16px !important;
                    box-shadow: 0 5px 16px rgba(67, 31, 78, 0.06);
                }

                [data-testid="stVerticalBlockBorderWrapper"]
                [data-testid="stHorizontalBlock"] {
                    row-gap: 10px;
                }

                .stButton > button {
                    min-height: 50px;
                    font-size: 15px !important;
                }

                [data-testid="stExpander"] {
                    border-radius: 16px !important;
                }

                [data-testid="stExpander"] summary {
                    min-height: 58px;
                    padding-left: 15px !important;
                    padding-right: 15px !important;
                    font-size: 15px !important;
                }

                [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
                    padding-left: 15px !important;
                    padding-right: 15px !important;
                }

                .ap-period-separator {
                    margin-top: 22px;
                    margin-bottom: 12px;
                }

                .ap-period-title {
                    padding: 0 10px;
                    font-size: 10px;
                }
            }

            @media (max-width: 390px) {
                [data-testid="stMainBlockContainer"] {
                    padding-left: 0.55rem;
                    padding-right: 0.55rem;
                }

                .ap-period-title {
                    letter-spacing: 0.75px;
                }
            }
        </style>
        """
    )


# ============================================================
# ENCABEZADO
# ============================================================


def obtener_logo_html() -> str:
    rutas_logo = [
        Path("assets/logo.PNG"),
        Path("assets/logo.png"),
        Path("assets/logo_acrylic_purple.PNG"),
        Path("assets/logo_acrylic_purple.png"),
        Path("assets/icons/logo.PNG"),
        Path("assets/icons/logo.png"),
        Path("assets/icons/logo_acrylic_purple.PNG"),
        Path("assets/icons/logo_acrylic_purple.png"),
    ]

    for ruta in rutas_logo:
        if not ruta.exists():
            continue

        try:
            contenido = base64.b64encode(
                ruta.read_bytes()
            ).decode("ascii")

            extension = ruta.suffix.lower().replace(".", "")
            tipo = "jpeg" if extension in ("jpg", "jpeg") else extension

            return (
                '<img class="calendar-logo-image" '
                f'src="data:image/{tipo};base64,{contenido}" '
                'alt="Logo Acrylic Purple">'
            )
        except OSError:
            continue

    return '<div class="calendar-main-icon">💅</div>'


def mostrar_estilos_encabezado_logo() -> None:
    st.html(
        """
        <style>
            .ap-brand-header {
                display: grid;
                grid-template-columns: 112px minmax(0, 1fr);
                align-items: center;
                gap: 20px;
                padding: 16px 20px;
                margin-bottom: 16px;
                background:
                    linear-gradient(
                        135deg,
                        rgba(255, 255, 255, 0.98),
                        rgba(249, 239, 253, 0.98)
                    );
                border: 1px solid #E4D2EC;
                border-radius: 24px;
                box-shadow:
                    0 10px 28px rgba(82, 24, 108, 0.11);
                overflow: hidden;
            }

            .ap-brand-logo-box {
                width: 112px;
                height: 112px;
                padding: 5px;
                overflow: hidden;
                background: #17071F;
                border: 2px solid #D99BEC;
                border-radius: 22px;
                box-shadow:
                    0 8px 20px rgba(83, 20, 111, 0.22);
            }

            .ap-brand-logo-box .calendar-logo-image {
                display: block;
                width: 100%;
                height: 100%;
                padding: 0;
                object-fit: cover;
                border-radius: 16px;
            }

            .ap-brand-logo-box .calendar-main-icon {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 100%;
                height: 100%;
                font-size: 42px;
            }

            .ap-brand-eyebrow {
                color: #9B45B7;
                font-size: 11px;
                font-weight: 900;
                letter-spacing: 1.7px;
                text-transform: uppercase;
            }

            .ap-brand-title {
                margin-top: 4px;
                color: #54116F;
                font-size: 30px;
                font-weight: 950;
                line-height: 1.05;
            }

            .ap-brand-salon {
                margin-top: 7px;
                color: #3F3045;
                font-size: 16px;
                font-weight: 800;
            }

            .ap-brand-subtitle {
                margin-top: 4px;
                color: #806E86;
                font-size: 13px;
                font-weight: 650;
            }

            .ap-brand-line {
                width: 78px;
                height: 4px;
                margin-top: 12px;
                background:
                    linear-gradient(
                        90deg,
                        #67158F,
                        #D947C8,
                        #F1A2DE
                    );
                border-radius: 999px;
            }

            @media (max-width: 680px) {
                .ap-brand-header {
                    grid-template-columns: 82px minmax(0, 1fr);
                    gap: 13px;
                    padding: 12px 13px;
                    margin-bottom: 11px;
                    border-radius: 19px;
                }

                .ap-brand-logo-box {
                    width: 82px;
                    height: 82px;
                    padding: 3px;
                    border-radius: 17px;
                }

                .ap-brand-logo-box .calendar-logo-image {
                    border-radius: 12px;
                }

                .ap-brand-eyebrow {
                    font-size: 9px;
                    letter-spacing: 1.2px;
                }

                .ap-brand-title {
                    margin-top: 3px;
                    font-size: 22px;
                }

                .ap-brand-salon {
                    margin-top: 4px;
                    font-size: 13px;
                }

                .ap-brand-subtitle {
                    margin-top: 2px;
                    font-size: 11px;
                    line-height: 1.25;
                }

                .ap-brand-line {
                    width: 55px;
                    height: 3px;
                    margin-top: 8px;
                }
            }
        </style>
        """
    )


def mostrar_encabezado_principal() -> None:
    logo_html = obtener_logo_html()

    st.html(
        f"""
        <section class="ap-brand-header">
            <div class="ap-brand-logo-box">
                {logo_html}
            </div>

            <div>
                <div class="ap-brand-eyebrow">
                    Salón de uñas
                </div>

                <div class="ap-brand-title">
                    Agenda PRO
                </div>

                <div class="ap-brand-salon">
                    Acrylic Purple
                </div>

                <div class="ap-brand-subtitle">
                    Gestión de reservas y clientas
                </div>

                <div class="ap-brand-line"></div>
            </div>
        </section>
        """
    )


def mostrar_navegacion_mes() -> None:
    anio = st.session_state.calendario_anio
    mes = st.session_state.calendario_mes

    columna_anterior, columna_titulo, columna_siguiente = st.columns([1, 5, 1])

    with columna_anterior:
        st.button(
            "‹",
            key="boton_mes_anterior",
            help="Mes anterior",
            use_container_width=True,
            on_click=ir_mes_anterior,
        )

    with columna_titulo:
        st.html(
            f'<div class="calendar-month-title">{nombre_mes(anio, mes)}</div>'
        )

    with columna_siguiente:
        st.button(
            "›",
            key="boton_mes_siguiente",
            help="Mes siguiente",
            use_container_width=True,
            on_click=ir_mes_siguiente,
        )

    st.button(
        "Hoy",
        key="boton_ir_hoy",
        help="Volver al día actual",
        use_container_width=True,
        on_click=ir_mes_actual,
    )


def mostrar_encabezado_dias() -> None:
    columnas = st.columns(7, gap="small")

    for indice, nombre_dia in enumerate(DIAS_SEMANA):
        clase = "calendar-weekday"

        if indice == 6:
            clase += " calendar-weekend-name"

        with columnas[indice]:
            st.html(f'<div class="{clase}">{nombre_dia}</div>')


# ============================================================
# CALENDARIO DE ESCRITORIO
# ============================================================


def construir_etiqueta_dia(
    dia: int,
    cantidad_reservas: int,
    es_domingo: bool,
    tiene_bloqueo: bool = False,
) -> str:
    if es_domingo:
        return f"{dia}\n—"

    indicadores = []

    if cantidad_reservas > 0:
        indicadores.extend(
            ["●"] * min(cantidad_reservas, 3)
        )

    if tiene_bloqueo:
        indicadores.append("◐")

    if not indicadores:
        return str(dia)

    return f"{dia}\n{' '.join(indicadores)}"


def mostrar_celda_dia(
    dia: int,
    anio: int,
    mes: int,
    columna_semana: int,
    resumen_reservas: dict[str, int],
) -> None:
    if dia == 0:
        st.html('<div class="calendar-empty-day"></div>')
        return

    fecha_dia = date(anio, mes, dia)
    fecha_iso = fecha_dia.isoformat()
    es_hoy = fecha_dia == date.today()
    es_domingo = columna_semana == 6
    esta_seleccionado = (
        fecha_iso == st.session_state.fecha_seleccionada
    )
    cantidad_reservas = resumen_reservas.get(fecha_iso, 0)
    resumen_bloqueos = obtener_resumen_bloqueos_mes(anio, mes)
    bloqueo_dia = resumen_bloqueos.get(fecha_iso, {})
    tiene_bloqueo = bool(
        bloqueo_dia.get("dia_completo")
        or bloqueo_dia.get("horas_bloqueadas", 0) > 0
    )

    etiqueta = construir_etiqueta_dia(
        dia=dia,
        cantidad_reservas=cantidad_reservas,
        es_domingo=es_domingo,
        tiene_bloqueo=tiene_bloqueo,
    )

    ayuda = fecha_dia.strftime("%d/%m/%Y")

    if es_hoy:
        ayuda = f"Hoy · {ayuda}"

    if tiene_bloqueo:
        if bloqueo_dia.get("dia_completo"):
            ayuda = f"{ayuda} · Día completo bloqueado"
        else:
            cantidad_bloqueada = int(
                bloqueo_dia.get("horas_bloqueadas", 0)
            )
            ayuda = (
                f"{ayuda} · "
                f"{cantidad_bloqueada} horario(s) bloqueado(s)"
            )

    st.button(
        etiqueta,
        key=f"calendario_dia_{fecha_iso}",
        help=ayuda,
        type="primary" if esta_seleccionado else "secondary",
        disabled=es_domingo,
        use_container_width=True,
        on_click=seleccionar_fecha,
        args=(fecha_iso,),
    )


def mostrar_grilla_mes() -> None:
    anio = st.session_state.calendario_anio
    mes = st.session_state.calendario_mes

    semanas = calendar.Calendar(
        firstweekday=calendar.MONDAY
    ).monthdayscalendar(anio, mes)

    resumen = cargar_resumen_reservas_mes(anio, mes)

    mostrar_encabezado_dias()

    for semana in semanas:
        columnas = st.columns(7, gap="small")

        for indice, dia in enumerate(semana):
            with columnas[indice]:
                mostrar_celda_dia(
                    dia=dia,
                    anio=anio,
                    mes=mes,
                    columna_semana=indice,
                    resumen_reservas=resumen,
                )


# ============================================================
# CALENDARIO MÓVIL HTML/CSS
# ============================================================


def es_dispositivo_movil() -> bool:
    try:
        user_agent = str(
            st.context.headers.get("User-Agent", "")
        ).lower()
    except Exception:
        user_agent = ""

    indicadores = (
        "iphone",
        "ipad",
        "ipod",
        "android",
        "mobile",
        "tablet",
        "samsungbrowser",
    )

    return any(indicador in user_agent for indicador in indicadores)


def construir_calendario_movil_html() -> str:
    anio = st.session_state.calendario_anio
    mes = st.session_state.calendario_mes
    fecha_seleccionada = st.session_state.fecha_seleccionada
    hoy = date.today()

    semanas = calendar.Calendar(
        firstweekday=calendar.MONDAY
    ).monthdayscalendar(anio, mes)

    resumen = cargar_resumen_reservas_mes(anio, mes)
    resumen_bloqueos = obtener_resumen_bloqueos_mes(anio, mes)

    anio_anterior, mes_anterior = sumar_mes(anio, mes, -1)
    anio_siguiente, mes_siguiente = sumar_mes(anio, mes, 1)

    partes = [
        '<section class="ap-mobile-calendar">',
        '<div class="ap-mobile-nav">',
        (
            f'<a class="ap-nav-button" '
            f'href="?anio={anio_anterior}&mes={mes_anterior}" '
            f'target="_self" aria-label="Mes anterior">‹</a>'
        ),
        f'<div class="ap-mobile-month">{nombre_mes(anio, mes)}</div>',
        (
            f'<a class="ap-nav-button" '
            f'href="?anio={anio_siguiente}&mes={mes_siguiente}" '
            f'target="_self" aria-label="Mes siguiente">›</a>'
        ),
        '</div>',
        '<div class="ap-calendar-grid">',
    ]

    for indice, dia_nombre in enumerate(DIAS_SEMANA):
        clase = "ap-weekday"

        if indice == 6:
            clase += " ap-weekday-sunday"

        partes.append(
            f'<div class="{clase}">{dia_nombre.upper()}</div>'
        )

    for semana in semanas:
        for indice, dia in enumerate(semana):
            if dia == 0:
                partes.append(
                    '<div class="ap-day ap-day-empty" aria-hidden="true"></div>'
                )
                continue

            fecha_dia = date(anio, mes, dia)
            fecha_iso = fecha_dia.isoformat()
            cantidad = resumen.get(fecha_iso, 0)
            bloqueo = resumen_bloqueos.get(fecha_iso, {})
            bloqueo_completo = bool(
                bloqueo.get("dia_completo", False)
            )
            bloqueo_parcial = (
                not bloqueo_completo
                and int(bloqueo.get("horas_bloqueadas", 0)) > 0
            )
            es_domingo = indice == 6
            es_hoy = fecha_dia == hoy
            es_seleccionado = fecha_iso == fecha_seleccionada

            clases = ["ap-day"]

            if es_domingo:
                clases.append("ap-day-disabled")
            if es_hoy:
                clases.append("ap-day-today")
            if es_seleccionado:
                clases.append("ap-day-selected")
            if cantidad > 0:
                clases.append("ap-day-with-booking")
            if bloqueo_completo:
                clases.append("ap-day-blocked-full")
            elif bloqueo_parcial:
                clases.append("ap-day-blocked-partial")

            puntos = ""

            if cantidad > 0:
                total_puntos = min(cantidad, 3)
                puntos = (
                    '<span class="ap-dots">'
                    + "".join(
                        '<span class="ap-dot"></span>'
                        for _ in range(total_puntos)
                    )
                    + "</span>"
                )

            bloqueo_html = ""

            if bloqueo_completo or bloqueo_parcial:
                bloqueo_html = (
                    '<span class="ap-block-dot" '
                    'aria-label="Agenda bloqueada"></span>'
                )

            contenido = (
                f'<span class="ap-day-number">{dia}</span>'
                f'{puntos}'
                f'{bloqueo_html}'
            )

            if es_domingo:
                partes.append(
                    f'<div class="{" ".join(clases)}">{contenido}</div>'
                )
            else:
                partes.append(
                    f'<a class="{" ".join(clases)}" '
                    f'href="?fecha={fecha_iso}" target="_self" '
                    f'aria-label="{titulo_fecha(fecha_dia)}">'
                    f'{contenido}</a>'
                )

    partes.extend(
        [
            '</div>',
            (
                f'<a class="ap-today-link" '
                f'href="?fecha={hoy.isoformat()}" target="_self">'
                f'Ir a hoy · {hoy.strftime("%d/%m/%Y")}</a>'
            ),
            '</section>',
        ]
    )

    return "".join(partes)


def mostrar_estilos_calendario_movil() -> None:
    st.html(
        """
        <style>
            .calendar-logo-wrapper {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 58px;
                height: 58px;
                overflow: hidden;
                border-radius: 16px;
                background: #F0D9FC;
            }

            .calendar-logo-image {
                width: 100%;
                height: 100%;
                object-fit: contain;
                padding: 4px;
            }

            .ap-mobile-calendar,
            .ap-mobile-calendar * {
                box-sizing: border-box;
            }

            .ap-mobile-calendar {
                width: 100%;
                margin: 8px 0 12px;
                padding: 13px 10px 12px;
                background: #FFFFFF;
                border: 1px solid #E5D7EC;
                border-radius: 20px;
                box-shadow: 0 9px 28px rgba(73, 32, 91, 0.08);
                overflow: hidden;
            }

            .ap-mobile-nav {
                display: grid;
                grid-template-columns: 44px minmax(0, 1fr) 44px;
                align-items: center;
                gap: 8px;
                margin-bottom: 9px;
            }

            .ap-mobile-month {
                color: #5F1485;
                font-size: 20px;
                font-weight: 850;
                text-align: center;
                line-height: 1.2;
            }

            .ap-nav-button {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 44px;
                height: 42px;
                color: #681391 !important;
                background: #F7ECFB;
                border: 1px solid #E5D1EE;
                border-radius: 13px;
                font-size: 29px;
                font-weight: 700;
                line-height: 1;
                text-decoration: none !important;
                -webkit-tap-highlight-color: transparent;
            }

            .ap-calendar-grid {
                display: grid;
                grid-template-columns: repeat(7, minmax(0, 1fr));
                width: 100%;
                gap: 4px;
            }

            .ap-weekday {
                display: flex;
                align-items: center;
                justify-content: center;
                min-width: 0;
                height: 27px;
                color: #6F6475;
                font-size: 9px;
                font-weight: 850;
                letter-spacing: 0.2px;
                text-align: center;
            }

            .ap-weekday-sunday {
                color: #A49BA8;
            }

            .ap-day {
                position: relative;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-width: 0;
                width: 100%;
                aspect-ratio: 1 / 1;
                min-height: 40px;
                color: #413548 !important;
                background: #FFFFFF;
                border: 1px solid #EAE2ED;
                border-radius: 12px;
                text-decoration: none !important;
                overflow: hidden;
                -webkit-tap-highlight-color: transparent;
            }

            .ap-day-number {
                font-size: 13px;
                font-weight: 800;
                line-height: 1;
            }

            .ap-day-empty {
                visibility: hidden;
                pointer-events: none;
            }

            .ap-day-disabled {
                color: #B7AFBA !important;
                background: #F7F4F8;
                border-color: #EFE9F1;
            }

            .ap-day-today {
                border: 2px solid #8A2AB4;
            }

            .ap-day-selected {
                color: #FFFFFF !important;
                background: linear-gradient(135deg, #691494, #962BC2);
                border-color: transparent;
                box-shadow: 0 5px 13px rgba(102, 20, 145, 0.25);
            }

            .ap-dots {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 2px;
                min-height: 5px;
                margin-top: 5px;
            }

            .ap-dot {
                display: block;
                width: 4px;
                height: 4px;
                background: #7E1EA7;
                border-radius: 999px;
            }

            .ap-day-selected .ap-dot {
                background: #FFFFFF;
            }

            .ap-day-blocked-full {
                color: #654B00 !important;
                background: #FFF1B8;
                border: 2px solid #E8C650;
                box-shadow: inset 0 0 0 1px #F7D96D;
            }

            .ap-day-blocked-partial {
                background: #FFFFFF;
                border: 2px solid #E7C75F;
                box-shadow: none;
            }

            .ap-day-selected.ap-day-blocked-full,
            .ap-day-selected.ap-day-blocked-partial {
                color: #FFFFFF !important;
                background: linear-gradient(135deg, #691494, #962BC2);
                border-color: transparent;
            }

            .ap-block-dot {
                position: absolute;
                right: 5px;
                bottom: 5px;
                width: 8px;
                height: 8px;
                background: #E4B300;
                border: 1px solid #B58A00;
                border-radius: 999px;
                box-shadow: 0 0 0 2px #FFF8D2;
            }

            .ap-day-selected .ap-block-dot {
                background: #FFD95A;
                border-color: #FFFFFF;
            }

            .ap-today-link {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 100%;
                min-height: 42px;
                margin-top: 11px;
                color: #65158D !important;
                background: #F8EFFC;
                border: 1px solid #E7D5EF;
                border-radius: 13px;
                font-size: 13px;
                font-weight: 800;
                text-decoration: none !important;
                -webkit-tap-highlight-color: transparent;
            }

            @media (max-width: 390px) {
                .ap-mobile-calendar {
                    padding-left: 8px;
                    padding-right: 8px;
                }

                .ap-calendar-grid {
                    gap: 3px;
                }

                .ap-day {
                    min-height: 38px;
                    border-radius: 10px;
                }

                .ap-day-number {
                    font-size: 12px;
                }
            }
        </style>
        """
    )


def mostrar_calendario_movil() -> None:
    mostrar_estilos_calendario_movil()
    mostrar_encabezado_principal()
    st.html(construir_calendario_movil_html())
    mostrar_detalle_dia()


# ============================================================
# DETALLE DEL DÍA
# ============================================================


def obtener_fecha_seleccionada() -> date:
    fecha_iso = st.session_state.fecha_seleccionada

    try:
        return datetime.strptime(fecha_iso, "%Y-%m-%d").date()

    except (TypeError, ValueError):
        hoy = date.today()
        st.session_state.fecha_seleccionada = hoy.isoformat()
        return hoy


def mostrar_encabezado_dia(fecha_seleccionada: date) -> None:
    st.html(
        f"""
        <div class="selected-day-header">
            <div>
                <div class="selected-day-label">
                    Día seleccionado
                </div>

                <div class="selected-day-title">
                    {titulo_fecha(fecha_seleccionada)}
                </div>
            </div>

            <div class="selected-day-date">
                {fecha_seleccionada.strftime("%d/%m/%Y")}
            </div>
        </div>
        """
    )


def mostrar_separador_periodo(titulo: str) -> None:
    st.html(
        f"""
        <div class="ap-period-separator">
            <div class="ap-period-line"></div>

            <div class="ap-period-title">
                {escape(titulo)}
            </div>

            <div class="ap-period-line"></div>
        </div>
        """
    )


def abrir_nueva_reserva(fecha_iso: str, hora: str) -> None:
    st.session_state.nueva_reserva_fecha = fecha_iso
    st.session_state.nueva_reserva_hora = hora
    st.session_state.reserva_seleccionada_id = None
    st.session_state.pantalla_actual = "nueva_reserva"


def abrir_detalle_reserva(reserva_id: int) -> None:
    st.session_state.reserva_seleccionada_id = reserva_id
    st.session_state.nueva_reserva_fecha = None
    st.session_state.nueva_reserva_hora = None
    st.session_state.pantalla_actual = "detalle_reserva"


def mostrar_horario_disponible(fecha_iso: str, hora: str) -> None:
    with st.container(border=True):
        columna_info, columna_estado, columna_boton = st.columns(
            [5.2, 1.3, 2.1],
            vertical_alignment="center",
        )

        with columna_info:
            st.html(
                f"""
                <div class="appointment-card appointment-free">
                    <div class="appointment-hour">{hora}</div>

                    <div class="appointment-information">
                        <div class="appointment-client">
                            Horario disponible
                        </div>

                        <div class="appointment-service">
                            Sin reserva registrada
                        </div>
                    </div>
                </div>
                """
            )

        with columna_estado:
            st.html(
                """
                <div class="appointment-status appointment-status-free">
                    Disponible
                </div>
                """
            )

        with columna_boton:
            if st.button(
                "Agregar reserva",
                key=f"boton_nueva_reserva_{fecha_iso}_{hora}",
                type="primary",
                use_container_width=True,
            ):
                abrir_nueva_reserva(fecha_iso, hora)
                st.rerun()



def mostrar_horario_bloqueado(
    hora: str,
    motivo: str,
) -> None:
    motivo_visible = escape(
        str(motivo or "Horario no disponible")
    )

    with st.container(border=True):
        columna_info, columna_estado = st.columns(
            [6.5, 2.2],
            vertical_alignment="center",
        )

        with columna_info:
            st.html(
                f"""
                <div class="appointment-card" style="
                    background: #FFF8D8;
                    border-left: 5px solid #E2B700;
                    border-radius: 14px;
                    padding: 12px 14px;
                ">
                    <div class="appointment-hour" style="
                        color: #6B5200;
                    ">{escape(hora)}</div>

                    <div class="appointment-information">
                        <div class="appointment-client" style="
                            color: #5F4900;
                        ">
                            Agenda bloqueada
                        </div>

                        <div class="appointment-service" style="
                            color: #7A6416;
                        ">
                            {motivo_visible}
                        </div>
                    </div>
                </div>
                """
            )

        with columna_estado:
            st.html(
                """
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 36px;
                    padding: 7px 8px;
                    color: #6A5000;
                    background: #FFE58A;
                    border: 1px solid #E1BD37;
                    border-radius: 999px;
                    font-size: 11px;
                    font-weight: 850;
                    text-align: center;
                ">
                    Bloqueado
                </div>
                """
            )

def mostrar_reserva_ocupada(reserva: dict) -> None:
    cliente = escape(str(reserva["cliente"]))
    celular = escape(str(reserva["celular"]))
    servicio = escape(str(reserva["servicio"]))
    estado = escape(str(reserva["estado"]))
    hora = escape(str(reserva["hora"]))
    precio = formato_pesos(reserva["precio_base"])

    atendida = str(reserva["estado"]) == "Atendida"

    if atendida:
        estado_financiero = "Pagado"
        fondo_financiero = "#DCFCE7"
        color_financiero = "#166534"
        icono_financiero = "✓"
    elif reserva["abono_pagado"]:
        estado_financiero = "Abono OK · $5.000"
        fondo_financiero = "#EDE9FE"
        color_financiero = "#5B21B6"
        icono_financiero = "$"
    else:
        estado_financiero = "Sin abono"
        fondo_financiero = "#FEE2E2"
        color_financiero = "#991B1B"
        icono_financiero = "!"

    with st.container(border=True):
        columna_info, columna_estado, columna_boton = st.columns(
            [5.4, 1.25, 2.0],
            vertical_alignment="center",
        )

        with columna_info:
            st.html(
                f"""
                <div style="
                    display: grid;
                    grid-template-columns: 66px 1fr;
                    gap: 12px;
                    align-items: start;
                    padding: 3px 0;
                ">
                    <div style="
                        padding: 10px 7px;
                        color: #FFFFFF;
                        background: linear-gradient(
                            145deg,
                            #8A2DAA,
                            #5F167C
                        );
                        border-radius: 14px;
                        font-size: 17px;
                        font-weight: 950;
                        text-align: center;
                        box-shadow: 0 5px 13px rgba(103, 21, 139, 0.18);
                    ">
                        {hora}
                    </div>

                    <div>
                        <div style="
                            color: #37253E;
                            font-size: 16px;
                            font-weight: 900;
                            line-height: 1.25;
                        ">
                            👤 {cliente}
                        </div>

                        <div style="
                            margin-top: 5px;
                            color: #66536D;
                            font-size: 13px;
                            font-weight: 750;
                        ">
                            💅 {servicio} · {precio}
                        </div>

                        <div style="
                            margin-top: 3px;
                            color: #8A768F;
                            font-size: 12px;
                            font-weight: 650;
                        ">
                            📱 {celular}
                        </div>

                        <div style="
                            display: inline-block;
                            margin-top: 8px;
                            padding: 5px 10px;
                            color: {color_financiero};
                            background: {fondo_financiero};
                            border-radius: 999px;
                            font-size: 11px;
                            font-weight: 900;
                        ">
                            {icono_financiero} {estado_financiero}
                        </div>
                    </div>
                </div>
                """
            )

        with columna_estado:
            st.html(
                f"""
                <div style="
                    padding: 7px 8px;
                    color: {'#166534' if atendida else '#6B167F'};
                    background: {'#DCFCE7' if atendida else '#F3E8FF'};
                    border-radius: 999px;
                    font-size: 11px;
                    font-weight: 900;
                    text-align: center;
                ">
                    {estado}
                </div>
                """
            )

        with columna_boton:
            if st.button(
                "Ver reserva",
                key=f"boton_ver_reserva_{reserva['id']}",
                type="primary",
                use_container_width=True,
            ):
                abrir_detalle_reserva(int(reserva["id"]))
                st.rerun()

def mostrar_detalle_dia() -> None:
    fecha_seleccionada = obtener_fecha_seleccionada()
    fecha_iso = fecha_seleccionada.isoformat()

    mostrar_encabezado_dia(fecha_seleccionada)

    if not fecha_es_dia_habil(fecha_seleccionada):
        st.warning(
            "Acrylic Purple atiende de lunes a sábado. "
            "Los domingos el salón permanece cerrado."
        )
        return

    horarios_base = obtener_horarios_del_dia(
        fecha_seleccionada.weekday()
    )
    reservas = cargar_reservas_fecha(fecha_iso)
    bloqueos = obtener_bloqueos_fecha(fecha_iso)
    duracion_minima_reservable = obtener_duracion_minima_reservable()

    if not horarios_base:
        st.warning(
            "No existen horarios configurados para este día."
        )
        return

    bloqueo_completo = next(
        (
            bloqueo
            for bloqueo in bloqueos
            if bloqueo["hora"] is None
        ),
        None,
    )

    bloqueos_por_hora = {
        bloqueo["hora"]: bloqueo
        for bloqueo in bloqueos
        if bloqueo["hora"] is not None
    }

    horas_extra_reservadas = sorted(
        {
            str(reserva["hora"])
            for reserva in reservas
            if str(reserva["hora"]) not in horarios_base
        }
    )

    horarios_visibles = sorted(
        set(horarios_base + horas_extra_reservadas)
    )

    disponibles = 0
    cantidad_bloqueados = 0

    for hora in horarios_base:
        if obtener_reserva_por_hora(reservas, hora) is not None:
            continue

        if bloqueo_completo is not None:
            cantidad_bloqueados += 1
            continue

        if hora in bloqueos_por_hora:
            cantidad_bloqueados += 1
            continue

        if horario_cubierto_por_reserva(
            fecha_iso,
            hora,
            reservas,
        ):
            continue

        if not horario_base_admite_reserva(
            fecha_iso,
            hora,
            reservas,
            duracion_minima_reservable,
        ):
            continue

        disponibles += 1

    ocupados = len(reservas)

    st.html(
        f"""
        <div class="day-summary">
            <div class="day-summary-free">
                {disponibles} disponibles
            </div>

            <div class="day-summary-busy">
                {ocupados} reservados
            </div>

            <div style="
                padding: 8px 12px;
                color: #6A5200;
                background: #FFF1A8;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 800;
            ">
                {cantidad_bloqueados} bloqueados
            </div>
        </div>
        """
    )

    mostrar_separador_periodo("Horarios del día")

    for hora in horarios_visibles:
        reserva = obtener_reserva_por_hora(reservas, hora)

        if reserva is not None:
            mostrar_reserva_ocupada(reserva)
            continue

        # Las horas extraordinarias solo se muestran si tienen reserva.
        if hora not in horarios_base:
            continue

        if bloqueo_completo is not None:
            mostrar_horario_bloqueado(
                hora=hora,
                motivo=bloqueo_completo["motivo"],
            )
            continue

        bloqueo_hora = bloqueos_por_hora.get(hora)

        if bloqueo_hora is not None:
            mostrar_horario_bloqueado(
                hora=hora,
                motivo=bloqueo_hora["motivo"],
            )
            continue

        # Si otra atención cubre este horario, no se muestra como
        # disponible para evitar una agenda visualmente engañosa.
        if horario_cubierto_por_reserva(
            fecha_iso,
            hora,
            reservas,
        ):
            continue

        # Además de no estar dentro de otra atención, debe existir
        # espacio suficiente para al menos el servicio activo más corto.
        if not horario_base_admite_reserva(
            fecha_iso,
            hora,
            reservas,
            duracion_minima_reservable,
        ):
            continue

        mostrar_horario_disponible(fecha_iso, hora)

    st.divider()

    st.html(
        """
        <div style="
            margin-top: 4px;
            color: #594A60;
            font-size: 12px;
            font-weight: 700;
        ">
            ¿Necesitas reservar fuera de los horarios habituales?
        </div>
        """
    )

    with st.expander("＋ Agregar horario excepcional"):
        st.caption(
            "Permite crear una atención fuera del horario normal. "
            "Agenda PRO comprobará automáticamente que no exista cruce."
        )

        hora_extra_objeto = st.time_input(
            "Hora acordada con la clienta",
            value=time(12, 0),
            step=1800,
            key=f"hora_extra_{fecha_iso}",
        )
        hora_extra = hora_extra_objeto.strftime("%H:%M")

        hora_ocupada = hora_extra_esta_ocupada(
            fecha_iso,
            hora_extra,
            reservas,
        )

        if hora_ocupada:
            st.warning(
                "Ese horario cae dentro de una atención existente "
                "o de su margen de preparación."
            )

        if st.button(
            "Continuar con la reserva",
            type="primary",
            use_container_width=True,
            disabled=hora_ocupada or bloqueo_completo is not None,
            key=f"continuar_hora_extra_{fecha_iso}",
        ):
            abrir_nueva_reserva(fecha_iso, hora_extra)
            st.rerun()


# ============================================================
# RETORNO VISUAL AL INICIO DEL CALENDARIO
# ============================================================


def forzar_scroll_inicio_calendario() -> None:
    """
    Lleva la pantalla al inicio real de la aplicación después de
    volver desde una reserva. Se ejecuta una sola vez por acción.
    """

    debe_subir = st.session_state.pop(
        "forzar_scroll_calendario",
        False,
    )

    if not debe_subir:
        return

    components.html(
        """
        <script>
        (function () {
            function subirAlInicio() {
                try {
                    const padre = window.parent;
                    const documento = padre.document;

                    padre.scrollTo({
                        top: 0,
                        left: 0,
                        behavior: "auto"
                    });

                    const contenedorApp = documento.querySelector(
                        '[data-testid="stAppViewContainer"]'
                    );

                    if (contenedorApp) {
                        contenedorApp.scrollTo({
                            top: 0,
                            left: 0,
                            behavior: "auto"
                        });
                    }

                    const seccionPrincipal = documento.querySelector(
                        'section.main'
                    );

                    if (seccionPrincipal) {
                        seccionPrincipal.scrollTo({
                            top: 0,
                            left: 0,
                            behavior: "auto"
                        });
                    }

                    documento.documentElement.scrollTop = 0;
                    documento.body.scrollTop = 0;
                } catch (error) {
                    console.log(
                        "Agenda PRO: no fue posible ajustar el scroll.",
                        error
                    );
                }
            }

            subirAlInicio();
            setTimeout(subirAlInicio, 80);
            setTimeout(subirAlInicio, 250);
            setTimeout(subirAlInicio, 500);
        })();
        </script>
        """,
        height=0,
        width=0,
    )


# ============================================================
# MENSAJE TEMPORAL DE NAVEGACIÓN
# ============================================================


def mostrar_mensaje_agenda() -> None:
    mensaje = st.session_state.pop(
        "mensaje_agenda",
        None,
    )

    if not mensaje:
        return

    texto = str(mensaje.get("texto", ""))
    tipo = str(mensaje.get("tipo", "success"))

    if tipo == "error":
        st.error(texto, icon="❌")
    elif tipo == "warning":
        st.warning(texto, icon="⚠️")
    elif tipo == "info":
        st.info(texto, icon="ℹ️")
    else:
        st.success(texto, icon="✅")


# ============================================================
# PANTALLA PRINCIPAL
# ============================================================


def mostrar_calendario() -> None:
    inicializar_estado_calendario()
    mostrar_estilos_normalizacion_visual()
    mostrar_estilos_encabezado_logo()
    forzar_scroll_inicio_calendario()
    mostrar_mensaje_agenda()

    if es_dispositivo_movil():
        mostrar_calendario_movil()
        return

    mostrar_encabezado_principal()
    mostrar_navegacion_mes()
    mostrar_grilla_mes()
    mostrar_detalle_dia()