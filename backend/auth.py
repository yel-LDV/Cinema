"""Autenticación del panel de administración.

Las cuentas de administración viven únicamente en data/config.json; la app
no ofrece ninguna pantalla para darlas de alta o modificarlas. Cada cuenta se
guarda como usuario + hash SHA-256 de la contraseña (nunca en texto plano).
"""

import hashlib
import json
import os

from backend.database import RAIZ

CONFIG_RUTA = os.path.join(RAIZ, "data", "config.json")

ADMIN_INICIAL = {"usuario": "admin", "clave": "admin123"}


def hash_sha256(texto):
    """Hash SHA-256 (hex) de una contraseña."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def leer_config(ruta=None):
    """Lee el JSON de configuración; si no existe, lo crea con una cuenta
    admin inicial. Devuelve una lista de dicts {'usuario', 'hash'}.
    """
    ruta = ruta or CONFIG_RUTA
    if not os.path.isfile(ruta):
        _crear_config(ruta)
    with open(ruta, "r", encoding="utf-8") as f:
        datos = json.load(f)
    return datos.get("admins", [])


def _crear_config(ruta):
    cuenta = {"usuario": ADMIN_INICIAL["usuario"],
              "hash": hash_sha256(ADMIN_INICIAL["clave"])}
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"admins": [cuenta]}, f, indent=2, ensure_ascii=False)
        f.write("\n")


def validar_login(usuario, clave, admins=None):
    """Devuelve True si usuario/hash (SHA-256 de clave) coinciden."""
    admins = admins if admins is not None else leer_config()
    for cuenta in admins:
        if (cuenta.get("usuario", "") == usuario
                and cuenta.get("hash", "") == hash_sha256(clave)):
            return True
    return False