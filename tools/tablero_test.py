"""Prueba del tablero completo de LEDs: 4 tramos, 3 nodos que titilan y el LED danado.

Uso:
    python tools/tablero_test.py               # todas las fases, puerto de config.toml
    python tools/tablero_test.py --port COM7
    python tools/tablero_test.py --fase 3      # una sola fase (1..4)
    python tools/tablero_test.py --pausado     # espera Enter antes de cada fase

Manda los comandos con el mismo LedController que usa la app, asi que tambien prueba
la conexion real. Los numeros de LED que imprime son "a mano" (desde 1), como se
cuentan sobre el tablero. El mapeo sale de app/leds/segments.py.
"""
from __future__ import annotations

import argparse
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.leds import segments as seg  # noqa: E402
from app.leds.controller import LedController  # noqa: E402

TRAMOS = {
    0: "TERMINAL -> switch-izq",
    1: "switch-izq -> router",
    2: "router -> switch-der",
    3: "switch-der -> FILE-SERVER",
}


def _port_from_config() -> str | None:
    p = ROOT / "config.toml"
    if p.exists():
        with open(p, "rb") as fh:
            return tomllib.load(fh).get("serial", {}).get("port")
    return None


def _dead_in(a: int, b: int) -> list[int]:
    return [d for d in seg.DEAD_LEDS if a <= d <= b]


def fase_tramos(leds: LedController) -> None:
    print("\n[1] Tramos uno por uno")
    for k in seg.ALL_SEGMENTS:
        a, b = seg.SEGMENT_LEDS[k]
        esperado = f"LEDs {a + 1}-{b + 1} en verde"
        nodo = seg.NODE_LEDS.get(k)
        if nodo is not None:
            esperado += f"; el {nodo + 1} ({seg.NODE_NAMES[k]}) titila blanco y queda verde"
        else:
            esperado += "; sin nodo (llega al FILE-SERVER)"
        for d in _dead_in(a, b):
            esperado += f"; el {d + 1} apagado"
        leds.off()
        time.sleep(0.8)
        print(f"  Tramo {k + 1} ({TRAMOS[k]}): {esperado}")
        leds.animate_segment(k, seg.ANIM_FOCUS)
        time.sleep(4.5)


def fase_nodos(leds: LedController) -> None:
    print("\n[2] Nodos solos")
    leds.off()
    time.sleep(1.0)
    for k, i in seg.NODE_LEDS.items():
        print(f"  Nodo {k} ({seg.NODE_NAMES[k]}): solo el LED {i + 1} titila ~2,5 s y se apaga")
        leds.animate_node(k, seg.ANIM_PROCESS)
        time.sleep(3.5)


def fase_danado(leds: LedController) -> None:
    print("\n[3] LED danado")
    dead = ", ".join(str(d + 1) for d in seg.DEAD_LEDS)
    print(f"  Toda la tira verde (los nodos titilan primero) menos el {dead}")
    leds.animate_all(seg.ANIM_FOCUS)
    time.sleep(5.0)
    for d in seg.DEAD_LEDS:
        a, b = max(d - 2, 0), min(d + 2, seg.NUM_LEDS - 1)
        print(f"  Solo LEDs {a + 1}-{b + 1}: el {d + 1} apagado en el medio")
        leds.animate_pixels(f"{a}-{b}", seg.ANIM_FOCUS)
        time.sleep(4.0)


def fase_ruta(leds: LedController) -> None:
    print("\n[4] Ruta completa hasta el FILE-SERVER (salto por salto)")
    leds.off()
    time.sleep(1.0)
    for k in seg.segments_for_role("fileserver"):
        nodo = seg.NODE_LEDS.get(k)
        detalle = f", procesa el {nodo + 1} ({seg.NODE_NAMES[k]})" if nodo is not None else ", llega"
        print(f"  Tramo {k + 1}: barrido verde{detalle}")
        leds.animate_segment(k, seg.ANIM_DISCOVER)
        time.sleep(3.0)
    time.sleep(1.5)


FASES = {1: fase_tramos, 2: fase_nodos, 3: fase_danado, 4: fase_ruta}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--fase", type=int, choices=sorted(FASES), default=None)
    ap.add_argument("--pausado", action="store_true", help="esperar Enter antes de cada fase")
    args = ap.parse_args()

    port = args.port or _port_from_config()
    if not port:
        print("Especifica --port (ej. COM7)")
        sys.exit(1)
    leds = LedController(port, args.baud)
    if not leds.connected:
        sys.exit(1)
    time.sleep(0.5)

    fases = [args.fase] if args.fase else sorted(FASES)
    try:
        for n in fases:
            if args.pausado:
                input(f"\nEnter para la fase {n}...")
            FASES[n](leds)
    except KeyboardInterrupt:
        pass
    finally:
        leds.close()  # termina apagada
    print("\nListo (la tira queda apagada).")


if __name__ == "__main__":
    main()
