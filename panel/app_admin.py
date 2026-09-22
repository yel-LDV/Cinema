"""Panel de administración: CRUD de películas y funciones, visión/cancelación
de cualquier venta y generación de estados de cuenta en PDF.
"""

import re
import tkinter as tk
from io import BytesIO
from tkinter import filedialog

from backend import poster
from backend.models import (CLASIFICACION_EDAD, ErrorNegocio)
from backend.pdf_generator import ReporteVentasPDF
from frontend import theme

T = theme.PALETA

COL_PELI = [("id", "ID", 40, "center"),
            ("titulo", "Título", 230, "w"),
            ("genero", "Género", 140, "w"),
            ("duracion", "Duración", 80, "center"),
            ("clas", "Clasif.", 70, "center"),
            ("precio", "Precio", 90, "e"),
            ("estado", "Estado", 90, "center")]

COL_FUNC = [("id", "ID", 40, "center"),
            ("titulo", "Película", 190, "w"),
            ("sala", "Sala", 80, "center"),
            ("horario", "Horario", 90, "center"),
            ("cap", "Cap.", 55, "center"),
            ("ocup", "Ocup.", 55, "center"),
            ("lib", "Libres", 60, "center")]

COL_VENTA = [("folio", "Folio", 75, "center"),
             ("fecha", "Fecha/Hora", 135, "w"),
             ("titulo", "Película", 150, "w"),
             ("sala", "Sala", 75, "center"),
             ("horario", "Horario", 85, "center"),
             ("cliente", "Cliente", 120, "w"),
             ("edad", "Edad", 45, "center"),
             ("bol", "Boletos", 55, "center"),
             ("pu", "P.U.", 75, "e"),
             ("desc", "Desc.", 55, "center"),
             ("total", "Total", 85, "e"),
             ("estado", "Estado", 85, "center")]


def aviso(win, texto, ok=True):
    if hasattr(win, "_aviso"):
        win._aviso.destroy()
    win._aviso = theme.panel_info(win, texto, "verde" if ok else "rojo")
    win._aviso.pack(fill="x", padx=16, pady=8)


def _entero(var, campo):
    try:
        return int(var.get().strip())
    except ValueError:
        raise ErrorNegocio(f"{campo} debe ser un número entero.") from None


def _precio(var, campo):
    try:
        return round(float(var.get().strip()), 2)
    except ValueError:
        raise ErrorNegocio(f"{campo} debe ser un número.") from None


def _imagen_cartel(form, fila, win, imagen_actual_ref):
    """Fila de 'Imagen (cartel)' en un formulario de película.

    Admite dos orígenes: archivo local (filedialog) o link de internet.
    Devuelve (estado, reset) donde estado["bytes"] guarda el PNG normalizado
    pendiente de guardar y reset(ruta) limpia la selección y refresca la
    vista previa de la película seleccionada.
    """
    PIL = None
    ImageTk = None
    try:
        from PIL import Image as _IMG, ImageTk as _ITK
        PIL, ImageTk = _IMG, _ITK
    except ImportError:
        pass

    estado = {"bytes": None}
    tk.Label(form, text="Imagen (cartel)", bg=T["panel"], fg=T["morado"],
             font=theme.ETIQUETA).grid(row=fila, column=0, sticky="w",
                                       pady=3)
    en_link = theme.entrada(form, 24)
    en_link.grid(row=fila, column=1, sticky="we", padx=6)
    form.columnconfigure(1, weight=1)

    botones = tk.Frame(form, bg=T["panel"])
    botones.grid(row=fila + 1, column=0, columnspan=2, sticky="w", padx=6)
    preview = tk.Frame(form, bg=T["entrada"], height=150,
                       highlightbackground=T["borde"], highlightthickness=1)
    preview.grid(row=fila + 2, column=0, columnspan=2, sticky="we",
                 padx=6, pady=(2, 8))
    preview.pack_propagate(False)

    def mostrar():
        for hijo in preview.winfo_children():
            hijo.destroy()
        foto = None
        if estado["bytes"] and PIL:
            img = PIL.open(BytesIO(estado["bytes"]))
            img.thumbnail((300, 140))
            foto = ImageTk.PhotoImage(img)
        elif imagen_actual_ref["ruta"]:
            foto = poster.cargar_thumb(imagen_actual_ref["ruta"],
                                       (300, 140))
        if foto:
            lbl = tk.Label(preview, image=foto, bg=T["entrada"])
            lbl.photo = foto
            preview._neon_foto = foto  # ref. robusta contra el recolector
            lbl.place(relx=.5, rely=.5, anchor="center")
        else:
            tk.Label(preview, text="Sin imagen: elige un archivo o pega un "
                     "link de internet", bg=T["entrada"],
                     fg=T["texto_suave"], font=(theme.FUENTE, 9),
                     wraplength=320, justify="center").place(
                relx=.5, rely=.5, anchor="center")

    def de_archivo():
        ruta = filedialog.askopenfilename(
            title="Cartel de la película",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.webp"),
                       ("Todos", "*.*")])
        if not ruta:
            return
        try:
            estado["bytes"] = poster.preparar_origen(ruta)
            en_link.delete(0, "end")
            mostrar()
        except ErrorNegocio as e:
            estado["bytes"] = None
            aviso(win, str(e), False)

    def usar_link():
        origen = en_link.get().strip()
        if not origen:
            aviso(win, "Pega primero el link de la imagen.", False)
            return
        try:
            estado["bytes"] = poster.preparar_origen(origen)
            mostrar()
        except ErrorNegocio as e:
            estado["bytes"] = None
            aviso(win, str(e), False)

    boton = theme.boton(botones, "De archivo", de_archivo, "cian")
    boton.pack(side="left", padx=(0, 6))
    theme.boton(botones, "Usar link", usar_link, "cian").pack(side="left")

    def reset(ruta):
        estado["bytes"] = None
        en_link.delete(0, "end")
        imagen_actual_ref["ruta"] = ruta or ""
        mostrar()

    mostrar()
    return estado, reset, en_link


class AppAdmin(tk.Toplevel):
    def __init__(self, raiz, servicio):
        super().__init__(raiz)
        self.raiz = raiz
        self.servicio = servicio
        theme.aplicar_raiz(self, "Cinema · Administración")
        self._centrar("900x520")
        self.ventanas_abiertas = []
        self._armar_menu()
        self.lift()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self.salir)

    def _centrar(self, dim):
        ancho, alto = dim.split("x")
        x = (self.winfo_screenwidth() - int(ancho)) // 2
        y = (self.winfo_screenheight() - int(alto)) // 3
        self.geometry(f"{dim}+{x}+{y}")

    # ---------------------------------------------------------------- #
    #                              Menú                                 #
    # ---------------------------------------------------------------- #
    def _armar_menu(self):
        frame = theme.marco(self, relleno=22)
        frame.pack(padx=24, pady=24, fill="both", expand=True)

        theme.titulo_neon(frame).pack(pady=(0, 4))
        tk.Label(frame, text="Panel de administración",
                 bg=T["panel"], fg=T["cian"], font=theme.SUBTITULO).pack()

        area = tk.Frame(frame, bg=T["panel"])
        area.pack(pady=12)
        tema_bloques = [
            ("Películas", [
                ("Ver catálogo", self._v_ver_peliculas, "morado"),
                ("Alta de película", self._v_alta_pelicula, "morado"),
                ("Editar película", self._v_editar_pelicula, "morado"),
                ("Dar de baja", self._v_baja_pelicula, "morado"),
            ]),
            ("Funciones", [
                ("Ver funciones", self._v_ver_funciones, "cian"),
                ("Alta de función", self._v_alta_funcion, "cian"),
                ("Ver asientos por función", self._v_asientos_funcion,
                 "cian"),
            ]),
            ("Ventas", [
                ("Ver todas las ventas", self._v_ventas, "verde"),
                ("Cancelar venta", self._v_cancelar, "ambar"),
            ]),
            ("Reportes PDF", [
                ("General", self._r_general, "rosa"),
                ("Por película", self._r_pelicula, "rosa"),
                ("Por día", self._r_dia, "rosa"),
                ("Por mes", self._r_mes, "rosa"),
            ]),
        ]
        columnas = tk.Frame(frame, bg=T["panel"])
        columnas.pack(pady=6)
        for i, (titulo, items) in enumerate(tema_bloques):
            col = tk.Frame(columnas, bg=T["panel2"],
                           highlightbackground=T["borde"],
                           highlightthickness=1, padx=10, pady=10)
            col.grid(row=0, column=i, padx=8)
            tk.Label(col, text=titulo, bg=T["panel2"], fg=T["cian"],
                     font=theme.SUBTITULO).pack(pady=(0, 8))
            for texto, comando, color in items:
                theme.boton(col, texto, comando, color, tamano=(theme.FUENTE,
                            10, "bold"), ancho=22).pack(pady=3)

        theme.boton(frame, "Salir", self.salir, "rojo", ancho=20).pack(pady=8)

    # ---------------------------------------------------------------- #
    #                          Películas                                #
    # ---------------------------------------------------------------- #
    def _v_ver_peliculas(self):
        win = self._nueva_ventana("Catálogo de películas", 780, 440)
        pelis = self.servicio.listar_peliculas(solo_activas=False)
        filas = [[p.id, p.titulo, p.genero, f"{p.duracion_min} min",
                  p.clasificacion, f"${p.precio_base:.2f}",
                  "Activa" if p.activa else "Baja"]
                 for p in pelis]
        cuerpo, _ = theme.crear_tabla(win, COL_PELI, filas)
        cuerpo.pack(fill="both", expand=True, padx=16, pady=8)
        if not pelis:
            aviso(win, "El catálogo está vacío.")
        theme.boton(win, "Cerrar", win.destroy, "panel", ancho=14).pack(pady=10)

    def _v_alta_pelicula(self):
        win = self._nueva_ventana("Alta de película", 500, 560)
        form = theme.marco(win, relleno=16)
        form.pack(fill="x", padx=16, pady=12)

        en_titulo = theme.entrada(form, 36)
        en_genero = theme.entrada(form, 36)
        en_duracion = theme.entrada(form, 16)
        en_precio = theme.entrada(form, 16)
        cb_clas = theme.combobox(form, sorted(CLASIFICACION_EDAD), 12)
        cb_clas.set("B")

        campos = [("Título", en_titulo), ("Género", en_genero),
                  ("Duración (min)", en_duracion), ("Precio base", en_precio),
                  ("Clasificación", cb_clas)]
        for i, (texto, widget) in enumerate(campos):
            tk.Label(form, text=texto, bg=T["panel"], fg=T["morado"],
                     font=theme.ETIQUETA).grid(row=i, column=0, sticky="w",
                                               pady=3)
            widget.grid(row=i, column=1, sticky="we", padx=6)
        form.columnconfigure(1, weight=1)

        estado_img, reset_img, _ = _imagen_cartel(
            form, len(campos), win, {"ruta": ""})

        def guardar():
            try:
                p = self.servicio.crear_pelicula(
                    en_titulo.get(), en_genero.get(),
                    _entero(en_duracion, "La duración"),
                    cb_clas.get(), _precio(en_precio, "El precio"))
                if estado_img["bytes"]:
                    ruta = poster.volcar_png(estado_img["bytes"],
                                             f"cartel_{p.id}.png")
                    self.servicio.editar_pelicula(
                        p.id, en_titulo.get(), en_genero.get(),
                        _entero(en_duracion, "La duración"), cb_clas.get(),
                        _precio(en_precio, "El precio"), imagen=ruta)
                aviso(win, f"Película '{p.titulo}' dada de alta.", True)
                reset_img("")
                for w in (en_titulo, en_genero, en_duracion, en_precio):
                    w.delete(0, "end")
            except (ErrorNegocio, ValueError) as e:
                aviso(win, str(e), False)

        theme.boton(form, "Guardar", guardar, "morado", ancho=16).grid(
            row=len(campos) + 3, column=0, columnspan=2, pady=10)

    def _v_baja_pelicula(self):
        win = self._nueva_ventana("Dar de baja película", 480, 300)
        pelis = self.servicio.listar_peliculas()
        cb = theme.combobox(
            win, [f"#{p.id} · {p.titulo} ({p.clasificacion})" for p in pelis],
            46)
        cb.set("Selecciona una película" if pelis else "")
        cb.pack(padx=16, pady=8)
        if not pelis:
            aviso(win, "No hay películas activas para dar de baja.")
            return

        def hacer():
            try:
                pid = int(cb.get().split("·")[0].strip().lstrip("#"))
                self.servicio.dar_de_baja_pelicula(pid)
                aviso(win, "Película dada de baja. Ya no aparece en "
                           "cartelera ni puede venderse.", True)
            except (ErrorNegocio, ValueError) as e:
                aviso(win, str(e), False)

        theme.boton(win, "Dar de baja", hacer, "rojo", ancho=16).pack(pady=6)

    def _v_editar_pelicula(self):
        win = self._nueva_ventana("Editar película", 500, 580)
        pelis = self.servicio.listar_peliculas(solo_activas=False)
        if not pelis:
            aviso(win, "No hay películas para editar.")
            return
        form = theme.marco(win, relleno=16)
        form.pack(fill="x", padx=16, pady=12)

        cb = theme.combobox(
            form, [f"#{p.id} · {p.titulo}" for p in pelis], 40)
        en_titulo = theme.entrada(form, 36)
        en_genero = theme.entrada(form, 36)
        en_duracion = theme.entrada(form, 16)
        en_precio = theme.entrada(form, 16)
        cb_clas = theme.combobox(form, sorted(CLASIFICACION_EDAD), 10)

        campos = [("Película a editar", cb), ("Título", en_titulo),
                  ("Género", en_genero), ("Duración (min)", en_duracion),
                  ("Precio base", en_precio), ("Clasificación", cb_clas)]
        for i, (texto, widget) in enumerate(campos):
            tk.Label(form, text=texto, bg=T["panel"], fg=T["morado"],
                     font=theme.ETIQUETA).grid(row=i, column=0, sticky="w",
                                               pady=3)
            widget.grid(row=i, column=1, sticky="we", padx=6)
        form.columnconfigure(1, weight=1)

        imagen_ref = {"ruta": ""}
        estado_img, reset_img, _ = _imagen_cartel(form, len(campos), win,
                                                  imagen_ref)

        def elegida(_e=None):
            if not cb.get():
                return
            pid = int(cb.get().split("·")[0].strip().lstrip("#"))
            p = self.servicio.obtener_pelicula(pid)
            if p is None:
                return
            en_titulo.delete(0, "end")
            en_genero.delete(0, "end")
            en_duracion.delete(0, "end")
            en_precio.delete(0, "end")
            en_titulo.insert(0, p.titulo)
            en_genero.insert(0, p.genero)
            en_duracion.insert(0, str(p.duracion_min))
            en_precio.insert(0, f"{p.precio_base:.2f}")
            cb_clas.set(p.clasificacion)
            reset_img(p.imagen)

        cb.bind("<<ComboboxSelected>>", elegida)

        def guardar():
            try:
                pid = int(cb.get().split("·")[0].strip().lstrip("#"))
                p0 = self.servicio.obtener_pelicula(pid)
                imagen = None
                if estado_img["bytes"]:
                    imagen = poster.volcar_png(estado_img["bytes"],
                                               f"cartel_{pid}.png")
                p = self.servicio.editar_pelicula(
                    pid, en_titulo.get(), en_genero.get(),
                    _entero(en_duracion, "La duración"),
                    cb_clas.get(), _precio(en_precio, "El precio"),
                    imagen=imagen)
                aviso(win,
                      f"Película '{p.titulo}' actualizada.", True)
                cb["values"] = [
                    f"#{x.id} · {x.titulo}" for x in
                    self.servicio.listar_peliculas(solo_activas=False)]
                reset_img(p.imagen or p0.imagen or "")
            except (ErrorNegocio, ValueError) as e:
                aviso(win, str(e), False)

        theme.boton(form, "Guardar cambios", guardar, "morado", ancho=18).grid(
            row=len(campos) + 3, column=0, columnspan=2, pady=10)

    # ---------------------------------------------------------------- #
    #                          Funciones                                #
    # ---------------------------------------------------------------- #
    def _v_ver_funciones(self):
        win = self._nueva_ventana("Funciones", 700, 440)
        filas = []
        for f in self.servicio.listar_funciones(
                solo_pelicula_activa=False):
            p = self.servicio.obtener_pelicula(f.pelicula_id)
            filas.append([f.id, p.titulo, f.sala, f.horario, f.capacidad,
                          f.ocupados, f.disponibles])
        cuerpo, _ = theme.crear_tabla(win, COL_FUNC, filas)
        cuerpo.pack(fill="both", expand=True, padx=16, pady=8)
        theme.boton(win, "Cerrar", win.destroy, "panel", ancho=14).pack(pady=10)

    def _v_alta_funcion(self):
        win = self._nueva_ventana("Alta de función", 480, 360)
        pelis = self.servicio.listar_peliculas()
        if not pelis:
            aviso(win, "Primero hay que dar de alta una película.")
            return
        form = theme.marco(win, relleno=16)
        form.pack(fill="x", padx=16, pady=12)

        cb = theme.combobox(
            form, [f"#{p.id} · {p.titulo} ({p.clasificacion})" for p in pelis],
            46)
        en_sala = theme.entrada(form, 36)
        en_hora = theme.entrada(form, 16)
        en_cap = theme.entrada(form, 16)

        campos = [("Película", cb), ("Sala", en_sala),
                  ("Horario", en_hora), ("Capacidad", en_cap)]
        for i, (texto, widget) in enumerate(campos):
            tk.Label(form, text=texto, bg=T["panel"], fg=T["cian"],
                     font=theme.ETIQUETA).grid(row=i, column=0, sticky="w",
                                               pady=3)
            widget.grid(row=i, column=1, sticky="we", padx=6)
        form.columnconfigure(1, weight=1)

        def guardar():
            try:
                pid = int(cb.get().split("·")[0].strip().lstrip("#"))
                f = self.servicio.crear_funcion(
                    pid, en_sala.get(), en_hora.get(),
                    _entero(en_cap, "La capacidad"))
                aviso(win, f"Función #{f.id} creada ({f.sala} · {f.horario}).",
                      True)
                for w in (en_sala, en_hora, en_cap):
                    w.delete(0, "end")
            except (ErrorNegocio, ValueError) as e:
                aviso(win, str(e), False)

        theme.boton(form, "Guardar", guardar, "cian", ancho=16).grid(
            row=len(campos), column=0, columnspan=2, pady=10)

    def _v_asientos_funcion(self):
        win = self._nueva_ventana("Asientos por función", 720, 700)
        funciones = self.servicio.listar_funciones(
            solo_pelicula_activa=False)
        if not funciones:
            aviso(win, "No hay funciones registradas.")
            return

        def etiqueta(f):
            p = self.servicio.obtener_pelicula(f.pelicula_id)
            return f"#{f.id} · {p.titulo} · {f.sala} · {f.horario} · " \
                   f"{f.disponibles} libres"

        cb = theme.combobox(win, [etiqueta(f) for f in funciones], 50)
        cb.pack(padx=16, pady=8)

        zona_mapa = tk.Frame(win, bg=T["panel"])
        zona_mapa.pack(padx=16, pady=(4, 0))

        def cargar():
            for w in zona_mapa.winfo_children():
                w.destroy()
            if not cb.get():
                return
            fid = int(cb.get().split("·")[0].strip().lstrip("#"))
            asientos = self.servicio.listar_asientos(fid)
            filas = []
            actual = None
            for a in asientos:
                if actual is None or actual["letra"] != a["fila"]:
                    actual = {"letra": a["fila"], "asientos": []}
                    filas.append(actual)
                actual["asientos"].append(a)
            libres = sum(1 for a in asientos if a["estado"] == "libre")
            theme.mapa_asientos(zona_mapa, filas, solo_lectura=True)
            theme.panel_info(zona_mapa,
                             f"{libres} libre(s) · "
                             f"{len(asientos) - libres} ocupado(s)").pack()

        cb.bind("<<ComboboxSelected>>", lambda _e: cargar())

        theme.boton(win, "Cerrar", win.destroy, "panel", ancho=14).pack(
            pady=10)

    # ---------------------------------------------------------------- #
    #                           Ventas                                  #
    # ---------------------------------------------------------------- #
    def _v_ventas(self):
        win = self._nueva_ventana("Todas las ventas", 880, 480)
        ventas = self.servicio.ventas_detalladas()
        filas = [[v["folio"], v["fecha_hora"], v["pelicula_titulo"],
                  v["sala"], v["horario"], v["cliente_nombre"], v["edad"],
                  v["cantidad_boletos"], f"${v['precio_unitario']:.2f}",
                  f"{v['descuento_pct'] * 100:.0f}%",
                  f"${v['total']:.2f}", v["estado"]] for v in ventas]
        cuerpo, _ = theme.crear_tabla(win, COL_VENTA, filas)
        cuerpo.pack(fill="both", expand=True, padx=16, pady=8)
        if not ventas:
            aviso(win, "Aún no hay ventas registradas.")
        theme.boton(win, "Cerrar", win.destroy, "panel", ancho=14).pack(pady=10)

    def _v_cancelar(self):
        win = self._nueva_ventana("Cancelar venta", 480, 280)
        form = theme.marco(win, relleno=16)
        form.pack(fill="x", padx=16, pady=16)
        tk.Label(form, text="Folio de la venta a cancelar", bg=T["panel"],
                 fg=T["ambar"], font=theme.ETIQUETA).pack(anchor="w")
        en_folio = theme.entrada(form, 42)
        en_folio.pack(fill="x", pady=(4, 12))

        def hacer():
            try:
                venta = self.servicio.cancelar_compra(en_folio.get())
                aviso(win, f"Venta {venta.folio} cancelada: se liberaron "
                           f"{venta.cantidad_boletos} lugar(es).", True)
            except ErrorNegocio as e:
                aviso(win, str(e), False)

        theme.boton(form, "Cancelar venta", hacer, "ambar", ancho=18).pack()

    # ---------------------------------------------------------------- #
    #                       Reportes PDF                                #
    # ---------------------------------------------------------------- #
    def _generar(self, reporte, nombre):
        ruta = ReporteVentasPDF().generar(reporte, nombre=nombre)
        theme.abrir_archivo(ruta)
        return ruta

    def _r_general(self):
        win = self._nueva_ventana("Reporte general", 420, 220)
        reporte = self.servicio.ventas_reporte("general")

        def generar():
            ruta = self._generar(reporte, "reporte_general")
            aviso(win, f"Estado de cuenta generado:\n{ruta}", True)

        aviso(win, f"Ventas activas: {reporte['num_ventas']} · "
                   f"Boletos: {reporte['total_boletos']} · "
                   f"Ingresos: ${reporte['total_ingresos']:.2f}")
        theme.boton(win, "Generar PDF", generar, "rosa", ancho=16).pack(pady=8)

    def _r_pelicula(self):
        win = self._nueva_ventana("Reporte por película", 480, 280)
        pelis = self.servicio.listar_peliculas(solo_activas=False)
        cb = theme.combobox(
            win, [f"#{p.id} · {p.titulo}" for p in pelis], 46)
        cb.set("Selecciona una película" if pelis else "")
        cb.pack(padx=16, pady=8)
        if not pelis:
            aviso(win, "No hay películas.")
            return

        def generar():
            try:
                pid = int(cb.get().split("·")[0].strip().lstrip("#"))
                reporte = self.servicio.ventas_reporte("pelicula", pid)
                nombre = f"reporte_pelicula_{pid}"
                ruta = self._generar(reporte, nombre)
                aviso(win, f"{reporte['titulo']}\n{ruta}", True)
            except (ErrorNegocio, ValueError) as e:
                aviso(win, str(e), False)

        theme.boton(win, "Generar PDF", generar, "rosa", ancho=16).pack(pady=6)

    def _r_dia(self):
        win = self._nueva_ventana("Reporte por día", 460, 260)
        form = theme.marco(win, relleno=16)
        form.pack(fill="x", padx=16, pady=16)
        tk.Label(form, text="Fecha (AAAA-MM-DD)", bg=T["panel"],
                 fg=T["rosa"], font=theme.ETIQUETA).pack(anchor="w")
        en = theme.entrada(form, 42)
        en.pack(fill="x", pady=(4, 12))
        en.insert(0, "AAAA-MM-DD")

        def generar():
            fecha = en.get().strip()
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
                aviso(win, "Usa el formato AAAA-MM-DD.", False)
                return
            reporte = self.servicio.ventas_reporte("dia", fecha)
            ruta = self._generar(reporte, f"reporte_dia_{fecha}")
            aviso(win, f"{reporte['titulo']}\n{ruta}", True)

        theme.boton(form, "Generar PDF", generar, "rosa", ancho=16).pack()

    def _r_mes(self):
        win = self._nueva_ventana("Reporte por mes", 460, 260)
        form = theme.marco(win, relleno=16)
        form.pack(fill="x", padx=16, pady=16)
        tk.Label(form, text="Mes (AAAA-MM)", bg=T["panel"],
                 fg=T["rosa"], font=theme.ETIQUETA).pack(anchor="w")
        en = theme.entrada(form, 42)
        en.pack(fill="x", pady=(4, 12))
        en.insert(0, "AAAA-MM")

        def generar():
            mes = en.get().strip()
            if not re.fullmatch(r"\d{4}-\d{2}", mes):
                aviso(win, "Usa el formato AAAA-MM.", False)
                return
            reporte = self.servicio.ventas_reporte("mes", mes)
            ruta = self._generar(reporte, f"reporte_mes_{mes}")
            aviso(win, f"{reporte['titulo']}\n{ruta}", True)

        theme.boton(form, "Generar PDF", generar, "rosa", ancho=16).pack()

    # ---------------------------------------------------------------- #
    #                              Utilidades                            #
    # ---------------------------------------------------------------- #
    def _nueva_ventana(self, titulo, ancho, alto):
        win = tk.Toplevel(self.raiz)
        theme.aplicar_raiz(win, titulo)
        win.geometry(f"{ancho}x{alto}")
        win.transient(self)
        win.lift()
        self.ventanas_abiertas.append(win)
        return win

    def salir(self):
        for w in self.ventanas_abiertas:
            if w.winfo_exists():
                w.destroy()
        self.destroy()