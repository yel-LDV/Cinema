"""Conexión y esquema de la base de datos del cine.

El proyecto usa **MariaDB** en ejecución normal y **SQLite** para las pruebas
automáticas (cuando se pasa una ruta de archivo a ``CineService``). Ambas
conexiones se exponen mediante el mismo envoltorio :class:`Conexion`, de modo
que la capa de negocio no depende del motor.

Configuración de MariaDB por variables de entorno (valores por defecto entre
paréntesis)::

    CINEMA_DB_HOST      (127.0.0.1)
    CINEMA_DB_PORT      (3306)
    CINEMA_DB_USER      (cinema)
    CINEMA_DB_PASSWORD  (cinema123)
    CINEMA_DB_NAME      (cinema)

El esquema está normalizado a 3FN: catálogos (géneros, clasificaciones,
descuentos, estados), salas y asientos físicos, funciones, clientes, ventas y
boletos. Los datos derivados (ocupación, total, cantidad de boletos) no se
almacenan: se calculan a partir de las relaciones.
"""

import os
import sqlite3

try:  # Dependencia opcional para que las pruebas con SQLite no la necesiten.
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:  # pragma: no cover - depende del entorno
    pymysql = None
    DictCursor = None

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ruta de la base SQLite histórica (se usa solo para migrar datos).
RUTA_DB = os.path.join(RAIZ, "data", "cine.db")

# Catálogos iniciales (también están normalizados en la base).
CLASIFICACIONES_INICIALES = [
    ("AA", 0), ("A", 0), ("B", 0), ("B15", 15),
    ("C", 18), ("D", 18), ("R", 18),
]
DESCUENTOS_INICIALES = [
    (0, 12, 0.50),
    (13, 17, 0.20),
    (18, 59, 0.00),
    (60, 200, 0.30),
]
ESTADOS_VENTA_INICIALES = ["activa", "cancelada"]


class ErrorConexion(Exception):
    """No se pudo abrir o inicializar la base de datos."""


def _cargar_env_local():
    """Carga variables desde .env (sin sobrescribir las ya exportadas)."""
    ruta = os.path.join(RAIZ, ".env")
    if not os.path.isfile(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            valor = valor.strip().strip('"').strip("'")
            os.environ.setdefault(clave.strip(), valor)


def config_mariadb():
    """Lee la configuración de MariaDB desde el entorno (y de .env)."""
    _cargar_env_local()
    return {
        "host": os.getenv("CINEMA_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("CINEMA_DB_PORT", "3306")),
        "user": os.getenv("CINEMA_DB_USER", "cinema"),
        "password": os.getenv("CINEMA_DB_PASSWORD", "cinema123"),
        "database": os.getenv("CINEMA_DB_NAME", "cinema"),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
    }


class Conexion:
    """Envoltorio mínimo y homogéneo sobre PyMySQL y sqlite3.

    Soporta ``execute`` con marcadores ``?``, ``executescript``, ``commit``,
    ``rollback`` y el protocolo de contexto (commit/rollback automático).
    """

    def __init__(self, motor, cruda):
        self.motor = motor
        self.cruda = cruda

    @property
    def es_mariadb(self):
        return self.motor == "mariadb"

    def execute(self, sql, params=()):
        if self.es_mariadb:
            sql = sql.replace("?", "%s")
        cur = self.cruda.cursor()
        cur.execute(sql, params)
        return cur

    def executescript(self, script):
        if not self.es_mariadb:
            self.cruda.executescript(script)
            return
        for sentencia in script.split(";"):
            sentencia = sentencia.strip()
            if sentencia:
                self.cruda.cursor().execute(sentencia)

    def commit(self):
        self.cruda.commit()

    def rollback(self):
        self.cruda.rollback()

    def close(self):
        try:
            self.cruda.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


def conexion(ruta=None):
    """Abre una conexión. ``ruta`` no nula fuerza SQLite (pruebas/migración)."""
    if ruta is not None:
        return _conectar_sqlite(ruta)
    return _conectar_mariadb()


def _conectar_sqlite(ruta):
    if ruta != ":memory:":
        carpeta = os.path.dirname(os.path.abspath(ruta))
        os.makedirs(carpeta, exist_ok=True)
    cruda = sqlite3.connect(ruta)
    cruda.row_factory = sqlite3.Row
    cruda.execute("PRAGMA foreign_keys = ON")
    return Conexion("sqlite", cruda)


def _conectar_mariadb(cfg=None):
    if pymysql is None:
        raise ErrorConexion(
            "Falta el controlador PyMySQL. Instala con: "
            ".venv/bin/pip install -r requirements.txt")
    cfg = dict(cfg or config_mariadb())
    try:
        cruda = pymysql.connect(**cfg)
    except pymysql.err.OperationalError as e:
        if e.args and e.args[0] == 1049:  # base de datos inexistente
            cruda = _crear_base_mariadb(cfg)
        else:
            raise ErrorConexion(
                "No se pudo conectar a MariaDB. Revisa que el servidor esté "
                "activo y las variables CINEMA_DB_*. Detalle: "
                f"{e}") from e
    return Conexion("mariadb", cruda)


def _crear_base_mariadb(cfg):
    """Intenta crear la base si el usuario tiene permiso; si no, informa."""
    nombre = cfg["database"]
    sin_bd = dict(cfg)
    sin_bd.pop("database", None)
    try:
        cruda = pymysql.connect(**sin_bd)
        cruda.cursor().execute(
            f"CREATE DATABASE IF NOT EXISTS `{nombre}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cruda.commit()
        cruda.close()
        return pymysql.connect(**cfg)
    except pymysql.err.MySQLError as e:
        raise ErrorConexion(
            f"La base '{nombre}' no existe y no se pudo crear. Ejecuta "
            "scripts/crear_bd_mariadb.sql como administrador. "
            f"Detalle: {e}") from e


def inicializar_db(ruta=None):
    """Crea el esquema normalizado si falta y devuelve una :class:`Conexion`."""
    conn = conexion(ruta)
    conn.executescript(_esquema(conn.motor))
    conn.commit()
    _sembrar_catalogos(conn)
    return conn


def _sembrar_catalogos(conn):
    with conn:
        for codigo, edad in CLASIFICACIONES_INICIALES:
            conn.execute(
                "INSERT INTO clasificaciones (codigo, edad_minima) "
                "SELECT ?, ? WHERE NOT EXISTS ("
                "SELECT 1 FROM clasificaciones WHERE codigo = ?)",
                (codigo, edad, codigo))
        for edad_min, edad_max, pct in DESCUENTOS_INICIALES:
            conn.execute(
                "INSERT INTO descuentos (edad_min, edad_max, porcentaje) "
                "SELECT ?, ?, ? WHERE NOT EXISTS ("
                "SELECT 1 FROM descuentos WHERE edad_min = ? "
                "AND edad_max = ?)",
                (edad_min, edad_max, pct, edad_min, edad_max))
        for estado in ESTADOS_VENTA_INICIALES:
            conn.execute(
                "INSERT INTO estados_venta (nombre) "
                "SELECT ? WHERE NOT EXISTS ("
                "SELECT 1 FROM estados_venta WHERE nombre = ?)",
                (estado, estado))


def _esquema(motor):
    """Devuelve el DDL del esquema normalizado para el motor indicado."""
    if motor == "mariadb":
        id_t = "INT AUTO_INCREMENT PRIMARY KEY"
        fk_t = "INT NOT NULL"
        texto = "VARCHAR(255)"
        corto = "VARCHAR(5)"
        dinero = "DECIMAL(10,2)"
        pct = "DECIMAL(5,4)"
        entero = "INT"
        fecha = "DATETIME"
        extra = " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        check_activa = "CHECK (activa IN (0, 1))"
    else:
        id_t = "INTEGER PRIMARY KEY AUTOINCREMENT"
        fk_t = "INTEGER NOT NULL"
        texto = "TEXT"
        corto = "TEXT"
        dinero = "REAL"
        pct = "REAL"
        entero = "INTEGER"
        fecha = "TEXT"
        extra = ""
        check_activa = "CHECK (activa IN (0, 1))"

    tablas = [
        f"""CREATE TABLE IF NOT EXISTS generos (
            id {id_t},
            nombre {texto} NOT NULL UNIQUE
        ){extra}""",
        f"""CREATE TABLE IF NOT EXISTS clasificaciones (
            id {id_t},
            codigo {texto} NOT NULL UNIQUE,
            edad_minima {entero} NOT NULL CHECK (edad_minima >= 0)
        ){extra}""",
        f"""CREATE TABLE IF NOT EXISTS salas (
            id {id_t},
            nombre {texto} NOT NULL UNIQUE
        ){extra}""",
        f"""CREATE TABLE IF NOT EXISTS asientos (
            id {id_t},
            sala_id {fk_t} REFERENCES salas(id),
            fila {texto} NOT NULL,
            numero {entero} NOT NULL CHECK (numero > 0),
            UNIQUE (sala_id, fila, numero)
        ){extra}""",
        f"""CREATE TABLE IF NOT EXISTS peliculas (
            id {id_t},
            titulo {texto} NOT NULL,
            genero_id {fk_t} REFERENCES generos(id),
            duracion_min {entero} NOT NULL CHECK (duracion_min > 0),
            clasificacion_id {fk_t} REFERENCES clasificaciones(id),
            precio_base {dinero} NOT NULL CHECK (precio_base >= 0),
            activa {entero} NOT NULL DEFAULT 1 {check_activa},
            imagen {texto} NOT NULL DEFAULT ''
        ){extra}""",
        f"""CREATE TABLE IF NOT EXISTS funciones (
            id {id_t},
            pelicula_id {fk_t} REFERENCES peliculas(id),
            sala_id {fk_t} REFERENCES salas(id),
            horario {corto} NOT NULL
        ){extra}""",
        f"""CREATE TABLE IF NOT EXISTS clientes (
            id {id_t},
            nombre {texto} NOT NULL,
            edad {entero} NOT NULL CHECK (edad >= 0)
        ){extra}""",
        f"""CREATE TABLE IF NOT EXISTS descuentos (
            id {id_t},
            edad_min {entero} NOT NULL CHECK (edad_min >= 0),
            edad_max {entero} NOT NULL,
            porcentaje {pct} NOT NULL CHECK (porcentaje >= 0 AND porcentaje <= 1),
            CHECK (edad_min <= edad_max)
        ){extra}""",
        f"""CREATE TABLE IF NOT EXISTS estados_venta (
            id {id_t},
            nombre {texto} NOT NULL UNIQUE
        ){extra}""",
        f"""CREATE TABLE IF NOT EXISTS ventas (
            id {id_t},
            folio {texto} NOT NULL UNIQUE,
            cliente_id {fk_t} REFERENCES clientes(id),
            funcion_id {fk_t} REFERENCES funciones(id),
            estado_id {fk_t} REFERENCES estados_venta(id),
            fecha_hora {fecha} NOT NULL,
            precio_unitario {dinero} NOT NULL CHECK (precio_unitario >= 0),
            descuento_pct {pct} NOT NULL DEFAULT 0
        ){extra}""",
        f"""CREATE TABLE IF NOT EXISTS boletos (
            venta_id {fk_t} REFERENCES ventas(id) ON DELETE CASCADE,
            asiento_id {fk_t} REFERENCES asientos(id),
            PRIMARY KEY (venta_id, asiento_id)
        ){extra}""",
    ]
    return ";\n".join(tablas)
