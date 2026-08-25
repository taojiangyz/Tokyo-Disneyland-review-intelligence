#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
docker compose --profile interview down
echo "Interview demo and temporary public tunnel stopped."
