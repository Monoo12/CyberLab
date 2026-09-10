"""Mapeo de enlaces logicos de la red a segmentos fisicos de LED.

Espejo del firmware (firmware/cyberlab_leds): cada 'rama' es un pin distinto del
microcontrolador con su propia tira. El id de segmento viaja por serial (SEG:<id>:<anim>).

Topologia (arbol, 6 enlaces / 5 ramas de datos):
  rama 0: router <-> switch-izq <-> TERMINAL           (una tira continua)
  rama 1: router <-> switch-der                         (troncal derecho)
  rama 2: switch-der <-> FILE-SERVER
  rama 3: switch-der <-> WORKSTATION-01
  rama 4: switch-der <-> SECURITY-SERVER
"""
from __future__ import annotations

# role del host  ->  ids de segmentos que se encienden para llegar a el desde la terminal
PATH_TO_ROLE: dict[str, list[int]] = {
    "router":      [0],
    "terminal":    [0],
    "fileserver":  [0, 1, 2],
    "workstation": [0, 1, 3],
    "security":    [0, 1, 4],
}

ALL_SEGMENTS: list[int] = [0, 1, 2, 3, 4]

# Animaciones reconocidas por el firmware
ANIM_DISCOVER = "DISCOVER"  # barrido suave al descubrir
ANIM_FOCUS = "FOCUS"        # resaltado fijo del tramo en foco
ANIM_EXPLOIT = "EXPLOIT"    # pulso intenso/rapido
ANIM_TRANSFER = "TRANSFER"  # parpadeo rapido (transferencia de datos)


def segments_for_role(role: str) -> list[int]:
    return PATH_TO_ROLE.get(role, [])
