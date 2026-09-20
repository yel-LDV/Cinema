"""Guardado y carga de carteles (imágenes) de películas.

Los carteles pueden provenir de un archivo local o de una URL de internet.
Siempre se guardan reescalados en data/Carteles/cartel_<id>.png para que la
pasarela funcione sin conexión y con un peso razonable.
"""

import os
import urllib.error
import urllib.request
from io import BytesIO

from PIL import Image

from backend.database import RAIZ
from backend.models import ErrorNegocio

CARPETA_CARTELES = os.path.join(RAIZ, "data", "Carteles")
FORMATOS_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MIMES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
ANCHO_MAX = 400  # px máx de la dimensión mayor del cartel guardado


def _carpeta():
    os.makedirs(CARPETA_CARTELES, exist_ok=True)
    return CARPETA_CARTELES


def _ruta_relativa(nombre):
    return os.path.join("data", "Carteles", nombre)


def _borrar_existentes(pelicula_id):
    """Elimina cualquier cartel previo de la película."""
    if not os.path.isdir(CARPETA_CARTELES):
        return
    for nombre in os.listdir(CARPETA_CARTELES):
        if nombre.startswith(f"cartel_{pelicula_id}."):
            try:
                os.remove(os.path.join(CARPETA_CARTELES, nombre))
            except OSError:
                pass


def _descargar(url):
    """Descarga la imagen de una URL y devuelve los bytes; valida el tipo."""
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ErrorNegocio("El link debe comenzar con http:// o https://.")
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            tipo = resp.headers.get("Content-Type", "").split(";")[0].lower()
            if tipo and tipo not in MIMES:
                raise ErrorNegocio(
                    "El link no apunta a una imagen válida "
                    f"(tipo '{tipo}' no soportado).")
            datos = resp.read()
    except urllib.error.HTTPError as e:
        raise ErrorNegocio(f"No se pudo descargar la imagen (HTTP {e.code}).")\
            from e
    except urllib.error.URLError as e:
        raise ErrorNegocio("No se pudo descargar la imagen: "
                           f"{e.reason}.") from e
    except TimeoutError:
        raise ErrorNegocio("No se pudo descargar la imagen (tiempo agotado).")
    return datos


def _normalizar(datos):
    """Abre, verifica, reescala y devuelve la imagen en PNG."""
    try:
        with Image.open(datos) as prueba:
            prueba.verify()
    except Exception:
        raise ErrorNegocio(
            "El archivo no es una imagen válida o el formato no está "
            "soportado.")
    datos.seek(0)  # verify() invalida el objeto; se reabre para manipularlo
    imagen = Image.open(datos).convert("RGBA")
    imagen.thumbnail((ANCHO_MAX, ANCHO_MAX))
    return imagen


def preparar_origen(origen):
    """Valida el origen (archivo local o URL), reescala y devuelve los bytes
    PNG normalizados. Lanza ErrorNegocio si el origen no es válido."""
    if origen.startswith(("http://", "https://")):
        datos = BytesIO(_descargar(origen))
        origen_nombre = "link"
    else:
        if "://" in origen:
            raise ErrorNegocio("El link debe comenzar con http:// o https://.")
        if not os.path.isfile(origen):
            raise ErrorNegocio(f"No se encontró el archivo: {origen}")
        ext = os.path.splitext(origen)[1].lower()
        if ext not in FORMATOS_EXT:
            raise ErrorNegocio(
                f"Formato '{ext or '(sin extensión)'}' no soportado. Usa: "
                + ", ".join(sorted(FORMATOS_EXT)))
        with open(origen, "rb") as f:
            datos = BytesIO(f.read())
        origen_nombre = os.path.basename(origen)

    try:
        imagen = _normalizar(datos)
    except ErrorNegocio as e:
        if origen_nombre == "link":
            raise ErrorNegocio(
                "El link no corresponde a una imagen válida.") from e
        raise
    bufer = BytesIO()
    imagen.save(bufer, "PNG")
    return bufer.getvalue()


def volcar_png(datos, nombre):
    """Escribe los bytes PNG en data/Carteles, borrando versiones previas del
    mismo cartel (p. ej. distintas extensiones). Devuelve la ruta relativa."""
    _carpeta()
    base = os.path.splitext(nombre)[0]
    for existente in os.listdir(CARPETA_CARTELES):
        if existente.startswith(f"{base}."):
            try:
                os.remove(os.path.join(CARPETA_CARTELES, existente))
            except OSError:
                pass
    destino = os.path.join(CARPETA_CARTELES, nombre)
    with open(destino, "wb") as f:
        f.write(datos)
    return _ruta_relativa(nombre)


def guardar_imagen(origen, pelicula_id):
    """Guarda el cartel de 'origen' (archivo o URL) y devuelve la ruta
    relativa almacenada. Borra cualquier cartel previo de la película.
    """
    return volcar_png(preparar_origen(origen), f"cartel_{pelicula_id}.png")


def ruta_absoluta(ruta_relativa):
    """Convierte una ruta relativa del repo en ruta absoluta (o None)."""
    if not ruta_relativa:
        return None
    return os.path.normpath(os.path.join(RAIZ, ruta_relativa))


def cargar_thumb(ruta_relativa, tamano=(230, 330)):
    """Devuelve una ImageTk.PhotoImage reescalada del cartel, o None si no
    se puede cargar (película sin imagen o archivo inexistente).
    """
    ruta = ruta_absoluta(ruta_relativa)
    if not ruta or not os.path.isfile(ruta):
        return None
    try:
        from PIL import ImageTk
        with Image.open(ruta) as img:
            img.thumbnail(tamano)
            return ImageTk.PhotoImage(img)
    except Exception:
        return None


def borrar_cartel(pelicula_id):
    _borrar_existentes(pelicula_id)