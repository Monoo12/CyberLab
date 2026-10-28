"""Menu de configuracion previo a la mision (seccion 9): tres ajustes + Start.

Cada ajuste es un bloque (etiqueta arriba, control full-width abajo) para que los
botones segmentados NO se corten con el escalado/DPI de Windows. Los bloques van en
una columna (pantallas altas) o en dos (apaisadas, p.ej. notebooks 1366x768), segun
el lienzo que elija app/ui/responsive.py. Toma los defaults de config.toml; con
autostart=true la app lo saltea (kiosco).
"""
from __future__ import annotations

import customtkinter as ctk

from app.ui import responsive, theme

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
    # Lienzos (px logicos a escala 1; ver app/ui/responsive.py):
    # 0 = una columna (pantallas altas), 1 = dos columnas (apaisadas).
    DESIGNS = ((700, 940), (1320, 640))

    def __init__(self, parent, cfg, on_start, leds=None):
        super().__init__(parent, fg_color=theme.BG)
        self.cfg = cfg
        self.on_start = on_start
        self.leds = leds
        self._leds_on = True  # al entrar al menu la tira esta en IDLE

        wrap = ctk.CTkFrame(self, fg_color=theme.BG_PANEL, corner_radius=16,
                            border_color=theme.GREEN, border_width=2)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        self._wrap = wrap

        def block(title, hint=None):
            """Bloque de un ajuste: etiqueta (fila 0), control (fila 1, lo pone quien
            llama) y ayuda opcional (fila 2)."""
            b = ctk.CTkFrame(wrap, fg_color="transparent")
            b.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(b, text=title, text_color=theme.FG, font=("Consolas", 15),
                         anchor="w").grid(row=0, column=0, sticky="ew", pady=(0, 4))
            if hint:
                ctk.CTkLabel(b, text=hint, text_color=theme.DIM, font=("Consolas", 11),
                             anchor="w", justify="left", wraplength=540
                             ).grid(row=2, column=0, sticky="ew", pady=(4, 0))
            return b

        head = ctk.CTkFrame(wrap, fg_color="transparent")
        ctk.CTkLabel(head, text="C Y B E R   L A B", text_color=theme.GREEN,
                     font=("Consolas", 34, "bold")).pack(pady=(0, 2))
        ctk.CTkLabel(head, text="Configuracion de la estacion", text_color=theme.DIM,
                     font=("Consolas", 14)).pack()

        # --- Modo de juego (el operador lo fija segun el visitante) ---
        b_mode = block("Modo de juego",
                       "Tarjetas: sin teclado   Guiado: un Enter   Experto: terminal real   "
                       "Reto: escape room")
        self.mode_seg = ctk.CTkSegmentedButton(
            b_mode, values=list(_MODE_LABELS.keys()), height=44,
            font=("Consolas", 16, "bold"), selected_color=theme.CYAN,
            selected_hover_color=theme.CYAN, command=self._on_mode_change)
        self.mode_seg.set(_MODE_LABELS_INV.get(cfg.modes.mode, "Experto"))
        self.mode_seg.grid(row=1, column=0, sticky="ew")

        # --- Panel visual ---
        b_visual = block("Panel visual (mapa de red)")
        self.visual_seg = ctk.CTkSegmentedButton(
            b_visual, values=list(_VISUAL_LABELS.keys()), height=40,
            font=("Consolas", 15), selected_color=theme.GREEN,
            selected_hover_color=theme.GREEN)
        self.visual_seg.set(_VISUAL_LABELS_INV.get(bool(cfg.modes.visual), "Encendido"))
        self.visual_seg.grid(row=1, column=0, sticky="ew")

        # --- Motor ---
        b_engine = block("Motor de ejecucion")
        self.engine_seg = ctk.CTkSegmentedButton(
            b_engine, values=list(_ENGINE_LABELS.keys()), height=40,
            font=("Consolas", 15), selected_color=theme.GREEN,
            selected_hover_color=theme.GREEN)
        self.engine_seg.set(_ENGINE_LABELS_INV.get(cfg.modes.engine, "Simulado"))
        self.engine_seg.grid(row=1, column=0, sticky="ew")

        # --- Dificultad ---
        b_diff = block("Dificultad",
                       "Experto: Facil->Pro (cuanto te guia).   "
                       "Guiado: Facil=auto-Enter, Medio=escribir el comando.")
        self.diff_seg = ctk.CTkSegmentedButton(
            b_diff, values=list(_DIFF_LABELS.keys()), height=44,
            font=("Consolas", 16, "bold"), selected_color=theme.GREEN,
            selected_hover_color=theme.GREEN)
        self.diff_seg.set(_DIFF_LABELS_INV.get(cfg.modes.difficulty, "Facil"))
        self.diff_seg.grid(row=1, column=0, sticky="ew")

        # --- Leccion (solo tarjetas/guiado) ---
        b_lesson = block("Leccion (tarjetas / guiado)")
        self.lesson_seg = ctk.CTkSegmentedButton(
            b_lesson, values=list(_LESSON_LABELS.keys()), height=40,
            font=("Consolas", 14), selected_color=theme.CYAN,
            selected_hover_color=theme.CYAN)
        self.lesson_seg.set(_LESSON_LABELS_INV.get(cfg.modes.lesson, "Rotar"))
        self.lesson_seg.grid(row=1, column=0, sticky="ew")

        # --- Modo libre ---
        b_free = block("Modo libre (tiempo infinito, todo hackeable)")
        self.free_seg = ctk.CTkSegmentedButton(
            b_free, values=["Mision", "Libre"], height=40,
            font=("Consolas", 15), selected_color=theme.CYAN,
            selected_hover_color=theme.CYAN)
        self.free_seg.set("Libre" if cfg.modes.free_mode else "Mision")
        self.free_seg.grid(row=1, column=0, sticky="ew")

        # --- Tira de LEDs (solo si hay controlador habilitado) ---
        self.leds_btn = None
        if self.leds is not None and getattr(self.leds, "enabled", False):
            self.leds_btn = ctk.CTkButton(
                wrap, text="APAGAR LEDS", fg_color=theme.BG_PANEL, hover_color="#222",
                text_color=theme.DIM, border_color=theme.DIM, border_width=1,
                font=("Consolas", 14), height=38, command=self._toggle_leds)

        # --- Start ---
        self._start_btn = ctk.CTkButton(
            wrap, text="COMENZAR", fg_color=theme.GREEN, hover_color="#2ecc12",
            text_color="#04140a", font=("Consolas", 20, "bold"), height=52, command=self._start)

        self._head = head
        # una columna: el orden de siempre; dos columnas: juego a la izq, estacion a la der
        self._one_col = [b_mode, b_visual, b_engine, b_diff, b_lesson, b_free]
        self._two_cols = ([b_mode, b_diff, b_lesson], [b_visual, b_engine, b_free])
        self._layout = None
        self._relayout()
        responsive.on_change(self, self._relayout)

        self._on_mode_change()  # estado inicial de dificultad/leccion segun el modo

    def _relayout(self):
        two = responsive.layout() == 1
        # ancho minimo por columna para que los botones segmentados NO se corten;
        # el alto se ajusta solo al contenido (sin fijarlo a mano).
        self._wrap.grid_columnconfigure(0, weight=1, minsize=responsive.px(540 if two else 560))
        self._wrap.grid_columnconfigure(1, weight=1 if two else 0,
                                        minsize=responsive.px(540) if two else 0)
        if two == self._layout:
            return
        self._layout = two
        for w in self._wrap.grid_slaves():
            w.grid_forget()

        cols = 2 if two else 1
        self._head.grid(row=0, column=0, columnspan=cols, padx=40, pady=(30, 22))
        if two:
            for c, blocks in enumerate(self._two_cols):
                for r, b in enumerate(blocks, start=1):
                    b.grid(row=r, column=c, sticky="new", padx=(40, 18) if c == 0 else (18, 40),
                           pady=(0, 16))
            row = 1 + len(self._two_cols[0])
        else:
            for r, b in enumerate(self._one_col, start=1):
                b.grid(row=r, column=0, sticky="ew", padx=40, pady=(0, 16))
            row = 1 + len(self._one_col)
        if self.leds_btn is not None:
            self.leds_btn.grid(row=row, column=0, columnspan=cols, sticky="ew", padx=40, pady=(0, 8))
            row += 1
        self._start_btn.grid(row=row, column=0, columnspan=cols, sticky="ew", padx=40, pady=(10, 30))

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
        # La dificultad aplica a EXPERTO (facil->pro) y a GUIADO (facil=auto, medio=escribir).
        diff_state = "normal" if mode in ("experto", "guiado") else "disabled"
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
