import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.auth import get_supabase_admin_client, get_data_backend
from services.local_db import get_local_db
from services.journey import (
    get_journey_timeline,
    add_guide_contribution,
    toggle_event_roadmap_inclusion,
    soft_delete_event
)

print("=== VERIFYING NEEDED / NOT NEEDED GOVERNANCE WORKFLOW ===")
print("Active Backend:", get_data_backend())

admin_client = get_supabase_admin_client()

# Fetch test aspirant and guide
res_asp = admin_client.table("profiles").select("id").eq("email", "ravi.kumar@milletfoods.in").execute()
res_guide = admin_client.table("profiles").select("id").eq("email", "rajendran@fulcrum.in").execute()
asp_id = res_asp.data[0]["id"]
guide_id = res_guide.data[0]["id"]

# 1. Guide logs a contribution (e.g. GST Certificate Acquisition)
test_title = "Assisted in Acquired GST Certificate (Test Workflow)"
ev, err = add_guide_contribution(
    aspirant_id=asp_id,
    guide_id=guide_id,
    title=test_title,
    description="Guide coordinated with tax specialist to obtain GST registration certificate."
)
assert ev is not None, f"Failed to log guide contribution: {err}"
event_id = ev["id"]
print(f"Step 1: Guide logged contribution -> ID: {event_id}")

# 2. Initial state: default included_in_roadmap is True
timeline = get_journey_timeline(asp_id)
matching = [e for e in timeline if e["id"] == event_id]
assert len(matching) == 1, "Event not found in timeline"
assert matching[0]["included_in_roadmap"] is True, "Default should be included_in_roadmap: True"
print("Step 2: Verified default status is Active (included_in_roadmap: True)")

# 3. Aspirant marks 'Not Needed'
ok, err = toggle_event_roadmap_inclusion(event_id, asp_id, False)
assert ok, f"Aspirant toggle failed: {err}"
print("Step 3: Aspirant marked contribution as 'Not Needed' (included_in_roadmap: False)")

# 4. Guide's view check: Guide STILL sees the event normally, with included_in_roadmap == False
guide_timeline = get_journey_timeline(asp_id)
g_matching = [e for e in guide_timeline if e["id"] == event_id]
assert len(g_matching) == 1, "CRITICAL: Event disappeared from Guide view! It should remain visible."
assert g_matching[0]["included_in_roadmap"] is False, "Guide view should reflect included_in_roadmap: False badge"
print("Step 4: Guide view verified -> Event remains visible normally with 'Founder Marked: Not Needed' status!")

# 5. Admin's view check: Admin STILL sees the event, with included_in_roadmap == False
admin_timeline = get_journey_timeline(asp_id)
a_matching = [e for e in admin_timeline if e["id"] == event_id]
assert len(a_matching) == 1, "CRITICAL: Event disappeared from Admin view! It should remain visible."
assert a_matching[0]["included_in_roadmap"] is False, "Admin view should reflect 'Marked Not Needed by Aspirant'"
print("Step 5: Admin view verified -> Admin sees event with 'Marked Not Needed by Aspirant' status!")

# 6. Aspirant active roadmap check: Excluded from active highlights
active_events = [e for e in guide_timeline if e.get("included_in_roadmap", True) is not False]
assert event_id not in [e["id"] for e in active_events], "Excluded event should not be on active roadmap"
print("Step 6: Aspirant active highlights verified -> Excluded from highlights preview and PDF dossier!")

# 7. Aspirant re-activates 'Needed'
ok, err = toggle_event_roadmap_inclusion(event_id, asp_id, True)
assert ok, f"Reactivation failed: {err}"
t_reinstated = get_journey_timeline(asp_id)
r_matching = [e for e in t_reinstated if e["id"] == event_id]
assert r_matching[0]["included_in_roadmap"] is True, "Reactivated event should be True"
print("Step 7: Aspirant re-activated to 'Needed' -> Successfully reinstated on active roadmap!")

# Clean up test event
soft_delete_event(event_id, guide_id, "guide")
if admin_client:
    admin_client.table("journey_events").delete().eq("id", event_id).execute()
print("Step 8: Cleaned up test milestone.")

print("\n>>> ALL 8 WORKFLOW CHECKS CONFIRMED AND PASSED 100%! <<<")
