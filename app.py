import streamlit as st
import streamlit.components.v1 as components
from streamlit_cookies_manager import EncryptedCookieManager
from usuarios import USUARIOS

from config import (
    PAGE_TITLE,
    PAGE_ICON,
    preparar_directorios,
)
from database.database import crear_base_de_datos
from utils.respaldos import crear_respaldo_diario
from modules.calendario import (
    inicializar_estado_calendario,
    mostrar_calendario,
)
from modules.reservas import (
    mostrar_detalle_reserva,
    mostrar_editar_reserva,
    mostrar_nueva_reserva,
)
from modules.servicios import mostrar_servicios
from modules.bloqueos import mostrar_bloqueos
from modules.estadisticas import mostrar_estadisticas


# ============================================================
# AGENDA PRO — ACRYLIC PURPLE
# ============================================================


st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)
cookies = EncryptedCookieManager(
    prefix="agenda_pro_acrylic_purple/",
    password="AGENDA_PRO_COOKIE_2026_SEGURA",
)

if not cookies.ready():
    st.stop()

@st.cache_resource
def inicializar_sistema() -> dict:
    preparar_directorios()
    crear_base_de_datos()

    # El respaldo se ejecuta después de crear o verificar la base.
    # Si ocurre un error, Agenda PRO igualmente continúa funcionando.
    return crear_respaldo_diario()


estado_respaldo = inicializar_sistema()


# ============================================================
# ESTILOS GENERALES
# ============================================================


st.html(
    """
    <style>
        #MainMenu,
        footer,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {
            display: none !important;
        }

        header {
            background: transparent !important;
        }

        .stApp {
            background:
                linear-gradient(
                    180deg,
                    #F9F3FC 0%,
                    #FFFFFF 36%,
                    #FFFFFF 100%
                );
        }

        .block-container {
            max-width: 1050px;
            padding-top: 0.9rem;
            padding-bottom: 4rem;
        }

        .calendar-main-header,
        .reservation-screen-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 18px;
            margin-bottom: 14px;
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid #E9DDEE;
            border-radius: 20px;
            box-shadow: 0 7px 24px rgba(85, 26, 112, 0.08);
        }

        .calendar-app-name,
        .reservation-screen-title {
            color: #61158A;
            font-size: 23px;
            font-weight: 850;
            line-height: 1.05;
        }

        .calendar-salon-name,
        .reservation-screen-subtitle {
            margin-top: 4px;
            color: #7D7283;
            font-size: 13px;
            font-weight: 600;
        }

        .calendar-main-icon,
        .reservation-screen-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 43px;
            height: 43px;
            background: #F0D9FC;
            border-radius: 14px;
            font-size: 23px;
        }

        .calendar-month-title {
            color: #392D40;
            font-size: 27px;
            font-weight: 850;
            text-align: center;
        }

        .calendar-weekday {
            padding: 10px 2px 7px 2px;
            color: #665A6D;
            font-size: 12px;
            font-weight: 800;
            text-align: center;
            text-transform: uppercase;
        }

        .calendar-weekend-name {
            color: #A59DA9;
        }

        .calendar-empty-day {
            min-height: 66px;
        }

        div[data-testid="stButton"] > button {
            min-height: 48px;
            border-radius: 14px;
            font-weight: 750;
        }

        button[kind="primary"] {
            background:
                linear-gradient(
                    135deg,
                    #691494,
                    #962BC2
                ) !important;
            border: none !important;
        }

        button[kind="secondary"] {
            color: #4C4052 !important;
            background: white !important;
            border: 1px solid #E8DFEB !important;
        }

        button:disabled {
            color: #B9B2BD !important;
            background: #F7F4F8 !important;
            border: 1px solid #EEE9F0 !important;
            opacity: 1 !important;
        }

        .selected-day-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 19px 21px;
            margin-top: 28px;
            margin-bottom: 14px;
            background:
                linear-gradient(
                    135deg,
                    #681391,
                    #9D35C8
                );
            border-radius: 20px;
            box-shadow: 0 10px 24px rgba(94, 22, 128, 0.18);
        }

        .selected-day-label {
            color: rgba(255, 255, 255, 0.72);
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
        }

        .selected-day-title {
            margin-top: 4px;
            color: white;
            font-size: 21px;
            font-weight: 850;
        }

        .selected-day-date {
            padding: 8px 11px;
            color: white;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            font-size: 12px;
            font-weight: 750;
        }

        .day-summary {
            display: flex;
            gap: 10px;
            margin-bottom: 8px;
            flex-wrap: wrap;
        }

        .day-summary-free,
        .day-summary-busy {
            padding: 7px 11px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 800;
        }

        .day-summary-free {
            background: #D7F2E0;
            color: #16713A;
        }

        .day-summary-busy {
            background: #EAD2F7;
            color: #641083;
        }

        .appointment-card {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 17px 18px;
            margin-top: 12px;
            background: white;
            border-radius: 18px;
            box-shadow: 0 5px 18px rgba(63, 32, 76, 0.06);
        }

        .appointment-free {
            border: 1px solid #E7DCEC;
        }

        .appointment-busy {
            border: 1px solid #D8C0E5;
            background: #FCF7FF;
        }

        .appointment-hour {
            min-width: 60px;
            color: #65168D;
            font-size: 18px;
            font-weight: 850;
        }

        .appointment-information {
            flex: 1;
        }

        .appointment-client {
            color: #332B38;
            font-size: 15px;
            font-weight: 800;
        }

        .appointment-service,
        .appointment-phone {
            margin-top: 4px;
            color: #817887;
            font-size: 12px;
        }

        .appointment-status {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 48px;
            padding: 7px 12px;
            color: #FFFFFF;
            background: #74139A;
            border-radius: 14px;
            font-size: 11px;
            font-weight: 800;
        }

        .appointment-status-free {
            color: #FFFFFF;
            background: #218A4B;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            margin-top: 12px;
            border-color: #E1D1E8 !important;
            border-radius: 18px !important;
            box-shadow: 0 5px 18px rgba(63, 32, 76, 0.05);
        }

        .reservation-date-card,
        .reservation-detail-card {
            padding: 20px;
            margin-bottom: 18px;
            background: white;
            border: 1px solid #E8DEEC;
            border-radius: 20px;
            box-shadow: 0 6px 20px rgba(68, 34, 86, 0.06);
        }

        .reservation-date-label,
        .reservation-detail-label,
        .service-selected-label {
            color: #817688;
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
        }

        .reservation-date-value {
            margin-top: 6px;
            color: #332A38;
            font-size: 17px;
            font-weight: 800;
        }

        .reservation-time-value {
            margin-top: 5px;
            color: #6A168F;
            font-size: 25px;
            font-weight: 900;
        }

        .form-section-title {
            margin-top: 12px;
            margin-bottom: 8px;
            color: #4B3B52;
            font-size: 17px;
            font-weight: 850;
        }

        .service-selected-card {
            display: flex;
            justify-content: space-between;
            gap: 20px;
            padding: 16px;
            margin-top: 8px;
            background: #F9F2FC;
            border: 1px solid #E9D9F0;
            border-radius: 16px;
        }

        .service-selected-price,
        .service-selected-duration {
            margin-top: 5px;
            color: #67168D;
            font-size: 18px;
            font-weight: 850;
        }

        .base-price-note {
            margin-top: 8px;
            margin-bottom: 14px;
            color: #817688;
            font-size: 12px;
        }

        .reservation-detail-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .reservation-detail-hour {
            color: #65158D;
            font-size: 30px;
            font-weight: 900;
        }

        .reservation-detail-date,
        .reservation-detail-secondary {
            margin-top: 4px;
            color: #807685;
            font-size: 13px;
        }

        .reservation-detail-divider {
            height: 1px;
            margin: 18px 0;
            background: #EEE7F0;
        }

        .reservation-detail-value {
            margin-top: 5px;
            color: #332B38;
            font-size: 17px;
            font-weight: 800;
        }

        .reservation-observation {
            margin-top: 7px;
            padding: 13px;
            color: #5B505F;
            background: #F8F4F9;
            border-radius: 13px;
            font-size: 14px;
            line-height: 1.5;
        }

        .reservation-state {
            padding: 8px 11px;
            color: #6B188F;
            background: #F0DDF8;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 850;
        }

        @media (max-width: 700px) {
            .block-container {
                padding-top: 0.45rem;
                padding-left: 0.45rem;
                padding-right: 0.45rem;
            }

            .calendar-month-title {
                font-size: 21px;
            }

            .calendar-weekday {
                font-size: 10px;
            }

            .calendar-empty-day {
                min-height: 50px;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.22rem;
            }

            div[data-testid="stButton"] > button {
                min-height: 51px;
                padding-left: 2px;
                padding-right: 2px;
                border-radius: 11px;
                font-size: 12px;
            }

            .service-selected-card {
                flex-direction: column;
                gap: 12px;
            }
        }

        /* ==================================================
           AJUSTES RESPONSIVE — CELULAR Y TABLET
           ================================================== */

        html {
            -webkit-text-size-adjust: 100%;
        }

        input,
        textarea,
        select,
        button {
            font-size: 16px;
        }

        div[data-testid="stForm"] {
            width: 100%;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stSelectbox"] > div,
        div[data-testid="stDateInput"] input {
            width: 100%;
            min-height: 46px;
            border-radius: 12px;
        }

        @media (min-width: 701px) and (max-width: 1100px) {
            .block-container {
                max-width: 940px;
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .calendar-month-title {
                font-size: 25px;
            }

            .appointment-card {
                padding: 15px 16px;
            }
        }

        @media (max-width: 700px) {
            .block-container {
                width: 100%;
                max-width: 100%;
                padding-top: 0.35rem;
                padding-left: 0.4rem;
                padding-right: 0.4rem;
                padding-bottom: 2.5rem;
            }

            .calendar-main-header,
            .reservation-screen-header {
                padding: 12px 14px;
                margin-bottom: 10px;
                border-radius: 16px;
            }

            .calendar-app-name,
            .reservation-screen-title {
                font-size: 20px;
            }

            .calendar-salon-name,
            .reservation-screen-subtitle {
                font-size: 12px;
            }

            .calendar-main-icon,
            .reservation-screen-icon {
                width: 39px;
                height: 39px;
                border-radius: 12px;
                font-size: 21px;
            }

            .calendar-month-title {
                font-size: 19px;
                line-height: 1.15;
                padding-top: 9px;
            }

            .calendar-weekday {
                padding: 7px 0 5px;
                font-size: 9px;
                letter-spacing: 0;
            }

            .calendar-empty-day {
                min-height: 46px;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.18rem;
            }

            div[data-testid="stButton"] > button {
                min-height: 48px;
                padding: 0.25rem 0.15rem;
                border-radius: 10px;
                font-size: 11px;
                line-height: 1.05;
                touch-action: manipulation;
            }

            .selected-day-header {
                align-items: flex-start;
                padding: 15px 16px;
                margin-top: 20px;
                margin-bottom: 12px;
                border-radius: 16px;
            }

            .selected-day-title {
                font-size: 18px;
            }

            .selected-day-date {
                padding: 6px 8px;
                font-size: 10px;
                white-space: nowrap;
            }

            .day-summary {
                gap: 7px;
                margin-bottom: 4px;
            }

            .day-summary-free,
            .day-summary-busy {
                padding: 6px 9px;
                font-size: 11px;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                border-radius: 15px;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] > div {
                padding: 0.55rem 0.6rem;
            }

            .appointment-card {
                gap: 9px;
                padding: 5px 0;
                margin-top: 0;
                border: 0;
                box-shadow: none;
                background: transparent;
            }

            .appointment-hour {
                min-width: 48px;
                font-size: 16px;
            }

            .appointment-client {
                font-size: 13px;
            }

            .appointment-service,
            .appointment-phone {
                margin-top: 2px;
                font-size: 10px;
                line-height: 1.25;
            }

            .appointment-status {
                padding: 6px 7px;
                font-size: 9px;
                white-space: nowrap;
            }

            .reservation-date-card,
            .reservation-detail-card {
                padding: 16px;
                margin-bottom: 14px;
                border-radius: 16px;
            }

            .reservation-date-value {
                font-size: 15px;
            }

            .reservation-time-value {
                font-size: 22px;
            }

            .form-section-title {
                font-size: 16px;
            }

            .service-selected-card {
                flex-direction: column;
                gap: 12px;
                padding: 14px;
            }

            .reservation-detail-top {
                align-items: flex-start;
                gap: 10px;
            }

            .reservation-detail-hour {
                font-size: 26px;
            }

            .reservation-detail-value {
                font-size: 15px;
            }

            div[data-testid="stFormSubmitButton"] button {
                min-height: 50px;
                font-size: 14px;
            }

            input,
            textarea,
            select,
            button {
                font-size: 16px;
            }
        }

        /* ==================================================
           MENÚ LATERAL
           ================================================== */

        section[data-testid="stSidebar"] {
            background:
                linear-gradient(
                    180deg,
                    #F4E7FA 0%,
                    #FFFFFF 55%,
                    #FFFFFF 100%
                );
            border-right: 1px solid #E8D9EF;
        }

        section[data-testid="stSidebar"] .block-container {
            padding-top: 1.2rem;
        }

        .sidebar-brand {
            padding: 16px;
            margin-bottom: 14px;
            background: white;
            border: 1px solid #E6D7ED;
            border-radius: 18px;
            box-shadow: 0 6px 18px rgba(77, 30, 98, 0.07);
        }

        .sidebar-brand-title {
            color: #62148B;
            font-size: 20px;
            font-weight: 900;
        }

        .sidebar-brand-subtitle {
            margin-top: 4px;
            color: #7D7283;
            font-size: 12px;
            font-weight: 650;
        }

        @media (max-width: 420px) {
            .calendar-month-title {
                font-size: 17px;
            }

            .calendar-weekday {
                font-size: 8px;
            }

            div[data-testid="stButton"] > button {
                min-height: 45px;
                font-size: 10px;
            }

            .selected-day-title {
                font-size: 16px;
            }

            .appointment-hour {
                min-width: 42px;
                font-size: 15px;
            }

            .appointment-status {
                display: none;
            }
        }

        /* ==================================================
           INICIO DE SESIÓN
           ================================================== */

        .login-wrapper {
            max-width: 430px;
            margin: 7vh auto 0 auto;
            padding: 28px;
            background: rgba(255, 255, 255, 0.97);
            border: 1px solid #E6D7ED;
            border-radius: 24px;
            box-shadow: 0 12px 34px rgba(85, 26, 112, 0.12);
        }

        .login-logo {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 62px;
            height: 62px;
            margin: 0 auto 15px auto;
            background: #F0D9FC;
            border-radius: 19px;
            font-size: 31px;
        }

        .login-title {
            color: #61158A;
            font-size: 27px;
            font-weight: 900;
            text-align: center;
        }

        .login-subtitle {
            margin-top: 7px;
            margin-bottom: 22px;
            color: #7D7283;
            font-size: 14px;
            font-weight: 600;
            text-align: center;
        }

        .login-footer {
            margin-top: 17px;
            color: #9A919E;
            font-size: 11px;
            text-align: center;
        }

        @media (max-width: 700px) {
            .login-wrapper {
                margin-top: 3vh;
                padding: 22px 18px;
                border-radius: 19px;
            }

            .login-title {
                font-size: 23px;
            }
        }


        /* Botón principal para regresar a la agenda */
        div[data-testid="stButton"]:has(
            button[kind="primary"] p
        ) button {
            font-weight: 850;
        }

    </style>
    """
)




# ============================================================
# AUTENTICACIÓN
# ============================================================


def cerrar_sesion() -> None:
    cookies["autenticado"] = "0"
    cookies.pop("usuario_actual", None)
    cookies.pop("nombre_usuario", None)
    cookies.save()

    st.session_state["autenticado"] = False
    st.session_state.pop("usuario_actual", None)
    st.session_state.pop("nombre_usuario", None)
    st.session_state["vista_principal"] = "calendario"
    st.session_state["pantalla_actual"] = "calendario"

def validar_acceso(usuario: str, password: str) -> bool:
    usuario_normalizado = usuario.strip().lower()
    datos_usuario = USUARIOS.get(usuario_normalizado)

    if datos_usuario is None:
        return False

    if str(datos_usuario.get("password", "")) != password:
        return False

    nombre_usuario = datos_usuario.get(
        "nombre",
        usuario_normalizado.title(),
    )

    st.session_state["autenticado"] = True
    st.session_state["usuario_actual"] = usuario_normalizado
    st.session_state["nombre_usuario"] = nombre_usuario

    cookies["autenticado"] = "1"
    cookies["usuario_actual"] = usuario_normalizado
    cookies["nombre_usuario"] = nombre_usuario
    cookies.save()

    return True


def mostrar_inicio_sesion() -> None:
    st.markdown(
        """
        <div class="login-wrapper">
            <div class="login-logo">💅</div>
            <div class="login-title">Agenda PRO</div>
            <div class="login-subtitle">
                Acrylic Purple · Acceso privado
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    columna_izquierda, columna_centro, columna_derecha = st.columns(
        [1, 2.2, 1]
    )

    with columna_centro:
        with st.form("formulario_inicio_sesion", clear_on_submit=False):
            usuario = st.text_input(
                "Usuario",
                placeholder="Ingresa tu usuario",
                autocomplete="username",
            )

            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="Ingresa tu contraseña",
                autocomplete="current-password",
            )

            ingresar = st.form_submit_button(
                "INGRESAR",
                use_container_width=True,
                type="primary",
            )

        if ingresar:
            if validar_acceso(usuario, password):
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

        st.markdown(
            '<div class="login-footer">Acceso exclusivo de Acrylic Purple</div>',
            unsafe_allow_html=True,
        )


if "autenticado" not in st.session_state:
    autenticado_cookie = cookies.get("autenticado") == "1"

    st.session_state["autenticado"] = autenticado_cookie

    if autenticado_cookie:
        st.session_state["usuario_actual"] = cookies.get(
            "usuario_actual",
            "",
        )
        st.session_state["nombre_usuario"] = cookies.get(
            "nombre_usuario",
            "Usuario",
        )


if not st.session_state["autenticado"]:
    mostrar_inicio_sesion()
    st.stop()


inicializar_estado_calendario()


with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">Agenda PRO</div>
            <div class="sidebar-brand-subtitle">
                Sesión: {st.session_state.get("nombre_usuario", "Usuario")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.button(
        "🚪 Cerrar sesión",
        key="cerrar_sesion_agenda",
        use_container_width=True,
        on_click=cerrar_sesion,
    )



# ============================================================
# NAVEGACIÓN PRINCIPAL
# ============================================================


def cambiar_vista_principal(nombre_vista: str) -> None:
    """
    Cambia entre Calendario, Servicios y Bloqueos.

    Se utiliza una clave propia que no es modificada por los módulos
    del calendario ni de reservas.
    """

    st.session_state["vista_principal"] = nombre_vista


def mostrar_menu_inferior() -> None:
    """
    Muestra los accesos administrativos después del calendario,
    los horarios y las reservas del día.
    """

    st.divider()

    st.markdown("### Administración")

    st.caption(
        "Configura y revisa otras áreas de Acrylic Purple."
    )

    fila_1_columna_1, fila_1_columna_2 = st.columns(2)

    with fila_1_columna_1:
        st.button(
            "💅 Servicios",
            key="menu_inferior_servicios",
            use_container_width=True,
            type="primary",
            on_click=cambiar_vista_principal,
            args=("servicios",),
        )

    with fila_1_columna_2:
        st.button(
            "🔒 Bloquear agenda",
            key="menu_inferior_bloqueos",
            use_container_width=True,
            type="primary",
            on_click=cambiar_vista_principal,
            args=("bloqueos",),
        )

    fila_2_columna_1, fila_2_columna_2 = st.columns(2)

    with fila_2_columna_1:
        st.button(
            "👩 Clientas",
            key="menu_inferior_clientas",
            use_container_width=True,
            disabled=True,
        )

    with fila_2_columna_2:
        st.button(
            "📊 Estadísticas",
            key="menu_inferior_estadisticas",
            use_container_width=True,
            type="primary",
            on_click=cambiar_vista_principal,
            args=("estadisticas",),
        )

    st.caption(
        "El registro de clientas se habilitará "
        "en una próxima etapa."
    )


def subir_pagina_al_inicio() -> None:
    """
    Lleva la ventana principal al inicio sin cubrir otros elementos.

    El iframe se crea con un tamaño mínimo y sin interacción del ratón,
    y se coloca después del contenido de Servicios.
    """

    components.html(
        """
        <style>
            html, body {
                width: 1px !important;
                height: 1px !important;
                margin: 0 !important;
                padding: 0 !important;
                overflow: hidden !important;
                pointer-events: none !important;
            }
        </style>
        <script>
            setTimeout(function () {
                window.parent.scrollTo(0, 0);
            }, 80);
        </script>
        """,
        width=1,
        height=1,
    )


# ============================================================
# ESTADO INICIAL DE NAVEGACIÓN
# ============================================================

if "vista_principal" not in st.session_state:
    st.session_state["vista_principal"] = "calendario"


# La navegación de reservas conserva su clave histórica.
pantalla_reserva = st.session_state.get(
    "pantalla_actual",
    "calendario",
)


# ============================================================
# RESOLUCIÓN DE LA PANTALLA
# ============================================================

if pantalla_reserva == "nueva_reserva":
    mostrar_nueva_reserva()

elif pantalla_reserva == "detalle_reserva":
    mostrar_detalle_reserva()

elif pantalla_reserva == "editar_reserva":
    mostrar_editar_reserva()

else:
    # Cuando no hay una reserva abierta, se normaliza únicamente
    # la navegación de reservas. La vista principal permanece aparte.
    st.session_state["pantalla_actual"] = "calendario"

    vista_principal = st.session_state.get(
        "vista_principal",
        "calendario",
    )

    if vista_principal == "servicios":
        mostrar_servicios()

        st.divider()

        st.button(
            "🏠 CONTINUAR EN LA AGENDA",
            key="volver_desde_servicios",
            use_container_width=True,
            type="primary",
            on_click=cambiar_vista_principal,
            args=("calendario",),
        )

        subir_pagina_al_inicio()

    elif vista_principal == "bloqueos":
        mostrar_bloqueos()

        st.divider()

        st.button(
            "🏠 CONTINUAR EN LA AGENDA",
            key="volver_desde_bloqueos",
            use_container_width=True,
            type="primary",
            on_click=cambiar_vista_principal,
            args=("calendario",),
        )

        subir_pagina_al_inicio()

    elif vista_principal == "estadisticas":
        mostrar_estadisticas()

        st.divider()

        st.button(
            "🏠 CONTINUAR EN LA AGENDA",
            key="volver_desde_estadisticas",
            use_container_width=True,
            type="primary",
            on_click=cambiar_vista_principal,
            args=("calendario",),
        )

        subir_pagina_al_inicio()

    else:
        # Cualquier valor inesperado regresa al calendario.
        st.session_state["vista_principal"] = "calendario"
        mostrar_calendario()
        mostrar_menu_inferior()