#!/usr/bin/env bash
# ============================================================================
#  CyberLab TERMINAL (estacion del visitante)  ·  RESTAURACION DE EMERGENCIA
# ----------------------------------------------------------------------------
#  Deja ESTA PC (la TERMINAL, no el file-server) EXACTAMENTE como estaba:
#  dependencias del sistema, venv de Python, config real en modo REAL, serie
#  del ESP (LEDs) y kiosco en pantalla completa al iniciar sesión (SIN autologin).
#
#  Para cuando alguien borra/formatea la PC. Pasos:
#     1) Recuperar el repo:   git clone https://github.com/Monoo12/CyberLab ~/CyberLab
#        (o copiarlo de un backup)  -> OJO: debe incluir esta carpeta EMERGENCIA/
#     2) Loguearte como el usuario operador de la terminal (MUESTRANOBORRAR).
#     3) Ejecutar:   bash ~/CyberLab/EMERGENCIA/restaurar-terminal.sh
#        Te va a pedir la contrasena de ese usuario (sudo) para los pasos de sistema.
#     4) REINICIAR: la terminal arranca sola en el menu de setup, pantalla completa.
#
#  Es IDEMPOTENTE: podes correrlo las veces que quieras; salta lo ya hecho.
#  NO instala el nodo vulnerable (node/) -> eso es del FILE-SERVER (restaurar.sh).
# ============================================================================
set -euo pipefail

# --- Lo que define a esta PC (ajustar solo si cambia el despliegue) ---------
EXPECT_USER="MUESTRANOBORRAR"      # usuario operador de la terminal
IFACE="enp2s0"                     # placa de red de esta PC
SERIAL_PORT="/dev/ttyUSB0"         # ESP (tira LED) por USB

# --- Rutas (derivadas, no tocar) -------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"   # EMERGENCIA/ vive dentro del repo
VENV="$REPO_DIR/.venv"
PY="$VENV/bin/python"
RUNNER="$REPO_DIR/run-terminal.sh"
AUTOSTART="$HOME/.config/autostart/cyberlab.desktop"
UID_NUM="$(id -u)"

# --- Colores / helpers -----------------------------------------------------
c_g(){ printf '\033[1;32m%s\033[0m\n' "$*"; }
c_y(){ printf '\033[1;33m%s\033[0m\n' "$*"; }
c_r(){ printf '\033[1;31m%s\033[0m\n' "$*"; }
step(){ printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die(){ c_r "ERROR: $*"; exit 1; }

# sudo: pedimos password una vez; si no hay sudo, avisamos.
SUDO=""
need_sudo() {
  [ -n "$SUDO" ] && return 0
  if [ "$UID_NUM" -eq 0 ]; then SUDO=""; return 0; fi
  command -v sudo >/dev/null 2>&1 || die "Hace falta sudo (o correr como root) para los pasos de sistema."
  c_y "Algunos pasos necesitan permisos de administrador (sudo)."
  sudo -v || die "No se pudo obtener sudo."
  SUDO="sudo"
}

# ============================================================================
step "0) Chequeos previos"
[ "$UID_NUM" -eq 0 ] && die "No corras esto como root: tiene que ser el usuario operador ($EXPECT_USER)."
if [ "$(id -un)" != "$EXPECT_USER" ]; then
  c_y "Aviso: el usuario actual es '$(id -un)', no '$EXPECT_USER'. Sigo igual, pero revisá que sea el correcto."
fi
. /etc/os-release 2>/dev/null || true
c_g "Usuario: $(id -un) (uid $UID_NUM)   SO: ${PRETTY_NAME:-?}   repo: $REPO_DIR"
[ -f "$REPO_DIR/app/main.py" ] || die "No encuentro el repo CyberLab en $REPO_DIR (falta app/main.py)."

# ============================================================================
step "1) Paquetes de sistema (apt)"
# python3-tk: customtkinter se apoya en tkinter (sin esto la GUI no abre).
# nmap: scan/inspect reales.  arp-scan/hydra: modos avanzados del exploit.
PKGS=(python3 python3-venv python3-tk python3-dev nmap arp-scan hydra git curl ca-certificates)
missing=()
for p in "${PKGS[@]}"; do
  dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p")
done
if [ "${#missing[@]}" -eq 0 ]; then
  c_g "Todos los paquetes ya están instalados."
else
  c_y "Faltan: ${missing[*]}"
  need_sudo
  $SUDO apt-get update
  $SUDO apt-get install -y "${missing[@]}"
  c_g "Paquetes instalados."
fi

# ============================================================================
step "2) Navegador para el paso 'connect'"
# La app busca (en este orden): google-chrome, google-chrome-stable, chromium,
# chromium-browser, microsoft-edge. Con cualquiera alcanza.
if command -v google-chrome >/dev/null 2>&1 || command -v google-chrome-stable >/dev/null 2>&1 \
   || command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1 \
   || command -v microsoft-edge >/dev/null 2>&1; then
  c_g "Ya hay un navegador compatible instalado."
else
  need_sudo
  c_y "No hay navegador; instalo google-chrome (con fallback a chromium)."
  tmp_deb="$(mktemp --suffix=.deb)"
  if curl -fL "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb" -o "$tmp_deb"; then
    $SUDO apt-get install -y "$tmp_deb" || { c_y "Chrome falló; voy a chromium."; $SUDO apt-get install -y chromium || $SUDO snap install chromium; }
  else
    c_y "No pude bajar Chrome; instalo chromium."
    $SUDO apt-get install -y chromium || $SUDO snap install chromium
  fi
  rm -f "$tmp_deb"
  c_g "Navegador instalado."
fi

# ============================================================================
step "3) Entorno virtual de Python (.venv) + dependencias"
# customtkinter queda fijado <6 por requirements.txt (la 6.x da ventana negra).
if [ ! -x "$PY" ]; then
  python3 -m venv "$VENV"
  c_g "venv creado en $VENV"
else
  c_g "venv ya existe."
fi
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -r "$REPO_DIR/requirements.txt"
ctk_ver="$("$PY" -c 'import customtkinter as c; print(c.__version__)' 2>/dev/null || echo '?')"
case "$ctk_ver" in
  5.*) c_g "customtkinter $ctk_ver OK (serie 5.x)";;
  *)   c_y "customtkinter quedó en '$ctk_ver' (se esperaba 5.x). Revisá requirements.txt.";;
esac
"$PY" -c 'import tkinter' 2>/dev/null && c_g "tkinter OK en el venv." || c_y "tkinter NO disponible: instalá python3-tk."

# ============================================================================
step "4) config.toml (modo REAL — no se versiona)"
# Prioridad: 1) el que ya exista (no lo piso)  2) snapshot local  3) lo escribo yo.
if [ -f "$REPO_DIR/config.toml" ]; then
  c_g "config.toml ya existe; lo dejo como está (no piso el actual)."
elif [ -f "$SCRIPT_DIR/config.toml.snapshot" ]; then
  cp "$SCRIPT_DIR/config.toml.snapshot" "$REPO_DIR/config.toml"
  c_g "config.toml restaurado desde el snapshot local."
else
  cat > "$REPO_DIR/config.toml" <<'TOML'
# Cyber Lab - config real de la TERMINAL (estacion del visitante). No se versiona.
[modes]
visual     = true
engine     = "real"        # contra el FILE-SERVER real
mode       = "experto"
difficulty = "facil"
lesson     = "rotar"
autostart  = false         # el kiosco abre siempre en el menu de setup
free_mode  = false
fullscreen = true          # arranca en pantalla completa (kiosco)

[timing]
mission_seconds   = 300
hint_idle_seconds = 40
typewriter_cps    = 160

[network]
cidr      = "192.168.10.0/24"
interface = "enp2s0"       # placa real de esta PC
scan_tool = "nmap"

[fileserver]
ip          = "192.168.10.20"
http_port   = 80
ssh_port    = 2222
ssh_user    = "ctf"
url         = "http://192.168.10.20:80"
secret_path = "/restricted/secret.txt"
base_path   = "/srv/lab"

[creds]
leak_user  = "admin"
leak_pass  = "S3cr3t-2024!"
brute_user = "admin"
wordlist   = ["123456", "password", "admin", "qwerty", "S3cr3t-2024!", "letmein"]

[serial]
enabled = true
port    = "/dev/ttyUSB0"   # ESP de la tira LED (Linux)
baud    = 115200

[[hosts]]
ip   = "192.168.10.1"
name = "router"
role = "router"

[[hosts]]
ip   = "192.168.10.10"
name = "TERMINAL-VISITANTE"
role = "terminal"

[[hosts]]
ip    = "192.168.10.20"
name  = "FILE-SERVER"
role  = "fileserver"
ports = [22, 80, 5000]

[[hosts]]
ip   = "192.168.10.30"
name = "WORKSTATION-01"
role = "workstation"

[[hosts]]
ip   = "192.168.10.40"
name = "SECURITY-SERVER"
role = "security"
TOML
  c_g "config.toml escrito (engine=real, interface=enp2s0, serie=/dev/ttyUSB0, fullscreen)."
fi

# ============================================================================
step "5) Lanzador run-terminal.sh"
if [ ! -f "$RUNNER" ]; then
  cat > "$RUNNER" <<'SH'
#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")"
exec .venv/bin/python -m app.main "$@"
SH
  c_g "run-terminal.sh creado."
else
  c_g "run-terminal.sh ya existe."
fi
chmod +x "$RUNNER"

# ============================================================================
step "6) Acceso al puerto serie del ESP (grupo dialout)"
if id -nG "$(id -un)" | tr ' ' '\n' | grep -qx dialout; then
  c_g "El usuario ya está en el grupo dialout."
else
  need_sudo
  $SUDO usermod -aG dialout "$(id -un)"
  c_y "Agregado a dialout -> toma efecto al CERRAR SESION y volver a entrar (o reiniciar)."
fi

# ============================================================================
step "7) Autostart del kiosco (XDG)"
mkdir -p "$(dirname "$AUTOSTART")"
cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=Cyber Lab (kiosco)
Comment=Arranca la terminal del visitante en el menu de setup
Exec=$RUNNER --menu --fullscreen
Path=$REPO_DIR
Terminal=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
EOF
c_g "Autostart escrito en $AUTOSTART"

# ============================================================================
step "8) SIN autologin (sddm): la PC es compartida, se entra con contraseña"
# Otras personas usan esta PC: NUNCA dejar autologin. Se quita cualquier
# autologin previo (drop-in viejo de este script o User= en la config de sddm).
# El kiosco igual arranca solo, pero recién DESPUÉS de loguearse con contraseña.
OLD_DROPIN="/etc/sddm.conf.d/95-cyberlab-autologin.conf"
if [ -f "$OLD_DROPIN" ] || grep -qs '^User=' /etc/sddm.conf /etc/sddm.conf.d/*.conf; then
  need_sudo
  $SUDO rm -f "$OLD_DROPIN"
  for f in /etc/sddm.conf /etc/sddm.conf.d/*.conf; do
    [ -f "$f" ] && grep -q '^User=' "$f" && $SUDO sed -i '/^User=/d' "$f"
  done
  c_g "Autologin quitado: al bootear pide usuario y contraseña."
else
  c_g "Sin autologin (correcto): al bootear pide usuario y contraseña."
fi

# ============================================================================
step "9) Verificación final"
ok=1
"$PY" -c 'import customtkinter, paramiko, requests, serial, PIL; import tkinter' 2>/dev/null \
  && c_g "Dependencias Python OK (customtkinter/paramiko/requests/pyserial/Pillow/tkinter)." \
  || { c_r "Faltan dependencias Python."; ok=0; }
command -v nmap >/dev/null && c_g "nmap OK (scan/inspect)." || { c_r "nmap falta."; ok=0; }
[ -f "$REPO_DIR/config.toml" ] && c_g "config.toml presente." || { c_r "config.toml falta."; ok=0; }
ip_now="$(ip -4 -o addr show "$IFACE" 2>/dev/null | awk '{print $4}' | cut -d/ -f1)"
[ -n "$ip_now" ] && c_g "Red: $IFACE -> ${ip_now}" || c_y "No hay IP en $IFACE (revisá la red del lab)."
if command -v curl >/dev/null && curl -s -o /dev/null -w '%{http_code}' --max-time 4 "http://192.168.10.20:80/" 2>/dev/null | grep -q 200; then
  c_g "FILE-SERVER responde en http://192.168.10.20:80 (modo real listo)."
else
  c_y "No llego al FILE-SERVER (192.168.10.20). Si el nodo no está prendido, la app cae a simulado."
fi
[ -e "$SERIAL_PORT" ] && c_g "ESP presente en $SERIAL_PORT." || c_y "No veo el ESP en $SERIAL_PORT (enchufalo para los LEDs; la app anda igual sin él)."

echo
if [ "$ok" -eq 1 ]; then
  c_g "========================================================================"
  c_g " TERMINAL RESTAURADA  ✓"
  c_g "   Probar a mano:   $RUNNER            (menu)"
  c_g "                    $RUNNER --menu --fullscreen   (como el kiosco)"
  c_g "========================================================================"
  echo
  c_y "Para que quede 100% como estaba, FALTA:"
  echo "   · REINICIAR y loguearse como el operador (CON contraseña) -> el autostart abre el kiosco."
  echo "     (el grupo dialout recién aplica tras reiniciar)."
  echo
  c_y "Pendientes que NO dependen del software de esta PC:"
  echo "   · Red del lab 192.168.10.0/24: esta PC debería tomar 192.168.10.10 (terminal)."
  echo "   · El FILE-SERVER (192.168.10.20) tiene que estar encendido para el modo real."
  echo "   · ESP de la tira LED enchufado por USB (aparece como $SERIAL_PORT)."
else
  c_r "La verificación encontró problemas (ver arriba). Revisalos y volvé a correr el script."
  exit 1
fi
