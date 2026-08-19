"""
Interfaz Streamlit para análisis de aumentos de renta.
"""

import streamlit as st
import pandas as pd
from typing import Optional
from datetime import datetime
from src.buk_client import BukClient
from src.analysis.data_loader import DataLoader
from src.analysis.db_manager import AnalysisDBManager
from src.analysis.salary_analyzer import SalaryAnalyzer
import logging

logger = logging.getLogger(__name__)


def show_analysis_section(buk_client: BukClient):
    """Muestra la sección de análisis de aumentos."""

    st.header("📊 Análisis de Aumentos de Renta")
    st.subheader("Suite de compensaciones ARP")

    # Inicializar BD
    db_manager = AnalysisDBManager()

    # SECCIÓN 1: Cargar datos
    st.divider()
    st.subheader("1️⃣ Cargar Datos desde Buk")
    st.info("ℹ️ **Solo se analizan empleados VIGENTES** (status = activo) con historial de sueldos")

    # Obtener empresas disponibles
    companies = buk_client.get_companies()
    if not companies:
        st.error("❌ No se pudieron obtener empresas de Buk")
        return

    company_dict = {comp["name"]: comp["id"] for comp in companies}
    company_names = list(company_dict.keys())

    # Selector de empresas
    st.subheader("Selecciona Empresas a Analizar")
    selected_companies = st.multiselect(
        "Elige una o más empresas:",
        options=company_names,
        default=[company_names[0]] if company_names else [],
        key="companies_to_load_select"
    )

    if not selected_companies:
        st.warning("⚠️ Selecciona al menos una empresa")
        return

    company_ids = [company_dict[name] for name in selected_companies]

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Cargar Empleados", width='stretch', type="primary"):
            with st.spinner(f"Cargando datos de {len(selected_companies)} empresa(s)..."):
                loader = DataLoader(buk_client, db_manager)
                loaded, errors, error_ruts = loader.load_all_employees(company_ids=company_ids)

                st.success(f"✅ Datos cargados exitosamente")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Empleados cargados", loaded)
                with col_b:
                    st.metric("Omitidos/Errores", errors)

                if error_ruts and len(error_ruts) <= 20:
                    st.info(f"RUTs omitidos (sin historial): {', '.join(error_ruts[:20])}")

    with col2:
        if st.button("🗑️ Limpiar Datos", width='stretch'):
            if db_manager.clear_data():
                st.success("✅ Datos eliminados")
                st.rerun()

    with col3:
        total_empleados = len(db_manager.get_analysis_by_empresa_area())
        st.metric("Empleados en BD", total_empleados)

    # SECCIÓN 2: Dashboard con filtros
    st.divider()
    st.subheader("2️⃣ Dashboard Analítico")

    # Obtener empresas y áreas para filtros
    empresas = db_manager.get_empresas()

    if not empresas:
        st.info("ℹ️ No hay datos cargados. Carga primero los empleados desde Buk.")
        return

    col1, col2 = st.columns(2)

    with col1:
        empresa_selected = st.selectbox("Selecciona Empresa:", ["Todas"] + empresas)
        empresa_filter = None if empresa_selected == "Todas" else empresa_selected

    with col2:
        areas = db_manager.get_areas(empresa_filter)
        area_selected = st.selectbox("Selecciona Área:", ["Todas"] + areas)
        area_filter = None if area_selected == "Todas" else area_selected

    # Obtener datos filtrados
    analyses = db_manager.get_analysis_by_empresa_area(empresa_filter, area_filter)
    metrics = db_manager.get_summary_metrics(empresa_filter, area_filter)

    # Calcular métricas avanzadas
    from src.analysis.metrics_calculator import AdvancedMetricsCalculator
    advanced_metrics = AdvancedMetricsCalculator.calculate_metrics(analyses)

    # Mostrar KPIs - Fila 1: Métricas Básicas
    st.divider()
    st.subheader("📈 Métricas Clave")

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        st.metric(
            "Total Empleados",
            metrics.get("total_empleados", 0),
            delta=None,
        )

    with kpi_col2:
        st.metric(
            "Aumento Invertido",
            f"${metrics.get('aumento_total_invertido', 0):,.0f}",
            delta=None,
        )

    with kpi_col3:
        st.metric(
            "Impacto Masa Salarial",
            f"{advanced_metrics.get('impacto_masa_salarial_pct', 0):.2f}%",
            delta=None,
        )

    with kpi_col4:
        st.metric(
            "Costo Anualizado",
            f"${advanced_metrics.get('costo_anualizado', 0):,.0f}",
            delta=None,
        )

    # Fila 2: Métricas de Estadística y Cobertura
    kpi_col5, kpi_col6, kpi_col7, kpi_col8 = st.columns(4)

    with kpi_col5:
        st.metric(
            "Mediana Aumento $",
            f"${advanced_metrics.get('mediana_aumento_monto', 0):,.0f}",
            delta=None,
        )

    with kpi_col6:
        st.metric(
            "Mediana Aumento %",
            f"{advanced_metrics.get('mediana_aumento_pct', 0):.1f}%",
            delta=None,
        )

    with kpi_col7:
        st.metric(
            "Concentración Top 3",
            f"{advanced_metrics.get('concentracion_top_3_pct', 0):.1f}%",
            delta=None,
        )

    with kpi_col8:
        st.metric(
            "Tasa de Cobertura",
            f"{advanced_metrics.get('tasa_cobertura_pct', 0):.1f}%",
            delta=None,
        )

    # Mostrar estadísticos detallados en expandible
    with st.expander("📊 Estadísticos Detallados"):
        stat_col1, stat_col2 = st.columns(2)

        with stat_col1:
            st.write("**Aumento ($) - Percentiles:**")
            st.write(f"- P25: ${advanced_metrics.get('p25_aumento_monto', 0):,.0f}")
            st.write(f"- Mediana: ${advanced_metrics.get('mediana_aumento_monto', 0):,.0f}")
            st.write(f"- P75: ${advanced_metrics.get('p75_aumento_monto', 0):,.0f}")
            st.write(f"- Desv. Est.: ${advanced_metrics.get('desv_est_aumento_monto', 0):,.0f}")

        with stat_col2:
            st.write("**Aumento (%) - Percentiles:**")
            st.write(f"- P25: {advanced_metrics.get('p25_aumento_pct', 0):.2f}%")
            st.write(f"- Mediana: {advanced_metrics.get('mediana_aumento_pct', 0):.2f}%")
            st.write(f"- P75: {advanced_metrics.get('p75_aumento_pct', 0):.2f}%")
            st.write(f"- Desv. Est.: {advanced_metrics.get('desv_est_aumento_pct', 0):.2f}%")

        st.write("**Antigüedad del Último Aumento:**")
        st.write(f"- Promedio: {advanced_metrics.get('antigüedad_promedio_meses_ultimo_aumento', 0):.1f} meses")

    # SECCIÓN 2B: Configurar Nivel HAY y Target manuales
    st.divider()
    st.subheader("2B️⃣ Configurar Nivel HAY y Target Manuales")
    st.caption("Ingresa valores manuales para empleados sin Nivel HAY o Target en el sistema")

    # Obtener lista de empleados sin filtros
    all_empleados = db_manager.get_analysis_by_empresa_area()

    if all_empleados:
        empleados_dict = {f"{emp.get('nombre')} ({emp.get('rut')})": emp for emp in all_empleados}
        empleado_manual = st.selectbox(
            "Selecciona empleado:",
            options=list(empleados_dict.keys()),
            key="manual_empleado_selector"
        )

        if empleado_manual:
            emp_data = empleados_dict[empleado_manual]
            rut = emp_data.get("rut", "")

            # Obtener valores manuales existentes
            manual_values = db_manager.get_manual_values(rut)
            nivel_hay_existente = manual_values.get("nivel_hay_manual") if manual_values else None
            target_existente = manual_values.get("target_manual") if manual_values else None

            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                nivel_hay_input = st.text_input(
                    "Nivel HAY:",
                    value=nivel_hay_existente or emp_data.get("nivel_hay") or "",
                    placeholder="Ej: 400, 450-500",
                    key=f"nivel_hay_{rut}"
                )

            with col2:
                target_input = st.text_input(
                    "Target (# de rentas):",
                    value=target_existente or emp_data.get("target") or "",
                    placeholder="Ej: 1.5, 2, 2.5",
                    key=f"target_{rut}"
                )

            with col3:
                if st.button("💾 Guardar", key=f"btn_save_{rut}"):
                    if nivel_hay_input or target_input:
                        if db_manager.save_manual_values(rut, nivel_hay_input or None, target_input or None):
                            st.success("✅ Valores guardados correctamente")
                            st.rerun()
                        else:
                            st.error("❌ Error al guardar")
                    else:
                        st.warning("⚠️ Ingresa al menos un valor")

        # Mostrar tabla de valores guardados
        manual_data = db_manager.get_all_manual_values()
        if manual_data:
            st.divider()
            st.subheader("📋 Valores Configurados Manualmente")

            # Enriquecer datos con información de empleados
            for record in manual_data:
                emp = next((e for e in all_empleados if e.get("rut") == record["rut"]), None)
                if emp:
                    record["nombre"] = emp.get("nombre", "")
                    record["cargo"] = emp.get("cargo_actual", "")

            df_manual = pd.DataFrame(manual_data)
            df_manual = df_manual[["rut", "nombre", "cargo", "nivel_hay_manual", "target_manual", "fecha_actualizacion"]]
            df_manual.columns = ["RUT", "Nombre", "Cargo", "Nivel HAY", "Target", "Última Actualización"]

            st.dataframe(df_manual, width='stretch', hide_index=True)

    # Gráficos
    st.divider()
    st.subheader("📊 Visualizaciones")

    if analyses:
        df = pd.DataFrame(analyses)

        # SECCIÓN 3: Tabla detallada
        st.divider()
        st.subheader("3️⃣ Tabla Detallada")
        st.caption("⚠️ Indicador: Sin aumento real (aumentos < 5%)")

        def calcular_antiguedad(fecha_ingreso_str):
            """Calcula antigüedad en años y meses desde fecha de ingreso."""
            if not fecha_ingreso_str:
                return "-"
            try:
                from datetime import datetime
                fecha_ingreso = datetime.strptime(fecha_ingreso_str[:10], "%Y-%m-%d")
                hoy = datetime.now()
                anos = (hoy.year - fecha_ingreso.year)
                meses = hoy.month - fecha_ingreso.month
                if meses < 0:
                    anos -= 1
                    meses += 12
                return f"{anos}a, {meses}m"
            except:
                return "-"

        def formato_fecha(fecha_str):
            """Convierte fecha yyyy-mm-dd a dd/mm/yyyy."""
            if not fecha_str:
                return "-"
            try:
                from datetime import datetime
                fecha = datetime.strptime(fecha_str[:10], "%Y-%m-%d")
                return fecha.strftime("%d/%m/%Y")
            except:
                return "-"

        # Inyectar CSS y JS para headers sticky
        st.markdown("""
        <style>
        /* Hacer los headers sticky */
        [data-testid="stVerticalBlockBorderWrapper"]:has(> [data-testid="stHorizontalBlock"]) > [data-testid="stHorizontalBlock"] {
            position: sticky;
            top: 0;
            background: white;
            z-index: 999;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        </style>
        <script>
        // Mantener headers visibles al scrollear
        document.addEventListener('DOMContentLoaded', function() {
            const headers = document.querySelectorAll('[data-testid="stHorizontalBlock"]');
            if(headers.length > 0) {
                headers[0].style.position = 'sticky';
                headers[0].style.top = '0';
                headers[0].style.backgroundColor = 'white';
                headers[0].style.zIndex = '999';
                headers[0].style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
            }
        });
        </script>
        """, unsafe_allow_html=True)

        # Paginación: cada fila genera ~24 elementos, así que renderizar
        # cientos de empleados de una vez satura el render y deja en blanco
        # las pestañas que vienen después de ANÁLISIS.
        FILAS_POR_PAGINA = 25
        total_filas = len(df)
        total_paginas = max(1, (total_filas + FILAS_POR_PAGINA - 1) // FILAS_POR_PAGINA)

        if total_paginas > 1:
            col_pag, col_info = st.columns([1, 3])
            with col_pag:
                pagina = st.number_input(
                    f"Página (de {total_paginas})",
                    min_value=1,
                    max_value=total_paginas,
                    value=1,
                    step=1,
                    key="tabla_detallada_pagina"
                )
            inicio = (pagina - 1) * FILAS_POR_PAGINA
            fin = min(inicio + FILAS_POR_PAGINA, total_filas)
            with col_info:
                st.caption(f"Mostrando {inicio + 1}-{fin} de {total_filas} empleados")
        else:
            inicio = 0
            fin = total_filas

        df_pagina = df.iloc[inicio:fin]

        # Headers fijos con scroll de contenido
        col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12 = st.columns([2, 1.2, 1.2, 1.6, 1.4, 1.4, 1.3, 1.2, 1.2, 1.2, 0.8, 0.8])

        with col1:
            st.write("**Nombre**")
        with col2:
            st.write("**F. Ingreso**")
        with col3:
            st.write("**Antigüedad**")
        with col4:
            st.write("**Cargo**")
        with col5:
            st.write("**Sueldo Inicial**")
        with col6:
            st.write("**Sueldo Actual**")
        with col7:
            st.write("**Aumento $**")
        with col8:
            st.write("**Aumento %**")
        with col9:
            st.write("**Nivel Hay**")
        with col10:
            st.write("**Target**")

        st.divider()

        for idx, row in df_pagina.iterrows():
            col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12 = st.columns([2, 1.2, 1.2, 1.6, 1.4, 1.4, 1.3, 1.2, 1.2, 1.2, 0.8, 0.8])

            nombre = row.get("nombre", "")
            sin_aumento_real = row.get("sin_aumento_real", False)
            indicador = " ⚠️" if sin_aumento_real else ""
            fecha_ingreso = row.get("fecha_ingreso", "")
            antiguedad = calcular_antiguedad(fecha_ingreso)
            rut = row.get("rut", "")

            with col1:
                st.write(f"{nombre}{indicador}")
            with col2:
                st.write(formato_fecha(fecha_ingreso))
            with col3:
                st.write(antiguedad)
            with col4:
                st.write(row.get("cargo_actual", ""))
            with col5:
                st.write(f"${row.get('sueldo_inicial', 0):,.0f}")
            with col6:
                st.write(f"${row.get('sueldo_actual', 0):,.0f}")
            with col7:
                st.write(f"${row.get('aumento_total', 0):,.0f}")
            with col8:
                st.write(f"{row.get('aumento_total_pct', 0):.1f}%")
            with col9:
                nivel = row.get("nivel_hay")
                st.write(nivel if (nivel and str(nivel).lower() != "nan") else "-")
            with col10:
                target = row.get("target")
                st.write(target if (target and str(target).lower() != "nan") else "-")
            with col11:
                if st.button("💰", key=f"prop_{idx}_{rut}", help="Crear propuesta de renta"):
                    # Guardar datos del empleado en session_state
                    st.session_state.empleado_para_propuesta = {
                        "rut": rut,
                        "nombre": nombre,
                        "sueldo_actual": row.get("sueldo_actual", 0),
                        "cargo": row.get("cargo_actual", ""),
                        "empresa": row.get("empresa", ""),
                        "edad": row.get("edad", ""),
                        "fecha_ingreso": row.get("fecha_ingreso", "")
                    }
                    st.session_state.main_tab = "propuestas"
                    st.session_state.propuestas_subtab = "propuesta"
                    st.rerun()
            with col12:
                if st.button("📋", key=f"btn_{idx}_{rut}", help="Ver historial"):
                    st.session_state[f"show_details_{idx}"] = not st.session_state.get(f"show_details_{idx}", False)

            # Mostrar detalles si está seleccionado
            if st.session_state.get(f"show_details_{idx}", False):
                with st.expander(f"📊 Historial de Aumentos - {row.get('nombre', '')}"):
                    try:
                        from src.buk_client import BukClient
                        import os
                        from dotenv import load_dotenv

                        load_dotenv()
                        buk = BukClient(os.getenv('BUK_API_TOKEN'), os.getenv('BUK_SUBDOMAIN'))
                        db = db_manager

                        # Obtener historial de sueldos
                        rut = row.get("rut")
                        salary_history = buk.get_salary_history(rut)

                        if salary_history:
                            hist_data = []
                            sobrepasa_ipc = []  # Rastrear qué filas sobrepasan IPC

                            for i, record in enumerate(salary_history):
                                fecha_inicio = record.get("start_date", "")
                                sueldo_actual = float(record.get('base_wage', 0))
                                periodo = fecha_inicio[:7] if fecha_inicio else "-"

                                # Calcular aumento vs periodo anterior
                                aumento_pct = 0.0
                                aumento_monto = 0
                                es_mayor_ipc = False

                                if i < len(salary_history) - 1:
                                    sueldo_anterior = float(salary_history[i + 1].get('base_wage', 0))
                                    if sueldo_anterior > 0 and sueldo_actual != sueldo_anterior:
                                        aumento_monto = sueldo_actual - sueldo_anterior
                                        aumento_pct = (aumento_monto / sueldo_anterior) * 100

                                        # Obtener IPC del mes del aumento
                                        ipc_bd = db.get_ipc(periodo)
                                        if ipc_bd is not None:
                                            ipc_valor = float(ipc_bd) * 100
                                            # Tolerancia de 0.1% para redondeos
                                            es_mayor_ipc = aumento_pct > (ipc_valor + 0.1)
                                        else:
                                            # Si no hay IPC registrado, asumir que sobrepasa
                                            es_mayor_ipc = True

                                        # Solo agregar si hay cambio de sueldo
                                        hist_data.append({
                                            "Período": periodo,
                                            "Sueldo Base": f"${sueldo_actual:,.0f}",
                                            "Variación ($)": f"${aumento_monto:,.0f}",
                                            "Variación (%)": f"{aumento_pct:+.1f}%",
                                            "_sobrepasa_ipc": es_mayor_ipc
                                        })
                                        sobrepasa_ipc.append(es_mayor_ipc)

                            if hist_data:
                                # Crear DataFrame sin la columna oculta para mostrar
                                hist_df_display = pd.DataFrame([{k: v for k, v in row.items() if k != "_sobrepasa_ipc"} for row in hist_data])

                                # Aplicar estilos
                                def estilo_fila(row):
                                    # Encontrar el índice de la fila en hist_data
                                    idx = row.name
                                    if idx < len(sobrepasa_ipc) and sobrepasa_ipc[idx]:
                                        # Celeste claro para filas que sobrepasan IPC
                                        return ['background-color: #B3E5FC'] * len(row)
                                    return [''] * len(row)

                                styled_df = hist_df_display.style.apply(estilo_fila, axis=1)
                                st.dataframe(styled_df, width='stretch', hide_index=True)
                                st.info(f"Total de períodos: {len(hist_data)}")
                                st.caption("🔵 Celeste = Aumento sobrepasa el IPC | Blanco = Aumento igual o menor al IPC")
                            else:
                                st.info("No hay historial de sueldos disponible")
                        else:
                            st.info("No se pudo obtener el historial de sueldos")

                    except Exception as e:
                        st.error(f"Error cargando historial: {str(e)}")

        # SECCIÓN 4: Exportar
        st.divider()
        st.subheader("4️⃣ Exportar Datos")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📥 Descargar Excel", width='stretch'):
                try:
                    from src.analysis.excel_exporter import ExcelExporter

                    exporter = ExcelExporter()
                    filename = f"Analisis_Aumentos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

                    success = exporter.export_analysis(
                        analyses=analyses,
                        metrics=metrics,
                        output_filename=filename,
                        empresa=empresa_selected,
                        area=area_selected,
                    )

                    if success:
                        with open(filename, "rb") as f:
                            st.download_button(
                                label="Descargar archivo",
                                data=f.read(),
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                        st.success("✅ Archivo generado")
                    else:
                        st.error("❌ Error al generar archivo")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        with col2:
            if st.button("🔌 JSON para API", width='stretch'):
                try:
                    import json

                    api_data = {
                        "fecha_exportacion": datetime.now().isoformat(),
                        "empresa": empresa_selected if empresa_selected != "Todas" else None,
                        "area": area_selected if area_selected != "Todas" else None,
                        "metricas": metrics,
                        "empleados": analyses[:100],  # Limitar a 100 para API
                    }

                    json_str = json.dumps(api_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="Descargar JSON",
                        data=json_str,
                        file_name=f"api_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                    )

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    else:
        st.info("ℹ️ No hay datos para mostrar con los filtros seleccionados")
