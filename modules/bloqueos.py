from datetime import date, datetime
from html import escape

import streamlit as st

from database.database import (
    desactivar_bloqueo,
    listar_bloqueos_activos,
    obtener_horarios_del_dia,
    registrar_bloqueo,
)


# ============================================================
# AGENDA PRO — BLOQUEOS DE AGENDA
# ============================================================


MESES_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}

DIAS_ES = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


def fecha_en_espanol(fecha_iso: str) -> str:
    try:
        fecha_objeto = datetime.strptime(
            fecha_iso,
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        return str(fecha_iso)

    return (
        f"{DIAS_ES[fecha_objeto.weekday()]} "
        f"{fecha_objeto.day} de "
        f"{MESES_ES[fecha_objeto.month]} de "
        f"{fecha_objeto.year}"
    )


def mostrar_encabezado() -> None:
    st.html(
        """
        <div style="
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 18px;
            padding: 19px 20px;
            background: linear-gradient(135deg, #FFF5C8, #FFFDF4);
            border: 1px solid #ECD36B;
            border-radius: 20px;
            box-shadow: 0 8px 24px rgba(112, 82, 0, 0.08);
        ">
            <div>
                <div style="
                    color: #725600;
                    font-size: 24px;
                    font-weight: 900;
                ">
                    Bloquear agenda
                </div>

                <div style="
                    margin-top: 3px;
                    color: #796B38;
                    font-size: 13px;
                    font-weight: 600;
                ">
                    Define días u horarios en que no atenderás
                </div>
            </div>

            <div style="
                display: flex;
                align-items: center;
                justify-content: center;
                width: 54px;
                height: 54px;
                background: #FFE37B;
                border-radius: 16px;
                font-size: 27px;
            ">
                🔒
            </div>
        </div>
        """
    )


def mostrar_formulario_bloqueo() -> None:
    st.markdown("### Nuevo bloqueo")

    fecha_seleccionada = st.date_input(
        "Fecha que deseas bloquear",
        value=date.today(),
        min_value=date.today(),
        format="DD/MM/YYYY",
        key="bloqueo_fecha",
    )

    if fecha_seleccionada.weekday() == 6:
        st.info(
            "Los domingos ya aparecen cerrados en la agenda."
        )
        return

    tipo = st.radio(
        "¿Qué deseas bloquear?",
        options=[
            "Día completo",
            "Un horario específico",
        ],
        horizontal=True,
        key="bloqueo_tipo",
    )

    horarios = obtener_horarios_del_dia(
        fecha_seleccionada.weekday()
    )

    hora_seleccionada = None

    if tipo == "Un horario específico":
        if not horarios:
            st.warning(
                "No existen horarios configurados para esta fecha."
            )
            return

        hora_seleccionada = st.selectbox(
            "Horario",
            options=horarios,
            key="bloqueo_hora",
        )

    motivos = [
        "No atenderé",
        "Vacaciones",
        "Trámite",
        "Feriado",
        "Otro",
    ]

    motivo_base = st.selectbox(
        "Motivo",
        options=motivos,
        key="bloqueo_motivo_base",
    )

    motivo_final = motivo_base

    if motivo_base == "Otro":
        motivo_final = st.text_input(
            "Escribe el motivo",
            max_chars=120,
            key="bloqueo_motivo_otro",
        ).strip()

    if tipo == "Día completo":
        st.warning(
            "El día completo solo podrá bloquearse si no tiene "
            "reservas activas."
        )
    else:
        st.info(
            "El horario solo podrá bloquearse si no tiene "
            "una reserva activa."
        )

    if st.button(
        "🔒 Guardar bloqueo",
        key="guardar_bloqueo",
        type="primary",
        use_container_width=True,
    ):
        if not motivo_final:
            st.error("Debes escribir un motivo.")
            return

        exito, mensaje = registrar_bloqueo(
            fecha_iso=fecha_seleccionada.isoformat(),
            hora=(
                None
                if tipo == "Día completo"
                else hora_seleccionada
            ),
            motivo=motivo_final,
        )

        if exito:
            st.success(mensaje)
            st.session_state.fecha_seleccionada = (
                fecha_seleccionada.isoformat()
            )
            st.rerun()
        else:
            st.error(mensaje)


def mostrar_bloqueos_vigentes() -> None:
    st.divider()
    st.markdown("### Bloqueos vigentes")

    bloqueos = listar_bloqueos_activos(
        date.today().isoformat()
    )

    if not bloqueos:
        st.success(
            "No existen bloqueos vigentes. "
            "Todos los horarios configurados están disponibles."
        )
        return

    for bloqueo in bloqueos:
        fecha_texto = fecha_en_espanol(
            bloqueo["fecha"]
        )
        hora = bloqueo["hora"]
        motivo = escape(
            str(bloqueo["motivo"] or "Sin motivo")
        )

        if hora is None:
            alcance = "Día completo"
            icono = "📅"
        else:
            alcance = f"{hora} hrs."
            icono = "🕒"

        with st.container(border=True):
            columna_info, columna_boton = st.columns(
                [4.8, 1.7],
                vertical_alignment="center",
            )

            with columna_info:
                st.html(
                    f"""
                    <div style="
                        display: flex;
                        align-items: flex-start;
                        gap: 12px;
                        padding: 4px 2px;
                    ">
                        <div style="
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            flex: 0 0 42px;
                            width: 42px;
                            height: 42px;
                            background: #FFF0A8;
                            border-radius: 13px;
                            font-size: 20px;
                        ">
                            {icono}
                        </div>

                        <div>
                            <div style="
                                color: #4C3B00;
                                font-size: 15px;
                                font-weight: 850;
                            ">
                                {escape(fecha_texto)}
                            </div>

                            <div style="
                                margin-top: 2px;
                                color: #7B6200;
                                font-size: 13px;
                                font-weight: 750;
                            ">
                                {escape(alcance)} · {motivo}
                            </div>
                        </div>
                    </div>
                    """
                )

            with columna_boton:
                if st.button(
                    "Desbloquear",
                    key=f"desbloquear_{bloqueo['id']}",
                    use_container_width=True,
                ):
                    exito, mensaje = desactivar_bloqueo(
                        int(bloqueo["id"])
                    )

                    if exito:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.error(mensaje)


def mostrar_bloqueos() -> None:
    mostrar_encabezado()
    mostrar_formulario_bloqueo()
    mostrar_bloqueos_vigentes()