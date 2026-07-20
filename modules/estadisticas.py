from datetime import date, datetime
from html import escape

import streamlit as st

from database.database import (
    eliminar_gasto,
    eliminar_retiro_duena,
    guardar_configuracion_financiera,
    listar_gastos_mes,
    listar_retiros_mes,
    obtener_estadisticas_mes,
    obtener_saldo_esperado_historico,
    registrar_gasto,
    registrar_retiro_duena,
)


MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre",
    12: "Diciembre",
}


def formato_pesos(valor: int) -> str:
    return f"${int(valor):,}".replace(",", ".")


def fecha_corta(fecha_iso: str) -> str:
    try:
        return datetime.strptime(fecha_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(fecha_iso)


def mostrar_tarjeta(titulo: str, valor: int, detalle: str) -> None:
    st.html(
        f"""
        <div style="
            padding:17px;
            min-height:122px;
            background:#F8F1FB;
            border:1px solid #E4D2EC;
            border-radius:18px;
        ">
            <div style="
                color:#701892;
                font-size:12px;
                font-weight:850;
                text-transform:uppercase;
            ">{escape(titulo)}</div>

            <div style="
                margin-top:8px;
                color:#3F3046;
                font-size:25px;
                font-weight:900;
            ">{formato_pesos(valor)}</div>

            <div style="
                margin-top:5px;
                color:#756A79;
                font-size:12px;
                font-weight:600;
            ">{escape(detalle)}</div>
        </div>
        """
    )


def selector_periodo() -> tuple[int, int]:
    hoy = date.today()
    col_mes, col_anio = st.columns(2)

    with col_mes:
        mes = st.selectbox(
            "Mes",
            list(MESES_ES.keys()),
            index=hoy.month - 1,
            format_func=lambda x: MESES_ES[x],
        )

    with col_anio:
        anios = list(range(max(2024, hoy.year - 3), hoy.year + 2))
        anio = st.selectbox(
            "Año",
            anios,
            index=anios.index(hoy.year),
        )

    return int(anio), int(mes)


def mostrar_resumen_mes(datos: dict) -> None:
    st.markdown("### Resultado real del mes")

    c1, c2 = st.columns(2)
    with c1:
        mostrar_tarjeta(
            "Cobros reales",
            datos["ingresos_reales"],
            f'{datos["atenciones"]} clienta(s) atendida(s)',
        )
    with c2:
        mostrar_tarjeta(
            "Gastos reales",
            datos["gastos"],
            "Gastos registrados durante el mes",
        )

    c3, c4 = st.columns(2)
    with c3:
        mostrar_tarjeta(
            "Resultado real",
            datos["resultado_real"],
            "Cobros del mes menos gastos del mes",
        )
    with c4:
        mostrar_tarjeta(
            "Retiros dueña",
            datos["retiros"],
            "No reducen el resultado; reducen el saldo disponible",
        )


def mostrar_saldo_historico() -> None:
    saldo = obtener_saldo_esperado_historico()

    st.divider()
    st.markdown("### Saldo esperado en cuenta")

    mostrar_tarjeta(
        "Saldo histórico esperado",
        saldo["saldo_esperado"],
        f'Desde {fecha_corta(saldo["fecha_inicio"])}',
    )

    st.caption(
        f'Saldo inicial {formato_pesos(saldo["saldo_inicial"])} + '
        f'ingresos en cuenta {formato_pesos(saldo["ingresos_cuenta"])} − '
        f'gastos desde cuenta {formato_pesos(saldo["gastos_cuenta"])} − '
        f'retiros {formato_pesos(saldo["retiros_cuenta"])}.'
    )

    with st.expander("Configurar saldo inicial"):
        fecha_inicio = st.date_input(
            "Fecha del saldo inicial",
            value=datetime.strptime(
                saldo["fecha_inicio"],
                "%Y-%m-%d",
            ).date(),
            format="DD/MM/YYYY",
            key="fecha_saldo_inicial",
        )

        saldo_inicial = st.number_input(
            "Saldo inicial de la cuenta",
            value=int(saldo["saldo_inicial"]),
            step=10000,
            format="%d",
            key="saldo_inicial_cuenta",
        )

        if st.button(
            "Guardar saldo inicial",
            use_container_width=True,
            key="guardar_saldo_inicial",
        ):
            exito, mensaje = guardar_configuracion_financiera(
                int(saldo_inicial),
                fecha_inicio.isoformat(),
            )
            if exito:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)


def mostrar_atenciones(datos: dict) -> None:
    st.divider()
    st.markdown("### Clientas atendidas")

    if not datos["atenciones_detalle"]:
        st.info("No hay cobros registrados en este mes.")
        return

    for item in datos["atenciones_detalle"]:
        with st.container(border=True):
            st.markdown(
                f'**{escape(str(item["cliente"]))}** · '
                f'{fecha_corta(item["fecha"])} · {escape(str(item["hora"]))}'
            )
            st.caption(
                f'{escape(str(item["servicio"]))} · '
                f'{escape(str(item["medio_pago_cobro"]))}'
            )

            st.html(
                f"""
                <div style="
                    display:grid;
                    grid-template-columns:1fr auto;
                    gap:6px 14px;
                    margin-top:8px;
                    font-size:13px;
                ">
                    <span>Servicio</span>
                    <strong>{formato_pesos(item["valor_servicio_cobrado"])}</strong>
                    <span>Diseños</span>
                    <strong>{formato_pesos(item["monto_disenos"])}</strong>
                    <span>Productos</span>
                    <strong>{formato_pesos(item["monto_productos"])}</strong>
                    <span style="font-weight:900;">Total cobrado</span>
                    <strong style="color:#69158D;font-size:16px;">
                        {formato_pesos(item["total_cobrado"])}
                    </strong>
                </div>
                """
            )

            if item["detalle_cobro"]:
                st.caption(f'Detalle: {item["detalle_cobro"]}')


def mostrar_formulario_gasto(anio: int, mes: int) -> None:
    with st.expander("Registrar gasto"):
        with st.form("form_gasto", clear_on_submit=True):
            fecha = st.date_input(
                "Fecha",
                value=date(anio, mes, 1),
                format="DD/MM/YYYY",
            )
            categoria = st.selectbox(
                "Categoría",
                [
                    "Insumos", "Arriendo", "Servicios básicos",
                    "Publicidad", "Mantención", "Transporte",
                    "Capacitación", "Otros",
                ],
            )
            descripcion = st.text_input("Descripción")
            monto = st.number_input(
                "Monto",
                min_value=0,
                step=1000,
                format="%d",
            )
            medio = st.selectbox(
                "Medio de pago",
                ["Transferencia", "Débito", "Crédito", "Efectivo", "Otro"],
            )
            guardar = st.form_submit_button(
                "Guardar gasto",
                type="primary",
                use_container_width=True,
            )

        if guardar:
            exito, mensaje = registrar_gasto(
                fecha.isoformat(),
                categoria,
                descripcion,
                int(monto),
                medio,
            )
            if exito:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)


def mostrar_formulario_retiro(anio: int, mes: int) -> None:
    with st.expander("Registrar retiro de la dueña"):
        with st.form("form_retiro", clear_on_submit=True):
            fecha = st.date_input(
                "Fecha del retiro",
                value=date(anio, mes, 1),
                format="DD/MM/YYYY",
                key="fecha_retiro",
            )
            descripcion = st.text_input(
                "Descripción",
                value="Retiro personal",
            )
            monto = st.number_input(
                "Monto retirado",
                min_value=0,
                step=10000,
                format="%d",
            )
            origen = st.selectbox(
                "Origen",
                ["Cuenta bancaria", "Efectivo"],
            )
            guardar = st.form_submit_button(
                "Guardar retiro",
                type="primary",
                use_container_width=True,
            )

        if guardar:
            exito, mensaje = registrar_retiro_duena(
                fecha.isoformat(),
                int(monto),
                descripcion,
                origen,
            )
            if exito:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)


def mostrar_movimientos(anio: int, mes: int) -> None:
    gastos = listar_gastos_mes(anio, mes)
    retiros = listar_retiros_mes(anio, mes)

    st.divider()
    st.markdown("### Gastos y retiros del mes")

    if not gastos and not retiros:
        st.info("No hay gastos ni retiros registrados.")
        return

    for gasto in gastos:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1.4])
            with c1:
                st.markdown(f'**Gasto · {escape(str(gasto["descripcion"]))}**')
                st.caption(
                    f'{fecha_corta(gasto["fecha"])} · '
                    f'{escape(str(gasto["categoria"]))} · '
                    f'{escape(str(gasto["medio_pago"]))}'
                )
                st.markdown(formato_pesos(gasto["monto"]))
            with c2:
                if st.button(
                    "Eliminar",
                    key=f'eliminar_gasto_{gasto["id"]}',
                    use_container_width=True,
                ):
                    exito, mensaje = eliminar_gasto(int(gasto["id"]))
                    if exito:
                        st.rerun()
                    else:
                        st.error(mensaje)

    for retiro in retiros:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1.4])
            with c1:
                st.markdown(f'**Retiro · {escape(str(retiro["descripcion"]))}**')
                st.caption(
                    f'{fecha_corta(retiro["fecha"])} · '
                    f'{escape(str(retiro["origen"]))}'
                )
                st.markdown(formato_pesos(retiro["monto"]))
            with c2:
                if st.button(
                    "Eliminar",
                    key=f'eliminar_retiro_{retiro["id"]}',
                    use_container_width=True,
                ):
                    exito, mensaje = eliminar_retiro_duena(
                        int(retiro["id"])
                    )
                    if exito:
                        st.rerun()
                    else:
                        st.error(mensaje)


def mostrar_estadisticas() -> None:
    st.html(
        """
        <div style="
            padding:20px;
            margin-bottom:18px;
            background:linear-gradient(135deg,#F3E4FA,#FFFFFF);
            border:1px solid #DFC9E9;
            border-radius:20px;
        ">
            <div style="
                color:#621286;
                font-size:24px;
                font-weight:900;
            ">Estadísticas reales</div>
            <div style="
                margin-top:3px;
                color:#74627C;
                font-size:13px;
                font-weight:600;
            ">Solo cobros, gastos y saldo efectivamente esperado</div>
        </div>
        """
    )

    anio, mes = selector_periodo()
    datos = obtener_estadisticas_mes(anio, mes)

    mostrar_resumen_mes(datos)
    mostrar_saldo_historico()
    mostrar_atenciones(datos)

    st.divider()
    st.markdown("### Registrar movimientos")
    mostrar_formulario_gasto(anio, mes)
    mostrar_formulario_retiro(anio, mes)
    mostrar_movimientos(anio, mes)