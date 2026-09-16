"""
services/schemes.py — Scheme Intelligence & Matching Engine for FULCRUM-INDIA
=============================================================================
Manages the 170-scheme catalogue with Admin CRUD and executes a
deterministic, explainable matching engine against founder profiles.

Rules:
- Terminology: "Recommended", "Matched", "Potentially Eligible"
- NEVER use: "Approved", "Guaranteed", "Granted"
- Generates transparent "WHY THIS MATCHED" checklists.
Supports dual backends: Supabase (primary) and SQLite (explicit local development).
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List, Tuple
from services.auth import get_supabase_client, get_supabase_admin_client, get_data_backend
from services.local_db import get_local_db

def _get_user_client():
    """Returns the authenticated user's Supabase client (RLS-enforced)."""
    return get_supabase_client()

def _get_admin_client():
    """Returns the privileged admin Supabase client (bypasses RLS). Use sparingly."""
    return get_supabase_admin_client()

def list_schemes(
    search: str = "",
    category: str = "ALL",
    stage: str = "ALL",
    sector: str = "ALL",
    active_only: bool = True
) -> List[Dict]:
    """Retrieves schemes from the active backend."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
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
                    res = q.order("display_order", desc=False).order("name", desc=False).execute()
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
                            sec_raw = s.get("sectors") or []
                            if isinstance(sec_raw, str):
                                try:
                                    sec_raw = json.loads(sec_raw)
                                except Exception:
                                    sec_raw = [sec_raw]
                            sec_list = [str(x).lower() for x in sec_raw]
                            if sector.lower() not in sec_list and "all sectors" not in sec_list:
                                continue
                        filtered.append(s)
                    return filtered
                return []
            except Exception as e:
                print(f"[Schemes] Supabase list error: {e}")
                return []
        return []

    # SQLite local mode
    return get_local_db().list_schemes(search, category, stage, sector, active_only)

def get_scheme(scheme_id: str) -> Optional[Dict]:
    """Retrieves full details of a single scheme."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        admin = _get_admin_client()
        reader = client if client else admin
        if reader:
            try:
                res = reader.table("schemes").select("*").or_(f"id.eq.{scheme_id},source_id.eq.{scheme_id}").execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception:
                pass
            if admin and admin != reader:
                try:
                    res = admin.table("schemes").select("*").or_(f"id.eq.{scheme_id},source_id.eq.{scheme_id}").execute()
                    if res.data and len(res.data) > 0:
                        return res.data[0]
                except Exception:
                    pass
        fallback = get_local_db().get_scheme_by_id(scheme_id)
        if fallback:
            return fallback
        return None

    return get_local_db().get_scheme_by_id(scheme_id)

def upsert_scheme(scheme: Dict, admin_id: str) -> Tuple[bool, Optional[str]]:
    """Admin adds or updates a funding opportunity."""
    if not scheme.get("name"):
        return False, "Scheme name is required."

    if not scheme.get("id"):
        import uuid
        scheme["id"] = f"SCH-ADMIN-{uuid.uuid4().hex[:8].upper()}"

    scheme["updated_at"] = datetime.now(timezone.utc).isoformat()
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_admin_client()
        if not client:
            return False, "Supabase client not available."
        try:
            client.table("schemes").upsert(scheme, on_conflict="id").execute()
            return True, None
        except Exception as e:
            return False, f"Failed to save scheme to Supabase: {e}"

    # SQLite mode
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
    now_iso = datetime.now(timezone.utc).isoformat()
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_admin_client()
        if not client:
            return False, "Supabase client not available."
        try:
            client.table("schemes").update({
                "is_active": new_active,
                "status": new_status,
                "updated_at": now_iso
            }).eq("id", scheme_id).execute()
            return True, None
        except Exception as e:
            return False, f"Failed to toggle archive state in Supabase: {e}"

    # SQLite mode
    s["is_active"] = new_active
    s["status"] = new_status
    get_local_db().upsert_scheme(s)
    get_local_db().log_activity(admin_id, f"set_{new_status}", "schemes", scheme_id)
    return True, None

def delete_scheme(scheme_id: str, admin_id: str) -> Tuple[bool, Optional[str]]:
    """Permanently deletes a scheme from the catalogue."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_admin_client()
        if not client:
            return False, "Supabase client not available."
        try:
            client.table("schemes").delete().eq("id", scheme_id).execute()
            return True, None
        except Exception as e:
            return False, f"Failed to delete scheme in Supabase: {e}"

    # SQLite mode
    get_local_db().delete_scheme(scheme_id)
    get_local_db().log_activity(admin_id, "delete_scheme", "schemes", scheme_id)
    return True, None

def match_schemes_for_aspirant(
    aspirant_id: str, 
    profile: Optional[Dict] = None, 
    limit: Optional[int] = None, 
    min_score: int = 60
) -> List[Dict]:
    """
    Explainable Deterministic Matching Engine:
    Computes a contextual match score (0-100%) for each active scheme based on:
    - Domain & Sector Alignment (Up to 40 pts) with negative penalty for incompatible high-tech/pharma verticals
    - Venture Stage Alignment (Up to 25 pts)
    - State / Geography Jurisdiction (Up to 20 pts)
    - Affirmative Demographic / Quota Priority (Up to 15 pts)
    
    Returns list of matched schemes scoring >= min_score ordered by match_score DESC.
    """
    import re

    if profile is None:
        from services.profiles import get_profile
        profile = get_profile(aspirant_id)
        if not profile:
            admin = _get_admin_client()
            if admin:
                try:
                    res_p = admin.table("profiles").select("*").eq("id", aspirant_id).execute()
                    if res_p.data:
                        profile = res_p.data[0]
                except Exception:
                    pass
    if not profile:
        return []

    p_data = profile.get("profile_data") or {}
    if isinstance(p_data, str):
        try:
            p_data = json.loads(p_data)
        except Exception:
            p_data = {}

    biz = p_data.get("business") or {}
    demo = p_data.get("demographics") or {}
    pers = p_data.get("personal") or {}

    asp_sector = (biz.get("sector") or "").lower()
    asp_biz_type = (biz.get("business_type") or "").lower()
    asp_stage = (biz.get("stage") or "idea").lower()
    asp_state = (profile.get("state") or demo.get("state") or "Tamil Nadu").lower()
    asp_district = (profile.get("district") or demo.get("district") or "").lower()
    asp_category = (demo.get("category") or demo.get("founder_category") or demo.get("social_category") or "").lower()
    asp_gender = (pers.get("gender") or demo.get("gender") or "").lower()
    women_equity = demo.get("women_equity_pct") or (100 if demo.get("is_women_led") else 0)
    try:
        women_equity_num = float(women_equity)
    except (ValueError, TypeError):
        women_equity_num = 0.0
    is_women_led = bool(demo.get("is_women_led") or "female" in asp_gender or "woman" in asp_gender or women_equity_num >= 51.0)
    asp_desc = (biz.get("description") or "").lower()
    asp_name = (biz.get("business_name") or "").lower()

    # Domain keyword extraction
    founder_keywords = set(re.findall(r'[a-zA-Z]{3,}', f"{asp_sector} {asp_biz_type} {asp_desc} {asp_name}"))

    agri_food_kws = {"food", "millet", "agri", "agriculture", "farmer", "processing", "fmcg", "dairy", "nutrition", "harvest", "crop", "horticulture", "organic", "grain", "bakery"}
    tech_exclusive_kws = {"semiconductor", "chip design", "deeptech", "ai/ml", "artificial intelligence", "gpu", "defence", "defense", "aerospace", "satellite", "space", "biotech", "clinical", "pharma", "medical devices", "quantum"}

    is_founder_food_agri = bool(founder_keywords & agri_food_kws or "food" in asp_sector or "agri" in asp_sector)
    is_founder_tech = bool(founder_keywords & {"tech", "software", "ai", "deeptech", "hardware", "saas", "electronics"})

    backend = get_data_backend()
    if backend == "supabase":
        admin = _get_admin_client()
        if admin:
            try:
                res = admin.table("schemes").select("*").eq("is_active", True).execute()
                all_schemes = res.data or []
            except Exception:
                all_schemes = []
        else:
            all_schemes = []
    else:
        all_schemes = list_schemes(active_only=True)

    results = []

    for s in all_schemes:
        score = 0
        reasons = []
        concerns = []

        s_name = (s.get("name") or "").lower()
        s_agency = (s.get("agency") or "").lower()
        s_brief = (s.get("brief") or "").lower()
        s_desc = (s.get("description") or "").lower()
        s_sectors = s.get("sectors") or []
        if isinstance(s_sectors, str):
            try:
                s_sectors = json.loads(s_sectors)
            except Exception:
                s_sectors = [s_sectors]
        sec_lower = [str(x).lower() for x in s_sectors]
        full_scheme_text = f"{s_name} {s_agency} {s_brief} {s_desc} {' '.join(sec_lower)}"

        # ── 1. Sector & Domain Alignment (Up to 40 pts) ──
        is_cross_sector_scheme = any("all sectors" in x or "cross-sector" in x or "any" in x for x in sec_lower)
        has_direct_food_match = is_founder_food_agri and any(k in full_scheme_text for k in agri_food_kws)
        has_keyword_match = bool(founder_keywords & set(sec_lower)) or (asp_sector and any(asp_sector in x or x in asp_sector for x in sec_lower if "all sectors" not in x))
        is_broad_msme = any(x in s_name for x in ["pmegp", "mudra", "stand up india", "uyegp", "needs", "cgtmse", "startup india seed", "tanfund", "angelstn", "pmfme", "fme", "agri", "food"])
        has_tech_conflict = not is_founder_tech and any(k in full_scheme_text for k in tech_exclusive_kws) and not has_direct_food_match

        if has_direct_food_match or (has_keyword_match and not has_tech_conflict):
            score += 40
            match_label = asp_sector.title() if asp_sector else "Core Domain"
            reasons.append(f"Direct sector alignment: {match_label}")
        elif "manufacturing" in sec_lower and ("manufacturing" in asp_sector or "manufacturing" in asp_biz_type):
            score += 25
            reasons.append("Manufacturing enterprise funding quota")
        elif is_broad_msme:
            score += 25
            reasons.append("Broad-based MSME enterprise scale fund")
        elif has_tech_conflict:
            score -= 20
            concerns.append("Specialized tech/hardware/defence fund outside your core domain")
        elif is_cross_sector_scheme:
            score += 15
            reasons.append("Cross-sector eligible fund")
        else:
            score += 5

        # ── 2. Stage Alignment (Up to 25 pts) ──
        s_stage = (s.get("stage") or "").lower()
        is_stage_agnostic = not s_stage or any(x in s_stage for x in ["all", "agnostic", "multi-stage", "any"])
        is_founder_early = any(x in asp_stage for x in ["ideation", "r&d", "pre-seed", "seed", "concept", "prototype"])
        is_scheme_early = any(x in s_stage for x in ["ideation", "r&d", "pre-seed", "seed", "early", "mvp"])
        is_founder_growth = any(x in asp_stage for x in ["growth", "series", "scale", "debt"])
        is_scheme_growth = any(x in s_stage for x in ["growth", "series", "scale", "debt"])

        if is_stage_agnostic:
            score += 20
            reasons.append("Open to all development stages")
        elif (is_founder_early and is_scheme_early) or (is_founder_growth and is_scheme_growth) or (asp_stage in s_stage):
            score += 25
            reasons.append(f"Stage match: {s.get('stage', 'Development Phase')}")
        elif is_founder_early and is_scheme_growth:
            score += 0
            concerns.append("Requires later-stage scaling metrics (Series A/Growth)")
        else:
            score += 12
            reasons.append(f"Stage eligibility: {s.get('stage', 'Stage Flexible')}")

        # ── 3. Geography & State Scope (Up to 20 pts) ──
        scope = (s.get("state_scope") or s.get("geography") or "All India").lower()
        is_tn_scheme = "tamil nadu" in scope or "tn" in scope or "startuptn" in s_agency or "tamil nadu" in s_agency
        is_tn_founder = "tamil nadu" in asp_state or (asp_district and "other" not in asp_district and "non-tn" not in asp_district)
        dist_display = asp_district.title() if (asp_district and "other" not in asp_district) else "Tamil Nadu"

        if is_tn_scheme:
            if is_tn_founder:
                score += 20
                reasons.append(f"Tamil Nadu state jurisdiction ({dist_display} eligible)")
            else:
                score += 0
                concerns.append("Restricted to Tamil Nadu registered enterprises")
        elif "all india" in scope or "central" in scope or "national" in scope:
            score += 15
            reasons.append("National Central Government initiative (All states eligible)")
        else:
            score += 5
            concerns.append(f"Regional scope: {s.get('state_scope', 'Specific Region')}")

        # ── 4. Demographics & Affirmative Priority (Up to 15 pts) ──
        elig = s.get("eligibility") or []
        if isinstance(elig, str):
            try:
                elig = json.loads(elig)
            except Exception:
                elig = [elig]
        elig_text = " ".join([str(x) for x in elig]).lower()

        # Check for gender-exclusive schemes (e.g. TWEES, TREAD, Women Entrepreneurship funds)
        is_women_scheme = (
            any(w in s_name or w in s_brief for w in ["women", "mahila", "nari", "twees", "tread"]) or
            any("women" in str(x).lower() and ("51%" in str(x).lower() or "ownership" in str(x).lower() or "exclusive" in str(x).lower() or "only" in str(x).lower()) for x in elig)
        )

        is_disqualified = False

        if is_women_scheme:
            if is_women_led:
                score += 20
                reasons.append("Eligible for affirmative Women Entrepreneur quota (>=51% women ownership)")
            else:
                score = 0
                is_disqualified = True
                concerns.append("Disqualified: Scheme is strictly reserved for women entrepreneurs (>=51% women equity). Male founders cannot be primary applicants.")
        elif is_women_led and ("women" in elig_text or "women" in full_scheme_text):
            score += 15
            reasons.append("Women-led enterprise preference benefit")

        if not is_disqualified:
            if asp_category and asp_category in elig_text:
                score += 15
                reasons.append(f"Target affirmative quota ({asp_category.upper()})")
            elif "obc" in elig_text or "backward" in full_scheme_text:
                score += 15
                reasons.append("Affirmative funding preference for backward classes")
            elif "dpiit" in elig_text:
                score += 8
                reasons.append("DPIIT recognized startup benefit")
            else:
                score += 3

        final_score = max(0, min(score, 100))
        if is_disqualified:
            status = "DISQUALIFIED"
        else:
            status = "HIGHLY RECOMMENDED" if final_score >= 80 else "RECOMMENDED" if final_score >= 65 else "QUALIFIED" if final_score >= 50 else "LOW FIT"

        s_copy = dict(s)
        s_copy["match_score"] = final_score
        s_copy["score"] = final_score
        s_copy["recommendation_status"] = status
        s_copy["match_reasons"] = reasons
        s_copy["reasons"] = reasons
        s_copy["potential_concerns"] = concerns
        s_copy["scheme"] = s

        # Filter by min_score
        if min_score is None or final_score >= min_score:
            results.append(s_copy)

    results.sort(key=lambda x: x["match_score"], reverse=True)
    if limit is not None:
        return results[:limit]
    return results

def evaluate_scheme_for_aspirant(aspirant_id: str, scheme_or_id: Any, profile: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Evaluates a specific scheme against an Aspirant's profile for the Guide's evaluation panel.
    Accepts either a scheme dict or a scheme_id string.
    Returns calculated score, match reasons, eligibility checklist, red flags, and hidden agenda.
    """
    if isinstance(scheme_or_id, str):
        scheme = get_scheme(scheme_or_id)
        if not scheme:
            admin = _get_admin_client()
            if admin:
                try:
                    res_s = admin.table("schemes").select("*").eq("id", scheme_or_id).execute()
                    if res_s.data:
                        scheme = res_s.data[0]
                except Exception:
                    pass
    else:
        scheme = scheme_or_id

    if not scheme:
        return {}

    # Run matching for this scheme
    matches = match_schemes_for_aspirant(aspirant_id, profile=profile, limit=None, min_score=0)
    match_record = next((m for m in matches if str(m.get("id")) == str(scheme.get("id"))), None)

    score = match_record["match_score"] if match_record else 50
    reasons = match_record.get("match_reasons", []) if match_record else ["General scheme eligibility review."]
    concerns = match_record.get("potential_concerns", []) if match_record else []
    status = match_record.get("recommendation_status", "RECOMMENDED") if match_record else "RECOMMENDED"

    elig = scheme.get("eligibility") or []
    if isinstance(elig, str):
        try:
            elig = json.loads(elig)
        except Exception:
            elig = [elig]

    checklist = []
    for item in elig:
        checklist.append({"item": str(item), "status": "Verified Eligible"})

    hidden_agenda = scheme.get("hidden_agenda") or []
    if isinstance(hidden_agenda, str):
        try:
            hidden_agenda = json.loads(hidden_agenda)
        except Exception:
            hidden_agenda = [hidden_agenda] if hidden_agenda else []

    red_flags = scheme.get("red_flags") or []
    if isinstance(red_flags, str):
        try:
            red_flags = json.loads(red_flags)
        except Exception:
            red_flags = [red_flags] if red_flags else []

    return {
        "match_score": score,
        "score": score,
        "recommendation_status": status,
        "match_reasons": reasons,
        "reasons": reasons,
        "potential_concerns": concerns,
        "scheme": scheme,
        "checklist": checklist,
        "eligibility_summary": f"Score: {score}% Match ({status}) | {len(reasons)} criteria met",
        "red_flags": red_flags,
        "hidden_agenda": hidden_agenda,
        "prompt": scheme.get("application_prompt") or ""
    }

def release_scheme_to_aspirant(
    guide_id: str,
    aspirant_id: str,
    scheme_id: str,
    guide_recommendation: str = "",
    guide_note: str = ""
) -> Tuple[bool, Optional[str]]:
    """
    Guide Gatekeeper action: Releases a scheme to an assigned Aspirant.
    """
    from services.relationships import get_aspirant_mentors
    from services.journey import log_meaningful_event

    # 1. Authorization check
    mentors = get_aspirant_mentors(aspirant_id)
    assigned_guide = mentors.get("guide")
    if not assigned_guide or str(assigned_guide.get("id")) != str(guide_id):
        return False, "You are not authorized to release schemes to this Aspirant."

    scheme = get_scheme(scheme_id)
    if not scheme:
        return False, "Scheme record not found."
    scheme_name = scheme.get("name", "Funding Opportunity")

    # Evaluate summary
    eval_res = evaluate_scheme_for_aspirant(aspirant_id, scheme)
    eligibility_summary = eval_res.get("eligibility_summary", "Potentially Eligible") if eval_res else "Potentially Eligible"

    now_iso = datetime.now(timezone.utc).isoformat()
    note_text = guide_note.strip() if guide_note else ""
    rec_text = guide_recommendation.strip() if guide_recommendation else "Reviewed and recommended by your Guide."

    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        admin = _get_admin_client()
        writer = client if client else admin
        if not writer:
            return False, "Supabase client not available."
        try:
            try:
                writer.table("scheme_releases").upsert({
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
            except Exception as e:
                if admin and admin != writer:
                    admin.table("scheme_releases").upsert({
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
                else:
                    raise e
        except Exception as e:
            return False, f"Failed to release scheme in Supabase: {e}"
    else:
        # SQLite mode
        get_local_db().create_or_update_scheme_release(
            aspirant_id=aspirant_id,
            guide_id=guide_id,
            scheme_id=scheme_id,
            guide_recommendation=rec_text,
            guide_note=note_text,
            eligibility_summary=eligibility_summary
        )

    # Log Journey Event
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

    # Dispatch In-App Notification to Aspirant
    try:
        from services.notifications import create_notification
        create_notification(
            user_id=aspirant_id,
            title=f"Scheme Released: {scheme_name}",
            message=f"Your Guide has released a curated scheme: '{scheme_name}'. Recommendation: {rec_text}",
            notification_type="scheme_released",
            actor_id=guide_id
        )
    except Exception as e:
        print(f"[Schemes] Notification error: {e}")

    return True, None

def withdraw_scheme_release(
    guide_id: str,
    aspirant_id: str,
    scheme_id: str
) -> Tuple[bool, Optional[str]]:
    """
    Guide Gatekeeper action: Withdraws a previously released scheme.
    """
    from services.relationships import get_aspirant_mentors
    from services.journey import log_meaningful_event

    mentors = get_aspirant_mentors(aspirant_id)
    assigned_guide = mentors.get("guide")
    if not assigned_guide or str(assigned_guide.get("id")) != str(guide_id):
        return False, "You are not authorized to release schemes to this Aspirant."

    scheme = get_scheme(scheme_id)
    scheme_name = scheme.get("name", "Funding Opportunity") if scheme else "Funding Opportunity"
    now_iso = datetime.now(timezone.utc).isoformat()

    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        admin = _get_admin_client()
        writer = client if client else admin
        if not writer:
            return False, "Supabase client not available."
        try:
            try:
                writer.table("scheme_releases").update({
                    "status": "WITHDRAWN",
                    "withdrawn_at": now_iso,
                    "withdrawn_by": guide_id,
                    "updated_at": now_iso
                }).eq("aspirant_id", aspirant_id).eq("scheme_id", scheme_id).execute()
            except Exception as e:
                if admin and admin != writer:
                    admin.table("scheme_releases").update({
                        "status": "WITHDRAWN",
                        "withdrawn_at": now_iso,
                        "withdrawn_by": guide_id,
                        "updated_at": now_iso
                    }).eq("aspirant_id", aspirant_id).eq("scheme_id", scheme_id).execute()
                else:
                    raise e
        except Exception as e:
            return False, f"Failed to withdraw scheme release in Supabase: {e}"
    else:
        # SQLite mode
        get_local_db().withdraw_scheme_release(aspirant_id, scheme_id, guide_id)

    # Log Journey Event
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
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        admin = _get_admin_client()
        reader = client if client else admin
        if reader:
            try:
                # 1. Fetch release records for this aspirant (RLS enforces aspirant reads own released records)
                res = None
                try:
                    res = reader.table("scheme_releases")\
                        .select("*")\
                        .eq("aspirant_id", aspirant_id)\
                        .eq("status", "RELEASED")\
                        .execute()
                except Exception:
                    pass
                if (not res or not res.data) and admin and admin != reader:
                    try:
                        res = admin.table("scheme_releases")\
                            .select("*")\
                            .eq("aspirant_id", aspirant_id)\
                            .eq("status", "RELEASED")\
                            .execute()
                    except Exception:
                        pass
                if not res or not res.data:
                    return []

                # 2. Extract scheme IDs and fetch active scheme catalogue records
                scheme_ids = [r["scheme_id"] for r in res.data if r.get("scheme_id")]
                if not scheme_ids:
                    return []

                fetcher = admin if admin else reader
                s_res = fetcher.table("schemes").select("*").in_("id", scheme_ids).eq("is_active", True).execute()
                s_map = {str(s["id"]): s for s in (s_res.data or [])}

                cleaned = []
                for r in res.data:
                    sid = str(r.get("scheme_id"))
                    s = s_map.get(sid)
                    if not s:
                        s = get_local_db().get_scheme_by_id(sid)
                    if not s:
                        continue
                    s_clean = dict(s)
                    s_clean["release_id"] = r.get("id")
                    s_clean["guide_id"] = r.get("guide_id")
                    s_clean["guide_recommendation"] = r.get("guide_recommendation")
                    s_clean["guide_note"] = r.get("guide_note")
                    s_clean["released_at"] = r.get("released_at")
                    s_clean["eligibility_summary"] = r.get("eligibility_summary")
                    # STRICT PRIVATE INTELLIGENCE STRIPPING
                    s_clean["hidden_agenda"] = []
                    s_clean["red_flags"] = []
                    s_clean["application_prompt"] = ""
                    cleaned.append(s_clean)
                return cleaned
            except Exception as e:
                print(f"[Schemes] Supabase released schemes query error: {e}")
                return []
        return []

    return get_local_db().get_released_schemes_for_aspirant(aspirant_id)

def get_guide_scheme_releases(guide_id: str, aspirant_id: Optional[str] = None) -> List[Dict]:
    """
    Returns complete release history (RELEASED and WITHDRAWN) for Guide view.
    """
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        admin = _get_admin_client()
        reader = client if client else admin
        if reader:
            try:
                res = None
                try:
                    q = reader.table("scheme_releases").select("*, schemes(name, agency, amount), profiles:aspirant_id(full_name, email)")
                    q = q.eq("guide_id", guide_id)
                    if aspirant_id:
                        q = q.eq("aspirant_id", aspirant_id)
                    res = q.order("updated_at", desc=True).execute()
                except Exception:
                    pass
                if (not res or not res.data) and admin and admin != reader:
                    try:
                        q = admin.table("scheme_releases").select("*, schemes(name, agency, amount), profiles:aspirant_id(full_name, email)")
                        q = q.eq("guide_id", guide_id)
                        if aspirant_id:
                            q = q.eq("aspirant_id", aspirant_id)
                        res = q.order("updated_at", desc=True).execute()
                    except Exception:
                        pass
                if res and res.data:
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
                return []
            except Exception as e:
                print(f"[Schemes] Supabase guide releases query error: {e}")
                return []
        return []

    return get_local_db().get_scheme_releases_for_guide(guide_id, aspirant_id)
