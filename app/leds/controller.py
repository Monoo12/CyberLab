"""Controlador de la tira LED por USB serial.

Protocolo de lineas (mismo que el firmware):
    IDLE                -> shimmer tenue de espera
    OFF                 -> apaga todo
    SEG:<id>:<anim>     -> anima un segmento (y su nodo del final titila "procesando")
    ALL:<anim>          -> anima todos los segmentos
    NODE:<id>:<anim>    -> anima solo el LED de un nodo (0 switch-izq, 1 router, 2 switch-der)
    PIX:<rangos>:<anim> -> anima LEDs sueltos (ej. 0-9,40-50) y apaga el resto
    ADD:<rangos>:<anim> -> idem, sin apagar el resto
(la app usa IDLE/OFF/SEG/ALL; NODE/PIX/ADD quedan para pruebas y efectos a mano)

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
            # Abrir sin activar DTR/RTS: en el NodeMCU esas lineas van a RST y GPIO0.
            ser = serial.Serial()
            ser.port = self.port
            ser.baudrate = self.baud
            ser.timeout = 0.2
            ser.dtr = False
            ser.rts = False
            ser.open()
            self._ser = ser
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

    def animate_node(self, node_id: int, anim: str = seg.ANIM_PROCESS) -> None:
        self._send(f"NODE:{node_id}:{anim}")

    def animate_pixels(self, ranges: str, anim: str, replace: bool = True) -> None:
        """LEDs sueltos por numero (desde 0), ej. "0-12,35-53". replace=False no apaga el resto."""
        self._send(f"{'PIX' if replace else 'ADD'}:{ranges}:{anim}")

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
