#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy .env.example to .env and fill in the secrets."
  exit 1
fi

python3 scripts/configure_interview_demo.py

if ! grep -Eq '^ALADDIN_DEMO_PASSWORD=.{12,}$' .env; then
  echo "ALADDIN_DEMO_PASSWORD must be at least 12 characters."
  exit 1
fi

if ! grep -Eq '^ALADDIN_API_TOKEN=.{24,}$' .env; then
  echo "ALADDIN_API_TOKEN must be at least 24 characters."
  exit 1
fi

docker compose --profile interview up --build --detach

echo "Interview demo started. The public trycloudflare.com URL will appear below."
echo "Press Control-C to stop following logs; use 'make demo-down' after the interview."
docker compose logs --follow tunnel
