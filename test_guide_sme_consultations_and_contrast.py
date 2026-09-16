import os
import sys
import html

# Ensure path and utf-8 output
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from services.schemes_ui import parse_list_field
from services.relationships import get_assigned_aspirants_for_guide, get_assigned_aspirants_for_sme
from services.help_requests import list_guide_requests, list_sme_requests

def main():
    print("=================================================================")
    print("FULCRUM-INDIA: GUIDE & SME CONSULTATIONS & CONTRAST VERIFICATION")
    print("=================================================================")

    # 1. Test parse_list_field Contrast & Formatting
    print("\n[TEST 1] Testing parse_list_field contrast & bullet markers...")
    sample_agenda = [
        ">> Government wants DIASPORA CAPITAL REMITTANCE into state startups - highlight Tamil Nadu footprint",
        ">> Media-friendly regional impact projects get faster syndicate spotlight on AngelsTN portal"
    ]
    agenda_html = parse_list_field(sample_agenda)
    print("Agenda HTML output length:", len(agenda_html))
    assert "&#9654;" in agenda_html, "Expected amber arrow entity &#9654; in agenda_html"
    assert "DIASPORA CAPITAL" in agenda_html, "Expected agenda text in output"

    sample_flags = [
        "!! Angel syndicates evaluate team integrity heavily - background checks are mandatory",
        "!! Do not attempt valuation inflation - Tamil diaspora angels are conservative value investors"
    ]
    flags_html = parse_list_field(sample_flags)
    print("Flags HTML output length:", len(flags_html))
    assert "&#9888;" in flags_html, "Expected red warning entity &#9888; in flags_html"
    assert "Angel syndicates" in flags_html, "Expected flags text in output"
    print("✅ TEST 1 PASSED: High-contrast bullets and clean formatting verified.")

    # 2. Test get_assigned_aspirants_for_guide
    print("\n[TEST 2] Testing get_assigned_aspirants_for_guide...")
    guide_id = "e44ba23e-05df-4c24-b831-4e38e38d3b27" # Rajendran
    guide_asps = get_assigned_aspirants_for_guide(guide_id)
    print(f"Guide '{guide_id}' caseload count: {len(guide_asps)}")
    for a in guide_asps:
        print(f"  - Aspirant: {a.get('full_name')} ({a.get('id')})")
    assert len(guide_asps) > 0, "Guide should have at least 1 assigned aspirant (Ravi Kumar)"
    print("✅ TEST 2 PASSED: Guide caseload verified.")

    # 3. Test get_assigned_aspirants_for_sme
    print("\n[TEST 3] Testing get_assigned_aspirants_for_sme...")
    sme_id = "083e04f3-5084-4ca8-a91d-cbf4e4294805" # Kumar S.
    sme_asps = get_assigned_aspirants_for_sme(sme_id)
    print(f"SME '{sme_id}' caseload count: {len(sme_asps)}")
    for a in sme_asps:
        print(f"  - Aspirant: {a.get('full_name')} ({a.get('id')})")
    assert len(sme_asps) > 0, "SME should have at least 1 assigned aspirant (Ravi Kumar)"
    print("✅ TEST 3 PASSED: SME caseload verified.")

    # 4. Test code structure of views/guide.py
    print("\n[TEST 4] Testing views/guide.py tab structure...")
    with open("views/guide.py", "r", encoding="utf-8") as f:
        guide_code = f.read()

    assert 'main_tabs = st.tabs(["👥 My Aspirants", "💬 All Consultations Overview", "👤 My Profile"])' in guide_code
    assert 'consult_label' in guide_code
    assert '"🏦 Scheme Matches"' in guide_code
    assert 'subtabs[4]' in guide_code
    assert 'color:#0F172A' in guide_code
    print("✅ TEST 4 PASSED: Guide portal contains 5 per-aspirant subtabs including Scheme Matches & Consultations, and high-contrast color #0F172A.")

    # 5. Test code structure of views/sme.py
    print("\n[TEST 5] Testing views/sme.py tab structure...")
    with open("views/sme.py", "r", encoding="utf-8") as f:
        sme_code = f.read()

    assert 'tabs = st.tabs([' in sme_code
    assert '"👥 My Assigned Cases"' in sme_code
    assert '"💬 All Consultations Overview"' in sme_code
    assert '"👤 My Profile"' in sme_code
    assert 'Select Entrepreneur for Domain Advisory' in sme_code
    assert 'subtabs = st.tabs([' in sme_code
    assert '"👤 Profile"' in sme_code
    assert '"🎬 Journey"' in sme_code
    assert '"🤝 Guidance Team"' in sme_code
    assert 'consult_label' in sme_code
    # Ensure SME does NOT have Scheme Matches subtab
    assert '"🏦 Scheme Matches"' not in sme_code
    print("✅ TEST 5 PASSED: SME portal matches Guide structure with 4 per-case subtabs (Profile, Journey, Guidance Team, Consultations) and NO Scheme Matches.")

    # 6. Test app.py sidebar navigation
    print("\n[TEST 6] Testing app.py navigation alignment...")
    with open("app.py", "r", encoding="utf-8") as f:
        app_code = f.read()
    assert '"👥 My Aspirants"' in app_code
    assert '"👥 My Assigned Cases"' in app_code
    assert '"💬 All Consultations Overview"' in app_code
    print("✅ TEST 6 PASSED: App navigation synchronized with portal architecture.")

    print("\n🎉 ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
