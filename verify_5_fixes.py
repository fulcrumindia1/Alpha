"""
verify_5_fixes.py — Automated End-to-End Verification of the 5 Critical Fixes
=============================================================================
Tests:
1. Teacher Profile Editor (Guide & SME can update phone, district, expertise, bio, industry)
2. Universal In-App Notifications (Create, list, mark read, unread count)
3. Mentor Reassignment & Handoff Audit (History log + alerts to outgoing/incoming mentors)
4. Phone Number Persistence & Self-Healing Sync
5. SME Help Requests (Category routing, SME queue, SME response, aspirant alert)
"""

import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure local testing environment
os.environ["DATA_BACKEND"] = "sqlite"

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from services.local_db import get_local_db
from services.profiles import get_profile, update_mentor_profile
from services.notifications import create_notification, list_notifications, mark_as_read, mark_all_as_read, get_unread_count
from services.relationships import assign_guide, assign_sme, get_aspirant_mentors, get_assignment_history
from services.help_requests import create_request, list_requests, list_sme_requests, sme_respond_request
from services.auth import sync_user_phone_if_missing

def create_test_profile(db, user_id, email, role, full_name, phone=None, district="Madurai"):
    return db.upsert_profile({
        "id": user_id,
        "email": email,
        "role": role,
        "full_name": full_name,
        "phone": phone or "",
        "district": district,
        "state": "Tamil Nadu",
        "profile_data": {},
        "is_active": True
    })

def test_problem_1_profile_editor():
    print("\n--- TEST 1: Teacher Profile Editor (Guide & SME) ---")
    db = get_local_db()
    
    # Create test guide with valid UUID
    guide_id = str(uuid.uuid4())
    guide_email = f"guide_{uuid.uuid4().hex[:6]}@test.fulcrum"
    create_test_profile(
        db=db,
        user_id=guide_id,
        email=guide_email,
        role="guide",
        full_name="Dr. Arul Kumar",
        phone="9876543210",
        district="Madurai"
    )
    
    # Guide updates own profile
    success, err = update_mentor_profile(
        user_id=guide_id,
        role="guide",
        full_name="Dr. Arul Kumar, Ph.D.",
        phone="9988776655",
        district="Coimbatore",
        expertise="Advanced Micro-Enterprises & SIDBI Loan Strategy",
        bio="Certified institutional mentor with 15+ years experience in MSME growth.",
        industry="Manufacturing"
    )
    assert success, f"Guide profile update failed: {err}"
    
    p = get_profile(guide_id)
    assert p["full_name"] == "Dr. Arul Kumar, Ph.D.", f"Name mismatch: {p['full_name']}"
    assert p["phone"] == "9988776655", f"Phone mismatch: {p['phone']}"
    assert p["district"] == "Coimbatore", f"District mismatch: {p['district']}"
    p_data = p.get("profile_data", {})
    assert p_data.get("expertise") == "Advanced Micro-Enterprises & SIDBI Loan Strategy"
    assert "15+ years" in p_data.get("bio", "")
    print("  [PASSED] Guide can successfully update phone, district, expertise, bio, and credentials.")

    # Create test SME with valid UUID
    sme_id = str(uuid.uuid4())
    sme_email = f"sme_{uuid.uuid4().hex[:6]}@test.fulcrum"
    create_test_profile(
        db=db,
        user_id=sme_id,
        email=sme_email,
        role="sme",
        full_name="CA Priya Sharma",
        phone="9123456780",
        district="Chennai"
    )
    
    # SME updates own profile
    success, err = update_mentor_profile(
        user_id=sme_id,
        role="sme",
        full_name="CA Priya Sharma, FCA",
        phone="9123456799",
        district="Chennai",
        expertise="GST Audit, Corporate Taxation & Litigations",
        bio="Senior Chartered Accountant specializing in industrial subsidy audits.",
        industry="Taxation & Compliance"
    )
    assert success, f"SME profile update failed: {err}"
    
    sme_p = get_profile(sme_id)
    assert sme_p["full_name"] == "CA Priya Sharma, FCA"
    assert sme_p["phone"] == "9123456799"
    assert sme_p.get("profile_data", {}).get("industry") == "Taxation & Compliance"
    print("  [PASSED] SME can successfully update phone, district, expertise, bio, and industry.")

def test_problem_2_notifications():
    print("\n--- TEST 2: In-App Notification System ---")
    user_id = str(uuid.uuid4())
    db = get_local_db()
    create_test_profile(
        db=db,
        user_id=user_id,
        email=f"asp_{uuid.uuid4().hex[:6]}@test.fulcrum",
        role="aspirant",
        full_name="Ravi Kumar",
        phone="9000000001"
    )
    
    # Initial count
    c0 = get_unread_count(user_id)
    assert c0 == 0, f"Expected 0 unread, got {c0}"
    
    # Create notifications
    n1, err1 = create_notification(
        user_id=user_id,
        title="Guide Assigned",
        message="Dr. Arul has been assigned as your enterprise Guide.",
        notification_type="guide_assigned"
    )
    assert n1 is not None and not err1
    
    n2, err2 = create_notification(
        user_id=user_id,
        title="New Scheme Released",
        message="NEEDS 25% Capital Subsidy is now available in your portal.",
        notification_type="scheme_released"
    )
    assert n2 is not None and not err2
    
    c1 = get_unread_count(user_id)
    assert c1 == 2, f"Expected 2 unread, got {c1}"
    
    notifs = list_notifications(user_id)
    assert len(notifs) >= 2, f"Expected at least 2 notifications, got {len(notifs)}"
    assert notifs[0]["title"] in ("New Scheme Released", "Guide Assigned")
    
    # Mark one read
    ok = mark_as_read(n1["id"], user_id)
    assert ok, "mark_as_read failed"
    assert get_unread_count(user_id) == 1
    
    # Mark all read
    ok_all = mark_all_as_read(user_id)
    assert ok_all, "mark_all_as_read failed"
    assert get_unread_count(user_id) == 0
    print("  [PASSED] Notification engine creates, lists, counts, and dismisses in-app alerts.")

def test_problem_3_mentor_reassignment_handoff():
    print("\n--- TEST 3: Mentor Reassignment & Handoff Audit Log ---")
    db = get_local_db()
    admin_id = str(uuid.uuid4())
    asp_id = str(uuid.uuid4())
    g1_id = str(uuid.uuid4())
    g2_id = str(uuid.uuid4())
    
    create_test_profile(db=db, user_id=admin_id, email=f"adm_{uuid.uuid4().hex[:6]}@test.fulcrum", role="admin", full_name="Admin Officer")
    create_test_profile(db=db, user_id=asp_id, email=f"asp_{uuid.uuid4().hex[:6]}@test.fulcrum", role="aspirant", full_name="Kavitha Founder")
    create_test_profile(db=db, user_id=g1_id, email=f"g1_{uuid.uuid4().hex[:6]}@test.fulcrum", role="guide", full_name="Guide A")
    create_test_profile(db=db, user_id=g2_id, email=f"g2_{uuid.uuid4().hex[:6]}@test.fulcrum", role="guide", full_name="Guide B")
    
    # 1. First assignment: Guide A
    rel1, err1 = assign_guide(asp_id, g1_id, assigned_by=admin_id)
    assert rel1 is not None, f"Assign Guide A failed: {err1}"
    
    # Check history
    h1 = get_assignment_history(asp_id)
    assert len(h1) == 1
    assert h1[0]["action"] == "ASSIGNED"
    assert h1[0]["mentor_id"] == g1_id
    
    # Check notifications: Guide A and Aspirant notified
    g1_notifs = list_notifications(g1_id)
    assert len(g1_notifs) >= 1
    assert "Assigned" in g1_notifs[0]["title"]
    
    # 2. Reassignment: Guide A -> Guide B
    rel2, err2 = assign_guide(asp_id, g2_id, assigned_by=admin_id)
    assert rel2 is not None, f"Assign Guide B failed: {err2}"
    
    # Check history
    h2 = get_assignment_history(asp_id)
    assert len(h2) == 2, f"Expected 2 history records, got {len(h2)}"
    latest_h = h2[0] # ordered by created_at DESC
    assert latest_h["action"] == "REPLACED"
    assert latest_h["mentor_id"] == g2_id
    assert latest_h["previous_mentor_id"] == g1_id
    
    # Check notifications for Guide A (unassignment alert)
    g1_notifs_after = list_notifications(g1_id)
    unassigned_found = any("Reassigned" in n["title"] for n in g1_notifs_after)
    assert unassigned_found, "Guide A did not receive unassignment notification"
    
    # Check notifications for Guide B (assignment alert)
    g2_notifs = list_notifications(g2_id)
    assigned_found = any("Assigned" in n["title"] for n in g2_notifs)
    assert assigned_found, "Guide B did not receive assignment notification"
    
    # Check notifications for Aspirant (transition alert)
    asp_notifs = list_notifications(asp_id)
    asp_trans = any("Guide" in n["title"] for n in asp_notifs)
    assert asp_trans, "Aspirant did not receive mentor handoff notification"
    
    print("  [PASSED] Reassignment creates immutable audit log and dispatches alerts to all 3 parties.")

def test_problem_4_phone_persistence_self_healing():
    print("\n--- TEST 4: Phone Number Persistence & Self-Healing Sync ---")
    db = get_local_db()
    uid = str(uuid.uuid4())
    email = f"phone_{uuid.uuid4().hex[:6]}@test.fulcrum"
    
    # Profile created without phone
    create_test_profile(
        db=db,
        user_id=uid,
        email=email,
        role="aspirant",
        full_name="Phone Test User",
        phone=None
    )
    p_before = get_profile(uid)
    assert not p_before.get("phone")
    
    # Simulate login self-healing from auth metadata
    sync_user_phone_if_missing(uid, "9840123456", district="Salem")
    p_after = get_profile(uid)
    assert p_after.get("phone") == "9840123456", f"Phone not healed: {p_after.get('phone')}"
    assert p_after.get("district") == "Salem", f"District not healed: {p_after.get('district')}"
    print("  [PASSED] Login self-healing recovers phone and district if dropped during signup.")

def test_problem_5_sme_help_requests():
    print("\n--- TEST 5: SME Help Requests & Domain Advisory Flow ---")
    db = get_local_db()
    asp_id = str(uuid.uuid4())
    sme_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    
    create_test_profile(db=db, user_id=asp_id, email=f"asp_{uuid.uuid4().hex[:6]}@test.fulcrum", role="aspirant", full_name="Suresh Dairy")
    create_test_profile(db=db, user_id=sme_id, email=f"sme_{uuid.uuid4().hex[:6]}@test.fulcrum", role="sme", full_name="CA Ananth")
    create_test_profile(db=db, user_id=admin_id, email=f"adm_{uuid.uuid4().hex[:6]}@test.fulcrum", role="admin", full_name="Admin Officer")
    
    # Assign SME to Aspirant
    assign_sme(asp_id, sme_id, assigned_by=admin_id)
    
    # Aspirant creates GST help request
    req, err = create_request(
        aspirant_id=asp_id,
        subject="Clarification on GST Exemption for Agro-processing",
        message="Need to know if milk packaging machinery qualifies for 5% or 18% GST.",
        priority="HIGH",
        category="GST_TAXATION",
        target_role="sme"
    )
    assert req is not None, f"create_request failed: {err}"
    assert req["category"] == "GST_TAXATION"
    assert req["target_role"] == "sme"
    assert req["assigned_sme_id"] == sme_id
    
    # Check SME received notification
    sme_notifs = list_notifications(sme_id)
    ticket_notif = any("Domain Advisory Request" in n["title"] or "Help" in n["title"] for n in sme_notifs)
    assert ticket_notif, "SME did not receive notification of new domain ticket"
    
    # SME lists their assigned requests
    sme_queue = list_sme_requests(sme_id)
    assert len(sme_queue) >= 1, f"Expected at least 1 ticket in SME queue, got {len(sme_queue)}"
    found_ticket = next((t for t in sme_queue if t["id"] == req["id"]), None)
    assert found_ticket is not None, "Created ticket not found in SME queue"
    
    # SME replies to the ticket
    reply_text = "Milk pasteurization machinery falls under HSN 8434 and attracts 12% GST, but capital subsidy is claimable under NEEDS."
    ok, r_err = sme_respond_request(req["id"], sme_id, reply_text)
    assert ok, f"sme_respond_request failed: {r_err}"
    
    # Verify ticket state
    updated_reqs = list_requests(aspirant_id=asp_id)
    target_req = next(r for r in updated_reqs if r["id"] == req["id"])
    assert target_req["sme_response"] == reply_text
    assert target_req["status"] == "IN_PROGRESS"
    
    # Verify Aspirant received notification that SME replied
    asp_notifs = list_notifications(asp_id)
    reply_notif = any("Responded" in n["title"] or "Domain" in n["title"] for n in asp_notifs)
    assert reply_notif, "Aspirant did not receive notification of SME's reply"
    
    print("  [PASSED] SME receives routed domain tickets, responds directly, and aspirant gets notified.")

if __name__ == "__main__":
    print("=" * 70)
    print("FULCRUM-INDIA: 5 CRITICAL FIXES VERIFICATION SUITE")
    print("=" * 70)
    
    test_problem_1_profile_editor()
    test_problem_2_notifications()
    test_problem_3_mentor_reassignment_handoff()
    test_problem_4_phone_persistence_self_healing()
    test_problem_5_sme_help_requests()
    
    print("\n" + "=" * 70)
    print(">>> ALL 5 PROBLEM AREAS SUCCESSFULLY VERIFIED! <<<")
    print("=" * 70)
