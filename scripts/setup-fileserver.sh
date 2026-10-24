#!/usr/bin/env bash
# ============================================================================
# NetLab - instalacion del FILE-SERVER (el nodo vulnerable) en Linux.
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

REPO_URL="${NETLAB_REPO:-https://github.com/Monoo12/CyberLab.git}"
TARGET_DIR="${NETLAB_DIR:-$HOME/NetLab}"

log()  { printf '\n\033[1;32m[netlab]\033[0m %s\n' "$*"; }
warn() { printf '\n\033[1;33m[netlab]\033[0m %s\n' "$*"; }

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

COMPOSE="$REPO_ROOT/node/docker-compose.yml"

# --- Chequeo previo de puertos (el nodo publica 80 web y 2222 SSH) ----------
# Si el host ya ocupa esos puertos, el contenedor no bindea y el modo real falla.
# El SSH va al 2222 a proposito, para NO chocar con el sshd propio del equipo (22).
check_port() {  # puerto, para_que
  if command -v ss >/dev/null 2>&1 && $SUDO ss -ltn 2>/dev/null | grep -q ":$1 "; then
    warn "El puerto $1 ($2) ya esta ocupado en este equipo -> el nodo no podra usarlo."
    echo "   Liberalo, o cambia el mapeo en node/docker-compose.yml (y config.toml si toca el SSH)."
  fi
}
check_port 80   "web del FILE-SERVER"
check_port 2222 "SSH del nodo"
if command -v ufw >/dev/null 2>&1 && $SUDO ufw status 2>/dev/null | grep -qi "Status: active"; then
  warn "ufw esta activo: habilita 80 y 2222 para que la PC de la muestra alcance el nodo:"
  echo "   sudo ufw allow 80/tcp && sudo ufw allow 2222/tcp"
fi

# --- Construir y levantar el nodo ------------------------------------------
log "Construyendo y levantando el FILE-SERVER..."
if ! $SUDO docker compose -f "$COMPOSE" up -d --build; then
  warn "Fallo al construir/levantar el contenedor. Causas comunes:"
  echo "   - Puerto 80 (web) o 2222 (SSH) ocupado en el host (ver avisos de arriba)."
  echo "   - Sin internet en la 1ra vez (hay que bajar la imagen base y los paquetes pip)."
  echo "   - docker sin permisos: reinicia sesion tras el 'usermod -aG docker', o corre con sudo."
  exit 1
fi

chmod +x "$REPO_ROOT/node/fileserver.sh" "$REPO_ROOT/node/reset.sh" 2>/dev/null || true

# --- Sanity post-arranque: que el nodo REALMENTE responda -------------------
# Que falle aca (en el armado) y no en vivo frente a los visitantes.
log "Verificando que el nodo responda (contenedor + web + SSH + usuario ctf)..."
sleep 4   # darle un momento a Flask/sshd/seed_db
NODE_OK=1
if [ "$($SUDO docker inspect -f '{{.State.Running}}' netlab-fileserver 2>/dev/null)" = "true" ]; then
  echo "   [OK] contenedor netlab-fileserver corriendo"
else
  warn "   [!] el contenedor NO quedo corriendo -> mira:  node/fileserver.sh logs"; NODE_OK=0
fi
if command -v curl >/dev/null 2>&1; then
  if curl -fsS -o /dev/null --max-time 5 http://localhost:80/; then
    echo "   [OK] web responde en http://localhost:80"
  else
    warn "   [!] la web NO responde en :80 -> revisa logs y que el 80 este libre"; NODE_OK=0
  fi
fi
if $SUDO docker exec netlab-fileserver id ctf >/dev/null 2>&1; then
  echo "   [OK] usuario ctf existe en el contenedor (lo usan ls/read por SSH)"
else
  warn "   [!] falta el usuario ctf -> ls/read por SSH fallaran"; NODE_OK=0
fi
if command -v ss >/dev/null 2>&1 && $SUDO ss -ltn 2>/dev/null | grep -q ":2222 "; then
  echo "   [OK] SSH del nodo publicado en host:2222"
else
  warn "   [!] no veo el 2222 escuchando -> revisa el mapeo 2222:22 del compose"; NODE_OK=0
fi
if [ "$NODE_OK" = 1 ]; then
  log "Nodo verificado OK (web + SSH + ctf). Recorda: en config.toml de la terminal, ssh_port = 2222."
else
  warn "Nodo con avisos: resolvelos ANTES del evento (node/fileserver.sh logs)."
fi

# --- Accesos de escritorio ON/OFF (best-effort) ----------------------------
DESKTOP=""
for d in "$HOME/Desktop" "$HOME/Escritorio"; do [ -d "$d" ] && DESKTOP="$d"; done
if [ -n "$DESKTOP" ]; then
  log "Creando accesos de escritorio ON/OFF en $DESKTOP..."
  make_launcher() {  # nombre, accion, comentario
    local file="$DESKTOP/NetLab FileServer $1.desktop"
    cat > "$file" <<DESK
[Desktop Entry]
Type=Application
Name=NetLab FileServer $1
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
[ -n "$DESKTOP" ] && echo "   O doble clic en los accesos 'NetLab FileServer ON/OFF' del escritorio."
echo
echo "   IMPORTANTE: las credenciales/IP del nodo deben coincidir con el config.toml de la"
echo "   terminal (LAB_PASS = [creds].leak_pass, usuario ctf). Ver docs/DESPLIEGUE-REAL.md."
