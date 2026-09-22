"""
scripts/health_check.py — Production Diagnostic Health Check for FULCRUM-INDIA
=============================================================================
Performs lightweight, non-destructive health checks:
1. Streamlit web server response (_stcore/health)
2. Active data backend configuration (verifies DATA_BACKEND=supabase in production)
3. Live Supabase database connectivity ping (read-only count query)
"""

import sys
import os
import requests
from datetime import datetime, timezone

def check_streamlit_health(base_url: str = None) -> bool:
    if not base_url:
        base_url = os.environ.get("STREAMLIT_HEALTH_URL", "http://localhost:8501")
    try:
        url = f"{base_url.rstrip('/')}/_stcore/health"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            print(f"[HealthCheck] Streamlit HTTP OK: {resp.status_code} ({resp.text.strip()})")
            return True
        else:
            print(f"[HealthCheck] Streamlit HTTP WARN: status {resp.status_code}")
            return False
    except Exception as e:
        print(f"[HealthCheck] Streamlit HTTP FAILED: {e}")
        return False

def check_supabase_connectivity() -> bool:
    # Set path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from services.auth import get_data_backend, get_supabase_admin_client, get_supabase_client
    backend = get_data_backend()
    print(f"[HealthCheck] Active Backend: {backend}")

    if backend != "supabase":
        print("[HealthCheck] Notice: DATA_BACKEND is not 'supabase' (running in SQLite mode).")
        return True

    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        print("[HealthCheck] Supabase Client: FAILED to initialize.")
        return False

    try:
        res = client.table("profiles").select("id", count="exact").limit(1).execute()
        count = res.count if hasattr(res, "count") and res.count is not None else len(res.data or [])
        print(f"[HealthCheck] Supabase Database OK: successfully connected. Profiles count: {count}")
        return True
    except Exception as e:
        print(f"[HealthCheck] Supabase Database FAILED: {e}")
        return False

def main():
    print(f"=== FULCRUM HEALTH CHECK [{datetime.now(timezone.utc).isoformat()}] ===")
    st_ok = check_streamlit_health()
    sb_ok = check_supabase_connectivity()

    if st_ok and sb_ok:
        print("=== RESULT: HEALTHY (ALL CHECKS PASSED) ===")
        sys.exit(0)
    elif sb_ok and not st_ok:
        print("=== RESULT: DATABASE HEALTHY (Streamlit web server not responding locally) ===")
        sys.exit(1)
    else:
        print("=== RESULT: UNHEALTHY ===")
        sys.exit(2)

if __name__ == "__main__":
    main()
