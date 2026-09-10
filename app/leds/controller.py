"""Controlador de la tira LED por USB serial.

Protocolo de lineas (mismo que el firmware):
    IDLE                -> shimmer tenue de espera
    OFF                 -> apaga todo
    SEG:<id>:<anim>     -> anima un segmento
    ALL:<anim>          -> anima todos los segmentos

Degrada con elegancia: si no hay dispositivo (o pyserial no esta), NO rompe la app;
loguea por consola las lineas que enviaria, util para verificar la sincronia sin hardware.
"""
from __future__ import annotations

from app.leds import segments as seg

try:
    import serial  # pyserial
except Exception:  # pragma: no cover - opcional
    serial = None


class LedController:
    def __init__(self, port: str, baud: int = 115200, enabled: bool = True):
        self.port = port
        self.baud = baud
        self.enabled = enabled
        self._ser = None
        self._connected = False
        if enabled:
            self._try_connect()

    def _try_connect(self) -> None:
        if serial is None:
            print(f"[leds] pyserial no disponible -> modo log (sin dispositivo)")
            return
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=0.2)
            self._connected = True
            print(f"[leds] conectado a {self.port} @ {self.baud}")
        except Exception as exc:  # dispositivo ausente/ocupado
            print(f"[leds] sin dispositivo en {self.port} ({exc}) -> modo log")

    @property
    def connected(self) -> bool:
        return self._connected

    def _send(self, line: str) -> None:
        if self._connected and self._ser is not None:
            try:
                self._ser.write((line + "\n").encode("ascii", "ignore"))
            except Exception as exc:
                print(f"[leds] error de escritura ({exc}); paso a modo log")
                self._connected = False
        else:
            print(f"[leds:log] {line}")

    # --- API de alto nivel usada por el MissionController ---
    def idle(self) -> None:
        self._send("IDLE")

    def off(self) -> None:
        self._send("OFF")

    def animate_segment(self, seg_id: int, anim: str) -> None:
        self._send(f"SEG:{seg_id}:{anim}")

    def animate_segments(self, seg_ids, anim: str) -> None:
        for sid in seg_ids:
            self._send(f"SEG:{sid}:{anim}")

    def animate_all(self, anim: str) -> None:
        self._send(f"ALL:{anim}")

    def path_to_role(self, role: str, anim: str = seg.ANIM_FOCUS) -> None:
        self.animate_segments(seg.segments_for_role(role), anim)

    def close(self) -> None:
        if self._ser is not None:
            try:
                self.off()
                self._ser.close()
            except Exception:
                pass
        self._connected = False
