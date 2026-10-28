"""Vista de TARJETAS: la experiencia sin teclado, para quien no sabe nada de redes.

Dos tipos de pantalla:
  - ACCION grande (un boton enorme): escanear, entrar.
  - GRILLA de opciones (tocar una tarjeta): elegir el servidor entre los equipos,
    y despues explorar las carpetas del servidor para encontrar y abrir el archivo.

Asi deja de ser "apretar 4 veces" y pasa a ser un jueguito: el visitante decide
que tocar. La vista es "tonta": muestra lo que el TarjetasController le pide y avisa
los toques por on_action() (boton grande) / on_choice(key) (grilla) / on_restart().
"""
from __future__ import annotations

import customtkinter as ctk

from app.ui import responsive, theme

_BEATS = ("MIRAR", "ENTRAR", "LLEVARSE")


class TarjetasView(ctk.CTkFrame):
    def __init__(self, parent, mono_font, on_action=None, on_choice=None, on_restart=None):
        super().__init__(parent, fg_color=theme.BG)
        self.mono = mono_font
        self.on_action = on_action
        self.on_choice = on_choice
        self.on_restart = on_restart

        wrap = ctk.CTkFrame(self, fg_color=theme.BG)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        wrap.grid_columnconfigure(0, weight=1)
        responsive.bind_minsize(wrap, 0, 680)
        self._wrap = wrap
        r = [0]

        def add(w, pady=(0, 6)):
            w.grid(row=r[0], column=0, sticky="ew", padx=30, pady=pady)
            r[0] += 1

        add(ctk.CTkLabel(wrap, text="MISION:  RECUPERAR EL ARCHIVO SECRETO",
                         text_color=theme.DIM, font=(mono_font, 15)), pady=(0, 14))

        track = ctk.CTkFrame(wrap, fg_color=theme.BG)
        track.grid(row=r[0], column=0, pady=(0, 22)); r[0] += 1
        self._beat_lbl = {}
        for i, b in enumerate(_BEATS):
            if i:
                ctk.CTkLabel(track, text="  >  ", text_color=theme.DIM,
                             font=(mono_font, 16)).pack(side="left")
            lbl = ctk.CTkLabel(track, text=b, text_color=theme.DIM, font=(mono_font, 16, "bold"))
            lbl.pack(side="left")
            self._beat_lbl[b] = lbl

        self.step_badge = ctk.CTkLabel(wrap, text="", text_color=theme.CYAN,
                                       font=(mono_font, 14, "bold"))
        add(self.step_badge, pady=(0, 2))
        self.desc = ctk.CTkLabel(wrap, text="", text_color=theme.FG, font=(mono_font, 20),
                                 wraplength=660, justify="center")
        add(self.desc, pady=(0, 20))

        # boton grande (acciones de un solo toque)
        self.btn = ctk.CTkButton(wrap, text="", command=self._clicked,
                                 fg_color=theme.GREEN, hover_color="#2ecc12",
                                 text_color="#04140a", font=(mono_font, 30, "bold"),
                                 height=130, corner_radius=18)
        self._btn_row = r[0]
        self.btn.grid(row=r[0], column=0, sticky="ew", padx=30, pady=(0, 18)); r[0] += 1

        # grilla de opciones (elegir equipo / explorar carpetas)
        self.grid_box = ctk.CTkFrame(wrap, fg_color=theme.BG)
        self.grid_box.grid(row=r[0], column=0, sticky="ew", padx=20, pady=(0, 14))
        self.grid_box.grid_columnconfigure((0, 1), weight=1)
        self.grid_box.grid_remove()
        r[0] += 1

        self.result = ctk.CTkLabel(wrap, text="", text_color=theme.WHITE, font=(mono_font, 17),
                                   wraplength=660, justify="center")
        add(self.result, pady=(0, 10))

    # ------------------------------------------------------------------
    def _clicked(self):
        if self.on_action:
            self.on_action()

    def _choose(self, key):
        if self.on_choice:
            self.on_choice(key)

    def set_beat(self, beat):
        for b, lbl in self._beat_lbl.items():
            lbl.configure(text_color=theme.GREEN if b == beat else theme.DIM)

    def _show_single(self):
        self.grid_box.grid_remove()
        self.btn.grid()

    def _show_grid(self):
        self.btn.grid_remove()
        self.grid_box.grid()

    def _clear_grid(self):
        for w in self.grid_box.winfo_children():
            w.destroy()

    def render_step(self, beat, title, desc, badge="", button=None):
        """Pantalla de accion: un boton grande."""
        self.set_beat(beat)
        self.step_badge.configure(text=badge)
        self.desc.configure(text=desc, text_color=theme.FG)
        self.result.configure(text="")
        self.btn.configure(text=button or title, state="normal",
                           fg_color=theme.GREEN, text_color="#04140a")
        self._show_single()

    def render_grid(self, beat, desc, items, badge=""):
        """Pantalla de eleccion: una tarjeta por item. items: [{label,key,is_dir?}]."""
        self.set_beat(beat)
        self.step_badge.configure(text=badge)
        self.desc.configure(text=desc, text_color=theme.FG)
        self.result.configure(text="")
        self._clear_grid()
        for i, it in enumerate(items):
            is_dir = it.get("is_dir")
            color = theme.CYAN if is_dir else theme.GREEN
            b = ctk.CTkButton(self.grid_box, text=it["label"],
                              command=lambda k=it["key"]: self._choose(k),
                              fg_color=theme.BG_PANEL, hover_color="#163b16",
                              border_color=color, border_width=2, text_color=theme.FG,
                              font=(self.mono, 18, "bold"), height=64)
            b.grid(row=i // 2, column=i % 2, padx=8, pady=8, sticky="ew")
        self._show_grid()

    def set_busy(self, text="PROCESANDO..."):
        self.btn.configure(text=text, state="disabled", fg_color=theme.DIM)
        self._show_single()

    def show_result(self, text, color=None):
        self.result.configure(text=text, text_color=color or theme.WHITE)

    def render_done(self, title, lesson, button="JUGAR DE NUEVO"):
        for lbl in self._beat_lbl.values():
            lbl.configure(text_color=theme.GREEN)
        self.step_badge.configure(text="MISION CUMPLIDA")
        self.desc.configure(text=title, text_color=theme.GREEN)
        self.result.configure(text=lesson, text_color=theme.WHITE)
        self.btn.configure(text=button, state="normal", fg_color=theme.CYAN, text_color="#04140a")
        self._show_single()
