"""Lanzador de Cinema: elige entre la interfaz de usuario y el panel de
administración (protegido por login). Crea carpetas, la base de datos y (si
está vacía) un catálogo de ejemplo.
"""

import tkinter as tk

from backend.auth import validar_login
from backend.models import CineService, sembrar_demo
from frontend import theme
from frontend.app_usuario import AppUsuario
from panel.app_admin import AppAdmin

T = theme.PALETA


class Lanzador:
    def __init__(self):
        self.servicio = CineService()
        sembrar_demo(self.servicio)

        self.raiz = tk.Tk()
        theme.aplicar_raiz(self.raiz, "Cinema")
        self.raiz.geometry("460x340")
        self.raiz.resizable(False, False)

        frame = theme.marco(self.raiz, relleno=24)
        frame.pack(padx=24, pady=24, fill="both", expand=True)

        theme.titulo_neon(frame).pack(pady=(0, 2))
        tk.Label(frame, text="Cinema", bg=T["panel"],
                 fg=T["morado"], font=theme.SUBTITULO).pack()

        area = tk.Frame(frame, bg=T["panel"])
        area.pack(pady=16)
        theme.boton(area, "Usuario", self.abrir_usuario, "rosa",
                    tamano=theme.BOTON_G, ancho=26).pack(pady=5)
        theme.boton(area, "Administración", self.abrir_admin, "cian",
                    tamano=theme.BOTON_G, ancho=26).pack(pady=5)

        tk.Label(frame, text="Datos: ./data · Tickets: ./tickets · "
                             "Reportes: ./reportes",
                 bg=T["panel"], fg=T["texto_suave"],
                 font=(theme.FUENTE, 9)).pack()

        self.ventanas = []

    def abrir_usuario(self):
        self.ventanas.append(AppUsuario(self.raiz, self.servicio))
        self.raiz.lower()

    def abrir_admin(self):
        self._pedir_login()

    def _pedir_login(self):
        """Diálogo de credenciales antes de abrir el panel de administración."""
        win = tk.Toplevel(self.raiz)
        theme.aplicar_raiz(win, "Cinema · Acceso administrador")
        win.geometry("380x280")
        win.transient(self.raiz)
        win.grab_set()
        self.ventanas.append(win)

        form = theme.marco(win, relleno=16)
        form.pack(fill="x", padx=18, pady=18)

        en_usuario = theme.entrada(form, 30)
        en_clave = theme.entrada(form, 30)
        en_clave.configure(show="*")

        campos = [("Usuario", en_usuario), ("Contraseña", en_clave)]
        for i, (texto, widget) in enumerate(campos):
            tk.Label(form, text=texto, bg=T["panel"], fg=T["cian"],
                     font=theme.ETIQUETA).grid(row=i, column=0, sticky="w",
                                               pady=4)
            widget.grid(row=i, column=1, sticky="we", padx=6)
        form.columnconfigure(1, weight=1)

        def aviso_login(texto, ok=True):
            for w in win.winfo_children():
                if getattr(w, "_es_aviso_login", False):
                    w.destroy()
            etiqueta = tk.Label(win, text=texto, bg=T["fondo"],
                                fg=T["verde"] if ok else T["rojo"],
                                font=(theme.FUENTE, 10, "bold"))
            etiqueta._es_aviso_login = True
            etiqueta.pack(pady=(0, 4))

        def ingresar(_e=None):
            if validar_login(en_usuario.get().strip(), en_clave.get()):
                win.destroy()
                self.ventanas.remove(win)
                self.abrir_admin_libre()
            else:
                aviso_login("Credenciales incorrectas.", False)

        en_clave.bind("<Return>", ingresar)
        botones = tk.Frame(win, bg=T["fondo"])
        botones.pack(pady=6)
        theme.boton(botones, "Ingresar", ingresar, "cian", ancho=14).pack(
            side="left", padx=6)
        theme.boton(botones, "Cancelar", win.destroy, "rojo", ancho=14).pack(
            side="left", padx=6)

    def abrir_admin_libre(self):
        self.ventanas.append(AppAdmin(self.raiz, self.servicio))
        self.raiz.lower()

    def ejecutar(self):
        self.raiz.mainloop()


def main():
    Lanzador().ejecutar()


if __name__ == "__main__":
    main()