import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config import (
    BACKUPS_DIR,
    DATABASE_PATH,
    MAXIMO_RESPALDOS,
    PREFIJO_RESPALDO,
)


def _nombre_respaldo_del_dia(fecha: datetime) -> str:
    """
    Construye el nombre del respaldo diario.
    """

    return f"{PREFIJO_RESPALDO}_{fecha.strftime('%Y-%m-%d')}.db"


def _listar_respaldos() -> list[Path]:
    """
    Devuelve los respaldos reconocidos, ordenados del más antiguo
    al más reciente.
    """

    patron = f"{PREFIJO_RESPALDO}_*.db"

    return sorted(
        BACKUPS_DIR.glob(patron),
        key=lambda archivo: (
            archivo.stat().st_mtime,
            archivo.name,
        ),
    )


def _eliminar_respaldos_antiguos() -> int:
    """
    Conserva únicamente la cantidad máxima configurada.

    Devuelve la cantidad de archivos eliminados.
    """

    respaldos = _listar_respaldos()
    cantidad_excedente = max(
        0,
        len(respaldos) - MAXIMO_RESPALDOS,
    )

    eliminados = 0

    for respaldo in respaldos[:cantidad_excedente]:
        try:
            respaldo.unlink()
            eliminados += 1
        except OSError:
            # Un problema al eliminar un respaldo antiguo no debe
            # impedir que Agenda PRO siga funcionando.
            continue

    return eliminados


def _verificar_integridad(ruta_respaldo: Path) -> None:
    """
    Comprueba que el archivo generado sea una base SQLite íntegra.

    Si la verificación falla, genera una excepción y el archivo
    temporal no reemplaza al respaldo definitivo.
    """

    with sqlite3.connect(str(ruta_respaldo)) as conexion:
        resultado = conexion.execute(
            "PRAGMA quick_check"
        ).fetchone()

    if not resultado or resultado[0] != "ok":
        raise RuntimeError(
            "La verificación de integridad del respaldo no fue correcta."
        )


def crear_respaldo_diario() -> dict[str, Any]:
    """
    Crea como máximo un respaldo por día.

    El respaldo utiliza la función nativa de SQLite para obtener una
    copia consistente incluso si la base se encuentra abierta.

    El proceso:
    1. Verifica que exista la base de datos.
    2. Comprueba si ya existe el respaldo del día.
    3. Crea una copia temporal.
    4. Verifica su integridad.
    5. La mueve al nombre definitivo.
    6. Conserva solo los últimos respaldos configurados.

    Nunca detiene el inicio de Agenda PRO: cualquier error se devuelve
    dentro del diccionario de estado.
    """

    fecha_actual = datetime.now()
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    destino = BACKUPS_DIR / _nombre_respaldo_del_dia(
        fecha_actual
    )

    estado: dict[str, Any] = {
        "correcto": False,
        "creado": False,
        "ya_existia": False,
        "ruta": str(destino),
        "fecha": fecha_actual,
        "eliminados": 0,
        "mensaje": "",
    }

    if not DATABASE_PATH.exists():
        estado["mensaje"] = (
            "No se encontró la base de datos para respaldar."
        )
        return estado

    if destino.exists():
        estado["correcto"] = True
        estado["ya_existia"] = True
        estado["eliminados"] = _eliminar_respaldos_antiguos()
        estado["mensaje"] = "El respaldo diario ya existía."
        return estado

    temporal = destino.with_suffix(".tmp")

    try:
        if temporal.exists():
            temporal.unlink()

        with sqlite3.connect(str(DATABASE_PATH)) as origen:
            with sqlite3.connect(str(temporal)) as copia:
                origen.backup(copia)

        _verificar_integridad(temporal)
        os.replace(temporal, destino)

        estado["correcto"] = True
        estado["creado"] = True
        estado["eliminados"] = _eliminar_respaldos_antiguos()
        estado["mensaje"] = "Respaldo diario creado correctamente."

    except Exception as error:
        try:
            if temporal.exists():
                temporal.unlink()
        except OSError:
            pass

        estado["mensaje"] = (
            "No fue posible crear el respaldo automático: "
            f"{error}"
        )

    return estado


def obtener_estado_respaldos() -> dict[str, Any]:
    """
    Entrega información resumida para una futura tarjeta visible
    dentro de Configuración.
    """

    respaldos = _listar_respaldos()

    if not respaldos:
        return {
            "cantidad": 0,
            "ultimo_respaldo": None,
            "ruta_ultimo_respaldo": None,
        }

    ultimo = max(
        respaldos,
        key=lambda archivo: archivo.stat().st_mtime,
    )

    return {
        "cantidad": len(respaldos),
        "ultimo_respaldo": datetime.fromtimestamp(
            ultimo.stat().st_mtime
        ),
        "ruta_ultimo_respaldo": str(ultimo),
    }
