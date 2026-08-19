"""Gestor de autenticación y control de acceso."""

import hashlib
import sqlite3
import os
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class AuthManager:
    """Gestor de autenticación de usuarios."""

    def __init__(self):
        """Inicializa el gestor de autenticación con BD local."""
        self.db_path = os.path.join(os.path.dirname(__file__), "analysis", "data", "auth.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._ensure_tables()
        self._init_default_users()

    def _get_connection(self):
        """Obtiene conexión a la BD."""
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self):
        """Crea tabla de usuarios si no existe."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
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
        """Crea usuarios por defecto si no existen."""
        default_users = [
            ("Ariquelme", "admin", "admin"),
            ("Pcuadra", "user", "user"),
        ]

        for usuario, password, rol in default_users:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM usuarios WHERE usuario = ?",
                    (usuario,)
                )
                if cursor.fetchone() is None:
                    password_hash = self._hash_password(password)
                    cursor.execute("""
                        INSERT INTO usuarios (usuario, password_hash, rol)
                        VALUES (?, ?, ?)
                    """, (usuario, password_hash, rol))
                    conn.commit()
                    logger.info(f"Usuario creado: {usuario} ({rol})")
                conn.close()
            except Exception as e:
                logger.error(f"Error creando usuario {usuario}: {e}")

    def _hash_password(self, password: str) -> str:
        """Hashea una contraseña."""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, usuario: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """Autentica un usuario."""
        try:
            password_hash = self._hash_password(password)
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, usuario, rol, activo
                FROM usuarios
                WHERE usuario = ? AND password_hash = ?
            """, (usuario, password_hash))

            resultado = cursor.fetchone()
            conn.close()

            if resultado:
                user_id, user, rol, activo = resultado
                if activo:
                    return True, {
                        "id": user_id,
                        "usuario": user,
                        "rol": rol
                    }
                else:
                    logger.warning(f"Usuario inactivo: {usuario}")
                    return False, None
            else:
                logger.warning(f"Fallo de autenticación: {usuario}")
                return False, None

        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return False, None

    def crear_usuario(self, usuario: str, password: str, rol: str = "user") -> Tuple[bool, str]:
        """Crea un nuevo usuario."""
        try:
            if not usuario or len(usuario) < 3:
                return False, "El usuario debe tener al menos 3 caracteres"

            if not password or len(password) < 3:
                return False, "La contraseña debe tener al menos 3 caracteres"

            if rol not in ["admin", "user"]:
                return False, "Rol inválido (admin o user)"

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM usuarios WHERE usuario = ?",
                (usuario,)
            )
            if cursor.fetchone() is not None:
                conn.close()
                return False, f"El usuario '{usuario}' ya existe"

            password_hash = self._hash_password(password)
            cursor.execute("""
                INSERT INTO usuarios (usuario, password_hash, rol)
                VALUES (?, ?, ?)
            """, (usuario, password_hash, rol))
            conn.commit()
            conn.close()

            logger.info(f"Usuario creado: {usuario} ({rol})")
            return True, f"Usuario '{usuario}' creado exitosamente"

        except Exception as e:
            logger.error(f"Error creando usuario: {e}")
            return False, f"Error: {str(e)}"

    def cambiar_password(self, usuario: str, password_actual: str, password_nueva: str) -> Tuple[bool, str]:
        """Cambia la contraseña de un usuario."""
        try:
            autenticado, _ = self.authenticate(usuario, password_actual)
            if not autenticado:
                return False, "Contraseña actual inválida"

            password_hash = self._hash_password(password_nueva)
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE usuarios
                SET password_hash = ?
                WHERE usuario = ?
            """, (password_hash, usuario))
            conn.commit()
            conn.close()

            logger.info(f"Contraseña actualizada: {usuario}")
            return True, "Contraseña actualizada exitosamente"

        except Exception as e:
            logger.error(f"Error cambiando contraseña: {e}")
            return False, f"Error: {str(e)}"

    def listar_usuarios(self) -> list:
        """Lista todos los usuarios."""
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
                    "fecha_creacion": u[4]
                }
                for u in usuarios
            ]
        except Exception as e:
            logger.error(f"Error listando usuarios: {e}")
            return []

    def eliminar_usuario(self, usuario: str) -> Tuple[bool, str]:
        """Desactiva un usuario."""
        try:
            if usuario == "Ariquelme":
                return False, "No se puede desactivar el usuario administrador"

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE usuarios
                SET activo = 0
                WHERE usuario = ?
            """, (usuario,))
            conn.commit()
            conn.close()

            logger.info(f"Usuario desactivado: {usuario}")
            return True, f"Usuario '{usuario}' desactivado exitosamente"

        except Exception as e:
            logger.error(f"Error eliminando usuario: {e}")
            return False, f"Error: {str(e)}"

    def cambiar_rol(self, usuario: str, nuevo_rol: str) -> Tuple[bool, str]:
        """Cambia el rol de un usuario."""
        try:
            if nuevo_rol not in ["admin", "user"]:
                return False, "Rol inválido (admin o user)"

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE usuarios
                SET rol = ?
                WHERE usuario = ?
            """, (nuevo_rol, usuario))
            conn.commit()
            conn.close()

            logger.info(f"Rol actualizado para {usuario}: {nuevo_rol}")
            return True, f"Rol de '{usuario}' actualizado a '{nuevo_rol}'"

        except Exception as e:
            logger.error(f"Error cambiando rol: {e}")
            return False, f"Error: {str(e)}"
