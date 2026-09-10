"""Carga y validacion de la configuracion del laboratorio.

Usa tomllib (stdlib >= 3.11). El archivo real es config.toml (no versionado);
config.example.toml es la plantilla. Los modos pueden overridearse por CLI.
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from app.backend.models import Host

VALID_ENGINES = ("simulated", "real")
VALID_DIFFICULTIES = ("facil", "medio", "dificil", "pro")


@dataclass
class Modes:
    visual: bool = True
    engine: str = "simulated"
    difficulty: str = "facil"
    autostart: bool = False


@dataclass
class Timing:
    mission_seconds: int = 300
    hint_idle_seconds: int = 40
    typewriter_cps: int = 160


@dataclass
class Network:
    cidr: str = "192.168.10.0/24"
    interface: str = "eth0"
    scan_tool: str = "nmap"


@dataclass
class FileServer:
    ip: str = "192.168.10.20"
    http_port: int = 80
    ssh_port: int = 22
    ssh_user: str = "ctf"
    url: str = "http://192.168.10.20:80"
    secret_path: str = "/restricted/secret.txt"
    base_path: str = "/srv/lab"  # raiz real del arbol en el nodo; "/" del mundo virtual mapea aca


@dataclass
class Creds:
    leak_user: str = "admin"
    leak_pass: str = "S3cr3t-2024!"
    brute_user: str = "admin"
    wordlist: list[str] = field(default_factory=list)


@dataclass
class Serial:
    enabled: bool = True
    port: str = "COM3"
    baud: int = 115200


@dataclass
class Config:
    modes: Modes
    timing: Timing
    network: Network
    fileserver: FileServer
    creds: Creds
    serial: Serial
    hosts: list[Host]

    def host_by_role(self, role: str) -> Host | None:
        return next((h for h in self.hosts if h.role == role), None)

    def host_by_ip(self, ip: str) -> Host | None:
        return next((h for h in self.hosts if h.ip == ip), None)


def _base_dir() -> Path:
    """Directorio base para buscar config: junto al .exe si esta empaquetado
    (PyInstaller), o la raiz del proyecto en desarrollo."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _default_config_path() -> Path:
    """config.toml junto al ejecutable/proyecto; cae a config.example.toml."""
    root = _base_dir()
    real = root / "config.toml"
    if real.exists():
        return real
    return root / "config.example.toml"


def load_config(path: str | Path | None = None, argv: list[str] | None = None) -> Config:
    cfg_path = Path(path) if path else _default_config_path()
    if not cfg_path.exists():
        print(f"[config] No se encontro {cfg_path}", file=sys.stderr)
        sys.exit(1)

    with open(cfg_path, "rb") as fh:
        raw = tomllib.load(fh)

    m = raw.get("modes", {})
    modes = Modes(
        visual=bool(m.get("visual", True)),
        engine=str(m.get("engine", "simulated")),
        difficulty=str(m.get("difficulty", "facil")),
        autostart=bool(m.get("autostart", False)),
    )
    t = raw.get("timing", {})
    timing = Timing(
        mission_seconds=int(t.get("mission_seconds", 300)),
        hint_idle_seconds=int(t.get("hint_idle_seconds", 40)),
        typewriter_cps=int(t.get("typewriter_cps", 160)),
    )
    n = raw.get("network", {})
    network = Network(
        cidr=str(n.get("cidr", "192.168.10.0/24")),
        interface=str(n.get("interface", "eth0")),
        scan_tool=str(n.get("scan_tool", "nmap")),
    )
    f = raw.get("fileserver", {})
    fileserver = FileServer(
        ip=str(f.get("ip", "192.168.10.20")),
        http_port=int(f.get("http_port", 80)),
        ssh_port=int(f.get("ssh_port", 22)),
        ssh_user=str(f.get("ssh_user", "ctf")),
        url=str(f.get("url", "http://192.168.10.20:80")),
        secret_path=str(f.get("secret_path", "/restricted/secret.txt")),
        base_path=str(f.get("base_path", "/srv/lab")),
    )
    c = raw.get("creds", {})
    creds = Creds(
        leak_user=str(c.get("leak_user", "admin")),
        leak_pass=str(c.get("leak_pass", "S3cr3t-2024!")),
        brute_user=str(c.get("brute_user", "admin")),
        wordlist=list(c.get("wordlist", [])),
    )
    s = raw.get("serial", {})
    serial = Serial(
        enabled=bool(s.get("enabled", True)),
        port=str(s.get("port", "COM3")),
        baud=int(s.get("baud", 115200)),
    )
    hosts = [
        Host(
            ip=str(h["ip"]),
            name=str(h.get("name", h["ip"])),
            role=str(h.get("role", "unknown")),
            ports=list(h.get("ports", [])),
        )
        for h in raw.get("hosts", [])
    ]

    cfg = Config(modes, timing, network, fileserver, creds, serial, hosts)
    _apply_cli_overrides(cfg, argv)
    _validate(cfg)
    return cfg


def _apply_cli_overrides(cfg: Config, argv: list[str] | None) -> None:
    parser = argparse.ArgumentParser(description="Cyber Lab - app del visitante")
    parser.add_argument("--engine", choices=VALID_ENGINES)
    parser.add_argument("--difficulty", choices=VALID_DIFFICULTIES)
    parser.add_argument("--no-visual", action="store_true")
    parser.add_argument("--visual", action="store_true")
    parser.add_argument("--autostart", action="store_true")
    parser.add_argument("--menu", action="store_true", help="forzar el menu de setup")
    args, _ = parser.parse_known_args(argv)

    if args.engine:
        cfg.modes.engine = args.engine
    if args.difficulty:
        cfg.modes.difficulty = args.difficulty
    if args.no_visual:
        cfg.modes.visual = False
    if args.visual:
        cfg.modes.visual = True
    if args.autostart:
        cfg.modes.autostart = True
    if args.menu:
        cfg.modes.autostart = False


def _validate(cfg: Config) -> None:
    if cfg.modes.engine not in VALID_ENGINES:
        raise ValueError(f"engine invalido: {cfg.modes.engine}")
    if cfg.modes.difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"difficulty invalida: {cfg.modes.difficulty}")
    if cfg.host_by_role("fileserver") is None:
        raise ValueError("config: falta un host con role='fileserver'")
