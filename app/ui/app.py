"""MissionApp: ventana raiz (customtkinter) que integra todos los paneles.

Vistas apiladas: setup -> mision (terminal + mapa) / espera (matrix rain).
Construye el backend (real/simulado) y el MissionController segun la config.
"""
from __future__ import annotations

import customtkinter as ctk

from app.backend.simulated import SimulatedBackend
from app.leds.controller import LedController
from app.mission.flow import MissionController
from app.ui import theme
from app.ui.matrix import MatrixRain
from app.ui.netmap import NetworkMapPanel
from app.ui.setup_menu import SetupMenu
from app.ui.terminal import TerminalPanel


def _make_backend(cfg):
    if cfg.modes.engine == "real":
        from app.backend.real import RealBackend  # import perezoso (evita deps si es simulado)
        return RealBackend(cfg)
    return SimulatedBackend(cfg)


class MissionApp:
    def __init__(self, cfg):
        self.cfg = cfg
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title("Cyber Lab")
        self.root.configure(fg_color=theme.BG)
        self.root.geometry("1200x760")
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False))
        self._fullscreen = False

        self.mono = theme.pick_mono(self.root)

        self.leds = LedController(cfg.serial.port, cfg.serial.baud, cfg.serial.enabled)
        self.backend = None
        self.controller = None
        self.netmap = None

        self._container = ctk.CTkFrame(self.root, fg_color=theme.BG)
        self._container.pack(fill="both", expand=True)

        if cfg.modes.autostart:
            self._build_mission()
        else:
            self._show_setup()

    # ------------------------------------------------------------------
    def _show_setup(self):
        self.setup = SetupMenu(self._container, self.cfg, on_start=self._on_setup_done)
        self.setup.pack(fill="both", expand=True)

    def _on_setup_done(self):
        self.setup.destroy()
        self._build_mission()

    def return_to_setup(self):
        """Vuelve al menu de configuracion (comando 'menu' o [M] al terminar)."""
        if self.controller:
            self.controller.shutdown()
        try:
            self.matrix.unbind_keys(self.root)
            self.matrix.stop()
            self.matrix.destroy()
        except Exception:
            pass
        try:
            self.mission_frame.destroy()
        except Exception:
            pass
        if self.backend:
            try:
                self.backend.close()
            except Exception:
                pass
        self.controller = None
        self.netmap = None
        self._show_setup()

    # ------------------------------------------------------------------
    def _build_mission(self):
        self.backend = _make_backend(self.cfg)

        # Vista de mision
        self.mission_frame = ctk.CTkFrame(self._container, fg_color=theme.BG)

        top = ctk.CTkFrame(self.mission_frame, fg_color=theme.BG, height=34)
        top.pack(fill="x", side="top")
        engine_txt = "SIMULADO" if self.cfg.modes.engine == "simulated" else "REAL"
        ctk.CTkLabel(top, text="  CYBER LAB   //   motor: " + engine_txt +
                     "   //   dificultad: " + self.cfg.modes.difficulty.upper() +
                     "   //   'menu' para volver",
                     text_color=theme.DIM, font=(self.mono, 12)).pack(side="left")
        self.timer_label = ctk.CTkLabel(top, text="TIEMPO 05:00", text_color=theme.GREEN,
                                        font=(self.mono, 14, "bold"))
        self.timer_label.pack(side="right", padx=14)

        body = ctk.CTkFrame(self.mission_frame, fg_color=theme.BG)
        body.pack(fill="both", expand=True)

        self.terminal = TerminalPanel(body, self.mono, cps=self.cfg.timing.typewriter_cps)
        if self.cfg.modes.visual:
            self.terminal.pack(side="left", fill="both", expand=True)
            self.netmap = NetworkMapPanel(body, self.cfg, self.mono)
            self.netmap.configure(width=460)
            self.netmap.pack(side="right", fill="both", expand=False)
            self.netmap.pack_propagate(False)
        else:
            self.terminal.pack(fill="both", expand=True)

        # Vista de espera (matrix)
        self.matrix = MatrixRain(self._container, self.mono, on_key=self._on_matrix_key)

        self.controller = MissionController(
            self.root, self.cfg, self.backend, self.terminal, self.netmap, self.leds,
            show_waiting=self._show_waiting, show_mission=self._show_mission,
            on_return_menu=self.return_to_setup, on_timer=self._on_timer,
        )
        self.controller.enter_waiting()

    # ------------------------------------------------------------------
    def _show_waiting(self):
        self.mission_frame.pack_forget()
        self.matrix.pack(fill="both", expand=True)
        self.matrix.start()
        self.matrix.bind_keys(self.root)

    def _show_mission(self):
        self.matrix.unbind_keys(self.root)
        self.matrix.stop()
        self.matrix.pack_forget()
        self.mission_frame.pack(fill="both", expand=True)
        self.terminal.focus_input()

    def _on_matrix_key(self):
        self.controller.on_any_key()

    def _on_timer(self, remaining):
        m, s = divmod(max(0, remaining), 60)
        self.timer_label.configure(text="TIEMPO %02d:%02d" % (m, s))
        self.timer_label.configure(text_color=theme.RED if remaining <= 60 else theme.GREEN)

    def _toggle_fullscreen(self, _evt=None):
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)

    # ------------------------------------------------------------------
    def run(self):
        try:
            self.root.mainloop()
        finally:
            try:
                self.leds.close()
            except Exception:
                pass
            if self.backend:
                try:
                    self.backend.close()
                except Exception:
                    pass
