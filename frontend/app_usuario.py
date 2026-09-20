"""Interfaz del usuario final: cartelera, compra (con ticket PDF), lugares
disponibles, cancelación, historial de ventas y salir.
"""

import tkinter as tk

from backend.models import (Cliente, ErrorNegocio,
                            edad_minima_clasificacion)
from backend.pdf_generator import TicketPDF
from frontend import theme

T = theme.PALETA

COL_PELICULA = [("titulo", "Película", 240, "w"),
                ("genero", "Género", 150, "w"),
                ("duracion", "Duración", 80, "center"),
                ("clas", "Clasif.", 70, "center"),
                ("precio", "Precio", 90, "e"),
                ("estado", "Estado", 80, "center")]

COL_FUNCION = [("id", "ID", 45, "center"),
               ("titulo", "Película", 200, "w"),
               ("sala", "Sala", 80, "center"),
               ("horario", "Horario", 90, "center"),
               ("cap", "Cap.", 55, "center"),
               ("ocu", "Ocup.", 55, "center"),
               ("lib", "Libres", 60, "center")]

COL_VENTA = [("folio", "Folio", 75, "center"),
             ("fecha", "Fecha/Hora", 140, "w"),
             ("titulo", "Película", 160, "w"),
             ("sala", "Sala", 80, "center"),
             ("horario", "Horario", 90, "center"),
             ("cliente", "Cliente", 130, "w"),
             ("edad", "Edad", 50, "center"),
             ("bol", "Boletos", 60, "center"),
             ("pu", "P.U.", 80, "e"),
             ("desc", "Desc.", 60, "center"),
             ("total", "Total", 90, "e"),
             ("estado", "Estado", 90, "center")]


def aviso(win, texto, ok=True):
    """Etiqueta de mensaje (reemplaza la anterior) en la ventana."""
    if hasattr(win, "_aviso"):
        win._aviso.destroy()
    win._aviso = theme.panel_info(win, texto, "verde" if ok else "rojo")
    win._aviso.pack(fill="x", padx=16, pady=8)


class AppUsuario(tk.Toplevel):
    def __init__(self, raiz, servicio):
        super().__init__(raiz)
        self.raiz = raiz
        self.servicio = servicio
        theme.aplicar_raiz(self, "Cinema · Usuario")
        self.ventanas_abiertas = []
        self._armar_menu()
        self.protocol("WM_DELETE_WINDOW", self.salir)

    # ---------------------------------------------------------------- #
    #                              Menú                                 #
    # ---------------------------------------------------------------- #
    def _armar_menu(self):
        frame = theme.marco(self, relleno=24)
        frame.pack(padx=24, pady=24, fill="both", expand=True)

        theme.titulo_neon(frame).pack(pady=(0, 4))
        tk.Label(frame, text="Usuario", bg=T["panel"],
                 fg=T["morado"], font=theme.SUBTITULO).pack()

        area = tk.Frame(frame, bg=T["panel"])
        area.pack(pady=14)
        for texto, comando, color in [
            ("01  Mostrar películas", self._v_peliculas, "morado"),
            ("02  Comprar boletos", self._v_comprar, "rosa"),
            ("03  Lugares disponibles", self._v_lugares, "cian"),
            ("04  Cancelar compra", self._v_cancelar, "ambar"),
            ("05  Mostrar ventas", self._v_ventas, "verde"),
            ("06  Salir", self.salir, "rojo"),
        ]:
            theme.boton(area, texto, comando, color, tamano=theme.BOTON_G,
                        ancho=28).pack(pady=4)

        tk.Label(frame, text="Los boletos se guardan en ./tickets",
                 bg=T["panel"], fg=T["texto_suave"],
                 font=theme.TEXTO_F).pack()

    # ---------------------------------------------------------------- #
    #                          Módulo 1: cartelera                      #
    # ---------------------------------------------------------------- #
    def _v_peliculas(self):
        win = self._nueva_ventana("Cartelera de películas", 720, 430)
        peliculas = self.servicio.listar_peliculas()
        filas = [[p.titulo, p.genero, f"{p.duracion_min} min",
                  p.clasificacion, f"${p.precio_base:.2f}",
                  "En cartelera" if p.activa else "Retirada"]
                 for p in peliculas]
        cuerpo, _ = theme.crear_tabla(win, COL_PELICULA, filas)
        cuerpo.pack(fill="both", expand=True, padx=16, pady=8)
        if not peliculas:
            aviso(win, "No hay películas en cartelera.")
        theme.boton(win, "Cerrar", win.destroy, "panel", ancho=14).pack(pady=10)

    # ---------------------------------------------------------------- #
    #                    Módulo 2: comprar boletos                       #
    # ---------------------------------------------------------------- #
    def _v_comprar(self):
        win = self._nueva_ventana("Comprar boletos", 720, 760)
        form = theme.marco(win, relleno=16)
        form.pack(fill="x", padx=16, pady=10)

        opciones = self._opciones_funciones()
        cb_funcion = theme.combobox(form, opciones, 44)
        en_nombre = theme.entrada(form, 42)
        en_edad = theme.entrada(form, 20)

        tk.Label(form, text="Función", bg=T["panel"], fg=T["morado"],
                 font=theme.ETIQUETA).grid(row=0, column=0, sticky="w",
                                           pady=3)
        cb_funcion.grid(row=0, column=1, sticky="we", padx=6)
        tk.Label(form, text="Cliente", bg=T["panel"], fg=T["morado"],
                 font=theme.ETIQUETA).grid(row=1, column=0, sticky="w",
                                           pady=3)
        en_nombre.grid(row=1, column=1, sticky="we", padx=6)
        tk.Label(form, text="Edad", bg=T["panel"], fg=T["morado"],
                 font=theme.ETIQUETA).grid(row=2, column=0, sticky="w",
                                           pady=3)
        en_edad.grid(row=2, column=1, sticky="w", padx=6)
        form.columnconfigure(1, weight=1)

        zona_mapa = tk.Frame(win, bg=T["panel"])
        zona_mapa.pack(padx=16, pady=(4, 0))

        lbl_asientos = tk.Label(
            win, text="0 asientos seleccionados — elige la función y haz "
                      "clic en la sala", bg=T["fondo"],
            fg=T["texto_suave"], font=theme.TEXTO_F)
        lbl_asientos.pack(pady=4)

        estado_mapa = {"seleccion": set()}

        def actualizar_lbl(seleccion):
            estado_mapa["seleccion"] = set(seleccion)
            if seleccion:
                lista = ", ".join(sorted(seleccion))
                lbl_asientos.configure(
                    text=f"{len(seleccion)} asiento(s): {lista}",
                    fg=T["cian"])
            else:
                lbl_asientos.configure(
                    text="0 asientos seleccionados — clic en asientos verdes",
                    fg=T["texto_suave"])

        def cargar_mapa():
            for w in zona_mapa.winfo_children():
                w.destroy()
            actualizar_lbl(set())
            if not cb_funcion.get():
                tk.Label(zona_mapa, text="Selecciona una función para ver "
                                         "la sala", bg=T["panel"],
                         fg=T["texto_suave"], font=theme.TEXTO_F).pack()
                return
            f = self.servicio.obtener_funcion(funcion_id())
            theme.mapa_asientos(zona_mapa, self._filas_asientos(f.id),
                                on_change=actualizar_lbl)

        def funcion_id():
            texto = cb_funcion.get()
            if not texto:
                raise ErrorNegocio("Selecciona una función.")
            return int(texto.split("·")[0].strip().lstrip("#"))

        def leer(var, campo):
            try:
                return int(var.get().strip())
            except ValueError:
                raise ErrorNegocio(f"{campo} debe ser un número entero.") \
                    from None

        def calcular():
            try:
                f = self.servicio.obtener_funcion(funcion_id())
                p = self.servicio.obtener_pelicula(f.pelicula_id)
                seleccion = estado_mapa["seleccion"]
                if not seleccion:
                    raise ErrorNegocio("Selecciona al menos un asiento.")
                cantidad = len(seleccion)
                edad = leer(en_edad, "La edad")
                cliente = Cliente(en_nombre.get() or "Cliente", edad)
                if not cliente.validar_clasificacion(p.clasificacion):
                    raise ErrorNegocio(
                        f"{p.titulo} es clasificación {p.clasificacion} "
                        f"y requiere edad mínima de "
                        f"{edad_minima_clasificacion(p.clasificacion)} años.")
                desc = cliente.calcular_descuento()
                total = round(cantidad * p.precio_base * (1 - desc), 2)
                aviso(win,
                      f"{cliente.nombre} ({edad} años) · {cantidad} "
                      f"boleto(s) × ${p.precio_base:.2f} · descuento "
                      f"{desc * 100:.0f}% · TOTAL ${total:.2f}", True)
            except (ErrorNegocio, ValueError) as e:
                aviso(win, str(e), False)

        def confirmar():
            try:
                cliente = Cliente(en_nombre.get(),
                                  leer(en_edad, "La edad"))
                seleccion = sorted(estado_mapa["seleccion"])
                if not seleccion:
                    raise ErrorNegocio("Selecciona al menos un asiento.")
                venta = self.servicio.comprar_boletos(
                    funcion_id(), cliente, seleccion)
                detalle = self.servicio.detalle_venta(venta.folio)
                ruta = TicketPDF().generar(detalle)
                aviso(win,
                      f"Compra registrada. Folio {venta.folio} · Asientos: "
                      f"{', '.join(seleccion)} · Total ${venta.total:.2f}.\n"
                      f"Ticket: {ruta}", True)
                theme.boton(win, "Abrir ticket PDF",
                            lambda: theme.abrir_archivo(ruta), "verde",
                            ancho=18).pack(pady=4)
                cb_funcion["values"] = self._opciones_funciones()
                cargar_mapa()
            except (ErrorNegocio, ValueError) as e:
                aviso(win, str(e), False)

        tk.Label(win, text="Asientos (clic para elegir)", bg=T["fondo"],
                 fg=T["morado"], font=theme.ETIQUETA).pack(anchor="w",
                                                           padx=20)
        cb_funcion.bind("<<ComboboxSelected>>",
                        lambda e: cargar_mapa())
        bienvenida = tk.Label(zona_mapa, text="Selecciona una función para "
                                              "ver la sala", bg=T["panel"],
                              fg=T["texto_suave"], font=theme.TEXTO_F)
        bienvenida.pack(pady=6)
        botones = tk.Frame(win, bg=T["fondo"])
        botones.pack(pady=6)
        theme.boton(botones, "Calcular", calcular, "cian",
                    ancho=14).pack(side="left", padx=6)
        theme.boton(botones, "Confirmar compra", confirmar, "rosa",
                    ancho=14).pack(side="left", padx=6)

    def _filas_asientos(self, funcion_id):
        """Agrupa los asientos de una función por fila para el mapa."""
        filas = []
        actual = None
        for a in self.servicio.listar_asientos(funcion_id):
            if actual is None or actual["letra"] != a["fila"]:
                actual = {"letra": a["fila"], "asientos": []}
                filas.append(actual)
            actual["asientos"].append(a)
        return filas

    def _opciones_funciones(self):
        opciones = []
        for f in self.servicio.listar_funciones():
            p = self.servicio.obtener_pelicula(f.pelicula_id)
            opciones.append(
                f"#{f.id} · {p.titulo} · {f.sala} · {f.horario} · "
                f"{f.disponibles} libres")
        return opciones

    # ---------------------------------------------------------------- #
    #                       Módulo 3: lugares libres                     #
    # ---------------------------------------------------------------- #
    def _v_lugares(self):
        win = self._nueva_ventana("Lugares disponibles", 660, 430)
        filas = []
        for f in self.servicio.listar_funciones():
            p = self.servicio.obtener_pelicula(f.pelicula_id)
            filas.append([f.id, p.titulo, f.sala, f.horario, f.capacidad,
                          f.ocupados, f.disponibles])
        cuerpo, _ = theme.crear_tabla(win, COL_FUNCION, filas)
        cuerpo.pack(fill="both", expand=True, padx=16, pady=8)
        theme.boton(win, "Cerrar", win.destroy, "panel", ancho=14).pack(pady=10)

    # ---------------------------------------------------------------- #
    #                        Módulo 4: cancelar compra                   #
    # ---------------------------------------------------------------- #
    def _v_cancelar(self):
        win = self._nueva_ventana("Cancelar compra", 480, 280)
        form = theme.marco(win, relleno=16)
        form.pack(fill="x", padx=16, pady=16)
        tk.Label(form, text="Folio a cancelar", bg=T["panel"],
                 fg=T["ambar"], font=theme.ETIQUETA).pack(anchor="w")
        en_folio = theme.entrada(form, 42)
        en_folio.pack(fill="x", pady=(4, 12))

        def hacer():
            try:
                venta = self.servicio.cancelar_compra(en_folio.get())
                aviso(win, f"Compra {venta.folio} cancelada. Sus lugares se "
                           f"liberaron.", True)
            except ErrorNegocio as e:
                aviso(win, str(e), False)

        theme.boton(form, "Cancelar compra", hacer, "ambar",
                    ancho=18).pack()

    # ---------------------------------------------------------------- #
    #                         Módulo 5: historial                        #
    # ---------------------------------------------------------------- #
    def _v_ventas(self):
        win = self._nueva_ventana("Historial de ventas", 880, 480)
        ventas = self.servicio.ventas_detalladas()
        filas = [[v["folio"], v["fecha_hora"], v["pelicula_titulo"],
                  v["sala"], v["horario"], v["cliente_nombre"], v["edad"],
                  v["cantidad_boletos"], f"${v['precio_unitario']:.2f}",
                  f"{v['descuento_pct'] * 100:.0f}%",
                  f"${v['total']:.2f}", v["estado"]] for v in ventas]
        cuerpo, _ = theme.crear_tabla(win, COL_VENTA, filas)
        cuerpo.pack(fill="both", expand=True, padx=16, pady=8)
        if not ventas:
            aviso(win, "Todavía no hay ventas.")
        theme.boton(win, "Cerrar", win.destroy, "panel", ancho=14).pack(pady=10)

    # ---------------------------------------------------------------- #
    #                              Utilidades                            #
    # ---------------------------------------------------------------- #
    def _nueva_ventana(self, titulo, ancho, alto):
        win = tk.Toplevel(self.raiz)
        theme.aplicar_raiz(win, titulo)
        win.geometry(f"{ancho}x{alto}")
        win.transient(self.raiz)
        win.grab_set()
        self.ventanas_abiertas.append(win)
        return win

    def salir(self):
        for w in self.ventanas_abiertas:
            if w.winfo_exists():
                w.destroy()
        self.destroy()