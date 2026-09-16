"""
E2E Verification: SME/Guide Consultation Routing & Queue Isolation
==================================================================
Tests the fix for the data-model discrepancy where SME tickets were
being routed into assigned_guide_id and responses written to guide_response.

Validates:
  1. Guide ticket -> assigned_guide_id populated, assigned_sme_id NULL
  2. SME ticket   -> assigned_sme_id populated, assigned_guide_id NULL
  3. Guide response persists in guide_response (not sme_response)
  4. SME response persists in sme_response (not guide_response)
  5. SME tickets do NOT appear in Guide queue
  6. Guide tickets do NOT appear in SME queue
  7. Domain-category auto-routing (FSSAI_FOOD -> sme)
"""

import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATA_BACKEND", "sqlite")

from services.local_db import get_local_db

db = get_local_db()
conn = db._get_conn()
cur = conn.cursor()

# ── Setup test users ──────────────────────────────────────────────
aspirant_id = f"test-asp-{uuid.uuid4().hex[:8]}"
guide_id    = f"test-guide-{uuid.uuid4().hex[:8]}"
sme_id      = f"test-sme-{uuid.uuid4().hex[:8]}"

for uid, role, name in [
    (aspirant_id, "aspirant", "Test Aspirant"),
    (guide_id, "guide", "Test Guide"),
    (sme_id, "sme", "Test SME"),
]:
    cur.execute("""
        INSERT OR IGNORE INTO profiles (id, role, full_name, email, phone)
        VALUES (?, ?, ?, ?, ?)
    """, (uid, role, name, f"{uid}@test.com", "0000000000"))

# Create relationship so create_request can auto-resolve mentors
cur.execute("""
    INSERT OR IGNORE INTO relationships (id, aspirant_id, guide_id, sme_id, status)
    VALUES (?, ?, ?, ?, 'active')
""", (str(uuid.uuid4()), aspirant_id, guide_id, sme_id))
conn.commit()
conn.close()

results = []

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((name, condition))
    print(f"  {status}: {name}" + (f" -- {detail}" if detail else ""))

# TEST 1: Guide Ticket Routing
print("\n=== TEST 1: Guide Ticket Creation & Routing ===")
from services.help_requests import create_request
guide_ticket, err1 = create_request(
    aspirant_id=aspirant_id,
    subject="Business registration help",
    message="I need help with Udyam registration",
    priority="MEDIUM",
    target_role="guide",
    category="GENERAL"
)
check("Guide ticket created", guide_ticket is not None and err1 is None, f"err={err1}")

gt_id = None
if guide_ticket:
    gt_id = guide_ticket.get("id") or guide_ticket.get("request_id")
    conn2 = db._get_conn()
    cur2 = conn2.cursor()
    cur2.execute("SELECT assigned_guide_id, assigned_sme_id, target_role, category FROM help_requests WHERE id = ?", (gt_id,))
    row = cur2.fetchone()
    conn2.close()
    if row:
        row = dict(row)
        check("Guide ticket: assigned_guide_id populated", row["assigned_guide_id"] == guide_id,
              f"expected={guide_id}, got={row['assigned_guide_id']}")
        check("Guide ticket: assigned_sme_id is NULL", row["assigned_sme_id"] is None,
              f"got={row['assigned_sme_id']}")
        check("Guide ticket: target_role='guide'", row["target_role"] == "guide",
              f"got={row['target_role']}")
    else:
        check("Guide ticket row found", False, "Row not found in DB")

# TEST 2: SME Ticket Routing
print("\n=== TEST 2: SME Ticket Creation & Routing ===")
sme_ticket, err2 = create_request(
    aspirant_id=aspirant_id,
    subject="GST registration query",
    message="What is the GST rate for food products?",
    priority="HIGH",
    target_role="sme",
    category="GST_TAXATION"
)
check("SME ticket created", sme_ticket is not None and err2 is None, f"err={err2}")

st_id = None
if sme_ticket:
    st_id = sme_ticket.get("id") or sme_ticket.get("request_id")
    conn3 = db._get_conn()
    cur3 = conn3.cursor()
    cur3.execute("SELECT assigned_guide_id, assigned_sme_id, target_role, category FROM help_requests WHERE id = ?", (st_id,))
    row2 = cur3.fetchone()
    conn3.close()
    if row2:
        row2 = dict(row2)
        check("SME ticket: assigned_sme_id populated", row2["assigned_sme_id"] == sme_id,
              f"expected={sme_id}, got={row2['assigned_sme_id']}")
        check("SME ticket: assigned_guide_id is NULL", row2["assigned_guide_id"] is None,
              f"got={row2['assigned_guide_id']}")
        check("SME ticket: target_role='sme'", row2["target_role"] == "sme",
              f"got={row2['target_role']}")
        check("SME ticket: category='GST_TAXATION'", row2["category"] == "GST_TAXATION",
              f"got={row2['category']}")
    else:
        check("SME ticket row found", False, "Row not found in DB")

# TEST 3: Queue Isolation
print("\n=== TEST 3: Queue Isolation (No Bleed) ===")
from services.help_requests import list_sme_requests

guide_queue = db.list_help_requests(guide_id=guide_id)
sme_queue = list_sme_requests(sme_id)

guide_queue_ids = [r.get("id") for r in guide_queue]
sme_queue_ids = [r.get("id") for r in sme_queue]

if gt_id and st_id:
    check("Guide queue contains guide ticket", gt_id in guide_queue_ids,
          f"guide_queue has {len(guide_queue)} items")
    check("Guide queue does NOT contain SME ticket", st_id not in guide_queue_ids,
          f"SME ticket {'FOUND' if st_id in guide_queue_ids else 'not found'} in guide queue")
    check("SME queue contains SME ticket", st_id in sme_queue_ids,
          f"sme_queue has {len(sme_queue)} items")
    check("SME queue does NOT contain Guide ticket", gt_id not in sme_queue_ids,
          f"Guide ticket {'FOUND' if gt_id in sme_queue_ids else 'not found'} in SME queue")

# TEST 4: Response Field Persistence
print("\n=== TEST 4: Response Field Persistence ===")
from services.help_requests import guide_respond_request, sme_respond_request

if gt_id:
    ok_g, err_g = guide_respond_request(gt_id, guide_id, "IN_PROGRESS", "I'll help you with Udyam registration.")
    check("Guide respond succeeded", ok_g, f"err={err_g}")

    conn4 = db._get_conn()
    cur4 = conn4.cursor()
    cur4.execute("SELECT guide_response, sme_response FROM help_requests WHERE id = ?", (gt_id,))
    row3 = cur4.fetchone()
    conn4.close()
    if row3:
        row3 = dict(row3)
        check("Guide response in guide_response field",
              row3["guide_response"] is not None and "Udyam" in row3["guide_response"],
              f"guide_response={row3['guide_response']}")
        check("sme_response is NULL for guide ticket", row3["sme_response"] is None,
              f"sme_response={row3['sme_response']}")

if st_id:
    ok_s, err_s = sme_respond_request(st_id, sme_id, "IN_PROGRESS", "GST rate for food is 5% under HSN 2106.")
    check("SME respond succeeded", ok_s, f"err={err_s}")

    conn5 = db._get_conn()
    cur5 = conn5.cursor()
    cur5.execute("SELECT guide_response, sme_response FROM help_requests WHERE id = ?", (st_id,))
    row4 = cur5.fetchone()
    conn5.close()
    if row4:
        row4 = dict(row4)
        check("SME response in sme_response field",
              row4["sme_response"] is not None and "GST" in row4["sme_response"],
              f"sme_response={row4['sme_response']}")
        check("guide_response is NULL for SME ticket", row4["guide_response"] is None,
              f"guide_response={row4['guide_response']}")

# TEST 5: Domain-Category Auto-Routing
print("\n=== TEST 5: Domain-Category Auto-Routing ===")
# FSSAI_FOOD category should auto-route to SME even if target_role says "guide"
auto_ticket, err_auto = create_request(
    aspirant_id=aspirant_id,
    subject="FSSAI license question",
    message="Do I need FSSAI for a cloud kitchen?",
    priority="MEDIUM",
    target_role="guide",       # Caller says guide...
    category="FSSAI_FOOD"      # ...but FSSAI_FOOD should auto-route to SME
)
check("Auto-routed ticket created", auto_ticket is not None and err_auto is None, f"err={err_auto}")

if auto_ticket:
    at_id = auto_ticket.get("id") or auto_ticket.get("request_id")
    conn6 = db._get_conn()
    cur6 = conn6.cursor()
    cur6.execute("SELECT assigned_guide_id, assigned_sme_id, target_role FROM help_requests WHERE id = ?", (at_id,))
    row5 = cur6.fetchone()
    conn6.close()
    if row5:
        row5 = dict(row5)
        check("FSSAI_FOOD auto-routed: target_role='sme'", row5["target_role"] == "sme",
              f"got={row5['target_role']}")
        check("FSSAI_FOOD auto-routed: assigned_sme_id populated", row5["assigned_sme_id"] == sme_id,
              f"got={row5['assigned_sme_id']}")
        check("FSSAI_FOOD auto-routed: assigned_guide_id is NULL", row5["assigned_guide_id"] is None,
              f"got={row5['assigned_guide_id']}")

# CLEANUP
print("\n=== Cleanup ===")
conn_cleanup = db._get_conn()
cur_cleanup = conn_cleanup.cursor()
cur_cleanup.execute("DELETE FROM help_requests WHERE aspirant_id = ?", (aspirant_id,))
cur_cleanup.execute("DELETE FROM relationships WHERE aspirant_id = ?", (aspirant_id,))
cur_cleanup.execute("DELETE FROM profiles WHERE id IN (?, ?, ?)", (aspirant_id, guide_id, sme_id))
conn_cleanup.commit()
conn_cleanup.close()
print("  Test data cleaned up.")

# SUMMARY
print("\n" + "=" * 60)
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
print(f"  TOTAL: {len(results)} tests  |  {passed} passed  |  {failed} failed")
if failed > 0:
    print("\n  Failed tests:")
    for name, ok in results:
        if not ok:
            print(f"    FAIL: {name}")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
