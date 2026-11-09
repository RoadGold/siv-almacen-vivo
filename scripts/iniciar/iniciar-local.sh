#!/usr/bin/env bash
# Inicia el entorno local de SIV · Almacén Vivo (Linux / macOS).
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$RAIZ"

echo "[SIV] Levantando la base de datos..."
docker compose up -d db

echo "[SIV] Aplicando migraciones..."
cd backend
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install -q -e ".[dev]"
./.venv/bin/python -m alembic upgrade head
cd "$RAIZ"

echo "[SIV] Iniciando la API en http://127.0.0.1:8000"
cd backend
./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
cd "$RAIZ"

if [ "${1:-}" = "--con-frontend" ]; then
  echo "[SIV] Iniciando el frontend en http://127.0.0.1:5173"
  cd frontend
  [ -d node_modules ] || npm install
  npm run dev &
  cd "$RAIZ"
fi

echo "[SIV] Listo. Pulse Ctrl+C para detener."
trap 'kill $API_PID 2>/dev/null || true' EXIT
wait $API_PID
