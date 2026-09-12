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
    def inspect(self, ip: str, versions: bool = False) -> InspectResult:
        nmap = shutil.which("nmap")
        if not nmap:
            raise RuntimeError("nmap no esta instalado.")
        known = self.cfg.host_by_ip(ip)
        ports = known.ports if (known and known.ports) else [22, 80, 5000]
        cmd = [nmap, "-p", ",".join(str(p) for p in ports)]
        if versions:
            cmd.append("-sV")
        cmd.append(ip)
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=180).stdout
        results = []
        for m in re.finditer(r"^(\d+)/tcp\s+(\w+)\s+(\S+)(?:\s+(.*))?$", out, re.M):
            svc = m.group(3)
            if versions and m.group(4):
                svc = svc + " " + m.group(4).strip()
            results.append(PortResult(int(m.group(1)), m.group(2), svc))
        if not results:
            results = [PortResult(p, "open", _SERVICE_BY_PORT.get(p, "unknown")) for p in ports]
        return InspectResult(ip=ip, ports=results)

    # ----------------------------- exploit ----------------------------
    def exploit(self, ip: str, method: str) -> ExploitResult:
        # El ataque apunta a la IP indicada: si no es el FILE-SERVER vulnerable,
        # las peticiones HTTP fallan y el exploit devuelve fallo (comportamiento real).
        base_url = "http://%s:%s" % (ip, self.cfg.fileserver.http_port)
        if method == "leak":
            return html_leak.run(self.cfg, base_url)
        if method == "sqli":
            return sqli.run(self.cfg, base_url)
        return bruteforce.run(self.cfg, base_url)

    # ------------------------------ SSH -------------------------------
    def _ssh_client(self, ip):
        import paramiko

        if not hasattr(self, "_ssh_by_ip"):
            self._ssh_by_ip = {}
        if ip in self._ssh_by_ip:
            return self._ssh_by_ip[ip]
        fs = self.cfg.fileserver
        port = fs.ssh_port if ip == fs.ip else 22
        cli = paramiko.SSHClient()
        cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        cli.connect(
            ip, port=port,
            username=fs.ssh_user,
            password=self.cfg.creds.leak_pass,
            timeout=8, allow_agent=False, look_for_keys=False,
        )
        self._ssh_by_ip[ip] = cli
        return cli

    def _real_path(self, ip, vpath: str) -> str:
        # El mapeo a base_path solo aplica al FILE-SERVER; otros hosts usan la ruta tal cual.
        vpath = "/" + vpath.strip().lstrip("/")
        if ip != self.cfg.fileserver.ip:
            return vpath
        base = self.cfg.fileserver.base_path
        real = posixpath.normpath(posixpath.join(base, vpath.lstrip("/")))
        if not (real == base or real.startswith(base + "/")):
            real = base
        return real

    def _run(self, ip, argv) -> str:
        cli = self._ssh_client(ip)
        _in, out, err = cli.exec_command(" ".join(argv), timeout=8)
        return out.read().decode("utf-8", "ignore")

    def ls(self, ip: str, path: str) -> LsResult:
        real = self._real_path(ip, path)
        text = self._run(ip, ["ls", "-1p", "--", "'" + real + "'"])
        entries = []
        for line in text.splitlines():
            name = line.strip()
            if not name:
                continue
            entries.append(DirEntry(name.rstrip("/"), name.endswith("/")))
        return LsResult(path="/" + path.strip().lstrip("/"), entries=entries)

    def read(self, ip: str, path: str) -> ReadResult:
        real = self._real_path(ip, path)
        content = self._run(ip, ["cat", "--", "'" + real + "'"])
        return ReadResult(path=path, content=content or "[archivo vacio o inexistente]")

    def is_dir(self, ip: str, path: str) -> bool:
        real = self._real_path(ip, path)
        out = self._run(ip, ["test", "-d", "'" + real + "'", "&&", "echo", "DIR"])
        return "DIR" in out

    # ------------------------- recon extra -------------------------
    def ping(self, ip: str) -> list[str]:
        import sys as _sys
        flag = "-n" if _sys.platform.startswith("win") else "-c"
        try:
            out = subprocess.run(["ping", flag, "3", ip], capture_output=True,
                                 text=True, timeout=20).stdout
        except Exception as exc:
            return [f"ping: error ({exc})"]
        return out.splitlines() or [f"ping {ip}: sin respuesta"]

    def telnet(self, ip: str, port: int) -> list[str]:
        import socket
        out = [f"Trying {ip}:{port}..."]
        try:
            with socket.create_connection((ip, port), timeout=5) as s:
                out.append(f"Connected to {ip}.")
                s.settimeout(2.5)
                try:
                    banner = s.recv(256).decode("utf-8", "ignore").strip()
                    if banner:
                        out.append(banner)
                except Exception:
                    pass
        except Exception as exc:
            return [f"telnet: no se puede conectar a {ip}:{port} ({exc})"]
        return out

    def traceroute(self, ip: str) -> list[str]:
        import sys as _sys
        cmd = ["tracert", "-d", "-h", "10", ip] if _sys.platform.startswith("win") \
            else ["traceroute", "-m", "10", ip]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
        except Exception as exc:
            return [f"traceroute: error ({exc})"]
        return out.splitlines() or [f"traceroute {ip}: sin salida"]

    def arp(self, ips) -> list[str]:
        try:
            out = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=15).stdout
        except Exception as exc:
            return [f"arp: error ({exc})"]
        return out.splitlines() or ["arp: sin entradas"]

    def netstat(self, ip: str) -> list[str]:
        import sys as _sys
        cmd = ["netstat", "-an"] if _sys.platform.startswith("win") else ["netstat", "-tuln"]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout
        except Exception as exc:
            return [f"netstat: error ({exc})"]
        return out.splitlines()[:30] or ["netstat: sin salida"]

    def close(self):
        super().close()
        for cli in getattr(self, "_ssh_by_ip", {}).values():
            try:
                cli.close()
            except Exception:
                pass
        self._ssh_by_ip = {}
