"""Vista de TARJETAS: la experiencia sin teclado, para quien no sabe nada de redes.

Una sola accion grande por pantalla. El visitante toca un boton enorme, el tablero
de LEDs y el overlay de suspenso hacen el show, y una frase en lenguaje de todos los
dias explica que logro. Nunca tiene que escribir ni saber cual es el proximo paso:
el unico boton activo ES el proximo paso.

La vista es "tonta": muestra lo que el TarjetasController le pide (render_step /
set_busy / show_result / render_done) y avisa los toques por on_action().
"""
from __future__ import annotations

import customtkinter as ctk

from app.ui import theme

_BEATS = ("MIRAR", "ENTRAR", "LLEVARSE")


class TarjetasView(ctk.CTkFrame):
    def __init__(self, parent, mono_font, on_action=None):
        super().__init__(parent, fg_color=theme.BG)
        self.mono = mono_font
        self.on_action = on_action

        wrap = ctk.CTkFrame(self, fg_color=theme.BG)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        wrap.grid_columnconfigure(0, weight=1, minsize=640)
        r = [0]

        def add(w, pady=(0, 6)):
            w.grid(row=r[0], column=0, sticky="ew", padx=30, pady=pady)
            r[0] += 1

        add(ctk.CTkLabel(wrap, text="MISION:  RECUPERAR EL ARCHIVO SECRETO",
                         text_color=theme.DIM, font=(mono_font, 15)), pady=(0, 16))

        # --- seguimiento de los 3 golpes ---
        track = ctk.CTkFrame(wrap, fg_color=theme.BG)
        track.grid(row=r[0], column=0, pady=(0, 24)); r[0] += 1
        self._beat_lbl = {}
        for i, b in enumerate(_BEATS):
            if i:
                ctk.CTkLabel(track, text="  >  ", text_color=theme.DIM,
                             font=(mono_font, 16)).pack(side="left")
            lbl = ctk.CTkLabel(track, text=b, text_color=theme.DIM,
                               font=(mono_font, 16, "bold"))
            lbl.pack(side="left")
            self._beat_lbl[b] = lbl

        # --- paso actual ---
        self.step_badge = ctk.CTkLabel(wrap, text="", text_color=theme.CYAN,
                                       font=(mono_font, 14, "bold"))
        add(self.step_badge, pady=(0, 2))
        self.desc = ctk.CTkLabel(wrap, text="", text_color=theme.FG, font=(mono_font, 20),
                                 wraplength=620, justify="center")
        add(self.desc, pady=(0, 22))

        self.btn = ctk.CTkButton(wrap, text="", command=self._clicked,
                                 fg_color=theme.GREEN, hover_color="#2ecc12",
                                 text_color="#04140a", font=(mono_font, 30, "bold"),
                                 height=130, corner_radius=18)
        add(self.btn, pady=(0, 18))

        self.result = ctk.CTkLabel(wrap, text="", text_color=theme.WHITE,
                                   font=(mono_font, 17), wraplength=640, justify="center")
        add(self.result, pady=(0, 10))

    # ------------------------------------------------------------------
    def _clicked(self):
        if self.on_action:
            self.on_action()

    def set_beat(self, beat):
        for b, lbl in self._beat_lbl.items():
            active = (b == beat)
            lbl.configure(text_color=theme.GREEN if active else theme.DIM,
                          font=(self.mono, 16, "bold"))

    def render_step(self, beat, title, desc, badge="", button=None):
        self.set_beat(beat)
        self.step_badge.configure(text=badge)
        self.desc.configure(text=desc, text_color=theme.FG)
        self.result.configure(text="")
        self.btn.configure(text=button or title, state="normal",
                           fg_color=theme.GREEN, text_color="#04140a")

    def set_busy(self, text="PROCESANDO..."):
        self.btn.configure(text=text, state="disabled", fg_color=theme.DIM)

    def show_result(self, text, color=None):
        self.result.configure(text=text, text_color=color or theme.WHITE)

    def render_done(self, title, lesson, button="JUGAR DE NUEVO"):
        for b, lbl in self._beat_lbl.items():
            lbl.configure(text_color=theme.GREEN)
        self.step_badge.configure(text="MISION CUMPLIDA")
        self.desc.configure(text=title, text_color=theme.GREEN)
        self.result.configure(text=lesson, text_color=theme.WHITE)
        self.btn.configure(text=button, state="normal",
                           fg_color=theme.CYAN, text_color="#04140a")
