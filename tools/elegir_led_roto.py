"""Elegir mirando el tablero que luz apaga el acertijo del "cable roto" del Reto.

Uso:
    python tools/elegir_led_roto.py               # puerto de config.toml
    python tools/elegir_led_roto.py --port COM7

Prende toda la red en verde (igual que la pista del Reto) y apaga UNA luz del tramo
switch-der -> FILE-SERVER. Con Enter se corre una hacia el FILE-SERVER, con "a" una
hacia el switch, con un numero se salta a esa luz (contando a mano, desde 1) y con
"q" se sale. Al final dice que valor poner en BROKEN_CABLE_LED (app/leds/segments.py).
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.leds import segments as seg  # noqa: E402
from app.leds.controller import LedController  # noqa: E402


def _port_from_config() -> str | None:
    p = ROOT / "config.toml"
    if p.exists():
        with open(p, "rb") as fh:
            return tomllib.load(fh).get("serial", {}).get("port")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", default=None)
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args()
    port = args.port or _port_from_config()
    if not port:
        print("No hay puerto: pasalo con --port o configuralo en config.toml")
        return 1

    leds = LedController(port, args.baud)
    if not leds.connected:
        print(f"No se pudo abrir {port} (esta abierto el kiosco? cerralo y proba de nuevo)")
        return 1

    first, last = seg.SEGMENT_LEDS[3]
    led = seg.BROKEN_CABLE_LED
    print(f"Tramo switch-der -> FILE-SERVER: luces {first + 1} a {last + 1} (a mano).")
    print(f"Hoy el Reto apaga la {seg.BROKEN_CABLE_LED + 1}.")
    print("Enter = una hacia el FILE-SERVER   a = una hacia el switch   "
          "<numero> = ir a esa luz   q = salir\n")
    while True:
        # los mismos comandos que la pista del Reto (cada SEG borra el ADD anterior)
        leds.animate_segments(seg.ALL_SEGMENTS, seg.ANIM_FOCUS)
        leds.animate_pixels(str(led), seg.ANIM_OFF, replace=False)
        cmd = input(f"  Apagada la luz {led + 1} "
                    f"({led - first + 1} de {last - first + 1} desde el switch) > ").strip().lower()
        if cmd == "q":
            break
        if cmd == "a":
            led = max(first, led - 1)
        elif cmd.isdigit():
            n = int(cmd) - 1
            if first <= n <= last:
                led = n
            else:
                print(f"  Tiene que ser entre {first + 1} y {last + 1}")
        else:
            led = min(last, led + 1)

    leds.off()
    leds.close()
    print(f"\nElegida la luz {led + 1} a mano -> BROKEN_CABLE_LED = {led}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
