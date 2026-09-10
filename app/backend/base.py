"""Interfaz comun de red. La terminal y el mapa visual siempre hablan con esta
interfaz sin saber si atras corre el motor Real o el Simulado (seccion 9 del plan).

Los backends son PUROS de red/datos: no tocan LEDs ni UI. La orquestacion visual
(LEDs + mapa + tiempos) vive en el MissionController.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.backend.browser import open_app_mode
from app.backend.models import ExploitResult, InspectResult, LsResult, ReadResult, ScanResult
from app.config import Config


class NetworkBackend(ABC):
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._browser_proc = None

    @abstractmethod
    def scan(self) -> ScanResult:
        """Descubre hosts en la red (nmap -sn / arp-scan)."""

    @abstractmethod
    def inspect(self, ip: str) -> InspectResult:
        """Escanea puertos de un host (nmap -p ...)."""

    @abstractmethod
    def exploit(self, method: str) -> ExploitResult:
        """Ejecuta una de las 3 tecnicas: 'leak' | 'sqli' | 'hydra'."""

    @abstractmethod
    def ls(self, path: str) -> LsResult:
        """Lista un directorio del file-server (SSH)."""

    @abstractmethod
    def read(self, path: str) -> ReadResult:
        """Lee un archivo del file-server (SSH)."""

    def is_dir(self, path: str) -> bool:
        """True si `path` es un directorio (para validar `cd`). Default: via ls."""
        try:
            return len(self.ls(path).entries) > 0 or path.rstrip("/") in ("", "/")
        except Exception:
            return False

    def ping(self, ip: str) -> list[str]:
        """Devuelve lineas de salida de un ping (real o simulado)."""
        return [f"PING {ip}: sin implementar"]

    # `connect` es identico en ambos motores: abre el navegador real.
    def connect(self, ip: str, port: int):
        url = f"http://{ip}:{port}"
        self._browser_proc = open_app_mode(url)
        return url

    def close_browser(self) -> None:
        if self._browser_proc is not None:
            try:
                self._browser_proc.terminate()
            except Exception:
                pass
            self._browser_proc = None

    def close(self) -> None:
        self.close_browser()
