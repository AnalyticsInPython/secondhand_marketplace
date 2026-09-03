#!/usr/bin/env bash
# One command to run the MVP locally: API on :8000, app on :3000.
#
#   ./dev.sh                      # seeds on first run
#   ./dev.sh --reseed             # drop and reseed the database
#   DEMO_EMAIL=you@columbia.edu ./dev.sh --reseed
set -euo pipefail
cd "$(dirname "$0")"

DEMO_EMAIL="${DEMO_EMAIL:-vinayak@columbia.edu}"
PY=backend/.venv/bin/python

# ---- backend environment
if [ ! -x "$PY" ]; then
  echo "▸ creating backend/.venv"
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 backend/.venv
    uv pip install --python "$PY" -r backend/requirements.txt
  else
    python3.12 -m venv backend/.venv
    "$PY" -m pip install -q -r backend/requirements.txt
  fi
fi
[ -f backend/.env ] || cp backend/.env.example backend/.env

# ---- seed
if [ "${1:-}" = "--reseed" ] || [ ! -f backend/columbia_market.db ]; then
  echo "▸ seeding (demo account: $DEMO_EMAIL)"
  (cd backend && "$PWD/../$PY" -m scripts.seed --users 600 --listings 900 --reset --demo-email "$DEMO_EMAIL")
fi

# ---- frontend environment
[ -d frontend/node_modules ] || (echo "▸ npm install" && cd frontend && npm install --no-audit --no-fund)

# ---- run both
cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd backend && exec "$PWD/.venv/bin/uvicorn" app.main:app --reload --port 8000) &
(cd frontend && exec npm run dev) &

echo
echo "  API   http://localhost:8000/docs"
echo "  App   http://localhost:3000/signin"
echo "  Sign in as $DEMO_EMAIL — the link appears on screen (EMAIL_DEV_MODE)."
echo
wait
