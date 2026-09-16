"""
verify_multi_sme_and_security.py — Automated Verification Test Suite
Tests:
1. Multi-SME assignment (Concurrent Advisory Panel)
2. Mentors retrieval returning all assigned SMEs in 'smes'
3. SME active caseload query (both SMEs see their assigned student)
4. Replacement mode reset
5. First-login permanent password change lifecycle
"""

import sys
import os
import json

# Ensure SQLite local backend for testing
os.environ["DATA_BACKEND"] = "sqlite"

from services.local_db import get_local_db
from services.relationships import (
    assign_sme,
    get_aspirant_mentors,
    get_assigned_aspirants_for_sme,
    get_assignment_history
)
from services.auth import complete_first_login_password_change
from services.profiles import get_profile

def run_tests():
    print("======================================================================")
    print("VERIFICATION SUITE: MULTI-SME SUPPORT & FIRST-LOGIN SECURITY")
    print("======================================================================")

    db = get_local_db()

    # Step 0: Ensure test accounts exist in SQLite
    admin_id = "72655c43-9f13-4309-a8a0-194570a6c2aa"
    aspirant_id = "6e667c86-84d3-4b65-b727-90f71f2b2875"
    sme1_id = "953bdd1a-5aeb-4919-84a7-8ac0c3b0b47f"
    
    # Create SME 2 (Legal & Corporate)
    sme2_id = "sme-legal-test-uuid-2026"
    db.create_user_with_password(
        "sme2@fulcrum.in",
        "Welcome@2026",
        {
            "id": sme2_id,
            "email": "sme2@fulcrum.in",
            "full_name": "Advocate Meenakshi Sundaram",
            "role": "sme",
            "phone": "9840998877",
            "district": "Madurai",
            "profile_data": {
                "expertise": "Corporate Law, IP & Trademark Licensing",
                "industry": "Legal & IP",
                "bio": "High Court advocate specializing in MSME intellectual property.",
                "temp_password_issued": True
            }
        }
    )

    print("\n--- TEST 1: Multi-SME Concurrent Advisory Panel Assignment ---")
    # 1. Assign SME 1
    ok1, err1 = assign_sme(aspirant_id, sme1_id, admin_id=admin_id, notes="GST advisory", mode="replace")
    assert ok1, f"Failed to assign SME 1: {err1}"
    print(f"  [PASSED] Assigned SME 1 ({sme1_id[:8]}) to Aspirant.")

    # 2. Add SME 2 using mode='add'
    ok2, err2 = assign_sme(aspirant_id, sme2_id, admin_id=admin_id, notes="Legal IP audit", mode="add")
    assert ok2, f"Failed to add SME 2: {err2}"
    print(f"  [PASSED] Added SME 2 ({sme2_id[:8]}) to Advisory Panel using mode='add'.")

    # 3. Verify get_aspirant_mentors returns both in 'smes'
    mentors = get_aspirant_mentors(aspirant_id)
    assigned_smes = mentors.get("smes", [])
    assigned_ids = [s["id"] for s in assigned_smes]
    assert len(assigned_smes) >= 2, f"Expected at least 2 SMEs, got {len(assigned_smes)}"
    assert sme1_id in assigned_ids, "SME 1 missing from assigned smes list"
    assert sme2_id in assigned_ids, "SME 2 missing from assigned smes list"
    print(f"  [PASSED] get_aspirant_mentors returned {len(assigned_smes)} concurrent specialists:")
    for s in assigned_smes:
        print(f"     - {s.get('full_name')} ({s.get('profile_data', {}).get('expertise')})")

    print("\n--- TEST 2: Multi-SME Caseload Visibility ---")
    # Verify SME 1 sees Aspirant
    caseload1 = get_assigned_aspirants_for_sme(sme1_id)
    c1_ids = [c["id"] for c in caseload1]
    assert aspirant_id in c1_ids, "Aspirant not visible in SME 1 caseload"
    print(f"  [PASSED] SME 1 correctly sees {len(caseload1)} assigned mentee(s) including target Aspirant.")

    # Verify SME 2 sees Aspirant
    caseload2 = get_assigned_aspirants_for_sme(sme2_id)
    c2_ids = [c["id"] for c in caseload2]
    assert aspirant_id in c2_ids, "Aspirant not visible in SME 2 caseload"
    print(f"  [PASSED] SME 2 correctly sees {len(caseload2)} assigned mentee(s) including target Aspirant.")

    print("\n--- TEST 3: Duplicate Assignment Prevention ---")
    # Trying to add SME 2 again should fail gracefully
    ok_dup, err_dup = assign_sme(aspirant_id, sme2_id, admin_id=admin_id, mode="add")
    assert not ok_dup, "Adding duplicate SME should return False"
    print(f"  [PASSED] Duplicate assignment rejected: '{err_dup}'")

    print("\n--- TEST 4: SME Replacement Mode ---")
    # Replacing should reset the panel to only the new SME
    sme3_id = "sme-tax-specialist-3"
    db.create_user_with_password(
        "sme3@fulcrum.in",
        "Welcome@2026",
        {
            "id": sme3_id,
            "email": "sme3@fulcrum.in",
            "full_name": "CA Ananthakrishnan",
            "role": "sme",
            "phone": "9840112233",
            "district": "Coimbatore",
            "profile_data": {
                "expertise": "Income Tax & Auditing",
                "industry": "Taxation",
                "bio": "Senior partner specializing in corporate returns."
            }
        }
    )
    ok_rep, err_rep = assign_sme(aspirant_id, sme3_id, admin_id=admin_id, notes="Replacing advisory team with new lead specialist", mode="replace")
    assert ok_rep, f"Replacement failed: {err_rep}"
    
    mentors_after_rep = get_aspirant_mentors(aspirant_id)
    post_rep_ids = [s["id"] for s in mentors_after_rep.get("smes", [])]
    assert post_rep_ids == [sme3_id], f"Expected only [sme3], got {post_rep_ids}"
    print(f"  [PASSED] Replacement mode correctly set advisory panel to new specialist: {post_rep_ids}")

    print("\n--- TEST 5: First-Login Password Change Lifecycle ---")
    # Verify SME 2 initially had temp_password_issued: True
    prof_sme2 = get_profile(sme2_id)
    assert prof_sme2.get("profile_data", {}).get("temp_password_issued") is True, "Expected temp_password_issued=True initially"
    print("  [PASSED] Account correctly flagged with temp_password_issued: True upon administrative provisioning.")

    # Execute first login permanent password change
    ok_pw, err_pw = complete_first_login_password_change(sme2_id, "Permanent@Secured2026")
    assert ok_pw, f"Password change failed: {err_pw}"
    
    # Verify profile now has temp_password_issued: False
    prof_sme2_updated = get_profile(sme2_id)
    assert prof_sme2_updated.get("profile_data", {}).get("temp_password_issued") is False, "Expected temp_password_issued=False after change"
    
    # Verify password hash updated and authenticates
    assert db.verify_password("sme2@fulcrum.in", "Permanent@Secured2026"), "New permanent password verification failed"
    print("  [PASSED] First-login password change completed, temp_password_issued cleared to False, and new password authenticated.")

    print("\n======================================================================")
    print(">>> ALL MULTI-SME & SECURITY TESTS COMPLETED SUCCESSFULLY! <<<")
    print("======================================================================")

if __name__ == "__main__":
    run_tests()
