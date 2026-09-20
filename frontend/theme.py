"""Paleta y helpers visuales del tema neón (morado/rosa/cian), compartidos
por la interfaz de usuario y la de administración.
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

PALETA = {
    "fondo": "#0D0B1E",
    "panel": "#171231",
    "panel2": "#1E1640",
    "borde": "#2A1F5E",
    "texto": "#EDE7FF",
    "texto_suave": "#9A8FC0",
    "entrada": "#241A4A",
    "morado": "#9D5CFF",
    "rosa": "#FF2BD8",
    "cian": "#00E5FF",
    "verde": "#00E88F",
    "rojo": "#FF3B6B",
    "ambar": "#FFD23F",
}

FUENTE = "Helvetica"
TITULO = (FUENTE, 22, "bold")
SUBTITULO = (FUENTE, 13, "bold")
TEXTO_F = (FUENTE, 11)
ETIQUETA = (FUENTE, 10, "bold")
BOTON_F = (FUENTE, 11, "bold")
BOTON_G = (FUENTE, 14, "bold")

_COLORES_BOTON = {
    "morado": ("#9D5CFF", "#B280FF"),
    "rosa": ("#FF2BD8", "#FF62E4"),
    "cian": ("#00E5FF", "#57EFFF"),
    "verde": ("#00E88F", "#4DF0B1"),
    "rojo": ("#FF3B6B", "#FF6B8F"),
    "ambar": ("#FFD23F", "#FFE07A"),
    "panel": ("#241A4A", "#31266B"),
}


def aplicar_raiz(raiz, titulo="Cinema"):
    raiz.configure(bg=PALETA["fondo"])
    if titulo:
        raiz.title(titulo)
    _estilos_tabla()


_ESTILO = [None]


def _estilos_tabla():
    if _ESTILO[0]:
        return _ESTILO[0]
    estilo = ttk.Style()
    if "clam" in estilo.theme_names():
        estilo.theme_use("clam")
    estilo.configure(
        "Neon.Treeview",
        background=PALETA["entrada"],
        fieldbackground=PALETA["entrada"],
        foreground=PALETA["texto"],
        rowheight=26,
        bordercolor=PALETA["borde"],
        lightcolor=PALETA["panel"],
        darkcolor=PALETA["panel"],
        font=TEXTO_F,
    )
    estilo.map(
        "Neon.Treeview",
        background=[("selected", PALETA["morado"])],
        foreground=[("selected", PALETA["fondo"])],
    )
    estilo.configure(
        "Neon.Treeview.Heading",
        background=PALETA["morado"],
        foreground=PALETA["fondo"],
        font=(FUENTE, 10, "bold"),
        relief="flat",
    )
    estilo.map(
        "Neon.Treeview.Heading",
        background=[("active", PALETA["rosa"])],
    )
    _ESTILO[0] = estilo
    return estilo


def marco(master, ancho=None, relleno=12):
    """Marco tipo 'tarjeta' con borde neón."""
    frame = tk.Frame(master, bg=PALETA["panel"],
                     highlightbackground=PALETA["borde"],
                     highlightthickness=1, padx=relleno, pady=relleno)
    if ancho:
        frame.configure(width=ancho)
    return frame


def etiqueta(master, texto, tamano=11, color=None, negrita=False, centro=False):
    lbl = tk.Label(master, text=texto, bg=PALETA["panel"],
                   fg=color or PALETA["texto"],
                   font=(FUENTE, tamano, "bold" if negrita else "normal"))
    if centro:
        lbl.configure(bg=PALETA["fondo"])
    return lbl


def boton(master, texto, comando, color="morado", tamano=BOTON_F,
          ancho=None):
    base, hover = _COLORES_BOTON[color]
    btn = tk.Button(
        master, text=texto, command=comando, bg=base,
        fg=PALETA["fondo"], font=tamano, relief="flat", cursor="hand2",
        activebackground=hover, activeforeground=PALETA["fondo"],
        padx=14, pady=8, bd=0, highlightthickness=0)
    if ancho:
        btn.configure(width=ancho)
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda e: btn.configure(bg=base))
    return btn


def entrada(master, ancho=28, var=None):
    e = tk.Entry(master, width=ancho, textvariable=var,
                 bg=PALETA["entrada"], fg=PALETA["texto"],
                 insertbackground=PALETA["cian"], relief="flat",
                 font=TEXTO_F, highlightbackground=PALETA["borde"],
                 highlightthickness=1)
    return e


def combobox(master, valores, ancho=28):
    cb = ttk.Combobox(master, values=valores, state="readonly", width=ancho,
                      font=TEXTO_F)
    cb.background = PALETA["entrada"]
    return cb


def crear_tabla(master, columnas, filas, alto=12, estilos=None):
    """Treeview con scrollbar estilo neón.

    columnas: [(clave, título, ancho, alineación)]
    filas:    listas de valores en el mismo orden.
    Devuelve (frame, tree) para colocar y refrescar.
    """
    _estilos_tabla()
    cuerpo = tk.Frame(master, bg=PALETA["panel"])
    keys = [c[0] for c in columnas]
    tree = ttk.Treeview(cuerpo, columns=keys, show="headings",
                        style="Neon.Treeview", height=alto)
    for clave, titulo, ancho, alineacion in columnas:
        tree.heading(clave, text=titulo)
        tree.column(clave, width=ancho, anchor=alineacion)
    barra = ttk.Scrollbar(cuerpo, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=barra.set)
    tree.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    _rellenar_tabla(tree, filas)
    return cuerpo, tree


def _rellenar_tabla(tree, filas):
    tree.delete(*tree.get_children())
    for fila in filas:
        tree.insert("", "end", values=fila)


def rellenar_tabla(tree, filas):
    _rellenar_tabla(tree, filas)


def panel_info(master, texto, color_estrellas="verde"):
    """Franja de aviso (éxito/error)."""
    f = tk.Frame(master, bg=PALETA["panel2"])
    lbl = tk.Label(f, text=texto, bg=PALETA["panel2"],
                   fg=PALETA[color_estrellas] if color_estrellas in PALETA
                   else PALETA["verde"],
                   font=(FUENTE, 10, "bold"), wraplength=420, justify="left")
    lbl.pack(padx=10, pady=8)
    return f


def mapa_asientos(master, filas, on_change=None, solo_lectura=False,
                  tamano=26):
    """Mapa de asientos como cuadrícula de cuadrados.

    filas:      [{'letra': 'A', 'asientos': [{'posicion','estado'}, ...]}, ...]
    on_change:  callback(fila) cuando cambia la selección.
    Devuelve (marco, seleccion) donde 'seleccion' es un set de posiciones.
    """
    seleccion = set()
    botones = {}

    def color(pos):
        if pos in seleccion:
            return PALETA["cian"]
        estado = botones[pos]._neon_estado
        if estado == "ocupado":
            return "#5A1B46"
        return PALETA["verde"]

    def alternar(pos):
        if solo_lectura or botones[pos]._neon_estado == "ocupado":
            return
        if pos in seleccion:
            seleccion.discard(pos)
        else:
            seleccion.add(pos)
        b = botones[pos]
        b.configure(bg=color(pos))
        if on_change:
            on_change(seleccion)

    contenedor = tk.Frame(master, bg=PALETA["panel"])
    if not filas:
        tk.Label(contenedor, text="Esta función no tiene asientos.",
                 bg=PALETA["panel"], fg=PALETA["texto_suave"],
                 font=(FUENTE, 10)).pack(pady=8)
    for fila in filas:
        renglon = tk.Frame(contenedor, bg=PALETA["panel"])
        renglon.pack(pady=4)
        tk.Label(renglon, text=f"Fila {fila['letra']}", width=7,
                 bg=PALETA["panel"], fg=PALETA["morado"],
                 font=(FUENTE, 9, "bold")).pack(side="left")
        medios = len(fila["asientos"]) // 2
        for i, asiento in enumerate(fila["asientos"]):
            if i == medios:
                tk.Label(renglon, text="  ", bg=PALETA["panel"]).pack(
                    side="left")
            pos = asiento["posicion"]
            estado = asiento["estado"]
            numero = asiento.get("numero", pos.split("-")[-1])
            disp = (estado != "ocupado") and not solo_lectura
            btn = tk.Button(
                renglon, width=2, height=1, font=(FUENTE, 8),
                relief="flat", bd=0, cursor="hand2" if disp else "arrow",
                text="X" if estado == "ocupado" else str(numero),
                state="normal" if not (solo_lectura or estado == "ocupado")
                else "disabled" if estado == "ocupado" or solo_lectura
                else "normal")
            btn.configure(
                bg=("#5A1B46" if estado == "ocupado" else PALETA["verde"]),
                disabledforeground=PALETA["texto_suave"],
                activebackground=PALETA["cian"],
                highlightbackground=PALETA["borde"],
                highlightthickness=1)
            btn._neon_estado = estado
            btn._neon_numero = numero
            botones[pos] = btn
            if not (solo_lectura or estado == "ocupado"):
                btn.configure(command=lambda p=pos: alternar(p))
            btn.pack(side="left", padx=2)

    leyenda = tk.Frame(contenedor, bg=PALETA["panel"])
    leyenda.pack(pady=(8, 0))
    for etiqueta, muestra in [("Libre", PALETA["verde"]),
                              ("Ocupado", "#5A1B46"),
                              ("Seleccionado", PALETA["cian"])]:
        celda = tk.Frame(leyenda, bg=muestra, width=14, height=14)
        celda.pack(side="left", padx=(12, 4), pady=2)
        celda.pack_propagate(False)
        tk.Label(leyenda, text=etiqueta, bg=PALETA["panel"],
                 fg=PALETA["texto_suave"], font=(FUENTE, 9)).pack(side="left")

    contenedor.pack()
    return contenedor, seleccion


def abrir_archivo(ruta):
    """Abre un archivo con la aplicación predeterminada del sistema."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except OSError:
        return False
    return True


def titulo_neon(master):
    """Encabezado 'CINEMA' con letras de dos colores."""
    frame = tk.Frame(master, bg=PALETA["fondo"])
    b1 = tk.Label(frame, text="CINE", bg=PALETA["fondo"],
                  fg=PALETA["rosa"], font=(FUENTE, 30, "bold"))
    b2 = tk.Label(frame, text="MA", bg=PALETA["fondo"],
                  fg=PALETA["cian"], font=(FUENTE, 30, "bold"))
    b1.pack(side="left")
    b2.pack(side="left")
    return frame


ANCHO_TARJETA = 176
ALTO_IMAGEN = 240


def tarjeta_pelicula(master, pelicula, on_click):
    """Tarjeta clicable de una película (foto o marcador con su título)."""
    card = tk.Frame(master, bg=PALETA["panel2"],
                    highlightbackground=PALETA["borde"],
                    highlightthickness=2, cursor="hand2")
    img_marco = tk.Frame(card, bg=PALETA["entrada"], width=ANCHO_TARJETA,
                         height=ALTO_IMAGEN)
    img_marco.pack_propagate(False)
    img_marco.pack(padx=6, pady=(6, 2))

    def actualizar_imagen():
        for hijo in img_marco.winfo_children():
            hijo.destroy()
        # Import tardío: backend.poster usa PIL y no debe cargarse con theme
        from backend.poster import cargar_thumb
        foto = cargar_thumb(pelicula.imagen,
                            (ANCHO_TARJETA - 6, ALTO_IMAGEN - 6))
        if foto:
            lbl = tk.Label(img_marco, image=foto, bg=PALETA["entrada"])
            lbl.photo = foto  # evita que el recolector borre la imagen
            lbl.place(relx=.5, rely=.5, anchor="center")
        else:
            lbl = tk.Label(img_marco, text=pelicula.titulo,
                           bg=PALETA["entrada"], fg=PALETA["texto_suave"],
                           font=(FUENTE, 13, "bold"),
                           wraplength=ANCHO_TARJETA - 24, justify="center")
            lbl.place(relx=.5, rely=.5, anchor="center")

    actualizar_imagen()
    titulo_lbl = tk.Label(card, text=pelicula.titulo, bg=PALETA["panel2"],
                          fg=PALETA["texto"], font=(FUENTE, 10, "bold"),
                          wraplength=ANCHO_TARJETA - 8, justify="center")
    titulo_lbl.pack(pady=(2, 6))
    for w in (card, img_marco, titulo_lbl):
        w.bind("<Button-1>", lambda e, p=pelicula: on_click(p))
        w.bind("<Enter>",
               lambda e: card.configure(highlightbackground=PALETA["cian"]))
        w.bind("<Leave>",
               lambda e: card.configure(highlightbackground=PALETA["borde"]))
    card._neon_pelicula_id = pelicula.id
    return card


def pasarela(master, peliculas, on_click, alto=330):
    """Carrusel horizontal de películas con flechas ◀ ▶ y rueda del ratón.

    peliculas: lista de objetos Pelicula.
    on_click:  callback(pelicula) al hacer clic en una tarjeta.
    Devuelve el contenedor (con ._neon_canvas para desplazarlo).
    """
    contenedor = tk.Frame(master, bg=PALETA["panel"])
    cab = tk.Frame(contenedor, bg=PALETA["panel"])
    cab.pack(fill="x", padx=6, pady=(4, 0))

    def xview(delta):
        contenedor._neon_canvas.xview_scroll(delta, "units")

    def ruleta(event):
        d = event.delta
        if not d:
            if getattr(event, "num", None) == 4:
                d = 120
            elif getattr(event, "num", None) == 5:
                d = -120
        if d:
            xview(-(d // 120))

    theme_boton_izq = tk.Button(
        cab, text="◀", command=lambda: xview(-3), bg=PALETA["morado"],
        fg=PALETA["fondo"], font=BOTON_F, relief="flat", cursor="hand2",
        activebackground=PALETA["rosa"], padx=10, pady=4)
    theme_boton_izq.pack(side="left", padx=(0, 8))
    tk.Label(cab, text="Cartelera", bg=PALETA["panel"],
             fg=PALETA["cian"], font=SUBTITULO).pack(side="left", expand=True)
    theme_boton_der = tk.Button(
        cab, text="▶", command=lambda: xview(3), bg=PALETA["morado"],
        fg=PALETA["fondo"], font=BOTON_F, relief="flat", cursor="hand2",
        activebackground=PALETA["rosa"], padx=10, pady=4)
    theme_boton_der.pack(side="right", padx=(8, 0))

    lienzo_contenedor = tk.Frame(contenedor, bg=PALETA["panel"])
    lienzo_contenedor.pack(fill="x", padx=6, pady=(2, 6))
    canvas = tk.Canvas(lienzo_contenedor, height=alto, bg=PALETA["panel"],
                       highlightthickness=0)
    lienzo = tk.Frame(canvas, bg=PALETA["panel"])
    ventana = canvas.create_window((0, 0), window=lienzo, anchor="nw")
    contenedor._neon_canvas = canvas

    def ajustar(event):
        canvas.itemconfigure(ventana, width=event.width)
        canvas.configure(scrollregion=canvas.bbox("all"))

    canvas.bind("<Configure>", ajustar)
    canvas.bind("<MouseWheel>", ruleta)
    canvas.pack(fill="x")
    for peli in peliculas:
        tarjeta = tarjeta_pelicula(lienzo, peli, on_click)
        tarjeta.pack(side="left", padx=8, pady=6)
        tarjeta.bind("<MouseWheel>", ruleta)
    contenedor.pack(fill="x")
    return contenedor