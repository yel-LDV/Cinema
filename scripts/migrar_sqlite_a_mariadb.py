#!/usr/bin/env python3
"""Migra la base SQLite histórica (data/cine.db) al esquema normalizado en
MariaDB.

Uso:
    .venv/bin/python scripts/migrar_sqlite_a_mariadb.py
    .venv/bin/python scripts/migrar_sqlite_a_mariadb.py --recrear
    CINEMA_DB_NAME=cinema_test .venv/bin/python scripts/... --sqlite vieja.db

La migración conserva folios, fechas, estados y asientos. Las salas se crean
con la capacidad máxima vista para cada nombre de sala y los asientos físicos
se comparten entre funciones (modelo normalizado). Es idempotente en el
sentido de que aborta si la base destino ya tiene películas, salvo --recrear.
"""

import argparse
import os
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from backend.database import conexion  # noqa: E402
from backend.models import CineService, SEATS_POR_FILA  # noqa: E402

TABLAS = ["boletos", "ventas", "funciones", "asientos", "salas",
          "peliculas", "descuentos", "estados_venta", "clientes",
          "clasificaciones", "generos"]


def _existe_tabla(conn, nombre):
    try:
        conn.execute(f"SELECT 1 FROM {nombre} LIMIT 1")
        return True
    except sqlite3.OperationalError:
        return False


def _asientos_para(capacidad):
    """Misma disposición que backend.models._generar_disposicion."""
    resultado = []
    letra_idx = 0
    resto = capacidad
    while resto > 0:
        n = min(SEATS_POR_FILA, resto)
        letra = chr(ord("A") + letra_idx)
        for i in range(1, n + 1):
            resultado.append((letra, i))
        resto -= n
        letra_idx += 1
    return resultado


def _preparar_destino(servicio, recrear):
    if recrear:
        for tabla in TABLAS:
            servicio.conn.execute(f"DROP TABLE IF EXISTS {tabla}")
        servicio.conn.commit()
        servicio.conn.close()
        servicio = CineService(servicio.ruta_db)
    fila = servicio.conn.execute(
        "SELECT COUNT(*) AS n FROM peliculas").fetchone()
    if int(fila["n"]) > 0:
        raise SystemExit(
            "La base destino ya tiene datos. Usa --recrear para reemplazarla.")
    return servicio


def migrar(ruta_sqlite, recrear=False, servicio=None):
    if not os.path.isfile(ruta_sqlite):
        raise SystemExit(f"No se encontró la base SQLite: {ruta_sqlite}")

    vieja = sqlite3.connect(ruta_sqlite)
    vieja.row_factory = sqlite3.Row
    if not _existe_tabla(vieja, "peliculas"):
        raise SystemExit(
            f"{ruta_sqlite} no parece una base de Cinema (falta 'peliculas').")

    servicio = _preparar_destino(servicio or CineService(), recrear)
    conn = servicio.conn

    # Capacidad máxima por sala (los asientos físicos son compartidos).
    capacidades = {}
    for f in vieja.execute("SELECT sala, capacidad FROM funciones"):
        capacidades[f["sala"]] = max(capacidades.get(f["sala"], 0),
                                     int(f["capacidad"]))

    salas_ids = {}
    for nombre, capacidad in capacidades.items():
        cur = conn.execute("INSERT INTO salas (nombre) VALUES (?)", (nombre,))
        sala_id = cur.lastrowid
        salas_ids[nombre] = sala_id
        for fila, numero in _asientos_para(capacidad):
            conn.execute(
                "INSERT INTO asientos (sala_id, fila, numero) VALUES (?,?,?)",
                (sala_id, fila, numero))

    peliculas_ids = {}
    for p in vieja.execute("SELECT * FROM peliculas"):
        genero_id = servicio._id_genero(p["genero"])
        clas_id = servicio._id_clasificacion(p["clasificacion"])
        conn.execute(
            "INSERT INTO peliculas (id, titulo, genero_id, duracion_min, "
            "clasificacion_id, precio_base, activa, imagen) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (p["id"], p["titulo"], genero_id, p["duracion_min"], clas_id,
             p["precio_base"], p["activa"],
             p["imagen"] if "imagen" in p.keys() else ""))
        peliculas_ids[p["id"]] = p["id"]

    funciones_ids = {}
    asientos_por_sala = {}
    for f in vieja.execute("SELECT * FROM funciones"):
        sala_nombre = f["sala"]
        sala_id = salas_ids[sala_nombre]
        conn.execute(
            "INSERT INTO funciones (id, pelicula_id, sala_id, horario) "
            "VALUES (?, ?, ?, ?)",
            (f["id"], peliculas_ids[f["pelicula_id"]], sala_id, f["horario"]))
        funciones_ids[f["id"]] = {"id": f["id"], "sala_id": sala_id}

        if sala_id not in asientos_por_sala:
            filas = conn.execute(
                "SELECT id, fila, numero FROM asientos WHERE sala_id = ?",
                (sala_id,)).fetchall()
            asientos_por_sala[sala_id] = {
                f"{a['fila']}-{a['numero']}": a["id"] for a in filas}

    mapa_asientos = {}
    if _existe_tabla(vieja, "asientos"):
        for a in vieja.execute("SELECT * FROM asientos"):
            funcion = funciones_ids.get(a["funcion_id"])
            if not funcion:
                continue
            mapa_asientos[a["id"]] = asientos_por_sala[
                funcion["sala_id"]][a["posicion"]]

    estados = {
        fila["nombre"]: fila["id"]
        for fila in conn.execute("SELECT id, nombre FROM estados_venta")
    }

    ventas_migradas = 0
    for v in vieja.execute("SELECT * FROM ventas"):
        cur_cliente = conn.execute(
            "INSERT INTO clientes (nombre, edad) VALUES (?, ?)",
            (v["cliente_nombre"], v["edad"]))
        estado_id = estados.get(v["estado"], estados["activa"])
        conn.execute(
            "INSERT INTO ventas (id, folio, cliente_id, funcion_id, "
            "estado_id, fecha_hora, precio_unitario, descuento_pct) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (v["id"], v["folio"], cur_cliente.lastrowid, v["funcion_id"],
             estado_id, v["fecha_hora"], v["precio_unitario"],
             v["descuento_pct"]))
        ventas_migradas += 1

    boletos_migrados = 0
    if _existe_tabla(vieja, "ventas_asientos"):
        for va in vieja.execute("SELECT * FROM ventas_asientos"):
            asiento_id = mapa_asientos.get(va["asiento_id"])
            if not asiento_id:
                continue
            try:
                conn.execute(
                    "INSERT INTO boletos (venta_id, asiento_id) "
                    "VALUES (?, ?)", (va["venta_id"], asiento_id))
                boletos_migrados += 1
            except Exception:
                # Datos históricos duplicados: se conserva el primero.
                pass

    conn.commit()
    vieja.close()
    print("Migración completada:")
    print(f"  Películas: {len(peliculas_ids)}")
    print(f"  Funciones: {len(funciones_ids)}")
    print(f"  Ventas: {ventas_migradas}")
    print(f"  Boletos: {boletos_migrados}")
    return servicio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite", default=os.path.join(RAIZ, "data", "cine.db"),
        help="Ruta de la base SQLite antigua (por defecto data/cine.db).")
    parser.add_argument(
        "--recrear", action="store_true",
        help="Borra las tablas del destino antes de migrar.")
    args = parser.parse_args()
    migrar(args.sqlite, recrear=args.recrear)


if __name__ == "__main__":
    main()
