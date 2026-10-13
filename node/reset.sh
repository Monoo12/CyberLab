#!/usr/bin/env bash
# Resetea el nodo a estado limpio entre visitantes (recrea el contenedor).
# Delega en fileserver.sh para usar el MISMO manejo de sudo/rootful (si docker
# necesita sudo en este equipo, fileserver.sh ya lo resuelve; antes este script
# llamaba a 'docker compose' pelado y fallaba en esos equipos).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]:-$0}")"
exec ./fileserver.sh reset
