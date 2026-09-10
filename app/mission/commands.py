"""Parser de comandos con lista blanca (seccion 9 del plan).

NUNCA se pasa el texto del visitante a una shell. Cada comando matchea un patron
regex conocido; se extraen argumentos tipados y la IP se valida contra el CIDR del
laboratorio. Si no matchea nada -> se marca error y la terminal muestra ayuda.

Acepta SIEMPRE las dos sintaxis (no depende de la dificultad):
  - guiada:  scan / inspect <ip> / connect <ip:puerto> / exploit [metodo] / ls / read ...
  - real:    nmap -sn <cidr> / nmap -p ... <ip> / hydra ... / curl ' OR '1'='1 ...
La dificultad solo cambia CUANTO te guia la terminal (ver mission/script.py y flow.py).
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

VALID_METHODS = ("leak", "sqli", "hydra")


@dataclass
class ParsedCommand:
    name: str  # scan|inspect|connect|exploit|ls|read|cd|pwd|whoami|ping|clear|help|hint|menu|empty
    ip: str | None = None
    port: int | None = None
    path: str | None = None
    method: str | None = None
    error: str | None = None


_IP = r"(\d{1,3}(?:\.\d{1,3}){3})"


class CommandParser:
    def __init__(self, cidr: str):
        try:
            self.network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            self.network = None

    def ip_in_lab(self, ip: str) -> bool:
        if self.network is None:
            return True
        try:
            return ipaddress.ip_address(ip) in self.network
        except ValueError:
            return False

    # --------------------------------------------------------------
    def parse(self, line: str) -> ParsedCommand:
        text = line.strip()
        if not text:
            return ParsedCommand("empty")
        low = text.lower()

        # comandos simples de una palabra
        if low in ("help", "ayuda", "?"):
            return ParsedCommand("help")
        if low in ("hint", "pista"):
            return ParsedCommand("hint")
        if low in ("clear", "cls", "limpiar"):
            return ParsedCommand("clear")
        if low in ("pwd",):
            return ParsedCommand("pwd")
        if low in ("whoami",):
            return ParsedCommand("whoami")
        if low in ("menu", "volver", "atras", "back"):
            return ParsedCommand("menu")

        # cd <dir>  (o 'cd' solo -> raiz)
        if low == "cd":
            return ParsedCommand("cd", path="/")
        m = re.fullmatch(r"cd\s+(\S+)", text)
        if m:
            return ParsedCommand("cd", path=m.group(1))

        # ls [ruta]
        if low == "ls" or low.startswith("ls "):
            return ParsedCommand("ls", path=text[3:].strip() or None)
        # read|cat <ruta>
        m = re.fullmatch(r"(?:read|cat)\s+(\S+)", text, re.I)
        if m:
            return ParsedCommand("read", path=m.group(1))

        # connect <ip:puerto>  (identico en toda dificultad)
        m = re.fullmatch(rf"connect\s+{_IP}[:\s]+(\d{{1,5}})", low)
        if m:
            return self._make_connect(m.group(1), m.group(2))

        # ping <ip>
        m = re.fullmatch(rf"ping\s+(?:-[a-z]\s+\d+\s+)?{_IP}", low)
        if m:
            ip = m.group(1)
            if not self.ip_in_lab(ip):
                return ParsedCommand("ping", error=f"IP fuera del laboratorio: {ip}")
            return ParsedCommand("ping", ip=ip)

        # ---- scan (guiado o nmap -sn) ----
        if low == "scan":
            return ParsedCommand("scan")
        if re.search(r"\bnmap\b", low) and re.search(r"-sn\b", low):
            return ParsedCommand("scan")

        # ---- inspect (guiado o nmap -p / nmap <ip>) ----
        m = re.fullmatch(rf"inspect\s+{_IP}", low)
        if m:
            return self._make_inspect(m.group(1))
        m = re.search(rf"\bnmap\b.*?-p\s*[\d,]+\s+{_IP}", low)
        if m:
            return self._make_inspect(m.group(1))
        m = re.search(rf"\bnmap\b.*?{_IP}", low)
        if m:
            return self._make_inspect(m.group(1))

        # ---- exploit (guiado / hydra / curl) ----
        m = re.fullmatch(r"exploit(?:\s+(\w+))?", low)
        if m:
            method = m.group(1)
            if method and method not in VALID_METHODS:
                return ParsedCommand("exploit", error=f"metodo desconocido '{method}' (leak | sqli | hydra)")
            return ParsedCommand("exploit", method=method)
        if re.search(r"\bhydra\b", low):
            return ParsedCommand("exploit", method="hydra")
        if re.search(r"\bcurl\b", low):
            method = "sqli" if ("'1'='1" in low or "1=1" in low or "--" in low) else "sqli"
            return ParsedCommand("exploit", method=method)

        return ParsedCommand("empty", error=f"comando no reconocido: {text}")

    # ------------------------------ helpers -----------------------------
    def _make_inspect(self, ip: str) -> ParsedCommand:
        if not self.ip_in_lab(ip):
            return ParsedCommand("inspect", error=f"IP fuera del laboratorio: {ip}")
        return ParsedCommand("inspect", ip=ip)

    def _make_connect(self, ip: str, port_s: str) -> ParsedCommand:
        if not self.ip_in_lab(ip):
            return ParsedCommand("connect", error=f"IP fuera del laboratorio: {ip}")
        try:
            port = int(port_s)
        except ValueError:
            return ParsedCommand("connect", error=f"puerto invalido: {port_s}")
        if not (0 < port < 65536):
            return ParsedCommand("connect", error=f"puerto fuera de rango: {port}")
        return ParsedCommand("connect", ip=ip, port=port)
