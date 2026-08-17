"""
Interfaz Streamlit para análisis de compensaciones.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from src.buk_client import BukClient
from src.analysis.db_manager import AnalysisDBManager
from src.analysis.compensation_calculator import CompensationCalculator
from src.utils.formatters import format_peso_chileno


def show_compensations_section(buk_client: BukClient):
    """Muestra la sección de análisis de compensaciones."""

    st.header("💰 Análisis de Compensaciones")
    st.subheader("Comparativa de Niveles HAY y Mercados")

    db_manager = AnalysisDBManager()

    # SECCIÓN 1: Verificar datos cargados
    st.divider()
    st.subheader("1️⃣ Estado de Datos")

    total_niveles = len(db_manager.get_compensation_levels())

    if total_niveles == 0:
        st.warning("⚠️ No hay tabla de compensaciones cargada. Ve a ⚙️ CONFIGURACIÓN → Tabla de Compensaciones para cargarla.")
        return

    col1, col2 = st.columns([3, 1])

    with col1:
        st.success(f"✅ Tabla de compensaciones cargada con {total_niveles} niveles")
        st.caption("Para actualizar, ve a ⚙️ CONFIGURACIÓN")

    with col2:
        st.metric("Niveles disponibles", total_niveles)

    # Obtener datos de compensaciones
    compensaciones = db_manager.get_compensation_levels()

    if not compensaciones:
        st.warning("⚠️ No hay datos de compensaciones cargados. Carga el archivo Excel primero.")
        return

    # SECCIÓN 2: Selector de empleado y configuración
    st.divider()
    st.subheader("2️⃣ Análisis de Compensación")

    # Obtener lista de empleados
    empleados = db_manager.get_analysis_by_empresa_area()

    if not empleados:
        st.info("ℹ️ No hay empleados cargados. Carga primero desde la pestaña de Análisis.")
        return

    # Crear diccionario empleado -> datos
    empleados_dict = {f"{emp.get('nombre')} ({emp.get('rut')})": emp for emp in empleados}

    # Selector de empleado
    empleado_seleccionado = st.selectbox(
        "Selecciona un empleado:",
        options=list(empleados_dict.keys())
    )

    if not empleado_seleccionado:
        return

    empleado = empleados_dict[empleado_seleccionado]

    # Primera fila: Área y Cargo
    col1, col2 = st.columns(2)

    with col1:
        area = empleado.get("area", "-")
        st.metric("Área", area if area else "-")

    with col2:
        cargo = empleado.get("cargo_actual", "-")
        st.metric("Cargo", cargo if cargo else "-")

    # Segunda fila: Nivel HAY, Target y Mercado
    col3, col4, col5 = st.columns(3)

    with col3:
        nivel_actual = empleado.get("nivel_hay")
        st.metric("Nivel HAY", nivel_actual if nivel_actual else "-")

    with col4:
        target = empleado.get("target")
        st.metric("Target", f"{target} Rentas" if target else "-")

    with col5:
        mercado_seleccionado = st.selectbox(
            "Mercado:",
            options=["Mercado Financiero", "Mercado Seguros"],
            key="mercado_selector"
        )

    # SECCIÓN 3: Cálculo de Compensación
    st.divider()
    st.subheader("3️⃣ Cálculo de Compensación")

    if not nivel_actual or not target:
        st.warning("⚠️ El empleado no tiene Nivel HAY o Target definido.")
        return

    try:
        nivel_actual = int(nivel_actual)
        target = float(target)
    except (ValueError, TypeError):
        st.error("❌ Nivel HAY o Target inválido")
        return

    # Obtener mes actual (para UF)
    hoy = datetime.now()
    mes_actual = hoy.strftime("%Y-%m")

    # Verificar que exista UF
    uf = db_manager.get_uf(mes_actual)
    if uf is None:
        st.warning(f"⚠️ No hay UF registrada para {mes_actual}. Por favor cárgala en configuración.")
        return

    # Crear calculador
    calculator = CompensationCalculator(db_manager)

    try:
        # Cargar parámetros de configuración para IMM
        import json
        with open("config/parameters.json") as f:
            params = json.load(f)
        imm_value = params.get("imm_value", 553_553)

        # Obtener sueldo base del empleado (es mensual)
        sueldo_base = empleado.get("sueldo_actual", 0)

        if not sueldo_base:
            st.error("❌ El empleado no tiene sueldo registrado")
            return

        # Crear calculador con IMM
        calculator = CompensationCalculator(db_manager, imm_value=imm_value)

        # Calcular compensación
        resultado = calculator.comparativa_completa(
            sueldo_base=sueldo_base,
            nivel_actual=nivel_actual,
            target=target,
            mes=mes_actual,
            mercado=mercado_seleccionado
        )

        # ===== DESGLOSE DE COMPONENTES (MENSUALIZADO) =====
        st.subheader("📊 Desglose de Compensación (Mensual)")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "Sueldo Base",
                format_peso_chileno(resultado['sueldo_base'])
            )

        with col2:
            st.metric(
                "Gratificación",
                format_peso_chileno(resultado['gratificacion']),
                f"(Anual: {format_peso_chileno(resultado['gratificacion_anual'])})"
            )

        with col3:
            st.metric(
                "Colación",
                format_peso_chileno(resultado['colacion'])
            )

        with col4:
            st.metric(
                "Movilización",
                format_peso_chileno(resultado['movilizacion'])
            )

        with col5:
            st.metric(
                "Target",
                format_peso_chileno(resultado['target'])
            )

        # Separador
        st.divider()

        # ===== MATRIZ DE PERCENTILES (ANÁLISIS TÉCNICO) =====
        st.subheader("📊 Matriz de Percentiles y Análisis Técnico")

        # Desglose de componentes (Imponibles vs No Imponibles)
        st.divider()
        st.subheader("📊 Desglose por Tipo de Componente")

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Total Cash (Imponibles)",
                format_peso_chileno(resultado.get('total_cash_anual', 0)),
                "Sueldo + Target (Base para benchmark)"
            )

        with col2:
            st.metric(
                "Haberes No Imponibles",
                format_peso_chileno(resultado.get('haberes_no_imponibles', 0)),
                "Colación + Movilización"
            )

        st.divider()

        # Tabla de percentiles (TOTAL CASH para comparativa Hay)
        percentiles_data = {
            "Percentil": ["P25 (Mínimo)", "P50 (Mediana)", "P75 (Máximo)", "Empleado"],
            "Valor Anual": [
                format_peso_chileno(resultado['p25']),
                format_peso_chileno(resultado['p50']),
                format_peso_chileno(resultado['p75']),
                format_peso_chileno(resultado.get('total_cash_anual', 0))
            ],
            "% del P50": ["80%", "100%", "120%", f"{resultado['compa_ratio']:.1f}%"]
        }

        df_percentiles = pd.DataFrame(percentiles_data)
        st.dataframe(df_percentiles, use_container_width=True, hide_index=True)

        # Métricas técnicas
        st.divider()
        st.subheader("⚙️ Métricas de Compensación")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Compa Ratio",
                f"{resultado['compa_ratio']:.1f}%",
                "Ideal: 95-105%"
            )

        with col2:
            st.metric(
                "Salary Spread",
                f"{resultado['salary_spread']:.1f}%",
                "Amplitud de banda"
            )

        with col3:
            st.metric(
                "Posición en Banda",
                f"{resultado.get('posicion_en_banda_pct', 0):.1f}%",
                "Penetración P25-P75"
            )

        with col4:
            # Color según compa ratio
            if resultado['compa_ratio'] < 90:
                color_comp = "🔴"
            elif resultado['compa_ratio'] <= 105:
                color_comp = "🟢"
            else:
                color_comp = "🔵"

            st.metric(
                "Análisis",
                f"{color_comp} {resultado['prioridad']}",
                resultado['recomendacion']
            )

        st.divider()

        # ===== TOTAL Y COMPARATIVA CON MERCADO (BANDAS) =====
        st.subheader("💰 Posición en Banda de Compensación")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Anualizado",
                format_peso_chileno(resultado['total']),
                f"(Mensual: {format_peso_chileno(resultado['total']/12)})"
            )

        with col2:
            st.metric(
                f"P50 Nivel {resultado['nivel_encontrado']}",
                format_peso_chileno(resultado['valor_nivel']),
                f"{resultado['descripcion_nivel']}"
            )

        with col3:
            st.metric(
                "Posición",
                f"{resultado.get('posicion_en_banda_pct', resultado.get('posicion_pct', 0)):.1f}%",
                "vs P50 (100%)"
            )

        with col4:
            st.metric(
                "Banda",
                resultado['estado'],
                resultado['banda']
            )

        # Barra visual de banda
        st.divider()
        posicion = resultado.get('posicion_en_banda_pct', resultado.get('posicion_pct', 0))

        if posicion < 90:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.error("BAJO MERCADO (80-90%)")
            with col2:
                st.markdown(f"Posición: **{posicion:.1f}%** del P50 — ⚠️ Necesita ajuste salarial para entrar en banda competitiva (90-105%)")
        elif posicion <= 105:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.success("EN BANDA (90-105%)")
            with col2:
                st.markdown(f"Posición: **{posicion:.1f}%** del P50 — ✅ Posición competitiva en el mercado. Puede crecer dentro de la banda")
        else:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.warning("SOBRE PAGADO (105%+)")
            with col2:
                st.markdown(f"Posición: **{posicion:.1f}%** del P50 — ⚠️ Costo elevado respecto al mercado. Revisar justificación")

        # Info detallada técnica
        st.divider()

        # Determinar color de alerta
        if resultado['compa_ratio'] < 90:
            st.error("ACCIÓN REQUERIDA - Posición bajo mercado")
        elif resultado['compa_ratio'] <= 105:
            st.success("POSICIÓN ÓPTIMA - En banda competitiva")
        else:
            st.warning("REVISAR ESTRUCTURA - Costo elevado vs mercado")

        st.info(
            f"""
            **Análisis Técnico de Compensación**

            **Datos del Empleado:**
            - Nombre: {empleado.get('nombre')}
            - Nivel HAY: {nivel_actual} ({resultado['descripcion_nivel']})
            - Target: {target} Rentas

            **Posición de Mercado:**
            - Compensación Anualizada: {format_peso_chileno(resultado['total'])}
            - Referencia P50 Nivel {nivel_actual}: {format_peso_chileno(resultado['valor_nivel'])}
            - Rango P25-P75: {format_peso_chileno(resultado['p25'])} — {format_peso_chileno(resultado['p75'])}
            - Mercado: {mercado_seleccionado}

            **Métricas de Compensación:**
            - Compa Ratio: {resultado['compa_ratio']:.1f}% (Ideal: 95-105%)
            - Salary Spread: {resultado['salary_spread']:.1f}%
            - Banda Actual: {resultado['banda']}

            **Recomendación:**
            - Prioridad: **{resultado['prioridad']}**
            - Acción: **{resultado['recomendacion']}**
            """
        )

    except ValueError as e:
        st.error(f"❌ Error en cálculo: {str(e)}")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

    # SECCIÓN 8: Tabla de todos los niveles
    st.divider()
    st.subheader("8️⃣ Tabla de Referencia - Todos los Niveles")

    # Crear DataFrame para mostrar
    tabla_datos = []
    for comp in compensaciones:
        tabla_datos.append({
            "Nivel": comp.get("nivel"),
            "Mercado Financiero": format_peso_chileno(comp.get('mercado_financiero', 0)) if comp.get('mercado_financiero') else "-",
            "Mercado Seguros": format_peso_chileno(comp.get('mercado_seguros', 0)) if comp.get('mercado_seguros') else "-",
            "Descripción": comp.get("descripcion", "-")
        })

    df_tabla = pd.DataFrame(tabla_datos)

    # Mostrar tabla con destaque del nivel actual y target
    st.dataframe(
        df_tabla,
        use_container_width=True,
        hide_index=True,
        height=400
    )

    # SECCIÓN 5: Análisis de Competitividad Interna
    st.divider()
    st.subheader("5️⃣ Análisis de Competitividad Interna")

    # Verificar si hay promedios calculados - intentar con diferentes formatos
    nivel_str = str(nivel_actual)
    promedios_internos = db_manager.get_compensation_average_by_level(nivel_str)

    # Debug: mostrar si hay promedios en BD
    todos_promedios = db_manager.get_compensation_averages()

    if not promedios_internos and todos_promedios:
        st.warning(f"⚠️ No hay promedio para nivel {nivel_str}. Niveles disponibles: {[p['nivel_hay'] for p in todos_promedios]}")

    if promedios_internos:
        from src.analysis.internal_competitiveness import InternalCompetitivenessCalculator

        calc_interno = InternalCompetitivenessCalculator(db_manager)
        comparativa_interna = calc_interno.comparar_empleado_vs_promedio(
            rut=empleado.get("rut"),
            nivel_hay=str(nivel_actual),
            compensacion_anual=resultado["total"]
        )

        if "error" not in comparativa_interna:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Compensación Empleado",
                    format_peso_chileno(comparativa_interna['empleado_anual'])
                )

            with col2:
                st.metric(
                    "Promedio Nivel",
                    format_peso_chileno(comparativa_interna['promedio_nivel']),
                    f"{comparativa_interna['diferencia_pct']:+.1f}%"
                )

            with col3:
                st.metric(
                    "Posición en Rango",
                    f"{comparativa_interna['posicion_en_rango_pct']:.1f}%",
                    f"de {comparativa_interna['cantidad_empleados_en_nivel']} empleados"
                )

            with col4:
                estado_color = comparativa_interna["color"]
                st.metric(
                    "Estado Interno",
                    comparativa_interna["estado"],
                    f"Rango: {format_peso_chileno(comparativa_interna['minimo_nivel'])} — {format_peso_chileno(comparativa_interna['maximo_nivel'])}"
                )

            st.divider()

            # Info de competitividad
            st.info(
                f"""
                **Análisis de Competitividad Interna (Nivel {nivel_actual})**

                - **Empleado Compensación:** {format_peso_chileno(comparativa_interna['empleado_anual'])}/año
                - **Promedio Nivel:** {format_peso_chileno(comparativa_interna['promedio_nivel'])}/año
                - **Diferencia:** {format_peso_chileno(comparativa_interna['diferencia'])} ({comparativa_interna['diferencia_pct']:+.1f}%)
                - **Rango del Nivel:** {format_peso_chileno(comparativa_interna['minimo_nivel'])} — {format_peso_chileno(comparativa_interna['maximo_nivel'])}
                - **Posición:** {comparativa_interna['posicion_en_rango_pct']:.1f}% (de {comparativa_interna['cantidad_empleados_en_nivel']} empleados)
                - **Estado:** {comparativa_interna['estado']}
                """
            )
        else:
            st.warning(f"⚠️ {promedios_internos.get('error', 'Sin datos')}")
    else:
        st.info("ℹ️ No hay promedios de compensación interna calculados aún. Ve a ⚙️ CONFIGURACIÓN para calcularlos.")

    st.divider()

    # SECCIÓN 6: Impacto de Incremento Propuesto
    st.divider()
    st.subheader("6️⃣ Impacto Presupuestario del Incremento Propuesto")

    incremento_propuesto = resultado.get('incremento_recomendado', 0)
    if incremento_propuesto > 0:
        incremento_mensual = incremento_propuesto / 12

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Incremento Mensual",
                format_peso_chileno(incremento_mensual),
                "Costo directo"
            )

        with col2:
            st.metric(
                "Incremento Anual",
                format_peso_chileno(incremento_propuesto),
                "Presupuesto requerido"
            )

        with col3:
            compa_nuevo = resultado['compa_ratio'] + (incremento_propuesto / resultado.get('valor_nivel', 1) * 100)
            st.metric(
                "Compa Ratio Después",
                f"{compa_nuevo:.1f}%",
                "Posición post-incremento"
            )

        with col4:
            impacto_pct = (incremento_propuesto / resultado.get('total_cash_anual', 1)) * 100
            st.metric(
                "% Incremento",
                f"{impacto_pct:.1f}%",
                "Sobre compensación actual"
            )

        st.info(
            f"""
            **Simulación de Incremento:**
            - Compensación actual (Total Cash): {format_peso_chileno(resultado.get('total_cash_anual', 0))}
            - Incremento sugerido: {format_peso_chileno(incremento_propuesto)} anual
            - Nueva compensación: {format_peso_chileno(resultado.get('total_cash_anual', 0) + incremento_propuesto)}
            - Nuevas posiciones: Compa Ratio {compa_nuevo:.1f}% (rango ideal: 95-105%)
            """
        )
    else:
        st.success("✅ Empleado dentro de banda - No requiere incremento")

    st.divider()

    # SECCIÓN 7: Análisis de impacto histórico
    st.subheader("7️⃣ Análisis Histórico y Contexto")

    sueldo_actual = empleado.get("sueldo_actual", 0)
    aumento_total = empleado.get("aumento_total", 0)
    aumento_pct = empleado.get("aumento_total_pct", 0)
    meses_en_empresa = empleado.get("meses_en_empresa", 0)
    meses_en_puesto = empleado.get("meses_en_puesto", 0)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Sueldo Base Actual",
            format_peso_chileno(sueldo_actual)
        )

    with col2:
        st.metric(
            "Aumento Total (Histórico)",
            format_peso_chileno(aumento_total),
            f"{aumento_pct:.1f}%"
        )

    with col3:
        años = int(meses_en_empresa // 12) if meses_en_empresa else 0
        meses = int(meses_en_empresa % 12) if meses_en_empresa else 0
        antigüedad_text = f"{años} años {meses} meses" if meses_en_empresa else "-"
        st.metric(
            "Antigüedad en la Empresa",
            antigüedad_text
        )

    # Información adicional
    st.info(
        f"""
        **Resumen Final:**
        - **Empleado:** {empleado.get('nombre')}
        - **Nivel HAY:** {nivel_actual} ({resultado['descripcion_nivel']})
        - **Target:** {target} Rentas
        - **Mercado Externo:** {mercado_seleccionado}
        - **Posición en Mercado:** {resultado.get('posicion_en_banda_pct', resultado.get('posicion_pct', 0)):.1f}% del P50 (Banda: {resultado['banda']})
        - **Estado Externo:** {resultado['estado']}
        """
    )

    # Botón para descargar PDF
    st.divider()
    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption("Exportar análisis a PDF")

    with col2:
        try:
            from src.analysis.pdf_compensation_exporter import CompensationPDFExporter

            exporter = CompensationPDFExporter(
                employee_data=empleado,
                compensation_data=resultado
            )
            pdf_buffer = exporter.generate_pdf()

            st.download_button(
                label="📄 Descargar PDF",
                data=pdf_buffer.getvalue(),
                file_name=f"analisis_compensacion_{empleado.get('rut').replace('.', '').replace('-', '')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error generando PDF: {str(e)}")
