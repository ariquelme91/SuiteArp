"""Gestor de autenticación y control de acceso.

Fuente de usuarios:

1. `st.secrets["usuarios"]` cuando existe (producción en Streamlit Cloud).
   Los Secrets sobreviven a los redeploys, a diferencia del disco.
2. SQLite local (`analysis/data/auth.db`) como respaldo para desarrollo.

En modo Secrets el alta/baja de usuarios se hace pegando una línea en el
panel de Streamlit, porque los Secrets son de solo lectura en ejecución.
"""

import hashlib
import hmac
import os
import secrets as _secrets
import sqlite3
from typing import Dict, Optional, Tuple
import logging

import streamlit as st

logger = logging.getLogger(__name__)

# Nº de iteraciones de PBKDF2. Alto a propósito: encarece el crackeo por
# fuerza bruta si alguien llegara a ver los hashes en el panel de Secrets.
_PBKDF2_ITERACIONES = 260_000


class AuthManager:
    """Gestor de autenticación de usuarios."""

    def __init__(self):
        """Inicializa el gestor: Secrets si están disponibles, si no SQLite."""
        self.db_path = os.path.join(os.path.dirname(__file__), "analysis", "data", "auth.db")
        self._usuarios_secrets = self._leer_usuarios_secrets()

        if not self.modo_secrets:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._ensure_tables()
            self._init_default_users()

    # ------------------------------------------------------------------
    # Origen de datos
    # ------------------------------------------------------------------

    @property
    def modo_secrets(self) -> bool:
        """True si los usuarios vienen de st.secrets (producción)."""
        return self._usuarios_secrets is not None

    @staticmethod
    def _leer_usuarios_secrets() -> Optional[Dict[str, Dict]]:
        """Lee la sección [usuarios] de los Secrets. None si no existe."""
        try:
            if "usuarios" not in st.secrets:
                return None
            crudos = st.secrets["usuarios"]
        except Exception:
            # Sin archivo de secrets, o fuera del runtime de Streamlit.
            return None

        usuarios = {}
        for nombre, datos in dict(crudos).items():
            try:
                usuarios[nombre] = {
                    "password_hash": datos["password_hash"],
                    "rol": datos.get("rol", "user"),
                }
            except (TypeError, KeyError):
                logger.error("Entrada de usuario inválida en secrets: %s", nombre)

        return usuarios or None

    def _get_connection(self):
        """Obtiene conexión a la BD local."""
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self):
        """Crea tabla de usuarios si no existe."""
        try:
            conn = self._get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    rol TEXT NOT NULL DEFAULT 'user',
                    activo INTEGER DEFAULT 1,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Tabla de usuarios: {e}")

    def _init_default_users(self):
        """Crea usuarios por defecto si no existen (solo modo local)."""
        default_users = [
            ("Ariquelme", "Marti.2026", "admin"),
            ("Pcuadra", "jsqv00", "user"),
        ]

        for usuario, password, rol in default_users:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,))
                if cursor.fetchone() is None:
                    cursor.execute(
                        "INSERT INTO usuarios (usuario, password_hash, rol) VALUES (?, ?, ?)",
                        (usuario, self._hash_password(password), rol),
                    )
                    conn.commit()
                    logger.info(f"Usuario creado: {usuario} ({rol})")
                conn.close()
            except Exception as e:
                logger.error(f"Error creando usuario {usuario}: {e}")

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
        """Hashea una contraseña con PBKDF2-HMAC-SHA256 y sal aleatoria."""
        if salt is None:
            salt = _secrets.token_bytes(16)
        derivada = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, _PBKDF2_ITERACIONES
        )
        return f"pbkdf2${_PBKDF2_ITERACIONES}${salt.hex()}${derivada.hex()}"

    @staticmethod
    def _verify_password(password: str, almacenado: str) -> bool:
        """Verifica una contraseña contra el hash guardado.

        Acepta el formato PBKDF2 actual y los SHA256 simples que quedaron
        en bases locales antiguas, para no romper instalaciones previas.
        """
        if not almacenado:
            return False

        if almacenado.startswith("pbkdf2$"):
            try:
                _, iteraciones, salt_hex, esperado = almacenado.split("$", 3)
                derivada = hashlib.pbkdf2_hmac(
                    "sha256", password.encode(), bytes.fromhex(salt_hex), int(iteraciones)
                )
                return hmac.compare_digest(derivada.hex(), esperado)
            except (ValueError, TypeError):
                logger.error("Hash PBKDF2 con formato inválido")
                return False

        # Formato heredado: SHA256 sin sal.
        return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), almacenado)

    # ------------------------------------------------------------------
    # Autenticación
    # ------------------------------------------------------------------

    def authenticate(self, usuario: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """Autentica un usuario contra Secrets o SQLite."""
        if not usuario or not password:
            return False, None

        try:
            if self.modo_secrets:
                datos = self._usuarios_secrets.get(usuario)
                if datos and self._verify_password(password, datos["password_hash"]):
                    return True, {"id": usuario, "usuario": usuario, "rol": datos["rol"]}
                logger.warning(f"Fallo de autenticación: {usuario}")
                return False, None

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, usuario, rol, activo, password_hash FROM usuarios WHERE usuario = ?",
                (usuario,),
            )
            resultado = cursor.fetchone()
            conn.close()

            if not resultado:
                logger.warning(f"Fallo de autenticación: {usuario}")
                return False, None

            user_id, user, rol, activo, password_hash = resultado

            if not self._verify_password(password, password_hash):
                logger.warning(f"Fallo de autenticación: {usuario}")
                return False, None

            if not activo:
                logger.warning(f"Usuario inactivo: {usuario}")
                return False, None

            return True, {"id": user_id, "usuario": user, "rol": rol}

        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return False, None

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------

    def listar_usuarios(self) -> list:
        """Lista todos los usuarios."""
        if self.modo_secrets:
            return [
                {
                    "id": nombre,
                    "usuario": nombre,
                    "rol": datos["rol"],
                    "activo": 1,
                    "fecha_creacion": None,
                }
                for nombre, datos in sorted(self._usuarios_secrets.items())
            ]

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, usuario, rol, activo, fecha_creacion
                FROM usuarios
                ORDER BY fecha_creacion DESC
            """)
            usuarios = cursor.fetchall()
            conn.close()

            return [
                {
                    "id": u[0],
                    "usuario": u[1],
                    "rol": u[2],
                    "activo": u[3],
                    "fecha_creacion": u[4],
                }
                for u in usuarios
            ]
        except Exception as e:
            logger.error(f"Error listando usuarios: {e}")
            return []

    # ------------------------------------------------------------------
    # Generación de configuración para Secrets
    # ------------------------------------------------------------------

    def generar_linea_secrets(self, usuario: str, password: str, rol: str = "user") -> Tuple[bool, str]:
        """Genera la línea TOML a pegar en el panel de Secrets.

        Returns:
            (True, línea) o (False, mensaje de error de validación).
        """
        valido, mensaje = self._validar_datos(usuario, password, rol)
        if not valido:
            return False, mensaje

        linea = f'{usuario} = {{ password_hash = "{self._hash_password(password)}", rol = "{rol}" }}'
        return True, linea

    @staticmethod
    def _validar_datos(usuario: str, password: str, rol: str) -> Tuple[bool, str]:
        """Valida usuario, contraseña y rol."""
        if not usuario or len(usuario) < 3:
            return False, "El usuario debe tener al menos 3 caracteres"
        if not password or len(password) < 3:
            return False, "La contraseña debe tener al menos 3 caracteres"
        if rol not in ("admin", "user"):
            return False, "Rol inválido (admin o user)"
        return True, ""

    # ------------------------------------------------------------------
    # Escritura (solo modo local con SQLite)
    # ------------------------------------------------------------------

    _MSG_SOLO_LECTURA = (
        "Los usuarios se administran desde los Secrets de Streamlit Cloud. "
        "Usa la pestaña 'Crear Usuario' para generar la línea a pegar."
    )

    def crear_usuario(self, usuario: str, password: str, rol: str = "user") -> Tuple[bool, str]:
        """Crea un nuevo usuario (solo modo local)."""
        if self.modo_secrets:
            return False, self._MSG_SOLO_LECTURA

        valido, mensaje = self._validar_datos(usuario, password, rol)
        if not valido:
            return False, mensaje

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,))
            if cursor.fetchone() is not None:
                conn.close()
                return False, f"El usuario '{usuario}' ya existe"

            cursor.execute(
                "INSERT INTO usuarios (usuario, password_hash, rol) VALUES (?, ?, ?)",
                (usuario, self._hash_password(password), rol),
            )
            conn.commit()
            conn.close()

            logger.info(f"Usuario creado: {usuario} ({rol})")
            return True, f"Usuario '{usuario}' creado exitosamente"

        except Exception as e:
            logger.error(f"Error creando usuario: {e}")
            return False, f"Error: {str(e)}"

    def cambiar_password(self, usuario: str, password_actual: str, password_nueva: str) -> Tuple[bool, str]:
        """Cambia la contraseña de un usuario (solo modo local)."""
        if self.modo_secrets:
            return False, self._MSG_SOLO_LECTURA

        try:
            autenticado, _ = self.authenticate(usuario, password_actual)
            if not autenticado:
                return False, "Contraseña actual inválida"

            if not password_nueva or len(password_nueva) < 3:
                return False, "La contraseña debe tener al menos 3 caracteres"

            conn = self._get_connection()
            conn.execute(
                "UPDATE usuarios SET password_hash = ? WHERE usuario = ?",
                (self._hash_password(password_nueva), usuario),
            )
            conn.commit()
            conn.close()

            logger.info(f"Contraseña actualizada: {usuario}")
            return True, "Contraseña actualizada exitosamente"

        except Exception as e:
            logger.error(f"Error cambiando contraseña: {e}")
            return False, f"Error: {str(e)}"

    def eliminar_usuario(self, usuario: str) -> Tuple[bool, str]:
        """Desactiva un usuario (solo modo local)."""
        if self.modo_secrets:
            return False, self._MSG_SOLO_LECTURA

        try:
            if usuario == "Ariquelme":
                return False, "No se puede desactivar el usuario administrador"

            conn = self._get_connection()
            conn.execute("UPDATE usuarios SET activo = 0 WHERE usuario = ?", (usuario,))
            conn.commit()
            conn.close()

            logger.info(f"Usuario desactivado: {usuario}")
            return True, f"Usuario '{usuario}' desactivado exitosamente"

        except Exception as e:
            logger.error(f"Error eliminando usuario: {e}")
            return False, f"Error: {str(e)}"

    def cambiar_rol(self, usuario: str, nuevo_rol: str) -> Tuple[bool, str]:
        """Cambia el rol de un usuario (solo modo local)."""
        if self.modo_secrets:
            return False, self._MSG_SOLO_LECTURA

        try:
            if nuevo_rol not in ("admin", "user"):
                return False, "Rol inválido (admin o user)"

            conn = self._get_connection()
            conn.execute("UPDATE usuarios SET rol = ? WHERE usuario = ?", (nuevo_rol, usuario))
            conn.commit()
            conn.close()

            logger.info(f"Rol actualizado para {usuario}: {nuevo_rol}")
            return True, f"Rol de '{usuario}' actualizado a '{nuevo_rol}'"

        except Exception as e:
            logger.error(f"Error cambiando rol: {e}")
            return False, f"Error: {str(e)}"
