"""
tests/test_concurrency_load.py
==============================
Part 19 — Concurrency & Load Stress Test Suite.
Measures system stability, latency (p50, p95, p99), error rates,
CPU utilization, and memory deltas under 10, 25, and 50 concurrent simulated users.
"""

import os
import sys
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil

# Ensure repo root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.auth import get_supabase_admin_client, get_data_backend
from services.profiles import get_profile, list_profiles_by_role
from services.journey import get_journey_timeline
from services.notifications import list_notifications
from services.schemes import list_schemes
from services.help_requests import list_requests


def simulate_user_session(user_id: str, role: str) -> dict:
    """Simulates a standard user dashboard load workflow."""
    start_time = time.perf_counter()
    errors = []
    
    try:
        # Step 1: Fetch user profile
        prof = get_profile(user_id)
        
        # Step 2: Fetch unread notifications
        notifs = list_notifications(user_id)
        
        # Step 3: Fetch schemes catalog
        schemes = list_schemes()
        
        # Step 4: Role-specific action
        if role == "aspirant":
            timeline = get_journey_timeline(user_id)
            reqs = list_requests(user_id)
        elif role in ("guide", "sme"):
            aspirants = list_profiles_by_role("aspirant")
        elif role == "admin":
            all_aspirants = list_profiles_by_role("aspirant")
            
    except Exception as e:
        errors.append(str(e))
        
    duration = time.perf_counter() - start_time
    return {
        "user_id": user_id,
        "duration": duration,
        "success": len(errors) == 0,
        "errors": errors
    }


def run_load_tier(num_users: int, test_users: list) -> dict:
    """Executes a load test tier with num_users concurrent threads."""
    print(f"\n==================================================")
    print(f"[*] RUNNING LOAD TIER: {num_users} CONCURRENT SESSIONS")
    print(f"==================================================")
    
    process = psutil.Process()
    mem_before_mb = process.memory_info().rss / (1024 * 1024)
    cpu_before = psutil.cpu_percent(interval=None)
    
    start_time = time.perf_counter()
    results = []
    
    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = []
        for i in range(num_users):
            user = test_users[i % len(test_users)]
            futures.append(executor.submit(simulate_user_session, user["id"], user["role"]))
            
        for future in as_completed(futures):
            results.append(future.result())
            
    total_elapsed = time.perf_counter() - start_time
    mem_after_mb = process.memory_info().rss / (1024 * 1024)
    cpu_after = psutil.cpu_percent(interval=None)
    
    durations = [r["duration"] for r in results]
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    
    durations.sort()
    n = len(durations)
    p50 = durations[int(0.50 * n)] if n > 0 else 0
    p95 = durations[int(0.95 * n)] if n > 0 else 0
    p99 = durations[min(int(0.99 * n), n - 1)] if n > 0 else 0
    avg_latency = statistics.mean(durations) if n > 0 else 0
    
    tier_summary = {
        "concurrency": num_users,
        "total_requests": num_users,
        "successful": len(successes),
        "failed": len(failures),
        "error_rate_percent": round((len(failures) / num_users) * 100, 2),
        "total_duration_sec": round(total_elapsed, 2),
        "throughput_req_per_sec": round(num_users / total_elapsed, 2) if total_elapsed > 0 else 0,
        "latency_p50_sec": round(p50, 3),
        "latency_p95_sec": round(p95, 3),
        "latency_p99_sec": round(p99, 3),
        "latency_avg_sec": round(avg_latency, 3),
        "memory_start_mb": round(mem_before_mb, 2),
        "memory_end_mb": round(mem_after_mb, 2),
        "memory_delta_mb": round(mem_after_mb - mem_before_mb, 2),
        "cpu_percent": cpu_after
    }
    
    print(f"Results for Concurrency {num_users}:")
    print(f" - Successful: {tier_summary['successful']}/{tier_summary['total_requests']} (Error rate: {tier_summary['error_rate_percent']}%)")
    print(f" - Total Time: {tier_summary['total_duration_sec']}s (Throughput: {tier_summary['throughput_req_per_sec']} req/s)")
    print(f" - Latencies: p50={tier_summary['latency_p50_sec']}s, p95={tier_summary['latency_p95_sec']}s, p99={tier_summary['latency_p99_sec']}s, avg={tier_summary['latency_avg_sec']}s")
    print(f" - Memory Delta: {tier_summary['memory_delta_mb']} MB (End: {tier_summary['memory_end_mb']} MB)")
    print(f" - CPU Usage: {tier_summary['cpu_percent']}%")
    
    if failures:
        print(f" - Sample failure: {failures[0]['errors']}")
        
    return tier_summary


def main():
    print("[*] Initializing Concurrency Test Suite...")
    backend = get_data_backend()
    admin_client = get_supabase_admin_client()
    print(f" - Data Backend: {backend}")
    print(f" - Admin Client: {'Available' if admin_client else 'None'}")
    
    # Harvest active profiles to use as test subjects
    test_users = []
    if backend == "supabase" and admin_client:
        try:
            res = admin_client.table("profiles").select("id, role, email").execute()
            if res.data:
                test_users = res.data
        except Exception as e:
            print(f"[!] Warning: Unable to fetch live profiles: {e}")
            
    if not test_users:
        test_users = [
            {"id": "00000000-0000-0000-0000-000000000001", "role": "admin", "email": "admin@fulcrum.in"},
            {"id": "00000000-0000-0000-0000-000000000002", "role": "admin", "email": "manicktie@gmail.com"},
            {"id": "00000000-0000-0000-0000-000000000010", "role": "guide", "email": "rajendran@fulcrum.in"},
            {"id": "00000000-0000-0000-0000-000000000020", "role": "sme", "email": "kumar.sme@fulcrum.in"},
            {"id": "00000000-0000-0000-0000-000000000100", "role": "aspirant", "email": "ravi.kumar@milletfoods.in"}
        ]
        
    print(f" - Harvested {len(test_users)} user personas for session simulation.")
    
    all_summaries = []
    for tier in [10, 25, 50]:
        summary = run_load_tier(tier, test_users)
        all_summaries.append(summary)
        time.sleep(1) # brief pause between tiers
        
    # Write JSON results artifact
    out_path = os.path.join(os.path.dirname(__file__), "load_test_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)
    print(f"\n[+] Concurrency test completed. Results written to: {out_path}")


if __name__ == "__main__":
    main()
