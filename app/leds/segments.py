"""Mapeo de enlaces logicos de la red a segmentos fisicos de LED.

Espejo del firmware (firmware/cyberlab_leds): una sola tira encadenada en un pin, donde
cada tramo es un rango de LEDs. El id de segmento viaja por serial (SEG:<id>:<anim>).

Topologia del tablero (68 LEDs; numeracion desde 0 como PIX, entre parentesis la
cuenta a mano desde 1):
  id 0 = Tramo 1: TERMINAL   <-> switch-izq    LEDs  0..12  (1-13)
         Nodo 0:  switch-izq                   LED  13      (14)
  id 1 = Tramo 2: switch-izq <-> router        LEDs 14..33  (15-34)
         Nodo 1:  router                       LED  34      (35)
  id 2 = Tramo 3: router     <-> switch-der    LEDs 35..53  (36-54)
         Nodo 2:  switch-der                   LED  54      (55)
  id 3 = Tramo 4: switch-der <-> FILE-SERVER   LEDs 55..67  (56-68)
No hay LEDs danados (DEAD_LEDS vacio): el 62 (63 a mano) se reparo. El acertijo del cable
roto del Reto apaga a proposito el 65 (66 a mano), cerca del FILE-SERVER (BROKEN_CABLE_LED).

Cada SEG que enciende un tramo hace que el nodo del final de ese tramo titile unos
segundos ("procesando") y despues quede como el tramo; la app no tiene que hacer nada
aparte. NODE:<id>:<anim> maneja un nodo suelto.

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

# LEDs fisicos (desde 0) de cada tramo y nodo; espejo de BRANCH_COUNTS del firmware.
SEGMENT_LEDS: dict[int, tuple[int, int]] = {0: (0, 12), 1: (14, 33), 2: (35, 53), 3: (55, 67)}
NODE_LEDS: dict[int, int] = {0: 13, 1: 34, 2: 54}
NODE_NAMES: dict[int, str] = {0: "switch-izq", 1: "router", 2: "switch-der"}
DEAD_LEDS: list[int] = []  # espejo de DEAD_LEDS del firmware (el los apaga siempre)
NUM_LEDS = 68
# "Cable roto" del Reto: la app apaga este LED a proposito (ADD:<n>:OFF). Esta en el
# tramo 4 (switch-der -> FILE-SERVER): la respuesta y la pista del acertijo asumen ese tramo.
BROKEN_CABLE_LED = 65  # 66 a mano: a 2 luces del FILE-SERVER (elegido mirando el tablero)

# Animaciones reconocidas por el firmware
ANIM_DISCOVER = "DISCOVER"  # barrido suave al descubrir
ANIM_FOCUS = "FOCUS"        # barrido de entrada y queda verde con un pulso de datos
ANIM_EXPLOIT = "EXPLOIT"    # fuerza bruta: rojo que late + rafagas blanco/naranja
ANIM_TRANSFER = "TRANSFER"  # parpadeo rapido (transferencia de datos)
ANIM_PROCESS = "PROCESS"    # titila unos segundos (nodo procesando) y vuelve
ANIM_WIN = "WIN"            # victoria SOSTENIDA: arcoiris, chispas y flashes
# Transitorias: animan un rato y vuelven solas al estado previo de la zona.
ANIM_PING = "PING"          # eco que va y vuelve (ping)
ANIM_SCAN = "SCAN"          # escaneo de puertos (flicker) -- telnet / knock
ANIM_BLIP = "BLIP"          # ack rapido de cualquier comando (reacciona a todo)
ANIM_ERROR = "ERROR"        # flash rojo de error (comando invalido / fallo)
ANIM_OPEN = "OPEN"          # abrir carpeta: colores rapidos + degrade amarillo->verde
ANIM_GLITCH = "GLITCH"      # caos de intrusion SOSTENIDO (nodos durante el exploit)
ANIM_OFF = "OFF"            # apagado (sirve con PIX/ADD para apagar LEDs sueltos)


def segments_for_role(role: str) -> list[int]:
    return PATH_TO_ROLE.get(role, [])
