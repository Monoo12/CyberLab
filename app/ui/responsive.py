"""Pantalla responsive: la ventana abre a la medida del dispositivo y el contenido
escala con ella.

Cada vista declara uno o mas "lienzos" (ancho x alto en px logicos, o sea sin el zoom
DPI de Windows) para los que esta disenada a escala 1. Si declara varios, son layouts
alternativos (p.ej. mapa al costado / mapa abajo). Cuando cambia el tamano de la ventana
(incluye maximizar y F11) se elige el lienzo que mejor entra y la escala que lo hace
entrar, y se aplica a:
  - los widgets customtkinter (fuentes, alturas, paddings) via su ScalingTracker;
  - las fuentes tk nativas creadas con font() (terminal, mapa, matrix);
  - lo demas (minsize de grillas, paddings tk) via los callbacks de on_change().
"""
from __future__ import annotations

import sys
import tkinter.font as tkfont
import traceback

from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker

MIN_SCALE = 0.55
MAX_SCALE = 2.4
MIN_WINDOW = (760, 540)      # px logicos
_DEBOUNCE_MS = 120
_TITLEBAR = 32               # alto aprox. de la barra de titulo (px logicos)

_current = None              # instancia de la ventana (la app tiene una sola)


def _work_area(root):
    """(x, y, ancho, alto) en px fisicos del area util de la pantalla (sin la barra de tareas)."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            from ctypes import wintypes

            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):  # SPI_GETWORKAREA
                return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
        except Exception:
            pass
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    return 0, 0, sw, sh - round(sh * 0.06)   # sin dato de la barra de tareas: dejar margen


class Responsive:
    def __init__(self, root):
        self.root = root
        self.scale = 1.0
        self.layout = 0
        self._designs = ((1280, 720),)
        self._fonts: dict[tuple, tkfont.Font] = {}   # (familia, tamano, peso) -> fuente viva
        self._listeners: list = []                     # (widget, callback)
        self._job = None
        self._size_hint = None   # tamano logico pedido, hasta que la ventana se dibuje
        root.minsize(*MIN_WINDOW)
        root.bind("<Configure>", self._on_configure, add="+")

    # ------------------------------------------------------------------
    def _dpi(self) -> float:
        try:
            return ScalingTracker.get_window_scaling(self.root)
        except Exception:
            return 1.0

    def open_window(self, design=(1280, 720)):
        """Tamano inicial segun la pantalla: 88% centrada si sobra lugar para el lienzo
        principal; si no (notebooks, pantallas chicas o con zoom alto), maximizada."""
        d = self._dpi()
        x0, y0, aw, ah = _work_area(self.root)
        lw, lh = aw / d, ah / d
        w, h = round(lw * 0.88), round(lh * 0.88)
        x = x0 + (aw - round(w * d)) // 2
        y = y0 + max(0, (ah - round((h + _TITLEBAR) * d)) // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")   # tambien es el tamano al des-maximizar
        if w >= design[0] * 1.1 and h >= design[1] * 1.1:
            self._size_hint = (w, h)
            return
        self._size_hint = (lw, lh - _TITLEBAR)
        # despues de que customtkinter muestre la ventana (su deiconify la des-maximiza)
        self.root.after(0, self._maximize)

    def _maximize(self):
        try:
            self.root.state("zoomed")                  # Windows / macOS
        except Exception:
            try:
                self.root.attributes("-zoomed", True)  # Linux (X11)
            except Exception:
                pass

    # ------------------------------------------------------------------
    def set_designs(self, *designs):
        """La vista que se va a mostrar declara sus lienzos; aplica ya la escala que
        les corresponde, asi los widgets nuevos nacen con el tamano correcto."""
        self._designs = designs
        self.layout = -1          # sin preferencia: elegir de cero
        self._apply()

    def _window_size(self):
        if self.root.winfo_ismapped():
            d = self._dpi()
            return self.root.winfo_width() / d, self.root.winfo_height() / d
        return self._size_hint

    def _fit(self):
        size = self._window_size()
        if not size:
            return None
        w, h = size
        fits = [min(w / dw, h / dh) for dw, dh in self._designs]
        best = max(range(len(fits)), key=fits.__getitem__)
        # histeresis: no saltar de layout por un 4% (evita que parpadee en el borde)
        if 0 <= self.layout < len(fits) and fits[best] < fits[self.layout] * 1.04:
            best = self.layout
        return best, max(MIN_SCALE, min(MAX_SCALE, fits[best]))

    def _on_configure(self, evt):
        if evt.widget is not self.root:   # el bind de la raiz tambien recibe el de los hijos
            return
        if self._job is not None:
            self.root.after_cancel(self._job)
        self._job = self.root.after(_DEBOUNCE_MS, self._apply)

    def _apply(self):
        self._job = None
        fit = self._fit()
        if fit is None:
            return
        layout, scale = fit
        if layout == self.layout and abs(scale - self.scale) < 0.015:
            return
        self.layout, self.scale = layout, scale
        self._scale_ctk()
        for (_fam, size, _weight), f in self._fonts.items():
            f.configure(size=self._font_size(size))
        alive = []
        for widget, cb in list(self._listeners):
            try:
                if not widget.winfo_exists():
                    continue
            except Exception:
                continue
            alive.append((widget, cb))
            try:
                cb()
            except Exception:
                traceback.print_exc()
        self._listeners = alive

    def _scale_ctk(self):
        # Como ctk.set_widget_scaling() pero SIN el callback de la ventana raiz: ese fija
        # min=max=tamano actual y re-aplica la geometria (des-maximiza y traba el resize).
        ScalingTracker.widget_scaling = self.scale
        base = (1.0 if ScalingTracker.deactivate_automatic_dpi_awareness
                else ScalingTracker.window_dpi_scaling_dict.get(self.root, 1.0))
        for cb in list(ScalingTracker.window_widgets_dict.get(self.root, ())):
            if getattr(cb, "__self__", None) is self.root:
                continue
            try:
                cb(base * self.scale, base * ScalingTracker.window_scaling)
            except Exception:
                pass   # widget a medio destruir

    # ------------------------------------------------------------------
    def _font_size(self, size) -> int:
        return max(6, round(size * self.scale))

    def font(self, family, size, weight="normal") -> tkfont.Font:
        key = (family, size, weight)
        f = self._fonts.get(key)
        if f is None:
            f = tkfont.Font(root=self.root, family=family, size=self._font_size(size), weight=weight)
            self._fonts[key] = f
        return f

    def px(self, value) -> int:
        return round(value * self._dpi() * self.scale)

    def on_change(self, widget, callback):
        self._listeners.append((widget, callback))


# ----------------------------------------------------------------------
# Atajos de modulo para las vistas (sin pasar la instancia por cada constructor).
# Sin instalar (vista suelta en un test) devuelven los valores a escala 1.

def install(root) -> Responsive:
    global _current
    _current = Responsive(root)
    return _current


def font(family, size, weight="normal"):
    if _current is None:
        return tkfont.Font(family=family, size=size, weight=weight)
    return _current.font(family, size, weight)


def px(value) -> int:
    return _current.px(value) if _current else round(value)


def scale() -> float:
    return _current.scale if _current else 1.0


def layout() -> int:
    return max(0, _current.layout) if _current else 0


def on_change(widget, callback):
    if _current is not None:
        _current.on_change(widget, callback)


def bind_minsize(frame, column, base):
    """minsize de columna de una grilla (px logicos), escalado y mantenido al cambiar."""
    def apply():
        frame.grid_columnconfigure(column, minsize=px(base))
    apply()
    on_change(frame, apply)
