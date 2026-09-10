"""Modelos de datos compartidos por los backends (real y simulado).

Los backends devuelven estas dataclasses (nunca strings crudos) para que la
terminal, el mapa visual y el controlador de LEDs consuman datos estructurados.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Host:
    ip: str
    name: str
    role: str  # router | terminal | fileserver | workstation | security
    ports: list[int] = field(default_factory=list)


@dataclass
class PortResult:
    port: int
    state: str      # "open" | "closed" | "filtered"
    service: str


@dataclass
class ScanResult:
    hosts: list[Host]


@dataclass
class InspectResult:
    ip: str
    ports: list[PortResult]


@dataclass
class ExploitResult:
    success: bool
    method: str                 # "leak" | "sqli" | "hydra"
    output: list[str]           # lineas a "tipear" en la terminal
    username: str | None = None
    password: str | None = None


@dataclass
class DirEntry:
    name: str
    is_dir: bool


@dataclass
class LsResult:
    path: str
    entries: list[DirEntry]


@dataclass
class ReadResult:
    path: str
    content: str
