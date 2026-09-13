"""
verify_governance.py — Automated Test Suite for Scheme Governance & Guide Gatekeeper
===================================================================================
Tests Scenarios A through H:
- Scenario A: Aspirant initially has 0 released schemes (Empty State Gate)
- Scenario B: Guide generates scheme evaluation (Score, Match Checklist, Eligibility, Red Flags, Insider Intel)
- Scenario C: Guide releases scheme to assigned Aspirant (Release stored, Journey logged, Aspirant can see)
- Scenario D: Unauthorized Guide cannot release schemes to unassigned Aspirant
- Scenario E: Private Intelligence (hidden_agenda, red_flags, prompt) strictly stripped from Aspirant payload
- Scenario F: Guide withdraws released scheme (Status WITHDRAWN, Journey logged, Aspirant no longer sees)
- Scenario G: Aspirant help request automatically assigned to assigned Guide
- Scenario H: Unresolved help requests older than 7 days automatically escalate to Admin
"""

import sys
import os
import uuid
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from services.local_db import get_local_db
from services.schemes import (
    evaluate_scheme_for_aspirant,
    release_scheme_to_aspirant,
    withdraw_scheme_release,
    get_released_schemes_for_aspirant,
    get_guide_scheme_releases,
    list_schemes
)
from services.help_requests import (
    create_request,
    list_guide_requests,
    check_and_escalate_overdue_requests
)
from services.relationships import assign_guide, get_aspirant_mentors
from services.journey import get_journey_timeline

def run_all_tests():
    print("=" * 70)
    print("FULCRUM SCHEME GOVERNANCE & GUIDE GATEKEEPER AUTOMATED TEST SUITE")
    print("=" * 70)

    db = get_local_db()
    test_run_id = uuid.uuid4().hex[:6]
    
    # Setup test users
    admin_id = f"test-admin-{test_run_id}"
    guide_a_id = f"test-guide-a-{test_run_id}"
    guide_b_id = f"test-guide-b-{test_run_id}"
    aspirant_id = f"test-asp-{test_run_id}"

    db.upsert_profile({
        "id": admin_id,
        "email": f"admin_{test_run_id}@fulcrum.test",
        "role": "admin",
        "full_name": "Test Administrator"
    })
    db.upsert_profile({
        "id": guide_a_id,
        "email": f"guide_a_{test_run_id}@fulcrum.test",
        "role": "guide",
        "full_name": "Guide Alpha",
        "district": "Madurai"
    })
    db.upsert_profile({
        "id": guide_b_id,
        "email": f"guide_b_{test_run_id}@fulcrum.test",
        "role": "guide",
        "full_name": "Guide Beta",
        "district": "Chennai"
    })
    db.upsert_profile({
        "id": aspirant_id,
        "email": f"aspirant_{test_run_id}@fulcrum.test",
        "role": "aspirant",
        "full_name": "Test Entrepreneur",
        "district": "Madurai",
        "state": "Tamil Nadu",
        "profile_data": {
            "business": {
                "business_name": "Millet Delights Pvt Ltd",
                "sector": "Food Processing",
                "stage": "Pre-Seed / Seed",
                "revenue": "15,00,000"
            },
            "demographics": {
                "district": "Madurai",
                "founder_category": "OBC",
                "is_women_led": False
            }
        }
    })

    # Assign Guide A to Aspirant
    assign_guide(aspirant_id, guide_a_id, admin_id, "Test Mentorship Assignment")

    # Pick a scheme to test
    schemes = list_schemes(active_only=True)
    if not schemes:
        print("FAIL: No schemes available in catalogue to test.")
        return False
    test_scheme = schemes[0]
    test_scheme_id = test_scheme["id"]
    test_scheme_name = test_scheme["name"]
    print(f"Using Scheme for Tests: '{test_scheme_name}' (ID: {test_scheme_id})")

    results = {}

    # ─────────────────────────────────────────────────────────────
    # Scenario A: Aspirant Initially Sees 0 Released Schemes
    # ─────────────────────────────────────────────────────────────
    print("\n[Testing Scenario A: Aspirant Visibility Gate (Default Empty)]...")
    initial_releases = get_released_schemes_for_aspirant(aspirant_id)
    if len(initial_releases) == 0:
        print("  PASS: Aspirant initially retrieves 0 schemes (Master catalogue hidden).")
        results["Scenario A"] = "PASS"
    else:
        print(f"  FAIL: Aspirant unexpectedly retrieved {len(initial_releases)} schemes.")
        results["Scenario A"] = "FAIL"

    # ─────────────────────────────────────────────────────────────
    # Scenario B: Guide Evaluates Scheme for Aspirant
    # ─────────────────────────────────────────────────────────────
    print("\n[Testing Scenario B: Guide Evaluates Scheme with Private Intelligence]...")
    eval_result = evaluate_scheme_for_aspirant(aspirant_id, test_scheme_id)
    has_score = "match_score" in eval_result and isinstance(eval_result["match_score"], (int, float))
    has_reasons = "match_reasons" in eval_result and len(eval_result["match_reasons"]) > 0
    sch_data = eval_result.get("scheme", {})
    has_intel = "hidden_agenda" in sch_data or "red_flags" in sch_data
    if has_score and has_reasons and has_intel:
        print(f"  PASS: Evaluation succeeded. Score: {eval_result['match_score']}%, Reasons: {len(eval_result['match_reasons'])}, Intel accessible.")
        results["Scenario B"] = "PASS"
    else:
        print("  FAIL: Evaluation missing required components.")
        results["Scenario B"] = "FAIL"

    # ─────────────────────────────────────────────────────────────
    # Scenario C: Guide Releases Scheme to Assigned Aspirant
    # ─────────────────────────────────────────────────────────────
    print("\n[Testing Scenario C: Guide Releases Scheme to Aspirant]...")
    rec_note = "Strong alignment with food processing incentives in Madurai. Prepare DPR."
    rel_ok, rel_err = release_scheme_to_aspirant(
        guide_id=guide_a_id,
        aspirant_id=aspirant_id,
        scheme_id=test_scheme_id,
        guide_recommendation=rec_note,
        guide_note="Private check: confirm DPIIT registration."
    )
    if rel_ok:
        asp_releases = get_released_schemes_for_aspirant(aspirant_id)
        released_ids = [s["id"] for s in asp_releases]
        # Check journey event
        timeline = get_journey_timeline(aspirant_id)
        has_journey_event = any(e.get("event_type") == "scheme_released" for e in timeline)
        if test_scheme_id in released_ids and has_journey_event:
            print("  PASS: Scheme successfully released, visible to Aspirant, and Journey event logged.")
            results["Scenario C"] = "PASS"
        else:
            print(f"  FAIL: Release call succeeded but scheme not in Aspirant list or journey event missing.")
            results["Scenario C"] = "FAIL"
    else:
        print(f"  FAIL: Release failed with error: {rel_err}")
        results["Scenario C"] = "FAIL"

    # ─────────────────────────────────────────────────────────────
    # Scenario D: Unauthorized Guide Cannot Release Scheme
    # ─────────────────────────────────────────────────────────────
    print("\n[Testing Scenario D: Unauthorized Release Prevention]...")
    unauth_ok, unauth_err = release_scheme_to_aspirant(
        guide_id=guide_b_id, # Guide B is NOT assigned to Aspirant
        aspirant_id=aspirant_id,
        scheme_id=test_scheme_id,
        guide_recommendation="Unauthorized attempt"
    )
    if not unauth_ok and "not authorized" in str(unauth_err).lower():
        print(f"  PASS: Unauthorized release properly blocked with message: '{unauth_err}'")
        results["Scenario D"] = "PASS"
    else:
        print(f"  FAIL: Unauthorized release was allowed or wrong error: ok={unauth_ok}, err={unauth_err}")
        results["Scenario D"] = "FAIL"

    # ─────────────────────────────────────────────────────────────
    # Scenario E: Private Intelligence Stripped from Aspirant View
    # ─────────────────────────────────────────────────────────────
    print("\n[Testing Scenario E: Hidden Intelligence Protection for Aspirant]...")
    asp_schemes = get_released_schemes_for_aspirant(aspirant_id)
    target_rel = next((s for s in asp_schemes if s["id"] == test_scheme_id), None)
    if target_rel:
        agenda_clean = target_rel.get("hidden_agenda") == []
        flags_clean = target_rel.get("red_flags") == []
        prompt_clean = target_rel.get("application_prompt") == ""
        has_guide_note = bool(target_rel.get("guide_recommendation"))
        if agenda_clean and flags_clean and prompt_clean and has_guide_note:
            print("  PASS: Private intelligence strictly stripped (hidden_agenda=[], red_flags=[], prompt=''), recommendation note intact.")
            results["Scenario E"] = "PASS"
        else:
            print(f"  FAIL: Intelligence leakage detected: agenda={target_rel.get('hidden_agenda')}, flags={target_rel.get('red_flags')}")
            results["Scenario E"] = "FAIL"
    else:
        print("  FAIL: Released scheme not found in Aspirant payload.")
        results["Scenario E"] = "FAIL"

    # ─────────────────────────────────────────────────────────────
    # Scenario F: Guide Withdraws Released Scheme
    # ─────────────────────────────────────────────────────────────
    print("\n[Testing Scenario F: Guide Withdraws Release]...")
    withd_ok, withd_err = withdraw_scheme_release(guide_a_id, aspirant_id, test_scheme_id)
    if withd_ok:
        asp_schemes_after = get_released_schemes_for_aspirant(aspirant_id)
        still_present = any(s["id"] == test_scheme_id for s in asp_schemes_after)
        timeline = get_journey_timeline(aspirant_id)
        has_withd_event = any(e.get("event_type") == "scheme_release_withdrawn" for e in timeline)
        if not still_present and has_withd_event:
            print("  PASS: Release successfully withdrawn, scheme removed from Aspirant view, Journey event logged.")
            results["Scenario F"] = "PASS"
        else:
            print(f"  FAIL: Scheme still visible after withdrawal ({still_present}) or journey event missing ({has_withd_event}).")
            results["Scenario F"] = "FAIL"
    else:
        print(f"  FAIL: Withdrawal failed: {withd_err}")
        results["Scenario F"] = "FAIL"

    # ─────────────────────────────────────────────────────────────
    # Scenario G: Help Request Routes to Assigned Guide
    # ─────────────────────────────────────────────────────────────
    print("\n[Testing Scenario G: Help Request Guide Routing]...")
    req, req_err = create_request(
        aspirant_id=aspirant_id,
        subject="Query about Subsidy Quotations",
        message="Need assistance understanding quotation requirements for equipment.",
        priority="HIGH"
    )
    if req:
        # Check assigned_guide_id
        if req.get("assigned_guide_id") == guide_a_id:
            guide_requests = list_guide_requests(guide_a_id)
            req_in_guide_queue = any(r["id"] == req["id"] for r in guide_requests)
            if req_in_guide_queue:
                print(f"  PASS: Help ticket assigned to Guide {guide_a_id} and appears in Guide queue.")
                results["Scenario G"] = "PASS"
            else:
                print("  FAIL: Ticket assigned to guide but missing from list_guide_requests.")
                results["Scenario G"] = "FAIL"
        else:
            print(f"  FAIL: Ticket assigned_guide_id is '{req.get('assigned_guide_id')}', expected '{guide_a_id}'.")
            results["Scenario G"] = "FAIL"
    else:
        print(f"  FAIL: Failed to create request: {req_err}")
        results["Scenario G"] = "FAIL"

    # ─────────────────────────────────────────────────────────────
    # Scenario H: 7-Day Auto Escalation
    # ─────────────────────────────────────────────────────────────
    print("\n[Testing Scenario H: 7-Day Auto-Escalation to Admin]...")
    # Directly insert an overdue ticket created 8 days ago
    conn = db._get_conn()
    cur = conn.cursor()
    overdue_ticket_id = f"test-ticket-overdue-{test_run_id}"
    eight_days_ago = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    cur.execute("""
        INSERT INTO help_requests (id, aspirant_id, subject, message, priority, status, assigned_guide_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        overdue_ticket_id,
        aspirant_id,
        "Overdue Support Ticket (>7 Days)",
        "This ticket has been pending for over 7 days without resolution.",
        "URGENT",
        "OPEN",
        guide_a_id,
        eight_days_ago,
        eight_days_ago
    ))
    conn.commit()
    conn.close()

    # Trigger escalation job
    escalated_count = check_and_escalate_overdue_requests()
    print(f"  Escalation check completed. Tickets escalated: {escalated_count}")

    # Inspect the ticket status
    conn = db._get_conn()
    cur = conn.cursor()
    cur.execute("SELECT status, escalated_at, escalation_reason FROM help_requests WHERE id = ?", (overdue_ticket_id,))
    ticket_row = cur.fetchone()
    conn.close()

    if ticket_row:
        t_status, esc_at, esc_reason = ticket_row
        if t_status == "ESCALATED" and esc_at is not None:
            print(f"  PASS: Ticket successfully escalated to 'ESCALATED'. Escalated at: {esc_at}, Reason: '{esc_reason}'")
            results["Scenario H"] = "PASS"
        else:
            print(f"  FAIL: Ticket status is '{t_status}', escalated_at={esc_at}")
            results["Scenario H"] = "FAIL"
    else:
        print("  FAIL: Overdue ticket not found.")
        results["Scenario H"] = "FAIL"

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUITE SUMMARY:")
    all_passed = True
    for sc, res in results.items():
        print(f"  {sc}: {res}")
        if res != "PASS":
            all_passed = False
    print("=" * 70)
    if all_passed:
        print("ALL 8 SCENARIOS PASSED WITH 100% SUCCESS!")
    else:
        print("SOME TESTS FAILED.")
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
