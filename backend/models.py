"""Clases de dominio y servicio central (reglas de negocio) del cine."""

from datetime import datetime

from backend.database import RUTA_DB, inicializar_db

# Rango de descuentos por edad (configurable):
#   hasta el límite i de la tupla → porcentaje. Orden irreversible.
REGLAS_DESCUENTO = [
    (12, 0.50),   # 0-12  → 50%
    (17, 0.20),   # 13-17 → 20%
    (59, 0.00),   # 18-59 → 0%
    (200, 0.30),  # 60+   → 30%
]

# Edad mínima permitida por clasificación. Clasificación desconocida → 0.
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


class Pelicula:
    def __init__(self, id, titulo, genero, duracion_min, clasificacion,
                 precio_base, activa=True):
        self.id = id
        self.titulo = titulo
        self.genero = genero
        self.duracion_min = duracion_min
        self.clasificacion = clasificacion
        self.precio_base = precio_base
        self.activa = bool(activa)

    @classmethod
    def desde_fila(cls, fila):
        return cls(fila["id"], fila["titulo"], fila["genero"],
                   fila["duracion_min"], fila["clasificacion"],
                   fila["precio_base"], fila["activa"])

    def __repr__(self):
        return f"<Pelicula {self.id} {self.titulo!r}>"


class Funcion:
    def __init__(self, id, pelicula_id, sala, horario, capacidad, ocupados=0):
        self.id = id
        self.pelicula_id = pelicula_id
        self.sala = sala
        self.horario = horario
        self.capacidad = capacidad
        self.ocupados = ocupados

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
        self.precio_unitario = precio_unitario
        self.descuento_pct = descuento_pct
        self.total = total
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
    """Fachada única: toda la lógica de negocio sobre SQLite.

    Las GUIs (usuario y admin) solo conversan con esta clase.
    """

    def __init__(self, ruta_db=None):
        self.ruta_db = ruta_db or RUTA_DB
        self.conn = inicializar_db(self.ruta_db)

    # ------------------------------------------------------------------ #
    #                           Películas                                #
    # ------------------------------------------------------------------ #
    def crear_pelicula(self, titulo, genero, duracion_min, clasificacion,
                       precio_base):
        if not titulo.strip():
            raise ErrorNegocio("El título no puede estar vacío.")
        if not genero.strip():
            raise ErrorNegocio("El género no puede estar vacío.")
        if duracion_min <= 0:
            raise ErrorNegocio("La duración debe ser mayor a cero.")
        if precio_base < 0:
            raise ErrorNegocio("El precio no puede ser negativo.")
        if clasificacion not in CLASIFICACION_EDAD:
            raise ErrorNegocio(
                f"Clasificación desconocida: {clasificacion}.")
        cur = self.conn.execute(
            "INSERT INTO peliculas (titulo, genero, duracion_min, "
            "clasificacion, precio_base, activa) VALUES (?, ?, ?, ?, ?, 1)",
            (titulo.strip(), genero.strip(), duracion_min, clasificacion,
             precio_base))
        self.conn.commit()
        return self.obtener_pelicula(cur.lastrowid)

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
            "SELECT * FROM peliculas WHERE id = ?", (pelicula_id,)).fetchone()
        return Pelicula.desde_fila(fila) if fila else None

    def listar_peliculas(self, solo_activas=True):
        if solo_activas:
            filas = self.conn.execute(
                "SELECT * FROM peliculas WHERE activa = 1 "
                "ORDER BY titulo").fetchall()
        else:
            filas = self.conn.execute(
                "SELECT * FROM peliculas ORDER BY titulo").fetchall()
        return [Pelicula.desde_fila(f) for f in filas]

    # ------------------------------------------------------------------ #
    #                           Funciones                                #
    # ------------------------------------------------------------------ #
    def crear_funcion(self, pelicula_id, sala, horario, capacidad):
        if self.obtener_pelicula(pelicula_id) is None:
            raise ErrorNegocio("La película no existe.")
        if not sala.strip():
            raise ErrorNegocio("La sala no puede estar vacía.")
        if not horario.strip():
            raise ErrorNegocio("El horario no puede estar vacío.")
        if capacidad <= 0:
            raise ErrorNegocio("La capacidad debe ser mayor a cero.")
        cur = self.conn.execute(
            "INSERT INTO funciones (pelicula_id, sala, horario, capacidad, "
            "ocupados) VALUES (?, ?, ?, ?, 0)",
            (pelicula_id, sala.strip(), horario.strip(), capacidad))
        self.conn.commit()
        return self.obtener_funcion(cur.lastrowid)

    def obtener_funcion(self, funcion_id):
        fila = self.conn.execute(
            "SELECT * FROM funciones WHERE id = ?", (funcion_id,)).fetchone()
        return Funcion.desde_fila(fila) if fila else None

    def listar_funciones(self, pelicula_id=None, solo_pelicula_activa=True):
        sql = "SELECT f.* FROM funciones f"
        if solo_pelicula_activa:
            sql += " JOIN peliculas p ON p.id = f.pelicula_id AND p.activa = 1"
        params = []
        if pelicula_id is not None:
            sql += " WHERE f.pelicula_id = ?"
            params.append(pelicula_id)
        sql += " ORDER BY f.horario"
        return [Funcion.desde_fila(f)
                for f in self.conn.execute(sql, params).fetchall()]

    def lugares_disponibles(self, funcion_id):
        funcion = self.obtener_funcion(funcion_id)
        if funcion is None:
            raise ErrorNegocio("Función no encontrada.")
        return funcion.disponibles

    # ------------------------------------------------------------------ #
    #                           Compras                                  #
    # ------------------------------------------------------------------ #
    def comprar_boletos(self, funcion_id, cliente, cantidad):
        """Registra la venta y actualiza los lugares ocupados, atómicamente."""
        if cantidad <= 0:
            raise ErrorNegocio("La cantidad de boletos debe ser mayor a cero.")
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
        # Re-leer la función dentro de la transacción para ver la disponibilidad
        with self.conn:
            fresca = self.conn.execute(
                "SELECT * FROM funciones WHERE id = ?",
                (funcion_id,)).fetchone()
            funcion = Funcion.desde_fila(fresca)
            if cantidad > funcion.disponibles:
                raise ErrorNegocio(
                    f"Solo hay {funcion.disponibles} lugares disponibles; "
                    f"solicitó {cantidad}.")

            descuento = cliente.calcular_descuento()
            precio_unitario = pelicula.precio_base
            total = round(cantidad * precio_unitario * (1 - descuento), 2)
            folio = self._generar_folio()
            cur = self.conn.execute(
                "INSERT INTO ventas (folio, funcion_id, cliente_nombre, edad, "
                "cantidad_boletos, precio_unitario, descuento_pct, total, "
                "fecha_hora, estado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, "
                "'activa')",
                (folio, funcion_id, cliente.nombre, cliente.edad, cantidad,
                 precio_unitario, descuento, total,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self.conn.execute(
                "UPDATE funciones SET ocupados = ocupados + ? WHERE id = ?",
                (cantidad, funcion_id))
        return self.obtener_venta_por_id(cur.lastrowid)

    def _generar_folio(self):
        fila = self.conn.execute(
            "SELECT COUNT(*) AS n FROM ventas").fetchone()
        return f"V{fila['n'] + 1:05d}"

    def cancelar_compra(self, folio):
        """Cancela la venta (solo una vez) y libera los lugares ocupados."""
        folio = folio.strip()
        venta = self.obtener_venta_por_folio(folio)
        if venta is None:
            raise ErrorNegocio("No existe una venta con ese folio.")
        if venta.estado == "cancelada":
            raise ErrorNegocio("La venta ya está cancelada.")
        with self.conn:
            self.conn.execute(
                "UPDATE ventas SET estado = 'cancelada' WHERE id = ?",
                (venta.id,))
            self.conn.execute(
                "UPDATE funciones SET ocupados = MAX(0, ocupados - ?) "
                "WHERE id = ?", (venta.cantidad_boletos, venta.funcion_id))
        return self.obtener_venta_por_folio(folio)

    # ------------------------------------------------------------------ #
    #                           Ventas                                   #
    # ------------------------------------------------------------------ #
    def obtener_venta_por_id(self, venta_id):
        fila = self.conn.execute(
            "SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
        return Venta.desde_fila(fila) if fila else None

    def obtener_venta_por_folio(self, folio):
        fila = self.conn.execute(
            "SELECT * FROM ventas WHERE folio = ?", (folio,)).fetchone()
        return Venta.desde_fila(fila) if fila else None

    def ventas_detalladas(self, estado=None):
        """Ventas enriquecidas con película, sala y horario."""
        sql = ("SELECT v.*, f.sala, f.horario, p.titulo AS pelicula_titulo, "
               "p.clasificacion "
               "FROM ventas v "
               "JOIN funciones f ON f.id = v.funcion_id "
               "JOIN peliculas p ON p.id = f.pelicula_id")
        params = []
        if estado:
            sql += " WHERE v.estado = ?"
            params.append(estado)
        sql += " ORDER BY v.fecha_hora DESC, v.id DESC"
        return [dict(fila)
                for fila in self.conn.execute(sql, params).fetchall()]

    def detalle_venta(self, folio):
        """Una venta enriquecida o None."""
        fila = self.conn.execute(
            "SELECT v.*, f.sala, f.horario, p.titulo AS pelicula_titulo, "
            "p.clasificacion "
            "FROM ventas v "
            "JOIN funciones f ON f.id = v.funcion_id "
            "JOIN peliculas p ON p.id = f.pelicula_id "
            "WHERE v.folio = ?", (folio,)).fetchone()
        return dict(fila) if fila else None

    # ------------------------------------------------------------------ #
    #                           Reportes                                 #
    # ------------------------------------------------------------------ #
    def ventas_reporte(self, ambito, valor=None):
        """Agrega ventas activas según ámbito.

        ambito: 'general' | 'pelicula' | 'dia' | 'mes'
        valor: pelicula_id, 'AAAA-MM-DD' o 'AAAA-MM' según el ámbito.
        Devuelve dict con titulo, filas y totales.
        """
        donde = ["v.estado = 'activa'"]
        params = []
        titulo = "Reporte general de ventas"

        if ambito == "pelicula":
            peli = self.obtener_pelicula(valor)
            if peli is None:
                raise ErrorNegocio("Película no encontrada.")
            donde.append("p.id = ?")
            params.append(valor)
            titulo = f"Ventas por película: {peli.titulo}"
        elif ambito == "dia":
            donde.append("date(v.fecha_hora) = ?")
            params.append(valor)
            titulo = f"Ventas del día {valor}"
        elif ambito == "mes":
            donde.append("strftime('%Y-%m', v.fecha_hora) = ?")
            params.append(valor)
            titulo = f"Ventas del mes {valor}"
        elif ambito != "general":
            raise ErrorNegocio("Ámbito de reporte no válido.")

        sql = ("SELECT v.*, f.sala, f.horario, "
               "p.titulo AS pelicula_titulo, p.clasificacion "
               "FROM ventas v "
               "JOIN funciones f ON f.id = v.funcion_id "
               "JOIN peliculas p ON p.id = f.pelicula_id "
               "WHERE " + " AND ".join(donde) + " "
               "ORDER BY v.fecha_hora")
        filas = [dict(fila)
                 for fila in self.conn.execute(sql, params).fetchall()]
        total_ingresos = round(sum(f["total"] for f in filas), 2)
        total_boletos = sum(f["cantidad_boletos"] for f in filas)
        promedio = (round(total_ingresos / len(filas), 2)
                    if filas else 0.0)
        return {
            "titulo": titulo,
            "ambito": ambito,
            "valor": valor,
            "filas": filas,
            "total_ingresos": total_ingresos,
            "total_boletos": total_boletos,
            "num_ventas": len(filas),
            "promedio_venta": promedio,
        }


def sembrar_demo(servicio):
    """Carga catálogo inicial si la base está vacía."""
    if servicio.listar_peliculas(solo_activas=False):
        return
    pelis = [
        ("Dune: Parte 3", "Ciencia ficción", 168, "B15", 89.00),
        ("La Nemesia Carmesí", "Suspenso", 131, "C", 75.50),
        ("Aventuras en Neón City", "Animación", 96, "A", 65.00),
        ("El Reino Helado", "Fantasía", 114, "B", 79.90),
        ("Medianoche Dorada", "Comedia romántica", 102, "B", 69.50),
    ]
    ids = []
    for t, g, d, c, p in pelis:
        ids.append(servicio.crear_pelicula(t, g, d, c, p).id)
    for idx in range(len(ids)):
        servicio.crear_funcion(ids[idx], "Sala 1", f"{(13 + idx):02d}:00", 60)
        servicio.crear_funcion(ids[idx], "Sala 2", f"{(18 + idx):02d}:30", 48)