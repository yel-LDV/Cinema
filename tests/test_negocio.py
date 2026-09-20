import pytest

from backend.models import Cliente, CineService, ErrorNegocio


@pytest.fixture()
def servicio(tmp_path):
    return CineService(str(tmp_path / "cine_test.db"))


@pytest.fixture()
def escenario(servicio):
    """Crea una función con capacidad 5 para una película B15 a $100."""
    pelicula = servicio.crear_pelicula(
        "Prueba", "Acción", 120, "B15", 100.00)
    funcion = servicio.crear_funcion(pelicula.id, "Sala 1", "20:00", 5)
    return pelicula, funcion


@pytest.fixture()
def escenario_todos(servicio):
    """Función con capacidad 5 para una película 'A' a $100 (sin restricción)."""
    pelicula = servicio.crear_pelicula(
        "Para Todos", "Familiar", 95, "A", 100.00)
    funcion = servicio.crear_funcion(pelicula.id, "Sala 1", "20:00", 5)
    return pelicula, funcion


def cliente(nombre="Ana", edad=30):
    return Cliente(nombre, edad)


def posiciones(servicio, funcion_id, n):
    return servicio.posiciones_libres(funcion_id, n)


class TestDescuento:
    @pytest.mark.parametrize("edad,esperado", [
        (0, 0.50), (12, 0.50),   # rango 0-12
        (13, 0.20), (17, 0.20),  # rango 13-17
        (18, 0.00), (59, 0.00),  # rango adulto
        (60, 0.30), (99, 0.30),  # 60+
    ])
    def test_límites(self, edad, esperado):
        assert Cliente("X", edad).calcular_descuento() == esperado

    def test_tabla_configurable(self):
        reglas = [(10, 0.50)]
        assert Cliente("X", 5).calcular_descuento(reglas) == 0.50
        assert Cliente("X", 11).calcular_descuento(reglas) == 0.0


class TestClasificacion:
    @pytest.mark.parametrize("clasificacion,edad,permitida", [
        ("B15", 14, False),
        ("B15", 15, True),
        ("C", 17, False),
        ("C", 18, True),
        ("A", 3, True),
        ("R", 18, True),
        ("Desconocida", 5, True),
    ])
    def test_edad_minima(self, clasificacion, edad, permitida):
        assert Cliente("X", edad).validar_clasificacion(clasificacion) \
            == permitida


class TestAsientos:
    def test_funcion_genera_asientos_en_filas(self, servicio, escenario):
        _, funcion = escenario
        asientos = servicio.listar_asientos(funcion.id)
        assert len(asientos) == 5
        assert asientos[0]["posicion"] == "A-1"
        assert asientos[4]["posicion"] == "A-5"
        assert all(a["estado"] == "libre" for a in asientos)

    def test_disposicion_multi_fila(self, servicio):
        peli = servicio.crear_pelicula("L", "Drama", 90, "B", 50)
        f = servicio.crear_funcion(peli.id, "Sala 1", "10:00", 20)
        asientos = servicio.listar_asientos(f.id)
        assert len(asientos) == 20
        assert asientos[0]["fila"] == "A" and asientos[0]["numero"] == 1
        assert asientos[9]["fila"] == "B" and asientos[10]["fila"] == "B"
        assert asientos[19]["fila"] == "C" and asientos[19]["numero"] == 4

    def test_migracion_crea_asientos_faltantes(self, tmp_path):
        servicio = CineService(str(tmp_path / "m.db"))
        peli = servicio.crear_pelicula("M", "Drama", 90, "B", 50)
        with servicio.conn:  # función vieja creada directamente sin asientos
            cur = servicio.conn.execute(
                "INSERT INTO funciones (pelicula_id, sala, horario, "
                "capacidad, ocupados) VALUES (?, ?, ?, ?, 0)",
                (peli.id, "Sala 9", "09:00", 40))
            funcion_id = cur.lastrowid
        nuevo = CineService(str(tmp_path / "m.db"))
        assert len(nuevo.listar_asientos(funcion_id)) == 40

    def test_bd_legada_sin_asientos_se_reinicia(self, tmp_path):
        import sqlite3
        ruta = str(tmp_path / "legacy.db")
        conn = sqlite3.connect(ruta)
        conn.executescript(
            "CREATE TABLE peliculas (id INTEGER PRIMARY KEY, titulo TEXT);"
            "INSERT INTO peliculas (id, titulo) VALUES (1, 'Vieja');")
        conn.commit()
        conn.close()
        servicio = CineService(ruta)
        assert servicio.listar_peliculas(solo_activas=False) == []
        tabla = servicio.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name = 'asientos'").fetchone()
        assert tabla[0] == "asientos"


class TestComprar:
    def test_compra_ok_actualiza_disponibilidad(self, servicio, escenario):
        _, funcion = escenario
        venta = servicio.comprar_boletos(
            funcion.id, cliente(), posiciones(servicio, funcion.id, 2))
        assert venta.folio == "V00001"
        assert venta.cantidad_boletos == 2
        assert venta.total == 200.00
        assert servicio.lugares_disponibles(funcion.id) == 3

    def test_total_con_descuento_50(self, servicio, escenario_todos):
        _, funcion = escenario_todos
        venta = servicio.comprar_boletos(
            funcion.id, Cliente("Nia", 10),
            posiciones(servicio, funcion.id, 3))
        assert venta.descuento_pct == 0.50
        assert venta.total == 150.00  # 3 * 100 * 0.5

    def test_total_con_descuento_adulto(self, servicio, escenario):
        _, funcion = escenario
        venta = servicio.comprar_boletos(
            funcion.id, cliente(), posiciones(servicio, funcion.id, 2))
        assert venta.descuento_pct == 0.00
        assert venta.total == 200.00

    def test_asientos_se_marcan_ocupados(self, servicio, escenario):
        _, funcion = escenario
        comprados = posiciones(servicio, funcion.id, 2)
        servicio.comprar_boletos(funcion.id, cliente(), comprados)
        estados = {a["posicion"]: a["estado"]
                   for a in servicio.listar_asientos(funcion.id)}
        assert estados[comprados[0]] == "ocupado"
        restantes = [p for p in estados
                     if p not in comprados]
        for p in restantes:
            assert estados[p] == "libre"

    def test_no_vende_asiento_ya_ocupado_tras_llenar(self, servicio,
                                                     escenario):
        _, funcion = escenario
        servicios = servicio.posiciones_libres(funcion.id, 5)
        servicio.comprar_boletos(funcion.id, cliente(), servicios[:4])
        # queda 1 libre; pedir uno vendido y el libre → rechazado
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente(),
                                     [servicios[3], servicios[4]])

    def test_rechaza_pedir_sin_asientos(self, servicio, escenario):
        _, funcion = escenario
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente(), [])

    def test_rechaza_asiento_repetido(self, servicio, escenario):
        _, funcion = escenario
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente(),
                                     ["A-1", "A-1"])

    def test_rechaza_asiento_inexistente(self, servicio, escenario):
        _, funcion = escenario
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente(), ["Z-99"])

    def test_no_vende_dos_veces_el_mismo_asiento(self, servicio, escenario):
        _, funcion = escenario
        servicio.comprar_boletos(funcion.id, cliente(), ["A-1"])
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente(), ["A-1"])

    def test_rechaza_clasificacion(self, servicio, escenario):
        _, funcion = escenario
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente("Niño", 12),
                                     ["A-1"])

    def test_rechaza_funcion_de_pelicula_dada_de_baja(
            self, servicio, escenario):
        pelicula, funcion = escenario
        servicio.dar_de_baja_pelicula(pelicula.id)
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente(), ["A-1"])

    def test_folio_unico_secuencial(self, servicio, escenario):
        _, funcion = escenario
        folios = [servicio.comprar_boletos(
            funcion.id, cliente(),
            posiciones(servicio, funcion.id, 1)).folio for _ in range(3)]
        assert folios == ["V00001", "V00002", "V00003"]

    def test_nombre_vacio_rechazado(self, servicio, escenario):
        _, funcion = escenario
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, Cliente("   ", 20),
                                     ["A-1"])


class TestCancelar:
    def test_cancelar_libera_asientos(self, servicio, escenario):
        _, funcion = escenario
        comprados = posiciones(servicio, funcion.id, 3)
        venta = servicio.comprar_boletos(funcion.id, cliente(), comprados)
        assert servicio.lugares_disponibles(funcion.id) == 2
        venta_cancelada = servicio.cancelar_compra(venta.folio)
        assert venta_cancelada.estado == "cancelada"
        assert servicio.lugares_disponibles(funcion.id) == 5
        estado = {a["posicion"]: a["estado"]
                  for a in servicio.listar_asientos(funcion.id)}
        assert all(estado[p] == "libre" for p in comprados)

    def test_asiento_libre_tras_cancelar_se_puede_revender(
            self, servicio, escenario):
        _, funcion = escenario
        comprados = posiciones(servicio, funcion.id, 1)
        venta = servicio.comprar_boletos(funcion.id, cliente(), comprados)
        servicio.cancelar_compra(venta.folio)
        venta2 = servicio.comprar_boletos(funcion.id, cliente(), comprados)
        assert venta2.cantidad_boletos == 1

    def test_doble_cancelacion_rechazada(self, servicio, escenario):
        _, funcion = escenario
        venta = servicio.comprar_boletos(
            funcion.id, cliente(), posiciones(servicio, funcion.id, 1))
        servicio.cancelar_compra(venta.folio)
        with pytest.raises(ErrorNegocio):
            servicio.cancelar_compra(venta.folio)

    def test_folio_inexistente(self, servicio):
        with pytest.raises(ErrorNegocio):
            servicio.cancelar_compra("V99999")


class TestHorarios:
    def test_no_solapa_misma_sala_mismo_horario(self, servicio):
        p1 = servicio.crear_pelicula("A1", "Drama", 90, "B", 50)
        p2 = servicio.crear_pelicula("A2", "Drama", 90, "B", 50)
        servicio.crear_funcion(p1.id, "Sala 1", "10:00", 30)
        with pytest.raises(ErrorNegocio):
            servicio.crear_funcion(p2.id, "Sala 1", "10:00", 30)

    def test_solapamiento_parcial_rechazado(self, servicio):
        p1 = servicio.crear_pelicula("Larga", "Drama", 120, "B", 50)
        p2 = servicio.crear_pelicula("Corta", "Drama", 60, "B", 50)
        servicio.crear_funcion(p1.id, "Sala 1", "10:00", 30)  # 10:00→12:00
        with pytest.raises(ErrorNegocio):
            servicio.crear_funcion(p2.id, "Sala 1", "11:00", 30)

    def test_funcion_contigua_permitida(self, servicio):
        p1 = servicio.crear_pelicula("Uno", "Drama", 120, "B", 50)
        p2 = servicio.crear_pelicula("Dos", "Drama", 90, "B", 50)
        servicio.crear_funcion(p1.id, "Sala 1", "10:00", 30)   # fin 12:00
        f = servicio.crear_funcion(p2.id, "Sala 1", "12:00", 30)
        assert f.horario == "12:00"

    def test_salas_distintas_simultaneas_permitidas(self, servicio):
        p1 = servicio.crear_pelicula("X", "Drama", 90, "B", 50)
        p2 = servicio.crear_pelicula("Y", "Drama", 90, "B", 50)
        servicio.crear_funcion(p1.id, "Sala 1", "18:00", 30)
        f = servicio.crear_funcion(p2.id, "Sala 2", "18:00", 30)
        assert f.id > 0

    def test_horario_formato_invalido(self, servicio):
        peli = servicio.crear_pelicula("H", "Drama", 90, "B", 50)
        with pytest.raises(ErrorNegocio):
            servicio.crear_funcion(peli.id, "Sala 1", "19:bc", 30)
        with pytest.raises(ErrorNegocio):
            servicio.crear_funcion(peli.id, "Sala 1", "25:00", 30)

    def test_misma_sala_distinto_rango_permitida(self, servicio):
        p1 = servicio.crear_pelicula("I1", "Drama", 60, "B", 50)
        p2 = servicio.crear_pelicula("I2", "Drama", 60, "B", 50)
        servicio.crear_funcion(p1.id, "Sala 1", "10:00", 30)  # 10:00→11:00
        f = servicio.crear_funcion(p2.id, "Sala 1", "16:00", 30)
        assert f.id > 0


class TestEditarPelicula:
    def test_editar_cambia_datos(self, servicio):
        peli = servicio.crear_pelicula("Viejo", "Drama", 90, "B", 50)
        editado = servicio.editar_pelicula(peli.id, "Nuevo", "Comedia",
                                           100, "B15", 70)
        assert editado.titulo == "Nuevo"
        assert editado.genero == "Comedia"
        assert editado.duracion_min == 100
        assert editado.precio_base == 70

    def test_editar_duracion_que_solapa_rechazada(self, servicio):
        p1 = servicio.crear_pelicula("Conviviente", "Drama", 60, "B", 50)
        p2 = servicio.crear_pelicula("Editable", "Drama", 120, "B", 50)
        servicio.crear_funcion(p1.id, "Sala 1", "13:00", 30)   # 13:00→14:00
        servicio.crear_funcion(p2.id, "Sala 1", "10:00", 30)   # 10:00→12:00
        # ampliar p2 a 240 min → invade el horario de la otra función
        with pytest.raises(ErrorNegocio):
            servicio.editar_pelicula(p2.id, "Editable", "Drama",
                                     240, "B", 50)
        # sin conflicto, la edición procede (la fallida se revirtió)
        editado = servicio.editar_pelicula(p2.id, "Editable Final", "Drama",
                                           110, "B", 55)
        assert editado.duracion_min == 110
        assert editado.precio_base == 55

    def test_editar_pelicula_inexistente(self, servicio):
        with pytest.raises(ErrorNegocio):
            servicio.editar_pelicula(999, "X", "Drama", 90, "B", 50)


class TestReportes:
    def test_reporte_general_suma_totales(self, servicio, escenario_todos):
        _, funcion = escenario_todos
        servicio.comprar_boletos(funcion.id, Cliente("Nia", 10),
                                 posiciones(servicio, funcion.id, 2))  # 100
        servicio.comprar_boletos(funcion.id, cliente(),
                                 posiciones(servicio, funcion.id, 1))  # 100
        reporte = servicio.ventas_reporte("general")
        assert reporte["num_ventas"] == 2
        assert reporte["total_boletos"] == 3
        assert reporte["total_ingresos"] == 200.00

    def test_reporte_incluye_asientos(self, servicio, escenario):
        _, funcion = escenario
        comprados = posiciones(servicio, funcion.id, 2)
        servicio.comprar_boletos(funcion.id, cliente(), comprados)
        reporte = servicio.ventas_reporte("general")
        assert reporte["filas"][0]["asientos"] == ", ".join(comprados)

    def test_reporte_excluye_canceladas(self, servicio, escenario):
        _, funcion = escenario
        venta = servicio.comprar_boletos(
            funcion.id, cliente(), posiciones(servicio, funcion.id, 2))
        servicio.cancelar_compra(venta.folio)
        reporte = servicio.ventas_reporte("general")
        assert reporte["total_ingresos"] == 0.0

    def test_reporte_por_pelicula(self, servicio, escenario):
        pelicula, funcion = escenario
        servicio.comprar_boletos(funcion.id, cliente(),
                                 posiciones(servicio, funcion.id, 2))
        reporte = servicio.ventas_reporte("pelicula", pelicula.id)
        assert reporte["total_ingresos"] == 200.00
        assert pelicula.titulo in reporte["titulo"]

    def test_reporte_por_dia(self, servicio, escenario):
        from datetime import datetime
        _, funcion = escenario
        servicio.comprar_boletos(funcion.id, cliente(),
                                 posiciones(servicio, funcion.id, 2))
        hoy = datetime.now().strftime("%Y-%m-%d")
        reporte = servicio.ventas_reporte("dia", hoy)
        assert reporte["total_boletos"] == 2

    def test_reporte_por_mes(self, servicio, escenario):
        from datetime import datetime
        _, funcion = escenario
        servicio.comprar_boletos(funcion.id, cliente(),
                                 posiciones(servicio, funcion.id, 2))
        mes = datetime.now().strftime("%Y-%m")
        reporte = servicio.ventas_reporte("mes", mes)
        assert reporte["total_boletos"] == 2

    def test_reporte_ambito_invalido(self, servicio):
        with pytest.raises(ErrorNegocio):
            servicio.ventas_reporte("semana")


class TestCatalogos:
    def test_baja_pelicula_la_oculta_del_catalogo(self, servicio):
        pelicula = servicio.crear_pelicula("X", "Drama", 90, "B", 60)
        servicio.dar_de_baja_pelicula(pelicula.id)
        assert servicio.listar_peliculas() == []
        assert len(servicio.listar_peliculas(solo_activas=False)) == 1

    def test_validaciones_catalogo(self, servicio):
        with pytest.raises(ErrorNegocio):
            servicio.crear_pelicula("", "Drama", 90, "B", 60)
        with pytest.raises(ErrorNegocio):
            servicio.crear_pelicula("X", "Drama", 0, "B", 60)
        with pytest.raises(ErrorNegocio):
            servicio.crear_pelicula("X", "Drama", 90, "ZZ", 60)
        pelicula = servicio.crear_pelicula("X", "Drama", 90, "B", 60)
        with pytest.raises(ErrorNegocio):
            servicio.crear_funcion(pelicula.id, "Sala 1", "10:00", 0)