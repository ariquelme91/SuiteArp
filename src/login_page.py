"""Página de login para la aplicación."""

import streamlit as st
from src.auth_manager import AuthManager


def render_login_page(auth_manager: AuthManager):
    """
    Renderiza la página de login.

    Args:
        auth_manager: Gestor de autenticación
    """
    # Estilos personalizados
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 50px auto;
    }
    .login-title {
        text-align: center;
        color: #1F4E78;
        font-size: 32px;
        margin-bottom: 5px;
    }
    .login-subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 30px;
    }
    .demo-info {
        background: #F5F5F5;
        padding: 15px;
        border-radius: 8px;
        margin-top: 20px;
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Contenedor de login
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.markdown('<div class="login-title">💰 Suite ARP IA</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Sistema de Compensaciones</div>', unsafe_allow_html=True)

        # Problema de configuración, no de credenciales: sin esto el usuario
        # solo vería "contraseña inválida" y no sabría que el fallo está
        # en los Secrets.
        if auth_manager.usuarios_invalidos:
            afectados = ", ".join(auth_manager.usuarios_invalidos)
            st.error(
                f"⚠️ **Error de configuración** — el `password_hash` de "
                f"**{afectados}** está incompleto en los Secrets de Streamlit.\n\n"
                "Debe ser el valor completo (111 caracteres, termina en el hash), "
                "sin recortes ni `...`. Estos usuarios no podrán ingresar hasta "
                "corregirlo."
            )

        # Formulario de login
        with st.form("login_form"):
            usuario = st.text_input(
                "👤 Usuario",
                placeholder="Ingresa tu usuario",
                key="login_usuario"
            )

            password = st.text_input(
                "🔐 Contraseña",
                type="password",
                placeholder="Ingresa tu contraseña",
                key="login_password"
            )

            # Botón de login
            col1, col2 = st.columns([1, 1])
            with col1:
                login_button = st.form_submit_button(
                    "🔓 Iniciar Sesión",
                    use_container_width=True,
                    type="primary"
                )

            if login_button:
                if not usuario or not password:
                    st.error("❌ Por favor completa usuario y contraseña")
                else:
                    # Intentar autenticación
                    autenticado, user_data = auth_manager.authenticate(usuario, password)

                    if autenticado:
                        # Guardar sesión
                        st.session_state.authenticated = True
                        st.session_state.usuario = user_data["usuario"]
                        st.session_state.rol = user_data["rol"]
                        st.session_state.user_id = user_data["id"]

                        st.success(f"✅ Bienvenido {user_data['usuario']} ({user_data['rol'].upper()})")
                        st.balloons()

                        # Recargar la aplicación
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña inválidos")

