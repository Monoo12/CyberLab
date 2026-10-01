#!/usr/bin/env bash
# Resetea el nodo a estado limpio entre visitantes (recrea el contenedor).
set -e
cd "$(dirname "$0")"
docker compose down
docker compose up -d
echo "[reset] FILE-SERVER reiniciado a estado limpio."
