"""Prueba de la tira LED sin la app: envia comandos por serial al firmware.

Uso:
    python tools/led_test.py --port COM3            # secuencia demo
    python tools/led_test.py --port /dev/ttyUSB0 SEG:2:EXPLOIT
    python tools/led_test.py --port COM3 PIX:0-9,40-50:FOCUS   # LEDs sueltos
    python tools/led_test.py --port COM3 --interactive   # tipear comandos a mano

Sin --port intenta leer [serial].port de config.toml.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

try:
    import serial
except ImportError:
    print("Falta pyserial:  pip install pyserial")
    sys.exit(1)


def _port_from_config() -> str | None:
    import tomllib

    for name in ("config.toml", "config.example.toml"):
        p = Path(__file__).resolve().parent.parent / name
        if p.exists():
            with open(p, "rb") as fh:
                return tomllib.load(fh).get("serial", {}).get("port")
    return None


DEMO = [
    "OFF", "IDLE",
    "SEG:0:DISCOVER", "SEG:1:DISCOVER", "SEG:2:DISCOVER", "SEG:3:DISCOVER",
    "SEG:3:FOCUS", "NODE:1:PROCESS", "ALL:EXPLOIT", "ALL:TRANSFER",
    "PIX:0-12,35-53:FOCUS", "ADD:55-67:EXPLOIT", "OFF",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("cmd", nargs="?", help="un comando unico, ej. SEG:2:EXPLOIT")
    args = ap.parse_args()

    port = args.port or _port_from_config()
    if not port:
        print("Especifica --port (ej. COM3 o /dev/ttyUSB0)")
        sys.exit(1)

    # Abrir sin activar DTR/RTS: en el NodeMCU esas lineas van a RST y GPIO0.
    ser = serial.Serial()
    ser.port = port
    ser.baudrate = args.baud
    ser.timeout = 0.3
    ser.dtr = False
    ser.rts = False
    ser.open()
    time.sleep(0.5)

    def send(line):
        print(">>", line)
        ser.write((line + "\n").encode())

    if args.cmd:
        send(args.cmd)
    elif args.interactive:
        print("Escribi comandos (IDLE/OFF/SEG:id:ANIM/ALL:ANIM/PIX:0-9,40-50:ANIM/ADD:...). "
              "Ctrl+C para salir.")
        try:
            while True:
                send(input("led> ").strip())
        except (KeyboardInterrupt, EOFError):
            pass
    else:
        for c in DEMO:
            send(c)
            time.sleep(1.0)

    ser.close()


if __name__ == "__main__":
    main()
