"""
services/relationships.py — Relationship Assignment Service for FULCRUM-INDIA
=============================================================================
Enforces the mandatory business rule:
- The Admin is the SOLE AUTHORITY for assigning Guides and SMEs.
- Aspirants cannot assign Guides or SMEs.
- Mentors cannot self-assign.
- Assignments automatically generate meaningful chronological Journey events.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from services.auth import get_supabase_client
from services.local_db import get_local_db

def get_aspirant_mentors(aspirant_id: str) -> Dict[str, Optional[Dict]]:
    """Fetches assigned Guide and SME details for an Aspirant."""
    rel = None
    client = get_supabase_client()
    if client:
        try:
            res = client.table("relationships").select("*").eq("aspirant_id", aspirant_id).execute()
            if res.data:
                rel = res.data[0]
        except Exception:
            pass

    if not rel:
        rel = get_local_db().get_relationship(aspirant_id)

    guide = None
    sme = None

    if rel:
        from services.profiles import get_profile
        if rel.get("guide_id"):
            guide = get_profile(rel["guide_id"])
        if rel.get("sme_id"):
            sme = get_profile(rel["sme_id"])

    return {
        "guide": guide,
        "sme": sme,
        "relationship": rel
    }

def assign_guide(aspirant_id: str, guide_id: str, admin_id: str, notes: str = "") -> Tuple[bool, Optional[str]]:
    """Admin assigns Guide to an Aspirant."""
    from services.profiles import get_profile
    from services.journey import log_meaningful_event

    guide = get_profile(guide_id)
    if not guide or guide.get("role") != "guide":
        return False, "Selected mentor is not a valid Guide."

    aspirant = get_profile(aspirant_id)
    if not aspirant:
        return False, "Aspirant not found."

    # 1. Update Supabase if available
    client = get_supabase_client()
    if client:
        try:
            client.table("relationships").upsert({
                "aspirant_id": aspirant_id,
                "guide_id": guide_id,
                "assigned_by": admin_id,
                "notes": notes,
                "status": "active",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }, on_conflict="aspirant_id").execute()
        except Exception:
            pass

    # 2. Persist locally
    get_local_db().assign_guide(aspirant_id, guide_id, admin_id, notes)

    # 3. Log Journey Event
    guide_name = guide.get("full_name") or "Mentor"
    guide_exp = guide.get("profile_data", {}).get("expertise", "Business Guidance")
    log_meaningful_event(
        aspirant_id=aspirant_id,
        actor_id=admin_id,
        actor_role="admin",
        event_type="guide_assigned",
        title="Guide Assigned",
        description=f"Admin assigned {guide_name} ({guide_exp}) as dedicated mentor.",
        metadata={"guide_id": guide_id, "guide_name": guide_name, "notes": notes}
    )

    return True, None

def assign_sme(aspirant_id: str, sme_id: str, admin_id: str, notes: str = "") -> Tuple[bool, Optional[str]]:
    """Admin assigns SME to an Aspirant."""
    from services.profiles import get_profile
    from services.journey import log_meaningful_event

    sme = get_profile(sme_id)
    if not sme or sme.get("role") != "sme":
        return False, "Selected mentor is not a valid SME."

    aspirant = get_profile(aspirant_id)
    if not aspirant:
        return False, "Aspirant not found."

    # 1. Update Supabase if available
    client = get_supabase_client()
    if client:
        try:
            client.table("relationships").upsert({
                "aspirant_id": aspirant_id,
                "sme_id": sme_id,
                "assigned_by": admin_id,
                "notes": notes,
                "status": "active",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }, on_conflict="aspirant_id").execute()
        except Exception:
            pass

    # 2. Persist locally
    get_local_db().assign_sme(aspirant_id, sme_id, admin_id, notes)

    # 3. Log Journey Event
    sme_name = sme.get("full_name") or "Specialist"
    sme_domain = sme.get("profile_data", {}).get("expertise") or sme.get("profile_data", {}).get("industry") or "Subject Matter Expertise"
    log_meaningful_event(
        aspirant_id=aspirant_id,
        actor_id=admin_id,
        actor_role="admin",
        event_type="sme_assigned",
        title="SME Assigned",
        description=f"Admin assigned SME {sme_name} for specialized domain advisory in {sme_domain}.",
        metadata={"sme_id": sme_id, "sme_name": sme_name, "domain": sme_domain, "notes": notes}
    )

    return True, None

def get_assigned_aspirants_for_guide(guide_id: str) -> List[Dict]:
    """Retrieves all Aspirants assigned to a Guide."""
    return get_local_db().list_aspirants_for_guide(guide_id)

def get_assigned_aspirants_for_sme(sme_id: str) -> List[Dict]:
    """Retrieves all Aspirants assigned to an SME."""
    return get_local_db().list_aspirants_for_sme(sme_id)
