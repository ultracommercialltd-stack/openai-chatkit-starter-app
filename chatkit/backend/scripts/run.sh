#!/usr/bin/env bash

# Simple helper to start the ChatKit backend (similar to cat-lounge UX).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
  echo "Creating virtual env in $PROJECT_ROOT/.venv ..."
  python -m venv .venv
fi

source .venv/bin/activate

echo "Installing backend deps (editable) ..."
pip install -e . >/dev/null

# Load env vars from the repo's .env.local (if present). The LoveGenie adapter
# needs LOVEGENIE_API_BASE (and optional SUPABASE_*); it does NOT need an
# OPENAI_API_KEY because the LLM lives in the Love-Genie backend.
ENV_FILE="$PROJECT_ROOT/../.env.local"
if [ -f "$ENV_FILE" ]; then
  echo "Sourcing env from $ENV_FILE"
  # shellcheck disable=SC1090
  set -a
  . "$ENV_FILE"
  set +a
fi

if [ -z "${LOVEGENIE_API_BASE:-}" ]; then
  echo "Note: LOVEGENIE_API_BASE not set; defaulting to http://127.0.0.1:4310"
fi

echo "Starting LoveGenie ChatKit adapter on http://127.0.0.1:8000 ..."
exec uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

