"""
services/profiles.py — Profile Service for FULCRUM-INDIA (Cluster A)
====================================================================
Manages Naukri/LinkedIn-style profile with 4 sections:
1. PERSONAL (Name, Email, Phone, Gender, DOB, Address, District, State)
2. PROFESSIONAL (Education, Skills, Experience, Certifications, Expertise)
3. BUSINESS (Name, Type, Sector, Stage, Description, Founded Date, Revenue, Team, Location)
4. DEMOGRAPHICS (District, State, Category, Special eligibility)

Automation:
- Saving an important business profile update recalculates scheme matches
- Records a meaningful Journey event
"""

from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from services.auth import get_supabase_client, get_supabase_admin_client, get_data_backend
from services.local_db import get_local_db

def _get_user_client():
    """Returns the authenticated user's Supabase client (RLS-enforced)."""
    return get_supabase_client()

def _get_admin_client():
    """Returns the privileged admin Supabase client (bypasses RLS). Use sparingly."""
    return get_supabase_admin_client()

def calculate_completion(p: Dict) -> int:
    """Calculates profile completion percentage (0-100%)."""
    data = p.get("profile_data", {})
    if isinstance(data, str):
        try:
            import json
            data = json.loads(data)
        except Exception:
            data = {}

    personal = data.get("personal", {})
    prof = data.get("professional", {})
    biz = data.get("business", {})
    demo = data.get("demographics", {})

    points = 0
    total = 10

    # 1. Personal (2 pts)
    if p.get("full_name") and p.get("phone"): points += 1
    if personal.get("address") or p.get("district"): points += 1

    # 2. Professional (2 pts)
    if prof.get("education") or prof.get("skills"): points += 1
    if prof.get("experience") or prof.get("experience_years") or prof.get("expertise"): points += 1

    # 3. Business (4 pts)
    if biz.get("business_name"): points += 1
    if biz.get("sector"): points += 1
    if biz.get("stage"): points += 1
    if biz.get("description") or biz.get("revenue") or biz.get("brief"): points += 1

    # 4. Demographics (2 pts)
    if demo.get("category") or demo.get("founder_category") or demo.get("social_category"): points += 1
    if p.get("district") and p.get("state"): points += 1

    return int((points / total) * 100)

def get_profile(user_id: str) -> Optional[Dict]:
    """Fetches user profile by ID using active backend."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        if client:
            try:
                res = client.table("profiles").select("*").eq("id", user_id).execute()
                if res.data and len(res.data) > 0:
                    p = res.data[0]
                    p["completion_pct"] = calculate_completion(p)
                    return p
            except Exception as e:
                print(f"[Profiles] Supabase query error: {e}")
        
        # Admin client fallback for service lookups & background tasks
        admin = _get_admin_client()
        if admin:
            try:
                res = admin.table("profiles").select("*").eq("id", user_id).execute()
                if res.data and len(res.data) > 0:
                    p = res.data[0]
                    p["completion_pct"] = calculate_completion(p)
                    return p
            except Exception as e:
                print(f"[Profiles] Supabase admin fallback error: {e}")
        return None

    # SQLite mode
    p = get_local_db().get_profile_by_id(user_id)
    if p:
        p["completion_pct"] = calculate_completion(p)
        return p
    return None

def list_profiles_by_role(role: str) -> List[Dict]:
    """Lists profiles by role from active backend."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_admin_client()
        if client:
            try:
                res = client.table("profiles").select("*").eq("role", role).order("created_at", desc=True).execute()
                rows = res.data or []
                for r in rows:
                    r["completion_pct"] = calculate_completion(r)
                return rows
            except Exception as e:
                print(f"[Profiles] Supabase list error for {role}: {e}")
                return []
        return []

    # SQLite mode
    rows = get_local_db().list_profiles_by_role(role)
    for r in rows:
        r["completion_pct"] = calculate_completion(r)
    return rows

def update_aspirant_profile(
    user_id: str,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    district: Optional[str] = None,
    state: Optional[str] = None,
    personal_data: Optional[Dict] = None,
    professional_data: Optional[Dict] = None,
    business_data: Optional[Dict] = None,
    demographics_data: Optional[Dict] = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Updates Aspirant profile across the 4 core sections.
    Supports either individual fields or a combined dictionary passed as second argument.
    Triggers automated scheme match recalculation & Journey event logging.
    """
    current = get_profile(user_id)
    if not current:
        return None, "User profile not found."

    # If full_name was passed as a dict of sections (e.g. in test script or API)
    if isinstance(full_name, dict):
        d = full_name
        personal_data = d.get("personal", {})
        professional_data = d.get("professional", {})
        business_data = d.get("business", {})
        demographics_data = d.get("demographics", {})
        full_name = personal_data.get("full_name") or current.get("full_name", "")
        phone = personal_data.get("phone") or current.get("phone", "")
        district = demographics_data.get("district") or personal_data.get("district") or current.get("district", "Tamil Nadu")
        state = demographics_data.get("state") or personal_data.get("state") or current.get("state", "Tamil Nadu")

    full_name = (full_name or current.get("full_name", "")).strip()
    phone = (phone or current.get("phone", "")).strip()
    district = (district or current.get("district", "")).strip()
    state = (state or current.get("state", "Tamil Nadu")).strip()

    profile_data = {
        "personal": personal_data or {},
        "professional": professional_data or {},
        "business": business_data or {},
        "demographics": demographics_data or {}
    }

    updated_record = {
        "id": user_id,
        "email": current["email"],
        "role": current.get("role", "aspirant"),
        "full_name": full_name.strip(),
        "phone": phone.strip(),
        "district": district.strip(),
        "state": state.strip(),
        "profile_data": profile_data,
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        if not client:
            return None, "Supabase client not available."
        try:
            # Under Postgres RLS, 'update' uses the UPDATE policy ("Users update own profile")
            # whereas 'upsert' triggers the INSERT policy which requires admin privileges
            res = client.table("profiles").update(updated_record).eq("id", user_id).execute()
            if not res.data:
                admin = _get_admin_client()
                if admin:
                    admin.table("profiles").upsert(updated_record, on_conflict="id").execute()
            # Update Journey business type and stage
            client.table("journeys").update({
                "title": f"{business_data.get('business_name') or full_name}'s Journey",
                "business_type": business_data.get("sector") or business_data.get("business_type") or "Entrepreneurship",
                "stage": business_data.get("stage", "idea"),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("aspirant_id", user_id).execute()
        except Exception as e:
            admin = _get_admin_client()
            if admin:
                try:
                    admin.table("profiles").update(updated_record).eq("id", user_id).execute()
                    admin.table("journeys").update({
                        "title": f"{business_data.get('business_name') or full_name}'s Journey",
                        "business_type": business_data.get("sector") or business_data.get("business_type") or "Entrepreneurship",
                        "stage": business_data.get("stage", "idea"),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("aspirant_id", user_id).execute()
                except Exception as ex2:
                    return None, f"Failed to update profile in Supabase: {ex2}"
            else:
                return None, f"Failed to update profile in Supabase: {e}"
    else:
        # SQLite mode
        local_db = get_local_db()
        local_db.upsert_profile(updated_record)
        j = local_db.get_journey(user_id)
        if j:
            conn = local_db._get_conn()
            cur = conn.cursor()
            cur.execute("""
            UPDATE journeys
            SET title = ?, business_type = ?, stage = ?, updated_at = ?
            WHERE aspirant_id = ?
            """, (
                f"{business_data.get('business_name') or full_name}'s Journey",
                business_data.get("sector") or business_data.get("business_type") or "Entrepreneurship",
                business_data.get("stage", "idea"),
                datetime.now(timezone.utc).isoformat(),
                user_id
            ))
            conn.commit()
            conn.close()

    # Automate Meaningful Journey Event
    from services.journey import log_meaningful_event
    sector_name = business_data.get("sector") or "General"
    biz_name = business_data.get("business_name") or "Enterprise"
    log_meaningful_event(
        aspirant_id=user_id,
        actor_id=user_id,
        actor_role="aspirant",
        event_type="profile_updated",
        title="Business Profile Updated",
        description=f"Updated venture details for '{biz_name}' ({sector_name}, {business_data.get('stage', 'early stage')}).",
        metadata={"sector": sector_name, "stage": business_data.get("stage"), "district": district}
    )

    # Automate Scheme Recalculation & Journey Note
    from services.schemes import match_schemes_for_aspirant
    matches = match_schemes_for_aspirant(user_id)
    if matches:
        top_schemes = [m["name"] for m in matches[:3]]
        log_meaningful_event(
            aspirant_id=user_id,
            actor_id=user_id,
            actor_role="system",
            event_type="scheme_matched",
            title="Funding Opportunities Identified",
            description=f"Matched with {len(matches)} active schemes. Top recommendations: {', '.join(top_schemes)}.",
            metadata={"match_count": len(matches), "top_schemes": top_schemes}
        )

    updated_record["completion_pct"] = calculate_completion(updated_record)
    return updated_record, None

def update_mentor_profile(
    user_id: str,
    full_name: str,
    phone: str,
    district: str,
    expertise: str,
    bio: str,
    industry: Optional[str] = None,
    role: Optional[str] = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Allows Guides and SMEs to update their own contact details and professional background.
    """
    current = get_profile(user_id)
    if not current:
        return None, "Profile not found."

    cur_data = current.get("profile_data", {})
    if isinstance(cur_data, str):
        import json
        try:
            cur_data = json.loads(cur_data)
        except Exception:
            cur_data = {}

    cur_data["expertise"] = expertise.strip() if expertise else ""
    cur_data["bio"] = bio.strip() if bio else ""
    if industry is not None:
        cur_data["industry"] = industry.strip()

    updated_record = {
        "id": user_id,
        "email": current["email"],
        "role": current.get("role", "guide"),
        "full_name": full_name.strip() if full_name else current.get("full_name", ""),
        "phone": phone.strip() if phone else current.get("phone", ""),
        "district": district.strip() if district else current.get("district", "Tamil Nadu"),
        "state": current.get("state", "Tamil Nadu"),
        "profile_data": cur_data,
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    backend = get_data_backend()
    if backend == "supabase":
        client = _get_user_client() or _get_admin_client()
        if not client:
            return None, "Supabase client not available."
        try:
            res = client.table("profiles").update(updated_record).eq("id", user_id).execute()
            if not res.data:
                admin = _get_admin_client()
                if admin:
                    admin.table("profiles").upsert(updated_record, on_conflict="id").execute()
        except Exception as e:
            admin = _get_admin_client()
            if admin:
                try:
                    admin.table("profiles").update(updated_record).eq("id", user_id).execute()
                except Exception as ex2:
                    return None, f"Failed to update profile in Supabase: {ex2}"
            else:
                return None, f"Failed to update profile in Supabase: {e}"
    else:
        # SQLite
        get_local_db().upsert_profile(updated_record)

    try:
        import streamlit as st
        if "user" in st.session_state and st.session_state.get("user_id") == user_id:
            st.session_state.user = updated_record
    except Exception:
        pass

    return updated_record, None

def update_profile(user_id: str, updates: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Generic profile update utility for system routines (e.g. password change flag, metadata)."""
    current = get_profile(user_id)
    if not current:
        return None, "Profile not found."

    merged = dict(current)
    for k, v in updates.items():
        if k == "profile_data" and isinstance(v, dict) and isinstance(merged.get("profile_data"), dict):
            merged_pd = dict(merged["profile_data"])
            merged_pd.update(v)
            merged["profile_data"] = merged_pd
        else:
            merged[k] = v

    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    backend = get_data_backend()
    if backend == "supabase":
        client = _get_admin_client() or _get_user_client()
        if client:
            try:
                valid_cols = {"id", "email", "role", "full_name", "phone", "district", "state", "profile_data", "is_active", "updated_at"}
                db_payload = {k: v for k, v in merged.items() if k in valid_cols}
                client.table("profiles").update(db_payload).eq("id", user_id).execute()
            except Exception as e:
                return None, f"Supabase update error: {e}"
    else:
        get_local_db().upsert_profile(merged)

    return merged, None


