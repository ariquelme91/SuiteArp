"""
UI del Simulador de Propuestas de Renta.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from src.analysis.db_manager import AnalysisDBManager
from src.analysis.compensation_calculator import CompensationCalculator
from src.analysis.proposal_pdf_exporter import ProposalPDFExporter
from src.payroll_engine import PayrollEngine
from src.utils.formatters import format_peso_chileno
import json


def show_proposal_simulator():
    """Muestra el simulador de propuestas de renta."""

    st.header("🎯 Simulador de Propuestas de Renta")
    st.subheader("Simula incrementos y compara posición vs mercado")

    db_manager = AnalysisDBManager()

    # SECCIÓN 1: Selección de Empleado
    st.divider()
    st.subheader("1️⃣ Selecciona Empleado")

    empleados = db_manager.get_analysis_by_empresa_area()

    if not empleados:
        st.info("ℹ️ No hay empleados cargados. Carga datos en la pestaña ANÁLISIS.")
        return

    empleados_dict = {f"{emp.get('nombre')} ({emp.get('rut')})": emp for emp in empleados}
    empleado_seleccionado = st.selectbox(
        "Selecciona empleado:",
        options=list(empleados_dict.keys()),
        key="prop_empleado"
    )

    if not empleado_seleccionado:
        return

    empleado = empleados_dict[empleado_seleccionado]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Empresa", empleado.get("empresa", "-"))

    with col2:
        st.metric("Cargo", empleado.get("cargo_actual", "-"))

    with col3:
        st.metric("Nivel HAY", empleado.get("nivel_hay", "-"))

    with col4:
        st.metric("Sueldo Base Actual", format_peso_chileno(empleado.get("sueldo_actual", 0)))

    # SECCIÓN 2: Haberes Propuestos
    st.divider()
    st.subheader("2️⃣ Haberes Propuestos")

    st.write("**¿Cómo ingresar el nuevo sueldo?**")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.radio(
            "Tipo de incremento",
            ["Sueldo base", "% sobre el sueldo base", "Sueldo Líquido", "% sobre el sueldo líquido"],
            horizontal=False,
            key="prop_tipo_ingreso",
            index=0
        )

    tipo_ingreso = st.session_state.get("prop_tipo_ingreso", "Sueldo base")

    st.write("**Nuevo Sueldo Base**")

    sueldo_actual = empleado.get("sueldo_actual", 0)

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if tipo_ingreso == "Sueldo base":
            sueldo_propuesto = st.number_input(
                "Sueldo Base Propuesto ($)",
                min_value=0,
                value=int(sueldo_actual),
                step=100000,
                key="prop_sueldo_nuevo"
            )
        elif tipo_ingreso == "% sobre el sueldo base":
            pct_incremento = st.number_input(
                "% de incremento",
                min_value=0.0,
                value=10.0,
                step=0.5,
                key="prop_pct_base"
            )
            sueldo_propuesto = int(sueldo_actual * (1 + pct_incremento / 100))
            st.info(f"Nuevo sueldo: {format_peso_chileno(sueldo_propuesto)}")
        elif tipo_ingreso == "Sueldo Líquido":
            sueldo_liquido_input = st.number_input(
                "Sueldo Líquido Deseado ($)",
                min_value=0,
                value=int(sueldo_actual * 0.85),
                step=100000,
                key="prop_sueldo_liquido"
            )
            # Aproximación inversa (simplificada)
            sueldo_propuesto = int(sueldo_liquido_input / 0.85)
        else:  # % sobre el sueldo líquido
            pct_incremento_liq = st.number_input(
                "% de incremento sobre líquido",
                min_value=0.0,
                value=10.0,
                step=0.5,
                key="prop_pct_liquido"
            )
            sueldo_liquido_actual = int(sueldo_actual * 0.85)
            sueldo_propuesto = int(sueldo_liquido_actual * (1 + pct_incremento_liq / 100) / 0.85)
            st.info(f"Nuevo sueldo: {format_peso_chileno(sueldo_propuesto)}")

    st.caption("Base tomada del lado izquierdo (modificar si es necesario)")

    # Haberes no imponibles
    st.write("**Haberes No Imponibles**")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        colacion = st.number_input(
            "Colación",
            min_value=0,
            value=130000,
            step=10000,
            key="prop_colacion"
        )

    with col2:
        movilizacion = st.number_input(
            "Movilización",
            min_value=0,
            value=99000,
            step=10000,
            key="prop_movilizacion"
        )

    with col3:
        otros = st.number_input(
            "Otros imponibles",
            min_value=0,
            value=0,
            step=10000,
            key="prop_otros"
        )

    with col4:
        mercado = st.selectbox(
            "Mercado Comparación",
            options=["Mercado Financiero", "Mercado Seguros"],
            key="prop_mercado"
        )

    # Descuentos voluntarios
    st.write("**Descuentos**")
    col1, col2 = st.columns(2)

    with col1:
        estacionamiento = st.number_input(
            "Estacionamiento",
            min_value=0,
            value=0,
            step=10000,
            key="prop_estacionamiento"
        )

    with col2:
        otros_descuentos = st.number_input(
            "Otros descuentos",
            min_value=0,
            value=0,
            step=10000,
            key="prop_otros_descuentos"
        )

    # Nivel HAY (en caso de cambio de cargo)
    st.write("**Cambios en Cargo/Nivel**")
    col1, col2 = st.columns(2)

    nivel_actual = int(empleado.get("nivel_hay") or 0)

    with col1:
        # Obtener todos los niveles disponibles en la BD
        niveles_disponibles = db_manager.get_compensation_levels()
        niveles_dict = {str(n.get('nivel')): n.get('nivel') for n in niveles_disponibles}

        nivel_propuesto = st.selectbox(
            "Nivel HAY Propuesto",
            options=list(niveles_dict.keys()),
            index=list(niveles_dict.keys()).index(str(nivel_actual)) if str(nivel_actual) in niveles_dict else 0,
            key="prop_nivel_hay"
        )
        nivel_propuesto = int(nivel_propuesto)

    with col2:
        st.metric(
            "Cambio de Nivel",
            f"Actual: {nivel_actual} → Propuesto: {nivel_propuesto}",
            delta="Promoción ✓" if nivel_propuesto > nivel_actual else ("Sin cambio" if nivel_propuesto == nivel_actual else "Cambio")
        )

    # Target
    st.write("**Target Propuesto**")
    col1, col2 = st.columns(2)

    target_actual = float(empleado.get("target") or 1.0)

    with col1:
        target_type = st.radio(
            "Modificar Target:",
            ["Nuevo Valor", "Incremento"],
            horizontal=True,
            key="prop_target_type"
        )

    with col2:
        if target_type == "Nuevo Valor":
            target_propuesto = st.number_input(
                "Nuevo Target (Rentas)",
                min_value=0.0,
                value=target_actual,
                step=0.1,
                key="prop_target_nuevo"
            )
        else:
            incremento_target = st.number_input(
                "Incremento Target (Rentas)",
                min_value=-target_actual,
                value=0.0,
                step=0.1,
                key="prop_target_incremento"
            )
            target_propuesto = target_actual + incremento_target

    incremento_sueldo = sueldo_propuesto - sueldo_actual

    # Cálculos
    try:
        import json
        with open("config/parameters.json") as f:
            params = json.load(f)
        imm_value = params.get("imm_value", 553_553)

        target_actual = float(empleado.get("target") or 1.0)
        nivel_actual = int(empleado.get("nivel_hay") or 0)
        mes_actual = datetime.now().strftime("%Y-%m")

        calculator = CompensationCalculator(db_manager, imm_value=imm_value)

        # Compensación ACTUAL
        comp_actual = calculator.comparativa_completa(
            sueldo_base=sueldo_actual,
            nivel_actual=nivel_actual,
            target=target_actual,
            mes=mes_actual,
            mercado=mercado
        )

        # Compensación PROPUESTA (usa nivel_propuesto si cambió)
        comp_propuesta = calculator.comparativa_completa(
            sueldo_base=sueldo_propuesto,
            nivel_actual=nivel_propuesto,  # Usa nivel propuesto para comparativa
            target=target_propuesto,  # Ya está en rentas
            mes=mes_actual,
            mercado=mercado
        )

        # SECCIÓN 3: Comparativo de Haberes y Descuentos
        st.divider()
        st.subheader("3️⃣ Comparativo de Haberes y Descuentos")

        # Datos para la tabla
        comparativo_data = []

        # Sueldo Base
        sueldo_base_actual = comp_actual.get('sueldo_anual', 0) / 12
        sueldo_base_propuesto = comp_propuesta.get('sueldo_anual', 0) / 12
        var_sb = sueldo_base_propuesto - sueldo_base_actual
        var_sb_pct = (var_sb / sueldo_base_actual * 100) if sueldo_base_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Sueldo Base",
            "Actual": format_peso_chileno(sueldo_base_actual),
            "Propuesta": format_peso_chileno(sueldo_base_propuesto),
            "Variación ($)": format_peso_chileno(var_sb),
            "Variación (%)": f"{var_sb_pct:.1f}%"
        })

        # Gratificación
        grat_actual = comp_actual.get('gratificacion', 0)
        grat_propuesta = comp_propuesta.get('gratificacion', 0)
        var_grat = grat_propuesta - grat_actual
        var_grat_pct = (var_grat / grat_actual * 100) if grat_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Gratificación",
            "Actual": format_peso_chileno(grat_actual),
            "Propuesta": format_peso_chileno(grat_propuesta),
            "Variación ($)": format_peso_chileno(var_grat),
            "Variación (%)": f"{var_grat_pct:.1f}%"
        })

        # Colación
        colacion_actual = comp_actual.get('colacion', 0)
        colacion_propuesta = colacion  # Usuario puede modificar
        var_colacion = colacion_propuesta - colacion_actual
        var_colacion_pct = (var_colacion / colacion_actual * 100) if colacion_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Colación",
            "Actual": format_peso_chileno(colacion_actual),
            "Propuesta": format_peso_chileno(colacion_propuesta),
            "Variación ($)": format_peso_chileno(var_colacion),
            "Variación (%)": f"{var_colacion_pct:.1f}%"
        })

        # Movilización
        movilizacion_actual = comp_actual.get('movilizacion', 0)
        movilizacion_propuesta = movilizacion  # Usuario puede modificar
        var_movilizacion = movilizacion_propuesta - movilizacion_actual
        var_movilizacion_pct = (var_movilizacion / movilizacion_actual * 100) if movilizacion_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Movilización",
            "Actual": format_peso_chileno(movilizacion_actual),
            "Propuesta": format_peso_chileno(movilizacion_propuesta),
            "Variación ($)": format_peso_chileno(var_movilizacion),
            "Variación (%)": f"{var_movilizacion_pct:.1f}%"
        })

        # Total Imponible
        total_imponible_actual = comp_actual.get('total_cash_anual', 0) / 12
        target_propuesto_anual = sueldo_propuesto * target_propuesto
        total_imponible_propuesto = (sueldo_propuesto + target_propuesto_anual / 12)
        var_total_imp = total_imponible_propuesto - total_imponible_actual
        var_total_imp_pct = (var_total_imp / total_imponible_actual * 100) if total_imponible_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Total Imponible",
            "Actual": format_peso_chileno(total_imponible_actual),
            "Propuesta": format_peso_chileno(total_imponible_propuesto),
            "Variación ($)": format_peso_chileno(var_total_imp),
            "Variación (%)": f"{var_total_imp_pct:.1f}%"
        })

        # Total No Imponible
        total_no_imp_actual = (colacion_actual + movilizacion_actual + otros) / 12
        total_no_imp_propuesto = (colacion_propuesta + movilizacion_propuesta + otros) / 12
        var_total_no_imp = total_no_imp_propuesto - total_no_imp_actual
        var_total_no_imp_pct = (var_total_no_imp / total_no_imp_actual * 100) if total_no_imp_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Total No Imponible",
            "Actual": format_peso_chileno(total_no_imp_actual),
            "Propuesta": format_peso_chileno(total_no_imp_propuesto),
            "Variación ($)": format_peso_chileno(var_total_no_imp),
            "Variación (%)": f"{var_total_no_imp_pct:.1f}%"
        })

        # Total Haberes
        total_haberes_actual = total_imponible_actual + total_no_imp_actual
        total_haberes_propuesto = total_imponible_propuesto + total_no_imp_propuesto
        var_total_hab = total_haberes_propuesto - total_haberes_actual
        var_total_hab_pct = (var_total_hab / total_haberes_actual * 100) if total_haberes_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Total Haberes",
            "Actual": format_peso_chileno(total_haberes_actual),
            "Propuesta": format_peso_chileno(total_haberes_propuesto),
            "Variación ($)": format_peso_chileno(var_total_hab),
            "Variación (%)": f"{var_total_hab_pct:.1f}%"
        })

        # Inicializar PayrollEngine para calcular impuesto a la renta
        payroll_engine = PayrollEngine(params)

        # Descuentos (aproximados basados en %s estándar)
        afp_pct = 0.10  # 10%
        salud_pct = 0.07  # 7%
        afc_pct = 0.0067  # 0.67%

        desc_afp_actual = total_imponible_actual * afp_pct
        desc_afp_propuesta = total_imponible_propuesto * afp_pct
        var_afp = desc_afp_propuesta - desc_afp_actual
        var_afp_pct = (var_afp / desc_afp_actual * 100) if desc_afp_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Descuento AFP",
            "Actual": format_peso_chileno(desc_afp_actual),
            "Propuesta": format_peso_chileno(desc_afp_propuesta),
            "Variación ($)": format_peso_chileno(var_afp),
            "Variación (%)": f"{var_afp_pct:.1f}%"
        })

        desc_salud_actual = total_imponible_actual * salud_pct
        desc_salud_propuesta = total_imponible_propuesto * salud_pct
        var_salud = desc_salud_propuesta - desc_salud_actual
        var_salud_pct = (var_salud / desc_salud_actual * 100) if desc_salud_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Descuento Salud",
            "Actual": format_peso_chileno(desc_salud_actual),
            "Propuesta": format_peso_chileno(desc_salud_propuesta),
            "Variación ($)": format_peso_chileno(var_salud),
            "Variación (%)": f"{var_salud_pct:.1f}%"
        })

        desc_afc_actual = total_imponible_actual * afc_pct
        desc_afc_propuesta = total_imponible_propuesto * afc_pct
        var_afc = desc_afc_propuesta - desc_afc_actual
        var_afc_pct = (var_afc / desc_afc_actual * 100) if desc_afc_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Descuento AFC",
            "Actual": format_peso_chileno(desc_afc_actual),
            "Propuesta": format_peso_chileno(desc_afc_propuesta),
            "Variación ($)": format_peso_chileno(var_afc),
            "Variación (%)": f"{var_afc_pct:.1f}%"
        })

        # Impuesto a la Renta
        impuesto_actual = payroll_engine._calculate_income_tax(total_imponible_actual * 12)
        impuesto_propuesta = payroll_engine._calculate_income_tax(total_imponible_propuesto * 12)
        var_impuesto = impuesto_propuesta - impuesto_actual
        var_impuesto_pct = (var_impuesto / impuesto_actual * 100) if impuesto_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Impuesto a la Renta",
            "Actual": format_peso_chileno(impuesto_actual / 12),
            "Propuesta": format_peso_chileno(impuesto_propuesta / 12),
            "Variación ($)": format_peso_chileno(var_impuesto / 12),
            "Variación (%)": f"{var_impuesto_pct:.1f}%" if impuesto_actual > 0 else "—"
        })

        # Estacionamiento
        estacionamiento_actual = comp_actual.get('estacionamiento', 0)
        estacionamiento_propuesta = estacionamiento
        var_estacionamiento = estacionamiento_propuesta - estacionamiento_actual
        var_estacionamiento_pct = (var_estacionamiento / estacionamiento_actual * 100) if estacionamiento_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Estacionamiento",
            "Actual": format_peso_chileno(estacionamiento_actual),
            "Propuesta": format_peso_chileno(estacionamiento_propuesta),
            "Variación ($)": format_peso_chileno(var_estacionamiento),
            "Variación (%)": f"{var_estacionamiento_pct:.1f}%" if estacionamiento_actual > 0 else "—"
        })

        # Otros descuentos
        otros_desc_actual = 0
        otros_desc_propuesta = otros_descuentos
        var_otros_desc = otros_desc_propuesta - otros_desc_actual
        var_otros_desc_pct = (var_otros_desc / otros_desc_actual * 100) if otros_desc_actual > 0 else 0

        if otros_descuentos > 0:
            comparativo_data.append({
                "Concepto": "Otros Descuentos",
                "Actual": format_peso_chileno(otros_desc_actual),
                "Propuesta": format_peso_chileno(otros_desc_propuesta),
                "Variación ($)": format_peso_chileno(var_otros_desc),
                "Variación (%)": "—"
            })

        # Total Descuentos
        total_desc_actual = desc_afp_actual + desc_salud_actual + desc_afc_actual + (impuesto_actual / 12) + estacionamiento_actual + otros_desc_actual
        total_desc_propuesta = desc_afp_propuesta + desc_salud_propuesta + desc_afc_propuesta + (impuesto_propuesta / 12) + estacionamiento_propuesta + otros_desc_propuesta
        var_total_desc = total_desc_propuesta - total_desc_actual
        var_total_desc_pct = (var_total_desc / total_desc_actual * 100) if total_desc_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Total Descuentos",
            "Actual": format_peso_chileno(total_desc_actual),
            "Propuesta": format_peso_chileno(total_desc_propuesta),
            "Variación ($)": format_peso_chileno(var_total_desc),
            "Variación (%)": f"{var_total_desc_pct:.1f}%"
        })

        # Sueldo Líquido Neto (Total Haberes - Total Descuentos)
        sueldo_liquido_neto_actual = total_haberes_actual - total_desc_actual
        sueldo_liquido_neto_propuesto = total_haberes_propuesto - total_desc_propuesta
        var_liquido_neto = sueldo_liquido_neto_propuesto - sueldo_liquido_neto_actual
        var_liquido_neto_pct = (var_liquido_neto / sueldo_liquido_neto_actual * 100) if sueldo_liquido_neto_actual > 0 else 0

        comparativo_data.append({
            "Concepto": "Sueldo Líquido Neto",
            "Actual": format_peso_chileno(sueldo_liquido_neto_actual),
            "Propuesta": format_peso_chileno(sueldo_liquido_neto_propuesto),
            "Variación ($)": format_peso_chileno(var_liquido_neto),
            "Variación (%)": f"{var_liquido_neto_pct:.1f}%"
        })

        df_comparativo = pd.DataFrame(comparativo_data)
        st.dataframe(df_comparativo, use_container_width=True, hide_index=True)

        # SECCIÓN 4: Comparativa Compensación
        st.divider()
        st.subheader("4️⃣ Comparativa: Compensación Actual vs Propuesta")

        comparativa_data = {
            "Métrica": [
                "Total Cash Anual",
                "Compa Ratio",
                "Posición en Banda",
                "Estado",
                "Banda"
            ],
            "Actual": [
                format_peso_chileno(comp_actual.get('total_cash_anual', 0)),
                f"{comp_actual.get('compa_ratio', 0):.1f}%",
                f"{comp_actual.get('posicion_en_banda_pct', 0):.1f}%",
                comp_actual.get('estado', ''),
                comp_actual.get('banda', '')
            ],
            "Propuesto": [
                format_peso_chileno(comp_propuesta.get('total_cash_anual', 0)),
                f"{comp_propuesta.get('compa_ratio', 0):.1f}%",
                f"{comp_propuesta.get('posicion_en_banda_pct', 0):.1f}%",
                comp_propuesta.get('estado', ''),
                comp_propuesta.get('banda', '')
            ],
            "Cambio": [
                format_peso_chileno(comp_propuesta.get('total_cash_anual', 0) - comp_actual.get('total_cash_anual', 0)),
                f"{comp_propuesta.get('compa_ratio', 0) - comp_actual.get('compa_ratio', 0):+.1f}%",
                f"{comp_propuesta.get('posicion_en_banda_pct', 0) - comp_actual.get('posicion_en_banda_pct', 0):+.1f}%",
                "✓" if comp_propuesta.get('estado') != comp_actual.get('estado') else "—",
                "Mejora" if comp_propuesta.get('banda') != comp_actual.get('banda') else "—"
            ]
        }

        df_comparativa = pd.DataFrame(comparativa_data)
        st.dataframe(df_comparativa, use_container_width=True, hide_index=True)

        # SECCIÓN 5: Impacto Presupuestario
        st.divider()
        st.subheader("5️⃣ Impacto Presupuestario")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Incremento Anual",
                format_peso_chileno(incremento_sueldo * 12),
                "Costo presupuestario"
            )

        with col2:
            pct_inc = (incremento_sueldo / sueldo_actual) * 100 if sueldo_actual > 0 else 0
            st.metric(
                "% Incremento",
                f"{pct_inc:.1f}%",
                "Sobre sueldo actual"
            )

        with col3:
            st.metric(
                "Compa Ratio Nuevo",
                f"{comp_propuesta.get('compa_ratio', 0):.1f}%",
                "Ideal: 95-105%"
            )

        with col4:
            st.metric(
                "Estado",
                comp_propuesta.get('estado', ''),
                comp_propuesta.get('banda', '')
            )

        # SECCIÓN 6: Exportar a PDF
        st.divider()
        st.subheader("6️⃣ Exportar Propuesta")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.caption("Genera PDF profesional de la simulación")

        with col2:
            try:
                proposal_data = {
                    'total_cash': comp_propuesta.get('total_cash_anual', 0),
                    'compa_ratio': comp_propuesta.get('compa_ratio', 0),
                    'banda_pct': comp_propuesta.get('posicion_en_banda_pct', 0),
                    'estado': comp_propuesta.get('estado', ''),
                    'incremento_mensual': incremento_sueldo,
                    'incremento_anual': incremento_sueldo * 12,
                    'incremento_pct': pct_inc
                }

                actual_data = {
                    'total_cash': comp_actual.get('total_cash_anual', 0),
                    'compa_ratio': comp_actual.get('compa_ratio', 0),
                    'banda_pct': comp_actual.get('posicion_en_banda_pct', 0),
                    'estado': comp_actual.get('estado', '')
                }

                exporter = ProposalPDFExporter(
                    employee_data=empleado,
                    actual_comp=actual_data,
                    proposal_comp=proposal_data
                )
                pdf_buffer = exporter.generate_pdf()

                st.download_button(
                    label="📄 Descargar PDF",
                    data=pdf_buffer.getvalue(),
                    file_name=f"propuesta_renta_{empleado.get('rut').replace('.', '').replace('-', '')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error generando PDF: {str(e)}")

        # SECCIÓN 7: Guardar Simulación
        st.divider()
        st.subheader("7️⃣ Guardar Simulación")

        col1, col2 = st.columns([3, 1])

        with col1:
            nombre_sim = st.text_input(
                "Nombre de la simulación",
                value=f"Prop: +${incremento_sueldo:,.0f}",
                key="prop_nombre"
            )

        with col2:
            if st.button("💾 Guardar", use_container_width=True, key="prop_guardar"):
                simulacion = {
                    'nombre': nombre_sim,
                    'fecha': datetime.now().isoformat(),
                    'empleado': empleado.get('nombre'),
                    'rut': empleado.get('rut'),
                    'incremento_sueldo': float(incremento_sueldo),
                    'target_propuesto': float(target_propuesto),
                    'compa_ratio_actual': float(comp_actual.get('compa_ratio', 0)),
                    'compa_ratio_propuesto': float(comp_propuesta.get('compa_ratio', 0)),
                    'estado_actual': comp_actual.get('estado', ''),
                    'estado_propuesto': comp_propuesta.get('estado', ''),
                }

                if 'simulaciones' not in st.session_state:
                    st.session_state.simulaciones = []

                st.session_state.simulaciones.append(simulacion)
                st.success(f"✅ Simulación '{nombre_sim}' guardada")

        # SECCIÓN 8: Simulaciones Guardadas
        if 'simulaciones' in st.session_state and st.session_state.simulaciones:
            st.divider()
            st.subheader("8️⃣ Simulaciones Guardadas")

            for i, sim in enumerate(st.session_state.simulaciones):
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.write(f"**{sim['nombre']}** - {sim['empleado']}")
                    st.caption(
                        f"Compa: {sim['compa_ratio_actual']:.1f}% → {sim['compa_ratio_propuesto']:.1f}% | "
                        f"Incremento: ${sim['incremento_sueldo']:,.0f}/mes"
                    )

                with col2:
                    if st.button("🗑️", key=f"prop_delete_{i}"):
                        st.session_state.simulaciones.pop(i)
                        st.rerun()

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
