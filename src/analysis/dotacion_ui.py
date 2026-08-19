"""Pestaña de planificación y control de dotación.

Segregada por empresa y área. Muestra el plan contra la dotación real y
cuánto costaría cubrir las vacantes.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from src.analysis.db_manager import AnalysisDBManager
from src.analysis.dotacion_manager import (
    COMPLETA, MERCADOS, SOBRE, VACANTES, DotacionManager,
)
from src.utils.formatters import format_peso_chileno

# La empresa con el plan de dotación más definido, así el panel abre con datos.
EMPRESA_POR_DEFECTO = "4Life Seguros de Vida S.A."

COLOR_ESTADO = {
    COMPLETA: "#2F6B4F",
    VACANTES: "#B26B00",
    SOBRE: "#B23A36",
    "Sin planificar": "#8A96A8",
}


def show_dotacion_section(payroll_engine=None):
    """Renderiza la pestaña completa."""
    st.header("🧭 Planificación de Dotación")
    st.caption("Plan por empresa y área, contrastado con la dotación real y el costo de cubrir las vacantes.")

    db = AnalysisDBManager()
    gestor = DotacionManager(db, payroll_engine)

    empresas = db.get_empresas()
    if not empresas:
        st.info("No hay datos cargados. Carga primero los empleados desde la pestaña ANÁLISIS.")
        return

    # --- Selección de empresa y período ---
    col_emp, col_per = st.columns([2, 1])

    with col_emp:
        indice = empresas.index(EMPRESA_POR_DEFECTO) if EMPRESA_POR_DEFECTO in empresas else 0
        empresa = st.selectbox("Empresa", empresas, index=indice, key="dot_empresa")

    with col_per:
        periodos = gestor.periodos_disponibles(empresa)
        actual = str(datetime.now().year)
        if actual not in periodos:
            periodos = [actual] + periodos
        periodo = st.selectbox("Período", periodos, key="dot_periodo")

    resumen = gestor.resumen(empresa, periodo)

    if resumen["planificado"] == 0:
        st.info(
            f"**{empresa}** tiene {resumen['real']} personas y todavía no hay plan "
            f"cargado para {periodo}. Usa la pestaña **Editar plan** para definirlo."
        )

    _metricas(resumen)
    st.divider()

    tab_control, tab_costo, tab_plan = st.tabs(
        ["📊 Control por área", "💵 Vacantes y costo", "✏️ Editar plan"]
    )

    with tab_control:
        _control_por_area(gestor, empresa, periodo, resumen)

    with tab_costo:
        _vacantes_y_costo(gestor, empresa, periodo, resumen)

    with tab_plan:
        _editar_plan(gestor, empresa, periodo)


# ----------------------------------------------------------------------
# Secciones
# ----------------------------------------------------------------------

def _metricas(r):
    # Fila 1: dotación
    c1, c2, c3 = st.columns(3)
    c1.metric("Dotación real", r["real"], help="Personas según la última carga desde Buk")
    c2.metric("Posiciones en el plan", r["planificado"],
              help="Posiciones definidas en el plan del período")
    c3.metric("Vacantes por cubrir", r["vacantes"],
              help="Posiciones planificadas que hoy no tienen a nadie en ese cargo")

    # Fila 2: el costo actual, lo que sumaría el plan, y el total
    st.markdown("")
    d1, d2, d3 = st.columns(3)
    d1.metric("Nómina actual", format_peso_chileno(r["costo_actual"]),
              help=f"Costo empresa mensual de las {r['personas_costeadas']} personas "
                   "que ya están trabajando")

    delta = f"+{r['variacion_pct']:.1f}%" if r["costo_vacantes"] else None
    d2.metric("Suma el plan", format_peso_chileno(r["costo_vacantes"]), delta=delta,
              delta_color="off",
              help="Costo empresa de cubrir las vacantes del plan")

    d3.metric("Total proyectado", format_peso_chileno(r["costo_total"]),
              help=f"Nómina actual + vacantes. Anualizado: "
                   f"{format_peso_chileno(r['costo_total_anual'])}")

    avisos = []
    if r["sin_sueldo"]:
        avisos.append(f"{r['sin_sueldo']} persona(s) sin sueldo cargado quedan fuera del costo")
    if r["vacantes_sin_estimar"]:
        avisos.append(f"{r['vacantes_sin_estimar']} vacante(s) sin costo estimado")
    if avisos:
        st.caption("⚠️ " + " · ".join(avisos))


def _control_por_area(gestor, empresa, periodo, resumen):
    filas = gestor.control_por_area(empresa, periodo)
    if not filas:
        st.info("Sin áreas para mostrar.")
        return

    # Costo de las vacantes agrupado por área, para sumarlo al costo actual.
    vac_area = {}
    for v in gestor.vacantes_detalladas(empresa, periodo):
        vac_area[v["area"]] = vac_area.get(v["area"], 0.0) + v["costo_total"]

    costo_actual = resumen["costo_por_area"]

    df = pd.DataFrame([{
        "Área": f["area"],
        "Plan": f["planificado"],
        "Real": f["real"],
        "Vacantes": f["vacantes"],
        "Exceso": f["exceso"],
        "Estado": f["estado"],
        "Nómina actual": costo_actual.get(f["area"], 0.0),
        "Suma el plan": vac_area.get(f["area"], 0.0),
        "Total área": costo_actual.get(f["area"], 0.0) + vac_area.get(f["area"], 0.0),
    } for f in filas])

    pesos = st.column_config.NumberColumn(format="$%,d", width="medium")
    st.dataframe(
        df, width="stretch", hide_index=True,
        column_config={
            "Plan": st.column_config.NumberColumn(width="small"),
            "Real": st.column_config.NumberColumn(width="small"),
            "Vacantes": st.column_config.NumberColumn(width="small"),
            "Exceso": st.column_config.NumberColumn(width="small"),
            "Nómina actual": pesos,
            "Suma el plan": pesos,
            "Total área": pesos,
        },
    )

    # Resumen de estados, para leer la situación de un vistazo.
    conteo = df["Estado"].value_counts().to_dict()
    partes = [f"**{n}** {estado.lower()}" for estado, n in conteo.items()]
    st.caption("Áreas: " + " · ".join(partes))

    # El estado compara el total del área, no cargo por cargo: si se
    # planificaron solo algunos cargos, el área aparecerá sobredotada.
    if SOBRE in conteo:
        st.caption(
            "ℹ️ Un área figura en **sobredotación** cuando tiene más gente que "
            "posiciones planificadas. Si todavía no cargaste todos sus cargos, "
            "es esperable: el estado compara el total del área."
        )

    with st.expander("Ver el detalle por cargo"):
        real_cargo = gestor.dotacion_real_por_cargo(empresa)
        detalle = []
        for f in filas:
            for p in f["posiciones"]:
                ocupadas = real_cargo.get((p["area"], p["cargo"]), 0)
                detalle.append({
                    "Área": p["area"],
                    "Cargo": p["cargo"],
                    "Nivel HAY": p["nivel_hay"] or "—",
                    "Plan": p["cantidad"],
                    "Ocupadas": ocupadas,
                    "Faltan": max(0, p["cantidad"] - ocupadas),
                })
        if detalle:
            st.dataframe(pd.DataFrame(detalle), width="stretch", hide_index=True)
        else:
            st.caption("Todavía no hay posiciones en el plan.")


def _vacantes_y_costo(gestor, empresa, periodo, resumen):
    vacantes = gestor.vacantes_detalladas(empresa, periodo)

    if not vacantes:
        st.success("No hay vacantes: todas las posiciones del plan están cubiertas.")
        return

    if resumen["vacantes_sin_estimar"]:
        st.warning(
            f"{resumen['vacantes_sin_estimar']} vacante(s) sin costo estimado: "
            "les falta el nivel HAY o un sueldo de referencia. Se pueden completar "
            "en **Editar plan**."
        )

    df = pd.DataFrame([{
        "Área": v["area"],
        "Cargo": v["cargo"],
        "Nivel": v["nivel_hay"] or "—",
        "Vacantes": v["vacantes"],
        "Sueldo base": format_peso_chileno(v["sueldo_base"]) if v["origen"] != "sin estimar" else "—",
        "Costo unitario": format_peso_chileno(v["costo_unitario"]) if v["origen"] != "sin estimar" else "—",
        "Costo total/mes": format_peso_chileno(v["costo_total"]) if v["origen"] != "sin estimar" else "—",
        "Base del cálculo": {"manual": "Sueldo definido",
                             "banda": "Banda de mercado",
                             "sin estimar": "Sin estimar"}[v["origen"]],
    } for v in vacantes])

    st.dataframe(df, width="stretch", hide_index=True)

    st.markdown("##### Impacto en la nómina")
    c1, c2, c3 = st.columns(3)
    c1.metric("Nómina actual", format_peso_chileno(resumen["costo_actual"]))
    c2.metric("Cubrir las vacantes", format_peso_chileno(resumen["costo_vacantes"]),
              delta=f"+{resumen['variacion_pct']:.1f}%", delta_color="off")
    c3.metric("Total proyectado", format_peso_chileno(resumen["costo_total"]))

    st.caption(
        f"Anualizado, el total proyectado son "
        f"**{format_peso_chileno(resumen['costo_total_anual'])}**. "
        "El costo empresa incluye sueldo base, gratificación legal y los aportes "
        "del empleador (SIS, AFC y mutual). No incluye colación ni movilización: "
        "los datos de Buk no las traen, así que quedan fuera de ambos lados por igual."
    )


def _editar_plan(gestor, empresa, periodo):
    st.subheader("Agregar o actualizar una posición")
    st.caption(
        "Si guardas un cargo que ya está en el plan para esta área y período, "
        "se actualiza la línea existente en vez de duplicarla."
    )

    areas = gestor.areas_de(empresa)
    if not areas:
        st.info("Esta empresa no tiene áreas cargadas.")
        return

    area = st.selectbox("Área", areas, key="dot_area_form")

    cargos = gestor.cargos_de(empresa, area)
    opciones = cargos + ["➕ Otro cargo (escribir)"]
    elegido = st.selectbox("Cargo", opciones, key="dot_cargo_form")

    cargo = elegido
    if elegido == "➕ Otro cargo (escribir)":
        cargo = st.text_input("Nombre del cargo nuevo", key="dot_cargo_nuevo").strip()

    # Se propone el nivel HAY que ya tienen quienes ocupan ese cargo.
    sugerido = gestor.niveles_hay_de(empresa, area, elegido) if elegido in cargos else None

    with st.form("form_posicion_dotacion"):
        c1, c2, c3 = st.columns(3)
        with c1:
            cantidad = st.number_input("Cantidad requerida", min_value=1, max_value=200,
                                       value=1, step=1)
        with c2:
            nivel = st.text_input(
                "Nivel HAY", value=sugerido or "",
                help="Se usa para estimar el sueldo desde la banda de mercado" +
                     (f". Sugerido: {sugerido}" if sugerido else ""),
            ).strip()
        with c3:
            mercado = st.selectbox("Mercado", MERCADOS)

        c4, c5 = st.columns(2)
        with c4:
            sueldo_ref = st.number_input(
                "Sueldo base de referencia ($)", min_value=0, step=50_000, value=0,
                help="Opcional. Si lo defines, manda sobre la banda de mercado.",
            )
        with c5:
            target = st.number_input(
                "Target (rentas de bono)", min_value=0.0, max_value=12.0,
                value=0.0, step=0.5,
                help="Bono anual expresado en rentas. Afecta el sueldo base "
                     "estimado desde la banda.",
            )

        notas = st.text_input("Notas", placeholder="ej: reemplazo, proyecto nuevo…")

        guardar = st.form_submit_button("💾 Guardar en el plan", width="stretch",
                                        type="primary")

    if guardar:
        if not cargo:
            st.error("Indica el nombre del cargo")
        else:
            ok, msg = gestor.guardar_posicion(
                empresa=empresa, area=area, cargo=cargo, cantidad=int(cantidad),
                periodo=periodo, nivel_hay=nivel or None,
                sueldo_referencia=float(sueldo_ref) or None,
                target_rentas=float(target), mercado=mercado,
                notas=notas or None,
            )
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    # --- Plan vigente y borrado ---
    st.divider()
    st.subheader(f"Plan cargado para {periodo}")

    plan = gestor.obtener_plan(empresa, periodo)
    if not plan:
        st.caption("Todavía no hay posiciones en el plan de esta empresa.")
        return

    st.dataframe(
        pd.DataFrame([{
            "Área": p["area"],
            "Cargo": p["cargo"],
            "Nivel": p["nivel_hay"] or "—",
            "Cantidad": p["cantidad"],
            "Sueldo ref.": format_peso_chileno(p["sueldo_referencia"]) if p["sueldo_referencia"] else "—",
            "Target": p["target_rentas"] or 0,
            "Notas": p["notas"] or "",
        } for p in plan]),
        width="stretch", hide_index=True,
    )

    etiquetas = {f"{p['area']} · {p['cargo']} ({p['cantidad']})": p["id"] for p in plan}
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        a_borrar = st.selectbox("Quitar del plan", list(etiquetas), key="dot_borrar")
    with col_btn:
        st.write("")
        if st.button("🗑️ Quitar", width="stretch"):
            ok, msg = gestor.eliminar_posicion(etiquetas[a_borrar])
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
