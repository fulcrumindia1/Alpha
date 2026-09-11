"""
services/journey.py — The Chronological Journey Service for FULCRUM-INDIA
==========================================================================
The central heart of Cluster A: "The entrepreneur's entire movie."
A single chronological timeline recording milestones, mentor support,
admin assignments, and system intelligence events.

Delete Rules:
- Aspirant: Can delete/edit only own manual entries.
- Guide: Can delete/edit only own contributions.
- SME: Can delete/edit only own contributions.
- Admin: Can manage/remove entries via administrative soft deletion.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from services.auth import get_supabase_client
from services.local_db import get_local_db

def get_or_create_journey(aspirant_id: str, title: Optional[str] = None) -> Dict:
    """Retrieves or creates the journey record for an aspirant."""
    local_db = get_local_db()
    j = local_db.get_journey(aspirant_id)
    if not j:
        default_title = title or "Enterprise Journey"
        local_db.create_initial_journey(aspirant_id, default_title)
        j = local_db.get_journey(aspirant_id)
    return j

def get_journey_timeline(aspirant_id: str) -> List[Dict]:
    """
    Returns the complete chronological timeline of journey events.
    Excludes soft-deleted records.
    """
    # 1. Fetch from Supabase if available
    client = get_supabase_client()
    if client:
        try:
            res = client.table("journey_events")\
                .select("*, profiles:actor_id(full_name)")\
                .eq("aspirant_id", aspirant_id)\
                .is_("deleted_at", "null")\
                .order("event_date", desc=False)\
                .execute()
            if res.data:
                timeline = []
                for e in res.data:
                    actor_name = e.get("profiles", {}).get("full_name") if e.get("profiles") else "Contributor"
                    e["actor_name"] = actor_name
                    data = e.get("event_data") or {}
                    if isinstance(data, str):
                        try:
                            import json
                            data = json.loads(data)
                        except Exception:
                            data = {}
                    e["title"] = data.get("title", e.get("event_type", "Event"))
                    e["description"] = data.get("description", "")
                    timeline.append(e)
                return timeline
        except Exception:
            pass

    # 2. Resilient local fallback
    return get_local_db().get_journey_events(aspirant_id)

def add_manual_aspirant_entry(
    aspirant_id: str,
    title: str,
    description: str,
    category: str = "Milestone",
    event_date: Optional[str] = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """Aspirant adds a personal milestone/event to their Journey."""
    if not title or not description:
        return None, "Title and description are required."

    j = get_or_create_journey(aspirant_id)
    date_str = event_date or datetime.now(timezone.utc).isoformat()

    event_payload = {
        "title": title.strip(),
        "description": description.strip(),
        "category": category.strip()
    }

    # 1. Supabase sync
    client = get_supabase_client()
    if client:
        try:
            client.table("journey_events").insert({
                "journey_id": j["id"],
                "aspirant_id": aspirant_id,
                "actor_id": aspirant_id,
                "actor_role": "aspirant",
                "event_type": "aspirant_milestone",
                "event_data": event_payload,
                "event_date": date_str
            }).execute()
        except Exception:
            pass

    # 2. Local DB
    ev = get_local_db().add_journey_event(
        journey_id=j["id"],
        aspirant_id=aspirant_id,
        actor_id=aspirant_id,
        actor_role="aspirant",
        event_type="aspirant_milestone",
        event_data=event_payload,
        event_date=date_str
    )

    return ev, None

def add_guide_contribution(
    aspirant_id: str,
    guide_id: str,
    title: str,
    description: str,
    topic: str = "General Mentorship",
    event_date: Optional[str] = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """Guide logs mentorship support to the assigned Aspirant's Journey."""
    if not title or not description:
        return None, "Title and guidance description are required."

    j = get_or_create_journey(aspirant_id)
    date_str = event_date or datetime.now(timezone.utc).isoformat()

    event_payload = {
        "title": title.strip(),
        "description": description.strip(),
        "topic": topic.strip()
    }

    # Supabase sync
    client = get_supabase_client()
    if client:
        try:
            client.table("journey_events").insert({
                "journey_id": j["id"],
                "aspirant_id": aspirant_id,
                "actor_id": guide_id,
                "actor_role": "guide",
                "event_type": "guide_support",
                "event_data": event_payload,
                "event_date": date_str
            }).execute()
        except Exception:
            pass

    ev = get_local_db().add_journey_event(
        journey_id=j["id"],
        aspirant_id=aspirant_id,
        actor_id=guide_id,
        actor_role="guide",
        event_type="guide_support",
        event_data=event_payload,
        event_date=date_str
    )
    return ev, None

def add_sme_contribution(
    aspirant_id: str,
    sme_id: str,
    title: str,
    description: str,
    domain: str = "Domain Advisory",
    event_date: Optional[str] = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """SME logs specialized advisory support to the assigned Aspirant's Journey."""
    if not title or not description:
        return None, "Title and guidance description are required."

    j = get_or_create_journey(aspirant_id)
    date_str = event_date or datetime.now(timezone.utc).isoformat()

    event_payload = {
        "title": title.strip(),
        "description": description.strip(),
        "domain": domain.strip()
    }

    # Supabase sync
    client = get_supabase_client()
    if client:
        try:
            client.table("journey_events").insert({
                "journey_id": j["id"],
                "aspirant_id": aspirant_id,
                "actor_id": sme_id,
                "actor_role": "sme",
                "event_type": "sme_support",
                "event_data": event_payload,
                "event_date": date_str
            }).execute()
        except Exception:
            pass

    ev = get_local_db().add_journey_event(
        journey_id=j["id"],
        aspirant_id=aspirant_id,
        actor_id=sme_id,
        actor_role="sme",
        event_type="sme_support",
        event_data=event_payload,
        event_date=date_str
    )
    return ev, None

def log_meaningful_event(
    aspirant_id: str,
    actor_id: str,
    actor_role: str,
    event_type: str,
    title: str,
    description: str,
    metadata: Optional[Dict] = None,
    event_date: Optional[str] = None
):
    """
    Automated helper to record significant milestones:
    - Profile updated
    - Guide assigned
    - SME assigned
    - Scheme matched
    - Help requested/resolved
    """
    j = get_or_create_journey(aspirant_id)
    date_str = event_date or datetime.now(timezone.utc).isoformat()

    payload = {
        "title": title,
        "description": description,
        **(metadata or {})
    }

    client = get_supabase_client()
    if client:
        try:
            client.table("journey_events").insert({
                "journey_id": j["id"],
                "aspirant_id": aspirant_id,
                "actor_id": actor_id,
                "actor_role": actor_role,
                "event_type": event_type,
                "event_data": payload,
                "event_date": date_str
            }).execute()
        except Exception:
            pass

    get_local_db().add_journey_event(
        journey_id=j["id"],
        aspirant_id=aspirant_id,
        actor_id=actor_id,
        actor_role=actor_role,
        event_type=event_type,
        event_data=payload,
        event_date=date_str
    )

def soft_delete_event(event_id: str, user_id: str, user_role: str) -> Tuple[bool, Optional[str]]:
    """Enforces soft deletion permissions."""
    local_db = get_local_db()
    conn = local_db._get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM journey_events WHERE id = ?", (event_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return False, "Event record not found."

    event = dict(row)
    # Check permissions
    if user_role != "admin" and event["actor_id"] != user_id:
        return False, "Permission denied: You can only delete your own journey contributions."

    # Soft delete in Supabase
    client = get_supabase_client()
    if client:
        try:
            client.table("journey_events").update({
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "deleted_by": user_id
            }).eq("id", event_id).execute()
        except Exception:
            pass

    success = local_db.soft_delete_journey_event(event_id, user_id)
    return success, None
