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
_MODE_LABELS = {"Tarjetas": "tarjetas", "Guiado": "guiado", "Experto": "experto", "Reto": "reto"}
_MODE_LABELS_INV = {v: k for k, v in _MODE_LABELS.items()}
_LESSON_LABELS = {"Rotar": "rotar", "Clave debil": "clave",
                  "Dato expuesto": "expuesto", "Truco login": "login"}
_LESSON_LABELS_INV = {v: k for k, v in _LESSON_LABELS.items()}


class SetupMenu(ctk.CTkFrame):
    def __init__(self, parent, cfg, on_start, leds=None):
        super().__init__(parent, fg_color=theme.BG)
        self.cfg = cfg
        self.on_start = on_start
        self.leds = leds
        self._leds_on = True  # al entrar al menu la tira esta en IDLE

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

        # --- Modo de juego (el operador lo fija segun el visitante) ---
        add(ctk.CTkLabel(wrap, text="Modo de juego", text_color=theme.FG,
                         font=("Consolas", 15), anchor="w"), pady=(6, 4))
        self.mode_seg = ctk.CTkSegmentedButton(
            wrap, values=list(_MODE_LABELS.keys()), height=44,
            font=("Consolas", 16, "bold"), selected_color=theme.CYAN,
            selected_hover_color=theme.CYAN, command=self._on_mode_change)
        self.mode_seg.set(_MODE_LABELS_INV.get(cfg.modes.mode, "Experto"))
        add(self.mode_seg, pady=(0, 4))
        add(ctk.CTkLabel(
            wrap,
            text="Tarjetas: sin teclado   Guiado: un Enter   Experto: terminal real   Reto: escape room",
            text_color=theme.DIM, font=("Consolas", 11), anchor="w"), pady=(0, 14))

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
            text_color=theme.DIM, font=("Consolas", 11), anchor="w"), pady=(0, 12))

        # --- Leccion (solo tarjetas/guiado) ---
        add(ctk.CTkLabel(wrap, text="Leccion (tarjetas / guiado)", text_color=theme.FG,
                         font=("Consolas", 15), anchor="w"), pady=(6, 4))
        self.lesson_seg = ctk.CTkSegmentedButton(
            wrap, values=list(_LESSON_LABELS.keys()), height=40,
            font=("Consolas", 14), selected_color=theme.CYAN,
            selected_hover_color=theme.CYAN)
        self.lesson_seg.set(_LESSON_LABELS_INV.get(cfg.modes.lesson, "Rotar"))
        add(self.lesson_seg, pady=(0, 14))

        # --- Modo libre ---
        add(ctk.CTkLabel(wrap, text="Modo libre (tiempo infinito, todo hackeable)",
                         text_color=theme.FG, font=("Consolas", 15), anchor="w"), pady=(6, 4))
        self.free_seg = ctk.CTkSegmentedButton(
            wrap, values=["Mision", "Libre"], height=40,
            font=("Consolas", 15), selected_color=theme.CYAN,
            selected_hover_color=theme.CYAN)
        self.free_seg.set("Libre" if cfg.modes.free_mode else "Mision")
        add(self.free_seg, pady=(0, 12))

        # --- Tira de LEDs (solo si hay controlador habilitado) ---
        if self.leds is not None and getattr(self.leds, "enabled", False):
            self.leds_btn = ctk.CTkButton(
                wrap, text="APAGAR LEDS", fg_color=theme.BG_PANEL, hover_color="#222",
                text_color=theme.DIM, border_color=theme.DIM, border_width=1,
                font=("Consolas", 14), height=38, command=self._toggle_leds)
            add(self.leds_btn, pady=(2, 10))

        # --- Start ---
        start = ctk.CTkButton(wrap, text="COMENZAR", fg_color=theme.GREEN, hover_color="#2ecc12",
                              text_color="#04140a", font=("Consolas", 20, "bold"), height=52,
                              command=self._start)
        add(start, pady=(14, 30))

        self._on_mode_change()  # estado inicial de dificultad/leccion segun el modo

    def _toggle_leds(self):
        if self.leds is None:
            return
        try:
            if self._leds_on:
                self.leds.off()
                self._leds_on = False
                self.leds_btn.configure(text="ENCENDER LEDS", text_color=theme.GREEN,
                                        border_color=theme.GREEN)
            else:
                self.leds.idle()
                self._leds_on = True
                self.leds_btn.configure(text="APAGAR LEDS", text_color=theme.DIM,
                                        border_color=theme.DIM)
        except Exception:
            pass

    def _on_mode_change(self, value=None):
        """Habilita solo los controles que aplican al modo elegido:
        dificultad -> solo EXPERTO; leccion -> solo TARJETAS/GUIADO."""
        mode = _MODE_LABELS.get(self.mode_seg.get(), "experto")
        diff_state = "normal" if mode == "experto" else "disabled"
        lesson_state = "normal" if mode in ("tarjetas", "guiado") else "disabled"
        for widget, state in ((self.diff_seg, diff_state), (self.lesson_seg, lesson_state)):
            try:
                widget.configure(state=state)
            except Exception:
                pass

    def _start(self):
        self.cfg.modes.visual = _VISUAL_LABELS.get(self.visual_seg.get(), True)
        self.cfg.modes.engine = _ENGINE_LABELS.get(self.engine_seg.get(), "simulated")
        self.cfg.modes.mode = _MODE_LABELS.get(self.mode_seg.get(), "experto")
        self.cfg.modes.difficulty = _DIFF_LABELS.get(self.diff_seg.get(), "facil")
        self.cfg.modes.lesson = _LESSON_LABELS.get(self.lesson_seg.get(), "rotar")
        self.cfg.modes.free_mode = (self.free_seg.get() == "Libre")
        self.on_start()
