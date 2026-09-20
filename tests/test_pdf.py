import os

from backend.models import CineService, Cliente
from backend.pdf_generator import ReporteVentasPDF, TicketPDF


def _escenario(tmp_path):
    servicio = CineService(str(tmp_path / "cine_test.db"))
    pelicula = servicio.crear_pelicula(
        "Prueba Óptica", "Acción", 120, "A", 89.50)
    funcion = servicio.crear_funcion(pelicula.id, "Sala 1", "20:00", 60)
    return servicio, pelicula, funcion


def test_ticket_pdf_se_genera(tmp_path):
    servicio, _, funcion = _escenario(tmp_path)
    venta = servicio.comprar_boletos(funcion.id, Cliente("Ana", 20), 2)
    detalle = servicio.detalle_venta(venta.folio)
    ruta = TicketPDF().generar(detalle, salida_dir=str(tmp_path / "tickets"))
    assert os.path.isfile(ruta)
    assert os.path.getsize(ruta) > 0
    assert os.path.basename(ruta) == f"ticket_{venta.folio}.pdf"


def test_reporte_pdf_se_genera(tmp_path):
    servicio, _, funcion = _escenario(tmp_path)
    servicio.comprar_boletos(funcion.id, Cliente("Ana", 20), 3)
    servicio.comprar_boletos(funcion.id, Cliente("Nia", 10), 2)
    reporte = servicio.ventas_reporte("general")
    ruta = ReporteVentasPDF().generar(reporte, salida_dir=str(tmp_path / "rep"))
    assert os.path.isfile(ruta)
    assert os.path.getsize(ruta) > 0


def test_reporte_vacio_se_genera(tmp_path):
    servicio, _, _ = _escenario(tmp_path)
    reporte = servicio.ventas_reporte("general")
    ruta = ReporteVentasPDF().generar(reporte, salida_dir=str(tmp_path / "rep"))
    assert os.path.isfile(ruta)
    assert os.path.getsize(ruta) > 0