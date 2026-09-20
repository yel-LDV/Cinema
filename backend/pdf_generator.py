"""Generación de tickets (por compra) y estados de cuenta (reportes) en PDF.

Usa las mismas reglas visuales del tema neón para que boletos y reportes
parezcan del mismo universo.
"""

import os
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A6, A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from backend.database import RAIZ

RUTA_TICKETS = os.path.join(RAIZ, "tickets")
RUTA_REPORTES = os.path.join(RAIZ, "reportes")

# Paleta neón (coincide con frontend/theme.py)
FONDO = HexColor("#0D0B1E")
PANEL = HexColor("#171231")
BORDE = HexColor("#2A1F5E")
TEXTO = HexColor("#EDE7FF")
TEXTO_SUAVE = HexColor("#9A8FC0")
MORADO = HexColor("#9D5CFF")
ROSA = HexColor("#FF2BD8")
CIAN = HexColor("#00E5FF")
VERDE = HexColor("#00E88F")
ROJO = HexColor("#FF3B6B")
AMBAR = HexColor("#FFD23F")

FUENTE = "Helvetica"
FUENTE_B = "Helvetica-Bold"

_RUTA_ACTUAL = [None]

ESTADO = {
    "activa": ("activa", VERDE),
    "cancelada": ("Cancelada", ROJO),
}


def _dinero(v):
    return f"${v:,.2f}"


def _pct(v):
    return f"{v * 100:.0f}%"


def _filtrar(texto):
    return escape(str(texto))


def ultimo_pdf_generado():
    return _RUTA_ACTUAL[0]


def _estilo(tamano, negrita=False, color=None, centro=False):
    return ParagraphStyle(
        "NeonEstilo",
        fontName=FUENTE_B if negrita else FUENTE,
        fontSize=tamano,
        textColor=color or TEXTO,
        alignment=TA_CENTER if centro else 0,
        leading=tamano * 1.3,
    )


class _FondoNeon:
    """Pinta el fondo oscuro y el marco neón de cada página."""

    def __call__(self, canv, doc):
        ancho, alto = doc.pagesize
        canv.saveState()
        canv.setFillColor(FONDO)
        canv.rect(0, 0, ancho, alto, fill=1, stroke=0)
        canv.setFillColor(MORADO)
        canv.rect(0, alto - 6 * mm, ancho, 6 * mm, fill=1, stroke=0)
        canv.setFillColor(ROSA)
        canv.rect(0, 0, ancho, 4 * mm, fill=1, stroke=0)
        canv.setStrokeColor(CIAN)
        canv.setLineWidth(0.5)
        m = 8 * mm
        canv.rect(m, m, ancho - 2 * m, alto - 2 * m, fill=0, stroke=1)
        canv.restoreState()


# --------------------------------------------------------------------- #
#                           Ticket de compra                            #
# --------------------------------------------------------------------- #
class TicketPDF:
    """Boleto de una venta (detalle enriquecido de CineService)."""

    def generar(self, detalle, salida_dir=None):
        salida_dir = salida_dir or RUTA_TICKETS
        os.makedirs(salida_dir, exist_ok=True)
        folio = detalle["folio"]
        ruta = os.path.join(salida_dir, f"ticket_{folio.replace('/', '_')}.pdf")
        doc = SimpleDocTemplate(
            ruta, pagesize=A6, topMargin=15 * mm, bottomMargin=12 * mm,
            leftMargin=12 * mm, rightMargin=12 * mm,
            title=f"Ticket {folio}", author="Cine Neón")
        doc.firstPage = _FondoNeon()
        doc.laterPages = _FondoNeon()

        ph = []
        ph.append(Paragraph(
            '<font color="#FF2BD8"><b>CINE</b></font>'
            '<font color="#00E5FF"><b>NEÓN</b></font>',
            _estilo(20, True, TEXTO, centro=True)))
        ph.append(Spacer(1, 1 * mm))
        ph.append(Paragraph("— BOLETO DE ENTRADA —",
                            _estilo(9, False, MORADO, centro=True)))
        ph.append(Spacer(1, 4 * mm))
        ph.append(Paragraph(
            f"Folio: <b>{_filtrar(detalle['folio'])}</b>"
            f'<br/><font color="#00E5FF">{_filtrar(detalle["fecha_hora"])}'
            "</font>", _estilo(8.5)))
        ph.append(Spacer(1, 3 * mm))

        detalles = [
            ("Película", detalle["pelicula_titulo"]),
            ("Clasificación", detalle.get("clasificacion", "A")),
            ("Sala", detalle["sala"]),
            ("Horario", detalle["horario"]),
            ("Cliente", detalle["cliente_nombre"]),
            ("Edad", f"{detalle['edad']} años"),
            ("Boletos", str(detalle["cantidad_boletos"])),
            ("Precio unitario", _dinero(detalle["precio_unitario"])),
            ("Descuento", _pct(detalle["descuento_pct"])
             if detalle["descuento_pct"] else "—"),
            ("TOTAL", _dinero(detalle["total"])),
        ]
        filas = [[Paragraph(f"<b>{k}</b>", _estilo(8, True, MORADO)),
                  Paragraph(v, _estilo(8))] for k, v in detalles]
        tabla = Table(filas, colWidths=[32 * mm, 45 * mm])
        n = len(filas)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, n - 1), (1, n - 1), PANEL),
            ("BOX", (0, 0), (-1, -1), 0.4, MORADO),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDE),
            ("ROWBACKGROUNDS", (0, 0), (-1, n - 2), [None, PANEL]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TEXTCOLOR", (0, n - 1), (1, n - 1), VERDE),
        ]))
        ph.append(tabla)
        ph.append(Spacer(1, 4 * mm))
        corte = "· " * 26
        ph.append(Paragraph(f'<font color="#9A8FC0">{corte}</font>',
                            _estilo(8, color=TEXTO_SUAVE, centro=True)))
        ph.append(Spacer(1, 2 * mm))
        ph.append(Paragraph('<font color="#FFD23F"><b>¡Disfruta la función!'
                            '</b></font>', _estilo(9, True, AMBAR,
                                                   centro=True)))

        doc.build(ph)
        _RUTA_ACTUAL[0] = ruta
        return ruta


# --------------------------------------------------------------------- #
#                         Estado de cuenta (reporte)                    #
# --------------------------------------------------------------------- #
class ReporteVentasPDF:
    """Reporte de ventas por película, día, mes o general."""

    def generar(self, reporte, salida_dir=None, nombre=None):
        salida_dir = salida_dir or RUTA_REPORTES
        os.makedirs(salida_dir, exist_ok=True)
        if nombre is None:
            nombre = f"reporte_{reporte['ambito']}"
            if reporte.get("valor"):
                nombre += f"_{str(reporte['valor']).replace('/', '-')}"
        ruta = os.path.join(salida_dir, f"{nombre}.pdf")
        doc = SimpleDocTemplate(
            ruta, pagesize=landscape(A4), topMargin=16 * mm,
            bottomMargin=14 * mm, leftMargin=12 * mm, rightMargin=12 * mm,
            title=reporte["titulo"], author="Cine Neón")
        doc.firstPage = _FondoNeon()
        doc.laterPages = _FondoNeon()

        ph = []
        ph.append(Paragraph(
            '<font color="#FF2BD8"><b>CINE</b></font>'
            '<font color="#00E5FF"><b>NEÓN</b></font> · '
            '<font color="#EDE7FF">Estado de cuenta</font>',
            _estilo(18, True, TEXTO)))
        ph.append(Spacer(1, 2 * mm))
        ph.append(Paragraph(_filtrar(reporte["titulo"]),
                            _estilo(12, False, CIAN)))
        ph.append(Spacer(1, 3 * mm))

        resumen = (
            f"Ventas: <b>{reporte['num_ventas']}</b> &nbsp; · &nbsp; "
            f"Boletos: <b>{reporte['total_boletos']}</b> &nbsp; · &nbsp; "
            f"Ingresos: <font color='#00E88F'><b>{_dinero(reporte['total_ingresos'])}"
            "</b></font> &nbsp; · &nbsp; Promedio por venta: "
            f"{_dinero(reporte['promedio_venta'])}")
        ph.append(Paragraph(resumen, _estilo(9.5)))
        ph.append(Spacer(1, 4 * mm))

        encabezados = ["Folio", "Fecha", "Película", "Sala / Horario",
                       "Cliente", "Edad", "Boleto", "P. unit.", "Desc.",
                       "Total", "Estado"]
        ancho_total = 297 * mm - 24 * mm
        anchos = [18 * mm, 42 * mm, 44 * mm, 32 * mm, 36 * mm, 14.5 * mm,
                  14.5 * mm, 21 * mm, 15 * mm, 24 * mm, 21 * mm]
        # Recalcula proporcionalmente para no exceder el ancho disponible
        suma = sum(anchos)
        anchos = [a * ancho_total / suma for a in anchos]

        filas = [[Paragraph(f"<b>{_filtrar(h)}</b>", _estilo(8, True)) for h in encabezados]]
        for f in reporte["filas"]:
            estado_color = ESTADO.get(f["estado"], ("activa", TEXTO))
            filas.append([
                Paragraph(_filtrar(f["folio"]), _estilo(7.5)),
                Paragraph(_filtrar(f["fecha_hora"]), _estilo(7.5)),
                Paragraph(_filtrar(f["pelicula_titulo"]), _estilo(7.5)),
                Paragraph(f"{_filtrar(f['sala'])} · {_filtrar(f['horario'])}",
                          _estilo(7.5)),
                Paragraph(_filtrar(f["cliente_nombre"]), _estilo(7.5)),
                Paragraph(str(f["edad"]), _estilo(7.5)),
                Paragraph(str(f["cantidad_boletos"]), _estilo(7.5)),
                Paragraph(_dinero(f["precio_unitario"]), _estilo(7.5)),
                Paragraph(_pct(f["descuento_pct"])
                          if f["descuento_pct"] else "—", _estilo(7.5)),
                Paragraph(_dinero(f["total"]), _estilo(7.5, True, VERDE)),
                Paragraph(f"<b>{_filtrar(estado_color[0])}</b>",
                          _estilo(7.5, True, estado_color[1])),
            ])

        tabla = Table(filas, colWidths=anchos, repeatRows=1)
        estilos_tabla = [
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#241A4A")),
            ("BOX", (0, 0), (-1, -1), 0.4, MORADO),
            ("INNERGRID", (0, 0), (-1, -1), 0.2, BORDE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [None, PANEL]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]
        if reporte["filas"]:
            f = len(filas) - 1
            estilos_tabla.append(("BACKGROUND", (0, f), (-1, f),
                                  HexColor("#241A4A")))
            estilos_tabla.append(
                ("LINEABOVE", (0, f), (-1, f), 0.6, ROSA))
            estilos_tabla.append(("TEXTCOLOR", (0, f), (-1, f), AMBAR))
            estilos_tabla.append(("FONT", (0, f), (-1, f), FUENTE_B))
        tabla.setStyle(TableStyle(estilos_tabla))
        ph.append(tabla)

        if not reporte["filas"]:
            ph.append(Spacer(1, 6 * mm))
            ph.append(Paragraph(
                '<font color="#9A8FC0">No hay ventas activas en este '
                "periodo.</font>", _estilo(10, color=TEXTO_SUAVE)))

        doc.build(ph)
        _RUTA_ACTUAL[0] = ruta
        return ruta