"""
Comprehensive Authorization Verification for Journey Roadmap Toggle
===================================================================
Tests that only the authenticated entrepreneur (aspirant) owning the
journey event can toggle 'Needed' / 'Not Needed' (included_in_roadmap).

Tests:
  1. Legitimate Aspirant toggling own event -> PASS
  2. Rogue Aspirant (B) trying to toggle Aspirant (A)'s event -> REJECT
  3. Guide trying to toggle Aspirant's event -> REJECT
  4. SME trying to toggle Aspirant's event -> REJECT
  5. Admin trying to toggle Aspirant's event -> REJECT
  6. Mismatched aspirant_id parameter vs DB record -> REJECT
  7. Session-state based protection (active Guide session cannot toggle) -> REJECT
  8. Session-state based protection (active Aspirant session can toggle) -> PASS
"""

import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATA_BACKEND", "sqlite")

import streamlit as st
from services.local_db import get_local_db
from services.journey import (
    get_journey_timeline,
    add_guide_contribution,
    toggle_event_roadmap_inclusion
)

db = get_local_db()
conn = db._get_conn()
cur = conn.cursor()

# ── Setup test identities ─────────────────────────────────────────
asp_a = f"test-asp-a-{uuid.uuid4().hex[:8]}"
asp_b = f"test-asp-b-{uuid.uuid4().hex[:8]}"
guide_id = f"test-guide-{uuid.uuid4().hex[:8]}"
sme_id = f"test-sme-{uuid.uuid4().hex[:8]}"
admin_id = f"test-admin-{uuid.uuid4().hex[:8]}"

for uid, role, name in [
    (asp_a, "aspirant", "Entrepreneur Alpha"),
    (asp_b, "aspirant", "Entrepreneur Beta"),
    (guide_id, "guide", "Assigned Guide"),
    (sme_id, "sme", "Assigned SME"),
    (admin_id, "admin", "System Administrator"),
]:
    cur.execute("""
        INSERT OR IGNORE INTO profiles (id, role, full_name, email, phone)
        VALUES (?, ?, ?, ?, ?)
    """, (uid, role, name, f"{uid}@test.com", "9999999999"))

# Create journey for asp_a
j_id = str(uuid.uuid4())
cur.execute("""
    INSERT OR IGNORE INTO journeys (id, aspirant_id, title, status)
    VALUES (?, ?, 'Alpha Journey', 'active')
""", (j_id, asp_a))
conn.commit()
conn.close()

results = []

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((name, condition))
    print(f"  {status}: {name}" + (f" -- {detail}" if detail else ""))

print("\n=== STEP 1: Guide adds a mentorship contribution to Aspirant A's Journey ===")
ev, err = add_guide_contribution(
    aspirant_id=asp_a,
    guide_id=guide_id,
    title="Apply for Udyam & GST",
    description="Guidance on setting up MSME registration",
    topic="Statutory Setup"
)
check("Contribution created", ev is not None, f"err={err}")
event_id = ev["id"]

# Verify initial default
tl = get_journey_timeline(asp_a)
matching = [e for e in tl if e["id"] == event_id]
check("Default inclusion is True", len(matching) == 1 and matching[0]["included_in_roadmap"] is True)

# Clear any session state
if hasattr(st, "session_state"):
    st.session_state.clear()

# ── TEST 1: Legitimate Aspirant (A) marks Not Needed ─────────────
print("\n=== TEST 1: Legitimate Aspirant (A) toggles own event ===")
ok1, err1 = toggle_event_roadmap_inclusion(
    event_id=event_id,
    aspirant_id=asp_a,
    included=False,
    actor_id=asp_a,
    actor_role="aspirant"
)
check("Aspirant A can mark Not Needed", ok1 is True and err1 is None, f"err={err1}")

tl_after = get_journey_timeline(asp_a)
matching_after = [e for e in tl_after if e["id"] == event_id]
check("Event updated to included_in_roadmap=False", matching_after[0]["included_in_roadmap"] is False)

# ── TEST 2: Rogue Aspirant (B) tries to toggle Aspirant (A)'s event ──
print("\n=== TEST 2: Rogue Aspirant (B) tries to toggle Aspirant (A)'s event ===")
ok2, err2 = toggle_event_roadmap_inclusion(
    event_id=event_id,
    aspirant_id=asp_a,
    included=True,
    actor_id=asp_b,
    actor_role="aspirant"
)
check("Rogue Aspirant B is BLOCKED", ok2 is False, f"err={err2}")
check("Error message indicates unauthorized journey access", "only alter roadmap inclusion for your own journey" in (err2 or "").lower())

# Verify status did NOT change
tl_check = get_journey_timeline(asp_a)
check("Status remains False (unmodified)", [e for e in tl_check if e["id"] == event_id][0]["included_in_roadmap"] is False)

# ── TEST 3: Guide tries to toggle Aspirant's event ─────────────────
print("\n=== TEST 3: Guide tries to toggle Aspirant's event ===")
ok3, err3 = toggle_event_roadmap_inclusion(
    event_id=event_id,
    aspirant_id=asp_a,
    included=True,
    actor_id=guide_id,
    actor_role="guide"
)
check("Guide is BLOCKED from toggling founder's roadmap", ok3 is False, f"err={err3}")
check("Error message indicates role restriction", "cannot alter" in (err3 or "").lower())

# ── TEST 4: SME tries to toggle Aspirant's event ───────────────────
print("\n=== TEST 4: SME tries to toggle Aspirant's event ===")
ok4, err4 = toggle_event_roadmap_inclusion(
    event_id=event_id,
    aspirant_id=asp_a,
    included=True,
    actor_id=sme_id,
    actor_role="sme"
)
check("SME is BLOCKED from toggling founder's roadmap", ok4 is False, f"err={err4}")
check("Error message indicates role restriction", "cannot alter" in (err4 or "").lower())

# ── TEST 5: Admin tries to toggle Aspirant's event ─────────────────
print("\n=== TEST 5: Admin tries to toggle Aspirant's event ===")
ok5, err5 = toggle_event_roadmap_inclusion(
    event_id=event_id,
    aspirant_id=asp_a,
    included=True,
    actor_id=admin_id,
    actor_role="admin"
)
check("Admin is BLOCKED from toggling founder's roadmap", ok5 is False, f"err={err5}")
check("Error message indicates role restriction", "cannot alter" in (err5 or "").lower())

# ── TEST 6: Mismatched aspirant_id parameter vs DB record ─────────
print("\n=== TEST 6: Mismatched aspirant_id parameter ===")
ok6, err6 = toggle_event_roadmap_inclusion(
    event_id=event_id,
    aspirant_id=asp_b,  # Passing wrong aspirant for this event
    included=True,
    actor_id=asp_b,
    actor_role="aspirant"
)
check("Mismatched aspirant_id parameter is BLOCKED", ok6 is False, f"err={err6}")
check("Error message indicates event ownership mismatch", "does not belong" in (err6 or "").lower())

# ── TEST 7: Session-state based protection (Guide logged in) ─────
print("\n=== TEST 7: Streamlit session has Guide logged in ===")
st.session_state.user_id = guide_id
st.session_state.role = "guide"
st.session_state.user = {"id": guide_id, "role": "guide"}

ok7, err7 = toggle_event_roadmap_inclusion(
    event_id=event_id,
    aspirant_id=asp_a,
    included=True
    # actor_id and actor_role not supplied -> resolves from session_state
)
check("Guide in session_state is BLOCKED automatically", ok7 is False, f"err={err7}")
check("Session-based role restriction enforced", "cannot alter" in (err7 or "").lower())

# ── TEST 8: Session-state based protection (Aspirant A logged in) ──
print("\n=== TEST 8: Streamlit session has Aspirant A logged in ===")
st.session_state.user_id = asp_a
st.session_state.role = "aspirant"
st.session_state.user = {"id": asp_a, "role": "aspirant"}

ok8, err8 = toggle_event_roadmap_inclusion(
    event_id=event_id,
    aspirant_id=asp_a,
    included=True
    # actor_id and actor_role not supplied -> resolves from session_state
)
check("Aspirant A in session_state can re-include (Needed)", ok8 is True and err8 is None, f"err={err8}")
tl_final = get_journey_timeline(asp_a)
check("Event reinstated to included_in_roadmap=True", [e for e in tl_final if e["id"] == event_id][0]["included_in_roadmap"] is True)

# ── CLEANUP ───────────────────────────────────────────────────────
print("\n=== Cleanup ===")
conn_c = db._get_conn()
cur_c = conn_c.cursor()
cur_c.execute("DELETE FROM journey_events WHERE id = ?", (event_id,))
cur_c.execute("DELETE FROM journeys WHERE aspirant_id = ?", (asp_a,))
cur_c.execute("DELETE FROM profiles WHERE id IN (?, ?, ?, ?, ?)", (asp_a, asp_b, guide_id, sme_id, admin_id))
conn_c.commit()
conn_c.close()
print("  Test data cleaned up.")

# ── SUMMARY ───────────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
print(f"  TOTAL: {len(results)} checks  |  {passed} passed  |  {failed} failed")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
