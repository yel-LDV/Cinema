import json
import os

import pytest

from backend.auth import (CONFIG_RUTA, hash_sha256, leer_config,
                          validar_login)


def test_hash_determinista():
    assert hash_sha256("admin123") == hash_sha256("admin123")
    assert hash_sha256("admin123") != hash_sha256("otra")

    # además es realmente un hash SHA-256 de 64 hex
    import hashlib
    assert hash_sha256("x") == hashlib.sha256(b"x").hexdigest()


def test_config_inicial_se_crea_y_contiene_solo_hash(tmp_path):
    ruta = str(tmp_path / "config.json")
    admins = leer_config(ruta)
    assert len(admins) == 1
    cuenta = admins[0]
    assert cuenta["usuario"] == "admin"
    assert cuenta["hash"] == hash_sha256("admin123")
    contenido = open(ruta, encoding="utf-8").read()
    assert "admin123" not in contenido  # nunca en texto plano
    assert "hash" in json.loads(contenido)["admins"][0]


def test_validar_login_acepta_y_rechaza(tmp_path, monkeypatch):
    ruta = str(tmp_path / "config.json")
    admins = leer_config(ruta)
    assert validar_login("admin", "admin123", admins)
    assert not validar_login("admin", "clave-mala", admins)
    assert not validar_login("otro", "admin123", admins)
    # por defecto lee del archivo de config real
    monkeypatch.setattr("backend.auth.CONFIG_RUTA", ruta)
    monkeypatch.setattr("backend.auth.leer_config",
                        lambda _ruta=ruta: leer_config(ruta))
    assert validar_login("admin", "admin123")


def test_admins_son_editables_solo_en_json(tmp_path, monkeypatch):
    ruta = str(tmp_path / "config.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"admins": [
            {"usuario": "jefe", "hash": hash_sha256("secreta")},
        ]}, f)
    assert validar_login("jefe", "secreta", leer_config(ruta))
    assert not validar_login("admin", "admin123", leer_config(ruta))