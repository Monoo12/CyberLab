"""Mapa de red en vivo (tkinter Canvas). Espejo en pantalla de los LEDs fisicos:
cada accion resalta el nodo/tramo correspondiente, en el mismo lenguaje visual.
"""
from __future__ import annotations

import tkinter as tk

from app.ui import theme

# posiciones relativas (x, y) en [0,1]
_POS = {
    "router":      (0.50, 0.13),
    "switch-left": (0.30, 0.42),
    "switch-right":(0.70, 0.42),
    "terminal":    (0.30, 0.78),
    "fileserver":  (0.55, 0.80),
    "workstation": (0.72, 0.80),
    "security":    (0.89, 0.80),
}
_LABEL = {
    "router": "ROUTER", "switch-left": "SWITCH", "switch-right": "SWITCH",
    "terminal": "TERMINAL", "fileserver": "FILE-SERVER",
    "workstation": "WORKSTATION", "security": "SECURITY",
}
# enlaces fisicos: (a, b)
_LINKS = [
    ("router", "switch-left"),
    ("router", "switch-right"),
    ("switch-left", "terminal"),
    ("switch-right", "fileserver"),
    ("switch-right", "workstation"),
    ("switch-right", "security"),
]
# segmento LED -> enlaces del mapa que se encienden juntos
_SEG_LINKS = {
    0: [("router", "switch-left"), ("switch-left", "terminal")],
    1: [("router", "switch-right")],
    2: [("switch-right", "fileserver")],
    3: [("switch-right", "workstation")],
    4: [("switch-right", "security")],
}
_ROLE_SEGS = {
    "router": [0], "terminal": [0],
    "fileserver": [0, 1, 2], "workstation": [0, 1, 3], "security": [0, 1, 4],
}


class NetworkMapPanel(tk.Frame):
    def __init__(self, parent, cfg, mono_font):
        super().__init__(parent, bg=theme.BG_PANEL, highlightthickness=0)
        self.cfg = cfg
        self.mono = mono_font
        self.canvas = tk.Canvas(self, bg=theme.BG_PANEL, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._link_items: dict[tuple, int] = {}
        self._node_items: dict[str, dict] = {}
        self._cw = 1
        self._ch = 1
        self._pulse_jobs: list = []
        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, evt):
        self._cw, self._ch = evt.width, evt.height
        self._redraw()

    def _xy(self, role):
        rx, ry = _POS[role]
        return rx * self._cw, ry * self._ch

    def _redraw(self):
        c = self.canvas
        c.delete("all")
        self._link_items.clear()
        self._node_items.clear()
        # titulo
        c.create_text(12, 14, text="MAPA DE RED", anchor="w",
                      fill=theme.DIM, font=(self.mono, 11, "bold"))
        # enlaces primero (van por debajo)
        for a, b in _LINKS:
            ax, ay = self._xy(a)
            bx, by = self._xy(b)
            line = c.create_line(ax, ay, bx, by, fill=theme.LINK_IDLE, width=3)
            self._link_items[(a, b)] = line
        # nodos
        present_roles = {h.role for h in self.cfg.hosts} | {"switch-left", "switch-right"}
        for role in _POS:
            if role not in present_roles:
                continue
            self._draw_node(role)

    def _draw_node(self, role):
        c = self.canvas
        x, y = self._xy(role)
        w = max(54, self._cw * 0.11)
        h = max(26, self._ch * 0.05)
        rect = c.create_rectangle(x - w / 2, y - h / 2, x + w / 2, y + h / 2,
                                  fill=theme.NODE_IDLE, outline=theme.DIM, width=2)
        label = c.create_text(x, y, text=_LABEL.get(role, role.upper()),
                              fill=theme.FG, font=(self.mono, 8, "bold"))
        ip = ""
        host = next((hh for hh in self.cfg.hosts if hh.role == role), None)
        if host:
            ip = host.ip
        iplabel = c.create_text(x, y + h / 2 + 9, text=ip, fill=theme.DIM,
                                font=(self.mono, 7))
        self._node_items[role] = {"rect": rect, "label": label, "ip": iplabel}

    # ------------------------- animaciones -------------------------
    def _set_link(self, link, color, width=3):
        pair = link if link in self._link_items else (link[1], link[0])
        item = self._link_items.get(pair)
        if item:
            self.canvas.itemconfig(item, fill=color, width=width)

    def _set_node(self, role, fill=None, outline=None):
        n = self._node_items.get(role)
        if not n:
            return
        if fill:
            self.canvas.itemconfig(n["rect"], fill=fill)
        if outline:
            self.canvas.itemconfig(n["rect"], outline=outline)

    def reset(self):
        for job in self._pulse_jobs:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._pulse_jobs.clear()
        for link in self._link_items:
            self._set_link(link, theme.LINK_IDLE, 3)
        for role in self._node_items:
            self._set_node(role, fill=theme.NODE_IDLE, outline=theme.DIM)

    def discover_node(self, role):
        """Barrido al descubrir: enciende el nodo y su camino, tenue."""
        self._set_node(role, fill="#1f5a26", outline=theme.GREEN)
        for sid in _ROLE_SEGS.get(role, []):
            for link in _SEG_LINKS[sid]:
                self._set_link(link, "#2a7a30", 3)

    def focus_role(self, role, color=None):
        color = color or theme.GREEN
        self.reset()
        for sid in _ROLE_SEGS.get(role, []):
            for link in _SEG_LINKS[sid]:
                self._set_link(link, color, 4)
        self._set_node(role, fill="#1f5a26", outline=color)
        self._set_node("terminal", outline=theme.GREEN)

    def pulse_role(self, role, times=8, color=theme.AMBER, interval=140):
        links = [l for sid in _ROLE_SEGS.get(role, []) for l in _SEG_LINKS[sid]]

        def step(i):
            on = i % 2 == 0
            col = color if on else theme.LINK_IDLE
            w = 5 if on else 3
            for l in links:
                self._set_link(l, col, w)
            self._set_node(role, outline=color if on else theme.DIM)
            if i < times:
                job = self.after(interval, lambda: step(i + 1))
                self._pulse_jobs.append(job)
            else:
                self.focus_role(role, color=theme.GREEN)

        step(0)

    def transfer_role(self, role, times=12, interval=90):
        self.pulse_role(role, times=times, color=theme.CYAN, interval=interval)
