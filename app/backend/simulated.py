"""Motor Simulado: ningun comando toca la red real. Respuestas guionadas con el
mismo contenido que el motor Real, con sleeps que imitan los tiempos. Es el default
de desarrollo y el fallback en vivo si algo se cae (secciones 9 y 11 del plan).
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from app.backend.base import NetworkBackend
from app.backend.browser import open_app_mode
from app.backend.models import (
    DirEntry,
    ExploitResult,
    Host,
    InspectResult,
    LsResult,
    PortResult,
    ReadResult,
    ScanResult,
)

_SERVICE_BY_PORT = {22: "ssh", 80: "http", 5000: "http-alt", 443: "https"}

# Arbol de archivos del file-server (metodos ls/read)
_FS = {
    "/": ["public", "users", "logs", "restricted"],
    "/public": ["index.html", "readme.txt"],
    "/users": ["admin", "guest"],
    "/logs": ["access.log", "auth.log"],
    "/restricted": ["secret.txt"],
}
_SECRET = (
    "==================== ACCESO CONCEDIDO ====================\n"
    " FLAG{c4ptur4st3_3l_s3cr3t0_d3_l4_r3d}\n"
    "\n"
    " Bien hecho. Recuperaste el archivo restringido del servidor.\n"
    " Escaneaste la red, encontraste un servicio vulnerable y lo\n"
    " explotaste para llegar hasta aca. Eso es, en esencia, lo que\n"
    " hace un atacante real -- y por que la seguridad importa.\n"
    "=========================================================\n"
)


_LOGIN_HTML = """<!DOCTYPE html>
<!--
  ==========================================================================
  NOTA DEV (BORRAR ANTES DE PRODUCCION):
  credenciales de prueba -> usuario={user}  clave={pwd}
  ==========================================================================
-->
<html lang="es"><head><meta charset="utf-8"><title>FILE-SERVER :: Acceso</title>
<style>
 body {{ background:#0a0e0a; color:#c8facc; font-family:Consolas,monospace;
        display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }}
 .box {{ border:2px solid #39ff14; border-radius:10px; padding:32px 40px; width:340px;
        box-shadow:0 0 24px rgba(57,255,20,.25); }}
 h1 {{ color:#39ff14; font-size:20px; letter-spacing:2px; text-align:center; }}
 label {{ display:block; margin:14px 0 4px; color:#3a6b3a; font-size:13px; }}
 input {{ width:100%; box-sizing:border-box; background:#0d130d; border:1px solid #2a5a2a;
         color:#e8ffe8; padding:9px; font-family:inherit; border-radius:4px; }}
 button {{ margin-top:20px; width:100%; background:#39ff14; color:#04140a; border:0;
          padding:11px; font-weight:bold; font-family:inherit; border-radius:4px; }}
 .hint {{ color:#243; font-size:11px; text-align:center; margin-top:18px; }}
 .sim {{ color:#ffb000; font-size:11px; text-align:center; margin-top:8px; }}
</style></head><body>
 <div class="box">
   <h1>FILE-SERVER</h1>
   <form onsubmit="return false;">
     <label>usuario</label><input autocomplete="off" autofocus>
     <label>clave</label><input type="password" autocomplete="off">
     <input type="hidden" id="dev-cred" data-user="{user}" data-pass="{pwd}">
     <button type="submit">INGRESAR</button>
   </form>
   <div class="hint">acceso restringido &bull; solo personal autorizado</div>
   <div class="sim">[ pagina de demostracion - modo simulado ]</div>
 </div>
</body></html>
"""


class SimulatedBackend(NetworkBackend):
    def __init__(self, cfg):
        super().__init__(cfg)
        self._page_path = None

    def connect(self, ip, port):
        # En simulado NO hay servidor real: servimos una copia local del login
        # (con las credenciales filtradas en el HTML) para que 'connect' y el
        # metodo 'leak' (Inspeccionar) funcionen 100% offline.
        html = _LOGIN_HTML.format(user=self.cfg.creds.leak_user, pwd=self.cfg.creds.leak_pass)
        f = Path(tempfile.gettempdir()) / "cyberlab_login.html"
        f.write_text(html, encoding="utf-8")
        self._page_path = f
        url = f.as_uri()
        self._browser_proc = open_app_mode(url)
        return url

    def is_dir(self, path: str) -> bool:
        return (path.rstrip("/") or "/") in _FS

    def ping(self, ip: str) -> list[str]:
        time.sleep(0.4)
        host = self.cfg.host_by_ip(ip)
        if host is None:
            return [f"ping: {ip} no responde (host desconocido)"]
        out = [f"PING {ip} ({host.name}): 56 data bytes"]
        for i in range(3):
            out.append(f"64 bytes desde {ip}: icmp_seq={i} ttl=64 tiempo={12 + i}.{i}3 ms")
        out.append("--- estadisticas: 3 enviados, 3 recibidos, 0% perdida ---")
        return out

    def scan(self) -> ScanResult:
        time.sleep(1.6)
        # Todos menos la propia terminal aparecen como "descubiertos"
        hosts = [Host(h.ip, h.name, h.role, list(h.ports)) for h in self.cfg.hosts]
        return ScanResult(hosts=hosts)

    def inspect(self, ip: str) -> InspectResult:
        time.sleep(1.2)
        host = self.cfg.host_by_ip(ip)
        ports = host.ports if (host and host.ports) else [22, 80]
        results = [PortResult(p, "open", _SERVICE_BY_PORT.get(p, "unknown")) for p in ports]
        return InspectResult(ip=ip, ports=results)

    def exploit(self, ip: str, method: str) -> ExploitResult:
        fs = self.cfg.fileserver
        creds = self.cfg.creds
        if ip != fs.ip:
            time.sleep(0.6)
            host = self.cfg.host_by_ip(ip)
            name = host.name if host else ip
            return ExploitResult(False, method, [
                "[*] Objetivo: " + ip + " (" + name + ")",
                "[!] El servicio en " + ip + " no respondio o no es vulnerable.",
                "[!] Estas seguro de que es el servidor correcto?",
            ])
        if method == "leak":
            time.sleep(0.6)
            out = [
                "[*] Descargando pagina de login...",
                "[*] Analizando el codigo fuente (HTML)...",
                f"[+] Credenciales encontradas en un comentario HTML oculto:",
                f"    usuario: {creds.leak_user}",
                f"    clave:   {creds.leak_pass}",
                "[+] ACCESO CONCEDIDO",
            ]
            return ExploitResult(True, "leak", out, creds.leak_user, creds.leak_pass)

        if method == "sqli":
            time.sleep(1.0)
            payload = "' OR '1'='1' -- "
            out = [
                f"[*] POST http://{fs.ip}:{fs.http_port}/login",
                f"[*] usuario = {payload}",
                "[*] La consulta SQL se rompe: WHERE user='' OR '1'='1' -- '",
                "[+] Autenticacion evadida (SQL injection)",
                "[+] ACCESO CONCEDIDO",
            ]
            return ExploitResult(True, "sqli", out, creds.brute_user, None)

        # hydra (fuerza bruta)
        out = [
            "Hydra v9.5 (simulado) starting...",
            f"[DATA] attacking http-post-form://{fs.ip}:{fs.http_port}/login",
        ]
        found = None
        for pw in creds.wordlist:
            time.sleep(0.35)
            if pw == creds.leak_pass:
                out.append(f"[80][http-post-form] host: {fs.ip}   login: {creds.brute_user}   password: {pw}")
                found = pw
                break
            out.append(f"[ATTEMPT] {creds.brute_user}:{pw} - fallo")
        if found is None and creds.wordlist:
            found = creds.wordlist[-1]
            out.append(f"[80][http-post-form] host: {fs.ip}   login: {creds.brute_user}   password: {found}")
        out.append("[+] 1 valid password found")
        out.append("[+] ACCESO CONCEDIDO")
        return ExploitResult(True, "hydra", out, creds.brute_user, found)

    def ls(self, path: str) -> LsResult:
        time.sleep(0.4)
        path = path.rstrip("/") or "/"
        names = _FS.get(path, [])
        entries = [DirEntry(n, is_dir=("." not in n)) for n in names]
        return LsResult(path=path, entries=entries)

    def read(self, path: str) -> ReadResult:
        time.sleep(0.5)
        if path.rstrip("/").endswith("secret.txt"):
            return ReadResult(path=path, content=_SECRET)
        return ReadResult(path=path, content=f"[sin contenido para {path}]")
