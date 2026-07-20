import calendar
from datetime import date, datetime
from html import escape

import streamlit as st

from database.database import conectar, obtener_horarios_del_dia


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


DIAS_SEMANA = [
    "Lun",
    "Mar",
    "Mié",
    "Jue",
    "Vie",
    "Sáb",
    "Dom",
]


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


def sumar_mes(
    anio: int,
    mes: int,
    cantidad: int,
) -> tuple[int, int]:
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
    nombre_dia = NOMBRES_DIAS[
        fecha_seleccionada.weekday()
    ]

    nombre_mes_fecha = MESES_ES[
        fecha_seleccionada.month
    ].lower()

    return (
        f"{nombre_dia} "
        f"{fecha_seleccionada.day} de "
        f"{nombre_mes_fecha}"
    )


def fecha_es_dia_habil(
    fecha_seleccionada: date,
) -> bool:
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


def cargar_resumen_reservas_mes(
    anio: int,
    mes: int,
) -> dict[str, int]:
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
            (
                primer_dia.isoformat(),
                siguiente_mes.isoformat(),
            ),
        ).fetchall()

        return {
            fila["fecha"]: int(fila["cantidad"])
            for fila in filas
        }

    finally:
        conexion.close()


def cargar_reservas_fecha(
    fecha_iso: str,
) -> list[dict]:
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


# ============================================================
# ENCABEZADO
# ============================================================


def mostrar_encabezado_principal() -> None:
    st.html(
        """
        <div class="calendar-main-header">
            <div>
                <div class="calendar-app-name">
                    Agenda PRO
                </div>

                <div class="calendar-salon-name">
                    Acrylic Purple
                </div>
            </div>

            <div class="calendar-main-icon">
                💅
            </div>
        </div>
        """
    )


def mostrar_navegacion_mes() -> None:
    anio = st.session_state.calendario_anio
    mes = st.session_state.calendario_mes

    columna_anterior, columna_titulo, columna_siguiente = (
        st.columns([1, 5, 1])
    )

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
            f"""
            <div class="calendar-month-title">
                {nombre_mes(anio, mes)}
            </div>
            """
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

    for indice, nombre_dia in enumerate(
        DIAS_SEMANA
    ):
        clase = "calendar-weekday"

        if indice == 6:
            clase += " calendar-weekend-name"

        with columnas[indice]:
            st.html(
                f"""
                <div class="{clase}">
                    {nombre_dia}
                </div>
                """
            )


# ============================================================
# CALENDARIO
# ============================================================


def construir_etiqueta_dia(
    dia: int,
    cantidad_reservas: int,
    es_domingo: bool,
) -> str:
    if es_domingo:
        return f"{dia}\n—"

    if cantidad_reservas <= 0:
        return str(dia)

    if cantidad_reservas == 1:
        return f"{dia}\n●"

    if cantidad_reservas == 2:
        return f"{dia}\n● ●"

    return f"{dia}\n● ● ●"


def mostrar_celda_dia(
    dia: int,
    anio: int,
    mes: int,
    columna_semana: int,
    resumen_reservas: dict[str, int],
) -> None:
    if dia == 0:
        st.html(
            '<div class="calendar-empty-day"></div>'
        )
        return

    fecha_dia = date(anio, mes, dia)
    fecha_iso = fecha_dia.isoformat()

    es_hoy = fecha_dia == date.today()
    es_domingo = columna_semana == 6

    esta_seleccionado = (
        fecha_iso
        == st.session_state.fecha_seleccionada
    )

    cantidad_reservas = resumen_reservas.get(
        fecha_iso,
        0,
    )

    etiqueta = construir_etiqueta_dia(
        dia=dia,
        cantidad_reservas=cantidad_reservas,
        es_domingo=es_domingo,
    )

    ayuda = fecha_dia.strftime("%d/%m/%Y")

    if es_hoy:
        ayuda = f"Hoy · {ayuda}"

    tipo_boton = (
        "primary"
        if esta_seleccionado
        else "secondary"
    )

    st.button(
        etiqueta,
        key=f"calendario_dia_{fecha_iso}",
        help=ayuda,
        type=tipo_boton,
        disabled=es_domingo,
        use_container_width=True,
        on_click=seleccionar_fecha,
        args=(fecha_iso,),
    )


def mostrar_grilla_mes() -> None:
    anio = st.session_state.calendario_anio
    mes = st.session_state.calendario_mes

    generador = calendar.Calendar(
        firstweekday=calendar.MONDAY
    )

    semanas = generador.monthdayscalendar(
        anio,
        mes,
    )

    resumen = cargar_resumen_reservas_mes(
        anio,
        mes,
    )

    mostrar_encabezado_dias()

    for semana in semanas:
        columnas = st.columns(
            7,
            gap="small",
        )

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
# DETALLE DEL DÍA
# ============================================================


def obtener_fecha_seleccionada() -> date:
    fecha_iso = st.session_state.fecha_seleccionada

    try:
        return datetime.strptime(
            fecha_iso,
            "%Y-%m-%d",
        ).date()

    except (TypeError, ValueError):
        hoy = date.today()

        st.session_state.fecha_seleccionada = (
            hoy.isoformat()
        )

        return hoy


def mostrar_encabezado_dia(
    fecha_seleccionada: date,
) -> None:
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
        <div style="
            display: flex;
            align-items: center;
            margin: 22px 0 10px 0;
        ">
            <div style="
                flex: 1;
                height: 1px;
                background: #E7DDF0;
            "></div>

            <div style="
                padding: 0 14px;
                color: #7A23A7;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1px;
                text-transform: uppercase;
            ">
                {escape(titulo)}
            </div>

            <div style="
                flex: 1;
                height: 1px;
                background: #E7DDF0;
            "></div>
        </div>
        """
    )


def abrir_nueva_reserva(
    fecha_iso: str,
    hora: str,
) -> None:
    st.session_state.nueva_reserva_fecha = fecha_iso
    st.session_state.nueva_reserva_hora = hora
    st.session_state.reserva_seleccionada_id = None
    st.session_state.pantalla_actual = "nueva_reserva"


def abrir_detalle_reserva(
    reserva_id: int,
) -> None:
    st.session_state.reserva_seleccionada_id = (
        reserva_id
    )

    st.session_state.nueva_reserva_fecha = None
    st.session_state.nueva_reserva_hora = None
    st.session_state.pantalla_actual = "detalle_reserva"


def mostrar_horario_disponible(
    fecha_iso: str,
    hora: str,
) -> None:
    with st.container(border=True):
        columna_info, columna_estado, columna_boton = st.columns(
            [5.2, 1.3, 2.1],
            vertical_alignment="center",
        )

        with columna_info:
            st.html(
                f"""
                <div class="appointment-card appointment-free">
                    <div class="appointment-hour">
                        {hora}
                    </div>

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
            st.button(
                "Agregar reserva",
                key=f"boton_nueva_reserva_{fecha_iso}_{hora}",
                type="primary",
                use_container_width=True,
                on_click=abrir_nueva_reserva,
                args=(fecha_iso, hora),
            )



def mostrar_reserva_ocupada(
    reserva: dict,
) -> None:
    cliente = escape(
        str(reserva["cliente"])
    )

    celular = escape(
        str(reserva["celular"])
    )

    servicio = escape(
        str(reserva["servicio"])
    )

    estado = escape(
        str(reserva["estado"])
    )

    hora = escape(
        str(reserva["hora"])
    )

    precio = formato_pesos(
        reserva["precio_base"]
    )

    with st.container(border=True):
        columna_info, columna_estado, columna_boton = st.columns(
            [5.2, 1.3, 2.1],
            vertical_alignment="center",
        )

        with columna_info:
            st.html(
                f"""
                <div class="appointment-card appointment-busy">
                    <div class="appointment-hour">
                        {hora}
                    </div>

                    <div class="appointment-information">
                        <div class="appointment-client">
                            {cliente}
                        </div>

                        <div class="appointment-service">
                            {servicio} · {precio}
                        </div>

                        <div class="appointment-phone">
                            {celular}
                        </div>
                    </div>
                </div>
                """
            )

        with columna_estado:
            st.html(
                f"""
                <div class="appointment-status">
                    {estado}
                </div>
                """
            )

        with columna_boton:
            st.button(
                "Ver reserva",
                key=f"boton_ver_reserva_{reserva['id']}",
                use_container_width=True,
                on_click=abrir_detalle_reserva,
                args=(int(reserva["id"]),),
            )



def mostrar_detalle_dia() -> None:
    fecha_seleccionada = (
        obtener_fecha_seleccionada()
    )

    fecha_iso = fecha_seleccionada.isoformat()

    mostrar_encabezado_dia(
        fecha_seleccionada
    )

    if not fecha_es_dia_habil(
        fecha_seleccionada
    ):
        st.warning(
            "Acrylic Purple atiende de lunes a sábado. "
            "Los domingos el salón permanece cerrado."
        )
        return

    horarios = obtener_horarios_del_dia(
        fecha_seleccionada.weekday()
    )

    reservas = cargar_reservas_fecha(
        fecha_iso
    )

    if not horarios:
        st.warning(
            "No existen horarios configurados "
            "para este día."
        )
        return

    ocupados = len(reservas)

    disponibles = max(
        len(horarios) - ocupados,
        0,
    )

    st.html(
        f"""
        <div class="day-summary">
            <div class="day-summary-free">
                {disponibles} disponibles
            </div>

            <div class="day-summary-busy">
                {ocupados} reservados
            </div>
        </div>
        """
    )

    for indice, hora in enumerate(horarios):
        if fecha_seleccionada.weekday() <= 4:
            if indice == 0:
                mostrar_separador_periodo("Mañana")
            elif indice == 1:
                mostrar_separador_periodo("Tarde")
            elif indice == 2:
                mostrar_separador_periodo("Último horario")

        elif fecha_seleccionada.weekday() == 5:
            if indice == 0:
                mostrar_separador_periodo("Mañana")
            elif indice == 1:
                mostrar_separador_periodo("Mediodía")

        reserva = obtener_reserva_por_hora(
            reservas,
            hora,
        )

        if reserva is None:
            mostrar_horario_disponible(
                fecha_iso,
                hora,
            )

        else:
            mostrar_reserva_ocupada(
                reserva
            )


# ============================================================
# PANTALLA PRINCIPAL
# ============================================================


def mostrar_calendario() -> None:
    inicializar_estado_calendario()

    mostrar_encabezado_principal()
    mostrar_navegacion_mes()
    mostrar_grilla_mes()
    mostrar_detalle_dia()