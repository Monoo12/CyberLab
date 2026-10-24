"""TarjetasController: el flujo del modo TARJETAS (sin teclado).

Maneja el mismo ciclo de vida que MissionController (enter_waiting / on_any_key /
shutdown) para que la app lo trate igual, pero en vez de una terminal conduce la
TarjetasView: un boton grande por paso. Orquesta backend + LEDs + overlay de
suspenso + mapa, reusando todo lo que ya existe. No se puede perder.

Recorrido en 3 golpes -> 4 toques:
  MIRAR     scan            "escanear la red"
  ENTRAR    exploit+show    "entrar al servidor"   (suspenso que siempre gana)
  LLEVARSE  ls              "buscar el archivo"
  LLEVARSE  read            "llevarse el secreto"  -> mision cumplida
"""
from __future__ import annotations

import queue
import threading

from app.leds import segments as seg
from app.mission import script
from app.ui import theme

# Cada leccion se "entra" por una via distinta del backend.
_LESSON_METHOD = {"clave": "hydra", "expuesto": "leak", "login": "sqli"}
_ROTATION = ("clave", "expuesto", "login")

_STEPS = [
    {"beat": "MIRAR", "run": "scan", "badge": "PASO 1 DE 4", "title": "ESCANEAR LA RED",
     "desc": "Toca para ver todos los aparatos conectados a la red."},
    {"beat": "ENTRAR", "run": "exploit", "badge": "PASO 2 DE 4", "title": "ENTRAR AL SERVIDOR",
     "desc": "El FILE-SERVER tiene la cerradura floja. Toca para forzar la entrada."},
    {"beat": "LLEVARSE", "run": "ls", "badge": "PASO 3 DE 4", "title": "BUSCAR EL ARCHIVO",
     "desc": "Ya estas adentro. Toca para abrir las carpetas del servidor."},
    {"beat": "LLEVARSE", "run": "read", "badge": "PASO 4 DE 4", "title": "LLEVARSE EL SECRETO",
     "desc": "Encontraste el archivo secreto. Toca para copiarlo y ganar."},
]


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
        self.state = "waiting"
        self.idx = 0
        self.session_ip = None
        self.target_ip = None
        self.lesson = "clave"
        self._round = 0
        self._adv_job = None
        self._q = queue.Queue()
        self._alive = True
        self._pump()

    # ================= ciclo de vida =================
    def enter_waiting(self):
        self.state = "waiting"
        self._cancel_adv()
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
        self.idx = 0
        self.session_ip = None
        self.lesson = self._resolve_lesson()
        self.target = self.cfg.host_by_role("fileserver")
        self.target_ip = self.target.ip if self.target else None
        if self.netmap:
            self.netmap.reset()
        self.leds.off()
        self.show_mission()
        if self.on_timer:
            self.on_timer(None)
        self._render_current()

    def shutdown(self):
        self._alive = False
        self._cancel_adv()
        if self.suspense:
            self.suspense.stop()
        try:
            self.backend.close_browser()
        except Exception:
            pass

    def _to_menu(self):
        self._cancel_adv()
        self.leds.idle()
        if self.on_return_menu:
            self.on_return_menu()

    # ================= pasos =================
    def _resolve_lesson(self):
        base = self.cfg.modes.lesson
        if base in _ROTATION:
            return base
        lesson = _ROTATION[self._round % len(_ROTATION)]  # 'rotar': una por ronda
        self._round += 1
        return lesson

    def _render_current(self):
        s = _STEPS[self.idx]
        self.cards.render_step(s["beat"], s["title"], s["desc"], badge=s["badge"])

    def on_action(self):
        if self.state == "done":
            self.enter_waiting()
            return
        if self.state != "playing":
            return
        run = _STEPS[self.idx]["run"]
        self.cards.set_busy()
        {"scan": self._do_scan, "exploit": self._do_exploit,
         "ls": self._do_ls, "read": self._do_read}[run]()

    def _do_scan(self):
        def done(res):
            self.hosts = res.hosts
            for h in self.hosts:
                if self.netmap:
                    self.netmap.discover_node(h.role)
                self.leds.animate_segments(seg.segments_for_role(h.role), seg.ANIM_DISCOVER)
            self.cards.show_result(
                "Encontramos {} aparatos conectados. El FILE-SERVER ({}) es el que "
                "guarda el archivo secreto.".format(len(self.hosts), self.target_ip),
                theme.GREEN)
            self._advance_after(2400)
        self._async(self.backend.scan, done)

    def _do_exploit(self):
        ip = self.target_ip
        method = _LESSON_METHOD.get(self.lesson, "hydra")
        if self.netmap:
            self.netmap.pulse_role("fileserver", times=10, color=theme.AMBER)

        def after_suspense():
            def done(_res):
                self.session_ip = ip
                if self.netmap:
                    self.netmap.focus_role("fileserver")
                self.leds.animate_segments(seg.segments_for_role("fileserver"), seg.ANIM_FOCUS)
                self.cards.show_result("Entraste al servidor. " +
                                       script.tarjetas_takeaway(self.lesson), theme.WHITE)
                self._advance_after(3200)
            self._async(lambda: self.backend.exploit(ip, method), done)

        if self.suspense is not None:
            self.suspense.play("fileserver", self.lesson, on_done=after_suspense)
        else:
            after_suspense()

    def _do_ls(self):
        def done(_res):
            self.leds.animate_segments(seg.segments_for_role("fileserver"), seg.ANIM_BLIP)
            self.cards.show_result(
                "Abriste las carpetas del servidor. El archivo esta en la carpeta "
                "'restringido'.", theme.GREEN)
            self._advance_after(2200)
        self._async(lambda: self.backend.ls(self.session_ip, "/"), done)

    def _do_read(self):
        secret = self.cfg.fileserver.secret_path

        def done(_res):
            if self.netmap:
                self.netmap.transfer_role("fileserver")
            self.leds.animate_segments(seg.segments_for_role("fileserver"), seg.ANIM_TRANSFER)
            self._finish()
        self._async(lambda: self.backend.read(self.session_ip, secret), done)

    def _finish(self):
        self.state = "done"
        self.cards.render_done("Mision cumplida: recuperaste el archivo secreto.",
                               script.tarjetas_takeaway(self.lesson))

    def _advance_after(self, ms):
        self._cancel_adv()
        self._adv_job = self.root.after(ms, self._advance)

    def _advance(self):
        self._adv_job = None
        self.idx += 1
        if self.idx >= len(_STEPS):
            self._finish()
            return
        self._render_current()

    def _cancel_adv(self):
        if self._adv_job:
            try:
                self.root.after_cancel(self._adv_job)
            except Exception:
                pass
        self._adv_job = None

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
                    self.cards.show_result("Ups, algo fallo. Toca para intentar de nuevo.",
                                           theme.RED)
                    if self.state == "playing":
                        self._render_current()
                else:
                    on_done(res)
        except queue.Empty:
            pass
        self.root.after(50, self._pump)
