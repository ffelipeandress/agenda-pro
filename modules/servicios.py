import sqlite3

import streamlit as st

from database.database import conectar, fecha_hora_actual


# ============================================================
# AGENDA PRO — ADMINISTRACIÓN DE SERVICIOS
# ============================================================
# Este módulo permite:
#
# - Crear servicios.
# - Modificar nombre, precio y duración.
# - Activar o desactivar servicios.
# - Mantener los servicios antiguos para conservar el historial.
#
# No elimina servicios físicamente de la base de datos.
# ============================================================


def formato_pesos(valor: int) -> str:
    """
    Convierte un número entero al formato de pesos chilenos.
    """

    try:
        numero = int(valor)
    except (TypeError, ValueError):
        numero = 0

    return f"${numero:,.0f}".replace(",", ".")


def obtener_todos_los_servicios() -> list[dict]:
    """
    Devuelve todos los servicios, activos e inactivos.
    """

    conexion = conectar()

    try:
        filas = conexion.execute(
            """
            SELECT
                id,
                nombre,
                precio_base,
                duracion_minutos,
                activo,
                fecha_creacion,
                fecha_actualizacion
            FROM servicios
            ORDER BY
                activo DESC,
                nombre COLLATE NOCASE
            """
        ).fetchall()

        return [dict(fila) for fila in filas]

    finally:
        conexion.close()


def obtener_servicio_por_id(servicio_id: int) -> dict | None:
    """
    Devuelve un servicio específico utilizando su identificador.
    """

    conexion = conectar()

    try:
        fila = conexion.execute(
            """
            SELECT
                id,
                nombre,
                precio_base,
                duracion_minutos,
                activo,
                fecha_creacion,
                fecha_actualizacion
            FROM servicios
            WHERE id = ?
            """,
            (servicio_id,),
        ).fetchone()

        if fila is None:
            return None

        return dict(fila)

    finally:
        conexion.close()


def crear_servicio(
    nombre: str,
    precio_base: int,
    duracion_minutos: int,
    activo: bool = True,
) -> tuple[bool, str]:
    """
    Crea un nuevo servicio.
    """

    nombre_limpio = nombre.strip()

    if not nombre_limpio:
        return False, "Debes ingresar el nombre del servicio."

    if precio_base < 0:
        return False, "El precio no puede ser negativo."

    if duracion_minutos <= 0:
        return False, "La duración debe ser mayor que cero."

    conexion = conectar()

    try:
        conexion.execute(
            """
            INSERT INTO servicios (
                nombre,
                precio_base,
                duracion_minutos,
                activo,
                fecha_creacion,
                fecha_actualizacion
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                nombre_limpio,
                int(precio_base),
                int(duracion_minutos),
                1 if activo else 0,
                fecha_hora_actual(),
                fecha_hora_actual(),
            ),
        )

        conexion.commit()

        return True, "Servicio creado correctamente."

    except sqlite3.IntegrityError:
        conexion.rollback()
        return False, "Ya existe un servicio con ese nombre."

    except sqlite3.Error as error:
        conexion.rollback()
        return False, f"No fue posible crear el servicio: {error}"

    finally:
        conexion.close()


def actualizar_servicio(
    servicio_id: int,
    nombre: str,
    precio_base: int,
    duracion_minutos: int,
    activo: bool,
) -> tuple[bool, str]:
    """
    Actualiza los datos de un servicio existente.
    """

    nombre_limpio = nombre.strip()

    if not nombre_limpio:
        return False, "Debes ingresar el nombre del servicio."

    if precio_base < 0:
        return False, "El precio no puede ser negativo."

    if duracion_minutos <= 0:
        return False, "La duración debe ser mayor que cero."

    conexion = conectar()

    try:
        cursor = conexion.execute(
            """
            UPDATE servicios
            SET
                nombre = ?,
                precio_base = ?,
                duracion_minutos = ?,
                activo = ?,
                fecha_actualizacion = ?
            WHERE id = ?
            """,
            (
                nombre_limpio,
                int(precio_base),
                int(duracion_minutos),
                1 if activo else 0,
                fecha_hora_actual(),
                servicio_id,
            ),
        )

        if cursor.rowcount == 0:
            conexion.rollback()
            return False, "El servicio seleccionado ya no existe."

        conexion.commit()

        return True, "Servicio actualizado correctamente."

    except sqlite3.IntegrityError:
        conexion.rollback()
        return False, "Ya existe otro servicio con ese nombre."

    except sqlite3.Error as error:
        conexion.rollback()
        return False, f"No fue posible actualizar el servicio: {error}"

    finally:
        conexion.close()


def cambiar_estado_servicio(
    servicio_id: int,
    nuevo_estado: bool,
) -> tuple[bool, str]:
    """
    Activa o desactiva un servicio sin eliminarlo.
    """

    conexion = conectar()

    try:
        cursor = conexion.execute(
            """
            UPDATE servicios
            SET
                activo = ?,
                fecha_actualizacion = ?
            WHERE id = ?
            """,
            (
                1 if nuevo_estado else 0,
                fecha_hora_actual(),
                servicio_id,
            ),
        )

        if cursor.rowcount == 0:
            conexion.rollback()
            return False, "El servicio seleccionado ya no existe."

        conexion.commit()

        if nuevo_estado:
            return True, "Servicio activado correctamente."

        return True, "Servicio desactivado correctamente."

    except sqlite3.Error as error:
        conexion.rollback()
        return False, f"No fue posible cambiar el estado: {error}"

    finally:
        conexion.close()


def mostrar_resumen(servicios: list[dict]) -> None:
    """
    Muestra indicadores básicos de la configuración de servicios.
    """

    activos = sum(1 for servicio in servicios if servicio["activo"] == 1)
    inactivos = len(servicios) - activos

    columna_1, columna_2, columna_3 = st.columns(3)

    columna_1.metric("Servicios totales", len(servicios))
    columna_2.metric("Activos", activos)
    columna_3.metric("Inactivos", inactivos)


def mostrar_formulario_nuevo_servicio() -> None:
    """
    Muestra el formulario para agregar un servicio.
    """

    with st.expander("➕ Agregar nuevo servicio", expanded=False):
        with st.form("formulario_nuevo_servicio", clear_on_submit=True):
            nombre = st.text_input(
                "Nombre del servicio",
                placeholder="Ejemplo: Kapping Gel",
            )

            columna_precio, columna_duracion = st.columns(2)

            with columna_precio:
                precio_base = st.number_input(
                    "Precio base",
                    min_value=0,
                    step=1000,
                    value=0,
                    format="%d",
                )

            with columna_duracion:
                duracion_minutos = st.number_input(
                    "Duración en minutos",
                    min_value=15,
                    step=15,
                    value=90,
                    format="%d",
                )

            activo = st.checkbox(
                "Servicio activo",
                value=True,
                help=(
                    "Los servicios activos aparecen en los formularios "
                    "de reserva."
                ),
            )

            guardar = st.form_submit_button(
                "Guardar servicio",
                use_container_width=True,
                type="primary",
            )

        if guardar:
            exito, mensaje = crear_servicio(
                nombre=nombre,
                precio_base=int(precio_base),
                duracion_minutos=int(duracion_minutos),
                activo=activo,
            )

            if exito:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)


def mostrar_editor_servicio(servicio: dict) -> None:
    """
    Muestra una tarjeta editable para un servicio.
    """

    servicio_id = servicio["id"]
    esta_activo = servicio["activo"] == 1

    icono_estado = "🟢" if esta_activo else "⚪"
    texto_estado = "Activo" if esta_activo else "Inactivo"

    titulo = (
        f"{icono_estado} {servicio['nombre']} · "
        f"{formato_pesos(servicio['precio_base'])} · "
        f"{servicio['duracion_minutos']} min · "
        f"{texto_estado}"
    )

    with st.expander(titulo, expanded=False):
        with st.form(f"formulario_editar_servicio_{servicio_id}"):
            nombre = st.text_input(
                "Nombre",
                value=servicio["nombre"],
                key=f"nombre_servicio_{servicio_id}",
            )

            columna_precio, columna_duracion = st.columns(2)

            with columna_precio:
                precio_base = st.number_input(
                    "Precio base",
                    min_value=0,
                    step=1000,
                    value=int(servicio["precio_base"]),
                    format="%d",
                    key=f"precio_servicio_{servicio_id}",
                )

            with columna_duracion:
                duracion_minutos = st.number_input(
                    "Duración en minutos",
                    min_value=15,
                    step=15,
                    value=int(servicio["duracion_minutos"]),
                    format="%d",
                    key=f"duracion_servicio_{servicio_id}",
                )

            activo = st.checkbox(
                "Servicio activo",
                value=esta_activo,
                key=f"activo_servicio_{servicio_id}",
            )

            guardar = st.form_submit_button(
                "Guardar cambios",
                use_container_width=True,
                type="primary",
            )

        if guardar:
            exito, mensaje = actualizar_servicio(
                servicio_id=servicio_id,
                nombre=nombre,
                precio_base=int(precio_base),
                duracion_minutos=int(duracion_minutos),
                activo=activo,
            )

            if exito:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)

        if esta_activo:
            if st.button(
                "Desactivar servicio",
                key=f"desactivar_servicio_{servicio_id}",
                use_container_width=True,
            ):
                exito, mensaje = cambiar_estado_servicio(
                    servicio_id=servicio_id,
                    nuevo_estado=False,
                )

                if exito:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.error(mensaje)

        else:
            if st.button(
                "Activar servicio",
                key=f"activar_servicio_{servicio_id}",
                use_container_width=True,
                type="primary",
            ):
                exito, mensaje = cambiar_estado_servicio(
                    servicio_id=servicio_id,
                    nuevo_estado=True,
                )

                if exito:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.error(mensaje)


def mostrar_servicios() -> None:
    """
    Página principal del módulo Servicios.
    """

    st.title("💅 Servicios")

    st.caption(
        "Administra los servicios de Acrylic Purple. Los cambios "
        "realizados aquí se utilizarán en las nuevas reservas."
    )

    servicios = obtener_todos_los_servicios()

    mostrar_resumen(servicios)
    mostrar_formulario_nuevo_servicio()

    st.divider()

    if not servicios:
        st.info(
            "Todavía no existen servicios registrados. "
            "Agrega el primero utilizando el formulario superior."
        )
        return

    st.subheader("Servicios registrados")

    mostrar_inactivos = st.toggle(
        "Mostrar servicios inactivos",
        value=True,
    )

    servicios_visibles = [
        servicio
        for servicio in servicios
        if mostrar_inactivos or servicio["activo"] == 1
    ]

    for servicio in servicios_visibles:
        mostrar_editor_servicio(servicio)


if __name__ == "__main__":
    st.set_page_config(
        page_title="Servicios | Agenda PRO",
        page_icon="💅",
        layout="wide",
    )

    mostrar_servicios()