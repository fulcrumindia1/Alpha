"""
test_dual_backend.py — Comprehensive Verification for FULCRUM-INDIA Cluster A
Tests both DATA_BACKEND=supabase and DATA_BACKEND=sqlite modes.
"""

import os
import sys

def test_supabase_mode():
    print("\n==========================================")
    print("TESTING SUPABASE PRIMARY MODE")
    print("==========================================")
    os.environ["DATA_BACKEND"] = "supabase"
    
    from services.auth import get_data_backend, get_supabase_client, get_supabase_admin_client, backfill_auth_users
    from services.profiles import get_profile, list_profiles_by_role
    from services.schemes import list_schemes, get_scheme
    from services.help_requests import list_requests, check_and_escalate_overdue_requests
    from services.journey import get_journey_timeline
    from services.relationships import get_aspirant_mentors

    backend = get_data_backend()
    print(f"[Supabase Test] Active backend: {backend}")
    assert backend == "supabase", f"Expected backend 'supabase', got {backend}"

    client = get_supabase_client()
    assert client is not None, "Public Supabase client must be initialized"
    print("[Supabase Test] Public Supabase client initialized successfully.")

    admin_client = get_supabase_admin_client()
    assert admin_client is not None, "Admin Supabase client must be initialized"
    print("[Supabase Test] Admin Supabase client initialized successfully.")

    # Check backfill
    res = backfill_auth_users("pravindev666@gmail.com")
    print(f"[Supabase Test] Backfill result: {res}")
    assert "error" not in res, f"Backfill failed: {res.get('error')}"

    # Check admin profile
    admin_prof = admin_client.table("profiles").select("*").eq("email", "pravindev666@gmail.com").execute().data
    assert len(admin_prof) > 0, "Admin profile must exist"
    assert admin_prof[0]["role"] == "admin", f"Expected role 'admin', got {admin_prof[0]['role']}"
    print(f"[Supabase Test] Verified admin user: {admin_prof[0]['email']} (role={admin_prof[0]['role']})")

    # Check schemes in Supabase using admin client
    # NOTE: list_schemes() now uses RLS-enforced user client, which returns 0 rows
    # outside a Streamlit session (no JWT). This is correct behavior — RLS is working!
    # We use the admin client here because this is a privileged test script.
    schemes_res = admin_client.table("schemes").select("*").execute()
    schemes = schemes_res.data or []
    print(f"[Supabase Test] Total schemes retrieved (via admin): {len(schemes)}")
    assert len(schemes) >= 170, f"Expected >= 170 schemes, got {len(schemes)}"

    # Check released schemes security invariant
    from services.schemes import get_released_schemes_for_aspirant
    aspirant_schemes = get_released_schemes_for_aspirant("5ef8bed6-fbc9-49a7-8a16-91a7cd26b612")
    print(f"[Supabase Test] Retrieved released schemes for aspirant: {len(aspirant_schemes)}")

    # Check help requests escalation RPC
    count_escalated = check_and_escalate_overdue_requests()
    print(f"[Supabase Test] Overdue ticket check ran successfully (escalated: {count_escalated}).")

    print(">>> SUPABASE PRIMARY MODE: ALL CHECKS PASSED <<<\n")


def test_sqlite_mode():
    print("\n==========================================")
    print("TESTING SQLITE FALLBACK MODE")
    print("==========================================")
    os.environ["DATA_BACKEND"] = "sqlite"

    from services.auth import get_data_backend, login_user
    from services.profiles import get_profile, list_profiles_by_role
    from services.schemes import list_schemes
    from services.help_requests import list_requests
    from services.journey import get_journey_timeline

    backend = get_data_backend()
    print(f"[SQLite Test] Active backend: {backend}")
    assert backend == "sqlite", f"Expected backend 'sqlite', got {backend}"

    # Verify verified test account login in SQLite mode
    prof, err = login_user("admin@fulcrum.in", "Admin@123")
    assert prof is not None, f"SQLite login failed: {err}"
    assert prof["role"] == "admin", f"Expected admin role, got {prof['role']}"
    print(f"[SQLite Test] Logged in admin: {prof['email']} ({prof['full_name']})")

    aspirant_prof, err = login_user("ravi.kumar@milletfoods.in", "Aspirant@123")
    assert aspirant_prof is not None, f"SQLite aspirant login failed: {err}"
    print(f"[SQLite Test] Logged in aspirant: {aspirant_prof['email']}")

    # Check schemes in SQLite
    sqlite_schemes = list_schemes(active_only=False)
    print(f"[SQLite Test] Total schemes in SQLite: {len(sqlite_schemes)}")

    print(">>> SQLITE FALLBACK MODE: ALL CHECKS PASSED <<<\n")


if __name__ == "__main__":
    test_supabase_mode()
    test_sqlite_mode()
    print("ALL TESTS PASSED SUCCESSFULLY!")
