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
Supports dual backends: Supabase (primary) and SQLite (explicit local development).
"""

import json
import uuid
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

def get_or_create_journey(aspirant_id: str, title: Optional[str] = None) -> Dict:
    """Retrieves or creates the journey record for an aspirant using active backend."""
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        if client:
            try:
                res = client.table("journeys").select("*").eq("aspirant_id", aspirant_id).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
            except Exception:
                pass

        admin = _get_admin_client()
        if admin:
            try:
                res = admin.table("journeys").select("*").eq("aspirant_id", aspirant_id).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
                # Create journey if missing
                default_title = title or "Enterprise Journey"
                new_journey = {
                    "aspirant_id": aspirant_id,
                    "title": default_title,
                    "business_type": "Entrepreneurship",
                    "stage": "idea",
                    "status": "active"
                }
                c_res = admin.table("journeys").insert(new_journey).execute()
                if c_res.data and len(c_res.data) > 0:
                    return c_res.data[0]
            except Exception as e:
                pass
        return {
            "id": aspirant_id,
            "aspirant_id": aspirant_id,
            "title": title or "Enterprise Journey",
            "business_type": "Entrepreneurship",
            "stage": "idea",
            "status": "active"
        }

    # SQLite local mode ONLY (when DATA_BACKEND=sqlite)
    local_db = get_local_db()
    j = local_db.get_journey(aspirant_id)
    if not j:
        default_title = title or "Enterprise Journey"
        local_db.create_initial_journey(aspirant_id, default_title)
        j = local_db.get_journey(aspirant_id)
    return j

def get_standard_role_label(role: str, is_aspirant_facing: bool = False) -> str:
    """
    Standardizes internal role keys into official platform titles:
    - aspirant -> Aspirant
    - guide -> Guide
    - sme -> SME (Subject Matter Expert)
    - admin -> Institutional Advisory Council (if aspirant-facing) or Admin
    - system -> System Automation
    """
    r = str(role or "").lower().strip()
    if r == "aspirant":
        return "Aspirant"
    elif r == "guide":
        return "Guide"
    elif r == "sme":
        return "SME (Subject Matter Expert)"
    elif r == "admin":
        return "Institutional Advisory Council" if is_aspirant_facing else "Admin"
    elif r == "system":
        return "System Automation"
    return role.capitalize() if role else "Contributor"

def _normalize_event_date(event_date: Optional[str]) -> str:
    """
    Normalizes event_date. If event_date matches today's calendar date (or is empty),
    attaches the exact current UTC timestamp so same-day entries reflect when they were posted.
    """
    now = datetime.now(timezone.utc)
    if not event_date:
        return now.isoformat()
    raw = str(event_date).strip()
    today_str = now.date().isoformat()
    if raw == today_str:
        return now.isoformat()
    if len(raw) == 10 and raw.count("-") == 2:
        return f"{raw}T12:00:00+00:00"
    return raw

def sort_journey_events(events: List[Dict]) -> List[Dict]:
    """
    Sorts journey events in reverse chronological order (most recent on top, older below).
    - Primary sort: Calendar date of the event (YYYY-MM-DD).
    - Same-day tie-breaker:
        If event_date contains a specific non-midnight time, use it.
        Otherwise, break ties using created_at DESC so entries logged today
        always appear in the exact order they were posted (most recent at top).
    """
    def _key(e):
        ed = str(e.get("event_date") or "").strip()
        ca = str(e.get("created_at") or "").strip()

        date_part = ed[:10] if len(ed) >= 10 else (ca[:10] if len(ca) >= 10 else "1970-01-01")

        has_ed_time = (
            ("T" in ed or " " in ed)
            and not ed.endswith("00:00:00")
            and not ed.endswith("00:00:00+00:00")
            and not ed.endswith("00:00:00Z")
            and not " 00:00:00" in ed
            and not "T00:00:00" in ed
        )

        if has_ed_time:
            time_part = ed[11:]
        else:
            time_part = ca[11:] if len(ca) > 11 else ""

        return (date_part, time_part, ca)

    events.sort(key=_key, reverse=True)
    return events

def get_journey_timeline(aspirant_id: str) -> List[Dict]:
    """
    Returns the complete chronological timeline of journey events, ordered
    with the most recent on top (DESC).
    Excludes soft-deleted records.
    """
    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        if client:
            try:
                res = client.table("journey_events")\
                    .select("*, profiles:actor_id(full_name)")\
                    .eq("aspirant_id", aspirant_id)\
                    .is_("deleted_at", "null")\
                    .order("event_date", desc=True)\
                    .order("created_at", desc=True)\
                    .execute()
                if res.data:
                    timeline = []
                    for e in res.data:
                        actor_name = e.get("profiles", {}).get("full_name") if e.get("profiles") else "Contributor"
                        e["actor_name"] = actor_name
                        data = e.get("event_data") or {}
                        if isinstance(data, str):
                            try:
                                data = json.loads(data)
                            except Exception:
                                data = {}
                        top_inc = e.get("included_in_roadmap")
                        e["title"] = data.get("title", e.get("event_type", "Event"))
                        e["description"] = data.get("description", "")
                        e["included_in_roadmap"] = (top_inc if top_inc is not None else data.get("included_in_roadmap", True)) is not False
                        timeline.append(e)
                    return sort_journey_events(timeline)
            except Exception as e:
                print(f"[Journey] Supabase timeline user client error: {e}")

        # Admin fallback for administrative review & cross-role inspection
        admin = _get_admin_client()
        if admin:
            try:
                res = admin.table("journey_events")\
                    .select("*, profiles:actor_id(full_name)")\
                    .eq("aspirant_id", aspirant_id)\
                    .is_("deleted_at", "null")\
                    .order("event_date", desc=True)\
                    .order("created_at", desc=True)\
                    .execute()
                timeline = []
                for e in (res.data or []):
                    actor_name = e.get("profiles", {}).get("full_name") if e.get("profiles") else "Contributor"
                    e["actor_name"] = actor_name
                    data = e.get("event_data") or {}
                    if isinstance(data, str):
                        try:
                            data = json.loads(data)
                        except Exception:
                            data = {}
                    top_inc = e.get("included_in_roadmap")
                    e["title"] = data.get("title", e.get("event_type", "Event"))
                    e["description"] = data.get("description", "")
                    e["included_in_roadmap"] = (top_inc if top_inc is not None else data.get("included_in_roadmap", True)) is not False
                    timeline.append(e)
                return sort_journey_events(timeline)
            except Exception as e:
                pass
        return []

    # SQLite local fallback ONLY (when DATA_BACKEND=sqlite)
    return sort_journey_events(get_local_db().get_journey_events(aspirant_id))

def toggle_event_roadmap_inclusion(
    event_id: str,
    aspirant_id: str,
    included: bool,
    actor_id: Optional[str] = None,
    actor_role: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Allows an Aspirant to toggle whether a contribution is included in their personal journey roadmap.
    Hardened Authorization:
      - Resolves effective actor from explicit parameters or active session.
      - Verifies that the journey event exists and belongs to the specified aspirant.
      - Enforces that only the owning aspirant can alter roadmap inclusion (rejects guide, sme, admin).
      - Rejects foreign users/aspirants from modifying another entrepreneur's roadmap.
    Mentors (Guide/SME) and Admins retain full visibility with inclusion status indicators.
    """
    # 1. Resolve effective actor identity & role from session if not explicitly provided
    session_user_id = None
    session_role = None
    try:
        import streamlit as st
        if hasattr(st, "session_state"):
            session_user_id = st.session_state.get("user_id") or (
                st.session_state.get("user", {}).get("id")
                if isinstance(st.session_state.get("user"), dict) else None
            )
            session_role = st.session_state.get("role") or (
                st.session_state.get("user", {}).get("role")
                if isinstance(st.session_state.get("user"), dict) else None
            )
    except Exception:
        pass

    effective_actor_id = actor_id or session_user_id
    effective_actor_role = actor_role or session_role

    # Strict role enforcement: Non-aspirant roles (guide, sme, admin) cannot alter founder's roadmap
    if effective_actor_role and effective_actor_role != "aspirant":
        return False, f"Permission denied: {effective_actor_role.capitalize()}s cannot alter the entrepreneur's personal roadmap inclusion."

    backend = get_data_backend()
    if backend == "supabase":
        user_client = _get_user_client()
        admin = _get_admin_client()
        client = user_client or admin
        if not client:
            return False, "Database client not available."

        try:
            ev = None
            if user_client:
                try:
                    res = user_client.table("journey_events").select("*").eq("id", event_id).execute()
                    if res.data and len(res.data) > 0:
                        ev = res.data[0]
                except Exception:
                    pass
            if not ev and admin:
                res = admin.table("journey_events").select("*").eq("id", event_id).execute()
                if res.data and len(res.data) > 0:
                    ev = res.data[0]

            if not ev:
                return False, "Journey event not found."

            event_aspirant_id = ev.get("aspirant_id")
            if not event_aspirant_id or str(event_aspirant_id) != str(aspirant_id):
                return False, "Unauthorized: Event does not belong to the specified aspirant."

            if effective_actor_id and str(effective_actor_id) != str(event_aspirant_id):
                return False, "Unauthorized: You can only alter roadmap inclusion for your own journey."

            ev_data = ev.get("event_data") or {}
            if isinstance(ev_data, str):
                try:
                    ev_data = json.loads(ev_data)
                except Exception:
                    ev_data = {}
            ev_data["included_in_roadmap"] = bool(included)
            now_iso = datetime.now(timezone.utc).isoformat()
            payload = {
                "event_data": ev_data,
                "included_in_roadmap": bool(included),
                "updated_at": now_iso
            }

            # Try updating via user_client first to respect RLS
            updated = False
            if user_client:
                try:
                    u_res = user_client.table("journey_events").update(payload).eq("id", event_id).execute()
                    if u_res.data and len(u_res.data) > 0:
                        updated = True
                except Exception:
                    pass

            if not updated and admin:
                try:
                    admin.table("journey_events").update(payload).eq("id", event_id).eq("aspirant_id", aspirant_id).execute()
                    updated = True
                except Exception:
                    admin.table("journey_events").update({
                        "event_data": ev_data,
                        "updated_at": now_iso
                    }).eq("id", event_id).eq("aspirant_id", aspirant_id).execute()
                    updated = True

            if updated:
                return True, None
            return False, "Failed to update journey event in Supabase."
        except Exception as e:
            return False, f"Failed to update roadmap status in Supabase: {e}"

    # SQLite mode
    success, err_msg = get_local_db().toggle_journey_event_inclusion(
        event_id=event_id,
        aspirant_id=aspirant_id,
        included=included,
        actor_id=effective_actor_id,
        actor_role=effective_actor_role
    )
    if success:
        return True, None
    return False, err_msg or "Failed to update journey event in local database."

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
    date_str = _normalize_event_date(event_date)

    event_payload = {
        "title": title.strip(),
        "description": description.strip(),
        "category": category.strip()
    }

    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        if not client:
            return None, "Supabase client not available."
        try:
            res = client.table("journey_events").insert({
                "journey_id": j["id"],
                "aspirant_id": aspirant_id,
                "actor_id": aspirant_id,
                "actor_role": "aspirant",
                "event_type": "aspirant_milestone",
                "event_data": event_payload,
                "event_date": date_str
            }).execute()
            if res.data and len(res.data) > 0:
                ev = res.data[0]
                ev["title"] = title.strip()
                ev["description"] = description.strip()
                return ev, None
            return {"id": str(uuid.uuid4()), "title": title, "description": description}, None
        except Exception as e:
            admin = _get_admin_client()
            if admin:
                try:
                    res = admin.table("journey_events").insert({
                        "journey_id": j["id"],
                        "aspirant_id": aspirant_id,
                        "actor_id": aspirant_id,
                        "actor_role": "aspirant",
                        "event_type": "aspirant_milestone",
                        "event_data": event_payload,
                        "event_date": date_str
                    }).execute()
                    if res.data and len(res.data) > 0:
                        ev = res.data[0]
                        ev["title"] = title.strip()
                        ev["description"] = description.strip()
                        return ev, None
                    return {"id": str(uuid.uuid4()), "title": title, "description": description}, None
                except Exception as ex2:
                    return None, f"Failed to record journey event in Supabase: {ex2}"
            return None, f"Failed to record journey event in Supabase: {e}"

    # SQLite mode
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
    date_str = _normalize_event_date(event_date)

    event_payload = {
        "title": title.strip(),
        "description": description.strip(),
        "topic": topic.strip()
    }

    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        if not client:
            return None, "Supabase client not available."
        try:
            res = client.table("journey_events").insert({
                "journey_id": j["id"],
                "aspirant_id": aspirant_id,
                "actor_id": guide_id,
                "actor_role": "guide",
                "event_type": "guide_support",
                "event_data": event_payload,
                "event_date": date_str
            }).execute()
            if res.data and len(res.data) > 0:
                ev = res.data[0]
                ev["title"] = title.strip()
                ev["description"] = description.strip()
                return ev, None
            return {"id": str(uuid.uuid4()), "title": title, "description": description}, None
        except Exception as e:
            admin = _get_admin_client()
            if admin:
                try:
                    res = admin.table("journey_events").insert({
                        "journey_id": j["id"],
                        "aspirant_id": aspirant_id,
                        "actor_id": guide_id,
                        "actor_role": "guide",
                        "event_type": "guide_support",
                        "event_data": event_payload,
                        "event_date": date_str
                    }).execute()
                    if res.data and len(res.data) > 0:
                        ev = res.data[0]
                        ev["title"] = title.strip()
                        ev["description"] = description.strip()
                        return ev, None
                    return {"id": str(uuid.uuid4()), "title": title, "description": description}, None
                except Exception as ex2:
                    return None, f"Failed to record Guide contribution in Supabase: {ex2}"
            return None, f"Failed to record Guide contribution in Supabase: {e}"

    # SQLite mode
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

def add_admin_journey_entry(
    aspirant_id: str,
    admin_id: str,
    title: str,
    description: str,
    category: str = "Administrative Directive",
    event_date: Optional[str] = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """Administrator logs an official milestone, grant sanction, or administrative directive to an Aspirant's Journey."""
    if not title or not description:
        return None, "Title and description are required."

    j = get_or_create_journey(aspirant_id)
    date_str = _normalize_event_date(event_date)

    event_payload = {
        "title": title.strip(),
        "description": description.strip(),
        "category": category.strip()
    }

    backend = get_data_backend()

    if backend == "supabase":
        client = _get_admin_client() or _get_user_client()
        if not client:
            return None, "Supabase client not available."
        try:
            res = client.table("journey_events").insert({
                "journey_id": j["id"],
                "aspirant_id": aspirant_id,
                "actor_id": admin_id,
                "actor_role": "admin",
                "event_type": "admin_directive",
                "event_data": event_payload,
                "event_date": date_str
            }).execute()
            if res.data and len(res.data) > 0:
                ev = res.data[0]
                ev["title"] = title.strip()
                ev["description"] = description.strip()
                return ev, None
            return {"id": str(uuid.uuid4()), "title": title, "description": description}, None
        except Exception as e:
            return None, f"Failed to record Admin entry in Supabase: {e}"

    # SQLite mode
    ev = get_local_db().add_journey_event(
        journey_id=j["id"],
        aspirant_id=aspirant_id,
        actor_id=admin_id,
        actor_role="admin",
        event_type="admin_directive",
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
    date_str = _normalize_event_date(event_date)

    event_payload = {
        "title": title.strip(),
        "description": description.strip(),
        "domain": domain.strip()
    }

    backend = get_data_backend()

    if backend == "supabase":
        client = _get_user_client()
        if not client:
            client = _get_admin_client()
        if not client:
            return None, "Supabase client not available."
        try:
            res = client.table("journey_events").insert({
                "journey_id": j["id"],
                "aspirant_id": aspirant_id,
                "actor_id": sme_id,
                "actor_role": "sme",
                "event_type": "sme_support",
                "event_data": event_payload,
                "event_date": date_str
            }).execute()
            if res.data and len(res.data) > 0:
                ev = res.data[0]
                ev["title"] = title.strip()
                ev["description"] = description.strip()
                return ev, None
            return {"id": str(uuid.uuid4()), "title": title, "description": description}, None
        except Exception as e:
            admin = _get_admin_client()
            if admin:
                try:
                    res = admin.table("journey_events").insert({
                        "journey_id": j["id"],
                        "aspirant_id": aspirant_id,
                        "actor_id": sme_id,
                        "actor_role": "sme",
                        "event_type": "sme_support",
                        "event_data": event_payload,
                        "event_date": date_str
                    }).execute()
                    if res.data and len(res.data) > 0:
                        ev = res.data[0]
                        ev["title"] = title.strip()
                        ev["description"] = description.strip()
                        return ev, None
                    return {"id": str(uuid.uuid4()), "title": title, "description": description}, None
                except Exception as ex2:
                    return None, f"Failed to record SME contribution in Supabase: {ex2}"
            return None, f"Failed to record SME contribution in Supabase: {e}"

    # SQLite mode
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
    Automated helper to record significant milestones in active backend:
    - Profile updated
    - Guide assigned
    - SME assigned
    - Scheme matched
    - Help requested/resolved
    """
    j = get_or_create_journey(aspirant_id)
    date_str = _normalize_event_date(event_date)

    payload = {
        "title": title,
        "description": description,
        **(metadata or {})
    }

    backend = get_data_backend()

    if backend == "supabase":
        client = _get_admin_client()
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
            except Exception as e:
                print(f"[Journey] log_meaningful_event Supabase error: {e}")
    else:
        # SQLite mode
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
    """Enforces soft deletion permissions in active backend."""
    backend = get_data_backend()

    if backend == "supabase":
        user_client = _get_user_client()
        admin = _get_admin_client()
        client = user_client or admin
        if not client:
            return False, "Supabase client not available."
        try:
            ev = None
            if user_client:
                try:
                    res = user_client.table("journey_events").select("*").eq("id", event_id).execute()
                    if res.data and len(res.data) > 0:
                        ev = res.data[0]
                except Exception:
                    pass
            if not ev and admin:
                try:
                    res = admin.table("journey_events").select("*").eq("id", event_id).execute()
                    if res.data and len(res.data) > 0:
                        ev = res.data[0]
                except Exception:
                    pass

            if not ev:
                return False, "Event record not found."

            event_actor_id = str(ev.get("actor_id") or "").strip()
            req_user_id = str(user_id or "").strip()

            # Authorization: Admin can delete any event.
            # Other roles (aspirant, guide, sme) can ONLY delete their own contributions.
            if str(user_role).lower() != "admin" and event_actor_id != req_user_id:
                return False, "Permission denied: You can only delete your own journey contributions."

            now_iso = datetime.now(timezone.utc).isoformat()
            payload = {
                "deleted_at": now_iso,
                "deleted_by": user_id
            }

            # Try updating with user_client first to respect RLS
            updated = False
            if user_client:
                try:
                    u_res = user_client.table("journey_events").update(payload).eq("id", event_id).execute()
                    if u_res.data and len(u_res.data) > 0:
                        updated = True
                except Exception:
                    pass

            # Fall back to admin client if user_client failed or RLS blocked UPDATE (e.g. for SME)
            if not updated and admin:
                try:
                    a_res = admin.table("journey_events").update(payload).eq("id", event_id).execute()
                    if a_res.data and len(a_res.data) > 0:
                        updated = True
                except Exception as ex:
                    print(f"[Journey] soft_delete_event admin update error: {ex}")

            if updated:
                return True, None
            return False, "Failed to update deletion status in database."
        except Exception as e:
            return False, f"Failed to delete event: {e}"

    # SQLite mode
    local_db = get_local_db()
    conn = local_db._get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM journey_events WHERE id = ?", (event_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return False, "Event record not found."

    event = dict(row)
    if str(user_role).lower() != "admin" and str(event.get("actor_id")) != str(user_id):
        return False, "Permission denied: You can only delete your own journey contributions."

    success = local_db.soft_delete_journey_event(event_id, user_id)
    return success, None
