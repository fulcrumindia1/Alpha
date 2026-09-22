#!/usr/bin/env bash
# ==============================================================================
# scripts/rollback.sh — 5-Minute Emergency Rollback for Fulcrum India
# Usage:
#   ./scripts/rollback.sh                 (reverts to previous Git commit HEAD~1)
#   ./scripts/rollback.sh <commit_hash>   (reverts to specific known-good commit)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

TARGET_COMMIT="${1:-HEAD~1}"

echo "=================================================="
echo "FULCRUM INDIA — EMERGENCY ROLLBACK PROCEDURE"
echo "Target Commit: $TARGET_COMMIT"
echo "=================================================="

# 1. Verify git repo
if [ ! -d ".git" ]; then
    echo "[-] Error: .git directory not found. Rollback requires git repository."
    exit 1
fi

# 2. Checkout target commit
echo "[*] Checking out $TARGET_COMMIT..."
git checkout "$TARGET_COMMIT"

# 3. Rebuild and start previous container
echo "[*] Rebuilding container from rolled-back commit..."
docker compose build fulcrum

echo "[*] Starting rolled-back container..."
docker compose up -d --remove-orphans

# 4. Wait for health
echo "[*] Waiting for container health check..."
sleep 8

# 5. Verify health
if docker compose exec -T fulcrum python scripts/health_check.py; then
    echo "=================================================="
    echo "[+] ROLLBACK COMPLETED SUCCESSFULLY!"
    echo "    Current commit: $(git rev-parse --short HEAD)"
    echo "=================================================="
else
    echo "[-] WARNING: Health check reported an issue after rollback."
    echo "[-] Inspect logs with: ./scripts/logs.sh"
    exit 1
fi
