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

Se reconecta solo: si el ESP no estaba al arrancar o se desenchufa en medio, cada
comando nuevo reintenta abrir el puerto (a lo sumo cada RETRY_SECONDS), asi los LEDs
vuelven sin reiniciar el kiosco.
"""
from __future__ import annotations

import threading
import time

from app.leds import segments as seg

try:
    import serial  # pyserial
except Exception:  # pragma: no cover - opcional
    serial = None


class LedController:
    RETRY_SECONDS = 3.0  # sin dispositivo: cada cuanto se reintenta abrir el puerto
    BOOT_SECONDS = 1.5   # al abrir, el NodeMCU se reinicia (ver _try_connect): lo que llegue
                         # mientras bootea se encola y sale despues, en orden

    def __init__(self, port: str, baud: int = 115200, enabled: bool = True):
        self.port = port
        self.baud = baud
        self.enabled = enabled
        self._ser = None
        self._connected = False
        self._closed = False
        self._lock = threading.RLock()  # _send (hilo de Tk) vs. el timer que vacia la cola
        self._next_retry = 0.0
        self._ready_at = 0.0
        self._pending: list[str] = []
        self._flush_timer = None
        self._warned = False  # ya se aviso que no hay dispositivo: no repetirlo en cada reintento
        if enabled:
            self._try_connect()

    def _try_connect(self) -> None:
        self._next_retry = time.monotonic() + self.RETRY_SECONDS
        if serial is None:
            if not self._warned:
                print(f"[leds] pyserial no disponible -> modo log (sin dispositivo)")
                self._warned = True
            return
        try:
            # DTR/RTS en False: en el NodeMCU van a RST y GPIO0 (asi un reset nunca lo deja
            # en modo flasheo). Ojo: en Linux el kernel igual las pulsa al abrir y el ESP se
            # reinicia; por eso lo que se mande en los primeros BOOT_SECONDS se encola.
            ser = serial.Serial()
            ser.port = self.port
            ser.baudrate = self.baud
            ser.timeout = 0.2
            ser.write_timeout = 0.5  # un USB colgado no debe congelar la UI
            ser.dtr = False
            ser.rts = False
            ser.open()
            self._ser = ser
            self._connected = True
            self._warned = False
            self._ready_at = time.monotonic() + self.BOOT_SECONDS
            print(f"[leds] conectado a {self.port} @ {self.baud}")
        except Exception as exc:  # dispositivo ausente/ocupado
            if not self._warned:
                print(f"[leds] sin dispositivo en {self.port} ({exc}) -> modo log; "
                      f"reintento cada {self.RETRY_SECONDS:.0f}s")
                self._warned = True

    @property
    def connected(self) -> bool:
        return self._connected

    def _drop(self) -> None:
        """Suelta el puerto (libera el ttyUSB para cuando se re-enchufe) y deja reintentar ya."""
        if self._flush_timer is not None:
            self._flush_timer.cancel()
            self._flush_timer = None
        self._pending.clear()
        try:
            if self._ser is not None:
                self._ser.close()
        except Exception:
            pass
        self._ser = None
        self._connected = False
        self._next_retry = 0.0

    def _write(self, line: str) -> None:
        try:
            self._ser.write((line + "\n").encode("ascii", "ignore"))
        except Exception as exc:
            print(f"[leds] error de escritura ({exc}); se perdio el dispositivo, reintento")
            self._drop()

    def _flush(self) -> None:
        with self._lock:
            self._flush_timer = None
            lines, self._pending = self._pending, []
            for line in lines:
                if not self._connected:
                    break
                self._write(line)

    def _send(self, line: str) -> None:
        with self._lock:
            if (self.enabled and not self._closed and not self._connected
                    and time.monotonic() >= self._next_retry):
                self._try_connect()
            if not self._connected:
                print(f"[leds:log] {line}")
                return
            wait = self._ready_at - time.monotonic()
            if wait > 0 or self._pending:
                self._pending.append(line)
                if self._flush_timer is None:
                    self._flush_timer = threading.Timer(max(wait, 0.0), self._flush)
                    self._flush_timer.daemon = True
                    self._flush_timer.start()
                return
            self._write(line)

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
        with self._lock:
            self._closed = True  # que ningun comando tardio lo vuelva a abrir
            if self._connected:
                self._pending.clear()
                self._write("OFF")
            self._drop()
