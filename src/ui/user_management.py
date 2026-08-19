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

    # Pestañas
    tab1, tab2, tab3 = st.tabs(["📋 Usuarios Actuales", "➕ Crear Usuario", "🔑 Cambiar Contraseña"])

    # TAB 1: Listar usuarios
    with tab1:
        st.subheader("Usuarios Registrados")

        usuarios = auth_manager.listar_usuarios()

        if usuarios:
            # Convertir a DataFrame para mejor visualización
            df_usuarios = pd.DataFrame([
                {
                    "Usuario": u["usuario"],
                    "Rol": u["rol"].upper(),
                    "Activo": "✅ Sí" if u["activo"] else "❌ No",
                    "Fecha Creación": u["fecha_creacion"][:10]
                }
                for u in usuarios
            ])

            st.dataframe(df_usuarios, use_container_width=True, hide_index=True)

            # Acciones
            st.subheader("⚙️ Acciones")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Cambiar Rol**")
                usuario_cambio = st.selectbox(
                    "Selecciona usuario:",
                    [u["usuario"] for u in usuarios if u["usuario"] != "Ariquelme"],
                    key="usuario_rol_cambio"
                )

                nuevo_rol = st.radio(
                    "Nuevo rol:",
                    ["admin", "user"],
                    key="nuevo_rol_select"
                )

                if st.button("Actualizar Rol", key="btn_cambiar_rol"):
                    exito, mensaje = auth_manager.cambiar_rol(usuario_cambio, nuevo_rol)
                    if exito:
                        st.success(f"✅ {mensaje}")
                        st.rerun()
                    else:
                        st.error(f"❌ {mensaje}")

            with col2:
                st.markdown("**Desactivar Usuario**")
                usuario_desactivar = st.selectbox(
                    "Selecciona usuario a desactivar:",
                    [u["usuario"] for u in usuarios if u["activo"] and u["usuario"] != "Ariquelme"],
                    key="usuario_desactivar"
                )

                if st.button("Desactivar", key="btn_desactivar", type="secondary"):
                    exito, mensaje = auth_manager.eliminar_usuario(usuario_desactivar)
                    if exito:
                        st.success(f"✅ {mensaje}")
                        st.rerun()
                    else:
                        st.error(f"❌ {mensaje}")
        else:
            st.info("No hay usuarios registrados")

    # TAB 2: Crear nuevo usuario
    with tab2:
        st.subheader("Crear Nuevo Usuario")

        with st.form("form_crear_usuario"):
            nuevo_usuario = st.text_input(
                "👤 Nombre de usuario",
                placeholder="ej: Juan",
                help="Mínimo 3 caracteres"
            )

            nueva_password = st.text_input(
                "🔐 Contraseña",
                type="password",
                placeholder="ej: miclave123",
                help="Mínimo 3 caracteres"
            )

            rol_nuevo = st.selectbox(
                "Rol del usuario",
                ["user", "admin"],
                index=0,
                help="User: acceso limitado | Admin: acceso completo"
            )

            col1, col2 = st.columns(2)
            with col1:
                submit_crear = st.form_submit_button(
                    "✅ Crear Usuario",
                    use_container_width=True,
                    type="primary"
                )

            if submit_crear:
                # Validaciones
                if not nuevo_usuario or len(nuevo_usuario) < 3:
                    st.error("❌ El usuario debe tener al menos 3 caracteres")
                elif not nueva_password or len(nueva_password) < 3:
                    st.error("❌ La contraseña debe tener al menos 3 caracteres")
                else:
                    exito, mensaje = auth_manager.crear_usuario(
                        nuevo_usuario,
                        nueva_password,
                        rol_nuevo
                    )

                    if exito:
                        st.success(f"✅ {mensaje}")
                        st.balloons()
                        # Limpiar formulario
                        st.rerun()
                    else:
                        st.error(f"❌ {mensaje}")

    # TAB 3: Cambiar contraseña
    with tab3:
        st.subheader("Cambiar Mi Contraseña")

        with st.form("form_cambiar_password"):
            usuario_actual = st.session_state.get("usuario")

            st.info(f"👤 Cambiar contraseña para: **{usuario_actual}**")

            password_actual = st.text_input(
                "🔐 Contraseña Actual",
                type="password",
                placeholder="Ingresa tu contraseña actual"
            )

            password_nueva = st.text_input(
                "🔑 Nueva Contraseña",
                type="password",
                placeholder="Ingresa la nueva contraseña"
            )

            password_confirmar = st.text_input(
                "🔑 Confirmar Nueva Contraseña",
                type="password",
                placeholder="Confirma la nueva contraseña"
            )

            submit_cambiar = st.form_submit_button(
                "✅ Cambiar Contraseña",
                use_container_width=True,
                type="primary"
            )

            if submit_cambiar:
                if not password_actual or not password_nueva:
                    st.error("❌ Completa todos los campos")
                elif password_nueva != password_confirmar:
                    st.error("❌ Las contraseñas nuevas no coinciden")
                else:
                    exito, mensaje = auth_manager.cambiar_password(
                        usuario_actual,
                        password_actual,
                        password_nueva
                    )

                    if exito:
                        st.success(f"✅ {mensaje}")
                    else:
                        st.error(f"❌ {mensaje}")
