"""Lanzador de Cine Neón: elige entre la interfaz de usuario y el panel de
administración. Crea carpetas, la base de datos y (si está vacía) un
catálogo de ejemplo.
"""

import tkinter as tk

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
        theme.aplicar_raiz(self.raiz, "Cine Neón")
        self.raiz.geometry("460x340")
        self.raiz.resizable(False, False)

        frame = theme.marco(self.raiz, relleno=24)
        frame.pack(padx=24, pady=24, fill="both", expand=True)

        theme.titulo_neon(frame).pack(pady=(0, 2))
        tk.Label(frame, text="Sistema de boletos", bg=T["panel"],
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

    def abrir_admin(self):
        self.ventanas.append(AppAdmin(self.raiz, self.servicio))

    def ejecutar(self):
        self.raiz.mainloop()


def main():
    Lanzador().ejecutar()


if __name__ == "__main__":
    main()