#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -f ".env.prod" ]]; then
  echo "ERROR: .env.prod not found in $(pwd)"
  exit 1
fi

export ENV_FILE=".env.prod"
export PYTHONUNBUFFERED="1"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  exit 1
fi

# Intentionally (re)install deps on each start, as requested.
rm -rf .venv
python3 -m venv .venv
./.venv/bin/python -m pip install -U pip wheel >/dev/null
./.venv/bin/python -m pip install -r requirements.txt >/dev/null

exec ./.venv/bin/python app.py

