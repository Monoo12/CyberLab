"""RetoController: el modo RETO (escape room), version "juego".

Objetivo: TOMAR EL CONTROL DE LA RED. Cada acertijo resuelto captura un nodo y
llena la barra de control; al 100% se logra ACCESO ROOT. Hay cronometro, penalidad
por error y un RANGO de hacker al final segun tiempo y errores.

Tipos de acertijo (el tablero siempre da la pista):
  - choice   : elegir una opcion (contar nodos, el cable roto, seguir la senal)
  - keypad   : cargar un numero leido del tablero (destellos del router)
  - sequence : repetir un patron tocando los nodos (estilo Simon) que el tablero
               acaba de parpadear -- la interaccion mas "juego/hacker".

Mismo ciclo de vida que los otros controllers (enter_waiting/on_any_key/shutdown).
No usa el backend de red: es acertijos + LEDs + reloj.
"""
from __future__ import annotations

import random

from app.leds import segments as seg
from app.ui import theme

_NODE_ID = {"izq": 0, "router": 1, "der": 2}
_SEQ_KEYS = ("izq", "router", "der")


class RetoController:
    SECONDS = 180
    PENALTY = 8

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
        self._mistakes = 0
        self._seq_pos = 0
        self._locked = False
        self._accept = True      # False mientras el tablero muestra un patron (secuencia)
        self._timer_job = None
        self._clue_job = None
        self._result_job = None

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
        self._mistakes = 0
        self.puzzles = self._build_puzzles()
        self._remaining = self.SECONDS
        if self.netmap:
            self.netmap.reset()
        self.leds.off()
        self.show_mission()
        self.reto.set_progress(0.0)
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
        self._seq_pos = 0
        self.reto.render_puzzle(self.idx + 1, len(self.puzzles), p["q"], p["clue"],
                                p["type"], p.get("options"))
        self._show_clue(p)

    def on_answer(self, value):
        if self.state != "playing" or self._locked or not self._accept:
            return
        p = self.puzzles[self.idx]
        if p["type"] == "sequence":
            self._answer_sequence(p, value)
            return
        if self._norm(value) == self._norm(p["answer"]):
            self._solved()
        else:
            self._wrong("No es esa. Mira el tablero y proba de nuevo.")

    def _answer_sequence(self, p, key):
        if key == p["seq"][self._seq_pos]:
            self.leds.animate_node(_NODE_ID[key], seg.ANIM_BLIP)
            self._seq_pos += 1
            if self._seq_pos >= len(p["seq"]):
                self._solved()
            else:
                self.reto.show_result("%d / %d" % (self._seq_pos, len(p["seq"])), theme.GREEN)
        else:
            self._seq_pos = 0
            self._wrong("Secuencia incorrecta. Mira el patron otra vez.")
            self._show_clue(p)

    def on_hint(self):
        if self.state != "playing":
            return
        p = self.puzzles[self.idx]
        self.reto.show_result("Pista: " + p.get("hint", p["clue"]), theme.AMBER)
        self._seq_pos = 0
        self._show_clue(p)

    def _solved(self):
        self._locked = True
        solved = self.idx + 1
        pct = solved / len(self.puzzles)
        self.reto.set_progress(pct)
        cap = max(1, int(round(pct * len(seg.ALL_SEGMENTS))))
        self.leds.animate_segments(seg.ALL_SEGMENTS[:cap], seg.ANIM_FOCUS)
        self.reto.show_result("Nodo capturado!   Control de la red: %d%%" % int(pct * 100),
                              theme.GREEN)
        self._result_job = self.root.after(1300, self._next)

    def _wrong(self, msg):
        self._mistakes += 1
        self._remaining = max(1, self._remaining - self.PENALTY)
        self.leds.animate_all(seg.ANIM_ERROR)
        self.reto.show_result("%s  (-%ds)" % (msg, self.PENALTY), theme.RED)

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
        self.leds.animate_segments(seg.ALL_SEGMENTS, seg.ANIM_TRANSFER)
        m, s = divmod(max(0, self._remaining), 60)
        self.reto.set_progress(1.0)
        self.reto.render_done(
            "ACCESO ROOT -- RED BAJO CONTROL",
            "Rango: %s    Tiempo restante: %02d:%02d    Errores: %d"
            % (self._rank(), m, s, self._mistakes), win=True)

    def _timeout(self):
        self.state = "done"
        self._cancel_all()
        self.leds.animate_all(seg.ANIM_ERROR)
        self.reto.render_done("SE ACABO EL TIEMPO",
                              "La red se bloqueo. Toca para intentarlo de nuevo.", win=False)

    def _rank(self):
        if self._mistakes == 0 and self._remaining >= self.SECONDS * 0.4:
            return "HACKER ELITE"
        if self._mistakes <= 2:
            return "HACKER"
        return "APRENDIZ"

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
        elif kind == "sequence":
            self._flash_sequence(p["seq"], 0)

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
        self.leds.animate_node(1, seg.ANIM_BLIP)
        self._clue_job = self.root.after(640, lambda: self._blink_router(n, i + 1))

    def _flash_sequence(self, seq, i):
        if i == 0:
            self._accept = False
            self.reto.lock_answers(True)
            self.reto.show_result("Mira el patron en los nodos...", theme.CYAN)
        if i >= len(seq):
            self._clue_job = None
            self._accept = True
            self.reto.lock_answers(False)
            self.reto.show_result("Ahora repetilo tocando los nodos en ese orden.", theme.AMBER)
            return
        self.leds.animate_node(_NODE_ID[seq[i]], seg.ANIM_BLIP)
        self._clue_job = self.root.after(520, lambda: self._flash_sequence(seq, i + 1))

    # ================= datos de los acertijos =================
    def _build_puzzles(self):
        flashes = random.randint(4, 8)
        seq1 = [random.choice(_SEQ_KEYS) for _ in range(4)]
        seq2 = [random.choice(_SEQ_KEYS) for _ in range(6)]
        return [
            {"type": "choice", "led": "count_nodes",
             "q": "El tablero cuenta los equipos clave. Cuantos NODOS (switches + router) titilan?",
             "clue": ">> Mira las luces de los switches y del router.",
             "options": ["2", "3", "4", "5"], "answer": "3",
             "hint": "Son dos switches y un router en el medio."},
            {"type": "sequence", "led": "sequence", "seq": seq1,
             "q": "INTERCEPTA LA SENAL: memoriza el patron de pulsos y repetilo tocando los nodos.",
             "clue": ">> Mira que nodos parpadean, y en que orden.",
             "hint": "Toca los nodos en el mismo orden en que parpadearon."},
            {"type": "choice", "led": "broken_cable",
             "q": "Un cable falla: una luz quedo apagada en un tramo. Mira la CANALETA. Cual tramo?",
             "clue": ">> El tramo con una luz muerta es el que falla.",
             "options": ["TERMINAL - switch izq", "switch izq - ROUTER",
                         "ROUTER - switch der", "switch der - FILE-SERVER"],
             "answer": "switch der - FILE-SERVER",
             "hint": "Es el ultimo tramo, el que llega al FILE-SERVER."},
            {"type": "keypad", "led": "flashes", "_n": flashes,
             "q": "CODIGO DE ACCESO: cuantas veces parpadea el ROUTER? Cargalo en el teclado.",
             "clue": ">> Mira SOLO la luz del router y conta los destellos.",
             "answer": str(flashes),
             "hint": "Conta de nuevo los destellos del router y toca OK."},
            {"type": "choice", "led": "follow_signal",
             "q": "RASTREA EL PAQUETE: la senal viajo desde la terminal. A que equipo llego?",
             "clue": ">> Segui la luz por la canaleta hasta donde se detiene.",
             "options": ["switch izquierdo", "ROUTER", "switch derecho", "FILE-SERVER"],
             "answer": "ROUTER",
             "hint": "La luz se detiene justo en el router."},
            {"type": "sequence", "led": "sequence", "seq": seq2,
             "q": "ACCESO ROOT: repeti la secuencia final para tomar el control total de la red.",
             "clue": ">> Ultimo patron, mas largo. Mira bien.",
             "hint": "Toca los nodos en el orden en que parpadearon."},
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
