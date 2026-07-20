from datetime import date
from pathlib import Path

import streamlit.components.v1 as components


_COMPONENT_PATH = Path(__file__).parent / "frontend"

_fecha_picker = components.declare_component(
    "fecha_picker_espanol",
    path=str(_COMPONENT_PATH),
)


def selector_fecha_espanol(
    value: date | str | None = None,
    key: str | None = None,
) -> str | None:
    """
    Calendario desplegable basado en Flatpickr.

    Devuelve la fecha seleccionada en formato ISO: YYYY-MM-DD.
    """
    if isinstance(value, date):
        value_iso = value.isoformat()
    elif isinstance(value, str):
        value_iso = value
    else:
        value_iso = date.today().isoformat()

    return _fecha_picker(
        value=value_iso,
        key=key,
        default=value_iso,
    )
