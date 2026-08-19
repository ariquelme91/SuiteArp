"""Página de gestión de usuarios para administradores."""

import streamlit as st
import pandas as pd
from src.auth_manager import AuthManager


def render_user_management(auth_manager: AuthManager):
    """
    Renderiza la página de gestión de usuarios.

    Args:
        auth_manager: Gestor de autenticación
    """
    st.title("👥 Gestión de Usuarios")

    # Verificar que sea admin
    if st.session_state.get("rol") != "admin":
        st.error("❌ Solo administradores pueden acceder a esta sección")
        return

    if auth_manager.modo_secrets:
        _render_modo_secrets(auth_manager)
    else:
        _render_modo_local(auth_manager)


# ----------------------------------------------------------------------
# Modo Secrets (producción en Streamlit Cloud)
# ----------------------------------------------------------------------

def _render_modo_secrets(auth_manager: AuthManager):
    """UI cuando los usuarios viven en los Secrets de Streamlit."""
    tab1, tab2 = st.tabs(["📋 Usuarios Actuales", "➕ Agregar / Cambiar Clave"])

    with tab1:
        st.subheader("Usuarios Registrados")
        _tabla_usuarios(auth_manager, mostrar_fecha=False)

        st.caption(
            "Los usuarios se guardan en los Secrets de Streamlit Cloud, "
            "así sobreviven a cada redeploy."
        )

    with tab2:
        st.subheader("Generar línea para los Secrets")
        st.markdown(
            "Completa los datos y copia la línea resultante en "
            "**Manage app → Settings → Secrets**, dentro de `[usuarios]`.\n\n"
            "Sirve tanto para **agregar** a alguien nuevo como para "
            "**cambiarle la clave** a alguien existente: en ese caso reemplaza "
            "su línea actual."
        )

        with st.form("form_generar_secret"):
            usuario = st.text_input(
                "👤 Nombre de usuario",
                placeholder="ej: Juan",
                help="Mínimo 3 caracteres",
            )
            password = st.text_input(
                "🔐 Contraseña",
                type="password",
                placeholder="ej: miclave123",
                help="Mínimo 3 caracteres",
            )
            rol = st.selectbox(
                "Rol del usuario",
                ["user", "admin"],
                index=0,
                help="User: acceso limitado | Admin: acceso completo",
            )

            generar = st.form_submit_button(
                "🔑 Generar línea", width='stretch', type="primary"
            )

        if generar:
            exito, resultado = auth_manager.generar_linea_secrets(usuario, password, rol)
            if not exito:
                st.error(f"❌ {resultado}")
            else:
                st.success("✅ Línea generada. Cópiala y pégala en los Secrets:")
                st.code(resultado, language="toml")
                st.info(
                    "La contraseña queda hasheada: la línea no la revela. "
                    "Tras guardar los Secrets, Streamlit reinicia la app sola."
                )


# ----------------------------------------------------------------------
# Modo local (SQLite, desarrollo)
# ----------------------------------------------------------------------

def _render_modo_local(auth_manager: AuthManager):
    """UI cuando los usuarios viven en la BD local."""
    st.caption("⚙️ Modo local: los usuarios se guardan en la base de datos del equipo.")

    tab1, tab2, tab3 = st.tabs(
        ["📋 Usuarios Actuales", "➕ Crear Usuario", "🔑 Cambiar Contraseña"]
    )

    # TAB 1: Listar usuarios y acciones
    with tab1:
        st.subheader("Usuarios Registrados")
        usuarios = _tabla_usuarios(auth_manager, mostrar_fecha=True)

        if not usuarios:
            return

        st.subheader("⚙️ Acciones")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Cambiar Rol**")
            candidatos_rol = [u["usuario"] for u in usuarios if u["usuario"] != "Ariquelme"]

            if not candidatos_rol:
                st.caption("No hay usuarios a los que cambiar el rol.")
            else:
                usuario_cambio = st.selectbox(
                    "Selecciona usuario:", candidatos_rol, key="usuario_rol_cambio"
                )
                nuevo_rol = st.radio("Nuevo rol:", ["admin", "user"], key="nuevo_rol_select")

                if st.button("Actualizar Rol", key="btn_cambiar_rol"):
                    exito, mensaje = auth_manager.cambiar_rol(usuario_cambio, nuevo_rol)
                    if exito:
                        st.success(f"✅ {mensaje}")
                        st.rerun()
                    else:
                        st.error(f"❌ {mensaje}")

        with col2:
            st.markdown("**Desactivar Usuario**")
            candidatos_baja = [
                u["usuario"] for u in usuarios if u["activo"] and u["usuario"] != "Ariquelme"
            ]

            if not candidatos_baja:
                st.caption("No hay usuarios activos que se puedan desactivar.")
            else:
                usuario_desactivar = st.selectbox(
                    "Selecciona usuario a desactivar:",
                    candidatos_baja,
                    key="usuario_desactivar",
                )

                if st.button("Desactivar", key="btn_desactivar", type="secondary"):
                    exito, mensaje = auth_manager.eliminar_usuario(usuario_desactivar)
                    if exito:
                        st.success(f"✅ {mensaje}")
                        st.rerun()
                    else:
                        st.error(f"❌ {mensaje}")

    # TAB 2: Crear nuevo usuario
    with tab2:
        st.subheader("Crear Nuevo Usuario")

        with st.form("form_crear_usuario"):
            nuevo_usuario = st.text_input(
                "👤 Nombre de usuario", placeholder="ej: Juan", help="Mínimo 3 caracteres"
            )
            nueva_password = st.text_input(
                "🔐 Contraseña",
                type="password",
                placeholder="ej: miclave123",
                help="Mínimo 3 caracteres",
            )
            rol_nuevo = st.selectbox(
                "Rol del usuario",
                ["user", "admin"],
                index=0,
                help="User: acceso limitado | Admin: acceso completo",
            )

            submit_crear = st.form_submit_button(
                "✅ Crear Usuario", width='stretch', type="primary"
            )

        if submit_crear:
            exito, mensaje = auth_manager.crear_usuario(
                nuevo_usuario, nueva_password, rol_nuevo
            )
            if exito:
                st.success(f"✅ {mensaje}")
                st.balloons()
            else:
                st.error(f"❌ {mensaje}")

    # TAB 3: Cambiar contraseña propia
    with tab3:
        st.subheader("Cambiar Mi Contraseña")
        usuario_actual = st.session_state.get("usuario")

        with st.form("form_cambiar_password"):
            st.info(f"👤 Cambiar contraseña para: **{usuario_actual}**")

            password_actual = st.text_input(
                "🔐 Contraseña Actual", type="password", placeholder="Ingresa tu contraseña actual"
            )
            password_nueva = st.text_input(
                "🔑 Nueva Contraseña", type="password", placeholder="Ingresa la nueva contraseña"
            )
            password_confirmar = st.text_input(
                "🔑 Confirmar Nueva Contraseña",
                type="password",
                placeholder="Confirma la nueva contraseña",
            )

            submit_cambiar = st.form_submit_button(
                "✅ Cambiar Contraseña", width='stretch', type="primary"
            )

        if submit_cambiar:
            if not password_actual or not password_nueva:
                st.error("❌ Completa todos los campos")
            elif password_nueva != password_confirmar:
                st.error("❌ Las contraseñas nuevas no coinciden")
            else:
                exito, mensaje = auth_manager.cambiar_password(
                    usuario_actual, password_actual, password_nueva
                )
                if exito:
                    st.success(f"✅ {mensaje}")
                else:
                    st.error(f"❌ {mensaje}")


# ----------------------------------------------------------------------
# Común
# ----------------------------------------------------------------------

def _tabla_usuarios(auth_manager: AuthManager, mostrar_fecha: bool) -> list:
    """Dibuja la tabla de usuarios y devuelve la lista cruda."""
    usuarios = auth_manager.listar_usuarios()

    if not usuarios:
        st.info("No hay usuarios registrados")
        return []

    filas = []
    for u in usuarios:
        fila = {
            "Usuario": u["usuario"],
            "Rol": u["rol"].upper(),
            "Activo": "✅ Sí" if u["activo"] else "❌ No",
        }
        if mostrar_fecha:
            fecha = u.get("fecha_creacion")
            fila["Fecha Creación"] = fecha[:10] if fecha else "—"
        filas.append(fila)

    st.dataframe(pd.DataFrame(filas), width='stretch', hide_index=True)
    return usuarios
