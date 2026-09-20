"""Conexión y esquema de la base de datos SQLite del cine."""

import os
import sqlite3

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_DB = os.path.join(RAIZ, "data", "cine.db")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS peliculas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    genero TEXT NOT NULL,
    duracion_min INTEGER NOT NULL CHECK (duracion_min > 0),
    clasificacion TEXT NOT NULL,
    precio_base REAL NOT NULL CHECK (precio_base >= 0),
    activa INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS funciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pelicula_id INTEGER NOT NULL REFERENCES peliculas(id),
    sala TEXT NOT NULL,
    horario TEXT NOT NULL,
    capacidad INTEGER NOT NULL CHECK (capacidad > 0),
    ocupados INTEGER NOT NULL DEFAULT 0 CHECK (ocupados >= 0)
);

CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folio TEXT NOT NULL UNIQUE,
    funcion_id INTEGER NOT NULL REFERENCES funciones(id),
    cliente_nombre TEXT NOT NULL,
    edad INTEGER NOT NULL CHECK (edad >= 0),
    cantidad_boletos INTEGER NOT NULL CHECK (cantidad_boletos > 0),
    precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
    descuento_pct REAL NOT NULL DEFAULT 0,
    total REAL NOT NULL CHECK (total >= 0),
    fecha_hora TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'activa' CHECK (estado IN ('activa', 'cancelada'))
);

CREATE INDEX IF NOT EXISTS idx_funciones_pelicula ON funciones(pelicula_id);
CREATE INDEX IF NOT EXISTS idx_ventas_funcion ON ventas(funcion_id);
"""


def conexion(ruta=None):
    """Abre (creando si falta) la base y devuelve una conexión con filas tipo Row."""
    ruta = ruta or RUTA_DB
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_db(ruta=None):
    """Crea el esquema si no existe y devuelve la conexión."""
    conn = conexion(ruta)
    conn.executescript(ESQUEMA)
    conn.commit()
    return conn