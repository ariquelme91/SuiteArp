"""Página de login para la aplicación."""

import os

import streamlit as st
from src.auth_manager import AuthManager
from src.branding import LOGO_PATH, logo_base64


def render_login_page(auth_manager: AuthManager):
    """
    Renderiza la página de login.

    Args:
        auth_manager: Gestor de autenticación
    """
    # Estilos personalizados
    st.markdown("""
    <style>
    .login-logo {
        text-align: center;
        margin-bottom: 10px;
    }
    .login-logo img {
        width: 240px;
        max-width: 100%;
    }
    .login-title {
        text-align: center;
        color: #3B78C3;
        font-size: 32px;
        margin-bottom: 5px;
    }
    .login-subtitle {
        text-align: center;
        color: #AAAAAA;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Contenedor de login
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        if os.path.exists(LOGO_PATH):
            st.markdown(
                f'<div class="login-logo">'
                f'<img src="data:image/png;base64,{logo_base64()}" />'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            # Reserva por si el archivo del logo no está disponible.
            st.markdown('<div class="login-title">💰 Suite ARP IA</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-subtitle">Sistema de Compensaciones</div>', unsafe_allow_html=True)

        # Problema de configuración, no de credenciales: sin esto el usuario
        # solo vería "contraseña inválida" y no sabría que el fallo está
        # en los Secrets.
        if auth_manager.usuarios_invalidos:
            afectados = ", ".join(auth_manager.usuarios_invalidos)
            st.error(
                f":material/warning: **Error de configuración** — el `password_hash` de "
                f"**{afectados}** está incompleto en los Secrets de Streamlit.\n\n"
                "Debe ser el valor completo (111 caracteres, termina en el hash), "
                "sin recortes ni `...`. Estos usuarios no podrán ingresar hasta "
                "corregirlo."
            )

        # Formulario de login
        with st.form("login_form"):
            usuario = st.text_input(
                ":material/person: Usuario",
                placeholder="Ingresa tu usuario",
                key="login_usuario"
            )

            password = st.text_input(
                ":material/lock: Contraseña",
                type="password",
                placeholder="Ingresa tu contraseña",
                key="login_password"
            )

            # Botón de login
            col1, col2 = st.columns([1, 1])
            with col1:
                login_button = st.form_submit_button(
                    ":material/lock_open: Iniciar Sesión",
                    width='stretch',
                    type="primary"
                )

            if login_button:
                if not usuario or not password:
                    st.error(":material/cancel: Por favor completa usuario y contraseña")
                else:
                    # Intentar autenticación
                    autenticado, user_data = auth_manager.authenticate(usuario, password)

                    if autenticado:
                        # Guardar sesión
                        st.session_state.authenticated = True
                        st.session_state.usuario = user_data["usuario"]
                        st.session_state.rol = user_data["rol"]
                        st.session_state.user_id = user_data["id"]

                        st.success(f":material/check_circle: Bienvenido {user_data['usuario']} ({user_data['rol'].upper()})")
                        st.balloons()

                        # Recargar la aplicación
                        st.rerun()
                    else:
                        st.error(":material/cancel: Usuario o contraseña inválidos")

