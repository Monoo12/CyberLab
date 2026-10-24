"""Overlay de SUSPENSO para los modos accesibles (tarjetas / guiado).

El "golpe 2" (ENTRAR) del recorrido: un show cinematografico que combina los tres
recursos elegidos y SIEMPRE termina en exito:

  1. cuenta regresiva  -> "DEFENSA REINICIANDO 00:xx" baja pero el acceso entra antes
  2. contador de claves -> miles de contrasenas probandose a toda velocidad
  3. barra de deteccion -> "INTRUSION DETECTADA xx%" sube y casi te atrapan

Al final: casi-fallo (todo rojo) -> ACCESO CONCEDIDO (verde). No se puede perder.

Es un CTkFrame que se coloca ENCIMA de la vista de mision (place), corre su propia
animacion con after() y al terminar se esconde y llama on_done(). Maneja los LEDs
para que el tablero acompane el drama. Reutilizable: no sabe nada de la terminal.
"""
from __future__ import annotations

import random

import customtkinter as ctk

from app.leds import segments as seg
from app.ui import theme

# Claves debiles de muestra para el contador (puro flavor visual).
_WEAK = ["123456", "password", "qwerty", "admin", "12345678", "iloveyou", "111111",
         "dragon", "sunshine", "princess", "football", "monkey", "letmein", "abc123",
         "000000", "trustno1", "master", "hola1234", "root", "toor", "pepe2010"]

# Frase final segun la leccion de la ronda (de que te diste cuenta al "entrar").
_LESSON_HIT = {
    "clave":    "CLAVE HALLADA  ->  la contrasena era debil",
    "expuesto": "DATO EXPUESTO  ->  la clave estaba a la vista en la pagina",
    "login":    "LOGIN BURLADO  ->  un truco en el formulario lo dejo pasar",
    "rotar":    "ACCESO FORZADO",
}
_LESSON_TASK = {
    "clave":    "probando miles de contrasenas",
    "expuesto": "rastreando datos expuestos en la pagina",
    "login":    "probando trucos en el formulario de login",
    "rotar":    "forzando el acceso",
}


class SuspenseOverlay(ctk.CTkFrame):
    def __init__(self, parent, mono_font, leds):
        super().__init__(parent, fg_color=theme.BG, corner_radius=0)
        self.mono = mono_font
        self.leds = leds
        self._job = None
        self._on_done = None
        self._role = "fileserver"
        self._lesson = "rotar"
        self._t = 0
        self._attempts = 0
        self._dur = 6400          # duracion del nucleo (ms) antes del climax

        box = ctk.CTkFrame(self, fg_color=theme.BG_PANEL, corner_radius=18,
                           border_color=theme.RED, border_width=2)
        box.place(relx=0.5, rely=0.5, anchor="center")
        box.grid_columnconfigure(0, weight=1, minsize=620)

        r = [0]

        def add(w, pady=(0, 6)):
            w.grid(row=r[0], column=0, sticky="ew", padx=46, pady=pady)
            r[0] += 1

        self.title = ctk.CTkLabel(box, text="FORZANDO ACCESO", text_color=theme.AMBER,
                                  font=(mono_font, 30, "bold"))
        add(self.title, pady=(34, 2))
        self.target = ctk.CTkLabel(box, text="", text_color=theme.DIM, font=(mono_font, 14))
        add(self.target, pady=(0, 20))

        self.clock = ctk.CTkLabel(box, text="DEFENSA REINICIANDO  00:20", text_color=theme.RED,
                                  font=(mono_font, 22, "bold"))
        add(self.clock, pady=(0, 16))

        self.attempt = ctk.CTkLabel(box, text="", text_color=theme.CYAN, font=(mono_font, 16))
        add(self.attempt, pady=(0, 0))
        self.counter = ctk.CTkLabel(box, text="0 claves probadas", text_color=theme.FG,
                                    font=(mono_font, 15, "bold"))
        add(self.counter, pady=(0, 20))

        self.det_lbl = ctk.CTkLabel(box, text="INTRUSION DETECTADA  0%", text_color=theme.RED,
                                    font=(mono_font, 15, "bold"))
        add(self.det_lbl, pady=(0, 4))
        self.bar = ctk.CTkProgressBar(box, height=22, corner_radius=8,
                                      progress_color=theme.RED, fg_color="#201010")
        self.bar.set(0.0)
        add(self.bar, pady=(0, 34))

    # ------------------------------------------------------------------
    def play(self, target_role, lesson, on_done):
        """Arranca el show sobre el host target y llama on_done() al final."""
        self._on_done = on_done
        self._role = target_role or "fileserver"
        self._lesson = lesson if lesson in _LESSON_HIT else "rotar"
        self._t = 0
        self._attempts = 0
        self.title.configure(text="FORZANDO ACCESO", text_color=theme.AMBER)
        host = self._role.upper().replace("_", "-")
        self.target.configure(text=_LESSON_TASK[self._lesson] + "  //  objetivo: " + host)
        self.clock.configure(text="DEFENSA REINICIANDO  00:20", text_color=theme.RED)
        self.attempt.configure(text="")
        self.counter.configure(text="0 claves probadas")
        self.det_lbl.configure(text="INTRUSION DETECTADA  0%", text_color=theme.RED)
        self.bar.configure(progress_color=theme.RED)
        self.bar.set(0.0)
        self._segs = seg.segments_for_role(self._role) or seg.ALL_SEGMENTS
        self.leds.animate_segments(self._segs, seg.ANIM_EXPLOIT)
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        self._frame()

    def _frame(self):
        self._t += 60
        frac = min(1.0, self._t / self._dur)
        # 1) cuenta regresiva 20 -> 2 (nunca llega a 0: el acceso entra antes)
        remaining = max(2, 20 - int(frac * 18))
        self.clock.configure(text="DEFENSA REINICIANDO  00:%02d" % remaining)
        # 2) contador de claves, acelerando
        self._attempts += int(40 + 1100 * frac) + random.randint(0, 60)
        self.attempt.configure(text="probando:  " + random.choice(_WEAK))
        self.counter.configure(text="{:,} claves probadas".format(self._attempts))
        # 3) barra de deteccion subiendo hasta ~92%, con temblor
        det = min(0.93, frac * 0.9 + random.uniform(0, 0.05))
        self.bar.set(det)
        self.det_lbl.configure(text="INTRUSION DETECTADA  %d%%" % int(det * 100))
        if frac >= 1.0:
            self._climax_near_miss()
            return
        self._job = self.after(60, self._frame)

    def _climax_near_miss(self):
        # casi te atrapan: todo rojo al 99%
        self.bar.set(0.99)
        self.det_lbl.configure(text="INTRUSION DETECTADA  99%", text_color=theme.RED)
        self.clock.configure(text="DEFENSA REINICIANDO  00:02", text_color=theme.RED)
        self.title.configure(text="! DETECCION INMINENTE !", text_color=theme.RED)
        self.leds.animate_all(seg.ANIM_ERROR)
        self._job = self.after(850, self._success)

    def _success(self):
        # entra justo a tiempo: verde
        self.title.configure(text="ACCESO CONCEDIDO", text_color=theme.GREEN)
        self.target.configure(text=_LESSON_HIT[self._lesson], text_color=theme.WHITE)
        self.clock.configure(text="DEFENSA REINICIANDO  00:02  (congelada)", text_color=theme.GREEN)
        self.bar.configure(progress_color=theme.GREEN)
        self.bar.set(1.0)
        self.det_lbl.configure(text="INTRUSION DETECTADA  --  evadida", text_color=theme.GREEN)
        self.leds.animate_segments(self._segs, seg.ANIM_TRANSFER)
        self._job = self.after(1500, self._finish)

    def _finish(self):
        self._cancel()
        self.place_forget()
        cb, self._on_done = self._on_done, None
        if cb:
            cb()

    def _cancel(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        self._job = None

    def stop(self):
        """Corta el show (al volver al menu / reset) sin llamar on_done."""
        self._cancel()
        self._on_done = None
        try:
            self.place_forget()
        except Exception:
            pass
