"""Aplicación web de Propuestas de Renta con Streamlit."""

import streamlit as st
import os
import json
import pandas as pd
# v2.5 - Fix estacionamiento descuento en comparativa
from datetime import datetime
from dotenv import load_dotenv
from src.utils.formatters import format_peso_chileno

# Importar módulos de la aplicación
from src.buk_client import BukClient
from src.payroll_engine import PayrollEngine
from src.simulator import Simulator
from src.exporter import ExcelExporter
from src.pdf_exporter import PDFExporter
from src.pdf_exporter_calc import PDFExporterCalc

# Cargar variables de entorno
load_dotenv()

# Configuración de Streamlit
st.set_page_config(
    page_title="Suite ARP IA",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1F4E78;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)


def initialize_session_state():
    """Inicializa variables de sesión."""
    if "current_employee" not in st.session_state:
        st.session_state.current_employee = None
    if "comparison" not in st.session_state:
        st.session_state.comparison = None
    if "standard_proposals" not in st.session_state:
        st.session_state.standard_proposals = None
    if "org_changes" not in st.session_state:
        st.session_state.org_changes = {
            "company": None,
            "position": None,
            "supervisor": None
        }
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "main_tab" not in st.session_state:
        st.session_state.main_tab = "propuestas"
    if "propuestas_subtab" not in st.session_state:
        st.session_state.propuestas_subtab = "buscar"
    if "proposal_reasons" not in st.session_state:
        st.session_state.proposal_reasons = []


def get_buk_client():
    """Obtiene instancia del cliente Buk."""
    api_token = os.getenv("BUK_API_TOKEN")
    subdomain = os.getenv("BUK_SUBDOMAIN")

    if not api_token or not subdomain:
        st.error("❌ Variables de entorno BUK_API_TOKEN y BUK_SUBDOMAIN no configuradas")
        st.stop()

    return BukClient(api_token, subdomain)


def get_payroll_engine():
    """Obtiene instancia del motor de nómina."""
    with open("config/parameters.json") as f:
        parameters = json.load(f)
    return PayrollEngine(parameters)


def get_company_logo(company_name: str):
    """Obtiene la ruta del logo según la empresa."""
    try:
        with open("config/company_logos.json") as f:
            config = json.load(f)
            logo_path = config.get("company_logos", {}).get(company_name, "assets/logos/default.png")

            # Verificar si el archivo existe
            import os
            if os.path.exists(logo_path):
                return logo_path
    except:
        pass
    return None


@st.cache_data(ttl=3600)
def get_all_active_employees():
    """Obtiene todos los empleados activos (máximo 3 páginas)."""
    buk_client = get_buk_client()

    all_employees = []

    try:
        # Cargar máximo 3 páginas de 100 empleados cada una = 300 máximo
        for page in range(1, 4):
            employees = buk_client.list_employees(page=page, page_size=100)

            if not employees:
                break

            all_employees.extend(employees)

        if not all_employees:
            return []

        # Ordenar por empresa y luego por nombre
        all_employees_sorted = sorted(
            all_employees,
            key=lambda x: (x.company_name or "", x.full_name or "")
        )

        return all_employees_sorted

    except Exception as e:
        import logging
        logging.error(f"Error cargando empleados: {e}")
        return []


def search_employee_section():
    """Sección de búsqueda de empleados."""
    st.header("🔍 Buscar Colaborador")

    search_by = st.radio("Buscar por:", ["RUT", "Ver Todos"], horizontal=True)

    search_input = ""
    if search_by == "RUT":
        search_input = st.text_input("Ingrese RUT (ej: 12.345.678-9)").strip()

    if st.button("🔎 Buscar", use_container_width=True) or search_by == "Ver Todos":
        if search_by != "Ver Todos" and not search_input:
            st.warning("Por favor ingrese un valor para buscar")
            return

        with st.spinner("Cargando colaboradores..."):
            buk_client = get_buk_client()

            if search_by == "RUT":
                # Búsqueda por RUT - resultado único
                employee = buk_client.search_employee(rut=search_input)
                if employee:
                    st.session_state.current_employee = employee
                    st.success(f"✅ Colaborador encontrado: {employee.full_name}")
                    # Auto-navegar a Crear Propuesta
                    st.session_state.propuestas_subtab = "propuesta"
                    st.rerun()
                else:
                    st.error("❌ Colaborador no encontrado")
            elif search_by == "Ver Todos":
                # Obtener todos los empleados activos (cacheado por 1 hora)
                employees_sorted = get_all_active_employees()
                if employees_sorted:
                    st.session_state.search_results = employees_sorted
                    st.success(f"✅ Total de {len(employees_sorted)} colaborador(es) activo(s) (datos en caché)")
                else:
                    st.error("❌ No se encontraron colaboradores")

    # Mostrar resultados de búsqueda por apellido
    if st.session_state.search_results:
        st.divider()

        # Mini buscador en tiempo real
        col1, col2 = st.columns([4, 1])
        with col1:
            search_filter = st.text_input("🔎 Filtrar por nombre...", placeholder="Ej: Angel, Riquelme, etc", key="employee_filter")

        # Filtrar resultados
        if search_filter:
            filtered_results = [
                emp for emp in st.session_state.search_results
                if search_filter.lower() in emp.full_name.lower()
            ]
        else:
            filtered_results = st.session_state.search_results

        st.subheader(f"📋 Seleccione un colaborador: ({len(filtered_results)} de {len(st.session_state.search_results)})")

        for idx, employee in enumerate(filtered_results):
            col1, col2, col3, col4, col5 = st.columns([2, 1.5, 2, 2, 1])

            with col1:
                st.write(f"**{employee.full_name}**")
            with col2:
                st.write(employee.rut)
            with col3:
                st.write(employee.company_name)
            with col4:
                st.write(employee.job_title[:20] + "..." if employee.job_title and len(employee.job_title) > 20 else employee.job_title or "N/A")
            with col5:
                if st.button("Seleccionar", key=f"select_{idx}", use_container_width=True):
                    st.session_state.current_employee = employee
                    st.session_state.search_results = None
                    st.session_state.propuestas_subtab = "propuesta"
                    st.success(f"✅ {employee.full_name} seleccionado")
                    st.rerun()


def employee_card(employee):
    """Muestra tarjeta de información del empleado."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Nombre", employee.full_name)
    with col2:
        st.metric("RUT", employee.rut)
    with col3:
        st.metric("Empresa", employee.company_name)
    with col4:
        st.metric("Cargo", employee.job_title or "N/A")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sueldo Base", f"${employee.base_salary:,.0f}")
    with col2:
        st.metric("Jefe", employee.supervisor or "N/A")
    with col3:
        st.metric("Ingreso", employee.start_date or "N/A")


def proposal_section():
    """Sección de creación de propuesta."""
    if not st.session_state.current_employee:
        st.warning("⚠️ Seleccione un colaborador primero")
        return

    employee = st.session_state.current_employee

    # Mostrar header con logo si existe
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        logo_path = get_company_logo(employee.company_name)
        if logo_path:
            st.image(logo_path, width=80)
        else:
            st.info("Logo no disponible")

    with col_title:
        st.header(f"📝 Propuesta de Renta - {employee.full_name}")

    # Información del empleado en cards compactos
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("RUT", employee.rut)
    with col2:
        st.metric("Empresa", employee.company_name)
    with col3:
        st.metric("Cargo", employee.job_title[:25] + "..." if employee.job_title and len(employee.job_title) > 25 else employee.job_title or "N/A")
    with col4:
        st.metric("Sueldo Base", f"${employee.base_salary:,.0f}")

    st.divider()

    # Cambios organizacionales - Inline
    st.subheader("📋 Cambios Organizacionales")
    col1, col2, col3 = st.columns(3)

    with col1:
        change_company = st.checkbox("¿Cambiará de empresa?", key="change_company")
    with col2:
        change_position = st.checkbox("¿Cambiará de cargo?", key="change_position")
    with col3:
        change_supervisor = st.checkbox("¿Cambiará de jefatura?", key="change_supervisor")

    new_company = employee.company_name
    new_position = employee.job_title
    new_supervisor = employee.supervisor

    if change_company:
        buk_client = get_buk_client()
        companies = buk_client.get_companies()
        if companies:
            company_names = [c['name'] for c in companies]
            new_company = st.selectbox("Seleccione nueva empresa", company_names, label_visibility="collapsed")

    if change_position:
        new_position = st.text_input("Nuevo cargo", value=employee.job_title or "", label_visibility="collapsed")

    if change_supervisor:
        new_supervisor = st.text_input("Nuevo nombre de jefe", value=employee.supervisor or "", label_visibility="collapsed")

    st.divider()

    # Motivo de la propuesta
    st.subheader("🎯 Motivo de la Propuesta")
    motivos_options = [
        "Mérito",
        "Retención",
        "Ascenso",
        "Ampliación de responsabilidades",
        "Ajuste por mercado",
        "Equidad Interna"
    ]

    proposal_reasons = st.multiselect(
        "Seleccione los motivos aplicables:",
        motivos_options,
        key="proposal_reasons",
        placeholder="Elija uno o más motivos..."
    )

    st.divider()

    # Datos organizados en dos columnas
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("💵 Haberes Actuales")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("Colación")
            current_collation = st.number_input("Colación", value=0, min_value=0, label_visibility="collapsed", key="col_actual", step=1000)
            # Guardar en session_state para que otros campos lo lean
            st.session_state.current_collation = current_collation
        with col2:
            st.caption("Movilización")
            current_mobility = st.number_input("Movilización", value=0, min_value=0, label_visibility="collapsed", key="mob_actual", step=1000)
            st.session_state.current_mobility = current_mobility
        with col3:
            st.caption("Otros imponibles")
            current_other_taxable = st.number_input("Otros imponibles", value=0, min_value=0, label_visibility="collapsed", key="other_actual", step=1000)
            st.session_state.current_other_taxable = current_other_taxable

        # Checkbox para estacionamiento
        has_parking = st.checkbox("¿Tiene Estacionamiento?", key="has_parking", value=False)

        # Nivel HAY y Target Actual
        st.divider()
        st.caption("**Información de Compensación Actual**")

        # Nivel HAY
        nivel_actual_sistema = employee.get("nivel_hay") if isinstance(employee, dict) else getattr(employee, "nivel_hay", None)
        if nivel_actual_sistema:
            st.metric("Nivel HAY", nivel_actual_sistema)
        else:
            st.text_input(
                "Nivel HAY",
                value="",
                placeholder="Ej: 16, 18, 20",
                key="nivel_hay_actual_input",
                help="No hay Nivel HAY en el sistema. Ingresa manualmente."
            )

        # Target Actual
        target_actual_sistema = employee.get("target") if isinstance(employee, dict) else getattr(employee, "target", None)
        if target_actual_sistema and target_actual_sistema > 0:
            st.metric("Target (rentas)", f"{target_actual_sistema:.1f}")
        else:
            st.number_input(
                "Target en rentas",
                value=0.0,
                min_value=0.0,
                step=0.1,
                key="target_actual_input",
                help="No hay Target en el sistema. Ingresa manualmente (Ej: 2.8)."
            )

    with col_right:
        st.subheader("📊 Haberes Propuestos")

        payroll_engine = get_payroll_engine()

        # Opciones de entrada de sueldo
        input_type = st.radio(
            "¿Cómo ingresar el nuevo sueldo?",
            [
                "Sueldo base",
                "% sobre el sueldo base",
                "Sueldo Líquido",
                "% sobre el sueldo líquido"
            ],
            horizontal=True
        )

        # Calcular líquido actual para referencias
        # Ajustar movilidad si tiene estacionamiento
        mobility_for_calc = current_mobility
        if has_parking and mobility_for_calc > 0:
            mobility_for_calc = 0  # Descuento total de movilización si tiene estacionamiento

        current_payroll = payroll_engine.calculate(
            base_salary=employee.base_salary,
            collation=current_collation,
            mobility=mobility_for_calc,
            other_taxable=current_other_taxable,
            contract_type=employee.contract_type,
            pension_fund=employee.pension_fund,
        )
        current_liquid = current_payroll.net_salary

        if input_type == "Sueldo base":
            st.caption("Nuevo Sueldo Base")
            proposal_base_salary = st.number_input(
                "Nuevo Sueldo Base",
                value=int(employee.base_salary),
                min_value=0,
                label_visibility="collapsed",
                key="base_direct"
            )

        elif input_type == "% sobre el sueldo base":
            st.caption("Porcentaje de aumento sobre Sueldo Base")
            porcentaje_aumento = st.number_input(
                "Porcentaje (%)",
                value=0.0,
                min_value=0.0,
                step=0.1,
                label_visibility="collapsed",
                key="percent_base"
            )
            proposal_base_salary = int(employee.base_salary * (1 + porcentaje_aumento / 100))
            st.info(f"**Base actual:** ${employee.base_salary:,.0f} → **Nueva base:** ${proposal_base_salary:,.0f}")

        elif input_type == "Sueldo Líquido":
            st.caption("Sueldo Líquido a Recibir")
            target_liquid = st.number_input(
                "Sueldo Líquido ($)",
                value=int(current_liquid),
                min_value=0,
                label_visibility="collapsed",
                key="target_liquid"
            )
            if target_liquid > 0:
                proposal_base_salary = payroll_engine.reverse_calculate_base_salary(
                    target_net_salary=target_liquid,
                    collation=current_collation,
                    mobility=current_mobility,
                    contract_type=employee.contract_type,
                    pension_fund=employee.pension_fund,
                    has_parking=has_parking,
                )
            else:
                proposal_base_salary = employee.base_salary
            st.info(f"**Líquido actual:** ${current_liquid:,.0f} → **Líquido objetivo:** ${target_liquid:,.0f}")

        else:  # % sobre el sueldo líquido
            st.caption("Porcentaje de aumento sobre Sueldo Líquido")
            porcentaje_liquido = st.number_input(
                "Porcentaje (%)",
                value=0.0,
                min_value=0.0,
                step=0.1,
                label_visibility="collapsed",
                key="percent_liquid"
            )
            target_liquid = current_liquid * (1 + porcentaje_liquido / 100)
            proposal_base_salary = payroll_engine.reverse_calculate_base_salary(
                target_net_salary=target_liquid,
                collation=current_collation,
                mobility=current_mobility,
                contract_type=employee.contract_type,
                pension_fund=employee.pension_fund,
                has_parking=has_parking,
            )
            st.info(f"**Líquido actual:** ${current_liquid:,.0f} → **Líquido objetivo:** ${target_liquid:,.0f}")

        st.caption("Base tomada del lado izquierdo (modificar si es necesario)")
        col1, col2, col3 = st.columns(3)

        # Leer valores de session_state para mantener sincronización
        base_collation = st.session_state.get("current_collation", current_collation)
        base_mobility = st.session_state.get("current_mobility", current_mobility)
        base_other_taxable = st.session_state.get("current_other_taxable", current_other_taxable)
        has_parking = st.session_state.get("has_parking", False) if "has_parking" in st.session_state else False

        # Calcular descuentos de estacionamiento
        current_parking_discount = 0
        if has_parking and current_mobility > 0:
            current_parking_discount = current_mobility  # Descuento total de movilización si tiene estacionamiento

        # Checkbox para estacionamiento en propuesta (ANTES de usarlo en labels)
        proposal_has_parking = st.checkbox("¿Tendrá Estacionamiento?", key="proposal_parking", value=has_parking)

        with col1:
            st.caption("Colación")
            proposal_collation = st.number_input("Colación", value=int(base_collation), min_value=0, label_visibility="collapsed", key="col_prop", step=1000)
        with col2:
            mobility_label = "Movilización" + (" (menos estacionamiento)" if proposal_has_parking else "")
            st.caption(mobility_label)
            proposal_mobility = st.number_input("Movilización", value=int(base_mobility), min_value=0, label_visibility="collapsed", key="mob_prop", step=1000)
        with col3:
            st.caption("Otros imponibles")
            proposal_other_taxable = st.number_input("Otros imponibles", value=int(base_other_taxable), min_value=0, label_visibility="collapsed", key="other_prop", step=1000)

        # Calcular descuento de estacionamiento propuesto (basado en movilización ORIGINAL, no la modificada)
        proposal_parking_discount = 0
        if proposal_has_parking and base_mobility > 0:
            proposal_parking_discount = base_mobility  # Descuento total de movilización si tendrá estacionamiento

        # Nivel HAY y Target Propuesta
        st.divider()
        st.caption("**Información de Compensación Propuesta**")

        # Nivel HAY Propuesta (prefill con actual si existe)
        default_nivel = st.session_state.get("nivel_hay_actual_input", "")
        st.text_input(
            "Nivel HAY Propuesta",
            value=default_nivel,
            placeholder="Ej: 16, 18, 20",
            key="nivel_hay_prop_input",
            help="Nivel HAY para la propuesta (puede ser igual al actual o diferente si hay promoción)."
        )

        # Target Propuesta (prefill con actual si existe)
        default_target = st.session_state.get("target_actual_input", 0.0)
        st.number_input(
            "Target Propuesta (rentas)",
            value=default_target,
            min_value=0.0,
            step=0.1,
            key="target_prop_input",
            help="Target en rentas para la propuesta (Ej: 2.8, 3.0, etc.)."
        )

    st.divider()

    # Mercado para Comparativa
    st.subheader("📊 Comparativa de Mercado")
    mercado_comparacion = st.selectbox(
        "Tipo de Mercado",
        options=["Mercado Financiero", "Mercado Seguros"],
        key="mercado_comparacion_main",
        help="Selecciona el mercado para comparar la compensación."
    )

    st.divider()

    # Fecha de aplicación
    col1, col2 = st.columns([1, 4])
    with col1:
        change_date = st.date_input("Fecha aplicación", value=datetime.now(), label_visibility="collapsed")

    # Mostrar fecha en formato visual "Mes Año"
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_nombre = meses[change_date.month - 1]
    fecha_visual = f"{mes_nombre} {change_date.year}"

    with col2:
        st.write(f"**{fecha_visual}**")

    change_date_str = change_date.strftime("%d/%m/%Y")

    st.divider()

    # Botón para crear propuesta
    if st.button("✅ Crear Propuesta", use_container_width=True, type="primary"):
        with st.spinner("Calculando propuesta..."):
            simulator = Simulator(payroll_engine)

            # Guardar datos organizacionales
            st.session_state.org_changes = {
                "company": new_company,
                "position": new_position,
                "supervisor": new_supervisor
            }

            # Guardar estacionamiento propuesto
            st.session_state.proposal_has_parking = proposal_has_parking

            # Guardar datos de compensación (usar keys correctas de los widgets)
            st.session_state.compensation_data = {
                "nivel_hay_actual": st.session_state.get("nivel_hay_actual_input", ""),
                "nivel_hay_propuesta": st.session_state.get("nivel_hay_prop_input", ""),
                "target_actual": st.session_state.get("target_actual_input", 0.0),
                "target_propuesta": st.session_state.get("target_prop_input", 0.0),
                "mercado": mercado_comparacion
            }

            # Crear comparativa
            comparison = simulator.compare(
                employee_name=employee.full_name,
                employee_rut=employee.rut,
                change_date=change_date_str,
                current_base_salary=employee.base_salary,
                proposal_base_salary=proposal_base_salary,
                contract_type=employee.contract_type,
                current_collation=current_collation,
                current_mobility=current_mobility,
                current_other_taxable=current_other_taxable,
                proposal_collation=proposal_collation,
                proposal_mobility=proposal_mobility,
                proposal_other_taxable=proposal_other_taxable,
                pension_fund=employee.pension_fund,
                current_parking_discount=current_parking_discount,
                proposal_parking_discount=proposal_parking_discount,
            )

            # Calcular propuestas estándar
            standard_proposals = simulator.calculate_standard_proposals(
                employee_name=employee.full_name,
                employee_rut=employee.rut,
                change_date=change_date_str,
                current_base_salary=employee.base_salary,
                contract_type=employee.contract_type,
                current_collation=current_collation,
                current_mobility=current_mobility,
                current_other_taxable=current_other_taxable,
                pension_fund=employee.pension_fund,
            )

            st.session_state.comparison = comparison
            st.session_state.standard_proposals = standard_proposals
            st.session_state.propuestas_subtab = "comparativa"

            st.success("✅ Propuesta calculada exitosamente")
            st.rerun()
            st.rerun()


@st.cache_data
def calculate_compensation_metrics(base_salary_actual, base_salary_proposal, target_actual, target_propuesta, nivel_hay_actual, nivel_hay_propuesta, mercado):
    """Calcula métricas de compensación con caching."""
    try:
        from src.analysis.db_manager import AnalysisDBManager
        from src.compensation_comparator import CompensationComparator, CompensationScenario

        db_manager = AnalysisDBManager()
        payroll = get_payroll_engine()
        comparador = CompensationComparator(db_manager, payroll)

        actual = CompensationScenario(
            base_salary=base_salary_actual,
            target_rentas=float(target_actual) if target_actual else 0.0,
            nivel_hay=str(nivel_hay_actual) if nivel_hay_actual else "0",
            mercado=mercado,
            months=12
        )

        propuesta = CompensationScenario(
            base_salary=base_salary_proposal,
            target_rentas=float(target_propuesta) if target_propuesta else 0.0,
            nivel_hay=str(nivel_hay_propuesta) if nivel_hay_propuesta else str(nivel_hay_actual) if nivel_hay_actual else "0",
            mercado=mercado,
            months=12
        )

        return comparador.compare(actual, propuesta)
    except Exception as e:
        return None


def comparison_section(payroll_engine=None):
    """Sección de visualización de comparativa."""
    if payroll_engine is None:
        payroll_engine = get_payroll_engine()

    if not st.session_state.comparison:
        st.info("ℹ️ Cree una propuesta primero")
        return

    comparison = st.session_state.comparison
    employee = st.session_state.current_employee

    # Mostrar header con logo si existe
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        logo_path = get_company_logo(employee.company_name)
        if logo_path:
            st.image(logo_path, width=80)
        else:
            st.info("Logo no disponible")

    with col_title:
        st.header(f"📊 Comparativa - {employee.full_name}")

    # Información organizacional
    st.subheader("Información de Empresa, Cargo, Jefe")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("**Item**")
        st.write("Empresa")
        st.write("Descripción Cargo")
        st.write("Nombre Jefe")
    with col2:
        st.write("**Actual**")
        st.write(employee.company_name)
        st.write(employee.job_title or "N/A")
        st.write(employee.supervisor or "N/A")
    with col3:
        st.write("**Propuesta**")
        st.write(st.session_state.org_changes.get("company", employee.company_name))
        st.write(st.session_state.org_changes.get("position", employee.job_title or "N/A"))
        st.write(st.session_state.org_changes.get("supervisor", employee.supervisor or "N/A"))

    st.divider()

    # Tabla de comparación
    st.subheader("Comparativo de Haberes y Descuentos")

    items = comparison.get_comparison_items()

    comp_data = []
    for concept, values in items.items():
        actual = values["actual"]
        proposal = values["proposal"]
        variation = proposal - actual
        variation_pct = (variation / actual * 100) if actual != 0 else 0

        comp_data.append({
            "Concepto": concept,
            "Actual": f"${actual:,.0f}",
            "Propuesta": f"${proposal:,.0f}",
            "Variación ($)": f"${variation:,.0f}",
            "Variación (%)": f"{variation_pct:.1f}%"
        })

    import pandas as pd
    df_comparison = pd.DataFrame(comp_data)
    st.dataframe(df_comparison, use_container_width=True, hide_index=True)

    st.divider()

    # Resumen de impacto
    st.subheader("📈 Resumen de Impacto")

    col1, col2 = st.columns(2)

    net_salary_impact = comparison.proposal.net_salary - comparison.current.net_salary
    employer_impact = comparison.proposal.total_employer_cost - comparison.current.total_employer_cost

    with col1:
        st.metric(
            "Impacto Sueldo Líquido",
            f"${net_salary_impact:,.0f}",
            f"{(net_salary_impact/comparison.current.net_salary*100):.1f}%" if comparison.current.net_salary > 0 else "0%"
        )
    with col2:
        st.metric(
            "Impacto Costo Empresa",
            f"${employer_impact:,.0f}",
            f"{(employer_impact/comparison.current.total_employer_cost*100):.1f}%" if comparison.current.total_employer_cost > 0 else "0%"
        )

    st.divider()

    # Compensación Anual - DESHABILITADO TEMPORALMENTE (causa bloqueos)
    # TODO: Optimizar calculate_compensation_metrics para que no bloquee
    if "compensation_data" in st.session_state and (st.session_state.compensation_data.get("nivel_hay_actual") or st.session_state.compensation_data.get("nivel_hay_propuesta")):
        st.subheader("💰 Análisis de Compensación Anual")

        comp_data = st.session_state.compensation_data

        # Mostrar resumen simple sin bloqueos
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nivel HAY Actual", comp_data.get("nivel_hay_actual", "—"))
        with col2:
            st.metric("Target Actual", f"{comp_data.get('target_actual', 0.0):.1f} rentas")
        with col3:
            st.metric("Mercado", comp_data.get("mercado", "—"))

        st.info("ℹ️ El análisis detallado de Compratio y Mediana está en desarrollo para optimizar el rendimiento.")

        st.divider()

    # Historial de Sueldos
    st.subheader("📈 Historial de Sueldos")

    buk_client = get_buk_client()
    salary_history = buk_client.get_salary_history(employee.rut)

    if salary_history:
        # Preparar datos para tabla
        import pandas as pd

        # Filtrar registros: excluir mayo 2019 y anteriores
        filtered_history = [record for record in salary_history if record.get("start_date", "")[:7] > "2019-05"]

        history_data = []
        for i, record in enumerate(filtered_history):
            start = record.get("start_date", "")
            wage = record.get("base_wage", 0)

            # Extraer solo mes y año del start_date (formato YYYY-MM-DD)
            periodo = start[:7] if start else "N/A"

            # Calcular variación respecto al mes anterior (el siguiente en la lista ordenada al revés)
            variation = ""
            variation_pct = ""
            skip_record = False

            if i < len(filtered_history) - 1:  # Si no es el último (más antiguo)
                prev_wage = filtered_history[i + 1].get("base_wage")
                if prev_wage:
                    change = wage - prev_wage
                    change_pct = (change / prev_wage * 100) if prev_wage > 0 else 0

                    # Omitir registros sin variación
                    if change == 0:
                        skip_record = True
                    else:
                        variation = f"${change:,.0f}"
                        variation_pct = f"{change_pct:+.1f}%"

            if not skip_record:
                history_data.append({
                    "Periodo": periodo,
                    "Sueldo Base": f"${wage:,.0f}",
                    "Variación ($)": variation,
                    "Variación (%)": variation_pct,
                })

        df = pd.DataFrame(history_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Resumen (usando datos filtrados)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Periodos", len(filtered_history))
        with col2:
            if len(filtered_history) > 1:
                first_wage = filtered_history[-1].get("base_wage", 0)
                current_wage = filtered_history[0].get("base_wage", 0)
                total_increase = current_wage - first_wage
                total_increase_pct = (total_increase / first_wage * 100) if first_wage > 0 else 0
                st.metric("Aumento Total", f"${total_increase:,.0f}", f"{total_increase_pct:+.1f}%")
        with col3:
            if len(filtered_history) > 0:
                current = filtered_history[0].get("base_wage", 0)
                first = filtered_history[-1].get("base_wage", 0)
                st.metric("Sueldo Inicial", f"${first:,.0f}")
    else:
        st.info("No se encontró historial de sueldos")

    st.divider()

    # Exportar
    st.subheader("💾 Exportar Propuesta")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Descargar Excel", use_container_width=True):
            filename = f"Propuesta_Renta_{employee.rut.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            excel_exporter = ExcelExporter()

            success = excel_exporter.export_comparison(
                comparison=comparison,
                output_filename=filename,
                company_name=employee.company_name,
                prepared_by="Recursos Humanos",
                standard_proposals=st.session_state.standard_proposals,
                current_company=employee.company_name,
                current_position=employee.job_title or "",
                current_supervisor=employee.supervisor or "",
                proposal_company=st.session_state.org_changes.get("company", employee.company_name),
                proposal_position=st.session_state.org_changes.get("position", employee.job_title or ""),
                proposal_supervisor=st.session_state.org_changes.get("supervisor", employee.supervisor or ""),
                salary_history=salary_history,
                proposal_reasons=st.session_state.get("proposal_reasons", []),
            )

            if success:
                with open(filename, "rb") as f:
                    st.download_button(
                        label="Descargar archivo Excel",
                        data=f.read(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                st.success("✅ Excel generado correctamente")
            else:
                st.error("❌ Error al generar Excel")

    with col2:
        if st.button("📑 Descargar PDF", use_container_width=True):
            filename = f"Propuesta_Renta_{employee.rut.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_exporter = PDFExporter()

            # Obtener logo de la empresa
            logo_path = get_company_logo(employee.company_name)

            success = pdf_exporter.export_comparison(
                comparison=comparison,
                output_filename=filename,
                company_name=employee.company_name,
                prepared_by="Recursos Humanos",
                current_company=employee.company_name,
                current_position=employee.job_title or "",
                current_supervisor=employee.supervisor or "",
                proposal_company=st.session_state.org_changes.get("company", employee.company_name),
                proposal_position=st.session_state.org_changes.get("position", employee.job_title or ""),
                proposal_supervisor=st.session_state.org_changes.get("supervisor", employee.supervisor or ""),
                logo_path=logo_path,
                salary_history=salary_history,
                proposal_reasons=st.session_state.get("proposal_reasons", []),
            )

            if success:
                with open(filename, "rb") as f:
                    st.download_button(
                        label="Descargar archivo PDF",
                        data=f.read(),
                        file_name=filename,
                        mime="application/pdf"
                    )
                st.success("✅ PDF generado correctamente")
            else:
                st.error("❌ Error al generar PDF")


def configuration_section():
    """Sección de configuración de parámetros."""
    import json

    st.header("⚙️ Configuración de Parámetros")

    with open("config/parameters.json") as f:
        parameters = json.load(f)

    # Dividir en columnas para mejor visualización
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📊 Valores Mensuales")
        uf_value = st.number_input(
            "UF Value",
            value=float(parameters.get("uf_value", 40873.77)),
            step=0.01,
            format="%.2f"
        )
        utm_value = st.number_input(
            "UTM Value",
            value=int(parameters.get("utm_value", 67000)),
            step=1000
        )
        imm_value = st.number_input(
            "IMM Value",
            value=int(parameters.get("imm_value", 553553)),
            step=1000
        )

    with col2:
        st.subheader("📏 Topes Previsionales")
        tope_afp_uf = st.number_input(
            "Tope AFP (UF)",
            value=parameters.get("tope_afp_uf", 90.0),
            step=0.1,
            format="%.1f"
        )
        tope_afc_uf = st.number_input(
            "Tope AFC (UF)",
            value=parameters.get("tope_afc_uf", 126.6),
            step=0.1,
            format="%.1f"
        )

    with col3:
        st.subheader("📈 Porcentajes")
        afp_percent = st.number_input(
            "AFP %",
            value=parameters.get("afp_percent", 10.0),
            step=0.1,
            format="%.1f"
        )
        salud_percent = st.number_input(
            "Salud %",
            value=parameters.get("salud_percent", 7.0),
            step=0.1,
            format="%.1f"
        )
        afc_indefinido = st.number_input(
            "AFC Indefinido %",
            value=parameters.get("afc_trabajador_indefinido", 0.6),
            step=0.1,
            format="%.1f"
        )

    # Botón para guardar cambios
    if st.button("💾 Guardar Cambios", use_container_width=True, type="primary"):
        # Actualizar parámetros
        parameters["uf_value"] = uf_value
        parameters["utm_value"] = utm_value
        parameters["imm_value"] = imm_value
        parameters["tope_afp_uf"] = tope_afp_uf
        parameters["tope_afc_uf"] = tope_afc_uf
        parameters["afp_percent"] = afp_percent
        parameters["salud_percent"] = salud_percent
        parameters["afc_trabajador_indefinido"] = afc_indefinido

        # Guardar en archivo
        with open("config/parameters.json", "w") as f:
            json.dump(parameters, f, indent=2)

        st.success("✅ Parámetros actualizados correctamente")
        st.balloons()

    st.divider()

    st.info("💡 **Edita los valores manualmente** (UF, UTM, IMM) en los campos arriba y haz clic en '💾 Guardar Cambios' para actualizar")

    st.divider()

    # Mostrar tabla resumen
    st.subheader("📋 Resumen Actual")
    summary_data = {
        "Parámetro": ["UF", "UTM", "IMM", "Tope AFP (UF)", "Tope AFC (UF)"],
        "Valor": [
            f"${uf_value:,.2f}",
            f"${utm_value:,.0f}",
            f"${imm_value:,.0f}",
            f"{tope_afp_uf:.1f} UF",
            f"{tope_afc_uf:.1f} UF"
        ]
    }

    import pandas as pd
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

    st.divider()

    # Sección de IPC
    st.subheader("📊 Histórico de IPC")

    from src.analysis.db_manager import AnalysisDBManager
    db = AnalysisDBManager()

    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption("Agregar/Actualizar IPC para nuevo mes")
        col_mes, col_val, col_btn = st.columns([2, 2, 1])
        with col_mes:
            new_mes = st.text_input("Mes (YYYY-MM):", placeholder="2026-09", key="new_ipc_mes")
        with col_val:
            new_ipc = st.number_input("Valor IPC:", min_value=0.0, step=0.0001, format="%.4f", key="new_ipc_val")
        with col_btn:
            st.write("")  # Spacing
            if st.button("Guardar IPC", use_container_width=True, key="save_ipc_btn"):
                if new_mes and new_ipc > 0:
                    if db.upsert_ipc(new_mes, new_ipc):
                        st.success(f"✅ IPC {new_mes}: {new_ipc:.4f} guardado")
                        st.rerun()
                    else:
                        st.error("Error al guardar IPC")
                else:
                    st.warning("Ingresa mes y valor válidos")

    with col2:
        st.write("")  # Spacing
        if st.button("🔄 Recargar", use_container_width=True, key="reload_ipc"):
            st.rerun()

    st.divider()

    # Mostrar tabla de IPCs
    ipc_history = db.get_ipc_history()

    if ipc_history:
        df_ipc = pd.DataFrame(ipc_history)
        df_ipc.columns = ["Mes", "IPC"]
        df_ipc["IPC (%)"] = df_ipc["IPC"].apply(lambda x: f"{float(x):.4f}")
        df_ipc = df_ipc[["Mes", "IPC (%)"]]

        st.caption(f"Total de registros: {len(ipc_history)}")
        st.dataframe(df_ipc, use_container_width=True, hide_index=True)
    else:
        st.info("No hay IPCs registrados")

    st.divider()

    # Sección de Compensaciones
    st.subheader("💰 Tabla de Compensaciones por Nivel")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption("Carga/Actualiza tabla de compensaciones")
        uploaded_comp = st.file_uploader(
            "📥 Selecciona archivo Excel",
            type=["xlsx", "xls"],
            key="comp_uploader",
            help="Columnas: Nivel | Mercado Financiero | Mercado Seguros | Descripción"
        )

        if uploaded_comp is not None:
            try:
                df_comp = pd.read_excel(uploaded_comp)
                st.success(f"✅ Archivo cargado: {len(df_comp)} niveles")

                with st.expander("👁️ Vista previa"):
                    st.dataframe(df_comp, use_container_width=True, hide_index=True)

                if st.button("💾 Guardar en Base de Datos", type="primary", use_container_width=True, key="save_comp_btn"):
                    with st.spinner("Cargando compensaciones..."):
                        insertados = 0
                        errores = 0

                        for idx, row in df_comp.iterrows():
                            try:
                                nivel = int(row.iloc[0])
                                mercado_financiero = float(row.iloc[1]) if len(row) > 1 and pd.notna(row.iloc[1]) else None
                                mercado_seguros = float(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else None
                                descripcion = str(row.iloc[3]) if len(row) > 3 and pd.notna(row.iloc[3]) else None

                                if db.upsert_compensation_level(nivel, mercado_financiero, mercado_seguros, descripcion):
                                    insertados += 1
                                else:
                                    errores += 1
                            except Exception as e:
                                st.warning(f"Error en fila {idx + 2}: {str(e)}")
                                errores += 1

                        st.success(f"✅ Guardado: {insertados} niveles, {errores} errores")
                        st.rerun()

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    with col2:
        total_comp = len(db.get_compensation_levels())
        st.metric("Niveles en BD", total_comp)

    st.divider()

    # Mostrar tabla actual de compensaciones
    compensaciones = db.get_compensation_levels()

    if compensaciones:
        df_comp_display = pd.DataFrame(compensaciones)
        df_comp_display = df_comp_display[["nivel", "mercado_financiero", "mercado_seguros", "descripcion"]]
        df_comp_display.columns = ["Nivel", "Mercado Financiero", "Mercado Seguros", "Descripción"]

        st.caption(f"Total registros: {len(compensaciones)}")
        st.dataframe(df_comp_display, use_container_width=True, hide_index=True)
    else:
        st.info("No hay compensaciones cargadas. Carga un archivo Excel.")

    st.divider()

    # Sección de UF
    st.subheader("💵 Histórico de UF (Unidad de Fomento)")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption("Agregar/Actualizar UF para nuevo mes")
        col_mes, col_val, col_btn = st.columns([2, 2, 1])
        with col_mes:
            new_mes_uf = st.text_input("Mes (YYYY-MM):", placeholder="2026-08", key="new_uf_mes")
        with col_val:
            new_uf = st.number_input("Valor UF:", min_value=0.0, step=0.01, format="%.2f", key="new_uf_val")
        with col_btn:
            st.write("")  # Spacing
            if st.button("Guardar UF", use_container_width=True, key="save_uf_btn"):
                if new_mes_uf and new_uf > 0:
                    if db.upsert_uf(new_mes_uf, new_uf):
                        st.success(f"✅ UF {new_mes_uf}: ${new_uf:,.2f} guardada")
                        st.rerun()
                    else:
                        st.error("Error al guardar UF")
                else:
                    st.warning("Ingresa mes y valor válidos")

    with col2:
        st.write("")  # Spacing
        if st.button("🔄 Recargar", use_container_width=True, key="reload_uf"):
            st.rerun()

    st.divider()

    # Mostrar tabla de UF
    uf_history = db.get_uf_history()

    if uf_history:
        df_uf = pd.DataFrame(uf_history)
        df_uf.columns = ["Mes", "UF"]
        df_uf["UF ($)"] = df_uf["UF"].apply(lambda x: f"${float(x):,.2f}")
        df_uf = df_uf[["Mes", "UF ($)"]]

        st.caption(f"Total de registros: {len(uf_history)}")
        st.dataframe(df_uf, use_container_width=True, hide_index=True)
    else:
        st.info("No hay UF registradas")

    st.divider()

    # Sección de Promedios de Compensación Interna
    st.subheader("📈 Promedios de Compensación Interna (Competitividad)")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption("Calcula promedios de compensación anualizada por Nivel HAY")
        st.info(
            "💡 Esta sección permite:\n"
            "1. **Seleccionar Empresa** para análisis específico\n"
            "2. **Calcular** promedios basándose en empleados cargados\n"
            "3. **Probar** en ambiente de prueba antes de producción\n"
            "4. **Guardar** los promedios calculados en BD\n"
            "5. **Comparar** posición de cada empleado vs promedio"
        )

    with col2:
        total_promedios = len(db.get_compensation_averages())
        st.metric("Promedios en BD", total_promedios)

    st.divider()

    # Selector de empresa
    empresas = db.get_empresas()

    if not empresas:
        st.warning("⚠️ No hay empresas cargadas. Carga datos primero en la pestaña ANÁLISIS.")
    else:
        empresa_seleccionada = st.selectbox(
            "Selecciona Empresa para calcular promedios:",
            options=empresas,
            key="empresa_promedios"
        )

        # Botón para calcular promedios
        if st.button("🧮 Calcular Promedios (Prueba)", use_container_width=True, key="calc_averages"):
            try:
                from src.analysis.internal_competitiveness import InternalCompetitivenessCalculator

                with st.spinner(f"Calculando promedios para {empresa_seleccionada}..."):
                    calculator = InternalCompetitivenessCalculator(db)
                    resultados = calculator.calcular_promedios(empresa=empresa_seleccionada)

                if "error" in resultados:
                    st.error(f"❌ {resultados['error']}")
                else:
                    st.success(f"✅ Se calcularon promedios para {len(resultados)} niveles de {empresa_seleccionada}")

                    # Mostrar tabla de promedios calculados
                    st.subheader("📊 Promedios Calculados")

                    tabla_promedios = []
                    for nivel, datos in sorted(resultados.items()):
                        if "error" not in datos:
                            tabla_promedios.append({
                                "Nivel": nivel,
                                "👥 Empleados": datos["cantidad_empleados"],
                                "Promedio Anual": format_peso_chileno(datos['promedio_anualizado']),
                                "Mínimo": format_peso_chileno(datos['minimo_anualizado']),
                                "Máximo": format_peso_chileno(datos['maximo_anualizado']),
                                "Desv. Estándar": format_peso_chileno(datos['desviacion_std'])
                            })

                    df_promedios = pd.DataFrame(tabla_promedios)
                    st.dataframe(df_promedios, use_container_width=True, hide_index=True)

                    # GUARDAR AUTOMÁTICAMENTE
                    st.divider()
                    st.info("Guardando promedios en BD...")

                    if calculator.guardar_promedios(resultados):
                        st.success("✅ Promedios guardados en BD correctamente")
                        st.info("Los promedios están ahora disponibles en COMPENSACIONES para todos los empleados")

                        # Crear Excel para descarga
                        from io import BytesIO
                        excel_buffer = BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            df_promedios.to_excel(writer, sheet_name='Promedios', index=False)
                        excel_buffer.seek(0)

                        st.download_button(
                            label="📥 Descargar Excel con Promedios",
                            data=excel_buffer.getvalue(),
                            file_name=f"promedios_{empresa_seleccionada.replace(' ', '_')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Error al guardar promedios")

            except ImportError as e:
                st.error(f"❌ Error de importación: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    st.divider()

    # Mostrar promedios actuales en BD
    st.subheader("📋 Promedios Almacenados en Base de Datos")

    promedios_bd = db.get_compensation_averages()

    if promedios_bd:
        tabla_bd = []
        for prom in promedios_bd:
            tabla_bd.append({
                "Nivel": prom.get("nivel_hay"),
                "Empleados": prom.get("cantidad_empleados"),
                "Promedio Anual": format_peso_chileno(prom.get('promedio_anualizado', 0)),
                "Mínimo": format_peso_chileno(prom.get('minimo_anualizado', 0)),
                "Máximo": format_peso_chileno(prom.get('maximo_anualizado', 0)),
                "Desv. Estándar": format_peso_chileno(prom.get('desviacion_std', 0)),
                "Fecha Cálculo": prom.get("fecha_calculo", "")
            })

        df_bd = pd.DataFrame(tabla_bd)
        st.caption(f"Total de niveles: {len(promedios_bd)}")
        st.dataframe(df_bd, use_container_width=True, hide_index=True)
    else:
        st.info("No hay promedios calculados aún. Haz clic en 'Calcular Promedios' arriba.")

    st.divider()

    # Sección de Detalle de Compensación por Empleado
    st.subheader("📋 Detalle de Compensación por Empleado")

    st.caption("Descarga Excel con desglose completo de compensación de cada empleado para validación")

    col1, col2 = st.columns([3, 1])

    with col1:
        empresa_detalle = st.selectbox(
            "Selecciona Empresa para descargar detalle:",
            options=empresas if empresas else [],
            key="empresa_detalle"
        )

    with col2:
        st.write("")  # Spacing

    if empresa_detalle and st.button("📥 Generar Excel de Detalle", use_container_width=True, key="gen_detalle_excel"):
        try:
            from src.analysis.compensation_calculator import CompensationCalculator
            from io import BytesIO

            # Parámetros
            with open("config/parameters.json") as f:
                params = json.load(f)
            imm_value = params.get("imm_value", 553_553)

            calculator = CompensationCalculator(db, imm_value=imm_value)
            mes_actual = datetime.now().strftime("%Y-%m")

            # Obtener empleados
            empleados = db.get_analysis_by_empresa_area(empresa=empresa_detalle)

            if not empleados:
                st.error(f"❌ No hay empleados para {empresa_detalle}")
            else:
                with st.spinner(f"Generando detalle para {len(empleados)} empleados..."):
                    datos_detalle = []

                    for emp in empleados:
                        try:
                            sueldo_base = emp.get("sueldo_actual", 0)
                            if sueldo_base <= 0:
                                continue

                            target = float(emp.get("target", 1.0)) if emp.get("target") else 1.0
                            componentes = calculator.calcular_componentes(
                                sueldo_base=sueldo_base,
                                target=target,
                                mes=mes_actual,
                                incluir_target=True
                            )

                            datos_detalle.append({
                                "RUT": emp.get("rut"),
                                "Nombre": emp.get("nombre"),
                                "Área": emp.get("area", "N/A"),
                                "Cargo": emp.get("cargo_actual", "N/A"),
                                "Nivel HAY": emp.get("nivel_hay", "N/A"),
                                "Sueldo Base (Mensual)": round(sueldo_base, 2),
                                "Sueldo Base (Anual)": round(componentes["sueldo_anual"], 2),
                                "Gratificación (Mensual)": round(componentes["gratificacion"], 2),
                                "Gratificación (Anual)": round(componentes["gratificacion_anual"], 2),
                                "Colación (Mensual)": round(componentes["colacion"], 2),
                                "Colación (Anual)": round(componentes["colacion_anual"], 2),
                                "Movilización (Mensual)": round(componentes["movilizacion"], 2),
                                "Movilización (Anual)": round(componentes["movilizacion_anual"], 2),
                                "Target (Rentas)": target,
                                "Target (Anual)": round(componentes["target"], 2),
                                "COMPENSACIÓN TOTAL ANUAL": round(componentes["total"], 2),
                            })
                        except Exception as e:
                            st.warning(f"⚠️ Error con {emp.get('nombre')}: {str(e)}")
                            continue

                    if datos_detalle:
                        df_detalle = pd.DataFrame(datos_detalle)

                        # Crear Excel
                        excel_buffer = BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            # Hoja 1: Resumen Ejecutivo
                            df_resumen = df_detalle[[
                                "RUT", "Nombre", "Área", "Cargo", "Nivel HAY",
                                "Sueldo Base (Mensual)", "Gratificación (Mensual)",
                                "Colación (Mensual)", "Movilización (Mensual)",
                                "Target (Rentas)", "COMPENSACIÓN TOTAL ANUAL"
                            ]].copy()
                            df_resumen.to_excel(writer, sheet_name='Resumen Ejecutivo', index=False)

                            # Hoja 2: Detalle Completo
                            df_detalle_cols = df_detalle[[
                                "RUT", "Nombre", "Área", "Cargo", "Nivel HAY",
                                "Sueldo Base (Mensual)", "Sueldo Base (Anual)",
                                "Gratificación (Mensual)", "Gratificación (Anual)",
                                "Colación (Mensual)", "Colación (Anual)",
                                "Movilización (Mensual)", "Movilización (Anual)",
                                "Target (Rentas)", "Target (Anual)",
                                "COMPENSACIÓN TOTAL ANUAL"
                            ]]
                            df_detalle_cols.to_excel(writer, sheet_name='Detalle Completo', index=False)

                            # Hoja 3: Análisis por Nivel
                            df_por_nivel = df_detalle.groupby("Nivel HAY").agg({
                                "RUT": "count",
                                "Sueldo Base (Mensual)": ["mean", "min", "max"],
                                "COMPENSACIÓN TOTAL ANUAL": ["mean", "min", "max"]
                            }).round(2)
                            df_por_nivel.columns = [
                                "Cantidad", "Sb Prom", "Sb Mín", "Sb Máx",
                                "Comp Prom", "Comp Mín", "Comp Máx"
                            ]
                            df_por_nivel.to_excel(writer, sheet_name='Análisis por Nivel')

                        excel_buffer.seek(0)

                        # Mostrar estadísticas
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("Total Empleados", len(df_detalle))

                        with col2:
                            st.metric(
                                "Comp Prom Anual",
                                format_peso_chileno(df_detalle['COMPENSACIÓN TOTAL ANUAL'].mean())
                            )

                        with col3:
                            st.metric(
                                "Comp Mín Anual",
                                format_peso_chileno(df_detalle['COMPENSACIÓN TOTAL ANUAL'].min())
                            )

                        with col4:
                            st.metric(
                                "Comp Máx Anual",
                                format_peso_chileno(df_detalle['COMPENSACIÓN TOTAL ANUAL'].max())
                            )

                        st.divider()

                        # Botón de descarga
                        st.download_button(
                            label="📥 Descargar Excel Detallado",
                            data=excel_buffer.getvalue(),
                            file_name=f"detalle_compensacion_{empresa_detalle.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_detalle"
                        )

                        st.success(f"✅ Excel generado con {len(df_detalle)} empleados")

                    else:
                        st.error("❌ No se pudo procesar ningún empleado")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            st.error(traceback.format_exc())


def calculator_section():
    """Sección calculadora de sueldos."""
    st.header("🧮 Calculadora de Sueldos")

    # Período actual
    from datetime import datetime
    meses_es = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    now = datetime.now()
    periodo = f"{meses_es[now.month]} {now.year}"
    st.caption(f"Período: {periodo}")

    st.divider()

    # Método de entrada
    payroll_engine = get_payroll_engine()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 Datos del Empleado")

        salary_method = st.radio(
            "Ingresar:",
            ["Sueldo Base Directo", "Líquido Objetivo"],
            horizontal=True,
            key="calc_method"
        )

        if salary_method == "Sueldo Base Directo":
            base_salary = st.number_input(
                "Sueldo Base ($)",
                value=800000,
                min_value=0,
                step=10000,
                key="calc_base"
            )
        else:
            target_liquid = st.number_input(
                "Líquido Objetivo ($)",
                value=500000,
                min_value=0,
                step=10000,
                key="calc_liquid"
            )
            base_salary = target_liquid if target_liquid > 0 else 800000

        st.caption("Haberes adicionales")
        col1, col2, col3 = st.columns(3)
        with col1:
            collation = st.number_input("Colación", value=0, min_value=0, step=1000, key="calc_col")
        with col2:
            mobility = st.number_input("Movilización", value=0, min_value=0, step=1000, key="calc_mob")
        with col3:
            other_taxable = st.number_input("Otros Imp.", value=0, min_value=0, step=1000, key="calc_other")

    with col_right:
        st.subheader("⚙️ Opciones")

        contract_type = st.selectbox(
            "Tipo de Contrato",
            ["indefinido", "plazo_fijo"],
            format_func=lambda x: "Indefinido" if x == "indefinido" else "Plazo Fijo",
            key="calc_contract"
        )

        pension_fund = st.selectbox(
            "Fondo de Pensión (AFP)",
            ["Habitat", "ProVida", "Capital", "Cuprum", "PlanVital", "Modelo", "Uno"],
            key="calc_afp"
        )

        has_parking = st.checkbox("¿Tiene Estacionamiento?", value=False, key="calc_parking")

        # Pasar movilización al cálculo
        calc_mobility = mobility

    st.divider()

    # Botón para calcular
    if st.button("🧮 Calcular Liquidación", use_container_width=True, type="primary"):
        with st.spinner("Calculando..."):
            # Si es líquido objetivo, calcular el sueldo base necesario
            if salary_method == "Líquido Objetivo":
                base_salary = payroll_engine.reverse_calculate_base_salary(
                    target_net_salary=target_liquid,
                    collation=collation,
                    mobility=calc_mobility,
                    contract_type=contract_type,
                    pension_fund=pension_fund,
                    has_parking=has_parking
                )

            # Calcular liquidación
            calc = payroll_engine.calculate(
                base_salary=base_salary,
                collation=collation,
                mobility=calc_mobility,
                other_taxable=other_taxable,
                contract_type=contract_type,
                pension_fund=pension_fund
            )

            # Guardar en session state
            st.session_state.last_calculation = {
                "calc": calc,
                "base_salary": base_salary,
                "collation": collation,
                "mobility": calc_mobility,
                "other_taxable": other_taxable,
                "contract_type": contract_type,
                "pension_fund": pension_fund,
                "has_parking": has_parking,
                "periodo": datetime.now().strftime("%m-%Y")
            }

            st.success("✅ Liquidación calculada")

    # Mostrar resultado si existe
    if "last_calculation" in st.session_state and st.session_state.last_calculation:
        st.divider()
        st.subheader("📋 Resultado")

        calc = st.session_state.last_calculation["calc"]
        has_parking = st.session_state.last_calculation.get("has_parking", False)
        collation_val = st.session_state.last_calculation.get("collation", 0)
        mobility_val = st.session_state.last_calculation.get("mobility", 0)

        # Tabla de desglose - HABERES IMPONIBLES y DESCUENTOS LEGALES
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**HABERES IMPONIBLES**")
            haberes_data = {
                "Concepto": ["Sueldo Base", "Gratificación", "Otros Imponibles"],
                "Monto": [
                    f"${calc.base_salary:,.0f}",
                    f"${calc.gratification:,.0f}",
                    f"${calc.other_taxable:,.0f}"
                ]
            }
            import pandas as pd
            df_haberes = pd.DataFrame(haberes_data)
            st.dataframe(df_haberes, use_container_width=True, hide_index=True)

            st.markdown(f"**Total Imponible: ${calc.total_taxable:,.0f}**")

        with col2:
            st.markdown("**DESCUENTOS LEGALES**")
            descuentos_data = {
                "Concepto": ["AFP", "Salud", "AFC", "Impuesto Renta"],
                "Monto": [
                    f"${calc.afp_discount:,.0f}",
                    f"${calc.health_discount:,.0f}",
                    f"${calc.afc_discount:,.0f}",
                    f"${calc.income_tax:,.0f}"
                ]
            }
            df_descuentos = pd.DataFrame(descuentos_data)
            st.dataframe(df_descuentos, use_container_width=True, hide_index=True)

            st.markdown(f"**Total Descuentos: ${calc.total_discounts:,.0f}**")

        st.divider()

        # Tabla de desglose - HABERES NO IMPONIBLES y OTROS DESCUENTOS
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**HABERES NO IMPONIBLES**")
            no_imponibles_data = {
                "Concepto": ["Movilización", "Colación", "Otros No Imponibles"],
                "Monto": [
                    f"${mobility_val:,.0f}",
                    f"${collation_val:,.0f}",
                    f"${calc.other_non_taxable:,.0f}"
                ]
            }
            df_no_imponibles = pd.DataFrame(no_imponibles_data)
            st.dataframe(df_no_imponibles, use_container_width=True, hide_index=True)

            st.markdown(f"**Total: ${calc.total_non_taxable:,.0f}**")

        with col2:
            st.markdown("**OTROS DESCUENTOS**")
            parking_discount = mobility_val if has_parking else 0
            otros_data = {
                "Concepto": ["Estacionamiento"],
                "Monto": [f"${parking_discount:,.0f}"]
            }
            df_otros = pd.DataFrame(otros_data)
            st.dataframe(df_otros, use_container_width=True, hide_index=True)

            st.markdown(f"**Total: ${parking_discount:,.0f}**")

        st.divider()

        # APORTES EMPLEADOR (NUEVO SEGMENTO)
        st.markdown("**APORTES EMPLEADOR (Tope Imponible Mensual)**")

        # Obtener valor de UF del período actual
        from src.analysis.db_manager import AnalysisDBManager
        db_mgr = AnalysisDBManager()
        mes_actual = datetime.now().strftime("%Y-%m")
        uf_valor = db_mgr.get_uf(mes_actual) or 40873.77  # Valor por defecto

        # Topes mensuales en UF (convertir a pesos)
        tope_afc_empleador = 135.2 * uf_valor  # 135.2 UF para AFC Empleador
        tope_otros_aportes = 90 * uf_valor  # 90 UF para los demás aportes

        # Base para cálculos: mínimo entre haberes imponibles y tope
        base_afc = min(calc.total_taxable, tope_afc_empleador)
        base_otros = min(calc.total_taxable, tope_otros_aportes)

        # Cálculos: % × MIN(Haberes Imponibles, Tope en UF)
        afc_empleador = base_afc * 0.024
        mutual = base_otros * 0.0093
        sis = base_otros * 0.020
        rentabilidad_protegida = base_otros * 0.0090
        expectativa_vida = base_otros * 0.005
        aporte_afp = base_otros * 0.001

        total_aportes_empleador = afc_empleador + mutual + sis + rentabilidad_protegida + expectativa_vida + aporte_afp
        pct_aportes = (total_aportes_empleador / calc.total_taxable * 100) if calc.total_taxable > 0 else 0

        aportes_data = {
            "Concepto": [
                "AFC Empleador (2.40%)",
                "Mutual (0.93%)",
                "SIS (2.00%)",
                "Rentabilidad Protegida (0.90%)",
                "Expectativa de vida (0.50%)",
                "Aporte empleador a la AFP (0.10%)"
            ],
            "Monto": [
                f"${afc_empleador:,.0f}",
                f"${mutual:,.0f}",
                f"${sis:,.0f}",
                f"${rentabilidad_protegida:,.0f}",
                f"${expectativa_vida:,.0f}",
                f"${aporte_afp:,.0f}"
            ]
        }
        df_aportes = pd.DataFrame(aportes_data)
        st.dataframe(df_aportes, use_container_width=True, hide_index=True)

        st.markdown(f"**Total Aportes Empleador: ${total_aportes_empleador:,.0f} ({pct_aportes:.2f}%)**")

        st.divider()

        # Resumen final con todos los totales
        col1, col2, col3 = st.columns(3)

        total_all_discounts = calc.total_discounts + (parking_discount if has_parking else 0)
        final_liquid = calc.net_salary - (parking_discount if has_parking else 0)
        total_costos_empresa = calc.total_earnings + total_aportes_empleador

        with col1:
            st.metric("Total Haberes", f"${calc.total_earnings:,.0f}")
        with col2:
            st.metric("Total Descuentos", f"${total_all_discounts:,.0f}")
        with col3:
            st.metric("Aportes Empleador", f"${total_aportes_empleador:,.0f}")

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.metric("COSTOS EMPRESA (Total)", f"${total_costos_empresa:,.0f}")
        with col2:
            st.metric("💰 LÍQUIDO (Empleado)", f"${final_liquid:,.0f}", delta=None)

        st.divider()

        # Botones de exportación
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("📥 Excel", use_container_width=True, key="export_excel_calc"):
                try:
                    from src.exporter import ExcelExporter
                    import tempfile

                    exporter = ExcelExporter()
                    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                        temp_path = tmp.name

                    exporter.export_calculator(
                        calculation=calc,
                        output_filename=temp_path,
                        periodo=st.session_state.last_calculation.get("periodo", "")
                    )

                    with open(temp_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Descargar Excel",
                            data=f.read(),
                            file_name=f"Liquidacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    os.remove(temp_path)
                    st.success("✅ Excel generado")
                except Exception as e:
                    st.error(f"❌ Error al generar Excel: {str(e)}")

        with col2:
            if st.button("📄 PDF", use_container_width=True, key="export_pdf_calc"):
                try:
                    import tempfile

                    pdf_exporter = PDFExporterCalc()

                    # Obtener logo si existe
                    logo_path = None
                    try:
                        with open("config/company_logos.json") as f:
                            logo_config = json.load(f)
                            logo_path = logo_config.get("company_logos", {}).get("DERCORP", None)
                            if logo_path and not os.path.exists(logo_path):
                                logo_path = None
                    except:
                        pass

                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        temp_path = tmp.name

                    # Pasar también los valores explícitos de colación y movilización
                    # por si no se preservan correctamente en el objeto
                    collation_val = st.session_state.last_calculation.get("collation", 0)
                    mobility_val = st.session_state.last_calculation.get("mobility", 0)

                    # Crear objeto actualizado si es necesario
                    calc_fixed = calc
                    if calc.collation != collation_val or calc.mobility != mobility_val:
                        # Recalcular total_non_taxable si los valores no coinciden
                        import copy
                        calc_fixed = copy.copy(calc)
                        calc_fixed.collation = collation_val
                        calc_fixed.mobility = mobility_val
                        calc_fixed.total_non_taxable = collation_val + mobility_val + calc.other_non_taxable

                    # Calcular descuento de estacionamiento si aplica
                    parking_discount = 0
                    if st.session_state.last_calculation.get("has_parking", False) and calc_fixed.mobility > 0:
                        # Descuento de estacionamiento: 100% de la movilización
                        parking_discount = calc_fixed.mobility

                    pdf_exporter.export_calculator(
                        calculation=calc_fixed,
                        output_filename=temp_path,
                        periodo=st.session_state.last_calculation.get("periodo", ""),
                        logo_path=logo_path,
                        has_parking=st.session_state.last_calculation.get("has_parking", False),
                        parking_discount=parking_discount
                    )

                    with open(temp_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Descargar PDF",
                            data=f.read(),
                            file_name=f"Liquidacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf"
                        )

                    os.remove(temp_path)
                    st.success("✅ PDF generado")
                except Exception as e:
                    st.error(f"❌ Error al generar PDF: {str(e)}")


def main():
    """Función principal."""
    initialize_session_state()

    # Header
    st.markdown('<p class="main-header">💰 Suite ARP IA</p>', unsafe_allow_html=True)
    st.markdown("Suite de compensaciones ARP")

    # Pestañas principales
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🧮 CALCULADORA", "📊 ANÁLISIS", "📝 PROPUESTAS", "💰 COMPENSACIONES", "🎯 SIMULADOR (test)", "⚙️ CONFIGURACIÓN"])

    with tab1:
        # === TAB CALCULADORA ===
        calculator_section()

    with tab2:
        # === TAB ANÁLISIS ===
        from src.analysis.streamlit_ui import show_analysis_section
        buk_client = get_buk_client()
        show_analysis_section(buk_client)

    with tab3:
        # === TAB PROPUESTAS ===
        # Detectar si hay empleado seleccionado desde ANÁLISIS
        if "empleado_para_propuesta" in st.session_state and st.session_state.empleado_para_propuesta:
            datos_emp = st.session_state.empleado_para_propuesta
            try:
                buk_client = get_buk_client()
                employee = buk_client.search_employee(rut=datos_emp["rut"])
                if employee:
                    st.session_state.current_employee = employee
                    st.session_state.propuestas_subtab = "propuesta"
                    st.success(f"✅ Empleado cargado desde ANÁLISIS: {employee.full_name}")
                    del st.session_state.empleado_para_propuesta
            except:
                pass

        if st.session_state.propuestas_subtab == "propuesta":
            # Sección de creación de propuesta
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("← Volver a Buscar", use_container_width=True, key="back_to_search"):
                    st.session_state.propuestas_subtab = "buscar"
                    st.rerun()
            with col3:
                if st.button("Ver Comparativa →", use_container_width=True, key="to_comparison"):
                    st.session_state.propuestas_subtab = "comparativa"
                    st.rerun()

            proposal_section()

        elif st.session_state.propuestas_subtab == "comparativa":
            # Sección de comparativa
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("← Crear Propuesta", use_container_width=True, key="back_to_proposal"):
                    st.session_state.propuestas_subtab = "propuesta"
                    st.rerun()
            with col3:
                if st.button("Buscar Nuevo →", use_container_width=True, key="search_new"):
                    st.session_state.propuestas_subtab = "buscar"
                    st.rerun()

            comparison_section()

        else:
            # Sección de búsqueda (default)
            col1, col2, col3 = st.columns([2, 1, 1])
            with col3:
                if st.session_state.current_employee:
                    if st.button("Crear Propuesta →", use_container_width=True, key="to_proposal"):
                        st.session_state.propuestas_subtab = "propuesta"
                        st.rerun()

            search_employee_section()

    with tab4:
        # === TAB COMPENSACIONES ===
        from src.analysis.compensaciones_ui import show_compensations_section
        buk_client = get_buk_client()
        show_compensations_section(buk_client)

    with tab5:
        # === TAB SIMULADOR (test) ===
        from src.analysis.proposal_simulator_ui import show_proposal_simulator, show_compensation_comparison

        # Subtab para seleccionar entre simulador clásico y comparativa de compensación
        simulador_subtab = st.radio(
            "Selecciona tipo de análisis:",
            ["Propuesta Tradicional", "Comparativa de Compensación Anual"],
            horizontal=True,
            key="simulador_tipo"
        )

        if simulador_subtab == "Propuesta Tradicional":
            show_proposal_simulator()
        else:
            # Comparativa de compensación anual
            from src.analysis.db_manager import AnalysisDBManager
            db_manager = AnalysisDBManager()
            engine = get_payroll_engine()
            show_compensation_comparison(db_manager, engine)

    with tab6:
        # === TAB CONFIGURACIÓN ===
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("← Volver", use_container_width=True, key="back_from_config"):
                st.session_state.main_tab = "propuestas"
                st.rerun()

        configuration_section()


if __name__ == "__main__":
    main()
