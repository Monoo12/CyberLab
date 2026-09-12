"""Motor Simulado: ningun comando toca la red real. Respuestas guionadas con el
mismo contenido que el motor Real, con sleeps que imitan los tiempos. Es el default
de desarrollo y el fallback en vivo si algo se cae.

Cada dispositivo tiene un "perfil" (puertos+versiones, banners, filesystem, flag y
si es hackeable). En la MISION normal solo el FILE-SERVER es el objetivo; en MODO
LIBRE (cfg.modes.free_mode) todos los dispositivos con perfil son hackeables.
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

# --------------------------------------------------------------------------
# Perfiles de dispositivo (por role). Puertos: (numero, servicio, version).
# --------------------------------------------------------------------------
_FS_SECRET = (
    "==================== ACCESO CONCEDIDO ====================\n"
    " FLAG{c4ptur4st3_3l_s3cr3t0_d3_l4_r3d}\n"
    "\n"
    " Bien hecho. Recuperaste el archivo restringido del servidor.\n"
    " Escaneaste la red, encontraste un servicio vulnerable y lo\n"
    " explotaste para llegar hasta aca. Eso es, en esencia, lo que\n"
    " hace un atacante real -- y por que la seguridad importa.\n"
    "=========================================================\n"
)

_DEVICES = {
    "router": {
        "ports": [(22, "ssh", "Dropbear sshd 2019.78"),
                  (23, "telnet", "MikroTik telnetd"),
                  (80, "http", "RouterOS webfig 6.48")],
        "banners": {
            22: "SSH-2.0-dropbear_2019.78",
            23: "MikroTik RouterOS\r\nLogin:",
            80: "HTTP/1.1 200 OK  Server: RouterOS/webfig",
        },
        "vuln": True,
        "user": "admin",
        "exploit": [
            "[*] Probando credenciales por defecto en el panel del router...",
            "[*] admin:admin ...",
            "[+] Login por defecto aceptado (nadie cambio la clave de fabrica).",
            "[+] ACCESO CONCEDIDO",
        ],
        "fs": {
            "/": ["etc", "tmp", "flag.txt"],
            "/etc": ["router.conf", "passwd"],
            "/tmp": [],
        },
        "files": {
            "/flag.txt": "FLAG{r0ut3r_c0n_cl4v3_d3_f4bric4}\nEl router usaba admin/admin. Cambia las claves por defecto.\n",
            "/etc/router.conf": "hostname=router\nadmin_user=admin\nadmin_pass=admin\nwifi_ssid=CyberLab\n",
            "/etc/passwd": "root:x:0:0:root:/root:/bin/sh\nadmin:x:1000:1000:admin:/home/admin:/bin/sh\n",
        },
    },
    "fileserver": {
        "ports": [(22, "ssh", "OpenSSH 8.9p1"),
                  (80, "http", "Apache 2.4.52"),
                  (5000, "http-alt", "Werkzeug/Flask")],
        "banners": {22: "SSH-2.0-OpenSSH_8.9p1", 80: "HTTP/1.1 200 OK  Server: Apache/2.4.52"},
        "vuln": True,  # objetivo de la mision; 3 metodos (leak/sqli/hydra)
        "user": "ctf",
        "fs": {
            "/": ["public", "users", "logs", "restricted"],
            "/public": ["index.html", "readme.txt"],
            "/users": ["admin", "guest"],
            "/logs": ["access.log", "auth.log"],
            "/restricted": ["secret.txt"],
        },
        "files": {"/restricted/secret.txt": _FS_SECRET},
    },
    "workstation": {
        "ports": [(139, "netbios-ssn", "Samba smbd 4.15"),
                  (445, "microsoft-ds", "Samba smbd 4.15"),
                  (3389, "ms-wbt-server", "xrdp")],
        "banners": {445: "SMB 3.1.1  (Samba 4.15)"},
        "vuln": True,
        "user": "usuario",
        "exploit": [
            "[*] Enumerando recursos compartidos SMB...",
            "[+] Share 'Documentos' accesible SIN contrasena (guest ok).",
            "[+] ACCESO CONCEDIDO",
        ],
        "fs": {
            "/": ["Documentos", "Descargas", "flag.txt"],
            "/Documentos": ["notas.txt", "presupuesto.xlsx"],
            "/Descargas": [],
        },
        "files": {
            "/flag.txt": "FLAG{sh4r3_smb_4bi3rt0_p4r4_gu3st}\nUn recurso compartido sin clave expone todo el disco.\n",
            "/Documentos/notas.txt": "recordar cambiar la clave del wifi\nusuario del server: ctf\n",
        },
    },
    "security": {
        "ports": [(22, "ssh", "OpenSSH 9.3p1"),
                  (443, "https", "nginx 1.24"),
                  (8080, "http", "Panel admin (PHP 7.4)")],
        "banners": {443: "HTTP/1.1 200 OK  Server: nginx/1.24", 8080: "HTTP/1.1 200 OK  X-Powered-By: PHP/7.4"},
        "vuln": True,
        "user": "admin",
        "exploit": [
            "[*] Atacando el panel admin en :8080 ...",
            "[*] usuario = ' OR '1'='1' -- ",
            "[+] Panel de seguridad evadido por SQL injection.",
            "[+] ACCESO CONCEDIDO",
        ],
        "fs": {
            "/": ["var", "flag.txt"],
            "/var": ["security"],
            "/var/security": ["flag.txt", "camaras.log"],
        },
        "files": {
            "/flag.txt": "FLAG{p4n3l_d3_s3gurid4d_1ny3ct4bl3}\n",
            "/var/security/flag.txt": "FLAG{c4m4r4s_c0mpr0m3tid4s}\nEl panel confiaba en el input del usuario.\n",
            "/var/security/camaras.log": "cam01 OK\ncam02 OK\ncam03 sin senal\n",
        },
    },
    "terminal": {
        "ports": [(22, "ssh", "OpenSSH 9.3p1")],
        "banners": {},
        "vuln": False,
        "user": "visitante",
        "fs": {"/": ["home"], "/home": ["visitante"], "/home/visitante": ["mision.txt"]},
        "files": {"/home/visitante/mision.txt": "Recupera el secreto del FILE-SERVER.\n"},
    },
}

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
   <h1>{title}</h1>
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


def _profile_for(cfg, ip):
    host = cfg.host_by_ip(ip)
    role = host.role if host else "fileserver"
    return role, _DEVICES.get(role, _DEVICES["fileserver"])


class SimulatedBackend(NetworkBackend):
    def __init__(self, cfg):
        super().__init__(cfg)
        self._page_path = None

    # ------------------------------ connect ------------------------------
    def connect(self, ip, port):
        # En simulado NO hay servidor real: servimos una copia local del login
        # (con las credenciales filtradas en el HTML) para que 'connect' y el
        # metodo 'leak' (Inspeccionar) funcionen 100% offline.
        role, _ = _profile_for(self.cfg, ip)
        host = self.cfg.host_by_ip(ip)
        title = host.name if host else "SERVICIO"
        html = _LOGIN_HTML.format(user=self.cfg.creds.leak_user, pwd=self.cfg.creds.leak_pass,
                                  title=title)
        f = Path(tempfile.gettempdir()) / "cyberlab_login.html"
        f.write_text(html, encoding="utf-8")
        self._page_path = f
        url = f.as_uri()
        self._browser_proc = open_app_mode(url)
        return url

    # ------------------------------ scan ---------------------------------
    def scan(self) -> ScanResult:
        time.sleep(1.6)
        hosts = [Host(h.ip, h.name, h.role, list(h.ports)) for h in self.cfg.hosts]
        return ScanResult(hosts=hosts)

    # ------------------------------ inspect ------------------------------
    def inspect(self, ip: str, versions: bool = False) -> InspectResult:
        time.sleep(1.0)
        _, prof = _profile_for(self.cfg, ip)
        results = []
        for port, service, version in prof["ports"]:
            svc = service + (" " + version if versions else "")
            results.append(PortResult(port, "open", svc))
        return InspectResult(ip=ip, ports=results)

    # ------------------------------ ping ---------------------------------
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

    # ------------------------------ telnet -------------------------------
    def telnet(self, ip: str, port: int) -> list[str]:
        time.sleep(0.4)
        _, prof = _profile_for(self.cfg, ip)
        open_ports = {p for p, _, _ in prof["ports"]}
        if port not in open_ports:
            return [f"telnet: no se puede conectar a {ip}:{port} (conexion rechazada)"]
        banner = prof.get("banners", {}).get(port, f"servicio en {ip}:{port}")
        return [f"Trying {ip}:{port}...", f"Connected to {ip}.", "Escape character is '^]'.", banner]

    # ---------------------------- traceroute -----------------------------
    def traceroute(self, ip: str) -> list[str]:
        router = self.cfg.host_by_role("router")
        hops = []
        out = [f"traceroute a {ip}, maximo 30 saltos:"]
        n = 1
        if router and router.ip != ip:
            hops.append((router.ip, router.name))
        hops.append((ip, (self.cfg.host_by_ip(ip).name if self.cfg.host_by_ip(ip) else ip)))
        for hip, hname in hops:
            time.sleep(0.35)
            out.append(f" {n}  {hname} ({hip})  {2 + n}.{n} ms  {2 + n}.{n + 1} ms")
            n += 1
        return out

    # ------------------------------- arp ---------------------------------
    def arp(self, ips) -> list[str]:
        time.sleep(0.3)
        out = ["Direccion         HWtipo  HWdireccion         Interfaz"]
        for ip in ips:
            octs = ip.split(".")
            mac = "02:%02x:%02x:%02x:%02x:%02x" % (
                int(octs[0]) & 0xFF, int(octs[1]) & 0xFF, int(octs[2]) & 0xFF,
                int(octs[3]) & 0xFF, (int(octs[3]) * 7) & 0xFF)
            out.append(f"{ip.ljust(17)} ether   {mac}   eth0")
        return out

    # ----------------------------- netstat -------------------------------
    def netstat(self, ip: str) -> list[str]:
        time.sleep(0.3)
        return [
            "Proto  Direccion local        Direccion remota       Estado",
            "tcp    " + (ip + ":22").ljust(22) + "0.0.0.0:*".ljust(22) + "LISTEN",
            "tcp    " + (ip + ":80").ljust(22) + "0.0.0.0:*".ljust(22) + "LISTEN",
            "tcp    " + (ip + ":54012").ljust(22) + "192.168.10.10:443".ljust(22) + "ESTABLISHED",
        ]

    # ------------------------------ exploit ------------------------------
    def exploit(self, ip: str, method: str) -> ExploitResult:
        fs = self.cfg.fileserver
        creds = self.cfg.creds
        role, prof = _profile_for(self.cfg, ip)
        free = getattr(self.cfg.modes, "free_mode", False)

        # El FILE-SERVER es el objetivo de la mision: 3 metodos reales.
        if ip == fs.ip:
            return self._exploit_fileserver(method, fs, creds)

        # Fuera de la mision, solo en MODO LIBRE los demas son hackeables.
        if free and prof.get("vuln"):
            time.sleep(0.8)
            host = self.cfg.host_by_ip(ip)
            out = ["[*] Objetivo: " + ip + " (" + (host.name if host else ip) + ")"]
            out += prof.get("exploit", ["[+] ACCESO CONCEDIDO"])
            return ExploitResult(True, method, out, prof.get("user"))

        time.sleep(0.6)
        host = self.cfg.host_by_ip(ip)
        name = host.name if host else ip
        extra = [] if free else ["[i] (En la mision el objetivo es el FILE-SERVER. Proba Modo Libre para hackear otros.)"]
        return ExploitResult(False, method, [
            "[*] Objetivo: " + ip + " (" + name + ")",
            "[!] El servicio en " + ip + " no respondio o no es vulnerable.",
        ] + extra)

    def _exploit_fileserver(self, method, fs, creds) -> ExploitResult:
        if method == "leak":
            time.sleep(0.6)
            out = [
                "[*] Descargando pagina de login...",
                "[*] Analizando el codigo fuente (HTML)...",
                "[+] Credenciales encontradas en un comentario HTML oculto:",
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
        out += ["[+] 1 valid password found", "[+] ACCESO CONCEDIDO"]
        return ExploitResult(True, "hydra", out, creds.brute_user, found)

    # -------------------------- filesystem (por ip) ----------------------
    def is_dir(self, ip: str, path: str) -> bool:
        _, prof = _profile_for(self.cfg, ip)
        return (path.rstrip("/") or "/") in prof["fs"]

    def ls(self, ip: str, path: str) -> LsResult:
        time.sleep(0.35)
        _, prof = _profile_for(self.cfg, ip)
        path = path.rstrip("/") or "/"
        names = prof["fs"].get(path, [])
        entries = [DirEntry(n, is_dir=("." not in n)) for n in names]
        return LsResult(path=path, entries=entries)

    def read(self, ip: str, path: str) -> ReadResult:
        time.sleep(0.45)
        _, prof = _profile_for(self.cfg, ip)
        key = "/" + path.strip().lstrip("/")
        if key in prof.get("files", {}):
            return ReadResult(path=path, content=prof["files"][key])
        return ReadResult(path=path, content=f"[sin contenido para {path}]")

    # nombres para autocompletado de rutas (sin sleep)
    def fs_names(self, ip: str, path: str) -> list[str]:
        _, prof = _profile_for(self.cfg, ip)
        return list(prof["fs"].get(path.rstrip("/") or "/", []))
