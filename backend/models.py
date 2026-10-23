"""Clases de dominio y servicio central (reglas de negocio) del cine.

El modelo de datos está normalizado a 3FN. Las entidades de catálogo
(géneros, clasificaciones, descuentos, estados), las salas/asientos físicos,
los clientes y las ventas viven en tablas separadas; los valores derivados
(ocupación, total, cantidad de boletos) se calculan al consultar.
"""

import re
from datetime import datetime, timedelta

from backend.database import RUTA_DB, inicializar_db  # noqa: F401

# Valores por defecto (también sembrados en las tablas de catálogo). Se
# conservan como funciones puras para pruebas y para no acoplar la UI.
REGLAS_DESCUENTO = [
    (12, 0.50),   # 0-12  → 50%
    (17, 0.20),   # 13-17 → 20%
    (59, 0.00),   # 18-59 → 0%
    (200, 0.30),  # 60+   → 30%
]

CLASIFICACION_EDAD = {
    "AA": 0,
    "A": 0,
    "B": 0,
    "B15": 15,
    "C": 18,
    "D": 18,
    "R": 18,
}
EDAD_MIN_DESCONOCIDA = 0

# Disposición del salón: asientos por fila (filas A, B, C…).
SEATS_POR_FILA = 8


class ErrorNegocio(Exception):
    """Error en una regla de negocio; su mensaje es apto para el usuario."""


def calcular_descuento_por_edad(edad, reglas=None):
    """Devuelve el porcentaje de descuento aplicable a una edad."""
    reglas = reglas if reglas is not None else REGLAS_DESCUENTO
    for limite, pct in sorted(reglas):
        if edad <= limite:
            return pct
    return 0.0


def edad_minima_clasificacion(clasificacion, mapa=None):
    mapa = mapa if mapa is not None else CLASIFICACION_EDAD
    return mapa.get(clasificacion, EDAD_MIN_DESCONOCIDA)


def _normalizar_posicion(posicion):
    """Normaliza una posición de asiento a mayúsculas (ej. 'f-5' → 'F-5')."""
    posicion = posicion.strip().upper()
    if not re.fullmatch(r"[A-Z]+-\d+", posicion):
        raise ErrorNegocio(
            f"Posición de asiento no válida: {posicion!r}. Usa formato F-5.")
    return posicion


def _validar_hhmm(horario):
    """Valida y normaliza un horario 'HH:MM' (24 h)."""
    horario = horario.strip()
    if not re.fullmatch(r"\d{2}:\d{2}", horario):
        raise ErrorNegocio("El horario debe tener formato HH:MM (24 h).")
    h, m = horario.split(":")
    if int(h) > 23 or int(m) > 59:
        raise ErrorNegocio("El horario debe ser una hora válida (00:00–23:59).")
    return f"{int(h):02d}:{int(m):02d}"


def _a_minutos(horario):
    h, m = horario.split(":")
    return int(h) * 60 + int(m)


def _hora_texto(minutos):
    h, m = divmod(minutos % (24 * 60), 60)
    return f"{h:02d}:{m:02d}"


def _generar_disposicion(capacidad, por_fila=SEATS_POR_FILA):
    """Devuelve lista de (fila, número) para una sala con 'capacidad' asientos."""
    resultado = []
    letra_idx = 0
    resto = capacidad
    while resto > 0:
        n = min(por_fila, resto)
        letra = chr(ord("A") + letra_idx)
        for i in range(1, n + 1):
            resultado.append((letra, i))
        resto -= n
        letra_idx += 1
    return resultado


def _numero(valor, defecto=0):
    """Convierte Decimal/str de la base a número (float/int) sin sorpresas."""
    if valor is None:
        return defecto
    return float(valor)


def _texto_fecha(valor):
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    return str(valor)


class Pelicula:
    def __init__(self, id, titulo, genero, duracion_min, clasificacion,
                 precio_base, activa=True, imagen=""):
        self.id = id
        self.titulo = titulo
        self.genero = genero
        self.duracion_min = duracion_min
        self.clasificacion = clasificacion
        self.precio_base = _numero(precio_base)
        self.activa = bool(activa)
        self.imagen = imagen or ""

    @classmethod
    def desde_fila(cls, fila):
        return cls(fila["id"], fila["titulo"], fila["genero"],
                   fila["duracion_min"], fila["clasificacion"],
                   fila["precio_base"], fila["activa"],
                   fila["imagen"] if "imagen" in fila.keys() else "")

    def __repr__(self):
        return f"<Pelicula {self.id} {self.titulo!r}>"


class Funcion:
    def __init__(self, id, pelicula_id, sala, horario, capacidad, ocupados=0):
        self.id = id
        self.pelicula_id = pelicula_id
        self.sala = sala
        self.horario = horario
        self.capacidad = int(capacidad)
        self.ocupados = int(ocupados)

    @property
    def disponibles(self):
        return self.capacidad - self.ocupados

    @classmethod
    def desde_fila(cls, fila):
        return cls(fila["id"], fila["pelicula_id"], fila["sala"],
                   fila["horario"], fila["capacidad"], fila["ocupados"])

    def __repr__(self):
        return f"<Funcion {self.id} sala={self.sala} {self.horario}>"


class Cliente:
    def __init__(self, nombre, edad):
        if not nombre or not nombre.strip():
            raise ErrorNegocio("El nombre del cliente no puede estar vacío.")
        if edad < 0:
            raise ErrorNegocio("La edad no puede ser negativa.")
        self.nombre = nombre.strip()
        self.edad = edad

    def calcular_descuento(self, reglas=None):
        return calcular_descuento_por_edad(self.edad, reglas)

    def validar_clasificacion(self, clasificacion, mapa=None):
        return self.edad >= edad_minima_clasificacion(clasificacion, mapa)


class Venta:
    def __init__(self, id, folio, funcion_id, cliente_nombre, edad,
                 cantidad_boletos, precio_unitario, descuento_pct, total,
                 fecha_hora, estado="activa"):
        self.id = id
        self.folio = folio
        self.funcion_id = funcion_id
        self.cliente_nombre = cliente_nombre
        self.edad = edad
        self.cantidad_boletos = cantidad_boletos
        self.precio_unitario = _numero(precio_unitario)
        self.descuento_pct = _numero(descuento_pct)
        self.total = _numero(total)
        self.fecha_hora = fecha_hora
        self.estado = estado

    @property
    def subtotal(self):
        return round(self.cantidad_boletos * self.precio_unitario, 2)

    @classmethod
    def desde_fila(cls, fila):
        return cls(fila["id"], fila["folio"], fila["funcion_id"],
                   fila["cliente_nombre"], fila["edad"],
                   fila["cantidad_boletos"], fila["precio_unitario"],
                   fila["descuento_pct"], fila["total"], fila["fecha_hora"],
                   fila["estado"])

    def __repr__(self):
        return f"<Venta {self.folio} {self.estado} ${self.total}>"


class CineService:
    """Fachada única: toda la lógica de negocio sobre MariaDB/SQLite.

    Las GUIs (usuario y admin) solo conversan con esta clase.
    """

    def __init__(self, ruta_db=None):
        self.ruta_db = ruta_db
        self.conn = inicializar_db(ruta_db)
        self._cache_estados = {}

    # ------------------------------------------------------------------ #
    #                         Catálogos internos                         #
    # ------------------------------------------------------------------ #
    def _id_estado(self, nombre):
        if nombre not in self._cache_estados:
            fila = self.conn.execute(
                "SELECT id FROM estados_venta WHERE nombre = ?",
                (nombre,)).fetchone()
            if fila is None:
                raise ErrorNegocio(f"Estado de venta desconocido: {nombre}.")
            self._cache_estados[nombre] = fila["id"]
        return self._cache_estados[nombre]

    def _id_genero(self, nombre):
        nombre = nombre.strip()
        fila = self.conn.execute(
            "SELECT id FROM generos WHERE nombre = ?", (nombre,)).fetchone()
        if fila:
            return fila["id"]
        cur = self.conn.execute(
            "INSERT INTO generos (nombre) VALUES (?)", (nombre,))
        return cur.lastrowid

    def _id_clasificacion(self, codigo):
        fila = self.conn.execute(
            "SELECT id FROM clasificaciones WHERE codigo = ?",
            (codigo,)).fetchone()
        if fila is None:
            raise ErrorNegocio(f"Clasificación desconocida: {codigo}.")
        return fila["id"]

    def _descuento_para_edad(self, edad):
        fila = self.conn.execute(
            "SELECT porcentaje FROM descuentos "
            "WHERE ? BETWEEN edad_min AND edad_max "
            "ORDER BY edad_min DESC LIMIT 1", (edad,)).fetchone()
        return _numero(fila["porcentaje"]) if fila else 0.0

    # ------------------------------------------------------------------ #
    #                           Películas                                #
    # ------------------------------------------------------------------ #
    _SELECT_PELICULA = (
        "SELECT p.id, p.titulo, g.nombre AS genero, p.duracion_min, "
        "c.codigo AS clasificacion, p.precio_base, p.activa, p.imagen "
        "FROM peliculas p "
        "JOIN generos g ON g.id = p.genero_id "
        "JOIN clasificaciones c ON c.id = p.clasificacion_id")

    def _validar_datos_pelicula(self, titulo, genero, duracion_min,
                                clasificacion, precio_base):
        if not titulo.strip():
            raise ErrorNegocio("El título no puede estar vacío.")
        if not genero.strip():
            raise ErrorNegocio("El género no puede estar vacío.")
        if duracion_min <= 0:
            raise ErrorNegocio("La duración debe ser mayor a cero.")
        if precio_base < 0:
            raise ErrorNegocio("El precio no puede ser negativo.")
        clasificacion_id = self._id_clasificacion(clasificacion)
        return titulo.strip(), genero.strip(), clasificacion_id

    def crear_pelicula(self, titulo, genero, duracion_min, clasificacion,
                       precio_base, imagen=""):
        titulo, genero, clasificacion_id = self._validar_datos_pelicula(
            titulo, genero, duracion_min, clasificacion, precio_base)
        with self.conn:
            genero_id = self._id_genero(genero)
            cur = self.conn.execute(
                "INSERT INTO peliculas (titulo, genero_id, duracion_min, "
                "clasificacion_id, precio_base, activa, imagen) "
                "VALUES (?, ?, ?, ?, ?, 1, ?)",
                (titulo, genero_id, duracion_min, clasificacion_id,
                 precio_base, imagen or ""))
        return self.obtener_pelicula(cur.lastrowid)

    def editar_pelicula(self, pelicula_id, titulo, genero, duracion_min,
                        clasificacion, precio_base, imagen=None):
        """Actualiza la película; rechaza cambios de duración que solapen
        funciones ya programadas. imagen=None conserva la actual."""
        if self.obtener_pelicula(pelicula_id) is None:
            raise ErrorNegocio("Película no encontrada.")
        titulo, genero, clasificacion_id = self._validar_datos_pelicula(
            titulo, genero, duracion_min, clasificacion, precio_base)
        with self.conn:
            genero_id = self._id_genero(genero)
            if imagen is None:
                self.conn.execute(
                    "UPDATE peliculas SET titulo=?, genero_id=?, "
                    "duracion_min=?, clasificacion_id=?, precio_base=? "
                    "WHERE id=?",
                    (titulo, genero_id, duracion_min, clasificacion_id,
                     precio_base, pelicula_id))
            else:
                self.conn.execute(
                    "UPDATE peliculas SET titulo=?, genero_id=?, "
                    "duracion_min=?, clasificacion_id=?, precio_base=?, "
                    "imagen=? WHERE id=?",
                    (titulo, genero_id, duracion_min, clasificacion_id,
                     precio_base, imagen or "", pelicula_id))
            self._verificar_solapamientos_pelicula(pelicula_id, duracion_min)
        return self.obtener_pelicula(pelicula_id)

    def dar_de_baja_pelicula(self, pelicula_id):
        peli = self.obtener_pelicula(pelicula_id)
        if peli is None:
            raise ErrorNegocio("Película no encontrada.")
        if not peli.activa:
            raise ErrorNegocio("La película ya está dada de baja.")
        self.conn.execute(
            "UPDATE peliculas SET activa = 0 WHERE id = ?", (pelicula_id,))
        self.conn.commit()

    def obtener_pelicula(self, pelicula_id):
        fila = self.conn.execute(
            self._SELECT_PELICULA + " WHERE p.id = ?",
            (pelicula_id,)).fetchone()
        return Pelicula.desde_fila(fila) if fila else None

    def listar_peliculas(self, solo_activas=True):
        sql = self._SELECT_PELICULA
        if solo_activas:
            sql += " WHERE p.activa = 1"
        sql += " ORDER BY p.titulo"
        return [Pelicula.desde_fila(f)
                for f in self.conn.execute(sql).fetchall()]

    # ------------------------------------------------------------------ #
    #                           Funciones                                #
    # ------------------------------------------------------------------ #
    def _sala_por_nombre(self, nombre):
        return self.conn.execute(
            "SELECT id FROM salas WHERE nombre = ?", (nombre,)).fetchone()

    def _crear_sala(self, nombre, capacidad):
        cur = self.conn.execute(
            "INSERT INTO salas (nombre) VALUES (?)", (nombre,))
        sala_id = cur.lastrowid
        self._crear_asientos(sala_id, capacidad)
        return sala_id

    def _contar_asientos_sala(self, sala_id):
        fila = self.conn.execute(
            "SELECT COUNT(*) AS n FROM asientos WHERE sala_id = ?",
            (sala_id,)).fetchone()
        return int(fila["n"])

    def crear_funcion(self, pelicula_id, sala, horario, capacidad):
        pelicula = self.obtener_pelicula(pelicula_id)
        if pelicula is None:
            raise ErrorNegocio("La película no existe.")
        if not sala.strip():
            raise ErrorNegocio("La sala no puede estar vacía.")
        if capacidad <= 0:
            raise ErrorNegocio("La capacidad debe ser mayor a cero.")
        horario = _validar_hhmm(horario)
        sala = sala.strip()
        fila_sala = self._sala_por_nombre(sala)
        if fila_sala:
            sala_id = fila_sala["id"]
            existente = self._contar_asientos_sala(sala_id)
            if existente != capacidad:
                raise ErrorNegocio(
                    f"La sala {sala} ya existe con capacidad {existente}; "
                    f"no puede crearse con {capacidad}.")
        else:
            with self.conn:
                sala_id = self._crear_sala(sala, capacidad)
        self._revisar_solapamiento_sala(sala_id, horario,
                                        pelicula.duracion_min)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO funciones (pelicula_id, sala_id, horario) "
                "VALUES (?, ?, ?)", (pelicula_id, sala_id, horario))
        return self.obtener_funcion(cur.lastrowid)

    def _revisar_solapamiento_sala(self, sala_id, horario, duracion_min,
                                   excepto_funcion_id=None):
        """Levanta ErrorNegocio si la sala ya tiene una función solapada."""
        sql = ("SELECT f.id, f.horario, p.duracion_min, p.titulo "
               "FROM funciones f JOIN peliculas p ON p.id = f.pelicula_id "
               "WHERE f.sala_id = ?")
        params = [sala_id]
        if excepto_funcion_id is not None:
            sql += " AND f.id <> ?"
            params.append(excepto_funcion_id)
        filas = self.conn.execute(sql, params).fetchall()
        inicio = _a_minutos(horario)
        fin = inicio + duracion_min
        for f in filas:
            i_viejo = _a_minutos(f["horario"])
            f_viejo = i_viejo + f["duracion_min"]
            if inicio < f_viejo and i_viejo < fin:
                raise ErrorNegocio(
                    f"Conflicto de horario en la sala: la función de "
                    f"'{f['titulo']}' empieza a las {f['horario']} y ocupa "
                    f"la sala hasta las {_hora_texto(f_viejo)}.")

    def _verificar_solapamientos_pelicula(self, pelicula_id, duracion_min):
        """Tras editar la duración, verifica que ninguna función de la
        película quede solapada en su sala."""
        funciones = self.conn.execute(
            "SELECT id, sala_id, horario FROM funciones "
            "WHERE pelicula_id = ?", (pelicula_id,)).fetchall()
        for f in funciones:
            self._revisar_solapamiento_sala(f["sala_id"], f["horario"],
                                            duracion_min,
                                            excepto_funcion_id=f["id"])

    def _crear_asientos(self, sala_id, capacidad):
        for fila, numero in _generar_disposicion(capacidad):
            self.conn.execute(
                "INSERT INTO asientos (sala_id, fila, numero) "
                "VALUES (?, ?, ?)", (sala_id, fila, numero))

    _SELECT_FUNCION = (
        "SELECT f.id, f.pelicula_id, s.nombre AS sala, f.horario, "
        "(SELECT COUNT(*) FROM asientos a WHERE a.sala_id = f.sala_id) "
        "AS capacidad, "
        "(SELECT COUNT(*) FROM boletos b JOIN ventas v ON v.id = b.venta_id "
        "WHERE v.funcion_id = f.id AND v.estado_id = ?) AS ocupados "
        "FROM funciones f JOIN salas s ON s.id = f.sala_id")

    def obtener_funcion(self, funcion_id):
        activa = self._id_estado("activa")
        fila = self.conn.execute(
            self._SELECT_FUNCION + " WHERE f.id = ?",
            (activa, funcion_id)).fetchone()
        return Funcion.desde_fila(fila) if fila else None

    def listar_funciones(self, pelicula_id=None, solo_pelicula_activa=True):
        sql = self._SELECT_FUNCION
        params = [self._id_estado("activa")]
        if solo_pelicula_activa:
            sql += " JOIN peliculas p ON p.id = f.pelicula_id"
        condiciones = []
        if solo_pelicula_activa:
            condiciones.append("p.activa = 1")
        if pelicula_id is not None:
            condiciones.append("f.pelicula_id = ?")
            params.append(pelicula_id)
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " ORDER BY s.nombre, f.horario"
        return [Funcion.desde_fila(f)
                for f in self.conn.execute(sql, params).fetchall()]

    def _asientos_ocupados(self, funcion_id):
        activa = self._id_estado("activa")
        filas = self.conn.execute(
            "SELECT b.asiento_id FROM boletos b "
            "JOIN ventas v ON v.id = b.venta_id "
            "WHERE v.funcion_id = ? AND v.estado_id = ?",
            (funcion_id, activa)).fetchall()
        return {f["asiento_id"] for f in filas}

    def lugares_disponibles(self, funcion_id):
        funcion = self.obtener_funcion(funcion_id)
        if funcion is None:
            raise ErrorNegocio("Función no encontrada.")
        return funcion.disponibles

    # ------------------------------------------------------------------ #
    #                           Asientos                                 #
    # ------------------------------------------------------------------ #
    def listar_asientos(self, funcion_id):
        """Asientos físicos de la sala con su estado en esta función."""
        funcion = self.obtener_funcion(funcion_id)
        if funcion is None:
            raise ErrorNegocio("Función no encontrada.")
        sala_id = self.conn.execute(
            "SELECT sala_id FROM funciones WHERE id = ?",
            (funcion_id,)).fetchone()["sala_id"]
        ocupados = self._asientos_ocupados(funcion_id)
        filas = self.conn.execute(
            "SELECT id, fila, numero FROM asientos WHERE sala_id = ? "
            "ORDER BY fila, numero", (sala_id,)).fetchall()
        return [{
            "id": f["id"],
            "fila": f["fila"],
            "numero": f["numero"],
            "posicion": f"{f['fila']}-{f['numero']}",
            "estado": "ocupado" if f["id"] in ocupados else "libre",
        } for f in filas]

    def posiciones_libres(self, funcion_id, n):
        """Primeras n posiciones libres (para pruebas y sugerencias)."""
        libres = [a["posicion"] for a in self.listar_asientos(funcion_id)
                  if a["estado"] == "libre"]
        return libres[:n]

    # ------------------------------------------------------------------ #
    #                           Compras                                  #
    # ------------------------------------------------------------------ #
    def comprar_boletos(self, funcion_id, cliente, posiciones):
        """Registra la venta de asientos concretos, atómicamente.

        Posiciones: lista como ['F-5', 'F-6']. Cada asiento debe existir y
        estar libre; el mismo asiento nunca se vende dos veces.
        """
        if not posiciones:
            raise ErrorNegocio("Selecciona al menos un asiento.")
        posiciones = [_normalizar_posicion(p) for p in posiciones]
        if len(set(posiciones)) != len(posiciones):
            raise ErrorNegocio("No puedes repetir un asiento en la compra.")
        funcion = self.obtener_funcion(funcion_id)
        if funcion is None:
            raise ErrorNegocio("Función no encontrada.")
        pelicula = self.obtener_pelicula(funcion.pelicula_id)
        if pelicula is None or not pelicula.activa:
            raise ErrorNegocio(
                "La película de esta función ya no está disponible.")
        minimo = edad_minima_clasificacion(pelicula.clasificacion)
        if not cliente.validar_clasificacion(pelicula.clasificacion):
            raise ErrorNegocio(
                f"Clasificación {pelicula.clasificacion}: esta función "
                f"requiere edad mínima de {minimo} años.")

        with self.conn:
            if self.conn.es_mariadb:
                # Serializa compras concurrentes de la misma función para que
                # dos procesos no vendan el mismo asiento.
                self.conn.execute(
                    "SELECT id FROM funciones WHERE id = ? FOR UPDATE",
                    (funcion_id,))
            sala_id = self.conn.execute(
                "SELECT sala_id FROM funciones WHERE id = ?",
                (funcion_id,)).fetchone()["sala_id"]
            filas = self.conn.execute(
                "SELECT id, fila, numero FROM asientos WHERE sala_id = ?",
                (sala_id,)).fetchall()
            por_posicion = {f"{f['fila']}-{f['numero']}": f["id"]
                            for f in filas}
            faltantes = [p for p in posiciones if p not in por_posicion]
            if faltantes:
                raise ErrorNegocio(
                    "Uno o más asientos no existen en esta función: "
                    + ", ".join(faltantes))
            ocupados = self._asientos_ocupados(funcion_id)
            for posicion in posiciones:
                if por_posicion[posicion] in ocupados:
                    raise ErrorNegocio(
                        f"El asiento {posicion} ya está ocupado.")

            cantidad = len(posiciones)
            descuento = self._descuento_para_edad(cliente.edad)
            precio_unitario = pelicula.precio_base
            folio = self._generar_folio()
            cur_cliente = self.conn.execute(
                "INSERT INTO clientes (nombre, edad) VALUES (?, ?)",
                (cliente.nombre, cliente.edad))
            cur = self.conn.execute(
                "INSERT INTO ventas (folio, cliente_id, funcion_id, "
                "estado_id, fecha_hora, precio_unitario, descuento_pct) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (folio, cur_cliente.lastrowid, funcion_id,
                 self._id_estado("activa"),
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 precio_unitario, descuento))
            for posicion in posiciones:
                self.conn.execute(
                    "INSERT INTO boletos (venta_id, asiento_id) VALUES (?, ?)",
                    (cur.lastrowid, por_posicion[posicion]))
        return self.obtener_venta_por_id(cur.lastrowid)

    def _generar_folio(self):
        fila = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 AS n FROM ventas").fetchone()
        return f"V{int(fila['n']):05d}"

    def cancelar_compra(self, folio):
        """Cancela la venta (solo una vez). Los asientos vuelven a estar
        libres automáticamente al excluir ventas canceladas de la ocupación."""
        folio = folio.strip()
        venta = self.obtener_venta_por_folio(folio)
        if venta is None:
            raise ErrorNegocio("No existe una venta con ese folio.")
        if venta.estado == "cancelada":
            raise ErrorNegocio("La venta ya está cancelada.")
        with self.conn:
            self.conn.execute(
                "UPDATE ventas SET estado_id = ? WHERE id = ?",
                (self._id_estado("cancelada"), venta.id))
        return self.obtener_venta_por_folio(folio)

    # ------------------------------------------------------------------ #
    #                           Ventas                                   #
    # ------------------------------------------------------------------ #
    _SELECT_VENTA = (
        "SELECT v.id, v.folio, v.funcion_id, v.cliente_id, v.estado_id, "
        "v.fecha_hora, v.precio_unitario, v.descuento_pct, "
        "c.nombre AS cliente_nombre, c.edad, e.nombre AS estado, "
        "f.horario, s.nombre AS sala, p.titulo AS pelicula_titulo, "
        "cl.codigo AS clasificacion "
        "FROM ventas v "
        "JOIN clientes c ON c.id = v.cliente_id "
        "JOIN estados_venta e ON e.id = v.estado_id "
        "JOIN funciones f ON f.id = v.funcion_id "
        "JOIN salas s ON s.id = f.sala_id "
        "JOIN peliculas p ON p.id = f.pelicula_id "
        "JOIN clasificaciones cl ON cl.id = p.clasificacion_id")

    def _asientos_por_venta(self, venta_ids):
        if not venta_ids:
            return {}
        marcas = ", ".join("?" * len(venta_ids))
        filas = self.conn.execute(
            "SELECT b.venta_id, a.fila, a.numero FROM boletos b "
            "JOIN asientos a ON a.id = b.asiento_id "
            f"WHERE b.venta_id IN ({marcas}) "
            "ORDER BY a.fila, a.numero", tuple(venta_ids)).fetchall()
        resultado = {}
        for f in filas:
            posicion = f"{f['fila']}-{f['numero']}"
            resultado.setdefault(f["venta_id"], []).append(posicion)
        return resultado

    def _venta_desde_fila(self, fila, asientos):
        cantidad = len(asientos)
        total = round(cantidad * _numero(fila["precio_unitario"])
                      * (1 - _numero(fila["descuento_pct"])), 2)
        return Venta(
            fila["id"], fila["folio"], fila["funcion_id"],
            fila["cliente_nombre"], fila["edad"], cantidad,
            fila["precio_unitario"], fila["descuento_pct"], total,
            _texto_fecha(fila["fecha_hora"]), fila["estado"])

    def _detalle_desde_fila(self, fila, asientos):
        cantidad = len(asientos)
        total = round(cantidad * _numero(fila["precio_unitario"])
                      * (1 - _numero(fila["descuento_pct"])), 2)
        detalle = dict(fila)
        detalle["fecha_hora"] = _texto_fecha(fila["fecha_hora"])
        detalle["precio_unitario"] = _numero(fila["precio_unitario"])
        detalle["descuento_pct"] = _numero(fila["descuento_pct"])
        detalle["cantidad_boletos"] = cantidad
        detalle["total"] = total
        detalle["asientos"] = ", ".join(asientos)
        return detalle

    def obtener_venta_por_id(self, venta_id):
        fila = self.conn.execute(
            self._SELECT_VENTA + " WHERE v.id = ?", (venta_id,)).fetchone()
        if not fila:
            return None
        asientos = self._asientos_por_venta([venta_id]).get(venta_id, [])
        return self._venta_desde_fila(fila, asientos)

    def obtener_venta_por_folio(self, folio):
        fila = self.conn.execute(
            self._SELECT_VENTA + " WHERE v.folio = ?", (folio,)).fetchone()
        if not fila:
            return None
        asientos = self._asientos_por_venta([fila["id"]]).get(fila["id"], [])
        return self._venta_desde_fila(fila, asientos)

    def ventas_detalladas(self, estado=None):
        """Ventas enriquecidas con película, sala, horario y asientos."""
        sql = self._SELECT_VENTA
        params = []
        if estado:
            sql += " WHERE e.nombre = ?"
            params.append(estado)
        sql += " ORDER BY v.fecha_hora DESC, v.id DESC"
        filas = self.conn.execute(sql, params).fetchall()
        asientos = self._asientos_por_venta([f["id"] for f in filas])
        return [self._detalle_desde_fila(f, asientos.get(f["id"], []))
                for f in filas]

    def detalle_venta(self, folio):
        """Una venta enriquecida o None."""
        fila = self.conn.execute(
            self._SELECT_VENTA + " WHERE v.folio = ?", (folio,)).fetchone()
        if not fila:
            return None
        asientos = self._asientos_por_venta([fila["id"]]).get(fila["id"], [])
        return self._detalle_desde_fila(fila, asientos)

    # ------------------------------------------------------------------ #
    #                           Reportes                                 #
    # ------------------------------------------------------------------ #
    def _rango_dia(self, valor):
        try:
            inicio = datetime.strptime(valor, "%Y-%m-%d")
        except ValueError:
            raise ErrorNegocio("La fecha debe tener formato AAAA-MM-DD.") \
                from None
        fin = inicio + timedelta(days=1)
        return (inicio.strftime("%Y-%m-%d 00:00:00"),
                fin.strftime("%Y-%m-%d 00:00:00"))

    def _rango_mes(self, valor):
        try:
            inicio = datetime.strptime(valor + "-01", "%Y-%m-%d")
        except ValueError:
            raise ErrorNegocio("El mes debe tener formato AAAA-MM.") from None
        if inicio.month == 12:
            fin = inicio.replace(year=inicio.year + 1, month=1)
        else:
            fin = inicio.replace(month=inicio.month + 1)
        return (inicio.strftime("%Y-%m-%d 00:00:00"),
                fin.strftime("%Y-%m-%d 00:00:00"))

    def ventas_reporte(self, ambito, valor=None):
        """Agrega ventas activas según ámbito.

        ambito: 'general' | 'pelicula' | 'dia' | 'mes'
        valor: pelicula_id, 'AAAA-MM-DD' o 'AAAA-MM' según el ámbito.
        Devuelve dict con titulo, filas y totales.
        """
        donde = ["e.nombre = ?"]
        params = ["activa"]
        titulo = "Reporte general de ventas"

        if ambito == "pelicula":
            peli = self.obtener_pelicula(valor)
            if peli is None:
                raise ErrorNegocio("Película no encontrada.")
            donde.append("p.id = ?")
            params.append(valor)
            titulo = f"Ventas por película: {peli.titulo}"
        elif ambito == "dia":
            inicio, fin = self._rango_dia(valor)
            donde.append("v.fecha_hora >= ? AND v.fecha_hora < ?")
            params.extend([inicio, fin])
            titulo = f"Ventas del día {valor}"
        elif ambito == "mes":
            inicio, fin = self._rango_mes(valor)
            donde.append("v.fecha_hora >= ? AND v.fecha_hora < ?")
            params.extend([inicio, fin])
            titulo = f"Ventas del mes {valor}"
        elif ambito != "general":
            raise ErrorNegocio("Ámbito de reporte no válido.")

        sql = (self._SELECT_VENTA + " WHERE " + " AND ".join(donde)
               + " ORDER BY v.fecha_hora")
        filas = self.conn.execute(sql, params).fetchall()
        asientos = self._asientos_por_venta([f["id"] for f in filas])
        detalladas = [self._detalle_desde_fila(f, asientos.get(f["id"], []))
                      for f in filas]
        total_ingresos = round(sum(f["total"] for f in detalladas), 2)
        total_boletos = sum(f["cantidad_boletos"] for f in detalladas)
        promedio = (round(total_ingresos / len(detalladas), 2)
                    if detalladas else 0.0)
        return {
            "titulo": titulo,
            "ambito": ambito,
            "valor": valor,
            "filas": detalladas,
            "total_ingresos": total_ingresos,
            "total_boletos": total_boletos,
            "num_ventas": len(detalladas),
            "promedio_venta": promedio,
        }


def sembrar_demo(servicio):
    """Carga catálogo inicial (sin solapamientos en cada sala)."""
    if servicio.listar_peliculas(solo_activas=False):
        return
    pelis = [
        ("Dune: Parte 3", "Ciencia ficción", 168, "B15", 89.00),
        ("La Nemesia Carmesí", "Suspenso", 131, "C", 75.50),
        ("Aventuras en Neón City", "Animación", 96, "A", 65.00),
        ("El Reino Helado", "Fantasía", 114, "B", 79.90),
        ("Medianoche Dorada", "Comedia romántica", 102, "B", 69.50),
    ]
    ids = [servicio.crear_pelicula(*d).id for d in pelis]
    sala1 = ["13:00", "16:00", "18:30", "20:30", "22:30"]
    sala2 = ["10:00", "13:00", "15:30", "17:30", "19:45"]
    for idx in range(len(ids)):
        servicio.crear_funcion(ids[idx], "Sala 1", sala1[idx], 60)
        servicio.crear_funcion(ids[idx], "Sala 2", sala2[idx], 48)
