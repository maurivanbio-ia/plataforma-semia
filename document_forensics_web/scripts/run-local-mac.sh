#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export WATERMARKS_SERVICE_URL="${WATERMARKS_SERVICE_URL:-http://127.0.0.1:18765}"

if ! curl -fsS "$WATERMARKS_SERVICE_URL/health" >/dev/null; then
  echo "Erro: watermarks-remover não está acessível em $WATERMARKS_SERVICE_URL"
  echo "Inicie-o antes, por exemplo:"
  echo "  cd ~/Developer/watermarks-remover"
  echo "  python3 service/scripts/server.py --host 127.0.0.1 --port 18765"
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install -r requirements.txt
exec uvicorn app.main:app --host 127.0.0.1 --port 8080
