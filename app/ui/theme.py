"""Paleta y fuentes del look 'terminal/cyber'."""
from __future__ import annotations

# Colores
BG = "#0a0e0a"          # fondo casi negro con tinte verde
BG_PANEL = "#0d130d"
FG = "#c8facc"          # texto verde claro
GREEN = "#39ff14"       # verde neon (acentos)
DIM = "#3a6b3a"         # verde apagado
CYAN = "#35e0e0"
AMBER = "#ffb000"
RED = "#ff4d4d"
WHITE = "#e8ffe8"

# Colores del mapa de red
NODE_IDLE = "#16391a"
NODE_ACTIVE = GREEN
LINK_IDLE = "#1c3a1c"
LINK_ACTIVE = GREEN

# Fuentes (con fallback). El primero disponible en el sistema gana.
MONO_FAMILIES = ("JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", "Courier New")


def pick_mono(root) -> str:
    import tkinter.font as tkfont

    available = set(tkfont.families(root))
    for fam in MONO_FAMILIES:
        if fam in available:
            return fam
    return "Courier New"
