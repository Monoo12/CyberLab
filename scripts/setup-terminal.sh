#!/usr/bin/env bash
# ============================================================================
# Cyber Lab - instalacion del dispositivo TERMINAL (la PC del visitante) en Linux.
#
# Clona (o actualiza) el repo del juego, instala Python + dependencias de la app,
# nmap, un navegador para el paso 'connect', da acceso al USB serial de los LEDs
# y deja un lanzador listo.
#
# Probado en Debian / Ubuntu / Raspberry Pi OS (apt). Corre CON internet la
# primera vez (clona el repo y baja dependencias). Despues la app anda offline.
#
# Uso (dentro del repo):   bash scripts/setup-terminal.sh
# Uso (equipo nuevo):      curl -fsSL https://raw.githubusercontent.com/Monoo12/CyberLab/main/scripts/setup-terminal.sh | bash
# ============================================================================
set -euo pipefail

REPO_URL="${CYBERLAB_REPO:-https://github.com/Monoo12/CyberLab.git}"
TARGET_DIR="${CYBERLAB_DIR:-$HOME/CyberLab}"

log()  { printf '\n\033[1;32m[cyberlab]\033[0m %s\n' "$*"; }
warn() { printf '\n\033[1;33m[cyberlab]\033[0m %s\n' "$*"; }

SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"

if ! command -v apt-get >/dev/null 2>&1; then
  warn "Este script asume apt (Debian/Ubuntu/Raspberry Pi OS)."
  warn "En otra distro instala a mano: git python3 python3-venv python3-tk python3-pip nmap chromium."
  exit 1
fi

# --- Asegurar git antes de clonar ------------------------------------------
if ! command -v git >/dev/null 2>&1; then
  log "Instalando git..."
  $SUDO apt-get update
  $SUDO apt-get install -y git
fi

# --- Ubicar o clonar el repo -----------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/../app/main.py" ]; then
  # El script ya esta dentro de un clon del repo: usarlo y actualizar.
  REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  log "Repo detectado en $REPO_ROOT. Actualizando..."
  git -C "$REPO_ROOT" pull --ff-only || warn "No pude actualizar; sigo con lo que hay."
else
  # Corrida suelta (o via curl | bash): clonar/actualizar en TARGET_DIR.
  if [ -d "$TARGET_DIR/.git" ]; then
    log "Repo ya clonado en $TARGET_DIR. Actualizando..."
    git -C "$TARGET_DIR" pull --ff-only || true
  else
    log "Clonando el juego en $TARGET_DIR..."
    git clone "$REPO_URL" "$TARGET_DIR"
  fi
  REPO_ROOT="$TARGET_DIR"
fi
cd "$REPO_ROOT"

# --- Paquetes del sistema ---------------------------------------------------
log "Instalando paquetes del sistema..."
$SUDO apt-get update
$SUDO apt-get install -y \
  python3 python3-venv python3-pip python3-tk nmap \
  build-essential python3-dev libffi-dev libssl-dev

log "Instalando navegador (para el paso 'connect')..."
$SUDO apt-get install -y chromium \
  || $SUDO apt-get install -y chromium-browser \
  || warn "No pude instalar chromium; instala Chrome/Chromium a mano para 'connect'."

log "Instalando opcionales (modo avanzado): arp-scan, hydra, fuente monoespaciada..."
$SUDO apt-get install -y arp-scan hydra fonts-firacode || warn "Opcionales no instalados (no es critico)."

# --- App Python -------------------------------------------------------------
log "Creando entorno virtual e instalando dependencias de la app..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f config.toml ]; then
  cp config.example.toml config.toml
  log "config.toml creado desde la plantilla (ajusta IPs/credenciales para modo real)."
fi

# Acceso al puerto serie del microcontrolador de los LEDs (/dev/ttyUSB*).
if getent group dialout >/dev/null 2>&1; then
  $SUDO usermod -aG dialout "$USER" || true
  warn "Te agregue al grupo 'dialout' (USB serial de los LEDs). Cerra sesion y volve a entrar para que tome efecto."
fi

# Lanzador comodo.
cat > run-terminal.sh <<'LAUNCH'
#!/usr/bin/env bash
# Arranca la app del visitante. Normalmente alcanza con:  ./run-terminal.sh
# En el MENU de arranque elegis Motor (Simulado/Real), Dificultad, Modo libre, Panel visual.
# Los flags son OPCIONALES, sobre todo para kiosco (que saltea el menu):
#   ./run-terminal.sh                 -> abre el menu y elegis todo ahi
#   ./run-terminal.sh --autostart     -> kiosco: sin menu, usa lo de config.toml
#   ./run-terminal.sh --autostart --engine real --difficulty medio   -> kiosco preconfigurado
cd "$(dirname "${BASH_SOURCE[0]}")"
exec .venv/bin/python -m app.main "$@"
LAUNCH
chmod +x run-terminal.sh

log "LISTO. La terminal quedo instalada en: $REPO_ROOT"
echo "   cd $REPO_ROOT"
echo "   Arrancar:          ./run-terminal.sh      (en el MENU elegis Simulado/Real, dificultad, etc.)"
echo "   Kiosco (sin menu): ./run-terminal.sh --autostart"
echo
echo "   Si vas a usar los LEDs: reinicia la sesion para el permiso de 'dialout'."
echo "   Para modo real, revisa docs/RED-ROUTER.md y docs/DESPLIEGUE-REAL.md."
