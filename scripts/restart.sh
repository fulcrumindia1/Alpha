#!/usr/bin/env bash
# ==============================================================================
# scripts/restart.sh — Safe Container Restart for Fulcrum India
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "[*] Restarting Fulcrum and Caddy services..."
docker compose restart

echo "[*] Waiting for services to stabilize..."
sleep 5

docker compose ps
echo "[+] Services restarted successfully. Run ./scripts/status.sh to check health."
