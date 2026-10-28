"""Pantalla de espera con efecto 'matrix rain' (seccion 6, paso 0).

Se muestra cuando nadie interactua; cualquier tecla arranca la mision.
"""
from __future__ import annotations

import random
import tkinter as tk

from app.ui import responsive, theme

_CHARS = "01<>[]{}#$%&*+=|/ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class MatrixRain(tk.Frame):
    def __init__(self, parent, mono_font, on_key=None):
        super().__init__(parent, bg="black", highlightthickness=0)
        self.mono = mono_font
        self.on_key = on_key
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, bd=0, width=1, height=1)
        self.canvas.pack(fill="both", expand=True)
        self._cols = []
        self._font = responsive.font(mono_font, 16)
        self._f_title = responsive.font(mono_font, 30, "bold")
        self._f_sub = responsive.font(mono_font, 13)
        self._running = False
        self._job = None
        self._title = None
        self._cw = 1
        self._ch = 1
        self._step = 18
        self.canvas.bind("<Configure>", self._on_resize)
        responsive.on_change(self, self._reflow)

    def _on_resize(self, evt):
        self._cw, self._ch = evt.width, evt.height
        self._reflow()

    def _reflow(self):
        # paso de la grilla = alto real de la fuente (sigue la escala y el DPI)
        self._step = max(8, self._font.metrics("linespace"))
        n = max(1, self._cw // self._step)
        self._cols = [random.randint(-40, 0) for _ in range(n)]

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
                    c.create_text(x, y, text=ch, fill=color, font=self._font, tags="rain")
            self._cols[i] = head + 1
            if head * self._step > self._ch and random.random() > 0.975:
                self._cols[i] = random.randint(-20, 0)
        self._draw_title()
        self._job = self.after(60, self._tick)

    def _draw_title(self):
        c = self.canvas
        c.delete("title")
        cx, cy = self._cw // 2, self._ch // 2
        px = responsive.px
        c.create_text(cx, cy - px(18), text="C Y B E R   L A B", fill=theme.GREEN,
                      font=self._f_title, tags="title")
        c.create_text(cx, cy + px(22), text="[ presiona cualquier tecla para comenzar ]",
                      fill=theme.WHITE, font=self._f_sub, tags="title")
        # el recuadro se ajusta al texto (a cualquier escala/DPI), con margen
        x0, y0, x1, y1 = c.bbox("title")
        box = c.create_rectangle(x0 - px(28), y0 - px(16), x1 + px(28), y1 + px(16),
                                 fill="black", outline=theme.GREEN, width=max(1, px(2)),
                                 tags="title")
        c.tag_lower(box, "title")

    def bind_keys(self, widget):
        widget.bind_all("<Key>", self._key)
        widget.bind_all("<Button-1>", self._key)

    def unbind_keys(self, widget):
        widget.unbind_all("<Key>")
        widget.unbind_all("<Button-1>")

    def _key(self, _evt=None):
        if self.on_key:
            self.on_key()
