#!/usr/bin/env bash
# ============================================================================
# Cyber Lab - instalacion del FILE-SERVER (el nodo vulnerable) en Linux.
#
# Clona (o actualiza) el repo, instala Docker, construye la imagen del nodo
# (Flask vulnerable + SSH), lo deja ENCENDIDO y crea accesos faciles ON/OFF
# (comando 'node/fileserver.sh' + accesos de escritorio).
#
# Probado en Debian / Ubuntu / Raspberry Pi OS. Corre CON internet la primera
# vez (baja Docker y construye la imagen). Despues el nodo anda offline.
#
# Uso (dentro del repo):   bash scripts/setup-fileserver.sh
# Uso (equipo nuevo):      curl -fsSL https://raw.githubusercontent.com/Monoo12/CyberLab/main/scripts/setup-fileserver.sh | bash
# ============================================================================
set -euo pipefail

REPO_URL="${CYBERLAB_REPO:-https://github.com/Monoo12/CyberLab.git}"
TARGET_DIR="${CYBERLAB_DIR:-$HOME/CyberLab}"

log()  { printf '\n\033[1;32m[cyberlab]\033[0m %s\n' "$*"; }
warn() { printf '\n\033[1;33m[cyberlab]\033[0m %s\n' "$*"; }

SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"

if ! command -v apt-get >/dev/null 2>&1; then
  warn "Este script asume apt (Debian/Ubuntu/Raspberry Pi OS). Instala Docker a mano en otra distro."
fi

# --- Asegurar git y clonar/ubicar el repo ----------------------------------
if ! command -v git >/dev/null 2>&1; then
  log "Instalando git..."
  $SUDO apt-get update && $SUDO apt-get install -y git
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/../node/docker-compose.yml" ]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  log "Repo detectado en $REPO_ROOT. Actualizando..."
  git -C "$REPO_ROOT" pull --ff-only || warn "No pude actualizar; sigo con lo que hay."
else
  if [ -d "$TARGET_DIR/.git" ]; then
    log "Repo ya clonado en $TARGET_DIR. Actualizando..."
    git -C "$TARGET_DIR" pull --ff-only || true
  else
    log "Clonando el repo en $TARGET_DIR..."
    git clone "$REPO_URL" "$TARGET_DIR"
  fi
  REPO_ROOT="$TARGET_DIR"
fi
cd "$REPO_ROOT"

# --- Docker -----------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "Instalando Docker (script oficial get.docker.com)..."
  curl -fsSL https://get.docker.com | $SUDO sh
  $SUDO usermod -aG docker "$USER" || true
  warn "Te agregue al grupo 'docker'. En este setup uso sudo; tras reloguear ya no hara falta."
fi
$SUDO systemctl enable --now docker 2>/dev/null || true

# --- Construir y levantar el nodo ------------------------------------------
log "Construyendo y levantando el FILE-SERVER..."
if ! $SUDO docker compose -f "$REPO_ROOT/node/docker-compose.yml" up -d --build; then
  warn "Fallo al levantar. Causa comun: el puerto 22 (SSH) ya lo usa el sshd del propio equipo."
  echo "   Opciones:"
  echo "   - Deshabilitar el SSH del host:   sudo systemctl disable --now ssh"
  echo "   - O cambiar el mapeo 22:22 en node/docker-compose.yml y [fileserver].ssh_port en config.toml."
  exit 1
fi

chmod +x "$REPO_ROOT/node/fileserver.sh" "$REPO_ROOT/node/reset.sh" 2>/dev/null || true

# --- Accesos de escritorio ON/OFF (best-effort) ----------------------------
DESKTOP=""
for d in "$HOME/Desktop" "$HOME/Escritorio"; do [ -d "$d" ] && DESKTOP="$d"; done
if [ -n "$DESKTOP" ]; then
  log "Creando accesos de escritorio ON/OFF en $DESKTOP..."
  make_launcher() {  # nombre, accion, comentario
    local file="$DESKTOP/CyberLab FileServer $1.desktop"
    cat > "$file" <<DESK
[Desktop Entry]
Type=Application
Name=CyberLab FileServer $1
Comment=$3
Exec=bash -c 'cd "$REPO_ROOT/node"; ./fileserver.sh $2; echo; read -p "Enter para cerrar..."'
Terminal=true
Icon=network-server
DESK
    chmod +x "$file" || true
    gio set "$file" metadata::trusted true 2>/dev/null || true
  }
  make_launcher "ON"  "on"  "Encender el FILE-SERVER del laboratorio"
  make_launcher "OFF" "off" "Apagar el FILE-SERVER del laboratorio"
fi

log "LISTO. El FILE-SERVER ya esta ENCENDIDO y arranca solo al bootear (restart unless-stopped)."
echo "   Control por comando (desde $REPO_ROOT):"
echo "     node/fileserver.sh on       # encender"
echo "     node/fileserver.sh off      # apagar"
echo "     node/fileserver.sh reset    # reiniciar a estado limpio (entre visitantes)"
echo "     node/fileserver.sh status   # ver estado"
echo "     node/fileserver.sh logs     # ver logs en vivo"
[ -n "$DESKTOP" ] && echo "   O doble clic en los accesos 'CyberLab FileServer ON/OFF' del escritorio."
echo
echo "   IMPORTANTE: las credenciales/IP del nodo deben coincidir con el config.toml de la"
echo "   terminal (LAB_PASS = [creds].leak_pass, usuario ctf). Ver docs/DESPLIEGUE-REAL.md."
