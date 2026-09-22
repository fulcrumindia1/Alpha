#!/usr/bin/env bash
# ==============================================================================
# scripts/status.sh — Quick System & Container Status for Fulcrum India
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=================================================="
echo "FULCRUM INDIA — PRODUCTION STATUS"
echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=================================================="

echo ""
echo "--- [1] CONTAINER STATE ---"
docker compose ps

echo ""
echo "--- [2] RESOURCE UTILIZATION ---"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}" fulcrum-app fulcrum-caddy 2>/dev/null || docker stats --no-stream

echo ""
echo "--- [3] HEALTH CHECK ---"
if docker ps -q -f name=fulcrum-app | grep -q .; then
    docker compose exec -T fulcrum python scripts/health_check.py 2>/dev/null || echo "[!] Healthcheck script failed"
else
    echo "[-] fulcrum-app is NOT running"
fi

echo "=================================================="
