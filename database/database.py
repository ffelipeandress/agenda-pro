import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import (
    DATABASE_PATH,
    DATABASE_DIR,
    HORARIOS_DIARIOS,
    ESTADO_RESERVADA,
)


# ============================================================
# AGENDA PRO — MOTOR DE BASE DE DATOS
# ============================================================
# Este archivo administra la conexión con SQLite y crea las
# tablas fundamentales del sistema.
#
# La interfaz no debe escribir consultas SQL directamente.
# Los módulos visuales utilizarán las funciones de este archivo.
# ============================================================


def conectar() -> sqlite3.Connection:
    """
    Abre una conexión con la base de datos de Agenda PRO.

    row_factory permite acceder a los resultados utilizando
    nombres de columnas, por ejemplo:

        fila["nombre"]

    en vez de utilizar posiciones numéricas.
    """

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    conexion = sqlite3.connect(
        DATABASE_PATH,
        timeout=20,
        check_same_thread=False,
    )

    conexion.row_factory = sqlite3.Row

    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.execute("PRAGMA journal_mode = WAL")

    return conexion


def fecha_hora_actual() -> str:
    """
    Devuelve la fecha y hora actual en un formato compatible
    con SQLite.
    """

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# CREACIÓN DE TABLAS
# ============================================================


def crear_tabla_clientes(conexion: sqlite3.Connection) -> None:
    """
    Crea la tabla de clientas.

    El celular se guarda como texto porque puede contener:
    +56, espacios, guiones o ceros iniciales.
    """

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL COLLATE NOCASE,
            celular TEXT NOT NULL,
            observaciones TEXT DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1)),
            fecha_creacion TEXT NOT NULL,
            fecha_actualizacion TEXT
        )
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_clientes_nombre
        ON clientes(nombre)
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_clientes_celular
        ON clientes(celular)
        """
    )


def crear_tabla_servicios(conexion: sqlite3.Connection) -> None:
    """
    Crea la tabla de servicios.

    La duración se guarda en minutos.
    El precio se guarda como número entero porque trabajaremos
    inicialmente con pesos chilenos sin decimales.
    """

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS servicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
            precio_base INTEGER NOT NULL DEFAULT 0
                CHECK (precio_base >= 0),
            duracion_minutos INTEGER NOT NULL DEFAULT 60
                CHECK (duracion_minutos > 0),
            activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1)),
            fecha_creacion TEXT NOT NULL,
            fecha_actualizacion TEXT
        )
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_servicios_activo
        ON servicios(activo)
        """
    )


def crear_tabla_horarios(conexion: sqlite3.Connection) -> None:
    """
    Crea los bloques fijos de atención.

    Los días se guardan según el sistema de Python:

        0 = lunes
        1 = martes
        2 = miércoles
        3 = jueves
        4 = viernes
        5 = sábado
        6 = domingo
    """

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS horarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dia_semana INTEGER NOT NULL
                CHECK (dia_semana BETWEEN 0 AND 6),
            hora TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1)),
            fecha_creacion TEXT NOT NULL,
            UNIQUE(dia_semana, hora)
        )
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_horarios_dia
        ON horarios(dia_semana, activo)
        """
    )


def crear_tabla_reservas(conexion: sqlite3.Connection) -> None:
    """
    Crea la tabla principal de reservas.

    Una reserva activa relaciona una clienta y un servicio con
    una fecha y una hora.

    Las reservas canceladas se conservan para mantener historial.
    """

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,

            cliente_id INTEGER NOT NULL,
            servicio_id INTEGER NOT NULL,

            precio_base INTEGER NOT NULL DEFAULT 0
                CHECK (precio_base >= 0),

            duracion_minutos INTEGER NOT NULL DEFAULT 60
                CHECK (duracion_minutos > 0),

            observacion_interna TEXT DEFAULT '',

            estado TEXT NOT NULL DEFAULT 'Reservada'
                CHECK (
                    estado IN (
                        'Reservada',
                        'Atendida',
                        'Cancelada'
                    )
                ),

            fecha_creacion TEXT NOT NULL,
            fecha_actualizacion TEXT,
            fecha_cancelacion TEXT,

            FOREIGN KEY (cliente_id)
                REFERENCES clientes(id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            FOREIGN KEY (servicio_id)
                REFERENCES servicios(id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        )
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_reservas_fecha
        ON reservas(fecha)
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_reservas_cliente
        ON reservas(cliente_id)
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_reservas_estado
        ON reservas(estado)
        """
    )

    conexion.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_reserva_activa_fecha_hora
        ON reservas(fecha, hora)
        WHERE estado IN ('Reservada', 'Atendida')
        """
    )




def crear_tablas_financieras(
    conexion: sqlite3.Connection,
) -> None:
    """
    Crea la configuración financiera y los retiros de la dueña.
    """

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS configuracion_financiera (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            saldo_inicial_cuenta INTEGER NOT NULL DEFAULT 0,
            fecha_saldo_inicial TEXT NOT NULL DEFAULT '2026-01-01',
            fecha_actualizacion TEXT
        )
        """
    )

    conexion.execute(
        """
        INSERT OR IGNORE INTO configuracion_financiera (
            id,
            saldo_inicial_cuenta,
            fecha_saldo_inicial,
            fecha_actualizacion
        )
        VALUES (1, 0, '2026-01-01', ?)
        """,
        (fecha_hora_actual(),),
    )

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS retiros_duena (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            descripcion TEXT NOT NULL DEFAULT 'Retiro personal',
            monto INTEGER NOT NULL CHECK (monto > 0),
            origen TEXT NOT NULL DEFAULT 'Cuenta bancaria',
            activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1)),
            fecha_creacion TEXT NOT NULL
        )
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_retiros_fecha
        ON retiros_duena(fecha, activo)
        """
    )

def crear_tabla_gastos(conexion: sqlite3.Connection) -> None:
    """
    Registra gastos operativos del salón.

    Los montos se guardan como enteros porque Agenda PRO trabaja
    con pesos chilenos sin decimales.
    """

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            categoria TEXT NOT NULL DEFAULT 'Otros',
            descripcion TEXT NOT NULL,
            monto INTEGER NOT NULL
                CHECK (monto > 0),
            medio_pago TEXT DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1)),
            fecha_creacion TEXT NOT NULL,
            fecha_actualizacion TEXT
        )
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_gastos_fecha
        ON gastos(fecha, activo)
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_gastos_categoria
        ON gastos(categoria, activo)
        """
    )


def migrar_reservas_cobro_real(
    conexion: sqlite3.Connection,
) -> None:
    """
    Agrega a reservas los campos de cobro real.

    Esta migración es segura para bases existentes y no elimina
    ni modifica las reservas ya registradas.
    """

    columnas = {
        fila["name"]
        for fila in conexion.execute(
            "PRAGMA table_info(reservas)"
        ).fetchall()
    }

    nuevas_columnas = {
        "valor_servicio_cobrado": (
            "INTEGER NOT NULL DEFAULT 0"
        ),
        "monto_disenos": (
            "INTEGER NOT NULL DEFAULT 0"
        ),
        "monto_productos": (
            "INTEGER NOT NULL DEFAULT 0"
        ),
        "total_cobrado": (
            "INTEGER NOT NULL DEFAULT 0"
        ),
        "detalle_cobro": (
            "TEXT DEFAULT ''"
        ),
        "medio_pago_cobro": (
            "TEXT DEFAULT 'Transferencia'"
        ),
        "abono_pagado": (
            "INTEGER NOT NULL DEFAULT 0"
        ),
    }

    for nombre_columna, definicion in nuevas_columnas.items():
        if nombre_columna not in columnas:
            conexion.execute(
                f"""
                ALTER TABLE reservas
                ADD COLUMN {nombre_columna} {definicion}
                """
            )

    # Las reservas atendidas antiguas no tenían desglose.
    # Se conserva su precio base como valor real conocido.
    conexion.execute(
        """
        UPDATE reservas
        SET
            valor_servicio_cobrado = precio_base,
            total_cobrado = precio_base
        WHERE estado = 'Atendida'
          AND total_cobrado = 0
        """
    )

    # Una atención no puede quedar registrada antes de ocurrir.
    # Se corrigen automáticamente los registros futuros creados
    # antes de incorporar esta validación.
    conexion.execute(
        """
        UPDATE reservas
        SET
            estado = 'Reservada',
            valor_servicio_cobrado = 0,
            monto_disenos = 0,
            monto_productos = 0,
            total_cobrado = 0,
            detalle_cobro = '',
            fecha_actualizacion = ?
        WHERE estado = 'Atendida'
          AND datetime(fecha || ' ' || hora)
              > datetime('now', 'localtime')
        """,
        (fecha_hora_actual(),),
    )

def crear_tabla_configuracion(conexion: sqlite3.Connection) -> None:
    """
    Crea una tabla para guardar configuraciones futuras sin
    tener que modificar la estructura de la base de datos.
    """

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT,
            descripcion TEXT DEFAULT '',
            fecha_actualizacion TEXT NOT NULL
        )
        """
    )


def crear_tabla_bloqueos(conexion: sqlite3.Connection) -> None:
    """
    Guarda horas o días que no estarán disponibles.

    Aunque no utilizaremos esta función inmediatamente, dejar
    esta tabla creada evita modificar la arquitectura después.
    """

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS bloqueos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            hora TEXT,
            motivo TEXT DEFAULT '',
            activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1)),
            fecha_creacion TEXT NOT NULL
        )
        """
    )

    conexion.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_bloqueos_fecha
        ON bloqueos(fecha, activo)
        """
    )

    conexion.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_bloqueo_dia_activo
        ON bloqueos(fecha)
        WHERE hora IS NULL AND activo = 1
        """
    )

    conexion.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_bloqueo_hora_activo
        ON bloqueos(fecha, hora)
        WHERE hora IS NOT NULL AND activo = 1
        """
    )


# ============================================================
# DATOS INICIALES
# ============================================================


def insertar_horarios_iniciales(
    conexion: sqlite3.Connection,
) -> None:
    """
    Inserta los horarios oficiales de Acrylic Purple.

    Python representa los días de esta forma:

        0 = lunes
        1 = martes
        2 = miércoles
        3 = jueves
        4 = viernes
        5 = sábado
        6 = domingo

    Horarios:

        Lunes a viernes:
        - 09:00
        - 15:00
        - 18:30

        Sábado:
        - 09:00
        - 12:30

        Domingo:
        - Sin atención
    """

    ahora = fecha_hora_actual()

    horarios_por_dia = {
        0: ["09:00", "15:00", "18:30"],
        1: ["09:00", "15:00", "18:30"],
        2: ["09:00", "15:00", "18:30"],
        3: ["09:00", "15:00", "18:30"],
        4: ["09:00", "15:00", "18:30"],
        5: ["09:00", "12:30"],
    }

    for dia_semana, horarios in horarios_por_dia.items():
        for hora in horarios:
            conexion.execute(
                """
                INSERT OR IGNORE INTO horarios (
                    dia_semana,
                    hora,
                    activo,
                    fecha_creacion
                )
                VALUES (?, ?, 1, ?)
                """,
                (
                    dia_semana,
                    hora,
                    ahora,
                ),
            )

    ahora = fecha_hora_actual()

    for dia_semana in range(5):
        for hora in HORARIOS_DIARIOS:
            conexion.execute(
                """
                INSERT OR IGNORE INTO horarios (
                    dia_semana,
                    hora,
                    activo,
                    fecha_creacion
                )
                VALUES (?, ?, 1, ?)
                """,
                (
                    dia_semana,
                    hora,
                    ahora,
                ),
            )


def insertar_servicios_iniciales(
    conexion: sqlite3.Connection,
) -> None:
    """
    Inserta servicios de ejemplo editables.

    Estos datos nos permitirán probar la agenda desde la primera
    versión. Posteriormente podrán modificarse desde el módulo
    Servicios.
    """

    servicios = [
        ("Esmaltado Permanente", 16000, 90),
        ("Acrílicas", 24000, 180),
        ("PolyGel", 22000, 150),
        ("Soft Gel", 22000, 150),
    ]

    ahora = fecha_hora_actual()

    for nombre, precio_base, duracion_minutos in servicios:
        conexion.execute(
            """
            INSERT OR IGNORE INTO servicios (
                nombre,
                precio_base,
                duracion_minutos,
                activo,
                fecha_creacion
            )
            VALUES (?, ?, ?, 1, ?)
            """,
            (
                nombre,
                precio_base,
                duracion_minutos,
                ahora,
            ),
        )


def insertar_configuracion_inicial(
    conexion: sqlite3.Connection,
) -> None:
    """
    Inserta configuraciones generales de Acrylic Purple.
    """

    configuraciones = [
        (
            "nombre_salon",
            "Acrylic Purple",
            "Nombre visible del salón",
        ),
        (
            "texto_precio_base",
            "Precio base, no incluye diseños adicionales.",
            "Aviso mostrado junto al precio del servicio",
        ),
        (
            "version_base_datos",
            "1",
            "Versión interna de la estructura de la base de datos",
        ),
    ]

    ahora = fecha_hora_actual()

    for clave, valor, descripcion in configuraciones:
        conexion.execute(
            """
            INSERT OR IGNORE INTO configuracion (
                clave,
                valor,
                descripcion,
                fecha_actualizacion
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                clave,
                valor,
                descripcion,
                ahora,
            ),
        )


# ============================================================
# INICIALIZACIÓN GENERAL
# ============================================================


def crear_base_de_datos() -> None:
    """
    Crea todas las tablas e inserta los datos iniciales.

    Esta función puede ejecutarse muchas veces sin duplicar
    tablas, horarios, servicios ni configuraciones.
    """

    conexion = conectar()

    try:
        crear_tabla_clientes(conexion)
        crear_tabla_servicios(conexion)
        crear_tabla_horarios(conexion)
        crear_tabla_reservas(conexion)
        migrar_reservas_cobro_real(conexion)
        crear_tablas_financieras(conexion)
        crear_tabla_gastos(conexion)
        crear_tabla_configuracion(conexion)
        crear_tabla_bloqueos(conexion)

        insertar_horarios_iniciales(conexion)
        insertar_servicios_iniciales(conexion)
        insertar_configuracion_inicial(conexion)

        conexion.commit()

    except sqlite3.Error:
        conexion.rollback()
        raise

    finally:
        conexion.close()


# ============================================================
# CONSULTAS GENERALES INICIALES
# ============================================================


def obtener_servicios_activos() -> list[dict]:
    """
    Devuelve todos los servicios activos ordenados por nombre.
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
                activo
            FROM servicios
            WHERE activo = 1
            ORDER BY nombre COLLATE NOCASE
            """
        ).fetchall()

        return [dict(fila) for fila in filas]

    finally:
        conexion.close()


def obtener_horarios_del_dia(
    dia_semana: int,
) -> list[str]:
    """
    Devuelve los horarios activos para un día de la semana.
    """

    conexion = conectar()

    try:
        filas = conexion.execute(
            """
            SELECT hora
            FROM horarios
            WHERE dia_semana = ?
              AND activo = 1
            ORDER BY hora
            """,
            (dia_semana,),
        ).fetchall()

        return [fila["hora"] for fila in filas]

    finally:
        conexion.close()


def obtener_configuracion(
    clave: str,
    valor_predeterminado: Optional[str] = None,
) -> Optional[str]:
    """
    Obtiene una configuración utilizando su clave.
    """

    conexion = conectar()

    try:
        fila = conexion.execute(
            """
            SELECT valor
            FROM configuracion
            WHERE clave = ?
            """,
            (clave,),
        ).fetchone()

        if fila is None:
            return valor_predeterminado

        return fila["valor"]

    finally:
        conexion.close()



# ============================================================
# BLOQUEOS DE AGENDA
# ============================================================


def obtener_bloqueos_fecha(fecha_iso: str) -> list[dict]:
    """
    Devuelve todos los bloqueos activos de una fecha.

    hora = None representa un bloqueo de día completo.
    """

    conexion = conectar()

    try:
        filas = conexion.execute(
            """
            SELECT
                id,
                fecha,
                hora,
                motivo,
                activo,
                fecha_creacion
            FROM bloqueos
            WHERE fecha = ?
              AND activo = 1
            ORDER BY
                CASE WHEN hora IS NULL THEN 0 ELSE 1 END,
                hora
            """,
            (fecha_iso,),
        ).fetchall()

        return [dict(fila) for fila in filas]

    finally:
        conexion.close()


def obtener_resumen_bloqueos_mes(
    anio: int,
    mes: int,
) -> dict[str, dict]:
    """
    Entrega un resumen de bloqueos para pintar el calendario mensual.
    """

    primer_dia = f"{anio:04d}-{mes:02d}-01"

    if mes == 12:
        siguiente_mes = f"{anio + 1:04d}-01-01"
    else:
        siguiente_mes = f"{anio:04d}-{mes + 1:02d}-01"

    conexion = conectar()

    try:
        filas = conexion.execute(
            """
            SELECT
                fecha,
                MAX(CASE WHEN hora IS NULL THEN 1 ELSE 0 END)
                    AS dia_completo,
                SUM(CASE WHEN hora IS NOT NULL THEN 1 ELSE 0 END)
                    AS horas_bloqueadas
            FROM bloqueos
            WHERE fecha >= ?
              AND fecha < ?
              AND activo = 1
            GROUP BY fecha
            """,
            (primer_dia, siguiente_mes),
        ).fetchall()

        return {
            fila["fecha"]: {
                "dia_completo": bool(fila["dia_completo"]),
                "horas_bloqueadas": int(
                    fila["horas_bloqueadas"] or 0
                ),
            }
            for fila in filas
        }

    finally:
        conexion.close()


def horario_esta_bloqueado(
    fecha_iso: str,
    hora: str,
    conexion: sqlite3.Connection | None = None,
) -> bool:
    """
    Comprueba si existe un bloqueo activo para el día completo
    o para una hora específica.
    """

    conexion_propia = conexion is None

    if conexion_propia:
        conexion = conectar()

    try:
        fila = conexion.execute(
            """
            SELECT id
            FROM bloqueos
            WHERE fecha = ?
              AND activo = 1
              AND (
                    hora IS NULL
                    OR hora = ?
              )
            LIMIT 1
            """,
            (fecha_iso, hora),
        ).fetchone()

        return fila is not None

    finally:
        if conexion_propia:
            conexion.close()


def registrar_bloqueo(
    fecha_iso: str,
    hora: str | None,
    motivo: str = "",
) -> tuple[bool, str]:
    """
    Registra un bloqueo después de comprobar que no existan reservas.

    hora = None bloquea el día completo.
    """

    motivo = str(motivo or "").strip()
    hora = str(hora).strip() if hora else None

    try:
        fecha_objeto = datetime.strptime(
            fecha_iso,
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        return False, "La fecha seleccionada no es válida."

    if fecha_objeto.weekday() == 6:
        return (
            False,
            "Los domingos ya están cerrados y no necesitan bloqueo.",
        )

    conexion = conectar()

    try:
        if hora is None:
            reserva = conexion.execute(
                """
                SELECT id
                FROM reservas
                WHERE fecha = ?
                  AND estado IN ('Reservada', 'Atendida')
                LIMIT 1
                """,
                (fecha_iso,),
            ).fetchone()

            if reserva is not None:
                return (
                    False,
                    "No puedes bloquear el día completo porque "
                    "existen reservas activas.",
                )

            existente = conexion.execute(
                """
                SELECT id
                FROM bloqueos
                WHERE fecha = ?
                  AND hora IS NULL
                  AND activo = 1
                LIMIT 1
                """,
                (fecha_iso,),
            ).fetchone()

            if existente is not None:
                return False, "Ese día ya está bloqueado."

            # Un bloqueo completo reemplaza bloqueos parciales previos.
            conexion.execute(
                """
                UPDATE bloqueos
                SET activo = 0
                WHERE fecha = ?
                  AND hora IS NOT NULL
                  AND activo = 1
                """,
                (fecha_iso,),
            )

        else:
            reserva = conexion.execute(
                """
                SELECT id
                FROM reservas
                WHERE fecha = ?
                  AND hora = ?
                  AND estado IN ('Reservada', 'Atendida')
                LIMIT 1
                """,
                (fecha_iso, hora),
            ).fetchone()

            if reserva is not None:
                return (
                    False,
                    "Ese horario tiene una reserva activa y no puede bloquearse.",
                )

            existente = conexion.execute(
                """
                SELECT id
                FROM bloqueos
                WHERE fecha = ?
                  AND activo = 1
                  AND (
                        hora IS NULL
                        OR hora = ?
                  )
                LIMIT 1
                """,
                (fecha_iso, hora),
            ).fetchone()

            if existente is not None:
                return False, "Ese horario ya está bloqueado."

        conexion.execute(
            """
            INSERT INTO bloqueos (
                fecha,
                hora,
                motivo,
                activo,
                fecha_creacion
            )
            VALUES (?, ?, ?, 1, ?)
            """,
            (
                fecha_iso,
                hora,
                motivo,
                fecha_hora_actual(),
            ),
        )

        conexion.commit()

        if hora is None:
            return True, "El día completo quedó bloqueado."

        return True, f"El horario {hora} quedó bloqueado."

    except sqlite3.IntegrityError:
        conexion.rollback()
        return False, "Ese bloqueo ya se encuentra registrado."

    except sqlite3.Error as error:
        conexion.rollback()
        return False, f"No fue posible guardar el bloqueo: {error}"

    finally:
        conexion.close()


def listar_bloqueos_activos(
    fecha_desde: str | None = None,
) -> list[dict]:
    """
    Lista bloqueos activos desde una fecha determinada.
    """

    if fecha_desde is None:
        fecha_desde = datetime.now().strftime("%Y-%m-%d")

    conexion = conectar()

    try:
        filas = conexion.execute(
            """
            SELECT
                id,
                fecha,
                hora,
                motivo,
                fecha_creacion
            FROM bloqueos
            WHERE activo = 1
              AND fecha >= ?
            ORDER BY fecha, hora
            """,
            (fecha_desde,),
        ).fetchall()

        return [dict(fila) for fila in filas]

    finally:
        conexion.close()


def desactivar_bloqueo(
    bloqueo_id: int,
) -> tuple[bool, str]:
    """
    Desactiva un bloqueo sin eliminar su registro histórico.
    """

    conexion = conectar()

    try:
        cursor = conexion.execute(
            """
            UPDATE bloqueos
            SET activo = 0
            WHERE id = ?
              AND activo = 1
            """,
            (bloqueo_id,),
        )

        if cursor.rowcount == 0:
            conexion.rollback()
            return False, "El bloqueo ya no se encuentra activo."

        conexion.commit()
        return True, "La agenda fue desbloqueada correctamente."

    except sqlite3.Error as error:
        conexion.rollback()
        return False, f"No fue posible desbloquear: {error}"

    finally:
        conexion.close()



# ============================================================
# COBRO REAL DE RESERVAS
# ============================================================


def registrar_cobro_reserva(
    reserva_id: int,
    valor_servicio_cobrado: int,
    monto_disenos: int = 0,
    monto_productos: int = 0,
    detalle_cobro: str = "",
    medio_pago_cobro: str = "Transferencia",
) -> tuple[bool, str]:
    """
    Guarda el cobro real y marca la reserva como atendida.
    """

    try:
        valor_servicio_cobrado = int(valor_servicio_cobrado)
        monto_disenos = int(monto_disenos)
        monto_productos = int(monto_productos)
    except (TypeError, ValueError):
        return False, "Los montos ingresados no son válidos."

    if valor_servicio_cobrado < 0:
        return False, "El valor del servicio no puede ser negativo."

    if monto_disenos < 0:
        return False, "El monto de diseños no puede ser negativo."

    if monto_productos < 0:
        return False, "El monto de productos no puede ser negativo."

    detalle_cobro = str(detalle_cobro or "").strip()
    medio_pago_cobro = (
        str(medio_pago_cobro or "Transferencia").strip()
        or "Transferencia"
    )

    total_cobrado = (
        valor_servicio_cobrado
        + monto_disenos
        + monto_productos
    )

    if total_cobrado <= 0:
        return False, "El total cobrado debe ser mayor que cero."

    conexion = conectar()

    try:
        reserva = conexion.execute(
            """
            SELECT id, estado, fecha, hora
            FROM reservas
            WHERE id = ?
            LIMIT 1
            """,
            (reserva_id,),
        ).fetchone()

        if reserva is None:
            return False, "La reserva ya no existe."

        if reserva["estado"] == "Cancelada":
            return (
                False,
                "No se puede registrar cobro en una reserva cancelada.",
            )

        try:
            fecha_hora_reserva = datetime.strptime(
                f'{reserva["fecha"]} {reserva["hora"]}',
                "%Y-%m-%d %H:%M",
            )
        except (TypeError, ValueError):
            return (
                False,
                "La fecha u hora de la reserva no es válida.",
            )

        if fecha_hora_reserva > datetime.now():
            return (
                False,
                "No puedes registrar el cobro antes de que ocurra "
                "la fecha y hora de la atención.",
            )

        ahora = fecha_hora_actual()

        conexion.execute(
            """
            UPDATE reservas
            SET
                valor_servicio_cobrado = ?,
                monto_disenos = ?,
                monto_productos = ?,
                total_cobrado = ?,
                detalle_cobro = ?,
                medio_pago_cobro = ?,
                estado = 'Atendida',
                fecha_actualizacion = ?,
                fecha_cancelacion = NULL
            WHERE id = ?
            """,
            (
                valor_servicio_cobrado,
                monto_disenos,
                monto_productos,
                total_cobrado,
                detalle_cobro,
                medio_pago_cobro,
                ahora,
                reserva_id,
            ),
        )

        conexion.commit()

        return (
            True,
            "La atención y su cobro real fueron registrados "
            "correctamente.",
        )

    except sqlite3.Error as error:
        conexion.rollback()
        return False, f"No fue posible guardar el cobro: {error}"

    finally:
        conexion.close()

# ============================================================
# GASTOS Y ESTADÍSTICAS
# ============================================================


def registrar_gasto(
    fecha_iso: str,
    categoria: str,
    descripcion: str,
    monto: int,
    medio_pago: str = "",
) -> tuple[bool, str]:
    """
    Registra un gasto operativo.
    """

    categoria = str(categoria or "Otros").strip() or "Otros"
    descripcion = str(descripcion or "").strip()
    medio_pago = str(medio_pago or "").strip()

    try:
        datetime.strptime(fecha_iso, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False, "La fecha del gasto no es válida."

    if not descripcion:
        return False, "Debes ingresar una descripción."

    try:
        monto = int(monto)
    except (TypeError, ValueError):
        return False, "El monto debe ser un número válido."

    if monto <= 0:
        return False, "El monto debe ser mayor que cero."

    conexion = conectar()

    try:
        ahora = fecha_hora_actual()

        conexion.execute(
            """
            INSERT INTO gastos (
                fecha,
                categoria,
                descripcion,
                monto,
                medio_pago,
                activo,
                fecha_creacion,
                fecha_actualizacion
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                fecha_iso,
                categoria,
                descripcion,
                monto,
                medio_pago,
                ahora,
                ahora,
            ),
        )

        conexion.commit()
        return True, "El gasto fue registrado correctamente."

    except sqlite3.Error as error:
        conexion.rollback()
        return False, f"No fue posible registrar el gasto: {error}"

    finally:
        conexion.close()


def listar_gastos_mes(
    anio: int,
    mes: int,
) -> list[dict]:
    """
    Lista los gastos activos de un mes.
    """

    primer_dia = f"{anio:04d}-{mes:02d}-01"

    if mes == 12:
        siguiente_mes = f"{anio + 1:04d}-01-01"
    else:
        siguiente_mes = f"{anio:04d}-{mes + 1:02d}-01"

    conexion = conectar()

    try:
        filas = conexion.execute(
            """
            SELECT
                id,
                fecha,
                categoria,
                descripcion,
                monto,
                medio_pago,
                fecha_creacion
            FROM gastos
            WHERE fecha >= ?
              AND fecha < ?
              AND activo = 1
            ORDER BY fecha DESC, id DESC
            """,
            (primer_dia, siguiente_mes),
        ).fetchall()

        return [dict(fila) for fila in filas]

    finally:
        conexion.close()


def eliminar_gasto(
    gasto_id: int,
) -> tuple[bool, str]:
    """
    Desactiva un gasto sin eliminarlo físicamente.
    """

    conexion = conectar()

    try:
        cursor = conexion.execute(
            """
            UPDATE gastos
            SET
                activo = 0,
                fecha_actualizacion = ?
            WHERE id = ?
              AND activo = 1
            """,
            (
                fecha_hora_actual(),
                gasto_id,
            ),
        )

        if cursor.rowcount == 0:
            conexion.rollback()
            return False, "El gasto ya no existe o fue eliminado."

        conexion.commit()
        return True, "El gasto fue eliminado del período."

    except sqlite3.Error as error:
        conexion.rollback()
        return False, f"No fue posible eliminar el gasto: {error}"

    finally:
        conexion.close()


def obtener_estadisticas_mes(
    anio: int,
    mes: int,
) -> dict:
    """
    Devuelve solo resultados reales del mes.

    Los ingresos corresponden exclusivamente a reservas atendidas
    con cobro registrado.
    """

    primer_dia = f"{anio:04d}-{mes:02d}-01"

    if mes == 12:
        siguiente_mes = f"{anio + 1:04d}-01-01"
    else:
        siguiente_mes = f"{anio:04d}-{mes + 1:02d}-01"

    conexion = conectar()

    try:
        resumen = conexion.execute(
            """
            SELECT
                COUNT(*) AS atenciones,
                COALESCE(
                    SUM(
                        CASE
                            WHEN total_cobrado > 0
                            THEN total_cobrado
                            ELSE precio_base
                        END
                    ),
                    0
                ) AS ingresos_reales,
                COALESCE(SUM(monto_disenos), 0) AS disenos,
                COALESCE(SUM(monto_productos), 0) AS productos
            FROM reservas
            WHERE fecha >= ?
              AND fecha < ?
              AND estado = 'Atendida'
            """,
            (primer_dia, siguiente_mes),
        ).fetchone()

        gastos = conexion.execute(
            """
            SELECT COALESCE(SUM(monto), 0) AS total
            FROM gastos
            WHERE fecha >= ?
              AND fecha < ?
              AND activo = 1
            """,
            (primer_dia, siguiente_mes),
        ).fetchone()["total"]

        retiros = conexion.execute(
            """
            SELECT COALESCE(SUM(monto), 0) AS total
            FROM retiros_duena
            WHERE fecha >= ?
              AND fecha < ?
              AND activo = 1
            """,
            (primer_dia, siguiente_mes),
        ).fetchone()["total"]

        servicios = conexion.execute(
            """
            SELECT
                s.nombre AS servicio,
                COUNT(*) AS cantidad,
                COALESCE(
                    SUM(
                        CASE
                            WHEN r.total_cobrado > 0
                            THEN r.total_cobrado
                            ELSE r.precio_base
                        END
                    ),
                    0
                ) AS ingreso_real
            FROM reservas r
            INNER JOIN servicios s
                ON s.id = r.servicio_id
            WHERE r.fecha >= ?
              AND r.fecha < ?
              AND r.estado = 'Atendida'
            GROUP BY s.id, s.nombre
            ORDER BY ingreso_real DESC, s.nombre
            """,
            (primer_dia, siguiente_mes),
        ).fetchall()

        atenciones = conexion.execute(
            """
            SELECT
                r.id,
                r.fecha,
                r.hora,
                c.nombre AS cliente,
                s.nombre AS servicio,
                r.precio_base,
                CASE
                    WHEN r.valor_servicio_cobrado > 0
                    THEN r.valor_servicio_cobrado
                    ELSE r.precio_base
                END AS valor_servicio_cobrado,
                r.monto_disenos,
                r.monto_productos,
                CASE
                    WHEN r.total_cobrado > 0
                    THEN r.total_cobrado
                    ELSE r.precio_base
                END AS total_cobrado,
                r.detalle_cobro,
                COALESCE(
                    NULLIF(r.medio_pago_cobro, ''),
                    'Transferencia'
                ) AS medio_pago_cobro
            FROM reservas r
            INNER JOIN clientes c
                ON c.id = r.cliente_id
            INNER JOIN servicios s
                ON s.id = r.servicio_id
            WHERE r.fecha >= ?
              AND r.fecha < ?
              AND r.estado = 'Atendida'
            ORDER BY r.fecha DESC, r.hora DESC
            """,
            (primer_dia, siguiente_mes),
        ).fetchall()

        ingresos_reales = int(resumen["ingresos_reales"] or 0)
        gastos = int(gastos or 0)
        retiros = int(retiros or 0)

        return {
            "atenciones": int(resumen["atenciones"] or 0),
            "ingresos_reales": ingresos_reales,
            "gastos": gastos,
            "retiros": retiros,
            "resultado_real": ingresos_reales - gastos,
            "disenos": int(resumen["disenos"] or 0),
            "productos": int(resumen["productos"] or 0),
            "servicios": [dict(fila) for fila in servicios],
            "atenciones_detalle": [dict(fila) for fila in atenciones],
        }

    finally:
        conexion.close()


def obtener_saldo_esperado_historico() -> dict:
    """
    Calcula el saldo histórico esperado de la cuenta bancaria.

    Solo considera movimientos asociados a la cuenta:
    Transferencia, Débito y Crédito.
    """

    medios_cuenta = (
        "Transferencia",
        "Débito",
        "Crédito",
    )

    conexion = conectar()

    try:
        config = conexion.execute(
            """
            SELECT
                saldo_inicial_cuenta,
                fecha_saldo_inicial
            FROM configuracion_financiera
            WHERE id = 1
            """
        ).fetchone()

        saldo_inicial = int(
            config["saldo_inicial_cuenta"] or 0
        )
        fecha_inicio = config["fecha_saldo_inicial"]

        placeholders = ",".join("?" for _ in medios_cuenta)

        ingresos = conexion.execute(
            f"""
            SELECT COALESCE(
                SUM(
                    CASE
                        WHEN total_cobrado > 0
                        THEN total_cobrado
                        ELSE precio_base
                    END
                ),
                0
            ) AS total
            FROM reservas
            WHERE estado = 'Atendida'
              AND fecha >= ?
              AND medio_pago_cobro IN ({placeholders})
            """,
            (fecha_inicio, *medios_cuenta),
        ).fetchone()["total"]

        gastos = conexion.execute(
            f"""
            SELECT COALESCE(SUM(monto), 0) AS total
            FROM gastos
            WHERE activo = 1
              AND fecha >= ?
              AND medio_pago IN ({placeholders})
            """,
            (fecha_inicio, *medios_cuenta),
        ).fetchone()["total"]

        retiros = conexion.execute(
            """
            SELECT COALESCE(SUM(monto), 0) AS total
            FROM retiros_duena
            WHERE activo = 1
              AND fecha >= ?
              AND origen = 'Cuenta bancaria'
            """,
            (fecha_inicio,),
        ).fetchone()["total"]

        ingresos = int(ingresos or 0)
        gastos = int(gastos or 0)
        retiros = int(retiros or 0)

        return {
            "saldo_inicial": saldo_inicial,
            "fecha_inicio": fecha_inicio,
            "ingresos_cuenta": ingresos,
            "gastos_cuenta": gastos,
            "retiros_cuenta": retiros,
            "saldo_esperado": (
                saldo_inicial
                + ingresos
                - gastos
                - retiros
            ),
        }

    finally:
        conexion.close()


def guardar_configuracion_financiera(
    saldo_inicial: int,
    fecha_inicio: str,
) -> tuple[bool, str]:
    try:
        saldo_inicial = int(saldo_inicial)
        datetime.strptime(fecha_inicio, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False, "Los datos financieros no son válidos."

    conexion = conectar()

    try:
        conexion.execute(
            """
            UPDATE configuracion_financiera
            SET
                saldo_inicial_cuenta = ?,
                fecha_saldo_inicial = ?,
                fecha_actualizacion = ?
            WHERE id = 1
            """,
            (
                saldo_inicial,
                fecha_inicio,
                fecha_hora_actual(),
            ),
        )
        conexion.commit()
        return True, "La configuración financiera fue actualizada."

    except sqlite3.Error as error:
        conexion.rollback()
        return False, f"No fue posible guardar: {error}"

    finally:
        conexion.close()


def registrar_retiro_duena(
    fecha_iso: str,
    monto: int,
    descripcion: str,
    origen: str,
) -> tuple[bool, str]:
    descripcion = str(descripcion or "Retiro personal").strip()
    origen = str(origen or "Cuenta bancaria").strip()

    try:
        monto = int(monto)
        datetime.strptime(fecha_iso, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False, "Los datos del retiro no son válidos."

    if monto <= 0:
        return False, "El monto debe ser mayor que cero."

    conexion = conectar()

    try:
        conexion.execute(
            """
            INSERT INTO retiros_duena (
                fecha,
                descripcion,
                monto,
                origen,
                activo,
                fecha_creacion
            )
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (
                fecha_iso,
                descripcion,
                monto,
                origen,
                fecha_hora_actual(),
            ),
        )
        conexion.commit()
        return True, "El retiro fue registrado correctamente."

    except sqlite3.Error as error:
        conexion.rollback()
        return False, f"No fue posible registrar el retiro: {error}"

    finally:
        conexion.close()


def listar_retiros_mes(
    anio: int,
    mes: int,
) -> list[dict]:
    inicio = f"{anio:04d}-{mes:02d}-01"

    if mes == 12:
        fin = f"{anio + 1:04d}-01-01"
    else:
        fin = f"{anio:04d}-{mes + 1:02d}-01"

    conexion = conectar()

    try:
        filas = conexion.execute(
            """
            SELECT id, fecha, descripcion, monto, origen
            FROM retiros_duena
            WHERE activo = 1
              AND fecha >= ?
              AND fecha < ?
            ORDER BY fecha DESC, id DESC
            """,
            (inicio, fin),
        ).fetchall()

        return [dict(fila) for fila in filas]

    finally:
        conexion.close()


def eliminar_retiro_duena(
    retiro_id: int,
) -> tuple[bool, str]:
    conexion = conectar()

    try:
        cursor = conexion.execute(
            """
            UPDATE retiros_duena
            SET activo = 0
            WHERE id = ?
              AND activo = 1
            """,
            (retiro_id,),
        )

        if cursor.rowcount == 0:
            conexion.rollback()
            return False, "El retiro ya no se encuentra activo."

        conexion.commit()
        return True, "El retiro fue eliminado."

    except sqlite3.Error as error:
        conexion.rollback()
        return False, f"No fue posible eliminar el retiro: {error}"

    finally:
        conexion.close()

def comprobar_base_de_datos() -> dict:
    """
    Entrega un resumen básico para comprobar que la base de
    datos fue creada correctamente.
    """

    conexion = conectar()

    try:
        tablas = conexion.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        cantidad_servicios = conexion.execute(
            """
            SELECT COUNT(*) AS total
            FROM servicios
            """
        ).fetchone()["total"]

        cantidad_horarios = conexion.execute(
            """
            SELECT COUNT(*) AS total
            FROM horarios
            """
        ).fetchone()["total"]

        return {
            "ruta": str(Path(DATABASE_PATH)),
            "tablas": [fila["name"] for fila in tablas],
            "cantidad_servicios": cantidad_servicios,
            "cantidad_horarios": cantidad_horarios,
            "estado_inicial": ESTADO_RESERVADA,
        }

    finally:
        conexion.close()


if __name__ == "__main__":
    crear_base_de_datos()

    resumen = comprobar_base_de_datos()

    print("=" * 55)
    print("AGENDA PRO — BASE DE DATOS")
    print("=" * 55)
    print(f"Ruta: {resumen['ruta']}")
    print(f"Tablas: {', '.join(resumen['tablas'])}")
    print(f"Servicios iniciales: {resumen['cantidad_servicios']}")
    print(f"Horarios iniciales: {resumen['cantidad_horarios']}")
    print("Base de datos creada correctamente.")
    print("=" * 55)