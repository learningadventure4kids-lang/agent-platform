#!/usr/bin/env bash
#
# One-click launcher for macOS/Linux.
#
# Postgres + pgvector, the FastAPI backend, and the knowledge worker run
# via Docker Compose (the RAG/knowledge-base feature needs pgvector, which
# SQLite can't provide). The admin dashboard runs locally via `npm run dev`
# for a fast dev-reload loop. See README.md "Local Postgres without Docker"
# if you'd rather run Postgres yourself instead of via Docker.
#
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

ADMIN_PORT=5178
MODEL="qwen3:8b"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[..]${NC} $1"; }
fail()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo "================================================================"
echo "  Aria Agent Platform - Local Launcher"
echo "================================================================"
echo

command -v docker >/dev/null 2>&1 || fail "Docker not found on PATH. Install Docker Desktop (or Docker Engine) and re-run this script."
docker compose version >/dev/null 2>&1 || fail "'docker compose' not available. Update Docker to a version with Compose v2 built in."
info "Docker found."

command -v ollama >/dev/null 2>&1 || fail "Ollama not found on PATH. Install it from https://ollama.com/download and re-run this script."
info "Ollama found."

command -v node >/dev/null 2>&1 || fail "Node.js not found on PATH. Install Node 18+ from https://nodejs.org/."
command -v npm  >/dev/null 2>&1 || fail "npm not found on PATH."
info "Node/npm found."

if [ -f backend/.env ]; then
    CONFIGURED_MODEL="$(grep -E '^OLLAMA_MODEL=' backend/.env | cut -d '=' -f2- || true)"
    [ -n "$CONFIGURED_MODEL" ] && MODEL="$CONFIGURED_MODEL"
    CONFIGURED_EMBED="$(grep -E '^EMBEDDING_MODEL=' backend/.env | cut -d '=' -f2- || true)"
fi
EMBED_MODEL="${CONFIGURED_EMBED:-nomic-embed-text}"

for m in "$MODEL" "$EMBED_MODEL"; do
    echo "Checking for Ollama model \"$m\"..."
    if ollama list | grep -qi "$m"; then
        info "Model $m already available."
    else
        warn "Model not found locally. Pulling $m (this may take a while)..."
        ollama pull "$m"
    fi
done

[ -f backend/.env ] || { cp backend/.env.example backend/.env; info "Created backend/.env from .env.example -- edit it if you need custom settings."; }
[ -f .env ] || { cp .env.example .env; info "Created root .env from .env.example (Postgres credentials for docker-compose)."; }
[ -f frontend/.env ] || cp frontend/.env.example frontend/.env

echo "Starting Postgres + pgvector, backend API, and the knowledge worker via Docker Compose..."
docker compose up -d --build

echo "Waiting for the backend to become healthy..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
        info "Backend is up."
        break
    fi
    sleep 1
done

cd frontend
if [ ! -d node_modules ]; then
    warn "Installing admin dashboard dependencies (first run only)..."
    npm install
fi
cd ..

mkdir -p .run-logs
ADMIN_LOG=".run-logs/admin.log"

cleanup() {
    echo
    warn "Stopping admin dashboard dev server (Docker services keep running -- 'docker compose down' to stop those too)..."
    [ -n "${ADMIN_PID:-}" ] && kill "$ADMIN_PID" 2>/dev/null || true
    wait 2>/dev/null || true
    echo "Stopped."
}
trap cleanup EXIT INT TERM

echo "Starting admin dashboard on http://localhost:${ADMIN_PORT} (log: $ADMIN_LOG)..."
(
    cd frontend
    exec npm run dev -- --port "$ADMIN_PORT"
) > "$ADMIN_LOG" 2>&1 &
ADMIN_PID=$!

sleep 3

URL="http://localhost:${ADMIN_PORT}"
if command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true
fi

echo
echo "================================================================"
echo "  Backend:         http://localhost:8000 (docs at /docs)"
echo "  Admin dashboard: http://localhost:${ADMIN_PORT}"
echo "  Postgres:        localhost:5432"
echo
echo "  Public agent tokens for the seeded sample agents were logged by"
echo "  the backend container -- run: docker compose logs backend | grep 'Seeded token'"
echo
echo "  Docker services (postgres/backend/worker) keep running after this"
echo "  script exits. Stop them with: docker compose down"
echo
echo "  Press Ctrl+C to stop the admin dashboard dev server."
echo "================================================================"

wait
