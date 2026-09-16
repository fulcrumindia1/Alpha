import sys
import json
from services.auth import login_user, get_data_backend
from services.relationships import get_assigned_aspirants_for_sme, get_assigned_aspirants_for_guide, get_aspirant_mentors
from services.schemes_ui import parse_list_field
from services.help_requests import list_guide_requests, list_sme_requests

print("1. Active Backend:", get_data_backend())

# Guide login check
prof_g, err_g = login_user("rajendran@fulcrum.in", "Welcome@2026")
assert prof_g is not None, f"Guide login failed: {err_g}"
pdata_g = prof_g.get("profile_data") or {}
if isinstance(pdata_g, str):
    pdata_g = json.loads(pdata_g)
print("2. Guide login successful. temp_password_issued:", pdata_g.get("temp_password_issued"))
assert pdata_g.get("temp_password_issued") is False, "Guide should not be prompted for password"

# SME login check
prof_s, err_s = login_user("kumar.sme@fulcrum.in", "Welcome@2026")
assert prof_s is not None, f"SME login failed: {err_s}"
pdata_s = prof_s.get("profile_data") or {}
if isinstance(pdata_s, str):
    pdata_s = json.loads(pdata_s)
print("3. SME login successful. temp_password_issued:", pdata_s.get("temp_password_issued"))
assert pdata_s.get("temp_password_issued") is False, "SME should not be prompted for password"

# SME Caseload check
sme_cases = get_assigned_aspirants_for_sme(prof_s["id"])
print("4. SME assigned caseload count:", len(sme_cases))
if sme_cases:
    print("   Assigned case:", sme_cases[0].get("full_name"))
assert len(sme_cases) > 0, "SME should have assigned caseload (Ravi Kumar)"

# Guide Caseload check
guide_cases = get_assigned_aspirants_for_guide(prof_g["id"])
print("5. Guide assigned caseload count:", len(guide_cases))
if guide_cases:
    print("   Assigned mentee:", guide_cases[0].get("full_name"))
assert len(guide_cases) > 0, "Guide should have assigned caseload (Ravi Kumar)"

# Aspirant Mentors Lookup
asp_id = guide_cases[0]["id"]
mentors = get_aspirant_mentors(asp_id)
g_name = mentors.get("guide", {}).get("full_name") if mentors.get("guide") else "None"
s_name = mentors.get("sme", {}).get("full_name") if mentors.get("sme") else "None"
print(f"6. Aspirant mentors: Guide = {g_name}, SME = {s_name}")
assert g_name == "Rajendran Natarajan", f"Expected Rajendran Natarajan, got {g_name}"
assert s_name == "Kumar S.", f"Expected Kumar S., got {s_name}"

# Private intelligence formatting test
sample_agenda = '["Emphasize local employment", "Highlight tech innovation"]'
parsed = parse_list_field(sample_agenda)
print("7. Sample parsed agenda:\n", parsed)
assert "• Emphasize local employment" in parsed, "Expected bullet points in parsed agenda"

print("\n>>> ALL 7 VERIFICATION CRITERIA PASSED! <<<")
