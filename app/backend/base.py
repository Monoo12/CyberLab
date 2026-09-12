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
    def inspect(self, ip: str, versions: bool = False) -> InspectResult:
        """Escanea puertos de un host (nmap -p / -sV). `versions` agrega version del servicio."""

    @abstractmethod
    def exploit(self, ip: str, method: str) -> ExploitResult:
        """Ataca el servicio de `ip` ('leak'|'sqli'|'hydra'). En la mision solo el
        FILE-SERVER es vulnerable; en Modo Libre todos los dispositivos con perfil."""

    @abstractmethod
    def ls(self, ip: str, path: str) -> LsResult:
        """Lista un directorio del host `ip` (SSH)."""

    @abstractmethod
    def read(self, ip: str, path: str) -> ReadResult:
        """Lee un archivo del host `ip` (SSH)."""

    def is_dir(self, ip: str, path: str) -> bool:
        """True si `path` es un directorio en `ip` (para validar `cd`)."""
        try:
            return len(self.ls(ip, path).entries) > 0 or path.rstrip("/") in ("", "/")
        except Exception:
            return False

    def fs_names(self, ip: str, path: str) -> list[str]:
        """Nombres de un directorio para autocompletar rutas (sin bloquear). Default: vacio."""
        return []

    def ping(self, ip: str) -> list[str]:
        return [f"PING {ip}: sin implementar"]

    def telnet(self, ip: str, port: int) -> list[str]:
        return [f"telnet {ip}:{port}: sin implementar"]

    def traceroute(self, ip: str) -> list[str]:
        return [f"traceroute {ip}: sin implementar"]

    def arp(self, ips) -> list[str]:
        return ["arp: sin implementar"]

    def netstat(self, ip: str) -> list[str]:
        return ["netstat: sin implementar"]

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
