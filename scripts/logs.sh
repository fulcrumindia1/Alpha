#!/usr/bin/env bash
# ==============================================================================
# scripts/logs.sh — Stream Application & Caddy Logs
# Usage:
#   ./scripts/logs.sh           (tail fulcrum logs)
#   ./scripts/logs.sh caddy     (tail caddy reverse proxy logs)
#   ./scripts/logs.sh all       (tail all service logs)
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

TARGET="${1:-fulcrum}"

if [ "$TARGET" = "all" ]; then
    echo "[*] Following all container logs (Ctrl+C to stop)..."
    docker compose logs --tail=150 -f
elif [ "$TARGET" = "caddy" ]; then
    echo "[*] Following Caddy reverse proxy logs (Ctrl+C to stop)..."
    docker compose logs --tail=150 -f caddy
else
    echo "[*] Following Fulcrum Streamlit application logs (Ctrl+C to stop)..."
    docker compose logs --tail=150 -f fulcrum
fi
