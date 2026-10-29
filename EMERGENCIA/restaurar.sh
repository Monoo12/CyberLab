#!/usr/bin/env bash
# ============================================================================
#  CyberLab FILE-SERVER  ·  RESTAURACION DE EMERGENCIA
# ----------------------------------------------------------------------------
#  Deja este equipo EXACTAMENTE como estaba: Docker rootless + nodo vulnerable
#  dockerizado, arranque al boot, cartel de estado en el login y config real.
#
#  Para cuando alguien borra/formatea la PC. Pasos:
#     1) Recuperar el repo:   git clone https://github.com/Monoo12/CyberLab ~/CyberLab
#        (o copiarlo de un backup)  -> OJO: debe incluir esta carpeta EMERGENCIA/
#     2) Loguearte como el usuario del file-server (MUESTRANOBORRAR_SERVER).
#     3) Ejecutar:   bash ~/CyberLab/EMERGENCIA/restaurar.sh
#        Te va a pedir la contrasena de ese usuario (sudo) para los pasos de sistema.
#
#  Es IDEMPOTENTE: podes correrlo las veces que quieras; salta lo ya hecho.
# ============================================================================
set -euo pipefail

# --- Versiones fijadas (lo que hay instalado hoy) --------------------------
DOCKER_VERSION="29.9.2"        # docker static + rootless-extras
COMPOSE_VERSION="v2.40.3"      # plugin compose v2
ARCH_STATIC="x86_64"           # arquitectura de los tarballs de docker
EXPECT_USER="MUESTRANOBORRAR_SERVER"
IFACE="enp2s0"                 # interfaz de red (la que lee el cartel)
CONTAINER="cyberlab-fileserver"

# --- Rutas (derivadas, no tocar) -------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"   # EMERGENCIA/ vive dentro del repo
BIN_DIR="$HOME/bin"
CLI_PLUGINS="$HOME/.docker/cli-plugins"
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
[ "$UID_NUM" -eq 0 ] && die "No corras esto como root: tiene que ser el usuario del file-server ($EXPECT_USER)."
if [ "$(id -un)" != "$EXPECT_USER" ]; then
  c_y "Aviso: el usuario actual es '$(id -un)', no '$EXPECT_USER'. Sigo igual, pero revisá que sea el correcto."
fi
. /etc/os-release 2>/dev/null || true
c_g "Usuario: $(id -un) (uid $UID_NUM)   SO: ${PRETTY_NAME:-?}   repo: $REPO_DIR"
[ -f "$REPO_DIR/node/docker-compose.yml" ] || die "No encuentro el repo CyberLab en $REPO_DIR (falta node/docker-compose.yml)."

# ============================================================================
step "1) Paquetes de sistema (apt)"
PKGS=(uidmap slirp4netns dbus-user-session fuse-overlayfs python3-paramiko curl ca-certificates)
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
step "2) Kernel: nf_tables, user namespaces y subuid/subgid"
# nf_tables (lo necesita el stack de red); lo cargamos y persistimos al boot.
if ! lsmod | grep -q '^nf_tables'; then
  need_sudo
  $SUDO modprobe nf_tables || c_y "No se pudo cargar nf_tables (quizá ya está compilado en el kernel)."
fi
if [ ! -f /etc/modules-load.d/cyberlab-nftables.conf ]; then
  need_sudo
  echo nf_tables | $SUDO tee /etc/modules-load.d/cyberlab-nftables.conf >/dev/null
  c_g "nf_tables se cargará al boot."
fi
# user namespaces sin privilegios (rootless los usa)
if [ "$(cat /proc/sys/kernel/unprivileged_userns_clone 2>/dev/null || echo 1)" != "1" ]; then
  need_sudo
  echo 'kernel.unprivileged_userns_clone=1' | $SUDO tee /etc/sysctl.d/99-cyberlab-userns.conf >/dev/null
  $SUDO sysctl -p /etc/sysctl.d/99-cyberlab-userns.conf
fi
# rangos subuid/subgid para el mapeo rootless
if ! grep -q "^$(id -un):" /etc/subuid 2>/dev/null; then
  need_sudo
  $SUDO usermod --add-subuids 362144-427679 --add-subgids 362144-427679 "$(id -un)" \
    || { echo "$(id -un):362144:65536" | $SUDO tee -a /etc/subuid >/dev/null; \
         echo "$(id -un):362144:65536" | $SUDO tee -a /etc/subgid >/dev/null; }
  c_g "subuid/subgid configurados."
else
  c_g "subuid/subgid ya presentes."
fi

# ============================================================================
step "3) Docker rootless (binarios estáticos en ~/bin)"
mkdir -p "$BIN_DIR"
install_docker=1
if [ -x "$BIN_DIR/dockerd" ] && "$BIN_DIR/dockerd" --version 2>/dev/null | grep -q "$DOCKER_VERSION"; then
  c_g "Docker $DOCKER_VERSION ya está en ~/bin."
  install_docker=0
fi
if [ "$install_docker" -eq 1 ]; then
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  base="https://download.docker.com/linux/static/stable/$ARCH_STATIC"
  c_y "Descargando docker-$DOCKER_VERSION.tgz ..."
  curl -fL "$base/docker-$DOCKER_VERSION.tgz" -o "$tmp/docker.tgz"
  c_y "Descargando docker-rootless-extras-$DOCKER_VERSION.tgz ..."
  curl -fL "$base/docker-rootless-extras-$DOCKER_VERSION.tgz" -o "$tmp/rootless.tgz"
  tar -xzf "$tmp/docker.tgz"            -C "$tmp"   # -> $tmp/docker/*
  tar -xzf "$tmp/rootless.tgz"          -C "$tmp"   # -> $tmp/docker-rootless-extras/*
  install -m 0755 "$tmp"/docker/* "$BIN_DIR"/
  install -m 0755 "$tmp"/docker-rootless-extras/* "$BIN_DIR"/
  c_g "Docker $DOCKER_VERSION instalado en ~/bin."
fi

# ============================================================================
step "4) Plugin docker compose ($COMPOSE_VERSION)"
mkdir -p "$CLI_PLUGINS"
if [ -x "$CLI_PLUGINS/docker-compose" ] && "$CLI_PLUGINS/docker-compose" version 2>/dev/null | grep -q "${COMPOSE_VERSION#v}"; then
  c_g "compose $COMPOSE_VERSION ya instalado."
else
  curl -fL "https://github.com/docker/compose/releases/download/$COMPOSE_VERSION/docker-compose-linux-x86_64" \
       -o "$CLI_PLUGINS/docker-compose"
  chmod +x "$CLI_PLUGINS/docker-compose"
  c_g "compose $COMPOSE_VERSION instalado."
fi

# ============================================================================
step "5) Permiso para bindear el puerto 80 (setcap en rootlesskit)"
if getcap "$BIN_DIR/rootlesskit" 2>/dev/null | grep -q cap_net_bind_service; then
  c_g "rootlesskit ya tiene cap_net_bind_service."
else
  need_sudo
  $SUDO setcap cap_net_bind_service=ep "$BIN_DIR/rootlesskit"
  c_g "cap_net_bind_service aplicado a rootlesskit."
fi

# ============================================================================
step "6) Bloque CyberLab en ~/.bashrc (env + cartel de estado)"
if grep -q "CyberLab rootless docker env" "$HOME/.bashrc" 2>/dev/null; then
  c_g "El bloque ya está en ~/.bashrc (no lo duplico)."
else
  { echo ""; cat "$SCRIPT_DIR/bashrc-cyberlab.snippet"; } >> "$HOME/.bashrc"
  c_g "Bloque CyberLab agregado a ~/.bashrc."
fi
# Lo cargamos en ESTA sesión para los pasos que siguen.
export PATH="$BIN_DIR:$PATH"
export XDG_RUNTIME_DIR="/run/user/$UID_NUM"
export DOCKER_HOST="unix:///run/user/$UID_NUM/docker.sock"
export CYBERLAB_NOSUDO=1

# ============================================================================
step "7) Servicio systemd --user + arranque al boot (linger)"
# linger: que el servicio de usuario levante sin login.
if [ "$(loginctl show-user "$(id -un)" -p Linger --value 2>/dev/null)" != "yes" ]; then
  if ! loginctl enable-linger "$(id -un)" 2>/dev/null; then
    need_sudo; $SUDO loginctl enable-linger "$(id -un)"
  fi
  c_g "linger habilitado."
else
  c_g "linger ya estaba habilitado."
fi
# Instala/habilita el servicio rootless de docker (idempotente).
if [ ! -f "$HOME/.config/systemd/user/docker.service" ]; then
  "$BIN_DIR/dockerd-rootless-setuptool.sh" install --skip-iptables || \
    "$BIN_DIR/dockerd-rootless-setuptool.sh" install || \
    c_y "setuptool reportó un problema; revisá 'systemctl --user status docker'."
fi
systemctl --user enable docker.service 2>/dev/null || true
systemctl --user start  docker.service 2>/dev/null || true
# Espera a que el socket responda.
for i in $(seq 1 15); do
  docker info >/dev/null 2>&1 && break
  sleep 1
done
docker info >/dev/null 2>&1 && c_g "Docker rootless activo." || c_y "Docker aún no responde; seguí con cuidado."

# ============================================================================
step "8) Restaurar config.toml (no se versiona)"
if [ -f "$REPO_DIR/config.toml" ]; then
  c_g "config.toml ya existe; lo dejo como está (no piso el actual)."
elif [ -f "$SCRIPT_DIR/config.toml.snapshot" ]; then
  # Snapshot local opcional (no se versiona: tiene credenciales literales).
  cp "$SCRIPT_DIR/config.toml.snapshot" "$REPO_DIR/config.toml"
  c_g "config.toml restaurado desde el snapshot local (apunta a 192.168.10.20)."
else
  # Sin snapshot -> usamos el example versionado (hoy es idéntico salvo comentarios).
  cp "$REPO_DIR/config.example.toml" "$REPO_DIR/config.toml"
  c_g "config.toml restaurado desde config.example.toml (ya apunta a 192.168.10.20)."
fi

# ============================================================================
step "9) Construir y encender el FILE-SERVER"
( cd "$REPO_DIR/node" && ./fileserver.sh on )

# ============================================================================
step "10) Verificación final"
sleep 3
ip_now="$(ip -4 -o addr show "$IFACE" 2>/dev/null | awk '{print $4}' | cut -d/ -f1)"
state="$(docker inspect -f '{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo '?')"
health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}' "$CONTAINER" 2>/dev/null || echo '?')"
http="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:80/ 2>/dev/null || echo '?')"
echo
if [ "$state" = "running" ] && [ "$http" = "200" ]; then
  c_g "========================================================================"
  c_g " FILE-SERVER RESTAURADO  ✓   estado=$state ($health)   web=[$http]   ip=${ip_now:-?}"
  c_g "   web: http://${ip_now:-?}:80      ssh: :2222"
  c_g "========================================================================"
  echo
  c_y "Pendientes que NO dependen de esta PC:"
  echo "   · Reserva DHCP en el router para la MAC de $IFACE -> IP 192.168.10.20."
  echo "   · Red aislada del lab 192.168.10.0/24 (router/DHCP en .1)."
  echo "   · Abrí una terminal nueva para ver el cartel de estado en el login."
else
  c_r "La verificación no dio verde: estado=$state web=$http"
  c_r "Revisá:  cd $REPO_DIR/node && ./fileserver.sh status   y   ./fileserver.sh logs"
  exit 1
fi
