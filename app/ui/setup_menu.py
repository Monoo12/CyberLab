"""Menu de configuracion previo a la mision (seccion 9): tres toggles + Start.

Toma los defaults de config.toml; con autostart=true la app lo saltea (kiosco).
"""
from __future__ import annotations

import customtkinter as ctk

from app.ui import theme

_ENGINE_LABELS = {"Simulado": "simulated", "Real": "real"}
_ENGINE_LABELS_INV = {v: k for k, v in _ENGINE_LABELS.items()}
_DIFF_LABELS = {"Facil": "facil", "Medio": "medio", "Dificil": "dificil", "Pro": "pro"}
_DIFF_LABELS_INV = {v: k for k, v in _DIFF_LABELS.items()}


class SetupMenu(ctk.CTkFrame):
    def __init__(self, parent, cfg, on_start):
        super().__init__(parent, fg_color=theme.BG)
        self.cfg = cfg
        self.on_start = on_start

        wrap = ctk.CTkFrame(self, fg_color=theme.BG_PANEL, corner_radius=16,
                            border_color=theme.GREEN, border_width=2)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(wrap, text="C Y B E R   L A B", text_color=theme.GREEN,
                     font=("Consolas", 34, "bold")).grid(row=0, column=0, columnspan=2,
                                                          padx=48, pady=(34, 4))
        ctk.CTkLabel(wrap, text="Configuracion de la estacion", text_color=theme.DIM,
                     font=("Consolas", 14)).grid(row=1, column=0, columnspan=2, pady=(0, 24))

        # Panel visual
        ctk.CTkLabel(wrap, text="Panel visual (mapa de red)", text_color=theme.FG,
                     font=("Consolas", 15)).grid(row=2, column=0, sticky="w", padx=(36, 20), pady=12)
        self.visual_sw = ctk.CTkSwitch(wrap, text="", progress_color=theme.GREEN,
                                       onvalue=True, offvalue=False)
        self.visual_sw.grid(row=2, column=1, sticky="e", padx=(20, 36))
        (self.visual_sw.select if cfg.modes.visual else self.visual_sw.deselect)()

        # Motor
        ctk.CTkLabel(wrap, text="Motor de ejecucion", text_color=theme.FG,
                     font=("Consolas", 15)).grid(row=3, column=0, sticky="w", padx=(36, 20), pady=12)
        self.engine_seg = ctk.CTkSegmentedButton(
            wrap, values=list(_ENGINE_LABELS.keys()),
            selected_color=theme.GREEN, selected_hover_color=theme.GREEN)
        self.engine_seg.set(_ENGINE_LABELS_INV.get(cfg.modes.engine, "Simulado"))
        self.engine_seg.grid(row=3, column=1, sticky="e", padx=(20, 36))

        # Dificultad
        ctk.CTkLabel(wrap, text="Dificultad", text_color=theme.FG,
                     font=("Consolas", 15)).grid(row=4, column=0, sticky="w", padx=(36, 20), pady=12)
        self.diff_seg = ctk.CTkSegmentedButton(
            wrap, values=list(_DIFF_LABELS.keys()),
            selected_color=theme.GREEN, selected_hover_color=theme.GREEN)
        self.diff_seg.set(_DIFF_LABELS_INV.get(cfg.modes.difficulty, "Facil"))
        self.diff_seg.grid(row=4, column=1, sticky="e", padx=(20, 36))
        ctk.CTkLabel(wrap,
                     text="Facil: comando+IP  ·  Medio: por concepto  ·  Dificil: comandos reales  ·  Pro: solo",
                     text_color=theme.DIM, font=("Consolas", 11)).grid(
            row=5, column=0, columnspan=2, pady=(0, 6))

        start = ctk.CTkButton(wrap, text="COMENZAR", fg_color=theme.GREEN, hover_color="#2ecc12",
                              text_color="#04140a", font=("Consolas", 18, "bold"),
                              command=self._start)
        start.grid(row=6, column=0, columnspan=2, pady=(22, 34), ipadx=30, ipady=6)

    def _start(self):
        self.cfg.modes.visual = bool(self.visual_sw.get())
        self.cfg.modes.engine = _ENGINE_LABELS.get(self.engine_seg.get(), "simulated")
        self.cfg.modes.difficulty = _DIFF_LABELS.get(self.diff_seg.get(), "facil")
        self.on_start()
