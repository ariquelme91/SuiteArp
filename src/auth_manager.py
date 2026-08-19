"""Gestor de autenticación y control de acceso."""

import hashlib
from typing import Optional, Dict, Tuple
from src.analysis.db_manager import AnalysisDBManager
import logging

logger = logging.getLogger(__name__)


class AuthManager:
    """Gestor de autenticación de usuarios."""

    def __init__(self, db_manager: AnalysisDBManager = None):
        """
        Inicializa el gestor de autenticación.

        Args:
            db_manager: Gestor de BD para persistencia
        """
        self.db_manager = db_manager or AnalysisDBManager()
        self._ensure_tables()
        self._init_default_users()

    def _ensure_tables(self):
        """Crea tabla de usuarios si no existe."""
        try:
            self.db_manager.cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    rol TEXT NOT NULL DEFAULT 'user',
                    activo INTEGER DEFAULT 1,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.db_manager.conn.commit()
        except Exception as e:
            logger.warning(f"Tabla de usuarios ya existe: {e}")

    def _init_default_users(self):
        """Crea usuarios por defecto si no existen."""
        default_users = [
            ("Ariquelme", "admin", "admin"),
            ("Pcuadra", "user", "user"),
        ]

        for usuario, password, rol in default_users:
            try:
                # Verificar si ya existe
                self.db_manager.cursor.execute(
                    "SELECT id FROM usuarios WHERE usuario = ?",
                    (usuario,)
                )
                if self.db_manager.cursor.fetchone() is None:
                    # No existe, crear
                    password_hash = self._hash_password(password)
                    self.db_manager.cursor.execute("""
                        INSERT INTO usuarios (usuario, password_hash, rol)
                        VALUES (?, ?, ?)
                    """, (usuario, password_hash, rol))
                    self.db_manager.conn.commit()
                    logger.info(f"Usuario creado: {usuario} ({rol})")
            except Exception as e:
                logger.error(f"Error creando usuario {usuario}: {e}")

    def _hash_password(self, password: str) -> str:
        """
        Hashea una contraseña.

        Args:
            password: Contraseña en texto plano

        Returns:
            Hash SHA256 de la contraseña
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, usuario: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Autentica un usuario.

        Args:
            usuario: Nombre de usuario
            password: Contraseña en texto plano

        Returns:
            Tupla (éxito, datos_usuario)
        """
        try:
            password_hash = self._hash_password(password)
            self.db_manager.cursor.execute("""
                SELECT id, usuario, rol, activo
                FROM usuarios
                WHERE usuario = ? AND password_hash = ?
            """, (usuario, password_hash))

            resultado = self.db_manager.cursor.fetchone()
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
        """
        Crea un nuevo usuario.

        Args:
            usuario: Nombre de usuario
            password: Contraseña en texto plano
            rol: Rol (admin o user)

        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            # Validaciones
            if not usuario or len(usuario) < 3:
                return False, "El usuario debe tener al menos 3 caracteres"

            if not password or len(password) < 3:
                return False, "La contraseña debe tener al menos 3 caracteres"

            if rol not in ["admin", "user"]:
                return False, "Rol inválido (admin o user)"

            # Verificar si ya existe
            self.db_manager.cursor.execute(
                "SELECT id FROM usuarios WHERE usuario = ?",
                (usuario,)
            )
            if self.db_manager.cursor.fetchone() is not None:
                return False, f"El usuario '{usuario}' ya existe"

            # Crear usuario
            password_hash = self._hash_password(password)
            self.db_manager.cursor.execute("""
                INSERT INTO usuarios (usuario, password_hash, rol)
                VALUES (?, ?, ?)
            """, (usuario, password_hash, rol))
            self.db_manager.conn.commit()

            logger.info(f"Usuario creado: {usuario} ({rol})")
            return True, f"Usuario '{usuario}' creado exitosamente"

        except Exception as e:
            logger.error(f"Error creando usuario: {e}")
            return False, f"Error: {str(e)}"

    def cambiar_password(self, usuario: str, password_actual: str, password_nueva: str) -> Tuple[bool, str]:
        """
        Cambia la contraseña de un usuario.

        Args:
            usuario: Nombre de usuario
            password_actual: Contraseña actual
            password_nueva: Nueva contraseña

        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            # Verificar contraseña actual
            autenticado, _ = self.authenticate(usuario, password_actual)
            if not autenticado:
                return False, "Contraseña actual inválida"

            # Actualizar contraseña
            password_hash = self._hash_password(password_nueva)
            self.db_manager.cursor.execute("""
                UPDATE usuarios
                SET password_hash = ?
                WHERE usuario = ?
            """, (password_hash, usuario))
            self.db_manager.conn.commit()

            logger.info(f"Contraseña actualizada: {usuario}")
            return True, "Contraseña actualizada exitosamente"

        except Exception as e:
            logger.error(f"Error cambiando contraseña: {e}")
            return False, f"Error: {str(e)}"

    def listar_usuarios(self) -> list:
        """
        Lista todos los usuarios.

        Returns:
            Lista de usuarios con sus datos
        """
        try:
            self.db_manager.cursor.execute("""
                SELECT id, usuario, rol, activo, fecha_creacion
                FROM usuarios
                ORDER BY fecha_creacion DESC
            """)
            usuarios = self.db_manager.cursor.fetchall()
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
        """
        Desactiva un usuario.

        Args:
            usuario: Nombre de usuario

        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            # No permitir eliminar el admin por defecto
            if usuario == "Ariquelme":
                return False, "No se puede desactivar el usuario administrador"

            self.db_manager.cursor.execute("""
                UPDATE usuarios
                SET activo = 0
                WHERE usuario = ?
            """, (usuario,))
            self.db_manager.conn.commit()

            logger.info(f"Usuario desactivado: {usuario}")
            return True, f"Usuario '{usuario}' desactivado exitosamente"

        except Exception as e:
            logger.error(f"Error eliminando usuario: {e}")
            return False, f"Error: {str(e)}"

    def cambiar_rol(self, usuario: str, nuevo_rol: str) -> Tuple[bool, str]:
        """
        Cambia el rol de un usuario.

        Args:
            usuario: Nombre de usuario
            nuevo_rol: Nuevo rol (admin o user)

        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            if nuevo_rol not in ["admin", "user"]:
                return False, "Rol inválido (admin o user)"

            self.db_manager.cursor.execute("""
                UPDATE usuarios
                SET rol = ?
                WHERE usuario = ?
            """, (nuevo_rol, usuario))
            self.db_manager.conn.commit()

            logger.info(f"Rol actualizado para {usuario}: {nuevo_rol}")
            return True, f"Rol de '{usuario}' actualizado a '{nuevo_rol}'"

        except Exception as e:
            logger.error(f"Error cambiando rol: {e}")
            return False, f"Error: {str(e)}"
