#!/usr/bin/env python3
"""Script para inicializar usuarios en la BD."""

from src.auth_manager import AuthManager

# Inicializar
auth_manager = AuthManager()

# Listar usuarios
usuarios = auth_manager.listar_usuarios()
print(f"✅ Usuarios en la BD: {len(usuarios)}")
for u in usuarios:
    print(f"   - {u['usuario']} ({u['rol']}) - Activo: {u['activo']}")

# Verificar que existan los usuarios necesarios
usuarios_dict = {u['usuario']: u for u in usuarios}

if 'Ariquelme' in usuarios_dict:
    print("✅ Ariquelme existe")
else:
    print("❌ Ariquelme no existe - creando...")
    exito, msg = auth_manager.crear_usuario('Ariquelme', 'admin', 'admin')
    print(f"   Resultado: {msg}")

if 'Pcuadra' in usuarios_dict:
    print("✅ Pcuadra existe")
else:
    print("❌ Pcuadra no existe - creando...")
    exito, msg = auth_manager.crear_usuario('Pcuadra', 'user', 'user')
    print(f"   Resultado: {msg}")

print("\n✅ Usuarios inicializados correctamente")
