"""RetoController: el modo RETO (escape room), 4º modo.

Acertijos tematicos de hackeo donde el TABLERO y los componentes fisicos (router,
switches, cable/canaleta) dan las pistas. Input mixto (opcion multiple + tipear) y
cronometro estilo escape room: si se acaba el tiempo, no escapas. Respuesta
incorrecta -> penalidad de tiempo. Pista -> el tablero vuelve a mostrar la clave.

Aprovecha un hecho real del hardware: el LED 62 esta quemado -> es "el cable roto".

Mismo ciclo de vida que los otros controllers (enter_waiting/on_any_key/shutdown).
No usa el backend de red: es puramente de acertijos + LEDs + reloj.
"""
from __future__ import annotations

import random

from app.leds import segments as seg
from app.ui import theme


class RetoController:
    SECONDS = 150          # reloj del escape room
    PENALTY = 10           # segundos que cuesta una respuesta incorrecta

    def __init__(self, root, cfg, backend, reto, netmap, leds,
                 show_waiting, show_mission, on_return_menu=None, on_timer=None,
                 suspense=None):
        self.root = root
        self.cfg = cfg
        self.backend = backend
        self.reto = reto
        self.netmap = netmap
        self.leds = leds
        self.show_waiting = show_waiting
        self.show_mission = show_mission
        self.on_return_menu = on_return_menu
        self.on_timer = on_timer
        self.suspense = suspense

        self.reto.on_answer = self.on_answer
        self.reto.on_hint = self.on_hint
        self.reto.on_restart = self.start_mission
        self.state = "waiting"
        self.idx = 0
        self.puzzles = []
        self._remaining = self.SECONDS
        self._timer_job = None
        self._clue_job = None
        self._result_job = None
        self._locked = False

    # ================= ciclo de vida =================
    def enter_waiting(self):
        self.state = "waiting"
        self._cancel_all()
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
        self._cancel_all()
        self.state = "playing"
        self.idx = 0
        self.puzzles = self._build_puzzles()
        self._remaining = self.SECONDS
        if self.netmap:
            self.netmap.reset()
        self.leds.off()
        self.show_mission()
        self._render_current()
        self._tick()

    def shutdown(self):
        self.state = "done"
        self._cancel_all()

    def _to_menu(self):
        self._cancel_all()
        self.leds.idle()
        if self.on_return_menu:
            self.on_return_menu()

    # ================= acertijos =================
    def _render_current(self):
        p = self.puzzles[self.idx]
        self._locked = False
        self.reto.render_puzzle(self.idx + 1, len(self.puzzles), p["q"], p["clue"],
                                p["type"], p.get("options"))
        self._show_clue(p)

    def on_answer(self, value):
        if self.state != "playing" or self._locked:
            return
        p = self.puzzles[self.idx]
        if self._norm(value) == self._norm(p["answer"]):
            self._locked = True
            self.leds.animate_segments(seg.ALL_SEGMENTS, seg.ANIM_TRANSFER)
            self.reto.show_result("Correcto!", theme.GREEN)
            self._result_job = self.root.after(1200, self._next)
        else:
            self._remaining = max(1, self._remaining - self.PENALTY)
            self.leds.animate_all(seg.ANIM_ERROR)
            self.reto.show_result(
                "No es esa. Perdiste %d segundos. Mira el tablero y proba de nuevo."
                % self.PENALTY, theme.RED)

    def on_hint(self):
        if self.state != "playing":
            return
        p = self.puzzles[self.idx]
        self.reto.show_result("Pista: " + p.get("hint", p["clue"]), theme.AMBER)
        self._show_clue(p)

    def _next(self):
        self._result_job = None
        self.idx += 1
        if self.idx >= len(self.puzzles):
            self._win()
            return
        self._render_current()

    def _win(self):
        self.state = "done"
        self._cancel_all()
        self.leds.animate_all(seg.ANIM_TRANSFER)
        m, s = divmod(max(0, self._remaining), 60)
        self.reto.render_done("ESCAPASTE!",
                              "Resolviste todos los acertijos con %02d:%02d en el reloj. "
                              "Las luces no mienten." % (m, s), win=True)

    def _timeout(self):
        self.state = "done"
        self._cancel_all()
        self.leds.animate_all(seg.ANIM_ERROR)
        self.reto.render_done("SE ACABO EL TIEMPO",
                              "Casi. La red se bloqueo. Toca para intentarlo de nuevo.", win=False)

    # ================= pistas en el tablero =================
    def _show_clue(self, p):
        self._cancel_clue()
        kind = p["led"]
        if kind == "count_nodes":
            for node_id in seg.NODE_LEDS:
                self.leds.animate_node(node_id, seg.ANIM_PROCESS)
        elif kind == "broken_cable":
            self.leds.animate_segments(seg.ALL_SEGMENTS, seg.ANIM_FOCUS)
        elif kind == "follow_signal":
            self._light_path(seg.segments_for_role("router"), 0)
        elif kind == "flashes":
            self._blink_router(p.get("_n", 3), 0)

    def _light_path(self, segs, i):
        if i >= len(segs):
            self._clue_job = None
            return
        self.leds.animate_segment(segs[i], seg.ANIM_DISCOVER)
        self._clue_job = self.root.after(500, lambda: self._light_path(segs, i + 1))

    def _blink_router(self, n, i):
        if i >= n:
            self._clue_job = None
            return
        self.leds.animate_node(1, seg.ANIM_BLIP)   # nodo 1 = router
        self._clue_job = self.root.after(640, lambda: self._blink_router(n, i + 1))

    # ================= datos de los acertijos =================
    def _build_puzzles(self):
        n = random.randint(3, 5)   # destellos del router (fresco cada ronda)
        return [
            {"type": "choice", "led": "count_nodes",
             "q": "El tablero esta contando los equipos de la red. Cuantos NODOS "
                  "(los dos switches y el router) ves parpadear?",
             "clue": ">> Mira las luces de los switches y del router.",
             "options": ["2", "3", "4", "5"], "answer": "3",
             "hint": "Son dos switches y un router en el medio."},
            {"type": "choice", "led": "broken_cable",
             "q": "Hay un cable con falla: una luz quedo apagada en un tramo. "
                  "Mira bien la CANALETA. En que tramo esta la falla?",
             "clue": ">> El tramo con una luz muerta es el que falla.",
             "options": ["TERMINAL - switch izq", "switch izq - ROUTER",
                         "ROUTER - switch der", "switch der - FILE-SERVER"],
             "answer": "switch der - FILE-SERVER",
             "hint": "Es el ultimo tramo, el que llega al FILE-SERVER."},
            {"type": "text", "led": "flashes", "_n": n,
             "q": "El ROUTER va a parpadear un numero. Conta los destellos y escribilo.",
             "clue": ">> Mira SOLO la luz del router.",
             "answer": str(n),
             "hint": "Conta de nuevo los destellos de la luz del router."},
            {"type": "choice", "led": "follow_signal",
             "q": "Segui la senal por la CANALETA: la informacion viajo desde la "
                  "terminal. A que equipo llego?",
             "clue": ">> Mira hasta donde avanza la luz.",
             "options": ["switch izquierdo", "ROUTER", "switch derecho", "FILE-SERVER"],
             "answer": "ROUTER",
             "hint": "La luz se detiene justo en el router."},
        ]

    @staticmethod
    def _norm(s):
        return str(s).strip().lower()

    # ================= reloj =================
    def _tick(self):
        if self.on_timer:
            self.on_timer(self._remaining)
        if self._remaining <= 0:
            self._timeout()
            return
        self._remaining -= 1
        self._timer_job = self.root.after(1000, self._tick)

    def _cancel_clue(self):
        if self._clue_job:
            try:
                self.root.after_cancel(self._clue_job)
            except Exception:
                pass
        self._clue_job = None

    def _cancel_all(self):
        for attr in ("_timer_job", "_result_job"):
            job = getattr(self, attr, None)
            if job:
                try:
                    self.root.after_cancel(job)
                except Exception:
                    pass
            setattr(self, attr, None)
        self._cancel_clue()
