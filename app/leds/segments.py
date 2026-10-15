"""Mapeo de enlaces logicos de la red a segmentos fisicos de LED.

Espejo del firmware (firmware/cyberlab_leds): una sola tira encadenada en un pin, donde
cada tramo es un rango de LEDs. El id de segmento viaja por serial (SEG:<id>:<anim>).

Topologia del tablero (cadena de 4 tramos, en "U" invertida):
  id 0 = Tramo 1: TERMINAL   <-> switch-izq    (50 cm, LEDs   0..29)
  id 1 = Tramo 2: switch-izq <-> router        (77 cm, LEDs  30..75)
  id 2 = Tramo 3: router     <-> switch-der    (73 cm, LEDs  76..118)
  id 3 = Tramo 4: switch-der <-> FILE-SERVER   (43 cm, LEDs 119..143)

WORKSTATION y SECURITY cuelgan del switch-der pero no tienen tramo propio en el
tablero (solo existen en el modo Simulado): su ruta se enciende hasta el switch-der.
"""
from __future__ import annotations

# role del host  ->  ids de segmentos que se encienden para llegar a el desde la terminal
PATH_TO_ROLE: dict[str, list[int]] = {
    "terminal":    [0],
    "router":      [0, 1],
    "fileserver":  [0, 1, 2, 3],
    "workstation": [0, 1, 2],
    "security":    [0, 1, 2],
}

ALL_SEGMENTS: list[int] = [0, 1, 2, 3]

# Animaciones reconocidas por el firmware
ANIM_DISCOVER = "DISCOVER"  # barrido suave al descubrir
ANIM_FOCUS = "FOCUS"        # resaltado fijo del tramo en foco
ANIM_EXPLOIT = "EXPLOIT"    # pulso intenso/rapido
ANIM_TRANSFER = "TRANSFER"  # parpadeo rapido (transferencia de datos)


def segments_for_role(role: str) -> list[int]:
    return PATH_TO_ROLE.get(role, [])
