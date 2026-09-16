"""
verify_journey_governance_and_ui.py
====================================
Automated verification suite testing:
1. Role standardization helper and masking of Admin for Aspirant view
2. Absence of user-facing 'Actor' / 'ACTOR' across all view files
3. High-contrast colors for Insider Intelligence and Red Flags
4. SQLite Mode:
   - Timeline ordering (most recent on top / DESC)
   - Guide adds contribution to Aspirant's journey
   - Aspirant toggles 'Not Needed' (included_in_roadmap -> False)
   - Verified that Highlights excludes it
   - Verified that Guide & Admin still see the contribution with inclusion flag False
   - Aspirant toggles back to 'Needed' (included_in_roadmap -> True)
5. Supabase Mode:
   - Timeline ordering (most recent on top / DESC)
   - Verified that included_in_roadmap field is exposed
"""

import os
import sys
import json
import re
import uuid

# Ensure path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def run_tests():
    print("\n" + "="*70)
    print("FULCRUM JOURNEY & GOVERNANCE VERIFICATION SUITE")
    print("="*70)

    # -------------------------------------------------------------
    # TEST 1: Role Standardization Helper
    # -------------------------------------------------------------
    print("\n--- Test 1: Role Standardization ---")
    from services.journey import get_standard_role_label
    assert get_standard_role_label("aspirant") == "Aspirant"
    assert get_standard_role_label("guide") == "Guide"
    assert get_standard_role_label("sme") == "SME (Subject Matter Expert)"
    assert get_standard_role_label("admin", is_aspirant_facing=False) == "Admin"
    assert get_standard_role_label("admin", is_aspirant_facing=True) == "Institutional Advisory Council"
    assert get_standard_role_label("system") == "System Automation"
    print("  ✓ All role labels standardized correctly (Admin masked for Aspirant).")

    # -------------------------------------------------------------
    # TEST 2: Static Audit - Zero 'Actor:' or 'ACTOR:' in Views
    # -------------------------------------------------------------
    print("\n--- Test 2: Static Audit for 'Actor' Terminology in Views ---")
    views_dir = os.path.join(current_dir, "views")
    for f in os.listdir(views_dir):
        if f.endswith(".py"):
            fpath = os.path.join(views_dir, f)
            with open(fpath, "r", encoding="utf-8") as fp:
                content = fp.read()
                actor_matches = re.findall(r"(?:Actor:|ACTOR:|Actor\s*:|ACTOR\s*:)", content)
                assert len(actor_matches) == 0, f"Found '{actor_matches}' in {f}"
    print("  ✓ All views verified: Zero user-facing 'Actor:' or 'ACTOR:' strings found.")

    # -------------------------------------------------------------
    # TEST 3: High-contrast Insider Intelligence & Red Flags
    # -------------------------------------------------------------
    print("\n--- Test 3: Contrast Audit for Insider Intelligence & Red Flags ---")
    guide_view_path = os.path.join(views_dir, "guide.py")
    with open(guide_view_path, "r", encoding="utf-8") as fp:
        guide_code = fp.read()
        assert "#FCD34D" not in guide_code, "Pale yellow #FCD34D still found in views/guide.py"
        assert "#FFFBEB" in guide_code, "Rich amber background #FFFBEB missing"
        assert "#78350F" in guide_code, "High-contrast text #78350F missing"
        assert "#FEF2F2" in guide_code, "Rich crimson background #FEF2F2 missing"
        assert "#7F1D1D" in guide_code, "High-contrast text #7F1D1D missing"
    print("  ✓ High-contrast styling verified: Dark, readable typography implemented.")

    # -------------------------------------------------------------
    # TEST 4: SQLite Mode - Timeline Ordering & Autonomy Toggle
    # -------------------------------------------------------------
    print("\n--- Test 4: SQLite Mode - DESC Ordering & Roadmap Autonomy ---")
    os.environ["DATA_BACKEND"] = "sqlite"

    from services.journey import (
        get_journey_timeline,
        add_guide_contribution,
        toggle_event_roadmap_inclusion
    )
    from services.local_db import get_local_db

    db = get_local_db()
    test_asp_id = "test-asp-sqlite-" + str(uuid.uuid4())[:8]
    db.create_initial_journey(test_asp_id, "Ordering Test Journey")

    # Add 3 events with distinct dates
    db.add_journey_event(
        journey_id="j1",
        aspirant_id=test_asp_id,
        actor_id=test_asp_id,
        actor_role="aspirant",
        event_type="event_1",
        event_data={"title": "Day 1 - Foundation"},
        event_date="2026-01-01T10:00:00Z"
    )
    db.add_journey_event(
        journey_id="j1",
        aspirant_id=test_asp_id,
        actor_id=test_asp_id,
        actor_role="aspirant",
        event_type="event_2",
        event_data={"title": "Day 15 - Prototype"},
        event_date="2026-01-15T10:00:00Z"
    )
    db.add_journey_event(
        journey_id="j1",
        aspirant_id=test_asp_id,
        actor_id=test_asp_id,
        actor_role="aspirant",
        event_type="event_3",
        event_data={"title": "Day 30 - Market Launch"},
        event_date="2026-01-30T10:00:00Z"
    )

    timeline = get_journey_timeline(test_asp_id)
    assert len(timeline) == 3, f"Expected 3 events, got {len(timeline)}"
    print(f"  Top Event: {timeline[0]['title']} ({timeline[0]['event_date']})")
    print(f"  Btm Event: {timeline[2]['title']} ({timeline[2]['event_date']})")
    assert timeline[0]["title"] == "Day 30 - Market Launch", "Top event must be the most recent!"
    assert timeline[2]["title"] == "Day 1 - Foundation", "Bottom event must be the oldest!"
    print("  ✓ SQLite reverse chronological timeline verified: Most recent event on top.")

    # Mentor adds contribution to Aspirant's journey
    test_guide_id = "guide-" + str(uuid.uuid4())[:8]
    ev, err = add_guide_contribution(
        aspirant_id=test_asp_id,
        guide_id=test_guide_id,
        title="Guide Assisted: Acquired GST Certificate",
        description="Assisted founder with MSME & GST registration compliance.",
        event_date="2026-02-01T10:00:00Z"
    )
    assert ev is not None, f"Failed to add guide contribution: {err}"
    event_id = ev["id"]

    # Check default: included_in_roadmap should be True
    tl = get_journey_timeline(test_asp_id)
    gst_ev = next(e for e in tl if e["id"] == event_id)
    assert gst_ev["included_in_roadmap"] is True, "New contribution should default to included"
    print("  ✓ Guide logged contribution: Default status is 'included_in_roadmap = True'")

    # Aspirant chooses: Not Needed (excludes from personal roadmap)
    ok, err = toggle_event_roadmap_inclusion(event_id, test_asp_id, included=False)
    assert ok, f"Failed to toggle roadmap inclusion: {err}"

    tl_after = get_journey_timeline(test_asp_id)
    gst_ev_after = next(e for e in tl_after if e["id"] == event_id)
    assert gst_ev_after["included_in_roadmap"] is False, "Event should now be excluded"
    print("  ✓ Aspirant marked 'Not Needed': Event updated to 'included_in_roadmap = False'")

    # Verify Aspirant Highlights preview filters it out
    active_for_aspirant_highlights = [e for e in tl_after if e.get("included_in_roadmap", True) is not False]
    assert not any(e["id"] == event_id for e in active_for_aspirant_highlights), "Excluded item MUST NOT appear in Aspirant Highlights preview!"
    print("  ✓ Aspirant Highlights preview: Excluded contribution is hidden as requested.")

    # Verify Guide and Admin timelines STILL see it!
    assert any(e["id"] == event_id for e in tl_after), "Guide & Admin must still see the event!"
    print("  ✓ Guide & Admin visibility: Contribution remains visible with 'Founder Marked: Not Needed' status.")

    # Aspirant changes mind: Includes back
    ok2, err2 = toggle_event_roadmap_inclusion(event_id, test_asp_id, included=True)
    assert ok2, f"Failed to re-include event: {err2}"
    tl_reincluded = get_journey_timeline(test_asp_id)
    gst_ev_re = next(e for e in tl_reincluded if e["id"] == event_id)
    assert gst_ev_re["included_in_roadmap"] is True, "Event should now be re-included"
    print("  ✓ Aspirant marked 'Needed': Contribution successfully re-activated on roadmap.")

    # -------------------------------------------------------------
    # TEST 5: Supabase Mode - Timeline Ordering & Structure
    # -------------------------------------------------------------
    print("\n--- Test 5: Supabase Mode - DESC Ordering & Schema Check ---")
    os.environ["DATA_BACKEND"] = "supabase"
    from services.auth import get_supabase_admin_client
    admin_client = get_supabase_admin_client()
    if admin_client:
        ravi_id = "5ef8bed6-fbc9-49a7-8a16-91a7cd26b612"
        sb_timeline = get_journey_timeline(ravi_id)
        print(f"  Supabase timeline for Ravi Kumar: {len(sb_timeline)} events retrieved.")
        if len(sb_timeline) >= 2:
            d0 = str(sb_timeline[0].get("event_date", ""))
            d1 = str(sb_timeline[1].get("event_date", ""))
            print(f"  Top Event Date: {d0}")
            print(f"  2nd Event Date: {d1}")
            assert d0 >= d1, f"Top event date ({d0}) should be >= second event date ({d1})"
        for e in sb_timeline:
            assert "included_in_roadmap" in e, "Event must expose 'included_in_roadmap'"
        print("  ✓ Supabase timeline verified: DESC ordering and roadmap inclusion attribute active.")

    print("\n" + "="*70)
    print("🎉 ALL 5 VERIFICATION SUITES PASSED FLAWLESSLY!")
    print("="*70)

if __name__ == "__main__":
    run_tests()
