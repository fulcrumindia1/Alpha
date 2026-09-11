"""
services/schemes.py — Scheme Intelligence & Matching Engine for FULCRUM-INDIA
=============================================================================
Manages the 170-scheme catalogue with Admin CRUD and executes a
deterministic, explainable matching engine against founder profiles.

Rules:
- Terminology: "Recommended", "Matched", "Potentially Eligible"
- NEVER use: "Approved", "Guaranteed", "Granted"
- Generates transparent "WHY THIS MATCHED" checklists.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from services.auth import get_supabase_client
from services.local_db import get_local_db

def list_schemes(
    search: str = "",
    category: str = "ALL",
    stage: str = "ALL",
    sector: str = "ALL",
    active_only: bool = True
) -> List[Dict]:
    """Retrieves schemes from Supabase or local store with multi-facet filters."""
    client = get_supabase_client()
    if client:
        try:
            q = client.table("schemes").select("*")
            if active_only:
                q = q.eq("is_active", True)
            if category and category != "ALL":
                q = q.eq("category_type", category)
            if stage and stage != "ALL":
                q = q.eq("stage", stage)
            try:
                res = q.order("display_order", desc=False).execute()
            except Exception:
                res = q.order("name", desc=False).execute()
            if res.data:
                filtered = []
                for s in res.data:
                    # Filter by search term
                    if search:
                        term = search.lower()
                        text_corpus = f"{s.get('name','')} {s.get('agency','')} {s.get('description','')} {s.get('brief','')}".lower()
                        if term not in text_corpus:
                            continue
                    # Filter by sector
                    if sector and sector != "ALL":
                        sec_list = [str(x).lower() for x in (s.get("sectors") or [])]
                        if sector.lower() not in sec_list and "all sectors" not in sec_list:
                            continue
                    filtered.append(s)
                return filtered
        except Exception:
            pass

    return get_local_db().list_schemes(search, category, stage, sector, active_only)

def get_scheme(scheme_id: str) -> Optional[Dict]:
    """Retrieves full details of a single scheme."""
    client = get_supabase_client()
    if client:
        try:
            res = client.table("schemes").select("*").or_(f"id.eq.{scheme_id},source_id.eq.{scheme_id}").execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    return get_local_db().get_scheme_by_id(scheme_id)

def upsert_scheme(scheme: Dict, admin_id: str) -> Tuple[bool, Optional[str]]:
    """Admin adds or updates a funding opportunity."""
    if not scheme.get("name"):
        return False, "Scheme name is required."

    if not scheme.get("id"):
        import uuid
        scheme["id"] = f"SCH-ADMIN-{uuid.uuid4().hex[:8].upper()}"

    scheme["updated_at"] = datetime.now(timezone.utc).isoformat()

    client = get_supabase_client()
    if client:
        try:
            client.table("schemes").upsert(scheme, on_conflict="id").execute()
        except Exception:
            pass

    get_local_db().upsert_scheme(scheme)
    get_local_db().log_activity(admin_id, "upsert_scheme", "schemes", scheme["id"], {"name": scheme["name"]})
    return True, None

def toggle_archive_scheme(scheme_id: str, admin_id: str) -> Tuple[bool, Optional[str]]:
    """Toggles active/archived state for a scheme."""
    s = get_scheme(scheme_id)
    if not s:
        return False, "Scheme not found."

    new_active = not s.get("is_active", True)
    new_status = "active" if new_active else "archived"

    client = get_supabase_client()
    if client:
        try:
            client.table("schemes").update({
                "is_active": new_active,
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", scheme_id).execute()
        except Exception:
            pass

    s["is_active"] = new_active
    s["status"] = new_status
    get_local_db().upsert_scheme(s)
    get_local_db().log_activity(admin_id, f"set_{new_status}", "schemes", scheme_id)
    return True, None

def delete_scheme(scheme_id: str, admin_id: str) -> Tuple[bool, Optional[str]]:
    """Permanently deletes a scheme from the catalogue."""
    client = get_supabase_client()
    if client:
        try:
            client.table("schemes").delete().eq("id", scheme_id).execute()
        except Exception:
            pass

    get_local_db().delete_scheme(scheme_id)
    get_local_db().log_activity(admin_id, "delete_scheme", "schemes", scheme_id)
    return True, None

def match_schemes_for_aspirant(aspirant_id: str) -> List[Dict]:
    """
    Automatic Deterministic Matching Process:
    Aspirant Profile Attributes
          ↓
    Eligibility & Taxonomy Comparison
          ↓
    State/Geo + Stage + Sector + Demographics + Registrations
          ↓
    Score (0-98%) + "Why This Matched" Reasons
    """
    from services.profiles import get_profile
    profile = get_profile(aspirant_id)
    if not profile:
        return []

    p_data = profile.get("profile_data", {})
    biz = p_data.get("business", {})
    demo = p_data.get("demographics", {})

    user_state = (profile.get("state") or demo.get("state") or "Tamil Nadu").lower()
    user_district = (profile.get("district") or demo.get("district") or "").lower()
    user_sector = (biz.get("sector") or biz.get("business_type") or "").lower()
    user_stage = (biz.get("stage") or "Pre-Seed / Seed").lower()
    founder_category = (demo.get("category") or demo.get("founder_category") or "General").lower()
    is_dpiit = demo.get("is_dpiit_recognized") or demo.get("dpiit") or False
    is_startuptn = demo.get("is_startuptn_registered") or demo.get("startuptn") or False

    all_schemes = list_schemes(active_only=True)
    matches = []

    for s in all_schemes:
        score = 45  # Base eligibility baseline
        reasons = []

        # 1. State / Geography match
        scheme_state = (s.get("state_scope") or "All India").lower()
        if "all india" in scheme_state:
            score += 15
            reasons.append("✓ National scope coverage")
        elif "tamil nadu" in scheme_state or user_state in scheme_state:
            score += 25
            reasons.append(f"✓ Tamil Nadu state jurisdiction ({s.get('state_scope', 'Tamil Nadu')})")

        # 2. Stage match
        scheme_stage = (s.get("stage") or "").lower()
        if user_stage in scheme_stage or ("seed" in user_stage and "seed" in scheme_stage):
            score += 15
            reasons.append(f"✓ Stage fit ({s.get('stage', 'Early Stage')})")
        elif not scheme_stage or "all" in scheme_stage:
            score += 10
            reasons.append("✓ Open across development stages")

        # 3. Sector match
        sectors = [str(x).lower() for x in (s.get("sectors") or [])]
        if user_sector and any(user_sector in sec for sec in sectors):
            score += 20
            reasons.append(f"✓ Direct sector alignment ({biz.get('sector')})")
        elif any("all sectors" in sec or "technology" in sec or "general" in sec for sec in sectors):
            score += 10
            reasons.append("✓ Multi-sector eligible")

        # 4. Demographic & Founder Category fit
        elig_text = " ".join([str(e) for e in (s.get("eligibility") or [])]).lower()
        if founder_category in ("sc", "st", "women", "obc"):
            if founder_category in elig_text or "women" in elig_text or "special" in elig_text:
                score += 10
                reasons.append(f"✓ Preferential founder category incentives ({founder_category.upper()})")

        # 5. DPIIT Recognition Fast-Track
        if is_dpiit and ("dpiit" in elig_text or "startup india" in str(s.get("agency", "")).lower() or "sisfs" in s.get("id", "").lower()):
            score += 10
            reasons.append("✓ DPIIT recognition fast-track")

        # 6. StartupTN Fast-Track
        if is_startuptn and ("startuptn" in str(s.get("agency", "")).lower() or "tanseed" in s.get("id", "").lower()):
            score += 15
            reasons.append("✓ StartupTN verified track")

        # Cap score at 98%
        final_score = min(score, 98)

        # Minimum relevance threshold (60% match to recommend)
        if final_score >= 60:
            matches.append({
                "id": s["id"],
                "name": s["name"],
                "agency": s.get("agency", ""),
                "category_type": s.get("category_type", ""),
                "funding_type": s.get("funding_type", ""),
                "stage": s.get("stage", ""),
                "amount": s.get("amount", ""),
                "brief": s.get("brief", ""),
                "description": s.get("description", ""),
                "sectors": s.get("sectors", []),
                "eligibility": s.get("eligibility", []),
                "terms": s.get("terms", []),
                "hidden_agenda": s.get("hidden_agenda", []),
                "red_flags": s.get("red_flags", []),
                "application_url": s.get("application_url", ""),
                "match_score": final_score,
                "score": final_score,
                "match_reasons": reasons,
                "reasons": reasons,
                "recommendation_status": "Recommended" if final_score >= 80 else "Potentially Eligible"
            })

    # Sort descending by match score
    matches.sort(key=lambda m: m["match_score"], reverse=True)
    return matches
