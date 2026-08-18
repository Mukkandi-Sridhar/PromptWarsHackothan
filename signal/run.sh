#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# SIGNAL — one-command setup and start
# Usage: ./run.sh
# ──────────────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo ""
echo "  ◉ SIGNAL — Reel Intelligence Agent"
echo "  ─────────────────────────────────────"
echo ""

# ── Copy .env if not present
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
  echo "  ℹ  Created .env from .env.example"
  echo "     Add your API key to .env to enable LLM mode (optional)"
  echo ""
fi

# ── Python virtual environment
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
  echo "  → Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
echo "  → Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r "$BACKEND_DIR/requirements.txt"

# ── Frontend dependencies
echo "  → Installing frontend dependencies..."
cd "$FRONTEND_DIR"
npm install --silent 2>/dev/null || npm install

# ── Database init and seeding
echo "  → Seeding database and vector index..."
cd "$SCRIPT_DIR"
python -m backend.seed 2>&1 | grep -E "(seeded|indexed|warn|error)" || true

# ── Start both servers
echo ""
echo "  ✓ Setup complete. Starting servers..."
echo ""
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "  API docs: http://localhost:8000/docs"
echo ""

# Start backend in background
cd "$SCRIPT_DIR"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "  → Waiting for backend..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    echo "  ✓ Backend ready"
    break
  fi
  sleep 0.5
done

# Start frontend
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  ✓ SIGNAL is running!"
echo "  ─────────────────────────────────────"
echo "  Open http://localhost:5173 in your browser"
echo ""
echo "  Demo: Swipe reels 1-4 → toggle Shallow/Agent → watch the ladder climb"
echo ""
echo "  Press Ctrl+C to stop"
echo ""

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait
