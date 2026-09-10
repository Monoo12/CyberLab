"""Motor Real: los comandos ejecutan de verdad contra la red y el nodo.

  scan     -> nmap -sn <cidr>   (o arp-scan)     [subprocess, sin shell=True]
  inspect  -> nmap -p <ports> <ip>
  exploit  -> app/exploits/{leak,sqli,bruteforce}
  ls/read  -> SSH real (paramiko) contra el FILE-SERVER

Nunca se pasa texto del visitante a una shell: los argumentos ya vienen tipados y
validados por el parser (app/mission/commands.py); aca se usan listas de argumentos.
El mundo virtual "/" mapea a fileserver.base_path en el nodo.
"""
from __future__ import annotations

import posixpath
import re
import shutil
import subprocess

from app.backend.base import NetworkBackend
from app.backend.models import (DirEntry, ExploitResult, Host, InspectResult,
                                LsResult, PortResult, ReadResult, ScanResult)
from app.exploits import bruteforce, html_leak, sqli

_SERVICE_BY_PORT = {22: "ssh", 80: "http", 443: "https", 5000: "http-alt"}


class RealBackend(NetworkBackend):
    def __init__(self, cfg):
        super().__init__(cfg)
        self._ssh = None

    # ------------------------------ scan ------------------------------
    def scan(self) -> ScanResult:
        tool = self.cfg.network.scan_tool
        if tool == "arp-scan" and shutil.which("arp-scan"):
            cmd = ["arp-scan", "--interface=" + self.cfg.network.interface,
                   self.cfg.network.cidr]
        else:
            nmap = shutil.which("nmap")
            if not nmap:
                raise RuntimeError("nmap no esta instalado (o usa scan_tool='arp-scan').")
            cmd = [nmap, "-sn", self.cfg.network.cidr]

        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
        ips = re.findall(r"(\d{1,3}(?:\.\d{1,3}){3})", out)
        seen, hosts = set(), []
        for ip in ips:
            if ip in seen or ip.endswith(".0") or ip.endswith(".255"):
                continue
            seen.add(ip)
            known = self.cfg.host_by_ip(ip)
            if known:
                hosts.append(Host(ip, known.name, known.role, list(known.ports)))
            else:
                hosts.append(Host(ip, ip, "unknown", []))
        if not hosts:
            raise RuntimeError("El escaneo no devolvio hosts (revisa red/permisos).")
        return ScanResult(hosts=hosts)

    # ----------------------------- inspect ----------------------------
    def inspect(self, ip: str) -> InspectResult:
        nmap = shutil.which("nmap")
        if not nmap:
            raise RuntimeError("nmap no esta instalado.")
        known = self.cfg.host_by_ip(ip)
        ports = known.ports if (known and known.ports) else [22, 80, 5000]
        cmd = [nmap, "-p", ",".join(str(p) for p in ports), ip]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
        results = []
        for m in re.finditer(r"^(\d+)/tcp\s+(\w+)\s+(\S+)", out, re.M):
            results.append(PortResult(int(m.group(1)), m.group(2), m.group(3)))
        if not results:
            results = [PortResult(p, "open", _SERVICE_BY_PORT.get(p, "unknown")) for p in ports]
        return InspectResult(ip=ip, ports=results)

    # ----------------------------- exploit ----------------------------
    def exploit(self, method: str) -> ExploitResult:
        if method == "leak":
            return html_leak.run(self.cfg)
        if method == "sqli":
            return sqli.run(self.cfg)
        return bruteforce.run(self.cfg)

    # ------------------------------ SSH -------------------------------
    def _ssh_client(self):
        import paramiko

        if self._ssh is not None:
            return self._ssh
        cli = paramiko.SSHClient()
        cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cli.connect(
            self.cfg.fileserver.ip,
            port=self.cfg.fileserver.ssh_port,
            username=self.cfg.fileserver.ssh_user,
            password=self.cfg.creds.leak_pass,  # el usuario ctf del nodo usa esta clave
            timeout=8,
            allow_agent=False,
            look_for_keys=False,
        )
        self._ssh = cli
        return cli

    def _real_path(self, vpath: str) -> str:
        vpath = "/" + vpath.strip().lstrip("/")
        real = posixpath.normpath(posixpath.join(self.cfg.fileserver.base_path, vpath.lstrip("/")))
        base = self.cfg.fileserver.base_path
        if not (real == base or real.startswith(base + "/")):
            real = base  # evita salir de la raiz virtual
        return real

    def _run(self, argv) -> str:
        cli = self._ssh_client()
        _in, out, err = cli.exec_command(" ".join(argv), timeout=8)
        return out.read().decode("utf-8", "ignore")

    def ls(self, path: str) -> LsResult:
        real = self._real_path(path)
        text = self._run(["ls", "-1p", "--", "'" + real + "'"])
        entries = []
        for line in text.splitlines():
            name = line.strip()
            if not name:
                continue
            is_dir = name.endswith("/")
            entries.append(DirEntry(name.rstrip("/"), is_dir))
        return LsResult(path="/" + path.strip().lstrip("/"), entries=entries)

    def read(self, path: str) -> ReadResult:
        real = self._real_path(path)
        content = self._run(["cat", "--", "'" + real + "'"])
        return ReadResult(path=path, content=content or "[archivo vacio o inexistente]")

    def is_dir(self, path: str) -> bool:
        real = self._real_path(path)
        out = self._run(["test", "-d", "'" + real + "'", "&&", "echo", "DIR"])
        return "DIR" in out

    def ping(self, ip: str) -> list[str]:
        import sys as _sys
        flag = "-n" if _sys.platform.startswith("win") else "-c"
        try:
            out = subprocess.run(["ping", flag, "3", ip], capture_output=True,
                                 text=True, timeout=20).stdout
        except Exception as exc:
            return [f"ping: error ({exc})"]
        return out.splitlines() or [f"ping {ip}: sin respuesta"]

    def close(self):
        super().close()
        if self._ssh is not None:
            try:
                self._ssh.close()
            except Exception:
                pass
            self._ssh = None
