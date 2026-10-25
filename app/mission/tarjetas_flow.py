"""TarjetasController: el modo TARJETAS (sin teclado), ahora con interaccion de juego.

Deja de ser "apretar 4 veces": el visitante DECIDE tocando.
  MIRAR     1) ESCANEAR (boton)  ->  2) elegir cual de los equipos es el servidor
  ENTRAR    3) ENTRAR (boton)    ->  overlay de suspenso que siempre gana
  LLEVARSE  4) explorar las carpetas del servidor (tocando) y abrir el archivo

Mismo ciclo de vida que los otros controllers (enter_waiting/on_any_key/shutdown).
Orquesta backend + LEDs + overlay de suspenso + mapa. No se puede perder.
"""
from __future__ import annotations

import posixpath
import queue
import random
import threading

from app.leds import segments as seg
from app.mission import script
from app.ui import theme

_LESSON_METHOD = {"clave": "hydra", "expuesto": "leak", "login": "sqli"}
_ROTATION = ("clave", "expuesto", "login")


class TarjetasController:
    def __init__(self, root, cfg, backend, cards, netmap, leds,
                 show_waiting, show_mission, on_return_menu=None, on_timer=None,
                 suspense=None):
        self.root = root
        self.cfg = cfg
        self.backend = backend
        self.cards = cards
        self.netmap = netmap
        self.leds = leds
        self.show_waiting = show_waiting
        self.show_mission = show_mission
        self.on_return_menu = on_return_menu
        self.on_timer = on_timer
        self.suspense = suspense

        self.cards.on_action = self.on_action
        self.cards.on_choice = self.on_choice
        self.cards.on_restart = self.on_any_key
        self.state = "waiting"
        self.phase = "intro"
        self.hosts = []
        self.session_ip = None
        self.target_ip = None
        self.lesson = "clave"
        self._cwd = "/"
        self._entries = {}
        self._round = 0
        self._q = queue.Queue()
        self._alive = True
        self._pump()

    # ================= ciclo de vida =================
    def enter_waiting(self):
        self.state = "waiting"
        if self.suspense:
            self.suspense.stop()
        try:
            self.backend.close_browser()
        except Exception:
            pass
        if self.netmap:
            self.netmap.reset()
        self.leds.idle()
        self.show_waiting()

    def on_any_key(self):
        if self.state == "waiting":
            self.start_mission()
        elif self.state == "done":
            self.enter_waiting()

    def start_mission(self):
        self.state = "playing"
        self.phase = "intro"
        self.session_ip = None
        self._cwd = "/"
        self.lesson = self._resolve_lesson()
        self.target = self.cfg.host_by_role("fileserver")
        self.target_ip = self.target.ip if self.target else None
        if self.netmap:
            self.netmap.reset()
        self.leds.off()
        self.show_mission()
        self._render_intro()

    def shutdown(self):
        self._alive = False
        if self.suspense:
            self.suspense.stop()
        try:
            self.backend.close_browser()
        except Exception:
            pass

    # ================= toques =================
    def on_action(self):
        if self.state == "done":
            self.enter_waiting()
            return
        if self.state != "playing":
            return
        if self.phase == "intro":
            self.cards.set_busy("ESCANEANDO...")
            self._do_scan()
        elif self.phase == "enter":
            self.cards.set_busy("ENTRANDO...")
            self._do_enter()

    def on_choice(self, key):
        if self.state != "playing":
            return
        if self.phase == "pick":
            self._choice_pick(key)
        elif self.phase == "explore":
            self._choice_explore(key)

    # ================= MIRAR: escanear + elegir servidor =================
    def _render_intro(self):
        self.cards.render_step("MIRAR", "ESCANEAR LA RED",
                               "Toca para ver todos los aparatos conectados a la red.",
                               badge="PASO 1 DE 4")

    def _do_scan(self):
        def done(res):
            self.hosts = res.hosts
            for h in self.hosts:
                if self.netmap:
                    self.netmap.discover_node(h.role)
                self.leds.animate_segments(seg.segments_for_role(h.role), seg.ANIM_DISCOVER)
            self.phase = "pick"
            self._render_pick()
        self._async(self.backend.scan, done)

    def _render_pick(self):
        items = [{"label": h.name, "key": h.role} for h in self.hosts]
        random.shuffle(items)   # que no quede siempre en el mismo lugar
        self.cards.render_grid(
            "MIRAR",
            "Encontramos %d equipos conectados. En cual te parece que estan guardados los "
            "archivos? Tocalo." % len(self.hosts),
            items, badge="PASO 2 DE 4")

    def _choice_pick(self, role):
        if role == "fileserver":
            self.leds.animate_segments(seg.segments_for_role("fileserver"), seg.ANIM_FOCUS)
            self.phase = "enter"
            self._render_enter()
        else:
            self.leds.animate_all(seg.ANIM_ERROR)
            self.cards.show_result("Ahi no. Fijate cual suena a 'guardar archivos' por su nombre.",
                                   theme.AMBER)

    # ================= ENTRAR: suspenso =================
    def _render_enter(self):
        self.cards.render_step("ENTRAR", "ENTRAR AL SERVIDOR",
                               "El FILE-SERVER tiene la cerradura floja. Toca para forzar la entrada.",
                               badge="PASO 3 DE 4")

    def _do_enter(self):
        ip = self.target_ip
        method = _LESSON_METHOD.get(self.lesson, "hydra")
        if self.netmap:
            self.netmap.pulse_role("fileserver", times=10, color=theme.AMBER)

        def after_suspense():
            def done(_res):
                self.session_ip = ip
                self._cwd = "/"
                if self.netmap:
                    self.netmap.focus_role("fileserver")
                self.leds.animate_segments(seg.segments_for_role("fileserver"), seg.ANIM_FOCUS)
                self.phase = "explore"
                self._render_explore(intro=True)
            self._async(lambda: self.backend.exploit(ip, method), done)

        if self.suspense is not None:
            self.suspense.play("fileserver", self.lesson, on_done=after_suspense)
        else:
            after_suspense()

    # ================= LLEVARSE: explorar carpetas y abrir el archivo =================
    def _render_explore(self, intro=False):
        def done(res):
            self._entries = {e.name: e.is_dir for e in res.entries}
            items = []
            if self._cwd != "/":
                items.append({"label": "..  (volver)", "key": "__up__", "is_dir": True})
            for e in res.entries:
                items.append({"label": e.name + ("/" if e.is_dir else ""),
                              "key": e.name, "is_dir": e.is_dir})
            hdr = ("Estas DENTRO del servidor. " if intro else "")
            self.cards.render_grid(
                "LLEVARSE",
                hdr + "Carpeta: %s\nToca una carpeta para abrirla, o el archivo para llevartelo."
                % self._cwd,
                items, badge="PASO 4 DE 4")
        self._async(lambda: self.backend.ls(self.session_ip, self._cwd), done)

    def _choice_explore(self, key):
        if key == "__up__":
            self._cwd = posixpath.dirname(self._cwd.rstrip("/")) or "/"
            self.leds.animate_segments(seg.segments_for_role("fileserver"), seg.ANIM_BLIP)
            self._render_explore()
            return
        is_dir = self._entries.get(key, False)
        child = ("/" + key) if self._cwd == "/" else posixpath.join(self._cwd, key)
        if is_dir:
            self._cwd = child
            self.leds.animate_segments(seg.segments_for_role("fileserver"), seg.ANIM_BLIP)
            self._render_explore()
        elif key == "secret.txt":
            self._open_secret(child)
        else:
            self.cards.show_result("Ese no es el archivo secreto. Mira en la carpeta 'restricted'.",
                                   theme.AMBER)

    def _open_secret(self, path):
        def done(_res):
            if self.netmap:
                self.netmap.transfer_role("fileserver")
            self.leds.animate_segments(seg.segments_for_role("fileserver"), seg.ANIM_TRANSFER)
            self._finish()
        self._async(lambda: self.backend.read(self.session_ip, path), done)

    def _finish(self):
        self.state = "done"
        self.cards.render_done("Mision cumplida: recuperaste el archivo secreto!",
                               script.tarjetas_takeaway(self.lesson))

    # ================= leccion =================
    def _resolve_lesson(self):
        base = self.cfg.modes.lesson
        if base in _ROTATION:
            return base
        lesson = _ROTATION[self._round % len(_ROTATION)]
        self._round += 1
        return lesson

    # ================= async =================
    def _async(self, fn, on_done):
        def worker():
            try:
                self._q.put((on_done, fn(), None))
            except Exception as exc:
                self._q.put((on_done, None, exc))
        threading.Thread(target=worker, daemon=True).start()

    def _pump(self):
        if not self._alive:
            return
        try:
            while True:
                on_done, res, err = self._q.get_nowait()
                if err is not None:
                    self.cards.show_result("Ups, algo fallo. Toca para intentar de nuevo.", theme.RED)
                else:
                    on_done(res)
        except queue.Empty:
            pass
        self.root.after(50, self._pump)
