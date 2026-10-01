#!/usr/bin/env bash
# ============================================================================
# Control facil del FILE-SERVER (nodo vulnerable dockerizado).
#   on | start    -> encender (construye si hace falta)
#   off | stop    -> apagar
#   reset         -> reiniciar a estado limpio (entre visitantes)
#   status        -> ver estado
#   logs          -> ver logs en vivo (Ctrl+C para salir)
#
# Instalacion inicial del equipo: scripts/setup-fileserver.sh
# ============================================================================
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"   # carpeta node/

# Siempre el MISMO daemon (rootful): sin sudo si ya sos root, con sudo si no.
# Evita el "split-brain" entre un daemon rootless y uno rootful (contenedores
# duplicados, puertos que no bindean). Si tu Docker es rootless, exporta
# CYBERLAB_NOSUDO=1 para no usar sudo.
dc() {
  if [ "$(id -u)" -eq 0 ] || [ "${CYBERLAB_NOSUDO:-0}" = "1" ]; then
    docker compose "$@"
  else
    sudo docker compose "$@"
  fi
}

case "${1:-}" in
  on|start)
    dc up -d --build
    echo "[fileserver] ENCENDIDO"
    ;;
  off|stop)
    dc down
    echo "[fileserver] APAGADO"
    ;;
  reset)
    dc down
    dc up -d
    echo "[fileserver] reiniciado a estado limpio"
    ;;
  status)
    dc ps
    ;;
  logs)
    dc logs -f
    ;;
  *)
    echo "uso: $0 {on|off|reset|status|logs}"
    exit 1
    ;;
esac
