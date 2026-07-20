import sqlite3
from datetime import date, datetime, time, timedelta
from html import escape

import streamlit as st

from database.database import (
    conectar,
    fecha_hora_actual,
    horario_esta_bloqueado,
    obtener_horarios_del_dia,
    obtener_servicios_activos,
    registrar_cobro_reserva,
)


# ============================================================
# AGENDA PRO — MÓDULO DE RESERVAS
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


# ============================================================
# FUNCIONES GENERALES
# ============================================================


def formato_pesos(valor: int) -> str:
    return f"${int(valor):,}".replace(",", ".")


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


def limpiar_texto(texto: str) -> str:
    return str(texto or "").strip()


def normalizar_celular(celular: str) -> str:
    celular = limpiar_texto(celular)

    caracteres_validos = []

    for caracter in celular:
        if caracter.isdigit():
            caracteres_validos.append(caracter)

        elif caracter == "+" and not caracteres_validos:
            caracteres_validos.append(caracter)

    return "".join(caracteres_validos)


def celular_valido(celular: str) -> bool:
    solo_numeros = "".join(
        caracter
        for caracter in celular
        if caracter.isdigit()
    )

    return len(solo_numeros) >= 8


def convertir_fecha(fecha_iso: str) -> date:
    try:
        return datetime.strptime(
            fecha_iso,
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        return date.today()


def volver_calendario(
    mensaje: str | None = None,
    tipo: str = "success",
) -> None:
    st.session_state.pantalla_actual = "calendario"
    st.session_state.vista_principal = "calendario"
    st.session_state.nueva_reserva_fecha = None
    st.session_state.nueva_reserva_hora = None
    st.session_state.reserva_seleccionada_id = None
    st.session_state.confirmar_cancelacion = False
    st.session_state.mostrar_formulario_cobro = False

    # Al regresar desde una acción, el calendario debe mostrarse
    # desde la parte superior, especialmente en teléfonos.
    st.session_state.forzar_scroll_calendario = True

    if mensaje:
        st.session_state.mensaje_agenda = {
            "texto": mensaje,
            "tipo": tipo,
        }


# ============================================================
# CLIENTAS
# ============================================================


def buscar_cliente_por_celular(
    conexion: sqlite3.Connection,
    celular: str,
) -> sqlite3.Row | None:
    return conexion.execute(
        """
        SELECT
            id,
            nombre,
            celular,
            observaciones,
            activo
        FROM clientes
        WHERE celular = ?
          AND activo = 1
        LIMIT 1
        """,
        (celular,),
    ).fetchone()


def crear_o_actualizar_cliente(
    conexion: sqlite3.Connection,
    nombre: str,
    celular: str,
) -> int:
    ahora = fecha_hora_actual()

    cliente_existente = buscar_cliente_por_celular(
        conexion,
        celular,
    )

    if cliente_existente is not None:
        cliente_id = int(cliente_existente["id"])

        conexion.execute(
            """
            UPDATE clientes
            SET
                nombre = ?,
                celular = ?,
                activo = 1,
                fecha_actualizacion = ?
            WHERE id = ?
            """,
            (
                nombre,
                celular,
                ahora,
                cliente_id,
            ),
        )

        return cliente_id

    cursor = conexion.execute(
        """
        INSERT INTO clientes (
            nombre,
            celular,
            observaciones,
            activo,
            fecha_creacion,
            fecha_actualizacion
        )
        VALUES (?, ?, '', 1, ?, ?)
        """,
        (
            nombre,
            celular,
            ahora,
            ahora,
        ),
    )

    return int(cursor.lastrowid)


# ============================================================
# CONSULTAS DE RESERVAS
# ============================================================


def cargar_reserva(reserva_id: int) -> dict | None:
    conexion = conectar()

    try:
        fila = conexion.execute(
            """
            SELECT
                r.id,
                r.fecha,
                r.hora,
                r.cliente_id,
                r.servicio_id,
                r.precio_base,
                r.duracion_minutos,
                r.observacion_interna,
                r.estado,
                r.fecha_creacion,
                r.fecha_actualizacion,
                r.fecha_cancelacion,
                r.valor_servicio_cobrado,
                r.monto_disenos,
                r.monto_productos,
                r.total_cobrado,
                r.detalle_cobro,
                r.abono_pagado,

                c.nombre AS cliente,
                c.celular AS celular,

                s.nombre AS servicio

            FROM reservas r

            INNER JOIN clientes c
                ON c.id = r.cliente_id

            INNER JOIN servicios s
                ON s.id = r.servicio_id

            WHERE r.id = ?
            LIMIT 1
            """,
            (reserva_id,),
        ).fetchone()

        if fila is None:
            return None

        return dict(fila)

    finally:
        conexion.close()


MARGEN_ENTRE_ATENCIONES_MINUTOS = 30


def horario_esta_ocupado(
    conexion: sqlite3.Connection,
    fecha_iso: str,
    hora: str,
    duracion_minutos: int,
    reserva_id_excluir: int | None = None,
) -> bool:
    """
    Comprueba cruces reales de horario.

    Cada reserva ocupa:
    hora de inicio + duración del servicio + 30 minutos de margen.
    """

    inicio_nuevo = datetime.strptime(
        f"{fecha_iso} {hora}",
        "%Y-%m-%d %H:%M",
    )
    fin_nuevo = inicio_nuevo + timedelta(
        minutes=(
            int(duracion_minutos)
            + MARGEN_ENTRE_ATENCIONES_MINUTOS
        )
    )

    parametros: list = [fecha_iso]

    consulta = """
        SELECT id, hora, duracion_minutos
        FROM reservas
        WHERE fecha = ?
          AND estado IN ('Reservada', 'Atendida')
    """

    if reserva_id_excluir is not None:
        consulta += " AND id != ?"
        parametros.append(reserva_id_excluir)

    filas = conexion.execute(
        consulta,
        parametros,
    ).fetchall()

    for fila in filas:
        inicio_existente = datetime.strptime(
            f'{fecha_iso} {fila["hora"]}',
            "%Y-%m-%d %H:%M",
        )
        fin_existente = inicio_existente + timedelta(
            minutes=(
                int(fila["duracion_minutos"])
                + MARGEN_ENTRE_ATENCIONES_MINUTOS
            )
        )

        if (
            inicio_nuevo < fin_existente
            and inicio_existente < fin_nuevo
        ):
            return True

    return False


# ============================================================
# CREACIÓN Y EDICIÓN DE RESERVAS
# ============================================================


def registrar_reserva(
    fecha_iso: str,
    hora: str,
    nombre_cliente: str,
    celular: str,
    servicio_id: int,
    precio_base: int,
    duracion_minutos: int,
    observacion_interna: str,
    abono_pagado: bool,
) -> tuple[bool, str]:
    nombre_cliente = limpiar_texto(nombre_cliente)
    celular = normalizar_celular(celular)
    observacion_interna = limpiar_texto(observacion_interna)

    if not nombre_cliente:
        return False, "Debes ingresar el nombre de la clienta."

    if not celular_valido(celular):
        return False, "Debes ingresar un celular válido."

    conexion = conectar()

    try:
        if horario_esta_bloqueado(
            fecha_iso,
            hora,
            conexion=conexion,
        ):
            return (
                False,
                "Ese horario está bloqueado y no admite reservas.",
            )

        if horario_esta_ocupado(
            conexion,
            fecha_iso,
            hora,
            duracion_minutos,
        ):
            return (
                False,
                "Ese horario se cruza con otra atención, "
                "considerando la duración del servicio y "
                "30 minutos de preparación.",
            )

        cliente_id = crear_o_actualizar_cliente(
            conexion,
            nombre_cliente,
            celular,
        )

        ahora = fecha_hora_actual()

        conexion.execute(
            """
            INSERT INTO reservas (
                fecha,
                hora,
                cliente_id,
                servicio_id,
                precio_base,
                duracion_minutos,
                observacion_interna,
                abono_pagado,
                estado,
                fecha_creacion,
                fecha_actualizacion,
                fecha_cancelacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Reservada', ?, ?, NULL)
            """,
            (
                fecha_iso,
                hora,
                cliente_id,
                servicio_id,
                precio_base,
                duracion_minutos,
                observacion_interna,
                1 if abono_pagado else 0,
                ahora,
                ahora,
            ),
        )

        conexion.commit()

        return True, "La reserva fue registrada correctamente."

    except sqlite3.IntegrityError:
        conexion.rollback()

        return (
            False,
            "No fue posible guardar la reserva porque "
            "el horario ya está ocupado.",
        )

    except sqlite3.Error as error:
        conexion.rollback()

        return (
            False,
            f"No fue posible guardar la reserva: {error}",
        )

    finally:
        conexion.close()


def actualizar_reserva(
    reserva_id: int,
    fecha_iso: str,
    hora: str,
    nombre_cliente: str,
    celular: str,
    servicio_id: int,
    precio_base: int,
    duracion_minutos: int,
    observacion_interna: str,
    abono_pagado: bool,
) -> tuple[bool, str]:
    nombre_cliente = limpiar_texto(nombre_cliente)
    celular = normalizar_celular(celular)
    observacion_interna = limpiar_texto(observacion_interna)

    if not nombre_cliente:
        return False, "Debes ingresar el nombre de la clienta."

    if not celular_valido(celular):
        return False, "Debes ingresar un celular válido."

    fecha_objeto = convertir_fecha(fecha_iso)

    if fecha_objeto.weekday() == 6:
        return False, "No se pueden registrar reservas los domingos."

    try:
        datetime.strptime(hora, "%H:%M")
    except (TypeError, ValueError):
        return False, "La hora seleccionada no es válida."

    conexion = conectar()

    try:
        reserva_actual = conexion.execute(
            """
            SELECT id, estado
            FROM reservas
            WHERE id = ?
            LIMIT 1
            """,
            (reserva_id,),
        ).fetchone()

        if reserva_actual is None:
            return False, "La reserva ya no existe."

        if reserva_actual["estado"] == "Cancelada":
            return False, "No se puede editar una reserva cancelada."

        fecha_hora_editada = datetime.strptime(
            f"{fecha_iso} {hora}",
            "%Y-%m-%d %H:%M",
        )

        if (
            reserva_actual["estado"] == "Atendida"
            and fecha_hora_editada > datetime.now()
        ):
            return (
                False,
                "Una reserva atendida no puede quedar con fecha "
                "u hora futura.",
            )

        if horario_esta_bloqueado(
            fecha_iso,
            hora,
            conexion=conexion,
        ):
            return (
                False,
                "El nuevo horario está bloqueado. "
                "Selecciona otro horario disponible.",
            )

        if horario_esta_ocupado(
            conexion,
            fecha_iso,
            hora,
            duracion_minutos,
            reserva_id_excluir=reserva_id,
        ):
            return (
                False,
                "El nuevo horario se cruza con otra atención, "
                "considerando la duración del servicio y "
                "30 minutos de preparación.",
            )

        cliente_id = crear_o_actualizar_cliente(
            conexion,
            nombre_cliente,
            celular,
        )

        cursor = conexion.execute(
            """
            UPDATE reservas
            SET
                fecha = ?,
                hora = ?,
                cliente_id = ?,
                servicio_id = ?,
                precio_base = ?,
                duracion_minutos = ?,
                observacion_interna = ?,
                abono_pagado = ?,
                fecha_actualizacion = ?
            WHERE id = ?
            """,
            (
                fecha_iso,
                hora,
                cliente_id,
                servicio_id,
                precio_base,
                duracion_minutos,
                observacion_interna,
                1 if abono_pagado else 0,
                fecha_hora_actual(),
                reserva_id,
            ),
        )

        if cursor.rowcount == 0:
            conexion.rollback()
            return False, "No fue posible encontrar la reserva."

        conexion.commit()

        return True, "La reserva fue actualizada correctamente."

    except sqlite3.IntegrityError:
        conexion.rollback()

        return (
            False,
            "No fue posible guardar los cambios porque "
            "el horario seleccionado ya está ocupado.",
        )

    except sqlite3.Error as error:
        conexion.rollback()

        return (
            False,
            f"No fue posible actualizar la reserva: {error}",
        )

    finally:
        conexion.close()


# ============================================================
# CAMBIOS DE ESTADO
# ============================================================


def cambiar_estado_reserva(
    reserva_id: int,
    nuevo_estado: str,
) -> tuple[bool, str]:
    estados_validos = {
        "Reservada",
        "Atendida",
        "Cancelada",
    }

    if nuevo_estado not in estados_validos:
        return False, "El estado seleccionado no es válido."

    conexion = conectar()

    try:
        ahora = fecha_hora_actual()

        fecha_cancelacion = (
            ahora
            if nuevo_estado == "Cancelada"
            else None
        )

        cursor = conexion.execute(
            """
            UPDATE reservas
            SET
                estado = ?,
                fecha_actualizacion = ?,
                fecha_cancelacion = ?
            WHERE id = ?
            """,
            (
                nuevo_estado,
                ahora,
                fecha_cancelacion,
                reserva_id,
            ),
        )

        if cursor.rowcount == 0:
            conexion.rollback()
            return False, "La reserva ya no existe."

        conexion.commit()

        mensajes = {
            "Reservada": "La reserva volvió al estado reservada.",
            "Atendida": "La reserva fue marcada como atendida.",
            "Cancelada": (
                "La reserva fue cancelada y el horario "
                "quedó nuevamente disponible."
            ),
        }

        return True, mensajes[nuevo_estado]

    except sqlite3.Error as error:
        conexion.rollback()

        return (
            False,
            f"No fue posible actualizar la reserva: {error}",
        )

    finally:
        conexion.close()


# ============================================================
# ENCABEZADOS VISUALES
# ============================================================


def mostrar_encabezado_pantalla(
    titulo: str,
    subtitulo: str,
    icono: str,
) -> None:
    st.html(
        f"""
        <div class="reservation-screen-header">
            <div>
                <div class="reservation-screen-title">
                    {escape(titulo)}
                </div>

                <div class="reservation-screen-subtitle">
                    {escape(subtitulo)}
                </div>
            </div>

            <div class="reservation-screen-icon">
                {icono}
            </div>
        </div>
        """
    )


def mostrar_datos_horario(
    fecha_iso: str,
    hora: str,
) -> None:
    st.html(
        f"""
        <div class="reservation-date-card">
            <div class="reservation-date-label">
                Fecha y horario
            </div>

            <div class="reservation-date-value">
                {escape(fecha_en_espanol(fecha_iso))}
            </div>

            <div class="reservation-time-value">
                {escape(hora)} hrs.
            </div>
        </div>
        """
    )


# ============================================================
# PANTALLA: NUEVA RESERVA
# ============================================================


def mostrar_nueva_reserva() -> None:
    fecha_iso = st.session_state.get(
        "nueva_reserva_fecha"
    )

    hora = st.session_state.get(
        "nueva_reserva_hora"
    )

    if not fecha_iso or not hora:
        st.warning(
            "No se seleccionó un horario. "
            "Regresa al calendario."
        )

        if st.button(
            "🏠 CONTINUAR EN LA AGENDA",
            type="primary",
            use_container_width=True,
        ):
            volver_calendario()
            st.rerun()

        return

    mostrar_encabezado_pantalla(
        titulo="Nueva reserva",
        subtitulo="Completa los datos de la clienta",
        icono="✨",
    )

    mostrar_datos_horario(
        fecha_iso,
        hora,
    )

    servicios = obtener_servicios_activos()

    if not servicios:
        st.error(
            "No existen servicios activos. "
            "Debes crear al menos un servicio."
        )
        return

    servicios_por_nombre = {
        servicio["nombre"]: servicio
        for servicio in servicios
    }

    nombres_servicios = list(
        servicios_por_nombre.keys()
    )

    st.html(
        """
        <div class="form-section-title">
            Servicio
        </div>
        """
    )

    servicio_nombre = st.selectbox(
        "Servicio",
        options=nombres_servicios,
        key="nueva_reserva_servicio",
    )

    servicio_seleccionado = servicios_por_nombre[
        servicio_nombre
    ]

    precio_base = int(
        servicio_seleccionado["precio_base"]
    )

    duracion_minutos = int(
        servicio_seleccionado["duracion_minutos"]
    )

    st.html(
        f"""
        <div class="service-selected-card">
            <div>
                <div class="service-selected-label">
                    Precio base
                </div>

                <div class="service-selected-price">
                    {formato_pesos(precio_base)}
                </div>
            </div>

            <div>
                <div class="service-selected-label">
                    Duración estimada
                </div>

                <div class="service-selected-duration">
                    {duracion_minutos} minutos
                </div>
            </div>
        </div>

        <div class="base-price-note">
            Precio base, no incluye diseños adicionales.<br>
            La agenda reservará automáticamente la duración del
            servicio más 30 minutos de preparación.
        </div>
        """
    )

    with st.form(
        "formulario_nueva_reserva",
        clear_on_submit=False,
    ):
        st.html(
            """
            <div class="form-section-title">
                Datos de la clienta
            </div>
            """
        )

        nombre_cliente = st.text_input(
            "Nombre de la clienta",
            placeholder="Ejemplo: Carolina Soto",
            max_chars=100,
        )

        celular = st.text_input(
            "Celular",
            placeholder="Ejemplo: +56 9 1234 5678",
            max_chars=25,
        )

        observacion_interna = st.text_area(
            "Observación interna",
            placeholder=(
                "Información que solo verá Acrylic Purple"
            ),
            max_chars=500,
            height=100,
        )

        abono_pagado = st.checkbox(
            "Abono de $5.000 recibido",
            value=False,
            help=(
                "Marca esta opción cuando la clienta ya haya "
                "pagado el abono para confirmar su reserva."
            ),
        )

        guardar = st.form_submit_button(
            "Guardar reserva",
            type="primary",
            use_container_width=True,
        )

    if guardar:
        exito, mensaje = registrar_reserva(
            fecha_iso=fecha_iso,
            hora=hora,
            nombre_cliente=nombre_cliente,
            celular=celular,
            servicio_id=int(
                servicio_seleccionado["id"]
            ),
            precio_base=precio_base,
            duracion_minutos=duracion_minutos,
            observacion_interna=observacion_interna,
            abono_pagado=abono_pagado,
        )

        if exito:
            st.session_state.fecha_seleccionada = fecha_iso

            volver_calendario(
                mensaje="Reserva creada correctamente.",
            )

            st.rerun()

        else:
            st.error(mensaje)

    if st.button(
        "🏠 CONTINUAR EN LA AGENDA",
        key="cancelar_nueva_reserva",
        type="primary",
        use_container_width=True,
    ):
        volver_calendario()
        st.rerun()


# ============================================================
# PANTALLA: EDITAR RESERVA
# ============================================================


def mostrar_editar_reserva() -> None:
    reserva_id = st.session_state.get(
        "reserva_seleccionada_id"
    )

    if not reserva_id:
        st.warning("No se seleccionó una reserva.")

        if st.button(
            "🏠 CONTINUAR EN LA AGENDA",
            type="primary",
            use_container_width=True,
        ):
            volver_calendario()
            st.rerun()

        return

    reserva = cargar_reserva(int(reserva_id))

    if reserva is None:
        st.error("La reserva seleccionada no existe.")

        if st.button(
            "🏠 CONTINUAR EN LA AGENDA",
            type="primary",
            use_container_width=True,
        ):
            volver_calendario()
            st.rerun()

        return

    if reserva["estado"] == "Cancelada":
        st.warning("Las reservas canceladas no se pueden editar.")

        if st.button(
            "Volver al detalle",
            use_container_width=True,
        ):
            st.session_state.pantalla_actual = "detalle_reserva"
            st.rerun()

        return

    mostrar_encabezado_pantalla(
        titulo="Editar reserva",
        subtitulo="Modifica solamente los datos necesarios",
        icono="✏️",
    )

    servicios = obtener_servicios_activos()

    if not servicios:
        st.error(
            "No existen servicios activos. "
            "Debes crear al menos un servicio."
        )
        return

    servicios_por_nombre = {
        servicio["nombre"]: servicio
        for servicio in servicios
    }

    nombres_servicios = list(servicios_por_nombre.keys())

    servicio_actual = reserva["servicio"]

    indice_servicio = (
        nombres_servicios.index(servicio_actual)
        if servicio_actual in nombres_servicios
        else 0
    )

    fecha_actual = convertir_fecha(reserva["fecha"])

    # Una reserva pasada puede seguir editándose para corregir datos,
    # registrar el estado del abono o ajustar información administrativa.
    # Streamlit genera un error cuando el valor inicial es anterior al
    # min_value, por eso se permite como mínimo la fecha original.
    fecha_minima_edicion = min(
        fecha_actual,
        date.today(),
    )

    fecha_editada = st.date_input(
        "Fecha",
        value=fecha_actual,
        min_value=fecha_minima_edicion,
        format="DD/MM/YYYY",
    )

    if fecha_editada.weekday() == 6:
        st.error(
            "Acrylic Purple no atiende los domingos. "
            "Selecciona una fecha entre lunes y sábado."
        )

    try:
        hora_actual = datetime.strptime(
            str(reserva["hora"]),
            "%H:%M",
        ).time()
    except (TypeError, ValueError):
        hora_actual = time(9, 0)

    hora_editada_objeto = st.time_input(
        "Hora",
        value=hora_actual,
        step=1800,
        help=(
            "Puedes elegir un horario distinto a los horarios "
            "habituales, por ejemplo 08:00 o 17:00."
        ),
    )

    hora_editada = hora_editada_objeto.strftime("%H:%M")

    st.html(
        """
        <div class="form-section-title">
            Servicio
        </div>
        """
    )

    servicio_nombre = st.selectbox(
        "Servicio",
        options=nombres_servicios,
        index=indice_servicio,
        key=f"editar_servicio_{reserva['id']}",
    )

    servicio_seleccionado = servicios_por_nombre[
        servicio_nombre
    ]

    precio_base = int(
        servicio_seleccionado["precio_base"]
    )

    duracion_minutos = int(
        servicio_seleccionado["duracion_minutos"]
    )

    st.html(
        f"""
        <div class="service-selected-card">
            <div>
                <div class="service-selected-label">
                    Precio base
                </div>

                <div class="service-selected-price">
                    {formato_pesos(precio_base)}
                </div>
            </div>

            <div>
                <div class="service-selected-label">
                    Duración estimada
                </div>

                <div class="service-selected-duration">
                    {duracion_minutos} minutos
                </div>
            </div>
        </div>

        <div class="base-price-note">
            El precio y la duración se actualizarán según el servicio.<br>
            También se reservarán 30 minutos adicionales de preparación.
        </div>
        """
    )

    with st.form(
        "formulario_editar_reserva",
        clear_on_submit=False,
    ):
        st.html(
            """
            <div class="form-section-title">
                Datos de la clienta
            </div>
            """
        )

        nombre_cliente = st.text_input(
            "Nombre de la clienta",
            value=str(reserva["cliente"]),
            max_chars=100,
        )

        celular = st.text_input(
            "Celular",
            value=str(reserva["celular"]),
            max_chars=25,
        )

        observacion_interna = st.text_area(
            "Observación interna",
            value=str(
                reserva["observacion_interna"] or ""
            ),
            max_chars=500,
            height=100,
        )

        abono_pagado = st.checkbox(
            "Abono de $5.000 recibido",
            value=bool(reserva["abono_pagado"]),
            help=(
                "Puedes marcar o desmarcar el estado del abono "
                "sin modificar el cobro final de la atención."
            ),
        )

        guardar_cambios = st.form_submit_button(
            "Guardar cambios",
            type="primary",
            use_container_width=True,
        )

    if guardar_cambios:
        if fecha_editada.weekday() == 6 or not hora_editada:
            st.error(
                "Debes seleccionar una fecha de lunes a sábado "
                "y una hora válida."
            )
        else:
            exito, mensaje = actualizar_reserva(
                reserva_id=int(reserva["id"]),
                fecha_iso=fecha_editada.isoformat(),
                hora=hora_editada,
                nombre_cliente=nombre_cliente,
                celular=celular,
                servicio_id=int(
                    servicio_seleccionado["id"]
                ),
                precio_base=precio_base,
                duracion_minutos=duracion_minutos,
                observacion_interna=observacion_interna,
                abono_pagado=abono_pagado,
            )

            if exito:
                st.session_state.fecha_seleccionada = (
                    fecha_editada.isoformat()
                )

                volver_calendario(
                    mensaje="Reserva actualizada correctamente.",
                )

                st.rerun()

            else:
                st.error(mensaje)

    if st.button(
        "🏠 CONTINUAR EN LA AGENDA",
        key="cancelar_edicion_reserva",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.fecha_seleccionada = reserva["fecha"]
        volver_calendario()
        st.rerun()


# ============================================================
# PANTALLA: DETALLE DE RESERVA
# ============================================================


def mostrar_detalle_reserva() -> None:
    reserva_id = st.session_state.get(
        "reserva_seleccionada_id"
    )

    if not reserva_id:
        st.warning(
            "No se seleccionó una reserva."
        )

        if st.button(
            "🏠 CONTINUAR EN LA AGENDA",
            type="primary",
            use_container_width=True,
        ):
            volver_calendario()
            st.rerun()

        return

    reserva = cargar_reserva(
        int(reserva_id)
    )

    if reserva is None:
        st.error(
            "La reserva seleccionada no existe."
        )

        if st.button(
            "🏠 CONTINUAR EN LA AGENDA",
            type="primary",
            use_container_width=True,
        ):
            volver_calendario()
            st.rerun()

        return

    mostrar_encabezado_pantalla(
        titulo="Detalle de reserva",
        subtitulo=fecha_en_espanol(
            reserva["fecha"]
        ),
        icono="💜",
    )

    cliente = escape(
        str(reserva["cliente"])
    )

    celular = escape(
        str(reserva["celular"])
    )

    servicio = escape(
        str(reserva["servicio"])
    )

    observacion = escape(
        str(
            reserva["observacion_interna"]
            or "Sin observaciones"
        )
    )

    estado = escape(
        str(reserva["estado"])
    )

    st.html(
        f"""
        <div class="reservation-detail-card">
            <div class="reservation-detail-top">
                <div>
                    <div class="reservation-detail-hour">
                        {escape(str(reserva["hora"]))}
                    </div>

                    <div class="reservation-detail-date">
                        {escape(fecha_en_espanol(reserva["fecha"]))}
                    </div>
                </div>

                <div class="reservation-state reservation-state-{estado.lower()}">
                    {estado}
                </div>
            </div>

            <div class="reservation-detail-divider"></div>

            <div class="reservation-detail-label">
                Clienta
            </div>

            <div class="reservation-detail-value">
                {cliente}
            </div>

            <div class="reservation-detail-secondary">
                {celular}
            </div>

            <div class="reservation-detail-divider"></div>

            <div class="reservation-detail-label">
                Servicio
            </div>

            <div class="reservation-detail-value">
                {servicio}
            </div>

            <div class="reservation-detail-secondary">
                {formato_pesos(reserva["precio_base"])}
                · {reserva["duracion_minutos"]} minutos
            </div>

            <div class="reservation-detail-divider"></div>

            <div class="reservation-detail-label">
                Estado del abono
            </div>

            <div class="reservation-detail-value">
                {'Abono OK · $5.000' if reserva["abono_pagado"] else 'Sin abono'}
            </div>

            <div class="reservation-detail-divider"></div>

            <div class="reservation-detail-label">
                Observación interna
            </div>

            <div class="reservation-observation">
                {observacion}
            </div>
        </div>
        """
    )

    if reserva["estado"] == "Reservada":
        try:
            fecha_hora_reserva = datetime.strptime(
                f'{reserva["fecha"]} {reserva["hora"]}',
                "%Y-%m-%d %H:%M",
            )
            reserva_ya_ocurrio = (
                fecha_hora_reserva <= datetime.now()
            )
        except (TypeError, ValueError):
            reserva_ya_ocurrio = False

        columna_atendida, columna_editar, columna_cancelar = st.columns(3)

        with columna_atendida:
            if st.button(
                "Registrar cobro",
                type="primary",
                use_container_width=True,
                disabled=not reserva_ya_ocurrio,
            ):
                st.session_state.mostrar_formulario_cobro = True

        with columna_editar:
            if st.button(
                "Editar reserva",
                use_container_width=True,
            ):
                st.session_state.pantalla_actual = (
                    "editar_reserva"
                )
                st.rerun()

        with columna_cancelar:
            if st.button(
                "Cancelar reserva",
                use_container_width=True,
            ):
                st.session_state.confirmar_cancelacion = True

        if not reserva_ya_ocurrio:
            st.info(
                "Registrar cobro se habilitará cuando haya ocurrido "
                "la fecha y hora de esta reserva."
            )

    if (
        reserva["estado"] == "Reservada"
        and st.session_state.get(
            "mostrar_formulario_cobro",
            False,
        )
    ):
        st.divider()

        st.html(
            """
            <div style="
                padding: 16px 17px;
                margin-bottom: 12px;
                background: #F6EAFB;
                border: 1px solid #DFC7EB;
                border-radius: 17px;
            ">
                <div style="
                    color: #67158B;
                    font-size: 18px;
                    font-weight: 900;
                ">
                    Registrar cobro real
                </div>

                <div style="
                    margin-top: 4px;
                    color: #75657B;
                    font-size: 12px;
                    font-weight: 600;
                ">
                    Puedes modificar el valor del servicio y sumar
                    diseños o productos vendidos.
                </div>
            </div>
            """
        )

        with st.form(
            "formulario_cobro_real",
            clear_on_submit=False,
        ):
            valor_servicio_cobrado = st.number_input(
                "Valor real del servicio",
                min_value=0,
                value=int(reserva["precio_base"]),
                step=1000,
                format="%d",
                help=(
                    "Puede ser distinto del precio base "
                    "si hubo una modificación."
                ),
            )

            monto_disenos = st.number_input(
                "Diseños adicionales",
                min_value=0,
                value=0,
                step=500,
                format="%d",
            )

            monto_productos = st.number_input(
                "Productos vendidos",
                min_value=0,
                value=0,
                step=1000,
                format="%d",
            )

            total_previsualizado = (
                int(valor_servicio_cobrado)
                + int(monto_disenos)
                + int(monto_productos)
            )

            monto_abono = (
                5000
                if bool(reserva["abono_pagado"])
                else 0
            )

            saldo_por_cobrar = max(
                total_previsualizado - monto_abono,
                0,
            )

            st.html(
                f"""
                <div style="
                    margin: 12px 0;
                    padding: 16px 17px;
                    background: #ECF8F1;
                    border: 1px solid #C8E6D4;
                    border-radius: 15px;
                ">
                    <div style="
                        color: #28704A;
                        font-size: 12px;
                        font-weight: 900;
                        text-transform: uppercase;
                        letter-spacing: 0.03em;
                    ">
                        Resumen de la atención
                    </div>

                    <div style="
                        display: grid;
                        grid-template-columns: 1fr auto;
                        gap: 8px 14px;
                        margin-top: 13px;
                        color: #496155;
                        font-size: 13px;
                    ">
                        <span>Servicio</span>
                        <strong>{formato_pesos(valor_servicio_cobrado)}</strong>

                        <span>Diseños</span>
                        <strong>{formato_pesos(monto_disenos)}</strong>

                        <span>Productos</span>
                        <strong>{formato_pesos(monto_productos)}</strong>

                        <span style="
                            padding-top: 8px;
                            border-top: 1px solid #CBE2D4;
                            font-weight: 900;
                        ">Total atención</span>

                        <strong style="
                            padding-top: 8px;
                            border-top: 1px solid #CBE2D4;
                            color: #185638;
                        ">
                            {formato_pesos(total_previsualizado)}
                        </strong>

                        <span>Abono recibido</span>
                        <strong>
                            {'-' + formato_pesos(monto_abono) if monto_abono else formato_pesos(0)}
                        </strong>

                        <span style="
                            padding-top: 9px;
                            border-top: 2px solid #A8D5BA;
                            color: #174D32;
                            font-weight: 900;
                            text-transform: uppercase;
                        ">Saldo por cobrar</span>

                        <strong style="
                            padding-top: 9px;
                            border-top: 2px solid #A8D5BA;
                            color: #174D32;
                            font-size: 21px;
                            font-weight: 900;
                        ">
                            {formato_pesos(saldo_por_cobrar)}
                        </strong>
                    </div>
                </div>
                """
            )

            detalle_cobro = st.text_area(
                "Detalle opcional",
                placeholder=(
                    "Ejemplo: diseño francesa en 4 uñas y "
                    "venta de aceite para cutículas"
                ),
                max_chars=300,
                height=90,
            )

            guardar_cobro = st.form_submit_button(
                f"Registrar pago de {formato_pesos(saldo_por_cobrar)}",
                type="primary",
                use_container_width=True,
            )

        if guardar_cobro:
            exito, mensaje = registrar_cobro_reserva(
                reserva_id=int(reserva["id"]),
                valor_servicio_cobrado=int(
                    valor_servicio_cobrado
                ),
                monto_disenos=int(monto_disenos),
                monto_productos=int(monto_productos),
                detalle_cobro=detalle_cobro,
            )

            if exito:
                st.session_state.fecha_seleccionada = reserva["fecha"]

                volver_calendario(
                    mensaje="Cobro registrado correctamente.",
                )

                st.rerun()
            else:
                st.error(mensaje)

        if st.button(
            "Cancelar registro de cobro",
            key="cancelar_registro_cobro",
            use_container_width=True,
        ):
            st.session_state.mostrar_formulario_cobro = False
            st.rerun()

    elif reserva["estado"] == "Atendida":
        total_cobrado = int(
            reserva["total_cobrado"]
            or reserva["precio_base"]
        )

        valor_servicio = int(
            reserva["valor_servicio_cobrado"]
            or reserva["precio_base"]
        )

        monto_abono = (
            5000
            if bool(reserva["abono_pagado"])
            else 0
        )

        pago_final = max(
            total_cobrado - monto_abono,
            0,
        )

        st.success(
            "Esta reserva fue marcada como atendida."
        )

        st.html(
            f"""
            <div style="
                margin-top: 12px;
                padding: 17px;
                background: #EFF9F3;
                border: 1px solid #C8E6D4;
                border-radius: 17px;
            ">
                <div style="
                    color: #1E6741;
                    font-size: 16px;
                    font-weight: 900;
                ">
                    Cobro registrado
                </div>

                <div style="
                    display: grid;
                    grid-template-columns: 1fr auto;
                    gap: 7px 16px;
                    margin-top: 12px;
                    color: #496155;
                    font-size: 13px;
                ">
                    <span>Servicio</span>
                    <strong>{formato_pesos(valor_servicio)}</strong>

                    <span>Diseños</span>
                    <strong>{formato_pesos(reserva["monto_disenos"] or 0)}</strong>

                    <span>Productos</span>
                    <strong>{formato_pesos(reserva["monto_productos"] or 0)}</strong>

                    <span style="
                        padding-top: 7px;
                        border-top: 1px solid #CBE2D4;
                        font-weight: 900;
                    ">Total atención</span>

                    <strong style="
                        padding-top: 7px;
                        border-top: 1px solid #CBE2D4;
                        color: #185638;
                    ">
                        {formato_pesos(total_cobrado)}
                    </strong>

                    <span>Abono recibido</span>
                    <strong>
                        {formato_pesos(monto_abono)}
                    </strong>

                    <span>Pago final</span>
                    <strong>
                        {formato_pesos(pago_final)}
                    </strong>

                    <span style="
                        padding-top: 8px;
                        border-top: 2px solid #A8D5BA;
                        font-weight: 900;
                        text-transform: uppercase;
                    ">Total pagado</span>

                    <strong style="
                        padding-top: 8px;
                        border-top: 2px solid #A8D5BA;
                        color: #185638;
                        font-size: 18px;
                    ">
                        {formato_pesos(total_cobrado)}
                    </strong>
                </div>
            </div>
            """
        )

        if reserva["detalle_cobro"]:
            st.caption(
                f"Detalle: {reserva['detalle_cobro']}"
            )

        st.divider()

        if st.button(
            "Editar datos de la reserva",
            key="editar_reserva_atendida",
            use_container_width=True,
        ):
            st.session_state.pantalla_actual = "editar_reserva"
            st.rerun()

        st.caption(
            "El cobro ya fue registrado. "
            "Por eso no vuelve a aparecer Registrar cobro."
        )

    elif reserva["estado"] == "Cancelada":
        st.warning(
            "Esta reserva está cancelada. "
            "El horario se encuentra disponible."
        )

    if st.session_state.get(
        "confirmar_cancelacion",
        False,
    ):
        st.warning(
            "¿Confirmas que deseas cancelar esta reserva?"
        )

        columna_confirmar, columna_mantener = st.columns(2)

        with columna_confirmar:
            if st.button(
                "Sí, cancelar",
                type="primary",
                use_container_width=True,
            ):
                exito, mensaje = cambiar_estado_reserva(
                    reserva_id=int(reserva["id"]),
                    nuevo_estado="Cancelada",
                )

                st.session_state.confirmar_cancelacion = False

                if exito:
                    st.session_state.fecha_seleccionada = reserva["fecha"]

                    volver_calendario(
                        mensaje="Reserva cancelada correctamente.",
                    )

                    st.rerun()

                else:
                    st.error(mensaje)

        with columna_mantener:
            if st.button(
                "No cancelar",
                use_container_width=True,
            ):
                st.session_state.confirmar_cancelacion = False
                st.rerun()

    if st.button(
        "🏠 CONTINUAR EN LA AGENDA",
        key="volver_desde_detalle",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.fecha_seleccionada = reserva["fecha"]
        volver_calendario()
        st.rerun()