"""Menu de configuracion previo a la mision (seccion 9): tres ajustes + Start.

Layout en columna (etiqueta arriba, control full-width abajo) para que los botones
segmentados NO se corten con el escalado/DPI de Windows. Toma los defaults de
config.toml; con autostart=true la app lo saltea (kiosco).
"""
from __future__ import annotations

import customtkinter as ctk

from app.ui import theme

_ENGINE_LABELS = {"Simulado": "simulated", "Real": "real"}
_ENGINE_LABELS_INV = {v: k for k, v in _ENGINE_LABELS.items()}
_DIFF_LABELS = {"Facil": "facil", "Medio": "medio", "Dificil": "dificil", "Pro": "pro"}
_DIFF_LABELS_INV = {v: k for k, v in _DIFF_LABELS.items()}
_VISUAL_LABELS = {"Encendido": True, "Apagado": False}
_VISUAL_LABELS_INV = {True: "Encendido", False: "Apagado"}


class SetupMenu(ctk.CTkFrame):
    def __init__(self, parent, cfg, on_start):
        super().__init__(parent, fg_color=theme.BG)
        self.cfg = cfg
        self.on_start = on_start

        wrap = ctk.CTkFrame(self, fg_color=theme.BG_PANEL, corner_radius=16,
                            border_color=theme.GREEN, border_width=2)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        # ancho minimo garantizado para que los botones segmentados NO se corten;
        # el alto se ajusta solo al contenido (sin fijarlo a mano).
        wrap.grid_columnconfigure(0, weight=1, minsize=560)

        row = [0]

        def add(widget, pady=(0, 4), padx=40):
            widget.grid(row=row[0], column=0, sticky="ew", padx=padx, pady=pady)
            row[0] += 1

        add(ctk.CTkLabel(wrap, text="C Y B E R   L A B", text_color=theme.GREEN,
                         font=("Consolas", 34, "bold")), pady=(30, 2))
        add(ctk.CTkLabel(wrap, text="Configuracion de la estacion", text_color=theme.DIM,
                         font=("Consolas", 14)), pady=(0, 22))

        # --- Panel visual ---
        add(ctk.CTkLabel(wrap, text="Panel visual (mapa de red)", text_color=theme.FG,
                         font=("Consolas", 15), anchor="w"), pady=(6, 4))
        self.visual_seg = ctk.CTkSegmentedButton(
            wrap, values=list(_VISUAL_LABELS.keys()), height=40,
            font=("Consolas", 15), selected_color=theme.GREEN,
            selected_hover_color=theme.GREEN)
        self.visual_seg.set(_VISUAL_LABELS_INV.get(bool(cfg.modes.visual), "Encendido"))
        add(self.visual_seg, pady=(0, 14))

        # --- Motor ---
        add(ctk.CTkLabel(wrap, text="Motor de ejecucion", text_color=theme.FG,
                         font=("Consolas", 15), anchor="w"), pady=(6, 4))
        self.engine_seg = ctk.CTkSegmentedButton(
            wrap, values=list(_ENGINE_LABELS.keys()), height=40,
            font=("Consolas", 15), selected_color=theme.GREEN,
            selected_hover_color=theme.GREEN)
        self.engine_seg.set(_ENGINE_LABELS_INV.get(cfg.modes.engine, "Simulado"))
        add(self.engine_seg, pady=(0, 14))

        # --- Dificultad ---
        add(ctk.CTkLabel(wrap, text="Dificultad", text_color=theme.FG,
                         font=("Consolas", 15), anchor="w"), pady=(6, 4))
        self.diff_seg = ctk.CTkSegmentedButton(
            wrap, values=list(_DIFF_LABELS.keys()), height=44,
            font=("Consolas", 16, "bold"), selected_color=theme.GREEN,
            selected_hover_color=theme.GREEN)
        self.diff_seg.set(_DIFF_LABELS_INV.get(cfg.modes.difficulty, "Facil"))
        add(self.diff_seg, pady=(0, 4))
        add(ctk.CTkLabel(
            wrap,
            text="Facil: comando+IP   Medio: por concepto   Dificil: comandos reales   Pro: solo",
            text_color=theme.DIM, font=("Consolas", 11), anchor="w"), pady=(0, 8))

        # --- Start ---
        start = ctk.CTkButton(wrap, text="COMENZAR", fg_color=theme.GREEN, hover_color="#2ecc12",
                              text_color="#04140a", font=("Consolas", 20, "bold"), height=52,
                              command=self._start)
        add(start, pady=(14, 30))

    def _start(self):
        self.cfg.modes.visual = _VISUAL_LABELS.get(self.visual_seg.get(), True)
        self.cfg.modes.engine = _ENGINE_LABELS.get(self.engine_seg.get(), "simulated")
        self.cfg.modes.difficulty = _DIFF_LABELS.get(self.diff_seg.get(), "facil")
        self.on_start()
