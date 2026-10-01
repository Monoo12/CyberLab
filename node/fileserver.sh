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

# Usa 'docker compose' con o sin sudo segun los permisos del usuario.
dc() {
  if docker compose version >/dev/null 2>&1 && docker ps >/dev/null 2>&1; then
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
