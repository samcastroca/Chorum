#!/usr/bin/env bash
# Chorum — bootstrap de desarrollo sin Docker.
# Instala las dependencias de backend (uv) y frontend (npm).
# La versión completa (wizard de configuración, etc.) llega en la Fase 11.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Chorum: bootstrap de desarrollo"

# --- Requisitos ---
command -v uv >/dev/null 2>&1 || {
  echo "ERROR: 'uv' no está instalado. Ver https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
}
command -v npm >/dev/null 2>&1 || {
  echo "ERROR: 'npm' no está instalado (se necesita Node.js 20+)."
  exit 1
}

# --- .env ---
if [ ! -f "$repo_root/.env" ]; then
  echo "==> Creando .env a partir de .env.example"
  cp "$repo_root/.env.example" "$repo_root/.env"
fi

# --- Backend ---
echo "==> Backend: uv sync"
(cd "$repo_root/backend" && uv sync)

# --- Frontend ---
echo "==> Frontend: npm install"
(cd "$repo_root/frontend" && npm install)

echo "==> Listo."
echo "    Backend:  cd backend && uv run uvicorn app.main:app --reload"
echo "    Frontend: cd frontend && npm run dev"
