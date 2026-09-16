"""
scripts/fix_scheme_urls.py
==========================
Rectifies official portal URLs for all 170 schemes in both seed/schemes.json
and the live Supabase/SQLite database tables.
Replaces generic/blank/broken links (like 'https://www.startupindia.gov.in' or 
'https://www.District Industries Centre') with authentic nodal portal URLs.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re
import json
from services.auth import get_supabase_admin_client, get_data_backend
from services.local_db import get_local_db

# Curated, authoritative URL mapping based on Scheme ID, Name, and Agency
PORTAL_URL_MAP = {
    # Food & Agriculture
    "PM FME": "https://pmfme.mofpi.gov.in",
    "CEFPPC": "https://mofpi.gov.in/schemes/creation-expansion-food-processing-preservation-capacities-cefppc",
    "Agro-Processing Cluster": "https://mofpi.gov.in/schemes/agro-processing-cluster",
    "Food Processing": "https://mofpi.gov.in",
    "Agriculture Infrastructure Fund": "https://agriinfra.dac.gov.in",
    "PM KUSUM": "https://pmkusum.mnre.gov.in",
    "NABARD PODF": "https://www.nabard.org",
    "NABARD Fintech": "https://www.nabard.org",
    "NABVENTURES": "https://nabventures.in",

    # Tamil Nadu State Schemes
    "Kalaignar Kaivinai Thittam": "https://msme.tn.gov.in",
    "NEEDS": "https://msmeonline.tn.gov.in/needs/",
    "UYEGP": "https://msmeonline.tn.gov.in/uyegp/",
    "TWEES": "https://msme.tn.gov.in",
    "AABCS": "https://msme.tn.gov.in",
    "TICEL BioPark": "https://ticelbiopark.com",
    "IIT Madras RTBI": "https://rtbi.in",
    "Tamil Nadu Startup Policy": "https://www.startuptn.in",
    "TANFUND": "https://www.startuptn.in",
    "AngelsTN": "https://www.startuptn.in",
    "StartupTN Schemes": "https://www.startuptn.in",
    "TN MSME Schemes": "https://msme.tn.gov.in",
    "TIDCO Schemes": "https://tidco.com",
    "TIDEL Park": "https://www.tidelpark.com",
    "TN EV Policy": "https://guidance.tn.gov.in",

    # Central MSME & Employment
    "PMEGP": "https://www.kviconline.gov.in/pmegpeportal/",
    "Mudra": "https://www.mudra.org.in",
    "Stand Up India": "https://www.standupmitra.in",
    "PM Vishwakarma": "https://pmvishwakarma.gov.in",
    "PM SVANidhi": "https://pmsvanidhi.mohua.gov.in",
    "CGTMSE": "https://www.cgtmse.in",
    "Udyam Registration": "https://udyamregistration.gov.in",
    "National Urban Livelihoods Mission": "https://nulm.gov.in",
    "MSME Schemes": "https://msme.gov.in",
    "TREAD Women": "https://msme.gov.in",
    "WEP": "https://wep.gov.in",
    "Women Entrepreneurship Platform": "https://wep.gov.in",

    # DeepTech, AI, Space, Semiconductors
    "IndiaAI": "https://www.indiaai.gov.in",
    "Semiconductor Mission": "https://www.semiconindia.org",
    "DLI": "https://www.semiconindia.org",
    "IN-SPACe": "https://www.inspace.gov.in",
    "ISRO": "https://www.isro.gov.in",
    "NIDHI PRAYAS": "https://nidhi-prayas.org",
    "NIDHI EIR": "https://dst.gov.in",
    "Atal New India Challenge": "https://aim.gov.in",
    "ANIC": "https://aim.gov.in",
    "NITI SVP": "https://aim.gov.in",
    "Niti Aayog": "https://aim.gov.in",
    "Startup India Seed Fund": "https://seedfund.startupindia.gov.in",
    "SISFS": "https://seedfund.startupindia.gov.in",
    "Fund of Funds": "https://www.sidbi.in",
    "CGSS": "https://www.cgtmse.in",

    # Defence & Aerospace
    "iDEX": "https://idex.gov.in",
    "TDF DRDO": "https://tdf.drdo.gov.in",
    "Technology Development Fund": "https://tdf.drdo.gov.in",
    "Make in India Defence": "https://www.makeinindiadefence.gov.in",

    # Biotechnology & Health
    "BIRAC": "https://birac.nic.in",
    "Biotechnology Ignition Grant": "https://birac.nic.in",
    "BIPP": "https://birac.nic.in",
    "IIPME": "https://birac.nic.in",
    "ICMR": "https://main.icmr.nic.in",
    "ABDM": "https://sandbox.abdm.gov.in",

    # Finance, Renewable, Trade & International
    "RBI Regulatory Sandbox": "https://www.rbi.org.in",
    "IFSCA": "https://ifsca.gov.in",
    "MNRE": "https://mnre.gov.in",
    "IREDA": "https://www.ireda.in",
    "PM-DevINE": "https://mdoner.gov.in",
    "NEAT": "https://neat.aicte-india.org",
    "PLI": "https://www.makeinindia.com/production-linked-incentive",
    "Niryat Bandhu": "https://www.dgft.gov.in",
    "VCF-BC": "https://vcf-bc.in",
    "VCF-SC": "https://vcf-sc.in",
    "SAGE": "https://sage.dosje.gov.in",
    "JETRO": "https://www.jetro.go.jp/en/",
    "USAID": "https://www.usaid.gov/india",
    "Gates Foundation": "https://www.gatesfoundation.org",
    "Green Climate Fund": "https://www.greenclimate.fund",

    # Venture Capital Funds
    "Accel Atoms": "https://atoms.accel.in",
    "Peak XV": "https://www.surgeahead.com",
    "Speciale Invest": "https://www.specialeinvest.com",
    "Anicut Capital": "https://www.anicutcapital.com",
    "Arali Ventures": "https://www.araliventures.com",
    "Better Capital": "https://www.bettercap.vc",
    "Titan Capital": "https://www.titancapital.vc"
}

def resolve_official_url(scheme: dict) -> str:
    name = scheme.get("name", "")
    agency = scheme.get("agency", "")
    current_url = scheme.get("application_url") or scheme.get("officialSourceUrl") or ""

    # Check if current URL is already specific (not generic startupindia, not broken)
    if current_url and "startupindia.gov.in" not in current_url and "District" not in current_url and current_url.startswith("http"):
        return current_url.strip()

    # Search keyword match in scheme name and agency
    search_text = f"{name} {agency}".lower()
    for kw, target_url in PORTAL_URL_MAP.items():
        if kw.lower() in search_text:
            return target_url

    # Agency based fallbacks
    ag_lower = agency.lower()
    if "food processing" in ag_lower:
        return "https://mofpi.gov.in"
    if "electronics" in ag_lower or "meity" in ag_lower:
        return "https://meity.gov.in"
    if "tamil nadu" in ag_lower or "startuptn" in ag_lower:
        return "https://www.startuptn.in"
    if "micro, small and medium" in ag_lower or "msme" in ag_lower:
        return "https://msme.gov.in"
    if "biotechnology" in ag_lower or "birac" in ag_lower:
        return "https://birac.nic.in"
    if "science & technology" in ag_lower or "dst" in ag_lower:
        return "https://dst.gov.in"
    if "defence" in ag_lower:
        return "https://idex.gov.in"
    if "textiles" in ag_lower:
        return "https://texmin.nic.in"
    if "finance" in ag_lower:
        return "https://financialservices.gov.in"
    if "social justice" in ag_lower:
        return "https://socialjustice.gov.in"
    if "tribal" in ag_lower:
        return "https://tribal.gov.in"
    if "ayush" in ag_lower:
        return "https://ayush.gov.in"
    if "private syndicate" in ag_lower or "angel" in ag_lower:
        return "https://www.startuptn.in/angelstn"

    return "https://www.startuptn.in" if "tamil nadu" in (scheme.get("state_scope") or "").lower() else "https://seedfund.startupindia.gov.in"

def run_fix():
    seed_file = Path(__file__).resolve().parent.parent / "seed" / "schemes.json"
    with open(seed_file, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    updated_count = 0
    for s in schemes:
        orig = s.get("application_url", "")
        new_url = resolve_official_url(s)
        if orig != new_url:
            s["application_url"] = new_url
            s["officialSourceUrl"] = new_url
            updated_count += 1

    # Save to seed/schemes.json
    with open(seed_file, "w", encoding="utf-8") as f:
        json.dump(schemes, f, indent=2, ensure_ascii=False)

    print(f"[Seed File] Updated {updated_count} scheme URLs in seed/schemes.json.")

    # Update SQLite database
    try:
        db = get_local_db()
        conn = db._get_conn()
        cur = conn.cursor()
        for s in schemes:
            cur.execute("UPDATE schemes SET application_url = ? WHERE id = ?", (s["application_url"], s["id"]))
        conn.commit()
        print(f"[SQLite] Synced updated URLs into local cluster_a.db.")
    except Exception as e:
        print(f"[SQLite Error] {e}")

    # Update Supabase database
    admin = get_supabase_admin_client()
    if admin:
        try:
            print("[Supabase] Syncing updated URLs into Supabase schemes table...")
            for s in schemes:
                admin.table("schemes").update({"application_url": s["application_url"]}).eq("id", s["id"]).execute()
            print("[Supabase] Successfully synchronized all scheme URLs to live Supabase!")
        except Exception as e:
            print(f"[Supabase Error] {e}")

if __name__ == "__main__":
    run_fix()
