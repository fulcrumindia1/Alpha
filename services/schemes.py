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
from typing import Any, Optional, Dict, List, Tuple
from services.auth import get_supabase_client
from services.local_db import get_local_db

def list_schemes(
    search: str = "",
    category: str = "ALL",
    stage: str = "ALL",
    sector: str = "ALL",
    active_only: bool = True
) -> List[Dict]:
    """Retrieves schemes from local SQLite first (instant 2ms response), then Supabase fallback."""
    try:
        local_schemes = get_local_db().list_schemes(search, category, stage, sector, active_only)
        if local_schemes:
            return local_schemes
    except Exception:
        pass

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

    return []

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

def evaluate_scheme_for_aspirant(aspirant_id: str, scheme_or_id: Any, profile: Optional[Dict] = None) -> Optional[Dict]:
    """
    Evaluates a specific funding scheme against an Aspirant's venture profile.
    Produces:
    - Match score (0-98%)
    - Match reasons checklist
    - Eligibility / status label
    - Potential concerns
    - Guide-only private intelligence (hidden_agenda, red_flags)
    """
    if profile is None:
        from services.profiles import get_profile
        profile = get_profile(aspirant_id)
    if not profile:
        return None

    if isinstance(scheme_or_id, dict):
        s = scheme_or_id
    else:
        s = get_scheme(str(scheme_or_id))
    if not s:
        return None

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

    score = 45  # Base eligibility baseline
    reasons = []
    concerns = []

    # 1. State / Geography match
    scheme_state = (s.get("state_scope") or "All India").lower()
    if "all india" in scheme_state:
        score += 15
        reasons.append("National scope coverage across India")
    elif "tamil nadu" in scheme_state or user_state in scheme_state:
        score += 25
        reasons.append(f"Tamil Nadu state jurisdiction ({s.get('state_scope', 'Tamil Nadu')})")
    else:
        concerns.append(f"Geographic scope may be limited to {s.get('state_scope')}")

    # 2. Stage match
    scheme_stage = (s.get("stage") or "").lower()
    if user_stage in scheme_stage or ("seed" in user_stage and "seed" in scheme_stage):
        score += 15
        reasons.append(f"Development stage alignment ({s.get('stage', 'Early Stage')})")
    elif not scheme_stage or "all" in scheme_stage:
        score += 10
        reasons.append("Open across multiple development stages")
    else:
        concerns.append(f"Scheme target stage is '{s.get('stage')}', venture is '{biz.get('stage')}'")

    # 3. Sector match
    sectors = [str(x).lower() for x in (s.get("sectors") or [])]
    if user_sector and any(user_sector in sec for sec in sectors):
        score += 20
        reasons.append(f"Direct sector alignment ({biz.get('sector')})")
    elif any("all sectors" in sec or "technology" in sec or "general" in sec for sec in sectors):
        score += 10
        reasons.append("Multi-sector eligible fund")
    else:
        concerns.append("Specific sector eligibility criteria should be verified")

    # 4. Demographic & Founder Category fit
    elig_text = " ".join([str(e) for e in (s.get("eligibility") or [])]).lower()
    if founder_category in ("sc", "st", "women", "obc"):
        if founder_category in elig_text or "women" in elig_text or "special" in elig_text:
            score += 10
            reasons.append(f"Preferential founder category incentives ({founder_category.upper()})")

    # 5. DPIIT Recognition Fast-Track
    if is_dpiit and ("dpiit" in elig_text or "startup india" in str(s.get("agency", "")).lower() or "sisfs" in str(s.get("id", "")).lower()):
        score += 10
        reasons.append("DPIIT recognition fast-track path")
    elif not is_dpiit and ("dpiit" in elig_text or "startup india" in str(s.get("agency", "")).lower()):
        concerns.append("DPIIT recognition may be mandatory for sanction")

    # 6. StartupTN Fast-Track
    if is_startuptn and ("startuptn" in str(s.get("agency", "")).lower() or "tanseed" in str(s.get("id", "")).lower()):
        score += 15
        reasons.append("StartupTN verified track eligibility")

    final_score = min(score, 98)
    status_label = "Recommended" if final_score >= 80 else "Potentially Eligible"

    return {
        "id": s["id"],
        "name": s["name"],
        "agency": s.get("agency", ""),
        "ministry": s.get("ministry", ""),
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
        "application_prompt": s.get("application_prompt", ""),
        "application_url": s.get("application_url", ""),
        "last_verified": s.get("last_verified", "August 2026"),
        "match_score": final_score,
        "score": final_score,
        "match_reasons": reasons,
        "reasons": reasons,
        "potential_concerns": concerns,
        "recommendation_status": status_label,
        "eligibility_summary": f"{final_score}% Match · {status_label}",
        "scheme": s
    }

def match_schemes_for_aspirant(aspirant_id: str, profile: Optional[Dict] = None) -> List[Dict]:
    """
    Internal Deterministic Matching Process used by Guides and AI evaluation:
    Aspirant Profile Attributes -> Evaluates all active schemes -> Threshold filter >= 60%
    """
    if profile is None:
        from services.profiles import get_profile
        profile = get_profile(aspirant_id)
    if not profile:
        return []

    all_schemes = list_schemes(active_only=True)
    matches = []
    for s in all_schemes:
        res = evaluate_scheme_for_aspirant(aspirant_id, s, profile=profile)
        if res and res["match_score"] >= 60:
            matches.append(res)
    matches.sort(key=lambda m: m["match_score"], reverse=True)
    return matches

def release_scheme_to_aspirant(
    guide_id: str,
    aspirant_id: str,
    scheme_id: str,
    guide_recommendation: str,
    guide_note: str = ""
) -> Tuple[bool, Optional[str]]:
    """
    Guide Gatekeeper action: Releases evaluated scheme to an assigned Aspirant.
    Strictly verifies Guide authority before writing to scheme_releases.
    """
    from services.relationships import get_aspirant_mentors
    from services.journey import log_meaningful_event

    # 1. Server-side Relationship Authorization Check
    mentors = get_aspirant_mentors(aspirant_id)
    assigned_guide = mentors.get("guide")
    if not assigned_guide or str(assigned_guide.get("id")) != str(guide_id):
        return False, "You are not authorized to release schemes to this Aspirant."

    # 2. Fetch scheme metadata
    scheme = get_scheme(scheme_id)
    if not scheme:
        return False, "Scheme not found in master catalogue."
    scheme_name = scheme.get("name", "Funding Opportunity")

    # 3. Evaluate summary
    eval_res = evaluate_scheme_for_aspirant(aspirant_id, scheme)
    eligibility_summary = eval_res.get("eligibility_summary", "Potentially Eligible") if eval_res else "Potentially Eligible"

    now_iso = datetime.now(timezone.utc).isoformat()
    note_text = guide_note.strip() if guide_note else ""
    rec_text = guide_recommendation.strip() if guide_recommendation else "Reviewed and recommended by your Guide."

    # 4. Supabase cloud write if available
    client = get_supabase_client()
    if client:
        try:
            client.table("scheme_releases").upsert({
                "aspirant_id": aspirant_id,
                "guide_id": guide_id,
                "scheme_id": scheme_id,
                "status": "RELEASED",
                "guide_note": note_text,
                "guide_recommendation": rec_text,
                "eligibility_summary": eligibility_summary,
                "released_at": now_iso,
                "released_by": guide_id,
                "withdrawn_at": None,
                "withdrawn_by": None,
                "updated_at": now_iso
            }, on_conflict="aspirant_id,scheme_id").execute()
        except Exception:
            pass

    # 5. Local database write
    get_local_db().create_or_update_scheme_release(
        aspirant_id=aspirant_id,
        guide_id=guide_id,
        scheme_id=scheme_id,
        guide_recommendation=rec_text,
        guide_note=note_text,
        eligibility_summary=eligibility_summary
    )

    # 6. Log Journey Event
    log_meaningful_event(
        aspirant_id=aspirant_id,
        actor_id=guide_id,
        actor_role="guide",
        event_type="scheme_released",
        title=f"Funding Opportunity Recommended: {scheme_name}",
        description=f"Guide released {scheme_name} as a recommended funding opportunity. Note: {rec_text}",
        metadata={
            "scheme_id": scheme_id,
            "scheme_name": scheme_name,
            "guide_id": guide_id,
            "recommendation": rec_text
        }
    )

    return True, None

def withdraw_scheme_release(
    guide_id: str,
    aspirant_id: str,
    scheme_id: str
) -> Tuple[bool, Optional[str]]:
    """
    Guide Gatekeeper action: Withdraws a previously released scheme.
    Preserves historical record by setting status='WITHDRAWN'.
    """
    from services.relationships import get_aspirant_mentors
    from services.journey import log_meaningful_event

    # 1. Server-side Relationship Authorization Check
    mentors = get_aspirant_mentors(aspirant_id)
    assigned_guide = mentors.get("guide")
    if not assigned_guide or str(assigned_guide.get("id")) != str(guide_id):
        return False, "You are not authorized to release schemes to this Aspirant."

    scheme = get_scheme(scheme_id)
    scheme_name = scheme.get("name", "Funding Opportunity") if scheme else "Funding Opportunity"
    now_iso = datetime.now(timezone.utc).isoformat()

    # 2. Supabase update if available
    client = get_supabase_client()
    if client:
        try:
            client.table("scheme_releases").update({
                "status": "WITHDRAWN",
                "withdrawn_at": now_iso,
                "withdrawn_by": guide_id,
                "updated_at": now_iso
            }).eq("aspirant_id", aspirant_id).eq("scheme_id", scheme_id).execute()
        except Exception:
            pass

    # 3. Local database update
    get_local_db().withdraw_scheme_release(aspirant_id, scheme_id, guide_id)

    # 4. Log Journey Event
    log_meaningful_event(
        aspirant_id=aspirant_id,
        actor_id=guide_id,
        actor_role="guide",
        event_type="scheme_release_withdrawn",
        title=f"Scheme Release Withdrawn: {scheme_name}",
        description=f"Guide withdrew prior release of {scheme_name}.",
        metadata={
            "scheme_id": scheme_id,
            "scheme_name": scheme_name,
            "guide_id": guide_id
        }
    )

    return True, None

def get_released_schemes_for_aspirant(aspirant_id: str) -> List[Dict]:
    """
    Aspirant-facing scheme query:
    STRICTLY returns ONLY released schemes with Guide recommendations.
    CRITICAL SECURITY INVARIANT:
    Sanitizes and eliminates all Guide-only private intelligence
    (hidden_agenda, red_flags, AI pitch prompt) from the payload.
    """
    client = get_supabase_client()
    if client:
        try:
            res = client.table("scheme_releases").select("*, schemes(*)").eq("aspirant_id", aspirant_id).eq("status", "RELEASED").execute()
            if res.data:
                cleaned = []
                for r in res.data:
                    s = r.get("schemes") or {}
                    if not s.get("is_active", True):
                        continue
                    # Flatten release metadata onto scheme
                    s["release_id"] = r.get("id")
                    s["guide_id"] = r.get("guide_id")
                    s["guide_recommendation"] = r.get("guide_recommendation")
                    s["guide_note"] = r.get("guide_note")
                    s["released_at"] = r.get("released_at")
                    s["eligibility_summary"] = r.get("eligibility_summary")
                    # STRICT PRIVATE INTELLIGENCE STRIPPING
                    s["hidden_agenda"] = []
                    s["red_flags"] = []
                    s["application_prompt"] = ""
                    cleaned.append(s)
                return cleaned
        except Exception:
            pass

    return get_local_db().get_released_schemes_for_aspirant(aspirant_id)

def get_guide_scheme_releases(guide_id: str, aspirant_id: Optional[str] = None) -> List[Dict]:
    """
    Returns complete release history (RELEASED and WITHDRAWN) for Guide view.
    """
    client = get_supabase_client()
    if client:
        try:
            q = client.table("scheme_releases").select("*, schemes(name, agency, amount), profiles:aspirant_id(full_name, email)")
            q = q.eq("guide_id", guide_id)
            if aspirant_id:
                q = q.eq("aspirant_id", aspirant_id)
            res = q.order("updated_at", desc=True).execute()
            if res.data:
                rows = []
                for r in res.data:
                    sc = r.get("schemes") or {}
                    ap = r.get("profiles") or {}
                    r["scheme_name"] = sc.get("name") or "Scheme"
                    r["scheme_agency"] = sc.get("agency") or ""
                    r["scheme_amount"] = sc.get("amount") or ""
                    r["aspirant_name"] = ap.get("full_name") or "Entrepreneur"
                    r["aspirant_email"] = ap.get("email") or ""
                    rows.append(r)
                return rows
        except Exception:
            pass

    return get_local_db().get_scheme_releases_for_guide(guide_id, aspirant_id)

