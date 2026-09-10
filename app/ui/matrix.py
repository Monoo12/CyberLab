"""Pantalla de espera con efecto 'matrix rain' (seccion 6, paso 0).

Se muestra cuando nadie interactua; cualquier tecla arranca la mision.
"""
from __future__ import annotations

import random
import tkinter as tk

from app.ui import theme

_CHARS = "01<>[]{}#$%&*+=|/ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class MatrixRain(tk.Frame):
    def __init__(self, parent, mono_font, on_key=None):
        super().__init__(parent, bg="black", highlightthickness=0)
        self.mono = mono_font
        self.on_key = on_key
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._cols = []
        self._font_size = 16
        self._running = False
        self._job = None
        self._title = None
        self._cw = 1
        self._ch = 1
        self._step = self._font_size + 2
        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, evt):
        self._cw, self._ch = evt.width, evt.height
        step = self._font_size + 2
        n = max(1, self._cw // step)
        self._cols = [random.randint(-40, 0) for _ in range(n)]
        self._step = step

    def start(self):
        if self._running:
            return
        self._running = True
        self._tick()

    def stop(self):
        self._running = False
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _tick(self):
        if not self._running:
            return
        c = self.canvas
        c.delete("rain")
        rows = max(1, self._ch // self._step)
        for i, head in enumerate(self._cols):
            x = i * self._step + self._step // 2
            for j in range(0, 6):
                y = (head - j) * self._step
                if 0 <= y <= self._ch:
                    ch = random.choice(_CHARS)
                    color = theme.WHITE if j == 0 else theme.GREEN if j < 2 else theme.DIM
                    c.create_text(x, y, text=ch, fill=color,
                                  font=(self.mono, self._font_size), tags="rain")
            self._cols[i] = head + 1
            if head * self._step > self._ch and random.random() > 0.975:
                self._cols[i] = random.randint(-20, 0)
        self._draw_title()
        self._job = self.after(60, self._tick)

    def _draw_title(self):
        c = self.canvas
        c.delete("title")
        cx, cy = self._cw // 2, self._ch // 2
        c.create_rectangle(cx - 260, cy - 60, cx + 260, cy + 60,
                           fill="black", outline=theme.GREEN, width=2, tags="title")
        c.create_text(cx, cy - 18, text="C Y B E R   L A B", fill=theme.GREEN,
                      font=(self.mono, 30, "bold"), tags="title")
        c.create_text(cx, cy + 22, text="[ presiona cualquier tecla para comenzar ]",
                      fill=theme.WHITE, font=(self.mono, 13), tags="title")

    def bind_keys(self, widget):
        widget.bind_all("<Key>", self._key)
        widget.bind_all("<Button-1>", self._key)

    def unbind_keys(self, widget):
        widget.unbind_all("<Key>")
        widget.unbind_all("<Button-1>")

    def _key(self, _evt=None):
        if self.on_key:
            self.on_key()
