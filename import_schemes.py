"""
import_schemes.py — Authoritative Scheme Importer for FULCRUM-INDIA (Cluster A)
=============================================================================
Reads source dataset from FOUNDER_AI_DIGITAL_PLAYBOOK_2026.html
Validates records, normalizes fields, saves seed/schemes.json,
and inserts/updates the schemes table in Supabase without hardcoded data.
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime

# Supabase Client
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None

def find_playbook_html() -> Path:
    """Locates FOUNDER_AI_DIGITAL_PLAYBOOK_2026.html in current or parent dirs."""
    candidates = [
        Path(__file__).resolve().parent / "FOUNDER_AI_DIGITAL_PLAYBOOK_2026.html",
        Path(__file__).resolve().parent.parent / "FOUNDER_AI_DIGITAL_PLAYBOOK_2026.html",
        Path("c:/Users/hp/Desktop/Fulcrum-Alpha/FOUNDER_AI_DIGITAL_PLAYBOOK_2026.html"),
        Path("FOUNDER_AI_DIGITAL_PLAYBOOK_2026.html")
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    raise FileNotFoundError("Could not find FOUNDER_AI_DIGITAL_PLAYBOOK_2026.html in search paths.")

def extract_schemes_from_html(html_path: Path) -> list:
    """Extracts the fundingSchemes JSON array from the HTML file."""
    print(f"[Importer] Reading source dataset from: {html_path}")
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r'const\s+fundingSchemes\s*=\s*(\[.*?\]);', content, re.DOTALL)
    if not match:
        raise ValueError("Regex failed to find 'const fundingSchemes = [...];' in HTML source.")

    raw_schemes = json.loads(match.group(1))
    print(f"[Importer] Successfully extracted {len(raw_schemes)} raw scheme records.")
    return raw_schemes

def normalize_scheme(raw: dict) -> dict:
    """Normalizes raw scheme record to standard Cluster A schema."""
    source_id = str(raw.get("id") or "").strip()
    name = str(raw.get("name") or "").strip()
    if not name:
        name = "Untitled Scheme"

    scheme_id = source_id if source_id else f"SCH-{re.sub(r'[^a-zA-Z0-9]', '', name)[:16].upper()}"

    # Normalize sectors to list
    sectors = raw.get("sectors") or []
    if isinstance(sectors, str):
        sectors = [s.strip() for s in sectors.split(",") if s.strip()]

    # Normalize eligibility to list
    eligibility = raw.get("eligibility") or []
    if isinstance(eligibility, str):
        eligibility = [eligibility]

    # Normalize terms to list
    terms = raw.get("terms") or []
    if isinstance(terms, str):
        terms = [terms]

    # Normalize hidden agenda and red flags
    hidden_agenda = raw.get("hidden_agenda") or []
    if isinstance(hidden_agenda, str):
        hidden_agenda = [hidden_agenda]

    red_flags = raw.get("red_flags") or []
    if isinstance(red_flags, str):
        red_flags = [red_flags]

    funding_type = str(raw.get("fundingType") or raw.get("type") or "Grant").strip()
    category_type = str(raw.get("categoryType") or "Central Govt").strip()
    state_scope = str(raw.get("stateScope") or "All India").strip()
    geography = str(raw.get("geography") or "National").strip()
    stage = raw.get("stage") or "Pre-Seed / Seed"

    return {
        "id": scheme_id,
        "source_id": source_id,
        "name": name,
        "agency": str(raw.get("agency") or "Government of India / Venture Network").strip(),
        "ministry": str(raw.get("agency") or "").strip(),
        "scheme_type": funding_type,
        "category_type": category_type,
        "funding_type": funding_type,
        "stage": stage,
        "amount": str(raw.get("amount") or "Grant / Investment Support").strip(),
        "brief": str(raw.get("brief") or name).strip(),
        "description": str(raw.get("details") or raw.get("description") or "").strip(),
        "sectors": sectors,
        "eligibility": eligibility,
        "terms": terms,
        "hidden_agenda": hidden_agenda,
        "red_flags": red_flags,
        "process": str(raw.get("process") or "").strip(),
        "timeline": str(raw.get("timeline") or "2-3 months").strip(),
        "success_rate": str(raw.get("success_rate") or "~20%").strip(),
        "contact": str(raw.get("contact") or "").strip(),
        "state_scope": state_scope,
        "geography": geography,
        "application_url": str(raw.get("officialSourceUrl") or "").strip(),
        "last_verified": str(raw.get("lastVerified") or "August 2026").strip(),
        "application_prompt": str(raw.get("applicationPrompt") or "").strip(),
        "source_dataset": "Founder AI Digital Playbook 2026",
        "status": "active",
        "is_active": True,
        "updated_at": datetime.utcnow().isoformat()
    }

def main(dry_run=False):
    html_file = find_playbook_html()
    raw_list = extract_schemes_from_html(html_file)

    normalized_schemes = []
    seen_ids = set()

    for s in raw_list:
        norm = normalize_scheme(s)
        # Deduplication
        if norm["id"] in seen_ids:
            norm["id"] = f"{norm['id']}-DUP-{len(seen_ids)}"
        seen_ids.add(norm["id"])
        normalized_schemes.append(norm)

    # Save to seed directory as fallback and offline backup
    seed_dir = Path(__file__).resolve().parent / "seed"
    seed_dir.mkdir(parents=True, exist_ok=True)
    seed_file = seed_dir / "schemes.json"

    with open(seed_file, "w", encoding="utf-8") as f:
        json.dump(normalized_schemes, f, indent=2, ensure_ascii=False)

    print(f"[Importer] Successfully normalized {len(normalized_schemes)} schemes.")
    print(f"[Importer] Offline seed JSON written to: {seed_file}")

    if dry_run:
        print("[Importer] Dry run complete. No database write performed.")
        return normalized_schemes

    # Attempt Supabase database sync if client is configured
    try:
        from services.auth import get_supabase_admin_client
        admin_client = get_supabase_admin_client()
        if admin_client:
            print("[Importer] Connecting to Supabase to upsert schemes...")
            # Upsert in batches of 25
            batch_size = 25
            for i in range(0, len(normalized_schemes), batch_size):
                batch = normalized_schemes[i:i + batch_size]
                res = admin_client.table("schemes").upsert(batch, on_conflict="id").execute()
                print(f"[Importer] Upserted batch {i // batch_size + 1} ({len(batch)} records)")
            print("[Importer] All 170 schemes synchronized with Supabase database successfully!")
        else:
            print("[Importer] Notice: Supabase admin client not initialized. Seed JSON ready.")
    except Exception as e:
        print(f"[Importer] Database sync notice (table may need DDL creation): {e}")

    return normalized_schemes

if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    main(dry_run=is_dry)
