import streamlit as st

from config import (
    PAGE_TITLE,
    PAGE_ICON,
    preparar_directorios,
)
from database.database import crear_base_de_datos
from modules.calendario import (
    inicializar_estado_calendario,
    mostrar_calendario,
)
from modules.reservas import (
    mostrar_detalle_reserva,
    mostrar_editar_reserva,
    mostrar_nueva_reserva,
)


# ============================================================
# AGENDA PRO — ACRYLIC PURPLE
# ============================================================


st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def inicializar_sistema() -> bool:
    preparar_directorios()
    crear_base_de_datos()

    return True


inicializar_sistema()
inicializar_estado_calendario()


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
    </style>
    """
)


# ============================================================
# NAVEGACIÓN
# ============================================================


pantalla = st.session_state.get(
    "pantalla_actual",
    "calendario",
)


if pantalla == "nueva_reserva":
    mostrar_nueva_reserva()

elif pantalla == "detalle_reserva":
    mostrar_detalle_reserva()

elif pantalla == "editar_reserva":
    mostrar_editar_reserva()

else:
    mostrar_calendario()