#!/usr/bin/env bash
# ============================================================================
#  CyberLab TERMINAL  ·  CHEQUEO PRE-VUELO  (correr antes de la prueba/demo)
# ----------------------------------------------------------------------------
#  En ~5s verifica que el MODO REAL vaya a andar: config, backend, red, el
#  FILE-SERVER, la mision completa (scan->inspect->exploit->ls->read), el ESP
#  y el navegador. Imprime OK/ATENCION por item y un veredicto final.
#
#  Uso:   ./chequeo.sh
#  Sale con codigo 0 si esta TODO listo, 1 si hay algo critico que revisar.
# ============================================================================
cd "$(dirname "${BASH_SOURCE[0]}")"
PY=".venv/bin/python"
[ -x "$PY" ] || { printf '\033[1;31mNo encuentro el venv (%s). Corré EMERGENCIA/restaurar-terminal.sh.\033[0m\n' "$PY"; exit 1; }

"$PY" - "$@" <<'PY'
import os, sys, shutil, subprocess

G="\033[1;32m"; Y="\033[1;33m"; R="\033[1;31m"; C="\033[1;36m"; Z="\033[0m"
def ok(m):   print(f"  {G}[ OK ]{Z} {m}")
def warn(m): print(f"  {Y}[ATEN]{Z} {m}")   # atencion: no critico (degrada)
def bad(m):  print(f"  {R}[FALLA]{Z} {m}")   # critico para la demo real
def head(m): print(f"\n{C}== {m} =={Z}")

critico = 0   # fallas que rompen el modo real
avisos  = 0   # cosas a mirar pero no bloqueantes

try:
    from app.config import load_config
    from app.backend import preflight
    from app.ui.app import _make_backend
except Exception as e:
    print(f"{R}No pude importar la app: {e}{Z}"); sys.exit(1)

# ---------------------------------------------------------------- config
head("Config y backend")
try:
    cfg = load_config("config.toml")
except Exception as e:
    print(f"{R}No pude cargar config.toml: {e}{Z}"); sys.exit(1)

if cfg.modes.engine == "real":
    ok(f"engine = real")
else:
    bad(f"engine = {cfg.modes.engine} (NO es real -> la demo correría simulada)"); critico += 1

b = _make_backend(cfg)
if type(b).__name__ == "RealBackend":
    ok("la app usará RealBackend (sin fallback silencioso)")
else:
    bad(f"backend = {type(b).__name__} (se esperaba RealBackend)"); critico += 1

ip = cfg.fileserver.ip

# ---------------------------------------------------------------- red
head("Red de esta PC")
iface = cfg.network.interface
try:
    out = subprocess.run(["ip","-4","-o","addr","show",iface], capture_output=True, text=True, timeout=4).stdout
    myip = out.split()[3].split("/")[0] if out.strip() else ""
except Exception:
    myip = ""
if myip:
    ok(f"{iface} -> {myip}")
    if not myip.startswith("192.168.10."):
        warn(f"la IP no está en la red del lab (192.168.10.0/24)"); avisos += 1
else:
    bad(f"sin IP en {iface} (¿cable/red del lab?)"); critico += 1

# ---------------------------------------------------------------- preflight
head("Preflight (wordlist / nmap / web / SSH)")
for estado, texto in preflight.run_checks(cfg):
    if estado == "ok": ok(texto)
    else: bad(texto); critico += 1

# ---------------------------------------------------------------- mision real
head("Misión real end-to-end")
try:
    sc = b.scan()
    ips = [h.ip for h in sc.hosts]
    (ok if ip in ips else bad)(f"scan -> {len(ips)} hosts; FILE-SERVER {'presente' if ip in ips else 'AUSENTE'}")
    if ip not in ips: critico += 1

    ins = b.inspect(ip)
    p80 = any(p.port == 80 and p.state == "open" for p in ins.ports)
    (ok if p80 else bad)("inspect -> " + ", ".join(f"{p.port}/{p.state}" for p in ins.ports))
    if not p80: critico += 1

    for m in ("leak","sqli","bruteforce"):
        r = b.exploit(ip, m)
        (ok if r.success else bad)(f"exploit {m}: success={r.success}")
        if not r.success: critico += 1

    rd = b.read(ip, cfg.fileserver.secret_path)
    flag = next((l.strip() for l in rd.content.splitlines() if "FLAG" in l), "")
    (ok if flag else bad)(f"read secreto -> {flag or 'SIN FLAG'}")
    if not flag: critico += 1
except Exception as e:
    bad(f"la misión real tiró error: {e!r}"); critico += 1

# ---------------------------------------------------------------- hardware
head("Hardware / entorno")
if cfg.serial.enabled:
    if os.path.exists(cfg.serial.port):
        ok(f"ESP presente en {cfg.serial.port}")
    else:
        warn(f"ESP no está en {cfg.serial.port} (los LEDs no andarán; la app sí)"); avisos += 1
else:
    ok("serial deshabilitado en config (sin LEDs)")

brs = [x for x in ("google-chrome","google-chrome-stable","chromium","chromium-browser","microsoft-edge") if shutil.which(x)]
(ok if brs else bad)(f"navegador para 'connect': {brs[0] if brs else 'NINGUNO'}")
if not brs: critico += 1

# ---------------------------------------------------------------- veredicto
print()
if critico == 0 and avisos == 0:
    print(f"{G}======================================================={Z}")
    print(f"{G}  LISTO PARA LA PRUEBA  ✓   modo real 100% operativo{Z}")
    print(f"{G}======================================================={Z}")
    sys.exit(0)
elif critico == 0:
    print(f"{Y}======================================================={Z}")
    print(f"{Y}  LISTO, con {avisos} aviso(s) no críticos (ver arriba){Z}")
    print(f"{Y}  El modo real funciona; revisá los avisos si querés.{Z}")
    print(f"{Y}======================================================={Z}")
    sys.exit(0)
else:
    print(f"{R}======================================================={Z}")
    print(f"{R}  ATENCIÓN: {critico} falla(s) crítica(s) + {avisos} aviso(s){Z}")
    print(f"{R}  NO arranques la demo en real hasta resolverlas.{Z}")
    print(f"{R}======================================================={Z}")
    sys.exit(1)
PY