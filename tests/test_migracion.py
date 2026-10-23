"""Pruebas de la migración del esquema SQLite histórico al normalizado."""

import sqlite3

from backend.models import CineService
from scripts.migrar_sqlite_a_mariadb import migrar


def _crear_vieja(tmp_path):
    ruta = str(tmp_path / "vieja.db")
    conn = sqlite3.connect(ruta)
    conn.executescript(
        "CREATE TABLE peliculas (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "titulo TEXT, genero TEXT, duracion_min INTEGER, clasificacion TEXT, "
        "precio_base REAL, activa INTEGER DEFAULT 1, imagen TEXT DEFAULT '');"
        "CREATE TABLE funciones (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "pelicula_id INTEGER, sala TEXT, horario TEXT, capacidad INTEGER, "
        "ocupados INTEGER DEFAULT 0);"
        "CREATE TABLE ventas (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "folio TEXT UNIQUE, funcion_id INTEGER, cliente_nombre TEXT, "
        "edad INTEGER, cantidad_boletos INTEGER, precio_unitario REAL, "
        "descuento_pct REAL, total REAL, fecha_hora TEXT, estado TEXT);"
        "CREATE TABLE asientos (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "funcion_id INTEGER, posicion TEXT, fila TEXT, numero INTEGER, "
        "estado TEXT, UNIQUE (funcion_id, posicion));"
        "CREATE TABLE ventas_asientos (venta_id INTEGER, asiento_id INTEGER, "
        "PRIMARY KEY (venta_id, asiento_id));"
        "INSERT INTO peliculas (titulo, genero, duracion_min, clasificacion, "
        "precio_base) VALUES ('Vieja', 'Drama', 90, 'B', 50);"
        "INSERT INTO funciones (pelicula_id, sala, horario, capacidad) "
        "VALUES (1, 'Sala 1', '10:00', 5);"
        "INSERT INTO asientos (funcion_id, posicion, fila, numero, estado) "
        "VALUES (1,'A-1','A',1,'ocupado'),(1,'A-2','A',2,'libre'),"
        "(1,'A-3','A',3,'libre'),(1,'A-4','A',4,'libre'),"
        "(1,'A-5','A',5,'libre');"
        "INSERT INTO ventas (folio, funcion_id, cliente_nombre, edad, "
        "cantidad_boletos, precio_unitario, descuento_pct, total, "
        "fecha_hora, estado) VALUES "
        "('V00001',1,'Ana',30,1,50,0,50,'2024-01-15 18:00:00','activa'),"
        "('V00002',1,'Nia',10,1,50,0.5,25,'2024-01-16 19:00:00','cancelada');"
        "INSERT INTO ventas_asientos (venta_id, asiento_id) "
        "VALUES (1,1),(2,2);")
    conn.commit()
    conn.close()
    return ruta


def test_migracion_conserva_datos_y_estados(tmp_path):
    vieja = _crear_vieja(tmp_path)
    destino = CineService(str(tmp_path / "nueva.db"))
    migrar(vieja, servicio=destino)

    assert [p.titulo for p in destino.listar_peliculas(False)] == ["Vieja"]
    assert len(destino.listar_funciones(solo_pelicula_activa=False)) == 1
    ventas = destino.ventas_detalladas()
    assert {v["folio"] for v in ventas} == {"V00001", "V00002"}
    activa = next(v for v in ventas if v["folio"] == "V00001")
    cancelada = next(v for v in ventas if v["folio"] == "V00002")
    assert activa["estado"] == "activa"
    assert activa["asientos"] == "A-1"
    assert cancelada["estado"] == "cancelada"
    assert destino.lugares_disponibles(1) == 4
    assert destino.ventas_reporte("general")["total_ingresos"] == 50.0
