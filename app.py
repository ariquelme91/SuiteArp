"""Aplicación web de Propuestas de Renta con Streamlit."""

import streamlit as st
from streamlit_option_menu import option_menu
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
from src.auth_manager import AuthManager
from src.branding import LOGO_HORIZONTAL_PATH, LOGO_PATH, logo_base64
from src.login_page import render_login_page
from src.user_management import render_user_management
from src.analysis.db_manager import AnalysisDBManager
from src.github_sync import commit_json_file, is_configured as github_sync_configured

# Cargar variables de entorno
load_dotenv()

# Configuración de Streamlit
st.set_page_config(
    page_title="Suite ARP IA",
    page_icon=":material/payments:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
    <style>
    /* Evitar que imágenes (logos, fotos de empleado) desborden en pantallas angostas */
    img {
        max-width: 100%;
        height: auto;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #3B78C3;
        margin-bottom: 1rem;
    }
    .app-logo {
        margin-bottom: 0.5rem;
    }
    .app-logo img {
        width: 280px;
        height: auto;
        max-width: 100%;
    }
    /* Dar contraste visual a los campos de entrada (texto, número, fecha,
       selectbox) para que se note claramente dónde hay que escribir o
       seleccionar. El tema oscuro los deja casi del mismo color que el
       fondo, por lo que un usuario nuevo no distingue la caja. Se usa
       box-shadow en vez de border porque Streamlit ya fija su propio
       border-color y lo sobrescribe; box-shadow no compite con esa regla. */
    [data-baseweb="input"],
    [data-baseweb="select"] > div,
    [data-baseweb="textarea"] {
        box-shadow: 0 0 0 1px #5A6472 !important;
        border-radius: 6px !important;
    }
    [data-baseweb="input"]:focus-within,
    [data-baseweb="select"] > div:focus-within,
    [data-baseweb="textarea"]:focus-within {
        box-shadow: 0 0 0 2px #3B78C3 !important;
    }
    </style>
    """, unsafe_allow_html=True)


def initialize_session_state():
    """Inicializa variables de sesión."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "usuario" not in st.session_state:
        st.session_state.usuario = None
    if "rol" not in st.session_state:
        st.session_state.rol = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
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
    if "enable_compensation_analysis" not in st.session_state:
        st.session_state.enable_compensation_analysis = False


def get_buk_client():
    """Obtiene instancia del cliente Buk."""
    api_token = os.getenv("BUK_API_TOKEN")
    subdomain = os.getenv("BUK_SUBDOMAIN")

    if not api_token or not subdomain:
        st.error(":material/cancel: Variables de entorno BUK_API_TOKEN y BUK_SUBDOMAIN no configuradas")
        st.stop()

    db_manager = AnalysisDBManager()
    return BukClient(api_token, subdomain, db_manager=db_manager)


def get_payroll_engine():
    """Obtiene instancia del motor de nómina."""
    with open("config/parameters.json") as f:
        parameters = json.load(f)
    return PayrollEngine(parameters)


def get_beneficios_config():
    """Obtiene los montos vigentes de beneficios adicionales (costo empresa).

    Se guardan en la BD (no en config/parameters.json) para que las
    actualizaciones hechas desde la app no se pierdan en cada rerun/reinicio
    normal del proceso.
    """
    return AnalysisDBManager().get_beneficios_config()


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
    # Dos columnas: Buscar a la izquierda, Análisis a la derecha
    col_search, col_extras = st.columns([1, 1])

    with col_search:
        st.header(":material/search: Buscar Colaborador")
        search_by = st.radio("Buscar por:", ["RUT", "Ver Todos"], horizontal=True)

        search_input = ""
        if search_by == "RUT":
            search_input = st.text_input("Ingrese RUT (ej: 12.345.678-9)").strip()

        if st.button(":material/search: Buscar", width='stretch') or search_by == "Ver Todos":
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
                        st.success(f":material/check_circle: Colaborador encontrado: {employee.full_name}")
                        # Auto-navegar a Crear Propuesta
                        st.session_state.propuestas_subtab = "propuesta"
                        st.rerun()
                    else:
                        st.error(":material/cancel: Colaborador no encontrado")
                elif search_by == "Ver Todos":
                    # Obtener todos los empleados activos (cacheado por 1 hora)
                    employees_sorted = get_all_active_employees()
                    if employees_sorted:
                        st.session_state.search_results = employees_sorted
                        st.success(f":material/check_circle: Total de {len(employees_sorted)} colaborador(es) activo(s) (datos en caché)")
                    else:
                        st.error(":material/cancel: No se encontraron colaboradores")

    with col_extras:
        st.header(":material/settings: Extras")
        st.info(":material/lightbulb: Usa el checkbox en la barra lateral para habilitar el Analizador de Renta")

    st.divider()

    # Mostrar resultados de búsqueda por apellido
    if st.session_state.search_results:
        st.divider()

        # Mini buscador en tiempo real
        col1, col2 = st.columns([4, 1])
        with col1:
            search_filter = st.text_input(":material/search: Filtrar por nombre...", placeholder="Ej: Angel, Riquelme, etc", key="employee_filter")

        # Filtrar resultados
        if search_filter:
            filtered_results = [
                emp for emp in st.session_state.search_results
                if search_filter.lower() in emp.full_name.lower()
            ]
        else:
            filtered_results = st.session_state.search_results

        st.subheader(f":material/assignment: Seleccione un colaborador: ({len(filtered_results)} de {len(st.session_state.search_results)})")

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
                if st.button("Seleccionar", key=f"select_{idx}", width='stretch'):
                    st.session_state.current_employee = employee
                    st.session_state.search_results = None
                    st.session_state.propuestas_subtab = "propuesta"
                    st.success(f":material/check_circle: {employee.full_name} seleccionado")
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
        st.warning(":material/warning: Seleccione un colaborador primero")
        return

    employee = st.session_state.current_employee

    # Mostrar estado de Analizador de Renta al inicio
    is_analysis_enabled = st.session_state.get("enable_compensation_analysis", False)
    if is_analysis_enabled:
        st.info(":material/check_circle: **Analizador de Renta HABILITADO** - Las secciones de compensación aparecerán abajo")
    else:
        st.warning(":material/radio_button_unchecked: **Analizador de Renta DESHABILITADO** - Marca el checkbox en 'Buscar Colaborador' para habilitar")

    st.divider()

    # Mostrar header con logo si existe
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        logo_path = get_company_logo(employee.company_name)
        if logo_path:
            st.image(logo_path, width=80)
        else:
            st.info("Logo no disponible")

    with col_title:
        st.header(f":material/edit_note: Propuesta de Renta - {employee.full_name}")

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

    # Inicializar variables de Cambios Org. FUERA de columnas
    new_company = employee.company_name
    new_position = employee.job_title
    new_supervisor = employee.supervisor

    # Layout: Motivo (izq) | Cambios Org. (der) SIEMPRE al lado
    col_motivo, col_cambios = st.columns([1, 1])

    with col_motivo:
        st.subheader(":material/track_changes: Motivo de la Propuesta")
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

    with col_cambios:
        st.subheader(":material/assignment: Cambios Organizacionales")
        change_company = st.checkbox("¿Cambiará de empresa?", key="change_company")
        change_position = st.checkbox("¿Cambiará de cargo?", key="change_position")
        change_supervisor = st.checkbox("¿Cambiará de jefatura?", key="change_supervisor")

        if change_company:
            try:
                buk_client = get_buk_client()
                companies = buk_client.get_companies()
                if companies:
                    company_names = [c['name'] for c in companies]
                    new_company = st.selectbox("Seleccione nueva empresa", company_names, label_visibility="collapsed", key="new_company_select")
            except:
                st.warning("No se pudieron cargar empresas")
                new_company = st.text_input("Nombre de empresa", value=employee.company_name, label_visibility="collapsed")

        if change_position:
            new_position = st.text_input("Nuevo cargo", value=employee.job_title or "", label_visibility="collapsed", key="new_position_input")

        if change_supervisor:
            new_supervisor = st.text_input("Nuevo nombre de jefe", value=employee.supervisor or "", label_visibility="collapsed", key="new_supervisor_input")

    st.divider()

    # Haberes Actuales y Propuestos (lado a lado)
    st.subheader(":material/bar_chart: Haberes Actuales vs Propuestos")

    # Obtener UF para valores sugeridos
    db_mgr = AnalysisDBManager()
    mes_actual = datetime.now().strftime("%Y-%m")
    uf_valor = db_mgr.get_uf(mes_actual) or 40873.77
    movilizacion_sugerida = int(2.44 * uf_valor)

    col_actual, col_propuesto = st.columns(2)

    # Inicializar valores en session_state si no existen
    if "col_actual" not in st.session_state:
        st.session_state.col_actual = 130000
    if "mob_actual" not in st.session_state:
        st.session_state.mob_actual = movilizacion_sugerida
    if "other_actual" not in st.session_state:
        st.session_state.other_actual = 0
    if "col_prop" not in st.session_state:
        st.session_state.col_prop = 130000
    if "mob_prop" not in st.session_state:
        st.session_state.mob_prop = movilizacion_sugerida
    if "other_prop" not in st.session_state:
        st.session_state.other_prop = 0

    # HABERES ACTUALES
    with col_actual:
        st.caption(":material/payments: Haberes Actuales")

        st.text("Colación")
        current_collation = st.number_input("Colación", value=st.session_state.col_actual, min_value=0, label_visibility="collapsed", key="col_actual", step=1000)
        st.session_state.current_collation = current_collation

        st.text("Movilización")
        current_mobility = st.number_input("Movilización", value=st.session_state.mob_actual, min_value=0, label_visibility="collapsed", key="mob_actual", step=1000, help=f"Sugerencia: 2.44 × UF = ${movilizacion_sugerida:,.0f}")
        st.session_state.current_mobility = current_mobility

        st.text("Otros imponibles")
        current_other_taxable = st.number_input("Otros imponibles", value=st.session_state.other_actual, min_value=0, label_visibility="collapsed", key="other_actual", step=1000)
        st.session_state.current_other_taxable = current_other_taxable

        # Checkbox para estacionamiento
        has_parking = st.checkbox("¿Tiene Estacionamiento?", key="has_parking", value=False)

    # HABERES PROPUESTOS
    with col_propuesto:
        st.caption(":material/trending_up: Haberes Propuestos")

        st.text("Colación")
        proposal_collation = st.number_input("Colación", value=st.session_state.col_prop, min_value=0, label_visibility="collapsed", key="col_prop", step=1000)

        st.text("Movilización")
        proposal_mobility = st.number_input("Movilización", value=st.session_state.mob_prop, min_value=0, label_visibility="collapsed", key="mob_prop", step=1000, help=f"Sugerencia: 2.44 × UF = ${movilizacion_sugerida:,.0f}")

        st.text("Otros imponibles")
        proposal_other_taxable = st.number_input("Otros imponibles", value=st.session_state.other_prop, min_value=0, label_visibility="collapsed", key="other_prop", step=1000)

        # Checkbox para estacionamiento en propuesta
        proposal_has_parking = st.checkbox("¿Tendrá Estacionamiento?", key="proposal_parking", value=has_parking)

    st.divider()

    # NUEVO SUELDO BASE
    st.subheader(":material/work: Cómo ingresar el nuevo sueldo")

    payroll_engine = get_payroll_engine()

    col_opcion, col_valor = st.columns(2)

    # COLUMNA IZQUIERDA: Opciones de entrada
    with col_opcion:
        st.caption("Tipo de Entrada")
        input_type = st.radio(
            "¿Cómo ingresar el nuevo sueldo?",
            [
                "Sueldo base",
                "% sobre el sueldo base",
                "Sueldo Líquido",
                "% sobre el sueldo líquido"
            ],
            label_visibility="collapsed"
        )

    # Calcular líquido actual para referencias
    mobility_for_calc = current_mobility
    if has_parking and mobility_for_calc > 0:
        mobility_for_calc = 0

    current_payroll = payroll_engine.calculate(
        base_salary=employee.base_salary,
        collation=current_collation,
        mobility=mobility_for_calc,
        other_taxable=current_other_taxable,
        contract_type=employee.contract_type,
        pension_fund=employee.pension_fund,
    )
    current_liquid = current_payroll.net_salary

    # COLUMNA DERECHA: Valor a ingresar
    with col_valor:
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
            st.caption("Porcentaje de aumento")
            porcentaje_aumento = st.number_input(
                "Porcentaje (%)",
                value=0.0,
                min_value=0.0,
                step=0.1,
                label_visibility="collapsed",
                key="percent_base"
            )
            proposal_base_salary = int(employee.base_salary * (1 + porcentaje_aumento / 100))
            st.info(f"**Base actual:** ${employee.base_salary:,.0f} :material/arrow_forward: **Nueva base:** ${proposal_base_salary:,.0f}")

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
            st.info(f"**Líquido actual:** ${current_liquid:,.0f} :material/arrow_forward: **Líquido objetivo:** ${target_liquid:,.0f}")

        else:  # % sobre el sueldo líquido
            st.caption("Porcentaje de aumento")
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
            st.info(f"**Líquido actual:** ${current_liquid:,.0f} :material/arrow_forward: **Líquido objetivo:** ${target_liquid:,.0f}")

    st.divider()

    # BENEFICIOS ADICIONALES (Costo Empresa - no afectan la liquidación del trabajador)
    st.subheader(":material/payments: Beneficios Adicionales")
    st.caption("Montos anuales, editables en CONFIGURACIÓN. No afectan AFP/Salud/Impuesto ni el líquido del trabajador — solo se suman al costo anual para la empresa.")

    beneficios_cfg = get_beneficios_config()
    monto_aguinaldo_navidad = beneficios_cfg.get("aguinaldo_navidad", 60000)
    monto_aguinaldo_fiestas = beneficios_cfg.get("aguinaldo_fiestas_patrias", 60000)
    monto_gift_card = beneficios_cfg.get("gift_card", 50000)
    monto_bono_vacaciones = beneficios_cfg.get("bono_vacaciones_monto", 200000)
    tope_bono_vacaciones = beneficios_cfg.get("bono_vacaciones_tope_renta", 2500000)

    # Elegibilidad automática del Bono Vacaciones: renta = Sueldo Base + Gratificación
    renta_actual_ben = employee.base_salary + payroll_engine.calculate(base_salary=employee.base_salary).gratification
    califica_bono_actual = renta_actual_ben < tope_bono_vacaciones

    renta_propuesta_ben = proposal_base_salary + payroll_engine.calculate(base_salary=proposal_base_salary).gratification
    califica_bono_propuesta = renta_propuesta_ben < tope_bono_vacaciones

    col_ben_check, col_ben_bono = st.columns(2)

    with col_ben_check:
        st.caption("Aplican a este trabajador (empresa/caso a caso)")
        chk_aguinaldo_navidad = st.checkbox(f"Aguinaldo de Navidad (${monto_aguinaldo_navidad:,.0f})", value=True, key="chk_aguinaldo_navidad")
        chk_aguinaldo_fiestas = st.checkbox(f"Aguinaldo Fiestas Patrias (${monto_aguinaldo_fiestas:,.0f})", value=True, key="chk_aguinaldo_fiestas")
        chk_gift_card = st.checkbox(f"Gift Card (${monto_gift_card:,.0f})", value=True, key="chk_gift_card")

    with col_ben_bono:
        st.caption(f"Bono Vacaciones — aplica si renta < ${tope_bono_vacaciones:,.0f}")
        chk_bono_actual = st.checkbox(
            f"Actual — renta ${renta_actual_ben:,.0f} ({':material/check_circle: califica' if califica_bono_actual else ':material/cancel: no califica'})",
            value=califica_bono_actual, key="chk_bono_actual",
        )
        chk_bono_propuesta = st.checkbox(
            f"Propuesta — renta ${renta_propuesta_ben:,.0f} ({':material/check_circle: califica' if califica_bono_propuesta else ':material/cancel: no califica'})",
            value=califica_bono_propuesta, key="chk_bono_propuesta",
        )

    beneficios_actual_anual = (
        (monto_aguinaldo_navidad if chk_aguinaldo_navidad else 0)
        + (monto_aguinaldo_fiestas if chk_aguinaldo_fiestas else 0)
        + (monto_gift_card if chk_gift_card else 0)
        + (monto_bono_vacaciones if chk_bono_actual else 0)
    )
    beneficios_propuesta_anual = (
        (monto_aguinaldo_navidad if chk_aguinaldo_navidad else 0)
        + (monto_aguinaldo_fiestas if chk_aguinaldo_fiestas else 0)
        + (monto_gift_card if chk_gift_card else 0)
        + (monto_bono_vacaciones if chk_bono_propuesta else 0)
    )

    col_ben_total1, col_ben_total2 = st.columns(2)
    with col_ben_total1:
        st.metric("Beneficios Anuales — Actual", f"${beneficios_actual_anual:,.0f}")
    with col_ben_total2:
        st.metric("Beneficios Anuales — Propuesta", f"${beneficios_propuesta_anual:,.0f}")

    st.session_state.beneficios_data = {
        "aguinaldo_navidad_aplica": chk_aguinaldo_navidad,
        "aguinaldo_navidad_monto": monto_aguinaldo_navidad if chk_aguinaldo_navidad else 0,
        "aguinaldo_fiestas_patrias_aplica": chk_aguinaldo_fiestas,
        "aguinaldo_fiestas_patrias_monto": monto_aguinaldo_fiestas if chk_aguinaldo_fiestas else 0,
        "gift_card_aplica": chk_gift_card,
        "gift_card_monto": monto_gift_card if chk_gift_card else 0,
        "bono_vacaciones_actual_aplica": chk_bono_actual,
        "bono_vacaciones_actual_monto": monto_bono_vacaciones if chk_bono_actual else 0,
        "bono_vacaciones_propuesta_aplica": chk_bono_propuesta,
        "bono_vacaciones_propuesta_monto": monto_bono_vacaciones if chk_bono_propuesta else 0,
        "total_anual_actual": beneficios_actual_anual,
        "total_anual_propuesta": beneficios_propuesta_anual,
    }

    st.divider()

    # INFORMACIÓN DE COMPENSACIÓN ACTUAL vs PROPUESTA (solo si está habilitado el Analizador)
    if st.session_state.get("enable_compensation_analysis", False):
        # Cargar Nivel HAY y Target desde múltiples fuentes (en orden de prioridad)
        if employee and hasattr(employee, 'rut'):
            try:
                # Prioridad 1: Desde el employee object de BUK (datos más frescos)
                if hasattr(employee, 'nivel_hay') and employee.nivel_hay:
                    if "nivel_hay_actual_input" not in st.session_state:
                        st.session_state.nivel_hay_actual_input = str(employee.nivel_hay)

                if hasattr(employee, 'target') and employee.target:
                    if "target_actual_input" not in st.session_state:
                        try:
                            target_val = float(str(employee.target).replace(',', '.'))
                            st.session_state.target_actual_input = target_val
                        except:
                            st.session_state.target_actual_input = 0.0

                # Prioridad 2: Desde la BD de análisis (si no viene de BUK)
                if not (hasattr(employee, 'nivel_hay') and employee.nivel_hay):
                    db_manager = AnalysisDBManager()
                    employee_analysis = db_manager.get_employee_by_rut(employee.rut)

                    if employee_analysis:
                        if "nivel_hay_actual_input" not in st.session_state and employee_analysis.get('nivel_hay'):
                            st.session_state.nivel_hay_actual_input = str(employee_analysis.get('nivel_hay', ''))

                        if "target_actual_input" not in st.session_state and employee_analysis.get('target'):
                            try:
                                target_val = float(str(employee_analysis.get('target', '0')).replace(',', '.'))
                                st.session_state.target_actual_input = target_val
                            except:
                                st.session_state.target_actual_input = 0.0
            except Exception as e:
                pass  # Si hay error, continúa sin cargar los datos

        # Inicializar valores en session_state si no existen
        if "nivel_hay_prop_input" not in st.session_state:
            st.session_state.nivel_hay_prop_input = ""
        if "target_prop_input" not in st.session_state:
            st.session_state.target_prop_input = 0.0
        if "mercado_comparacion_main" not in st.session_state:
            st.session_state.mercado_comparacion_main = "Mercado Financiero"
        if "mercado_comparacion_info_prop" not in st.session_state:
            st.session_state.mercado_comparacion_info_prop = "Mercado Financiero"

        st.subheader(":material/lightbulb: Información de Compensación")

        col_comp_actual, col_comp_propuesta = st.columns(2)

        # DATOS ACTUALES (editable)
        with col_comp_actual:
            st.caption(":material/payments: Datos Actuales")

            st.text("Nivel HAY")
            hay_actual_comp = st.session_state.get("nivel_hay_actual_input", "")
            # Inicializar en session_state si no existe
            if "nivel_hay_actual_input" not in st.session_state:
                st.session_state.nivel_hay_actual_input = ""
            # Campo siempre editable para permitir cambios
            st.text_input("Nivel HAY Actual", value=st.session_state.nivel_hay_actual_input, label_visibility="collapsed", key="nivel_hay_actual_input", placeholder="Ej: 16, 18, 20")

            st.text("Target (rentas)")
            if "target_actual_input" not in st.session_state:
                st.session_state.target_actual_input = 0.0
            # Campo siempre editable
            st.number_input("Target Actual", value=float(st.session_state.target_actual_input), label_visibility="collapsed", key="target_actual_input", step=0.1, min_value=0.0)

            st.text("Tipo de Mercado")
            if "mercado_comparacion_main" not in st.session_state:
                st.session_state.mercado_comparacion_main = "Mercado Financiero"
            mercado_actual_comp = st.session_state.mercado_comparacion_main
            st.selectbox("Mercado Actual", options=["Mercado Financiero", "Mercado Seguros"], index=0 if mercado_actual_comp == "Mercado Financiero" else 1, label_visibility="collapsed", key="mercado_comparacion_main")

        # DATOS PROPUESTOS (editable)
        with col_comp_propuesta:
            st.caption(":material/trending_up: Datos Propuestos")

            st.text("Nivel HAY")
            st.text_input(
                "Nivel HAY Propuesta",
                value=st.session_state.nivel_hay_prop_input,
                placeholder="Ej: 18, 20",
                label_visibility="collapsed",
                key="nivel_hay_prop_input",
                help="Nivel HAY para la propuesta (puede ser igual al actual o diferente si hay promoción)."
            )

            st.text("Target (rentas)")
            st.number_input(
                "Target Propuesta",
                value=st.session_state.target_prop_input,
                min_value=0.0,
                step=0.1,
                label_visibility="collapsed",
                key="target_prop_input",
                help="Target en rentas para la propuesta (Ej: 2.8, 3.0, etc.)."
            )

            st.text("Tipo de Mercado")
            mercado_comparacion = st.selectbox(
                "Tipo de Mercado",
                options=["Mercado Financiero", "Mercado Seguros"],
                key="mercado_comparacion_info_prop",
                label_visibility="collapsed",
                help="Selecciona el mercado para comparar la compensación."
            )

        st.divider()

        # CALCULADOR DE COMPENSACIÓN REAL basado en Nivel HAY × Target
        st.subheader(":material/payments: Compensación Real por Nivel HAY")

        col_calc_actual, col_calc_prop = st.columns(2)

        beneficios_data_comp = st.session_state.get("beneficios_data", {})
        beneficios_anual_actual_comp = beneficios_data_comp.get("total_anual_actual", 0)
        beneficios_anual_prop_comp = beneficios_data_comp.get("total_anual_propuesta", 0)

        # Obtener valores actuales de Haberes
        sal_base_actual = employee.base_salary
        grat_actual = payroll_engine.calculate(base_salary=sal_base_actual).gratification
        col_actual_hab = st.session_state.get("col_actual", 130000)
        mob_actual_hab = st.session_state.get("mob_actual", 0)

        # Anualizados
        sal_base_anual = sal_base_actual * 12
        grat_anual = grat_actual * 12
        col_anual = col_actual_hab * 12
        mob_anual = mob_actual_hab * 12

        # Variables para el bono
        bono_target_actual = 0
        monto_nivel_actual = 0
        bono_target_prop = 0
        monto_nivel_prop = 0

        with col_calc_actual:
            st.caption(":material/payments: ACTUAL")

            st.metric("Sueldo Base x12", f"${sal_base_anual:,.0f}")
            st.metric("Gratificación x12", f"${grat_anual:,.0f}")
            st.metric("Colación x12", f"${col_anual:,.0f}")
            st.metric("Movilización x12", f"${mob_anual:,.0f}")

            st.divider()

            # Obtener nivel HAY actual y calcular bono
            nivel_hay_actual_str = st.session_state.get("nivel_hay_actual_input", "").strip()
            target_actual_input = st.session_state.get("target_actual_input", 0.0)

            # Calcular bono (incluso sin nivel HAY)
            bono_target_actual = target_actual_input * sal_base_actual if target_actual_input > 0 else 0

            # Siempre mostrar Bono Target (aunque sea $0)
            st.metric(":material/payments: Bono Target", f"${bono_target_actual:,.0f}", delta=f"({target_actual_input} × ${sal_base_actual:,.0f})")

            if beneficios_anual_actual_comp > 0:
                st.metric(":material/payments: Beneficios Adicionales", f"${beneficios_anual_actual_comp:,.0f}")

            total_actual_comp = sal_base_anual + grat_anual + col_anual + mob_anual + bono_target_actual + beneficios_anual_actual_comp
            st.metric("TOTAL ANUALIZADO", f"${total_actual_comp:,.0f}", delta_color="off")
            st.divider()

            # Mostrar valores de Mercado y Promedio Interno con Gap Análisis
            if nivel_hay_actual_str and nivel_hay_actual_str.isdigit():
                try:
                    db_manager = AnalysisDBManager()

                    # Obtener datos de mercado y promedio
                    comp_data = db_manager.get_compensation_by_level(int(nivel_hay_actual_str))
                    avg_data = db_manager.get_compensation_average_by_level(nivel_hay_actual_str)

                    # Seleccionar el campo correcto según el mercado elegido
                    mercado_field = 'mercado_seguros' if mercado_actual_comp == 'Mercado Seguros' else 'mercado_financiero'
                    mercado_val = comp_data.get(mercado_field, 0) if comp_data else 0
                    promedio_val = avg_data.get('promedio_anualizado', 0) if avg_data else 0

                    st.caption(f":material/bar_chart: **Estudio de Mercado** (Nivel {nivel_hay_actual_str}, {mercado_actual_comp}): **${mercado_val:,.0f}**")

                    # Gap vs Mercado
                    if mercado_val > 0:
                        gap_mercado = total_actual_comp - mercado_val
                        pct_mercado = (gap_mercado / mercado_val * 100) if mercado_val != 0 else 0
                        icon_mercado = ":material/check_circle:" if gap_mercado >= 0 else ":material/warning:"
                        direction = "ARRIBA" if gap_mercado >= 0 else "DEBAJO"
                        st.caption(f"{icon_mercado} {direction} del mercado: **${abs(gap_mercado):,.0f}** ({pct_mercado:+.1f}%)")

                    st.caption(f":material/bar_chart: **Mediana Interna** (Nivel {nivel_hay_actual_str}): **${promedio_val:,.0f}**")

                    # Gap vs Mediana Interna
                    if promedio_val > 0:
                        gap_promedio = total_actual_comp - promedio_val
                        pct_promedio = (gap_promedio / promedio_val * 100) if promedio_val != 0 else 0
                        icon_promedio = ":material/check_circle:" if gap_promedio >= 0 else ":material/warning:"
                        direction = "ARRIBA" if gap_promedio >= 0 else "DEBAJO"
                        st.caption(f"{icon_promedio} {direction} de la mediana: **${abs(gap_promedio):,.0f}** ({pct_promedio:+.1f}%)")
                except Exception as e:
                    st.caption(f":material/bar_chart: Nivel {nivel_hay_actual_str}: Datos no disponibles en BD")
            elif nivel_hay_actual_str:
                st.warning(f":material/warning: Nivel HAY debe ser numérico (Ej: 16, 18, 20)")
            else:
                st.caption(":material/bar_chart: Ingresa Nivel HAY para ver la media de compensación")

        with col_calc_prop:
            st.caption(":material/trending_up: PROPUESTO")

            # Obtener valores propuestos
            sal_base_prop = int(proposal_base_salary) if 'proposal_base_salary' in locals() else sal_base_actual
            grat_prop = payroll_engine.calculate(base_salary=sal_base_prop).gratification
            col_prop_hab = st.session_state.get("col_prop", 130000)
            mob_prop_hab = st.session_state.get("mob_prop", 0)

            sal_base_anual_prop = sal_base_prop * 12
            grat_anual_prop = grat_prop * 12
            col_anual_prop = col_prop_hab * 12
            mob_anual_prop = mob_prop_hab * 12

            st.metric("Sueldo Base x12", f"${sal_base_anual_prop:,.0f}")
            st.metric("Gratificación x12", f"${grat_anual_prop:,.0f}")
            st.metric("Colación x12", f"${col_anual_prop:,.0f}")
            st.metric("Movilización x12", f"${mob_anual_prop:,.0f}")

            st.divider()

            # Obtener nivel HAY propuesto y calcular bono
            nivel_hay_prop_str = st.session_state.get("nivel_hay_prop_input", "").strip()
            target_prop_input = st.session_state.get("target_prop_input", 0.0)

            # Siempre mostrar Bono Target
            bono_target_prop = target_prop_input * sal_base_prop
            st.metric(":material/payments: Bono Target", f"${bono_target_prop:,.0f}", delta=f"({target_prop_input} × ${sal_base_prop:,.0f})")

            if beneficios_anual_prop_comp > 0:
                st.metric(":material/payments: Beneficios Adicionales", f"${beneficios_anual_prop_comp:,.0f}")

            total_prop_comp = sal_base_anual_prop + grat_anual_prop + col_anual_prop + mob_anual_prop + bono_target_prop + beneficios_anual_prop_comp
            st.metric("TOTAL ANUALIZADO", f"${total_prop_comp:,.0f}", delta_color="off")
            st.divider()

            # Mostrar valores de Mercado y Promedio Interno con Gap Análisis
            if nivel_hay_prop_str and nivel_hay_prop_str.isdigit():
                try:
                    db_manager = AnalysisDBManager()

                    # Obtener datos de mercado y promedio
                    comp_data = db_manager.get_compensation_by_level(int(nivel_hay_prop_str))
                    avg_data = db_manager.get_compensation_average_by_level(nivel_hay_prop_str)

                    # Seleccionar el campo correcto según el mercado elegido
                    mercado_comparacion_prop = st.session_state.get('mercado_comparacion_info_prop', 'Mercado Financiero')
                    mercado_field = 'mercado_seguros' if mercado_comparacion_prop == 'Mercado Seguros' else 'mercado_financiero'
                    mercado_val = comp_data.get(mercado_field, 0) if comp_data else 0
                    promedio_val = avg_data.get('promedio_anualizado', 0) if avg_data else 0

                    st.caption(f":material/bar_chart: **Estudio de Mercado** (Nivel {nivel_hay_prop_str}, {mercado_comparacion_prop}): **${mercado_val:,.0f}**")

                    # Gap vs Mercado
                    if mercado_val > 0:
                        gap_mercado = total_prop_comp - mercado_val
                        pct_mercado = (gap_mercado / mercado_val * 100) if mercado_val != 0 else 0
                        icon_mercado = ":material/check_circle:" if gap_mercado >= 0 else ":material/warning:"
                        direction = "ARRIBA" if gap_mercado >= 0 else "DEBAJO"
                        st.caption(f"{icon_mercado} {direction} del mercado: **${abs(gap_mercado):,.0f}** ({pct_mercado:+.1f}%)")

                    st.caption(f":material/bar_chart: **Mediana Interna** (Nivel {nivel_hay_prop_str}): **${promedio_val:,.0f}**")

                    # Gap vs Mediana Interna
                    if promedio_val > 0:
                        gap_promedio = total_prop_comp - promedio_val
                        pct_promedio = (gap_promedio / promedio_val * 100) if promedio_val != 0 else 0
                        icon_promedio = ":material/check_circle:" if gap_promedio >= 0 else ":material/warning:"
                        direction = "ARRIBA" if gap_promedio >= 0 else "DEBAJO"
                        st.caption(f"{icon_promedio} {direction} de la mediana: **${abs(gap_promedio):,.0f}** ({pct_promedio:+.1f}%)")
                except Exception as e:
                    st.caption(f":material/bar_chart: Nivel {nivel_hay_prop_str}: Datos no disponibles en BD")
            elif nivel_hay_prop_str:
                st.warning(f":material/warning: Nivel HAY debe ser numérico (Ej: 16, 18, 20)")
            else:
                st.caption(":material/bar_chart: Ingresa Nivel HAY para ver la media de compensación")

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
    if st.button(":material/check_circle: Crear Propuesta", width='stretch', type="primary"):
        with st.spinner("Calculando propuesta..."):
            simulator = Simulator(payroll_engine)

            # Calcular descuentos de estacionamiento
            current_parking_discount = 0
            if has_parking and current_mobility > 0:
                current_parking_discount = current_mobility

            proposal_parking_discount = 0
            if proposal_has_parking and proposal_mobility > 0:
                proposal_parking_discount = proposal_mobility

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
                "nivel_hay_actual_input": str(st.session_state.get("nivel_hay_actual_input", "")),
                "nivel_hay_prop_input": str(st.session_state.get("nivel_hay_prop_input", "")),
                "target_actual": float(st.session_state.get("target_actual_input", 0.0)) if st.session_state.get("target_actual_input") is not None else 0.0,
                "target_propuesta_input": float(st.session_state.get("target_prop_input", 0.0)) if st.session_state.get("target_prop_input") is not None else 0.0,
                "mercado": st.session_state.get("mercado_comparacion_info_prop", "Mercado Financiero")
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

            # Guardar propuesta en historial
            try:
                db_manager = AnalysisDBManager()
                beneficios_snapshot = st.session_state.get("beneficios_data", {})
                proposal_record = {
                    "rut": employee.rut,
                    "nombre": employee.full_name,
                    "empresa": employee.company_name,
                    "cargo": employee.job_title,
                    "sueldo_actual": float(employee.base_salary) if employee.base_salary else 0,
                    "sueldo_propuesto": float(proposal_base_salary) if proposal_base_salary else 0,
                    "diferencia_pesos": float(proposal_base_salary - employee.base_salary) if (proposal_base_salary and employee.base_salary) else 0,
                    "diferencia_pct": ((proposal_base_salary - employee.base_salary) / employee.base_salary * 100) if (employee.base_salary and proposal_base_salary) else 0,
                    "nivel_hay": st.session_state.get("nivel_hay_prop_input", ""),
                    "target": float(st.session_state.get("target_prop_input", 0.0)),
                    "cambio_comp": 0,  # Se puede calcular después si es necesario
                    "cambio_comp_pct": 0,
                    "comentarios": "Propuesta creada desde interfaz",
                    "aguinaldo_navidad_monto": beneficios_snapshot.get("aguinaldo_navidad_monto", 0),
                    "aguinaldo_fiestas_patrias_monto": beneficios_snapshot.get("aguinaldo_fiestas_patrias_monto", 0),
                    "gift_card_monto": beneficios_snapshot.get("gift_card_monto", 0),
                    "bono_vacaciones_actual_monto": beneficios_snapshot.get("bono_vacaciones_actual_monto", 0),
                    "bono_vacaciones_propuesta_monto": beneficios_snapshot.get("bono_vacaciones_propuesta_monto", 0),
                    "beneficios_total_anual_actual": beneficios_snapshot.get("total_anual_actual", 0),
                    "beneficios_total_anual_propuesta": beneficios_snapshot.get("total_anual_propuesta", 0),
                }
                guardado_ok = db_manager.save_proposal(proposal_record)
                if not guardado_ok:
                    st.warning(":material/warning: La propuesta se calculó, pero no se pudo guardar en el historial.")
            except Exception as e:
                # No bloquear la creación de propuesta si falla el guardado en historial
                logger.warning(f"Advertencia: No se pudo guardar propuesta en historial: {e}")
                st.warning(":material/warning: La propuesta se calculó, pero no se pudo guardar en el historial.")

            st.success(":material/check_circle: Propuesta calculada exitosamente")
            st.rerun()
            st.rerun()


@st.cache_data
def calculate_compensation_metrics(base_salary_actual, base_salary_proposal, target_actual, target_propuesta, nivel_hay_actual, nivel_hay_propuesta, mercado):
    """Calcula métricas de compensación con caching."""
    try:
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
        st.header(f":material/bar_chart: Comparativa - {employee.full_name}")

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
    st.dataframe(df_comparison, width='stretch', hide_index=True)

    st.divider()

    # Resumen de impacto
    st.subheader(":material/trending_up: Resumen de Impacto")

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

    # Compensación Anual - Mostrar solo si el usuario habilitó el análisis
    if st.session_state.get("enable_compensation_analysis", False) and "compensation_data" in st.session_state:
        st.subheader(":material/payments: Análisis de Compensación Anual")

        comp_data = st.session_state.compensation_data

        # Mostrar resumen en layout tipo informe (2 columnas)
        col_actual_resume, col_prop_resume = st.columns(2)

        with col_actual_resume:
            st.write("**:material/bar_chart: Datos Actuales**")
            st.write(f"• **Nivel HAY:** {comp_data.get('nivel_hay_actual_input', '—')}")
            st.write(f"• **Target:** {comp_data.get('target_actual', 0.0):.1f} rentas")
            st.write(f"• **Mercado:** {comp_data.get('mercado', '—')}")

        with col_prop_resume:
            st.write("**:material/trending_up: Datos Propuestos**")
            st.write(f"• **Nivel HAY:** {comp_data.get('nivel_hay_prop_input', '—')}")
            st.write(f"• **Target:** {comp_data.get('target_propuesta_input', 0.0):.1f} rentas")
            st.write(f"• **Mercado:** {comp_data.get('mercado', '—')}")

        # Botón para calcular compensación
        if st.button(":material/calculate: Calcular Compensación Anual", key="btn_comp_calc", width='stretch'):
            st.session_state.show_compensation = True

        # Mostrar análisis si se presionó el botón
        if st.session_state.get("show_compensation", False):
            with st.spinner("Calculando métricas de compensación..."):
                try:
                    # Verificar que comparison existe
                    if not comparison:
                        st.error(":material/cancel: No hay comparativa disponible. Crea una propuesta primero.")
                        st.session_state.show_compensation = False
                    else:
                        # Obtener datos para el cálculo
                        base_salary_actual = float(comparison.current.base_salary or 0)
                        base_salary_proposal = float(comparison.proposal.base_salary or 0)
                        target_actual = float(comp_data.get("target_actual", 0.0))
                        target_propuesta = float(comp_data.get("target_propuesta_input", 0.0))
                        nivel_hay_actual = str(comp_data.get("nivel_hay_actual_input", ""))
                        nivel_hay_propuesta = str(comp_data.get("nivel_hay_prop_input", nivel_hay_actual))
                        mercado = str(comp_data.get("mercado", "Mercado Financiero"))

                        st.info(f":material/search: Debug: Base={base_salary_actual}, Target={target_actual}, Nivel={nivel_hay_actual}, Mercado={mercado}")

                        # Calcular métricas
                        metrics = calculate_compensation_metrics(
                            base_salary_actual, base_salary_proposal,
                            target_actual, target_propuesta,
                            nivel_hay_actual, nivel_hay_propuesta, mercado
                        )

                        if metrics is None:
                            st.error(":material/cancel: Error: función de cálculo retornó None")
                        elif metrics:
                            # Tabla comparativa
                            st.divider()
                            st.subheader(":material/bar_chart: Análisis de Compratio y Mediana")

                            comp_table_data = {
                                "Métrica": [
                                    "Compensación Anual",
                                    "Mediana Mercado",
                                    "Compratio %",
                                    "% Variable",
                                    "Bonus Anual"
                                ],
                                "Actual": [
                                    format_peso_chileno(metrics['actual']['annual_compensation']),
                                    format_peso_chileno(metrics['actual']['median']),
                                    f"{metrics['actual']['compratio_pct']:.1f}%",
                                    f"{metrics['actual']['variable_pct']:.1f}%",
                                    format_peso_chileno(metrics['actual']['bono_anualizado']),
                                ],
                                "Propuesta": [
                                    format_peso_chileno(metrics['propuesta']['annual_compensation']),
                                    format_peso_chileno(metrics['propuesta']['median']),
                                    f"{metrics['propuesta']['compratio_pct']:.1f}%",
                                    f"{metrics['propuesta']['variable_pct']:.1f}%",
                                    format_peso_chileno(metrics['propuesta']['bono_anualizado']),
                                ]
                            }

                            df_comp = pd.DataFrame(comp_table_data)
                            st.dataframe(df_comp, width='stretch', hide_index=True)

                            # Resumen de cambios
                            st.divider()
                            st.subheader(":material/balance: Análisis de Cambios")

                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric(
                                    "Comp. Actual",
                                    format_peso_chileno(metrics['actual']['annual_compensation']),
                                    delta=None
                                )
                            with col2:
                                delta_comp = metrics['propuesta']['annual_compensation'] - metrics['actual']['annual_compensation']
                                st.metric(
                                    "Comp. Propuesta",
                                    format_peso_chileno(metrics['propuesta']['annual_compensation']),
                                    delta=format_peso_chileno(delta_comp) if delta_comp != 0 else "Sin cambio",
                                    delta_color="off"
                                )
                            with col3:
                                delta_compratio = metrics['propuesta']['compratio_pct'] - metrics['actual']['compratio_pct']
                                st.metric(
                                    "Cambio Compratio",
                                    f"{metrics['propuesta']['compratio_pct']:.1f}%",
                                    delta=f"{delta_compratio:+.1f}%" if delta_compratio != 0 else "Sin cambio",
                                    delta_color="off"
                                )

                            # Análisis de equidad
                            st.divider()
                            st.subheader(":material/trending_up: Posicionamiento en Mercado")

                            if metrics['actual']['median'] > 0:
                                actual_compratio = metrics['actual']['compratio_pct']
                                if actual_compratio < 80:
                                    st.warning(f":material/warning: Compensación BAJO mercado (Compratio {actual_compratio:.1f}%)")
                                elif actual_compratio < 100:
                                    st.info(f"ℹ️ Compensación en RANGO BAJO (Compratio {actual_compratio:.1f}%)")
                                elif actual_compratio < 120:
                                    st.success(f":material/check_circle: Compensación COMPETITIVA (Compratio {actual_compratio:.1f}%)")
                                else:
                                    st.error(f":material/warning: Compensación SOBRE mercado (Compratio {actual_compratio:.1f}%)")

                                # Análisis de la propuesta
                                proposal_compratio = metrics['propuesta']['compratio_pct']
                                if proposal_compratio > actual_compratio:
                                    st.success(f":material/check_circle: Propuesta MEJORA equidad: {proposal_compratio:.1f}% vs {actual_compratio:.1f}%")
                                elif proposal_compratio == actual_compratio:
                                    st.info("ℹ️ Propuesta MANTIENE equidad actual")
                                else:
                                    st.warning(f":material/warning: Propuesta REDUCE equidad: {proposal_compratio:.1f}% vs {actual_compratio:.1f}%")
                        else:
                            st.error(":material/cancel: No se pudo calcular la compensación. Verifica que Nivel HAY esté completado.")
                except Exception as e:
                    st.error(f":material/cancel: Error al calcular compensación: {str(e)}")

        st.divider()

    # Historial de Sueldos
    st.subheader(":material/trending_up: Historial de Sueldos")

    buk_client = get_buk_client()
    salary_history = buk_client.get_salary_history(employee.rut)

    if salary_history:
        # Preparar datos para tabla
        import pandas as pd

        # Filtrar registros: excluir mayo 2019 y anteriores
        filtered_history = [record for record in salary_history if record.get("start_date", "")[:7] > "2019-05"]

        db_ipc = AnalysisDBManager()

        history_data = []
        sobrepasa_ipc = []  # Rastrear qué filas sobrepasan el IPC
        for i, record in enumerate(filtered_history):
            start = record.get("start_date", "")
            wage = record.get("base_wage", 0)

            # Extraer solo mes y año del start_date (formato YYYY-MM-DD)
            periodo = start[:7] if start else "N/A"

            # Calcular variación respecto al mes anterior (el siguiente en la lista ordenada al revés)
            variation = ""
            variation_pct = ""
            skip_record = False
            es_mayor_ipc = False

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

                        es_mayor_ipc = db_ipc.aumento_supera_ipc(periodo, change_pct)

            if not skip_record:
                history_data.append({
                    "Periodo": periodo,
                    "Sueldo Base": f"${wage:,.0f}",
                    "Variación ($)": variation,
                    "Variación (%)": variation_pct,
                })
                sobrepasa_ipc.append(es_mayor_ipc)

        df = pd.DataFrame(history_data)

        def _resaltar_sobre_ipc(row):
            idx = row.name
            if idx < len(sobrepasa_ipc) and sobrepasa_ipc[idx]:
                return ['background-color: #B3E5FC; color: #000000'] * len(row)
            return [''] * len(row)

        st.dataframe(df.style.apply(_resaltar_sobre_ipc, axis=1), width='stretch', hide_index=True)
        st.caption(":blue[:material/circle:] Celeste = Aumento sobrepasa el IPC registrado | Blanco = Igual o menor al IPC, o sin IPC para comparar")

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

        # Gráfico de evolución salarial (el mismo que se incluye en el PDF)
        if len(filtered_history) >= 2:
            try:
                ipc_history_list = db_ipc.get_ipc_history()
                if ipc_history_list:
                    from src.pdf_exporter import PDFExporter

                    # Mismo criterio "sobrepasa IPC" que la tabla de arriba, indexado
                    # por período, para que el punto resaltado en el gráfico coincida
                    # exactamente con la fila resaltada en la tabla.
                    sobrepasa_por_periodo = {
                        row["Periodo"]: sobrepasa_ipc[idx]
                        for idx, row in enumerate(history_data)
                    }

                    pdf_exp = PDFExporter()
                    fig, _ = pdf_exp._build_salary_evolution_figure(
                        filtered_history, ipc_history_list, sobrepasa_por_periodo=sobrepasa_por_periodo
                    )
                    if fig is not None:
                        st.pyplot(fig)
                        import matplotlib.pyplot as plt
                        plt.close(fig)
                    else:
                        st.warning(":material/warning: No se pudo construir el gráfico de evolución (datos insuficientes para este empleado).")
                else:
                    st.warning(":material/warning: No hay histórico de IPC cargado — ve a Configuración para cargarlo y ver el gráfico de evolución.")
            except Exception as e:
                st.warning(f":material/warning: No se pudo generar el gráfico de evolución: {e}")
    else:
        st.info("No se encontró historial de sueldos")

    st.divider()

    # Exportar
    st.subheader(":material/save: Exportar Propuesta")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(":material/description: Descargar Excel", width='stretch'):
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
                st.success(":material/check_circle: Excel generado correctamente")

                # Log exportación
                try:
                    db_manager = AnalysisDBManager()
                    db_manager.log_export({
                        "empresa": employee.company_name,
                        "area": "N/A",
                        "cantidad_empleados": 1,
                        "archivo": filename,
                        "tipo": "excel"
                    })
                except Exception as e:
                    logger.warning(f"No se pudo loguear exportación: {e}")
            else:
                st.error(":material/cancel: Error al generar Excel")

    with col2:
        if st.button(":material/bookmark: Descargar PDF", width='stretch'):
            filename = f"Propuesta_Renta_{employee.rut.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_exporter = PDFExporter()

            # Obtener logo de la empresa
            logo_path = get_company_logo(employee.company_name)

            # Preparar datos de compensación para PDF - Traer datos reales del calculador
            comp_data = st.session_state.get("compensation_data", {})

            # Extraer datos reales del calculador - usar compensation_data que se guardó al crear propuesta
            nivel_hay_actual = comp_data.get("nivel_hay_actual_input", st.session_state.get("nivel_hay_actual_input", "—"))
            nivel_hay_propuesto = comp_data.get("nivel_hay_prop_input", st.session_state.get("nivel_hay_prop_input", "—"))
            target_actual = comp_data.get("target_actual", st.session_state.get("target_actual_input", 0.0))
            target_propuesto = comp_data.get("target_propuesta_input", st.session_state.get("target_prop_input", 0.0))

            # Calcular bonos y compensaciones desde el comparison
            sal_base_actual = float(comparison.current.base_salary) if comparison and comparison.current else employee.base_salary
            sal_base_propuesto = float(comparison.proposal.base_salary) if comparison and comparison.proposal else sal_base_actual

            bono_actual = target_actual * sal_base_actual if target_actual > 0 else 0
            bono_propuesto = target_propuesto * sal_base_propuesto if target_propuesto > 0 else 0

            # Total anualizado (sueldos + bonos)
            sal_anual_actual = sal_base_actual * 12
            sal_anual_propuesto = sal_base_propuesto * 12

            mercado_actual = st.session_state.get("mercado_comparacion_main", "Mercado Financiero")
            mercado_propuesto = st.session_state.get("mercado_comparacion_info_prop", "Mercado Financiero")

            # Mediana de mercado y Compratio (posición media) reales, calculados
            # con el mismo motor que usa la pantalla de "Análisis de Compratio y
            # Mediana" (src/compensation_comparator.py). Antes estos valores
            # estaban hardcodeados como números de prueba fijos.
            from src.compensation_comparator import CompensationComparator, CompensationScenario

            comparador_pdf = CompensationComparator(AnalysisDBManager(), get_payroll_engine())
            escenario_actual_pdf = CompensationScenario(
                base_salary=sal_base_actual,
                target_rentas=target_actual if target_actual else 0.0,
                nivel_hay=str(nivel_hay_actual) if nivel_hay_actual and nivel_hay_actual != "—" else "0",
                mercado=mercado_actual,
            )
            escenario_propuesto_pdf = CompensationScenario(
                base_salary=sal_base_propuesto,
                target_rentas=target_propuesto if target_propuesto else 0.0,
                nivel_hay=str(nivel_hay_propuesto) if nivel_hay_propuesto and nivel_hay_propuesto != "—" else str(nivel_hay_actual) if nivel_hay_actual and nivel_hay_actual != "—" else "0",
                mercado=mercado_propuesto,
            )
            metrics_pdf = comparador_pdf.compare(escenario_actual_pdf, escenario_propuesto_pdf)

            compensation_pdf_data = {
                "bono_actual": bono_actual,
                "bono_propuesto": bono_propuesto,
                "mercado_actual": mercado_actual,
                "mercado_propuesto": mercado_propuesto,
                "nivel_hay_actual": nivel_hay_actual,
                "nivel_hay_propuesto": nivel_hay_propuesto,
                "posicion_media_actual": metrics_pdf["actual"]["compratio_pct"],
                "posicion_media_propuesto": metrics_pdf["propuesta"]["compratio_pct"],
                "mediana_actual": metrics_pdf["actual"]["median"],
                "mediana_propuesto": metrics_pdf["propuesta"]["median"],
                "pct_variable_actual": (target_actual * 100) if target_actual > 0 else 0,
                "pct_variable_propuesto": (target_propuesto * 100) if target_propuesto > 0 else 0,
                "comp_anual_actual": sal_anual_actual + bono_actual,
                "comp_anual_propuesto": sal_anual_propuesto + bono_propuesto,
            }

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
                compensation_data=compensation_pdf_data,
                beneficios_data=st.session_state.get("beneficios_data", {}),
            )

            if success:
                with open(filename, "rb") as f:
                    st.download_button(
                        label="Descargar archivo PDF",
                        data=f.read(),
                        file_name=filename,
                        mime="application/pdf"
                    )
                st.success(":material/check_circle: PDF generado correctamente")

                # Log exportación
                try:
                    db_manager = AnalysisDBManager()
                    db_manager.log_export({
                        "empresa": employee.company_name,
                        "area": "N/A",
                        "cantidad_empleados": 1,
                        "archivo": filename,
                        "tipo": "pdf"
                    })
                except Exception as e:
                    logger.warning(f"No se pudo loguear exportación PDF: {e}")
            else:
                st.error(":material/cancel: Error al generar PDF")


def configuration_section():
    """Sección de configuración de parámetros."""
    import json

    st.header(":material/settings: Configuración de Parámetros")

    with open("config/parameters.json") as f:
        parameters = json.load(f)

    # Dividir en columnas para mejor visualización
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader(":material/bar_chart: Valores Mensuales")
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
        st.subheader(":material/straighten: Topes Previsionales")
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
        st.subheader(":material/trending_up: Porcentajes")
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

    st.divider()

    # Porcentajes de AFP por fondo
    st.subheader(":material/credit_card: Tasas AFP (Fondo + Comisión)")
    afp_rates = parameters.get("afp_rates", {
        "capital": 11.44,
        "cuprum": 11.44,
        "habitat": 11.27,
        "planvital": 11.16,
        "provida": 11.45,
        "modelo": 10.58,
        "uno": 10.46
    })

    col_afp1, col_afp2, col_afp3, col_afp4 = st.columns(4)

    with col_afp1:
        afp_capital = st.number_input("Capital %", value=float(afp_rates.get("capital", 11.44)), step=0.01, format="%.2f", key="afp_capital")
        afp_habitat = st.number_input("Habitat %", value=float(afp_rates.get("habitat", 11.27)), step=0.01, format="%.2f", key="afp_habitat")

    with col_afp2:
        afp_cuprum = st.number_input("Cuprum %", value=float(afp_rates.get("cuprum", 11.44)), step=0.01, format="%.2f", key="afp_cuprum")
        afp_planvital = st.number_input("PlanVital %", value=float(afp_rates.get("planvital", 11.16)), step=0.01, format="%.2f", key="afp_planvital")

    with col_afp3:
        afp_provida = st.number_input("ProVida %", value=float(afp_rates.get("provida", 11.45)), step=0.01, format="%.2f", key="afp_provida")
        afp_modelo = st.number_input("Modelo %", value=float(afp_rates.get("modelo", 10.58)), step=0.01, format="%.2f", key="afp_modelo")

    with col_afp4:
        afp_uno = st.number_input("Uno %", value=float(afp_rates.get("uno", 10.46)), step=0.01, format="%.2f", key="afp_uno")

    st.divider()

    # Beneficios adicionales (costo empresa, no afectan la liquidación)
    st.subheader(":material/payments: Beneficios Adicionales (Costo Empresa)")
    st.caption("Montos anuales de referencia. No afectan AFP/Salud/Impuesto ni el líquido del trabajador — solo se usan para costear el total anual.")

    beneficios = AnalysisDBManager().get_beneficios_config()

    col_ben1, col_ben2 = st.columns(2)

    with col_ben1:
        aguinaldo_navidad = st.number_input(
            "Aguinaldo de Navidad ($)",
            value=int(beneficios.get("aguinaldo_navidad", 60000)),
            min_value=0,
            step=1000,
            key="cfg_aguinaldo_navidad",
        )
        aguinaldo_fiestas_patrias = st.number_input(
            "Aguinaldo Fiestas Patrias ($)",
            value=int(beneficios.get("aguinaldo_fiestas_patrias", 60000)),
            min_value=0,
            step=1000,
            key="cfg_aguinaldo_fiestas_patrias",
        )
        gift_card = st.number_input(
            "Gift Card ($)",
            value=int(beneficios.get("gift_card", 50000)),
            min_value=0,
            step=1000,
            key="cfg_gift_card",
        )

    with col_ben2:
        bono_vacaciones_monto = st.number_input(
            "Bono Vacaciones ($)",
            value=int(beneficios.get("bono_vacaciones_monto", 200000)),
            min_value=0,
            step=1000,
            key="cfg_bono_vacaciones_monto",
        )
        bono_vacaciones_tope_renta = st.number_input(
            "Tope de Renta para Bono Vacaciones ($)",
            value=int(beneficios.get("bono_vacaciones_tope_renta", 2500000)),
            min_value=0,
            step=10000,
            key="cfg_bono_vacaciones_tope_renta",
            help="Aplica si (Sueldo Base + Gratificación) es menor a este monto.",
        )

    # Botón para guardar cambios
    if st.button(":material/save: Guardar Cambios", width='stretch', type="primary"):
        # Actualizar parámetros
        parameters["uf_value"] = uf_value
        parameters["utm_value"] = utm_value
        parameters["imm_value"] = imm_value
        parameters["tope_afp_uf"] = tope_afp_uf
        parameters["tope_afc_uf"] = tope_afc_uf
        parameters["afp_percent"] = afp_percent
        parameters["salud_percent"] = salud_percent
        parameters["afc_trabajador_indefinido"] = afc_indefinido
        parameters["afp_rates"] = {
            "capital": afp_capital,
            "cuprum": afp_cuprum,
            "habitat": afp_habitat,
            "planvital": afp_planvital,
            "provida": afp_provida,
            "modelo": afp_modelo,
            "uno": afp_uno
        }
        # Guardar en archivo
        with open("config/parameters.json", "w") as f:
            json.dump(parameters, f, indent=2)

        # Beneficios adicionales se guardan en la BD, para que una
        # actualización hecha desde la app esté disponible de inmediato.
        beneficios_dict = {
            "aguinaldo_navidad": aguinaldo_navidad,
            "aguinaldo_fiestas_patrias": aguinaldo_fiestas_patrias,
            "gift_card": gift_card,
            "bono_vacaciones_monto": bono_vacaciones_monto,
            "bono_vacaciones_tope_renta": bono_vacaciones_tope_renta,
        }
        beneficios_guardado_ok = AnalysisDBManager().save_beneficios_config(beneficios_dict)

        # Además se comitea a GitHub, para que sobreviva a un reinicio real
        # del contenedor de Streamlit Cloud (que reclona el repo desde git).
        beneficios_sync_ok = False
        beneficios_sync_detalle = ""
        if beneficios_guardado_ok:
            beneficios_sync_ok, beneficios_sync_detalle = commit_json_file(
                "config/beneficios_config.json",
                beneficios_dict,
                "Actualizar configuración de Beneficios Adicionales",
            )

        if beneficios_guardado_ok and beneficios_sync_ok:
            st.success(":material/check_circle: Parámetros actualizados correctamente")
        elif beneficios_guardado_ok and not github_sync_configured():
            st.warning(":material/warning: Beneficios Adicionales guardados, pero sin sincronización con GitHub configurada — se perderán en un reinicio real de la app. Configura `[github]` en los Secrets de Streamlit Cloud.")
        elif beneficios_guardado_ok:
            st.warning(f":material/warning: Beneficios Adicionales guardados, pero no se pudo sincronizar con GitHub — se perderán en un reinicio real de la app.\n\n**Detalle:** {beneficios_sync_detalle}")
        else:
            st.warning(":material/warning: Parámetros generales guardados, pero no se pudieron guardar los Beneficios Adicionales.")
        st.balloons()

    st.divider()

    st.info(":material/lightbulb: **Edita los valores manualmente** (UF, UTM, IMM) en los campos arriba y haz clic en ':material/save: Guardar Cambios' para actualizar")

    st.divider()

    # Mostrar tabla resumen
    st.subheader(":material/assignment: Resumen Actual")
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
    st.dataframe(df_summary, width='stretch', hide_index=True)

    st.divider()

    # Sección de IPC
    st.subheader(":material/bar_chart: Histórico de IPC")

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
            if st.button("Guardar IPC", width='stretch', key="save_ipc_btn"):
                if new_mes and new_ipc > 0:
                    if db.upsert_ipc(new_mes, new_ipc):
                        # Comitear el histórico completo a GitHub, para que sobreviva
                        # a un reinicio real del contenedor de Streamlit Cloud.
                        ipc_sync_ok, ipc_sync_detalle = commit_json_file(
                            "config/ipc_history.json",
                            db.get_ipc_history_dict(),
                            f"Actualizar IPC {new_mes}",
                        )
                        if ipc_sync_ok:
                            st.success(f":material/check_circle: IPC {new_mes}: {new_ipc:.4f} guardado y sincronizado")
                        elif not github_sync_configured():
                            st.warning(f":material/warning: IPC {new_mes} guardado, pero sin sincronización con GitHub configurada — se perderá en un reinicio real de la app.")
                        else:
                            st.warning(f":material/warning: IPC {new_mes} guardado, pero no se pudo sincronizar con GitHub — se perderá en un reinicio real de la app.\n\n**Detalle:** {ipc_sync_detalle}")
                    else:
                        st.error("Error al guardar IPC")
                else:
                    st.warning("Ingresa mes y valor válidos")

    with col2:
        st.write("")  # Spacing
        if st.button(":material/refresh: Recargar", width='stretch', key="reload_ipc"):
            st.rerun()

    ipc_seed = db.leer_ipc_seed_desde_archivo()
    with st.expander(f":material/database: Cargar histórico completo de IPC ({len(ipc_seed)} meses de referencia)"):
        st.caption(
            "Carga de una sola vez el histórico de reajustes por IPC de la empresa (marzo, julio y "
            "noviembre de cada año). Útil para completar meses faltantes sin ingresarlos uno por uno. "
            "Sobrescribe el valor de los meses que ya estén cargados."
        )
        if st.button(":material/upload: Cargar histórico completo", key="load_ipc_seed_btn"):
            cargados = 0
            for mes_seed, valor_seed in ipc_seed.items():
                if db.upsert_ipc(mes_seed, valor_seed):
                    cargados += 1

            ipc_sync_ok, ipc_sync_detalle = commit_json_file(
                "config/ipc_history.json",
                db.get_ipc_history_dict(),
                "Cargar histórico completo de IPC",
            )

            if ipc_sync_ok:
                st.success(f":material/check_circle: {cargados} meses de IPC cargados y sincronizados")
            elif not github_sync_configured():
                st.warning(f":material/warning: {cargados} meses de IPC cargados, pero sin sincronización con GitHub configurada — se perderán en un reinicio real de la app.")
            else:
                st.warning(f":material/warning: {cargados} meses de IPC cargados, pero no se pudo sincronizar con GitHub.\n\n**Detalle:** {ipc_sync_detalle}")
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
        st.dataframe(df_ipc, width='stretch', hide_index=True)
    else:
        st.info("No hay IPCs registrados")

    st.divider()

    # Sección de Compensaciones
    st.subheader(":material/payments: Tabla de Compensaciones por Nivel")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption("Carga/Actualiza tabla de compensaciones")
        uploaded_comp = st.file_uploader(
            ":material/download: Selecciona archivo Excel",
            type=["xlsx", "xls"],
            key="comp_uploader",
            help="Columnas: Nivel | Mercado Financiero | Mercado Seguros | Descripción"
        )

        if uploaded_comp is not None:
            try:
                df_comp = pd.read_excel(uploaded_comp)
                st.success(f":material/check_circle: Archivo cargado: {len(df_comp)} niveles")

                with st.expander(":material/visibility: Vista previa"):
                    st.dataframe(df_comp, width='stretch', hide_index=True)

                if st.button(":material/save: Guardar en Base de Datos", type="primary", width='stretch', key="save_comp_btn"):
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

                        st.success(f":material/check_circle: Guardado: {insertados} niveles, {errores} errores")
                        st.rerun()

            except Exception as e:
                st.error(f":material/cancel: Error: {str(e)}")

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
        st.dataframe(df_comp_display, width='stretch', hide_index=True)
    else:
        st.info("No hay compensaciones cargadas. Carga un archivo Excel.")

    st.divider()

    # Sección de UF
    st.subheader(":material/attach_money: Histórico de UF (Unidad de Fomento)")

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
            if st.button("Guardar UF", width='stretch', key="save_uf_btn"):
                if new_mes_uf and new_uf > 0:
                    if db.upsert_uf(new_mes_uf, new_uf):
                        st.success(f":material/check_circle: UF {new_mes_uf}: ${new_uf:,.2f} guardada")
                        st.rerun()
                    else:
                        st.error("Error al guardar UF")
                else:
                    st.warning("Ingresa mes y valor válidos")

    with col2:
        st.write("")  # Spacing
        if st.button(":material/refresh: Recargar", width='stretch', key="reload_uf"):
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
        st.dataframe(df_uf, width='stretch', hide_index=True)
    else:
        st.info("No hay UF registradas")

    st.divider()

    # Sección de Promedios de Compensación Interna
    st.subheader(":material/trending_up: Promedios de Compensación Interna (Competitividad)")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption("Calcula promedios de compensación anualizada por Nivel HAY")
        st.info(
            ":material/lightbulb: Esta sección permite:\n"
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
        st.warning(":material/warning: No hay empresas cargadas. Carga datos primero en la pestaña ANÁLISIS.")
    else:
        empresa_seleccionada = st.selectbox(
            "Selecciona Empresa para calcular promedios:",
            options=empresas,
            key="empresa_promedios"
        )

        # Botón para calcular promedios
        if st.button(":material/calculate: Calcular Promedios (Prueba)", width='stretch', key="calc_averages"):
            try:
                from src.analysis.internal_competitiveness import InternalCompetitivenessCalculator

                with st.spinner(f"Calculando promedios para {empresa_seleccionada}..."):
                    calculator = InternalCompetitivenessCalculator(db)
                    resultados = calculator.calcular_promedios(empresa=empresa_seleccionada)

                if "error" in resultados:
                    st.error(f":material/cancel: {resultados['error']}")
                else:
                    st.success(f":material/check_circle: Se calcularon promedios para {len(resultados)} niveles de {empresa_seleccionada}")

                    # Mostrar tabla de promedios calculados
                    st.subheader(":material/bar_chart: Promedios Calculados")

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
                    st.dataframe(df_promedios, width='stretch', hide_index=True)

                    # GUARDAR AUTOMÁTICAMENTE
                    st.divider()
                    st.info("Guardando promedios en BD...")

                    if calculator.guardar_promedios(resultados):
                        st.success(":material/check_circle: Promedios guardados en BD correctamente")
                        st.info("Los promedios están ahora disponibles en COMPENSACIONES para todos los empleados")

                        # Crear Excel para descarga
                        from io import BytesIO
                        excel_buffer = BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            df_promedios.to_excel(writer, sheet_name='Promedios', index=False)
                        excel_buffer.seek(0)

                        st.download_button(
                            label=":material/download: Descargar Excel con Promedios",
                            data=excel_buffer.getvalue(),
                            file_name=f"promedios_{empresa_seleccionada.replace(' ', '_')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                        st.balloons()
                        st.rerun()
                    else:
                        st.error(":material/cancel: Error al guardar promedios")

            except ImportError as e:
                st.error(f":material/cancel: Error de importación: {str(e)}")
            except Exception as e:
                st.error(f":material/cancel: Error: {str(e)}")

    st.divider()

    # Mostrar promedios actuales en BD
    st.subheader(":material/assignment: Promedios Almacenados en Base de Datos")

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
        st.dataframe(df_bd, width='stretch', hide_index=True)
    else:
        st.info("No hay promedios calculados aún. Haz clic en 'Calcular Promedios' arriba.")

    st.divider()

    # Sección de Detalle de Compensación por Empleado
    st.subheader(":material/assignment: Detalle de Compensación por Empleado")

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

    if empresa_detalle and st.button(":material/download: Generar Excel de Detalle", width='stretch', key="gen_detalle_excel"):
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
                st.error(f":material/cancel: No hay empleados para {empresa_detalle}")
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
                            st.warning(f":material/warning: Error con {emp.get('nombre')}: {str(e)}")
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
                            label=":material/download: Descargar Excel Detallado",
                            data=excel_buffer.getvalue(),
                            file_name=f"detalle_compensacion_{empresa_detalle.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_detalle"
                        )

                        st.success(f":material/check_circle: Excel generado con {len(df_detalle)} empleados")

                    else:
                        st.error(":material/cancel: No se pudo procesar ningún empleado")

        except Exception as e:
            st.error(f":material/cancel: Error: {str(e)}")
            import traceback
            st.error(traceback.format_exc())


def calculator_section():
    """Sección calculadora de sueldos."""
    st.header(":material/calculate: Calculadora de Sueldos")

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

    # Método de entrada - Cargar parámetros actuales cada vez
    # Leer parámetros del archivo para asegurar valores actuales
    with open("config/parameters.json") as f:
        current_params = json.load(f)
    payroll_engine = PayrollEngine(current_params)

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader(":material/bar_chart: Datos del Empleado")

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

        # Obtener valor de UF para Movilización
        db_mgr = AnalysisDBManager()
        mes_actual = datetime.now().strftime("%Y-%m")
        uf_valor = db_mgr.get_uf(mes_actual) or 40873.77  # Valor por defecto

        # Calcular sugerencia de movilización: 2.44 * UF
        movilizacion_sugerida = int(2.44 * uf_valor)

        col1, col2, col3 = st.columns(3)
        with col1:
            collation = st.number_input("Colación", value=130000, min_value=0, step=1000, key="calc_col")
        with col2:
            mobility = st.number_input("Movilización", value=movilizacion_sugerida, min_value=0, step=1000, key="calc_mob", help=f"Sugerencia: 2.44 × UF = ${movilizacion_sugerida:,.0f}")
        with col3:
            other_taxable = st.number_input("Otros Imp.", value=0, min_value=0, step=1000, key="calc_other")

    with col_right:
        st.subheader(":material/settings: Opciones")

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
    if st.button(":material/calculate: Calcular Liquidación", width='stretch', type="primary"):
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

            st.success(":material/check_circle: Liquidación calculada")

    # Mostrar resultado si existe
    if "last_calculation" in st.session_state and st.session_state.last_calculation:
        st.divider()
        st.subheader(":material/assignment: Resultado")

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
            st.dataframe(df_haberes, width='stretch', hide_index=True)

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
            st.dataframe(df_descuentos, width='stretch', hide_index=True)

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
            st.dataframe(df_no_imponibles, width='stretch', hide_index=True)

            st.markdown(f"**Total: ${calc.total_non_taxable:,.0f}**")

        with col2:
            st.markdown("**OTROS DESCUENTOS**")
            parking_discount = mobility_val if has_parking else 0
            otros_data = {
                "Concepto": ["Estacionamiento"],
                "Monto": [f"${parking_discount:,.0f}"]
            }
            df_otros = pd.DataFrame(otros_data)
            st.dataframe(df_otros, width='stretch', hide_index=True)

            st.markdown(f"**Total: ${parking_discount:,.0f}**")

        st.divider()

        # APORTES EMPLEADOR (NUEVO SEGMENTO)
        st.markdown("**APORTES EMPLEADOR (Tope Imponible Mensual)**")

        # Obtener valor de UF del período actual
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
        st.dataframe(df_aportes, width='stretch', hide_index=True)

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
            st.metric(":material/payments: LÍQUIDO (Empleado)", f"${final_liquid:,.0f}", delta=None)

        st.divider()

        # Botones de exportación
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button(":material/download: Excel", width='stretch', key="export_excel_calc"):
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
                            label=":material/download: Descargar Excel",
                            data=f.read(),
                            file_name=f"Liquidacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    os.remove(temp_path)
                    st.success(":material/check_circle: Excel generado")
                except Exception as e:
                    st.error(f":material/cancel: Error al generar Excel: {str(e)}")

        with col2:
            if st.button(":material/description: PDF", width='stretch', key="export_pdf_calc"):
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
                            label=":material/download: Descargar PDF",
                            data=f.read(),
                            file_name=f"Liquidacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf"
                        )

                    os.remove(temp_path)
                    st.success(":material/check_circle: PDF generado")
                except Exception as e:
                    st.error(f":material/cancel: Error al generar PDF: {str(e)}")


def main():
    """Función principal."""
    initialize_session_state()

    # === VERIFICAR AUTENTICACIÓN ===
    if not st.session_state.authenticated:
        db_manager = AnalysisDBManager()
        auth_manager = AuthManager()
        render_login_page(auth_manager)
        st.stop()

    # === USUARIO AUTENTICADO - MOSTRAR APLICACIÓN ===

    # Sidebar: Información del usuario y logout
    with st.sidebar:
        st.header(":material/settings: Opciones Globales")

        # Información del usuario
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**:material/person: {st.session_state.usuario}**")
            st.caption(f"Rol: {st.session_state.rol.upper()}")
        with col2:
            if st.button(":material/logout: Logout", width='stretch'):
                st.session_state.authenticated = False
                st.session_state.usuario = None
                st.session_state.rol = None
                st.session_state.user_id = None
                st.rerun()

        st.divider()

        if st.session_state.rol == "admin":
            menu_options = [
                "Calculadora", "Análisis", "Propuestas", "Compensaciones",
                "Dotación", "Configuración", "Gestión de Usuarios",
            ]
            menu_icons = [
                "calculator", "bar-chart-line", "file-earmark-text", "cash-coin",
                "compass", "gear", "people",
            ]
        else:
            menu_options = ["Calculadora", "Análisis", "Propuestas", "Compensaciones"]
            menu_icons = ["calculator", "bar-chart-line", "file-earmark-text", "cash-coin"]

        selected_section = option_menu(
            menu_title=None,
            options=menu_options,
            icons=menu_icons,
            default_index=0,
            key="main_nav",
            styles={
                "container": {"padding": "0!important", "background-color": "#111111"},
                "icon": {"color": "#3B78C3", "font-size": "16px"},
                "nav-link": {
                    "font-size": "14px",
                    "text-align": "left",
                    "margin": "2px",
                    "color": "#FAFAFA",
                    "--hover-color": "#222222",
                },
                "nav-link-selected": {"background-color": "#3B78C3", "color": "#FFFFFF"},
            },
        )

        # Opción propia del módulo Propuestas: solo se despliega si está seleccionado
        if selected_section == "Propuestas":
            st.checkbox(":material/bar_chart: Habilitar Analizador de Renta", key="enable_compensation_analysis",
                       help="Muestra las secciones de análisis de compensación en PROPUESTAS")

    # Header
    if os.path.exists(LOGO_HORIZONTAL_PATH):
        st.markdown(
            f'<div class="app-logo">'
            f'<img src="data:image/png;base64,{logo_base64(LOGO_HORIZONTAL_PATH)}" />'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        # Reserva por si el archivo del logo no está disponible.
        st.markdown('<p class="main-header">💰 Suite ARP IA</p>', unsafe_allow_html=True)
        st.markdown("Suite de compensaciones ARP")

    # Secciones principales - Navegación en el menú lateral, según rol
    if selected_section == "Calculadora":
        # === SECCIÓN CALCULADORA ===
        calculator_section()

    elif selected_section == "Análisis":
        # === SECCIÓN ANÁLISIS ===
        from src.analysis.streamlit_ui import show_analysis_section
        buk_client = get_buk_client()
        show_analysis_section(buk_client)

    elif selected_section == "Propuestas":
        # === SECCIÓN PROPUESTAS ===
        # Detectar si hay empleado seleccionado desde ANÁLISIS
        if "empleado_para_propuesta" in st.session_state and st.session_state.empleado_para_propuesta:
            datos_emp = st.session_state.empleado_para_propuesta
            try:
                buk_client = get_buk_client()
                employee = buk_client.search_employee(rut=datos_emp["rut"])
                if employee:
                    st.session_state.current_employee = employee
                    st.session_state.propuestas_subtab = "propuesta"
                    st.success(f":material/check_circle: Empleado cargado desde ANÁLISIS: {employee.full_name}")
                    del st.session_state.empleado_para_propuesta
            except:
                pass

        if st.session_state.propuestas_subtab == "propuesta":
            # Sección de creación de propuesta
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button(":material/arrow_back: Volver a Buscar", width='stretch', key="back_to_search"):
                    st.session_state.propuestas_subtab = "buscar"
                    st.rerun()
            with col3:
                if st.button("Ver Comparativa :material/arrow_forward:", width='stretch', key="to_comparison"):
                    st.session_state.propuestas_subtab = "comparativa"
                    st.rerun()

            proposal_section()

        elif st.session_state.propuestas_subtab == "comparativa":
            # Sección de comparativa
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button(":material/arrow_back: Crear Propuesta", width='stretch', key="back_to_proposal"):
                    st.session_state.propuestas_subtab = "propuesta"
                    st.rerun()
            with col3:
                if st.button("Buscar Nuevo :material/arrow_forward:", width='stretch', key="search_new"):
                    st.session_state.propuestas_subtab = "buscar"
                    st.rerun()

            comparison_section()

        else:
            # Sección de búsqueda (default)
            col1, col2, col3 = st.columns([2, 1, 1])
            with col3:
                if st.session_state.current_employee:
                    if st.button("Crear Propuesta :material/arrow_forward:", width='stretch', key="to_proposal"):
                        st.session_state.propuestas_subtab = "propuesta"
                        st.rerun()

            search_employee_section()

    elif selected_section == "Compensaciones":
        # === SECCIÓN COMPENSACIONES ===
        from src.analysis.compensaciones_ui import show_compensations_section
        buk_client = get_buk_client()
        show_compensations_section(buk_client)

    elif selected_section == "Dotación" and st.session_state.rol == "admin":
        # === SECCIÓN DOTACIÓN ===
        from src.analysis.dotacion_ui import show_dotacion_section
        show_dotacion_section(get_payroll_engine())

    elif selected_section == "Configuración" and st.session_state.rol == "admin":
        # === SECCIÓN CONFIGURACIÓN ===
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button(":material/arrow_back: Volver", width='stretch', key="back_from_config"):
                st.session_state.main_tab = "propuestas"
                st.rerun()

        configuration_section()

    elif selected_section == "Gestión de Usuarios" and st.session_state.rol == "admin":
        # === SECCIÓN GESTIÓN DE USUARIOS ===
        db_manager = AnalysisDBManager()
        auth_manager = AuthManager()
        render_user_management(auth_manager)


if __name__ == "__main__":
    main()
