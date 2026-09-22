#!/usr/bin/env bash
# ==============================================================================
# scripts/deploy.sh — One-Command Production Deployment for Fulcrum India
# ==============================================================================
set -e

# Navigate to project root (directory containing this script's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=================================================="
echo "[*] FULCRUM PRODUCTION DEPLOYMENT STARTING"
echo "    Directory: $PROJECT_DIR"
echo "    Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=================================================="

# 1. Pull latest git changes if inside a git repository
if [ -d ".git" ]; then
    echo "[*] Pulling latest code from Git..."
    git pull || echo "[!] Warning: Git pull encountered an issue. Proceeding with local files."
fi

# 2. Validate production configuration (.env)
echo "[*] Checking production environment file (.env)..."
if [ ! -f ".env" ]; then
    echo "[-] FATAL ERROR: .env file missing in $PROJECT_DIR"
    echo "    Please create .env with DATA_BACKEND=supabase, SUPABASE_URL, and keys."
    exit 1
fi

# Check required variables
source .env 2>/dev/null || true
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SECRET_KEY" ]; then
    echo "[-] FATAL ERROR: .env is missing SUPABASE_URL or SUPABASE_SECRET_KEY."
    exit 1
fi
echo "[+] Environment configuration validated."

# 3. Build Docker container images
echo "[*] Building Docker Compose services..."
docker compose build

# 4. Launch or update containers
echo "[*] Starting containers in background..."
docker compose up -d --remove-orphans

# 5. Wait for Fulcrum healthcheck
echo "[*] Waiting for Fulcrum container health verification..."
MAX_RETRIES=20
COUNT=0
HEALTHY=false

while [ $COUNT -lt $MAX_RETRIES ]; do
    STATUS=$(docker inspect --format='{{json .State.Health.Status}}' fulcrum-app 2>/dev/null || echo '"starting"')
    echo "    [Try $((COUNT+1))/$MAX_RETRIES] Container health: $STATUS"
    if [ "$STATUS" = '"healthy"' ]; then
        HEALTHY=true
        break
    fi
    sleep 2
    COUNT=$((COUNT+1))
done

if [ "$HEALTHY" = false ]; then
    echo "[-] DEPLOYMENT FAILED: Fulcrum container did not reach healthy state in time."
    echo "[-] Recent logs:"
    docker compose logs --tail=60 fulcrum
    exit 1
fi

echo "[+] Fulcrum container is healthy!"

# 6. Run application & database health check inside container
echo "[*] Executing deep health check..."
docker compose exec -T fulcrum python scripts/health_check.py

# 7. Summary
echo "=================================================="
echo "[+] DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo "=================================================="
docker compose ps
