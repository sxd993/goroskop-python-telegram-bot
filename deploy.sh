#!/usr/bin/env bash
set -euo pipefail

APP_NAME="goroskop-bot-prod"
ENV_PATH=".env.prod"

cd "$(dirname "${BASH_SOURCE[0]}")"

echo "== goroskop-bot production bootstrap =="

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  exit 1
fi

if [[ ! -f "$ENV_PATH" ]]; then
  echo "ERROR: $ENV_PATH not found in $(pwd)"
  echo "Create it first (example: cp .env.prod.example .env.prod) and fill BOT_TOKEN/PROVIDER_TOKEN."
  exit 1
fi

echo "== venv + deps =="
rm -rf .venv
python3 -m venv .venv
./.venv/bin/python -m pip install -U pip wheel >/dev/null
./.venv/bin/python -m pip install -r requirements.txt >/dev/null

echo "== pm2 =="
if ! command -v pm2 >/dev/null 2>&1; then
  if command -v npm >/dev/null 2>&1; then
    npm i -g pm2
  else
    echo "ERROR: pm2 not found and npm not found to install it."
    echo "Install Node.js/npm and run: npm i -g pm2"
    exit 1
  fi
fi

CMD="export ENV_FILE=$ENV_PATH; export PYTHONUNBUFFERED=1; exec $(pwd)/.venv/bin/python $(pwd)/app.py"

if pm2 describe "$APP_NAME" >/dev/null 2>&1; then
  pm2 delete "$APP_NAME"
  pm2 start bash --name "$APP_NAME" -- -lc "$CMD"
else
  pm2 start bash --name "$APP_NAME" -- -lc "$CMD"
fi

pm2 save
pm2 status "$APP_NAME" || true

echo ""
echo "Done. If you want автозапуск после ребута:"
echo "  pm2 startup"
echo "  pm2 save"
