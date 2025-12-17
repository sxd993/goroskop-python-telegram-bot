#!/usr/bin/env bash
set -euo pipefail

APP_NAME="goroskop-bot-prod"

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -f ".env.prod" ]]; then
  echo "ERROR: .env.prod not found in $(pwd)"
  echo "Create it first (example: cp .env.prod.example .env.prod) and fill BOT_TOKEN/PROVIDER_TOKEN."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

./.venv/bin/python -m pip install -U pip wheel >/dev/null
./.venv/bin/python -m pip install -r requirements.txt

if ! command -v pm2 >/dev/null 2>&1; then
  if command -v npm >/dev/null 2>&1; then
    npm i -g pm2
  else
    echo "ERROR: pm2 not found and npm not found to install it."
    echo "Install Node.js/npm and run: npm i -g pm2"
    exit 1
  fi
fi

if pm2 describe "$APP_NAME" >/dev/null 2>&1; then
  pm2 reload ecosystem.config.js --only "$APP_NAME" --update-env
else
  pm2 start ecosystem.config.js --only "$APP_NAME"
fi

pm2 save
pm2 status "$APP_NAME"
