"""Pruebas de guardado/carga de carteles (backend.poster)."""

import os

import pytest
from PIL import Image

from backend import poster
from backend.models import ErrorNegocio


@pytest.fixture()
def imagen_png(tmp_path):
    ruta = str(tmp_path / "origen.png")
    Image.new("RGB", (120, 180), "purple").save(ruta)
    return ruta


@pytest.fixture()
def imagen_jpg(tmp_path):
    ruta = str(tmp_path / "origen.jpg")
    Image.new("RGB", (120, 180), "purple").save(ruta)
    return ruta


class TestGuardar:
    def test_guardar_devuelve_ruta_relativa_y_crea_archivo(self, imagen_png):
        ruta = poster.guardar_imagen(imagen_png, 7)
        assert ruta == "data/Carteles/cartel_7.png"
        assert os.path.isfile(poster.ruta_absoluta(ruta))
        with Image.open(poster.ruta_absoluta(ruta)) as img:
            assert img.format == "PNG"
            assert img.width <= poster.ANCHO_MAX

    def test_reemplazo_borra_versiones_previas(self, imagen_png, imagen_jpg):
        poster.guardar_imagen(imagen_jpg, 3)
        ruta = poster.guardar_imagen(imagen_png, 3)
        assert ruta == "data/Carteles/cartel_3.png"
        sobrantes = [n for n in os.listdir(poster.CARPETA_CARTELES)
                     if n.startswith("cartel_3.")]
        assert sobrantes == ["cartel_3.png"]

    def test_volcar_png_desde_bytes(self, imagen_png):
        datos = poster.preparar_origen(imagen_png)
        ruta = poster.volcar_png(datos, "cartel_5.png")
        assert ruta == "data/Carteles/cartel_5.png"
        assert os.path.isfile(poster.ruta_absoluta(ruta))


class TestValidacion:
    def test_formato_no_soportado(self, tmp_path):
        texto = tmp_path / "no_imagen.txt"
        texto.write_text("hola")
        with pytest.raises(ErrorNegocio):
            poster.preparar_origen(str(texto))

    def test_archivo_inexistente(self):
        with pytest.raises(ErrorNegocio):
            poster.preparar_origen("/ruta/que/no/existe.png")

    def test_link_con_prefijo_invalido(self):
        with pytest.raises(ErrorNegocio):
            poster.preparar_origen("ftp://ejemplo.com/a.png")

    def test_url_que_falla_descarga(self):
        with pytest.raises(ErrorNegocio):
            poster.preparar_origen(
                "https://no-existe.dominio.invalido.falso/cartel.png")


def test_cargar_thumb_devuelve_none_si_no_existe():
    assert poster.cargar_thumb("data/Carteles/inexistente.png") is None
    assert poster.cargar_thumb("") is None