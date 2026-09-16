"""
services/relationships.py — Relationship Assignment Service for FULCRUM-INDIA
=============================================================================
Enforces the mandatory business rule:
- The Admin is the SOLE AUTHORITY for assigning Guides and SMEs.
- Aspirants cannot assign Guides or SMEs.
- Mentors cannot self-assign.
- Assignments automatically generate meaningful chronological Journey events.
Supports dual backends: Supabase (primary) and SQLite (explicit local development).
"""

import json
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

def get_aspirant_mentors(aspirant_id: str) -> Dict[str, Optional[Dict]]:
    """Fetches assigned Guide and SME details for an Aspirant from active backend."""
    backend = get_data_backend()
    from services.profiles import get_profile

    if backend == "supabase":
        admin = _get_admin_client()
        client = _get_user_client()
        fetcher = admin if admin else client
        rel = None
        if fetcher:
            try:
                res = fetcher.table("relationships").select("*").eq("aspirant_id", aspirant_id).execute()
                if res.data and len(res.data) > 0:
                    rel = res.data[0]
            except Exception as e:
                print(f"[Relationships] Supabase query error: {e}")

        guide = None
        guides = []
        guide_b = None
        sme = None
        smes = []
        if rel:
            if rel.get("guide_id"):
                guide = get_profile(rel["guide_id"])
            guide_ids = rel.get("guide_ids") or []
            if isinstance(guide_ids, str):
                try: guide_ids = json.loads(guide_ids)
                except Exception: guide_ids = []
            if not isinstance(guide_ids, list):
                guide_ids = []
            if rel.get("guide_id") and rel["guide_id"] not in guide_ids:
                guide_ids.insert(0, rel["guide_id"])
            for gid in guide_ids:
                gp = get_profile(gid)
                if gp and not any(existing["id"] == gp["id"] for existing in guides):
                    guides.append(gp)
            if not guides and guide:
                guides = [guide]
            if len(guides) > 1:
                guide_b = guides[1]

            if rel.get("sme_id"):
                sme = get_profile(rel["sme_id"])
            sme_ids = rel.get("sme_ids") or []
            if isinstance(sme_ids, str):
                try:
                    sme_ids = json.loads(sme_ids)
                except Exception:
                    sme_ids = []
            if not isinstance(sme_ids, list):
                sme_ids = []
            if rel.get("sme_id") and rel["sme_id"] not in sme_ids:
                sme_ids.insert(0, rel["sme_id"])
            for sid in sme_ids:
                sp = get_profile(sid)
                if sp and not any(existing["id"] == sp["id"] for existing in smes):
                    smes.append(sp)
            if not smes and sme:
                smes = [sme]

        if len(guides) <= 1:
            try:
                local_rel = get_local_db().get_relationship(aspirant_id)
                if local_rel and local_rel.get("guide_ids"):
                    lg_ids = json.loads(local_rel["guide_ids"]) if isinstance(local_rel["guide_ids"], str) else local_rel["guide_ids"]
                    for gid in lg_ids:
                        gp = get_profile(gid)
                        if gp and not any(existing["id"] == gp["id"] for existing in guides):
                            guides.append(gp)
                    if len(guides) > 1:
                        guide_b = guides[1]
            except Exception:
                pass

        return {
            "guide": guide,
            "guide_b": guide_b,
            "guides": guides,
            "sme": sme,
            "smes": smes,
            "relationship": rel
        }

    # SQLite local mode
    rel = get_local_db().get_relationship(aspirant_id)
    guide = None
    guides = []
    guide_b = None
    sme = None
    smes = []
    if rel:
        if rel.get("guide_id"):
            guide = get_profile(rel["guide_id"])
        guide_ids = rel.get("guide_ids") or []
        if isinstance(guide_ids, str):
            try: guide_ids = json.loads(guide_ids)
            except Exception: guide_ids = []
        if not isinstance(guide_ids, list):
            guide_ids = []
        if rel.get("guide_id") and rel["guide_id"] not in guide_ids:
            guide_ids.insert(0, rel["guide_id"])
        for gid in guide_ids:
            gp = get_profile(gid)
            if gp and not any(existing["id"] == gp["id"] for existing in guides):
                guides.append(gp)
        if not guides and guide:
            guides = [guide]
        if len(guides) > 1:
            guide_b = guides[1]

        if rel.get("sme_id"):
            sme = get_profile(rel["sme_id"])
        sme_ids = rel.get("sme_ids") or []
        if isinstance(sme_ids, str):
            try:
                sme_ids = json.loads(sme_ids)
            except Exception:
                sme_ids = []
        if not isinstance(sme_ids, list):
            sme_ids = []
        if rel.get("sme_id") and rel["sme_id"] not in sme_ids:
            sme_ids.insert(0, rel["sme_id"])
        for sid in sme_ids:
            sp = get_profile(sid)
            if sp and not any(existing["id"] == sp["id"] for existing in smes):
                smes.append(sp)
        if not smes and sme:
            smes = [sme]

    return {
        "guide": guide,
        "guide_b": guide_b,
        "guides": guides,
        "sme": sme,
        "smes": smes,
        "relationship": rel
    }

def assign_guide(
    aspirant_id: str,
    guide_id: str,
    admin_id: Optional[str] = None,
    notes: str = "",
    assigned_by: Optional[str] = None,
    mode: str = "replace"
) -> Tuple[bool, Optional[str]]:
    """Admin assigns Guide to an Aspirant with transition history and alerts.
    mode='replace': replaces the primary Guide.
    mode='add': assigns as Co-Guide (Guide B) alongside the primary Guide.
    """
    admin_id = admin_id or assigned_by
    from services.profiles import get_profile
    from services.journey import log_meaningful_event
    from services.notifications import create_notification

    guide = get_profile(guide_id)
    if not guide or guide.get("role") != "guide":
        return False, "Selected mentor is not a valid Guide."

    aspirant = get_profile(aspirant_id)
    if not aspirant:
        return False, "Aspirant not found."

    # Inspect current assignment
    curr_mentors = get_aspirant_mentors(aspirant_id)
    old_guide = curr_mentors.get("guide")
    old_guide_id = old_guide["id"] if old_guide else None
    existing_guides = curr_mentors.get("guides", [])
    existing_guide_ids = [g["id"] for g in existing_guides]

    if mode == "add":
        if guide_id in existing_guide_ids:
            return False, "This mentor is already assigned as a Guide to this entrepreneur."
        new_guide_ids = list(dict.fromkeys(existing_guide_ids + [guide_id]))
        primary_guide_id = old_guide_id or guide_id
        is_replacement = False
        is_co_guide = True
    else:
        is_replacement = bool(old_guide_id and str(old_guide_id) != str(guide_id))
        new_guide_ids = [guide_id]
        primary_guide_id = guide_id
        is_co_guide = False

    backend = get_data_backend()
    now_iso = datetime.now(timezone.utc).isoformat()

    if backend == "supabase":
        client = _get_admin_client()
        if not client:
            return False, "Supabase client not available."
        try:
            client.table("relationships").upsert({
                "aspirant_id": aspirant_id,
                "guide_id": primary_guide_id,
                "guide_ids": new_guide_ids,
                "assigned_by": admin_id,
                "notes": notes,
                "status": "active",
                "updated_at": now_iso
            }, on_conflict="aspirant_id").execute()

            # Record assignment history
            import uuid
            hist_id = str(uuid.uuid4())
            action_label = "ASSIGNED" if not is_replacement else "REPLACED"
            hist_note = f"Co-Guide (Guide B) added. {notes}" if is_co_guide else notes
            client.table("assignment_history").insert({
                "id": hist_id,
                "aspirant_id": aspirant_id,
                "mentor_id": guide_id,
                "mentor_role": "guide",
                "assigned_by": admin_id,
                "action": action_label,
                "previous_mentor_id": old_guide_id if is_replacement else None,
                "notes": hist_note,
                "created_at": now_iso
            }).execute()

            # Transfer open/in-progress tickets to the new Guide if replaced
            if is_replacement:
                try:
                    client.table("help_requests").update({
                        "assigned_guide_id": guide_id,
                        "updated_at": now_iso
                    }).eq("aspirant_id", aspirant_id).in_("status", ["OPEN", "IN_PROGRESS"]).execute()
                except Exception:
                    pass
        except Exception as e:
            print(f"[Relationships] Supabase guide_ids notice ({e}), trying without guide_ids")
            try:
                client.table("relationships").upsert({
                    "aspirant_id": aspirant_id,
                    "guide_id": primary_guide_id,
                    "assigned_by": admin_id,
                    "notes": notes,
                    "status": "active",
                    "updated_at": now_iso
                }, on_conflict="aspirant_id").execute()
            except Exception as e2:
                print(f"[Relationships] Supabase assign_guide warning: {e2}")

        # Always synchronize to local_db
        conn = get_local_db()._get_conn()
        cur = conn.cursor()
        cur.execute("""
        UPDATE relationships
        SET guide_id = ?, guide_ids = ?, assigned_by = ?, notes = ?, updated_at = ?
        WHERE aspirant_id = ?
        """, (primary_guide_id, json.dumps(new_guide_ids), admin_id, notes, now_iso, aspirant_id))
        conn.commit()
        conn.close()
    else:
        # SQLite mode
        conn = get_local_db()._get_conn()
        cur = conn.cursor()
        cur.execute("""
        UPDATE relationships
        SET guide_id = ?, guide_ids = ?, assigned_by = ?, notes = ?, updated_at = ?
        WHERE aspirant_id = ?
        """, (primary_guide_id, json.dumps(new_guide_ids), admin_id, notes, now_iso, aspirant_id))
        conn.commit()
        conn.close()

        action_label = "ASSIGNED" if not is_replacement else "REPLACED"
        hist_note = f"Co-Guide (Guide B) added. {notes}" if is_co_guide else notes
        get_local_db().record_assignment_history(
            aspirant_id=aspirant_id,
            mentor_id=guide_id,
            mentor_role="guide",
            assigned_by=admin_id,
            action=action_label,
            previous_mentor_id=old_guide_id if is_replacement else None,
            notes=hist_note
        )
        if is_replacement:
            try:
                conn = get_local_db()._get_conn()
                cur = conn.cursor()
                cur.execute("UPDATE help_requests SET assigned_guide_id = ? WHERE aspirant_id = ? AND status IN ('OPEN', 'IN_PROGRESS')", (guide_id, aspirant_id))
                conn.commit()
                conn.close()
            except Exception:
                pass

    guide_name = guide.get("full_name") or "Mentor"
    guide_exp = guide.get("profile_data", {}).get("expertise", "Business Guidance") if isinstance(guide.get("profile_data"), dict) else "Business Guidance"
    asp_name = aspirant.get("full_name") or "Entrepreneur"

    if is_replacement and old_guide:
        old_guide_name = old_guide.get("full_name", "Previous Guide")
        # 1. Alert old Guide
        create_notification(
            user_id=old_guide_id,
            title="Mentee Reassigned",
            message=f"You are no longer assigned as Guide to {asp_name}. Mentorship handed over to {guide_name}. Notes: {notes or 'No notes provided.'}",
            notification_type="guide_reassigned",
            actor_id=admin_id
        )
        # 2. Alert new Guide
        create_notification(
            user_id=guide_id,
            title="New Mentee Assigned (Reassignment)",
            message=f"You have been assigned as dedicated Guide for {asp_name}, succeeding {old_guide_name}. Notes: {notes or 'No notes provided.'}",
            notification_type="guide_assigned",
            actor_id=admin_id
        )
        # 3. Alert Aspirant
        create_notification(
            user_id=aspirant_id,
            title="Dedicated Guide Updated",
            message=f"Your dedicated Guide has been updated from {old_guide_name} to {guide_name} ({guide_exp}).",
            notification_type="guide_assigned",
            actor_id=admin_id
        )
        # 4. Journey Event
        log_meaningful_event(
            aspirant_id=aspirant_id,
            actor_id=guide_id,
            actor_role="guide",
            event_type="guide_reassigned",
            title="Guide Transitioned",
            description=f"Mentorship transition: Dedicated guide transitioned to {guide_name} ({guide_exp}).",
            metadata={"old_guide_id": old_guide_id, "new_guide_id": guide_id, "notes": notes}
        )
    else:
        # First-time Guide assignment
        # 1. Alert new Guide
        create_notification(
            user_id=guide_id,
            title="New Mentee Assigned",
            message=f"You have been assigned as dedicated Guide for {asp_name} ({aspirant.get('district', 'Tamil Nadu')}). Notes: {notes or 'No notes provided.'}",
            notification_type="guide_assigned",
            actor_id=admin_id
        )
        # 2. Alert Aspirant
        create_notification(
            user_id=aspirant_id,
            title="Dedicated Guide Assigned",
            message=f"{guide_name} ({guide_exp}) has been assigned as your institutional mentor.",
            notification_type="guide_assigned",
            actor_id=admin_id
        )
        # 3. Journey Event
        log_meaningful_event(
            aspirant_id=aspirant_id,
            actor_id=guide_id,
            actor_role="guide",
            event_type="guide_assigned",
            title="Guide Assigned",
            description=f"{guide_name} ({guide_exp}) assigned as dedicated mentor.",
            metadata={"guide_id": guide_id, "guide_name": guide_name, "notes": notes}
        )

    return True, None

def assign_sme(aspirant_id: str, sme_id: str, admin_id: Optional[str] = None, notes: str = "", assigned_by: Optional[str] = None, mode: str = "add") -> Tuple[bool, Optional[str]]:
    """Admin assigns SME to an Aspirant with transition history and alerts.
    mode="add": Appends SME to the Aspirant's advisory panel.
    mode="replace": Overwrites previous SME assignment(s).
    """
    admin_id = admin_id or assigned_by
    from services.profiles import get_profile
    from services.journey import log_meaningful_event
    from services.notifications import create_notification

    sme = get_profile(sme_id)
    if not sme or sme.get("role") != "sme":
        return False, "Selected mentor is not a valid SME."

    aspirant = get_profile(aspirant_id)
    if not aspirant:
        return False, "Aspirant not found."

    # Inspect current assignment to detect replacement or panel addition
    curr_mentors = get_aspirant_mentors(aspirant_id)
    old_sme = curr_mentors.get("sme")
    old_sme_id = old_sme["id"] if old_sme else None
    existing_sme_ids = [s["id"] for s in curr_mentors.get("smes", [])]

    if mode == "add":
        if sme_id in existing_sme_ids:
            return False, "This specialist is already assigned to this entrepreneur."
        new_sme_ids = list(dict.fromkeys(existing_sme_ids + [sme_id]))
        is_replacement = False
    else:  # mode == "replace"
        is_replacement = bool(old_sme_id and str(old_sme_id) != str(sme_id))
        new_sme_ids = [sme_id]

    backend = get_data_backend()
    now_iso = datetime.now(timezone.utc).isoformat()

    if backend == "supabase":
        client = _get_admin_client()
        if not client:
            return False, "Supabase client not available."
        try:
            try:
                client.table("relationships").upsert({
                    "aspirant_id": aspirant_id,
                    "sme_id": sme_id,
                    "sme_ids": new_sme_ids,
                    "assigned_by": admin_id,
                    "notes": notes,
                    "status": "active",
                    "updated_at": now_iso
                }, on_conflict="aspirant_id").execute()
            except Exception as ex_col:
                client.table("relationships").upsert({
                    "aspirant_id": aspirant_id,
                    "sme_id": sme_id,
                    "assigned_by": admin_id,
                    "notes": notes,
                    "status": "active",
                    "updated_at": now_iso
                }, on_conflict="aspirant_id").execute()

            # Record assignment history
            import uuid
            hist_id = str(uuid.uuid4())
            hist_notes = f"[Advisory Panel Addition] {notes}" if (mode == "add" and notes) else (notes or ("[Advisory Panel Addition]" if mode == "add" else ""))
            client.table("assignment_history").insert({
                "id": hist_id,
                "aspirant_id": aspirant_id,
                "mentor_id": sme_id,
                "mentor_role": "sme",
                "assigned_by": admin_id,
                "action": "REPLACED" if is_replacement else "ASSIGNED",
                "previous_mentor_id": old_sme_id if is_replacement else None,
                "notes": hist_notes,
                "created_at": now_iso
            }).execute()
        except Exception as e:
            return False, f"Failed to record SME assignment in Supabase: {e}"
    else:
        # SQLite mode
        get_local_db().assign_sme(aspirant_id, sme_id, admin_id, notes, mode=mode)
        hist_notes = f"[Advisory Panel Addition] {notes}" if (mode == "add" and notes) else (notes or ("[Advisory Panel Addition]" if mode == "add" else ""))
        get_local_db().record_assignment_history(
            aspirant_id=aspirant_id,
            mentor_id=sme_id,
            mentor_role="sme",
            assigned_by=admin_id,
            action="REPLACED" if is_replacement else "ASSIGNED",
            previous_mentor_id=old_sme_id if is_replacement else None,
            notes=hist_notes
        )

    sme_name = sme.get("full_name") or "Specialist"
    prof_data = sme.get("profile_data") if isinstance(sme.get("profile_data"), dict) else {}
    sme_domain = prof_data.get("expertise") or prof_data.get("industry") or "Subject Matter Expertise"
    asp_name = aspirant.get("full_name") or "Entrepreneur"

    if is_replacement and old_sme:
        old_sme_name = old_sme.get("full_name", "Previous SME")
        # 1. Alert old SME
        create_notification(
            user_id=old_sme_id,
            title="Advisory Case Reassigned",
            message=f"You are no longer assigned as Domain SME for {asp_name}. Reassigned to {sme_name}. Notes: {notes or 'No notes provided.'}",
            notification_type="sme_reassigned",
            actor_id=admin_id
        )
        # 2. Alert new SME
        create_notification(
            user_id=sme_id,
            title="New Advisory Case Assigned",
            message=f"You have been assigned as Domain SME for {asp_name} ({sme_domain}). Notes: {notes or 'No notes provided.'}",
            notification_type="sme_assigned",
            actor_id=admin_id
        )
        # 3. Alert Aspirant
        create_notification(
            user_id=aspirant_id,
            title="Domain Specialist Updated",
            message=f"Your assigned SME for {sme_domain} has been updated to {sme_name}.",
            notification_type="sme_assigned",
            actor_id=admin_id
        )
        # 4. Journey Event
        log_meaningful_event(
            aspirant_id=aspirant_id,
            actor_id=sme_id,
            actor_role="sme",
            event_type="sme_reassigned",
            title="SME Transitioned",
            description=f"Domain specialist transitioned from {old_sme_name} to {sme_name} for {sme_domain}.",
            metadata={"old_sme_id": old_sme_id, "new_sme_id": sme_id, "notes": notes}
        )
    else:
        # First-time SME assignment or Addition to Panel
        # 1. Alert new SME
        create_notification(
            user_id=sme_id,
            title="New Advisory Case Assigned",
            message=f"You have been added to the Advisory Panel for {asp_name} ({sme_domain}). Notes: {notes or 'No notes provided.'}",
            notification_type="sme_assigned",
            actor_id=admin_id
        )
        # 2. Alert Aspirant
        create_notification(
            user_id=aspirant_id,
            title="Domain SME Added",
            message=f"{sme_name} ({sme_domain}) has been assigned to your advisory team.",
            notification_type="sme_assigned",
            actor_id=admin_id
        )
        # 3. Journey Event
        log_meaningful_event(
            aspirant_id=aspirant_id,
            actor_id=sme_id,
            actor_role="sme",
            event_type="sme_assigned",
            title="Specialist Assigned to Panel",
            description=f"{sme_name} assigned to your advisory panel for {sme_domain}.",
            metadata={"sme_id": sme_id, "sme_name": sme_name, "domain": sme_domain, "notes": notes}
        )

    return True, None

def get_assignment_history(aspirant_id: Optional[str] = None, mentor_id: Optional[str] = None) -> List[Dict]:
    """Admin audit log query for mentor reassignments and handovers."""
    backend = get_data_backend()
    if backend == "supabase":
        client = _get_admin_client() or _get_user_client()
        if client:
            try:
                query = client.table("assignment_history").select("*, aspirant:profiles!aspirant_id(full_name), mentor:profiles!mentor_id(full_name), previous_mentor:profiles!previous_mentor_id(full_name)")
                if aspirant_id:
                    query = query.eq("aspirant_id", aspirant_id)
                elif mentor_id:
                    query = query.or_(f"mentor_id.eq.{mentor_id},previous_mentor_id.eq.{mentor_id}")
                res = query.order("created_at", desc=True).execute()
                rows = []
                for r in (res.data or []):
                    d = dict(r)
                    d["aspirant_name"] = r.get("aspirant", {}).get("full_name") if isinstance(r.get("aspirant"), dict) else "Entrepreneur"
                    d["mentor_name"] = r.get("mentor", {}).get("full_name") if isinstance(r.get("mentor"), dict) else "Mentor"
                    d["previous_mentor_name"] = r.get("previous_mentor", {}).get("full_name") if isinstance(r.get("previous_mentor"), dict) else None
                    rows.append(d)
                return rows
            except Exception as e:
                print(f"[Relationships] Supabase assignment history error: {e}")
                return []
        return []

    return get_local_db().list_assignment_history(aspirant_id, mentor_id)

def get_assigned_aspirants_for_guide(guide_id: str) -> List[Dict]:
    """Retrieves all active caseload entrepreneurs for a Guide, including consultation requesters."""
    backend = get_data_backend()
    rows = []
    seen_ids = set()
    from services.profiles import get_profile

    if backend == "supabase":
        client = _get_admin_client() or _get_user_client()
        if client:
            try:
                try:
                    res = client.table("relationships").select("aspirant_id, notes, status, created_at, guide_id, guide_ids").eq("status", "active").execute()
                except Exception:
                    res = client.table("relationships").select("aspirant_id, notes, status, created_at, guide_id").eq("status", "active").execute()
                for r in (res.data or []):
                    g_ids = r.get("guide_ids") or []
                    if isinstance(g_ids, str):
                        try: g_ids = json.loads(g_ids)
                        except Exception: g_ids = []
                    is_active_guide = (r.get("guide_id") == guide_id) or (isinstance(g_ids, list) and guide_id in g_ids)
                    if is_active_guide:
                        aid = r["aspirant_id"]
                        if aid not in seen_ids:
                            p = get_profile(aid)
                            if p:
                                p["assigned_at"] = r.get("created_at")
                                p["assignment_notes"] = r.get("notes")
                                rows.append(p)
                                seen_ids.add(aid)
            except Exception as e:
                print(f"[Relationships] Supabase list aspirants for guide error: {e}")

            return rows
        return []

    return get_local_db().list_aspirants_for_guide(guide_id)

def get_assigned_aspirants_for_sme(sme_id: str) -> List[Dict]:
    """Retrieves all active Aspirants assigned to an SME."""
    backend = get_data_backend()
    rows = []
    seen_ids = set()
    from services.profiles import get_profile

    if backend == "supabase":
        client = _get_admin_client() or _get_user_client()
        if client:
            try:
                try:
                    res = client.table("relationships").select("aspirant_id, notes, status, created_at, sme_id, sme_ids").eq("status", "active").execute()
                except Exception:
                    res = client.table("relationships").select("aspirant_id, notes, status, created_at, sme_id").eq("status", "active").execute()
                for r in (res.data or []):
                    s_ids = r.get("sme_ids") or []
                    if isinstance(s_ids, str):
                        try: s_ids = json.loads(s_ids)
                        except Exception: s_ids = []
                    is_assigned = (r.get("sme_id") == sme_id) or (isinstance(s_ids, list) and sme_id in s_ids)
                    if is_assigned:
                        aid = r["aspirant_id"]
                        if aid not in seen_ids:
                            p = get_profile(aid)
                            if p:
                                p["assigned_at"] = r.get("created_at")
                                p["assignment_notes"] = r.get("notes")
                                rows.append(p)
                                seen_ids.add(aid)
            except Exception as e:
                print(f"[Relationships] Supabase list aspirants for sme error: {e}")

            return rows
        return []

    return get_local_db().list_aspirants_for_sme(sme_id)
