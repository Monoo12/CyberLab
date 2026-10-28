"""MissionApp: ventana raiz (customtkinter) que integra todos los paneles.

Vistas apiladas: setup -> mision (terminal + mapa) / espera (matrix rain).
Construye el backend (real/simulado) y el MissionController segun la config.
El tamano de la ventana y la escala del contenido los maneja app/ui/responsive.py.
"""
from __future__ import annotations

import customtkinter as ctk

from app.backend.simulated import SimulatedBackend
from app.leds.controller import LedController
from app.mission.flow import MissionController
from app.mission.reto_flow import RetoController
from app.mission.tarjetas_flow import TarjetasController
from app.ui import responsive, theme
from app.ui.matrix import MatrixRain
from app.ui.netmap import NetworkMapPanel
from app.ui.reto import RetoView
from app.ui.setup_menu import SetupMenu
from app.ui.suspense import SuspenseOverlay
from app.ui.tarjetas import TarjetasView
from app.ui.terminal import TerminalPanel

# Lienzos de la vista de mision (px logicos a escala 1; ver app/ui/responsive.py).
# Con mapa: 0 = mapa al costado (pantallas apaisadas), 1 = mapa abajo (verticales/angostas).
_MISSION_DESIGNS = ((1280, 720), (860, 980))
_MISSION_DESIGNS_NO_MAP = ((860, 720),)


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
        self.resp = responsive.install(self.root)
        self.resp.open_window(design=_MISSION_DESIGNS[0])
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._exit_fullscreen)
        # Atajo del operador: volver al menu de setup desde cualquier modo (util en
        # tarjetas/reto, que no tienen comando 'menu'). F5 o Ctrl+M.
        self.root.bind("<Control-m>", lambda e: self.return_to_setup())
        self.root.bind("<F5>", lambda e: self.return_to_setup())
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
        self.resp.set_designs(*SetupMenu.DESIGNS)
        self.setup = SetupMenu(self._container, self.cfg, on_start=self._on_setup_done,
                               leds=self.leds)
        self.setup.pack(fill="both", expand=True)

    def _on_setup_done(self):
        self.setup.destroy()
        self._build_mission()

    def return_to_setup(self):
        """Vuelve al menu de configuracion (comando 'menu', [M] al terminar, o Ctrl+M)."""
        if self.controller is None:
            return   # ya estamos en el menu (p.ej. Ctrl+M en setup): no hacer nada
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
        self.resp.set_designs(*(_MISSION_DESIGNS if self.cfg.modes.visual
                                else _MISSION_DESIGNS_NO_MAP))

        # Vista de mision
        self.mission_frame = ctk.CTkFrame(self._container, fg_color=theme.BG)

        top = ctk.CTkFrame(self.mission_frame, fg_color=theme.BG, height=34)
        top.pack(fill="x", side="top")
        engine_txt = "SIMULADO" if self.cfg.modes.engine == "simulated" else "REAL"
        mode_txt = self.cfg.modes.mode.upper()
        # la dificultad solo aplica al modo EXPERTO
        extra = ("   //   dificultad: " + self.cfg.modes.difficulty.upper()
                 if self.cfg.modes.mode == "experto" else "")
        ctk.CTkLabel(top, text="  CYBER LAB   //   modo: " + mode_txt +
                     "   //   motor: " + engine_txt + extra +
                     "   //   'menu' para volver",
                     text_color=theme.DIM, font=(self.mono, 12)).pack(side="left")
        self.timer_label = ctk.CTkLabel(top, text="TIEMPO 05:00", text_color=theme.GREEN,
                                        font=(self.mono, 14, "bold"))
        self.timer_label.pack(side="right", padx=14)

        body = ctk.CTkFrame(self.mission_frame, fg_color=theme.BG)
        body.pack(fill="both", expand=True)

        # Vista principal segun el modo: tarjetas / reto (sin teclado) o terminal.
        mode = self.cfg.modes.mode
        self.terminal = None
        self.cards = None
        self.reto = None
        if mode == "tarjetas":
            self.cards = main_view = TarjetasView(body, self.mono)
        elif mode == "reto":
            self.reto = main_view = RetoView(body, self.mono)
        else:
            self.terminal = main_view = TerminalPanel(body, self.mono,
                                                      cps=self.cfg.timing.typewriter_cps)
        if self.cfg.modes.visual:
            self.netmap = NetworkMapPanel(body, self.cfg, self.mono)
        self._body, self._main_view, self._map_below = body, main_view, None
        self._layout_body()
        responsive.on_change(body, self._layout_body)

        # Overlay de suspenso (modos accesibles): cubre la vista de mision cuando juega
        self.suspense = SuspenseOverlay(self.mission_frame, self.mono, self.leds)

        # Vista de espera (matrix)
        self.matrix = MatrixRain(self._container, self.mono, on_key=self._on_matrix_key)

        if mode == "tarjetas":
            self.controller = TarjetasController(
                self.root, self.cfg, self.backend, self.cards, self.netmap, self.leds,
                show_waiting=self._show_waiting, show_mission=self._show_mission,
                on_return_menu=self.return_to_setup, on_timer=self._on_timer,
                suspense=self.suspense,
            )
        elif mode == "reto":
            self.controller = RetoController(
                self.root, self.cfg, self.backend, self.reto, self.netmap, self.leds,
                show_waiting=self._show_waiting, show_mission=self._show_mission,
                on_return_menu=self.return_to_setup, on_timer=self._on_timer,
                suspense=self.suspense,
            )
        else:
            self.controller = MissionController(
                self.root, self.cfg, self.backend, self.terminal, self.netmap, self.leds,
                show_waiting=self._show_waiting, show_mission=self._show_mission,
                on_return_menu=self.return_to_setup, on_timer=self._on_timer,
                suspense=self.suspense,
            )
        self.controller.enter_waiting()

    def _layout_body(self):
        """Vista principal + mapa: el mapa va al costado (36% del ancho) o, si el lienzo
        elegido es el vertical, abajo (32% del alto). Sin mapa, la vista ocupa todo."""
        body, main = self._body, self._main_view
        if self.netmap is None:
            if not main.winfo_manager():
                main.pack(fill="both", expand=True)
            return
        below = self.resp.layout == 1
        if below == self._map_below:
            return
        self._map_below = below
        for i in (0, 1):   # limpiar la grilla del layout anterior
            body.grid_columnconfigure(i, weight=0, uniform="")
            body.grid_rowconfigure(i, weight=0, uniform="")
        main.grid(row=0, column=0, sticky="nsew")
        if below:
            self.netmap.grid(row=1, column=0, sticky="nsew")
            body.grid_columnconfigure(0, weight=1)
            body.grid_rowconfigure(0, weight=68, uniform="body")
            body.grid_rowconfigure(1, weight=32, uniform="body")
        else:
            self.netmap.grid(row=0, column=1, sticky="nsew")
            body.grid_rowconfigure(0, weight=1)
            body.grid_columnconfigure(0, weight=64, uniform="body")
            body.grid_columnconfigure(1, weight=36, uniform="body")

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
        if self.terminal is not None:
            self.terminal.focus_input()

    def _on_matrix_key(self):
        self.controller.on_any_key()

    def _on_timer(self, remaining):
        if remaining is None:   # modo libre o tarjetas: sin cuenta regresiva
            txt = "MODO TARJETAS" if self.cfg.modes.mode == "tarjetas" else "MODO LIBRE"
            self.timer_label.configure(text=txt, text_color=theme.CYAN)
            return
        m, s = divmod(max(0, remaining), 60)
        self.timer_label.configure(text="TIEMPO %02d:%02d" % (m, s))
        self.timer_label.configure(text_color=theme.RED if remaining <= 60 else theme.GREEN)

    def _toggle_fullscreen(self, _evt=None):
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)

    def _exit_fullscreen(self, _evt=None):
        self._fullscreen = False   # si no, el proximo F11 "apagaba" de nuevo y no hacia nada
        self.root.attributes("-fullscreen", False)

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
