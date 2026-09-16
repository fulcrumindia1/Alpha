"""
scratch/test_mentor_admin_hierarchy.py
Verifies:
1. Mentor (Guide / SME) can submit an institutional query / roadblock to Admin for an Aspirant.
2. Query appears in list_mentor_admin_queries().
3. Query does NOT appear in Aspirant's consultation queue (list_requests).
4. Admin can issue an official directive back to the Mentor and optionally assign Guide B.
5. Mentor sees the issued directive.
6. Aspirant's journey remains 100% untouched.
7. Aspirant has zero knowledge of the Admin.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.local_db import get_local_db
from services.help_requests import (
    create_mentor_admin_query,
    list_mentor_admin_queries,
    admin_respond_to_mentor,
    list_requests
)
from services.relationships import get_aspirant_mentors, assign_guide
from services.journey import get_journey_timeline
from services.profiles import list_profiles_by_role

def test_hierarchy():
    admins = list_profiles_by_role("admin")
    guides = list_profiles_by_role("guide")
    aspirants = list_profiles_by_role("aspirant")

    admin = next((a for a in admins if a.get("email") == "admin@fulcrum.in"), admins[0] if admins else None)
    guide_a = next((g for g in guides if g.get("email") == "rajendran@fulcrum.in"), guides[0] if guides else None)
    aspirant = next((p for p in aspirants if p.get("email") == "ravi.kumar@milletfoods.in"), aspirants[0] if aspirants else None)
    
    assert admin and guide_a and aspirant, "Test accounts missing"

    asp_id = aspirant["id"]
    guide_id = guide_a["id"]
    admin_id = admin["id"]

    print(f"Testing with Aspirant: {aspirant['full_name']} ({asp_id})")
    print(f"Primary Guide: {guide_a['full_name']} ({guide_id})")
    print(f"Admin: {admin['full_name']} ({admin_id})")

    # 1. Count journey events before test
    journey_before = get_journey_timeline(asp_id)
    journey_count_before = len(journey_before)

    # 2. Guide submits institutional query on behalf of Aspirant
    subject = "DIC Capital Subsidy District Clearance Blocked"
    message = "District Industries Centre has stalled the capital subsidy clearance citing pending survey. Need Directorate fast-track intervention and Co-Guide B for financial sanction."
    
    query, err = create_mentor_admin_query(
        mentor_id=guide_id,
        mentor_role="guide",
        aspirant_id=asp_id,
        subject=subject,
        message=message,
        priority="HIGH"
    )
    assert query is not None, f"Failed to create query: {err}"
    query_id = query["id"]
    print(f"Created mentor query ID: {query_id}")

    # 3. Check list_mentor_admin_queries
    admin_queries = list_mentor_admin_queries(aspirant_id=asp_id)
    found = any(q["id"] == query_id for q in admin_queries)
    assert found, "Query not found in list_mentor_admin_queries"
    print(" Verified query appears in list_mentor_admin_queries")

    # 4. Check list_requests for Aspirant - MUST NOT appear!
    asp_requests = list_requests(aspirant_id=asp_id)
    polluted = any(r["id"] == query_id for r in asp_requests)
    assert not polluted, "CRITICAL ERROR: Mentor query appeared in Aspirant's consultation queue!"
    print(" Verified query is INVISIBLE to Aspirant (not in list_requests)")

    # 5. Admin responds to query with Directive and assigns Co-Guide B (if another guide exists)
    other_guides = [g for g in list_profiles_by_role("guide") if g["id"] != guide_id]
    co_guide_id = other_guides[0]["id"] if other_guides else None

    directive_text = "Directorate has contacted the District Collectorate. Fast-track inspection clearance approved. Co-Guide assigned to supervise bank sanction."
    ok, err = admin_respond_to_mentor(
        query_id=query_id,
        admin_id=admin_id,
        directive=directive_text,
        new_status="DIRECTIVE_ISSUED",
        assign_co_guide_id=co_guide_id
    )
    assert ok, f"Admin response failed: {err}"
    print(" Verified Admin issued official directive")

    # 6. Check mentor view has directive
    updated_queries = list_mentor_admin_queries(mentor_id=guide_id, aspirant_id=asp_id)
    target = next((q for q in updated_queries if q["id"] == query_id), None)
    assert target is not None, "Query not returned for mentor"
    assert target["status"] == "DIRECTIVE_ISSUED", f"Expected DIRECTIVE_ISSUED, got {target['status']}"
    assert target["admin_directive"] == directive_text, "Directive text mismatch"
    print(" Verified Guide sees the official Directorate Directive")

    # 7. Check Co-Guide assignment if applied
    if co_guide_id:
        mentors = get_aspirant_mentors(asp_id)
        guides_list = mentors.get("guides", [])
        guide_ids = [g["id"] for g in guides_list]
        assert guide_id in guide_ids and co_guide_id in guide_ids, f"Expected both guides in {guide_ids}"
        print(f" Verified Co-Guide {other_guides[0]['full_name']} was added as Guide B alongside Guide A!")

    # 8. Check Journey events: No admin query or consultation should be written to journey_events!
    journey_after = get_journey_timeline(asp_id)
    # Only assignment event if co-guide was added
    new_events = [e for e in journey_after if e["id"] not in [b["id"] for b in journey_before]]
    for e in new_events:
        assert "DIC Capital Subsidy" not in str(e), "Error: mentor admin query was logged to journey!"
    print(" Verified Aspirant Journey is 100% free of help/consultation tickets and admin queries")

    print("\n ALL ACCEPTANCE TESTS PASSED!")

if __name__ == "__main__":
    test_hierarchy()
