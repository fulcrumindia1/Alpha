import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.auth import get_supabase_admin_client, get_data_backend
from services.local_db import get_local_db
from services.help_requests import create_request, guide_respond_request, list_requests
from services.journey import get_journey_timeline

print("Active Backend:", get_data_backend())

# Look up test aspirant Ravi Kumar
admin_client = get_supabase_admin_client()
res = admin_client.table("profiles").select("id").eq("email", "ravi.kumar@milletfoods.in").execute()
assert res.data, "Ravi Kumar profile not found"
asp_id = res.data[0]["id"]

# Count journey events before consultation request
timeline_before = get_journey_timeline(asp_id)
count_before = len(timeline_before)
print(f"Journey timeline count before consultation request: {count_before}")

# Create a consultation request
req, err = create_request(
    aspirant_id=asp_id,
    subject="FSSAI Labelling Consultation Test",
    message="Need advice on nutritional panel requirements for export packs.",
    priority="MEDIUM",
    category="FSSAI_FOOD",
    target_role="sme"
)
assert req is not None, f"Failed to create consultation request: {err}"
print(f"Created consultation request: ID={req['id']}")

# Count journey events immediately after consultation request
timeline_after = get_journey_timeline(asp_id)
count_after = len(timeline_after)
print(f"Journey timeline count after consultation request: {count_after}")
assert count_after == count_before, f"CRITICAL: Consultation request created a journey event! (Before: {count_before}, After: {count_after})"

# Check that the request is in the consultation queue
my_consultations = list_requests(aspirant_id=asp_id)
found = any(c["id"] == req["id"] for c in my_consultations)
assert found, "Consultation request missing from consultation queue!"
print("Verified: Consultation exists in consultation queue, but NOT in journey timeline!")

# Clean up test consultation request
if admin_client:
    admin_client.table("help_requests").delete().eq("id", req["id"]).execute()
    print("Cleaned up test consultation request.")

print("\n>>> ALL CONSULTATION ISOLATION CHECKS PASSED! <<<")
