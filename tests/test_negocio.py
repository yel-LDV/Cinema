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


class TestComprar:
    def test_compra_ok_actualiza_disponibilidad(self, servicio, escenario):
        _, funcion = escenario
        venta = servicio.comprar_boletos(funcion.id, cliente(), 2)
        assert venta.folio == "V00001"
        assert venta.total == 200.00
        assert servicio.lugares_disponibles(funcion.id) == 3

    def test_total_con_descuento_50(self, servicio, escenario_todos):
        _, funcion = escenario_todos
        venta = servicio.comprar_boletos(
            funcion.id, Cliente("Nia", 10), 3)
        assert venta.descuento_pct == 0.50
        assert venta.total == 150.00  # 3 * 100 * 0.5

    def test_total_con_descuento_adulto(self, servicio, escenario):
        _, funcion = escenario
        venta = servicio.comprar_boletos(funcion.id, cliente(), 2)
        assert venta.descuento_pct == 0.00
        assert venta.total == 200.00

    def test_rechaza_exceso_disponibilidad(self, servicio, escenario):
        _, funcion = escenario
        servicio.comprar_boletos(funcion.id, cliente(), 4)
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente(), 2)

    def test_rechaza_cantidad_invalida(self, servicio, escenario):
        _, funcion = escenario
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente(), 0)
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente(), -3)

    def test_rechaza_clasificacion(self, servicio, escenario):
        _, funcion = escenario
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente("Niño", 12), 1)

    def test_rechaza_funcion_de_pelicula_dada_de_baja(
            self, servicio, escenario):
        pelicula, funcion = escenario
        servicio.dar_de_baja_pelicula(pelicula.id)
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, cliente(), 1)

    def test_folio_unico_secuencial(self, servicio, escenario):
        _, funcion = escenario
        folios = [servicio.comprar_boletos(funcion.id, cliente(), 1).folio
                  for _ in range(3)]
        assert folios == ["V00001", "V00002", "V00003"]

    def test_nombre_vacio_rechazado(self, servicio, escenario):
        _, funcion = escenario
        with pytest.raises(ErrorNegocio):
            servicio.comprar_boletos(funcion.id, Cliente("   ", 20), 1)


class TestCancelar:
    def test_cancelar_libera_lugares(self, servicio, escenario):
        _, funcion = escenario
        venta = servicio.comprar_boletos(funcion.id, cliente(), 3)
        assert servicio.lugares_disponibles(funcion.id) == 2
        venta_cancelada = servicio.cancelar_compra(venta.folio)
        assert venta_cancelada.estado == "cancelada"
        assert servicio.lugares_disponibles(funcion.id) == 5

    def test_doble_cancelacion_rechazada(self, servicio, escenario):
        _, funcion = escenario
        venta = servicio.comprar_boletos(funcion.id, cliente(), 1)
        servicio.cancelar_compra(venta.folio)
        with pytest.raises(ErrorNegocio):
            servicio.cancelar_compra(venta.folio)

    def test_folio_inexistente(self, servicio):
        with pytest.raises(ErrorNegocio):
            servicio.cancelar_compra("V99999")


class TestReportes:
    def test_reporte_general_suma_totales(self, servicio, escenario_todos):
        _, funcion = escenario_todos
        servicio.comprar_boletos(funcion.id, Cliente("Nia", 10), 2)   # 100
        servicio.comprar_boletos(funcion.id, cliente(), 1)            # 100
        reporte = servicio.ventas_reporte("general")
        assert reporte["num_ventas"] == 2
        assert reporte["total_boletos"] == 3
        assert reporte["total_ingresos"] == 200.00

    def test_reporte_excluye_canceladas(self, servicio, escenario):
        pelicula, funcion = escenario
        venta = servicio.comprar_boletos(funcion.id, cliente(), 2)
        servicio.cancelar_compra(venta.folio)
        reporte = servicio.ventas_reporte("general")
        assert reporte["total_ingresos"] == 0.0

    def test_reporte_por_pelicula(self, servicio, escenario):
        pelicula, funcion = escenario
        servicio.comprar_boletos(funcion.id, cliente(), 2)
        reporte = servicio.ventas_reporte("pelicula", pelicula.id)
        assert reporte["total_ingresos"] == 200.00
        assert pelicula.titulo in reporte["titulo"]

    def test_reporte_por_dia(self, servicio, escenario):
        from datetime import datetime
        _, funcion = escenario
        servicio.comprar_boletos(funcion.id, cliente(), 2)
        hoy = datetime.now().strftime("%Y-%m-%d")
        reporte = servicio.ventas_reporte("dia", hoy)
        assert reporte["total_boletos"] == 2

    def test_reporte_por_mes(self, servicio, escenario):
        from datetime import datetime
        _, funcion = escenario
        servicio.comprar_boletos(funcion.id, cliente(), 2)
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