#!/usr/bin/env python3
"""Verifica la conexión a MariaDB y muestra el estado del esquema."""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from backend.database import config_mariadb  # noqa: E402
from backend.models import CineService  # noqa: E402


def main():
    cfg = config_mariadb()
    print(f"Conectando a MariaDB {cfg['host']}:{cfg['port']}/"
          f"{cfg['database']} como {cfg['user']}…")
    servicio = CineService()
    conn = servicio.conn
    fila = conn.execute("SELECT VERSION() AS version").fetchone()
    print(f"OK · MariaDB {fila['version']}")
    tablas = [f["name"] for f in conn.execute(
        "SELECT table_name AS name FROM information_schema.tables "
        "WHERE table_schema = ? ORDER BY table_name",
        (cfg["database"],)).fetchall()]
    print(f"Tablas ({len(tablas)}): " + ", ".join(tablas))

    print(f"Películas activas: {len(servicio.listar_peliculas())}")
    print(f"Funciones: {len(servicio.listar_funciones())}")
    print(f"Ventas: {len(servicio.ventas_detalladas())}")
    servicio.conn.close()


if __name__ == "__main__":
    main()
